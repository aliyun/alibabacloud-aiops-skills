# -*- coding: utf-8 -*-
"""发起诊断：InvokeDiagnosis + 轮询 GetDiagnosisResult（仅远程）。

不作为 CLI 子命令注册；由 ``lib.diagnosis_backend`` 与专项子命令在内部调用。
"""
from __future__ import annotations

import asyncio
import json
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sysom_cli.core.base import ExecutionMode, RemoteOnlyCommand
from sysom_cli.core.registry import CommandRegistry
from sysom_cli.lib.diagnosis_helper import (
    DiagnoseResultCode,
    DiagnosisMCPHelper,
    DiagnosisRequest,
    DiagnosisResponse,
)
from sysom_cli.lib.diagnosis_source import (
    DIAGNOSIS_SOURCE_KEY,
    LEGACY_DIAGNOSIS_SOURCE_KEYS,
    resolve_diagnosis_source,
)
from sysom_cli.lib.ecs_metadata import get_ecs_metadata
from sysom_cli.lib.guidance import diagnosis_subsystem_minimal_guidance
from sysom_cli.lib.invoke_envelope_finalize import finalize_diagnosis_invoke_envelope
from sysom_cli.lib.schema import agent_block, envelope
from sysom_cli.memory.lib.oom_quick import normalize_oomcheck_time_param


def _diagnosis_hint_for_invoke_failure(resp: DiagnosisResponse) -> str:
    """根据 InvokeDiagnosis 返回的原始 code/message 给出补充说明（避免误导向「仅控制台授权」）。"""
    raw_msg = resp.message or ""
    text = f"{raw_msg} {resp.api_business_code}".lower()
    msg_lower = raw_msg.lower()

    if "notowninstance" in text or "not belong" in text or "不属于" in raw_msg:
        return (
            "当前凭证所属账号与 params 中的 instance/region 不匹配（例如本机元数据补全的实例不属于当前 AK/SK 账号）。"
            "请改用该实例所属账号的凭证，或请用户明确选择「远程实例」并提供正确的 region/instance；"
            "勿用本机元数据去诊断其它账号下的机器。"
        )

    # InvalidParameter 常合并多种校验失败；须先于泛化 InvalidParameter 分支匹配
    if "instance not found" in msg_lower or "instance not found in ecs" in msg_lower:
        return (
            "服务端提示在指定地域下未查询到该 ECS 实例（文案前缀如「不支持的系统版本」多为合并错误类说明，未必表示 OS 版本问题）。"
            "常见真实原因：本机元数据中的 instance 不属于当前 AK/SK 所属账号、region/instance 与控制台不一致、或实例已释放。"
            "请改用目标实例所属账号的凭证，或由用户提供远程实例的 region 与 instance-id。"
        )

    if "sysom.invalidparameter" in text or "invalidparameter" in text:
        return (
            "参数或诊断项与地域/实例要求不一致。请核对 region、instance、service_name 与各 diagnoses 专文；"
            "并确认实例属于当前凭证账号。"
        )

    if "notexists" in text or "not found" in text or "未查询到实例" in raw_msg:
        return "请确认 instance-id、region 是否正确，且实例存在于当前凭证所属账号。"

    return (
        "若未对实例做诊断授权，请在阿里云 SysOM 或 ECS 控制台为目标实例完成诊断授权"
        "（勿调用已废弃的 OpenAPI 授权接口）。"
    )


def _include_console_authorization_extra_hint(resp: DiagnosisResponse) -> bool:
    """是否附加「控制台诊断授权」类 remediation 尾句（实例归属错误时不应喧宾夺主）。"""
    raw_msg = resp.message or ""
    text = f"{raw_msg} {resp.api_business_code}".lower()
    msg_lower = raw_msg.lower()
    if "notowninstance" in text or "not belong" in text:
        return False
    if "notexists" in text or "not found" in text:
        return False
    if "instance not found" in msg_lower:
        return False
    if "sysom.invalidparameter" in text or "invalidparameter" in text:
        return False
    return True


def _fill_params_from_ecs_metadata(params: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """若未显式提供 region / instance，尝试从 ECS 元数据服务补全（仅本机跑在 ECS 内网时可用）。"""
    filled: list[str] = []
    reg = (params.get("region") or "").strip()
    if not reg:
        r = get_ecs_metadata("region-id", timeout=3.0)
        if r.get("ok") and (r.get("text") or "").strip():
            params["region"] = str(r["text"]).strip()
            filled.append("region")
    inst = (params.get("instance") or "").strip()
    if not inst:
        i = get_ecs_metadata("instance-id", timeout=3.0)
        if i.get("ok") and (i.get("text") or "").strip():
            params["instance"] = str(i["text"]).strip()
            filled.append("instance")
    return params, filled


def _load_params(ns: Namespace) -> Dict[str, Any]:
    raw = getattr(ns, "params", None)
    path = getattr(ns, "params_file", None)
    if raw and str(raw).strip():
        return json.loads(str(raw))
    if path:
        p = Path(str(path))
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


class DiagnosisInvokeCommand(RemoteOnlyCommand):
    """远程诊断发起命令"""

    @property
    def command_name(self) -> str:
        return "invoke"

    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: False,
            ExecutionMode.REMOTE: True,
            ExecutionMode.HYBRID: False,
        }

    def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
        def _out(**kwargs: Any) -> Dict[str, Any]:
            svc = str(getattr(ns, "service_name", "") or "").strip()
            sub = CommandRegistry.get_subsystem(svc) if svc else None
            return finalize_diagnosis_invoke_envelope(
                envelope(**kwargs), ns, cli_subsystem=sub
            )

        try:
            params = _load_params(ns)
        except (json.JSONDecodeError, OSError, TypeError) as e:
            return _out(
                action="diagnosis_invoke",
                ok=False,
                agent=agent_block("error", f"解析 params 失败: {e}"),
                error={"code": "invalid_params", "message": str(e)},
                data=diagnosis_subsystem_minimal_guidance(),
                execution={"subsystem": "invoke", "mode": "remote"},
            )

        inst = getattr(ns, "instance", None)
        reg = getattr(ns, "region", None)
        if inst:
            params["instance"] = str(inst).strip()
        if reg:
            params["region"] = str(reg).strip()

        params, metadata_filled = _fill_params_from_ecs_metadata(params)

        # 内建来源字段：不由用户 params 传入；见 diagnosis_source.resolve_diagnosis_source
        for _k in LEGACY_DIAGNOSIS_SOURCE_KEYS:
            params.pop(_k, None)
        params.pop(DIAGNOSIS_SOURCE_KEY, None)
        src, src_origin = resolve_diagnosis_source()
        if src:
            params[DIAGNOSIS_SOURCE_KEY] = src

        region = (params.get("region") or "").strip()
        if not region:
            return _out(
                action="diagnosis_invoke",
                ok=False,
                agent=agent_block(
                    "error",
                    "params 中缺少 region。若诊断本机 ECS：在实例内执行深度诊断命令且省略 --region/--instance，由 CLI 从元数据补全。"
                    "若诊断远程实例：须由用户提供目标 --region，禁止 Agent 自行 curl 元数据。",
                ),
                error={"code": "missing_region", "message": "region 必填"},
                data=diagnosis_subsystem_minimal_guidance(),
                execution={"subsystem": "invoke", "mode": "remote"},
            )

        if not (params.get("instance") or "").strip():
            return _out(
                action="diagnosis_invoke",
                ok=False,
                agent=agent_block(
                    "error",
                    "params 中缺少 instance。若诊断本机 ECS：在实例内执行深度诊断命令且省略 --region/--instance，由 CLI 从元数据补全。"
                    "若诊断远程实例：须由用户提供目标 --instance，禁止 Agent 自行 curl 元数据。",
                ),
                error={"code": "missing_instance", "message": "instance 必填"},
                data=diagnosis_subsystem_minimal_guidance(),
                execution={"subsystem": "invoke", "mode": "remote"},
            )

        service_name = str(getattr(ns, "service_name", "")).strip()
        channel = str(getattr(ns, "channel", "ecs") or "ecs").strip()
        timeout = int(getattr(ns, "timeout", 300) or 300)
        poll_interval = int(getattr(ns, "poll_interval", 1) or 1)

        if service_name == "oomcheck":
            tv = params.get("time")
            if tv is not None and str(tv).strip() != "":
                params["time"] = normalize_oomcheck_time_param(str(tv))

        req = DiagnosisRequest(
            service_name=service_name,
            channel=channel,
            region=region,
            params=params,
        )

        helper = DiagnosisMCPHelper(timeout=timeout, poll_interval=poll_interval)

        try:
            resp: DiagnosisResponse = asyncio.run(helper.execute(req))
        except Exception as e:  # noqa: BLE001
            return _out(
                action="diagnosis_invoke",
                ok=False,
                agent=agent_block("error", str(e)[:500]),
                error={"code": "invoke_exception", "message": str(e)},
                data=diagnosis_subsystem_minimal_guidance(),
                execution={"subsystem": "invoke", "mode": "remote"},
            )

        if resp.code != DiagnoseResultCode.SUCCESS:
            msg = (resp.message or "").strip() or resp.code
            hint = _diagnosis_hint_for_invoke_failure(resp)
            api_code = (resp.api_business_code or "").strip()
            err_code = api_code or resp.code
            dg = diagnosis_subsystem_minimal_guidance(
                include_console_authorization_hint=_include_console_authorization_extra_hint(
                    resp
                ),
            )
            data_out: Dict[str, Any] = {
                "service_name": service_name,
                "channel": channel,
                "region": region,
                "ecs_metadata_filled": metadata_filled,
                "diagnosis_source_origin": src_origin,
                **dg,
            }
            if src:
                data_out["diagnosis_source"] = src
            if (resp.task_id or "").strip():
                data_out["task_id"] = resp.task_id.strip()
            err: Dict[str, Any] = {"code": err_code, "message": msg}
            if (resp.api_request_id or "").strip():
                err["request_id"] = resp.api_request_id.strip()
            return _out(
                action="diagnosis_invoke",
                ok=False,
                agent=agent_block("error", f"{msg}。{hint}"),
                error=err,
                data=data_out,
                execution={"subsystem": "invoke", "mode": "remote"},
            )

        return _out(
            action="diagnosis_invoke",
            ok=True,
            agent=agent_block(
                "normal",
                f"诊断完成 task_id={resp.task_id}",
            ),
            data={
                "task_id": resp.task_id,
                "service_name": service_name,
                "channel": channel,
                "region": region,
                "result": resp.result,
                "ecs_metadata_filled": metadata_filled,
                "diagnosis_source_origin": src_origin,
                **({"diagnosis_source": src} if src else {}),
            },
            execution={"subsystem": "invoke", "mode": "remote", "phase": "invoke_diagnosis"},
        )
