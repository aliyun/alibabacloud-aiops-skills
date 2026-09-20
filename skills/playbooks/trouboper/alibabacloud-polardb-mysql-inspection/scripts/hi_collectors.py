"""PolarDB MySQL 健康巡检 - 数据采集函数"""
import json
import sys
import os
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import hi_config as config
from hi_config import call_cli, REGIONS
from hi_utils import _node_role_short


def find_region(cluster_id):
    print(f'🔍 查找集群 {cluster_id} 所在 Region...')
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
        return call_cli(product, action, region, **{**extra, 'start-time': s, 'end-time': e, 'interval': '60'})

    with ThreadPoolExecutor(max_workers=7) as pool:
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

    perf_cluster = _cp('PolarDBCPU,PolarDBMemory,PolarDBDiskUsage,PolarDBInnoDBDataReadWrite,PolarDBConnections')

    results['cluster']['cpu'] = calc_avg_peak(extract_metric_values(perf_cluster, 'cpu_ratio'))
    results['cluster']['memory'] = calc_avg_peak(extract_metric_values(perf_cluster, 'mem_ratio'))
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

    read_vals = extract_metric_values(perf_cluster, 'mean_innodb_data_read')
    write_vals = extract_metric_values(perf_cluster, 'mean_innodb_data_written')
    if read_vals and write_vals:
        combined = [r + w for r, w in zip(read_vals, write_vals)]
        results['cluster']['io'] = calc_avg_peak(combined)
    else:
        results['cluster']['io'] = (0.0, 0.0)

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

    with ThreadPoolExecutor(max_workers=len(nodes)) as pool:
        futures = [pool.submit(_fetch_node, node) for node in nodes]
        for f in as_completed(futures):
            node_id, node_data, node_ts = f.result()
            if node_id:
                results['nodes'][node_id] = node_data
                results['node_ts'][node_id] = node_ts

    return results


def get_disk_usage_trend(cluster_id, region, start_time, end_time):
    """Lightweight disk-only trend collection (PolarDBDiskUsage).

    Returns the same cluster_ts['disk'] / cluster_ts['disk_detail'] structure
    as get_resource_usage(), but skips CPU/Memory/Connections/IO metrics.
    Used when --item space is selected without --item resource.
    """
    perf = _call_perf_daily('polardb', 'describe-db-cluster-performance',
                            region, start_time, end_time,
                            **{'db-cluster-id': cluster_id, 'key': 'PolarDBDiskUsage'})
    cluster_ts = {}
    cluster_ts['disk'] = extract_metric_timeseries(perf, 'mean_data_size')

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
    cluster_ts['disk_detail'] = {}
    for label, metric in disk_detail_map.items():
        ts = extract_metric_timeseries(perf, metric)
        if ts:
            cluster_ts['disk_detail'][label] = ts

    return cluster_ts


def get_proxy_performance(cluster_id, region, nodes, start_time, end_time):
    print('📡 Proxy 监控...', end=' ', flush=True)
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

    with ThreadPoolExecutor(max_workers=len(nodes)) as pool:
        futures = [pool.submit(_fetch_proxy_node, node) for node in nodes]
        for f in as_completed(futures):
            label, ts = f.result()
            if label and ts:
                proxy_ts['node_conns'][label] = ts

    print('✅')
    return proxy_ts


def get_space_top20(cluster_id):
    print('💾 空间分析...', end='', flush=True)
    create_resp = call_cli('das', 'create-storage-analysis-task',
                           endpoint='das.cn-shanghai.aliyuncs.com',
                           **{'instance-id': cluster_id})
    if not create_resp:
        print(' ❌ 创建失败')
        return None

    task_data = create_resp.get('Data', {})
    if not task_data.get('CreateTaskSuccess'):
        print(' ❌ 任务未成功')
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
    print(' ⚠️ 超时')
    return None


def get_slow_logs(cluster_id, region):
    data = call_cli('polardb', 'describe-slow-logs', region,
                    **{'db-cluster-id': cluster_id,
                       'start-time': (datetime.now(timezone.utc) - timedelta(days=config._INSPECT_DAYS)).strftime('%Y-%m-%dZ'),
                       'end-time': datetime.now(timezone.utc).strftime('%Y-%m-%dZ'),
                       'biz-region-id': region})
    return data


def get_max_connections_from_params(cluster_id, region):
    print('🔧 实例参数...', end=' ', flush=True)
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
    print('⚠️ 未找到')
    return None


def get_alert_history(cluster_id, start_time, end_time):
    print('🔔 报警历史...', end='', flush=True)
    start_ms = int(datetime.strptime(start_time, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end_time, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp() * 1000)
    all_logs = []
    page = 1
    while True:
        result = call_cli('cms', 'describe-alert-log-list',
                          **{'start-time': str(start_ms), 'end-time': str(end_ms),
                             'page-size': '100', 'page-number': str(page)})
        if not result:
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
        if '通道沉默' in status_text or 'channel_silence' in send_status.lower():
            continue
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
    print(f' ✅ ({len(filtered)} 条)')
    return filtered


def get_auto_increment_usage(cluster_id):
    print('🔢 自增主键...', end='', flush=True)
    result = call_cli('das', 'get-auto-increment-usage-statistic',
                      endpoint='das.cn-shanghai.aliyuncs.com',
                      **{'instance-id': cluster_id,
                         'real-time': 'false',
                         'ratio-filter': '0'})
    if not result or result.get('Code') != 200:
        print(' ⚠️ 失败')
        return None
    data = result.get('Data', {})
    items = data.get('AutoIncrementUsageList', data.get('Items', []))
    print(f' ✅ ({len(items)} 张表)')
    return items


def _fetch_node_session(cluster_id, node_id=None):
    params = {'instance-id': cluster_id}
    if node_id:
        params['node-id'] = node_id
    result = call_cli('das', 'get-mysql-all-session-async',
                      endpoint='das.cn-shanghai.aliyuncs.com', **params)
    if not result or result.get('Code') != 200:
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
    print('🔗 会话信息...', end='', flush=True)
    if not nodes:
        sd = _fetch_node_session(cluster_id)
        if sd:
            total = sd.get('TotalSessionCount', 0)
            active = sd.get('ActiveSessionCount', 0)
            print(f' ✅ (总{total}/活跃{active})')
            return {'nodes': {'primary': sd}}
        print(' ⚠️ 失败')
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
        print(f' ✅ ({len(all_nodes)}节点, 总{total}/活跃{active})')
        return {'nodes': all_nodes}
    print(' ⚠️ 失败')
    return None
