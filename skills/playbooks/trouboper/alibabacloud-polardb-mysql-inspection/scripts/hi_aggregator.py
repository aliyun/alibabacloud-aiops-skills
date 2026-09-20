#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-instance data aggregation for batch inspection summary report.

Produces a comprehensive 26-key dict mirroring the 8-section report structure:
  1. Overview (counts, distributions, global_score)
  2. Health ranking (TOP20 lowest scores)
  3. Alerts (totals, level distribution, TOP20)
  4. Resource tops (CPU/memory/IOPS/connection/disk TOP20)
  5. Slow logs (count/time ranking, cross-instance SQL TOP20)
  6. Space (instance ranking, table TOP20, fragmentation)
  7. Version & expiration
  8. Suggestions (problem-centric deduction aggregation)
"""
from datetime import datetime, timezone

from hi_score import score_status


def aggregate_summaries(summaries, time_range='', scanned_total=0):
    """Aggregate multiple instance summaries into cross-instance rankings.

    Args:
        summaries: list of summary dicts from inspect_single_cluster()
        time_range: human-readable inspection period string
        scanned_total: total clusters discovered (before filtering errors)

    Returns:
        dict with ~26 keys covering all 8 report sections.
    """
    if not summaries:
        return {
            'total_instances': 0,
            'scanned_total': scanned_total,
            'region_count': 0,
            'status_dist': {},
            'category_dist': {},
            'health_dist': {'ok': 0, 'warn': 0, 'danger': 0},
            'region_dist': {},
            'global_score': 0,
            'health_ranking': [],
            'total_alerts': 0,
            'instances_with_alerts': 0,
            'alert_level_dist': {},
            'alerts_ranking': [],
            'resource_tops': {k: [] for k in ('cpu', 'memory', 'iops', 'connection', 'disk')},
            'slow_count_ranking': [],
            'slow_time_ranking': [],
            'sql_max_time_top20': [],
            'instance_space_ranking': [],
            'tables_top20': [],
            'fragmentation_ranking': [],
            'upgradable': [],
            'expiring_30d': [],
            'expiring_90d': [],
            'suggestions': {},
            'time_range': time_range,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # Section 1: Overview
    # ═══════════════════════════════════════════════════════════════════════

    status_dist = {}
    for s in summaries:
        st = s.get('status') or 'Unknown'
        status_dist[st] = status_dist.get(st, 0) + 1

    category_dist = {}
    for s in summaries:
        cat = s.get('category') or 'Unknown'
        category_dist[cat] = category_dist.get(cat, 0) + 1

    health_dist = {'ok': 0, 'warn': 0, 'danger': 0}
    for s in summaries:
        _, tier = score_status(s.get('health_score', 0))
        health_dist[tier] = health_dist.get(tier, 0) + 1

    region_dist = {}
    for s in summaries:
        r = s.get('region', 'unknown')
        region_dist[r] = region_dist.get(r, 0) + 1

    global_score = round(
        sum(s.get('health_score', 0) for s in summaries) / len(summaries), 1
    )

    # ═══════════════════════════════════════════════════════════════════════
    # Section 2: Health ranking (lowest TOP 20)
    # ═══════════════════════════════════════════════════════════════════════

    sorted_by_score = sorted(summaries, key=lambda s: s.get('health_score', 100))
    health_ranking = []
    for s in sorted_by_score[:20]:
        health_ranking.append({
            'cluster_id': s.get('cluster_id', ''),
            'region': s.get('region', ''),
            'health_score': s.get('health_score', 0),
            'health_deductions': s.get('health_deductions', []),
            'category': s.get('category', ''),
            'category_en': s.get('category_en', s.get('category', '')),
            'category_zh': s.get('category_zh', s.get('category', '')),
            'node_class': s.get('node_class', ''),
        })

    # ═══════════════════════════════════════════════════════════════════════
    # Section 3: Alerts
    # ═══════════════════════════════════════════════════════════════════════

    _level_priority = {'P1': 1, 'P2': 2, 'P3': 3, 'P4': 4}

    total_alerts = 0
    instances_with_alerts_count = 0
    alert_level_dist = {}
    alerts_ranking_raw = []

    for s in summaries:
        alerts = s.get('alert_history') or []
        count = len(alerts)
        total_alerts += count
        if count > 0:
            instances_with_alerts_count += 1

        for a in alerts:
            lvl = (a.get('level') or 'Unknown').upper()
            alert_level_dist[lvl] = alert_level_dist.get(lvl, 0) + 1

        if count > 0:
            max_level = 'P4'
            high_severity = 0
            for a in alerts:
                lvl = (a.get('level') or 'P4').upper()
                if _level_priority.get(lvl, 99) < _level_priority.get(max_level, 99):
                    max_level = lvl
                if lvl in ('P1', 'P2'):
                    high_severity += 1
            alerts_ranking_raw.append({
                'cluster_id': s.get('cluster_id', ''),
                'region': s.get('region', ''),
                'alert_count': count,
                'max_level': max_level,
                'high_severity': high_severity,
            })

    alerts_ranking_raw.sort(key=lambda x: -x['alert_count'])
    alerts_ranking = alerts_ranking_raw[:20]

    # ═══════════════════════════════════════════════════════════════════════
    # Section 4: Resource tops (5 dimensions, TOP 20 each)
    # ═══════════════════════════════════════════════════════════════════════

    _resource_keys = {
        'cpu':        ('cpu_avg', 'cpu_peak'),
        'memory':     ('mem_avg', 'mem_peak'),
        'iops':       ('iops_avg', 'iops_peak'),
        'connection': ('conn_avg_pct', 'conn_peak_pct'),
        'disk':       ('disk_avg_pct', 'disk_peak_pct'),
    }

    resource_tops = {}
    for dim, (avg_key, peak_key) in _resource_keys.items():
        ranked = []
        for s in summaries:
            ranked.append({
                'cluster_id': s.get('cluster_id', ''),
                'region': s.get('region', ''),
                'avg': s.get(avg_key, 0) or 0,
                'peak': s.get(peak_key, 0) or 0,
            })
        ranked.sort(key=lambda x: -x['peak'])
        resource_tops[dim] = ranked[:20]

    # ═══════════════════════════════════════════════════════════════════════
    # Section 5: Slow logs
    # ═══════════════════════════════════════════════════════════════════════

    slow_count_ranking = []
    slow_time_ranking = []
    all_sql_max_time = []

    for s in summaries:
        detail = s.get('slow_logs_detail') or []
        total_count = sum(e.get('count', 0) for e in detail)
        total_time = sum(e.get('total_time', 0) for e in detail)
        unique_sqls = len(detail)

        slow_count_ranking.append({
            'cluster_id': s.get('cluster_id', ''),
            'region': s.get('region', ''),
            'total_count': total_count,
            'unique_sqls': unique_sqls,
        })
        slow_time_ranking.append({
            'cluster_id': s.get('cluster_id', ''),
            'region': s.get('region', ''),
            'total_time': total_time,
            'unique_sqls': unique_sqls,
        })

        cid = s.get('cluster_id', '')
        for e in detail:
            all_sql_max_time.append({
                'cluster_id': cid,
                'db_name': e.get('db', ''),
                'sql': (e.get('sql_text') or '')[:300],
                'max_time': e.get('max_time', 0),
            })

    slow_count_ranking.sort(key=lambda x: -x['total_count'])
    slow_time_ranking.sort(key=lambda x: -x['total_time'])
    all_sql_max_time.sort(key=lambda x: -x['max_time'])

    # ═══════════════════════════════════════════════════════════════════════
    # Section 6: Space
    # ═══════════════════════════════════════════════════════════════════════

    instance_space_ranking = []
    all_tables = []
    fragmentation_ranking = []

    for s in summaries:
        space = s.get('space_data')
        if not space:
            continue
        total_used = space.get('total_used', 0) or 0
        daily_inc = space.get('daily_inc', 0) or 0
        storage_total = s.get('storage_total', 0) or 0
        table_list = space.get('table_list') or []

        if daily_inc > 0 and storage_total > total_used:
            estimate_days = int((storage_total - total_used) / daily_inc)
        else:
            estimate_days = None

        instance_space_ranking.append({
            'cluster_id': s.get('cluster_id', ''),
            'region': s.get('region', ''),
            'total_used': total_used,
            'storage_total': storage_total,
            'daily_inc': daily_inc,
            'estimate_days': estimate_days,
            'tables_count': len(table_list),
        })

        cid = s.get('cluster_id', '')
        region = s.get('region', '')
        for t in table_list:
            all_tables.append({
                'cluster_id': cid,
                'region': region,
                **t,
            })
            total_size = t.get('total', 0) or 0
            frag_size = t.get('frag', 0) or 0
            if total_size > 0 and frag_size > 0:
                frag_pct = frag_size / total_size * 100
                if frag_pct >= 5:
                    fragmentation_ranking.append({
                        'cluster_id': cid,
                        'db_name': t.get('db', ''),
                        'table_name': t.get('table', ''),
                        'total_size': total_size,
                        'frag_size': frag_size,
                        'frag_pct': frag_pct,
                    })

    instance_space_ranking.sort(key=lambda x: -x['total_used'])
    all_tables.sort(key=lambda x: -(x.get('total', 0) or 0))
    fragmentation_ranking.sort(key=lambda x: -x['frag_pct'])

    # ═══════════════════════════════════════════════════════════════════════
    # Section 7: Version & expiration
    # ═══════════════════════════════════════════════════════════════════════

    upgradable = []
    expiring_30d = []
    expiring_90d = []

    for s in summaries:
        if s.get('is_latest') is False:
            upgradable.append({
                'cluster_id': s.get('cluster_id', ''),
                'region': s.get('region', ''),
                'current': s.get('revision_version', ''),
                'latest': s.get('latest_version', ''),
            })

        expire = s.get('expire_time', '')
        if expire:
            try:
                et = datetime.strptime(expire[:10], '%Y-%m-%d').replace(
                    tzinfo=timezone.utc)
                days_left = (et - datetime.now(timezone.utc)).days
                rec = {
                    'cluster_id': s.get('cluster_id', ''),
                    'region': s.get('region', ''),
                    'expire_date': expire[:10],
                    'days_left': days_left,
                }
                if 0 <= days_left <= 30:
                    expiring_30d.append(rec)
                elif 30 < days_left <= 90:
                    expiring_90d.append(rec)
            except (ValueError, TypeError):
                pass

    expiring_30d.sort(key=lambda x: x['days_left'])
    expiring_90d.sort(key=lambda x: x['days_left'])

    # ═══════════════════════════════════════════════════════════════════════
    # Section 8: Suggestions (problem-centric deduction aggregation)
    # ═══════════════════════════════════════════════════════════════════════

    suggestions = {}
    for s in summaries:
        for ded in s.get('health_deductions', []):
            key = ded.get('en') if isinstance(ded, dict) else str(ded)
            if key not in suggestions:
                suggestions[key] = {
                    'label': ded if isinstance(ded, dict) else {'en': str(ded), 'zh': str(ded)},
                    'cluster_ids': [],
                }
            suggestions[key]['cluster_ids'].append(s.get('cluster_id', ''))

    # ═══════════════════════════════════════════════════════════════════════
    # Assemble final dict
    # ═══════════════════════════════════════════════════════════════════════

    return {
        # Overview
        'total_instances': len(summaries),
        'scanned_total': scanned_total,
        'region_count': len(set(s.get('region', '') for s in summaries)),
        'status_dist': status_dist,
        'category_dist': category_dist,
        'health_dist': health_dist,
        'region_dist': region_dist,
        'global_score': global_score,
        # Health ranking
        'health_ranking': health_ranking,
        # Alerts
        'total_alerts': total_alerts,
        'instances_with_alerts': instances_with_alerts_count,
        'alert_level_dist': alert_level_dist,
        'alerts_ranking': alerts_ranking,
        # Resource tops
        'resource_tops': resource_tops,
        # Slow logs
        'slow_count_ranking': slow_count_ranking[:20],
        'slow_time_ranking': slow_time_ranking[:20],
        'sql_max_time_top20': all_sql_max_time[:20],
        # Space
        'instance_space_ranking': instance_space_ranking[:20],
        'tables_top20': all_tables[:20],
        'fragmentation_ranking': fragmentation_ranking[:20],
        # Version & expiration
        'upgradable': upgradable,
        'expiring_30d': expiring_30d,
        'expiring_90d': expiring_90d,
        # Suggestions
        'suggestions': suggestions,
        # Metadata
        'time_range': time_range,
    }
