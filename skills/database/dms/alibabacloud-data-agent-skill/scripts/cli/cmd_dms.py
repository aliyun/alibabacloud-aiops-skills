"""DMS tools subcommand (dms).

Author: Tinker
Created: 2026-03-05
"""

import argparse
import sys

from data_agent import DataAgentConfig, DmsMcpTools


def cmd_dms(args: argparse.Namespace) -> None:
    """Handle dms subcommand for DMS tools."""
    config = DataAgentConfig.from_env()
    mcp_tools = DmsMcpTools(config)

    tool = getattr(args, "tool", None)

    if tool == "list-instances":
        _list_instances(mcp_tools, args)
    elif tool == "search-database":
        _search_database(mcp_tools, args)
    elif tool == "list-tables":
        _list_tables(mcp_tools, args)
    else:
        print("Error: Unknown tool. Use 'list-instances', 'search-database', or 'list-tables'.", file=sys.stderr)
        sys.exit(1)


def _list_instances(mcp_tools: DmsMcpTools, args: argparse.Namespace) -> None:
    """List DMS instances using MCP tool."""
    search_key = getattr(args, "search", None)
    db_type = getattr(args, "db_type", None)
    env_type = getattr(args, "env_type", None)
    page_number = getattr(args, "page_number", 1)
    page_size = getattr(args, "page_size", 50)

    print(f"Region: {mcp_tools._config.region}")
    print("Fetching instances from DMS...")
    print("-" * 60)

    try:
        result = mcp_tools.list_instances(
            search_key=search_key,
            db_type=db_type,
            env_type=env_type,
            page_number=page_number,
            page_size=page_size,
        )

        if not result.items:
            print("No instances found.")
            return

        print(f"Page {result.page_number}/{result.total_pages} (Total: {result.total_count} instances)\n")

        for inst in result.items:
            print(f"  {inst.instance_alias}  [{inst.instance_type}]")
            print(f"    Instance ID   : {inst.instance_id}")
            print(f"    Host:Port     : {inst.host}:{inst.port}")
            print(f"    State         : {inst.state}")
            print(f"    Env Type      : {inst.env_type}")
            print(f"    Source        : {inst.instance_source}")
            if inst.instance_resource_id:
                print(f"    Resource ID   : {inst.instance_resource_id}")
            print()

        # Show pagination hint
        print("-" * 60)
        if result.has_next:
            print(f"📄 Next page: --page-number {result.page_number + 1}")
        else:
            print("📄 This is the last page.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _search_database(mcp_tools: DmsMcpTools, args: argparse.Namespace) -> None:
    """Search databases by schema name."""
    search_key = getattr(args, "search_key", None)
    page_number = getattr(args, "page_number", 1)
    page_size = getattr(args, "page_size", 200)

    if not search_key:
        print("Error: --search-key is required for search-database tool.", file=sys.stderr)
        sys.exit(1)

    print(f"Region: {mcp_tools._config.region}")
    print(f"Search Key: {search_key}")
    print("Searching databases in DMS...")
    print("-" * 60)

    try:
        databases = mcp_tools.search_database(
            search_key=search_key,
            page_number=page_number,
            page_size=page_size,
        )

        if not databases:
            print("No databases found.")
            print("\nTroubleshooting tips:")
            print("  1. The database may not be registered in DMS")
            print("  2. The search_key is case-sensitive, try different cases")
            print("  3. Try using 'dms list-instances' to see available instances first")
            return

        print(f"Found {len(databases)} database(s):\n")

        for db in databases:
            print(f"  {db.schema_name}  [{db.db_type}]")
            print(f"    Database ID   : {db.database_id}")
            print(f"    Host:Port     : {db.host}:{db.port}")
            print(f"    Instance      : {db.instance_alias} (ID: {db.instance_id})")
            print(f"    Env Type      : {db.env_type}")
            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _list_tables(mcp_tools: DmsMcpTools, args: argparse.Namespace) -> None:
    """List tables in a database."""
    database_id = getattr(args, "database_id", None)
    search_name = getattr(args, "search_name", None)
    page_number = getattr(args, "page_number", 1)
    page_size = getattr(args, "page_size", 200)

    if not database_id:
        print("Error: --database-id is required for list-tables tool.", file=sys.stderr)
        sys.exit(1)

    print(f"Region: {mcp_tools._config.region}")
    print(f"Database ID: {database_id}")
    if search_name:
        print(f"Search Name: {search_name}")
    print("Fetching tables from DMS...")
    print("-" * 60)

    try:
        tables = mcp_tools.list_tables(
            database_id=database_id,
            search_name=search_name,
            page_number=page_number,
            page_size=page_size,
        )

        if not tables:
            print("No tables found.")
            return

        print(f"Found {len(tables)} table(s):\n")

        for table in tables:
            print(f"  {table.table_name}")
            print(f"    Table ID      : {table.table_id}")
            print(f"    Table GUID    : {table.table_guid}")
            print(f"    Schema        : {table.schema_name}")
            if table.engine:
                print(f"    Engine        : {table.engine}")
            if table.table_comment:
                print(f"    Comment       : {table.table_comment}")
            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
