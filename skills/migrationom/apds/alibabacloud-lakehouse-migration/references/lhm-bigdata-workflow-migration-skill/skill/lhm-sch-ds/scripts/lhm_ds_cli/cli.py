"""CLI entry point for LHM Scheduler Datasource management tool.

The CLI is Agent-driven: each command is a stateless single-shot operation that
makes one API call and prints a structured JSON status. The Agent inspects the
JSON `status` field (and the exit code) to decide the next step — ask the user,
upload a file, advance, retry, or abort. State (parsed config, datasource name,
new id) is passed explicitly via command-line arguments; nothing is persisted.

Exit codes:
- 0: operation succeeded (status ok / empty / available / match)
- 1: configuration / validation error
- 2: business failure or name already taken (status failed / exists)
"""

import json
import sys
import os
from pathlib import Path

import click

from lhm_ds_cli import operations
from lhm_ds_cli.config import LhmConfig
from lhm_ds_cli.validator import validate_environment

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_FAILED = 2


def _load_config_or_exit(endpoint, region):
    """Load config from environment, exiting with EXIT_CONFIG_ERROR on failure."""
    try:
        return LhmConfig.from_environment(
            endpoint_override=endpoint, region_override=region
        )
    except ValueError as config_error:
        click.echo(f"✗ Configuration error: {config_error}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)


def _emit_and_exit(result: dict) -> None:
    """Print a step result as JSON to stdout and exit with the mapped code.

    Exit code mapping:
    - ok / empty / available / match → EXIT_OK
    - exists / failed                → EXIT_FAILED
    """
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    status = result.get("status")
    if status in ("ok", "empty", "available", "match"):
        sys.exit(EXIT_OK)
    sys.exit(EXIT_FAILED)


def _run_or_fail(operation, *args, **kwargs) -> dict:
    """Invoke an operation, converting any uncaught exception into a 'failed'
    status dict so the CLI always emits the structured JSON contract instead of
    leaking a Python traceback (e.g. network / auth / SDK errors).
    """
    try:
        return operation(*args, **kwargs)
    except Exception as operation_error:  # noqa: BLE001 - boundary, must not leak traceback
        return {
            "status": "failed",
            "err_code": type(operation_error).__name__,
            "err_message": str(operation_error),
            "request_id": "",
        }


def _load_ds_config_or_exit(config_file: str) -> dict:
    """Load and parse the filled datasource config JSON file."""
    try:
        with open(config_file, "r", encoding="utf-8") as handle:
            parsed = json.load(handle)
    except FileNotFoundError:
        click.echo(f"✗ Config file not found: {config_file}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)
    except json.JSONDecodeError as parse_error:
        click.echo(f"✗ Invalid JSON in {config_file}: {parse_error}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    parsed.pop("_comment", None)
    return parsed


@click.group()
def main():
    """LHM Sch DS CLI - Agent-driven datasource management tool."""


@main.command()
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def validate(endpoint, region):
    """Validate environment prerequisites (SDK, credentials, client init)."""
    config = _load_config_or_exit(endpoint, region)

    click.echo("=" * 60)
    click.echo("LHM Scheduler Datasource Environment Validation")
    click.echo("=" * 60)

    result = validate_environment(config)

    click.echo("\n" + "=" * 60)
    if result.success:
        click.echo("✓ Environment validation PASSED")
        for warning in result.warnings:
            click.echo(f"  ⚠ {warning}")
        sys.exit(EXIT_OK)
    click.echo("✗ Environment validation FAILED")
    for error in result.errors:
        click.echo(f"  ✗ {error}", err=True)
    sys.exit(EXIT_CONFIG_ERROR)


@main.command()
@click.option("--ds-name", "-n", required=True, help="Datasource name to look up.")
@click.option(
    "--category-type",
    "-c",
    default="WORKFLOW",
    show_default=True,
    help="Datasource category type.",
)
@click.option(
    "--ds-type",
    "-t",
    default=None,
    help="Datasource technical type; omit to send an empty string (no type filter).",
)
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def check(ds_name, category_type, ds_type, endpoint, region):
    """Query datasources by name (ListMetaDataComponentPage).

    Omitting --ds-type sends dsType as an empty string "".
    Outputs JSON status. 'empty' (exit 0) → none found, proceed to check-name.
    'match' (exit 0) → carries 'matches'; Agent asks the user to pick one.
    """
    config = _load_config_or_exit(endpoint, region)
    result = _run_or_fail(
        operations.check_existing, config, ds_name, category_type, ds_type
    )
    _emit_and_exit(result)


@main.command(name="check-name")
@click.option("--ds-name", "-n", required=True, help="Candidate datasource name.")
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def check_name(ds_name, endpoint, region):
    """Validate datasource name uniqueness (ExecMetaDataComponentName).

    Outputs JSON status. 'available' (exit 0) → free, proceed. 'exists'
    (exit 2) → taken/invalid; Agent asks the user for a new name and re-runs.
    """
    config = _load_config_or_exit(endpoint, region)
    result = _run_or_fail(operations.check_name, config, ds_name)
    _emit_and_exit(result)


@main.command(name="oss-key")
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def oss_key(endpoint, region):
    """Fetch OSS temporary upload credentials (GetMetaOssTempKey).

    Outputs JSON status. 'ok' (exit 0) → carries 'oss' (ak/policy/signature/
    security_token/dir/...) and an 'expired' flag the Agent must check before
    building the upload curl. The Agent performs the upload itself.
    """
    config = _load_config_or_exit(endpoint, region)
    result = _run_or_fail(operations.oss_key, config)
    _emit_and_exit(result)


@main.command()
@click.option(
    "--file",
    "-f",
    "local_file",
    required=True,
    help="Path to the local metadata file to upload.",
)
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def upload(local_file, endpoint, region):
    """Upload a local metadata file to OSS (fetch STS + multipart upload).

    Fetches credentials, generates a unique OSS object name, and uploads the
    file. The LOCAL file is never renamed or modified. Outputs JSON status.
    'ok' (exit 0) → carries 'oss_filename'; the Agent writes it back into
    dsConfig.source-file-path before calling 'create'.
    """
    config = _load_config_or_exit(endpoint, region)
    result = _run_or_fail(operations.upload_file, config, local_file)
    _emit_and_exit(result)


@main.command()
@click.option(
    "--config-file",
    "-f",
    "config_file",
    required=True,
    help="Path to the filled datasource config JSON file.",
)
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def create(config_file, endpoint, region):
    """Create a datasource (AddMetaDataComponent).

    Reads the filled config JSON (dsName / categoryType / dsType / dsConfig /
    dsStatus). Any OSS upload + source-file-path rewrite must already be done.
    Outputs JSON status. 'ok' (exit 0) → carries 'ds_id'.
    """
    config = _load_config_or_exit(endpoint, region)
    parsed = _load_ds_config_or_exit(config_file)
    result = _run_or_fail(
        operations.create_datasource,
        config,
        ds_name=parsed.get("dsName"),
        category_type=parsed.get("categoryType", "WORKFLOW"),
        ds_type=parsed.get("dsType"),
        ds_config=parsed.get("dsConfig", {}),
        ds_status=parsed.get("dsStatus", 0),
    )
    _emit_and_exit(result)


@main.command(name="test-conn")
@click.option(
    "--config-file",
    "-f",
    "config_file",
    required=True,
    help="Path to the filled datasource config JSON file.",
)
@click.option(
    "--ds-id",
    "ds_id",
    type=int,
    default=None,
    help="Optional datasource id to associate the check with.",
)
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def test_conn(config_file, ds_id, endpoint, region):
    """Test datasource connectivity (ExecWorkflowConnectivity).

    Outputs JSON status. 'ok' (exit 0) → connectivity passed. 'failed' (exit 2)
    → connectivity failed; Agent translates the cause into user guidance.
    """
    config = _load_config_or_exit(endpoint, region)
    parsed = _load_ds_config_or_exit(config_file)
    ds_config = parsed.get("dsConfig", {})
    result = _run_or_fail(
        operations.test_connectivity,
        config,
        ds_name=parsed.get("dsName"),
        ds_type=parsed.get("dsType"),
        ds_version=ds_config.get("dsVersion"),
        ds_config=ds_config,
        ds_id=ds_id,
    )
    _emit_and_exit(result)


if __name__ == "__main__":
    main()
