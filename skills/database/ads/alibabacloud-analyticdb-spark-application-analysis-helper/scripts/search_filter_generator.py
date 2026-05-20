#!/usr/bin/env python3
"""
ADB Spark Search Filter Generator

Generate the --filters JSON string for `aliyun adb list-spark-apps` CLI commands
from natural-language-friendly command-line arguments.

Only Python standard library is required (datetime, time, json, argparse).

Usage examples:
  # Failed jobs in the last 1 hour
  python search_filter_generator.py --app-states FAILED --last-hours 1

  # Failed and running jobs in the last 24 hours with name matching etl.*
  python search_filter_generator.py \
      --app-states FAILED RUNNING \
      --last-hours 24 \
      --app-name-regex "etl.*"

  # Jobs that terminated yesterday
  python search_filter_generator.py --app-states FAILED --yesterday --time-type terminated

  # Specific AppId lookup
  python search_filter_generator.py --app-id s202401011200xx1234ab000****

# Note: All time calculations use the local system timezone.
# Timestamps are generated based on the machine's local time.
"""

import argparse
import datetime
import json
import sys
import time


def now_ms():
    """Return current time in milliseconds since epoch."""
    return int(time.time() * 1000)


def date_to_ms(date_obj, end_of_day=False):
    """Convert a datetime.date to millisecond timestamp.

    Args:
        date_obj: datetime.date instance.
        end_of_day: If True, use 23:59:59.999; otherwise 00:00:00.000.

    Returns:
        Millisecond timestamp as int.
    """
    if end_of_day:
        t = datetime.time(23, 59, 59, 999999)
    else:
        t = datetime.time.min
    dt = datetime.datetime.combine(date_obj, t)
    return int(dt.timestamp() * 1000)


def compute_time_range(args):
    """Compute (min_ms, max_ms) from the parsed CLI arguments.

    Priority: --yesterday > --last-hours > --last-minutes > --start-date/--end-date.
    If none provided, returns None (no time range filter).
    """
    if args.yesterday:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        return date_to_ms(yesterday, end_of_day=False), date_to_ms(yesterday, end_of_day=True)

    if args.last_hours is not None:
        max_val = now_ms()
        min_val = max_val - args.last_hours * 3600 * 1000
        return min_val, max_val

    if args.last_minutes is not None:
        max_val = now_ms()
        min_val = max_val - args.last_minutes * 60 * 1000
        return min_val, max_val

    if args.start_date or args.end_date:
        min_val = date_to_ms(args.start_date, end_of_day=False) if args.start_date else 0
        max_val = date_to_ms(args.end_date, end_of_day=True) if args.end_date else now_ms()
        return min_val, max_val

    return None


def build_filters(args):
    """Build the filters dictionary from parsed CLI arguments.

    Returns:
        dict: Filters object suitable for the list-spark-apps API.
    """
    filters = {}

    # Time range
    time_range = compute_time_range(args)
    if time_range is not None:
        min_ms, max_ms = time_range
        time_key = "TerminatedTimeRange" if args.time_type == "terminated" else "SubmittedTimeRange"
        filters[time_key] = {"Min": min_ms, "Max": max_ms}

    # Application states
    if args.app_states:
        filters["AppStates"] = args.app_states

    # Application name regex
    if args.app_name_regex:
        filters["AppNameRegex"] = args.app_name_regex

    # Resource group name
    if args.resource_group_name:
        filters["ResourceGroupName"] = args.resource_group_name

    # Application ID
    if args.app_id:
        filters["AppId"] = args.app_id

    return filters


def parse_date(s):
    """Parse a date string in YYYY-MM-DD format.

    Args:
        s: Date string.

    Returns:
        datetime.date instance.

    Raises:
        argparse.ArgumentTypeError: If the string cannot be parsed.
    """
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{s}'. Expected YYYY-MM-DD.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate --filters JSON for `aliyun adb list-spark-apps` CLI commands.",
        epilog="Output is a compact JSON string (no extra whitespace) that can be "
               "directly used as the value of the --filters parameter.",
    )

    # Time range options (mutually convenient, not strictly exclusive — last one wins)
    time_group = parser.add_argument_group("Time Range")
    time_group.add_argument(
        "--last-hours",
        type=int,
        default=None,
        help="Look back N hours from now (e.g., 1 for last hour, 24 for last day)",
    )
    time_group.add_argument(
        "--last-minutes",
        type=int,
        default=None,
        help="Look back N minutes from now (e.g., 30 for last 30 minutes)",
    )
    time_group.add_argument(
        "--yesterday",
        action="store_true",
        default=False,
        help="Set time range to yesterday 00:00:00 - 23:59:59.999",
    )
    time_group.add_argument(
        "--start-date",
        type=parse_date,
        default=None,
        help="Start date in YYYY-MM-DD format (inclusive, 00:00:00)",
    )
    time_group.add_argument(
        "--end-date",
        type=parse_date,
        default=None,
        help="End date in YYYY-MM-DD format (inclusive, 23:59:59.999)",
    )
    time_group.add_argument(
        "--time-type",
        choices=["submitted", "terminated"],
        default="submitted",
        help="Whether the time range applies to SubmittedTimeRange or "
             "TerminatedTimeRange (default: submitted)",
    )

    # Filter options
    filter_group = parser.add_argument_group("Filters")
    filter_group.add_argument(
        "--app-states",
        nargs="+",
        choices=["SUBMITTED", "STARTING", "RUNNING", "SUCCEEDED", "FAILED", "KILLED", "COMPLETED"],
        default=None,
        help="One or more application states to filter by "
             "(e.g., FAILED RUNNING)",
    )
    filter_group.add_argument(
        "--app-name-regex",
        default=None,
        help="Regex pattern to match application names (e.g., 'etl.*')",
    )
    filter_group.add_argument(
        "--resource-group-name",
        default=None,
        help="Exact resource group name to filter by (e.g., 'default')",
    )
    filter_group.add_argument(
        "--app-id",
        default=None,
        help="Exact application ID to look up (e.g., 's202401011200xx1234ab000****')",
    )

    # Output options
    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Pretty-print the JSON output (with indentation). "
             "By default, compact JSON is produced for direct CLI use.",
    )

    args = parser.parse_args()

    # Build the filters dict
    filters = build_filters(args)

    if not filters:
        parser.error("At least one filter condition is required (e.g., --app-states, --last-hours, --app-id).")

    # Serialize
    if args.pretty:
        filters_json = json.dumps(filters, indent=2)
    else:
        filters_json = json.dumps(filters, separators=(",", ":"))

    print(filters_json)


if __name__ == "__main__":
    main()
