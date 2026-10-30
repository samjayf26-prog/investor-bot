"""Claude's trade picks: picks/latest.json, written by the scheduled Claude research run.

The bot treats the file as untrusted input: anything malformed is dropped, and every
number is clamped to config limits before it can size or exit a trade.
"""
import json
import re
from datetime import datetime, timedelta

ACTIONS = ("buy", "buy_put")
SYMBOL = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_TTL = timedelta(hours=30)
# Inverse and single-stock bear ETFs: bearish bets lost in every study we ran
# (review/profit-overhaul.md 3.2), so the bot refuses them whatever the picks file says.
BEAR_ETFS = {"SQQQ", "SPXU", "SPXS", "SDOW", "SDS", "SH", "PSQ", "QID", "SOXS", "TZA", "SRTY", "RWM",
             "DOG", "TECS", "FAZ", "LABD", "DRIP", "DUST", "JDST", "ERY", "SCO", "KOLD", "TBT", "TMV",
             "TSLQ", "TSLS", "TSLZ", "NVDS", "NVD", "MSTZ", "CONL", "UVXY", "VIXY", "VXX", "UVIX"}


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
    blocked = BEAR_ETFS | {str(b).upper() for b in cfg.get("blocked_symbols", [])}
    min_hold, default_hold = int(cfg.get("min_hold_days", 0)), int(cfg.get("default_hold_days", 5))
    earliest = cfg.get("earliest_entry_et", "10:00")
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
        if put and not cfg.get("options_enabled", False):
            notes.append(f"dropped {pid!r}: options are off (no bearish trades)")
            continue
        if sym in blocked:
            notes.append(f"dropped {pid!r}: {sym} is an inverse/bear ETF (no bearish trades)")
            continue
        when = str(raw.get("earliest_et") or earliest)
        if not HHMM.match(when):
            when = earliest
        when = min(max(when, "09:30"), "15:30")
        # No profit target unless Claude sets one: a 20-day time exit kept the post-news
        # drift that 10-15% targets gave away (review/profit-overhaul.md 3.2).
        target = raw.get("target_pct")
        entries.append({
            "id": pid,
            "symbol": sym,
            "action": action,
            "conviction": int(_clamp(raw.get("conviction"), 1, 3, 1)),
            "stop_pct": _clamp(raw.get("stop_pct"), 0.02 if put else 0.10, 0.6 if put else 0.25, 0.5 if put else 0.15),
            "target_pct": (1.0 if put else None) if target is None else _clamp(target, 0.10, 5.0, None),
            "max_hold_days": int(_clamp(raw.get("max_hold_days"), min_hold, cfg["max_hold_days"], default_hold)),
            "max_entry_price": _clamp(raw.get("max_entry_price"), 0, 1e6, 0) or None,
            "confirm_vwap": raw.get("confirm_vwap") is True,
            "earliest_et": when,
        })
    return entries, close_ids, notes


def watch_symbols(path, limit=10):
    """Optional "watch" list in the picks file: extra symbols for state/market.json only."""
    try:
        with open(path) as f:
            raw = json.load(f).get("watch", [])
    except (OSError, ValueError, AttributeError):
        return []
    out = []
    for s in raw if isinstance(raw, list) else []:
        s = str(s).upper()
        if SYMBOL.match(s) and s not in out:
            out.append(s)
    return out[:limit]


if __name__ == "__main__":
    # Validate a picks file the way the bot will read it: python -m bot.picks picks/latest.json
    import sys
    from datetime import timezone
    from pathlib import Path

    cfg = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text())
    entries, close_ids, notes = load(sys.argv[1], datetime.now(timezone.utc), cfg)
    print(json.dumps({"entries": entries, "close": sorted(close_ids), "notes": notes}, indent=2))
    sys.exit(1 if notes else 0)
