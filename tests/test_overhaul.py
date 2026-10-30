"""The profit overhaul (review/profit-overhaul.md): the leveraged core and the new pick rules."""
import json
import statistics
from datetime import datetime, timedelta, timezone

import pytest

from bot import picks, risk
from bot.core import Core
from bot.trader import Trader

from test_bot import LIVE_CFG, NOW, FakeAlpaca, FakeClock, write_picks

WINDOW = datetime(2026, 10, 8, 19, 40, tzinfo=timezone.utc)      # 15:40 ET, inside 15:35-15:58
LATE = datetime(2026, 10, 8, 20, 0, tzinfo=timezone.utc)         # 16:00 ET, past the window
LEV_CFG = {**LIVE_CFG, "core": {**LIVE_CFG["core"], "leverage": True}}


def closes(n=260, drift=0.001, start=100.0):
    """n daily closes climbing steadily: above the 200-day average, with low volatility."""
    out, px = [], start
    for i in range(n):
        px *= 1 + drift * (1 if i % 2 else 0.5)
        out.append(px)
    return out


def falling(n=260, start=200.0):
    """A downtrend without three lower closes in a row (so the dip overlay stays off)."""
    out, px = [], start
    for i in range(n):
        px *= 0.985 if i % 2 else 1.005
        out.append(px)
    return out


# signals
def test_sma_trend():
    assert risk.sma_trend(closes(), 200) == 1
    assert risk.sma_trend(list(reversed(closes())), 200) == 0
    assert risk.sma_trend(closes(150), 200) == 0          # too little history: no leverage
    flat = [100.0] * 200
    assert risk.sma_trend(flat, 200) == 0                 # equal to the average is not above it


def test_realized_vol_matches_sample_stdev():
    c = [100, 101, 99, 102, 103, 101, 104, 103, 105, 106, 104, 107, 108, 106, 109, 110, 108, 111, 112, 110, 113]
    rets = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
    assert risk.realized_vol(c, 20) == pytest.approx(statistics.stdev(rets) * 252 ** 0.5)
    assert risk.realized_vol(c[:20], 20) is None


def test_core_weight():
    assert risk.core_weight(1, 0.20) == pytest.approx(0.5)      # 0.30 / (3 x 20%)
    assert risk.core_weight(1, 0.05) == 1.0                      # capped at all-in
    assert risk.core_weight(0, 0.05) == 0.0                      # below the trend: none
    assert risk.core_weight(1, None) == 0.0
    assert risk.core_weight(1, 0.40, target=0.40, lev=3.0) == pytest.approx(1 / 3)


def test_dip_state_follows_the_backtest_rule():
    # three lower closes in a row enter; the first higher close exits; five sessions at most
    assert risk.dip_state([10, 9, 8, 7], 0) == 1
    assert risk.dip_state([10, 9, 8], 0) == 0                    # only two down days
    assert risk.dip_state([10, 9, 8, 7, 6], 1) == 2
    assert risk.dip_state([10, 9, 8, 7, 6, 7], 2) == 0           # up close: out
    assert risk.dip_state([10, 9, 8, 7, 6, 5, 4, 3], 5) == 0     # fifth session: out regardless
    assert risk.dip_state([10, 9, 8, 7, 6, 5, 4, 3], 4) == 5
    assert risk.dip_state([1, 2, 1], 0, down_days=1) == 1


def test_rebalance_band():
    assert not risk.rebalance_needed(0.50, 0.58)
    assert risk.rebalance_needed(0.50, 0.61)
    assert risk.rebalance_needed(0.0, 0.05)                      # switching the 3x sleeve on
    assert risk.rebalance_needed(0.05, 0.0)                      # or off
    assert not risk.rebalance_needed(0.0, 0.0)


def test_core_target():
    assert risk.core_target(60, 0.5, False) == (30.0, 30.0)
    assert risk.core_target(60, 0.5, True) == (60.0, 0.0)        # overlay: all in the 3x fund
    assert risk.core_target(-3, 0.5, False) == (0.0, 0.0)


def test_simulate_core_tracks_the_rest_fund_when_the_trend_is_off():
    n = 260
    idx = falling(n)                                             # below its average, no dip signal
    lev = [100 * 1.01 ** i for i in range(n)]
    rest = [100 * 1.001 ** i for i in range(n)]
    values = risk.simulate_core(idx, lev, rest, 75.0, start_at=250)
    assert len(values) == n - 250
    assert values[-1] == pytest.approx(75.0 * rest[-1] / rest[249])


def test_simulate_core_levers_up_in_a_calm_uptrend():
    n = 260
    idx = closes(n)                                              # calm climb: vol ~1%, weight 1.0
    lev = [100 * 1.002 ** i for i in range(n)]
    rest = [100 * 1.0005 ** i for i in range(n)]
    values = risk.simulate_core(idx, lev, rest, 75.0, start_at=250)
    assert values[-1] == pytest.approx(75.0 * lev[-1] / lev[249])


def test_exit_reason_without_a_target_only_times_out():
    assert risk.exit_reason(0.40, 0.15, None, 3, 28, False) is None
    assert risk.exit_reason(0.40, 0.15, None, 28, 28, False) == "max hold of 28 days"
    assert risk.exit_reason(-0.16, 0.15, None, 3, 28, False).startswith("stop loss")


# picks: the new defaults
def test_pick_defaults_hold_the_drift(tmp_path):
    p = write_picks(tmp_path, [{"id": "a", "symbol": "NVDA", "action": "buy"},
                               {"id": "b", "symbol": "AMD", "action": "buy", "stop_pct": 0.05, "target_pct": 0.3,
                                "max_hold_days": 0, "earliest_et": "11:15"},
                               {"id": "c", "symbol": "MU", "action": "buy", "max_hold_days": 99, "earliest_et": "bogus"}])
    entries, _, notes = picks.load(p, NOW, LIVE_CFG)
    a, b, c = entries
    assert a["stop_pct"] == 0.15 and a["target_pct"] is None and a["max_hold_days"] == 28 and a["earliest_et"] == "10:00"
    assert b["stop_pct"] == 0.10 and b["target_pct"] == 0.3 and b["max_hold_days"] == 3 and b["earliest_et"] == "11:15"
    assert c["max_hold_days"] == 30 and c["earliest_et"] == "10:00"
    assert notes == []


def test_bearish_picks_are_refused(tmp_path):
    p = write_picks(tmp_path, [{"id": "s", "symbol": "SQQQ", "action": "buy"},
                               {"id": "put", "symbol": "F", "action": "buy_put"},
                               {"id": "ok", "symbol": "TQQQ", "action": "buy"}])
    entries, _, notes = picks.load(p, NOW, LIVE_CFG)
    assert [e["id"] for e in entries] == ["ok"]
    assert len(notes) == 2 and "inverse/bear ETF" in notes[0] and "options are off" in notes[1]
    blocked = {**LIVE_CFG, "blocked_symbols": ["tqqq"]}
    assert picks.load(p, NOW, blocked)[0] == []


def test_no_entry_before_earliest_et(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "earliest_et": "11:00"}])
    clock = FakeClock(NOW)                                        # 10:50 ET
    api = FakeAlpaca()
    t = Trader(api, LIVE_CFG, now=clock.now, sleep=clock.sleep, root=tmp_path)
    t.cycle()
    assert "p1-entry" not in api.orders
    clock.t += timedelta(minutes=15)
    t.cycle()
    assert "p1-entry" in api.orders


# the leveraged core
def make(tmp_path, cfg=LEV_CFG, start=WINDOW, api=None, qqq=None):
    api = api or FakeAlpaca()
    api.closes = closes(260, 0.002) if qqq is None else qqq        # 20-day vol ~ 1.1% -> weight 1.0
    api.prices["QQQ"] = api.closes[-1]                             # today's last trade = an unchanged close
    clock = FakeClock(start)
    t = Trader(api, cfg, now=clock.now, sleep=clock.sleep, root=tmp_path)
    return t, api, clock


def hold(api, sym, value):
    api.pos[sym] = {"symbol": sym, "qty": "1", "market_value": str(value), "unrealized_plpc": "0", "unrealized_pl": "0"}


def test_leveraged_core_rebalances_once_in_the_window(tmp_path):
    write_picks(tmp_path, [])
    # a volatile index: alternate +2% / -2% days, trending up -> vol ~ 32%, weight 0.30/(3*0.32) ~ 0.31
    qqq, px = [], 100.0
    for i in range(260):
        px *= 1.021 if i % 2 else 0.98
        qqq.append(px)
    t, api, clock = make(tmp_path, qqq=qqq)
    assert t.cycle() == "managed"
    buys = {o["symbol"]: float(o["notional"]) for o in api.orders.values() if o["side"] == "buy"}
    assert set(buys) == {"TQQQ", "SPY"} and buys["TQQQ"] + buys["SPY"] == pytest.approx(98.0, abs=0.02)
    assert 0.25 < buys["TQQQ"] / 98 < 0.40
    state = json.loads((tmp_path / "state" / "core.json").read_text())
    assert state["date"] == "2026-10-08" and state["trend"] == 1 and state["dip_state"] == 0 and state["ordered"]
    assert 0.25 < state["weight"] < 0.40
    snap = json.loads((tmp_path / "state" / "account.json").read_text())
    assert snap["core"]["leverage"] is True and snap["core"]["signals"]["weight"] == state["weight"]
    ledger = (tmp_path / "ledger" / "core.csv").read_text()
    assert "rebalance trend=1" in ledger
    clock.t += timedelta(minutes=10)
    n = len(api.orders)
    t.cycle()                                                     # same session: nothing more
    assert len(api.orders) == n


def test_leveraged_core_does_nothing_outside_the_window(tmp_path):
    write_picks(tmp_path, [])
    for start in (NOW, datetime(2026, 10, 8, 18, 45, tzinfo=timezone.utc), LATE):   # 10:50, 14:45, 16:00 ET
        t, api, _ = make(tmp_path, start=start)
        (tmp_path / "state").mkdir(exist_ok=True)
        (tmp_path / "state" / "core.json").write_text(json.dumps({"date": "2026-10-06", "dip_state": 0}))  # last close seen
        t.cycle()
        assert not api.orders, start


def test_dip_replay_is_self_healing():
    assert risk.dip_replay([10, 9, 8, 7]) == 1
    assert risk.dip_replay([10, 9, 8, 7, 6]) == 2
    assert risk.dip_replay([10, 9, 8, 7, 6, 7]) == 0
    assert risk.dip_replay([10, 9, 8, 7, 6, 5, 4, 3]) == 5        # fifth session held...
    assert risk.dip_replay([10, 9, 8, 7, 6, 5, 4, 3, 2]) == 0     # ...then out regardless
    assert risk.dip_replay(closes(50)) == 0


def test_missed_window_catches_up_at_the_next_run_on_the_completed_close(tmp_path):
    """The 15:35-15:58 run was skipped after the third lower close: the 9:35 run acts on
    it at once, from completed closes only (today's live price plays no part)."""
    write_picks(tmp_path, [])
    qqq = closes(260, 0.002)
    qqq[-3:] = [qqq[-4] * 0.99, qqq[-4] * 0.98, qqq[-4] * 0.97]   # three lower closes, all completed
    api = FakeAlpaca(cash=2.0)
    hold(api, "SPY", 98.0)
    t, api, _ = make(tmp_path, api=api, start=NOW, qqq=qqq)        # 10:50 ET
    api.prices["QQQ"] = qqq[-1] * 1.05                            # a live bounce must not matter
    t.cycle()
    assert "SPY" in api.closed
    tqqq = [o for o in api.orders.values() if o["side"] == "buy" and o["symbol"] == "TQQQ"]
    assert len(tqqq) == 1 and float(tqqq[0]["notional"]) == pytest.approx(98.0, abs=0.02)
    state = json.loads((tmp_path / "state" / "core.json").read_text())
    assert state["dip_state"] == 1 and state["date"] == "2026-10-06" and state["index_close"] == qqq[-1]
    assert "catch-up" in (tmp_path / "ledger" / "core.csv").read_text()
    n = len(api.orders)
    t.cycle()                                                     # same completed close: nothing more
    assert len(api.orders) == n


def test_missed_exit_sells_at_the_next_run(tmp_path):
    write_picks(tmp_path, [])
    qqq = falling()                                               # below the trend: without the overlay, no TQQQ
    qqq[-4:-1] = [qqq[-5] * 0.99, qqq[-5] * 0.98, qqq[-5] * 0.97]  # entered on the third lower close...
    qqq[-1] = qqq[-2] * 1.01                                      # ...then an up close the window run missed
    api = FakeAlpaca(cash=2.0)
    hold(api, "TQQQ", 98.0)
    t, api, _ = make(tmp_path, api=api, start=NOW, qqq=qqq)
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "state" / "core.json").write_text(json.dumps({"date": "2026-10-05", "dip_state": 1}))
    t.cycle()
    state = json.loads((tmp_path / "state" / "core.json").read_text())
    assert state["dip_state"] == 0 and state["date"] == "2026-10-06" and state["weight"] == 0
    assert "TQQQ" in api.closed
    spy = [o for o in api.orders.values() if o["side"] == "buy" and o["symbol"] == "SPY"]
    assert len(spy) == 1 and float(spy[0]["notional"]) == pytest.approx(98.0, abs=0.02)


def test_weight_can_wait_for_completed_sessions_while_the_overlay_uses_the_live_price(tmp_path):
    write_picks(tmp_path, [])
    cfg = {**LEV_CFG, "core": {**LEV_CFG["core"], "weight_live_close": False}}
    qqq = closes(260, 0.002)
    api = FakeAlpaca(cash=2.0)
    hold(api, "SPY", 98.0)
    t, api, _ = make(tmp_path, cfg=cfg, api=api, qqq=qqq)
    api.prices["QQQ"] = qqq[-1] * 0.5                             # a crash today: trend would flip off if used
    t.cycle()
    state = json.loads((tmp_path / "state" / "core.json").read_text())
    assert state["trend"] == 1 and state["weight"] == 1.0         # weight from completed sessions
    assert state["index_close"] == qqq[-1] * 0.5                  # the overlay saw the live price


def test_dip_overlay_goes_all_in(tmp_path):
    write_picks(tmp_path, [])
    qqq = closes(260, 0.002)
    qqq[-3:] = [qqq[-4] * 0.99, qqq[-4] * 0.98, qqq[-4] * 0.97]   # three lower closes (the last is today)
    api = FakeAlpaca(cash=2.0)
    hold(api, "SPY", 98.0)
    t, api, _ = make(tmp_path, api=api, qqq=qqq[:-1])
    api.prices["QQQ"] = qqq[-1]                                   # today's close stands in via the last trade
    t.cycle()
    assert "SPY" in api.closed
    tqqq = [o for o in api.orders.values() if o["side"] == "buy" and o["symbol"] == "TQQQ"]
    assert len(tqqq) == 1 and float(tqqq[0]["notional"]) == pytest.approx(98.0, abs=0.02)
    assert json.loads((tmp_path / "state" / "core.json").read_text())["dip_state"] == 1


def test_below_the_trend_the_core_is_all_spy(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    hold(api, "TQQQ", 50.0)
    hold(api, "SPY", 48.0)
    t, api, _ = make(tmp_path, api=api, qqq=falling())
    t.cycle()
    assert "TQQQ" in api.closed
    spy = [o for o in api.orders.values() if o["side"] == "buy" and o["symbol"] == "SPY"]
    assert len(spy) == 1 and float(spy[0]["notional"]) == pytest.approx(50.0, abs=0.02)
    assert json.loads((tmp_path / "state" / "core.json").read_text())["weight"] == 0


def test_within_the_band_nothing_trades(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    hold(api, "TQQQ", 95.0)                                       # calm uptrend wants 100%: 97% held is close enough
    hold(api, "SPY", 3.0)
    t, api, _ = make(tmp_path, api=api)
    t.cycle()
    assert not api.orders and not api.closed
    assert json.loads((tmp_path / "state" / "core.json").read_text())["ordered"] is False


def test_halt_only_reduces_leverage(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    api.account = lambda: {"equity": "70", "last_equity": "100", "cash": str(api.cash), "status": "ACTIVE"}
    hold(api, "TQQQ", 60.0)
    hold(api, "SPY", 8.0)
    t, api, _ = make(tmp_path, api=api, qqq=falling())           # trend off: target 0% TQQQ
    assert t.cycle() == "halted"
    assert "TQQQ" in api.closed
    assert not [o for o in api.orders.values() if o["side"] == "buy"]              # proceeds stay in cash


def test_halt_never_sells_spy_to_fund_a_blocked_tqqq_buy(tmp_path):
    """Review finding: under a halt the rule may want MORE TQQQ (a dip signal on a crash
    day, or a rising weight); the SPY sleeve must stay put, not be sold into cash."""
    write_picks(tmp_path, [])
    qqq = closes(260, 0.002)
    qqq[-3:] = [qqq[-4] * 0.99, qqq[-4] * 0.98, qqq[-4] * 0.97]   # dip signal: wants 100% TQQQ
    for held_tqqq in (0.0, 20.0):
        root = tmp_path / f"held{int(held_tqqq)}"
        root.mkdir()
        write_picks(root, [])
        api = FakeAlpaca(cash=2.0)
        api.account = lambda: {"equity": "70", "last_equity": "100", "cash": str(api.cash), "status": "ACTIVE"}
        if held_tqqq:
            hold(api, "TQQQ", held_tqqq)
        hold(api, "SPY", 68.0 - held_tqqq)
        t, api, _ = make(root, api=api, qqq=qqq[:-1])
        api.prices["QQQ"] = qqq[-1]
        assert t.cycle() == "halted"
        assert not api.orders and not api.closed, held_tqqq
        state = json.loads((root / "state" / "core.json").read_text())
        assert state["dip_state"] == 1 and state["halted"] and state["rest_target"] == 68.0 - held_tqqq
        assert state["lev_target"] == held_tqqq
    # the same with no dip but a weight rising above what is held (calm uptrend wants 100%)
    api = FakeAlpaca(cash=2.0)
    api.account = lambda: {"equity": "70", "last_equity": "100", "cash": str(api.cash), "status": "ACTIVE"}
    hold(api, "TQQQ", 30.0)
    hold(api, "SPY", 38.0)
    t, api, _ = make(tmp_path, api=api)
    assert t.cycle() == "halted"
    assert not api.orders and not api.closed


def test_stale_core_orders_are_cancelled_before_a_rebalance(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    hold(api, "SPY", 98.0)
    cancelled = []
    api.open_orders = lambda: [{"id": "o1", "client_order_id": "core-20261007-1540-TQQQ", "symbol": "TQQQ"},
                               {"id": "o2", "client_order_id": "pick-x", "symbol": "NVDA"}]
    api.cancel_order = lambda oid: cancelled.append(oid)
    qqq = closes(260, 0.002)
    qqq[-3:] = [qqq[-4] * 0.99, qqq[-4] * 0.98, qqq[-4] * 0.97]
    t, api, _ = make(tmp_path, api=api, qqq=qqq[:-1])
    api.prices["QQQ"] = qqq[-1]
    t.cycle()
    assert cancelled == ["o1"]


def test_a_refused_cancel_does_not_abort_the_rebalance(tmp_path):
    from bot.alpaca import AlpacaError
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    hold(api, "SPY", 98.0)
    api.open_orders = lambda: [{"id": "o1", "client_order_id": "core-20261007-1540-TQQQ", "symbol": "TQQQ"}]

    def refuse(oid):
        raise AlpacaError("order already filled")
    api.cancel_order = refuse
    qqq = closes(260, 0.002)
    qqq[-3:] = [qqq[-4] * 0.99, qqq[-4] * 0.98, qqq[-4] * 0.97]
    t, api, _ = make(tmp_path, api=api, qqq=qqq[:-1])
    api.prices["QQQ"] = qqq[-1]
    assert t.cycle() == "managed"
    assert "SPY" in api.closed                                    # the dip entry still happened
    assert json.loads((tmp_path / "state" / "core.json").read_text())["dip_state"] == 1


def test_picks_are_funded_from_spy_first_then_tqqq(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "conviction": 3}])
    api = FakeAlpaca(cash=2.0)
    hold(api, "SPY", 20.0)
    hold(api, "TQQQ", 78.0)
    t, api, _ = make(tmp_path, api=api, start=NOW)
    assert t.cycle() == "traded"
    assert "SPY" in api.closed                                    # all $20 of SPY went first
    tqqq_sells = [o for o in api.orders.values() if o["side"] == "sell" and o["symbol"] == "TQQQ"]
    assert len(tqqq_sells) == 1 and 18 < float(tqqq_sells[0]["notional"]) < 22   # ~$40 pick - $2 cash - $20 SPY
    assert api.orders["p1-entry"]["notional"] == "40.00"
    assert "fund pick" in (tmp_path / "ledger" / "core.csv").read_text()


def test_tqqq_is_core_not_a_pick_or_an_adoptee(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "TQQQ", "action": "buy"}], close=["adopted-TQQQ"])
    api = FakeAlpaca()
    hold(api, "TQQQ", 50.0)
    t, api, _ = make(tmp_path, api=api, start=NOW)
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "state" / "core.json").write_text(json.dumps({"date": "2026-10-06", "dip_state": 0}))  # nothing to catch up
    t.cycle()
    assert not api.orders and not api.closed
    assert json.loads((tmp_path / "state" / "positions.json").read_text()) == {}


def test_leverage_off_unwinds_tqqq_into_spy(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    hold(api, "TQQQ", 50.0)
    hold(api, "SPY", 48.0)
    t, api, _ = make(tmp_path, cfg=LIVE_CFG, api=api)             # leverage false, 15:40 ET
    t.cycle()
    assert "TQQQ" in api.closed
    spy = [o for o in api.orders.values() if o["side"] == "buy" and o["symbol"] == "SPY"]
    assert len(spy) == 1 and float(spy[0]["notional"]) == pytest.approx(50.0, abs=0.02)
    assert "leverage off" in (tmp_path / "ledger" / "core.csv").read_text()


def test_short_history_holds(tmp_path):
    write_picks(tmp_path, [])
    t, api, _ = make(tmp_path, qqq=closes(120))
    t.cycle()
    assert not api.orders and not (tmp_path / "state" / "core.json").exists()


def test_core_buys_are_capped_and_whole_shares_when_not_fractionable(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=1000.0)
    api.asset = lambda sym: {"tradable": True, "status": "active", "class": "us_equity", "exchange": "NASDAQ",
                             "fractionable": sym != "TQQQ"}
    t, api, _ = make(tmp_path, api=api)
    t.cycle()
    tqqq = next(o for o in api.orders.values() if o["symbol"] == "TQQQ")
    assert "qty" in tqqq and int(tqqq["qty"]) * 80.8 <= 500.0         # whole shares, under the $500 ceiling
    assert float(tqqq["qty"]) >= 6


def test_core_config_shape_defaults_to_plain_spy():
    assert LIVE_CFG["core"]["leverage"] is False and LIVE_CFG["core"]["symbol"] == "SPY"
    assert LIVE_CFG["options_enabled"] is False and LIVE_CFG["learning"] is False
    assert (LIVE_CFG["min_hold_days"], LIVE_CFG["default_hold_days"], LIVE_CFG["max_hold_days"]) == (3, 28, 30)
    # the hard limits are untouched
    assert LIVE_CFG["daily_loss_cap_pct"] == 0.25 and LIVE_CFG["drawdown_halt_pct"] == 0.60
    assert LIVE_CFG["max_order_notional"] == 500.0


def test_core_snapshot_without_leverage_keeps_the_old_keys(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=2.0)
    hold(api, "SPY", 98.0)
    t, api, _ = make(tmp_path, cfg=LIVE_CFG, api=api, start=NOW)
    t.cycle()
    core = Core(t, LIVE_CFG).snapshot()
    assert core["symbol"] == "SPY" and core["value"] == 98.0 and core["held"] == {"SPY": 98.0, "TQQQ": 0.0}
