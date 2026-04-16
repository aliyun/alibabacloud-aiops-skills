# -*- coding: utf-8 -*-
"""memory 域 stdout 信封后处理：routing/local、扁平 remote；下一步仅在 agent.next。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict, List, Optional


from sysom_cli.lib.invoke_envelope_finalize import ensure_findings_finding_type


_ROUTING_KEYS = (
    "recommended_service_name",
    "confidence",
    "primary_reason_zh",
    "categories",
    "category_labels_zh",
    "oom_signal",
    "hit_count",
    "java_signal",
    "go_signal",
)
_LOCAL_KEYS = ("facts", "oom_local", "meminfo_facts", "rss_top_sample")

# 输出时从 data 根剥离的冗余字段（静态描述/与 agent 重复/已在 summary 中）
_DATA_STRIP_KEYS = ("remote_analysis_value", "quick_analysis", "oom_diagnosis_cli_hints_zh")

# oom_local 中仅供内部逻辑、不需输出给 Agent 的调试字段
_OOM_LOCAL_STRIP_KEYS = (
    "oom_lines_total",
    "extraction_mode",
    "parsed_time_count",
    "unparsed_wallclock_count",
    "dmesg_relative_line_count",
    "relative_boot_seconds_sample",
    "source_note_zh",
)


def _build_routing(data: Dict[str, Any]) -> Dict[str, Any]:
    routing: Dict[str, Any] = {}
    for k in _ROUTING_KEYS:
        if k in data:
            routing[k] = data[k]
    return routing


def _build_local(data: Dict[str, Any]) -> Dict[str, Any]:
    local: Dict[str, Any] = {}
    for k in _LOCAL_KEYS:
        if k in data:
            local[k] = data[k]
    return local


def _strip_verbose_output(data: Dict[str, Any]) -> None:
    """输出前剥离冗余字段：静态描述、与 agent 重复字段、oom_local 调试字段。"""
    for k in _DATA_STRIP_KEYS:
        data.pop(k, None)
    oom_local = (data.get("local") or {}).get("oom_local")
    if isinstance(oom_local, dict):
        for k in _OOM_LOCAL_STRIP_KEYS:
            oom_local.pop(k, None)


def _invoke_data_coalesce(idata: Dict[str, Any], key: str) -> Any:
    """DiagnosisInvoke 信封经 finalize 后，业务字段常在 data.remote；合并时两边都读。"""
    v = idata.get(key)
    if v is not None:
        return v
    nested = idata.get("remote")
    if isinstance(nested, dict):
        return nested.get(key)
    return None


def merge_deep_diagnosis_flat(
    out: Dict[str, Any],
    inv: Dict[str, Any],
    *,
    service_name: str,
) -> None:
    """将远程专项调用结果写入 data.remote，不再嵌套整包子信封。"""
    data = out.setdefault("data", {})
    data.pop("deep_diagnosis", None)
    idata = inv.get("data") if isinstance(inv.get("data"), dict) else {}
    # finalize_diagnosis_invoke_envelope 会把 result 挪到 data.remote 并 pop 顶层 result
    nested_remote = idata.get("remote") if isinstance(idata.get("remote"), dict) else {}
    merged_result = idata.get("result")
    if merged_result is None and nested_remote:
        merged_result = nested_remote.get("result")
    remote: Dict[str, Any] = {
        "ok": bool(inv.get("ok")),
        "action": inv.get("action"),
        "service_name": service_name,
        "task_id": _invoke_data_coalesce(idata, "task_id"),
        "channel": _invoke_data_coalesce(idata, "channel"),
        "region": _invoke_data_coalesce(idata, "region"),
        "result": merged_result,
        "ecs_metadata_filled": _invoke_data_coalesce(idata, "ecs_metadata_filled"),
        "diagnosis_source_origin": _invoke_data_coalesce(idata, "diagnosis_source_origin"),
    }
    ds = _invoke_data_coalesce(idata, "diagnosis_source")
    if ds:
        remote["diagnosis_source"] = ds
    if inv.get("error"):
        remote["error"] = inv["error"]
    data["remote"] = remote


def finalize_memory_envelope(
    out: Dict[str, Any],
    ns: Namespace,
    *,
    verbose_summary: str,
) -> Dict[str, Any]:
    """
    - 写入 data.routing、data.local；并从 data 根删除已收入二者的键
    - 移除 data.next_steps（若存在）；**下一步动作以 agent.next 为准**（由各 command 写入，含 action_kind）
    - quick_analysis 中与 oom_local 重复项改为 detail_pointers
    - agent：data_refs、data_field_guide；**不覆盖 agent.next**（成功路径）；仅按 verbose 切换 summary
    """
    data = out.setdefault("data", {})
    agent = out.setdefault("agent", {})

    routing = _build_routing(data)
    if routing:
        data["routing"] = routing
        for k in routing:
            data.pop(k, None)

    local = _build_local(data)
    if local:
        data["local"] = local
        for k in local:
            data.pop(k, None)

    data.pop("read_next", None)
    data.pop("next_analysis", None)
    data.pop("follow_up", None)
    data.pop("next_steps", None)

    _strip_verbose_output(data)

    ensure_findings_finding_type(agent.get("findings") or [])

    # 深度诊断等失败时保留上游已写入的 agent.summary / agent.next
    if out.get("error") is not None:
        return out

    remote = data.get("remote")
    remote_ok = (
        isinstance(remote, dict)
        and bool(remote.get("ok"))
        and bool(out.get("ok"))
    )
    if isinstance(remote, dict):
        exec_ = dict(out.get("execution") or {})
        exec_["phase"] = "invoke_diagnosis"
        out["execution"] = exec_

    verbose = bool(getattr(ns, "verbose_envelope", False))
    if remote_ok:
        if verbose:
            if (verbose_summary or "").strip():
                agent["summary"] = verbose_summary
            else:
                tid = (remote.get("task_id") or "").strip() if isinstance(remote, dict) else ""
                agent["summary"] = (
                    f"深度诊断已完成（紧凑 verbose 未提供摘要）。task_id={tid or '(无)'}；详见 data.remote。"
                )
        else:
            res = remote.get("result") if isinstance(remote, dict) else None
            if isinstance(res, dict) and res.get("_sysom_cli_note_zh"):
                agent["summary"] = (
                    "深度诊断调用已成功；服务端未返回标准 result 字段，说明与 _raw_data_keys 见 data.remote.result；"
                    "task_id 见 data.remote.task_id。勿再重复发起同一条 --deep-diagnosis 命令。"
                )
            elif res is not None:
                agent["summary"] = (
                    "深度诊断调用已成功。业务载荷见 data.remote.result；"
                    "task_id 见 data.remote.task_id。勿再重复发起同一条 --deep-diagnosis 命令。"
                )
            else:
                agent["summary"] = (
                    "深度诊断调用已成功但 data.remote.result 为 null。"
                    "请凭 data.remote.task_id 在控制台或后续 API 查询；勿再重复发起同一条 --deep-diagnosis 命令。"
                )
        agent["next"] = []
    elif verbose:
        agent["summary"] = verbose_summary
    else:
        agent["summary"] = (
            "OOM 信号已检出，本机初步发现见 agent.findings 和 data.local。"
            "请向用户展示本机发现，并执行 agent.next 中的命令获取深度诊断结果。"
        )

    return out
