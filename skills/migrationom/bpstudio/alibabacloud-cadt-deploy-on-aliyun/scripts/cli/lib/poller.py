"""Async poller — wraps `aliyun bpstudio get-execute-operation-result`."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from typing import Any, Dict

from .errors import ApiError, BusinessFailure, CadtTimeout
from .normalize import normalize_ecs_run_result

ALIYUN_BIN = shutil.which("aliyun") or "aliyun"
BPSTUDIO_API_VERSION = "2021-09-31"
BPSTUDIO_REGION = "cn-hangzhou"

# Observability: session-id injected by the agent at invocation time.
_SKILL_NAME = "alibabacloud-cadt-deploy-on-aliyun"
def _session_id() -> str:
    return os.environ.get("SKILL_SESSION_ID", "")

DEFAULT_TIMEOUT_S = 300


def _interval_for(elapsed: float) -> float:
    """Tiered polling interval: first 10s every 1s, 10-30s every 2s, after 30s every 5s."""
    if elapsed < 10:
        return 1.0
    if elapsed < 30:
        return 2.0
    return 5.0


def poll_until_done(invocation_id: str, *, timeout: int = DEFAULT_TIMEOUT_S) -> Any:
    """Poll until status is success or failure or timeout."""
    start = time.monotonic()
    deadline = start + timeout
    last_status = "unknown"
    while time.monotonic() < deadline:
        snapshot = _query_once(invocation_id)
        status = (snapshot.get("status") or snapshot.get("Status") or "").lower()
        last_status = status or last_status
        if status == "success":
            return normalize_ecs_run_result(_unwrap_data(snapshot))
        if status == "failure":
            raise BusinessFailure(
                snapshot.get("message") or snapshot.get("Message") or "async task failed",
                fix_hint=str(snapshot.get("code") or snapshot.get("Code") or ""),
                details=normalize_ecs_run_result(_unwrap_data(snapshot)),
            )
        time.sleep(_interval_for(time.monotonic() - start))
    raise CadtTimeout(
        f"async task {invocation_id} timed out ({timeout}s, last_status={last_status})",
        invocation_id=invocation_id,
        fix_hint=f"Operation is still running in background; use cadt_deploy_on_aliyun -poll {invocation_id} to continue querying",
    )


def poll_once(invocation_id: str) -> Dict[str, Any]:
    """Single query for `cadt_deploy_on_aliyun -poll <id> --wait=once`."""
    snapshot = _query_once(invocation_id)
    status = (snapshot.get("status") or snapshot.get("Status") or "running").lower()
    out = {
        "invocationId": invocation_id,
        "status": status,
    }
    for k_in, k_out in (("progress", "progress"), ("Message", "message"),
                        ("message", "message")):
        if k_in in snapshot:
            out[k_out] = snapshot[k_in]
    if status == "success":
        out["data"] = normalize_ecs_run_result(_unwrap_data(snapshot))
    elif status == "failure":
        out["data"] = normalize_ecs_run_result(_unwrap_data(snapshot))
    return out


def _query_once(invocation_id: str) -> Dict[str, Any]:
    cmd = [
        ALIYUN_BIN, "bpstudio", "get-execute-operation-result",
        f"--operation-id={invocation_id}",
        f"--api-version={BPSTUDIO_API_VERSION}",
        f"--region={BPSTUDIO_REGION}",
    ]
    # Observability: attach user-agent per SKILL.md §Observability
    sid = _session_id()
    if sid:
        cmd.extend(["--user-agent", f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{sid}"])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL)
    except FileNotFoundError as e:
        raise ApiError(
            f"aliyun CLI not found: {e}",
            fix_hint="Install aliyun CLI first",
        )
    except subprocess.TimeoutExpired:
        raise ApiError(
            f"get-execute-operation-result single call exceeded 30s: {invocation_id}",
            fix_hint="Backend unreachable; check network or retry later",
        )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()[:300]
        if "503" in stderr or "ServiceUnavailable" in stderr:
            raise ApiError(
                f"Backend temporarily unavailable (503), operationId may have expired: {invocation_id}",
                fix_hint="Verify operationId is valid and not expired, or retry later",
            )
        raise ApiError(
            f"poll non-zero ({proc.returncode}): {stderr}",
            fix_hint="Check if invocation-id is valid or has expired",
        )
    out = proc.stdout.strip()
    if not out:
        raise ApiError(
            f"get-execute-operation-result returned empty response: {invocation_id}",
            fix_hint="operationId may be invalid or expired",
        )
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        raise ApiError(
            f"get-execute-operation-result returned non-JSON: {out[:200]}",
            fix_hint="Check aliyun CLI version or network status",
        )
    # Detect business-layer errors (CLI exit 0 but response body is an error)
    code = parsed.get("Code") or parsed.get("code")
    if code is not None and code not in (200, "200", "Success", "success"):
        raise ApiError(
            f"get-execute-operation-result business error Code={code}: "
            f"{parsed.get('Message') or parsed.get('message') or ''}",
            fix_hint=f"operationId={invocation_id}; verify validity",
        )
    # Unwrap outer envelope; always return a normalized single-layer envelope (Status/Data/Message at same level)
    data = parsed.get("Data") if "Data" in parsed else parsed.get("data")
    if not isinstance(data, dict):
        data = {"Status": "success", "Data": data}
    data.setdefault("RequestId", parsed.get("RequestId") or parsed.get("requestId") or "")
    return data


def _unwrap_data(snapshot: Dict[str, Any]) -> Any:
    for k in ("Data", "data", "result", "Result"):
        if k in snapshot:
            return snapshot[k]
    return snapshot
