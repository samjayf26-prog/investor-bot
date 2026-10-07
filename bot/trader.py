"""Daily lifecycle of the SPY intraday momentum bot.

    python -m bot.trader day       # one trading day: check, maybe enter, exit before close
    python -m bot.trader flatten   # cancel all orders and close all positions
    python -m bot.trader status    # print account and positions (setup check)

Runs from GitHub Actions. Exits non-zero on anything unexpected so GitHub emails Sam.
"""
import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import overlay, risk
from .alpaca import Alpaca

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent.parent


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
    live = cfg["mode"] == "live"
    if live and cfg.get("confirm_live") is not True:
        raise SystemExit("mode is live but confirm_live is not true; refusing to start")
    if cfg["mode"] not in ("live", "paper"):
        raise SystemExit(f"unknown mode {cfg['mode']!r}")
    return Alpaca.from_env(live)


class Trader:
    def __init__(self, api, cfg, now=lambda: datetime.now(timezone.utc), sleep=time.sleep,
                 overlay_path=ROOT / "overlay" / "latest.json", ledger_path=ROOT / "ledger" / "trades.csv"):
        self.api, self.cfg, self.now, self.sleep = api, cfg, now, sleep
        self.overlay_path, self.ledger_path = overlay_path, ledger_path
        self.symbol = cfg["trade_symbol"]

    # helpers
    def sleep_until(self, when):
        while True:
            left = (when - self.now()).total_seconds()
            if left <= 0:
                return
            self.sleep(min(left, 60))

    def flatten(self, why):
        log(f"Flattening: {why}")
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

    def position(self):
        return next((p for p in self.api.positions() if p["symbol"] == self.symbol), None)

    def peak_equity(self, equity):
        hist = self.api.portfolio_history() or {}
        vals = [v for v in (hist.get("equity") or []) if v]
        return max(vals + [equity])

    def signal_inputs(self, today, cal):
        """Previous trading day's close and the price at 10:00 ET today (SIP bars)."""
        days = [d["date"] for d in cal if d["date"] < today.isoformat()]
        if not days:
            return None, None
        prev = days[-1]
        sig = self.cfg["signal_symbol"]
        daily = self.api.bars(sig, "1Day", prev, prev)
        prev_close = daily[-1]["c"] if daily else None
        ten = datetime.combine(today, datetime.min.time(), ET).replace(hour=10)
        mins = self.api.bars(sig, "1Min", (ten - timedelta(minutes=5)).astimezone(timezone.utc).isoformat(),
                             (ten - timedelta(seconds=1)).astimezone(timezone.utc).isoformat())
        price_at_10 = mins[-1]["c"] if mins else None
        return prev_close, price_at_10

    def record(self, row):
        self.ledger_path.parent.mkdir(exist_ok=True)
        new = not self.ledger_path.exists()
        with open(self.ledger_path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)

    # the day
    def day(self):
        cfg = self.cfg
        log(f"Mode: {cfg['mode'].upper()}")
        if cfg.get("kill"):
            self.flatten("kill switch is on in config.json")
            return "killed"

        clock = self.api.clock()
        if not clock["is_open"]:
            log("Market closed today/now; nothing to do.")
            return "closed"

        now_et = self.now().astimezone(ET)
        today = now_et.date()
        cal = self.api.calendar((today - timedelta(days=10)).isoformat(), today.isoformat())
        today_cal = next((d for d in cal if d["date"] == today.isoformat()), None)
        if not today_cal or today_cal["close"][:5] != "16:00":
            log(f"Not a normal full trading day (close {today_cal and today_cal['close']}); skipping.")
            return "skip-halfday"
        close = datetime.combine(today, datetime.min.time(), ET).replace(hour=16)
        entry_at = close - timedelta(minutes=cfg["entry_minutes_before_close"])
        latest_entry = close - timedelta(minutes=cfg["latest_entry_minutes_before_close"])
        exit_at = close - timedelta(minutes=cfg["exit_minutes_before_close"])

        if now_et < entry_at - timedelta(minutes=45):
            log("Too early (this is the off-season cron run); exiting.")
            return "too-early"

        if self.api.positions():
            self.flatten("leftover position from an earlier run")

        entry_id = f"{today.isoformat()}-mom-{self.symbol}-entry"
        if self.api.order_by_client_id(entry_id):
            log("Already entered today (rerun); not trading again.")
            return "already-traded"

        acct = self.api.account()
        if acct.get("trading_blocked") or acct.get("account_blocked"):
            raise RuntimeError("Alpaca says the account is blocked from trading")
        equity, start_eq, cash = float(acct["equity"]), float(acct["last_equity"]), float(acct["cash"])
        log(f"Equity ${equity:.2f}, cash ${cash:.2f}")

        for ok, why in (risk.daily_loss_ok(equity, start_eq, cfg["daily_loss_cap_pct"]),
                        risk.drawdown_ok(equity, self.peak_equity(equity), cfg["drawdown_halt_pct"]),
                        risk.symbol_allowed(self.symbol, cfg["universe"])):
            if not ok:
                raise RuntimeError(f"Risk halt: {why}")

        mult, blocked, note = overlay.load(self.overlay_path, self.now(), cfg["no_overlay_risk_dial"], self.symbol)
        log(f"Overlay: {note}")
        if blocked:
            log(f"No trade today: {blocked}")
            return "overlay-blocked"

        prev_close, p10 = self.signal_inputs(today, cal)
        direction = risk.entry_signal(prev_close, p10, cfg["entry_threshold"], cfg["long_only"])
        log(f"Signal: prev close {prev_close}, 10:00 price {p10} -> {direction or 'no trade'}")
        if direction != "long":
            # Shorting is off: a cash account under $2k can't short and fractional shares can't be shorted.
            return "no-signal"

        notional = risk.position_notional(equity, cash, cfg["max_position_frac"], mult,
                                          cfg["max_order_notional"], cfg["min_order_notional"])
        if notional <= 0:
            log("Position size is below the broker minimum; skipping.")
            return "too-small"

        self.sleep_until(entry_at)
        if self.now() > latest_entry:
            log("Started too late to enter safely; skipping today.")
            return "too-late"

        order = self.api.submit_order(symbol=self.symbol, notional=f"{notional:.2f}", side="buy",
                                      type="market", time_in_force="day", client_order_id=entry_id)
        log(f"Bought ${notional:.2f} of {self.symbol} (order {order['id']})")
        for _ in range(12):
            order = self.api.order_by_client_id(entry_id)
            if order["status"] == "filled":
                break
            self.sleep(5)
        else:
            self.flatten(f"entry not filled (status {order['status']})")
            raise RuntimeError("entry order did not fill")
        entry_price = float(order["filled_avg_price"])
        log(f"Filled {order['filled_qty']} @ ${entry_price:.2f}")

        exit_reason = "end of day"
        while self.now() < exit_at:
            pos = self.position()
            if pos is None:
                exit_reason = "position disappeared (closed outside the bot)"
                break
            if risk.stop_hit(float(pos["unrealized_plpc"]), cfg["stop_loss_pct"]):
                exit_reason = f"stop loss ({float(pos['unrealized_plpc']):.2%})"
                break
            self.sleep(cfg["poll_seconds"])

        pos = self.position()
        exit_price = float(pos["current_price"]) if pos else None
        self.flatten(exit_reason)
        pnl = (exit_price - entry_price) * float(order["filled_qty"]) if exit_price else None
        log(f"Exit ~${exit_price}, approx P&L ${pnl:.2f}" if pnl is not None else "Exit price unknown")
        self.record({"date": today.isoformat(), "mode": cfg["mode"], "symbol": self.symbol,
                     "notional": notional, "qty": order["filled_qty"], "entry": entry_price,
                     "exit_approx": exit_price, "pnl_approx": round(pnl, 4) if pnl is not None else "",
                     "exit_reason": exit_reason, "overlay": note[:80]})
        return "traded"

    def status(self):
        acct = self.api.account()
        log(f"Mode {self.cfg['mode']}: equity ${acct['equity']}, cash ${acct['cash']}, "
            f"status {acct['status']}, blocked {acct.get('trading_blocked')}")
        log(f"Positions: {[(p['symbol'], p['qty']) for p in self.api.positions()] or 'none'}")
        log(f"Market open now: {self.api.clock()['is_open']}")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "day"
    cfg = load_config()
    t = Trader(make_client(cfg), cfg)
    if cmd == "day":
        log(f"Result: {t.day()}")
    elif cmd == "backstop":
        if cfg.get("kill") or (t.api.clock()["is_open"] and t.api.positions()):
            t.flatten("backstop: kill switch on or position left open")
        else:
            log("Backstop: nothing open.")
    elif cmd == "flatten":
        t.flatten("manual or backstop run")
    elif cmd == "status":
        t.status()
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv)
