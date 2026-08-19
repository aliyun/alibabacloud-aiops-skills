#!/usr/bin/env python3
"""
Manage user profile schemas: create / list / update.

A profile schema defines which user attributes to extract from conversations.
The profile_schema_id is used in memory extraction (profile_schema) and
profile get/update operations.

Usage:
    # 创建 schema（immutable=true 的属性必须提供 default_value）
    python3 scripts/manage_profile_schema.py create --name "用户基础画像" \
        --attributes '[{"name":"姓名","description":"用户姓名","immutable":true,"default_value":"张三"},
                       {"name":"兴趣","description":"兴趣爱好"}]' \
        [--description <text>] [--plan-version pro|lite]

    # 分页查询 schema 列表
    python3 scripts/manage_profile_schema.py list [--page-num 1] [--page-size 10]

    # 更新 schema（至少传一个可更新字段；属性变更通过 attributes-operations）
    python3 scripts/manage_profile_schema.py update --profile-schema-id <id> [--name <name>] \
        [--description <text>] [--plan-version pro|lite] \
        [--attributes-operations '[{"op":"add","name":"喜欢的音乐"},
                                   {"op":"update","attribute_id":"attr_002","name":"常用运动"},
                                   {"op":"delete","attribute_id":"attr_003"}]']

attributes_operations semantics (each element requires 'op'):
- op=add:    requires 'name'; 'immutable' only supported here (default_value
             required when immutable=true)
- op=update: requires 'attribute_id' and at least one of name/description/
             default_value; 'immutable' cannot be updated
- op=delete: requires 'attribute_id'
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def _parse_json_array(raw, arg_name):
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON for {arg_name}: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(parsed, list) or not parsed:
        print(f"ERROR: {arg_name} must be a non-empty JSON array.", file=sys.stderr)
        sys.exit(1)
    return parsed


def main():
    parser = argparse.ArgumentParser(description="Manage user profile schemas (create/list/update).")
    subparsers = parser.add_subparsers(dest="action", required=True)

    create_parser = subparsers.add_parser("create", help="Create a profile schema.")
    create_parser.add_argument("--name", required=True, help="Schema name (max 32 chars).")
    create_parser.add_argument("--attributes", required=True,
                               help="JSON array of attribute definitions; each element requires 'name', "
                                    "optional 'description'/'immutable'/'default_value' "
                                    "(default_value required when immutable=true).")
    create_parser.add_argument("--description", help="Schema description (optional).")
    create_parser.add_argument("--plan-version", choices=["pro", "lite"],
                               help="Billing plan (defaults to pro server-side).")
    create_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    list_parser = subparsers.add_parser("list", help="List profile schemas with pagination.")
    list_parser.add_argument("--page-num", type=int, help="Page number (starts at 1, default 1).")
    list_parser.add_argument("--page-size", type=int, help="Items per page (default 10).")
    list_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    update_parser = subparsers.add_parser("update", help="Update a profile schema.")
    update_parser.add_argument("--profile-schema-id", required=True, help="Profile schema ID.")
    update_parser.add_argument("--name", help="New schema name (max 32 chars).")
    update_parser.add_argument("--description", help="New schema description.")
    update_parser.add_argument("--plan-version", choices=["pro", "lite"], help="Billing plan.")
    update_parser.add_argument("--attributes-operations",
                               help="JSON array of attribute change operations "
                                    "(op=add/update/delete, see module docstring).")
    update_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    args = parser.parse_args()

    try:
        client = MemoryClient()
        if args.action == "create":
            attributes = _parse_json_array(args.attributes, "--attributes")
            result = client.create_profile_schema(
                name=args.name,
                attributes=attributes,
                description=args.description,
                plan_version=args.plan_version,
                memory_library_id=args.memory_library_id,
            )
        elif args.action == "list":
            result = client.list_profile_schemas(
                page_num=args.page_num,
                page_size=args.page_size,
                memory_library_id=args.memory_library_id,
            )
        else:  # update
            operations = None
            if args.attributes_operations:
                operations = _parse_json_array(args.attributes_operations, "--attributes-operations")
            result = client.update_profile_schema(
                profile_schema_id=args.profile_schema_id,
                name=args.name,
                description=args.description,
                plan_version=args.plan_version,
                attributes_operations=operations,
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
