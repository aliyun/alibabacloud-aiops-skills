"""Stateless single-step operations for Agent-driven polling.

Each function makes exactly ONE API call and returns a structured status
dict. There is NO internal looping or sleeping — the Agent (caller) is
responsible for waiting and re-invoking poll steps based on the returned
`status` field. State (task_id, confirmed datasource name) is passed in via
function arguments, never persisted internally.

Status values:
- "started":   start step accepted; task is now running
- "running":   poll step — task still in progress, Agent should wait & retry
- "completed": poll step — task finished successfully
- "ambiguous": datasource name matched multiple candidates (E610R1002)
- "failed":    unrecoverable business error
"""

import json
from typing import Any, Dict, Optional

from lhm_read_exec_cli.workflow import _create_client, _safe_parse_json

ERR_CODE_SUCCESS = "200"
ERR_CODE_AMBIGUOUS = "E610R1002"
ERR_CODE_DS_NOT_FOUND = "E610R1001"
ERR_CODE_READ_IN_PROGRESS = "E610R1004"
ERR_CODE_CONVERT_IN_PROGRESS = "E610R1016"


def _failed(err_code: str, err_message: str, request_id: str = "") -> Dict[str, Any]:
    """Build a 'failed' status dict."""
    return {
        "status": "failed",
        "err_code": err_code,
        "err_message": err_message,
        "request_id": request_id,
    }


def _request_id(body) -> str:
    """Extract request_id from a response body, defaulting to empty."""
    return getattr(body, "request_id", "") or ""


def _handle_sdk_exception(exc: Exception, context: str = "") -> Dict[str, Any]:
    """Convert an SDK-level exception into a structured failed status dict."""
    exc_type = type(exc).__name__
    # Try to extract details from known SDK exception types
    status_code = getattr(exc, "status_code", None) or ""
    code = getattr(exc, "code", "") or ""
    message = getattr(exc, "message", "") or str(exc)
    request_id = getattr(exc, "request_id", "") or ""

    err_code = f"SDK_{code}" if code else f"SDK_{exc_type}"
    err_message = f"{context}: {message}" if context else message
    if status_code:
        err_message = f"[HTTP {status_code}] {err_message}"

    return _failed(err_code, err_message, request_id)


def read_start(config, source_ds_name: str) -> Dict[str, Any]:
    """Single step: start schedule exploration (PostInnerReader).

    Args:
        config: LHM configuration.
        source_ds_name: Source datasource name.

    Returns:
        Status dict. On "started", caller should next call `read_poll`.
        On "ambiguous", `candidates` lists matching datasources; caller must
        re-invoke with a confirmed exact name.
    """
    client = _create_client(config)
    request = {"dataSourceName": source_ds_name}
    try:
        body = client.post_inner_reader(request).body
    except Exception as cli_exc:
        return _handle_sdk_exception(cli_exc, "PostInnerReader")

    if body.err_code == ERR_CODE_SUCCESS:
        return {
            "status": "started",
            "source_ds_name": source_ds_name,
            "request_id": _request_id(body),
        }

    if body.err_code == ERR_CODE_AMBIGUOUS:
        candidates = _safe_parse_json(body.data, "datasource candidates")
        return {
            "status": "ambiguous",
            "err_code": body.err_code,
            "candidates": candidates,
            "source_ds_name": source_ds_name,
            "request_id": _request_id(body),
        }

    if body.err_code == ERR_CODE_DS_NOT_FOUND:
        return {
            "status": "failed",
            "err_code": body.err_code,
            "err_message": "数据源不存在，请使用 /lhm-sch-ds 技能创建数据源。示例：/lhm-sch-ds 创建一个 DolphinScheduler 类型的数据源",
            "request_id": _request_id(body),
            "action_required": "create_datasource",
            "suggested_skill": "/lhm-sch-ds",
        }

    return _failed(body.err_code, body.err_message, _request_id(body))


def read_poll(config, source_ds_name: str) -> Dict[str, Any]:
    """Single step: poll exploration result (GetInnerReadAsyncResult).

    Args:
        config: LHM configuration.
        source_ds_name: Source datasource name.

    Returns:
        Status dict. "running" → Agent waits and retries; "completed" →
        carries workflow_count / node_count / node_type_distribution.
    """
    client = _create_client(config)
    request = {"dataSourceName": source_ds_name}
    body = client.get_inner_read_async_result(request).body

    if body.err_code == ERR_CODE_SUCCESS:
        parsed = _safe_parse_json(body.data, "exploration result")
        result: Dict[str, Any] = {
            "status": "completed",
            "request_id": _request_id(body),
        }
        if isinstance(parsed, dict):
            result["workflow_count"] = parsed.get("workflowCount")
            result["node_count"] = parsed.get("taskNodeCount")
            result["script_count"] = parsed.get("scriptCount")
            result["node_type_distribution"] = parsed.get("nodeTypeCountMap", {})
        return result

    if body.err_code == ERR_CODE_READ_IN_PROGRESS:
        return {
            "status": "running",
            "err_code": body.err_code,
            "request_id": _request_id(body),
        }

    return _failed(body.err_code, body.err_message, _request_id(body))


def convert_start(
    config, source_ds_name: str, target_ds_name: str, sql_convert_map: Optional[str] = None
) -> Dict[str, Any]:
    """Single step: trigger schedule conversion (PostInnerConvert).

    Args:
        config: LHM configuration.
        source_ds_name: Source datasource name.
        target_ds_name: Target datasource name.
        sql_convert_map: Optional JSON string mapping source SQL dialect to target dialect,
                         e.g. '{"DWSSQL":"HOLOGRES_SQL"}'.

    Returns:
        Status dict. On "started", carries `task_id` for the convert-poll step.
    """
    client = _create_client(config)
    
    request = {
        "srcDataSourceName": source_ds_name,
        "tgtDataSourceName": target_ds_name,
    }
    
    if sql_convert_map is not None:
        try:
            parsed_map = json.loads(sql_convert_map)
            request["sqlConvertMap"] = parsed_map
        except json.JSONDecodeError as parse_error:
            return _failed(
                "INVALID_PARAM",
                f"Invalid JSON in --sql-convert-map: {parse_error}",
            )
    body = client.post_inner_convert(request).body

    if body.err_code == ERR_CODE_SUCCESS:
        return {
            "status": "started",
            "task_id": body.data,
            "request_id": _request_id(body),
        }

    if body.err_code == ERR_CODE_DS_NOT_FOUND:
        return {
            "status": "failed",
            "err_code": body.err_code,
            "err_message": "数据源不存在，请使用 /lhm-sch-ds 技能创建数据源。示例：/lhm-sch-ds 创建一个 DolphinScheduler 类型的数据源",
            "request_id": _request_id(body),
            "action_required": "create_datasource",
            "suggested_skill": "/lhm-sch-ds",
        }

    if body.err_code == ERR_CODE_AMBIGUOUS:
        candidates = _safe_parse_json(body.data, "datasource candidates")
        return {
            "status": "ambiguous",
            "err_code": body.err_code,
            "candidates": candidates,
            "request_id": _request_id(body),
        }

    return _failed(body.err_code, body.err_message, _request_id(body))


def convert_poll(config, task_id: str) -> Dict[str, Any]:
    """Single step: poll conversion result (GetInnerConvertAsyncResult).

    Args:
        config: LHM configuration.
        task_id: Task ID from the convert-start step.

    Returns:
        Status dict. "running" → Agent waits and retries; "completed" →
        carries `task_id`, `request_id`, and raw `data` (incl. download_url).
    """
    client = _create_client(config)
    request = {"taskId": task_id}
    body = client.get_inner_convert_async_result(request).body

    if body.err_code == ERR_CODE_SUCCESS:
        return {
            "status": "completed",
            "task_id": task_id,
            "request_id": _request_id(body),
            "data": _safe_parse_json(body.data, "conversion result"),
        }

    if body.err_code == ERR_CODE_CONVERT_IN_PROGRESS:
        return {
            "status": "running",
            "task_id": task_id,
            "err_code": body.err_code,
            "request_id": _request_id(body),
        }

    return _failed(body.err_code, body.err_message, _request_id(body))
