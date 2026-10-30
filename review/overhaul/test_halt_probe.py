"""Probe: during a halt, when the rule wants MORE TQQQ, does the core sell SPY into cash?"""
import json, sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, "tests")   # run from a checkout of PR #2: python -m pytest -q review/overhaul/test_halt_probe.py
sys.path.insert(0, ".")
from test_bot import LIVE_CFG, FakeAlpaca, FakeClock, write_picks
from test_overhaul import closes, hold, WINDOW
from bot.trader import Trader

LEV_CFG = {**LIVE_CFG, "core": {**LIVE_CFG["core"], "leverage": True}}


def test_halt_with_dip_signal_dumps_spy(tmp_path):
    write_picks(tmp_path, [])
    qqq = closes(260, 0.002)
    qqq[-3:] = [qqq[-4] * 0.99, qqq[-4] * 0.98, qqq[-4] * 0.97]   # three lower closes -> overlay wants 100% TQQQ
    api = FakeAlpaca(cash=2.0)
    api.account = lambda: {"equity": "70", "last_equity": "100", "cash": str(api.cash), "status": "ACTIVE"}  # -30% day: halted
    hold(api, "TQQQ", 30.0)
    hold(api, "SPY", 30.0)
    api.closes = qqq[:-1]
    api.prices["QQQ"] = qqq[-1]
    clock = FakeClock(WINDOW)
    t = Trader(api, LEV_CFG, now=clock.now, sleep=clock.sleep, root=tmp_path)
    assert t.cycle() == "halted"
    print("closed:", api.closed, "orders:", {k: (v["side"], v["symbol"], v.get("notional")) for k, v in api.orders.items()}, "cash:", api.cash)
    state = json.loads((tmp_path / "state" / "core.json").read_text())
    print("state:", {k: state[k] for k in ("lev_target", "rest_target", "halted", "ordered")})
    assert "SPY" not in api.closed, "SPY was sold into cash during a halt although TQQQ cannot be bought"


def test_halt_wants_more_tqqq_partial(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    api.account = lambda: {"equity": "70", "last_equity": "100", "cash": str(api.cash), "status": "ACTIVE"}
    hold(api, "TQQQ", 10.0)
    hold(api, "SPY", 50.0)
    api.closes = closes(260, 0.002)          # calm uptrend: weight 1.0 -> wants all TQQQ
    api.prices["QQQ"] = api.closes[-1]
    clock = FakeClock(WINDOW)
    t = Trader(api, LEV_CFG, now=clock.now, sleep=clock.sleep, root=tmp_path)
    assert t.cycle() == "halted"
    print("closed:", api.closed, "orders:", {k: (v["side"], v["symbol"], v.get("notional")) for k, v in api.orders.items()}, "cash:", api.cash)
    assert "SPY" not in api.closed and not [o for o in api.orders.values() if o["side"] == "sell"]
