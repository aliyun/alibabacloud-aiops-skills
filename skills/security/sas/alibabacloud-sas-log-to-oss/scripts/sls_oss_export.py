#!/usr/bin/env python3
"""
SLS Log Export to OSS Tool

Automates exporting Alibaba Cloud SLS (Log Service) logs to OSS (Object Storage) for cold storage.
Supports listing LogStores, creating/listing/viewing/stopping/starting/deleting OSS export tasks,
and batch creating export tasks for all LogStores under a Project.

Built on the alibabacloud_sls20201230 SDK.

Prerequisites:
    pip install -r scripts/requirements.txt
    (or: pip install alibabacloud_sls20201230==5.14.0 alibabacloud_credentials==1.0.10)

Credentials (environment variables, automatically read by CredentialClient):
    ALIBABA_CLOUD_ACCESS_KEY_ID     - AccessKey ID
    ALIBABA_CLOUD_ACCESS_KEY_SECRET  - AccessKey Secret
    ALIBABA_CLOUD_ACCOUNT_ID         - Alibaba Cloud account ID (used to construct RAM role ARN)
    SKILL_SESSION_ID                 - Observability session ID (injected by Agent, optional)

Usage:
    python sls_oss_export.py <command> [options]

Commands:
    list-logstores          List all LogStores under an SLS Project
    create-export           Create a single OSS export task
    batch-create            Batch create export tasks for all (or specified) LogStores
    list-exports            List all OSS export tasks
    get-export              View details of a specific export task
    stop-export             Stop an export task
    start-export            Start an export task
    delete-export           Delete an export task
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

# Observability configuration
SKILL_NAME = "alibabacloud-sas-log-to-oss"
SESSION_ID = os.environ.get("SKILL_SESSION_ID", "")


def _build_user_agent() -> str:
    """Build User-Agent string for server-side observability tracking."""
    ua = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}"
    if SESSION_ID:
        ua = f"{ua}/{SESSION_ID}"
    return ua


# Default configuration
DEFAULT_REGION = "cn-hangzhou"
DEFAULT_SLS_ENDPOINT = f"{DEFAULT_REGION}.log.aliyuncs.com"
DEFAULT_OSS_ENDPOINT = f"https://oss-{DEFAULT_REGION}-internal.aliyuncs.com"
DEFAULT_ROLE_NAME = "aliyunlogdefaultrole"
DEFAULT_PATH_FORMAT = "%Y/%m/%d/%H/%M"
DEFAULT_TIMEZONE = "+0800"
DEFAULT_CONTENT_TYPE = "json"
DEFAULT_COMPRESSION = "snappy"
DEFAULT_BUFFER_INTERVAL = 300
DEFAULT_BUFFER_SIZE = 256
DEFAULT_DELAY_SECONDS = 0


def get_account_id() -> str:
    """Read Alibaba Cloud account ID from environment variable (used to construct RAM role ARN)."""
    account_id = os.environ.get("ALIBABA_CLOUD_ACCOUNT_ID")
    if not account_id:
        print("Error: Please set the ALIBABA_CLOUD_ACCOUNT_ID environment variable.")
        print("  This variable is used to construct the RAM role ARN, format: acs:ram::<account_id>:role/aliyunlogdefaultrole")
        sys.exit(1)
    return account_id


def create_client(endpoint: str = None):
    """Create and return an SLS client instance (using CredentialClient to automatically load credentials)."""
    from alibabacloud_sls20201230.client import Client
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_credentials.client import Client as CredentialClient

    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=endpoint or DEFAULT_SLS_ENDPOINT,
        user_agent=_build_user_agent(),
    )
    return Client(config)


def get_role_arn(account_id: str, role_name: str = None) -> str:
    """Construct a RAM role ARN."""
    return f"acs:ram::{account_id}:role/{role_name or DEFAULT_ROLE_NAME}"


def build_content_detail(content_type: str, args) -> dict:
    """Build contentDetail configuration based on storage format."""
    if content_type == "json":
        return {"enableTag": args.enable_tag if hasattr(args, "enable_tag") else True}
    elif content_type == "csv":
        columns = args.columns.split(",") if hasattr(args, "columns") and args.columns else []
        delimiter = args.delimiter if hasattr(args, "delimiter") and args.delimiter else ","
        header = args.header if hasattr(args, "header") else True
        return {
            "columns": columns,
            "delimiter": delimiter,
            "header": header,
            "lineFeed": "\n",
            "null": "-",
            "quote": '"',
        }
    elif content_type in ("parquet", "orc"):
        columns = []
        if hasattr(args, "columns") and args.columns:
            for col in args.columns.split(","):
                columns.append({"name": col.strip(), "type": "string"})
        return {"columns": columns}
    else:
        return {}


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def cmd_list_logstores(args):
    """List all LogStores under an SLS Project."""
    from alibabacloud_sls20201230 import models

    client = create_client(args.endpoint)
    request = models.ListLogStoresRequest(
        offset=0,
        size=500,
        telemetry_type="None",
    )
    response = client.list_log_stores(args.project, request)
    body = response.body
    logstores = body.logstores or []

    print(f"Project: {args.project}")
    print(f"Total LogStores: {body.total}")
    print(f"Returned: {body.count}")
    print("-" * 60)
    for ls in logstores:
        print(f"  {ls}")
    return logstores


def cmd_create_export(args):
    """Create a single OSS export task."""
    from alibabacloud_sls20201230 import models

    account_id = get_account_id()
    client = create_client(args.endpoint)

    role_arn = get_role_arn(account_id, args.role_name)
    content_detail = build_content_detail(args.content_type, args)

    sink = models.OSSExportConfigurationSink(
        endpoint=args.oss_endpoint,
        bucket=args.bucket,
        prefix=args.prefix,
        suffix=args.suffix,
        role_arn=role_arn,
        path_format=args.path_format,
        path_format_type="time",
        time_zone=args.timezone,
        content_type=args.content_type,
        content_detail=content_detail,
        compression_type=args.compression,
        buffer_interval=args.buffer_interval,
        buffer_size=args.buffer_size,
        delay_seconds=args.delay_seconds,
    )

    configuration = models.OSSExportConfiguration(
        logstore=args.logstore,
        role_arn=role_arn,
        sink=sink,
        from_time=args.from_time,
        to_time=args.to_time,
    )

    request = models.CreateOSSExportRequest(
        name=args.name,
        display_name=args.display_name or args.name,
        description=args.description or f"Export {args.logstore} logs to OSS Bucket {args.bucket}",
        configuration=configuration,
    )

    try:
        client.create_ossexport(args.project, request)
        print(f"[Success] Export task '{args.name}' created successfully.")
        print(f"     Project:    {args.project}")
        print(f"     LogStore:   {args.logstore}")
        print(f"     OSS Bucket: {args.bucket}")
        print(f"     OSS Prefix: {args.prefix}")
        print(f"     Format:     {args.content_type} ({args.compression})")
        print(f"     From Time:  {args.from_time} (1=from first log)")
        print(f"     To Time:    {args.to_time} (0=run forever)")
    except Exception as e:
        print(f"[Failed] Failed to create export task '{args.name}': {e}")
        sys.exit(1)


def cmd_batch_create(args):
    """Batch create export tasks for all (or specified) LogStores."""
    from alibabacloud_sls20201230 import models

    account_id = get_account_id()
    client = create_client(args.endpoint)

    # Get LogStore list
    list_request = models.ListLogStoresRequest(offset=0, size=500, telemetry_type="None")
    list_response = client.list_log_stores(args.project, list_request)
    all_logstores = list_response.body.logstores or []

    # Filter if --logstores is specified
    if args.logstores:
        specified = set(args.logstores.split(","))
        logstores = [ls for ls in all_logstores if ls in specified]
        missing = specified - set(logstores)
        if missing:
            print(f"[Warning] LogStores not found: {', '.join(missing)}")
    else:
        logstores = all_logstores

    print(f"Creating export tasks for {len(logstores)} LogStore(s)...")
    print(f"Target OSS Bucket: {args.bucket}")
    print(f"OSS Prefix Base:   {args.prefix}")
    print("=" * 60)

    role_arn = get_role_arn(account_id, args.role_name)
    success = []
    failed = []

    for ls in logstores:
        task_name = f"export-{ls}-to-oss"
        oss_prefix = f"{args.prefix}{ls}/"
        content_detail = build_content_detail(args.content_type, args)

        sink = models.OSSExportConfigurationSink(
            endpoint=args.oss_endpoint,
            bucket=args.bucket,
            prefix=oss_prefix,
            suffix=args.suffix,
            role_arn=role_arn,
            path_format=args.path_format,
            path_format_type="time",
            time_zone=args.timezone,
            content_type=args.content_type,
            content_detail=content_detail,
            compression_type=args.compression,
            buffer_interval=args.buffer_interval,
            buffer_size=args.buffer_size,
            delay_seconds=args.delay_seconds,
        )

        configuration = models.OSSExportConfiguration(
            logstore=ls,
            role_arn=role_arn,
            sink=sink,
            from_time=args.from_time,
            to_time=args.to_time,
        )

        request = models.CreateOSSExportRequest(
            name=task_name,
            display_name=task_name,
            description=f"Export {ls} logs to OSS cold storage",
            configuration=configuration,
        )

        try:
            client.create_ossexport(args.project, request)
            print(f"  [OK]    {ls:40s} -> {task_name}")
            success.append(ls)
        except Exception as e:
            err_msg = str(e)
            if "already exist" in err_msg.lower() or "conflict" in err_msg.lower():
                print(f"  [SKIP]  {ls:40s} -> export task already exists")
                success.append(ls)
            else:
                print(f"  [FAIL]  {ls:40s} -> {err_msg}")
                failed.append((ls, err_msg))

    print("=" * 60)
    print(f"Summary: {len(success)} succeeded, {len(failed)} failed")
    if failed:
        print("\nFailed LogStores:")
        for ls, err in failed:
            print(f"  {ls}: {err}")


def cmd_list_exports(args):
    """List all OSS export tasks under a Project."""
    from alibabacloud_sls20201230 import models

    client = create_client(args.endpoint)
    request = models.ListOSSExportsRequest(offset=0, size=100)
    if args.logstore:
        request.logstore = args.logstore

    response = client.list_ossexports(args.project, request)
    body = response.body
    results = body.results or []

    print(f"Project: {args.project}")
    print(f"Total export tasks: {body.total}")
    print(f"Returned: {body.count}")
    print("-" * 80)
    for task in results:
        status_icon = {
            "RUNNING": "[Running]",
            "STOPPED": "[Stopped]",
            "FAILED":  "[Failed]",
        }.get(task.status, f"[{task.status}]")
        print(f"  {status_icon} {task.name}")
        print(f"         LogStore:  {task.configuration.logstore}")
        print(f"         Bucket:    {task.configuration.sink.bucket}")
        print(f"         Prefix:    {task.configuration.sink.prefix}")
        print(f"         Format:    {task.configuration.sink.content_type} ({task.configuration.sink.compression_type})")
        if task.create_time:
            print(f"         Created:   {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task.create_time))}")
        print()


def cmd_get_export(args):
    """View details of a specific export task."""
    client = create_client(args.endpoint)
    response = client.get_ossexport(args.project, args.name)
    task = response.body

    print(f"Task Name:       {task.name}")
    print(f"Display Name:    {task.display_name}")
    print(f"Description:     {task.description}")
    print(f"Status:          {task.status}")
    print(f"Schedule ID:     {task.schedule_id}")
    if task.create_time:
        print(f"Created:         {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task.create_time))}")
    if task.last_modified_time:
        print(f"Last Modified:   {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task.last_modified_time))}")
    print()
    print("Configuration:")
    cfg = task.configuration
    print(f"  LogStore:          {cfg.logstore}")
    print(f"  Read RAM Role ARN: {cfg.role_arn}")
    print(f"  From Time:         {cfg.from_time}")
    print(f"  To Time:           {cfg.to_time}")
    print()
    print("OSS Sink:")
    sink = cfg.sink
    print(f"  Endpoint:           {sink.endpoint}")
    print(f"  Bucket:             {sink.bucket}")
    print(f"  Prefix:             {sink.prefix}")
    print(f"  Suffix:             {sink.suffix}")
    print(f"  Write RAM Role ARN: {sink.role_arn}")
    print(f"  Path Format:        {sink.path_format}")
    print(f"  Time Zone:          {sink.time_zone}")
    print(f"  Content Type:       {sink.content_type}")
    print(f"  Content Detail:     {json.dumps(sink.content_detail, ensure_ascii=False)}")
    print(f"  Compression:        {sink.compression_type}")
    print(f"  Buffer Interval:    {sink.buffer_interval}s")
    print(f"  Buffer Size:        {sink.buffer_size}MB")
    print(f"  Delay Seconds:      {sink.delay_seconds}s")


def cmd_stop_export(args):
    """Stop an export task."""
    client = create_client(args.endpoint)
    client.stop_ossexport(args.project, args.name)
    print(f"[Success] Export task '{args.name}' has been stopped.")


def cmd_start_export(args):
    """Start an export task."""
    client = create_client(args.endpoint)
    client.start_ossexport(args.project, args.name)
    print(f"[Success] Export task '{args.name}' has been started.")


def cmd_delete_export(args):
    """Delete an export task."""
    client = create_client(args.endpoint)
    if not args.force:
        confirm = input(f"Confirm deletion of export task '{args.name}'? (y/N): ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return
    client.delete_ossexport(args.project, args.name)
    print(f"[Success] Export task '{args.name}' has been deleted.")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def add_common_args(parser):
    """Add common arguments shared by all subcommands."""
    parser.add_argument("--project", required=True, help="SLS Project name")
    parser.add_argument("--endpoint", default=None, help=f"SLS endpoint (default: {DEFAULT_SLS_ENDPOINT})")


def add_export_config_args(parser):
    """Add OSS export configuration arguments."""
    parser.add_argument("--bucket", required=True, help="OSS Bucket name")
    parser.add_argument("--oss-endpoint", default=DEFAULT_OSS_ENDPOINT, help=f"OSS endpoint (default: {DEFAULT_OSS_ENDPOINT})")
    parser.add_argument("--prefix", default="sls-export/", help="OSS file prefix (default: sls-export/)")
    parser.add_argument("--suffix", default=".json", help="OSS file suffix (default: .json)")
    parser.add_argument("--role-name", default=DEFAULT_ROLE_NAME, help=f"RAM role name (default: {DEFAULT_ROLE_NAME})")
    parser.add_argument("--path-format", default=DEFAULT_PATH_FORMAT, help=r"Partition format, e.g. %%Y/%%m/%%d/%%H/%%M (default: %%Y/%%m/%%d/%%H/%%M)")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help=f"Time zone (default: {DEFAULT_TIMEZONE})")
    parser.add_argument("--content-type", default=DEFAULT_CONTENT_TYPE, choices=["json", "csv", "parquet", "orc"], help=f"Storage format (default: {DEFAULT_CONTENT_TYPE})")
    parser.add_argument("--compression", default=DEFAULT_COMPRESSION, choices=["snappy", "gzip", "zstd", "none"], help=f"Compression type (default: {DEFAULT_COMPRESSION})")
    parser.add_argument("--buffer-interval", type=int, default=DEFAULT_BUFFER_INTERVAL, help=f"Buffer interval in seconds, 300-900 (default: {DEFAULT_BUFFER_INTERVAL})")
    parser.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE, help=f"Buffer size in MB, 5-256 (default: {DEFAULT_BUFFER_SIZE})")
    parser.add_argument("--delay-seconds", type=int, default=DEFAULT_DELAY_SECONDS, help=f"Delay in seconds (default: {DEFAULT_DELAY_SECONDS})")
    parser.add_argument("--from-time", type=int, default=1, help="Start time: 1=from first log, or Unix timestamp (default: 1)")
    parser.add_argument("--to-time", type=int, default=0, help="End time: 0=run forever, or Unix timestamp (default: 0)")
    # CSV/Parquet/ORC specific arguments
    parser.add_argument("--columns", default=None, help="Column names, comma-separated (for csv/parquet/orc formats)")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
    parser.add_argument("--header", action="store_true", default=True, help="Include CSV header (default: True)")
    parser.add_argument("--enable-tag", action="store_true", default=True, help="Include tag fields in JSON (default: True)")


def main():
    parser = argparse.ArgumentParser(
        description="SLS Log Export to OSS Tool - Automate exporting SLS logs to OSS cold storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list-logstores - List LogStores
    p_list = subparsers.add_parser("list-logstores", help="List all LogStores under an SLS Project")
    add_common_args(p_list)

    # create-export - Create a single export task
    p_create = subparsers.add_parser("create-export", help="Create a single OSS export task")
    add_common_args(p_create)
    p_create.add_argument("--logstore", required=True, help="Source LogStore name")
    p_create.add_argument("--name", required=True, help="Export task name (lowercase letters, digits, hyphens, underscores; 2-64 characters)")
    p_create.add_argument("--display-name", default=None, help="Display name (defaults to task name)")
    p_create.add_argument("--description", default=None, help="Task description")
    add_export_config_args(p_create)

    # batch-create - Batch create
    p_batch = subparsers.add_parser("batch-create", help="Batch create export tasks for all (or specified) LogStores")
    add_common_args(p_batch)
    p_batch.add_argument("--logstores", default=None, help="LogStore names, comma-separated (default: all LogStores)")
    add_export_config_args(p_batch)

    # list-exports - List export tasks
    p_list_exp = subparsers.add_parser("list-exports", help="List all OSS export tasks")
    add_common_args(p_list_exp)
    p_list_exp.add_argument("--logstore", default=None, help="Filter by LogStore name")

    # get-export - View export task
    p_get = subparsers.add_parser("get-export", help="View details of a specific export task")
    add_common_args(p_get)
    p_get.add_argument("--name", required=True, help="Export task name")

    # stop-export - Stop export task
    p_stop = subparsers.add_parser("stop-export", help="Stop an export task")
    add_common_args(p_stop)
    p_stop.add_argument("--name", required=True, help="Export task name")

    # start-export - Start export task
    p_start = subparsers.add_parser("start-export", help="Start an export task")
    add_common_args(p_start)
    p_start.add_argument("--name", required=True, help="Export task name")

    # delete-export - Delete export task
    p_delete = subparsers.add_parser("delete-export", help="Delete an export task")
    add_common_args(p_delete)
    p_delete.add_argument("--name", required=True, help="Export task name")
    p_delete.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to the corresponding command handler
    commands = {
        "list-logstores": cmd_list_logstores,
        "create-export":  cmd_create_export,
        "batch-create":   cmd_batch_create,
        "list-exports":   cmd_list_exports,
        "get-export":     cmd_get_export,
        "stop-export":    cmd_stop_export,
        "start-export":   cmd_start_export,
        "delete-export":  cmd_delete_export,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
