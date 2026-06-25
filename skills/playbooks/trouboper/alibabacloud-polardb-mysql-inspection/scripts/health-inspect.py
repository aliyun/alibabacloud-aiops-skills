#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PolarDB MySQL Instance Health Inspection Script
Performs comprehensive inspection via aliyun CLI calling PolarDB API and DAS API

Usage:
    python3 health-inspect.py <cluster_id> [options]

Examples:
    python3 health-inspect.py pc-bp167736gfqyn483x
    python3 health-inspect.py pc-bp167736gfqyn483x --region cn-hangzhou
    python3 health-inspect.py pc-bp167736gfqyn483x --profile myprofile --output ./report.txt
"""

import subprocess
import json
import sys
import os
import time
import argparse
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

_CLI_PROFILE = None
_INSPECT_DAYS = 7

ALL_ITEMS = ['resource', 'space', 'slowlog', 'session', 'alert']
_INSPECT_ITEMS = set(ALL_ITEMS)
_last_cli_error = ''


def _repair_plugin_manifest():
    """Repair corrupted plugin manifest by running plugin update."""
    try:
        subprocess.run(['aliyun', 'plugin', 'update'],
                       capture_output=True, text=True, timeout=60)
    except Exception:
        pass


def _sync_after_install():
    """Flush filesystem caches after plugin installation to avoid 'text file busy'."""
    try:
        subprocess.run(['sync'], capture_output=True, text=True, timeout=10)
    except Exception:
        pass
    time.sleep(1)


def ensure_cli_plugins():
    """Ensure required aliyun CLI plugins are installed and healthy."""
    try:
        subprocess.run(['aliyun', 'configure', 'set', '--auto-plugin-install', 'true'],
                       capture_output=True, text=True, timeout=10)
    except Exception:
        pass
    try:
        check = subprocess.run(['aliyun', 'plugin', 'list'], capture_output=True, text=True, timeout=15)
        combined = (check.stdout or '') + (check.stderr or '')
        if 'manifest' in combined.lower() or 'unexpected' in combined.lower() or check.returncode != 0:
            print('  🔧 Repairing CLI plugin manifest...', flush=True)
            _repair_plugin_manifest()
    except Exception:
        _repair_plugin_manifest()
    installed_any = False
    required_plugins = ['polardb', 'cms', 'das']
    for plugin in required_plugins:
        try:
            result = subprocess.run(['aliyun', 'plugin', 'list'], capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and f'aliyun-cli-{plugin}' not in result.stdout:
                print(f'  📦 Installing CLI plugin: {plugin}...', end='', flush=True)
                install = subprocess.run(['aliyun', 'plugin', 'install', '--name', f'aliyun-cli-{plugin}'],
                                         capture_output=True, text=True, timeout=60)
                if install.returncode == 0:
                    print(' ✅', flush=True)
                    installed_any = True
                else:
                    print(f' ⚠️ ({(install.stderr or install.stdout or "unknown error").strip()[:100]})', flush=True)
        except Exception:
            pass
    if installed_any:
        _sync_after_install()
    for plugin in required_plugins:
        try:
            verify = subprocess.run(['aliyun', 'plugin', 'list'], capture_output=True, text=True, timeout=15)
            if verify.returncode == 0 and f'aliyun-cli-{plugin}' not in verify.stdout:
                print(f'  ⚠️ Plugin {plugin} not available, related features may fail', flush=True)
        except Exception:
            pass


_plugin_install_lock = __import__('threading').Lock()


def _install_plugin_for(product, repair=False):
    """Install or repair a CLI plugin for the given product."""
    if not _plugin_install_lock.acquire(timeout=120):
        return
    try:
        if repair:
            print(f'  🔧 Repairing CLI plugin: {product}...', flush=True)
            _repair_plugin_manifest()
            subprocess.run(['aliyun', 'plugin', 'uninstall', '--name', f'aliyun-cli-{product}'],
                           capture_output=True, text=True, timeout=30)
        else:
            print(f'  📦 Installing CLI plugin: {product}...', flush=True)
        subprocess.run(['aliyun', 'plugin', 'install', '--name', f'aliyun-cli-{product}'],
                       capture_output=True, text=True, timeout=60)
        _sync_after_install()
    except Exception:
        pass
    finally:
        _plugin_install_lock.release()


_ALLOWED_ACTIONS = frozenset({
    'polardb:describe-db-clusters', 'polardb:describe-db-cluster-attribute',
    'polardb:describe-db-cluster-version', 'polardb:describe-db-cluster-performance',
    'polardb:describe-db-node-performance', 'polardb:describe-db-proxy-performance',
    'polardb:describe-db-nodes', 'polardb:describe-db-cluster-parameters',
    'polardb:describe-das-config', 'polardb:describe-slow-logs',
    'polardb:describe-slow-log-records',
    'das:create-storage-analysis-task', 'das:get-storage-analysis-result',
    'das:get-auto-increment-usage-statistic', 'das:get-mysql-all-session-async',
    'cms:describe-alert-log-list', 'cms:describe-metric-rule-list',
})


def call_cli(product, action, region=None, endpoint=None, **kwargs):
    global _last_cli_error
    _last_cli_error = ''
    action_key = f'{product}:{action}'
    if action_key not in _ALLOWED_ACTIONS:
        _last_cli_error = f'blocked: {action_key} not in read-only allowlist'
        return None
    cmd = ['aliyun', product, action]
    if _CLI_PROFILE:
        cmd.extend(['--profile', _CLI_PROFILE])
    if region:
        cmd.extend(['--region', region])
    if endpoint:
        cmd.extend(['--endpoint', endpoint])
    for key, value in kwargs.items():
        cmd.extend([f'--{key}', str(value)])

    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            combined_output = (result.stdout or '') + (result.stderr or '')
            if 'text file busy' in combined_output.lower() and attempt < max_attempts - 1:
                time.sleep(2)
                continue
            is_manifest_error = 'plugin manifest' in combined_output.lower() or 'check plugin status' in combined_output.lower()
            if is_manifest_error and attempt < max_attempts - 1:
                _install_plugin_for(product, repair=True)
                continue
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    idx = result.stdout.find('{')
                    if idx > 0:
                        try:
                            return json.loads(result.stdout[idx:])
                        except json.JSONDecodeError:
                            pass
                    raw = result.stdout.strip()[:200] if result.stdout else '(empty)'
                    _last_cli_error = f'invalid JSON: {raw}'
            else:
                stderr = result.stderr.strip()
                if attempt < max_attempts - 1 and ('Plugin' in stderr and 'not installed' in stderr or 'text file busy' in stderr.lower()):
                    _install_plugin_for(product)
                    continue
                throttled = any(k in stderr for k in ('Throttling', 'throttl', 'Too Many', 'Busy'))
                if not throttled and result.returncode != 0:
                    try:
                        err_obj = json.loads(stderr or result.stdout or '')
                        err_code = err_obj.get('Code', '') or err_obj.get('code', '')
                        throttled = 'Throttling' in str(err_code) or 'Busy' in str(err_code)
                    except (json.JSONDecodeError, AttributeError):
                        pass
                if throttled and attempt < max_attempts - 1:
                    import random as _rand
                    wait = min(3 ** attempt + _rand.uniform(1, 3), 30)
                    print(f'  [RETRY] {product} {action}: throttled, retry in {wait:.1f}s ({attempt+1}/{max_attempts})', file=sys.stderr)
                    time.sleep(wait)
                    continue
                _last_cli_error = stderr[:200] if stderr else f'exit code {result.returncode}'
        except subprocess.TimeoutExpired:
            if attempt < max_attempts - 1:
                import random as _rand
                wait = min(3 ** attempt + _rand.uniform(1, 3), 30)
                print(f'  [RETRY] {product} {action}: timeout, retry in {wait:.1f}s ({attempt+1}/{max_attempts})', file=sys.stderr)
                time.sleep(wait)
                continue
            _last_cli_error = 'timeout (60s)'
        break
    return None


REGIONS = [
    'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen',
    'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
    'cn-wulanchabu', 'cn-nanjing', 'cn-fuzhou', 'cn-guangzhou',
    'cn-hongkong', 'ap-southeast-1', 'ap-southeast-3',
    'ap-southeast-5', 'ap-southeast-6', 'ap-southeast-7',
    'ap-northeast-1', 'ap-northeast-2',
    'us-west-1', 'us-east-1',
    'eu-west-1', 'eu-central-1', 'me-east-1', 'me-central-1',
]


def find_region(cluster_id):
    print(f'🔍 Discovering region for cluster {cluster_id}...')
    for region in REGIONS:
        data = call_cli('polardb', 'describe-db-cluster-attribute',
                        region, **{'db-cluster-id': cluster_id})
        if data and data.get('DBClusterId'):
            actual_region = data.get('RegionId', region)
            print(f'   ✅ Region: {actual_region}')
            return actual_region
    return None


def get_cluster_info(cluster_id, region):
    data = call_cli('polardb', 'describe-db-cluster-attribute',
                    region, **{'db-cluster-id': cluster_id})
    return data


def get_version_info(cluster_id, region):
    data = call_cli('polardb', 'describe-db-cluster-version',
                    region, **{'db-cluster-id': cluster_id})
    return data


def _merge_perf_items(perf_list):
    merged = {}
    for perf in perf_list:
        if not perf:
            continue
        for item in perf.get('PerformanceKeys', {}).get('PerformanceItem', []):
            mn = item.get('MetricName', '')
            points = item.get('Points', {}).get('PerformanceItemValue', [])
            if mn not in merged:
                merged[mn] = []
            merged[mn].extend(points)
    return {'PerformanceKeys': {'PerformanceItem': [
        {'MetricName': mn, 'Points': {'PerformanceItemValue': pts}}
        for mn, pts in merged.items()
    ]}}


def _call_perf_daily(product, action, region, start_time, end_time, **extra):
    st = datetime.strptime(start_time, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc)
    et = datetime.strptime(end_time, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc)
    day_ranges = []
    cur = st
    while cur < et:
        nxt = min(cur + timedelta(days=1), et)
        day_ranges.append((cur.strftime('%Y-%m-%dT%H:%MZ'), nxt.strftime('%Y-%m-%dT%H:%MZ')))
        cur = nxt

    def _fetch(s, e):
        return call_cli(product, action, region, **{**extra, 'start-time': s, 'end-time': e})

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(_fetch, s, e) for s, e in day_ranges]
        results = [f.result() for f in futures]
    return _merge_perf_items(results)


def extract_metric_values(perf_data, target_metric=None):
    if not perf_data:
        return []
    items = perf_data.get('PerformanceKeys', {}).get('PerformanceItem', [])
    all_values = []
    for item in items:
        metric_name = item.get('MetricName', '')
        if target_metric and metric_name != target_metric:
            continue
        points = item.get('Points', {}).get('PerformanceItemValue', [])
        for point in points:
            try:
                all_values.append(float(point.get('Value', '')))
            except (ValueError, TypeError):
                pass
    return all_values


def extract_metric_timeseries(perf_data, target_metric):
    if not perf_data:
        return []
    items = perf_data.get('PerformanceKeys', {}).get('PerformanceItem', [])
    ts = []
    for item in items:
        if item.get('MetricName', '') != target_metric:
            continue
        points = item.get('Points', {}).get('PerformanceItemValue', [])
        for p in points:
            try:
                ts.append((int(p['Timestamp']), float(p['Value'])))
            except (KeyError, ValueError, TypeError):
                pass
    return sorted(ts, key=lambda x: x[0])


def calc_avg_peak(values):
    if not values:
        return 0.0, 0.0
    return round(sum(values) / len(values), 2), round(max(values), 2)


def get_node_performance(node_id, region, key, metric_name, start_time, end_time):
    perf = _call_perf_daily('polardb', 'describe-db-node-performance', region,
                            start_time, end_time,
                            **{'db-node-id': node_id, 'key': key})
    values = extract_metric_values(perf, metric_name)
    ts = extract_metric_timeseries(perf, metric_name)
    return calc_avg_peak(values), ts


def get_resource_usage(cluster_id, region, nodes, start_time, end_time):
    results = {'cluster': {}, 'nodes': {}, 'cluster_ts': {}, 'node_ts': {}}

    _cp = lambda key: _call_perf_daily('polardb', 'describe-db-cluster-performance',
                                       region, start_time, end_time,
                                       **{'db-cluster-id': cluster_id, 'key': key})
    _np = lambda nid, key: _call_perf_daily('polardb', 'describe-db-node-performance',
                                             region, start_time, end_time,
                                             **{'db-node-id': nid, 'key': key})

    cluster_keys = ['PolarDBCPU', 'PolarDBMemory', 'PolarDBDiskUsage', 'PolarDBConnections']

    def _fetch_node(node):
        node_id = node.get('DBNodeId', '')
        if not node_id:
            return None, None, None
        perf_node = _np(node_id, 'PolarDBCPU,PolarDBMemory,PolarDBConnections,PolarDBIOSTAT')
        node_data = {}
        node_ts = {}
        node_data['cpu'] = calc_avg_peak(extract_metric_values(perf_node, 'cpu_ratio'))
        node_ts['cpu'] = extract_metric_timeseries(perf_node, 'cpu_ratio')
        node_data['memory'] = calc_avg_peak(extract_metric_values(perf_node, 'mem_ratio'))
        node_ts['memory'] = extract_metric_timeseries(perf_node, 'mem_ratio')
        node_data['connections'] = calc_avg_peak(extract_metric_values(perf_node, 'mean_total_session'))
        node_data['active_connections'] = calc_avg_peak(extract_metric_values(perf_node, 'mean_active_session'))
        node_ts['conn'] = extract_metric_timeseries(perf_node, 'mean_total_session')
        node_data['iops'] = calc_avg_peak(extract_metric_values(perf_node, 'mean_iops'))
        node_data['iops_usage'] = calc_avg_peak(extract_metric_values(perf_node, 'mean_iops_usage'))
        node_ts['iops'] = extract_metric_timeseries(perf_node, 'mean_iops_usage')
        return node_id, node_data, node_ts

    with ThreadPoolExecutor(max_workers=min(len(cluster_keys) + 1 + len(nodes), 5)) as pool:
        cluster_futures = {k: pool.submit(_cp, k) for k in cluster_keys}
        io_future = pool.submit(_cp, 'PolarDBInnoDBDataReadWrite')
        node_futures = [pool.submit(_fetch_node, node) for node in nodes]

        cluster_perfs = {k: f.result() for k, f in cluster_futures.items()}
        perf_cluster_io = io_future.result()
        for f in as_completed(node_futures):
            node_id, node_data, node_ts = f.result()
            if node_id:
                results['nodes'][node_id] = node_data
                results['node_ts'][node_id] = node_ts

    perf_cluster = _merge_perf_items([cluster_perfs[k] for k in cluster_keys])

    cluster_cpu_vals = extract_metric_values(perf_cluster, 'cpu_ratio')
    cluster_mem_vals = extract_metric_values(perf_cluster, 'mem_ratio')
    cluster_level_ok = bool(cluster_cpu_vals or cluster_mem_vals)

    results['cluster']['cpu'] = calc_avg_peak(cluster_cpu_vals)
    results['cluster']['memory'] = calc_avg_peak(cluster_mem_vals)
    results['cluster']['disk_mb'] = calc_avg_peak(extract_metric_values(perf_cluster, 'mean_data_size'))
    results['cluster_ts']['disk'] = extract_metric_timeseries(perf_cluster, 'mean_data_size')
    results['cluster']['connections'] = calc_avg_peak(extract_metric_values(perf_cluster, 'mean_total_session'))

    disk_detail_map = {
        'Data Size': 'mean_data_size',
        'Log Size': 'mean_log_size',
        'Redo Log Size': 'mean_redo_log_size',
        'Binlog Size': 'mean_binlog_size',
        'Undo Log Size': 'mean_undo_log_size',
        'Other Log Size': 'mean_other_log_size',
        'Temp Size': 'mean_tmp_data_size',
        'System Size': 'mean_sys_data_size',
    }
    results['cluster_ts']['disk_detail'] = {}
    for label, metric in disk_detail_map.items():
        ts = extract_metric_timeseries(perf_cluster, metric)
        if ts:
            results['cluster_ts']['disk_detail'][label] = ts

    read_vals = extract_metric_values(perf_cluster_io, 'mean_innodb_data_read')
    write_vals = extract_metric_values(perf_cluster_io, 'mean_innodb_data_written')
    if read_vals and write_vals:
        combined = [r + w for r, w in zip(read_vals, write_vals)]
        results['cluster']['io'] = calc_avg_peak(combined)
    else:
        results['cluster']['io'] = (0.0, 0.0)

    if not cluster_level_ok and results['nodes']:
        all_cpu, all_mem, all_conn = [], [], []
        for nd in results['nodes'].values():
            avg_c, peak_c = nd.get('cpu', (0, 0))
            avg_m, peak_m = nd.get('memory', (0, 0))
            avg_cn, peak_cn = nd.get('connections', (0, 0))
            all_cpu.extend([avg_c, peak_c])
            all_mem.extend([avg_m, peak_m])
            all_conn.extend([avg_cn, peak_cn])
        if all_cpu:
            results['cluster']['cpu'] = (round(sum(all_cpu) / len(all_cpu), 2), round(max(all_cpu), 2))
        if all_mem:
            results['cluster']['memory'] = (round(sum(all_mem) / len(all_mem), 2), round(max(all_mem), 2))
        if all_conn:
            results['cluster']['connections'] = (round(sum(all_conn) / 2, 2), round(max(all_conn), 2))

    return results


STORAGE_TYPE_MAP = {
    'HighPerformance': 'PSL5',
    'PSL4': 'PSL4',
    'essdautopl': 'ESSD AutoPL',
    'essdpl0': 'ESSD PL0',
    'essdpl1': 'ESSD PL1',
    'essdpl2': 'ESSD PL2',
    'essdpl3': 'ESSD PL3',
}

CATEGORY_MAP = {
    'Normal': 'Cluster Edition',
    'Basic': 'Single-node',
    'Archive': 'High-compression Engine (X-Engine)',
    'NormalMultimaster': 'Multi-master Cluster',
    'SENormal': 'Standard Edition',
}


def get_proxy_performance(cluster_id, region, nodes, start_time, end_time):
    print('📡 Proxy monitoring...', end=' ', flush=True)
    proxy_ts = {}
    try:
        perf = _call_perf_daily('polardb', 'describe-db-proxy-performance',
                                region, start_time, end_time,
                                **{'db-cluster-id': cluster_id,
                                   'key': 'PolarProxy_CpuUsage,PolarProxy_LsnNotMatch,PolarProxy_QueriesInTrx'})
        proxy_ts['cpu'] = extract_metric_timeseries(perf, 'docker_container_cpu')
        proxy_ts['lsn_not_match'] = extract_metric_timeseries(perf, 'service_queries_lsn_not_match')
        proxy_ts['queries_in_trx'] = extract_metric_timeseries(perf, 'service_queries_in_trx')
    except Exception:
        proxy_ts['cpu'] = []
        proxy_ts['lsn_not_match'] = []
        proxy_ts['queries_in_trx'] = []

    proxy_ts['node_conns'] = {}

    def _fetch_proxy_node(node):
        nid = node.get('DBNodeId', node.get('id', ''))
        if not nid:
            return None, None
        try:
            perf_n = _call_perf_daily('polardb', 'describe-db-proxy-performance',
                                      region, start_time, end_time,
                                      **{'db-cluster-id': cluster_id,
                                         'db-node-id': nid,
                                         'key': 'PolarProxy_DBConns'})
            rs = _node_role_short(node)
            label = f'{nid}({rs})'
            return label, extract_metric_timeseries(perf_n, 'server_connections')
        except Exception:
            return None, None

    with ThreadPoolExecutor(max_workers=min(len(nodes), 3)) as pool:
        futures = [pool.submit(_fetch_proxy_node, node) for node in nodes]
        for f in as_completed(futures):
            label, ts = f.result()
            if label and ts:
                proxy_ts['node_conns'][label] = ts

    print('✅')
    return proxy_ts


def get_space_top20(cluster_id):
    print('💾 Space analysis...', end='', flush=True)
    create_resp = call_cli('das', 'create-storage-analysis-task',
                           endpoint='das.cn-shanghai.aliyuncs.com',
                           **{'instance-id': cluster_id})
    if not create_resp:
        print(f' ❌ Creation failed ({_last_cli_error})')
        return None

    task_data = create_resp.get('Data', {})
    if not task_data.get('CreateTaskSuccess'):
        detail = task_data.get('ErrorMessage') or task_data.get('Message') or json.dumps(task_data, ensure_ascii=False)[:150]
        print(f' ❌ Task failed ({detail})')
        return None

    task_id = task_data.get('TaskId')

    for i in range(30):
        time.sleep(5)
        print('.', end='', flush=True)
        result = call_cli('das', 'get-storage-analysis-result',
                          endpoint='das.cn-shanghai.aliyuncs.com',
                          **{'instance-id': cluster_id, 'task-id': task_id})
        if result and result.get('Code') == 200:
            data = result.get('Data', {})
            task_state = data.get('TaskState', '')
            if task_state in ('FINISH', 'SUCCESS') or data.get('TaskSuccess'):
                print(' ✅')
                sar = data.get('StorageAnalysisResult', {})
                if isinstance(sar, str):
                    try:
                        sar = json.loads(sar)
                    except json.JSONDecodeError:
                        sar = {}
                return sar
    print(' ⚠️ Timeout')
    return None


def get_slow_logs(cluster_id, region):
    data = call_cli('polardb', 'describe-slow-logs', region,
                    **{'db-cluster-id': cluster_id,
                       'start-time': (datetime.now(timezone.utc) - timedelta(days=_INSPECT_DAYS)).strftime('%Y-%m-%dZ'),
                       'end-time': datetime.now(timezone.utc).strftime('%Y-%m-%dZ'),
                       'biz-region-id': region})
    return data


def get_max_connections_from_params(cluster_id, region):
    print('🔧 Instance parameters...', end=' ', flush=True)
    data = call_cli('polardb', 'describe-db-cluster-parameters', region,
                    **{'db-cluster-id': cluster_id})
    if not data:
        print('⚠️')
        return None
    params = data.get('RunningParameters', {}).get('Parameter', [])
    for p in params:
        if p.get('ParameterName') == 'max_connections':
            try:
                val = int(p.get('ParameterValue', 0))
                print(f'✅ (max_connections={val})')
                return val
            except (ValueError, TypeError):
                pass
    print('⚠️ Not found')
    return None


def get_alert_history(cluster_id, start_time, end_time):
    print('🔔 Alert history...', end='', flush=True)
    start_ms = int(datetime.strptime(start_time, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end_time, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp() * 1000)
    all_logs = []
    page = 1
    while True:
        result = call_cli('cms', 'describe-alert-log-list',
                          **{'start-time': str(start_ms), 'end-time': str(end_ms),
                             'send-status': '0',
                             'page-size': '100', 'page-number': str(page)})
        if not result:
            if page == 1:
                print(f' ⚠️ Query failed ({_last_cli_error})')
            break
        logs = result.get('AlertLogList', [])
        if isinstance(logs, dict):
            logs = logs.get('AlertLog', [])
        if not logs:
            break
        all_logs.extend(logs)
        if len(logs) < 100:
            break
        page += 1
    filtered = []
    for log in all_logs:
        product = log.get('Product', '').lower()
        namespace = log.get('Namespace', '').lower()
        if 'polardb' not in product and 'polardb' not in namespace:
            continue
        dims = {d['Key']: d['Value'] for d in log.get('Dimensions', [])}
        dim_cluster = dims.get('clusterId', '')
        inst_id = log.get('InstanceId', '')
        if cluster_id not in dim_cluster and cluster_id not in inst_id:
            continue
        alert_time = log.get('AlertTime', 0)
        level = log.get('Level', '')
        rule_name = log.get('RuleName', '')
        metric_name = log.get('MetricName', '')
        node_id = dims.get('nodeId', '')
        send_status = log.get('SendStatus', '')
        ext_info = {e['Name']: e['Value'] for e in log.get('ExtendedInfo', [])}
        send_desc = ext_info.get('sendStatusDescription', '')
        threshold = ''
        cur_value = ''
        try:
            msg = json.loads(log.get('Message', ''))
            esc = msg.get('escalation', {})
            threshold = esc.get('threshold', '')
            fetched = msg.get('fetched', {})
            if fetched:
                cur_value = f'{list(fetched.values())[0]:.1f}' if fetched else ''
        except (json.JSONDecodeError, AttributeError):
            pass
        status_text = send_desc or send_status
        filtered.append({
            'time': datetime.fromtimestamp(alert_time / 1000).strftime('%Y-%m-%d %H:%M:%S') if alert_time else '',
            'level': level,
            'rule_name': rule_name,
            'metric': metric_name,
            'node_id': node_id,
            'cur_value': cur_value,
            'threshold': threshold,
            'send_status': status_text,
        })
    filtered.sort(key=lambda x: x['time'], reverse=True)
    print(f' ✅ ({len(filtered)} entries)')
    return filtered


def get_alert_rules(cluster_id):
    print('📋 Alert rules...', end='', flush=True)
    all_rules = []
    page = 1
    while True:
        result = call_cli('cms', 'describe-metric-rule-list',
                          **{'namespace': 'acs_polardb', 'page': str(page), 'page-size': '100'})
        if not result:
            if page == 1:
                print(f' ⚠️ Query failed ({_last_cli_error})')
            break
        alarms = result.get('Alarms', {})
        rules = alarms.get('Alarm', []) if isinstance(alarms, dict) else []
        if not rules:
            break
        all_rules.extend(rules)
        total = int(result.get('Total', 0))
        if len(all_rules) >= total:
            break
        page += 1
    filtered = []
    for rule in all_rules:
        resources = rule.get('Resources', '[]')
        try:
            res_list = json.loads(resources) if isinstance(resources, str) else resources
        except (json.JSONDecodeError, TypeError):
            res_list = []
        is_all = any(r.get('resource') == '_ALL' for r in res_list if isinstance(r, dict))
        matches_cluster = cluster_id in resources
        if not is_all and not matches_cluster:
            continue
        esc = rule.get('Escalations', {})
        thresholds = {}
        for lvl in ('Critical', 'Warn', 'Info'):
            t = esc.get(lvl, {})
            if t and t.get('Threshold'):
                op = t.get('ComparisonOperator', '')
                op_symbol = '>=' if 'Greater' in op else '<=' if 'Less' in op else op
                thresholds[lvl] = f'{op_symbol} {t["Threshold"]}%'
        filtered.append({
            'rule_name': rule.get('RuleName', ''),
            'metric': rule.get('MetricName', ''),
            'state': rule.get('AlertState', ''),
            'enabled': rule.get('EnableState', False),
            'interval': rule.get('Interval', 60),
            'silence': rule.get('SilenceTime', 0),
            'thresholds': thresholds,
            'contact_groups': rule.get('ContactGroups', '').replace('云账号报警联系人', 'Default Alert Contacts'),
        })
    print(f' ✅ ({len(filtered)} entries)')
    return filtered


def get_auto_increment_usage(cluster_id):
    print('🔢 Auto-increment primary key...', end='', flush=True)
    result = call_cli('das', 'get-auto-increment-usage-statistic',
                      endpoint='das.cn-shanghai.aliyuncs.com',
                      **{'instance-id': cluster_id,
                         'real-time': 'false',
                         'ratio-filter': '0'})
    if not result:
        print(f' ⚠️ Failed ({_last_cli_error})')
        return None
    if result.get('Code') != 200:
        print(f' ⚠️ Failed (Code={result.get("Code")}, {result.get("Message", "")})')
        return None
    data = result.get('Data', {})
    items = data.get('AutoIncrementUsageList', data.get('Items', []))
    print(f' ✅ ({len(items)} tables)')
    return items


def _fetch_node_session(cluster_id, node_id=None):
    params = {'instance-id': cluster_id}
    if node_id:
        params['node-id'] = node_id
    result = call_cli('das', 'get-mysql-all-session-async',
                      endpoint='das.cn-shanghai.aliyuncs.com', **params)
    if not result:
        print(f' ⚠️({_last_cli_error})', end='', flush=True)
        return None
    if result.get('Code') != 200:
        print(f' ⚠️(Code={result.get("Code")})', end='', flush=True)
        return None
    rid = result.get('Data', {}).get('ResultId', '')
    if not rid:
        return None
    fetch_params = {'instance-id': cluster_id, 'result-id': rid}
    if node_id:
        fetch_params['node-id'] = node_id
    for _ in range(6):
        time.sleep(2)
        r = call_cli('das', 'get-mysql-all-session-async',
                      endpoint='das.cn-shanghai.aliyuncs.com', **fetch_params)
        if r and r.get('Code') == 200:
            d = r.get('Data', {})
            if d.get('Complete') or d.get('IsFinish'):
                return d.get('SessionData', {})
    return None


def get_session_info(cluster_id, nodes=None):
    print('🔗 Session info...', end='', flush=True)
    if not nodes:
        sd = _fetch_node_session(cluster_id)
        if sd:
            total = sd.get('TotalSessionCount', 0)
            active = sd.get('ActiveSessionCount', 0)
            print(f' ✅ (total {total} / active {active})')
            return {'nodes': {'primary': sd}}
        print(' ⚠️ Failed')
        return None
    all_nodes = {}
    for node in nodes:
        nid = node.get('DBNodeId', '')
        role_short = _node_role_short(node)
        label = f'{nid}({role_short})'
        print(f' {nid}..', end='', flush=True)
        sd = _fetch_node_session(cluster_id, nid)
        if sd:
            sd['_node_id'] = nid
            sd['_role'] = role_short
            all_nodes[label] = sd
    if all_nodes:
        total = sum(v.get('TotalSessionCount', 0) for v in all_nodes.values())
        active = sum(v.get('ActiveSessionCount', 0) for v in all_nodes.values())
        print(f' ✅ ({len(all_nodes)} nodes, total {total} / active {active})')
        return {'nodes': all_nodes}
    print(' ⚠️ Failed')
    return None


# ─── Utilities ────────────────────────────────────────────────────────────────

def format_bytes(size_bytes):
    if size_bytes is None:
        return 'N/A'
    try:
        size_bytes = float(size_bytes)
    except (ValueError, TypeError):
        return str(size_bytes)
    if size_bytes >= 1024 ** 4:
        return f'{size_bytes / (1024**4):.2f} TB'
    elif size_bytes >= 1024 ** 3:
        return f'{size_bytes / (1024**3):.2f} GB'
    elif size_bytes >= 1024 ** 2:
        return f'{size_bytes / (1024**2):.2f} MB'
    elif size_bytes >= 1024:
        return f'{size_bytes / 1024:.2f} KB'
    return f'{size_bytes:.0f} B'


def format_mb(mb_value):
    if mb_value >= 1024 * 1024:
        return f'{mb_value / (1024*1024):.2f} TB'
    elif mb_value >= 1024:
        return f'{mb_value / 1024:.2f} GB'
    return f'{mb_value:.2f} MB'


def status_icon(value, metric_type='default'):
    thresholds = {'space': (70, 85), 'memory': (90, 95), 'default': (60, 80)}
    low, high = thresholds.get(metric_type, thresholds['default'])
    if value > high:
        return '🔴'
    elif value > low:
        return '🟡'
    return '🟢'


def _html_escape(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _escape_preserve_links(text):
    import re as _re
    links = _re.findall(r'<a\s[^>]*>.*?</a>|<code>.*?</code>', text)
    placeholders = []
    for i, link in enumerate(links):
        ph = f'\x00LINK{i}\x00'
        placeholders.append((ph, link))
        text = text.replace(link, ph, 1)
    text = _html_escape(text)
    for ph, link in placeholders:
        text = text.replace(_html_escape(ph), link)
    return text


def _i18n(en, zh):
    return f'<span class="i18n-en">{en}</span><span class="i18n-zh">{zh}</span>'


# ─── Data Processing ─────────────────────────────────────────────────────────

def _node_role_short(node):
    role = node.get('DBNodeRole', node.get('role', ''))
    if node.get('ImciSwitch', '') == 'ON':
        return 'IMCI'
    if role in ('Writer', 'ReadWrite'):
        return 'RW'
    return 'RO'


def collect_report_data(cluster_id, region, cluster_info, version_info,
                        resource_usage, nodes, space_data, slow_logs,
                        auto_inc_data=None, param_max_conn=None, session_info=None,
                        alert_history=None, alert_rules=None, das_config=None, proxy_perf=None):
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
        'category': CATEGORY_MAP.get(cluster_info.get('Category', ''), cluster_info.get('Category', 'N/A')),
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
                    'type': 'Space fragmentation', 'db': db_name, 'table': table_name,
                    'detail': f'Fragmentation rate {pct}%, fragmentation {format_bytes(frag_size)}'
                })
            if index_size == 0 and data_size > 100 * 1024 * 1024:
                space['anomalies'].append({
                    'type': 'Large table without index', 'db': db_name, 'table': table_name,
                    'detail': f'Data {format_bytes(data_size)}, no index'
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
                level = 'Critical' if usage >= 0.95 else 'Warning'
                space['anomalies'].append({
                    'type': 'Auto-increment overflow', 'db': db_name, 'table': table_name,
                    'detail': f'{level}: usage {usage*100:.1f}% ({current_val:,}/{max_val:,})'
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
    data['alert_rules'] = alert_rules or []

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
        suffix = f' and {len(auto_inc_danger)-5} more tables' if len(auto_inc_danger) > 5 else ''
        alter_sqls = '; '.join(f'ALTER TABLE `{a["db"]}`.`{a["table"]}` MODIFY `{a["column"]}` BIGINT NOT NULL AUTO_INCREMENT' for a in auto_inc_danger[:5])
        suggestions.append(('danger', 0, f'⚠️ Auto-increment PK about to overflow: {items}{suffix}, failure to act will cause write failures. Recommended SQL (execute during off-peak hours): <code>{alter_sqls}</code>', f'⚠️ 自增主键即将溢出: {items}{suffix}，不处理将导致写入失败。建议 SQL（业务低峰期执行）: <code>{alter_sqls}</code>'))
    if auto_inc_warn:
        items = ', '.join(f'{a["db"]}.{a["table"]}({a["usage"]*100:.0f}%)' for a in auto_inc_warn[:5])
        suffix = f' and {len(auto_inc_warn)} more tables' if len(auto_inc_warn) > 5 else ''
        suggestions.append(('warn', 30, f'Auto-increment PK usage exceeds 50%: {items}{suffix}, recommend planning PK type change in advance', f'自增主键使用率超过 50%: {items}{suffix}，建议提前规划主键类型变更'))

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
                suggestions.append(('danger', 1, f'{total_abnormal} long-running uncommitted transactions found (longest {max_trx_dur}s), blocking other sessions and causing undo log growth, recommend immediately killing or contacting the application team to commit', f'发现 {total_abnormal} 个长时间未提交事务（最长 {max_trx_dur}s），阻塞其他会话并导致 undo log 增长，建议立即 kill 或联系业务方提交'))
            else:
                suggestions.append(('warn', 31, f'{total_abnormal} long-running uncommitted transactions found (longest {max_trx_dur}s), recommend checking for uncommitted transactions', f'发现 {total_abnormal} 个长时间未提交事务（最长 {max_trx_dur}s），建议检查未提交事务'))

    # ═══ Priority 2: Correlated resource issues ═══
    if resource_usage:
        c = res.get('cluster', {})

        # --- CPU correlation: peak + alerts + slow SQL ---
        cpu_peak = c.get('cpu_peak', 0)
        if cpu_peak > 80:
            _, peak_nid, peak_role, peak_time = _peak_node_info(node_ts, 'cpu', nodes_res)
            time_part = f'(peak {peak_time}' if peak_time else '('
            node_part = f', node {peak_nid}({peak_role})' if peak_nid else ''
            time_part += node_part

            parts_en = [f'CPU peak {cpu_peak:.1f}%{time_part})']
            parts_zh = [f'CPU 峰值 {cpu_peak:.1f}%{time_part})']

            if cpu_alerts:
                parts_en.append(f'triggered {len(cpu_alerts)} alerts')
                parts_zh.append(f'触发 {len(cpu_alerts)} 次告警')
                alert_covered = True
            if top_sql and data['slow_total'] > 0:
                sql_raw = top_sql["sql_text"]
                sql_brief = (sql_raw[:80] + '...') if len(sql_raw) > 80 else sql_raw
                sql_hash = top_sql.get("sql_hash", "")
                sql_link = f'<a href="#sql_{sql_hash}" title="Click to view full SQL">{sql_brief}</a>' if sql_hash else sql_brief
                parts_en.append(f'correlated with TOP1 slow SQL ({top_sql["db"]}): {sql_link} ({top_sql["count"]} executions, max duration {top_sql["max_time"]}s)')
                parts_zh.append(f'关联 TOP1 慢 SQL（{top_sql["db"]}）: {sql_link}（{top_sql["count"]} 次执行，最大耗时 {top_sql["max_time"]}s）')
                slow_covered = True

            if len(parts_en) > 1:
                text_en = ', '.join(parts_en) + ', recommend optimizing this SQL first to reduce CPU usage'
                text_zh = '，'.join(parts_zh) + '，建议优先优化该 SQL 以降低 CPU 使用率'
            else:
                text_en = parts_en[0] + ', recommend investigating high-cost SQL and consider upgrading specs or adding read-only nodes'
                text_zh = parts_zh[0] + '，建议排查高消耗 SQL，考虑升级规格或增加只读节点'

            suggestions.append(('danger', 2, text_en, text_zh))
            cpu_covered = True
        elif cpu_peak > 60:
            _, _, _, peak_time = _peak_node_info(node_ts, 'cpu', nodes_res)
            time_part = f'(peak {peak_time})' if peak_time else ''
            suggestions.append(('warn', 32, f'CPU peak {cpu_peak:.1f}%{time_part}, load is relatively high, recommend monitoring the trend', f'CPU 峰值 {cpu_peak:.1f}%{time_part}，负载偏高，建议持续关注趋势'))
            cpu_covered = True

        # Per-node CPU imbalance
        if not cpu_covered or cpu_peak <= 80:
            cpu_danger_nodes = []
            for nid, nd in nodes_res.items():
                if nd.get('cpu_peak', 0) > 80 and cpu_peak <= 80:
                    t = _peak_time_str(node_ts.get(nid, {}).get('cpu', []))
                    cpu_danger_nodes.append(f'{nid}({nd.get("role_short","RO")}) {nd["cpu_peak"]:.1f}%' + (f' @{t}' if t else ''))
            if cpu_danger_nodes:
                suggestions.append(('danger', 2, f'Node CPU peak exceeds 80%: {", ".join(cpu_danger_nodes)}, load imbalance, recommend checking read-write splitting routing policy', f'节点 CPU 峰值超过 80%: {", ".join(cpu_danger_nodes)}，负载不均衡，建议检查读写分离路由策略'))

        # --- Memory ---
        mem_peak = c.get('mem_peak', 0)
        if mem_peak > 95:
            _, _, _, peak_time = _peak_node_info(node_ts, 'memory', nodes_res)
            time_part = f'(peak {peak_time})' if peak_time else ''
            suggestions.append(('danger', 2, f'Memory peak {mem_peak:.1f}%{time_part}, OOM risk exists, recommend checking buffer pool config and memory-intensive queries', f'内存峰值 {mem_peak:.1f}%{time_part}，存在 OOM 风险，建议检查 buffer pool 配置和高内存查询'))
        elif mem_peak > 90:
            suggestions.append(('warn', 32, f'Memory peak {mem_peak:.1f}%, approaching limit, recommend checking for memory leaks or large result set queries', f'内存峰值 {mem_peak:.1f}%，接近上限，建议检查内存泄漏或大结果集查询'))
        mem_danger_nodes = []
        for nid, nd in nodes_res.items():
            if nd.get('mem_peak', 0) > 95 and mem_peak <= 95:
                mem_danger_nodes.append(f'{nid}({nd.get("role_short","RO")}) {nd["mem_peak"]:.1f}%')
        if mem_danger_nodes:
            suggestions.append(('danger', 2, f'Node memory peak exceeds 95%: {", ".join(mem_danger_nodes)}, OOM risk exists', f'节点内存峰值超过 95%: {", ".join(mem_danger_nodes)}，存在 OOM 风险'))

        # --- Disk ---
        disk_pct = c.get('disk_peak_pct', 0)
        if disk_pct > 85:
            suggestions.append(('danger', 2, f'Space usage {disk_pct:.1f}%, approaching capacity limit, recommend cleaning unused data or expanding storage ASAP', f'空间使用率 {disk_pct:.1f}%，接近容量上限，建议尽快清理无用数据或扩容'))
        elif disk_pct > 70:
            suggestions.append(('warn', 32, f'Space usage {disk_pct:.1f}%, recommend planning expansion in advance to prevent sudden writes from filling the disk', f'空间使用率 {disk_pct:.1f}%，建议提前规划扩容以防突发写入打满磁盘'))

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
            time_part = f', peak {t}' if t else ''
            # Correlate with high-scan-rows slow SQL
            high_scan_sql = next((s for s in slow_logs_list if s.get('avg_parse_rows', 0) > 100000), None)
            if high_scan_sql and not slow_covered:
                hs_raw = high_scan_sql["sql_text"]
                hs_brief = (hs_raw[:80] + '...') if len(hs_raw) > 80 else hs_raw
                hs_hash = high_scan_sql.get("sql_hash", "")
                hs_link = f'<a href="#sql_{hs_hash}" title="Click to view full SQL">{hs_brief}</a>' if hs_hash else hs_brief
                text_en = (f'IOPS usage reached bottleneck (node {nid}({rs}) {peak_val:.0f}%{time_part}), '
                           f'possibly caused by full table scan ({high_scan_sql["db"]}): {hs_link} (scanning {high_scan_sql["avg_parse_rows"]:,} rows), recommend adding indexes')
                text_zh = (f'IOPS 使用率达到瓶颈（节点 {nid}({rs}) {peak_val:.0f}%{time_part}），'
                           f'可能由全表扫描引起（{high_scan_sql["db"]}）: {hs_link}（扫描 {high_scan_sql["avg_parse_rows"]:,} 行），建议添加索引')
                slow_covered = True
            else:
                nodes_str = ', '.join(f'{n}({r}) {v:.0f}%' for n, r, v, _ in iops_danger_nodes)
                text_en = f'IOPS usage peak reached bottleneck: {nodes_str}{time_part}, recommend optimizing full-scan SQL or upgrading storage specs'
                text_zh = f'IOPS 使用率峰值达到瓶颈: {nodes_str}{time_part}，建议优化全表扫描 SQL 或升级存储规格'
            if iops_alerts:
                text_en += f' (triggered {len(iops_alerts)} alerts)'
                text_zh += f'（触发 {len(iops_alerts)} 次告警）'
                alert_covered = True
            suggestions.append(('danger', 2, text_en, text_zh))
            iops_covered = True

        if iops_warn_nodes:
            suggestions.append(('warn', 32, f'IOPS usage peak exceeds 60%: {", ".join(iops_warn_nodes)}, IO load is high', f'IOPS 使用率峰值超过 60%: {", ".join(iops_warn_nodes)}，IO 负载偏高'))
        if iops_avg_warn_nodes:
            suggestions.append(('warn', 32, f'IOPS usage average persistently high: {", ".join(iops_avg_warn_nodes)}, persistent IO pressure exists', f'IOPS 使用率均值持续偏高: {", ".join(iops_avg_warn_nodes)}，存在持续 IO 压力'))

        # --- Connections ---
        conn_pct = c.get('conn_peak_pct', 0)
        if conn_pct > 80:
            suggestions.append(('danger', 2, f'Connection usage peak {conn_pct:.1f}%, approaching limit, recommend checking connection pool config and investigating connection leaks', f'连接使用率峰值 {conn_pct:.1f}%，接近上限，建议检查连接池配置并排查连接泄漏'))
        elif conn_pct > 60:
            suggestions.append(('warn', 32, f'Connection usage peak {conn_pct:.1f}%, recommend optimizing max connection pool config', f'连接使用率峰值 {conn_pct:.1f}%，建议优化最大连接池配置'))
        conn_danger_nodes = []
        for nid, nd in nodes_res.items():
            if nd.get('conn_pct', 0) > 80 and conn_pct <= 80:
                conn_danger_nodes.append(f'{nid}({nd.get("role_short","RO")}) {nd["conn_pct"]:.1f}%')
        if conn_danger_nodes:
            suggestions.append(('danger', 2, f'Node connection usage exceeds 80%: {", ".join(conn_danger_nodes)}, recommend checking app-side connection pool or increasing max_connections', f'节点连接使用率超过 80%: {", ".join(conn_danger_nodes)}，建议检查应用端连接池或增大 max_connections'))

    # ═══ Slow logs (only if not already covered by correlation) ═══
    if not slow_covered:
        if data['slow_total'] > 10:
            detail_en = ''
            detail_zh = ''
            if top_sql:
                detail_en = f', TOP1: {top_sql["db"]}.{top_sql["sql_text"][:50]} ({top_sql["count"]} executions, max duration {top_sql["max_time"]}s)'
                detail_zh = f'，TOP1: {top_sql["db"]}.{top_sql["sql_text"][:50]}（{top_sql["count"]} 次执行，最大耗时 {top_sql["max_time"]}s）'
            suggestions.append(('warn', 33, f'Many slow logs ({data["slow_total"]} entries), recommend focusing on optimizing high-frequency slow SQL{detail_en}', f'慢日志较多（{data["slow_total"]} 条），建议重点优化高频慢 SQL{detail_zh}'))
        elif data['slow_total'] > 0:
            suggestions.append(('info', 40, f'{data["slow_total"]} slow queries found, recommend monitoring', f'发现 {data["slow_total"]} 条慢查询，建议持续关注'))

    # ═══ Space anomalies ═══
    anomalies = space['anomalies']
    if anomalies:
        no_idx = [a for a in anomalies if a['type'] == 'Large table without index']
        if no_idx:
            tables = ', '.join(f'{i["db"]}.{i["table"]}' for i in no_idx[:3])
            suffix = f' and {len(no_idx)} more tables' if len(no_idx) > 3 else ''
            suggestions.append(('warn', 33, f'Large table without index: {tables}{suffix}, recommend adding appropriate indexes to improve query performance', f'大表无索引: {tables}{suffix}，建议添加适当索引以提高查询性能'))
        frag = [a for a in anomalies if a['type'] == 'Space fragmentation']
        if frag:
            tables = ', '.join(f'{i["db"]}.{i["table"]}' for i in frag[:3])
            suffix = f' and {len(frag)} more tables' if len(frag) > 3 else ''
            suggestions.append(('warn', 33, f'Space fragmentation too high: {tables}{suffix}, recommend running OPTIMIZE TABLE to reclaim fragmentation', f'空间碎片率过高: {tables}{suffix}，建议执行 OPTIMIZE TABLE 回收碎片'))

    # ═══ Alert history (only if not already covered by correlation) ═══
    if not alert_covered and alerts:
        p3 = [a for a in alerts if a.get('level') == 'P3']
        uncovered_p1p2 = [a for a in p1p2_alerts if a not in cpu_alerts and a not in iops_alerts]
        if uncovered_p1p2:
            metrics = {}
            for a in uncovered_p1p2:
                key = a.get('rule_name') or a.get('metric', 'unknown')
                metrics[key] = metrics.get(key, 0) + 1
            detail = ', '.join(f'{k}({v} times)' for k, v in sorted(metrics.items(), key=lambda x: -x[1])[:3])
            suggestions.append(('danger', 2, f'{len(uncovered_p1p2)} high-priority (P1/P2) alerts triggered in last {_INSPECT_DAYS} days: {detail}, recommend investigating root cause', f'近 {_INSPECT_DAYS} 天触发 {len(uncovered_p1p2)} 次高优先级（P1/P2）告警: {detail}，建议排查根因'))
        elif p3:
            metrics = {}
            for a in p3:
                key = a.get('rule_name') or a.get('metric', 'unknown')
                metrics[key] = metrics.get(key, 0) + 1
            detail = ', '.join(f'{k}({v} times)' for k, v in sorted(metrics.items(), key=lambda x: -x[1])[:3])
            suggestions.append(('warn', 33, f'{len(p3)} alerts (P3) triggered in last {_INSPECT_DAYS} days: {detail}, recommend monitoring alert frequency', f'近 {_INSPECT_DAYS} 天触发 {len(p3)} 次告警（P3）: {detail}，建议关注告警频率'))

    # ═══ Info-level ═══
    if version_info and not bi['is_latest']:
        suggestions.append(('info', 40, f'Kernel version upgradable: current {bi["revision_version"]} → latest {bi["latest_version"]}, brief service interruption during upgrade', f'内核版本可升级: 当前 {bi["revision_version"]} → 最新 {bi["latest_version"]}，升级期间有短暂服务中断'))
    if bi.get('is_essd') and not bi.get('storage_auto_scale'):
        suggestions.append(('warn', 33, f'ESSD storage auto-expansion not enabled, recommend enabling to prevent disk from being locked', f'ESSD 存储自动扩容未开启，建议开启以防磁盘被锁'))

    # Sort by priority (lower number = more urgent)
    data['suggestions'] = [(level, _, text_en, text_zh) for level, _, text_en, text_zh in sorted(suggestions, key=lambda x: x[1])]
    return data


# ─── Text Renderer ────────────────────────────────────────────────────────────

def render_text(data):
    lines = []
    p = lines.append
    bi = data['basic_info']

    p('')
    p('┌' + '─' * 78 + '┐')
    p('│' + ' PolarDB MySQL Instance Health Inspection Report'.center(68) + '│')
    p('└' + '─' * 78 + '┘')
    p(f'  Inspection Time: {data["inspect_time"]}')
    p(f'  Instance ID:  {data["cluster_id"]}')
    p(f'  Region:   {data["region"]}')
    if _CLI_PROFILE:
        p(f'  Profile:  {_CLI_PROFILE}')

    # 1. Basic Information
    p('')
    p('═' * 80)
    p(' 1. Instance Basic Information')
    p('═' * 80)
    p('')
    p(f'  ┌{"─"*30}┬{"─"*46}┐')
    p(f'  │ {"Item":<27} │ {"Value":<43} │')
    p(f'  ├{"─"*30}┼{"─"*46}┤')
    p(f'  │ {"Database Type":<26} │ {bi["db_type"]:<44} │')
    p(f'  │ {"Major Version":<27} │ {bi["db_type"]+" "+bi["db_version"]:<44} │')
    p(f'  │ {"Kernel Minor Version":<26} │ {bi["revision_version"]:<44} │')
    p(f'  │ {"Latest Available Version":<25} │ {bi["latest_version"]:<44} │')
    vs = "✅ Latest" if bi['is_latest'] else "⬆️  Upgradable"
    p(f'  │ {"Version Status":<26} │ {vs:<43} │')
    p(f'  │ {"Proxy Version":<26} │ {bi["proxy_version"]:<44} │')
    p(f'  │ {"Cluster Status":<27} │ {bi["status"]:<44} │')
    p(f'  │ {"Storage Type":<27} │ {bi["storage_type"]:<44} │')
    p(f'  │ {"Cluster Category":<27} │ {bi["category"]:<44} │')
    p(f'  │ {"Storage Used":<27} │ {bi["storage_used_str"]:<44} │')
    p(f'  │ {"Storage Capacity":<27} │ {(bi["storage_space_str"] or bi["storage_max_str"]):<44} │')
    if bi.get('is_psl'):
        auto_expand_txt = 'Auto-expand (PSL storage)'
    elif bi.get('is_essd'):
        auto_expand_txt = 'Enabled (upper limit ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + ')' if bi.get("storage_auto_scale") else 'Disabled'
    else:
        auto_expand_txt = 'N/A'
    p(f'  │ {"Auto Expansion":<27} │ {auto_expand_txt:<44} │')
    p(f'  └{"─"*30}┴{"─"*46}┘')

    nl = data['nodes']
    p('')
    p(f'  Node Details ({len(nl)} nodes):')
    p(f'  ┌{"─"*26}┬{"─"*8}┬{"─"*10}┬{"─"*26}┬{"─"*6}┬{"─"*10}┬{"─"*10}┬{"─"*10}┐')
    p(f'  │ {"Node ID":<24} │ {"Role":<6} │ {"Status":<8} │ {"Spec":<24} │ {"CPU":<4} │ {"Memory":<8} │ {"Max Conn":<8} │ {"Max IOPS":<8} │')
    p(f'  ├{"─"*26}┼{"─"*8}┼{"─"*10}┼{"─"*26}┼{"─"*6}┼{"─"*10}┼{"─"*10}┼{"─"*10}┤')
    for nd in nl:
        p(f'  │ {nd["id"]:<24} │ {nd["role"]:<6} │ {nd["status"]:<8} │ {nd["class"]:<24} │ {str(nd["cpu"])+" cores":<4} │ {nd["mem"]:<8} │ {str(nd["max_conn"]):<8} │ {str(nd["max_iops"]):<8} │')
    p(f'  ├{"─"*26}┴{"─"*8}┴{"─"*10}┴{"─"*26}┴{"─"*6}┼{"─"*10}┼{"─"*10}┼{"─"*10}┤')
    p(f'  │ {"Total":<76} │ {str(data["total_max_conn"]):<8} │ {str(data["total_max_iops"]):<8} │ {"":8} │')
    p(f'  └{"─"*78}┴{"─"*10}┴{"─"*10}┴{"─"*10}┘')

    # 2. Current Sessions
    p('')
    p('═' * 80)
    p(' 2. Current Sessions')
    p('═' * 80)
    si = data.get('session_info')
    if si and si.get('nodes'):
        for node_label, sd in si['nodes'].items():
            p('')
            p(f'  ┌─ {node_label}')
            p(f'  │  Total: {sd.get("TotalSessionCount", 0)}    Active: {sd.get("ActiveSessionCount", 0)}    Max Active Time: {sd.get("MaxActiveTime", 0)}s')
            session_list = sd.get('SessionList', [])
            active_s = [s for s in session_list if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump')]
            abnormal_s = [s for s in session_list if s.get('TrxDuration', 0) > 10]
            binlog_s = [s for s in session_list if s.get('Command', '').startswith('Binlog Dump')]
            if active_s:
                p(f'  │')
                p(f'  │  [Active Sessions ({len(active_s)})]')
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
                p(f'  │  [Abnormal Sessions (uncommitted transactions >10s)]')
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
                p(f'  │  ⚠️ Binlog Dump Sessions ({len(binlog_s)}) — Many downstream Binlog consumers, may cause high IOPS')
            user_stats = sd.get('UserStats', [])
            if user_stats:
                p(f'  │')
                p(f'  │  [By User]')
                p(f'  │  {"User":<20}{"Total":<10}{"Active":<10}')
                p(f'  │  {"─"*20}{"─"*10}{"─"*10}')
                for u in user_stats:
                    p(f'  │  {u.get("Key",""):<20}{u.get("TotalCount",0):<10}{u.get("ActiveCount",0):<10}')
            if not active_s and not abnormal_s and len(binlog_s) <= 10:
                p(f'  │  No active or abnormal sessions currently')
            p(f'  └────────────────────────────────────────────────────────────')
    else:
        p('\n  ⚠️ Failed to retrieve session info')

    # 3. Resource Usage
    p('')
    p('═' * 80)
    p(f' 3. Resource Usage (Last {_INSPECT_DAYS} Days)')
    p('═' * 80)
    res = data.get('resource', {})
    if res.get('cluster'):
        c = res['cluster']
        tmc = data['total_max_conn']
        p('')
        p('  [Cluster Overview]')
        p(f'  ┌{"─"*16}┬{"─"*22}┬{"─"*22}┬{"─"*8}┐')
        p(f'  │ {"Metric":<13} │ {"Average":<19} │ {"Peak":<19} │ {"Status":<5} │')
        p(f'  ├{"─"*16}┼{"─"*22}┼{"─"*22}┼{"─"*8}┤')
        cpu_a, cpu_p = f'{c["cpu_avg"]:.2f}%', f'{c["cpu_peak"]:.2f}%'
        mem_a, mem_p = f'{c["mem_avg"]:.2f}%', f'{c["mem_peak"]:.2f}%'
        dsk_a = f'{c["disk_avg_pct"]:.2f}% ({format_mb(c["disk_avg_mb"])})'
        dsk_p = f'{c["disk_peak_pct"]:.2f}% ({format_mb(c["disk_peak_mb"])})'
        io_a, io_p = f'{c["io_avg"]:.0f} KB/s', f'{c["io_peak"]:.0f} KB/s'
        cn_a = f'{c["conn_avg"]:.0f}/{tmc} ({c["conn_avg_pct"]:.1f}%)'
        cn_p = f'{c["conn_peak"]:.0f}/{tmc} ({c["conn_peak_pct"]:.1f}%)'
        p(f'  │ {"CPU":<14} │ {cpu_a:<20} │ {cpu_p:<20} │ {status_icon(c["cpu_peak"]):<6} │')
        p(f'  │ {"Memory":<13} │ {mem_a:<20} │ {mem_p:<20} │ {status_icon(c["mem_peak"], "memory"):<6} │')
        p(f'  │ {"Space":<13} │ {dsk_a:<20} │ {dsk_p:<20} │ {status_icon(c["disk_peak_pct"], "space"):<6} │')
        p(f'  │ {"IO Throughput":<12} │ {io_a:<20} │ {io_p:<20} │ {"🔵":<6} │')
        p(f'  │ {"Connections":<13} │ {cn_a:<20} │ {cn_p:<20} │ {status_icon(c["conn_peak_pct"]):<6} │')
        p(f'  └{"─"*16}┴{"─"*22}┴{"─"*22}┴{"─"*8}┘')

        p('')
        p('  [Per-Node Details]')
        for nid, nd in res.get('nodes', {}).items():
            p('')
            p(f'  ▸ {nid} ({nd["role"]})')
            p(f'    CPU:    Avg {nd["cpu_avg"]:.2f}%  Peak {nd["cpu_peak"]:.2f}%  {status_icon(nd["cpu_peak"])}')
            p(f'    Memory: Avg {nd["mem_avg"]:.2f}%  Peak {nd["mem_peak"]:.2f}%  {status_icon(nd["mem_peak"], "memory")}')
            p(f'    Conn:   Avg {nd["conn_avg"]:.0f}  Peak {nd["conn_peak"]:.0f}  Usage {nd["conn_pct"]:.1f}% (upper limit {nd["max_conn"]})  {status_icon(nd["conn_pct"])}')
            p(f'    Active Conn: Avg {nd["active_avg"]:.0f}  Peak {nd["active_peak"]:.0f}')
            if nd.get('iops_peak', 0) > 0:
                p(f'    IOPS:   Avg {nd["iops_avg"]:.0f}  Peak {nd["iops_peak"]:.0f}')
    else:
        p('\n  ⚠️ Failed to retrieve resource usage data')

    # 4. Space Inspection
    p('')
    p('═' * 80)
    p(' 4. Space Inspection')
    p('═' * 80)
    space = data.get('space', {})
    p('')
    p('  4.1 Table Space TOP20')
    p('')
    tl = space.get('table_list', [])
    if tl:
        p(f'  {"#":<4}{"Database":<20}{"Table":<28}{"Total Space":<12}{"Data":<12}{"Index":<12}{"Rows":<14}')
        p(f'  {"─"*4}{"─"*20}{"─"*28}{"─"*12}{"─"*12}{"─"*12}{"─"*14}')
        for i, t in enumerate(tl, 1):
            rows_s = f'{t["rows"]:,}' if t['rows'] else '0'
            p(f'  {i:<4}{t["db"]:<20}{t["table"]:<28}{t["total_str"]:<12}{t["data_str"]:<12}{t["index_str"]:<12}{rows_s:<14}')
        if space.get('total_used'):
            p(f'\n  Total Used Space: {format_bytes(space["total_used"])}')
        di = space.get('daily_inc', 0)
        if di:
            p(f'  Daily avg growth: {"+" if di > 0 else "-"}{format_bytes(abs(di))}{" (space is shrinking)" if di < 0 else ""}')
    else:
        p('  ⚠️ Space analysis returned no table statistics')

    p('')
    p('  4.2 Space Change Trend')
    p('')
    disk_ts = res.get('cluster_ts', {}).get('disk', [])
    if disk_ts and len(disk_ts) >= 2:
        first_mb, last_mb = disk_ts[0][1], disk_ts[-1][1]
        days = (disk_ts[-1][0] - disk_ts[0][0]) / (86400 * 1000) or 1
        daily = (last_mb - first_mb) / days
        p(f'  Start: {format_mb(first_mb)}  →  Current: {format_mb(last_mb)}')
        p(f'  Daily avg {"growth" if daily >= 0 else "decrease"}: {"+" if daily >= 0 else "-"}{format_mb(abs(daily))}')
    else:
        p('  ⚠️ No disk trend data')

    p('')
    p('  4.3 Anomaly List')
    p('')
    anom = space.get('anomalies', [])
    if anom:
        p(f'  {"Type":<12}{"Database":<20}{"Table":<28}{"Details"}')
        p(f'  {"─"*12}{"─"*20}{"─"*28}{"─"*30}')
        for a in anom:
            p(f'  {a["type"]:<12}{a["db"]:<20}{a["table"]:<28}{a["detail"]}')
    else:
        p('  ✅ No anomalies found')

    # 5. Slow Logs
    p('')
    p('═' * 80)
    p(f' 5. Slow Log Statistics (Last {_INSPECT_DAYS} Days)')
    p('═' * 80)
    sl = data.get('slow_logs', [])
    if sl:
        p('')
        p(f'  {"#":<4}{"Database":<14}{"SQLHASH":<36}{"Count":<8}{"Total(s)":<11}{"Max(s)":<9}{"Avg Rows Scanned":<14}{"Avg Rows Returned":<14}{"SQL Summary"}')
        p(f'  {"─"*4}{"─"*14}{"─"*36}{"─"*8}{"─"*11}{"─"*9}{"─"*12}{"─"*12}{"─"*40}')
        for i, s in enumerate(sl, 1):
            sql = s['sql_text'][:48] + ('...' if len(s['sql_text']) > 48 else '')
            p(f'  {i:<4}{s["db"]:<14}{s.get("sql_hash","")[:34]:<36}{s["count"]:<8}{s["total_time"]:<11}{s["max_time"]:<9}{s.get("avg_parse_rows",0):<14}{s.get("avg_return_rows",0):<14}{sql}')
        p(f'\n  Total {data["slow_total"]} slow query entries')
    else:
        p(f'\n  ✅ No slow log records in last {_INSPECT_DAYS} days')

    # 6. Alert History
    p('')
    p('═' * 80)
    p(f' 6. Alert History (Last {_INSPECT_DAYS} Days)')
    p('═' * 80)
    alerts = data.get('alert_history', [])
    if alerts:
        p('')
        p(f'  {"#":<4}{"Time":<22}{"Level":<6}{"Rule":<12}{"Metric":<28}{"Node":<26}{"Current Value":<10}{"Threshold":<8}{"Notification Status"}')
        p(f'  {"─"*4}{"─"*22}{"─"*6}{"─"*12}{"─"*28}{"─"*26}{"─"*10}{"─"*8}{"─"*12}')
        for i, a in enumerate(alerts, 1):
            p(f'  {i:<4}{a["time"]:<22}{a["level"]:<6}{a.get("rule_name",""):<12}{a.get("metric","")[:26]:<28}{a.get("node_id",""):<26}{a.get("cur_value",""):<10}{a.get("threshold",""):<8}{a.get("send_status","")}')
        p(f'\n  Total {len(alerts)} alert records')
    else:
        p(f'\n  ✅ No alert records in last {_INSPECT_DAYS} days')

    # 7. Conclusions
    p('')
    p('═' * 80)
    p(' 7. Inspection Conclusions & Recommendations')
    p('═' * 80)
    p('')
    sug = data.get('suggestions', [])
    if not sug:
        p('  ✅ No significant issues found, instance is running normally.')
    else:
        danger_items = [text_en for level, _, text_en, text_zh in sug if level == 'danger']
        warn_items = [text_en for level, _, text_en, text_zh in sug if level == 'warn']
        info_items = [text_en for level, _, text_en, text_zh in sug if level == 'info']
        for label, items in [('🔴 High Risk', danger_items), ('🟡 Medium Risk', warn_items), ('🔵 Low Risk', info_items)]:
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
    p('│' + ' Inspection Complete'.center(72) + '│')
    p('└' + '─' * 78 + '┘')
    return '\n'.join(lines)


# ─── Markdown Renderer ────────────────────────────────────────────────────────

def render_markdown(data):
    lines = []
    p = lines.append
    bi = data['basic_info']

    p('# PolarDB MySQL Instance Health Inspection Report')
    p('')
    p(f'- **Inspection Time**: {data["inspect_time"]}')
    p(f'- **Instance ID**: {data["cluster_id"]}')
    p(f'- **Region**: {data["region"]}')

    p('')
    p('## 1. Instance Basic Information')
    p('')
    p('| Item | Value |')
    p('|------|------|')
    p(f'| Database Type | {bi["db_type"]} |')
    p(f'| Major Version | {bi["db_type"]} {bi["db_version"]} |')
    p(f'| Kernel Minor Version | {bi["revision_version"]} |')
    p(f'| Latest Available Version | {bi["latest_version"]} |')
    vs = "✅ Latest" if bi['is_latest'] else "⬆️ Upgradable"
    p(f'| Version Status | {vs} |')
    p(f'| Proxy Version | {bi["proxy_version"]} |')
    p(f'| Cluster Status | {bi["status"]} |')
    p(f'| Storage Type | {bi["storage_type"]} |')
    p(f'| Cluster Category | {bi["category"]} |')
    p(f'| Storage Used | {bi["storage_used_str"]} |')
    p(f'| Storage Capacity | {bi["storage_space_str"] or bi["storage_max_str"]} |')
    if bi.get('is_psl'):
        auto_expand_txt = 'Auto-expand (PSL storage)'
    elif bi.get('is_essd'):
        auto_expand_txt = 'Enabled (upper limit ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + ')' if bi.get("storage_auto_scale") else 'Disabled'
    else:
        auto_expand_txt = 'N/A'
    p(f'| Auto Expansion | {auto_expand_txt} |')

    p('')
    p(f'### Node Details ({len(data["nodes"])} nodes)')
    p('')
    p('| Node ID | Role | Status | Spec | CPU | Memory | Max Connections | Max IOPS |')
    p('|--------|------|------|------|-----|------|----------|----------|')
    for nd in data['nodes']:
        p(f'| {nd["id"]} | {nd["role"]} | {nd["status"]} | {nd["class"]} | {nd["cpu"]} cores | {nd["mem"]} | {nd["max_conn"]} | {nd["max_iops"]} |')
    p(f'| **Total** | | | | | | **{data["total_max_conn"]}** | **{data["total_max_iops"]}** |')

    p('')
    p('## 2. Current Sessions')
    si = data.get('session_info')
    if si and si.get('nodes'):
        for node_label, sd in si['nodes'].items():
            p('')
            p(f'### {node_label}')
            p('')
            p(f'- **Total Connections**: {sd.get("TotalSessionCount", 0)}')
            p(f'- **Active Sessions**: {sd.get("ActiveSessionCount", 0)}')
            p(f'- **Max Active Time**: {sd.get("MaxActiveTime", 0)}s')
            sl = sd.get('SessionList', [])
            active_s = [s for s in sl if s.get('Command', '') != 'Sleep' and not s.get('Command', '').startswith('Binlog Dump')]
            abnormal_s = [s for s in sl if s.get('TrxDuration', 0) > 10]
            binlog_s = [s for s in sl if s.get('Command', '').startswith('Binlog Dump')]
            if active_s:
                p('')
                p(f'#### Active Sessions ({len(active_s)})')
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
                p(f'#### Abnormal Sessions (uncommitted transactions >10s)')
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
                p(f'> ⚠️ Binlog Dump Sessions ({len(binlog_s)}) — Many downstream Binlog consumers, may cause high IOPS')
            us = sd.get('UserStats', [])
            if us:
                p('')
                p(f'#### By User')
                p('')
                p('| User | Total | Active |')
                p('|------|--------|------|')
                for u in us:
                    p(f'| {u.get("Key","")} | {u.get("TotalCount",0)} | {u.get("ActiveCount",0)} |')
            if not active_s and not abnormal_s and len(binlog_s) <= 10:
                p('')
                p('> No active or abnormal sessions currently')
    else:
        p('')
        p('> ⚠️ Failed to retrieve session info')

    p('')
    p(f'## 3. Resource Usage (Last {_INSPECT_DAYS} Days)')
    res = data.get('resource', {})
    if res.get('cluster'):
        c = res['cluster']
        tmc = data['total_max_conn']
        p('')
        p('### Cluster Overview')
        p('')
        p('| Metric | Average | Peak | Status |')
        p('|------|--------|------|------|')
        p(f'| CPU | {c["cpu_avg"]:.2f}% | {c["cpu_peak"]:.2f}% | {status_icon(c["cpu_peak"])} |')
        p(f'| Memory | {c["mem_avg"]:.2f}% | {c["mem_peak"]:.2f}% | {status_icon(c["mem_peak"], "memory")} |')
        p(f'| Space | {c["disk_avg_pct"]:.2f}% ({format_mb(c["disk_avg_mb"])}) | {c["disk_peak_pct"]:.2f}% ({format_mb(c["disk_peak_mb"])}) | {status_icon(c["disk_peak_pct"], "space")} |')
        p(f'| IO Throughput | {c["io_avg"]:.0f} KB/s | {c["io_peak"]:.0f} KB/s | 🔵 |')
        p(f'| Connections | {c["conn_avg"]:.0f}/{tmc} ({c["conn_avg_pct"]:.1f}%) | {c["conn_peak"]:.0f}/{tmc} ({c["conn_peak_pct"]:.1f}%) | {status_icon(c["conn_peak_pct"])} |')

        p('')
        p('### Per-Node Details')
        for nid, nd in res.get('nodes', {}).items():
            icons = [status_icon(nd['cpu_peak']), status_icon(nd['mem_peak'], 'memory'), status_icon(nd['conn_pct'])]
            worst = '🔴' if '🔴' in icons else ('🟡' if '🟡' in icons else '🟢')
            p('')
            p(f'#### {worst} {nid} ({nd["role"]})')
            p('')
            p('| Metric | Average | Peak | Status |')
            p('|------|--------|------|------|')
            p(f'| CPU | {nd["cpu_avg"]:.2f}% | {nd["cpu_peak"]:.2f}% | {status_icon(nd["cpu_peak"])} |')
            p(f'| Memory | {nd["mem_avg"]:.2f}% | {nd["mem_peak"]:.2f}% | {status_icon(nd["mem_peak"], "memory")} |')
            p(f'| Connections | {nd["conn_avg"]:.0f} | {nd["conn_peak"]:.0f} ({nd["conn_pct"]:.1f}%) | {status_icon(nd["conn_pct"])} |')
            p(f'| Active Connections | {nd["active_avg"]:.0f} | {nd["active_peak"]:.0f} | |')
            if nd.get('iops_peak', 0) > 0:
                p(f'| IOPS | {nd["iops_avg"]:.0f} | {nd["iops_peak"]:.0f} | |')
    else:
        p('')
        p('> ⚠️ Failed to retrieve resource usage data')

    p('')
    p('## 4. Space Inspection')
    p('')
    p('### 4.1 Table Space TOP20')
    tl = data['space'].get('table_list', [])
    if tl:
        p('')
        p('| # | Database | Table | Total Space | Data | Index | Rows |')
        p('|---|--------|------|--------|------|------|------|')
        for i, t in enumerate(tl, 1):
            rs = f'{t["rows"]:,}' if t['rows'] else '0'
            p(f'| {i} | {t["db"]} | {t["table"]} | {t["total_str"]} | {t["data_str"]} | {t["index_str"]} | {rs} |')
        if data['space'].get('total_used'):
            p(f'\nTotal Used Space: {format_bytes(data["space"]["total_used"])}')
    else:
        p('')
        p('> ⚠️ Space analysis returned no table statistics')

    p('')
    p('### 4.2 Space Change Trend')
    disk_ts = res.get('cluster_ts', {}).get('disk', [])
    if disk_ts and len(disk_ts) >= 2:
        first_mb, last_mb = disk_ts[0][1], disk_ts[-1][1]
        days = (disk_ts[-1][0] - disk_ts[0][0]) / (86400 * 1000) or 1
        daily = (last_mb - first_mb) / days
        p('')
        p(f'- Start: {format_mb(first_mb)} → Current: {format_mb(last_mb)}')
        p(f'- Daily avg {"growth" if daily >= 0 else "decrease"}: {"+" if daily >= 0 else "-"}{format_mb(abs(daily))}')
    else:
        p('')
        p('> No disk trend data')

    p('')
    p('### 4.3 Anomaly List')
    anom = data['space'].get('anomalies', [])
    if anom:
        p('')
        p('| Type | Database | Table | Details |')
        p('|------|--------|------|------|')
        for a in anom:
            p(f'| {a["type"]} | {a["db"]} | {a["table"]} | {a["detail"]} |')
    else:
        p('')
        p('✅ No anomalies found')

    p('')
    p(f'## 5. Slow Log Statistics (Last {_INSPECT_DAYS} Days)')
    sl = data.get('slow_logs', [])
    if sl:
        p('')
        p('| # | Database | SQLHASH | Count | Total Duration(s) | Max(s) | Avg Rows Scanned | Avg Rows Returned | SQL Summary |')
        p('|---|--------|---------|------|-----------|---------|----------|----------|----------|')
        for i, s in enumerate(sl, 1):
            sql = s['sql_text'][:48].replace('|', '\\|')
            if len(s['sql_text']) > 48:
                sql += '...'
            p(f'| {i} | {s["db"]} | `{s.get("sql_hash","")}` | {s["count"]} | {s["total_time"]} | {s["max_time"]} | {s.get("avg_parse_rows",0):,} | {s.get("avg_return_rows",0):,} | {sql} |')
        p(f'\nTotal {data["slow_total"]} slow query entries')
    else:
        p('')
        p(f'✅ No slow log records in last {_INSPECT_DAYS} days')

    p('')
    p(f'## 6. Alert History (Last {_INSPECT_DAYS} Days)')
    alerts = data.get('alert_history', [])
    if alerts:
        p('')
        p('| # | Time | Level | Rule | Metric | Node | Current Value | Threshold | Notification Status |')
        p('|---|------|------|------|------|------|--------|------|----------|')
        for i, a in enumerate(alerts, 1):
            p(f'| {i} | {a["time"]} | {a["level"]} | {a.get("rule_name","")} | {a.get("metric","")} | {a.get("node_id","")} | {a.get("cur_value","")} | {a.get("threshold","")} | {a.get("send_status","")} |')
        p(f'\nTotal {len(alerts)} alert records')
    else:
        p('')
        p(f'✅ No alert records in last {_INSPECT_DAYS} days')

    p('')
    p('## 7. Inspection Conclusions & Recommendations')
    p('')
    sug = data.get('suggestions', [])
    if not sug:
        p('✅ No significant issues found, instance is running normally.')
    else:
        danger_items = [text_en for level, _, text_en, text_zh in sug if level == 'danger']
        warn_items = [text_en for level, _, text_en, text_zh in sug if level == 'warn']
        info_items = [text_en for level, _, text_en, text_zh in sug if level == 'info']
        for label, items in [('🔴 High Risk', danger_items), ('🟡 Medium Risk', warn_items), ('🔵 Low Risk', info_items)]:
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


# ─── HTML Renderer ────────────────────────────────────────────────────────────

def render_html(data):
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

    vb = _i18n('⬆️ Upgradable', '⬆️ 可升级') if not bi['is_latest'] else _i18n('✅ Up to date', '✅ 已是最新')

    node_rows = ''
    for nd in nodes:
        node_rows += f'<tr><td>{nd["id"]}</td><td>{_badge(nd)}</td><td>{nd["status"]}</td><td>{nd["class"]}</td><td>{nd["cpu"]} {_i18n("cores", "核")}</td><td>{nd["mem"]}</td><td>{nd["max_conn"]}</td><td>{nd["max_iops"]}</td></tr>\n'

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
            summary_parts.append(f'<span class="suggestion danger">{_i18n(f"🔴 {total_abnormal} abnormal sessions found (uncommitted long transactions), longest transaction duration {max_trx_dur}s, please investigate promptly", f"🔴 发现 {total_abnormal} 个异常会话（未提交长事务），最长事务持续 {max_trx_dur}s，请及时排查")}</span>')
        if total_binlog > 10:
            summary_parts.append(f'<span class="suggestion warn">{_i18n(f"🟡 Many Binlog Dump connections ({total_binlog}), may cause high IOPS", f"🟡 Binlog Dump 连接数较多（{total_binlog}），可能导致 IOPS 较高")}</span>')
        if not summary_parts:
            summary_parts.append(f'<span class="suggestion ok">{_i18n(f"🟢 Session status normal, {total_all} connections, {total_active} active", f"🟢 会话状态正常，{total_all} 个连接，{total_active} 个活跃")}</span>')
        session_html += '<div style="margin-bottom:1rem;">' + '<br>'.join(summary_parts) + '</div>'

        node_labels = list(si['nodes'].keys())
        default_idx = 0
        for i, lbl in enumerate(node_labels):
            role = si['nodes'][lbl].get('_role', '')
            if role in ('Writer', 'ReadWrite'):
                default_idx = i
                break

        options_html = ''.join(f'<option value="sess_node_{i}"{" selected" if i == default_idx else ""}>{_html_escape(lbl)}</option>' for i, lbl in enumerate(node_labels))
        session_html += f'<div style="margin-bottom:1rem;"><label style="font-weight:600;margin-right:0.5rem;">{_i18n("Select Node:", "选择节点:")}</label><select id="sessNodeSelect" onchange="(function(){{var sel=document.getElementById(\'sessNodeSelect\').value;document.querySelectorAll(\'.sess-node-panel\').forEach(function(el){{el.style.display=el.id===sel?\'block\':\'none\';}});}})()" style="padding:4px 12px;border:1px solid #d0d5dd;border-radius:6px;font-size:14px;">{options_html}</select></div>'

        for idx, (node_label, sd) in enumerate(si['nodes'].items()):
            display = 'block' if idx == default_idx else 'none'
            total_sess = sd.get('TotalSessionCount', 0)
            active_sess = sd.get('ActiveSessionCount', 0)
            max_time = sd.get('MaxActiveTime', 0)
            node_html = f'<p><strong>{_i18n("Total Sessions", "总会话数")}</strong>: {total_sess} &nbsp;&nbsp; <strong>{_i18n("Active Sessions", "活跃会话")}</strong>: {active_sess} &nbsp;&nbsp; <strong>{_i18n("Max Active Time", "最长活跃时间")}</strong>: {max_time}s</p>'

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
                node_html += f'<h4>{_i18n(f"Active Sessions ({len(active_s)})", f"活跃会话（{len(active_s)}）")}</h4><div class="table-scroll"><table><tr><th>ID</th><th>User</th><th>Host</th><th>DB</th><th>Command</th><th>{_i18n("Time(s)", "时间(s)")}</th><th>{_i18n("TrxDuration", "事务时长")}</th><th>{_i18n("State", "状态")}</th><th>SQL</th></tr>{rows}</table></div>'

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
                node_html += f'<h4>{_i18n("Abnormal Sessions (uncommitted transactions &gt;10s)", "异常会话（未提交事务 &gt;10s）")}</h4><div class="table-scroll"><table><tr><th>ID</th><th>User</th><th>Host</th><th>DB</th><th>Command</th><th>{_i18n("Time(s)", "时间(s)")}</th><th>{_i18n("TrxDuration", "事务时长")}</th><th>{_i18n("State", "状态")}</th><th>SQL</th></tr>{rows}</table></div>'

            # 3. Binlog Dump
            if len(binlog_s) > 10:
                rows = ''
                for s in binlog_s[:20]:
                    rows += f'<tr><td>{s.get("SessionId","")}</td><td>{_html_escape(s.get("User",""))}</td><td>{s.get("Command","")}</td><td>{s.get("Time",0)}</td></tr>'
                node_html += f'<h4>Binlog Dump Sessions ({len(binlog_s)})</h4><p class="suggestion warn">{_i18n(f"⚠️ Many downstream Binlog consumers ({len(binlog_s)} connections), may cause high IOPS", f"⚠️ 下游 Binlog 消费者较多（{len(binlog_s)} 个连接），可能导致 IOPS 较高")}</p><div class="table-scroll"><table><tr><th>ID</th><th>User</th><th>Command</th><th>{_i18n("Time(s)", "时间(s)")}</th></tr>{rows}</table></div>'

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
                    db = s.get('DbName', '') or '(none)'
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
                grid_parts.append(f'<div><h4>{_i18n("By User", "按用户")}</h4><table><tr><th>User</th><th>{_i18n("Total", "总计")}</th><th>{_i18n("Active", "活跃")}</th></tr>{rows}</table></div>')
            client_stats = sd.get('ClientStats', [])
            if client_stats:
                rows = ''
                for c in client_stats:
                    ul = c.get('UserList', '')
                    if isinstance(ul, list):
                        ul = ', '.join(str(u) for u in ul)
                    rows += f'<tr><td>{_html_escape(c.get("Key",""))}</td><td>{c.get("TotalCount",0)}</td><td>{c.get("ActiveCount",0)}</td><td>{_html_escape(str(ul))}</td></tr>'
                grid_parts.append(f'<div><h4>{_i18n("By Client IP", "按客户端 IP")}</h4><table><tr><th>{_i18n("Client IP", "客户端 IP")}</th><th>{_i18n("Total", "总计")}</th><th>{_i18n("Active", "活跃")}</th><th>User</th></tr>{rows}</table></div>')
            db_stats = sd.get('DbStats', [])
            if db_stats:
                rows = ''.join(f'<tr><td>{_html_escape(d.get("Key","") or "(none)")}</td><td>{d.get("TotalCount",0)}</td><td>{d.get("ActiveCount",0)}</td></tr>' for d in db_stats)
                grid_parts.append(f'<div><h4>{_i18n("By Database", "按数据库")}</h4><table><tr><th>{_i18n("Database", "数据库")}</th><th>{_i18n("Total", "总计")}</th><th>{_i18n("Active", "活跃")}</th></tr>{rows}</table></div>')
            if grid_parts:
                node_html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem;margin:1rem 0;">' + ''.join(grid_parts) + '</div>'

            if not active_s and not abnormal_s and len(binlog_s) <= 10:
                node_html += f'<p>{_i18n("No active or abnormal sessions", "无活跃或异常会话")}</p>'

            session_html += f'<div id="sess_node_{idx}" class="sess-node-panel" style="display:{display};">{node_html}</div>'
    else:
        session_html = f'<p>{_i18n("⚠️ Failed to retrieve session info", "⚠️ 会话信息获取失败")}</p>'

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
        disk_trend_html = f'<p><strong>{_i18n("Current Usage", "当前使用量")}</strong>: {format_mb(last_mb)} &nbsp;|&nbsp; <strong>{_i18n(f"{_INSPECT_DAYS} days ago", f"{_INSPECT_DAYS} 天前")}</strong>: {format_mb(first_mb)} &nbsp;|&nbsp; <strong>{_i18n(f"{_INSPECT_DAYS}-day change", f"{_INSPECT_DAYS} 天变化")}</strong>: {sign_c}{format_mb(abs(change_mb))} &nbsp;|&nbsp; <strong>{_i18n("Daily Avg Growth", "日均增长")}</strong>: {sign_d}{format_mb(abs(daily))}</p>'

    # 4.2 Space TOP20 rows (with fragment column)
    space_rows = ''
    for i, t in enumerate(space.get('table_list', []), 1):
        frag_str = format_bytes(t.get('frag', 0))
        space_rows += f'<tr><td>{i}</td><td>{_html_escape(t["db"])}</td><td>{_html_escape(t["table"])}</td><td>{t["total_str"]}</td><td>{t["data_str"]}</td><td>{t["index_str"]}</td><td>{frag_str}</td><td>{t["rows"]:,}</td></tr>\n'

    # 4.3 Anomalies (with # column)
    anom = space.get('anomalies', [])
    if anom:
        anom_rows = ''.join(f'<tr><td>{i}</td><td>{a["type"]}</td><td>{_html_escape(a["db"])}</td><td>{_html_escape(a["table"])}</td><td>{a["detail"]}</td></tr>' for i, a in enumerate(anom, 1))
        anom_html = f'<table><tr><th>#</th><th>{_i18n("Type", "类型")}</th><th>{_i18n("Database", "数据库")}</th><th>{_i18n("Table", "表名")}</th><th>{_i18n("Details", "详情")}</th></tr>{anom_rows}</table>'
    else:
        anom_html = f'<p class="ok-msg">{_i18n("✅ No anomalies found", "✅ 未发现异常")}</p>'

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
        slow_detail = f'<h3 style="margin-top:2rem;">{_i18n("SQLHASH and Full SQL Reference", "SQLHASH 与完整 SQL 参考")}</h3><table class="sql-detail-table">'
        slow_detail += f'<tr><th>SQLHASH</th><th>{_i18n("Full SQL", "完整 SQL")}</th></tr>'
        for s in data['slow_logs']:
            hash_val = _html_escape(s.get("sql_hash", ""))
            full_text = _html_escape(s['sql_text'])
            slow_detail += f'<tr id="sql_{hash_val}"><td><code>{hash_val}</code></td><td class="sql-full">{full_text}</td></tr>'
        slow_detail += '</table>'
    slow_total = data.get('slow_total', 0)
    _slow_th = (
        '<th>#</th><th>' + _i18n('Database', '数据库') + '</th><th>SQLHASH</th>'
        '<th>' + _i18n('Count', '次数') + '</th>'
        '<th>' + _i18n('Total Duration(s)', '总耗时(s)') + '</th>'
        '<th>' + _i18n('Max(s)', '最大(s)') + '</th>'
        '<th>' + _i18n('Avg Rows Scanned', '平均扫描行数') + '</th>'
        '<th>' + _i18n('Avg Rows Returned', '平均返回行数') + '</th>'
        '<th>' + _i18n('SQL Summary', 'SQL 摘要') + '</th>'
    )
    _slow_summary = _i18n(f'Total {slow_total} slow query entries', f'共 {slow_total} 条慢查询记录')
    slow_html = f'<table><tr>{_slow_th}</tr>{slow_rows}</table><p>{_slow_summary}</p>{slow_detail}' if slow_rows else f'<p class="ok-msg">{_i18n("✅ No slow log records in last " + str(_INSPECT_DAYS) + " days", "✅ 近 " + str(_INSPECT_DAYS) + " 天无慢日志记录")}</p>'

    # Alert rules
    a_rules = data.get('alert_rules', [])
    if a_rules:
        rule_rows = ''
        for i, r in enumerate(a_rules, 1):
            state_cls = 'danger' if r['state'] == 'ALARM' else ('ok' if r['state'] == 'OK' else '')
            state_text = f'<span class="{state_cls}">{r["state"]}</span>'
            th = r.get('thresholds', {})
            th_parts = []
            for lvl, val in [('Critical', '🔴'), ('Warn', '🟡'), ('Info', '🔵')]:
                if lvl in th:
                    th_parts.append(f'{val} {th[lvl]}')
            th_text = ' / '.join(th_parts) if th_parts else '-'
            enabled_text = '✅' if r['enabled'] else '❌'
            rule_rows += f'<tr><td>{i}</td><td>{_html_escape(r["rule_name"])}</td><td>{_html_escape(r["metric"])}</td><td>{th_text}</td><td>{state_text}</td><td>{enabled_text}</td><td>{r["interval"]}s</td><td>{_html_escape(r["contact_groups"])}</td></tr>'
        rules_html = f'<h3>{_i18n("6.1 Alert Rule Configuration", "6.1 告警规则配置")}</h3><table><tr><th>#</th><th>{_i18n("Rule Name", "规则名称")}</th><th>{_i18n("Metric", "指标")}</th><th>{_i18n("Threshold", "阈值")}</th><th>{_i18n("Current Status", "当前状态")}</th><th>{_i18n("Enabled", "启用")}</th><th>{_i18n("Detection Period", "探测周期")}</th><th>{_i18n("Notification Group", "通知组")}</th></tr>{rule_rows}</table><p>{_i18n(f"Total {len(a_rules)} alert rules", f"共 {len(a_rules)} 条告警规则")}</p>'
    else:
        rules_html = f'<h3>{_i18n("6.1 Alert Rule Configuration", "6.1 告警规则配置")}</h3><p class="ok-msg">{_i18n("No alert rules detected for this instance", "未检测到该实例的告警规则")}</p>'

    # Alert history
    alerts = data.get('alert_history', [])
    if alerts:
        alert_rows = ''
        for i, a in enumerate(alerts, 1):
            lvl_cls = 'danger' if a['level'] in ('P1', 'P2') else ('warn' if a['level'] == 'P3' else '')
            alert_rows += f'<tr class="{lvl_cls}"><td>{i}</td><td>{a["time"]}</td><td>{a["level"]}</td><td>{_html_escape(a.get("rule_name",""))}</td><td>{_html_escape(a.get("metric",""))}</td><td>{_html_escape(a.get("node_id",""))}</td><td>{a.get("cur_value","")}</td><td>{a.get("threshold","")}</td><td>{_html_escape(a.get("send_status",""))}</td></tr>'
        alert_hist_html = f'<h3>{_i18n("6.2 Alert Records", "6.2 告警记录")}</h3><table><tr><th>#</th><th>{_i18n("Time", "时间")}</th><th>{_i18n("Level", "级别")}</th><th>{_i18n("Rule", "规则")}</th><th>{_i18n("Metric", "指标")}</th><th>{_i18n("Node", "节点")}</th><th>{_i18n("Current Value", "当前值")}</th><th>{_i18n("Threshold", "阈值")}</th><th>{_i18n("Notification Status", "通知状态")}</th></tr>{alert_rows}</table><p>{_i18n(f"Total {len(alerts)} alert records", f"共 {len(alerts)} 条告警记录")}</p>'
    else:
        alert_hist_html = f'<h3>{_i18n("6.2 Alert Records", "6.2 告警记录")}</h3><p class="ok-msg">{_i18n(f"✅ No alert records in last {_INSPECT_DAYS} days", f"✅ 近 {_INSPECT_DAYS} 天无告警记录")}</p>'
    alert_html = rules_html + alert_hist_html

    # Suggestions
    sug_html = ''
    sug = data.get('suggestions', [])
    if not sug:
        sug_html = f'<p class="ok-msg">{_i18n("✅ No significant issues found, instance is running normally.", "✅ 未发现明显问题，实例运行正常。")}</p>'
    else:
        danger_items = [(text_en, text_zh) for level, _, text_en, text_zh in sug if level == 'danger']
        warn_items = [(text_en, text_zh) for level, _, text_en, text_zh in sug if level == 'warn']
        info_items = [(text_en, text_zh) for level, _, text_en, text_zh in sug if level == 'info']
        for label, items in [(_i18n('🔴 High Risk', '🔴 高风险'), danger_items), (_i18n('🟡 Medium Risk', '🟡 中风险'), warn_items), (_i18n('🔵 Low Risk', '🔵 低风险'), info_items)]:
            if not items:
                continue
            sug_html += f'<h3 style="margin:0.8rem 0 0.4rem;">{label}</h3>'
            if len(items) == 1:
                sug_html += f'<p style="margin-left:1.2rem;">{_i18n(_escape_preserve_links(items[0][0]), _escape_preserve_links(items[0][1]))}</p>'
            else:
                sug_html += '<ol class="sug-list">'
                for en, zh in items:
                    sug_html += f'<li>{_i18n(_escape_preserve_links(en), _escape_preserve_links(zh))}</li>'
                sug_html += '</ol>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PolarDB MySQL Inspection Report - {data["cluster_id"]}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root {{ --ok: #10b981; --warn: #f59e0b; --danger: #ef4444; --info: #3b82f6; --bg: #f8fafc; --card: #ffffff; --border: #e2e8f0; --text: #1e293b; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; position: relative; }}
.header h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
.header .meta {{ opacity: 0.9; font-size: 0.9rem; }}
.toc {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 0.7rem 1.2rem; margin-bottom: 1.5rem; font-size: 0.85rem; }}
.toc a {{ color: #1e40af; margin-right: 1rem; text-decoration: none; }}
.toc a:hover {{ text-decoration: underline; }}
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
.info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; }}
.info-item {{ padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border); display: flex; }}
.info-item .label {{ color: #64748b; min-width: 170px; font-size: 0.83rem; white-space: nowrap; margin-right: 0.5rem; }}
.info-item .value {{ font-weight: 500; font-size: 0.83rem; }}
.table-scroll {{ overflow-x: auto; }}
.chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 1rem; }}
.chart-card {{ background: #f8fafc; border: 1px solid var(--border); border-radius: 6px; padding: 12px; }}
.chart-card h4 {{ margin: 0 0 4px 0; font-size: 0.9rem; color: #334155; }}
.echart {{ width: 100%; height: 280px; }}
html[lang="en"] .i18n-zh {{ display: none; }}
html[lang="zh"] .i18n-en {{ display: none; }}
.lang-toggle {{ position: absolute; top: 1rem; right: 1.5rem; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.35); border-radius: 999px; padding: 4px 14px; cursor: pointer; color: #fff; font-size: 0.78rem; font-weight: 500; user-select: none; letter-spacing: 0.5px; }}
.lang-toggle:hover {{ background: rgba(255,255,255,0.28); }}
@media (max-width: 768px) {{ body {{ padding: 1rem; }} table {{ font-size: 0.75rem; }} th, td {{ padding: 0.3rem 0.5rem; }} .chart-grid {{ grid-template-columns: 1fr; }} .info-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <button class="lang-toggle" type="button">中文</button>
        <h1>{_i18n('PolarDB MySQL Instance Health Inspection Report', 'PolarDB MySQL 实例健康巡检报告')}</h1>
        <div class="meta">
            <span>{_i18n('Inspection Time', '巡检时间')}: {data["inspect_time"]}</span> &nbsp;|&nbsp;
            <span>{_i18n('Instance', '实例')}: {data["cluster_id"]}</span> &nbsp;|&nbsp;
            <span>Region: {data["region"]}</span>
        </div>
    </div>

    <div class="toc">
        <a href="#sec-1">{_i18n('1. Basic Info', '一、基础信息')}</a>
        <a href="#sec-2">{_i18n('2. Sessions', '二、会话信息')}</a>
        <a href="#sec-3">{_i18n('3. Resource Usage', '三、资源使用率')}</a>
        <a href="#sec-4">{_i18n('4. Space', '四、空间分析')}</a>
        <a href="#sec-5">{_i18n('5. Slow Logs', '五、慢日志')}</a>
        <a href="#sec-6">{_i18n('6. Alerts', '六、告警历史')}</a>
        <a href="#sec-7">{_i18n('7. Conclusions', '七、巡检结论')}</a>
    </div>

    <div class="section" id="sec-1" data-item="basic">
        <h2>{_i18n('1. Instance Basic Information', '一、实例基本信息')}</h2>
        <div class="info-grid">
            <div class="info-item"><span class="label">{_i18n('Database Type', '数据库类型')}</span><span class="value">{bi["db_type"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Major Version', '主版本')}</span><span class="value">{bi["db_type"]} {bi["db_version"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Cluster Status', '集群状态')}</span><span class="value">{bi["status"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Kernel Minor Version', '内核小版本')}</span><span class="value">{bi["revision_version"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Latest Available Version', '最新可用版本')}</span><span class="value">{bi["latest_version"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Version Status', '版本状态')}</span><span class="value">{vb}</span></div>
            <div class="info-item"><span class="label">{_i18n('Proxy Version', 'Proxy 版本')}</span><span class="value">{bi["proxy_version"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Storage Type', '存储类型')}</span><span class="value">{bi["storage_type"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Cluster Category', '集群系列')}</span><span class="value">{bi["category"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Storage Used', '已用存储')}</span><span class="value">{bi["storage_used_str"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Storage Capacity', '存储容量')}</span><span class="value">{bi["storage_space_str"] or bi["storage_max_str"]}</span></div>
            <div class="info-item"><span class="label">{_i18n('Auto Expansion', '自动扩容')}</span><span class="value">{
    _i18n('Auto-expand (PSL storage)', '自动扩展（PSL 存储）') if bi.get('is_psl') else
    (_i18n('Enabled (upper limit ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + ')', '已开启（上限 ' + (f'{bi["storage_auto_scale_upper"]/1024:.1f} TB' if bi["storage_auto_scale_upper"] >= 1024 else f'{bi["storage_auto_scale_upper"]} GB') + '）') if bi.get('storage_auto_scale') else _i18n('Disabled', '未开启')) if bi.get('is_essd') else
    'N/A'
}</span></div>
        </div>
        <h3 style="margin-top:1rem;font-size:1rem;">{_i18n(f'Node Details ({len(nodes)} nodes)', f'节点详情（{len(nodes)} 个节点）')}</h3>
        <table>
            <tr><th>{_i18n('Node ID', '节点 ID')}</th><th>{_i18n('Role', '角色')}</th><th>{_i18n('Status', '状态')}</th><th>{_i18n('Spec', '规格')}</th><th>CPU</th><th>{_i18n('Memory', '内存')}</th><th>{_i18n('Max Conn', '最大连接数')}</th><th>Max IOPS</th></tr>
            {node_rows}
        </table>
    </div>

    {'<div class="section" id="sec-2" data-item="session"><h2>' + _i18n('2. Current Sessions', '二、当前会话') + '</h2>' + session_html + '</div>' if 'session' in _INSPECT_ITEMS else ''}

    {'<div class="section" id="sec-3" data-item="resource"><h2>' + _i18n('3. Resource Usage (Last ' + str(_INSPECT_DAYS) + ' Days)', '三、资源使用率（近 ' + str(_INSPECT_DAYS) + ' 天）') + '</h2><div class="table-scroll"><table><tr><th>' + _i18n('Node', '节点') + '</th><th>' + _i18n('CPU (Avg/Peak)', 'CPU（均值/峰值）') + '</th><th>' + _i18n('Memory (Avg/Peak)', '内存（均值/峰值）') + '</th><th>' + _i18n('IOPS (Avg/Peak)', 'IOPS（均值/峰值）') + '</th><th>' + _i18n('Conn (Avg/Peak)', '连接数（均值/峰值）') + '</th><th>' + _i18n('Active Conn (Avg/Peak)', '活跃连接（均值/峰值）') + '</th><th>' + _i18n('Status', '状态') + '</th></tr>' + resource_rows + '</table></div><h3 style="margin-top:1.5rem;font-size:1rem;">' + _i18n('Proxy Monitoring Trends', 'Proxy 监控趋势') + '</h3><div class="chart-grid"><div class="chart-card"><h4>' + _i18n('Proxy CPU Usage (%)', 'Proxy CPU 使用率（%）') + '</h4><div id="chart-proxy-cpu" class="echart"></div></div><div class="chart-card"><h4>' + _i18n('Proxy Session Routing (ops/sec)', 'Proxy 会话路由（ops/sec）') + '</h4><div id="chart-proxy-route" class="echart"></div></div></div><h3 style="margin-top:1.5rem;font-size:1rem;">' + _i18n('DB Monitoring Trends', 'DB 监控趋势') + '</h3><div class="chart-grid"><div class="chart-card"><h4>' + _i18n('CPU Usage (%)', 'CPU 使用率（%）') + '</h4><div id="chart-cpu" class="echart"></div></div><div class="chart-card"><h4>' + _i18n('Memory Usage (%)', '内存使用率（%）') + '</h4><div id="chart-mem" class="echart"></div></div><div class="chart-card"><h4>' + _i18n('IOPS Usage (%)', 'IOPS 使用率（%）') + '</h4><div id="chart-iops" class="echart"></div></div><div class="chart-card"><h4>' + _i18n('Connection Usage (%)', '连接使用率（%）') + '</h4><div id="chart-conn" class="echart"></div></div></div></div>' if 'resource' in _INSPECT_ITEMS else ''}

    {'<div class="section" id="sec-4" data-item="space"><h2>' + _i18n('4. Space Inspection', '四、空间巡检') + '</h2><h3>' + _i18n('4.1 Space Change Trend (' + str(_INSPECT_DAYS) + ' days, GB)', '4.1 空间变化趋势（' + str(_INSPECT_DAYS) + ' 天，GB）') + '</h3>' + disk_trend_html + '<div class="chart-card"><div id="chart-disk" class="echart"></div></div><h3>' + _i18n('4.2 Table Space Overview (TOP20)', '4.2 表空间概览（TOP20）') + '</h3><table><tr><th>#</th><th>' + _i18n('Database', '数据库') + '</th><th>' + _i18n('Table', '表名') + '</th><th>' + _i18n('Total', '总大小') + '</th><th>' + _i18n('Data', '数据') + '</th><th>' + _i18n('Index', '索引') + '</th><th>' + _i18n('Fragment', '碎片') + '</th><th>' + _i18n('Rows', '行数') + '</th></tr>' + space_rows + '</table><h3>' + _i18n('4.3 Anomaly List', '4.3 异常列表') + '</h3>' + anom_html + '</div>' if 'space' in _INSPECT_ITEMS else ''}

    {'<div class="section" id="sec-5" data-item="slowlog"><h2>' + _i18n('5. Slow Log Statistics (Last ' + str(_INSPECT_DAYS) + ' Days)', '五、慢日志统计（近 ' + str(_INSPECT_DAYS) + ' 天）') + '</h2>' + slow_html + '</div>' if 'slowlog' in _INSPECT_ITEMS else ''}

    {'<div class="section" id="sec-6" data-item="alert"><h2>' + _i18n('6. Alert History (Last ' + str(_INSPECT_DAYS) + ' Days)', '六、告警历史（近 ' + str(_INSPECT_DAYS) + ' 天）') + '</h2>' + alert_html + '</div>' if 'alert' in _INSPECT_ITEMS else ''}

    <div class="section" id="sec-7" data-item="conclusions">
        <h2>{_i18n('7. Inspection Conclusions & Recommendations', '七、巡检结论与建议')}</h2>
        {sug_html}
    </div>

    <div class="footer">{_i18n('Inspection Complete · PolarDB MySQL Health Inspection', '巡检完成 · PolarDB MySQL 健康巡检')}</div>
</div>

<script>
(function initLang() {{
    var saved = localStorage.getItem('polardb-inspection-lang') || 'en';
    document.documentElement.lang = saved;
    document.addEventListener('DOMContentLoaded', function() {{
        var btn = document.querySelector('.lang-toggle');
        if (!btn) return;
        function paint() {{
            var cur = document.documentElement.lang;
            btn.textContent = cur === 'en' ? '中文' : 'EN';
        }}
        paint();
        btn.addEventListener('click', function() {{
            var next = document.documentElement.lang === 'en' ? 'zh' : 'en';
            document.documentElement.lang = next;
            localStorage.setItem('polardb-inspection-lang', next);
            paint();
        }});
    }});
}})();
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
}}

// Proxy charts
(function() {{
    if (!document.getElementById('chart-proxy-cpu')) return;
    var proxyCpu = {proxy_cpu_js};
    var proxyLsn = {proxy_lsn_js};
    var proxyTrx = {proxy_trx_js};
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
            params.forEach(function(p){{ r+=p.marker+p.seriesName+': '+p.value[1].toFixed(2)+' ops/sec<br/>'; }});
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
}})();

function makeLineChart(domId, metricKey) {{
    var el = document.getElementById(domId);
    if (!el) return;
    var chart = echarts.init(el);
    var series = [];
    var legendData = [];

    chartNodes.forEach(function(nd, i) {{
        var label = nd.label;
        var d = metricKey === 'connections'
            ? nd.connections.map(function(p){{ return [p[0], +(p[1]/maxConn*100).toFixed(2)]; }})
            : nd[metricKey];
        series.push({{ name:label, type:'line', symbol:'none', smooth:true, lineStyle:{{width:1.5}}, itemStyle:{{color:colors[i%colors.length]}}, areaStyle:{{opacity:0.05}}, data:d }});
        legendData.push(label);
    }});

    chart.setOption({{
        tooltip: {{ trigger:'axis', formatter:function(params) {{
            if(!params.length) return '';
            var t=new Date(params[0].value[0]);
            var s=t.getFullYear()+'-'+(t.getMonth()+1).toString().padStart(2,'0')+'-'+t.getDate().toString().padStart(2,'0')+' '+t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
            var r='<b>'+s+'</b><br/>';
            params.forEach(function(p){{ r+=p.marker+p.seriesName+': '+p.value[1].toFixed(2)+'%<br/>'; }});
            return r;
        }} }},
        legend: {{ data:legendData, top:0, type:'scroll', textStyle:{{fontSize:10}} }},
        grid: {{ left:45, right:15, top:30, bottom:55 }},
        xAxis: {{ type:'time', axisLabel:{{fontSize:10, formatter:'{{MM}}-{{dd}} {{HH}}:{{mm}}'}} }},
        yAxis: {{ type:'value', min:0, max:100, axisLabel:{{fontSize:10}} }},
        dataZoom: [
            {{type:'inside'}},
            {{type:'slider', height:20, bottom:5, borderColor:'#ddd', fillerColor:'rgba(84,112,198,0.15)', handleStyle:{{color:'#5470c6'}}, textStyle:{{fontSize:10}}, labelFormatter:function(v){{ var d=new Date(v); return (d.getMonth()+1).toString().padStart(2,'0')+'-'+d.getDate().toString().padStart(2,'0')+' '+d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0'); }}}}
        ],
        series: series
    }});
    resCharts.push(chart);
    window.addEventListener('resize', function(){{ chart.resize(); }});
}}

{chart_nodes_js}
makeLineChart('chart-cpu','cpu');
makeLineChart('chart-mem','memory');
makeLineChart('chart-iops','iops');
makeLineChart('chart-conn','connections');

// Link all resource charts zoom
var _zoomLock = false;
resCharts.forEach(function(c, ci) {{
    c.on('dataZoom', function() {{
        if (_zoomLock) return;
        _zoomLock = true;
        var opt = c.getOption();
        var dz = opt.dataZoom[0];
        resCharts.forEach(function(other, oi) {{
            if (oi !== ci) other.dispatchAction({{ type:'dataZoom', start:dz.start, end:dz.end }});
        }});
        _zoomLock = false;
    }});
}});

(function() {{
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
}})();
</script>
</body>
</html>'''
    if _INSPECT_ITEMS != set(ALL_ITEMS):
        import re
        _removable = {'session', 'resource', 'space', 'slowlog', 'alert'}
        for item in _removable - _INSPECT_ITEMS:
            pattern = rf'<div class="section"[^>]*data-item="{item}"[^>]*>.*?</div>\s*(?=<div class="|<script>)'
            html = re.sub(pattern, '', html, flags=re.DOTALL)

        _toc_short_en = {
            'basic': 'Basic Info', 'session': 'Sessions', 'resource': 'Resource Usage',
            'space': 'Space', 'slowlog': 'Slow Logs', 'alert': 'Alerts', 'conclusions': 'Conclusions',
        }
        _toc_short_zh = {
            'basic': '基础信息', 'session': '会话信息', 'resource': '资源使用率',
            'space': '空间分析', 'slowlog': '慢日志', 'alert': '告警历史', 'conclusions': '巡检结论',
        }
        remaining = []
        counter = [0]
        def _renumber_sec(m):
            counter[0] += 1
            data_item = re.search(r'data-item="([^"]+)"', m.group(1))
            item_key = data_item.group(1) if data_item else ''
            remaining.append((counter[0], item_key))
            return f'<div class="section" id="sec-{counter[0]}" {m.group(1).split(">")[0].split("id=")[0]}>'

        html = re.sub(r'<div class="section"([^>]*)>', _renumber_sec, html)

        num_counter = [0]
        def _renumber_h2(m):
            num_counter[0] += 1
            content = m.group(1)
            content = re.sub(r'(?<=>)[一二三四五六七八九十\d]+[、.．]\s*', f'{num_counter[0]}. ', content)
            content = re.sub(r'^[一二三四五六七八九十\d]+[、.．]\s*', f'{num_counter[0]}. ', content)
            return f'<h2>{content}</h2>'
        html = re.sub(r'<h2>(.*?)</h2>', _renumber_h2, html)

        toc_links = ''.join(
            f'<a href="#sec-{i}">{_i18n(f"{i}. {_toc_short_en.get(k, k)}", f"{i}. {_toc_short_zh.get(k, k)}")}</a>'
            for i, k in remaining
        )
        html = re.sub(r'<div class="toc">.*?</div>', f'<div class="toc">{toc_links}</div>', html, flags=re.DOTALL)

    return html



# ─── Dispatcher ───────────────────────────────────────────────────────────────

def generate_report(cluster_id, region, cluster_info, version_info, resource_usage,
                    nodes, space_data, slow_logs, fmt='markdown',
                    param_max_conn=None, auto_inc_data=None, session_info=None,
                    alert_history=None, alert_rules=None, das_config=None, proxy_perf=None):
    data = collect_report_data(cluster_id, region, cluster_info, version_info,
                               resource_usage, nodes, space_data, slow_logs,
                               auto_inc_data, param_max_conn, session_info,
                               alert_history, alert_rules=alert_rules,
                               das_config=das_config, proxy_perf=proxy_perf)
    if fmt == 'html':
        return render_html(data), data
    elif fmt == 'text':
        return render_text(data), data
    else:
        return render_markdown(data), data


# ─── Main ─────────────────────────────────────────────────────────────────────

def discover_all_clusters(region=None):
    """List all PolarDB MySQL clusters in the current account"""
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
                if page == 1 and _last_cli_error:
                    print(f'    {r}: query failed ({_last_cli_error})', flush=True)
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
    """Inspect a single cluster, return (cluster_id, report_path, summary_data)"""
    print(f'\n{"="*60}')
    print(f'  Inspecting cluster: {cluster_id}')
    print(f'{"="*60}')

    if not region:
        region = find_region(cluster_id)
        if not region:
            print(f'  ❌ Cluster not found {cluster_id}')
            return cluster_id, None, {'cluster_id': cluster_id, 'error': 'Cluster not found'}
    print(f'  Region: {region}')

    print('  📋 Basic info...', end=' ', flush=True)
    cluster_info = get_cluster_info(cluster_id, region)
    if not cluster_info:
        print('❌')
        return cluster_id, None, {'cluster_id': cluster_id, 'region': region, 'error': 'Failed to get info'}
    print('✅')

    print('  🏷️  Version info...', end=' ', flush=True)
    version_info = get_version_info(cluster_id, region)
    print('✅' if version_info else '⚠️')

    nodes = cluster_info.get('DBNodes', [])
    if isinstance(nodes, dict):
        nodes = nodes.get('DBNode', [])

    param_max_conn = get_max_connections_from_params(cluster_id, region)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=_INSPECT_DAYS)
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
    alert_rules = None

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        if 'resource' in _INSPECT_ITEMS:
            futures['resource'] = pool.submit(get_resource_usage, cluster_id, region, nodes, start_time, end_time)
            futures['proxy'] = pool.submit(get_proxy_performance, cluster_id, region, nodes, start_time, end_time)
        if 'space' in _INSPECT_ITEMS:
            futures['space'] = pool.submit(get_space_top20, cluster_id)
            futures['auto_inc'] = pool.submit(get_auto_increment_usage, cluster_id)
        if 'slowlog' in _INSPECT_ITEMS:
            futures['slow'] = pool.submit(get_slow_logs, cluster_id, region)
        if 'session' in _INSPECT_ITEMS:
            futures['session'] = pool.submit(get_session_info, cluster_id, nodes)
        if 'alert' in _INSPECT_ITEMS:
            futures['alert'] = pool.submit(get_alert_history, cluster_id, start_time, end_time)
            futures['alert_rules'] = pool.submit(get_alert_rules, cluster_id)

        if 'resource' in futures:
            resource_usage = futures['resource'].result()
        if 'proxy' in futures:
            proxy_perf = futures['proxy'].result()
        if 'space' in futures:
            space_data = futures['space'].result()
        if 'auto_inc' in futures:
            auto_inc_data = futures['auto_inc'].result()
        if 'slow' in futures:
            slow_logs = futures['slow'].result()
        if 'session' in futures:
            session_info = futures['session'].result()
        if 'alert' in futures:
            alert_history = futures['alert'].result()
        if 'alert_rules' in futures:
            alert_rules = futures['alert_rules'].result()

    items_count = len(slow_logs.get('Items', {}).get('SQLSlowLog', [])) if slow_logs else 0
    print(f'  ✅ Data collection complete ({items_count} slow logs)')

    das_config = None
    if 'essd' in cluster_info.get('StorageType', '').lower():
        das_config = call_cli('polardb', 'describe-das-config', region,
                              **{'db-cluster-id': cluster_id})

    report, data = generate_report(cluster_id, region, cluster_info, version_info,
                                   resource_usage, nodes, space_data, slow_logs,
                                   fmt=fmt, param_max_conn=param_max_conn,
                                   auto_inc_data=auto_inc_data, session_info=session_info,
                                   alert_history=alert_history, alert_rules=alert_rules,
                                   das_config=das_config, proxy_perf=proxy_perf)

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
    return cluster_id, report_path, summary


def render_summary_html(summaries, output_dir, inspect_time):
    """Generate summary HTML page (card layout)"""

    def _health_level(s):
        if s.get('error'):
            return 'error'
        for item in s.get('suggestions', []):
            if item[0] == 'danger':
                return 'danger'
        for item in s.get('suggestions', []):
            if item[0] == 'warn':
                return 'warn'
        return 'normal'

    def _level_color(level):
        return {'danger': '#e53935', 'warn': '#f9a825', 'normal': '#43a047', 'error': '#9e9e9e'}[level]

    def _level_icon(level):
        return {'danger': '🔴', 'warn': '🟡', 'normal': '🟢', 'error': '⚪'}[level]

    def _metric_class(value, thresholds=(60, 80)):
        if value > thresholds[1]:
            return 'metric-danger'
        elif value > thresholds[0]:
            return 'metric-warn'
        return ''

    total = len(summaries)
    levels = [_health_level(s) for s in summaries]
    danger_count = levels.count('danger')
    warn_count = levels.count('warn')
    normal_count = levels.count('normal')
    error_count = levels.count('error')

    cards_html = ''
    for i, s in enumerate(summaries):
        level = levels[i]
        color = _level_color(level)
        icon = _level_icon(level)

        if s.get('error'):
            cards_html += f'''
            <div class="card" data-level="{level}" style="border-top:4px solid {color};">
              <div class="card-header"><span class="card-icon">{icon}</span> {_html_escape(s['cluster_id'])}</div>
              <div class="card-body"><p class="error-msg">{_html_escape(s['error'])}</p></div>
            </div>'''
            continue

        cpu_cls = _metric_class(s['cpu_peak'])
        mem_cls = _metric_class(s['mem_peak'])
        iops_cls = _metric_class(s['iops_peak'])
        conn_cls = _metric_class(s['conn_peak_pct'])
        disk_cls = _metric_class(s['disk_peak_pct'], (70, 85))

        node_mem_raw = s.get('node_mem', '')
        if node_mem_raw.endswith('MB'):
            try:
                node_mem_display = f"{int(node_mem_raw[:-2])/1024:.0f}G"
            except ValueError:
                node_mem_display = node_mem_raw
        elif node_mem_raw.endswith('GB'):
            node_mem_display = node_mem_raw[:-2] + 'G'
        else:
            node_mem_display = node_mem_raw
        node_spec = f"{s.get('node_cpu', '')}C{node_mem_display} × {s['node_count']}"
        desc = s.get('description', '')
        desc_html = f'<div class="card-desc">{_html_escape(desc)}</div>' if desc else ''

        danger_sug = sum(1 for item in s.get('suggestions', []) if item[0] == 'danger')
        warn_sug = sum(1 for item in s.get('suggestions', []) if item[0] == 'warn')
        sug_badge = ''
        if danger_sug:
            sug_badge += f'<span class="sug-badge sug-danger">{danger_sug} {_i18n("High Risk", "高风险")}</span>'
        if warn_sug:
            sug_badge += f'<span class="sug-badge sug-warn">{warn_sug} {_i18n("Medium Risk", "中风险")}</span>'

        cards_html += f'''
        <a class="card" data-level="{level}" href="{s['report_file']}" style="border-top:4px solid {color};">
          <div class="card-header">
            <span class="card-icon">{icon}</span>
            <span class="card-id">{_html_escape(s['cluster_id'])}</span>
          </div>
          {desc_html}
          <div class="card-meta">{_html_escape(s['region'])} | {_html_escape(node_spec)}</div>
          <div class="card-metrics"><div class="card-metrics-inner">
            <div class="metric-row"><span class="metric-label">{_i18n('CPU Usage', 'CPU 使用率')}</span><span class="metric-val {cpu_cls}">{s['cpu_avg']:.1f}% / {s['cpu_peak']:.1f}%</span></div>
            <div class="metric-row"><span class="metric-label">{_i18n('Memory Usage', '内存使用率')}</span><span class="metric-val {mem_cls}">{s['mem_avg']:.1f}% / {s['mem_peak']:.1f}%</span></div>
            <div class="metric-row"><span class="metric-label">{_i18n('IOPS Usage', 'IOPS 使用率')}</span><span class="metric-val {iops_cls}">{s['iops_avg']:.1f}% / {s['iops_peak']:.1f}%</span></div>
            <div class="metric-row"><span class="metric-label">{_i18n('Conn Usage', '连接使用率')}</span><span class="metric-val {conn_cls}">{s['conn_avg_pct']:.1f}% / {s['conn_peak_pct']:.1f}%</span></div>
            <div class="metric-row"><span class="metric-label">{_i18n('Space Usage', '空间使用率')}</span><span class="metric-val {disk_cls}">{s['disk_avg_pct']:.1f}% / {s['disk_peak_pct']:.1f}%</span></div>
          </div></div>
          <div class="card-footer">
            <span>{_i18n('Slow Logs', '慢日志')}: {s['slow_count']}</span>
            <span>{_i18n('Alerts', '告警')}: {s['alert_count']}</span>
          </div>
          {f'<div class="card-sug">{sug_badge}</div>' if sug_badge else ''}
          <div class="card-link">{_i18n('View Details →', '查看详情 →')}</div>
        </a>'''

    # Build risk detail card
    risk_html = ''
    has_risk = False
    for i, s in enumerate(summaries):
        if s.get('error'):
            continue
        danger_items = [(en, zh) for lv, _, en, zh in s.get('suggestions', []) if lv == 'danger']
        warn_items = [(en, zh) for lv, _, en, zh in s.get('suggestions', []) if lv == 'warn']
        if not danger_items and not warn_items:
            continue
        has_risk = True
        cid = s.get('cluster_id', '')
        desc = s.get('description', '')
        label = f'{cid}' + (f' ({desc})' if desc and desc != cid else '')
        report_file = s["report_file"]
        risk_html += f'<div class="risk-instance"><div class="risk-instance-header"><a href="{report_file}">{_html_escape(label)}</a></div>'
        if danger_items:
            risk_html += '<ul class="risk-list risk-list-danger">'
            for en, zh in danger_items:
                en = en.replace('href="#', 'href="' + report_file + '#')
                zh = zh.replace('href="#', 'href="' + report_file + '#')
                risk_html += f'<li>{_i18n(_escape_preserve_links(en), _escape_preserve_links(zh))}</li>'
            risk_html += '</ul>'
        if warn_items:
            risk_html += '<ul class="risk-list risk-list-warn">'
            for en, zh in warn_items:
                en = en.replace('href="#', 'href="' + report_file + '#')
                zh = zh.replace('href="#', 'href="' + report_file + '#')
                risk_html += f'<li>{_i18n(_escape_preserve_links(en), _escape_preserve_links(zh))}</li>'
            risk_html += '</ul>'
        risk_html += '</div>'

    risk_section = ''
    if has_risk:
        risk_section = f'''
<div class="risk-card">
  <h2 class="risk-title">⚠ {_i18n('Risk Details', '风险详情')}</h2>
  {risk_html}
</div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>PolarDB MySQL Batch Inspection Overview</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html[lang="en"] .i18n-zh {{ display: none; }}
html[lang="zh"] .i18n-en {{ display: none; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f5f5f5; padding:2rem; color:#333; }}
.container {{ max-width:1200px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg, #1e40af, #3b82f6); color:white; padding:2rem; border-radius:12px; margin-bottom:24px; position:relative; }}
.lang-toggle {{ position:absolute; top:1rem; right:1.5rem; background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.35); border-radius:999px; padding:4px 14px; cursor:pointer; color:#fff; font-size:0.78rem; font-weight:500; user-select:none; letter-spacing:0.5px; }}
.lang-toggle:hover {{ background:rgba(255,255,255,0.28); }}
.header h1 {{ font-size:1.5rem; margin-bottom:8px; }}
.header .time {{ color:rgba(255,255,255,0.85); font-size:0.9rem; }}
.filters {{ display:flex; justify-content:center; gap:8px; margin:16px 0 24px; flex-wrap:wrap; }}
.filter-btn {{ background:#fff; border:1.5px solid #ddd; border-radius:20px; padding:6px 16px; font-size:0.9rem; cursor:pointer; transition:all 0.15s; user-select:none; }}
.filter-btn:hover {{ border-color:#999; }}
.filter-btn.active {{ border-color:currentColor; font-weight:600; }}
.filter-btn[data-filter="all"] {{ color:#333; }}
.filter-btn[data-filter="all"].active {{ background:#333; color:#fff; border-color:#333; }}
.filter-btn[data-filter="danger"] {{ color:#e53935; }}
.filter-btn[data-filter="danger"].active {{ background:#e53935; color:#fff; border-color:#e53935; }}
.filter-btn[data-filter="warn"] {{ color:#f9a825; }}
.filter-btn[data-filter="warn"].active {{ background:#f9a825; color:#fff; border-color:#f9a825; }}
.filter-btn[data-filter="normal"] {{ color:#43a047; }}
.filter-btn[data-filter="normal"].active {{ background:#43a047; color:#fff; border-color:#43a047; }}
.filter-btn[data-filter="error"] {{ color:#9e9e9e; }}
.filter-btn[data-filter="error"].active {{ background:#9e9e9e; color:#fff; border-color:#9e9e9e; }}
.grid {{ display:flex; flex-wrap:wrap; justify-content:center; gap:16px; }}
.card {{ width:280px; flex-shrink:0; }}
.card {{ display:block; background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.08); text-decoration:none; color:inherit; transition:transform 0.15s,box-shadow 0.15s,opacity 0.2s; }}
.card.hidden {{ display:none; }}
a.card:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.12); }}
.card-header {{ display:flex; align-items:center; gap:6px; margin-bottom:6px; }}
.card-icon {{ font-size:1.1rem; }}
.card-id {{ font-weight:600; font-size:0.95rem; font-family:monospace; }}
.card-desc {{ color:#666; font-size:0.8rem; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.card-meta {{ color:#888; font-size:0.8rem; margin-bottom:10px; }}
.card-metrics {{ display:inline-block; margin:0 auto 10px; width:100%; text-align:center; }}
.card-metrics-inner {{ display:inline-block; text-align:left; }}
.metric-row {{ display:flex; align-items:baseline; font-size:0.85rem; padding:1px 0; }}
.metric-label {{ color:#666; white-space:nowrap; width:8em; flex-shrink:0; margin-right:1em; }}
.metric-val {{ font-weight:500; font-family:monospace; font-size:0.8rem; white-space:nowrap; }}
.metric-danger {{ color:#e53935; font-weight:700; }}
.metric-warn {{ color:#f9a825; font-weight:600; }}
.card-footer {{ display:flex; gap:12px; font-size:0.8rem; color:#666; margin-bottom:6px; }}
.card-sug {{ margin-bottom:6px; }}
.sug-badge {{ font-size:0.75rem; padding:2px 6px; border-radius:3px; margin-right:4px; }}
.sug-danger {{ background:#ffebee; color:#c62828; }}
.sug-warn {{ background:#fff8e1; color:#f57f17; }}
.card-link {{ text-align:right; font-size:0.8rem; color:#1976d2; }}
.error-msg {{ color:#9e9e9e; font-style:italic; }}
.metric-hint {{ text-align:right; font-size:0.7rem; color:#aaa; margin-bottom:4px; }}
.risk-card {{ background:#fff; border-radius:8px; padding:24px; margin-bottom:24px; box-shadow:0 1px 4px rgba(0,0,0,0.08); border-left:4px solid #e53935; }}
.risk-title {{ font-size:1.2rem; color:#333; margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid #eee; }}
.risk-instance {{ margin-bottom:16px; }}
.risk-instance:last-child {{ margin-bottom:0; }}
.risk-instance-header {{ font-weight:600; font-size:0.95rem; margin-bottom:6px; }}
.risk-instance-header a {{ color:#1e40af; text-decoration:none; }}
.risk-instance-header a:hover {{ text-decoration:underline; }}
.risk-list {{ padding-left:20px; margin:4px 0 8px; }}
.risk-list li {{ font-size:0.85rem; line-height:1.6; margin-bottom:4px; }}
.risk-list-danger li {{ color:#c62828; }}
.risk-list-warn li {{ color:#e65100; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <button class="lang-toggle" type="button">中文</button>
  <h1>{_i18n('PolarDB MySQL Batch Inspection Overview', 'PolarDB MySQL 批量巡检概览')}</h1>
  <div class="time">{_i18n('Inspection Time', '巡检时间')}: {inspect_time}</div>
</div>
<div class="filters">
  <button class="filter-btn active" data-filter="all">{_i18n(f'All {total}', f'全部 {total}')}</button>
  {f'<button class="filter-btn" data-filter="danger">🔴 {_i18n(f"Critical {danger_count}", f"严重 {danger_count}")}</button>' if danger_count else ''}
  {f'<button class="filter-btn" data-filter="warn">🟡 {_i18n(f"Warning {warn_count}", f"警告 {warn_count}")}</button>' if warn_count else ''}
  <button class="filter-btn" data-filter="normal">🟢 {_i18n(f'Normal {normal_count}', f'正常 {normal_count}')}</button>
  {f'<button class="filter-btn" data-filter="error">⚪ {_i18n(f"Failed {error_count}", f"失败 {error_count}")}</button>' if error_count else ''}
</div>
{risk_section}
<div class="grid">
{cards_html}
</div>
</div>
<script>
(function initLang() {{
    var saved = localStorage.getItem('polardb-inspection-lang') || 'en';
    document.documentElement.lang = saved;
    document.addEventListener('DOMContentLoaded', function() {{
        var btn = document.querySelector('.lang-toggle');
        if (!btn) return;
        function paint() {{
            var cur = document.documentElement.lang;
            btn.textContent = cur === 'en' ? '中文' : 'EN';
        }}
        paint();
        btn.addEventListener('click', function() {{
            var next = document.documentElement.lang === 'en' ? 'zh' : 'en';
            document.documentElement.lang = next;
            localStorage.setItem('polardb-inspection-lang', next);
            paint();
        }});
    }});
}})();
document.querySelectorAll('.filter-btn').forEach(function(btn) {{
  btn.addEventListener('click', function() {{
    document.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    btn.classList.add('active');
    var filter = btn.getAttribute('data-filter');
    document.querySelectorAll('.card').forEach(function(card) {{
      if (filter === 'all' || card.getAttribute('data-level') === filter) {{
        card.classList.remove('hidden');
      }} else {{
        card.classList.add('hidden');
      }}
    }});
  }});
}});
</script>
</body>
</html>'''

    index_path = os.path.join(output_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return index_path


def main():
    parser = argparse.ArgumentParser(
        prog='health-inspect',
        description='PolarDB MySQL Instance Health Inspection Tool (supports single/multi/full-account inspection)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s pc-bp167736gfqyn483x
  %(prog)s pc-bp167736gfqyn483x pc-bp2xxxxx pc-bp3xxxxx
  %(prog)s --all
  %(prog)s --all --region cn-hangzhou
  %(prog)s pc-bp167736gfqyn483x -p myprofile -o ./report.html
        """
    )
    parser.add_argument('cluster_ids', metavar='CLUSTER_ID', nargs='*', help='PolarDB cluster ID (supports multiple)')
    parser.add_argument('--all', action='store_true', help='Inspect all PolarDB MySQL instances in current account')
    parser.add_argument('-r', '--region', help='Instance region')
    parser.add_argument('-p', '--profile', help='aliyun CLI profile name')
    parser.add_argument('-o', '--output', help='Report output file path (single) or directory (multi)')
    parser.add_argument('-d', '--days', type=int, default=7, help='Inspection time range (days), default 7')
    parser.add_argument('--item', action='append', choices=ALL_ITEMS,
                        help='Specify inspection items (can repeat), omit for full inspection. Options: resource, space, slowlog, session, alert')
    parser.add_argument('-f', '--format', choices=['markdown', 'html', 'text'], default='html', help='Report format: html (default), markdown, text')
    args = parser.parse_args()

    if not args.all and not args.cluster_ids:
        parser.error('Please provide at least one CLUSTER_ID or use --all to inspect all instances')

    global _CLI_PROFILE, _INSPECT_DAYS, _INSPECT_ITEMS
    _CLI_PROFILE = args.profile
    _INSPECT_DAYS = args.days
    _INSPECT_ITEMS = set(args.item) if args.item else set(ALL_ITEMS)

    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('❌ aliyun CLI not found, please install first: https://help.aliyun.com/zh/cli/')
        sys.exit(1)

    ensure_cli_plugins()

    # Determine clusters to inspect
    if args.all:
        print('🔍 Discovering all PolarDB MySQL instances...')
        clusters = discover_all_clusters(region=args.region)
        if not clusters:
            print('❌ No PolarDB MySQL instances found')
            sys.exit(1)
        print(f'   ✅ Found {len(clusters)} instances')
        for c in clusters:
            print(f'      - {c["cluster_id"]} ({c["region"]}) {c.get("description", "")}')
    else:
        clusters = [{'cluster_id': cid, 'region': args.region} for cid in args.cluster_ids]

    # Single instance → single file output (no directory wrapper)
    if len(clusters) == 1:
        cluster_id = clusters[0]['cluster_id']
        region = clusters[0].get('region')

        print('┌' + '─' * 50 + '┐')
        print('│  PolarDB MySQL Instance Health Inspection              │')
        print('└' + '─' * 50 + '┘')
        print(f'  Cluster: {cluster_id}')
        if _CLI_PROFILE:
            print(f'  Profile: {_CLI_PROFILE}')

        if not region:
            region = find_region(cluster_id)
            if not region:
                print(f'❌ Cluster not found {cluster_id}')
                sys.exit(1)
        print(f'  Region: {region}')
        print()

        print('📋 Basic info...', end=' ', flush=True)
        cluster_info = get_cluster_info(cluster_id, region)
        if not cluster_info:
            print('❌')
            sys.exit(1)
        print('✅')

        print('🏷️  Version info...', end=' ', flush=True)
        version_info = get_version_info(cluster_id, region)
        print('✅' if version_info else '⚠️')

        nodes = cluster_info.get('DBNodes', [])
        if isinstance(nodes, dict):
            nodes = nodes.get('DBNode', [])

        param_max_conn = get_max_connections_from_params(cluster_id, region)

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=_INSPECT_DAYS)
        start_time = start.strftime('%Y-%m-%dT%H:%MZ')
        end_time = now.strftime('%Y-%m-%dT%H:%MZ')

        print(f'📊 Collecting data in parallel (cluster + {len(nodes)} nodes)...', flush=True)

        resource_usage = None
        proxy_perf = None
        space_data = None
        slow_logs = None
        auto_inc_data = None
        session_info = None
        alert_history = None
        alert_rules = None

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {}
            if 'resource' in _INSPECT_ITEMS:
                futures['resource'] = pool.submit(get_resource_usage, cluster_id, region, nodes, start_time, end_time)
                futures['proxy'] = pool.submit(get_proxy_performance, cluster_id, region, nodes, start_time, end_time)
            if 'space' in _INSPECT_ITEMS:
                futures['space'] = pool.submit(get_space_top20, cluster_id)
                futures['auto_inc'] = pool.submit(get_auto_increment_usage, cluster_id)
            if 'slowlog' in _INSPECT_ITEMS:
                futures['slow'] = pool.submit(get_slow_logs, cluster_id, region)
            if 'session' in _INSPECT_ITEMS:
                futures['session'] = pool.submit(get_session_info, cluster_id, nodes)
            if 'alert' in _INSPECT_ITEMS:
                futures['alert'] = pool.submit(get_alert_history, cluster_id, start_time, end_time)
                futures['alert_rules'] = pool.submit(get_alert_rules, cluster_id)

            if 'resource' in futures:
                resource_usage = futures['resource'].result()
            if 'proxy' in futures:
                proxy_perf = futures['proxy'].result()
            if 'space' in futures:
                space_data = futures['space'].result()
            if 'auto_inc' in futures:
                auto_inc_data = futures['auto_inc'].result()
            if 'slow' in futures:
                slow_logs = futures['slow'].result()
            if 'session' in futures:
                session_info = futures['session'].result()
            if 'alert' in futures:
                alert_history = futures['alert'].result()
            if 'alert_rules' in futures:
                alert_rules = futures['alert_rules'].result()

        items_count = len(slow_logs.get('Items', {}).get('SQLSlowLog', [])) if slow_logs else 0
        print(f'  ✅ Data collection complete ({items_count} slow logs)')

        das_config = None
        if 'essd' in cluster_info.get('StorageType', '').lower():
            das_config = call_cli('polardb', 'describe-das-config', region,
                                  **{'db-cluster-id': cluster_id})

        fmt = args.format
        report, data = generate_report(cluster_id, region, cluster_info, version_info,
                                       resource_usage, nodes, space_data, slow_logs,
                                       fmt=fmt, param_max_conn=param_max_conn,
                                       auto_inc_data=auto_inc_data, session_info=session_info,
                                       alert_history=alert_history, alert_rules=alert_rules,
                                       das_config=das_config, proxy_perf=proxy_perf)
        print(report)

        ext = '.html' if fmt == 'html' else '.md' if fmt == 'markdown' else '.txt'
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        if args.output:
            output_path = os.path.abspath(args.output)
            if os.path.isdir(output_path) or (not os.path.splitext(output_path)[1] and not output_path.endswith(ext)):
                os.makedirs(output_path, exist_ok=True)
                output_path = os.path.join(output_path, f'{cluster_id}_health_report_{timestamp}{ext}')
            elif not output_path.endswith(ext):
                output_path += ext
        else:
            output_path = os.path.join(os.path.expanduser('~/Downloads'),
                                       f'{cluster_id}_health_report_{timestamp}{ext}')
        output_dir_path = os.path.dirname(output_path)
        if output_dir_path and not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'\n📄 Report saved: {output_path}')
        return

    # Batch mode: multiple clusters → directory with index.html
    fmt = 'html' if len(clusters) > 1 else args.format
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    if args.output:
        output_dir = args.output
    else:
        base_dir = os.path.expanduser('~/Downloads')
        output_dir = os.path.join(base_dir, f'polardb_mysql_health_inspect_report_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)

    print('┌' + '─' * 50 + '┐')
    print('│  PolarDB MySQL Batch Inspection                  │')
    print('└' + '─' * 50 + '┘')
    print(f'  Instance count: {len(clusters)}')
    print(f'  Output directory: {output_dir}')
    if _CLI_PROFILE:
        print(f'  Profile: {_CLI_PROFILE}')
    print()

    def _do_inspect(cluster):
        cid = cluster['cluster_id']
        r = cluster.get('region')
        _, _, summary = inspect_single_cluster(cid, r, output_dir, fmt=fmt)
        return summary

    summaries = [_do_inspect(c) for c in clusters]

    inspect_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if len(summaries) > 1:
        index_path = render_summary_html(summaries, output_dir, inspect_time)
        print(f'\n{"="*60}')
        print(f'📊 Summary report: {index_path}')
        print(f'   {len(summaries)} instances inspection completed')
        danger_n = sum(1 for s in summaries if any(item[0] == 'danger' for item in s.get('suggestions', [])))
        warn_n = sum(1 for s in summaries if not any(item[0] == 'danger' for item in s.get('suggestions', [])) and any(item[0] == 'warn' for item in s.get('suggestions', [])))
        print(f'   🔴 {danger_n} critical  🟡 {warn_n} warning  🟢 {len(summaries) - danger_n - warn_n} normal')
    else:
        print(f'\n📄 Report directory: {output_dir}')


if __name__ == '__main__':
    main()
