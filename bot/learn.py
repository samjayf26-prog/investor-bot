"""Daily learning step, run by GitHub Actions after the close.

    python -m bot.learn

1. Scorecard: how today's and recent scalps and picks did (research/scorecard.md).
2. Tuner: replays the scalper's rules on the last LOOKBACK sessions of 1-minute bars
   with every combination in GRID. If a combination beats the current settings in both
   halves of that window by MARGIN, it is written to tuning.json, and every change is
   logged with its reason in research/tuning_log.csv so it can be undone.

Only the knobs in bot/tuning.py BOUNDS can change. Safety limits are never touched.
"""
import csv
import itertools
import json
from collections import defaultdict
from datetime import datetime, time as dtime, timedelta, timezone

from . import tuning
from .trader import ET, ROOT, load_config, log, make_client

LOOKBACK = 10        # trading sessions replayed
COST = 0.0003        # assumed spread + slippage per round trip, as a fraction
MARGIN = 0.002       # a new setting must beat the current one by 0.2% of notional per half
GRID = {
    "take_profit_pct": [0.001, 0.0015, 0.002, 0.003, 0.005],
    "stop_pct": [0.001, 0.0015, 0.002, 0.003, 0.005],
    "max_hold_minutes": [3, 5, 10, 20],
    "ema": [(3, 9), (5, 13), (8, 21)],
}
KNOBS = ["take_profit_pct", "stop_pct", "max_hold_minutes", "ema_fast", "ema_slow"]


# replay (pure)
def signals(bars, fast, slow):
    """Per bar: True when the fast EMA crossed above the slow EMA on that bar's close."""
    k_f, k_s = 2 / (fast + 1), 2 / (slow + 1)
    ef = es = None
    out = []
    for i, b in enumerate(bars):
        c = b["c"]
        pf, ps = ef, es
        ef = c if ef is None else c * k_f + ef * (1 - k_f)
        es = c if es is None else c * k_s + es * (1 - k_s)
        out.append(i >= slow and pf <= ps and ef > es)
    return out


def simulate(bars, sig, p, cost=COST):
    """Round-trip returns from running the scalper's rules over one session of bars.

    Enters at the next bar's open after an EMA cross-up, like the live bot buying at
    market once a bar closes. Exits on the stop first if a bar touches both levels.
    """
    out, pos = [], None
    for i, b in enumerate(bars):
        if pos is not None:
            entry, held = pos[1], i - pos[0] + 1
            if b["l"] <= entry * (1 - p["stop_pct"]):
                r = -p["stop_pct"]
            elif b["h"] >= entry * (1 + p["take_profit_pct"]):
                r = p["take_profit_pct"]
            elif held >= p["max_hold_minutes"] or i == len(bars) - 1:
                r = b["c"] / entry - 1
            else:
                r = None
            if r is not None:
                out.append(r - cost)
                pos = None
        if pos is None and sig[i] and i + 1 < len(bars):
            pos = (i + 1, bars[i + 1]["o"])
    return out


def combos():
    for tp, sl, hold, (fast, slow) in itertools.product(
            GRID["take_profit_pct"], GRID["stop_pct"], GRID["max_hold_minutes"], GRID["ema"]):
        yield {"take_profit_pct": tp, "stop_pct": sl, "max_hold_minutes": hold,
               "ema_fast": fast, "ema_slow": slow}


def evaluate(sessions, p, cache=None):
    """sessions: {symbol: [bars of day 1, bars of day 2, ...]} oldest first.
    Returns {symbol: (first_half_total, second_half_total, trades)} in fractions of notional."""
    cache = {} if cache is None else cache
    res = {}
    for sym, days in sessions.items():
        half = len(days) // 2
        totals, trades = [0.0, 0.0], 0
        for n, bars in enumerate(days):
            key = (sym, n, p["ema_fast"], p["ema_slow"])
            if key not in cache:
                cache[key] = signals(bars, p["ema_fast"], p["ema_slow"])
            rs = simulate(bars, cache[key], p)
            totals[n >= half] += sum(rs)
            trades += len(rs)
        res[sym] = (totals[0], totals[1], trades)
    return res


def score(res, symbols):
    return (sum(res[s][0] for s in symbols), sum(res[s][1] for s in symbols))


def choose(sessions, current, current_symbols, all_symbols):
    """Best settings and symbol set, or None if nothing clearly beats the current ones."""
    cache = {}
    base = score(evaluate(sessions, current, cache), current_symbols)
    best = None
    for p in combos():
        res = evaluate(sessions, p, cache)
        # keep symbols that made money in both halves; never drop to zero symbols
        syms = [s for s in all_symbols if res[s][0] > 0 and res[s][1] > 0] or list(all_symbols)
        a, b = score(res, syms)
        if a > base[0] + MARGIN and b > base[1] + MARGIN and (best is None or a + b > sum(best[2])):
            best = (p, syms, (a, b), sum(res[s][2] for s in syms))
    return base, best


# scorecard
def read_csv(path):
    try:
        with open(path) as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def summarize(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(float(r["pnl" if "pnl" in r else "pnl_approx"]))
    return {k: (len(v), sum(1 for x in v if x > 0), round(sum(v), 2)) for k, v in sorted(groups.items())}


def scorecard(today, root=ROOT):
    scalps = read_csv(root / "ledger" / "scalps.csv")
    picks = read_csv(root / "ledger" / "trades.csv")
    days = sorted({r["date"] for r in scalps})[-5:]
    recent = [r for r in scalps if r["date"] in days]
    lines = [f"# Scorecard {today}", "", "## Scalper, last 5 sessions",
             "| day | trips | winners | P&L $ |", "|---|---|---|---|"]
    for d, (n, w, pnl) in summarize(recent, "date").items():
        lines.append(f"| {d} | {n} | {w} | {pnl} |")
    lines += ["", "| symbol | trips | winners | P&L $ |", "|---|---|---|---|"]
    for s, (n, w, pnl) in summarize(recent, "symbol").items():
        lines.append(f"| {s} | {n} | {w} | {pnl} |")
    lines += ["", "| exit reason | trips | winners | P&L $ |", "|---|---|---|---|"]
    for s, (n, w, pnl) in summarize(recent, "reason").items():
        lines.append(f"| {s} | {n} | {w} | {pnl} |")
    lines += ["", "## Research picks, all closed", "| closed | pick | P&L $ | P&L % | why closed |",
              "|---|---|---|---|---|"]
    for r in picks:
        lines.append(f"| {r['closed']} | {r['id']} | {r['pnl_approx']} | "
                     f"{float(r['pnl_pct']):.1%} | {r['reason']} |")
    total = sum(float(r["pnl_approx"]) for r in picks)
    wins = sum(1 for r in picks if float(r["pnl_approx"]) > 0)
    lines.append(f"\nPicks: {len(picks)} closed, {wins} winners, ${total:.2f} total.")
    return lines


# Claude's daily direction call
def score_direction(api, today, root=ROOT):
    """Log whether today's scalp_bias called QQQ's 9:35-15:15 move right
    (research/direction_log.csv, one row per day). Returns the scorecard lines."""
    path = root / "research" / "direction_log.csv"
    rows = [r for r in read_csv(path) if r["date"] != today.isoformat()]
    try:
        data = json.loads((root / "picks" / "latest.json").read_text())
        made = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00")).astimezone(ET).date()
        bias = data.get("scalp_bias", "neutral") if made == today else "none"
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        bias = "none"
    lo = datetime.combine(today, dtime(9, 35), ET).astimezone(timezone.utc).isoformat()
    hi = datetime.combine(today, dtime(15, 15), ET).astimezone(timezone.utc).isoformat()
    bars = api.bars_between("QQQ", "1Min", lo, hi)
    if bars:
        move = bars[-1]["c"] / bars[0]["o"] - 1
        right = {"bull": move > 0, "bear": move < 0}.get(bias)
        rows.append({"date": today.isoformat(), "bias": bias, "qqq_move": f"{move:.4f}",
                     "correct": "" if right is None else str(right).lower()})
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "bias", "qqq_move", "correct"])
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: r["date"]))
    else:
        rows = read_csv(path)
    calls = [r for r in rows if r["correct"]]
    hits = sum(1 for r in calls if r["correct"] == "true")
    lines = ["", "## Claude's direction calls (scalp_bias vs QQQ 9:35-15:15)",
             "| day | bias | QQQ move | right? |", "|---|---|---|---|"]
    lines += [f"| {r['date']} | {r['bias']} | {float(r['qqq_move']):+.2%} | {r['correct'] or '-'} |"
              for r in rows[-10:]]
    lines.append(f"\nBull/bear calls: {hits} of {len(calls)} right." if calls else "\nNo bull/bear calls scored yet.")
    return lines


# the bot vs the S&P 500
def benchmark(api, cfg, today, root=ROOT):
    """Compare the account with the same money put in SPY when the bot went live.
    Logs one row per day to research/benchmark.csv; returns the scorecard lines."""
    b = cfg.get("benchmark") or {}
    if not b.get("since") or not b.get("start_equity"):
        return []
    path = root / "research" / "benchmark.csv"
    rows = [r for r in read_csv(path) if r["date"] != today.isoformat()]
    since = datetime.fromisoformat(b["since"].replace("Z", "+00:00"))
    start_bars = api.bars_between("SPY", "1Min", since.isoformat(), (since + timedelta(minutes=30)).isoformat())
    if not start_bars:
        return ["", "## Bot vs S&P 500", "No SPY price found for the start date."]
    start, spy_start = float(b["start_equity"]), start_bars[0]["o"]
    equity, spy_now = float(api.account()["equity"]), api.last_price("SPY")
    spy_value = start * spy_now / spy_start
    rows.append({"date": today.isoformat(), "bot": f"{equity:.2f}", "sp500": f"{spy_value:.2f}"})
    rows.sort(key=lambda r: r["date"])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "bot", "sp500"])
        w.writeheader()
        w.writerows(rows)
    lines = ["", f"## Bot vs S&P 500 (${start:.0f} since {since.astimezone(ET):%Y-%m-%d %H:%M} ET)",
             f"**Bot ${equity:.2f} ({equity / start - 1:+.2%}) vs S&P 500 ${spy_value:.2f} "
             f"({spy_value / start - 1:+.2%}): the bot is {'ahead' if equity >= spy_value else 'behind'} "
             f"by ${abs(equity - spy_value):.2f}.**",
             "", "| day | bot $ | $ in S&P 500 (SPY) |", "|---|---|---|"]
    lines += [f"| {r['date']} | {r['bot']} | {r['sp500']} |" for r in rows[-10:]]
    lines.append("(Deposits or withdrawals would distort this; reset benchmark.since in config.json after one.)")
    return lines


# run
def load_sessions(api, symbols, start_et, today):
    """Last LOOKBACK full sessions of 1-minute bars per symbol, from start_et to 15:50 ET."""
    begin = (today - timedelta(days=LOOKBACK * 2 + 4)).isoformat()
    cal = [d for d in api.calendar(begin, today.isoformat()) if d["date"] <= today.isoformat()]
    dates = [d["date"] for d in cal][-LOOKBACK:]
    sessions = {}
    for sym in symbols:
        sessions[sym] = []
        for d in dates:
            day = datetime.fromisoformat(d).date()
            lo = datetime.combine(day, start_et, ET)
            hi = datetime.combine(day, dtime(15, 50), ET)
            bars = api.bars_between(sym, "1Min", lo.astimezone(timezone.utc).isoformat(),
                                    hi.astimezone(timezone.utc).isoformat())
            if bars:
                sessions[sym].append(bars)
    return sessions


def log_changes(path, today, old, new, reason):
    new_file = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["date", "setting", "old", "new", "reason"])
        for k in KNOBS + ["enabled_symbols"]:
            if old.get(k) != new.get(k):
                w.writerow([today, k, old.get(k), new.get(k), reason])


def run(api, cfg, today, root=ROOT):
    sc = cfg["scalper"]
    current = tuning.scalper_config(cfg, root / "tuning.json")
    current_syms = current.get("enabled_symbols") or sc["symbols"]
    tuned = tuning.load(root / "tuning.json")
    if tuned.get("updated") == today.isoformat():
        log("Already learned today.")
        return "already-done"
    lines = [*scorecard(today.isoformat(), root)[:1], *benchmark(api, cfg, today, root),
             *scorecard(today.isoformat(), root)[1:]]
    lines += score_direction(api, today, root)
    lines += ["", "## Tuner"]
    if not cfg.get("learning", True):
        lines.append("Learning is off in config.json; nothing changed.")
    else:
        start_et = datetime.strptime(sc["start_et"], "%H:%M").time()
        sessions = load_sessions(api, sc["symbols"], start_et, today)
        days = min((len(v) for v in sessions.values()), default=0)
        if days < 4:
            lines.append(f"Only {days} sessions of data; need 4. Nothing changed.")
        else:
            base, best = choose(sessions, current, current_syms, sc["symbols"])
            lines.append(f"Replayed {days} sessions. Current settings: {base[0]:+.2%} / {base[1]:+.2%} "
                         f"of trade size (earlier / later half, after {COST:.2%} costs per trade).")
            if best:
                p, syms, (a, b), n = best
                new = {**p, "enabled_symbols": syms}
                old = {k: current.get(k) for k in KNOBS} | {"enabled_symbols": current_syms}
                reason = (f"replay of {days} sessions: {a:+.2%}/{b:+.2%} vs current "
                          f"{base[0]:+.2%}/{base[1]:+.2%} ({n} trades)")
                log_changes(root / "research" / "tuning_log.csv", today.isoformat(), old, new, reason)
                tuned = {"scalper": new}
                lines.append(f"Changed to {json.dumps(new)} because {reason}.")
            else:
                lines.append("No setting beat the current one in both halves by enough; kept it.")
    tuned["updated"] = today.isoformat()
    (root / "tuning.json").write_text(json.dumps(tuned, indent=2) + "\n")
    (root / "research" / "scorecard.md").write_text("\n".join(lines) + "\n")
    for line in lines[-3:]:
        log(line)
    return "done"


def main():
    cfg = load_config()
    api = make_client(cfg)
    log(f"Result: {run(api, cfg, datetime.now(ET).date())}")


if __name__ == "__main__":
    main()
