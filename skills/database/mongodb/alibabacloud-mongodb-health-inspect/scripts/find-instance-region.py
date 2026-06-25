#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find the Region of a MongoDB (DDS) instance
Uses aliyun CLI, no manual AK/SK configuration needed

Usage:
    python3 find-instance-region.py <instance_id> [--profile <profile_name>]
"""

import subprocess
import json
import sys
import os
import argparse


def call_cli(action, region, profile=None, **kwargs):
    session_id = os.environ.get('SKILL_SESSION_ID', '') or 'no-session'
    user_agent = f'AlibabaCloud-Agent-Skills/alibabacloud-mongodb-health-inspect/{session_id}'
    cmd = [
        'aliyun', 'dds', action,
        '--region', region,
        '--user-agent', user_agent
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


def find_mongodb_instance(instance_id, profile=None):
    for region in REGIONS:
        data = call_cli('DescribeDBInstanceAttribute', region, profile,
                        DBInstanceId=instance_id)
        if data:
            instances = data.get('DBInstances', {}).get('DBInstance', [])
            if instances:
                inst = instances[0]
                actual_region = inst.get('RegionId', region)
                print(f'\n✅ MongoDB instance found!')
                print(f'   Region: {actual_region}')
                print(f'   Instance ID: {inst.get("DBInstanceId")}')
                print(f'   Status: {inst.get("DBInstanceStatus")}')
                print(f'   Engine: {inst.get("Engine")} {inst.get("EngineVersion")}')
                print(f'   Instance Type: {inst.get("DBInstanceType")}')
                print(f'   Instance Class: {inst.get("DBInstanceClass", "-")}')
                return actual_region
    return None


def main():
    parser = argparse.ArgumentParser(description='Find the Region of a MongoDB instance')
    parser.add_argument('instance_id', metavar='INSTANCE_ID',
                        help='MongoDB instance ID (dds-xxx)')
    parser.add_argument('-p', '--profile',
                        help='aliyun CLI profile name')
    args = parser.parse_args()

    instance_id = args.instance_id

    # Check if aliyun CLI is available
    try:
        result = subprocess.run(['aliyun', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('❌ aliyun CLI not found, please install: https://help.aliyun.com/zh/cli/')
        sys.exit(1)

    print(f'🔍 Finding Region for instance {instance_id}...')
    print('=' * 80)

    region = find_mongodb_instance(instance_id, args.profile)

    if not region:
        print(f'\n❌ Instance not found: {instance_id}')
        print('Possible reasons:')
        print('  1. Incorrect instance ID')
        print('  2. Current credentials do not have access (run aliyun configure list to check)')
        print('  3. Instance has been released')
        if args.profile:
            print(f'  4. Profile "{args.profile}" credentials lack permission')
        sys.exit(1)


if __name__ == '__main__':
    main()
