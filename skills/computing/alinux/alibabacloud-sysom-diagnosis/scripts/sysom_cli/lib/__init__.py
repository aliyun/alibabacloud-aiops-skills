# -*- coding: utf-8 -*-
"""
通用工具库

提供所有子系统共享的工具函数和基础类。
"""
from sysom_cli.lib.schema import (
    FORMAT_NAME, FORMAT_VERSION, agent_block, envelope, dumps, error_envelope,
)
from sysom_cli.lib.kernel_log import get_kernel_log_lines
from sysom_cli.lib.log_plugin import LogScanContext, CollectContext
from sysom_cli.lib import auth  # 认证模块
from sysom_cli.lib import ecs_metadata  # ECS 元数据服务
from sysom_cli.lib import log_parser  # 日志解析器框架

__all__ = [
    "FORMAT_NAME", "FORMAT_VERSION", "agent_block", "envelope", "dumps",
    "error_envelope", "get_kernel_log_lines", "LogScanContext", "CollectContext",
    "auth", "ecs_metadata", "log_parser",
]
