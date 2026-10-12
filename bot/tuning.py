"""Settings the bot learns on its own (tuning.json), and the bounds they must stay in.

Only the scalper's strategy knobs below can be learned. Safety limits (daily loss caps,
drawdown halt, kill switch, trade size, position limits, mode) are never read from
tuning.json, whatever it contains. Set "learning": false in config.json to ignore it.
"""
import json

from .trader import ROOT

PATH = ROOT / "tuning.json"

# key: (lowest, highest, type)
BOUNDS = {
    "take_profit_pct": (0.0005, 0.01, float),
    "stop_pct": (0.0005, 0.01, float),
    "max_hold_minutes": (1, 30, int),
    "ema_fast": (2, 20, int),
    "ema_slow": (5, 60, int),
}


def load(path=PATH):
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def clamp(key, value):
    lo, hi, kind = BOUNDS[key]
    return kind(min(hi, max(lo, kind(value))))


def apply(sc, tuned):
    """The scalper config with learned values laid over it, clamped to BOUNDS."""
    out = dict(sc)
    learned = tuned.get("scalper") if isinstance(tuned.get("scalper"), dict) else {}
    for key in BOUNDS:
        if key in learned:
            try:
                out[key] = clamp(key, learned[key])
            except (TypeError, ValueError):
                pass
    if out["ema_fast"] >= out["ema_slow"]:
        out["ema_fast"], out["ema_slow"] = sc["ema_fast"], sc["ema_slow"]
    enabled = learned.get("enabled_symbols")
    if isinstance(enabled, list):
        keep = [s for s in sc["symbols"] if s in enabled]
        if keep:
            out["enabled_symbols"] = keep
    return out


def scalper_config(cfg, path=PATH):
    sc = cfg["scalper"]
    return apply(sc, load(path)) if cfg.get("learning", True) else dict(sc)
