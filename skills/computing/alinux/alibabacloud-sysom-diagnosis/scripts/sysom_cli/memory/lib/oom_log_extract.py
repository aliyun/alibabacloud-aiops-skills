# -*- coding: utf-8 -*-
"""
从内核日志中按块提取 OOM 记录（对齐 SysOM oomcheck 的块边界规则）。

- 块起点：invoked oom-killer
- 块结束：Killed process+total-vm / oom_reaper / oom-kill:constraint / Out of memory+total-vm
- 块内解析 cgroup（Task in / oom-kill:constraint）

extract_oom_digest() 从已提取的块中解析关键诊断字段（参考 SysOM oomcheck.py），
本地模式仅提取信息，不做结论/建议。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# 与 sysAK oomcheck.py 一致（起点：invoked oom-killer，见 _OOM_BEGIN_RE）
OOM_CGROUP_KEYWORD = "Task in /"
OOM_END_KEYWORD_5_10 = "oom-kill:constraint"


def _is_oom_block_end(line: str, idx: int, lines: List[str]) -> bool:
    """对应 sysAK is_oom_end。"""
    if "Killed process" in line and "total-vm" in line:
        if idx + 1 < len(lines) and "oom_reaper" in lines[idx + 1]:
            return False
        return True
    if "oom_reaper" in line:
        return True
    if "oom-kill:constraint" in line:
        if idx + 1 < len(lines) and "Out of memory" in lines[idx + 1]:
            return False
        return True
    if "Out of memory" in line and "total-vm" in line:
        return True
    return False


def _cgroup_from_task_line(line: str) -> Tuple[str, str]:
    """对应 sysAK oom_get_cgroup_name_api(line, is_510=0)。"""
    if OOM_CGROUP_KEYWORD not in line:
        return "", ""
    try:
        task_list = line.strip().split("Task in")[1].strip().split()
        if len(task_list) < 2:
            return "", ""
        return task_list[0], task_list[-1]
    except (IndexError, ValueError):
        return "", ""


def _cgroup_from_constraint_line(line: str) -> Tuple[str, str]:
    """对应 sysAK oom_get_cgroup_name_api(line, is_510=1)。"""
    if "CONSTRAINT_MEMCG" not in line or "task_memcg=" not in line or "oom_memcg=" not in line:
        return "", ""
    try:
        cgroup = line.split("task_memcg=")[1].split(",")[0]
        pcgroup = line.split("oom_memcg=")[1].split(",")[0]
        return cgroup, pcgroup
    except IndexError:
        return "", ""


_OOM_BEGIN_RE = re.compile(r"invoked\s+oom-killer", re.IGNORECASE)

# ---------- digest 提取正则（参考 SysOM oomcheck.py）----------

_INVOKER_RE = re.compile(
    r"(\S+)\s+invoked\s+oom-killer.*?gfp_mask=(0x\w+)(?:\([^)]*\))?\s*,\s*order=(\d+)",
    re.IGNORECASE,
)
# Killed process 111 (comm) total-vm:NNNkB, anon-rss:NNNkB, file-rss:NNNkB, shmem-rss:NNNkB
_KILLED_PROCESS_RE = re.compile(
    r"Killed\s+process\s+(\d+)\s+\(([^)]+)\).*?"
    r"total-vm:(\d+)kB.*?anon-rss:(\d+)kB.*?file-rss:(\d+)kB"
    r"(?:.*?shmem-rss:(\d+)kB)?",
    re.IGNORECASE,
)
# Fallback: Killed process PID (comm) total-vm:NNNkB (no anon-rss/file-rss)
_KILLED_PROCESS_SIMPLE_RE = re.compile(
    r"Killed\s+process\s+(\d+)\s+\(([^)]+)\).*?total-vm:(\d+)kB",
    re.IGNORECASE,
)
# oom-kill:constraint=XXX,...,task=YYY,pid=NNN,uid=NNN
_CONSTRAINT_KV_RE = re.compile(
    r"oom-kill:constraint=(\S+?)(?:,|\s)"
)
_CONSTRAINT_TASK_RE = re.compile(
    r"task=(\S+?),pid=(\d+),uid=(\d+)"
)
# memory: usage NNNkB, limit NNNkB, failcnt NNN
_CG_USAGE_LIMIT_RE = re.compile(
    r"memory:\s*usage\s+(\d+)kB,\s*limit\s+(\d+)kB"
)
# Task table row: [PID] UID TGID TOTAL_VM RSS ...
_TASK_ROW_RE = re.compile(
    r"\[\s*(\d+)\]\s+\d+\s+\d+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+[-\d]+\s+(\S+)"
)


def _strip_ts_prefix(line: str) -> str:
    """去除 journal/dmesg 时间戳前缀，返回内核消息体。"""
    # journal: "Mar 18 16:02:39.381492 host kernel: MSG"
    if " kernel: " in line:
        return line.split(" kernel: ", 1)[1]
    # dmesg -T: "[Thu Mar 18 ...] MSG" or "[123.456] MSG"
    if line.startswith("[") and "]" in line:
        return line.split("]", 1)[1].strip()
    return line


def extract_oom_digest(block: Dict[str, Any]) -> Dict[str, Any]:
    """从 OOM 块提取关键诊断字段（参考 SysOM oomcheck.py 提取逻辑）。

    仅提取事实信息，不做结论/建议——结论由远程 oomcheck 专项或 Agent 给出。
    """
    lines: List[str] = block.get("lines", [])
    digest: Dict[str, Any] = {
        "line_count": len(lines),
        "invoker_comm": None,
        "gfp_mask": None,
        "order": None,
        "constraint": None,
        "killed_pid": None,
        "killed_comm": None,
        "total_vm_kb": None,
        "anon_rss_kb": None,
        "file_rss_kb": None,
        "shmem_rss_kb": None,
        "task_cgroup": block.get("cgroup") or None,
        "oom_cgroup": block.get("parent_cgroup") or None,
        "cg_usage_kb": None,
        "cg_limit_kb": None,
        "top_rss_tasks": [],
    }

    task_rows: List[Dict[str, Any]] = []

    for raw_line in lines:
        line = _strip_ts_prefix(raw_line)

        # --- invoker ---
        m = _INVOKER_RE.search(line)
        if m:
            digest["invoker_comm"] = m.group(1)
            digest["gfp_mask"] = m.group(2)
            digest["order"] = int(m.group(3))
            continue

        # --- constraint (5.10) ---
        m = _CONSTRAINT_KV_RE.search(line)
        if m:
            digest["constraint"] = m.group(1)
            # 5.10 cgroup: task=...,pid=...,uid=...
            tm = _CONSTRAINT_TASK_RE.search(line)
            if tm and digest["killed_comm"] is None:
                digest["killed_comm"] = tm.group(1)
                digest["killed_pid"] = int(tm.group(2))
            # task_memcg / oom_memcg
            if "task_memcg=" in line:
                digest["task_cgroup"] = line.split("task_memcg=")[1].split(",")[0]
            if "oom_memcg=" in line:
                digest["oom_cgroup"] = line.split("oom_memcg=")[1].split(",")[0]
            continue

        # --- killed process (3.10/4.19/5.10-host) ---
        m = _KILLED_PROCESS_RE.search(line)
        if m:
            digest["killed_pid"] = int(m.group(1))
            digest["killed_comm"] = m.group(2)
            digest["total_vm_kb"] = int(m.group(3))
            digest["anon_rss_kb"] = int(m.group(4))
            digest["file_rss_kb"] = int(m.group(5))
            digest["shmem_rss_kb"] = int(m.group(6)) if m.group(6) else 0
            continue
        # fallback: simpler Killed process line without full mem detail
        m = _KILLED_PROCESS_SIMPLE_RE.search(line)
        if m and digest["killed_pid"] is None:
            digest["killed_pid"] = int(m.group(1))
            digest["killed_comm"] = m.group(2)
            digest["total_vm_kb"] = int(m.group(3))
            continue

        # --- cgroup usage / limit ---
        m = _CG_USAGE_LIMIT_RE.search(line)
        if m and digest["cg_usage_kb"] is None:
            digest["cg_usage_kb"] = int(m.group(1))
            digest["cg_limit_kb"] = int(m.group(2))
            continue

        # --- 4.19 oom_reaper (killed pid/comm) ---
        if "oom_reaper" in line and "reaped process" in line:
            try:
                seg = line.split("reaped process")[1].strip()
                parts = seg.split()
                if len(parts) >= 2 and digest["killed_pid"] is None:
                    digest["killed_pid"] = int(parts[0])
                    digest["killed_comm"] = parts[1].strip(",").strip("()")
            except (ValueError, IndexError):
                pass
            continue

        # --- task table row ---
        m = _TASK_ROW_RE.search(line)
        if m:
            task_rows.append({
                "pid": int(m.group(1)),
                "total_vm_pages": int(m.group(2)),
                "rss_pages": int(m.group(3)),
                "comm": m.group(4),
            })

    # top 5 by RSS
    task_rows.sort(key=lambda t: t["rss_pages"], reverse=True)
    digest["top_rss_tasks"] = task_rows[:5]

    return digest


def extract_oom_blocks(lines: List[str]) -> List[Dict[str, Any]]:
    """
    返回若干 OOM 块；每块含 lines（行列表）、raw_block、cgroup 等。
    无匹配时返回 []。
    """
    res: List[str] = []
    blocks: List[Dict[str, Any]] = []
    in_oom = False
    pending: Optional[Dict[str, Any]] = None

    for idx, line in enumerate(lines):
        if _OOM_BEGIN_RE.search(line):
            res = [line]
            in_oom = True
            pending = {
                "lines": res,
                "cgroup": "",
                "parent_cgroup": "",
            }
            continue

        if not in_oom or pending is None:
            continue

        if _is_oom_block_end(line, idx, lines):
            in_oom = False
            if OOM_END_KEYWORD_5_10 in line:
                cg, pcg = _cgroup_from_constraint_line(line)
                if cg or pcg:
                    pending["cgroup"] = cg
                    pending["parent_cgroup"] = pcg
            pending["lines"].append(line)
            raw = "\n".join(pending["lines"])
            blocks.append(
                {
                    "lines": pending["lines"],
                    "raw_block": raw,
                    "cgroup": pending["cgroup"] or "",
                    "parent_cgroup": pending["parent_cgroup"] or "",
                    "incomplete": False,
                }
            )
            pending = None
            res = []
        elif OOM_CGROUP_KEYWORD in line:
            cg, pcg = _cgroup_from_task_line(line)
            pending["cgroup"] = cg
            pending["parent_cgroup"] = pcg
            pending["lines"].append(line)
        else:
            pending["lines"].append(line)

    if in_oom and pending is not None:
        raw = "\n".join(pending["lines"])
        blocks.append(
            {
                "lines": pending["lines"],
                "raw_block": raw,
                "cgroup": pending["cgroup"] or "",
                "parent_cgroup": pending["parent_cgroup"] or "",
                "incomplete": True,
            }
        )

    return blocks
