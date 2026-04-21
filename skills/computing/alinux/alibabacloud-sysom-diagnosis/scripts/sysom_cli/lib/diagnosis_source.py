# -*- coding: utf-8 -*-
"""内建注入 __sysom_diagnosis_source：固定值 skill_hub。"""
from __future__ import annotations

from typing import Optional, Tuple

__all__ = [
    "DIAGNOSIS_SOURCE_KEY",
    "LEGACY_DIAGNOSIS_SOURCE_KEYS",
    "resolve_diagnosis_source",
]

# 写入 OpenAPI params 的键名（旧名 $diagnosis_source 会被网关/后端拦截，勿再用）
DIAGNOSIS_SOURCE_KEY = "__sysom_diagnosis_source"

# 历史上曾注入的键，invoke 前会从 params 中剔除，避免残留进请求体
LEGACY_DIAGNOSIS_SOURCE_KEYS: Tuple[str, ...] = ("$diagnosis_source",)

def resolve_diagnosis_source() -> Tuple[Optional[str], str]:
    """
    固定写入 params['__sysom_diagnosis_source'] = ``skill_hub``。
    不再基于 cwd 启发式推断，也不再读取环境变量覆盖/关闭。

    Returns:
        (value, provenance) provenance = ``fixed``
    """
    return "skill_hub", "fixed"
