"""Does buying a mega-cap after big news pay? Event study over ~5 years of daily bars.

    python review/megacap_test.py

Event: a stock opens 3%+ above (or below) its previous close, i.e. news broke before
the open. Buy (or, for down gaps, the bearish side) at that day's open, the earliest
the bot could act, and measure the return over the same day, 5 and 10 trading days,
minus SPY over the same span. Market data only.
"""
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.alpaca import Alpaca  # noqa: E402
from bot.trader import ET, ROOT  # noqa: E402

MEGA = ["TSLA", "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AVGO", "AMD", "NFLX",
        "ORCL", "CRM", "ADBE", "INTC", "MU", "PLTR", "COIN", "UBER", "JPM", "LLY"]
GAP = 0.03


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


def stats(xs):
    n = len(xs)
    if n < 2:
        return n, 0.0, 0.0, 0.0
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) or 1e-12
    return n, m, m / sd * math.sqrt(n), sum(x > 0 for x in xs) / n


def main():
    api = Alpaca.from_env(False)
    today = datetime.now(ET).date()
    start, end = (today - timedelta(days=365 * 5)).isoformat(), (today - timedelta(days=1)).isoformat()
    spy = {b["t"][:10]: b for b in daily(api, "SPY", start, end)}
    res = {(d, h): [] for d in ("up", "down") for h in (0, 5, 10)}
    for sym in MEGA:
        bars = daily(api, sym, start, end)
        for i in range(1, len(bars) - 10):
            gap = bars[i]["o"] / bars[i - 1]["c"] - 1
            if abs(gap) < GAP:
                continue
            side = "up" if gap > 0 else "down"
            d0 = bars[i]["t"][:10]
            for h in (0, 5, 10):
                dh = bars[i + h]["t"][:10]
                if d0 not in spy or dh not in spy:
                    continue
                r = bars[i + h]["c"] / bars[i]["o"] - 1
                m = spy[dh]["c"] / spy[d0]["o"] - 1
                ex = (r - m) if side == "up" else (m - r)  # return of trading in the news direction
                res[(side, h)].append(ex)
    lines = [f"# Buying mega-caps after big news ({start} to {end})", "",
             f"Stocks: {', '.join(MEGA)}. Event: opened {GAP:.0%}+ away from the previous close. "
             "Trade in the news direction from that day's open; returns are vs SPY over the same "
             "span (positive = the news kept paying after the open). t of about 2+ is unlikely to be luck.", "",
             "| news | hold | events | avg vs SPY | t | share that paid |", "|---|---|---|---|---|---|"]
    for (side, h), xs in res.items():
        n, m, t, w = stats(xs)
        hold = "same day (open to close)" if h == 0 else f"open to close {h} trading days later"
        lines.append(f"| gap {side} | {hold} | {n} | {m:+.2%} | {t:+.2f} | {w:.0%} |")
    text = "\n".join(lines) + "\n"
    print(text)
    (ROOT / "review" / "megacap-results.md").write_text(text)


if __name__ == "__main__":
    main()
