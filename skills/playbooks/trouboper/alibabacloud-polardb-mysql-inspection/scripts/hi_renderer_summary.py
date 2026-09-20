# -*- coding: utf-8 -*-
"""Batch inspection summary page (index.html) renderer with ECharts visualizations.

Data preparation lives here; the HTML template is in hi_summary_template.py.
Mirrors the 8-section structure of the RDS MySQL inspection summary report.
"""

import json
import os

from hi_utils import _html_escape, format_bytes
from hi_i18n import _i18n, L
from hi_score import score_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_color(score):
    """Return CSS color hex for health score."""
    if score >= 80:
        return '#10b981'
    if score >= 60:
        return '#f59e0b'
    return '#ef4444'


def _score_cls(score):
    """Return CSS class name for health score."""
    if score >= 80:
        return 'ok'
    if score >= 60:
        return 'warn'
    return 'danger'


def _link(cluster_id, report_map):
    """Build an HTML link to a cluster's detail report."""
    cid_esc = _html_escape(cluster_id)
    href = report_map.get(cluster_id, '')
    if href:
        return f'<a href="{href}" target="_blank">{cid_esc}</a>'
    return cid_esc


_LEVEL_PRIORITY = {'P1': 1, 'P2': 2, 'P3': 3, 'P4': 4}


def _level_weight(level):
    """Map alert level to numeric weight (lower = more severe)."""
    return _LEVEL_PRIORITY.get(str(level).upper(), 99)


# ---------------------------------------------------------------------------
# Section 1: Overview
# ---------------------------------------------------------------------------

def _section_overview(agg, report_map):
    """Build Overview section: KPI cards + 4 chart data JSONs."""
    total = agg.get('total_instances', 0)
    scanned = agg.get('scanned_total', 0) or total
    region_count = agg.get('region_count', 0)
    global_score = agg.get('global_score', 0)
    hd = agg.get('health_dist', {})
    inst_w_alerts = agg.get('instances_with_alerts', 0)
    total_alerts = agg.get('total_alerts', 0)
    sc = _score_color(global_score)

    kpis = f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">{_i18n("Instances Inspected","巡检实例总数")}</div>
        <div class="value">{total}</div>
        <div class="sub">{_i18n(f"Scanned {scanned}",f"扫描发现 {scanned} 个")}</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Regions Covered","覆盖 Region")}</div>
        <div class="value">{region_count}</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Global Health","全局健康度")}</div>
        <div class="value" style="color:{sc}">{global_score}</div>
        <div class="sub">/100</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Health Distribution","健康分布")}</div>
        <div class="value" style="font-size:1.1rem">🟢{hd.get('ok',0)} 🟡{hd.get('warn',0)} 🔴{hd.get('danger',0)}</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Instances w/ Alerts","告警实例")}</div>
        <div class="value">{inst_w_alerts}</div>
        <div class="sub">{_i18n(f"{total_alerts} alerts",f"告警 {total_alerts} 条")}</div></div>
    </div>"""

    charts = f"""
    <div class="chart-grid">
      <div class="chart-card"><h4>{_i18n("Health Distribution","健康状态分布")}</h4>
        <div id="chart-health" class="echart" style="height:260px"></div></div>
      <div class="chart-card"><h4>{_i18n("Instances per Region","各 Region 实例数")}</h4>
        <div id="chart-regions" class="echart" style="height:260px"></div></div>
      <div class="chart-card"><h4>{_i18n("Status Distribution","实例状态分布")}</h4>
        <div id="chart-status" class="echart" style="height:260px"></div></div>
      <div class="chart-card"><h4>{_i18n("Category Distribution","实例类别分布")}</h4>
        <div id="chart-category" class="echart" style="height:260px"></div></div>
    </div>"""

    overview_html = kpis + charts

    # Chart JSON data
    health_dist_json = json.dumps([
        {'value': hd.get('ok', 0), 'name': '🟢 Healthy',
         'itemStyle': {'color': '#10b981'}},
        {'value': hd.get('warn', 0), 'name': '🟡 Warning',
         'itemStyle': {'color': '#f59e0b'}},
        {'value': hd.get('danger', 0), 'name': '🔴 Critical',
         'itemStyle': {'color': '#ef4444'}},
    ])
    rd = agg.get('region_dist', {})
    region_dist_json = json.dumps([
        {'value': c, 'name': r}
        for r, c in sorted(rd.items(), key=lambda x: -x[1])
    ])
    sd = agg.get('status_dist', {})
    status_dist_json = json.dumps([
        {'value': c, 'name': s} for s, c in sd.items()
    ])
    cd = agg.get('category_dist', {})
    category_dist_json = json.dumps([
        {'value': c, 'name': s} for s, c in cd.items()
    ])

    return (overview_html, health_dist_json, region_dist_json,
            status_dist_json, category_dist_json)


# ---------------------------------------------------------------------------
# Section 2: Health Ranking
# ---------------------------------------------------------------------------

def _section_health_ranking(agg, rmap):
    """Build Health Score Ranking TOP 20 table."""
    rows = []
    for i, d in enumerate(agg.get('health_ranking', []), 1):
        score = d.get('health_score', 0)
        emoji, cls = score_status(score)
        deds = (d.get('health_deductions') or [])[:3]
        de = '; '.join(_html_escape(x.get('en', ''))
                       for x in deds if isinstance(x, dict))
        dz = '；'.join(_html_escape(x.get('zh', ''))
                       for x in deds if isinstance(x, dict))
        dh = _i18n(de, dz) if de or dz else '-'
        rows.append(
            f'<tr><td>{i}</td>'
            f'<td class="link-cell">{_link(d["cluster_id"], rmap)}</td>'
            f'<td>{_html_escape(d.get("region",""))}</td>'
            f'<td class="{cls}">{emoji} {score}</td>'
            f'<td>{_i18n(_html_escape(d.get("category_en","") or "N/A"), _html_escape(d.get("category_zh","") or "N/A"))}</td>'
            f'<td>{_html_escape(d.get("node_class",""))}</td>'
            f'<td style="font-size:.78rem;color:var(--muted)">{dh}</td></tr>')

    return (
        f'<p>{_i18n("Lower health score = more issues; investigate these first. Click a Cluster ID for the detailed report.","健康分越低代表问题越多，建议优先排查。点击集群 ID 查看详细报告。")}</p>'
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
        f'<th>Region</th><th>{_i18n("Health Score","健康分")}</th>'
        f'<th>{_i18n("Category","类别")}</th>'
        f'<th>{_i18n("Class","规格")}</th>'
        f'<th>{_i18n("Top Deductions","主要扣分项")}</th></tr>'
        + ''.join(rows) + '</table></div>')


# ---------------------------------------------------------------------------
# Section 3: Alert Statistics
# ---------------------------------------------------------------------------

def _section_alerts(agg, rmap):
    """Build Alert Statistics: KPIs + chart data + TOP20 table."""
    iw = agg.get('instances_with_alerts', 0)
    ta = agg.get('total_alerts', 0)

    arows = []
    for i, d in enumerate(agg.get('alerts_ranking', []), 1):
        arows.append(
            f'<tr><td>{i}</td>'
            f'<td class="link-cell">{_link(d["cluster_id"], rmap)}</td>'
            f'<td>{_html_escape(d.get("region",""))}</td>'
            f'<td>{d["alert_count"]}</td>'
            f'<td>{_html_escape(d.get("max_level","-"))}</td>'
            f'<td>{d.get("high_severity",0)}</td></tr>')

    if arows:
        tbl = (
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
            f'<th>Region</th><th>{_i18n("Alert Count","告警条数")}</th>'
            f'<th>{_i18n("Max Level","最高级别")}</th>'
            f'<th>{_i18n("P1/P2 High Severity","P1/P2 高严重")}</th></tr>'
            + ''.join(arows) + '</table></div>')
    else:
        tbl = f'<p class="ok-msg">{_i18n("✅ No recent alerts on any instance","✅ 所有实例近期均无告警")}</p>'

    html = f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">{_i18n("Instances w/ Alerts","告警实例数")}</div>
        <div class="value">{iw}</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Total Alerts","告警总条数")}</div>
        <div class="value">{ta}</div></div>
    </div>
    <div class="chart-card" style="margin-bottom:1rem">
      <h4>{_i18n("Alert Level Distribution","告警级别分布")}</h4>
      <div id="chart-alert-levels" class="echart" style="height:220px"></div></div>
    <h3>{_i18n("Top 20 Instances by Alert Count","告警最多 TOP 20 实例")}</h3>
    {tbl}"""

    ald = agg.get('alert_level_dist', {})
    alert_json = json.dumps(sorted(
        [{'name': k, 'value': v} for k, v in ald.items()],
        key=lambda x: _level_weight(x['name'])))

    return html, alert_json


# ---------------------------------------------------------------------------
# Section 4: Resource Utilization (tab-switchable)
# ---------------------------------------------------------------------------

_RES_DIMS = [
    ('cpu',        'CPU Peak TOP 20',        'CPU 峰值 TOP 20'),
    ('memory',     'Memory Peak TOP 20',     '内存峰值 TOP 20'),
    ('iops',       'IOPS Peak TOP 20',       'IOPS 峰值 TOP 20'),
    ('connection', 'Connection Usage TOP 20', '连接使用率 TOP 20'),
    ('disk',       'Disk Usage TOP 20',       '磁盘使用率 TOP 20'),
]


def _section_resource(agg, rmap):
    """Build 5 tab-switchable resource TOP 20 tables."""
    btns = ''
    panels = ''
    for idx, (key, en, zh) in enumerate(_RES_DIMS):
        act = ' active' if idx == 0 else ''
        btns += (f'<button class="tab-btn{act}" '
                 f'data-tab="res-{key}">{_i18n(en, zh)}</button>\n')
        items = agg.get('resource_tops', {}).get(key, [])
        if not items:
            body = (f'<p class="ok-msg">'
                    f'{_i18n(f"No {en} data", f"无{zh}数据")}</p>')
        else:
            rs = []
            for i, it in enumerate(items, 1):
                rs.append(
                    f'<tr><td>{i}</td>'
                    f'<td class="link-cell">{_link(it["cluster_id"], rmap)}</td>'
                    f'<td>{_html_escape(it.get("region",""))}</td>'
                    f'<td>{it["avg"]:.2f}%</td>'
                    f'<td>{it["peak"]:.2f}%</td></tr>')
            body = (
                '<div class="table-scroll"><table>'
                f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
                f'<th>Region</th><th>{_i18n("Average","平均")}</th>'
                f'<th>{_i18n("Peak","峰值")}</th></tr>'
                + ''.join(rs) + '</table></div>')
        panels += f'<div class="tab-panel{act}" id="panel-res-{key}">{body}</div>\n'

    return f'<div class="tab-bar">\n{btns}</div>\n{panels}'


# ---------------------------------------------------------------------------
# Section 5: Slow Logs
# ---------------------------------------------------------------------------

def _section_slow_logs(agg, rmap):
    """Build 3 slow-log sub-tables."""
    nm = (f'<p class="ok-msg">'
          f'{_i18n("✅ No slow queries on any instance","✅ 所有实例无慢日志")}</p>')

    # 5-1: Count TOP 20
    ci = [x for x in agg.get('slow_count_ranking', [])
          if x.get('total_count', 0) > 0]
    if ci:
        rs = []
        for i, it in enumerate(ci, 1):
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(it["cluster_id"], rmap)}</td>'
                f'<td>{_html_escape(it.get("region",""))}</td>'
                f'<td>{it["total_count"]:,}</td>'
                f'<td>{it.get("unique_sqls",0)}</td></tr>')
        ct = ('<div class="table-scroll"><table>'
              f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
              f'<th>Region</th><th>{_i18n("Slow Count","慢日志条数")}</th>'
              f'<th>{_i18n("SQL Templates","SQL 模板数")}</th></tr>'
              + ''.join(rs) + '</table></div>')
    else:
        ct = nm

    # 5-2: Total time TOP 20
    ti = [x for x in agg.get('slow_time_ranking', [])
          if x.get('total_time', 0) > 0]
    if ti:
        rs = []
        for i, it in enumerate(ti, 1):
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(it["cluster_id"], rmap)}</td>'
                f'<td>{_html_escape(it.get("region",""))}</td>'
                f'<td>{it["total_time"]:.2f}</td>'
                f'<td>{it.get("unique_sqls",0)}</td></tr>')
        tt = ('<div class="table-scroll"><table>'
              f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
              f'<th>Region</th><th>{_i18n("Total Time (s)","总耗时(s)")}</th>'
              f'<th>{_i18n("SQL Templates","SQL 模板数")}</th></tr>'
              + ''.join(rs) + '</table></div>')
    else:
        tt = nm

    # 5-3: Single SQL max time TOP 20
    si = [x for x in agg.get('sql_max_time_top20', [])
          if x.get('max_time', 0) > 0]
    if si:
        rs = []
        for i, it in enumerate(si, 1):
            sql_txt = _html_escape(it.get('sql', ''))
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(it["cluster_id"], rmap)}</td>'
                f'<td>{_html_escape(it.get("db_name",""))}</td>'
                f'<td>{it["max_time"]:.2f}</td>'
                f'<td class="sql-cell">{sql_txt}</td></tr>')
        st = ('<div class="table-scroll"><table>'
              f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
              f'<th>{_i18n("Database","数据库")}</th>'
              f'<th>{_i18n("Max Exec Time (s)","最大执行时间(s)")}</th>'
              f'<th>SQL</th></tr>'
              + ''.join(rs) + '</table></div>')
    else:
        st = f'<p class="ok-msg">{_i18n("No data","无数据")}</p>'

    return f"""
    <h3>{_i18n("TOP 20 Instances by Slow Log Count","慢日志条数 TOP 20 实例")}</h3>{ct}
    <h3>{_i18n("TOP 20 Instances by Slow Log Total Time","慢日志总耗时 TOP 20 实例")}</h3>{tt}
    <h3>{_i18n("TOP 20 Single Slow SQL by Max Exec Time","单条慢 SQL 最大执行时间 TOP 20")}</h3>{st}"""


# ---------------------------------------------------------------------------
# Section 6: Space Analysis
# ---------------------------------------------------------------------------

def _section_space(agg, rmap):
    """Build 3 space sub-tables."""
    # 6-1: Instance space TOP 20
    sp = agg.get('instance_space_ranking', [])
    if sp:
        rs = []
        for i, it in enumerate(sp, 1):
            ed = it.get('estimate_days')
            ds = (_i18n(f'{ed} days', f'{ed} 天')
                  if ed not in (None, '', '-') else '-')
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(it["cluster_id"], rmap)}</td>'
                f'<td>{_html_escape(it.get("region",""))}</td>'
                f'<td>{format_bytes(it.get("total_used",0))}</td>'
                f'<td>{format_bytes(it.get("storage_total",0))}</td>'
                f'<td>{format_bytes(it.get("daily_inc",0))}</td>'
                f'<td>{ds}</td>'
                f'<td>{it.get("tables_count",0):,}</td></tr>')
        s1 = ('<div class="table-scroll"><table>'
              f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
              f'<th>Region</th><th>{_i18n("Used Space","已用空间")}</th>'
              f'<th>{_i18n("Total Storage","总存储")}</th>'
              f'<th>{_i18n("Daily Growth","日增量")}</th>'
              f'<th>{_i18n("Days Left","预计可用天数")}</th>'
              f'<th>{_i18n("Tables","表数量")}</th></tr>'
              + ''.join(rs) + '</table></div>')
    else:
        s1 = f'<p class="ok-msg">{_i18n("No space data","无空间数据")}</p>'

    # 6-2: Table size TOP 20
    tb = agg.get('tables_top20', [])
    if tb:
        rs = []
        for i, t in enumerate(tb, 1):
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(t.get("cluster_id",""), rmap)}</td>'
                f'<td>{_html_escape(t.get("db",""))}</td>'
                f'<td>{_html_escape(t.get("table",""))}</td>'
                f'<td>{format_bytes(t.get("total",0))}</td>'
                f'<td>{format_bytes(t.get("data",0))}</td>'
                f'<td>{format_bytes(t.get("index",0))}</td>'
                f'<td>{t.get("rows",0):,}</td></tr>')
        s2 = ('<div class="table-scroll"><table>'
              f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
              f'<th>{_i18n("Database","数据库")}</th>'
              f'<th>{_i18n("Table","表")}</th>'
              f'<th>{_i18n("Total Size","总空间")}</th>'
              f'<th>{_i18n("Data","数据")}</th>'
              f'<th>{_i18n("Index","索引")}</th>'
              f'<th>{_i18n("Rows","行数")}</th></tr>'
              + ''.join(rs) + '</table></div>')
    else:
        s2 = f'<p class="ok-msg">{_i18n("No data","无数据")}</p>'

    # 6-3: Fragmentation TOP 20
    fg = agg.get('fragmentation_ranking', [])
    if fg:
        rs = []
        for i, t in enumerate(fg, 1):
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(t.get("cluster_id",""), rmap)}</td>'
                f'<td>{_html_escape(t.get("db_name",""))}</td>'
                f'<td>{_html_escape(t.get("table_name",""))}</td>'
                f'<td>{format_bytes(t.get("total_size",0))}</td>'
                f'<td>{format_bytes(t.get("frag_size",0))}</td>'
                f'<td class="warn">{t.get("frag_pct",0):.1f}%</td></tr>')
        s3 = ('<div class="table-scroll"><table>'
              f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
              f'<th>{_i18n("Database","数据库")}</th>'
              f'<th>{_i18n("Table","表")}</th>'
              f'<th>{_i18n("Total Size","总空间")}</th>'
              f'<th>{_i18n("Fragmented","碎片")}</th>'
              f'<th>{_i18n("Fragmentation Rate","碎片率")}</th></tr>'
              + ''.join(rs) + '</table></div>')
    else:
        s3 = (f'<p class="ok-msg">'
              f'{_i18n("✅ No significant fragmentation","✅ 未发现明显碎片")}</p>')

    return f"""
    <h3>{_i18n("TOP 20 Instances by Used Space","实例已用空间 TOP 20")}</h3>{s1}
    <h3>{_i18n("TOP 20 Tables (cross-instance)","单表 TOP 20（跨实例聚合）")}</h3>{s2}
    <h3>{_i18n("TOP 20 Most-Fragmented Tables","碎片率最高的表 TOP 20")}</h3>{s3}"""


# ---------------------------------------------------------------------------
# Section 7: Version & Expiration
# ---------------------------------------------------------------------------

def _section_version(agg, rmap):
    """Build Version & Expiration section: upgradable + expiring tables."""
    upg = agg.get('upgradable', [])
    if upg:
        rs = []
        for i, it in enumerate(upg, 1):
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(it["cluster_id"], rmap)}</td>'
                f'<td>{_html_escape(it.get("region",""))}</td>'
                f'<td>{_html_escape(it.get("current",""))}</td>'
                f'<td>{_html_escape(it.get("latest",""))}</td></tr>')
        uh = ('<div class="table-scroll"><table>'
              f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
              f'<th>Region</th>'
              f'<th>{_i18n("Current Kernel","当前内核")}</th>'
              f'<th>{_i18n("Latest Kernel","最新内核")}</th></tr>'
              + ''.join(rs) + '</table></div>')
    else:
        uh = (f'<p class="ok-msg">'
              f'{_i18n("✅ All instances are on the latest kernel","✅ 所有实例内核均为最新版本")}</p>')

    def _exp_tbl(records, ten, tzh):
        if not records:
            return (f'<p class="ok-msg">'
                    f'{_i18n(f"✅ No instances {ten}", f"✅ 无{tzh}的实例")}</p>')
        rs = []
        for i, it in enumerate(records, 1):
            c = 'danger' if it['days_left'] <= 30 else 'warn'
            dl = it['days_left']
            rs.append(
                f'<tr><td>{i}</td>'
                f'<td class="link-cell">{_link(it["cluster_id"], rmap)}</td>'
                f'<td>{_html_escape(it.get("region",""))}</td>'
                f'<td>{_html_escape(it.get("expire_date",""))}</td>'
                f'<td class="{c}">{_i18n(f"{dl} days", f"{dl} 天")}</td></tr>')
        return ('<div class="table-scroll"><table>'
                f'<tr><th>#</th><th>{_i18n("Cluster ID","集群 ID")}</th>'
                f'<th>Region</th>'
                f'<th>{_i18n("Expire Date","到期日期")}</th>'
                f'<th>{_i18n("Days Left","剩余天数")}</th></tr>'
                + ''.join(rs) + '</table></div>')

    e30 = agg.get('expiring_30d', [])
    e90 = agg.get('expiring_90d', [])

    html = f"""
    <h3>{_i18n(f"Upgradable Kernel Instances ({len(upg)} total)",f"内核版本可升级实例（共 {len(upg)} 个）")}</h3>
    {uh}
    <h3>{_i18n(f"Instances Expiring in 30 Days ({len(e30)} total)",f"30 天内到期实例（共 {len(e30)} 个）")}</h3>
    {_exp_tbl(e30, 'expiring in 30 days', '30 天内到期')}
    <h3>{_i18n(f"Instances Expiring in 90 Days ({len(e90)} total)",f"90 天内到期实例（共 {len(e90)} 个）")}</h3>
    {_exp_tbl(e90, 'expiring in 90 days', '90 天内到期')}"""

    if not e30 and not e90:
        html += (f'\n    <p class="ok-msg" style="margin-top:.5rem">'
                 f'{_i18n("No expiring instances (PolarDB pay-as-you-go)","无到期实例（PolarDB 按量付费）")}</p>')
    return html


# ---------------------------------------------------------------------------
# Section 8: Conclusion
# ---------------------------------------------------------------------------

def _section_conclusion(agg, rmap):
    """Build Conclusion: KPI summary + problem list."""
    hd = agg.get('health_dist', {})
    gs = agg.get('global_score', 0)

    kpi = f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">{_i18n("Global Health","全局健康度")}</div>
        <div class="value">{gs}</div><div class="sub">/100</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Healthy","健康实例")}</div>
        <div class="value ok">{hd.get('ok',0)}</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Needs Attention","需关注实例")}</div>
        <div class="value warn">{hd.get('warn',0)}</div></div>
      <div class="kpi-card"><div class="label">{_i18n("Urgent","紧急处理实例")}</div>
        <div class="value danger">{hd.get('danger',0)}</div></div>
    </div>"""

    sug = agg.get('suggestions', {})
    if sug:
        ss = sorted(sug.items(),
                     key=lambda x: -len(x[1].get('cluster_ids', [])))
        rows = []
        for idx, (_k, info) in enumerate(ss, 1):
            lab = info.get('label', {})
            ids = info.get('cluster_ids', [])
            aff = ', '.join(_link(c, rmap) for c in ids[:10])
            more = _i18n(
                f'... {len(ids)} total' if len(ids) > 10 else f'{len(ids)} total',
                f'... 共 {len(ids)} 个' if len(ids) > 10 else f'共 {len(ids)} 个')
            desc = _i18n(
                _html_escape(lab.get('en', '') if isinstance(lab, dict) else str(lab)),
                _html_escape(lab.get('zh', '') if isinstance(lab, dict) else str(lab)))
            rows.append(
                f'<tr><td>{idx}</td><td>{desc}</td><td>{len(ids)}</td>'
                f'<td>{aff}<br/>'
                f'<span style="color:var(--muted);font-size:.78rem">{more}</span></td></tr>')
        ptbl = (
            f'<h3>{_i18n("Problem List (sorted by impacted instance count)","问题清单（按受影响实例数排序）")}</h3>'
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Problem","问题描述")}</th>'
            f'<th>{_i18n("Count","数量")}</th>'
            f'<th>{_i18n("Impacted Instances","受影响实例")}</th></tr>'
            + ''.join(rows) + '</table></div>')
    else:
        ptbl = (f'<p class="ok-msg">'
                f'{_i18n("No problems detected.","✅ 巡检未发现明显问题")}</p>')

    return kpi + ptbl


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_summary_html(summaries, agg_data, output_dir, inspect_time):
    """Generate the batch-inspection summary HTML page (index.html).

    Args:
        summaries:    list of summary dicts from inspect_single_cluster()
        agg_data:     output of aggregate_summaries(), or None
        output_dir:   directory to write index.html into
        inspect_time: human-readable timestamp string

    Returns:
        Absolute path of the written index.html file.
    """
    if not agg_data:
        agg_data = {
            'total_instances': 0, 'scanned_total': 0, 'region_count': 0,
            'status_dist': {}, 'category_dist': {},
            'health_dist': {'ok': 0, 'warn': 0, 'danger': 0},
            'region_dist': {}, 'global_score': 0,
            'health_ranking': [],
            'total_alerts': 0, 'instances_with_alerts': 0,
            'alert_level_dist': {}, 'alerts_ranking': [],
            'resource_tops': {k: [] for k in
                             ('cpu', 'memory', 'iops', 'connection', 'disk')},
            'slow_count_ranking': [], 'slow_time_ranking': [],
            'sql_max_time_top20': [],
            'instance_space_ranking': [], 'tables_top20': [],
            'fragmentation_ranking': [],
            'upgradable': [], 'expiring_30d': [], 'expiring_90d': [],
            'suggestions': {}, 'time_range': '',
        }

    rmap = {s.get('cluster_id', ''): s.get('report_file', '')
            for s in summaries}

    # Build each section
    (overview_html, health_dist_json, region_dist_json,
     status_dist_json, category_dist_json) = _section_overview(agg_data, rmap)
    health_html = _section_health_ranking(agg_data, rmap)
    alerts_html, alert_levels_json = _section_alerts(agg_data, rmap)
    resource_html = _section_resource(agg_data, rmap)
    slow_html = _section_slow_logs(agg_data, rmap)
    space_html = _section_space(agg_data, rmap)
    version_html = _section_version(agg_data, rmap)
    conclusion_html = _section_conclusion(agg_data, rmap)

    gs = agg_data.get('global_score', 0)

    ctx = {
        'title': _i18n('PolarDB MySQL Inspection Summary Report',
                       'PolarDB MySQL 巡检汇总报告'),
        'inspect_time': inspect_time,
        'time_range': agg_data.get('time_range', ''),
        'total_instances': agg_data.get('total_instances', 0),
        'global_score': gs,
        'score_color': _score_color(gs),
        # Section HTML
        'section_overview': overview_html,
        'section_health': health_html,
        'section_alerts': alerts_html,
        'section_resource': resource_html,
        'section_slow': slow_html,
        'section_space': space_html,
        'section_version': version_html,
        'section_conclusion': conclusion_html,
        # Chart data JSON strings
        'health_dist_json': health_dist_json,
        'region_dist_json': region_dist_json,
        'status_dist_json': status_dist_json,
        'category_dist_json': category_dist_json,
        'alert_levels_json': alert_levels_json,
    }

    from hi_summary_template import assemble_summary_page
    html = assemble_summary_page(ctx)

    index_path = os.path.join(output_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return index_path
