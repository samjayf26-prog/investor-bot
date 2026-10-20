# Scorecard 2026-10-20

## Bot vs S&P 500 ($75 since 2026-10-13 12:40 ET)
**Bot $73.82 (-1.57%) vs S&P 500 $74.17 (-1.10%): the bot is behind by $0.35.**

| day | bot $ | $ in S&P 500 (SPY) |
|---|---|---|
| 2026-10-13 | 75.02 | 75.03 |
| 2026-10-14 | 75.02 | 74.17 |
| 2026-10-15 | 73.91 | 74.43 |
| 2026-10-16 | 74.00 | 73.62 |
| 2026-10-19 | 73.83 | 73.94 |
| 2026-10-20 | 73.82 | 74.17 |
(Deposits or withdrawals would distort this; reset benchmark.since in config.json after one.)

## Scalper, last 5 sessions
| day | trips | winners | P&L $ |
|---|---|---|---|
| 2026-10-14 | 10 | 7 | 0.2 |
| 2026-10-15 | 8 | 2 | -0.15 |
| 2026-10-16 | 7 | 5 | 0.25 |
| 2026-10-19 | 4 | 2 | 0.05 |
| 2026-10-20 | 2 | 1 | 0.06 |

| symbol | trips | winners | P&L $ |
|---|---|---|---|
| SQQQ | 31 | 17 | 0.42 |

| exit reason | trips | winners | P&L $ |
|---|---|---|---|
| end of session | 2 | 1 | -0.0 |
| stop | 12 | 0 | -0.63 |
| take profit | 9 | 9 | 0.73 |
| time | 8 | 7 | 0.32 |

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

Picks: 11 closed, 4 winners, $0.13 total.

## Claude's direction calls (scalp_bias vs QQQ 9:35-15:15)
| day | bias | QQQ move | right? |
|---|---|---|---|
| 2026-10-13 | bear | +0.38% | false |
| 2026-10-14 | bear | -1.43% | true |
| 2026-10-15 | bear | +1.41% | false |
| 2026-10-16 | bear | -1.91% | true |
| 2026-10-19 | neutral | +0.03% | - |
| 2026-10-20 | bull | +0.65% | true |

Bull/bear calls: 3 of 5 right.

## Tuner
Replayed 10 sessions. Current settings: +0.10% / +6.50% of trade size (earlier / later half, after 0.03% costs per trade).
No setting beat the current one in both halves by enough; kept it.
