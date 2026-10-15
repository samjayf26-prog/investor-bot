# Scorecard 2026-10-15

## Bot vs S&P 500 ($75 since 2026-10-13 12:40 ET)
**Bot $73.91 (-1.45%) vs S&P 500 $74.43 (-0.76%): the bot is behind by $0.52.**

| day | bot $ | $ in S&P 500 (SPY) |
|---|---|---|
| 2026-10-13 | 75.02 | 75.03 |
| 2026-10-14 | 75.02 | 74.17 |
| 2026-10-15 | 73.91 | 74.43 |
(Deposits or withdrawals would distort this; reset benchmark.since in config.json after one.)

## Scalper, last 5 sessions
| day | trips | winners | P&L $ |
|---|---|---|---|
| 2026-10-08 | 16 | 8 | -0.06 |
| 2026-10-09 | 60 | 33 | -0.01 |
| 2026-10-13 | 2 | 0 | -0.08 |
| 2026-10-14 | 10 | 7 | 0.2 |
| 2026-10-15 | 8 | 2 | -0.15 |

| symbol | trips | winners | P&L $ |
|---|---|---|---|
| QQQ | 25 | 15 | 0.01 |
| SPY | 24 | 14 | 0.05 |
| SQQQ | 26 | 11 | -0.08 |
| TQQQ | 21 | 10 | -0.07 |

| exit reason | trips | winners | P&L $ |
|---|---|---|---|
| end of session | 4 | 3 | 0.01 |
| stop | 16 | 0 | -0.73 |
| take profit | 9 | 9 | 0.47 |
| time | 67 | 38 | 0.15 |

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

Picks: 8 closed, 3 winners, $0.28 total.

## Claude's direction calls (scalp_bias vs QQQ 9:35-15:15)
| day | bias | QQQ move | right? |
|---|---|---|---|
| 2026-10-13 | bear | +0.38% | false |
| 2026-10-14 | bear | -1.43% | true |
| 2026-10-15 | bear | +1.41% | false |

Bull/bear calls: 1 of 3 right.

## Tuner
Replayed 10 sessions. Current settings: +0.57% / +0.05% of trade size (earlier / later half, after 0.03% costs per trade).
No setting beat the current one in both halves by enough; kept it.
