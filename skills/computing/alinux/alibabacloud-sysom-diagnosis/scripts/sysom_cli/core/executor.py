# -*- coding: utf-8 -*-
"""
统一命令执行器

负责：
1. 从环境变量获取执行模式（local/remote/hybrid）
2. 从注册中心获取命令实例
3. 调用命令的 execute 方法
"""
from __future__ import annotations

import os
from argparse import Namespace
from typing import Any, Dict

from sysom_cli.core.registry import CommandRegistry
from sysom_cli.lib.schema import FORMAT_NAME


class CommandExecutor:
    """统一命令执行器"""
    
    @staticmethod
    def get_execution_mode() -> str:
        """
        从环境变量获取执行模式
        
        环境变量：MEMORY_MODE (local/remote/hybrid)
        默认：local
        """
        mode = os.environ.get("MEMORY_MODE", "local").lower()
        if mode not in ["local", "remote", "hybrid"]:
            mode = "local"
        return mode
    
    @staticmethod
    def execute(command_name: str, ns: Namespace) -> Dict[str, Any]:
        """
        执行命令
        
        Args:
            command_name: 命令名称
            ns: 参数命名空间
        
        Returns:
            标准 JSON 信封
        """
        try:
            command = CommandRegistry.get(command_name)
        except KeyError as e:
            return {
                "format": FORMAT_NAME,
                "ok": False,
                "error": {
                    "code": "command_not_found",
                    "message": str(e)
                },
                "data": {}
            }
        
        mode = CommandExecutor.get_execution_mode()
        return command.execute(ns, mode)
