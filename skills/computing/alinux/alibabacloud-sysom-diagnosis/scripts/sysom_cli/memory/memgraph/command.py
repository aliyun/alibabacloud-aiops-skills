# -*- coding: utf-8 -*-
"""内存偏高 / 组成不明 / TCP·socket 相关内存：本机 meminfo 与 RSS 粗采样；SysOM memgraph 含全景与 socket/TCP 等采集（见专文）。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict, List

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata
from sysom_cli.lib.schema import agent_block, envelope
from sysom_cli.memory.lib.classify_engine import meminfo_quick_facts, memory_ps_top_sample
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


def _limits_memgraph() -> str:
    return (
        "本机仅 /proc/meminfo 与进程 RSS 粗采样；整机/应用维度的内存大图与组成拆解需 "
        "SysOM memgraph 深度诊断。"
        "MemAvailable 占比偏高**不能**单独证明「无内存问题」：尖峰、cgroup/容器限额、"
        "JVM/语言运行时堆、延迟回收缓存等，均可能使用户或应用仍感知「内存不够」。"
        "本输出人读与自动化共用：若**要继续用 SysOM 做全景/专项**，应在技能根按 agent.next 执行 "
        "`memory memgraph --deep-diagnosis`；若仅查看本机粗检、不打算调用 SysOM，可忽略 agent.next。"
    )


@command_metadata(
    name="memgraph",
    help=(
        "本机快速排查：内存用量摘要与高 RSS 采样；深度诊断走 SysOM memgraph（整机/应用内存组成）；"
        "可选 --deep-diagnosis。"
    ),
    subsystem="memory",
    args=list(MEMORY_DEEP_DIAGNOSIS_ARGS),
)
class MemgraphHintCommand(BaseCommand):
    @property
    def command_name(self) -> str:
        return "memgraph"

    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: True,
            ExecutionMode.HYBRID: False,
        }

    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        recommended = "memgraph"
        remote_analysis_value = remote_analysis_value_map()
        if getattr(ns, "deep_diagnosis", False):
            return run_memory_deep_diagnosis_local_first(
                recommended=recommended,
                memory_action="memory_memgraph_hint",
                ns=ns,
                remote_analysis_value=remote_analysis_value,
                verbose_summary=(
                    "深度诊断：已发起 SysOM memgraph 专项。"
                    "（未跑本机 meminfo/RSS 快照；本路径以远程专项为主。）"
                ),
            )

        facts = meminfo_quick_facts()
        top = memory_ps_top_sample()

        ratio = facts.get("mem_available_ratio")
        total_kb = facts.get("mem_total_kb", 0)
        if total_kb <= 0:
            summary = (
                "未能读取本机 MemTotal；仍可直接发起 SysOM memgraph 在目标机采集内存全景大图。"
            )
            confidence = 0.4
            cats = ["memory_panorama"]
        elif ratio is not None and ratio < 0.08:
            summary = (
                f"MemAvailable 占比偏低（约 {ratio:.1%}），适合用 SysOM memgraph 做内存全景拆解。"
                "本机粗检不能替代 SysOM 采集；拟用 SysOM 时须按 agent.next 发起 --deep-diagnosis。"
            )
            confidence = 0.72
            cats = ["memory_pressure", "memory_panorama"]
        else:
            summary = (
                "本机 MemAvailable 比例尚可，仍**不**排除用户感知的内存压力或应用侧内存错误；"
                "若本次会话按「内存不够/内存高/OOM 相关」排障，须用 SysOM memgraph 深度复核。"
                "请按 agent.next 执行 `memory memgraph --deep-diagnosis`，勿仅凭本封粗检下结论。"
            )
            confidence = 0.62
            cats = ["memory_panorama", "memory_deep_followup_recommended"]

        sample = [{"comm": c, "rss_kb": rss} for c, _, rss in top[:8]]
        next_actions = next_steps_struct(recommended, ns)
        agent = agent_block(
            "normal",
            summary,
            findings=[
                {
                    "kind": "meminfo_summary",
                    "mem_total_kb": facts.get("mem_total_kb"),
                    "mem_available_ratio": facts.get("mem_available_ratio"),
                },
            ],
            next_steps=next_actions,
        )

        data: Dict[str, Any] = {
            "recommended_service_name": recommended,
            "meminfo_facts": facts,
            "rss_top_sample": sample,
        }

        out = envelope(
            action="memory_memgraph_hint",
            ok=True,
            agent=agent,
            data=data,
            execution={"subsystem": "memory", "phase": "quick_review"},
        )

        return finalize_memory_envelope(out, ns, verbose_summary=summary)

    def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
        recommended = "memgraph"
        remote_analysis_value = remote_analysis_value_map()
        rsummary = "深度诊断模式：直接发起 memgraph（未跑本机 meminfo/RSS 快照）。"
        out = envelope(
            action="memory_memgraph_hint",
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
