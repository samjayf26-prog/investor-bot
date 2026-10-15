"""Checks the bot's market snapshot (state/market.json rows) against real Alpaca data,
using the PAPER keys. Read-only: places no orders.

    python review/probe_orders.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import risk  # noqa: E402
from bot.alpaca import Alpaca  # noqa: E402
from bot.trader import MARKET  # noqa: E402

api = Alpaca.from_env(False)
syms = list(MARKET) + ["AZZ", "TQQQ", "SQQQ"]
snaps = api.snapshots(syms)
print("raw keys for QQQ:", sorted((snaps.get("QQQ") or {}).keys()))
rows = {s: risk.market_row(snaps.get(s)) for s in syms}
print(json.dumps(rows, indent=1))
missing = [s for s, r in rows.items() if not r or r["vwap"] is None or r["pct_vs_prev_close"] is None]
print("MISSING FIELDS:", missing or "none")
