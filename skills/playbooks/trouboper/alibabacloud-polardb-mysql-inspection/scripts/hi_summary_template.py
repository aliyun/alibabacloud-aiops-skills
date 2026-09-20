# -*- coding: utf-8 -*-
"""Batch inspection summary HTML page template (8-section layout).

Contains the large f-string HTML template for the summary report.
{{ }} are CSS/JS brace escapes in f-strings.
Do not run code formatters on this file.
"""

from hi_i18n import I18N_CSS, LANG_TOGGLE_JS, LANG_TOGGLE_HTML, _i18n, L


# ---------------------------------------------------------------------------
# CSS (extracted to keep template readable; stays under 32KB total)
# ---------------------------------------------------------------------------

_SUMMARY_CSS = """
:root {
  --ok:#10b981; --warn:#f59e0b; --danger:#ef4444; --info:#3b82f6;
  --bg:#f8fafc; --card:#fff; --border:#e2e8f0;
  --text:#1e293b; --muted:#64748b; --blue:#1e40af;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--text);line-height:1.6;padding:1.5rem;}
.container{max-width:1280px;margin:0 auto;}

/* header */
.header{background:linear-gradient(135deg,#1e40af,#3b82f6);color:#fff;
  padding:1.5rem 2rem;border-radius:12px;margin-bottom:1.5rem;position:relative;}
.header h1{font-size:1.4rem;margin-bottom:.4rem;}
.header .meta{opacity:.92;font-size:.85rem;}
.header .meta span{margin-right:1.2rem;}

/* toc */
.toc{background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:.7rem 1.2rem;margin-bottom:1.5rem;font-size:.85rem;
  position:sticky;top:0;z-index:50;box-shadow:0 1px 3px rgba(0,0,0,.06);}
.toc a{color:#1e40af;margin-right:1rem;text-decoration:none;white-space:nowrap;}
.toc a:hover{text-decoration:underline;}

/* sections */
.section{background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:1.4rem 1.5rem;margin-bottom:1.5rem;}
.section h2{font-size:1.15rem;color:#1e40af;margin-bottom:.9rem;
  padding-bottom:.5rem;border-bottom:2px solid #e2e8f0;}
.section h3{font-size:1rem;color:#334155;margin:1rem 0 .5rem 0;}

/* tables */
table{width:100%;border-collapse:collapse;font-size:.85rem;}
th,td{padding:.45rem .7rem;text-align:left;border-bottom:1px solid var(--border);}
th{background:#f1f5f9;font-weight:600;color:#334155;}
tr:hover{background:#f8fafc;}
.ok{color:var(--ok);} .warn{color:var(--warn);} .danger{color:var(--danger);}
.na{color:var(--muted);}
td.ok,td.warn,td.danger{font-weight:600;}
.table-scroll{overflow-x:auto;}
.link-cell a{color:var(--blue);text-decoration:none;}
.link-cell a:hover{text-decoration:underline;}
.no-data{text-align:center;color:#94a3b8;padding:2rem !important;}
.sql-cell{font-family:monospace;font-size:.78rem;max-width:600px;
  white-space:pre-wrap;word-break:break-word;line-height:1.4;}
.ok-msg{color:var(--ok);font-weight:500;padding:.5rem 0;}

/* KPI grid */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:.8rem;margin:.5rem 0 1rem 0;}
.kpi-card{background:#f8fafc;border:1px solid var(--border);border-radius:6px;
  padding:.7rem .9rem;text-align:center;}
.kpi-card .label{font-size:.78rem;color:var(--muted);}
.kpi-card .value{font-size:1.4rem;font-weight:600;color:#1e40af;}
.kpi-card .sub{font-size:.72rem;color:var(--muted);margin-top:.1rem;}

/* charts */
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:.8rem;}
.chart-card{background:#f8fafc;border:1px solid var(--border);border-radius:6px;
  padding:10px 12px;}
.chart-card h4{margin:0 0 4px 0;font-size:.88rem;color:#334155;}
.echart{width:100%;min-height:240px;}

/* tabs */
.tab-bar{display:flex;gap:4px;margin-bottom:1rem;
  border-bottom:2px solid var(--border);flex-wrap:wrap;}
.tab-btn{padding:8px 16px;border:none;background:transparent;font-size:.85rem;
  cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;
  color:#64748b;transition:all .15s;}
.tab-btn:hover{color:var(--text);}
.tab-btn.active{color:var(--blue);border-bottom-color:var(--blue);font-weight:600;}
.tab-panel{display:none;}
.tab-panel.active{display:block;}

/* footer */
.footer{text-align:center;color:var(--muted);font-size:.8rem;margin:1.5rem 0 0 0;}

@media(max-width:768px){
  body{padding:1rem;}
  .kpi-grid{grid-template-columns:repeat(2,1fr);}
  .chart-grid{grid-template-columns:1fr;}
  table{font-size:.75rem;}
  th,td{padding:.3rem .5rem;}
}
"""


def assemble_summary_page(ctx):
    """Accept a dict with all template variables, return complete HTML string."""
    title = ctx['title']
    inspect_time = ctx['inspect_time']
    time_range = ctx.get('time_range', '')
    total_instances = ctx.get('total_instances', 0)
    global_score = ctx.get('global_score', 0)
    score_color = ctx.get('score_color', '#10b981')

    sec_overview = ctx['section_overview']
    sec_health = ctx['section_health']
    sec_alerts = ctx['section_alerts']
    sec_resource = ctx['section_resource']
    sec_slow = ctx['section_slow']
    sec_space = ctx['section_space']
    sec_version = ctx['section_version']
    sec_conclusion = ctx['section_conclusion']

    health_dist_json = ctx['health_dist_json']
    region_dist_json = ctx['region_dist_json']
    status_dist_json = ctx['status_dist_json']
    category_dist_json = ctx['category_dist_json']
    alert_levels_json = ctx['alert_levels_json']

    # Chart unavailable message
    _chart_na = _i18n("Chart library unavailable", "图表库不可用")
    _na_div = f'<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;">{_chart_na}</div>'

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{_i18n("PolarDB MySQL Inspection Summary","PolarDB MySQL 巡检汇总报告")}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
{_SUMMARY_CSS}
{I18N_CSS}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    {LANG_TOGGLE_HTML}
    <h1>📊 {title}</h1>
    <div class="meta">
      <span>{_i18n("Generated","巡检时间")}: {inspect_time}</span>
      <span>{_i18n("Time Range","时间范围")}: {time_range}</span>
      <span>{_i18n("Total Instances","实例总数")}: {total_instances}</span>
      <span>{_i18n("Global Health","全局健康度")}: <b style="color:{score_color}">{global_score}/100</b></span>
    </div>
  </div>

  <!-- TOC -->
  <div class="toc">
    <a href="#sec-1">{L('toc_overview')}</a>
    <a href="#sec-2">{L('toc_health_ranking')}</a>
    <a href="#sec-3">{L('toc_alerts')}</a>
    <a href="#sec-4">{L('toc_resource')}</a>
    <a href="#sec-5">{L('toc_slow_logs')}</a>
    <a href="#sec-6">{L('toc_space')}</a>
    <a href="#sec-7">{L('toc_version')}</a>
    <a href="#sec-8">{L('toc_conclusion')}</a>
  </div>

  <!-- Section 1: Overview -->
  <div class="section" id="sec-1">
    <h2>{_i18n("1. Inspection Overview","一、巡检概览")}</h2>
    {sec_overview}
  </div>

  <!-- Section 2: Health Ranking -->
  <div class="section" id="sec-2">
    <h2>{_i18n("2. Health Score Ranking (lowest TOP 20)","二、健康得分排行（最不健康 TOP 20）")}</h2>
    {sec_health}
  </div>

  <!-- Section 3: Alert Statistics -->
  <div class="section" id="sec-3">
    <h2>{_i18n("3. Alert Instance Statistics","三、告警实例统计")}</h2>
    {sec_alerts}
  </div>

  <!-- Section 4: Resource TOP Boards -->
  <div class="section" id="sec-4">
    <h2>{_i18n("4. Resource Utilization TOP Boards","四、资源水位 TOP 榜")}</h2>
    {sec_resource}
  </div>

  <!-- Section 5: Slow Log TOP Boards -->
  <div class="section" id="sec-5">
    <h2>{_i18n("5. Slow Log TOP Boards","五、慢日志 TOP 榜")}</h2>
    {sec_slow}
  </div>

  <!-- Section 6: Space Analysis -->
  <div class="section" id="sec-6">
    <h2>{_i18n("6. Space Analysis","六、空间分析")}</h2>
    {sec_space}
  </div>

  <!-- Section 7: Version & Expiration -->
  <div class="section" id="sec-7">
    <h2>{_i18n("7. Version & Expiration","七、版本与到期")}</h2>
    {sec_version}
  </div>

  <!-- Section 8: Conclusion -->
  <div class="section" id="sec-8">
    <h2>{_i18n("8. Inspection Conclusion","八、巡检结论")}</h2>
    {sec_conclusion}
  </div>

  <div class="footer">PolarDB MySQL Inspection Summary &middot; {inspect_time}</div>
</div>

<script>
/* ── Language toggle ── */
{LANG_TOGGLE_JS}

/* ── Tab switching ── */
document.querySelectorAll('.tab-btn').forEach(function(btn){{
  btn.addEventListener('click',function(){{
    var bar=btn.parentNode;
    bar.querySelectorAll('.tab-btn').forEach(function(b){{b.classList.remove('active');}});
    var container=bar.parentNode;
    container.querySelectorAll('.tab-panel').forEach(function(p){{p.classList.remove('active');}});
    btn.classList.add('active');
    var p=container.querySelector('#panel-'+btn.getAttribute('data-tab'));
    if(p) p.classList.add('active');
  }});
}});

/* ── TOC smooth scroll ── */
document.querySelectorAll('.toc a').forEach(function(a){{
  a.addEventListener('click',function(e){{
    e.preventDefault();
    var t=document.querySelector(this.getAttribute('href'));
    if(t) t.scrollIntoView({{behavior:'smooth'}});
  }});
}});

/* ── ECharts: parameterized creators ── */
function makePie(domId, data) {{
  var el=document.getElementById(domId);
  if(!el) return;
  if(typeof echarts==='undefined'){{el.innerHTML='{_na_div}';return;}}
  var c=echarts.init(el);
  c.setOption({{
    tooltip:{{trigger:'item',formatter:'{{b}}: {{c}} ({{d}}%)'}},
    legend:{{orient:'vertical',right:5,top:'middle',textStyle:{{fontSize:11}}}},
    series:[{{type:'pie',radius:['40%','70%'],center:['38%','50%'],
      itemStyle:{{borderRadius:6,borderColor:'#fff',borderWidth:2}},
      label:{{show:true,formatter:'{{b}}\\n{{c}}',fontSize:11}},
      data:data}}]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}}

function makeBar(domId, data) {{
  var el=document.getElementById(domId);
  if(!el) return;
  if(typeof echarts==='undefined'){{el.innerHTML='{_na_div}';return;}}
  if(!data||!data.length){{el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;">No data</div>';return;}}
  var c=echarts.init(el);
  c.setOption({{
    tooltip:{{trigger:'axis'}},
    grid:{{left:120,right:30,top:10,bottom:30}},
    xAxis:{{type:'value',axisLabel:{{fontSize:11}}}},
    yAxis:{{type:'category',
      data:data.map(function(d){{return d.name;}}).reverse(),
      axisLabel:{{fontSize:11,width:100,overflow:'truncate'}},inverse:false}},
    series:[{{type:'bar',
      data:data.map(function(d){{return d.value;}}).reverse(),
      barMaxWidth:30,
      itemStyle:{{color:'#3b82f6',borderRadius:[0,4,4,0]}},
      label:{{show:true,position:'right',fontSize:11}}}}]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}}

function makeAlertBar(domId, data) {{
  var el=document.getElementById(domId);
  if(!el) return;
  if(typeof echarts==='undefined'){{el.innerHTML='{_na_div}';return;}}
  if(!data||!data.length) return;
  var c=echarts.init(el);
  var lc=function(n){{
    var u=(n||'').toUpperCase();
    if(u==='P1'||u.indexOf('CRITICAL')>=0) return '#ef4444';
    if(u==='P2'||u.indexOf('WARN')>=0) return '#f59e0b';
    return '#3b82f6';
  }};
  c.setOption({{
    tooltip:{{trigger:'axis'}},
    grid:{{left:50,right:20,top:10,bottom:30}},
    xAxis:{{type:'category',data:data.map(function(d){{return d.name;}})}},
    yAxis:{{type:'value'}},
    series:[{{type:'bar',
      data:data.map(function(d){{return {{value:d.value,itemStyle:{{color:lc(d.name)}}}}}}),
      label:{{show:true,position:'top'}}}}]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}}

/* ── Chart data ── */
var _healthData={health_dist_json};
var _regionData={region_dist_json};
var _statusData={status_dist_json};
var _categoryData={category_dist_json};
var _alertLevels={alert_levels_json};

/* ── Lazy-load via IntersectionObserver ── */
var _chartInits={{
  'chart-health':   function(){{ makePie('chart-health', _healthData); }},
  'chart-regions':  function(){{ makeBar('chart-regions', _regionData); }},
  'chart-status':   function(){{ makePie('chart-status', _statusData); }},
  'chart-category': function(){{ makePie('chart-category', _categoryData); }},
  'chart-alert-levels': function(){{ makeAlertBar('chart-alert-levels', _alertLevels); }}
}};
var _done={{}};
if('IntersectionObserver' in window){{
  var _obs=new IntersectionObserver(function(entries){{
    entries.forEach(function(e){{
      if(e.isIntersecting && !_done[e.target.id]){{
        _done[e.target.id]=1;
        var fn=_chartInits[e.target.id];
        if(fn) fn();
      }}
    }});
  }},{{rootMargin:'200px'}});
  document.querySelectorAll('.echart').forEach(function(el){{_obs.observe(el);}});
}}else{{
  Object.keys(_chartInits).forEach(function(k){{_chartInits[k]();}});
}}
</script>
</body>
</html>'''
    return html
