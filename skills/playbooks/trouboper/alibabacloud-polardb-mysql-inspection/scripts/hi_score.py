# -*- coding: utf-8 -*-
"""PolarDB MySQL Health Inspection - Health scoring module

Deduction-based 100-point model covering CPU / memory / disk / IOPS /
connections / slow logs / alerts / version / expiry / lock status,
producing a quantitative score with bilingual deduction details.
"""
from datetime import datetime, timezone


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _level_weight(level):
    """Map PolarDB alert level (P1-P4) to numeric weight."""
    weights = {'P1': 100, 'P2': 70, 'P3': 30, 'P4': 10}
    return weights.get(str(level).upper(), 0)


# ─── Health Score ─────────────────────────────────────────────────────────────

def calc_health_score(summary):
    """Compute a 0-100 health score from a flat PolarDB summary dict.

    Parameters
    ----------
    summary : dict
        Flat keys: cpu_peak, mem_peak, disk_peak_pct, iops_peak, conn_peak_pct,
        slow_count, alert_history (list), is_latest (bool), expire_time (str),
        lock_mode (str).

    Returns
    -------
    (score: int, deductions: list[dict])
        Each deduction is ``{'en': '...', 'zh': '...'}``.
    """
    score = 100
    deductions = []

    # ── Resource metrics (flat keys) ──────────────────────────────────────
    metric_rules = [
        # (key, high_thresh, high_deduct, mid_thresh, mid_deduct, en_label, zh_label)
        ('cpu_peak',     80, 10, 60, 5, 'CPU peak',        'CPU 峰值'),
        ('mem_peak',     80, 10, 60, 5, 'Memory peak',     '内存峰值'),
        ('iops_peak',    80, 10, 60, 5, 'IOPS peak',       'IOPS 峰值'),
        ('conn_peak_pct', 80, 10, 60, 5, 'Connection peak', '连接峰值'),
    ]
    for key, h_t, h_d, m_t, m_d, en, zh in metric_rules:
        val = summary.get(key, 0) or 0
        if val > h_t:
            score -= h_d
            deductions.append({'en': f'{en} > {h_t}%', 'zh': f'{zh}超 {h_t}%'})
        elif val > m_t:
            score -= m_d
            deductions.append({'en': f'{en} > {m_t}%', 'zh': f'{zh}超 {m_t}%'})

    # Disk has different thresholds (85/70)
    disk = summary.get('disk_peak_pct', 0) or 0
    if disk > 85:
        score -= 15
        deductions.append({'en': 'Disk usage > 85%', 'zh': '磁盘使用率超 85%'})
    elif disk > 70:
        score -= 5
        deductions.append({'en': 'Disk usage > 70%', 'zh': '磁盘使用率超 70%'})

    # ── Slow queries ──────────────────────────────────────────────────────
    slow = summary.get('slow_count', 0) or 0
    if slow > 1000:
        score -= 8
        deductions.append({'en': 'Too many slow queries (>1000)',
                           'zh': '慢日志数量过多 (>1000 条)'})
    elif slow > 100:
        score -= 3
        deductions.append({'en': 'Many slow queries (>100)',
                           'zh': '慢日志数量较多 (>100 条)'})

    # ── Alerts (P1 critical / P2 high / volume) ──────────────────────────
    alerts = summary.get('alert_history', []) or []
    p1_count = sum(1 for a in alerts if _level_weight(a.get('level', '')) >= 100)
    p2_count = sum(1 for a in alerts if _level_weight(a.get('level', '')) >= 70)
    if p1_count > 0:
        score -= 10
        deductions.append({'en': 'Critical P1 alerts present',
                           'zh': '存在 P1 紧急告警'})
    elif p2_count > 50:
        score -= 5
        deductions.append({'en': 'Many P2 high-severity alerts (>50)',
                           'zh': 'P2 高严重告警数量较多 (>50 条)'})
    elif len(alerts) > 100:
        score -= 3
        deductions.append({'en': 'High alert volume (>100)',
                           'zh': '告警总数较多 (>100 条)'})

    # ── Kernel version not latest ─────────────────────────────────────────
    if summary.get('is_latest') is False:
        score -= 3
        deductions.append({'en': 'Kernel version not latest',
                           'zh': '内核版本未更新到最新'})

    # ── Expiring within 30 days ───────────────────────────────────────────
    expire = summary.get('expire_time', '')
    if expire:
        try:
            et = datetime.strptime(expire[:10], '%Y-%m-%d').replace(
                tzinfo=timezone.utc)
            days_left = (et - datetime.now(timezone.utc)).days
            if 0 <= days_left <= 30:
                score -= 5
                deductions.append({
                    'en': f'Instance expires in {days_left} days',
                    'zh': f'实例 {days_left} 天后到期',
                })
        except (ValueError, TypeError):
            pass

    # ── LockMode abnormal ─────────────────────────────────────────────────
    lock = (summary.get('lock_mode') or '').strip()
    if lock and lock.lower() != 'unlock':
        score -= 8
        deductions.append({
            'en': f'Instance in {lock} state',
            'zh': f'实例处于 {lock} 状态',
        })

    return max(0, score), deductions


# ─── Status tier ──────────────────────────────────────────────────────────────

def score_status(score):
    """Map health score to (emoji, tier_name)."""
    if score >= 80:
        return '🟢', 'ok'
    elif score >= 60:
        return '🟡', 'warn'
    else:
        return '🔴', 'danger'
