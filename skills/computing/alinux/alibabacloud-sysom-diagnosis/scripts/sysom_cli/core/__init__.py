# -*- coding: utf-8 -*-
"""
核心框架模块

提供所有子系统（diagnosis、io 等）共享的基础设施：
- BaseCommand / RemoteOnlyCommand: 抽象基类
- CommandRegistry: 命令自动发现与注册
- CommandExecutor: 统一执行器
"""
from sysom_cli.core.base import BaseCommand, ExecutionMode, RemoteOnlyCommand
from sysom_cli.core.registry import CommandRegistry, command_metadata
from sysom_cli.core.executor import CommandExecutor

__all__ = [
    "BaseCommand",
    "RemoteOnlyCommand",
    "ExecutionMode",
    "CommandRegistry",
    "command_metadata",
    "CommandExecutor",
]
