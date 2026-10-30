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
- The scalper (bot/scalper.py) is retired: it only ever trades the paper account and no
  longer runs on a schedule (replays showed it loses after costs). Run scalp.yml by hand to watch it.
- Picks are buys only: the stock or ETF (fractional when allowed), bought from 10:00 ET
  (`earliest_et`), held about 20 trading days by default (max 30) with a 15% disaster stop
  and no profit target unless Claude sets one. Bearish trades (puts, inverse or bear ETFs)
  are off: the news-gap study found they lose. Real short selling needs $2,000 at Alpaca.
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
- 4:45pm ET, a Claude review reads the scorecard and journal and appends observations to the
  journal. research/lessons.md is a frozen rulebook: a rule changes only with 30+ trades and a
  t-statistic above 2 behind the change.
- The tuner is frozen (`"learning": false` in config.json); it never touched the safety limits.
  The scorecard also shows the same money in QQQ and the core rule's model return.

## Kill switch
- Fastest: close positions in the Alpaca app.
- Stop the bot: edit config.json in the GitHub app, set `"kill": true`. The next run sells everything and does nothing else.

## Paper vs live
`"mode": "paper"` uses ALPACA_PAPER_* secrets. Live needs `"mode": "live"`, `"confirm_live": true` and ALPACA_LIVE_* secrets.

## Manual runs
Actions tab → trade → Run workflow → `status`, `cycle` or `flatten`.

## Tests
`python -m pytest`

## The core (idle cash)
Config "core" in config.json decides where cash that picks aren't using sits (set it to `null`
to turn the core off). Either way the core never counts as an open position, is never adopted
or closed by picks, and picks are funded by selling it (SPY first, then TQQQ) right before the
pick's order. Core trades go to ledger/core.csv with the signal values; state/account.json
shows its value under "core". The kill switch and `flatten` sell it like everything else.

- `"leverage": false` (the default): from 14:30 ET, cash above the $2 reserve goes into SPY and
  stays until a pick needs it. This is the shape that has run since 2026-10-20. Any TQQQ left
  from the leveraged mode is sold back into SPY.
- `"leverage": true`: the rule from review/profit-overhaul.md (bot/core.py). Once a day, in the
  15:35-15:58 ET window, core money is split between TQQQ and SPY: TQQQ weight = min(1,
  vol_target / (3 x QQQ 20-day volatility)) while QQQ closes above its 200-day average, else 0.
  After three lower QQQ closes in a row the core goes 100% TQQQ until the first higher close (at
  most 5 sessions). It only trades when the target moved more than `band` (10 points) from what
  is held, or new cash arrived. The window run uses QQQ's last trade as today's close; if that
  run is skipped, the next run of any kind acts on the completed close at once (the overlay's
  edge is the first session after the signal). `"weight_live_close": false` makes the
  SMA/volatility weight wait for completed sessions (the overlay still uses the live price).
  While a loss halt is on the core may sell TQQQ but never buy. Nothing in the research runs
  can touch it. Backtest 2011-2026: 39.9%/yr vs 13.9% for SPY, worst year -17%, max drawdown
  -42% (the 60% halt was never hit); plan on -30% to -45% in a bad year.
- `python -m bot.core paper` (core-paper.yml, 15:36 ET) rehearses the leveraged rule on the
  paper account, sized like the live stake, to check order mechanics before the live switch.
