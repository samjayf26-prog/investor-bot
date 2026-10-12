# Rules for anyone (human or Claude) changing this bot

- Keys come only from GitHub Actions secrets (ALPACA_PAPER_*, ALPACA_LIVE_*). Never commit keys, never put them in chat or give them to a Claude run.
- Claude's research runs write only picks/latest.json, research/journal.md and research/lessons.md. They never edit bot code, config.json or tuning.json.
- tuning.json is written only by the learn workflow (bot/learn.py). bot/tuning.py lists the only settings it may change and their bounds; safety limits (loss caps, drawdown halt, kill switch, trade size, position limits, mode) are never learnable. Every change is logged in research/tuning_log.csv. To undo, revert tuning.json; to freeze learning, set `"learning": false` in config.json.
- Live trading needs both `"mode": "live"` and `"confirm_live": true` in config.json.
- The bot treats picks/latest.json as untrusted: it validates and clamps every field, and a bad file means no new entries, never a crash.
- Every risk limit lives in bot/risk.py as a tested pure function. Run `python -m pytest` before every push.
- No leverage, no short selling (account under $2,000). Bearish views are puts or inverse ETFs.
- The Alpaca account is dedicated to this bot: `flatten` closes every position in it.
