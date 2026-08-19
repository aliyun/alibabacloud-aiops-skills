#!/usr/bin/env python3
"""
Query the status of an asynchronous memory operation by event_id.

Sends REST GET /events/{event_id}. Usually NOT needed — writes are
fire-and-forget. Query only when the user explicitly asks to confirm the write,
or a later step depends on extraction completion. Returns one event record per
resource (project/profile); status is PENDING / SUCCEEDED / FAILED, and FAILED
records carry a 'detail' field formatted as 'errorCode: errorMessage'.

Usage:
    python3 scripts/get_event.py --event-id <event_id>
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(description="Query asynchronous memory event status.")
    parser.add_argument("--event-id", required=True,
                        help="The event ID returned by add_memory_messages.py or add_memory_content.py.")
    args = parser.parse_args()

    try:
        client = MemoryClient()
        result = client.get_event(args.event_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except MemoryApiError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
