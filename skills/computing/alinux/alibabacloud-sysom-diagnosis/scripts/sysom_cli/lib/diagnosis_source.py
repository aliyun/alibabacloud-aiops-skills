# -*- coding: utf-8 -*-
"""内建注入 __sysom_diagnosis_source：工作区目录启发式；可用环境变量覆盖或关闭。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

__all__ = [
    "DIAGNOSIS_SOURCE_KEY",
    "LEGACY_DIAGNOSIS_SOURCE_KEYS",
    "infer_diagnosis_source_from_cwd",
    "resolve_diagnosis_source",
]

# 写入 OpenAPI params 的键名（旧名 $diagnosis_source 会被网关/后端拦截，勿再用）
DIAGNOSIS_SOURCE_KEY = "__sysom_diagnosis_source"

# 历史上曾注入的键，invoke 前会从 params 中剔除，避免残留进请求体
LEGACY_DIAGNOSIS_SOURCE_KEYS: Tuple[str, ...] = ("$diagnosis_source",)

# 当前目录下存在这些子目录/文件时命中（优先级高于路径段）。
DIR_MARKERS: Tuple[Tuple[str, str], ...] = (
    (".claude", "claude"),
    (".copilot", "cosh"),
)

# 向上遍历时，若当前路径的**最后一段**为下列名称则命中（如 /usr/share/os-copilot/skills/...）。
PATH_SEGMENT_MARKERS: Tuple[Tuple[str, str], ...] = (
    ("os-copilot", "cosh"),
)

# 设置 SYSOM_DIAGNOSIS_SOURCE / OSOPS_DIAGNOSIS_SOURCE 为这些值时：不注入该字段（屏蔽 cwd 启发式）
_DISABLE_SENTINELS = frozenset(
    {
        "-",
        "0",
        "off",
        "none",
        "false",
        "disable",
        "disabled",
    }
)


def infer_diagnosis_source_from_cwd(
    start: Optional[Path] = None,
    *,
    max_depth: int = 64,
) -> Optional[str]:
    """
    从 start（默认 Path.cwd()）逐级向父目录查找：
    1) 是否存在 DIR_MARKERS 中的子目录/文件（如 ``.claude`` / ``.copilot``）；
    2) 否则当前路径最后一段是否匹配 PATH_SEGMENT_MARKERS（如 ``os-copilot``，常见于 ``/usr/share/os-copilot/skills``）。
    命中即返回对应来源标识；同一层内 DIR_MARKERS 优先于路径段。
    """
    cur = (start or Path.cwd()).resolve()
    for _ in range(max_depth):
        for dirname, source in DIR_MARKERS:
            if (cur / dirname).exists():
                return source
        for segment, source in PATH_SEGMENT_MARKERS:
            if cur.name == segment:
                return source
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


def resolve_diagnosis_source() -> Tuple[Optional[str], str]:
    """
    决定本次 Invoke 是否写入 params['__sysom_diagnosis_source']。

    - 未设置环境变量：仅根据当前工作目录向上启发式推断（内建）。
    - 已设置 ``SYSOM_DIAGNOSIS_SOURCE`` 或 ``OSOPS_DIAGNOSIS_SOURCE``（非空）：
      使用该值，**不再**做 cwd 启发式（覆盖自动识别）。
      值为 ``-`` / ``off`` / ``none`` 等（见 _DISABLE_SENTINELS）时：**不注入** 该字段（完全屏蔽）。

    Returns:
        (value_or_none, provenance) provenance ∈ {env, cwd, none, disabled}
    """
    raw = os.environ.get("SYSOM_DIAGNOSIS_SOURCE") or os.environ.get("OSOPS_DIAGNOSIS_SOURCE")
    env = (raw or "").strip()
    if env:
        if env.lower() in _DISABLE_SENTINELS:
            return None, "disabled"
        return env, "env"

    inferred = infer_diagnosis_source_from_cwd()
    if inferred:
        return inferred, "cwd"

    return None, "none"
