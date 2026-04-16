"""
_common.py — shared time utilities for the health-check rule engine.
"""

import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def to_ms_timestamp(time_str: str) -> int:
    """
    Parse several time formats into epoch milliseconds.

    Supported:
      -60                  → now minus 60 minutes
      2024-01-01 00:00:00  → full datetime
      2024-01-01T00:00:00  → ISO-style
      2024-01-01           → midnight that day
    """
    try:
        minutes = int(time_str)
        dt = datetime.now() + timedelta(minutes=minutes)
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(time_str, fmt).timestamp() * 1000)
        except ValueError:
            continue

    print(f"Error: cannot parse time string '{time_str}'")
    print("Supported: '2024-01-01 00:00:00' / '2024-01-01T00:00:00' / '2024-01-01' / '-60'")
    sys.exit(1)


def format_timestamp(ts_ms: int) -> str:
    """Epoch ms → local time string YYYY-MM-DD HH:MM:SS."""
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts_ms)


def now_ms() -> int:
    """Current time in epoch milliseconds."""
    return int(datetime.now().timestamp() * 1000)


def ago_ms(minutes: int) -> int:
    """Epoch ms for *minutes* ago."""
    return int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)


def ms_to_str(ms: int) -> str:
    """Alias of format_timestamp."""
    return format_timestamp(ms)


def parse_utc(s: str) -> Optional[datetime]:
    """
    Parse ISO UTC strings into timezone-aware datetime (UTC).

    Supports: ...Z / +00:00 / [UTC] suffix / fractional seconds stripped.
    """
    if not s:
        return None
    clean = re.sub(r"\.\d+", "", s.replace("[UTC]", "").strip())
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(clean, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
