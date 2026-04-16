# -*- coding: utf-8 -*-
"""
Precheck 命令实现

环境预检查：验证阿里云认证配置和 SysOM API 权限
"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata


@command_metadata(
    name="precheck",
    help="环境预检查：验证阿里云认证配置和 SysOM API 权限",
    args=[]  # precheck 不需要额外参数
)
class PrecheckCommand(BaseCommand):
    """环境预检查命令"""
    
    @property
    def command_name(self) -> str:
        return "precheck"
    
    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: False,
            ExecutionMode.HYBRID: False,
        }
    
    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        """
        Local 模式：执行环境预检查
        
        检查阿里云认证配置（AKSK / ECS RAM Role）
        并验证 SysOM API 访问权限
        
        返回标准 JSON 信封格式
        """
        from sysom_cli.lib.auth import run_precheck
        from sysom_cli.lib.precheck_envelope import envelope_from_precheck_result

        return envelope_from_precheck_result(run_precheck())
