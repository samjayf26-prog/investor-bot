"""Shared bits: the market's time zone and the run log (also the GitHub step summary)."""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent.parent


def log(msg):
    stamp = datetime.now(ET).strftime("%H:%M:%S ET")
    print(f"[{stamp}] {msg}", flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"- `{stamp}` {msg}\n")
