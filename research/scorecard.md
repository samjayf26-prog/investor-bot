# Scorecard 2026-10-13

## Bot vs S&P 500 ($75 since 2026-10-13 12:40 ET)
**Bot $75.02 (+0.03%) vs S&P 500 $75.03 (+0.05%): the bot is behind by $0.01.**

| day | bot $ | $ in S&P 500 (SPY) |
|---|---|---|
| 2026-10-13 | 75.02 | 75.03 |
(Deposits or withdrawals would distort this; reset benchmark.since in config.json after one.)

## Scalper, last 5 sessions
| day | trips | winners | P&L $ |
|---|---|---|---|
| 2026-10-08 | 16 | 8 | -0.06 |
| 2026-10-09 | 60 | 33 | -0.01 |
| 2026-10-13 | 2 | 0 | -0.08 |

| symbol | trips | winners | P&L $ |
|---|---|---|---|
| QQQ | 25 | 15 | 0.01 |
| SPY | 24 | 14 | 0.05 |
| SQQQ | 8 | 2 | -0.12 |
| TQQQ | 21 | 10 | -0.07 |

| exit reason | trips | winners | P&L $ |
|---|---|---|---|
| end of session | 3 | 2 | 0.0 |
| stop | 8 | 0 | -0.32 |
| take profit | 5 | 5 | 0.16 |
| time | 62 | 34 | 0.01 |

## Research picks, all closed
| closed | pick | P&L $ | P&L % | why closed |
|---|---|---|---|---|
| 2026-10-08 | 2026-10-07-CEG | -0.74 | -5.0% | Claude asked to close |
| 2026-10-09 | 2026-10-07-SH | 0.03 | 0.2% | Claude asked to close |
| 2026-10-09 | 2026-10-08-1420-SOXS | -0.11 | -0.7% | Claude asked to close |
| 2026-10-09 | 2026-10-09-HUM | -0.32 | -1.3% | Claude asked to close |
| 2026-10-13 | 2026-10-07-1420-PENG | 2.07 | 8.3% | Claude asked to close |
| 2026-10-13 | 2026-10-13-UNH | 0.42 | 1.7% | Claude asked to close |

Picks: 6 closed, 3 winners, $1.35 total.

## Claude's direction calls (scalp_bias vs QQQ 9:35-15:15)
| day | bias | QQQ move | right? |
|---|---|---|---|
| 2026-10-13 | bear | +0.38% | false |

Bull/bear calls: 0 of 1 right.

## Tuner
Replayed 10 sessions. Current settings: +0.46% / -6.16% of trade size (earlier / later half, after 0.03% costs per trade).
Changed to {"take_profit_pct": 0.005, "stop_pct": 0.003, "max_hold_minutes": 20, "ema_fast": 5, "ema_slow": 13, "enabled_symbols": ["SQQQ"]} because replay of 10 sessions: +0.96%/+0.10% vs current +0.46%/-6.16% (82 trades).
