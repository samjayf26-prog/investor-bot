"""Upper bound for a research-steered scalper: replay the scalper as if Claude's daily
scalp_bias were always right (hindsight: bull on days QQQ rose 9:35-15:15, bear/SQQQ on
days it fell). If even perfect daily calls can't beat costs, real calls can't either.

    python review/bias_test.py [sessions]
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt  # noqa: E402

learn, tuning = bt.learn, bt.tuning


def main():
    nsess = int(sys.argv[1]) if len(sys.argv) > 1 else 70
    cfg = bt.load_config()
    api = bt.Alpaca.from_env(False)
    today = datetime.now(bt.ET).date()
    cal = api.calendar((today - timedelta(days=nsess * 2)).isoformat(), (today - timedelta(days=1)).isoformat())
    dates = [d["date"] for d in cal][-nsess:]
    sessions = bt.fetch(api, dates, "sip")
    sc = cfg["scalper"]
    tuned = tuning.apply(sc, tuning.load(bt.ROOT / "tuning.json"))
    out = [f"# Perfect-direction scalper ({dates[0]} to {dates[-1]}, {len(dates)} sessions, SIP)", "",
           "| settings | cost | policy | trades | P&L $ at $15/trade | per trade % |", "|---|---|---|---|---|---|"]
    settings = {"current tuning.json": {k: tuned[k] for k in learn.KNOBS}}
    for cost in (0.0, learn.COST):
        rows = []
        for p in learn.combos():
            cache, tot, n = {}, 0.0, 0
            for i in range(len(dates)):
                q = sessions["QQQ"][i]
                if len(q) < 30:
                    continue
                syms = sc["bull_symbols"] if q[-1]["c"] > q[0]["o"] else sc["bear_symbols"]
                r, k = bt.day_returns(sessions, i, p, syms, cache, cost)
                tot, n = tot + r, n + k
            rows.append((tot, n, p))
        rows.sort(key=lambda r: r[0])
        best = rows[-1]
        pos = sum(1 for r in rows if r[0] > 0)
        cur = next(r for r in rows if all(r[2][k] == settings["current tuning.json"][k] for k in learn.KNOBS)) \
            if any(all(r[2][k] == settings["current tuning.json"][k] for k in learn.KNOBS) for r in rows) else None
        for name, r in (("best of 300 (hindsight)", best), ("current tuning.json", cur)):
            if r:
                out.append(f"| {name} | {cost:.2%} | perfect daily bias | {r[1]} | {r[0] * bt.NOTIONAL:+.2f} | "
                           f"{(r[0] / r[1] * 100 if r[1] else 0):+.4f}% |")
        out.append(f"| all 300 | {cost:.2%} | perfect daily bias | | {pos} of 300 made money | |")
    # buy-and-hold the right side with $30 (the scalper's max capital) for comparison
    hold = 0.0
    for i in range(len(dates)):
        q = sessions["QQQ"][i]
        if len(q) < 30:
            continue
        sym = "TQQQ" if q[-1]["c"] > q[0]["o"] else "SQQQ"
        b = sessions[sym][i]
        hold += 30 * (b[-1]["c"] / b[0]["o"] - 1)
    out += ["", f"For scale: simply holding the right 3x ETF (TQQQ up days, SQQQ down days) with $30, "
            f"9:35-15:15, one trade a day: {hold:+.2f} $ over {len(dates)} sessions."]
    text = "\n".join(out) + "\n"
    print(text)
    (bt.ROOT / "review" / "bias-results.md").write_text(text)


if __name__ == "__main__":
    main()
