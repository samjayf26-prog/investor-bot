"""Overnight vs daytime returns, and how noisy the first half hour is.

    python review/overnight_test.py

Daily bars (SIP, split/dividend adjusted) for SPY and QQQ over ~5 years: overnight =
previous close to open, daytime = open to close. Then 1-minute bars over the last 250
sessions: the typical size of the move in each half hour, to show how much of the day's
noise lands in the first 30 minutes when the bot buys. Market data only.
"""
import math
import sys
from collections import defaultdict
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.alpaca import Alpaca  # noqa: E402
from bot.trader import ET, ROOT  # noqa: E402


def daily(api, sym, start, end):
    out, token = [], None
    while True:
        p = {"timeframe": "1Day", "start": start, "end": end, "feed": "sip", "limit": 10000, "adjustment": "all"}
        if token:
            p["page_token"] = token
        page = api._req("GET", f"https://data.alpaca.markets/v2/stocks/{sym}/bars", p)
        out += page.get("bars") or []
        token = page.get("next_page_token")
        if not token:
            return out


def main():
    api = Alpaca.from_env(False)
    today = datetime.now(ET).date()
    lines = ["# Overnight vs daytime", ""]
    for years in (5, 1):
        start = (today - timedelta(days=365 * years)).isoformat()
        lines += [f"## Last {years} year(s), daily bars", "",
                  "| ETF | days | overnight total | daytime total | overnight up-share | mean overnight | mean daytime |",
                  "|---|---|---|---|---|---|---|"]
        for sym in ("SPY", "QQQ"):
            bars = daily(api, sym, start, (today - timedelta(days=1)).isoformat())
            on = [bars[i]["o"] / bars[i - 1]["c"] - 1 for i in range(1, len(bars))]
            dy = [b["c"] / b["o"] - 1 for b in bars[1:]]
            tot = lambda rs: math.prod(1 + r for r in rs) - 1  # noqa: E731
            lines.append(f"| {sym} | {len(on)} | {tot(on):+.1%} | {tot(dy):+.1%} | "
                         f"{sum(r > 0 for r in on) / len(on):.0%} | {sum(on) / len(on):+.3%} | {sum(dy) / len(dy):+.3%} |")
        lines.append("")
    # half-hour noise over the last 250 sessions
    lo = datetime.combine(today - timedelta(days=370), dtime(9, 30), ET).astimezone(timezone.utc).isoformat()
    hi = datetime.combine(today - timedelta(days=1), dtime(16, 0), ET).astimezone(timezone.utc).isoformat()
    lines += ["## Size of the move in each half hour (QQQ, 1-min bars, last ~250 sessions)", "",
              "Average absolute % move from the start to the end of each half hour. Bigger = a buy in that "
              "window lands at a more random price.", "", "| window ET | avg abs move |", "|---|---|"]
    bars = api.bars_between("QQQ", "1Min", lo, hi, feed="sip")
    days = defaultdict(dict)
    for b in bars:
        t = datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
        days[t.date()][t.time()] = b
    slots = [dtime(9 + (30 + 30 * k) // 60, (30 + 30 * k) % 60) for k in range(13)]
    for a, b in zip(slots, slots[1:]):
        moves = []
        for d in days.values():
            ka = [k for k in d if a <= k < b]
            if ka:
                moves.append(abs(d[max(ka)]["c"] / d[min(ka)]["o"] - 1))
        if moves:
            lines.append(f"| {a.strftime('%H:%M')}-{b.strftime('%H:%M')} | {sum(moves) / len(moves):.2%} |")
    text = "\n".join(lines) + "\n"
    print(text)
    (ROOT / "review" / "overnight-results.md").write_text(text)


if __name__ == "__main__":
    main()
