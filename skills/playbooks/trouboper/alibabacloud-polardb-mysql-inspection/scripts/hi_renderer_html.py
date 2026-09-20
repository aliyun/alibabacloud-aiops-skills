# -*- coding: utf-8 -*-
"""HTML 格式巡检报告渲染：数据准备 + 章节按巡检项条件拼接（拆分自 health-inspect.py 的 render_html）

HTML 模板片段位于 hi_html_template.py，章节的取舍与重编号在模板拼接阶段完成
（见 hi_html_template.assemble_page），不再对生成后的 HTML 做正则删除。
"""

import json
import os
from datetime import datetime, timedelta, timezone

import hi_config as config
from hi_utils import _html_escape, format_bytes, format_mb, status_icon, _node_role_short
from hi_i18n import _i18n, L


# ─── HTML Renderer ────────────────────────────────────────────────────────────

def render_html(data, items=None):
    """渲染单实例 HTML 巡检报告。

    data  : collect_report_data() 产出的报告数据
    items : 选中的巡检项集合（config.ALL_ITEMS 的子集）；None = 全量模式，
            渲染所有章节。基本信息与结论建议为基础章节，任何模式下都保留。
    """
    # ===== Phase 1: 数据准备 =====
    # 选中巡检项在函数入口就固化，避免被后续局部变量遮蔽（None = 全量）
    selected_items = set(config.ALL_ITEMS) if items is None else set(items)

    bi = data['basic_info']
    nodes = data['nodes']
    res = data.get('resource', {})
    space = data.get('space', {})
    node_ts = res.get('node_ts', {})
    cluster_ts = res.get('cluster_ts', {})

    max_conn = nodes[0]['max_conn'] if nodes else 0

    def _badge(nd):
        rs = nd.get('role_short', 'RO')
        if rs == 'RW':
            return '<span class="badge badge-rw">RW</span>'
        elif rs == 'IMCI':
            return '<span class="badge badge-ro" style="background:#e8f5e9;color:#2e7d32;">IMCI</span>'
        return '<span class="badge badge-ro">RO</span>'

    def _rshort(nd):
        return nd.get('role_short', 'RO')

    vb = L('status_upgradable') if not bi['is_latest'] else L('status_latest')

    node_rows = ''
    for nd in nodes:
        node_rows += f'<tr><td>{nd["id"]}</td><td>{_badge(nd)}</td><td>{nd["status"]}</td><td>{nd["class"]}</td><td>{nd["cpu"]}{L("unit_cores")}</td><td>{nd["mem"]}</td><td>{nd["max_conn"]}</td><td>{nd["max_iops"]}</td></tr>\n'

    # Session HTML
    si = data.get('session_info')
    session_html = ''
    if si and si.get('nodes'):
        # Session summary across all nodes
        total_abnormal = 0
        total_binlog = 0
        total_active = 0
        total_all = 0
        max_trx_dur = 0
        for sd in si['nodes'].values():
            sl = sd.get('SessionList', [])
            total_all += sd.get('TotalSessionCount', 0)
            total_active += len([s for s in sl if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump')])
            node_abnormal = [s for s in sl if s.get('TrxDuration', 0) > 10]
            total_abnormal += len(node_abnormal)
            for s in node_abnormal:
                trx = s.get('TrxDuration', 0)
                if trx > max_trx_dur:
                    max_trx_dur = trx
            total_binlog += len([s for s in sl if s.get('Command', '').startswith('Binlog Dump')])
        summary_parts = []
        if total_abnormal > 0:
            summary_parts.append(f'<span class="suggestion danger">🔴 {_i18n(f"Found {total_abnormal} abnormal sessions (long uncommitted txn), longest {max_trx_dur}s", f"发现 {total_abnormal} 个异常会话（长事务未提交），最长事务持续 {max_trx_dur}s，请及时关注")}</span>')
        if total_binlog > 10:
            summary_parts.append(f'<span class="suggestion warn">🟡 {_i18n(f"High Binlog Dump connections ({total_binlog}), may consume significant IOPS", f"Binlog Dump 连接较多（{total_binlog} 个），可能占用较高 IOPS")}</span>')
        if not summary_parts:
            summary_parts.append(f'<span class="suggestion ok">🟢 {_i18n(f"Sessions normal, {total_all} total, {total_active} active", f"会话状态正常，共 {total_all} 个连接，{total_active} 个活跃")}</span>')
        session_html += '<div style="margin-bottom:1rem;">' + '<br>'.join(summary_parts) + '</div>'

        node_labels = list(si['nodes'].keys())
        default_idx = 0
        for i, lbl in enumerate(node_labels):
            role = si['nodes'][lbl].get('_role', '')
            if role in ('Writer', 'ReadWrite'):
                default_idx = i
                break

        options_html = ''.join(f'<option value="sess_node_{i}"{" selected" if i == default_idx else ""}>{_html_escape(lbl)}</option>' for i, lbl in enumerate(node_labels))
        session_html += f'<div style="margin-bottom:1rem;"><label style="font-weight:600;margin-right:0.5rem;">{L("lbl_select_node")}</label><select id="sessNodeSelect" onchange="(function(){{var sel=document.getElementById(\'sessNodeSelect\').value;document.querySelectorAll(\'.sess-node-panel\').forEach(function(el){{el.style.display=el.id===sel?\'block\':\'none\';}});}})()" style="padding:4px 12px;border:1px solid #d0d5dd;border-radius:6px;font-size:14px;">{options_html}</select></div>'

        for idx, (node_label, sd) in enumerate(si['nodes'].items()):
            display = 'block' if idx == default_idx else 'none'
            total_sess = sd.get('TotalSessionCount', 0)
            active_sess = sd.get('ActiveSessionCount', 0)
            max_time = sd.get('MaxActiveTime', 0)
            node_html = f'<p><strong>{L("lbl_total_sessions")}</strong>: {total_sess} &nbsp;&nbsp; <strong>{L("lbl_active_sessions")}</strong>: {active_sess} &nbsp;&nbsp; <strong>{L("lbl_max_active_time")}</strong>: {max_time}s</p>'

            session_list = sd.get('SessionList', [])

            # 1. Active sessions
            active_s = [s for s in session_list if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump')]
            abnormal_s = [s for s in session_list if s.get('TrxDuration', 0) > 10]
            binlog_s = [s for s in session_list if s.get('Command', '').startswith('Binlog Dump')]

            if active_s:
                rows = ''
                for s in active_s[:20]:
                    full_sql = _html_escape(s.get('SqlText', '') or '')
                    sql = _html_escape((s.get('SqlText', '') or '')[:60])
                    host = _html_escape(str(s.get('Client', s.get('Host', ''))))
                    trx_dur = s.get('TrxDuration', '')
                    trx_str = f'{trx_dur}s' if trx_dur else '-'
                    state = _html_escape(s.get('State', '') or '')
                    rows += f'<tr><td>{s.get("SessionId","")}</td><td>{_html_escape(s.get("User",""))}</td><td>{host}</td><td>{_html_escape(s.get("DbName",""))}</td><td>{s.get("Command","")}</td><td>{s.get("Time",0)}</td><td>{trx_str}</td><td>{state}</td><td class="sql-cell" title="{full_sql}">{sql}</td></tr>'
                node_html += f'<h4>{_i18n(f"Active Sessions ({len(active_s)})", f"活跃会话（{len(active_s)}）")}</h4><div class="table-scroll"><table><tr><th>ID</th><th>User</th><th>Host</th><th>DB</th><th>Command</th><th>Time(s)</th><th>TrxDuration</th><th>State</th><th>SQL</th></tr>{rows}</table></div>'

            # 2. Abnormal sessions
            if abnormal_s:
                rows = ''
                for s in abnormal_s[:20]:
                    time_val = s.get('Time', 0)
                    trx_dur = s.get('TrxDuration', '')
                    trx_str = f'{trx_dur}s' if trx_dur else '-'
                    host = _html_escape(str(s.get('Client', s.get('Host', ''))))
                    state = _html_escape(s.get('State', '') or '')
                    full_sql = _html_escape(s.get('SqlText', '') or '')
                    sql = _html_escape((s.get('SqlText', '') or '')[:60])
                    rows += f'<tr><td>{s.get("SessionId","")}</td><td>{_html_escape(s.get("User",""))}</td><td>{host}</td><td>{_html_escape(s.get("DbName",""))}</td><td>{s.get("Command","")}</td><td>{time_val}</td><td>{trx_str}</td><td>{state}</td><td class="sql-cell" title="{full_sql}">{sql}</td></tr>'
                node_html += f'<h4>{L("sub_abnormal_sessions")}</h4><div class="table-scroll"><table><tr><th>ID</th><th>User</th><th>Host</th><th>DB</th><th>Command</th><th>Time(s)</th><th>TrxDuration</th><th>State</th><th>SQL</th></tr>{rows}</table></div>'

            # 3. Binlog Dump
            if len(binlog_s) > 10:
                rows = ''
                for s in binlog_s[:20]:
                    rows += f'<tr><td>{s.get("SessionId","")}</td><td>{_html_escape(s.get("User",""))}</td><td>{s.get("Command","")}</td><td>{s.get("Time",0)}</td></tr>'
                node_html += f'<h4>{_i18n(f"Binlog Dump Sessions ({len(binlog_s)})", f"Binlog Dump 会话（{len(binlog_s)}）")}</h4><p class="suggestion warn">⚠️ {_i18n(f"High downstream Binlog connections ({len(binlog_s)}), may consume significant IOPS", f"下游消费 Binlog 连接较多（{len(binlog_s)} 个），可能占用较高 IOPS")}</p><div class="table-scroll"><table><tr><th>ID</th><th>User</th><th>Command</th><th>Time(s)</th></tr>{rows}</table></div>'

            # 4. User / Client / DB stats
            if 'ClientStats' not in sd and session_list:
                client_map = {}
                for s in session_list:
                    host = s.get('Client', s.get('Host', ''))
                    if ':' in str(host):
                        host = str(host).split(':')[0]
                    if not host:
                        continue
                    if host not in client_map:
                        client_map[host] = {'total': 0, 'active': 0, 'users': set()}
                    client_map[host]['total'] += 1
                    if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump'):
                        client_map[host]['active'] += 1
                    user = s.get('User', '')
                    if user:
                        client_map[host]['users'].add(user)
                sd['ClientStats'] = sorted(
                    [{'Key': ip, 'TotalCount': v['total'], 'ActiveCount': v['active'],
                      'UserList': ', '.join(sorted(v['users']))} for ip, v in client_map.items()],
                    key=lambda x: x['TotalCount'], reverse=True)
            if 'DbStats' not in sd and session_list:
                db_map = {}
                for s in session_list:
                    db = s.get('DbName', '') or ''
                    if db not in db_map:
                        db_map[db] = {'total': 0, 'active': 0}
                    db_map[db]['total'] += 1
                    if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump'):
                        db_map[db]['active'] += 1
                sd['DbStats'] = sorted(
                    [{'Key': db, 'TotalCount': v['total'], 'ActiveCount': v['active']}
                     for db, v in db_map.items()],
                    key=lambda x: x['TotalCount'], reverse=True)

            grid_parts = []
            user_stats = sd.get('UserStats', [])
            if user_stats:
                rows = ''.join(f'<tr><td>{_html_escape(u.get("Key",""))}</td><td>{u.get("TotalCount",0)}</td><td>{u.get("ActiveCount",0)}</td></tr>' for u in user_stats)
                grid_parts.append(f'<div><h4>{L("sub_by_user")}</h4><table><tr><th>{L("th_user")}</th><th>{L("th_total_conn")}</th><th>{L("th_active")}</th></tr>{rows}</table></div>')
            client_stats = sd.get('ClientStats', [])
            if client_stats:
                rows = ''
                for c in client_stats:
                    ul = c.get('UserList', '')
                    if isinstance(ul, list):
                        ul = ', '.join(str(u) for u in ul)
                    rows += f'<tr><td>{_html_escape(c.get("Key",""))}</td><td>{c.get("TotalCount",0)}</td><td>{c.get("ActiveCount",0)}</td><td>{_html_escape(str(ul))}</td></tr>'
                grid_parts.append(f'<div><h4>{L("sub_by_client_ip")}</h4><table><tr><th>{L("th_client_ip")}</th><th>{L("th_total_conn")}</th><th>{L("th_active")}</th><th>{L("th_user")}</th></tr>{rows}</table></div>')
            db_stats = sd.get('DbStats', [])
            if db_stats:
                rows = ''.join(f'<tr><td>{_html_escape(d.get("Key","")) or L("lbl_none_db")}</td><td>{d.get("TotalCount",0)}</td><td>{d.get("ActiveCount",0)}</td></tr>' for d in db_stats)
                grid_parts.append(f'<div><h4>{L("sub_by_database")}</h4><table><tr><th>{L("th_database")}</th><th>{L("th_total_conn")}</th><th>{L("th_active")}</th></tr>{rows}</table></div>')
            if grid_parts:
                node_html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem;margin:1rem 0;">' + ''.join(grid_parts) + '</div>'

            if not active_s and not abnormal_s and len(binlog_s) <= 10:
                node_html += f'<p>{L("msg_no_active_session")}</p>'

            session_html += f'<div id="sess_node_{idx}" class="sess-node-panel" style="display:{display};">{node_html}</div>'
    else:
        session_html = f'<p>{L("msg_no_session_info")}</p>'

    # Resource table (nodes as rows)
    res_nodes = res.get('nodes', {})
    resource_rows = ''
    for nd in nodes:
        nid = nd['id']
        nd_data = res_nodes.get(nid, {})
        bdg = _badge(nd)
        cpu_a = f'{nd_data.get("cpu_avg",0):.2f}%'
        cpu_p = f'{nd_data.get("cpu_peak",0):.2f}%'
        mem_a = f'{nd_data.get("mem_avg",0):.2f}%'
        mem_p = f'{nd_data.get("mem_peak",0):.2f}%'
        mc = nd_data.get('max_conn', nd['max_conn'])
        conn_a = nd_data.get('conn_avg', 0)
        conn_p = nd_data.get('conn_peak', 0)
        conn_a_pct = round(conn_a / mc * 100, 1) if mc else 0
        conn_p_pct = round(conn_p / mc * 100, 1) if mc else 0
        conn_str = f'{conn_a_pct}% / {conn_p_pct}%'
        active_a = f'{nd_data.get("active_avg",0):.0f}'
        active_p = f'{nd_data.get("active_peak",0):.0f}'
        iops_u_a = nd_data.get('iops_usage_avg', 0)
        iops_u_p = nd_data.get('iops_usage_peak', 0)
        iops_str = f'{iops_u_a:.1f}% / {iops_u_p:.1f}%'
        icons = [status_icon(nd_data.get('cpu_peak', 0)), status_icon(nd_data.get('mem_peak', 0), 'memory'), status_icon(nd_data.get('conn_pct', 0)), status_icon(iops_u_p)]
        worst = '🔴' if '🔴' in icons else ('🟡' if '🟡' in icons else '🟢')
        worst_class = 'danger' if '🔴' in icons else ('warn' if '🟡' in icons else 'ok')
        resource_rows += f'''<tr>
            <td>{nid} {bdg}</td>
            <td>{cpu_a} / {cpu_p}</td>
            <td>{mem_a} / {mem_p}</td>
            <td>{iops_str}</td>
            <td>{conn_str}</td>
            <td>{active_a} / {active_p}</td>
            <td class="{worst_class}" style="text-align:center">{worst}</td>
        </tr>\n'''

    # Chart nodes JS
    chart_nodes_js = 'var chartNodes = [];\n'
    for nd in nodes:
        nid = nd['id']
        rs = _rshort(nd)
        label = f'{nid}({rs})'
        nts = node_ts.get(nid, {})
        cpu_d = json.dumps([[t[0], round(t[1], 2)] for t in nts.get('cpu', [])])
        mem_d = json.dumps([[t[0], round(t[1], 2)] for t in nts.get('memory', [])])
        iops_d = json.dumps([[t[0], round(t[1], 2)] for t in nts.get('iops', [])])
        conn_d = json.dumps([[t[0], round(t[1], 2)] for t in nts.get('conn', [])])
        chart_nodes_js += f"    chartNodes.push({{\n        id:'{nid}', role:'{rs}', label:'{label}',\n        cpu:{cpu_d},\n        memory:{mem_d},\n        iops:{iops_d},\n        connections:{conn_d}\n    }});\n"
    chart_nodes_js += f'\nvar maxConn = {max_conn};\n'

    # Proxy chart data
    proxy_ts = res.get('proxy_ts', {})
    proxy_cpu_js = json.dumps([[t[0], round(t[1], 2)] for t in proxy_ts.get('cpu', [])])
    proxy_lsn_js = json.dumps([[t[0], round(t[1], 2)] for t in proxy_ts.get('lsn_not_match', [])])
    proxy_trx_js = json.dumps([[t[0], round(t[1], 2)] for t in proxy_ts.get('queries_in_trx', [])])
    proxy_conns_parts = []
    for plabel, pts in proxy_ts.get('node_conns', {}).items():
        d = json.dumps([[t[0], round(t[1], 2)] for t in pts])
        proxy_conns_parts.append(f'{{label:"{plabel}",data:{d}}}')
    proxy_conns_js = '[' + ','.join(proxy_conns_parts) + ']'

    # Disk chart data
    disk_ts = cluster_ts.get('disk', [])
    disk_total_js = json.dumps([[t[0], round(t[1], 2)] for t in disk_ts])
    disk_detail = cluster_ts.get('disk_detail', {})
    disk_detail_parts = []
    for label, ts in disk_detail.items():
        d = json.dumps([[t[0], round(t[1], 2)] for t in ts])
        disk_detail_parts.append(f'"{label}":{d}')
    disk_detail_js = '{' + ','.join(disk_detail_parts) + '}'

    # 4.1 Disk trend summary
    disk_trend_html = ''
    if disk_ts and len(disk_ts) >= 2:
        first_mb, last_mb = disk_ts[0][1], disk_ts[-1][1]
        days = (disk_ts[-1][0] - disk_ts[0][0]) / (86400 * 1000) or 1
        change_mb = last_mb - first_mb
        daily = change_mb / days
        sign_c = '+' if change_mb >= 0 else ''
        sign_d = '+' if daily >= 0 else ''
        disk_trend_html = f'<p><strong>{L("lbl_current_usage")}</strong>: {format_mb(last_mb)} &nbsp;|&nbsp; <strong>{L("lbl_7days_ago")}</strong>: {format_mb(first_mb)} &nbsp;|&nbsp; <strong>{L("lbl_7days_change")}</strong>: {sign_c}{format_mb(abs(change_mb))} &nbsp;|&nbsp; <strong>{L("lbl_daily_growth")}</strong>: {sign_d}{format_mb(abs(daily))}</p>'

    # 4.2 Space TOP20 rows (with fragment column)
    space_rows = ''
    for i, t in enumerate(space.get('table_list', []), 1):
        frag_str = format_bytes(t.get('frag', 0))
        space_rows += f'<tr><td>{i}</td><td>{_html_escape(t["db"])}</td><td>{_html_escape(t["table"])}</td><td>{t["total_str"]}</td><td>{t["data_str"]}</td><td>{t["index_str"]}</td><td>{frag_str}</td><td>{t["rows"]:,}</td></tr>\n'

    # 4.3 Anomalies (with # column)
    anom = space.get('anomalies', [])
    if anom:
        anom_rows = ''.join(f'<tr><td>{i}</td><td>{a["type"]}</td><td>{_html_escape(a["db"])}</td><td>{_html_escape(a["table"])}</td><td>{a["detail"]}</td></tr>' for i, a in enumerate(anom, 1))
        anom_html = f'<table><tr><th>{L("th_rank")}</th><th>{L("th_type")}</th><th>{L("th_database")}</th><th>{L("th_table")}</th><th>{L("th_detail")}</th></tr>{anom_rows}</table>'
    else:
        anom_html = f'<p class="ok-msg">{L("msg_no_anomaly")}</p>'

    # Slow logs
    slow_rows = ''
    for i, s in enumerate(data.get('slow_logs', []), 1):
        full_sql = _html_escape(s['sql_text'])
        sql = _html_escape(s['sql_text'][:80])
        if len(s['sql_text']) > 80:
            sql += '...'
        avg_parse = f'{s.get("avg_parse_rows",0):,}'
        avg_return = f'{s.get("avg_return_rows",0):,}'
        hash_val = _html_escape(s.get("sql_hash", ""))
        slow_rows += f'<tr><td>{i}</td><td>{_html_escape(s["db"])}</td><td class="hash-cell"><a href="#sql_{hash_val}" class="hash-link" title="{hash_val}"><code>{hash_val}</code></a></td><td>{s["count"]}</td><td>{s["total_time"]}</td><td>{s["max_time"]}</td><td>{avg_parse}</td><td>{avg_return}</td><td class="sql-cell" title="{full_sql}">{sql}</td></tr>'
    slow_detail = ''
    if data.get('slow_logs'):
        slow_detail = f'<h3 style="margin-top:2rem;">{L("sub_sqlhash_detail")}</h3><table class="sql-detail-table">'
        slow_detail += f'<tr><th>{L("th_sqlhash")}</th><th>{L("th_full_sql")}</th></tr>'
        for s in data['slow_logs']:
            hash_val = _html_escape(s.get("sql_hash", ""))
            full_text = _html_escape(s['sql_text'])
            slow_detail += f'<tr id="sql_{hash_val}"><td><code>{hash_val}</code></td><td class="sql-full">{full_text}</td></tr>'
        slow_detail += '</table>'
    _slow_count_text = _i18n(f'Total {data["slow_total"]} slow query entries', f'共计 {data["slow_total"]} 条慢查询统计')
    slow_html = f'<table><tr><th>{L("th_rank")}</th><th>{L("th_database")}</th><th>{L("th_sqlhash")}</th><th>{L("th_count")}</th><th>{L("th_total_time")}</th><th>{L("th_max_time")}</th><th>{L("th_avg_scan_rows")}</th><th>{L("th_avg_return_rows")}</th><th>{L("th_sql_summary")}</th></tr>{slow_rows}</table><p>{_slow_count_text}</p>{slow_detail}' if slow_rows else f'<p class="ok-msg">{L("msg_no_slowlog")}</p>'

    # Alert history
    alerts = data.get('alert_history', [])
    if alerts:
        alert_rows = ''
        for i, a in enumerate(alerts, 1):
            lvl_cls = 'danger' if a['level'] in ('P1', 'P2') else ('warn' if a['level'] == 'P3' else '')
            alert_rows += f'<tr class="{lvl_cls}"><td>{i}</td><td>{a["time"]}</td><td>{a["level"]}</td><td>{_html_escape(a.get("rule_name",""))}</td><td>{_html_escape(a.get("metric",""))}</td><td>{_html_escape(a.get("node_id",""))}</td><td>{a.get("cur_value","")}</td><td>{a.get("threshold","")}</td><td>{_html_escape(a.get("send_status",""))}</td></tr>'
        alert_html = f'<table><tr><th>{L("th_rank")}</th><th>{L("th_time")}</th><th>{L("th_level")}</th><th>{L("th_rule")}</th><th>{L("th_metric")}</th><th>{L("th_node")}</th><th>{L("th_cur_value")}</th><th>{L("th_threshold")}</th><th>{L("th_notify_status")}</th></tr>{alert_rows}</table><p>{_i18n(f"Total {len(alerts)} alert records", f"共计 {len(alerts)} 条报警记录")}</p>'
    else:
        alert_html = f'<p class="ok-msg">{L("msg_no_alert")}</p>'

    # Suggestions (triplet: level, en_text, zh_text)
    sug_html = ''
    sug = data.get('suggestions', [])
    if not sug:
        sug_html = f'<p class="ok-msg">{L("msg_no_issue")}</p>'
    else:
        danger_items = [_i18n(_html_escape(en), _html_escape(zh)) for level, en, zh in sug if level == 'danger']
        warn_items = [_i18n(_html_escape(en), _html_escape(zh)) for level, en, zh in sug if level == 'warn']
        info_items = [_i18n(_html_escape(en), _html_escape(zh)) for level, en, zh in sug if level == 'info']
        for label, sug_items in [(L('risk_high'), danger_items), (L('risk_medium'), warn_items), (L('risk_low'), info_items)]:
            if not sug_items:
                continue
            sug_html += f'<h3 style="margin:0.8rem 0 0.4rem;">{label}</h3>'
            if len(sug_items) == 1:
                sug_html += f'<p style="margin-left:1.2rem;">{sug_items[0]}</p>'
            else:
                sug_html += '<ol class="sug-list">'
                for t in sug_items:
                    sug_html += f'<li>{t}</li>'
                sug_html += '</ol>'

    # ===== Phase 2: 组装 HTML 页面（章节片段与取舍逻辑见 hi_html_template.py）=====
    from hi_html_template import assemble_page
    return assemble_page({
        'data': data, 'bi': bi, 'nodes': nodes, 'vb': vb, 'node_rows': node_rows,
        'session_html': session_html, 'resource_rows': resource_rows,
        'chart_nodes_js': chart_nodes_js, 'proxy_cpu_js': proxy_cpu_js,
        'proxy_lsn_js': proxy_lsn_js, 'proxy_trx_js': proxy_trx_js,
        'proxy_conns_js': proxy_conns_js, 'disk_total_js': disk_total_js,
        'disk_detail_js': disk_detail_js, 'disk_trend_html': disk_trend_html,
        'space_rows': space_rows, 'anom_html': anom_html, 'slow_html': slow_html,
        'alert_html': alert_html, 'sug_html': sug_html, 'max_conn': max_conn
    }, items=selected_items)
