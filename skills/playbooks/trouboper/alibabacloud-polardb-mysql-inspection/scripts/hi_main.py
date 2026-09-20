"""PolarDB MySQL Health Inspection - CLI entry point"""
import subprocess
import json
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import hi_config as config
from hi_config import call_cli
from hi_collectors import (find_region, get_cluster_info, get_version_info,
    get_resource_usage, get_disk_usage_trend, get_proxy_performance,
    get_space_top20, get_slow_logs,
    get_max_connections_from_params, get_alert_history, get_auto_increment_usage,
    get_session_info)
from hi_orchestrator import discover_all_clusters, inspect_single_cluster, generate_report
from hi_renderer_summary import render_summary_html
from hi_aggregator import aggregate_summaries


_REQUIRED_PLUGINS = ('polardb', 'das', 'cms')


def _ensure_plugins():
    """Pre-check that all required aliyun CLI plugins are installed.

    Silently passes when every plugin is present; auto-installs missing ones
    and exits on failure so later API calls never hit cryptic 'Tip' errors.
    """
    try:
        result = subprocess.run(
            ['aliyun', 'plugin', 'list'],
            capture_output=True, text=True, timeout=15,
        )
        installed_lines = result.stdout.strip().splitlines()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # aliyun CLI reachability is already verified before this call,
        # so this branch should never trigger; bail out defensively.
        print('\u274c Failed to list aliyun CLI plugins')
        sys.exit(1)

    # Parse plugin names from output lines like "aliyun-cli-cms  0.9.0  ..."
    # The actual plugin name used by `aliyun plugin install` is the short form
    # (e.g. "polardb"), while `plugin list` shows "aliyun-cli-polardb".
    installed = set()
    for line in installed_lines:
        parts = line.split()
        if not parts:
            continue
        raw = parts[0].strip().lower()
        # Strip the common "aliyun-cli-" prefix to get the short name
        short = raw.removeprefix('aliyun-cli-') if raw.startswith('aliyun-cli-') else raw
        installed.add(short)
        installed.add(raw)  # keep full name for robustness

    for name in _REQUIRED_PLUGINS:
        if name in installed:
            continue
        print(f'\U0001f50c Installing required plugin: {name}...', end=' ', flush=True)
        try:
            ret = subprocess.run(
                ['aliyun', 'plugin', 'install', '--name', name],
                capture_output=True, text=True, timeout=60,
            )
            if ret.returncode != 0:
                err_detail = (ret.stderr or ret.stdout or '').strip()
                print(f'\u274c Failed to install required plugin \'{name}\'.'
                      f' Please run manually: aliyun plugin install {name}')
                if err_detail:
                    print(f'   Detail: {err_detail}')
                sys.exit(1)
            print('\u2705')
        except subprocess.TimeoutExpired:
            print(f'\u274c Timed out installing plugin \'{name}\'.'
                  f' Please run manually: aliyun plugin install {name}')
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog='health-inspect',
        description='PolarDB MySQL instance health inspection tool (single / multi / full-scan)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s pc-bp1715bzkcrateo69
  %(prog)s pc-bp1715bzkcrateo69 pc-bp2xxxxx pc-bp3xxxxx
  %(prog)s --all
  %(prog)s --all --region cn-hangzhou
  %(prog)s pc-bp1715bzkcrateo69 -p myprofile -o ./report.html
        """
    )
    parser.add_argument('cluster_ids', metavar='CLUSTER_ID', nargs='*', help='PolarDB cluster ID(s)')
    parser.add_argument('--all', action='store_true', help='Inspect all PolarDB MySQL instances under current account')
    parser.add_argument('-r', '--region', help='Instance region')
    parser.add_argument('-p', '--profile', help='aliyun CLI profile name')
    parser.add_argument('-o', '--output', help='Report output file path (single) or directory (multi)')
    parser.add_argument('-d', '--days', type=int, default=7, help='Inspection time range in days (default: 7)')
    parser.add_argument('--item', action='append', choices=config.ALL_ITEMS,
                        help='Inspection items (repeatable). If omitted, all items are inspected. Options: resource, space, slowlog, session, alert')
    parser.add_argument('-f', '--format', choices=['markdown', 'html', 'text'], default='html', help='Report format: html (default), markdown, text')
    args = parser.parse_args()

    if not args.all and not args.cluster_ids:
        parser.error('Provide at least one CLUSTER_ID or use --all to inspect all instances')

    config._CLI_PROFILE = args.profile
    config._INSPECT_DAYS = args.days
    config._INSPECT_ITEMS = set(args.item) if args.item else set(config.ALL_ITEMS)

    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('❌ aliyun CLI not found. Please install: https://help.aliyun.com/zh/cli/')
        sys.exit(1)

    _ensure_plugins()

    # Determine clusters to inspect
    if args.all:
        print('🔍 Discovering all PolarDB MySQL instances...')
        clusters = discover_all_clusters(region=args.region)
        if not clusters:
            print('❌ No PolarDB MySQL instances found')
            sys.exit(1)
        print(f'   ✅ Found {len(clusters)} instance(s)')
        for c in clusters:
            print(f'      - {c["cluster_id"]} ({c["region"]}) {c.get("description", "")}')
    else:
        clusters = [{'cluster_id': cid, 'region': args.region} for cid in args.cluster_ids]

    # Single instance → single file output (no directory wrapper)
    if len(clusters) == 1:
        cluster_id = clusters[0]['cluster_id']
        region = clusters[0].get('region')

        print('┌' + '─' * 50 + '┐')
        print('│  PolarDB MySQL Instance Health Inspection    │')
        print('└' + '─' * 50 + '┘')
        print(f'  Cluster: {cluster_id}')
        if config._CLI_PROFILE:
            print(f'  Profile: {config._CLI_PROFILE}')

        if not region:
            region = find_region(cluster_id)
            if not region:
                print(f'❌ Cluster {cluster_id} not found')
                sys.exit(1)
        print(f'  Region: {region}')
        print()

        print('📋 Basic info...', end=' ', flush=True)
        cluster_info = get_cluster_info(cluster_id, region)
        if not cluster_info:
            print('❌')
            sys.exit(1)
        print('✅')

        print('🏷️  Version info...', end=' ', flush=True)
        version_info = get_version_info(cluster_id, region)
        print('✅' if version_info else '⚠️')

        nodes = cluster_info.get('DBNodes', [])
        if isinstance(nodes, dict):
            nodes = nodes.get('DBNode', [])

        param_max_conn = get_max_connections_from_params(cluster_id, region)

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=config._INSPECT_DAYS)
        start_time = start.strftime('%Y-%m-%dT%H:%MZ')
        end_time = now.strftime('%Y-%m-%dT%H:%MZ')

        print(f'📊 Collecting data in parallel (cluster + {len(nodes)} nodes)...', flush=True)

        resource_usage = None
        proxy_perf = None
        space_data = None
        slow_logs = None
        auto_inc_data = None
        session_info = None
        alert_history = None

        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {}
            if 'resource' in config._INSPECT_ITEMS:
                futures['resource'] = pool.submit(get_resource_usage, cluster_id, region, nodes, start_time, end_time)
                futures['proxy'] = pool.submit(get_proxy_performance, cluster_id, region, nodes, start_time, end_time)
            if 'space' in config._INSPECT_ITEMS:
                futures['space'] = pool.submit(get_space_top20, cluster_id)
                futures['auto_inc'] = pool.submit(get_auto_increment_usage, cluster_id)
            if 'slowlog' in config._INSPECT_ITEMS:
                futures['slow'] = pool.submit(get_slow_logs, cluster_id, region)
            if 'session' in config._INSPECT_ITEMS:
                futures['session'] = pool.submit(get_session_info, cluster_id, nodes)
            if 'alert' in config._INSPECT_ITEMS:
                futures['alert'] = pool.submit(get_alert_history, cluster_id, start_time, end_time)

            # When space is selected without resource, collect disk trend separately
            if 'space' in config._INSPECT_ITEMS and 'resource' not in config._INSPECT_ITEMS:
                futures['disk_trend'] = pool.submit(get_disk_usage_trend,
                                                    cluster_id, region, start_time, end_time)

            if 'resource' in futures:
                resource_usage = futures['resource'].result()
            if 'proxy' in futures:
                proxy_perf = futures['proxy'].result()
            if 'space' in futures:
                space_data = futures['space'].result()
            if 'auto_inc' in futures:
                auto_inc_data = futures['auto_inc'].result()
            if 'disk_trend' in futures:
                disk_ts = futures['disk_trend'].result()
                if disk_ts:
                    resource_usage = {'cluster': {}, 'nodes': {}, 'cluster_ts': {}, 'node_ts': {}}
                    resource_usage['cluster_ts']['disk'] = disk_ts.get('disk', [])
                    resource_usage['cluster_ts']['disk_detail'] = disk_ts.get('disk_detail', {})
            if 'slow' in futures:
                slow_logs = futures['slow'].result()
            if 'session' in futures:
                session_info = futures['session'].result()
            if 'alert' in futures:
                alert_history = futures['alert'].result()

        items_count = len(slow_logs.get('Items', {}).get('SQLSlowLog', [])) if slow_logs else 0
        print(f'  ✅ Data collection complete (slow logs: {items_count})')

        das_config = None
        if 'essd' in cluster_info.get('StorageType', '').lower():
            das_config = call_cli('polardb', 'describe-das-config', region,
                                  **{'db-cluster-id': cluster_id})

        fmt = args.format
        report, data = generate_report(cluster_id, region, cluster_info, version_info,
                                       resource_usage, nodes, space_data, slow_logs,
                                       fmt=fmt, param_max_conn=param_max_conn,
                                       auto_inc_data=auto_inc_data, session_info=session_info,
                                       alert_history=alert_history, das_config=das_config,
                                       proxy_perf=proxy_perf,
                                       items=config._INSPECT_ITEMS)
        print(report)

        ext = '.html' if fmt == 'html' else '.md' if fmt == 'markdown' else '.txt'
        if args.output:
            output_path = os.path.abspath(args.output)
            if not output_path.endswith(ext):
                output_path += ext
        else:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            output_path = os.path.join(os.path.expanduser('~/Downloads'),
                                       f'{cluster_id}_health_report_{timestamp}{ext}')
        output_dir_path = os.path.dirname(output_path)
        if output_dir_path and not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'\n📄 Report saved: {output_path}')
        return

    # Batch mode: multiple clusters → directory with index.html
    fmt = 'html' if len(clusters) > 1 else args.format
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    if args.output:
        output_dir = args.output
    else:
        base_dir = os.path.expanduser('~/Downloads')
        output_dir = os.path.join(base_dir, f'polardb_mysql_health_inspect_report_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)

    print('┌' + '─' * 50 + '┐')
    print('│  PolarDB MySQL Batch Inspection              │')
    print('└' + '─' * 50 + '┘')
    print(f'  Instances: {len(clusters)}')
    print(f'  Output directory: {output_dir}')
    if config._CLI_PROFILE:
        print(f'  Profile: {config._CLI_PROFILE}')
    print()

    def _do_inspect(cluster):
        cid = cluster['cluster_id']
        r = cluster.get('region')
        _, _, summary = inspect_single_cluster(cid, r, output_dir, fmt=fmt)
        return summary

    if len(clusters) == 1:
        summaries = [_do_inspect(clusters[0])]
    else:
        with ThreadPoolExecutor(max_workers=min(len(clusters), 5)) as pool:
            futures = [pool.submit(_do_inspect, c) for c in clusters]
            summaries = [f.result() for f in futures]

    inspect_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if len(summaries) > 1:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
        time_range = f"{start_date} ~ {end_date} (past {args.days} days)"
        agg_data = aggregate_summaries(summaries, time_range=time_range, scanned_total=len(clusters))
        index_path = render_summary_html(summaries, agg_data, output_dir, inspect_time)
        print(f'\n{"="*60}')
        print(f'📊 Summary report: {index_path}')
        print(f'   {len(summaries)} instance(s) inspected')
        danger_n = sum(1 for s in summaries if any(item[0] == 'danger' for item in s.get('suggestions', []) if isinstance(item, (list, tuple)) and item))
        warn_n = sum(1 for s in summaries if not any(item[0] == 'danger' for item in s.get('suggestions', []) if isinstance(item, (list, tuple)) and item) and any(item[0] == 'warn' for item in s.get('suggestions', []) if isinstance(item, (list, tuple)) and item))
        print(f'   🔴 {danger_n} danger  🟡 {warn_n} warning  🟢 {len(summaries) - danger_n - warn_n} healthy')
    else:
        print(f'\n📄 Report directory: {output_dir}')
