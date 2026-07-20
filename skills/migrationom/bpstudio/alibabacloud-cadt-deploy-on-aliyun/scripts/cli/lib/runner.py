"""Runner — orchestrates a single Op call.

Pipeline (mirrors SPEC §4.3 "5 gates"):
  1. load contract           (lib.manifest.load_op)
  2. validate input          (lib.validator)
  3. pre-hook (optional)     (hooks/pre/<Op>.py)
  4. invoke aliyun bpstudio  (subprocess; sync or async + poll)
  5. post-hook (optional)    (hooks/post/<Op>.py)

This module ONLY raises CadtError subclasses; cadt-deploy-on-aliyun.main() converts to envelope.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from typing import Any, Dict, Tuple

from . import attrs as attrs_mod
from . import poller
from . import validator
from .normalize import normalize_ecs_run_result
from .envelope import stopwatch
from .errors import (
    ApiError,
    BusinessFailure,
    CadtError,
    HookReject,
    PostVerifyFailed,
)
from .hooks import run_pre_hooks, run_post_hooks
from .identity import get_uid
from .manifest import load_op, resolve_op_name


ALIYUN_BIN = shutil.which("aliyun") or "aliyun"

# Observability: session-id injected by the agent at invocation time.
_SKILL_NAME = "alibabacloud-cadt-deploy-on-aliyun"
def _session_id() -> str:
    return os.environ.get("SKILL_SESSION_ID", "")

# Internal service_type routing table: hidden from upper layers.
# For historical reasons, the backend API's service-type is split into three categories:
#   - ecs  : ops in the ECS_OPS dict
#   - oss  : ops in the OSS_OPS dict
#   - qoder: default, everything else
# key = cadt-deploy-on-aliyun canonical name (PascalCase), value = backend-expected operation name (camelCase/snake_case)
ECS_OPS: dict[str, str] = {
    "EcsRunCommand": "runCommand",
    "EcsRunCommandSync": "runCommand",
    "EcsSendFile": "sendFile",
    "EcsGetDesc": "getDesc",
    "EcsGetDescList": "getDescList",
}

OSS_OPS: dict[str, str] = {
    "OssGeneratePresignedUrl": "generate_presigned_url",
}


def _service_type_of(op_name: str) -> str:
    if op_name in ECS_OPS:
        return "ecs"
    if op_name in OSS_OPS:
        return "oss"
    return "qoder"


def _backend_op_name(op_name: str) -> str:
    """Map cadt-deploy-on-aliyun canonical name → backend-expected --operation name.
    ecs-type Ops use camelCase, oss-type use snake_case, qoder-type use PascalCase directly.
    """
    return ECS_OPS.get(op_name) or OSS_OPS.get(op_name, op_name)


def run_op(op_name: str, args: Dict[str, Any], *, timeout: int = 300) -> Dict[str, Any]:
    """Execute a single Op end-to-end. Returns success envelope dict.

    Raises CadtError on any failure path; caller is responsible for
    converting to err() envelope.
    """
    sw = stopwatch()
    # Case-insensitive resolution: user can pass any casing, but canonical name from manifest is sent to backend
    op_name = resolve_op_name(op_name)
    spec = load_op(op_name)

    # ---- 1. coerce string fields (dict→JSON string before validation)
    input_schema = spec.get("input_schema") or {}
    attrs_mod.coerce_string_fields(args, input_schema)

    # ---- 2. forbidden + schema validation
    validator.validate_input(args, spec)

    # ---- 2.5 coerce array fields → comma-separated strings (post-validation,
    #        so schema still sees the original list; gateway requires plain strings)
    attrs_mod.coerce_array_fields(args, input_schema)

    # ---- 3. inject auto fields (uid / clientToken / serviceType)
    enriched, control = _enrich_args(args, spec)

    # ---- 4. optional pre-hook
    hook_ctx = {
        "op_name": op_name,
        "exec_mode": spec.get("exec_mode", "sync"),
        "service_type": _service_type_of(op_name),
    }
    enriched = run_pre_hooks(op_name, enriched, hook_ctx)

    # ---- 4.5 pre-hook bypass (e.g. EcsSendFile > 32KB routes via OSS + EcsRunCommandSync)
    bypass = enriched.pop("__bypass_result__", None)
    if bypass is not None:
        bypass.setdefault("meta", {})["elapsedMs"] = sw.elapsed_ms
        return bypass

    # ---- 5. invoke
    exec_mode = spec.get("exec_mode", "sync")
    if exec_mode == "async":
        # async Op returns operationId immediately by default (matches doc convention);
        # pass _no_wait=false to force blocking wait.
        no_wait = control.get("_no_wait")
        if no_wait is None:
            no_wait = True  # default: non-blocking
        invocation_id, business, request_id = _invoke_async(
            op_name,
            enriched,
            spec,
            no_wait=bool(no_wait),
            timeout=control.get("_timeout") or timeout,
        )
        meta = {
            "operation": op_name,
            "exec_mode": "async",
            "invocationId": invocation_id,
            "requestId": request_id,
            "elapsedMs": sw.elapsed_ms,
        }
        if no_wait:
            return {
                "ok": True,
                "data": {"status": "submitted", "invocationId": invocation_id,
                         "next": f"cadt_deploy_on_aliyun -poll {invocation_id}",
                         "next_action_required": f"YOU MUST execute: cadt-deploy-on-aliyun -poll {invocation_id}"},
                "meta": meta,
            }
    else:
        business, request_id = _invoke_sync(op_name, enriched, spec)
        meta = {
            "operation": op_name,
            "exec_mode": "sync",
            "requestId": request_id,
            "elapsedMs": sw.elapsed_ms,
        }

    # ---- 6. output schema check (best-effort, non-fatal in Phase 0)
    try:
        validator.validate_output(business, spec)
    except CadtError:
        # Phase 0 chooses to log-and-pass; Phase 1+ may promote to fatal.
        pass

    # ---- 7. optional post-hook (postverify)
    business = run_post_hooks(op_name, args, business, hook_ctx)

    return {"ok": True, "data": business, "meta": meta}


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _enrich_args(args: Dict[str, Any], spec: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Apply auto_inject (uid/clientToken/serviceType) and pull control fields."""
    control = attrs_mod.extract_control(args)
    enriched = {k: v for k, v in args.items() if k not in control}

    # qoder-type and oss-type ops require uid — always inject from identity resolver.
    if _service_type_of(spec.get("name", "")) in ("qoder", "oss"):
        enriched["uid"] = get_uid()

    # client_token for idempotency (only if spec declares it)
    auto = spec.get("auto_inject") or {}
    if "client_token" in auto:
        enriched.setdefault("clientToken", str(uuid.uuid4()))
    return enriched, control


def _invoke_sync(op_name: str, args: Dict[str, Any], spec: Dict[str, Any]) -> Tuple[Any, str]:
    cmd = _build_cmd(op_name, args, async_mode=False, spec=spec)
    raw = _exec(cmd)
    request_id = raw.get("RequestId") or raw.get("requestId") or ""
    business = _unwrap_sync(raw, op_name)
    return normalize_ecs_run_result(business), str(request_id)


def _invoke_async(
    op_name: str,
    args: Dict[str, Any],
    spec: Dict[str, Any],
    *,
    no_wait: bool,
    timeout: int,
) -> Tuple[str, Any, str]:
    cmd = _build_cmd(op_name, args, async_mode=True, spec=spec)
    raw = _exec(cmd)
    request_id = raw.get("RequestId") or raw.get("requestId") or ""
    invocation_id = _extract_invocation_id(raw, op_name)
    if no_wait:
        return invocation_id, None, str(request_id)
    business = poller.poll_until_done(invocation_id, timeout=timeout)
    return invocation_id, business, str(request_id)


def _build_cmd(op_name: str, args: Dict[str, Any], *, async_mode: bool, spec: Dict[str, Any]) -> list:
    mode = "execute-operation-async" if async_mode else "execute-operation-sync"
    service_type = _service_type_of(op_name)
    backend_name = _backend_op_name(op_name)
    # Workaround: aliyun CLI silently drops --attributes for bpstudio commands,
    # so we pass the full payload via --body instead.
    body: Dict[str, Any] = {
        "Operation": backend_name,
        "ServiceType": service_type,
    }
    attrs_json = attrs_mod.to_attrs_json(args)
    if attrs_json:
        body["Attributes"] = attrs_json
    cmd = [
        ALIYUN_BIN, "bpstudio", mode,
        "--body", json.dumps(body, ensure_ascii=False),
    ]
    # Observability: attach user-agent per SKILL.md §Observability
    sid = _session_id()
    if sid:
        cmd.extend(["--user-agent", f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{sid}"])
    return cmd


def _exec(cmd: list) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                              stdin=subprocess.DEVNULL)
    except FileNotFoundError as e:
        raise ApiError(
            f"aliyun CLI not found: {e}",
            fix_hint="Install aliyun CLI first (brew install aliyun-cli or download official package)",
        )
    except subprocess.TimeoutExpired:
        raise ApiError(
            "aliyun bpstudio call timed out (120s)",
            fix_hint="Network or backend issue; retry, or use cadt_deploy_on_aliyun -poll <id> for async tasks",
        )

    if proc.returncode != 0:
        # Try to extract business error from stdout (some scenarios CLI returns non-zero but stdout still has JSON)
        detail = proc.stderr.strip()[:300]
        stdout = proc.stdout.strip()
        if stdout:
            try:
                body = json.loads(stdout)
                data = body.get("Data") or body.get("data")
                if isinstance(data, dict):
                    msg = data.get("Message") or data.get("message")
                    if msg:
                        detail = msg
            except (json.JSONDecodeError, AttributeError):
                pass
        raise ApiError(
            f"aliyun bpstudio returned non-zero ({proc.returncode}): {detail}",
            fix_hint="Check parameters / network / auth (aliyun configure list)",
        )
    out = proc.stdout.strip()
    if not out:
        raise ApiError("aliyun bpstudio returned empty output", fix_hint="Possible CLI anomaly; retry or run -doctor")
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise ApiError(
            f"aliyun bpstudio output is not JSON: {e}",
            fix_hint="Check CLI version is up to date (aliyun version)",
        )


def _unwrap_sync(raw: Dict[str, Any], op_name: str) -> Any:
    """Unwrap aliyun bpstudio sync response.

    aliyun CLI returns: {Code, Data: {Arguments, Message, OperationId, Status}}
    We want to surface `Arguments` as the business payload.
    If Status=FAILURE, raise BusinessFailure with Message.
    """
    # Layer 1: outer API envelope — pull Data
    data = raw.get("Data") or raw.get("data") or raw

    # Layer 2: check business Status inside Data
    status = (data.get("Status") or data.get("status") or "").upper()
    if status == "FAILURE":
        msg = data.get("Message") or data.get("message") or f"{op_name} business failure"
        raise BusinessFailure(msg, fix_hint=str(data.get("Code") or ""),
                               details=normalize_ecs_run_result(data.get("Arguments")))

    # Layer 3: extract Arguments (the actual business response)
    arguments = data.get("Arguments")
    if arguments is not None:
        return arguments
    # Fallback for non-standard shapes
    return data


def _extract_invocation_id(raw: Dict[str, Any], op_name: str) -> str:
    inv = raw.get("InvocationId") or raw.get("invocationId") or raw.get("invocation_id")
    if not inv:
        # aliyun bpstudio execute-operation-async returns {"Code":200, "Data":"op/..."}
        # invocationId is the Data field itself (string starting with "op/")
        data = raw.get("Data") or raw.get("data")
        if isinstance(data, str) and data.startswith("op/"):
            inv = data
    if not inv:
        raise ApiError(
            f"async call did not return invocationId (op={op_name}); raw response: {json.dumps(raw, ensure_ascii=False)[:200]}",
            fix_hint="Check aliyun CLI version or --service-type/--operation parameters",
        )
    return str(inv)


# ---------------------------------------------------------------------------
# Hook plumbing — delegated to lib.hooks (dynamic loader).
# Phase 0 stubs removed; hooks now live in hooks/pre/<Op>.py & hooks/post/<Op>.py.
# ---------------------------------------------------------------------------
