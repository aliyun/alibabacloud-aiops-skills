#!/usr/bin/env python3
"""
Asynchronously save a custom content string as memory (no LLM extraction).

Sends REST POST /add-async in custom_content mode. Custom content binds to
exactly one project (--project-ids not supported); profile extraction depends on
conversation messages (--profile-schema not supported).
To extract memories from a conversation, use add_memory_messages.py instead.

Usage:
    python3 scripts/add_memory_content.py --user-id <id> --content <text>
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(
        description="Asynchronously save custom content as memory without LLM extraction (fire-and-forget).")
    parser.add_argument("--user-id", required=True, help="Memory entity ID (max 64 chars).")
    parser.add_argument("--content", required=True, help="The memory content to save as-is (max 512 chars).")
    parser.add_argument("--timestamp", type=int, help="Message Unix timestamp in seconds (optional, defaults to current time).")
    parser.add_argument("--memory-library-id", help="Memory library ID (optional, uses default).")
    parser.add_argument("--project-id", help="Memory project ID (optional; custom content binds to exactly one project).")
    parser.add_argument("--meta-data", help="JSON object of custom metadata (optional).")
    args = parser.parse_args()

    meta_data = None
    if args.meta_data:
        try:
            meta_data = json.loads(args.meta_data)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON for --meta-data: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        client = MemoryClient()
        result = client.add_memory_content(
            user_id=args.user_id,
            custom_content=args.content,
            timestamp=args.timestamp,
            memory_library_id=args.memory_library_id,
            project_id=args.project_id,
            meta_data=meta_data,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except MemoryApiError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
