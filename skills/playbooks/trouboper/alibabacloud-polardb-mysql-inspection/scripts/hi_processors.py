"""PolarDB MySQL 健康巡检 - 报告数据组装"""
import json
import os
from datetime import datetime, timedelta, timezone

import hi_config as config
from hi_utils import format_bytes, _node_role_short
from hi_config import STORAGE_TYPE_MAP, CATEGORY_MAP
from hi_suggestions import generate_suggestions


def collect_report_data(cluster_id, region, cluster_info, version_info,
                        resource_usage, nodes, space_data, slow_logs,
                        auto_inc_data=None, param_max_conn=None, session_info=None,
                        alert_history=None, das_config=None, proxy_perf=None):
    data = {}
    data['cluster_id'] = cluster_id
    data['region'] = region
    data['inspect_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    storage_space = cluster_info.get('StorageSpace', 0)
    storage_max = cluster_info.get('StorageMax', 0)
    storage_used = cluster_info.get('StorageUsed', 0)
    storage_type_raw = cluster_info.get('StorageType', 'N/A')
    storage_type = STORAGE_TYPE_MAP.get(storage_type_raw, storage_type_raw)
    is_essd = 'essd' in storage_type_raw.lower()
    is_psl = not is_essd
    auto_scale = ''
    auto_scale_upper = 0
    if is_essd and das_config:
        auto_scale = das_config.get('StorageAutoScale', '')
        auto_scale_upper = das_config.get('StorageUpperBound', 0)
    data['basic_info'] = {
        'db_type': cluster_info.get('DBType', 'MySQL'),
        'db_version': cluster_info.get('DBVersion', 'N/A'),
        'status': cluster_info.get('DBClusterStatus', 'N/A'),
        'storage_type': storage_type,
        'is_essd': is_essd,
        'is_psl': is_psl,
        'category': CATEGORY_MAP.get(cluster_info.get('Category', ''), (cluster_info.get('Category', 'N/A'), cluster_info.get('Category', 'N/A')))[0],
        'category_en': CATEGORY_MAP.get(cluster_info.get('Category', ''), (cluster_info.get('Category', 'N/A'), cluster_info.get('Category', 'N/A')))[0],
        'category_zh': CATEGORY_MAP.get(cluster_info.get('Category', ''), (cluster_info.get('Category', 'N/A'), cluster_info.get('Category', 'N/A')))[1],
        'storage_used': storage_used,
        'storage_space': storage_space,
        'storage_max': storage_max,
        'storage_auto_scale': auto_scale == 'Enable',
        'storage_auto_scale_upper': auto_scale_upper,
        'storage_used_str': format_bytes(storage_used),
        'storage_space_str': format_bytes(storage_space) if storage_space else '',
        'storage_max_str': format_bytes(storage_max),
    }
    if version_info:
        data['basic_info'].update({
            'revision_version': version_info.get('DBRevisionVersion', 'N/A'),
            'latest_version': version_info.get('DBLatestVersion', 'N/A'),
            'is_latest': version_info.get('IsLatestVersion', 'false') == 'true',
            'proxy_version': version_info.get('ProxyRevisionVersion', 'N/A'),
        })
    else:
        data['basic_info'].update({
            'revision_version': 'N/A', 'latest_version': 'N/A',
            'is_latest': False, 'proxy_version': 'N/A',
        })

    node_list = []
    total_max_conn = 0
    total_max_iops = 0
    for node in nodes:
        max_conn = node.get('MaxConnections', 0)
        max_iops = node.get('MaxIOPS', 0)
        mem_size = node.get('MemorySize', 0)
        mc = int(max_conn) if isinstance(max_conn, (int, float)) else 0
        mi = int(max_iops) if isinstance(max_iops, (int, float)) else 0
        total_max_conn += mc
        total_max_iops += mi
        mem_str = f'{int(mem_size)/1024:.0f}GB' if isinstance(mem_size, (int, float)) and mem_size >= 1024 else f'{mem_size}MB'
        node_list.append({
            'id': node.get('DBNodeId', 'N/A'),
            'role': node.get('DBNodeRole', 'N/A'),
            'role_short': _node_role_short(node),
            'status': node.get('DBNodeStatus', 'N/A'),
            'class': node.get('DBNodeClass', 'N/A'),
            'cpu': node.get('CpuCores', 'N/A'),
            'mem': mem_str,
            'max_conn': mc,
            'max_iops': mi,
        })
    if param_max_conn and param_max_conn > 0:
        for nd in node_list:
            nd['max_conn'] = param_max_conn
        total_max_conn = param_max_conn * len(node_list)
    data['nodes'] = node_list
    data['total_max_conn'] = total_max_conn
    data['total_max_iops'] = total_max_iops
    data['session_info'] = session_info

    res = {}
    if resource_usage:
        cm = resource_usage.get('cluster', {})
        nm = resource_usage.get('nodes', {})
        cpu_avg, cpu_peak = cm.get('cpu', (0, 0))
        mem_avg, mem_peak = cm.get('memory', (0, 0))
        disk_avg_mb, disk_peak_mb = cm.get('disk_mb', (0, 0))
        io_avg, io_peak = cm.get('io', (0, 0))
        conn_avg, conn_peak = cm.get('connections', (0, 0))

        storage_cap = storage_space if storage_space else storage_max
        storage_cap_mb = storage_cap / (1024 * 1024) if storage_cap else 0
        disk_avg_pct = round(disk_avg_mb / storage_cap_mb * 100, 2) if storage_cap_mb else 0
        disk_peak_pct = round(disk_peak_mb / storage_cap_mb * 100, 2) if storage_cap_mb else 0
        conn_avg_pct = round(conn_avg / total_max_conn * 100, 2) if total_max_conn else 0
        conn_peak_pct = round(conn_peak / total_max_conn * 100, 2) if total_max_conn else 0

        res['cluster'] = {
            'cpu_avg': cpu_avg, 'cpu_peak': cpu_peak,
            'mem_avg': mem_avg, 'mem_peak': mem_peak,
            'disk_avg_mb': disk_avg_mb, 'disk_peak_mb': disk_peak_mb,
            'disk_avg_pct': disk_avg_pct, 'disk_peak_pct': disk_peak_pct,
            'io_avg': io_avg, 'io_peak': io_peak,
            'conn_avg': conn_avg, 'conn_peak': conn_peak,
            'conn_avg_pct': conn_avg_pct, 'conn_peak_pct': conn_peak_pct,
        }

        res['nodes'] = {}
        for nd in node_list:
            nid = nd['id']
            nd_m = nm.get(nid, {})
            n_cpu_avg, n_cpu_peak = nd_m.get('cpu', (0, 0))
            n_mem_avg, n_mem_peak = nd_m.get('memory', (0, 0))
            n_conn_avg, n_conn_peak = nd_m.get('connections', (0, 0))
            n_active_avg, n_active_peak = nd_m.get('active_connections', (0, 0))
            n_iops_avg, n_iops_peak = nd_m.get('iops', (0, 0))
            n_iops_usage_avg, n_iops_usage_peak = nd_m.get('iops_usage', (0, 0))
            n_conn_pct = round(n_conn_peak / nd['max_conn'] * 100, 2) if nd['max_conn'] else 0
            res['nodes'][nid] = {
                'role': nd['role'],
                'role_short': nd.get('role_short', 'RO'),
                'cpu_avg': n_cpu_avg, 'cpu_peak': n_cpu_peak,
                'mem_avg': n_mem_avg, 'mem_peak': n_mem_peak,
                'conn_avg': n_conn_avg, 'conn_peak': n_conn_peak,
                'conn_pct': n_conn_pct,
                'active_avg': n_active_avg, 'active_peak': n_active_peak,
                'iops_avg': n_iops_avg, 'iops_peak': n_iops_peak,
                'iops_usage_avg': n_iops_usage_avg, 'iops_usage_peak': n_iops_usage_peak,
                'max_conn': nd['max_conn'],
            }
        res['node_ts'] = resource_usage.get('node_ts', {})
        res['cluster_ts'] = resource_usage.get('cluster_ts', {})
    res['proxy_ts'] = proxy_perf or {}
    data['resource'] = res

    # Space
    space = {'table_list': [], 'total_used': 0, 'daily_inc': 0, 'anomalies': []}
    if space_data:
        table_stats = space_data.get('TableStats', [])
        if isinstance(table_stats, str):
            try:
                table_stats = json.loads(table_stats)
            except json.JSONDecodeError:
                table_stats = []
        sorted_tables = sorted(table_stats, key=lambda x: x.get('TotalSize', x.get('PhyTotalSize', 0)), reverse=True)
        for t in sorted_tables[:20]:
            total_size = t.get('TotalSize', t.get('PhyTotalSize', 0))
            data_size = t.get('DataSize', 0)
            index_size = t.get('IndexSize', 0)
            rows = t.get('TableRows', t.get('RowCount', 0))
            frag_size = t.get('FreeSize', t.get('FragSize', 0))
            space['table_list'].append({
                'db': t.get('DbName', t.get('DatabaseName', 'N/A')),
                'table': t.get('TableName', 'N/A'),
                'total': total_size, 'total_str': format_bytes(total_size),
                'data': data_size, 'data_str': format_bytes(data_size),
                'index': index_size, 'index_str': format_bytes(index_size),
                'rows': int(rows) if isinstance(rows, (int, float)) else 0,
                'frag': frag_size,
            })
        space['total_used'] = space_data.get('TotalUsedStorageSize', 0)
        space['daily_inc'] = space_data.get('DailyIncrement', 0)
        for t in sorted_tables:
            total_size = t.get('TotalSize', t.get('PhyTotalSize', 0))
            data_size = t.get('DataSize', 0)
            index_size = t.get('IndexSize', 0)
            frag_size = t.get('FreeSize', t.get('FragSize', 0))
            db_name = t.get('DbName', t.get('DatabaseName', 'N/A'))
            table_name = t.get('TableName', 'N/A')
            if total_size and total_size > 0 and frag_size / total_size > 0.3 and frag_size > 100 * 1024 * 1024:
                pct = round(frag_size / total_size * 100, 1)
                space['anomalies'].append({
                    'type': '空间碎片', 'db': db_name, 'table': table_name,
                    'detail': f'碎片率 {pct}%，碎片 {format_bytes(frag_size)}'
                })
            if index_size == 0 and data_size > 100 * 1024 * 1024:
                space['anomalies'].append({
                    'type': '大表无索引', 'db': db_name, 'table': table_name,
                    'detail': f'数据 {format_bytes(data_size)}，无索引'
                })

    auto_inc_list = []
    if auto_inc_data:
        for item in auto_inc_data:
            db_name = item.get('DbName', item.get('Schema', 'N/A'))
            table_name = item.get('TableName', 'N/A')
            column_name = item.get('ColumnName', 'N/A')
            data_type = item.get('DataType', item.get('ColumnType', 'N/A'))
            current_val = item.get('AutoIncrementCurrentValue', item.get('CurrentValue', 0))
            max_val = item.get('MaximumValue', item.get('MaxValue', 0))
            usage = item.get('AutoIncrementRatio', item.get('Usage', 0))
            try:
                usage = float(usage)
            except (ValueError, TypeError):
                usage = 0
            auto_inc_list.append({
                'db': db_name, 'table': table_name, 'column': column_name,
                'data_type': data_type, 'current': current_val, 'max': max_val,
                'usage': usage,
            })
            if usage >= 0.9:
                level = '危险' if usage >= 0.95 else '警告'
                space['anomalies'].append({
                    'type': '自增主键溢出', 'db': db_name, 'table': table_name,
                    'detail': f'{level}：使用率 {usage*100:.1f}%（{current_val:,}/{max_val:,}）'
                })
    auto_inc_list.sort(key=lambda x: x['usage'], reverse=True)
    data['auto_inc'] = auto_inc_list
    data['space'] = space

    # Slow logs (merge by db+sql)
    slow_list = []
    if slow_logs:
        items = slow_logs.get('Items', {}).get('SQLSlowLog', [])
        merged = {}
        for item in items:
            db = item.get('DBName', 'N/A')
            sql = item.get('SQLText', '')
            sql_hash = item.get('SQLHASH', item.get('SQLHash', ''))
            key = (db, sql)
            if key in merged:
                m = merged[key]
                m['count'] += item.get('TotalExecutionCounts', 0)
                m['total_time'] += item.get('TotalExecutionTimes', 0)
                m['max_time'] = max(m['max_time'], item.get('MaxExecutionTime', 0))
                m['parse_rows'] += item.get('ParseTotalRowCounts', 0)
                m['return_rows'] += item.get('ReturnTotalRowCounts', 0)
            else:
                merged[key] = {
                    'db': db, 'sql_hash': sql_hash,
                    'count': item.get('TotalExecutionCounts', 0),
                    'total_time': item.get('TotalExecutionTimes', 0),
                    'max_time': item.get('MaxExecutionTime', 0),
                    'parse_rows': item.get('ParseTotalRowCounts', 0),
                    'return_rows': item.get('ReturnTotalRowCounts', 0),
                    'sql_text': sql,
                }
        for m in merged.values():
            cnt = m['count'] or 1
            m['avg_parse_rows'] = round(m['parse_rows'] / cnt)
            m['avg_return_rows'] = round(m['return_rows'] / cnt)
        slow_list = sorted(merged.values(), key=lambda x: x['total_time'], reverse=True)[:20]
    data['slow_logs'] = slow_list
    data['slow_total'] = len(slow_list)

    data['alert_history'] = alert_history or []

    suggestions_list = generate_suggestions(data, resource_usage, version_info)
    data['suggestions'] = suggestions_list
    return data
