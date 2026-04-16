# -*- coding: utf-8 -*-
"""
命令注册中心

支持自动发现和注册命令：
- 扫描子系统下的所有子命令目录
- 自动导入 command.py 模块
- 通过 @command_metadata 装饰器注册
"""
from __future__ import annotations

import importlib
import warnings
from pathlib import Path
from typing import Any, Dict, List

from sysom_cli.core.base import BaseCommand


class CommandRegistry:
    """
    命令注册中心，支持自动发现和注册
    
    自动扫描子系统目录下的所有子命令，
    发现标记为 @command_metadata 的命令类并注册。
    """
    
    _commands: Dict[str, BaseCommand] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    _command_subsystem: Dict[str, str] = {}  # 记录命令所属的子系统
    _discovered: bool = False
    
    @classmethod
    def register(cls, command: BaseCommand, metadata: Dict[str, Any] = None, subsystem: str = None):
        """
        注册命令
        
        Args:
            command: 命令实例
            metadata: 命令元数据（参数定义、帮助信息等）
            subsystem: 所属子系统（如 'diagnosis'），顶层命令为 None
        """
        cls._commands[command.command_name] = command
        if metadata:
            cls._metadata[command.command_name] = metadata
        cls._command_subsystem[command.command_name] = subsystem or "__top_level__"
    
    @classmethod
    def get(cls, command_name: str) -> BaseCommand:
        """获取命令实例"""
        cls._ensure_discovered()
        if command_name not in cls._commands:
            raise KeyError(f"Command '{command_name}' not registered")
        return cls._commands[command_name]
    
    @classmethod
    def get_metadata(cls, command_name: str) -> Dict[str, Any]:
        """获取命令元数据"""
        cls._ensure_discovered()
        return cls._metadata.get(command_name, {})

    @classmethod
    def get_subsystem(cls, command_name: str) -> str | None:
        """子系统名：如 io / net / load / diagnosis；未知返回 None。"""
        cls._ensure_discovered()
        v = cls._command_subsystem.get(command_name)
        if v in (None, "__top_level__"):
            return None
        return v
    
    @classmethod
    def list_commands(cls) -> List[str]:
        """列出所有已注册命令"""
        cls._ensure_discovered()
        return list(cls._commands.keys())
    
    @classmethod
    def get_all_metadata(cls, subsystem: str = None) -> Dict[str, Dict[str, Any]]:
        """
        获取所有命令的元数据
        
        Args:
            subsystem: 子系统名称，如果指定则只返回该子系统的命令
        """
        cls._ensure_discovered()
        if subsystem is None:
            return cls._metadata.copy()
        
        # 只返回指定子系统的命令
        result = {}
        for cmd_name, metadata in cls._metadata.items():
            if cls._command_subsystem.get(cmd_name) == subsystem:
                result[cmd_name] = metadata
        return result
    
    @classmethod
    def discover_commands(cls, subsystem: str = None, top_level: bool = False):
        """
        自动发现并注册命令
        
        Args:
            subsystem: 子系统名称（如 'diagnosis', 'io'）
                      如果为 None 且 top_level=False，扫描所有子系统
            top_level: 是否扫描顶层命令（如 precheck, version）
        
        扫描指定子系统下的所有子命令目录，
        或扫描顶层命令目录，
        自动导入 command.py 并触发 @command_metadata 装饰器。
        """
        if cls._discovered and subsystem is None and not top_level:
            return
        
        import sysom_cli
        cli_path = Path(sysom_cli.__file__).parent
        
        if top_level:
            # 扫描顶层命令（直接在 sysom_cli/ 下有 command.py 的目录）
            for cmd_dir in cli_path.iterdir():
                if not cmd_dir.is_dir():
                    continue
                if cmd_dir.name.startswith(("_", ".")):
                    continue
                # 排除特殊目录：core, lib, auth, commands, diagnosis, io 等子系统
                if cmd_dir.name in (
                    "core",
                    "lib",
                    "auth",
                    "commands",
                    "io",
                    "net",
                    "load",
                    "network",
                    "diagnosis",
                ):
                    continue
                
                # 检查是否有 command.py（顶层命令标志）
                command_file = cmd_dir / "command.py"
                if not command_file.exists():
                    continue
                
                try:
                    # 动态导入顶层命令的 command.py
                    module_path = f"sysom_cli.{cmd_dir.name}.command"
                    importlib.import_module(module_path)
                except Exception as e:
                    warnings.warn(
                        f"Failed to load top-level command '{cmd_dir.name}': {e}"
                    )
            return
        
        # 确定要扫描的子系统
        if subsystem:
            subsystems = [subsystem]
        else:
            # 扫描所有子系统目录（排除特殊目录）
            subsystems = [
                d.name for d in cli_path.iterdir()
                if d.is_dir()
                and not d.name.startswith(("_", "."))
                and d.name not in ("core", "lib", "auth", "commands", "diagnosis")
                and (d / "__init__.py").exists()
                # 排除顶层命令目录（没有 __init__.py 或有 command.py）
                and not (d / "command.py").exists()
            ]
        
        for subsys in subsystems:
            subsys_path = cli_path / subsys
            if not subsys_path.exists():
                continue
            
            # 扫描子系统下的所有子命令目录
            for cmd_dir in subsys_path.iterdir():
                if not cmd_dir.is_dir():
                    continue
                if cmd_dir.name.startswith(("_", ".")):
                    continue
                
                # 检查是否有 command.py
                command_file = cmd_dir / "command.py"
                if not command_file.exists():
                    continue
                
                try:
                    # 动态导入 command.py，触发装饰器注册
                    module_path = f"sysom_cli.{subsys}.{cmd_dir.name}.command"
                    module = importlib.import_module(module_path)
                    # 标记命令所属的子系统
                    cmd_name = cmd_dir.name
                    if cmd_name in cls._commands:
                        cls._command_subsystem[cmd_name] = subsys
                except Exception as e:
                    warnings.warn(
                        f"Failed to load command '{subsys}.{cmd_dir.name}': {e}"
                    )
        
        if subsystem is None and not top_level:
            cls._discovered = True
    
    @classmethod
    def _ensure_discovered(cls):
        """确保已执行发现过程"""
        if not cls._discovered:
            cls.discover_commands()


# 命令元数据装饰器
def command_metadata(**kwargs):
    """
    命令元数据装饰器
    
    用法示例:
    @command_metadata(
        name="oom",
        help="OOM 分析命令",
        args=[
            (["--log-file"], {"help": "日志文件路径", "default": None}),
            (["--list-only"], {"action": "store_true", "help": "仅列出 OOM 块"}),
        ],
        subsystem="diagnosis"  # 可选，指定所属子系统
    )
    class OomCommand(BaseCommand):
        ...
    
    Args:
        name: 命令名称（可选，默认使用类的 command_name 属性）
        help: 命令帮助信息
        args: 参数定义列表，格式同 argparse
        subsystem: 所属子系统（可选），顶层命令不需要指定
    """
    def decorator(cls):
        # 实例化命令
        instance = cls()
        
        # 构建元数据
        metadata = {
            "name": kwargs.get("name", instance.command_name),
            "help": kwargs.get("help", ""),
            "args": kwargs.get("args", []),
            "supported_modes": instance.supported_modes,
        }
        
        # 注册到注册中心
        subsystem = kwargs.get("subsystem")
        CommandRegistry.register(instance, metadata, subsystem=subsystem)
        
        return cls
    
    return decorator
