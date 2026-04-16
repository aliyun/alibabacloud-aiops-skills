# -*- coding: utf-8 -*-
"""SysOM 专项后端接缝：默认走 DiagnosisInvokeCommand，可替换为异步任务等实现。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from argparse import Namespace
from typing import Any, Dict

from sysom_cli.diagnosis.invoke.command import DiagnosisInvokeCommand


def namespace_for_diagnosis_invoke(service_name: str, ns: Namespace) -> Namespace:
    """从任意子命令 Namespace 构造 invoke 所需参数。"""
    return Namespace(
        service_name=service_name,
        channel=str(getattr(ns, "channel", None) or "ecs").strip() or "ecs",
        params=getattr(ns, "params", None),
        params_file=getattr(ns, "params_file", None),
        instance=getattr(ns, "instance", None),
        region=getattr(ns, "region", None),
        timeout=int(getattr(ns, "timeout", 300) or 300),
        poll_interval=int(getattr(ns, "poll_interval", 1) or 1),
        verbose_envelope=bool(getattr(ns, "verbose_envelope", False)),
    )


class DiagnosisBackend(ABC):
    """发起 SysOM 专项（当前默认：InvokeDiagnosis + 轮询）。"""

    @abstractmethod
    def invoke_specialty(self, service_name: str, ns: Namespace) -> Dict[str, Any]:
        ...


class DefaultDiagnosisBackend(DiagnosisBackend):
    def invoke_specialty(self, service_name: str, ns: Namespace) -> Dict[str, Any]:
        invoke_ns = namespace_for_diagnosis_invoke(service_name, ns)
        return DiagnosisInvokeCommand().execute_remote(invoke_ns)


_default_backend: DiagnosisBackend | None = None


def get_diagnosis_backend() -> DiagnosisBackend:
    global _default_backend
    if _default_backend is None:
        _default_backend = DefaultDiagnosisBackend()
    return _default_backend


def set_diagnosis_backend(backend: DiagnosisBackend | None) -> None:
    """测试或替换实现时注入。"""
    global _default_backend
    _default_backend = backend
