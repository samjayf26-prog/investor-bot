# Lessons (rewritten by the evening review 2026-10-22; the morning research must follow these)

Evidence base: 6 closed paper picks (10-07 to 10-13, net +$0.89: PENG +2.07, UNH +0.42, SH +0.03, SOXS -0.11, HUM -0.32, CEG -0.74) and 6 closed live picks (AZZ -$0.82, HAL -$0.55, SQQQ same-day -$0.25 and +$0.11, TQQQ same-day -$0.15 and -$0.11). Open: MMM (10-20, +3.2%) and the overnight SPY core. Live account since 10-13: $72.77 (-2.97%) vs $73.68 in the S&P 500 (-1.76%), behind by $0.91. Tiny sample: treat as leanings, not laws.

Catalysts
- Prefer lasting estimate changes (guidance raise, rating reversal) over one-day headlines. PENG (+$2.07) is still the only real winner. A raise alone isn't enough: AZZ (beat and raise, ~3% gap) faded in two days for -$0.82 when small caps sold off on rates.
- Big names with fresh news are first-class candidates (PROMPT.md, review/megacap-results.md): good-news gaps paid over 5-10 days, not on the day; no bearish bets right after a big name's bad-news gap.
- Don't chase a big gap on one unconfirmed source: CEG (+12% gap, -$0.74) is the largest loss.
- A beat-and-raise whose gap fully fades in the first hour is a sell signal for a position already held (UNH 10-13, +$0.42).
- Don't cancel an unbought confirm_vwap pick on an early dip: CLF 10-19 dipped -5.6% early, I dropped it, and it finished ~+18% vs Friday. Keep such picks until the stated wrong-if breaks.
- If a capped pick runs past its cap while the tape confirms the thesis, raising the cap once is fine (MMM 10-20: cap $166 to $172, filled $169.74, $173.26 on 10-21).
- Check beat quality before trusting a big EPS beat: ELV 10-21 (adj EPS $6.99 vs ~$4.70, guide raised) gapped to ~$448 and sank to $428 in the first hour; GAAP included a $1.85/share non-operating benefit and membership fell. confirm_vwap kept us out. A post-earnings gap that fades below VWAP in the first hour has twice been the right skip (HUM, ELV); LMT 10-22 (+7.6%, raised guide) stayed below VWAP all day in a -2.7% Nasdaq and never filled.

Entry
- Picks execute within minutes as limit orders capped at max_entry_price. Give every gap pick a cap and judge the thesis on the first-hour price.
- Check state/market.json's as_of_et before setting a cap; on a moving tape set a 3x ETF's cap 2-3% over the snapshot (10-16 SQQQ missed its stale cap).

Exits
- Write a concrete "wrong if" for every pick and act on it at the next refresh (AZZ's ~$132 line, -$0.82; HAL's $33 line, -$0.55). Close on the stated kill condition even before the hold limit.
- A sector tailwind doesn't protect a stock in a broad selloff: HAL fell -4% on 10-22 while Brent hit a five-month high (energy sold with everything).

Direction calls (scalp_bias and same-day SQQQ/TQQQ)
- Bias hit rate 3 of 5 (10-13 wrong, 10-14 right, 10-15 wrong, 10-16 right, 10-20 bull right; 10-19 neutral). Conviction 1 only, with the tape (QQQ vs its open), never fading it; revisit after ~20 scored calls in research/direction_log.csv.
- But with-the-tape same-day trades are net -$0.15 over 3 (10-16 +$0.11, 10-19 -$0.15, 10-20 -$0.11). On 10-20 the call was right (QQQ +0.65% in the window) yet TQQQ lost: bought near the late-morning high (QQQ +0.99% at 11:00), then the rally cooled to +0.4%. Leaning: the 11:20 entry buys after most of the move; skip it when QQQ is already ~1% up (stretched) as well as when it's within ~0.5%.
- Headline index levels are often stale; trust state/market.json. Watch yields, not just the print (10-15 PPI: SQQQ -$0.25 as yields fell).

Sizing, regime and process
- Live equity ~$74: conviction 1 is ~$11, 2 is ~$18, 3 is ~$30; one bad pick costs about $1. Reserve conviction 3 for catalysts confirmed by primary sources.
- From 10-21 the bot parks idle cash in SPY after 14:30 ET (overnight core) and sells just enough when a pick needs it; size picks as usual and never pick SPY.
- Before CPI/FOMC/major event mornings, carrying new picks into the print has had no edge. Puts only fit stocks under ~$15; check the chain.
- Scalper (paper): no after-cost edge; its result just follows the bias (10-14 to 10-20: +0.20, -0.15, +0.25, +0.05, +0.06). No tuning change since 10-13; the 16:46 review dispatches the late learn workflow.
- Overnight SPY core: runs as designed (10-21 $42.21, 10-22 +$17.87 of HAL's cash). Its first night lost ~1.5% (-$0.63) into the 10-22 gap-down; one night says nothing about the edge, so judge it over weeks, not days.
