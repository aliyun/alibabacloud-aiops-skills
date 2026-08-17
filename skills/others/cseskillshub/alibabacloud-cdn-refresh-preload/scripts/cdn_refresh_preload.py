#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDN Refresh/Preload Verification Tool

API used (only one):
    DescribeRefreshTasks (invoked via aliyun CLI)

Workflow:
    1. Fetch all refresh (file/directory) and preload tasks for domain in last 3 days
    2. Check if user-provided URL is covered by existing tasks
       - URL refresh (file): exact match
       - Directory refresh: prefix match
       - Preload: exact match
    3. Verify cache hit status via curl, supports --resolve to bind specific node IP
    4. Output final conclusion: URL, refresh/preload status, curl verification, curl results

Auth: relies entirely on the aliyun CLI default chain (CLI config or
platform-injected environment); this script performs no explicit auth handling.

Usage:
    python3 cdn_refresh_preload.py --url https://example.com/1.jpg
    python3 cdn_refresh_preload.py --url https://example.com/1.jpg --resolve 1.2.3.4
    python3 cdn_refresh_preload.py --url https://example.com/1.jpg --days 7 --json
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

# Per-run session id for platform-level tracing (Observability)
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-cdn-refresh-preload/{_SESSION_ID}"


# Status label mapping
STATUS_MAP = {
    'Complete': 'Complete',
    'Refreshing': 'Refreshing',
    'Pending': 'Pending',
    'Failed': 'Failed',
    'PreloadPending': 'Preload Pending',
    'Preloading': 'Preloading',
}

OBJECT_TYPE_MAP = {
    'file': 'URL Refresh',
    'directory': 'Directory Refresh',
    'preload': 'Preload',
}

DEFAULT_LOOKBACK_DAYS = 3
MAX_PAGES_PER_TYPE = 20  # Prevent infinite pagination


# ==================== CLI backend: DescribeRefreshTasks ====================
#
# DescribeRefreshTasks is invoked through the `aliyun` CLI (subprocess, plugin
# mode) rather than direct HTTP. This keeps ALL cloud API access on one
# interceptable path (the evaluation platform injects mocks at the CLI command
# line). Authentication is resolved by the CLI itself via its default chain;
# this script inherits the current environment untouched.

def _parse_cli_error(stdout: str, stderr: str) -> Tuple[str, str]:
    """Extract (Code, Message) from aliyun CLI error output (JSON or plain text)."""
    for text in (stdout, stderr):
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict) and data.get('Code'):
            return str(data['Code']), str(data.get('Message', ''))
    detail = (stderr or stdout or '').strip()
    return 'CliError', detail[:300]


def _describe_refresh_tasks_via_cli(
    object_type: Optional[str] = None,
    status: Optional[str] = None,
    page_number: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Call CDN DescribeRefreshTasks via aliyun CLI (plugin mode).

    Returns the normalized shape:
    {'total_count', 'page_number', 'page_size', 'tasks': [...]}
    Raises RuntimeError("<Code>: <Message>") on any API/CLI failure so the
    caller can record the error and degrade gracefully.
    """
    cmd = [
        'aliyun', 'cdn', 'describe-refresh-tasks',
        '--page-number', str(page_number),
        '--page-size', str(page_size),
        '--user-agent', _USER_AGENT,
    ]
    if object_type:
        cmd += ['--object-type', object_type]
    if status:
        cmd += ['--status', status]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        raise RuntimeError('CliError: aliyun CLI request timed out after 30s')
    except FileNotFoundError:
        raise RuntimeError('CliError: aliyun CLI not found on PATH')

    if proc.returncode != 0:
        code, message = _parse_cli_error(proc.stdout, proc.stderr)
        raise RuntimeError(f"{code}: {message}")

    try:
        result = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError('CliError: unparseable response from aliyun CLI')
    if isinstance(result, dict) and result.get('Code'):
        raise RuntimeError(f"{result['Code']}: {result.get('Message', '')}")

    tasks = []
    for task in (result.get('Tasks') or {}).get('CDNTask') or []:
        tasks.append({
            'task_id': task.get('TaskId'),
            'object_path': task.get('ObjectPath'),
            'object_type': task.get('ObjectType'),
            'status': task.get('Status'),
            'creation_time': task.get('CreationTime'),
            'completion_time': task.get('CompletionTime'),
        })
    return {
        'total_count': result.get('TotalCount', 0),
        'page_number': result.get('PageNumber', 1),
        'page_size': result.get('PageSize', 20),
        'tasks': tasks,
    }


# ==================== Core class ====================

class RefreshPreloadVerifier:
    """Refresh/preload verifier using only DescribeRefreshTasks API"""

    def __init__(self, verbose: bool = True):
        if shutil.which('aliyun') is None:
            print("Error: aliyun CLI not found. DescribeRefreshTasks requires the aliyun CLI.", file=sys.stderr)
            raise ValueError("aliyun CLI not found. Install it and run 'aliyun configure'.")
        # Whether to print in real-time (disable in JSON output mode to avoid stdout pollution)
        self.verbose = verbose

    def _log(self, msg: str = ''):
        """Print analysis progress in real-time (only when verbose=True)"""
        if self.verbose:
            print(msg, flush=True)

    # ---------- Step 1: Fetch tasks from last N days ----------

    def fetch_recent_tasks(self, domain: Optional[str], lookback_days: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch all refresh (file/directory) and preload tasks for this domain
        within the last lookback_days days.

        If domain is None or empty, fetch all tasks without domain filtering.

        DescribeRefreshTasks returns tasks in descending submission time by
        default, so pagination for a type stops once a task older than the
        cutoff is encountered.

        Returns:
            (filtered_tasks, raw_responses)
            - filtered_tasks: tasks of the same domain within the time window
            - raw_responses: raw response list of every API call, including
              request and response parameters
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        all_tasks: List[Dict[str, Any]] = []
        raw_responses: List[Dict[str, Any]] = []

        self._log()
        self._log('-' * 70)
        self._log(f'[Step 1] Fetching all refresh/preload tasks for domain in last {lookback_days} days')
        self._log('-' * 70)
        self._log(f'  Domain: {domain or "(all domains)"}')
        self._log(f'  Time window: {cutoff.strftime("%Y-%m-%d %H:%M:%S")} UTC ~ now')
        self._log(f'  Query API: DescribeRefreshTasks (by object_type, descending by submission time)')

        for obj_type in ('file', 'directory', 'preload'):
            type_label = OBJECT_TYPE_MAP.get(obj_type, obj_type)
            self._log(f'\n  > Type [{obj_type}/{type_label}]')
            page_number = 1
            page_size = 100
            stop_paginating = False
            kept_for_type = 0
            total_received = 0
            while not stop_paginating and page_number <= MAX_PAGES_PER_TYPE:
                api_response: Dict[str, Any] = {}
                api_error: Optional[str] = None
                try:
                    api_response = _describe_refresh_tasks_via_cli(
                        object_type=obj_type,
                        page_number=page_number,
                        page_size=page_size,
                    )
                except Exception as e:
                    api_error = f"{type(e).__name__}: {e}"

                # Record input/output params for this call
                raw_responses.append({
                    'request': {
                        'object_type': obj_type,
                        'page_number': page_number,
                        'page_size': page_size,
                    },
                    'response': api_response,
                    'error': api_error,
                })

                if api_error:
                    # Degradation trace: always visible on stderr (even in --json/--quiet)
                    print(f"[WARN] DescribeRefreshTasks [{obj_type}] page {page_number} failed -> "
                          f"{api_error} (recorded in api_raw_responses, continuing)", file=sys.stderr)
                    self._log(f'    Page {page_number}: API error -> {api_error} (stop pagination)')
                    break

                tasks = api_response.get('tasks', []) or []
                if not tasks:
                    self._log(f'    Page {page_number}: 0 results (stop pagination)')
                    break

                page_kept = 0
                page_out_of_window = 0
                page_other_domain = 0
                for t in tasks:
                    ct = self._parse_api_time(t.get('creation_time', ''))
                    if ct and ct < cutoff:
                        stop_paginating = True
                        page_out_of_window += 1
                        continue
                    # Only filter by domain if domain is specified
                    if domain and self._extract_domain(t.get('object_path', '')) != domain:
                        page_other_domain += 1
                        continue
                    all_tasks.append(t)
                    page_kept += 1

                total_received += len(tasks)
                kept_for_type += page_kept
                self._log(
                    f'    Page {page_number}: {len(tasks)} results -> '
                    f'domain match +{page_kept} | other domain -{page_other_domain} | out of window -{page_out_of_window}'
                )
                if stop_paginating:
                    self._log(f'    Found task older than window, stop paging [{obj_type}]')

                if len(tasks) < page_size:
                    break
                page_number += 1
            self._log(f'    Subtotal: [{obj_type}] fetched {total_received}, kept {kept_for_type} for this domain in window')

        self._log(f'\n  [OK] Fetch complete: kept {len(all_tasks)} tasks for domain + time window')
        return all_tasks, raw_responses

    # ---------- Step 2: Check if URL is in coverage scope ----------

    def find_matching_tasks(
        self,
        target_url: str,
        tasks: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter tasks covering the target URL from the fetched task set.

        Match rules (scheme is ignored; http/https are treated as the same
        resource):
        - file (URL refresh): matched when host+path is exactly equal
        - directory (directory refresh): matched when the target URL lies
          under this directory
          (target_path == task_path, or target_path starts with task_path/)
        - preload: matched when host+path is exactly equal

        Returns:
            (refresh_matches, preload_matches)
        """
        target_key = self._match_key(target_url)

        self._log()
        self._log('-' * 70)
        self._log('[Step 2] Check if target URL is covered by existing tasks')
        self._log('-' * 70)
        self._log(f'  Target URL  : {target_url}')
        self._log(f'  Match key   : {target_key} (host+path, ignore scheme/port/query)')
        self._log(f'  Match rules : file=exact / directory=prefix / preload=exact')
        self._log(f'  Tasks to compare: {len(tasks)}')

        refresh_matches: List[Dict[str, Any]] = []
        preload_matches: List[Dict[str, Any]] = []
        match_log: List[str] = []

        for task in tasks:
            task_url = task.get('object_path', '')
            obj_type = task.get('object_type', '')
            task_key = self._match_key(task_url)

            covered = False
            coverage_type = ''

            if obj_type == 'file':
                if target_key and target_key == task_key:
                    covered = True
                    coverage_type = 'URL refresh exact match (scheme ignored)'
            elif obj_type == 'directory':
                # Directory refresh: check if target is under this directory
                if target_key and task_key:
                    task_dir = task_key.rstrip('/') + '/'
                    target_norm = target_key.rstrip('/')
                    task_norm = task_key.rstrip('/')
                    if target_norm == task_norm:
                        covered = True
                        coverage_type = 'Directory refresh: target path equals directory (scheme ignored)'
                    elif target_key.startswith(task_dir):
                        covered = True
                        coverage_type = 'Directory refresh: target under this directory (scheme ignored)'
            elif obj_type == 'preload':
                if target_key and target_key == task_key:
                    covered = True
                    coverage_type = 'Preload exact match (scheme ignored)'

            if not covered:
                continue

            enriched = dict(task)
            enriched['coverage_type'] = coverage_type
            enriched['object_type_label'] = OBJECT_TYPE_MAP.get(obj_type, obj_type)
            enriched['status_label'] = STATUS_MAP.get(task.get('status', ''), task.get('status', ''))
            if obj_type == 'preload':
                preload_matches.append(enriched)
            else:
                refresh_matches.append(enriched)
            match_log.append(
                f"    [OK] [{obj_type}] {task.get('status', '')} | {task_url} -> {coverage_type}"
            )

        if match_log:
            for line in match_log:
                self._log(line)
        else:
            self._log('    (No task covers target URL)')

        # Sort: Complete first, then newest submission time
        refresh_matches.sort(key=self._task_sort_key)
        preload_matches.sort(key=self._task_sort_key)
        self._log(f'\n  [OK] Match complete: {len(refresh_matches)} refresh / {len(preload_matches)} preload')
        return refresh_matches, preload_matches

    # ---------- Step 3: curl cache verification ----------

    def curl_check(self, url: str, resolve: Optional[str]) -> Dict[str, Any]:
        self._log()
        self._log('-' * 70)
        self._log('[Step 3] curl actual request to verify cache hit')
        self._log('-' * 70)
        cmd = [
            'curl', '-s', '-i', '-o', '-',
            '--max-time', '10',
            '-A', 'CDN-RefreshPreload-Verify/1.0',
            '-H', 'Accept: */*',
        ]

        resolve_used: Optional[str] = None
        if resolve:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname or ''
            scheme = parsed.scheme or 'https'
            default_port = 443 if scheme == 'https' else 80
            target_port = parsed.port or default_port
            if resolve.count(':') >= 2:
                # Full form host:port:ip
                resolve_used = resolve
            else:
                # IP only, assemble automatically
                resolve_used = f'{host}:{target_port}:{resolve}'
            cmd.extend(['--resolve', resolve_used])

        cmd.append(url)
        curl_command = ' '.join(cmd)

        if resolve_used:
            self._log(f'  Bind IP (--resolve): {resolve_used}')
        self._log(f'  Command: {curl_command}')

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:
            return {'ok': False, 'curl_command': curl_command, 'resolve': resolve_used,
                    'error': 'curl request timeout (>15s)'}
        except FileNotFoundError:
            return {'ok': False, 'curl_command': curl_command, 'resolve': resolve_used,
                    'error': 'curl not installed locally'}
        except Exception as e:
            return {'ok': False, 'curl_command': curl_command, 'resolve': resolve_used,
                    'error': f'curl invocation error: {e}'}

        if proc.returncode != 0:
            self._log(f'  [FAIL] curl failed: exit code {proc.returncode} - {proc.stderr.strip()}')
            return {'ok': False, 'curl_command': curl_command, 'resolve': resolve_used,
                    'error': f'curl exit code {proc.returncode}: {proc.stderr.strip()}'}

        status_code, headers = self._parse_curl_headers(proc.stdout)

        age = headers.get('age', '')
        x_cache = headers.get('x-cache', '')
        x_swlc = headers.get('x-swlc-cachestatus', '')
        last_modified = headers.get('last-modified', '')
        date_h = headers.get('date', '')
        via = headers.get('via', '')
        vary = headers.get('vary', '')

        is_cached: Optional[bool] = None
        cache_source = ''
        if x_swlc:
            up = x_swlc.upper()
            is_cached = up in ('HIT', 'HIT_TCP_MEM_HIT', 'HIT_TCP_DISK_HIT')
            cache_source = f'X-Swlc-CacheStatus: {x_swlc}'
        elif x_cache:
            is_cached = 'HIT' in x_cache.upper()
            cache_source = f'X-Cache: {x_cache}'
        elif age:
            try:
                is_cached = int(age) > 0
                cache_source = f'Age: {age}s'
            except ValueError:
                pass

        # Print key response headers in real-time
        cache_label = 'unknown' if is_cached is None else ('HIT' if is_cached else 'MISS')
        self._log(f'  HTTP status: {status_code}')
        self._log(f'  Cache hit   : {cache_label}'
                  + (f' [source: {cache_source}]' if cache_source else ''))
        if age:
            self._log(f'  Age       : {age}s')
        if x_cache:
            self._log(f'  X-Cache   : {x_cache}')
        if x_swlc:
            self._log(f'  X-Swlc-CacheStatus: {x_swlc}')
        if via:
            self._log(f'  Via       : {via}')
        if vary:
            self._log(f'  Vary      : {vary}')

        return {
            'ok': True,
            'curl_command': curl_command,
            'resolve': resolve_used,
            'status_code': status_code,
            'is_cached': is_cached,
            'cache_source': cache_source,
            'age': age,
            'x_cache': x_cache,
            'x_swlc_cachestatus': x_swlc,
            'last_modified': last_modified,
            'date': date_h,
            'via': via,
            'vary': vary,
        }

    # ---------- Utility functions ----------

    def _task_sort_key(self, t: Dict[str, Any]):
        priority = {'Complete': 0, 'Refreshing': 1, 'Preloading': 1,
                    'Pending': 2, 'PreloadPending': 2, 'Failed': 3}
        ct = self._parse_api_time(t.get('creation_time', ''))
        ts = ct.timestamp() if ct else 0
        return (priority.get(t.get('status', ''), 99), -ts)

    @staticmethod
    def _normalize_url(u: str) -> str:
        if not u:
            return ''
        p = urllib.parse.urlparse(u)
        return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, '', '', ''))

    @staticmethod
    def _match_key(u: str) -> str:
        """
        Build the matching key: host (lowercase) + path.
        Scheme (http/https treated as the same resource), port, query and
        fragment are ignored.
        """
        if not u:
            return ''
        p = urllib.parse.urlparse(u)
        host = (p.hostname or '').lower()
        path = p.path or ''
        if not path:
            path = '/'
        return f"{host}{path}"

    @staticmethod
    def _extract_domain(u: str) -> str:
        if not u:
            return ''
        try:
            return urllib.parse.urlparse(u).hostname or ''
        except Exception:
            return ''

    @staticmethod
    def _parse_api_time(s: str) -> Optional[datetime]:
        if not s:
            return None
        for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    @staticmethod
    def extract_url_from_tasks(tasks: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract the most recent URL from task records.
        
        Returns the URL from the most recently created task, or None if no tasks.
        """
        if not tasks:
            return None
        
        # Sort by creation time descending
        def _parse_time(t: Dict[str, Any]) -> float:
            s = t.get('creation_time', '')
            for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S'):
                try:
                    return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()
                except (ValueError, TypeError):
                    continue
            return 0
        
        sorted_tasks = sorted(tasks, key=_parse_time, reverse=True)
        
        # Return the URL from the most recent task
        for task in sorted_tasks:
            url = task.get('object_path', '')
            if url:
                return url
        
        return None

    @staticmethod
    def _parse_curl_headers(stdout: str) -> Tuple[int, Dict[str, str]]:
        if not stdout:
            return 0, {}
        blocks = re.split(r'\r?\n\r?\n', stdout)
        header_blocks = [b for b in blocks if b.startswith('HTTP/')]
        if not header_blocks:
            return 0, {}
        last_block = header_blocks[-1]
        lines = re.split(r'\r?\n', last_block)
        status_code = 0
        headers: Dict[str, str] = {}
        if lines:
            m = re.match(r'HTTP/[\d.]+\s+(\d+)', lines[0])
            if m:
                status_code = int(m.group(1))
        for line in lines[1:]:
            if ':' in line:
                k, _, v = line.partition(':')
                headers[k.strip().lower()] = v.strip()
        return status_code, headers


# ==================== Main verification flow ====================

def verify(
    verifier: RefreshPreloadVerifier,
    url: Optional[str],
    resolve: Optional[str],
    lookback_days: int,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify CDN refresh/preload status.
    
    Supports three modes:
    1. URL provided: use it directly (existing behavior)
    2. Domain provided (no URL): query tasks for domain, extract most recent URL
    3. Neither provided: query all tasks, extract most recent URL
    """
    auto_extracted_url = False
    
    # Mode 2 & 3: No URL provided, need to extract from task records
    if not url:
        verifier._log()
        verifier._log('=' * 70)
        verifier._log('CDN Refresh/Preload Verification - Auto-extract URL from task records')
        verifier._log('=' * 70)
        verifier._log(f'  Domain  : {domain or "(all domains)"}')
        verifier._log(f'  Lookback: last {lookback_days} days')
        verifier._log(f'  Mode    : {"domain-only" if domain else "no-params"} (auto-extract URL)')
        
        # Fetch tasks
        tasks, raw_responses = verifier.fetch_recent_tasks(domain, lookback_days=lookback_days)
        
        if not tasks:
            return {
                'ok': False,
                'url': None,
                'domain': domain,
                'error': f'No refresh/preload tasks found in last {lookback_days} days'
                        + (f' for domain {domain}' if domain else ''),
                'api_raw_responses': raw_responses,
            }
        
        # Extract most recent URL
        url = verifier.extract_url_from_tasks(tasks)
        if not url:
            return {
                'ok': False,
                'url': None,
                'domain': domain,
                'error': 'Could not extract URL from task records (no valid URLs found)',
                'all_tasks': tasks,
                'api_raw_responses': raw_responses,
            }
        
        auto_extracted_url = True
        verifier._log(f'\n  [OK] Auto-extracted URL from task records: {url}')
        verifier._log(f'       (from {len(tasks)} tasks in last {lookback_days} days)')
    
    # Now we have a URL, proceed with normal verification
    parsed = urllib.parse.urlparse(url)
    url_domain = parsed.hostname or ''
    if not url_domain:
        return {'ok': False, 'url': url, 'error': 'Invalid URL format, cannot extract domain'}
    
    # Use the provided domain or the extracted domain
    effective_domain = domain or url_domain
    
    verifier._log()
    verifier._log('=' * 70)
    verifier._log('CDN Refresh/Preload Verification - Analysis')
    verifier._log('=' * 70)
    verifier._log(f'  URL     : {url}')
    verifier._log(f'  Domain  : {effective_domain}')
    verifier._log(f'  Lookback: last {lookback_days} days')
    if auto_extracted_url:
        verifier._log(f'  Note    : URL auto-extracted from task records')
    if resolve:
        verifier._log(f'  Bind IP : {resolve}')

    # 1. Fetch tasks from last N days (if not already fetched)
    if not auto_extracted_url:
        tasks, raw_responses = verifier.fetch_recent_tasks(effective_domain, lookback_days=lookback_days)
    # else: tasks and raw_responses already fetched above

    # 2. Check coverage scope
    refresh_matches, preload_matches = verifier.find_matching_tasks(url, tasks)

    # 3. Select best match (Complete first, newest first)
    best_refresh = next((t for t in refresh_matches if t.get('status') == 'Complete'),
                       refresh_matches[0] if refresh_matches else None)
    best_preload = next((t for t in preload_matches if t.get('status') == 'Complete'),
                       preload_matches[0] if preload_matches else None)

    has_match = bool(refresh_matches or preload_matches)
    has_complete_refresh = bool(best_refresh and best_refresh.get('status') == 'Complete')
    has_complete_preload = bool(best_preload and best_preload.get('status') == 'Complete')

    # 4. Whether curl verification is needed
    #    - No matching tasks -> skip curl
    #    - Preload exists but not Complete -> skip curl
    #    - Only refresh Complete -> curl verify refresh
    #    - Preload Complete -> curl verify preload
    if preload_matches and not has_complete_preload:
        # Preload exists but not succeeded, conclude directly
        should_curl = False
    else:
        should_curl = has_complete_refresh or has_complete_preload
    curl: Optional[Dict[str, Any]] = None
    if should_curl:
        curl = verifier.curl_check(url, resolve)

    # 5. Determine curl verification conclusions
    if not has_match:
        verify_conclusion = (
            f"No refresh/preload task covering this URL in last {lookback_days} days, "
            f"curl not triggered (no task to verify)"
        )
    elif not should_curl:
        # Preload task exists but not succeeded -> conclude directly from preload task status
        if preload_matches:
            t = best_preload or preload_matches[0]
            status = t.get('status', '')
            status_label = t.get('status_label', status)
            if status == 'Failed':
                verify_conclusion = (
                    f"Preload task failed (Status=Failed), not effective. "
                    f"Curl skipped (preload not succeeded)"
                )
            else:
                verify_conclusion = (
                    f"Preload task not complete (status: {status_label}). "
                    f"Curl skipped (wait for completion)"
                )
        else:
            # Non-preload: refresh all not succeeded
            non_complete = [t for t in refresh_matches if t.get('status') != 'Complete']
            if non_complete:
                t = non_complete[0]
                status = t.get('status', '')
                type_label = t.get('object_type_label', '')
                status_label = t.get('status_label', status)
                if status == 'Failed':
                    verify_conclusion = (
                        f"{type_label} task failed (Status=Failed), not effective. "
                        f"Curl skipped (task not succeeded)"
                    )
                else:
                    verify_conclusion = (
                        f"{type_label} task not complete (status: {status_label}). "
                        f"Curl skipped (wait for completion)"
                    )
            else:
                verify_conclusion = "Abnormal status, please investigate manually"
    elif curl and not curl.get('ok'):
        verify_conclusion = f"curl test failed: {curl.get('error', '')}"
    else:
        is_cached = curl.get('is_cached') if curl else None
        if has_complete_preload and is_cached is True:
            verify_conclusion = f"Preload effective: cache HIT ({curl.get('cache_source', '')})"
        elif has_complete_preload and is_cached is False:
            verify_conclusion = (
                f"Preload not effective: cache MISS ({curl.get('cache_source') or 'no cache header'}), "
                f"Check origin reachable, URL correct, or retry later"
            )
        elif has_complete_refresh and is_cached is False:
            verify_conclusion = (
                f"Refresh effective: cache MISS ({curl.get('cache_source') or 'no cache header'}), "
                f"CDN cleared old cache"
            )
        elif has_complete_refresh and is_cached is True:
            verify_conclusion = (
                f"Refresh may not be effective: cache HIT ({curl.get('cache_source', '')}), "
                f"Node has old cache (possible sync delay, retry or try different IP)"
            )
        else:
            verify_conclusion = "curl verification result inconclusive, please investigate manually"

    # 6. Generate troubleshooting suggestions
    suggestions: List[str] = []
    if preload_matches and not has_complete_preload:
        best_p = best_preload or preload_matches[0]
        if best_p.get('status') == 'Failed':
            suggestions = [
                "Check domain HTTPS cert config, check expiration (curl exit code 60 = cert issue)",
                "Confirm origin responds to GET for this URL",
                "Check if origin restricts CDN back-to-origin IP (firewall/whitelist)",
                "After cert/origin fix, resubmit preload task",
            ]
        else:
            suggestions = [
                "Wait for preload task to complete and recheck",
                "If pending long, check CDN console or contact support",
            ]
    elif curl and not curl.get('ok'):
        err = curl.get('error', '')
        if '60' in err:
            suggestions = [
                "curl exit code 60 = SSL cert verification failure",
                "Check domain HTTPS cert config in CDN console",
                "Confirm cert not expired or domain matches cert",
            ]

    # 6.1 Vary header diagnosis (origin multi-variant detection)
    vary_diagnosis = None
    if curl and curl.get('ok'):
        vary_value = curl.get('vary', '')
        if vary_value:
            parsed_url = urllib.parse.urlparse(url)
            accel_domain = parsed_url.hostname or ''

            vary_diagnosis = {
                'has_vary': True,
                'vary_value': vary_value,
                'explanation': (
                    f"Origin response has Vary header (Vary: {vary_value}), origin may return different content by request headers."
                    f" This may reduce CDN cache hit rate as different Vary values are separate cache objects."
                ),
                'suggestion': (
                    f"Confirm whether the origin really serves multiple variants: use cdn_probe.py "
                    f"with and without the request header corresponding to '{vary_value}' "
                    f"(e.g. Accept-Encoding / Accept) to request this URL on {accel_domain}, "
                    f"then compare the response body and Cache-Control for differences.\n"
                    f"  Example: python3 scripts/cdn_probe.py 'curl -ksI \"{url}\"'"
                ),
            }
            # Auto-add to suggested troubleshooting directions
            suggestions.append(
                f"Detected Vary header ({vary_value}), may affect cache hit rate. "
                f"Manually probe with different request headers to confirm multi-variant behavior."
            )

    return {
        'ok': True,
        'url': url,
        'domain': domain,
        'lookback_days': lookback_days,
        'tasks_total_in_range': len(tasks),
        'all_tasks': tasks,
        'refresh_matches': refresh_matches,
        'preload_matches': preload_matches,
        'best_refresh': best_refresh,
        'best_preload': best_preload,
        'curl_skipped': not should_curl,
        'curl': curl,
        'verify_conclusion': verify_conclusion,
        'suggestions': suggestions,
        'vary_diagnosis': vary_diagnosis,
        'api_raw_responses': raw_responses,
    }


# ==================== Output ====================

def _fmt_task_line(t: Dict[str, Any]) -> str:
    return (f"{t.get('status_label', '')} ({t.get('status', '')})"
            f" | Submitted: {t.get('creation_time', '-')}"
            f" | Completed: {t.get('completion_time', '-')}")


def print_text(result: Dict[str, Any]):
    if not result.get('ok'):
        print(f"\n[FAIL] Error: {result.get('error', '')}\n")
        return

    url = result['url']
    look = result['lookback_days']
    refresh_matches = result['refresh_matches']
    preload_matches = result['preload_matches']
    best_refresh = result['best_refresh']
    best_preload = result['best_preload']
    curl = result['curl']
    suggestions = result.get('suggestions') or []

    print()
    print('=' * 70)
    print("CDN Refresh/Preload Verification")
    print('=' * 70)
    print(f"URL: {url}")
    print(f"Lookback: last {look} days")
    print(f"Matched tasks: {len(refresh_matches)} refresh / {len(preload_matches)} preload")
    print('-' * 70)

    # Refresh
    if best_refresh:
        ok = best_refresh.get('status') == 'Complete'
        icon = '[OK]' if ok else '[WARN]'
        print(f"{icon} Refresh {_fmt_task_line(best_refresh)}")
        print(f"   Match type: {best_refresh.get('coverage_type', '')}")
        print(f"   Task URL: {best_refresh.get('object_path', '')}")
        if len(refresh_matches) > 1:
            print(f"   ({len(refresh_matches) - 1} more refresh task(s) also cover this URL)")
    else:
        print(f"[MISS] Refresh: No task covering this URL in last {look} days")

    # Preload
    if best_preload:
        ok = best_preload.get('status') == 'Complete'
        icon = '[OK]' if ok else '[WARN]'
        print(f"{icon} Preload {_fmt_task_line(best_preload)}")
        print(f"   Match type: {best_preload.get('coverage_type', '')}")
        print(f"   Task URL: {best_preload.get('object_path', '')}")
        if len(preload_matches) > 1:
            print(f"   ({len(preload_matches) - 1} more preload task(s) also cover this URL)")
    else:
        print(f"[MISS] Preload: No task covering this URL in last {look} days")

    print('-' * 70)
    print(f"Verification: {result.get('verify_conclusion', '')}")

    # Only output curl details when curl was actually performed
    if not result.get('curl_skipped') and curl is not None:
        print()
        print("curl test result:")
        if curl.get('resolve'):
            print(f"  Bind IP (--resolve): {curl.get('resolve')}")
        print(f"  curl command: {curl.get('curl_command', '')}")
        if curl.get('ok'):
            print(f"  HTTP status: {curl.get('status_code', 0)}")
            is_cached = curl.get('is_cached')
            if is_cached is None:
                cache_label = 'unknown'
            elif is_cached:
                cache_label = 'yes (HIT)'
            else:
                cache_label = 'no (MISS)'
            print(f"  Cache hit: {cache_label}")
            if curl.get('cache_source'):
                print(f"  Cache source: {curl.get('cache_source')}")
            if curl.get('age'):
                print(f"  Age: {curl.get('age')}s")
            if curl.get('x_cache'):
                print(f"  X-Cache: {curl.get('x_cache')}")
            if curl.get('x_swlc_cachestatus'):
                print(f"  X-Swlc-CacheStatus: {curl.get('x_swlc_cachestatus')}")
            if curl.get('last_modified'):
                print(f"  Last-Modified: {curl.get('last_modified')}")
            if curl.get('date'):
                print(f"  Date: {curl.get('date')}")
            if curl.get('via'):
                print(f"  Via: {curl.get('via')}")
            if curl.get('vary'):
                print(f"  Vary: {curl.get('vary')}")
        else:
            print(f"  [FAIL] {curl.get('error', '')}")

    # Suggested troubleshooting directions
    if suggestions:
        print('-' * 70)
        print("Suggested troubleshooting directions:")
        for i, s in enumerate(suggestions, start=1):
            print(f"  {i}. {s}")

    # Vary header diagnosis
    vary_diag = result.get('vary_diagnosis')
    if vary_diag and vary_diag.get('has_vary'):
        print()
        print('-' * 70)
        print("Origin multi-variant detection (Vary header)")
        print('-' * 70)
        print(f"  Detected Vary header: {vary_diag['vary_value']}")
        print()
        print(f"  Explanation:")
        print(f"  {vary_diag['explanation']}")
        print()
        print(f"  Suggestion:")
        print(f"  {vary_diag['suggestion']}")

    # DescribeRefreshTasks info query (placed after suggested troubleshooting)
    _print_all_tasks_section(result)
    _print_api_raw_section(result)

    print('=' * 70)
    print()


def _print_all_tasks_section(result: Dict[str, Any]):
    """Output all refresh/preload tasks for domain in lookback window."""
    domain = result.get('domain', '')
    look = result.get('lookback_days', 0)
    all_tasks: List[Dict[str, Any]] = result.get('all_tasks') or []

    # Group by type
    grouped: Dict[str, List[Dict[str, Any]]] = {'file': [], 'directory': [], 'preload': []}
    for t in all_tasks:
        ot = t.get('object_type', '')
        if ot in grouped:
            grouped[ot].append(t)

    # Sort by submission time descending
    def _ts(t: Dict[str, Any]):
        s = t.get('creation_time', '')
        for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(s, fmt).timestamp()
            except (ValueError, TypeError):
                continue
        return 0
    for k in grouped:
        grouped[k].sort(key=_ts, reverse=True)

    print('-' * 70)
    print(f"Info query: All refresh/preload for ({domain}) last {look} days ({len(all_tasks)} total)")
    MAX_DISPLAY = 30
    for ot in ('file', 'directory', 'preload'):
        label = OBJECT_TYPE_MAP.get(ot, ot)
        items = grouped[ot]
        print(f"\n  [{label}({ot})] {len(items)} total")
        if not items:
            print("    (none)")
            continue
        for i, t in enumerate(items[:MAX_DISPLAY], start=1):
            status = t.get('status', '')
            status_label = STATUS_MAP.get(status, status)
            ct = t.get('creation_time', '-')
            ft = t.get('completion_time', '-') or '-'
            path = t.get('object_path', '')
            print(f"    [{i}] {status_label}({status}) | Submitted: {ct} | Completed: {ft}")
            print(f"        URL: {path}")
        if len(items) > MAX_DISPLAY:
            print(f"    ... Showing first {MAX_DISPLAY}, {len(items) - MAX_DISPLAY} more not listed.")


def _print_api_raw_section(result: Dict[str, Any]):
    """Output raw DescribeRefreshTasks API call records."""
    raw: List[Dict[str, Any]] = result.get('api_raw_responses') or []
    print('-' * 70)
    print(f"DescribeRefreshTasks raw response ({len(raw)} calls):")
    if not raw:
        print("  (no call records)")
        return
    for idx, item in enumerate(raw, start=1):
        req = item.get('request', {})
        resp = item.get('response', {}) or {}
        err = item.get('error')
        print(f"\n  [#{idx}] Input: object_type={req.get('object_type')}, "
              f"page_number={req.get('page_number')}, page_size={req.get('page_size')}")
        if err:
            print(f"        Call error: {err}")
            continue
        try:
            resp_str = json.dumps(resp, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            resp_str = f"<Cannot serialize response body: {e}>"
        # Indent each line by 8 spaces
        for line in resp_str.splitlines():
            print(f"        {line}")


def main():
    parser = argparse.ArgumentParser(
        description="CDN Refresh/Preload Verification Tool (DescribeRefreshTasks only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify URL refresh/preload status in the last 3 days
  python3 cdn_refresh_preload.py --url https://example.com/1.jpg

  # Domain-only mode: query task records and auto-extract most recent URL
  python3 cdn_refresh_preload.py --domain example.com

  # No-params mode: query all task records and auto-extract most recent URL
  python3 cdn_refresh_preload.py

  # Bind CDN node IP for testing (IP only auto-binds to domain:443/80)
  python3 cdn_refresh_preload.py --url https://example.com/1.jpg --resolve 1.2.3.4

  # Full host:port:ip format (native curl --resolve format)
  python3 cdn_refresh_preload.py --url https://example.com/1.jpg --resolve example.com:443:1.2.3.4

  # Extend lookback window to 7 days
  python3 cdn_refresh_preload.py --url https://example.com/1.jpg --days 7

  # JSON output
  python3 cdn_refresh_preload.py --url https://example.com/1.jpg --json
        """,
    )
    parser.add_argument('--url', required=False, default=None,
                        help='Full URL to verify, e.g. https://example.com/1.jpg (optional)')
    parser.add_argument('--domain', required=False, default=None,
                        help='CDN domain name. If provided without --url, queries task records '
                             'for this domain and auto-extracts the most recent URL')
    parser.add_argument('--resolve', default=None,
                        help='curl bind IP. IP only (e.g. 1.2.3.4) auto-binds; '
                             'also supports full host:port:ip')
    parser.add_argument('--days', type=int, default=DEFAULT_LOOKBACK_DAYS,
                        help=f'Lookback window days, default {DEFAULT_LOOKBACK_DAYS}')
    parser.add_argument('--uid', type=str, default=None,
                        help='Target customer UID (informational only; authentication '
                             'is resolved by the aliyun CLI default chain)')
    parser.add_argument('--json', action='store_true', help='JSON output (auto-silences analysis)')
    parser.add_argument('--quiet', action='store_true',
                        help='Text mode: suppress analysis (final report only)')
    args = parser.parse_args()

    if args.days <= 0:
        print("[FAIL] Error: --days must be positive integer", file=sys.stderr)
        sys.exit(1)

    # JSON output or --quiet silences analysis
    verbose = not (args.json or args.quiet)

    if args.uid:
        print(f"Target UID (informational): {args.uid}", file=sys.stderr)

    try:
        verifier = RefreshPreloadVerifier(verbose=verbose)
    except ValueError as e:
        print(f"Environment error: {e}", file=sys.stderr)
        sys.exit(1)

    result = verify(verifier, args.url, args.resolve, args.days, domain=args.domain)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print_text(result)

    sys.exit(0 if result.get('ok') else 1)


if __name__ == '__main__':
    main()
