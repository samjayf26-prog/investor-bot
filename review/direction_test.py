"""Do simple tape rules call the rest of the day's direction better than a coin flip?

    python review/direction_test.py [sessions]

For each session and decision time (the research run times), each rule says bull or
bear. The trade is $30 of TQQQ (bull) or SQQQ (bear) from the decision bar's close to
the 15:30 ET bar's close, which is how a same-day pick works. Market data only.
"""
import math
import sys
from collections import defaultdict
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.alpaca import Alpaca  # noqa: E402
from bot.trader import ET, ROOT  # noqa: E402

STAKE = 30.0
TIMES = [dtime(10, 0), dtime(10, 20), dtime(11, 20), dtime(13, 20)]
EXIT = dtime(15, 30)


def by_day(api, sym, dates):
    lo = datetime.combine(datetime.fromisoformat(dates[0]).date(), dtime(9, 30), ET).astimezone(timezone.utc)
    hi = datetime.combine(datetime.fromisoformat(dates[-1]).date(), dtime(16, 0), ET).astimezone(timezone.utc)
    out = defaultdict(dict)
    for b in api.bars_between(sym, "1Min", lo.isoformat(), hi.isoformat(), feed="sip"):
        t = datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
        if dtime(9, 30) <= t.time() < dtime(16, 0):
            out[t.date().isoformat()][t.time()] = b
    return out


def at(day, t):
    """The last bar at or before t (bars can be missing)."""
    keys = [k for k in day if k <= t]
    return day[max(keys)] if keys else None


def stats(rs):
    n = len(rs)
    if n < 2:
        return n, 0, 0, 0
    m = sum(rs) / n
    sd = math.sqrt(sum((r - m) ** 2 for r in rs) / (n - 1)) or 1e-12
    return n, sum(1 for r in rs if r > 0) / n, m, m / sd * math.sqrt(n)


def main():
    nsess = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    api = Alpaca.from_env(False)
    today = datetime.now(ET).date()
    cal = api.calendar((today - timedelta(days=int(nsess * 1.6))).isoformat(), (today - timedelta(days=1)).isoformat())
    dates = [d["date"] for d in cal][-(nsess + 1):]
    data = {s: by_day(api, s, dates) for s in ("QQQ", "TQQQ", "SQQQ")}
    rules = defaultdict(list)  # (rule, time) -> [(date, trade return, qqq right?)]
    for k in range(1, len(dates)):
        d, prev = dates[k], dates[k - 1]
        q, qp = data["QQQ"].get(d), data["QQQ"].get(prev)
        if not q or not qp or dtime(9, 30) not in q:
            continue
        o, pc = q[dtime(9, 30)]["o"], at(qp, dtime(15, 59))["c"]
        prev_ret = pc / qp[min(qp)]["o"] - 1
        x = at(q, EXIT)
        for t in TIMES:
            b = at(q, t)
            if not b or not x:
                continue
            seen = [v for kk, v in q.items() if kk <= t]
            vwap = sum(v["vw"] * v["v"] for v in seen) / max(1, sum(v["v"] for v in seen))
            later = x["c"] / b["c"] - 1
            sig = {
                "tape: QQQ above/below open": b["c"] > o,
                "tape: above/below VWAP": b["c"] > vwap,
                "fade: against the open-to-now move": b["c"] < o,
                "gap: follow the overnight gap": o > pc,
                "gap: fade the overnight gap": o < pc,
                "yesterday: follow": prev_ret > 0,
                "yesterday: reverse": prev_ret < 0,
                "always bull (TQQQ)": True,
                "always bear (SQQQ)": False,
            }
            both = (b["c"] > o) == (b["c"] > vwap)
            sig_agree = b["c"] > o if both else None
            for name, bull in list(sig.items()) + [("tape: open AND VWAP agree (else no trade)", sig_agree)]:
                if bull is None:
                    continue
                etf = data["TQQQ" if bull else "SQQQ"].get(d)
                e1, e2 = (at(etf, t), at(etf, EXIT)) if etf else (None, None)
                if not e1 or not e2:
                    continue
                rules[(name, t)].append((d, e2["c"] / e1["c"] - 1, (later > 0) == bull))
    out = [f"# Same-day direction rules on QQQ ({dates[1]} to {dates[-1]}, {len(dates) - 1} sessions, SIP)", "",
           f"Trade: ${STAKE:.0f} of TQQQ (bull) or SQQQ (bear) from the decision time to 15:30 ET. "
           "t = t-statistic of the mean daily return (about 2 or more is unlikely to be luck; "
           "with ~40 rule/time combinations, expect one or two to reach 2 by chance). "
           "Halves = $ in the earlier / later half of the period.", ""]
    for t in TIMES:
        out += [f"## Decision at {t.strftime('%H:%M')} ET", "",
                "| rule | days | QQQ direction right | trade win rate | mean % | t | total $ | halves $ |",
                "|---|---|---|---|---|---|---|---|"]
        for (name, tt), rows in rules.items():
            if tt != t:
                continue
            rs = [r for _, r, _ in rows]
            n, win, m, tstat = stats(rs)
            right = sum(1 for *_, ok in rows if ok) / max(1, n)
            h = n // 2
            out.append(f"| {name} | {n} | {right:.0%} | {win:.0%} | {m * 100:+.3f}% | {tstat:+.2f} | "
                       f"{sum(rs) * STAKE:+.2f} | {sum(rs[:h]) * STAKE:+.2f} / {sum(rs[h:]) * STAKE:+.2f} |")
        out.append("")
    text = "\n".join(out)
    print(text)
    (ROOT / "review" / "direction-results.md").write_text(text + "\n")


if __name__ == "__main__":
    main()
