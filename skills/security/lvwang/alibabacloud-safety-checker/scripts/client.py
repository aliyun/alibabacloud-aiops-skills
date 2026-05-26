"""
API客户端 - 封装阿里云内容安全各模态审核接口
支持：文本审核增强版PLUS、图片审核增强版、语音审核增强版、视频审核增强版
"""
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from alibabacloud_green20220302.client import Client
from alibabacloud_green20220302 import models
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions
from alibabacloud_credentials.client import Client as CredClient

from config import (
    ENDPOINT,
    REGION_ID,
)
from models import ModalityType, ModerationResult

logger = logging.getLogger(__name__)


class ContentModerationClient:
    """内容安全审核客户端 - 统一封装多模态审核能力"""

    def __init__(self):
        self._client = self._create_client()
        self._runtime = RuntimeOptions()

    def _create_client(self) -> Client:
        """创建阿里云API客户端（使用默认凭证链）"""
        cred = CredClient()
        config = Config(
            credential=cred,
            region_id=REGION_ID,
            endpoint=ENDPOINT,
            user_agent="AlibabaCloud-Agent-Skills/alibabacloud-safety-checker",
            read_timeout=30,
            connect_timeout=10,
        )
        return Client(config)

    # ==================== 文本审核 ====================

    def moderate_text(
        self, content: str, service: str, data_id: str = ""
    ) -> ModerationResult:
        """
        文本审核增强版PLUS
        - service: ugc_moderation_byllm / ugc_moderation_byllm_pro /
                   aigc_moderation_byllm / ugc_moderation_byllm_cb
        """
        sample_id = data_id or f"text_{int(time.time() * 1000)}"
        request_time = datetime.now().isoformat()
        start_ts = time.time()

        service_parameters = {"content": content}
        if data_id:
            service_parameters["dataId"] = data_id

        request = models.TextModerationPlusRequest(
            service=service,
            service_parameters=json.dumps(service_parameters),
        )

        result = ModerationResult(
            sample_id=sample_id,
            service=service,
            request_id="",
            modality=ModalityType.TEXT,
            request_time=request_time,
        )

        try:
            response = self._client.text_moderation_plus_with_options(
                request, self._runtime
            )
            elapsed_ms = (time.time() - start_ts) * 1000
            result.response_time = datetime.now().isoformat()
            result.latency_ms = elapsed_ms

            if response.status_code == 200:
                body = response.body
                result.request_id = body.request_id or ""

                if body.code == 200:
                    result.success = True
                    data = body.data
                    if data:
                        result.risk_level = data.risk_level or "none"
                        if data.result:
                            for item in data.result:
                                if item.label:
                                    result.labels.append(item.label)
                                if item.confidence is not None:
                                    result.confidence[item.label] = item.confidence
                                if item.description:
                                    result.reason = item.description
                        result.raw_response = self._body_to_dict(body)
                else:
                    result.success = False
                    result.error_code = str(body.code)
                    result.error_message = body.message or ""
                    result.request_id = body.request_id or ""
            else:
                result.success = False
                result.error_code = str(response.status_code)
                result.error_message = "HTTP请求失败"

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.response_time = datetime.now().isoformat()
            result.latency_ms = (time.time() - start_ts) * 1000
            logger.error(f"文本审核异常 [service={service}]: {e}")

        return result

    # ==================== 图片审核 ====================

    def moderate_image(
        self, image_url: str, service: str, data_id: str = ""
    ) -> ModerationResult:
        """
        图片审核增强版
        - service: baselineCheck / baselineCheck_pro / baselineCheckByVL /
                   aigcCheck / profilePhotoCheck / postImageCheck 等
        """
        sample_id = data_id or f"image_{int(time.time() * 1000)}"
        request_time = datetime.now().isoformat()
        start_ts = time.time()

        service_parameters = {"imageUrl": image_url}
        if data_id:
            service_parameters["dataId"] = data_id

        request = models.ImageModerationRequest(
            service=service,
            service_parameters=json.dumps(service_parameters),
        )

        result = ModerationResult(
            sample_id=sample_id,
            service=service,
            request_id="",
            modality=ModalityType.IMAGE,
            request_time=request_time,
        )

        try:
            response = self._client.image_moderation_with_options(
                request, self._runtime
            )
            elapsed_ms = (time.time() - start_ts) * 1000
            result.response_time = datetime.now().isoformat()
            result.latency_ms = elapsed_ms

            if response.status_code == 200:
                body = response.body
                result.request_id = body.request_id or ""

                if body.code == 200:
                    result.success = True
                    data = body.data
                    if data:
                        result.risk_level = data.risk_level or "none"
                        if data.result:
                            for item in data.result:
                                if item.label:
                                    result.labels.append(item.label)
                                if item.confidence is not None:
                                    result.confidence[item.label] = item.confidence
                                if item.description:
                                    result.reason = item.description
                        result.raw_response = self._body_to_dict(body)
                else:
                    result.success = False
                    result.error_code = str(body.code)
                    result.error_message = body.msg or ""
                    result.request_id = body.request_id or ""
            else:
                result.success = False
                result.error_code = str(response.status_code)
                result.error_message = "HTTP请求失败"

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.response_time = datetime.now().isoformat()
            result.latency_ms = (time.time() - start_ts) * 1000
            logger.error(f"图片审核异常 [service={service}]: {e}")

        return result

    # ==================== 音频审核（异步） ====================

    def moderate_audio(
        self, audio_url: str, service: str = "audio_media_detection", data_id: str = ""
    ) -> ModerationResult:
        """
        音频审核增强版（异步接口：提交 → 轮询结果）
        """
        sample_id = data_id or f"audio_{int(time.time() * 1000)}"
        request_time = datetime.now().isoformat()
        start_ts = time.time()

        service_parameters = {"url": audio_url}
        if data_id:
            service_parameters["dataId"] = data_id

        request = models.VoiceModerationRequest(
            service=service,
            service_parameters=json.dumps(service_parameters),
        )

        result = ModerationResult(
            sample_id=sample_id,
            service=service,
            request_id="",
            modality=ModalityType.AUDIO,
            request_time=request_time,
            is_async=True,
        )

        try:
            response = self._client.voice_moderation_with_options(
                request, self._runtime
            )
            elapsed_ms = (time.time() - start_ts) * 1000
            result.latency_ms = elapsed_ms

            if response.status_code == 200:
                body = response.body
                result.request_id = body.request_id or ""

                if body.code == 200:
                    result.success = True
                    data = body.data
                    if data and data.task_id:
                        result.task_id = data.task_id
                    result.raw_response = self._body_to_dict(body)
                else:
                    result.success = False
                    result.error_code = str(body.code)
                    result.error_message = body.message or ""
            else:
                result.success = False
                result.error_code = str(response.status_code)
                result.error_message = "HTTP请求失败"

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"音频审核提交异常 [service={service}]: {e}")

        result.response_time = datetime.now().isoformat()
        return result

    def poll_audio_result(
        self, task_id: str, service: str = "audio_media_detection"
    ) -> Optional[Dict]:
        """轮询音频审核结果"""
        service_parameters = {"taskId": task_id}
        request = models.VoiceModerationResultRequest(
            service=service,
            service_parameters=json.dumps(service_parameters),
        )

        try:
            response = self._client.voice_moderation_result_with_options(
                request, self._runtime
            )
            if response.status_code == 200:
                body = response.body
                if body.code == 200 and body.data:
                    data = body.data
                    # 检查任务是否完成
                    raw = self._body_to_dict(body)
                    return raw
            return None
        except Exception as e:
            logger.error(f"音频结果查询异常 [task_id={task_id}]: {e}")
            return None

    # ==================== 视频审核（异步） ====================

    def moderate_video(
        self, video_url: str, service: str = "videoDetection", data_id: str = ""
    ) -> ModerationResult:
        """
        视频审核增强版（异步接口：提交 → 轮询结果）
        """
        sample_id = data_id or f"video_{int(time.time() * 1000)}"
        request_time = datetime.now().isoformat()
        start_ts = time.time()

        service_parameters = {"url": video_url}
        if data_id:
            service_parameters["dataId"] = data_id

        request = models.VideoModerationRequest(
            service=service,
            service_parameters=json.dumps(service_parameters),
        )

        result = ModerationResult(
            sample_id=sample_id,
            service=service,
            request_id="",
            modality=ModalityType.VIDEO,
            request_time=request_time,
            is_async=True,
        )

        try:
            response = self._client.video_moderation_with_options(
                request, self._runtime
            )
            elapsed_ms = (time.time() - start_ts) * 1000
            result.latency_ms = elapsed_ms

            if response.status_code == 200:
                body = response.body
                result.request_id = body.request_id or ""

                if body.code == 200:
                    result.success = True
                    data = body.data
                    if data and data.task_id:
                        result.task_id = data.task_id
                    result.raw_response = self._body_to_dict(body)
                else:
                    result.success = False
                    result.error_code = str(body.code)
                    result.error_message = body.message or ""
            else:
                result.success = False
                result.error_code = str(response.status_code)
                result.error_message = "HTTP请求失败"

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"视频审核提交异常 [service={service}]: {e}")

        result.response_time = datetime.now().isoformat()
        return result

    def poll_video_result(
        self, task_id: str, service: str = "videoDetection"
    ) -> Optional[Dict]:
        """轮询视频审核结果"""
        service_parameters = {"taskId": task_id}
        request = models.VideoModerationResultRequest(
            service=service,
            service_parameters=json.dumps(service_parameters),
        )

        try:
            response = self._client.video_moderation_result_with_options(
                request, self._runtime
            )
            if response.status_code == 200:
                body = response.body
                if body.code == 200 and body.data:
                    return self._body_to_dict(body)
            return None
        except Exception as e:
            logger.error(f"视频结果查询异常 [task_id={task_id}]: {e}")
            return None

    # ==================== 辅助方法 ====================

    @staticmethod
    def _body_to_dict(body) -> Dict:
        """将SDK响应body对象转换为字典（尽可能保留原始数据）"""
        try:
            if hasattr(body, "to_map"):
                return body.to_map()
            return {"raw": str(body)}
        except Exception:
            return {"raw": str(body)}
