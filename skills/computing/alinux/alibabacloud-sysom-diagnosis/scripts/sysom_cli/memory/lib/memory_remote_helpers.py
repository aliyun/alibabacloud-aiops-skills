# -*- coding: utf-8 -*-
"""memory 子命令：--deep-diagnosis 与 execute_remote 共用的远程结果合并。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict

from sysom_cli.lib.precheck_gate import merge_precheck_gate_failure_into_memory_envelope
from sysom_cli.lib.schema import agent_block, envelope
from sysom_cli.memory.lib.invoke_bridge import run_deep_diagnosis_invoke
from sysom_cli.memory.lib.memory_envelope_finalize import (
    finalize_memory_envelope,
    merge_deep_diagnosis_flat,
)


def apply_deep_diagnosis_or_precheck_merge(
    out: Dict[str, Any],
    inv: Dict[str, Any],
    *,
    recommended: str,
    ns: Namespace,
    verbose_summary: str,
) -> Dict[str, Any]:
    """inv 为 run_deep_diagnosis_invoke 返回值；precheck 失败时合并进 quick 信封。"""
    if not inv.get("ok") and inv.get("action") == "precheck":
        merge_precheck_gate_failure_into_memory_envelope(out, inv)
    else:
        merge_deep_diagnosis_flat(out, inv, service_name=recommended)
        if not inv.get("ok"):
            out["ok"] = False
            if inv.get("agent"):
                out["agent"] = inv["agent"]
            if inv.get("error"):
                out["error"] = inv["error"]
    return finalize_memory_envelope(out, ns, verbose_summary=verbose_summary)


def run_memory_remote_invoke(
    out: Dict[str, Any],
    recommended: str,
    ns: Namespace,
    *,
    verbose_summary: str,
) -> Dict[str, Any]:
    """execute_remote：外层已在 BaseCommand.execute(REMOTE) 做过 precheck 门禁。"""
    inv = run_deep_diagnosis_invoke(recommended, ns, skip_precheck=True)
    return apply_deep_diagnosis_or_precheck_merge(
        out, inv, recommended=recommended, ns=ns, verbose_summary=verbose_summary
    )


def run_memory_deep_diagnosis_local_first(
    *,
    recommended: str,
    memory_action: str,
    ns: Namespace,
    remote_analysis_value: Dict[str, Any],
    verbose_summary: str,
) -> Dict[str, Any]:
    """
    本地入口带 --deep-diagnosis：先发起远程专项，避免先构造整块本机 quick 数据。
    precheck 失败时合并进最小信封（与 apply_deep_diagnosis 的 precheck 分支一致）。
    """
    inv = run_deep_diagnosis_invoke(recommended, ns)
    out = envelope(
        action=memory_action,
        ok=True,
        agent=agent_block("normal", "", findings=[], next_steps=[]),
        data={
            "recommended_service_name": recommended,
            "remote_analysis_value": remote_analysis_value,
        },
        execution={"subsystem": "memory", "phase": "quick_review"},
    )
    if not inv.get("ok") and inv.get("action") == "precheck":
        merge_precheck_gate_failure_into_memory_envelope(out, inv)
        return finalize_memory_envelope(out, ns, verbose_summary=verbose_summary)
    merge_deep_diagnosis_flat(out, inv, service_name=recommended)
    if not inv.get("ok"):
        out["ok"] = False
        if inv.get("agent"):
            out["agent"] = inv["agent"]
        if inv.get("error"):
            out["error"] = inv["error"]
    return finalize_memory_envelope(out, ns, verbose_summary=verbose_summary)
