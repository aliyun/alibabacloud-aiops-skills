# -*- coding: utf-8 -*-
"""Markdown 格式巡检报告渲染（拆分自 health-inspect.py 的 render_markdown）"""

import json
import os
from datetime import datetime, timedelta, timezone

from hi_utils import format_bytes, format_mb, status_icon


# ─── Markdown Renderer ────────────────────────────────────────────────────────

def render_markdown(data):
    lines = []
    p = lines.append
    bi = data['basic_info']

    p('# PolarDB MySQL 实例健康巡检报告')
    p('')
    p(f'- **巡检时间**: {data["inspect_time"]}')
    p(f'- **实例 ID**: {data["cluster_id"]}')
    p(f'- **Region**: {data["region"]}')

    p('')
    p('## 一、实例基本信息')
    p('')
    p('| 项目 | 值 |')
    p('|------|------|')
    p(f'| 数据库类型 | {bi["db_type"]} |')
    p(f'| 大版本 | {bi["db_type"]} {bi["db_version"]} |')
    p(f'| 内核小版本 | {bi["revision_version"]} |')
    p(f'| 最新可用版本 | {bi["latest_version"]} |')
    vs = "✅ 已是最新" if bi['is_latest'] else "⬆️ 可升级"
    p(f'| 版本状态 | {vs} |')
    p(f'| Proxy 版本 | {bi["proxy_version"]} |')
    p(f'| 集群状态 | {bi["status"]} |')
    p(f'| 存储类型 | {bi["storage_type"]} |')
    p(f'| 集群类别 | {bi.get("category_zh", bi["category"])} |')
    p(f'| 已用存储 | {bi["storage_used_str"]} |')
    p(f'| 存储容量 | {bi["storage_space_str"] or bi["storage_max_str"]} |')
    if bi.get('is_psl'):
        auto_expand_txt = '自动扩展（PSL 存储）'
    elif bi.get('is_essd'):
        auto_expand_txt = '已开启（上限 ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + '）' if bi.get("storage_auto_scale") else '未开启'
    else:
        auto_expand_txt = 'N/A'
    p(f'| 自动扩展 | {auto_expand_txt} |')

    p('')
    p(f'### 节点详情 ({len(data["nodes"])} 个节点)')
    p('')
    p('| 节点ID | 角色 | 状态 | 规格 | CPU | 内存 | 最大连接 | 最大IOPS |')
    p('|--------|------|------|------|-----|------|----------|----------|')
    for nd in data['nodes']:
        p(f'| {nd["id"]} | {nd["role"]} | {nd["status"]} | {nd["class"]} | {nd["cpu"]}核 | {nd["mem"]} | {nd["max_conn"]} | {nd["max_iops"]} |')
    p(f'| **合计** | | | | | | **{data["total_max_conn"]}** | **{data["total_max_iops"]}** |')

    p('')
    p('## 二、当前会话')
    si = data.get('session_info')
    if si and si.get('nodes'):
        for node_label, sd in si['nodes'].items():
            p('')
            p(f'### {node_label}')
            p('')
            p(f'- **总连接数**: {sd.get("TotalSessionCount", 0)}')
            p(f'- **活跃会话**: {sd.get("ActiveSessionCount", 0)}')
            p(f'- **最大活跃时间**: {sd.get("MaxActiveTime", 0)}s')
            sl = sd.get('SessionList', [])
            active_s = [s for s in sl if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump')]
            abnormal_s = [s for s in sl if s.get('TrxDuration', 0) > 10]
            binlog_s = [s for s in sl if s.get('Command', '').startswith('Binlog Dump')]
            if active_s:
                p('')
                p(f'#### 活跃会话（{len(active_s)}）')
                p('')
                p('| ID | User | Host | DB | Command | Time | TrxDuration | State | SQL |')
                p('|-----|------|------|-----|---------|------|-------------|-------|------|')
                for s in active_s[:20]:
                    sql = (s.get('SqlText', '') or '')[:40].replace('|', '\\|')
                    host = s.get('Client', s.get('Host', ''))
                    trx_dur = s.get('TrxDuration', '')
                    trx_str = f'{trx_dur}s' if trx_dur else '-'
                    state = (s.get('State', '') or '')[:18].replace('|', '\\|')
                    p(f'| {s.get("SessionId","")} | {s.get("User","")} | {host} | {s.get("DbName","")} | {s.get("Command","")} | {s.get("Time",0)} | {trx_str} | {state} | {sql} |')
            if abnormal_s:
                p('')
                p(f'#### 异常会话（长时间未提交的事务>10s）')
                p('')
                p('| ID | User | Host | DB | Command | Time | TrxDuration | State | SQL |')
                p('|-----|------|------|-----|---------|------|-------------|-------|------|')
                for s in abnormal_s[:20]:
                    host = s.get('Client', s.get('Host', ''))
                    state = (s.get('State', '') or '')[:18].replace('|', '\\|')
                    trx_dur = s.get('TrxDuration', '')
                    trx_str = f'{trx_dur}s' if trx_dur else '-'
                    sql = (s.get('SqlText', '') or '')[:40].replace('|', '\\|')
                    p(f'| {s.get("SessionId","")} | {s.get("User","")} | {host} | {s.get("DbName","")} | {s.get("Command","")} | {s.get("Time",0)} | {trx_str} | {state} | {sql} |')
            if len(binlog_s) > 10:
                p('')
                p(f'> ⚠️ Binlog Dump 会话（{len(binlog_s)} 个）— 下游消费 Binlog 连接较多，可能占用较高 IOPS')
            us = sd.get('UserStats', [])
            if us:
                p('')
                p(f'#### 按用户统计')
                p('')
                p('| 用户 | 总连接 | 活跃 |')
                p('|------|--------|------|')
                for u in us:
                    p(f'| {u.get("Key","")} | {u.get("TotalCount",0)} | {u.get("ActiveCount",0)} |')
            if not active_s and not abnormal_s and len(binlog_s) <= 10:
                p('')
                p('> 当前无活跃或异常会话')
    else:
        p('')
        p('> ⚠️ 未获取到会话信息')

    p('')
    p('## 三、资源使用率（最近 7 天）')
    res = data.get('resource', {})
    if res.get('cluster'):
        c = res['cluster']
        tmc = data['total_max_conn']
        p('')
        p('### 集群总览')
        p('')
        p('| 指标 | 平均值 | 峰值 | 状态 |')
        p('|------|--------|------|------|')
        p(f'| CPU | {c["cpu_avg"]:.2f}% | {c["cpu_peak"]:.2f}% | {status_icon(c["cpu_peak"])} |')
        p(f'| 内存 | {c["mem_avg"]:.2f}% | {c["mem_peak"]:.2f}% | {status_icon(c["mem_peak"], "memory")} |')
        p(f'| 空间 | {c["disk_avg_pct"]:.2f}% ({format_mb(c["disk_avg_mb"])}) | {c["disk_peak_pct"]:.2f}% ({format_mb(c["disk_peak_mb"])}) | {status_icon(c["disk_peak_pct"], "space")} |')
        p(f'| IO吞吐 | {c["io_avg"]:.0f} KB/s | {c["io_peak"]:.0f} KB/s | 🔵 |')
        p(f'| 连接数 | {c["conn_avg"]:.0f}/{tmc} ({c["conn_avg_pct"]:.1f}%) | {c["conn_peak"]:.0f}/{tmc} ({c["conn_peak_pct"]:.1f}%) | {status_icon(c["conn_peak_pct"])} |')

        p('')
        p('### 各节点详情')
        for nid, nd in res.get('nodes', {}).items():
            icons = [status_icon(nd['cpu_peak']), status_icon(nd['mem_peak'], 'memory'), status_icon(nd['conn_pct'])]
            worst = '🔴' if '🔴' in icons else ('🟡' if '🟡' in icons else '🟢')
            p('')
            p(f'#### {worst} {nid} ({nd["role"]})')
            p('')
            p('| 指标 | 平均值 | 峰值 | 状态 |')
            p('|------|--------|------|------|')
            p(f'| CPU | {nd["cpu_avg"]:.2f}% | {nd["cpu_peak"]:.2f}% | {status_icon(nd["cpu_peak"])} |')
            p(f'| 内存 | {nd["mem_avg"]:.2f}% | {nd["mem_peak"]:.2f}% | {status_icon(nd["mem_peak"], "memory")} |')
            p(f'| 连接 | {nd["conn_avg"]:.0f} | {nd["conn_peak"]:.0f} ({nd["conn_pct"]:.1f}%) | {status_icon(nd["conn_pct"])} |')
            p(f'| 活跃连接 | {nd["active_avg"]:.0f} | {nd["active_peak"]:.0f} | |')
            if nd.get('iops_peak', 0) > 0:
                p(f'| IOPS | {nd["iops_avg"]:.0f} | {nd["iops_peak"]:.0f} | |')
    else:
        p('')
        p('> ⚠️ 未获取到资源使用率数据')

    p('')
    p('## 四、空间巡检')
    p('')
    p('### 4.1 库表空间 TOP20')
    tl = data['space'].get('table_list', [])
    if tl:
        p('')
        p('| # | 数据库 | 表名 | 总空间 | 数据 | 索引 | 行数 |')
        p('|---|--------|------|--------|------|------|------|')
        for i, t in enumerate(tl, 1):
            rs = f'{t["rows"]:,}' if t['rows'] else '0'
            p(f'| {i} | {t["db"]} | {t["table"]} | {t["total_str"]} | {t["data_str"]} | {t["index_str"]} | {rs} |')
        if data['space'].get('total_used'):
            p(f'\n总使用空间: {format_bytes(data["space"]["total_used"])}')
    else:
        p('')
        p('> ⚠️ 空间分析未返回表统计数据')

    p('')
    p('### 4.2 空间变化趋势')
    disk_ts = res.get('cluster_ts', {}).get('disk', [])
    if disk_ts and len(disk_ts) >= 2:
        first_mb, last_mb = disk_ts[0][1], disk_ts[-1][1]
        days = (disk_ts[-1][0] - disk_ts[0][0]) / (86400 * 1000) or 1
        daily = (last_mb - first_mb) / days
        p('')
        p(f'- 起始: {format_mb(first_mb)} → 当前: {format_mb(last_mb)}')
        p(f'- 日均{"增长" if daily >= 0 else "减少"}: {"+" if daily >= 0 else "-"}{format_mb(abs(daily))}')
    else:
        p('')
        p('> 无磁盘趋势数据')

    p('')
    p('### 4.3 异常列表')
    anom = data['space'].get('anomalies', [])
    if anom:
        p('')
        p('| 类型 | 数据库 | 表名 | 详情 |')
        p('|------|--------|------|------|')
        for a in anom:
            p(f'| {a["type"]} | {a["db"]} | {a["table"]} | {a["detail"]} |')
    else:
        p('')
        p('✅ 未发现异常')

    p('')
    p('## 五、慢日志统计（最近 7 天）')
    sl = data.get('slow_logs', [])
    if sl:
        p('')
        p('| # | 数据库 | SQLHASH | 次数 | 总耗时(s) | 最大(s) | 平均扫描行数 | 平均返回行数 | SQL 摘要 |')
        p('|---|--------|---------|------|-----------|---------|----------|----------|----------|')
        for i, s in enumerate(sl, 1):
            sql = s['sql_text'][:48].replace('|', '\\|')
            if len(s['sql_text']) > 48:
                sql += '...'
            p(f'| {i} | {s["db"]} | `{s.get("sql_hash","")}` | {s["count"]} | {s["total_time"]} | {s["max_time"]} | {s.get("avg_parse_rows",0):,} | {s.get("avg_return_rows",0):,} | {sql} |')
        p(f'\n共计 {data["slow_total"]} 条慢查询统计')
    else:
        p('')
        p('✅ 最近 7 天无慢日志记录')

    p('')
    p('## 六、报警历史（最近 7 天）')
    alerts = data.get('alert_history', [])
    if alerts:
        p('')
        p('| # | 时间 | 级别 | 规则 | 指标 | 节点 | 当前值 | 阈值 | 通知状态 |')
        p('|---|------|------|------|------|------|--------|------|----------|')
        for i, a in enumerate(alerts, 1):
            p(f'| {i} | {a["time"]} | {a["level"]} | {a.get("rule_name","")} | {a.get("metric","")} | {a.get("node_id","")} | {a.get("cur_value","")} | {a.get("threshold","")} | {a.get("send_status","")} |')
        p(f'\n共计 {len(alerts)} 条报警记录')
    else:
        p('')
        p('✅ 最近 7 天无报警记录')

    p('')
    p('## 七、巡检结论与建议')
    p('')
    sug = data.get('suggestions', [])
    if not sug:
        p('✅ 巡检未发现明显问题，实例运行状态良好。')
    else:
        danger_items = [zh for level, en, zh in sug if level == 'danger']
        warn_items = [zh for level, en, zh in sug if level == 'warn']
        info_items = [zh for level, en, zh in sug if level == 'info']
        for label, items in [('🔴 高风险', danger_items), ('🟡 中风险', warn_items), ('🔵 低风险', info_items)]:
            if not items:
                continue
            p(f'### {label}')
            if len(items) == 1:
                p(f'- {items[0]}')
            else:
                for i, t in enumerate(items, 1):
                    p(f'{i}. {t}')
            p('')
    return '\n'.join(lines)
