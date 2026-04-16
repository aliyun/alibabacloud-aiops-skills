# -*- coding: utf-8 -*-
"""远程 OpenAPI 前的环境门禁：复用 run_precheck 与同构信封。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from sysom_cli.lib.auth import run_precheck
from sysom_cli.lib.precheck_envelope import envelope_from_precheck_result


def remote_precheck_gate() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Returns:
        (True, None) 可继续远程调用；
        (False, envelope) 与 `osops precheck` 失败同构的信封，不应再发 invoke。
    """
    cr = run_precheck()
    if cr["ok"]:
        return True, None
    return False, envelope_from_precheck_result(cr)


def merge_precheck_gate_failure_into_memory_envelope(
    quick_envelope: Dict[str, Any],
    precheck_env: Dict[str, Any],
) -> None:
    """
    在已构建的 memory quick 信封上合并 precheck 失败（--deep-diagnosis 路径）。
    就地修改 quick_envelope。
    """
    quick_envelope["ok"] = False
    if precheck_env.get("error"):
        quick_envelope["error"] = precheck_env["error"]
    pdata = precheck_env.get("data") or {}
    data = quick_envelope.setdefault("data", {})
    data["precheck_gate"] = {
        "ok": False,
        "remediation": pdata.get("remediation"),
        "guidance": pdata.get("guidance"),
        "check_details": pdata.get("check_details"),
        "path_summary": pdata.get("path_summary"),
    }
    agent = quick_envelope.setdefault("agent", {})
    base_summary = (agent.get("summary") or "").strip()
    p_agent = precheck_env.get("agent") or {}
    ps = (p_agent.get("summary") or "").strip()
    agent["summary"] = (
        "data.local 已包含所有本机 OOM 发现，请直接展示给用户，无需采集额外信息。"
        "深度诊断需要认证，请按 data.precheck_gate.remediation 引导用户配置凭证以获取更全面的远程分析。"
    )
    existing = agent.get("findings") or []
    extra = list(p_agent.get("findings") or [])
    if len(extra) > 2:
        extra = [
            extra[0],
            {
                "severity": "info",
                "title": "预检补充说明",
                "detail": (
                    "完整修复步骤见 data.precheck_gate.remediation 与 path_summary；"
                    "无需将 precheck 全部 findings 逐条展开。"
                ),
            },
        ]
    agent["findings"] = list(existing) + extra
    # precheck 失败时清空 next，避免 Agent 解读为“还有命令可跑”
    agent["next"] = []
