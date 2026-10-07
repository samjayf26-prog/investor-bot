# investing-bot

A small SPY day-trading bot on Alpaca, run by GitHub Actions. Built from the plan in the
"Investing Bot Feasibility Study" project (03-plan.md).

## What it does each trading day
1. ~15:07 ET GitHub starts the job. It checks the kill switch, that today is a normal full trading day, the daily loss cap (-2%) and drawdown halt (-10% from peak).
2. Signal: if SPY at 10:00 ET was above yesterday's close, it will buy; otherwise it sits out (long only).
3. 15:30 ET: buys SPY for 50% of equity (fractional), capped at $500 and at available cash. Claude's overlay, if present, can halve that or block the day.
4. Watches the position every 20 s; sells at once if it is down 1% (a 0.5% hit to the account).
5. 15:50 ET: sells everything and confirms the account is flat. Writes a line to ledger/trades.csv.
6. ~09:47 ET backstop job: closes anything that was somehow left open overnight.

Any error fails the job, and GitHub emails you.

## Kill switch
- Fastest: Alpaca app, close the SPY position.
- Stop the bot: in the GitHub app, edit config.json and set `"kill": true`. The next run flattens and does nothing else until you set it back to false.

## Paper vs live
config.json `"mode": "paper"` uses the ALPACA_PAPER_* secrets. Live needs `"mode": "live"` and `"confirm_live": true` and the ALPACA_LIVE_* secrets.

## Manual runs
Actions tab → trade → Run workflow → `status` (account check), `flatten`, or `day`.

## Tests
`python -m pytest`
