#!/usr/bin/env python3
"""
Asynchronously extract memories from conversation messages.

Sends REST POST /add-async in messages mode. Accepted immediately and returns
an event_id while LLM extraction runs in the background. Default usage is
fire-and-forget; check status via get_event.py only when confirmation is needed.
To save a known text as-is (no extraction), use add_memory_content.py instead.

Usage:
    python3 scripts/add_memory_messages.py --user-id <id> --messages '<json>'
    python3 scripts/add_memory_messages.py --user-id <id> --messages '<json>' --project-ids p1,p2
    python3 scripts/add_memory_messages.py --user-id <id> --messages '<json>' --profile-schema <schema_id>
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(
        description="Asynchronously extract memories from conversation messages (fire-and-forget).")
    parser.add_argument("--user-id", required=True, help="Memory entity ID (max 64 chars).")
    parser.add_argument("--messages", required=True,
                        help="JSON array of conversation messages (roles user/assistant/tool, "
                             "standard OpenAI tool_calls format supported).")
    parser.add_argument("--timestamp", type=int, help="Message Unix timestamp in seconds (optional, defaults to current time).")
    parser.add_argument("--memory-library-id", help="Memory library ID (optional, uses default).")
    parser.add_argument("--project-id", help="Memory project ID (optional). Mutually exclusive with --project-ids.")
    parser.add_argument("--project-ids", help="Comma-separated memory project IDs for extracting into multiple "
                                              "projects at once. Mutually exclusive with --project-id.")
    parser.add_argument("--profile-schema", help="Profile schema ID; pass it to also extract user profile "
                                                 "attributes from the conversation (create the schema via "
                                                 "manage_profile_schema.py or in the Bailian console).")
    parser.add_argument("--meta-data", help="JSON object of custom metadata (optional).")
    args = parser.parse_args()

    if args.project_id and args.project_ids:
        parser.error("--project-id and --project-ids are mutually exclusive.")

    try:
        messages = json.loads(args.messages)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON for --messages: {e}", file=sys.stderr)
        sys.exit(1)

    meta_data = None
    if args.meta_data:
        try:
            meta_data = json.loads(args.meta_data)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON for --meta-data: {e}", file=sys.stderr)
            sys.exit(1)

    project_ids = None
    if args.project_ids:
        project_ids = [p.strip() for p in args.project_ids.split(",") if p.strip()]

    try:
        client = MemoryClient()
        result = client.add_memory_messages(
            user_id=args.user_id,
            messages=messages,
            timestamp=args.timestamp,
            memory_library_id=args.memory_library_id,
            project_id=args.project_id,
            project_ids=project_ids,
            profile_schema=args.profile_schema,
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
