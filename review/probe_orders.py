"""Checks on the PAPER account which entry order shapes Alpaca accepts. Each order is
priced 10% under the market so it cannot fill, and is cancelled at once.

    python review/probe_orders.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.alpaca import Alpaca, AlpacaError  # noqa: E402

api = Alpaca.from_env(False)
sym = "AAPL"
last = api.last_price(sym)
limit = f"{last * 0.9:.2f}"
shapes = {
    "notional + limit (what d8804fb sends)": dict(notional="10.00", type="limit", limit_price=limit),
    "fractional qty + limit": dict(qty=f"{10 / last:.6f}", type="limit", limit_price=limit),
}
for name, o in shapes.items():
    cid = f"review-probe-{int(time.time())}-{len(name)}"
    try:
        r = api.submit_order(symbol=sym, side="buy", time_in_force="day", client_order_id=cid, **o)
        print(f"ACCEPTED  {name}: status {r.get('status')}")
        api.cancel_order(r["id"])
    except AlpacaError as e:
        print(f"REFUSED   {name}: HTTP {e.status} {e}")
