#!/usr/bin/env python3
"""
Semantically search across memory fragments.

Sends REST POST /memory_nodes/search. Tuning and billing parameters
(min_score, plan_version, enable_rerank) are server-controlled and not exposed;
the server applies its defaults (plan_version=pro, min_score=0.3).

Usage:
    python3 scripts/search_memory.py --user-id <id> --query <text>
    python3 scripts/search_memory.py --user-id <id> --query <text> --top-k 5
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(description="Semantic search across memory fragments.")
    parser.add_argument("--user-id", required=True, help="Memory entity ID.")
    parser.add_argument("--query", required=True, help="Search query text.")
    parser.add_argument("--memory-library-id", help="Memory library ID (optional).")
    parser.add_argument("--project-id", help="Memory project ID (optional, defaults to the default project).")
    parser.add_argument("--top-k", type=int, help="Max results (1-100, default 10).")
    args = parser.parse_args()

    # Build messages from query text
    messages = [{"role": "user", "content": args.query}]

    try:
        client = MemoryClient()
        result = client.search_memory(
            user_id=args.user_id,
            messages=messages,
            memory_library_id=args.memory_library_id,
            project_id=args.project_id,
            top_k=args.top_k,
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
