# Rulebook (frozen 2026-10-30 by the profit overhaul; the research runs must follow it)

These rules come from review/profit-overhaul.md: a news-gap study of 201 stocks, 2016-2026,
12,603 gaps of 3%+ net of SPY, plus our own 16 closed picks (net about -$0.3, 6 paper + 10
live). Our own sample is far too small to set rules; it is listed as observations only.
A rule changes only when research/scorecard.md shows at least 30 closed trades bearing on
the claim and a t-statistic above 2. The evening review appends observations to the
journal and may add one line under "Proposed changes" below; it does not rewrite this file.

## Rules
1. Buy only. No puts, no inverse or bear ETFs, no shorting, no same-day direction trades.
   Evidence: betting against a bad-news gap lost 1.56% vs SPY at 10 days and 2.17% at 20
   days (t -10); the same-day reaction to news is a coin flip (+0.00%, 48% paid, 6,658
   events). Our own direction calls: 5 same-day trades, net -$0.28.
2. Prefer gaps of 6% or more on a concrete estimate change (guidance raise, rating reversal,
   decision). Evidence: 10-day drift vs SPY, gap 3-6% +0.22% (not significant); 6-12% +1.12%
   (t 3.1); 12%+ +2.08% (t 3.1). Big names qualify on fresh news; mega-caps after a good-news
   gap beat SPY by +1.2% at 10 days.
3. Hold about 20 trading days (max_hold_days default 28, 14-30 allowed, never under 3).
   Evidence: 5 days -0.03%, 10 days +0.53% (t 3.5), 20 days +1.33% (t 6.1); the median is
   negative and the hit rate 48-49%, so the edge is a right tail. Do not sell winners early.
4. Wide disaster stop (15%), no default target. Evidence over 20-day holds: no stop or
   target +1.20%; 10% target only +0.67%; 7% stop only +0.48%; 7% stop + 10% target +0.18%.
   The old defaults (5-8% stop, 10-15% target, under 10 days) were the worst combination.
5. Buy on day 0 from 10:00 ET, not the next morning. Evidence: the day-1 open entry after a
   held gap was the worst entry tested (5 days -0.30%, t -2.1). Do not wait for VWAP by
   default: faded gaps drifted as well as held ones (10 days +0.65% vs +0.43%).
6. Close only on a stated wrong-if judged on a close (or the 14:20 price), or a reversal of
   the news. Intraday dips are not exits. Evidence: rule 3; our own intraday exits (CLS,
   HAL, AZZ) were taken in broad selloffs, not on company news.
7. Conviction 1/2/3 = 15/25/40% of equity, at most 3 open; conviction 3 only on catalysts
   confirmed by primary sources. Confirm every story from two outlets (CEG, bought on one
   unconfirmed source, is still the largest paper loss).
8. The core is not yours to time: no SPY/TQQQ/QQQ picks, no hedging it. Its rule (TQQQ
   weight = min(1, 0.30 / (3 x QQQ 20-day vol)) above the 200-day average, 100% TQQQ for up
   to 5 sessions after three lower closes) made 39.9%/yr vs 13.9% for SPY in 2011-2026 and
   its whole edge is in acting the first session after the signal.
9. Experiment lane, flagged "[experiment]", conviction 1-2: a mega-cap bought the day it gaps
   down on an earnings or guidance miss, 20-day hold. Evidence +1.6% vs SPY at 10 days
   (t 9.7) but this is the most survivorship-biased number in the study.

## Observations (not rules; our own trades, n = 16)
- Winners: PENG +$2.07 (guidance raise), LMT +$1.10 (raised guide, re-issued on day 2 and
  sold at a 10% target, which rule 4 now says was early), UNH +$0.42, MMM +$0.14.
- Losers: AZZ -$0.82 and HAL -$0.55 (small caps in rate and sector selloffs), CLS -$0.76 and
  CEG -$0.74 (bought high after large gaps, one unconfirmed), HUM -$0.32.
- Beat quality matters: ELV's big EPS beat (10-21) was a non-operating benefit; it fell 4%
  in the first hour. Read the release, not the headline number.
- GitHub's cron skips runs; if state/account.json is over ~30 minutes old in market hours,
  dispatch `trade.yml -f command=cycle`.
- Headline index levels are often stale; trust state/market.json.

## Proposed changes (evening review; each line needs n >= 30 and t > 2 in the scorecard)
- none yet
