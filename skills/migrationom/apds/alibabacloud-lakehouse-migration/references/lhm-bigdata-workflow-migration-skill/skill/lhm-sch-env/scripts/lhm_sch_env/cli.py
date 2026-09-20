"""lhm-sch-env CLI 入口与命令定义。"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

import click

from lhm_sch_env.checks import run_checks


# ---------------------------------------------------------------------------
# Profile 定义：每个 profile 包含必选和可选检查项
# ---------------------------------------------------------------------------

PROFILES: Dict[str, Dict[str, List[str]]] = {
    "schedule": {
        "required": ["api_connectivity"],
        "optional": ["resource_group", "agent"],
    },
    "data-validation": {
        "required": ["api_connectivity", "resource_group", "agent"],
        "optional": [],
    },
    "full": {
        "required": ["api_connectivity", "resource_group", "agent"],
        "optional": [],
    },
}

DEFAULT_PROFILE = "schedule"


# ---------------------------------------------------------------------------
# CLI 命令组
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """LHM 调度迁移环境检查工具。"""


@cli.command()
@click.option(
    "--profile",
    type=click.Choice(list(PROFILES.keys()), case_sensitive=False),
    default=DEFAULT_PROFILE,
    help="检查配置集（默认 schedule）。",
)
@click.option(
    "--session-file",
    default=None,
    help="显式指定 session.json 路径（覆盖自动发现）。",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="输出机器可读的 JSON 结果。",
)
def check(profile: str, session_file: Optional[str], output_json: bool):
    """执行环境检查。

    从 lhm-sch-env 会话配置（session.json）加载凭证，依次执行指定
    profile 中的检查项，输出每项的状态与修复指引。
    """
    results = run_checks(profile=profile, session_file=session_file)

    if output_json:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_human_readable(results)

    # 存在 blocking 失败项时返回非零退出码
    has_blocking_failure = any(
        item.get("blocking") and item["status"] == "fail"
        for item in results.get("checks", [])
    )
    sys.exit(1 if has_blocking_failure else 0)


# ---------------------------------------------------------------------------
# 人类可读输出
# ---------------------------------------------------------------------------

_STATUS_ICONS = {"pass": "✓", "fail": "✗", "skip": "⊘", "pending_api": "…"}


def _print_human_readable(results: Dict[str, Any]) -> None:
    """将检查结果以简洁文本形式打印到 stdout。"""
    profile = results.get("profile", DEFAULT_PROFILE)
    checks = results.get("checks", [])
    ready = results.get("ready", False)
    summary = results.get("summary", "")

    click.echo(f"LHM 环境检查（profile={profile}）")
    click.echo("-" * 60)

    for item in checks:
        icon = _STATUS_ICONS.get(item["status"], "?")
        name = item["name"]
        message = item["message"]
        click.echo(f"  {icon} {name}: {message}")

        if item["status"] == "fail" and item.get("fix_guide"):
            for line in item["fix_guide"].splitlines():
                click.echo(f"      {line}")

    click.echo("-" * 60)
    click.echo(summary)

    if not ready:
        blocking = [c["name"] for c in checks if c.get("blocking") and c["status"] == "fail"]
        if blocking:
            click.echo(f"阻塞项: {', '.join(blocking)}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    cli()
