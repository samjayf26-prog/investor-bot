
# Lessons (rewritten by the evening review 2026-10-13; the morning research must follow these)

Evidence base: 6 closed picks (paper, 10-07 to 10-13), net +$0.89 (PENG +2.07, UNH +0.42, SH +0.03, SOXS -0.11, HUM -0.32, CEG -0.74). Tiny sample: treat as leanings, not laws.

Catalysts
- Prefer lasting estimate changes (guidance raise, rating reversal) over one-day headlines. PENG (+$2.07, +8.3%) was a guidance raise and is the only real winner.
- Don't chase a big gap on one unconfirmed source: CEG (+12% gap, -$0.74, -5%) is the largest loss.
- A beat-and-raise whose gap fully fades in the first hour is a sell signal, not a dip: UNH (10-13) was closed near flat on that rule (+$0.42).

Entry
- The bot's first check is 9:50, after gaps have often faded or run. Give every gap pick a max_entry_price (HUM bought $441, -$0.32). Even so, a cap can't protect you from a gap that fades before 9:50 (UNH): judge the thesis on the 9:50 price, not the premarket one.
- Prefer picks whose thesis survives the open without needing the gap: PENG, CRM-type setups held through multiple days.

Exits
- Write a concrete "wrong if" for every pick and act on it at the very next refresh. SOXS, HUM and UNH were closed on their own rules for small losses/gains; this discipline has kept losses to cents except CEG, where it was applied late.
- Close on the stated kill condition even a day before the hold limit if it triggers (PENG closed +8% when the sector kill condition hit).

Sizing and market regime
- Live equity is ~$75, so conviction 2 is ~$19 and 3 is ~$30; one bad gap pick costs about $1. Reserve conviction 3 for catalysts that are confirmed by primary sources.
- Before CPI/FOMC/major event mornings, carrying new picks into the print has had no edge; 10-13 no-pick afternoon ahead of CPI is the default.
- Puts only fit stocks under ~$15 at the $11/$18/$30 budget; check the chain before picking (JNJ 10-13 didn't fit).

Scalper / scalp_bias
- Scalper is on paper since 10-13 (70-session replay found no after-cost edge). Last 5 scored sessions: -$0.07 total; stops lost -$0.25, take-profits won +$0.16, time exits ~0.
- 10-13 bear bias: 2 SQQQ trips, -0.077% (stop) and -0.007% (time): a correct chip-selloff read, still no profit. A bias call alone doesn't pay at scalp size; if the view is strong, express it as a same-day TQQQ/SQQQ pick (max_hold_days 0) instead.
- Check the scorecard's scalp_bias hit rate before sizing any direction call; it has not yet been shown to be reliable.

Process
- research/scorecard.md was still dated 10-12 at the 10-13 evening review: the tuner's view lags a day, so lean on ledger/*.csv for same-day results.
