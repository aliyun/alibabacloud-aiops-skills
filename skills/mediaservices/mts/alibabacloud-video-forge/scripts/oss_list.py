#!/usr/bin/env python3
"""
阿里云 OSS 文件列表脚本

功能：
  使用阿里云 OSS Python SDK (oss2) 列出指定 Bucket 中的文件列表，支持路径前缀过滤。

用法：
  # 列出 Bucket 根目录下的所有文件（使用环境变量中的 bucket）
  python oss_list.py

  # 列出指定路径下的文件
  python oss_list.py --prefix output/transcode/

  # 指定 bucket 和 endpoint
  python oss_list.py --prefix input/ --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

  # 限制返回数量
  python oss_list.py --prefix output/ --max-keys 50

  # JSON 格式输出
  python oss_list.py --prefix output/ --json

环境变量：
  ALIBABA_CLOUD_OSS_BUCKET        - OSS Bucket 名称
  ALIBABA_CLOUD_OSS_ENDPOINT      - OSS Endpoint（如 oss-cn-hangzhou.aliyuncs.com）
  
  凭证通过 alibabacloud_credentials 默认凭证链获取，请使用 'aliyun configure' 配置。
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 加载环境变量模块（同目录）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
try:
    from load_env import ensure_env_loaded, get_oss_auth, _print_setup_hint
    _LOAD_ENV_AVAILABLE = True
except ImportError:
    _LOAD_ENV_AVAILABLE = False

try:
    import oss2
except ImportError:
    print("错误：未安装阿里云 OSS SDK。请运行：pip install oss2", file=sys.stderr)
    sys.exit(1)


def validate_prefix(prefix: str) -> bool:
    """
    验证 OSS 前缀格式安全性
    
    Args:
        prefix: OSS 路径前缀
    
    Returns:
        bool: 是否通过验证
    """
    # 空前缀是合法的（表示根目录）
    if not prefix:
        return True
    
    # 防止路径遍历
    if '..' in prefix:
        print(f"错误：OSS 前缀包含非法序列 '..': {prefix}", file=sys.stderr)
        return False
    
    # 防止双斜杠
    if '//' in prefix:
        print(f"错误：OSS 前缀包含非法双斜杠: {prefix}", file=sys.stderr)
        return False
    
    # 检查特殊字符（允许常见安全字符）
    import re
    # 允许: 字母、数字、/、-、_、.
    if not re.match(r'^[a-zA-Z0-9/_\-.]*$', prefix):
        print(f"错误：OSS 前缀包含非法字符: {prefix}", file=sys.stderr)
        return False
    
    return True


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="阿里云 OSS 文件列表工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 列出 Bucket 根目录所有文件
  python oss_list.py

  # 列出指定路径下的文件
  python oss_list.py --prefix output/transcode/

  # 限制返回数量
  python oss_list.py --prefix output/ --max-keys 50

  # JSON 格式输出
  python oss_list.py --prefix output/ --json
        """
    )

    parser.add_argument(
        "--prefix", "-p",
        default="",
        help="路径前缀，用于过滤指定目录下的文件（如 output/transcode/）"
    )
    parser.add_argument(
        "--max-keys", "-m",
        type=int,
        default=100,
        help="最大返回文件数量（默认 100）"
    )
    parser.add_argument(
        "--bucket", "-b",
        default=None,
        help="OSS Bucket 名称（默认使用环境变量 ALIBABA_CLOUD_OSS_BUCKET）"
    )
    parser.add_argument(
        "--endpoint", "-e",
        default=None,
        help="OSS Endpoint（默认使用环境变量 ALIBABA_CLOUD_OSS_ENDPOINT）"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="以 JSON 格式输出"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志"
    )

    return parser.parse_args()


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.2f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


def format_time(time_str):
    """格式化时间字符串"""
    try:
        # OSS 返回的时间格式可能是 datetime 对象或字符串
        if isinstance(time_str, datetime):
            return time_str.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # 尝试解析 ISO 格式时间字符串
            dt = datetime.fromisoformat(str(time_str).replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(time_str)


def list_files(bucket_name, endpoint, auth,
               prefix="", max_keys=100, verbose=False):
    """
    列出 OSS Bucket 中的文件

    Args:
        bucket_name: OSS Bucket 名称
        endpoint: OSS Endpoint
        auth: OSS 认证对象（oss2.Auth 或 oss2.ProviderAuth）
        prefix: 路径前缀
        max_keys: 最大返回数量
        verbose: 是否显示详细日志

    Returns:
        list: 文件列表
    """
    # 创建 Bucket 对象
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    if verbose:
        print(f"Bucket: {bucket_name}")
        print(f"Endpoint: {endpoint}")
        print(f"Prefix: {prefix if prefix else '(根目录)'}")
        print(f"限制: 最多 {max_keys} 个文件")
        print("-" * 60)

    # 列出文件
    files = []

    try:
        # 使用 list_objects_v2 列出文件
        marker = ''
        while len(files) < max_keys:
            # 每次请求的数量
            batch_size = min(100, max_keys - len(files))

            result = bucket.list_objects(
                prefix=prefix,
                marker=marker,
                max_keys=batch_size
            )

            # 获取文件列表
            for obj in result.object_list:
                # 跳过目录（以 / 结尾的 key）
                if obj.key.endswith('/'):
                    continue

                file_info = {
                    'Key': obj.key,
                    'Size': obj.size,
                    'LastModified': obj.last_modified,
                    'ETag': obj.etag.strip('"') if obj.etag else ''
                }

                files.append(file_info)

                if len(files) >= max_keys:
                    break

            # 检查是否还有更多文件
            if not result.is_truncated:
                break

            # 获取下一页的 marker
            marker = result.next_marker

        return files

    except oss2.exceptions.OssError as e:
        print(f"列出文件失败: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"列出文件失败: {e}", file=sys.stderr)
        return None


def print_files(files, json_output=False):
    """
    打印文件列表

    Args:
        files: 文件列表
        json_output: 是否以 JSON 格式输出
    """
    if not files:
        if json_output:
            print(json.dumps([], ensure_ascii=False, indent=2))
        else:
            print("未找到文件。")
        return

    if json_output:
        # JSON 格式输出
        output = []
        for file in files:
            output.append({
                'key': file['Key'],
                'filename': os.path.basename(file['Key']),
                'size': file['Size'],
                'size_formatted': format_size(file['Size']),
                'last_modified': format_time(file['LastModified']),
                'etag': file['ETag']
            })
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 表格格式输出
        print(f"\n共找到 {len(files)} 个文件\n")

        # 表头
        print(f"{'序号':<6} {'文件名':<50} {'大小':<12} {'修改时间'}")
        print("-" * 90)

        # 打印文件信息
        for idx, file in enumerate(files, 1):
            key = file['Key']
            filename = os.path.basename(key)
            size = format_size(file['Size'])
            last_modified = format_time(file['LastModified'])

            # 截断文件名以适应显示
            display_name = filename[:47] + "..." if len(filename) > 50 else filename

            print(f"{idx:<6} {display_name:<50} {size:<12} {last_modified}")

        print()

        # 统计信息
        total_size = sum(f['Size'] for f in files)
        print(f"总大小: {format_size(total_size)}")


def main():
    """主函数"""
    args = parse_args()

    # 输入参数安全校验
    if not validate_prefix(args.prefix):
        print("错误：OSS 前缀校验失败", file=sys.stderr)
        sys.exit(1)

    # 加载环境变量
    if _LOAD_ENV_AVAILABLE:
        ensure_env_loaded(verbose=args.verbose)

    # 获取配置
    bucket = args.bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET")
    endpoint = args.endpoint or os.environ.get("ALIBABA_CLOUD_OSS_ENDPOINT")

    # 检查必需参数
    if not bucket:
        print("错误：缺少 OSS Bucket 配置。请设置 ALIBABA_CLOUD_OSS_BUCKET 环境变量，或使用 --bucket 参数。", file=sys.stderr)
        sys.exit(1)

    if not endpoint:
        print("错误：缺少 OSS Endpoint 配置。请设置 ALIBABA_CLOUD_OSS_ENDPOINT 环境变量，或使用 --endpoint 参数。", file=sys.stderr)
        sys.exit(1)

    # 获取 OSS 认证对象（使用 alibabacloud_credentials）
    if _LOAD_ENV_AVAILABLE:
        auth = get_oss_auth()
    else:
        # alibabacloud_credentials 不可用时报错
        print("错误：缺少阿里云凭证配置。请使用 'aliyun configure' 命令配置凭证。", file=sys.stderr)
        sys.exit(1)

    # 列出文件
    files = list_files(
        bucket_name=bucket,
        endpoint=endpoint,
        auth=auth,
        prefix=args.prefix,
        max_keys=args.max_keys,
        verbose=args.verbose
    )

    if files is not None:
        print_files(files, json_output=args.json)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
