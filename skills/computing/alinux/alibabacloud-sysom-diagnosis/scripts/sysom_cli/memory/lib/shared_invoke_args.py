# -*- coding: utf-8 -*-
"""memory 子命令共用的「可选深度诊断」CLI 参数（与 io|net|load 专项子命令共用 OpenAPI 侧选项）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# (flags, kwargs) 供 @command_metadata args= 使用（含 --deep-diagnosis 与远程专项共用参数）
MEMORY_DEEP_DIAGNOSIS_ARGS: List[Tuple[Any, Dict[str, Any]]] = [
    (
        ["--verbose-envelope"],
        {
            "action": "store_true",
            "help": "输出展开型 agent.summary 与 agent.next（默认紧凑：省 token，结论见 data.*）。",
        },
    ),
    (
        ["--deep-diagnosis"],
        {
            "action": "store_true",
            "help": "快速排查完成后，同一次调用内继续深度诊断（与 io|net|load 同一 OpenAPI 链路）。",
        },
    ),
    (
        ["--channel"],
        {"default": "ecs", "help": "诊断通道，默认 ecs"},
    ),
    (
        ["--timeout"],
        {"type": int, "default": 300, "help": "轮询 GetDiagnosisResult 超时秒数"},
    ),
    (
        ["--poll-interval"],
        {"type": int, "default": 1, "help": "轮询间隔秒数"},
    ),
    (
        ["--region"],
        {"default": None, "help": "合并到 params.region；与专项 invoke 子命令相同"},
    ),
    (
        ["--instance"],
        {"default": None, "help": "合并到 params.instance；与专项 invoke 子命令相同"},
    ),
    (
        ["--params"],
        {"default": None, "help": "params JSON 字符串"},
    ),
    (
        ["--params-file"],
        {"default": None, "help": "params JSON 文件路径"},
    ),
]
