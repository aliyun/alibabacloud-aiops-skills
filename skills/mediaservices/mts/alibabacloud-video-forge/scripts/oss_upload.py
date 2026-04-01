#!/usr/bin/env python3
"""
阿里云 OSS 文件上传脚本

功能：
  使用阿里云 OSS Python SDK (oss2) 将本地文件上传到 OSS Bucket。

用法：
  # 最简用法（使用环境变量中的 bucket 和 endpoint）
  python oss_upload.py --local-file /path/to/local/file.mp4 --oss-key input/video.mp4

  # 指定 bucket 和 endpoint（覆盖环境变量）
  python oss_upload.py --local-file /path/to/file.mp4 --oss-key input/video.mp4 \
      --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

  # 预览模式（不实际上传）
  python oss_upload.py --local-file ./test.mp4 --oss-key input/test.mp4 --dry-run

环境变量：
  ALIBABA_CLOUD_OSS_BUCKET        - OSS Bucket 名称
  ALIBABA_CLOUD_OSS_ENDPOINT      - OSS Endpoint（如 oss-cn-hangzhou.aliyuncs.com）
  
  凭证通过 alibabacloud_credentials 默认凭证链获取，请使用 'aliyun configure' 配置。
"""

import argparse
import os
import sys

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


def validate_local_file(file_path: str) -> bool:
    """
    验证本地文件路径安全性
    
    Args:
        file_path: 本地文件路径
    
    Returns:
        bool: 是否通过验证
    """
    if not file_path:
        print("错误：本地文件路径不能为空", file=sys.stderr)
        return False
    
    # 防止路径遍历攻击
    if '..' in file_path:
        print(f"错误：文件路径包含非法序列 '..': {file_path}", file=sys.stderr)
        return False
    
    # 规范化路径后检查是否仍包含 ..
    normalized = os.path.normpath(file_path)
    if '..' in normalized:
        print(f"错误：文件路径规范化后仍包含非法序列: {normalized}", file=sys.stderr)
        return False
    
    # 检查是否为绝对路径指向系统敏感目录
    abs_path = os.path.abspath(file_path)
    sensitive_dirs = ['/etc', '/var', '/usr', '/bin', '/sbin', '/root', '/proc', '/sys']
    for sensitive_dir in sensitive_dirs:
        if abs_path.startswith(sensitive_dir + '/') or abs_path == sensitive_dir:
            print(f"错误：不允许访问系统敏感目录: {abs_path}", file=sys.stderr)
            return False
    
    return True


def validate_oss_key(key: str) -> bool:
    """
    验证 OSS Key 格式安全性
    
    Args:
        key: OSS 对象键
    
    Returns:
        bool: 是否通过验证
    """
    if not key:
        print("错误：OSS Key 不能为空", file=sys.stderr)
        return False
    
    # 防止路径遍历
    if '..' in key:
        print(f"错误：OSS Key 包含非法序列 '..': {key}", file=sys.stderr)
        return False
    
    # 防止双斜杠（oss:// 除外）
    key_check = key.replace('oss://', '')
    if '//' in key_check:
        print(f"错误：OSS Key 包含非法双斜杠: {key}", file=sys.stderr)
        return False
    
    # 检查特殊字符（允许常见安全字符）
    import re
    # 允许: 字母、数字、/、-、_、.
    if not re.match(r'^[a-zA-Z0-9/_\-.]+$', key.lstrip('/')):
        print(f"错误：OSS Key 包含非法字符: {key}", file=sys.stderr)
        return False
    
    return True


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="阿里云 OSS 文件上传工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 上传文件到 OSS（使用环境变量中的 bucket）
  python oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4

  # 指定 bucket 和 endpoint
  python oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4 \\
      --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

  # 预览模式（不实际上传）
  python oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4 --dry-run
        """
    )

    parser.add_argument(
        "--local-file", "-f",
        required=True,
        help="本地文件路径（必填）"
    )
    parser.add_argument(
        "--oss-key", "-k",
        required=True,
        help="OSS 对象键（Key），如 input/video.mp4（必填）"
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
        "--dry-run", "-d",
        action="store_true",
        help="预览模式，只显示将要执行的操作，不实际上传"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志"
    )

    return parser.parse_args()


def generate_presigned_url(bucket, oss_key, expiration=3600):
    """
    生成预签名下载 URL

    Args:
        bucket: OSS Bucket 对象
        oss_key: OSS 对象键
        expiration: URL 有效期（秒），默认 1 小时

    Returns:
        str: 预签名 URL
    """
    try:
        url = bucket.sign_url('GET', oss_key, expiration)
        return url
    except Exception as e:
        return None


def upload_file(local_file, oss_key, bucket_name, endpoint, auth,
                dry_run=False, verbose=False):
    """
    上传文件到 OSS

    Args:
        local_file: 本地文件路径
        oss_key: OSS 对象键
        bucket_name: OSS Bucket 名称
        endpoint: OSS Endpoint
        auth: OSS 认证对象（oss2.Auth 或 oss2.ProviderAuth）
        dry_run: 是否为预览模式
        verbose: 是否显示详细日志

    Returns:
        dict: 上传结果，包含 URL 和预签名 URL
    """
    # 检查本地文件是否存在
    if not os.path.isfile(local_file):
        print(f"错误：本地文件不存在: {local_file}", file=sys.stderr)
        return None

    # 获取文件大小
    file_size = os.path.getsize(local_file)

    if verbose or dry_run:
        print(f"本地文件: {local_file}")
        print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
        print(f"目标 Bucket: {bucket_name}")
        print(f"目标 Endpoint: {endpoint}")
        print(f"OSS Key: {oss_key}")

    if dry_run:
        print("\n[预览模式] 以上操作不会实际执行")
        return {
            "Key": oss_key,
            "Bucket": bucket_name,
            "Endpoint": endpoint,
            "Size": file_size,
            "DryRun": True
        }

    # 创建 Bucket 对象
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # 上传文件
    try:
        if verbose:
            print(f"\n开始上传...")

        # 使用 put_object_from_file 上传文件
        result = bucket.put_object_from_file(oss_key, local_file)

        if verbose:
            print(f"上传成功！")
            print(f"ETag: {result.etag}")
            print(f"RequestId: {result.request_id}")

        # 构建文件 URL
        url = f"https://{bucket_name}.{endpoint}/{oss_key.lstrip('/')}"

        # 生成预签名 URL
        presigned_url = generate_presigned_url(bucket, oss_key, expiration=3600)

        return {
            "ETag": result.etag,
            "Key": oss_key,
            "Bucket": bucket_name,
            "Endpoint": endpoint,
            "URL": url,
            "PresignedURL": presigned_url,
            "Size": file_size,
            "RequestId": result.request_id
        }

    except oss2.exceptions.OssError as e:
        print(f"上传失败: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"上传失败: {e}", file=sys.stderr)
        return None


def main():
    """主函数"""
    args = parse_args()

    # 输入参数安全校验
    if not validate_local_file(args.local_file):
        print("错误：本地文件路径校验失败", file=sys.stderr)
        sys.exit(1)
    
    if not validate_oss_key(args.oss_key):
        print("错误：OSS Key 校验失败", file=sys.stderr)
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

    # 执行上传
    result = upload_file(
        local_file=args.local_file,
        oss_key=args.oss_key,
        bucket_name=bucket,
        endpoint=endpoint,
        auth=auth,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    if result:
        if result.get("DryRun"):
            print("\n=== 预览完成 ===")
        else:
            print("\n=== 上传成功 ===")
            print(f"文件: {args.local_file}")
            print(f"大小: {result['Size'] / 1024 / 1024:.2f} MB")
            print(f"Bucket: {result['Bucket']}")
            print(f"Key: {result['Key']}")
            print(f"OSS 路径: oss://{result['Bucket']}/{result['Key']}")
            print(f"\n永久 URL: {result['URL']}")
            if result.get('PresignedURL'):
                print(f"预签名 URL（有效期 1 小时）: [已生成，含临时凭证]")
        return 0
    else:
        print("\n=== 上传失败 ===", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
