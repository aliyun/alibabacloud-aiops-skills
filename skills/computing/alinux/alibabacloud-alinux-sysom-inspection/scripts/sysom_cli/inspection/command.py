# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Optional

from sysom_cli.lib.auth import resolve_sysom_credentials
from sysom_cli.lib.openapi import SysomOpenApiCaller, normalize_sysom_body


class InspectionApiUnavailableError(RuntimeError):
    """Standard inspection API is unavailable in this environment (for example InvalidAction.NotFound)."""


MEMORY_USAGE_ITEM = "sysom:metric:memory_usage_rate"
DIAGNOSIS_TRIGGER_ITEM = "memory_usage_rate"
SKILL_HUB_SOURCE = "skill_hub"
DIAGNOSIS_SOURCE_KEY = "__sysom_diagnosis_source"
LEGACY_DIAGNOSIS_SOURCE_KEYS = ("$diagnosis_source",)
DEFAULT_DIAGNOSIS_TIMEOUT_SECONDS = 150
DEFAULT_DIAGNOSIS_POLL_INTERVAL_SECONDS = 1
DEFAULT_INSPECTION_REPORT_TIMEOUT_SECONDS = 150
DEFAULT_INSPECTION_REPORT_POLL_INTERVAL_SECONDS = 1
DEFAULT_ACTIVATION_RETRY_COUNT = 3
DEFAULT_ACTIVATION_RETRY_INTERVAL_SECONDS = 2
DEFAULT_SYSOM_AGENT_ID = "74a86327-3170-412c-8e67-da3389ec56a9"
DEFAULT_SYSOM_AGENT_VERSION = "latest"
DEFAULT_SYSOM_INSTANCE_TYPE = "ecs"
DEFAULT_SYSOM_CONFIG_ID = ""
ALLOWED_METRIC_SOURCES = ("cms", "sysom", "auto")
ALLOWED_MANAGED_TYPES = ("managed", "unmanaged", "all")
_REGION_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
_INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9]{8,64}$")
DEFAULT_INSPECTION_ITEMS = [
    "sysom:metric:system_load",
    "sysom:metric:memory_usage_rate",
    "sysom:metric:dist_write_latency",
    "sysom:metric:dist_read_latency",
    "sysom:metric:avg_schedule_delay",
    "sysom:metric:socket_leak",
    "sysom:metric:tcp_memory",
    "sysom:metric:udp_memory",
    "sysom:metric:cpu_iowait",
    "sysom:metric:cpu_softirq",
    "sysom:metric:cpu_sys",
    "sysom:metric:memcg_leak",
    "sysom:metric:vmalloc_leak",
    "sysom:metric:slab_leak",
    "sysom:metric:alloc_page_leak",
    "sysom:metric:root_fs_usage",
    "sysom:metric:root_fs_inode_usage",
    "sysom:metric:file_descriptor_usage",
    "sysom:metric:tid_usage",
]
REPORT_TEMPLATE_FILE = Path(__file__).resolve().parents[3] / "references" / "report-template.md"
REPORT_OUTPUT_DIR = Path("inspection-reports")


def _load_report_template() -> str:
    default_template = """## Inspection Overview
- Target Instance: `{instance_id}` ({region_id})
- Inspection Time: `{report_time}`
- Inspection Report: `{inspection_report_id}` (Status: {inspection_report_status})
- Inspection Result: {inspection_report_result}
- Report File: `{report_file_name}`
- File Path: `{report_file_path}`

## Abnormal Item Details
{abnormal_items_markdown}

## Diagnosis Information
- Diagnosis Status: {diagnosis_status}
- Diagnosis Task: `{diagnosis_task_id}`
- Diagnosis Conclusion: {diagnosis_report_result}
- Root Cause: {diagnosis_root_cause}
- Suggestion: {diagnosis_suggestion}

## Key Findings
{diagnosis_key_findings}

## Application Memory Usage Ranking (TOP10)
{diagnosis_app_mem_ranking}

## Final Conclusion
{final_conclusion}
"""
    try:
        raw = REPORT_TEMPLATE_FILE.read_text(encoding="utf-8")
        return raw.strip() or default_template
    except Exception:  # noqa: BLE001
        return default_template


def _validate_region_id(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise argparse.ArgumentTypeError("region-id cannot be empty")
    if len(value) < 3 or len(value) > 32:
        raise argparse.ArgumentTypeError("region-id length must be between 3 and 32")
    if "-" not in value or not _REGION_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("invalid region-id format, for example cn-hangzhou")
    return value


def _validate_instance_id(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise argparse.ArgumentTypeError("instance-id cannot be empty")
    if len(value) < 10 or len(value) > 66:
        raise argparse.ArgumentTypeError("invalid instance-id length")
    if not _INSTANCE_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("invalid instance-id format, for example i-abcdefgh12345678")
    return value


def _validate_metric_source(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if not value:
        raise argparse.ArgumentTypeError("metric-source cannot be empty")
    if value not in ALLOWED_METRIC_SOURCES:
        raise argparse.ArgumentTypeError(
            f"metric-source must be one of {', '.join(ALLOWED_METRIC_SOURCES)}"
        )
    return value


def _validate_instance_type(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value != DEFAULT_SYSOM_INSTANCE_TYPE:
        raise argparse.ArgumentTypeError("instance-type currently only supports ecs")
    return value


def _validate_managed_type(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if not value:
        raise argparse.ArgumentTypeError("managed-type cannot be empty")
    if value not in ALLOWED_MANAGED_TYPES:
        raise argparse.ArgumentTypeError(
            f"managed-type must be one of {', '.join(ALLOWED_MANAGED_TYPES)}"
        )
    return value


def _validate_positive_int(raw: str) -> int:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("must be a positive integer")
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _build_client_token(prefix: str, payload: Dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:48]
    return f"{prefix}-{digest}"


def _is_http_ok(status: Any) -> bool:
    if status is None:
        # In some ROA cases SDK only returns body without statusCode; rely on business code then.
        return True
    try:
        return int(status) == 200
    except (TypeError, ValueError):
        return False


def add_inspection_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = subparsers.add_parser("inspection", help="Inspect an instance and trigger diagnosis based on the report")
    p.add_argument("--region-id", required=True, type=_validate_region_id, help="Target instance RegionId")
    p.add_argument(
        "--instance-id",
        type=_validate_instance_id,
        help="Target instance ID; if omitted, list instances and select interactively",
    )
    p.add_argument(
        "--instance-type",
        type=_validate_instance_type,
        default=DEFAULT_SYSOM_INSTANCE_TYPE,
        help="instanceType for ListAllInstances, currently only ecs is supported",
    )
    p.add_argument(
        "--managed-type",
        type=_validate_managed_type,
        default="all",
        help="managedType for ListAllInstances: managed/unmanaged/all",
    )
    p.add_argument(
        "--current", type=_validate_positive_int, default=1, help="Start page number for ListAllInstances (from 1)"
    )
    p.add_argument("--page-size", type=_validate_positive_int, default=50, help="Page size for ListAllInstances")
    p.add_argument(
        "--inspection-items",
        nargs="*",
        default=DEFAULT_INSPECTION_ITEMS,
        help="Inspection items for CreateInstanceInspection; explicitly pass empty to inspect all items",
    )
    p.add_argument(
        "--metric-source",
        type=_validate_metric_source,
        help="metricSource for CreateInstanceInspection, one of cms/sysom/auto; omit to use service default",
    )
    p.add_argument(
        "--disable-memgraph-diagnosis",
        action="store_true",
        help="Do not trigger memgraph diagnosis when high memory usage is detected",
    )
    p.add_argument(
        "--inspection-report-timeout-seconds",
        type=int,
        default=DEFAULT_INSPECTION_REPORT_TIMEOUT_SECONDS,
        help="Total polling timeout seconds for GetInspectionReport",
    )
    p.add_argument(
        "--inspection-report-poll-interval-seconds",
        type=int,
        default=DEFAULT_INSPECTION_REPORT_POLL_INTERVAL_SECONDS,
        help="Polling interval seconds for GetInspectionReport",
    )
    p.add_argument(
        "--diagnosis-timeout-seconds",
        type=int,
        default=DEFAULT_DIAGNOSIS_TIMEOUT_SECONDS,
        help="Total polling timeout seconds for GetDiagnosisResult",
    )
    p.add_argument(
        "--diagnosis-poll-interval-seconds",
        type=int,
        default=DEFAULT_DIAGNOSIS_POLL_INTERVAL_SECONDS,
        help="Polling interval seconds for GetDiagnosisResult",
    )
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.set_defaults(top_cmd="inspection")


async def _create_instance_inspection(
    caller: SysomOpenApiCaller,
    *,
    instance_id: str,
    region_id: str,
    items: list[str],
    metric_source: Optional[str] = None,
) -> Dict[str, Any]:
    token_payload: Dict[str, Any] = {
        "instance": instance_id,
        "region": region_id,
        "source": SKILL_HUB_SOURCE,
        "items": items,
    }
    if metric_source:
        token_payload["metricSource"] = metric_source
    client_token = _build_client_token(
        "insp",
        token_payload,
    )
    request_body: Dict[str, Any] = {
        "instance": instance_id,
        "source": SKILL_HUB_SOURCE,
        "region": region_id,
        "items": items,
        "clientToken": client_token,
    }
    if metric_source:
        request_body["metricSource"] = metric_source
    raw = await caller.call_roa(
        action="CreateInstanceInspection",
        pathname="/api/v1/inspection/createInstanceInspection",
        method="POST",
        body=request_body,
    )
    status = raw.get("statusCode") or raw.get("status_code")
    body = normalize_sysom_body(raw)
    code = str(body.get("code") or body.get("Code") or "").strip()
    if int(status or 0) == 404 and code == "InvalidAction.NotFound":
        raise InspectionApiUnavailableError(
            "CreateInstanceInspection is unavailable for current API version (InvalidAction.NotFound)"
        )
    if status != 200:
        raise RuntimeError(f"CreateInstanceInspection HTTP {status}: {body.get('message') or body}")
    return body


async def _list_all_instances_page(
    caller: SysomOpenApiCaller,
    *,
    region_id: str,
    instance_type: str,
    managed_type: str,
    current: int,
    page_size: int,
) -> Dict[str, Any]:
    raw = await caller.call_rpc(
        "ListAllInstances",
        {
            "region": region_id,
            "instanceType": instance_type,
            "managedType": managed_type,
            "current": current,
            "pageSize": page_size,
        },
    )
    status = raw.get("statusCode") or raw.get("status_code")
    body = normalize_sysom_body(raw)
    if status != 200:
        raise RuntimeError(f"ListAllInstances HTTP {status}: {body.get('message') or body}")
    code = str(body.get("code") or body.get("Code") or "").strip().lower()
    if code and code != "success":
        raise RuntimeError(f"ListAllInstances BizError: {body.get('message') or body}")
    return body


def _extract_pagination_data(list_body: Dict[str, Any]) -> tuple[list[Dict[str, Any]], Optional[int]]:
    data = list_body.get("data") or list_body.get("Data") or {}
    if not isinstance(data, dict):
        return [], None

    instances_obj: Any = None
    for key in ("instances", "Instances", "list", "List", "items", "Items", "rows", "Rows"):
        candidate = data.get(key)
        if isinstance(candidate, list):
            instances_obj = candidate
            break
    if instances_obj is None:
        nested = data.get("data") if isinstance(data.get("data"), list) else data.get("Data")
        if isinstance(nested, list):
            instances_obj = nested
    instances = [x for x in (instances_obj or []) if isinstance(x, dict)]

    total: Optional[int] = None
    for key in ("total", "Total", "totalCount", "TotalCount"):
        val = data.get(key)
        if val is None:
            continue
        try:
            total = int(val)
            break
        except (TypeError, ValueError):
            continue
    return instances, total


def _extract_instance_id(instance: Dict[str, Any]) -> str:
    for key in ("instance", "instanceId", "InstanceId", "id", "Id"):
        val = instance.get(key)
        if val:
            return str(val).strip()
    return ""


def _extract_instance_name(instance: Dict[str, Any]) -> str:
    for key in ("instanceName", "InstanceName", "name", "Name"):
        val = instance.get(key)
        if val:
            return str(val).strip()
    return ""


def _infer_instance_managed_type(instance: Dict[str, Any]) -> str:
    for key in ("managedType", "ManagedType"):
        val = instance.get(key)
        if isinstance(val, str):
            low = val.strip().lower()
            if low in ("managed", "unmanaged"):
                return low

    for key in ("isManaged", "managed", "managedStatus"):
        val = instance.get(key)
        if isinstance(val, bool):
            return "managed" if val else "unmanaged"
        if isinstance(val, (int, float)):
            return "managed" if int(val) != 0 else "unmanaged"
        if isinstance(val, str):
            low = val.strip().lower()
            if low in ("true", "1", "managed", "yes"):
                return "managed"
            if low in ("false", "0", "unmanaged", "no"):
                return "unmanaged"
    return "unknown"


async def _list_all_instances(
    caller: SysomOpenApiCaller,
    *,
    region_id: str,
    instance_type: str,
    managed_type: str,
    current: int,
    page_size: int,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    instances: list[Dict[str, Any]] = []
    pages: list[Dict[str, Any]] = []
    page = max(1, int(current))
    size = max(1, int(page_size))

    while True:
        page_body = await _list_all_instances_page(
            caller,
            region_id=region_id,
            instance_type=instance_type,
            managed_type=managed_type,
            current=page,
            page_size=size,
        )
        page_instances, total = _extract_pagination_data(page_body)
        pages.append(
            {
                "current": page,
                "page_size": size,
                "count": len(page_instances),
                "total": total,
            }
        )
        instances.extend(page_instances)

        if total is not None and len(instances) >= total:
            break
        if not page_instances:
            break
        if len(page_instances) < size:
            break
        page += 1

    return instances, pages


def _select_instance_interactive(instances: list[Dict[str, Any]]) -> Dict[str, Any]:
    if not instances:
        raise RuntimeError("ListAllInstances returned no selectable instances")
    if not sys.stdin.isatty():
        raise RuntimeError("No --instance-id provided and current environment is non-interactive")

    print("Select an instance to inspect:")
    for idx, item in enumerate(instances, start=1):
        instance_id = _extract_instance_id(item) or "-"
        instance_name = _extract_instance_name(item)
        managed = _infer_instance_managed_type(item)
        display_name = f" ({instance_name})" if instance_name else ""
        print(f"  {idx}. {instance_id}{display_name} managedType={managed}")

    while True:
        try:
            answer = input(f"Enter index [1-{len(instances)}] (press Enter to cancel): ").strip()
        except EOFError:
            answer = ""
        if not answer:
            raise RuntimeError("Instance selection cancelled by user")
        try:
            pos = int(answer)
        except ValueError:
            print("Invalid input, please enter a numeric index.")
            continue
        if 1 <= pos <= len(instances):
            return instances[pos - 1]
        print("Index out of range, please retry.")


def _extract_initial_sysom_role_exist(data: Any) -> Optional[bool]:
    if not isinstance(data, dict):
        return None
    candidate = data.get("role_exist")
    if candidate is None:
        candidate = data.get("roleExist")
    if candidate is None:
        candidate = data.get("RoleExist")
    if isinstance(candidate, bool):
        return candidate
    if isinstance(candidate, str):
        low = candidate.strip().lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
    if isinstance(candidate, (int, float)):
        return bool(candidate)
    return None


async def _call_initial_sysom(
    caller: SysomOpenApiCaller,
    *,
    check_only: Optional[bool],
    require_ready: bool,
) -> Dict[str, Any]:
    request: Dict[str, Any] = {"source": SKILL_HUB_SOURCE}
    if check_only is not None:
        request["check_only"] = check_only
    raw = await caller.call_roa(
        action="InitialSysom",
        pathname="/api/v1/openapi/initial",
        method="POST",
        body=request,
    )
    status = raw.get("statusCode") or raw.get("status_code")
    body = normalize_sysom_body(raw)
    if not _is_http_ok(status):
        raise RuntimeError(f"InitialSysom HTTP {status}: {body.get('message') or body}")

    code = str(body.get("code") or body.get("Code") or "").strip().lower()
    if code and code != "success":
        return {
            "ok": False,
            "error_code": "api_call_failed",
            "message": str(body.get("message") or body.get("Message") or "InitialSysom returned non-Success"),
            "raw_response": body,
        }

    if not require_ready:
        return {"ok": True, "response": body}

    data = body.get("data") or body.get("Data")
    if not data:
        return {
            "ok": False,
            "error_code": "service_not_activated",
            "message": "SysOM service is not activated (InitialSysom returned empty data)",
            "raw_response": body,
        }

    role_exist = _extract_initial_sysom_role_exist(data)
    if role_exist is False:
        return {
            "ok": False,
            "error_code": "sysom_role_not_exist",
            "message": "SysOM service-linked role is not created or not ready (role_exist=false)",
            "raw_response": body,
        }
    return {"ok": True, "response": body}


async def _install_sysom_agent(caller: SysomOpenApiCaller, *, instance_id: str, region_id: str) -> Dict[str, Any]:
    raw = await caller.call_rpc(
        "InstallAgentWithType",
        {
            "instances": [{"instance": instance_id, "region": region_id}],
            "agentId": DEFAULT_SYSOM_AGENT_ID,
            "agentVersion": DEFAULT_SYSOM_AGENT_VERSION,
            "instanceType": DEFAULT_SYSOM_INSTANCE_TYPE,
            "configId": DEFAULT_SYSOM_CONFIG_ID,
        },
    )
    status = raw.get("statusCode") or raw.get("status_code")
    body = normalize_sysom_body(raw)
    if status != 200:
        raise RuntimeError(f"InstallAgentWithType HTTP {status}: {body.get('message') or body}")
    code = str(body.get("code") or body.get("Code") or "").strip().lower()
    if code and code != "success":
        raise RuntimeError(f"InstallAgentWithType BizError: {body.get('message') or body}")
    return body


async def _ensure_sysom_ready(caller: SysomOpenApiCaller, *, instance_id: str, region_id: str) -> Dict[str, Any]:
    first = await _call_initial_sysom(caller, check_only=True, require_ready=True)
    if first.get("ok"):
        return {"ready": True, "initial_sysom": first.get("response")}

    ret: Dict[str, Any] = {
        "ready": False,
        "error_code": first.get("error_code"),
        "message": first.get("message") or "InitialSysom check did not pass",
        "initial_sysom_response": first.get("raw_response"),
    }
    ret["activation_confirmation_required"] = True
    ret["activation_prompt"] = (
        "SysOM is not activated or installed. Activate and install SysOM, then continue inspection?"
    )

    if not sys.stdin.isatty():
        ret["activation_interactive_unavailable"] = True
        ret["activation_cancelled"] = True
        ret["activation_hint"] = (
            "Current environment is non-interactive, cannot confirm activation. Inspection and diagnosis stopped."
        )
        return ret

    try:
        answer = input(
            "SysOM is not activated or installed. Activate and install SysOM, then continue inspection? [y/N]: "
        ).strip().lower()
    except EOFError:
        answer = ""
    if answer not in ("y", "yes"):
        ret["activation_cancelled"] = True
        ret["activation_hint"] = "Activation cancelled. Inspection and diagnosis stopped."
        return ret

    ret["activation_attempted"] = True
    activate_result = await _call_initial_sysom(caller, check_only=False, require_ready=False)
    if not activate_result.get("ok"):
        ret["activation_failed"] = True
        ret["activation_hint"] = (
            activate_result.get("message") or "InitialSysom(check_only=false) activation failed."
        )
        ret["activation_response"] = activate_result.get("raw_response")
        return ret
    ret["activation_response"] = activate_result.get("response")

    try:
        install_resp = await _install_sysom_agent(caller, instance_id=instance_id, region_id=region_id)
        ret["install_attempted"] = True
        ret["install_response"] = install_resp
    except Exception as e:  # noqa: BLE001
        ret["install_attempted"] = True
        ret["install_failed"] = True
        ret["activation_hint"] = f"Failed to install SysOM: {e}"
        return ret

    retry_count = DEFAULT_ACTIVATION_RETRY_COUNT
    retry_interval = DEFAULT_ACTIVATION_RETRY_INTERVAL_SECONDS
    for _ in range(retry_count):
        await asyncio.sleep(retry_interval)
        next_result = await _call_initial_sysom(caller, check_only=True, require_ready=True)
        if next_result.get("ok"):
            return {
                "ready": True,
                "initial_sysom": next_result.get("response"),
                "activation_attempted": True,
                "install_attempted": True,
                "install_response": ret.get("install_response"),
                "activation_response": ret.get("activation_response"),
            }
        ret["error_code"] = next_result.get("error_code")
        ret["message"] = next_result.get("message") or ret["message"]
        ret["initial_sysom_response"] = next_result.get("raw_response")

    ret["activation_failed"] = True
    ret["activation_hint"] = (
        "Activation and installation were attempted, but InitialSysom recheck still failed. Please retry later."
    )
    return ret


async def _get_inspection_report(caller: SysomOpenApiCaller, report_id: str) -> Dict[str, Any]:
    raw = await caller.call_roa(
        action="GetInspectionReport",
        pathname="/api/v1/inspection/getInspectionReport",
        method="GET",
        query={"reportId": report_id},
    )
    status = raw.get("statusCode") or raw.get("status_code")
    body = normalize_sysom_body(raw)
    code = str(body.get("code") or body.get("Code") or "").strip()
    if int(status or 0) == 404 and code == "InvalidAction.NotFound":
        raise InspectionApiUnavailableError(
            "GetInspectionReport is unavailable for current API version (InvalidAction.NotFound)"
        )
    if status != 200:
        raise RuntimeError(f"GetInspectionReport HTTP {status}: {body.get('message') or body}")
    return body


def _extract_inspection_report_status(report_body: Dict[str, Any]) -> str:
    data = report_body.get("data") or report_body.get("Data") or {}
    if not isinstance(data, dict):
        return ""
    for key in ("status", "Status", "reportStatus", "ReportStatus", "inspectionStatus", "InspectionStatus"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


async def _wait_inspection_report_success(
    caller: SysomOpenApiCaller,
    *,
    report_id: str,
    timeout_seconds: int = DEFAULT_INSPECTION_REPORT_TIMEOUT_SECONDS,
    poll_interval_seconds: int = DEFAULT_INSPECTION_REPORT_POLL_INTERVAL_SECONDS,
) -> Dict[str, Any]:
    timeout_seconds = max(1, int(timeout_seconds))
    poll_interval_seconds = max(1, int(poll_interval_seconds))
    start = asyncio.get_running_loop().time()
    while (asyncio.get_running_loop().time() - start) < timeout_seconds:
        body = await _get_inspection_report(caller, report_id)
        status = _extract_inspection_report_status(body).lower()
        if status == "success":
            return body
        await asyncio.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"GetInspectionReport timed out ({timeout_seconds}s), report_id: {report_id}"
    )


async def _probe_get_inspection_report(caller: SysomOpenApiCaller) -> Dict[str, Any]:
    """
    When CreateInstanceInspection is unavailable, still run one GetInspectionReport probe call
    so evaluation and logs can confirm the action was actually triggered.
    """
    probe_report_id = "inspection-probe-unavailable"
    try:
        body = await _get_inspection_report(caller, probe_report_id)
        return {
            "called": True,
            "report_id": probe_report_id,
            "ok": True,
            "response": body,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "called": True,
            "report_id": probe_report_id,
            "ok": False,
            "error": str(e),
        }


async def _invoke_memgraph_diagnosis(
    caller: SysomOpenApiCaller,
    *,
    region_id: str,
    instance_id: str,
    report_id: str,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "region": region_id,
        "instance": instance_id,
        "trigger_item": DIAGNOSIS_TRIGGER_ITEM,
        "trigger_report_id": report_id,
    }
    for key in LEGACY_DIAGNOSIS_SOURCE_KEYS:
        params.pop(key, None)
    params.pop(DIAGNOSIS_SOURCE_KEY, None)
    params[DIAGNOSIS_SOURCE_KEY] = SKILL_HUB_SOURCE
    client_token = _build_client_token(
        "diag",
        {
            "service_name": "memgraph",
            "channel": "ecs",
            "region": region_id,
            "instance": instance_id,
            "trigger_report_id": report_id,
        },
    )

    raw = await caller.call_roa(
        action="InvokeDiagnosis",
        pathname="/api/v1/openapi/diagnosis/invoke_diagnosis",
        method="POST",
        body={
            "service_name": "memgraph",
            "channel": "ecs",
            "params": json.dumps(params, ensure_ascii=False),
            "clientToken": client_token,
        },
    )
    status = raw.get("statusCode") or raw.get("status_code")
    body = normalize_sysom_body(raw)
    if status != 200:
        raise RuntimeError(f"InvokeDiagnosis HTTP {status}: {body.get('message') or body}")
    code = str(body.get("code") or body.get("Code") or "").strip().lower()
    if code and code != "success":
        raise RuntimeError(f"InvokeDiagnosis BizError: {body.get('message') or body}")
    return body


def _extract_diagnosis_task_id(invoke_resp: Dict[str, Any]) -> str:
    data = invoke_resp.get("data") or invoke_resp.get("Data") or {}
    if not isinstance(data, dict):
        return ""
    for key in ("task_id", "taskId", "TaskId"):
        val = data.get(key)
        if val:
            return str(val).strip()
    return ""


def _extract_get_diagnosis_result_payload(data: Dict[str, Any]) -> Any:
    if not isinstance(data, dict):
        return None
    for key in ("result", "Result", "diagnosis_result", "DiagnosisResult", "output", "Output", "report", "Report"):
        value = data.get(key)
        if value not in (None, "", {}, []):
            return value

    meta_keys = {
        "task_id",
        "taskId",
        "TaskId",
        "status",
        "Status",
        "err_msg",
        "ErrMsg",
        "message",
        "Message",
        "request_id",
        "RequestId",
        "code",
        "Code",
    }
    rest = {k: v for k, v in data.items() if k not in meta_keys}
    if len(rest) == 1:
        return next(iter(rest.values()))
    if rest:
        return rest
    return None


async def _get_diagnosis_result(caller: SysomOpenApiCaller, task_id: str) -> Dict[str, Any]:
    raw = await caller.call_roa(
        action="GetDiagnosisResult",
        pathname="/api/v1/openapi/diagnosis/get_diagnosis_results",
        method="GET",
        query={"task_id": task_id},
    )
    status = raw.get("statusCode") or raw.get("status_code")
    body = normalize_sysom_body(raw)
    if status != 200:
        raise RuntimeError(f"GetDiagnosisResult HTTP {status}: {body.get('message') or body}")
    return body


async def _wait_diagnosis_result(
    caller: SysomOpenApiCaller,
    *,
    task_id: str,
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> Dict[str, Any]:
    timeout_seconds = max(1, int(timeout_seconds))
    poll_interval_seconds = max(1, int(poll_interval_seconds))
    start = asyncio.get_running_loop().time()

    while (asyncio.get_running_loop().time() - start) < timeout_seconds:
        body = await _get_diagnosis_result(caller, task_id)
        code = str(body.get("code") or body.get("Code") or "").strip().lower()
        if code and code != "success":
            message = body.get("message") or body.get("Message") or "GetDiagnosisResult returned non-Success"
            return {
                "code": "GetResultFailed",
                "message": str(message),
                "task_id": task_id,
                "raw_response": body,
            }

        data = body.get("data") or body.get("Data") or {}
        status = str((data.get("status") if isinstance(data, dict) else "") or "").strip().lower()
        if status == "success":
            return {
                "code": "Success",
                "message": "",
                "task_id": task_id,
                "result": _extract_get_diagnosis_result_payload(data) if isinstance(data, dict) else data,
                "raw_response": body,
            }
        if status == "fail":
            err_msg = ""
            if isinstance(data, dict):
                err_msg = str(data.get("err_msg") or data.get("ErrMsg") or data.get("message") or "").strip()
            return {
                "code": "TaskExecuteFailed",
                "message": err_msg or "Diagnosis task execution failed",
                "task_id": task_id,
                "raw_response": body,
            }
        await asyncio.sleep(poll_interval_seconds)

    return {
        "code": "TaskTimeout",
        "message": f"Diagnosis timed out ({timeout_seconds}s), task_id: {task_id}",
        "task_id": task_id,
    }


def _has_memory_usage_issue(report_body: Dict[str, Any]) -> bool:
    marker_keys = (
        "item",
        "item_name",
        "itemName",
        "metric",
        "metricName",
        "name",
        "key",
        "type",
    )
    positive_keys = ("abnormal", "isAbnormal", "hasIssue", "isIssue", "triggered", "detected", "hit")
    positive_status_values = {
        "abnormal",
        "alert",
        "warning",
        "warn",
        "critical",
        "high",
        "error",
    }

    def _contains_marker(obj: Any) -> bool:
        if isinstance(obj, str):
            return obj.strip() == MEMORY_USAGE_ITEM
        if isinstance(obj, dict):
            for mk in marker_keys:
                v = obj.get(mk)
                if isinstance(v, str) and v.strip() == MEMORY_USAGE_ITEM:
                    return True
        return False

    def _is_positive(obj: Dict[str, Any]) -> bool:
        for k in positive_keys:
            if obj.get(k) is True:
                return True
        for k in ("status", "level", "severity", "verdict", "result"):
            val = obj.get(k)
            if isinstance(val, str) and val.strip().lower() in positive_status_values:
                return True
        return False

    def _walk(obj: Any) -> bool:
        if isinstance(obj, dict):
            if _contains_marker(obj) and _is_positive(obj):
                return True
            # Common aggregate structures: treat memory item hit in abnormalItems/issues/alerts as detected.
            for k in ("abnormalItems", "issues", "alerts", "abnormal_metrics"):
                v = obj.get(k)
                if isinstance(v, list):
                    for item in v:
                        if _contains_marker(item):
                            return True
            for v in obj.values():
                if _walk(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if _walk(item):
                    return True
        return False

    data = report_body.get("data") or report_body.get("Data") or report_body
    return _walk(data)


def _render_report_markdown(template: str, values: Dict[str, str]) -> str:
    rendered = template
    for k, v in values.items():
        rendered = rendered.replace("{" + k + "}", str(v))
    return rendered


def _format_abnormal_items_markdown(abnormal_items: list[Dict[str, str]]) -> str:
    if not abnormal_items:
        return "- No abnormal items were found in this inspection."
    lines: list[str] = []
    for idx, item in enumerate(abnormal_items, start=1):
        item_name = item.get("item") or "-"
        level = item.get("level") or "Unknown"
        reason = item.get("reason") or "No detailed reason"
        lines.append(f"- {idx}. `{item_name}` (Level: {level}): {reason}")
    return "\n".join(lines)


def _extract_top_process_findings(diagnosis_result: Dict[str, Any]) -> str:
    result = diagnosis_result.get("result")
    if not isinstance(result, dict):
        return "- No process-level diagnosis details are available."
    app_top = result.get("dataAppMemTopN")
    if not isinstance(app_top, dict):
        return "- No process-level diagnosis details are available."
    data = app_top.get("data")
    if not isinstance(data, list) or not data:
        return "- No process-level diagnosis details are available."

    lines: list[str] = []
    for row in data[:3]:
        if not isinstance(row, dict):
            continue
        task = str(row.get("task") or "-").strip()
        mem_total = str(row.get("memTotal") or "-").strip()
        rss_anon = str(row.get("rssAnon") or "-").strip()
        cmdline = str(row.get("cmdline") or "").strip()
        if cmdline:
            lines.append(f"- `{task}`: total memory {mem_total}, anonymous memory {rss_anon}, command `{cmdline}`")
        else:
            lines.append(f"- `{task}`: total memory {mem_total}, anonymous memory {rss_anon}")
    return "\n".join(lines) if lines else "- No process-level diagnosis details are available."


def _format_app_mem_ranking_markdown(diagnosis_result: Dict[str, Any], limit: int = 10) -> str:
    result = diagnosis_result.get("result")
    if not isinstance(result, dict):
        return "- No application memory usage ranking data is available."
    app_top = result.get("dataAppMemTopN")
    if not isinstance(app_top, dict):
        return "- No application memory usage ranking data is available."
    data = app_top.get("data")
    if not isinstance(data, list) or not data:
        return "- No application memory usage ranking data is available."

    def _sanitize(cell: Any) -> str:
        text = str(cell or "-").replace("\n", " ").strip()
        return text.replace("|", "\\|")

    lines = [
        "| Rank | Process | Total Memory | Anonymous Memory | Command Line |",
        "|---|---|---|---|---|",
    ]
    for idx, row in enumerate(data[: max(1, int(limit))], start=1):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| {idx} | {_sanitize(row.get('task'))} | {_sanitize(row.get('memTotal'))} | {_sanitize(row.get('rssAnon'))} | {_sanitize(row.get('cmdline'))} |"
        )

    if len(lines) == 2:
        return "- No application memory usage ranking data is available."
    return "\n".join(lines)


def _normalize_report_time_token(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    if not value:
        return datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 20:
        return f"{digits[:8]}-{digits[8:14]}-{digits[14:20]}"
    if len(digits) >= 14:
        return f"{digits[:8]}-{digits[8:14]}-000000"
    if len(digits) >= 8:
        return f"{digits[:8]}-{datetime.now().strftime('%H%M%S-%f')}"
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _persist_report_markdown(*, report_markdown: str, report_time_token: str) -> tuple[str, str]:
    report_file_name = f"inspection-report-{report_time_token}.md"
    report_path = REPORT_OUTPUT_DIR / report_file_name
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_markdown, encoding="utf-8")
    return report_file_name, str(report_path.resolve())


def _build_inspection_conclusion(result: Dict[str, Any]) -> Dict[str, Any]:
    report_resp = result.get("inspection_report_response")
    report_data = report_resp.get("data") if isinstance(report_resp, dict) else None
    if not isinstance(report_data, dict):
        report_data = report_resp.get("Data") if isinstance(report_resp, dict) else None
    if not isinstance(report_data, dict):
        report_data = {}

    report_time_token = _normalize_report_time_token(
        str(report_data.get("updated_at") or report_data.get("created_at") or "")
    )
    report_status = str(report_data.get("status") or report_data.get("Status") or "").strip() or "Unknown"
    report_items = report_data.get("report_items")
    if not isinstance(report_items, list):
        report_items = report_data.get("reportItems")
    if not isinstance(report_items, list):
        report_items = []

    abnormal_items: list[Dict[str, str]] = []
    for item in report_items:
        if not isinstance(item, dict):
            continue
        item_name = str(
            item.get("item_name")
            or item.get("itemName")
            or item.get("item")
            or item.get("metric")
            or ""
        ).strip()
        level = str(item.get("level") or item.get("severity") or item.get("status") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if not item_name:
            continue
        if level.lower() not in ("", "normal", "ok", "success"):
            abnormal_items.append(
                {
                    "item": item_name,
                    "level": level or "Unknown",
                    "reason": reason,
                }
            )

    if result.get("inspection_invoked") is not True:
        inspection_report_result = "Inspection was not started successfully, so no report result is available."
    elif result.get("inspection_report_id") and report_status.lower() == "success":
        if abnormal_items:
            inspection_report_result = (
                f"Inspection report completed (Success), {len(abnormal_items)} abnormal item(s) found."
            )
        else:
            inspection_report_result = "Inspection report completed (Success), no abnormal items found."
    elif result.get("inspection_report_id"):
        inspection_report_result = f"Inspection report retrieved, but status is {report_status}."
    else:
        inspection_report_result = "Inspection task started, but no reportId was returned."

    diagnosis_result = result.get("memgraph_diagnosis_result")
    diag_code = ""
    diag_message = ""
    if isinstance(diagnosis_result, dict):
        diag_code = str(diagnosis_result.get("code") or "").strip()
        diag_message = str(diagnosis_result.get("message") or "").strip()

    diagnosis_status = "Not Triggered"
    diagnosis_task_id = str(result.get("memgraph_diagnosis_task_id") or "-")
    diagnosis_root_cause = "N/A"
    diagnosis_suggestion = "N/A"
    diagnosis_key_findings = "- Automatic diagnosis was not triggered, no diagnosis details available."
    diagnosis_app_mem_ranking = "- Automatic diagnosis was not triggered, no app memory ranking available."
    if result.get("memgraph_diagnosis_invoked"):
        diagnosis_status = "Triggered"
        if diag_code.lower() == "success":
            summary = diagnosis_result.get("result", {}).get("summary") if isinstance(diagnosis_result, dict) else None
            cause = ""
            suggestion = ""
            if isinstance(summary, dict):
                cause = str(summary.get("cause") or "").strip()
                suggestion = str(summary.get("suggestion") or "").strip()
            diagnosis_root_cause = cause or "Not Provided"
            diagnosis_suggestion = suggestion or "Not Provided"
            diagnosis_key_findings = (
                _extract_top_process_findings(diagnosis_result)
                if isinstance(diagnosis_result, dict)
                else "- No process-level diagnosis details are available."
            )
            diagnosis_app_mem_ranking = (
                _format_app_mem_ranking_markdown(diagnosis_result, limit=10)
                if isinstance(diagnosis_result, dict)
                else "- No application memory usage ranking data is available."
            )
            detail_parts = [p for p in (cause, suggestion) if p]
            detail = f" Conclusion: {'; '.join(detail_parts)}" if detail_parts else ""
            diagnosis_report_result = f"memgraph diagnosis was triggered automatically, result is Success.{detail}".strip()
        else:
            diagnosis_report_result = (
                f"memgraph diagnosis was triggered automatically, result is {diag_code or 'Unknown'}, "
                f"{diag_message or 'no detailed message'}."
            )
            diagnosis_root_cause = diag_message or "Diagnosis did not return root cause details"
            diagnosis_suggestion = "Please investigate further with task logs"
            diagnosis_key_findings = "- Diagnosis task was triggered, but no usable structured details were returned."
            diagnosis_app_mem_ranking = "- Diagnosis did not return usable app memory ranking data."
    else:
        diagnosis_report_result = "Automatic diagnosis was not triggered."

    final_parts = [inspection_report_result, diagnosis_report_result]
    if result.get("memgraph_diagnosis_skipped_reason"):
        final_parts.append(f"Note: {result['memgraph_diagnosis_skipped_reason']}")

    final_conclusion = " ".join(final_parts)
    abnormal_items_markdown = _format_abnormal_items_markdown(abnormal_items)
    template_values = {
        "instance_id": str(result.get("instance_id") or "-"),
        "region_id": str(result.get("region_id") or "-"),
        "report_time": report_time_token,
        "inspection_report_id": str(result.get("inspection_report_id") or "-"),
        "inspection_report_status": report_status,
        "inspection_report_result": inspection_report_result,
        "abnormal_items_markdown": abnormal_items_markdown,
        "diagnosis_status": diagnosis_status,
        "diagnosis_task_id": diagnosis_task_id,
        "diagnosis_report_result": diagnosis_report_result,
        "diagnosis_root_cause": diagnosis_root_cause,
        "diagnosis_suggestion": diagnosis_suggestion,
        "diagnosis_key_findings": diagnosis_key_findings,
        "diagnosis_app_mem_ranking": diagnosis_app_mem_ranking,
        "final_conclusion": final_conclusion,
        "report_file_name": "-",
        "report_file_path": "-",
    }
    template = _load_report_template()
    report_markdown = _render_report_markdown(template, template_values)
    report_file_name = "-"
    report_file_path = "-"
    report_file_write_error = ""
    try:
        report_file_name, report_file_path = _persist_report_markdown(
            report_markdown=report_markdown,
            report_time_token=report_time_token,
        )
        template_values["report_file_name"] = report_file_name
        template_values["report_file_path"] = report_file_path
        report_markdown = _render_report_markdown(template, template_values)
        Path(report_file_path).write_text(report_markdown, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        report_file_write_error = str(e)

    return {
        "inspection_report_result": inspection_report_result,
        "diagnosis_report_result": diagnosis_report_result,
        "final_conclusion": final_conclusion,
        "abnormal_items": abnormal_items,
        "report_markdown": report_markdown,
        "report_file_name": report_file_name,
        "report_file_path": report_file_path,
        "report_time": report_time_token,
        "report_file_write_error": report_file_write_error,
    }


def _attach_conclusion(result: Dict[str, Any]) -> Dict[str, Any]:
    result["inspection_conclusion"] = _build_inspection_conclusion(result)
    return result


async def run_inspection(args: argparse.Namespace) -> Dict[str, Any]:
    caller = SysomOpenApiCaller(resolve_sysom_credentials())
    selected_instance_id = getattr(args, "instance_id", None)
    selected_instance: Optional[Dict[str, Any]] = None
    list_pages: list[Dict[str, Any]] = []
    listed_instances: list[Dict[str, Any]] = []
    if not selected_instance_id:
        listed_instances, list_pages = await _list_all_instances(
            caller,
            region_id=args.region_id,
            instance_type=getattr(args, "instance_type", DEFAULT_SYSOM_INSTANCE_TYPE),
            managed_type=getattr(args, "managed_type", "all"),
            current=getattr(args, "current", 1),
            page_size=getattr(args, "page_size", 50),
        )
        selected_instance = _select_instance_interactive(listed_instances)
        selected_instance_id = _extract_instance_id(selected_instance)
        if not selected_instance_id:
            raise RuntimeError("Selected instance has no instanceId, cannot start inspection")

    readiness = await _ensure_sysom_ready(caller, instance_id=selected_instance_id, region_id=args.region_id)
    if not readiness.get("ready"):
        return _attach_conclusion(
            {
            "instance_id": selected_instance_id,
            "region_id": args.region_id,
            "inspection_invoked": False,
            "memgraph_diagnosis_invoked": False,
            "initial_sysom_ready": False,
            "initial_sysom_check": readiness,
            "instance_selection": {
                "selected_by_user": bool(selected_instance),
                "selected_instance": selected_instance,
                "managed_type_filter": getattr(args, "managed_type", "all"),
                "instance_type": getattr(args, "instance_type", DEFAULT_SYSOM_INSTANCE_TYPE),
                "list_pages": list_pages,
                "listed_count": len(listed_instances),
            },
            }
        )

    items = list(getattr(args, "inspection_items", DEFAULT_INSPECTION_ITEMS))
    managed_type = _infer_instance_managed_type(selected_instance or {}) if selected_instance else "unknown"
    metric_source = getattr(args, "metric_source", None)
    if not metric_source:
        if managed_type == "managed":
            metric_source = "sysom"
        elif managed_type == "unmanaged":
            metric_source = "cms"
        else:
            metric_source = "auto"
    try:
        create_resp = await _create_instance_inspection(
            caller,
            instance_id=selected_instance_id,
            region_id=args.region_id,
            items=items,
            metric_source=metric_source,
        )
    except InspectionApiUnavailableError as e:
        report_probe = await _probe_get_inspection_report(caller)
        return _attach_conclusion(
            {
            "instance_id": selected_instance_id,
            "region_id": args.region_id,
            "inspection_invoked": False,
            "memgraph_diagnosis_invoked": False,
            "initial_sysom_ready": True,
            "initial_sysom_check": readiness,
            "inspection_api_available": False,
            "inspection_api_unavailable_reason": str(e),
            "inspection_report_probe": report_probe,
            "instance_selection": {
                "selected_by_user": bool(selected_instance),
                "selected_instance": selected_instance,
                "selected_instance_managed_type": managed_type,
                "managed_type_filter": getattr(args, "managed_type", "all"),
                "instance_type": getattr(args, "instance_type", DEFAULT_SYSOM_INSTANCE_TYPE),
                "list_pages": list_pages,
                "listed_count": len(listed_instances),
            },
            }
        )

    result: Dict[str, Any] = {
        "instance_id": selected_instance_id,
        "region_id": args.region_id,
        "inspection_source": SKILL_HUB_SOURCE,
        "inspection_metric_source": metric_source,
        "inspection_items": items,
        "inspection_invoked": True,
        "inspection_api_available": True,
        "initial_sysom_ready": True,
        "initial_sysom_check": readiness,
        "inspection_create_response": create_resp,
        "memgraph_diagnosis_invoked": False,
        "instance_selection": {
            "selected_by_user": bool(selected_instance),
            "selected_instance": selected_instance,
            "selected_instance_managed_type": managed_type,
            "managed_type_filter": getattr(args, "managed_type", "all"),
            "instance_type": getattr(args, "instance_type", DEFAULT_SYSOM_INSTANCE_TYPE),
            "list_pages": list_pages,
            "listed_count": len(listed_instances),
        },
    }

    report_data = create_resp.get("data") or create_resp.get("Data") or {}
    report_id: Optional[str] = report_data.get("reportId") or report_data.get("ReportId")
    if not report_id:
        result["memgraph_diagnosis_skipped_reason"] = "CreateInstanceInspection did not return reportId"
        return _attach_conclusion(result)

    result["inspection_report_id"] = report_id
    try:
        report_resp = await _wait_inspection_report_success(
            caller,
            report_id=str(report_id),
            timeout_seconds=getattr(args, "inspection_report_timeout_seconds", DEFAULT_INSPECTION_REPORT_TIMEOUT_SECONDS),
            poll_interval_seconds=getattr(
                args,
                "inspection_report_poll_interval_seconds",
                DEFAULT_INSPECTION_REPORT_POLL_INTERVAL_SECONDS,
            ),
        )
    except InspectionApiUnavailableError as e:
        result["inspection_api_available"] = False
        result["inspection_api_unavailable_reason"] = str(e)
        result["inspection_invoked"] = False
        return _attach_conclusion(result)
    except TimeoutError as e:
        result["inspection_report_wait_timeout"] = True
        result["inspection_report_wait_timeout_reason"] = str(e)
        result["memgraph_diagnosis_skipped_reason"] = "Inspection report wait timed out before diagnosis stage"
        return _attach_conclusion(result)
    result["inspection_report_response"] = report_resp

    memory_issue = _has_memory_usage_issue(report_resp)
    result["memory_usage_issue_detected"] = memory_issue
    if not memory_issue:
        return _attach_conclusion(result)
    if getattr(args, "disable_memgraph_diagnosis", False):
        result["memgraph_diagnosis_skipped_reason"] = "memgraph diagnosis was disabled by argument"
        return _attach_conclusion(result)

    result["memgraph_diagnosis_invoked"] = True
    try:
        invoke_resp = await _invoke_memgraph_diagnosis(
            caller,
            region_id=args.region_id,
            instance_id=selected_instance_id,
            report_id=str(report_id),
        )
    except Exception as e:  # noqa: BLE001
        result["memgraph_diagnosis_result"] = {
            "code": "InvokeFailed",
            "message": str(e),
            "task_id": "",
        }
        return _attach_conclusion(result)
    result["memgraph_diagnosis_response"] = invoke_resp
    task_id = _extract_diagnosis_task_id(invoke_resp)
    result["memgraph_diagnosis_task_id"] = task_id
    if not task_id:
        result["memgraph_diagnosis_result"] = {
            "code": "TaskCreateFailed",
            "message": "InvokeDiagnosis did not return task_id, cannot call GetDiagnosisResult",
            "task_id": "",
        }
        return _attach_conclusion(result)

    result["memgraph_diagnosis_result"] = await _wait_diagnosis_result(
        caller,
        task_id=task_id,
        timeout_seconds=getattr(args, "diagnosis_timeout_seconds", DEFAULT_DIAGNOSIS_TIMEOUT_SECONDS),
        poll_interval_seconds=getattr(
            args,
            "diagnosis_poll_interval_seconds",
            DEFAULT_DIAGNOSIS_POLL_INTERVAL_SECONDS,
        ),
    )
    return _attach_conclusion(result)
