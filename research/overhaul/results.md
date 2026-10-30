# Profit overhaul: evidence (real market data)  Generated 2026-10-30 21:22 UTC by research/overhaul/overhaul_backtest.py on GitHub Actions. 
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
| up 1%+ | 718 | +0.030% | 57% | +21% |
 ## 2. What to do with the idle cash (the 'core'), daily data since 2011 (base costs)  All strategies trade at the official open/close (section 7 measures the cost of the bot's real run times). One-way costs this run: SPY/QQQ 0.005%, 3x ETFs 0.010%, charged on every position change; the overnight-only strategies pay a round trip every day. Sharpe uses a 0% cash rate. 'worst year' is the worst calendar year. Dividends included; TQQQ's fees and financing are in its prices. No taxes. Signals use only data known at the prior close. 
 ### Core strategies, 2011 to now (base costs) 
| strategy | CAGR | vol | Sharpe | max DD | worst day | worst year | 1st half CAGR | 2nd half CAGR | $75 becomes | last 1y | last 3y |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY buy & hold (today's core) | +13.9% | 17% | 0.85 | -34% | -10.9% | -18% (2022) | +12.1% | +15.7% | $588 | +11.1% | +87.7% |
| QQQ buy & hold | +18.3% | 21% | 0.92 | -35% | -12.0% | -33% (2022) | +15.9% | +20.8% | $1,071 | +9.1% | +100.5% |
| TQQQ buy & hold | +38.0% | 61% | 0.84 | -82% | -34.5% | -79% (2022) | +40.0% | +36.1% | $12,179 | +3.6% | +290.9% |
| QQQ overnight only | +9.4% | 13% | 0.77 | -29% | -9.5% | -23% (2022) | +9.1% | +9.6% | $309 | +6.7% | +64.2% |
| TQQQ overnight only | +24.7% | 38% | 0.78 | -70% | -28.8% | -60% (2022) | +31.3% | +18.4% | $2,459 | +10.5% | +205.6% |
| TQQQ overnight only, when QQQ > SMA200 (else cash) | +29.9% | 29% | 1.06 | -50% | -19.9% | -19% (2022) | +27.3% | +32.4% | $4,649 | -2.1% | +245.2% |
| TQQQ overnight only, vol-target 30% + SMA200 | +18.7% | 17% | 1.09 | -28% | -10.6% | -11% (2016) | +18.4% | +19.0% | $1,123 | -3.3% | +126.7% |
| TQQQ overnight only, vol-target 40% + SMA200 | +23.2% | 21% | 1.10 | -32% | -10.6% | -12% (2016) | +22.5% | +24.0% | $2,034 | -4.7% | +168.9% |
| A. TQQQ when QQQ > SMA200, else SPY (full-time) | +35.7% | 48% | 0.88 | -61% | -20.3% | -48% (2022) | +29.7% | +42.0% | $9,315 | -3.3% | +254.6% |
| TQQQ when QQQ > SMA200, else cash (full-time) | +30.8% | 47% | 0.81 | -56% | -20.3% | -43% (2022) | +23.7% | +38.4% | $5,229 | -7.2% | +229.3% |
| QLD (2x) when QQQ > SMA200, else SPY (full-time) | +27.6% | 34% | 0.90 | -49% | -13.8% | -37% (2022) | +23.1% | +32.3% | $3,533 | +4.5% | +173.2% |
| B20. TQQQ vol-target 20% + SMA200, rest SPY (full-time) | +25.7% | 29% | 0.94 | -42% | -10.9% | -27% (2022) | +23.4% | +28.1% | $2,790 | +6.9% | +152.5% |
| B30. TQQQ vol-target 30% + SMA200, rest SPY (full-time) | +30.2% | 35% | 0.93 | -45% | -12.2% | -31% (2022) | +26.8% | +33.7% | $4,856 | +3.7% | +190.1% |
| B40. TQQQ vol-target 40% + SMA200, rest SPY (full-time) | +32.7% | 40% | 0.91 | -49% | -13.7% | -35% (2022) | +28.4% | +37.3% | $6,586 | +0.4% | +214.6% |
| B30q. same, rest QQQ instead of SPY | +31.4% | 37% | 0.92 | -47% | -12.2% | -42% (2022) | +27.7% | +35.3% | $5,634 | +1.6% | +193.4% |
| B30c. same, rest cash | +22.3% | 29% | 0.83 | -38% | -12.2% | -19% (2022) | +19.5% | +25.1% | $1,796 | -3.6% | +118.3% |
| B30 with a 10-point rebalance band | +29.8% | 35% | 0.92 | -46% | -12.2% | -32% (2022) | +26.5% | +33.0% | $4,594 | +5.3% | +190.4% |
| TQQQ vol-target 30%, no trend filter, rest SPY | +33.2% | 39% | 0.93 | -51% | -14.4% | -47% (2022) | +32.5% | +33.9% | $6,964 | +6.4% | +196.6% |
| B30 with SMA100 instead of SMA200 | +25.0% | 34% | 0.83 | -46% | -12.2% | -32% (2022) | +23.0% | +27.0% | $2,553 | -2.5% | +144.1% |
| B30 with SMA150 instead of SMA200 | +31.3% | 35% | 0.96 | -45% | -12.2% | -28% (2022) | +27.9% | +34.7% | $5,505 | +0.7% | +167.6% |
| B30 with SMA250 instead of SMA200 | +29.9% | 36% | 0.92 | -45% | -12.2% | -33% (2022) | +27.4% | +32.5% | $4,700 | +3.7% | +184.1% |
| B30 with 10-day vol instead of 20-day | +28.1% | 36% | 0.88 | -46% | -14.5% | -32% (2022) | +26.5% | +29.7% | $3,751 | -8.6% | +156.8% |
| B30 with 60-day vol instead of 20-day | +27.3% | 35% | 0.87 | -50% | -12.7% | -33% (2022) | +26.0% | +28.6% | $3,393 | -0.1% | +164.7% |
| B30 + dip overlay (3 down closes: all-in TQQQ until an up close, max 5 days) | +39.9% | 39% | 1.06 | -42% | -13.9% | -17% (2016) | +28.8% | +51.9% | $15,033 | +18.7% | +274.3% |
 ### Core strategies: calendar-year returns 
| year | SPY buy & hold (today's core) | QQQ buy & hold | TQQQ buy & hold | TQQQ overnight only | TQQQ overnight only, when QQQ > SMA200 (else cash) | TQQQ overnight only, vol-target 30% + SMA200 | A. TQQQ when QQQ > SMA200, else SPY (full-time) | B20. TQQQ vol-target 20% + SMA200, rest SPY (full-time) | B30. TQQQ vol-target 30% + SMA200, rest SPY (full-time) | B40. TQQQ vol-target 40% + SMA200, rest SPY (full-time) | B30 with a 10-point rebalance band |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2011 | +1% | +2% | -12% | +0% | -2% | -3% | -27% | -7% | -12% | -18% | -13% |
| 2012 | +16% | +18% | +52% | +44% | +32% | +22% | +34% | +31% | +34% | +31% | +33% |
| 2013 | +32% | +37% | +140% | +64% | +64% | +43% | +140% | +76% | +103% | +125% | +105% |
| 2014 | +13% | +19% | +57% | +49% | +49% | +33% | +57% | +31% | +39% | +47% | +39% |
| 2015 | +1% | +9% | +17% | +31% | +27% | +13% | +4% | -1% | -3% | -0% | -1% |
| 2016 | +12% | +7% | +11% | -8% | -13% | -11% | +1% | +2% | -2% | -2% | -1% |
| 2017 | +22% | +33% | +118% | +61% | +61% | +55% | +118% | +84% | +107% | +116% | +103% |
| 2018 | -5% | -0% | -20% | +37% | +18% | +7% | -22% | -7% | -10% | -14% | -11% |
| 2019 | +31% | +39% | +134% | +40% | +45% | +19% | +73% | +48% | +55% | +61% | +49% |
| 2020 | +18% | +48% | +110% | +54% | +73% | +33% | +117% | +52% | +69% | +82% | +65% |
| 2021 | +29% | +27% | +83% | +44% | +44% | +19% | +83% | +49% | +59% | +65% | +60% |
| 2022 | -18% | -33% | -79% | -60% | -19% | -7% | -48% | -27% | -31% | -35% | -32% |
| 2023 | +26% | +55% | +198% | +15% | +14% | +14% | +128% | +61% | +81% | +100% | +85% |
| 2024 | +25% | +26% | +58% | +86% | +86% | +44% | +58% | +40% | +45% | +50% | +42% |
| 2025 | +18% | +21% | +34% | +26% | +61% | +47% | +31% | +23% | +28% | +29% | +30% |
| 2026 | +12% | +13% | +18% | +6% | -6% | -6% | +10% | +13% | +13% | +12% | +13% |
 Stress windows (total return of each strategy): 
| strategy | 2015-08 flash crash | 2018 Q4 | Covid 2020-02-19..03-23 | 2022 bear | 2025 tariff shock | last 12 months |
|---|---|---|---|---|---|---|
| SPY buy & hold | -11% | -19% | -33% | -18% | -19% | +11% |
| QQQ buy & hold | -11% | -23% | -27% | -33% | -23% | +9% |
| TQQQ buy & hold | -31% | -57% | -69% | -79% | -57% | +4% |
| TQQQ overnight only, vol 30% + SMA200 | -7% | -4% | -18% | -7% | -1% | -3% |
| A. TQQQ>SMA200 else SPY (full-time) | -25% | -52% | -60% | -48% | -39% | -3% |
| B20. vol 20% + SMA200, rest SPY | -18% | -33% | -41% | -27% | -27% | +7% |
| B30. vol 30% + SMA200, rest SPY | -21% | -39% | -44% | -31% | -31% | +4% |
| B40. vol 40% + SMA200, rest SPY | -24% | -43% | -47% | -35% | -34% | +0% |
| B30 + dip overlay | -30% | -41% | -40% | +3% | -31% | +19% |
 B30 exposure: average TQQQ weight 59% (i.e. average leverage 2.17x counting the SPY rest), fully in TQQQ on 13% of days, zero TQQQ on 15% of days; the weight changed by more than 10 points on 5.8% of days (banded version trades on 9.3% of days).
B30 weight today: 50% TQQQ (QQQ 20d vol 20%, QQQ above its 200-day SMA).
 TQQQ overnight gaps since 2011: 3980 nights; worst -28.8% (2020-03-16), nights below -10%: 14, below -15%: 6, below -25%: 1; best +16.7%. Worst TQQQ days (close to close): 2020-03-16 -34%, 2020-03-12 -27%, 2020-03-09 -20%, 2025-04-04 -18%, 2011-08-08 -18%.
 ## 2. What to do with the idle cash (the 'core'), daily data since 2011 (3x costs)  All strategies trade at the official open/close (section 7 measures the cost of the bot's real run times). One-way costs this run: SPY/QQQ 0.015%, 3x ETFs 0.030%, charged on every position change; the overnight-only strategies pay a round trip every day. Sharpe uses a 0% cash rate. 'worst year' is the worst calendar year. Dividends included; TQQQ's fees and financing are in its prices. No taxes. Signals use only data known at the prior close. 
 ### Core strategies, 2011 to now (3x costs) 
| strategy | CAGR | vol | Sharpe | max DD | worst day | worst year | 1st half CAGR | 2nd half CAGR | $75 becomes | last 1y | last 3y |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY buy & hold (today's core) | +13.9% | 17% | 0.85 | -34% | -10.9% | -18% (2022) | +12.1% | +15.7% | $588 | +11.1% | +87.7% |
| QQQ buy & hold | +18.3% | 21% | 0.92 | -35% | -12.0% | -33% (2022) | +15.9% | +20.8% | $1,071 | +9.1% | +100.5% |
| TQQQ buy & hold | +38.0% | 61% | 0.84 | -82% | -34.5% | -79% (2022) | +40.0% | +36.1% | $12,179 | +3.6% | +290.9% |
| QQQ overnight only | +4.0% | 13% | 0.37 | -33% | -9.5% | -27% (2022) | +3.8% | +4.2% | $139 | +1.5% | +41.2% |
| TQQQ overnight only | +12.8% | 38% | 0.51 | -74% | -28.9% | -64% (2022) | +18.8% | +7.1% | $501 | -0.1% | +125.9% |
| TQQQ overnight only, when QQQ > SMA200 (else cash) | +19.2% | 29% | 0.76 | -50% | -20.0% | -20% (2022) | +16.4% | +22.1% | $1,204 | -11.1% | +161.1% |
| TQQQ overnight only, vol-target 30% + SMA200 | +11.9% | 17% | 0.74 | -30% | -10.6% | -16% (2016) | +10.6% | +13.2% | $442 | -8.3% | +90.7% |
| TQQQ overnight only, vol-target 40% + SMA200 | +14.8% | 21% | 0.76 | -35% | -10.6% | -18% (2016) | +13.1% | +16.4% | $659 | -11.2% | +115.5% |
| A. TQQQ when QQQ > SMA200, else SPY (full-time) | +35.5% | 48% | 0.87 | -61% | -20.3% | -48% (2022) | +29.4% | +41.8% | $9,073 | -3.3% | +253.9% |
| TQQQ when QQQ > SMA200, else cash (full-time) | +30.7% | 47% | 0.81 | -56% | -20.3% | -43% (2022) | +23.5% | +38.3% | $5,139 | -7.2% | +228.9% |
| QLD (2x) when QQQ > SMA200, else SPY (full-time) | +27.4% | 34% | 0.89 | -49% | -13.8% | -37% (2022) | +22.9% | +32.1% | $3,441 | +4.4% | +172.7% |
| B20. TQQQ vol-target 20% + SMA200, rest SPY (full-time) | +25.5% | 29% | 0.93 | -42% | -10.9% | -27% (2022) | +23.1% | +27.9% | $2,711 | +6.8% | +151.5% |
| B30. TQQQ vol-target 30% + SMA200, rest SPY (full-time) | +29.9% | 35% | 0.92 | -45% | -12.2% | -31% (2022) | +26.5% | +33.4% | $4,689 | +3.5% | +188.5% |
| B40. TQQQ vol-target 40% + SMA200, rest SPY (full-time) | +32.5% | 40% | 0.90 | -49% | -13.7% | -35% (2022) | +28.1% | +37.0% | $6,369 | +0.2% | +212.8% |
| B30q. same, rest QQQ instead of SPY | +31.2% | 37% | 0.92 | -47% | -12.2% | -42% (2022) | +27.4% | +35.0% | $5,441 | +1.4% | +191.8% |
| B30c. same, rest cash | +22.1% | 29% | 0.83 | -38% | -12.2% | -19% (2022) | +19.3% | +25.0% | $1,754 | -3.7% | +117.4% |
| B30 with a 10-point rebalance band | +29.6% | 35% | 0.91 | -46% | -12.2% | -32% (2022) | +26.3% | +32.9% | $4,480 | +5.2% | +189.4% |
| TQQQ vol-target 30%, no trend filter, rest SPY | +33.0% | 39% | 0.93 | -52% | -14.4% | -47% (2022) | +32.3% | +33.7% | $6,790 | +6.2% | +195.1% |
| B30 with SMA100 instead of SMA200 | +24.6% | 34% | 0.82 | -46% | -12.2% | -32% (2022) | +22.6% | +26.7% | $2,430 | -2.9% | +141.9% |
| B30 with SMA150 instead of SMA200 | +30.9% | 35% | 0.95 | -45% | -12.2% | -28% (2022) | +27.5% | +34.5% | $5,307 | +0.4% | +165.6% |
| B30 with SMA250 instead of SMA200 | +29.7% | 36% | 0.91 | -45% | -12.2% | -33% (2022) | +27.1% | +32.3% | $4,544 | +3.5% | +182.4% |
| B30 with 10-day vol instead of 20-day | +27.7% | 36% | 0.87 | -46% | -14.5% | -32% (2022) | +26.1% | +29.3% | $3,557 | -9.0% | +154.2% |
| B30 with 60-day vol instead of 20-day | +27.1% | 35% | 0.87 | -50% | -12.7% | -33% (2022) | +25.7% | +28.5% | $3,323 | -0.2% | +164.1% |
| B30 + dip overlay (3 down closes: all-in TQQQ until an up close, max 5 days) | +39.1% | 39% | 1.04 | -42% | -13.9% | -17% (2016) | +28.1% | +51.1% | $13,813 | +18.0% | +269.1% |
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
| RSI(2) < 10, any trend; exit RSI(2) > 60 or 5 days | 414 | 70% | +1.02% | +3.0 | +422% | +0.69% | +95% | +326% | 33% |
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
 ## 7. Cost of the bot's run times (Alpaca minute bars, SIP, split-adjusted)  The bot's first run lands about 9:35 ET and its last useful run about 15:50 ET. These legs show what that timing costs or earns versus trading at the official open and close. t = mean / std * sqrt(n). 
### QQQ, last 5 years (1252 full sessions; 2 short sessions skipped) 
| leg | mean per day | t | total compounded | std per day |
|---|---|---|---|---|
| open to 09:35 | +0.001% | +0.2 | +1.0% | 0.24% |
| open to 09:50 | +0.003% | +0.2 | +2.5% | 0.41% |
| open to 10:00 | +0.008% | +0.6 | +8.5% | 0.48% |
| open to 10:20 | +0.004% | +0.2 | +3.1% | 0.60% |
| 15:30 to close | +0.002% | +0.3 | +2.1% | 0.31% |
| 15:45 to close | +0.009% | +1.3 | +11.7% | 0.24% |
| 15:50 to close | +0.007% | +1.1 | +8.6% | 0.22% |
| overnight, close to open (ideal) | +0.039% | +1.6 | +56.2% | 0.86% |
| overnight, 15:50 to 9:35 next day (the bot's runs) | +0.047% | +1.9 | +70.4% | 0.88% |
| overnight, 15:30 to 9:35 next day (if the 15:50 run is late) | +0.042% | +1.6 | +60.6% | 0.90% |
| intraday, open to close | +0.025% | +0.7 | +25.0% | 1.20% |

### TQQQ, last 5 years (1254 full sessions; 0 short sessions skipped) 
| leg | mean per day | t | total compounded | std per day |
|---|---|---|---|---|
| open to 09:35 | +0.004% | +0.2 | +2.4% | 0.71% |
| open to 09:50 | +0.010% | +0.3 | +2.4% | 1.24% |
| open to 10:00 | +0.024% | +0.6 | +18.3% | 1.44% |
| open to 10:20 | +0.015% | +0.3 | -2.3% | 1.83% |
| 15:30 to close | +0.004% | +0.2 | +0.2% | 0.92% |
| 15:45 to close | +0.028% | +1.4 | +37.4% | 0.73% |
| 15:50 to close | +0.021% | +1.1 | +27.2% | 0.66% |
| overnight, close to open (ideal) | +0.078% | +1.1 | +73.5% | 2.59% |
| overnight, 15:50 to 9:35 next day (the bot's runs) | +0.100% | +1.3 | +125.4% | 2.65% |
| overnight, 15:30 to 9:35 next day (if the 15:50 run is late) | +0.083% | +1.1 | +77.4% | 2.70% |
| intraday, open to close | +0.070% | +0.7 | +7.1% | 3.61% |

 Done in 142s.
