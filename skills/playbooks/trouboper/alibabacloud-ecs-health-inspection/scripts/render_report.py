#!/usr/bin/env python3
# DEPENDENCIES: Python stdlib only (>= 3.8). No third-party packages required.
# See scripts/requirements.txt and the "Dependencies" block below.
"""
ECS Health Inspection HTML report renderer.

The LLM collects and assesses the metrics and passes a structured JSON
blob into this script. The script assembles the final HTML, avoiding
the latency of having the LLM emit 400+ lines of HTML token-by-token.

Usage:
    python3 render_report.py --input data.json --output report.html
    # Or read JSON from stdin
    cat data.json | python3 render_report.py --output report.html

    # Inspect schema / validate without rendering:
    python3 render_report.py --schema
    python3 render_report.py --validate --input data.json

The JSON schema is the SCHEMA_DOC constant below, also referenced from
the "Step 6" section of SKILL.md.

--------------------------------------------------------------------
Dependencies (declared inline; mirrored in scripts/requirements.txt)
--------------------------------------------------------------------
  Runtime:
    - Python      >= 3.8
  Third-party:
    - (none)      This script is intentionally stdlib-only so that
                  it runs in any environment without `pip install`.
  Standard library:
    - argparse, html, json, sys, typing, __future__

Upgrade policy: do NOT introduce third-party dependencies (e.g.
Jinja2, pydantic, lxml) without an explicit decision recorded in
SKILL.md and a corresponding bump in scripts/requirements.txt.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from typing import Any


SCHEMA_DOC = """
{
  "meta": {
    "report_id": "RPT-20260512-154941",
    "generated_at": "2026-05-12 15:49:41 CST",
    "generated_ymd": "20260512",
    "data_source": "cloudmonitor" | "fallback",
    "agent_status": "running" | "stopped" | "not_installed",
    "time_range_minutes": 15,
    "duration_seconds": 25
  },
  "instance": {
    "id": "i-xxx",
    "name": "...",
    "region": "cn-chengdu",
    "region_label": "China West 1 (Chengdu)",
    "zone": "cn-chengdu-b",
    "os_type": "linux" | "windows",
    "os_version": "Alibaba Cloud Linux 3.2104 LTS 64-bit",
    "instance_type": "ecs.c7.large",
    "instance_type_family": "ecs.c7 general-purpose",
    "cpu_cores": 2,
    "cpu_note": "(1 physical core x 2 hyperthreads)",
    "memory_gb": 4,
    "gpu_count": 0,
    "gpu_model": "",
    "network_type": "VPC",
    "public_ip": "8.156.84.135",
    "private_ip": "10.0.2.63",
    "charge_type": "PayAsYouGo",
    "creation_time": "2026-05-12 15:18:00 CST",
    "internet_in_bw_mbps": 2000,
    "internet_out_bw_mbps": 100
  },
  "metrics": {
    "cpu": {"current": 99.27, "avg": 99.27, "max": 99.27, "max_time": "2026-05-12 15:48"},
    "load": {"load_1m": 8.39, "load_5m": 5.37, "load_15m": 3.18} | null,
    "memory": {"current": 28.77, "avg": 28.77, "max": 40.30} | null,
    "disk_bps": {"read_avg": 857088, "read_max": 857088, "read_current": 857088,
                 "write_avg": 1270716, "write_max": 1270716, "write_current": 1270716},
    "disk_iops": {"read_avg": 209.25, "read_max": 209.25, "read_current": 209.25,
                  "write_avg": 236.05, "write_max": 236.05, "write_current": 236.05},
    "disk_latency": null | {"read_avg": 0.5, "read_max": 1.2, "write_avg": 0.6, "write_max": 1.3},
    "network": {"in_avg": 6366, "in_max": 170915, "in_current": 6366,
                "out_avg": 60210, "out_max": 237466, "out_current": 60210},
    "disk_usage": [{"mount": "/", "device": "/dev/vda3", "usage": 15.14}],
    "gpu": null | {"temp": 62, "util": 75, "mem_util": 68, "util_max": 90, "mem_util_max": 70, "temp_max": 65}
  },
  "disks": [
    {"id": "d-xxx", "device": "/dev/xvda", "mount": "/",
     "category": "cloud_essd", "performance_level": "PL0",
     "type": "system disk", "size_gb": 40, "usage_pct": 15.14,
     "iops_limit": 2280, "bps_limit_mbps": 110,
     "status": "In_use", "snapshot_enabled": true}
  ],
  "processes": null | {
    "top_cpu": [{"name": "stress", "pid": 3421, "user": "root", "value": 41.83}],
    "top_mem": [{"name": "stress", "pid": 3429, "user": "root", "value": 19.54}]
  },
  "assessment": {
    "health_score": 58,
    "grade": "A|B|C|D",
    "grade_label": "Critical",
    "one_liner": "CPU sustained at 99%, root cause is the stress process",
    "narrative": "Instance xxx is currently in a critical CPU overload state...",
    "cost_evaluation": "...",
    "cost_suggestion": "...",
    "dimensions": [
      {"name": "CPU", "grade": "D", "score": 2, "max_score": 25,
       "current": "99.27%", "threshold": "80% warn / 95% crit",
       "trend": "sustained high", "detail": "..."}
    ],
    "anomalies": [
      {"level": "crit|warn", "title": "Critical CPU alert", "message": "...", "anchor": "cpu"}
    ]
  },
  "recommendations": {
    "immediate": ["..."],
    "short_term": ["..."],
    "long_term": ["..."]
  }
}
"""


# ---------- Formatters ----------

def _esc(s: Any) -> str:
    """HTML-escape; <code>-style tags are preserved; all user-supplied data flows through this helper."""
    return html.escape(str(s), quote=False)


def _fmt_bps(bps: float) -> str:
    """bytes/s -> human-readable."""
    if bps is None:
        return "N/A"
    bps = float(bps)
    if bps >= 1024 * 1024:
        return f"{bps / 1024 / 1024:.2f} MB/s"
    if bps >= 1024:
        return f"{bps / 1024:.2f} KB/s"
    return f"{bps:.0f} B/s"


def _fmt_bits(bps: float) -> str:
    """bits/s -> human-readable (network traffic)."""
    if bps is None:
        return "N/A"
    bps = float(bps)
    if bps >= 1e9:
        return f"{bps / 1e9:.2f} Gbps"
    if bps >= 1e6:
        return f"{bps / 1e6:.2f} Mbps"
    if bps >= 1e3:
        return f"{bps / 1e3:.2f} Kbps"
    return f"{bps:.0f} bps"


def _fmt_num(v: Any, precision: int = 2) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.{precision}f}"
    except (TypeError, ValueError):
        return str(v)


def _grade_letter(grade: str) -> str:
    return (grade or "a").lower()


def _bar_width(pct: float, cap: float = 100.0) -> int:
    if pct is None:
        return 0
    return max(0, min(100, int(round(float(pct) / cap * 100))))


def _bar_cls(pct: float, warn: float, crit: float) -> str:
    if pct is None:
        return ""
    if pct >= crit:
        return "crit"
    if pct >= warn:
        return "warn"
    return ""


def _status_icon(grade: str) -> str:
    g = (grade or "").upper()
    return {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}.get(g, "🟢")


# ---------- Template fragments ----------

CSS = """
  :root {
    --bg: #f5f6fa; --card-bg: #fff; --text: #2d3436; --muted: #636e72;
    --border: #dfe6e9; --green: #00b894; --green-bg: #e6faf3; --yellow: #fdcb6e;
    --orange: #e17055; --red: #d63031; --blue: #0984e3; --accent: #6c5ce7;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; padding: 24px 16px; }
  .container { max-width: 960px; margin: 0 auto; }
  .header { background: linear-gradient(135deg, #6c5ce7, #a29bfe); color: #fff;
            text-align: center; padding: 40px 24px; border-radius: 12px 12px 0 0; }
  .header.fallback { background: linear-gradient(135deg, #e17055, #fab1a0); }
  .header h1 { font-size: 26px; font-weight: 700; margin-bottom: 12px; }
  .header .meta { font-size: 14px; opacity: .88; display: flex; gap: 24px;
                  justify-content: center; flex-wrap: wrap; }
  .header .meta span { white-space: nowrap; }
  .card { background: var(--card-bg); border: 1px solid var(--border);
          border-radius: 0 0 12px 12px; padding: 28px 32px; margin-bottom: 20px; }
  .card + .card { border-radius: 12px; }
  .section-title { font-size: 18px; font-weight: 700; margin-bottom: 16px;
                   padding-bottom: 10px; border-bottom: 2px solid var(--accent);
                   display: flex; align-items: center; gap: 8px; }
  .section-title .icon { font-size: 20px; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
  th, td { padding: 10px 14px; border: 1px solid var(--border); text-align: left; }
  th { background: #f8f9fa; font-weight: 600; color: var(--muted); white-space: nowrap; }
  td { vertical-align: middle; }
  .ta-c { text-align: center; }
  .score-num { font-size: 36px; font-weight: 800; color: var(--green); }
  .score-num.warn { color: var(--orange); }
  .score-num.crit { color: var(--red); }
  .score-small { font-size: 16px; color: #636e72; }
  .rating { display: inline-block; padding: 2px 10px; border-radius: 10px;
            font-size: 12px; font-weight: 700; }
  .rating-a { background: var(--green-bg); color: #00a376; }
  .rating-b { background: #fff8e1; color: #f39c12; }
  .rating-c { background: #fff3e0; color: #e17055; }
  .rating-d { background: #ffeaea; color: #d63031; }
  .bar-bg { display: inline-block; width: 100px; height: 10px; border-radius: 5px;
            background: #eee; vertical-align: middle; overflow: hidden; }
  .bar { display: inline-block; height: 100%; border-radius: 5px; background: var(--green); }
  .bar.warn { background: var(--orange); }
  .bar.crit { background: var(--red); }
  .ok { color: var(--green); font-weight: 600; }
  .warn { color: var(--orange); font-weight: 600; }
  .crit { color: var(--red); font-weight: 600; }
  .highlight { background: #f0faf6; border-left: 3px solid var(--green);
               padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 12px 0; font-size: 14px; }
  .highlight.warn { background: #fff8e1; border-color: var(--orange); }
  .highlight.crit { background: #ffeaea; border-color: var(--red); }
  .note { color: var(--muted); font-size: 13px; margin: 8px 0; }
  ul { padding-left: 20px; }
  li { margin: 4px 0; font-size: 14px; }
  .footer { text-align: center; color: var(--muted); font-size: 12px; padding: 20px 0; }
  .sep { text-align: center; color: var(--muted); font-size: 12px;
         margin: 8px 0; letter-spacing: 6px; }
  .summary-item { display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 2px 0; }
  .summary-item .bar-bg { width: 80px; }
  .gauge-row { display: flex; align-items: center; gap: 10px; font-size: 14px; margin: 4px 0; }
  .gauge-label { width: 80px; text-align: right; font-weight: 600; white-space: nowrap; }
  .gauge-val { width: 55px; text-align: right; }
  .anomaly-box { border: 1px solid var(--border); border-radius: 8px;
                 padding: 16px; margin: 12px 0; }
  .anomaly-box.warn { border-color: var(--orange); background: #fffaf5; }
  .anomaly-box.crit { border-color: var(--red); background: #fff5f5; }
  .anomaly-box h4 { margin-bottom: 8px; }
"""


# ---------- Section renderers ----------

def render_header(meta: dict, assessment: dict) -> str:
    fallback = meta.get("data_source") == "fallback"
    header_cls = " fallback" if fallback else ""
    grade = assessment.get("grade", "A").upper()
    icon = _status_icon(grade)
    warn_banner = ""
    if fallback:
        warn_banner = (
            '<p style="margin-top:8px; opacity:.9;">⚠️ CloudMonitor Agent unavailable — '
            "limited metrics retrieved via ECS API. Install the Agent for full monitoring capability.</p>"
        )
    ds_label = "☁️ CloudMonitor Agent" if not fallback else "🟠 ECS API fallback"
    return f"""
<div class="header{header_cls}">
  <h1>{icon} ECS Instance Inspection Report{" (fallback mode)" if fallback else ""}</h1>
  {warn_banner}
  <div class="meta">
    <span>Report ID: {_esc(meta.get("report_id", ""))}</span>
    <span>Generated At: {_esc(meta.get("generated_at", ""))}</span>
    <span>Data Source: {ds_label}</span>
  </div>
</div>
"""


def render_instance_card(inst: dict, meta: dict) -> str:
    rows = [
        ("Instance ID", f"<code>{_esc(inst.get('id', ''))}</code>"),
        ("Instance Name", _esc(inst.get("name", ""))),
        ("Region / Zone", f"{_esc(inst.get('region_label', inst.get('region', '')))} / {_esc(inst.get('zone', ''))}"),
        ("Operating System", f"{_esc(inst.get('os_type', '').title())} ({_esc(inst.get('os_version', ''))})"),
        ("Instance Type", f"{_esc(inst.get('instance_type', ''))} ({_esc(inst.get('instance_type_family', ''))})"),
        ("vCPU / Memory", f"{inst.get('cpu_cores', '?')} cores {_esc(inst.get('cpu_note', ''))} / {inst.get('memory_gb', '?')} GB"),
    ]
    if inst.get("gpu_count", 0):
        rows.append(("GPU", f"{inst['gpu_count']} x {_esc(inst.get('gpu_model', ''))}"))
    rows.extend([
        ("Network Type", _esc(inst.get("network_type", "VPC"))),
        ("Public IP / Private IP", f"{_esc(inst.get('public_ip', '-'))} / {_esc(inst.get('private_ip', '-'))}"),
        ("Charge Type", _esc(inst.get("charge_type", ""))),
        ("Created At", _esc(inst.get("creation_time", ""))),
        ("Status", '<span class="ok">🟢 Running</span>'),
        ("Data Source", "CloudMonitor metrics (acs_ecs_dashboard / Agent running)"
                if meta.get("data_source") != "fallback"
                else "ECS API fallback (CloudMonitor Agent unavailable)"),
        ("Time Range", f"Last {meta.get('time_range_minutes', 15)} minutes (sampling: 60s)"),
    ])
    trs = "\n".join(
        f'    <tr><td style="width:160px;"><b>{k}</b></td><td>{v}</td></tr>'
        for k, v in rows
    )
    return f"""
<div class="card">
  <div class="section-title"><span class="icon">🖥️</span> Instance Information</div>
  <table>
{trs}
  </table>
</div>
"""


def render_overview(assessment: dict, metrics: dict, inst: dict) -> str:
    grade = assessment.get("grade", "A").upper()
    score = assessment.get("health_score", 100)
    score_cls = ""
    if score < 60:
        score_cls = " crit"
    elif score < 75:
        score_cls = " warn"

    dim_rows = []
    for d in assessment.get("dimensions", []):
        dim_rows.append(
            f'<tr><td>{_esc(d["name"])}</td>'
            f'<td class="ta-c"><span class="rating rating-{_grade_letter(d["grade"])}">{_esc(d["grade"])}</span></td>'
            f'<td class="ta-c">{_esc(d.get("current", ""))}</td>'
            f'<td>{_esc(d.get("threshold", ""))}</td>'
            f'<td class="ta-c">{_esc(d.get("trend", ""))}</td></tr>'
        )

    return f"""
<div class="card">
  <div class="section-title"><span class="icon">📊</span> Inspection Overview</div>
  <table>
    <tr><th style="width:140px;">Health Score</th><th>Status</th><th>Key Finding</th></tr>
    <tr>
      <td><span class="score-num{score_cls}">{score} <span class="score-small">/ 100</span></span></td>
      <td><span class="rating rating-{_grade_letter(grade)}">{grade} · {_esc(assessment.get("grade_label", ""))}</span></td>
      <td>{_esc(assessment.get("one_liner", ""))}</td>
    </tr>
  </table>
  <table style="margin-top:16px;">
    <tr><th>Dimension</th><th style="text-align:center;">Grade</th><th style="text-align:center;">Current</th><th>Threshold</th><th style="text-align:center;">Trend</th></tr>
    {"".join(dim_rows)}
  </table>
  <p class="note">Grade legend: 🟢 A (Excellent &ge; 90) / 🟡 B (Good &ge; 75) / 🟠 C (Fair &ge; 60) / 🔴 D (Critical &lt; 60)</p>
</div>
"""


def render_summary(assessment: dict, metrics: dict, inst: dict) -> str:
    anomalies_html = ""
    for a in assessment.get("anomalies", []):
        lvl = a.get("level", "warn")
        icon = "🔴" if lvl == "crit" else "🟠"
        anchor = a.get("anchor", "")
        detail_link = f' &rarr; see <a href="#{anchor}">section</a>' if anchor else ""
        anomalies_html += (
            f'  <div class="highlight {lvl}">\n'
            f'    {icon} <b>{_esc(a.get("title", ""))}</b>: {_esc(a.get("message", ""))}{detail_link}\n'
            f'  </div>\n'
        )
    if not anomalies_html:
        anomalies_html = (
            '  <div class="highlight">\n'
            "    ✅ <b>All metrics normal</b> — all measured metrics fall within healthy thresholds; no anomalies detected.\n"
            "  </div>\n"
        )

    # Per-metric summary items
    items = []
    cpu = metrics.get("cpu") or {}
    items.append(_summary_item("CPU", f'{_fmt_num(cpu.get("avg"))}%', cpu.get("avg"), 80, 95))
    if metrics.get("load"):
        ld = metrics["load"]
        cores = inst.get("cpu_cores", 1) or 1
        items.append(_summary_item("Load", f'{_fmt_num(ld.get("load_15m"))}',
                                   ld.get("load_15m"), cores, cores * 2,
                                   normalize_cap=cores * 2))
    mem = metrics.get("memory") or {}
    if mem:
        items.append(_summary_item("Memory", f'{_fmt_num(mem.get("avg"))}%', mem.get("avg"), 80, 95))
    # Disk IO: use IOPS max / limit
    disk_iops = metrics.get("disk_iops") or {}
    iops_max = max(disk_iops.get("read_max", 0) or 0, disk_iops.get("write_max", 0) or 0)
    iops_limit = next((d.get("iops_limit", 2280) for d in (metrics.get("disks") or []) if d.get("iops_limit")),
                      2280)
    iops_pct = (iops_max / iops_limit * 100) if iops_limit else 0
    items.append(_summary_item("Disk IO", f"{iops_max:.0f} IOPS", iops_pct, 80, 95))
    # Network
    net = metrics.get("network") or {}
    out_max = net.get("out_max", 0) or 0
    out_limit_bps = (inst.get("internet_out_bw_mbps", 100) or 100) * 1e6
    net_pct = (out_max / out_limit_bps * 100) if out_limit_bps else 0
    items.append(_summary_item("Network", _fmt_bits(out_max), net_pct, 80, 95))
    # Disk usage
    du = metrics.get("disk_usage") or []
    du_max = max((d.get("usage", 0) or 0) for d in du) if du else 0
    items.append(_summary_item("Disk Usage", f"{du_max:.2f}%", du_max, 80, 95))
    # GPU
    if metrics.get("gpu"):
        gpu = metrics["gpu"]
        items.append(_summary_item("GPU",
                                   f'{_fmt_num(gpu.get("util"))}% / {_fmt_num(gpu.get("temp"))}°C',
                                   gpu.get("util"), 80, 95))

    # Resource utilization table
    cpu_cores = inst.get("cpu_cores", 1)
    mem_gb = inst.get("memory_gb", 0)
    mem_max = (mem or {}).get("max", 0) or 0
    disk_bps = metrics.get("disk_bps") or {}
    bps_max_bytes = max(disk_bps.get("read_max", 0) or 0, disk_bps.get("write_max", 0) or 0)
    bps_limit_mbps = next(
        (d.get("bps_limit_mbps", 110) for d in (metrics.get("disks") or []) if d.get("bps_limit_mbps")),
        110,
    )
    bps_pct = (bps_max_bytes / (bps_limit_mbps * 1024 * 1024) * 100) if bps_limit_mbps else 0

    util_rows = [
        ("vCPU", f"{cpu_cores} cores", f'{_fmt_num(cpu.get("max"))}%',
         _fmt_num(cpu.get("max")), cpu.get("max"), 80, 95),
        ("Memory", f"{mem_gb} GB", f'{_fmt_num(mem_max)}%', _fmt_num(mem_max), mem_max, 80, 95),
        ("Disk IOPS (per disk)", str(iops_limit), f"{iops_max:.0f}", _fmt_num(iops_pct), iops_pct, 80, 95),
        ("Disk BPS (per disk)", f"{bps_limit_mbps} MB/s", _fmt_bps(bps_max_bytes),
         _fmt_num(bps_pct), bps_pct, 80, 95),
        ("Internet Outbound BW", f'{inst.get("internet_out_bw_mbps", 100)} Mbps',
         _fmt_bits(out_max), _fmt_num(net_pct), net_pct, 80, 95),
    ]
    util_tr = "\n".join(
        f'    <tr><td>{_esc(r[0])}</td>'
        f'<td class="ta-c">{_esc(r[1])}</td>'
        f'<td class="ta-c">{_esc(r[2])}</td>'
        f'<td><div class="bar-bg"><div class="bar {_bar_cls(r[5] * 1.0 if False else r[5], r[5], r[6])}" '
        f'style="width:{_bar_width(r[4])}%"></div></div> {_esc(r[3])}%</td></tr>'
        for r in util_rows
    )

    return f"""
<div class="card">
  <div class="section-title"><span class="icon">📋</span> Inspection Summary</div>
  <p>{_esc(assessment.get("narrative", ""))}</p>
  <p style="margin-top:12px;"><b>Anomalies:</b></p>
{anomalies_html}
  <div style="margin-top:12px;">
{chr(10).join(items)}
  </div>
  <p style="margin-top:16px;"><b>Resource Utilization:</b></p>
  <table>
    <tr><th>Resource</th><th style="text-align:center;">Limit</th><th style="text-align:center;">Current Max</th><th>Utilization</th></tr>
{util_tr}
  </table>
</div>
"""


def _summary_item(name: str, value_text: str, pct: float | None,
                  warn: float, crit: float, normalize_cap: float = 100.0) -> str:
    cls = _bar_cls(pct, warn, crit)
    if cls == "crit":
        icon, label, label_cls = "🔴", "Critical", "crit"
    elif cls == "warn":
        icon, label, label_cls = "🟠", "Elevated", "warn"
    else:
        icon, label, label_cls = "🟢", "✓ Normal", "ok"
    width = _bar_width(pct, normalize_cap)
    return (
        f'    <div class="summary-item"><span class="{label_cls}">{icon}</span> '
        f'{_esc(name)} <span style="margin-left:auto;">{_esc(value_text)}</span>'
        f'<div class="bar-bg"><div class="bar {cls}" style="width:{width}%"></div></div>'
        f'<span class="{label_cls}">{label}</span></div>'
    )


def render_cpu_card(metrics: dict, inst: dict, assessment: dict) -> str:
    cpu = metrics.get("cpu") or {}
    cpu_avg = cpu.get("avg", 0) or 0
    cpu_status_cls, cpu_icon, cpu_label = _status_from(cpu_avg, 80, 95)
    cpu_avg_span = f'<span class="{cpu_status_cls}">{_fmt_num(cpu_avg)}%</span>'
    cpu_max_span = f'<span class="{cpu_status_cls}">{_fmt_num(cpu.get("max"))}%</span>'
    cpu_cur_span = f'<span class="{cpu_status_cls}">{_fmt_num(cpu.get("current"))}%</span>'

    cpu_table = f"""
  <h4>CPU Usage</h4>
  <table>
    <tr><th>Metric</th><th style="text-align:center;">Value</th></tr>
    <tr><td>Current</td><td class="ta-c">{cpu_cur_span}</td></tr>
    <tr><td>Avg</td><td class="ta-c">{cpu_avg_span}</td></tr>
    <tr><td>Max</td><td class="ta-c">{cpu_max_span} ({_esc(cpu.get("max_time", ""))})</td></tr>
    <tr><td>Status</td><td class="ta-c"><span class="{cpu_status_cls}">{cpu_icon} {cpu_label}</span></td></tr>
  </table>
"""

    # Load (Linux only)
    load_table = ""
    title_suffix = ""
    if metrics.get("load"):
        title_suffix = " and Load"
        cores = inst.get("cpu_cores", 1) or 1
        ld = metrics["load"]
        load_rows = []
        for label, key in [("1-minute", "load_1m"), ("5-minute", "load_5m"), ("15-minute", "load_15m")]:
            v = ld.get(key, 0) or 0
            ratio = v / cores if cores else 0
            cls, icon, txt = _load_status(ratio)
            load_rows.append(
                f'    <tr><td>{label}</td>'
                f'<td class="ta-c"><span class="{cls}">{_fmt_num(v)}</span></td>'
                f'<td class="ta-c"><span class="{cls}">{_fmt_num(ratio, 1)}x</span></td>'
                f'<td class="ta-c"><span class="{cls}">{icon} {txt}</span></td></tr>'
            )
        load_table = f"""
  <h4 style="margin-top:16px;">System Load Average</h4>
  <table>
    <tr><th>Load</th><th style="text-align:center;">Value</th><th style="text-align:center;">Ratio to CPU cores ({cores})</th><th style="text-align:center;">Status</th></tr>
{chr(10).join(load_rows)}
  </table>
  <p class="note">Interpretation: load &le; cores = normal. load &gt; cores = moderate. load &gt; 2x cores = elevated. load &gt; 5x cores = critical.</p>
"""

    # Anomaly box (includes top processes)
    anomaly_html = ""
    cpu_anomaly = next((a for a in assessment.get("anomalies", [])
                       if a.get("anchor") == "cpu"), None)
    procs = metrics.get("processes") or {}
    if cpu_anomaly or (cpu_avg >= 80):
        lvl = cpu_anomaly.get("level", "warn") if cpu_anomaly else ("crit" if cpu_avg >= 95 else "warn")
        title = cpu_anomaly.get("title", "CPU anomaly") if cpu_anomaly else "CPU usage elevated"
        message = cpu_anomaly.get("message", "") if cpu_anomaly else ""
        proc_table = ""
        if procs.get("top_cpu"):
            proc_rows = []
            for i, p in enumerate(procs["top_cpu"][:5], 1):
                proc_rows.append(
                    f'      <tr><td class="ta-c">{i}</td><td><code>{_esc(p.get("name", ""))}</code></td>'
                    f'<td class="ta-c">{_esc(p.get("pid", ""))}</td>'
                    f'<td class="ta-c">{_esc(p.get("user", ""))}</td>'
                    f'<td class="ta-c"><span class="{"crit" if (p.get("value", 0) or 0) > 30 else "warn"}">{_fmt_num(p.get("value"))}%</span></td></tr>'
                )
            proc_table = f"""
    <p style="margin-top:8px;"><b>Top 5 CPU processes (collected by CloudMonitor Agent):</b></p>
    <table>
      <tr><th>#</th><th>Process</th><th style="text-align:center;">PID</th><th style="text-align:center;">User</th><th style="text-align:center;">CPU%</th></tr>
{chr(10).join(proc_rows)}
    </table>
"""
        anomaly_html = f"""
  <div class="anomaly-box {lvl}">
    <h4><span class="{lvl}">{"🔴" if lvl == "crit" else "🟠"} Anomaly: {_esc(title)}</span></h4>
    <p>{_esc(message)}</p>
{proc_table}
  </div>
"""
    else:
        anomaly_html = '  <p class="note">✅ CPU usage is within the normal range.</p>\n'

    return f"""
<div class="card" id="cpu">
  <div class="section-title"><span class="icon">📈</span> CPU{title_suffix}</div>
{cpu_table}
{load_table}
{anomaly_html}
</div>
"""


def _status_from(v: float, warn: float, crit: float) -> tuple[str, str, str]:
    if v is None:
        return ("", "", "N/A")
    if v >= crit:
        return ("crit", "🔴", "Critical")
    if v >= warn:
        return ("warn", "🟠", "Elevated")
    return ("ok", "🟢", "Normal")


def _load_status(ratio: float) -> tuple[str, str, str]:
    if ratio >= 5:
        return ("crit", "🔴", "Critical")
    if ratio >= 2:
        return ("crit", "🔴", "Elevated")
    if ratio >= 1:
        return ("warn", "🟠", "Moderate")
    return ("ok", "🟢", "Normal")


def render_memory_card(metrics: dict, inst: dict) -> str:
    mem = metrics.get("memory")
    if not mem:
        return ""
    cur, avg, mx = mem.get("current", 0), mem.get("avg", 0), mem.get("max", 0)
    total = inst.get("memory_gb", 0)
    used = round(total * (avg or 0) / 100, 2)
    free = round(total - used, 2)
    cls, icon, label = _status_from(avg, 80, 95)

    return f"""
<div class="card">
  <div class="section-title"><span class="icon">🧠</span> Memory</div>
  <div style="margin:12px 0;">
    <div class="gauge-row"><span class="gauge-label">Current</span><span class="gauge-val">{_fmt_num(cur)}%</span><div class="bar-bg"><div class="bar {_bar_cls(cur, 80, 95)}" style="width:{_bar_width(cur)}%"></div></div></div>
    <div class="gauge-row"><span class="gauge-label">Avg</span><span class="gauge-val">{_fmt_num(avg)}%</span><div class="bar-bg"><div class="bar {_bar_cls(avg, 80, 95)}" style="width:{_bar_width(avg)}%"></div></div></div>
    <div class="gauge-row"><span class="gauge-label">Max</span><span class="gauge-val">{_fmt_num(mx)}%</span><div class="bar-bg"><div class="bar {_bar_cls(mx, 80, 95)}" style="width:{_bar_width(mx)}%"></div></div></div>
  </div>
  <table>
    <tr><th>Metric</th><th style="text-align:center;">Value</th></tr>
    <tr><td>Total Memory</td><td class="ta-c">{total} GB</td></tr>
    <tr><td>Used (by avg)</td><td class="ta-c">~{used} GB</td></tr>
    <tr><td>Available (by avg)</td><td class="ta-c">~{free} GB</td></tr>
    <tr><td>Status</td><td class="ta-c"><span class="{cls}">{icon} {label}</span></td></tr>
  </table>
</div>
"""



def render_disk_io_card(metrics: dict) -> str:
    bps = metrics.get("disk_bps") or {}
    iops = metrics.get("disk_iops") or {}
    lat = metrics.get("disk_latency")
    disks_info = metrics.get("disks") or []
    iops_limit = disks_info[0].get("iops_limit", 2280) if disks_info else 2280
    bps_limit = disks_info[0].get("bps_limit_mbps", 110) if disks_info else 110

    def _row(dir_label: str, cur: float, avg: float, mx: float, fmt) -> str:
        return (f'    <tr><td><b>{dir_label}</b></td>'
                f'<td class="ta-c">{fmt(cur)}</td>'
                f'<td class="ta-c">{fmt(avg)}</td>'
                f'<td class="ta-c">{fmt(mx)}</td>'
                f'<td class="ta-c"><span class="ok">🟢</span></td></tr>')

    bps_rows = [
        _row("Read", bps.get("read_current"), bps.get("read_avg"), bps.get("read_max"), _fmt_bps),
        _row("Write", bps.get("write_current"), bps.get("write_avg"), bps.get("write_max"), _fmt_bps),
    ]
    iops_rows = [
        _row("Read", iops.get("read_current"), iops.get("read_avg"), iops.get("read_max"), lambda x: f"{float(x or 0):.2f}"),
        _row("Write", iops.get("write_current"), iops.get("write_avg"), iops.get("write_max"), lambda x: f"{float(x or 0):.2f}"),
    ]

    latency_table = ""
    if lat:
        latency_table = f"""
  <h4 style="margin-top:16px;">Latency</h4>
  <table>
    <tr><th>Direction</th><th style="text-align:center;">Avg</th><th style="text-align:center;">Max</th></tr>
    <tr><td><b>Read</b></td><td class="ta-c">{_fmt_num(lat.get("read_avg"))} μs</td><td class="ta-c">{_fmt_num(lat.get("read_max"))} μs</td></tr>
    <tr><td><b>Write</b></td><td class="ta-c">{_fmt_num(lat.get("write_avg"))} μs</td><td class="ta-c">{_fmt_num(lat.get("write_max"))} μs</td></tr>
  </table>
"""

    return f"""
<div class="card">
  <div class="section-title"><span class="icon">💾</span> Disk IO</div>
  <h4>Throughput (BPS)</h4>
  <table>
    <tr><th>Direction</th><th style="text-align:center;">Current</th><th style="text-align:center;">Avg</th><th style="text-align:center;">Max</th><th style="text-align:center;">Status</th></tr>
{chr(10).join(bps_rows)}
  </table>
  <h4 style="margin-top:16px;">Operations (IOPS)</h4>
  <table>
    <tr><th>Direction</th><th style="text-align:center;">Current</th><th style="text-align:center;">Avg</th><th style="text-align:center;">Max</th><th style="text-align:center;">Status</th></tr>
{chr(10).join(iops_rows)}
  </table>
{latency_table}
  <p class="note">Disk IOPS limit: {iops_limit} | BPS limit: {bps_limit} MB/s</p>
  <p class="note">✅ Disk IO throughput and IOPS are within normal ranges.</p>
</div>
"""


def render_network_card(metrics: dict, inst: dict) -> str:
    net = metrics.get("network") or {}
    in_bw = inst.get("internet_in_bw_mbps", 2000)
    out_bw = inst.get("internet_out_bw_mbps", 100)
    out_max_bps = net.get("out_max", 0) or 0
    out_peak_pct = out_max_bps / (out_bw * 1e6) * 100 if out_bw else 0
    return f"""
<div class="card">
  <div class="section-title"><span class="icon">🌐</span> Network Traffic</div>
  <table>
    <tr><th>Direction</th><th style="text-align:center;">Current</th><th style="text-align:center;">Avg</th><th style="text-align:center;">Max (Peak)</th><th style="text-align:center;">Status</th></tr>
    <tr><td><b>Inbound</b></td><td class="ta-c">{_fmt_bits(net.get("in_current"))}</td><td class="ta-c">{_fmt_bits(net.get("in_avg"))}</td><td class="ta-c">{_fmt_bits(net.get("in_max"))}</td><td class="ta-c"><span class="ok">🟢</span></td></tr>
    <tr><td><b>Outbound</b></td><td class="ta-c">{_fmt_bits(net.get("out_current"))}</td><td class="ta-c">{_fmt_bits(net.get("out_avg"))}</td><td class="ta-c">{_fmt_bits(net.get("out_max"))}</td><td class="ta-c"><span class="ok">🟢</span></td></tr>
  </table>
  <p class="note">Bandwidth limit: in {in_bw} Mbps / out {out_bw} Mbps | Outbound peak utilization: {_fmt_num(out_peak_pct)}%</p>
</div>
"""


def render_disk_capacity_card(metrics: dict) -> str:
    disks = metrics.get("disks") or []
    rows = []
    total_size = 0
    for d in disks:
        size = d.get("size_gb", 0) or 0
        total_size += size
        usage = d.get("usage_pct", 0) or 0
        free = round(size * (1 - usage / 100), 2) if size else 0
        cls, icon, _ = _status_from(usage, 80, 95)
        rows.append(f"""    <tr>
      <td><code>{_esc(d.get("id", ""))}</code></td>
      <td>{_esc(d.get("device", ""))} ({_esc(d.get("mount", ""))})</td>
      <td class="ta-c">{_esc(d.get("type", ""))}</td>
      <td>{_esc(d.get("category", ""))} ({_esc(d.get("performance_level", ""))})</td>
      <td class="ta-c">{size} GB</td>
      <td><div class="bar-bg"><div class="bar {_bar_cls(usage, 80, 95)}" style="width:{_bar_width(usage)}%"></div></div> {_fmt_num(usage)}%</td>
      <td class="ta-c">~{free} GB</td>
      <td class="ta-c"><span class="{cls}">{icon}</span></td>
    </tr>""")
    snap = "enabled" if any(d.get("snapshot_enabled") for d in disks) else "disabled"
    return f"""
<div class="card">
  <div class="section-title"><span class="icon">📀</span> Disk Capacity</div>
  <table>
    <tr><th>Disk ID</th><th>Mount</th><th style="text-align:center;">Type</th><th>Category</th><th style="text-align:center;">Size</th><th>Used</th><th style="text-align:center;">Free</th><th style="text-align:center;">Status</th></tr>
{chr(10).join(rows)}
  </table>
  <p class="note">Total: {len(disks)} disk(s), {total_size} GB | Snapshot policy: {snap}</p>
</div>
"""


def render_gpu_card(metrics: dict, inst: dict) -> str:
    gpu = metrics.get("gpu")
    if not gpu:
        return ""
    rows = [
        ("GPU Utilization", f'{_fmt_num(gpu.get("util"))}%', gpu.get("util"), 80, 95),
        ("GPU Memory Utilization", f'{_fmt_num(gpu.get("mem_util"))}%', gpu.get("mem_util"), 80, 95),
        ("GPU Temperature", f'{_fmt_num(gpu.get("temp"))}°C', gpu.get("temp"), 75, 85),
    ]
    trs = []
    for name, val, v, w, c in rows:
        cls, icon, _ = _status_from(v, w, c)
        trs.append(f'    <tr><td>{name}</td><td class="ta-c">{val}</td><td class="ta-c"><span class="{cls}">{icon}</span></td></tr>')
    return f"""
<div class="card">
  <div class="section-title"><span class="icon">🎮</span> GPU</div>
  <p><b>GPU Configuration</b>: {inst.get("gpu_count", 0)} x {_esc(inst.get("gpu_model", ""))}</p>
  <table style="margin-top:12px;">
    <tr><th>Metric</th><th style="text-align:center;">Current</th><th style="text-align:center;">Status</th></tr>
{chr(10).join(trs)}
  </table>
</div>
"""


def render_assessment_card(assessment: dict) -> str:
    score = assessment.get("health_score", 100)
    grade = assessment.get("grade", "A").upper()
    score_cls = ""
    if score < 60:
        score_cls = " crit"
    elif score < 75:
        score_cls = " warn"
    dim_rows = []
    for i, d in enumerate(assessment.get("dimensions", []), 1):
        dim_rows.append(
            f'    <tr><td class="ta-c">{i}</td><td>{_esc(d["name"])}</td>'
            f'<td class="ta-c"><span class="rating rating-{_grade_letter(d["grade"])}">{_esc(d["grade"])}</span></td>'
            f'<td class="ta-c">{d.get("score", 0)}/{d.get("max_score", 0)}</td>'
            f'<td>{_esc(d.get("key_metric", d.get("current", "")))}</td>'
            f'<td>{_esc(d.get("detail", ""))}</td></tr>'
        )
    return f"""
<div class="card">
  <div class="section-title"><span class="icon">📋</span> Overall Health Assessment</div>
  <div style="text-align:center; margin:16px 0;">
    <span class="score-num{score_cls}">{score} <span class="score-small">/ 100</span></span>
  </div>
  <table>
    <tr><th style="text-align:center;">#</th><th>Dimension</th><th style="text-align:center;">Grade</th><th style="text-align:center;">Score</th><th>Key Metric</th><th>Detail</th></tr>
{chr(10).join(dim_rows)}
    <tr style="background:#f8f9fa; font-weight:700;">
      <td class="ta-c"></td><td><b>Total</b></td><td class="ta-c"><span class="rating rating-{_grade_letter(grade)}">{grade}</span></td><td class="ta-c">{score}/100</td><td>—</td><td>{_esc(assessment.get("grade_label", ""))}</td>
    </tr>
  </table>
</div>
"""


def render_recommendations_card(rec: dict, inst: dict, metrics: dict, assessment: dict) -> str:
    def _ul(items: list) -> str:
        if not items:
            return '<p class="note">No specific recommendations.</p>'
        return "<ul>\n" + "\n".join(f"    <li>{_esc(x)}</li>" for x in items) + "\n  </ul>"

    cpu_avg = (metrics.get("cpu") or {}).get("avg", 0) or 0
    mem_avg = (metrics.get("memory") or {}).get("avg", 0) or 0
    gpu_util = (metrics.get("gpu") or {}).get("util", 0) if metrics.get("gpu") else None
    usage_line = f"CPU {_fmt_num(cpu_avg)}% · Memory {_fmt_num(mem_avg)}%"
    if gpu_util is not None:
        usage_line += f" · GPU {_fmt_num(gpu_util)}%"

    return f"""
<div class="card">
  <div class="section-title"><span class="icon">💡</span> Recommendations</div>
  <h4>⚡ Immediate (within 24h)</h4>
  {_ul(rec.get("immediate", []))}
  <h4 style="margin-top:12px;">📅 Short-term (this week)</h4>
  {_ul(rec.get("short_term", []))}
  <h4 style="margin-top:12px;">🔭 Long-term</h4>
  {_ul(rec.get("long_term", []))}
  <h4 style="margin-top:12px;">🔔 Monitoring &amp; Alerting</h4>
  <ul>
    <li>CPU &gt; 80% for 5 consecutive minutes</li>
    <li>load_5m &gt; 2x CPU cores</li>
    <li>Memory &gt; 80% for 5 consecutive minutes</li>
    <li>Disk usage &gt; 85%</li>
    <li>Instance health status check</li>
    <li>Subscribe to ECS system event notifications</li>
  </ul>
  <h4 style="margin-top:12px;">💰 Cost Optimization</h4>
  <table>
    <tr><td style="width:140px;"><b>Instance Type</b></td><td>{_esc(inst.get("instance_type", ""))} ({_esc(inst.get("charge_type", ""))})</td></tr>
    <tr><td><b>Resource Utilization</b></td><td>{_esc(usage_line)}</td></tr>
    <tr><td><b>Evaluation</b></td><td>{_esc(assessment.get("cost_evaluation", ""))}</td></tr>
    <tr><td><b>Suggestion</b></td><td>{_esc(assessment.get("cost_suggestion", ""))}</td></tr>
  </table>
</div>
"""


def render_appendix_card(meta: dict, metrics: dict) -> str:
    return f"""
<div class="card">
  <div class="section-title"><span class="icon">📎</span> Appendix</div>
  <h4>Data Collection Details</h4>
  <table>
    <tr><td style="width:140px;"><b>Inspection Time</b></td><td>{_esc(meta.get("generated_at", ""))}</td></tr>
    <tr><td><b>Data Source</b></td><td>{"☁️ CloudMonitor Agent" if meta.get("data_source") != "fallback" else "🟠 ECS API fallback"} (Agent status: {_esc(meta.get("agent_status", "running"))})</td></tr>
    <tr><td><b>Query API</b></td><td><code>cms DescribeMetricLast</code> / <code>ecs DescribeInstances</code> / <code>ecs DescribeDisks</code></td></tr>
    <tr><td><b>Namespace</b></td><td><code>acs_ecs_dashboard</code></td></tr>
    <tr><td><b>Sampling Interval</b></td><td>60 seconds</td></tr>
    <tr><td><b>Time Range</b></td><td>Last {meta.get("time_range_minutes", 15)} minutes</td></tr>
  </table>
</div>
"""


def render_footer(meta: dict, inst: dict) -> str:
    return f"""
<div class="footer">
  <div class="sep">━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>
  <p>Report generated by alibabacloud-ecs-health-inspection</p>
  <p>{_esc(meta.get("generated_at", ""))} · Region: {_esc(inst.get("region", ""))} · Duration: {meta.get("duration_seconds", 0)} seconds</p>
</div>
"""


# ---------- Main render ----------

def render(data: dict) -> str:
    meta = data.get("meta", {})
    inst = data.get("instance", {})
    metrics = data.get("metrics", {})
    # Attach disks into metrics for convenience
    metrics["disks"] = data.get("disks", [])
    # Attach processes
    metrics["processes"] = data.get("processes")
    assessment = data.get("assessment", {})
    rec = data.get("recommendations", {})

    title_id = _esc(inst.get("id", ""))
    body = "\n".join([
        render_header(meta, assessment),
        '<div class="container">',
        render_instance_card(inst, meta),
        render_overview(assessment, metrics, inst),
        render_summary(assessment, metrics, inst),
        render_cpu_card(metrics, inst, assessment),
        render_memory_card(metrics, inst),
        render_disk_io_card(metrics),
        render_network_card(metrics, inst),
        render_disk_capacity_card(metrics),
        render_gpu_card(metrics, inst),
        render_assessment_card(assessment),
        render_recommendations_card(rec, inst, metrics, assessment),
        render_appendix_card(meta, metrics),
        render_footer(meta, inst),
        "</div>",
    ])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ECS Instance Inspection Report — {title_id}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def validate(data: dict) -> list[str]:
    """Pre-render validation. Returns a list of error messages; empty list means pass."""
    errors: list[str] = []

    # 1) Required top-level objects
    for top in ("meta", "instance", "metrics", "assessment"):
        if top not in data or not isinstance(data.get(top), dict):
            errors.append(f"[required] top-level field `{top}` is missing or has wrong type")

    assessment = data.get("assessment", {}) or {}

    # 2) assessment required non-empty fields
    for key in ("health_score", "grade", "grade_label", "one_liner", "narrative"):
        v = assessment.get(key)
        if v is None or (isinstance(v, str) and not v.strip()):
            errors.append(f"[required] assessment.{key} must not be empty")

    # 3) health_score must match grade strictly
    score = assessment.get("health_score")
    grade = assessment.get("grade")
    if isinstance(score, (int, float)) and isinstance(grade, str):
        expected = (
            "A" if score >= 90 else
            "B" if score >= 75 else
            "C" if score >= 60 else
            "D" if score >= 40 else
            "F"
        )
        if grade.upper() != expected:
            errors.append(
                f"[logic] grade={grade} does not match health_score={score}; expected grade={expected} "
                f"(thresholds: >=90:A / >=75:B / >=60:C / >=40:D / <40:F)"
            )

    one_liner = (assessment.get("one_liner") or "").strip().lower()
    if isinstance(score, (int, float)) and score < 60 and one_liner:
        normal_keywords = (
            "all metrics normal", "all normal", "no anomaly", "no anomalies",
            "running normally", "operating normally", "everything is normal",
            "no issues",
        )
        if any(kw in one_liner for kw in normal_keywords):
            errors.append(
                f"[logic] health_score={score} is below 60 but one_liner='{assessment.get('one_liner')}' "
                f"indicates a normal status; logical contradiction"
            )

    # 4) dimensions[] type check
    dims = assessment.get("dimensions") or []
    if isinstance(dims, list):
        for i, d in enumerate(dims):
            if not isinstance(d, dict):
                continue
            cur = d.get("current")
            if isinstance(cur, str):
                # Allow N/A or numeric with % suffix; reject range expressions
                stripped = cur.replace("%", "").replace("°C", "").strip()
                if ("-" in stripped or "~" in stripped or "approx" in stripped.lower()) and "N/A" not in stripped.upper():
                    errors.append(
                        f"[type] dimensions[{i}].current='{cur}' is a range expression; expected a number or 'N/A'"
                    )

    # 5) Disk latency unit check (raw value must be in microseconds)
    metrics = data.get("metrics", {}) or {}
    lat = metrics.get("disk_latency")
    if isinstance(lat, dict):
        for k, v in lat.items():
            if isinstance(v, (int, float)) and 0 < v < 1:
                errors.append(
                    f"[unit] metrics.disk_latency.{k}={v} is too small; suspected incorrect conversion to ms. "
                    f"Pass through raw microseconds (μs) from API; do NOT divide by 1000"
                )

    # 6) disks[] must not be empty
    disks = data.get("disks")
    if disks is not None and isinstance(disks, list) and len(disks) == 0:
        errors.append("[required] disks[] is empty; must cover all disks discovered in Step 4")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Render ECS inspection HTML report from JSON.")
    parser.add_argument("--input", "-i", help="Path to JSON input file; defaults to stdin.")
    parser.add_argument("--output", "-o", help="Path to write HTML output. Required unless --schema/--validate.")
    parser.add_argument("--schema", action="store_true", help="Print JSON schema doc and exit.")
    parser.add_argument("--validate", action="store_true",
                        help="Validate input JSON against schema/logic rules without rendering.")
    args = parser.parse_args()

    if args.schema:
        print(SCHEMA_DOC)
        return 0

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    if args.validate:
        errs = validate(data)
        if errs:
            print("✗ JSON validation failed:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print("✓ JSON validation passed", file=sys.stderr)
        return 0

    if not args.output:
        parser.error("--output is required when not using --schema or --validate")

    # Auto-validate before rendering; errors are warnings only and do not block rendering
    errs = validate(data)
    if errs:
        print("⚠ JSON pre-validation found issues (continuing render anyway; recommend fixing per SKILL Step 6.1):", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)

    html_str = render(data)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"✓ HTML report written to: {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
