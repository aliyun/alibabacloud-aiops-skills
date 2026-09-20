"""CLI entry point for LHM Scheduler migration tool.

The CLI is Agent-driven: each step is a stateless single-shot command that
makes one API call and prints a structured JSON status. The Agent inspects the
JSON `status` field (and the exit code) to decide whether to wait and retry a
poll command, advance to the next step, or abort.

Exit codes:
- 0: step completed / normal (status started or completed)
- 1: configuration / validation error
- 2: business failure (status failed)
- 3: task still in progress — Agent should wait and re-invoke the poll command
"""

import json
import sys
import os
from typing import Optional

import click

from lhm_read_exec_cli import credentials as credential_file
from lhm_read_exec_cli import single_step
from lhm_read_exec_cli.config import LhmConfig
from lhm_read_exec_cli.renderer import render_result
from lhm_read_exec_cli.validator import validate_environment

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_FAILED = 2
EXIT_IN_PROGRESS = 3


def _load_config_or_exit(endpoint, region):
    """Load config from environment, exiting with EXIT_CONFIG_ERROR on failure."""
    try:
        return LhmConfig.from_environment(
            endpoint_override=endpoint, region_override=region
        )
    except ValueError as config_error:
        click.echo(f"✗ Configuration error: {config_error}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)


def _save_task_id(task_id: str) -> None:
    """Save task_id to <session-dir>/output/ds-cli/result/readexec.json.

    结果文件与会话配置（session.json）共用同一临时目录
    /tmp/lhm-sch-session-<uid>/，与 statistics_loader 的解压目录保持一致。
    """
    from datetime import datetime

    output_dir = credential_file.session_dir_path() / "output" / "ds-cli" / "result"
    output_dir.mkdir(parents=True, exist_ok=True)

    result_file = output_dir / "readexec.json"
    data = {"task_id": task_id, "created_at": datetime.now().isoformat()}
    result_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_task_id_to_session(task_id: str) -> None:
    """Merge task_id into the session temp config (top-level convert_task_id).

    The session file uses the flat layout written by lhm-sch-env (same shape as
    lhm_credentials.template.json), with mode 0600 and possibly plaintext
    credentials, so existing content is preserved and permissions are re-applied
    on rewrite. Failure to persist is non-fatal: a warning goes to stderr and the
    step result is still emitted normally.
    """
    from datetime import datetime

    session_path = credential_file.session_file_path()

    data = {}
    if session_path.is_file():
        try:
            loaded = json.loads(session_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError) as read_error:
            click.echo(f"⚠️  会话配置读取失败，将重建 {session_path}: {read_error}", err=True)

    # 扁平结构：与 lhm-sch-env 转写输出一致，直接写顶层键
    data["convert_task_id"] = task_id
    data["convert_task_created_at"] = (
        datetime.now().astimezone().isoformat(timespec="seconds")
    )
    # 清理旧版分节结构中可能残留的 migration.convert_task_id，避免两处不一致
    legacy_migration = data.get("migration")
    if isinstance(legacy_migration, dict):
        legacy_migration.pop("convert_task_id", None)
        legacy_migration.pop("convert_task_created_at", None)
        if not legacy_migration:
            data.pop("migration", None)

    try:
        session_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(session_path.parent, 0o700)
        # 先以 0600 创建再写入，避免默认 umask 造成的短暂宽权限窗口
        fd = os.open(str(session_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(session_path, 0o600)
    except OSError as write_error:
        click.echo(f"⚠️  task_id 写入会话配置失败 {session_path}: {write_error}", err=True)


def _emit_and_exit(result: dict) -> None:
    """Print a step result as JSON to stdout and exit with the mapped code.

    Exit code mapping:
    - started / completed → EXIT_OK
    - running             → EXIT_IN_PROGRESS
    - ambiguous / failed  → EXIT_FAILED
    """
    # convert-start 成功时，记录 task_id 到 readexec.json 和会话临时配置
    if result.get("task_id") and result.get("status") == "started":
        _save_task_id(result["task_id"])
        _save_task_id_to_session(result["task_id"])

    click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    status = result.get("status")
    if status in ("started", "completed"):
        sys.exit(EXIT_OK)
    if status == "running":
        sys.exit(EXIT_IN_PROGRESS)
    sys.exit(EXIT_FAILED)


@click.group()
def main():
    """LHM Sch Read Exec CLI - Agent-driven schedule migration tool."""


@main.command()
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def validate(endpoint: Optional[str], region: Optional[str]):
    """Validate environment prerequisites (SDK, credentials, connectivity)."""
    config = _load_config_or_exit(endpoint, region)

    click.echo("=" * 60)
    click.echo("LHM Scheduler Inner API Environment Validation")
    click.echo("=" * 60)

    result = validate_environment(config)

    click.echo("\n" + "=" * 60)
    if result.success:
        click.echo("✓ Environment validation PASSED")
        for warning in result.warnings:
            click.echo(f"  ⚠ {warning}")
        sys.exit(EXIT_OK)
    else:
        click.echo("✗ Environment validation FAILED")
        for error in result.errors:
            click.echo(f"  ✗ {error}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)


@main.command(name="read-start")
@click.option("--source", "-s", required=True, help="Source datasource name.")
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def read_start(source: str, endpoint: Optional[str], region: Optional[str]):
    """Start schedule exploration (one API call, no polling).

    Outputs JSON status. On 'started', next call 'read-poll'. On 'ambiguous',
    pick an exact name from 'candidates' and re-run with it.
    """
    config = _load_config_or_exit(endpoint, region)
    result = single_step.read_start(config, source)
    _emit_and_exit(result)


@main.command(name="read-poll")
@click.option("--source", "-s", required=True, help="Source datasource name.")
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def read_poll(source: str, endpoint: Optional[str], region: Optional[str]):
    """Poll exploration result (one API call, no polling).

    Outputs JSON status. 'running' (exit 3) → Agent waits ~20s and re-runs this
    command. 'completed' (exit 0) → carries workflow_count / node_count.
    """
    config = _load_config_or_exit(endpoint, region)
    result = single_step.read_poll(config, source)
    _emit_and_exit(result)


@main.command(name="convert-start")
@click.option("--source", "-s", required=True, help="Source datasource name.")
@click.option("--target", "-t", required=True, help="Target datasource name.")
@click.option(
    "--sql-convert-map",
    default=None,
    help='JSON map for SQL dialect conversion, e.g. \'{"DWSSQL":"HOLOGRES_SQL"}\'.',
)
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def convert_start(
    source: str,
    target: str,
    sql_convert_map: Optional[str],
    endpoint: Optional[str],
    region: Optional[str],
):
    """Trigger schedule conversion (one API call, no polling).

    Outputs JSON status. On 'started', carries 'task_id' — pass it to
    'convert-poll --task-id'.
    """
    config = _load_config_or_exit(endpoint, region)
    result = single_step.convert_start(config, source, target, sql_convert_map)
    _emit_and_exit(result)


@main.command(name="convert-poll")
@click.option("--task-id", "task_id", required=True, help="Conversion task ID.")
@click.option(
    "--output-format",
    "-o",
    type=click.Choice(["text", "json"]),
    default="json",
    show_default=True,
    help="When completed, render summary as 'text' or include raw 'json'.",
)
@click.option("--endpoint", default=None, help="Override LHM_ENDPOINT env var.")
@click.option("--region", default=None, help="Override REGION_ID env var.")
def convert_poll(
    task_id: str,
    output_format: str,
    endpoint: Optional[str],
    region: Optional[str],
):
    """Poll conversion result (one API call, no polling).

    Outputs JSON status. 'running' (exit 3) → Agent waits ~20s and re-runs.
    'completed' (exit 0) → with -o text, prints the §5.4 summary to stderr in
    addition to the JSON status on stdout.
    """
    config = _load_config_or_exit(endpoint, region)
    result = single_step.convert_poll(config, task_id)

    if result.get("status") == "completed" and output_format == "text":
        summary = render_result(
            result.get("task_id", task_id),
            result.get("request_id", "N/A"),
            result.get("data", {}),
            "text",
        )
        click.echo(summary, err=True)

    _emit_and_exit(result)


if __name__ == "__main__":
    main()
