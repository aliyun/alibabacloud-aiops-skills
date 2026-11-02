"""Bounded log-query time windows, shared by both model workflows."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TimeRangeError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "M": 2592000, "y": 31536000}


def parse_time_point(value, now):
    value = value.strip()
    if value == "now":
        return int(now.timestamp())
    match = re.fullmatch(r"now([+-])(\d+)([smhdwMy])", value)
    if match:
        seconds = int(match[2]) * UNITS[match[3]]
        return int(now.timestamp()) + (seconds if match[1] == "+" else -seconds)
    if re.fullmatch(r"\d{10,19}", value):
        return int(value) // {13: 1000, 16: 1000000, 19: 1000000000}.get(len(value), 1)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("missing timezone")
        return int(parsed.timestamp())
    except (ValueError, OverflowError):
        raise TimeRangeError("InvalidTimeRange", "Use Unix timestamps, now±N[s/m/h/d/w/M/y], or RFC3339 with a timezone") from None


def resolve_time_range(time_range=None, from_value=None, to_value=None, timezone=None, now=None):
    try:
        now = now or datetime.now(ZoneInfo(timezone) if timezone else None)
    except (ZoneInfoNotFoundError, ValueError):
        raise TimeRangeError("InvalidTimeRange", "Unknown timezone: " + str(timezone)) from None
    if time_range:
        expression = time_range.strip()
        match = re.fullmatch(r"last_(\d+)([smhdwMy])", expression)
        if match:
            end = int(now.timestamp())
            start = end - int(match[1]) * UNITS[match[2]]
        elif expression in ("today", "yesterday"):
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start, end = int(midnight.timestamp()), int(now.timestamp())
            if expression == "yesterday":
                start, end = int((midnight - timedelta(days=1)).timestamp()), start
        elif expression.count("~") == 1:
            first, last = expression.split("~")
            start, end = parse_time_point(first, now), parse_time_point(last, now)
        else:
            raise TimeRangeError("InvalidTimeRange", "Use last_15m, today, yesterday, or start~end")
    elif from_value is not None and to_value is not None:
        start, end = parse_time_point(from_value, now), parse_time_point(to_value, now)
    else:
        raise TimeRangeError("InvalidTimeRange", "Provide --time-range or both --from and --to")
    if start >= end:
        raise TimeRangeError("InvalidTimeRange", "Start must be before end")
    return start, end
