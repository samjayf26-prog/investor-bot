"""Probe: a stale core order whose cancel Alpaca refuses must not abort the rebalance (PR #2 fixed at 5c9be84)."""
import sys
sys.path.insert(0, "tests"); sys.path.insert(0, ".")
import pytest
from test_bot import LIVE_CFG, FakeAlpaca, FakeClock, write_picks
from test_overhaul import closes, hold, WINDOW
from bot.alpaca import AlpacaError
from bot.trader import Trader

LEV_CFG = {**LIVE_CFG, "core": {**LIVE_CFG["core"], "leverage": True}}


def test_failed_cancel_of_stale_core_order(tmp_path):
    write_picks(tmp_path, [])
    api = FakeAlpaca(cash=50.0)
    hold(api, "SPY", 30.0)
    api.closes = closes(260, 0.002)
    api.prices["QQQ"] = api.closes[-1]
    api.open_orders = lambda: [{"id": "o1", "client_order_id": "core-20261029-TQQQ", "symbol": "TQQQ"}]
    def cancel_order(oid):
        raise AlpacaError(422, "order already filled")
    api.cancel_order = cancel_order
    clock = FakeClock(WINDOW)
    t = Trader(api, LEV_CFG, now=clock.now, sleep=clock.sleep, root=tmp_path)
    r = t.cycle()
    print('result:', r, 'orders:', {k: (v['side'], v['symbol'], v.get('notional')) for k, v in api.orders.items()})
    assert r != 'halted'
    assert [o for o in api.orders.values() if o['symbol'] == 'TQQQ' and o['side'] == 'buy'], 'rebalance did not buy TQQQ after a refused cancel'
    assert (tmp_path / 'state' / 'core.json').exists()
