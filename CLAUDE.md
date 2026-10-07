# Rules for anyone (human or Claude) changing this bot

- Keys come only from GitHub Actions secrets (ALPACA_PAPER_*, ALPACA_LIVE_*). Never commit keys, never put them in chat or in a Claude routine.
- Live trading needs both `"mode": "live"` and `"confirm_live": true` in config.json.
- The bot must work with the Claude overlay (overlay/latest.json) missing, stale or garbage. The overlay can only reduce size or block a day, never increase.
- Every risk limit lives in bot/risk.py as a tested pure function. Run `python -m pytest` before every push.
- Long only, SPY only, one entry per day (deterministic client_order_id), flat before the close.
- The Alpaca account is dedicated to this bot: `flatten` closes every position in it.
