#!/usr/bin/env python3
"""
Upload file to OSS and get temporary URL.
Uses aliyun ossutil CLI plugin.
"""

import subprocess
import json
import sys
import os
import argparse


def check_aliyun_cli_available():
    """Check if aliyun CLI is available."""
    try:
        result = subprocess.run(
            ['aliyun', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_bucket_region(oss_bucket):
    """Get the region of an OSS bucket using aliyun CLI."""
    try:
        result = subprocess.run(
            ['aliyun', 'ossutil', 'ls', '--user-agent', 'AlibabaCloud-Agent-Skills'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        for line in result.stdout.split('\n'):
            if oss_bucket in line:
                # Extract region from output like: oss-cn-beijing
                for token in line.split():
                    if token.startswith('oss-'):
                        return token.replace('oss-', '')

    except Exception:
        pass
    return None


def upload_to_oss(local_file_path, oss_bucket, oss_object_key):
    """Upload local file to OSS using aliyun CLI."""
    try:
        region = get_bucket_region(oss_bucket)

        cmd = ['aliyun', 'ossutil', 'cp', local_file_path, f'oss://{oss_bucket}/{oss_object_key}',
               '--user-agent', 'AlibabaCloud-Agent-Skills']

        if region:
            cmd.extend(['--region', region])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if result.returncode != 0:
            raise Exception(f'OSS 上传失败: {result.stderr}')

        return True
    except Exception as error:
        raise Exception(f'上传文件到 OSS 失败: {str(error)}')


def get_file_url(oss_bucket, oss_object_key, expire_seconds=3600, region=None):
    """Get temporary URL for OSS object using aliyun CLI."""
    try:
        # Convert seconds to ossutil format: e.g. 7200 -> 2h, 3600 -> 1h
        hours = max(1, expire_seconds // 3600)
        expires_flag = f'{hours}h'

        cmd = ['aliyun', 'ossutil', 'sign', f'oss://{oss_bucket}/{oss_object_key}',
               '--expires-duration', expires_flag, '--user-agent', 'AlibabaCloud-Agent-Skills']

        if region:
            cmd.extend(['--region', region])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            raise Exception(f'获取签名 URL 失败: {result.stderr}')

        temp_url = result.stdout.strip()
        return temp_url
    except Exception as error:
        raise Exception(f'获取临时 URL 失败: {str(error)}')


def get_first_oss_bucket():
    """Get the first OSS bucket using aliyun CLI."""
    try:
        result = subprocess.run(
            ['aliyun', 'ossutil', 'ls', '--user-agent', 'AlibabaCloud-Agent-Skills'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        # 输出格式示例:
        # CreationTime                                 Region       StorageClass    BucketName
        # 2026-03-12 11:17:53 +0800 CST        oss-cn-beijing           Standard    oss://quanmiao1
        lines = result.stdout.strip().split('\n')
        buckets = []
        for line in lines:
            line = line.strip()
            if 'oss://' in line:
                # 提取 bucket 名称: 找到 oss:// 开头到 / 或行末的部分
                idx = line.index('oss://')
                rest = line[idx+6:]  # 去掉 'oss://'
                bucket_name = rest.split('/')[0].strip()
                if bucket_name:
                    buckets.append(bucket_name)

        if buckets:
            return buckets[0]
    except Exception:
        pass

    return None


def main(local_file_path, oss_bucket=None, oss_object_key=None, expire_seconds=7200):
    try:
        # 验证本地文件
        if not os.path.exists(local_file_path):
            raise ValueError(f'文件不存在: {local_file_path}')

        if not os.path.isfile(local_file_path):
            raise ValueError(f'路径不是文件: {local_file_path}')

        # Check aliyun CLI availability
        has_cli = check_aliyun_cli_available()
        if not has_cli:
            install_msg = (
                '未检测到 aliyun CLI，请先安装 aliyun CLI 和 ossutil 插件：\n\n'
                '# macOS (Homebrew):\n'
                'brew install aliyun-cli\n'
                'aliyun plugin install --names aliyun-cli-ossutil\n\n'
                '# 或从源码安装:\n'
                '# 参考 https://github.com/aliyun/aliyun-cli\n\n'
                '# 配置凭据:\n'
                'aliyun configure'
            )
            print(json.dumps({
                'status': 'error',
                'error': 'aliyun CLI 未安装',
                'recommend': install_msg
            }, indent=2, ensure_ascii=False))
            sys.exit(1)

        # 如果未指定 OSS bucket，尝试获取第一个
        if not oss_bucket:
            oss_bucket = get_first_oss_bucket()
            if not oss_bucket:
                recommend = '请先创建 OSS Bucket 并授权。使用命令: aliyun oss mb oss://<bucket-name> --region <region-id>'
                print(json.dumps({
                    'status': 'error',
                    'error': '未找到 OSS Bucket',
                    'recommend': recommend
                }, indent=2, ensure_ascii=False))
                sys.exit(1)

        # 如果未指定 OSS 对象键，使用默认路径
        if not oss_object_key:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            file_name = os.path.basename(local_file_path)
            oss_object_key = f'temp/quanmiao/{date_str}/{file_name}'

        # Get bucket region once, reuse for upload and sign
        region = get_bucket_region(oss_bucket)

        # Upload
        print(json.dumps({'status': 'uploading', 'message': '正在上传文件到 OSS...'}, indent=2, ensure_ascii=False))
        upload_to_oss(local_file_path, oss_bucket, oss_object_key)

        print(json.dumps({'status': 'generating_url', 'message': '正在生成临时 URL...'}, indent=2, ensure_ascii=False))
        file_url = get_file_url(oss_bucket, oss_object_key, expire_seconds, region)

        # 输出结果
        result = {
            'status': 'success',
            'ossBucket': oss_bucket,
            'ossObjectKey': oss_object_key,
            'file_url': file_url,
            'expireSeconds': expire_seconds
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as error:
        print(json.dumps({
            'status': 'error',
            'error': str(error),
            'recommend': '请确保已安装 aliyun CLI 和 ossutil 插件（aliyun plugin install --names aliyun-cli-ossutil）'
        }, indent=2, ensure_ascii=False))
        sys.exit(1)


# 参数校验函数
def validate_local_file_path(arg):
    if not arg or arg.strip() == '':
        raise ValueError('localFilePath 不能为空')
    if not isinstance(arg, str):
        raise ValueError('localFilePath 必须是字符串类型')

    trimmed = arg.strip()

    if not os.path.exists(trimmed):
        raise ValueError(f'文件不存在: {trimmed}')

    if not os.path.isfile(trimmed):
        raise ValueError(f'路径不是文件: {trimmed}')

    return trimmed


def validate_oss_bucket(arg):
    if not arg or arg.strip() == '':
        raise ValueError('ossBucket 不能为空')
    if not isinstance(arg, str):
        raise ValueError('ossBucket 必须是字符串类型')

    trimmed = arg.strip()

    import re
    if not re.match(r'^[a-z0-9-]+$', trimmed):
        raise ValueError('ossBucket 包含非法字符，只允许小写字母、数字和连字符')

    return trimmed


def validate_expire_seconds(arg):
    try:
        seconds = int(arg)
        if seconds <= 0 or seconds > 86400 * 7:  # 最大 7 天
            raise ValueError('过期时间必须在 1 秒到 7 天之间')
        return seconds
    except ValueError:
        raise ValueError('expireSeconds 必须是有效的整数')


# 从命令行参数获取参数
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload file to OSS and get temporary URL')
    parser.add_argument('--localFilePath', required=True, help='Local file path')
    parser.add_argument('--ossBucket', required=False, default=None, help='OSS bucket name (auto-detect if not specified)')
    parser.add_argument('--ossObjectKey', required=False, default=None, help='OSS object key (default: temp/quanmiao/YYYYMMDD/filename)')
    parser.add_argument('--expireSeconds', required=False, type=int, default=7200, help='URL expiration time in seconds (default: 7200)')

    args = parser.parse_args()

    try:
        local_file_path_arg = validate_local_file_path(args.localFilePath)

        oss_bucket_arg = None
        if args.ossBucket:
            oss_bucket_arg = validate_oss_bucket(args.ossBucket)

        oss_object_key_arg = args.ossObjectKey
        expire_seconds_arg = validate_expire_seconds(str(args.expireSeconds))

        main(local_file_path_arg, oss_bucket_arg, oss_object_key_arg, expire_seconds_arg)
    except Exception as error:
        print(json.dumps({'error': str(error)}, indent=2, ensure_ascii=False))
        sys.exit(1)
