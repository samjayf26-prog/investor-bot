"""Executes Claude's research picks on Alpaca, with hard limits.

    python -m bot.trader cycle     # one pass: exits, then new entries from picks/latest.json
    python -m bot.trader flatten   # cancel all orders and close all positions
    python -m bot.trader status    # print account and positions (setup check)

Runs from GitHub Actions every 15 minutes in market hours and on each picks push. Exits non-zero
on anything unexpected so GitHub emails Sam.
"""
import csv
import json
import math
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import picks, risk
from .alpaca import Alpaca, AlpacaError

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent.parent
MARKET = ("SPY", "QQQ", "IWM", "SMH", "TLT", "VIXY")  # always in state/market.json
PENDING = {"new", "accepted", "pending_new", "partially_filled", "accepted_for_bidding", "held"}


def log(msg):
    stamp = datetime.now(ET).strftime("%H:%M:%S ET")
    print(f"[{stamp}] {msg}", flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"- `{stamp}` {msg}\n")


def load_config(path=ROOT / "config.json"):
    with open(path) as f:
        return json.load(f)


def scalper_mode(cfg):
    """Account the scalper trades on: its own "mode" if set, else the bot's."""
    return cfg.get("scalper", {}).get("mode", cfg["mode"])


def scalper_symbols(cfg):
    """Symbols reserved for the scalper on this account (none when it trades elsewhere)."""
    sc = cfg.get("scalper", {})
    return set(sc.get("symbols", [])) if sc.get("enabled") and scalper_mode(cfg) == cfg["mode"] else set()


def core_cfg(cfg):
    """The SPY core that parks idle cash overnight, or None when it is off (missing or null)."""
    core = cfg.get("core")
    return core if isinstance(core, dict) and core.get("symbol") else None


def make_client(cfg):
    if cfg["mode"] not in ("live", "paper"):
        raise SystemExit(f"unknown mode {cfg['mode']!r}")
    live = cfg["mode"] == "live"
    if live and cfg.get("confirm_live") is not True:
        raise SystemExit("mode is live but confirm_live is not true; refusing to start")
    return Alpaca.from_env(live)


class Trader:
    def __init__(self, api, cfg, now=lambda: datetime.now(timezone.utc), sleep=time.sleep, root=ROOT):
        self.api, self.cfg, self.now, self.sleep = api, cfg, now, sleep
        self.picks_path = root / "picks" / "latest.json"
        self.state_path = root / "state" / "positions.json"
        self.ledger_path = root / "ledger" / "trades.csv"
        self.snapshot_path = root / "state" / "account.json"
        self.market_path = root / "state" / "market.json"
        self.core_ledger_path = root / "ledger" / "core.csv"

    # persistence
    def load_state(self):
        try:
            return json.loads(self.state_path.read_text())
        except FileNotFoundError:
            return {}

    def save_state(self, state):
        self.state_path.parent.mkdir(exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    def record(self, row, path=None):
        path = path or self.ledger_path
        path.parent.mkdir(exist_ok=True)
        new = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)

    # actions
    def flatten(self, why):
        log(f"Flattening everything: {why}")
        self.api.cancel_all_orders()
        for p in self.api.positions():
            self.api.close_position(p["symbol"])
            log(f"Closed {p['qty']} {p['symbol']}")
        for _ in range(12):
            if not self.api.positions():
                log("Flat.")
                return
            self.sleep(5)
        raise RuntimeError("positions still open after flatten; close them in the Alpaca app")

    def peak_equity(self, equity):
        hist = self.api.portfolio_history() or {}
        return max([v for v in (hist.get("equity") or []) if v] + [equity])

    def close(self, entry, pos, reason, today):
        self.api.close_position(pos["symbol"])
        pl = float(pos.get("unrealized_pl") or 0)
        log(f"Sold {pos['symbol']} ({entry['id']}): {reason}, approx P&L ${pl:.2f}")
        self.record({"closed": today.isoformat(), "id": entry["id"], "symbol": pos["symbol"],
                     "action": entry["action"], "opened": entry["entry_date"],
                     "cost": pos.get("cost_basis", ""), "pnl_approx": round(pl, 2),
                     "pnl_pct": round(float(pos.get("unrealized_plpc") or 0), 4),
                     "reason": reason, "mode": self.cfg["mode"]})

    def cycle(self):
        cfg = self.cfg
        log(f"Mode: {cfg['mode'].upper()}")
        if cfg.get("kill"):
            self.flatten("kill switch is on in config.json")
            return "killed"
        if not self.api.clock()["is_open"]:
            log("Market is closed; nothing to do.")
            return "closed"

        now = self.now()
        today = now.astimezone(ET).date()
        state = self.load_state()
        entries, close_ids, notes = picks.load(self.picks_path, now, cfg)
        for n in notes:
            log(f"Picks: {n}")

        # Our unfilled entries from earlier runs are stale; the reconcile below drops them.
        # Orders and positions of the scalper (its own symbols, if it trades this account)
        # are left alone.
        scalp = scalper_symbols(cfg)
        core = core_cfg(cfg)
        core_sym = core["symbol"] if core else None
        for o in self.api.open_orders():
            if o.get("client_order_id", "").endswith("-entry") and o["symbol"] not in scalp:
                self.api.cancel_order(o["id"])
        # The SPY core is not a pick: it is never reconciled, adopted, closed by Claude or counted
        # as an open position. Only flatten (kill switch) and pick funding sell it.
        positions = {p["symbol"]: p for p in self.api.positions()
                     if p["symbol"] not in scalp and p["symbol"] != core_sym}

        # reconcile our records with the broker, which is the source of truth
        for pid, e in list(state.items()):
            if e["broker_symbol"] in positions:
                continue
            order = self.api.order_by_client_id(f"{pid}-entry")
            status = order["status"] if order else "missing"
            if status in PENDING:
                continue
            if float((order or {}).get("filled_qty") or 0) == 0:
                log(f"Entry for {pid} never filled ({status}); dropping it.")
            else:
                log(f"{pid} is no longer held (closed outside the bot).")
                self.record({"closed": today.isoformat(), "id": pid, "symbol": e["broker_symbol"],
                             "action": e["action"], "opened": e["entry_date"], "cost": "",
                             "pnl_approx": "", "pnl_pct": "", "reason": "closed outside the bot",
                             "mode": cfg["mode"]})
            del state[pid]
        known = {e["broker_symbol"] for e in state.values()}
        for sym, p in positions.items():
            if sym not in known:
                lost = self.lost_pick(sym, entries)
                if lost:   # bought by a run whose state save failed (10-26 TSLA)
                    log(f"Restoring pick {lost['id']} for {sym} (its state was not saved).")
                    state[lost["id"]] = lost
                    continue
                log(f"Adopting unknown position {sym} with default exits.")
                state[f"adopted-{today.isoformat()}-{sym}"] = {
                    "id": f"adopted-{sym}", "broker_symbol": sym, "action": "buy", "entry_date": today.isoformat(),
                    "stop_pct": 0.10, "target_pct": 0.20, "max_hold_days": 5, "expiry": None}

        # exits
        cutoff = datetime.combine(today, datetime.strptime(cfg["no_entries_after_et"], "%H:%M").time(), ET)
        for pid, e in list(state.items()):
            pos = positions.get(e["broker_symbol"])
            if not pos:
                continue
            dte = (date.fromisoformat(e["expiry"]) - today).days if e.get("expiry") else None
            reason = risk.exit_reason(float(pos["unrealized_plpc"]), e["stop_pct"], e["target_pct"],
                                      (today - date.fromisoformat(e["entry_date"])).days,
                                      e["max_hold_days"], pid in close_ids, dte,
                                      late_in_day=now >= cutoff)
            if reason:
                self.close(e, pos, reason, today)
                del state[pid]
                positions.pop(e["broker_symbol"])

        # entries
        result = "managed"
        acct = self.api.account()
        if acct.get("trading_blocked") or acct.get("account_blocked"):
            self.save_state(state)
            raise RuntimeError("Alpaca says the account is blocked from trading")
        equity, cash = float(acct["equity"]), float(acct["cash"])
        halts = [why for ok, why in (risk.daily_loss_ok(equity, float(acct["last_equity"]), cfg["daily_loss_cap_pct"]),
                                     risk.drawdown_ok(equity, self.peak_equity(equity), cfg["drawdown_halt_pct"])) if not ok]
        if halts:
            log(f"No new entries: {'; '.join(halts)}")
            entries, result = [], "halted"
        elif now > cutoff:
            entries = []
        for pick in entries:
            if len(state) >= cfg["max_open_positions"]:
                log("At the open-position limit; remaining picks wait.")
                break
            if pick["id"] in state or self.api.order_by_client_id(f"{pick['id']}-entry"):
                continue
            if pick["symbol"] in scalp:
                log(f"Skip {pick['id']}: {pick['symbol']} is reserved for the scalper.")
                continue
            if pick["symbol"] == core_sym:
                log(f"Skip {pick['id']}: {core_sym} is reserved for the overnight core.")
                continue
            held = sum(abs(float(p.get("market_value") or 0)) for p in self.api.positions()
                       if p["symbol"] not in scalp and p["symbol"] != core_sym)
            # Live picks size off real equity so gains compound (Sam's call, 2026-10-13);
            # the cap only makes the big paper account trade like the small live one.
            cap = cfg["sizing_equity_cap"] if cfg["mode"] == "paper" else float("inf")
            # Cash parked in the core counts as available: it is sold only when a pick needs it.
            size_eq, size_cash = risk.sizing_view(equity, cash + self.core_value(core_sym), held, cap)
            budget = risk.pick_budget(size_eq, size_cash, pick["conviction"], cfg["max_order_notional"],
                                      cfg["min_order_notional"])
            if budget <= 0:
                log(f"Skip {pick['id']}: not enough cash.")
                continue
            fund = (lambda b: self.fund(b, core_sym)) if core_sym else None
            try:
                entry = self.enter(pick, budget, acct, today, fund=fund)
            except AlpacaError as e:  # one refused order must not lose the picks already bought
                log(f"Skip {pick['id']}: Alpaca refused it: {e}")
                continue
            if entry:
                state[pick["id"]] = entry
                self.save_state(state)
                result = "traded"
                acct = self.api.account()
                cash = float(acct["cash"])

        if core and not halts:
            try:
                if self.buy_core(core, now, today):
                    acct = self.api.account()
            except AlpacaError as e:  # the core is optional; it must never break a trade run
                log(f"Core buy skipped: Alpaca refused it: {e}")

        self.save_state(state)
        self.snapshot_path.write_text(json.dumps({
            "as_of": now.isoformat(), "mode": cfg["mode"], "equity": acct["equity"], "cash": acct["cash"],
            "core": {"symbol": core_sym, "value": round(self.core_value(core_sym), 2)} if core else None,
            "positions": [{k: p.get(k) for k in ("symbol", "qty", "avg_entry_price", "current_price",
                                                  "unrealized_pl", "unrealized_plpc")}
                          for p in self.api.positions()]}, indent=2) + "\n")
        self.write_market(now, state, entries)
        log(f"Equity ${float(acct['equity']):.2f}, cash ${float(acct['cash']):.2f}, open positions {len(state)}")
        return result

    # overnight core: idle cash sits in SPY from the afternoon until a pick needs it
    def core_value(self, sym):
        if not sym:
            return 0.0
        return sum(abs(float(p.get("market_value") or 0)) for p in self.api.positions() if p["symbol"] == sym)

    def buy_core(self, core, now, today):
        """After buy_after_et, put cash above the reserve into the core. Returns True if it ordered."""
        after = datetime.combine(today, datetime.strptime(core["buy_after_et"], "%H:%M").time(), ET)
        if now < after:
            return False
        sym = core["symbol"]
        if any(o["symbol"] == sym for o in self.api.open_orders()):
            return False   # an earlier core order is still working
        acct = self.api.account()
        avail = min(float(acct["cash"]), float(acct.get("buying_power") or acct["cash"]))
        amount = math.floor((avail - float(core.get("reserve", 2.0))) * 100) / 100
        if amount < self.cfg["min_order_notional"]:
            return False
        price = self.api.last_price(sym)
        limit = risk.entry_limit(price)
        cid = f"core-{now.astimezone(ET):%Y%m%d-%H%M}"
        try:
            self.api.submit_order(symbol=sym, side="buy", type="limit", notional=f"{amount:.2f}",
                                  limit_price=f"{limit:.2f}", time_in_force="day", client_order_id=cid)
        except AlpacaError as e:
            if e.status != 422:
                raise
            self.api.submit_order(symbol=sym, side="buy", type="market", notional=f"{amount:.2f}",
                                  time_in_force="day", client_order_id=cid)
        log(f"Core: bought ${amount:.2f} of {sym} (limit ${limit:.2f}) to hold idle cash overnight.")
        self.record({"time": now.isoformat(), "side": "buy", "symbol": sym, "notional": f"{amount:.2f}",
                     "price": price, "reason": "idle cash", "mode": self.cfg["mode"]}, self.core_ledger_path)
        return True

    def fund(self, budget, sym):
        """Called by enter() just before a pick's order: sells enough core to cover `budget`.
        Returns the budget the cash now covers (lower if the sale fell short)."""
        cash = float(self.api.account()["cash"])
        need = budget / 0.98 - cash   # pick_budget keeps 2% of cash back
        held = self.core_value(sym)
        if need <= 0 or held <= 0:
            return min(budget, math.floor(cash * 0.98 * 100) / 100)
        amount = min(held, math.ceil(need * 1.01 * 100) / 100)   # 1% slack for the market sale
        if amount >= held - 0.01:
            self.api.close_position(sym)
            amount = held
        else:
            self.api.submit_order(symbol=sym, side="sell", type="market", notional=f"{amount:.2f}",
                                  time_in_force="day",
                                  client_order_id=f"core-sell-{self.now().astimezone(ET):%Y%m%d-%H%M%S}")
        log(f"Core: sold ${amount:.2f} of {sym} to fund a pick.")
        self.record({"time": self.now().isoformat(), "side": "sell", "symbol": sym, "notional": f"{amount:.2f}",
                     "price": "", "reason": "fund pick", "mode": self.cfg["mode"]}, self.core_ledger_path)
        for _ in range(12):   # wait for the sale to land in cash
            cash = float(self.api.account()["cash"])
            if cash * 0.98 >= budget - 0.01:
                break
            self.sleep(2)
        return min(budget, math.floor(cash * 0.98 * 100) / 100)

    def write_market(self, now, state, entries):
        """state/market.json: live prices for the research runs, which trust it over index levels
        quoted in headlines. Purely informational: a failure never stops a trade run."""
        syms = list(MARKET)
        for s in [e["broker_symbol"] for e in state.values()] + [p["symbol"] for p in entries] \
                + picks.watch_symbols(self.picks_path):
            if picks.SYMBOL.match(s) and s not in syms:   # skips option contract symbols
                syms.append(s)
        try:
            snaps = self.api.snapshots(syms)
        except Exception as e:  # noqa: BLE001 - market data must never break trading
            log(f"Market snapshot skipped: {e}")
            return
        rows = {s: risk.market_row(snaps.get(s)) for s in syms}
        self.market_path.write_text(json.dumps({
            "as_of": now.isoformat(), "as_of_et": now.astimezone(ET).strftime("%Y-%m-%d %H:%M ET"),
            "note": "IEX feed. pct vs previous close and vs today's open; vwap_side = last vs today's VWAP.",
            "symbols": {s: r for s, r in rows.items() if r}}, indent=2) + "\n")

    def enter(self, pick, budget, acct, today, fund=None):
        sym, cid = pick["symbol"], f"{pick['id']}-entry"
        asset = self.api.asset(sym)
        if not asset or not asset.get("tradable") or asset.get("status") != "active" \
                or asset.get("class") != "us_equity" or asset.get("exchange") == "OTC":
            log(f"Skip {pick['id']}: {sym} is not a tradable listed US stock on Alpaca.")
            return None
        price = self.api.last_price(sym)
        base = {"id": pick["id"], "action": pick["action"], "entry_date": today.isoformat(),
                "stop_pct": pick["stop_pct"], "target_pct": pick["target_pct"],
                "max_hold_days": pick["max_hold_days"], "expiry": None}

        if pick["action"] == "buy":
            if price < self.cfg["min_stock_price"]:
                log(f"Skip {pick['id']}: {sym} at ${price} is below the minimum price.")
                return None
            if pick["max_entry_price"] and price > pick["max_entry_price"]:
                log(f"Skip {pick['id']}: {sym} at ${price} is above Claude's max entry ${pick['max_entry_price']}.")
                return None
            if pick.get("confirm_vwap") and not self.vwap_ok(sym, price, bullish=True):
                return None
            if fund:   # sell core only now, once the pick is really about to be bought
                budget = fund(budget)
                if budget < self.cfg["min_order_notional"]:
                    log(f"Skip {pick['id']}: not enough cash after selling the core.")
                    return None
            # A limit order lets the broker enforce the cap: never pay above Claude's max entry
            # price, or more than 1% over the last trade when there is none.
            limit = risk.entry_limit(price, pick["max_entry_price"])
            if asset.get("fractionable"):
                order = dict(notional=f"{budget:.2f}")
            else:
                qty = risk.whole_shares(budget, limit)
                if qty < 1:
                    log(f"Skip {pick['id']}: one share of {sym} (${price}) costs more than ${budget}.")
                    return None
                order = dict(qty=str(qty))
            try:
                self.api.submit_order(symbol=sym, side="buy", type="limit", limit_price=f"{limit:.2f}",
                                      time_in_force="day", client_order_id=cid, **order)
            except AlpacaError as e:
                if e.status != 422:
                    raise
                # Alpaca's docs disagree on limit orders for fractional amounts; if it is refused,
                # fall back to market (the max-entry check above already passed).
                log(f"Limit order for {sym} refused ({e}); sending a market order.")
                self.api.submit_order(symbol=sym, side="buy", type="market", time_in_force="day",
                                      client_order_id=cid, **order)
            log(f"Bought {sym} ({order}, limit ${limit:.2f}) for pick {pick['id']}")
            return {**base, "broker_symbol": sym}

        # buy_put: the bearish trade available to a small cash account (shorting needs $2k+)
        if not self.cfg["options_enabled"] or int(acct.get("options_trading_level") or 0) < 2:
            log(f"Skip {pick['id']}: account is not approved to buy options (level 2).")
            return None
        if pick.get("confirm_vwap") and not self.vwap_ok(sym, price, bullish=False):
            return None
        contracts = self.api.put_contracts(sym, (today + timedelta(days=10)).isoformat(),
                                           (today + timedelta(days=45)).isoformat())
        contracts = sorted(contracts, key=lambda c: abs(float(c["strike_price"]) - price))[:100]
        if not contracts:
            log(f"Skip {pick['id']}: no listed puts on {sym}.")
            return None
        contract, ask = risk.choose_put(contracts, self.api.option_quotes([c["symbol"] for c in contracts]),
                                        price, budget, today)
        if not contract:
            log(f"Skip {pick['id']}: no liquid put on {sym} fits ${budget:.2f}.")
            return None
        if fund and fund(ask * 100) < ask * 100 - 0.01:
            log(f"Skip {pick['id']}: not enough cash for the put after selling the core.")
            return None
        self.api.submit_order(symbol=contract["symbol"], qty="1", side="buy", type="limit",
                              limit_price=f"{ask:.2f}", time_in_force="day", client_order_id=cid)
        log(f"Bought 1 put {contract['symbol']} at ${ask:.2f} (${ask * 100:.0f}) for pick {pick['id']}")
        return {**base, "broker_symbol": contract["symbol"], "expiry": contract["expiration_date"]}

    def lost_pick(self, sym, entries):
        """A position whose entry order belongs to one of today's buy picks: rebuild that
        pick's record (exits as Claude set them) instead of adopting it with defaults."""
        for pick in entries:
            if pick["action"] != "buy" or pick["symbol"] != sym:
                continue
            order = self.api.order_by_client_id(f"{pick['id']}-entry")
            if order and float(order.get("filled_qty") or 0) > 0:
                opened = (order.get("filled_at") or order.get("submitted_at") or "")[:10]
                return {"id": pick["id"], "broker_symbol": sym, "action": "buy",
                        "entry_date": opened or self.now().astimezone(ET).date().isoformat(),
                        "stop_pct": pick["stop_pct"], "target_pct": pick["target_pct"],
                        "max_hold_days": pick["max_hold_days"], "expiry": None}
        return None

    def vwap_ok(self, sym, price, bullish):
        """Claude asked to enter only on confirmation. No order is sent while waiting, so the
        pick is retried on every run until the entry cutoff."""
        try:
            vwap = float((((self.api.snapshots([sym]) or {}).get(sym) or {}).get("dailyBar") or {}).get("vw") or 0)
        except (AlpacaError, OSError, TypeError, ValueError):  # no data = no confirmation, retry later
            vwap = 0.0
        if risk.vwap_confirms(price, vwap, bullish):
            return True
        side = "above" if bullish else "below"
        log(f"Waiting on {sym}: ${price} is not {side} today's VWAP (${vwap:.2f}); will retry next run.")
        return False

    def status(self):
        acct = self.api.account()
        log(f"Mode {self.cfg['mode']}: equity ${acct['equity']}, cash ${acct['cash']}, status {acct['status']}, "
            f"options level {acct.get('options_trading_level')}, blocked {acct.get('trading_blocked')}")
        log(f"Positions: {[(p['symbol'], p['qty']) for p in self.api.positions()] or 'none'}")
        log(f"Market open now: {self.api.clock()['is_open']}")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "cycle"
    cfg = load_config()
    t = Trader(make_client(cfg), cfg)
    if cmd == "cycle":
        log(f"Result: {t.cycle()}")
    elif cmd == "flatten":
        t.flatten("manual run")
    elif cmd == "status":
        t.status()
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv)
