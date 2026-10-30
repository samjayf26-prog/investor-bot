"""Download the daily bars the independent review needs and save them as CSV (market data only).

Runs on GitHub Actions (the review's cloud environment cannot reach market-data hosts). Each file
keeps Yahoo's unadjusted open/high/low/close plus the adjusted close, so the review can redo the
adjustments itself. Stooq is the fallback for the ETFs and indexes.
"""
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
SYMS = ["SPY", "QQQ", "TQQQ", "QLD", "SQQQ", "SSO", "^NDX", "^GSPC", "^IRX"]
STOOQ = {"SPY": "spy.us", "QQQ": "qqq.us", "TQQQ": "tqqq.us", "QLD": "qld.us", "SQQQ": "sqqq.us",
         "SSO": "sso.us", "^NDX": "^ndx", "^GSPC": "^spx"}


def flat(df):
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def yahoo(sym):
    import yfinance as yf
    raw = yf.download(sym, start="1985-01-01", auto_adjust=False, actions=False, progress=False,
                      threads=False)
    df = flat(raw).dropna(subset=["close"])
    if len(df) < 200:
        raise ValueError(f"yahoo returned {len(df)} rows for {sym}")
    if "adj_close" not in df.columns:
        df["adj_close"] = df["close"]
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    return df[["open", "high", "low", "close", "adj_close", "volume"]].sort_index()


def stooq(sym):
    r = requests.get(f"https://stooq.com/q/d/l/?s={STOOQ[sym]}&i=d", timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if "Close" not in df.columns or len(df) < 200:
        raise ValueError(f"stooq returned no data for {sym}: {r.text[:80]!r}")
    df = flat(df)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df["adj_close"] = df["close"]
    if "volume" not in df:
        df["volume"] = 0
    return df[["open", "high", "low", "close", "adj_close", "volume"]]


def main():
    ok = []
    for s in SYMS:
        for name, fn in (("yahoo", yahoo), ("stooq", stooq)):
            if name == "stooq" and s not in STOOQ:
                continue
            try:
                df = fn(s)
                df.round(6).to_csv(OUT / f"{s.replace('^', 'IDX_')}.csv")
                print(f"{s}: {name} {df.index[0].date()}..{df.index[-1].date()} ({len(df)} rows)")
                ok.append(s)
                break
            except Exception as e:  # noqa: BLE001
                print(f"{name} {s}: {e}")
        time.sleep(1)
    missing = [s for s in SYMS if s not in ok]
    print("missing:", missing or "none")
    if any(s in missing for s in ("SPY", "QQQ", "TQQQ")):
        sys.exit(1)


if __name__ == "__main__":
    main()
