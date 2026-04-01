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
    data = resp.get("Data") or resp.get("data", [])
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("List") or data.get("DataList") or data.get("Content") or []
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
    db_id  = getattr(args, "db_id", None)
    sep    = "-" * 60

    print(f"Region: {config.region}")

    # -- list databases --
    if db_id is None:
        print("Fetching databases...")
        try:
            resp = client.list_databases(search_key=search)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        items = _extract_list(resp)
        if not items:
            print("No databases found.")
            return

        # Separate real DB connections from file-based data sources
        # Handle both PascalCase and camelCase keys from API response
        def _get_import_type(d):
            return d.get("ImportType") or d.get("importType", "")

        real_dbs  = [d for d in items if _get_import_type(d) in ("RDS", "DMS")]
        file_dbs  = [d for d in items if _get_import_type(d) == "FILE"]

        # -- Real databases (RDS / DMS) --
        print(f"\n{'=' * 60}")
        print(f"  Database Connections ({len(real_dbs)})  [ImportType: RDS/DMS]")
        print(f"{'=' * 60}")
        if real_dbs:
            for db in real_dbs:
                db_name         = _get_field(db, "DatabaseName", "databaseName")
                db_type         = _get_field(db, "DbType", "dbType", default="").lower()
                import_type     = _get_field(db, "ImportType", "importType")
                dms_db_id       = _get_field(db, "DmsDbId", "dmsDbId")
                dms_instance_id = _get_field(db, "DmsInstanceId", "dmsInstanceId")
                instance_name   = _get_field(db, "InstanceName", "instanceName")
                db_desc         = _get_field(db, "DatabaseDesc", "databaseDesc")
                agent_db_id     = _get_field(db, "DbId", "dbId")

                print(f"\n  {db_name}  [{db_type}]  ({import_type})")
                if db_desc:
                    print(f"    Desc          : {db_desc}")
                print(f"    AgentDbId     : {agent_db_id}")
                print(f"    DmsDbId       : {dms_db_id}")
                print(f"    DmsInstanceId : {dms_instance_id}")
                print(f"    InstanceName  : {instance_name}")
        else:
            print("  (none)")

        # -- File-based data sources --
        print(f"\n{'=' * 60}")
        print(f"  File Data Sources ({len(file_dbs)})  [ImportType: FILE]")
        print(f"{'=' * 60}")
        if file_dbs:
            for db in file_dbs:
                db_name     = _get_field(db, "DatabaseName", "databaseName")
                db_type     = _get_field(db, "DbType", "dbType", default="").lower()
                agent_db_id = _get_field(db, "DbId", "dbId")
                db_desc     = _get_field(db, "DatabaseDesc", "databaseDesc")
                internal    = _get_field(db, "IsInternal", "isInternal", default="N")
                label       = "[sample]" if internal == "Y" else ""
                print(f"  {db_name:<45}  [{db_type}]  {label}  DbId={agent_db_id}")
        else:
            print("  (none)")
        print()
        return

    # -- list tables for a specific db_id --
    print(f"Fetching tables for DbId={db_id}...")

    # Fetch all databases first to get InstanceName + DatabaseName (required by API)
    db_meta: dict = {}
    try:
        db_resp = client.list_databases()
        all_dbs = _extract_list(db_resp)
        for db in all_dbs:
            if str(db.get("DbId", "")) == str(db_id):
                db_meta = db
                break
    except Exception:
        pass

    if not db_meta:
        print(f"Error: DbId '{db_id}' not found in database list.", file=sys.stderr)
        sys.exit(1)

    inst_name = db_meta.get("InstanceName", "")
    db_name_q = db_meta.get("DatabaseName", "")

    try:
        resp = client.list_tables(inst_name, db_name_q)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    items = _extract_list(resp)
    if not items:
        print("No tables found.")
        return

    table_names = [t.get("TableName", t.get("Name", "")) for t in items]
    table_ids   = [t.get("TableId", t.get("Id", "")) for t in items]

    db_name         = db_meta.get("DatabaseName", "")
    db_type         = db_meta.get("DbType", "").lower()
    dms_instance_id = db_meta.get("DmsInstanceId", "")
    dms_db_id       = db_meta.get("DmsDbId", "")
    instance_name   = db_meta.get("InstanceName", "")

    print(f"\n{'=' * 60}")
    print(f"  Database  : {db_name}  [{db_type}]")
    print(f"  AgentDbId : {db_id}")
    print(f"  DmsDbId   : {dms_db_id}")
    print(f"  Instance  : {instance_name}  (DmsInstanceId={dms_instance_id})")
    print(f"  Tables    : {len(items)}")
    print(f"{'=' * 60}")
    for name, tid in zip(table_names, table_ids):
        print(f"  {name:<30}  {tid}")
    print()

    # Print ready-to-use CLI command
    tables_arg    = ",".join(table_names)
    table_ids_arg = ",".join(table_ids)
    print(sep)
    print("  Ready-to-use db command:")
    print(sep)
    print(f"  python3 data_agent_cli.py db \\")
    print(f"    --dms-instance-id {dms_instance_id} \\")
    print(f"    --dms-db-id {dms_db_id} \\")
    print(f"    --instance-name {instance_name} \\")
    print(f"    --db-name {db_name} \\")
    print(f"    --engine {db_type} \\")
    print(f"    --tables {tables_arg} \\")
    print(f"    --session-mode ASK_DATA \\")
    print(f"    -q \"your question here\"")
    print(sep)
