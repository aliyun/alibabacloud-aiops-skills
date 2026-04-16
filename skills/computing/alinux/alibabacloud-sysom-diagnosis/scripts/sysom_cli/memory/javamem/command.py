# -*- coding: utf-8 -*-
"""Java 工作负载快速排查骨架：高 RSS 中 Java 特征 → 建议 SysOM javamem。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict, List

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata
from sysom_cli.lib.schema import agent_block, envelope
from sysom_cli.memory.lib.classify_engine import java_go_hints_from_rows, memory_ps_top_sample
from sysom_cli.memory.lib.envelope_memory import (
    next_steps_struct,
)
from sysom_cli.memory.lib.memory_envelope_finalize import finalize_memory_envelope
from sysom_cli.memory.lib.memory_remote_helpers import (
    run_memory_deep_diagnosis_local_first,
    run_memory_remote_invoke,
)
from sysom_cli.memory.lib.remote_capabilities import remote_analysis_value_map
from sysom_cli.memory.lib.shared_invoke_args import MEMORY_DEEP_DIAGNOSIS_ARGS


def _limits_javamem() -> str:
    return (
        "仅基于进程名 RSS 粗采样，非 JVM 堆/GC 分析；"
        "堆、GC、语言侧结论需 SysOM javamem 专项。"
    )


@command_metadata(
    name="javamem",
    help="本机快速排查：高内存进程中 Java 特征；建议 SysOM javamem；可选 --deep-diagnosis 接深度诊断。",
    subsystem="memory",
    args=list(MEMORY_DEEP_DIAGNOSIS_ARGS),
)
class JavamemHintCommand(BaseCommand):
    @property
    def command_name(self) -> str:
        return "javamem"

    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: True,
            ExecutionMode.HYBRID: False,
        }

    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        recommended = "javamem"
        remote_analysis_value = remote_analysis_value_map()
        if getattr(ns, "deep_diagnosis", False):
            return run_memory_deep_diagnosis_local_first(
                recommended=recommended,
                memory_action="memory_javamem_hint",
                ns=ns,
                remote_analysis_value=remote_analysis_value,
                verbose_summary=(
                    "深度诊断：已发起 SysOM javamem 专项。"
                    "（未跑本机进程 RSS 采样；本路径以远程专项为主。）"
                ),
            )

        top = memory_ps_top_sample()
        java_hint, _ = java_go_hints_from_rows(top)

        sample = [{"comm": c, "rss_kb": rss} for c, _, rss in top[:8]]
        if java_hint:
            summary = "高 RSS 进程中出现 Java 相关工作负载，建议 SysOM javamem 专项。"
            cats = ["java_workload"]
        else:
            summary = (
                "当前粗采样未见明显 Java 进程特征；若问题与 Java 相关仍可直接发起 javamem，"
                "或先用 memory classify 综合归类。"
            )
            cats = ["general"]

        next_actions = next_steps_struct(recommended, ns)
        agent = agent_block(
            "normal",
            summary,
            findings=[
                {"kind": "rss_top_sample", "process_count": len(sample)}
            ],
            next_steps=next_actions,
        )

        data: Dict[str, Any] = {
            "recommended_service_name": recommended,
            "java_signal": java_hint,
            "rss_top_sample": sample,
        }

        out = envelope(
            action="memory_javamem_hint",
            ok=True,
            agent=agent,
            data=data,
            execution={"subsystem": "memory", "phase": "quick_review"},
        )

        return finalize_memory_envelope(out, ns, verbose_summary=summary)

    def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
        recommended = "javamem"
        remote_analysis_value = remote_analysis_value_map()
        rsummary = "深度诊断模式：直接发起 javamem（未跑本机进程采样）。"
        out = envelope(
            action="memory_javamem_hint",
            ok=True,
            agent=agent_block("normal", rsummary, findings=[], next_steps=[]),
            data={
                "recommended_service_name": recommended,
                "remote_analysis_value": remote_analysis_value,
            },
            execution={"subsystem": "memory", "mode": "remote", "phase": "remote_invoke"},
        )
        return run_memory_remote_invoke(
            out, recommended, ns, verbose_summary=rsummary
        )
