# investing-bot

Claude researches the market each morning and picks trades; a bot on GitHub Actions
executes them on Alpaca with hard limits. Started from the plan in the "Investing Bot
Feasibility Study" project, reworked so Claude picks trades.

## Each trading day
- ~8:50 ET: a scheduled Claude run researches (earnings, news, analyst moves, macro
  calendar) and writes up to 3 picks to picks/latest.json, with reasons in research/journal.md.
- Every hour 9:50-15:50 ET: the bot (bot/trader.py) checks exits (stop, target, max
  hold days, Claude's close list, options near expiry), then buys new picks until 15:30.
- Long picks: buy the stock or ETF (fractional when allowed). Bearish picks: buy one put,
  or a Claude-chosen inverse ETF. Real short selling needs $2,000 at Alpaca.
- Size by conviction: 15% / 25% / 40% of equity per pick, never more than cash on hand,
  never more than $500, at most 3 open positions.
- New entries stop for the day after a 25% daily loss, and stop entirely after a 60% fall
  from the peak.
- Every run commits state/ (account snapshot) and ledger/trades.csv. Errors fail the job and GitHub emails you.

## Kill switch
- Fastest: close positions in the Alpaca app.
- Stop the bot: edit config.json in the GitHub app, set `"kill": true`. The next run sells everything and does nothing else.

## Paper vs live
`"mode": "paper"` uses ALPACA_PAPER_* secrets. Live needs `"mode": "live"`, `"confirm_live": true` and ALPACA_LIVE_* secrets.

## Manual runs
Actions tab → trade → Run workflow → `status`, `cycle` or `flatten`.

## Tests
`python -m pytest`
