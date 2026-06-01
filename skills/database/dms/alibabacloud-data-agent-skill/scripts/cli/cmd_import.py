"""Import subcommand - Add DMS database tables to Data Agent Data Center.

Author: Tinker
Created: 2026-03-05
"""

import argparse
import sys

from data_agent import DataAgentConfig, DataAgentClient


def _confirm_import(args: argparse.Namespace) -> bool:
    """Confirm the high-risk import operation before calling the API."""
    if getattr(args, "yes", False):
        return True

    if not sys.stdin.isatty():
        print("Error: Import requires explicit confirmation. Re-run with --yes in non-interactive mode.", file=sys.stderr)
        return False

    answer = input("Confirm import these tables to Data Center? Type 'yes' to continue: ")
    if answer.strip().lower() in {"yes", "y"}:
        return True

    print("Import cancelled.")
    return False


def cmd_import(args: argparse.Namespace) -> None:
    """Handle import subcommand for adding DMS tables to Data Center."""
    # Validate required parameters
    missing = []
    for attr, name in [
        ("dms_instance_id", "--dms-instance-id"),
        ("dms_db_id", "--dms-db-id"),
        ("instance_name", "--instance-name"),
        ("db_name", "--db-name"),
        ("tables", "--tables"),
    ]:
        if not getattr(args, attr, None):
            missing.append(name)
    if missing:
        print(f"Error: Missing required parameters: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Parse tables
    table_list = [t.strip() for t in args.tables.split(",") if t.strip()]
    if not table_list:
        print("Error: --tables must contain at least one table name", file=sys.stderr)
        sys.exit(1)

    print("Adding database tables to Data Center...")
    print(f"  Region: {args.region}")
    print(f"  Instance: {args.instance_name}")
    print(f"  Database: {args.db_name}")
    print(f"  DMS Instance ID: {args.dms_instance_id}")
    print(f"  DMS DB ID: {args.dms_db_id}")
    print(f"  DB Type: {getattr(args, 'engine', 'mysql')}")
    print(f"  Tables: {', '.join(table_list)}")
    print("-" * 60)

    if not _confirm_import(args):
        sys.exit(1)

    # Initialize client only after the operation is confirmed.
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)

    try:
        result = client.add_data_center_table(
            instance_name=args.instance_name,
            database_name=args.db_name,
            dms_instance_id=args.dms_instance_id,
            dms_db_id=args.dms_db_id,
            table_name_list=table_list,
            db_type=getattr(args, "engine", "mysql"),
            region_id=args.region,
        )
        print("✓ Successfully added to Data Center")
        print(f"  Response: {result.get('Data', result)}")
    except Exception as e:
        print(f"✗ Failed to add to Data Center: {e}", file=sys.stderr)
        sys.exit(1)
