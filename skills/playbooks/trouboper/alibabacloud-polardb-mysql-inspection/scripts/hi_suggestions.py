"""PolarDB MySQL Health Inspection - Health suggestions and risk generation"""
from datetime import datetime, timedelta, timezone

import hi_config as config


def generate_suggestions(data, resource_usage, version_info):
    """Generate prioritized health suggestions based on inspection data.
    Returns: list of (level, en_text, zh_text) tuples
    """
    res = data.get('resource', {})
    space = data.get('space', {})

    # ─── Suggestions (with correlation, timestamps, priority) ───────────────────

    def _peak_time_str(ts_list):
        if not ts_list:
            return ''
        peak_point = max(ts_list, key=lambda x: x[1])
        t = datetime.fromtimestamp(peak_point[0] / 1000, tz=timezone(timedelta(hours=8)))
        return t.strftime('%m-%d %H:%M')

    def _peak_node_info(node_ts_data, metric, nodes_res):
        peak_val = 0
        peak_nid = ''
        peak_time = ''
        for nid, ts_dict in node_ts_data.items():
            ts_list = ts_dict.get(metric, [])
            if not ts_list:
                continue
            point = max(ts_list, key=lambda x: x[1])
            if point[1] > peak_val:
                peak_val = point[1]
                peak_nid = nid
                t = datetime.fromtimestamp(point[0] / 1000, tz=timezone(timedelta(hours=8)))
                peak_time = t.strftime('%m-%d %H:%M')
        role = nodes_res.get(peak_nid, {}).get('role_short', '') if peak_nid else ''
        return peak_val, peak_nid, role, peak_time

    suggestions = []
    bi = data['basic_info']
    node_ts = res.get('node_ts', {})
    nodes_res = res.get('nodes', {})
    slow_logs_list = data.get('slow_logs', [])
    top_sql = slow_logs_list[0] if slow_logs_list else None
    alerts = data.get('alert_history', [])
    p1p2_alerts = [a for a in alerts if a.get('level') in ('P1', 'P2')]
    cpu_alerts = [a for a in p1p2_alerts if 'cpu' in (a.get('metric') or a.get('rule_name') or '').lower()]
    iops_alerts = [a for a in p1p2_alerts if 'iops' in (a.get('metric') or a.get('rule_name') or '').lower()]

    # Track which issues have been covered by correlation
    cpu_covered = False
    iops_covered = False
    alert_covered = False
    slow_covered = False

    # ═══ Priority 0: Auto-increment overflow (ticking time bomb) ═══
    auto_inc_danger = [a for a in data.get('auto_inc', []) if a['usage'] >= 0.8]
    auto_inc_warn = [a for a in data.get('auto_inc', []) if 0.5 <= a['usage'] < 0.8]
    if auto_inc_danger:
        items = ', '.join(f'{a["db"]}.{a["table"]}({a["usage"]*100:.0f}%)' for a in auto_inc_danger[:5])
        zh_suffix = f' 等 {len(auto_inc_danger)} 张表' if len(auto_inc_danger) > 5 else ''
        en_suffix = f' and {len(auto_inc_danger)} more tables' if len(auto_inc_danger) > 5 else ''
        suggestions.append(('danger', 0,
            f'Auto-increment primary key approaching overflow: {items}{en_suffix}. Failure to act will cause write failures. Immediate ALTER TABLE to BIGINT recommended',
            f'⚠️ 自增主键即将溢出: {items}{zh_suffix}，不处理将导致写入失败，建议立即 ALTER TABLE 改用 BIGINT'))
    if auto_inc_warn:
        items = ', '.join(f'{a["db"]}.{a["table"]}({a["usage"]*100:.0f}%)' for a in auto_inc_warn[:5])
        zh_suffix = f' 等 {len(auto_inc_warn)} 张表' if len(auto_inc_warn) > 5 else ''
        en_suffix = f' and {len(auto_inc_warn)} more tables' if len(auto_inc_warn) > 5 else ''
        suggestions.append(('warn', 30,
            f'Auto-increment key usage exceeds 50%: {items}{en_suffix}. Plan primary key type migration in advance',
            f'自增主键使用率超 50%: {items}{zh_suffix}，建议提前规划主键类型变更'))

    # ═══ Priority 1: Long transactions (active blocker) ═══
    si = data.get('session_info')
    if si and si.get('nodes'):
        total_abnormal = 0
        max_trx_dur = 0
        for sd in si['nodes'].values():
            for s in sd.get('SessionList', []):
                trx = s.get('TrxDuration', 0)
                if trx > 10:
                    total_abnormal += 1
                    if trx > max_trx_dur:
                        max_trx_dur = trx
        if total_abnormal > 0:
            if max_trx_dur > 300:
                suggestions.append(('danger', 1,
                    f'{total_abnormal} long-running uncommitted transactions detected (longest {max_trx_dur}s), blocking other sessions and causing undo log bloat. Immediate termination or commit recommended',
                    f'存在 {total_abnormal} 个长事务未提交（最长 {max_trx_dur}s），正在阻塞其他会话并导致 undo 膨胀，建议立即 KILL 或联系业务方提交'))
            else:
                suggestions.append(('warn', 31,
                    f'{total_abnormal} long-running uncommitted transactions detected (longest {max_trx_dur}s). Monitor for uncommitted transactions',
                    f'存在 {total_abnormal} 个长事务未提交（最长 {max_trx_dur}s），建议关注是否有未提交事务'))

    # ═══ Priority 2: Correlated resource issues ═══
    if resource_usage:
        c = res.get('cluster', {})

        # --- CPU correlation: peak + alerts + slow SQL ---
        cpu_peak = c.get('cpu_peak', 0)
        if cpu_peak > 80:
            _, peak_nid, peak_role, peak_time = _peak_node_info(node_ts, 'cpu', nodes_res)
            zh_time = f'（峰值 {peak_time}' if peak_time else '（'
            en_time = f' (peak at {peak_time}' if peak_time else ' ('
            zh_node = f'，节点 {peak_nid}({peak_role})' if peak_nid else ''
            en_node = f', node {peak_nid}({peak_role})' if peak_nid else ''
            zh_time += zh_node
            en_time += en_node

            zh_parts = [f'CPU 峰值 {cpu_peak:.1f}%{zh_time}）']
            en_parts = [f'CPU peak {cpu_peak:.1f}%{en_time})']

            if cpu_alerts:
                zh_parts.append(f'触发 {len(cpu_alerts)} 次报警')
                en_parts.append(f'{len(cpu_alerts)} alerts triggered')
                alert_covered = True
            if top_sql and data['slow_total'] > 0:
                zh_parts.append(f'关联 TOP1 慢 SQL: {top_sql["db"]}.{top_sql["sql_text"][:50]}（{top_sql["count"]}次，最大耗时 {top_sql["max_time"]}s）')
                en_parts.append(f'correlated with TOP1 slow SQL: {top_sql["db"]}.{top_sql["sql_text"][:50]} ({top_sql["count"]} times, max {top_sql["max_time"]}s)')
                slow_covered = True

            if len(zh_parts) > 1:
                zh_text = '，'.join(zh_parts) + '，建议优先优化该 SQL 以降低 CPU 消耗'
                en_text = ', '.join(en_parts) + '. Prioritize optimizing this SQL to reduce CPU consumption'
            else:
                zh_text = zh_parts[0] + '，建议排查高消耗 SQL 并考虑升级规格或增加只读节点'
                en_text = en_parts[0] + '. Investigate high-consumption SQL and consider upgrading specs or adding read-only nodes'

            suggestions.append(('danger', 2, en_text, zh_text))
            cpu_covered = True
        elif cpu_peak > 60:
            _, _, _, peak_time = _peak_node_info(node_ts, 'cpu', nodes_res)
            zh_time = f'（峰值 {peak_time}）' if peak_time else ''
            en_time = f' (peak at {peak_time})' if peak_time else ''
            suggestions.append(('warn', 32,
                f'CPU peak {cpu_peak:.1f}%{en_time}, moderately high load. Continue monitoring the trend',
                f'CPU 峰值 {cpu_peak:.1f}%{zh_time}，负载偏高，建议持续关注趋势'))
            cpu_covered = True

        # Per-node CPU imbalance
        if not cpu_covered or cpu_peak <= 80:
            cpu_danger_nodes = []
            for nid, nd in nodes_res.items():
                if nd.get('cpu_peak', 0) > 80 and cpu_peak <= 80:
                    t = _peak_time_str(node_ts.get(nid, {}).get('cpu', []))
                    cpu_danger_nodes.append(f'{nid}({nd.get("role_short","RO")}) {nd["cpu_peak"]:.1f}%' + (f' @{t}' if t else ''))
            if cpu_danger_nodes:
                suggestions.append(('danger', 2,
                    f'Node CPU peak exceeds 80%: {", ".join(cpu_danger_nodes)}. Unbalanced load detected, review read-write splitting routing strategy',
                    f'节点 CPU 峰值超 80%：{"、".join(cpu_danger_nodes)}，负载不均衡，建议检查读写分离路由策略'))

        # --- Memory ---
        mem_peak = c.get('mem_peak', 0)
        if mem_peak > 95:
            _, _, _, peak_time = _peak_node_info(node_ts, 'memory', nodes_res)
            zh_time = f'（峰值 {peak_time}）' if peak_time else ''
            en_time = f' (peak at {peak_time})' if peak_time else ''
            suggestions.append(('danger', 2,
                f'Memory peak {mem_peak:.1f}%{en_time}, OOM risk. Check buffer pool configuration and memory-intensive queries',
                f'内存峰值 {mem_peak:.1f}%{zh_time}，存在 OOM 风险，建议检查 buffer pool 配置和内存消耗大的查询'))
        elif mem_peak > 90:
            suggestions.append(('warn', 32,
                f'Memory peak {mem_peak:.1f}%, approaching limit. Monitor for memory leaks or large result set queries',
                f'内存峰值 {mem_peak:.1f}%，接近上限，建议关注是否有内存泄漏或大结果集查询'))
        mem_danger_nodes = []
        for nid, nd in nodes_res.items():
            if nd.get('mem_peak', 0) > 95 and mem_peak <= 95:
                mem_danger_nodes.append(f'{nid}({nd.get("role_short","RO")}) {nd["mem_peak"]:.1f}%')
        if mem_danger_nodes:
            suggestions.append(('danger', 2,
                f'Node memory peak exceeds 95%: {", ".join(mem_danger_nodes)}, OOM risk',
                f'节点内存峰值超 95%：{"、".join(mem_danger_nodes)}，存在 OOM 风险'))

        # --- Disk ---
        disk_pct = c.get('disk_peak_pct', 0)
        if disk_pct > 85:
            suggestions.append(('danger', 2,
                f'Disk usage {disk_pct:.1f}%, approaching capacity limit. Clean up unused data or expand storage promptly',
                f'空间使用率 {disk_pct:.1f}%，接近容量上限，建议尽快清理无用数据或扩容'))
        elif disk_pct > 70:
            suggestions.append(('warn', 32,
                f'Disk usage {disk_pct:.1f}%. Plan storage expansion ahead to prevent write failures from sudden data growth',
                f'空间使用率 {disk_pct:.1f}%，建议提前规划扩容，避免突发写入导致磁盘写满'))

        # --- IOPS correlation: peak + slow SQL with high scan rows ---
        iops_danger_nodes = []
        iops_warn_nodes = []
        iops_avg_warn_nodes = []
        for nid, nd in nodes_res.items():
            iops_usage_peak = min(nd.get('iops_usage_peak', 0), 100.0)
            iops_usage_avg = nd.get('iops_usage_avg', 0)
            rs = nd.get('role_short', 'RO')
            t = _peak_time_str(node_ts.get(nid, {}).get('iops', []))
            if iops_usage_peak > 80:
                iops_danger_nodes.append((nid, rs, iops_usage_peak, t))
            elif iops_usage_peak > 60:
                iops_warn_nodes.append(f'{nid}({rs}) {iops_usage_peak:.1f}%')
            if iops_usage_avg > 60:
                iops_avg_warn_nodes.append(f'{nid}({rs}) {iops_usage_avg:.1f}%')

        if iops_danger_nodes:
            top_iops_node = max(iops_danger_nodes, key=lambda x: x[2])
            nid, rs, peak_val, t = top_iops_node
            zh_time = f'，峰值 {t}' if t else ''
            en_time = f', peak at {t}' if t else ''
            # Correlate with high-scan-rows slow SQL
            high_scan_sql = next((s for s in slow_logs_list if s.get('avg_parse_rows', 0) > 100000), None)
            if high_scan_sql and not slow_covered:
                zh_text = (f'IOPS 使用率达到瓶颈（节点 {nid}({rs}) {peak_val:.0f}%{zh_time}），'
                           f'可能由全表扫描引起: {high_scan_sql["db"]}.{high_scan_sql["sql_text"][:50]}（扫描 {high_scan_sql["avg_parse_rows"]:,} 行），建议添加索引')
                en_text = (f'IOPS usage reached bottleneck (node {nid}({rs}) {peak_val:.0f}%{en_time}), '
                           f'possibly caused by full table scan: {high_scan_sql["db"]}.{high_scan_sql["sql_text"][:50]} (scanned {high_scan_sql["avg_parse_rows"]:,} rows). Add indexes recommended')
                slow_covered = True
            else:
                zh_nodes_str = '、'.join(f'{n}({r}) {v:.0f}%' for n, r, v, _ in iops_danger_nodes)
                en_nodes_str = ', '.join(f'{n}({r}) {v:.0f}%' for n, r, v, _ in iops_danger_nodes)
                zh_text = f'IOPS 使用率峰值达到瓶颈：{zh_nodes_str}{zh_time}，建议优化全表扫描类 SQL 或升级存储规格'
                en_text = f'IOPS usage peak reached bottleneck: {en_nodes_str}{en_time}. Optimize full table scan SQL or upgrade storage specs'
            if iops_alerts:
                zh_text += f'（已触发 {len(iops_alerts)} 次报警）'
                en_text += f' ({len(iops_alerts)} alerts triggered)'
                alert_covered = True
            suggestions.append(('danger', 2, en_text, zh_text))
            iops_covered = True

        if iops_warn_nodes:
            suggestions.append(('warn', 32,
                f'IOPS usage peak exceeds 60%: {", ".join(iops_warn_nodes)}, moderately high IO load',
                f'IOPS 使用率峰值超 60%：{"、".join(iops_warn_nodes)}，IO 负载偏高'))
        if iops_avg_warn_nodes:
            suggestions.append(('warn', 32,
                f'IOPS usage average consistently high: {", ".join(iops_avg_warn_nodes)}, sustained IO pressure detected',
                f'IOPS 使用率均值持续偏高：{"、".join(iops_avg_warn_nodes)}，存在持续性 IO 压力'))

        # --- Connections ---
        conn_pct = c.get('conn_peak_pct', 0)
        if conn_pct > 80:
            suggestions.append(('danger', 2,
                f'Connection usage peak {conn_pct:.1f}%, approaching limit. Check connection pool configuration and investigate potential connection leaks',
                f'连接使用率峰值 {conn_pct:.1f}%，接近上限，建议检查连接池配置并排查是否存在连接泄漏'))
        elif conn_pct > 60:
            suggestions.append(('warn', 32,
                f'Connection usage peak {conn_pct:.1f}%. Optimize max connections in connection pool configuration',
                f'连接使用率峰值 {conn_pct:.1f}%，建议优化连接池最大连接数配置'))
        conn_danger_nodes = []
        for nid, nd in nodes_res.items():
            if nd.get('conn_pct', 0) > 80 and conn_pct <= 80:
                conn_danger_nodes.append(f'{nid}({nd.get("role_short","RO")}) {nd["conn_pct"]:.1f}%')
        if conn_danger_nodes:
            suggestions.append(('danger', 2,
                f'Node connection usage exceeds 80%: {", ".join(conn_danger_nodes)}. Check application connection pools or increase max_connections',
                f'节点连接使用率超 80%：{"、".join(conn_danger_nodes)}，建议检查应用端连接池或增大 max_connections'))

    # ═══ Slow logs (only if not already covered by correlation) ═══
    if not slow_covered:
        if data['slow_total'] > 10:
            zh_detail = ''
            en_detail = ''
            if top_sql:
                zh_detail = f'，TOP1: {top_sql["db"]}.{top_sql["sql_text"][:50]}（{top_sql["count"]}次，最大耗时 {top_sql["max_time"]}s）'
                en_detail = f', TOP1: {top_sql["db"]}.{top_sql["sql_text"][:50]} ({top_sql["count"]} times, max {top_sql["max_time"]}s)'
            suggestions.append(('warn', 33,
                f'High volume of slow queries ({data["slow_total"]} entries). Focus on optimizing frequently occurring slow SQL{en_detail}',
                f'慢日志较多（{data["slow_total"]} 条），建议重点优化高频慢 SQL{zh_detail}'))
        elif data['slow_total'] > 0:
            suggestions.append(('info', 40,
                f'{data["slow_total"]} slow queries detected. Recommend monitoring',
                f'存在 {data["slow_total"]} 条慢查询，建议关注'))

    # ═══ Space anomalies ═══
    anomalies = space['anomalies']
    if anomalies:
        no_idx = [a for a in anomalies if a['type'] == '大表无索引']
        if no_idx:
            tables = ', '.join(f'{i["db"]}.{i["table"]}' for i in no_idx[:3])
            zh_suffix = f' 等 {len(no_idx)} 张表' if len(no_idx) > 3 else ''
            en_suffix = f' and {len(no_idx)} more tables' if len(no_idx) > 3 else ''
            suggestions.append(('warn', 33,
                f'Large tables without indexes: {tables}{en_suffix}. Add appropriate indexes to improve query performance',
                f'大表无索引: {tables}{zh_suffix}，建议添加合适索引提升查询性能'))
        frag = [a for a in anomalies if a['type'] == '空间碎片']
        if frag:
            tables = ', '.join(f'{i["db"]}.{i["table"]}' for i in frag[:3])
            zh_suffix = f' 等 {len(frag)} 张表' if len(frag) > 3 else ''
            en_suffix = f' and {len(frag)} more tables' if len(frag) > 3 else ''
            suggestions.append(('warn', 33,
                f'High space fragmentation: {tables}{en_suffix}. Run OPTIMIZE TABLE to reclaim space',
                f'空间碎片过高: {tables}{zh_suffix}，建议执行 OPTIMIZE TABLE 回收碎片'))

    # ═══ Alert history (only if not already covered by correlation) ═══
    if not alert_covered and alerts:
        p3 = [a for a in alerts if a.get('level') == 'P3']
        uncovered_p1p2 = [a for a in p1p2_alerts if a not in cpu_alerts and a not in iops_alerts]
        if uncovered_p1p2:
            metrics = {}
            for a in uncovered_p1p2:
                key = a.get('rule_name') or a.get('metric', 'unknown')
                metrics[key] = metrics.get(key, 0) + 1
            sorted_metrics = sorted(metrics.items(), key=lambda x: -x[1])[:3]
            zh_detail = '、'.join(f'{k}({v}次)' for k, v in sorted_metrics)
            en_detail = ', '.join(f'{k}({v} times)' for k, v in sorted_metrics)
            suggestions.append(('danger', 2,
                f'{len(uncovered_p1p2)} high-priority alerts (P1/P2) triggered in the last {config._INSPECT_DAYS} days: {en_detail}. Root cause investigation recommended',
                f'近 {config._INSPECT_DAYS} 天触发 {len(uncovered_p1p2)} 次高优先级报警（P1/P2）：{zh_detail}，建议排查根因'))
        elif p3:
            metrics = {}
            for a in p3:
                key = a.get('rule_name') or a.get('metric', 'unknown')
                metrics[key] = metrics.get(key, 0) + 1
            sorted_metrics = sorted(metrics.items(), key=lambda x: -x[1])[:3]
            zh_detail = '、'.join(f'{k}({v}次)' for k, v in sorted_metrics)
            en_detail = ', '.join(f'{k}({v} times)' for k, v in sorted_metrics)
            suggestions.append(('warn', 33,
                f'{len(p3)} alerts (P3) triggered in the last {config._INSPECT_DAYS} days: {en_detail}. Monitor alert frequency',
                f'近 {config._INSPECT_DAYS} 天触发 {len(p3)} 次报警（P3）：{zh_detail}，建议关注触发频率'))

    # ═══ Info-level ═══
    if version_info and not bi['is_latest']:
        suggestions.append(('info', 40,
            f'Kernel version upgrade available: current {bi["revision_version"]} -> latest {bi["latest_version"]}. Brief service interruption expected during upgrade',
            f'内核版本可升级: 当前 {bi["revision_version"]} → 最新 {bi["latest_version"]}，升级期间业务会有短暂闪断'))
    if bi.get('is_essd') and not bi.get('storage_auto_scale'):
        suggestions.append(('warn', 33,
            'ESSD storage auto-scaling is not enabled. Enable it to prevent disk from becoming full',
            'ESSD 存储未开启自动扩展，建议开启以免磁盘被写满'))

    # Sort by priority (lower number = more urgent)
    return [(level, en, zh) for level, _, en, zh in sorted(suggestions, key=lambda x: x[1])]
