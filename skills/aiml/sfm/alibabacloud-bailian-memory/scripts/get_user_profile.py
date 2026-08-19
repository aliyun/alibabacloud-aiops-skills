#!/usr/bin/env python3
"""
Get extracted user profile based on a profile schema.

Usage:
    python3 scripts/get_user_profile.py --user-id <id> --profile-schema-id <id>
    # 展开 value_items（含 item_id，供画像值 update/delete 使用）
    python3 scripts/get_user_profile.py --user-id <id> --profile-schema-id <id> --need-detail
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(description="Get extracted user profile by schema.")
    parser.add_argument("--user-id", required=True, help="Memory entity ID.")
    parser.add_argument("--profile-schema-id", required=True, help="Profile schema ID.")
    parser.add_argument("--memory-library-id", help="Memory library ID (optional).")
    parser.add_argument("--need-detail", action="store_true",
                        help="Return expanded value_items (each with item_id/value/status) "
                             "instead of a joined value string.")
    args = parser.parse_args()

    try:
        client = MemoryClient()
        result = client.get_user_profile(
            profile_schema_id=args.profile_schema_id,
            user_id=args.user_id,
            memory_library_id=args.memory_library_id,
            need_detail=args.need_detail or None,
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
