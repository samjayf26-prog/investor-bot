import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from bot import overlay, risk
from bot.trader import Trader, load_config

ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 8, 19, 10, tzinfo=timezone.utc)  # 15:10 ET, a Thursday


# risk
def test_daily_loss_cap():
    assert risk.daily_loss_ok(99, 100, 0.02)[0]
    assert not risk.daily_loss_ok(98, 100, 0.02)[0]


def test_drawdown_halt():
    assert risk.drawdown_ok(91, 100, 0.10)[0]
    assert not risk.drawdown_ok(90, 100, 0.10)[0]


def test_universe():
    assert not risk.symbol_allowed("TSLA", ["SPY"])[0]


def test_sizing_never_exceeds_limits():
    assert risk.position_notional(100, 100, 0.5, 1.0, 500, 1) == 50.0
    assert risk.position_notional(100, 100, 0.5, 0.5, 500, 1) == 25.0
    assert risk.position_notional(100, 100, 0.5, 7.0, 500, 1) == 50.0   # multiplier clamped
    assert risk.position_notional(100, 10, 0.5, 1.0, 500, 1) == 9.8     # no leverage
    assert risk.position_notional(10_000, 10_000, 0.5, 1.0, 500, 1) == 500  # hard ceiling
    assert risk.position_notional(100, 100, 0.5, 0.0, 500, 1) == 0.0


def test_signal():
    assert risk.entry_signal(100, 101, 0, True) == "long"
    assert risk.entry_signal(100, 99, 0, True) is None
    assert risk.entry_signal(100, 99, 0, False) == "short"
    assert risk.entry_signal(None, 99, 0, True) is None


def test_unknown_dial_is_off():
    assert risk.dial_multiplier("YOLO") == 0.0


# overlay
def write_overlay(tmp_path, **kw):
    data = {"schema_version": 1, "run_type": "premarket", "generated_at": "2026-10-08T12:45:00Z",
            "expires_at": "2026-10-08T20:00:00Z", "risk_dial": "normal", "avoid": []}
    data.update(kw)
    p = tmp_path / "latest.json"
    p.write_text(json.dumps(data))
    return p


def test_overlay_missing_uses_default(tmp_path):
    assert overlay.load(tmp_path / "nope.json", NOW, "normal", "SPY")[:2] == (1.0, None)


def test_overlay_reduces(tmp_path):
    assert overlay.load(write_overlay(tmp_path, risk_dial="reduced"), NOW, "normal", "SPY")[0] == 0.5


def test_overlay_cannot_increase(tmp_path):
    assert overlay.load(write_overlay(tmp_path), NOW, "reduced", "SPY")[0] == 0.5


def test_overlay_avoid_blocks(tmp_path):
    p = write_overlay(tmp_path, avoid=[{"symbol": "*", "reason": "FOMC", "until": "2026-10-08T21:00:00Z"}])
    assert overlay.load(p, NOW, "normal", "SPY")[1] == "overlay avoid: FOMC"


def test_overlay_expired_or_bad_is_ignored(tmp_path):
    assert overlay.load(write_overlay(tmp_path, expires_at="2026-10-08T15:00:00Z", risk_dial="off"),
                        NOW, "normal", "SPY")[0] == 1.0
    assert overlay.load(write_overlay(tmp_path, risk_dial="max"), NOW, "normal", "SPY")[0] == 1.0
    assert overlay.load(write_overlay(tmp_path, generated_at="2026-10-09T12:00:00Z"), NOW, "normal", "SPY")[0] == 1.0
    (tmp_path / "latest.json").write_text("{garbage")
    assert overlay.load(tmp_path / "latest.json", NOW, "normal", "SPY")[0] == 1.0


# simulated day against a fake broker
class FakeClock:
    def __init__(self, t):
        self.t = t

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += timedelta(seconds=s)


class FakeAlpaca:
    def __init__(self, clock, prev_close=600.0, p10=603.0, drop_after=None):
        self.clock_, self.prev_close, self.p10, self.drop_after = clock, prev_close, p10, drop_after
        self.orders, self.pos, self.closed = {}, None, []

    def clock(self):
        return {"is_open": True}

    def calendar(self, start, end):
        return [{"date": "2026-10-07", "close": "16:00"}, {"date": "2026-10-08", "close": "16:00"}]

    def account(self):
        return {"equity": "100", "last_equity": "100", "cash": "100", "status": "ACTIVE"}

    def portfolio_history(self):
        return {"equity": [100, 100]}

    def bars(self, symbol, tf, start, end):
        return [{"c": self.prev_close}] if tf == "1Day" else [{"c": self.p10}]

    def positions(self):
        if self.pos is None:
            return []
        plpc = -0.02 if self.drop_after and self.clock_.t >= self.drop_after else 0.001
        return [{**self.pos, "unrealized_plpc": str(plpc), "current_price": "605"}]

    def order_by_client_id(self, cid):
        return self.orders.get(cid)

    def submit_order(self, **o):
        assert o["symbol"] == "SPY" and o["side"] == "buy"
        self.entry_time = self.clock_.t
        o.update(id="1", status="filled", filled_avg_price="604", filled_qty=str(float(o["notional"]) / 604))
        self.orders[o["client_order_id"]] = o
        self.pos = {"symbol": "SPY", "qty": o["filled_qty"]}
        return o

    def cancel_all_orders(self):
        pass

    def close_position(self, sym):
        self.closed.append(self.clock_.t)
        self.pos = None


def make(tmp_path, start=NOW, **kw):
    clock = FakeClock(start)
    api = FakeAlpaca(clock, **kw)
    t = Trader(api, load_config(), now=clock.now, sleep=clock.sleep,
               overlay_path=tmp_path / "none.json", ledger_path=tmp_path / "trades.csv")
    return t, api, clock


def et(h, m):
    return datetime(2026, 10, 8, h, m, tzinfo=ET)


def test_day_enters_at_1530_and_exits_at_1550(tmp_path):
    t, api, clock = make(tmp_path)
    assert t.day() == "traded"
    assert api.entry_time.astimezone(ET).strftime("%H:%M") == "15:30"
    assert api.closed[0].astimezone(ET).strftime("%H:%M") == "15:50"
    assert float(api.orders["2026-10-08-mom-SPY-entry"]["notional"]) == 50.0
    assert "end of day" in (tmp_path / "trades.csv").read_text()


def test_day_stop_loss(tmp_path):
    t, api, _ = make(tmp_path, drop_after=et(15, 35))
    assert t.day() == "traded"
    assert api.closed[0] < et(15, 36)
    assert "stop loss" in (tmp_path / "trades.csv").read_text()


def test_day_no_trade_on_down_morning(tmp_path):
    t, api, _ = make(tmp_path, p10=597.0)
    assert t.day() == "no-signal" and not api.orders


def test_rerun_does_not_double_trade(tmp_path):
    t, api, _ = make(tmp_path)
    t.day()
    assert t.day() == "already-traded" and len(api.orders) == 1


def test_late_start_skips(tmp_path):
    t, api, _ = make(tmp_path, start=et(15, 45))
    assert t.day() == "too-late" and not api.orders


def test_offseason_cron_exits(tmp_path):
    t, api, _ = make(tmp_path, start=et(14, 7))
    assert t.day() == "too-early"


def test_live_requires_confirmation():
    from bot.trader import make_client
    with pytest.raises(SystemExit):
        make_client({"mode": "live", "confirm_live": False})
