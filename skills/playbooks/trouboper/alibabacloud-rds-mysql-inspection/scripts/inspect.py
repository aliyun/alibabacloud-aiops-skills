#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alibaba Cloud RDS MySQL instance inspection script.

Supports single-instance / multi-instance / global batch inspection, with a
time range of 1-30 days (default 7 days). Calls the RDS / CMS / DAS APIs via
the aliyun CLI and emits per-instance HTML reports plus a summary HTML.

Usage:
    python3 inspect.py -i rm-bp1xxx
    python3 inspect.py -i rm-bp1xxx,rm-bp1yyy --days 14
    python3 inspect.py --all --output ./reports/
    python3 inspect.py --all --regions cn-hangzhou,cn-shanghai --days 30
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

_CLI_PROFILE = None
_CLI_TIMEOUT = 60


# ═══════════════════════════════════════════════════════════════════════════
# 1. CLI invocation wrapper
# ═══════════════════════════════════════════════════════════════════════════

def call_cli(_svc, _action, region=None, endpoint=None, timeout=None, **kwargs):
    """Invoke the aliyun CLI and return the parsed JSON dict or None.

    The positional arguments are intentionally prefixed with an underscore
    (`_svc` / `_action`) to avoid clashing with API parameter names (for
    example, CMS DescribeAlertLogList itself has a `--product` parameter).
    """
    cmd = ['aliyun', _svc, _action, '--user-agent', 'AlibabaCloud-Agent-Skills/alibabacloud-rds-mysql-inspection']
    if _CLI_PROFILE:
        cmd.extend(['--profile', _CLI_PROFILE])
    if region:
        cmd.extend(['--region', region])
    if endpoint:
        cmd.extend(['--endpoint', endpoint])
    for key, value in kwargs.items():
        if value is None:
            continue
        cmd.extend([f'--{key}', str(value)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout or _CLI_TIMEOUT)
        if result.returncode == 0:
            try:
                return json.loads(result.stdout) if result.stdout.strip() else {}
            except json.JSONDecodeError:
                return None
        else:
            stderr = (result.stderr or '').strip()
            if stderr and 'InvalidAction' not in stderr:
                err_msg = stderr.split('\n')[-1][:200]
                print(f'  [WARN] {_svc} {_action}: {err_msg}', file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f'  [WARN] {_svc} {_action} timed out ({timeout or _CLI_TIMEOUT}s)',
              file=sys.stderr)
    except Exception as e:
        print(f'  [ERROR] {_svc} {_action}: {e}', file=sys.stderr)
    return None


def parallel_map(fn, items, max_workers=3, desc=None):
    """Run fn(item) concurrently for each item, preserving input order in the results."""
    if not items:
        return []
    results = [None] * len(items)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fn, item): i for i, item in enumerate(items)}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = None
                print(f'  [ERROR] parallel task {i} failed: {e}', file=sys.stderr)
            done += 1
            if desc:
                print(f'  {desc}: {done}/{len(items)}', end='\r', flush=True)
        if desc:
            print(f'  {desc}: {done}/{len(items)} ✅')
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 2. Utility functions (some copied from PolarDB)
# ═══════════════════════════════════════════════════════════════════════════

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


def format_gb(gb_value):
    if gb_value is None:
        return 'N/A'
    try:
        gb_value = float(gb_value)
    except (ValueError, TypeError):
        return str(gb_value)
    if gb_value >= 1024:
        return f'{gb_value / 1024:.2f} TB'
    return f'{gb_value:.2f} GB'


def status_icon(value, metric_type='default'):
    """Return a status icon based on the value and metric type."""
    if value is None:
        return '⚪'
    thresholds = {
        'space': (70, 85),
        'memory': (60, 80),
        'iops': (60, 80),
        'cpu': (60, 80),
        'connection': (60, 80),
        'default': (60, 80),
    }
    low, high = thresholds.get(metric_type, thresholds['default'])
    if value > high:
        return '🔴'
    elif value > low:
        return '🟡'
    return '🟢'


def status_class(value, metric_type='default'):
    """Return a CSS class name used for coloring HTML cells."""
    if value is None:
        return 'na'
    thresholds = {
        'space': (70, 85), 'memory': (60, 80), 'iops': (60, 80),
        'cpu': (60, 80), 'connection': (60, 80), 'default': (60, 80),
    }
    low, high = thresholds.get(metric_type, thresholds['default'])
    if value > high:
        return 'danger'
    elif value > low:
        return 'warn'
    return 'ok'


def _html_escape(text):
    if text is None:
        return ''
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _i18n(en, zh):
    """Wrap a translatable label into bilingual spans for runtime EN/ZH toggle.

    The visible language is controlled by the `lang` attribute on the <html>
    element (toggled by the lang button + persisted in localStorage). CSS hides
    the non-active variant.
    """
    return f'<span class="i18n-en">{en}</span><span class="i18n-zh">{zh}</span>'


def _label_i18n(key, label_map=None):
    """Render a translatable METRIC_LABEL_MAP entry as bilingual spans."""
    m = (label_map or METRIC_LABEL_MAP).get(key, {})
    if isinstance(m, dict):
        return _i18n(m.get('en', key), m.get('zh', key))
    return _i18n(str(m), str(m))


def calc_avg_peak(values):
    if not values:
        return 0.0, 0.0
    return round(sum(values) / len(values), 2), round(max(values), 2)


def parse_timestamp(ts_str):
    """CMS returns timestamps as millisecond ints or ISO-format strings; normalize to ms."""
    if ts_str is None:
        return 0
    try:
        return int(ts_str)
    except (ValueError, TypeError):
        pass
    try:
        dt = datetime.strptime(str(ts_str)[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return 0


def to_iso_date(dt):
    """datetime → 'YYYY-MM-DD'"""
    return dt.strftime('%Y-%m-%d')


# ═══════════════════════════════════════════════════════════════════════════
# 3. RDS region & instance discovery
# ═══════════════════════════════════════════════════════════════════════════

# Fallback region list (used when DescribeRegions fails)
_FALLBACK_REGIONS = [
    'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen',
    'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
    'cn-hongkong', 'cn-wulanchabu', 'cn-heyuan', 'cn-guangzhou',
    'cn-nanjing', 'cn-fuzhou',
    'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-5',
    'ap-southeast-6', 'ap-southeast-7', 'ap-northeast-1', 'ap-northeast-2',
    'ap-south-1',
    'us-west-1', 'us-east-1', 'eu-west-1', 'eu-central-1', 'me-east-1',
]


_SPECIAL_REGION_PATTERNS = ('acdr', 'jva', '-ut-', 'finance', 'gov-', 'edu-')


def _is_standard_region(rid):
    """Filter out special-purpose regions like ACDR / JVA / industry cloud / POC (not for public sale or restricted access)."""
    if not rid:
        return False
    rl = rid.lower()
    return not any(p in rl for p in _SPECIAL_REGION_PATTERNS)


def list_active_regions(filter_regions=None):
    """Fetch all available RDS regions, filtering out special-purpose regions (ACDR / JVA / POC)."""
    print('Fetching region list...', end=' ', flush=True)
    data = call_cli('rds', 'describe-regions', region='cn-hangzhou')
    regions = []
    if data:
        items = data.get('Regions', {}).get('RDSRegion', [])
        seen = set()
        for it in items:
            rid = it.get('RegionId')
            if not rid or rid in seen:
                continue
            status = it.get('Status', '').lower()
            if status and 'closed' in status:
                continue
            if not _is_standard_region(rid):
                continue
            seen.add(rid)
            regions.append(rid)
    if not regions:
        regions = list(_FALLBACK_REGIONS)
        print(f'  using fallback ({len(regions)} regions)')
    else:
        print(f'  done ({len(regions)} regions)')
    if filter_regions:
        regions = [r for r in regions if r in filter_regions]
    return regions


def list_instances_in_region(region):
    """Paginate through and return all RDS MySQL instances in a region."""
    instances = []
    page = 1
    page_size = 100
    while True:
        data = call_cli('rds', 'describe-db-instances', region=region,
                        **{'engine': 'MySQL',
                           'biz-region-id': region,  # required by the RDS API
                           'page-size': page_size, 'page-number': page})
        if not data:
            break
        items = data.get('Items', {}).get('DBInstance', [])
        for it in items:
            iid = it.get('DBInstanceId')
            if iid:
                instances.append({
                    'instance_id': iid,
                    'region_id': it.get('RegionId') or region,
                    'engine_version': it.get('EngineVersion', ''),
                    'status': it.get('DBInstanceStatus', ''),
                    'instance_class': it.get('DBInstanceClass', ''),
                    'pay_type': it.get('PayType', ''),
                    'lock_mode': it.get('LockMode', ''),
                    'category': it.get('Category', ''),
                    'storage_type': it.get('DBInstanceStorageType', ''),
                    'expire_time': it.get('ExpireTime', ''),
                    'create_time': it.get('CreateTime', ''),
                })
        total = int(data.get('TotalRecordCount') or 0)
        if page * page_size >= total or not items:
            break
        page += 1
    return instances


def discover_all_instances(regions, region_concurrency=3):
    """Concurrently scan all regions and merge into a complete RDS MySQL instance list."""
    print(f'Scanning RDS MySQL instances across {len(regions)} regions (concurrency {region_concurrency})...')
    results = parallel_map(list_instances_in_region, regions,
                           max_workers=region_concurrency, desc='Scanning instances')
    all_instances = []
    region_count = {}
    for r, lst in zip(regions, results):
        if not lst:
            continue
        all_instances.extend(lst)
        region_count[r] = len(lst)
    print(f'   Total {len(all_instances)} instances across {len(region_count)} regions')
    return all_instances, region_count


def get_instance_attribute(instance_id, region):
    """Fetch detailed instance attributes via DescribeDBInstanceAttribute."""
    data = call_cli('rds', 'describe-db-instance-attribute', region=region,
                    **{'db-instance-id': instance_id})
    if not data:
        return None
    items = data.get('Items', {}).get('DBInstanceAttribute', [])
    if not items:
        return None
    return items[0]


def normalize_attribute(attr):
    """Extract the key fields from a DescribeDBInstanceAttribute response."""
    if not attr:
        return {}

    # Handle DBClusterNodes (cluster instances)
    raw_nodes = attr.get('DBClusterNodes', {})
    if isinstance(raw_nodes, dict):
        raw_nodes = raw_nodes.get('DBClusterNode', []) or raw_nodes.get('DBClusterNodeInfo', [])
    elif isinstance(raw_nodes, list):
        pass
    else:
        raw_nodes = []

    nodes = []
    for n in raw_nodes:
        nodes.append({
            'node_id': n.get('NodeId') or n.get('DBInstanceId') or '',
            'role': n.get('NodeRole') or n.get('Role', ''),
            'zone': n.get('NodeZoneId') or n.get('ZoneId', ''),
            'class': n.get('ClassCode') or n.get('NodeClass') or n.get('DBInstanceClass', ''),
            'status': n.get('Status') or n.get('NodeStatus', ''),
            'cpu': n.get('Cpu', ''),
            'memory': n.get('Memory', ''),
        })

    # SlaveZones (primary/standby instances)
    slave_zones_raw = attr.get('SlaveZones', {})
    if isinstance(slave_zones_raw, dict):
        slave_zones_raw = slave_zones_raw.get('SlaveZone', [])
    slave_zones = [z.get('ZoneId', '') for z in slave_zones_raw if isinstance(z, dict)]

    category = attr.get('Category', '')
    is_cluster = (category or '').lower() == 'cluster'

    return {
        'instance_id': attr.get('DBInstanceId', ''),
        'region_id': attr.get('RegionId', ''),
        'master_zone': attr.get('MasterZone') or attr.get('ZoneId', ''),
        'slave_zones': slave_zones,
        'engine': attr.get('Engine', 'MySQL'),
        'engine_version': attr.get('EngineVersion', ''),
        'category': category,
        'is_cluster': is_cluster,
        'instance_class': attr.get('DBInstanceClass', ''),
        'storage': attr.get('DBInstanceStorage', 0),
        'storage_type': attr.get('DBInstanceStorageType', ''),
        'max_iops': attr.get('MaxIOPS', 0),
        'max_iombps': attr.get('MaxIOMBPS', 0),
        'max_connections': attr.get('MaxConnections', 0),
        'status': attr.get('DBInstanceStatus', ''),
        'pay_type': attr.get('PayType', ''),
        'lock_mode': attr.get('LockMode', ''),
        'vpc_id': attr.get('VpcId', ''),
        'vswitch_id': attr.get('VSwitchId', ''),
        'maintain_time': attr.get('MaintainTime', ''),
        'expire_time': attr.get('ExpireTime', ''),
        'creation_time': attr.get('CreationTime', ''),
        'current_kernel': attr.get('CurrentKernelVersion', ''),
        'latest_kernel': attr.get('LatestKernelVersion', ''),
        'serverless_config': attr.get('ServerlessConfig', {}),
        'nodes': nodes,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. CMS monitoring data collection
# ═══════════════════════════════════════════════════════════════════════════

# 5 core metrics (user-confirmed), with separate metric names for cluster and non-cluster instances
METRICS_NON_CLUSTER = [
    ('CpuUsage', 'cpu', 'CPU usage', '%'),
    ('MemoryUsage', 'memory', 'Memory usage', '%'),
    ('DiskUsage', 'space', 'Disk usage', '%'),
    ('IOPSUsage', 'iops', 'IOPS usage', '%'),
    ('ConnectionUsage', 'connection', 'Connection usage', '%'),
]

METRICS_CLUSTER = [
    ('Cluster_CpuUsage', 'cpu', 'CPU usage', '%'),
    ('Cluster_MemoryUsage', 'memory', 'Memory usage', '%'),
    ('Cluster_DiskUsage', 'space', 'Disk usage', '%'),
    ('Cluster_IOPSUsage', 'iops', 'IOPS usage', '%'),
    ('Cluster_ConnectionUsage', 'connection', 'Connection usage', '%'),
]

METRIC_KEY_MAP = ['cpu', 'memory', 'space', 'iops', 'connection']
METRIC_LABEL_MAP = {
    'cpu': {'en': 'CPU', 'zh': 'CPU'},
    'memory': {'en': 'Memory', 'zh': '内存'},
    'space': {'en': 'Disk', 'zh': '磁盘'},
    'iops': {'en': 'IOPS', 'zh': 'IOPS'},
    'connection': {'en': 'Connections', 'zh': '连接'},
}


def call_cms_metric_paginated(metric_name, dimensions_dict, start_ms, end_ms, period=60):
    """Paginate CMS DescribeMetricList and return [(ts_ms, value), ...]"""
    points = []
    next_token = None
    page = 0
    dims_json = json.dumps([dimensions_dict], separators=(',', ':'))
    while page < 100:  # defensive upper bound
        kwargs = {
            'namespace': 'acs_rds_dashboard',
            'metric-name': metric_name,
            'period': str(period),
            'start-time': str(start_ms),
            'end-time': str(end_ms),
            'dimensions': dims_json,
            'length': '2000',
        }
        if next_token:
            kwargs['next-token'] = next_token
        data = call_cli('cms', 'describe-metric-list', region='cn-hangzhou',
                        timeout=30, **kwargs)
        if not data:
            break
        # CMS returns Datapoints as a JSON string
        dp_str = data.get('Datapoints', '') or '[]'
        try:
            dps = json.loads(dp_str) if isinstance(dp_str, str) else dp_str
        except (json.JSONDecodeError, TypeError):
            dps = []
        for dp in dps:
            try:
                ts = int(dp.get('timestamp', 0))
                # Prefer Average, then Value, then Maximum
                val = dp.get('Average')
                if val is None:
                    val = dp.get('Value')
                if val is None:
                    val = dp.get('Maximum', 0)
                points.append((ts, float(val)))
            except (ValueError, TypeError):
                continue
        next_token = data.get('NextToken')
        if not next_token:
            break
        page += 1
    points.sort(key=lambda x: x[0])
    return points


def collect_instance_metrics(instance_attr, start_ms, end_ms):
    """Collect all 5 metrics for an instance. Cluster instances get one time-series per node."""
    is_cluster = instance_attr.get('is_cluster', False)
    instance_id = instance_attr['instance_id']
    metric_set = METRICS_CLUSTER if is_cluster else METRICS_NON_CLUSTER

    result = {}
    for metric_name, key, label, unit in metric_set:
        result[key] = {
            'metric_name': metric_name,
            'label': label,
            'unit': unit,
            'cluster': None,  # overall (non-cluster results go here directly)
            'nodes': {},      # node-level data (cluster only)
        }
        if is_cluster:
            for node in instance_attr.get('nodes', []) or []:
                node_id = node.get('node_id')
                if not node_id:
                    continue
                pts = call_cms_metric_paginated(
                    metric_name,
                    {'instanceId': instance_id, 'nodeId': node_id},
                    start_ms, end_ms,
                )
                values = [v for _, v in pts]
                avg, peak = calc_avg_peak(values)
                result[key]['nodes'][node_id] = {
                    'avg': avg, 'peak': peak, 'timeseries': pts, 'role': node.get('role', ''),
                }
            # Cluster-level aggregation: take the max of node peaks; take the max of node averages
            all_avg = [n['avg'] for n in result[key]['nodes'].values() if n['avg']]
            all_peak = [n['peak'] for n in result[key]['nodes'].values() if n['peak']]
            result[key]['cluster'] = {
                'avg': round(max(all_avg), 2) if all_avg else 0.0,
                'peak': round(max(all_peak), 2) if all_peak else 0.0,
            }
        else:
            pts = call_cms_metric_paginated(
                metric_name, {'instanceId': instance_id}, start_ms, end_ms,
            )
            values = [v for _, v in pts]
            avg, peak = calc_avg_peak(values)
            result[key]['cluster'] = {
                'avg': avg, 'peak': peak, 'timeseries': pts,
            }

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 5. CMS alert history
# ═══════════════════════════════════════════════════════════════════════════

# Alert level sort weight (higher = more severe)
LEVEL_WEIGHT = {
    'CRITICAL': 100, 'P1': 100, 'P0': 110,
    'WARN': 70, 'WARNING': 70, 'P2': 70,
    'INFO': 30, 'P3': 30, 'P4': 10,
    'OK': 0,
    '': 0, None: 0,
}


def level_weight(level_str):
    if not level_str:
        return 0
    s = str(level_str).upper().strip()
    return LEVEL_WEIGHT.get(s, 50)


def _format_alert_time(ts):
    """Millisecond timestamp -> 'YYYY-MM-DD HH:MM:SS' string."""
    if not ts:
        return ''
    try:
        ms = int(ts)
        if ms > 1e12:  # ms
            dt = datetime.fromtimestamp(ms / 1000.0)
        else:  # already seconds
            dt = datetime.fromtimestamp(ms)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError):
        return str(ts)


def _extract_alert_metadata(message_str):
    """Alert Message is a JSON string; pull out RuleName / MetricName / Expression / etc."""
    if not message_str:
        return {}
    try:
        m = json.loads(message_str) if isinstance(message_str, str) else message_str
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(m, dict):
        return {}
    # Common paths: m.metricName / m.ruleName / m.alertState / m.curValue
    return {
        'rule_name': m.get('ruleName') or m.get('RuleName', ''),
        'metric_name': m.get('metricName') or m.get('MetricName', ''),
        'cur_value': m.get('curValue') or m.get('CurValue', ''),
        'expression': m.get('expression') or m.get('Expression', ''),
        'state': m.get('alertState') or m.get('AlertState', ''),
    }


def collect_instance_alerts(instance_id, start_ms, end_ms):
    """Fetch an instance's alert history and return it sorted by severity.
    Note: the CMS DescribeAlertLogList response has no Total field, so stop when items < page_size."""
    alerts = []
    page = 1
    page_size = 100
    while page <= 50:  # cap at 5000 entries
        data = call_cli('cms', 'describe-alert-log-list', region='cn-hangzhou',
                        timeout=30,
                        **{
                            'namespace': 'acs_rds_dashboard',
                            'product': 'rds',
                            'search-key': instance_id,
                            'start-time': str(start_ms),
                            'end-time': str(end_ms),
                            'page-size': str(page_size),
                            'page-number': str(page),
                        })
        if not data:
            break
        items = data.get('AlertLogList', []) or []
        if isinstance(items, dict):
            items = items.get('AlertLog', []) or []
        if not items:
            break
        for a in items:
            meta = _extract_alert_metadata(a.get('Message', ''))
            # Pull nodeId out of Dimensions (cluster instance node-level alerts carry it)
            node_id = ''
            for dim in a.get('Dimensions', []) or []:
                if isinstance(dim, dict) and dim.get('Key') == 'nodeId':
                    node_id = dim.get('Value', '')
                    break
            alerts.append({
                'time': _format_alert_time(a.get('AlertTime') or a.get('Time')),
                'level': a.get('LevelType') or a.get('Level', ''),
                'level_change': a.get('LevelChange', ''),
                'rule_name': meta.get('rule_name') or a.get('RuleName', ''),
                'metric_name': meta.get('metric_name') or a.get('MetricName', ''),
                'instance_name': a.get('InstanceName', ''),  # display name (not InstanceId)
                'node_id': node_id,
                'event_name': a.get('EventName', ''),
                'cur_value': meta.get('cur_value', ''),
                'expression': meta.get('expression', ''),
            })
        # No Total field, so terminate when items < page_size
        if len(items) < page_size:
            break
        page += 1

    # Sort by level descending
    alerts.sort(key=lambda x: -level_weight(x['level']))
    return alerts


# ═══════════════════════════════════════════════════════════════════════════
# 6. DAS slow log statistics
# ═══════════════════════════════════════════════════════════════════════════

# DAS DescribeSlowLogStatistic hard-caps a single request to a 7-day window
# (server returns State=FAIL with "time span exceeds the allowed limit"
# otherwise). Subtract a 1-minute safety margin from 7d.
_DAS_SLOW_LOG_MAX_WINDOW_MS = 7 * 86_400_000 - 60_000


def _das_fail_message(inner, instance_id, start_ms, end_ms, order_by):
    """If the DAS async response signals failure, log a warning and return True.
    DAS returns Code=200 but the inner payload carries State='FAIL' +
    ErrorCode + Message; callers must surface this rather than silently
    treating it as an empty result set."""
    if not isinstance(inner, dict):
        return False
    if inner.get('State') == 'FAIL' or (inner.get('ErrorCode', -1) not in (-1, 0, None)):
        msg = inner.get('Message') or '(no message)'
        err = inner.get('ErrorCode', '?')
        print(f'  [WARN] DAS slow-log query failed for {instance_id} '
              f'[{start_ms}~{end_ms}, order_by={order_by}, ErrorCode={err}]: {msg}',
              file=sys.stderr)
        return True
    return False


def _collect_slow_log_chunk(instance_id, start_ms, end_ms, node_id=None, order_by='Count',
                            max_poll_seconds=60):
    """DescribeSlowLogStatistic for a single chunk (must be <= 7 days).

    Asynchronous API: the first call kicks off the task and returns a ResultId;
    subsequent polls with the same ResultId return IsFinish=true when ready.
    DAS State=FAIL is surfaced as a stderr warning before returning [].
    Public callers should use `collect_slow_log_stats` instead, which chunks
    the window automatically and merges results.
    """
    kwargs = {
        'instance-id': instance_id,
        'start-time': str(start_ms),
        'end-time': str(end_ms),
        'order-by': order_by,
        'page-size': '50',
        'page-number': '1',
    }
    if node_id:
        kwargs['node-id'] = node_id

    # First call: trigger the async task
    data = call_cli('das', 'describe-slow-log-statistic',
                    endpoint='das.cn-shanghai.aliyuncs.com',
                    timeout=30, **kwargs)
    if not data:
        return []

    inner = data.get('Data', {}) or {}
    if isinstance(inner, str):
        try:
            inner = json.loads(inner)
        except (json.JSONDecodeError, TypeError):
            return []

    if _das_fail_message(inner, instance_id, start_ms, end_ms, order_by):
        return []

    result_id = inner.get('ResultId')
    is_finish = inner.get('IsFinish', False)

    # Poll
    deadline = time.time() + max_poll_seconds
    while not is_finish and result_id and time.time() < deadline:
        time.sleep(3)
        kwargs['result-id'] = result_id
        data = call_cli('das', 'describe-slow-log-statistic',
                        endpoint='das.cn-shanghai.aliyuncs.com',
                        timeout=30, **kwargs)
        if not data:
            break
        inner = data.get('Data', {}) or {}
        if isinstance(inner, str):
            try:
                inner = json.loads(inner)
            except (json.JSONDecodeError, TypeError):
                break
        if _das_fail_message(inner, instance_id, start_ms, end_ms, order_by):
            return []
        is_finish = inner.get('IsFinish', False)

    if not is_finish:
        return []

    # The actual result lives in Data.Data.Logs
    payload = inner.get('Data') or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return []
    items = payload.get('Logs') or payload.get('List') or payload.get('Items') or []
    if isinstance(items, dict):
        items = items.get('SlowLogStatistic') or items.get('Logs') or []

    def _seconds(it, name):
        """Prefer the *Seconds field (seconds); otherwise use the raw field (ms) / 1000."""
        sec_val = it.get(f'{name}Seconds')
        if sec_val is not None:
            try:
                return float(sec_val)
            except (TypeError, ValueError):
                pass
        ms_val = it.get(name)
        try:
            return float(ms_val or 0) / 1000.0
        except (TypeError, ValueError):
            return 0.0

    stats = []
    for it in items:
        stats.append({
            'sql_template': it.get('SQLText') or it.get('SqlTemplate') or it.get('SqlText', ''),
            'sql_id': it.get('SqlId', ''),
            'db_name': it.get('DBName') or it.get('DbName', ''),
            'table_name': it.get('TableName', ''),
            'sql_type': it.get('SqlType', ''),
            'count': int(it.get('Count') or it.get('SQLExecuteCount') or 0),
            'total_query_time': _seconds(it, 'QueryTime'),
            'max_query_time': _seconds(it, 'MaxQueryTime'),
            'avg_query_time': _seconds(it, 'AvgQueryTime'),
            'parsed_rows': int(it.get('RowsExamined') or it.get('ParseRowCounts') or 0),
            'returned_rows': int(it.get('RowsSent') or it.get('ReturnRowCounts') or 0),
            'rule_id': it.get('RuleId', ''),
        })
    return stats


def _merge_slow_logs(node_lists):
    """Merge slow logs from multiple nodes, grouped by SQL ID (or SQL template):
    count/parsed_rows/returned_rows are summed, max_query_time is the max, avg_query_time is recomputed.
    Used for cross-instance summary aggregation and SQL-dimension TOP ranking."""
    merged = {}
    for lst in node_lists:
        for s in lst or []:
            key = s.get('sql_id') or s.get('sql_template', '')[:200]
            if not key:
                continue
            if key not in merged:
                # Copy so we don't mutate the original data
                merged[key] = dict(s)
            else:
                m = merged[key]
                m['count'] += s.get('count', 0)
                m['total_query_time'] += s.get('total_query_time', 0)
                m['max_query_time'] = max(m['max_query_time'], s.get('max_query_time', 0))
                m['parsed_rows'] += s.get('parsed_rows', 0)
                m['returned_rows'] += s.get('returned_rows', 0)
                m['avg_query_time'] = (m['total_query_time'] / m['count']) if m['count'] else 0
    return sorted(merged.values(), key=lambda x: -x['count'])


def collect_slow_log_stats(instance_id, start_ms, end_ms, node_id=None, order_by='Count',
                           max_poll_seconds=60):
    """DescribeSlowLogStatistic with automatic chunking for windows > 7 days.

    DAS imposes a hard 7-day max window per request; for longer windows we
    split into <=7-day chunks, fetch them in parallel (up to 3 concurrent),
    then merge by SQL template and re-sort by the requested order_by.
    """
    window_ms = end_ms - start_ms
    if window_ms <= _DAS_SLOW_LOG_MAX_WINDOW_MS:
        return _collect_slow_log_chunk(instance_id, start_ms, end_ms, node_id,
                                       order_by, max_poll_seconds)

    chunks = []
    cur = start_ms
    while cur < end_ms:
        chunk_end = min(cur + _DAS_SLOW_LOG_MAX_WINDOW_MS, end_ms)
        chunks.append((cur, chunk_end))
        cur = chunk_end

    def _fetch_chunk(se):
        s, e = se
        return _collect_slow_log_chunk(instance_id, s, e, node_id, order_by,
                                       max_poll_seconds)

    chunk_results = parallel_map(_fetch_chunk, chunks,
                                 max_workers=min(len(chunks), 3))
    merged = _merge_slow_logs([r for r in chunk_results if r])
    if order_by == 'QueryTime':
        merged.sort(key=lambda x: -x.get('total_query_time', 0))
    else:
        merged.sort(key=lambda x: -x.get('count', 0))
    return merged


def collect_slow_logs_full(instance_attr, start_ms, end_ms):
    """Collect slow log statistics for an instance.
    - Non-cluster instance: call once directly; per_node uses an empty-string key.
    - Cluster instance: call once per node (DAS requires NodeId for clusters),
      then merge across nodes to surface the union of all SQL templates.
    """
    instance_id = instance_attr['instance_id']
    is_cluster = instance_attr.get('is_cluster', False)

    per_node = {}  # node_id (or '') -> {'role', 'top_count', 'top_query_time'}

    if is_cluster:
        nodes = instance_attr.get('nodes', []) or []
        for n in nodes:
            nid = n.get('node_id')
            if not nid:
                continue
            per_node[nid] = {
                'role': n.get('role', ''),
                'top_count': collect_slow_log_stats(instance_id, start_ms, end_ms, nid, 'Count'),
                'top_query_time': collect_slow_log_stats(instance_id, start_ms, end_ms, nid, 'QueryTime'),
            }
    else:
        per_node[''] = {
            'role': '',
            'top_count': collect_slow_log_stats(instance_id, start_ms, end_ms, None, 'Count'),
            'top_query_time': collect_slow_log_stats(instance_id, start_ms, end_ms, None, 'QueryTime'),
        }

    # Cross-node merge (used for summary reports + global SQL ranking)
    merged_count = _merge_slow_logs([d['top_count'] for d in per_node.values()])
    merged_qt = _merge_slow_logs([d['top_query_time'] for d in per_node.values()])
    # Re-sort top_query_time by total_query_time
    merged_qt.sort(key=lambda x: -x['total_query_time'])

    return {
        'top_count': merged_count,
        'top_query_time': merged_qt,
        'per_node': per_node,
        'is_cluster': is_cluster,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 7. DAS space analysis TOP 20
# ═══════════════════════════════════════════════════════════════════════════

def collect_space_top20(instance_id, node_id=None, max_wait_seconds=180):
    """Trigger and poll a DAS space-analysis task.

    For cluster instances, pass node_id to analyze a single node's space;
    pass None for non-cluster instances.
    """
    create_kwargs = {'instance-id': instance_id}
    if node_id:
        create_kwargs['node-id'] = node_id
    create_resp = call_cli('das', 'create-storage-analysis-task',
                           endpoint='das.cn-shanghai.aliyuncs.com',
                           timeout=20, **create_kwargs)
    if not create_resp:
        return None
    task_data = create_resp.get('Data', {}) or {}
    if isinstance(task_data, str):
        try:
            task_data = json.loads(task_data)
        except (json.JSONDecodeError, TypeError):
            task_data = {}
    if not task_data.get('CreateTaskSuccess'):
        err = task_data.get('ErrorCode', '?')
        msg = task_data.get('Message') or task_data.get('ErrorMessage') or '(no message)'
        print(f'  [WARN] DAS space-analysis CreateTask failed for {instance_id} '
              f'(node={node_id or "-"}, ErrorCode={err}): {msg}',
              file=sys.stderr)
        return None
    task_id = task_data.get('TaskId')
    if not task_id:
        return None

    get_kwargs = {'instance-id': instance_id, 'task-id': task_id}
    if node_id:
        get_kwargs['node-id'] = node_id

    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        time.sleep(5)
        result = call_cli('das', 'get-storage-analysis-result',
                          endpoint='das.cn-shanghai.aliyuncs.com',
                          timeout=20, **get_kwargs)
        if not result:
            continue
        if int(result.get('Code', 0)) != 200:
            continue
        data = result.get('Data', {}) or {}
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                continue
        state = (data.get('TaskState') or '').upper()
        # Detect terminal failure states so we exit early instead of polling
        # until max_wait_seconds and silently reporting "no data".
        if state in ('FAIL', 'FAILED', 'ERROR'):
            err = data.get('ErrorCode', '?')
            msg = data.get('Message') or data.get('ErrorMessage') or '(no message)'
            print(f'  [WARN] DAS space-analysis FAILED for {instance_id} '
                  f'(node={node_id or "-"}, task={task_id}, ErrorCode={err}): {msg}',
                  file=sys.stderr)
            return None
        if state in ('FINISH', 'SUCCESS', 'FINISHED') or data.get('TaskSuccess'):
            sar = data.get('StorageAnalysisResult', {}) or {}
            if isinstance(sar, str):
                try:
                    sar = json.loads(sar)
                except (json.JSONDecodeError, TypeError):
                    sar = {}
            tables_raw = sar.get('TableStats') or sar.get('Tables') or []
            tables = []
            for t in tables_raw:
                tables.append({
                    'db_name': (t.get('DbName') or t.get('SchemaName')
                                or t.get('DBName') or t.get('DatabaseName') or ''),
                    'table_name': t.get('TableName', ''),
                    'engine': t.get('Engine', ''),
                    'total_size': int(t.get('TotalSize') or t.get('TableSize') or 0),
                    'data_size': int(t.get('DataSize') or 0),
                    'index_size': int(t.get('IndexSize') or 0),
                    'frag_size': int(t.get('FragmentSize') or t.get('DataFree') or 0),
                    'phy_size': int(t.get('PhysicalFileSize') or t.get('PhyTotalSize') or 0),
                    'rows': int(t.get('TableRows') or t.get('Rows') or 0),
                })
            tables.sort(key=lambda x: -x['total_size'])

            # Instance-level storage stats (present even when TableStats is empty)
            total_used = int(sar.get('TotalUsedStorageSize') or 0)
            total_storage = int(sar.get('TotalStorageSize') or 0)
            total_free = int(sar.get('TotalFreeStorageSize') or 0)
            daily_increment = int(sar.get('DailyIncrement') or 0)
            estimate_days = sar.get('EstimateAvailableDays')

            # If the instance-level stats are missing, fall back to summing the tables
            if total_used == 0 and tables:
                total_used = sum(t['total_size'] for t in tables)

            return {
                'task_id': task_id,
                'tables_top20': tables[:20],
                'total_tables': len(tables),
                'total_used_bytes': total_used,
                'total_storage_bytes': total_storage,
                'total_free_bytes': total_free,
                'daily_increment_bytes': daily_increment,
                'estimate_available_days': estimate_days,
            }
    return None


def collect_space_full(instance_attr):
    """Collect space analysis for an instance.
    - Non-cluster instance: call DAS once.
    - Cluster instance: call DAS concurrently for each node (DAS takes 30-150s per node;
      concurrency cuts the runtime roughly in half).
    The return structure remains backward-compatible: top-level tables_top20 /
    total_used_bytes / etc. come from the master node, plus a new per_node field.
    """
    instance_id = instance_attr['instance_id']
    is_cluster = instance_attr.get('is_cluster', False)

    if not is_cluster:
        result = collect_space_top20(instance_id)
        if result:
            result['is_cluster'] = False
            result['per_node'] = {'': {**result, 'role': ''}}
        return result

    nodes = instance_attr.get('nodes', []) or []
    if not nodes:
        return None

    # Analyze each node concurrently (DAS tasks are independent and do not conflict)
    def _node_task(node):
        nid = node.get('node_id')
        if not nid:
            return None
        r = collect_space_top20(instance_id, node_id=nid)
        if r:
            r['node_id'] = nid
            r['role'] = node.get('role', '')
        return r

    node_results = parallel_map(_node_task, nodes,
                                max_workers=min(len(nodes), 3))

    per_node = {}
    for n, r in zip(nodes, node_results):
        nid = n.get('node_id')
        if not nid or not r:
            continue
        per_node[nid] = {**r, 'role': n.get('role', '')}

    if not per_node:
        return None

    # Top-level fields come from the master node (used for summary report aggregation)
    primary_data = None
    for nid, d in per_node.items():
        if 'primary' in (d.get('role') or '').lower() or 'master' in (d.get('role') or '').lower():
            primary_data = d
            break
    if primary_data is None:
        primary_data = next(iter(per_node.values()))

    return {
        'is_cluster': True,
        'per_node': per_node,
        'tables_top20': primary_data.get('tables_top20', []),
        'total_tables': primary_data.get('total_tables', 0),
        'total_used_bytes': primary_data.get('total_used_bytes', 0),
        'total_storage_bytes': primary_data.get('total_storage_bytes', 0),
        'total_free_bytes': primary_data.get('total_free_bytes', 0),
        'daily_increment_bytes': primary_data.get('daily_increment_bytes', 0),
        'estimate_available_days': primary_data.get('estimate_available_days'),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 8. Health scoring
# ═══════════════════════════════════════════════════════════════════════════

def calc_health_score(inst_data):
    """Compute a 0-100 health score from per-metric thresholds, slow logs,
    alerts, kernel version, expiration, and lock-mode. Deductions are returned
    as bilingual dicts so they can be rendered in either language.
    """
    score = 100
    deductions = []

    metrics = inst_data.get('metrics') or {}
    metric_thresholds = {
        'cpu': ('cpu', 'CPU', 'CPU'),
        'memory': ('memory', 'Memory', '内存'),
        'space': ('space', 'Disk', '磁盘'),
        'iops': ('iops', 'IOPS', 'IOPS'),
        'connection': ('connection', 'Connections', '连接'),
    }
    for key, (mtype, label_en, label_zh) in metric_thresholds.items():
        m = metrics.get(key, {}).get('cluster') or {}
        peak = m.get('peak', 0) or 0
        if mtype == 'space':
            if peak > 85:
                score -= 15
                deductions.append({'en': f'{label_en} usage > 85%', 'zh': f'{label_zh}使用率超 85%'})
            elif peak > 70:
                score -= 5
                deductions.append({'en': f'{label_en} usage > 70%', 'zh': f'{label_zh}使用率超 70%'})
        else:
            if peak > 80:
                score -= 10
                deductions.append({'en': f'{label_en} peak > 80%', 'zh': f'{label_zh}峰值超 80%'})
            elif peak > 60:
                score -= 5
                deductions.append({'en': f'{label_en} peak > 60%', 'zh': f'{label_zh}峰值超 60%'})

    # Slow logs
    slow = inst_data.get('slow_logs') or {}
    slow_count = sum(s.get('count', 0) for s in (slow.get('top_count') or []))
    if slow_count > 1000:
        score -= 8
        deductions.append({'en': 'Too many slow queries (>1000)', 'zh': '慢日志数量过多 (>1000 条)'})
    elif slow_count > 100:
        score -= 3
        deductions.append({'en': 'Many slow queries (>100)', 'zh': '慢日志数量较多 (>100 条)'})

    # Alerts (P1=critical weight=100, P2=warning weight=70)
    alerts = inst_data.get('alerts') or []
    critical_count = sum(1 for a in alerts if level_weight(a['level']) >= 100)
    high_count = sum(1 for a in alerts if level_weight(a['level']) >= 70)
    if critical_count > 0:
        score -= 10
        deductions.append({'en': 'Critical P1 alerts present', 'zh': '存在 P1 紧急告警'})
    elif high_count > 50:
        score -= 5
        deductions.append({'en': 'Many P2 high-severity alerts (>50)', 'zh': 'P2 高严重告警数量较多 (>50 条)'})
    elif len(alerts) > 100:
        score -= 3
        deductions.append({'en': 'High alert volume (>100)', 'zh': '告警总数较多 (>100 条)'})

    # Kernel version not latest
    attr = inst_data.get('attribute') or {}
    cur, latest = attr.get('current_kernel', ''), attr.get('latest_kernel', '')
    if cur and latest and cur != latest:
        score -= 3
        deductions.append({'en': 'Kernel version not latest', 'zh': '内核版本未更新到最新'})

    # Expiring within 30 days
    expire = attr.get('expire_time', '')
    if expire:
        try:
            et = datetime.strptime(expire[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            days_left = (et - datetime.now(timezone.utc)).days
            if 0 <= days_left <= 30:
                score -= 5
                deductions.append({
                    'en': f'Instance expires in {days_left} days',
                    'zh': f'实例 {days_left} 天后到期',
                })
        except (ValueError, TypeError):
            pass

    # LockMode abnormal
    lock = (attr.get('lock_mode') or '').lower()
    if lock and lock != 'unlock':
        score -= 8
        deductions.append({
            'en': f'Instance in {attr.get("lock_mode")} state',
            'zh': f'实例处于 {attr.get("lock_mode")} 状态',
        })

    return max(0, score), deductions


def score_status(score):
    """Health score -> color tier."""
    if score >= 80:
        return '🟢', 'ok'
    elif score >= 60:
        return '🟡', 'warn'
    else:
        return '🔴', 'danger'


# ═══════════════════════════════════════════════════════════════════════════
# 9. Instance inspection main flow (single instance)
# ═══════════════════════════════════════════════════════════════════════════

def inspect_one_instance(instance_meta, start_ms, end_ms, skip_space=False):
    """Fully inspect a single instance and return the instance_data dict."""
    instance_id = instance_meta['instance_id']
    region = instance_meta['region_id']

    inst_data = {
        'instance_id': instance_id,
        'region_id': region,
        'attribute': None,
        'metrics': {},
        'alerts': [],
        'slow_logs': {'top_count': [], 'top_query_time': [], 'node_id': None},
        'space': None,
        # space_status: one of 'ok' / 'skipped' / 'no_data' / 'exception'.
        # Distinguishes the three reasons `space` may be empty so render_*
        # can show a clear message instead of a generic "no data" line.
        'space_status': 'no_data',
        'health_score': 0,
        'health_deductions': [],
        'errors': [],
    }

    # Attributes
    try:
        attr_raw = get_instance_attribute(instance_id, region)
        attr = normalize_attribute(attr_raw)
        if not attr:
            inst_data['errors'].append('DescribeDBInstanceAttribute failed')
            return inst_data
        inst_data['attribute'] = attr
    except Exception as e:
        inst_data['errors'].append(f'Attribute query failed: {e}')
        return inst_data

    # Metrics
    try:
        inst_data['metrics'] = collect_instance_metrics(attr, start_ms, end_ms)
    except Exception as e:
        inst_data['errors'].append(f'CMS metric collection failed: {e}')

    # Alerts
    try:
        inst_data['alerts'] = collect_instance_alerts(instance_id, start_ms, end_ms)
    except Exception as e:
        inst_data['errors'].append(f'Alert collection failed: {e}')

    # Slow logs
    try:
        inst_data['slow_logs'] = collect_slow_logs_full(attr, start_ms, end_ms)
    except Exception as e:
        inst_data['errors'].append(f'Slow log collection failed: {e}')

    # Space (cluster instances analyzed concurrently per node).
    # space_status reflects WHY space may be missing: explicit skip, DAS
    # returned nothing within the polling deadline (or FAILed — warning
    # already printed by collect_space_top20), or a Python-level exception.
    if skip_space:
        inst_data['space_status'] = 'skipped'
    else:
        try:
            space_data = collect_space_full(attr)
            if space_data:
                inst_data['space'] = space_data
                inst_data['space_status'] = 'ok'
            else:
                inst_data['space_status'] = 'no_data'
        except Exception as e:
            inst_data['errors'].append(f'Space analysis failed: {e}')
            inst_data['space_status'] = 'exception'

    # Health score
    try:
        score, deductions = calc_health_score(inst_data)
        inst_data['health_score'] = score
        inst_data['health_deductions'] = deductions
    except Exception as e:
        inst_data['errors'].append(f'Health score calculation failed: {e}')

    return inst_data


# ═══════════════════════════════════════════════════════════════════════════
# 10. HTML rendering - shared CSS / JS templates
# ═══════════════════════════════════════════════════════════════════════════

_HTML_CSS = """
:root { --ok:#10b981; --warn:#f59e0b; --danger:#ef4444; --info:#3b82f6;
        --bg:#f8fafc; --card:#fff; --border:#e2e8f0; --text:#1e293b;
        --muted:#64748b; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
       background:var(--bg); color:var(--text); line-height:1.6; padding:1.5rem; }
.container { max-width:1280px; margin:0 auto; }
.header { background:linear-gradient(135deg,#1e40af,#3b82f6); color:#fff;
          padding:1.5rem 2rem; border-radius:12px; margin-bottom:1.5rem; }
.header h1 { font-size:1.4rem; margin-bottom:0.4rem; }
.header .meta { opacity:0.92; font-size:0.85rem; }
.header .meta span { margin-right:1.2rem; }
.toc { background:var(--card); border:1px solid var(--border); border-radius:8px;
       padding:0.7rem 1.2rem; margin-bottom:1.5rem; font-size:0.85rem; }
.toc a { color:#1e40af; margin-right:1rem; text-decoration:none; }
.toc a:hover { text-decoration:underline; }
.section { background:var(--card); border:1px solid var(--border); border-radius:8px;
           padding:1.4rem 1.5rem; margin-bottom:1.5rem; }
.section h2 { font-size:1.15rem; color:#1e40af; margin-bottom:0.9rem;
              padding-bottom:0.5rem; border-bottom:2px solid #e2e8f0; }
.section h3 { font-size:1rem; color:#334155; margin:1rem 0 0.5rem 0; }
table { width:100%; border-collapse:collapse; font-size:0.85rem; }
th, td { padding:0.45rem 0.7rem; text-align:left; border-bottom:1px solid var(--border); }
th { background:#f1f5f9; font-weight:600; color:#334155; }
tr:hover { background:#f8fafc; }
.ok { color:var(--ok); } .warn { color:var(--warn); } .danger { color:var(--danger); }
.na { color:var(--muted); }
td.ok, td.warn, td.danger { font-weight:600; }
.badge { display:inline-block; padding:1px 7px; border-radius:4px; font-size:0.72rem;
         font-weight:500; margin-right:4px; }
.badge-master { background:#fef3c7; color:#92400e; }
.badge-slave { background:#dbeafe; color:#1e40af; }
.badge-ok { background:#d1fae5; color:#065f46; }
.badge-warn { background:#fef3c7; color:#92400e; }
.badge-danger { background:#fee2e2; color:#991b1b; }
.suggestion { padding:0.4rem 0; }
.suggestion.danger { color:var(--danger); }
.suggestion.warn { color:var(--warn); }
.suggestion.info { color:var(--info); }
.ok-msg { color:var(--ok); font-weight:500; padding:0.5rem 0; }
.sql-cell { font-family:monospace; font-size:0.78rem; max-width:600px;
            white-space:pre-wrap; word-break:break-word; line-height:1.4; }
.sql-cell-short { font-family:monospace; font-size:0.78rem; max-width:420px;
                  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer; }
.info-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:0; }
.info-item { padding:0.4rem 0.7rem; border-bottom:1px solid var(--border); display:flex; }
.info-item .label { color:var(--muted); min-width:96px; padding-right:10px; font-size:0.82rem; flex-shrink:0; }
.info-item .value { font-weight:500; font-size:0.82rem; word-break:break-all; }
.table-scroll { overflow-x:auto; }
.chart-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:0.8rem; }
.chart-card { background:#f8fafc; border:1px solid var(--border); border-radius:6px;
              padding:10px 12px; }
.chart-card h4 { margin:0 0 4px 0; font-size:0.88rem; color:#334155; }
.echart { width:100%; height:280px; }
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
            gap:0.8rem; margin:0.5rem 0 1rem 0; }
.kpi-card { background:#f8fafc; border:1px solid var(--border); border-radius:6px;
            padding:0.7rem 0.9rem; }
.kpi-card .label { font-size:0.78rem; color:var(--muted); }
.kpi-card .value { font-size:1.4rem; font-weight:600; color:#1e40af; }
.kpi-card .sub { font-size:0.72rem; color:var(--muted); margin-top:0.1rem; }
.footer { text-align:center; color:var(--muted); font-size:0.8rem; margin:1.5rem 0 0 0; }
.error-banner { background:#fef2f2; border:1px solid #fecaca; color:#991b1b;
                padding:0.6rem 1rem; border-radius:6px; margin-bottom:1rem; font-size:0.85rem; }
@media (max-width:768px) { body { padding:1rem; } .info-grid,.chart-grid { grid-template-columns:1fr; } }

/* ── i18n: bilingual spans + language toggle button ── */
html[lang="en"] .i18n-zh { display: none; }
html[lang="zh"] .i18n-en { display: none; }
.header { position: relative; }
.lang-toggle {
  position: absolute; top: 1rem; right: 1.5rem;
  background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.35);
  border-radius: 999px; padding: 4px 14px; cursor: pointer;
  color: #fff; font-size: 0.78rem; font-weight: 500;
  user-select: none; letter-spacing: 0.5px;
}
.lang-toggle:hover { background: rgba(255,255,255,0.28); }
"""

_LANG_TOGGLE_JS = """
(function initLang() {
    var saved = localStorage.getItem('rds-inspection-lang') || 'en';
    document.documentElement.lang = saved;
    document.addEventListener('DOMContentLoaded', function() {
        var btn = document.querySelector('.lang-toggle');
        if (!btn) return;
        function paint() {
            var cur = document.documentElement.lang;
            btn.textContent = cur === 'en' ? '中文' : 'EN';
        }
        paint();
        btn.addEventListener('click', function() {
            var next = document.documentElement.lang === 'en' ? 'zh' : 'en';
            document.documentElement.lang = next;
            localStorage.setItem('rds-inspection-lang', next);
            paint();
        });
    });
})();
"""

_CHART_OPTS_FN = """
function _chartOpts(tooltip, legend, series, yMax) {
    return {
        tooltip: tooltip,
        legend: legend,
        grid: { left:48, right:18, top:30, bottom:55 },
        xAxis: { type:'time', axisLabel:{fontSize:10, formatter:'{MM}-{dd} {HH}:{mm}'} },
        yAxis: { type:'value', min:0, max:yMax, axisLabel:{fontSize:10} },
        dataZoom: [
            {type:'inside'},
            {type:'slider', height:20, bottom:5, borderColor:'#ddd',
             fillerColor:'rgba(84,112,198,0.15)', handleStyle:{color:'#5470c6'},
             textStyle:{fontSize:10},
             labelFormatter:function(v){ var d=new Date(v); return (d.getMonth()+1).toString().padStart(2,'0')+'-'+d.getDate().toString().padStart(2,'0')+' '+d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0'); }}
        ],
        series: series
    };
}
function _tipFmt(unit) {
    return function(params) {
        if(!params.length) return '';
        var t=new Date(params[0].value[0]);
        var s=t.getFullYear()+'-'+(t.getMonth()+1).toString().padStart(2,'0')+'-'+t.getDate().toString().padStart(2,'0')+' '+t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
        var r='<b>'+s+'</b><br/>';
        params.forEach(function(p){ r+=p.marker+p.seriesName+': '+(p.value[1]==null?'-':p.value[1].toFixed(2))+unit+'<br/>'; });
        return r;
    };
}
"""

_DATAZOOM_LINK_JS = """
var _zoomLock = false;
function linkCharts(charts) {
    charts.forEach(function(c, ci) {
        c.on('dataZoom', function() {
            if (_zoomLock) return;
            _zoomLock = true;
            var opt = c.getOption();
            var dz = opt.dataZoom[0];
            charts.forEach(function(other, oi) {
                if (oi !== ci) other.dispatchAction({ type:'dataZoom', start:dz.start, end:dz.end });
            });
            _zoomLock = false;
        });
    });
}
"""


# ═══════════════════════════════════════════════════════════════════════════
# 11. Single-instance HTML rendering (5 sections)
# ═══════════════════════════════════════════════════════════════════════════

def render_instance_html(inst_data, time_range, slow_log_days):
    """Generate the HTML inspection report for a single instance (5 sections)."""
    instance_id = inst_data['instance_id']
    region = inst_data['region_id']
    attr = inst_data.get('attribute') or {}
    metrics = inst_data.get('metrics') or {}
    is_cluster = attr.get('is_cluster', False)
    nodes = attr.get('nodes', []) or []
    score = inst_data.get('health_score', 0)
    score_emoji, score_cls = score_status(score)

    start_dt, end_dt, days = time_range
    inspect_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    range_str = _i18n(
        f'{to_iso_date(start_dt)} ~ {to_iso_date(end_dt)} (past {days} days)',
        f'{to_iso_date(start_dt)} ~ {to_iso_date(end_dt)} (近 {days} 天)',
    )

    errors_banner = ''
    if inst_data.get('errors'):
        err_str = '; '.join(inst_data['errors'])
        errors_banner = (
            f'<div class="error-banner">⚠️ '
            f'{_i18n("Some data collection failed: ", "部分数据采集失败: ")}'
            f'{_html_escape(err_str)}</div>'
        )

    # ── Section 1: Instance basic info ──
    storage_str = format_gb(attr.get('storage', 0))
    expire_str = (attr.get('expire_time') or '')[:10] or 'N/A'
    create_str = (attr.get('creation_time') or '')[:10] or 'N/A'
    cur_kernel = attr.get('current_kernel') or 'N/A'
    latest_kernel = attr.get('latest_kernel') or 'N/A'
    if cur_kernel == 'N/A' or latest_kernel == 'N/A':
        kernel_status = 'N/A'
    elif cur_kernel == latest_kernel:
        kernel_status = _i18n('✅ Up to date', '✅ 已是最新')
    else:
        kernel_status = _i18n('⬆️ Upgradable', '⬆️ 可升级')

    nodes_html = ''
    if nodes:
        rows = []
        for n in nodes:
            role_badge = f'<span class="badge badge-master">{_html_escape(n.get("role","?"))}</span>' \
                if 'master' in (n.get('role','').lower()) \
                else f'<span class="badge badge-slave">{_html_escape(n.get("role","?"))}</span>'
            rows.append(
                f'<tr><td>{_html_escape(n.get("node_id",""))}</td>'
                f'<td>{role_badge}</td>'
                f'<td>{_html_escape(n.get("zone",""))}</td>'
                f'<td>{_html_escape(n.get("class",""))}</td>'
                f'<td>{_html_escape(n.get("status",""))}</td></tr>'
            )
        nodes_html = (
            f'<h3>{_i18n("Node List", "节点列表")}</h3>'
            f'<table><tr><th>{_i18n("Node ID", "节点 ID")}</th>'
            f'<th>{_i18n("Role", "角色")}</th>'
            f'<th>{_i18n("Zone", "可用区")}</th>'
            f'<th>{_i18n("Class", "规格")}</th>'
            f'<th>{_i18n("Status", "状态")}</th></tr>'
            + ''.join(rows) + '</table>'
        )

    category_text = _html_escape(attr.get('category', '')) or 'N/A'
    if is_cluster:
        category_text += ' ' + _i18n('(cluster)', '(集群)')

    basic_info_html = f"""
    <div class="info-grid">
        <div class="info-item"><span class="label">{_i18n("Instance ID", "实例 ID")}</span><span class="value">{_html_escape(attr.get('instance_id',''))}</span></div>
        <div class="info-item"><span class="label">Region</span><span class="value">{_html_escape(attr.get('region_id',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Engine", "引擎")}</span><span class="value">{_html_escape(attr.get('engine','MySQL'))} {_html_escape(attr.get('engine_version',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Category", "类别")}</span><span class="value">{category_text}</span></div>
        <div class="info-item"><span class="label">{_i18n("Class", "规格")}</span><span class="value">{_html_escape(attr.get('instance_class',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Storage Type", "存储类型")}</span><span class="value">{_html_escape(attr.get('storage_type',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Storage Size", "存储容量")}</span><span class="value">{storage_str}</span></div>
        <div class="info-item"><span class="label">{_i18n("Max Connections", "最大连接")}</span><span class="value">{attr.get('max_connections',0)}</span></div>
        <div class="info-item"><span class="label">{_i18n("Max IOPS", "最大 IOPS")}</span><span class="value">{attr.get('max_iops',0)}</span></div>
        <div class="info-item"><span class="label">{_i18n("Max IO Bandwidth", "最大 IO 带宽")}</span><span class="value">{attr.get('max_iombps',0)} MB/s</span></div>
        <div class="info-item"><span class="label">{_i18n("Master Zone", "主可用区")}</span><span class="value">{_html_escape(attr.get('master_zone',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Slave Zones", "备可用区")}</span><span class="value">{_html_escape(','.join(attr.get('slave_zones',[]))) or 'N/A'}</span></div>
        <div class="info-item"><span class="label">VPC ID</span><span class="value">{_html_escape(attr.get('vpc_id',''))}</span></div>
        <div class="info-item"><span class="label">VSwitch</span><span class="value">{_html_escape(attr.get('vswitch_id',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Status", "实例状态")}</span><span class="value">{_html_escape(attr.get('status',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Pay Type", "付费方式")}</span><span class="value">{_html_escape(attr.get('pay_type',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Lock Mode", "锁定状态")}</span><span class="value">{_html_escape(attr.get('lock_mode','')) or 'Unlock'}</span></div>
        <div class="info-item"><span class="label">{_i18n("Maintain Window", "维护时间")}</span><span class="value">{_html_escape(attr.get('maintain_time',''))}</span></div>
        <div class="info-item"><span class="label">{_i18n("Created", "创建时间")}</span><span class="value">{create_str}</span></div>
        <div class="info-item"><span class="label">{_i18n("Expires", "到期时间")}</span><span class="value">{expire_str}</span></div>
        <div class="info-item"><span class="label">{_i18n("Current Kernel", "当前内核")}</span><span class="value">{_html_escape(cur_kernel)}</span></div>
        <div class="info-item"><span class="label">{_i18n("Latest Kernel", "最新内核")}</span><span class="value">{_html_escape(latest_kernel)}</span></div>
        <div class="info-item"><span class="label">{_i18n("Version Status", "版本状态")}</span><span class="value">{kernel_status}</span></div>
    </div>
    {nodes_html}
    """

    # ─── Section 2: Resource utilization ───
    res_table_rows = []
    chart_payloads = {}  # metric_key -> list of (label, [(ts, val), ...])

    for mkey in METRIC_KEY_MAP:
        m = metrics.get(mkey, {}) or {}
        label_html = _label_i18n(mkey)
        cluster_overall = _i18n('Cluster overall', '集群整体')
        instance_overall = _i18n('Instance overall', '实例整体')

        if is_cluster and m.get('nodes'):
            # Cluster: one row per node
            chart_payloads[mkey] = []
            for nid, nd in m['nodes'].items():
                avg = nd.get('avg', 0) or 0
                peak = nd.get('peak', 0) or 0
                role = nd.get('role') or ''
                cls = status_class(peak, mkey)
                icon = status_icon(peak, mkey)
                res_table_rows.append(
                    f'<tr><td>{label_html}</td><td>{_html_escape(nid)} ({_html_escape(role)})</td>'
                    f'<td>{avg:.2f}%</td><td class="{cls}">{peak:.2f}%</td>'
                    f'<td>{icon}</td></tr>'
                )
                chart_payloads[mkey].append((f'{nid}({role})', nd.get('timeseries') or []))
            # Cluster-level aggregate row
            cluster_m = m.get('cluster') or {}
            cls = status_class(cluster_m.get('peak'), mkey)
            icon = status_icon(cluster_m.get('peak'), mkey)
            res_table_rows.append(
                f'<tr style="background:#f1f5f9;font-weight:600"><td>{label_html}</td><td>{cluster_overall}</td>'
                f'<td>{cluster_m.get("avg",0):.2f}%</td><td class="{cls}">{cluster_m.get("peak",0):.2f}%</td>'
                f'<td>{icon}</td></tr>'
            )
        else:
            cluster_m = m.get('cluster') or {}
            avg = cluster_m.get('avg', 0) or 0
            peak = cluster_m.get('peak', 0) or 0
            cls = status_class(peak, mkey)
            icon = status_icon(peak, mkey)
            res_table_rows.append(
                f'<tr><td>{label_html}</td><td>{instance_overall}</td>'
                f'<td>{avg:.2f}%</td><td class="{cls}">{peak:.2f}%</td>'
                f'<td>{icon}</td></tr>'
            )
            # Chart series names stay English-only (data-side labels are language-agnostic)
            chart_payloads[mkey] = [('Instance', cluster_m.get('timeseries') or [])]

    res_table_html = (
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Metric", "指标")}</th><th>{_i18n("Target", "对象")}</th>'
        f'<th>{_i18n("Average", "平均值")}</th><th>{_i18n("Peak", "峰值")}</th>'
        f'<th>{_i18n("Status", "状态")}</th></tr>'
        + ''.join(res_table_rows) + '</table></div>'
    )

    # 5 charts
    chart_html_blocks = []
    chart_data_js = []
    for i, mkey in enumerate(METRIC_KEY_MAP):
        label_html = _label_i18n(mkey)
        chart_id = f'chart-{mkey}'
        chart_html_blocks.append(
            f'<div class="chart-card"><h4>{label_html} {_i18n("Usage (%)", "使用率（%）")}</h4>'
            f'<div id="{chart_id}" class="echart"></div></div>'
        )
        series_data = chart_payloads.get(mkey, [])
        js_var = f'cdata_{mkey}'
        # Serialize the time-series data
        series_js = json.dumps([
            {'name': lbl, 'data': [[ts, round(v, 2)] for ts, v in tsdata]}
            for lbl, tsdata in series_data
        ])
        chart_data_js.append(f'var {js_var} = {series_js};')

    chart_grid_html = '<div class="chart-grid">' + ''.join(chart_html_blocks) + '</div>'

    # JS that renders the charts
    chart_init_js = '\n'.join(chart_data_js) + '\n'
    chart_init_js += "var resCharts = [];\n"
    chart_init_js += "var colors = ['#5470c6','#91cc75','#ee6666','#fac858','#73c0de','#3ba272','#fc8452','#9a60b4'];\n"
    for mkey in METRIC_KEY_MAP:
        chart_init_js += f"""
(function() {{
    var data = cdata_{mkey};
    if (!data.length) return;
    var chart = echarts.init(document.getElementById('chart-{mkey}'));
    var series = data.map(function(d, i) {{
        return {{name:d.name, type:'line', symbol:'none', smooth:true,
                 lineStyle:{{width:1.5}}, itemStyle:{{color:colors[i%colors.length]}},
                 areaStyle:{{opacity:0.05}}, data:d.data}};
    }});
    var legendData = data.map(function(d){{return d.name;}});
    chart.setOption(_chartOpts(
        {{trigger:'axis', formatter:_tipFmt('%')}},
        {{data:legendData, top:0, type:'scroll', textStyle:{{fontSize:10}}}},
        series, 100
    ));
    resCharts.push(chart);
    window.addEventListener('resize', function(){{ chart.resize(); }});
}})();
"""

    # ── Section 3: Space usage TOP 20 ──
    space = inst_data.get('space')

    def _render_table_top20(tables_top20, total_tables):
        if not tables_top20:
            return f'<p class="ok-msg">{_i18n("ℹ️ TableStats is empty (instance may have only system tables / no user-table data)", "ℹ️ TableStats 为空（实例可能只有系统表 / 无用户表数据）")}</p>'
        rows = []
        for i, t in enumerate(tables_top20, 1):
            db = _html_escape(t['db_name']) or '<span class="na">-</span>'
            idx_size = format_bytes(t['index_size']) if t['index_size'] else '<span class="na">0 B</span>'
            rows_str = f'{t["rows"]:,}' if t['rows'] else '<span class="na">0</span>'
            rows.append(
                f'<tr><td>{i}</td><td>{db}</td>'
                f'<td>{_html_escape(t["table_name"])}</td>'
                f'<td>{_html_escape(t["engine"])}</td>'
                f'<td>{format_bytes(t["total_size"])}</td>'
                f'<td>{format_bytes(t["data_size"])}</td>'
                f'<td>{idx_size}</td>'
                f'<td>{format_bytes(t["frag_size"])}</td>'
                f'<td>{rows_str}</td></tr>'
            )
        title_html = _i18n(
            f'Top 20 tables by size ({total_tables} tables total)',
            f'表空间 TOP 20（共 {total_tables} 张表）',
        )
        return (
            f'<h4 style="margin:0.5rem 0;color:#475569;font-size:0.92rem">{title_html}</h4>'
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Database", "数据库")}</th>'
            f'<th>{_i18n("Table", "表名")}</th>'
            f'<th>{_i18n("Engine", "引擎")}</th>'
            f'<th>{_i18n("Total Size", "总空间")}</th>'
            f'<th>{_i18n("Data", "数据")}</th>'
            f'<th>{_i18n("Index", "索引")}</th>'
            f'<th>{_i18n("Fragmented", "碎片")}</th>'
            f'<th>{_i18n("Rows", "行数")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    def _render_space_kpi(d):
        return f"""
        <div class="kpi-grid">
            <div class="kpi-card"><div class="label">{_i18n("Used Space", "已用空间")}</div>
                <div class="value">{format_bytes(d.get('total_used_bytes', 0))}</div></div>
            <div class="kpi-card"><div class="label">{_i18n("Allocated", "已分配空间")}</div>
                <div class="value">{format_bytes(d.get('total_storage_bytes', 0))}</div></div>
            <div class="kpi-card"><div class="label">{_i18n("Free Space", "剩余空间")}</div>
                <div class="value">{format_bytes(d.get('total_free_bytes', 0))}</div></div>
            <div class="kpi-card"><div class="label">{_i18n("Daily Growth", "日均增长")}</div>
                <div class="value">{format_bytes(d.get('daily_increment_bytes', 0))}</div></div>
            <div class="kpi-card"><div class="label">{_i18n("Days Until Full", "预计可用天数")}</div>
                <div class="value">{d.get('estimate_available_days', '-') or '-'}</div></div>
            <div class="kpi-card"><div class="label">{_i18n("Scanned Tables", "扫描表数")}</div>
                <div class="value">{d.get('total_tables', 0)}</div></div>
        </div>
        """

    if not space:
        # Pick a specific empty-state message based on space_status so the
        # report distinguishes "skipped" from "DAS failed" from "exception"
        # instead of lumping them under a single ambiguous line.
        status = inst_data.get('space_status', 'no_data')
        _space_msgs = {
            'skipped': (
                'ℹ️ Space analysis was skipped (--skip-space). Re-run without that flag to populate this section.',
                'ℹ️ 已跳过空间分析（--skip-space），去掉该参数重跑可填充本节',
            ),
            'no_data': (
                '⚠️ DAS space analysis did not complete in time or returned no data (check stderr [WARN] for FAIL details).',
                '⚠️ DAS 空间分析在轮询窗口内未完成或无数据（如 DAS 报错请看 stderr 的 [WARN]）',
            ),
            'exception': (
                '⚠️ DAS space analysis raised an exception — see the error banner above.',
                '⚠️ DAS 空间分析抛出异常，详见页面顶部的错误条',
            ),
        }
        msg_en, msg_zh = _space_msgs.get(status, _space_msgs['no_data'])
        space_html = f'<p class="ok-msg">{_i18n(msg_en, msg_zh)}</p>'
    elif space.get('is_cluster') and space.get('per_node'):
        per_node_space = space['per_node']
        # Per-node space overview table (side-by-side KPI per node)
        node_rows = []
        for nid, nd in per_node_space.items():
            used = nd.get('total_used_bytes', 0)
            storage = nd.get('total_storage_bytes', 0)
            pct = (used / storage * 100) if storage else 0
            cls = status_class(pct, 'space')
            # NB: do not rebind `days` here — the outer scope's `days` (time
            # window in days) is still consumed by sections 2 and 5 below.
            est_days = nd.get('estimate_available_days')
            days_str = _i18n(f'{est_days} days', f'{est_days} 天') if est_days not in (None, '', '-') else '-'
            node_rows.append(
                f'<tr><td>{_html_escape(nid)}</td>'
                f'<td>{_html_escape(nd.get("role",""))}</td>'
                f'<td>{format_bytes(used)}</td>'
                f'<td>{format_bytes(storage)}</td>'
                f'<td class="{cls}">{pct:.1f}%</td>'
                f'<td>{format_bytes(nd.get("daily_increment_bytes", 0))}</td>'
                f'<td>{days_str}</td>'
                f'<td>{nd.get("total_tables", 0)}</td></tr>'
            )
        node_overview = (
            f'<h3>{_i18n("Per-Node Space Overview", "各节点空间概览")}</h3>'
            '<div class="table-scroll"><table>'
            f'<tr><th>{_i18n("Node ID", "节点 ID")}</th>'
            f'<th>{_i18n("Role", "角色")}</th>'
            f'<th>{_i18n("Used", "已用")}</th>'
            f'<th>{_i18n("Allocated", "已分配")}</th>'
            f'<th>{_i18n("Usage", "使用率")}</th>'
            f'<th>{_i18n("Daily Growth", "日均增长")}</th>'
            f'<th>{_i18n("Days Left", "预计可用")}</th>'
            f'<th>{_i18n("Tables", "表数")}</th></tr>'
            + ''.join(node_rows) + '</table></div>'
        )
        # Per-node Top 20 blocks
        per_node_blocks = []
        for nid, nd in per_node_space.items():
            per_node_blocks.append(f"""
            <h3>📍 {_i18n("Node", "节点")} {_html_escape(nid)} ({_html_escape(nd.get('role',''))})</h3>
            {_render_table_top20(nd.get('tables_top20', []), nd.get('total_tables', 0))}
            """)
        space_html = node_overview + ''.join(per_node_blocks)
    else:
        # Non-cluster instance
        space_html = (
            _render_space_kpi(space)
            + _render_table_top20(space.get('tables_top20', []), space.get('total_tables', 0))
        )

    # ── Section 4: Slow log statistics ──
    slow = inst_data.get('slow_logs') or {}
    slow_count_top = slow.get('top_count') or []
    slow_qt_top = slow.get('top_query_time') or []

    def _slow_table(items, kind):
        if not items:
            return f'<p class="ok-msg">{_i18n("✅ No slow queries found", "✅ 未发现慢日志")}</p>'
        rows = []
        for i, s in enumerate(items[:20], 1):
            # SQL displayed in full with line-wrapping (not truncated)
            sql_full = _html_escape(s['sql_template'])
            rows.append(
                f'<tr><td>{i}</td><td>{_html_escape(s["db_name"])}</td>'
                f'<td>{s["count"]:,}</td>'
                f'<td>{s["total_query_time"]:.2f}</td>'
                f'<td>{s["max_query_time"]:.2f}</td>'
                f'<td>{s["avg_query_time"]:.2f}</td>'
                f'<td>{s["parsed_rows"]:,}</td>'
                f'<td>{s["returned_rows"]:,}</td>'
                f'<td class="sql-cell">{sql_full}</td></tr>'
            )
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Database", "数据库")}</th>'
            f'<th>{_i18n("Count", "次数")}</th>'
            f'<th>{_i18n("Total Time (s)", "总耗时(s)")}</th>'
            f'<th>{_i18n("Max (s)", "最大(s)")}</th>'
            f'<th>{_i18n("Avg (s)", "平均(s)")}</th>'
            f'<th>{_i18n("Scanned Rows", "扫描行")}</th>'
            f'<th>{_i18n("Returned Rows", "返回行")}</th>'
            '<th>SQL</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    per_node = slow.get('per_node') or {}
    is_cluster_slow = slow.get('is_cluster', False)

    if is_cluster_slow and per_node:
        # Cluster instance: show cross-node merged view first, then per-node detail
        node_summary_rows = []
        for nid, nd in per_node.items():
            total_count = sum(s.get('count', 0) for s in nd.get('top_count') or [])
            total_time = sum(s.get('total_query_time', 0) for s in nd.get('top_query_time') or [])
            unique_sqls = len(nd.get('top_count') or [])
            node_summary_rows.append(
                f'<tr><td>{_html_escape(nid)}</td>'
                f'<td>{_html_escape(nd.get("role",""))}</td>'
                f'<td>{total_count:,}</td>'
                f'<td>{total_time:.2f}</td>'
                f'<td>{unique_sqls}</td></tr>'
            )
        node_summary = (
            f'<h3>{_i18n("Per-Node Slow Log Overview", "各节点慢日志概览")}</h3>'
            '<div class="table-scroll"><table>'
            f'<tr><th>{_i18n("Node ID", "节点 ID")}</th>'
            f'<th>{_i18n("Role", "角色")}</th>'
            f'<th>{_i18n("Slow Log Count", "慢日志条数")}</th>'
            f'<th>{_i18n("Total Time (s)", "总耗时(s)")}</th>'
            f'<th>{_i18n("Unique SQL Templates", "独立 SQL 模板数")}</th></tr>'
            + ''.join(node_summary_rows) + '</table></div>'
        )

        merged_block = f"""
        <h3>{_i18n("Cross-Node Merged - TOP 20 by Execution Count", "跨节点合并 - 按执行次数 TOP 20")}</h3>
        {_slow_table(slow_count_top[:20], 'count')}
        <h3>{_i18n("Cross-Node Merged - TOP 20 by Total Time", "跨节点合并 - 按总耗时 TOP 20")}</h3>
        {_slow_table(slow_qt_top[:20], 'query_time')}
        """

        per_node_blocks = []
        for nid, nd in per_node.items():
            per_node_blocks.append(f"""
            <h3>📍 {_i18n("Node", "节点")} {_html_escape(nid)} ({_html_escape(nd.get('role',''))})</h3>
            <h4 style="margin:0.5rem 0;color:#475569;font-size:0.92rem">{_i18n("TOP 20 by Execution Count", "按执行次数 TOP 20")}</h4>
            {_slow_table(nd.get('top_count', [])[:20], 'count')}
            <h4 style="margin:0.5rem 0;color:#475569;font-size:0.92rem">{_i18n("TOP 20 by Total Time", "按总耗时 TOP 20")}</h4>
            {_slow_table(nd.get('top_query_time', [])[:20], 'query_time')}
            """)

        slow_html = node_summary + merged_block + ''.join(per_node_blocks)
    else:
        # Non-cluster instance
        slow_html = f"""
        <h3>{_i18n("TOP 20 by Execution Count", "按执行次数 TOP 20")}</h3>
        {_slow_table(slow_count_top[:20], 'count')}
        <h3>{_i18n("TOP 20 by Total Time", "按总耗时 TOP 20")}</h3>
        {_slow_table(slow_qt_top[:20], 'query_time')}
        """

    # ── Section 5: Alert history ──
    alerts = inst_data.get('alerts') or []
    is_cluster_alert = attr.get('is_cluster', False)

    def _render_alert_table(items, show_node=False, limit=200):
        if not items:
            return ''
        rows = []
        for i, a in enumerate(items[:limit], 1):
            lvl = a.get('level', '') or ''
            lvl_cls = ('badge-danger' if level_weight(lvl) >= 100
                       else 'badge-warn' if level_weight(lvl) >= 70
                       else 'badge-ok' if lvl.upper() == 'OK'
                       else 'badge-warn')
            level_change = a.get('level_change', '')
            level_display = level_change or lvl
            node_cell = ''
            if show_node:
                nid = a.get('node_id', '')
                node_display = _html_escape(nid) if nid else f'<span class="na">{_i18n("Cluster-level", "集群级")}</span>'
                node_cell = f'<td>{node_display}</td>'
            rows.append(
                f'<tr><td>{i}</td><td>{_html_escape(a.get("time",""))}</td>'
                + node_cell
                + f'<td><span class="badge {lvl_cls}">{_html_escape(level_display)}</span></td>'
                f'<td>{_html_escape(a.get("rule_name",""))}</td>'
                f'<td>{_html_escape(a.get("metric_name",""))}</td>'
                f'<td>{_html_escape(a.get("cur_value",""))}</td>'
                f'<td>{_html_escape(a.get("expression",""))[:80]}</td>'
                f'<td>{_html_escape(a.get("event_name",""))}</td></tr>'
            )
        header_node = f'<th>{_i18n("Node", "节点")}</th>' if show_node else ''
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Time", "时间")}</th>{header_node}'
            f'<th>{_i18n("Level", "级别")}</th>'
            f'<th>{_i18n("Rule", "规则")}</th>'
            f'<th>{_i18n("Metric", "指标")}</th>'
            f'<th>{_i18n("Current Value", "当前值")}</th>'
            f'<th>{_i18n("Expression", "表达式")}</th>'
            f'<th>{_i18n("Event", "事件")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    def _more_note(n):
        if n > 200:
            txt = _i18n(f'{n} total, showing first 200', f'共 {n} 条，仅展示前 200 条')
        else:
            txt = _i18n(f'{n} total', f'共 {n} 条')
        return f'<p style="color:var(--muted);font-size:0.8rem">{txt}</p>'

    if not alerts:
        alerts_html = f'<p class="ok-msg">{_i18n(f"✅ No alerts in the past {days} days", f"✅ 近 {days} 天无告警记录")}</p>'
    elif is_cluster_alert:
        # Cluster instance: group by node first, then show per-node detail
        by_node = {}
        for a in alerts:
            nid = a.get('node_id', '') or '__cluster__'
            by_node.setdefault(nid, []).append(a)
        # Per-node alert overview
        node_summary_rows = []
        # Make sure every actual node shows up (even with 0 alerts)
        for n in nodes:
            nid = n.get('node_id', '')
            n_alerts = by_node.get(nid, [])
            max_lvl = max((a.get('level', '') for a in n_alerts), key=level_weight, default='-')
            high_severity = sum(1 for a in n_alerts if level_weight(a.get('level', '')) >= 70)
            node_summary_rows.append(
                f'<tr><td>{_html_escape(nid)}</td>'
                f'<td>{_html_escape(n.get("role",""))}</td>'
                f'<td>{len(n_alerts)}</td>'
                f'<td>{_html_escape(max_lvl)}</td>'
                f'<td>{high_severity}</td></tr>'
            )
        # Cluster-level alerts (those without a nodeId)
        cluster_alerts = by_node.get('__cluster__', [])
        if cluster_alerts:
            max_lvl = max((a.get('level', '') for a in cluster_alerts), key=level_weight, default='-')
            high_severity = sum(1 for a in cluster_alerts if level_weight(a.get('level', '')) >= 70)
            node_summary_rows.append(
                f'<tr style="background:#f1f5f9;font-weight:600">'
                f'<td>({_i18n("Cluster-level", "集群级")})</td><td>-</td>'
                f'<td>{len(cluster_alerts)}</td>'
                f'<td>{_html_escape(max_lvl)}</td>'
                f'<td>{high_severity}</td></tr>'
            )
        node_overview = (
            f'<h3>{_i18n("Per-Node Alert Overview", "各节点告警概览")}</h3>'
            '<div class="table-scroll"><table>'
            f'<tr><th>{_i18n("Node ID", "节点 ID")}</th>'
            f'<th>{_i18n("Role", "角色")}</th>'
            f'<th>{_i18n("Alert Count", "告警条数")}</th>'
            f'<th>{_i18n("Max Level", "最高级别")}</th>'
            f'<th>{_i18n("P1/P2 High Severity", "P1/P2 高严重")}</th></tr>'
            + ''.join(node_summary_rows) + '</table></div>'
        )
        alerts_html = (
            node_overview
            + f'<h3>{_i18n("Alert Detail", "告警明细")}</h3>'
            + _more_note(len(alerts))
            + _render_alert_table(alerts, show_node=True)
        )
    else:
        # Non-cluster instance
        alerts_html = _more_note(len(alerts)) + _render_alert_table(alerts, show_node=False)

    # Final assembly. The <html> `lang` attribute is set by the toggle JS from
    # localStorage at load time (defaults to "en"); CSS hides the inactive language.
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RDS MySQL Inspection - {_html_escape(instance_id)}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>{_HTML_CSS}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <button class="lang-toggle" type="button">中文</button>
        <h1>{score_emoji} {_i18n("RDS MySQL Instance Inspection Report", "RDS MySQL 实例巡检报告")}</h1>
        <div class="meta">
            <span>{_i18n("Instance", "实例")}: <b>{_html_escape(instance_id)}</b></span>
            <span>Region: {_html_escape(region)}</span>
            <span>{_i18n("Generated", "巡检时间")}: {inspect_time}</span>
            <span>{_i18n("Time Range", "时间范围")}: {range_str}</span>
            <span>{_i18n("Health Score", "健康分")}: <b>{score}/100</b></span>
        </div>
    </div>
    {errors_banner}
    <div class="toc">
        <a href="#sec-1">{_i18n("1. Basic Info", "一、基础信息")}</a>
        <a href="#sec-2">{_i18n("2. Resource Utilization", "二、资源使用率")}</a>
        <a href="#sec-3">{_i18n("3. Space TOP 20", "三、空间 TOP 20")}</a>
        <a href="#sec-4">{_i18n("4. Slow Log Statistics", "四、慢日志统计")}</a>
        <a href="#sec-5">{_i18n("5. Alert History", "五、告警历史")}</a>
    </div>

    <div class="section" id="sec-1">
        <h2>{_i18n("1. Instance Basic Info", "一、实例基础信息")}</h2>
        {basic_info_html}
    </div>

    <div class="section" id="sec-2">
        <h2>{_i18n(f"2. Resource Utilization (past {days} days)", f"二、资源使用率（近 {days} 天）")}</h2>
        {res_table_html}
        <h3>{_i18n("Monitoring Trends", "监控趋势图")}</h3>
        {chart_grid_html}
    </div>

    <div class="section" id="sec-3">
        <h2>{_i18n("3. Top 20 Space Usage", "三、空间使用详情 TOP 20")}</h2>
        {space_html}
    </div>

    <div class="section" id="sec-4">
        <h2>{_i18n(f"4. Slow Log Statistics (past {slow_log_days} days)", f"四、慢日志统计（近 {slow_log_days} 天）")}</h2>
        {slow_html}
    </div>

    <div class="section" id="sec-5">
        <h2>{_i18n(f"5. Alert History (past {days} days)", f"五、告警历史（近 {days} 天）")}</h2>
        {alerts_html}
    </div>

    <div class="footer">RDS MySQL Inspection · {inspect_time}</div>
</div>
<script>
{_LANG_TOGGLE_JS}
{_CHART_OPTS_FN}
{chart_init_js}
{_DATAZOOM_LINK_JS}
linkCharts(resCharts);
</script>
</body>
</html>
"""
    return html


# ═══════════════════════════════════════════════════════════════════════════
# 12. Summary report - cross-instance aggregation
# ═══════════════════════════════════════════════════════════════════════════

def aggregate_summary(instances_data, time_range, region_count, scanned_count):
    """Aggregate across instances and produce the summary dict."""
    total = len(instances_data)
    cluster_count = sum(1 for d in instances_data if (d.get('attribute') or {}).get('is_cluster'))
    non_cluster_count = total - cluster_count

    status_dist = {}
    for d in instances_data:
        s = (d.get('attribute') or {}).get('status') or 'Unknown'
        status_dist[s] = status_dist.get(s, 0) + 1

    health_dist = {'ok': 0, 'warn': 0, 'danger': 0}
    for d in instances_data:
        _, c = score_status(d.get('health_score', 0))
        health_dist[c] = health_dist.get(c, 0) + 1

    # Health score ranking (lowest TOP 20)
    health_ranking = sorted(instances_data, key=lambda d: d.get('health_score', 100))[:20]

    # Alert TOP 20
    instances_with_alerts = [d for d in instances_data if d.get('alerts')]
    alerts_ranking = sorted(instances_data, key=lambda d: -len(d.get('alerts', [])))[:20]
    alerts_ranking = [d for d in alerts_ranking if d.get('alerts')]
    total_alerts = sum(len(d.get('alerts', [])) for d in instances_data)
    alert_level_dist = {}
    for d in instances_data:
        for a in d.get('alerts', []):
            lvl = (a.get('level') or 'Unknown').upper()
            alert_level_dist[lvl] = alert_level_dist.get(lvl, 0) + 1

    # Resource TOP boards (5 of them)
    def metric_top(key, n=20):
        ranked = []
        for d in instances_data:
            m = (d.get('metrics') or {}).get(key, {})
            cluster_m = m.get('cluster') or {}
            peak = cluster_m.get('peak', 0) or 0
            avg = cluster_m.get('avg', 0) or 0
            ranked.append({
                'instance_id': d['instance_id'],
                'region_id': d['region_id'],
                'avg': avg, 'peak': peak,
            })
        ranked.sort(key=lambda x: -x['peak'])
        return ranked[:n]

    resource_tops = {k: metric_top(k) for k in METRIC_KEY_MAP}

    # Slow log TOP boards
    slow_count_ranking = []
    slow_time_ranking = []
    all_sql_max_time = []  # cross-instance aggregation of individual slow SQL
    for d in instances_data:
        slow = d.get('slow_logs') or {}
        top_c = slow.get('top_count') or []
        top_q = slow.get('top_query_time') or []
        total_count = sum(s.get('count', 0) for s in top_c)
        total_time = sum(s.get('total_query_time', 0) for s in top_q)
        slow_count_ranking.append({
            'instance_id': d['instance_id'], 'region_id': d['region_id'],
            'total_count': total_count, 'unique_sqls': len(top_c),
        })
        slow_time_ranking.append({
            'instance_id': d['instance_id'], 'region_id': d['region_id'],
            'total_time': total_time, 'unique_sqls': len(top_q),
        })
        for s in top_q:
            all_sql_max_time.append({
                'instance_id': d['instance_id'],
                'db_name': s.get('db_name', ''),
                'sql': s.get('sql_template', '')[:300],
                'max_time': s.get('max_query_time', 0),
            })
    slow_count_ranking.sort(key=lambda x: -x['total_count'])
    slow_time_ranking.sort(key=lambda x: -x['total_time'])
    all_sql_max_time.sort(key=lambda x: -x['max_time'])

    # Space TOP boards
    instance_space_ranking = []
    all_tables = []  # single-table TOP 20 (cross-instance)
    fragmentation_ranking = []
    for d in instances_data:
        space = d.get('space')
        if not space:
            continue
        used = space.get('total_used_bytes', 0)
        instance_space_ranking.append({
            'instance_id': d['instance_id'], 'region_id': d['region_id'],
            'total_used': used,
            'total_storage': space.get('total_storage_bytes', 0),
            'daily_increment': space.get('daily_increment_bytes', 0),
            'estimate_days': space.get('estimate_available_days'),
            'tables_count': space.get('total_tables', 0),
        })
        for t in space.get('tables_top20') or []:
            all_tables.append({
                'instance_id': d['instance_id'],
                'region_id': d['region_id'],
                **t,
            })
            if t['total_size'] > 0 and t.get('frag_size', 0) > 0:
                frag_pct = t['frag_size'] / t['total_size'] * 100
                if frag_pct >= 5:
                    fragmentation_ranking.append({
                        'instance_id': d['instance_id'],
                        'db_name': t['db_name'],
                        'table_name': t['table_name'],
                        'total_size': t['total_size'],
                        'frag_size': t['frag_size'],
                        'frag_pct': frag_pct,
                    })
    instance_space_ranking.sort(key=lambda x: -x['total_used'])
    all_tables.sort(key=lambda x: -x['total_size'])
    fragmentation_ranking.sort(key=lambda x: -x['frag_pct'])

    # Version & expiration
    upgradable = []
    expiring_30d = []
    expiring_90d = []
    for d in instances_data:
        attr = d.get('attribute') or {}
        cur, latest = attr.get('current_kernel', ''), attr.get('latest_kernel', '')
        if cur and latest and cur != latest:
            upgradable.append({
                'instance_id': d['instance_id'], 'region_id': d['region_id'],
                'current': cur, 'latest': latest,
            })
        expire = attr.get('expire_time', '')
        if expire:
            try:
                et = datetime.strptime(expire[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                days_left = (et - datetime.now(timezone.utc)).days
                rec = {
                    'instance_id': d['instance_id'], 'region_id': d['region_id'],
                    'expire_date': expire[:10], 'days_left': days_left,
                }
                if 0 <= days_left <= 30:
                    expiring_30d.append(rec)
                elif 30 < days_left <= 90:
                    expiring_90d.append(rec)
            except (ValueError, TypeError):
                pass
    expiring_30d.sort(key=lambda x: x['days_left'])
    expiring_90d.sort(key=lambda x: x['days_left'])

    # Optimization-suggestion aggregation.
    # Each deduction is now a bilingual dict {'en': ..., 'zh': ...}, so we
    # bucket by the stable English string and keep the bilingual label alongside.
    suggestions = {}
    for d in instances_data:
        for ded in d.get('health_deductions', []):
            key = ded.get('en') if isinstance(ded, dict) else str(ded)
            if key not in suggestions:
                suggestions[key] = {
                    'label': ded if isinstance(ded, dict) else {'en': str(ded), 'zh': str(ded)},
                    'instance_ids': [],
                }
            suggestions[key]['instance_ids'].append(d['instance_id'])

    # Global health score
    if instances_data:
        global_score = round(sum(d.get('health_score', 0) for d in instances_data) / len(instances_data), 1)
    else:
        global_score = 0

    return {
        'total_instances': total,
        'scanned_total': scanned_count,
        'cluster_count': cluster_count,
        'non_cluster_count': non_cluster_count,
        'region_count': region_count,
        'status_dist': status_dist,
        'health_dist': health_dist,
        'health_ranking': health_ranking,
        'global_score': global_score,
        'total_alerts': total_alerts,
        'instances_with_alerts': len(instances_with_alerts),
        'alert_level_dist': alert_level_dist,
        'alerts_ranking': alerts_ranking,
        'resource_tops': resource_tops,
        'slow_count_ranking': slow_count_ranking[:20],
        'slow_time_ranking': slow_time_ranking[:20],
        'sql_max_time_top20': all_sql_max_time[:20],
        'instance_space_ranking': instance_space_ranking[:20],
        'tables_top20': all_tables[:20],
        'fragmentation_ranking': fragmentation_ranking[:20],
        'upgradable': upgradable,
        'expiring_30d': expiring_30d,
        'expiring_90d': expiring_90d,
        'suggestions': suggestions,
        'time_range': time_range,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 13. Summary HTML rendering (8 sections)
# ═══════════════════════════════════════════════════════════════════════════

def render_summary_html(summary):
    inspect_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    start_dt, end_dt, days = summary['time_range']
    range_str = _i18n(
        f'{to_iso_date(start_dt)} ~ {to_iso_date(end_dt)} (past {days} days)',
        f'{to_iso_date(start_dt)} ~ {to_iso_date(end_dt)} (近 {days} 天)',
    )

    total = summary['total_instances']
    cluster_count = summary['cluster_count']
    non_cluster_count = summary['non_cluster_count']
    region_count = summary['region_count']
    health_dist = summary['health_dist']
    global_score = summary['global_score']

    def link(iid):
        return f'<a href="instances/{_html_escape(iid)}.html" target="_blank">{_html_escape(iid)}</a>'

    # ── Section 1: Inspection overview ──
    region_rows = ''.join(
        f'<tr><td>{_html_escape(r)}</td><td>{c}</td></tr>'
        for r, c in sorted(region_count.items(), key=lambda x: -x[1])
    )

    overview_kpis = f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">{_i18n("Instances Inspected", "巡检实例总数")}</div>
            <div class="value">{total}</div>
            <div class="sub">{_i18n(f"Scanned {summary['scanned_total']}", f"扫描发现 {summary['scanned_total']} 个")}</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Regions Covered", "覆盖 Region")}</div>
            <div class="value">{len(region_count)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Cluster Instances", "集群实例")}</div>
            <div class="value">{cluster_count}</div>
            <div class="sub">{_i18n(f"Non-cluster {non_cluster_count}", f"非集群 {non_cluster_count} 个")}</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Global Health", "全局健康度")}</div>
            <div class="value">{global_score}</div>
            <div class="sub">/100</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Health Distribution", "健康分布")}</div>
            <div class="value">🟢{health_dist.get('ok',0)} 🟡{health_dist.get('warn',0)} 🔴{health_dist.get('danger',0)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Instances w/ Alerts", "告警实例")}</div>
            <div class="value">{summary['instances_with_alerts']}</div>
            <div class="sub">{_i18n(f"{summary['total_alerts']} alerts", f"告警 {summary['total_alerts']} 条")}</div></div>
    </div>
    """

    overview_html = f"""
    {overview_kpis}
    <div class="chart-grid">
        <div class="chart-card"><h4>{_i18n("Category Distribution", "实例类别分布")}</h4><div id="chart-category" class="echart" style="height:240px"></div></div>
        <div class="chart-card"><h4>{_i18n("Status Distribution", "实例状态分布")}</h4><div id="chart-status" class="echart" style="height:240px"></div></div>
        <div class="chart-card"><h4>{_i18n("Health Distribution", "健康状态分布")}</h4><div id="chart-health" class="echart" style="height:240px"></div></div>
        <div class="chart-card"><h4>{_i18n("Instances per Region", "各 Region 实例数")}</h4><div id="chart-regions" class="echart" style="height:240px"></div></div>
    </div>
    <h3>{_i18n("Instances per Region (detail)", "各 Region 实例数明细")}</h3>
    <div class="table-scroll"><table><tr><th>Region</th><th>{_i18n("Instances", "实例数")}</th></tr>{region_rows}</table></div>
    """

    # ── Section 2: Health-score ranking ──
    hr_rows = []
    for i, d in enumerate(summary['health_ranking'], 1):
        score = d.get('health_score', 0)
        emoji, cls = score_status(score)
        attr = d.get('attribute') or {}
        deds_list = (d.get('health_deductions') or [])[:3]
        deds_en = '; '.join(_html_escape(ded.get('en', '')) for ded in deds_list if isinstance(ded, dict))
        deds_zh = '；'.join(_html_escape(ded.get('zh', '')) for ded in deds_list if isinstance(ded, dict))
        deds_html = _i18n(deds_en, deds_zh)
        hr_rows.append(
            f'<tr><td>{i}</td><td>{link(d["instance_id"])}</td>'
            f'<td>{_html_escape(d["region_id"])}</td>'
            f'<td class="{cls}">{emoji} {score}</td>'
            f'<td>{_html_escape(attr.get("category","")) or "N/A"}</td>'
            f'<td>{_html_escape(attr.get("instance_class",""))}</td>'
            f'<td style="font-size:0.78rem;color:var(--muted)">{deds_html}</td></tr>'
        )
    health_ranking_html = (
        f'<p>{_i18n("Lower health score = more issues; investigate these first. Click an instance ID for the detailed report.", "健康分越低代表问题越多，建议优先排查。点击实例 ID 查看详细报告。")}</p>'
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
        f'<th>Region</th><th>{_i18n("Health Score", "健康分")}</th>'
        f'<th>{_i18n("Category", "类别")}</th>'
        f'<th>{_i18n("Class", "规格")}</th>'
        f'<th>{_i18n("Top Deductions", "主要扣分项")}</th></tr>'
        + ''.join(hr_rows) + '</table></div>'
    )

    # ── Section 3: Alert-instance statistics ──
    alert_rows = []
    for i, d in enumerate(summary['alerts_ranking'], 1):
        alerts = d.get('alerts') or []
        max_lvl = max((a.get('level', '') for a in alerts), key=level_weight, default='-')
        cnt = len(alerts)
        # P1+P2 high-severity count (Alibaba Cloud: P1 = critical, P2 = warning)
        high_severity = sum(1 for a in alerts if level_weight(a.get('level', '')) >= 70)
        alert_rows.append(
            f'<tr><td>{i}</td><td>{link(d["instance_id"])}</td>'
            f'<td>{_html_escape(d["region_id"])}</td>'
            f'<td>{cnt}</td>'
            f'<td>{_html_escape(max_lvl)}</td>'
            f'<td>{high_severity}</td></tr>'
        )
    alert_table = (
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
        f'<th>Region</th><th>{_i18n("Alert Count", "告警条数")}</th>'
        f'<th>{_i18n("Max Level", "最高级别")}</th>'
        f'<th>{_i18n("P1/P2 High Severity", "P1/P2 高严重")}</th></tr>'
        + ''.join(alert_rows) + '</table></div>'
        if alert_rows else f'<p class="ok-msg">{_i18n("✅ No recent alerts on any instance", "✅ 所有实例近期均无告警")}</p>'
    )
    alert_section_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">{_i18n("Instances w/ Alerts", "告警实例数")}</div><div class="value">{summary['instances_with_alerts']}</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Total Alerts", "告警总条数")}</div><div class="value">{summary['total_alerts']}</div></div>
    </div>
    <div class="chart-card" style="margin-bottom:1rem"><h4>{_i18n("Alert Level Distribution", "告警级别分布")}</h4>
        <div id="chart-alert-levels" class="echart" style="height:220px"></div></div>
    <h3>{_i18n("Top 20 Instances by Alert Count", "告警最多 TOP 20 实例")}</h3>
    {alert_table}
    """

    # ── Section 4: Resource utilization TOP boards ──
    def res_top_table(key, label_en, label_zh):
        items = summary['resource_tops'].get(key) or []
        if not items:
            return f'<p class="ok-msg">{_i18n(f"No {label_en} data", f"无 {label_zh} 数据")}</p>'
        rows = []
        for i, it in enumerate(items, 1):
            cls = status_class(it['peak'], key)
            rows.append(
                f'<tr><td>{i}</td><td>{link(it["instance_id"])}</td>'
                f'<td>{_html_escape(it["region_id"])}</td>'
                f'<td>{it["avg"]:.2f}%</td>'
                f'<td class="{cls}">{it["peak"]:.2f}%</td></tr>'
            )
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
            f'<th>Region</th><th>{_i18n("Average", "平均")}</th>'
            f'<th>{_i18n("Peak", "峰值")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    resource_section_html = f"""
    <h3>{_i18n("CPU Peak TOP 20", "CPU 峰值 TOP 20")}</h3> {res_top_table('cpu', 'CPU', 'CPU')}
    <h3>{_i18n("Memory Peak TOP 20", "内存峰值 TOP 20")}</h3> {res_top_table('memory', 'Memory', '内存')}
    <h3>{_i18n("Disk Usage TOP 20", "磁盘使用率 TOP 20")}</h3> {res_top_table('space', 'Disk', '磁盘')}
    <h3>{_i18n("IOPS Peak TOP 20", "IOPS 峰值 TOP 20")}</h3> {res_top_table('iops', 'IOPS', 'IOPS')}
    <h3>{_i18n("Connection Usage TOP 20", "连接使用率 TOP 20")}</h3> {res_top_table('connection', 'Connection', '连接')}
    """

    # ── Section 5: Slow log TOP boards ──
    no_slow_msg = f'<p class="ok-msg">{_i18n("✅ No slow queries on any instance", "✅ 所有实例无慢日志")}</p>'

    def slow_count_table():
        rows = []
        items = [x for x in summary['slow_count_ranking'] if x['total_count'] > 0]
        for i, it in enumerate(items, 1):
            rows.append(
                f'<tr><td>{i}</td><td>{link(it["instance_id"])}</td>'
                f'<td>{_html_escape(it["region_id"])}</td>'
                f'<td>{it["total_count"]:,}</td>'
                f'<td>{it["unique_sqls"]}</td></tr>'
            )
        if not rows:
            return no_slow_msg
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
            f'<th>Region</th><th>{_i18n("Slow Log Count", "慢日志条数")}</th>'
            f'<th>{_i18n("SQL Templates", "SQL 模板数")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    def slow_time_table():
        rows = []
        items = [x for x in summary['slow_time_ranking'] if x['total_time'] > 0]
        for i, it in enumerate(items, 1):
            rows.append(
                f'<tr><td>{i}</td><td>{link(it["instance_id"])}</td>'
                f'<td>{_html_escape(it["region_id"])}</td>'
                f'<td>{it["total_time"]:.2f}</td>'
                f'<td>{it["unique_sqls"]}</td></tr>'
            )
        if not rows:
            return no_slow_msg
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
            f'<th>Region</th><th>{_i18n("Total Time (s)", "总耗时(s)")}</th>'
            f'<th>{_i18n("SQL Templates", "SQL 模板数")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    def sql_max_time_table():
        rows = []
        items = [x for x in summary['sql_max_time_top20'] if x['max_time'] > 0]
        for i, it in enumerate(items, 1):
            sql_full = _html_escape(it['sql'])
            rows.append(
                f'<tr><td>{i}</td><td>{link(it["instance_id"])}</td>'
                f'<td>{_html_escape(it["db_name"])}</td>'
                f'<td>{it["max_time"]:.2f}</td>'
                f'<td class="sql-cell">{sql_full}</td></tr>'
            )
        if not rows:
            return f'<p class="ok-msg">{_i18n("No data", "无数据")}</p>'
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
            f'<th>{_i18n("Database", "数据库")}</th>'
            f'<th>{_i18n("Max Exec Time (s)", "最大执行时间(s)")}</th>'
            '<th>SQL</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    slow_section_html = f"""
    <h3>{_i18n("TOP 20 Instances by Slow Log Count", "慢日志条数 TOP 20 实例")}</h3> {slow_count_table()}
    <h3>{_i18n("TOP 20 Instances by Slow Log Total Time", "慢日志总耗时 TOP 20 实例")}</h3> {slow_time_table()}
    <h3>{_i18n("TOP 20 Single Slow SQL by Max Exec Time (cross-instance)", "单条慢 SQL 最大执行时间 TOP 20（跨实例）")}</h3> {sql_max_time_table()}
    """

    # ── Section 6: Space analysis ──
    space_inst_rows = []
    for i, it in enumerate(summary['instance_space_ranking'], 1):
        usage_pct = (it['total_used'] / it['total_storage'] * 100) if it['total_storage'] else 0
        usage_cls = status_class(usage_pct, 'space')
        # Same shadowing concern as render_instance_html — keep `days` (the
        # time-window int from L2215) untouched in case future renderers use it.
        est_days = it.get('estimate_days')
        days_str = _i18n(f'{est_days} days', f'{est_days} 天') if est_days not in (None, '', '-') else '-'
        space_inst_rows.append(
            f'<tr><td>{i}</td><td>{link(it["instance_id"])}</td>'
            f'<td>{_html_escape(it["region_id"])}</td>'
            f'<td>{format_bytes(it["total_used"])}</td>'
            f'<td>{format_bytes(it["total_storage"])}</td>'
            f'<td class="{usage_cls}">{usage_pct:.1f}%</td>'
            f'<td>{format_bytes(it["daily_increment"])}</td>'
            f'<td>{days_str}</td>'
            f'<td>{it["tables_count"]:,}</td></tr>'
        )
    space_inst_table = (
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
        f'<th>Region</th><th>{_i18n("Used", "已用")}</th>'
        f'<th>{_i18n("Allocated", "已分配")}</th>'
        f'<th>{_i18n("Usage", "使用率")}</th>'
        f'<th>{_i18n("Daily Growth", "日均增长")}</th>'
        f'<th>{_i18n("Days Left", "预计可用")}</th>'
        f'<th>{_i18n("Tables", "表数")}</th></tr>'
        + ''.join(space_inst_rows) + '</table></div>'
        if space_inst_rows else f'<p class="ok-msg">{_i18n("No space data", "无空间数据")}</p>'
    )

    table_rows = []
    for i, t in enumerate(summary['tables_top20'], 1):
        table_rows.append(
            f'<tr><td>{i}</td><td>{link(t["instance_id"])}</td>'
            f'<td>{_html_escape(t["db_name"])}</td>'
            f'<td>{_html_escape(t["table_name"])}</td>'
            f'<td>{format_bytes(t["total_size"])}</td>'
            f'<td>{format_bytes(t["data_size"])}</td>'
            f'<td>{format_bytes(t["index_size"])}</td>'
            f'<td>{t["rows"]:,}</td></tr>'
        )
    tables_top_html = (
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
        f'<th>{_i18n("Database", "数据库")}</th>'
        f'<th>{_i18n("Table", "表")}</th>'
        f'<th>{_i18n("Total Size", "总空间")}</th>'
        f'<th>{_i18n("Data", "数据")}</th>'
        f'<th>{_i18n("Index", "索引")}</th>'
        f'<th>{_i18n("Rows", "行数")}</th></tr>'
        + ''.join(table_rows) + '</table></div>'
        if table_rows else f'<p class="ok-msg">{_i18n("No data", "无数据")}</p>'
    )

    frag_rows = []
    for i, t in enumerate(summary['fragmentation_ranking'], 1):
        frag_rows.append(
            f'<tr><td>{i}</td><td>{link(t["instance_id"])}</td>'
            f'<td>{_html_escape(t["db_name"])}</td>'
            f'<td>{_html_escape(t["table_name"])}</td>'
            f'<td>{format_bytes(t["total_size"])}</td>'
            f'<td>{format_bytes(t["frag_size"])}</td>'
            f'<td class="warn">{t["frag_pct"]:.1f}%</td></tr>'
        )
    frag_html = (
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Instance ID", "实例 ID")}</th>'
        f'<th>{_i18n("Database", "数据库")}</th>'
        f'<th>{_i18n("Table", "表")}</th>'
        f'<th>{_i18n("Total Size", "总空间")}</th>'
        f'<th>{_i18n("Fragmented", "碎片")}</th>'
        f'<th>{_i18n("Fragmentation Rate", "碎片率")}</th></tr>'
        + ''.join(frag_rows) + '</table></div>'
        if frag_rows else f'<p class="ok-msg">{_i18n("✅ No significant fragmentation", "✅ 未发现明显碎片")}</p>'
    )

    space_section_html = f"""
    <h3>{_i18n("TOP 20 Instances by Used Space", "实例已用空间 TOP 20")}</h3> {space_inst_table}
    <h3>{_i18n("TOP 20 Tables (cross-instance)", "单表 TOP 20（跨实例聚合）")}</h3> {tables_top_html}
    <h3>{_i18n("TOP 20 Most-Fragmented Tables", "碎片率最高的表 TOP 20")}</h3> {frag_html}
    """

    # ── Section 7: Version & expiration ──
    upg_rows = []
    for it in summary['upgradable']:
        upg_rows.append(
            f'<tr><td>{link(it["instance_id"])}</td><td>{_html_escape(it["region_id"])}</td>'
            f'<td>{_html_escape(it["current"])}</td><td>{_html_escape(it["latest"])}</td></tr>'
        )
    upg_html = (
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Instance ID", "实例 ID")}</th><th>Region</th>'
        f'<th>{_i18n("Current Kernel", "当前内核")}</th>'
        f'<th>{_i18n("Latest Kernel", "最新内核")}</th></tr>'
        + ''.join(upg_rows) + '</table></div>'
        if upg_rows else f'<p class="ok-msg">{_i18n("✅ All instances are on the latest kernel", "✅ 所有实例内核均为最新版本")}</p>'
    )

    def expire_table(records, title_en, title_zh):
        if not records:
            return f'<p class="ok-msg">{_i18n(f"✅ No instances {title_en}", f"✅ 无{title_zh}的实例")}</p>'
        rows = []
        for it in records:
            cls = 'danger' if it['days_left'] <= 30 else 'warn'
            dl = it['days_left']
            days_cell = _i18n(f'{dl} days', f'{dl} 天')
            rows.append(
                f'<tr><td>{link(it["instance_id"])}</td><td>{_html_escape(it["region_id"])}</td>'
                f'<td>{_html_escape(it["expire_date"])}</td>'
                f'<td class="{cls}">{days_cell}</td></tr>'
            )
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>{_i18n("Instance ID", "实例 ID")}</th><th>Region</th>'
            f'<th>{_i18n("Expire Date", "到期日期")}</th>'
            f'<th>{_i18n("Days Left", "剩余天数")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )

    version_section_html = f"""
    <h3>{_i18n(f"Upgradable Kernel Instances ({len(summary['upgradable'])} total)", f"内核版本可升级实例（共 {len(summary['upgradable'])} 个）")}</h3>
    {upg_html}
    <h3>{_i18n(f"Instances Expiring in 30 Days ({len(summary['expiring_30d'])} total)", f"30 天内到期实例（共 {len(summary['expiring_30d'])} 个）")}</h3>
    {expire_table(summary['expiring_30d'], 'expiring in 30 days', '30 天内到期')}
    <h3>{_i18n(f"Instances Expiring in 90 Days ({len(summary['expiring_90d'])} total)", f"90 天内到期实例（共 {len(summary['expiring_90d'])} 个）")}</h3>
    {expire_table(summary['expiring_90d'], 'expiring in 90 days', '90 天内到期')}
    """

    # ── Section 8: Inspection conclusion (problem-list aggregation) ──
    sug_rows = []
    sorted_suggestions = sorted(
        summary['suggestions'].items(),
        key=lambda x: -len(x[1]['instance_ids']),
    )
    for _key, info in sorted_suggestions:
        label = info['label']
        ids = info['instance_ids']
        affected_html = ', '.join(link(iid) for iid in ids[:10])
        more_html = _i18n(
            (f'... {len(ids)} total' if len(ids) > 10 else f'{len(ids)} total'),
            (f'... 共 {len(ids)} 个' if len(ids) > 10 else f'共 {len(ids)} 个'),
        )
        desc_html = _i18n(_html_escape(label.get('en', '')), _html_escape(label.get('zh', '')))
        sug_rows.append(
            f'<tr><td>{desc_html}</td><td>{len(ids)}</td>'
            f'<td>{affected_html}<br/><span style="color:var(--muted);font-size:0.78rem">{more_html}</span></td></tr>'
        )
    problem_table_html = (
        f'<h3>{_i18n("Problem List (sorted by impacted instance count)", "问题清单（按受影响实例数排序）")}</h3>'
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Problem", "问题描述")}</th>'
        f'<th>{_i18n("Impacted Instances", "受影响实例数")}</th>'
        f'<th>{_i18n("Instances", "受影响实例")}</th></tr>'
        + ''.join(sug_rows) + '</table></div>'
        if sug_rows else f'<p class="ok-msg">{_i18n("No notable problems detected.", "✅ 巡检未发现明显问题")}</p>'
    )

    conclusion_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">{_i18n("Global Health", "全局健康度")}</div><div class="value">{global_score}</div><div class="sub">/100</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Healthy", "健康实例")}</div><div class="value ok">{health_dist.get('ok', 0)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Needs Attention", "需关注实例")}</div><div class="value warn">{health_dist.get('warn', 0)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n("Urgent", "紧急处理实例")}</div><div class="value danger">{health_dist.get('danger', 0)}</div></div>
    </div>
    {problem_table_html}
    """

    # Chart JS data. Chart labels stay English-only (legend / tooltip / series
    # names render once at page load and do not switch with the language toggle).
    health_dist_js = json.dumps([
        {'value': health_dist.get('ok', 0), 'name': '🟢 Healthy', 'itemStyle': {'color': '#10b981'}},
        {'value': health_dist.get('warn', 0), 'name': '🟡 Warning', 'itemStyle': {'color': '#f59e0b'}},
        {'value': health_dist.get('danger', 0), 'name': '🔴 Critical', 'itemStyle': {'color': '#ef4444'}},
    ])
    category_dist_js = json.dumps([
        {'value': cluster_count, 'name': 'Cluster'},
        {'value': non_cluster_count, 'name': 'Non-cluster'},
    ])
    status_dist_js = json.dumps([
        {'value': c, 'name': s} for s, c in summary['status_dist'].items()
    ])
    region_dist_js = json.dumps([
        {'value': c, 'name': r} for r, c in sorted(region_count.items(), key=lambda x: -x[1])
    ])
    alert_levels_js = json.dumps(sorted(
        [{'name': lvl, 'value': cnt} for lvl, cnt in summary['alert_level_dist'].items()],
        key=lambda x: -level_weight(x['name'])
    ))

    # Final assembly. <html> `lang` is set by the toggle JS from localStorage at
    # load time (defaults to "en"); CSS hides the inactive language.
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RDS MySQL Inspection Summary</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>{_HTML_CSS}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <button class="lang-toggle" type="button">中文</button>
        <h1>📊 {_i18n("RDS MySQL Inspection Summary Report", "RDS MySQL 巡检汇总报告")}</h1>
        <div class="meta">
            <span>{_i18n("Generated", "巡检时间")}: {inspect_time}</span>
            <span>{_i18n("Time Range", "时间范围")}: {range_str}</span>
            <span>{_i18n("Total Instances", "实例总数")}: {total}</span>
            <span>{_i18n("Global Health", "全局健康度")}: <b>{global_score}/100</b></span>
        </div>
    </div>
    <div class="toc">
        <a href="#sec-1">{_i18n("1. Overview", "一、巡检概览")}</a>
        <a href="#sec-2">{_i18n("2. Health Ranking", "二、健康得分排行")}</a>
        <a href="#sec-3">{_i18n("3. Alert Statistics", "三、告警统计")}</a>
        <a href="#sec-4">{_i18n("4. Resource TOP Boards", "四、资源水位 TOP 榜")}</a>
        <a href="#sec-5">{_i18n("5. Slow Log TOP Boards", "五、慢日志 TOP 榜")}</a>
        <a href="#sec-6">{_i18n("6. Space Analysis", "六、空间分析")}</a>
        <a href="#sec-7">{_i18n("7. Version & Expiration", "七、版本与到期")}</a>
        <a href="#sec-8">{_i18n("8. Conclusion", "八、巡检结论")}</a>
    </div>

    <div class="section" id="sec-1"><h2>{_i18n("1. Inspection Overview", "一、巡检概览")}</h2>{overview_html}</div>
    <div class="section" id="sec-2"><h2>{_i18n("2. Health Score Ranking (lowest TOP 20)", "二、健康得分排行（最不健康 TOP 20）")}</h2>{health_ranking_html}</div>
    <div class="section" id="sec-3"><h2>{_i18n("3. Alert Instance Statistics", "三、告警实例统计")}</h2>{alert_section_html}</div>
    <div class="section" id="sec-4"><h2>{_i18n("4. Resource Utilization TOP Boards", "四、资源水位 TOP 榜")}</h2>{resource_section_html}</div>
    <div class="section" id="sec-5"><h2>{_i18n("5. Slow Log TOP Boards", "五、慢日志 TOP 榜")}</h2>{slow_section_html}</div>
    <div class="section" id="sec-6"><h2>{_i18n("6. Space Analysis", "六、空间分析")}</h2>{space_section_html}</div>
    <div class="section" id="sec-7"><h2>{_i18n("7. Version & Expiration", "七、版本与到期")}</h2>{version_section_html}</div>
    <div class="section" id="sec-8"><h2>{_i18n("8. Inspection Conclusion", "八、巡检结论")}</h2>{conclusion_html}</div>

    <div class="footer">RDS MySQL Inspection Summary · {inspect_time}</div>
</div>
<script>
{_LANG_TOGGLE_JS}
function makePie(domId, data) {{
    var el = document.getElementById(domId);
    if (!el) return;
    var chart = echarts.init(el);
    chart.setOption({{
        tooltip: {{trigger:'item', formatter:'{{b}}: {{c}} ({{d}}%)'}},
        legend: {{orient:'vertical', right:5, top:'middle', textStyle:{{fontSize:11}}}},
        series: [{{type:'pie', radius:['40%','70%'], center:['38%','50%'],
                   label:{{formatter:'{{b}}\\n{{c}}'}}, data:data}}]
    }});
    window.addEventListener('resize', function(){{chart.resize();}});
}}
makePie('chart-health', {health_dist_js});
makePie('chart-category', {category_dist_js});
makePie('chart-status', {status_dist_js});
(function() {{
    var el = document.getElementById('chart-regions');
    if (!el) return;
    var chart = echarts.init(el);
    var data = {region_dist_js};
    chart.setOption({{
        tooltip: {{trigger:'axis'}},
        grid: {{left:60, right:20, top:10, bottom:30}},
        xAxis: {{type:'value'}},
        yAxis: {{type:'category', data:data.map(function(d){{return d.name;}}).reverse()}},
        series: [{{type:'bar', data:data.map(function(d){{return d.value;}}).reverse(),
                   itemStyle:{{color:'#3b82f6'}}, label:{{show:true, position:'right'}}}}]
    }});
    window.addEventListener('resize', function(){{chart.resize();}});
}})();
(function() {{
    var el = document.getElementById('chart-alert-levels');
    if (!el) return;
    var data = {alert_levels_js};
    if (!data.length) return;
    var chart = echarts.init(el);
    var levelColor = function(name) {{
        var n = (name||'').toUpperCase();
        if (n.indexOf('CRITICAL')>=0||n==='P0'||n==='P1') return '#ef4444';
        if (n.indexOf('WARN')>=0||n==='P2') return '#f59e0b';
        return '#3b82f6';
    }};
    chart.setOption({{
        tooltip: {{trigger:'axis'}},
        grid: {{left:50, right:20, top:10, bottom:30}},
        xAxis: {{type:'category', data:data.map(function(d){{return d.name;}})}},
        yAxis: {{type:'value'}},
        series: [{{type:'bar', data:data.map(function(d){{return {{value:d.value, itemStyle:{{color:levelColor(d.name)}}}};}}),
                   label:{{show:true, position:'top'}}}}]
    }});
    window.addEventListener('resize', function(){{chart.resize();}});
}})();
</script>
</body>
</html>
"""
    return html


# ═══════════════════════════════════════════════════════════════════════════
# 14. Main flow
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        prog='rds-inspect',
        description='Alibaba Cloud RDS MySQL batch health inspection tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single-instance inspection (default 7 days)
  %(prog)s -i rm-bp1xxx

  # Multiple instances (comma-separated or repeated -i)
  %(prog)s -i rm-bp1xxx,rm-bp1yyy --days 14
  %(prog)s -i rm-bp1xxx -i rm-bp1yyy

  # Global inspection (up to 30 days)
  %(prog)s --all --days 30

  # Restrict the scan to certain regions for faster runs
  %(prog)s --all --regions cn-hangzhou,cn-shanghai

  # Skip space analysis (which is the slow step)
  %(prog)s --all --skip-space
        """,
    )
    parser.add_argument('-i', '--instance-ids', action='append', default=[],
                        help='Instance ID (may be repeated or comma-separated)')
    parser.add_argument('--all', action='store_true',
                        help='Inspect every RDS MySQL instance')
    parser.add_argument('-d', '--days', type=int, default=7,
                        help='Time range in days (default 7, max 30)')
    parser.add_argument('--start-time',
                        help='Start date YYYY-MM-DD (mutually exclusive with --days)')
    parser.add_argument('--end-time',
                        help='End date YYYY-MM-DD (must be paired with --start-time)')
    parser.add_argument('-o', '--output',
                        help='Output directory (default ./rds-inspection-reports/<ts>/)')
    parser.add_argument('-p', '--profile',
                        help='aliyun CLI profile')
    parser.add_argument('--regions',
                        help='Comma-separated list of regions to limit the scan to')
    parser.add_argument('-c', '--concurrency', type=int, default=3,
                        help='Per-instance inspection concurrency (default 3)')
    parser.add_argument('--region-concurrency', type=int, default=3,
                        help='Region scan concurrency (default 3)')
    parser.add_argument('--skip-space', action='store_true',
                        help='Skip DAS space analysis (saves 30-150s per instance)')
    return parser.parse_args()


def normalize_instance_ids(raw_list):
    """Accept either -i a,b,c or repeated -i a -i b forms."""
    out = []
    for raw in raw_list:
        for part in raw.split(','):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def resolve_time_range(args):
    """Return the (start_dt, end_dt, days) tuple."""
    if args.start_time and args.end_time:
        try:
            start_dt = datetime.strptime(args.start_time, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(args.end_time, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            print('ERROR: --start-time / --end-time must be in YYYY-MM-DD format', file=sys.stderr)
            sys.exit(2)
        if end_dt <= start_dt:
            print('ERROR: --end-time must be later than --start-time', file=sys.stderr)
            sys.exit(2)
        days = (end_dt - start_dt).days
        if days > 30:
            print(f'ERROR: time range exceeds the 30-day limit (current {days} days)', file=sys.stderr)
            sys.exit(2)
        return start_dt, end_dt, days
    elif args.start_time or args.end_time:
        print('ERROR: --start-time and --end-time must be provided together', file=sys.stderr)
        sys.exit(2)

    days = args.days
    if days < 1 or days > 30:
        print(f'ERROR: --days must be between 1 and 30 (current {days})', file=sys.stderr)
        sys.exit(2)
    end_dt = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=days)
    return start_dt, end_dt, days


def main():
    args = parse_args()

    # Validate mutually exclusive options
    instance_ids = normalize_instance_ids(args.instance_ids)
    if not instance_ids and not args.all:
        print('ERROR: must specify either -i/--instance-ids or --all', file=sys.stderr)
        sys.exit(2)
    if instance_ids and args.all:
        print('WARNING: -i and --all both supplied; -i will be ignored, running global inspection', file=sys.stderr)
        instance_ids = []

    # CLI profile
    global _CLI_PROFILE
    _CLI_PROFILE = args.profile

    # Check that the aliyun CLI is available
    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('ERROR: aliyun CLI not found; please install it first: https://help.aliyun.com/zh/cli/', file=sys.stderr)
        sys.exit(1)

    # Time range
    time_range = resolve_time_range(args)
    start_dt, end_dt, days = time_range
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    # Output directory
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = args.output or os.path.join('./rds-inspection-reports', ts)
    os.makedirs(out_dir, exist_ok=True)
    instances_dir = os.path.join(out_dir, 'instances')
    os.makedirs(instances_dir, exist_ok=True)

    # Print inspection task overview
    print('=' * 64)
    print('  Alibaba Cloud RDS MySQL Instance Inspection')
    print('=' * 64)
    print(f'  Time range: {to_iso_date(start_dt)} ~ {to_iso_date(end_dt)} ({days} days)')
    print(f'  Concurrency: instance {args.concurrency} / region {args.region_concurrency}')
    if _CLI_PROFILE:
        print(f'  Profile: {_CLI_PROFILE}')
    print(f'  Output directory: {out_dir}')
    print('-' * 64)

    # Phase 1: Region list
    filter_regions = None
    if args.regions:
        filter_regions = [r.strip() for r in args.regions.split(',') if r.strip()]
    regions = list_active_regions(filter_regions)
    if not regions:
        print('ERROR: no available regions were obtained', file=sys.stderr)
        sys.exit(1)

    # Phase 2: Full instance discovery
    all_instances, region_count = discover_all_instances(regions, args.region_concurrency)
    scanned_total = len(all_instances)
    if not all_instances:
        print('ERROR: no RDS MySQL instances were found', file=sys.stderr)
        sys.exit(1)

    # Phase 3: Filter target instances
    if args.all:
        target_metas = all_instances
        print(f'Inspection target: all {len(target_metas)} RDS MySQL instances')
    else:
        existing = {x['instance_id']: x for x in all_instances}
        target_metas = []
        missing = []
        for iid in instance_ids:
            if iid in existing:
                target_metas.append(existing[iid])
            else:
                missing.append(iid)
        if missing:
            print(f'WARNING: the following instance IDs were not found in the full list (ignored): {", ".join(missing)}')
        if not target_metas:
            print('ERROR: no target instances matched; exiting', file=sys.stderr)
            sys.exit(1)
        print(f'Inspection target: {len(target_metas)} / {scanned_total} RDS MySQL instances')

    print('-' * 64)

    # Phase 4: Instance-level inspection (concurrent)
    print(f'Starting instance inspection (concurrency {args.concurrency}, ~30-180s per instance)...')
    t_start = time.time()

    def _inspect_wrapper(meta):
        try:
            d = inspect_one_instance(meta, start_ms, end_ms, skip_space=args.skip_space)
            print(f'  OK  {meta["instance_id"]} ({meta["region_id"]}) health score {d.get("health_score",0)}',
                  flush=True)
            return d
        except Exception as e:
            traceback.print_exc()
            return {
                'instance_id': meta['instance_id'],
                'region_id': meta['region_id'],
                'errors': [f'Inspection failed: {e}'],
                'attribute': None, 'metrics': {}, 'alerts': [],
                'slow_logs': {'top_count': [], 'top_query_time': [], 'node_id': None},
                'space': None, 'health_score': 0, 'health_deductions': [],
            }

    instances_data = parallel_map(_inspect_wrapper, target_metas,
                                   max_workers=args.concurrency)
    # Filter out None
    instances_data = [d for d in instances_data if d]
    elapsed = time.time() - t_start
    print(f'   Instance inspection finished in {elapsed:.0f}s')
    print('-' * 64)

    # Phase 5: Render per-instance HTML
    print(f'Rendering per-instance reports ({len(instances_data)} total)...')
    for d in instances_data:
        try:
            html = render_instance_html(d, time_range, slow_log_days=days)
            out_path = os.path.join(instances_dir, f'{d["instance_id"]}.html')
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception as e:
            print(f'  WARNING: failed to render {d["instance_id"]}: {e}', file=sys.stderr)

    # Phase 6: Render summary HTML
    print('Generating summary report...')
    summary = aggregate_summary(instances_data, time_range, region_count, scanned_total)
    summary_html = render_summary_html(summary)
    summary_path = os.path.join(out_dir, 'summary.html')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_html)

    # Done
    print('=' * 64)
    print('Inspection complete')
    print(f'   Summary report: {summary_path}')
    print(f'   Per-instance reports: {instances_dir}/<instance_id>.html')
    print('=' * 64)


if __name__ == '__main__':
    main()

