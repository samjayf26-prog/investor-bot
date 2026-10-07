# Rules for anyone (human or Claude) changing this bot

- Keys come only from GitHub Actions secrets (ALPACA_PAPER_*, ALPACA_LIVE_*). Never commit keys, never put them in chat or give them to a Claude run.
- Claude's research runs write only picks/latest.json and research/journal.md. They never edit bot code or config.
- Live trading needs both `"mode": "live"` and `"confirm_live": true` in config.json.
- The bot treats picks/latest.json as untrusted: it validates and clamps every field, and a bad file means no new entries, never a crash.
- Every risk limit lives in bot/risk.py as a tested pure function. Run `python -m pytest` before every push.
- No leverage, no short selling (account under $2,000). Bearish views are puts or inverse ETFs.
- The Alpaca account is dedicated to this bot: `flatten` closes every position in it.
