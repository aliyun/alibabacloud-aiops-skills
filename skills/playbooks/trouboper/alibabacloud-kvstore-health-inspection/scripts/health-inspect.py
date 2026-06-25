#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alibaba Cloud Redis (KVStore) Instance Health Inspection Script
Performs resource usage inspection via aliyun CLI calling R-kvstore API

Usage:
    python3 health-inspect.py <instance_id> [options]

Examples:
    python3 health-inspect.py r-bp1xxxxxxxxxxxx
    python3 health-inspect.py r-bp1xxxxxxxxxxxx --region cn-hangzhou
    python3 health-inspect.py r-bp1xxxxxxxxxxxx --profile myprofile --output ./report
    python3 health-inspect.py --all --days 3
"""

import subprocess
import json
import sys
import os
import time
import re
import uuid
import argparse
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

_CLI_PROFILE = None
_INSPECT_DAYS = 7
_last_cli_error = ''

# Observability (SA-2.11): per-command --user-agent with full UA template.
# UA format (full, single literal below):
#   AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/<session-id>
# - 'alibabacloud-kvstore-health-inspection' is the explicit skill name (NOT a placeholder).
# - <session-id> is a 32-char lowercase hex (UUID v4 without dashes).
SKILL_NAME = 'alibabacloud-kvstore-health-inspection'
_SKILL_SESSION_ID = (
    os.environ.get('ALICLOUD_SKILL_SESSION_ID')
    or uuid.uuid4().hex
)
os.environ.setdefault('ALICLOUD_SKILL_SESSION_ID', _SKILL_SESSION_ID)
# Full UA literal: only the session-id is interpolated; skill name is hard-coded.
SKILL_USER_AGENT = f'AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/{_SKILL_SESSION_ID}'

ALL_ITEMS = ['resource', 'session', 'bigkey', 'slowlog', 'alert']
_INSPECT_ITEMS = set(ALL_ITEMS)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'config')


def load_metrics_config():
    """Load metrics configuration from config/metrics.json."""
    config_path = os.path.join(CONFIG_DIR, 'metrics.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f'Warning: Failed to load metrics config: {e}', file=sys.stderr)
        return None


METRICS_CONFIG = load_metrics_config()


def _sync_after_install():
    """Flush filesystem caches after plugin installation."""
    try:
        subprocess.run(['sync'], capture_output=True, text=True, timeout=10)
    except Exception:
        pass
    time.sleep(1)


def ensure_cli_plugins():
    """Ensure required aliyun CLI plugins are installed."""
    try:
        subprocess.run(['aliyun', 'configure', 'set', '--auto-plugin-install', 'true'],
                       capture_output=True, text=True, timeout=10)
    except Exception:
        pass
    required_plugins = ['r-kvstore', 'cms', 'das']
    for plugin in required_plugins:
        try:
            result = subprocess.run(['aliyun', 'plugin', 'list'],
                                    capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and f'aliyun-cli-{plugin}' not in result.stdout:
                print(f'  Installing CLI plugin: {plugin}...', end='', flush=True)
                install = subprocess.run(
                    ['aliyun', 'plugin', 'install', '--name', f'aliyun-cli-{plugin}'],
                    capture_output=True, text=True, timeout=60)
                if install.returncode == 0:
                    print(' done', flush=True)
                    _sync_after_install()
                else:
                    print(f' warning ({(install.stderr or install.stdout or "unknown").strip()[:100]})', flush=True)
        except Exception:
            pass


_ALLOWED_ACTIONS = frozenset({
    'r-kvstore:describe-instances',
    'r-kvstore:describe-instance-attribute',
    'r-kvstore:describe-engine-version',
    'r-kvstore:describe-history-monitor-values',
    'r-kvstore:describe-logic-instance-topology',
    'r-kvstore:describe-slow-log-records',
    'das:describe-hot-big-keys',
    'das:get-redis-all-session',
    'cms:describe-alert-log-list',
    'cms:describe-metric-rule-list',
})


def call_cli(product, action, region=None, **kwargs):
    """Call aliyun CLI with retry and error handling."""
    global _last_cli_error
    _last_cli_error = ''
    action_key = f'{product}:{action}'
    if action_key not in _ALLOWED_ACTIONS:
        _last_cli_error = f'blocked: {action_key} not in read-only allowlist'
        return None
    cmd = ['aliyun', product, action]
    # SA-2.11: per-command UA with session-id
    cmd.extend(['--user-agent', SKILL_USER_AGENT])
    if _CLI_PROFILE:
        cmd.extend(['--profile', _CLI_PROFILE])
    if region:
        cmd.extend(['--region', region])
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
                    _last_cli_error = f'invalid JSON: {(result.stdout or "").strip()[:200]}'
            else:
                stderr = result.stderr.strip()
                throttled = any(k in stderr for k in ('Throttling', 'throttl', 'Too Many', 'Busy'))
                if not throttled:
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
    'cn-hongkong', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3',
    'ap-southeast-5', 'ap-southeast-6', 'ap-southeast-7',
    'ap-northeast-1', 'ap-northeast-2',
    'us-west-1', 'us-east-1',
    'eu-west-1', 'eu-central-1', 'me-east-1', 'me-central-1',
    'ap-south-1',
]


def find_region(instance_id):
    """Discover instance region by iterating all regions."""
    print(f'Discovering region for instance {instance_id}...')
    for region in REGIONS:
        data = call_cli('r-kvstore', 'describe-instance-attribute',
                        region, **{'instance-id': instance_id})
        if data and data.get('Instances', {}).get('DBInstanceAttribute'):
            attrs = data['Instances']['DBInstanceAttribute']
            if attrs:
                actual_region = attrs[0].get('RegionId', region)
                print(f'   Region: {actual_region}')
                return actual_region
    return None


def get_instance_info(instance_id, region):
    """Get instance attribute information."""
    data = call_cli('r-kvstore', 'describe-instance-attribute',
                    region, **{'instance-id': instance_id})
    if data and data.get('Instances', {}).get('DBInstanceAttribute'):
        return data['Instances']['DBInstanceAttribute'][0]
    return None


def get_engine_version(instance_id, region):
    """Get engine version details (major, minor, proxy version)."""
    data = call_cli('r-kvstore', 'describe-engine-version',
                    region, **{'instance-id': instance_id})
    if not data:
        return None
    return {
        'major_version': data.get('MajorVersion', ''),
        'minor_version': data.get('MinorVersion', ''),
        'latest_minor_version': (data.get('DBLatestMinorVersion') or {}).get('MinorVersion', ''),
        'is_latest_version': data.get('IsLatestVersion', False),
        'enable_upgrade_minor': data.get('EnableUpgradeMinorVersion', False),
        'enable_upgrade_major': data.get('EnableUpgradeMajorVersion', False),
        'proxy_minor_version': data.get('ProxyMinorVersion', ''),
        'proxy_latest_minor_version': (data.get('ProxyLatestMinorVersion') or {}).get('MinorVersion', ''),
    }


def get_topology(instance_id, region):
    """Get cluster topology (for cluster/splitrw architecture)."""
    data = call_cli('r-kvstore', 'describe-logic-instance-topology',
                    region, **{'instance-id': instance_id})
    return data


def get_architecture_type(instance_info):
    """Determine architecture type from instance info."""
    arch = instance_info.get('ArchitectureType', 'standard')
    if METRICS_CONFIG:
        mapping = METRICS_CONFIG.get('architecture_mapping', {})
        return mapping.get(arch, 'standard')
    return arch.lower()


def get_instance_type(instance_info):
    """Detect instance type (pena/essd/regular).

    Priority: Engine field (most reliable) -> RealInstanceClass -> InstanceClass.
    InstanceClass may return a logical template (e.g. tair.pdb.cluster.sharding.common.ce)
    while RealInstanceClass holds the real SKU (e.g. tair.localssd.c1m8.*).
    """
    if not METRICS_CONFIG:
        return 'regular'
    engine = (instance_info.get('Engine', '') or '').lower()
    engine_map = {
        'tair_essd': 'essd',
        'tair_pena': 'pena',
        'tair_scm': 'pena',
        'tair_pmem': 'pena',
    }
    if engine in engine_map:
        return engine_map[engine]
    candidates = [
        (instance_info.get('RealInstanceClass', '') or '').lower(),
        (instance_info.get('InstanceClass', '') or '').lower(),
    ]
    detection = METRICS_CONFIG.get('instance_type_detection', {})
    for inst_type, prefixes in detection.items():
        for prefix in prefixes:
            for cls in candidates:
                if cls and cls.startswith(prefix):
                    return inst_type
    return 'regular'


def get_instance_type_extra_metrics(inst_type):
    """Get extra metrics for specific instance types (pena/essd)."""
    if not METRICS_CONFIG or inst_type == 'regular':
        return {}
    type_metrics = METRICS_CONFIG.get('instance_type_metrics', {})
    result = {}
    for metric_name, info in type_metrics.get(inst_type, {}).items():
        if isinstance(info, dict):
            result[metric_name] = info.get('key', '')
        else:
            result[metric_name] = info
    return result


def get_monitor_keys(inst_type=None):
    """Get the base monitor keys list for DB nodes.

    If inst_type is provided and there is a per-type override in metrics config,
    return the type-specific keys (e.g. essd / pena).
    """
    if METRICS_CONFIG and inst_type:
        type_keys = METRICS_CONFIG.get('instance_type_monitor_keys', {}).get(inst_type)
        if type_keys:
            return list(type_keys)
    if METRICS_CONFIG and 'monitor_keys' in METRICS_CONFIG:
        return METRICS_CONFIG['monitor_keys']
    return ['CpuUsage', 'MemoryUsage', 'ConnectionUsage', 'IntranetInRatio', 'IntranetOutRatio']


def get_proxy_monitor_keys():
    """Get the monitor keys list for proxy nodes."""
    if METRICS_CONFIG and 'proxy_monitor_keys' in METRICS_CONFIG:
        return METRICS_CONFIG['proxy_monitor_keys']
    return ['CpuUsage', 'UsedConnection', 'IntranetIn', 'IntranetOut', 'AvgRt']


def get_topology_nodes(instance_id, region):
    """Get DB and Proxy node IDs from cluster topology."""
    data = get_topology(instance_id, region)
    if not data:
        return {'db_nodes': [], 'proxy_nodes': [], 'db_node_details': [], 'proxy_node_details': []}
    db_nodes = []
    proxy_nodes = []
    db_node_details = []
    proxy_node_details = []
    shard_list = data.get('RedisShardList', {}).get('NodeInfo', [])
    for node in shard_list:
        node_id = node.get('NodeId', '')
        if node_id and node.get('NodeType') == 'db':
            db_nodes.append(node_id)
            cap_mb = int(node.get('Capacity', 0) or 0)
            mem_gb = round(cap_mb / 1024, 1) if cap_mb >= 1024 else cap_mb
            mem_str = f'{mem_gb} GB' if cap_mb >= 1024 else f'{mem_gb} MB'
            db_node_details.append({
                'node_id': node_id.split('#')[0],
                'memory': mem_str,
                'bandwidth': node.get('Bandwidth', 0),
                'connection': node.get('Connection', 0),
                'role': node.get('SubInstanceType', 'master'),
            })
    proxy_list = data.get('RedisProxyList', {}).get('NodeInfo', [])
    for node in proxy_list:
        node_id = node.get('NodeId', '')
        if node_id:
            proxy_nodes.append(node_id)
            proxy_node_details.append({
                'node_id': node_id,
                'connection': 120000,
            })
    return {'db_nodes': db_nodes, 'proxy_nodes': proxy_nodes,
            'db_node_details': db_node_details, 'proxy_node_details': proxy_node_details}


def get_history_monitor_values(instance_id, region, monitor_keys, start_time, end_time, node_id=None):
    """Fetch historical monitor values for given keys."""
    keys_str = ','.join(monitor_keys) if isinstance(monitor_keys, list) else monitor_keys
    params = {
        'instance-id': instance_id,
        'start-time': start_time,
        'end-time': end_time,
        'monitor-keys': keys_str,
        'interval-for-history': '01m',
    }
    if node_id:
        params['node-id'] = node_id
    data = call_cli('r-kvstore', 'describe-history-monitor-values', region, **params)
    return data


# Map a query key to the field name actually present in the API response payload.
# Used only for parsing API response.
_MONITOR_KEY_RESPONSE_MAP = {
    'MemoryUsage': 'memoryUsage',
    'ConnectionUsage': 'connectionUsage',
    'IntranetInRatio': 'intranetInRatio',
    'IntranetOutRatio': 'intranetOutRatio',
    'IntranetIn': 'InFlow',
    'IntranetOut': 'OutFlow',
    'Tair_PmemUsage': 'PmemUsage',
    'Tair_Disk_Monitor': 'iops_usage',
    'DiskUsage': 'disk_usage',
    # Proxy: query key is 'UsedConnection' (API-recognized), but we want
    # the percentage field 'ConnectionUsage' from the response (not the
    # absolute count 'UsedConnection') for unified % rendering.
    'UsedConnection': 'ConnectionUsage',
}

# Rename query key -> result dict key (for unifying naming across roles).
# Proxy queries 'UsedConnection' but we store the result under 'ConnectionUsage'
# so the chart/table rendering pipeline can treat it uniformly.
_RESULT_KEY_RENAME = {
    'UsedConnection': 'ConnectionUsage',
}


def parse_monitor_values(data, key_name):
    """Parse monitor values from API response into time-series list."""
    if not data:
        return []
    monitor_history = data.get('MonitorHistory', '')
    if not monitor_history:
        return []
    try:
        history_list = json.loads(monitor_history) if isinstance(monitor_history, str) else monitor_history
    except json.JSONDecodeError:
        return []
    possible_keys = []
    if key_name in _MONITOR_KEY_RESPONSE_MAP:
        possible_keys.append(_MONITOR_KEY_RESPONSE_MAP[key_name])
    possible_keys.append(key_name)
    alt = key_name[0].lower() + key_name[1:] if key_name else ''
    if alt not in possible_keys:
        possible_keys.append(alt)
    values = []
    if isinstance(history_list, dict):
        for ts, metrics in history_list.items():
            try:
                if not isinstance(metrics, dict):
                    continue
                val_str = ''
                for k in possible_keys:
                    if k in metrics:
                        val_str = metrics[k]
                        break
                if val_str == '' or val_str is None:
                    continue
                if '#' in str(val_str):
                    parts = [p for p in str(val_str).split('#') if p]
                    val = max(float(p) for p in parts) if parts else 0.0
                else:
                    val = float(val_str)
                values.append({'timestamp': ts, 'value': val})
            except (ValueError, TypeError):
                continue
    else:
        for entry in history_list:
            try:
                val_str = ''
                for k in possible_keys:
                    if k in entry:
                        val_str = entry[k]
                        break
                if val_str == '' or val_str is None:
                    continue
                if '#' in str(val_str):
                    parts = [p for p in str(val_str).split('#') if p]
                    val = max(float(p) for p in parts) if parts else 0.0
                else:
                    val = float(val_str)
                ts = entry.get('date', '')
                values.append({'timestamp': ts, 'value': val})
            except (ValueError, TypeError):
                continue
    return values


def calc_avg_peak(values):
    """Calculate average and peak from value list."""
    if not values:
        return 0.0, 0.0
    nums = [v['value'] for v in values]
    return round(sum(nums) / len(nums), 2), round(max(nums), 2)


def _query_node_metrics(instance_id, region, monitor_keys, start_time, end_time, node_id=None):
    """Query metrics for a single node, return parsed results."""
    keys_str = ','.join(monitor_keys)
    data = get_history_monitor_values(instance_id, region, keys_str, start_time, end_time, node_id)
    results = {}
    for key in monitor_keys:
        values = parse_monitor_values(data, key)
        avg, peak = calc_avg_peak(values)
        # Rename result key when needed (e.g. UsedConnection -> ConnectionUsage)
        result_key = _RESULT_KEY_RENAME.get(key, key)
        results[result_key] = {'avg': avg, 'peak': peak, 'values': values, 'monitor_key': result_key}
    return results


def _merge_node_results(all_node_results, monitor_keys):
    """Merge results from multiple nodes: take max peak and max avg across nodes."""
    merged = {}
    for key in monitor_keys:
        # Rename result key when needed (e.g. UsedConnection -> ConnectionUsage)
        result_key = _RESULT_KEY_RENAME.get(key, key)
        max_avg = 0.0
        max_peak = 0.0
        for node_result in all_node_results:
            node_data = node_result.get(result_key, {})
            if not node_data:
                continue
            max_avg = max(max_avg, node_data.get('avg', 0.0))
            max_peak = max(max_peak, node_data.get('peak', 0.0))
        best_values = []
        for node_result in all_node_results:
            node_data = node_result.get(result_key, {})
            if node_data.get('peak', 0.0) == max_peak and node_data.get('values'):
                best_values = node_data['values']
                break
        merged[result_key] = {'avg': max_avg, 'peak': max_peak, 'values': best_values, 'monitor_key': result_key}
    return merged


def get_resource_usage(instance_id, region, arch_type, start_time, end_time, extra_metrics=None, inst_type=None):
    """Collect resource usage: concurrently query all nodes for cluster/splitrw."""
    monitor_keys = get_monitor_keys(inst_type)
    results = {}
    node_details = {}  # 存储每个节点的独立数据

    if arch_type == 'standard':
        print(f'Fetching monitor data (standard)...', end='', flush=True)
        results = _query_node_metrics(instance_id, region, monitor_keys, start_time, end_time)
        print(' done')
    else:
        print(f'Getting topology ({arch_type})...', end='', flush=True)
        topo = get_topology_nodes(instance_id, region)
        db_nodes = topo['db_nodes']
        proxy_nodes = topo['proxy_nodes']
        print(f' {len(db_nodes)} DB nodes, {len(proxy_nodes)} Proxy nodes')

        if db_nodes:
            print(f'Fetching DB node metrics ({len(db_nodes)} nodes)...', end='', flush=True)
            db_results = {}
            with ThreadPoolExecutor(max_workers=min(len(db_nodes), 8)) as executor:
                futures = {
                    executor.submit(_query_node_metrics, instance_id, region, monitor_keys, start_time, end_time, nid): nid
                    for nid in db_nodes
                }
                for future in as_completed(futures):
                    nid = futures[future]
                    try:
                        db_results[nid] = future.result()
                    except Exception:
                        pass
            # 保存每个节点的独立数据
            node_details['db_nodes'] = db_results
            # 合并结果（取最大值）
            results = _merge_node_results(list(db_results.values()), monitor_keys)
            print(' done')

        if proxy_nodes:
            print(f'Fetching Proxy node metrics ({len(proxy_nodes)} nodes)...', end='', flush=True)
            proxy_monitor_keys = get_proxy_monitor_keys()
            proxy_results = {}
            with ThreadPoolExecutor(max_workers=min(len(proxy_nodes), 8)) as executor:
                futures = {
                    executor.submit(_query_node_metrics, instance_id, region, proxy_monitor_keys, start_time, end_time, nid): nid
                    for nid in proxy_nodes
                }
                for future in as_completed(futures):
                    nid = futures[future]
                    try:
                        proxy_results[nid] = future.result()
                    except Exception:
                        pass
            # 保存每个节点的独立数据
            node_details['proxy_nodes'] = proxy_results
            # 合并结果
            proxy_merged = _merge_node_results(list(proxy_results.values()), proxy_monitor_keys)
            for key, data in proxy_merged.items():
                results[f'proxy_{key}'] = data
            print(' done')

    if extra_metrics:
        extra_key_values = list(extra_metrics.values())
        print(f'Fetching instance-type metrics...', end='', flush=True)
        # For cluster/splitrw: query extra metrics per DB node so they can be
        # rendered as multi-line charts (one line per shard) like the regular
        # metrics. For standard: keep instance-level single query.
        if arch_type != 'standard' and node_details.get('db_nodes'):
            db_nodes_list = list(node_details['db_nodes'].keys())
            per_node_extra = {}
            with ThreadPoolExecutor(max_workers=min(len(db_nodes_list), 8)) as executor:
                futures = {
                    executor.submit(_query_node_metrics, instance_id, region, extra_key_values, start_time, end_time, nid): nid
                    for nid in db_nodes_list
                }
                for future in as_completed(futures):
                    nid = futures[future]
                    try:
                        per_node_extra[nid] = future.result()
                    except Exception:
                        per_node_extra[nid] = {}
            # Merge per-node extras: rename monitor_key -> metric_name and
            # attach to node_details['db_nodes'][nid] so chart rendering can
            # produce multi-line series keyed by metric_name.
            for nid, node_extra in per_node_extra.items():
                target = node_details['db_nodes'].setdefault(nid, {})
                for metric_name, monitor_key in extra_metrics.items():
                    if monitor_key in node_extra:
                        target[metric_name] = node_extra[monitor_key]
            # Aggregate across nodes for table/summary view (max peak/avg).
            merged_extra = _merge_node_results(list(per_node_extra.values()), extra_key_values)
            # Safety net: if per-node query returned no data points at all
            # (e.g. API does not accept node_id for these metrics), fall back
            # to instance-level query so the chart can still render single-line.
            any_data = any(
                merged_extra.get(mk, {}).get('values')
                for mk in extra_key_values
            )
            if not any_data:
                # Drop empty per-node entries so chart renderer falls back to single-line.
                for nid in list(node_details['db_nodes'].keys()):
                    for metric_name in extra_metrics.keys():
                        node_details['db_nodes'][nid].pop(metric_name, None)
                extra_data = _query_node_metrics(instance_id, region, extra_key_values, start_time, end_time)
                for metric_name, monitor_key in extra_metrics.items():
                    if monitor_key in extra_data:
                        results[metric_name] = extra_data[monitor_key]
            else:
                for metric_name, monitor_key in extra_metrics.items():
                    if monitor_key in merged_extra:
                        results[metric_name] = merged_extra[monitor_key]
        else:
            extra_data = _query_node_metrics(instance_id, region, extra_key_values, start_time, end_time)
            for metric_name, monitor_key in extra_metrics.items():
                if monitor_key in extra_data:
                    results[metric_name] = extra_data[monitor_key]
        print(' done')

    # 返回合并结果和节点详情
    return results, node_details if node_details else None


def discover_all_instances(region=None):
    """Discover all Redis instances (optionally filtered by region)."""
    print('Discovering all Redis instances...', flush=True)
    all_instances = []
    search_regions = [region] if region else REGIONS

    seen_ids = set()
    for r in search_regions:
        page = 1
        while True:
            data = call_cli('r-kvstore', 'describe-instances', r,
                            **{'page-size': '50', 'page-number': str(page)})
            if not data:
                break
            instances = data.get('Instances', {}).get('KVStoreInstance', [])
            if not instances:
                break
            for inst in instances:
                iid = inst.get('InstanceId', '')
                if iid in seen_ids:
                    continue
                seen_ids.add(iid)
                all_instances.append({
                    'instance_id': iid,
                    'region': inst.get('RegionId', r),
                    'name': inst.get('InstanceName', ''),
                    'status': inst.get('InstanceStatus', ''),
                    'architecture': inst.get('ArchitectureType', 'standard'),
                    'instance_class': inst.get('InstanceClass', ''),
                    'engine_version': inst.get('EngineVersion', ''),
                })
            total = data.get('TotalCount', 0)
            if page * 50 >= total or len(instances) < 50:
                break
            page += 1

    print(f'   Found {len(all_instances)} instances')
    return all_instances


def get_redis_all_session(instance_id):
    """Get Redis instance current sessions via DAS GetRedisAllSession API."""
    das_region = 'cn-shanghai'
    result = call_cli('das', 'get-redis-all-session', das_region,
                      **{'instance-id': instance_id})
    if not result:
        return None
    if result.get('Code') != 200 and result.get('Code') != '200':
        return None
    data = result.get('Data', {})
    if not data:
        return None
    sessions = data.get('Sessions', [])
    source_stats = data.get('SourceStats', [])
    return {
        'total': data.get('Total', len(sessions)),
        'sessions': sessions,
        'source_stats': source_stats,
        'timestamp': data.get('Timestamp', 0),
    }


def get_session_info(instance_id, region, arch_type, resource_data=None, instance_info=None):
    """Get current session/connection info for the instance."""
    print('Session info...', end=' ', flush=True)
    session = {'connections': {}, 'total_connections': 0, 'max_connections': 0}

    # Max connections from instance info
    if instance_info:
        session['max_connections'] = instance_info.get('Connections', 0)

    if resource_data:
        conn_data = resource_data.get('ConnectionUsage', {})
        if conn_data:
            session['connection_usage_avg'] = conn_data.get('avg', 0)
            session['connection_usage_peak'] = conn_data.get('peak', 0)
            # Estimate used connections from peak usage
            if session.get('max_connections'):
                session['used_connections_peak'] = int(session['max_connections'] * conn_data.get('peak', 0) / 100)
        proxy_conn = resource_data.get('proxy_ConnectionUsage', {})
        if proxy_conn:
            session['proxy_connection_usage_avg'] = proxy_conn.get('avg', 0)
            session['proxy_connection_usage_peak'] = proxy_conn.get('peak', 0)

    if arch_type in ('cluster', 'splitrw'):
        topo = get_topology_nodes(instance_id, region)
        session['db_node_count'] = len(topo.get('db_nodes', []))
        session['proxy_node_count'] = len(topo.get('proxy_nodes', []))
        session['db_node_details'] = topo.get('db_node_details', [])
        session['proxy_node_details'] = topo.get('proxy_node_details', [])
    else:
        session['db_node_count'] = 1
        session['proxy_node_count'] = 0

    # Fetch real-time sessions via DAS API
    real_sessions = get_redis_all_session(instance_id)
    if real_sessions:
        session['real_sessions'] = real_sessions
        session['total_connections'] = real_sessions.get('total', 0)

    print('done')
    return session


def get_big_hot_keys(instance_id, region):
    """Get real-time big key and hot key via DAS DescribeHotBigKeys API."""
    print('Big/Hot key analysis...', end='', flush=True)
    result = {'big_keys': [], 'hot_keys': [], 'large_keys': [], 'high_traffic_keys': []}

    das_region = 'cn-shanghai'
    params = {'instance-id': instance_id}
    report = call_cli('das', 'describe-hot-big-keys', das_region, **params)
    if not report:
        print(f' warning ({_last_cli_error})')
        return result

    data = report.get('Data', {})

    big_keys_data = data.get('BigKeys', {}).get('BigKey', [])
    for key_info in big_keys_data:
        result['big_keys'].append({
            'db': key_info.get('Db', 0),
            'key': key_info.get('Key', ''),
            'type': key_info.get('KeyType', ''),
            'size': key_info.get('Size', 0),
            'node_id': key_info.get('NodeId', ''),
        })

    large_keys_data = data.get('LargeKeys', {}).get('LargeKey', [])
    for key_info in large_keys_data:
        result['large_keys'].append({
            'db': key_info.get('Db', 0),
            'key': key_info.get('Key', ''),
            'type': key_info.get('KeyType', ''),
            'data_size': int(key_info.get('DataSize', 0)),
            'node_id': key_info.get('NodeId', ''),
        })

    hot_keys_data = data.get('HotKeys', {}).get('HotKey', [])
    for key_info in hot_keys_data:
        result['hot_keys'].append({
            'db': key_info.get('Db', 0),
            'key': key_info.get('Key', ''),
            'type': key_info.get('KeyType', ''),
            'hot': key_info.get('Hot', ''),
            'lfu': key_info.get('Lfu', 0),
            'size': key_info.get('Size', 0),
            'node_id': key_info.get('NodeId', ''),
        })

    high_traffic_data = data.get('HighTrafficKeys', {}).get('HighTrafficKey', [])
    for key_info in high_traffic_data:
        result['high_traffic_keys'].append({
            'db': key_info.get('Db', 0),
            'key': key_info.get('Key', ''),
            'type': key_info.get('KeyType', ''),
            'hot': key_info.get('Hot', ''),
            'in_bytes': key_info.get('inBytes', 0),
            'out_bytes': key_info.get('outBytes', 0),
            'size': key_info.get('Size', 0),
            'node_id': key_info.get('NodeId', ''),
        })

    big_count = len(result['big_keys']) + len(result['large_keys'])
    hot_count = len(result['hot_keys']) + len(result['high_traffic_keys'])
    print(f' done ({big_count} big keys, {hot_count} hot keys)')
    return result


def get_slow_logs(instance_id, region):
    """Get slow log records for the last N days."""
    print(f'Slow logs (last {_INSPECT_DAYS} days)...', end='', flush=True)
    now = datetime.now(timezone.utc)
    all_records = []

    for day_offset in range(_INSPECT_DAYS):
        day_end = now - timedelta(days=day_offset)
        day_start = now - timedelta(days=day_offset + 1)
        start_time = day_start.strftime('%Y-%m-%dT%H:%MZ')
        end_time = day_end.strftime('%Y-%m-%dT%H:%MZ')

        page = 1
        while True:
            data = call_cli('r-kvstore', 'describe-slow-log-records', region, **{
                'instance-id': instance_id,
                'start-time': start_time,
                'end-time': end_time,
                'page-size': '50',
                'page-number': str(page),
            })
            if not data:
                break
            items = data.get('Items', {}).get('LogRecords', [])
            if not items:
                break
            all_records.extend(items)
            total = data.get('TotalRecordCount', 0)
            if page * 50 >= total or len(items) < 50:
                break
            page += 1
            if page > 20:
                break

    cmd_stats = {}
    for record in all_records:
        cmd = record.get('Command', 'UNKNOWN')
        elapsed = record.get('ElapsedTime', 0)
        elapsed_ms = elapsed / 1000.0
        key = record.get('Key', '')
        node_id = record.get('NodeId', '')

        if cmd not in cmd_stats:
            cmd_stats[cmd] = {
                'command': cmd,
                'count': 0,
                'total_time_ms': 0.0,
                'max_time_ms': 0.0,
                'sample_key': key,
                'sample_node': node_id,
            }
        cmd_stats[cmd]['count'] += 1
        cmd_stats[cmd]['total_time_ms'] += elapsed_ms
        if elapsed_ms > cmd_stats[cmd]['max_time_ms']:
            cmd_stats[cmd]['max_time_ms'] = elapsed_ms
            cmd_stats[cmd]['sample_key'] = key

    for stats in cmd_stats.values():
        stats['avg_time_ms'] = round(stats['total_time_ms'] / stats['count'], 2) if stats['count'] > 0 else 0
        stats['total_time_ms'] = round(stats['total_time_ms'], 2)
        stats['max_time_ms'] = round(stats['max_time_ms'], 2)

    slow_list = sorted(cmd_stats.values(), key=lambda x: x['total_time_ms'], reverse=True)[:20]
    print(f' done ({len(all_records)} records, {len(cmd_stats)} commands)')
    return {'records': all_records, 'stats': slow_list, 'total_count': len(all_records)}


def get_alert_history(instance_id, start_time, end_time):
    """Get alert history from CloudMonitor CMS."""
    print('Alert history...', end='', flush=True)
    start_ms = int(datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp() * 1000)

    all_logs = []
    page = 1
    while True:
        result = call_cli('cms', 'describe-alert-log-list',
                          **{'start-time': str(start_ms), 'end-time': str(end_ms),
                             'send-status': '0',
                             'page-size': '100', 'page-number': str(page)})
        if not result:
            if page == 1:
                print(f' warning ({_last_cli_error})')
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
        if page > 10:
            break

    filtered = []
    for log in all_logs:
        product = log.get('Product', '').lower()
        namespace = log.get('Namespace', '').lower()
        if 'kvstore' not in product and 'redis' not in product and 'kvstore' not in namespace:
            continue
        dims = {}
        raw_dims = log.get('Dimensions', [])
        if isinstance(raw_dims, list):
            dims = {d.get('Key', ''): d.get('Value', '') for d in raw_dims if isinstance(d, dict)}
        elif isinstance(raw_dims, str):
            try:
                dims = json.loads(raw_dims)
            except (json.JSONDecodeError, TypeError):
                pass
        dim_instance = dims.get('instanceId', '')
        log_instance = log.get('InstanceId', '')
        if instance_id not in dim_instance and instance_id not in log_instance:
            continue

        alert_time = log.get('AlertTime', 0)
        level = log.get('Level', '')
        rule_name = log.get('RuleName', '')
        metric_name = log.get('MetricName', '')
        node_id = dims.get('nodeId', '')

        threshold = ''
        cur_value = ''
        try:
            msg = json.loads(log.get('Message', '{}'))
            esc = msg.get('escalation', {})
            threshold = esc.get('threshold', '')
            fetched = msg.get('fetched', {})
            if fetched:
                cur_value = f'{list(fetched.values())[0]:.1f}' if fetched else ''
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

        filtered.append({
            'time': datetime.fromtimestamp(alert_time / 1000).strftime('%Y-%m-%d %H:%M:%S') if alert_time else '',
            'level': level,
            'rule_name': rule_name,
            'metric': metric_name,
            'node_id': node_id,
            'cur_value': cur_value,
            'threshold': threshold,
            'send_status': log.get('SendStatus', ''),
        })

    filtered.sort(key=lambda x: x['time'], reverse=True)
    print(f' done ({len(filtered)} entries)')
    return filtered


def get_alert_rules(instance_id):
    """Get alert rules from CloudMonitor CMS for kvstore."""
    print('Alert rules...', end='', flush=True)
    all_rules = []
    page = 1
    while True:
        result = call_cli('cms', 'describe-metric-rule-list',
                          **{'namespace': 'acs_kvstore', 'page': str(page), 'page-size': '100'})
        if not result:
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
        # Check if rule applies to all instances or specifically to this instance
        is_all = False
        matches_instance = False
        if isinstance(res_list, list):
            for r in res_list:
                if not isinstance(r, dict):
                    continue
                # _ALL can be in 'resource' or 'instanceId' field
                for v in r.values():
                    if v == '_ALL':
                        is_all = True
                    if v == instance_id:
                        matches_instance = True
        if not is_all and not matches_instance:
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
            'thresholds': thresholds,
            'interval': rule.get('Interval', 60),
            'contact_groups': rule.get('ContactGroups', ''),
        })
    print(f' done ({len(filtered)} rules)')
    return filtered


def status_icon(value):
    """Return status icon based on threshold."""
    if value > 80:
        return '[HIGH]'
    elif value > 60:
        return '[MED]'
    return '[OK]'


def format_suggestions(resource_data, slow_logs=None, big_hot_keys=None, alert_history=None, engine_version=None):
    """Generate suggestions based on all inspection data with cross-dimensional correlation.

    Each suggestion is a tuple: (level, priority, en_text, zh_text)
    - level: 'danger' or 'warn'
    - priority: lower number = higher priority (for sorting)
    - en_text / zh_text: bilingual suggestion text
    """
    suggestions = []

    # Classify alerts by metric/rule for correlation.
    # We classify ALL alert levels (P1-P4 + OK), because lower-level alerts (e.g. P4)
    # may still indicate a misconfigured rule or persistent threshold breach worth surfacing.
    alerts = alert_history or []
    p1p2_alerts = [a for a in alerts if a.get('level') in ('P1', 'P2')]
    def _alert_text(a):
        return ((a.get('metric') or '') + ' ' + (a.get('rule_name') or '')).lower()
    cpu_alerts = [a for a in alerts if 'cpu' in _alert_text(a)]
    mem_alerts = [a for a in alerts
                  if 'memory' in _alert_text(a) or 'mem' in _alert_text(a)]
    conn_alerts = [a for a in alerts if 'conn' in _alert_text(a)]
    bw_alerts = [a for a in alerts
                 if 'bandwidth' in _alert_text(a) or 'intranet' in _alert_text(a)
                 or 'flow' in _alert_text(a)]

    # Track coverage to avoid duplicate suggestions
    alert_covered = False
    slow_covered = False
    bigkey_covered = False
    hotkey_covered = False

    # Prepare big/hot key data
    large_keys = (big_hot_keys or {}).get('large_keys', [])
    big_keys = (big_hot_keys or {}).get('big_keys', [])
    hot_keys = (big_hot_keys or {}).get('hot_keys', [])
    high_traffic_keys = (big_hot_keys or {}).get('high_traffic_keys', [])

    # Prepare slow log data
    slow_total = (slow_logs or {}).get('total_count', 0)
    slow_stats = (slow_logs or {}).get('stats', [])
    top_cmd = slow_stats[0] if slow_stats else None

    # ═══ Priority 0: Memory overflow risk (ticking time bomb) ═══
    mem_data = resource_data.get('MemoryUsage', {})
    mem_peak = mem_data.get('peak', 0)
    if mem_peak > 95:
        parts_en = [f'Memory usage peak {mem_peak:.1f}%, OOM risk exists']
        parts_zh = [f'内存使用率峰值 {mem_peak:.1f}%，存在 OOM 风险']
        if large_keys:
            largest = large_keys[0]
            size_mb = int(largest.get('data_size', 0)) / (1024 * 1024)
            parts_en.append(f'largest key: {largest.get("key", "")[:40]} ({size_mb:.2f}MB)')
            parts_zh.append(f'最大 key: {largest.get("key", "")[:40]}（{size_mb:.2f}MB）')
            bigkey_covered = True
        if mem_alerts:
            parts_en.append(f'triggered {len(mem_alerts)} alerts')
            parts_zh.append(f'触发 {len(mem_alerts)} 次告警')
            alert_covered = True
        text_en = ', '.join(parts_en) + ', recommend analyzing memory usage and cleaning large/expired keys'
        text_zh = '，'.join(parts_zh) + '，建议分析内存使用情况，清理大 key 或过期 key'
        suggestions.append(('danger', 0, text_en, text_zh))
    elif mem_peak > 90:
        parts_en = [f'Memory usage peak {mem_peak:.1f}%, approaching limit']
        parts_zh = [f'内存使用率峰值 {mem_peak:.1f}%，接近上限']
        if large_keys:
            largest = large_keys[0]
            size_mb = int(largest.get('data_size', 0)) / (1024 * 1024)
            parts_en.append(f'{len(large_keys)} large keys detected (largest: {size_mb:.2f}MB)')
            parts_zh.append(f'检测到 {len(large_keys)} 个大 key（最大: {size_mb:.2f}MB）')
            bigkey_covered = True
        text_en = ', '.join(parts_en) + ', recommend planning capacity upgrade or optimizing key sizes'
        text_zh = '，'.join(parts_zh) + '，建议规划扩容或优化 key 大小'
        suggestions.append(('warn', 10, text_en, text_zh))

    # ═══ Priority 1: CPU + Hot Keys correlation ═══
    cpu_data = resource_data.get('CpuUsage', {})
    cpu_peak = cpu_data.get('peak', 0)
    if cpu_peak > 80:
        parts_en = [f'CPU usage peak {cpu_peak:.1f}%']
        parts_zh = [f'CPU 使用率峰值 {cpu_peak:.1f}%']
        if hot_keys:
            hottest = hot_keys[0]
            hk_name = hottest.get('key', '')[:40]
            hk_qps = hottest.get('hot', '')
            parts_en.append(f'correlated with {len(hot_keys)} hot keys (hottest: {hk_name}, QPS {hk_qps})')
            parts_zh.append(f'关联 {len(hot_keys)} 个热 key（最热: {hk_name}，QPS {hk_qps}）')
            hotkey_covered = True
        if cpu_alerts:
            parts_en.append(f'triggered {len(cpu_alerts)} alerts')
            parts_zh.append(f'触发 {len(cpu_alerts)} 次告警')
            alert_covered = True
        if len(parts_en) > 1:
            text_en = ', '.join(parts_en) + ', recommend optimizing hot key access patterns or using local cache'
            text_zh = '，'.join(parts_zh) + '，建议优化热 key 访问模式或使用本地缓存'
        else:
            text_en = parts_en[0] + ', recommend investigating high-cost commands and consider upgrading specs'
            text_zh = parts_zh[0] + '，建议排查高消耗命令，考虑升级规格'
        suggestions.append(('danger', 1, text_en, text_zh))
    elif cpu_peak > 60:
        suggestions.append(('warn', 20, f'CPU usage peak {cpu_peak:.1f}%, load is relatively high, recommend monitoring the trend',
                            f'CPU 使用率峰值 {cpu_peak:.1f}%，负载偏高，建议持续关注趋势'))

    # ═══ Priority 2: Connection + Slow Logs correlation ═══
    conn_data = resource_data.get('ConnectionUsage', {})
    conn_peak = conn_data.get('peak', 0)
    if conn_peak > 80:
        parts_en = [f'Connection usage peak {conn_peak:.1f}%']
        parts_zh = [f'连接使用率峰值 {conn_peak:.1f}%']
        if slow_total > 20:
            cmd_name = top_cmd['command'] if top_cmd else 'UNKNOWN'
            parts_en.append(f'correlated with {slow_total} slow log records (top command: {cmd_name})')
            parts_zh.append(f'关联 {slow_total} 条慢日志（最高频命令: {cmd_name}）')
            slow_covered = True
        if conn_alerts:
            parts_en.append(f'triggered {len(conn_alerts)} alerts')
            parts_zh.append(f'触发 {len(conn_alerts)} 次告警')
            alert_covered = True
        if len(parts_en) > 1:
            text_en = ', '.join(parts_en) + ', recommend investigating slow commands causing connection accumulation'
            text_zh = '，'.join(parts_zh) + '，建议排查慢命令是否导致连接堆积'
        else:
            text_en = parts_en[0] + ', approaching limit, recommend checking connection pool config and investigating connection leaks'
            text_zh = parts_zh[0] + '，接近上限，建议检查连接池配置并排查连接泄漏'
        suggestions.append(('danger', 2, text_en, text_zh))
    elif conn_peak > 60:
        suggestions.append(('warn', 22, f'Connection usage peak {conn_peak:.1f}%, recommend optimizing max connection pool config',
                            f'连接使用率峰值 {conn_peak:.1f}%，建议优化最大连接池配置'))

    # ═══ Priority 2: Bandwidth + Big Keys correlation ═══
    for bw_key, bw_label, bw_label_zh, bw_covered_flag in [
        ('IntranetInRatio', 'Input bandwidth', '入方向带宽', 'bw_in'),
        ('IntranetOutRatio', 'Output bandwidth', '出方向带宽', 'bw_out'),
    ]:
        bw_data = resource_data.get(bw_key, {})
        bw_peak = bw_data.get('peak', 0)
        if bw_peak > 80:
            parts_en = [f'{bw_label} usage peak {bw_peak:.1f}%']
            parts_zh = [f'{bw_label_zh}使用率峰值 {bw_peak:.1f}%']
            if (big_keys or large_keys) and not bigkey_covered:
                bk_count = len(large_keys) + len(big_keys)
                parts_en.append(f'correlated with {bk_count} big keys that may cause high transfer volume')
                parts_zh.append(f'关联 {bk_count} 个大 key，可能导致大量数据传输')
                bigkey_covered = True
            if bw_alerts:
                parts_en.append(f'triggered {len(bw_alerts)} alerts')
                parts_zh.append(f'触发 {len(bw_alerts)} 次告警')
                alert_covered = True
            if len(parts_en) > 1:
                text_en = ', '.join(parts_en) + ', recommend checking big key transfer impact on bandwidth'
                text_zh = '，'.join(parts_zh) + '，建议检查大 key 传输对带宽的影响'
            else:
                text_en = parts_en[0] + ', approaching limit, recommend optimizing data transfer patterns'
                text_zh = parts_zh[0] + '，接近上限，建议优化数据传输模式'
            suggestions.append(('danger', 2, text_en, text_zh))
        elif bw_peak > 60:
            level_label = bw_label if bw_covered_flag == 'bw_in' else bw_label
            level_label_zh = bw_label_zh if bw_covered_flag == 'bw_in' else bw_label_zh
            suggestions.append(('warn', 22, f'{level_label} usage peak {bw_peak:.1f}%, recommend monitoring trend',
                                f'{level_label_zh}使用率峰值 {bw_peak:.1f}%，建议持续关注'))

    # ═══ Proxy metrics ═══
    # Note: proxy IntranetIn/IntranetOut report absolute KB/s without an upper bound,
    # so we cannot derive a generic % threshold. Only CPU/Connection are evaluated.
    proxy_thresholds = {
        'proxy_CpuUsage': ('Proxy CPU Usage', 'Proxy CPU 使用率'),
        'proxy_ConnectionUsage': ('Proxy Connection Usage', 'Proxy 连接使用率'),
    }
    for metric, (en_name, zh_name) in proxy_thresholds.items():
        data = resource_data.get(metric, {})
        if not data:
            continue
        peak = data.get('peak', 0)
        avg = data.get('avg', 0)
        if peak > 90:
            suggestions.append(('danger', 2, f'{en_name} peak {peak:.1f}%, critical level. Immediate attention required.',
                                f'{zh_name}峰值 {peak:.1f}%，已达危险水平，需立即关注'))
        elif peak > 80:
            suggestions.append(('danger', 2, f'{en_name} peak {peak:.1f}%, approaching limit. Recommend scaling up or optimizing.',
                                f'{zh_name}峰值 {peak:.1f}%，接近上限，建议扩容或优化'))
        elif peak > 60:
            suggestions.append(('warn', 22, f'{en_name} peak {peak:.1f}%, relatively high. Recommend monitoring trend.',
                                f'{zh_name}峰值 {peak:.1f}%，偏高，建议持续关注趋势'))
        if avg > 70:
            suggestions.append(('warn', 22, f'{en_name} average {avg:.1f}%, sustained high load. Recommend scaling.',
                                f'{zh_name}均值 {avg:.1f}%，持续高负载，建议扩容'))

    # ═══ Instance-type-specific metrics ═══
    extra_thresholds = {
        'pmem_usage': ('Persistent Memory Usage', '持久内存使用率'),
        'disk_usage': ('Disk Usage', '磁盘使用率'),
    }
    for metric, (en_name, zh_name) in extra_thresholds.items():
        data = resource_data.get(metric, {})
        if not data:
            continue
        peak = data.get('peak', 0)
        avg = data.get('avg', 0)
        if peak > 90:
            suggestions.append(('danger', 0, f'{en_name} peak {peak:.1f}%, critical level. Immediate attention required.',
                                f'{zh_name}峰值 {peak:.1f}%，已达危险水平，需立即关注'))
        elif peak > 80:
            suggestions.append(('danger', 2, f'{en_name} peak {peak:.1f}%, approaching limit. Recommend scaling up or cleaning data.',
                                f'{zh_name}峰值 {peak:.1f}%，接近上限，建议扩容或清理数据'))
        elif peak > 60:
            suggestions.append(('warn', 22, f'{en_name} peak {peak:.1f}%, relatively high. Recommend monitoring trend.',
                                f'{zh_name}峰值 {peak:.1f}%，偏高，建议持续关注趋势'))
        if avg > 70:
            suggestions.append(('warn', 22, f'{en_name} average {avg:.1f}%, sustained high load. Recommend scaling.',
                                f'{zh_name}均值 {avg:.1f}%，持续高负载，建议扩容'))

    # ═══ Slow logs (only if not covered by correlation) ═══
    if not slow_covered:
        if slow_total > 100:
            cmd_name = top_cmd['command'] if top_cmd else 'UNKNOWN'
            suggestions.append(('danger', 3, f'High number of slow logs ({slow_total} records in {_INSPECT_DAYS} days). Top command: {cmd_name}. Recommend optimizing hot paths.',
                                f'慢日志较多（{_INSPECT_DAYS} 天内 {slow_total} 条），最高频命令: {cmd_name}，建议优化热点路径'))
        elif slow_total > 20:
            suggestions.append(('warn', 23, f'Slow logs detected ({slow_total} records in {_INSPECT_DAYS} days). Recommend reviewing command patterns.',
                                f'检测到慢日志（{_INSPECT_DAYS} 天内 {slow_total} 条），建议检查命令模式'))

    # ═══ Big/Hot keys (only if not covered by correlation) ═══
    if large_keys and not bigkey_covered:
        largest = large_keys[0]
        size_mb = int(largest.get('data_size', 0)) / (1024 * 1024)
        suggestions.append(('warn', 24, f'{len(large_keys)} large keys by memory (largest: {largest.get("key", "")[:40]}, {size_mb:.2f}MB). Recommend splitting them into multiple smaller keys, or migrating these keys to a dedicated instance with larger memory.',
                            f'{len(large_keys)} 个大 key（按内存），最大: {largest.get("key", "")[:40]}（{size_mb:.2f}MB），建议拆分为多个小 key，或将这类 key 迁移到内存更大的专用实例'))
    elif big_keys and not bigkey_covered:
        biggest = big_keys[0]
        suggestions.append(('warn', 24, f'{len(big_keys)} big keys by element count (largest: {biggest.get("key", "")[:40]}). Recommend splitting collections into smaller ones (e.g. shard a Hash/List/Set by key suffix) or moving heavy collections to a dedicated instance.',
                            f'{len(big_keys)} 个大 key（按元素数），最大: {biggest.get("key", "")[:40]}，建议将 Hash/List/Set 按后缀拆分为多个小集合，或将重型集合迁移到专用实例'))

    if hot_keys and not hotkey_covered:
        hottest = hot_keys[0]
        suggestions.append(('warn', 24, f'{len(hot_keys)} hot keys (hottest: {hottest.get("key", "")[:40]}, QPS {hottest.get("hot", "")}). Recommend caching these keys in client-side local cache (e.g. Caffeine), or distributing read load via read-only replicas.',
                            f'{len(hot_keys)} 个热 key（最热: {hottest.get("key", "")[:40]}，QPS {hottest.get("hot", "")}），建议在客户端本地缓存这些 key（如 Caffeine），或通过只读副本分摆读压力'))
    elif high_traffic_keys and not hotkey_covered:
        suggestions.append(('warn', 24, f'{len(high_traffic_keys)} high-traffic keys found. Recommend reviewing client access patterns and adding client-side caching for frequently-read keys.',
                            f'发现 {len(high_traffic_keys)} 个高流量 key，建议检查客户端访问模式，对高频读取的 key 在客户端增加本地缓存'))

    # ═══ Alerts (only if not covered by correlation) ═══
    if not alert_covered and alerts:
        # Aggregate alerts by rule_name to surface per-rule context
        # (rule name, trigger count, threshold, peak observed value, metric).
        def _summarize_rules(alert_list):
            rules = {}
            for a in alert_list:
                rn = a.get('rule_name') or '(unnamed)'
                if rn not in rules:
                    rules[rn] = {
                        'count': 0,
                        'max_value': None,
                        'threshold': a.get('threshold', ''),
                        'metric': a.get('metric', ''),
                    }
                rules[rn]['count'] += 1
                try:
                    v = float(a.get('cur_value', '') or 'nan')
                    if rules[rn]['max_value'] is None or v > rules[rn]['max_value']:
                        rules[rn]['max_value'] = v
                except (ValueError, TypeError):
                    pass
            return rules

        def _format_rule_summary(alert_list):
            """Return ('rule (Nx, metric M, threshold T, peak P); ...', zh-version)."""
            parts_en, parts_zh = [], []
            for rn, info in sorted(_summarize_rules(alert_list).items(), key=lambda x: -x[1]['count']):
                metric = info['metric'] or '-'
                thr = info['threshold'] if info['threshold'] != '' else '-'
                mx = info['max_value']
                mx_en = f', peak {mx:.1f}' if isinstance(mx, (int, float)) else ''
                mx_zh = f'，峰值 {mx:.1f}' if isinstance(mx, (int, float)) else ''
                parts_en.append(f'"{rn}" triggered {info["count"]}x ({metric}, threshold {thr}{mx_en})')
                parts_zh.append(f'「{rn}」触发 {info["count"]} 次（{metric}，阈值 {thr}{mx_zh}）')
            return '; '.join(parts_en), '；'.join(parts_zh)

        # Per-category guidance, with concrete rule names + thresholds + peaks.
        alert_groups = []
        if cpu_alerts:
            sum_en, sum_zh = _format_rule_summary(cpu_alerts)
            alert_groups.append((
                f'CPU alerts: {sum_en}. Recommend checking high-cost commands (KEYS/HGETALL/SMEMBERS), hot keys, or upgrading CPU specs.',
                f'CPU 告警：{sum_zh}。建议排查高消耗命令（KEYS/HGETALL/SMEMBERS）、热 key，或升级 CPU 规格'
            ))
        if mem_alerts:
            sum_en, sum_zh = _format_rule_summary(mem_alerts)
            alert_groups.append((
                f'Memory alerts: {sum_en}. Recommend cleaning expired/large keys, configuring an eviction policy (e.g. allkeys-lru), or upgrading memory specs.',
                f'内存告警：{sum_zh}。建议清理过期/大 key、配置淘汰策略（如 allkeys-lru），或升级内存规格'
            ))
        if conn_alerts:
            sum_en, sum_zh = _format_rule_summary(conn_alerts)
            alert_groups.append((
                f'Connection alerts: {sum_en}. Recommend checking connection pool config, slow commands causing connection accumulation, or connection leaks.',
                f'连接告警：{sum_zh}。建议检查连接池配置、慢命令导致的连接堆积、连接泄漏'
            ))
        if bw_alerts:
            sum_en, sum_zh = _format_rule_summary(bw_alerts)
            alert_groups.append((
                f'Bandwidth alerts: {sum_en}. Recommend checking big-key transfers, optimizing batch operations (e.g. MGET/MSET pagination), or upgrading bandwidth specs.',
                f'带宽告警：{sum_zh}。建议检查大 key 传输、优化批量操作（如 MGET/MSET 分页），或升级带宽规格'
            ))

        if alert_groups:
            for en, zh in alert_groups:
                suggestions.append(('danger', 3, en, zh))
        else:
            # Fallback: alerts that don't match any known metric category - per-rule guidance.
            rule_summary = _summarize_rules(alerts)
            for rn, info in sorted(rule_summary.items(), key=lambda x: -x[1]['count'])[:5]:
                metric = info['metric'] or '-'
                thr = info['threshold'] if info['threshold'] != '' else '-'
                mx = info['max_value']
                mx_en = f', peak {mx:.1f}' if isinstance(mx, (int, float)) else ''
                mx_zh = f'，峰值 {mx:.1f}' if isinstance(mx, (int, float)) else ''
                level = 'danger' if rn in [a.get('rule_name') for a in p1p2_alerts] else 'warn'
                priority = 3 if level == 'danger' else 25
                suggestions.append((level, priority,
                    f'Alert rule "{rn}" triggered {info["count"]}x in last {_INSPECT_DAYS} days ({metric}, threshold {thr}{mx_en}). Recommend reviewing whether the threshold matches actual baseline and investigating the underlying metric trend.',
                    f'告警规则「{rn}」近 {_INSPECT_DAYS} 天触发 {info["count"]} 次（{metric}，阈值 {thr}{mx_zh}），建议复核阈值是否符合实际基线并排查对应指标趋势'))

    # ═══ Version upgrade check ═══
    if engine_version:
        is_latest = engine_version.get('is_latest_version', True)
        enable_upgrade_minor = engine_version.get('enable_upgrade_minor', False)
        enable_upgrade_major = engine_version.get('enable_upgrade_major', False)
        minor_ver = engine_version.get('minor_version', '')
        latest_minor_ver = engine_version.get('latest_minor_version', '')
        proxy_minor_ver = engine_version.get('proxy_minor_version', '')
        proxy_latest_ver = engine_version.get('proxy_latest_minor_version', '')

        if enable_upgrade_minor and minor_ver and latest_minor_ver and minor_ver != latest_minor_ver:
            suggestions.append(('info', 40, f'Minor version upgrade available: current {minor_ver} → latest {latest_minor_ver}. Brief service interruption during upgrade.',
                                f'小版本可升级: 当前 {minor_ver} → 最新 {latest_minor_ver}，升级期间有短暂服务中断'))

        if enable_upgrade_major:
            major_ver = engine_version.get('major_version', '')
            suggestions.append(('info', 40, f'Major version upgrade available for Redis {major_ver}. Contact support for upgrade planning.',
                                f'Redis {major_ver} 有大版本可升级，请联系技术支持规划升级'))

        if proxy_minor_ver and proxy_latest_ver and proxy_minor_ver != proxy_latest_ver:
            suggestions.append(('info', 40, f'Proxy version upgrade available: current {proxy_minor_ver} → latest {proxy_latest_ver}.',
                                f'代理版本可升级: 当前 {proxy_minor_ver} → 最新 {proxy_latest_ver}'))

    # Sort by priority, then convert to (level, text) format for backward compatibility
    suggestions.sort(key=lambda x: x[1])

    # Return format depends on whether we have bilingual data
    # For render_html and render_text, we need bilingual
    return [(s[0], s[2], s[3]) for s in suggestions]


def format_architecture(instance_info):
    """Format architecture description, returns (en, zh) tuple."""
    arch = instance_info.get('ArchitectureType', 'standard')
    node_type = instance_info.get('NodeType', 'double')
    read_only = instance_info.get('ReadOnlyCount', 0) or 0
    arch_map_en = {'cluster': 'Cluster', 'standard': 'Standard', 'rwsplit': 'Read-Write Split'}
    arch_map_zh = {'cluster': '\u96c6\u7fa4\u7248', 'standard': '\u6807\u51c6\u7248', 'rwsplit': '\u8bfb\u5199\u5206\u79bb'}
    arch_en = arch_map_en.get(arch, arch)
    arch_zh = arch_map_zh.get(arch, arch)
    if read_only > 0:
        detail_en = f'Read-Write Split, {read_only} read-only'
        detail_zh = f'\u8bfb\u5199\u5206\u79bb, {read_only} \u53ea\u8bfb'
    elif node_type == 'single':
        detail_en = 'Single Replica'
        detail_zh = '\u5355\u526f\u672c'
    else:
        detail_en = 'Dual Replica'
        detail_zh = '\u53cc\u526f\u672c'
    return (f'{arch_en} ({detail_en})', f'{arch_zh}\uff08{detail_zh}\uff09')


def format_instance_spec(instance_info):
    """Format instance specification string, returns (en, zh) tuple."""
    capacity_mb = instance_info.get('Capacity', 0)
    shard_count = instance_info.get('ShardCount', 1) or 1
    real_class = instance_info.get('RealInstanceClass', '') or instance_info.get('InstanceClass', '')
    if capacity_mb >= 1024:
        capacity_str = f'{capacity_mb // 1024}GB'
    else:
        capacity_str = f'{capacity_mb}MB'
    if shard_count > 1:
        per_shard_mb = capacity_mb // shard_count
        per_shard_str = f'{per_shard_mb // 1024}GB' if per_shard_mb >= 1024 else f'{per_shard_mb}MB'
        spec_en = f'{real_class} ({per_shard_str} * {shard_count} shards)'
        spec_zh = f'{real_class} ({per_shard_str} * {shard_count}\u5206\u7247)'
    else:
        spec_en = f'{real_class} ({capacity_str})'
        spec_zh = spec_en
    return (spec_en, spec_zh)


def _render_node_details_table(node_details, inst_type='regular'):
    """Render unified node-level metrics table (PolarDB style: all nodes in one table)."""
    if not node_details:
        return ''

    db_nodes = node_details.get('db_nodes', {})
    proxy_nodes = node_details.get('proxy_nodes', {})
    if not db_nodes and not proxy_nodes:
        return ''

    # Metric columns (full set)
    all_cols_full = [
        ('CpuUsage', 'CPU (Avg/Peak)', 'CPU（均值/峰值）'),
        ('MemoryUsage', 'Memory (Avg/Peak)', '内存（均值/峰值）'),
        ('ConnectionUsage', 'Conn (Avg/Peak)', '连接数（均值/峰值）'),
        ('IntranetInRatio', 'Input BW (Avg/Peak)', '入带宽（均值/峰值）'),
        ('IntranetOutRatio', 'Output BW (Avg/Peak)', '出带宽（均值/峰值）'),
    ]
    # Filter columns by per-instance-type config (if any).
    # Always keep ConnectionUsage column so proxy rows can render their data.
    type_keys = (METRICS_CONFIG or {}).get('instance_type_monitor_keys', {}).get(inst_type)
    if type_keys:
        keep = set(type_keys) | {'ConnectionUsage'}
        all_cols = [c for c in all_cols_full if c[0] in keep]
    else:
        all_cols = all_cols_full

    html = '<div class="table-scroll"><table><tr>'
    html += '<th data-en="Node" data-zh="节点">Node</th>'
    for _, en_h, zh_h in all_cols:
        html += f'<th data-en="{en_h}" data-zh="{zh_h}">{en_h}</th>'
    html += '<th data-en="Status" data-zh="状态">Status</th></tr>'

    def _short_name(full_id):
        """Extract short node name: r-bp1xxx-db-0#12345 -> db-0"""
        m = re.search(r'-((?:db|proxy|ro)\w*?-\d+)', full_id)
        if m:
            return m.group(1)
        # Fallback: strip hash suffix and instance prefix
        name = full_id.split('#')[0]
        parts = name.split('-')
        # Find type-number pattern (e.g., db-0, proxy-0)
        for i, p in enumerate(parts):
            if p in ('db', 'proxy', 'ro', 'cs') and i + 1 < len(parts) and parts[i + 1].isdigit():
                return f'{p}-{parts[i + 1]}'
        return name.split('-')[-2] + '-' + name.split('-')[-1] if len(name.split('-')) >= 2 else name

    def _add_rows(nodes, role_label):
        rows = ''
        is_proxy = (role_label == 'Proxy')

        # First pass: collect all short names to detect duplicates (for DB nodes only)
        short_names = []
        for node_id in sorted(nodes.keys()):
            if is_proxy:
                short_names.append(node_id)  # Proxy nodes use full ID
            else:
                short_names.append(_short_name(node_id))

        # Count occurrences of each base name
        from collections import Counter
        name_counts = Counter(short_names)

        # Second pass: generate final names with sequential numbering for duplicates
        name_index = {}
        for node_id in sorted(nodes.keys()):
            if is_proxy:
                # Proxy nodes: show full node ID
                display_name = node_id
            else:
                base_short = _short_name(node_id)
                if name_counts[base_short] > 1:
                    # Multiple nodes with same base name, renumber sequentially
                    if base_short not in name_index:
                        name_index[base_short] = 0
                    idx = name_index[base_short]
                    name_index[base_short] += 1
                    # Replace the trailing number: proxy-0 -> proxy-0, proxy-1, proxy-2
                    node_type = base_short.rsplit('-', 1)[0]  # Extract 'proxy' from 'proxy-0'
                    display_name = f'{node_type}-{idx}'
                else:
                    display_name = base_short

            metrics = nodes[node_id]
            rows += f'<tr><td>{display_name} <span class="role-badge">{role_label}</span></td>'
            max_peak = 0
            for key, _, _ in all_cols:
                m = metrics.get(key, {})
                # Proxy nodes don't have memory metrics, show "/"
                if is_proxy and key == 'MemoryUsage':
                    rows += '<td>/</td>'
                    continue
                avg = m.get('avg', 0)
                peak = m.get('peak', 0)
                if peak > max_peak:
                    max_peak = peak
                rows += f'<td>{avg:.2f}% / {peak:.2f}%</td>'
            if max_peak > 80:
                status = f'<span class="danger">{status_icon(max_peak)}</span>'
            elif max_peak > 60:
                status = f'<span class="warn">{status_icon(max_peak)}</span>'
            else:
                status = f'<span class="ok">{status_icon(max_peak)}</span>'
            rows += f'<td>{status}</td></tr>'
        return rows

    if db_nodes:
        html += _add_rows(db_nodes, 'DB')
    if proxy_nodes:
        html += _add_rows(proxy_nodes, 'Proxy')

    html += '</table></div>'
    return html


def render_html(report_data):
    """Render HTML report with ECharts and 7 sections."""
    instance_id = report_data['instance_id']
    region = report_data['region']
    instance_info = report_data['instance_info']
    resource_data = report_data['resource_data']
    node_details = report_data.get('node_details')  # 节点级别详情
    inst_type = report_data.get('instance_type', 'regular')  # 实例类型
    session_info = report_data.get('session_info', {})
    big_hot_keys = report_data.get('big_hot_keys', {})
    slow_logs = report_data.get('slow_logs', {})
    alert_history = report_data.get('alert_history', [])
    alert_rules = report_data.get('alert_rules', [])
    suggestions = report_data.get('suggestions', [])

    # Build display order based on instance type (pena/essd/regular)
    metric_label_map = {
        'CpuUsage': 'CPU Usage', 'ConnectionUsage': 'Connection Usage',
        'MemoryUsage': 'Memory Usage', 'IntranetInRatio': 'Input Bandwidth',
        'IntranetOutRatio': 'Output Bandwidth', 'pmem_usage': 'PMem Usage',
        'disk_usage': 'Disk Usage', 'iops_usage': 'IOPS Usage',
        'AvgRt': 'Avg RT',
        'proxy_CpuUsage': 'Proxy CPU Usage', 'proxy_ConnectionUsage': 'Proxy Connection Usage',
        'proxy_IntranetIn': 'Proxy Input Traffic', 'proxy_IntranetOut': 'Proxy Output Traffic',
        'proxy_AvgRt': 'Proxy Avg RT',
    }
    # Chinese labels from config
    zh_metric_label_map = {}
    if METRICS_CONFIG and 'metric_labels' in METRICS_CONFIG:
        for key, labels in METRICS_CONFIG['metric_labels'].items():
            zh_metric_label_map[key] = labels.get('zh', labels.get('en', key))
    display_order = None
    if METRICS_CONFIG:
        display_order = METRICS_CONFIG.get('instance_type_display_order', {}).get(inst_type)
    if display_order:
        metrics_display = [(k, metric_label_map.get(k, k)) for k in display_order if k in metric_label_map]
    else:
        metrics_display = [
            ('CpuUsage', 'CPU Usage'),
            ('ConnectionUsage', 'Connection Usage'),
            ('MemoryUsage', 'Memory Usage'),
            ('IntranetInRatio', 'Input Bandwidth'),
            ('IntranetOutRatio', 'Output Bandwidth'),
        ]
    proxy_metrics_display = [
        ('proxy_CpuUsage', 'Proxy CPU Usage'),
        ('proxy_ConnectionUsage', 'Proxy Connection Usage'),
        ('proxy_IntranetIn', 'Proxy Input Traffic'),
        ('proxy_IntranetOut', 'Proxy Output Traffic'),
        ('proxy_AvgRt', 'Proxy Avg RT'),
    ]
    has_proxy = any(resource_data.get(k) for k, _ in proxy_metrics_display)
    all_metrics = metrics_display + (proxy_metrics_display if has_proxy else [])

    chart_data = {}
    for key, en_label in all_metrics:
        data = resource_data.get(key, {})
        if not data:
            continue
        values = data.get('values', [])
        chart_data[key] = json.dumps([[v['timestamp'], v['value']] for v in values])

    # Session HTML
    session_html = '<div class="info-grid">'
    if session_info:
        max_conn = session_info.get('max_connections', 0)
        session_html += f'<div class="info-item"><span class="label" data-en="Max Connections" data-zh="\u6700\u5927\u8fde\u63a5\u6570">Max Connections</span><span class="value">{max_conn}</span></div>'
        used_peak = session_info.get('used_connections_peak', 0)
        session_html += f'<div class="info-item"><span class="label" data-en="Used Connections (Peak)" data-zh="\u5df2\u7528\u8fde\u63a5\u6570\uff08\u5cf0\u503c\uff09">Used Connections (Peak)</span><span class="value">{used_peak}</span></div>'
        conn_avg = session_info.get('connection_usage_avg', 0)
        conn_peak = session_info.get('connection_usage_peak', 0)
        session_html += f'<div class="info-item"><span class="label" data-en="Connection Usage (Avg)" data-zh="\u8fde\u63a5\u4f7f\u7528\u7387\uff08\u5e73\u5747\uff09">Connection Usage (Avg)</span><span class="value">{conn_avg:.2f}%</span></div>'
        session_html += f'<div class="info-item"><span class="label" data-en="Connection Usage (Peak)" data-zh="\u8fde\u63a5\u4f7f\u7528\u7387\uff08\u5cf0\u503c\uff09">Connection Usage (Peak)</span><span class="value">{conn_peak:.2f}%</span></div>'
        proxy_avg = session_info.get('proxy_connection_usage_avg', 0)
        proxy_peak = session_info.get('proxy_connection_usage_peak', 0)
        if proxy_avg or proxy_peak:
            session_html += f'<div class="info-item"><span class="label" data-en="Proxy Conn Usage (Avg)" data-zh="\u4ee3\u7406\u8fde\u63a5\u4f7f\u7528\u7387\uff08\u5e73\u5747\uff09">Proxy Conn Usage (Avg)</span><span class="value">{proxy_avg:.2f}%</span></div>'
            session_html += f'<div class="info-item"><span class="label" data-en="Proxy Conn Usage (Peak)" data-zh="\u4ee3\u7406\u8fde\u63a5\u4f7f\u7528\u7387\uff08\u5cf0\u503c\uff09">Proxy Conn Usage (Peak)</span><span class="value">{proxy_peak:.2f}%</span></div>'
    session_html += '</div>'
    # Real-time session list from DAS API
    real_sessions = session_info.get('real_sessions', {}) if session_info else {}
    if real_sessions:
        total_sess = real_sessions.get('total', 0)
        sessions_list = real_sessions.get('sessions', [])
        source_stats = real_sessions.get('source_stats', [])
        session_html += f'<h3 data-en="Active Sessions (Total: {total_sess})" data-zh="\u6d3b\u8dc3\u4f1a\u8bdd\uff08\u5171 {total_sess} \u4e2a\uff09">Active Sessions (Total: {total_sess})</h3>'
        if source_stats:
            session_html += '<h3 data-en="Source Statistics" data-zh="\u6765\u6e90\u7edf\u8ba1">Source Statistics</h3><table><tr><th>#</th><th data-en="Client IP" data-zh="\u5ba2\u6237\u7aef IP">Client IP</th><th data-en="Sessions" data-zh="\u4f1a\u8bdd\u6570">Sessions</th></tr>'
            for i, src in enumerate(sorted(source_stats, key=lambda x: int(x.get('Count', 0)), reverse=True)[:20], 1):
                session_html += f'<tr><td>{i}</td><td>{src.get("Key", "")}</td><td>{src.get("Count", 0)}</td></tr>'
            session_html += '</table>'
        if sessions_list:
            session_html += '<h3 data-en="Session Details (Top 50)" data-zh="会话详情 (Top 50)">会话详情 (Top 50)</h3><div class="table-scroll-h"><table><tr><th>#</th><th>Addr</th><th>Cmd</th><th>Age(s)</th><th>Idle(s)</th><th>DB</th><th>Node</th><th>Flags</th><th>Fd</th><th>Events</th><th>Name</th><th>Sub</th><th>Psub</th><th>Multi</th><th>Obl</th><th>Oll</th><th>Omem</th><th>Qbuf</th></tr>'
            sorted_sessions = sorted(sessions_list, key=lambda x: int(x.get('Idle', 0) or 0))
            for i, s in enumerate(sorted_sessions[:50], 1):
                addr = s.get('Addr', '') or s.get('Client', '')
                cmd = s.get('Cmd', '')
                age = s.get('Age', '')
                idle = s.get('Idle', '')
                db = s.get('Db', 0)
                node_id = s.get('NodeId', '')
                flags = s.get('Flags', '')
                fd = s.get('Fd', '')
                events = s.get('Events', '')
                name = s.get('Name', '')
                sub = s.get('Sub', 0)
                psub = s.get('Psub', 0)
                multi = s.get('Multi', '')
                obl = s.get('Obl', '')
                oll = s.get('Oll', '')
                omem = s.get('Omem', '')
                qbuf = s.get('Qbuf', '')
                session_html += f'<tr><td>{i}</td><td>{addr}</td><td><strong>{cmd}</strong></td><td>{age}</td><td>{idle}</td><td>{db}</td><td>{node_id}</td><td>{flags}</td><td>{fd}</td><td>{events}</td><td>{name}</td><td>{sub}</td><td>{psub}</td><td>{multi}</td><td>{obl}</td><td>{oll}</td><td>{omem}</td><td>{qbuf}</td></tr>'
            session_html += '</table></div>'
    elif session_info:
        session_html += '<p data-en="Session details not available (DAS API)" data-zh="\u4f1a\u8bdd\u8be6\u60c5\u4e0d\u53ef\u7528\uff08DAS API\uff09">Session details not available (DAS API)</p>'

    # Basic info
    engine_version = report_data.get('engine_version', {})
    inst_name = instance_info.get('InstanceName', 'N/A') if instance_info else 'N/A'
    engine_ver = instance_info.get('EngineVersion', 'N/A') if instance_info else 'N/A'
    minor_ver = (engine_version or {}).get('minor_version', 'N/A') if engine_version else 'N/A'
    latest_minor_ver = (engine_version or {}).get('latest_minor_version', '') if engine_version else ''
    is_latest = (engine_version or {}).get('is_latest_version', False) if engine_version else False
    enable_upgrade_minor = (engine_version or {}).get('enable_upgrade_minor', False) if engine_version else False
    enable_upgrade_major = (engine_version or {}).get('enable_upgrade_major', False) if engine_version else False

    # Build version status HTML
    version_status_html = ''
    if engine_version:
        if latest_minor_ver:
            version_status_html += f'<div class="info-item"><span class="label" data-en="Latest Minor Version" data-zh="\u6700\u65b0\u5c0f\u7248\u672c">Latest Minor Version</span><span class="value">{latest_minor_ver}</span></div>'

        # Version status indicator
        if is_latest:
            ver_status_en = '\u2705 Latest'
            ver_status_zh = '\u2705 \u5df2\u662f\u6700\u65b0'
            ver_status_cls = 'ver-ok'
        elif enable_upgrade_minor:
            ver_status_en = '\u2b06\ufe0f Upgrade Available'
            ver_status_zh = '\u2b06\ufe0f \u53ef\u5347\u7ea7\u5c0f\u7248\u672c'
            ver_status_cls = 'ver-upgrade'
        elif enable_upgrade_major:
            ver_status_en = '\u2b06\ufe0f Major Upgrade Available'
            ver_status_zh = '\u2b06\ufe0f \u53ef\u5347\u7ea7\u5927\u7248\u672c'
            ver_status_cls = 'ver-major'
        else:
            ver_status_en = 'Unknown'
            ver_status_zh = '\u672a\u77e5'
            ver_status_cls = ''

        version_status_html += f'<div class="info-item"><span class="label" data-en="Version Status" data-zh="\u7248\u672c\u72b6\u6001">Version Status</span><span class="value {ver_status_cls}" data-en="{ver_status_en}" data-zh="{ver_status_zh}">{ver_status_en}</span></div>'

    proxy_minor_ver = (engine_version or {}).get('proxy_minor_version', '') if engine_version else ''
    proxy_latest_ver = (engine_version or {}).get('proxy_latest_minor_version', '') if engine_version else ''
    proxy_minor_ver_html = ''
    if proxy_minor_ver:
        proxy_minor_ver_html += f'<div class="info-item"><span class="label" data-en="Proxy Minor Version" data-zh="\u4ee3\u7406\u5c0f\u7248\u672c">Proxy Minor Version</span><span class="value">{proxy_minor_ver}</span></div>'
        if proxy_latest_ver and proxy_latest_ver != proxy_minor_ver:
            proxy_minor_ver_html += f'<div class="info-item"><span class="label" data-en="Proxy Latest Version" data-zh="\u4ee3\u7406\u6700\u65b0\u7248\u672c">Proxy Latest Version</span><span class="value">{proxy_latest_ver}</span></div>'
            proxy_minor_ver_html += f'<div class="info-item"><span class="label" data-en="Proxy Version Status" data-zh="\u4ee3\u7406\u7248\u672c\u72b6\u6001">Proxy Version Status</span><span class="value ver-upgrade" data-en="\u2b06\ufe0f Upgrade Available" data-zh="\u2b06\ufe0f \u53ef\u5347\u7ea7">\u2b06\ufe0f Upgrade Available</span></div>'
    inst_spec = format_instance_spec(instance_info) if instance_info else ('N/A', 'N/A')
    inst_spec_en, inst_spec_zh = inst_spec if isinstance(inst_spec, tuple) else (inst_spec, inst_spec)
    arch_disp = format_architecture(instance_info) if instance_info else ('N/A', 'N/A')
    arch_en, arch_zh = arch_disp if isinstance(arch_disp, tuple) else (arch_disp, arch_disp)
    inst_status = instance_info.get('InstanceStatus', 'N/A') if instance_info else 'N/A'
    status_map_zh = {'Normal': '\u6b63\u5e38', 'Creating': '\u521b\u5efa\u4e2d', 'Changing': '\u53d8\u66f4\u4e2d', 'Inactive': '\u5df2\u505c\u7528', 'Flushing': '\u6e05\u9664\u4e2d', 'Released': '\u5df2\u91ca\u653e', 'Transforming': '\u8f6c\u6362\u4e2d', 'Migrating': '\u8fc1\u79fb\u4e2d'}
    inst_status_zh = status_map_zh.get(inst_status, inst_status)
    max_conn = instance_info.get('Connections', 'N/A') if instance_info else 'N/A'
    max_bw = instance_info.get('Bandwidth', 'N/A') if instance_info else 'N/A'
    create_time = instance_info.get('CreateTime', 'N/A') if instance_info else 'N/A'

    # Node topology HTML for basic info section
    node_topology_html = ''
    db_details = session_info.get('db_node_details', []) if session_info else []
    proxy_details = session_info.get('proxy_node_details', []) if session_info else []
    if db_details:
        node_topology_html += '<h3 data-en="DB Node Details" data-zh="DB \u8282\u70b9\u8be6\u60c5">DB Node Details</h3>'
        node_topology_html += '<div class="table-scroll-h"><table><tr><th>#</th><th data-en="Node ID" data-zh="\u8282\u70b9 ID">Node ID</th><th data-en="Memory (GB)" data-zh="\u5185\u5b58 (GB)">Memory (GB)</th><th data-en="Max Connections" data-zh="\u6700\u5927\u8fde\u63a5\u6570">Max Connections</th><th data-en="Bandwidth(MB/s)" data-zh="\u5e26\u5bbd(MB/s)">Bandwidth(MB/s)</th></tr>'
        for i, nd in enumerate(db_details, 1):
            node_topology_html += f'<tr><td>{i}</td><td>{nd.get("node_id", "")}</td><td>{nd.get("memory", "")}</td><td>{nd.get("connection", "")}</td><td>{nd.get("bandwidth", "")}</td></tr>'
        node_topology_html += '</table></div>'
    if proxy_details:
        node_topology_html += f'<h3 data-en="Proxy Node Details" data-zh="Proxy \u8282\u70b9\u8be6\u60c5">Proxy Node Details</h3>'
        node_topology_html += '<div class="table-scroll-h"><table><tr><th>#</th><th data-en="Node ID" data-zh="\u8282\u70b9 ID">Node ID</th><th data-en="Max Connections" data-zh="\u6700\u5927\u8fde\u63a5\u6570">Max Connections</th></tr>'
        for i, nd in enumerate(proxy_details, 1):
            node_topology_html += f'<tr><td>{i}</td><td>{nd.get("node_id", "")}</td><td>{nd.get("connection", "")}</td></tr>'
        node_topology_html += '</table></div>'

    # Suggestions HTML - PolarDB style with three risk levels
    sug_html = ''
    if not suggestions:
        sug_html = '<p class="ok-msg" data-en="\u2705 No significant issues found, instance is running normally." data-zh="\u2705 \u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\uff0c\u5b9e\u4f8b\u8fd0\u884c\u6b63\u5e38\u3002">\u2705 No significant issues found, instance is running normally.</p>'
    else:
        danger_items = [s for s in suggestions if s[0] == 'danger']
        warn_items = [s for s in suggestions if s[0] == 'warn']
        info_items = [s for s in suggestions if s[0] == 'info']

        for label, label_zh, items in [('\U0001F534 High Risk', '\U0001F534 \u9ad8\u98ce\u9669', danger_items), ('\U0001F7E1 Medium Risk', '\U0001F7E1 \u4e2d\u98ce\u9669', warn_items), ('\U0001F535 Low Risk', '\U0001F535 \u4f4e\u98ce\u9669', info_items)]:
            if not items:
                continue
            sug_html += f'<h3 style="margin:0.8rem 0 0.4rem;" data-en="{label}" data-zh="{label_zh}">{label}</h3>'
            if len(items) == 1:
                en_msg = items[0][1] if len(items[0]) > 2 else items[0][1]
                zh_msg = items[0][2] if len(items[0]) > 2 else items[0][1]
                sug_html += f'<p style="margin-left:1.2rem;" data-en="{en_msg}" data-zh="{zh_msg}">{en_msg}</p>'
            else:
                sug_html += '<ol class="sug-list">'
                for s in items:
                    en_msg = s[1] if len(s) > 2 else s[1]
                    zh_msg = s[2] if len(s) > 2 else s[1]
                    sug_html += f'<li data-en="{en_msg}" data-zh="{zh_msg}">{en_msg}</li>'
                sug_html += '</ol>'

    # Big key HTML
    bigkey_html = ''
    if big_hot_keys:
        large_keys = big_hot_keys.get('large_keys', [])
        bk = big_hot_keys.get('big_keys', [])
        hk = big_hot_keys.get('hot_keys', [])
        htk = big_hot_keys.get('high_traffic_keys', [])
        if large_keys:
            bigkey_html += '<h3 data-en="Large Keys (by Memory)" data-zh="\u5927 Key\uff08\u6309\u5185\u5b58\uff09">Large Keys (by Memory)</h3><table><tr><th>#</th><th>DB</th><th data-en="Type" data-zh="\u7c7b\u578b">Type</th><th data-en="Memory" data-zh="\u5185\u5b58">Memory</th><th>Key</th></tr>'
            for i, k in enumerate(large_keys[:10], 1):
                ds = int(k.get('data_size', 0))
                size_str = f'{ds/1024:.1f}KB' if ds < 1024*1024 else f'{ds/(1024*1024):.2f}MB'
                bigkey_html += f'<tr><td>{i}</td><td>{k.get("db", 0)}</td><td>{k.get("type", "")}</td><td>{size_str}</td><td><code>{k.get("key", "")[:60]}</code></td></tr>'
            bigkey_html += '</table>'
        if bk:
            bigkey_html += '<h3 data-en="Big Keys (by Elements)" data-zh="\u5927 Key\uff08\u6309\u5143\u7d20\u6570\uff09">Big Keys (by Elements)</h3><table><tr><th>#</th><th>DB</th><th data-en="Type" data-zh="\u7c7b\u578b">Type</th><th data-en="Elements" data-zh="\u5143\u7d20\u6570">Elements</th><th>Key</th></tr>'
            for i, k in enumerate(bk[:10], 1):
                bigkey_html += f'<tr><td>{i}</td><td>{k.get("db", 0)}</td><td>{k.get("type", "")}</td><td>{k.get("size", 0)}</td><td><code>{k.get("key", "")[:60]}</code></td></tr>'
            bigkey_html += '</table>'
        if not large_keys and not bk:
            bigkey_html += f'<p class="ok-msg" data-en="\u2705 No big keys found in last {_INSPECT_DAYS} days" data-zh="\u2705 \u8fd1 {_INSPECT_DAYS} \u5929\u672a\u53d1\u73b0\u5927 Key">\u2705 No big keys found in last {_INSPECT_DAYS} days</p>'
        if hk:
            bigkey_html += '<h3 data-en="Hot Keys (by QPS)" data-zh="\u70ed Key\uff08\u6309 QPS\uff09">Hot Keys (by QPS)</h3><table><tr><th>#</th><th>DB</th><th data-en="Type" data-zh="\u7c7b\u578b">Type</th><th>QPS</th><th>Key</th></tr>'
            for i, k in enumerate(hk[:10], 1):
                bigkey_html += f'<tr><td>{i}</td><td>{k.get("db", 0)}</td><td>{k.get("type", "")}</td><td>{k.get("hot", "")}</td><td><code>{k.get("key", "")[:60]}</code></td></tr>'
            bigkey_html += '</table>'
        if not hk and not htk:
            bigkey_html += f'<p class="ok-msg" data-en="\u2705 No hot keys found in last {_INSPECT_DAYS} days" data-zh="\u2705 \u8fd1 {_INSPECT_DAYS} \u5929\u672a\u53d1\u73b0\u70ed Key">\u2705 No hot keys found in last {_INSPECT_DAYS} days</p>'
    else:
        bigkey_html = '<p data-en="Big/Hot key analysis not available" data-zh="\u5927 Key/\u70ed Key \u5206\u6790\u4e0d\u53ef\u7528">Big/Hot key analysis not available</p>'

    # Slow log HTML
    slowlog_html = ''
    if slow_logs and slow_logs.get('stats'):
        stats = slow_logs['stats']
        total = slow_logs.get('total_count', 0)
        slowlog_html += f'<p data-en="Total: {total}" data-zh="\u5171 {total} \u6761">Total: <strong>{total}</strong></p>'
        slowlog_html += '<table><tr><th>#</th><th data-en="Command" data-zh="\u547d\u4ee4">Command</th><th data-en="Count" data-zh="\u6b21\u6570">Count</th><th data-en="Total(ms)" data-zh="\u603b\u8017\u65f6(ms)">Total(ms)</th><th data-en="Avg(ms)" data-zh="\u5e73\u5747(ms)">Avg(ms)</th><th data-en="Max(ms)" data-zh="\u6700\u5927(ms)">Max(ms)</th></tr>'
        for i, s in enumerate(stats[:15], 1):
            slowlog_html += f'<tr><td>{i}</td><td><strong>{s["command"]}</strong></td><td>{s["count"]}</td><td>{s["total_time_ms"]:.2f}</td><td>{s["avg_time_ms"]:.2f}</td><td>{s["max_time_ms"]:.2f}</td></tr>'
        slowlog_html += '</table>'
    else:
        slowlog_html = f'<p class="ok-msg" data-en="\u2705 No slow log records in last {_INSPECT_DAYS} days" data-zh="\u2705 \u8fd1 {_INSPECT_DAYS} \u5929\u65e0\u6162\u65e5\u5fd7\u8bb0\u5f55">\u2705 No slow log records in last {_INSPECT_DAYS} days</p>'

    # Alert HTML
    alert_html = ''
    # Alert rules config
    alert_html += '<h3 data-en="6.1 Alert Rule Configuration" data-zh="6.1 \u544a\u8b66\u89c4\u5219\u914d\u7f6e">6.1 Alert Rule Configuration</h3>'
    if alert_rules:
        alert_html += '<div class="table-scroll-h"><table><tr><th>#</th><th data-en="Rule Name" data-zh="\u89c4\u5219\u540d\u79f0">Rule Name</th><th data-en="Metric" data-zh="\u6307\u6807">Metric</th><th data-en="Threshold" data-zh="\u9608\u503c">Threshold</th><th data-en="Current Status" data-zh="\u5f53\u524d\u72b6\u6001">Current Status</th><th data-en="Enabled" data-zh="\u542f\u7528">Enabled</th><th data-en="Detection Period" data-zh="\u63a2\u6d4b\u5468\u671f">Detection Period</th><th data-en="Notification Group" data-zh="\u901a\u77e5\u7ec4">Notification Group</th></tr>'
        for i, r in enumerate(alert_rules, 1):
            thresholds = r.get('thresholds', {})
            # Build threshold text with emoji indicators like PolarDB
            th_parts = []
            for lvl, emoji in [('Critical', '\U0001F534'), ('Warn', '\U0001F7E1'), ('Info', '\U0001F535')]:
                if lvl in thresholds:
                    th_parts.append(f'{emoji} {thresholds[lvl]}')
            th_text = ' / '.join(th_parts) if th_parts else '-'

            state = r.get('state', '')
            state_cls = 'danger' if state == 'ALARM' else 'ok' if state == 'OK' else ''
            state_html = f'<span class="{state_cls}">{state}</span>' if state_cls else state

            enabled = r.get('enabled', False)
            enabled_html = '\u2705' if enabled else '\u274c'

            interval = r.get('interval', 60)
            interval_text = f'{interval}s'

            contact_groups = r.get('contact_groups', '')

            alert_html += f'<tr><td>{i}</td><td>{r.get("rule_name","")}</td><td><code>{r.get("metric","")}</code></td><td>{th_text}</td><td>{state_html}</td><td>{enabled_html}</td><td>{interval_text}</td><td>{contact_groups}</td></tr>'
        alert_html += '</table></div>'
        alert_html += f'<p data-en="Total: {len(alert_rules)} rules" data-zh="\u5171 {len(alert_rules)} \u6761\u89c4\u5219">Total: {len(alert_rules)} rules</p>'
    else:
        alert_html += '<p class="ok-msg" data-en="No alert rules configured" data-zh="\u672a\u68c0\u6d4b\u5230\u8be5\u5b9e\u4f8b\u7684\u544a\u8b66\u89c4\u5219">No alert rules configured</p>'
    # Alert history records
    alert_html += f'<h3 data-en="6.2 Alert Records" data-zh="6.2 \u544a\u8b66\u8bb0\u5f55">6.2 Alert Records</h3>'
    if alert_history:
        alert_html += '<div class="table-scroll-h"><table><tr><th>#</th><th data-en="Time" data-zh="\u65f6\u95f4">Time</th><th data-en="Level" data-zh="\u7ea7\u522b">Level</th><th data-en="Rule" data-zh="\u89c4\u5219">Rule</th><th data-en="Metric" data-zh="\u6307\u6807">Metric</th><th data-en="Node" data-zh="\u8282\u70b9">Node</th><th data-en="Current Value" data-zh="\u5f53\u524d\u503c">Current Value</th><th data-en="Threshold" data-zh="\u9608\u503c">Threshold</th><th data-en="Notification Status" data-zh="\u901a\u77e5\u72b6\u6001">Notification Status</th></tr>'
        for i, a in enumerate(alert_history[:20], 1):
            level_cls = 'danger' if a['level'] in ('P1', 'P2') else 'warn'
            alert_html += f'<tr class="{level_cls}"><td>{i}</td><td>{a["time"]}</td><td>{a["level"]}</td><td>{a.get("rule_name","")}</td><td>{a.get("metric","")}</td><td>{a.get("node_id","")}</td><td>{a.get("cur_value","")}</td><td>{a.get("threshold","")}</td><td>{a.get("send_status","")}</td></tr>'
        alert_html += '</table></div>'
        alert_html += f'<p data-en="Total: {len(alert_history)} records" data-zh="\u5171 {len(alert_history)} \u6761\u8bb0\u5f55">Total: {len(alert_history)} records</p>'
    else:
        alert_html += f'<p class="ok-msg" data-en="\u2705 No alert records in last {_INSPECT_DAYS} days" data-zh="\u2705 \u8fd1 {_INSPECT_DAYS} \u5929\u65e0\u544a\u8b66\u8bb0\u5f55">\u2705 No alert records in last {_INSPECT_DAYS} days</p>'

    # Compute conditional sections
    toc_session = '<a href="#sec-2" data-en="Sessions" data-zh="\u5f53\u524d\u4f1a\u8bdd">Sessions</a>' if 'session' in _INSPECT_ITEMS else ''
    toc_resource = '<a href="#sec-3" data-en="Resource Usage" data-zh="\u8d44\u6e90\u4f7f\u7528">Resource Usage</a>' if 'resource' in _INSPECT_ITEMS else ''
    toc_bigkey = '<a href="#sec-4" data-en="Big/Hot Key" data-zh="\u5927Key/\u70edKey">Big/Hot Key</a>' if 'bigkey' in _INSPECT_ITEMS else ''
    toc_slowlog = '<a href="#sec-5" data-en="Slow Log" data-zh="\u6162\u65e5\u5fd7">Slow Log</a>' if 'slowlog' in _INSPECT_ITEMS else ''
    toc_alert = '<a href="#sec-6" data-en="Alerts" data-zh="\u544a\u8b66\u5386\u53f2">Alerts</a>' if 'alert' in _INSPECT_ITEMS else ''

    sec_session = f'''<div class="section" id="sec-2">
        <h2 data-en="2. Current Sessions" data-zh="2. \u5f53\u524d\u4f1a\u8bdd">2. Current Sessions</h2>
        {session_html}
    </div>''' if 'session' in _INSPECT_ITEMS else ''

    # Build dynamic chart grid and JS config based on all_metrics
    chart_colors = {
        'CpuUsage': '#ef4444', 'ConnectionUsage': '#3b82f6', 'MemoryUsage': '#8b5cf6',
        'IntranetInRatio': '#10b981', 'IntranetOutRatio': '#f59e0b', 'AvgRt': '#06b6d4',
        'proxy_CpuUsage': '#ef4444', 'proxy_ConnectionUsage': '#3b82f6',
        'proxy_IntranetIn': '#10b981', 'proxy_IntranetOut': '#f59e0b',
        'proxy_AvgRt': '#06b6d4',
        'pmem_usage': '#a855f7', 'disk_usage': '#d946ef',
        'iops_usage': '#14b8a6',
    }

    # Multi-line chart colors for nodes
    node_colors = ['#5470c6', '#91cc75', '#ee6666', '#fac858', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']

    # Split charts into DB and Proxy groups (like PolarDB)
    db_chart_grid = ''
    proxy_chart_grid = ''
    chart_js_configs = ''

    # Prepare per-node time series for multi-line charts
    def _get_short_name(full_id):
        """Extract short node name for chart legend."""
        m = re.search(r'-((?:db|proxy|ro)\w*?-\d+)', full_id)
        if m:
            return m.group(1)
        name = full_id.split('#')[0]
        parts = name.split('-')
        for i, p in enumerate(parts):
            if p in ('db', 'proxy', 'ro') and i + 1 < len(parts) and parts[i + 1].isdigit():
                return f'{p}-{parts[i + 1]}'
        return name.split('-')[-2] + '-' + name.split('-')[-1] if len(name.split('-')) >= 2 else name

    for key, en_label in all_metrics:
        chart_id = f'chart-{key.replace("_", "-")}'
        zh_label = zh_metric_label_map.get(key, metric_label_map.get(key, en_label))
        # AvgRt -> microseconds; proxy traffic -> KB/s; everything else -> percentage
        is_rt_metric = 'AvgRt' in key
        if is_rt_metric:
            unit = 'us'
        elif key in ('proxy_IntranetIn', 'proxy_IntranetOut'):
            unit = 'KB/s'
        else:
            unit = '%'
        chart_html = f'<div class="chart-card"><h4 data-en="{en_label} ({unit})" data-zh="{zh_label} ({unit})">{en_label} ({unit})</h4><div id="{chart_id}" class="echart"></div></div>\n'

        # Determine if this is a multi-node chart
        is_proxy_chart = key.startswith('proxy_')
        base_key = key.replace('proxy_', '') if is_proxy_chart else key

        if node_details:
            nodes_dict = node_details.get('proxy_nodes' if is_proxy_chart else 'db_nodes', {})
            # Some metrics (disk_usage / iops_usage / pmem_usage) are queried at instance
            # level (no node_id), so they don't appear under per-node buckets. In that case
            # fall back to a single-line chart even when there are multiple nodes.
            has_node_data = any(
                nm.get(base_key, {}).get('values') for nm in nodes_dict.values()
            )
            if len(nodes_dict) > 1 and has_node_data:
                # Multi-line chart: each node gets its own series
                series_data = []
                sorted_nodes = sorted(nodes_dict.keys())
                for node_id in sorted_nodes:
                    node_metrics = nodes_dict[node_id]
                    node_values = node_metrics.get(base_key, {}).get('values', [])
                    # Proxy nodes use full node ID, DB nodes use short name
                    node_name = node_id if is_proxy_chart else _get_short_name(node_id)
                    ts_data = json.dumps([[v['timestamp'], v['value']] for v in node_values])
                    series_data.append({'name': node_name, 'data': ts_data})
                chart_js_configs += f"    {{id: '{chart_id}', series: {json.dumps(series_data)}, multi: true, colors: {json.dumps(node_colors[:len(sorted_nodes)])}, unit: '{unit}'}},\n"
            else:
                # Single-line chart
                color = chart_colors.get(key, '#666')
                chart_js_configs += f"    {{id: '{chart_id}', data: {chart_data.get(key, '[]')}, color: '{color}', unit: '{unit}'}},\n"
        else:
            # Standard architecture: single-line
            color = chart_colors.get(key, '#666')
            chart_js_configs += f"    {{id: '{chart_id}', data: {chart_data.get(key, '[]')}, color: '{color}', unit: '{unit}'}},\n"

        if is_proxy_chart:
            proxy_chart_grid += chart_html
        else:
            db_chart_grid += chart_html

    # Build chart sections
    charts_html = ''
    if has_proxy and proxy_chart_grid:
        charts_html += f'''<h3 style="margin-top:1.5rem;font-size:1rem;" data-en="Proxy Monitoring Trends" data-zh="Proxy \u76d1\u63a7\u8d8b\u52bf">Proxy Monitoring Trends</h3>
        <div class="chart-grid">{proxy_chart_grid}</div>'''
    if db_chart_grid:
        charts_html += f'''<h3 style="margin-top:1.5rem;font-size:1rem;" data-en="DB Monitoring Trends" data-zh="DB \u76d1\u63a7\u8d8b\u52bf">DB Monitoring Trends</h3>
        <div class="chart-grid">{db_chart_grid}</div>'''

    sec_resource = f'''<div class="section" id="sec-3">
        <h2 data-en="3. Resource Usage (Last {_INSPECT_DAYS} Days)" data-zh="3. \u8d44\u6e90\u4f7f\u7528\u60c5\u51b5\uff08\u8fd1 {_INSPECT_DAYS} \u5929\uff09">3. Resource Usage (Last {_INSPECT_DAYS} Days)</h2>
        {_render_node_details_table(node_details, inst_type)}
        {charts_html}
    </div>''' if 'resource' in _INSPECT_ITEMS else ''

    sec_bigkey = f'''<div class="section" id="sec-4">
        <h2 data-en="4. Big Key / Hot Key" data-zh="4. \u5927 Key / \u70ed Key">4. Big Key / Hot Key</h2>
        {bigkey_html}
    </div>''' if 'bigkey' in _INSPECT_ITEMS else ''

    sec_slowlog = f'''<div class="section" id="sec-5">
        <h2 data-en="5. Slow Log Statistics (Last {_INSPECT_DAYS} Days)" data-zh="5. \u6162\u65e5\u5fd7\u7edf\u8ba1\uff08\u8fd1 {_INSPECT_DAYS} \u5929\uff09">5. Slow Log Statistics (Last {_INSPECT_DAYS} Days)</h2>
        {slowlog_html}
    </div>''' if 'slowlog' in _INSPECT_ITEMS else ''

    sec_alert = f'''<div class="section" id="sec-6">
        <h2 data-en="6. Alert Rules &amp; History (Last {_INSPECT_DAYS} Days)" data-zh="6. \u544a\u8b66\u89c4\u5219\u4e0e\u5386\u53f2\uff08\u8fd1 {_INSPECT_DAYS} \u5929\uff09">6. Alert Rules &amp; History (Last {_INSPECT_DAYS} Days)</h2>
        {alert_html}
    </div>''' if 'alert' in _INSPECT_ITEMS else ''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redis / Tair Health Inspection - {instance_id}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root {{ --ok: #10b981; --warn: #f59e0b; --danger: #ef4444; --bg: #f8fafc; --card: #fff; --border: #e2e8f0; --text: #1e293b; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 1.5rem; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; }}
.header h1 {{ font-size: 1.4rem; margin-bottom: 0.3rem; }}
.header .meta {{ opacity: 0.9; font-size: 0.85rem; }}
.section {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem 1.5rem; margin-bottom: 1.2rem; }}
.section h2 {{ font-size: 1.1rem; color: #dc2626; margin-bottom: 0.8rem; padding-bottom: 0.4rem; border-bottom: 2px solid #e2e8f0; }}
.section h3 {{ font-size: 0.95rem; color: #334155; margin: 0.8rem 0 0.4rem 0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
th, td {{ padding: 0.4rem 0.6rem; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ background: #f1f5f9; font-weight: 600; position: sticky; top: 0; }}
code {{ background: #f1f5f9; padding: 2px 5px; border-radius: 3px; font-size: 0.78rem; word-break: break-all; }}
.ok {{ color: var(--ok); }} .warn {{ color: var(--warn); }} .danger {{ color: var(--danger); }}
.ok-msg {{ color: var(--ok); font-weight: 500; }}
.sug-list {{ margin: 0.3rem 0 0.8rem 1.2rem; line-height: 1.8; }}
.sug-list li {{ margin-bottom: 0.2rem; }}
.ver-ok {{ color: var(--ok); font-weight: 600; }}
.ver-upgrade {{ color: var(--warn); font-weight: 600; }}
.ver-major {{ color: var(--danger); font-weight: 600; }}
.info-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 0; }}
.info-item {{ padding: 0.45rem 0.8rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; }}
.info-item .label {{ color: #64748b; min-width: 180px; font-size: 0.8rem; flex-shrink: 0; margin-right: 0.5rem; }}
.info-item .value {{ font-weight: 500; font-size: 0.8rem; word-break: break-all; }}
.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 12px; margin-top: 0.8rem; }}
.chart-card {{ background: #f8fafc; border: 1px solid var(--border); border-radius: 6px; padding: 10px; }}
.chart-card h4 {{ margin: 0 0 4px 0; font-size: 0.85rem; color: #334155; }}
.echart {{ width: 100%; height: 250px; }}
.table-scroll {{ max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 4px; margin-top: 0.4rem; }}
.table-scroll table {{ margin: 0; }}
.table-scroll-h {{ max-height: 400px; overflow: auto; border: 1px solid var(--border); border-radius: 4px; margin-top: 0.4rem; }}
.table-scroll-h table {{ margin: 0; white-space: nowrap; }}
.role-badge {{ display: inline-block; font-size: 0.7rem; padding: 1px 5px; border-radius: 3px; background: #e0e7ff; color: #3730a3; margin-left: 4px; font-weight: 500; }}
.footer {{ text-align: center; color: #64748b; font-size: 0.8rem; margin-top: 1.5rem; }}
.toc {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 0.7rem 1.2rem; margin-bottom: 1.2rem; font-size: 0.85rem; }}
.toc a {{ color: #1e40af; margin-right: 1rem; text-decoration: none; white-space: nowrap; }}
.toc a:hover {{ text-decoration: underline; }}
.lang-switch {{ position: absolute; top: 1.5rem; right: 2rem; }}
.lang-toggle {{ background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.5); color: white; padding: 4px 14px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; font-weight: 500; transition: all 0.2s; user-select: none; }}
.lang-toggle:hover {{ background: rgba(255,255,255,0.35); }}
.header {{ position: relative; }}
@media (max-width: 768px) {{
    body {{ padding: 0.8rem; }}
    .info-grid {{ grid-template-columns: 1fr; }}
    .chart-grid {{ grid-template-columns: 1fr; }}
    .echart {{ height: 180px; }}
}}
@media print {{
    body {{ padding: 0; }}
    .section {{ break-inside: avoid; page-break-inside: avoid; }}
    .chart-grid {{ grid-template-columns: 1fr 1fr; }}
    .table-scroll {{ max-height: none; overflow: visible; }}
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1 data-en="Redis / Tair Instance Health Inspection Report" data-zh="Redis / Tair 实例健康巡检报告">Redis / Tair Instance Health Inspection Report</h1>
        <div class="meta">
            <span data-en="Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" data-zh="时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}">Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span> |
            <span data-en="Instance: {instance_id}" data-zh="实例: {instance_id}">Instance: {instance_id}</span> |
            <span data-en="Region: {region}" data-zh="区域: {region}">Region: {region}</span>
        </div>
        <div class="lang-switch"><button class="lang-toggle" id="btn-lang" onclick="toggleLang()">中文</button></div>
    </div>
    <div class="toc">
        <a href="#sec-1" data-en="Basic Info" data-zh="基本信息">Basic Info</a>
        {toc_session}
        {toc_resource}
        {toc_bigkey}
        {toc_slowlog}
        {toc_alert}
        <a href="#sec-7" data-en="Conclusions" data-zh="巡检结论">Conclusions</a>
    </div>
    <div class="section" id="sec-1">
        <h2 data-en="1. Instance Basic Information" data-zh="1. 实例基本信息">1. Instance Basic Information</h2>
        <div class="info-grid">
            <div class="info-item"><span class="label" data-en="Instance ID" data-zh="实例 ID">Instance ID</span><span class="value">{instance_id}</span></div>
            <div class="info-item"><span class="label" data-en="Instance Name" data-zh="实例名称">Instance Name</span><span class="value">{inst_name}</span></div>
            <div class="info-item"><span class="label" data-en="Engine Version" data-zh="引擎版本">Engine Version</span><span class="value">{engine_ver}</span></div>
            <div class="info-item"><span class="label" data-en="Minor Version" data-zh="内核小版本">Minor Version</span><span class="value">{minor_ver}</span></div>
            {version_status_html}
            {proxy_minor_ver_html}
            <div class="info-item"><span class="label" data-en="Instance Spec" data-zh="实例规格">Instance Spec</span><span class="value" data-en="{inst_spec_en}" data-zh="{inst_spec_zh}">{inst_spec_en}</span></div>
            <div class="info-item"><span class="label" data-en="Architecture" data-zh="架构类型">Architecture</span><span class="value" data-en="{arch_en}" data-zh="{arch_zh}">{arch_en}</span></div>
            <div class="info-item"><span class="label" data-en="Status" data-zh="状态">Status</span><span class="value" data-en="{inst_status}" data-zh="{inst_status_zh}">{inst_status}</span></div>
            <div class="info-item"><span class="label" data-en="Max Connections" data-zh="最大连接数">Max Connections</span><span class="value">{max_conn}</span></div>
            <div class="info-item"><span class="label" data-en="Max Bandwidth" data-zh="最大带宽">Max Bandwidth</span><span class="value">{max_bw} MB/s</span></div>
            <div class="info-item"><span class="label" data-en="Create Time" data-zh="\u521b\u5efa\u65f6\u95f4">Create Time</span><span class="value">{create_time}</span></div>
        </div>
        {node_topology_html}
    </div>
    {sec_session}
    {sec_resource}
    {sec_bigkey}
    {sec_slowlog}
    {sec_alert}
    <div class="section" id="sec-7">
        <h2 data-en="7. Inspection Conclusions & Recommendations" data-zh="7. 巡检结论与建议">7. Inspection Conclusions & Recommendations</h2>
        {sug_html}
    </div>
    <div class="footer" data-en="Generated by alibabacloud-kvstore-health-inspection" data-zh="由 alibabacloud-kvstore-health-inspection 生成">Generated by alibabacloud-kvstore-health-inspection</div>
</div>
<script>
var chartConfigs = [
{chart_js_configs}];
chartConfigs.forEach(function(cfg) {{
    var dom = document.getElementById(cfg.id);
    if (!dom) return;

    if (cfg.multi && cfg.series) {{
        // Multi-line chart: each node gets its own series
        var chart = echarts.init(dom);
        var seriesList = cfg.series.map(function(s, i) {{
            var color = cfg.colors[i % cfg.colors.length];
            return {{
                name: s.name,
                type: 'line',
                data: JSON.parse(s.data),
                smooth: true,
                symbol: 'none',
                lineStyle: {{color: color, width: 1.5}}
            }};
        }});
        // Use first series for x-axis
        var xData = seriesList[0] && seriesList[0].data ? seriesList[0].data.map(function(d) {{ return d[0]; }}) : [];
        seriesList.forEach(function(s) {{
            s.data = s.data.map(function(d) {{ return d[1]; }});
        }});
        chart.setOption({{
            tooltip: {{
                trigger: 'axis',
                formatter: function(params) {{
                    var time = params[0].axisValue.replace('T',' ').replace('Z','');
                    var lines = [time];
                    params.forEach(function(p) {{
                        lines.push(p.marker + p.seriesName + ': ' + p.value.toFixed(2) + ' ' + cfg.unit);
                    }});
                    return lines.join('<br/>');
                }}
            }},
            legend: {{
                data: cfg.series.map(function(s) {{ return s.name; }}),
                top: 0,
                textStyle: {{fontSize: 10}}
            }},
            xAxis: {{type: 'category', data: xData, axisLabel: {{fontSize: 9, rotate: 30, formatter: function(v) {{ return v.slice(5,16).replace('T',' '); }} }} }},
            yAxis: {{type: 'value', axisLabel: {{formatter: function(v) {{ return v + ' ' + cfg.unit; }}, fontSize: 10}}}},
            dataZoom: [{{type: 'inside', start: 0, end: 100}}, {{type: 'slider', start: 0, end: 100, height: 18, bottom: 4, borderColor: '#e2e8f0', fillerColor: 'rgba(99,102,241,0.15)', handleSize: '60%'}}],
            series: seriesList,
            grid: {{left: 45, right: 15, top: 30, bottom: 55}}
        }});
        window.addEventListener('resize', function() {{ chart.resize(); }});
    }} else if (cfg.data && cfg.data.length > 0) {{
        // Single-line chart
        var chart = echarts.init(dom);
        var xData = cfg.data.map(function(d) {{ return d[0]; }});
        var yData = cfg.data.map(function(d) {{ return d[1]; }});
        chart.setOption({{
            tooltip: {{trigger: 'axis', formatter: function(p) {{ return p[0].axisValue.replace('T',' ').replace('Z','') + '<br/>' + p[0].value.toFixed(2) + ' ' + cfg.unit; }} }},
            xAxis: {{type: 'category', data: xData, axisLabel: {{fontSize: 9, rotate: 30, formatter: function(v) {{ return v.slice(5,16).replace('T',' '); }} }} }},
            yAxis: {{type: 'value', axisLabel: {{formatter: function(v) {{ return v + ' ' + cfg.unit; }}, fontSize: 10}}}},
            dataZoom: [{{type: 'inside', start: 0, end: 100}}, {{type: 'slider', start: 0, end: 100, height: 18, bottom: 4, borderColor: '#e2e8f0', fillerColor: 'rgba(99,102,241,0.15)', handleSize: '60%'}}],
            series: [{{type: 'line', data: yData, smooth: true, symbol: 'none', lineStyle: {{color: cfg.color, width: 1.5}}, areaStyle: {{color: cfg.color + '20'}}}}],
            grid: {{left: 45, right: 15, top: 15, bottom: 55}}
        }});
        window.addEventListener('resize', function() {{ chart.resize(); }});
    }}
}});
var _curLang = localStorage.getItem('kvstore-inspection-lang') || 'en';
function applyLang() {{
    document.querySelectorAll('[data-' + _curLang + ']').forEach(function(el) {{
        el.textContent = el.getAttribute('data-' + _curLang);
    }});
    document.getElementById('btn-lang').textContent = _curLang === 'en' ? '中文' : 'EN';
}}
applyLang();
function toggleLang() {{
    _curLang = _curLang === 'en' ? 'zh' : 'en';
    localStorage.setItem('kvstore-inspection-lang', _curLang);
    applyLang();
}}
</script>
</body>
</html>'''
    return html


def _status_icon(peak):
    """Return status icon string based on peak value."""
    if peak > 80:
        return '❌ HIGH'
    elif peak > 60:
        return '⚠️ MED'
    return '✅ OK'


def render_text(data):
    """Render plain text report with box-drawing characters."""
    lines = []
    p = lines.append

    p('')
    p('┌' + '─' * 78 + '┐')
    p('│' + ' Redis / Tair Instance Health Inspection Report'.center(78) + '│')
    p('└' + '─' * 78 + '┘')
    p(f'  Inspection Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    p(f'  Instance ID:  {data["instance_id"]}')
    p(f'  Region:       {data["region"]}')
    if _CLI_PROFILE:
        p(f'  Profile:      {_CLI_PROFILE}')

    ii = data.get('instance_info', {})
    ev = data.get('engine_version', {}) or {}

    # Section 1: Basic Info (always shown)
    p('')
    p('═' * 80)
    p(' 1. Instance Basic Information')
    p('═' * 80)
    p('')
    p(f'  ┌{"─"*30}┬{"─"*46}┐')
    p(f'  │ {"Item":<28} │ {"Value":<44} │')
    p(f'  ├{"─"*30}┼{"─"*46}┤')
    p(f'  │ {"Instance ID":<28} │ {data["instance_id"]:<44} │')
    p(f'  │ {"Instance Name":<28} │ {ii.get("InstanceName", "N/A"):<44} │')
    p(f'  │ {"Engine Version":<28} │ {ii.get("EngineVersion", "N/A"):<44} │')
    minor = ev.get('minor_version', 'N/A')
    p(f'  │ {"Minor Version":<28} │ {minor:<44} │')
    proxy_v = ev.get('proxy_minor_version', '')
    if proxy_v:
        p(f'  │ {"Proxy Minor Version":<28} │ {proxy_v:<44} │')
    spec_en, spec_zh = format_instance_spec(ii) if ii else ('N/A', 'N/A')
    p(f'  │ {"Instance Spec":<28} │ {spec_en:<44} │')
    arch_en, arch_zh = format_architecture(ii) if ii else ('N/A', 'N/A')
    p(f'  │ {"Architecture":<28} │ {arch_en:<44} │')
    p(f'  │ {"Status":<28} │ {ii.get("InstanceStatus", "N/A"):<44} │')
    p(f'  │ {"Max Connections":<28} │ {str(ii.get("Connections", "N/A")):<44} │')
    p(f'  │ {"Max Bandwidth":<28} │ {str(ii.get("Bandwidth", "N/A")) + " MB/s":<44} │')
    p(f'  │ {"Create Time":<28} │ {ii.get("CreateTime", "N/A"):<44} │')
    p(f'  └{"─"*30}┴{"─"*46}┘')

    # Section 2: Sessions
    if 'session' in _INSPECT_ITEMS:
        p('')
        p('═' * 80)
        p(' 2. Current Sessions')
        p('═' * 80)
        si = data.get('session_info', {})
        if si:
            p(f'  Max Connections:       {si.get("max_connections", "N/A")}')
            p(f'  Used Connections (Peak): {si.get("used_connections_peak", 0)}')
            p(f'  Connection Usage (Avg):  {si.get("connection_usage_avg", 0):.2f}%')
            p(f'  Connection Usage (Peak): {si.get("connection_usage_peak", 0):.2f}%')
            proxy_avg = si.get('proxy_connection_usage_avg', 0)
            proxy_peak = si.get('proxy_connection_usage_peak', 0)
            if proxy_avg or proxy_peak:
                p(f'  Proxy Conn (Avg/Peak):   {proxy_avg:.2f}% / {proxy_peak:.2f}%')
            real = si.get('real_sessions', {})
            if real:
                p(f'  Real-time Sessions (DAS): {real.get("total", 0)}')
                src_stats = real.get('source_stats', [])
                if src_stats:
                    p('')
                    p('  [Source Statistics - Top 10 Client IPs]')
                    p(f'  ┌{"─"*30}┬{"─"*14}┐')
                    p(f'  │ {"Client IP":<28} │ {"Sessions":<12} │')
                    p(f'  ├{"─"*30}┼{"─"*14}┤')
                    for src in sorted(src_stats, key=lambda x: int(x.get('Count', 0)), reverse=True)[:10]:
                        p(f'  │ {src.get("Key", ""):<28} │ {str(src.get("Count", 0)):<12} │')
                    p(f'  └{"─"*30}┴{"─"*14}┘')
        else:
            p('  Session details not available (DAS API)')

    # Section 3: Resource Usage
    if 'resource' in _INSPECT_ITEMS:
        p('')
        p('═' * 80)
        p(f' 3. Resource Usage (Last {_INSPECT_DAYS} Days)')
        p('═' * 80)
        rd = data.get('resource_data', {})
        metrics_list = [
            ('CpuUsage', 'CPU'),
            ('ConnectionUsage', 'Connection'),
            ('MemoryUsage', 'Memory'),
            ('IntranetInRatio', 'Input BW'),
            ('IntranetOutRatio', 'Output BW'),
        ]
        p('')
        p(f'  ┌{"─"*16}┬{"─"*20}┬{"─"*20}┬{"─"*16}┐')
        p(f'  │ {"Metric":<14} │ {"Average":<18} │ {"Peak":<18} │ {"Status":<14} │')
        p(f'  ├{"─"*16}┼{"─"*20}┼{"─"*20}┼{"─"*16}┤')
        for key, label in metrics_list:
            d = rd.get(key, {})
            if not d:
                continue
            avg = d.get('avg', 0)
            peak = d.get('peak', 0)
            icon = _status_icon(peak)
            avg_s = f'{avg:.2f}%'
            peak_s = f'{peak:.2f}%'
            p(f'  │ {label:<14} │ {avg_s:<18} │ {peak_s:<18} │ {icon:<14} │')
        p(f'  └{"─"*16}┴{"─"*20}┴{"─"*20}┴{"─"*16}┘')
        # Proxy metrics
        proxy_metrics = [
            ('proxy_CpuUsage', 'Proxy CPU'),
            ('proxy_ConnectionUsage', 'Proxy Conn'),
            ('proxy_IntranetIn', 'Proxy In KB/s'),
            ('proxy_IntranetOut', 'Proxy Out KB/s'),
        ]
        has_proxy = any(rd.get(k) for k, _ in proxy_metrics)
        if has_proxy:
            p('')
            p('  [Proxy Metrics]')
            p(f'  ┌{"─"*16}┬{"─"*20}┬{"─"*20}┬{"─"*16}┐')
            p(f'  │ {"Metric":<14} │ {"Average":<18} │ {"Peak":<18} │ {"Status":<14} │')
            p(f'  ├{"─"*16}┼{"─"*20}┼{"─"*20}┼{"─"*16}┤')
            for key, label in proxy_metrics:
                d = rd.get(key, {})
                if not d:
                    continue
                _suffix = ' KB/s' if key in ('proxy_IntranetIn', 'proxy_IntranetOut') else '%'
                avg_s = f'{d.get("avg", 0):.2f}{_suffix}'
                peak_s = f'{d.get("peak", 0):.2f}{_suffix}'
                _icon = '-' if key in ('proxy_IntranetIn', 'proxy_IntranetOut') else _status_icon(d.get("peak", 0))
                p(f'  │ {label:<14} │ {avg_s:<18} │ {peak_s:<18} │ {_icon:<14} │')
            p(f'  └{"─"*16}┴{"─"*20}┴{"─"*20}┴{"─"*16}┘')

    # Section 4: Big/Hot Keys
    if 'bigkey' in _INSPECT_ITEMS:
        p('')
        p('═' * 80)
        p(' 4. Big Key / Hot Key')
        p('═' * 80)
        bhk = data.get('big_hot_keys', {})
        large_keys = bhk.get('large_keys', [])
        big_keys = bhk.get('big_keys', [])
        hot_keys = bhk.get('hot_keys', [])
        if large_keys:
            p('')
            p('  [Large Keys (by Memory) - Top 10]')
            p(f'  {"#":<3}  {"DB":<3}  {"Type":<8}  {"Memory":<12}  Key')
            p(f'  {"─"*3}  {"─"*3}  {"─"*8}  {"─"*12}  {"─"*30}')
            for i, k in enumerate(large_keys[:10], 1):
                ds = int(k.get('data_size', 0))
                size_str = f'{ds/1024:.1f}KB' if ds < 1024*1024 else f'{ds/(1024*1024):.2f}MB'
                p(f'  {i:<3}  {k.get("db", 0):<3}  {k.get("type", ""):<8}  {size_str:<12}  {str(k.get("key", ""))[:40]}')
        if big_keys:
            p('')
            p('  [Big Keys (by Elements) - Top 10]')
            p(f'  {"#":<3}  {"DB":<3}  {"Type":<8}  {"Elements":<10}  Key')
            p(f'  {"─"*3}  {"─"*3}  {"─"*8}  {"─"*10}  {"─"*30}')
            for i, k in enumerate(big_keys[:10], 1):
                p(f'  {i:<3}  {k.get("db", 0):<3}  {k.get("type", ""):<8}  {str(k.get("size", 0)):<10}  {str(k.get("key", ""))[:40]}')
        if not large_keys and not big_keys:
            p(f'  ✅ No big keys found in last {_INSPECT_DAYS} days')
        if hot_keys:
            p('')
            p('  [Hot Keys (by QPS) - Top 10]')
            p(f'  {"#":<3}  {"DB":<3}  {"Type":<8}  {"QPS":<10}  Key')
            p(f'  {"─"*3}  {"─"*3}  {"─"*8}  {"─"*10}  {"─"*30}')
            for i, k in enumerate(hot_keys[:10], 1):
                p(f'  {i:<3}  {k.get("db", 0):<3}  {k.get("type", ""):<8}  {str(k.get("hot", "")):<10}  {str(k.get("key", ""))[:40]}')
        elif not bhk.get('high_traffic_keys', []):
            p(f'  ✅ No hot keys found in last {_INSPECT_DAYS} days')

    # Section 5: Slow Log
    if 'slowlog' in _INSPECT_ITEMS:
        p('')
        p('═' * 80)
        p(f' 5. Slow Log Statistics (Last {_INSPECT_DAYS} Days)')
        p('═' * 80)
        sl = data.get('slow_logs', {})
        stats = sl.get('stats', [])
        total = sl.get('total_count', 0)
        if stats:
            p(f'  Total: {total} records')
            p('')
            p(f'  {"#":<3}  {"Command":<12}  {"Count":<7}  {"Total(ms)":<12}  {"Avg(ms)":<10}  {"Max(ms)":<10}')
            p(f'  {"─"*3}  {"─"*12}  {"─"*7}  {"─"*12}  {"─"*10}  {"─"*10}')
            for i, s in enumerate(stats[:15], 1):
                total_s = f'{s["total_time_ms"]:.2f}'
                avg_s = f'{s["avg_time_ms"]:.2f}'
                max_s = f'{s["max_time_ms"]:.2f}'
                p(f'  {i:<3}  {s["command"]:<12}  {str(s["count"]):<7}  {total_s:<12}  {avg_s:<10}  {max_s:<10}')
        else:
            p(f'  ✅ No slow log records in last {_INSPECT_DAYS} days')

    # Section 6: Alerts
    if 'alert' in _INSPECT_ITEMS:
        p('')
        p('═' * 80)
        p(f' 6. Alert Rules & History (Last {_INSPECT_DAYS} Days)')
        p('═' * 80)
        ar = data.get('alert_rules', [])
        if ar:
            p(f'  Alert Rules: {len(ar)} configured')
            p(f'  ┌{"─"*24}┬{"─"*18}┬{"─"*10}┬{"─"*10}┬{"─"*10}┬{"─"*8}┐')
            p(f'  │ {"Rule Name":<22} │ {"Metric":<16} │ {"Critical":<8} │ {"Warn":<8} │ {"Info":<8} │ {"State":<6} │')
            p(f'  ├{"─"*24}┼{"─"*18}┼{"─"*10}┼{"─"*10}┼{"─"*10}┼{"─"*8}┤')
            for r in ar:
                th = r.get('thresholds', {})
                p(f'  │ {r.get("rule_name", "")[:22]:<22} │ {str(r.get("metric", ""))[:16]:<16} │ {str(th.get("Critical", "-")):<8} │ {str(th.get("Warn", "-")):<8} │ {str(th.get("Info", "-")):<8} │ {r.get("state", ""):<6} │')
            p(f'  └{"─"*24}┴{"─"*18}┴{"─"*10}┴{"─"*10}┴{"─"*10}┴{"─"*8}┘')
        else:
            p('  No alert rules configured')
        ah = data.get('alert_history', [])
        if ah:
            p(f'')
            p(f'  Alert Records: {len(ah)} total')
            p(f'  ┌{"─"*18}┬{"─"*5}┬{"─"*16}┬{"─"*14}┬{"─"*10}┬{"─"*10}┐')
            p(f'  │ {"Time":<16} │ {"Lvl":<3} │ {"Rule":<14} │ {"Metric":<12} │ {"Value":<8} │ {"Threshold":<8} │')
            p(f'  ├{"─"*18}┼{"─"*5}┼{"─"*16}┼{"─"*14}┼{"─"*10}┼{"─"*10}┤')
            for a in ah[:20]:
                p(f'  │ {a.get("time", ""):<16} │ {a["level"]:<3} │ {str(a.get("rule_name", ""))[:14]:<14} │ {str(a.get("metric", ""))[:12]:<12} │ {str(a.get("cur_value", "")):<8} │ {str(a.get("threshold", "")):<8} │')
            p(f'  └{"─"*18}┴{"─"*5}┴{"─"*16}┴{"─"*14}┴{"─"*10}┴{"─"*10}┘')
        else:
            p(f'  No alert records in last {_INSPECT_DAYS} days ✅')

    # Section 7: Conclusions
    p('')
    p('═' * 80)
    p(' 7. Inspection Conclusions & Recommendations')
    p('═' * 80)
    suggestions = data.get('suggestions', [])
    if not suggestions:
        p('  No significant issues found ✅')
    else:
        danger_items = [s for s in suggestions if s[0] == 'danger']
        warn_items = [s for s in suggestions if s[0] == 'warn']
        if danger_items:
            p('')
            p('  [🔴 High Risk]')
            for i, s in enumerate(danger_items, 1):
                msg = s[1] if len(s) > 2 else s[1]
                p(f'  {i}. {msg}')
        if warn_items:
            p('')
            p('  [🟡 Medium Risk]')
            for i, s in enumerate(warn_items, 1):
                msg = s[1] if len(s) > 2 else s[1]
                p(f'  {i}. {msg}')

    p('')
    p('─' * 80)
    p('  Generated by alibabacloud-kvstore-health-inspection')
    p('')

    return '\n'.join(lines)


def render_markdown(data):
    """Render markdown report."""
    lines = []
    p = lines.append

    p(f'# Redis / Tair Instance Health Inspection Report')
    p('')
    p(f'- **Time**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    p(f'- **Instance**: {data["instance_id"]}')
    p(f'- **Region**: {data["region"]}')
    if _CLI_PROFILE:
        p(f'- **Profile**: {_CLI_PROFILE}')
    p('')

    ii = data.get('instance_info', {})
    ev = data.get('engine_version', {}) or {}

    # Section 1: Basic Info
    p('## 1. Instance Basic Information')
    p('')
    p('| Item | Value |')
    p('|------|-------|')
    p(f'| Instance ID | {data["instance_id"]} |')
    p(f'| Instance Name | {ii.get("InstanceName", "N/A")} |')
    p(f'| Engine Version | {ii.get("EngineVersion", "N/A")} |')
    p(f'| Minor Version | {ev.get("minor_version", "N/A")} |')
    proxy_v = ev.get('proxy_minor_version', '')
    if proxy_v:
        p(f'| Proxy Minor Version | {proxy_v} |')
    spec_en, _ = format_instance_spec(ii) if ii else ('N/A', 'N/A')
    p(f'| Instance Spec | {spec_en} |')
    arch_en, _ = format_architecture(ii) if ii else ('N/A', 'N/A')
    p(f'| Architecture | {arch_en} |')
    p(f'| Status | {ii.get("InstanceStatus", "N/A")} |')
    p(f'| Max Connections | {ii.get("Connections", "N/A")} |')
    p(f'| Max Bandwidth | {ii.get("Bandwidth", "N/A")} MB/s |')
    p(f'| Create Time | {ii.get("CreateTime", "N/A")} |')
    p('')

    # Section 2: Sessions
    if 'session' in _INSPECT_ITEMS:
        p('## 2. Current Sessions')
        p('')
        si = data.get('session_info', {})
        if si:
            p(f'- Max Connections: **{si.get("max_connections", "N/A")}**')
            p(f'- Used Connections (Peak): **{si.get("used_connections_peak", 0)}**')
            p(f'- Connection Usage (Avg/Peak): **{si.get("connection_usage_avg", 0):.2f}% / {si.get("connection_usage_peak", 0):.2f}%**')
            proxy_avg = si.get('proxy_connection_usage_avg', 0)
            proxy_peak = si.get('proxy_connection_usage_peak', 0)
            if proxy_avg or proxy_peak:
                p(f'- Proxy Conn (Avg/Peak): **{proxy_avg:.2f}% / {proxy_peak:.2f}%**')
            real = si.get('real_sessions', {})
            if real:
                p(f'')
                p(f'**Real-time Sessions (DAS): {real.get("total", 0)}**')
                src_stats = real.get('source_stats', [])
                if src_stats:
                    p('')
                    p('### Source Statistics (Top 10)')
                    p('')
                    p('| Client IP | Sessions |')
                    p('|-----------|----------|')
                    for src in sorted(src_stats, key=lambda x: int(x.get('Count', 0)), reverse=True)[:10]:
                        p(f'| {src.get("Key", "")} | {src.get("Count", 0)} |')
        else:
            p('Session details not available (DAS API)')
        p('')

    # Section 3: Resource Usage
    if 'resource' in _INSPECT_ITEMS:
        p(f'## 3. Resource Usage (Last {_INSPECT_DAYS} Days)')
        p('')
        rd = data.get('resource_data', {})
        metrics_list = [
            ('CpuUsage', 'CPU'),
            ('ConnectionUsage', 'Connection'),
            ('MemoryUsage', 'Memory'),
            ('IntranetInRatio', 'Input BW'),
            ('IntranetOutRatio', 'Output BW'),
        ]
        p('| Metric | Average | Peak | Status |')
        p('|--------|---------|------|--------|')
        for key, label in metrics_list:
            d = rd.get(key, {})
            if not d:
                continue
            avg = d.get('avg', 0)
            peak = d.get('peak', 0)
            icon = _status_icon(peak)
            p(f'| {label} | {avg:.2f}% | {peak:.2f}% | {icon} |')
        proxy_metrics = [
            ('proxy_CpuUsage', 'Proxy CPU'),
            ('proxy_ConnectionUsage', 'Proxy Conn'),
            ('proxy_IntranetIn', 'Proxy In KB/s'),
            ('proxy_IntranetOut', 'Proxy Out KB/s'),
        ]
        has_proxy = any(rd.get(k) for k, _ in proxy_metrics)
        if has_proxy:
            p('')
            p('### Proxy Metrics')
            p('')
            p('| Metric | Average | Peak | Status |')
            p('|--------|---------|------|--------|')
            for key, label in proxy_metrics:
                d = rd.get(key, {})
                if not d:
                    continue
                _suffix = ' KB/s' if key in ('proxy_IntranetIn', 'proxy_IntranetOut') else '%'
                _icon = '-' if key in ('proxy_IntranetIn', 'proxy_IntranetOut') else _status_icon(d.get("peak", 0))
                p(f'| {label} | {d.get("avg", 0):.2f}{_suffix} | {d.get("peak", 0):.2f}{_suffix} | {_icon} |')
        p('')

    # Section 4: Big/Hot Keys
    if 'bigkey' in _INSPECT_ITEMS:
        p('## 4. Big Key / Hot Key')
        p('')
        bhk = data.get('big_hot_keys', {})
        large_keys = bhk.get('large_keys', [])
        big_keys = bhk.get('big_keys', [])
        hot_keys = bhk.get('hot_keys', [])
        if large_keys:
            p('### Large Keys (by Memory)')
            p('')
            p('| # | DB | Type | Memory | Key |')
            p('|---|----|------|--------|-----|')
            for i, k in enumerate(large_keys[:10], 1):
                ds = int(k.get('data_size', 0))
                size_str = f'{ds/1024:.1f}KB' if ds < 1024*1024 else f'{ds/(1024*1024):.2f}MB'
                p(f'| {i} | {k.get("db", 0)} | {k.get("type", "")} | {size_str} | `{str(k.get("key", ""))[:50]}` |')
            p('')
        if big_keys:
            p('### Big Keys (by Elements)')
            p('')
            p('| # | DB | Type | Elements | Key |')
            p('|---|----|------|----------|-----|')
            for i, k in enumerate(big_keys[:10], 1):
                p(f'| {i} | {k.get("db", 0)} | {k.get("type", "")} | {k.get("size", 0)} | `{str(k.get("key", ""))[:50]}` |')
            p('')
        if not large_keys and not big_keys:
            p(f'✅ No big keys found in last {_INSPECT_DAYS} days')
            p('')
        if hot_keys:
            p('### Hot Keys (by QPS)')
            p('')
            p('| # | DB | Type | QPS | Key |')
            p('|---|----|------|-----|-----|')
            for i, k in enumerate(hot_keys[:10], 1):
                p(f'| {i} | {k.get("db", 0)} | {k.get("type", "")} | {k.get("hot", "")} | `{str(k.get("key", ""))[:50]}` |')
            p('')
        elif not large_keys and not big_keys:
            p(f'✅ No hot keys found in last {_INSPECT_DAYS} days')
            p('')

    # Section 5: Slow Log
    if 'slowlog' in _INSPECT_ITEMS:
        p(f'## 5. Slow Log Statistics (Last {_INSPECT_DAYS} Days)')
        p('')
        sl = data.get('slow_logs', {})
        stats = sl.get('stats', [])
        total = sl.get('total_count', 0)
        if stats:
            p(f'**Total: {total} records**')
            p('')
            p('| # | Command | Count | Total(ms) | Avg(ms) | Max(ms) |')
            p('|---|---------|-------|-----------|---------|---------|')
            for i, s in enumerate(stats[:15], 1):
                p(f'| {i} | **{s["command"]}** | {s["count"]} | {s["total_time_ms"]:.2f} | {s["avg_time_ms"]:.2f} | {s["max_time_ms"]:.2f} |')
        else:
            p(f'✅ No slow log records in last {_INSPECT_DAYS} days')
        p('')

    # Section 6: Alerts
    if 'alert' in _INSPECT_ITEMS:
        p(f'## 6. Alert Rules & History (Last {_INSPECT_DAYS} Days)')
        p('')
        ar = data.get('alert_rules', [])
        if ar:
            p(f'**Alert Rules: {len(ar)} configured**')
            p('')
            p('| Rule Name | Metric | Critical | Warn | Info | State |')
            p('|-----------|--------|----------|------|------|-------|')
            for r in ar:
                th = r.get('thresholds', {})
                state = r.get('state', '')
                state_icon = '🔴' if state == 'ALARM' else '🟢' if state == 'OK' else ''
                p(f'| {r.get("rule_name", "")} | `{r.get("metric", "")}` | {th.get("Critical", "-")} | {th.get("Warn", "-")} | {th.get("Info", "-")} | {state_icon} {state} |')
            p('')
        else:
            p('No alert rules configured')
            p('')
        ah = data.get('alert_history', [])
        if ah:
            p(f'**Alert Records: {len(ah)} total**')
            p('')
            p('| Time | Level | Rule | Metric | Value | Threshold |')
            p('|------|-------|------|--------|-------|-----------|')
            for a in ah[:20]:
                level_icon = '🔴' if a['level'] in ('P1', 'P2') else '🟡'
                p(f'| {a.get("time", "")} | {level_icon} {a["level"]} | {a.get("rule_name", "")} | {a.get("metric", "")} | {a.get("cur_value", "")} | {a.get("threshold", "")} |')
        else:
            p(f'No alert records in last {_INSPECT_DAYS} days ✅')
        p('')

    # Section 7: Conclusions
    p('## 7. Inspection Conclusions & Recommendations')
    p('')
    suggestions = data.get('suggestions', [])
    if not suggestions:
        p('✅ **No significant issues found.**')
    else:
        danger_items = [s for s in suggestions if s[0] == 'danger']
        warn_items = [s for s in suggestions if s[0] == 'warn']
        if danger_items:
            p('### 🔴 High Risk')
            p('')
            for i, s in enumerate(danger_items, 1):
                msg = s[1] if len(s) > 2 else s[1]
                p(f'{i}. {msg}')
            p('')
        if warn_items:
            p('### 🟡 Medium Risk')
            p('')
            for i, s in enumerate(warn_items, 1):
                msg = s[1] if len(s) > 2 else s[1]
                p(f'{i}. {msg}')
    p('')
    p('---')
    p('*Generated by alibabacloud-kvstore-health-inspection*')
    p('')

    return '\n'.join(lines)


def inspect_single_instance(instance_id, region=None, output_dir=None, report_format='html'):
    """Perform health inspection for a single instance."""
    print(f'\n{"="*60}')
    print(f'Inspecting Redis instance: {instance_id}')
    print(f'{"="*60}')

    if not region:
        region = find_region(instance_id)
        if not region:
            print(f'ERROR: Cannot find instance {instance_id} in any region')
            return None

    print('Instance info...', end=' ', flush=True)
    instance_info = get_instance_info(instance_id, region)
    if not instance_info:
        print(f'ERROR: Failed to get instance info ({_last_cli_error})')
        return None
    print('done')

    arch_type = get_architecture_type(instance_info)
    inst_type = get_instance_type(instance_info)
    extra_metrics = get_instance_type_extra_metrics(inst_type)
    print(f'   Architecture: {arch_type}')
    if inst_type != 'regular':
        print(f'   Instance Type: Tair {inst_type}')

    engine_version = get_engine_version(instance_id, region)

    topology_details = None
    if arch_type != 'standard':
        topo = get_topology_nodes(instance_id, region)
        topology_details = {
            'db_node_details': topo.get('db_node_details', []),
            'proxy_node_details': topo.get('proxy_node_details', []),
        }

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=_INSPECT_DAYS)
    start_time = start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Conditionally collect data based on --item selection
    resource_data = {}
    session_info = {}
    big_hot_keys = {}
    slow_logs = {}
    alert_history = []
    alert_rules = []

    if 'resource' in _INSPECT_ITEMS:
        print('Resource usage...', end=' ', flush=True)
        resource_data, node_details = get_resource_usage(instance_id, region, arch_type, start_time, end_time,
                                           extra_metrics=extra_metrics, inst_type=inst_type)
        print('done')

    if 'session' in _INSPECT_ITEMS:
        print('Session info...', end=' ', flush=True)
        session_info = get_session_info(instance_id, region, arch_type, resource_data, instance_info)
        print('done')

    if 'bigkey' in _INSPECT_ITEMS:
        print('Big/Hot keys...', end=' ', flush=True)
        big_hot_keys = get_big_hot_keys(instance_id, region)
        print('done')

    if 'slowlog' in _INSPECT_ITEMS:
        print('Slow logs...', end=' ', flush=True)
        slow_logs = get_slow_logs(instance_id, region)
        print('done')

    if 'alert' in _INSPECT_ITEMS:
        print('Alert history...', end=' ', flush=True)
        alert_history = get_alert_history(instance_id, start_time, end_time)
        alert_rules = get_alert_rules(instance_id)
        print('done')

    suggestions = format_suggestions(resource_data, slow_logs, big_hot_keys, alert_history, engine_version)

    report_data = {
        'instance_id': instance_id,
        'region': region,
        'instance_info': instance_info,
        'engine_version': engine_version,
        'topology_details': topology_details,
        'resource_data': resource_data,
        'node_details': node_details,  # 添加节点级别详情
        'instance_type': inst_type,  # 实例类型 (pena/essd/regular)
        'session_info': session_info,
        'big_hot_keys': big_hot_keys,
        'slow_logs': slow_logs,
        'alert_history': alert_history,
        'alert_rules': alert_rules,
        'suggestions': suggestions,
    }

    # Select renderer based on format
    if report_format == 'text':
        report = render_text(report_data)
        ext = '.txt'
    elif report_format == 'markdown':
        report = render_markdown(report_data)
        ext = '.md'
    else:
        report = render_html(report_data)
        ext = '.html'

    if not output_dir:
        output_dir = os.path.expanduser('~/Downloads')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f'kvstore_health_inspect_report_{instance_id}_{timestamp}{ext}'
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f'\nReport saved: {filepath}')

    # Build summary for batch overview
    res_data = report_data.get('resource_data', {}) or {}
    def _peak(key):
        d = res_data.get(key, {})
        if not d:
            return 0.0
        return float(d.get('peak', 0) or 0)
    danger_count = sum(1 for s in (suggestions or []) if (isinstance(s, tuple) and s[0] == 'danger') or (isinstance(s, dict) and s.get('level') == 'danger'))
    warn_count = sum(1 for s in (suggestions or []) if (isinstance(s, tuple) and s[0] == 'warn') or (isinstance(s, dict) and s.get('level') == 'warn'))
    spec_pair = format_instance_spec(instance_info) if instance_info else ('N/A', 'N/A')
    arch_pair = format_architecture(instance_info) if instance_info else ('N/A', 'N/A')
    summary = {
        'instance_id': instance_id,
        'instance_name': (instance_info or {}).get('InstanceName', '') if instance_info else '',
        'region': region,
        'engine_version': (engine_version or {}).get('engine_version', '') if engine_version else '',
        'minor_version': (engine_version or {}).get('minor_version', '') if engine_version else '',
        'spec_en': spec_pair[0] if isinstance(spec_pair, tuple) else spec_pair,
        'spec_zh': spec_pair[1] if isinstance(spec_pair, tuple) else spec_pair,
        'arch_en': arch_pair[0] if isinstance(arch_pair, tuple) else arch_pair,
        'arch_zh': arch_pair[1] if isinstance(arch_pair, tuple) else arch_pair,
        'status': (instance_info or {}).get('InstanceStatus', 'N/A') if instance_info else 'N/A',
        'peak_cpu': _peak('CpuUsage'),
        'peak_conn': _peak('ConnectionUsage'),
        'peak_mem': _peak('MemoryUsage'),
        'peak_in_bw': _peak('IntranetInRatio'),
        'peak_out_bw': _peak('IntranetOutRatio'),
        'danger_count': danger_count,
        'warn_count': warn_count,
        'slow_count': (slow_logs or {}).get('total_count', 0) if slow_logs else 0,
        'alert_count': len(alert_history or []),
        'big_keys': len((big_hot_keys or {}).get('big_keys', [])) + len((big_hot_keys or {}).get('large_keys', [])),
        'hot_keys': len((big_hot_keys or {}).get('hot_keys', [])),
        # Carry suggestion details (level, en_text, zh_text) so the batch overview
        # can show specific recommendations under the Risk Details panel.
        'suggestions': [
            {'level': s[0], 'en': s[1], 'zh': s[2]}
            for s in (suggestions or [])
            if isinstance(s, tuple) and len(s) >= 3 and s[0] in ('danger', 'warn')
        ],
    }
    return filepath, summary


def render_batch_overview(reports):
    """Render batch inspection overview index page (card layout, PolarDB style)."""

    def _html_escape(s):
        if not s:
            return ''
        # Filter out surrogate characters (U+D800-U+DFFF) which are invalid in UTF-8
        s = ''.join(ch for ch in str(s) if not (0xD800 <= ord(ch) <= 0xDFFF))
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def _health_level(s):
        if s.get('danger_count', 0) > 0:
            return 'danger'
        if s.get('warn_count', 0) > 0:
            return 'warn'
        return 'normal'

    def _level_color(level):
        return {'danger': '#e53935', 'warn': '#f9a825', 'normal': '#43a047'}[level]

    def _level_icon(level):
        return {'danger': '\U0001f534', 'warn': '\U0001f7e1', 'normal': '\U0001f7e2'}[level]

    def _metric_class(value, thresholds=(60, 80)):
        if value > thresholds[1]:
            return 'metric-danger'
        elif value > thresholds[0]:
            return 'metric-warn'
        return ''

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = len(reports)
    levels = [_health_level(r.get('summary') or {}) for r in reports]
    danger_count = levels.count('danger')
    warn_count = levels.count('warn')
    normal_count = levels.count('normal')

    cards_html = ''
    for idx, r in enumerate(reports, 1):
        s = r.get('summary') or {}
        level = levels[idx - 1]
        color = _level_color(level)
        icon = _level_icon(level)
        report_file = os.path.basename(r['report'])

        cpu_peak = s.get('peak_cpu', 0)
        mem_peak = s.get('peak_mem', 0)
        conn_peak = s.get('peak_conn', 0)
        in_bw_peak = s.get('peak_in_bw', 0)
        out_bw_peak = s.get('peak_out_bw', 0)

        cpu_cls = _metric_class(cpu_peak)
        mem_cls = _metric_class(mem_peak)
        conn_cls = _metric_class(conn_peak)
        bw_cls = _metric_class(max(in_bw_peak, out_bw_peak))

        spec_en = s.get('spec_en', '-') or '-'
        spec_zh = s.get('spec_zh', '-') or '-'
        arch_en = s.get('arch_en', '-') or '-'
        arch_zh = s.get('arch_zh', '-') or '-'

        inst_name = s.get('instance_name', '')
        name_html = f'<div class="card-desc">{_html_escape(inst_name)}</div>' if inst_name else ''

        # Suggestion badges
        d_count = s.get('danger_count', 0)
        w_count = s.get('warn_count', 0)
        sug_badge = ''
        if d_count:
            sug_badge += f'<span class="sug-badge sug-danger">{d_count} <span class="i18n-en">High Risk</span><span class="i18n-zh">\u9ad8\u98ce\u9669</span></span>'
        if w_count:
            sug_badge += f'<span class="sug-badge sug-warn">{w_count} <span class="i18n-en">Medium Risk</span><span class="i18n-zh">\u4e2d\u98ce\u9669</span></span>'

        cards_html += f'''
        <a class="card" data-level="{level}" href="{report_file}" style="border-top:4px solid {color};">
          <div class="card-header">
            <span class="card-icon">{icon}</span>
            <span class="card-id">{_html_escape(r["instance_id"])}</span>
          </div>
          {name_html}
          <div class="card-meta">{_html_escape(r["region"])} | <span class="i18n-en">{_html_escape(arch_en)}</span><span class="i18n-zh">{_html_escape(arch_zh)}</span></div>
          <div class="card-spec"><span class="i18n-en">{_html_escape(spec_en)}</span><span class="i18n-zh">{_html_escape(spec_zh)}</span></div>
          <div class="card-metrics"><div class="card-metrics-inner">
            <div class="metric-row"><span class="metric-label"><span class="i18n-en">CPU Usage</span><span class="i18n-zh">CPU \u4f7f\u7528\u7387</span></span><span class="metric-val {cpu_cls}">{cpu_peak:.1f}%</span></div>
            <div class="metric-row"><span class="metric-label"><span class="i18n-en">Memory Usage</span><span class="i18n-zh">\u5185\u5b58\u4f7f\u7528\u7387</span></span><span class="metric-val {mem_cls}">{mem_peak:.1f}%</span></div>
            <div class="metric-row"><span class="metric-label"><span class="i18n-en">Conn Usage</span><span class="i18n-zh">\u8fde\u63a5\u4f7f\u7528\u7387</span></span><span class="metric-val {conn_cls}">{conn_peak:.1f}%</span></div>
            <div class="metric-row"><span class="metric-label"><span class="i18n-en">Bandwidth</span><span class="i18n-zh">\u5e26\u5bbd\u4f7f\u7528\u7387</span></span><span class="metric-val {bw_cls}">{max(in_bw_peak, out_bw_peak):.1f}%</span></div>
          </div></div>
          <div class="card-footer">
            <span><span class="i18n-en">Slow Logs</span><span class="i18n-zh">\u6162\u65e5\u5fd7</span>: {s.get('slow_count', 0)}</span>
            <span><span class="i18n-en">Alerts</span><span class="i18n-zh">\u544a\u8b66</span>: {s.get('alert_count', 0)}</span>
            <span><span class="i18n-en">Big/Hot Keys</span><span class="i18n-zh">\u5927/\u70ed Key</span>: {s.get('big_keys', 0)}/{s.get('hot_keys', 0)}</span>
          </div>
          {f'<div class="card-sug">{sug_badge}</div>' if sug_badge else ''}
          <div class="card-link"><span class="i18n-en">View Details \u2192</span><span class="i18n-zh">\u67e5\u770b\u8be6\u60c5 \u2192</span></div>
        </a>'''

    # Build risk detail card
    risk_html = ''
    has_risk = False
    for idx, r in enumerate(reports, 1):
        s = r.get('summary') or {}
        d_count = s.get('danger_count', 0)
        w_count = s.get('warn_count', 0)
        if not d_count and not w_count:
            continue
        has_risk = True
        iid = r['instance_id']
        inst_name = s.get('instance_name', '')
        label = f'{iid}' + (f' ({inst_name})' if inst_name and inst_name != iid else '')
        report_file = os.path.basename(r['report'])
        risk_html += f'<div class="risk-instance"><div class="risk-instance-header"><a href="{report_file}">{_html_escape(label)}</a> <span class="risk-counts">'
        if d_count:
            risk_html += f'<span class="risk-count-danger">{d_count} <span class="i18n-en">high risk</span><span class="i18n-zh">高风险</span></span>'
        if w_count:
            risk_html += f'<span class="risk-count-warn">{w_count} <span class="i18n-en">medium risk</span><span class="i18n-zh">中风险</span></span>'
        risk_html += '</span></div>'
        sug_list = s.get('suggestions') or []
        danger_items = [x for x in sug_list if x.get('level') == 'danger']
        warn_items = [x for x in sug_list if x.get('level') == 'warn']
        if danger_items:
            risk_html += '<ul class="risk-list risk-list-danger">'
            for item in danger_items:
                risk_html += (
                    f'<li><span class="i18n-en">{_html_escape(item.get("en", ""))}</span>'
                    f'<span class="i18n-zh">{_html_escape(item.get("zh", ""))}</span></li>'
                )
            risk_html += '</ul>'
        if warn_items:
            risk_html += '<ul class="risk-list risk-list-warn">'
            for item in warn_items:
                risk_html += (
                    f'<li><span class="i18n-en">{_html_escape(item.get("en", ""))}</span>'
                    f'<span class="i18n-zh">{_html_escape(item.get("zh", ""))}</span></li>'
                )
            risk_html += '</ul>'
        risk_html += '</div>'

    risk_section = ''
    if has_risk:
        risk_section = f'''
<div class="risk-card">
  <h2 class="risk-title">\u26a0 <span class="i18n-en">Risk Details</span><span class="i18n-zh">\u98ce\u9669\u8be6\u60c5</span></h2>
  {risk_html}
</div>'''

    # Pre-compute filter buttons to avoid f-string with backslash issues
    danger_btn = f'<button class="filter-btn" data-filter="danger">\U0001f534 <span class="i18n-en">Critical {danger_count}</span><span class="i18n-zh">\u4e25\u91cd {danger_count}</span></button>' if danger_count else ''
    warn_btn = f'<button class="filter-btn" data-filter="warn">\U0001f7e1 <span class="i18n-en">Warning {warn_count}</span><span class="i18n-zh">\u8b66\u544a {warn_count}</span></button>' if warn_count else ''

    # Pre-compute JavaScript code to avoid quote conflicts in f-string
    js_code = '''
<script>
(function initLang() {
    var saved = localStorage.getItem('kvstore-inspection-lang') || 'en';
    document.documentElement.lang = saved;
    document.addEventListener('DOMContentLoaded', function() {
        var btn = document.querySelector('.lang-toggle');
        if (!btn) return;
        function paint() {
            var cur = document.documentElement.lang;
            btn.textContent = cur === 'en' ? '\u4e2d\u6587' : 'EN';
        }
        paint();
        btn.addEventListener('click', function() {
            var next = document.documentElement.lang === 'en' ? 'zh' : 'en';
            document.documentElement.lang = next;
            localStorage.setItem('kvstore-inspection-lang', next);
            paint();
        });
    });
})();
document.querySelectorAll('.filter-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    var filter = btn.getAttribute('data-filter');
    document.querySelectorAll('.card').forEach(function(card) {
      if (filter === 'all' || card.getAttribute('data-level') === filter) {
        card.classList.remove('hidden');
      } else {
        card.classList.add('hidden');
      }
    });
  });
});
</script>
'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Redis / Tair Batch Inspection Overview</title>
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
.grid {{ display:flex; flex-wrap:wrap; justify-content:center; gap:16px; }}
.card {{ width:280px; flex-shrink:0; }}
.card {{ display:block; background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.08); text-decoration:none; color:inherit; transition:transform 0.15s,box-shadow 0.15s,opacity 0.2s; }}
.card.hidden {{ display:none; }}
a.card:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.12); }}
.card-header {{ display:flex; align-items:center; gap:6px; margin-bottom:6px; }}
.card-icon {{ font-size:1.1rem; }}
.card-id {{ font-weight:600; font-size:0.95rem; font-family:monospace; }}
.card-desc {{ color:#666; font-size:0.8rem; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.card-meta {{ color:#888; font-size:0.8rem; margin-bottom:4px; }}
.card-spec {{ color:#999; font-size:0.75rem; margin-bottom:10px; font-family:monospace; }}
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
.risk-counts {{ font-weight:400; font-size:0.8rem; margin-left:8px; }}
.risk-count-danger {{ color:#c62828; background:#ffebee; padding:1px 8px; border-radius:10px; margin-right:6px; }}
.risk-count-warn {{ color:#e65100; background:#fff3e0; padding:1px 8px; border-radius:10px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <button class="lang-toggle" type="button">\u4e2d\u6587</button>
  <h1><span class="i18n-en">Redis / Tair Batch Inspection Overview</span><span class="i18n-zh">Redis / Tair 批量巡检概览</span></h1>
  <div class="time"><span class="i18n-en">Inspection Time</span><span class="i18n-zh">\u5de1\u68c0\u65f6\u95f4</span>: {now_str}</div>
</div>
<div class="filters">
  <button class="filter-btn active" data-filter="all"><span class="i18n-en">All {total}</span><span class="i18n-zh">\u5168\u90e8 {total}</span></button>
  {danger_btn}
  {warn_btn}
  <button class="filter-btn" data-filter="normal">\ud83d\udfe2 <span class="i18n-en">Normal {normal_count}</span><span class="i18n-zh">\u6b63\u5e38 {normal_count}</span></button>
</div>
{risk_section}
<div class="grid">
{cards_html}
</div>
</div>
{js_code}
</body>
</html>'''

    return html


def inspect_all_instances(region=None, output_dir=None, report_format='html'):
    """Inspect all Redis instances."""
    instances = discover_all_instances(region)
    if not instances:
        print('ERROR: No Redis instances found')
        return None

    if not output_dir:
        output_dir = os.path.expanduser('~/Downloads/kvstore_health_inspection')
    os.makedirs(output_dir, exist_ok=True)

    reports = []
    for inst in instances:
        iid = inst['instance_id']
        r = inst['region']
        try:
            result = inspect_single_instance(iid, r, output_dir, report_format)
            if result:
                if isinstance(result, tuple):
                    filepath, summary = result
                else:
                    filepath, summary = result, None
                reports.append({'instance_id': iid, 'region': r, 'report': filepath, 'summary': summary})
        except Exception as e:
            print(f'ERROR: Failed to inspect {iid}: {e}')

    if len(reports) >= 1 and report_format == 'html':
        index_path = os.path.join(output_dir, 'index.html')
        index_html = render_batch_overview(reports)
        # Filter out surrogate characters (U+D800-U+DFFF) which are invalid in UTF-8
        index_html = ''.join(ch for ch in index_html if not (0xD800 <= ord(ch) <= 0xDFFF))
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        print(f'\nIndex page: {index_path}')

    print(f'\nAll inspections complete. {len(reports)} reports generated.')
    return output_dir


def main():
    global _CLI_PROFILE, _INSPECT_DAYS, _INSPECT_ITEMS

    parser = argparse.ArgumentParser(
        description='Alibaba Cloud Redis (KVStore) Instance Health Inspection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 health-inspect.py r-bp1xxxxxxxxxxxx
  python3 health-inspect.py r-bp1xxx r-bp2yyy
  python3 health-inspect.py --all
  python3 health-inspect.py --all --region cn-hangzhou
  python3 health-inspect.py r-bp1xxx --days 3
  python3 health-inspect.py r-bp1xxx --item resource
  python3 health-inspect.py r-bp1xxx --item slowlog --item alert
  python3 health-inspect.py r-bp1xxx --format markdown
  python3 health-inspect.py r-bp1xxx -p myprofile -o ./report
''')
    parser.add_argument('instance_ids', nargs='*', metavar='INSTANCE_ID',
                        help='Redis instance ID(s) (r-xxx), omit with --all')
    parser.add_argument('--all', action='store_true',
                        help='Inspect all Redis instances in the account')
    parser.add_argument('--region', '-r',
                        help='Specify Region (auto-discovers if not specified)')
    parser.add_argument('--days', '-d', type=int, default=7,
                        help='Inspection time range in days (default: 7)')
    parser.add_argument('--item', action='append', choices=ALL_ITEMS,
                        help='Specify inspection items (can be used multiple times); '
                             'omit for full inspection. Options: resource, session, bigkey, slowlog, alert')
    parser.add_argument('--profile', '-p',
                        help='aliyun CLI profile name')
    parser.add_argument('--output', '-o',
                        help='Report output directory or file path')
    parser.add_argument('--format', '-f', choices=['html', 'markdown', 'text'],
                        default='html', help='Report format (default: html)')

    args = parser.parse_args()

    if not args.all and not args.instance_ids:
        parser.print_help()
        sys.exit(1)

    _CLI_PROFILE = args.profile
    _INSPECT_DAYS = args.days
    _INSPECT_ITEMS = set(args.item) if args.item else set(ALL_ITEMS)

    print('Redis (KVStore) Health Inspection')
    print(f'   Time Range: Last {_INSPECT_DAYS} days')
    print(f'   Format: {args.format}')
    if _INSPECT_ITEMS != set(ALL_ITEMS):
        print(f'   Items: {", ".join(sorted(_INSPECT_ITEMS))}')
    if _CLI_PROFILE:
        print(f'   Profile: {_CLI_PROFILE}')
    print('')

    ensure_cli_plugins()

    if args.all:
        inspect_all_instances(args.region, args.output, args.format)
    elif len(args.instance_ids) == 1:
        inspect_single_instance(args.instance_ids[0], args.region, args.output, args.format)
    else:
        output_dir = args.output or os.path.expanduser('~/Downloads/kvstore_health_inspection')
        os.makedirs(output_dir, exist_ok=True)
        reports = []
        for iid in args.instance_ids:
            try:
                result = inspect_single_instance(iid, args.region, output_dir, args.format)
                if result:
                    if isinstance(result, tuple):
                        filepath, summary = result
                    else:
                        filepath, summary = result, None
                    region = (summary or {}).get('region', args.region or '')
                    reports.append({'instance_id': iid, 'region': region, 'report': filepath, 'summary': summary})
            except Exception as e:
                print(f'ERROR: Failed to inspect {iid}: {e}')

        if len(reports) >= 1 and args.format == 'html':
            index_path = os.path.join(output_dir, 'index.html')
            index_html = render_batch_overview(reports)
            # Filter out surrogate characters (U+D800-U+DFFF) which are invalid in UTF-8
            index_html = ''.join(ch for ch in index_html if not (0xD800 <= ord(ch) <= 0xDFFF))
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_html)
            print(f'\nIndex page: {index_path}')

        print(f'\nAll inspections complete. {len(reports)} reports generated.')


if __name__ == '__main__':
    main()
