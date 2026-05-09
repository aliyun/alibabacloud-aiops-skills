#!/usr/bin/env python3
"""
Flink Ververica CLI – manage Flink jobs lifecycle (API 2022-07-18).

Single entry-point that registers subcommands from 5 workflow modules.
"""

import argparse
import os
import sys

# Ensure scripts/ is on sys.path so workflow modules can import client.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        prog="flink-ververica",
        description="Flink Ververica CLI – manage Flink jobs lifecycle (API 2022-07-18)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflows:
  SQL Development (W1)   create_folder, create_draft, validate_sql, deploy_draft ...
  Job Operations  (W2)   list_deployments, start_job, stop_job, diagnose_job ...
  Session Cluster (W3)   create_session_cluster, start_session_cluster ...
  Dev Resources   (W4)   get_catalogs, get_databases, get_tables, execute_sql ...
  Workspace Admin (W5)   create_member, create_variable, create_deploy_target ...

Authentication:
  Uses Alibaba Cloud default credential chain (RAM role, CLI profile, etc.)

Examples:
  # List all deployments
  flink-ververica list_deployments -w w-xxx -n default -r cn-beijing

  # Start a job (interactive confirmation)
  flink-ververica start_job -w w-xxx -n default -r cn-beijing --deployment_id d-xxx

  # Start a job (non-interactive, for scripts/agents)
  flink-ververica start_job -w w-xxx -n default -r cn-beijing --deployment_id d-xxx --confirm

  # Table output
  flink-ververica list_deployments -w w-xxx -n default -r cn-beijing -o table
""",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # Register all workflow modules
    import w1_sql_development
    import w2_deployment_ops
    import w3_session_cluster
    import w4_dev_resources
    import w5_workspace_admin

    w1_sql_development.register(subparsers)
    w2_deployment_ops.register(subparsers)
    w3_session_cluster.register(subparsers)
    w4_dev_resources.register(subparsers)
    w5_workspace_admin.register(subparsers)

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
