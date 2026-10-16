# Scorecard 2026-10-16

## Bot vs S&P 500 ($75 since 2026-10-13 12:40 ET)
**Bot $74.00 (-1.33%) vs S&P 500 $73.62 (-1.84%): the bot is ahead by $0.38.**

| day | bot $ | $ in S&P 500 (SPY) |
|---|---|---|
| 2026-10-13 | 75.02 | 75.03 |
| 2026-10-14 | 75.02 | 74.17 |
| 2026-10-15 | 73.91 | 74.43 |
| 2026-10-16 | 74.00 | 73.62 |
(Deposits or withdrawals would distort this; reset benchmark.since in config.json after one.)

## Scalper, last 5 sessions
| day | trips | winners | P&L $ |
|---|---|---|---|
| 2026-10-09 | 60 | 33 | -0.01 |
| 2026-10-13 | 2 | 0 | -0.08 |
| 2026-10-14 | 10 | 7 | 0.2 |
| 2026-10-15 | 8 | 2 | -0.15 |
| 2026-10-16 | 7 | 5 | 0.25 |

| symbol | trips | winners | P&L $ |
|---|---|---|---|
| QQQ | 21 | 12 | -0.02 |
| SPY | 21 | 11 | 0.02 |
| SQQQ | 27 | 14 | 0.22 |
| TQQQ | 18 | 10 | -0.0 |

| exit reason | trips | winners | P&L $ |
|---|---|---|---|
| end of session | 3 | 3 | 0.01 |
| stop | 15 | 0 | -0.74 |
| take profit | 11 | 11 | 0.67 |
| time | 58 | 33 | 0.26 |

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

Picks: 9 closed, 4 winners, $0.39 total.

## Claude's direction calls (scalp_bias vs QQQ 9:35-15:15)
| day | bias | QQQ move | right? |
|---|---|---|---|
| 2026-10-13 | bear | +0.38% | false |
| 2026-10-14 | bear | -1.43% | true |
| 2026-10-15 | bear | +1.41% | false |
| 2026-10-16 | bear | -1.91% | true |

Bull/bear calls: 2 of 4 right.

## Tuner
Replayed 10 sessions. Current settings: -1.71% / +5.72% of trade size (earlier / later half, after 0.03% costs per trade).
No setting beat the current one in both halves by enough; kept it.
