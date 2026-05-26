"""
数据模型 - 样本数据和审核结果的数据结构定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ModalityType(Enum):
    """内容模态类型"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class RiskLevel(Enum):
    """风险等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
    UNKNOWN = "unknown"


class AnnotationLabel(Enum):
    """人工标注标签"""
    CORRECT = "correct"            # 正确：审核结果与实际一致
    FALSE_POSITIVE = "false_positive"  # 误判：内容安全但被判为违规
    FALSE_NEGATIVE = "false_negative"  # 漏判：内容违规但被判为安全
    UNCERTAIN = "uncertain"        # 不确定：需要进一步确认
    PENDING = "pending"            # 待标注


@dataclass
class SampleData:
    """样本数据"""
    sample_id: str                       # 样本唯一ID
    modality: ModalityType               # 模态类型
    content: str                         # 文本内容或URL（图片/音频/视频）
    data_id: str = ""                    # 自定义数据ID，用于追踪
    category: str = ""                   # 样本分类（如：政治、色情、暴力等）
    expected_risk_level: str = ""        # 期望风险等级（可选，用于自动对比）
    expected_labels: List[str] = field(default_factory=list)  # 期望标签列表
    metadata: Dict[str, Any] = field(default_factory=dict)    # 额外元数据


@dataclass
class ModerationResult:
    """单次审核结果"""
    sample_id: str                       # 对应的样本ID
    service: str                         # 使用的审核服务
    request_id: str                      # 请求ID（核心追踪字段）
    modality: ModalityType               # 模态类型
    risk_level: str = "unknown"          # 风险等级: high/medium/low/none
    labels: List[str] = field(default_factory=list)    # 风险标签列表
    confidence: Dict[str, float] = field(default_factory=dict)  # 各标签置信度
    reason: str = ""                     # 审核原因描述
    raw_response: Dict[str, Any] = field(default_factory=dict)  # 原始响应（完整保留）

    # 时间信息
    request_time: str = ""               # 请求发送时间
    response_time: str = ""              # 响应接收时间
    latency_ms: float = 0.0             # 请求耗时（毫秒）

    # 异步任务相关
    task_id: str = ""                    # 异步任务ID（音频/视频）
    is_async: bool = False               # 是否为异步任务

    # 错误信息
    success: bool = True                 # 是否调用成功
    error_code: str = ""                 # 错误码
    error_message: str = ""              # 错误消息

    # 人工标注
    annotation: str = AnnotationLabel.PENDING.value  # 标注结果
    annotation_note: str = ""            # 标注备注
    annotated_by: str = ""               # 标注人
    annotated_at: str = ""               # 标注时间


@dataclass
class TestBatchResult:
    """一批测试的汇总结果"""
    batch_id: str                        # 批次ID
    start_time: str                      # 开始时间
    end_time: str = ""                   # 结束时间
    total_samples: int = 0               # 总样本数
    total_requests: int = 0              # 总请求数（样本数 × 服务数）
    success_count: int = 0               # 成功数
    failure_count: int = 0               # 失败数
    results: List[ModerationResult] = field(default_factory=list)  # 所有审核结果

    # 按服务统计
    service_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # 按风险等级统计
    risk_level_stats: Dict[str, int] = field(default_factory=dict)
    # 按模态类型统计
    modality_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
