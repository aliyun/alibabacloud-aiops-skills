"""Workspace management subcommand (workspace).

Author: Tinker
Created: 2026-04-16
"""

import argparse
import sys
from datetime import datetime

from data_agent import DataAgentConfig, DataAgentClient


def _get_field(obj: dict, *names: str, default=""):
    """Get a field value trying multiple possible key names."""
    for name in names:
        if name in obj:
            return obj[name]
    return default


def _format_timestamp(ts) -> str:
    """Format a unix timestamp (seconds) to readable date string."""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError, OSError):
        return str(ts)


def cmd_workspace(args: argparse.Namespace) -> None:
    """List Data Agent workspaces."""
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)

    workspace_type = getattr(args, "workspace_type", "MY")
    search_name = getattr(args, "search", None)
    page_number = getattr(args, "page_number", 1)
    page_size = getattr(args, "page_size", 50)

    print(f"Region: {config.region}")
    print(f"Fetching workspaces (type={workspace_type})...")

    try:
        resp = client.list_workspaces(
            workspace_type=workspace_type,
            workspace_name=search_name,
            page_number=page_number,
            page_size=page_size,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract workspace list from response
    # Response structure: { data: { content: [...], totalElements, totalPages, ... } }
    data = resp.get("data") or resp.get("Data") or {}
    items = []
    if isinstance(data, dict):
        items = data.get("content") or data.get("Content") or []
    elif isinstance(data, list):
        items = data

    total_elements = 0
    total_pages = 0
    if isinstance(data, dict):
        total_elements = data.get("totalElements") or data.get("TotalElements") or len(items)
        total_pages = data.get("totalPages") or data.get("TotalPages") or 1

    if not items:
        print("No workspaces found.")
        return

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  Workspaces ({len(items)})  [Type: {workspace_type}]  Total: {total_elements}")
    print(f"{sep}")

    for ws in items:
        ws_name = _get_field(ws, "workspaceName", "WorkspaceName")
        ws_id = _get_field(ws, "workspaceId", "WorkspaceId")
        ws_status = _get_field(ws, "workspaceStatus", "WorkspaceStatus", default="unknown")
        role = _get_field(ws, "roleName", "RoleName")
        creator = _get_field(ws, "creator", "Creator")
        desc = _get_field(ws, "description", "Description")
        members = _get_field(ws, "totalMember", "TotalMember", default=0)
        create_time = _get_field(ws, "createTime", "CreateTime")
        modify_time = _get_field(ws, "modifyTime", "ModifyTime")

        print(f"\n  {ws_name}  [{ws_status}]  ({role})")
        print(f"    WorkspaceId   : {ws_id}")
        if creator:
            print(f"    Creator       : {creator}")
        print(f"    Members       : {members}")
        if desc:
            print(f"    Description   : {desc}")
        if create_time:
            print(f"    Created       : {_format_timestamp(create_time)}")
        if modify_time:
            print(f"    Modified      : {_format_timestamp(modify_time)}")

    if total_pages > 1:
        print(f"\n  Page {page_number}/{total_pages} (use --page-number to navigate)")

    # Print usage hint
    print(f"\n{'-' * 60}")
    print("  To create a session in a workspace:")
    print(f"{'-' * 60}")
    print("  python3 scripts/data_agent_cli.py db \\")
    print("    --workspace-id <WorkspaceId> \\")
    print("    --dms-instance-id <ID> --dms-db-id <ID> \\")
    print("    --instance-name <NAME> --db-name <DB> \\")
    print('    --tables "t1,t2" -q "your question"')
    print(f"{'-' * 60}")
    print()
