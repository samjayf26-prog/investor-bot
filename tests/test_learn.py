import csv
import json
from datetime import date, timedelta

from bot import learn, scalper, tuning
from bot.trader import load_config

CFG = load_config()
SC = CFG["scalper"]
TODAY = date(2026, 10, 12)


def wave_day(start=100.0):
    """Flat, then a steady climb, then a slide back, repeated: the EMA cross catches each climb."""
    bars, px = [], start
    for _ in range(10):
        for step in [0] * 12 + [0.001] * 10 + [-0.001] * 10:
            o = px
            px = px * (1 + step)
            bars.append({"t": "", "o": o, "h": max(o, px), "l": min(o, px), "c": px})
    return bars


# tuning bounds
def test_apply_clamps_and_ignores_safety_limits():
    tuned = {"scalper": {"take_profit_pct": 5, "stop_pct": -1, "max_hold_minutes": 999,
                         "daily_loss_cap": 10_000, "trade_notional": 10_000, "max_open": 50,
                         "enabled_symbols": ["SPY", "GME"]},
             "kill": False, "sizing_equity_cap": 1e9}
    out = tuning.apply(SC, tuned)
    assert out["take_profit_pct"] == 0.01 and out["stop_pct"] == 0.0005 and out["max_hold_minutes"] == 30
    for key in ("daily_loss_cap", "trade_notional", "max_open", "max_round_trips"):
        assert out[key] == SC[key]
    assert out["enabled_symbols"] == ["SPY"]


def test_apply_rejects_bad_ema_order_and_empty_symbols():
    out = tuning.apply(SC, {"scalper": {"ema_fast": 30, "ema_slow": 10, "enabled_symbols": ["GME"]}})
    assert (out["ema_fast"], out["ema_slow"]) == (SC["ema_fast"], SC["ema_slow"])
    assert "enabled_symbols" not in out


def test_learning_off_ignores_tuning(tmp_path):
    path = tmp_path / "tuning.json"
    path.write_text(json.dumps({"scalper": {"take_profit_pct": 0.005}}))
    assert tuning.scalper_config({**CFG, "learning": False}, path)["take_profit_pct"] == SC["take_profit_pct"]
    assert tuning.scalper_config(CFG, path)["take_profit_pct"] == 0.005
    (tmp_path / "bad.json").write_text("{nope")
    assert tuning.scalper_config(CFG, tmp_path / "bad.json") == SC


def test_enabled_symbols_limit_what_scalper_trades():
    sc = {**SC, "enabled_symbols": ["SPY", "SQQQ"]}
    assert scalper.active_symbols(sc, "bull") == ["SPY"]
    assert scalper.active_symbols(sc, "neutral") == ["SPY", "SQQQ"]


# replay
def test_simulate_take_profit_and_stop_first():
    p = {"take_profit_pct": 0.003, "stop_pct": 0.002, "max_hold_minutes": 20, "ema_fast": 3, "ema_slow": 9}
    bars = wave_day()[:40]
    rs = learn.simulate(bars, learn.signals(bars, 3, 9), p, cost=0)
    assert rs and abs(rs[0] - 0.003) < 1e-12
    # one bar touching both levels counts as a stop
    wide = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 2 + [{"o": 100, "h": 101, "l": 99, "c": 100}]
    assert learn.simulate(wide, [True, False, False], p, cost=0) == [-0.002]


def test_choose_finds_better_settings_on_a_clear_pattern():
    sessions = {s: [wave_day() for _ in range(6)] for s in SC["symbols"]}
    current = tuning.apply(SC, {})
    base, best = learn.choose(sessions, current, SC["symbols"], SC["symbols"])
    assert best is not None
    p, syms, (a, b), _ = best
    assert a > base[0] + learn.MARGIN and b > base[1] + learn.MARGIN
    assert set(syms) <= set(SC["symbols"])


def test_choose_keeps_current_when_nothing_helps():
    flat = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 300
    sessions = {s: [flat] * 6 for s in SC["symbols"]}
    assert learn.choose(sessions, tuning.apply(SC, {}), SC["symbols"], SC["symbols"])[1] is None


# full run
class FakeData:
    def calendar(self, start, end):
        days = [TODAY - timedelta(days=i) for i in range(14)]
        return [{"date": d.isoformat()} for d in sorted(days) if d.weekday() < 5]

    def bars_between(self, sym, tf, start, end):
        return wave_day()


def setup_root(tmp_path, bias="bull"):
    (tmp_path / "picks").mkdir()
    (tmp_path / "picks" / "latest.json").write_text(json.dumps(
        {"generated_at": "2026-10-12T18:20:00Z", "scalp_bias": bias}))
    (tmp_path / "ledger").mkdir()
    (tmp_path / "research").mkdir()
    with open(tmp_path / "ledger" / "scalps.csv", "w") as f:
        f.write("date,symbol,opened,closed,entry,exit,qty,pnl,reason,mode\n"
                "2026-10-12,SPY,10:00:00,10:05:00,1,1,1,0.02,time,paper\n"
                "2026-10-12,QQQ,10:00:00,10:05:00,1,1,1,-0.01,stop,paper\n")
    with open(tmp_path / "ledger" / "trades.csv", "w") as f:
        f.write("closed,id,symbol,action,opened,cost,pnl_approx,pnl_pct,reason,mode\n"
                "2026-10-09,2026-10-09-HUM,HUM,buy,2026-10-09,24.99,-0.32,-0.0126,Claude asked to close,paper\n")


def test_run_writes_tuning_log_and_scorecard_once_a_day(tmp_path):
    setup_root(tmp_path)
    assert learn.run(FakeData(), CFG, TODAY, tmp_path) == "done"
    tuned = json.loads((tmp_path / "tuning.json").read_text())
    assert tuned["updated"] == TODAY.isoformat() and "scalper" in tuned
    rows = list(csv.DictReader(open(tmp_path / "research" / "tuning_log.csv")))
    assert rows and all(r["reason"].startswith("replay of") for r in rows)
    card = (tmp_path / "research" / "scorecard.md").read_text()
    assert "2026-10-09-HUM" in card and "| SPY | 1 | 1 | 0.02 |" in card and "Changed to" in card
    assert learn.run(FakeData(), CFG, TODAY, tmp_path) == "already-done"


def test_run_with_learning_off_changes_nothing(tmp_path):
    setup_root(tmp_path)
    learn.run(FakeData(), {**CFG, "learning": False}, TODAY, tmp_path)
    assert "scalper" not in json.loads((tmp_path / "tuning.json").read_text())
    assert not (tmp_path / "research" / "tuning_log.csv").exists()


def test_direction_call_is_scored_once_per_day(tmp_path):
    setup_root(tmp_path, bias="bear")
    lines = learn.score_direction(FakeData(), TODAY, tmp_path)
    lines = learn.score_direction(FakeData(), TODAY, tmp_path)   # rerun replaces, not duplicates
    rows = list(csv.DictReader(open(tmp_path / "research" / "direction_log.csv")))
    move = wave_day()[-1]["c"] / wave_day()[0]["o"] - 1
    assert len(rows) == 1 and rows[0]["bias"] == "bear"
    assert rows[0]["correct"] == str(move < 0).lower()
    assert any("of 1 right" in l for l in lines)
