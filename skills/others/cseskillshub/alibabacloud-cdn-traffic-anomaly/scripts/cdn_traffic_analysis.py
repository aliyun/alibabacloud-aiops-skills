#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDN Offline-Log Traffic Forensics Tool (read-only)

API used (only one cloud API):
    DescribeCdnDomainLogs (invoked via aliyun CLI plugin mode)

Workflow:
    1. Call DescribeCdnDomainLogs to list offline access-log download URLs
    2. Download the gzip log files locally
    3. Parse logs and build dual-metric Top-N statistics over four
       dimensions (URL / IP+subnet / Referer / UserAgent x requests/traffic)
    4. Commonality analysis (status codes, cache hit ratio, methods, hourly
       distribution, response-size buckets, IP request-frequency buckets)
    5. Traffic-theft (abuse) determination via 13 built-in rules
    6. Scenario classification T1~T6 and evidence-based recommendations

Auth: relies entirely on the aliyun CLI default credential chain (CLI config
or platform-injected environment); this script performs no explicit auth
handling and never reads, prints, or passes AK/SK/STS tokens.

Usage:
    python3 cdn_traffic_analysis.py --domain example.com
    python3 cdn_traffic_analysis.py --domain example.com \\
        --start-time "2026-08-20 10:00:00" --end-time "2026-08-20 12:00:00"
    python3 cdn_traffic_analysis.py --domain example.com --json
    python3 cdn_traffic_analysis.py --domain example.com --keep-logs

Notes:
    - CDN offline logs are typically downloadable 3~4 hours after the fact;
      a too-recent window may return no logs.
    - Logs are split per hour; align the window to whole hours when possible.
"""

import argparse
import gzip
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Per-run session id for platform-level tracing (Observability)
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-cdn-traffic-anomaly/{_SESSION_ID}"

# ==================== Embedded constants ====================
DEFAULT_TOP_N = 5
DEFAULT_LOG_DIR = Path(__file__).parent / ".cdn_logs"
HTTP_TIMEOUT = 60
MAX_LOG_FILES = 24          # max log files per run (guards oversized windows)
MAX_LOG_BYTES = 2 * 1024 * 1024 * 1024  # per-file download cap (2 GB)
CLI_TIMEOUT_SECONDS = 30

# --- Abuse thresholds: ratio-based ---
IP_HIGH_THRESHOLD = 0.30
IP_MED_THRESHOLD = 0.10
IP_TOP5_THRESHOLD = 0.60
REFER_EMPTY_HIGH = 0.50
REFER_EMPTY_MED = 0.30
URL_HIGH_THRESHOLD = 0.40
URL_MED_THRESHOLD = 0.20
UA_HIGH_THRESHOLD = 0.30
UA_MED_THRESHOLD = 0.15
UA_SUSPICIOUS_KEYWORDS = (
    "bot", "spider", "crawler", "scraper", "curl", "wget", "python-requests",
    "java/", "go-http-client", "okhttp", "scrapy", "headless",
)

# --- Abuse thresholds: absolute-volume gates ---
# A ratio signal only counts toward the risk score when the absolute request
# volume gate is also met (prevents false positives on tiny samples).
MIN_SAMPLE_REQUESTS = 100           # below this the verdict is forced low
ABS_TOP1_IP_REQUESTS = 500          # top-1 IP requests (high risk)
ABS_TOP1_IP_REQUESTS_MED = 200      # top-1 IP requests (medium)
ABS_TOP5_IP_REQUESTS = 1000         # top-5 IP cumulative requests
ABS_EMPTY_REFER_REQUESTS = 500      # empty Referer requests (high)
ABS_EMPTY_REFER_REQUESTS_MED = 200  # empty Referer requests (medium)
ABS_HOT_URL_REQUESTS = 500          # hot URL requests (high)
ABS_HOT_URL_REQUESTS_MED = 200      # hot URL requests (medium)
ABS_SUSPICIOUS_UA_REQUESTS = 500    # suspicious UA requests (high)
ABS_SUSPICIOUS_UA_REQUESTS_MED = 200
ABS_BIG_FILE_TRAFFIC_BYTES = 100 * 1024 * 1024  # large-file traffic gate

# --- Abuse thresholds: 13-rule engine ---
ABUSE_IP_HIGH_FREQ = 500            # abnormally high per-IP request count
ABUSE_SINGLE_REFER_HIGH = 0.40      # single Referer concentration
ABUSE_BIG_FILE_RATIO = 0.50         # large-file traffic share
ABUSE_CONCURRENT_THRESHOLD = 20     # same-second concurrent requests
ABUSE_UA_CONSISTENCY_HIGH = 0.50    # identical-UA share
ABUSE_EMPTY_UA_RATIO = 0.30         # empty-UA share
ABUSE_INTERVAL_CV_THRESHOLD = 0.3   # request-interval CV (lower = uniform)
ABUSE_IP_DISPERSAL_HIGH = 100       # unique-IP dispersal count
ABUSE_IP_CONSISTENCY_CV = 0.5       # per-IP volume consistency CV
# R01 dual absolute-volume gates (E2E fix): on tiny samples the per-IP
# consistency CV is ~0 by construction (e.g. 300 requests spread over 250
# IPs at 1-2 req/IP), which used to false-positive. A real botnet replays
# objects many times, so R01 now requires BOTH a sizable total volume and
# repeated hits per IP before the CV signal is trusted.
ABS_R01_MIN_TOTAL_REQUESTS = 1000   # min total requests before R01 may fire
ABS_R01_MIN_MEAN_REQ_PER_IP = 3.0   # min average requests per IP for R01

# Critical API error codes that must surface as hard failures (exit 1)
# rather than benign no-data (exit 2).
CRITICAL_API_ERROR_CODES = ('InvalidDomain.NotFound',
                            'InvalidAccessKeyId.NotFound')

# Plain-language explanations for non-technical readers (text report only;
# JSON keeps the raw enums).
ABUSE_VERDICT_EXPLAIN = {
    True: 'the traffic pattern matches known theft/attack signatures; '
          'act on the recommendations below.',
    False: 'no theft/attack pattern matched; the traffic looks organic, or '
           'the sample is too small to judge.',
}
SCENARIO_EXPLAIN = {
    'T1': 'a few hot objects absorb most traffic - typically targeted '
          'scraping or hotlinked files.',
    'T2': 'a few IP addresses dominate the traffic - typically attack '
          'sources or a botnet.',
    'T3': 'traffic arrives with abnormal Referers - typically off-site '
          'hotlinking or direct tool access.',
    'T4': 'traffic comes from scripts/tools rather than real browsers.',
    'T5': 'traffic is broadly dispersed; usually a legitimate surge, but '
          'confirm with the business owner.',
    'T6': 'cache misses force requests back to the origin, amplifying '
          'origin load and egress.',
}

# Error-code -> actionable guidance (shown in the text report so non-technical
# users get a next step instead of a raw CLI error).
ERROR_GUIDANCE = {
    'InvalidDomain.NotFound':
        'The domain does not exist or does not belong to the current '
        'account; check the domain spelling and which account owns it.',
    'InvalidAccessKeyId.NotFound':
        'The credential was not recognized; fix the CLI default credential '
        'chain with `aliyun configure` (never paste AK/SK).',
    'Forbidden':
        'Permission denied; the caller lacks cdn:DescribeCdnDomainLogs - '
        'see references/ram-policies.md.',
    'Forbidden.RAM':
        'Permission denied by RAM; the caller lacks '
        'cdn:DescribeCdnDomainLogs - see references/ram-policies.md.',
    'NoPermission':
        'Permission denied; the caller lacks cdn:DescribeCdnDomainLogs - '
        'see references/ram-policies.md.',
    'Throttling.User':
        'API requests were rate limited; wait a moment and retry.',
    'NoLogsInWindow':
        'No offline logs exist for this window yet. Offline logs lag 3-4 '
        'hours behind real time; retry later, widen the window, or verify '
        'the domain actually had traffic.',
    'AllDownloadsFailed':
        'Every log download failed; check outbound network access to the '
        'log storage endpoint and retry later.',
    'CliError':
        'The aliyun CLI itself failed; verify it is installed and '
        'configured (`aliyun configure`).',
}

EMPTY_VALUES = {"", "-", "none", "null", "direct", "unknown", "/", "(direct)"}

MACHINE_FREQ_THRESHOLD = 1000       # per-IP requests above this = machine-like

_IP_FREQ_BUCKETS_ORDER = [
    "1-10", "11-100", "101-500", "501-1000", "1001-3000", "3001-5000", ">5000",
]

_RESP_SIZE_BUCKETS_ORDER = [
    "empty/304", "<1KB", "1KB-10KB", "10KB-100KB", "100KB-1MB", "1MB-10MB", ">10MB",
]

# Scenario concentration threshold used by T1~T4 classification
SCENARIO_CONCENTRATION = 0.30

# Alibaba Cloud CDN offline log line format:
# [14/Jun/2018:14:08:54 +0800] 192.168.0.18 - 8 "-" "GET https://cdn.example.com/path" 200 7541 5972 HIT "Mozilla/5.0..." "image/png"
LOG_PATTERN = re.compile(
    r'\[(?P<time>[^\]]+)\]\s+'
    r'(?P<ip>\S+)\s+'
    r'(?P<proxy>\S+)\s+'
    r'(?P<resp_time>\S+)\s+'
    r'"(?P<refer>[^"]*)"\s+'
    r'"(?P<request>[^"]*)"\s+'
    r'(?P<status>\d+)\s+'
    r'(?P<req_size>\d+)\s+'
    r'(?P<resp_size>\d+)\s+'
    r'(?P<cache>\S+)\s+'
    r'"(?P<ua>[^"]*)"'
    r'(?:\s+"(?P<ctype>[^"]*)")?'
)

_TIME_HOUR_PATTERN = re.compile(r'\d+/\w+/\d+:(\d{2}):\d{2}:\d{2}')
_TIME_TS_PATTERN = re.compile(r'(\d+)/(\w+)/(\d+):(\d{2}):(\d{2}):(\d{2})\s+([+-]\d{4})')
_MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}
# Blank out query-parameter values while keeping path and parameter names:
# '?a=1&b=2' -> '?a=&b=' (URLs without a query string are returned as-is).
_URL_VALUE_RE = re.compile(r'(=)[^&]*')


# ==================== CLI backend ====================
#
# All cloud API access goes through the `aliyun` CLI (subprocess, plugin
# mode, lowercase-hyphenated subcommands) so every call stays on one
# interceptable path. Credentials are resolved by the CLI itself via its
# default chain; this script inherits the current environment untouched and
# passes NO credential parameters.

# Regex fallback for non-JSON CLI errors: the real aliyun CLI often prints
# multi-line SDKError text like "Code: InvalidDomain.NotFound" plus a
# "Message: ..." line rather than a JSON document.
_CLI_ERR_CODE_RE = re.compile(r'Code:\s*(\S+)')
_CLI_ERR_MSG_RE = re.compile(r'Message:\s*(.+)')


def _parse_cli_error(stdout: str, stderr: str) -> Tuple[str, str]:
    """Extract (Code, Message) from aliyun CLI error output.

    Tries JSON first, then regex extraction on SDKError-style plain text,
    and only then falls back to the first 300 chars of the raw output.
    """
    for text in (stdout, stderr):
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict) and data.get('Code'):
            return str(data['Code']), str(data.get('Message', ''))
    for text in (stderr, stdout):
        if not text:
            continue
        # Prefer a non-purely-numeric Code match: SDKError dumps may also
        # carry HTTP status lines (e.g. "StatusCode: 404") whose digits
        # must not shadow the real API error code.
        matches = list(_CLI_ERR_CODE_RE.finditer(text))
        code_m = next((m for m in matches
                       if not m.group(1).isdigit()), None) or (
                           matches[0] if matches else None)
        if code_m:
            mm = _CLI_ERR_MSG_RE.search(text)
            return code_m.group(1), (mm.group(1).strip() if mm else '')
    detail = (stderr or stdout or '').strip()
    return 'CliError', detail[:300]


def _describe_cdn_domain_logs(domain: str, start_iso: str,
                              end_iso: str) -> Dict[str, Any]:
    """Call CDN DescribeCdnDomainLogs via aliyun CLI (plugin mode).

    Raises RuntimeError("<Code>: <Message>") on any CLI/API failure.
    """
    cmd = [
        'aliyun', 'cdn', 'describe-cdn-domain-logs',
        '--domain-name', domain,
        '--start-time', start_iso,
        '--end-time', end_iso,
        '--page-size', '100',
        '--user-agent', _USER_AGENT,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=CLI_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'CliError: aliyun CLI request timed out after '
                           f'{CLI_TIMEOUT_SECONDS}s')
    except FileNotFoundError:
        raise RuntimeError('CliError: aliyun CLI not found on PATH')

    if proc.returncode != 0:
        code, message = _parse_cli_error(proc.stdout, proc.stderr)
        raise RuntimeError(f'{code}: {message}')

    try:
        result = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError('CliError: unparseable response from aliyun CLI')
    if isinstance(result, dict) and result.get('Code'):
        raise RuntimeError(f"{result['Code']}: {result.get('Message', '')}")
    return result if isinstance(result, dict) else {}


def extract_log_entries(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Tolerantly extract log file entries from the API response.

    The response is walked recursively; any dict carrying a log-path-like
    key is treated as one log record. No nesting layout is hardcoded.
    """
    entries: List[Dict[str, Any]] = []

    def walk(node: Any):
        if isinstance(node, dict):
            log_path = node.get('LogPath') or node.get('logPath') or ''
            log_name = node.get('LogName') or node.get('logName') or ''
            if log_path or log_name:
                entries.append({
                    'log_name': str(log_name),
                    'log_path': str(log_path),
                    'log_size': node.get('LogSize') or node.get('logSize') or 0,
                    'start_time': node.get('StartTime') or node.get('startTime') or '',
                    'end_time': node.get('EndTime') or node.get('endTime') or '',
                })
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(response)
    return entries


# ==================== Log parsing & download ====================

def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse one CDN offline access-log line; None when unparseable."""
    line = line.strip()
    if not line:
        return None
    m = LOG_PATTERN.match(line)
    if not m:
        return None

    request = m.group('request')
    method = ''
    url = ''
    parts = request.split(' ', 2)
    if len(parts) >= 2:
        method = parts[0]
        url = parts[1]

    return {
        'time': m.group('time'),
        'ip': m.group('ip'),
        'refer': m.group('refer') or '',
        'method': method,
        'url': url,
        'status': int(m.group('status')) if m.group('status').isdigit() else 0,
        'req_size': int(m.group('req_size')) if m.group('req_size').isdigit() else 0,
        'resp_size': int(m.group('resp_size')) if m.group('resp_size').isdigit() else 0,
        'cache': m.group('cache') or '',
        'ua': m.group('ua') or '',
    }


def _normalize_log_url(log_path: str) -> str:
    """LogPath is usually returned without a scheme; complete it to https."""
    if not log_path:
        return ''
    if log_path.startswith(('http://', 'https://')):
        return log_path
    return 'https://' + log_path.lstrip('/')


def download_log(log_url: str, save_path: Path,
                 timeout: int = HTTP_TIMEOUT,
                 max_bytes: int = MAX_LOG_BYTES) -> bool:
    """Download one gzip log file in chunks, truncated at max_bytes;
    returns success flag."""
    if save_path.exists() and save_path.stat().st_size > 0:
        return True
    save_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(log_url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            written = 0
            truncated = False
            with open(save_path, 'wb') as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    if written + len(chunk) > max_bytes:
                        chunk = chunk[:max_bytes - written]
                        truncated = True
                    f.write(chunk)
                    written += len(chunk)
                    if truncated:
                        break
            if truncated:
                print(f'[WARN] log file truncated at {max_bytes} bytes '
                      f'[{save_path.name}] (continuing with partial data)',
                      file=sys.stderr)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, OSError) as e:
        print(f'[WARN] log download failed [{save_path.name}]: {e} '
              f'(skipping this file, continuing)', file=sys.stderr)
        if save_path.exists():
            try:
                save_path.unlink()
            except OSError:
                pass
        return False


def iter_log_lines(log_file: Path):
    """Yield decoded lines from a gzip log file (tolerant on encoding).

    A corrupt gzip payload (bad header, truncated or bit-flipped body) must
    never crash the whole run: warn once and skip the file.
    """
    try:
        with gzip.open(log_file, 'rb') as f:
            for raw in f:
                try:
                    yield raw.decode('utf-8', errors='replace')
                except Exception:
                    continue
    except (OSError, EOFError, zlib.error) as e:
        print(f'[WARN] failed to read log file [{log_file.name}]: {e} '
              f'(skipping this file, continuing)', file=sys.stderr)


# ==================== Small helpers ====================

def _fmt_bytes(b: float) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(b) < 1024:
            return f'{b:.1f} {unit}'
        b /= 1024
    return f'{b:.1f} PB'


def _fmt_pct(v: float) -> str:
    return f'{v * 100:.1f}%'


def _normalize_refer_protocol(refer: str) -> str:
    """Merge http/https variants of the same Referer page."""
    if refer.startswith('http://'):
        return 'https://' + refer[7:]
    return refer


def _is_empty_refer(refer: str) -> bool:
    return refer.strip().lower() in EMPTY_VALUES


def _to_subnet24(ip: str) -> str:
    """IPv4 -> /24 subnet string; empty string for IPv6/invalid."""
    if not ip or ':' in ip:
        return ''
    parts = ip.split('.')
    if len(parts) != 4:
        return ''
    for p in parts:
        if not p.isdigit() or not 0 <= int(p) <= 255:
            return ''
    return f'{parts[0]}.{parts[1]}.{parts[2]}.0/24'


def _is_suspicious_ua(ua: str) -> bool:
    if not ua:
        return True
    ua_lower = ua.lower()
    return any(kw in ua_lower for kw in UA_SUSPICIOUS_KEYWORDS)


def _extract_hour(time_str: str) -> Optional[int]:
    if not time_str:
        return None
    m = _TIME_HOUR_PATTERN.match(time_str)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _resp_size_bucket(byts: int) -> str:
    if byts <= 0:
        return 'empty/304'
    if byts < 1024:
        return '<1KB'
    if byts < 10 * 1024:
        return '1KB-10KB'
    if byts < 100 * 1024:
        return '10KB-100KB'
    if byts < 1024 * 1024:
        return '100KB-1MB'
    if byts < 10 * 1024 * 1024:
        return '1MB-10MB'
    return '>10MB'


def _extract_url_pattern(url: str) -> str:
    """URL pattern: keep path and parameter names, blank out values.

    '?a=1&b=2' -> '?a=&b='; URLs without a query string pass through
    unchanged so R08 can aggregate across parameter values.
    """
    if not url:
        return ''
    if '?' not in url:
        return url
    return _URL_VALUE_RE.sub(r'\1', url)


def _extract_refer_domain(refer: str) -> str:
    if not refer or _is_empty_refer(refer):
        return ''
    try:
        return urllib.parse.urlparse(refer).hostname or ''
    except Exception:
        return ''


def _extract_timestamp_sec(time_str: str) -> Optional[int]:
    """Parse '14/Jun/2018:14:08:54 +0800' into a unix second timestamp."""
    if not time_str:
        return None
    m = _TIME_TS_PATTERN.match(time_str)
    if not m:
        return None
    try:
        day, month_str, year, hour, minute, sec, tz = m.groups()
        month = _MONTH_MAP.get(month_str)
        if month is None:
            return None
        tz_sign = '+' if tz[0] == '+' else '-'
        iso_str = (f'{year}-{month:02d}-{int(day):02d}T{hour}:{minute}:{sec}'
                   f'{tz_sign}{tz[1:3]}:{tz[3:5]}')
        return int(datetime.fromisoformat(iso_str).timestamp())
    except Exception:
        return None


# ==================== Aggregation ====================

def aggregate_top(log_files: List[Path], top_n: int = DEFAULT_TOP_N) -> Dict[str, Any]:
    """Single pass over all log files building:
    1) request-count Top-N for URL/IP/subnet/UA/Referer
    2) traffic Top-N for the same four dimensions
    plus commonality dimensions and abuse-analysis raw data.
    """
    url_counter: Counter = Counter()
    ip_counter: Counter = Counter()
    ip_subnet_counter: Counter = Counter()
    ua_counter: Counter = Counter()
    refer_counter: Counter = Counter()

    url_traffic: Counter = Counter()
    ip_traffic: Counter = Counter()
    ip_subnet_traffic: Counter = Counter()
    ua_traffic: Counter = Counter()
    refer_traffic: Counter = Counter()

    status_counter: Counter = Counter()
    cache_counter: Counter = Counter()
    method_counter: Counter = Counter()
    hour_counter: Counter = Counter()
    resp_size_buckets: Counter = Counter()
    resp_size_bucket_traffic: Counter = Counter()

    url_pattern_counter: Counter = Counter()
    refer_pattern_counter: Counter = Counter()
    ip_second_counter: Counter = Counter()
    ip_request_times: Dict[str, List[int]] = {}
    total_lines = 0
    parsed_lines = 0
    total_traffic_bytes = 0

    for log_file in log_files:
        for line in iter_log_lines(log_file):
            total_lines += 1
            entry = parse_log_line(line)
            if not entry:
                continue
            parsed_lines += 1

            url = entry['url']
            ip = entry['ip']
            ua = entry['ua']
            refer = _normalize_refer_protocol(entry['refer'] or '-')
            resp_size = entry['resp_size']
            total_traffic_bytes += resp_size

            if url:
                url_counter[url] += 1
                url_traffic[url] += resp_size
            if ip:
                ip_counter[ip] += 1
                ip_traffic[ip] += resp_size
                subnet = _to_subnet24(ip)
                if subnet:
                    ip_subnet_counter[subnet] += 1
                    ip_subnet_traffic[subnet] += resp_size
            # Normalize empty UA to '-' so empty-UA traffic is counted and
            # R13 (empty UA) can evaluate against the full population.
            ua_key = ua if ua else '-'
            ua_counter[ua_key] += 1
            ua_traffic[ua_key] += resp_size
            refer_counter[refer] += 1
            refer_traffic[refer] += resp_size

            status_counter[entry['status']] += 1
            cache_counter[(entry['cache'] or '-').upper()] += 1
            method_counter[(entry['method'] or '-').upper()] += 1
            hour = _extract_hour(entry['time'])
            if hour is not None:
                hour_counter[hour] += 1
            bucket = _resp_size_bucket(resp_size)
            resp_size_buckets[bucket] += 1
            resp_size_bucket_traffic[bucket] += resp_size

            url_pattern = _extract_url_pattern(url)
            if url_pattern:
                url_pattern_counter[url_pattern] += 1
            refer_domain = _extract_refer_domain(refer)
            if refer_domain:
                refer_pattern_counter[refer_domain] += 1
            ts_sec = _extract_timestamp_sec(entry['time'])
            if ts_sec is not None and ip:
                # Tuple key keeps IPv6 addresses intact (no ':' splitting).
                ip_second_counter[(ip, ts_sec)] += 1
                if ip not in ip_request_times:
                    ip_request_times[ip] = []
                ip_request_times[ip].append(ts_sec)

    def _by_traffic(traffic_counter: Counter, count_counter: Counter,
                    n: int) -> List[Tuple[str, int, int]]:
        return [(k, count_counter.get(k, 0), b)
                for k, b in traffic_counter.most_common(n)]

    return {
        'total_lines': total_lines,
        'parsed_lines': parsed_lines,
        'total_requests': sum(url_counter.values()) or parsed_lines,
        'total_traffic_bytes': total_traffic_bytes,
        'top_urls': url_counter.most_common(top_n),
        'top_ips': ip_counter.most_common(top_n),
        'top_ip_subnets': ip_subnet_counter.most_common(top_n),
        'top_uas': ua_counter.most_common(top_n),
        'top_refers': refer_counter.most_common(top_n),
        'top_urls_traffic': _by_traffic(url_traffic, url_counter, top_n),
        'top_ips_traffic': _by_traffic(ip_traffic, ip_counter, top_n),
        'top_ip_subnets_traffic': _by_traffic(ip_subnet_traffic, ip_subnet_counter, top_n),
        'top_uas_traffic': _by_traffic(ua_traffic, ua_counter, top_n),
        'top_refers_traffic': _by_traffic(refer_traffic, refer_counter, top_n),
        'url_traffic': url_traffic,
        'ip_traffic': ip_traffic,
        'ip_counter': ip_counter,
        'ip_subnet_traffic': ip_subnet_traffic,
        'ip_subnet_counter': ip_subnet_counter,
        'ua_traffic': ua_traffic,
        'ua_counter': ua_counter,
        'refer_traffic': refer_traffic,
        'refer_counter': refer_counter,
        'status_counter': status_counter,
        'cache_counter': cache_counter,
        'method_counter': method_counter,
        'hour_counter': hour_counter,
        'resp_size_buckets': resp_size_buckets,
        'resp_size_bucket_traffic': resp_size_bucket_traffic,
        'url_pattern_counter': url_pattern_counter,
        'refer_pattern_counter': refer_pattern_counter,
        'ip_second_counter': ip_second_counter,
        'ip_request_times': ip_request_times,
    }


# ==================== IP request-frequency distribution ====================

def analyze_ip_freq_distribution(ip_counter: Counter,
                                 total_requests: int) -> Dict[str, Any]:
    """Bucket IPs by per-IP request count; detect machine-like traffic and
    narrow-band frequency clustering of high-frequency IPs."""
    if not ip_counter or not total_requests:
        return {'available': False}

    bucket_ip_count: Dict[str, int] = {b: 0 for b in _IP_FREQ_BUCKETS_ORDER}
    bucket_request_count: Dict[str, int] = {b: 0 for b in _IP_FREQ_BUCKETS_ORDER}
    high_freq_ips: List[Tuple[str, int]] = []

    for ip, cnt in ip_counter.items():
        if cnt <= 10:
            bucket = '1-10'
        elif cnt <= 100:
            bucket = '11-100'
        elif cnt <= 500:
            bucket = '101-500'
        elif cnt <= 1000:
            bucket = '501-1000'
        elif cnt <= 3000:
            bucket = '1001-3000'
        elif cnt <= 5000:
            bucket = '3001-5000'
        else:
            bucket = '>5000'
        bucket_ip_count[bucket] += 1
        bucket_request_count[bucket] += cnt
        if cnt >= MACHINE_FREQ_THRESHOLD:
            high_freq_ips.append((ip, cnt))

    machine_ips = len(high_freq_ips)
    machine_requests = sum(cnt for _, cnt in high_freq_ips)
    machine_ratio = machine_requests / total_requests if total_requests else 0

    cluster_signals: List[Dict[str, Any]] = []
    if len(high_freq_ips) >= 2:
        freq_groups: Counter = Counter()
        for ip, cnt in high_freq_ips:
            freq_groups[(cnt // 100) * 100] += 1
        for group_center, ip_count in freq_groups.most_common(5):
            if ip_count >= 3:
                cluster_signals.append({
                    'freq_range': f'{group_center}-{group_center + 99}',
                    'ip_count': ip_count,
                })

    if machine_ratio >= 0.30 or machine_ips >= 10:
        machine_level = 'high'
    elif machine_ratio >= 0.15 or machine_ips >= 5:
        machine_level = 'medium'
    elif machine_ratio >= 0.05 or machine_ips >= 2:
        machine_level = 'low'
    else:
        machine_level = 'none'

    return {
        'available': True,
        'total_unique_ips': len(ip_counter),
        'bucket_ip_count': bucket_ip_count,
        'bucket_request_count': bucket_request_count,
        'machine_ips': machine_ips,
        'machine_requests': machine_requests,
        'machine_ratio': round(machine_ratio, 4),
        'machine_level': machine_level,
        'cluster_signals': cluster_signals,
        'high_freq_ips': sorted(high_freq_ips, key=lambda x: -x[1])[:20],
    }


# ==================== 13-rule abuse determination ====================

def analyze_abuse(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Judge traffic theft via 13 common-feature rules.

    Rule 3 (overseas-IP ratio) requires IP geo lookups, which this
    read-only build intentionally does not perform; the rule is reported
    as skipped so the full 13-rule structure stays auditable.
    """
    matched_rules: List[str] = []
    weak_rules: List[str] = []
    rule_details: Dict[str, Any] = {}
    total = stats.get('total_requests', 0) or 1
    total_requests = stats.get('total_requests', 0)
    low_sample = stats.get('total_requests', 0) < MIN_SAMPLE_REQUESTS

    # Rule 1: IPs extremely dispersed but per-IP volume highly consistent.
    # Guarded by a dual absolute-volume gate (ABS_R01_*): below the gate the
    # consistency CV is sampling noise and the rule is skipped (E2E bug-3
    # fix: 300 reqs over 250 IPs at 1-2 req/IP used to false-positive).
    ip_counter = stats.get('ip_counter', Counter())
    unique_ips = len(ip_counter)
    if unique_ips >= ABUSE_IP_DISPERSAL_HIGH and total:
        ip_counts = list(ip_counter.values())
        if len(ip_counts) >= 10:
            mean_cnt = sum(ip_counts) / len(ip_counts)
            if mean_cnt > 0:
                if (total_requests >= ABS_R01_MIN_TOTAL_REQUESTS
                        and mean_cnt >= ABS_R01_MIN_MEAN_REQ_PER_IP):
                    variance = sum((c - mean_cnt) ** 2 for c in ip_counts) / len(ip_counts)
                    cv = (variance ** 0.5) / mean_cnt
                    if cv <= ABUSE_IP_CONSISTENCY_CV:
                        matched_rules.append('R01: IPs highly dispersed yet per-IP volume highly consistent')
                        rule_details['ip_dispersion'] = {
                            'unique_ips': unique_ips,
                            'mean_requests_per_ip': round(mean_cnt, 2),
                            'cv': round(cv, 4),
                        }
                else:
                    rule_details['ip_dispersion'] = {
                        'status': 'skipped',
                        'reason': 'absolute-volume gate not met '
                                  f'(total {total_requests} < '
                                  f'{ABS_R01_MIN_TOTAL_REQUESTS} or mean '
                                  f'{mean_cnt:.2f} req/IP < '
                                  f'{ABS_R01_MIN_MEAN_REQ_PER_IP}); '
                                  'per-IP consistency CV is unreliable on '
                                  'such a small sample',
                        'unique_ips': unique_ips,
                        'mean_requests_per_ip': round(mean_cnt, 2),
                    }

    # Rule 2: abnormally high request frequency from a single IP
    if ip_counter and total:
        max_ip, max_cnt = ip_counter.most_common(1)[0]
        if max_cnt >= ABUSE_IP_HIGH_FREQ:
            matched_rules.append('R02: abnormally high request frequency from a single IP')
            rule_details['high_freq_ip'] = {'ip': max_ip, 'count': max_cnt}

    # Rule 3: overseas-IP ratio mismatch (geo lookup not performed in this build)
    rule_details['overseas_ips'] = {
        'status': 'skipped',
        'reason': 'IP geo lookup is not performed by this read-only build; '
                  'evaluate manually if client geography is known',
    }

    # Rule 4: abnormally high empty-Referer share (ratio + absolute gate).
    # Computed over the FULL referer population, not the Top-N list.
    refer_counter = stats.get('refer_counter', Counter())
    top_refers = stats.get('top_refers', [])
    if refer_counter and total:
        empty_refer_cnt = sum(c for r, c in refer_counter.items()
                              if _is_empty_refer(r))
        empty_refer_ratio = empty_refer_cnt / total
        if empty_refer_ratio >= REFER_EMPTY_HIGH and empty_refer_cnt >= ABS_EMPTY_REFER_REQUESTS:
            matched_rules.append('R04: abnormally high empty-Referer share')
            rule_details['empty_refer'] = {
                'ratio': round(empty_refer_ratio, 4),
                'count': empty_refer_cnt,
            }
        elif empty_refer_ratio >= REFER_EMPTY_MED and empty_refer_cnt >= ABS_EMPTY_REFER_REQUESTS_MED:
            # Weak signal only: never drives is_abuse on its own.
            weak_rules.append('R04w: elevated empty-Referer share (weak)')
            rule_details['empty_refer'] = {
                'ratio': round(empty_refer_ratio, 4),
                'count': empty_refer_cnt,
                'weak': True,
            }

    # Rule 5: single forged Referer highly concentrated (ratio + absolute gate)
    refer_pattern_counter = stats.get('refer_pattern_counter', Counter())
    if refer_pattern_counter and total:
        top_refer_domain, top_refer_cnt = refer_pattern_counter.most_common(1)[0]
        if (top_refer_cnt / total >= ABUSE_SINGLE_REFER_HIGH
                and top_refer_domain
                and top_refer_cnt >= ABS_EMPTY_REFER_REQUESTS):
            matched_rules.append('R05: single Referer domain highly concentrated')
            rule_details['single_referer'] = {
                'domain': top_refer_domain,
                'ratio': round(top_refer_cnt / total, 4),
                'count': top_refer_cnt,
            }

    # Rule 6: Top-1 Referer dominance (manual review: competitor/aggregate site)
    if top_refers and total:
        top1_refer, top1_cnt = top_refers[0]
        if (not _is_empty_refer(top1_refer)
                and top1_cnt / total >= 0.60
                and top1_cnt >= ABS_HOT_URL_REQUESTS):
            matched_rules.append('R06: Referer highly concentrated (manual review: competitor or aggregator)')
            rule_details['competitor_referer'] = {
                'refer': top1_refer[:80],
                'ratio': round(top1_cnt / total, 4),
                'count': top1_cnt,
            }

    # Rule 7: requests concentrated on a few large files (ratio + absolute gate)
    bucket_traffic = stats.get('resp_size_bucket_traffic', Counter())
    total_bytes = stats.get('total_traffic_bytes', 0) or 1
    if bucket_traffic:
        big_traffic = bucket_traffic.get('1MB-10MB', 0) + bucket_traffic.get('>10MB', 0)
        big_ratio = big_traffic / total_bytes
        if big_ratio >= ABUSE_BIG_FILE_RATIO and big_traffic >= ABS_BIG_FILE_TRAFFIC_BYTES:
            matched_rules.append('R07: traffic concentrated on large files')
            rule_details['big_files'] = {
                'ratio': round(big_ratio, 4),
                'traffic_bytes': big_traffic,
            }

    # Rule 8: URI with regularly varying parameters (ratio + absolute gate)
    url_pattern_counter = stats.get('url_pattern_counter', Counter())
    if url_pattern_counter and total:
        top_pattern, top_pattern_cnt = url_pattern_counter.most_common(1)[0]
        if ('?' in top_pattern
                and top_pattern_cnt / total >= 0.30
                and top_pattern_cnt >= ABS_HOT_URL_REQUESTS):
            matched_rules.append('R08: URI shows regularly varying parameters')
            rule_details['uri_pattern'] = {
                'pattern': top_pattern[:80],
                'ratio': round(top_pattern_cnt / total, 4),
                'count': top_pattern_cnt,
            }

    # Rule 9: request intervals unnaturally uniform
    ip_request_times = stats.get('ip_request_times', {})
    if ip_request_times:
        uniform_interval_ips = []
        for ip, times in list(ip_request_times.items())[:200]:
            if len(times) >= 50:
                times_sorted = sorted(times)
                intervals = [times_sorted[i + 1] - times_sorted[i]
                             for i in range(len(times_sorted) - 1)]
                if intervals:
                    mean_interval = sum(intervals) / len(intervals)
                    if mean_interval > 0:
                        variance = sum((iv - mean_interval) ** 2
                                       for iv in intervals) / len(intervals)
                        cv = (variance ** 0.5) / mean_interval
                        if cv <= ABUSE_INTERVAL_CV_THRESHOLD:
                            uniform_interval_ips.append(
                                (ip, round(cv, 4), round(mean_interval, 2)))
        if uniform_interval_ips:
            matched_rules.append('R09: request intervals unnaturally uniform')
            rule_details['uniform_intervals'] = {
                'ip_count': len(uniform_interval_ips),
                'top_ips': uniform_interval_ips[:5],
            }

    # Rule 10: massive concurrent requests within the same second
    ip_second_counter = stats.get('ip_second_counter', Counter())
    if ip_second_counter:
        ip_max_concurrent: Dict[str, int] = {}
        for key, cnt in ip_second_counter.most_common(500):
            # key is an (ip, unix_second) tuple; IPv6-safe by construction.
            ip = key[0] if isinstance(key, tuple) else str(key)
            if cnt >= ABUSE_CONCURRENT_THRESHOLD:
                if ip not in ip_max_concurrent or cnt > ip_max_concurrent[ip]:
                    ip_max_concurrent[ip] = cnt
        if ip_max_concurrent:
            matched_rules.append('R10: massive same-second concurrent requests')
            rule_details['concurrent_requests'] = {
                'ip_count': len(ip_max_concurrent),
                'top_ips': sorted(ip_max_concurrent.items(),
                                  key=lambda x: -x[1])[:5],
            }

    # Rule 11: UAs concentrated on non-browser identifiers (ratio + absolute
    # gate). Computed over the FULL UA population, not the Top-N list.
    ua_counter = stats.get('ua_counter', Counter())
    top_uas = stats.get('top_uas', [])
    if ua_counter and total:
        suspicious_ua_cnt = sum(c for ua, c in ua_counter.items()
                                if _is_suspicious_ua(ua))
        suspicious_ua_ratio = suspicious_ua_cnt / total
        if suspicious_ua_ratio >= 0.30 and suspicious_ua_cnt >= ABS_SUSPICIOUS_UA_REQUESTS:
            matched_rules.append('R11: UAs concentrated on non-browser identifiers')
            rule_details['non_browser_ua'] = {
                'ratio': round(suspicious_ua_ratio, 4),
                'count': suspicious_ua_cnt,
                'top_uas': [ua for ua, _ in ua_counter.most_common()
                            if _is_suspicious_ua(ua)][:3],
            }

    # Rule 12: fully identical UA with dominant share (ratio + absolute gate)
    if top_uas and total:
        top1_ua, top1_ua_cnt = top_uas[0]
        if (top1_ua and top1_ua != '-'
                and top1_ua_cnt / total >= ABUSE_UA_CONSISTENCY_HIGH
                and top1_ua_cnt >= ABS_SUSPICIOUS_UA_REQUESTS):
            is_mainstream_browser = any(kw in top1_ua.lower() for kw in (
                'chrome/', 'firefox/', 'safari/', 'edge/', 'msie ', 'trident/'))
            if not is_mainstream_browser:
                matched_rules.append('R12: fully identical UA with dominant share')
                rule_details['consistent_ua'] = {
                    'ua': top1_ua[:80],
                    'ratio': round(top1_ua_cnt / total, 4),
                    'count': top1_ua_cnt,
                }

    # Rule 13: UA empty or '-' (ratio + absolute gate). Empty UAs are
    # normalized to '-' during aggregation, evaluated on the full population.
    if ua_counter and total:
        empty_ua_cnt = ua_counter.get('-', 0)
        empty_ua_ratio = empty_ua_cnt / total
        if empty_ua_ratio >= ABUSE_EMPTY_UA_RATIO and empty_ua_cnt >= ABS_SUSPICIOUS_UA_REQUESTS_MED:
            matched_rules.append("R13: UA empty or '-'")
            rule_details['empty_ua'] = {
                'ratio': round(empty_ua_ratio, 4),
                'count': empty_ua_cnt,
            }

    # Overall: any STRONG rule indicates abuse, except on tiny samples.
    # Weak rules (R04w) are advisory hints only and never drive is_abuse.
    is_abuse = len(matched_rules) >= 1
    if low_sample:
        is_abuse = False

    return {
        'is_abuse': is_abuse,
        'matched_rules': matched_rules,
        'weak_rules': weak_rules,
        'rule_details': rule_details,
        'total_rules_matched': len(matched_rules),
        'low_sample': low_sample,
        'total_requests': stats.get('total_requests', 0),
    }


def analyze_risk(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Dual-gate risk scoring: a ratio signal only scores when the matching
    absolute-volume gate is also met. Total < MIN_SAMPLE_REQUESTS forces
    the level down to 'low'."""
    total = stats.get('total_requests', 0)
    signals: List[str] = []
    score = 0
    low_sample = bool(total) and total < MIN_SAMPLE_REQUESTS

    suspicious_ips: List[str] = []
    top_ips = stats.get('top_ips', [])
    if top_ips and total:
        top1_ip, top1_cnt = top_ips[0]
        ratio = top1_cnt / total
        if ratio >= IP_HIGH_THRESHOLD and top1_cnt >= ABS_TOP1_IP_REQUESTS:
            signals.append(f'[HIGH] Top-1 IP [{top1_ip}] holds {_fmt_pct(ratio)} '
                           f'of requests ({top1_cnt:,} reqs)')
            score += 35
            suspicious_ips.append(top1_ip)
        elif ratio >= IP_MED_THRESHOLD and top1_cnt >= ABS_TOP1_IP_REQUESTS_MED:
            signals.append(f'[MED] Top-1 IP [{top1_ip}] holds {_fmt_pct(ratio)} '
                           f'of requests ({top1_cnt:,} reqs)')
            score += 15
            suspicious_ips.append(top1_ip)
        elif ratio >= IP_HIGH_THRESHOLD and top1_cnt < ABS_TOP1_IP_REQUESTS_MED:
            signals.append(f'[INFO] Top-1 IP share {_fmt_pct(ratio)} but only '
                           f'{top1_cnt:,} reqs (below absolute gate), not scored')
        top5_cnt = sum(c for _, c in top_ips[:5])
        top5_ratio = top5_cnt / total
        if top5_ratio >= IP_TOP5_THRESHOLD and top5_cnt >= ABS_TOP5_IP_REQUESTS:
            signals.append(f'[HIGH] Top-5 IPs hold {_fmt_pct(top5_ratio)} '
                           f'({top5_cnt:,} reqs), traffic highly concentrated')
            score += 20

    refer_counter = stats.get('refer_counter', Counter())
    empty_refer_cnt = sum(c for r, c in refer_counter.items()
                          if _is_empty_refer(r))
    empty_refer_ratio = empty_refer_cnt / total if total else 0
    if empty_refer_ratio >= REFER_EMPTY_HIGH and empty_refer_cnt >= ABS_EMPTY_REFER_REQUESTS:
        signals.append(f'[HIGH] Empty Referer {_fmt_pct(empty_refer_ratio)} '
                       f'({empty_refer_cnt:,} reqs), likely crawler/abuse')
        score += 30
    elif empty_refer_ratio >= REFER_EMPTY_MED and empty_refer_cnt >= ABS_EMPTY_REFER_REQUESTS_MED:
        signals.append(f'[MED] Empty Referer {_fmt_pct(empty_refer_ratio)} '
                       f'({empty_refer_cnt:,} reqs)')
        score += 15
    elif empty_refer_ratio >= REFER_EMPTY_HIGH and empty_refer_cnt < ABS_EMPTY_REFER_REQUESTS_MED:
        signals.append(f'[INFO] Empty Referer share {_fmt_pct(empty_refer_ratio)} '
                       f'but only {empty_refer_cnt:,} reqs (below absolute gate), not scored')

    top_urls = stats.get('top_urls', [])
    if top_urls and total:
        top1_url, top1_cnt = top_urls[0]
        ratio = top1_cnt / total
        if ratio >= URL_HIGH_THRESHOLD and top1_cnt >= ABS_HOT_URL_REQUESTS:
            signals.append(f'[HIGH] Single URL [{top1_url[:60]}] holds '
                           f'{_fmt_pct(ratio)} ({top1_cnt:,} reqs), targeted scraping suspected')
            score += 25
        elif ratio >= URL_MED_THRESHOLD and top1_cnt >= ABS_HOT_URL_REQUESTS_MED:
            signals.append(f'[MED] Single URL [{top1_url[:60]}] holds '
                           f'{_fmt_pct(ratio)} ({top1_cnt:,} reqs)')
            score += 10
        elif ratio >= URL_HIGH_THRESHOLD and top1_cnt < ABS_HOT_URL_REQUESTS_MED:
            signals.append(f'[INFO] Hot URL share {_fmt_pct(ratio)} but only '
                           f'{top1_cnt:,} reqs (below absolute gate), not scored')

    ua_counter = stats.get('ua_counter', Counter())
    suspicious_ua_cnt = sum(c for ua, c in ua_counter.items()
                            if _is_suspicious_ua(ua))
    suspicious_ua_ratio = suspicious_ua_cnt / total if total else 0
    suspicious_uas: List[str] = [ua for ua, _ in ua_counter.most_common()
                                 if _is_suspicious_ua(ua)][:3]
    if suspicious_ua_ratio >= UA_HIGH_THRESHOLD and suspicious_ua_cnt >= ABS_SUSPICIOUS_UA_REQUESTS:
        signals.append(f'[HIGH] Suspicious tool-like UAs hold {_fmt_pct(suspicious_ua_ratio)} '
                       f'({suspicious_ua_cnt:,} reqs)')
        score += 25
    elif suspicious_ua_ratio >= UA_MED_THRESHOLD and suspicious_ua_cnt >= ABS_SUSPICIOUS_UA_REQUESTS_MED:
        signals.append(f'[MED] Suspicious tool-like UAs hold {_fmt_pct(suspicious_ua_ratio)} '
                       f'({suspicious_ua_cnt:,} reqs)')
        score += 10

    if low_sample:
        signals.insert(0, f'[INFO] Sample too small ({total:,} < {MIN_SAMPLE_REQUESTS:,}); '
                          f'ratio signals are unreliable, risk forced to low')
        score = min(score, 20)
        level = 'low'
    else:
        score = min(score, 100)
        if score >= 60:
            level = 'high'
        elif score >= 30:
            level = 'medium'
        else:
            level = 'low'

    return {
        'risk_level': level,
        'risk_score': score,
        'signals': signals,
        'suspicious_ips': suspicious_ips,
        'suspicious_uas': suspicious_uas,
        'empty_refer_ratio': round(empty_refer_ratio, 4),
        'empty_refer_count': empty_refer_cnt,
        'suspicious_ua_ratio': round(suspicious_ua_ratio, 4),
        'suspicious_ua_count': suspicious_ua_cnt,
        'low_sample': low_sample,
        'total_requests': total,
    }


# ==================== Scenario classification T1~T6 ====================

def classify_scenario(stats: Dict[str, Any], abuse: Dict[str, Any],
                      risk: Dict[str, Any]) -> Dict[str, Any]:
    """Classify into T1~T6 based on four-dimension concentration.

    T1 URL concentration | T2 IP/subnet concentration | T3 Referer anomaly
    T4 UA anomaly | T5 benign surge (dispersed + business event)
    T6 cache hit-rate drop causing origin amplification (high MISS share)
    """
    total = stats.get('total_requests', 0) or 1
    findings: List[str] = []

    url_share = (stats['top_urls'][0][1] / total) if stats.get('top_urls') else 0
    ip_share = (stats['top_ips'][0][1] / total) if stats.get('top_ips') else 0
    subnet_share = (stats['top_ip_subnets'][0][1] / total) if stats.get('top_ip_subnets') else 0
    empty_refer_share = risk.get('empty_refer_ratio', 0)
    refer_domain_counter: Counter = stats.get('refer_pattern_counter', Counter())
    refer_share = (refer_domain_counter.most_common(1)[0][1] / total) if refer_domain_counter else 0
    ua_share = risk.get('suspicious_ua_ratio', 0)

    cache_counter: Counter = stats.get('cache_counter', Counter())
    cache_total = sum(cache_counter.values()) or 1
    miss_share = sum(c for k, c in cache_counter.items()
                     if 'MISS' in str(k).upper()) / cache_total

    scenario = 'T5'
    if url_share >= SCENARIO_CONCENTRATION:
        scenario = 'T1'
        findings.append(f'URL dimension concentrated: top URL share {_fmt_pct(url_share)}')
    elif max(ip_share, subnet_share) >= SCENARIO_CONCENTRATION:
        scenario = 'T2'
        findings.append(f'IP/subnet dimension concentrated: top IP share '
                        f'{_fmt_pct(ip_share)}, top /24 share {_fmt_pct(subnet_share)}')
    elif max(empty_refer_share, refer_share) >= SCENARIO_CONCENTRATION:
        scenario = 'T3'
        findings.append(f'Referer dimension anomalous: empty-Referer share '
                        f'{_fmt_pct(empty_refer_share)}, top Referer-domain share {_fmt_pct(refer_share)}')
    elif ua_share >= SCENARIO_CONCENTRATION:
        scenario = 'T4'
        findings.append(f'UA dimension anomalous: suspicious-UA share {_fmt_pct(ua_share)}')
    elif miss_share >= 0.50:
        scenario = 'T6'
        findings.append(f'Cache MISS share {_fmt_pct(miss_share)}: origin amplification suspected')
    else:
        findings.append('All four dimensions dispersed; consistent with a benign '
                        'traffic surge if a business event matches the window (confirm with user)')

    scenario_labels = {
        'T1': 'URL concentration (few hot objects: targeted scraping or large-file downloads)',
        'T2': 'IP/IP-subnet concentration (high-bandwidth attack sources or botnet/IP pool)',
        'T3': 'Referer anomaly (hotlink abuse or empty-Referer direct access)',
        'T4': 'UA anomaly (script/tool traffic)',
        'T5': 'Benign surge (dispersed pattern; cross-check business events before concluding)',
        'T6': 'Cache hit-rate drop causing origin amplification',
    }
    return {
        'scenario': scenario,
        'scenario_label': scenario_labels[scenario],
        'findings': findings,
        'shares': {
            'top_url': round(url_share, 4),
            'top_ip': round(ip_share, 4),
            'top_subnet': round(subnet_share, 4),
            'empty_referer': round(empty_refer_share, 4),
            'top_referer_domain': round(refer_share, 4),
            'suspicious_ua': round(ua_share, 4),
            'cache_miss': round(miss_share, 4),
        },
        'abuse_verdict': abuse.get('is_abuse', False),
        'risk_level': risk.get('risk_level', 'low'),
    }


def build_recommendations(stats: Dict[str, Any], risk: Dict[str, Any],
                          scenario: Dict[str, Any]) -> List[str]:
    """Evidence-based manual protection guidance (this skill never applies
    any configuration change)."""
    recs: List[str] = []

    suspicious_ips = risk.get('suspicious_ips', [])
    if suspicious_ips:
        recs.append(
            f"Top IPs (e.g. {', '.join(suspicious_ips[:3])}) show concentrated volume; "
            'manually consider the CDN IP blacklist/whitelist (console: Access Control '
            '-> IP Black/White List)')
    if risk.get('empty_refer_ratio', 0) >= REFER_EMPTY_MED:
        recs.append(
            f"Empty-Referer share is {_fmt_pct(risk['empty_refer_ratio'])}; "
            'manually consider Referer-based hotlink protection (console: Access Control '
            '-> Referer Hotlink Protection). Cross-check business type first: download/API '
            'scenarios legitimately send empty Referer and would be blocked')
    if risk.get('suspicious_ua_ratio', 0) >= UA_MED_THRESHOLD:
        recs.append(
            f"Suspicious tool-like UA share is {_fmt_pct(risk['suspicious_ua_ratio'])}; "
            'manually consider a UA blacklist (console: Access Control -> UA Black/White List)')
    top_urls = stats.get('top_urls', [])
    total = stats.get('total_requests', 0)
    if top_urls and total and top_urls[0][1] / total >= URL_MED_THRESHOLD:
        recs.append(
            f"Hot URL share is {_fmt_pct(top_urls[0][1] / total)}; "
            'manually consider URL authentication (signing) plus a bandwidth cap as the '
            'last-resort bill guard')
    if scenario.get('scenario') == 'T6':
        recs.append('Investigate cache configuration: TTL rules, parameter filtering and '
                    'Vary handling (MISS amplification raises origin load and egress)')
    # Safety-net advice is ALWAYS present, even when scenario-specific
    # recommendations already fill the list.
    fallback = ('Fallback guard: configure a bandwidth cap and bill alerts so a future '
                'spike is contained automatically')
    return recs[:4] + [fallback]


# ==================== Main flow ====================

def analyze(domain: str, start_ts: int, end_ts: int, top_n: int,
            log_dir: Path, max_files: int, keep_logs: bool,
            verbose: bool = True) -> Dict[str, Any]:
    """Full read-only offline-log analysis; degrade-and-continue on errors."""

    def log(msg: str = ''):
        if verbose:
            print(msg, flush=True)

    start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    log('=' * 70)
    log('CDN Offline-Log Traffic Forensics (read-only)')
    log('=' * 70)
    log(f'  Domain    : {domain}')
    log(f'  Window    : {start_iso} ~ {end_iso} UTC')
    log(f'  Session ID: {_SESSION_ID}')

    # Step 1: list offline logs via DescribeCdnDomainLogs
    log()
    log('[Step 1] describe-cdn-domain-logs: list offline access logs')
    api_error: Optional[str] = None
    entries: List[Dict[str, Any]] = []
    try:
        response = _describe_cdn_domain_logs(domain, start_iso, end_iso)
        entries = extract_log_entries(response)
        log(f'  Found {len(entries)} log file(s)')
    except RuntimeError as e:
        api_error = str(e)
        print(f'[WARN] describe-cdn-domain-logs failed -> {api_error} '
              f'(continuing with empty log list)', file=sys.stderr)

    if not entries:
        # Stable error_code contract: a critical API error passes through
        # (exit 1); an empty result without an API error is the benign
        # 'NoLogsInWindow' state (exit 2).
        if api_error:
            error_code = str(api_error).split(':', 1)[0].strip() or 'CliError'
        else:
            error_code = 'NoLogsInWindow'
        return {
            'ok': False,
            'error_code': error_code,
            'domain': domain,
            'session_id': _SESSION_ID,
            'window': {'start': start_iso, 'end': end_iso},
            'error': (api_error or 'No offline logs found for the window. '
                      'Possible causes: window too recent (offline logs lag '
                      '3-4 hours), no traffic in window, or domain mismatch'),
        }

    # Step 2: download logs (degrade-and-continue per file)
    log()
    log('[Step 2] Download gzip log files')
    if len(entries) > max_files:
        log(f'  [WARN] {len(entries)} files exceed limit {max_files}; '
            f'downloading the first {max_files} only')
        entries = entries[:max_files]
    log_dir.mkdir(parents=True, exist_ok=True)
    log_files: List[Path] = []
    for entry in entries:
        url = _normalize_log_url(entry['log_path'])
        if not url:
            continue
        # Sanitize the log name to a bare filename (no path traversal).
        name = Path(entry['log_name'] or url.rsplit('/', 1)[-1] or 'log.gz').name
        if not name:
            name = 'log.gz'
        save_path = log_dir / name
        if download_log(url, save_path):
            log_files.append(save_path)
            log(f'  Downloaded: {name}')
    log(f'  Downloaded {len(log_files)}/{len(entries)} file(s)')

    if not log_files:
        return {
            'ok': False,
            'error_code': 'AllDownloadsFailed',
            'domain': domain,
            'session_id': _SESSION_ID,
            'window': {'start': start_iso, 'end': end_iso},
            'error': 'All log downloads failed; check network access to the '
                     'log storage endpoint and retry later',
        }

    # Step 3: aggregate
    log()
    log('[Step 3] Parse logs and build four-dimension Top statistics')
    stats = aggregate_top(log_files, top_n=top_n)
    log(f"  Lines: {stats['parsed_lines']}/{stats['total_lines']} parsed | "
        f"requests={stats['total_requests']} | "
        f"traffic={_fmt_bytes(stats['total_traffic_bytes'])}")

    # Step 4: frequency + abuse + risk + scenario
    ip_freq = analyze_ip_freq_distribution(stats['ip_counter'],
                                           stats['total_requests'])
    abuse = analyze_abuse(stats)
    risk = analyze_risk(stats)
    scenario = classify_scenario(stats, abuse, risk)
    recommendations = build_recommendations(stats, risk, scenario)

    log()
    log(f"[Step 4] Abuse rules matched: {abuse['total_rules_matched']} | "
        f"risk={risk['risk_level']} (score {risk['risk_score']}) | "
        f"scenario={scenario['scenario']}")

    # Cleanup downloaded logs unless --keep-logs
    if not keep_logs:
        for f in log_files:
            try:
                f.unlink()
            except OSError:
                pass

    def _top_tuples(items):
        return [{'key': k, 'count': c} for k, c in items]

    def _top_traffic_tuples(items):
        return [{'key': k, 'count': c, 'bytes': b} for k, c, b in items]

    return {
        'ok': True,
        'error_code': '',
        'domain': domain,
        'session_id': _SESSION_ID,
        'window': {'start': start_iso, 'end': end_iso},
        'log_files': len(log_files),
        'summary': {
            'total_lines': stats['total_lines'],
            'parsed_lines': stats['parsed_lines'],
            'total_requests': stats['total_requests'],
            'total_traffic_bytes': stats['total_traffic_bytes'],
        },
        'top_by_requests': {
            'urls': _top_tuples(stats['top_urls']),
            'ips': _top_tuples(stats['top_ips']),
            'ip_subnets': _top_tuples(stats['top_ip_subnets']),
            'user_agents': _top_tuples(stats['top_uas']),
            'referrers': _top_tuples(stats['top_refers']),
        },
        'top_by_traffic': {
            'urls': _top_traffic_tuples(stats['top_urls_traffic']),
            'ips': _top_traffic_tuples(stats['top_ips_traffic']),
            'ip_subnets': _top_traffic_tuples(stats['top_ip_subnets_traffic']),
            'user_agents': _top_traffic_tuples(stats['top_uas_traffic']),
            'referrers': _top_traffic_tuples(stats['top_refers_traffic']),
        },
        'commonality': {
            'status_codes': dict(stats['status_counter']),
            'cache_status': dict(stats['cache_counter']),
            'methods': dict(stats['method_counter']),
            'hourly_distribution': dict(sorted(stats['hour_counter'].items())),
            'response_size_buckets': {b: stats['resp_size_buckets'].get(b, 0)
                                      for b in _RESP_SIZE_BUCKETS_ORDER},
        },
        'ip_frequency': ip_freq,
        'abuse': abuse,
        'risk': risk,
        'scenario': scenario,
        'recommendations': recommendations,
    }


# ==================== Text report ====================

def _translate_error(err: str) -> str:
    """Translate a raw CLI/API error into an actionable hint."""
    code = str(err).split(':', 1)[0].strip()
    guidance = ERROR_GUIDANCE.get(code)
    if guidance:
        return f'{code} -> {guidance}'
    return str(err)[:300]


def print_text(result: Dict[str, Any]):
    print()
    print('=' * 70)
    print('CDN Offline-Log Traffic Forensics Report')
    print('=' * 70)
    win = result.get('window') or {}
    print(f"Domain    : {result.get('domain')}")
    print(f"Window    : {win.get('start')} ~ {win.get('end')} UTC")
    print(f"Session ID: {result.get('session_id')}")
    print('-' * 70)

    if not result.get('ok'):
        error_code = result.get('error_code') or ''
        print(f"[FAIL] {result.get('error', '')} "
              f"(error_code: {error_code or 'n/a'})")
        guidance = ERROR_GUIDANCE.get(error_code)
        if guidance:
            print(f'       What to do: {guidance}')
        else:
            print(f'       What to do: {_translate_error(result.get("error", ""))}')
        print('=' * 70)
        return

    abuse = result['abuse']
    risk = result['risk']
    sc = result['scenario']

    # ---- Executive summary (conclusion first, for non-technical users) ----
    print('[EXECUTIVE SUMMARY]')
    verdict_txt = ('ABUSE SUSPECTED' if abuse['is_abuse']
                   else 'no abuse pattern detected')
    print(f'  Verdict : {verdict_txt} '
          f"(risk: {risk['risk_level']}, score {risk['risk_score']})")
    print(f"    ({ABUSE_VERDICT_EXPLAIN[bool(abuse['is_abuse'])]})")
    print(f"  Scenario: {sc['scenario']} - {sc['scenario_label']}")
    strongest = next((sig for sig in risk['signals']
                      if sig.startswith('[HIGH]')),
                     abuse['matched_rules'][0]
                     if abuse['matched_rules'] else '')
    print(f'  Strongest evidence: '
          f"{strongest or 'no significant abuse signal found'}")
    print('-' * 70)

    s = result['summary']
    print(f"Parsed {s['parsed_lines']}/{s['total_lines']} lines | "
          f"{s['total_requests']:,} requests | "
          f"{_fmt_bytes(s['total_traffic_bytes'])} traffic | "
          f"{result['log_files']} log file(s)")

    def _print_top(title: str, rows, traffic_mode=False):
        print(f'\n  {title}')
        if not rows:
            print('    (no data)')
            return
        for i, r in enumerate(rows, start=1):
            if traffic_mode:
                print(f"    [{i}] {r['key'][:90]} | reqs={r['count']:,} | "
                      f"traffic={_fmt_bytes(r['bytes'])}")
            else:
                print(f"    [{i}] {r['key'][:90]} | reqs={r['count']:,}")

    print('\n[Top by request count]')
    for title, key in (('Top URLs', 'urls'), ('Top IPs', 'ips'),
                       ('Top IP /24 subnets', 'ip_subnets'),
                       ('Top Referrers', 'referrers'),
                       ('Top UserAgents', 'user_agents')):
        _print_top(title, result['top_by_requests'][key])

    print('\n[Top by traffic volume]')
    for title, key in (('Top URLs', 'urls'), ('Top IPs', 'ips'),
                       ('Top IP /24 subnets', 'ip_subnets'),
                       ('Top Referrers', 'referrers'),
                       ('Top UserAgents', 'user_agents')):
        _print_top(title, result['top_by_traffic'][key], traffic_mode=True)

    c = result['commonality']
    print('\n[Commonality]')
    print(f"  Status codes : {dict(sorted(c['status_codes'].items(), key=lambda x: -x[1]))}")
    print(f"  Cache status : {dict(sorted(c['cache_status'].items(), key=lambda x: -x[1]))}")
    print(f"  Methods      : {dict(sorted(c['methods'].items(), key=lambda x: -x[1]))}")
    print(f"  Size buckets : {c['response_size_buckets']}")
    hourly = c.get('hourly_distribution') or {}
    hourly_fmt = {f'{int(h):02d}:00': n for h, n in
                  sorted(hourly.items(), key=lambda x: int(x[0]))}
    print(f"  Hourly dist  : {hourly_fmt or '(no data)'}")
    print('                   (hour buckets follow log-line timestamps, '
          '+0800 Beijing time; the query window itself is UTC)')

    freq = result.get('ip_frequency') or {}
    if freq.get('available'):
        print('\n[IP request-frequency distribution]')
        print(f"  Machine-like IPs (>= {MACHINE_FREQ_THRESHOLD} reqs): "
              f"{freq['machine_ips']} ({_fmt_pct(freq['machine_ratio'])} of requests), "
              f"level={freq['machine_level']}")
        if freq.get('cluster_signals'):
            print(f"  Narrow-band clustering: {freq['cluster_signals']}")

    abuse = result['abuse']
    print('\n[Abuse determination (13 rules)]')
    print(f"  Verdict: {'ABUSE SUSPECTED' if abuse['is_abuse'] else 'no abuse pattern'} | "
          f"matched {abuse['total_rules_matched']} rule(s)"
          + (' | LOW SAMPLE: verdict downgraded' if abuse['low_sample'] else ''))
    for rule in abuse['matched_rules']:
        print(f'    - {rule}')
    for rule in abuse.get('weak_rules', []):
        print(f'    - [hint] {rule}')
    skipped = [f"{k}: {v.get('reason')}" for k, v in
               (abuse.get('rule_details') or {}).items()
               if isinstance(v, dict) and v.get('status') == 'skipped']
    for reason in skipped:
        print(f'    - [skipped] {reason}')

    risk = result['risk']
    print('\n[Risk score]')
    print(f"  Level={risk['risk_level']} score={risk['risk_score']}")
    for sig in risk['signals']:
        print(f'    {sig}')

    sc = result['scenario']
    print('\n[Scenario classification]')
    print(f"  {sc['scenario']}: {sc['scenario_label']}")
    print(f"    ({SCENARIO_EXPLAIN.get(sc['scenario'], '')})")
    for f in sc['findings']:
        print(f'    - {f}')

    print('\n[Recommendations (manual guidance only - this skill is read-only)]')
    for i, r in enumerate(result['recommendations'], start=1):
        print(f'  {i}. {r}')

    print('=' * 70)
    print()


def _parse_time(s: str) -> int:
    """Accept 'YYYY-MM-DD HH:MM:SS' (UTC) or a unix timestamp string."""
    s = s.strip()
    if s.isdigit():
        return int(s)
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return int(datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"unrecognized time format: '{s}'; use 'YYYY-MM-DD HH:MM:SS' (UTC) or unix timestamp")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='cdn_traffic_analysis.py',
        description='CDN offline-log traffic forensics '
                    '(DescribeCdnDomainLogs + local parsing, read-only)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze yesterday's full day (UTC) by default
  python3 cdn_traffic_analysis.py --domain example.com

  # Custom window (keep it within ~24h; logs are hourly)
  python3 cdn_traffic_analysis.py --domain example.com \\
      --start-time "2026-08-20 10:00:00" --end-time "2026-08-20 12:00:00"

  # JSON output / keep downloaded logs
  python3 cdn_traffic_analysis.py --domain example.com --json --keep-logs
        """,
    )
    parser.add_argument('--domain', '-d', required=True,
                        help='CDN accelerated domain name')
    parser.add_argument('--start-time', type=_parse_time, metavar='TIME',
                        help='Window start, UTC (default: yesterday 00:00:00)')
    parser.add_argument('--end-time', type=_parse_time, metavar='TIME',
                        help='Window end, UTC (default: yesterday 23:59:59)')
    parser.add_argument('--top-n', type=int, default=DEFAULT_TOP_N, metavar='N',
                        help=f'Top-N rows per dimension (default {DEFAULT_TOP_N})')
    parser.add_argument('--log-dir', type=Path, default=DEFAULT_LOG_DIR, metavar='DIR',
                        help=f'Local log cache directory (default {DEFAULT_LOG_DIR})')
    parser.add_argument('--max-files', type=int, default=MAX_LOG_FILES, metavar='N',
                        help=f'Max log files to download (default {MAX_LOG_FILES})')
    parser.add_argument('--keep-logs', action='store_true',
                        help='Keep downloaded log files (default: cleaned up after analysis)')
    parser.add_argument('--json', action='store_true',
                        help='JSON output (auto-silences analysis)')
    parser.add_argument('--quiet', action='store_true',
                        help='Text mode: suppress analysis (final report only)')
    args = parser.parse_args()

    # Default window: yesterday 00:00:00 ~ 23:59:59 UTC (offline logs lag 3-4h)
    now_dt = datetime.now(timezone.utc)
    yesterday_start = (now_dt - timedelta(days=1)).replace(hour=0, minute=0,
                                                           second=0, microsecond=0)
    start_ts = args.start_time if args.start_time else int(yesterday_start.timestamp())
    end_ts = args.end_time if args.end_time else int(yesterday_start.replace(
        hour=23, minute=59, second=59).timestamp())
    if start_ts >= end_ts:
        print('[FAIL] Error: start time must be earlier than end time', file=sys.stderr)
        sys.exit(1)
    if args.top_n <= 0:
        print('[FAIL] Error: --top-n must be a positive integer', file=sys.stderr)
        sys.exit(1)
    if args.max_files <= 0:
        print('[FAIL] Error: --max-files must be a positive integer', file=sys.stderr)
        sys.exit(1)

    verbose = not (args.json or args.quiet)

    result = analyze(args.domain, start_ts, end_ts, args.top_n,
                     args.log_dir, args.max_files, args.keep_logs,
                     verbose=verbose)

    if args.json:
        # Contract: with --json, stdout carries ONLY the JSON document;
        # all diagnostics are emitted on stderr.
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print_text(result)

    # Exit codes: 0 = completed with usable data; 2 = benign no-data
    # (no offline logs in the window, not an error); 1 = real error.
    if result.get('ok'):
        sys.exit(0)
    sys.exit(2 if result.get('error_code') == 'NoLogsInWindow' else 1)


if __name__ == '__main__':
    main()
