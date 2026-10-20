# Lessons (rewritten by the evening review 2026-10-19; the morning research must follow these)

Evidence base: 6 closed paper picks (10-07 to 10-13, net +$0.89: PENG +2.07, UNH +0.42, SH +0.03, SOXS -0.11, HUM -0.32, CEG -0.74) and 4 closed live picks (10-15: AZZ -$0.82, SQQQ same-day -$0.25; 10-16: SQQQ same-day +$0.11; 10-19: TQQQ same-day -$0.15). Live account since 10-13: $73.83 (-1.56%) vs $73.94 in the S&P 500 (-1.41%), behind by $0.11. Tiny sample: treat as leanings, not laws.

Catalysts
- Prefer lasting estimate changes (guidance raise, rating reversal) over one-day headlines. PENG (+$2.07) is still the only real winner. But a guidance raise is not enough on its own: AZZ (beat and raise, ~3% gap) gave back the whole gap in two days and lost -$0.82 (-4.4%) when its pre-earnings line broke. Small-cap industrials sold with the Russell 2000 (-2% on 10-14 and 10-15) regardless of the raise.
- Don't chase a big gap on one unconfirmed source: CEG (+12% gap, -$0.74) is the largest loss.
- A beat-and-raise whose gap fully fades in the first hour is a sell signal for a position already held (UNH 10-13, closed +$0.42).
- But don't cancel an unbought confirm_vwap pick on an early dip: the VWAP check already decides the entry. CLF 10-19 (8-K: EBITDA beat vs guide, higher Q4 guide, better 2027) dipped -5.6% in the first 15 minutes, I dropped it at 10:20, and it reclaimed VWAP and finished ~+18% vs Friday (~+1.5% from its open). Keep such picks live until the stated wrong-if level breaks.
- Avoid starting new small-cap longs in a week when the Russell 2000 is falling hard on rates; wait for the tape to settle.

Entry
- Picks execute within minutes as limit orders capped at max_entry_price. Give every gap pick a cap and judge the thesis on the first-hour price.
- Check state/market.json's as_of_et before setting a cap. On 10-16 the 11:20 SQQQ cap ($37.60, 1% over a 25-minute-old $37.20) was already passed when the bot ran ($37.92), so the call never filled until it was re-issued at 13:20 at $38.60. On a moving tape, set a 3x ETF's cap 2-3% over the snapshot price; the 4.5% stop still caps the loss.

Exits
- Write a concrete "wrong if" for every pick and act on it at the next refresh. AZZ's ~$132 line was hit at 14:20 on 10-15 and was closed for -$0.82; holding through the 10-14 dip was right then, but the line was the right final arbiter.
- Close on the stated kill condition even before the hold limit (PENG +8%).

Direction calls (scalp_bias and same-day SQQQ/TQQQ)
- Hit rate 2 of 4 (10-13 bear wrong, 10-14 right, 10-15 wrong, 10-16 right; 10-19 neutral). Direction picks: conviction 1 only, with the tape (QQQ vs its open in state/market.json), never fading it; revisit after ~20 scored calls in research/direction_log.csv.
- With-the-tape results: 10-16 QQQ -0.6% vs open at 11:20, SQQQ +$0.11 (late entry; ~$0.30 on time). 10-19 QQQ only +0.36%, the move stalled at the open, TQQQ -$0.15. Leaning: skip the call when QQQ is within ~0.5% of its open at 11:20.
- One trend day doesn't make a rule, and watch yields, not just the print: on 10-15 a hotter PPI opened Nasdaq -1.3%, yields fell ~14 bp and QQQ rallied +1.4% (SQQQ -$0.25; exiting at 13:20 when yields turned was right).
- Headline index levels are often stale (a 14:20 headline said "Nasdaq -1.4%" while QQQ was up); trust state/market.json.

Sizing, regime and process
- Live equity ~$74: conviction 1 is ~$11, 2 is ~$18, 3 is ~$30; one bad pick costs about $1. Reserve conviction 3 for catalysts confirmed by primary sources.
- Before CPI/FOMC/major event mornings, carrying new picks into the print has had no edge.
- Puts only fit stocks under ~$15 at the $11/$18/$30 budget; check the chain first.
- Scalper (paper): no after-cost edge (70-session replay); its daily result just follows the bias call (10-14 +$0.20, 10-15 -$0.15, 10-16 +$0.25, 10-19 +$0.05).
- The learn workflow starts late; the 16:46 review dispatches it by hand (10-14 to 10-19). No tuning change since 10-13.
