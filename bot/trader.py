"""Executes Claude's research picks on Alpaca, with hard limits.

    python -m bot.trader cycle     # one pass: exits, then new entries from picks/latest.json
    python -m bot.trader flatten   # cancel all orders and close all positions
    python -m bot.trader status    # print account and positions (setup check)

Runs from GitHub Actions about once an hour while the market is open. Exits non-zero
on anything unexpected so GitHub emails Sam.
"""
import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import picks, risk
from .alpaca import Alpaca

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent.parent
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

    # persistence
    def load_state(self):
        try:
            return json.loads(self.state_path.read_text())
        except FileNotFoundError:
            return {}

    def save_state(self, state):
        self.state_path.parent.mkdir(exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    def record(self, row):
        self.ledger_path.parent.mkdir(exist_ok=True)
        new = not self.ledger_path.exists()
        with open(self.ledger_path, "a", newline="") as f:
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

        # Unfilled orders from earlier runs are stale; the reconcile below drops them.
        self.api.cancel_all_orders()
        positions = {p["symbol"]: p for p in self.api.positions()}

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
                log(f"Adopting unknown position {sym} with default exits.")
                state[f"adopted-{today.isoformat()}-{sym}"] = {
                    "id": f"adopted-{sym}", "broker_symbol": sym, "action": "buy", "entry_date": today.isoformat(),
                    "stop_pct": 0.10, "target_pct": 0.20, "max_hold_days": 5, "expiry": None}

        # exits
        for pid, e in list(state.items()):
            pos = positions.get(e["broker_symbol"])
            if not pos:
                continue
            dte = (date.fromisoformat(e["expiry"]) - today).days if e.get("expiry") else None
            reason = risk.exit_reason(float(pos["unrealized_plpc"]), e["stop_pct"], e["target_pct"],
                                      (today - date.fromisoformat(e["entry_date"])).days,
                                      e["max_hold_days"], pid in close_ids, dte)
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
        cutoff = datetime.combine(today, datetime.strptime(cfg["no_entries_after_et"], "%H:%M").time(), ET)
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
            held = sum(abs(float(p.get("market_value") or 0)) for p in self.api.positions())
            size_eq, size_cash = risk.sizing_view(equity, cash, held, cfg["sizing_equity_cap"])
            budget = risk.pick_budget(size_eq, size_cash, pick["conviction"], cfg["max_order_notional"],
                                      cfg["min_order_notional"])
            if budget <= 0:
                log(f"Skip {pick['id']}: not enough cash.")
                continue
            entry = self.enter(pick, budget, acct, today)
            if entry:
                state[pick["id"]] = entry
                result = "traded"
                acct = self.api.account()
                cash = float(acct["cash"])

        self.save_state(state)
        self.snapshot_path.write_text(json.dumps({
            "as_of": now.isoformat(), "mode": cfg["mode"], "equity": acct["equity"], "cash": acct["cash"],
            "positions": [{k: p.get(k) for k in ("symbol", "qty", "avg_entry_price", "current_price",
                                                  "unrealized_pl", "unrealized_plpc")}
                          for p in self.api.positions()]}, indent=2) + "\n")
        log(f"Equity ${float(acct['equity']):.2f}, cash ${float(acct['cash']):.2f}, open positions {len(state)}")
        return result

    def enter(self, pick, budget, acct, today):
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
            if asset.get("fractionable"):
                order = dict(notional=f"{budget:.2f}")
            else:
                qty = risk.whole_shares(budget, price)
                if qty < 1:
                    log(f"Skip {pick['id']}: one share of {sym} (${price}) costs more than ${budget}.")
                    return None
                order = dict(qty=str(qty))
            self.api.submit_order(symbol=sym, side="buy", type="market", time_in_force="day",
                                  client_order_id=cid, **order)
            log(f"Bought {sym} ({order}) for pick {pick['id']}")
            return {**base, "broker_symbol": sym}

        # buy_put: the bearish trade available to a small cash account (shorting needs $2k+)
        if not self.cfg["options_enabled"] or int(acct.get("options_trading_level") or 0) < 2:
            log(f"Skip {pick['id']}: account is not approved to buy options (level 2).")
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
        self.api.submit_order(symbol=contract["symbol"], qty="1", side="buy", type="limit",
                              limit_price=f"{ask:.2f}", time_in_force="day", client_order_id=cid)
        log(f"Bought 1 put {contract['symbol']} at ${ask:.2f} (${ask * 100:.0f}) for pick {pick['id']}")
        return {**base, "broker_symbol": contract["symbol"], "expiry": contract["expiration_date"]}

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
