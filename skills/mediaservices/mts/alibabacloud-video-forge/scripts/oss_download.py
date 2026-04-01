#!/usr/bin/env python3
"""
阿里云 OSS 文件下载脚本

功能：
  使用阿里云 OSS Python SDK (oss2) 从 OSS Bucket 下载文件到本地。

用法：
  # 最简用法（使用环境变量中的 bucket 和 endpoint）
  python oss_download.py --oss-key input/video.mp4 --local-file ./downloaded/video.mp4

  # 指定 bucket 和 endpoint（覆盖环境变量）
  python oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4 \\
      --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

  # 仅生成预签名 URL，不下载
  python oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4 --sign-url

  # 预览模式（不实际下载）
  python oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4 --dry-run

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


def validate_local_path(file_path: str) -> bool:
    """
    验证本地文件写入路径安全性
    
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
    
    # 检查是否写入系统敏感目录
    abs_path = os.path.abspath(file_path)
    sensitive_dirs = ['/etc', '/var', '/usr', '/bin', '/sbin', '/root', '/proc', '/sys', '/boot']
    for sensitive_dir in sensitive_dirs:
        if abs_path.startswith(sensitive_dir + '/') or abs_path == sensitive_dir:
            print(f"错误：不允许写入系统敏感目录: {abs_path}", file=sys.stderr)
            return False
    
    return True


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="阿里云 OSS 文件下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 下载文件到本地（使用环境变量中的 bucket）
  python oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4

  # 指定 bucket 和 endpoint
  python oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4 \\
      --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

  # 仅生成预签名 URL，不下载
  python oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4 --sign-url

  # 预览模式（不实际下载）
  python oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4 --dry-run
        """
    )

    parser.add_argument(
        "--oss-key", "-k",
        required=True,
        help="OSS 对象键（Key），如 input/video.mp4（必填）"
    )
    parser.add_argument(
        "--local-file", "-f",
        required=True,
        help="本地保存路径（必填）"
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
        "--sign-url", "-s",
        action="store_true",
        help="仅生成预签名 URL，不下载文件"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="预览模式，只显示将要执行的操作，不实际下载"
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


def download_file(oss_key, local_file, bucket_name, endpoint, auth,
                  sign_url_only=False, dry_run=False, verbose=False):
    """
    从 OSS 下载文件

    Args:
        oss_key: OSS 对象键
        local_file: 本地保存路径
        bucket_name: OSS Bucket 名称
        endpoint: OSS Endpoint
        auth: OSS 认证对象（oss2.Auth 或 oss2.ProviderAuth）
        sign_url_only: 是否仅生成预签名 URL
        dry_run: 是否为预览模式
        verbose: 是否显示详细日志

    Returns:
        dict: 下载结果，包含文件大小和本地路径
    """
    # 创建 Bucket 对象
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # 生成预签名 URL
    presigned_url = generate_presigned_url(bucket, oss_key, expiration=3600)

    if sign_url_only:
        return {
            "Key": oss_key,
            "Bucket": bucket_name,
            "Endpoint": endpoint,
            "PresignedURL": presigned_url,
            "SignUrlOnly": True
        }

    # 创建本地目录（如果不存在）
    local_dir = os.path.dirname(os.path.abspath(local_file))
    if local_dir and not os.path.exists(local_dir):
        if dry_run:
            if verbose:
                print(f"[预览] 将创建目录: {local_dir}")
        else:
            os.makedirs(local_dir, exist_ok=True)
            if verbose:
                print(f"创建目录: {local_dir}")

    if verbose or dry_run:
        print(f"源 Bucket: {bucket_name}")
        print(f"源 Endpoint: {endpoint}")
        print(f"OSS Key: {oss_key}")
        print(f"本地保存路径: {local_file}")

    if dry_run:
        print("\n[预览模式] 以上操作不会实际执行")
        return {
            "Key": oss_key,
            "Bucket": bucket_name,
            "Endpoint": endpoint,
            "LocalFile": local_file,
            "PresignedURL": presigned_url,
            "DryRun": True
        }

    # 下载文件
    try:
        if verbose:
            print(f"\n开始下载...")

        # 使用 get_object_to_file 下载文件
        result = bucket.get_object_to_file(oss_key, local_file)

        # 获取下载后的文件大小
        file_size = os.path.getsize(local_file)

        # 构建文件 URL
        url = f"https://{bucket_name}.{endpoint}/{oss_key.lstrip('/')}"

        if verbose:
            print(f"下载成功！")
            print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")

        return {
            "Key": oss_key,
            "Bucket": bucket_name,
            "Endpoint": endpoint,
            "LocalFile": local_file,
            "URL": url,
            "PresignedURL": presigned_url,
            "Size": file_size,
            "ETag": result.etag,
            "RequestId": result.request_id
        }

    except oss2.exceptions.NoSuchKey:
        print(f"错误：OSS 对象不存在: {oss_key}", file=sys.stderr)
        return None
    except oss2.exceptions.OssError as e:
        print(f"下载失败: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"下载失败: {e}", file=sys.stderr)
        return None


def main():
    """主函数"""
    args = parse_args()

    # 输入参数安全校验
    if not validate_oss_key(args.oss_key):
        print("错误：OSS Key 校验失败", file=sys.stderr)
        sys.exit(1)
    
    if not validate_local_path(args.local_file):
        print("错误：本地文件路径校验失败", file=sys.stderr)
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

    # 执行下载
    result = download_file(
        oss_key=args.oss_key,
        local_file=args.local_file,
        bucket_name=bucket,
        endpoint=endpoint,
        auth=auth,
        sign_url_only=args.sign_url,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    if result:
        if result.get("SignUrlOnly"):
            print("\n=== 预签名 URL 生成成功 ===")
            print(f"Bucket: {result['Bucket']}")
            print(f"Key: {result['Key']}")
            print(f"\n预签名 URL（有效期 1 小时）: [已生成，含临时凭证]")
            print(f"永久访问 URL: https://{result['Bucket']}.{result['Endpoint'].replace('oss-', '')}/{result['Key'].lstrip('/')}")
        elif result.get("DryRun"):
            print("\n=== 预览完成 ===")
            if result.get('PresignedURL'):
                print(f"\n预签名 URL（有效期 1 小时）: [已生成，含临时凭证]")
        else:
            print("\n=== 下载成功 ===")
            print(f"Bucket: {result['Bucket']}")
            print(f"Key: {result['Key']}")
            print(f"本地文件: {result['LocalFile']}")
            print(f"大小: {result['Size'] / 1024 / 1024:.2f} MB")
            print(f"\n永久 URL: {result['URL']}")
            if result.get('PresignedURL'):
                print(f"预签名 URL（有效期 1 小时）: [已生成，含临时凭证]")
        return 0
    else:
        print("\n=== 下载失败 ===", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
