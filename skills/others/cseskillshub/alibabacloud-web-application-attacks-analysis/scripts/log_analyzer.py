#!/usr/bin/env python3
"""
log_analyzer.py - Web Log Security Analyzer
Supports Nginx, Apache, and IIS W3C log formats.

SECURITY:
  - Read-only analysis: this script only parses the given access log and
    NEVER modifies the input file.
  - It is invoked only after explicit user confirmation and processes ONLY
    the file explicitly specified by the user on the command line.
  - Fully offline: it makes no network connections and sends no data
    anywhere; all analysis happens locally.
"""

import argparse
import gzip
import ipaddress
import json
import re
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Log format patterns
# ---------------------------------------------------------------------------

NGINX_PATTERN = re.compile(
    r'^(?P<remote_ip>\S+)\s+-\s+(?P<remote_user>\S+)\s+\[(?P<time_local>[^\]]+)\]\s+'
    r'"(?P<request>[^"]+)"\s+(?P<status>\d{3})\s+(?P<body_bytes_sent>\d+|-)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
    r'(?:\s+"(?P<xff>[^"]*)")?(?:\s+(?P<request_time>[\d.]+))?(?:\s+(?P<upstream_time>[\d.]+))?'
)

# Alternative nginx pattern with xff in different position
NGINX_PATTERN_ALT = re.compile(
    r'^(?P<remote_ip>\S+)\s+-\s+(?P<remote_user>\S+)\s+\[(?P<time_local>[^\]]+)\]\s+'
    r'"(?P<request>[^"]+)"\s+(?P<status>\d{3})\s+(?P<body_bytes_sent>\d+|-)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"\s+'
    r'"(?P<xff>[^"]*)"\s+(?P<request_time>[\d.]+)\s+(?P<upstream_time>[\d.]+)'
)

APACHE_PATTERN = re.compile(
    r'^(?P<remote_ip>\S+)\s+(?P<remote_logname>\S+)\s+(?P<remote_user>\S+)\s+'
    r'\[(?P<time_local>[^\]]+)\]\s+"(?P<request>[^"]+)"\s+(?P<status>\d{3})\s+'
    r'(?P<body_bytes_sent>\d+|-)\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
    r'(?:\s+"(?P<xff>[^"]*)")?'
)

# Tolerant fallback patterns for real-world variants (tried only after the
# strict patterns fail):
#  - nginx: leading XFF field (quoted or comma-separated IP list) before
#    remote_addr, empty request line ('""' for malformed requests).
#  - apache: common format without referer/user-agent fields.
NGINX_PATTERN_LOOSE = re.compile(
    r'^(?P<lead>.+?)\s+-\s+(?P<remote_user>\S+)\s+\[(?P<time_local>[^\]]+)\]\s+'
    r'"(?P<request>[^"]*)"\s+(?P<status>\d{3})\s+(?P<body_bytes_sent>\d+|-)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
)

APACHE_PATTERN_LOOSE = re.compile(
    r'^(?P<remote_ip>\S+)\s+(?P<remote_logname>\S+)\s+(?P<remote_user>\S+)\s+'
    r'\[(?P<time_local>[^\]]+)\]\s+"(?P<request>[^"]*)"\s+(?P<status>\d{3})\s+'
    r'(?P<body_bytes_sent>\d+|-)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
    r'(?:\s+"(?P<xff>[^"]*)")?'
)

LOGIN_PATHS = {'/login', '/api/login', '/auth', '/signin', '/api/v1/auth',
               '/oauth/token', '/api/signin', '/user/login', '/admin/login'}

SCAN_PATHS = {'/.env', '/.git/config', '/.git/HEAD', '/phpmyadmin',
              '/wp-admin', '/wp-login.php', '/admin', '/api/v1/users',
              '/config.json', '/.aws/credentials', '/env.js',
              '/server-status', '/actuator', '/manager/html', '/config', '/backup'}

SUSPICIOUS_UA_KEYWORDS = {'curl', 'wget', 'python-requests', 'go-http-client',
                          'java', 'apache-httpclient', 'okhttp', 'sqlmap', 'masscan'}

API_PATTERN = re.compile(r'^/api/')


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def is_private_ip(ip_str):
    """Check if an IP address is private/reserved."""
    if not ip_str or ip_str == '-':
        return True
    try:
        addr = ipaddress.ip_address(ip_str.strip())
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        return True


def aggregate_ips_to_cidr(ips):
    """Find the smallest CIDR network that contains all given IPv4 addresses.
    Returns None if input is empty or contains non-IPv4 addresses.
    """
    if not ips or len(ips) == 0:
        return None
    try:
        int_ips = [int(ipaddress.ip_address(ip)) for ip in ips]
    except ValueError:
        return None

    if len(int_ips) == 1:
        return f"{ips[0]}/32"

    min_ip = min(int_ips)
    max_ip = max(int_ips)
    xor = min_ip ^ max_ip
    prefix_len = 32
    while xor > 0:
        xor >>= 1
        prefix_len -= 1

    # Reject overly broad aggregations (e.g. /1, /8) as operationally meaningless
    MIN_PREFIX_LEN = 24
    if prefix_len < MIN_PREFIX_LEN:
        return None

    network_addr = min_ip & (0xFFFFFFFF << (32 - prefix_len))
    network = ipaddress.ip_network(
        f"{ipaddress.ip_address(network_addr)}/{prefix_len}", strict=False
    )
    return str(network)


def aggregate_ips_to_precise_cidrs(ips, min_prefix=24):
    """Group IPs by /24 subnet, then compute the tightest CIDR per group.

    Returns a list of (cidr_str, ip_list) tuples sorted by ip count desc.
    Each CIDR is guaranteed to have prefix length >= min_prefix (default /24).
    Single IPs are returned as /32.
    """
    if not ips:
        return []

    # Group by /24 subnet
    subnet_groups = defaultdict(list)
    for ip_str in ips:
        try:
            addr = ipaddress.ip_address(ip_str)
            # /24 key: first 3 octets
            subnet_key = int(addr) >> 8
            subnet_groups[subnet_key].append(ip_str)
        except ValueError:
            continue

    results = []
    for _key, group_ips in subnet_groups.items():
        if len(group_ips) == 1:
            results.append((f"{group_ips[0]}/32", group_ips))
            continue

        try:
            int_ips = [int(ipaddress.ip_address(ip)) for ip in group_ips]
        except ValueError:
            continue

        min_ip = min(int_ips)
        max_ip = max(int_ips)
        xor = min_ip ^ max_ip
        prefix_len = 32
        while xor > 0:
            xor >>= 1
            prefix_len -= 1

        # Clamp to min_prefix (never broader than /24)
        prefix_len = max(prefix_len, min_prefix)

        network_addr = min_ip & (0xFFFFFFFF << (32 - prefix_len))
        network = ipaddress.ip_network(
            f"{ipaddress.ip_address(network_addr)}/{prefix_len}", strict=False
        )
        results.append((str(network), group_ips))

    # Sort by group size desc, then by CIDR prefix length asc (broader first)
    results.sort(key=lambda x: (-len(x[1]), x[0]))
    return results


def human_readable_size(size_bytes):
    """Convert bytes to human-readable string (B / KB / MB / GB / TB)."""
    if size_bytes < 0:
        return '0 B'
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 ** 2:
        return f'{size_bytes / 1024:.2f} KB'
    elif size_bytes < 1024 ** 3:
        return f'{size_bytes / (1024 ** 2):.2f} MB'
    elif size_bytes < 1024 ** 4:
        return f'{size_bytes / (1024 ** 3):.2f} GB'
    else:
        return f'{size_bytes / (1024 ** 4):.2f} TB'


def extract_client_ip(remote_ip, xff_header):
    """
    Extract real client IP for attack analysis.
    1. If xff exists: left-to-right, first valid public IP as client_ip.
    2. If xff absent/empty/invalid: client_ip = remote_ip.
    remote_ip is always preserved and never overwritten.
    """
    if xff_header and xff_header != '-' and xff_header.strip():
        for ip in xff_header.split(','):
            ip = ip.strip()
            if ip and not is_private_ip(ip):
                return ip
    return remote_ip if remote_ip and remote_ip != '-' else None


def parse_timestamp(time_str, source_type):
    """Parse log timestamp to timezone-aware datetime."""
    if not time_str:
        return None
    try:
        if source_type in ('nginx', 'apache'):
            dt = datetime.strptime(time_str, '%d/%b/%Y:%H:%M:%S %z')
            return dt
        elif source_type == 'iis':
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def parse_request(request_str):
    """Parse 'METHOD /path?query HTTP/1.1' into components."""
    if not request_str or request_str == '-':
        return None, None, None
    parts = request_str.split(' ')
    method = parts[0] if len(parts) > 0 else None
    url = parts[1] if len(parts) > 1 else None
    if url:
        parsed = urlparse(url)
        return method, parsed.path, parsed.query
    return method, None, None


# ---------------------------------------------------------------------------
# detect_log_type
# ---------------------------------------------------------------------------

def detect_log_type(lines):
    """Auto-detect log format from first 10 non-empty lines.
    Returns: 'nginx' | 'apache' | 'iis' | 'mixed' | 'unknown'
    """
    sample = [ln for ln in lines if ln.strip()][:10]
    if not sample:
        raise ValueError("Empty log file")

    if any(ln.startswith('#Software:') or ln.startswith('#Fields:') for ln in sample):
        return 'iis'

    scores = {'nginx': 0, 'apache': 0}
    for ln in sample:
        if NGINX_PATTERN.match(ln) or NGINX_PATTERN_ALT.match(ln):
            scores['nginx'] += 1
        if APACHE_PATTERN.match(ln):
            scores['apache'] += 1

    total_matched = scores['nginx'] + scores['apache']
    if total_matched == 0:
        return 'unknown'

    # Mixed: both formats matched in the sample
    if scores['nginx'] > 0 and scores['apache'] > 0:
        return 'mixed'

    if scores['nginx'] >= scores['apache']:
        return 'nginx'
    return 'apache'


# ---------------------------------------------------------------------------
# parse_log_line
# ---------------------------------------------------------------------------

def parse_nginx_line(line):
    for pat in (NGINX_PATTERN, NGINX_PATTERN_ALT):
        m = pat.match(line)
        if m:
            d = m.groupdict()
            method, path, query = parse_request(d.get('request'))
            return {
                'source_type': 'nginx',
                'remote_ip': d.get('remote_ip'),
                'remote_user': d.get('remote_user'),
                'time_local': d.get('time_local'),
                'method': method,
                'url': d.get('request'),
                'path': path,
                'query': query,
                'status': int(d['status']) if d.get('status') else None,
                'bytes': int(d['body_bytes_sent']) if d.get('body_bytes_sent') and d['body_bytes_sent'] != '-' else 0,
                'referer': d.get('referer'),
                'ua': d.get('user_agent'),
                'request_time': float(d['request_time']) if d.get('request_time') else None,
                'upstream_time': float(d['upstream_time']) if d.get('upstream_time') else None,
                'xff': d.get('xff'),
            }
    # Fallback: real-world variants (leading XFF field, empty request line)
    m = NGINX_PATTERN_LOOSE.match(line)
    if m:
        d = m.groupdict()
        remote_ip, xff_lead = _split_nginx_lead(d.get('lead') or '')
        if not remote_ip:
            return None
        method, path, query = parse_request(d.get('request'))
        return {
            'source_type': 'nginx',
            'remote_ip': remote_ip,
            'remote_user': d.get('remote_user'),
            'time_local': d.get('time_local'),
            'method': method,
            'url': d.get('request'),
            'path': path,
            'query': query,
            'status': int(d['status']) if d.get('status') else None,
            'bytes': int(d['body_bytes_sent']) if d.get('body_bytes_sent') and d['body_bytes_sent'] != '-' else 0,
            'referer': d.get('referer'),
            'ua': d.get('user_agent'),
            'request_time': None,
            'upstream_time': None,
            'xff': xff_lead,
        }
    return None


def _split_nginx_lead(lead):
    """Split the leading field(s) of a tolerant-matched nginx line into
    (remote_ip, xff). Handles 'IP', 'IP, IP, IP' and '"IP, IP" IP' forms:
    the right-most whitespace-separated token is the remote_addr, everything
    before it is treated as the X-Forwarded-For field.
    """
    lead = lead.strip()
    if not lead:
        return None, None
    if lead.startswith('"'):
        end = lead.find('"', 1)
        if end < 0:
            return None, None
        quoted = lead[1:end].strip()
        rest = lead[end + 1:].strip()
        if not rest:
            return None, None
        # rest may contain several whitespace-separated tokens; the right-most
        # one is remote_addr, the rest is folded into the XFF field
        # (consistent with the non-quoted branch).
        tokens = rest.split()
        xff_parts = ([quoted] if quoted else []) + tokens[:-1]
        xff = ' '.join(xff_parts).rstrip(',') or None
        return tokens[-1], xff
    tokens = lead.split()
    if len(tokens) >= 2:
        return tokens[-1], ' '.join(tokens[:-1]).rstrip(',')
    return lead, None


def parse_apache_line(line):
    m = APACHE_PATTERN.match(line)
    if not m:
        # Fallback: common format without referer/user-agent fields
        m = APACHE_PATTERN_LOOSE.match(line)
    if not m:
        return None
    d = m.groupdict()
    method, path, query = parse_request(d.get('request'))
    return {
        'source_type': 'apache',
        'remote_ip': d.get('remote_ip'),
        'remote_user': d.get('remote_user'),
        'time_local': d.get('time_local'),
        'method': method,
        'url': d.get('request'),
        'path': path,
        'query': query,
        'status': int(d['status']) if d.get('status') else None,
        'bytes': int(d['body_bytes_sent']) if d.get('body_bytes_sent') and d['body_bytes_sent'] != '-' else 0,
        'referer': d.get('referer'),
        'ua': d.get('user_agent'),
        'request_time': None,
        'upstream_time': None,
        'xff': d.get('xff'),
    }


def parse_iis_log(lines):
    records = []
    fields = []
    schemas = []  # all #Fields declarations seen so far (logs concatenated
    # from multiple days/servers may switch field layouts mid-file)
    alt_schema_rows = 0  # data rows parsed with a non-current schema
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            if line.startswith('#Fields:'):
                rest = line.split(' ', 1)[1].strip() if ' ' in line else ''
                new_fields = rest.split(' ') if rest else []
                if new_fields:  # ignore empty field lists (bare '#Fields:')
                    fields = new_fields
                    if fields not in schemas:
                        schemas.append(fields)
            continue
        if not fields:
            continue
        values = line.split(' ')
        if len(values) == len(fields):
            row = dict(zip(fields, values))
        else:
            # Field-count mismatch: try every schema seen so far (most
            # recent first) so concatenated logs with different layouts
            # still parse instead of being silently dropped.
            row = None
            for cand in reversed(schemas):
                if len(cand) == len(values):
                    row = dict(zip(cand, values))
                    if cand != fields:
                        alt_schema_rows += 1
                    break
            if row is None:
                continue
        method = row.get('cs-method', '-')
        path = row.get('cs-uri-stem', '')
        query = row.get('cs-uri-query', '')
        status = row.get('sc-status', '0')
        time_taken = row.get('time-taken', '')
        sc_bytes = row.get('sc-bytes', '')
        dt_str = f"{row.get('date', '')} {row.get('time', '')}".strip()
        records.append({
            'source_type': 'iis',
            'remote_ip': row.get('c-ip'),
            'remote_user': row.get('cs-username', '-'),
            'time_local': dt_str,
            'method': method if method != '-' else None,
            'url': f"{path}?{query}" if query and query != '-' else path,
            'path': path,
            'query': query if query != '-' else '',
            'status': int(status) if status.isdigit() else None,
            'bytes': int(sc_bytes) if sc_bytes.isdigit() else 0,
            'referer': row.get('cs(Referer)', None),
            'ua': row.get('cs(User-Agent)', None),
            'request_time': (int(time_taken) / 1000.0) if time_taken.isdigit() else None,
            'upstream_time': None,
            'xff': row.get('cs(X-Forwarded-For)', None),
        })
    return records, alt_schema_rows


def parse_log_line(line, source_type):
    if source_type in ('nginx', 'mixed', 'unknown'):
        rec = parse_nginx_line(line)
        if rec:
            return rec
    if source_type in ('apache', 'mixed', 'unknown'):
        rec = parse_apache_line(line)
        if rec:
            return rec
    return None


# ---------------------------------------------------------------------------
# normalize_record
# ---------------------------------------------------------------------------

def normalize_record(raw):
    """Normalize parsed record to standard schema with client_ip extraction."""
    ts = parse_timestamp(raw.get('time_local'), raw.get('source_type'))
    client_ip = extract_client_ip(raw.get('remote_ip'), raw.get('xff'))
    return {
        'timestamp': ts,
        'source_type': raw.get('source_type'),
        'remote_ip': raw.get('remote_ip'),
        'xff': raw.get('xff'),
        'client_ip': client_ip,
        'method': raw.get('method'),
        'url': raw.get('url'),
        'path': raw.get('path'),
        'query': raw.get('query'),
        'status': raw.get('status'),
        'bytes': raw.get('bytes'),
        'ua': raw.get('ua'),
        'referer': raw.get('referer'),
        'request_time': raw.get('request_time'),
        'upstream_time': raw.get('upstream_time'),
    }


# ---------------------------------------------------------------------------
# aggregate_timeline
# ---------------------------------------------------------------------------

def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    if f == c:
        return round(s[f], 3)
    return round(s[f] * (c - k) + s[c] * (k - f), 3)


def aggregate_timeline(records):
    """Aggregate records by minute bucket."""
    buckets = defaultdict(lambda: {
        'count': 0, 'ips': set(), 'status_codes': Counter(),
        'request_times': [], 'upstream_times': [], 'bytes': 0,
    })
    for r in records:
        ts = r.get('timestamp')
        if not ts:
            continue
        key = ts.strftime('%Y-%m-%d %H:%M')
        b = buckets[key]
        b['count'] += 1
        if r.get('client_ip'):
            b['ips'].add(r['client_ip'])
        if r.get('status'):
            b['status_codes'][r['status']] += 1
        if r.get('request_time') is not None:
            b['request_times'].append(r['request_time'])
        if r.get('upstream_time') is not None:
            b['upstream_times'].append(r['upstream_time'])
        b['bytes'] += r.get('bytes', 0)

    timeline = []
    for k in sorted(buckets.keys()):
        b = buckets[k]
        status_codes = dict(b['status_codes'])
        timeline.append({
            'minute': k,
            'request_count': b['count'],
            'unique_ip': len(b['ips']),
            'qps': round(b['count'] / 60.0, 2),
            'status_codes': status_codes,
            'count_4xx': sum(v for s, v in status_codes.items() if 400 <= s < 500),
            'count_5xx': sum(v for s, v in status_codes.items() if 500 <= s < 600),
            'avg_request_time': round(sum(b['request_times']) / len(b['request_times']), 3) if b['request_times'] else None,
            'p95_request_time': percentile(b['request_times'], 95),
            'p95_upstream_time': percentile(b['upstream_times'], 95),
            'total_bytes': b['bytes'],
        })
    return timeline


# ---------------------------------------------------------------------------
# aggregate_dimensions
# ---------------------------------------------------------------------------

def aggregate_dimensions(records, top_n=20):
    ip_stats = defaultdict(lambda: {
        'count': 0, 'urls': Counter(), 'status_codes': Counter(),
        'bytes': 0, 'uas': set(), 'referers': set(), 'minute_buckets': Counter(),
    })
    url_stats = defaultdict(lambda: {
        'count': 0, 'ips': set(), 'status_codes': Counter(),
        'request_times': [], 'upstream_times': [], 'bytes': 0,
        'empty_referer': 0, 'uas': set(),
    })
    ua_stats = defaultdict(lambda: {
        'count': 0, 'ips': set(), 'urls': Counter(), 'status_codes': Counter(),
    })
    referer_stats = defaultdict(lambda: {
        'count': 0, 'ips': set(), 'urls': Counter(),
    })
    status_stats = Counter()
    total_bytes = 0
    total_count = len(records)

    for r in records:
        ip = r.get('client_ip')
        path = r.get('path') or r.get('url') or '/'
        ua = r.get('ua') or '(empty)'
        raw_ref = r.get('referer')
        ref = '(empty)' if raw_ref in (None, '', '-') else raw_ref
        status = r.get('status')
        ts = r.get('timestamp')
        b = r.get('bytes', 0)

        if ip:
            s = ip_stats[ip]
            s['count'] += 1
            s['urls'][path] += 1
            if status:
                s['status_codes'][status] += 1
            s['bytes'] += b
            s['uas'].add(ua)
            s['referers'].add(ref)
            if ts:
                s['minute_buckets'][ts.strftime('%Y-%m-%d %H:%M')] += 1

        url_stats[path]['count'] += 1
        if ip:
            url_stats[path]['ips'].add(ip)
        if status:
            url_stats[path]['status_codes'][status] += 1
        if r.get('request_time') is not None:
            url_stats[path]['request_times'].append(r['request_time'])
        if r.get('upstream_time') is not None:
            url_stats[path]['upstream_times'].append(r['upstream_time'])
        url_stats[path]['bytes'] += b
        if ref == '(empty)':
            url_stats[path]['empty_referer'] += 1
        url_stats[path]['uas'].add(ua)

        ua_stats[ua]['count'] += 1
        if ip:
            ua_stats[ua]['ips'].add(ip)
        ua_stats[ua]['urls'][path] += 1
        if status:
            ua_stats[ua]['status_codes'][status] += 1

        referer_stats[ref]['count'] += 1
        if ip:
            referer_stats[ref]['ips'].add(ip)
        referer_stats[ref]['urls'][path] += 1

        if status:
            status_stats[status] += 1
        total_bytes += b

    top_ips = []
    for ip, s in sorted(ip_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:top_n]:
        peak_qps = max(s['minute_buckets'].values()) if s['minute_buckets'] else 0
        ratio = round(s['count'] / total_count * 100, 2) if total_count else 0
        risk = 'critical' if peak_qps >= 500 or ratio > 20 else 'high' if peak_qps >= 100 or ratio > 5 else 'medium'
        top_ips.append({
            'client_ip': ip,
            'request_count': s['count'],
            'ratio': ratio,
            'peak_qps': peak_qps,
            'url_count': len(s['urls']),
            'top_url': s['urls'].most_common(1)[0][0] if s['urls'] else '-',
            'status_codes': dict(s['status_codes']),
            'ua_count': len(s['uas']),
            'referer_count': len(s['referers']),
            'bytes': s['bytes'],
            'risk': risk,
        })

    top_urls = []
    for url, s in sorted(url_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:top_n]:
        p95_req = percentile(s['request_times'], 95)
        p95_up = percentile(s['upstream_times'], 95)
        avg_time = round(sum(s['request_times']) / len(s['request_times']), 3) if s['request_times'] else None
        empty_ref_ratio = round(s['empty_referer'] / s['count'] * 100, 2) if s['count'] else 0
        ua_concentration = round(len(s['uas']) / s['count'] * 100, 2) if s['count'] else 0
        risk = 'critical' if s['count'] > total_count * 0.3 else 'high' if s['count'] > total_count * 0.1 else 'medium'
        top_urls.append({
            'url': url,
            'request_count': s['count'],
            'unique_ip': len(s['ips']),
            'avg_req_per_ip': round(s['count'] / len(s['ips']), 2) if s['ips'] else 0,
            'status_codes': dict(s['status_codes']),
            'bytes': s['bytes'],
            'avg_request_time': avg_time,
            'p95_request_time': p95_req,
            'p95_upstream_time': p95_up,
            'empty_referer_ratio': empty_ref_ratio,
            'ua_concentration': ua_concentration,
            'risk': risk,
        })

    ua_analysis = []
    for ua, s in sorted(ua_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:top_n]:
        risk = 'high' if ua == '(empty)' or any(k in ua.lower() for k in SUSPICIOUS_UA_KEYWORDS) else 'medium'
        top_url = s['urls'].most_common(1)[0][0] if s['urls'] else '-'
        ua_analysis.append({
            'ua': ua,
            'count': s['count'],
            'ip_count': len(s['ips']),
            'url_count': len(s['urls']),
            'status_codes': dict(s['status_codes']),
            'top_url': top_url,
            'risk': risk,
        })

    referer_analysis = []
    for ref, s in sorted(referer_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:top_n]:
        risk = 'high' if ref == '(empty)' else 'low'
        referer_analysis.append({
            'referer': ref,
            'count': s['count'],
            'ip_count': len(s['ips']),
            'top_url': s['urls'].most_common(1)[0][0] if s['urls'] else '-',
            'risk': risk,
        })

    empty_referer_ratio = round(referer_stats.get('(empty)', {}).get('count', 0) / total_count * 100, 2) if total_count else 0

    # Traffic analysis
    ip_bytes = defaultdict(int)
    url_bytes = defaultdict(int)
    for r in records:
        if r.get('client_ip'):
            ip_bytes[r['client_ip']] += r.get('bytes', 0)
        if r.get('path'):
            url_bytes[r['path']] += r.get('bytes', 0)

    top_traffic_ips = sorted(ip_bytes.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_traffic_urls = sorted(url_bytes.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # Latency analysis
    all_request_times = [r['request_time'] for r in records if r.get('request_time') is not None]
    slow_requests = [r for r in records if r.get('request_time') and r['request_time'] > 3.0]
    slow_by_url = Counter(r['path'] for r in slow_requests if r.get('path'))
    slow_by_ip = Counter(r['client_ip'] for r in slow_requests if r.get('client_ip'))

    return {
        'top_ips': top_ips,
        'top_urls': top_urls,
        'ua_analysis': ua_analysis,
        'referer_analysis': referer_analysis,
        'empty_referer_ratio': empty_referer_ratio,
        'status_stats': dict(status_stats),
        'total_requests': total_count,
        'total_unique_ips': len(ip_stats),
        'total_bytes': total_bytes,
        'top_traffic_ips': top_traffic_ips,
        'top_traffic_urls': top_traffic_urls,
        'avg_response_size': round(total_bytes / total_count, 0) if total_count else 0,
        'latency_summary': {
            'avg_request_time': round(sum(all_request_times) / len(all_request_times), 3) if all_request_times else None,
            'p95_request_time': percentile(all_request_times, 95),
            'p99_request_time': percentile(all_request_times, 99),
            'slow_request_count': len(slow_requests),
            'slow_top_urls': slow_by_url.most_common(5),
            'slow_top_ips': slow_by_ip.most_common(5),
        },
    }


# ---------------------------------------------------------------------------
# IP x URL cross analysis
# ---------------------------------------------------------------------------

def ip_url_cross_analysis(records, total_requests=None, total_unique_ips=None):
    """Cross-analysis of IP and URL for attack pattern detection.
    Thresholds scale dynamically with log volume to remain effective
    for both small and large log files.
    """
    ip_url = defaultdict(Counter)
    for r in records:
        ip = r.get('client_ip')
        path = r.get('path')
        if ip and path:
            ip_url[ip][path] += 1

    total_req = total_requests or len(records)
    total_ips = total_unique_ips or len(ip_url)
    total_unique_urls = len(set(r.get('path') for r in records if r.get('path')))

    # Dynamic thresholds based on log volume, capped to avoid excessive
    # values when sites have many unique URLs (e.g. IDs in paths).
    cc_threshold = max(20, int(total_req * 0.02))
    scan_threshold = max(10, min(25, int(total_unique_urls * 0.015)))
    crawler_url_threshold = max(6, min(15, int(total_unique_urls * 0.01)))
    crawler_total_threshold = max(15, int(total_req * 0.015))
    proxy_pool_threshold = max(10, min(30, int(total_ips * 0.1)))

    single_ip_cc = []
    proxy_pool = defaultdict(int)
    scan_ips = []
    crawler_ips = []

    for ip, urls in ip_url.items():
        total = sum(urls.values())
        unique_urls = len(urls)
        top_url, top_count = urls.most_common(1)[0] if urls else (None, 0)

        if unique_urls == 1 and top_count >= cc_threshold:
            single_ip_cc.append({
                'client_ip': ip,
                'url': top_url,
                'count': top_count,
            })
        elif unique_urls >= scan_threshold:
            scan_ips.append({
                'client_ip': ip,
                'unique_urls': unique_urls,
                'total': total,
            })
        elif unique_urls >= crawler_url_threshold and total >= crawler_total_threshold:
            crawler_ips.append({
                'client_ip': ip,
                'unique_urls': unique_urls,
                'total': total,
            })

        if top_url:
            proxy_pool[top_url] += 1

    return {
        'single_ip_cc': sorted(single_ip_cc, key=lambda x: x['count'], reverse=True)[:10],
        'scan_ips': sorted(scan_ips, key=lambda x: x['unique_urls'], reverse=True)[:10],
        'crawler_ips': sorted(crawler_ips, key=lambda x: x['total'], reverse=True)[:10],
        'proxy_pool_targets': sorted(
            [(url, cnt) for url, cnt in proxy_pool.items() if cnt >= proxy_pool_threshold],
            key=lambda x: x[1], reverse=True
        )[:5],
    }


# ---------------------------------------------------------------------------
# detect_qps_surge
# ---------------------------------------------------------------------------

def _adjacent_minutes(minute_a, minute_b):
    """True when two '%Y-%m-%d %H:%M' bucket keys are truly adjacent in
    time (gap <= 1 minute). Surge/drop comparisons must only run between
    adjacent buckets; gaps in the timeline (empty minutes) would otherwise
    produce false surge/drop signals."""
    try:
        a = datetime.strptime(minute_a, '%Y-%m-%d %H:%M')
        b = datetime.strptime(minute_b, '%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return False
    return timedelta(0) < (b - a) <= timedelta(minutes=1)

def detect_qps_surge(timeline, surge_threshold_pct=300.0, surge_threshold_abs=500.0,
                     drop_threshold_pct=-70.0):
    """
    Analyze minute-level QPS timeline to detect sudden surges or drops
    between adjacent time windows.

    Parameters:
        timeline: list of dicts from aggregate_timeline(), each containing 'minute' and 'qps'
        surge_threshold_pct: percentage increase threshold for flagging a surge (default 300%)
        surge_threshold_abs: absolute QPS increase threshold (default 500)
        drop_threshold_pct: percentage decrease threshold for flagging a drop (default -70%)

    Returns:
        list of dicts: [{'minute': str, 'type': 'surge'|'drop', 'from_qps': float,
                          'to_qps': float, 'delta_pct': float, 'delta_abs': float}, ...]
    """
    if not timeline or len(timeline) < 2:
        return []

    surges = []
    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        curr = timeline[i]
        if not _adjacent_minutes(prev.get('minute', ''), curr.get('minute', '')):
            continue
        prev_qps = prev.get('qps', 0) or 0.0
        curr_qps = curr.get('qps', 0) or 0.0

        if prev_qps <= 0:
            # Avoid division by zero; treat any positive QPS as infinite surge
            if curr_qps > 0:
                surges.append({
                    'minute': curr['minute'],
                    'type': 'surge',
                    'from_qps': prev_qps,
                    'to_qps': curr_qps,
                    'delta_pct': float('inf'),
                    'delta_abs': round(curr_qps - prev_qps, 2),
                })
            continue

        delta_abs = round(curr_qps - prev_qps, 2)
        delta_pct = round((delta_abs / prev_qps) * 100, 1)

        # Surge detection
        if delta_pct >= surge_threshold_pct and delta_abs >= surge_threshold_abs:
            surges.append({
                'minute': curr['minute'],
                'type': 'surge',
                'from_qps': prev_qps,
                'to_qps': curr_qps,
                'delta_pct': delta_pct,
                'delta_abs': delta_abs,
            })
        # Drop detection
        elif delta_pct <= drop_threshold_pct:
            surges.append({
                'minute': curr['minute'],
                'type': 'drop',
                'from_qps': prev_qps,
                'to_qps': curr_qps,
                'delta_pct': delta_pct,
                'delta_abs': delta_abs,
            })

    return surges


# ---------------------------------------------------------------------------
# detect_bandwidth_surge
# ---------------------------------------------------------------------------

def detect_bandwidth_surge(timeline, surge_threshold_pct=300.0, surge_threshold_abs_mb=100.0,
                           drop_threshold_pct=-70.0):
    """
    Analyze minute-level bandwidth (total_bytes) to detect sudden surges or drops.

    Parameters:
        timeline: list of dicts from aggregate_timeline(), each containing 'minute' and 'total_bytes'
        surge_threshold_pct: percentage increase threshold (default 300%)
        surge_threshold_abs_mb: absolute increase threshold in MB (default 100)
        drop_threshold_pct: percentage decrease threshold (default -70%)

    Returns:
        list of dicts: [{'minute': str, 'type': 'surge'|'drop', 'from_bytes': int,
                          'to_bytes': int, 'delta_pct': float, 'delta_abs': int,
                          'delta_abs_mb': float}, ...]
    """
    if not timeline or len(timeline) < 2:
        return []

    surges = []
    abs_bytes = surge_threshold_abs_mb * 1024 * 1024

    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        curr = timeline[i]
        if not _adjacent_minutes(prev.get('minute', ''), curr.get('minute', '')):
            continue
        prev_bytes = prev.get('total_bytes', 0) or 0
        curr_bytes = curr.get('total_bytes', 0) or 0

        if prev_bytes <= 0:
            if curr_bytes > 0 and curr_bytes >= abs_bytes:
                surges.append({
                    'minute': curr['minute'],
                    'type': 'surge',
                    'from_bytes': prev_bytes,
                    'to_bytes': curr_bytes,
                    'delta_pct': float('inf'),
                    'delta_abs': curr_bytes - prev_bytes,
                    'delta_abs_mb': round((curr_bytes - prev_bytes) / (1024 * 1024), 2),
                })
            continue

        delta_abs = curr_bytes - prev_bytes
        delta_pct = round((delta_abs / prev_bytes) * 100, 1)

        if delta_pct >= surge_threshold_pct and abs(delta_abs) >= abs_bytes:
            surges.append({
                'minute': curr['minute'],
                'type': 'surge',
                'from_bytes': prev_bytes,
                'to_bytes': curr_bytes,
                'delta_pct': delta_pct,
                'delta_abs': delta_abs,
                'delta_abs_mb': round(delta_abs / (1024 * 1024), 2),
            })
        elif delta_pct <= drop_threshold_pct:
            surges.append({
                'minute': curr['minute'],
                'type': 'drop',
                'from_bytes': prev_bytes,
                'to_bytes': curr_bytes,
                'delta_pct': delta_pct,
                'delta_abs': delta_abs,
                'delta_abs_mb': round(delta_abs / (1024 * 1024), 2),
            })

    return surges


# ---------------------------------------------------------------------------
# detect_status_surge
# ---------------------------------------------------------------------------

def detect_status_surge(timeline, status_filter='5xx',
                        surge_threshold_pct=300.0, surge_threshold_abs=50.0,
                        drop_threshold_pct=-70.0):
    """
    Analyze minute-level status code counts to detect sudden surges or drops.

    Parameters:
        timeline: list of dicts from aggregate_timeline(), each containing 'minute' and 'status_codes'
        status_filter: '4xx', '5xx', or a list of specific status codes (default '5xx')
        surge_threshold_pct: percentage increase threshold (default 300%)
        surge_threshold_abs: absolute count increase threshold (default 50)
        drop_threshold_pct: percentage decrease threshold (default -70%)

    Returns:
        list of dicts: [{'minute': str, 'type': 'surge'|'drop', 'status_filter': str,
                          'from_count': int, 'to_count': int, 'delta_pct': float,
                          'delta_abs': int}, ...]
    """
    if not timeline or len(timeline) < 2:
        return []

    def _count_status(status_codes, filter_val):
        if filter_val == '4xx':
            return sum(v for s, v in status_codes.items() if 400 <= s < 500)
        elif filter_val == '5xx':
            return sum(v for s, v in status_codes.items() if 500 <= s < 600)
        elif isinstance(filter_val, (list, tuple)):
            return sum(v for s, v in status_codes.items() if s in filter_val)
        else:
            return status_codes.get(filter_val, 0)

    surges = []
    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        curr = timeline[i]
        if not _adjacent_minutes(prev.get('minute', ''), curr.get('minute', '')):
            continue
        prev_count = _count_status(prev.get('status_codes', {}), status_filter)
        curr_count = _count_status(curr.get('status_codes', {}), status_filter)

        if prev_count <= 0:
            if curr_count > 0 and curr_count >= surge_threshold_abs:
                surges.append({
                    'minute': curr['minute'],
                    'type': 'surge',
                    'status_filter': str(status_filter),
                    'from_count': prev_count,
                    'to_count': curr_count,
                    'delta_pct': float('inf'),
                    'delta_abs': curr_count - prev_count,
                })
            continue

        delta_abs = curr_count - prev_count
        delta_pct = round((delta_abs / prev_count) * 100, 1)

        if delta_pct >= surge_threshold_pct and abs(delta_abs) >= surge_threshold_abs:
            surges.append({
                'minute': curr['minute'],
                'type': 'surge',
                'status_filter': str(status_filter),
                'from_count': prev_count,
                'to_count': curr_count,
                'delta_pct': delta_pct,
                'delta_abs': delta_abs,
            })
        elif delta_pct <= drop_threshold_pct:
            surges.append({
                'minute': curr['minute'],
                'type': 'drop',
                'status_filter': str(status_filter),
                'from_count': prev_count,
                'to_count': curr_count,
                'delta_pct': delta_pct,
                'delta_abs': delta_abs,
            })

    return surges


# ---------------------------------------------------------------------------
# detect_attack_type
# ---------------------------------------------------------------------------

def detect_attack_type(records, timeline, dimensions, cross):
    attacks = []
    total_req = dimensions['total_requests']
    if total_req == 0:
        return attacks

    # 1. Single-IP High-Frequency CC
    for ip_info in dimensions['top_ips'][:5]:
        if ip_info['peak_qps'] >= 100 or ip_info['request_count'] > 1000:
            attacks.append({
                'type': 'Single-IP high-frequency CC',
                'target': ip_info['client_ip'],
                'confidence': 'High',
                'evidence': f"peak QPS {ip_info['peak_qps']}, total requests {ip_info['request_count']}, URL: {ip_info['top_url']}",
            })
            break

    # 2. Proxy-Pool Distributed CC
    unique_ips = dimensions.get('total_unique_ips', len(dimensions['top_ips']))
    top_url_ratio = (dimensions['top_urls'][0]['request_count'] / total_req) if dimensions['top_urls'] else 0
    proxy_pool_evidence = []
    if unique_ips > 500:
        proxy_pool_evidence.append(f"{unique_ips} unique IPs")
    if dimensions['top_urls'] and dimensions['top_urls'][0]['avg_req_per_ip'] < 50:
        proxy_pool_evidence.append(f"avg {dimensions['top_urls'][0]['avg_req_per_ip']} requests per IP")
    if top_url_ratio > 0.6:
        proxy_pool_evidence.append(f"URL concentration {top_url_ratio:.1%}")
    if dimensions['empty_referer_ratio'] > 80:
        proxy_pool_evidence.append(f"empty Referer {dimensions['empty_referer_ratio']}%")
    if dimensions['ua_analysis']:
        top_ua_ips = dimensions['ua_analysis'][0]['ip_count']
        if top_ua_ips > 100:
            proxy_pool_evidence.append(f"same UA used by {top_ua_ips} IPs")
    if cross['proxy_pool_targets']:
        proxy_pool_evidence.append(f"{cross['proxy_pool_targets'][0][1]} IPs concentrated on {cross['proxy_pool_targets'][0][0]}")

    if len(proxy_pool_evidence) >= 3:
        attacks.append({
            'type': 'Proxy-pool distributed bot CC',
            'target': dimensions['top_urls'][0]['url'] if dimensions['top_urls'] else '-',
            'confidence': 'High',
            'evidence': '; '.join(proxy_pool_evidence),
        })
    elif len(proxy_pool_evidence) >= 2:
        attacks.append({
            'type': 'Proxy-pool distributed bot CC',
            'target': dimensions['top_urls'][0]['url'] if dimensions['top_urls'] else '-',
            'confidence': 'Medium',
            'evidence': '; '.join(proxy_pool_evidence),
        })

    # 3. API Abuse
    api_records = [r for r in records if API_PATTERN.search(r.get('path') or '')]
    if len(api_records) > 200 and (len(api_records) / total_req) > 0.3:
        api_200 = sum(1 for r in api_records if r.get('status') == 200)
        api_200_ratio = api_200 / len(api_records) if api_records else 0
        if api_200_ratio > 0.8:
            attacks.append({
                'type': 'API Abuse',
                'target': 'API endpoints',
                'confidence': 'Medium',
                'evidence': f"{len(api_records)} API requests, 200 ratio {api_200_ratio:.1%}",
            })

    # 4. Scanning / Probing
    scan_records = [r for r in records if r.get('path') in SCAN_PATHS]
    not_found = [r for r in records if r.get('status') == 404]
    if scan_records:
        scan_404 = sum(1 for r in scan_records if r.get('status') == 404)
        if scan_404 / len(scan_records) > 0.4:
            attacks.append({
                'type': 'Scanning/probing',
                'target': 'Sensitive paths',
                'confidence': 'Medium',
                'evidence': f"{len(scan_records)} probe requests, {scan_404} returned 404",
            })
    if not_found and len(not_found) > 50:
        nf_ratio = len(not_found) / total_req
        if nf_ratio > 0.1:
            attacks.append({
                'type': 'Scanning/probing',
                'target': 'Many nonexistent paths',
                'confidence': 'Medium',
                'evidence': f"{len(not_found)} 404 requests, ratio {nf_ratio:.1%}",
            })

    # 5. Login Brute-Force
    login_records = [r for r in records
                     if r.get('path') in LOGIN_PATHS and r.get('method') == 'POST']
    if len(login_records) > 20:
        login_fail = sum(1 for r in login_records if r.get('status') in (401, 403))
        login_redirect = sum(1 for r in login_records if r.get('status') == 302)
        if (login_fail + login_redirect) / len(login_records) > 0.5:
            attacks.append({
                'type': 'Credential stuffing/login brute force',
                'target': 'Login endpoint',
                'confidence': 'Medium',
                'evidence': f"{len(login_records)} POST login requests, {login_fail + login_redirect} failed/redirected",
            })

    # 6. Abnormal Crawler
    tool_ua = {'curl', 'wget', 'python-requests', 'go-http-client', 'java',
               'apache-httpclient', 'okhttp', 'sqlmap', 'masscan'}
    crawler_records = [r for r in records if r.get('ua') and any(t in r['ua'].lower() for t in tool_ua)]
    if len(crawler_records) > 100:
        attacks.append({
            'type': 'Abnormal crawler',
            'target': 'Detail/list pages',
            'confidence': 'Low',
            'evidence': f"{len(crawler_records)} requests with tool UAs",
        })
    # Fake browser detection
    if dimensions['ua_analysis']:
        top_ua = dimensions['ua_analysis'][0]
        if 'chrome' in top_ua['ua'].lower() or 'safari' in top_ua['ua'].lower():
            if top_ua['ip_count'] > 100 and top_ua['url_count'] > 5:
                attacks.append({
                    'type': 'Abnormal crawler (spoofed browser)',
                    'target': 'Detail/list pages',
                    'confidence': 'Medium',
                    'evidence': f"same browser UA used by {top_ua['ip_count']} IPs, visiting {top_ua['url_count']} URLs",
                })

    # 7. QPS Surge / Drop
    qps_surges = detect_qps_surge(timeline)
    if qps_surges:
        surge_events = [e for e in qps_surges if e['type'] == 'surge']
        drop_events = [e for e in qps_surges if e['type'] == 'drop']
        evidence_parts = []
        if surge_events:
            top_surge = max(surge_events, key=lambda x: x['delta_pct'])
            evidence_parts.append(
                f"QPS surged {top_surge['delta_pct']:.0f}% ({top_surge['from_qps']:.1f} -> {top_surge['to_qps']:.1f}) "
                f"at {top_surge['minute']}"
            )
        if drop_events:
            top_drop = min(drop_events, key=lambda x: x['delta_pct'])
            evidence_parts.append(
                f"QPS dropped {top_drop['delta_pct']:.0f}% ({top_drop['from_qps']:.1f} -> {top_drop['to_qps']:.1f}) "
                f"at {top_drop['minute']}"
            )
        confidence = 'High' if len(surge_events) >= 2 else 'Medium'
        attacks.append({
            'type': 'QPS surge',
            'target': 'Traffic burst',
            'confidence': confidence,
            'evidence': '; '.join(evidence_parts),
        })

    # 7b. Bandwidth Surge / Drop
    bw_surges = detect_bandwidth_surge(timeline)
    if bw_surges:
        surge_events = [e for e in bw_surges if e['type'] == 'surge']
        drop_events = [e for e in bw_surges if e['type'] == 'drop']
        evidence_parts = []
        if surge_events:
            top_surge = max(surge_events, key=lambda x: x['delta_pct'])
            evidence_parts.append(
                f"bandwidth surged {top_surge['delta_pct']:.0f}% "
                f"({human_readable_size(top_surge['from_bytes'])} -> {human_readable_size(top_surge['to_bytes'])}) "
                f"at {top_surge['minute']}"
            )
        if drop_events:
            top_drop = min(drop_events, key=lambda x: x['delta_pct'])
            evidence_parts.append(
                f"bandwidth dropped {top_drop['delta_pct']:.0f}% "
                f"({human_readable_size(top_drop['from_bytes'])} -> {human_readable_size(top_drop['to_bytes'])}) "
                f"at {top_drop['minute']}"
            )
        confidence = 'High' if len(surge_events) >= 2 else 'Medium'
        attacks.append({
            'type': 'Bandwidth surge',
            'target': 'Traffic burst',
            'confidence': confidence,
            'evidence': '; '.join(evidence_parts),
        })

    # 7c. Status Code Surge (5xx / 4xx)
    status_evidence = []
    for status_filter in ('5xx', '4xx'):
        status_surges = detect_status_surge(timeline, status_filter=status_filter)
        if status_surges:
            surge_events = [e for e in status_surges if e['type'] == 'surge']
            if surge_events:
                top_surge = max(surge_events, key=lambda x: x['delta_abs'])
                status_evidence.append(
                    f"{status_filter} surged by {top_surge['delta_abs']:+d} requests "
                    f"({top_surge['from_count']} -> {top_surge['to_count']}) "
                    f"at {top_surge['minute']}"
                )
    if status_evidence:
        attacks.append({
            'type': 'Status code surge',
            'target': 'Error response surge',
            'confidence': 'High' if len(status_evidence) >= 2 else 'Medium',
            'evidence': '; '.join(status_evidence),
        })

    # 8. Slow Resource Consumption
    slow_timeline = [t for t in timeline if (t.get('p95_request_time') and t['p95_request_time'] > 5.0)
                     or (t.get('p95_upstream_time') and t['p95_upstream_time'] > 3.0)]
    if len(slow_timeline) > 3:
        attacks.append({
            'type': 'Slow resource consumption',
            'target': 'Dynamic endpoints',
            'confidence': 'Medium',
            'evidence': f"{len(slow_timeline)} time windows with P95 latency above threshold",
        })

    # 9. Origin Direct-Connect Risk
    direct_count = sum(1 for r in records if r.get('remote_ip') == r.get('client_ip'))
    if total_req > 0 and (direct_count / total_req) > 0.3:
        attacks.append({
            'type': 'Origin direct-access risk',
            'target': 'Origin server',
            'confidence': 'Low',
            'evidence': f"{direct_count}/{total_req} ({direct_count/total_req:.1%}) requests with remote_ip == client_ip",
        })

    return attacks


# ---------------------------------------------------------------------------
# compute_block_targets - shared by text & markdown report generators
# ---------------------------------------------------------------------------

def compute_block_targets(dimensions, attacks, top_n=20):
    """Compute high-risk IPs and precise CIDR groups for mitigation.

    Returns (high_risk_ips, cidr_groups, block_cidrs).
      - high_risk_ips: list of IP strings with risk critical/high
      - cidr_groups: list of (cidr_str, ip_list) from precise aggregation
      - block_cidrs: list of CIDR strings for deny rules (deduped, /32 excluded when covered by broader CIDR)
    """
    high_risk_ips = [ip['client_ip'] for ip in dimensions['top_ips'] if ip['risk'] in ('critical', 'high')]

    # Primary: aggregate high-risk IPs precisely
    cidr_groups = aggregate_ips_to_precise_cidrs(high_risk_ips)

    # Fallback: when no meaningful aggregation (empty or all /32) but attacks
    # detected, retry with the risk-filtered candidate pool ONLY (critical /
    # high IPs). Normal-traffic IPs must never be merged into block targets.
    has_real_aggregation = any(not c.endswith('/32') for c, _ in cidr_groups)
    if not has_real_aggregation and attacks and dimensions['top_ips']:
        fallback_ips = list(dict.fromkeys(
            ip['client_ip'] for ip in dimensions['top_ips']
            if ip['risk'] in ('critical', 'high')
        ))
        cidr_groups = aggregate_ips_to_precise_cidrs(fallback_ips)

    # Build deny list:
    #   - /32 singles: only high-risk IPs (critical/high)
    #   - aggregated subnets (non-/32): require at least one high-risk
    #     member, otherwise display-only (never advise blocking subnets that
    #     contain only normal-traffic IPs)
    high_risk_set = set(high_risk_ips)
    block_cidrs = []
    for cidr_str, ip_list in cidr_groups:
        if cidr_str.endswith('/32'):
            if ip_list[0] in high_risk_set:
                block_cidrs.append(cidr_str)
        elif any(ip in high_risk_set for ip in ip_list):
            block_cidrs.append(cidr_str)

    return high_risk_ips, cidr_groups, block_cidrs


# ---------------------------------------------------------------------------
# Dual-audience rendering helpers: Executive Summary + Structured Findings
# (rendering layer only - no detection logic or thresholds here)
# ---------------------------------------------------------------------------

SEVERITY_BY_ATTACK = {
    'Single-IP high-frequency CC': {'High': 'critical', 'Medium': 'high', 'Low': 'medium'},
    'Proxy-pool distributed bot CC': {'High': 'critical', 'Medium': 'high', 'Low': 'medium'},
    'API Abuse': {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
    'Scanning/probing': {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
    'Credential stuffing/login brute force': {'High': 'critical', 'Medium': 'high', 'Low': 'medium'},
    'Abnormal crawler': {'High': 'medium', 'Medium': 'medium', 'Low': 'low'},
    'Abnormal crawler (spoofed browser)': {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
    'QPS surge': {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
    'Bandwidth surge': {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
    'Status code surge': {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
    'Slow resource consumption': {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
    'Origin direct-access risk': {'High': 'medium', 'Medium': 'low', 'Low': 'low'},
}

RISK_ORDER = {'none': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}


def attack_severity(attack):
    """Map a detected attack (type + confidence) to a severity level."""
    return SEVERITY_BY_ATTACK.get(attack['type'], {}).get(attack['confidence'], 'medium')


def overall_risk_level(attacks):
    """Highest severity across all detected attacks; 'none' when no attack."""
    if not attacks:
        return 'none'
    return max((attack_severity(a) for a in attacks), key=lambda s: RISK_ORDER[s])


def missing_field_notes(records):
    """Shared missing-field detection used by all report sections."""
    missing = []
    if not any(r.get('xff') for r in records):
        missing.append('xff (cannot identify real client IP)')
    if not any(r.get('ua') for r in records):
        missing.append('ua (cannot detect bot characteristics)')
    if not any(r.get('referer') for r in records):
        missing.append('referer (cannot detect direct API hits)')
    if not any(r.get('request_time') for r in records):
        missing.append('request_time (cannot assess origin consumption)')
    return missing


def build_executive_summary(records, timeline, dimensions, attacks, block_cidrs):
    """Build the non-technical executive summary components.

    Returns a dict with keys: risk, conclusion, explanation (list of
    sentences), actions (ordered list of plain-language recommendations).
    """
    total = dimensions['total_requests']
    risk = overall_risk_level(attacks)
    types_present = {a['type'] for a in attacks}
    top_ip = dimensions['top_ips'][0] if dimensions['top_ips'] else None
    top_url = dimensions['top_urls'][0] if dimensions['top_urls'] else None

    if not attacks:
        conclusion = (f"No attack detected. Overall risk level: NONE. "
                      f"The analyzed traffic ({total:,} requests) shows no obvious attack patterns.")
        explanation = [
            f"We checked {total:,} requests to your website and did not find signs of an attack.",
            "Traffic looks like regular visitors: requests are spread across many addresses "
            "and pages, with no suspicious bursts or repeated failures.",
            "No urgent action is needed; keep an eye on future traffic for sudden changes.",
        ]
        actions = [
            "No urgent action is needed right now.",
            "Consider adding rate limiting (a speed limit for requests) on key pages such as login.",
            "Save your access logs regularly so future incidents can be analyzed quickly.",
        ]
        return {'risk': risk, 'conclusion': conclusion, 'explanation': explanation, 'actions': actions}

    attack_count = len(attacks)
    conclusion = (f"ATTACK DETECTED: {attack_count} attack pattern(s) found. "
                  f"Overall risk level: {risk.upper()}.")

    explanation = []
    for a in attacks:
        t = a['type']
        if t == 'Single-IP high-frequency CC' and top_ip:
            window_hint = ""
            if timeline:
                window_hint = (f" between {timeline[0]['minute']} and {timeline[-1]['minute']}")
            explanation.append(
                f"One internet address ({top_ip['client_ip']}) sent {top_ip['request_count']:,} requests"
                f"{window_hint} - like someone ringing your doorbell thousands of times "
                f"non-stop, trying to overwhelm your website.")
        elif t == 'Proxy-pool distributed bot CC':
            explanation.append(
                "Many different addresses are quietly working together, all aiming at the same page "
                "with a low individual rate - like a crowd taking turns to knock so that no single "
                "person looks suspicious.")
        elif t == 'Credential stuffing/login brute force':
            explanation.append(
                "Automated programs are trying to log in again and again, guessing passwords - "
                "like someone repeatedly trying different keys on your front door.")
        elif t == 'Scanning/probing':
            explanation.append(
                "Someone is testing many web addresses to find hidden files or weaknesses - "
                "like a burglar trying every window to see which one is open.")
        elif t == 'API Abuse':
            explanation.append(
                "Your site's programming interfaces (APIs, the doors apps use to fetch data) "
                "are being called abnormally often, which can waste server resources or harvest data.")
        elif t.startswith('Abnormal crawler'):
            explanation.append(
                "Automated programs are copying your pages at an unusual scale, "
                "which can steal content and slow the site down for real visitors.")
        elif t == 'QPS surge':
            explanation.append(
                "The number of requests per second jumped suddenly - like a quiet street "
                "filling with traffic out of nowhere. Legitimate viral traffic can look similar, "
                "so this needs a human look.")
        elif t == 'Bandwidth surge':
            explanation.append(
                "The amount of data leaving your server spiked suddenly, "
                "which can raise hosting costs and slow the site down.")
        elif t == 'Status code surge':
            explanation.append(
                "Your website suddenly started returning many more errors than usual, "
                "a sign that something is under pressure or failing.")
        elif t == 'Slow resource consumption':
            explanation.append(
                "Requests are taking unusually long to finish, tying up your server's attention - "
                "like callers who keep the phone line open without saying anything.")
        elif t == 'Origin direct-access risk':
            explanation.append(
                "Some visitors reach your server directly instead of through your protective "
                "front layer (CDN/WAF, a shield service that filters traffic first), "
                "which weakens your defenses.")
    if top_url:
        explanation.append(
            f"The most targeted page was {top_url['url']} "
            f"({top_url['request_count']:,} of {total:,} requests).")
    if risk in ('high', 'critical'):
        explanation.append(
            "If this continues, your website may slow down or become unavailable for real users.")
    else:
        explanation.append(
            "The immediate impact appears limited, but the pattern deserves attention "
            "before it grows.")

    actions = []
    if block_cidrs:
        shown = block_cidrs[:5]
        more = f" and {len(block_cidrs) - len(shown)} more" if len(block_cidrs) > len(shown) else ""
        actions.append(
            f"Block the attack sources: deny {', '.join(shown)}{more} in your firewall or "
            f"security group (the addresses identified as attack sources).")
    elif top_ip:
        actions.append(
            f"Block the attack source {top_ip['client_ip']} in your firewall or security group.")
    if 'Credential stuffing/login brute force' in types_present:
        actions.append(
            "Enable account lockout or CAPTCHA (a human-check puzzle) on the login page, "
            "and warn users who may be affected.")
    if any(t in types_present for t in ('Single-IP high-frequency CC',
                                        'Proxy-pool distributed bot CC', 'API Abuse')):
        actions.append(
            "Add rate limiting (a per-address speed limit for requests) on the most targeted pages.")
    if any(t in types_present for t in ('Proxy-pool distributed bot CC', 'Abnormal crawler',
                                        'Abnormal crawler (spoofed browser)',
                                        'Single-IP high-frequency CC')):
        actions.append(
            "Enable bot management / human verification (e.g. a WAF challenge that separates "
            "real visitors from automated scripts).")
    if any(t in types_present for t in ('QPS surge', 'Bandwidth surge', 'Slow resource consumption',
                                        'Status code surge')):
        actions.append(
            "Put a CDN or DCDN (a caching shield in front of your server) in place to absorb "
            "traffic spikes and protect the origin.")
    if 'Origin direct-access risk' in types_present:
        actions.append(
            "Route traffic through your CDN/WAF and block direct access to the origin server "
            "so all requests are filtered first.")
    actions.append("Keep monitoring the traffic over the next hours; repeat this analysis "
                   "after applying the fixes to confirm the attack stopped.")
    actions = actions[:5]

    return {'risk': risk, 'conclusion': conclusion, 'explanation': explanation, 'actions': actions}


def build_structured_findings(records, timeline, dimensions, attacks):
    """Build the machine-readable findings dict (JSON-serializable, ASCII only)."""
    total = dimensions['total_requests']
    fmt = records[0].get('source_type', 'unknown') if records else 'unknown'

    attack_entries = []
    for a in attacks:
        attack_entries.append({
            'type': a['type'],
            'severity': attack_severity(a),
            'evidence_count': max(1, len([p for p in a['evidence'].split('; ') if p])),
        })

    top_sources = [{'ip': ip['client_ip'], 'request_count': ip['request_count']}
                   for ip in dimensions['top_ips'][:5]]

    time_window = {
        'start': timeline[0]['minute'] if timeline else None,
        'end': timeline[-1]['minute'] if timeline else None,
    }

    return {
        'overall_risk': overall_risk_level(attacks),
        'attack_types': attack_entries,
        'top_attack_sources': top_sources,
        'time_window': time_window,
        'total_requests': total,
        'format': fmt,
        'data_quality_notes': missing_field_notes(records),
    }


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

def generate_report(records, timeline, dimensions, cross, attacks, output_path=None, top_n=20,
                    analyzed_file=None):
    lines = []
    total = dimensions['total_requests']

    high_risk_ips, cidr_groups, block_cidrs = compute_block_targets(dimensions, attacks, top_n)

    def conf_icon(c):
        return {'High': '[HIGH]', 'Medium': '[MED] ', 'Low': '[LOW] '}.get(c, '[?]   ')

    def sep(char='-', width=70):
        lines.append(char * width)

    def section(title, width=70):
        lines.append("")
        sep('=', width)
        lines.append(f"  {title}")
        sep('-', width)

    # -- Title --
    sep('=', 70)
    lines.append("        Origin Web Access Log Security Analysis Report")
    sep('=', 70)
    lines.append(f"  Analysis sample : {total:,} records")
    if records:
        src = records[0].get('source_type', 'unknown')
        lines.append(f"  Log format      : {src.upper()}")
    if analyzed_file:
        lines.append(f"  Analyzed file   : {analyzed_file}")
    lines.append("")

    # 0. Executive Summary (non-technical audience)
    summary = build_executive_summary(records, timeline, dimensions, attacks, block_cidrs)
    section("0. Executive Summary")
    lines.append(f"  Conclusion : {summary['conclusion']}")
    lines.append("")
    lines.append("  Plain language explanation:")
    for sent in summary['explanation']:
        lines.append(f"    {sent}")
    lines.append("")
    lines.append("  What you should do:")
    for i, act in enumerate(summary['actions'], 1):
        lines.append(f"    {i}. {act}")

    # 1. Attack Conclusion
    section("1. Attack Conclusion")
    if attacks:
        for a in attacks:
            icon = conf_icon(a['confidence'])
            lines.append(f"  {icon} {a['type']:32s}  Confidence: {a['confidence']}")
    else:
        lines.append("  [OK]  No obvious attack patterns detected.")

    if timeline:
        start = timeline[0]['minute']
        end = timeline[-1]['minute']
        peak_qps = max(t['qps'] for t in timeline)
        lines.append(f"")
        lines.append(f"  Attack time window :  {start}  ->  {end}")
        lines.append(f"  Peak QPS           :  {peak_qps:,.2f}")

    if dimensions['top_urls']:
        targets = ', '.join(u['url'] for u in dimensions['top_urls'][:3])
        lines.append(f"  Primary targets    :  {targets}")

    status_200 = dimensions['status_stats'].get(200, 0)
    ratio_200 = status_200 / total * 100 if total else 0
    count_5xx = sum(v for s, v in dimensions['status_stats'].items() if 500 <= s < 600)
    if ratio_200 > 70:
        lines.append(f"  Origin impact      :  High - 200 ratio {ratio_200:.1f}%, attack requests heavily hit business endpoints")
    elif count_5xx > 10:
        lines.append(f"  Origin impact      :  High - {count_5xx:,} 5xx errors, origin is impacted")
    else:
        lines.append(f"  Origin impact      :  Medium - 200 ratio {ratio_200:.1f}%")

    # 2. Core Evidence
    section("2. Core Evidence")
    if timeline:
        peak = max(timeline, key=lambda x: x['qps'])
        lines.append(f"  - Request volume spike, peak QPS {peak['qps']:,.2f}  at  {peak['minute']}")
        lines.append(f"  - {dimensions.get('total_unique_ips', len(dimensions['top_ips'])):,} unique client_ip")
    if dimensions['top_urls']:
        top = dimensions['top_urls'][0]
        lines.append(f"  - Top URL  {top['url']}  accounts for {top['request_count']:,}/{total:,} ({top['request_count']/total*100:.1f}%)")
        lines.append(f"  - Avg requests per IP: {top['avg_req_per_ip']:.1f}")
    lines.append(f"  - Empty Referer ratio {dimensions['empty_referer_ratio']:.1f}%")
    if dimensions['ua_analysis']:
        ua = dimensions['ua_analysis'][0]
        lines.append(f"  - Same UA ({ua['ua']}) used by {ua['ip_count']} IPs")
    lines.append(f"  - Status 200 ratio {ratio_200:.1f}%")
    if timeline and any(t.get('p95_request_time') for t in timeline):
        p95s = [t['p95_request_time'] for t in timeline if t.get('p95_request_time')]
        lines.append(f"  - request_time P95 range  {min(p95s):.3f}s ~ {max(p95s):.3f}s")

    bw_attack = next((a for a in attacks if a['type'] == 'Bandwidth surge'), None)
    if bw_attack:
        lines.append(f"  - {bw_attack['evidence']}")
    status_attack = next((a for a in attacks if a['type'] == 'Status code surge'), None)
    if status_attack:
        lines.append(f"  - {status_attack['evidence']}")

    # 3. Top client_ip
    section("3. Top client_ip")
    display_ips = dimensions['top_ips'][:top_n]
    max_ip_len = max(len(ip['client_ip']) for ip in display_ips) if display_ips else 9
    ip_col_width = max(max_ip_len, 9)
    hdr = f"  {'client_ip':<{ip_col_width}} {'requests':>10} {'ratio%':>7} {'peakQPS':>10} {'URLs':>8} {'UAs':>6} {'traffic':>14} {'risk':>8}"
    lines.append(hdr)
    sep('-', 74 + ip_col_width)
    for ip in display_ips:
        lines.append(f"  {ip['client_ip']:<{ip_col_width}} {ip['request_count']:>10,} {ip['ratio']:>7.2f} {ip['peak_qps']:>10,} {ip['url_count']:>8} {ip['ua_count']:>6} {human_readable_size(ip['bytes']):>14} {ip['risk']:>8}")

    # 3.5 CIDR Aggregation for attacker IPs
    non_single_cidrs = [(c, ips) for c, ips in cidr_groups if not c.endswith('/32')]
    if non_single_cidrs:
        lines.append("")
        lines.append("  [Attacker IP subnet aggregation]")
        for cidr_str, ip_list in non_single_cidrs:
            lines.append(f"    -{cidr_str:<20} contains {len(ip_list)} attack IPs: {', '.join(ip_list)}")

    # 4. Top URL
    section("4. Top URL")
    display_urls = dimensions['top_urls'][:top_n]
    hdr = f"  {'URL':<35} {'requests':>10} {'uniqIPs':>8} {'avg/IP':>10} {'P95time':>10} {'emptyRef%':>9} {'risk':>8}"
    lines.append(hdr)
    sep('-', 100)
    for u in display_urls:
        p95 = u.get('p95_request_time') or u.get('p95_upstream_time') or 0
        url_disp = u['url'][:34] if len(u['url']) <= 35 else u['url'][:32] + '..'
        lines.append(f"  {url_disp:<35} {u['request_count']:>10,} {u['unique_ip']:>8} {u['avg_req_per_ip']:>10.1f} {p95:>9.3f}s {u['empty_referer_ratio']:>8.1f}% {u['risk']:>8}")

    # 5. IP x URL Cross Analysis
    has_cross = any([
        cross['single_ip_cc'], cross['scan_ips'], cross['crawler_ips'], cross['proxy_pool_targets']
    ])
    if has_cross:
        section("5. IP x URL Cross Analysis")
        if cross['single_ip_cc']:
            lines.append("  [Single-IP high-frequency CC] same IP high-frequency requests to a single URL:")
            for item in cross['single_ip_cc'][:5]:
                lines.append(f"    -{item['client_ip']:<{ip_col_width}} ->  {item['url']:<40} : {item['count']:,} requests")
        if cross['scan_ips']:
            lines.append("  [Scanning/probing] single IP visiting many distinct paths (>50):")
            for item in cross['scan_ips'][:5]:
                lines.append(f"    -{item['client_ip']:<{ip_col_width}}   URLs: {item['unique_urls']:,}   total requests: {item['total']:,}")
        if cross['crawler_ips']:
            lines.append("  [Abnormal crawler] single IP visiting many detail pages:")
            for item in cross['crawler_ips'][:5]:
                lines.append(f"    -{item['client_ip']:<{ip_col_width}}   URLs: {item['unique_urls']:,}   total requests: {item['total']:,}")
        if cross['proxy_pool_targets']:
            url, ip_count = cross['proxy_pool_targets'][0]
            total_hits = sum(1 for r in records if r.get('path') == url)
            avg = round(total_hits / ip_count, 1) if ip_count else 0
            lines.append(f"  [Proxy-pool pattern] {url} visited by {ip_count} IPs, {total_hits:,} requests in total, avg {avg}/IP")

    # 6. UA Analysis
    section("6. UA Analysis")
    ua_list = dimensions['ua_analysis'][:8]
    max_ua_len = max(len(ua['ua']) for ua in ua_list) if ua_list else 35
    ua_col_width = max(max_ua_len, 2)
    lines.append(f"  {'UA':<{ua_col_width}} {'requests':>10} {'IPs':>8} {'URLs':>8} {'risk':>8}")
    sep('-', max(ua_col_width + 40, 70))
    for ua in ua_list:
        lines.append(f"  {ua['ua']:<{ua_col_width}} {ua['count']:>10,} {ua['ip_count']:>8} {ua['url_count']:>8} {ua['risk']:>8}")

    # 7. Referer Analysis
    section("7. Referer Analysis")
    lines.append(f"  Empty Referer ratio: {dimensions['empty_referer_ratio']:.1f}%")
    if dimensions['referer_analysis']:
        lines.append(f"  {'Referer':<45} {'requests':>10} {'IPs':>8} {'risk':>8}")
        sep('-', 80)
        for ref in dimensions['referer_analysis'][:5]:
            ref_disp_raw = '-' if ref['referer'] == '(empty)' else ref['referer']
            ref_disp = ref_disp_raw[:44] if len(ref_disp_raw) <= 45 else ref_disp_raw[:43] + '..'
            lines.append(f"  {ref_disp:<45} {ref['count']:>10,} {ref['ip_count']:>8} {ref['risk']:>8}")

    # 8. Status Code Analysis
    section("8. Status Code Analysis")
    lines.append(f"  {'status':>6} {'count':>10} {'ratio':>8}   note")
    sep('-', 60)
    for code, cnt in sorted(dimensions['status_stats'].items()):
        ratio = cnt / total * 100 if total else 0
        desc = {
            200: 'Success (business hit)',
            301: 'Redirect',
            302: 'Login redirect',
            401: 'Auth failed (suspected brute force)',
            403: 'Blocked',
            404: 'Scan probe',
            408: 'Client timeout',
            499: 'Client closed',
            500: 'Origin error',
            502: 'Origin error',
            503: 'Origin overloaded',
            504: 'Origin timeout',
        }.get(code, '')
        bar = '#' * int(ratio / 2)
        lines.append(f"  {code:>6} {cnt:>10,} {ratio:>7.1f}%  {bar:<20} {desc}")

    # 9. Traffic Analysis
    section("9. Traffic Analysis")
    lines.append(f"  Avg response size : {human_readable_size(dimensions['avg_response_size'])}")
    if dimensions['top_traffic_ips']:
        ip, b = dimensions['top_traffic_ips'][0]
        lines.append(f"  Top traffic IP    : {ip:<20} {human_readable_size(b):>15}")
    if dimensions['top_traffic_urls']:
        url, b = dimensions['top_traffic_urls'][0]
        lines.append(f"  Top traffic URL   : {url:<40} {human_readable_size(b):>15}")

    # 10. Latency Analysis
    lat = dimensions.get('latency_summary', {})
    if lat.get('avg_request_time'):
        section("10. Request Latency Analysis")
        lines.append(f"  Avg request_time    : {lat['avg_request_time']}s")
        lines.append(f"  P95 request_time    : {lat['p95_request_time']}s")
        lines.append(f"  P99 request_time    : {lat['p99_request_time']}s")
        lines.append(f"  Slow requests (>3s) : {lat['slow_request_count']:,}")
        if lat.get('slow_top_urls'):
            lines.append(f"  Slow request Top URL : {lat['slow_top_urls'][0][0]} ({lat['slow_top_urls'][0][1]} requests)")
        if lat.get('slow_top_ips'):
            lines.append(f"  Slow request Top IP  : {lat['slow_top_ips'][0][0]} ({lat['slow_top_ips'][0][1]} requests)")

    # 11. Mitigation Recommendations
    section("11. Mitigation Recommendations")
    if block_cidrs:
        cidr_display = ', '.join(block_cidrs)
        lines.append(f"  1. Set subnet/IP blacklist; temporarily deny attacker subnets: {cidr_display}")
    else:
        lines.append("  1. Set subnet/IP blacklist; temporarily deny the top high-risk IPs")
    lines.append("  2. Enable WAF bot/human verification (paid edition) for suspicious IPs (e.g. JS challenge, slider) to separate real users from automated scripts")
    lines.append("  3. Set WAF custom rate-limit rules (paid edition) on critical endpoints (e.g. login, payment) (e.g. 10s window, threshold 5, block 1800s) to prevent endpoint exhaustion")
    lines.append("  4. Put CDN/DCDN in front to cache static content and reduce origin bandwidth pressure")

    # Missing fields
    missing = missing_field_notes(records)
    if missing:
        section("Note - missing fields reduce analysis accuracy")
        for m in missing:
            lines.append(f"  [!] {m}")

    # 12. Structured Findings (machine-readable input for the next agent stage)
    findings = build_structured_findings(records, timeline, dimensions, attacks)
    section("12. Structured Findings (machine-readable)")
    lines.append("  JSON block for downstream agents/tools:")
    lines.append("")
    for jl in json.dumps(findings, indent=2).splitlines():
        lines.append(f"  {jl}" if jl else "")

    lines.append("")
    sep('=', 70)
    lines.append("                          END OF REPORT")
    sep('=', 70)

    report_text = '\n'.join(lines)
    if output_path:
        Path(output_path).write_text(report_text, encoding='utf-8')
    return report_text


# ---------------------------------------------------------------------------
# generate_report_markdown
# ---------------------------------------------------------------------------

def generate_report_markdown(records, timeline, dimensions, cross, attacks, output_path=None, top_n=20,
                             analyzed_file=None):
    """Generate Markdown-formatted report suitable for documentation tools."""
    lines = []
    total = dimensions['total_requests']

    high_risk_ips, cidr_groups, block_cidrs = compute_block_targets(dimensions, attacks, top_n)

    def conf_badge(c):
        return {'High': 'HIGH', 'Medium': 'MED', 'Low': 'LOW'}.get(c, '?')

    # -- Title --
    lines.append("# Origin Web Access Log Security Analysis Report")
    lines.append("")
    lines.append(f"- **Analysis sample**: {total:,} records")
    if records:
        src = records[0].get('source_type', 'unknown')
        lines.append(f"- **Log format**: {src.upper()}")
    if analyzed_file:
        lines.append(f"- **Analyzed file**: {analyzed_file}")
    if timeline:
        lines.append(f"- **Time range**: {timeline[0]['minute']} -> {timeline[-1]['minute']}")
    lines.append("")

    # 0. Executive Summary (non-technical audience)
    summary = build_executive_summary(records, timeline, dimensions, attacks, block_cidrs)
    lines.append("## 0. Executive Summary")
    lines.append("")
    lines.append(f"**Conclusion**: {summary['conclusion']}")
    lines.append("")
    lines.append("**Plain language explanation**:")
    lines.append("")
    for sent in summary['explanation']:
        lines.append(f"- {sent}")
    lines.append("")
    lines.append("**What you should do**:")
    lines.append("")
    for i, act in enumerate(summary['actions'], 1):
        lines.append(f"{i}. {act}")
    lines.append("")

    # 1. Attack Conclusion
    lines.append("## 1. Attack Conclusion")
    lines.append("")
    if attacks:
        lines.append("| Level | Attack Type | Confidence |")
        lines.append("| --- | --- | --- |")
        for a in attacks:
            lines.append(f"| {conf_badge(a['confidence'])} | {a['type']} | {a['confidence']} |")
    else:
        lines.append("> No obvious attack patterns detected.")
    lines.append("")

    if timeline:
        peak_qps = max(t['qps'] for t in timeline)
        lines.append(f"- **Attack time window**: {timeline[0]['minute']} -> {timeline[-1]['minute']}")
        lines.append(f"- **Peak QPS**: {peak_qps:,.2f}")

    if dimensions['top_urls']:
        targets = ', '.join(f"`{u['url']}`" for u in dimensions['top_urls'][:3])
        lines.append(f"- **Primary targets**: {targets}")

    status_200 = dimensions['status_stats'].get(200, 0)
    ratio_200 = status_200 / total * 100 if total else 0
    count_5xx = sum(v for s, v in dimensions['status_stats'].items() if 500 <= s < 600)
    if ratio_200 > 70:
        lines.append(f"- **Origin impact**: High - 200 ratio {ratio_200:.1f}%, attack requests heavily hit business endpoints")
    elif count_5xx > 10:
        lines.append(f"- **Origin impact**: High - {count_5xx:,} 5xx errors, origin is impacted")
    else:
        lines.append(f"- **Origin impact**: Medium - 200 ratio {ratio_200:.1f}%")
    lines.append("")

    # 2. Core Evidence
    lines.append("## 2. Core Evidence")
    lines.append("")
    if timeline:
        peak = max(timeline, key=lambda x: x['qps'])
        lines.append(f"- Request volume spike, peak QPS **{peak['qps']:,.2f}** at {peak['minute']}")
        lines.append(f"- **{dimensions.get('total_unique_ips', len(dimensions['top_ips'])):,}** unique client_ip")
    if dimensions['top_urls']:
        top = dimensions['top_urls'][0]
        lines.append(f"- Top URL `{top['url']}` accounts for {top['request_count']:,}/{total:,} ({top['request_count']/total*100:.1f}%)")
        lines.append(f"- Avg requests per IP: {top['avg_req_per_ip']:.1f}")
    lines.append(f"- Empty Referer ratio {dimensions['empty_referer_ratio']:.1f}%")
    if dimensions['ua_analysis']:
        ua = dimensions['ua_analysis'][0]
        lines.append(f"- Same UA (`{ua['ua']}`) used by **{ua['ip_count']}** IPs")
    lines.append(f"- Status 200 ratio {ratio_200:.1f}%")
    if timeline and any(t.get('p95_request_time') for t in timeline):
        p95s = [t['p95_request_time'] for t in timeline if t.get('p95_request_time')]
        lines.append(f"- request_time P95 range {min(p95s):.3f}s ~ {max(p95s):.3f}s")

    bw_attack = next((a for a in attacks if a['type'] == 'Bandwidth surge'), None)
    if bw_attack:
        lines.append(f"- {bw_attack['evidence']}")
    status_attack = next((a for a in attacks if a['type'] == 'Status code surge'), None)
    if status_attack:
        lines.append(f"- {status_attack['evidence']}")
    lines.append("")

    # 3. Top client_ip
    lines.append("## 3. Top client_ip")
    lines.append("")
    display_ips = dimensions['top_ips'][:top_n]
    lines.append("| client_ip | Requests | Ratio% | Peak QPS | URLs | UAs | Traffic | Risk |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for ip in display_ips:
        lines.append(f"| {ip['client_ip']} | {ip['request_count']:,} | {ip['ratio']:.2f} | {ip['peak_qps']:,} | {ip['url_count']} | {ip['ua_count']} | {human_readable_size(ip['bytes'])} | {ip['risk']} |")

    non_single_cidrs = [(c, ips) for c, ips in cidr_groups if not c.endswith('/32')]
    if non_single_cidrs:
        lines.append("")
        lines.append("**Attacker IP subnet aggregation**:")
        lines.append("")
        lines.append("| Subnet | IP Count | Attack IPs Contained |")
        lines.append("| --- | ---: | --- |")
        for cidr_str, ip_list in non_single_cidrs:
            ips_display = ', '.join(f'`{ip}`' for ip in ip_list)
            lines.append(f"| `{cidr_str}` | {len(ip_list)} | {ips_display} |")
    lines.append("")

    # 4. Top URL
    lines.append("## 4. Top URL")
    lines.append("")
    display_urls = dimensions['top_urls'][:top_n]
    lines.append("| URL | Requests | Unique IPs | Avg/IP | P95 Time | Empty Ref% | Risk |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for u in display_urls:
        p95 = u.get('p95_request_time') or u.get('p95_upstream_time') or 0
        url_disp = u['url'] if len(u['url']) <= 50 else u['url'][:48] + '..'
        url_disp = url_disp.replace('|', '\\|')
        lines.append(f"| `{url_disp}` | {u['request_count']:,} | {u['unique_ip']} | {u['avg_req_per_ip']:.1f} | {p95:.3f}s | {u['empty_referer_ratio']:.1f}% | {u['risk']} |")
    lines.append("")

    # 5. IP x URL Cross Analysis
    has_cross = any([
        cross['single_ip_cc'], cross['scan_ips'], cross['crawler_ips'], cross['proxy_pool_targets']
    ])
    if has_cross:
        lines.append("## 5. IP x URL Cross Analysis")
        lines.append("")
        if cross['single_ip_cc']:
            lines.append("### Single-IP High-Frequency CC")
            lines.append("")
            lines.append("| IP | Target URL | Request Count |")
            lines.append("| --- | --- | ---: |")
            for item in cross['single_ip_cc'][:5]:
                url_disp = item['url'].replace('|', '\\|')
                lines.append(f"| {item['client_ip']} | `{url_disp}` | {item['count']:,} |")
            lines.append("")
        if cross['scan_ips']:
            lines.append("### Scanning/Probing")
            lines.append("")
            lines.append("Single IP visiting many distinct paths:")
            lines.append("")
            lines.append("| IP | URLs | Total Requests |")
            lines.append("| --- | ---: | ---: |")
            for item in cross['scan_ips'][:5]:
                lines.append(f"| {item['client_ip']} | {item['unique_urls']:,} | {item['total']:,} |")
            lines.append("")
        if cross['crawler_ips']:
            lines.append("### Abnormal Crawler")
            lines.append("")
            lines.append("| IP | URLs | Total Requests |")
            lines.append("| --- | ---: | ---: |")
            for item in cross['crawler_ips'][:5]:
                lines.append(f"| {item['client_ip']} | {item['unique_urls']:,} | {item['total']:,} |")
            lines.append("")
        if cross['proxy_pool_targets']:
            url, ip_count = cross['proxy_pool_targets'][0]
            total_hits = sum(1 for r in records if r.get('path') == url)
            avg = round(total_hits / ip_count, 1) if ip_count else 0
            lines.append(f"> **Proxy-pool pattern**: `{url}` visited by {ip_count} IPs, {total_hits:,} requests in total, avg {avg}/IP")
            lines.append("")

    # 6. UA Analysis
    lines.append("## 6. UA Analysis")
    lines.append("")
    ua_list = dimensions['ua_analysis'][:8]
    lines.append("| UA | Requests | IPs | URLs | Risk |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for ua in ua_list:
        ua_disp = ua['ua'].replace('|', '\\|')
        lines.append(f"| {ua_disp} | {ua['count']:,} | {ua['ip_count']} | {ua['url_count']} | {ua['risk']} |")
    lines.append("")

    # 7. Referer Analysis
    lines.append("## 7. Referer Analysis")
    lines.append("")
    lines.append(f"**Empty Referer ratio**: {dimensions['empty_referer_ratio']:.1f}%")
    lines.append("")
    if dimensions['referer_analysis']:
        lines.append("| Referer | Requests | IPs | Risk |")
        lines.append("| --- | ---: | ---: | --- |")
        for ref in dimensions['referer_analysis'][:5]:
            ref_disp = '-' if ref['referer'] == '(empty)' else ref['referer']
            ref_disp = ref_disp.replace('|', '\\|')
            lines.append(f"| {ref_disp} | {ref['count']:,} | {ref['ip_count']} | {ref['risk']} |")
    lines.append("")

    # 8. Status Code Analysis
    lines.append("## 8. Status Code Analysis")
    lines.append("")
    lines.append("| Status | Count | Ratio | Note |")
    lines.append("| ---: | ---: | ---: | --- |")
    status_desc_map = {
        200: 'Success (business hit)', 206: 'Partial content',
        301: 'Redirect', 302: 'Login redirect', 304: 'Cache hit',
        401: 'Auth failed (suspected brute force)', 403: 'Blocked', 404: 'Scan probe',
        408: 'Client timeout', 499: 'Client closed',
        500: 'Origin error', 502: 'Origin error', 503: 'Origin overloaded', 504: 'Origin timeout',
    }
    for code, cnt in sorted(dimensions['status_stats'].items()):
        ratio = cnt / total * 100 if total else 0
        desc = status_desc_map.get(code, '')
        bar = '#' * int(ratio / 2)
        lines.append(f"| {code} | {cnt:,} | {ratio:.1f}% | {bar} {desc} |")
    lines.append("")

    # 9. Traffic Analysis
    lines.append("## 9. Traffic Analysis")
    lines.append("")
    lines.append(f"- **Avg response size**: {human_readable_size(dimensions['avg_response_size'])}")
    if dimensions['top_traffic_ips']:
        ip, b = dimensions['top_traffic_ips'][0]
        lines.append(f"- **Top traffic IP**: `{ip}` - {human_readable_size(b)}")
    if dimensions['top_traffic_urls']:
        url, b = dimensions['top_traffic_urls'][0]
        lines.append(f"- **Top traffic URL**: `{url}` - {human_readable_size(b)}")
    lines.append("")

    # 10. Latency Analysis
    lat = dimensions.get('latency_summary', {})
    if lat.get('avg_request_time'):
        lines.append("## 10. Request Latency Analysis")
        lines.append("")
        lines.append(f"- **Avg request_time**: {lat['avg_request_time']}s")
        lines.append(f"- **P95 request_time**: {lat['p95_request_time']}s")
        lines.append(f"- **P99 request_time**: {lat['p99_request_time']}s")
        lines.append(f"- **Slow requests (>3s)**: {lat['slow_request_count']:,}")
        if lat.get('slow_top_urls'):
            lines.append(f"- **Slow request Top URL**: `{lat['slow_top_urls'][0][0]}` ({lat['slow_top_urls'][0][1]} requests)")
        if lat.get('slow_top_ips'):
            lines.append(f"- **Slow request Top IP**: `{lat['slow_top_ips'][0][0]}` ({lat['slow_top_ips'][0][1]} requests)")
        lines.append("")

    # 11. Mitigation Recommendations
    lines.append("## 11. Mitigation Recommendations")
    lines.append("")
    if block_cidrs:
        cidr_display = ', '.join(f'`{c}`' for c in block_cidrs)
        lines.append(f"1. **IP/subnet blacklist** - temporarily deny attacker subnets: {cidr_display}")
    else:
        lines.append("1. **IP/subnet blacklist** - temporarily deny the top high-risk IPs")
    lines.append("2. **WAF bot/human verification** - trigger JS challenge/slider for suspicious IPs to separate real users from automated scripts")
    lines.append("3. **WAF custom rate limiting** - set access rate limits on critical endpoints (e.g. 10s window, threshold 5, block 1800s)")
    lines.append("4. **CDN/DCDN in front** - cache static content to reduce origin bandwidth pressure")
    lines.append("")

    # Missing fields
    missing = missing_field_notes(records)
    if missing:
        lines.append("## Missing Fields")
        lines.append("")
        lines.append("> The following missing fields may reduce analysis accuracy:")
        lines.append(">")
        for m in missing:
            lines.append(f"> - `{m}`")
        lines.append("")

    # 12. Structured Findings (machine-readable input for the next agent stage)
    findings = build_structured_findings(records, timeline, dimensions, attacks)
    lines.append("## 12. Structured Findings (machine-readable)")
    lines.append("")
    lines.append("JSON block for downstream agents/tools:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(findings, indent=2))
    lines.append("```")
    lines.append("")

    lines.append("---")
    lines.append("*End of report*")

    report_text = '\n'.join(lines)
    if output_path:
        Path(output_path).write_text(report_text, encoding='utf-8')
    return report_text


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Web Log Security Analyzer')
    parser.add_argument('log_file', help='Path to access log file')
    parser.add_argument('--format', choices=['nginx', 'apache', 'iis'], help='Force log format')
    parser.add_argument('--top-n', type=int, default=20, help='Top N entries to display in report tables')
    parser.add_argument('--time-window', type=int, default=None,
                        help='Only analyze the last N minutes of log data (default: full range)')
    parser.add_argument('--output', help='Output report file path (default: <skill>/output/<logname>_report.<ext>)')
    parser.add_argument('--output-format', choices=['text', 'markdown'], default='text',
                        help='Report output format: text (default) or markdown (for documentation tools)')
    args = parser.parse_args()

    log_path = Path(args.log_file)
    if not log_path.exists():
        print(f"Error: file not found: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    # Auto-generate output path under <skill>/output/ when --output is not specified.
    # Fall back to the current working directory when the skill directory is
    # read-only (common in customer environments).
    if not args.output:
        script_dir = Path(__file__).resolve().parent
        skill_dir = script_dir.parent
        output_dir = skill_dir / 'output'
        log_stem = log_path.stem
        if log_stem.endswith('.log'):
            log_stem = log_stem[:-4]
        ext = '.md' if args.output_format == 'markdown' else '.txt'
        report_name = f"{log_stem}_report{ext}"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            probe = output_dir / '.write_probe'
            probe.touch()
            probe.unlink()
            args.output = str(output_dir / report_name)
        except OSError as e:
            args.output = str(Path.cwd() / report_name)
            print(f"Warning: skill output directory not writable ({e}); "
                  f"falling back to current working directory", file=sys.stderr)

    try:
        if str(log_path).endswith('.gz'):
            with gzip.open(log_path, 'rt', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        else:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
    except (OSError, EOFError, zlib.error, gzip.BadGzipFile) as e:
        # Covers: unreadable file, directory passed as input, corrupt or
        # truncated .gz, etc. (EOFError/zlib.error carry no strerror attr,
        # hence the getattr fallback.)
        print(f"Error: cannot read log file '{args.log_file}': {getattr(e, 'strerror', None) or e}", file=sys.stderr)
        sys.exit(1)

    source_type = args.format
    if not source_type:
        try:
            source_type = detect_log_type(lines)
            print(f"Detected log format: {source_type}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Using forced format: {source_type}")

    raw_records = []
    skipped_lines = 0
    alt_schema_rows = 0
    total_lines = len([ln for ln in lines if ln.strip() and not ln.startswith('#')])
    if source_type == 'iis':
        raw_records, alt_schema_rows = parse_iis_log(lines)
        skipped_lines = total_lines - len(raw_records)
    else:
        for line in lines:
            if not line.strip():
                continue
            rec = parse_log_line(line, source_type)
            if rec:
                raw_records.append(rec)
            else:
                skipped_lines += 1

    if not raw_records:
        print("Error: no valid log records parsed", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(raw_records)} records")
    if skipped_lines > 0:
        print(f"Skipped {skipped_lines} unparseable lines ({skipped_lines/max(total_lines,1)*100:.1f}%)")
    if alt_schema_rows > 0:
        print(f"Warning: {alt_schema_rows} rows parsed with alternate schema", file=sys.stderr)

    records = [normalize_record(r) for r in raw_records]
    parsed_count = len(records)
    records = [r for r in records if r['timestamp']]
    dropped_ts = parsed_count - len(records)
    if dropped_ts > 0:
        print(f"Dropped {dropped_ts} records with unparseable timestamps", file=sys.stderr)
    if not records:
        print("Error: no valid log records with parseable timestamps", file=sys.stderr)
        sys.exit(1)

    # Apply --time-window filter: keep only last N minutes
    if args.time_window and records:
        try:
            max_ts = max(r['timestamp'] for r in records)
            cutoff = max_ts - timedelta(minutes=args.time_window)
            before_count = len(records)
            records = [r for r in records if r['timestamp'] >= cutoff]
            print(f"Time window filter: last {args.time_window} min, {before_count} -> {len(records)} records")
            if not records:
                print("Error: no valid log records with parseable timestamps "
                      f"remain inside the last {args.time_window} minutes", file=sys.stderr)
                sys.exit(1)
        except TypeError as e:
            # Mixed timezone-aware/naive timestamps: proceed with full range
            print(f"Warning: --time-window skipped due to mixed timestamp types ({e})",
                  file=sys.stderr)

    try:
        timeline = aggregate_timeline(records)
        dimensions = aggregate_dimensions(records, top_n=args.top_n)
        cross = ip_url_cross_analysis(records, total_requests=len(records), total_unique_ips=dimensions.get('total_unique_ips', 0))
        attacks = detect_attack_type(records, timeline, dimensions, cross)

        if args.output_format == 'markdown':
            report = generate_report_markdown(records, timeline, dimensions, cross, attacks, None,
                                              top_n=args.top_n, analyzed_file=args.log_file)
        else:
            report = generate_report(records, timeline, dimensions, cross, attacks, None,
                                     top_n=args.top_n, analyzed_file=args.log_file)
    except Exception as e:
        # Never leak a raw traceback for unexpected data shapes; emit a
        # clean error and exit with the standard failure code.
        print(f"Error: analysis failed for '{args.log_file}': {e}", file=sys.stderr)
        sys.exit(1)

    # Report writing is handled separately so a write failure is never
    # misreported as an analysis failure.
    if args.output:
        try:
            Path(args.output).write_text(report, encoding='utf-8')
        except OSError as e:
            print(f"Error: cannot write report to '{args.output}': {getattr(e, 'strerror', None) or e}",
                  file=sys.stderr)
            sys.exit(1)
    print(report)
    if args.output:
        print(f"\nReport saved to: {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
