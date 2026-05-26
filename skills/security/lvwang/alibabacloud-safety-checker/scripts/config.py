"""
配置模块 - 内容安全自动化测试框架
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List

# ============ 区域和端点配置 ============
REGION_ID = os.environ.get("CONTENT_SECURITY_REGION", "cn-shanghai")
ENDPOINT = f"green-cip.{REGION_ID}.aliyuncs.com"

# ============ QPS限制 ============
MAX_QPS = 50  # 单用户QPS限制

# ============ 审核服务配置 ============
# 文本审核服务
TEXT_SERVICES = {
    "ugc_moderation_byllm": "UGC文本审核标准版",
    "ugc_moderation_byllm_pro": "UGC文本审核Pro版",
    "aigc_moderation_byllm": "AIGC文本审核",
    "ugc_moderation_byllm_cb": "UGC文本审核跨境版",
}

# 图片审核服务
IMAGE_SERVICES = {
    "baselineCheck": "图片基线检测",
    "baselineCheck_pro": "图片基线检测Pro",
    "baselineCheckByVL": "图片VL模型检测",
    "aigcCheck": "AIGC图片检测",
    "profilePhotoCheck": "头像检测",
    "postImageCheck": "帖子图片检测",
    "advertisingCheck": "广告检测",
    "liveStreamCheck": "直播截图检测",
}

# 音频审核服务
AUDIO_SERVICES = {
    "audio_media_detection": "音频媒体检测",
}

# 视频审核服务
VIDEO_SERVICES = {
    "videoDetection": "视频检测",
    "liveStreamDetection": "直播流检测",
}

# ============ 风险等级定义 ============
RISK_LEVELS = ["high", "medium", "low", "none"]

# ============ 标注标签定义 ============
ANNOTATION_LABELS = {
    "correct": "正确（审核结果与实际一致）",
    "false_positive": "误判（内容安全但被判为违规）",
    "false_negative": "漏判（内容违规但被判为安全）",
    "uncertain": "不确定（需要进一步确认）",
}

# ============ 输出配置 ============
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")


@dataclass
class TestConfig:
    """测试运行配置"""
    # 要测试的服务列表
    text_services: List[str] = field(default_factory=lambda: list(TEXT_SERVICES.keys()))
    image_services: List[str] = field(default_factory=lambda: list(IMAGE_SERVICES.keys())[:2])
    audio_services: List[str] = field(default_factory=lambda: list(AUDIO_SERVICES.keys()))
    video_services: List[str] = field(default_factory=lambda: list(VIDEO_SERVICES.keys())[:1])

    # 并发控制
    max_concurrent: int = 10
    request_interval: float = 0.02  # 请求间隔（秒），控制QPS

    # 异步任务轮询
    async_poll_interval: float = 2.0  # 异步任务结果轮询间隔（秒）
    async_max_wait: float = 300.0  # 异步任务最大等待时间（秒）

    # 输出格式
    output_format: str = "xlsx"  # xlsx 或 csv
