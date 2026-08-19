#!/usr/bin/env python3
"""
Update or delete a memory fragment.

Sends REST PATCH / DELETE /memory_nodes/{id}.
Delete is irreversible — the agent must confirm with the user before running it.

Usage:
    python3 scripts/manage_memory.py update --memory-node-id <id> --user-id <uid> --content <text>
    python3 scripts/manage_memory.py delete --memory-node-id <id>
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def cmd_update(args):
    meta_data = None
    if args.meta_data:
        try:
            meta_data = json.loads(args.meta_data)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON for --meta-data: {e}", file=sys.stderr)
            sys.exit(1)

    client = MemoryClient()
    result = client.update_memory(
        memory_node_id=args.memory_node_id,
        custom_content=args.content,
        user_id=args.user_id,
        memory_library_id=args.memory_library_id,
        timestamp=args.timestamp,
        meta_data=meta_data,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_delete(args):
    client = MemoryClient()
    result = client.delete_memory(
        memory_node_id=args.memory_node_id,
        memory_library_id=args.memory_library_id,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Update or delete a memory fragment.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # update subcommand
    update_parser = subparsers.add_parser("update", help="Update a memory fragment.")
    update_parser.add_argument("--memory-node-id", required=True, help="Memory fragment ID.")
    update_parser.add_argument("--content", required=True, help="New content (max 512 chars).")
    update_parser.add_argument("--user-id", required=True, help="Memory entity ID.")
    update_parser.add_argument("--memory-library-id", help="Memory library ID (optional, for ownership check).")
    update_parser.add_argument("--timestamp", type=int, help="Unix timestamp in seconds (optional).")
    update_parser.add_argument("--meta-data", help="JSON object of metadata (optional, incremental update: "
                                                   "keys not specified remain unchanged).")

    # delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete a memory fragment (irreversible).")
    delete_parser.add_argument("--memory-node-id", required=True, help="Memory fragment ID.")
    delete_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    args = parser.parse_args()

    try:
        if args.command == "update":
            cmd_update(args)
        elif args.command == "delete":
            cmd_delete(args)
    except MemoryApiError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
