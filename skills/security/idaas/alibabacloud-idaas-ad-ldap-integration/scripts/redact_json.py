#!/usr/bin/env python3
"""Redact CLI JSON before it reaches tool logs; uses only Python's standard library.

Pipe a read command's stdout here before tee/display. Use shell pipefail so a
failed CLI call cannot be hidden by a successful final pipeline process.
Non-JSON input fails closed without echoing any source content.
"""

import json
import sys

from eiam_read import redact


def main():
    try:
        value = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{"error":"Invalid JSON; original input suppressed"}', file=sys.stderr)
        return 1
    json.dump(redact(value), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
