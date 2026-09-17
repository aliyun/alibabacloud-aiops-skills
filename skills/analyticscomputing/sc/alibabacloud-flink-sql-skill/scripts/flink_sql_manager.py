#!/usr/bin/env python3
"""Unified Alibaba Cloud Flink SQL lifecycle CLI (API 2022-07-18)."""

import argparse
import os
import sys

# Keep scripts/ on sys.path so workflow modules can import client.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        prog="flink-sql-manager",
        description="Develop, validate, deploy, operate, and diagnose Alibaba Cloud Flink SQL Jobs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Lifecycle:
  Prepare              config_init, config_doctor, get_catalogs, get_tables, list_connectors ...
  Develop              create_draft, update_draft, validate_sql, validate_draft ...
  Deploy               deploy_draft, get_deploy_result, get_deployment ...
  Operate              start_job, get_job, stop_job, create_savepoint ...
  Diagnose             diagnose_job, get_start_log, get_events, flink_api_proxy ...
  Historical Metrics   get_metric_dashboard, get_metric_data
  Git                  git_init, git_sync (automatically synchronizes Deployment mutations when configured)

Authentication:
  Uses the Alibaba Cloud default credential chain (RAM Role, CLI profile, and so on)
  Historical Metrics use a user-provided VVP Cookie (standard input or VVP_COOKIE)

Examples:
  # Save one default scope for the first time (without credentials)
  python3 scripts/flink_sql_manager.py config_init -w <workspace> -n <namespace> -r <region>

  # Check scope, credential discovery, and Git configuration without calling a Flink resource API
  python3 scripts/flink_sql_manager.py config_doctor

  # List all Deployments
  python3 scripts/flink_sql_manager.py list_deployments -w <workspace> -n <namespace> -r <region>

  # Start a Job (interactive confirmation)
  python3 scripts/flink_sql_manager.py start_job -w <workspace> -n <namespace> -r <region> --deployment_id <deployment-id> --restore_strategy LATEST_STATE

  # Start a Job (non-interactive mode for scripts or agents)
  python3 scripts/flink_sql_manager.py start_job -w <workspace> -n <namespace> -r <region> --deployment_id <deployment-id> --restore_strategy LATEST_STATE --confirm

  # Table output
  python3 scripts/flink_sql_manager.py list_deployments -w <workspace> -n <namespace> -r <region> -o table
""",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="available commands")

    # Expose one CLI surface; modules split implementation only by lifecycle domain.
    import config_cmd
    import git_sync
    import sql_development
    import job_operations
    import metric_history
    import session_clusters
    import sql_extensions
    import sql_runtime_resources

    config_cmd.register(subparsers)
    git_sync.register(subparsers)
    sql_development.register(subparsers)
    job_operations.register(subparsers)
    metric_history.register(subparsers)
    session_clusters.register(subparsers)
    sql_extensions.register(subparsers)
    sql_runtime_resources.register(subparsers)

    args = parser.parse_args()

    from client import SkillIdentityError, apply_scope_defaults, error_response, output

    apply_scope_defaults(args)

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
        try:
            args.func(args)
        except SkillIdentityError as exc:
            output(error_response(args.subcommand, "SkillIdentityError", str(exc)), args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
