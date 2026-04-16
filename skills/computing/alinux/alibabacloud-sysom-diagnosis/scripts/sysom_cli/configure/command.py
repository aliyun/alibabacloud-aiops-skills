# -*- coding: utf-8 -*-
"""将 RAM 用户 AK 写入 ~/.aliyun/config.json，供 osops / SDK 跨 Shell 读取。"""
from __future__ import annotations

import getpass
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata
from sysom_cli.lib.guidance import base_guidance_block, precheck_commands


def _default_config_path() -> Path:
    return Path.home() / ".aliyun" / "config.json"


def _envelope_non_interactive_shell() -> Dict[str, Any]:
    """
    无 PTY 时 input/getpass 触发 EOFError：返回结构化信封，避免被 __main__ 打成泛化 execution_error，
    并显式提示 /settings（PTY）与 /bash（与 credential_policy 一致）。
    """
    from sysom_cli.lib.schema import agent_block, envelope

    bg = base_guidance_block()
    pc0 = precheck_commands()[0]
    remediation = [
        "原因：当前 shell 无交互式输入（无 PTY），无法在本命令内读取 AccessKey（EOF）。",
        "方式 1（优先）：在 **COSH** 中执行 **/settings**，使能「**交互式Shell（PTY）**」，再在 sysom-diagnosis（技能根）重试: ./scripts/osops.sh configure",
        "方式 2：执行 **/bash** 进入交互式 Bash，cd 到技能根后执行: ./scripts/osops.sh configure",
        "方式 3：按 references/authentication.md「方式 A: 手动编辑配置文件」编辑 ~/.aliyun/config.json（mode=AK），勿在聊天粘贴 Secret",
        f"配置完成后执行: {pc0}",
    ]
    detail_lines = "\n".join(
        [
            "1) /settings → 开启「交互式Shell（PTY）」→ 技能根重试 ./scripts/osops.sh configure",
            "2) /bash → cd <sysom-diagnosis 技能根> → ./scripts/osops.sh configure",
            "3) 或手工编辑 ~/.aliyun/config.json（见 authentication.md）",
        ]
    )
    return envelope(
        action="configure",
        ok=False,
        agent=agent_block(
            status="error",
            summary=(
                "无 PTY，无法交互输入。请先在 /settings 使能「交互式Shell（PTY）」或使用 /bash 后再运行 configure；"
                "或手工编辑 ~/.aliyun/config.json。"
            ),
            findings=[
                {
                    "severity": "info",
                    "title": "补救步骤（含 /settings）",
                    "detail": detail_lines,
                }
            ],
        ),
        data={
            "remediation": remediation,
            "read_next": [
                "references/authentication.md",
            ],
            "guidance": {
                "credential_policy": bg["credential_policy"],
                "configure_command": bg["configure_command"],
                "precheck_command": bg["precheck_command"],
            },
        },
        error={
            "code": "non_interactive_shell",
            "message": "EOF when reading a line（无 PTY，无法交互输入）",
        },
        execution={"mode": "local", "subsystem": "configure"},
    )


@command_metadata(
    name="configure",
    help="交互式配置 RAM 用户 AccessKey 到 ~/.aliyun/config.json（mode=AK），供 precheck 使用",
    args=[],
)
class ConfigureCommand(BaseCommand):
    @property
    def command_name(self) -> str:
        return "configure"

    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: False,
            ExecutionMode.HYBRID: False,
        }

    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        from sysom_cli.lib.schema import agent_block, envelope

        path = _default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        existing: Dict[str, Any] = {}
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8").strip()
                if raw:
                    existing = json.loads(raw)
            except json.JSONDecodeError:
                return envelope(
                    action="configure",
                    ok=False,
                    agent=agent_block(
                        status="error",
                        summary="现有 ~/.aliyun/config.json 不是合法 JSON，请先备份后删除或手工修复。",
                        findings=[],
                    ),
                    data={"config_path": str(path)},
                    error={"code": "invalid_config", "message": "config.json 解析失败"},
                    execution={"mode": "local"},
                )

        print("交互式写入 ~/.aliyun/config.json（RAM 用户 AK 模式）。Secret 不会回显。", file=sys.stderr)
        try:
            ak_id = input("AccessKey ID: ").strip()
            ak_secret = getpass.getpass("AccessKey Secret: ").strip()
            region = input("Region ID [cn-hangzhou]: ").strip() or "cn-hangzhou"
        except EOFError:
            return _envelope_non_interactive_shell()


        if not ak_id or not ak_secret:
            return envelope(
                action="configure",
                ok=False,
                agent=agent_block(
                    status="error",
                    summary="AccessKey ID 或 Secret 为空，已取消写入。",
                    findings=[],
                ),
                data={},
                error={"code": "empty_credentials", "message": "未输入完整 AK"},
                execution={"mode": "local"},
            )

        profiles = existing.get("profiles")
        if not isinstance(profiles, list):
            profiles = []

        profile_name = "default"
        replaced = False
        for p in profiles:
            if isinstance(p, dict) and p.get("name") == profile_name:
                p["mode"] = "AK"
                p["access_key_id"] = ak_id
                p["access_key_secret"] = ak_secret
                p["region_id"] = region
                p["output_format"] = p.get("output_format") or "json"
                p["language"] = p.get("language") or "zh"
                replaced = True
                break
        if not replaced:
            profiles.append(
                {
                    "name": profile_name,
                    "mode": "AK",
                    "access_key_id": ak_id,
                    "access_key_secret": ak_secret,
                    "region_id": region,
                    "output_format": "json",
                    "language": "zh",
                }
            )

        out_doc: Dict[str, Any] = {
            **{k: v for k, v in existing.items() if k not in ("current", "current_profile", "profiles")},
            "current": profile_name,
            "profiles": profiles,
        }

        path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)

        return envelope(
            action="configure",
            ok=True,
            agent=agent_block(
                status="success",
                summary=f"已写入 {path}（profile={profile_name}, mode=AK）。请执行 ./scripts/osops.sh precheck 验证。",
                findings=[
                    {
                        "severity": "info",
                        "title": "下一步",
                        "detail": "在 sysom-diagnosis（技能根）执行: ./scripts/osops.sh precheck",
                    }
                ],
            ),
            data={
                "config_path": str(path),
                "profile": profile_name,
                "mode": "AK",
                "note": "Agent 多段 Bash 中 export 不会传递到下一次命令；写入 config.json 可跨会话生效。",
            },
            execution={"mode": "local"},
        )
