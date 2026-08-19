#!/usr/bin/env python3
"""
Operate on a single user profile attribute value item (add / update / delete).

Sends REST PATCH /profile_schemas/{id}/profile_values.

Operation semantics (--op-type, case-insensitive):
- add:    appends --value as a new value item; --item-id not needed
- update: modifies an existing value item; --item-id required
- delete: removes an existing value item; --item-id required

attribute_id comes from get_user_profile.py output (field 'id');
item_id comes from get_user_profile.py --need-detail output (value_items[].item_id).

Usage:
    python3 scripts/update_user_profile.py --entity-id <user_id> --profile-schema-id <schema_id> \
        --attribute-id attr_001 --op-type add --value "游泳"
    python3 scripts/update_user_profile.py --entity-id <user_id> --profile-schema-id <schema_id> \
        --attribute-id attr_001 --op-type update --item-id 5634 --value "打排球"
    python3 scripts/update_user_profile.py --entity-id <user_id> --profile-schema-id <schema_id> \
        --attribute-id attr_001 --op-type delete --item-id 5634
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(
        description="Operate on a single user profile attribute value item (add/update/delete).")
    parser.add_argument("--entity-id", required=True,
                        help="Profile owner entity ID; for user profiles pass the user ID.")
    parser.add_argument("--profile-schema-id", required=True, help="Profile schema ID.")
    parser.add_argument("--attribute-id", required=True,
                        help="Attribute ID (from get_user_profile.py output field 'id').")
    parser.add_argument("--op-type", required=True, choices=["add", "update", "delete"],
                        help="Operation type.")
    parser.add_argument("--item-id", type=int,
                        help="Value item ID (from get_user_profile.py --need-detail). "
                             "Required when --op-type is update or delete.")
    parser.add_argument("--value", help="Attribute value content. Used when --op-type is add or update.")
    parser.add_argument("--memory-library-id", help="Memory library ID (optional, for ownership check).")
    args = parser.parse_args()

    try:
        client = MemoryClient()
        result = client.update_user_profile_value(
            profile_schema_id=args.profile_schema_id,
            entity_id=args.entity_id,
            attribute_id=args.attribute_id,
            op_type=args.op_type,
            item_id=args.item_id,
            value=args.value,
            memory_library_id=args.memory_library_id,
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
