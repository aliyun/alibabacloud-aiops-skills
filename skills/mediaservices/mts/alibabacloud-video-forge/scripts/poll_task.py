#!/usr/bin/env python3
"""
阿里云 MPS 异步任务轮询工具模块

提供 poll_mps_job() 函数，供各处理脚本在提交任务后直接内置轮询等待，
无需 Agent 手动启动查询。

支持的任务类型：
  - transcode: 转码任务
  - snapshot: 截图任务
  - audit: 审核任务
  - smarttag: 智能标签任务
  - mediainfo: 媒体信息任务

重要说明：
  ⚠️ 本模块设计用于异步任务提交后的结果轮询。
  ⚠️ 默认配置：每 1 秒轮询一次
  ⚠️ 默认超时：根据任务类型自动设置
     • mediainfo: 60 秒 (1 分钟)
     • transcode/snapshot/audit/smarttag: 900 秒 (15 分钟)
  ⚠️ 推荐模式：先使用 async=true 提交任务，然后调用 poll_mps_job() 轮询。

用法（被其他脚本 import）：
    from poll_task import poll_mps_job

    # 提交异步任务后直接轮询（使用默认超时）
    job_id = submit_media_info_job(client, input_json, async_flag=True)
    result = poll_mps_job(job_id, job_type="mediainfo", region="cn-shanghai")
    
    # 自定义超时配置
    result = poll_mps_job(job_id, job_type="transcode", interval=1, max_wait=1800)  # 30 分钟
"""

import json
import os
import sys
import time


def _is_network_error(e):
    """Check if exception is a network error."""
    error_str = str(e).lower()
    return any(keyword in error_str for keyword in [
        'timeout', 'timed out', 'connection', 'network',
        'reset by peer', 'broken pipe', 'eof', 'refused',
        'unreachable', 'sdk.serverunreachable', 'read error',
    ])


def _call_with_retry(func, *args, **kwargs):
    """Call function with retry on network errors (max 1 retry)."""
    for attempt in range(2):  # 最多尝试2次
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == 0 and _is_network_error(e):
                print("[Retry] Network error detected, retrying in 2s...")
                time.sleep(2)
                continue
            raise


# SDK imports - lazy load to allow --help without SDK
try:
    from alibabacloud_credentials.client import Client as CredClient
    from alibabacloud_mts20140618.client import Client as MtsClient
    from alibabacloud_mts20140618 import models as mts_models
    from alibabacloud_tea_openapi.models import Config as OpenApiConfig
    _SDK_AVAILABLE = True
except ImportError as e:
    _SDK_AVAILABLE = False
    _SDK_ERROR = str(e)


# 各类型任务状态映射
STATUS_MAP = {
    # 通用状态
    "Init": "初始化",
    "Submitted": "已提交",
    "Queuing": "排队中",
    "Processing": "处理中",
    "Success": "成功",
    "Fail": "失败",
    "Failed": "失败",
    "Canceled": "已取消",
    "Cancelled": "已取消",
    # 转码特有状态
    "TranscodeSuccess": "转码成功",
    "TranscodeFail": "转码失败",
    "TranscodeCancelled": "转码已取消",
}

# 各任务类型的终态
TERMINAL_STATES = {
    "transcode": ["TranscodeSuccess", "TranscodeFail", "TranscodeCancelled"],
    "snapshot": ["Success", "Fail"],
    "audit": ["Success", "Fail"],
    "smarttag": ["Success", "Fail"],  # smarttag 状态从 Results.Status 获取
    "mediainfo": ["Success", "Fail"],
}


def _get_credentials():
    """使用阿里云默认凭证链获取凭证。"""
    if not _SDK_AVAILABLE:
        print(f"错误：请先安装阿里云 SDK：pip install alibabacloud-mts20140618 alibabacloud-credentials", file=sys.stderr)
        sys.exit(1)
    try:
        cred = CredClient()
        return cred
    except Exception as e:
        print(f"错误：获取阿里云凭证失败: {e}", file=sys.stderr)
        print("请使用 'aliyun configure' 命令配置凭证", file=sys.stderr)
        sys.exit(1)


def _create_client(region):
    """创建 MPS 客户端，带 User-Agent 配置。"""
    cred = _get_credentials()
    config = OpenApiConfig(
        credential=cred,
        endpoint=f"mts.{region}.aliyuncs.com",
        region_id=region,
        user_agent='AlibabaCloud-Agent-Skills',  # Required user-agent
    )
    return MtsClient(config)


def _fmt(status):
    """格式化状态显示。"""
    return STATUS_MAP.get(status, status)


def _query_transcode_job(client, job_id):
    """查询转码任务。"""
    request = mts_models.QueryJobListRequest(
        job_ids=job_id
    )
    response = _call_with_retry(client.query_job_list, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())
    
    # to_map() 返回的数据直接包含字段，没有 body 层级
    job_list = result.get("JobList", {}).get("Job", [])
    if not job_list:
        return None, None, result
    
    job = job_list[0]
    state = job.get("State", "")
    return state, job, result


def _query_snapshot_job(client, job_id):
    """查询截图任务。"""
    request = mts_models.QuerySnapshotJobListRequest(
        snapshot_job_ids=job_id
    )
    response = _call_with_retry(client.query_snapshot_job_list, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())
    
    # to_map() 返回的数据直接包含字段，没有 body 层级
    job_list = result.get("SnapshotJobList", {}).get("SnapshotJob", [])
    if not job_list:
        return None, None, result
    
    job = job_list[0]
    state = job.get("State", "")
    return state, job, result


def _query_audit_job(client, job_id):
    """查询审核任务。"""
    request = mts_models.QueryMediaCensorJobDetailRequest(
        job_id=job_id
    )
    response = _call_with_retry(client.query_media_censor_job_detail, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())
    
    # to_map() 返回的数据直接包含字段，没有 body 层级
    job_detail = result.get("MediaCensorJobDetail", {})
    state = job_detail.get("State", "")
    return state, job_detail, result


def _query_smarttag_job(client, job_id):
    """查询智能标签任务。"""
    request = mts_models.QuerySmarttagJobRequest(
        job_id=job_id
    )
    response = _call_with_retry(client.query_smarttag_job, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())
    
    # 智能标签的状态在 Results 中
    # to_map() 返回的数据直接包含字段，没有 body 层级
    results = result.get("Results", [])
    if not results:
        return None, None, result
    
    # 取第一个结果的状态
    status = results[0].get("Status", "")
    return status, results[0], result


def _query_mediainfo_job(client, job_id):
    """查询媒体信息任务。"""
    request = mts_models.QueryMediaInfoJobListRequest(
        media_info_job_ids=job_id
    )
    response = _call_with_retry(client.query_media_info_job_list, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())
    
    # to_map() 返回的数据直接包含字段，没有 body 层级
    job_list = result.get("MediaInfoJobList", {}).get("MediaInfoJob", [])
    if not job_list:
        return None, None, result
    
    job = job_list[0]
    state = job.get("State", "")
    return state, job, result


def _print_job_result(result, job_type):
    """打印任务结果摘要。"""
    if not result:
        return
    
    # to_map() 返回的数据直接包含字段，没有 body 层级
    # 但为了兼容性，也检查是否有 body 层级（旧版本 SDK 或不同响应格式）
    data = result.get("body") if "body" in result else result
    
    if job_type == "transcode":
        job_list = data.get("JobList", {}).get("Job", [])
        if job_list:
            job = job_list[0]
            output = job.get("Output", {})
            if output:
                output_file = output.get("OutputFile", {})
                if output_file:
                    # 构造输出文件URL (OutputFile中没有FileURL字段，需要手动构造)
                    bucket = output_file.get("Bucket", "")
                    location = output_file.get("Location", "")
                    obj = output_file.get("Object", "")
                    if bucket and obj:
                        # 构造 OSS URL: oss://bucket/object
                        file_url = f"oss://{bucket}/{obj}"
                        print(f"   📁 输出文件: {file_url}")
                    # 也检查是否有直接的FileURL字段（兼容不同版本）
                    file_url_direct = output_file.get("FileURL", "")
                    if file_url_direct:
                        print(f"   📁 输出文件URL: {file_url_direct}")
    
    elif job_type == "snapshot":
        job_list = data.get("SnapshotJobList", {}).get("SnapshotJob", [])
        if job_list:
            job = job_list[0]
            snapshot_config = job.get("SnapshotConfig", {})
            # 截图输出可能有多个
            output_files = snapshot_config.get("OutputFile", {}).get("OutputFile", [])
            if output_files:
                for i, f in enumerate(output_files[:3]):  # 最多显示前3个
                    file_url = f.get("FileURL", "")
                    if file_url:
                        print(f"   📁 截图{i+1}: {file_url}")
                if len(output_files) > 3:
                    print(f"   ... 共 {len(output_files)} 个截图文件")
    
    elif job_type == "audit":
        job_detail = data.get("MediaCensorJobDetail", {})
        # 显示审核结果摘要
        label = job_detail.get("Label", "")
        suggestion = job_detail.get("Suggestion", "")
        if label:
            print(f"   🏷️  审核标签: {label}")
        if suggestion:
            print(f"   💡 建议: {suggestion}")
    
    elif job_type == "smarttag":
        results = data.get("Results", [])
        if results:
            tags = results[0].get("Tags", [])
            if tags:
                print(f"   🏷️  识别到的标签:")
                for tag in tags[:5]:  # 最多显示前5个
                    tag_name = tag.get("Tag", "")
                    confidence = tag.get("Confidence", "")
                    if tag_name:
                        print(f"      • {tag_name} (置信度: {confidence})")
                if len(tags) > 5:
                    print(f"      ... 共 {len(tags)} 个标签")
    
    elif job_type == "mediainfo":
        job_list = data.get("MediaInfoJobList", {}).get("MediaInfoJob", [])
        if job_list:
            job = job_list[0]
            media_info = job.get("MediaInfo", {})
            streams = media_info.get("Streams", [])
            if streams:
                for stream in streams:
                    if stream.get("Type") == "video":
                        video_stream = stream.get("VideoStream", {})
                        if video_stream:
                            codec = video_stream.get("Codec", "")
                            width = video_stream.get("Width", "")
                            height = video_stream.get("Height", "")
                            bitrate = video_stream.get("Bitrate", "")
                            print(f"   📹 视频: {codec} {width}x{height} @ {bitrate}kbps")
                    elif stream.get("Type") == "audio":
                        audio_stream = stream.get("AudioStream", {})
                        if audio_stream:
                            codec = audio_stream.get("Codec", "")
                            sample_rate = audio_stream.get("SampleRate", "")
                            channels = audio_stream.get("Channels", "")
                            print(f"   🔊 音频: {codec} {sample_rate}Hz {channels}ch")


def poll_mps_job(job_id, job_type, region=None, interval=1, max_wait=None, verbose=False):
    """
    轮询 MPS 任务直到完成。
    
    Args:
        job_id:    任务 ID
        job_type:  任务类型 (transcode/snapshot/audit/smarttag/mediainfo)
        region:    MPS 服务区域 (默认从 ALIBABA_CLOUD_REGION 环境变量或 cn-shanghai)
        interval:  轮询间隔（秒），默认 1 秒
        max_wait:  最长等待时间（秒）
                   - mediainfo: 默认 60 秒
                   - transcode/snapshot/audit/smarttag: 默认 900 秒 (15 分钟)
        verbose:   是否输出完整 JSON
    
    Returns:
        最终任务结果 dict，或 None（超时）
    
    Note:
        ⚠️ 重要：此函数设计用于异步任务提交后的结果轮询。
           建议先在提交任务时使用 async=true，然后调用此函数轮询。
    """
    if region is None:
        region = os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai")
    
    # 根据任务类型设置默认超时
    if max_wait is None:
        if job_type == "mediainfo":
            max_wait = 60  # 媒体信息探测通常较快，1 分钟足够
        else:
            max_wait = 900  # 其他任务（转码/截图/审核等）可能需要更长时间，15 分钟
    # 验证任务类型
    valid_types = ["transcode", "snapshot", "audit", "smarttag", "mediainfo"]
    if job_type not in valid_types:
        print(f"错误：不支持的任务类型 '{job_type}'，支持: {', '.join(valid_types)}", file=sys.stderr)
        return None
    
    client = _create_client(region)
    elapsed = 0
    attempt = 0
    
    # 选择查询函数
    query_funcs = {
        "transcode": _query_transcode_job,
        "snapshot": _query_snapshot_job,
        "audit": _query_audit_job,
        "smarttag": _query_smarttag_job,
        "mediainfo": _query_mediainfo_job,
    }
    query_func = query_funcs[job_type]
    
    print(f"\n⏳ 开始轮询 {job_type} 任务状态（间隔 {interval}s，最长等待 {max_wait}s）...")
    
    while elapsed < max_wait:
        attempt += 1
        try:
            state, job_data, result = query_func(client, job_id)
            
            if state is None:
                print(f"   [{attempt}] 未找到任务 {job_id}，{interval}s 后重试...")
            else:
                print(f"   [{attempt}] 状态: {_fmt(state)}  (已等待 {elapsed}s)")
                
                # 检查是否终态
                terminal_states = TERMINAL_STATES.get(job_type, ["Success", "Fail"])
                
                if state in terminal_states or state in ["Success", "TranscodeSuccess"]:
                    print(f"\n✅ 任务完成！")
                    _print_job_result(result, job_type)
                    
                    if verbose:
                        print("\n完整响应：")
                        print(json.dumps(result, ensure_ascii=False, indent=2))
                    return result
                
                if state in ["Fail", "Failed", "TranscodeFail"]:
                    print(f"\n❌ 任务失败！")
                    if job_data:
                        error_code = job_data.get("Code", "")
                        error_msg = job_data.get("Message", "")
                        print(f"   错误码: {error_code}")
                        print(f"   错误信息: {error_msg}")
                    if verbose:
                        print(json.dumps(result, ensure_ascii=False, indent=2))
                    return result
        
        except Exception as e:
            print(f"   [{attempt}] 查询失败: {e}，{interval}s 后重试...")
        
        time.sleep(interval)
        elapsed += interval
    
    print(f"\n⚠️  等待超时（已等待 {max_wait}s），任务可能仍在处理中。")
    print(f"   可手动查询：python scripts/poll_task.py --job-id {job_id} --job-type {job_type} --region {region}")
    return None


# ─── 独立运行时：命令行模式 ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="轮询阿里云 MPS 任务状态"
    )
    parser.add_argument(
        "--job-id", "-j", required=True, help="任务 ID"
    )
    parser.add_argument(
        "--job-type", "-t", required=True, 
        choices=["transcode", "snapshot", "audit", "smarttag", "mediainfo"],
        help="任务类型 (transcode|snapshot|audit|smarttag|mediainfo)"
    )
    parser.add_argument(
        "--region", "-r", default=os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai"), help="服务区域，默认从 ALIBABA_CLOUD_REGION 环境变量或 cn-shanghai"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=1, help="轮询间隔（秒），默认 1"
    )
    parser.add_argument(
        "--max-wait", "-w", type=int, default=None, help="最长等待时间（秒），默认根据任务类型自动设置（mediainfo: 60 秒，其他：900 秒）"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="显示完整 JSON 输出"
    )
    args = parser.parse_args()

    result = poll_mps_job(
        job_id=args.job_id,
        job_type=args.job_type,
        region=args.region,
        interval=args.interval,
        max_wait=args.max_wait,
        verbose=args.verbose
    )
    
    if result is None:
        sys.exit(1)
