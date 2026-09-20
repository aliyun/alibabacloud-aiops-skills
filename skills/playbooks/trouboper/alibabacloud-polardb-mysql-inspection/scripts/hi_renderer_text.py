# -*- coding: utf-8 -*-
"""纯文本格式巡检报告渲染（拆分自 health-inspect.py 的 render_text）"""

import json
import os
from datetime import datetime, timedelta, timezone

import hi_config as config
from hi_utils import format_bytes, format_mb, status_icon


# ─── Text Renderer ────────────────────────────────────────────────────────────

def render_text(data):
    lines = []
    p = lines.append
    bi = data['basic_info']

    p('')
    p('┌' + '─' * 78 + '┐')
    p('│' + ' PolarDB MySQL 实例健康巡检报告'.center(68) + '│')
    p('└' + '─' * 78 + '┘')
    p(f'  巡检时间: {data["inspect_time"]}')
    p(f'  实例 ID:  {data["cluster_id"]}')
    p(f'  Region:   {data["region"]}')
    if config._CLI_PROFILE:
        p(f'  Profile:  {config._CLI_PROFILE}')

    # 一、基本信息
    p('')
    p('═' * 80)
    p(' 一、实例基本信息')
    p('═' * 80)
    p('')
    p(f'  ┌{"─"*30}┬{"─"*46}┐')
    p(f'  │ {"项目":<27} │ {"值":<43} │')
    p(f'  ├{"─"*30}┼{"─"*46}┤')
    p(f'  │ {"数据库类型":<26} │ {bi["db_type"]:<44} │')
    p(f'  │ {"大版本":<27} │ {bi["db_type"]+" "+bi["db_version"]:<44} │')
    p(f'  │ {"内核小版本":<26} │ {bi["revision_version"]:<44} │')
    p(f'  │ {"最新可用版本":<25} │ {bi["latest_version"]:<44} │')
    vs = "✅ 已是最新" if bi['is_latest'] else "⬆️  可升级"
    p(f'  │ {"版本状态":<26} │ {vs:<43} │')
    p(f'  │ {"Proxy 版本":<26} │ {bi["proxy_version"]:<44} │')
    p(f'  │ {"集群状态":<27} │ {bi["status"]:<44} │')
    p(f'  │ {"存储类型":<27} │ {bi["storage_type"]:<44} │')
    p(f'  │ {"集群类别":<27} │ {bi.get("category_zh", bi["category"]):<44} │')
    p(f'  │ {"已用存储":<27} │ {bi["storage_used_str"]:<44} │')
    p(f'  │ {"存储容量":<27} │ {(bi["storage_space_str"] or bi["storage_max_str"]):<44} │')
    if bi.get('is_psl'):
        auto_expand_txt = '自动扩展（PSL 存储）'
    elif bi.get('is_essd'):
        auto_expand_txt = '已开启（上限 ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + '）' if bi.get("storage_auto_scale") else '未开启'
    else:
        auto_expand_txt = 'N/A'
    p(f'  │ {"自动扩展":<27} │ {auto_expand_txt:<44} │')
    p(f'  └{"─"*30}┴{"─"*46}┘')

    nl = data['nodes']
    p('')
    p(f'  节点详情 ({len(nl)} 个节点):')
    p(f'  ┌{"─"*26}┬{"─"*8}┬{"─"*10}┬{"─"*26}┬{"─"*6}┬{"─"*10}┬{"─"*10}┬{"─"*10}┐')
    p(f'  │ {"节点ID":<24} │ {"角色":<6} │ {"状态":<8} │ {"规格":<24} │ {"CPU":<4} │ {"内存":<8} │ {"最大连接":<8} │ {"最大IOPS":<8} │')
    p(f'  ├{"─"*26}┼{"─"*8}┼{"─"*10}┼{"─"*26}┼{"─"*6}┼{"─"*10}┼{"─"*10}┼{"─"*10}┤')
    for nd in nl:
        p(f'  │ {nd["id"]:<24} │ {nd["role"]:<6} │ {nd["status"]:<8} │ {nd["class"]:<24} │ {str(nd["cpu"])+"核":<4} │ {nd["mem"]:<8} │ {str(nd["max_conn"]):<8} │ {str(nd["max_iops"]):<8} │')
    p(f'  ├{"─"*26}┴{"─"*8}┴{"─"*10}┴{"─"*26}┴{"─"*6}┼{"─"*10}┼{"─"*10}┼{"─"*10}┤')
    p(f'  │ {"合计":<76} │ {str(data["total_max_conn"]):<8} │ {str(data["total_max_iops"]):<8} │ {"":8} │')
    p(f'  └{"─"*78}┴{"─"*10}┴{"─"*10}┴{"─"*10}┘')

    # 二、当前会话
    p('')
    p('═' * 80)
    p(' 二、当前会话')
    p('═' * 80)
    si = data.get('session_info')
    if si and si.get('nodes'):
        for node_label, sd in si['nodes'].items():
            p('')
            p(f'  ┌─ {node_label}')
            p(f'  │  总连接: {sd.get("TotalSessionCount", 0)}    活跃: {sd.get("ActiveSessionCount", 0)}    最大活跃时间: {sd.get("MaxActiveTime", 0)}s')
            session_list = sd.get('SessionList', [])
            active_s = [s for s in session_list if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump')]
            abnormal_s = [s for s in session_list if s.get('TrxDuration', 0) > 10]
            binlog_s = [s for s in session_list if s.get('Command', '').startswith('Binlog Dump')]
            if active_s:
                p(f'  │')
                p(f'  │  【活跃会话（{len(active_s)}）】')
                p(f'  │  {"ID":<10}{"User":<15}{"Host":<22}{"DB":<15}{"Command":<10}{"Time":<8}{"TrxDur":<8}{"State":<18}{"SQL"}')
                p(f'  │  {"─"*10}{"─"*15}{"─"*22}{"─"*15}{"─"*10}{"─"*8}{"─"*8}{"─"*18}{"─"*30}')
                for s in active_s[:20]:
                    sql = (s.get('SqlText', '') or '')[:40]
                    host = str(s.get('Client', s.get('Host', '')))
                    trx_dur = s.get('TrxDuration', '')
                    trx_str = f'{trx_dur}s' if trx_dur else '-'
                    state = (s.get('State', '') or '')[:18]
                    p(f'  │  {s.get("SessionId",""):<10}{s.get("User",""):<15}{host:<22}{s.get("DbName",""):<15}{s.get("Command",""):<10}{s.get("Time",0):<8}{trx_str:<8}{state:<18}{sql}')
            if abnormal_s:
                p(f'  │')
                p(f'  │  【异常会话（长时间未提交的事务>10s）】')
                p(f'  │  {"ID":<10}{"User":<15}{"Host":<22}{"DB":<15}{"Command":<10}{"Time":<8}{"TrxDur":<8}{"State":<18}{"SQL"}')
                p(f'  │  {"─"*10}{"─"*15}{"─"*22}{"─"*15}{"─"*10}{"─"*8}{"─"*8}{"─"*18}{"─"*30}')
                for s in abnormal_s[:20]:
                    host = str(s.get('Client', s.get('Host', '')))
                    state = (s.get('State', '') or '')[:18]
                    trx_dur = s.get('TrxDuration', '')
                    trx_str = f'{trx_dur}s' if trx_dur else '-'
                    sql = (s.get('SqlText', '') or '')[:40]
                    p(f'  │  {s.get("SessionId",""):<10}{s.get("User",""):<15}{host:<22}{s.get("DbName",""):<15}{s.get("Command",""):<10}{s.get("Time",0):<8}{trx_str:<8}{state:<18}{sql}')
            if len(binlog_s) > 10:
                p(f'  │')
                p(f'  │  ⚠️ Binlog Dump 会话（{len(binlog_s)} 个）— 下游消费 Binlog 连接较多，可能占用较高 IOPS')
            user_stats = sd.get('UserStats', [])
            if user_stats:
                p(f'  │')
                p(f'  │  【按用户统计】')
                p(f'  │  {"用户":<20}{"总连接":<10}{"活跃":<10}')
                p(f'  │  {"─"*20}{"─"*10}{"─"*10}')
                for u in user_stats:
                    p(f'  │  {u.get("Key",""):<20}{u.get("TotalCount",0):<10}{u.get("ActiveCount",0):<10}')
            if not active_s and not abnormal_s and len(binlog_s) <= 10:
                p(f'  │  当前无活跃或异常会话')
            p(f'  └────────────────────────────────────────────────────────────')
    else:
        p('\n  ⚠️ 未获取到会话信息')

    # 三、资源使用率
    p('')
    p('═' * 80)
    p(' 三、资源使用率（最近 7 天）')
    p('═' * 80)
    res = data.get('resource', {})
    if res.get('cluster'):
        c = res['cluster']
        tmc = data['total_max_conn']
        p('')
        p('  【集群总览】')
        p(f'  ┌{"─"*16}┬{"─"*22}┬{"─"*22}┬{"─"*8}┐')
        p(f'  │ {"指标":<13} │ {"平均值":<19} │ {"峰值":<19} │ {"状态":<5} │')
        p(f'  ├{"─"*16}┼{"─"*22}┼{"─"*22}┼{"─"*8}┤')
        cpu_a, cpu_p = f'{c["cpu_avg"]:.2f}%', f'{c["cpu_peak"]:.2f}%'
        mem_a, mem_p = f'{c["mem_avg"]:.2f}%', f'{c["mem_peak"]:.2f}%'
        dsk_a = f'{c["disk_avg_pct"]:.2f}% ({format_mb(c["disk_avg_mb"])})'
        dsk_p = f'{c["disk_peak_pct"]:.2f}% ({format_mb(c["disk_peak_mb"])})'
        io_a, io_p = f'{c["io_avg"]:.0f} KB/s', f'{c["io_peak"]:.0f} KB/s'
        cn_a = f'{c["conn_avg"]:.0f}/{tmc} ({c["conn_avg_pct"]:.1f}%)'
        cn_p = f'{c["conn_peak"]:.0f}/{tmc} ({c["conn_peak_pct"]:.1f}%)'
        p(f'  │ {"CPU":<14} │ {cpu_a:<20} │ {cpu_p:<20} │ {status_icon(c["cpu_peak"]):<6} │')
        p(f'  │ {"内存":<13} │ {mem_a:<20} │ {mem_p:<20} │ {status_icon(c["mem_peak"], "memory"):<6} │')
        p(f'  │ {"空间":<13} │ {dsk_a:<20} │ {dsk_p:<20} │ {status_icon(c["disk_peak_pct"], "space"):<6} │')
        p(f'  │ {"IO吞吐":<12} │ {io_a:<20} │ {io_p:<20} │ {"🔵":<6} │')
        p(f'  │ {"连接数":<13} │ {cn_a:<20} │ {cn_p:<20} │ {status_icon(c["conn_peak_pct"]):<6} │')
        p(f'  └{"─"*16}┴{"─"*22}┴{"─"*22}┴{"─"*8}┘')

        p('')
        p('  【各节点详情】')
        for nid, nd in res.get('nodes', {}).items():
            p('')
            p(f'  ▸ {nid} ({nd["role"]})')
            p(f'    CPU:    平均 {nd["cpu_avg"]:.2f}%  峰值 {nd["cpu_peak"]:.2f}%  {status_icon(nd["cpu_peak"])}')
            p(f'    内存:   平均 {nd["mem_avg"]:.2f}%  峰值 {nd["mem_peak"]:.2f}%  {status_icon(nd["mem_peak"], "memory")}')
            p(f'    连接:   平均 {nd["conn_avg"]:.0f}  峰值 {nd["conn_peak"]:.0f}  使用率 {nd["conn_pct"]:.1f}% (上限 {nd["max_conn"]})  {status_icon(nd["conn_pct"])}')
            p(f'    活跃连接: 平均 {nd["active_avg"]:.0f}  峰值 {nd["active_peak"]:.0f}')
            if nd.get('iops_peak', 0) > 0:
                p(f'    IOPS:   平均 {nd["iops_avg"]:.0f}  峰值 {nd["iops_peak"]:.0f}')
    else:
        p('\n  ⚠️ 未获取到资源使用率数据')

    # 四、空间巡检
    p('')
    p('═' * 80)
    p(' 四、空间巡检')
    p('═' * 80)
    space = data.get('space', {})
    p('')
    p('  4.1 库表空间 TOP20')
    p('')
    tl = space.get('table_list', [])
    if tl:
        p(f'  {"#":<4}{"数据库":<20}{"表名":<28}{"总空间":<12}{"数据":<12}{"索引":<12}{"行数":<14}')
        p(f'  {"─"*4}{"─"*20}{"─"*28}{"─"*12}{"─"*12}{"─"*12}{"─"*14}')
        for i, t in enumerate(tl, 1):
            rows_s = f'{t["rows"]:,}' if t['rows'] else '0'
            p(f'  {i:<4}{t["db"]:<20}{t["table"]:<28}{t["total_str"]:<12}{t["data_str"]:<12}{t["index_str"]:<12}{rows_s:<14}')
        if space.get('total_used'):
            p(f'\n  总使用空间: {format_bytes(space["total_used"])}')
        di = space.get('daily_inc', 0)
        if di:
            p(f'  日均增长:   {"+" if di > 0 else "-"}{format_bytes(abs(di))}{" (空间在缩减)" if di < 0 else ""}')
    else:
        p('  ⚠️ 空间分析未返回表统计数据')

    p('')
    p('  4.2 空间变化趋势')
    p('')
    disk_ts = res.get('cluster_ts', {}).get('disk', [])
    if disk_ts and len(disk_ts) >= 2:
        first_mb, last_mb = disk_ts[0][1], disk_ts[-1][1]
        days = (disk_ts[-1][0] - disk_ts[0][0]) / (86400 * 1000) or 1
        daily = (last_mb - first_mb) / days
        p(f'  起始: {format_mb(first_mb)}  →  当前: {format_mb(last_mb)}')
        p(f'  日均{"增长" if daily >= 0 else "减少"}: {"+" if daily >= 0 else "-"}{format_mb(abs(daily))}')
    else:
        p('  ⚠️ 无磁盘趋势数据')

    p('')
    p('  4.3 异常列表')
    p('')
    anom = space.get('anomalies', [])
    if anom:
        p(f'  {"类型":<12}{"数据库":<20}{"表名":<28}{"详情"}')
        p(f'  {"─"*12}{"─"*20}{"─"*28}{"─"*30}')
        for a in anom:
            p(f'  {a["type"]:<12}{a["db"]:<20}{a["table"]:<28}{a["detail"]}')
    else:
        p('  ✅ 未发现异常')

    # 五、慢日志
    p('')
    p('═' * 80)
    p(' 五、慢日志统计（最近 7 天）')
    p('═' * 80)
    sl = data.get('slow_logs', [])
    if sl:
        p('')
        p(f'  {"#":<4}{"数据库":<14}{"SQLHASH":<36}{"次数":<8}{"总耗时(s)":<11}{"最大(s)":<9}{"平均扫描行数":<14}{"平均返回行数":<14}{"SQL 摘要"}')
        p(f'  {"─"*4}{"─"*14}{"─"*36}{"─"*8}{"─"*11}{"─"*9}{"─"*12}{"─"*12}{"─"*40}')
        for i, s in enumerate(sl, 1):
            sql = s['sql_text'][:48] + ('...' if len(s['sql_text']) > 48 else '')
            p(f'  {i:<4}{s["db"]:<14}{s.get("sql_hash","")[:34]:<36}{s["count"]:<8}{s["total_time"]:<11}{s["max_time"]:<9}{s.get("avg_parse_rows",0):<14}{s.get("avg_return_rows",0):<14}{sql}')
        p(f'\n  共计 {data["slow_total"]} 条慢查询统计')
    else:
        p('\n  ✅ 最近 7 天无慢日志记录')

    # 六、报警历史
    p('')
    p('═' * 80)
    p(' 六、报警历史（最近 7 天）')
    p('═' * 80)
    alerts = data.get('alert_history', [])
    if alerts:
        p('')
        p(f'  {"#":<4}{"时间":<22}{"级别":<6}{"规则":<12}{"指标":<28}{"节点":<26}{"当前值":<10}{"阈值":<8}{"通知状态"}')
        p(f'  {"─"*4}{"─"*22}{"─"*6}{"─"*12}{"─"*28}{"─"*26}{"─"*10}{"─"*8}{"─"*12}')
        for i, a in enumerate(alerts, 1):
            p(f'  {i:<4}{a["time"]:<22}{a["level"]:<6}{a.get("rule_name",""):<12}{a.get("metric","")[:26]:<28}{a.get("node_id",""):<26}{a.get("cur_value",""):<10}{a.get("threshold",""):<8}{a.get("send_status","")}')
        p(f'\n  共计 {len(alerts)} 条报警记录')
    else:
        p('\n  ✅ 最近 7 天无报警记录')

    # 七、结论
    p('')
    p('═' * 80)
    p(' 七、巡检结论与建议')
    p('═' * 80)
    p('')
    sug = data.get('suggestions', [])
    if not sug:
        p('  ✅ 巡检未发现明显问题，实例运行状态良好。')
    else:
        danger_items = [zh for level, en, zh in sug if level == 'danger']
        warn_items = [zh for level, en, zh in sug if level == 'warn']
        info_items = [zh for level, en, zh in sug if level == 'info']
        for label, items in [('🔴 高风险', danger_items), ('🟡 中风险', warn_items), ('🔵 低风险', info_items)]:
            if not items:
                continue
            p(f'  {label}')
            if len(items) == 1:
                p(f'    {items[0]}')
            else:
                for i, t in enumerate(items, 1):
                    p(f'    {i}. {t}')
            p('')
    p('')
    p('┌' + '─' * 78 + '┐')
    p('│' + ' 巡检完成'.center(72) + '│')
    p('└' + '─' * 78 + '┘')
    return '\n'.join(lines)
