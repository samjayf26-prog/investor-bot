import json
import math
from datetime import datetime, timedelta, timezone

from bot import scalper
from bot.trader import load_config

CFG = load_config()
SC = CFG["scalper"]
START = datetime(2026, 10, 8, 13, 35, tzinfo=timezone.utc)  # 09:35 ET


def test_ema_and_cross():
    assert scalper.ema([1, 1, 1], 3) == 1
    flat_then_up = [10.0] * 10 + [10.5]
    assert scalper.cross_up(flat_then_up, 3, 9)
    assert not scalper.cross_up([10.0] * 11, 3, 9)
    assert not scalper.cross_up([10.0] * 5, 3, 9)


def test_exits():
    assert scalper.scalp_exit(0.004, 1, SC) == "take profit"
    assert scalper.scalp_exit(-0.003, 1, SC) == "stop"
    assert scalper.scalp_exit(0.0, 10, SC) == "time"
    assert scalper.scalp_exit(0.001, 2, SC) is None


def test_bias(tmp_path):
    assert scalper.active_symbols(SC, "bull") == ["SPY", "QQQ", "TQQQ"]
    assert scalper.active_symbols(SC, "bear") == ["SQQQ"]
    assert scalper.active_symbols(SC, "off") == []
    p = tmp_path / "latest.json"
    p.write_text(json.dumps({"expires_at": "2026-10-08T19:30:00Z", "scalp_bias": "bear"}))
    assert scalper.read_bias(p, START) == "bear"
    p.write_text(json.dumps({"expires_at": "2026-10-08T19:30:00Z", "scalp_bias": "yolo"}))
    assert scalper.read_bias(p, START) == "neutral"
    assert scalper.read_bias(tmp_path / "missing.json", START) == "neutral"


class Clock:
    def __init__(self, t):
        self.t = t

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += timedelta(seconds=s)


class FakeAlpaca:
    """Prices oscillate so EMA crossovers happen every few minutes."""

    def __init__(self, clock):
        self.clock_, self.pos, self.orders, self.n = clock, {}, {}, 0

    def price(self, sym, t=None):
        m = ((t or self.clock_.t) - START).total_seconds() / 60
        return 100 * (1 + 0.004 * math.sin(m / 3))

    def clock(self):
        return {"is_open": True}

    def positions(self):
        out = []
        for s, p in self.pos.items():
            cur = self.price(s)
            out.append({"symbol": s, "qty": str(p["qty"]), "unrealized_plpc": str(cur / p["entry"] - 1)})
        return out

    def bars(self, sym, tf, start):
        now = self.clock_.t.replace(second=0, microsecond=0)
        return [{"t": (now - timedelta(minutes=i)).isoformat(), "c": self.price(sym, now - timedelta(minutes=i))}
                for i in range(30, 0, -1)]

    def submit_order(self, **o):
        self.n += 1
        oid = str(self.n)
        price = self.price(o["symbol"])
        qty = float(o["notional"]) / price
        self.orders[oid] = {"status": "filled", "filled_avg_price": str(price), "filled_qty": str(qty)}
        self.pos[o["symbol"]] = {"entry": price, "qty": qty}
        return {"id": oid}

    def close_position(self, sym):
        self.n += 1
        oid = str(self.n)
        p = self.pos.pop(sym)
        self.orders[oid] = {"status": "filled", "filled_avg_price": str(self.price(sym)), "filled_qty": str(p["qty"])}
        return {"id": oid}

    def order(self, oid):
        return self.orders[oid]

    def cancel_order(self, oid):
        pass


def test_session_trades_many_times_and_ends_flat(tmp_path):
    clock = Clock(START)
    api = FakeAlpaca(clock)
    s = scalper.Scalper(api, CFG, now=clock.now, sleep=clock.sleep, root=tmp_path)
    assert s.run() == "done"
    assert len(s.trips) >= 4
    assert not api.pos
    assert all(t["qty"] * t["entry"] <= SC["trade_notional"] + 0.01 for t in s.trips)
    assert clock.t <= START + timedelta(minutes=SC["minutes"] + 1)
    assert (tmp_path / "ledger" / "scalps.csv").exists()


def test_loss_cap_stops_session(tmp_path):
    clock = Clock(START)
    api = FakeAlpaca(clock)
    cfg = {**CFG, "scalper": {**SC, "daily_loss_cap": 0.0001}}
    s = scalper.Scalper(api, cfg, now=clock.now, sleep=clock.sleep, root=tmp_path)
    s.run()
    first_loss = next(i for i, t in enumerate(s.trips) if t["pnl"] < 0)
    # Open trades are closed at the end, so at most max_open extra trips follow the first loss.
    assert len(s.trips) <= first_loss + 1 + SC["max_open"]
    assert not api.pos


def test_off_bias_does_nothing(tmp_path):
    (tmp_path / "picks").mkdir()
    (tmp_path / "picks" / "latest.json").write_text(
        json.dumps({"expires_at": "2026-10-08T19:30:00Z", "scalp_bias": "off"}))
    clock = Clock(START)
    api = FakeAlpaca(clock)
    assert scalper.Scalper(api, CFG, now=clock.now, sleep=clock.sleep, root=tmp_path).run() == "bias-off"
    assert not api.orders


def test_bias_change_midsession_switches_symbols(tmp_path):
    (tmp_path / "picks").mkdir()
    picks = tmp_path / "picks" / "latest.json"
    picks.write_text(json.dumps({"expires_at": "2026-10-08T19:30:00Z", "scalp_bias": "bull"}))
    clock = Clock(START)
    api = FakeAlpaca(clock)
    s = scalper.Scalper(api, CFG, now=clock.now, sleep=clock.sleep, root=tmp_path)
    s.refresh_repo = lambda: picks.write_text(json.dumps({"expires_at": "2026-10-08T19:30:00Z", "scalp_bias": "off"}))
    s.run()
    assert all(t["symbol"] != "SQQQ" for t in s.trips)
    assert not api.pos
