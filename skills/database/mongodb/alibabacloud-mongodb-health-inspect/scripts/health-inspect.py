#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB (DDS) Instance Health Inspection Script
Uses aliyun CLI to call DDS / DAS / CMS APIs for comprehensive inspection
Supports: single instance / multiple instances / --all / --item / --days / --format(html|markdown|text)

Usage:
    python3 health-inspect.py <instance_id> [<instance_id> ...] [options]
    python3 health-inspect.py --all [options]
"""

import subprocess
import json
import sys
import os
import argparse
import html as _html
import re
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Globals ─────────────────────────────────────────────────────────────────

_CLI_PROFILE = None
_INSPECT_DAYS = 7
ALL_ITEMS = ['config', 'resource', 'space', 'slowlog', 'session', 'alert']
_INSPECT_ITEMS = set(ALL_ITEMS)

REGIONS = [
    'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen',
    'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
    'cn-hongkong', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3',
    'ap-southeast-5', 'ap-northeast-1', 'us-west-1', 'us-east-1',
    'eu-west-1', 'eu-central-1', 'me-east-1', 'ap-south-1',
]

INSTANCE_TYPES = ['sharding', 'replicate']

# ─── CLI Helper ──────────────────────────────────────────────────────────────


def call_cli(product, action, region=None, endpoint=None, timeout=30, **kwargs):
    session_id = os.environ.get('SKILL_SESSION_ID', '') or 'no-session'
    user_agent = f'AlibabaCloud-Agent-Skills/alibabacloud-mongodb-health-inspect/{session_id}'
    cmd = ['aliyun', product, action, '--user-agent', user_agent]
    if _CLI_PROFILE:
        cmd.extend(['--profile', _CLI_PROFILE])
    if region:
        cmd.extend(['--region', region])
    if endpoint:
        cmd.extend(['--endpoint', endpoint])
    for key, value in kwargs.items():
        cmd.extend([f'--{key}', str(value)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return None
        else:
            stderr = (result.stderr or '').strip()
            if stderr:
                print(f'  [WARN] {product} {action}: {stderr[:180]}', file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f'  [WARN] {product} {action} timed out', file=sys.stderr)
    return None


def call_dds(action, region=None, **kwargs):
    return call_cli('dds', action, region=region, **kwargs)


def call_das(action, **kwargs):
    return call_cli('das', action, endpoint='das.cn-shanghai.aliyuncs.com', **kwargs)


def call_cms(action, region=None, **kwargs):
    return call_cli('cms', action, region=region or 'cn-hangzhou', **kwargs)


# ─── Region Discovery ────────────────────────────────────────────────────────


def find_region(instance_id):
    for region in REGIONS:
        data = call_dds('DescribeDBInstanceAttribute', region, DBInstanceId=instance_id)
        if data:
            insts = data.get('DBInstances', {}).get('DBInstance', [])
            if insts:
                return insts[0].get('RegionId', region)
    return None


def discover_all_instances(region=None):
    """List all DDS instances (Sharding + ReplicaSet) under the current account"""
    instances = []
    regions_to_check = [region] if region else REGIONS

    def _fetch(r, t):
        found = []
        page = 1
        while True:
            data = call_dds('DescribeDBInstances', r, DBInstanceType=t,
                            PageSize='30', PageNumber=str(page))
            if not data:
                break
            items = data.get('DBInstances', {}).get('DBInstance', [])
            for it in items:
                found.append({
                    'instance_id': it.get('DBInstanceId', ''),
                    'region': it.get('RegionId', r),
                    'instance_type': t,
                    'description': it.get('DBInstanceDescription', ''),
                    'status': it.get('DBInstanceStatus', ''),
                    'engine_version': it.get('EngineVersion', ''),
                    'storage_type': it.get('StorageType', ''),
                })
            total = int(data.get('TotalCount', 0) or 0)
            if page * 30 >= total or not items:
                break
            page += 1
        return found

    pairs = [(r, t) for r in regions_to_check for t in INSTANCE_TYPES]
    with ThreadPoolExecutor(max_workers=min(len(pairs), 16)) as pool:
        futures = [pool.submit(_fetch, r, t) for r, t in pairs]
        for f in as_completed(futures):
            instances.extend(f.result())

    # Deduplicate (by instance_id)
    seen = set()
    deduped = []
    for inst in instances:
        if inst['instance_id'] in seen:
            continue
        seen.add(inst['instance_id'])
        deduped.append(inst)
    return deduped


# ─── Instance Info ───────────────────────────────────────────────────────────


def get_instance_info(instance_id, region):
    data = call_dds('DescribeDBInstanceAttribute', region, DBInstanceId=instance_id)
    if not data:
        return None
    insts = data.get('DBInstances', {}).get('DBInstance', [])
    return insts[0] if insts else None


def collect_node_ids(info):
    """Return (shard_nodes, mongos_nodes, cs_nodes), each node dict contains NodeId/NodeClass/MaxConnections/MaxIOPS/NodeStorage/Status"""
    shards = info.get('ShardList', {}).get('ShardAttribute', []) or []
    mongos = info.get('MongosList', {}).get('MongosAttribute', []) or []
    cs = info.get('ConfigserverList', {}).get('ConfigserverAttribute', []) or []
    return shards, mongos, cs


# ─── Performance ─────────────────────────────────────────────────────────────


def _split_time_windows(start_time, end_time, hours_per_window=24):
    """Split time window by hours to avoid exceeding per-call limits. Returns [(start, end), ...]"""
    fmt = '%Y-%m-%dT%H:%MZ'
    s = datetime.strptime(start_time, fmt).replace(tzinfo=timezone.utc)
    e = datetime.strptime(end_time, fmt).replace(tzinfo=timezone.utc)
    windows = []
    cur = s
    while cur < e:
        nxt = min(cur + timedelta(hours=hours_per_window), e)
        windows.append((cur.strftime(fmt), nxt.strftime(fmt)))
        cur = nxt
    return windows


def get_performance(instance_id, region, node_id, key, start_time, end_time):
    """Single-segment performance query; when node_id is None/empty, NodeId is omitted (for ReplicaSet default Primary)"""
    kwargs = dict(DBInstanceId=instance_id, Key=key,
                  StartTime=start_time, EndTime=end_time)
    if node_id:
        kwargs['NodeId'] = node_id
    data = call_dds('DescribeDBInstancePerformance', region, **kwargs)
    if not data:
        return []
    return data.get('PerformanceKeys', {}).get('PerformanceKey', [])


def get_replicaset_role_ids(instance_id, region):
    """ReplicaSet only: get RoleId list from DescribeReplicaSetRole (skip SRV connection addresses)"""
    data = call_dds('DescribeReplicaSetRole', region, DBInstanceId=instance_id)
    if not data:
        return []
    role_ids = []
    for r in data.get('ReplicaSets', {}).get('ReplicaSet', []) or []:
        rid = r.get('RoleId')
        role = r.get('ReplicaSetRole', '')
        if rid and role in ('Primary', 'Secondary'):
            role_ids.append({'RoleId': rid, 'Role': role,
                             'ConnectionDomain': r.get('ConnectionDomain', '')})
    return role_ids


def get_performance_daily(instance_id, region, node_id, key, start_time, end_time):
    """Query in 24-hour segments and merge all data points"""
    merged = {}  # key -> list of perf values
    for s, e in _split_time_windows(start_time, end_time, 24):
        perf_list = get_performance(instance_id, region, node_id, key, s, e)
        for pk in perf_list:
            k = pk.get('Key', '')
            if k not in merged:
                merged[k] = []
            for pv in pk.get('PerformanceValues', {}).get('PerformanceValue', []):
                merged[k].append(pv)
    return [{'Key': k, 'PerformanceValues': {'PerformanceValue': v}} for k, v in merged.items()]


def parse_perf_values(perf_keys, target_key=None, value_index=0):
    values = []
    for pk in perf_keys:
        if target_key and pk.get('Key', '') != target_key:
            continue
        for pv in pk.get('PerformanceValues', {}).get('PerformanceValue', []):
            raw = pv.get('Value', '')
            try:
                parts = raw.split('&')
                if value_index < len(parts):
                    values.append(float(parts[value_index]))
                else:
                    values.append(float(parts[0]))
            except (ValueError, IndexError):
                pass
    return values


def parse_perf_timeseries(perf_keys, target_key=None, value_index=0):
    """Return [(timestamp_ms, value), ...], sorted chronologically"""
    points = []
    for pk in perf_keys:
        if target_key and pk.get('Key', '') != target_key:
            continue
        for pv in pk.get('PerformanceValues', {}).get('PerformanceValue', []):
            ts_str = pv.get('Date') or pv.get('Timestamp') or ''
            raw = pv.get('Value', '')
            try:
                parts = raw.split('&')
                val = float(parts[value_index]) if value_index < len(parts) else float(parts[0])
            except (ValueError, IndexError):
                continue
            try:
                if 'T' in ts_str:
                    iso = ts_str.replace('Z', '')
                    ts = None
                    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
                        try:
                            ts = datetime.strptime(iso[:len(fmt) + 6], fmt).replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue
                    if ts is None:
                        continue
                    ms = int(ts.timestamp() * 1000)
                else:
                    ms = int(ts_str)
            except (ValueError, TypeError):
                continue
            points.append((ms, val))
    points.sort(key=lambda x: x[0])
    return points


def calc_avg_peak(values):
    if not values:
        return 0.0, 0.0
    return round(sum(values) / len(values), 2), round(max(values), 2)


# ─── Inspect: Resource ───────────────────────────────────────────────────────


_PERF_KEYS_FULL = [
    ('CpuUsage', 'cpu', 1, [0]),
    ('MemoryUsage', 'memory', 1, [0]),
    ('MongoDB_Connections', 'connections', 1, [0]),
    ('DiskUsage', 'disk_usage', 1, [0]),
    ('IOPSUsage', 'iops_usage', 1, [0]),
    ('MongoDB_MbpsUsage', 'mbps', 3, [0, 1, 2]),  # total, read, write
    ('MongoDB_IOPS', 'iops_abs', 3, [0, 1, 2]),
    ('MongoDB_DetailedSpaceUsage', 'space', 3, [0, 1, 2]),  # total, data, log
    ('MongoDB_Network', 'net', 3, [0, 1, 2]),
    ('MongoDB_Opcounters', 'ops', 6, [0, 1, 2, 3, 4, 5]),
]

_PERF_KEYS_MONGOS = [
    ('CpuUsage', 'cpu', 1, [0]),
    ('MongoDB_Connections', 'connections', 1, [0]),
]


def get_node_metrics(instance_id, region, node_id, start_time, end_time, is_mongos=False):
    """Collect all metrics for a single node, return metrics dict + timeseries dict"""
    keys_def = _PERF_KEYS_MONGOS if is_mongos else _PERF_KEYS_FULL
    metrics = {}
    timeseries = {}
    for key, label, _, indices in keys_def:
        perf = get_performance_daily(instance_id, region, node_id, key, start_time, end_time)
        if not perf:
            continue
        for idx in indices:
            sub = '' if len(indices) == 1 else f'_{idx}'
            values = parse_perf_values(perf, value_index=idx)
            metrics[f'{label}{sub}'] = calc_avg_peak(values)
            ts = parse_perf_timeseries(perf, value_index=idx)
            timeseries[f'{label}{sub}'] = ts
    return metrics, timeseries


def inspect_config(info):
    """Assess instance configuration risks using field values only, zero API calls.

    Returns {'items': [(category, level, message, value)], 'overall': level}
    level: 'danger' | 'warn' | 'info' | 'normal'
    """
    items = []

    # 1. Billing & Expiration
    charge = info.get('ChargeType', '') or ''
    charge_label = {'PostPaid': 'Pay-As-You-Go', 'PrePaid': 'Subscription'}.get(charge, charge)
    if charge == 'PrePaid':
        expire = info.get('ExpireTime', '') or ''
        days_left = None
        if expire:
            iso = expire.replace('Z', '').strip()
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S'):
                try:
                    exp_dt = datetime.strptime(iso[:len(fmt) + 6], fmt)
                    days_left = (exp_dt - datetime.utcnow()).days
                    break
                except Exception:
                    continue
        if days_left is None:
            items.append(('Billing & Expiration', 'info', 'Expiration time format unrecognized', f'{charge_label} / {expire or "N/A"}'))
        elif days_left < 0:
            items.append(('Billing & Expiration', 'danger', f'Instance expired {-days_left} days ago, at risk of release', f'{charge_label} / {expire}'))
        elif days_left <= 7:
            items.append(('Billing & Expiration', 'danger', f'{days_left} days until expiration, immediate renewal recommended', f'{charge_label} / {expire}'))
        elif days_left <= 30:
            items.append(('Billing & Expiration', 'warn', f'{days_left} days until expiration, plan renewal soon', f'{charge_label} / {expire}'))
        else:
            items.append(('Billing & Expiration', 'normal', f'Expiration is well ahead ({days_left} days remaining)', f'{charge_label} / {expire}'))
    else:
        items.append(('Billing & Expiration', 'normal', 'Pay-As-You-Go, no expiration risk', charge_label or 'N/A'))

    # 2. Lock Status
    lock = info.get('LockMode', '') or 'Unlock'
    if lock and lock != 'Unlock':
        reason = info.get('LockReason', '') or lock
        items.append(('Lock Status', 'danger', f'Instance is locked: {lock}', reason))
    else:
        items.append(('Lock Status', 'normal', 'Instance is not locked', 'Unlock'))

    # 3. Storage Type
    st = info.get('StorageType', '') or ''
    st_lower = st.lower()
    if st_lower == 'local_ssd':
        items.append(('Storage Type', 'danger', 'Local SSD is discontinued, migrate to cloud_essd', st))
    elif st_lower == 'cloud_ssd':
        items.append(('Storage Type', 'warn', 'cloud_ssd has limited performance, upgrade to cloud_essd recommended', st))
    elif st_lower.startswith('cloud_essd'):
        items.append(('Storage Type', 'normal', 'Cloud ESSD (recommended)', st))
    elif st:
        items.append(('Storage Type', 'info', f'Storage type: {st}', st))
    else:
        items.append(('Storage Type', 'info', 'Storage type not recognized', 'N/A'))

    # 4. Engine Version
    ev = (info.get('EngineVersion', '') or '').strip()
    try:
        major = float(ev) if ev else 0.0
    except ValueError:
        major = 0.0
    if major and major < 4.4:
        items.append(('Engine Version', 'danger', f'MongoDB {ev} is end-of-life, upgrade to 5.0+ recommended', ev))
    elif major and major < 5.0:
        items.append(('Engine Version', 'warn', f'MongoDB {ev} is outdated, plan an upgrade', ev))
    elif major:
        items.append(('Engine Version', 'normal', f'MongoDB {ev} is supported', ev))
    else:
        items.append(('Engine Version', 'info', 'Version not recognized', ev or 'N/A'))

    # 5. Availability Zone Deployment
    primary_zone = info.get('ZoneId', '') or ''
    secondary_zone = info.get('SecondaryZoneId', '') or ''
    hidden_zone = info.get('HiddenZoneId', '') or ''
    distinct_zones = sorted({z for z in [primary_zone, secondary_zone, hidden_zone] if z})
    if len(distinct_zones) >= 3:
        items.append(('AZ Deployment', 'normal', 'Triple-AZ high availability deployment', ' / '.join(distinct_zones)))
    elif len(distinct_zones) == 2:
        items.append(('AZ Deployment', 'normal', 'Dual-AZ deployment', ' / '.join(distinct_zones)))
    elif len(distinct_zones) == 1:
        items.append(('AZ Deployment', 'warn', 'Single-AZ deployment, no AZ-level disaster recovery', distinct_zones[0]))
    else:
        items.append(('AZ Deployment', 'info', 'Availability zone info missing', 'N/A'))

    levels = [it[1] for it in items]
    if 'danger' in levels:
        overall = 'danger'
    elif 'warn' in levels:
        overall = 'warn'
    elif 'info' in levels:
        overall = 'info'
    else:
        overall = 'normal'
    return {'items': items, 'overall': overall}


def inspect_resource(instance_id, region, info, start_time, end_time):
    shards, mongos, _ = collect_node_ids(info)
    instance_type = info.get('DBInstanceType', '')
    is_replica = instance_type == 'replicate'
    shard_ids = [s.get('NodeId') for s in shards if s.get('NodeId')]
    mongos_ids = [m.get('NodeId') for m in mongos if m.get('NodeId')]

    # ReplicaSet: DDS DescribeDBInstancePerformance does not support NodeId (causes InternalError),
    # so only instance-level aggregated data is available. Rendering shows each node (Primary/Secondary) separately.
    replica_roles = []
    if is_replica and not shard_ids:
        replica_roles = get_replicaset_role_ids(instance_id, region)
        for role in replica_roles:
            rid = role.get('RoleId', '')
            label = f'{rid} ({role.get("Role", "")})'
            shards = list(shards) + [{
                'NodeId': label,
                'NodeClass': info.get('DBInstanceClass', ''),
                'MaxConnections': info.get('MaxConnections', 0),
                'MaxIOPS': info.get('MaxIOPS', ''),
                'NodeStorage': info.get('DBInstanceStorage', ''),
                'Status': info.get('DBInstanceStatus', ''),
            }]
            shard_ids.append(label)

    # Job tuples: (metrics_label, api_node_id, is_mongos). ReplicaSet API does not support NodeId, pass None for instance-level data.
    all_jobs = []
    for nid in shard_ids:
        api_nid = None if is_replica else nid
        all_jobs.append((nid, api_nid, False))
    for nid in mongos_ids:
        all_jobs.append((nid, nid, True))

    if not all_jobs:
        return {'shards': shards, 'mongos': mongos, 'metrics': {}, 'timeseries': {},
                'shard_ids': shard_ids, 'mongos_ids': mongos_ids,
                'replica_roles': replica_roles}

    node_metrics = {}
    node_timeseries = {}
    with ThreadPoolExecutor(max_workers=min(len(all_jobs), 8)) as pool:
        future_map = {
            pool.submit(get_node_metrics, instance_id, region, api_nid, start_time, end_time, is_mg): (label, api_nid, is_mg)
            for label, api_nid, is_mg in all_jobs
        }
        for f in as_completed(future_map):
            label, _api, _is_mg = future_map[f]
            try:
                m, ts = f.result()
            except Exception:
                m, ts = {}, {}
            node_metrics[label] = m
            node_timeseries[label] = ts

    return {
        'shards': shards, 'mongos': mongos,
        'shard_ids': shard_ids, 'mongos_ids': mongos_ids,
        'metrics': node_metrics, 'timeseries': node_timeseries,
        'replica_roles': replica_roles,
    }


# ─── Inspect: Space ──────────────────────────────────────────────────────────


def inspect_space(instance_id):
    """Get TOP20 collections via DAS API storage analysis"""
    try:
        create = call_das('CreateStorageAnalysisTask', InstanceId=instance_id)
    except Exception:
        create = None
    if not create:
        return {'available': False, 'reason': 'DAS CreateStorageAnalysisTask unavailable or not enabled for this account'}
    code = create.get('Code', 0)
    data = create.get('Data', {}) or {}
    task_id = data.get('TaskId')
    if not (code == 200 and task_id):
        return {'available': False, 'reason': f'Task creation failed: {create.get("Message", "")[:120]}'}

    # Poll task result (up to 60 seconds)
    result = None
    for _ in range(20):
        time.sleep(3)
        r = call_das('GetStorageAnalysisResult', InstanceId=instance_id, TaskId=task_id)
        if not r:
            continue
        if r.get('Code', 0) != 200:
            continue
        d = r.get('Data', {}) or {}
        status = d.get('Status') or d.get('TaskStatus') or ''
        if d.get('StorageAnalysisResult') or status.lower() in ('finished', 'succeed', 'success', 'completed'):
            result = d
            break
    if not result:
        return {'available': False, 'reason': 'Task timed out or returned no result'}

    sa = result.get('StorageAnalysisResult', {}) or {}
    # Compatible with multiple field names
    coll_stats = (sa.get('CollectionStats') or sa.get('TableStats')
                  or sa.get('Collections') or [])
    if isinstance(coll_stats, dict):
        coll_stats = (coll_stats.get('CollectionStat') or coll_stats.get('TableStat')
                      or coll_stats.get('Collection') or [])
    rows = []
    for c in coll_stats:
        rows.append({
            'db': c.get('DbName') or c.get('SchemaName') or '',
            'collection': c.get('CollectionName') or c.get('TableName') or '',
            'total_size': float(c.get('TotalSize') or c.get('TotalSizeMB') or c.get('Size') or 0),
            'data_size': float(c.get('DataSize') or c.get('DataSizeMB') or 0),
            'index_size': float(c.get('IndexSize') or c.get('IndexSizeMB') or 0),
            'count': int(c.get('Count') or c.get('Rows') or c.get('DocCount') or 0),
        })
    rows.sort(key=lambda x: x['total_size'], reverse=True)
    return {'available': True, 'top20': rows[:20], 'total_used': sum(r['total_size'] for r in rows)}


# ─── Inspect: Session (DAS) ──────────────────────────────────────────────────


def inspect_session(instance_id, node_ids):
    sessions = {}

    def _one(nid):
        data = call_das('GetMongoDBCurrentOp', **{'InstanceId': instance_id, 'NodeId': nid})
        if not data or not data.get('Success'):
            return nid, None
        d = data.get('Data', {}) or {}
        stat = d.get('SessionStat', {}) or {}
        return nid, {
            'total': stat.get('TotalCount', 0),
            'active': stat.get('ActiveCount', 0),
            'longest_secs': stat.get('LongestSecsRunning', 0),
            'session_list': d.get('SessionList', []) or [],
        }

    if not node_ids:
        return sessions
    with ThreadPoolExecutor(max_workers=min(len(node_ids), 8)) as pool:
        futures = [pool.submit(_one, nid) for nid in node_ids]
        for f in as_completed(futures):
            nid, s = f.result()
            if s is not None:
                sessions[nid] = s
    return sessions


# ─── Inspect: Slowlog ────────────────────────────────────────────────────────


def inspect_slowlog(instance_id, region, info, start_time, end_time):
    """Sharding: query by Shard/Mongos/CS nodes; ReplicaSet: query by Primary/Secondary nodes. Time window split by day."""
    shards, mongos, cs = collect_node_ids(info)
    instance_type = info.get('DBInstanceType', '')

    if instance_type == 'sharding':
        shard_ids = [s.get('NodeId') for s in shards if s.get('NodeId')]
        mongos_ids = [m.get('NodeId') for m in mongos if m.get('NodeId')]
        cs_ids = [c.get('NodeId') for c in cs if c.get('NodeId')]
        targets = shard_ids + mongos_ids + cs_ids if (shard_ids or mongos_ids or cs_ids) else [None]
    else:
        replica_roles = get_replicaset_role_ids(instance_id, region)
        if replica_roles:
            targets = [r.get('RoleId') for r in replica_roles if r.get('RoleId')]
        else:
            targets = [None]

    all_records = []
    for nid in targets:
        records = []
        total = 0
        for s, e in _split_time_windows(start_time, end_time, 24):
            kwargs = {
                'DBInstanceId': instance_id,
                'StartTime': s,
                'EndTime': e,
                'PageSize': '30',
                'PageNumber': '1',
            }
            if nid:
                kwargs['NodeId'] = nid
            data = call_dds('DescribeSlowLogRecords', region, **kwargs)
            if not data:
                continue
            recs = data.get('Items', {}).get('LogRecords', []) or []
            records.extend(recs)
            total += int(data.get('TotalRecordCount', 0) or 0)
        # Sort by query time descending, take top 30
        records.sort(key=lambda r: int(r.get('QueryTimes', 0) or 0), reverse=True)
        all_records.append({
            'node_id': nid or instance_id,
            'total': total,
            'records': records[:30],
        })
    return all_records


# ─── Inspect: Alert ──────────────────────────────────────────────────────────


def inspect_alert(instance_id, region, start_time, end_time):
    """Query CMS alert history"""
    fmt = '%Y-%m-%dT%H:%MZ'
    try:
        s_ts = int(datetime.strptime(start_time, fmt).replace(tzinfo=timezone.utc).timestamp() * 1000)
        e_ts = int(datetime.strptime(end_time, fmt).replace(tzinfo=timezone.utc).timestamp() * 1000)
    except ValueError:
        return {'available': False, 'records': [], 'reason': 'Time format error'}

    namespaces = ['acs_mongodb', 'acs_mongodb_replicate']
    records = []
    available = False
    for ns in namespaces:
        data = call_cms('DescribeAlertHistoryList', region,
                        Namespace=ns, StartTime=str(s_ts), EndTime=str(e_ts),
                        PageSize='100')
        if data is None:
            continue
        available = True
        items = data.get('AlarmHistoryList', {}).get('AlarmHistory', []) or []
        if isinstance(items, dict):
            items = items.get('AlarmHistory', []) or []
        for it in items:
            res_str = it.get('Resource', '') or ''
            if instance_id and instance_id not in res_str:
                continue
            records.append({
                'time': it.get('AlertTime') or it.get('LastTime') or '',
                'level': it.get('LevelChange') or it.get('Level') or '',
                'metric': it.get('MetricName', ''),
                'message': (it.get('AlertContent') or it.get('AlertName') or '')[:200],
                'state': it.get('AlertState', ''),
            })
    return {'available': available, 'records': records,
            'reason': '' if available else 'CMS DescribeAlertHistoryList unavailable'}


# ─── Status & Format Helpers ─────────────────────────────────────────────────


def status_icon(value, warn=60, danger=80):
    if value > danger:
        return '🔴'
    if value > warn:
        return '🟡'
    return '🟢'


def format_size_mb(mb):
    if mb >= 1024:
        return f'{mb/1024:.2f} GB'
    return f'{mb:.2f} MB'


def short(s, n=80):
    if not s:
        return ''
    s = str(s)
    return s if len(s) <= n else s[:n] + '...'


def he(s):
    return _html.escape(str(s) if s is not None else '')


def sparkline(points, width=40):
    """Convert [(ts, val), ...] to a Unicode block sparkline string."""
    if not points:
        return ''
    vals = [p[1] for p in points]
    n = len(vals)
    if n > width:
        step = n / width
        sampled = [vals[int(i * step)] for i in range(width)]
    else:
        sampled = vals
    blocks = ' ▁▂▃▄▅▆▇█'
    lo, hi = min(sampled), max(sampled)
    if hi == lo:
        return blocks[1] * len(sampled)
    return ''.join(blocks[1 + int((v - lo) / (hi - lo) * 7)] for v in sampled)


# ─── Suggestions ─────────────────────────────────────────────────────────────


def build_suggestions(report):
    """Aggregate suggestions; returns [(level, message), ...], level: danger/warn/info"""
    sug = []

    # Config risks
    cfg = report.get('config') or {}
    for cat, level, msg, _val in cfg.get('items', []) or []:
        if level in ('danger', 'warn'):
            sug.append((level, f'[Config] {cat}: {msg}'))

    res = report.get('resource') or {}
    metrics = res.get('metrics') or {}
    shards = res.get('shards') or []

    for shard in shards:
        nid = shard.get('NodeId')
        m = metrics.get(nid) or {}
        max_conn = int(shard.get('MaxConnections', 0) or 0)

        cpu_peak = m.get('cpu', (0, 0))[1]
        mem_peak = m.get('memory', (0, 0))[1]
        conn_peak = m.get('connections', (0, 0))[1]
        disk_peak = m.get('disk_usage', (0, 0))[1]
        iops_peak = m.get('iops_usage', (0, 0))[1]
        mbps_peak = m.get('mbps_0', (0, 0))[1]

        conn_pct = (conn_peak / max_conn * 100) if max_conn else 0

        if cpu_peak > 80:
            sug.append(('danger', f'{nid} CPU peak {cpu_peak}% exceeds 80%, consider upgrading Shard specs or optimizing high-CPU slow queries'))
        elif cpu_peak > 60:
            sug.append(('warn', f'{nid} CPU peak {cpu_peak}% exceeds 60%, monitor recommended'))
        if mem_peak > 80:
            sug.append(('danger', f'{nid} Memory peak {mem_peak}% exceeds 80%, consider upgrading specs or checking working set'))
        elif mem_peak > 60:
            sug.append(('warn', f'{nid} Memory peak {mem_peak}% exceeds 60%, monitor recommended'))
        if conn_pct > 80:
            sug.append(('danger', f'{nid} Connection peak {conn_pct:.1f}% exceeds 80%, check connection pool configuration'))
        elif conn_pct > 60:
            sug.append(('warn', f'{nid} Connection peak {conn_pct:.1f}% exceeds 60%, monitor recommended'))
        if disk_peak > 85:
            sug.append(('danger', f'{nid} Disk usage peak {disk_peak}% exceeds 85%, clean up data or expand storage'))
        elif disk_peak > 70:
            sug.append(('warn', f'{nid} Disk usage peak {disk_peak}% exceeds 70%, monitor recommended'))
        if iops_peak > 80:
            sug.append(('danger', f'{nid} IOPS usage peak {iops_peak}% exceeds 80%, optimize IO or upgrade specs'))
        elif iops_peak > 60:
            sug.append(('warn', f'{nid} IOPS usage peak {iops_peak}% exceeds 60%, monitor recommended'))
        if mbps_peak > 80:
            sug.append(('danger', f'{nid} Disk bandwidth peak {mbps_peak}% exceeds 80%, optimize bulk I/O or upgrade specs'))
        elif mbps_peak > 60:
            sug.append(('warn', f'{nid} Disk bandwidth peak {mbps_peak}% exceeds 60%, monitor recommended'))

    sessions = report.get('session') or {}
    for nid, s in sessions.items():
        longest = int(s.get('longest_secs', 0) or 0)
        active = int(s.get('active', 0) or 0)
        if longest > 300:
            sug.append(('danger', f'{nid} has sessions running over 5 minutes (longest {longest}s), investigate blocking operations'))
        elif longest > 60:
            sug.append(('warn', f'{nid} has sessions running over 1 minute (longest {longest}s), monitor recommended'))
        if active > 100:
            sug.append(('warn', f'{nid} active sessions count {active} is high, check workload'))

    slow_total = sum(s.get('total', 0) for s in (report.get('slowlog') or []))
    if slow_total > 10:
        sug.append(('warn', f'High slow query count ({slow_total}), optimize top slow queries and add indexes'))
    elif slow_total > 0:
        sug.append(('info', f'{slow_total} slow queries found, monitor recommended'))

    alert = report.get('alert') or {}
    alert_count = len(alert.get('records', []) or [])
    if alert_count > 0:
        sug.append(('warn', f'{alert_count} alerts in the last {_INSPECT_DAYS} days, follow up on alert rules in the console'))

    return sug


# ─── Renderers split into separate concerns; loaded later ─────────────────────



# ─── Render: Text ────────────────────────────────────────────────────────────


def render_text(report):
    L = []
    p = L.append

    info = report['info']
    instance_id = report['instance_id']
    region = report['region']
    inspect_time = report['inspect_time']
    start_time = report['start_time']
    end_time = report['end_time']
    days = report['days']

    instance_type = info.get('DBInstanceType', '')
    type_label = {'sharding': 'Sharding Cluster', 'replicate': 'ReplicaSet'}.get(instance_type, instance_type)
    charge_label = {'PostPaid': 'Pay-As-You-Go', 'PrePaid': 'Subscription'}.get(info.get('ChargeType', ''), info.get('ChargeType', ''))

    # Header
    p('┌' + '─' * 78 + '┐')
    p('│' + 'MongoDB (DDS) Instance Health Inspection Report'.center(76) + '│')
    p('└' + '─' * 78 + '┘')
    p(f'  Inspect Time: {inspect_time}')
    p(f'  Instance ID:  {instance_id}')
    p(f'  Region:       {region}')
    p(f'  Inspect Period: {start_time} ~ {end_time}')
    p('')

    # Section 1 -- only show when full inspection or config item selected
    is_full = _INSPECT_ITEMS == set(ALL_ITEMS)
    if is_full:
        p('=' * 80)
        p(' Section 1: Instance Basic Info')
        p('=' * 80)
        p('')
        rows = [
            ('Instance Type', type_label),
            ('Major Version', f'MongoDB {info.get("EngineVersion", "")}'),
            ('Kernel Version', info.get('CurrentKernelVersion', '')),
            ('Storage Engine', info.get('StorageEngine', '')),
            ('Storage Type', info.get('StorageType', '')),
            ('Billing', charge_label),
            ('Status', info.get('DBInstanceStatus', '')),
            ('Created At', info.get('CreationTime', '')),
            ('Max Connections', str(info.get('MaxConnections', 'N/A'))),
            ('Max IOPS', str(info.get('MaxIOPS', 'N/A'))),
        ]
        for k, v in rows:
            p(f'  {k:<16}{v}')
        p('')

        shards, mongos, cs = collect_node_ids(info)
        if mongos:
            p(f'  Mongos Nodes ({len(mongos)}):')
            p(f'    {"Node ID":<26}{"Spec":<22}{"Max Conn":<10}{"Status"}')
            for m in mongos:
                p(f'    {m.get("NodeId",""):<26}{m.get("NodeClass",""):<22}{str(m.get("MaxConnections","")):<10}{m.get("Status","")}')
            p('')
        if shards:
            p(f'  Shard Nodes ({len(shards)}):')
            p(f'    {"Node ID":<26}{"Spec":<22}{"Storage(GB)":<12}{"Max Conn":<10}{"Max IOPS":<10}{"Status"}')
            for s in shards:
                p(f'    {s.get("NodeId",""):<26}{s.get("NodeClass",""):<22}{str(s.get("NodeStorage","")):<12}{str(s.get("MaxConnections","")):<10}{str(s.get("MaxIOPS","")):<10}{s.get("Status","")}')
            p('')
        if cs:
            p(f'  ConfigServer Nodes ({len(cs)}):')
            p(f'    {"Node ID":<26}{"Spec":<22}{"Storage(GB)":<12}{"Status"}')
            for c in cs:
                p(f'    {c.get("NodeId",""):<26}{c.get("NodeClass",""):<22}{str(c.get("NodeStorage","")):<12}{c.get("Status","")}')
            p('')

    # Section 2: Config Risk
    if 'config' in _INSPECT_ITEMS and report.get('config'):
        cfg = report['config']
        p('=' * 80)
        p(' Section 2: Configuration Risk Assessment')
        p('=' * 80)
        p('')
        icon_map = {'danger': '🔴', 'warn': '🟡', 'info': '🔵', 'normal': '🟢'}
        p(f'  {"Level":<8}{"Category":<22}{"Description":<46}{"Current Value"}')
        p('  ' + '─' * 90)
        for cat, level, msg, val in cfg.get('items', []) or []:
            icon = icon_map.get(level, '🔵')
            p(f'  {icon:<5}{cat:<22}{msg[:44]:<46}{val}')
        overall_icon = icon_map.get(cfg.get('overall', 'info'), '🔵')
        p('')
        p(f'  Overall Config Risk: {overall_icon} {cfg.get("overall", "info").upper()}')
        p('')

    # Section 3: Resource
    if 'resource' in _INSPECT_ITEMS and report.get('resource'):
        res = report['resource']
        metrics = res['metrics']
        shard_ids = res['shard_ids']
        mongos_ids = res['mongos_ids']
        p('=' * 80)
        p(f' Section 3: Resource Usage (Last {days} Days)')
        p('=' * 80)
        p('')
        if shard_ids:
            p('  [Shard Node Details]')
            p('')
            for nid in shard_ids:
                m = metrics.get(nid) or {}
                if not m:
                    continue
                shard_info = next((s for s in res['shards'] if s.get('NodeId') == nid), {})
                max_conn = int(shard_info.get('MaxConnections', 0) or 0)
                max_iops = shard_info.get('MaxIOPS', '')
                cpu_a, cpu_p = m.get('cpu', (0, 0))
                mem_a, mem_p = m.get('memory', (0, 0))
                conn_a, conn_p = m.get('connections', (0, 0))
                disk_a, disk_p = m.get('disk_usage', (0, 0))
                iops_a, iops_p = m.get('iops_usage', (0, 0))
                mbps_a, mbps_p = m.get('mbps_0', (0, 0))
                mbps_r_a, mbps_r_p = m.get('mbps_1', (0, 0))
                mbps_w_a, mbps_w_p = m.get('mbps_2', (0, 0))
                space_a, space_p = m.get('space_0', (0, 0))
                iops_abs_a, iops_abs_p = m.get('iops_abs_0', (0, 0))
                net_in_a, _ = m.get('net_0', (0, 0))
                net_out_a, _ = m.get('net_1', (0, 0))
                net_req_a, _ = m.get('net_2', (0, 0))

                conn_pct_a = (conn_a / max_conn * 100) if max_conn else 0
                conn_pct_p = (conn_p / max_conn * 100) if max_conn else 0

                p(f'  ▸ {nid} (Shard)')
                p(f'    CPU:          Avg {cpu_a}%  Peak {cpu_p}%  {status_icon(cpu_p)}')
                p(f'    Memory:       Avg {mem_a}%  Peak {mem_p}%  {status_icon(mem_p)}')
                p(f'    Connections:  Avg {conn_a:.0f}/{max_conn} ({conn_pct_a:.1f}%)  Peak {conn_p:.0f}/{max_conn} ({conn_pct_p:.1f}%)  {status_icon(conn_pct_p)}')
                p(f'    Disk Usage:   Avg {disk_a}%  Peak {disk_p}%  {status_icon(disk_p, 70, 85)}')
                p(f'    IOPS Usage:   Avg {iops_a}%  Peak {iops_p}%  {status_icon(iops_p)}')
                p(f'    Disk BW:      Avg {mbps_a}% (R:{mbps_r_a}% W:{mbps_w_a}%)  Peak {mbps_p}% (R:{mbps_r_p}% W:{mbps_w_p}%)  {status_icon(mbps_p)}')
                p(f'    Disk Space:   Avg {format_size_mb(space_a)}  Peak {format_size_mb(space_p)}')
                p(f'    IOPS Abs:     Avg {iops_abs_a:.0f}  Peak {iops_abs_p:.0f} (Limit {max_iops})')
                p(f'    Network:      In {net_in_a:.0f} B/s  Out {net_out_a:.0f} B/s  Req {net_req_a:.0f} ops')
                ops_labels = ['insert', 'query', 'update', 'delete', 'getmore', 'command']
                ops_strs = []
                for i, lbl in enumerate(ops_labels):
                    a, q = m.get(f'ops_{i}', (0, 0))
                    ops_strs.append(f'{lbl} {a:.1f}/{q:.1f}')
                p(f'    Opcounters: {" | ".join(ops_strs[:3])}')
                p(f'                {" | ".join(ops_strs[3:])}')
                p('')

        if mongos_ids:
            p('  [Mongos Node Details]')
            p('')
            for nid in mongos_ids:
                m = metrics.get(nid) or {}
                if not m:
                    continue
                mongos_info = next((mg for mg in mongos if mg.get('NodeId') == nid), {})
                max_conn = int(mongos_info.get('MaxConnections', 0) or 0)
                cpu_a, cpu_p = m.get('cpu', (0, 0))
                conn_a, conn_p = m.get('connections', (0, 0))
                conn_pct_p = (conn_p / max_conn * 100) if max_conn else 0
                p(f'  ▸ {nid} (Mongos)')
                p(f'    CPU:         Avg {cpu_a}%  Peak {cpu_p}%  {status_icon(cpu_p)}')
                p(f'    Connections: Avg {conn_a:.0f}  Peak {conn_p:.0f}  Usage {conn_pct_p:.1f}% (Limit {max_conn})  {status_icon(conn_pct_p)}')
                p('')

    # Section 4: Space
    if 'space' in _INSPECT_ITEMS:
        sp = report.get('space') or {}
        p('=' * 80)
        p(' Section 4: Storage Usage Details TOP20')
        p('=' * 80)
        p('')
        if not sp.get('available'):
            p(f'  ⚠️  Not supported / data unavailable: {sp.get("reason", "")}')
            p('')
        else:
            top = sp.get('top20', []) or []
            if not top:
                p('  ✅ No collection data available')
            else:
                p(f'  {"#":<4}{"Database":<20}{"Collection":<28}{"Total Size":<12}{"Data":<12}{"Index":<12}{"Doc Count":<10}')
                p('  ' + '─' * 96)
                for i, c in enumerate(top, 1):
                    p(f'  {i:<4}{c["db"][:18]:<20}{c["collection"][:26]:<28}'
                      f'{format_size_mb(c["total_size"])[:10]:<12}'
                      f'{format_size_mb(c["data_size"])[:10]:<12}'
                      f'{format_size_mb(c["index_size"])[:10]:<12}'
                      f'{c["count"]:<10}')
                p('')
                p(f'  Total space used: {format_size_mb(sp.get("total_used", 0))}')
            p('')

    # Section 5: Session
    if 'session' in _INSPECT_ITEMS:
        sessions = report.get('session') or {}
        p('=' * 80)
        p(' Section 5: Current Sessions')
        p('=' * 80)
        p('')
        if not sessions:
            p('  ⚠️  No session data retrieved')
            p('')
        else:
            p(f'  {"Node ID":<26}{"Total":<10}{"Active":<8}{"Longest(s)":<12}{"Status"}')
            p('  ' + '─' * 60)
            for nid, s in sessions.items():
                total = s.get('total', 0)
                active = s.get('active', 0)
                longest = s.get('longest_secs', 0)
                if longest > 300:
                    icon = '🔴'
                elif longest > 60 or active > 50:
                    icon = '🟡'
                else:
                    icon = '🟢'
                p(f'  {nid:<26}{str(total):<10}{str(active):<8}{str(longest):<12}{icon}')
            p('')
            for nid, s in sessions.items():
                long_ones = [ss for ss in s.get('session_list', []) if int(ss.get('SecsRunning', 0) or 0) > 10]
                if not long_ones:
                    continue
                p(f'  ▸ {nid} Long-running sessions ({len(long_ones)}):')
                for ss in sorted(long_ones, key=lambda x: int(x.get('SecsRunning', 0) or 0), reverse=True)[:10]:
                    p(f'    - {ss.get("Op",""):<10} {int(ss.get("SecsRunning",0) or 0)}s  '
                      f'{ss.get("Ns","")[:30]}  {ss.get("Client","")[:25]}  {short(ss.get("Desc",""), 40)}')
                p('')

    # Section 6: Slowlog
    if 'slowlog' in _INSPECT_ITEMS:
        slow_logs = report.get('slowlog') or []
        total_slow = sum(sl.get('total', 0) for sl in slow_logs)
        p('=' * 80)
        p(f' Section 6: Slow Query Statistics (Last {days} Days)')
        p('=' * 80)
        p('')
        p(f'  Total {total_slow} slow query records')
        p('')
        for sl in slow_logs:
            if not sl.get('records'):
                continue
            p(f'  ▸ {sl["node_id"]} ({sl["total"]} records)')
            p(f'  {"#":<4}{"Database":<14}{"Time(ms)":<12}{"Timestamp":<22}{"Operation"}')
            p('  ' + '─' * 90)
            for i, rec in enumerate(sl['records'][:10], 1):
                p(f'  {i:<4}{(rec.get("DBName","") or "")[:12]:<14}'
                  f'{str(rec.get("QueryTimes","")):<12}'
                  f'{(rec.get("ExecutionStartTime","") or "")[:20]:<22}'
                  f'{short(rec.get("SQLText",""), 60)}')
            p('')

    # Section 7: Alert
    if 'alert' in _INSPECT_ITEMS:
        alert = report.get('alert') or {}
        p('=' * 80)
        p(f' Section 7: Alert History (Last {days} Days)')
        p('=' * 80)
        p('')
        if not alert.get('available'):
            p(f'  ⚠️  Not supported / data unavailable: {alert.get("reason","")}')
            p('')
        else:
            recs = alert.get('records', []) or []
            if not recs:
                p('  ✅ No recent alert events')
            else:
                p(f'  Total {len(recs)} alert records')
                p('')
                p(f'  {"#":<4}{"Time":<22}{"Level":<10}{"Metric":<22}{"Description"}')
                p('  ' + '─' * 90)
                for i, r in enumerate(recs[:30], 1):
                    p(f'  {i:<4}{(r.get("time","") or "")[:20]:<22}'
                      f'{(r.get("level","") or "")[:8]:<10}'
                      f'{(r.get("metric","") or "")[:20]:<22}'
                      f'{short(r.get("message",""), 50)}')
            p('')

    # Section 8: Suggestions
    p('=' * 80)
    p(' Section 8: Inspection Conclusions & Recommendations')
    p('=' * 80)
    p('')
    sug = report.get('suggestions') or []
    if not sug:
        p('  ✅ No significant issues found, instance is running normally.')
    else:
        for level, msg in sug:
            icon = {'danger': '🔴', 'warn': '🟡', 'info': '🔵'}.get(level, '🔵')
            p(f'  {icon} {msg}')
    p('')
    p('┌' + '─' * 78 + '┐')
    p('│' + 'Inspection Complete'.center(76) + '│')
    p('└' + '─' * 78 + '┘')
    return '\n'.join(L)


# ─── Render: Markdown ────────────────────────────────────────────────────────


def render_markdown(report):
    L = []
    p = L.append

    info = report['info']
    instance_id = report['instance_id']
    region = report['region']
    inspect_time = report['inspect_time']
    days = report['days']
    instance_type = info.get('DBInstanceType', '')
    type_label = {'sharding': 'Sharding Cluster', 'replicate': 'ReplicaSet'}.get(instance_type, instance_type)
    charge_label = {'PostPaid': 'Pay-As-You-Go', 'PrePaid': 'Subscription'}.get(info.get('ChargeType', ''), info.get('ChargeType', ''))

    p(f'# MongoDB (DDS) Instance Health Inspection Report')
    p('')
    p(f'- **Inspect Time**: {inspect_time}')
    p(f'- **Instance ID**: {instance_id}')
    p(f'- **Region**: {region}')
    p(f'- **Inspect Period**: {report["start_time"]} ~ {report["end_time"]}')
    p('')

    is_full = _INSPECT_ITEMS == set(ALL_ITEMS)
    if is_full:
        p('## Section 1: Instance Basic Info')
        p('')
        p('| Item | Value |')
        p('|------|------|')
        p(f'| Instance Type | {type_label} |')
        p(f'| Major Version | MongoDB {info.get("EngineVersion","")} |')
        p(f'| Kernel Version | {info.get("CurrentKernelVersion","")} |')
        p(f'| Storage Engine | {info.get("StorageEngine","")} |')
        p(f'| Storage Type | {info.get("StorageType","")} |')
        p(f'| Billing | {charge_label} |')
        p(f'| Status | {info.get("DBInstanceStatus","")} |')
        p(f'| Created At | {info.get("CreationTime","")} |')
        p(f'| Max Connections | {info.get("MaxConnections","N/A")} |')
        p(f'| Max IOPS | {info.get("MaxIOPS","N/A")} |')
        p('')

        shards, mongos, cs = collect_node_ids(info)
        if mongos:
            p('### Mongos Nodes')
            p('')
            p('| Node ID | Spec | Max Connections | Status |')
            p('|---------|------|----------|------|')
            for m in mongos:
                p(f'| {m.get("NodeId","")} | {m.get("NodeClass","")} | {m.get("MaxConnections","")} | {m.get("Status","")} |')
            p('')
        if shards:
            p('### Shard Nodes')
            p('')
            p('| Node ID | Spec | Storage(GB) | Max Connections | Max IOPS | Status |')
            p('|---------|------|---------|----------|----------|------|')
            for s in shards:
                p(f'| {s.get("NodeId","")} | {s.get("NodeClass","")} | {s.get("NodeStorage","")} | {s.get("MaxConnections","")} | {s.get("MaxIOPS","")} | {s.get("Status","")} |')
            p('')
        if cs:
            p('### ConfigServer Nodes')
            p('')
            p('| Node ID | Spec | Storage(GB) | Status |')
            p('|---------|------|---------|------|')
            for c in cs:
                p(f'| {c.get("NodeId","")} | {c.get("NodeClass","")} | {c.get("NodeStorage","")} | {c.get("Status","")} |')
            p('')

    if 'config' in _INSPECT_ITEMS and report.get('config'):
        cfg = report['config']
        p('## Section 2: Configuration Risk Assessment')
        p('')
        icon_map = {'danger': '🔴', 'warn': '🟡', 'info': '🔵', 'normal': '🟢'}
        p('| Level | Category | Description | Current Value |')
        p('|------|------|------|--------|')
        for cat, level, msg, val in cfg.get('items', []) or []:
            icon = icon_map.get(level, '🔵')
            p(f'| {icon} {level} | {cat} | {msg} | {val} |')
        overall_icon = icon_map.get(cfg.get('overall', 'info'), '🔵')
        p('')
        p(f'> **Overall Config Risk**: {overall_icon} {cfg.get("overall", "info").upper()}')
        p('')

    if 'resource' in _INSPECT_ITEMS and report.get('resource'):
        res = report['resource']
        metrics = res['metrics']
        timeseries = res.get('timeseries') or {}
        p(f'## Section 3: Resource Usage (Last {days} Days)')
        p('')
        if res['shard_ids']:
            p('### Shard Node Monitoring')
            p('')
            for nid in res['shard_ids']:
                m = metrics.get(nid) or {}
                if not m:
                    continue
                shard_info = next((s for s in res['shards'] if s.get('NodeId') == nid), {})
                max_conn = int(shard_info.get('MaxConnections', 0) or 0)
                cpu_a, cpu_p = m.get('cpu', (0, 0))
                mem_a, mem_p = m.get('memory', (0, 0))
                conn_a, conn_p = m.get('connections', (0, 0))
                disk_a, disk_p = m.get('disk_usage', (0, 0))
                iops_a, iops_p = m.get('iops_usage', (0, 0))
                mbps_a, mbps_p = m.get('mbps_0', (0, 0))
                conn_pct_a = (conn_a / max_conn * 100) if max_conn else 0
                conn_pct_p = (conn_p / max_conn * 100) if max_conn else 0
                p(f'#### {nid}')
                p('')
                p('| Metric | Average | Peak | Status |')
                p('|------|--------|------|------|')
                p(f'| CPU Usage | {cpu_a}% | {cpu_p}% | {status_icon(cpu_p)} |')
                p(f'| Memory Usage | {mem_a}% | {mem_p}% | {status_icon(mem_p)} |')
                p(f'| Connection Usage | {conn_a:.0f}/{max_conn} ({conn_pct_a:.1f}%) | {conn_p:.0f}/{max_conn} ({conn_pct_p:.1f}%) | {status_icon(conn_pct_p)} |')
                p(f'| Disk Usage | {disk_a}% | {disk_p}% | {status_icon(disk_p, 70, 85)} |')
                p(f'| IOPS Usage | {iops_a}% | {iops_p}% | {status_icon(iops_p)} |')
                p(f'| Disk Bandwidth Usage | {mbps_a}% | {mbps_p}% | {status_icon(mbps_p)} |')
                p('')
                # Monitoring trend sparkline (Unicode)
                node_ts = timeseries.get(nid) or {}
                trend_rows = [
                    ('CPU', node_ts.get('cpu') or []),
                    ('Mem', node_ts.get('memory') or []),
                    ('Conn', node_ts.get('connections') or []),
                    ('IOPS', node_ts.get('iops_usage') or []),
                ]
                trend_lines = [(lbl, sparkline(pts)) for lbl, pts in trend_rows if pts]
                if trend_lines:
                    p(f'**{nid} Monitoring Trend (Last {days} Days)**')
                    p('')
                    p('```')
                    for lbl, line in trend_lines:
                        p(f'{lbl:<6} {line}')
                    p('```')
                    p('')
                ops_labels = ['insert', 'query', 'update', 'delete', 'getmore', 'command']
                p('Opcounters (avg/peak):')
                for i, lbl in enumerate(ops_labels):
                    a, q = m.get(f'ops_{i}', (0, 0))
                    p(f'- {lbl}: {a:.1f} / {q:.1f}')
                p('')
        if res['mongos_ids']:
            p('### Mongos Node Monitoring')
            p('')
            p('| Node ID | CPU Avg | CPU Peak | Conn Avg | Conn Peak | Status |')
            p('|---------|---------|---------|---------|---------|------|')
            for nid in res['mongos_ids']:
                m = metrics.get(nid) or {}
                if not m:
                    continue
                cpu_a, cpu_p = m.get('cpu', (0, 0))
                conn_a, conn_p = m.get('connections', (0, 0))
                p(f'| {nid} | {cpu_a}% | {cpu_p}% | {conn_a:.0f} | {conn_p:.0f} | {status_icon(cpu_p)} |')
            p('')

    if 'space' in _INSPECT_ITEMS:
        sp = report.get('space') or {}
        p('## Section 4: Storage Usage Details TOP20')
        p('')
        if not sp.get('available'):
            p(f'> ⚠️ Not supported / data unavailable: {sp.get("reason","")}')
            p('')
        else:
            top = sp.get('top20', []) or []
            if not top:
                p('No collection data available')
            else:
                p('| # | Database | Collection | Total Size | Data | Index | Doc Count |')
                p('|---|--------|-----------|--------|------|------|-------|')
                for i, c in enumerate(top, 1):
                    p(f'| {i} | {c["db"]} | {c["collection"]} | {format_size_mb(c["total_size"])} | {format_size_mb(c["data_size"])} | {format_size_mb(c["index_size"])} | {c["count"]} |')
                p('')
                p(f'> Total space used: {format_size_mb(sp.get("total_used", 0))}')
            p('')

    if 'session' in _INSPECT_ITEMS:
        sessions = report.get('session') or {}
        p('## Section 5: Current Sessions')
        p('')
        if not sessions:
            p('> ⚠️ No session data retrieved')
            p('')
        else:
            p('| Node ID | Total | Active | Longest(s) | Status |')
            p('|---------|--------|------|--------|------|')
            for nid, s in sessions.items():
                longest = s.get('longest_secs', 0)
                active = s.get('active', 0)
                if longest > 300:
                    icon = '🔴'
                elif longest > 60 or active > 50:
                    icon = '🟡'
                else:
                    icon = '🟢'
                p(f'| {nid} | {s.get("total",0)} | {active} | {longest} | {icon} |')
            p('')

    if 'slowlog' in _INSPECT_ITEMS:
        slow_logs = report.get('slowlog') or []
        total_slow = sum(sl.get('total', 0) for sl in slow_logs)
        p(f'## Section 6: Slow Query Statistics (Last {days} Days)')
        p('')
        p(f'Total **{total_slow}** slow query records')
        p('')
        for sl in slow_logs:
            if not sl.get('records'):
                continue
            p(f'### {sl["node_id"]} ({sl["total"]} records)')
            p('')
            p('| # | Database | Time(ms) | Timestamp | Operation |')
            p('|---|--------|---------|------|------|')
            for i, rec in enumerate(sl['records'][:10], 1):
                sqltext = (rec.get('SQLText', '') or '').replace('|', '\\|').replace('\n', ' ')
                p(f'| {i} | {rec.get("DBName","")} | {rec.get("QueryTimes","")} | {rec.get("ExecutionStartTime","")} | `{short(sqltext, 80)}` |')
            p('')

    if 'alert' in _INSPECT_ITEMS:
        alert = report.get('alert') or {}
        p(f'## Section 7: Alert History (Last {days} Days)')
        p('')
        if not alert.get('available'):
            p(f'> ⚠️ Not supported / data unavailable: {alert.get("reason","")}')
            p('')
        else:
            recs = alert.get('records', []) or []
            if not recs:
                p('✅ No recent alert events')
                p('')
            else:
                p(f'Total **{len(recs)}** alerts')
                p('')
                p('| # | Time | Level | Metric | Description |')
                p('|---|------|------|------|------|')
                for i, r in enumerate(recs[:30], 1):
                    p(f'| {i} | {r.get("time","")} | {r.get("level","")} | {r.get("metric","")} | {short(r.get("message",""), 80)} |')
                p('')

    p('## Section 8: Inspection Conclusions & Recommendations')
    p('')
    sug = report.get('suggestions') or []
    if not sug:
        p('✅ No significant issues found, instance is running normally.')
    else:
        for level, msg in sug:
            icon = {'danger': '🔴', 'warn': '🟡', 'info': '🔵'}.get(level, '🔵')
            p(f'- {icon} {msg}')
    p('')
    return '\n'.join(L)



# ─── Render: HTML ────────────────────────────────────────────────────────────


_HTML_HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>MongoDB (DDS) Health Inspection Report - {instance_id}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f5f5f5; padding:1.5rem; color:#333; }}
.container {{ max-width:1400px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg, #047857, #10b981); color:white; padding:1.5rem 2rem; border-radius:10px; margin-bottom:20px; }}
.header h1 {{ font-size:1.4rem; margin-bottom:6px; }}
.header .meta {{ font-size:0.85rem; opacity:0.9; line-height:1.6; }}
.section {{ background:#fff; border-radius:8px; padding:1.5rem; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
.section h2 {{ font-size:1.15rem; padding-bottom:10px; border-bottom:2px solid #10b981; margin-bottom:16px; color:#065f46; }}
.section h3 {{ font-size:1rem; margin:14px 0 10px; color:#047857; }}
.basic-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px 24px; }}
.basic-item {{ display:flex; padding:6px 0; font-size:0.9rem; border-bottom:1px dashed #e5e7eb; }}
.basic-key {{ color:#6b7280; min-width:8em; }}
.basic-val {{ color:#111; font-weight:500; word-break:break-all; }}
table {{ width:100%; border-collapse:collapse; font-size:0.85rem; margin-bottom:10px; }}
table th, table td {{ padding:6px 10px; text-align:left; border-bottom:1px solid #e5e7eb; }}
table th {{ background:#f0fdf4; font-weight:600; color:#065f46; }}
.metric-table {{ overflow-x:auto; }}
.metric-table table {{ min-width:600px; }}
.metric-cell {{ font-family:monospace; }}
.icon-cell {{ text-align:center; font-size:1.05rem; }}
.danger {{ color:#dc2626; font-weight:600; }}
.warn {{ color:#d97706; font-weight:600; }}
.normal {{ color:#059669; }}
.charts-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.chart-card {{ background:#fafafa; border:1px solid #e5e7eb; border-radius:6px; padding:8px 6px; }}
.chart-title {{ font-size:0.8rem; color:#6b7280; padding:0 8px 4px; }}
.chart-box {{ width:100%; height:260px; }}
.sql-cell {{ max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer; font-family:monospace; font-size:0.8rem; }}
.sug-list li {{ list-style:none; padding:6px 0; font-size:0.9rem; }}
.sug-danger {{ color:#dc2626; }}
.sug-warn {{ color:#d97706; }}
.sug-info {{ color:#0284c7; }}
.unavailable {{ color:#9ca3af; font-style:italic; padding:8px 0; }}
</style>
</head>
<body>
<div class="container">
'''


def _metric_class(value, warn=60, danger=80):
    if value > danger:
        return 'danger'
    if value > warn:
        return 'warn'
    return 'normal'


def _node_metric_table_html(node_ids, metrics, node_attrs, role):
    """Generate horizontal comparison table: node columns, metric rows"""
    if not node_ids:
        return ''
    rows = []
    cols = []
    for nid in node_ids:
        m = metrics.get(nid) or {}
        attr = next((n for n in node_attrs if n.get('NodeId') == nid), {})
        max_conn = int(attr.get('MaxConnections', 0) or 0)
        cpu_a, cpu_p = m.get('cpu', (0, 0))
        mem_a, mem_p = m.get('memory', (0, 0))
        conn_a, conn_p = m.get('connections', (0, 0))
        disk_a, disk_p = m.get('disk_usage', (0, 0))
        iops_a, iops_p = m.get('iops_usage', (0, 0))
        mbps_a, mbps_p = m.get('mbps_0', (0, 0))
        ops_a, ops_p = m.get('ops_0', (0, 0))
        conn_pct_p = (conn_p / max_conn * 100) if max_conn else 0
        cols.append({
            'nid': nid, 'class': attr.get('NodeClass', ''),
            'cpu_a': cpu_a, 'cpu_p': cpu_p,
            'mem_a': mem_a, 'mem_p': mem_p,
            'conn_a': conn_a, 'conn_p': conn_p, 'max_conn': max_conn, 'conn_pct_p': conn_pct_p,
            'disk_a': disk_a, 'disk_p': disk_p,
            'iops_a': iops_a, 'iops_p': iops_p,
            'mbps_a': mbps_a, 'mbps_p': mbps_p,
            'ops_a': ops_a, 'ops_p': ops_p,
        })
    head = '<tr><th>Metric</th>' + ''.join(f'<th>{he(c["nid"])}<br><span style="font-weight:400;color:#6b7280">{he(c["class"])}</span></th>' for c in cols) + '</tr>'

    def _row(label, fmt_fn, peak_fn, warn=60, danger=80):
        cells = []
        for c in cols:
            avg, peak = fmt_fn(c)
            cls = _metric_class(peak_fn(c), warn, danger)
            cells.append(f'<td class="metric-cell {cls}">{avg} / {peak}</td>')
        return f'<tr><td>{label}</td>' + ''.join(cells) + '</tr>'

    rows.append(_row('CPU Usage', lambda c: (f'{c["cpu_a"]}%', f'{c["cpu_p"]}%'), lambda c: c['cpu_p']))
    if role != 'mongos':
        rows.append(_row('Memory Usage', lambda c: (f'{c["mem_a"]}%', f'{c["mem_p"]}%'), lambda c: c['mem_p']))
    rows.append(_row('Connections', lambda c: (f'{c["conn_a"]:.0f}', f'{c["conn_p"]:.0f}'), lambda c: c['conn_pct_p']))
    if role != 'mongos':
        rows.append(_row('Disk Usage', lambda c: (f'{c["disk_a"]}%', f'{c["disk_p"]}%'), lambda c: c['disk_p'], 70, 85))
        rows.append(_row('IOPS Usage', lambda c: (f'{c["iops_a"]}%', f'{c["iops_p"]}%'), lambda c: c['iops_p']))
        rows.append(_row('Disk Bandwidth', lambda c: (f'{c["mbps_a"]}%', f'{c["mbps_p"]}%'), lambda c: c['mbps_p']))
        rows.append(_row('Opcounters', lambda c: (f'{c["ops_a"]:.0f}', f'{c["ops_p"]:.0f}'), lambda c: 0, 999999, 999999))

    # Status row
    icon_cells = []
    for c in cols:
        worst = max(c['cpu_p'], c['mem_p'], c['conn_pct_p'], c['iops_p'], c['mbps_p'])
        worst_disk = c['disk_p']
        if worst > 80 or worst_disk > 85:
            icon = '🔴'
        elif worst > 60 or worst_disk > 70:
            icon = '🟡'
        else:
            icon = '🟢'
        icon_cells.append(f'<td class="icon-cell">{icon}</td>')
    rows.append('<tr><td><b>Status</b></td>' + ''.join(icon_cells) + '</tr>')

    return f'<div class="metric-table"><table><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def _build_chart_data(node_ids, timeseries, ts_key):
    """Build ECharts series + time point collection"""
    series = []
    legend = []
    for nid in node_ids:
        ts = (timeseries.get(nid) or {}).get(ts_key) or []
        data = [[t, v] for t, v in ts]
        series.append({'name': nid, 'type': 'line', 'symbol': 'none', 'smooth': True,
                       'lineStyle': {'width': 1.5}, 'data': data})
        legend.append(nid)
    return series, legend


_CHART_TPL = '''
<div class="chart-card">
  <div class="chart-title">{title}</div>
  <div class="chart-box" id="{cid}"></div>
</div>
<script>
(function(){{
  var chart = echarts.init(document.getElementById('{cid}'));
  chart.setOption({{
    tooltip: {{ trigger:'axis' }},
    legend: {{ data: {legend}, top:0, type:'scroll', textStyle:{{fontSize:10}} }},
    grid: {{ left:45, right:15, top:30, bottom:55 }},
    xAxis: {{ type:'time', axisLabel:{{fontSize:10, formatter:'{{MM}}-{{dd}} {{HH}}:{{mm}}'}} }},
    yAxis: {{ type:'value', max:{ymax}, axisLabel:{{fontSize:10}} }},
    dataZoom: [
      {{type:'inside'}},
      {{type:'slider', height:20, bottom:5}}
    ],
    series: {series}
  }});
  if(!window._chartGroup_{group}) window._chartGroup_{group}=[];
  window._chartGroup_{group}.push(chart);
  window.addEventListener('resize', function(){{ chart.resize(); }});
}})();
</script>
'''


def _render_chart_group(group_id, charts):
    """charts: [(title, ts_key, ymax, node_ids, timeseries), ...]"""
    parts = []
    parts.append('<div class="charts-grid">')
    for i, (title, ts_key, ymax, node_ids, ts) in enumerate(charts):
        cid = f'chart_{group_id}_{i}'
        series, legend = _build_chart_data(node_ids, ts, ts_key)
        parts.append(_CHART_TPL.format(
            title=he(title), cid=cid, group=group_id,
            legend=json.dumps(legend, ensure_ascii=False),
            series=json.dumps(series, ensure_ascii=False),
            ymax='100' if ymax == 100 else 'null',
        ))
    parts.append('</div>')
    parts.append(f'''<script>
(function(){{
  setTimeout(function(){{
    var arr = window._chartGroup_{group_id} || [];
    if (arr.length>1) echarts.connect(arr);
  }}, 100);
}})();
</script>''')
    return ''.join(parts)


def render_html(report):
    info = report['info']
    instance_id = report['instance_id']
    region = report['region']
    inspect_time = report['inspect_time']
    days = report['days']
    instance_type = info.get('DBInstanceType', '')
    type_label = {'sharding': 'Sharding Cluster', 'replicate': 'ReplicaSet'}.get(instance_type, instance_type)

    out = []
    out.append(_HTML_HEAD.format(instance_id=he(instance_id)))
    out.append(f'''
<div class="header">
  <h1>MongoDB (DDS) Instance Health Inspection Report</h1>
  <div class="meta">
    Inspect Time: {he(inspect_time)} &nbsp;|&nbsp; Instance ID: <b>{he(instance_id)}</b> &nbsp;|&nbsp; Region: {he(region)}<br>
    Inspect Period: {he(report["start_time"])} ~ {he(report["end_time"])} &nbsp;|&nbsp; Type: {he(type_label)}
  </div>
</div>
''')

    # Section 1: Basic -- only show when full inspection
    is_full = _INSPECT_ITEMS == set(ALL_ITEMS)
    shards, mongos, cs = collect_node_ids(info)
    if is_full:
        basic = [
            ('Instance Type', type_label),
            ('Major Version', f'MongoDB {info.get("EngineVersion","")}'),
            ('Kernel Version', info.get('CurrentKernelVersion', '')),
            ('Storage Engine', info.get('StorageEngine', '')),
            ('Storage Type', info.get('StorageType', '')),
            ('Billing', {'PostPaid': 'Pay-As-You-Go', 'PrePaid': 'Subscription'}.get(info.get('ChargeType', ''), info.get('ChargeType', ''))),
            ('Status', info.get('DBInstanceStatus', '')),
            ('Created At', info.get('CreationTime', '')),
            ('Max Connections', info.get('MaxConnections', 'N/A')),
            ('Max IOPS', info.get('MaxIOPS', 'N/A')),
            ('VPC ID', info.get('VPCId', '')),
            ('Zone', info.get('ZoneId', '')),
        ]
        items_html = ''.join(f'<div class="basic-item"><span class="basic-key">{he(k)}</span><span class="basic-val">{he(v)}</span></div>' for k, v in basic if v)
        out.append(f'<div class="section"><h2>Section 1: Instance Basic Info</h2><div class="basic-grid">{items_html}</div>')
        if mongos:
            out.append('<h3>Mongos Nodes</h3><table><thead><tr><th>Node ID</th><th>Spec</th><th>Max Conn</th><th>Status</th></tr></thead><tbody>')
            for m in mongos:
                out.append(f'<tr><td>{he(m.get("NodeId",""))}</td><td>{he(m.get("NodeClass",""))}</td><td>{he(m.get("MaxConnections",""))}</td><td>{he(m.get("Status",""))}</td></tr>')
            out.append('</tbody></table>')
        if shards:
            out.append('<h3>Shard Nodes</h3><table><thead><tr><th>Node ID</th><th>Spec</th><th>Storage(GB)</th><th>Max Conn</th><th>Max IOPS</th><th>Status</th></tr></thead><tbody>')
            for s in shards:
                out.append(f'<tr><td>{he(s.get("NodeId",""))}</td><td>{he(s.get("NodeClass",""))}</td><td>{he(s.get("NodeStorage",""))}</td><td>{he(s.get("MaxConnections",""))}</td><td>{he(s.get("MaxIOPS",""))}</td><td>{he(s.get("Status",""))}</td></tr>')
            out.append('</tbody></table>')
        if cs:
            out.append('<h3>ConfigServer Nodes</h3><table><thead><tr><th>Node ID</th><th>Spec</th><th>Storage(GB)</th><th>Status</th></tr></thead><tbody>')
            for c in cs:
                out.append(f'<tr><td>{he(c.get("NodeId",""))}</td><td>{he(c.get("NodeClass",""))}</td><td>{he(c.get("NodeStorage",""))}</td><td>{he(c.get("Status",""))}</td></tr>')
            out.append('</tbody></table>')
        out.append('</div>')

    # Section 2: Config Risk
    if 'config' in _INSPECT_ITEMS and report.get('config'):
        cfg = report['config']
        out.append('<div class="section"><h2>Section 2: Configuration Risk Assessment</h2>')
        icon_map = {'danger': '🔴', 'warn': '🟡', 'info': '🔵', 'normal': '🟢'}
        out.append('<table><thead><tr><th>Level</th><th>Category</th><th>Description</th><th>Current Value</th></tr></thead><tbody>')
        for cat, level, msg, val in cfg.get('items', []) or []:
            icon = icon_map.get(level, '🔵')
            out.append(f'<tr><td class="icon-cell">{icon} {he(level)}</td><td>{he(cat)}</td><td>{he(msg)}</td><td>{he(val)}</td></tr>')
        out.append('</tbody></table>')
        overall = cfg.get('overall', 'info')
        overall_icon = icon_map.get(overall, '🔵')
        out.append(f'<div style="margin-top:10px;font-weight:600">Overall Config Risk: {overall_icon} {he(overall.upper())}</div>')
        out.append('</div>')

    # Section 3: Resource
    if 'resource' in _INSPECT_ITEMS and report.get('resource'):
        res = report['resource']
        metrics = res['metrics']
        timeseries = res['timeseries']
        shard_ids = res['shard_ids']
        mongos_ids = res['mongos_ids']
        out.append(f'<div class="section"><h2>Section 3: Resource Usage (Last {days} Days)</h2>')
        if shard_ids:
            out.append('<h3>Shard Node Comparison</h3>')
            out.append(_node_metric_table_html(shard_ids, metrics, res['shards'], 'shard'))
            out.append('<h3>Shard Monitoring Trend</h3>')
            out.append(_render_chart_group('shard', [
                ('CPU Usage (%)', 'cpu', 100, shard_ids, timeseries),
                ('Memory Usage (%)', 'memory', 100, shard_ids, timeseries),
                ('Connections (Absolute)', 'connections', None, shard_ids, timeseries),
                ('IOPS Usage (%)', 'iops_usage', 100, shard_ids, timeseries),
                ('Opcounters (ops/s)', 'ops', None, shard_ids, timeseries),
            ]))
        if mongos_ids:
            out.append('<h3>Mongos Node Comparison</h3>')
            out.append(_node_metric_table_html(mongos_ids, metrics, mongos, 'mongos'))
            out.append('<h3>Mongos Monitoring Trend</h3>')
            out.append(_render_chart_group('mongos', [
                ('CPU Usage (%)', 'cpu', 100, mongos_ids, timeseries),
                ('Connections (Absolute)', 'connections', None, mongos_ids, timeseries),
            ]))
        out.append('</div>')

    # Section 4: Space
    if 'space' in _INSPECT_ITEMS:
        sp = report.get('space') or {}
        out.append('<div class="section"><h2>Section 4: Storage Usage Details TOP20</h2>')
        if not sp.get('available'):
            out.append(f'<div class="unavailable">⚠️ Not supported / data unavailable: {he(sp.get("reason",""))}</div>')
        else:
            top = sp.get('top20', []) or []
            if not top:
                out.append('<div class="unavailable">No collection data available</div>')
            else:
                out.append('<table><thead><tr><th>#</th><th>Database</th><th>Collection</th><th>Total Size</th><th>Data</th><th>Index</th><th>Doc Count</th></tr></thead><tbody>')
                for i, c in enumerate(top, 1):
                    out.append(f'<tr><td>{i}</td><td>{he(c["db"])}</td><td>{he(c["collection"])}</td><td>{format_size_mb(c["total_size"])}</td><td>{format_size_mb(c["data_size"])}</td><td>{format_size_mb(c["index_size"])}</td><td>{c["count"]}</td></tr>')
                out.append('</tbody></table>')
                out.append(f'<div style="margin-top:8px;color:#6b7280;font-size:0.85rem">Total space used: {format_size_mb(sp.get("total_used", 0))}</div>')
        out.append('</div>')

    # Section 5: Session
    if 'session' in _INSPECT_ITEMS:
        sessions = report.get('session') or {}
        out.append('<div class="section"><h2>Section 5: Current Sessions</h2>')
        if not sessions:
            out.append('<div class="unavailable">⚠️ No session data retrieved</div>')
        else:
            out.append('<table><thead><tr><th>Node ID</th><th>Total</th><th>Active</th><th>Longest(s)</th><th>Status</th></tr></thead><tbody>')
            for nid, s in sessions.items():
                longest = s.get('longest_secs', 0)
                active = s.get('active', 0)
                if longest > 300:
                    icon = '🔴'
                elif longest > 60 or active > 50:
                    icon = '🟡'
                else:
                    icon = '🟢'
                out.append(f'<tr><td>{he(nid)}</td><td>{s.get("total",0)}</td><td>{active}</td><td>{longest}</td><td class="icon-cell">{icon}</td></tr>')
            out.append('</tbody></table>')
            for nid, s in sessions.items():
                long_ones = [ss for ss in s.get('session_list', []) if int(ss.get('SecsRunning', 0) or 0) > 10]
                if not long_ones:
                    continue
                out.append(f'<h3>{he(nid)} Long-running Sessions ({len(long_ones)})</h3>')
                out.append('<table><thead><tr><th>Operation</th><th>Runtime(s)</th><th>Namespace</th><th>Client</th><th>Description</th></tr></thead><tbody>')
                for ss in sorted(long_ones, key=lambda x: int(x.get('SecsRunning', 0) or 0), reverse=True)[:20]:
                    desc_full = he(ss.get('Desc', ''))
                    out.append(f'<tr><td>{he(ss.get("Op",""))}</td><td>{int(ss.get("SecsRunning",0) or 0)}</td><td>{he(ss.get("Ns",""))}</td><td>{he(ss.get("Client",""))}</td><td class="sql-cell" title="{desc_full}">{desc_full}</td></tr>')
                out.append('</tbody></table>')
        out.append('</div>')

    # Section 6: Slowlog
    if 'slowlog' in _INSPECT_ITEMS:
        slow_logs = report.get('slowlog') or []
        total_slow = sum(sl.get('total', 0) for sl in slow_logs)
        out.append(f'<div class="section"><h2>Section 6: Slow Query Statistics (Last {days} Days)</h2>')
        out.append(f'<div style="margin-bottom:12px;color:#6b7280">Total <b>{total_slow}</b> slow query records</div>')

        # Aggregate by query pattern across all nodes
        all_records = []
        for sl in slow_logs:
            all_records.extend(sl.get('records') or [])
        if all_records:
            pattern_map = {}
            for rec in all_records:
                sql = (rec.get('SQLText', '') or '')[:200]
                db = rec.get('DBName', '') or ''
                key = f'{db}::{sql}'
                if key not in pattern_map:
                    pattern_map[key] = {'db': db, 'sql': sql, 'count': 0, 'total_ms': 0, 'max_ms': 0}
                pattern_map[key]['count'] += 1
                qt = int(rec.get('QueryTimes', 0) or 0)
                pattern_map[key]['total_ms'] += qt
                if qt > pattern_map[key]['max_ms']:
                    pattern_map[key]['max_ms'] = qt
            patterns = sorted(pattern_map.values(), key=lambda p: p['count'], reverse=True)
            out.append('<h3>Query Pattern Aggregation (By Frequency)</h3>')
            out.append('<table><thead><tr><th>#</th><th>Database</th><th>Count</th><th>Max Time(ms)</th><th>Avg Time(ms)</th><th>Query Pattern</th></tr></thead><tbody>')
            for i, p in enumerate(patterns[:20], 1):
                avg_ms = p['total_ms'] // p['count'] if p['count'] else 0
                highlight = ' style="background:#fef2f2"' if p['count'] >= 10 or p['max_ms'] >= 1000 else ''
                out.append(f'<tr{highlight}><td>{i}</td><td>{he(p["db"])}</td><td><b>{p["count"]}</b></td><td>{p["max_ms"]}</td><td>{avg_ms}</td><td class="sql-cell" title="{he(p["sql"])}">{he(p["sql"])}</td></tr>')
            out.append('</tbody></table>')

        # Per-node detail (sorted by execution time desc)
        for sl in slow_logs:
            if not sl.get('records'):
                continue
            sorted_recs = sorted(sl['records'], key=lambda r: int(r.get('QueryTimes', 0) or 0), reverse=True)
            out.append(f'<h3>{he(sl["node_id"])} ({sl["total"]} records)</h3>')
            out.append('<table><thead><tr><th>#</th><th>Database</th><th>Time(ms)</th><th>Timestamp</th><th>Operation (hover for full text)</th></tr></thead><tbody>')
            for i, rec in enumerate(sorted_recs[:20], 1):
                sqltext = rec.get('SQLText', '') or ''
                out.append(f'<tr><td>{i}</td><td>{he(rec.get("DBName",""))}</td><td>{he(rec.get("QueryTimes",""))}</td><td>{he(rec.get("ExecutionStartTime",""))}</td><td class="sql-cell" title="{he(sqltext)}">{he(sqltext)}</td></tr>')
            out.append('</tbody></table>')
        out.append('</div>')

    # Section 7: Alert
    if 'alert' in _INSPECT_ITEMS:
        alert = report.get('alert') or {}
        out.append(f'<div class="section"><h2>Section 7: Alert History (Last {days} Days)</h2>')
        if not alert.get('available'):
            out.append(f'<div class="unavailable">⚠️ Not supported / data unavailable: {he(alert.get("reason",""))}</div>')
        else:
            recs = alert.get('records', []) or []
            if not recs:
                out.append('<div class="unavailable">✅ No recent alert events</div>')
            else:
                out.append(f'<div style="margin-bottom:12px">Total <b>{len(recs)}</b> alerts</div>')
                out.append('<table><thead><tr><th>#</th><th>Time</th><th>Level</th><th>Metric</th><th>Description</th></tr></thead><tbody>')
                for i, r in enumerate(recs[:50], 1):
                    out.append(f'<tr><td>{i}</td><td>{he(r.get("time",""))}</td><td>{he(r.get("level",""))}</td><td>{he(r.get("metric",""))}</td><td>{he(short(r.get("message",""), 200))}</td></tr>')
                out.append('</tbody></table>')
        out.append('</div>')

    # Section 8: Suggestions
    out.append('<div class="section"><h2>Section 8: Inspection Conclusions & Recommendations</h2>')
    sug = report.get('suggestions') or []
    if not sug:
        out.append('<div class="normal">✅ No significant issues found, instance is running normally.</div>')
    else:
        out.append('<ul class="sug-list">')
        for level, msg in sug:
            cls = {'danger': 'sug-danger', 'warn': 'sug-warn', 'info': 'sug-info'}.get(level, 'sug-info')
            icon = {'danger': '🔴', 'warn': '🟡', 'info': '🔵'}.get(level, '🔵')
            out.append(f'<li class="{cls}">{icon} {he(msg)}</li>')
        out.append('</ul>')
    out.append('</div>')

    out.append('</div></body></html>')
    return ''.join(out)


# ─── Render: Summary HTML (multi-instance) ───────────────────────────────────


def render_summary_html(summaries, output_dir, inspect_time):
    def _level(s):
        if s.get('error'):
            return 'error'
        for lv, _ in s.get('suggestions', []):
            if lv == 'danger':
                return 'danger'
        for lv, _ in s.get('suggestions', []):
            if lv == 'warn':
                return 'warn'
        return 'normal'

    def _color(lv):
        return {'danger': '#dc2626', 'warn': '#d97706', 'normal': '#059669', 'error': '#9ca3af'}[lv]

    def _icon(lv):
        return {'danger': '🔴', 'warn': '🟡', 'normal': '🟢', 'error': '⚪'}[lv]

    def _mc(value, warn=60, danger=80):
        if value > danger:
            return 'metric-danger'
        if value > warn:
            return 'metric-warn'
        return ''

    total = len(summaries)
    levels = [_level(s) for s in summaries]
    danger_n = levels.count('danger')
    warn_n = levels.count('warn')
    normal_n = levels.count('normal')
    error_n = levels.count('error')

    cards = []
    for i, s in enumerate(summaries):
        lv = levels[i]
        color = _color(lv)
        icon = _icon(lv)
        if s.get('error'):
            cards.append(f'''<div class="card" data-level="{lv}" style="border-top:4px solid {color};">
  <div class="card-header"><span class="card-icon">{icon}</span> {he(s["instance_id"])}</div>
  <div class="card-body"><p class="error-msg">{he(s["error"])}</p></div>
</div>''')
            continue
        cpu_p, mem_p, conn_p, disk_p, iops_p = s['cpu_peak'], s['mem_peak'], s['conn_pct_peak'], s['disk_peak'], s['iops_peak']
        danger_sug = sum(1 for lv2, _ in s.get('suggestions', []) if lv2 == 'danger')
        warn_sug = sum(1 for lv2, _ in s.get('suggestions', []) if lv2 == 'warn')
        sug_badge = ''
        if danger_sug:
            sug_badge += f'<span class="sug-badge sug-danger">{danger_sug} Critical</span>'
        if warn_sug:
            sug_badge += f'<span class="sug-badge sug-warn">{warn_sug} Warning</span>'
        cards.append(f'''<a class="card" data-level="{lv}" href="{s["report_file"]}" style="border-top:4px solid {color};">
  <div class="card-header"><span class="card-icon">{icon}</span><span class="card-id">{he(s["instance_id"])}</span></div>
  <div class="card-desc">{he(s.get("description",""))}</div>
  <div class="card-meta">{he(s["region"])} | {he(s["instance_type"])} | Shard {s["shard_count"]} / Mongos {s["mongos_count"]}</div>
  <div class="card-metrics">
    <div class="metric-row"><span class="metric-label">CPU</span><span class="metric-val {_mc(cpu_p)}">{s["cpu_avg"]:.1f}% / {cpu_p:.1f}%</span></div>
    <div class="metric-row"><span class="metric-label">Mem</span><span class="metric-val {_mc(mem_p)}">{s["mem_avg"]:.1f}% / {mem_p:.1f}%</span></div>
    <div class="metric-row"><span class="metric-label">Conn</span><span class="metric-val {_mc(conn_p)}">{s["conn_pct_avg"]:.1f}% / {conn_p:.1f}%</span></div>
    <div class="metric-row"><span class="metric-label">Disk</span><span class="metric-val {_mc(disk_p, 70, 85)}">{s["disk_avg"]:.1f}% / {disk_p:.1f}%</span></div>
    <div class="metric-row"><span class="metric-label">IOPS</span><span class="metric-val {_mc(iops_p)}">{s["iops_avg"]:.1f}% / {iops_p:.1f}%</span></div>
  </div>
  <div class="card-footer"><span>Slow Queries: {s["slow_count"]}</span><span>Alerts: {s["alert_count"]}</span></div>
  {f'<div class="card-sug">{sug_badge}</div>' if sug_badge else ''}
  <div class="card-link">View Details</div>
</a>''')

    risk_html = ''
    has_risk = False
    for s in summaries:
        if s.get('error'):
            continue
        d_items = [t for lv, t in s.get('suggestions', []) if lv == 'danger']
        w_items = [t for lv, t in s.get('suggestions', []) if lv == 'warn']
        if not d_items and not w_items:
            continue
        has_risk = True
        risk_html += f'<div class="risk-instance"><div class="risk-instance-header"><a href="{s["report_file"]}">{he(s["instance_id"])}</a></div>'
        if d_items:
            risk_html += '<ul class="risk-list risk-list-danger">' + ''.join(f'<li>{he(t)}</li>' for t in d_items) + '</ul>'
        if w_items:
            risk_html += '<ul class="risk-list risk-list-warn">' + ''.join(f'<li>{he(t)}</li>' for t in w_items) + '</ul>'
        risk_html += '</div>'
    risk_section = f'<div class="risk-card"><h2 class="risk-title">⚠ Risk Details</h2>{risk_html}</div>' if has_risk else ''

    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MongoDB (DDS) Batch Inspection Overview</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f5f5f5; padding:2rem; color:#333; }}
.container {{ max-width:1200px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg,#047857,#10b981); color:white; padding:2rem; border-radius:12px; margin-bottom:24px; }}
.header h1 {{ font-size:1.5rem; margin-bottom:8px; }}
.header .time {{ color:rgba(255,255,255,0.85); font-size:0.9rem; }}
.filters {{ display:flex; justify-content:center; gap:8px; margin:16px 0 24px; flex-wrap:wrap; }}
.filter-btn {{ background:#fff; border:1.5px solid #ddd; border-radius:20px; padding:6px 16px; font-size:0.9rem; cursor:pointer; user-select:none; }}
.filter-btn.active {{ font-weight:600; }}
.filter-btn[data-filter="all"].active {{ background:#333; color:#fff; border-color:#333; }}
.filter-btn[data-filter="danger"].active {{ background:#dc2626; color:#fff; border-color:#dc2626; }}
.filter-btn[data-filter="warn"].active {{ background:#d97706; color:#fff; border-color:#d97706; }}
.filter-btn[data-filter="normal"].active {{ background:#059669; color:#fff; border-color:#059669; }}
.filter-btn[data-filter="error"].active {{ background:#9ca3af; color:#fff; border-color:#9ca3af; }}
.grid {{ display:flex; flex-wrap:wrap; justify-content:center; gap:16px; }}
.card {{ width:300px; display:block; background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.08); text-decoration:none; color:inherit; transition:transform .15s; }}
.card.hidden {{ display:none; }}
a.card:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.12); }}
.card-header {{ display:flex; align-items:center; gap:6px; margin-bottom:6px; }}
.card-icon {{ font-size:1.1rem; }}
.card-id {{ font-weight:600; font-size:0.95rem; font-family:monospace; }}
.card-desc {{ color:#666; font-size:0.8rem; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.card-meta {{ color:#888; font-size:0.78rem; margin-bottom:10px; }}
.card-metrics {{ margin-bottom:10px; }}
.metric-row {{ display:flex; justify-content:space-between; font-size:0.82rem; padding:1px 0; }}
.metric-label {{ color:#666; }}
.metric-val {{ font-family:monospace; }}
.metric-danger {{ color:#dc2626; font-weight:700; }}
.metric-warn {{ color:#d97706; font-weight:600; }}
.card-footer {{ display:flex; gap:12px; font-size:0.8rem; color:#666; margin-bottom:6px; }}
.sug-badge {{ font-size:0.75rem; padding:2px 6px; border-radius:3px; margin-right:4px; }}
.sug-danger {{ background:#fee2e2; color:#991b1b; }}
.sug-warn {{ background:#fef3c7; color:#92400e; }}
.card-link {{ text-align:right; font-size:0.8rem; color:#0284c7; }}
.error-msg {{ color:#9ca3af; font-style:italic; }}
.risk-card {{ background:#fff; border-radius:8px; padding:24px; margin-bottom:24px; box-shadow:0 1px 4px rgba(0,0,0,0.08); border-left:4px solid #dc2626; }}
.risk-title {{ font-size:1.2rem; margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid #eee; }}
.risk-instance {{ margin-bottom:16px; }}
.risk-instance-header a {{ color:#065f46; font-weight:600; text-decoration:none; }}
.risk-list {{ padding-left:20px; margin:4px 0 8px; }}
.risk-list li {{ font-size:0.85rem; line-height:1.6; margin-bottom:4px; }}
.risk-list-danger li {{ color:#991b1b; }}
.risk-list-warn li {{ color:#9a3412; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>MongoDB (DDS) Batch Inspection Overview</h1>
  <div class="time">Inspect Time: {he(inspect_time)}</div>
</div>
<div class="filters">
  <button class="filter-btn active" data-filter="all">All {total}</button>
  {f'<button class="filter-btn" data-filter="danger">🔴 Critical {danger_n}</button>' if danger_n else ''}
  {f'<button class="filter-btn" data-filter="warn">🟡 Warning {warn_n}</button>' if warn_n else ''}
  <button class="filter-btn" data-filter="normal">🟢 Normal {normal_n}</button>
  {f'<button class="filter-btn" data-filter="error">⚪ Failed {error_n}</button>' if error_n else ''}
</div>
{risk_section}
<div class="grid">
{"".join(cards)}
</div>
</div>
<script>
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
        f.write(html_doc)
    return index_path



# ─── Dispatcher ──────────────────────────────────────────────────────────────


def render_report(report, fmt):
    if fmt == 'html':
        return render_html(report)
    if fmt == 'text':
        return render_text(report)
    return render_markdown(report)


def inspect_one_instance(instance_id, region, output_dir, fmt='html'):
    """Inspect a single instance, return (instance_id, report_path, summary)"""
    print(f'\n{"=" * 60}')
    print(f'  Inspecting instance: {instance_id}')
    print(f'{"=" * 60}')

    if not region:
        region = find_region(instance_id)
        if not region:
            print(f'  ❌ Instance not found: {instance_id}')
            return instance_id, None, {'instance_id': instance_id, 'error': 'Instance not found'}
    print(f'  Region: {region}')

    print('  📋 Basic info...', end=' ', flush=True)
    info = get_instance_info(instance_id, region)
    if not info:
        print('❌')
        return instance_id, None, {'instance_id': instance_id, 'region': region, 'error': 'Failed to retrieve instance info'}
    print('✅')

    instance_type = info.get('DBInstanceType', '')
    shards, mongos, _ = collect_node_ids(info)
    shard_ids = [s.get('NodeId') for s in shards if s.get('NodeId')]
    mongos_ids = [m.get('NodeId') for m in mongos if m.get('NodeId')]
    all_node_ids = shard_ids + mongos_ids

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=_INSPECT_DAYS)
    start_time = start.strftime('%Y-%m-%dT%H:%MZ')
    end_time = now.strftime('%Y-%m-%dT%H:%MZ')

    if instance_type == 'replicate':
        print(f'  📊 Collecting data in parallel (ReplicaSet, default Primary node)...', flush=True)
    else:
        print(f'  📊 Collecting data in parallel ({len(shard_ids)} Shard + {len(mongos_ids)} Mongos)...', flush=True)

    report = {
        'instance_id': instance_id,
        'region': region,
        'info': info,
        'inspect_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'start_time': start_time,
        'end_time': end_time,
        'days': _INSPECT_DAYS,
    }

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}
        if 'config' in _INSPECT_ITEMS:
            futures['config'] = pool.submit(inspect_config, info)
        if 'resource' in _INSPECT_ITEMS:
            futures['resource'] = pool.submit(inspect_resource, instance_id, region, info, start_time, end_time)
        if 'space' in _INSPECT_ITEMS:
            futures['space'] = pool.submit(inspect_space, instance_id)
        if 'slowlog' in _INSPECT_ITEMS:
            futures['slowlog'] = pool.submit(inspect_slowlog, instance_id, region, info, start_time, end_time)
        if 'session' in _INSPECT_ITEMS:
            futures['session'] = pool.submit(inspect_session, instance_id, all_node_ids)
        if 'alert' in _INSPECT_ITEMS:
            futures['alert'] = pool.submit(inspect_alert, instance_id, region, start_time, end_time)
        for k, fut in futures.items():
            try:
                report[k] = fut.result()
            except Exception as exc:
                print(f'  [WARN] {k} collection failed: {exc}', file=sys.stderr)
                report[k] = None

    report['suggestions'] = build_suggestions(report)

    slow_total = sum(s.get('total', 0) for s in (report.get('slowlog') or []))
    print(f'  ✅ Data collection complete (slow queries: {slow_total})')

    rendered = render_report(report, fmt)
    ext = '.html' if fmt == 'html' else '.md' if fmt == 'markdown' else '.txt'
    report_filename = f'{instance_id}_health_report{ext}'
    report_path = os.path.join(output_dir, report_filename)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(rendered)
    print(f'  📄 Report: {report_path}')

    # Build summary
    res = report.get('resource') or {}
    metrics = res.get('metrics') or {}
    if shard_ids:
        cpu_avgs = [metrics.get(n, {}).get('cpu', (0, 0))[0] for n in shard_ids]
        cpu_peaks = [metrics.get(n, {}).get('cpu', (0, 0))[1] for n in shard_ids]
        mem_avgs = [metrics.get(n, {}).get('memory', (0, 0))[0] for n in shard_ids]
        mem_peaks = [metrics.get(n, {}).get('memory', (0, 0))[1] for n in shard_ids]
        disk_avgs = [metrics.get(n, {}).get('disk_usage', (0, 0))[0] for n in shard_ids]
        disk_peaks = [metrics.get(n, {}).get('disk_usage', (0, 0))[1] for n in shard_ids]
        iops_avgs = [metrics.get(n, {}).get('iops_usage', (0, 0))[0] for n in shard_ids]
        iops_peaks = [metrics.get(n, {}).get('iops_usage', (0, 0))[1] for n in shard_ids]

        def _conn_pct(n, kind):
            attr = next((s for s in shards if s.get('NodeId') == n), {})
            mc = int(attr.get('MaxConnections', 0) or 0)
            v = metrics.get(n, {}).get('connections', (0, 0))[0 if kind == 'avg' else 1]
            return (v / mc * 100) if mc else 0
        conn_avgs = [_conn_pct(n, 'avg') for n in shard_ids]
        conn_peaks = [_conn_pct(n, 'peak') for n in shard_ids]
    else:
        cpu_avgs = cpu_peaks = mem_avgs = mem_peaks = disk_avgs = disk_peaks = iops_avgs = iops_peaks = conn_avgs = conn_peaks = [0]

    summary = {
        'instance_id': instance_id,
        'region': region,
        'instance_type': {'sharding': 'Sharding', 'replicate': 'ReplicaSet'}.get(instance_type, instance_type),
        'description': info.get('DBInstanceDescription', ''),
        'engine_version': info.get('EngineVersion', ''),
        'shard_count': len(shard_ids),
        'mongos_count': len(mongos_ids),
        'cpu_avg': sum(cpu_avgs) / max(len(cpu_avgs), 1),
        'cpu_peak': max(cpu_peaks) if cpu_peaks else 0,
        'mem_avg': sum(mem_avgs) / max(len(mem_avgs), 1),
        'mem_peak': max(mem_peaks) if mem_peaks else 0,
        'conn_pct_avg': sum(conn_avgs) / max(len(conn_avgs), 1),
        'conn_pct_peak': max(conn_peaks) if conn_peaks else 0,
        'disk_avg': sum(disk_avgs) / max(len(disk_avgs), 1),
        'disk_peak': max(disk_peaks) if disk_peaks else 0,
        'iops_avg': sum(iops_avgs) / max(len(iops_avgs), 1),
        'iops_peak': max(iops_peaks) if iops_peaks else 0,
        'slow_count': slow_total,
        'alert_count': len((report.get('alert') or {}).get('records', []) or []),
        'suggestions': report.get('suggestions') or [],
        'report_file': report_filename,
    }
    return instance_id, report_path, summary


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog='health-inspect',
        description='MongoDB (DDS) Instance Health Inspection Tool (supports single/multiple/all instances)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s dds-bp1acbc74a1f9e04
  %(prog)s dds-bp1xxxxxxxx dds-bp2xxxxxxxx
  %(prog)s --all
  %(prog)s --all --region cn-hangzhou
  %(prog)s dds-bp1xxxxxxxx -p myprofile -d 14 -f html -o ./report
"""
    )
    parser.add_argument('instance_ids', metavar='INSTANCE_ID', nargs='*', help='DDS instance ID(s)')
    parser.add_argument('--all', action='store_true', help='Inspect all DDS instances under the current account')
    parser.add_argument('-r', '--region', help='Instance region')
    parser.add_argument('-p', '--profile', help='aliyun CLI profile name')
    parser.add_argument('-o', '--output', help='Report output file path (single) or directory (multiple)')
    parser.add_argument('-d', '--days', type=int, default=7, help='Inspection time range in days (default: 7)')
    parser.add_argument('--item', action='append', choices=ALL_ITEMS,
                        help='Specify inspection items (can be used multiple times). Options: resource, space, slowlog, session, alert')
    parser.add_argument('-f', '--format', choices=['html', 'markdown', 'text'], default='html', help='Report format')
    args = parser.parse_args()

    if not args.all and not args.instance_ids:
        parser.error('Please provide at least one INSTANCE_ID or use --all')

    global _CLI_PROFILE, _INSPECT_DAYS, _INSPECT_ITEMS
    _CLI_PROFILE = args.profile
    _INSPECT_DAYS = max(1, int(args.days))
    _INSPECT_ITEMS = set(args.item) if args.item else set(ALL_ITEMS)

    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('❌ aliyun CLI not found, please install: https://help.aliyun.com/zh/cli/', file=sys.stderr)
        sys.exit(1)

    # Determine instance list
    if args.all:
        print('🔍 Discovering all MongoDB (DDS) instances...')
        instances = discover_all_instances(region=args.region)
        if not instances:
            print('❌ No MongoDB instances found')
            sys.exit(1)
        print(f'   ✅ Found {len(instances)} instances')
        for it in instances:
            print(f'      - {it["instance_id"]} ({it["region"]}) {it.get("description","")}')
    else:
        instances = [{'instance_id': iid, 'region': args.region} for iid in args.instance_ids]

    fmt = args.format

    # ── Single instance ──
    if len(instances) == 1:
        inst = instances[0]
        instance_id = inst['instance_id']
        region = inst.get('region')

        print('┌' + '─' * 50 + '┐')
        print('│  MongoDB (DDS) Health Inspection' + ' ' * 17 + '│')
        print('└' + '─' * 50 + '┘')
        print(f'  Instance: {instance_id}')
        if _CLI_PROFILE:
            print(f'  Profile: {_CLI_PROFILE}')
        print()

        ext = '.html' if fmt == 'html' else '.md' if fmt == 'markdown' else '.txt'
        if args.output:
            output_path = os.path.abspath(args.output)
            if os.path.isdir(output_path) or output_path.endswith('/'):
                os.makedirs(output_path, exist_ok=True)
                output_dir = output_path
            else:
                output_dir = os.path.dirname(output_path) or '.'
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = os.path.expanduser('~/Downloads')
            os.makedirs(output_dir, exist_ok=True)

        _, report_path, summary = inspect_one_instance(instance_id, region, output_dir, fmt=fmt)
        if not report_path:
            sys.exit(1)

        # Rename to user-specified filename (when --output is a file path)
        if args.output and not (os.path.isdir(args.output) or args.output.endswith('/')):
            target = os.path.abspath(args.output)
            if not target.endswith(ext):
                target += ext
            if target != report_path:
                try:
                    os.rename(report_path, target)
                    report_path = target
                except OSError:
                    pass

        print(f'\n📄 Report saved: {report_path}')
        return

    # ── Multi instance ──
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    if args.output:
        output_dir = os.path.abspath(args.output)
    else:
        output_dir = os.path.join(os.path.expanduser('~/Downloads'),
                                  f'mongodb_health_inspect_report_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)

    print('┌' + '─' * 50 + '┐')
    print('│  MongoDB (DDS) Batch Inspection' + ' ' * 18 + '│')
    print('└' + '─' * 50 + '┘')
    print(f'  Instances: {len(instances)}')
    print(f'  Output Dir: {output_dir}')
    if _CLI_PROFILE:
        print(f'  Profile: {_CLI_PROFILE}')
    print()

    # Force HTML for multi-instance
    batch_fmt = 'html' if len(instances) > 1 else fmt

    def _do(inst):
        _, _, summary = inspect_one_instance(inst['instance_id'], inst.get('region'), output_dir, fmt=batch_fmt)
        return summary

    with ThreadPoolExecutor(max_workers=min(len(instances), 4)) as pool:
        futures = [pool.submit(_do, it) for it in instances]
        summaries = [f.result() for f in futures]

    inspect_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    index_path = render_summary_html(summaries, output_dir, inspect_time)
    print(f'\n{"=" * 60}')
    print(f'📊 Summary report: {index_path}')
    print(f'   {len(summaries)} instances inspection complete')
    danger_n = sum(1 for s in summaries if any(lv == 'danger' for lv, _ in s.get('suggestions', [])))
    warn_n = sum(1 for s in summaries if not any(lv == 'danger' for lv, _ in s.get('suggestions', []))
                 and any(lv == 'warn' for lv, _ in s.get('suggestions', [])))
    error_n = sum(1 for s in summaries if s.get('error'))
    normal_n = len(summaries) - danger_n - warn_n - error_n
    print(f'   🔴 {danger_n} Critical  🟡 {warn_n} Warning  🟢 {normal_n} Normal  ⚪ {error_n} Failed')


if __name__ == '__main__':
    main()
