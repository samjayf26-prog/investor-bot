"""Claude's risk overlay: overlay/latest.json, written by a scheduled Claude run.

It can only make the bot trade less. Anything missing, expired, malformed or
from the future is ignored and the config's no_overlay_risk_dial applies.
"""
import json
from datetime import datetime, timedelta

from .risk import dial_multiplier

MAX_TTL = timedelta(hours=8)


def _ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load(path, now, fallback_dial, symbol):
    """Returns (multiplier, blocked_reason or None, note)."""
    fallback = (dial_multiplier(fallback_dial), None, "no valid overlay; using config default")
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return fallback
    except (OSError, ValueError) as e:
        return (*fallback[:2], f"overlay unreadable ({e}); using config default")

    try:
        if data.get("schema_version") != 1:
            raise ValueError("schema_version must be 1")
        generated, expires = _ts(data["generated_at"]), _ts(data["expires_at"])
        if generated > now + timedelta(minutes=5):
            raise ValueError("generated_at is in the future")
        if expires - generated > MAX_TTL:
            raise ValueError("expires_at is too far after generated_at")
        dial = data["risk_dial"]
        if dial not in ("normal", "reduced", "off"):
            raise ValueError(f"unknown risk_dial {dial!r}")
        avoid = data.get("avoid", [])
        if not isinstance(avoid, list):
            raise ValueError("avoid must be a list")
    except (KeyError, TypeError, ValueError) as e:
        return (*fallback[:2], f"overlay rejected ({e}); using config default")

    if now >= expires:
        return (*fallback[:2], "overlay expired; using config default")

    for item in avoid:
        try:
            if item.get("symbol") in ("*", symbol) and now < _ts(item["until"]):
                return 0.0, f"overlay avoid: {item.get('reason', 'no reason given')}", "overlay applied"
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    # The overlay may only reduce: never above the config default.
    mult = min(dial_multiplier(dial), dial_multiplier(fallback_dial))
    return mult, None, f"overlay dial {dial}: {str(data.get('summary', ''))[:200]}"
