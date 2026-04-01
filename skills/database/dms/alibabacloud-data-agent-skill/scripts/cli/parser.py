"""Argument parsing and CLI entry point.

Author: Tinker
Created: 2026-03-04
"""

import argparse
import os
import sys

from cli.cmd_db import cmd_db
from cli.cmd_ls import cmd_ls
from cli.cmd_file import cmd_file
from cli.cmd_attach import cmd_attach
from cli.cmd_dms import cmd_dms
from cli.cmd_import import cmd_import
from cli.cmd_reports import cmd_reports


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="data_agent_cli",
        description="Data Agent Unified CLI - Database Query/Analysis & File Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Database Mode Description
  ASK_DATA: Quick query mode with SQL execution + natural language response
  ANALYSIS: Deep analysis mode with planning, multi-step reasoning, and report generation

Examples:
  # -- Database ASK_DATA (default) --
  python data_agent_cli.py db \\
      --dms-instance-id <DMS_INSTANCE_ID> --dms-db-id <DMS_DB_ID> \\
      --instance-name <INSTANCE_NAME> --db-name chinook \\
      --tables "album,artist,customer" \\
      -q "Who has the highest sales?"

  # -- Database ANALYSIS mode --
  python data_agent_cli.py db --session-mode ANALYSIS \\
      --dms-instance-id <DMS_INSTANCE_ID> --dms-db-id <DMS_DB_ID> \\
      --instance-name <INSTANCE_NAME> --db-name chinook \\
      --tables "album,artist,customer" \\
      -q "Analyze sales trends and generate report"

  # -- File Analysis --
  python data_agent_cli.py file /path/to/data.csv
  python data_agent_cli.py file /path/to/data.csv -q "Analyze sales trends"
""",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # -- db subcommand --
    db_parser = subparsers.add_parser(
        "db",
        help="Database query/analysis (supports ASK_DATA and ANALYSIS modes)",
        description="""Connect to DMS database for natural language queries or data analysis.

Mode Description:
  ASK_DATA (default): Quick SQL query + natural language response
  ANALYSIS          : Deep analysis, multi-step reasoning, report generation""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Data source parameters
    ds_group = db_parser.add_argument_group("Data Source Parameters (required)")
    ds_group.add_argument(
        "--dms-instance-id",
        type=int,
        metavar="INT",
        help="DMS Instance ID (e.g., 1234567)",
    )
    ds_group.add_argument(
        "--dms-db-id",
        type=int,
        metavar="INT",
        help="DMS Database ID (e.g., 12345678)",
    )
    ds_group.add_argument(
        "--instance-name",
        metavar="STR",
        help="RDS instance name (e.g., rm-xxxxxx.mysql.rds.aliyuncs.com)",
    )
    ds_group.add_argument(
        "--db-name",
        metavar="STR",
        help="Database name (e.g., chinook)",
    )
    ds_group.add_argument(
        "--tables",
        metavar="T1,T2,...",
        help="Table names to include (comma-separated, e.g., album,artist,track)",
    )
    ds_group.add_argument(
        "--table-ids",
        metavar="ID1,ID2,...",
        help="Data Center table IDs (comma-separated)",
    )
    ds_group.add_argument(
        "--engine",
        default="mysql",
        metavar="ENGINE",
        help="Database engine type (default: mysql)",
    )
    # Default region from env, fallback to cn-hangzhou
    _default_region = os.environ.get("DATA_AGENT_REGION", "cn-hangzhou")
    ds_group.add_argument(
        "--region",
        default=_default_region,
        metavar="REGION",
        help=f"Region ID (default: {_default_region})",
    )

    # Query
    db_parser.add_argument(
        "--query", "-q",
        metavar="QUERY",
        help="Execute a single natural language query (runs preset queries if omitted)",
    )

    db_parser.add_argument(
        "--async-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run asynchronously in background (default: True). Use --no-async-run for synchronous mode.",
    )

    # Session options
    db_parser.add_argument(
        "--session-mode",
        default="ASK_DATA",
        choices=["ASK_DATA", "ANALYSIS", "INSIGHT"],
        metavar="MODE",
        help="Session mode: ASK_DATA (default) | ANALYSIS | INSIGHT",
    )
    db_parser.add_argument(
        "--output",
        choices=["summary", "detail", "raw"],
        default="summary",
        metavar="MODE",
        help="Output verbosity: summary (default, conclusion only) | detail (full process) | raw (every SSE event)",
    )
    db_parser.add_argument(
        "--enable-search",
        action="store_true",
        help="Enable search capability in the session (default: False)",
    )

    db_parser.set_defaults(func=cmd_db)

    # -- file subcommand --
    file_parser = subparsers.add_parser(
        "file",
        help="File upload and analysis (CSV / Excel / JSON)",
        description="Upload local data files for intelligent analysis via Data Agent.",
    )

    # Create a mutually exclusive group for file source
    file_source_group = file_parser.add_mutually_exclusive_group(required=True)

    file_source_group.add_argument(
        "file_path",
        nargs='?',  # Make it optional since we have --file-id
        metavar="FILE",
        help="Local file path to upload for analysis (supports: .csv / .xlsx / .xls / .json / .txt)",
    )

    file_source_group.add_argument(
        "--file-id",
        metavar="FILE_ID",
        help="Data Center file ID to analyze directly (e.g., f-8941bx83xy9513xvpewrha01m)",
    )

    # Query
    file_parser.add_argument(
        "--query", "-q",
        metavar="QUERY",
        help="Execute a single custom query (uses preset questions if not specified)",
    )

    file_parser.add_argument(
        "--async-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run asynchronously in background (default: True). Use --no-async-run for synchronous mode.",
    )

    file_parser.add_argument(
        "--list-generated-files",
        action="store_true",
        help="List agent-generated reports/charts after analysis",
    )
    file_parser.add_argument(
        "--session-mode",
        default="ANALYSIS",
        choices=["ASK_DATA", "ANALYSIS", "INSIGHT"],
        metavar="MODE",
        help="Session mode: ASK_DATA | ANALYSIS (default) | INSIGHT",
    )
    file_parser.add_argument(
        "--output",
        default="summary",
        choices=["summary", "detail", "raw"],
        metavar="MODE",
        help="Output mode: summary (default, conclusion only) | detail (full process) | raw (all SSE events)",
    )
    file_parser.add_argument(
        "--enable-search",
        action="store_true",
        help="Enable search capability in the session (default: False)",
    )

    file_parser.set_defaults(func=cmd_file)

    # -- attach subcommand --
    attach_parser = subparsers.add_parser(
        "attach",
        help="Connect to an existing session to continue analysis or confirm plan",
        description=(
            "Attach to an existing Data Agent session. Use this to:\n"
            "  - Continue an interrupted ANALYSIS session\n"
            "  - Confirm an execution plan after WAIT_INPUT\n"
            "  - Ask follow-up questions in an existing session\n\n"
            "Examples:\n"
            "  python3 scripts/data_agent_cli.py attach --session-id <ID> -q '\u786e\u8ba4\u6267\u884c\u8ba1\u5212'\n"
            "  python3 scripts/data_agent_cli.py attach --session-id <ID>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    attach_parser.add_argument(
        "--session-id",
        required=True,
        metavar="SESSION_ID",
        help="Session ID to connect to",
    )
    attach_parser.add_argument(
        "--output",
        choices=["summary", "detail", "raw"],
        default="summary",
        metavar="MODE",
        help="Output verbosity: summary (default, conclusion only) | detail (full process) | raw (every SSE event)",
    )
    attach_parser.add_argument(
        "--checkpoint",
        type=int,
        metavar="CHECKPOINT",
        help="Specific checkpoint to resume from (e.g. 52). Resumes from breakpoint.",
    )
    attach_parser.add_argument(
        "--from-start",
        action="store_true",
        help="Replay from checkpoint=0 (full history) instead of watching live stream",
    )
    attach_parser.add_argument(
        "--query", "-q",
        metavar="QUERY",
        help="Execute a single query (e.g., '\u786e\u8ba4\u6267\u884c\u8ba1\u5212' or '\u7ee7\u7eed\u5206\u6790')",
    )
    attach_parser.add_argument(
        "--async-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run asynchronously in background (default: True). Use --no-async-run for synchronous mode.",
    )
    attach_parser.set_defaults(func=cmd_attach)

    # -- ls subcommand --
    ls_parser = subparsers.add_parser(
        "ls",
        help="List DMS databases and tables with analysis-ready parameters",
        description=(
            "List databases registered in DMS Data Center and print the\n"
            "key IDs and parameters needed for the db subcommand.\n\n"
            "Examples:\n"
            "  python3 scripts/data_agent_cli.py ls                  # all databases\n"
            "  python3 scripts/data_agent_cli.py ls --search chinook # filter by name\n"
            "  python3 scripts/data_agent_cli.py ls --db-id <DB_ID> # tables in DB"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ls_parser.add_argument(
        "--search", "-s",
        metavar="KEYWORD",
        help="Filter databases by keyword (database or instance name)",
    )
    ls_parser.add_argument(
        "--db-id",
        metavar="DB_ID",
        help="DbId of a specific database; lists its tables and prints the ready-to-use db command",
    )
    ls_parser.set_defaults(func=cmd_ls)

    # -- dms subcommand --
    dms_parser = subparsers.add_parser(
        "dms",
        help="DMS tools integration (list-instances, search-database, list-tables)",
        description="""Access DMS Server tools for instance, database and table management.

Tools:
  list-instances    Search and list database instances in DMS
  search-database   Search databases by schema name
  list-tables       List tables in a database

Examples:
  python3 scripts/data_agent_cli.py dms list-instances
  python3 scripts/data_agent_cli.py dms list-instances --search mysql --db-type mysql
  python3 scripts/data_agent_cli.py dms search-database --search-key mydb
  python3 scripts/data_agent_cli.py dms list-tables --database-id <DATABASE_ID>
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    dms_parser.add_argument(
        "tool",
        choices=["list-instances", "search-database", "list-tables"],
        help="DMS tool to execute",
    )
    # list-instances options
    dms_parser.add_argument(
        "--search",
        metavar="KEYWORD",
        help="Search key for instances (host, alias, etc.)",
    )
    dms_parser.add_argument(
        "--db-type",
        metavar="TYPE",
        help="Database type filter (e.g., mysql, polardb, oracle)",
    )
    dms_parser.add_argument(
        "--env-type",
        metavar="ENV",
        help="Environment type filter (e.g., product, dev, test)",
    )
    # search-database options
    dms_parser.add_argument(
        "--search-key",
        metavar="KEYWORD",
        help="Schema name search keyword for search-database",
    )
    dms_parser.add_argument(
        "--page-number",
        type=int,
        default=1,
        metavar="PAGE",
        help="Page number for pagination (default: 1)",
    )
    dms_parser.add_argument(
        "--page-size",
        type=int,
        default=200,
        metavar="SIZE",
        help="Page size for pagination (default: 200, max: 1000)",
    )
    # list-tables options
    dms_parser.add_argument(
        "--database-id",
        metavar="DB_ID",
        help="Database ID for list-tables",
    )
    dms_parser.add_argument(
        "--search-name",
        metavar="NAME",
        help="Table name search keyword for list-tables",
    )
    dms_parser.set_defaults(func=cmd_dms)

    # -- import subcommand --
    import_parser = subparsers.add_parser(
        "import",
        help="Import DMS database tables to Data Agent Data Center",
        description="""Add DMS database tables to Data Agent Data Center.

This command imports tables from DMS into Data Agent's Data Center,
making them available for analysis via the 'db' subcommand.

Examples:
  python3 scripts/data_agent_cli.py import \\
    --dms-instance-id <DMS_INSTANCE_ID> \\
    --dms-db-id <DMS_DB_ID> \\
    --instance-name <INSTANCE_NAME> \\
    --db-name employees \\
    --tables "departments,employees,salaries"
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Data source parameters (required)
    import_group = import_parser.add_argument_group("Data Source Parameters (required)")
    import_group.add_argument(
        "--dms-instance-id",
        type=int,
        metavar="INT",
        help="DMS Instance ID (e.g., 1234567)",
    )
    import_group.add_argument(
        "--dms-db-id",
        type=int,
        metavar="INT",
        help="DMS Database ID (e.g., 12345678)",
    )
    import_group.add_argument(
        "--instance-name",
        metavar="STR",
        help="RDS instance name (e.g., rm-xxxxxx.mysql.rds.aliyuncs.com)",
    )
    import_group.add_argument(
        "--db-name",
        metavar="STR",
        help="Database name (e.g., employees)",
    )
    import_group.add_argument(
        "--tables",
        metavar="T1,T2,...",
        help="Table names to import (comma-separated, e.g., departments,employees,salaries)",
    )
    import_group.add_argument(
        "--engine",
        default="mysql",
        metavar="ENGINE",
        help="Database engine type (default: mysql)",
    )
    _default_region = os.environ.get("DATA_AGENT_REGION", "cn-hangzhou")
    import_group.add_argument(
        "--region",
        default=_default_region,
        metavar="REGION",
        help=f"Region ID (default: {_default_region})",
    )

    import_parser.set_defaults(func=cmd_import)

    # -- reports subcommand --
    reports_parser = subparsers.add_parser(
        "reports",
        help="List and download agent-generated files (reports, charts, data files)",
        description="""List and download files generated during an ANALYSIS or INSIGHT session.

Examples:
  python3 scripts/data_agent_cli.py reports --session-id <ID>
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    reports_parser.add_argument(
        "--session-id",
        required=True,
        metavar="SESSION_ID",
        help="Session ID to fetch reports for",
    )
    # The download parameter is no longer an optional flag;
    # reports command now downloads files automatically.
    # We keep the argument parser clean by removing it.
    reports_parser.set_defaults(func=cmd_reports)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
