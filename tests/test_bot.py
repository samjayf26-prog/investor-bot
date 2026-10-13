import json
from datetime import date, datetime, timedelta, timezone

import pytest

from bot import picks, risk
from bot.alpaca import AlpacaError
from bot.trader import Trader, load_config, make_client, scalper_symbols

NOW = datetime(2026, 10, 8, 14, 50, tzinfo=timezone.utc)  # 10:50 ET, a Thursday
TODAY = date(2026, 10, 8)
CFG = load_config()


# risk
def test_daily_loss_cap():
    assert risk.daily_loss_ok(80, 100, 0.25)[0]
    assert not risk.daily_loss_ok(75, 100, 0.25)[0]


def test_drawdown_halt():
    assert risk.drawdown_ok(41, 100, 0.60)[0]
    assert not risk.drawdown_ok(40, 100, 0.60)[0]


def test_budget():
    assert risk.pick_budget(100, 100, 3, 500, 1) == 40.0
    assert risk.pick_budget(100, 100, 1, 500, 1) == 15.0
    assert risk.pick_budget(100, 100, 99, 500, 1) == 15.0   # unknown conviction = smallest
    assert risk.pick_budget(100, 10, 3, 500, 1) == 9.8      # no leverage
    assert risk.pick_budget(10_000, 10_000, 3, 500, 1) == 500
    assert risk.pick_budget(100, 0.5, 3, 500, 1) == 0.0


def test_sizing_cap_makes_paper_trade_like_100_dollars():
    assert risk.sizing_view(100_000, 100_000, 0, 100) == (100, 100)
    assert risk.sizing_view(100_000, 100_000, 70, 100) == (100, 30)
    assert risk.sizing_view(80, 80, 0, 100) == (80, 80)


def test_exit_reasons():
    assert risk.exit_reason(-0.09, 0.08, 0.15, 0, 5, False).startswith("stop")
    assert risk.exit_reason(0.16, 0.08, 0.15, 0, 5, False).startswith("profit")
    assert risk.exit_reason(0.0, 0.08, 0.15, 0, 5, True) == "Claude asked to close"
    assert risk.exit_reason(0.0, 0.08, 0.15, 5, 5, False).startswith("max hold")
    assert risk.exit_reason(0.0, 0.5, 1.0, 0, 5, False, days_to_expiry=2) == "option near expiry"
    assert risk.exit_reason(0.0, 0.08, 0.15, 1, 5, False) is None
    # max_hold_days 0 = day trade: kept intraday, sold late in the day or the next day
    assert risk.exit_reason(0.0, 0.08, 0.15, 0, 0, False) is None
    assert risk.exit_reason(0.0, 0.08, 0.15, 0, 0, False, late_in_day=True) == "day trade: end of day"
    assert risk.exit_reason(0.0, 0.08, 0.15, 1, 0, False) == "day trade: end of day"


def contract(sym, strike, days):
    return {"symbol": sym, "strike_price": str(strike), "expiration_date": (TODAY + timedelta(days=days)).isoformat()}


def test_choose_put_picks_affordable_near_money():
    cs = [contract("ATM", 20, 20), contract("OTM", 18, 20), contract("SOON", 20, 3), contract("WIDE", 19.5, 20)]
    quotes = {"ATM": {"ap": 1.20, "bp": 1.10}, "OTM": {"ap": 0.40, "bp": 0.35},
              "SOON": {"ap": 0.30, "bp": 0.28}, "WIDE": {"ap": 0.50, "bp": 0.10}}
    c, ask = risk.choose_put(cs, quotes, 20.0, 60, TODAY)
    assert c["symbol"] == "OTM" and ask == 0.40   # ATM too expensive, SOON too close, WIDE illiquid
    assert risk.choose_put(cs, quotes, 20.0, 30, TODAY) == (None, None)


# picks
def write_picks(tmp_path, items, **kw):
    data = {"schema_version": 2, "generated_at": "2026-10-08T12:50:00Z",
            "expires_at": "2026-10-08T20:00:00Z", "picks": items, "close": []}
    data.update(kw)
    (tmp_path / "picks").mkdir(exist_ok=True)
    (tmp_path / "picks" / "latest.json").write_text(json.dumps(data))
    return tmp_path / "picks" / "latest.json"


def test_picks_validation_and_clamping(tmp_path):
    p = write_picks(tmp_path, [
        {"id": "a", "symbol": "nvda", "action": "buy", "conviction": 9, "stop_pct": 0.9, "max_hold_days": 99},
        {"id": "b", "symbol": "XYZ;rm", "action": "buy"},
        {"id": "c", "symbol": "TSLA", "action": "short"},
        {"id": "d", "symbol": "F", "action": "buy_put"},
    ])
    entries, _, notes = picks.load(p, NOW, CFG)
    assert [e["id"] for e in entries] == ["a"]
    a = entries[0]
    assert a["symbol"] == "NVDA" and a["conviction"] == 3 and a["stop_pct"] == 0.25 and a["max_hold_days"] == 10
    assert len(notes) == 2   # b and c dropped; d is beyond max_picks_per_run


def test_expired_picks_still_allow_close(tmp_path):
    p = write_picks(tmp_path, [{"id": "a", "symbol": "F", "action": "buy"}],
                    expires_at="2026-10-08T13:00:00Z", close=["old"])
    entries, close, _ = picks.load(p, NOW, CFG)
    assert entries == [] and close == {"old"}


def test_garbage_picks(tmp_path):
    (tmp_path / "latest.json").write_text("{nope")
    assert picks.load(tmp_path / "latest.json", NOW, CFG)[0] == []
    assert picks.load(tmp_path / "missing.json", NOW, CFG)[0] == []


# simulated broker
class FakeClock:
    def __init__(self, t):
        self.t = t

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += timedelta(seconds=s)


class FakeAlpaca:
    def __init__(self, cash=100.0, options_level=2, open_=True):
        self.cash, self.options_level, self.open_ = cash, options_level, open_
        self.orders, self.pos, self.closed = {}, {}, []
        self.prices = {"NVDA": 180.0, "F": 11.0, "BRK.A": 700000.0, "PENNY": 0.5, "TQQQ": 80.0, "WHOLE": 10.0}

    def clock(self):
        return {"is_open": self.open_}

    def account(self):
        return {"equity": "100", "last_equity": "100", "cash": str(self.cash), "status": "ACTIVE",
                "options_trading_level": self.options_level}

    def portfolio_history(self):
        return {"equity": [100, None]}

    def positions(self):
        return list(self.pos.values())

    def order_by_client_id(self, cid):
        return self.orders.get(cid)

    def cancel_all_orders(self):
        pass

    def open_orders(self):
        return []

    def asset(self, sym):
        if sym == "OTCX":
            return {"tradable": True, "status": "active", "class": "us_equity", "exchange": "OTC"}
        return {"tradable": True, "status": "active", "class": "us_equity", "exchange": "NASDAQ",
                "fractionable": sym not in ("BRK.A", "WHOLE")}

    def last_price(self, sym):
        return self.prices[sym]

    def put_contracts(self, und, a, b):
        return [contract("F261030P00011000", 11, 22), contract("F261030P00010000", 10, 22)]

    def option_quotes(self, syms):
        return {"F261030P00011000": {"ap": 0.35, "bp": 0.32}, "F261030P00010000": {"ap": 0.15, "bp": 0.13}}

    def submit_order(self, **o):
        cost = float(o.get("notional") or 0) or float(o["qty"]) * (float(o.get("limit_price", 0)) * 100 or 1)
        self.cash -= cost
        o.update(status="filled", filled_qty=o.get("qty", "1"))
        self.orders[o["client_order_id"]] = o
        self.pos[o["symbol"]] = {"symbol": o["symbol"], "qty": o["filled_qty"], "unrealized_plpc": "0.01",
                                 "unrealized_pl": "0.4", "cost_basis": str(cost)}
        return o

    def close_position(self, sym):
        self.closed.append(sym)
        del self.pos[sym]


def make(tmp_path, api=None, start=NOW):
    clock = FakeClock(start)
    api = api or FakeAlpaca()
    t = Trader(api, CFG, now=clock.now, sleep=clock.sleep, root=tmp_path)
    return t, api, clock


def test_buy_and_put_entries(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "conviction": 3},
                           {"id": "p2", "symbol": "F", "action": "buy_put", "conviction": 3}])
    t, api, _ = make(tmp_path)
    assert t.cycle() == "traded"
    # live picks size off real equity ($100 here), so gains compound
    assert api.orders["p1-entry"]["notional"] == "40.00"
    put = api.orders["p2-entry"]
    # the nearest-the-money put that fits the $40 budget
    assert (put["symbol"], put["limit_price"]) == ("F261030P00011000", "0.35") and put["type"] == "limit"
    state = json.loads((tmp_path / "state" / "positions.json").read_text())
    assert state["p2"]["expiry"] and state["p1"]["broker_symbol"] == "NVDA"


def test_paper_sizes_like_the_capped_stake(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "conviction": 3}])
    t, api, _ = make(tmp_path, FakeAlpaca(cash=100_000))
    t.cfg = {**CFG, "mode": "paper", "sizing_equity_cap": 75.0}
    t.cycle()
    assert api.orders["p1-entry"]["notional"] == "30.00"


def test_rerun_does_not_double_buy(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy"}])
    t, api, _ = make(tmp_path)
    t.cycle()
    t.cycle()
    assert len(api.orders) == 1


def test_puts_skipped_without_options_approval(tmp_path):
    write_picks(tmp_path, [{"id": "p2", "symbol": "F", "action": "buy_put"}])
    t, api, _ = make(tmp_path, FakeAlpaca(options_level=0))
    t.cycle()
    assert not api.orders


def test_rejects_otc_penny_and_unaffordable(tmp_path):
    write_picks(tmp_path, [{"id": "a", "symbol": "OTCX", "action": "buy"},
                           {"id": "b", "symbol": "PENNY", "action": "buy"},
                           {"id": "c", "symbol": "BRK.A", "action": "buy"}])
    t, api, _ = make(tmp_path)
    t.cycle()
    assert not api.orders


def test_stop_loss_and_claude_close(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy"},
                           {"id": "p3", "symbol": "F", "action": "buy"}])
    t, api, clock = make(tmp_path)
    t.cycle()
    api.pos["NVDA"]["unrealized_plpc"] = "-0.09"
    write_picks(tmp_path, [], close=["p3"])
    clock.t += timedelta(hours=1)
    t.cycle()
    assert set(api.closed) == {"NVDA", "F"}
    ledger = (tmp_path / "ledger" / "trades.csv").read_text()
    assert "stop loss" in ledger and "Claude asked to close" in ledger


def test_max_hold_exit(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "max_hold_days": 2}])
    t, api, clock = make(tmp_path)
    t.cycle()
    clock.t += timedelta(days=2)
    t.cycle()
    assert api.closed == ["NVDA"]


def test_position_limit(tmp_path):
    write_picks(tmp_path, [{"id": f"p{i}", "symbol": "F", "action": "buy"} for i in range(3)])
    cfg = {**CFG, "max_open_positions": 1}
    api = FakeAlpaca()
    t = Trader(api, cfg, now=lambda: NOW, sleep=lambda s: None, root=tmp_path)
    t.cycle()
    assert len(api.orders) == 1


def test_no_entries_after_cutoff(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy"}])
    t, api, _ = make(tmp_path, start=datetime(2026, 10, 8, 19, 50, tzinfo=timezone.utc))  # 15:50 ET
    t.cycle()
    assert not api.orders


def test_kill_switch_flattens(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy"}])
    t, api, _ = make(tmp_path)
    t.cycle()
    t.cfg = {**CFG, "kill": True}
    assert t.cycle() == "killed" and api.closed == ["NVDA"]


def test_market_closed_does_nothing(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy"}])
    t, api, _ = make(tmp_path, FakeAlpaca(open_=False))
    assert t.cycle() == "closed" and not api.orders


def test_live_requires_confirmation():
    with pytest.raises(SystemExit):
        make_client({"mode": "live", "confirm_live": False})


def test_entry_limit():
    assert risk.entry_limit(100.0) == 101.0
    assert risk.entry_limit(100.0, 100.5) == 100.5
    assert risk.entry_limit(100.0, 120) == 101.0
    assert risk.entry_limit(9.999) == 10.09


def test_stock_entries_are_limit_orders_capped_at_max_entry(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "max_entry_price": 181},
                           {"id": "p2", "symbol": "WHOLE", "action": "buy"}])
    t, api, _ = make(tmp_path)
    t.cycle()
    assert api.orders["p1-entry"]["type"] == "limit" and api.orders["p1-entry"]["limit_price"] == "181.00"
    assert api.orders["p2-entry"]["limit_price"] == "10.10" and api.orders["p2-entry"]["qty"] == "1"


class RefusesLimits(FakeAlpaca):
    def submit_order(self, **o):
        if o["type"] == "limit" and "notional" in o:
            raise AlpacaError(422, '{"message":"limit not allowed"}')
        return super().submit_order(**o)


def test_refused_fractional_limit_falls_back_to_market(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy"}])
    t, api, _ = make(tmp_path, RefusesLimits())
    assert t.cycle() == "traded" and api.orders["p1-entry"]["type"] == "market"


class RejectsSecondOrder(FakeAlpaca):
    def submit_order(self, **o):
        if len(self.orders) == 1:
            raise AlpacaError(403, '{"message":"insufficient buying power"}')
        return super().submit_order(**o)


def test_refused_order_skips_that_pick_and_keeps_the_others(tmp_path):
    # review finding: a refused 2nd order used to crash the run before pick 1 was saved
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "stop_pct": 0.03},
                           {"id": "p2", "symbol": "F", "action": "buy"}])
    t, api, _ = make(tmp_path, RejectsSecondOrder())
    assert t.cycle() == "traded"
    state = json.loads((tmp_path / "state" / "positions.json").read_text())
    assert set(state) == {"p1"} and state["p1"]["stop_pct"] == 0.03


def test_scalper_symbols_reserved_only_on_its_own_account(tmp_path):
    live = {**CFG, "mode": "live", "scalper": {**CFG["scalper"], "mode": "paper"}}
    assert scalper_symbols(live) == set()
    same = {**CFG, "mode": "live", "scalper": {**CFG["scalper"], "mode": "live"}}
    assert scalper_symbols(same) == {"SPY", "QQQ", "TQQQ", "SQQQ"}
    assert scalper_symbols({**same, "scalper": {**same["scalper"], "enabled": False}}) == set()
    write_picks(tmp_path, [{"id": "p1", "symbol": "TQQQ", "action": "buy"}])
    t, api, _ = make(tmp_path)
    t.cfg = live
    t.cycle()
    assert "p1-entry" in api.orders
    (tmp_path / "x").mkdir()
    write_picks(tmp_path / "x", [{"id": "p1", "symbol": "TQQQ", "action": "buy"}])
    t2, api2, _ = make(tmp_path / "x")
    t2.cfg = same
    t2.cycle()
    assert not api2.orders


def test_day_trade_held_until_late_then_sold(tmp_path):
    write_picks(tmp_path, [{"id": "d1", "symbol": "TQQQ", "action": "buy", "max_hold_days": 0}])
    t, api, clock = make(tmp_path)
    t.cycle()
    clock.t += timedelta(minutes=15)
    t.cycle()
    assert not api.closed
    clock.t = datetime(2026, 10, 8, 19, 35, tzinfo=timezone.utc)   # 15:35 ET
    t.cycle()
    assert api.closed == ["TQQQ"]
