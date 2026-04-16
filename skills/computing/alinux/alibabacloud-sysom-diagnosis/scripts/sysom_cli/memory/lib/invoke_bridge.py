# -*- coding: utf-8 -*-
"""memory 子命令可选地复用 SysOM 专项后端（与 io / net / load 专项子命令同一实现）。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict

from sysom_cli.lib.diagnosis_backend import get_diagnosis_backend, namespace_for_diagnosis_invoke

# 供测试或需直接构造 Namespace 的场景
__all__ = ["namespace_for_diagnosis_invoke", "run_deep_diagnosis_invoke"]


def run_deep_diagnosis_invoke(
    service_name: str,
    ns: Namespace,
    *,
    skip_precheck: bool = False,
) -> Dict[str, Any]:
    """
    skip_precheck: 为 True 时跳过 run_precheck（调用方已在 execute(REMOTE) 等路径做过门禁）。
    """
    if not skip_precheck:
        from sysom_cli.lib.precheck_gate import remote_precheck_gate

        ok_gate, fail_env = remote_precheck_gate()
        if not ok_gate:
            return fail_env  # type: ignore[return-value]
    return get_diagnosis_backend().invoke_specialty(service_name, ns)
