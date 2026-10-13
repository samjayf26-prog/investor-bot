"""Reproductions of review findings against the current bot code. Each assert shows a bug.

    python -m pytest review/repro_findings.py
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from test_bot import FakeAlpaca, make, write_picks  # noqa: E402

from bot.alpaca import AlpacaError  # noqa: E402


class RejectsSecondOrder(FakeAlpaca):
    """Broker that refuses the second order (e.g. insufficient buying power while the
    first market order's cash is not yet deducted, or any 4xx)."""
    def submit_order(self, **o):
        if len(self.orders) == 1:
            raise AlpacaError(403, '{"message":"insufficient buying power"}')
        return super().submit_order(**o)


def test_rejected_order_crashes_cycle_and_loses_first_pick_state(tmp_path):
    write_picks(tmp_path, [{"id": "p1", "symbol": "NVDA", "action": "buy", "stop_pct": 0.03},
                           {"id": "p2", "symbol": "F", "action": "buy"}])
    t, api, _ = make(tmp_path, RejectsSecondOrder())
    with pytest.raises(AlpacaError):
        t.cycle()                       # finding: one refused order aborts the whole run
    assert "NVDA" in api.pos            # p1 was bought...
    assert not (tmp_path / "state" / "positions.json").exists()   # ...but its record was never saved
    t.api.__class__ = FakeAlpaca        # broker healthy again next hour
    t.cycle()
    state = json.loads((tmp_path / "state" / "positions.json").read_text())
    adopted = [e for k, e in state.items() if e["broker_symbol"] == "NVDA"]
    # Claude's 3% stop is replaced by the 10% default and the pick id is lost, so
    # "close": ["p1"] can no longer close it.
    assert adopted[0]["stop_pct"] == 0.10 and "p1" not in state
