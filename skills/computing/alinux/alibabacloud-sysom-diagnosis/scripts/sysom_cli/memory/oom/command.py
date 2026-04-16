# -*- coding: utf-8 -*-
"""本机 OOM 线索：内核日志轻量扫描；建议 SysOM oomcheck 专项。"""
from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata
from sysom_cli.lib.schema import agent_block, envelope
from sysom_cli.memory.lib.envelope_memory import (
    next_steps_struct,
    oom_diagnosis_agent_brief_zh,
    oom_diagnosis_invoke_extra_purpose_zh,
)
from sysom_cli.memory.lib.memory_envelope_finalize import finalize_memory_envelope
from sysom_cli.memory.lib.memory_remote_helpers import (
    run_memory_deep_diagnosis_local_first,
    run_memory_remote_invoke,
)
from sysom_cli.memory.lib.oom_quick import (
    analyze_oom_local,
    normalize_oomcheck_time_param,
)
from sysom_cli.memory.lib.remote_capabilities import remote_analysis_value_map
from sysom_cli.memory.lib.shared_invoke_args import MEMORY_DEEP_DIAGNOSIS_ARGS


def merge_oom_time_into_namespace(ns: Namespace) -> Namespace:
    """将 `--oom-time` 写入 params.time，供远程 oomcheck / --deep-diagnosis 调用。"""
    oom_time = getattr(ns, "oom_time", None)
    if not oom_time or not str(oom_time).strip():
        return ns
    params: Dict[str, Any] = {}
    try:
        if getattr(ns, "params", None):
            params = json.loads(ns.params)
        elif getattr(ns, "params_file", None):
            raw = Path(ns.params_file).read_text(encoding="utf-8")
            params = json.loads(raw)
    except (json.JSONDecodeError, OSError, TypeError):
        params = {}
    params["time"] = normalize_oomcheck_time_param(str(oom_time).strip())
    kw = vars(ns).copy()
    kw["params"] = json.dumps(params, ensure_ascii=False)
    kw["params_file"] = None
    return Namespace(**kw)


OOM_COMMAND_EXTRA_ARGS: List[Tuple[Any, Dict[str, Any]]] = [
    (
        ["--oom-at"],
        {
            "dest": "oom_at",
            "default": None,
            "help": "本机 quick：锚定墙钟时间，选取时间上最接近的 OOM 块作为全文主选（Unix 秒 / ISO / journal 风格月日时分秒）",
        },
    ),
    (
        ["--oom-time"],
        {
            "dest": "oom_time",
            "default": None,
            "help": (
                "远程 oomcheck：合并到 params.time（可与 --params / --params-file 叠加）；"
                "支持 ISO、日期+时间、Unix 秒、journal 风格等，发起前会转为 Unix 秒以满足 OpenAPI 字符集"
            ),
        },
    ),
    (
        ["--max-oom-summaries"],
        {
            "dest": "max_oom_summaries",
            "type": int,
            "default": 64,
            "help": "折叠同类摘要后，oom_events_summary 最多保留最近若干条（默认 64）",
        },
    ),
    (
        ["--max-oom-full-logs"],
        {
            "dest": "max_oom_full_logs",
            "type": int,
            "default": 1,
            "help": "本机 oom_logs 全文条数上限（默认 1；与 --oom-at 组合时以锚定块为末端向前取）",
        },
    ),
]


@command_metadata(
    name="oom",
    help=(
        "本机快速排查：扫描内核日志中的 OOM / oom-killer 行；建议 SysOM oomcheck；"
        "可选 --deep-diagnosis：快速排查后继续深度诊断。"
    ),
    subsystem="memory",
    args=list(MEMORY_DEEP_DIAGNOSIS_ARGS) + OOM_COMMAND_EXTRA_ARGS,
)
class OomHintCommand(BaseCommand):
    @property
    def command_name(self) -> str:
        return "oom"

    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: True,
            ExecutionMode.HYBRID: False,
        }

    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        recommended = "oomcheck"
        remote_analysis_value = remote_analysis_value_map()
        invoke_ns = merge_oom_time_into_namespace(ns)
        if getattr(ns, "deep_diagnosis", False):
            return run_memory_deep_diagnosis_local_first(
                recommended=recommended,
                memory_action="memory_oom_hint",
                ns=invoke_ns,
                remote_analysis_value=remote_analysis_value,
                verbose_summary=(
                    "深度诊断：已发起 SysOM oomcheck 专项。"
                    "（未跑本机内核日志扫描；本路径以远程专项为主。）"
                ),
            )

        oom_local = analyze_oom_local(
            oom_at=getattr(ns, "oom_at", None),
            max_event_summaries=int(getattr(ns, "max_oom_summaries", 64) or 64),
            max_full_oom_logs=int(getattr(ns, "max_oom_full_logs", 1) or 0),
        )
        n = oom_local["hit_count"]
        lt = oom_local.get("oom_lines_total")
        has_signal = n > 0
        if has_signal:
            if oom_local.get("extraction_mode") == "sysak_blocks" and lt is not None:
                summary = f"解析到 {n} 次 OOM 事件（{lt} 行内核文本）。"
            else:
                summary = f"宽松匹配到 {n} 条 OOM 相关内核行。"
        else:
            summary = "近期内核日志未匹配到 OOM 事件。"
        tr = oom_local.get("time_range")
        if has_signal and tr:
            summary += f" 时间：{tr['first_seen_local']} ~ {tr['last_seen_local']}。"
        if has_signal and n > 1:
            summary += " 多次 OOM，可用 --oom-at/--oom-time 指定某次。"

        next_actions = next_steps_struct(
            recommended,
            ns,
            diagnosis_extra_purpose_zh=oom_diagnosis_invoke_extra_purpose_zh(n),
        )
        findings: List[Dict[str, Any]] = [
            {"kind": "oom_kernel_hits", "oom_event_count": n},
        ]

        agent = agent_block(
            "normal",
            summary,
            findings=findings,
            next_steps=next_actions,
        )

        data: Dict[str, Any] = {
            "recommended_service_name": recommended,
            "oom_signal": has_signal,
            "hit_count": n,
            "oom_local": oom_local,
        }

        out = envelope(
            action="memory_oom_hint",
            ok=True,
            agent=agent,
            data=data,
            execution={"subsystem": "memory", "phase": "quick_review"},
        )

        return finalize_memory_envelope(out, ns, verbose_summary=summary)

    def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
        recommended = "oomcheck"
        remote_analysis_value = remote_analysis_value_map()
        rsummary = "深度诊断模式：直接发起 oomcheck（未跑本机内核日志扫描）。"
        out = envelope(
            action="memory_oom_hint",
            ok=True,
            agent=agent_block("normal", rsummary, findings=[], next_steps=[]),
            data={
                "recommended_service_name": recommended,
                "remote_analysis_value": remote_analysis_value,
            },
            execution={"subsystem": "memory", "mode": "remote", "phase": "remote_invoke"},
        )
        return run_memory_remote_invoke(
            out, recommended, merge_oom_time_into_namespace(ns), verbose_summary=rsummary
        )
