#!/usr/bin/env python3
"""Parse the aggregate executor state from GetSemanticJobDetail JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STATUS_NAMES = {
    1: "WAITING",
    2: "RUNNING",
    3: "FINISH",
    4: "ERROR",
    6: "KILLED",
}


def extract_statuses(payload: Any) -> list[int]:
    if not isinstance(payload, dict):
        raise ValueError("response must be a JSON object")
    data = payload.get("Data", payload.get("data"))
    if not isinstance(data, dict):
        raise ValueError("response has no Data object")
    statuses = data.get("Statuses", data.get("statuses"))
    if not isinstance(statuses, list) or not statuses:
        raise ValueError("response has no non-empty Data.Statuses array")
    if any(type(status) is not int or status not in STATUS_NAMES for status in statuses):
        raise ValueError("response contains an unknown executor status code")
    return statuses


def aggregate_status(statuses: list[int]) -> str:
    """Return a fail-closed aggregate for a possibly multi-command executor."""
    if not statuses:
        raise ValueError("executor status array is empty")
    if any(status == 2 for status in statuses):
        return "RUNNING"
    if any(status == 1 for status in statuses):
        return "WAITING"
    if any(status == 4 for status in statuses):
        return "ERROR"
    if any(status == 6 for status in statuses):
        return "KILLED"
    if all(status == 3 for status in statuses):
        return "FINISH"
    raise ValueError("response has no recognized aggregate executor state")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print the aggregate state from a GetSemanticJobDetail response."
    )
    parser.add_argument("--response", required=True, type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.response.read_text(encoding="utf-8"))
        print(aggregate_status(extract_statuses(payload)))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"invalid GetSemanticJobDetail response: {error}") from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
