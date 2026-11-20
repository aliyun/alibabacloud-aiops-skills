#!/usr/bin/env python3
"""Convert a time point to common formats.

Usage: python3 scripts/time_point.py [POINT] [--field FIELD]
Examples:
  python3 scripts/time_point.py now
  python3 scripts/time_point.py now-1m --field unix_timestamp_seconds
  python3 scripts/time_point.py now-1h30m8s --field unix_timestamp_milliseconds
  python3 scripts/time_point.py now+3h --field rfc3339
  python3 scripts/time_point.py '1970-01-01T08:00:01.234+08:00' -f unix_timestamp_milliseconds
  # Output: 1234

POINT defaults to now. Combine integer d, h, m and s units after now+ or now-;
the sign applies to the entire offset. RFC3339 inputs require Z or +/-HH:MM.
Leap seconds are not supported. All date and time strings use UTC.
Output is JSON by default; --field / -f prints one unquoted value.
Unix timestamps are rounded down to the requested precision.
"""

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
RELATIVE = re.compile(r"now(?:([+-])((?:[0-9]+[dhms])+))?")
RFC3339 = re.compile(
    r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?:\.([0-9]+))?([Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def parse_time_point(text):
    relative = RELATIVE.fullmatch(text)
    if relative:
        sign, duration = relative.groups()
        seconds, nanos = divmod(time.time_ns(), 1_000_000_000)
        offset = sum(int(amount) * UNIT_SECONDS[unit]
                     for amount, unit in re.findall(r"([0-9]+)([dhms])", duration or ""))
        seconds += -offset if sign == "-" else offset
        return EPOCH + timedelta(seconds=seconds), f"{nanos:09d}".rstrip("0")

    absolute = RFC3339.fullmatch(text)
    if not absolute:
        raise ValueError("expected now, a relative time such as now-1h30m8s, or RFC3339 with a time zone")
    date, clock, fraction, zone = absolute.groups()
    zone = "+00:00" if zone.upper() == "Z" else zone
    instant = datetime.fromisoformat(f"{date}T{clock}{zone}")
    return instant.astimezone(timezone.utc), fraction or ""


def format_time_point(instant, fraction):
    elapsed = instant - EPOCH
    seconds = elapsed.days * 86400 + elapsed.seconds
    decimal = "." + fraction if fraction else ""
    clock = instant.time().isoformat() + decimal
    return {
        "unix_timestamp_seconds": seconds,
        "unix_timestamp_milliseconds": seconds * 1000 + int((fraction + "000")[:3]),
        "rfc3339": f"{instant.date()}T{clock}Z",
        "iso8601": f"{instant.date()}T{clock}+00:00",
        "rfc2822": format_datetime(instant),
        "date": instant.date().isoformat(),
        "time": clock,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("point", nargs="?", default="now", help="time point (default: now)")
    parser.add_argument("-f", "--field", choices=tuple(format_time_point(EPOCH, "")), help="print only this field")
    args = parser.parse_args()
    try:
        result = format_time_point(*parse_time_point(args.point))
    except (ValueError, OverflowError) as error:
        parser.error(str(error))
    print(result[args.field] if args.field else json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
