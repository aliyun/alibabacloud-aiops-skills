# -*- coding: utf-8 -*-
"""Bilingual (EN/ZH) internationalisation helpers for the inspection report.

Provides CSS-based language switching: two <span> siblings are rendered for
every label; CSS rules hide one of them based on the ``<html lang="...">``
attribute.  A toggle button + tiny JS snippet let the user switch at runtime.
"""


# ---------------------------------------------------------------------------
# Core helper
# ---------------------------------------------------------------------------

def _i18n(en, zh):
    """Generate bilingual HTML span for CSS-based language switching."""
    return f'<span class="i18n-en">{en}</span><span class="i18n-zh">{zh}</span>'


# ---------------------------------------------------------------------------
# CSS / JS / HTML assets
# ---------------------------------------------------------------------------

I18N_CSS = """
/* i18n language switching */
html[lang="en"] .i18n-zh { display: none !important; }
html[lang="zh"] .i18n-en, html[lang="zh-CN"] .i18n-en { display: none !important; }
html:not([lang]) .i18n-en { display: none !important; }
.lang-toggle {
    position: absolute; right: 20px; top: 20px;
    padding: 6px 16px; border: 1px solid #d0d7de; border-radius: 6px;
    background: #fff; color: #24292f; cursor: pointer; font-size: 13px;
    z-index: 100;
}
.lang-toggle:hover { background: #f3f4f6; }
"""

LANG_TOGGLE_JS = """
(function() {
    var savedLang = localStorage.getItem('lang') || 'zh-CN';
    document.documentElement.lang = savedLang;
    var btn = document.querySelector('.lang-toggle');
    if (!btn) return;
    function updateBtn() {
        var cur = document.documentElement.lang;
        btn.textContent = (cur === 'en') ? '中文' : 'English';
    }
    updateBtn();
    window.toggleLang = function() {
        var cur = document.documentElement.lang;
        var next = (cur === 'en') ? 'zh-CN' : 'en';
        document.documentElement.lang = next;
        localStorage.setItem('lang', next);
        updateBtn();
    };
})();
"""

LANG_TOGGLE_HTML = '<button class="lang-toggle" onclick="toggleLang()">English</button>'


# ---------------------------------------------------------------------------
# Translation dictionary
# ---------------------------------------------------------------------------

LABELS = {
    # -- Report title / footer --
    'title_page':           {'en': 'PolarDB MySQL Inspection Report',  'zh': 'PolarDB MySQL 巡检报告'},
    'title_report':         {'en': 'PolarDB MySQL Health Inspection Report', 'zh': 'PolarDB MySQL 实例健康巡检报告'},
    'footer_text':          {'en': 'Inspection Complete · PolarDB MySQL Health Inspection', 'zh': '巡检完成 · PolarDB MySQL Health Inspection'},
    # -- Header meta --
    'meta_time':            {'en': 'Inspection Time', 'zh': '巡检时间'},
    'meta_instance':        {'en': 'Instance',        'zh': '实例'},
    # -- Section titles (一~七) --
    'section_basic_info':   {'en': 'I. Basic Instance Information',           'zh': '一、实例基本信息'},
    'section_session':      {'en': 'II. Current Sessions',                    'zh': '二、当前会话'},
    'section_resource':     {'en': 'III. Resource Usage (Last 7 Days)',        'zh': '三、资源使用率（最近 7 天）'},
    'section_space':        {'en': 'IV. Space Inspection',                    'zh': '四、空间巡检'},
    'section_slowlog':      {'en': 'V. Slow Log Statistics (Last 7 Days)',    'zh': '五、慢日志统计（最近 7 天）'},
    'section_alert':        {'en': 'VI. Alert History (Last 7 Days)',         'zh': '六、报警历史（最近 7 天）'},
    'section_suggestion':   {'en': 'VII. Conclusions &amp; Suggestions',      'zh': '七、巡检结论与建议'},
    # -- Basic-info labels --
    'lbl_db_type':          {'en': 'DB Type',          'zh': '数据库类型'},
    'lbl_major_version':    {'en': 'Major Version',    'zh': '大版本'},
    'lbl_cluster_status':   {'en': 'Cluster Status',   'zh': '集群状态'},
    'lbl_minor_version':    {'en': 'Minor Version',    'zh': '内核小版本'},
    'lbl_latest_version':   {'en': 'Latest Available', 'zh': '最新可用版本'},
    'lbl_version_status':   {'en': 'Version Status',   'zh': '版本状态'},
    'lbl_proxy_version':    {'en': 'Proxy Version',    'zh': 'Proxy 版本'},
    'lbl_storage_type':     {'en': 'Storage Type',     'zh': '存储类型'},
    'lbl_cluster_category': {'en': 'Cluster Category', 'zh': '集群类别'},
    'lbl_storage_used':     {'en': 'Storage Used',     'zh': '已用存储'},
    'lbl_storage_capacity': {'en': 'Storage Capacity', 'zh': '存储容量'},
    'lbl_auto_scaling':     {'en': 'Auto Scaling',     'zh': '自动扩展'},
    # -- Node table headers --
    'th_node_id':           {'en': 'Node ID',          'zh': '节点ID'},
    'th_role':              {'en': 'Role',             'zh': '角色'},
    'th_status':            {'en': 'Status',           'zh': '状态'},
    'th_spec':              {'en': 'Spec',             'zh': '规格'},
    'th_cpu':               {'en': 'CPU',              'zh': 'CPU'},
    'th_memory':            {'en': 'Memory',           'zh': '内存'},
    'th_max_conn':          {'en': 'Max Connections',  'zh': '最大连接'},
    'th_max_iops':          {'en': 'Max IOPS',         'zh': '最大IOPS'},
    # -- Resource table headers --
    'th_node':              {'en': 'Node',                         'zh': '节点'},
    'th_cpu_avg_peak':      {'en': 'CPU (Avg/Peak)',               'zh': 'CPU (均值/峰值)'},
    'th_mem_avg_peak':      {'en': 'Memory (Avg/Peak)',            'zh': '内存 (均值/峰值)'},
    'th_iops_avg_peak':     {'en': 'IOPS (Avg/Peak)',              'zh': 'IOPS (均值/峰值)'},
    'th_conn_avg_peak':     {'en': 'Connections (Avg/Peak)',       'zh': '连接 (均值/峰值)'},
    'th_active_avg_peak':   {'en': 'Active Conn (Avg/Peak)',       'zh': '活跃连接 (均值/峰值)'},
    'th_res_status':        {'en': 'Status',                       'zh': '状态'},
    # -- Chart labels --
    'chart_proxy_trend':    {'en': 'Proxy Monitoring Trends',      'zh': 'Proxy 监控趋势'},
    'chart_proxy_cpu':      {'en': 'Proxy CPU Usage (%)',          'zh': 'Proxy CPU 使用率（%）'},
    'chart_proxy_route':    {'en': 'Proxy Session Routing (req/s)','zh': 'Proxy 会话路由（次/秒）'},
    'chart_db_trend':       {'en': 'DB Monitoring Trends',         'zh': 'DB 监控趋势'},
    'chart_cpu':            {'en': 'CPU Usage (%)',                'zh': 'CPU 使用率（%）'},
    'chart_mem':            {'en': 'Memory Usage (%)',             'zh': '内存使用率（%）'},
    'chart_iops':           {'en': 'IOPS Usage (%)',               'zh': 'IOPS 使用率（%）'},
    'chart_conn':           {'en': 'Connection Usage (%)',         'zh': '连接使用率（%）'},
    # -- Space sub-sections & table headers --
    'sub_disk_trend':       {'en': '4.1 Storage Trend (7 Days, GB)',             'zh': '4.1 空间变化趋势（7天，GB）'},
    'sub_space_top20':      {'en': '4.2 DB &amp; Table Space Overview (TOP20)', 'zh': '4.2 库表空间概况（TOP20）'},
    'sub_anomaly_list':     {'en': '4.3 Anomaly List',             'zh': '4.3 异常列表'},
    'th_rank':              {'en': '#',           'zh': '#'},
    'th_database':          {'en': 'Database',    'zh': '数据库'},
    'th_table':             {'en': 'Table',       'zh': '表名'},
    'th_total_space':       {'en': 'Total',       'zh': '总空间'},
    'th_data':              {'en': 'Data',        'zh': '数据'},
    'th_index':             {'en': 'Index',       'zh': '索引'},
    'th_fragment':          {'en': 'Fragment',    'zh': '碎片'},
    'th_rows':              {'en': 'Rows',        'zh': '行数'},
    # -- Renderer: version status --
    'status_upgradable':    {'en': '⬆️ Upgradable',  'zh': '⬆️ 可升级'},
    'status_latest':        {'en': '✅ Up to date',   'zh': '✅ 已是最新'},
    'unit_cores':           {'en': ' Cores',          'zh': '核'},
    # -- Renderer: session labels --
    'lbl_select_node':      {'en': 'Select Node:',   'zh': '选择节点：'},
    'lbl_total_sessions':   {'en': 'Total Sessions',  'zh': '总会话数'},
    'lbl_active_sessions':  {'en': 'Active Sessions', 'zh': '活跃会话数'},
    'lbl_max_active_time':  {'en': 'Max Active Time', 'zh': '最长活跃时间'},
    'sub_active_sessions':  {'en': 'Active Sessions',  'zh': '活跃会话'},
    'sub_abnormal_sessions':{'en': 'Abnormal Sessions (uncommitted txn &gt;10s)', 'zh': '异常会话（长时间未提交的事务&gt;10s）'},
    'sub_binlog_sessions':  {'en': 'Binlog Dump Sessions', 'zh': 'Binlog Dump 会话'},
    'msg_no_active_session':{'en': 'No active or abnormal sessions', 'zh': '当前无活跃或异常会话'},
    'msg_no_session_info':  {'en': '⚠️ Session info not available',  'zh': '⚠️ 未获取到会话信息'},
    # -- Renderer: session summary --
    'msg_session_normal':   {'en': 'Session status normal', 'zh': '会话状态正常'},
    # -- Renderer: session stats --
    'sub_by_user':          {'en': 'By User',        'zh': '按用户统计'},
    'sub_by_client_ip':     {'en': 'By Client IP',   'zh': '按客户端 IP 统计'},
    'sub_by_database':      {'en': 'By Database',    'zh': '按数据库统计'},
    'th_user':              {'en': 'User',            'zh': '用户'},
    'th_total_conn':        {'en': 'Total Conn',     'zh': '总连接'},
    'th_active':            {'en': 'Active',         'zh': '活跃'},
    'th_client_ip':         {'en': 'Client IP',      'zh': '客户端 IP'},
    # -- Renderer: disk trend --
    'lbl_current_usage':    {'en': 'Current Usage',  'zh': '当前使用'},
    'lbl_7days_ago':        {'en': '7 Days Ago',     'zh': '7天前'},
    'lbl_7days_change':     {'en': '7-Day Change',   'zh': '7天变化'},
    'lbl_daily_growth':     {'en': 'Daily Growth',   'zh': '日均增长'},
    # -- Renderer: anomaly --
    'th_type':              {'en': 'Type',   'zh': '类型'},
    'th_detail':            {'en': 'Detail', 'zh': '详情'},
    'msg_no_anomaly':       {'en': '✅ No anomalies found', 'zh': '✅ 未发现异常'},
    # -- Renderer: slow log --
    'th_sqlhash':           {'en': 'SQLHASH',          'zh': 'SQLHASH'},
    'th_count':             {'en': 'Count',            'zh': '次数'},
    'th_total_time':        {'en': 'Total(s)',         'zh': '总耗时(s)'},
    'th_max_time':          {'en': 'Max(s)',           'zh': '最大(s)'},
    'th_avg_scan_rows':     {'en': 'Avg Scan Rows',   'zh': '平均扫描行数'},
    'th_avg_return_rows':   {'en': 'Avg Return Rows', 'zh': '平均返回行数'},
    'th_sql_summary':       {'en': 'SQL Summary',     'zh': 'SQL 摘要'},
    'sub_sqlhash_detail':   {'en': 'SQLHASH &amp; Full SQL Reference', 'zh': 'SQLHASH 与完整 SQL 对照'},
    'th_full_sql':          {'en': 'Full SQL',         'zh': '完整 SQL'},
    'msg_no_slowlog':       {'en': '✅ No slow logs in the last 7 days', 'zh': '✅ 最近 7 天无慢日志记录'},
    # -- Renderer: alert --
    'th_time':              {'en': 'Time',          'zh': '时间'},
    'th_level':             {'en': 'Level',         'zh': '级别'},
    'th_rule':              {'en': 'Rule',          'zh': '规则'},
    'th_metric':            {'en': 'Metric',        'zh': '指标'},
    'th_cur_value':         {'en': 'Value',         'zh': '当前值'},
    'th_threshold':         {'en': 'Threshold',     'zh': '阈值'},
    'th_notify_status':     {'en': 'Notification',  'zh': '通知状态'},
    'msg_no_alert':         {'en': '✅ No alerts in the last 7 days', 'zh': '✅ 最近 7 天无报警记录'},
    # -- Renderer: suggestions --
    'msg_no_issue':         {'en': '✅ No issues found. Instance is running normally.', 'zh': '✅ 巡检未发现明显问题，实例运行状态良好。'},
    'risk_high':            {'en': '🔴 High Risk',   'zh': '🔴 高风险'},
    'risk_medium':          {'en': '🟡 Medium Risk', 'zh': '🟡 中风险'},
    'risk_low':             {'en': '🔵 Low Risk',    'zh': '🔵 低风险'},
    # -- Renderer: auto-scale --
    'auto_scale_psl':       {'en': 'Auto Scaling (PSL Storage)', 'zh': '自动扩展（PSL 存储）'},
    'auto_scale_off':       {'en': 'Disabled',       'zh': '未开启'},
    # -- Renderer: misc --
    'lbl_none_db':          {'en': '(none)', 'zh': '(无)'},

    # ===================================================================
    # Summary-report labels (8-section layout)
    # ===================================================================

    # -- Header metadata --
    'header_time_range':        {'en': 'Time Range',            'zh': '巡检时间范围'},
    'header_total_instances':   {'en': 'Total Instances',       'zh': '实例总数'},
    'header_global_health':     {'en': 'Global Health',         'zh': '全局健康度'},
    'header_scanned_total':     {'en': 'Scanned Total',         'zh': '扫描发现总数'},

    # -- TOC navigation --
    'toc_overview':             {'en': '1. Overview',                   'zh': '1. 巡检概览'},
    'toc_health_ranking':       {'en': '2. Health Ranking',             'zh': '2. 健康排行'},
    'toc_alerts':               {'en': '3. Alert Statistics',           'zh': '3. 告警统计'},
    'toc_resource':             {'en': '4. Resource TOP Boards',        'zh': '4. 资源水位 TOP 榜'},
    'toc_slow_logs':            {'en': '5. Slow Log TOP Boards',        'zh': '5. 慢日志 TOP 榜'},
    'toc_space':                {'en': '6. Space Analysis',             'zh': '6. 空间分析'},
    'toc_version':              {'en': '7. Version & Expiration',       'zh': '7. 版本与到期'},
    'toc_conclusion':           {'en': '8. Conclusion',                 'zh': '8. 巡检结论'},

    # -- Section 1: Overview (KPIs) --
    'kpi_scanned_total':        {'en': 'Scanned Total',         'zh': '扫描发现总数'},
    'kpi_global_health':        {'en': 'Global Health',         'zh': '全局健康度'},

    # -- Section 2: Health Ranking --
    'health_ranking_title':     {'en': 'Health Score Ranking (lowest TOP 20)',   'zh': '健康得分排行（最低 TOP 20）'},
    'th_health_score':          {'en': 'Health Score',          'zh': '健康分'},
    'th_top_deductions':        {'en': 'Top Deductions',        'zh': '主要扣分项'},

    # -- Section 3: Alert Statistics --
    'alert_statistics_title':   {'en': 'Alert Instance Statistics',     'zh': '告警实例统计'},
    'kpi_instances_with_alerts':{'en': 'Instances w/ Alerts',   'zh': '有告警实例数'},
    'kpi_total_alerts':         {'en': 'Total Alerts',          'zh': '告警总数'},
    'th_max_level':             {'en': 'Max Level',             'zh': '最高级别'},
    'th_high_severity':         {'en': 'High Severity',         'zh': '高严重数'},

    # -- Section 5: Slow Log (expanded) --
    'slow_count_top20':         {'en': 'Slow Query Count TOP 20',               'zh': '慢日志条数 TOP 20'},
    'slow_time_top20':          {'en': 'Slow Query Total Time TOP 20',          'zh': '慢日志总耗时 TOP 20'},
    'sql_max_time_top20':       {'en': 'Single SQL Max Execution Time TOP 20',  'zh': '单条 SQL 最大执行时间 TOP 20'},
    'th_max_exec_time':         {'en': 'Max Exec Time (s)',     'zh': '最大执行时间 (秒)'},
    'th_sql_templates':         {'en': 'SQL Templates',         'zh': 'SQL 模板数'},
    'th_sql_text':              {'en': 'SQL Text',              'zh': 'SQL 文本'},

    # -- Section 6: Space Analysis --
    'space_analysis_title':     {'en': 'Space Analysis',                        'zh': '空间分析'},
    'instance_space_top20':     {'en': 'Instance Used Space TOP 20',            'zh': '实例已用空间 TOP 20'},
    'table_size_top20':         {'en': 'Single Table Size TOP 20 (Cross-Instance)', 'zh': '单表大小 TOP 20（跨实例）'},
    'fragmentation_top20':      {'en': 'Fragmentation Rate TOP 20',             'zh': '碎片率 TOP 20'},
    'th_used_space':            {'en': 'Used Space',            'zh': '已用空间'},
    'th_total_storage':         {'en': 'Total Storage',         'zh': '总存储'},
    'th_daily_growth':          {'en': 'Daily Growth',          'zh': '日增量'},
    'th_days_left':             {'en': 'Days Left',             'zh': '预计可用天数'},
    'th_tables':                {'en': 'Tables',                'zh': '表数量'},
    'th_data_size':             {'en': 'Data Size',             'zh': '数据大小'},
    'th_index_size':            {'en': 'Index Size',            'zh': '索引大小'},
    'th_frag_size':             {'en': 'Fragment Size',         'zh': '碎片大小'},
    'th_frag_pct':              {'en': 'Frag Rate',             'zh': '碎片率'},

    # -- Section 7: Version & Expiration --
    'version_expiration_title': {'en': 'Version & Expiration',  'zh': '版本与到期'},
    'upgradable_kernels':       {'en': 'Upgradable Kernel Instances',           'zh': '可升级内核实例'},
    'expiring_30d':             {'en': 'Instances Expiring within 30 Days',     'zh': '30 天内到期实例'},
    'expiring_90d':             {'en': 'Instances Expiring within 90 Days',     'zh': '90 天内到期实例'},
    'th_current_kernel':        {'en': 'Current Kernel',        'zh': '当前内核'},
    'th_latest_kernel':         {'en': 'Latest Kernel',         'zh': '最新内核'},
    'th_expire_date':           {'en': 'Expire Date',           'zh': '到期日期'},
    'th_days_remaining':        {'en': 'Days Left',             'zh': '剩余天数'},
    'msg_no_expiration':        {'en': 'No expiring instances (PolarDB pay-as-you-go)', 'zh': '无到期实例（PolarDB 按量付费）'},

    # -- Section 8: Conclusion --
    'conclusion_title':         {'en': 'Inspection Conclusion', 'zh': '巡检结论'},
    'kpi_healthy':              {'en': 'Healthy',               'zh': '健康'},
    'kpi_needs_attention':      {'en': 'Needs Attention',       'zh': '需关注'},
    'kpi_urgent':               {'en': 'Urgent',                'zh': '紧急'},
    'th_problem':               {'en': 'Problem',               'zh': '问题'},
    'th_impacted_instances':    {'en': 'Impacted Instances',    'zh': '受影响实例'},
    'msg_no_problems':          {'en': 'No problems detected',  'zh': '未发现问题'},
}


# ---------------------------------------------------------------------------
# Lookup shortcut
# ---------------------------------------------------------------------------

def L(key):
    """Lookup bilingual label by key."""
    entry = LABELS[key]
    return _i18n(entry['en'], entry['zh'])
