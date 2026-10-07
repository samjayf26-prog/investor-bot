"""Claude's trade picks: picks/latest.json, written by the scheduled Claude research run.

The bot treats the file as untrusted input: anything malformed is dropped, and every
number is clamped to config limits before it can size or exit a trade.
"""
import json
import re
from datetime import datetime, timedelta

ACTIONS = ("buy", "buy_put")
SYMBOL = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")
MAX_TTL = timedelta(hours=30)


def _ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _clamp(value, lo, hi, default):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(v, lo), hi)


def load(path, now, cfg):
    """Returns (entries, close_ids, notes). Entries only when the file is fresh."""
    notes = []
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return [], set(), ["no picks file"]
    except (OSError, ValueError) as e:
        return [], set(), [f"picks file unreadable: {e}"]
    if not isinstance(data, dict) or data.get("schema_version") != 2:
        return [], set(), ["picks file has wrong schema_version"]

    close_ids = {c for c in data.get("close", []) if isinstance(c, str)}
    try:
        generated, expires = _ts(data["generated_at"]), _ts(data["expires_at"])
    except (KeyError, TypeError, ValueError) as e:
        return [], close_ids, [f"picks timestamps invalid: {e}"]
    if generated > now + timedelta(minutes=5) or expires - generated > MAX_TTL:
        return [], close_ids, ["picks timestamps out of range; ignoring new entries"]
    if now >= expires:
        return [], close_ids, ["picks expired; no new entries"]

    entries, seen = [], set()
    for raw in data.get("picks", [])[: cfg["max_picks_per_run"]]:
        try:
            pid, sym, action = str(raw["id"]), str(raw["symbol"]).upper(), raw["action"]
        except (KeyError, TypeError):
            notes.append("dropped a pick with missing fields")
            continue
        if action not in ACTIONS or not SYMBOL.match(sym) or not re.match(r"^[\w.-]{1,60}$", pid) or pid in seen:
            notes.append(f"dropped invalid pick {pid!r}")
            continue
        seen.add(pid)
        put = action == "buy_put"
        entries.append({
            "id": pid,
            "symbol": sym,
            "action": action,
            "conviction": int(_clamp(raw.get("conviction"), 1, 3, 1)),
            "stop_pct": _clamp(raw.get("stop_pct"), 0.02, 0.6 if put else 0.25, 0.5 if put else 0.08),
            "target_pct": _clamp(raw.get("target_pct"), 0.03, 5.0, 1.0 if put else 0.15),
            "max_hold_days": int(_clamp(raw.get("max_hold_days"), 0, cfg["max_hold_days"], 5)),
            "max_entry_price": _clamp(raw.get("max_entry_price"), 0, 1e6, 0) or None,
        })
    return entries, close_ids, notes


if __name__ == "__main__":
    # Validate a picks file the way the bot will read it: python -m bot.picks picks/latest.json
    import sys
    from datetime import timezone
    from pathlib import Path

    cfg = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text())
    entries, close_ids, notes = load(sys.argv[1], datetime.now(timezone.utc), cfg)
    print(json.dumps({"entries": entries, "close": sorted(close_ids), "notes": notes}, indent=2))
    sys.exit(1 if notes else 0)
