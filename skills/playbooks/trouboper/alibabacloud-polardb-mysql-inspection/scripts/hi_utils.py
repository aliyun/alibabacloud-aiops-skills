"""PolarDB MySQL 健康巡检 - 通用工具函数"""

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


# ─── Data Processing ─────────────────────────────────────────────────────────

def _node_role_short(node):
    role = node.get('DBNodeRole', node.get('role', ''))
    if node.get('ImciSwitch', '') == 'ON':
        return 'IMCI'
    if role in ('Writer', 'ReadWrite'):
        return 'RW'
    return 'RO'
