#!/usr/bin/env python3
"""Convert a time range to common formats.

Usage: python3 scripts/time_range.py RANGE [--tz ZONE] [--at POINT] [-f FIELD]
Examples:
  python3 scripts/time_range.py last_1h
  python3 scripts/time_range.py last_3d -f unix_timestamp_milliseconds
  python3 scripts/time_range.py last_1mo -f rfc3339
  python3 scripts/time_range.py prev_year --tz Asia/Shanghai -f rfc3339
  python3 scripts/time_range.py this_month --tz Asia/Shanghai -f rfc3339
  python3 scripts/time_range.py yesterday --tz Asia/Shanghai --at 1970-01-02T12:00:00+08:00 -f unix_timestamp_seconds
  # Output: {"start": -28800, "end": 57600}

All ranges include start and exclude end. The reference point (--at) defaults to now.
  last_Ns/m/h/d/w: fixed duration ending at the reference point (1m = one minute,
                   1d = 24 hours, 1w = 7 days). Examples: last_1m, last_3d, last_1w.
  last_Nmo:        N calendar months back at the same local time, clamped to month end.
  prev_day, prev_week, prev_month, prev_year: the entire preceding calendar period.
  this_day, this_week, this_month: start of the current period up to the reference point.
  Use this_ with a single unit, without a count. Shortcuts: today = this_day;
  yesterday (or yestoday) = prev_day.
Weeks start on Monday. Calendar boundaries use --tz (IANA name; default UTC).
Output strings always use UTC. JSON fields contain {"start": ..., "end": ...};
--field / -f prints just the selected pair.
"""

import argparse
import calendar
import json
import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from time_point import EPOCH, UNIT_SECONDS, format_time_point, parse_time_point


def previous_month(date, count):
    year, month_index = divmod(date.year * 12 + date.month - 1 - count, 12)
    month = month_index + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return date.replace(year=year, month=month, day=day)


def resolve_range(expression, anchor, zone):
    instant, fraction = anchor
    local = instant.astimezone(zone)
    rolling = re.fullmatch(r"last_([1-9][0-9]*)(mo|[wdhms])", expression)
    if rolling:
        count, unit = rolling.groups()
        if unit == "mo":
            start = previous_month(local, int(count)).astimezone(timezone.utc)
        else:
            unit_seconds = 604800 if unit == "w" else UNIT_SECONDS[unit]
            start = instant - timedelta(seconds=int(count) * unit_seconds)
        return (start, fraction), anchor

    aliases = {"today": "this_day", "yesterday": "prev_day", "yestoday": "prev_day"}
    expression = aliases.get(expression, expression)
    if expression == "last_week":
        raise ValueError("use prev_week for the previous full calendar week")
    if expression not in ("this_day", "this_week", "this_month", "prev_day", "prev_week", "prev_month", "prev_year"):
        raise ValueError(f"unknown range {expression!r}; see --help for supported expressions")
    kind, unit = expression.split("_")
    today = local.date()
    if unit == "day":
        boundary = today
    elif unit == "week":
        boundary = today - timedelta(days=today.weekday())
    elif unit == "month":
        boundary = today.replace(day=1)
    else:
        boundary = today.replace(month=1, day=1)

    def midnight(date):
        return datetime.combine(date, time.min, tzinfo=zone).astimezone(timezone.utc), ""

    if kind == "this":
        return midnight(boundary), anchor
    if unit == "month":
        start_date = previous_month(boundary, 1)
    elif unit == "year":
        start_date = boundary.replace(year=boundary.year - 1)
    else:
        start_date = boundary - timedelta(days=7 if unit == "week" else 1)
    return midnight(start_date), midnight(boundary)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("range", help="rolling or calendar range")
    parser.add_argument("--tz", default="UTC", help="calendar time zone (default: UTC)")
    parser.add_argument("--at", default="now", help="reference time, e.g. an RFC3339 timestamp")
    parser.add_argument("-f", "--field", choices=tuple(format_time_point(EPOCH, "")), help="print only this format")
    args = parser.parse_args()
    try:
        zone = ZoneInfo(args.tz)
        start, end = resolve_range(args.range, parse_time_point(args.at), zone)
        first, last = format_time_point(*start), format_time_point(*end)
    except ZoneInfoNotFoundError:
        parser.error(f"time zone {args.tz!r} not found; check its name and the installed time zone database")
    except (ValueError, OverflowError) as error:
        parser.error(str(error))
    result = {key: {"start": first[key], "end": last[key]} for key in first}
    print(json.dumps(result[args.field]) if args.field else json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
