"""The core: where the account's idle cash sits (review/profit-overhaul.md, section 3.1).

Two modes, chosen by config "core":
  "leverage": false (default)  Plain SPY, as since 2026-10-20: from buy_after_et, cash above
      the reserve goes into SPY and stays until a pick needs it.
  "leverage": true  A rule-based leveraged core. Once a day, in the 15:35-15:58 ET window,
      the core money is split between TQQQ and SPY. TQQQ weight = min(1, vol_target / (3 x
      QQQ 20-day volatility)) while QQQ closes above its 200-day average, else 0; after three
      lower QQQ closes in a row the core goes 100% TQQQ until the first higher close (at most
      5 sessions). It trades only when the target moved more than `band` from what is held
      (or new cash arrived). The window run uses QQQ's last trade as today's close; if that
      run is skipped, the next run of any kind acts on the completed close at once (the dip
      overlay's edge is the first session after the signal). "weight_live_close": false makes
      the SMA/vol weight wait for completed sessions (the overlay still uses the live price).
      The research runs cannot touch any of this.

Either way the core is not a pick: never adopted, never closed by Claude, not one of the open
positions. Picks are funded by selling SPY first, then TQQQ. While a loss halt is on the core
may reduce TQQQ but never buy. The kill switch and `flatten` close it.

    python -m bot.core paper   # rehearse the leveraged rule on the paper account (mechanics only)
"""
import json
import math
import sys
from datetime import datetime, timedelta, timezone

from . import risk
from .common import ET, log

SIGNAL_KEYS = ("date", "trend", "vol", "weight", "dip_state", "index_close", "lev_target", "rest_target", "halted")


def core_cfg(cfg):
    """The "core" block, or None when the core is off (missing or null)."""
    core = cfg.get("core")
    return core if isinstance(core, dict) and (core.get("symbol") or core.get("rest_symbol")) else None


class Core:
    def __init__(self, trader, cfg, paper_rehearsal=False):
        self.t, self.api, self.cfg = trader, trader.api, cfg
        self.c = core_cfg(cfg) or {}
        self.rest = self.c.get("rest_symbol") or self.c.get("symbol") or "SPY"
        self.lev = self.c.get("lev_symbol") or "TQQQ"
        self.index = self.c.get("index") or "QQQ"
        self.leverage = self.c.get("leverage") is True or paper_rehearsal
        self.reserve = float(self.c.get("reserve", 2.0))
        self.idle_cap = float(cfg.get("sizing_equity_cap") or 0) if paper_rehearsal else None
        tag = "paper_core" if paper_rehearsal else "core"
        self.state_path = trader.root / "state" / f"{tag}.json"
        self.ledger_path = trader.root / "ledger" / f"{tag}.csv"

    @property
    def symbols(self):
        return {self.rest, self.lev}

    # holdings
    def held(self):
        out = {self.rest: 0.0, self.lev: 0.0}
        for p in self.api.positions():
            if p["symbol"] in out:
                out[p["symbol"]] += abs(float(p.get("market_value") or 0))
        return out

    def total(self):
        return sum(self.held().values())

    def load_state(self):
        try:
            return json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            return {}

    def save_state(self, state):
        self.state_path.parent.mkdir(exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    def snapshot(self):
        held = self.held()
        st = self.load_state()
        return {"symbol": self.rest, "value": round(sum(held.values()), 2), "leverage": self.leverage,
                "held": {s: round(v, 2) for s, v in held.items()},
                "signals": {k: st.get(k) for k in SIGNAL_KEYS if k in st}}

    def record(self, now, side, sym, amount, price, reason):
        self.t.record({"time": now.isoformat(), "side": side, "symbol": sym, "notional": f"{amount:.2f}",
                       "price": price, "reason": reason, "mode": self.cfg["mode"]}, self.ledger_path)

    # orders
    def buy(self, sym, amount, now, reason, cid):
        """Limit order 1% over the last trade for `amount` dollars, never more than the per-order
        ceiling (the broker refuses fractional limits sometimes; then market). Whole shares when
        the fund is not fractionable; nothing if it is not tradable. Returns the dollars ordered."""
        asset = self.api.asset(sym) or {}
        if not asset.get("tradable") or asset.get("status") != "active":
            log(f"Core: {sym} is not tradable on Alpaca right now; skipping its buy.")
            return 0.0
        amount = min(amount, float(self.cfg["max_order_notional"]))
        price = self.api.last_price(sym)
        limit = risk.entry_limit(price)
        if asset.get("fractionable", True):
            order = dict(notional=f"{amount:.2f}")
        else:
            qty = risk.whole_shares(amount, limit)
            if qty < 1:
                log(f"Core: one share of {sym} (${price}) costs more than ${amount:.2f}; skipping its buy.")
                return 0.0
            order, amount = dict(qty=str(qty)), qty * limit
        try:
            self.api.submit_order(symbol=sym, side="buy", type="limit", limit_price=f"{limit:.2f}",
                                  time_in_force="day", client_order_id=cid, **order)
        except Exception as e:  # noqa: BLE001 - AlpacaError 422 only; anything else re-raised below
            if getattr(e, "status", None) != 422:
                raise
            self.api.submit_order(symbol=sym, side="buy", type="market", time_in_force="day",
                                  client_order_id=cid, **order)
        log(f"Core: bought ${amount:.2f} of {sym} (limit ${limit:.2f}): {reason}.")
        self.record(now, "buy", sym, amount, price, reason)
        return amount

    def sell(self, sym, amount, held, now, reason, cid):
        """Market sell of `amount` dollars of `sym`; the whole position when that is about all of it."""
        if amount >= held - 0.01:
            self.api.close_position(sym)
            amount = held
        else:
            self.api.submit_order(symbol=sym, side="sell", type="market", notional=f"{amount:.2f}",
                                  time_in_force="day", client_order_id=cid)
        log(f"Core: sold ${amount:.2f} of {sym}: {reason}.")
        self.record(now, "sell", sym, amount, "", reason)
        return amount

    def wait_for_cash(self, needed):
        for _ in range(12):
            cash = float(self.api.account()["cash"])
            if cash >= needed - 0.01:
                return cash
            self.t.sleep(2)
        return float(self.api.account()["cash"])

    def fund(self, budget):
        """Called by Trader.enter() just before a pick's order: sells enough core (SPY first,
        then TQQQ) to cover `budget`. Returns the budget the cash now covers."""
        cash = float(self.api.account()["cash"])
        need = budget / 0.98 - cash   # pick_budget keeps 2% of cash back
        held = self.held()
        if need <= 0 or sum(held.values()) <= 0:
            return min(budget, math.floor(cash * 0.98 * 100) / 100)
        now = self.t.now()
        left = math.ceil(need * 1.01 * 100) / 100   # 1% slack for the market sale
        for sym in (self.rest, self.lev):
            if left <= 0 or held[sym] <= 0:
                continue
            amount = min(held[sym], left)
            sold = self.sell(sym, amount, held[sym], now, "fund pick",
                             f"core-sell-{now.astimezone(ET):%Y%m%d-%H%M%S}-{sym}")
            left -= sold
        cash = self.wait_for_cash(budget / 0.98)
        return min(budget, math.floor(cash * 0.98 * 100) / 100)

    # the daily step
    def run(self, now, today, halted):
        """Once per run, after the picks. Returns True if it placed an order."""
        if self.leverage:
            return self.rebalance(now, today, halted)
        ordered = self.unwind(now)
        if not halted:
            ordered = self.buy_rest(now, today) or ordered
        return ordered

    def unwind(self, now):
        """Leverage was switched off while TQQQ is held: sell it (the SPY buy below reinvests)."""
        held = self.held()
        if held[self.lev] <= 0:
            return False
        self.sell(self.lev, held[self.lev], held[self.lev], now, "leverage off",
                  f"core-sell-{now.astimezone(ET):%Y%m%d-%H%M%S}-{self.lev}")
        self.wait_for_cash(held[self.lev] * 0.99)
        return True

    def buy_rest(self, now, today):
        """Plain core: after buy_after_et, put cash above the reserve into SPY."""
        after = datetime.combine(today, datetime.strptime(self.c.get("buy_after_et", "14:30"), "%H:%M").time(), ET)
        if now < after:
            return False
        if any(o["symbol"] == self.rest for o in self.api.open_orders()):
            return False   # an earlier core order is still working
        acct = self.api.account()
        avail = min(float(acct["cash"]), float(acct.get("buying_power") or acct["cash"]))
        amount = math.floor((avail - self.reserve) * 100) / 100
        if amount < self.cfg["min_order_notional"]:
            return False
        self.buy(self.rest, amount, now, "idle cash", f"core-{now.astimezone(ET):%Y%m%d-%H%M}")
        return True

    def cancel_stale_orders(self):
        """An earlier core order still working (a limit that never filled) would double up
        with today's rebalance: cancel it first."""
        for o in self.api.open_orders():
            if str(o.get("client_order_id", "")).startswith("core-") and o["symbol"] in self.symbols:
                try:
                    self.api.cancel_order(o["id"])
                    log(f"Core: cancelled stale order {o.get('client_order_id')} ({o['symbol']}).")
                except AlpacaError as e:
                    log(f"Core: could not cancel {o.get('client_order_id')}: {e}")

    def in_window(self, now, today):
        lo = datetime.combine(today, datetime.strptime(self.c.get("rebalance_from_et", "15:35"), "%H:%M").time(), ET)
        hi = datetime.combine(today, datetime.strptime(self.c.get("rebalance_until_et", "15:58"), "%H:%M").time(), ET)
        return lo <= now <= hi

    def completed_closes(self, today):
        """QQQ daily closes of completed sessions, oldest first (Alpaca, adjusted), and the
        date of the last one."""
        start = (today - timedelta(days=int(self.c.get("history_days", 420)))).isoformat()
        end = (today - timedelta(days=1)).isoformat()
        bars = [b for b in self.api.daily_bars(self.index, start, end, feed=self.c.get("feed", "sip"))
                if str(b.get("t", ""))[:10] < today.isoformat()]
        closes = [float(b["c"]) for b in bars]
        last = str(bars[-1]["t"])[:10] if bars else None
        return closes, last

    def signals(self, completed, live=None):
        """Signals after the latest close. In the window `live` (QQQ's last trade) stands in
        for today's close; the dip overlay always uses it, the SMA/vol weight only when
        weight_live_close is on (default; off = weight lags a day, ~1.6 pts/yr)."""
        c = self.c
        closes = completed + ([live] if live is not None else [])
        for_weight = closes if live is None or c.get("weight_live_close", True) is not False else completed
        trend = risk.sma_trend(for_weight, int(c.get("sma_days", 200)))
        vol = risk.realized_vol(for_weight, int(c.get("vol_days", 20)))
        weight = risk.core_weight(trend, vol, float(c.get("vol_target", 0.30)), float(c.get("max_lev", 3.0)))
        dip = c.get("dip") or {}
        dip_now = risk.dip_replay(closes, int(dip.get("down_days", 3)), int(dip.get("max_days", 5)))
        enough = len(completed) >= max(int(c.get("sma_days", 200)), int(c.get("vol_days", 20)) + 1)
        return {"trend": trend, "vol": None if vol is None else round(vol, 4), "weight": round(weight, 4),
                "dip_state": dip_now, "index_close": closes[-1] if closes else None, "enough_history": enough}

    def rebalance(self, now, today, halted):
        """One evaluation per close. Inside the window (15:35-15:58 ET) today's last trade is
        the close. Outside it, a close the window run never acted on (the run was skipped)
        is acted on at the next run of any kind: the dip overlay's edge lives in the first
        session after the signal, so it never waits for the next window."""
        state = self.load_state()
        in_window = self.in_window(now, today)
        completed, last_session = self.completed_closes(today)
        as_of = today.isoformat() if in_window else last_session
        if not as_of or str(state.get("date", "")) >= as_of:
            return False   # that close was already evaluated (or nothing new yet)
        sig = self.signals(completed, self.api.last_price(self.index) if in_window else None)
        if not sig.pop("enough_history"):
            log(f"Core: only {len(completed)} {self.index} closes; need the 200-day history. Holding.")
            return False
        if not in_window:
            log(f"Core: the {as_of} close was never acted on; catching up now.")
        want = 1.0 if sig["dip_state"] else sig["weight"]
        self.cancel_stale_orders()
        held = self.held()
        acct = self.api.account()
        cash = min(float(acct["cash"]), float(acct.get("buying_power") or acct["cash"]))
        idle = sum(held.values()) + max(0.0, cash - self.reserve)
        if self.idle_cap:
            idle = min(idle, self.idle_cap)
        held_w = held[self.lev] / idle if idle > 0 else 0.0
        lev_target, rest_target = risk.core_target(idle, sig["weight"], bool(sig["dip_state"]))
        if halted:   # a halt may cut leverage, never add it or buy anything: so the SPY
            lev_target = min(lev_target, held[self.lev])   # sleeve is never sold to fund a
            rest_target = held[self.rest]                  # TQQQ buy the halt would block
        min_order = float(self.cfg["min_order_notional"])
        new_cash = max(0.0, cash - self.reserve) >= min_order
        reason = (f"rebalance trend={sig['trend']} vol={sig['vol']} w={want:.2f} dip={sig['dip_state']}"
                  + (" halted" if halted else "") + ("" if in_window else " catch-up"))
        ordered = False
        if risk.rebalance_needed(held_w, want, float(self.c.get("band", 0.10))) or new_cash:
            diffs = {self.lev: lev_target - held[self.lev], self.rest: rest_target - held[self.rest]}
            stamp = f"{now.astimezone(ET):%Y%m%d-%H%M%S}"
            buys = 0.0
            for sym, d in diffs.items():
                if d < -min_order:
                    self.sell(sym, -d, held[sym], now, reason, f"core-sell-{stamp}-{sym}")
                    ordered = True
            for sym, d in diffs.items():
                if d > min_order and not halted:
                    buys += d
            if buys > 0:
                cash = self.wait_for_cash(buys + self.reserve)
                for sym, d in diffs.items():
                    if d > min_order and not halted:
                        amount = math.floor(min(d, cash - self.reserve) * 100) / 100
                        if amount >= min_order:
                            spent = self.buy(sym, amount, now, reason, f"core-{stamp}-{sym}")
                            cash -= spent
                            ordered = ordered or spent > 0
        else:
            log(f"Core: {reason}; held {held_w:.0%} {self.lev}, within the band. Nothing to do.")
        self.save_state({**sig, "date": as_of, "lev_target": lev_target, "rest_target": rest_target,
                         "halted": halted, "ordered": ordered})
        return ordered


def main(argv):
    """`python -m bot.core paper`: run the leveraged rule once on the paper account, sized
    like the live stake, to check order mechanics before the live switch."""
    from .trader import Trader, load_config, make_client
    if (argv[1] if len(argv) > 1 else "") != "paper":
        raise SystemExit("usage: python -m bot.core paper")
    cfg = {**load_config(), "mode": "paper"}
    t = Trader(make_client(cfg), cfg)
    if not t.api.clock()["is_open"]:
        log("Market is closed; nothing to do.")
        return
    core = Core(t, cfg, paper_rehearsal=True)
    now = datetime.now(timezone.utc)
    ordered = core.rebalance(now, now.astimezone(ET).date(), halted=False)
    log(f"Paper core rehearsal: {'ordered' if ordered else 'no orders'}; {json.dumps(core.snapshot())}")


if __name__ == "__main__":
    main(sys.argv)
