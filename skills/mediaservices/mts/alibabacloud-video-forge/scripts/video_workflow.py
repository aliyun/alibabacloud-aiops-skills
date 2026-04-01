#!/usr/bin/env python3
"""
video_workflow.py - 阿里云视频处理端到端工作流脚本

功能：
  一键完成视频上传、媒体信息获取、截图、转码、内容审核和结果下载
  
使用场景：
  - B 站/YouTube 等视频平台发布
  - UGC 视频内容处理和审核
  - 视频批量处理

用法：
  # 完整工作流（上传 + 转码 + 审核 + 下载）
  python video_workflow.py --input /path/to/video.mp4 --output-dir ./output
  
  # 仅转码和审核
  python video_workflow.py --oss-object oss://bucket/input/video.mp4 --skip-upload
  
  # 自定义处理选项
  python video_workflow.py --input video.mp4 --preset 720p --scenes porn terrorism
"""

import argparse
import os
import sys
import time
from datetime import datetime

# 添加脚本目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 导入依赖检查
from dependency_check import check_alicloud_dependencies

# 检查依赖
if not check_alicloud_dependencies():
    sys.exit(1)


def log(message, level="INFO"):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌"
    }.get(level, "•")
    print(f"[{timestamp}] {prefix} {message}")


def step_upload(local_file, oss_key, bucket, endpoint):
    """步骤 1: 上传视频到 OSS"""
    log("开始上传视频到 OSS...")
    
    from oss_upload import upload_file, get_oss_auth
    import oss2
    
    auth = get_oss_auth()
    
    if not os.path.isfile(local_file):
        log(f"文件不存在：{local_file}", "ERROR")
        return None
    
    file_size = os.path.getsize(local_file)
    log(f"本地文件：{local_file} ({file_size / 1024 / 1024:.2f} MB)")
    log(f"目标 OSS: oss://{bucket}/{oss_key}")
    
    result = upload_file(
        local_file=local_file,
        oss_key=oss_key,
        bucket_name=bucket,
        endpoint=endpoint,
        auth=auth,
        verbose=False
    )
    
    if result:
        log("上传成功!", "SUCCESS")
        return result
    else:
        log("上传失败", "ERROR")
        return None


def step_mediainfo(oss_key, region):
    """步骤 2: 获取媒体信息"""
    log("获取媒体信息...")
    
    import subprocess
    
    # 使用命令行调用
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'mps_mediainfo.py'),
        '--oss-object', oss_key,
        '--region', region
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        log("媒体信息获取成功", "SUCCESS")
        # 解析输出获取关键信息
        output = result.stdout
        if 'Duration' in output:
            for line in output.split('\n'):
                if 'Duration:' in line or 'FPS:' in line or 'Resolution:' in line:
                    log(f"  {line.strip()}")
        return {'success': True, 'output': output}
    else:
        log(f"媒体信息获取失败：{result.stderr}", "ERROR")
        return None


def step_snapshot(oss_key, output_prefix, region, time_ms=30000):
    """步骤 3: 生成封面截图"""
    log(f"生成封面截图 (时间点：{time_ms}ms)...")
    
    import subprocess
    
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'mps_snapshot.py'),
        '--oss-object', oss_key,
        '--mode', 'normal',
        '--time', str(time_ms),
        '--count', '1',
        '--output-prefix', output_prefix,
        '--region', region
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    
    if result.returncode == 0 or 'Job' in result.stdout:
        log("截图生成成功", "SUCCESS")
        # 提取输出信息
        for line in result.stdout.split('\n'):
            if 'URL:' in line or 'Object:' in line:
                log(f"  {line.strip()}")
        return {'success': True, 'output': result.stdout}
    else:
        log(f"截图生成失败：{result.stderr}", "WARNING")
        return None


def step_transcode(oss_key, output_prefix, region, preset="multi"):
    """步骤 4: 提交转码任务"""
    log(f"提交转码任务 (预设：{preset})...")
    
    import subprocess
    
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'mps_transcode.py'),
        '--oss-object', oss_key,
        '--preset', preset,
        '--output-prefix', output_prefix,
        '--region', region
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0 or 'JobId' in result.stdout:
        log("转码任务提交成功", "SUCCESS")
        # 提取 JobID 信息
        for line in result.stdout.split('\n'):
            if 'JobId=' in line:
                log(f"  {line.strip()}")
        return {'success': True, 'output': result.stdout}
    else:
        log(f"转码任务提交失败：{result.stderr}", "ERROR")
        return None


def step_audit(oss_key, region, scenes=None):
    """步骤 5: 提交内容审核"""
    log("提交内容审核...")
    
    if scenes is None:
        scenes = ["porn", "terrorism", "ad"]
    
    import subprocess
    
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'mps_audit.py'),
        '--oss-object', oss_key,
        '--scenes'] + scenes + ['--region', region]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0 or 'Job' in result.stdout:
        log("内容审核提交成功", "SUCCESS")
        # 提取审核结果
        for line in result.stdout.split('\n'):
            if 'Suggestion:' in line or 'Pass' in line:
                log(f"  {line.strip()}")
        return {'success': True, 'output': result.stdout}
    else:
        log(f"内容审核提交失败：{result.stderr}", "WARNING")
        return None


def run_workflow(args):
    """执行完整工作流"""
    log("=" * 60)
    log("阿里云视频处理工作流 - 开始执行")
    log("=" * 60)
    
    # 设置默认参数
    bucket = os.environ.get('ALIBABA_CLOUD_OSS_BUCKET', 'test-video-forge')
    endpoint = os.environ.get('ALIBABA_CLOUD_OSS_ENDPOINT', 'oss-cn-beijing.aliyuncs.com')
    region = os.environ.get('ALIBABA_CLOUD_REGION', 'cn-beijing')
    
    # 步骤 0: 凭证检查
    log("检查环境配置...")
    from load_env import ensure_env_loaded, check_and_setup_credentials
    ensure_env_loaded()
    
    if not check_and_setup_credentials():
        log("凭证配置失败，无法继续", "ERROR")
        return False
    
    # 步骤 1: 上传视频
    if not args.skip_upload:
        if not args.input_file:
            log("必须指定输入文件 (--input)", "ERROR")
            return False
        
        oss_key = args.oss_key or f"input/{os.path.basename(args.input_file)}"
        upload_result = step_upload(args.input_file, oss_key, bucket, endpoint)
        
        if not upload_result:
            log("上传失败，终止流程", "ERROR")
            return False
    else:
        if not args.oss_object:
            log("必须指定 OSS 对象 (--oss-object)", "ERROR")
            return False
        oss_key = args.oss_object
        log(f"跳过上传，使用现有 OSS 对象：{oss_key}")
    
    # 步骤 2: 获取媒体信息
    mediainfo_result = step_mediainfo(oss_key, region)
    
    # 步骤 3: 生成封面截图
    if args.generate_cover:
        snapshot_prefix = args.output_prefix or "snapshot/"
        step_snapshot(oss_key, snapshot_prefix, region, args.snapshot_time)
    
    # 步骤 4: 转码
    if not args.skip_transcode:
        transcode_prefix = args.output_prefix or "output/"
        step_transcode(oss_key, transcode_prefix, region, args.preset)
    
    # 步骤 5: 内容审核
    if not args.skip_audit:
        step_audit(oss_key, region, args.scenes)
    
    log("=" * 60)
    log("工作流执行完成!", "SUCCESS")
    log("=" * 60)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="阿里云视频处理端到端工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整处理流程
  python video_workflow.py --input /path/to/video.mp4
  
  # 仅转码和审核（跳过上传）
  python video_workflow.py --oss-object oss://bucket/input/video.mp4 --skip-upload
  
  # 自定义输出和质量
  python video_workflow.py --input video.mp4 --preset 720p --output-prefix bilibili/
        """
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", "-i", dest="input_file", help="本地视频文件路径")
    input_group.add_argument("--oss-object", dest="oss_object", help="OSS 对象路径（跳过上传时使用）")
    
    # 输出参数
    parser.add_argument("--output-prefix", "-o", default="output/", help="OSS 输出前缀 (default: output/)")
    parser.add_argument("--output-dir", dest="output_dir", help="本地输出目录（用于下载结果）")
    
    # 控制参数
    parser.add_argument("--oss-key", "-k", help="上传到 OSS 的 Key 路径 (default: input/<filename>)")
    parser.add_argument("--preset", "-p", choices=["360p", "480p", "720p", "1080p", "4k", "multi"], 
                       default="multi", help="转码质量预设 (default: multi)")
    parser.add_argument("--scenes", nargs="+", default=["porn", "terrorism", "ad"],
                       help="内容审核类型 (default: porn terrorism ad)")
    
    # 功能开关
    parser.add_argument("--skip-upload", action="store_true", help="跳过上传步骤")
    parser.add_argument("--skip-transcode", action="store_true", help="跳过转码步骤")
    parser.add_argument("--skip-audit", action="store_true", help="跳过审核步骤")
    parser.add_argument("--generate-cover", action="store_true", help="生成封面截图")
    parser.add_argument("--snapshot-time", type=int, default=30000, 
                       help="封面截图时间点 (毫秒) (default: 30000)")
    
    # 其他参数
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出模式")
    
    args = parser.parse_args()
    
    # 执行工作流
    success = run_workflow(args)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
