#!/usr/bin/env python3
"""
Manage memory projects: create / list / get / update.

A memory project provides second-level memory isolation. The project_id is
used in memory add and search operations.

Usage:
    # 创建项目
    python3 scripts/manage_memory_project.py create --name "观察项目" \
        [--plan-version pro|lite] \
        [--instruction-type default|custom] [--custom-instruction <text>] \
        [--expired-in-days 30] [--auto-refresh true|false]

    # 分页查询项目列表
    python3 scripts/manage_memory_project.py list [--page-num 1] [--page-size 10]

    # 查询项目详情
    python3 scripts/manage_memory_project.py get --project-id <id>

    # 更新项目（至少传一个可更新字段）
    python3 scripts/manage_memory_project.py update --project-id <id> [--name <name>] \
        [--instruction-type custom] [--custom-instruction <text>] [--expired-in-days 60] \
        [--auto-refresh true|false] [--plan-version pro|lite]
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def _str2bool(value):
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"Expected true/false, got: {value}")


def main():
    parser = argparse.ArgumentParser(description="Manage memory projects (create/list/get/update).")
    subparsers = parser.add_subparsers(dest="action", required=True)

    create_parser = subparsers.add_parser("create", help="Create a memory project.")
    create_parser.add_argument("--name", required=True, help="Project name (max 32 chars).")
    create_parser.add_argument("--plan-version", choices=["pro", "lite"],
                               help="Billing plan (defaults to pro server-side).")
    create_parser.add_argument("--instruction-type", choices=["default", "custom"],
                               help="Extraction instruction type.")
    create_parser.add_argument("--custom-instruction", help="Custom extraction instruction content.")
    create_parser.add_argument("--expired-in-days", type=int,
                               help="Memory expiration in days: 1-180, or -1 for never expiring.")
    create_parser.add_argument("--auto-refresh", type=_str2bool,
                               help="Whether accessing a memory refreshes its expiration (true/false).")
    create_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    list_parser = subparsers.add_parser("list", help="List memory projects with pagination.")
    list_parser.add_argument("--page-num", type=int, help="Page number (starts at 1).")
    list_parser.add_argument("--page-size", type=int, help="Items per page.")
    list_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    get_parser = subparsers.add_parser("get", help="Get the detail of a memory project.")
    get_parser.add_argument("--project-id", required=True, help="Memory project ID.")
    get_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    update_parser = subparsers.add_parser("update", help="Update a memory project.")
    update_parser.add_argument("--project-id", required=True, help="Memory project ID.")
    update_parser.add_argument("--name", help="New project name (max 32 chars).")
    update_parser.add_argument("--instruction-type", choices=["default", "custom"],
                               help="Extraction instruction type.")
    update_parser.add_argument("--custom-instruction", help="Custom extraction instruction content.")
    update_parser.add_argument("--expired-in-days", type=int,
                               help="Memory expiration in days: 1-180, or -1 for never expiring.")
    update_parser.add_argument("--auto-refresh", type=_str2bool,
                               help="Whether accessing a memory refreshes its expiration (true/false).")
    update_parser.add_argument("--plan-version", choices=["pro", "lite"], help="Billing plan.")
    update_parser.add_argument("--memory-library-id", help="Memory library ID (optional).")

    args = parser.parse_args()

    try:
        client = MemoryClient()
        if args.action == "create":
            result = client.create_memory_project(
                name=args.name,
                plan_version=args.plan_version,
                instruction_type=args.instruction_type,
                custom_instruction=args.custom_instruction,
                expired_in_days=args.expired_in_days,
                auto_refresh=args.auto_refresh,
                memory_library_id=args.memory_library_id,
            )
        elif args.action == "list":
            result = client.list_memory_projects(
                page_num=args.page_num,
                page_size=args.page_size,
                memory_library_id=args.memory_library_id,
            )
        elif args.action == "get":
            result = client.get_memory_project(
                project_id=args.project_id,
                memory_library_id=args.memory_library_id,
            )
        else:  # update
            result = client.update_memory_project(
                project_id=args.project_id,
                name=args.name,
                instruction_type=args.instruction_type,
                custom_instruction=args.custom_instruction,
                expired_in_days=args.expired_in_days,
                auto_refresh=args.auto_refresh,
                plan_version=args.plan_version,
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
