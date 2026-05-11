"""Shared structured error helpers."""

import json
import sys


def die(message: str, hint: str = "") -> None:
    """Print a structured error to stderr and exit."""
    err = {"success": False, "error": message}
    if hint:
        err["hint"] = hint
    print(json.dumps(err), file=sys.stderr)
    sys.exit(1)
