#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find the region of a PolarDB cluster.
Uses aliyun CLI — no manual AK/SK configuration required.

Usage:
    python3 find-instance-region.py <cluster_id> [--profile <profile_name>]
"""

import subprocess
import json
import sys
import argparse


_ALLOWED_ACTIONS = frozenset({
    'polardb:describe-db-cluster-attribute',
    'polardb:describe-db-clusters',
})


def call_cli(product, action, region, profile=None, **kwargs):
    action_key = f'{product}:{action}'
    if action_key not in _ALLOWED_ACTIONS:
        return None
    cmd = [
        'aliyun', product, action,
        '--region', region,
    ]
    if profile:
        cmd.extend(['--profile', profile])
    for key, value in kwargs.items():
        cmd.extend([f'--{key}', str(value)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


REGIONS = [
    'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen',
    'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
    'cn-hongkong', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3',
    'ap-southeast-5', 'ap-northeast-1', 'us-west-1', 'us-east-1',
    'eu-west-1', 'eu-central-1', 'me-east-1', 'ap-south-1',
]


def find_polardb_cluster(cluster_id, profile=None):
    for region in REGIONS:
        data = call_cli('polardb', 'describe-db-cluster-attribute',
                        region, profile, **{'db-cluster-id': cluster_id})
        if data and data.get('DBClusterId'):
            actual_region = data.get('RegionId', region)
            print(f'\n✅ PolarDB cluster found!')
            print(f'   Region: {actual_region}')
            print(f'   Cluster ID: {data.get("DBClusterId")}')
            print(f'   Cluster status: {data.get("DBClusterStatus")}')
            print(f'   Engine: {data.get("DBType")} {data.get("DBVersion")}')
            print(f'   Node class: {data.get("DBNodeClass")}')
            return actual_region
    return None


def main():
    parser = argparse.ArgumentParser(description='Find the region of a PolarDB cluster')
    parser.add_argument('cluster_id', metavar='CLUSTER_ID',
                        help='PolarDB cluster ID (pc-xxx)')
    parser.add_argument('-p', '--profile',
                        help='aliyun CLI profile name')
    args = parser.parse_args()

    cluster_id = args.cluster_id

    # Check if aliyun CLI is available
    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('❌ aliyun CLI not found. Please install: https://help.aliyun.com/zh/cli/')
        sys.exit(1)

    print(f'🔍 Searching for cluster {cluster_id} region...')
    print('=' * 80)

    region = find_polardb_cluster(cluster_id, args.profile)

    if not region:
        print(f'\n❌ Cluster {cluster_id} not found')
        print('Possible reasons:')
        print('  1. Incorrect cluster ID')
        print('  2. Current credentials have no access to this cluster (run aliyun configure list to check)')
        print('  3. Cluster has been released')
        if args.profile:
            print(f'  4. Profile "{args.profile}" credentials lack permission')
        sys.exit(1)


if __name__ == '__main__':
    main()
