# -*- coding: utf-8 -*-
"""内存类命令信封：agent.next 由 next_steps_struct 生成；finalize 补全 routing/local。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict, List, Optional

# agent.next 的 purpose_zh
_AGENT_NEXT_RUN_HINT_ZH = (
    "在技能根 Bash 执行，勿让用户手抄。"
)

_REMOTE_REGION_INSTANCE_ZH = (
    "本机不传 --region/--instance。"
)

_DEEP_DIAGNOSIS_MUST_ZH = (
    "应继续深度诊断，勿仅以 quick 结论结束。"
)


def oom_diagnosis_agent_brief_zh(hit_count: int) -> str:
    """供 data.oom_diagnosis_cli_hints_zh：仅「下一步」引导。"""
    multi = f"本封 {hit_count} 次 OOM，针对某次用 --oom-time。" if hit_count > 1 else ""
    return multi + "深度用 memory oom --deep-diagnosis；细则见 oomcheck.md。"


def oom_diagnosis_invoke_extra_purpose_zh(hit_count: int) -> str:
    """附在 diagnosis_invoke 的 purpose_zh 末尾；内容与 data.oom_diagnosis_cli_hints_zh 同源，仅多换行包裹。"""
    return f"\n【oomcheck 下一步】{oom_diagnosis_agent_brief_zh(hit_count)}\n"


def recommended_specialty_cli_command(
    service_name: str,
    ns: Optional[Namespace] = None,
) -> str:
    """可复制 shell：内存域 memory 子命令。"""
    suffix = "--channel ecs --timeout 300"
    memory_cli = {
        "memgraph": f"./scripts/osops.sh memory memgraph --deep-diagnosis {suffix}",
        "oomcheck": f"./scripts/osops.sh memory oom --deep-diagnosis {suffix}",
        "javamem": f"./scripts/osops.sh memory javamem --deep-diagnosis {suffix}",
    }
    cmd = memory_cli.get(
        service_name,
        f"./scripts/osops.sh memory classify --deep-diagnosis {suffix}",
    )
    if ns is not None:
        reg = str(getattr(ns, "region", None) or "").strip()
        inst = str(getattr(ns, "instance", None) or "").strip()
        if reg and inst:
            cmd += f" --region {reg} --instance {inst}"
    return cmd


def _deep_step_only_commands(
    recommended: str,
    ns: Optional[Namespace] = None,
) -> List[Dict[str, str]]:
    """环境检查已通过时仅保留一条可执行的深度诊断命令。"""
    return [
        {
            "action": "diagnosis_invoke",
            "command": recommended_specialty_cli_command(recommended, ns),
            "purpose_zh": (
                f"{_AGENT_NEXT_RUN_HINT_ZH}"
                f"{_REMOTE_REGION_INSTANCE_ZH}"
                f"{_DEEP_DIAGNOSIS_MUST_ZH}"
                f"发起「{recommended}」深度诊断；环境已通过。"
            ),
        }
    ]


def build_next_steps_commands(
    recommended: str,
    ns: Optional[Namespace] = None,
) -> List[Dict[str, str]]:
    """扁平步骤（供 agent.next 展开）；每项含 action、command、purpose_zh。"""
    pre = (
        f"{_AGENT_NEXT_RUN_HINT_ZH}"
        f"{_REMOTE_REGION_INSTANCE_ZH}"
        "先执行 precheck 确认凭证。"
    )
    inv = (
        f"{_AGENT_NEXT_RUN_HINT_ZH}"
        f"{_REMOTE_REGION_INSTANCE_ZH}"
        f"{_DEEP_DIAGNOSIS_MUST_ZH}"
        f"precheck 通过后发起「{recommended}」深度诊断。"
    )
    return [
        {
            "action": "precheck",
            "command": "./scripts/osops.sh precheck",
            "purpose_zh": pre,
        },
        {
            "action": "diagnosis_invoke",
            "command": recommended_specialty_cli_command(recommended, ns),
            "purpose_zh": inv,
        },
    ]


def _steps_with_action_kind(raw_steps: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in raw_steps:
        action = s.get("action", "")
        if action == "precheck":
            kind = "precheck"
        elif action == "diagnosis_invoke":
            kind = "sysom_specialty"
        else:
            kind = "other_subcommand"
        out.append(
            {
                "action_kind": kind,
                "action": action,
                "command": s.get("command", ""),
                "purpose_zh": s.get("purpose_zh", ""),
            }
        )
    return out


def next_steps_struct(
    recommended_service_name: str,
    ns: Optional[Namespace] = None,
    *,
    diagnosis_extra_purpose_zh: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """供写入 agent.next：若 run_precheck 已通过则仅深度命令一步，否则 precheck + 深度两步。"""
    from sysom_cli.lib.auth import run_precheck

    cr = run_precheck()
    if cr["ok"]:
        raw = _deep_step_only_commands(recommended_service_name, ns)
    else:
        raw = build_next_steps_commands(recommended_service_name, ns)
    out = _steps_with_action_kind(raw)
    if diagnosis_extra_purpose_zh:
        for step in out:
            if step.get("action") == "diagnosis_invoke":
                step["purpose_zh"] = step.get("purpose_zh", "") + diagnosis_extra_purpose_zh
    return out


def quick_analysis_block_classify(
    *,
    inputs_checked: List[str],
    categories: List[str],
    conclusion_zh: str,
    confidence: float,
    limits_zh: str,
) -> Dict[str, Any]:
    return {
        "inputs_checked": inputs_checked,
        "categories": categories,
        "conclusion_zh": conclusion_zh,
        "confidence": confidence,
        "limits_zh": limits_zh,
    }


def quick_analysis_block_oom(
    *,
    conclusion_zh: str,
    limits_zh: str,
) -> Dict[str, Any]:
    """结论与局限；命中次数见 data.routing / data.local，不在此重复。"""
    return {
        "inputs_checked": ["kernel_log_journal_oom_patterns"],
        "conclusion_zh": conclusion_zh,
        "limits_zh": limits_zh,
    }


# 信封约定：classify 的完整 facts（含 top_processes_sample）只在 data.local.facts
CLASSIFY_FACTS_DATA_REF_ZH = (
    "完整本机摘要（meminfo 指标、RSS 采样、OOM 行数等）见 data.local.facts；"
    "若存在 OOM，逐次摘要见 data.local.oom_local.oom_events_summary，结构化关键字段见 oom_digest。"
)

# memgraph quick：本机快照只在 data.meminfo_facts / data.rss_top_sample
MEMGRAPH_LOCAL_SNAPSHOT_REF_ZH = (
    "本机 meminfo 摘要见 data.local.meminfo_facts，高 RSS 进程采样见 data.local.rss_top_sample。"
)

# javamem：RSS 采样仅在 data.rss_top_sample
RSS_TOP_SAMPLE_DATA_REF_ZH = "高 RSS 进程采样（comm、rss_kb）见 data.local.rss_top_sample。"


def limits_zh_default_classify() -> str:
    return (
        "未在目标机执行 SysOM 采集；语言运行时（JVM/Go）细节、"
        "全景 memgraph 等需走下方 SysOM 专项。"
    )


def limits_zh_default_oom() -> str:
    return (
        "仅扫描本机内核日志尾部窗口；journal/dmesg 格式不同会导致部分行无法解析墙钟时间；"
        "遗漏与根因链仍可能需 SysOM oomcheck 专项。"
    )
