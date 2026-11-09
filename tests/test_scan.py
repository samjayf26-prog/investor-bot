"""Claude's hourly news-gap scan (bot/scan.py): the model proposes, the data and the rules decide."""
import csv
import json
from types import SimpleNamespace

from datetime import timedelta

from bot import picks, risk
from bot.scan import Scanner, expiry_utc, extract_json, rulebook

from test_bot import CFG, NOW, TODAY, FakeAlpaca, write_picks

SCAN_CFG = {**CFG, "claude": {"enabled": True, "model": "claude-opus-5-5", "monthly_budget_usd": 75.0,
                              "scan": {"enabled": True, "max_picks": 2, "min_gap_pct": 6.0}}}


class GapAlpaca(FakeAlpaca):
    prev = {"NVDA": 160.0, "F": 10.8, "WHOLE": 9.0}   # NVDA +12.5%, F +1.9%, WHOLE +11%

    def snapshots(self, syms):
        return {s: {"latestTrade": {"p": self.prices.get(s, 100.0)}, "dailyBar": {"o": 99.0, "vw": 1.0},
                    "prevDailyBar": {"c": self.prev.get(s, 100.0)}} for s in syms}


class FakeClient:
    def __init__(self, answer=None, error=None, text=None, searches=5):
        self.answer, self.error, self.text, self.searches, self.calls = answer, error, text, searches, []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        text = self.text if self.text is not None else json.dumps(self.answer)
        return SimpleNamespace(
            content=[SimpleNamespace(type="server_tool_use", name="web_search"), SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=20000, output_tokens=1500, cache_read_input_tokens=0,
                                  cache_creation_input_tokens=0, server_tool_use=SimpleNamespace(web_search_requests=self.searches)),
            model=kw["model"], stop_reason="end_turn", _request_id="req_scan")


ANSWER = {
    "picks": [
        {"symbol": "NVDA", "conviction": 3, "max_entry_price": 181.0, "thesis": "Beat and raise.", "wrong_if": "closes below $170",
         "sources": ["https://ir.example.com/q3", "https://news.example.com/nvda"], "news_time_et": "11:05"},
        {"symbol": "F", "conviction": 1, "max_entry_price": 11.2, "thesis": "Upgrade.", "wrong_if": "x",
         "sources": ["https://a"], "news_time_et": "11:10"},
        {"symbol": "WHOLE", "conviction": 2, "max_entry_price": 500.0, "thesis": "Contract.", "wrong_if": "y",
         "sources": [], "news_time_et": "11:20"},
        {"symbol": "SQQQ", "conviction": 1, "max_entry_price": 10.0, "thesis": "bear", "wrong_if": "z",
         "sources": [], "news_time_et": "11:30"},
    ],
    "close": [{"id": "old-EL", "reason": "guidance cut reversed the story"}, {"id": "ghost", "reason": "n/a"}],
    "notes": "Chips rallied on the NVDA print.",
}


def setup(tmp_path, client, state=None, current=True):
    (tmp_path / "state").mkdir()
    (tmp_path / "research").mkdir()
    (tmp_path / "state" / "positions.json").write_text(json.dumps(state if state is not None else {
        "old-EL": {"broker_symbol": "EL", "entry_date": "2026-10-01", "thesis": "Beauty rebound", "wrong_if": "guidance cut"}}))
    (tmp_path / "research" / "lessons.md").write_text("# Rulebook\n\n## Rules\n1. Buy only.\n2. Prefer 6% gaps.\n\n## Observations\n- x\n")
    (tmp_path / "research" / "journal.md").write_text("# Journal\n")
    if current:
        write_picks(tmp_path, [{"id": "r1", "symbol": "TSLA", "action": "buy", "thesis": "Roadster"}],
                    generated_at="2026-10-08T14:20:00Z", watch=["AMD"])
    api = GapAlpaca()
    return Scanner(SCAN_CFG, api, root=tmp_path, client=client, now=lambda: NOW), api


def rows(tmp_path):
    with open(tmp_path / "ledger" / "claude_calls.csv", newline="") as f:
        return list(csv.DictReader(f))


def test_scan_keeps_only_data_backed_picks_and_real_closes(tmp_path):
    sc, api = setup(tmp_path, FakeClient(ANSWER))
    assert sc.run() is True
    data = json.loads((tmp_path / "picks" / "latest.json").read_text())
    ids = [p["id"] for p in data["picks"]]
    assert ids == ["r1", "2026-10-08-1050-scan-NVDA", "2026-10-08-1050-scan-WHOLE"]   # F: gap too small; SQQQ: bear ETF
    nvda = data["picks"][1]
    assert nvda["conviction"] == 2 and nvda["max_entry_price"] == 181.0 and nvda["scan"] is True
    assert data["picks"][2]["max_entry_price"] == 10.1          # model's cap was silly; 1% over the last trade
    assert data["close"] == ["old-EL"] and data["watch"] == ["AMD"]
    assert data["expires_at"] == "2026-10-08T19:30:00Z" and data["generated_at"] == "2026-10-08T14:20:00Z"
    assert data["scan_at"] == "2026-10-08T14:50:00Z"
    entries, close, notes = picks.load(tmp_path / "picks" / "latest.json", NOW, CFG)
    assert [e["symbol"] for e in entries] == ["TSLA", "NVDA", "WHOLE"] and close == {"old-EL"} and notes == []
    # the model saw the rulebook, the open position's thesis and today's picks; the call used web search
    sent = sc.client.calls[0]
    assert "1. Buy only." in sent["messages"][0]["content"] and "Beauty rebound" in sent["messages"][0]["content"]
    assert sent["tools"][0]["type"] == "web_search_20260209" and sent["tools"][0]["max_uses"] == 8
    row = rows(tmp_path)[0]
    assert row["purpose"] == "scan" and row["headlines"] == "5" and float(row["cost_usd"]) > 0.05 + 0.08
    journal = (tmp_path / "research" / "journal.md").read_text()
    assert "New pick NVDA" in journal and "Close old-EL" in journal and "Dropped candidate F" in journal


def test_scan_with_nothing_new_changes_no_picks(tmp_path):
    sc, api = setup(tmp_path, FakeClient({"picks": [], "close": [], "notes": "Quiet tape."}))
    before = (tmp_path / "picks" / "latest.json").read_text()
    assert sc.run() is False
    assert (tmp_path / "picks" / "latest.json").read_text() == before
    assert "Quiet tape." in (tmp_path / "research" / "journal.md").read_text()


def test_scan_errors_and_garbage_change_nothing(tmp_path):
    sc, api = setup(tmp_path, FakeClient(error=RuntimeError("down")))
    before = (tmp_path / "picks" / "latest.json").read_text()
    assert sc.run() is False
    assert (tmp_path / "picks" / "latest.json").read_text() == before
    assert rows(tmp_path)[0]["note"].startswith("error: RuntimeError")
    sc.client = FakeClient(text="I could not find anything useful today.")
    assert sc.run() is False and rows(tmp_path)[1]["decision"] == "unclear"
    # prose around the JSON is tolerated
    assert extract_json('Here you go: {"picks": [], "close": [], "notes": "n"} thanks')["notes"] == "n"


def test_scan_respects_the_budget_and_market_hours(tmp_path):
    sc, api = setup(tmp_path, FakeClient(ANSWER))
    sc.advisor.record(at=NOW.isoformat(), purpose="scan", cost_usd="75.0")
    assert sc.run() is False and sc.client.calls == []
    (tmp_path / "b").mkdir()
    sc2, api2 = setup(tmp_path / "b", FakeClient(ANSWER))
    api2.open_ = False
    assert sc2.run() is False and sc2.client.calls == []


def test_scan_starts_a_fresh_picks_file_when_none_is_valid(tmp_path):
    sc, api = setup(tmp_path, FakeClient(ANSWER), current=False)
    assert sc.run() is True
    data = json.loads((tmp_path / "picks" / "latest.json").read_text())
    assert [p["symbol"] for p in data["picks"]] == ["NVDA", "WHOLE"] and data["close"] == ["old-EL"]


def test_schema_fallback_when_search_and_format_do_not_mix(tmp_path):
    class Picky(FakeClient):
        def create(self, **kw):
            if "format" in kw.get("output_config", {}):
                raise type("BadRequestError", (Exception,), {"status_code": 400})("output_config.format: not supported with tools")
            return super().create(**kw)
    sc, api = setup(tmp_path, Picky(ANSWER))
    assert sc.run() is True
    assert len(sc.client.calls) == 1 and "format" not in sc.client.calls[0]["output_config"]   # the refused call is not recorded


def test_helpers():
    assert rulebook("# R\n\n## Rules\n1. a\n2. b\n\n## Observations\nx") == "1. a\n2. b"
    assert expiry_utc(TODAY) == "2026-10-08T19:30:00Z"


def test_scan_adds_nothing_when_the_picks_file_is_full(tmp_path):
    sc, api = setup(tmp_path, FakeClient(ANSWER))
    write_picks(tmp_path, [{"id": f"r{i}", "symbol": s, "action": "buy"} for i, s in enumerate(("TSLA", "AMD", "MU"))],
                generated_at="2026-10-08T14:20:00Z")
    assert sc.run() is True   # the close still goes through
    data = json.loads((tmp_path / "picks" / "latest.json").read_text())
    assert [p["symbol"] for p in data["picks"]] == ["TSLA", "AMD", "MU"] and data["close"] == ["old-EL"]
    assert "no room" in (tmp_path / "research" / "journal.md").read_text()


def test_scan_survives_odd_fallback_answers(tmp_path):
    odd = {"picks": [{"symbol": "NVDA", "conviction": "high", "max_entry_price": "n/a", "thesis": 1, "wrong_if": None, "sources": "x"}],
           "close": [{"id": ["old-EL"], "reason": "r"}, {"id": "old-EL", "reason": "   "}], "notes": 5}
    sc, api = setup(tmp_path, FakeClient(text="Sure. " + json.dumps(odd)))
    assert sc.run() is True
    data = json.loads((tmp_path / "picks" / "latest.json").read_text())
    nvda = data["picks"][1]
    assert nvda["conviction"] == 1 and nvda["max_entry_price"] == 181.8 and nvda["sources"] == [] and data["close"] == []


def test_scan_hours_and_unrelated_400s():
    assert risk.scan_room(3, 1, 2) == 2 and risk.scan_room(3, 3, 2) == 0 and risk.scan_room(3, 2, 2) == 1
    assert risk.scan_conviction(3) == 2 and risk.scan_conviction("2") == 2 and risk.scan_conviction(None) == 1
    assert risk.scan_entry_cap(100.0, 102.0) == 102.0 and risk.scan_entry_cap(100.0, 110.0) == 101.0
    assert risk.scan_gap_ok(6.0, 6.0, 50.0, 2.0)[0] and not risk.scan_gap_ok(5.9, 6.0, 50.0, 2.0)[0]
    assert not risk.scan_gap_ok(None, 6.0, 50.0, 2.0)[0] and not risk.scan_gap_ok(9.0, 6.0, 1.5, 2.0)[0]


def test_scan_skips_early_runs_and_rethrows_unrelated_400s(tmp_path):
    sc, api = setup(tmp_path, FakeClient(ANSWER))
    sc.now = lambda: NOW - timedelta(hours=1)   # 9:50 ET
    assert sc.run() is False and sc.client.calls == []
    sc.now = lambda: NOW
    sc.client = FakeClient(error=type("BadRequestError", (Exception,), {"status_code": 400})("max_tokens too large"))
    assert sc.run() is False and rows(tmp_path)[0]["note"].startswith("error: BadRequestError: max_tokens")


def open_state(*symbols):
    return {f"old-{s}": {"broker_symbol": s, "entry_date": "2026-10-01"} for s in symbols}


def test_scan_adds_only_what_the_free_slots_allow(tmp_path):
    # three open and one research pick still waiting: one of the five slots is free
    sc, api = setup(tmp_path, FakeClient(ANSWER), state=open_state("EL", "AAA", "BBB"))
    assert sc.run() is True
    data = json.loads((tmp_path / "picks" / "latest.json").read_text())
    assert [p["id"] for p in data["picks"]] == ["r1", "2026-10-08-1050-scan-NVDA"]
    sent = sc.client.calls[0]["messages"][0]["content"]
    assert '"max_open_positions": 5' in sent and '"free": 1' in sent and '"waiting_in_picks_file": 1' in sent


def test_scan_adds_nothing_without_a_free_slot(tmp_path):
    sc, api = setup(tmp_path, FakeClient(ANSWER), state=open_state("EL", "AAA", "BBB", "CCC", "DDD"))
    assert sc.run() is True                                   # the close still goes through
    data = json.loads((tmp_path / "picks" / "latest.json").read_text())
    assert [p["symbol"] for p in data["picks"]] == ["TSLA"] and data["close"] == ["old-EL"]
    assert '"free": 0' in sc.client.calls[0]["messages"][0]["content"]
    assert "no room" in (tmp_path / "research" / "journal.md").read_text()


def test_scan_respects_the_picks_cap(tmp_path):
    def account(el_price):
        return json.dumps({"equity": "100", "positions": [{"symbol": "EL", "qty": "1", "current_price": str(el_price)},
                                                          {"symbol": "SPY", "qty": "0.03", "current_price": "700"}]})
    sc, api = setup(tmp_path, FakeClient(ANSWER))
    (tmp_path / "state" / "account.json").write_text(account(72))    # picks hold $72 of $100: $3 left under 75%
    assert sc.run() is True                                           # only the close
    data = json.loads((tmp_path / "picks" / "latest.json").read_text())
    assert [p["symbol"] for p in data["picks"]] == ["TSLA"]
    sent = sc.client.calls[0]["messages"][0]["content"]
    assert '"room_for_new_picks_usd": 3.0' in sent and '"free": 0' in sent
    (tmp_path / "b").mkdir()
    sc2, api2 = setup(tmp_path / "b", FakeClient(ANSWER))
    # $15 left holds two smallest picks ($10, then a trimmed $5); one is spoken for by the pick
    # already waiting in the file, so the scan may add one
    (tmp_path / "b" / "state" / "account.json").write_text(account(60))
    assert sc2.run() is True
    data = json.loads((tmp_path / "b" / "picks" / "latest.json").read_text())
    assert [p["symbol"] for p in data["picks"]] == ["TSLA", "NVDA"]
    assert '"free": 1' in sc2.client.calls[0]["messages"][0]["content"]
    (tmp_path / "d").mkdir()
    sc4, api4 = setup(tmp_path / "d", FakeClient(ANSWER))
    (tmp_path / "d" / "state" / "account.json").write_text(account(40))   # $35 left: room for both
    assert sc4.run() is True
    data = json.loads((tmp_path / "d" / "picks" / "latest.json").read_text())
    assert [p["symbol"] for p in data["picks"]] == ["TSLA", "NVDA", "WHOLE"]
    # an unreadable account snapshot never blocks the scan: the slot count still applies
    (tmp_path / "c").mkdir()
    sc3, api3 = setup(tmp_path / "c", FakeClient(ANSWER))
    (tmp_path / "c" / "state" / "account.json").write_text('{"equity": "n/a", "positions": "x"}')
    assert sc3.run() is True
    assert len(json.loads((tmp_path / "c" / "picks" / "latest.json").read_text())["picks"]) == 3
