"""Independent review backtest of the scalper and its daily tuner (read-only market data).

    python review/backtest.py [sessions]

Fetches 1-minute bars for the scalper's ETFs over the last `sessions` trading days and
measures, out of sample, what the live rules and the learn.py tuner would have earned.
Uses bot/learn.py's own simulate() so the replay matches the bot's. Places no orders.
Writes review/backtest-results.md.
"""
import sys
from collections import defaultdict
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot import learn, tuning  # noqa: E402
from bot.alpaca import Alpaca, AlpacaError  # noqa: E402
from bot.trader import ET, load_config  # noqa: E402

SYMS = ["SPY", "QQQ", "TQQQ", "SQQQ"]
NOTIONAL = 15.0
LOOKBACK = learn.LOOKBACK
OUT = []


def say(line=""):
    print(line, flush=True)
    OUT.append(line)


def fetch(api, dates, feed, start_t=dtime(9, 35), end_t=dtime(15, 15)):
    """{sym: [bars of each date]} for the live scalping window only (9:35-15:15 ET)."""
    lo = datetime.combine(datetime.fromisoformat(dates[0]).date(), dtime(9, 0), ET).astimezone(timezone.utc)
    hi = datetime.combine(datetime.fromisoformat(dates[-1]).date(), dtime(16, 0), ET).astimezone(timezone.utc)
    out = {}
    for sym in SYMS:
        bars = api.bars_between(sym, "1Min", lo.isoformat(), hi.isoformat(), feed=feed)
        by_day = defaultdict(list)
        for b in bars:
            t = datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
            if start_t <= t.time() <= end_t:
                by_day[t.date().isoformat()].append(b)
        out[sym] = [by_day[d] for d in dates]
    return out


def day_returns(sessions, i, p, syms, cache, cost):
    """Sum of round-trip returns on day i for symbols syms with settings p."""
    total, n = 0.0, 0
    for s in syms:
        bars = sessions[s][i]
        if len(bars) < 30:
            continue
        key = (s, i, p["ema_fast"], p["ema_slow"])
        if key not in cache:
            cache[key] = learn.signals(bars, p["ema_fast"], p["ema_slow"])
        rs = learn.simulate(bars, cache[key], p, cost=cost)
        total += sum(rs)
        n += len(rs)
    return total, n


def window_scores(sessions, idxs, p, cache, cost):
    """{sym: (first_half, second_half)} over day indexes idxs, like learn.evaluate."""
    half = len(idxs) // 2
    res = {}
    for s in SYMS:
        a = b = 0.0
        for k, i in enumerate(idxs):
            t, _ = day_returns(sessions, i, p, [s], cache, cost)
            if k < half:
                a += t
            else:
                b += t
        res[s] = (a, b)
    return res


def walk_forward(sessions, ndays, start_p, cost):
    """Each day, run the tuner on the previous LOOKBACK days, then trade that day.
    Returns per-policy lists of (day P&L in $, trades)."""
    cache, combos = {}, list(learn.combos())
    cur_p, cur_syms = dict(start_p), list(SYMS)
    pol = {"tuner as shipped": [], "tuner + must be profitable": [], "fixed current tuning.json": [],
           "fixed config.json defaults": []}
    fixed_now = {k: start_p[k] for k in learn.KNOBS}
    tuned_now = tuning.apply(load_config()["scalper"], tuning.load(ROOT / "tuning.json"))
    switches = 0
    for i in range(LOOKBACK, ndays):
        idxs = list(range(i - LOOKBACK, i))
        base_res = window_scores(sessions, idxs, cur_p, cache, cost)
        base = (sum(base_res[s][0] for s in cur_syms), sum(base_res[s][1] for s in cur_syms))
        best = None      # learn.choose rule: beat current by MARGIN in both halves
        best_abs = None  # stricter rule: also positive in both halves
        for p in combos:
            res = window_scores(sessions, idxs, p, cache, cost)
            syms = [s for s in SYMS if res[s][0] > 0 and res[s][1] > 0] or list(SYMS)
            a, b = sum(res[s][0] for s in syms), sum(res[s][1] for s in syms)
            if a > base[0] + learn.MARGIN and b > base[1] + learn.MARGIN and (best is None or a + b > best[2]):
                best = (p, syms, a + b)
            if a > 0 and b > 0 and (best_abs is None or a + b > best_abs[2]):
                best_abs = (p, syms, a + b)
        if best:
            cur_p, cur_syms = dict(best[0]), best[1]
            switches += 1
        r, n = day_returns(sessions, i, cur_p, cur_syms, cache, cost)
        pol["tuner as shipped"].append((r * NOTIONAL, n))
        if best_abs:
            r2, n2 = day_returns(sessions, i, best_abs[0], best_abs[1], cache, cost)
        else:
            r2, n2 = 0.0, 0
        pol["tuner + must be profitable"].append((r2 * NOTIONAL, n2))
        tn = {k: tuned_now[k] for k in learn.KNOBS}
        r3, n3 = day_returns(sessions, i, tn, tuned_now.get("enabled_symbols") or SYMS, cache, cost)
        pol["fixed current tuning.json"].append((r3 * NOTIONAL, n3))
        r4, n4 = day_returns(sessions, i, fixed_now, SYMS, cache, cost)
        pol["fixed config.json defaults"].append((r4 * NOTIONAL, n4))
    return pol, switches


def all_combos(sessions, ndays, cost):
    cache, rows = {}, []
    for p in learn.combos():
        tot, n = 0.0, 0
        for i in range(ndays):
            r, k = day_returns(sessions, i, p, SYMS, cache, cost)
            tot += r
            n += k
        rows.append((tot, n, p))
    rows.sort(key=lambda r: r[0])
    return rows


def report_policies(pol, switches, ndays):
    say(f"Out-of-sample days: {ndays - LOOKBACK}. Tuner switched settings on {switches} days.")
    say("")
    say("| policy | trades | P&L $ (at $15/trade) | per trade % | winning days |")
    say("|---|---|---|---|---|")
    for name, rows in pol.items():
        pnl = sum(r[0] for r in rows)
        n = sum(r[1] for r in rows)
        wins = sum(1 for r in rows if r[0] > 0)
        per = (pnl / NOTIONAL / n * 100) if n else 0.0
        say(f"| {name} | {n} | {pnl:+.2f} | {per:+.4f}% | {wins}/{len(rows)} |")


def main():
    nsess = int(sys.argv[1]) if len(sys.argv) > 1 else 70
    cfg = load_config()
    api = Alpaca.from_env(False)  # paper keys; market data only
    today = datetime.now(ET).date()
    cal = api.calendar((today - timedelta(days=nsess * 2)).isoformat(), (today - timedelta(days=1)).isoformat())
    dates = [d["date"] for d in cal][-nsess:]
    start_p = {k: cfg["scalper"][k] for k in learn.KNOBS}
    say(f"# Scalper backtest ({dates[0]} to {dates[-1]}, {len(dates)} sessions, 9:35-15:15 ET)")
    say("")
    say("Replays bot/learn.py simulate() (entry at next bar open after an EMA cross-up, exact stop/target"
        " fills, stop first when a bar touches both). Each symbol is replayed independently, so the live"
        " limit of 2 open scalps is ignored. Costs are per round trip, as a fraction of trade size.")
    for feed in ("iex", "sip"):
        try:
            sessions = fetch(api, dates, feed)
        except AlpacaError as e:
            say(f"\n## Feed {feed}: not available ({e.status})")
            continue
        ndays = len(dates)
        counts = {s: sum(len(d) for d in sessions[s]) // max(1, ndays) for s in SYMS}
        say(f"\n## Feed: {feed} (bars per day: {counts})")
        for cost in (0.0, learn.COST, 0.0006):
            say(f"\n### Cost {cost:.2%} per round trip")
            rows = all_combos(sessions, ndays, cost)
            pos = sum(1 for r in rows if r[0] > 0)
            say(f"All 300 settings over all {ndays} sessions: {pos} of 300 made money. "
                f"Best {rows[-1][0] * NOTIONAL:+.2f} $ ({rows[-1][1]} trades, {rows[-1][2]}), median "
                f"{rows[150][0] * NOTIONAL:+.2f} $, worst {rows[0][0] * NOTIONAL:+.2f} $.")
            if feed == "iex" or cost == learn.COST:
                pol, sw = walk_forward(sessions, ndays, start_p, cost)
                say("")
                report_policies(pol, sw, ndays)
        by_sym = {}
        cache = {}
        tuned = tuning.apply(cfg["scalper"], tuning.load(ROOT / "tuning.json"))
        tp = {k: tuned[k] for k in learn.KNOBS}
        for s in SYMS:
            r, n = 0.0, 0
            for i in range(ndays):
                a, b = day_returns(sessions, i, tp, [s], cache, learn.COST)
                r += a
                n += b
            by_sym[s] = (round(r * NOTIONAL, 2), n)
        say(f"\nCurrent tuning.json by symbol over all sessions (P&L $, trades): {by_sym}")
    (ROOT / "review" / "backtest-results.md").write_text("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
