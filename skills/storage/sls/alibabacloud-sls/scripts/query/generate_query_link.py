#!/usr/bin/env python3
"""Generate an SLS Logstore console query URL locally, without cloud API calls."""

import argparse
import base64
import time
from urllib.parse import quote


def nonempty(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be empty or whitespace")
    return value


def nonnegative_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if number < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return number


def positive_int(value):
    number = nonnegative_int(value)
    if number == 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_query_url(project, logstore, query, start_time, end_time):
    encoded_query = base64.b64encode(query.encode("utf-8")).decode("ascii")
    params = (
        "encode=base64&queryString=" + encoded_query
        + "&queryTimeType=99&startTime=" + str(start_time)
        + "&endTime=" + str(end_time)
    )
    return (
        "https://sls.console.aliyun.com/lognext/project/"
        + quote(project, safe="")
        + "/logsearch/" + quote(logstore, safe="")
        + "?" + quote(params, safe="")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=nonempty)
    parser.add_argument("--logstore", required=True, type=nonempty)
    parser.add_argument("--query", required=True, type=nonempty, help="Original query text")
    parser.add_argument(
        "--range", dest="range_seconds", type=positive_int, metavar="SECONDS",
        help="Last N seconds ending now (default: 900); cannot combine with --from/--to",
    )
    parser.add_argument(
        "--from", dest="start_time", type=nonnegative_int, metavar="UNIX_SECONDS",
        help="Absolute start time; requires --to",
    )
    parser.add_argument(
        "--to", dest="end_time", type=nonnegative_int, metavar="UNIX_SECONDS",
        help="Absolute end time; requires --from",
    )
    args = parser.parse_args()

    has_absolute_time = args.start_time is not None or args.end_time is not None
    if has_absolute_time:
        if args.range_seconds is not None:
            parser.error("--range cannot be combined with --from or --to")
        if args.start_time is None or args.end_time is None:
            parser.error("--from and --to must be supplied together")
        start_time, end_time = args.start_time, args.end_time
    else:
        end_time = int(time.time())
        start_time = end_time - (args.range_seconds or 900)

    if start_time < 0:
        parser.error("time range starts before Unix epoch")
    if start_time >= end_time:
        parser.error("--from must be earlier than --to")

    print(build_query_url(args.project, args.logstore, args.query, start_time, end_time))


if __name__ == "__main__":
    main()
