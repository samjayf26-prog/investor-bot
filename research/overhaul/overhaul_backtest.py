"""Profit-overhaul evidence: real-data backtests for the redesign of investor-bot.

    python research/overhaul/overhaul_backtest.py

Runs on GitHub Actions (this cloud env blocks market-data hosts). Market data only; places no
orders. Daily data comes from Yahoo Finance (yfinance), falling back to Stooq, then Alpaca
(paper keys, data only). Minute data (optional) comes from Alpaca.

Sections
  1. Overnight vs intraday returns, SPY/QQQ, by year and by half (long sample).
  2. Core strategies on daily data since 2011 (TQQQ era): buy-and-hold, overnight-only,
     trend (200-day SMA) and volatility filters, with trading costs.
  3. Calendar: turn-of-the-month days vs other days.
  4. Short-term mean reversion (dip buying) on QQQ with TQQQ.
  5. ETF momentum rotation (monthly).
  6. News-gap event study on ~150 large/mid caps: buy at the open vs after the gap held,
     holding 5/10/20 days, stops and targets, gap size buckets, and bad-news gaps.
  7. (Alpaca minute bars) cost of the bot's run times: 9:35/9:50 vs the open, 15:50 vs the close.
Writes research/overhaul/results.md and research/overhaul/yearly.csv.
"""
import io
import json
import math
import os
import sys
import time
import traceback
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

START = "2000-01-01"
CORE_START = "2011-01-03"      # TQQQ has traded since Feb 2010; a common sample for all core tests
COST = {"SPY": 0.0001, "QQQ": 0.0001, "TQQQ": 0.0003, "QLD": 0.0003, "SSO": 0.0003, "UPRO": 0.0003,
        "SQQQ": 0.0003, "TLT": 0.0002, "IWM": 0.0001, "EFA": 0.0002, "EEM": 0.0002, "GLD": 0.0001}
LINES = []
SOURCES = {}


def say(*parts):
    line = " ".join(str(p) for p in parts)
    LINES.append(line)
    print(line, flush=True)


# ----------------------------------------------------------------------------- data
def _flatten(df):
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.columns = [str(c).lower() for c in df.columns]
    return df


def _from_yahoo_frame(df):
    df = _flatten(df).dropna(subset=["open", "close"])
    if "adj close" not in df.columns:
        df["adj close"] = df["close"]
    f = df["adj close"] / df["close"]
    out = pd.DataFrame({"open": df["open"] * f, "high": df["high"] * f, "low": df["low"] * f,
                        "close": df["adj close"], "raw_close": df["close"]})
    out.index = pd.to_datetime(out.index).tz_localize(None).normalize()
    return out[~out.index.duplicated()].sort_index()


def yahoo_many(symbols, start):
    """One batched download; returns {sym: frame} for the symbols that came back."""
    import yfinance as yf
    out = {}
    for i in range(0, len(symbols), 40):
        chunk = symbols[i:i + 40]
        try:
            raw = yf.download(chunk, start=start, auto_adjust=False, actions=False, progress=False,
                              threads=True, group_by="ticker")
        except Exception as e:  # noqa: BLE001
            print(f"yahoo batch failed: {e}")
            continue
        for s in chunk:
            try:
                df = raw[s] if isinstance(raw.columns, pd.MultiIndex) else raw
                df = df.dropna(how="all")
                if len(df) > 100:
                    out[s] = _from_yahoo_frame(df)
            except Exception as e:  # noqa: BLE001
                print(f"yahoo {s}: {e}")
        time.sleep(1)
    return out


def stooq(sym, start):
    import requests
    s = sym.lower().replace(".", "-")
    r = requests.get(f"https://stooq.com/q/d/l/?s={s}.us&i=d", timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if "Close" not in df.columns or len(df) < 100:
        raise ValueError(f"stooq returned no data for {sym}: {r.text[:80]!r}")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    df = df[df.index >= pd.Timestamp(start)]
    return pd.DataFrame({"open": df["Open"], "high": df["High"], "low": df["Low"], "close": df["Close"],
                         "raw_close": df["Close"]})


def alpaca_daily(sym, start):
    from bot.alpaca import Alpaca
    api = Alpaca.from_env(False)
    start = max(pd.Timestamp(start), pd.Timestamp("2016-01-01")).date().isoformat()
    end = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    out, token = [], None
    while True:
        p = {"timeframe": "1Day", "start": start, "end": end, "feed": "sip", "limit": 10000, "adjustment": "all"}
        if token:
            p["page_token"] = token
        page = api._req("GET", f"https://data.alpaca.markets/v2/stocks/{sym}/bars", p)
        out += page.get("bars") or []
        token = page.get("next_page_token")
        if not token:
            break
    if not out:
        raise ValueError(f"alpaca returned no bars for {sym}")
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df["t"]).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return pd.DataFrame({"open": df["o"], "high": df["h"], "low": df["l"], "close": df["c"], "raw_close": df["c"]})


def load_all(symbols, start=START):
    data = {}
    try:
        data = yahoo_many(symbols, start)
        for s in data:
            SOURCES[s] = "yahoo"
    except Exception as e:  # noqa: BLE001
        print(f"yahoo unavailable: {e}")
    for s in symbols:
        if s in data:
            continue
        for name, fn in (("stooq", stooq), ("alpaca", alpaca_daily)):
            try:
                data[s] = fn(s, start)
                SOURCES[s] = name
                break
            except Exception as e:  # noqa: BLE001
                print(f"{name} {s}: {e}")
    return data


# ----------------------------------------------------------------------------- metrics
def metrics(r, name, dollars=75.0):
    r = r.dropna()
    if len(r) < 50:
        return None
    eq = (1 + r).cumprod()
    years = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = r.std() * math.sqrt(252)
    sharpe = r.mean() / r.std() * math.sqrt(252) if r.std() > 0 else 0
    dd = (eq / eq.cummax() - 1)
    yearly = eq.groupby(eq.index.year).last()
    yearly = yearly / yearly.shift(1).fillna(1.0) - 1
    half = len(r) // 2
    c1 = (1 + r.iloc[:half]).prod() ** (252 / half) - 1
    c2 = (1 + r.iloc[half:]).prod() ** (252 / (len(r) - half)) - 1
    last = {}
    for lab, days in (("1y", 252), ("3y", 756), ("5y", 1260)):
        if len(r) > days:
            last[lab] = (1 + r.iloc[-days:]).prod() - 1
    return {"name": name, "years": years, "cagr": cagr, "vol": vol, "sharpe": sharpe, "mdd": dd.min(),
            "worst_day": r.min(), "best_day": r.max(), "pos_years": float((yearly > 0).mean()),
            "half1": c1, "half2": c2, "end75": dollars * eq.iloc[-1], "yearly": yearly, "last": last,
            "worst_year": yearly.min(), "worst_year_lab": int(yearly.idxmin())}


def table(rows, title, note=None):
    say("", f"### {title}", "")
    if note:
        say(note, "")
    say("| strategy | CAGR | vol | Sharpe | max DD | worst day | worst year | 1st half CAGR | 2nd half CAGR | $75 becomes | last 1y | last 3y |")
    say("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in rows:
        if not m:
            continue
        say(f"| {m['name']} | {m['cagr']:+.1%} | {m['vol']:.0%} | {m['sharpe']:.2f} | {m['mdd']:.0%} | {m['worst_day']:+.1%} | "
            f"{m['worst_year']:+.0%} ({m['worst_year_lab']}) | {m['half1']:+.1%} | {m['half2']:+.1%} | ${m['end75']:,.0f} | "
            f"{m['last'].get('1y', float('nan')):+.1%} | {m['last'].get('3y', float('nan')):+.1%} |")


def yearly_table(rows, title):
    rows = [m for m in rows if m]
    years = sorted({y for m in rows for y in m["yearly"].index})
    say("", f"### {title}: calendar-year returns", "")
    say("| year | " + " | ".join(m["name"] for m in rows) + " |")
    say("|---|" + "---|" * len(rows))
    for y in years:
        say(f"| {y} | " + " | ".join(f"{m['yearly'].get(y, float('nan')):+.0%}" for m in rows) + " |")
    return pd.DataFrame({m["name"]: m["yearly"] for m in rows})


def tstat(xs):
    xs = np.asarray([x for x in xs if np.isfinite(x)], dtype=float)
    n = len(xs)
    if n < 3:
        return n, float("nan"), float("nan"), float("nan")
    m, sd = xs.mean(), xs.std(ddof=1)
    return n, m, (m / sd * math.sqrt(n)) if sd > 0 else float("nan"), float((xs > 0).mean())


# ----------------------------------------------------------------------------- 1. overnight vs intraday
def overnight_section(data):
    say("", "## 1. Overnight (close to next open) vs intraday (open to close)", "",
        "Total-return adjusted daily bars (dividends land in the overnight leg). "
        "This extends review/overnight-results.md (which used 1 and 5 years) to the full sample.", "")
    say("| ETF | period | days | overnight total | intraday total | overnight CAGR | intraday CAGR | nights up | mean night | mean day | night vol | day vol |")
    say("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sym in ("SPY", "QQQ"):
        df = data.get(sym)
        if df is None:
            continue
        on = df["open"] / df["close"].shift(1) - 1
        dy = df["close"] / df["open"] - 1
        periods = [("2000-2010", "2000-01-01", "2010-12-31"), ("2011-2018", "2011-01-01", "2018-12-31"),
                   ("2019-now", "2019-01-01", "2100-01-01"), ("last 1y", df.index[-252], "2100-01-01"),
                   ("full", "2000-01-01", "2100-01-01")]
        for lab, a, b in periods:
            o = on[(on.index >= pd.Timestamp(a)) & (on.index <= pd.Timestamp(b))].dropna()
            d = dy.reindex(o.index).dropna()
            if len(o) < 100:
                continue
            yrs = len(o) / 252
            tot_o, tot_d = (1 + o).prod() - 1, (1 + d).prod() - 1
            say(f"| {sym} | {lab} | {len(o)} | {tot_o:+.1%} | {tot_d:+.1%} | {(1 + tot_o) ** (1 / yrs) - 1:+.1%} | "
                f"{(1 + tot_d) ** (1 / yrs) - 1:+.1%} | {(o > 0).mean():.0%} | {o.mean():+.3%} | {d.mean():+.3%} | "
                f"{o.std() * math.sqrt(252):.0%} | {d.std() * math.sqrt(252):.0%} |")
    # by year for QQQ and TQQQ: did the pattern hold every year?
    say("", "Year by year, QQQ and TQQQ (TQQQ from 2011):", "")
    say("| year | QQQ overnight | QQQ intraday | TQQQ overnight | TQQQ intraday | TQQQ close-to-close |")
    say("|---|---|---|---|---|---|")
    q, t = data.get("QQQ"), data.get("TQQQ")
    if q is not None and t is not None:
        for y in range(2011, datetime.now().year + 1):
            qq, tt = q[q.index.year == y], t[t.index.year == y]
            if len(qq) < 20 or len(tt) < 20:
                continue
            prevq = q["close"].shift(1).reindex(qq.index)
            prevt = t["close"].shift(1).reindex(tt.index)
            qo, qd = (qq["open"] / prevq - 1).dropna(), (qq["close"] / qq["open"] - 1)
            to, td = (tt["open"] / prevt - 1).dropna(), (tt["close"] / tt["open"] - 1)
            tcc = (tt["close"] / prevt - 1).dropna()
            say(f"| {y} | {(1 + qo).prod() - 1:+.0%} | {(1 + qd).prod() - 1:+.0%} | {(1 + to).prod() - 1:+.0%} | "
                f"{(1 + td).prod() - 1:+.0%} | {(1 + tcc).prod() - 1:+.0%} |")
    # overnight after an up day vs a down day
    if q is not None:
        on = (q["open"] / q["close"].shift(1) - 1)
        prev_day = (q["close"] / q["close"].shift(1) - 1).shift(1)
        sub = pd.DataFrame({"on": on, "prev": prev_day}).dropna()
        sub = sub[sub.index >= pd.Timestamp(CORE_START)]
        say("", "QQQ overnight return conditional on the previous session (since 2011):", "")
        say("| previous close-to-close | nights | mean overnight | nights up | total |")
        say("|---|---|---|---|---|")
        for lab, mask in (("down 1%+", sub["prev"] <= -0.01), ("down 0-1%", (sub["prev"] < 0) & (sub["prev"] > -0.01)),
                          ("up 0-1%", (sub["prev"] >= 0) & (sub["prev"] < 0.01)), ("up 1%+", sub["prev"] >= 0.01)):
            o = sub.loc[mask, "on"]
            say(f"| {lab} | {len(o)} | {o.mean():+.3%} | {(o > 0).mean():.0%} | {(1 + o).prod() - 1:+.0%} |")


# ----------------------------------------------------------------------------- 2. core strategies
def core_section(data):
    say("", "## 2. What to do with the idle cash (the 'core'), daily data since 2011", "",
        "All strategies trade at the official open/close (section 7 measures the cost of the bot's "
        "real run times). Costs: one-way spread+slippage per trade of 0.01% (SPY/QQQ), 0.03% (3x ETFs), "
        "0.02% (TLT), charged on every position change; the overnight-only strategies pay a round trip "
        "every day. Sharpe uses a 0% cash rate. 'worst year' is the worst calendar year. Dividends "
        "included; TQQQ's fees and financing are in its prices. No taxes.", "")
    need = ["SPY", "QQQ", "TQQQ", "QLD", "TLT"]
    if any(data.get(s) is None for s in need):
        say(f"Missing data for {[s for s in need if data.get(s) is None]}; section skipped.")
        return []
    idx = data["TQQQ"].index
    idx = idx[idx >= pd.Timestamp(CORE_START)]
    D = {s: data[s].reindex(idx).ffill() for s in need}
    on = {s: (D[s]["open"] / D[s]["close"].shift(1) - 1) for s in need}      # overnight leg
    cc = {s: (D[s]["close"] / D[s]["close"].shift(1) - 1) for s in need}     # full day
    q = data["QQQ"]["close"]
    sma200 = q.rolling(200).mean().reindex(idx)
    trend = (q.reindex(idx) > sma200).shift(1).fillna(False).astype(bool)     # known at the prior close
    rv20 = (q.pct_change().rolling(20).std() * math.sqrt(252)).reindex(idx).shift(1)
    rows = []

    def bh(sym):
        return cc[sym].fillna(0)

    def overnight(sym, w=None):
        w = pd.Series(1.0, index=idx) if w is None else w
        return (w * on[sym] - w * 2 * COST[sym]).fillna(0)

    def switching(weights, syms):
        """weights: {sym: Series of weight held over day t (set at close t-1)}; charges turnover."""
        r = pd.Series(0.0, index=idx)
        for s in syms:
            w = weights[s].fillna(0)
            r += w * cc[s].fillna(0) - (w - w.shift(1).fillna(0)).abs() * COST[s]
        return r

    rows.append(metrics(bh("SPY"), "SPY buy & hold (today's core)"))
    rows.append(metrics(bh("QQQ"), "QQQ buy & hold"))
    rows.append(metrics(bh("TQQQ"), "TQQQ buy & hold"))
    rows.append(metrics(overnight("SPY"), "SPY overnight only"))
    rows.append(metrics(overnight("QQQ"), "QQQ overnight only"))
    rows.append(metrics(overnight("QLD"), "QLD (2x) overnight only"))
    rows.append(metrics(overnight("TQQQ"), "TQQQ overnight only"))
    # trend filter: TQQQ overnight when QQQ > 200d SMA, else SPY overnight / cash
    w = trend.astype(float)
    rows.append(metrics(overnight("TQQQ", w), "TQQQ overnight only, only when QQQ > 200d SMA (else cash)"))
    rows.append(metrics(overnight("TQQQ", w) + overnight("SPY", 1 - w), "TQQQ overnight when QQQ > SMA200, else SPY overnight"))
    # vol targeting: leverage = min(3, target / realized vol), via TQQQ weight
    for tgt in (0.20, 0.30, 0.40):
        lev = (tgt / rv20).clip(upper=3.0).fillna(0)
        wt = (lev / 3.0)
        rows.append(metrics(overnight("TQQQ", wt), f"TQQQ overnight only, vol-targeted {tgt:.0%} (QQQ 20d vol)"))
        rows.append(metrics(overnight("TQQQ", wt * w), f"TQQQ overnight only, vol-targeted {tgt:.0%} + SMA200 filter"))
    # classic full-time leveraged with trend filter
    rows.append(metrics(switching({"TQQQ": w, "SPY": 1 - w}, ["TQQQ", "SPY"]), "TQQQ when QQQ > SMA200, else SPY (full-time)"))
    rows.append(metrics(switching({"TQQQ": w, "TLT": 1 - w}, ["TQQQ", "TLT"]), "TQQQ when QQQ > SMA200, else TLT (full-time)"))
    rows.append(metrics(switching({"QLD": w, "SPY": 1 - w}, ["QLD", "SPY"]), "QLD (2x) when QQQ > SMA200, else SPY (full-time)"))
    lev = (0.30 / rv20).clip(upper=3.0).fillna(0)
    rows.append(metrics(switching({"TQQQ": lev / 3 * w, "SPY": 1 - lev / 3 * w}, ["TQQQ", "SPY"]),
                        "TQQQ vol-targeted 30% + SMA200, rest SPY (full-time)"))
    # the overnight TQQQ with daytime SPY: sell TQQQ at the open, hold SPY during the day
    dy_spy = (D["SPY"]["close"] / D["SPY"]["open"] - 1).fillna(0)
    rows.append(metrics(overnight("TQQQ", w) + (dy_spy - 2 * COST["SPY"]), "TQQQ overnight (SMA200 filter) + SPY during the day"))
    table(rows, "Core strategies, 2011 to now")
    y = yearly_table(rows[:9], "Core strategies")
    y.to_csv(OUT / "yearly.csv")
    # stress windows
    say("", "Stress windows (total return of each strategy):", "")
    wins = [("2018 Q4", "2018-10-01", "2018-12-31"), ("Covid 2020-02-19..03-23", "2020-02-19", "2020-03-23"),
            ("2022 bear", "2022-01-01", "2022-12-31"), ("2025-04 tariff shock", "2025-03-01", "2025-04-30"),
            ("last 12 months", str(idx[-252].date()), "2100-01-01")]
    say("| strategy | " + " | ".join(w[0] for w in wins) + " |")
    say("|---|" + "---|" * len(wins))
    series = {"SPY buy & hold": bh("SPY"), "TQQQ buy & hold": bh("TQQQ"), "TQQQ overnight only": overnight("TQQQ"),
              "TQQQ overnight, SMA200 filter": overnight("TQQQ", w),
              "TQQQ overnight, vol 30% + SMA200": overnight("TQQQ", (0.30 / rv20).clip(upper=3.0).fillna(0) / 3 * w),
              "TQQQ>SMA200 else SPY (full-time)": switching({"TQQQ": w, "SPY": 1 - w}, ["TQQQ", "SPY"])}
    for name, r in series.items():
        cells = []
        for _, a, b in wins:
            rr = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
            cells.append(f"{(1 + rr).prod() - 1:+.0%}" if len(rr) else "n/a")
        say(f"| {name} | " + " | ".join(cells) + " |")
    # how often does an overnight gap blow through the daily-loss cap?
    tq = on["TQQQ"].dropna()
    say("", f"TQQQ overnight gaps since 2011: {len(tq)} nights; worst {tq.min():+.1%} ({tq.idxmin().date()}), "
        f"nights below -10%: {(tq < -0.10).sum()}, below -15%: {(tq < -0.15).sum()}, below -25%: {(tq < -0.25).sum()}; "
        f"best {tq.max():+.1%}.")
    return rows


# ----------------------------------------------------------------------------- 3. turn of the month
def tom_section(data):
    say("", "## 3. Turn of the month", "",
        "TOM days = the last trading day of a month and the first three of the next. Position held "
        "over the day (prior close to close). Does the old finding (most of the market's return lands "
        "in those 4 days) still hold?", "")
    say("| ETF | period | TOM days | mean TOM day | other days | mean other day | TOM total | other total | TOM share of days |")
    say("|---|---|---|---|---|---|---|---|---|")
    for sym in ("SPY", "QQQ", "TQQQ"):
        df = data.get(sym)
        if df is None:
            continue
        cc = (df["close"] / df["close"].shift(1) - 1).dropna()
        m = cc.index.to_series().dt.month
        last_of_month = (m != m.shift(-1))
        pos = pd.Series(np.arange(len(cc)), index=cc.index)
        start_pos = pos[m != m.shift(1)]       # first trading day of each month
        first3 = pd.Series(False, index=cc.index)
        for p in start_pos:
            first3.iloc[p:p + 3] = True
        tom = last_of_month | first3
        for lab, a, b in (("2000-2010", "2000-01-01", "2010-12-31"), ("2011-2018", "2011-01-01", "2018-12-31"),
                          ("2019-now", "2019-01-01", "2100-01-01")):
            sel = (cc.index >= pd.Timestamp(a)) & (cc.index <= pd.Timestamp(b))
            t, o = cc[sel & tom], cc[sel & ~tom]
            if len(t) < 30:
                continue
            say(f"| {sym} | {lab} | {len(t)} | {t.mean():+.3%} | {len(o)} | {o.mean():+.3%} | {(1 + t).prod() - 1:+.0%} | "
                f"{(1 + o).prod() - 1:+.0%} | {len(t) / (len(t) + len(o)):.0%} |")


# ----------------------------------------------------------------------------- 4. mean reversion
def meanrev_section(data):
    say("", "## 4. Dip buying (short-term mean reversion) on QQQ, traded with TQQQ", "",
        "Rules known at the close, entered at that close, exit at the close. Returns per trade are "
        "TQQQ close-to-close minus 0.06% round trip. 'excess' = vs holding SPY over the same days.", "")
    q, t, s = data.get("QQQ"), data.get("TQQQ"), data.get("SPY")
    if q is None or t is None or s is None:
        say("missing data")
        return
    idx = t.index[t.index >= pd.Timestamp(CORE_START)]
    qc = q["close"].reindex(idx).ffill()
    tc = t["close"].reindex(idx).ffill()
    sc = s["close"].reindex(idx).ffill()
    sma = qc.rolling(200).mean()
    down = qc < qc.shift(1)
    d3 = down & down.shift(1).fillna(False) & down.shift(2).fillna(False)
    delta = qc.diff()
    gain = delta.clip(lower=0).rolling(2).mean()
    loss = (-delta.clip(upper=0)).rolling(2).mean()
    rsi2 = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    drop5 = qc / qc.rolling(5).max() - 1
    rules = {
        "3 down closes, QQQ > SMA200; exit first up close or 5 days": (d3 & (qc > sma), lambda i: qc.iloc[i] > qc.iloc[i - 1]),
        "3 down closes, any trend; exit first up close or 5 days": (d3, lambda i: qc.iloc[i] > qc.iloc[i - 1]),
        "RSI(2) < 10, QQQ > SMA200; exit RSI(2) > 60 or 5 days": ((rsi2 < 10) & (qc > sma), lambda i: rsi2.iloc[i] > 60),
        "RSI(2) < 10, any trend; exit RSI(2) > 60 or 5 days": ((rsi2 < 10), lambda i: rsi2.iloc[i] > 60),
        "QQQ 3%+ below its 5-day high, > SMA200; exit first up close or 5 days": ((drop5 < -0.03) & (qc > sma), lambda i: qc.iloc[i] > qc.iloc[i - 1]),
    }
    say("| rule | trades | win rate | mean/trade | t | total (sum) | excess vs SPY/trade | 1st half sum | 2nd half sum | days in market |")
    say("|---|---|---|---|---|---|---|---|---|---|")
    for name, (sig, exit_fn) in rules.items():
        rets, exc, days, i = [], [], 0, 201
        half = len(idx) // 2
        hsum = [0.0, 0.0]
        while i < len(idx) - 6:
            if bool(sig.iloc[i]):
                j = i + 1
                while j < min(i + 5, len(idx) - 1) and not exit_fn(j):
                    j += 1
                r = tc.iloc[j] / tc.iloc[i] - 1 - 0.0006
                rets.append(r)
                exc.append(r - (sc.iloc[j] / sc.iloc[i] - 1))
                hsum[i >= half] += r
                days += j - i
                i = j
            i += 1
        n, m, tt, wr = tstat(rets)
        say(f"| {name} | {n} | {wr:.0%} | {m:+.2%} | {tt:+.1f} | {sum(rets):+.0%} | {np.mean(exc) if exc else float('nan'):+.2%} | "
            f"{hsum[0]:+.0%} | {hsum[1]:+.0%} | {days / len(idx):.0%} |")


# ----------------------------------------------------------------------------- 5. momentum rotation
def momentum_section(data):
    say("", "## 5. Monthly ETF momentum rotation (for completeness)", "",
        "At each month end, rank SPY, QQQ, IWM, EFA, EEM, GLD, TLT by trailing total return and hold the "
        "leader for the next month; cash when the leader's trailing return is negative. Costs 0.02% per switch.", "")
    syms = [s for s in ("SPY", "QQQ", "IWM", "EFA", "EEM", "GLD", "TLT") if data.get(s) is not None]
    if len(syms) < 4 or data.get("SPY") is None:
        say("missing data")
        return
    idx = data["SPY"].index[data["SPY"].index >= pd.Timestamp(CORE_START)]
    px = pd.DataFrame({s: data[s]["close"].reindex(idx).ffill() for s in syms})
    me = px.groupby([px.index.year, px.index.month]).tail(1).index   # month ends
    rows = []
    for look, lab in ((126, "6-month"), (252, "12-month"), (231, "12-1 month (skip last month)")):
        r = pd.Series(0.0, index=idx)
        held = None
        for k in range(len(me) - 1):
            d0, d1 = me[k], me[k + 1]
            pos = px.index.get_loc(d0)
            if pos < 252:
                continue
            if lab.startswith("12-1"):
                mom = px.iloc[pos - 21] / px.iloc[pos - 252] - 1
            else:
                mom = px.iloc[pos] / px.iloc[pos - look] - 1
            lead = mom.idxmax()
            pick = lead if mom[lead] > 0 else None
            window = (px.index > d0) & (px.index <= d1)
            if pick:
                r[window] = px[pick].pct_change()[window]
            if pick != held:
                r[px.index[window][0]] -= 0.0002
                held = pick
        rows.append(metrics(r, f"rotation, {lab} lookback"))
    rows.append(metrics(px["SPY"].pct_change().fillna(0), "SPY buy & hold"))
    rows.append(metrics(px["QQQ"].pct_change().fillna(0), "QQQ buy & hold"))
    table(rows, "ETF momentum rotation vs buy & hold, 2011 to now")


# ----------------------------------------------------------------------------- 6. news gaps
UNIVERSE = """AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO BRK-B LLY JPM UNH V XOM MA JNJ PG COST HD ABBV WMT NFLX
BAC CRM KO CVX MRK ORCL AMD PEP CSCO TMO ACN LIN ADBE MCD ABT WFC PM IBM GE TXN CAT QCOM INTU ISRG VZ DHR AMGN
NOW GS NEE DIS SPGI PFE CMCSA RTX AXP LOW UBER T HON UNP BKNG MS PGR BLK COP SCHW ETN SYK LMT TJX BA C VRTX ADP
BSX PANW MDT GILD ADI MMC SBUX DE BMY PLD CB MU FI LRCX KLAC MDLZ SO INTC ANET PLTR CRWD DUK AMAT REGN ELV CI HUM
HCA GD NOC MO EOG SLB HAL MMM EMR ITW NKE SHW TGT CMG ORLY MAR HLT ABNB DASH PYPL COIN SNOW DDOG NET SMCI CLS
DELL HPQ WDC STX MRVL ON NXPI TER APH GLW F GM RIVN UPS FDX CVS WBA MRNA ZM ROKU SHOP SQ SNAP PINS ETSY W CHWY
AFRM UPST HOOD SOFI LULU DECK ULTA DG DLTR KHC CPB CAG GIS K HSY CL KMB EL TPR RL VFC HAS MAT EA TTWO RBLX U
OKTA ZS MDB TEAM WDAY ADSK CDNS SNPS FTNT AKAM TTD APP ARM MSTR CELH MNST SMH""".split()


def gap_section(data):
    say("", "## 6. Buying stocks after big news gaps, ~150 large and mid caps", "",
        "Event: the stock opens 3%+ away from its previous close *after removing SPY's own gap* (so the "
        "move is the stock's news). Returns are vs SPY over the same span, in the direction of the news "
        "(for down gaps, 'long' = buying the fallen stock). The universe is today's names, so the long "
        "side is flattered (survivorship) and the bearish side penalised. t uses one row per event.", "")
    spy = data.get("SPY")
    if spy is None:
        say("no SPY")
        return
    spy = spy[spy.index >= pd.Timestamp("2016-01-01")]
    spy_on = spy["open"] / spy["close"].shift(1) - 1
    buckets = {}

    def add(key, val, d0):
        buckets.setdefault(key, []).append((d0, val))

    n_syms = 0
    for sym in UNIVERSE:
        df = data.get(sym)
        if df is None:
            continue
        df = df[df.index >= pd.Timestamp("2016-01-01")].reindex(spy.index).dropna(subset=["open", "close"])
        if len(df) < 500:
            continue
        n_syms += 1
        o, c, h, l = df["open"].values, df["close"].values, df["high"].values, df["low"].values
        so, sc = spy["open"].reindex(df.index).values, spy["close"].reindex(df.index).values
        gap = o[1:] / c[:-1] - 1 - (so[1:] / sc[:-1] - 1)
        dates = df.index[1:]
        for k in range(len(gap) - 25):
            g = gap[k]
            if abs(g) < 0.03:
                continue
            i = k + 1                         # index in o/c arrays of the gap day
            side = 1 if g > 0 else -1
            d0 = dates[k]
            held = c[i] >= o[i] if side > 0 else c[i] <= o[i]
            size = "3-6%" if abs(g) < 0.06 else ("6-12%" if abs(g) < 0.12 else "12%+")

            def ex(entry_px, entry_i, exit_i, sentry_px):
                r = c[exit_i] / entry_px - 1
                m = sc[exit_i] / sentry_px - 1
                return side * (r - m)

            for hd in (0, 5, 10, 20):
                add((side, "buy at the open, day 0", hd), ex(o[i], i, i + hd, so[i]), d0)
            for hd in (5, 10, 20):
                add((side, "buy at the close of day 0 if the gap held (close on the news side of the open)" if held
                     else "buy at the close of day 0 if the gap faded", hd), ex(c[i], i, i + hd, sc[i]), d0)
                if held:
                    add((side, "buy at the open of day 1 after a held gap", hd), ex(o[i + 1], i + 1, i + hd, so[i + 1]), d0)
            add((side, f"buy at the open, day 0, gap {size}", 10), ex(o[i], i, i + 10, so[i]), d0)
            add((side, f"buy at the close of day 0 if held, gap {size}", 10), ex(c[i], i, i + 10, sc[i]), d0)
            # exits for the held-gap close entry over 20 days: stop / target vs none (long side only)
            if side > 0 and held:
                e = c[i]
                for stop, tgt, lab in ((0.07, None, "7% stop, no target"), (None, 0.10, "10% target, no stop"),
                                       (0.07, 0.15, "7% stop + 15% target"), (0.07, 0.10, "7% stop + 10% target"),
                                       (None, None, "no stop, no target (time exit only)")):
                    j = i + 1
                    out = None
                    while j <= i + 20:
                        pl = c[j] / e - 1
                        if stop is not None and pl <= -stop:
                            out = j
                            break
                        if tgt is not None and pl >= tgt:
                            out = j
                            break
                        j += 1
                    j = out if out is not None else i + 20
                    add((1, f"held gap, close entry, 20-day max hold, {lab}", 20), (c[j] / e - 1) - (sc[j] / sc[i] - 1), d0)
    say(f"Universe with data: {n_syms} stocks, 2016 to now. Events: "
        f"{sum(len(v) for (s, lab, h), v in buckets.items() if lab == 'buy at the open, day 0' and h == 0)} "
        f"(up {len(buckets.get((1, 'buy at the open, day 0', 0), []))}, down {len(buckets.get((-1, 'buy at the open, day 0', 0), []))}).", "")
    for side, title in ((1, "Good-news gaps (long)"), (-1, "Bad-news gaps (the bearish side: positive = betting against the stock paid)")):
        say("", f"### {title}", "")
        say("| entry | hold (trading days) | events | avg vs SPY | median | t | share that paid | 2016-20 avg | 2021-now avg |")
        say("|---|---|---|---|---|---|---|---|---|")
        keys = sorted([k for k in buckets if k[0] == side], key=lambda k: (k[1], k[2]))
        for k in keys:
            vals = buckets[k]
            xs = [v for _, v in vals]
            n, m, t, w = tstat(xs)
            a = [v for d, v in vals if d < pd.Timestamp("2021-01-01")]
            b = [v for d, v in vals if d >= pd.Timestamp("2021-01-01")]
            say(f"| {k[1]} | {k[2]} | {n} | {m:+.2%} | {np.median(xs):+.2%} | {t:+.1f} | {w:.0%} | "
                f"{np.mean(a) if a else float('nan'):+.2%} | {np.mean(b) if b else float('nan'):+.2%} |")
    # bad-news gaps, long side (buying the dip after bad news)
    say("", "### Buying the fallen stock after a bad-news gap (long side)", "")
    say("| entry | hold | events | avg vs SPY | t | share that paid |")
    say("|---|---|---|---|---|---|")
    for k in sorted([k for k in buckets if k[0] == -1 and k[1] in ("buy at the open, day 0", "buy at the close of day 0 if the gap faded",
                                                                     "buy at the close of day 0 if the gap held (close on the news side of the open)")],
                    key=lambda k: (k[1], k[2])):
        xs = [-v for _, v in buckets[k]]
        n, m, t, w = tstat(xs)
        say(f"| {k[1]} | {k[2]} | {n} | {m:+.2%} | {t:+.1f} | {w:.0%} |")


# ----------------------------------------------------------------------------- 7. minute bars (Alpaca)
def minute_section():
    say("", "## 7. Cost of the bot's run times (Alpaca minute bars, SIP)", "")
    try:
        from bot.alpaca import Alpaca
        api = Alpaca.from_env(False)
    except SystemExit as e:
        say(f"Skipped: {e}")
        return
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    today = datetime.now(ET).date()
    for sym, years in (("QQQ", 5), ("TQQQ", 3)):
        try:
            lo = datetime.combine(today - timedelta(days=365 * years), dtime(9, 30), ET).astimezone(timezone.utc).isoformat()
            hi = datetime.combine(today - timedelta(days=1), dtime(16, 0), ET).astimezone(timezone.utc).isoformat()
            bars = api.bars_between(sym, "1Min", lo, hi, feed="sip")
        except Exception as e:  # noqa: BLE001
            say(f"{sym}: minute bars unavailable ({e})")
            continue
        days = {}
        for b in bars:
            t = datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
            if dtime(9, 30) <= t.time() < dtime(16, 0):
                days.setdefault(t.date(), {})[t.time()] = b
        marks = [dtime(9, 35), dtime(9, 50), dtime(10, 0), dtime(10, 20), dtime(15, 30), dtime(15, 45), dtime(15, 50)]
        rows = {m: [] for m in marks}
        prev_close = None
        on_ideal, on_real, dy_ideal = [], [], []
        for d in sorted(days):
            bd = days[d]
            times = sorted(bd)
            if len(times) < 300:
                prev_close = None
                continue
            op, cl = bd[times[0]]["o"], bd[times[-1]]["c"]
            px = {}
            for m in marks:
                later = [k for k in times if k >= m]
                if later:
                    px[m] = bd[later[0]]["o"]
            if all(m in px for m in marks):
                for m in marks[:4]:
                    rows[m].append(px[m] / op - 1)
                for m in marks[4:]:
                    rows[m].append(cl / px[m] - 1)
                if prev_close is not None:
                    on_ideal.append(op / prev_close[0] - 1)
                    on_real.append(px[dtime(9, 35)] / prev_close[1] - 1)
                    dy_ideal.append(cl / op - 1)
                prev_close = (cl, px[dtime(15, 50)])
        say(f"### {sym}, last {years} years ({len(rows[marks[0]])} sessions)", "")
        say("| leg | mean per day | total compounded | std per day |")
        say("|---|---|---|---|")
        for m in marks[:4]:
            xs = np.array(rows[m])
            say(f"| open to {m:%H:%M} | {xs.mean():+.3%} | {np.prod(1 + xs) - 1:+.1%} | {xs.std():.2%} |")
        for m in marks[4:]:
            xs = np.array(rows[m])
            say(f"| {m:%H:%M} to close | {xs.mean():+.3%} | {np.prod(1 + xs) - 1:+.1%} | {xs.std():.2%} |")
        a, b, c = np.array(on_ideal), np.array(on_real), np.array(dy_ideal)
        say(f"| overnight, close to open (ideal) | {a.mean():+.3%} | {np.prod(1 + a) - 1:+.1%} | {a.std():.2%} |")
        say(f"| overnight, 15:50 to 9:35 next day (the bot's runs) | {b.mean():+.3%} | {np.prod(1 + b) - 1:+.1%} | {b.std():.2%} |")
        say(f"| intraday, open to close | {c.mean():+.3%} | {np.prod(1 + c) - 1:+.1%} | {c.std():.2%} |")
        say("")


def main():
    t0 = time.time()
    say("# Profit overhaul: evidence (real market data)", "",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by research/overhaul/overhaul_backtest.py on GitHub Actions.", "")
    core = ["SPY", "QQQ", "TQQQ", "QLD", "SSO", "UPRO", "SQQQ", "TLT", "IWM", "EFA", "EEM", "GLD"]
    data = load_all(core + [s for s in UNIVERSE if s not in core])
    src = {}
    for s, v in SOURCES.items():
        src[v] = src.get(v, 0) + 1
    say(f"Data: {len(data)} symbols loaded ({src}); SPY from {data['SPY'].index[0].date() if 'SPY' in data else 'n/a'} "
        f"to {data['SPY'].index[-1].date() if 'SPY' in data else 'n/a'}.")
    for fn in (overnight_section, core_section, tom_section, meanrev_section, momentum_section, gap_section):
        try:
            fn(data)
        except Exception:  # noqa: BLE001
            say("", f"Section {fn.__name__} failed:", "```", traceback.format_exc(), "```")
    try:
        minute_section()
    except Exception:  # noqa: BLE001
        say("", "Section minute_section failed:", "```", traceback.format_exc(), "```")
    say("", f"Done in {time.time() - t0:.0f}s.")
    (OUT / "results.md").write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
