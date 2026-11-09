"""Claude's pre-buy news check (bot/advisor.py): it can only remove a buy, never add or
resize one, and every failure path lets the buy proceed as before."""
import csv
import json
from datetime import timedelta
from types import SimpleNamespace

from bot import picks, risk
from bot.advisor import Advisor, call_cost, month_to_date_spend, parse_verdict
from bot.trader import Trader

from test_bot import CFG, NOW, TODAY, FakeAlpaca, FakeClock, write_picks


class NewsAlpaca(FakeAlpaca):
    def news(self, symbols, start, limit=20):
        return [{"headline": "NVDA raises guidance", "summary": "Strong AI demand.", "source": "wire",
                 "created_at": "2026-10-08T12:00:00Z", "url": "https://example.com/n", "symbols": symbols}]


class FakeClient:
    """Stands in for anthropic.Anthropic: canned answers, or an exception."""

    def __init__(self, answers=None, error=None, stop_reason="end_turn"):
        self.answers = list(answers or [])
        self.error, self.stop_reason, self.calls = error, stop_reason, []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        text = self.answers.pop(0) if self.answers else json.dumps({"decision": "confirm", "reason": "ok", "confidence": 0.9})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=100,
                                                     cache_read_input_tokens=0, cache_creation_input_tokens=0),
                               model=kw["model"], stop_reason=self.stop_reason, _request_id="req_1")


ADV_CFG = {**CFG, "claude": {"enabled": True, "model": "claude-opus-5-5", "monthly_budget_usd": 15.0}}
PICK = {"id": "p1", "symbol": "NVDA", "action": "buy", "conviction": 2, "thesis": "Beat and raise.",
        "wrong_if": "closes below $170", "sources": ["https://example.com/ir"]}


def make(tmp_path, client, start=NOW):
    clock, api = FakeClock(start), NewsAlpaca()
    adv = Advisor(ADV_CFG, api, root=tmp_path, client=client, now=clock.now)
    t = Trader(api, ADV_CFG, now=clock.now, sleep=clock.sleep, root=tmp_path, advisor=adv)
    return t, api, adv, clock


def rows(tmp_path):
    with open(tmp_path / "ledger" / "claude_calls.csv", newline="") as f:
        return list(csv.DictReader(f))


def test_veto_blocks_the_buy_and_is_remembered_for_the_day(tmp_path):
    write_picks(tmp_path, [PICK])
    client = FakeClient([json.dumps({"decision": "veto", "reason": "guidance raise was retracted", "confidence": 0.8})])
    t, api, adv, clock = make(tmp_path, client)
    assert t.cycle() == "managed"
    assert "p1-entry" not in api.orders
    row = rows(tmp_path)[0]
    assert row["decision"] == "veto" and row["pick_id"] == "p1" and float(row["cost_usd"]) > 0
    # the model saw the thesis, the wrong-if, the quote and the headlines
    sent = client.calls[0]["messages"][0]["content"]
    assert "Beat and raise." in sent and "closes below $170" in sent and "raises guidance" in sent and "180.0" in sent
    assert client.calls[0]["output_config"]["format"]["type"] == "json_schema"
    # the 15-minute rerun does not ask again, and still does not buy
    clock.t += timedelta(minutes=15)
    t.cycle()
    assert len(client.calls) == 1 and "p1-entry" not in api.orders
    # a new day with the same id is judged afresh
    ok, _ = adv.check_entry(picks.load(t.picks_path, NOW, ADV_CFG)[0][0], 180.0, TODAY + timedelta(days=1))
    assert ok and len(client.calls) == 2


def test_confirm_buys_as_before(tmp_path):
    write_picks(tmp_path, [PICK])
    t, api, adv, _ = make(tmp_path, FakeClient())
    assert t.cycle() == "traded"
    assert api.orders["p1-entry"]["notional"] == "15.00"
    assert rows(tmp_path)[0]["decision"] == "confirm"


def test_api_error_fails_open(tmp_path):
    write_picks(tmp_path, [PICK])
    t, api, adv, _ = make(tmp_path, FakeClient(error=TimeoutError("slow")))
    assert t.cycle() == "traded"
    assert "p1-entry" in api.orders
    assert rows(tmp_path)[0]["note"].startswith("error: TimeoutError")


def test_unclear_or_refused_answer_fails_open(tmp_path):
    write_picks(tmp_path, [PICK])
    t, api, adv, _ = make(tmp_path, FakeClient(["not json at all"]))
    assert t.cycle() == "traded"
    assert rows(tmp_path)[0]["decision"] == "unclear"
    assert parse_verdict(json.dumps({"decision": "maybe", "reason": "", "confidence": 1})) is None
    assert parse_verdict(json.dumps({"decision": "veto", "reason": "x", "confidence": "9"}))["confidence"] == 1.0


def test_budget_cap_stops_calls_not_trades(tmp_path):
    write_picks(tmp_path, [PICK])
    t, api, adv, clock = make(tmp_path, FakeClient())
    adv.record(at=NOW.isoformat(), purpose="entry", cost_usd="15.0")   # this month's spend is at the cap
    assert t.cycle() == "traded"
    assert adv.client.calls == []
    assert not risk.spend_ok(15.0, 15.0)[0] and risk.spend_ok(14.99, 15.0)[0]
    # last month's spend does not count
    assert month_to_date_spend(adv.ledger_path, NOW + timedelta(days=31)) == 0.0


def test_call_cost_uses_the_price_table():
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 1_000_000,
             "cache_creation_input_tokens": 0}
    cost, _ = call_cost("claude-opus-5-5", usage)
    assert cost == 4.0 + 2.0 + 0.4
    assert call_cost("claude-haiku-5-5", {"input_tokens": 1_000_000})[0] == 0.10
    assert call_cost("mystery-model", {"input_tokens": 1_000_000})[0] == 5.0   # unknown = conservative


def test_advisor_off_or_keyless_means_no_advisor(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert Advisor.from_env(ADV_CFG, api=None, root=tmp_path) is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    assert Advisor.from_env({**CFG, "claude": {"enabled": False}}, api=None, root=tmp_path) is None
    assert Advisor.from_env({k: v for k, v in CFG.items() if k != "claude"}, api=None, root=tmp_path) is None


def test_picks_carry_text_fields_clamped(tmp_path):
    p = write_picks(tmp_path, [{**PICK, "thesis": "x" * 2000, "sources": ["https://a", "javascript:alert(1)", 5]}])
    e = picks.load(p, NOW, CFG)[0][0]
    assert len(e["thesis"]) == 800 and e["wrong_if"] == "closes below $170" and e["sources"] == ["https://a"]
    e = picks.load(write_picks(tmp_path, [{"id": "q", "symbol": "F", "action": "buy", "thesis": {"a": 1}}]), NOW, CFG)[0][0]
    assert e["thesis"] == "" and e["sources"] == []


def test_ping_logs_a_row(tmp_path):
    client = FakeClient(["pong"])
    adv = Advisor(ADV_CFG, api=None, root=tmp_path, client=client, now=lambda: NOW)
    assert adv.ping() == "pong"
    assert rows(tmp_path)[0]["purpose"] == "ping" and client.calls[0]["max_tokens"] == 1024
    assert TODAY.isoformat() in rows(tmp_path)[0]["at"]


def test_cut_off_answer_and_corrupt_memo_fail_open(tmp_path):
    write_picks(tmp_path, [PICK])
    t, api, adv, _ = make(tmp_path, FakeClient([""], stop_reason="max_tokens"))
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "advisor.json").write_text('{"p1": "veto"}')   # hand-edited garbage
    assert t.cycle() == "traded"
    row = rows(tmp_path)[0]
    assert row["decision"] == "unclear" and "max_tokens" in row["note"] and row["headlines"] == "1"
    adv.record = lambda **row: 1 / 0   # even broken bookkeeping does not stop the buy
    assert adv.check_entry(PICK, 180.0, TODAY + timedelta(days=1))[0]


def test_picks_with_odd_sources_do_not_crash(tmp_path):
    p = write_picks(tmp_path, [{**PICK, "sources": {"a": 1}}, {**PICK, "id": "p2", "sources": 5}])
    entries = picks.load(p, NOW, CFG)[0]
    assert [e["sources"] for e in entries] == [[], []]
