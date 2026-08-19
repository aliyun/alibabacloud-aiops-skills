#!/usr/bin/env python3
"""
List memory fragments with pagination.

Usage:
    python3 scripts/list_memories.py --user-id <id>
    python3 scripts/list_memories.py --user-id <id> --page-num 1 --page-size 20
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(description="List memory fragments with pagination.")
    parser.add_argument("--user-id", required=True, help="Memory entity ID.")
    parser.add_argument("--memory-library-id", help="Memory library ID (optional).")
    parser.add_argument("--project-id", help="Memory fragment rule ID (optional).")
    parser.add_argument("--page-num", type=int, help="Page number (starts at 1, default 1).")
    parser.add_argument("--page-size", type=int, help="Items per page (default 10).")
    args = parser.parse_args()

    try:
        client = MemoryClient()
        result = client.list_memories(
            user_id=args.user_id,
            memory_library_id=args.memory_library_id,
            project_id=args.project_id,
            page_num=args.page_num,
            page_size=args.page_size,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except MemoryApiError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
