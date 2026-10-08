"""Fast mode: trades a few very liquid ETFs on 1-minute signals, many times a day.

    python -m bot.scalper          # one scalping session (started by GitHub Actions)

Rules decide every trade (EMA crossover on 1-minute bars, small take-profit and stop,
short max hold). Claude steers it from picks/latest.json with "scalp_bias":
"bull" (long SPY/QQQ/TQQQ only), "bear" (SQQQ only), "neutral" (all) or "off".
Symbols come only from config, never from the picks file.
"""
import csv
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .trader import ET, ROOT, load_config, log, make_client

BIASES = ("bull", "bear", "neutral", "off")


# pure logic
def ema(values, n):
    k, out = 2 / (n + 1), None
    for v in values:
        out = v if out is None else v * k + out * (1 - k)
    return out


def cross_up(closes, fast, slow):
    """True when the fast EMA crossed above the slow EMA on the latest bar."""
    if len(closes) < slow + 1:
        return False
    prev, now = closes[:-1], closes
    return ema(prev, fast) <= ema(prev, slow) and ema(now, fast) > ema(now, slow)


def scalp_exit(plpc, held_minutes, sc):
    if plpc >= sc["take_profit_pct"]:
        return "take profit"
    if plpc <= -sc["stop_pct"]:
        return "stop"
    if held_minutes >= sc["max_hold_minutes"]:
        return "time"
    return None


def active_symbols(sc, bias):
    if bias == "off":
        return []
    if bias == "bull":
        return [s for s in sc["bull_symbols"] if s in sc["symbols"]]
    if bias == "bear":
        return [s for s in sc["bear_symbols"] if s in sc["symbols"]]
    return list(sc["symbols"])


def read_bias(path, now):
    """Claude's steer, if the picks file is fresh; otherwise neutral."""
    try:
        data = json.loads(Path(path).read_text())
        expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        bias = data.get("scalp_bias", "neutral")
        return bias if bias in BIASES and now < expires else "neutral"
    except (OSError, ValueError, KeyError, TypeError):
        return "neutral"


class Scalper:
    def __init__(self, api, cfg, now=lambda: datetime.now(timezone.utc), sleep=time.sleep, root=ROOT):
        self.api, self.cfg, self.sc = api, cfg, cfg["scalper"]
        self.now, self.sleep, self.root = now, sleep, root
        self.open = {}      # symbol -> {"entry": price, "qty": float, "at": datetime, "cid": str}
        self.trips = []     # closed round trips
        self.last_bar = {}  # symbol -> timestamp of the last bar acted on

    def realized(self):
        return sum(t["pnl"] for t in self.trips)

    def fill(self, order_id):
        for _ in range(10):
            o = self.api.order(order_id)
            if o["status"] == "filled":
                return float(o["filled_avg_price"]), float(o["filled_qty"])
            if o["status"] in ("canceled", "rejected", "expired"):
                return None, None
            self.sleep(1)
        self.api.cancel_order(order_id)
        return None, None

    def close(self, sym, reason):
        pos = self.open.pop(sym)
        order = self.api.close_position(sym)
        price, _ = self.fill(order["id"]) if order and order.get("id") else (None, None)
        price = price or pos["entry"]
        pnl = (price - pos["entry"]) * pos["qty"]
        self.trips.append({"date": self.now().astimezone(ET).date().isoformat(), "symbol": sym,
                           "opened": pos["at"].astimezone(ET).strftime("%H:%M:%S"),
                           "closed": self.now().astimezone(ET).strftime("%H:%M:%S"),
                           "entry": round(pos["entry"], 4), "exit": round(price, 4),
                           "qty": round(pos["qty"], 6), "pnl": round(pnl, 4), "reason": reason,
                           "mode": self.cfg["mode"]})

    def run(self):
        sc = self.sc
        if not sc.get("enabled") or self.cfg.get("kill"):
            log("Scalper disabled or kill switch on.")
            return "disabled"
        if not self.api.clock()["is_open"]:
            log("Market closed.")
            return "closed"
        now_et = self.now().astimezone(ET)
        today = now_et.date()
        start = datetime.combine(today, datetime.strptime(sc["start_et"], "%H:%M").time(), ET)
        minutes = sc["minutes"]
        if os.environ.get("SCALP_START_NOW") == "1":  # manual run from the Actions tab
            start = now_et
            minutes = int(os.environ.get("SCALP_MINUTES") or minutes)
        elif now_et > start + timedelta(minutes=25):
            log("Started too long after the window opened (off-season cron run).")
            return "too-late"
        end = min(start + timedelta(minutes=minutes),
                  datetime.combine(today, datetime.min.time(), ET).replace(hour=15, minute=55))
        if now_et < start - timedelta(minutes=30):
            log("Too early (off-season cron run).")
            return "too-early"
        if now_et >= end:
            log("Scalping window already over.")
            return "too-late"

        bias = read_bias(self.root / "picks" / "latest.json", self.now())
        symbols = active_symbols(sc, bias)
        log(f"Scalping {symbols} (Claude bias: {bias}) until {end.strftime('%H:%M')} ET, "
            f"${sc['trade_notional']} per trade, mode {self.cfg['mode']}")
        if not symbols:
            return "bias-off"
        for p in self.api.positions():
            if p["symbol"] in sc["symbols"]:
                self.api.close_position(p["symbol"])
                log(f"Closed leftover scalper position {p['symbol']}")

        self.sleep_until(start)
        n, next_refresh = 0, self.now() + timedelta(minutes=15)
        while self.now() < end:
            if self.now() >= next_refresh:  # pick up Claude's midday research refreshes
                next_refresh = self.now() + timedelta(minutes=15)
                self.refresh_repo()
                new_bias = read_bias(self.root / "picks" / "latest.json", self.now())
                if new_bias != bias:
                    bias, symbols = new_bias, active_symbols(sc, new_bias)
                    log(f"Claude bias changed to {bias}: now scalping {symbols}")
            if len(self.trips) >= sc["max_round_trips"] or self.realized() <= -sc["daily_loss_cap"]:
                log(f"Stopping: {len(self.trips)} round trips, realized ${self.realized():.2f}")
                break
            held = {p["symbol"]: p for p in self.api.positions() if p["symbol"] in self.open}
            for sym in list(self.open):
                pos = held.get(sym)
                if pos is None:
                    self.open.pop(sym)
                    continue
                minutes = (self.now() - self.open[sym]["at"]).total_seconds() / 60
                reason = scalp_exit(float(pos["unrealized_plpc"]), minutes, sc)
                if reason:
                    self.close(sym, reason)
            for sym in symbols:
                if sym in self.open or len(self.open) >= sc["max_open"]:
                    continue
                bars = self.api.bars(sym, "1Min", (self.now() - timedelta(minutes=40)).isoformat())
                if not bars or bars[-1]["t"] == self.last_bar.get(sym):
                    continue
                self.last_bar[sym] = bars[-1]["t"]
                if cross_up([b["c"] for b in bars], sc["ema_fast"], sc["ema_slow"]):
                    n += 1
                    cid = f"scalp-{today.isoformat()}-{sym}-{n}"
                    order = self.api.submit_order(symbol=sym, notional=f"{sc['trade_notional']:.2f}", side="buy",
                                                  type="market", time_in_force="day", client_order_id=cid)
                    price, qty = self.fill(order["id"])
                    if price:
                        self.open[sym] = {"entry": price, "qty": qty, "at": self.now(), "cid": cid}
            self.sleep(sc["poll_seconds"])

        for sym in list(self.open):
            self.close(sym, "end of session")
        wins = sum(1 for t in self.trips if t["pnl"] > 0)
        log(f"Session done: {len(self.trips)} round trips ({2 * len(self.trips)} orders), "
            f"{wins} winners, realized P&L ${self.realized():.2f}")
        self.save()
        return "done"

    def refresh_repo(self):
        if (self.root / ".git").exists():
            subprocess.run(["git", "-C", str(self.root), "pull", "-q", "--rebase", "origin", "main"],
                           check=False, timeout=60)

    def sleep_until(self, when):
        while (left := (when - self.now()).total_seconds()) > 0:
            self.sleep(min(left, 30))

    def save(self):
        if not self.trips:
            return
        path = self.root / "ledger" / "scalps.csv"
        path.parent.mkdir(exist_ok=True)
        new = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.trips[0]))
            if new:
                w.writeheader()
            w.writerows(self.trips)


def main():
    cfg = load_config()
    log(f"Result: {Scalper(make_client(cfg), cfg).run()}")


if __name__ == "__main__":
    main()
