# -*- coding: utf-8 -*-
"""巡检报告 HTML 页面模板（拆分自 health-inspect.py render_html 中的 f-string 模板）

⚠️ 本文件主体是若干巨大的 f-string，其中 {{ }} 为 CSS/JS 花括号的转义。
   修改时务必保持转义原样，且不要使用任何代码格式化工具处理本文件。

章节按「巡检项(item)」归属拆分为独立片段：每个 <div class="section"> 由一个
_section_xxx() 生成，assemble_page() 依据选中的巡检项集合决定拼接哪些片段，
并在拼接**之前**完成章节重编号（I/II/III… 与 一/二/三…）。因此不需要、也不
应该再对已生成的 HTML 字符串做正则删除（那会误删相邻的保留章节）。
"""

import re

import hi_config as config
from hi_i18n import I18N_CSS, LABELS, LANG_TOGGLE_HTML, LANG_TOGGLE_JS, L, _i18n


# 章节渲染顺序及其巡检项归属；item 为 None 表示「始终保留」的基础章节
SECTION_ITEMS = [
    (None,       'section_basic_info'),
    ('session',  'section_session'),
    ('resource', 'section_resource'),
    ('space',    'section_space'),
    ('slowlog',  'section_slowlog'),
    ('alert',    'section_alert'),
    (None,       'section_suggestion'),
]

_EN_NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
_ZH_NUMERALS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

# 仅用于剥离 i18n 词条中内嵌的章节序号前缀（词条是本仓库常量，不是运行时 HTML）
_RE_EN_NUMERAL = re.compile(r'^[IVXL]+\.\s*')
_RE_ZH_NUMERAL = re.compile(r'^[一二三四五六七八九十]+、\s*')


def _numerals(ordinal):
    """返回第 ordinal（0 起）个保留章节的中英序号。"""
    if ordinal < len(_EN_NUMERALS):
        return _EN_NUMERALS[ordinal], _ZH_NUMERALS[ordinal]
    return str(ordinal + 1), str(ordinal + 1)


def _section_title(label_key, ordinal):
    """按保留章节的实际顺序生成双语标题，保证编号连续、无跳号、无重复。"""
    entry = LABELS[label_key]
    en_num, zh_num = _numerals(ordinal)
    en_text = _RE_EN_NUMERAL.sub('', entry['en'])
    zh_text = _RE_ZH_NUMERAL.sub('', entry['zh'])
    return _i18n(f'{en_num}. {en_text}', f'{zh_num}、{zh_text}')


# ─── 页头（始终输出）──────────────────────────────────────────────────────────

def _render_prefix(ctx):
    """<!DOCTYPE html> … <head> … 页头 header，与巡检项无关，始终输出。"""
    data = ctx['data']
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_i18n("PolarDB MySQL Inspection Report", "PolarDB MySQL 巡检报告")} - {data["cluster_id"]}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root {{ --ok: #10b981; --warn: #f59e0b; --danger: #ef4444; --info: #3b82f6; --bg: #f8fafc; --card: #ffffff; --border: #e2e8f0; --text: #1e293b; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }}
.header h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
.header .meta {{ opacity: 0.9; font-size: 0.9rem; }}
.section {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }}
.section h2 {{ font-size: 1.2rem; color: #1e40af; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
th, td {{ padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ background: #f1f5f9; font-weight: 600; }}
tr:hover {{ background: #f8fafc; }}
.badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }}
.badge-rw {{ background: #fef3c7; color: #92400e; }}
.badge-ro {{ background: #dbeafe; color: #1e40af; }}
.ok {{ color: var(--ok); }} .warn {{ color: var(--warn); }} .danger {{ color: var(--danger); }}
.suggestion {{ padding: 0.5rem 0; }} .suggestion.danger {{ color: var(--danger); }} .suggestion.warn {{ color: var(--warn); }}
.sug-list {{ margin: 0.3rem 0 0.8rem 1.2rem; line-height: 1.8; }} .sug-list li {{ margin-bottom: 0.2rem; }}
.ok-msg {{ color: var(--ok); font-weight: 500; }}
.sql-cell {{ font-family: monospace; font-size: 0.8rem; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }}
.hash-cell {{ max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.hash-link {{ color: #1976d2; text-decoration: none; }}
.hash-link:hover {{ text-decoration: underline; }}
.sql-detail-table {{ margin-top: 1rem; }}
.sql-detail-table td.sql-full {{ font-family: monospace; font-size: 0.8rem; word-break: break-all; white-space: pre-wrap; max-width: 800px; user-select: all; }}
.sql-detail-table tr:target {{ background: #fff3cd; }}
.footer {{ text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 2rem; }}
.info-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0; }}
.info-item {{ padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border); display: flex; gap: 0.5rem; }}
.info-item .label {{ color: #64748b; min-width: 120px; font-size: 0.83rem; }}
.info-item .value {{ font-weight: 500; font-size: 0.83rem; }}
.table-scroll {{ overflow-x: auto; }}
.chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 1rem; }}
.chart-card {{ background: #f8fafc; border: 1px solid var(--border); border-radius: 6px; padding: 12px; }}
.chart-card h4 {{ margin: 0 0 4px 0; font-size: 0.9rem; color: #334155; }}
.echart {{ width: 100%; height: 280px; }}
@media (max-width: 768px) {{ body {{ padding: 1rem; }} table {{ font-size: 0.75rem; }} th, td {{ padding: 0.3rem 0.5rem; }} .chart-grid {{ grid-template-columns: 1fr; }} .info-grid {{ grid-template-columns: 1fr; }} }}
{I18N_CSS}</style>
</head>
<body>
<div class="container">
    <div class="header" style="position:relative;">
        {LANG_TOGGLE_HTML}
        <h1>{L('title_report')}</h1>
        <div class="meta">
            <span>{L('meta_time')}: {data["inspect_time"]}</span> &nbsp;|&nbsp;
            <span>{L('meta_instance')}: {data["cluster_id"]}</span> &nbsp;|&nbsp;
            <span>Region: {data["region"]}</span>
        </div>
    </div>'''


# ─── 章节片段（每个片段自成一个 <div class="section">）─────────────────────────

def _section_basic_info(ctx, title):
    """基础章节：始终保留。"""
    bi = ctx['bi']
    nodes = ctx['nodes']
    vb = ctx['vb']
    node_rows = ctx['node_rows']
    return f'''    <div class="section">
        <h2>{title}</h2>
        <div class="info-grid">
            <div class="info-item"><span class="label">{L('lbl_db_type')}</span><span class="value">{bi["db_type"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_major_version')}</span><span class="value">{bi["db_type"]} {bi["db_version"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_cluster_status')}</span><span class="value">{bi["status"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_minor_version')}</span><span class="value">{bi["revision_version"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_latest_version')}</span><span class="value">{bi["latest_version"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_version_status')}</span><span class="value">{vb}</span></div>
            <div class="info-item"><span class="label">{L('lbl_proxy_version')}</span><span class="value">{bi["proxy_version"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_storage_type')}</span><span class="value">{bi["storage_type"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_cluster_category')}</span><span class="value">{_i18n(bi.get('category_en', bi['category']), bi.get('category_zh', bi['category']))}</span></div>
            <div class="info-item"><span class="label">{L('lbl_storage_used')}</span><span class="value">{bi["storage_used_str"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_storage_capacity')}</span><span class="value">{bi["storage_space_str"] or bi["storage_max_str"]}</span></div>
            <div class="info-item"><span class="label">{L('lbl_auto_scaling')}</span><span class="value">{
    _i18n('Auto-expand (PSL Storage)', '自动扩展（PSL 存储）') if bi.get('is_psl') else
    (_i18n('Enabled (Max ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + ')', '已开启（上限 ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + '）') if bi.get('storage_auto_scale') else _i18n('Disabled', '未开启')) if bi.get('is_essd') else
    'N/A'
}</span></div>
            <div class="info-item"></div>
        </div>
        <h3 style="margin-top:1rem;font-size:1rem;">{_i18n(f"Node Details ({len(nodes)} nodes)", f"节点详情（{len(nodes)} 个节点）")}</h3>
        <table>
            <tr><th>{L('th_node_id')}</th><th>{L('th_role')}</th><th>{L('th_status')}</th><th>{L('th_spec')}</th><th>{L('th_cpu')}</th><th>{L('th_memory')}</th><th>{L('th_max_conn')}</th><th>{L('th_max_iops')}</th></tr>
            {node_rows}
        </table>
    </div>'''


def _section_session(ctx, title):
    """巡检项 session。"""
    session_html = ctx['session_html']
    return f'''    <div class="section">
        <h2>{title}</h2>
        {session_html}
    </div>'''


def _section_resource(ctx, title):
    """巡检项 resource（含 Proxy / DB 节点趋势图容器）。"""
    resource_rows = ctx['resource_rows']
    return f'''    <div class="section">
        <h2>{title}</h2>
        <div class="table-scroll"><table>
        <tr><th>{L('th_node')}</th><th>{L('th_cpu_avg_peak')}</th><th>{L('th_mem_avg_peak')}</th><th>{L('th_iops_avg_peak')}</th><th>{L('th_conn_avg_peak')}</th><th>{L('th_active_avg_peak')}</th><th>{L('th_res_status')}</th></tr>
        {resource_rows}
    </table></div>

        <h3 style="margin-top:1.5rem;font-size:1rem;">{L('chart_proxy_trend')}</h3>
        <div class="chart-grid">
            <div class="chart-card"><h4>{L('chart_proxy_cpu')}</h4><div id="chart-proxy-cpu" class="echart"></div></div>
            <div class="chart-card"><h4>{L('chart_proxy_route')}</h4><div id="chart-proxy-route" class="echart"></div></div>
        </div>

        <h3 style="margin-top:1.5rem;font-size:1rem;">{L('chart_db_trend')}</h3>
        <div class="chart-grid">
            <div class="chart-card"><h4>{L('chart_cpu')}</h4><div id="chart-cpu" class="echart"></div></div>
            <div class="chart-card"><h4>{L('chart_mem')}</h4><div id="chart-mem" class="echart"></div></div>
            <div class="chart-card"><h4>{L('chart_iops')}</h4><div id="chart-iops" class="echart"></div></div>
            <div class="chart-card"><h4>{L('chart_conn')}</h4><div id="chart-conn" class="echart"></div></div>
        </div>
    </div>'''


def _section_space(ctx, title):
    """巡检项 space（磁盘趋势图 + 库表空间 TOP20 + 异常列表）。"""
    disk_trend_html = ctx['disk_trend_html']
    space_rows = ctx['space_rows']
    anom_html = ctx['anom_html']
    return f'''    <div class="section">
        <h2>{title}</h2>
        <h3>{L('sub_disk_trend')}</h3>
        {disk_trend_html}
        <div class="chart-card"><div id="chart-disk" class="echart"></div></div>

        <h3>{L('sub_space_top20')}</h3>
        <table><tr><th>{L('th_rank')}</th><th>{L('th_database')}</th><th>{L('th_table')}</th><th>{L('th_total_space')}</th><th>{L('th_data')}</th><th>{L('th_index')}</th><th>{L('th_fragment')}</th><th>{L('th_rows')}</th></tr>{space_rows}</table>

        <h3>{L('sub_anomaly_list')}</h3>
        {anom_html}
    </div>'''


def _section_slowlog(ctx, title):
    """巡检项 slowlog。"""
    slow_html = ctx['slow_html']
    return f'''    <div class="section">
        <h2>{title}</h2>
        {slow_html}
    </div>'''


def _section_alert(ctx, title):
    """巡检项 alert。"""
    alert_html = ctx['alert_html']
    return f'''    <div class="section">
        <h2>{title}</h2>
        {alert_html}
    </div>'''


def _section_suggestion(ctx, title):
    """基础章节：巡检结论与建议，始终保留。"""
    sug_html = ctx['sug_html']
    return f'''    <div class="section">
        <h2>{title}</h2>
        {sug_html}
    </div>'''


_SECTION_BUILDERS = {
    'section_basic_info': _section_basic_info,
    'section_session':    _section_session,
    'section_resource':   _section_resource,
    'section_space':      _section_space,
    'section_slowlog':    _section_slowlog,
    'section_alert':      _section_alert,
    'section_suggestion': _section_suggestion,
}


# ─── 图表脚本片段（随所属章节一起取舍，避免引用不存在的 DOM）────────────────────

def _script_resource_data(ctx):
    """resource 章节所需的数据变量与公共图表选项构造函数。"""
    chart_nodes_js = ctx['chart_nodes_js']
    proxy_cpu_js = ctx['proxy_cpu_js']
    proxy_lsn_js = ctx['proxy_lsn_js']
    proxy_trx_js = ctx['proxy_trx_js']
    proxy_conns_js = ctx['proxy_conns_js']
    return f'''{chart_nodes_js}
var proxyCpu = {proxy_cpu_js};
var proxyLsn = {proxy_lsn_js};
var proxyTrx = {proxy_trx_js};
var proxyNodeConns = {proxy_conns_js};
var colors = ['#5470c6','#91cc75','#ee6666','#fac858','#73c0de','#3ba272','#fc8452','#9a60b4'];

var resCharts = [];
function _chartOpts(tooltip, legend, series, yMax) {{
    return {{
        tooltip: tooltip,
        legend: legend,
        grid: {{ left:45, right:15, top:30, bottom:55 }},
        xAxis: {{ type:'time', axisLabel:{{fontSize:10, formatter:'{{MM}}-{{dd}} {{HH}}:{{mm}}'}} }},
        yAxis: {{ type:'value', min:0, max:yMax, axisLabel:{{fontSize:10}} }},
        dataZoom: [
            {{type:'inside'}},
            {{type:'slider', height:20, bottom:5, borderColor:'#ddd', fillerColor:'rgba(84,112,198,0.15)', handleStyle:{{color:'#5470c6'}}, textStyle:{{fontSize:10}}, labelFormatter:function(v){{ var d=new Date(v); return (d.getMonth()+1).toString().padStart(2,'0')+'-'+d.getDate().toString().padStart(2,'0')+' '+d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0'); }}}}
        ],
        series: series
    }};
}}'''


def _script_proxy_charts(ctx):
    """resource 章节：Proxy CPU / LsnNotMatch / QueriesInTrx 图表。"""
    return f'''// Proxy charts
(function() {{
    var fmt = function(params) {{
        if(!params.length) return '';
        var t=new Date(params[0].value[0]);
        var s=t.getFullYear()+'-'+(t.getMonth()+1).toString().padStart(2,'0')+'-'+t.getDate().toString().padStart(2,'0')+' '+t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
        var r='<b>'+s+'</b><br/>';
        params.forEach(function(p){{ r+=p.marker+p.seriesName+': '+p.value[1].toFixed(2)+'<br/>'; }});
        return r;
    }};

    // Proxy CPU
    var cpuChart = echarts.init(document.getElementById('chart-proxy-cpu'));
    cpuChart.setOption(_chartOpts(
        {{ trigger:'axis', formatter:function(params){{
            if(!params.length) return '';
            var t=new Date(params[0].value[0]);
            var s=t.getFullYear()+'-'+(t.getMonth()+1).toString().padStart(2,'0')+'-'+t.getDate().toString().padStart(2,'0')+' '+t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
            return '<b>'+s+'</b><br/>'+params[0].marker+'Proxy CPU: '+params[0].value[1].toFixed(2)+'%';
        }} }},
        {{ show:false }},
        [{{ name:'Proxy CPU', type:'line', symbol:'none', smooth:true, lineStyle:{{width:1.5}}, itemStyle:{{color:'#5470c6'}}, areaStyle:{{opacity:0.1}}, data:proxyCpu }}],
        100
    ));
    resCharts.push(cpuChart);
    window.addEventListener('resize', function(){{ cpuChart.resize(); }});

    // Proxy LsnNotMatch + QueriesInTrx
    var routeChart = echarts.init(document.getElementById('chart-proxy-route'));
    routeChart.setOption(_chartOpts(
        {{ trigger:'axis', formatter:function(params){{
            if(!params.length) return '';
            var t=new Date(params[0].value[0]);
            var s=t.getFullYear()+'-'+(t.getMonth()+1).toString().padStart(2,'0')+'-'+t.getDate().toString().padStart(2,'0')+' '+t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
            var r='<b>'+s+'</b><br/>';
            params.forEach(function(p){{ r+=p.marker+p.seriesName+': '+p.value[1].toFixed(2)+' {_i18n("times/sec", "次/秒")}<br/>'; }});
            return r;
        }} }},
        {{ data:['LsnNotMatch','QueriesInTrx'], top:0, type:'scroll', textStyle:{{fontSize:10}} }},
        [
            {{ name:'LsnNotMatch', type:'line', symbol:'none', smooth:true, lineStyle:{{width:1.5}}, itemStyle:{{color:'#5470c6'}}, areaStyle:{{opacity:0.05}}, data:proxyLsn }},
            {{ name:'QueriesInTrx', type:'line', symbol:'none', smooth:true, lineStyle:{{width:1.5}}, itemStyle:{{color:'#ee6666'}}, areaStyle:{{opacity:0.05}}, data:proxyTrx }}
        ],
        null
    ));
    resCharts.push(routeChart);
    window.addEventListener('resize', function(){{ routeChart.resize(); }});
}})();'''


def _script_node_charts(ctx):
    """resource 章节：各节点 CPU / 内存 / IOPS / 连接数图表与缩放联动。"""
    return '''function makeLineChart(domId, metricKey) {
    var chart = echarts.init(document.getElementById(domId));
    var series = [];
    var legendData = [];

    chartNodes.forEach(function(nd, i) {
        var label = nd.label;
        var d = metricKey === 'connections'
            ? nd.connections.map(function(p){ return [p[0], +(p[1]/maxConn*100).toFixed(2)]; })
            : nd[metricKey];
        series.push({ name:label, type:'line', symbol:'none', smooth:true, lineStyle:{width:1.5}, itemStyle:{color:colors[i%colors.length]}, areaStyle:{opacity:0.05}, data:d });
        legendData.push(label);
    });

    chart.setOption({
        tooltip: { trigger:'axis', formatter:function(params) {
            if(!params.length) return '';
            var t=new Date(params[0].value[0]);
            var s=t.getFullYear()+'-'+(t.getMonth()+1).toString().padStart(2,'0')+'-'+t.getDate().toString().padStart(2,'0')+' '+t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
            var r='<b>'+s+'</b><br/>';
            params.forEach(function(p){ r+=p.marker+p.seriesName+': '+p.value[1].toFixed(2)+'%<br/>'; });
            return r;
        } },
        legend: { data:legendData, top:0, type:'scroll', textStyle:{fontSize:10} },
        grid: { left:45, right:15, top:30, bottom:55 },
        xAxis: { type:'time', axisLabel:{fontSize:10, formatter:'{MM}-{dd} {HH}:{mm}'} },
        yAxis: { type:'value', min:0, max:100, axisLabel:{fontSize:10} },
        dataZoom: [
            {type:'inside'},
            {type:'slider', height:20, bottom:5, borderColor:'#ddd', fillerColor:'rgba(84,112,198,0.15)', handleStyle:{color:'#5470c6'}, textStyle:{fontSize:10}, labelFormatter:function(v){ var d=new Date(v); return (d.getMonth()+1).toString().padStart(2,'0')+'-'+d.getDate().toString().padStart(2,'0')+' '+d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0'); }}
        ],
        series: series
    });
    resCharts.push(chart);
    window.addEventListener('resize', function(){ chart.resize(); });
}

makeLineChart('chart-cpu','cpu');
makeLineChart('chart-mem','memory');
makeLineChart('chart-iops','iops');
makeLineChart('chart-conn','connections');

// Link all resource charts zoom
var _zoomLock = false;
resCharts.forEach(function(c, ci) {
    c.on('dataZoom', function() {
        if (_zoomLock) return;
        _zoomLock = true;
        var opt = c.getOption();
        var dz = opt.dataZoom[0];
        resCharts.forEach(function(other, oi) {
            if (oi !== ci) other.dispatchAction({ type:'dataZoom', start:dz.start, end:dz.end });
        });
        _zoomLock = false;
    });
});'''


def _script_disk_chart(ctx):
    """space 章节：磁盘使用量趋势图。"""
    disk_total_js = ctx['disk_total_js']
    disk_detail_js = ctx['disk_detail_js']
    return f'''(function() {{
    var diskTotal = {disk_total_js};
    var diskDetail = {disk_detail_js};
    var el = document.getElementById('chart-disk');
    if (!el || diskTotal.length === 0) return;
    var chart = echarts.init(el);
    var series = [];
    var legendData = [];
    var diskColors = ['#3b82f6','#10b981','#f59e0b','#6366f1','#8b5cf6','#ec4899','#14b8a6','#f97316','#64748b'];
    var totalGb = diskTotal.map(function(p) {{ return [p[0], +(p[1]/1024).toFixed(2)]; }});
    series.push({{ name:'Total Size', type:'line', symbol:'none', smooth:true, lineStyle:{{width:2}}, itemStyle:{{color:diskColors[0]}}, areaStyle:{{opacity:0.08}}, data:totalGb }});
    legendData.push('Total Size');
    var idx = 1;
    Object.keys(diskDetail).forEach(function(label) {{
        var d = diskDetail[label].map(function(p) {{ return [p[0], +(p[1]/1024).toFixed(2)]; }});
        series.push({{ name:label, type:'line', symbol:'none', smooth:true, lineStyle:{{width:1.5}}, itemStyle:{{color:diskColors[idx%diskColors.length]}}, data:d }});
        legendData.push(label);
        idx++;
    }});
    chart.setOption({{
        tooltip: {{ trigger:'axis', formatter:function(params) {{
            if(!params.length) return '';
            var t=new Date(params[0].value[0]);
            var s=t.getFullYear()+'-'+(t.getMonth()+1).toString().padStart(2,'0')+'-'+t.getDate().toString().padStart(2,'0')+' '+t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
            var r='<b>'+s+'</b><br/>';
            params.forEach(function(p){{ r+=p.marker+p.seriesName+': '+p.value[1].toFixed(2)+' GB<br/>'; }});
            return r;
        }} }},
        legend: {{ data:legendData, top:0, type:'scroll', textStyle:{{fontSize:10}} }},
        grid: {{ left:55, right:15, top:30, bottom:55 }},
        xAxis: {{ type:'time', axisLabel:{{fontSize:10, formatter:'{{MM}}-{{dd}} {{HH}}:{{mm}}'}} }},
        yAxis: {{ type:'value', axisLabel:{{fontSize:10}} }},
        dataZoom: [
            {{type:'inside'}},
            {{type:'slider', height:20, bottom:5, borderColor:'#ddd', fillerColor:'rgba(59,130,246,0.15)', handleStyle:{{color:'#3b82f6'}}, textStyle:{{fontSize:10}}, labelFormatter:function(v){{ var d=new Date(v); return (d.getMonth()+1).toString().padStart(2,'0')+'-'+d.getDate().toString().padStart(2,'0')+' '+d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0'); }}}}
        ],
        series: series
    }});
    window.addEventListener('resize', function(){{ chart.resize(); }});
}})();'''


def _render_suffix(ctx, selected):
    """页脚 + 图表脚本（脚本片段随所属章节一起取舍）。"""
    script_parts = []
    if 'resource' in selected:
        script_parts.append(_script_resource_data(ctx))
        script_parts.append(_script_proxy_charts(ctx))
        script_parts.append(_script_node_charts(ctx))
    if 'space' in selected:
        script_parts.append(_script_disk_chart(ctx))

    chart_script = ''
    if script_parts:
        chart_script = '<script>\n' + '\n\n'.join(script_parts) + '\n</script>\n'

    return f'''    <div class="footer">{L('footer_text')}</div>
</div>

{chart_script}<script>{LANG_TOGGLE_JS}</script>
</body>
</html>'''


# ─── 页面组装入口 ─────────────────────────────────────────────────────────────

def assemble_page(ctx, items=None):
    """按选中的巡检项拼接章节片段，返回完整 HTML 字符串。

    ctx   : 包含所有模板变量的 dict（见 hi_renderer_html.render_html）
    items : 选中的巡检项集合（hi_config.ALL_ITEMS 的子集）；
            None 表示全量模式，渲染所有章节。
    """
    selected = set(config.ALL_ITEMS) if items is None else set(items)

    parts = [_render_prefix(ctx)]
    ordinal = 0
    for item, label_key in SECTION_ITEMS:
        if item is not None and item not in selected:
            continue
        parts.append(_SECTION_BUILDERS[label_key](ctx, _section_title(label_key, ordinal)))
        ordinal += 1
    parts.append(_render_suffix(ctx, selected))

    return '\n\n'.join(parts)
