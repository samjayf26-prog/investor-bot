# Scorecard 2026-11-19

## Bot vs S&P 500 ($75 since 2026-10-13 12:40 ET)
**Bot $69.46 (-7.39%) vs S&P 500 $69.09 (-7.88%): the bot is ahead by $0.37.**
Same money in the Nasdaq 100 (QQQ): $65.08 (-13.22%).
Core rule on paper (TQQQ/SPY rule at official closes from the go-live day's close, no picks): $55.69 (-25.75%). The gap between this and the account is the picks plus execution slippage.

| day | bot $ | $ in S&P 500 (SPY) | $ in QQQ | core rule $ |
|---|---|---|---|---|
| 2026-11-06 | 71.46 | 70.94 | 66.22 | 57.68 |
| 2026-11-09 | 73.76 | 72.59 | 68.46 | 59.03 |
| 2026-11-10 | 72.76 | 72.32 | 68.11 | 58.81 |
| 2026-11-11 | 73.01 | 73.31 | 69.63 | 59.61 |
| 2026-11-12 | 72.70 | 73.04 | 69.55 | 59.38 |
| 2026-11-13 | 72.20 | 72.52 | 67.99 | 58.09 |
| 2026-11-16 | 70.67 | 71.37 | 66.80 | 57.41 |
| 2026-11-17 | 69.79 | 70.72 | 66.43 | 56.13 |
| 2026-11-18 | 70.50 | 70.51 | 66.59 | 56.99 |
| 2026-11-19 | 69.46 | 69.09 | 65.08 | 55.69 |
(Deposits or withdrawals would distort this; reset benchmark.since in config.json after one.)

## Scalper, last 5 sessions
| day | trips | winners | P&L $ |
|---|---|---|---|
| 2026-10-26 | 1 | 0 | -0.04 |
| 2026-10-27 | 1 | 0 | -0.03 |
| 2026-10-28 | 1 | 0 | -0.04 |
| 2026-10-29 | 1 | 1 | 0.02 |
| 2026-10-30 | 1 | 0 | -0.04 |

| symbol | trips | winners | P&L $ |
|---|---|---|---|
| SQQQ | 5 | 1 | -0.12 |

| exit reason | trips | winners | P&L $ |
|---|---|---|---|
| end of session | 1 | 1 | 0.02 |
| stop | 4 | 0 | -0.14 |

## Research picks, all closed
| closed | pick | P&L $ | P&L % | why closed |
|---|---|---|---|---|
| 2026-10-08 | 2026-10-07-CEG | -0.74 | -5.0% | Claude asked to close |
| 2026-10-09 | 2026-10-07-SH | 0.03 | 0.2% | Claude asked to close |
| 2026-10-09 | 2026-10-08-1420-SOXS | -0.11 | -0.7% | Claude asked to close |
| 2026-10-09 | 2026-10-09-HUM | -0.32 | -1.3% | Claude asked to close |
| 2026-10-13 | 2026-10-07-1420-PENG | 2.07 | 8.3% | Claude asked to close |
| 2026-10-13 | 2026-10-13-UNH | 0.42 | 1.7% | Claude asked to close |
| 2026-10-15 | 2026-10-15-1020-SQQQ | -0.25 | -1.3% | Claude asked to close |
| 2026-10-15 | 2026-10-14-AZZ | -0.82 | -4.3% | Claude asked to close |
| 2026-10-16 | 2026-10-16-1320-SQQQ | 0.11 | 1.0% | day trade: end of day |
| 2026-10-19 | 2026-10-19-1120-TQQQ | -0.15 | -1.4% | Claude asked to close |
| 2026-10-20 | 2026-10-20-1120-TQQQ | -0.11 | -1.0% | day trade: end of day |
| 2026-10-22 | 2026-10-20-HAL | -0.55 | -3.0% | Claude asked to close |
| 2026-10-26 | 2026-10-23-1120-TQQQ | 0.12 | 1.1% | day trade: end of day |
| 2026-10-27 | 2026-10-20-MMM | 0.14 | 1.2% | max hold of 7 days |
| 2026-10-29 | 2026-10-23-LMT | 1.1 | 10.1% | profit target (10.1%) |
| 2026-10-30 | 2026-10-27-1020-CLS | -0.76 | -6.9% | Claude asked to close |
| 2026-11-03 | 2026-10-26-1020-TSLA | 0.2 | 1.8% | max hold of 8 days |

Picks: 17 closed, 8 winners, $0.38 total.

## Claude's direction calls (scalp_bias vs QQQ 9:35-15:15)
| day | bias | QQQ move | right? |
|---|---|---|---|
| 2026-11-06 | neutral | +0.40% | - |
| 2026-11-09 | neutral | +2.34% | - |
| 2026-11-10 | neutral | -0.02% | - |
| 2026-11-11 | neutral | +0.64% | - |
| 2026-11-12 | neutral | +0.36% | - |
| 2026-11-13 | neutral | -1.03% | - |
| 2026-11-16 | neutral | -0.99% | - |
| 2026-11-17 | neutral | -1.44% | - |
| 2026-11-18 | neutral | -0.17% | - |
| 2026-11-19 | neutral | -4.29% | - |

Bull/bear calls: 8 of 10 right.

## Tuner
Learning is off in config.json; nothing changed.
