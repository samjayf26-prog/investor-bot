# Lessons (rewritten by the evening review 2026-10-14; the morning research must follow these)

Evidence base: 6 closed picks (paper, 10-07 to 10-13), net +$0.89 (PENG +2.07, UNH +0.42, SH +0.03, SOXS -0.11, HUM -0.32, CEG -0.74), plus 1 open live pick (AZZ, flat). Tiny sample: treat as leanings, not laws.

Catalysts
- Prefer lasting estimate changes (guidance raise, rating reversal) over one-day headlines. PENG (+$2.07, +8.3%) was a guidance raise and is the only real winner; AZZ (beat and raise, 10-14) closed flat (~$137.85 vs $137.57 fill) on a day the S&P fell 1.1% and small caps ~2%, so the stock held its gains through a rate-driven selloff.
- Don't chase a big gap on one unconfirmed source: CEG (+12% gap, -$0.74, -5%) is the largest loss.
- A beat-and-raise whose gap fully fades in the first hour is a sell signal, not a dip: UNH (10-13) was closed near flat on that rule (+$0.42).

Entry
- Picks now execute within minutes as limit orders capped at max_entry_price (AZZ filled 9:38 at $137.57 under a $140 cap). Still give every gap pick a cap (HUM bought $441, -$0.32) and judge the thesis on the first-hour price, not premarket.
- Prefer picks whose thesis survives the open without needing the gap (PENG, AZZ).

Exits
- Write a concrete "wrong if" for every pick and act on it at the very next refresh. SOXS, HUM and UNH were closed on their own rules for small losses/gains; this kept losses to cents except CEG, where it was applied late.
- Close on the stated kill condition even before the hold limit (PENG closed +8% on the sector kill condition).
- Don't close a pick for following the market down when its own kill line isn't hit: AZZ dipped -2.1% at 13:20 with the tape and recovered to flat by the close.

Sizing and market regime
- Live equity is ~$75, so conviction 2 is ~$19 and 3 is ~$30; one bad gap pick costs about $1. Reserve conviction 3 for catalysts confirmed by primary sources.
- Before CPI/FOMC/major event mornings, carrying new picks into the print has had no edge; a no-pick afternoon before the print stays the default.
- Puts only fit stocks under ~$15 at the $11/$18/$30 budget; check the chain before picking (JNJ 10-13 didn't fit).
- On a macro trend day (hot CPI 10-14: yields up, Nasdaq-100 -0.6% by 10:20, QQQ -1.43% 9:35-15:15) the move kept going all day. I skipped a 10:20 same-day SQQQ pick as "chasing"; it would have caught roughly another -0.8% of QQQ (about +$0.45 at conviction 2). One data point: next time a hot macro print sets a clear direction by 10:20, consider a conviction-2 same-day SQQQ/TQQQ pick with a tight stop instead of sitting out.

Scalper / scalp_bias
- Scalper is on paper (70-session replay found no after-cost edge). 10-14 bear bias: 10 SQQQ trips, 7 winners, +$0.20 on paper; the right call made cents at scalp size, again.
- Direction-call hit rate: 1 of 2 (10-13 bear wrong at QQQ +0.38%, 10-14 bear right at QQQ -1.43%). Not yet reliable; size direction picks at conviction 2 at most until it is.

Process
- The scheduled learn workflow can start 30+ minutes late; the 16:46 review may need to dispatch it by hand (done 10-14). Lean on ledger/*.csv for same-day results if it hasn't run.
- Benchmark since live start (10-13 12:40 ET): bot $75.02 (+0.03%) vs S&P 500 $74.17 (-1.10%). Mostly cash, so this lead is from sitting out a down day, not from picks.
