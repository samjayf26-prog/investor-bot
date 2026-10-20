# investor-bot

Claude researches the market each morning and picks trades; a bot on GitHub Actions
executes them on Alpaca with hard limits. Started from the plan in the "Investing Bot
Feasibility Study" project, reworked so Claude picks trades.

## Each trading day
- ~8:50 ET: a scheduled Claude run researches (earnings, news, analyst moves, macro
  calendar) and writes up to 3 picks to picks/latest.json, with reasons in research/journal.md.
- Every 15 minutes in market hours, and whenever Claude pushes new picks: the bot
  (bot/trader.py) checks exits (stop, target, max hold days, Claude's close list, options
  near expiry), then buys new picks until 15:30 with limit orders (never above Claude's max
  entry price, or 1% over the last trade). A refused order skips that pick only. A pick
  with "confirm_vwap": true waits (no order) until the price is above today's VWAP (below
  it for a put). Each run also writes state/market.json, live index and pick prices that
  the research runs read instead of headline numbers.
- The scalper (bot/scalper.py) trades the paper account (config scalper.mode "paper") since
  replays showed it loses after costs; set it to "live" to put it back on real money.
- Long picks: buy the stock or ETF (fractional when allowed). Bearish picks: buy one put,
  or a Claude-chosen inverse ETF. Real short selling needs $2,000 at Alpaca.
- Size by conviction: 15% / 25% / 40% of equity per pick, never more than cash on hand,
  never more than $500, at most 3 open positions. Live picks size off the real account so
  gains compound; sizing_equity_cap only applies to the paper account.
- New entries stop for the day after a 25% daily loss, and stop entirely after a 60% fall
  from the peak.
- Every run commits state/ (account snapshot) and ledger/trades.csv. Errors fail the job and GitHub emails you.

## Learning (after each close)
- 4:15pm ET, the learn workflow (bot/learn.py) writes research/scorecard.md (how scalps and
  picks did) and replays the scalper's rules over the last 10 sessions of 1-minute bars with
  300 setting combinations (take profit, stop, max hold, EMA pair, which ETFs). If one beats
  the current settings in both halves of that window after trading costs, it goes into
  tuning.json and each change is logged with its reason in research/tuning_log.csv.
- 4:45pm ET, a Claude review reads the scorecard and journal and rewrites
  research/lessons.md, the rules the morning research must follow.
- Learning never touches the safety limits. Undo: revert tuning.json. Freeze: set
  `"learning": false` in config.json.

## Kill switch
- Fastest: close positions in the Alpaca app.
- Stop the bot: edit config.json in the GitHub app, set `"kill": true`. The next run sells everything and does nothing else.

## Paper vs live
`"mode": "paper"` uses ALPACA_PAPER_* secrets. Live needs `"mode": "live"`, `"confirm_live": true` and ALPACA_LIVE_* secrets.

## Manual runs
Actions tab → trade → Run workflow → `status`, `cycle` or `flatten`.

## Tests
`python -m pytest`

## Overnight SPY core
`"core": {"symbol": "SPY", "buy_after_et": "14:30", "reserve": 2.0}` in config.json (set it to
`null` to turn it off). On runs from 14:30 ET the bot buys SPY with cash above the reserve, so
idle cash is invested overnight, when market returns have come. When a pick's budget is more
than the cash on hand, the bot sells just enough SPY right before the pick's order. The core
never counts as an open position, is never adopted or closed by picks, and no core is bought
while a loss halt is on. The kill switch and `flatten` sell it like everything else. Core
trades go to ledger/core.csv; state/account.json shows its value under "core".
