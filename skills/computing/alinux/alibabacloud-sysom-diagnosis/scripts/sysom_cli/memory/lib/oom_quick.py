# -*- coding: utf-8 -*-
"""`memory oom` 本机 quick 模式：内核日志扫描、OOM 块解析、oom_digest / oom_events_summary 信封数据。"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sysom_cli.lib.kernel_log import get_kernel_log_lines

from sysom_cli.memory.lib.oom_log_extract import extract_oom_blocks, extract_oom_digest

_OOM_PATTERNS = re.compile(
    r"out of memory|oom-killer|killed process|invoked oom-killer",
    re.IGNORECASE,
)

_JOURNAL_TS = re.compile(
    r"^([A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+",
)
_DMESG_HUMAN_TS = re.compile(r"^\[([A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})\]")
_DMESG_REL = re.compile(r"^\[\s*([\d.]+)\]")

_KILLED_RE = re.compile(r"Killed\s+process\s+\d+\s+\(([^)]+)\)", re.IGNORECASE)


def parse_oom_at_anchor(s: Optional[str]) -> Optional[datetime]:
    """解析 `--oom-at`：Unix 秒、ISO 日期时间、或 journal 风格 `Mar 20 12:00:00`（补当前年）。"""
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    if t.isdigit():
        return datetime.fromtimestamp(int(t))
    ts = t.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        pass
    for fmt in ("%b %d %H:%M:%S.%f", "%b %d %H:%M:%S"):
        try:
            dt = datetime.strptime(t, fmt)
            now = datetime.now()
            dt = dt.replace(year=now.year)
            if dt > now + timedelta(days=1):
                dt = dt.replace(year=now.year - 1)
            return dt
        except ValueError:
            continue
    return None


_HMS_ONLY = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?$")


def parse_oom_time_for_remote(s: str) -> Optional[datetime]:
    """
    解析用户可能传入的多种时间串（供远程 oomcheck params.time）。
    含：纯 Unix 秒、ISO、`YYYY-MM-DD HH:MM:SS`、仅 `HH:MM:SS`（按本地当天）、journal 风格。
    """
    t = (s or "").strip()
    if not t:
        return None
    m = _HMS_ONLY.match(t)
    if m:
        h, mi, sec_s = int(m.group(1)), int(m.group(2)), m.group(3) or "0"
        sec = int(sec_s)
        now = datetime.now()
        return now.replace(hour=h, minute=mi, second=sec, microsecond=0)
    if len(t) >= 11 and t[4] == "-" and t[10] == " ":
        t = t[:10] + "T" + t[11:]
    return parse_oom_at_anchor(t)


def _one_oom_time_segment_to_unix(seg: str) -> str:
    seg = seg.strip()
    if not seg:
        return seg
    if re.fullmatch(r"\d+", seg):
        return seg
    if re.fullmatch(r"\d+\.\d+", seg):
        return str(int(float(seg)))
    dt = parse_oom_time_for_remote(seg)
    if dt is None:
        return seg
    return str(int(dt.timestamp()))


def normalize_oomcheck_time_param(raw: Optional[str]) -> str:
    """
    SysOM Invoke 对 params 值字符集限制为 [a-zA-Z0-9_.~-]；冒号等 ISO 时间会被拒。
    将 oomcheck 的 time（或 `开始~结束`）转为 Unix 秒数字符串（段间仍用 ~）。
    无法解析的片段保持原样，便于服务端或其它格式仍报错时排查。
    """
    if raw is None:
        return ""
    t = str(raw).strip()
    if not t:
        return ""
    if "~" in t:
        left, right = t.split("~", 1)
        return f"{_one_oom_time_segment_to_unix(left)}~{_one_oom_time_segment_to_unix(right)}"
    return _one_oom_time_segment_to_unix(t)


def _kernel_tail_lines(max_lines: int = 4000) -> List[str]:
    lines = get_kernel_log_lines("journal", None)
    if not lines:
        return []
    return lines[-max_lines:] if len(lines) > max_lines else lines


def _oom_loose_line_hits(tail: List[str]) -> List[str]:
    return [ln for ln in tail if _OOM_PATTERNS.search(ln)]


def _oom_hit_lines(max_lines: int = 4000) -> List[str]:
    """OOM 相关行：优先按 sysAK 块展开；无块时退回宽松单行匹配。"""
    tail = _kernel_tail_lines(max_lines)
    if not tail:
        return []
    blocks = extract_oom_blocks(tail)
    if blocks:
        out: List[str] = []
        for b in blocks:
            out.extend(b["lines"])
        return out
    return _oom_loose_line_hits(tail)


def get_oom_kernel_hits(max_lines: int = 4000) -> List[str]:
    return _oom_hit_lines(max_lines)


def _parse_oom_line_time(line: str) -> Tuple[Optional[datetime], str]:
    """
    从内核日志行解析时间。返回 (datetime 或 None, reason)。
    reason: journal | dmesg_human | dmesg_relative_s | none
    """
    m = _JOURNAL_TS.match(line)
    if m:
        frag = m.group(1)
        for fmt in ("%b %d %H:%M:%S.%f", "%b %d %H:%M:%S"):
            try:
                dt = datetime.strptime(frag, fmt)
                now = datetime.now()
                dt = dt.replace(year=now.year)
                if dt > now + timedelta(days=1):
                    dt = dt.replace(year=now.year - 1)
                return dt, "journal"
            except ValueError:
                continue
    m = _DMESG_HUMAN_TS.match(line)
    if m:
        try:
            return datetime.strptime(m.group(1), "%a %b %d %H:%M:%S %Y"), "dmesg_human"
        except ValueError:
            pass
    m = _DMESG_REL.match(line)
    if m:
        try:
            sec = float(m.group(1))
            return None, f"dmesg_relative_s:{sec:.3f}"
        except ValueError:
            pass
    return None, "none"


def _killed_comm_from_lines(lines: List[str]) -> Optional[str]:
    for ln in lines:
        m = _KILLED_RE.search(ln)
        if m:
            comm = (m.group(1) or "").strip()
            return comm.split()[0] if comm else None
    return None


def _scope_hint_from_block(b: Dict[str, Any]) -> str:
    raw = b.get("raw_block") or ""
    if b.get("cgroup") or b.get("parent_cgroup"):
        return "memcg"
    if "CONSTRAINT_MEMCG" in raw or "task_memcg=" in raw:
        return "memcg"
    return "host"


def _block_start_dt(lines: List[str]) -> Tuple[Optional[datetime], str]:
    first = lines[0] if lines else ""
    return _parse_oom_line_time(first)


def _pick_primary_block_index(
    block_dts: List[Optional[datetime]],
    *,
    anchor: Optional[datetime],
) -> Tuple[int, Optional[str]]:
    """返回 (primary_index, note_zh)；无墙钟且指定了 anchor 时退回最后一块并附说明。"""
    n = len(block_dts)
    if n == 0:
        return 0, None
    if anchor is None:
        return n - 1, None
    usable = [(i, dt) for i, dt in enumerate(block_dts) if dt is not None]
    if not usable:
        return n - 1, "已指定 --oom-at，但扫描窗口内各 OOM 块首行均无墙钟时间，全文退回为最后一次 OOM 块。"
    best_i, best_dt = min(usable, key=lambda x: abs((x[1] - anchor).total_seconds()))
    return best_i, None


def _full_log_indices(n_blocks: int, max_full: int, primary: int) -> List[int]:
    if max_full <= 0 or n_blocks == 0:
        return []
    start = max(0, primary - max_full + 1)
    return list(range(start, primary + 1))


def _similar_oom_group_key(s: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """
    强分组：scope_hint + killed_comm + cgroup 路径（cgroup 优先，否则 parent）+ 本地小时桶。
    无墙钟时小时桶为 __no_wallclock__（同类仍可按 scope/comm/cg 合并）。
    """
    scope = str(s.get("scope_hint") or "unknown")
    comm = str(s.get("killed_comm") or "")
    cg = str(s.get("cgroup") or s.get("parent_cgroup") or "")
    ps = s.get("parsed_start_local")
    if ps:
        try:
            dt = datetime.fromisoformat(str(ps))
            hour = dt.replace(minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        except ValueError:
            hour = "__no_wallclock__"
    else:
        hour = "__no_wallclock__"
    return (scope, comm, cg, hour)


def _collapse_similar_oom_summaries(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """同组仅保留时间上最后一条（按扫描顺序 / event_index），并写入 similar_oom_count。"""
    reps: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for s in summaries:
        k = _similar_oom_group_key(s)
        if k not in reps:
            reps[k] = {**s, "similar_oom_count": 1}
        else:
            old = reps[k]
            reps[k] = {**s, "similar_oom_count": int(old.get("similar_oom_count", 1)) + 1}
    return sorted(reps.values(), key=lambda x: int(x.get("event_index", 0)))


def analyze_oom_local(
    *,
    max_lines: int = 4000,
    max_event_summaries: int = 64,
    max_full_oom_logs: int = 1,
    oom_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    本机 OOM quick：按块边界解析；oom_events_summary 为轻量摘要（先按
    scope_hint、killed_comm、cgroup 路径与**同一本地小时**折叠同类，每组只保留最近一条并带
    similar_oom_count，再取最近至多 max_event_summaries 条）。
    oom_digest 为结构化关键字段（默认仅最近一次，可用 oom_at 锚定最近墙钟块）。
    无块时退回宽松单行匹配。
    """
    anchor = parse_oom_at_anchor(oom_at)

    empty: Dict[str, Any] = {
        "hit_count": 0,
        "oom_event_count": 0,
        "oom_lines_total": None,
        "extraction_mode": "none",
        "oom_events_summary": [],
        "oom_digest": [],
        "time_range": None,
        "histogram_hour_local": [],
        "parsed_time_count": 0,
        "unparsed_wallclock_count": 0,
        "dmesg_relative_line_count": 0,
        "relative_boot_seconds_sample": [],
        "source_note_zh": "未在扫描窗口内匹配到 OOM / oom-killer 相关行。",
    }

    tail = _kernel_tail_lines(max_lines)
    if not tail:
        return dict(empty)

    blocks = extract_oom_blocks(tail)
    extraction_mode = "sysak_blocks" if blocks else "loose_lines"

    if blocks:
        n_events = len(blocks)
        n_lines = sum(len(b["lines"]) for b in blocks)
        parsed_dts: List[datetime] = []
        relative_secs: List[float] = []
        unparsed_first = 0
        block_wallclock: List[Optional[datetime]] = []

        for b in blocks:
            first = b["lines"][0] if b["lines"] else ""
            dt, _src = _parse_oom_line_time(first)
            block_wallclock.append(dt)
            if dt is not None:
                parsed_dts.append(dt)
            elif _src.startswith("dmesg_relative_s:"):
                try:
                    relative_secs.append(float(_src.split(":", 1)[1]))
                except (ValueError, IndexError):
                    unparsed_first += 1
            else:
                unparsed_first += 1

        primary, anchor_note = _pick_primary_block_index(block_wallclock, anchor=anchor)
        idx_full = _full_log_indices(n_events, max_full_oom_logs, primary)
        oom_digest = [extract_oom_digest(blocks[i]) for i in idx_full]

        summaries_all: List[Dict[str, Any]] = []
        for i, b in enumerate(blocks):
            dt_b, _ = _block_start_dt(b["lines"])
            first_line = b["lines"][0] if b["lines"] else ""
            summaries_all.append(
                {
                    "event_index": i,
                    "parsed_start_local": dt_b.isoformat(timespec="seconds") if dt_b else None,
                    "line_count": len(b["lines"]),
                    "cgroup": b.get("cgroup") or None,
                    "parent_cgroup": b.get("parent_cgroup") or None,
                    "scope_hint": _scope_hint_from_block(b),
                    "killed_comm": _killed_comm_from_lines(b["lines"]),
                    "incomplete": bool(b.get("incomplete", False)),
                    "first_line_preview": (first_line[:240] + "…") if len(first_line) > 240 else first_line,
                }
            )

        collapsed = _collapse_similar_oom_summaries(summaries_all)
        oom_events_summary = collapsed[-max_event_summaries:] if collapsed else []

        hour_counter: Counter[str] = Counter()
        for dt in parsed_dts:
            buck = dt.replace(minute=0, second=0, microsecond=0)
            hour_counter[buck.isoformat(timespec="seconds")] += 1

        histogram = [{"bucket_start_local": k, "count": v} for k, v in sorted(hour_counter.items())]
        time_range = None
        if parsed_dts:
            mn, mx = min(parsed_dts), max(parsed_dts)
            time_range = {
                "first_seen_local": mn.isoformat(timespec="seconds"),
                "last_seen_local": mx.isoformat(timespec="seconds"),
            }

        note_parts = [
            f"扫描内核日志尾部至多 {max_lines} 行；按 sysAK oomcheck 块解析到 {n_events} 次完整 OOM（共 {n_lines} 行内核文本）；"
            f"摘要先按同类（scope/comm/cgroup/小时）折叠为 {len(collapsed)} 条，再保留最近 {len(oom_events_summary)} 条（上限 {max_event_summaries}）；"
            f"oom_digest 含 {len(oom_digest)} 条结构化摘要（上限 {max_full_oom_logs}"
            + ("，按 --oom-at 锚定最近墙钟块" if anchor is not None else "，默认以最近一次为主")
            + "）。"
            f"{len(parsed_dts)} 次在块首行解析到墙钟；{len(relative_secs)} 次块首为 dmesg 相对启动秒；{unparsed_first} 次块首无墙钟。"
        ]
        if anchor_note:
            note_parts.append(anchor_note)
        if relative_secs and not parsed_dts:
            note_parts.append(" 仅相对启动时间时按小时曲线为空，可换用 journal 或 dmesg -T。")

        return {
            "hit_count": n_events,
            "oom_event_count": n_events,
            "oom_lines_total": n_lines,
            "extraction_mode": extraction_mode,
            "oom_events_summary": oom_events_summary,
            "oom_digest": oom_digest,
            "time_range": time_range,
            "histogram_hour_local": histogram,
            "parsed_time_count": len(parsed_dts),
            "unparsed_wallclock_count": unparsed_first,
            "dmesg_relative_line_count": len(relative_secs),
            "relative_boot_seconds_sample": relative_secs[-8:] if relative_secs else [],
            "source_note_zh": "".join(note_parts),
        }

    hits = _oom_loose_line_hits(tail)
    n = len(hits)
    if n == 0:
        return dict(empty)

    parsed_dts = []
    relative_secs = []
    unparsed_wall = 0
    hit_dts: List[Optional[datetime]] = []
    for ln in hits:
        dt, src = _parse_oom_line_time(ln)
        hit_dts.append(dt)
        if dt is not None:
            parsed_dts.append(dt)
        elif src.startswith("dmesg_relative_s:"):
            try:
                relative_secs.append(float(src.split(":", 1)[1]))
            except (ValueError, IndexError):
                unparsed_wall += 1
        else:
            unparsed_wall += 1

    primary, anchor_note = _pick_primary_block_index(hit_dts, anchor=anchor)
    idx_full = _full_log_indices(n, max_full_oom_logs, primary)
    oom_digest = [{"raw_line": hits[i]} for i in idx_full]

    summaries_all = []
    for i, ln in enumerate(hits):
        dt_b, _ = _parse_oom_line_time(ln)
        summaries_all.append(
            {
                "event_index": i,
                "parsed_start_local": dt_b.isoformat(timespec="seconds") if dt_b else None,
                "line_count": 1,
                "cgroup": None,
                "parent_cgroup": None,
                "scope_hint": "unknown",
                "killed_comm": _killed_comm_from_lines([ln]),
                "incomplete": False,
                "first_line_preview": (ln[:240] + "…") if len(ln) > 240 else ln,
            }
        )
    collapsed = _collapse_similar_oom_summaries(summaries_all)
    oom_events_summary = collapsed[-max_event_summaries:] if collapsed else []

    hour_counter = Counter()
    for dt in parsed_dts:
        b = dt.replace(minute=0, second=0, microsecond=0)
        hour_counter[b.isoformat(timespec="seconds")] += 1

    histogram = [{"bucket_start_local": k, "count": v} for k, v in sorted(hour_counter.items())]
    time_range = None
    if parsed_dts:
        mn, mx = min(parsed_dts), max(parsed_dts)
        time_range = {
            "first_seen_local": mn.isoformat(timespec="seconds"),
            "last_seen_local": mx.isoformat(timespec="seconds"),
        }

    note_parts = [
        f"扫描尾部 {max_lines} 行：未形成 invoked oom-killer 起点的完整块，退回宽松匹配共 {n} 条相关行；"
        f"摘要先折叠为 {len(collapsed)} 条，再保留最近 {len(oom_events_summary)} 条（上限 {max_event_summaries}），"
        f"oom_digest {len(oom_digest)} 条（上限 {max_full_oom_logs}）。"
        f"{len(parsed_dts)} 条解析到墙钟，{len(relative_secs)} 条相对启动秒，{unparsed_wall} 条无时间。"
    ]
    if anchor_note:
        note_parts.append(anchor_note)
    if relative_secs and not parsed_dts:
        note_parts.append(" 仅相对启动时间时按小时曲线为空。")

    return {
        "hit_count": n,
        "oom_event_count": 0,
        "oom_lines_total": None,
        "extraction_mode": extraction_mode,
        "oom_events_summary": oom_events_summary,
        "oom_digest": oom_digest,
        "time_range": time_range,
        "histogram_hour_local": histogram,
        "parsed_time_count": len(parsed_dts),
        "unparsed_wallclock_count": unparsed_wall,
        "dmesg_relative_line_count": len(relative_secs),
        "relative_boot_seconds_sample": relative_secs[-8:] if relative_secs else [],
        "source_note_zh": "".join(note_parts),
    }
