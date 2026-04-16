# -*- coding: utf-8 -*-
"""
抽象基类定义

所有子命令必须继承 BaseCommand 并实现对应的执行方法。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from argparse import Namespace
from typing import Any, Dict


class ExecutionMode:
    """执行模式常量"""
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


class BaseCommand(ABC):
    """
    命令抽象基类
    
    每个子命令继承此类，实现对应模式的执行方法。
    未实现的模式会抛出 NotImplementedError。
    """
    
    @property
    @abstractmethod
    def command_name(self) -> str:
        """命令名称，如 'oom', 'classify'"""
        pass
    
    @property
    def supported_modes(self) -> Dict[str, bool]:
        """
        声明支持的模式
        
        Returns:
            {"local": True, "remote": False, "hybrid": False}
        """
        return {
            ExecutionMode.LOCAL: False,
            ExecutionMode.REMOTE: False,
            ExecutionMode.HYBRID: False,
        }
    
    def execute(self, ns: Namespace, mode: str) -> Dict[str, Any]:
        """
        统一执行入口，根据 mode 路由到具体实现
        
        Args:
            ns: 命令行参数
            mode: 执行模式 (local/remote/hybrid)
        
        Returns:
            标准 sysom_agent JSON 信封（见 ``lib.schema``）
        """
        if mode not in self.supported_modes or not self.supported_modes[mode]:
            return self._unsupported_mode_error(mode)
        
        if mode == ExecutionMode.LOCAL:
            return self.execute_local(ns)
        elif mode == ExecutionMode.REMOTE:
            from sysom_cli.lib.precheck_gate import remote_precheck_gate

            ok_gate, fail_env = remote_precheck_gate()
            if not ok_gate:
                return fail_env  # type: ignore[return-value]
            return self.execute_remote(ns)
        elif mode == ExecutionMode.HYBRID:
            from sysom_cli.lib.precheck_gate import remote_precheck_gate

            ok_gate, fail_env = remote_precheck_gate()
            if not ok_gate:
                return fail_env  # type: ignore[return-value]
            return self.execute_hybrid(ns)
        else:
            return self._unsupported_mode_error(mode)
    
    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        """
        Local 模式实现
        流程：生成命令 → 本地执行 → 本地分析
        """
        raise NotImplementedError(
            f"{self.command_name} 未实现 local 模式"
        )
    
    def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
        """
        Remote 模式实现
        流程：调用远程 API → 直接返回结果
        """
        raise NotImplementedError(
            f"{self.command_name} 未实现 remote 模式"
        )
    
    def execute_hybrid(self, ns: Namespace) -> Dict[str, Any]:
        """
        Hybrid 模式实现
        流程：调用 OpenAPI（异步+轮询）→ 本地处理 → 转换格式
        """
        raise NotImplementedError(
            f"{self.command_name} 未实现 hybrid 模式"
        )
    
    def _unsupported_mode_action(self) -> str:
        """信封 ``action`` 字段，用于不支持模式时的错误。"""
        return f"cmd_{self.command_name}"
    
    def _unsupported_mode_error(self, mode: str) -> Dict[str, Any]:
        """返回不支持模式的标准错误"""
        # 动态导入避免循环依赖
        try:
            from sysom_cli.lib.schema import envelope, agent_block
            return envelope(
                action=self._unsupported_mode_action(),
                ok=False,
                agent=agent_block(
                    "unknown",
                    f"{self.command_name} 不支持 {mode} 模式"
                ),
                error={
                    "code": "unsupported_mode",
                    "message": f"Mode '{mode}' not supported",
                    "supported_modes": [k for k, v in self.supported_modes.items() if v]
                },
                data={}
            )
        except ImportError:
            # 降级处理：如果 schema 不可用，返回基本错误格式
            return {
                "format": "sysom_agent",
                "ok": False,
                "error": {
                    "code": "unsupported_mode",
                    "message": f"Mode '{mode}' not supported for {self.command_name}",
                    "supported_modes": [k for k, v in self.supported_modes.items() if v]
                },
                "data": {}
            }


class RemoteOnlyCommand(BaseCommand):
    """仅调用远程 OpenAPI，忽略 ``MEMORY_MODE``，始终执行 ``execute_remote``。"""

    def execute(self, ns: Namespace, mode: str) -> Dict[str, Any]:
        from sysom_cli.lib.precheck_gate import remote_precheck_gate

        ok_gate, fail_env = remote_precheck_gate()
        if not ok_gate:
            return fail_env  # type: ignore[return-value]
        return self.execute_remote(ns)
