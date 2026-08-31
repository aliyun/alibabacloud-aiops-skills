#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDN Traffic Anomaly Diagnosis Tool (read-only)

APIs used (all Describe-class, invoked via aliyun CLI plugin mode):
    GetCallerIdentity              (sts, identity label only)
    DescribeDomainUsageData        (cdn, bps + traf per interval, primary)
    DescribeDomainBpsData          (cdn, bandwidth trend backup)
    DescribeDomainQpsData          (cdn, request-rate correlation)
    DescribeDomainRealTimeBpsData  (cdn, last-hour fine-grained view)

Workflow:
    1. Verify caller identity via sts get-caller-identity (traceability only)
    2. Pull bps/flow/qps usage series for the requested time window
    3. Compute baseline (mean/median) and peak for each series
    4. Locate anomalous time windows (intervals above threshold)
    5. Output a structured conclusion (JSON via --json, or a text report)

Auth: relies entirely on the aliyun CLI default credential chain (CLI config
or platform-injected environment); this script performs no explicit auth
handling and never reads, prints, or passes AK/SK/STS tokens.

Usage:
    python3 cdn_traffic_anomaly.py --domain example.com
    python3 cdn_traffic_anomaly.py --domain example.com --days 3 --interval 300
    python3 cdn_traffic_anomaly.py --domain example.com --json
"""

import argparse
import json
import re
import statistics
import subprocess
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

# Per-run session id for platform-level tracing (Observability)
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-cdn-traffic-anomaly/{_SESSION_ID}"

# ==================== Embedded analysis constants ====================
# Threshold model: an interval is anomalous when its value exceeds
# max(mean * PEAK_MEAN_RATIO, median * PEAK_MEDIAN_RATIO).
PEAK_MEAN_RATIO = 3.0
PEAK_MEDIAN_RATIO = 4.0
# Verdict grading on peak/baseline ratio
SUSPICIOUS_RATIO = 2.0   # peak >= mean * 2.0  -> suspicious
ANOMALOUS_RATIO = 3.0    # peak >= mean * 3.0  -> anomalous
MIN_POINTS_FOR_BASELINE = 6

DEFAULT_DAYS = 7
DEFAULT_INTERVAL = 3600          # seconds: 300 / 3600 / 86400
REALTIME_LOOKBACK_MINUTES = 60   # real-time bps covers the last hour
CLI_TIMEOUT_SECONDS = 30

# Keys that plausibly carry a timestamp / a numeric value in CDN usage
# responses. Parsing is tolerant: responses are walked recursively and the
# first list of dicts carrying one time-like and one value-like key is used.
TIME_KEYS = ('Time', 'TimeStamp', 'StartTime', 'EndTime', 'DataTimeStamp')
VALUE_KEYS = ('Value', 'Bps', 'Flow', 'Qps', 'Traffic', 'Acc',
              'DomesticValue', 'OverseasValue', 'GlobalValue',
              'DomesticBps', 'OverseasBps', 'BpsModel')

# Critical API error codes that must surface as hard failures (exit 1)
# rather than benign no-data (exit 2).
CRITICAL_API_ERROR_CODES = ('InvalidDomain.NotFound',
                            'InvalidAccessKeyId.NotFound')

# Plain-language explanations of verdict values for non-technical readers
# (text report only; JSON keeps the raw enum).
VERDICT_EXPLAIN = {
    'normal': 'traffic stayed within its usual range; nothing unusual detected.',
    'suspicious': 'the peak is clearly above the usual level; worth a closer '
                  'look, though it may still be a legitimate business peak.',
    'anomalous': 'the peak is far above the usual level; treat this as a '
                 'real anomaly and investigate.',
    'insufficient-data': 'not enough data points (or all-zero values) to '
                         'judge reliably.',
    'no-data': 'no usage data could be retrieved at all.',
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
        'Permission denied; the caller lacks a Describe permission - see '
        'references/ram-policies.md.',
    'Forbidden.RAM':
        'Permission denied by RAM; the caller lacks a Describe permission - '
        'see references/ram-policies.md.',
    'NoPermission':
        'Permission denied; the caller lacks a Describe permission - see '
        'references/ram-policies.md.',
    'Throttling.User':
        'API requests were rate limited; wait a moment and retry.',
    'NoUsageData':
        'The API returned no usage data for this window; the domain may be '
        'stopped/offline, unused, or the window may be wrong.',
    'CliError':
        'The aliyun CLI itself failed; verify it is installed and '
        'configured (`aliyun configure`).',
}

# Human-readable series names for the text report
SERIES_LABELS = {
    'traf': 'Traffic (bytes per interval)',
    'bps': 'Bandwidth',
    'usage_bps': 'Bandwidth (usage API)',
    'realtime_bps': 'Real-time bandwidth (last hour)',
    'src_bps': 'Origin (return-to-source) bandwidth',
    'qps': 'Request rate',
}


# ==================== CLI backend ====================
#
# All cloud API access goes through the `aliyun` CLI (subprocess, plugin
# mode, lowercase-hyphenated subcommands) so the evaluation platform can
# intercept every call at the command line. Credentials are resolved by the
# CLI itself via its default chain; this script inherits the current
# environment untouched and passes NO credential parameters.

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


def _run_cli(cmd: List[str]) -> Dict[str, Any]:
    """Run one aliyun CLI command; return parsed JSON response.

    Raises RuntimeError("<Code>: <Message>") on any CLI/API failure so the
    caller can record the error and degrade gracefully.
    """
    full_cmd = list(cmd) + ['--user-agent', _USER_AGENT]
    try:
        proc = subprocess.run(full_cmd, capture_output=True, text=True,
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


def _get_caller_identity() -> Dict[str, Any]:
    return _run_cli(['aliyun', 'sts', 'get-caller-identity'])


def _describe_domain_usage_data(domain: str, start_time: str, end_time: str,
                                field: str, interval: str) -> Dict[str, Any]:
    return _run_cli([
        'aliyun', 'cdn', 'describe-domain-usage-data',
        '--domain-name', domain,
        '--start-time', start_time,
        '--end-time', end_time,
        '--field', field,
        '--interval', interval,
    ])


def _describe_domain_bps_data(domain: str, start_time: str, end_time: str,
                              interval: str) -> Dict[str, Any]:
    return _run_cli([
        'aliyun', 'cdn', 'describe-domain-bps-data',
        '--domain-name', domain,
        '--start-time', start_time,
        '--end-time', end_time,
        '--interval', interval,
    ])


def _describe_domain_qps_data(domain: str, start_time: str, end_time: str,
                              interval: str) -> Dict[str, Any]:
    return _run_cli([
        'aliyun', 'cdn', 'describe-domain-qps-data',
        '--domain-name', domain,
        '--start-time', start_time,
        '--end-time', end_time,
        '--interval', interval,
    ])


def _describe_domain_real_time_bps_data(domain: str) -> Dict[str, Any]:
    return _run_cli([
        'aliyun', 'cdn', 'describe-domain-real-time-bps-data',
        '--domain-name', domain,
    ])


def _describe_domain_src_bps_data(domain: str, start_time: str, end_time: str,
                                  interval: str) -> Dict[str, Any]:
    return _run_cli([
        'aliyun', 'cdn', 'describe-domain-src-bps-data',
        '--domain-name', domain,
        '--start-time', start_time,
        '--end-time', end_time,
        '--interval', interval,
    ])


# ==================== Tolerant response parsing ====================

def _to_float(value: Any) -> Optional[float]:
    """Parse API numeric values: floats, ints, and numeric strings
    (CDN returns values like "1234567.89" as strings)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace(',', '')
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _extract_series(node: Any) -> List[Dict[str, Any]]:
    """Recursively walk an API response and extract a time-series.

    Tolerant by design: no response layout is assumed. The first list of
    dicts found whose items carry at least one time-like key and one
    numeric value-like key is used. Returns [{'time', 'value'}] sorted by
    time; empty list when nothing usable is found.
    """
    candidates: List[List[Dict[str, Any]]] = []

    def walk(item: Any):
        if isinstance(item, dict):
            for v in item.values():
                walk(v)
        elif isinstance(item, list):
            if item and all(isinstance(x, dict) for x in item):
                looks_like_series = False
                for x in item:
                    has_time = any(x.get(k) for k in TIME_KEYS)
                    has_value = any(_to_float(x.get(k)) is not None
                                    for k in VALUE_KEYS)
                    if has_time and has_value:
                        looks_like_series = True
                        break
                if looks_like_series:
                    candidates.append(item)
            for x in item:
                walk(x)

    walk(node)
    if not candidates:
        return []

    points: List[Dict[str, Any]] = []
    for item in candidates[0]:
        time_str = next((str(item.get(k)) for k in TIME_KEYS
                         if item.get(k)), '')
        value = None
        for k in VALUE_KEYS:
            value = _to_float(item.get(k))
            if value is not None:
                break
        if time_str and value is not None:
            points.append({'time': time_str, 'value': value})
    points.sort(key=lambda p: p['time'])
    return points


# ==================== Statistics & anomaly detection ====================

def _analyze_series(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute baseline, peak, threshold and anomalous windows for a series."""
    if not points:
        return {'ok': False, 'points': 0}

    values = [p['value'] for p in points]
    mean = statistics.fmean(values)
    median = statistics.median(values)
    peak_point = max(points, key=lambda p: p['value'])
    threshold = max(mean * PEAK_MEAN_RATIO, median * PEAK_MEDIAN_RATIO)

    anomalous_windows: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []
    for p in points:
        if len(points) >= MIN_POINTS_FOR_BASELINE and p['value'] > threshold:
            current.append(p)
        else:
            if current:
                anomalous_windows.append(_summarize_window(current, mean))
                current = []
    if current:
        anomalous_windows.append(_summarize_window(current, mean))

    peak_mean_ratio = (peak_point['value'] / mean) if mean > 0 else 0.0
    if len(points) < MIN_POINTS_FOR_BASELINE or mean <= 0:
        verdict = 'insufficient-data'
    elif peak_mean_ratio >= ANOMALOUS_RATIO:
        verdict = 'anomalous'
    elif peak_mean_ratio >= SUSPICIOUS_RATIO:
        verdict = 'suspicious'
    else:
        verdict = 'normal'

    return {
        'ok': True,
        'points': len(points),
        'mean': round(mean, 2),
        'median': round(median, 2),
        'peak': peak_point['value'],
        'peak_time': peak_point['time'],
        'peak_mean_ratio': round(peak_mean_ratio, 2),
        'threshold': round(threshold, 2),
        'anomalous_windows': anomalous_windows,
        'verdict': verdict,
    }


def _summarize_window(window: List[Dict[str, Any]], mean: float) -> Dict[str, Any]:
    peak = max(window, key=lambda p: p['value'])
    return {
        'start': window[0]['time'],
        'end': window[-1]['time'],
        'intervals': len(window),
        'peak_value': peak['value'],
        'peak_time': peak['time'],
        'multiple_over_baseline': round(peak['value'] / mean, 2) if mean > 0 else None,
    }


# ==================== Main diagnosis flow ====================

def diagnose(domain: str, days: int, interval: int,
             verbose: bool = True,
             include_raw: bool = True) -> Dict[str, Any]:
    """Run the full read-only diagnosis; degrade-and-continue on every error.

    include_raw=False trims api_raw_responses to per-query summaries
    (--no-raw) to save downstream tokens.
    """

    def log(msg: str = ''):
        if verbose:
            print(msg, flush=True)

    def warn(error: str, query: str):
        print(f"[WARN] {query} failed -> {error} (recorded, continuing)",
              file=sys.stderr)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    start_time = start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    interval_str = str(interval)

    log('=' * 70)
    log('CDN Traffic Anomaly Diagnosis (read-only)')
    log('=' * 70)
    log(f'  Domain    : {domain}')
    log(f'  Window    : {start_time} ~ {end_time} UTC (last {days} days)')
    log(f'  Interval  : {interval_str}s')
    log(f'  Session ID: {_SESSION_ID}')

    api_raw_responses: List[Dict[str, Any]] = []

    def record(query: str, request: Dict[str, Any],
               response: Optional[Dict[str, Any]] = None,
               error: Optional[str] = None):
        api_raw_responses.append({
            'query': query,
            'request': request,
            'response': response or {},
            'error': error,
        })

    # ---------- Step 1: Caller identity (traceability only) ----------
    log()
    log('[Step 1] Verify caller identity (sts get-caller-identity)')
    caller_uid: Optional[str] = None
    try:
        identity = _get_caller_identity()
        caller_uid = str(identity.get('AccountId', '')) or None
        record('GetCallerIdentity', {}, identity)
        log(f'  Caller UID: {caller_uid or "(unavailable)"}')
    except RuntimeError as e:
        record('GetCallerIdentity', {}, error=str(e))
        warn(str(e), 'GetCallerIdentity')
        log('  Caller UID: (identity check failed, continuing)')

    # ---------- Step 2: Usage data series ----------
    log()
    log('[Step 2] Pull usage data series for the time window')

    series_sets: Dict[str, Dict[str, Any]] = {}

    # 2.1 DescribeDomainUsageData (field=traf, primary traffic series).
    # The API only accepts field=bps|traf|acc ('flow' is rejected with
    # InvalidParameterField); traf returns bytes per interval.
    log('  > describe-domain-usage-data (field=traf)')
    try:
        resp = _describe_domain_usage_data(domain, start_time, end_time,
                                           'traf', interval_str)
        record('DescribeDomainUsageData/traf',
               {'domain': domain, 'start': start_time, 'end': end_time,
                'field': 'traf', 'interval': interval_str}, resp)
        series_sets['traf'] = {'response': resp,
                               'points': _extract_series(resp)}
        log(f"    parsed {len(series_sets['traf']['points'])} points")
    except RuntimeError as e:
        record('DescribeDomainUsageData/traf',
               {'domain': domain, 'field': 'traf'}, error=str(e))
        warn(str(e), 'describe-domain-usage-data (traf)')

    # 2.2 DescribeDomainUsageData (field=bps)
    log('  > describe-domain-usage-data (field=bps)')
    try:
        resp = _describe_domain_usage_data(domain, start_time, end_time,
                                           'bps', interval_str)
        record('DescribeDomainUsageData/bps',
               {'domain': domain, 'start': start_time, 'end': end_time,
                'field': 'bps', 'interval': interval_str}, resp)
        series_sets['usage_bps'] = {'response': resp,
                                    'points': _extract_series(resp)}
        log(f"    parsed {len(series_sets['usage_bps']['points'])} points")
    except RuntimeError as e:
        record('DescribeDomainUsageData/bps',
               {'domain': domain, 'field': 'bps'}, error=str(e))
        warn(str(e), 'describe-domain-usage-data (bps)')

    # 2.3 DescribeDomainBpsData (bandwidth trend backup)
    log('  > describe-domain-bps-data')
    try:
        resp = _describe_domain_bps_data(domain, start_time, end_time,
                                         interval_str)
        record('DescribeDomainBpsData',
               {'domain': domain, 'start': start_time, 'end': end_time,
                'interval': interval_str}, resp)
        series_sets['bps'] = {'response': resp,
                              'points': _extract_series(resp)}
        log(f"    parsed {len(series_sets['bps']['points'])} points")
    except RuntimeError as e:
        record('DescribeDomainBpsData', {'domain': domain}, error=str(e))
        warn(str(e), 'describe-domain-bps-data')

    # 2.4 DescribeDomainQpsData (request-rate correlation)
    log('  > describe-domain-qps-data')
    try:
        resp = _describe_domain_qps_data(domain, start_time, end_time,
                                         interval_str)
        record('DescribeDomainQpsData',
               {'domain': domain, 'start': start_time, 'end': end_time,
                'interval': interval_str}, resp)
        series_sets['qps'] = {'response': resp,
                              'points': _extract_series(resp)}
        log(f"    parsed {len(series_sets['qps']['points'])} points")
    except RuntimeError as e:
        record('DescribeDomainQpsData', {'domain': domain}, error=str(e))
        warn(str(e), 'describe-domain-qps-data')

    # 2.5 DescribeDomainRealTimeBpsData (last hour, fine-grained)
    log('  > describe-domain-real-time-bps-data')
    try:
        resp = _describe_domain_real_time_bps_data(domain)
        record('DescribeDomainRealTimeBpsData', {'domain': domain}, resp)
        series_sets['realtime_bps'] = {'response': resp,
                                       'points': _extract_series(resp)}
        log(f"    parsed {len(series_sets['realtime_bps']['points'])} points")
    except RuntimeError as e:
        record('DescribeDomainRealTimeBpsData', {'domain': domain},
               error=str(e))
        warn(str(e), 'describe-domain-real-time-bps-data')

    # 2.6 DescribeDomainSrcBpsData (origin/return-to-source bandwidth series;
    # backs the T6 "origin amplification" scenario; degrade-and-continue)
    log('  > describe-domain-src-bps-data')
    try:
        resp = _describe_domain_src_bps_data(domain, start_time, end_time,
                                             interval_str)
        record('DescribeDomainSrcBpsData',
               {'domain': domain, 'start': start_time, 'end': end_time,
                'interval': interval_str}, resp)
        series_sets['src_bps'] = {'response': resp,
                                  'points': _extract_series(resp)}
        log(f"    parsed {len(series_sets['src_bps']['points'])} points")
    except RuntimeError as e:
        record('DescribeDomainSrcBpsData', {'domain': domain}, error=str(e))
        warn(str(e), 'describe-domain-src-bps-data')

    # ---------- Step 3 & 4: Baseline comparison + anomaly windows ----------
    log()
    log('[Step 3/4] Baseline comparison and anomalous window detection')
    query_errors = {r['query']: r['error'] for r in api_raw_responses
                    if r.get('error')}
    analyses: Dict[str, Any] = {}
    for name, ss in series_sets.items():
        analyses[name] = _analyze_series(ss['points'])
        a = analyses[name]
        if a.get('ok'):
            log(f"  [{name}] points={a['points']} mean={a['mean']} "
                f"median={a['median']} peak={a['peak']} @ {a['peak_time']} "
                f"ratio={a['peak_mean_ratio']} verdict={a['verdict']} "
                f"anomalous_windows={len(a['anomalous_windows'])}")
        elif name in query_errors:
            log(f'  [{name}] query failed: {str(query_errors[name])[:120]}')
        else:
            log(f'  [{name}] query succeeded but returned 0 data points')

    # Primary verdict: prefer traf, then bps/usage_bps, then qps
    primary_verdict = 'no-data'
    primary_series: Optional[str] = None
    for preferred in ('traf', 'bps', 'usage_bps', 'realtime_bps', 'qps'):
        a = analyses.get(preferred)
        if a and a.get('ok'):
            primary_verdict = a['verdict']
            primary_series = preferred
            break

    total_flow = None
    traf_analysis = analyses.get('traf')
    if traf_analysis and traf_analysis.get('ok'):
        total_flow = round(sum(p['value'] for p in series_sets['traf']['points']), 2)

    # T6 evidence: origin bandwidth trend. Distinguish "query failed" from
    # "query succeeded with 0 data points" (Bug-5: the latter is NOT a
    # failure and must not be reported as one).
    src_bps_query_failed = 'DescribeDomainSrcBpsData' in query_errors
    src_bps_available = bool((analyses.get('src_bps') or {}).get('ok'))
    src_bps_rising = False
    if src_bps_available:
        src_bps_rising = analyses['src_bps'].get('verdict') in (
            'suspicious', 'anomalous')

    # ---------- Step 5: Conclusion ----------
    # "All retrieved series are all-zero" = no billable traffic in window
    # (benign state; needs its own guidance, not the generic error text).
    ok_analyses = [a for a in analyses.values() if a.get('ok')]
    all_zero_traffic = bool(ok_analyses) and all(
        (a.get('peak') or 0) == 0 for a in ok_analyses)

    suggestions: List[str] = []
    if primary_verdict == 'anomalous':
        suggestions = [
            'Correlate the anomalous window with business events (promotion, '
            'live stream) before assuming abuse',
            'Review CDN access logs for the anomalous window: top URLs, '
            'Referers and client UAs (hotlink pattern = concentrated Referers '
            'with large-object downloads)',
            'Manually consider hotlink protection (Referer/UA allowlist) and a '
            'bandwidth cap in the CDN console - this skill never applies '
            'configuration changes',
        ]
    elif primary_verdict == 'suspicious':
        suggestions = [
            'Monitor the next 24h; the elevation may be a periodic business '
            'peak',
            'Compare QPS and flow: flow rising without proportional QPS '
            'growth suggests large-object downloads',
        ]
    elif primary_verdict == 'normal':
        suggestions = ['Traffic within baseline range; no action required']
    elif all_zero_traffic:
        suggestions = [
            'This domain had no billable traffic in the window (all usage '
            'values are 0); verify the domain name is correct and check '
            'whether the domain is stopped/offline or simply unused',
        ]
    else:
        suggestions = [
            'No usable usage data was retrieved; verify the domain name, '
            'time window, and RAM permissions (references/ram-policies.md)',
        ]

    # Annotate T6 evidence status so the report is honest about degradation
    if src_bps_query_failed:
        suggestions.append(
            'Origin bandwidth data was unavailable (describe-domain-src-bps-data '
            'failed); cache-hit / origin-amplification (T6) assessment falls '
            'back to MISS-ratio judgment only')
    elif not src_bps_available:
        suggestions.append(
            'Origin bandwidth query succeeded but returned 0 data points; '
            'the origin likely received no traffic in the window (full cache '
            'hit) or origin-side data is unavailable - T6 assessment falls '
            'back to MISS-ratio judgment only')
    elif src_bps_rising:
        suggestions.append(
            'Origin (return-to-source) bandwidth shows a rising/anomalous '
            'trend; combined with a high MISS share this indicates origin '
            'amplification - review cache TTL / cacheability settings')

    ok = any(a.get('ok') for a in analyses.values())

    # Stable error_code contract: '' when data was retrieved; a critical API
    # error code passes through (exit 1); otherwise benign 'NoUsageData'
    # (exit 2).
    error_code = ''
    if not ok:
        error_code = (_critical_error_code(query_errors.values())
                      or 'NoUsageData')

    if not include_raw:
        # Token-saving mode: drop payloads, keep a per-query summary only.
        for entry in api_raw_responses:
            if entry.get('response'):
                entry['response'] = {
                    'trimmed': True,
                    'point_count': len(_extract_series(entry['response'])),
                }

    log()
    log(f'  Overall verdict: {primary_verdict}')

    return {
        'ok': ok,
        'error_code': error_code,
        'domain': domain,
        'uid': caller_uid,
        'session_id': _SESSION_ID,
        'window': {'start': start_time, 'end': end_time, 'days': days,
                   'interval': interval_str},
        'primary_verdict': primary_verdict,
        'primary_series': primary_series,
        'total_flow_bytes_approx': total_flow,
        'src_bps_available': src_bps_available,
        'src_bps_rising': src_bps_rising,
        'analyses': analyses,
        'suggestions': suggestions,
        'query_errors': query_errors,
        'api_raw_responses': api_raw_responses,
    }


# ==================== Output ====================

def _fmt_bytes(b: float) -> str:
    """Human-readable byte quantity."""
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(b) < 1024:
            return f'{b:.1f} {unit}'
        b /= 1024
    return f'{b:.1f} PB'


def _fmt_bps(b: float) -> str:
    """Human-readable bit/s quantity (bandwidth uses decimal prefixes)."""
    for unit in ('bit/s', 'Kbit/s', 'Mbit/s', 'Gbit/s', 'Tbit/s'):
        if abs(b) < 1000:
            return f'{b:.1f} {unit}'
        b /= 1000
    return f'{b:.1f} Pbit/s'


def _fmt_value(series_name: str, v: float) -> str:
    """Human-readable value annotated with the unit of the series."""
    if series_name == 'traf':
        return _fmt_bytes(v)
    if series_name in ('bps', 'usage_bps', 'realtime_bps', 'src_bps'):
        return _fmt_bps(v)
    return f'{v:,.1f} req/s'


def _critical_error_code(errors) -> Optional[str]:
    """Return the first critical API error code found among raw errors."""
    for err in errors:
        code = str(err).split(':', 1)[0].strip()
        if code in CRITICAL_API_ERROR_CODES:
            return code
    return None


def _translate_error(err: str) -> str:
    """Translate a raw CLI/API error into an actionable hint."""
    code = str(err).split(':', 1)[0].strip()
    guidance = ERROR_GUIDANCE.get(code)
    if guidance:
        return f'{code} -> {guidance}'
    return str(err)[:300]


def _print_query_errors(result: Dict[str, Any]):
    qe = result.get('query_errors') or {}
    if not qe:
        return
    print('[Degraded queries ([WARN] details on stderr)]')
    for query, err in qe.items():
        print(f'  {query}: {_translate_error(err)}')


def print_text(result: Dict[str, Any]):
    print()
    print('=' * 70)
    print('CDN Traffic Anomaly Diagnosis Report')
    print('=' * 70)
    print(f"Domain    : {result.get('domain')}")
    win = result.get('window') or {}
    print(f"Window    : {win.get('start')} ~ {win.get('end')} UTC "
          f"(last {win.get('days')} days, interval {win.get('interval')}s)")
    print(f"UID       : {result.get('uid') or '(identity check failed)'}")
    print(f"Session ID: {result.get('session_id')}")
    print('-' * 70)

    # ---- Executive summary (conclusion first, for non-technical users) ----
    verdict = result.get('primary_verdict')
    print('[EXECUTIVE SUMMARY]')
    explain = VERDICT_EXPLAIN.get(verdict or '', '')
    print(f'  Verdict : {verdict}' + (f' - {explain}' if explain else ''))
    primary_name = result.get('primary_series') or ''
    primary = (result.get('analyses') or {}).get(primary_name)
    if primary and primary.get('ok'):
        print(f"  Peak    : {primary['peak_mean_ratio']}x baseline on "
              f"{SERIES_LABELS.get(primary_name, primary_name)} "
              f"(peak {_fmt_value(primary_name, primary['peak'])} vs mean "
              f"{_fmt_value(primary_name, primary['mean'])})")
        windows = primary.get('anomalous_windows') or []
        if windows:
            w = windows[0]
            more = f' (+{len(windows) - 1} more)' if len(windows) > 1 else ''
            print(f"  Window  : {w['start']} ~ {w['end']} "
                  f"({w['multiple_over_baseline']}x baseline){more}")
        else:
            print('  Window  : no anomalous window detected')
    elif not result.get('ok'):
        print('  No usable usage data could be retrieved (see notes below).')
    print('-' * 70)

    if not result.get('ok'):
        code = result.get('error_code') or ''
        print(f'[FAIL] No usable usage data retrieved '
              f"(error_code: {code or 'n/a'})")
        guidance = ERROR_GUIDANCE.get(code)
        if guidance:
            print(f'       What to do: {guidance}')
        else:
            print('       What to do: verify the domain name, time window '
                  'and RAM permissions; see the degraded-query notes below.')
        _print_query_errors(result)
        print('=' * 70)
        return

    for name, a in (result.get('analyses') or {}).items():
        label = SERIES_LABELS.get(name, name)
        if not a.get('ok'):
            print(f'[{label}] query succeeded but returned 0 data points')
            continue
        print(f"[{label}] verdict={a['verdict']} points={a['points']} "
              f"mean={_fmt_value(name, a['mean'])} "
              f"median={_fmt_value(name, a['median'])} "
              f"peak={_fmt_value(name, a['peak'])} @ {a['peak_time']} "
              f"(peak/baseline ratio {a['peak_mean_ratio']}x)")
        for w in a.get('anomalous_windows', []):
            print(f"    Anomalous window: {w['start']} ~ {w['end']} "
                  f"({w['intervals']} intervals, peak "
                  f"{_fmt_value(name, w['peak_value'])} @ {w['peak_time']}, "
                  f"{w['multiple_over_baseline']}x baseline)")

    if result.get('total_flow_bytes_approx') is not None:
        print('-' * 70)
        print('Total traffic in window (approx): '
              f"{_fmt_bytes(result['total_flow_bytes_approx'])} "
              f"({result['total_flow_bytes_approx']:,.0f} bytes)")

    _print_query_errors(result)

    print('-' * 70)
    overall = result.get('primary_verdict')
    overall_explain = VERDICT_EXPLAIN.get(overall or '', '')
    print(f'Overall verdict: {overall}'
          + (f' - {overall_explain}' if overall_explain else ''))
    for i, s in enumerate(result.get('suggestions') or [], start=1):
        print(f'  {i}. {s}')
    print('=' * 70)
    print()


def main():
    parser = argparse.ArgumentParser(
        description='CDN Traffic Anomaly Diagnosis Tool (read-only, '
                    'Describe-class APIs only)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze the last 7 days (default) with hourly granularity
  python3 cdn_traffic_anomaly.py --domain example.com

  # 3-day window with 5-minute granularity
  python3 cdn_traffic_anomaly.py --domain example.com --days 3 --interval 300

  # JSON output
  python3 cdn_traffic_anomaly.py --domain example.com --json
        """,
    )
    parser.add_argument('--domain', required=True,
                        help='CDN accelerated domain name to analyze')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS,
                        help=f'Lookback window in days, default {DEFAULT_DAYS}')
    parser.add_argument('--interval', type=int, default=DEFAULT_INTERVAL,
                        choices=(300, 3600, 86400),
                        help=f'Data interval in seconds, default {DEFAULT_INTERVAL}')
    parser.add_argument('--json', action='store_true',
                        help='JSON output (auto-silences analysis)')
    parser.add_argument('--quiet', action='store_true',
                        help='Text mode: suppress analysis (final report only)')
    parser.add_argument('--no-raw', action='store_true',
                        help='Trim api_raw_responses to per-query summaries '
                             '(saves downstream tokens; recommended with --json)')
    args = parser.parse_args()

    if args.days <= 0:
        print('[FAIL] Error: --days must be a positive integer', file=sys.stderr)
        sys.exit(1)

    if args.days > 3 and args.interval == 300:
        print('[WARN] --days > 3 with --interval 300 requests a very large '
              'number of fine-grained points; the API may throttle or return '
              'coarser granularity. Consider --interval 3600 for long windows.',
              file=sys.stderr)

    # JSON output or --quiet silences analysis
    verbose = not (args.json or args.quiet)

    result = diagnose(args.domain, args.days, args.interval, verbose=verbose,
                      include_raw=not args.no_raw)

    if args.json:
        # Contract: with --json, stdout carries ONLY the JSON document;
        # all diagnostics are emitted on stderr.
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print_text(result)

    # Exit codes: 0 = completed with usable data; 2 = benign no-data
    # (nothing to analyze, not an error); 1 = real error.
    if result.get('ok'):
        sys.exit(0)
    sys.exit(2 if result.get('error_code') == 'NoUsageData' else 1)


if __name__ == '__main__':
    main()
