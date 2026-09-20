"""PolarDB MySQL Health Inspection - Orchestration layer

Report generation dispatcher, cluster discovery, and single-cluster
inspection workflow.
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import hi_config as config
from hi_config import call_cli, REGIONS
from hi_collectors import (find_region, get_cluster_info, get_version_info,
    get_resource_usage, get_disk_usage_trend, get_proxy_performance,
    get_space_top20, get_slow_logs,
    get_max_connections_from_params, get_alert_history, get_auto_increment_usage,
    get_session_info)
from hi_processors import collect_report_data
from hi_score import calc_health_score
from hi_renderer_text import render_text
from hi_renderer_markdown import render_markdown
from hi_renderer_html import render_html


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def generate_report(cluster_id, region, cluster_info, version_info, resource_usage,
                    nodes, space_data, slow_logs, fmt='markdown',
                    param_max_conn=None, auto_inc_data=None, session_info=None,
                    alert_history=None, das_config=None, proxy_perf=None, items=None):
    data = collect_report_data(cluster_id, region, cluster_info, version_info,
                               resource_usage, nodes, space_data, slow_logs,
                               auto_inc_data, param_max_conn, session_info,
                               alert_history, das_config=das_config,
                               proxy_perf=proxy_perf)
    # Selected items determine which sections the HTML report retains; defaults to global --item config
    selected_items = set(config._INSPECT_ITEMS) if items is None else set(items)
    if fmt == 'html':
        return render_html(data, items=selected_items), data
    elif fmt == 'text':
        return render_text(data), data
    else:
        return render_markdown(data), data


# ─── Main ─────────────────────────────────────────────────────────────────────

def discover_all_clusters(region=None):
    """List all PolarDB MySQL clusters under the current account."""
    clusters = []
    regions_to_check = [region] if region else REGIONS

    def _fetch_region(r):
        found = []
        page = 1
        while True:
            data = call_cli('polardb', 'describe-db-clusters', r,
                            **{'db-type': 'MySQL', 'page-size': '50', 'page-number': str(page),
                               'biz-region-id': r})
            if not data:
                break
            items = data.get('Items', {}).get('DBCluster', [])
            for item in items:
                found.append({
                    'cluster_id': item.get('DBClusterId', ''),
                    'region': item.get('RegionId', r),
                    'description': item.get('DBClusterDescription', ''),
                    'status': item.get('DBClusterStatus', ''),
                    'db_version': item.get('DBVersion', ''),
                    'db_node_class': item.get('DBNodeClass', ''),
                    'db_node_number': item.get('DBNodeNumber', 0),
                })
            total = data.get('TotalRecordCount', 0)
            if page * 50 >= total or not items:
                break
            page += 1
        return found

    with ThreadPoolExecutor(max_workers=min(len(regions_to_check), 10)) as pool:
        futures = [pool.submit(_fetch_region, r) for r in regions_to_check]
        for f in as_completed(futures):
            clusters.extend(f.result())

    return clusters


def inspect_single_cluster(cluster_id, region, output_dir, fmt='html'):
    """Inspect a single cluster and return (cluster_id, report_path, summary_data)."""
    print(f'\n{"="*60}')
    print(f'  Inspecting cluster: {cluster_id}')
    print(f'{"="*60}')

    if not region:
        region = find_region(cluster_id)
        if not region:
            print(f'  ❌ Cluster {cluster_id} not found')
            return cluster_id, None, {'cluster_id': cluster_id, 'error': 'Cluster not found'}
    print(f'  Region: {region}')

    print('  📋 Basic info...', end=' ', flush=True)
    cluster_info = get_cluster_info(cluster_id, region)
    if not cluster_info:
        print('❌')
        return cluster_id, None, {'cluster_id': cluster_id, 'region': region, 'error': 'Failed to retrieve info'}
    print('✅')

    print('  🏷️  Version info...', end=' ', flush=True)
    version_info = get_version_info(cluster_id, region)
    print('✅' if version_info else '⚠️')

    nodes = cluster_info.get('DBNodes', [])
    if isinstance(nodes, dict):
        nodes = nodes.get('DBNode', [])

    param_max_conn = get_max_connections_from_params(cluster_id, region)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=config._INSPECT_DAYS)
    start_time = start.strftime('%Y-%m-%dT%H:%MZ')
    end_time = now.strftime('%Y-%m-%dT%H:%MZ')

    print(f'  📊 Collecting data in parallel (cluster + {len(nodes)} nodes)...', flush=True)

    resource_usage = None
    proxy_perf = None
    space_data = None
    slow_logs = None
    auto_inc_data = None
    session_info = None
    alert_history = None

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}
        if 'resource' in config._INSPECT_ITEMS:
            futures['resource'] = pool.submit(get_resource_usage, cluster_id, region, nodes, start_time, end_time)
            futures['proxy'] = pool.submit(get_proxy_performance, cluster_id, region, nodes, start_time, end_time)
        if 'space' in config._INSPECT_ITEMS:
            futures['space'] = pool.submit(get_space_top20, cluster_id)
            futures['auto_inc'] = pool.submit(get_auto_increment_usage, cluster_id)
        if 'slowlog' in config._INSPECT_ITEMS:
            futures['slow'] = pool.submit(get_slow_logs, cluster_id, region)
        if 'session' in config._INSPECT_ITEMS:
            futures['session'] = pool.submit(get_session_info, cluster_id, nodes)
        if 'alert' in config._INSPECT_ITEMS:
            futures['alert'] = pool.submit(get_alert_history, cluster_id, start_time, end_time)

        # When space is selected without resource, collect disk trend separately
        if 'space' in config._INSPECT_ITEMS and 'resource' not in config._INSPECT_ITEMS:
            futures['disk_trend'] = pool.submit(get_disk_usage_trend,
                                                cluster_id, region, start_time, end_time)

        if 'resource' in futures:
            resource_usage = futures['resource'].result()
        if 'proxy' in futures:
            proxy_perf = futures['proxy'].result()
        if 'space' in futures:
            space_data = futures['space'].result()
        if 'auto_inc' in futures:
            auto_inc_data = futures['auto_inc'].result()
        if 'disk_trend' in futures:
            disk_ts = futures['disk_trend'].result()
            if disk_ts:
                resource_usage = {'cluster': {}, 'nodes': {}, 'cluster_ts': {}, 'node_ts': {}}
                resource_usage['cluster_ts']['disk'] = disk_ts.get('disk', [])
                resource_usage['cluster_ts']['disk_detail'] = disk_ts.get('disk_detail', {})
        if 'slow' in futures:
            slow_logs = futures['slow'].result()
        if 'session' in futures:
            session_info = futures['session'].result()
        if 'alert' in futures:
            alert_history = futures['alert'].result()

    items_count = len(slow_logs.get('Items', {}).get('SQLSlowLog', [])) if slow_logs else 0
    print(f'  ✅ Data collection complete (slow logs: {items_count})')

    das_config = None
    if 'essd' in cluster_info.get('StorageType', '').lower():
        das_config = call_cli('polardb', 'describe-das-config', region,
                              **{'db-cluster-id': cluster_id})

    report, data = generate_report(cluster_id, region, cluster_info, version_info,
                                   resource_usage, nodes, space_data, slow_logs,
                                   fmt=fmt, param_max_conn=param_max_conn,
                                   auto_inc_data=auto_inc_data, session_info=session_info,
                                   alert_history=alert_history, das_config=das_config,
                                   proxy_perf=proxy_perf,
                                   items=config._INSPECT_ITEMS)

    ext = '.html' if fmt == 'html' else '.md' if fmt == 'markdown' else '.txt'
    report_filename = f'{cluster_id}_health_report{ext}'
    report_path = os.path.join(output_dir, report_filename)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'  📄 Report: {report_path}')

    # Build summary data for index page
    res = data.get('resource', {})
    cluster_res = res.get('cluster', {})
    nodes_res = res.get('nodes', {})
    iops_peak = max((nd.get('iops_usage_peak', 0) for nd in nodes_res.values()), default=0)
    iops_avg = sum(nd.get('iops_usage_avg', 0) for nd in nodes_res.values()) / max(len(nodes_res), 1)
    summary = {
        'cluster_id': cluster_id,
        'region': region,
        'description': cluster_info.get('DBClusterDescription', ''),
        'status': cluster_info.get('DBClusterStatus', ''),
        'db_version': data['basic_info'].get('db_version', ''),
        'revision_version': data['basic_info'].get('revision_version', ''),
        'category': data['basic_info'].get('category', ''),
        'category_en': data['basic_info'].get('category_en', ''),
        'category_zh': data['basic_info'].get('category_zh', ''),
        'storage_type': data['basic_info'].get('storage_type', ''),
        'node_count': len(data.get('nodes', [])),
        'node_class': data['nodes'][0]['class'] if data.get('nodes') else '',
        'node_cpu': data['nodes'][0].get('cpu', '') if data.get('nodes') else '',
        'node_mem': data['nodes'][0].get('mem', '') if data.get('nodes') else '',
        'cpu_avg': cluster_res.get('cpu_avg', 0),
        'cpu_peak': cluster_res.get('cpu_peak', 0),
        'mem_avg': cluster_res.get('mem_avg', 0),
        'mem_peak': cluster_res.get('mem_peak', 0),
        'iops_avg': round(iops_avg, 1),
        'iops_peak': iops_peak,
        'conn_avg_pct': cluster_res.get('conn_avg_pct', 0),
        'conn_peak_pct': cluster_res.get('conn_peak_pct', 0),
        'disk_avg_pct': cluster_res.get('disk_avg_pct', 0),
        'disk_peak_pct': cluster_res.get('disk_peak_pct', 0),
        'slow_count': data.get('slow_total', 0),
        'alert_count': len(data.get('alert_history', [])),
        'suggestions': data.get('suggestions', []),
        'report_file': report_filename,
    }

    # Pass-through data for cross-instance aggregation & health scoring
    summary['space_data'] = data.get('space', {})
    summary['alert_history'] = data.get('alert_history', [])
    summary['slow_logs_detail'] = data.get('slow_logs', [])
    summary['latest_version'] = data['basic_info'].get('latest_version', '')
    summary['is_latest'] = data['basic_info'].get('is_latest', True)
    summary['lock_mode'] = cluster_info.get('LockMode', 'Unlock')
    summary['expire_time'] = cluster_info.get('ExpireTime', '')
    summary['storage_total'] = data['basic_info'].get('storage_space', 0)

    # Health score (depends on cpu_peak, slow_count, alert_history, etc.)
    _score, _deductions = calc_health_score(summary)
    summary['health_score'] = _score
    summary['health_deductions'] = _deductions

    return cluster_id, report_path, summary
