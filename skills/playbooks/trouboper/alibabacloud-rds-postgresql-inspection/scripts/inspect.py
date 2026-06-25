#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alibaba Cloud RDS PostgreSQL batch instance inspection script

Supports single-instance, multi-instance, or all-instance global inspection. Time window: 1-30 days (default 7).
Invokes RDS APIs via the aliyun CLI and outputs one HTML inspection report per instance plus one summary HTML report.

Usage:
    python3 inspect.py -i pgm-bp1xxx
    python3 inspect.py -i pgm-bp1xxx,pgm-bp1yyy --days 14
    python3 inspect.py --all --output ./reports/
    python3 inspect.py --all --regions cn-hangzhou,cn-shanghai --days 30
"""

import argparse
import concurrent.futures
import json
import os
import secrets
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

_CLI_PROFILE = None
_CLI_TIMEOUT = 60
_CLI_MAX_RETRIES = 5
_CLI_RETRY_BASE = 3  # backoff base (seconds)

# User-Agent configuration
# Per SA-2.11, the User-Agent MUST always follow the full format:
#   AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
# If SKILL_SESSION_ID is not provided via env, generate a 32-char hex fallback
# so the {session-id} segment is never omitted.
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '').strip() or secrets.token_hex(16)

# Security whitelist: only read-only API actions are allowed
_ALLOWED_ACTIONS = frozenset({
    # RDS Read-only API
    'describe-regions',
    'describe-db-instances',
    'describe-db-instance-attribute',
    'describe-db-instance-performance',
    'describe-slow-log-records',
    'describe-slow-logs',
    'describe-error-logs',
    'describe-parameters',
    'describe-resource-usage',
    # CMS Read-only API
    'describe-metric-list',
    'describe-alert-log-list',
    'describe-monitor-groups',
})

# Throttling error keywords
_THROTTLING_KEYWORDS = ('Throttling', 'Throttled', 'FlowControl', 'TooManyRequests', 'QPS')


def _build_user_agent() -> str:
    """Build the complete User-Agent string required by SA-2.11.

    Format: AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
    The {session-id} segment is mandatory and MUST never be omitted.
    """
    return 'AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/' + SESSION_ID


def _is_throttling_error(stderr: str, error_code: str = '') -> bool:
    """Detect whether the error is a throttling error."""
    if any(kw in stderr for kw in _THROTTLING_KEYWORDS):
        return True
    if any(kw in error_code for kw in _THROTTLING_KEYWORDS):
        return True
    return False


def ensure_cli_plugins(required_plugins: list = None):
    """
    Pre-install required CLI plugins to avoid auto-install conflicts during concurrent calls.
    Must be invoked synchronously before concurrent data collection.
    """
    if required_plugins is None:
        required_plugins = ['aliyun-cli-rds', 'aliyun-cli-cms']

    print('🔧 Checking CLI plugins...', flush=True)

    # Fetch the list of installed plugins
    try:
        result = subprocess.run(
            ['aliyun', 'plugin', 'list'],
            capture_output=True, text=True, timeout=30
        )
        installed = result.stdout.lower()
    except Exception as e:
        print(f'  [WARN] Failed to retrieve plugin list: {e}', file=sys.stderr)
        installed = ''

    for plugin in required_plugins:
        plugin_lower = plugin.lower()
        if plugin_lower in installed:
            print(f'  ✅ {plugin} installed')
            continue

        print(f'  📦 Install {plugin}...', end=' ', flush=True)
        try:
            # CLI 3.3.16+ Must use the --name argument
            install_result = subprocess.run(
                ['aliyun', 'plugin', 'install', '--name', plugin],
                capture_output=True, text=True, timeout=120
            )
            if install_result.returncode == 0:
                print('✅')
            else:
                print(f'❌ {install_result.stderr[:100]}')
        except subprocess.TimeoutExpired:
            print('❌ timeout')
        except Exception as e:
            print(f'❌ {e}')

    # Verifying plugin installation
    print('🔍 Verifying plugin installation...', flush=True)
    try:
        result = subprocess.run(
            ['aliyun', 'plugin', 'list'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f'  Installed plugins: {result.stdout.strip()[:200]}')
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# 1. CLI Call wrapper
# ═══════════════════════════════════════════════════════════════════════════

def call_cli(_svc, _action, region=None, endpoint=None, timeout=None, **kwargs):
    """
    Invoke the aliyun CLI and return the parsed JSON dict or None.
    Includes whitelist enforcement and throttling-retry behaviour.
    """
    # Security whitelist check
    if _action not in _ALLOWED_ACTIONS:
        print(f'  [BLOCKED] {_svc} {_action}: action not in whitelist', file=sys.stderr)
        return None

    cmd = ['aliyun', _svc, _action, '--user-agent', _build_user_agent()]
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

    # Retry loop (handles throttling and timeouts)
    for attempt in range(_CLI_MAX_RETRIES):
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
                # Detect throttling errors
                if _is_throttling_error(stderr):
                    wait_time = _CLI_RETRY_BASE * (2 ** attempt)
                    wait_time = min(wait_time, 30)  # Maximum backoff 30s
                    print(f'  [THROTTLED] {_svc} {_action}: retry {attempt+1}/{_CLI_MAX_RETRIES} in {wait_time}s',
                          file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                # Non-throttling error
                if stderr and 'InvalidAction' not in stderr:
                    err_msg = stderr.split('\n')[-1][:200]
                    print(f'  [WARN] {_svc} {_action}: {err_msg}', file=sys.stderr)
                return None
        except subprocess.TimeoutExpired:
            if attempt < _CLI_MAX_RETRIES - 1:
                wait_time = _CLI_RETRY_BASE * (2 ** attempt)
                print(f'  [TIMEOUT] {_svc} {_action}: retry {attempt+1}/{_CLI_MAX_RETRIES} in {wait_time}s',
                      file=sys.stderr)
                time.sleep(wait_time)
                continue
            print(f'  [WARN] {_svc} {_action} timed out after {_CLI_MAX_RETRIES} retries',
                  file=sys.stderr)
        except Exception as e:
            print(f'  [ERROR] {_svc} {_action}: {e}', file=sys.stderr)
            return None

    return None


def parallel_map(fn, items, max_workers=3, desc=None):
    """Run fn(item) for each item concurrently and return results preserving input order."""
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
# 2. RDS Region & Instance discovery
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
    """Filter out special-purpose regions such as ACDR / JVA / industry cloud / POC."""
    if not rid:
        return False
    rl = rid.lower()
    return not any(p in rl for p in _SPECIAL_REGION_PATTERNS)


def list_active_regions(filter_regions=None):
    """Fetch all available RDS regions; filter out special-purpose regions."""
    print('🌐 Fetching region list...', end=' ', flush=True)
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
        print(f'⚠️  use fallback ({len(regions)} )')
    else:
        print(f'✅ ({len(regions)} )')
    if filter_regions:
        regions = [r for r in regions if r in filter_regions]
    return regions


def list_instances_in_region(region):
    """Paginate through all RDS PostgreSQL instances in a single region."""
    instances = []
    page = 1
    page_size = 100
    while True:
        data = call_cli('rds', 'describe-db-instances', region=region,
                        **{'engine': 'PostgreSQL',
                           'biz-region-id': region,
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
    """Scan all regions concurrently and merge the full RDS PostgreSQL instance list."""
    print(f'🔍 Scan {len(regions)} regions of RDS PostgreSQL instances (concurrency {region_concurrency})...')
    results = parallel_map(list_instances_in_region, regions,
                           max_workers=region_concurrency, desc='Scan instances')
    all_instances = []
    region_count = {}
    for r, lst in zip(regions, results):
        if not lst:
            continue
        all_instances.extend(lst)
        region_count[r] = len(lst)
    print(f'   Total {len(all_instances)} instances / {len(region_count)} region(s)')
    return all_instances, region_count


def get_instance_attribute(instance_id, region):
    """DescribeDBInstanceAttribute Fetch detailed attributes."""
    data = call_cli('rds', 'describe-db-instance-attribute', region=region,
                    **{'db-instance-id': instance_id})
    if not data:
        return None
    items = data.get('Items', {}).get('DBInstanceAttribute', [])
    if not items:
        return None
    return items[0]


def normalize_attribute(attr):
    """Extract key fields from the DescribeDBInstanceAttribute result."""
    if not attr:
        return {}
    
    # SlaveZones
    slave_zones_raw = attr.get('SlaveZones', {})
    if isinstance(slave_zones_raw, dict):
        slave_zones_raw = slave_zones_raw.get('SlaveZone', [])
    slave_zones = [z.get('ZoneId', '') for z in slave_zones_raw if isinstance(z, dict)]
    
    return {
        'instance_id': attr.get('DBInstanceId', ''),
        'region_id': attr.get('RegionId', ''),
        'engine': attr.get('Engine', 'PostgreSQL'),
        'engine_version': attr.get('EngineVersion', ''),
        'category': attr.get('Category', ''),
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
        'master_zone': attr.get('MasterZone') or attr.get('ZoneId', ''),
        'slave_zones': slave_zones,
        'maintain_time': attr.get('MaintainTime', ''),
        'expire_time': attr.get('ExpireTime', ''),
        'creation_time': attr.get('CreationTime', ''),
        'current_kernel': attr.get('CurrentKernelVersion', ''),
        'latest_kernel': attr.get('LatestKernelVersion', ''),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. Utility functions
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
    """Return a CSS class name for HTML colouring."""
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
    """CMS Returned timestamps are usually milliseconds (int) or ISO strings. Normalize to ms."""
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


def level_weight(level):
    """Alert severity → Weight value."""
    if not level:
        return 0
    level = level.upper()
    if level in ('CRITICAL', 'P0', 'P1'):
        return 100
    if level in ('WARN', 'WARNING', 'P2'):
        return 70
    if level in ('INFO', 'P3', 'P4'):
        return 30
    return 50


# ═══════════════════════════════════════════════════════════════════════════
# 4. CMS Monitoring data collection (consistent with the MySQL skill)
# ══════════════════════════════════════════════════════════════════════════

# 5 core monitoring metrics (PostgreSQL shares metric names with MySQL)
METRICS_POSTGRESQL = [
    ('CpuUsage', 'cpu', 'CPU Usage rate', '%'),
    ('MemoryUsage', 'memory', 'Memory usage', '%'),
    ('DiskUsage', 'space', 'Disk usage', '%'),
    ('IOPSUsage', 'iops', 'IOPS Usage rate', '%'),
    ('ConnectionUsage', 'connection', 'Connection usage rate', '%'),
]

METRIC_KEY_MAP = ['cpu', 'memory', 'space', 'iops', 'connection']
METRIC_LABEL_MAP = {
    'cpu': {'en': 'CPU', 'zh': 'CPU'},
    'memory': {'en': 'Memory', 'zh': 'Memory'},
    'space': {'en': 'Disk', 'zh': 'Disk'},
    'iops': {'en': 'IOPS', 'zh': 'IOPS'},
    'connection': {'en': 'Connections', 'zh': 'Connections'},
}


def call_cms_metric_paginated(metric_name, dimensions_dict, start_ms, end_ms, period=60):
    """Paginate through CMS DescribeMetricList; returns [(ts_ms, value), ...]"""
    points = []
    next_token = None
    page = 0
    dims_json = json.dumps([dimensions_dict], separators=(',', ':'))
    while page < 100:  # Defensive upper bound
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
        # CMS The returned Datapoints is a JSON string
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


# ═══════════════════════════════════════════════════════════════════════════
# 4.5 RDS Performance metric collection (PostgreSQL-specific sub-metrics)
# ══════════════════════════════════════════════════════════════════════════

# PostgreSQL Specific performance metric list
RDS_PERFORMANCE_METRICS = [
    'MemoryUsage',
    'CpuUsage',
    'PgSQL_IOPS',
    'PolarDBConnections',
    'PolarDBLocalDiskUsage',
    'PolarDBLongTransaction',
    'PolarDBQPSTPS',
    'PolarDBSwellTime',
    'PolarDBReplication',
]

# Metric label mapping
RDS_METRIC_LABELS = {
    'MemoryUsage': {'en': 'Memory Usage', 'zh': 'Memory usage'},
    'CpuUsage': {'en': 'CPU Usage', 'zh': 'CPU Usage rate'},
    'PgSQL_IOPS': {'en': 'IOPS', 'zh': 'IOPS Usage amount'},
    'PolarDBConnections': {'en': 'Connections', 'zh': 'Connection usage'},
    'PolarDBLocalDiskUsage': {'en': 'Local Disk Usage', 'zh': 'Local disk usage'},
    'PolarDBLongTransaction': {'en': 'Long Transactions', 'zh': 'Long transactions'},
    'PolarDBQPSTPS': {'en': 'QPS/TPS', 'zh': 'QPS/TPS'},
    'PolarDBSwellTime': {'en': 'Swell Time', 'zh': 'Bloat hotspots'},
    'PolarDBReplication': {'en': 'Replication', 'zh': 'Replication delay'},
}

# Sub-metric label mapping
RDS_SUB_METRIC_LABELS = {
    # PolarDBConnections Sub-metric
    'mean_active_session': {'en': 'Active Sessions', 'zh': 'Active connections'},
    'mean_idle_connection': {'en': 'Idle Connections', 'zh': 'Idle connections'},
    'mean_total_session': {'en': 'Total Sessions', 'zh': 'Total connections'},
    'mean_waiting_connection': {'en': 'Waiting Connections', 'zh': 'Waiting connections'},
    # PolarDBLocalDiskUsage Sub-metric
    'mean_local_pg_wal_dir_size': {'en': 'WAL Size', 'zh': 'WAL Space'},
    'mean_local_pg_log_dir_size': {'en': 'Log Size', 'zh': 'Log Space'},
    'mean_local_base_dir_size': {'en': 'Data Size', 'zh': 'Data space'},
    # PolarDBLongTransaction Sub-metric
    'mean_one_second_transactions': {'en': '>1s Transactions', 'zh': '>1Transactions per second'},
    'mean_three_seconds_transactions': {'en': '>3s Transactions', 'zh': '>3Transactions per second'},
    # PolarDBQPSTPS Sub-metric
    'mean_commits_delta': {'en': 'Commits/s', 'zh': 'Commits per second'},
    'mean_rollbacks_delta': {'en': 'Rollbacks/s', 'zh': 'Rollbacks per second'},
    'mean_deadlocks_delta': {'en': 'Deadlocks/s', 'zh': 'Deadlocks per second'},
    'mean_tps': {'en': 'TPS', 'zh': 'Transactions per second'},
    # PolarDBReplication Sub-metric
    'mean_replay_latency_in_mb': {'en': 'Replay Latency', 'zh': 'Standby sync delay'},
    'mean_send_latency_in_mb': {'en': 'Send Latency', 'zh': 'Primary send delay'},
    'mean_logical_rep_latency_in_mb': {'en': 'Logical Rep Latency', 'zh': 'Logical replication delay'},
}


def call_rds_performance_metric(instance_id, region, key, start_time_str, end_time_str):
    """Call DescribeDBInstancePerformance for a single performance metric."""
    try:
        data = call_cli('rds', 'describe-db-instance-performance', region=region,
                        **{
                            'db-instance-id': instance_id,
                            'key': key,
                            'start-time': start_time_str,
                            'end-time': end_time_str,
                        })
        if not data:
            return None
        return data.get('PerformanceKeys', {}).get('PerformanceKey', [])
    except Exception as e:
        print(f'   [WARN] DescribeDBInstancePerformance {key} failed: {e}')
        return None


def collect_rds_performance_metrics(instance_id, region, start_ms, end_ms):
    """Collect PostgreSQL-specific performance sub-metrics."""
    # Convert timestamps into RDS API format (YYYY-MM-DDTHH:mmZ)
    start_dt = datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(end_ms / 1000.0, tz=timezone.utc)
    start_time_str = start_dt.strftime('%Y-%m-%dT%H:%MZ')
    end_time_str = end_dt.strftime('%Y-%m-%dT%H:%MZ')
    
    result = {}
    for key in RDS_PERFORMANCE_METRICS:
        perf_keys = call_rds_performance_metric(instance_id, region, key, start_time_str, end_time_str)
        if not perf_keys:
            result[key] = None
            continue
        
        # Parse performance data and store time-series
        # APIReturn format: Value field contains multiple values separated by&; ValueFormat defines the order
        sub_metrics = {}  # {sub_metric_name: {timeseries: [(date, value), ...]}}
        
        for pk in perf_keys:
            metric_name = pk.get('Key', '')
            value_format = pk.get('ValueFormat', '')  # e.g. "mean_active_session&mean_idle_connection&..."
            
            # Parse ValueFormat and obtain sub-metric names
            sub_metric_names = [name.strip() for name in value_format.split('&') if name.strip()]
            
            # Initialize timeseries for each sub-metric
            for sub_name in sub_metric_names:
                if sub_name not in sub_metrics:
                    sub_metrics[sub_name] = {'timeseries': []}
            
            # Parse each data point
            for pv in pk.get('Values', {}).get('PerformanceValue', []):
                date_str = pv.get('Date', '')
                value_str = pv.get('Value', '')
                
                # Split the Value field (with&as separator)
                values = [v.strip() for v in value_str.split('&')]
                
                # Map each value to its corresponding sub-metric
                for i, sub_name in enumerate(sub_metric_names):
                    if i < len(values):
                        try:
                            val = float(values[i])
                            sub_metrics[sub_name]['timeseries'].append((date_str, val))
                        except (ValueError, TypeError):
                            pass
        
        # Compute avg and peak
        for sub_name in sub_metrics:
            timeseries = sub_metrics[sub_name]['timeseries']
            if timeseries:
                values = [v for _, v in timeseries]
                sub_metrics[sub_name]['avg'] = sum(values) / len(values)
                sub_metrics[sub_name]['peak'] = max(values)
        
        result[key] = sub_metrics if sub_metrics else None
    
    return result


def collect_slow_logs(instance_id, region, start_ms, end_ms, top_n=20):
    """Collect slow log records within the given time window, sorted by execution time, top N.

    DescribeSlowLogRecords only allows up to 24 hours per call, so when the
    requested window is longer we split it into <=24h chunks, query each
    chunk and aggregate the results. This keeps the slow-log statistics
    window consistent with the monitoring data and alert history windows.
    """
    try:
        chunk_ms = 24 * 60 * 60 * 1000  # API limit: 24 hours per call
        total_ms = max(1, end_ms - start_ms)
        n_chunks = (total_ms + chunk_ms - 1) // chunk_ms

        win_start = datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        win_end = datetime.fromtimestamp(end_ms / 1000.0, tz=timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        print(f'   [INFO] Collect slow logs: {win_start} ~ {win_end} '
              f'(split into {n_chunks} chunk(s) of <=24h, API limit)')

        all_slow_logs = []
        cur_start = start_ms
        chunk_idx = 0
        while cur_start < end_ms:
            chunk_idx += 1
            cur_end = min(cur_start + chunk_ms, end_ms)
            cs_str = datetime.fromtimestamp(cur_start / 1000.0, tz=timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
            ce_str = datetime.fromtimestamp(cur_end / 1000.0, tz=timezone.utc).strftime('%Y-%m-%dT%H:%MZ')

            # Call DescribeSlowLogRecords for this <=24h chunk
            data = call_cli('rds', 'describe-slow-log-records', region=region,
                            **{
                                'db-instance-id': instance_id,
                                'start-time': cs_str,
                                'end-time': ce_str,
                                'page-size': '100',  # max page size (range 30~100)
                                'page-number': '1',
                            })

            items = []
            if data:
                items = data.get('Items', {}).get('SQLSlowRecord', []) or []
            print(f'   [INFO]   chunk {chunk_idx}/{n_chunks}: {cs_str} ~ {ce_str}, returned {len(items)} records')

            for item in items:
                all_slow_logs.append({
                    'sql': item.get('SQLText', ''),
                    'execution_time': float(item.get('QueryTimeMS', '0')) / 1000.0,  # ms -> s
                    'parse_rows': int(item.get('ParseRowCounts', '0')),
                    'return_rows': int(item.get('ReturnRowCounts', '0')),
                    'execution_start_time': item.get('ExecutionStartTime', ''),
                    'database_name': item.get('DBName', ''),
                    'host_address': item.get('HostAddress', ''),
                    'query_times': int(item.get('QueryTimes', '0')),
                    'lock_time_ms': int(item.get('LockTimeMS', '0')),
                })

            cur_start = cur_end

        print(f'   [INFO] Slow log aggregated: {len(all_slow_logs)} records across {n_chunks} chunk(s)')
        # Sort by execution time, take top N across the full window
        all_slow_logs.sort(key=lambda x: x['execution_time'], reverse=True)
        return all_slow_logs[:top_n]

    except Exception as e:
        print(f'   [WARN] DescribeSlowLogRecords failed: {e}')
        return []


def collect_instance_metrics(instance_attr, start_ms, end_ms):
    """Collect all 5 metrics for one instance."""
    instance_id = instance_attr['instance_id']
    region = instance_attr['region_id']
    
    result = {}
    for metric_name, key, label, unit in METRICS_POSTGRESQL:
        result[key] = {
            'metric_name': metric_name,
            'label': label,
            'unit': unit,
            'cluster': None,
        }
        # Call CMS APIs to fetch monitoring data
        pts = call_cms_metric_paginated(
            metric_name, {'instanceId': instance_id}, start_ms, end_ms,
        )
        values = [v for _, v in pts]
        avg, peak = calc_avg_peak(values)
        result[key]['cluster'] = {
            'avg': avg, 'peak': peak, 'timeseries': pts,
        }
    
    # Call DescribeDBInstancePerformance to fetch PostgreSQL-specific sub-metrics
    rds_perf_metrics = collect_rds_performance_metrics(instance_id, region, start_ms, end_ms)
    result['rds_performance'] = rds_perf_metrics
    
    # Collect slow logs (within the same time window as monitoring data, TOP 20)
    slow_logs = collect_slow_logs(instance_id, region, start_ms, end_ms, top_n=20)
    result['slow_logs'] = slow_logs
    
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 5. CMS Alert history collection
# ══════════════════════════════════════════════════════════════════════════

# Alert severity ranking weights (larger means more severe)
ALERT_LEVEL_WEIGHT = {
    'CRITICAL': 100, 'P1': 100, 'P0': 110,
    'WARN': 70, 'WARNING': 70, 'P2': 70,
    'INFO': 30, 'P3': 30, 'P4': 10,
    '': 0, None: 0,
}


def alert_level_weight(level_str):
    """Alert severity → Weight value"""
    if not level_str:
        return 0
    s = str(level_str).upper().strip()
    return ALERT_LEVEL_WEIGHT.get(s, 50)


def format_alert_time(ts):
    """Millisecond timestamp → 'YYYY-MM-DD HH:MM:SS' string"""
    if not ts:
        return ''
    try:
        ms = int(ts)
        if ms > 1e12:  # ms
            dt = datetime.fromtimestamp(ms / 1000.0)
        else:  # already in seconds
            dt = datetime.fromtimestamp(ms)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError):
        return str(ts)


def extract_alert_metadata(message_str):
    """The alert Message is a JSON string; extract RuleName / MetricName / Expression, etc."""
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
    """Fetch the alert history of an instance and return it sorted by severity.
    Note: the CMS DescribeAlertLogList response has no Total field; iterate by items < page_size to decide termination."""
    alerts = []
    page = 1
    page_size = 100
    while page <= 50:  # upper bound 5000 records
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
            meta = extract_alert_metadata(a.get('Message', ''))
            alerts.append({
                'time': format_alert_time(a.get('AlertTime') or a.get('Time')),
                'level': a.get('LevelType') or a.get('Level', ''),
                'level_change': a.get('LevelChange', ''),
                'rule_name': meta.get('rule_name') or a.get('RuleName', ''),
                'metric_name': meta.get('metric_name') or a.get('MetricName', ''),
                'instance_name': a.get('InstanceName', ''),  # Display name (not InstanceId)
                'event_name': a.get('EventName', ''),
                'cur_value': meta.get('cur_value', ''),
                'expression': meta.get('expression', ''),
            })
        # No Total field is returned; terminate when items < page_size
        if len(items) < page_size:
            break
        page += 1

    # Sort by severity desc
    alerts.sort(key=lambda x: -alert_level_weight(x['level']))
    return alerts


def calc_health_score(inst_data):
    """Compute the health score (0-100) based on threshold violations, alerts, slow logs and version status."""
    score = 100
    deductions = []

    metrics = inst_data.get('metrics') or {}
    metric_thresholds = {
        'cpu': ('cpu', 'CPU'), 'memory': ('memory', 'Memory'),
        'space': ('space', 'Disk'), 'iops': ('iops', 'IOPS'),
        'connection': ('connection', 'Connections'),
    }
    for key, (mtype, label) in metric_thresholds.items():
        m = metrics.get(key, {}).get('cluster') or {}
        peak = m.get('peak', 0) or 0
        if mtype == 'space':
            if peak > 85:
                score -= 15; deductions.append(f'{label}usage above 85%')
            elif peak > 70:
                score -= 5; deductions.append(f'{label}usage above 70%')
        else:
            if peak > 80:
                score -= 10; deductions.append(f'{label}peak above 80%')
            elif peak > 60:
                score -= 5; deductions.append(f'{label}peak above 60%')

    # Slow logs
    slow = inst_data.get('slow_logs') or {}
    slow_count = sum(s.get('count', 0) for s in (slow.get('top_count') or []))
    if slow_count > 1000:
        score -= 8; deductions.append('Too many slow logs (>1000 items)')
    elif slow_count > 100:
        score -= 3; deductions.append('Slow log count is high (>100 items)')

    # alerts (P1=critical weight=100, P2=warning weight=70)
    alerts = inst_data.get('alerts') or []
    critical_count = sum(1 for a in alerts if level_weight(a.get('level', '')) >= 100)
    high_count = sum(1 for a in alerts if level_weight(a.get('level', '')) >= 70)
    if critical_count > 0:
        score -= 10; deductions.append('P1 critical alerts present')
    elif high_count > 50:
        score -= 5; deductions.append('P2 Too many high-severity alerts (>50 items)')
    elif len(alerts) > 100:
        score -= 3; deductions.append('Too many alerts in total (>100 items)')

    # Version is not the latest
    attr = inst_data.get('attribute') or {}
    cur, latest = attr.get('current_kernel', ''), attr.get('latest_kernel', '')
    if cur and latest and cur != latest:
        score -= 3; deductions.append('Kernel version is not the latest')

    # Expiring soon (within 30 days)
    expire = attr.get('expire_time', '')
    if expire:
        try:
            et = datetime.strptime(expire[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            days_left = (et - datetime.now(timezone.utc)).days
            if 0 <= days_left <= 30:
                score -= 5; deductions.append(f'Instance {days_left} expiring in N days')
        except (ValueError, TypeError):
            pass

    # LockMode exception
    lock = (attr.get('lock_mode') or '').lower()
    if lock and lock != 'unlock':
        score -= 8; deductions.append(f'Instance is in {attr.get("lock_mode")} Status')

    return max(0, score), deductions


def score_status(score):
    """Health score → Colour tier"""
    if score >= 80:
        return '🟢', 'ok'
    elif score >= 60:
        return '🟡', 'warn'
    else:
        return '🔴', 'danger'


def aggregate_summary(all_instance_data, region_count):
    """Aggregate inspection data of all instances into a summary dict."""
    total = len(all_instance_data)
    
    # Health score distribution
    health_dist = {'ok': 0, 'warn': 0, 'danger': 0}
    for inst in all_instance_data:
        score = inst.get('health_score', 0)
        if score >= 80:
            health_dist['ok'] += 1
        elif score >= 60:
            health_dist['warn'] += 1
        else:
            health_dist['danger'] += 1
    
    # Global health score (average across all instances)
    global_score = round(sum(inst.get('health_score', 0) for inst in all_instance_data) / total) if total > 0 else 0
    
    # Health score ranking (lowest 20)
    sorted_by_score = sorted(all_instance_data, key=lambda x: x.get('health_score', 0))
    health_ranking = []
    for inst in sorted_by_score[:20]:
        health_ranking.append({
            'instance_id': inst.get('instance_id', ''),
            'region_id': inst.get('region_id', ''),
            'health_score': inst.get('health_score', 0),
            'category': inst.get('attribute', {}).get('category', ''),
            'instance_class': inst.get('attribute', {}).get('instance_class', ''),
            'deductions': inst.get('deductions', [])[:3],  # Take top 3 deductions
        })
    
    # Alert statistics
    alerts_ranking = []
    total_alerts = 0
    instances_with_alerts = 0
    alert_level_dist = {}
    for inst in all_instance_data:
        alerts = inst.get('alerts', [])
        if alerts:
            instances_with_alerts += 1
            total_alerts += len(alerts)
            for alert in alerts:
                level = alert.get('level', 'UNKNOWN')
                alert_level_dist[level] = alert_level_dist.get(level, 0) + 1
            alerts_ranking.append({
                'instance_id': inst.get('instance_id', ''),
                'region_id': inst.get('region_id', ''),
                'alerts': alerts,
            })
    alerts_ranking = sorted(alerts_ranking, key=lambda x: -len(x['alerts']))[:20]
    
    # Resource watermark TOP (simplified)
    resource_tops = {
        'cpu': [], 'memory': [], 'space': [], 'iops': [], 'connection': []
    }
    for inst in all_instance_data:
        metrics = inst.get('metrics', {})
        for key in resource_tops.keys():
            m = metrics.get(key, {}).get('cluster', {})
            if m.get('peak') is not None:
                resource_tops[key].append({
                    'instance_id': inst.get('instance_id', ''),
                    'region_id': inst.get('region_id', ''),
                    'avg': m.get('avg', 0),
                    'peak': m.get('peak', 0),
                })
    for key in resource_tops:
        resource_tops[key] = sorted(resource_tops[key], key=lambda x: -x['peak'])[:20]
    
    # Slow log TOP (slow log count within the inspection time window)
    slow_count_ranking = []
    
    for inst in all_instance_data:
        metrics = inst.get('metrics', {})
        slow_logs = metrics.get('slow_logs', [])
        if slow_logs:
            slow_count_ranking.append({
                'instance_id': inst.get('instance_id', ''),
                'region_id': inst.get('region_id', ''),
                'slow_log_count': len(slow_logs),
            })
    
    slow_count_ranking = sorted(slow_count_ranking, key=lambda x: -x['slow_log_count'])[:20]
    
    # Version & expiration
    upgradable = []
    expiring_30d = []
    expiring_90d = []
    
    for inst in all_instance_data:
        attr = inst.get('attribute', {})
        cur, latest = attr.get('current_kernel', ''), attr.get('latest_kernel', '')
        if cur and latest and cur != latest:
            upgradable.append({
                'instance_id': inst.get('instance_id', ''),
                'region_id': inst.get('region_id', ''),
                'current': cur,
                'latest': latest,
            })
        
        expire = attr.get('expire_time', '')
        if expire:
            try:
                et = datetime.strptime(expire[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                days_left = (et - datetime.now(timezone.utc)).days
                if 0 <= days_left <= 30:
                    expiring_30d.append({
                        'instance_id': inst.get('instance_id', ''),
                        'region_id': inst.get('region_id', ''),
                        'expire_date': expire[:10],
                        'days_left': days_left,
                    })
                elif 30 < days_left <= 90:
                    expiring_90d.append({
                        'instance_id': inst.get('instance_id', ''),
                        'region_id': inst.get('region_id', ''),
                        'expire_date': expire[:10],
                        'days_left': days_left,
                    })
            except (ValueError, TypeError):
                pass
    
    # Optimization suggestions (simplified)
    suggestions = {}
    for inst in all_instance_data:
        for deduction in inst.get('deductions', []):
            if deduction not in suggestions:
                suggestions[deduction] = []
            suggestions[deduction].append(inst.get('instance_id', ''))
    
    return {
        'total_instances': total,
        'region_count': region_count,
        'global_score': global_score,
        'health_dist': health_dist,
        'health_ranking': health_ranking,
        'alerts_ranking': alerts_ranking,
        'total_alerts': total_alerts,
        'instances_with_alerts': instances_with_alerts,
        'alert_level_dist': alert_level_dist,
        'resource_tops': resource_tops,
        'slow_count_ranking': slow_count_ranking,
        'upgradable': upgradable,
        'expiring_30d': expiring_30d,
        'expiring_90d': expiring_90d,
        'suggestions': suggestions,
    }


# CSSStylesheet (copied from the MySQL skill to keep formatting, fonts and table sizes identical)
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
.label-cell { background: #f5f7fa; color: #909399; font-weight: 600; width: 120px; white-space: nowrap; }
/* i18n: bilingual spans + language toggle button */
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
@media (max-width:768px) { body { padding:1rem; } .info-grid,.chart-grid { grid-template-columns:1fr; } }
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
            btn.textContent = cur === 'en' ? 'label' : 'EN';
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


def render_single_instance_html(inst_data, inspect_time, range_str):
    """Generate the detailed HTML inspection report for a single instance (consistent with MySQL skill style)."""
    instance_id = inst_data['instance_id']
    region = inst_data['region_id']
    attr = inst_data.get('attribute') or {}
    metrics = inst_data.get('metrics') or {}
    alerts = inst_data.get('alerts') or []
    score = inst_data.get('health_score', 0)
    score_emoji, score_cls = score_status(score)
    
    # Slow logs
    slow_logs = metrics.get('slow_logs') or []
    
    # Basics
    storage_str = format_gb(attr.get('storage', 0))
    expire_str = (attr.get('expire_time') or '')[:10] or 'N/A'
    create_str = (attr.get('creation_time') or '')[:10] or 'N/A'
    cur_kernel = attr.get('current_kernel') or 'N/A'
    latest_kernel = attr.get('latest_kernel') or 'N/A'
    kernel_status = '✅ ' + _i18n('Up to date', 'already latest') if cur_kernel == latest_kernel and cur_kernel != 'N/A' else ' ' + _i18n('Upgrade available', 'upgradable')
    
    # Basics 3-column table
    basic_info_html = f"""
    <table>
        <tr><td class="label-cell">{_i18n('Instance ID', 'Instance ID')}</td><td>{_html_escape(instance_id)}</td>
            <td class="label-cell">Region</td><td>{_html_escape(region)}</td>
            <td class="label-cell">{_i18n('Engine', 'Engine')}</td><td>PostgreSQL {_html_escape(attr.get('engine_version', ''))}</td></tr>
        <tr><td class="label-cell">{_i18n('Category', 'Category')}</td><td>{_html_escape(attr.get('category', '') or 'N/A')}</td>
            <td class="label-cell">{_i18n('Class', 'Spec')}</td><td>{_html_escape(attr.get('instance_class', ''))}</td>
            <td class="label-cell">{_i18n('Storage Type', 'Storage type')}</td><td>{_html_escape(attr.get('storage_type', ''))}</td></tr>
        <tr><td class="label-cell">{_i18n('Storage', 'Storage capacity')}</td><td>{storage_str}</td>
            <td class="label-cell">{_i18n('Max Connections', 'Max connections')}</td><td>{attr.get('max_connections', 0)}</td>
            <td class="label-cell">{_i18n('Max IOPS', 'Max IOPS')}</td><td>{attr.get('max_iops', 0)}</td></tr>
        <tr><td class="label-cell">{_i18n('Max IO Bandwidth', 'Max IO bandwidth')}</td><td>{attr.get('max_iombps', 0)} MB/s</td>
            <td class="label-cell">{_i18n('Primary Zone', 'Primary AZ')}</td><td>{_html_escape(attr.get('master_zone', '') or 'N/A')}</td>
            <td class="label-cell">{_i18n('Secondary Zones', 'Standby AZ')}</td><td>{_html_escape(','.join(attr.get('slave_zones', [])) or 'N/A')}</td></tr>
        <tr><td class="label-cell">VPC ID</td><td>{_html_escape(attr.get('vpc_id', '') or 'N/A')}</td>
            <td class="label-cell">VSwitch</td><td>{_html_escape(attr.get('vswitch_id', '') or 'N/A')}</td>
            <td class="label-cell">{_i18n('Status', 'Instance status')}</td><td>{_html_escape(attr.get('status', ''))}</td></tr>
        <tr><td class="label-cell">{_i18n('Pay Type', 'Charge type')}</td><td>{_html_escape(attr.get('pay_type', ''))}</td>
            <td class="label-cell">{_i18n('Lock Mode', 'lock state')}</td><td>{_html_escape(attr.get('lock_mode', '') or 'Unlock')}</td>
            <td class="label-cell">{_i18n('Maintain Time', 'Maintenance window')}</td><td>{_html_escape(attr.get('maintain_time', '') or 'N/A')}</td></tr>
        <tr><td class="label-cell">{_i18n('Creation Time', 'Creation time')}</td><td>{create_str}</td>
            <td class="label-cell">{_i18n('Expire Time', 'Expiration time')}</td><td>{expire_str}</td>
            <td class="label-cell">{_i18n('Current Kernel', 'Current kernel')}</td><td>{_html_escape(cur_kernel)}</td></tr>
        <tr><td class="label-cell">{_i18n('Latest Kernel', 'Latest kernel')}</td><td>{_html_escape(latest_kernel)}</td>
            <td class="label-cell">Version status</td><td>{kernel_status}</td>
            <td></td><td></td><td></td><td></td></tr>
    </table>
    """
    
    # Resource utilization table (add"Object" cols)
    res_rows = []
    chart_data = {}
    for mkey in ['cpu', 'memory', 'space', 'iops', 'connection']:
        m = metrics.get(mkey, {})
        label = _label_i18n(mkey)
        cluster_m = m.get('cluster') or {}
        avg = cluster_m.get('avg', 0) or 0
        peak = cluster_m.get('peak', 0) or 0
        cls = status_class(peak, mkey)
        icon = status_icon(peak, mkey)
        # Add"Object"col
        res_rows.append(
            f'<tr><td>{label}</td><td>{_i18n("Instance Overall", "Instance overall")}</td><td>{avg:.2f}%</td><td class="{cls}">{peak:.2f}%</td><td>{icon}</td></tr>'
        )
        # Time-series chart data - from cluster.timeseries
        series = cluster_m.get('timeseries') or []
        if series:
            chart_data[mkey] = series
    
    res_table = (
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Metric", "Metric")}</th><th>{_i18n("Object", "Object")}</th><th>{_i18n("Average", "Average")}</th><th>{_i18n("Peak", "Peak")}</th><th>{_i18n("Status", "Status")}</th></tr>'
        + ''.join(res_rows) + '</table></div>'
    )
    
    # PostgreSQL Specific performance sub-metric display
    rds_perf = metrics.get('rds_performance') or {}
    sub_metrics_html = ''
    for key in RDS_PERFORMANCE_METRICS:
        sub_data = rds_perf.get(key)
        if not sub_data:
            continue
        
        metric_label = RDS_METRIC_LABELS.get(key, {}).get('en', key)
        metric_label_zh = RDS_METRIC_LABELS.get(key, {}).get('zh', key)
        
        sub_rows = []
        for sub_key, sub_val in sub_data.items():
            sub_label = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('en', sub_key)
            sub_label_zh = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('zh', sub_key)
            avg_val = sub_val.get('avg', 0)
            peak_val = sub_val.get('peak', 0)
            sub_rows.append(
                f'<tr><td>{_i18n(sub_label, sub_label_zh)}</td><td>{avg_val:.2f}</td><td>{peak_val:.2f}</td></tr>'
            )
        
        if sub_rows:
            sub_metrics_html += f'''
            <div style="margin-top:1rem">
                <h4 style="font-size:0.95rem;color:#1e40af;margin-bottom:0.5rem">{_i18n(metric_label, metric_label_zh)}</h4>
                <div class="table-scroll"><table>
                    <tr><th>{_i18n("Sub-Metric", "Sub-metric")}</th><th>{_i18n("Average", "Average")}</th><th>{_i18n("Peak", "Peak")}</th></tr>
                    {''.join(sub_rows)}
                </table></div>
            </div>
            '''
    
    # Prepare chart data for RDS performance sub-metrics (multi-line trends)
    rds_perf = metrics.get('rds_performance') or {}
    rds_perf_chart_data = {}
    
    # Chart 1: PolarDBLocalDiskUsage - Data disk per-directory usage (MB)
    local_disk_data = rds_perf.get('PolarDBLocalDiskUsage')
    if local_disk_data:
        rds_perf_chart_data['localDisk'] = []
        for sub_key in ['mean_local_pg_wal_dir_size', 'mean_local_base_dir_size', 'mean_local_pg_log_dir_size']:
            if sub_key in local_disk_data:
                sub_label = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('en', sub_key)
                timeseries = local_disk_data[sub_key].get('timeseries', [])
                rds_perf_chart_data['localDisk'].append({
                    'name': sub_label,
                    'data': timeseries
                })
    
    # Chart 2: PolarDBConnections - Connection details
    conn_data = rds_perf.get('PolarDBConnections')
    if conn_data:
        rds_perf_chart_data['connections'] = []
        for sub_key in ['mean_active_session', 'mean_idle_connection', 'mean_total_session', 'mean_waiting_connection']:
            if sub_key in conn_data:
                sub_label = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('en', sub_key)
                timeseries = conn_data[sub_key].get('timeseries', [])
                rds_perf_chart_data['connections'].append({
                    'name': sub_label,
                    'data': timeseries
                })
    
    # Chart 3: PolarDBReplication - Replication delay (Bytes)
    repl_data = rds_perf.get('PolarDBReplication')
    if repl_data:
        rds_perf_chart_data['replication'] = []
        for sub_key in ['mean_replay_latency_in_mb', 'mean_send_latency_in_mb', 'mean_logical_rep_latency_in_mb']:
            if sub_key in repl_data:
                sub_label = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('en', sub_key)
                timeseries = repl_data[sub_key].get('timeseries', [])
                rds_perf_chart_data['replication'].append({
                    'name': sub_label,
                    'data': timeseries
                })
    
    # Chart 4: PolarDBQPSTPS - QPS/TPS details (/s)
    qps_data = rds_perf.get('PolarDBQPSTPS')
    if qps_data:
        rds_perf_chart_data['qpsTps'] = []
        for sub_key in ['mean_commits_delta', 'mean_rollbacks_delta', 'mean_deadlocks_delta', 'mean_tps']:
            if sub_key in qps_data:
                sub_label = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('en', sub_key)
                timeseries = qps_data[sub_key].get('timeseries', [])
                rds_perf_chart_data['qpsTps'].append({
                    'name': sub_label,
                    'data': timeseries
                })
    
    # Chart 5: PolarDBLongTransaction - Long transactions
    long_tx_data = rds_perf.get('PolarDBLongTransaction')
    if long_tx_data:
        rds_perf_chart_data['longTx'] = []
        for sub_key in ['mean_one_second_transactions', 'mean_three_seconds_transactions']:
            if sub_key in long_tx_data:
                sub_label = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('en', sub_key)
                timeseries = long_tx_data[sub_key].get('timeseries', [])
                rds_perf_chart_data['longTx'].append({
                    'name': sub_label,
                    'data': timeseries
                })
    
    # Chart 6: PolarDBSwellTime - Bloat hotspots
    swell_data = rds_perf.get('PolarDBSwellTime')
    if swell_data:
        rds_perf_chart_data['swell'] = []
        for sub_key, sub_val in swell_data.items():
            sub_label = RDS_SUB_METRIC_LABELS.get(sub_key, {}).get('en', sub_key)
            timeseries = sub_val.get('timeseries', [])
            rds_perf_chart_data['swell'].append({
                'name': sub_label,
                'data': timeseries
            })
    
    # Slow log TOP 20 table
    slow_log_rows = []
    for i, log in enumerate(slow_logs, 1):
        exec_time = log.get('execution_time', 0)
        sql_text = log.get('sql', '')
        # Truncate over-long SQL
        if len(sql_text) > 200:
            sql_text = sql_text[:200] + '...'
        slow_log_rows.append(
            f'<tr><td>{i}</td>'
            f'<td>{exec_time:.3f}s</td>'
            f'<td>{_html_escape(log.get("execution_start_time", ""))}</td>'
            f'<td>{_html_escape(log.get("database_name", ""))}</td>'
            f'<td class="sql-cell"><code>{_html_escape(sql_text)}</code></td></tr>'
        )
    slow_log_table = (
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Rank", "Rank")}</th>'
        f'<th>{_i18n("Exec Time", "Execution time")}</th>'
        f'<th>{_i18n("Start Time", "Start time")}</th>'
        f'<th>{_i18n("Database", "Database")}</th>'
        f'<th>{_i18n("SQL Statement", "SQL Statement")}</th></tr>'
        + ''.join(slow_log_rows) + '</table></div>'
        if slow_log_rows else f'<p class="ok-msg">✅ {_i18n("No slow logs in", "No slow logs in")} {range_str}</p>'
    )
    
    # Alert list (most recent 10)
    alert_rows = []
    for a in alerts[:10]:  # most recent 10
        level_cls = 'danger' if alert_level_weight(a.get('level', '')) >= 100 else ('warn' if alert_level_weight(a.get('level', '')) >= 70 else 'ok')
        alert_rows.append(
            f'<tr><td class="{level_cls}">{_html_escape(a.get("level", ""))}</td>'
            f'<td>{_html_escape(a.get("time", ""))}</td>'
            f'<td>{_html_escape(a.get("rule_name", ""))}</td>'
            f'<td>{_html_escape(a.get("metric_name", ""))}</td>'
            f'<td>{_html_escape(a.get("cur_value", ""))}</td></tr>'
        )
    alert_table = (
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Level", "Severity")}</th><th>{_i18n("Time", "Time")}</th><th>{_i18n("Rule", "Rule")}</th><th>{_i18n("Metric", "Metric")}</th><th>{_i18n("Current Value", "Current value")}</th></tr>'
        + ''.join(alert_rows) + '</table></div>'
        if alert_rows else f'<p class="ok-msg">✅ {_i18n("No recent alerts", "No recent alerts")}</p>'
    )
    
    # Deductions
    deductions = inst_data.get('deductions') or []
    deductions_html = (
        '<ul>' + ''.join(f'<li>{_html_escape(d)}</li>' for d in deductions) + '</ul>'
        if deductions else '<p class="ok-msg">✅ No deductions</p>'
    )
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RDS PostgreSQL {_i18n('Inspection Report', 'Inspection report')} - {instance_id}</title>
<style>
{_HTML_CSS}
.label-cell {{ background: #f5f7fa; color: #909399; font-weight: 600; width: 120px; white-space: nowrap; }}
.sql-cell {{ max-width: 500px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.sql-cell code {{ font-family: 'Courier New', monospace; font-size: 0.85rem; color: #1e40af; background: #f0f4ff; padding: 2px 6px; border-radius: 3px; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <button class="lang-toggle">EN</button>
        <h1>📊 {_i18n('RDS PostgreSQL Inspection Report', 'RDS PostgreSQL Inspection report')}</h1>
        <div class="meta">
            <span>{_i18n('Instance', 'Instance')}: <b>{instance_id}</b></span>
            <span>Region: {region}</span>
            <span>{_i18n('Inspection Time', 'Inspection time')}: {inspect_time}</span>
            <span>{_i18n('Time Range', 'Time range')}: {range_str}</span>
            <span>{_i18n('Health Score', 'Health score')}: <b>{score}</b>/100</span>
        </div>
    </div>
    
    <div class="toc">
        <a href="#sec-1">{_i18n('1. Instance Basics', '1. 实例基础信息')}</a>
        <a href="#sec-2">{_i18n('2. Resource Utilization', '2. 资源利用率')}</a>
        <a href="#sec-3">{_i18n('3. Slow Log TOP 20', '3. 慢日志 TOP 20')}</a>
        <a href="#sec-4">{_i18n('4. Recent 10 Alerts', '4. 告警历史')}</a>
        <a href="#sec-5">{_i18n('5. Performance Metrics Sub-metrics', '5. 性能指标子指标')}</a>
    </div>
    
    <div class="section" id="sec-1">
        <h2>{_i18n('1. Instance Basics', '1. 实例基础信息')}</h2>
        {basic_info_html}
    </div>
    
    <div class="section" id="sec-2">
        <h2>{_i18n('2. Resource Utilization', '2. 资源利用率')} ({range_str})</h2>
        {res_table}
    </div>
    
    <div class="section" id="sec-3">
        <h2>{_i18n('3. Slow Log TOP 20', '3. 慢日志 TOP 20')}</h2>
        <p>{_i18n('Top 20 slowest queries in', 'Top 20 slowest queries in')} {range_str}</p>
        {slow_log_table}
    </div>
    
    <div class="section" id="sec-4">
        <h2>{_i18n('4. Recent 10 Alerts', '4. 告警历史')}</h2>
        <p>{_i18n('Total', 'Total')} <b>{len(alerts)}</b> {_i18n('alerts, showing latest 10', 'alerts; showing the most recent 10')}</p>
        {alert_table}
    </div>
    
    <div class="section" id="sec-5">
        <h2>{_i18n('5. Performance Metrics Sub-metrics', '5. 性能指标子指标')} ({range_str})</h2>
        <p>{_i18n('PostgreSQL-specific performance sub-metrics: long transactions, table bloat, QPS/TPS, replication delay, etc.', 'PostgreSQL-specific performance sub-metrics: long transactions, table bloat, QPS/TPS, replication delay, etc.')}</p>
        <h3 style="font-size:1.05rem;color:#1e40af;margin:1.5rem 0 0.8rem 0">{_i18n('Performance Metrics Sub-metrics Trends', 'Performance sub-metric trends')}</h3>
        <div class="chart-grid" style="margin-top:10px">
            <div class="chart-card"><h4>{_i18n('Local Disk Usage by Directory', 'Data disk per-directory usage')}</h4><div id="chart-local-disk" class="echart"></div></div>
            <div class="chart-card"><h4>{_i18n('Connection Details', 'Connection details')}</h4><div id="chart-connections" class="echart"></div></div>
            <div class="chart-card"><h4>{_i18n('Replication Delay', 'Replication delay')}</h4><div id="chart-replication" class="echart"></div></div>
            <div class="chart-card"><h4>{_i18n('QPS/TPS Details', 'QPS/TPS Details')}</h4><div id="chart-qps-tps" class="echart"></div></div>
            <div class="chart-card"><h4>{_i18n('Long Transactions', 'Long transactions')}</h4><div id="chart-long-tx" class="echart"></div></div>
            <div class="chart-card"><h4>{_i18n('Swell Time', 'Bloat hotspots')}</h4><div id="chart-swell" class="echart"></div></div>
        </div>
    </div>
    
    <div class="footer">RDS PostgreSQL {_i18n('Inspection Report', 'Inspection report')} · {inspect_time}</div>
</div>

<!-- ECharts -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<script>
{_LANG_TOGGLE_JS}

// Chart data
const chartData = {json.dumps(chart_data, ensure_ascii=False)};

// RDS Performance sub-metrics data for multi-line charts
const rdsPerfData = {json.dumps(rds_perf_chart_data, ensure_ascii=False)};

// Render single line chart function
function renderChart(containerId, data, title, color) {{
    const chart = echarts.init(document.getElementById(containerId));
    const option = {{
        tooltip: {{
            trigger: 'axis',
            axisPointer: {{ type: 'cross' }}
        }},
        grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
        xAxis: {{
            type: 'category',
            data: data.map(d => d[0]),
            axisLabel: {{ rotate: 45, fontSize: 10 }}
        }},
        yAxis: {{
            type: 'value',
            max: 100,
            axisLabel: {{ formatter: '{{value}}%' }}
        }},
        series: [{{
            name: title,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: {{ width: 2, color: color }},
            areaStyle: {{
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    {{ offset: 0, color: color + '40' }},
                    {{ offset: 1, color: color + '10' }}
                ])
            }},
            data: data.map(d => d[1])
        }}]
    }};
    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}}

// Render multi-line chart function for sub-metrics
function renderMultiLineChart(containerId, seriesData, unit) {{
    const chart = echarts.init(document.getElementById(containerId));
    if (!seriesData || seriesData.length === 0) return;
    
    // Get all timestamps from first series
    const timestamps = seriesData[0].data.map(d => d[0]);
    
    const series = seriesData.map(s => ({{
        name: s.name,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: s.data.map(d => d[1])
    }}));
    
    const option = {{
        tooltip: {{
            trigger: 'axis',
            axisPointer: {{ type: 'cross' }}
        }},
        legend: {{
            data: seriesData.map(s => s.name),
            bottom: 0,
            textStyle: {{ fontSize: 11 }}
        }},
        grid: {{ left: '3%', right: '4%', bottom: '15%', containLabel: true }},
        xAxis: {{
            type: 'category',
            data: timestamps,
            axisLabel: {{ rotate: 45, fontSize: 10 }}
        }},
        yAxis: {{
            type: 'value',
            axisLabel: {{ formatter: '{{value}} ' + unit }}
        }},
        series: series
    }};
    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}}

// Render RDS performance sub-metrics charts
if (rdsPerfData.localDisk) renderMultiLineChart('chart-local-disk', rdsPerfData.localDisk, 'MB');
if (rdsPerfData.connections) renderMultiLineChart('chart-connections', rdsPerfData.connections, '');
if (rdsPerfData.replication) renderMultiLineChart('chart-replication', rdsPerfData.replication, 'Byte');
if (rdsPerfData.qpsTps) renderMultiLineChart('chart-qps-tps', rdsPerfData.qpsTps, '/s');
if (rdsPerfData.longTx) renderMultiLineChart('chart-long-tx', rdsPerfData.longTx, '');
if (rdsPerfData.swell) renderMultiLineChart('chart-swell', rdsPerfData.swell, '');
</script>

</body>
</html>"""
    
    return html


def render_summary_html(summary, output_dir, inspect_time, range_str):
    """Render the summary HTML report (full edition - 9 sections)."""
    total = summary['total_instances']
    global_score = summary['global_score']
    health_dist = summary['health_dist']
    region_count = summary['region_count']
    
    # Instance ID link generator
    def link(instance_id):
        return f'<a href="instances/{instance_id}.html" target="_blank">{instance_id}</a>'
    
    # ─── 1. Inspection Overview ───
    region_rows = ''.join(
        f'<tr><td>{_html_escape(r)}</td><td>{c}</td></tr>'
        for r, c in sorted(region_count.items(), key=lambda x: -x[1])
    )
    
    overview_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">{_i18n('Total Instances', 'Total instances inspected')}</div>
            <div class="value">{total}</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Regions Covered', 'Covered regions')}</div>
            <div class="value">{len(region_count)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Global Health Score', 'Global health')}</div>
            <div class="value">{global_score}</div>
            <div class="sub">/100</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Health Distribution', 'Health distribution')}</div>
            <div class="value">🟢{health_dist.get('ok',0)} 🟡{health_dist.get('warn',0)} 🔴{health_dist.get('danger',0)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Alerting Instances', 'Alerted instances')}</div>
            <div class="value">{summary['instances_with_alerts']}</div>
            <div class="sub">{_i18n('Alerts', 'Alerts')} {summary['total_alerts']} {_i18n('items', 'items')}</div></div>
    </div>
    <div class="chart-grid">
        <div class="chart-card"><h4>{_i18n('Health Status Distribution', 'Health status distribution')}</h4><div id="chart-health" class="echart" style="height:240px"></div></div>
        <div class="chart-card"><h4>{_i18n('Instances per Region', 'Per-region instance count')}</h4><div id="chart-regions" class="echart" style="height:240px"></div></div>
    </div>
    <h3>{_i18n('Instances per Region Detail', 'Per-region instance breakdown')}</h3>
    <div class="table-scroll"><table><tr><th>Region</th><th>{_i18n('Count', 'Instance count')}</th></tr>{region_rows}</table></div>
    """
    
    # ─── 2. Health Score Ranking ───
    hr_rows = []
    for i, d in enumerate(summary['health_ranking'], 1):
        score = d['health_score']
        emoji, cls = score_status(score)
        deds = '；'.join(d['deductions'][:3]) if d['deductions'] else ''
        hr_rows.append(
            f'<tr><td>{i}</td><td>{link(d["instance_id"])}</td>'
            f'<td>{_html_escape(d["region_id"])}</td>'
            f'<td class="{cls}">{emoji} {score}</td>'
            f'<td>{_html_escape(d.get("category","")) or "N/A"}</td>'
            f'<td>{_html_escape(d.get("instance_class",""))}</td>'
            f'<td style="font-size:0.78rem;color:var(--muted)">{_html_escape(deds)}</td></tr>'
        )
    health_ranking_html = (
        f'<p>{_i18n("Lower health score means more issues, investigate first. Click instance ID for details.", "Lower scores indicate more issues; investigate first. Click an instance ID for the detailed report.")}</p>'
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Instance ID", "Instance ID")}</th><th>Region</th><th>{_i18n("Health Score", "Health score")}</th><th>{_i18n("Category", "Category")}</th><th>{_i18n("Class", "Spec")}</th><th>{_i18n("Top Deductions", "Top deductions")}</th></tr>'
        + ''.join(hr_rows) + '</table></div>'
    )
    
    # ─── 3. Alert Statistics ───
    alert_rows = []
    for i, d in enumerate(summary['alerts_ranking'], 1):
        alerts = d.get('alerts') or []
        max_lvl = max((a.get('level', '') for a in alerts), key=level_weight, default='-')
        cnt = len(alerts)
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
        f'<tr><th>#</th><th>{_i18n("Instance ID", "Instance ID")}</th><th>Region</th><th>{_i18n("Alert Count", "Alert count")}</th><th>{_i18n("Highest Level", "Highest severity")}</th><th>{_i18n("P1/P2 High Severity", "P1/P2 High severity")}</th></tr>'
        + ''.join(alert_rows) + '</table></div>'
        if alert_rows else f'<p class="ok-msg">✅ {_i18n("All instances have no recent alerts", "All instances have no recent alerts")}</p>'
    )
    alert_section_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">{_i18n('Alerting Instances', 'Alerted instance count')}</div><div class="value">{summary['instances_with_alerts']}</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Total Alerts', 'Total alert count')}</div><div class="value">{summary['total_alerts']}</div></div>
    </div>
    <div class="chart-card" style="margin-bottom:1rem"><h4>{_i18n('Alert Level Distribution', 'Alert severity distribution')}</h4>
        <div id="chart-alert-levels" class="echart" style="height:220px"></div></div>
    <h3>{_i18n('Top 20 Instances by Alert Count', 'Top 20 instances with most alerts')}</h3>
    {alert_table}
    """
    
    # ─── 4. Resource Watermark TOP ───
    def res_top_table(key, label_en, label_zh):
        items = summary['resource_tops'].get(key) or []
        if not items:
            return f'<p class="ok-msg">{_i18n("No " + label_en + " data", "None " + label_zh + " Data")}</p>'
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
            f'<tr><th>#</th><th>{_i18n("Instance ID", "Instance ID")}</th><th>Region</th><th>{_i18n("Average", "Average")}</th><th>{_i18n("Peak", "Peak")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )
    
    resource_section_html = f"""
    <h3>{_i18n('CPU Peak TOP 20', 'CPU Peak TOP 20')}</h3> {res_top_table('cpu', 'CPU', 'CPU')}
    <h3>{_i18n('Memory Peak TOP 20', 'Memory peak TOP 20')}</h3> {res_top_table('memory', 'Memory', 'Memory')}
    <h3>{_i18n('Disk Usage TOP 20', 'Disk usage TOP 20')}</h3> {res_top_table('space', 'Disk', 'Disk')}
    <h3>{_i18n('IOPS Peak TOP 20', 'IOPS Peak TOP 20')}</h3> {res_top_table('iops', 'IOPS', 'IOPS')}
    <h3>{_i18n('Connection Usage TOP 20', 'Connection usage TOP 20')}</h3> {res_top_table('connection', 'Connection', 'Connections')}
    """
    
    # ─── 5. Slow Log TOP (slow log count within the inspection time window) ──
    slow_log_rows = []
    for i, it in enumerate(summary.get('slow_count_ranking', []), 1):
        slow_log_rows.append(
            f'<tr><td>{i}</td><td>{link(it["instance_id"])}</td>'
            f'<td>{it["slow_log_count"]}</td></tr>'
        )
    slow_log_section_html = (
        '<div class="table-scroll"><table>'
        f'<tr><th>#</th><th>{_i18n("Instance ID", "Instance ID")}</th><th>{_i18n("Slow Log Count", "Slow log count")}</th></tr>'
        + ''.join(slow_log_rows) + '</table></div>'
        if slow_log_rows else f'<p class="ok-msg">✅ {_i18n("No slow logs across all instances in", "No slow logs across all instances in")} {range_str}</p>'
    )
    
    # ─── 5. Version & Expiration ───
    upg_rows = []
    for it in summary['upgradable']:
        upg_rows.append(
            f'<tr><td>{link(it["instance_id"])}</td><td>{_html_escape(it["region_id"])}</td>'
            f'<td>{_html_escape(it["current"])}</td><td>{_html_escape(it["latest"])}</td></tr>'
        )
    upg_html = (
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Instance ID", "Instance ID")}</th><th>Region</th><th>{_i18n("Current Kernel", "Current kernel")}</th><th>{_i18n("Latest Kernel", "Latest kernel")}</th></tr>'
        + ''.join(upg_rows) + '</table></div>'
        if upg_rows else f'<p class="ok-msg">✅ {_i18n("All instances have the latest kernel version", "All instances are on the latest kernel version")}</p>'
    )
    
    def expire_table(records, title_en, title_zh):
        if not records:
            return f'<p class="ok-msg">✅ {_i18n("No instances " + title_en, "No " + title_en + " instances")}</p>'
        rows = []
        for it in records:
            cls = 'danger' if it['days_left'] <= 30 else 'warn'
            rows.append(
                f'<tr><td>{link(it["instance_id"])}</td><td>{_html_escape(it["region_id"])}</td>'
                f'<td>{_html_escape(it["expire_date"])}</td>'
                f'<td class="{cls}">{it["days_left"]} {_i18n("days", "day(s)")}</td></tr>'
            )
        return (
            '<div class="table-scroll"><table>'
            f'<tr><th>{_i18n("Instance ID", "Instance ID")}</th><th>Region</th><th>{_i18n("Expire Date", "Expiration date")}</th><th>{_i18n("Days Remaining", "Days remaining")}</th></tr>'
            + ''.join(rows) + '</table></div>'
        )
    
    version_section_html = f"""
    <h3>{_i18n('Instances with Kernel Upgrade Available', 'Instances with upgradable kernel version')}（{_i18n('Total', 'Total')} {len(summary['upgradable'])} {_i18n('instances', '')}）</h3>
    {upg_html}
    <h3>{_i18n('Instances Expiring within 30 Days', '30 Instances expiring within N days')}（{_i18n('Total', 'Total')} {len(summary['expiring_30d'])} {_i18n('instances', '')}）</h3>
    {expire_table(summary['expiring_30d'], 'expiring within 30 days', '30 expiring within')}
    <h3>{_i18n('Instances Expiring within 90 Days', '90 Instances expiring within N days')}（{_i18n('Total', 'Total')} {len(summary['expiring_90d'])} {_i18n('instances', '')}）</h3>
    {expire_table(summary['expiring_90d'], 'expiring within 90 days', '90 expiring within')}
    """
    
    # ── 7. Inspection Conclusion ───
    conclusion_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">{_i18n('Global Health Score', 'Global health')}</div><div class="value">{global_score}</div><div class="sub">/100</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Healthy Instances', 'Healthy instances')}</div><div class="value ok">{health_dist.get('ok', 0)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Instances Needing Attention', 'Instances to watch')}</div><div class="value warn">{health_dist.get('warn', 0)}</div></div>
        <div class="kpi-card"><div class="label">{_i18n('Critical Instances', 'Critical instances')}</div><div class="value danger">{health_dist.get('danger', 0)}</div></div>
    </div>
    """
    
    # ─── 8. Optimization Suggestions ───
    sug_rows = []
    sorted_suggestions = sorted(summary['suggestions'].items(), key=lambda x: -len(x[1]))
    for desc, ids in sorted_suggestions:
        affected_html = ', '.join(link(iid) for iid in ids[:10])
        more = f'... {_i18n("Total", "Total")} {len(ids)} {_i18n("instances", "")}' if len(ids) > 10 else f'{_i18n("Total", "Total")} {len(ids)} {_i18n("instances", "")}'
        sug_rows.append(
            f'<tr><td>{_html_escape(desc)}</td><td>{len(ids)}</td>'
            f'<td>{affected_html}<br/><span style="color:var(--muted);font-size:0.78rem">{more}</span></td></tr>'
        )
    suggestions_html = (
        '<div class="table-scroll"><table>'
        f'<tr><th>{_i18n("Issue Description", "Issue description")}</th><th>{_i18n("Affected Instances", "Affected instance count")}</th><th>{_i18n("Affected Instances", "Affected instances")}</th></tr>'
        + ''.join(sug_rows) + '</table></div>'
        if sug_rows else f'<p class="ok-msg">✅ {_i18n("No obvious issues found during inspection", "No obvious issues detected")}</p>'
    )
    
    # Chart JS data
    health_dist_js = json.dumps([
        {'value': health_dist.get('ok', 0), 'name': 'Healthy', 'itemStyle': {'color': '#10b981'}},
        {'value': health_dist.get('warn', 0), 'name': 'Warning', 'itemStyle': {'color': '#f59e0b'}},
        {'value': health_dist.get('danger', 0), 'name': 'Critical', 'itemStyle': {'color': '#ef4444'}},
    ], ensure_ascii=False)
    region_dist_js = json.dumps([
        {'value': c, 'name': r} for r, c in sorted(region_count.items(), key=lambda x: -x[1])
    ])
    alert_levels_js = json.dumps(sorted(
        [{'name': lvl, 'value': cnt} for lvl, cnt in summary['alert_level_dist'].items()],
        key=lambda x: -level_weight(x['name'])
    ))
    
    # Final composition (8 sections, identical to the MySQL skill)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RDS PostgreSQL {_i18n('Inspection Summary', 'Inspection summary')}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>{_HTML_CSS}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <button class="lang-toggle">EN</button>
        <h1>📊 {_i18n('RDS PostgreSQL Inspection Summary', 'RDS PostgreSQL Inspection summary report')}</h1>
        <div class="meta">
            <span>{_i18n('Inspection Time', 'Inspection time')}: {inspect_time}</span>
            <span>{_i18n('Time Range', 'Time range')}: {range_str}</span>
            <span>{_i18n('Total Instances', 'Total instance count')}: {total}</span>
            <span>{_i18n('Global Health Score', 'Global health')}: <b>{global_score}/100</b></span>
        </div>
    </div>
    <div class="toc">
        <a href="#sec-1">{_i18n('1. Overview', '1. 巡检概览')}</a>
        <a href="#sec-2">{_i18n('2. Health Ranking', '2. 健康评分排名')}</a>
        <a href="#sec-3">{_i18n('3. Alert Statistics', '3. 告警实例统计')}</a>
        <a href="#sec-4">{_i18n('4. Resource TOP', '4. 资源利用率 Top')}</a>
        <a href="#sec-5">{_i18n('5. Slow Log TOP', '5. 慢日志 Top')}</a>
        <a href="#sec-6">{_i18n('6. Version & Expiry', '6. 版本与到期')}</a>
        <a href="#sec-7">{_i18n('7. Conclusion', '7. 巡检结论')}</a>
        <a href="#sec-8">{_i18n('8. Suggestions', '8. 优化建议')}</a>
    </div>

    <div class="section" id="sec-1"><h2>{_i18n('1. Inspection Overview', '1. 巡检概览')}</h2>{overview_html}</div>
    <div class="section" id="sec-2"><h2>{_i18n('2. Health Score Ranking (Least Healthy TOP 20)', '2. 健康评分排名（最低 TOP 20）')}</h2>{health_ranking_html}</div>
    <div class="section" id="sec-3"><h2>{_i18n('3. Alerting Instance Statistics', '3. 告警实例统计')}</h2>{alert_section_html}</div>
    <div class="section" id="sec-4"><h2>{_i18n('4. Resource Utilization TOP Lists', '4. 资源利用率 Top')}</h2>{resource_section_html}</div>
    <div class="section" id="sec-5"><h2>{_i18n('5. Slow Log TOP Lists', '5. 慢日志 Top')}</h2><p>{_i18n('Slow log count per instance in', '各实例慢日志数量统计 ·')} {range_str}</p>{slow_log_section_html}</div>
    <div class="section" id="sec-6"><h2>{_i18n('6. Version and Expiration', '6. 版本与到期')}</h2>{version_section_html}</div>
    <div class="section" id="sec-7"><h2>{_i18n('7. Inspection Conclusion', '7. 巡检结论')}</h2>{conclusion_html}</div>
    <div class="section" id="sec-8"><h2>{_i18n('8. Optimization Suggestions', '8. 优化建议')}</h2>{suggestions_html}</div>

    <div class="footer">RDS PostgreSQL {_i18n('Inspection Summary', 'Inspection summary')} · {inspect_time}</div>
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
</html>"""
    
    output_file = os.path.join(output_dir, 'summary.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'📄 Summary report: {output_file}')
    return output_file


# ═══════════════════════════════════════════════════════════════════════════
# 4. Main flow
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Alibaba Cloud RDS PostgreSQL batch instance inspection script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python3 inspect.py -i pgm-bp1xxx
  python3 inspect.py -i pgm-bp1xxx,pgm-bp1yyy --days 14
  python3 inspect.py --all --output ./reports/
  python3 inspect.py --all --regions cn-hangzhou,cn-shanghai --days 30
        """,
    )
    
    parser.add_argument(
        '--instance-ids', '-i',
        help='Instance IDs (may be specified multiple times or comma-separated)',
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Inspect all RDS PostgreSQL instances globally',
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=7,
        help='Time range in days (1-30, default 7)',
    )
    parser.add_argument(
        '--output', '-o',
        help='Output directory',
    )
    parser.add_argument(
        '--profile', '-p',
        help='aliyun CLI profile Name',
    )
    parser.add_argument(
        '--regions',
        help='Limit scanned regions (comma separated)',
    )
    parser.add_argument(
        '--concurrency', '-c',
        type=int,
        default=3,
        help='Per-instance inspection concurrency (default 3)',
    )
    parser.add_argument(
        '--region-concurrency',
        type=int,
        default=3,
        help='Region Region scan concurrency (default 3)',
    )
    
    args = parser.parse_args()
    
    global _CLI_PROFILE
    _CLI_PROFILE = args.profile
    
    # Validate arguments
    if not args.instance_ids and not args.all:
        print('Error: Either --instance-ids or --all must be specified', file=sys.stderr)
        sys.exit(1)
    
    if args.instance_ids and args.all:
        print('⚠️  -i and --all are both provided, -i will be ignored and --all takes precedence', file=sys.stderr)
    
    if args.days < 1 or args.days > 30:
        print('Error: --days must be between 1 and 30', file=sys.stderr)
        sys.exit(1)
    
    # Determine the output directory
    if args.output:
        output_dir = args.output
    else:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f'./rds-pg-inspection-reports/{ts}'
    
    os.makedirs(output_dir, exist_ok=True)
    
    print('=' * 70)
    print('RDS PostgreSQL Batch instance inspection')
    print('=' * 70)
    print(f'Time range: last {args.days} day(s)')
    print(f'Output directory: {output_dir}')
    print()

    # Pre-install CLI plugins (must run synchronously before concurrent calls)
    ensure_cli_plugins(['aliyun-cli-rds', 'aliyun-cli-cms'])
    print()

    # Phase 1: Fetch instance list
    if args.all:
        filter_regions = None
        if args.regions:
            filter_regions = [r.strip() for r in args.regions.split(',')]
        
        regions = list_active_regions(filter_regions)
        instances, region_count = discover_all_instances(regions, args.region_concurrency)
        
        if not instances:
            print('❌ No RDS PostgreSQL instances found')
            sys.exit(1)
    else:
        # Parse instance IDs
        instance_ids = []
        for id_str in args.instance_ids.split(','):
            instance_ids.extend([s.strip() for s in id_str.split() if s.strip()])
        
        if not instance_ids:
            print('Error: No valid instance IDs provided', file=sys.stderr)
            sys.exit(1)
        
        # TODO: Locate the region of each instance (single region for now)
        instances = []
        for iid in instance_ids:
            # Simple handling: assume all in cn-hangzhou
            instances.append({
                'instance_id': iid,
                'region_id': 'cn-hangzhou',
            })
        region_count = {'cn-hangzhou': len(instances)}
    
    print(f'\n📋 Pending inspection instances: {len(instances)} ')
    print()
    
    # Phase 2: Inspect each instance
    print('🔍 Start inspection...')
    all_instance_data = []
    
    for idx, inst in enumerate(instances, 1):
        iid = inst['instance_id']
        rid = inst['region_id']
        print(f'\n[{idx}/{len(instances)}] Inspecting {iid} ({rid})...')
        
        # Fetch instance attributes
        attr = get_instance_attribute(iid, rid)
        if not attr:
            print(f'  ⚠️  Failed to fetch instance attributes; skipping')
            continue
        
        norm_attr = normalize_attribute(attr)
                
        # Compute the time range (ms timestamps)
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = end_ms - (args.days * 24 * 3600 * 1000)
                
        # Collect monitoring data
        print(f'   Collecting monitoring data...', end=' ', flush=True)
        metrics_data = collect_instance_metrics(norm_attr, start_ms, end_ms)
        print('✅')
        
        # Collect alert history
        print(f'   Collecting alert history...', end=' ', flush=True)
        alerts_data = collect_instance_alerts(iid, start_ms, end_ms)
        print(f'✅ ({len(alerts_data)} items)')
                
        # Build instance data (integrating CMS monitoring and alert data)
        inst_data = {
            'instance_id': iid,
            'region_id': rid,
            'attribute': norm_attr,
            'metrics': metrics_data,  # CMS monitoring data integrated
            'slow_logs': {},  # TODO: Call the RDS API to fetch slow logs
            'alerts': alerts_data,  # CMS alert data integrated
        }
        
        # Compute health score
        health_score, deductions = calc_health_score(inst_data)
        inst_data['health_score'] = health_score
        inst_data['deductions'] = deductions
        
        all_instance_data.append(inst_data)
        
        icon, cls = score_status(health_score)
        print(f'  ✅ Health score: {icon} {health_score}/100')
        if deductions:
            print(f'  ⚠️  Deductions: {"; ".join(deductions[:3])}')
    
    # Phase 3: Generate the summary report
    print()
    print('=' * 70)
    print('Generating summary report...')
    print('=' * 70)
    
    summary = aggregate_summary(all_instance_data, region_count)
    
    inspect_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    range_str = f'last {args.days} day(s)'
    
    summary_file = render_summary_html(summary, output_dir, inspect_time, range_str)
    
    # Generate summary JSON
    summary_json_file = os.path.join(output_dir, 'summary.json')
    with open(summary_json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_instances': len(all_instance_data),
            'region_count': region_count,
            'global_score': summary['global_score'],
            'health_distribution': summary['health_dist'],
            'results': all_instance_data,
        }, f, ensure_ascii=False, indent=2)
    
    print(f'📄 Summary JSON: {summary_json_file}')
    
    # Phase 4: Generate the per-instance detailed report
    print()
    print('=' * 70)
    print('Generating per-instance detailed report...')
    print('=' * 70)
    
    instances_dir = os.path.join(output_dir, 'instances')
    os.makedirs(instances_dir, exist_ok=True)
    
    for idx, inst_data in enumerate(all_instance_data, 1):
        iid = inst_data['instance_id']
        print(f'[{idx}/{len(all_instance_data)}] Generate {iid} report...', end=' ', flush=True)
        
        instance_html = render_single_instance_html(inst_data, inspect_time, range_str)
        instance_file = os.path.join(instances_dir, f'{iid}.html')
        
        with open(instance_file, 'w', encoding='utf-8') as f:
            f.write(instance_html)
        
        print('✅')
    
    print(f'📁 Per-instance report directory: {instances_dir}')
    print()
    print('=' * 70)
    print('Inspection complete')
    print('=' * 70)
    print(f'Instances inspected: {len(all_instance_data)}')
    print(f'Global health: {summary["global_score"]}/100')
    print(f'Output directory: {output_dir}')
    print()
    print('✅ All done')


if __name__ == '__main__':
    main()
