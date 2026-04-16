# -*- coding: utf-8 -*-
"""diagnosis invoke / io|net|load 专项：routing、remote、data_refs、紧凑/verbose。"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict, List, Optional


def ensure_findings_finding_type(findings: Optional[List[Dict[str, Any]]]) -> None:
    """为 findings 补全 finding_type（precheck：severity；memory：kind）。"""
    if not findings:
        return
    for f in findings:
        if not isinstance(f, dict):
            continue
        if "finding_type" in f:
            continue
        if "severity" in f:
            f["finding_type"] = f"precheck_{f.get('severity', 'info')}"
        elif "kind" in f:
            f["finding_type"] = f["kind"]


def finalize_diagnosis_invoke_envelope(
    out: Dict[str, Any],
    ns: Namespace,
    *,
    cli_subsystem: Optional[str] = None,
) -> Dict[str, Any]:
    """
    - 写入 data.routing、data.remote（与 memory --deep-diagnosis 同形）
    - 成功时业务结果仅在 data.remote.result（不再写顶层 data.result）
    - 不写 data.next_steps；invoke 无内存式「下一步」列表
    - agent：data_refs、data_field_guide；错误时不改 summary
    """
    if out.get("action") != "diagnosis_invoke":
        return out

    data = out.setdefault("data", {})
    agent = out.setdefault("agent", {})
    ok = bool(out.get("ok"))

    svc = (data.get("service_name") or "").strip()
    ch = (data.get("channel") or "").strip() or "ecs"
    reg = (data.get("region") or "").strip()
    tid = (data.get("task_id") or "").strip() or None

    routing: Dict[str, Any] = {
        "recommended_service_name": svc,
        "channel": ch,
        "region": reg,
    }
    if tid:
        routing["task_id"] = tid
    data["routing"] = routing

    remote: Dict[str, Any] = {
        "ok": ok,
        "action": "diagnosis_invoke",
        "service_name": svc,
        "channel": ch,
        "region": reg,
    }
    if tid:
        remote["task_id"] = tid
    if "ecs_metadata_filled" in data:
        remote["ecs_metadata_filled"] = data["ecs_metadata_filled"]
    if "diagnosis_source_origin" in data:
        remote["diagnosis_source_origin"] = data["diagnosis_source_origin"]
    if data.get("diagnosis_source"):
        remote["diagnosis_source"] = data["diagnosis_source"]

    if ok:
        # 与 invoke 约定一致：成功时始终暴露 data.remote.result（可为 null），便于 Agent 稳定读取
        prev_remote = data.get("remote") if isinstance(data.get("remote"), dict) else {}
        if "result" in data:
            remote["result"] = data.pop("result")
        elif "result" in prev_remote:
            # 幂等：已被 finalize 过且顶层 result 已 pop 时，保留原 remote.result
            remote["result"] = prev_remote.get("result")
        else:
            remote["result"] = None
    else:
        if out.get("error"):
            remote["error"] = out["error"]

    data["remote"] = remote
    data.pop("next_steps", None)

    ensure_findings_finding_type(agent.get("findings") or [])

    refs: List[str] = [
        "data.routing.recommended_service_name",
        "data.routing.region",
        "data.remote",
    ]
    guides: List[Dict[str, Any]] = [
        {
            "pointer": "data.routing.recommended_service_name",
            "label_zh": "专项名",
            "meaning_zh": "本次调用的 SysOM service_name（OpenAPI）。",
            "reading_zh": "与 data.remote.service_name 一致。",
        },
        {
            "pointer": "data.remote",
            "label_zh": "深度诊断结果壳",
            "meaning_zh": "ok、task_id、result、error 等与内存域 data.remote 同形。",
            "reading_zh": "成功时读 data.remote.result；失败时读 data.remote.error 与 agent.summary。",
        },
    ]
    if ok:
        refs.append("data.remote.result")
        guides.append(
            {
                "pointer": "data.remote.result",
                "label_zh": "API 业务结果",
                "meaning_zh": "GetDiagnosisResult 返回的专项载荷（形态随 service_name 变化）。",
                "reading_zh": (
                    "仅此一处；无顶层 data.result。"
                    "若对象内含 _sysom_cli_note_zh，表示未命中标准 result 字段，已尽力从兄弟键聚合或给出键名提示。"
                ),
            }
        )
    agent["data_refs"] = refs
    agent["data_field_guide"] = guides

    exec_ = dict(out.get("execution") or {})
    if cli_subsystem:
        exec_["subsystem"] = cli_subsystem
        exec_.setdefault("mode", "remote")
    out["execution"] = exec_

    if out.get("error") is not None:
        return out

    verbose = bool(getattr(ns, "verbose_envelope", False))
    if verbose:
        if not (agent.get("summary") or "").strip():
            agent["summary"] = (
                f"诊断完成：service_name={svc} task_id={tid or '(无)'} region={reg}"
            )
    else:
        domain = (cli_subsystem or "invoke").lower()
        res = remote.get("result") if ok else None
        if ok and isinstance(res, dict) and res.get("_sysom_cli_note_zh"):
            agent["summary"] = (
                f"深度诊断（{domain}）已完成；服务端返回体未含可解析的标准 result，"
                "已写入占位说明与 _raw_data_keys，请读 data.remote.result。"
            )
        else:
            agent["summary"] = (
                f"深度诊断（{domain}，紧凑输出）。请读 data.remote.result（成功时）。"
            )
        agent["next"] = []

    return out
