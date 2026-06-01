"""List databases and tables (ls subcommand).

Author: Tinker
Created: 2026-03-04
"""

import argparse
import sys

from data_agent import DataAgentConfig, DataAgentClient


def _extract_list(resp: dict) -> list:
    """Extract a list from an API response regardless of nesting style.

    Handles ``{Data: [...]}`` and ``{Data: {List/DataList/Content: [...]}}``.
    Also handles lowercase ``{data: {...}}`` format from some API responses.
    """
    # Try uppercase "Data" first, then lowercase "data"
    data = resp.get("Data") or resp.get("data") or []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return (
            data.get("MetaEntities")
            or data.get("metaEntities")
            or data.get("List")
            or data.get("DataList")
            or data.get("Content")
            or []
        )
    return []


def _get_field(obj: dict, *names: str, default=""):
    """Get a field value trying multiple possible key names (case-insensitive).

    Args:
        obj: The dictionary to search
        *names: Possible field names to try (e.g., "DatabaseName", "databaseName")
        default: Default value if none found
    """
    for name in names:
        if name in obj:
            return obj[name]
    return default


def cmd_ls(args: argparse.Namespace) -> None:
    """List DMS databases and (optionally) their tables."""
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)

    search = getattr(args, "search", None)
    db_id = getattr(args, "db_id", None)
    workspace_id_arg = getattr(args, "workspace_id", None)
    sep = "-" * 60

    # Resolve workspace
    workspace_id = client._resolve_workspace_id(workspace_id_arg)
    workspace_source = client._workspace_source or "unknown"

    print(f"Region: {config.region}")
    print(f"Workspace: {workspace_id} (source: {workspace_source})")

    # -- list databases --
    if db_id is None:
        print("Fetching databases...")
        try:
            resp = client.list_databases(workspace_id=workspace_id_arg, search_key=search)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        items = _extract_list(resp)
        if not items:
            print("No databases found.")
            return

        print(f"\n{'=' * 60}")
        print(f"  Databases ({len(items)})")
        print(f"{'=' * 60}")
        for db in items:
            attrs = db.get("MetaEntityAttrs") or db.get("metaEntityAttrs") or {}
            db_id_val = _get_field(attrs, "dbId", "DbId", default="")
            schema_name = _get_field(attrs, "schemaName", "SchemaName", default="")
            catalog_name = _get_field(attrs, "catalogName", "CatalogName", default="")
            db_type = _get_field(attrs, "dbType", "DbType", default="")
            instance_id = _get_field(attrs, "instanceId", "InstanceId", default="")
            instance_resource_id = _get_field(attrs, "instanceResourceId", "InstanceResourceId", default="")

            print(f"  {schema_name} [{db_type}] dbId={db_id_val} instanceId={instance_id} instanceResourceId={instance_resource_id} catalogName={catalog_name}")
        print()
        return

    # -- list tables for a specific db_id --
    print(f"Fetching tables for AgentDbId={db_id}...")

    try:
        resp = client.list_tables(agent_db_id=db_id, workspace_id=workspace_id_arg)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    items = _extract_list(resp)
    if not items:
        print("No tables found.")
        return

    # Extract table names from MetaEntityAttrs
    table_names = []
    for t in items:
        attrs = t.get("MetaEntityAttrs") or t.get("metaEntityAttrs") or {}
        name = _get_field(attrs, "tableName", "TableName", "Name", default="")
        if not name:
            # Fallback: try top-level keys
            name = _get_field(t, "TableName", "Name", default="")
        table_names.append(name)

    # Also fetch db metadata from the databases list for display
    schema_name = ""
    db_type = ""
    instance_id = ""
    try:
        db_resp = client.list_databases(workspace_id=workspace_id_arg)
        all_dbs = _extract_list(db_resp)
        for db in all_dbs:
            attrs = db.get("MetaEntityAttrs") or db.get("metaEntityAttrs") or {}
            if str(_get_field(attrs, "dbId", "DbId", default="")) == str(db_id):
                schema_name = _get_field(attrs, "schemaName", "SchemaName", default="")
                db_type = _get_field(attrs, "dbType", "DbType", default="")
                instance_id = _get_field(attrs, "instanceId", "InstanceId", default="")
                break
    except Exception:
        pass

    print(f"\n{'=' * 60}")
    print(f"  Database  : {schema_name}  [{db_type}]")
    print(f"  AgentDbId : {db_id}")
    print(f"  Tables    : {len(items)}")
    print(f"{'=' * 60}")
    for name in table_names:
        print(f"  {name}")
    print()

    # Print ready-to-use CLI command
    tables_arg = ",".join(table_names)
    print(sep)
    print("  Ready-to-use db command:")
    print(sep)
    print(f"  python3 data_agent_cli.py db \\")
    print(f"    --dms-instance-id {instance_id} \\")
    print(f"    --dms-db-id {db_id} \\")
    print(f"    --db-name {schema_name} \\")
    print(f"    --tables {tables_arg} \\")
    print(f"    --workspace-id {workspace_id} \\")
    print(f"    --session-mode ASK_DATA \\")
    print(f"    -q \"your question here\"")
    print(sep)
