#!/usr/bin/env python3
"""
阿里云 OSS 文件删除脚本

功能：
  使用阿里云 OSS Python SDK (oss2) 删除 OSS Bucket 中的文件或目录。

用法：
  # 删除单个文件
  python oss_delete.py --oss-key output/transcode/video.mp4

  # 删除目录下所有文件（递归删除）
  python oss_delete.py --prefix output/transcode/ --recursive

  # 强制删除（跳过确认提示，用于脚本调用）
  python oss_delete.py --oss-key output/video.mp4 --force

  # 预览模式（不实际删除）
  python oss_delete.py --prefix output/ --recursive --dry-run

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


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="阿里云 OSS 文件删除工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 删除单个文件
  python oss_delete.py --oss-key output/transcode/video.mp4

  # 删除目录下所有文件（递归删除）
  python oss_delete.py --prefix output/transcode/ --recursive

  # 强制删除（跳过确认提示）
  python oss_delete.py --oss-key output/video.mp4 --force

  # 预览模式（不实际删除）
  python oss_delete.py --prefix output/ --recursive --dry-run
        """
    )

    # 互斥组：--oss-key 或 --prefix
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--oss-key", "-k",
        help="OSS 对象键（Key），删除单个文件，如 output/video.mp4"
    )
    input_group.add_argument(
        "--prefix", "-p",
        help="OSS 路径前缀，配合 --recursive 删除该前缀下所有文件，如 output/transcode/"
    )

    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="递归删除前缀下的所有文件（仅与 --prefix 配合使用）"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制删除，跳过确认提示（用于脚本自动化）"
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
        help="预览模式，只显示将要删除的文件，不实际删除"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志"
    )

    args = parser.parse_args()

    # 验证参数组合
    if args.prefix and not args.recursive:
        parser.error("使用 --prefix 时必须同时指定 --recursive 参数")

    return args


def list_objects_by_prefix(bucket, prefix, verbose=False):
    """
    列出指定前缀下的所有对象

    Args:
        bucket: OSS Bucket 对象
        prefix: 路径前缀
        verbose: 是否显示详细日志

    Returns:
        list: 对象键列表
    """
    objects = []
    marker = ''
    
    while True:
        result = bucket.list_objects(prefix=prefix, marker=marker, max_keys=1000)
        
        for obj in result.object_list:
            objects.append(obj.key)
            if verbose:
                print(f"  找到: {obj.key}")
        
        if result.is_truncated:
            marker = result.next_marker
        else:
            break
    
    return objects


def delete_single_object(bucket, oss_key, dry_run=False, verbose=False):
    """
    删除单个对象

    Args:
        bucket: OSS Bucket 对象
        oss_key: OSS 对象键
        dry_run: 是否为预览模式
        verbose: 是否显示详细日志

    Returns:
        bool: 是否成功
    """
    if dry_run:
        print(f"[预览] 将删除: {oss_key}")
        return True

    try:
        bucket.delete_object(oss_key)
        if verbose:
            print(f"已删除: {oss_key}")
        return True
    except oss2.exceptions.OssError as e:
        print(f"删除失败 {oss_key}: {e}", file=sys.stderr)
        return False


def delete_objects_batch(bucket, keys, dry_run=False, verbose=False):
    """
    批量删除对象

    Args:
        bucket: OSS Bucket 对象
        keys: 对象键列表
        dry_run: 是否为预览模式
        verbose: 是否显示详细日志

    Returns:
        tuple: (成功数量, 失败数量)
    """
    if not keys:
        return 0, 0

    if dry_run:
        for key in keys:
            print(f"[预览] 将删除: {key}")
        return len(keys), 0

    success_count = 0
    fail_count = 0

    # OSS 批量删除每次最多 1000 个
    batch_size = 1000
    for i in range(0, len(keys), batch_size):
        batch = keys[i:i + batch_size]
        try:
            result = bucket.batch_delete_objects(batch)
            deleted = len(result.deleted_keys)
            success_count += deleted
            if verbose:
                for key in result.deleted_keys:
                    print(f"已删除: {key}")
        except oss2.exceptions.OssError as e:
            print(f"批量删除失败: {e}", file=sys.stderr)
            fail_count += len(batch)

    return success_count, fail_count


def confirm_delete(message, force=False):
    """
    确认删除操作

    Args:
        message: 确认提示信息
        force: 是否强制跳过确认

    Returns:
        bool: 是否确认
    """
    if force:
        return True

    print(f"\n{message}")
    try:
        response = input("确认删除？[y/N]: ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        print("\n操作已取消")
        return False


def validate_oss_key(key: str) -> bool:
    """验证 OSS Key 格式"""
    if not key:
        return False
    
    # 防止路径遍历
    if '..' in key:
        print(f"错误：OSS Key 包含非法序列'..': {key}", file=sys.stderr)
        return False
    
    # 防止双斜杠（oss://除外）
    if '//' in key.replace('oss://', ''):
        print(f"错误：OSS Key 包含非法双斜杠：{key}", file=sys.stderr)
        return False
    
    return True


def validate_prefix(prefix: str) -> bool:
    """验证 OSS 前缀格式"""
    if not prefix:
        return False
    
    # 防止路径遍历
    if '..' in prefix:
        print(f"错误：OSS 前缀包含非法序列'..': {prefix}", file=sys.stderr)
        return False
    
    return True


def safety_check_delete(bucket, prefix_or_key, is_recursive=False, force=False):
    """
    删除操作的安全性预检
    
    Args:
        bucket: OSS Bucket 对象
        prefix_or_key: 前缀或 Key
        is_recursive: 是否递归删除
        force: 是否强制模式
    
    Returns:
        bool: 是否通过安全检查
    """
    # 检查是否为危险操作：删除整个 bucket 或过大范围
    if is_recursive:
        # 统计将要删除的文件数量
        keys = list_objects_by_prefix(bucket, prefix_or_key, verbose=False)
        file_count = len(keys)
        
        # 如果文件数量过大，需要额外确认
        if file_count > 1000 and not force:
            print(f"\n⚠️  警告：即将删除 {file_count} 个文件（数量过大）", file=sys.stderr)
            print(f"前缀：{prefix_or_key}", file=sys.stderr)
            print("\n这是一个高危操作！请确认：", file=sys.stderr)
            print("1. 您确实要删除这么多文件吗？", file=sys.stderr)
            print("2. 这不是生产环境的重要数据吧？", file=sys.stderr)
            print("3. 是否有备份？", file=sys.stderr)
            
            if not confirm_delete("\n确认要继续这个高危删除操作吗？[y/N]: ", force):
                print("操作已取消", file=sys.stderr)
                return False
        
        # 检测是否尝试删除整个 bucket
        if prefix_or_key in ['', '/', '/*'] and file_count > 0:
            print(f"\n⚠️  严重警告：您正在尝试删除整个 Bucket 的所有内容！", file=sys.stderr)
            print(f"Bucket: {bucket.bucket_name}", file=sys.stderr)
            print(f"文件总数：{file_count}", file=sys.stderr)
            print("\n除非您完全确定，否则请立即停止！", file=sys.stderr)
            
            if not force:
                confirm_msg = input("\n输入 Bucket 名称以确认删除：").strip()
                if confirm_msg != bucket.bucket_name:
                    print("Bucket 名称不匹配，操作已取消", file=sys.stderr)
                    return False
    
    return True


def main():
    """主函数"""
    args = parse_args()

    # 加载环境变量
    if _LOAD_ENV_AVAILABLE:
        ensure_env_loaded(verbose=args.verbose)

    # 获取配置
    bucket_name = args.bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET")
    endpoint = args.endpoint or os.environ.get("ALIBABA_CLOUD_OSS_ENDPOINT")

    # 检查必需参数
    if not bucket_name:
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

    # 创建 Bucket 对象
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    if args.verbose:
        print(f"Bucket: {bucket_name}")
        print(f"Endpoint: {endpoint}")

    # 处理删除逻辑
    if args.oss_key:
        # 删除单个文件
        if not validate_oss_key(args.oss_key):
            print("错误：无效的 OSS Key 格式", file=sys.stderr)
            sys.exit(1)
            
        if args.verbose or args.dry_run:
            print(f"\n删除目标：{args.oss_key}")
    
        if not args.dry_run and not confirm_delete(f"即将删除文件：{args.oss_key}", args.force):
            print("操作已取消")
            return 0
    
        success = delete_single_object(bucket, args.oss_key, args.dry_run, args.verbose)

        if args.dry_run:
            print("\n=== 预览完成 ===")
            print("以上文件将被删除（实际未执行）")
        elif success:
            print("\n=== 删除成功 ===")
            print(f"已删除: {args.oss_key}")
        else:
            print("\n=== 删除失败 ===", file=sys.stderr)
            return 1

    else:
        # 递归删除前缀下的所有文件
        if not validate_prefix(args.prefix):
            print("错误：无效的 OSS 前缀格式", file=sys.stderr)
            sys.exit(1)
            
        if args.verbose:
            print(f"\n扫描前缀：{args.prefix}")
    
        keys = list_objects_by_prefix(bucket, args.prefix, args.verbose)
    
        if not keys:
            print(f"未找到匹配的文件（前缀：{args.prefix}）")
            return 0
    
        print(f"\n找到 {len(keys)} 个文件")
            
        # 安全性预检
        if not safety_check_delete(bucket, args.prefix, is_recursive=True, force=args.force):
            print("安全检查未通过，操作已取消", file=sys.stderr)
            return 0
    
        if not args.dry_run and not confirm_delete(f"即将删除 {len(keys)} 个文件（前缀：{args.prefix}）", args.force):
            print("操作已取消")
            return 0

        success_count, fail_count = delete_objects_batch(bucket, keys, args.dry_run, args.verbose)

        if args.dry_run:
            print("\n=== 预览完成 ===")
            print(f"将删除 {len(keys)} 个文件（实际未执行）")
        else:
            print("\n=== 删除完成 ===")
            print(f"成功: {success_count} 个文件")
            if fail_count > 0:
                print(f"失败: {fail_count} 个文件")
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

