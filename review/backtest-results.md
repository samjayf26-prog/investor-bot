# Scalper backtest (2026-07-06 to 2026-10-12, 70 sessions, 9:35-15:15 ET)

Replays bot/learn.py simulate() (entry at next bar open after an EMA cross-up, exact stop/target fills, stop first when a bar touches both). Each symbol is replayed independently, so the live limit of 2 open scalps is ignored. Costs are per round trip, as a fraction of trade size.

## Feed: iex (bars per day: {'SPY': 340, 'QQQ': 334, 'TQQQ': 318, 'SQQQ': 294})

### Cost 0.00% per round trip
All 300 settings over all 70 sessions: 67 of 300 made money. Best +5.43 $ (3802 trades, {'take_profit_pct': 0.005, 'stop_pct': 0.001, 'max_hold_minutes': 20, 'ema_fast': 3, 'ema_slow': 9}), median -1.79 $, worst -8.15 $.

Out-of-sample days: 60. Tuner switched settings on 12 days.

| policy | trades | P&L $ (at $15/trade) | per trade % | winning days |
|---|---|---|---|---|
| tuner as shipped | 2294 | +3.58 | +0.0104% | 35/60 |
| tuner + must be profitable | 1799 | +1.63 | +0.0060% | 34/60 |
| fixed current tuning.json | 1373 | +0.69 | +0.0033% | 38/60 |
| fixed config.json defaults | 4219 | -1.23 | -0.0019% | 27/60 |

### Cost 0.03% per round trip
All 300 settings over all 70 sessions: 0 of 300 made money. Best -5.93 $ (1780 trades, {'take_profit_pct': 0.005, 'stop_pct': 0.0015, 'max_hold_minutes': 20, 'ema_fast': 8, 'ema_slow': 21}), median -15.31 $, worst -30.27 $.

Out-of-sample days: 60. Tuner switched settings on 14 days.

| policy | trades | P&L $ (at $15/trade) | per trade % | winning days |
|---|---|---|---|---|
| tuner as shipped | 639 | -2.34 | -0.0244% | 24/60 |
| tuner + must be profitable | 520 | -2.72 | -0.0349% | 19/60 |
| fixed current tuning.json | 1373 | -5.49 | -0.0267% | 18/60 |
| fixed config.json defaults | 4219 | -20.21 | -0.0319% | 1/60 |

### Cost 0.06% per round trip
All 300 settings over all 70 sessions: 0 of 300 made money. Best -13.94 $ (1780 trades, {'take_profit_pct': 0.005, 'stop_pct': 0.0015, 'max_hold_minutes': 20, 'ema_fast': 8, 'ema_slow': 21}), median -29.27 $, worst -52.39 $.

Out-of-sample days: 60. Tuner switched settings on 4 days.

| policy | trades | P&L $ (at $15/trade) | per trade % | winning days |
|---|---|---|---|---|
| tuner as shipped | 548 | -4.64 | -0.0564% | 16/60 |
| tuner + must be profitable | 65 | -0.69 | -0.0703% | 3/60 |
| fixed current tuning.json | 1373 | -11.67 | -0.0567% | 7/60 |
| fixed config.json defaults | 4219 | -39.20 | -0.0619% | 0/60 |

Current tuning.json by symbol over all sessions (P&L $, trades): {'SPY': (-1.7, 418), 'QQQ': (-2.06, 409), 'TQQQ': (-1.97, 409), 'SQQQ': (-2.23, 388)}

## Feed: sip (bars per day: {'SPY': 341, 'QQQ': 341, 'TQQQ': 341, 'SQQQ': 341})

### Cost 0.00% per round trip
All 300 settings over all 70 sessions: 5 of 300 made money. Best +0.67 $ (5473 trades, {'take_profit_pct': 0.003, 'stop_pct': 0.001, 'max_hold_minutes': 3, 'ema_fast': 3, 'ema_slow': 9}), median -2.32 $, worst -4.72 $.

### Cost 0.03% per round trip
All 300 settings over all 70 sessions: 0 of 300 made money. Best -7.52 $ (1688 trades, {'take_profit_pct': 0.005, 'stop_pct': 0.005, 'max_hold_minutes': 20, 'ema_fast': 8, 'ema_slow': 21}), median -17.81 $, worst -26.99 $.

Out-of-sample days: 60. Tuner switched settings on 12 days.

| policy | trades | P&L $ (at $15/trade) | per trade % | winning days |
|---|---|---|---|---|
| tuner as shipped | 785 | -5.18 | -0.0440% | 15/60 |
| tuner + must be profitable | 287 | -1.53 | -0.0354% | 13/60 |
| fixed current tuning.json | 1444 | -6.33 | -0.0292% | 17/60 |
| fixed config.json defaults | 4491 | -22.19 | -0.0329% | 1/60 |

### Cost 0.06% per round trip
All 300 settings over all 70 sessions: 0 of 300 made money. Best -15.12 $ (1688 trades, {'take_profit_pct': 0.005, 'stop_pct': 0.005, 'max_hold_minutes': 20, 'ema_fast': 8, 'ema_slow': 21}), median -32.71 $, worst -51.38 $.

Current tuning.json by symbol over all sessions (P&L $, trades): {'SPY': (-1.65, 412), 'QQQ': (-2.03, 417), 'TQQQ': (-2.87, 439), 'SQQQ': (-1.98, 436)}
