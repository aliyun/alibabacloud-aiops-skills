#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Alibaba Cloud Redis (KVStore) instance Region
Uses aliyun CLI, no manual AK/SK configuration needed

Usage:
    python3 find-instance-region.py <instance_id> [--profile <profile_name>]
"""

import subprocess
import json
import sys
import argparse


_ALLOWED_ACTIONS = frozenset({
    'r-kvstore:describe-instance-attribute',
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
    'cn-wulanchabu', 'cn-nanjing', 'cn-fuzhou', 'cn-guangzhou',
    'cn-hongkong', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3',
    'ap-southeast-5', 'ap-southeast-6', 'ap-southeast-7',
    'ap-northeast-1', 'ap-northeast-2',
    'us-west-1', 'us-east-1',
    'eu-west-1', 'eu-central-1', 'me-east-1', 'me-central-1',
    'ap-south-1',
]


def find_kvstore_instance(instance_id, profile=None):
    for region in REGIONS:
        data = call_cli('r-kvstore', 'describe-instance-attribute',
                        region, profile, **{'instance-id': instance_id})
        if data and data.get('Instances', {}).get('DBInstanceAttribute'):
            attrs = data['Instances']['DBInstanceAttribute']
            if attrs:
                attr = attrs[0]
                actual_region = attr.get('RegionId', region)
                print(f'\nFound Redis instance!')
                print(f'   Region: {actual_region}')
                print(f'   Instance ID: {attr.get("InstanceId")}')
                print(f'   Status: {attr.get("InstanceStatus")}')
                print(f'   Engine Version: Redis {attr.get("EngineVersion")}')
                print(f'   Instance Class: {attr.get("InstanceClass")}')
                print(f'   Architecture: {attr.get("ArchitectureType")}')
                return actual_region
    return None


def main():
    parser = argparse.ArgumentParser(description='Find Alibaba Cloud Redis instance Region')
    parser.add_argument('instance_id', metavar='INSTANCE_ID',
                        help='Redis instance ID (r-xxx)')
    parser.add_argument('-p', '--profile',
                        help='aliyun CLI profile name')
    args = parser.parse_args()

    instance_id = args.instance_id

    # Check aliyun CLI availability
    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('ERROR: aliyun CLI not found. Install: https://help.aliyun.com/zh/cli/')
        sys.exit(1)

    print(f'Searching for instance {instance_id}...')
    print('=' * 80)

    region = find_kvstore_instance(instance_id, args.profile)

    if not region:
        print(f'\nERROR: Instance {instance_id} not found')
        print('Possible reasons:')
        print('  1. Instance ID is incorrect')
        print('  2. Current credentials have no access (run: aliyun configure list)')
        print('  3. Instance has been released')
        if args.profile:
            print(f'  4. Profile "{args.profile}" credentials have no permission')
        sys.exit(1)


if __name__ == '__main__':
    main()
