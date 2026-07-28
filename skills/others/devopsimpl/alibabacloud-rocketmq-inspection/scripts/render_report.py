#!/usr/bin/env python3
"""Read intermediate inspection data, score against thresholds, render Markdown.

Usage:
    render_report.py <work_dir> <thresholds.yaml> <output.md>

Work dir layout (written by inspect.sh):
    <work>/meta.json
    <work>/regions.json
    <work>/ghosts.json
    <work>/<instanceId>/meta.json
    <work>/<instanceId>/quota.json
    <work>/<instanceId>/instance/<metric>.json   (datapoints array)
    <work>/<instanceId>/group/<metric>.json
    <work>/<instanceId>/topic/<metric>.json
    <work>/<instanceId>/consumer_status/<group>.json
    <work>/errors.log
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERR: PyYAML required: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)


# For each metric, the datapoint field that carries the value
STAT_FIELD = {
    # Instance
    "InstanceApiCallTps": "Sum",
    "InstanceApiCallTpsMax": "Sum",
    "InstanceTpsUtilization": "Value",
    "InstanceSendApiCallTps": "Maximum",
    "InstanceSendTpsUtilization": "Value",
    "InstanceReceiveApiCallTps": "Maximum",
    "InstanceReceiveTpsUtilization": "Value",
    "InstanceOnlineClients": "Sum",
    "InstanceOnlineClientsUtilization": "Maximum",
    "InstanceActiveConnection": "Maximum",
    "ThrottledSendRequestsPerInstance": "Sum",
    "ThrottledReceiveRequestsPerInstance": "Sum",
    "SendMessageCountPerInstance": "Sum",
    "ReceiveMessageCountPerInstance": "Sum",
    "InstanceTrafficRX": "Maximum",
    "InstanceTrafficTX": "Maximum",
    "InstanceTrafficRXUtilization": "Maximum",
    "InstanceTrafficTXUtilization": "Maximum",
    "InstanceDropTrafficRX": "Maximum",
    "InstanceDropTrafficTX": "Maximum",
    "InstanceInternetFlowoutBandwidth": "Sum",
    "InstanceStorageSize": "Sum",
    # Group
    "ConsumerLag": "Sum",
    "ConsumerLagLatencyPerGid": "Maximum",
    "ReadyMessages": "Sum",
    "ReadyMessageQueueTime": "Maximum",
    "ReceiveMessageCountPerGid": "Sum",
    "ThrottledReceiveRequestsPerGid": "Sum",
    "SendDLQMessageCountPerGid": "Sum",
    # Topic
    "SendMessageCountPerTopic": "Sum",
    "ReceiveMessageCountPerTopic": "Sum",
    "ThrottledSendRequestsPerTopic": "Sum",
}

METRIC_LABEL = {
    # Instance
    "InstanceApiCallTps": "API TPS avg (count/s)",
    "InstanceApiCallTpsMax": "API TPS peak (count/s)",
    "InstanceTpsUtilization": "TPS utilization (%)",
    "InstanceSendApiCallTps": "Send TPS peak (count/s, 5.0)",
    "InstanceSendTpsUtilization": "Send TPS utilization (%, 5.0)",
    "InstanceReceiveApiCallTps": "Receive TPS peak (count/s, 5.0)",
    "InstanceReceiveTpsUtilization": "Receive TPS utilization (%, 5.0)",
    "InstanceOnlineClients": "Online clients",
    "InstanceOnlineClientsUtilization": "Online clients utilization (%)",
    "InstanceActiveConnection": "Public active connections (count/s)",
    "ThrottledSendRequestsPerInstance": "Send throttles/min",
    "ThrottledReceiveRequestsPerInstance": "Receive throttles/min",
    "SendMessageCountPerInstance": "Sent messages/min",
    "ReceiveMessageCountPerInstance": "Received messages/min",
    "InstanceTrafficRX": "Public RX bandwidth (bit/s)",
    "InstanceTrafficTX": "Public TX bandwidth (bit/s)",
    "InstanceTrafficRXUtilization": "Public RX bandwidth utilization (%)",
    "InstanceTrafficTXUtilization": "Public TX bandwidth utilization (%)",
    "InstanceDropTrafficRX": "Public RX drop (bit/s)",
    "InstanceDropTrafficTX": "Public TX drop (bit/s)",
    "InstanceInternetFlowoutBandwidth": "Public downstream bandwidth (B/s, 5.0)",
    "InstanceStorageSize": "Storage size (B, 5.0)",
    # Group
    "ConsumerLag": "Backlog",
    "ConsumerLagLatencyPerGid": "Consume latency (ms)",
    "ReadyMessages": "Ready messages",
    "ReadyMessageQueueTime": "Ready queue time (ms)",
    "ReceiveMessageCountPerGid": "Received messages/min",
    "ThrottledReceiveRequestsPerGid": "Receive throttles/min",
    "SendDLQMessageCountPerGid": "DLQ messages/min",
    # Topic
    "SendMessageCountPerTopic": "Sent messages/min",
    "ReceiveMessageCountPerTopic": "Received messages/min",
    "ThrottledSendRequestsPerTopic": "Send throttles/min",
}

# Instance-dimension metrics grouped by section (section name -> metric list)
INSTANCE_SECTIONS = [
    ("Traffic & TPS", [
        "InstanceApiCallTps", "InstanceApiCallTpsMax",
        "InstanceTpsUtilization",
        "InstanceSendApiCallTps", "InstanceSendTpsUtilization",
        "InstanceReceiveApiCallTps", "InstanceReceiveTpsUtilization",
        "SendMessageCountPerInstance", "ReceiveMessageCountPerInstance",
    ]),
    ("Clients / connections", [
        "InstanceOnlineClients", "InstanceOnlineClientsUtilization",
        "InstanceActiveConnection",
    ]),
    ("Throttling", [
        "ThrottledSendRequestsPerInstance", "ThrottledReceiveRequestsPerInstance",
    ]),
    ("Public bandwidth (5.0 internet-enabled)", [
        "InstanceTrafficRX", "InstanceTrafficTX",
        "InstanceTrafficRXUtilization", "InstanceTrafficTXUtilization",
        "InstanceDropTrafficRX", "InstanceDropTrafficTX",
        "InstanceInternetFlowoutBandwidth",
    ]),
    ("Storage (5.0)", [
        "InstanceStorageSize",
    ]),
]


def load_points(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text() or "[]") or []
    except json.JSONDecodeError:
        return []


def aggregate(points: list[dict], stat: str, key_fields: tuple[str, ...]) -> dict[tuple, dict]:
    """Group by key_fields, return per-bucket max/avg/last."""
    groups: dict[tuple, list[float]] = defaultdict(list)
    for p in points:
        v = p.get(stat)
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        key = tuple(p.get(k, "") for k in key_fields)
        groups[key].append(v)
    out = {}
    for k, vs in groups.items():
        if not vs:
            continue
        out[k] = {"max": max(vs), "avg": sum(vs) / len(vs), "last": vs[-1], "count": len(vs)}
    return out


def evaluate(metric: str, value: float, thresholds: dict) -> str:
    cfg = thresholds.get(metric)
    if not cfg:
        return ""
    crit = cfg.get("critical")
    warn = cfg.get("warn")
    if crit is not None and value >= crit:
        return "critical"
    if warn is not None and value >= warn:
        return "warn"
    return ""


def fmt_value(v) -> str:
    if v is None:
        return "N/A"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if v == int(v) and abs(v) < 1e15:
        return f"{int(v):,}"
    return f"{v:,.2f}"


def status_icon(level: str) -> str:
    return {"critical": " CRIT", "warn": " WARN", "": ""}[level]


def status_label(level: str) -> str:
    return {"critical": "CRIT", "warn": "WARN", "": "-"}[level]


def health_score(deductions: list[tuple[str, int]]) -> tuple[int, str]:
    score = max(0, 100 - sum(p for _, p in deductions))
    if score >= 80:
        return score, "HEALTHY"
    if score >= 60:
        return score, "WATCH"
    return score, "CRITICAL"


INTERNAL_TOPIC_PREFIXES = ("%RETRY%", "%DLQ%", "%SYS%")


def is_internal_topic(name: str) -> bool:
    return any(name.startswith(p) for p in INTERNAL_TOPIC_PREFIXES)


# Per-version resource quotas (per official documentation)
# 4.x: https://help.aliyun.com/zh/apsaramq-for-rocketmq/cloud-message-queue-rocketmq-4-x-series/product-overview/limits
# 5.x: https://help.aliyun.com/zh/apsaramq-for-rocketmq/cloud-message-queue-rocketmq-5-x-series/product-overview/usage-limits
QUOTA_LIMITS = {
    "4": {"group_count": 1000, "topic_count": None},
    "5": {"group_count": 5000, "topic_count": 5000},
}

# Per-region total instance count cap (4.x + 5.x combined)
REGION_INSTANCE_LIMIT = 1000

# 5.x docs: in-processing messages per consumer group must be <= 2500
INFLIGHT_LIMIT = 2500


def render_quota(inst_dir: Path, version: str, quota_thresh: dict) -> tuple[str, list[tuple[str, int]]]:
    quota_path = inst_dir / "quota.json"
    if not quota_path.exists():
        return "", []
    try:
        data = json.loads(quota_path.read_text())
    except json.JSONDecodeError:
        return "", []
    limits = QUOTA_LIMITS.get(version, {})
    rows = []
    deductions: list[tuple[str, int]] = []
    for key, label in [("group_count", "Group count"), ("topic_count", "Topic count")]:
        cur = data.get(key)
        limit = limits.get(key)
        if cur is None:
            rows.append(f"| {label} | fetch failed | - | - | |")
            continue
        if limit is None:
            rows.append(f"| {label} | {cur:,} | no explicit cap | - | |")
            continue
        pct = (cur / limit * 100) if limit else 0
        cfg = quota_thresh.get(key, {}) or {}
        warn_pct = cfg.get("warn_pct")
        crit_pct = cfg.get("critical_pct")
        level = ""
        if crit_pct is not None and pct >= crit_pct:
            level = "critical"
            deductions.append((f"{label} quota critical ({cur}/{limit} = {pct:.1f}%)", 15))
        elif warn_pct is not None and pct >= warn_pct:
            level = "warn"
            deductions.append((f"{label} quota warn ({cur}/{limit} = {pct:.1f}%)", 5))
        rows.append(f"| {label} | {cur:,} | {limit:,} | {pct:.1f}% |{status_icon(level)} |")

    # Message retention
    retention = data.get("retention_hours")
    if retention is None:
        rows.append("| Message retention | unavailable | - | - | |")
    else:
        days = retention / 24
        if version == "4":
            note = "(4.x fixed, not configurable)"
        else:
            note = "(5.x range 24h-720h)"
        rows.append(f"| Message retention | {retention:.0f}h ({days:.1f} days) {note} | - | - | |")

    md = (
        "**Resource quota**\n\n"
        "| Item | Current | Cap | Utilization | Status |\n"
        "|------|---------|-----|-------------|--------|\n"
        + "\n".join(rows)
    )
    return md, deductions


def render_region_quota(work: Path, region_thresh: dict) -> str:
    p = work / "regions.json"
    if not p.exists():
        return ""
    try:
        regions = json.loads(p.read_text())
    except json.JSONDecodeError:
        return ""
    if not regions:
        return ""
    cfg = region_thresh.get("instance_count", {}) or {}
    warn_pct = cfg.get("warn_pct", 80)
    crit_pct = cfg.get("critical_pct", 95)
    rows = []
    for r in regions:
        reg = r.get("region", "?")
        total = r.get("instance_total", 0)
        v4 = r.get("instance_4x", 0)
        v5 = r.get("instance_5x", 0)
        pct = total / REGION_INSTANCE_LIMIT * 100
        level = ""
        if pct >= crit_pct:
            level = "critical"
        elif pct >= warn_pct:
            level = "warn"
        rows.append(
            f"| `{reg}` | {total} | {v4} | {v5} | {REGION_INSTANCE_LIMIT} | {pct:.1f}% |{status_icon(level)} |"
        )
    return (
        "## Region quota\n\n"
        "Per-region instance cap is 1,000 (4.x + 5.x combined).\n\n"
        "| Region | Total | 4.x | 5.x | Cap | Utilization | Status |\n"
        "|--------|-------|-----|-----|-----|-------------|--------|\n"
        + "\n".join(rows)
        + "\n"
    )


def render_consumer_status(inst_dir: Path, cs_thresh: dict) -> tuple[str, list[tuple[str, int]]]:
    cs_dir = inst_dir / "consumer_status"
    if not cs_dir.exists():
        return "", []
    files = sorted(cs_dir.glob("*.json"))
    if not files:
        return "", []
    inflight_cfg = cs_thresh.get("inflight_count", {}) or {}
    warn = inflight_cfg.get("warn")
    crit = inflight_cfg.get("critical")
    rows = []
    deductions: list[tuple[str, int]] = []
    for f in files:
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if not d:
            continue
        gid = d.get("groupId", f.stem)
        online = "yes" if d.get("online") else "no" if d.get("online") is False else "-"
        rebal = "yes" if d.get("rebalanceOk") else "no" if d.get("rebalanceOk") is False else "-"
        subsame = "yes" if d.get("subscriptionSame") else "no" if d.get("subscriptionSame") is False else "-"
        conn = d.get("connectionCount", "-")
        tps = d.get("consumeTps")
        delay = d.get("delayTime")
        diff = d.get("totalDiff")
        rt = d.get("consumeRt")
        inflight = d.get("inflightCount")
        # Evaluate inflight
        inflight_icon = ""
        if inflight is not None:
            if crit is not None and inflight >= crit:
                inflight_icon = " CRIT"
                deductions.append((f"Group `{gid}` inflight critical ({inflight}/{INFLIGHT_LIMIT}, cap 2500)", 15))
            elif warn is not None and inflight >= warn:
                inflight_icon = " WARN"
                deductions.append((f"Group `{gid}` inflight warn ({inflight}/{INFLIGHT_LIMIT}, cap 2500)", 5))
        inflight_str = f"{fmt_value(inflight)}{inflight_icon}"
        rows.append(
            f"| `{gid}` | {online} | {rebal} | {subsame} | {conn} | "
            f"{fmt_value(tps)} | {fmt_value(delay)} | {fmt_value(diff)} | {inflight_str} | {fmt_value(rt)} |"
        )
    if not rows:
        return "", []
    md = (
        "#### Consumer runtime state\n\n"
        "Live snapshot at fetch time. `Inflight` corresponds to the 5.x doc limit (in-processing messages per group <= 2500).\n\n"
        "| Group | Online | Rebalance OK | Subscription consistent | Connections | Consume TPS | Delay(ms) | Backlog total | Inflight | RT(ms) |\n"
        "|-------|--------|-------------|-------------------------|-------------|-------------|-----------|---------------|----------|--------|\n"
        + "\n".join(rows)
    )
    return md, deductions


def render_instance(inst_dir: Path, thresholds: dict) -> tuple[dict, list[tuple[str, int]], list[str]]:
    meta = json.loads((inst_dir / "meta.json").read_text())
    iid = meta["instanceId"]
    ver = meta.get("version", "?")
    name = meta.get("name", "")
    sections: list[str] = []
    deductions: list[tuple[str, int]] = []
    summary_issues: list[str] = []
    inst_thresh = thresholds.get("instance", {}) or {}
    grp_thresh = thresholds.get("group", {}) or {}
    top_thresh = thresholds.get("topic", {}) or {}

    # ---------------- Instance dimension (sectioned) ----------------
    inst_md_parts = ["#### Instance metrics\n"]
    for section_name, metric_list in INSTANCE_SECTIONS:
        rows = []
        all_na = True
        for metric in metric_list:
            stat = STAT_FIELD.get(metric, "Sum")
            pts = load_points(inst_dir / "instance" / f"{metric}.json")
            agg = aggregate(pts, stat, ())
            cell = agg.get(())
            label = METRIC_LABEL.get(metric, metric)
            if cell is None:
                rows.append(f"| {label} | N/A | N/A | N/A | |")
                continue
            all_na = False
            level = evaluate(metric, cell["max"], inst_thresh)
            if level == "critical":
                deductions.append(
                    (f"Instance {label} critical (peak {fmt_value(cell['max'])})", 15)
                )
            elif level == "warn":
                deductions.append(
                    (f"Instance {label} warn (peak {fmt_value(cell['max'])})", 5)
                )
            rows.append(
                f"| {label} | {fmt_value(cell['max'])} | {fmt_value(cell['avg'])} | "
                f"{fmt_value(cell['last'])} |{status_icon(level)} |"
            )
        # Sections that are entirely N/A (e.g. 4.x instance's public bandwidth) fold
        if all_na:
            inst_md_parts.append(
                f"<details><summary>{section_name} (no data - 4.x instance or public not enabled)</summary>\n\n"
                "| Metric | Peak | Avg | Last | Status |\n"
                "|--------|------|-----|------|--------|\n"
                + "\n".join(rows)
                + "\n\n</details>\n"
            )
        else:
            inst_md_parts.append(f"**{section_name}**\n")
            inst_md_parts.append(
                "| Metric | Peak | Avg | Last | Status |\n"
                "|--------|------|-----|------|--------|\n"
                + "\n".join(rows)
            )
            inst_md_parts.append("")

    # Resource quota
    quota_thresh = thresholds.get("quota", {}) or {}
    quota_md, quota_deduc = render_quota(inst_dir, ver, quota_thresh)
    if quota_md:
        inst_md_parts.append(quota_md)
        inst_md_parts.append("")
        deductions.extend(quota_deduc)

    sections.append("\n".join(inst_md_parts))

    # Instance summary
    inst_warn = sum(1 for r, p in deductions if (r.startswith("Instance") or "quota" in r) and p == 5)
    inst_crit = sum(1 for r, p in deductions if (r.startswith("Instance") or "quota" in r) and p == 15)
    if inst_crit:
        summary_issues.append(f"instance: {inst_crit} critical")
    elif inst_warn:
        summary_issues.append(f"instance: {inst_warn} warn")

    # ---------------- Group dimension ----------------
    GROUP_COLS = [
        ("ConsumerLag", "Backlog"),
        ("ConsumerLagLatencyPerGid", "Latency(ms)"),
        ("ReadyMessages", "Ready"),
        ("ReadyMessageQueueTime", "ReadyQueue(ms)"),
        ("ReceiveMessageCountPerGid", "Recv/min"),
        ("SendDLQMessageCountPerGid", "DLQ/min"),
        ("ThrottledReceiveRequestsPerGid", "Throttle/min"),
    ]
    group_rows: dict[str, dict[str, dict]] = defaultdict(dict)
    group_levels: dict[str, dict[str, str]] = defaultdict(dict)
    for metric, _ in GROUP_COLS:
        stat = STAT_FIELD[metric]
        pts = load_points(inst_dir / "group" / f"{metric}.json")
        agg = aggregate(pts, stat, ("groupId",))
        for (gid,), cell in agg.items():
            group_rows[gid][metric] = cell
            level = evaluate(metric, cell["max"], grp_thresh)
            group_levels[gid][metric] = level
            label = METRIC_LABEL.get(metric, metric)
            if level == "critical":
                deductions.append(
                    (f"Group `{gid}` {label} critical (peak {fmt_value(cell['max'])})", 15)
                )
            elif level == "warn":
                deductions.append(
                    (f"Group `{gid}` {label} warn (peak {fmt_value(cell['max'])})", 5)
                )

    if group_rows:
        header_cells = ["Group"] + [c[1] for c in GROUP_COLS] + ["Status"]
        header = "| " + " | ".join(header_cells) + " |"
        sep = "|" + "|".join(["---"] * len(header_cells)) + "|"
        grows = []
        for gid in sorted(group_rows.keys()):
            cells = group_rows[gid]
            levels = group_levels[gid]
            worst = ""
            for lv in levels.values():
                if lv == "critical":
                    worst = "critical"; break
                if lv == "warn":
                    worst = "warn"
            row = [f"`{gid}`"]
            for metric, _ in GROUP_COLS:
                row.append(fmt_value(cells.get(metric, {}).get("max")))
            row.append(status_label(worst))
            grows.append("| " + " | ".join(row) + " |")
        sections.append("#### Group health\n\n" + header + "\n" + sep + "\n" + "\n".join(grows))

        bad = sum(1 for g in group_levels.values() if any(v == "critical" for v in g.values()))
        warn_g = sum(1 for g in group_levels.values()
                     if not any(v == "critical" for v in g.values())
                     and any(v == "warn" for v in g.values()))
        if bad:
            summary_issues.append(f"{bad} group critical")
        elif warn_g:
            summary_issues.append(f"{warn_g} group warn")
    else:
        sections.append("#### Group health\n\n_no group data_")

    # Consumer runtime state (independent of CMS group metrics; both 4.x and 5.x have it)
    cs_thresh = thresholds.get("consumer_status", {}) or {}
    consumer_md, consumer_deduc = render_consumer_status(inst_dir, cs_thresh)
    if consumer_md:
        sections.append(consumer_md)
        deductions.extend(consumer_deduc)

    # ---------------- Topic dimension ----------------
    TOPIC_COLS = [
        ("SendMessageCountPerTopic", "Send/min"),
        ("ReceiveMessageCountPerTopic", "Recv/min"),
        ("ThrottledSendRequestsPerTopic", "Throttle/min"),
    ]
    topic_rows: dict[str, dict[str, dict]] = defaultdict(dict)
    topic_levels: dict[str, dict[str, str]] = defaultdict(dict)
    for metric, _ in TOPIC_COLS:
        stat = STAT_FIELD[metric]
        pts = load_points(inst_dir / "topic" / f"{metric}.json")
        agg = aggregate(pts, stat, ("topic",))
        for (topic,), cell in agg.items():
            if is_internal_topic(topic):
                continue
            topic_rows[topic][metric] = cell
            level = evaluate(metric, cell["max"], top_thresh)
            topic_levels[topic][metric] = level
            label = METRIC_LABEL.get(metric, metric)
            if level == "critical":
                deductions.append(
                    (f"Topic `{topic}` {label} critical (peak {fmt_value(cell['max'])})", 15)
                )
            elif level == "warn":
                deductions.append(
                    (f"Topic `{topic}` {label} warn (peak {fmt_value(cell['max'])})", 5)
                )

    if topic_rows:
        header_cells = ["Topic"] + [c[1] for c in TOPIC_COLS] + ["Status"]
        header = "| " + " | ".join(header_cells) + " |"
        sep = "|" + "|".join(["---"] * len(header_cells)) + "|"
        trows = []
        for topic in sorted(topic_rows.keys()):
            cells = topic_rows[topic]
            levels = topic_levels[topic]
            worst = ""
            for lv in levels.values():
                if lv == "critical":
                    worst = "critical"; break
                if lv == "warn":
                    worst = "warn"
            row = [f"`{topic}`"]
            for metric, _ in TOPIC_COLS:
                row.append(fmt_value(cells.get(metric, {}).get("max")))
            row.append(status_label(worst))
            trows.append("| " + " | ".join(row) + " |")
        sections.append("#### Topic load\n\n" + header + "\n" + sep + "\n" + "\n".join(trows))

        topic_crit = sum(1 for t in topic_levels.values() if any(v == "critical" for v in t.values()))
        topic_warn = sum(1 for t in topic_levels.values()
                         if not any(v == "critical" for v in t.values())
                         and any(v == "warn" for v in t.values()))
        if topic_crit:
            summary_issues.append(f"{topic_crit} topic critical")
        elif topic_warn:
            summary_issues.append(f"{topic_warn} topic warn")
    else:
        sections.append("#### Topic load\n\n_no topic data (internal %RETRY% / %DLQ% / %SYS% topics filtered)_")

    meta["_deductions"] = deductions
    meta["_summary_issues"] = summary_issues
    meta["_sections"] = sections
    meta["_label"] = f"{iid}{f' ({name})' if name else ''}"
    meta["_ver_label"] = "5.x" if ver == "5" else "4.x" if ver == "4" else ver
    return meta, deductions, sections


def main():
    if len(sys.argv) != 4:
        print("Usage: render_report.py <work_dir> <thresholds.yaml> <output.md>", file=sys.stderr)
        sys.exit(2)
    work = Path(sys.argv[1])
    thresh_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    overall_meta = json.loads((work / "meta.json").read_text())
    thresholds = yaml.safe_load(thresh_path.read_text()) or {}

    inst_dirs = sorted([d for d in work.iterdir() if d.is_dir()])
    results = [render_instance(d, thresholds) for d in inst_dirs]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        f"# RocketMQ Inspection Report - {now}",
        "",
        f"- Window (UTC): `{overall_meta['start_utc']}` -> `{overall_meta['end_utc']}`"
        f" ({overall_meta['window']})",
        f"- Instance count: {overall_meta['instance_count']}",
        f"- Threshold file: `{overall_meta['thresholds_file']}`",
        "",
    ]
    # Region quota (before summary)
    region_md = render_region_quota(work, thresholds.get("region", {}) or {})
    if region_md:
        lines.append(region_md)
        lines.append("")

    # Ghost instances (CMS still has skeleton data but the management API says NotFound)
    ghosts_path = work / "ghosts.json"
    if ghosts_path.exists():
        try:
            ghosts = json.loads(ghosts_path.read_text())
        except json.JSONDecodeError:
            ghosts = []
        if ghosts:
            lines.append("## Skipped instances (ghost / released)")
            lines.append("")
            lines.append("These IDs still appear in CMS (retained for ~31 days) but the management API returns `Instance.NotFound`, so they are either released or not in the current account. Any metrics are stale residue; detailed inspection is skipped.")
            lines.append("")
            lines.append("| Instance ID | Version | Region | Reason |")
            lines.append("|-------------|---------|--------|--------|")
            for g in ghosts:
                lines.append(
                    f"| `{g.get('instanceId','')}` | {g.get('version','?')}.x | "
                    f"`{g.get('region','?')}` | {g.get('reason','Instance.NotFound')} |"
                )
            lines.append("")

    lines += [
        "## Summary",
        "",
        "| Instance | Version | Health | Status | Top issues |",
        "|----------|---------|--------|--------|------------|",
    ]
    for meta, dedu, _ in results:
        score, status = health_score(dedu)
        issues = "; ".join(meta["_summary_issues"]) if meta["_summary_issues"] else "-"
        lines.append(f"| `{meta['_label']}` | {meta['_ver_label']} | {score} | {status} | {issues} |")
    lines.append("")
    lines.append("## Detailed inspection")
    lines.append("")
    for meta, dedu, sections in results:
        score, status = health_score(dedu)
        lines.append(f"### `{meta['_label']}` ({meta['_ver_label']}) - Health {score} {status}")
        lines.append("")
        if dedu:
            lines.append(
                f"<details><summary>Deductions ({sum(p for _, p in dedu)} points total)</summary>\n"
            )
            for reason, pts in dedu:
                lines.append(f"- -{pts}: {reason}")
            lines.append("\n</details>\n")
        for sec in sections:
            lines.append(sec)
            lines.append("")

    err_log = work / "errors.log"
    if err_log.exists() and err_log.stat().st_size > 0:
        lines.append("## Failed fetches")
        lines.append("")
        lines.append("```")
        lines.append(err_log.read_text().strip())
        lines.append("```")

    out_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
