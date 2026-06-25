#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询 PolarDB 集群所在 Region
使用 aliyun CLI 调用，无需手动配置 AK/SK

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
            print(f'\n✅ 找到 PolarDB 集群！')
            print(f'   Region: {actual_region}')
            print(f'   集群 ID: {data.get("DBClusterId")}')
            print(f'   集群状态: {data.get("DBClusterStatus")}')
            print(f'   引擎: {data.get("DBType")} {data.get("DBVersion")}')
            print(f'   集群规格: {data.get("DBNodeClass")}')
            return actual_region
    return None


def main():
    parser = argparse.ArgumentParser(description='查找 PolarDB 集群所在 Region')
    parser.add_argument('cluster_id', metavar='CLUSTER_ID',
                        help='PolarDB 集群 ID (pc-xxx)')
    parser.add_argument('-p', '--profile',
                        help='aliyun CLI profile 名称')
    args = parser.parse_args()

    cluster_id = args.cluster_id

    # 检查 aliyun CLI 是否可用
    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('❌ 未找到 aliyun CLI，请先安装：https://help.aliyun.com/zh/cli/')
        sys.exit(1)

    print(f'🔍 查找集群 {cluster_id} 所在的 Region...')
    print('=' * 80)

    region = find_polardb_cluster(cluster_id, args.profile)

    if not region:
        print(f'\n❌ 未找到集群 {cluster_id}')
        print('可能原因:')
        print('  1. 集群 ID 错误')
        print('  2. 当前凭证无权访问该集群（运行 aliyun configure list 检查）')
        print('  3. 集群已被释放')
        if args.profile:
            print(f'  4. profile "{args.profile}" 配置的凭证无权限')
        sys.exit(1)


if __name__ == '__main__':
    main()
