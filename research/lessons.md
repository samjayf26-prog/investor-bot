# Lessons (rewritten by the evening review 2026-10-16; the morning research must follow these)

Evidence base: 6 closed paper picks (10-07 to 10-13, net +$0.89: PENG +2.07, UNH +0.42, SH +0.03, SOXS -0.11, HUM -0.32, CEG -0.74) and 3 closed live picks (10-15: AZZ -$0.82, SQQQ same-day -$0.25; 10-16: SQQQ same-day +$0.11). Live account since 10-13: $74.00 (-1.33%) vs $73.62 in the S&P 500 (-1.84%), ahead by $0.38. Tiny sample: treat as leanings, not laws.

Catalysts
- Prefer lasting estimate changes (guidance raise, rating reversal) over one-day headlines. PENG (+$2.07) is still the only real winner. But a guidance raise is not enough on its own: AZZ (beat and raise, ~3% gap) gave back the whole gap in two days and lost -$0.82 (-4.4%) when its pre-earnings line broke. Small-cap industrials sold with the Russell 2000 (-2% on 10-14 and 10-15) regardless of the raise.
- Don't chase a big gap on one unconfirmed source: CEG (+12% gap, -$0.74) is the largest loss.
- A beat-and-raise whose gap fully fades in the first hour is a sell signal (UNH 10-13, closed +$0.42).
- Avoid starting new small-cap longs in a week when the Russell 2000 is falling hard on rates; wait for the tape to settle.

Entry
- Picks execute within minutes as limit orders capped at max_entry_price. Give every gap pick a cap and judge the thesis on the first-hour price.
- Check state/market.json's as_of_et before setting a cap. On 10-16 the 11:20 SQQQ cap ($37.60, 1% over a 25-minute-old $37.20) was already passed when the bot ran ($37.92), so the call never filled until it was re-issued at 13:20 at $38.60. On a moving tape, set a 3x ETF's cap 2-3% over the snapshot price; the 4.5% stop still caps the loss.

Exits
- Write a concrete "wrong if" for every pick and act on it at the next refresh. AZZ's ~$132 line was hit at 14:20 on 10-15 and was closed for -$0.82; holding through the 10-14 dip was right then, but the line was the right final arbiter.
- Close on the stated kill condition even before the hold limit (PENG +8%).

Direction calls (scalp_bias and same-day SQQQ/TQQQ)
- Hit rate 2 of 4: 10-13 bear wrong (QQQ +0.38%), 10-14 bear right (-1.43%), 10-15 bear wrong (+1.41%), 10-16 bear right (-1.91%). Not reliable: direction picks are conviction 1 only, with the tape (QQQ vs its open in state/market.json), never fading it (PROMPT.md, 10-15).
- 10-16 was the first call made by the with-the-tape rule: QQQ was -0.6% vs its open at 11:20 and kept falling to about -2%, VIXY +12%. Entered late (13:22 at $38.60) and sold at the close for +$0.11; on time at ~$37.9 it would have made ~$0.30. One data point; keep conviction 1 until ~20 scored calls in research/direction_log.csv.
- One trend day does not make a rule. On 10-14 a hot CPI drove an all-day selloff; on 10-15 a hotter PPI opened Nasdaq -1.3% and then QQQ rallied +1.4% as Treasury yields fell ~14 bp. The 10:20 SQQQ pick (bought $37.34) lost -$0.25.
- Watch yields, not just the inflation print: when yields fall after a hot print, the market is saying the print won't drive a hike; don't bet on a selloff then.
- Exiting the SQQQ at 13:20 when the S&P and yields turned was right (QQQ kept rallying into the close). Act on a broken thesis even before the stop.
- Headlines with index levels are often stale; check the time stamp before acting on one (a 14:20 headline said "Nasdaq -1.4%" while QQQ was actually up).

Sizing and market regime
- Live equity ~$74: conviction 1 is ~$11, 2 is ~$18, 3 is ~$30; one bad pick costs about $1. Reserve conviction 3 for catalysts confirmed by primary sources.
- Before CPI/FOMC/major event mornings, carrying new picks into the print has had no edge.
- Puts only fit stocks under ~$15 at the $11/$18/$30 budget; check the chain first.

Scalper (paper)
- No after-cost edge (70-session replay). 10-14 bear +$0.20 (right day), 10-15 bear -$0.15 (wrong day), 10-16 neutral then bear +$0.25 (right day): its result just follows the bias call.

Process
- The scheduled learn workflow starts late; the 16:46 review dispatches it by hand (10-14, 10-15, 10-16). The learning loop made no setting change since 10-13.
