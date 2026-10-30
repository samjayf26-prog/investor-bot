"""Independent re-check of the profit-overhaul core backtest (review thread, 2026-10-30).

Own implementation, position-based (dollars held in each leg, trades only when the band is
crossed, costs on the dollars traded), so it does not share code with
research/overhaul/overhaul_backtest.py on the research branch. Inputs: review/overhaul/data/*.csv
written by fetch_data.py. Output: review/overhaul/verify-results.md.

Checks: (A) replicate the claimed numbers; (B) look-ahead / timing shifts; (C) costs; (D) parameter
sensitivity; (E) out of sample 1986-2010 with a simulated 3x fund (TQQQ did not exist); (F) the hard
halts; (G) volatility decay.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "verify-results.md"
L = []
COST_LEV, COST_REST = 0.0001, 0.00005     # one-way, same as the research backtest's base case


def say(*parts):
    line = " ".join(str(p) for p in parts)
    L.append(line)
    print(line, flush=True)


def load(sym):
    p = DATA / f"{sym.replace('^', 'IDX_')}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, index_col=0, parse_dates=True).sort_index()
    df = df[~df.index.duplicated()]
    df = df[(df["close"] > 0) & (df["adj_close"] > 0)]
    f = df["adj_close"] / df["close"]
    return pd.DataFrame({"open": df["open"] * f, "close": df["adj_close"], "raw_close": df["close"]}).dropna()


# ----------------------------------------------------------------------------- signals
def signals(close, sma_n=200, vol_n=20, vol_target=0.30, lev=3.0, down_days=3, max_days=5,
            overlay_needs_trend=False, extra_lag=0):
    """Everything is known at close t and used for the position held over day t+1.
    extra_lag shifts the SMA/vol weight one more day (the bot using only completed sessions)."""
    sma = close.rolling(sma_n).mean()
    trend = (close > sma).astype(float)
    trend[sma.isna()] = np.nan
    vol = close.pct_change().rolling(vol_n).std() * math.sqrt(252)
    w = (vol_target / (lev * vol)).clip(upper=1.0) * trend
    if extra_lag:
        w = w.shift(extra_lag)
    c = close.values
    down = np.r_[False, c[1:] < c[:-1]]
    overlay = np.zeros(len(c))
    in_ov, held = False, 0
    for t in range(len(c)):
        if in_ov:
            held += 1
            if c[t] > c[t - 1] or held >= max_days:
                in_ov, held = False, 0
        if not in_ov and t >= down_days and all(down[t - k] for k in range(down_days)) \
                and (not overlay_needs_trend or trend.iloc[t] == 1.0):
            in_ov, held = True, 0
        overlay[t] = 1.0 if in_ov else 0.0
    return pd.DataFrame({"trend": trend, "vol": vol, "w": w, "overlay": overlay}, index=close.index)


# ----------------------------------------------------------------------------- simulation
def simulate(lev_ret, rest_ret, target_w, band=0.0, cost_lev=COST_LEV, cost_rest=COST_REST,
             lev_open_ret=None, entries_at_open=False):
    """Daily portfolio returns. target_w[t] is the leveraged-ETF weight decided at close t and held over
    day t+1 (NaN = 0). Trades happen at the close only when |held - target| > band, or when moving
    between zero and non-zero. entries_at_open: a leg entered from zero is bought at the next open
    (misses the overnight gap), as when the bot's last run is skipped and it trades at 9:35."""
    idx = lev_ret.index
    lr, rr = lev_ret.fillna(0).values, rest_ret.fillna(0).values
    tw = target_w.reindex(idx).fillna(0).clip(0, 1).values
    lo = None if lev_open_ret is None else lev_open_ret.reindex(idx).fillna(0).values
    out = np.zeros(len(idx))
    lev, rest = 0.0, 1.0
    prev_total = 1.0
    pending_open = False
    for t in range(1, len(idx)):
        lev *= 1 + (lo[t] if (pending_open and lo is not None) else lr[t])
        rest *= 1 + rr[t]
        pending_open = False
        total = lev + rest
        held = lev / total if total > 0 else 0.0
        want = tw[t]
        if abs(want - held) > band or (want == 0 and lev > 0) or (want > 0 and lev == 0):
            trade = want * total - lev
            cost = abs(trade) * (cost_lev + cost_rest)
            if entries_at_open and lev == 0 and trade > 0:
                pending_open = True
            lev, rest = want * total, total - want * total - cost
            total = lev + rest
        out[t] = total / prev_total - 1
        prev_total = total
    return pd.Series(out, index=idx)


def metrics(r, name):
    r = r.dropna()
    if len(r) < 50:
        return None
    eq = (1 + r).cumprod()
    years = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = r.std() * math.sqrt(252)
    sharpe = r.mean() / r.std() * math.sqrt(252) if r.std() > 0 else float("nan")
    dd = eq / eq.cummax() - 1
    dd1y = eq / eq.rolling(252, min_periods=1).max() - 1
    yearly = eq.groupby(eq.index.year).last()
    yearly = yearly / yearly.shift(1).fillna(1.0) - 1
    half = len(r) // 2
    c1 = (1 + r.iloc[:half]).prod() ** (252 / half) - 1
    c2 = (1 + r.iloc[half:]).prod() ** (252 / (len(r) - half)) - 1
    under = (dd < 0).astype(int)
    runs, cur = [], 0
    for u in under.values:
        cur = cur + 1 if u else 0
        runs.append(cur)
    return {"name": name, "cagr": cagr, "vol": vol, "sharpe": sharpe, "mdd": dd.min(), "mdd1y": dd1y.min(),
            "worst_day": r.min(), "worst_day_date": r.idxmin().date(), "days_le_25": int((r <= -0.25).sum()),
            "half1": c1, "half2": c2, "yearly": yearly, "worst_year": yearly.min(),
            "worst_year_lab": int(yearly.idxmin()), "end": eq.iloc[-1], "underwater_days": max(runs),
            "years": years}


def table(rows, title, note=None):
    say("", f"### {title}", "")
    if note:
        say(note, "")
    say("| strategy | CAGR | vol | Sharpe | max DD | DD vs 1y peak | worst day | worst year | 1st half | 2nd half | $75 becomes | longest underwater |")
    say("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in rows:
        if not m:
            continue
        say(f"| {m['name']} | {m['cagr']:+.1%} | {m['vol']:.0%} | {m['sharpe']:.2f} | {m['mdd']:.0%} | {m['mdd1y']:.0%} | "
            f"{m['worst_day']:+.1%} ({m['worst_day_date']}) | {m['worst_year']:+.0%} ({m['worst_year_lab']}) | "
            f"{m['half1']:+.1%} | {m['half2']:+.1%} | ${75 * m['end']:,.0f} | {m['underwater_days'] / 252:.1f}y |")


def yearly_table(rows, title):
    rows = [m for m in rows if m]
    years = sorted({y for m in rows for y in m["yearly"].index})
    say("", f"### {title}: calendar years", "")
    say("| year | " + " | ".join(m["name"] for m in rows) + " |")
    say("|---|" + "---|" * len(rows))
    for y in years:
        say(f"| {y} | " + " | ".join(f"{m['yearly'].get(y, float('nan')):+.0%}" for m in rows) + " |")


def window_table(series, wins, title):
    say("", f"### {title}", "")
    say("| strategy | " + " | ".join(w[0] for w in wins) + " |")
    say("|---|" + "---|" * len(wins))
    for name, r in series.items():
        cells = []
        for _, a, b in wins:
            rr = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
            cells.append(f"{(1 + rr).prod() - 1:+.0%}" if len(rr) else "n/a")
        say(f"| {name} | " + " | ".join(cells) + " |")


def splice(early, late):
    """One continuous price series: `late` where it exists, `early` before that, scaled so the
    returns across the join are the early series' own returns (levels differ, e.g. index vs ETF)."""
    first = late.index[0]
    e = early[early.index < first]
    anchor = early.loc[first] if first in early.index else e.iloc[-1]
    out = pd.concat([e * (late.iloc[0] / anchor), late]).sort_index()
    return out[~out.index.duplicated()]


def sim3x(index_close, rf_annual=None, er=0.0095, spread=0.004, lev=3.0):
    """Daily-reset 3x fund on an index: 3x the daily return minus financing on the borrowed 2x
    (T-bill + spread) minus the expense ratio. rf_annual: Series of annual T-bill yields (fraction)."""
    r = index_close.pct_change()
    rf = (rf_annual.reindex(r.index).ffill().bfill() if rf_annual is not None else pd.Series(0.0, index=r.index))
    return lev * r - (lev - 1) * (rf + spread) / 252 - er / 252


def overlay_trades(close, lev_ret, rest_ret, down_days=3, max_days=5, needs_trend=False, sma_n=200):
    """The dip rule on its own: one row per trade (TQQQ return minus 0.06% round trip, excess vs rest)."""
    sig = signals(close, sma_n=sma_n, down_days=down_days, max_days=max_days, overlay_needs_trend=needs_trend)
    ov = sig["overlay"].values
    lr, rr = lev_ret.reindex(close.index).fillna(0).values, rest_ret.reindex(close.index).fillna(0).values
    first = lev_ret.first_valid_index()
    rets, exc, i = [], [], (int(close.index.searchsorted(first)) if first is not None else 0)
    n = len(ov)
    while i < n - 1:
        if ov[i] == 1.0:
            j = i + 1
            g, gr = 1.0, 1.0
            while True:
                g *= 1 + lr[j]
                gr *= 1 + rr[j]
                if j >= n - 1 or ov[j] == 0.0:
                    break
                j += 1
            rets.append(g - 1 - 0.0006)
            exc.append(g - gr)
            i = j
        i += 1
    xs = np.array(rets)
    if len(xs) < 3:
        return len(xs), float("nan"), float("nan"), float("nan"), float("nan")
    return len(xs), xs.mean(), xs.mean() / xs.std(ddof=1) * math.sqrt(len(xs)), float((xs > 0).mean()), float(np.mean(exc))


# ----------------------------------------------------------------------------- main
def main():
    data = {s: load(s) for s in ("SPY", "QQQ", "TQQQ", "QLD", "^NDX", "^GSPC", "^IRX")}
    for s, d in data.items():
        say(f"- {s}: " + (f"{d.index[0].date()}..{d.index[-1].date()} ({len(d)} rows)" if d is not None else "missing"))
    spy, qqq, tqqq = data["SPY"], data["QQQ"], data["TQQQ"]
    if spy is None or qqq is None or tqqq is None:
        say("SPY/QQQ/TQQQ missing; stopping.")
        OUT.write_text("\n".join(L) + "\n")
        sys.exit(1)
    rf = None
    if data["^IRX"] is not None:
        rf = (data["^IRX"]["raw_close"] / 100).clip(lower=0)

    # ---- A. replicate 2011-2026 on real TQQQ
    say("", "## A. Replication on real TQQQ, 2011-01-03 to now (base costs: TQQQ 0.01%, SPY 0.005% one-way)", "",
        "Own position-based simulation. 'daily' rebalances to the target every day; 'band 10' trades only when the "
        "target is more than 10 points from the held weight. Claimed (research backtest): SPY 13.9%, QQQ 18.3%, "
        "TQQQ 38.0%, B30 30.2% (banded 29.8%), B30+dip 39.9%, max DD -42%, Sharpe 1.06, worst day -13.9%.", "")
    idx = tqqq.index[tqqq.index >= pd.Timestamp("2011-01-03")]
    P = {s: data[s].reindex(idx).ffill() for s in ("SPY", "QQQ", "TQQQ")}
    R = {s: P[s]["close"].pct_change() for s in P}
    qclose = qqq["close"]                       # signals use QQQ's own full history
    sig = signals(qclose)
    w30 = sig["w"]
    wdip = pd.concat([sig["w"], sig["overlay"]], axis=1).max(axis=1)
    rows = [metrics(R["SPY"].fillna(0), "SPY buy & hold"), metrics(R["QQQ"].fillna(0), "QQQ buy & hold"),
            metrics(R["TQQQ"].fillna(0), "TQQQ buy & hold"),
            metrics(simulate(R["TQQQ"], R["SPY"], sig["trend"]), "A. TQQQ when QQQ > SMA200 else SPY (daily)"),
            metrics(simulate(R["TQQQ"], R["SPY"], w30), "B30 (daily)"),
            metrics(simulate(R["TQQQ"], R["SPY"], w30, band=0.10), "B30 (band 10)"),
            metrics(simulate(R["TQQQ"], R["SPY"], wdip), "B30 + dip (daily)"),
            metrics(simulate(R["TQQQ"], R["SPY"], wdip, band=0.10), "B30 + dip (band 10)"),
            metrics(simulate(R["TQQQ"], R["SPY"], sig["overlay"]), "dip overlay alone, rest SPY")]
    table(rows, "Replication, 2011 to now")
    yearly_table(rows, "Replication")
    base = simulate(R["TQQQ"], R["SPY"], wdip, band=0.10)
    say("", f"B30+dip target moved by more than 10 points on {(wdip.reindex(idx).fillna(0).diff().abs() > 0.10).mean():.1%} of days; "
        f"overlay active on {sig['overlay'].reindex(idx).mean():.1%} of days; TQQQ weight today {wdip.iloc[-1]:.0%} "
        f"(trend {int(sig['trend'].iloc[-1])}, 20d vol {sig['vol'].iloc[-1]:.0%}, overlay {int(sig['overlay'].iloc[-1])}).")
    n, m, t, wr, ex = overlay_trades(qclose, R["TQQQ"], R["SPY"])
    say(f"Dip rule alone since 2011: {n} trades, win rate {wr:.0%}, mean {m:+.2%}/trade, t={t:+.1f}, excess vs SPY {ex:+.2%}/trade "
        f"(claimed 176 trades, 74%, +1.39%, t 3.8).")

    # ---- B. look-ahead and timing
    say("", "## B. Timing and look-ahead shifts (B30 + dip, band 10, 2011 to now)", "",
        "If the result survives acting a day late it does not depend on knowing the close before it prints.", "")
    lag_w = signals(qclose, extra_lag=1)
    wdip_lagw = pd.concat([lag_w["w"], sig["overlay"]], axis=1).max(axis=1)
    wdip_lagd = pd.concat([sig["w"], sig["overlay"].shift(1)], axis=1).max(axis=1)
    wdip_lagb = pd.concat([lag_w["w"], sig["overlay"].shift(1)], axis=1).max(axis=1)
    open_ret = P["TQQQ"]["close"] / P["TQQQ"]["open"] - 1
    rows = [metrics(base, "as specified"),
            metrics(simulate(R["TQQQ"], R["SPY"], wdip_lagw, band=0.10), "SMA/vol weight one day later (bot uses completed sessions only)"),
            metrics(simulate(R["TQQQ"], R["SPY"], wdip_lagd, band=0.10), "dip entry/exit one day later"),
            metrics(simulate(R["TQQQ"], R["SPY"], wdip_lagb, band=0.10), "both one day later"),
            metrics(simulate(R["TQQQ"], R["SPY"], wdip, band=0.10, lev_open_ret=open_ret, entries_at_open=True),
                    "TQQQ entries from zero filled at the next open (misses the gap)"),
            metrics(simulate(R["TQQQ"], R["SPY"], wdip.shift(2), band=0.10), "everything two days later"),
            metrics(simulate(R["TQQQ"], R["SPY"], w30.shift(1), band=0.10), "B30 only, one day later"),
            metrics(simulate(R["TQQQ"], R["SPY"], sig["overlay"].shift(1)), "dip overlay alone, one day later")]
    table(rows, "Shifted signals")
    yearly_table(rows[:5], "Shifted signals")
    say("", "Dip rule alone, by execution lag (TQQQ return per trade minus 0.06%):", "")
    say("| variant | trades | win rate | mean/trade | t | excess vs SPY |")
    say("|---|---|---|---|---|---|")
    for lab, dd, md, nt in (("3 down, max 5, any trend (spec)", 3, 5, False), ("3 down, max 5, only above SMA200", 3, 5, True),
                            ("2 down, max 5", 2, 5, False), ("4 down, max 5", 4, 5, False), ("3 down, max 3", 3, 3, False),
                            ("3 down, max 10", 3, 10, False)):
        n, m, t, wr, ex = overlay_trades(qclose, R["TQQQ"], R["SPY"], dd, md, nt)
        say(f"| {lab} | {n} | {wr:.0%} | {m:+.2%} | {t:+.1f} | {ex:+.2%} |")
    for lag in (1, 2):
        n, m, t, wr, ex = overlay_trades(qclose, R["TQQQ"].shift(-lag), R["SPY"].shift(-lag))
        say(f"| spec rule, entered {lag} day(s) late | {n} | {wr:.0%} | {m:+.2%} | {t:+.1f} | {ex:+.2%} |")

    # ---- C. costs
    say("", "## C. Trading costs (B30 + dip, band 10, 2011 to now)", "")
    rows = [metrics(simulate(R["TQQQ"], R["SPY"], wdip, band=0.10, cost_lev=COST_LEV * k, cost_rest=COST_REST * k),
                    f"{k}x base costs (TQQQ {COST_LEV * k:.3%} one-way)") for k in (0, 1, 3, 5, 10, 20)]
    table(rows, "Cost multiples")

    # ---- D. parameter sensitivity
    say("", "## D. Parameter sensitivity (band 10, base costs, 2011 to now)", "",
        "Each row changes one thing from the spec (vol target 30%, SMA200, 20-day vol, 3 down closes, max 5 days, "
        "overlay ignores the trend filter, overlay weight 100%).", "")
    say("| variant | CAGR | Sharpe | max DD | worst year | 1st half | 2nd half |")
    say("|---|---|---|---|---|---|---|")

    def row(lab, **kw):
        ov_w = kw.pop("overlay_weight", 1.0)
        s = signals(qclose, **kw)
        ww = pd.concat([s["w"], s["overlay"] * ov_w], axis=1).max(axis=1)
        m = metrics(simulate(R["TQQQ"], R["SPY"], ww, band=0.10), lab)
        say(f"| {lab} | {m['cagr']:+.1%} | {m['sharpe']:.2f} | {m['mdd']:.0%} | {m['worst_year']:+.0%} ({m['worst_year_lab']}) | {m['half1']:+.1%} | {m['half2']:+.1%} |")

    row("spec")
    for vt in (0.20, 0.25, 0.35, 0.40):
        row(f"vol target {vt:.0%}", vol_target=vt)
    for n in (100, 150, 250):
        row(f"SMA{n}", sma_n=n)
    for n in (10, 40, 60):
        row(f"{n}-day vol", vol_n=n)
    for d in (2, 4):
        row(f"{d} down closes", down_days=d)
    for m_ in (3, 10):
        row(f"max {m_} days in overlay", max_days=m_)
    row("overlay only when QQQ > SMA200", overlay_needs_trend=True)
    row("overlay at 50% TQQQ instead of 100%", overlay_weight=0.5)
    row("overlay at 50%, only when QQQ > SMA200", overlay_weight=0.5, overlay_needs_trend=True)

    # ---- E. out of sample: simulated 3x before 2011
    say("", "## E. Out of sample: 1986-2010 with a simulated 3x Nasdaq-100 fund", "",
        "TQQQ started in 2010, so the earlier period uses 3x the index's daily return minus financing on the "
        "borrowed 2x (13-week T-bill + 0.4%) minus a 0.95% expense ratio, reset daily (this reproduces volatility "
        "decay). The index is QQQ's total return from 1999-03 and the Nasdaq-100 price index before; the 'rest' "
        "leg is SPY from 1993-02 and the S&P 500 price index before (dividends missing, so SPY-side returns "
        "are understated by ~2%/yr before 1993).", "")
    ndx, spx = data["^NDX"], data["^GSPC"]
    # validation: simulated 3x of QQQ vs actual TQQQ since 2011
    s3 = sim3x(qqq["close"], rf).reindex(idx)
    s3_nofin = sim3x(qqq["close"], None, er=0.0, spread=0.0).reindex(idx)
    say("", "### Does the simulation reproduce TQQQ? (2011 to now)", "")
    rows = [metrics(R["TQQQ"].fillna(0), "TQQQ actual"), metrics(s3.fillna(0), "simulated 3x QQQ (financing + 0.95% fee)"),
            metrics(s3_nofin.fillna(0), "3x QQQ daily, no costs at all")]
    table(rows, "Simulation check")
    diff = (s3 - R["TQQQ"]).dropna()
    say(f"Daily tracking error simulated vs actual: mean {diff.mean() * 252:+.2%}/yr, std {diff.std() * math.sqrt(252):.2%}/yr, "
        f"correlation {s3.corr(R['TQQQ']):.4f}.")
    yearly_table(rows, "Simulation check")

    if ndx is not None:
        index_close = splice(ndx["close"], qqq["close"])
        rest_close = splice(spx["close"], spy["close"]) if spx is not None else spy["close"]
        lev_all = sim3x(index_close, rf)
        for lab, a, b in (("1986-2010", "1986-01-01", "2010-12-31"), ("2000-2010", "2000-01-03", "2010-12-31"),
                          ("1986-1999", "1986-01-01", "1999-12-31"), ("1986 to now (simulated 3x throughout)", "1986-01-01", "2100-01-01")):
            ii = index_close.index[(index_close.index >= pd.Timestamp(a)) & (index_close.index <= pd.Timestamp(b))]
            if len(ii) < 300:
                continue
            lr = lev_all.reindex(ii)
            ir = index_close.pct_change().reindex(ii)
            rr = rest_close.pct_change().reindex(ii)
            s = signals(index_close)
            ww = pd.concat([s["w"], s["overlay"]], axis=1).max(axis=1)
            rows = [metrics(rr.fillna(0), "S&P 500 (rest leg) buy & hold"), metrics(ir.fillna(0), "Nasdaq-100 buy & hold"),
                    metrics(lr.fillna(0), "simulated 3x buy & hold"),
                    metrics(simulate(lr, rr, s["trend"]), "A. 3x when index > SMA200 else S&P (daily)"),
                    metrics(simulate(lr, rr, s["w"], band=0.10), "B30 (band 10)"),
                    metrics(simulate(lr, rr, ww, band=0.10), "B30 + dip (band 10)"),
                    metrics(simulate(lr, rr, ww.shift(1), band=0.10), "B30 + dip, one day later"),
                    metrics(simulate(lr, rr, s["overlay"]), "dip overlay alone, rest S&P")]
            table(rows, f"Out of sample {lab}")
            yearly_table(rows, f"Out of sample {lab}")
            n, m, t, wr, ex = overlay_trades(index_close.reindex(ii), lr, rr)
            say(f"Dip rule alone {lab}: {n} trades, win rate {wr:.0%}, mean {m:+.2%}/trade, t={t:+.1f}, excess vs S&P {ex:+.2%}/trade.")
            if lab.startswith("1986-2010"):
                wins = [("1987 crash (Oct 1-30)", "1987-10-01", "1987-10-30"), ("1990 (Jul-Oct)", "1990-07-16", "1990-10-11"),
                        ("1998 LTCM (Jul 17-Oct 8)", "1998-07-17", "1998-10-08"), ("dotcom 2000-03-10..2002-10-09", "2000-03-10", "2002-10-09"),
                        ("2000 calendar", "2000-01-01", "2000-12-31"), ("2001", "2001-01-01", "2001-12-31"), ("2002", "2002-01-01", "2002-12-31"),
                        ("GFC 2007-10-09..2009-03-09", "2007-10-09", "2009-03-09"), ("2008 calendar", "2008-01-01", "2008-12-31")]
                series = {"S&P 500": rr.fillna(0), "Nasdaq-100": ir.fillna(0), "simulated 3x": lr.fillna(0),
                          "A. 3x>SMA200 else S&P": simulate(lr, rr, s["trend"]),
                          "B30 (band 10)": simulate(lr, rr, s["w"], band=0.10),
                          "B30 + dip (band 10)": simulate(lr, rr, ww, band=0.10),
                          "dip overlay alone": simulate(lr, rr, s["overlay"])}
                window_table(series, wins, "Stress windows before 2011")
    else:
        say("Nasdaq-100 index data missing; only the 1999-2010 QQQ period can be tested.")

    # ---- E2. consistency across rolling windows
    if ndx is not None:
        say("", "## E2. How often does the rule beat buy-and-hold? Rolling windows, 1986 to now (simulated 3x throughout)", "")
        ii = index_close.index[index_close.index >= pd.Timestamp("1986-01-01")]
        s = signals(index_close)
        ww = pd.concat([s["w"], s["overlay"]], axis=1).max(axis=1)
        lr, rr = lev_all.reindex(ii), rest_close.pct_change().reindex(ii)
        strat = {"B30 (band 10)": simulate(lr, rr, s["w"], band=0.10), "B30 + dip (band 10)": simulate(lr, rr, ww, band=0.10),
                 "B30 + dip, one day later": simulate(lr, rr, ww.shift(1), band=0.10)}
        spy_r = rr.fillna(0)
        say("| strategy | window | windows | beat S&P | median excess CAGR | worst window CAGR | share of windows with a 50%+ drawdown |")
        say("|---|---|---|---|---|---|---|")
        for name, r in strat.items():
            for yrs in (3, 5, 10):
                n = yrs * 252
                eq, eqs = (1 + r).cumprod(), (1 + spy_r).cumprod()
                g = (eq / eq.shift(n)) ** (1 / yrs) - 1
                gs = (eqs / eqs.shift(n)) ** (1 / yrs) - 1
                dd = (eq / eq.rolling(n, min_periods=1).max() - 1)
                wdd = dd.rolling(n).min()
                ok = g.notna() & gs.notna()
                say(f"| {name} | {yrs}y | {int(ok.sum())} | {float((g[ok] > gs[ok]).mean()):.0%} | {float((g[ok] - gs[ok]).median()):+.1%} | "
                    f"{float(g[ok].min()):+.1%} | {float((wdd[ok] <= -0.5).mean()):.0%} |")
        for lab, a in (("2000 to now", "2000-01-03"), ("1986-1999", "1986-01-01")):
            jj = ii[ii >= pd.Timestamp(a)] if lab != "1986-1999" else ii[ii <= pd.Timestamp("1999-12-31")]
            rows = [metrics(rr.reindex(jj).fillna(0), "S&P 500 buy & hold"), metrics(index_close.pct_change().reindex(jj).fillna(0), "Nasdaq-100 buy & hold"),
                    metrics(simulate(lr.reindex(jj), rr.reindex(jj), s["w"], band=0.10), "B30 (band 10)"),
                    metrics(simulate(lr.reindex(jj), rr.reindex(jj), ww, band=0.10), "B30 + dip (band 10)"),
                    metrics(simulate(lr.reindex(jj), rr.reindex(jj), ww.shift(1), band=0.10), "B30 + dip, one day later")]
            table(rows, f"Simulated 3x, {lab}")

    # ---- F. halts
    say("", "## F. Interplay with the hard limits (B30 + dip, band 10)", "",
        "The bot halts new entries after a 25% loss from the previous close and stops at a 60% drawdown from the "
        "peak of the last year's equity (Alpaca portfolio history, 1 year). Neither can stop an overnight gap.", "")
    say("| sample | max DD (all-time peak) | max DD (1-year peak) | worst day | days at or below -25% | nights TQQQ gapped below -10% |")
    say("|---|---|---|---|---|---|")
    gaps = (P["TQQQ"]["open"] / P["TQQQ"]["close"].shift(1) - 1)
    m = metrics(base, "x")
    say(f"| 2011 to now (real TQQQ) | {m['mdd']:.0%} | {m['mdd1y']:.0%} | {m['worst_day']:+.1%} ({m['worst_day_date']}) | {m['days_le_25']} | {(gaps < -0.10).sum()} |")
    if ndx is not None:
        ii = index_close.index[(index_close.index >= pd.Timestamp("1986-01-01")) & (index_close.index <= pd.Timestamp("2010-12-31"))]
        s = signals(index_close)
        ww = pd.concat([s["w"], s["overlay"]], axis=1).max(axis=1)
        m = metrics(simulate(lev_all.reindex(ii), rest_close.pct_change().reindex(ii), ww, band=0.10), "x")
        say(f"| 1986-2010 (simulated 3x) | {m['mdd']:.0%} | {m['mdd1y']:.0%} | {m['worst_day']:+.1%} ({m['worst_day_date']}) | {m['days_le_25']} | n/a |")

    # ---- G. decay
    say("", "## G. Volatility decay, 2011 to now", "")
    q_cagr = metrics(R["QQQ"].fillna(0), "q")["cagr"]
    t_cagr = metrics(R["TQQQ"].fillna(0), "t")["cagr"]
    say(f"QQQ CAGR {q_cagr:+.1%}; naive 3x of that {3 * q_cagr:+.1%}; TQQQ actual {t_cagr:+.1%}; 3x daily with no costs "
        f"{metrics(s3_nofin.fillna(0), 'n')['cagr']:+.1%}. The gap between the naive 3x and the no-cost daily 3x is the "
        f"decay from daily resetting; the rest is fees and financing. Decay is in TQQQ's prices, so the 2011+ tests include it; "
        f"the simulated series reproduces it by construction.")
    OUT.write_text("\n".join(L) + "\n")
    say("", "Written", OUT)


if __name__ == "__main__":
    main()
