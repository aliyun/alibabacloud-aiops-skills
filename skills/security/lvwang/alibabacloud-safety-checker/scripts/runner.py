"""
测试运行器 - 批量调用审核接口，支持多服务对比、异步任务轮询、结果汇总
"""
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

from client import ContentModerationClient
from config import (
    AUDIO_SERVICES,
    IMAGE_SERVICES,
    OUTPUT_DIR,
    SAMPLES_DIR,
    TEXT_SERVICES,
    VIDEO_SERVICES,
    TestConfig,
)
from models import (
    AnnotationLabel,
    ModalityType,
    ModerationResult,
    SampleData,
    TestBatchResult,
)

logger = logging.getLogger(__name__)


class SampleLoader:
    """样本数据加载器 - 支持CSV、JSON、Excel格式"""

    @staticmethod
    def load_from_json(file_path: str) -> List[SampleData]:
        """从JSON文件加载样本"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = []
        items = data if isinstance(data, list) else data.get("samples", [])
        for item in items:
            sample = SampleData(
                sample_id=item.get("sample_id", str(uuid.uuid4())[:8]),
                modality=ModalityType(item.get("modality", "text")),
                content=item.get("content", ""),
                data_id=item.get("data_id", ""),
                category=item.get("category", ""),
                expected_risk_level=item.get("expected_risk_level", ""),
                expected_labels=item.get("expected_labels", []),
                metadata=item.get("metadata", {}),
            )
            samples.append(sample)
        return samples

    @staticmethod
    def load_from_csv(file_path: str) -> List[SampleData]:
        """从CSV文件加载样本"""
        import csv

        samples = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sample = SampleData(
                    sample_id=row.get("sample_id", str(uuid.uuid4())[:8]),
                    modality=ModalityType(row.get("modality", "text")),
                    content=row.get("content", ""),
                    data_id=row.get("data_id", ""),
                    category=row.get("category", ""),
                    expected_risk_level=row.get("expected_risk_level", ""),
                    expected_labels=row.get("expected_labels", "").split("|") if row.get("expected_labels") else [],
                )
                samples.append(sample)
        return samples

    @staticmethod
    def load_from_excel(file_path: str) -> List[SampleData]:
        """从Excel文件加载样本"""
        import pandas as pd

        df = pd.read_excel(file_path)
        samples = []
        for _, row in df.iterrows():
            expected_labels = []
            if pd.notna(row.get("expected_labels", "")):
                expected_labels = str(row["expected_labels"]).split("|")

            sample = SampleData(
                sample_id=str(row.get("sample_id", str(uuid.uuid4())[:8])),
                modality=ModalityType(str(row.get("modality", "text"))),
                content=str(row.get("content", "")),
                data_id=str(row.get("data_id", "")) if pd.notna(row.get("data_id")) else "",
                category=str(row.get("category", "")) if pd.notna(row.get("category")) else "",
                expected_risk_level=str(row.get("expected_risk_level", "")) if pd.notna(row.get("expected_risk_level")) else "",
                expected_labels=expected_labels,
            )
            samples.append(sample)
        return samples

    @classmethod
    def load(cls, file_path: str) -> List[SampleData]:
        """根据文件扩展名自动选择加载方式"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".json":
            return cls.load_from_json(file_path)
        elif ext == ".csv":
            return cls.load_from_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            return cls.load_from_excel(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}，请使用 .json / .csv / .xlsx")


class TestRunner:
    """测试运行器 - 协调批量审核流程"""

    def __init__(self, config: Optional[TestConfig] = None):
        self.config = config or TestConfig()
        self.client = ContentModerationClient()
        self.batch_result: Optional[TestBatchResult] = None

    def run(self, samples: List[SampleData]) -> TestBatchResult:
        """
        运行一批测试
        - 对每个样本，调用其对应模态的所有配置服务
        - 文本/图片同步调用，音频/视频异步调用后轮询结果
        """
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.batch_result = TestBatchResult(
            batch_id=batch_id,
            start_time=datetime.now().isoformat(),
            total_samples=len(samples),
        )

        logger.info(f"开始测试批次: {batch_id}, 样本数: {len(samples)}")

        # 按模态分组
        text_samples = [s for s in samples if s.modality == ModalityType.TEXT]
        image_samples = [s for s in samples if s.modality == ModalityType.IMAGE]
        audio_samples = [s for s in samples if s.modality == ModalityType.AUDIO]
        video_samples = [s for s in samples if s.modality == ModalityType.VIDEO]

        # 执行同步审核（文本、图片）
        self._run_sync_moderation(text_samples, ModalityType.TEXT)
        self._run_sync_moderation(image_samples, ModalityType.IMAGE)

        # 执行异步审核（音频、视频）
        self._run_async_moderation(audio_samples, ModalityType.AUDIO)
        self._run_async_moderation(video_samples, ModalityType.VIDEO)

        # 汇总统计
        self.batch_result.end_time = datetime.now().isoformat()
        self.batch_result.total_requests = len(self.batch_result.results)
        self.batch_result.success_count = sum(
            1 for r in self.batch_result.results if r.success
        )
        self.batch_result.failure_count = (
            self.batch_result.total_requests - self.batch_result.success_count
        )
        self._compute_stats()

        logger.info(
            f"批次 {batch_id} 完成: "
            f"总请求={self.batch_result.total_requests}, "
            f"成功={self.batch_result.success_count}, "
            f"失败={self.batch_result.failure_count}"
        )

        return self.batch_result

    def _get_services_for_modality(self, modality: ModalityType) -> List[str]:
        """获取指定模态应使用的服务列表"""
        if modality == ModalityType.TEXT:
            return self.config.text_services
        elif modality == ModalityType.IMAGE:
            return self.config.image_services
        elif modality == ModalityType.AUDIO:
            return self.config.audio_services
        elif modality == ModalityType.VIDEO:
            return self.config.video_services
        return []

    def _run_sync_moderation(
        self, samples: List[SampleData], modality: ModalityType
    ):
        """执行同步审核（文本、图片）- 使用线程池并发"""
        if not samples:
            return

        services = self._get_services_for_modality(modality)
        if not services:
            return

        logger.info(
            f"开始{modality.value}审核: {len(samples)}个样本 × {len(services)}个服务"
        )

        tasks = []
        for sample in samples:
            for service in services:
                tasks.append((sample, service))

        with ThreadPoolExecutor(max_workers=self.config.max_concurrent) as executor:
            futures = {}
            for sample, service in tasks:
                # 控制QPS
                time.sleep(self.config.request_interval)
                future = executor.submit(
                    self._execute_single_sync, sample, service, modality
                )
                futures[future] = (sample.sample_id, service)

            for future in as_completed(futures):
                sample_id, service = futures[future]
                try:
                    result = future.result()
                    self.batch_result.results.append(result)
                    status = "✓" if result.success else "✗"
                    logger.debug(
                        f"  {status} [{sample_id}] service={service} "
                        f"risk={result.risk_level} request_id={result.request_id}"
                    )
                except Exception as e:
                    logger.error(f"  ✗ [{sample_id}] service={service} error={e}")

    def _execute_single_sync(
        self, sample: SampleData, service: str, modality: ModalityType
    ) -> ModerationResult:
        """执行单个同步审核请求"""
        if modality == ModalityType.TEXT:
            result = self.client.moderate_text(
                content=sample.content,
                service=service,
                data_id=sample.data_id or sample.sample_id,
            )
        elif modality == ModalityType.IMAGE:
            result = self.client.moderate_image(
                image_url=sample.content,
                service=service,
                data_id=sample.data_id or sample.sample_id,
            )
        else:
            raise ValueError(f"不支持的同步模态: {modality}")

        result.sample_id = sample.sample_id
        return result

    def _run_async_moderation(
        self, samples: List[SampleData], modality: ModalityType
    ):
        """执行异步审核（音频、视频）- 提交后轮询结果"""
        if not samples:
            return

        services = self._get_services_for_modality(modality)
        if not services:
            return

        logger.info(
            f"开始{modality.value}审核: {len(samples)}个样本 × {len(services)}个服务"
        )

        # 阶段1: 提交所有任务
        submitted_tasks: List[ModerationResult] = []
        for sample in samples:
            for service in services:
                time.sleep(self.config.request_interval)
                if modality == ModalityType.AUDIO:
                    result = self.client.moderate_audio(
                        audio_url=sample.content,
                        service=service,
                        data_id=sample.data_id or sample.sample_id,
                    )
                elif modality == ModalityType.VIDEO:
                    result = self.client.moderate_video(
                        video_url=sample.content,
                        service=service,
                        data_id=sample.data_id or sample.sample_id,
                    )
                else:
                    continue

                result.sample_id = sample.sample_id
                submitted_tasks.append(result)

                if result.success and result.task_id:
                    logger.debug(
                        f"  → [{sample.sample_id}] 提交成功, "
                        f"task_id={result.task_id}"
                    )
                else:
                    logger.warning(
                        f"  ✗ [{sample.sample_id}] 提交失败: "
                        f"{result.error_message}"
                    )

        # 阶段2: 轮询异步任务结果
        pending_tasks = [t for t in submitted_tasks if t.success and t.task_id]
        start_wait = time.time()

        while pending_tasks and (
            time.time() - start_wait < self.config.async_max_wait
        ):
            time.sleep(self.config.async_poll_interval)
            still_pending = []

            for task in pending_tasks:
                if modality == ModalityType.AUDIO:
                    poll_result = self.client.poll_audio_result(
                        task.task_id, task.service
                    )
                else:
                    poll_result = self.client.poll_video_result(
                        task.task_id, task.service
                    )

                if poll_result:
                    # 解析异步结果
                    data = poll_result.get("Data", poll_result.get("data", {}))
                    if isinstance(data, dict):
                        task.risk_level = data.get("RiskLevel", data.get("riskLevel", "unknown"))
                        results_list = data.get("Result", data.get("result", []))
                        if results_list:
                            for item in results_list:
                                label = item.get("Label", item.get("label", ""))
                                if label:
                                    task.labels.append(label)
                                conf = item.get("Confidence", item.get("confidence"))
                                if conf is not None:
                                    task.confidence[label] = conf
                    task.raw_response = poll_result
                    task.response_time = datetime.now().isoformat()
                    logger.debug(
                        f"  ✓ [{task.sample_id}] 异步结果就绪, "
                        f"risk={task.risk_level}"
                    )
                else:
                    still_pending.append(task)

            pending_tasks = still_pending

        # 超时的任务标记为失败
        for task in pending_tasks:
            task.success = False
            task.error_message = "异步任务超时未返回结果"
            logger.warning(f"  ✗ [{task.sample_id}] 异步任务超时")

        # 收集所有异步结果
        self.batch_result.results.extend(submitted_tasks)

    def _compute_stats(self):
        """计算统计数据"""
        for result in self.batch_result.results:
            # 按服务统计
            if result.service not in self.batch_result.service_stats:
                self.batch_result.service_stats[result.service] = {
                    "total": 0, "success": 0, "high": 0, "medium": 0,
                    "low": 0, "none": 0,
                }
            stats = self.batch_result.service_stats[result.service]
            stats["total"] += 1
            if result.success:
                stats["success"] += 1
            stats[result.risk_level] = stats.get(result.risk_level, 0) + 1

            # 按风险等级统计
            rl = result.risk_level
            self.batch_result.risk_level_stats[rl] = (
                self.batch_result.risk_level_stats.get(rl, 0) + 1
            )

            # 按模态统计
            mod = result.modality.value
            if mod not in self.batch_result.modality_stats:
                self.batch_result.modality_stats[mod] = {
                    "total": 0, "success": 0, "high": 0, "medium": 0,
                    "low": 0, "none": 0,
                }
            mstats = self.batch_result.modality_stats[mod]
            mstats["total"] += 1
            if result.success:
                mstats["success"] += 1
            mstats[result.risk_level] = mstats.get(result.risk_level, 0) + 1
