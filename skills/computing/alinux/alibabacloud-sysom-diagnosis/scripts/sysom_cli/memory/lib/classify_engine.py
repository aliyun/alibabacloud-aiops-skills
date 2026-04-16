# -*- coding: utf-8 -*-
"""
内存问题本地轻量归类：meminfo、本机进程 RSS 粗采样，以及通过 `oom_quick.analyze_oom_local`
复用 `memory oom` 的 quick 结论作为 OOM 归类信号。不调用 OpenAPI。
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sysom_cli.memory.lib.oom_quick import analyze_oom_local
from sysom_cli.memory.lib.remote_capabilities import remote_analysis_value_map


def _read_meminfo() -> Dict[str, int]:
    out: Dict[str, int] = {}
    path = Path("/proc/meminfo")
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(\w+):\s+(\d+)\s+kB\s*$", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def meminfo_quick_facts() -> Dict[str, Any]:
    """本机 /proc/meminfo 轻量摘要（kb），供 memory memgraph 等 quick_review。"""
    mem = _read_meminfo()
    total_kb = mem.get("MemTotal", 0)
    avail_kb = mem.get("MemAvailable") or mem.get("MemFree", 0)
    swap_total = mem.get("SwapTotal", 0)
    swap_free = mem.get("SwapFree", 0)
    facts: Dict[str, Any] = {
        "mem_total_kb": total_kb,
        "mem_available_kb": avail_kb,
        "swap_total_kb": swap_total,
        "swap_free_kb": swap_free,
    }
    if total_kb > 0:
        facts["mem_available_ratio"] = round(avail_kb / total_kb, 4)
    for k in ("Slab", "Buffers", "Cached", "AnonPages", "Shmem"):
        if k in mem:
            facts[f"{k.lower()}_kb"] = mem[k]
    return facts


def _top_rss_processes(limit: int = 24) -> List[Tuple[str, str, int]]:
    """返回 [(comm, cmdline_snippet, rss_kb), ...] 按 RSS 降序；失败则空列表。"""
    try:
        r = subprocess.run(
            [
                "ps",
                "-eo",
                "comm,rss",
                "--sort=-rss",
                "--no-headers",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0 or not r.stdout:
            return []
        rows: List[Tuple[str, str, int]] = []
        for line in r.stdout.strip().splitlines():
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            comm, rss_s = parts[0], parts[1].strip()
            try:
                rss = int(rss_s)
            except ValueError:
                continue
            rows.append((comm, comm, rss))
            if len(rows) >= limit:
                break
        return rows
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _java_go_hints(rows: List[Tuple[str, str, int]]) -> Tuple[bool, bool]:
    java = False
    go = False
    for comm, _, _ in rows[:15]:
        c = comm.lower()
        if "java" in c or c == "java":
            java = True
        # Go 进程 comm 多变，仅对极弱特征做启发式，避免误判
        if any(x in c for x in ("___go_", "dlv", "gopls")):
            go = True
    return java, go


@dataclass
class ClassifyResult:
    """归类结果。"""

    categories: List[str] = field(default_factory=list)
    category_labels_zh: Dict[str, str] = field(default_factory=dict)
    primary_reason_zh: str = ""
    recommended_service_name: str = "memgraph"
    confidence: float = 0.5
    facts: Dict[str, Any] = field(default_factory=dict)
    oom_hits: List[str] = field(default_factory=list)
    oom_local: Optional[Dict[str, Any]] = None


def run_classify() -> ClassifyResult:
    mem = _read_meminfo()
    total_kb = mem.get("MemTotal", 0)
    avail_kb = mem.get("MemAvailable") or mem.get("MemFree", 0)
    swap_total = mem.get("SwapTotal", 0)
    swap_free = mem.get("SwapFree", 0)

    facts: Dict[str, Any] = {
        "mem_total_kb": total_kb,
        "mem_available_kb": avail_kb,
        "swap_total_kb": swap_total,
        "swap_free_kb": swap_free,
    }
    if total_kb > 0:
        facts["mem_available_ratio"] = round(avail_kb / total_kb, 4)

    # OOM 详细提取属 memory oom quick，此处仅复用以驱动 classify 路由与 facts
    oom_local = analyze_oom_local()
    facts["oom_signal_lines"] = oom_local.get("oom_lines_total") or oom_local["hit_count"]
    if oom_local.get("oom_event_count"):
        facts["oom_event_count"] = oom_local["oom_event_count"]

    top = _top_rss_processes()
    facts["top_processes_sample"] = [
        {"comm": c, "rss_kb": rss} for c, _, rss in top[:8]
    ]
    java_hint, go_hint = _java_go_hints(top)

    cats: List[str] = []
    labels: Dict[str, str] = {
        "oom_signal": "内核日志中存在 OOM / oom-killer 相关线索",
        "memory_pressure": "可用内存占比偏低（压力）",
        "swap_pressure": "Swap 空间紧张或未配置 Swap",
        "java_workload": "高 RSS 进程中出现 Java 相关工作负载",
        "go_workload": "高 RSS 进程中出现 Go 相关弱特征（启发式，需结合业务确认）",
        "general": "通用内存分布与全景（默认）",
    }

    recommended = "memgraph"
    confidence = 0.55
    reason_parts: List[str] = []

    if oom_local["hit_count"]:
        cats.append("oom_signal")
        recommended = "oomcheck"
        confidence = 0.82
        reason_parts.append("内核日志中存在 OOM / oom-killer 相关线索，优先走 OOM 专项。")
    elif total_kb > 0 and (avail_kb / total_kb) < 0.08:
        cats.append("memory_pressure")
        recommended = "memgraph"
        confidence = 0.78
        reason_parts.append("MemAvailable 占比偏低，建议先做内存全景（memgraph）。")
    elif swap_total > 0 and swap_free < swap_total * 0.15:
        cats.append("swap_pressure")
        recommended = "memgraph"
        confidence = 0.72
        reason_parts.append("Swap 使用率较高，建议内存全景排查回收与组成。")
    elif swap_total == 0:
        cats.append("swap_pressure")
        reason_parts.append("当前未配置 Swap（SwapTotal=0），突发内存压力时风险更高；可选 memgraph 看组成。")

    if java_hint and recommended == "memgraph" and "oom_signal" not in cats:
        cats.append("java_workload")
        recommended = "javamem"
        confidence = max(confidence, 0.68)
        reason_parts.append("高内存进程偏 Java，建议 Java 内存专项（javamem）。")
    elif go_hint and recommended == "memgraph" and "oom_signal" not in cats and not java_hint:
        cats.append("go_workload")
        recommended = "memgraph"
        confidence = max(confidence, 0.62)
        reason_parts.append(
            "启发式存在 Go 相关弱特征：CLI 侧优先走内存全景（memgraph）；若已确认 Java 工作负载再改用 javamem。"
        )

    if not cats:
        cats.append("general")
    if not reason_parts:
        cats.append("general")
        reason_parts.append("未见强特征，默认建议内存全景（memgraph）。")

    primary = " ".join(reason_parts) if reason_parts else labels.get(cats[0], labels["general"])

    oom_tail5 = oom_local["oom_digest"][-2:] if oom_local["hit_count"] else []

    return ClassifyResult(
        categories=cats,
        category_labels_zh={k: labels[k] for k in cats if k in labels},
        primary_reason_zh=primary,
        recommended_service_name=recommended,
        confidence=confidence,
        facts=facts,
        oom_hits=oom_tail5,
        oom_local=oom_local if oom_local["hit_count"] else None,
    )


def build_remote_analysis_payload() -> Dict[str, str]:
    """供信封 data.remote_analysis_value。"""
    return remote_analysis_value_map()


def memory_ps_top_sample(limit: int = 24) -> List[Tuple[str, str, int]]:
    """供 memory javamem 等子命令复用。"""
    return _top_rss_processes(limit)


def java_go_hints_from_rows(rows: List[Tuple[str, str, int]]) -> Tuple[bool, bool]:
    """基于 RSS Top 行判断 Java / Go 弱特征。"""
    return _java_go_hints(rows)
