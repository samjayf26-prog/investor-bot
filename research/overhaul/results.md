# Profit overhaul: evidence (real market data)  Generated 2026-10-30 21:11 UTC by research/overhaul/overhaul_backtest.py on GitHub Actions. 
Data: 213 symbols loaded ({'yahoo': 207, 'alpaca': 6}); SPY from 2000-01-03 to 2026-10-30.
 ## 1. Overnight (close to next open) vs intraday (open to close)  Total-return adjusted daily bars (dividends land in the overnight leg). This extends review/overnight-results.md (which used 1 and 5 years) to the full sample. 
| ETF | period | days | overnight total | intraday total | overnight CAGR | intraday CAGR | nights up | mean night | mean day | night vol | day vol |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 2000-2010 | 2766 | +63.4% | -35.7% | +4.6% | -3.9% | 54% | +0.020% | -0.009% | 12% | 19% |
| SPY | 2011-2018 | 2012 | +84.3% | +26.8% | +8.0% | +3.0% | 55% | +0.032% | +0.014% | 9% | 11% |
| SPY | 2019-now | 1969 | +106.4% | +64.2% | +9.7% | +6.5% | 57% | +0.040% | +0.029% | 13% | 14% |
| SPY | last 1y | 252 | +10.5% | +0.6% | +10.5% | +0.6% | 56% | +0.041% | +0.004% | 9% | 10% |
| SPY | full | 6747 | +521.4% | +33.8% | +7.1% | +1.1% | 55% | +0.030% | +0.009% | 11% | 15% |
| QQQ | 2000-2010 | 2766 | +172.0% | -78.1% | +9.5% | -12.9% | 54% | +0.041% | -0.037% | 16% | 30% |
| QQQ | 2011-2018 | 2012 | +153.4% | +22.0% | +12.4% | +2.5% | 57% | +0.048% | +0.014% | 10% | 14% |
| QQQ | 2019-now | 1969 | +144.0% | +92.3% | +12.1% | +8.7% | 57% | +0.050% | +0.040% | 15% | 18% |
| QQQ | last 1y | 252 | +9.4% | -0.3% | +9.4% | -0.3% | 54% | +0.039% | +0.003% | 14% | 15% |
| QQQ | full | 6747 | +1582.0% | -48.5% | +11.1% | -2.5% | 56% | +0.046% | +0.000% | 14% | 23% |
 Year by year, QQQ and TQQQ (TQQQ from 2011): 
| year | QQQ overnight | QQQ intraday | TQQQ overnight | TQQQ intraday | TQQQ close-to-close |
|---|---|---|---|---|---|
| 2011 | +2% | +1% | +8% | -15% | -8% |
| 2012 | +13% | +4% | +51% | +1% | +52% |
| 2013 | +20% | +14% | +73% | +39% | +140% |
| 2014 | +17% | +1% | +56% | +0% | +57% |
| 2015 | +12% | -2% | +38% | -15% | +17% |
| 2016 | -1% | +8% | -4% | +16% | +11% |
| 2017 | +21% | +10% | +70% | +29% | +118% |
| 2018 | +15% | -13% | +44% | -44% | -20% |
| 2019 | +15% | +20% | +47% | +59% | +134% |
| 2020 | +26% | +18% | +62% | +30% | +110% |
| 2021 | +16% | +10% | +52% | +21% | +83% |
| 2022 | -21% | -15% | -58% | -50% | -79% |
| 2023 | +12% | +39% | +21% | +145% | +198% |
| 2024 | +32% | -5% | +95% | -19% | +58% |
| 2025 | +16% | +4% | +33% | +1% | +34% |
| 2026 | +7% | +6% | +10% | +7% | +18% |
 QQQ overnight return conditional on the previous session (since 2011): 
| previous close-to-close | nights | mean overnight | nights up | total |
|---|---|---|---|---|
| down 1%+ | 600 | +0.076% | 59% | +51% |
| down 0-1% | 1151 | +0.048% | 57% | +68% |
| up 0-1% | 1512 | +0.048% | 56% | +101% |
| up 1%+ | 718 | +0.030% | 56% | +21% |
 ## 2. What to do with the idle cash (the 'core'), daily data since 2011  All strategies trade at the official open/close (section 7 measures the cost of the bot's real run times). Costs: one-way spread+slippage per trade of 0.01% (SPY/QQQ), 0.03% (3x ETFs), 0.02% (TLT), charged on every position change; the overnight-only strategies pay a round trip every day. Sharpe uses a 0% cash rate. 'worst year' is the worst calendar year. Dividends included; TQQQ's fees and financing are in its prices. No taxes. 
 ### Core strategies, 2011 to now 
| strategy | CAGR | vol | Sharpe | max DD | worst day | worst year | 1st half CAGR | 2nd half CAGR | $75 becomes | last 1y | last 3y |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY buy & hold (today's core) | +13.9% | 17% | 0.85 | -34% | -10.9% | -18% (2022) | +12.1% | +15.7% | $588 | +11.1% | +87.7% |
| QQQ buy & hold | +18.3% | 21% | 0.92 | -35% | -12.0% | -33% (2022) | +15.9% | +20.8% | $1,071 | +9.1% | +100.5% |
| TQQQ buy & hold | +38.0% | 61% | 0.84 | -82% | -34.5% | -79% (2022) | +40.0% | +36.1% | $12,179 | +3.6% | +290.9% |
| SPY overnight only | +3.4% | 11% | 0.37 | -30% | -10.5% | -18% (2022) | +2.4% | +4.4% | $128 | +5.1% | +33.5% |
| QQQ overnight only | +6.6% | 13% | 0.57 | -31% | -9.5% | -25% (2022) | +6.4% | +6.9% | $207 | +4.1% | +52.2% |
| QLD (2x) overnight only | +3.0% | 25% | 0.24 | -61% | -20.9% | -52% (2022) | +4.9% | +1.1% | $119 | -1.4% | +60.6% |
| TQQQ overnight only | +12.8% | 38% | 0.51 | -74% | -28.9% | -64% (2022) | +18.8% | +7.1% | $501 | -0.1% | +125.9% |
| TQQQ overnight only, only when QQQ > 200d SMA (else cash) | +19.2% | 29% | 0.76 | -50% | -20.0% | -20% (2022) | +16.4% | +22.1% | $1,204 | -11.1% | +161.1% |
| TQQQ overnight when QQQ > SMA200, else SPY overnight | +18.2% | 30% | 0.72 | -56% | -20.0% | -31% (2022) | +17.7% | +18.7% | $1,052 | -7.7% | +154.0% |
| TQQQ overnight only, vol-targeted 20% (QQQ 20d vol) | +8.1% | 13% | 0.67 | -24% | -7.3% | -17% (2022) | +8.9% | +7.3% | $257 | -1.2% | +56.7% |
| TQQQ overnight only, vol-targeted 20% + SMA200 filter | +8.4% | 12% | 0.74 | -21% | -7.3% | -11% (2016) | +7.5% | +9.2% | $267 | -5.2% | +58.1% |
| TQQQ overnight only, vol-targeted 30% (QQQ 20d vol) | +11.3% | 19% | 0.67 | -34% | -10.6% | -25% (2022) | +12.6% | +10.1% | $410 | -2.6% | +87.6% |
| TQQQ overnight only, vol-targeted 30% + SMA200 filter | +11.9% | 17% | 0.74 | -30% | -10.6% | -16% (2016) | +10.6% | +13.2% | $442 | -8.3% | +90.7% |
| TQQQ overnight only, vol-targeted 40% (QQQ 20d vol) | +13.9% | 23% | 0.67 | -43% | -11.7% | -32% (2022) | +15.6% | +12.2% | $584 | -3.7% | +110.1% |
| TQQQ overnight only, vol-targeted 40% + SMA200 filter | +14.8% | 21% | 0.76 | -35% | -10.6% | -18% (2016) | +13.1% | +16.4% | $659 | -11.2% | +115.5% |
| TQQQ when QQQ > SMA200, else SPY (full-time) | +35.5% | 48% | 0.87 | -61% | -20.3% | -48% (2022) | +29.4% | +41.9% | $9,113 | -3.3% | +254.0% |
| TQQQ when QQQ > SMA200, else TLT (full-time) | +28.9% | 48% | 0.77 | -64% | -20.3% | -58% (2022) | +23.3% | +34.8% | $4,158 | -5.7% | +223.1% |
| QLD (2x) when QQQ > SMA200, else SPY (full-time) | +27.4% | 34% | 0.89 | -49% | -13.8% | -37% (2022) | +22.9% | +32.1% | $3,457 | +4.4% | +172.7% |
| TQQQ vol-targeted 30% + SMA200, rest SPY (full-time) | +30.0% | 35% | 0.92 | -45% | -12.2% | -31% (2022) | +26.6% | +33.5% | $4,717 | +3.5% | +188.7% |
| TQQQ overnight (SMA200 filter) + SPY during the day | +18.7% | 31% | 0.70 | -54% | -20.4% | -28% (2022) | +15.2% | +22.3% | $1,124 | -15.0% | +172.2% |
 ### Core strategies: calendar-year returns 
| year | SPY buy & hold (today's core) | QQQ buy & hold | TQQQ buy & hold | SPY overnight only | QQQ overnight only | QLD (2x) overnight only | TQQQ overnight only | TQQQ overnight only, only when QQQ > 200d SMA (else cash) | TQQQ overnight when QQQ > SMA200, else SPY overnight |
|---|---|---|---|---|---|---|---|---|---|
| 2011 | +1% | +2% | -12% | -1% | -4% | -12% | -9% | -9% | -6% |
| 2012 | +16% | +18% | +52% | +1% | +8% | +12% | +30% | +21% | +23% |
| 2013 | +32% | +37% | +140% | +9% | +14% | +23% | +49% | +49% | +49% |
| 2014 | +13% | +19% | +57% | +6% | +12% | +16% | +34% | +34% | +34% |
| 2015 | +1% | +9% | +17% | -3% | +7% | +2% | +18% | +16% | +18% |
| 2016 | +12% | +7% | +11% | -8% | -5% | -20% | -17% | -19% | -20% |
| 2017 | +22% | +33% | +118% | +9% | +15% | +18% | +46% | +46% | +46% |
| 2018 | -5% | -0% | -20% | +9% | +10% | +11% | +24% | +8% | +13% |
| 2019 | +31% | +39% | +134% | +9% | +10% | +11% | +26% | +33% | +32% |
| 2020 | +18% | +48% | +110% | +9% | +20% | +21% | +39% | +58% | +51% |
| 2021 | +29% | +27% | +83% | +12% | +11% | +14% | +30% | +30% | +30% |
| 2022 | -18% | -33% | -79% | -18% | -25% | -52% | -64% | -20% | -31% |
| 2023 | +26% | +55% | +198% | +1% | +6% | -1% | +5% | +4% | +4% |
| 2024 | +25% | +26% | +58% | +18% | +26% | +37% | +68% | +68% | +68% |
| 2025 | +18% | +21% | +34% | +3% | +10% | +8% | +14% | +48% | +39% |
| 2026 | +12% | +13% | +18% | +4% | +2% | -3% | -3% | -13% | -10% |
 Stress windows (total return of each strategy): 
| strategy | 2018 Q4 | Covid 2020-02-19..03-23 | 2022 bear | 2025-04 tariff shock | last 12 months |
|---|---|---|---|---|---|
| SPY buy & hold | -14% | -33% | -18% | -6% | +11% |
| TQQQ buy & hold | -48% | -69% | -79% | -27% | +4% |
| TQQQ overnight only | +4% | -64% | -64% | -38% | -0% |
| TQQQ overnight, SMA200 filter | -10% | -48% | -20% | -6% | -11% |
| TQQQ overnight, vol 30% + SMA200 | -4% | -18% | -8% | -3% | -8% |
| TQQQ>SMA200 else SPY (full-time) | -49% | -60% | -48% | -18% | -3% |
 TQQQ overnight gaps since 2011: 3980 nights; worst -28.8% (2020-03-16), nights below -10%: 14, below -15%: 6, below -25%: 1; best +16.7%.
 ## 3. Turn of the month  TOM days = the last trading day of a month and the first three of the next. Position held over the day (prior close to close). Does the old finding (most of the market's return lands in those 4 days) still hold? 
| ETF | period | TOM days | mean TOM day | other days | mean other day | TOM total | other total | TOM share of days |
|---|---|---|---|---|---|---|---|---|
| SPY | 2000-2010 | 528 | +0.073% | 2238 | -0.003% | +41% | -25% | 19% |
| SPY | 2011-2018 | 384 | +0.029% | 1628 | +0.050% | +10% | +112% | 19% |
| SPY | 2019-now | 376 | +0.090% | 1593 | +0.064% | +37% | +148% | 19% |
| QQQ | 2000-2010 | 528 | +0.065% | 2238 | -0.011% | +24% | -52% | 19% |
| QQQ | 2011-2018 | 384 | +0.067% | 1628 | +0.061% | +27% | +144% | 19% |
| QQQ | 2019-now | 376 | +0.121% | 1593 | +0.083% | +51% | +211% | 19% |
| TQQQ | 2000-2010 | 44 | +0.873% | 180 | +0.184% | +43% | +25% | 20% |
| TQQQ | 2011-2018 | 384 | +0.187% | 1628 | +0.173% | +70% | +606% | 19% |
| TQQQ | 2019-now | 376 | +0.331% | 1593 | +0.212% | +138% | +492% | 19% |
 ## 4. Dip buying (short-term mean reversion) on QQQ, traded with TQQQ  Rules known at the close, entered at that close, exit at the close. Returns per trade are TQQQ close-to-close minus 0.06% round trip. 'excess' = vs holding SPY over the same days. 
| rule | trades | win rate | mean/trade | t | total (sum) | excess vs SPY/trade | 1st half sum | 2nd half sum | days in market |
|---|---|---|---|---|---|---|---|---|---|
| 3 down closes, QQQ > SMA200; exit first up close or 5 days | 134 | 74% | +0.93% | +2.5 | +125% | +0.63% | +49% | +75% | 6% |
| 3 down closes, any trend; exit first up close or 5 days | 176 | 74% | +1.39% | +3.8 | +244% | +0.98% | +58% | +186% | 7% |
| RSI(2) < 10, QQQ > SMA200; exit RSI(2) > 60 or 5 days | 343 | 71% | +0.77% | +2.3 | +265% | +0.51% | +79% | +186% | 28% |
| RSI(2) < 10, any trend; exit RSI(2) > 60 or 5 days | 414 | 70% | +1.02% | +3.0 | +422% | +0.69% | +96% | +326% | 33% |
| QQQ 3%+ below its 5-day high, > SMA200; exit first up close or 5 days | 133 | 74% | +1.31% | +3.4 | +174% | +0.95% | +34% | +140% | 5% |
 ## 5. Monthly ETF momentum rotation (for completeness)  At each month end, rank SPY, QQQ, IWM, EFA, EEM, GLD, TLT by trailing total return and hold the leader for the next month; cash when the leader's trailing return is negative. Costs 0.02% per switch. 
 ### ETF momentum rotation vs buy & hold, 2011 to now 
| strategy | CAGR | vol | Sharpe | max DD | worst day | worst year | 1st half CAGR | 2nd half CAGR | $75 becomes | last 1y | last 3y |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rotation, 6-month lookback | +6.8% | 18% | 0.45 | -42% | -12.0% | -22% (2022) | +5.1% | +8.5% | $212 | +4.2% | +111.2% |
| rotation, 12-month lookback | +6.9% | 18% | 0.46 | -38% | -10.3% | -21% (2016) | +2.1% | +11.8% | $214 | +11.9% | +144.8% |
| rotation, 12-1 month (skip last month) lookback | +11.4% | 19% | 0.67 | -29% | -12.0% | -12% (2022) | +8.2% | +14.8% | $415 | +2.8% | +139.6% |
| SPY buy & hold | +13.9% | 17% | 0.85 | -34% | -10.9% | -18% (2022) | +12.1% | +15.7% | $588 | +11.1% | +87.7% |
| QQQ buy & hold | +18.3% | 21% | 0.92 | -35% | -12.0% | -33% (2022) | +15.9% | +20.8% | $1,071 | +9.1% | +100.5% |
 ## 6. Buying stocks after big news gaps, ~150 large and mid caps  Event: the stock opens 3%+ away from its previous close *after removing SPY's own gap* (so the move is the stock's news). Returns are vs SPY over the same span, in the direction of the news (for down gaps, 'long' = buying the fallen stock). The universe is today's names, so the long side is flattered (survivorship) and the bearish side penalised. t uses one row per event. 
Universe with data: 201 stocks, 2016 to now. Events: 12603 (up 6658, down 5945). 
 ### Good-news gaps (long) 
| entry | hold (trading days) | events | avg vs SPY | median | t | share that paid | 2016-20 avg | 2021-now avg |
|---|---|---|---|---|---|---|---|---|
| buy at the close of day 0 if held, gap 12%+ | 10 | 432 | +1.59% | +0.99% | +2.7 | 55% | +2.66% | +1.12% |
| buy at the close of day 0 if held, gap 3-6% | 10 | 4836 | +0.30% | -0.45% | +1.8 | 48% | +0.97% | -0.02% |
| buy at the close of day 0 if held, gap 6-12% | 10 | 1390 | +1.07% | +0.13% | +3.3 | 51% | +1.08% | +1.07% |
| buy at the close of day 0 if the gap faded | 5 | 3434 | +0.10% | -0.18% | +0.7 | 49% | +0.32% | -0.02% |
| buy at the close of day 0 if the gap faded | 10 | 3434 | +0.65% | -0.27% | +3.3 | 48% | +1.25% | +0.35% |
| buy at the close of day 0 if the gap faded | 20 | 3434 | +1.45% | -0.08% | +5.1 | 50% | +2.84% | +0.75% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 5 | 3224 | -0.14% | -0.41% | -1.0 | 47% | +0.23% | -0.33% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 10 | 3224 | +0.43% | -0.15% | +2.1 | 49% | +0.93% | +0.19% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 20 | 3224 | +1.20% | -0.34% | +3.9 | 49% | +2.74% | +0.44% |
| buy at the open of day 1 after a held gap | 5 | 3224 | -0.30% | -0.44% | -2.1 | 46% | -0.16% | -0.37% |
| buy at the open of day 1 after a held gap | 10 | 3224 | +0.27% | -0.26% | +1.4 | 49% | +0.53% | +0.14% |
| buy at the open of day 1 after a held gap | 20 | 3224 | +1.04% | -0.50% | +3.5 | 48% | +2.35% | +0.39% |
| buy at the open, day 0 | 0 | 6658 | +0.00% | -0.17% | +0.0 | 48% | +0.03% | -0.01% |
| buy at the open, day 0 | 5 | 6658 | -0.03% | -0.40% | -0.3 | 48% | +0.32% | -0.20% |
| buy at the open, day 0 | 10 | 6658 | +0.53% | -0.30% | +3.5 | 49% | +1.14% | +0.23% |
| buy at the open, day 0 | 20 | 6658 | +1.33% | -0.51% | +6.1 | 48% | +2.86% | +0.57% |
| buy at the open, day 0, gap 12%+ | 10 | 432 | +2.08% | +1.26% | +3.1 | 56% | +3.28% | +1.56% |
| buy at the open, day 0, gap 3-6% | 10 | 4836 | +0.22% | -0.54% | +1.3 | 47% | +0.98% | -0.14% |
| buy at the open, day 0, gap 6-12% | 10 | 1390 | +1.12% | +0.37% | +3.1 | 52% | +1.09% | +1.15% |
| held gap, close entry, 20-day max hold, 10% target, no stop | 20 | 3224 | +0.67% | +1.68% | +3.3 | 56% | +1.53% | +0.25% |
| held gap, close entry, 20-day max hold, 7% stop + 10% target | 20 | 3224 | +0.18% | -1.29% | +1.1 | 46% | +0.87% | -0.16% |
| held gap, close entry, 20-day max hold, 7% stop + 15% target | 20 | 3224 | +0.10% | -2.45% | +0.6 | 42% | +1.06% | -0.37% |
| held gap, close entry, 20-day max hold, 7% stop, no target | 20 | 3224 | +0.48% | -3.13% | +1.8 | 39% | +1.67% | -0.12% |
| held gap, close entry, 20-day max hold, no stop, no target (time exit only) | 20 | 3224 | +1.20% | -0.34% | +3.9 | 49% | +2.74% | +0.44% |
 ### Bad-news gaps (the bearish side: positive = betting against the stock paid) 
| entry | hold (trading days) | events | avg vs SPY | median | t | share that paid | 2016-20 avg | 2021-now avg |
|---|---|---|---|---|---|---|---|---|
| buy at the close of day 0 if held, gap 12%+ | 10 | 340 | -0.87% | +0.13% | -1.5 | 50% | -2.02% | -0.44% |
| buy at the close of day 0 if held, gap 3-6% | 10 | 4395 | -1.18% | -0.00% | -6.7 | 50% | -2.02% | -0.79% |
| buy at the close of day 0 if held, gap 6-12% | 10 | 1210 | -1.59% | -0.38% | -4.6 | 48% | -1.48% | -1.64% |
| buy at the close of day 0 if the gap faded | 5 | 3130 | -0.71% | -0.16% | -4.7 | 49% | -1.18% | -0.51% |
| buy at the close of day 0 if the gap faded | 10 | 3130 | -1.29% | -0.24% | -6.2 | 49% | -1.91% | -1.01% |
| buy at the close of day 0 if the gap faded | 20 | 3130 | -1.92% | -0.22% | -6.7 | 49% | -2.94% | -1.47% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 5 | 2815 | -0.89% | +0.02% | -5.2 | 50% | -0.69% | -0.98% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 10 | 2815 | -1.20% | +0.06% | -5.4 | 50% | -1.92% | -0.87% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 20 | 2815 | -1.77% | -0.10% | -5.8 | 49% | -3.56% | -0.92% |
| buy at the open of day 1 after a held gap | 5 | 2815 | -0.85% | -0.05% | -5.1 | 50% | -0.68% | -0.94% |
| buy at the open of day 1 after a held gap | 10 | 2815 | -1.17% | +0.06% | -5.3 | 51% | -1.90% | -0.83% |
| buy at the open of day 1 after a held gap | 20 | 2815 | -1.79% | +0.11% | -5.7 | 51% | -3.56% | -0.94% |
| buy at the open, day 0 | 0 | 5945 | -0.31% | -0.26% | -5.8 | 47% | -0.35% | -0.29% |
| buy at the open, day 0 | 5 | 5945 | -1.11% | -0.29% | -8.8 | 48% | -1.31% | -1.02% |
| buy at the open, day 0 | 10 | 5945 | -1.56% | -0.41% | -9.7 | 48% | -2.26% | -1.24% |
| buy at the open, day 0 | 20 | 5945 | -2.17% | -0.30% | -10.1 | 49% | -3.56% | -1.53% |
| buy at the open, day 0, gap 12%+ | 10 | 340 | -1.19% | -0.38% | -1.7 | 50% | -1.92% | -0.91% |
| buy at the open, day 0, gap 3-6% | 10 | 4395 | -1.57% | -0.43% | -8.6 | 47% | -2.45% | -1.15% |
| buy at the open, day 0, gap 6-12% | 10 | 1210 | -1.65% | -0.19% | -4.2 | 49% | -1.64% | -1.65% |
 ### Buying the fallen stock after a bad-news gap (long side) 
| entry | hold | events | avg vs SPY | t | share that paid |
|---|---|---|---|---|---|
| buy at the close of day 0 if the gap faded | 5 | 3130 | +0.71% | +4.7 | 51% |
| buy at the close of day 0 if the gap faded | 10 | 3130 | +1.29% | +6.2 | 51% |
| buy at the close of day 0 if the gap faded | 20 | 3130 | +1.92% | +6.7 | 51% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 5 | 2815 | +0.89% | +5.2 | 50% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 10 | 2815 | +1.20% | +5.4 | 50% |
| buy at the close of day 0 if the gap held (close on the news side of the open) | 20 | 2815 | +1.77% | +5.8 | 51% |
| buy at the open, day 0 | 0 | 5945 | +0.31% | +5.8 | 53% |
| buy at the open, day 0 | 5 | 5945 | +1.11% | +8.8 | 52% |
| buy at the open, day 0 | 10 | 5945 | +1.56% | +9.7 | 52% |
| buy at the open, day 0 | 20 | 5945 | +2.17% | +10.1 | 51% |
 ## 7. Cost of the bot's run times (Alpaca minute bars, SIP) 
### QQQ, last 5 years (1252 sessions) 
| leg | mean per day | total compounded | std per day |
|---|---|---|---|
| open to 09:35 | +0.001% | +1.0% | 0.24% |
| open to 09:50 | +0.003% | +2.5% | 0.41% |
| open to 10:00 | +0.008% | +8.6% | 0.48% |
| open to 10:20 | +0.004% | +3.1% | 0.60% |
| 15:30 to close | +0.002% | +2.2% | 0.31% |
| 15:45 to close | +0.009% | +11.7% | 0.24% |
| 15:50 to close | +0.007% | +8.7% | 0.22% |
| overnight, close to open (ideal) | +0.037% | +51.3% | 0.86% |
| overnight, 15:50 to 9:35 next day (the bot's runs) | +0.044% | +65.1% | 0.88% |
| intraday, open to close | +0.025% | +25.0% | 1.20% |

### TQQQ, last 3 years (752 sessions) 
| leg | mean per day | total compounded | std per day |
|---|---|---|---|
| open to 09:35 | -0.012% | -10.2% | 0.62% |
| open to 09:50 | -0.004% | -7.2% | 1.06% |
| open to 10:00 | -0.008% | -11.3% | 1.28% |
| open to 10:20 | +0.011% | -2.2% | 1.67% |
| 15:30 to close | +0.018% | +12.1% | 0.80% |
| 15:45 to close | +0.040% | +32.9% | 0.65% |
| 15:50 to close | +0.007% | +3.7% | 0.60% |
| overnight, close to open (ideal) | +0.132% | +81.2% | 3.01% |
| overnight, 15:50 to 9:35 next day (the bot's runs) | +0.124% | +69.1% | 3.05% |
| intraday, open to close | +0.067% | +16.5% | 3.10% |

 Done in 243s.
