# -*- coding: utf-8 -*-
"""本地内存归类：多特征分类与路由建议。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict, List

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata
from sysom_cli.lib.schema import agent_block, envelope
from sysom_cli.memory.lib.classify_engine import build_remote_analysis_payload, run_classify
from sysom_cli.memory.lib.envelope_memory import (
    next_steps_struct,
    oom_diagnosis_invoke_extra_purpose_zh,
)
from sysom_cli.memory.lib.memory_envelope_finalize import finalize_memory_envelope
from sysom_cli.memory.lib.memory_remote_helpers import (
    run_memory_deep_diagnosis_local_first,
    run_memory_remote_invoke,
)
from sysom_cli.memory.lib.shared_invoke_args import MEMORY_DEEP_DIAGNOSIS_ARGS


@command_metadata(
    name="classify",
    help=(
        "本机快速排查：meminfo / 内核 OOM 线索 / 进程 RSS 粗采样，给出类别与建议的 SysOM 专项；"
        "可选 --deep-diagnosis：快速排查后继续深度诊断。"
    ),
    subsystem="memory",
    args=list(MEMORY_DEEP_DIAGNOSIS_ARGS),
)
class ClassifyCommand(BaseCommand):
    """本地 memory classify：默认仅快速排查；可选 --deep-diagnosis 接深度诊断。"""

    @property
    def command_name(self) -> str:
        return "classify"

    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: True,
            ExecutionMode.HYBRID: False,
        }

    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        result = run_classify()
        remote_analysis_value = build_remote_analysis_payload()

        recommended = result.recommended_service_name
        summary = result.primary_reason_zh + (
            f"（建议 SysOM 专项：{recommended}，置信度约 {result.confidence:.2f}）"
        )
        oom_hc = int((result.oom_local or {}).get("hit_count") or 0)
        if recommended == "oomcheck" and oom_hc > 1:
            summary += f" 检出 {oom_hc} 次 OOM，可用 --oom-time 指定某次。"

        if getattr(ns, "deep_diagnosis", False):
            return run_memory_deep_diagnosis_local_first(
                recommended=recommended,
                memory_action="memory_classify",
                ns=ns,
                remote_analysis_value=remote_analysis_value,
                verbose_summary=f"深度诊断：已按归类建议发起专项「{recommended}」。{summary}",
            )

        ff = result.facts
        meminfo_finding: Dict[str, Any] = {
            "kind": "meminfo_and_classify",
            "mem_total_kb": ff.get("mem_total_kb"),
            "mem_available_kb": ff.get("mem_available_kb"),
            "mem_available_ratio": ff.get("mem_available_ratio"),
            "oom_event_count": ff.get("oom_event_count"),
        }
        findings: List[Dict[str, Any]] = [meminfo_finding]
        if result.oom_local:
            findings.append({"kind": "oom_kernel_hits", "oom_event_count": oom_hc})

        oom_brief_zh = ""
        next_actions = next_steps_struct(
            recommended,
            ns,
            diagnosis_extra_purpose_zh=(
                oom_diagnosis_invoke_extra_purpose_zh(oom_hc)
                if recommended == "oomcheck"
                else None
            ),
        )

        agent = agent_block(
            "normal",
            summary,
            findings=findings,
            next_steps=next_actions,
        )

        data: Dict[str, Any] = {
            "categories": result.categories,
            "recommended_service_name": recommended,
            "confidence": result.confidence,
            "primary_reason_zh": result.primary_reason_zh,
            "facts": result.facts,
        }
        if result.oom_local:
            ol = result.oom_local
            data["oom_local"] = ol
            data["oom_signal"] = ol["hit_count"] > 0
            data["hit_count"] = ol["hit_count"]

        out = envelope(
            action="memory_classify",
            ok=True,
            agent=agent,
            data=data,
            execution={"subsystem": "memory", "phase": "quick_review"},
        )

        return finalize_memory_envelope(out, ns, verbose_summary=summary)

    def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
        result = run_classify()
        remote_analysis_value = build_remote_analysis_payload()
        recommended = result.recommended_service_name
        rsummary = f"深度诊断模式：按归类建议直接发起专项「{recommended}」。"
        out = envelope(
            action="memory_classify",
            ok=True,
            agent=agent_block("normal", rsummary, findings=[], next_steps=[]),
            data={
                "recommended_service_name": recommended,
                "remote_analysis_value": remote_analysis_value,
                "confidence": result.confidence,
                "primary_reason_zh": result.primary_reason_zh,
                "categories": result.categories,
            },
            execution={"subsystem": "memory", "mode": "remote", "phase": "remote_invoke"},
        )
        return run_memory_remote_invoke(
            out, recommended, ns, verbose_summary=rsummary
        )
