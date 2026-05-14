#!/usr/bin/env python3
"""Alibaba Cloud Function Compute (FC 3.0) management.

Capabilities:
  - list_regions  (region query)
  - create_function / get_function / list_functions  (function creation)
  - invoke_function  (script execution)
  - delete_function

FC 3.0 uses ROA-style API (version=2023-03-30).
Endpoint pattern: {account_id}.{region}.fc.aliyuncs.com
"""

from __future__ import annotations

import base64
import json
import sys
import os
import time
import zipfile
import tempfile
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from common import USER_AGENT, build_client, call_rpc_api, call_roa_api, get_default_region, pp

VERSION = "2023-03-30"

_cached_account_id: str | None = None
_async_task_configured: set[str] = set()


def _get_account_id() -> str:
    """Get Alibaba Cloud account ID.

    Priority: env var > STS GetCallerIdentity (cached after first call).
    """
    global _cached_account_id
    aid = os.environ.get("ALIBABA_CLOUD_ACCOUNT_ID", "")
    if aid:
        return aid
    if _cached_account_id:
        return _cached_account_id

    result = call_rpc_api(
        product="sts",
        version="2015-04-01",
        action="GetCallerIdentity",
        endpoint="sts.aliyuncs.com",
    )
    _cached_account_id = result.get("AccountId", "")
    if not _cached_account_id:
        raise RuntimeError("Failed to get AccountId from STS GetCallerIdentity")
    print(f"Account ID auto-detected: {_cached_account_id}")
    return _cached_account_id


def _get_endpoint(region: str | None = None, account_id: str | None = None) -> str:
    """Build FC endpoint: {account_id}.{region}.fc.aliyuncs.com"""
    r = region or get_default_region()
    aid = account_id or _get_account_id()
    return f"{aid}.{r}.fc.aliyuncs.com"


def _call(
    pathname: str,
    method: str = "GET",
    query: dict | None = None,
    body: dict | None = None,
    region: str | None = None,
    account_id: str | None = None,
    body_type: str = "json",
) -> dict | str:
    ep = _get_endpoint(region, account_id)
    return call_roa_api(
        version=VERSION,
        pathname=pathname,
        method=method,
        query=query,
        body=body,
        region=region,
        endpoint=ep,
        body_type=body_type,
    )


# ---------------------------------------------------------------------------
# Region query
# ---------------------------------------------------------------------------

def list_regions(region: str | None = None, account_id: str | None = None) -> list:
    """List available FC regions.

    Note: FC doesn't have a dedicated ListRegions API at 2023-03-30 level.
    Use ECS DescribeRegions as a proxy, or hardcode common regions.
    """
    common_regions = [
        "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen",
        "cn-chengdu", "cn-hongkong", "ap-southeast-1", "us-west-1",
        "eu-central-1", "ap-northeast-1",
    ]
    print(f"FC commonly available regions: {common_regions}")
    return common_regions


# ---------------------------------------------------------------------------
# Function management
# ---------------------------------------------------------------------------

def create_function(
    function_name: str,
    runtime: str = "python3.10",
    handler: str = "index.handler",
    code_dir: str | None = None,
    code_zip_path: str | None = None,
    code_inline: str | None = None,
    memory_size: int = 512,
    cpu: float = 0.35,
    timeout: int = 300,
    disk_size: int = 512,
    gpu_memory_size: int | None = None,
    environment_variables: dict | None = None,
    description: str = "Created by Alibaba Cloud Compute Provision skill",
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Create a function in FC 3.0.

    Provide code via one of:
      - code_dir: local directory to zip and upload
      - code_zip_path: pre-built zip file path
      - code_inline: inline code string (will create a zip with index.py)

    For custom-runtime, set runtime='custom' and handler to your entrypoint.
    """
    body: dict[str, Any] = {
        "functionName": function_name,
        "runtime": runtime,
        "handler": handler,
        "memorySize": memory_size,
        "cpu": cpu,
        "timeout": timeout,
        "diskSize": disk_size,
        "description": description,
    }

    if gpu_memory_size:
        body["gpuConfig"] = {"gpuMemorySize": gpu_memory_size}

    if environment_variables:
        body["environmentVariables"] = environment_variables

    zip_bytes = None
    if code_inline:
        zip_bytes = _create_inline_zip(code_inline, handler)
    elif code_dir:
        zip_bytes = _zip_directory(code_dir)
    elif code_zip_path:
        with open(code_zip_path, "rb") as f:
            zip_bytes = f.read()

    if zip_bytes:
        encoded = base64.b64encode(zip_bytes).decode("utf-8")
        body["code"] = {"zipFile": encoded}

    result = _call(
        f"/2023-03-30/functions",
        method="POST",
        body=body,
        region=region,
        account_id=account_id,
    )
    print(f"Function created: {function_name}")
    return result


def get_function(
    function_name: str,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Get function details."""
    return _call(
        f"/2023-03-30/functions/{function_name}",
        region=region,
        account_id=account_id,
    )


def list_functions(
    prefix: str | None = None,
    limit: int = 50,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """List functions."""
    query: dict[str, Any] = {"limit": limit}
    if prefix:
        query["prefix"] = prefix
    return _call(
        "/2023-03-30/functions",
        query=query,
        region=region,
        account_id=account_id,
    )


def delete_function(
    function_name: str,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Delete a function."""
    return _call(
        f"/2023-03-30/functions/{function_name}",
        method="DELETE",
        region=region,
        account_id=account_id,
        body_type="none",
    )


def put_async_invoke_config(
    function_name: str,
    async_task: bool = True,
    max_async_retry_attempts: int = 0,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Configure async invocation for a function.

    Required for GetAsyncTask to work — must enable asyncTask before async invoke.
    """
    body = {
        "asyncTask": async_task,
        "maxAsyncRetryAttempts": max_async_retry_attempts,
    }
    result = _call(
        f"/2023-03-30/functions/{function_name}/async-invoke-config",
        method="PUT",
        body=body,
        region=region,
        account_id=account_id,
    )
    if async_task:
        _async_task_configured.add(function_name)
    print(f"Async invoke config set for {function_name}: asyncTask={async_task}")
    return result


def delete_async_invoke_config(
    function_name: str,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Delete async invocation config for a function."""
    return _call(
        f"/2023-03-30/functions/{function_name}/async-invoke-config",
        method="DELETE",
        region=region,
        account_id=account_id,
        body_type="none",
    )


# ---------------------------------------------------------------------------
# Function invocation (script execution)
# ---------------------------------------------------------------------------

def invoke_function(
    function_name: str,
    payload: str | dict | None = None,
    invocation_type: str | None = None,
    log_type: str = "Tail",
    qualifier: str | None = None,
    async_task_id: str | None = None,
    timeout: int | None = None,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Invoke a function.

    Args:
        function_name: Function to invoke.
        payload: Event payload (string or dict).
        invocation_type: Sync | Async. If None, auto-selects based on timeout:
            timeout > 60s → Async, otherwise Sync.
        log_type: None | Tail (return execution logs, Sync only).
        qualifier: Version or alias.
        async_task_id: Custom task ID for async invocations (for tracking).
            Auto-generated if not provided for async calls.
        timeout: Function timeout in seconds. Used for auto Sync/Async decision.
            If not set, reads from function config or defaults to Sync.

    Returns:
        For Sync: response body.
        For Async: dict with taskId for polling via get_async_task.
    """
    if invocation_type is None:
        invocation_type = "Async" if (timeout and timeout > 60) else "Sync"

    if invocation_type == "Async" and not async_task_id:
        import uuid
        async_task_id = f"acf-{uuid.uuid4().hex[:16]}"

    ep = _get_endpoint(region, account_id)
    r = region or get_default_region()

    from alibabacloud_tea_openapi import models as open_api_models
    from darabonba.runtime import RuntimeOptions

    client = build_client(ep, r)

    query_params: dict[str, str] = {}
    if qualifier:
        query_params["qualifier"] = qualifier

    headers: dict[str, str] = {
        "x-fc-invocation-type": invocation_type,
    }
    if invocation_type == "Sync":
        headers["x-fc-log-type"] = log_type
    if async_task_id:
        headers["x-fc-async-task-id"] = async_task_id

    body_str = ""
    if payload:
        body_str = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    body_type = "none" if invocation_type == "Async" else "json"

    api_params = open_api_models.Params(
        action="InvokeFunction",
        version=VERSION,
        protocol="HTTPS",
        pathname=f"/2023-03-30/functions/{function_name}/invocations",
        method="POST",
        auth_type="AK",
        style="ROA",
        body_type=body_type,
        req_body_type="json",
    )
    request = open_api_models.OpenApiRequest(
        query=query_params if query_params else None,
        headers=headers,
        body=body_str,
    )
    result = client.call_api(api_params, request, RuntimeOptions())
    body = result.get("body", result)

    if invocation_type == "Async":
        print(f"Function {function_name} invoked asynchronously, taskId: {async_task_id}")
        return {"taskId": async_task_id, "invocationType": "Async"}
    else:
        print(f"Function {function_name} invoked synchronously")
        return body


def get_async_task(
    function_name: str,
    task_id: str,
    qualifier: str | None = None,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Get async task status and result.

    Returns dict with: taskId, status, startedTime, endTime, durationMs,
    taskErrorMessage, taskPayload, returnPayload, etc.

    Status values: Running, Succeeded, Failed, Stopped, Expired, Retrying.
    """
    query: dict[str, str] = {}
    if qualifier:
        query["qualifier"] = qualifier
    return _call(
        f"/2023-03-30/functions/{function_name}/async-tasks/{task_id}",
        query=query or None,
        region=region,
        account_id=account_id,
    )


def invoke_function_and_wait(
    function_name: str,
    payload: str | dict | None = None,
    timeout: int = 300,
    qualifier: str | None = None,
    region: str | None = None,
    account_id: str | None = None,
    poll_interval: int = 5,
) -> dict:
    """Invoke a function and wait for result.

    Auto-selects Sync or Async based on timeout (>60s → Async).
    For async calls, enables asyncTask config then polls GetAsyncTask until completion.
    """
    invocation_type = "Sync" if timeout <= 60 else "Async"

    if invocation_type == "Async" and function_name not in _async_task_configured:
        put_async_invoke_config(function_name, async_task=True, region=region, account_id=account_id)

    result = invoke_function(
        function_name=function_name,
        payload=payload,
        timeout=timeout,
        qualifier=qualifier,
        region=region,
        account_id=account_id,
    )

    if not isinstance(result, dict) or result.get("invocationType") != "Async":
        return result

    task_id = result["taskId"]
    print(f"Waiting for async task {task_id}...")
    time.sleep(3)
    deadline = time.time() + timeout + 60
    terminal_statuses = {"Succeeded", "Failed", "Stopped", "Expired"}

    while time.time() < deadline:
        try:
            task = get_async_task(function_name, task_id, qualifier, region, account_id)
        except Exception as e:
            if "AsyncTaskNotFound" in str(e):
                print("  Async task not yet registered, retrying...")
                time.sleep(poll_interval)
                continue
            raise
        status = task.get("status", "")
        print(f"  Async task status: {status}")
        if status in terminal_statuses:
            if status != "Succeeded":
                err = task.get("taskErrorMessage", "unknown error")
                raise RuntimeError(f"Async task {task_id} {status}: {err}")
            return task
        time.sleep(poll_interval)

    raise TimeoutError(f"Async task {task_id} timed out after {timeout + 60}s")


def _generate_function_name(prefix: str = "acf-task") -> str:
    """Generate a unique function name with timestamp suffix."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    import uuid
    short_id = uuid.uuid4().hex[:6]
    return f"{prefix}-{ts}-{short_id}"


def create_and_invoke(
    function_name: str | None = None,
    script_content: str | None = None,
    script_path: str | None = None,
    script_type: str = "python",
    runtime: str = "python3.10",
    handler: str = "index.handler",
    memory_size: int = 512,
    cpu: float = 0.35,
    timeout: int = 300,
    payload: str | dict | None = None,
    auto_cleanup: bool = True,
    region: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Create a function from code, invoke it, wait for result, optionally cleanup.

    Args:
        function_name: Function name. Auto-generated with timestamp if None.
        script_content: Handler code string. Mutually exclusive with script_path.
        script_path: Path to a local script file. Auto-wrapped via
            wrap_shell_script (for .sh) or wrap_python_script (for .py).
            script_type is inferred from file extension when script_path is used.
        script_type: "shell" | "python". Used when script_content is raw
            user code (not yet wrapped). Ignored if script_content is already
            a handler function or if script_path determines the type.
        auto_cleanup: If True (default), delete_function after execution.
        Other args: passed to create_function / invoke_function_and_wait.

    Returns:
        Execution result dict.
    """
    if function_name is None:
        function_name = _generate_function_name()

    if script_path:
        with open(script_path, "r", encoding="utf-8") as f:
            raw_script = f.read()
        if script_path.endswith(".sh"):
            script_type = "shell"
        elif script_path.endswith(".py"):
            script_type = "python"
        script_content = _auto_wrap(raw_script, script_type, timeout)
    elif script_content and "def handler(" not in script_content:
        script_content = _auto_wrap(script_content, script_type, timeout)

    if not script_content:
        raise ValueError("Either script_content or script_path must be provided")

    mem_gb = memory_size / 1024
    ratio = mem_gb / cpu if cpu > 0 else 0
    if ratio < 1 or ratio > 4:
        raise ValueError(
            f"FC requires Memory(GB)/CPU ratio between 1 and 4, "
            f"got {mem_gb:.2f}GB/{cpu}core = {ratio:.2f}. "
            f"Tip: use the defaults (memory_size=512, cpu=0.35) or "
            f"adjust to satisfy the constraint, e.g. memory_size=512, cpu=0.35."
        )

    create_function(
        function_name=function_name,
        runtime=runtime,
        handler=handler,
        code_inline=script_content,
        memory_size=memory_size,
        cpu=cpu,
        timeout=timeout,
        region=region,
        account_id=account_id,
    )
    time.sleep(2)
    try:
        result = invoke_function_and_wait(
            function_name=function_name,
            payload=payload,
            timeout=timeout,
            region=region,
            account_id=account_id,
        )
        return result
    finally:
        if auto_cleanup:
            try:
                if function_name in _async_task_configured:
                    delete_async_invoke_config(function_name, region=region, account_id=account_id)
                    _async_task_configured.discard(function_name)
                delete_function(function_name, region=region, account_id=account_id)
                print(f"Function {function_name} auto-cleaned up")
            except Exception as e:
                print(f"Warning: auto-cleanup of {function_name} failed: {e}")


def create_script_executor(
    function_name: str | None = None,
    runtime: str = "python3.10",
    memory_size: int = 512,
    cpu: float = 0.35,
    timeout: int = 600,
    region: str | None = None,
    account_id: str | None = None,
) -> str:
    """Create a reusable script executor function.

    The executor accepts scripts via payload, so one function can run
    many different scripts without recreation.

    Payload format:
        {"script": "echo hello", "type": "shell"}
        {"script": "print(1+1)", "type": "python"}

    Returns:
        The function_name (for use with invoke_function_and_wait).
    """
    if function_name is None:
        function_name = _generate_function_name("acf-executor")

    executor_code = '''
import subprocess, json, base64, time, sys, os

def handler(event, context):
    start = time.time()
    try:
        evt = json.loads(event) if isinstance(event, (str, bytes)) else event
    except Exception:
        evt = {}

    script = evt.get("script", "")
    script_b64 = evt.get("script_b64", "")
    script_type = evt.get("type", "shell")
    fc_timeout = int(evt.get("timeout", context.credentials.timeout if hasattr(context, "credentials") else 300))
    sub_timeout = max(fc_timeout - 20, 10)

    if script_b64:
        script = base64.b64decode(script_b64).decode("utf-8")

    if not script:
        return json.dumps({"error": "No script provided in payload"})

    env_info = {"python": sys.version, "cwd": os.getcwd(), "platform": sys.platform}

    if script_type == "shell":
        r = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True, timeout=sub_timeout,
        )
        elapsed = round(time.time() - start, 3)
        return json.dumps({
            "stdout": r.stdout, "stderr": r.stderr,
            "returncode": r.returncode, "elapsed_s": elapsed,
            "env": env_info,
        })
    else:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        from io import StringIO
        sys.stdout, sys.stderr = StringIO(), StringIO()
        exec_globals = {"__builtins__": __builtins__}
        try:
            exec(script, exec_globals)
            elapsed = round(time.time() - start, 3)
            return json.dumps({
                "stdout": sys.stdout.getvalue(), "stderr": sys.stderr.getvalue(),
                "returncode": 0, "elapsed_s": elapsed,
                "env": env_info,
            })
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            return json.dumps({
                "stdout": sys.stdout.getvalue(), "stderr": sys.stderr.getvalue() + str(e),
                "returncode": 1, "error": str(e), "elapsed_s": elapsed,
                "env": env_info,
            })
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
'''
    create_function(
        function_name=function_name,
        runtime=runtime,
        handler="index.handler",
        code_inline=executor_code,
        memory_size=memory_size,
        cpu=cpu,
        timeout=timeout,
        region=region,
        account_id=account_id,
    )
    print(f"Script executor created: {function_name}")
    return function_name


# ---------------------------------------------------------------------------
# Script wrapping helpers
# ---------------------------------------------------------------------------

def wrap_shell_script(script: str, timeout: int = 300) -> str:
    """Wrap a shell script into an FC handler using base64 encoding.

    Uses base64 to safely embed any shell content (avoids triple-quote,
    backtick, and dollar-sign escaping issues). subprocess timeout is
    derived from FC timeout with a 20s safety margin.
    Includes execution timing, environment info, and stderr capture.
    """
    encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
    sub_timeout = max(timeout - 20, 10)
    return f'''import subprocess, json, base64, time, sys, os

def handler(event, context):
    start = time.time()
    script = base64.b64decode("{encoded}").decode("utf-8")
    r = subprocess.run(
        ["bash", "-c", script],
        capture_output=True, text=True, timeout={sub_timeout},
    )
    elapsed = round(time.time() - start, 3)
    return json.dumps({{
        "stdout": r.stdout, "stderr": r.stderr,
        "returncode": r.returncode, "elapsed_s": elapsed,
        "env": {{"python": sys.version, "cwd": os.getcwd()}},
    }})
'''


def wrap_python_script(script: str, timeout: int = 300) -> str:
    """Wrap a Python script into an FC handler using base64 encoding.

    Captures stdout/stderr via StringIO redirection. Includes execution
    timing and environment info for debugging.
    """
    encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
    return f'''import json, base64, time, sys, os
from io import StringIO

def handler(event, context):
    start = time.time()
    script = base64.b64decode("{encoded}").decode("utf-8")
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    try:
        exec(script, {{"__builtins__": __builtins__}})
        elapsed = round(time.time() - start, 3)
        return json.dumps({{
            "stdout": sys.stdout.getvalue(), "stderr": sys.stderr.getvalue(),
            "returncode": 0, "elapsed_s": elapsed,
            "env": {{"python": sys.version, "cwd": os.getcwd()}},
        }})
    except Exception as e:
        elapsed = round(time.time() - start, 3)
        return json.dumps({{
            "stdout": sys.stdout.getvalue(),
            "stderr": sys.stderr.getvalue() + "\\n" + str(e),
            "returncode": 1, "error": str(e), "elapsed_s": elapsed,
            "env": {{"python": sys.version, "cwd": os.getcwd()}},
        }})
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
'''


def _auto_wrap(script: str, script_type: str, timeout: int) -> str:
    """Auto-wrap a raw script into FC handler format."""
    if script_type == "shell":
        return wrap_shell_script(script, timeout)
    else:
        return wrap_python_script(script, timeout)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_inline_zip(code: str, handler: str) -> bytes:
    """Create a zip file from inline code string.

    For handler='index.handler', creates index.py with the code.
    """
    module_name = handler.split(".")[0] if "." in handler else "index"
    filename = f"{module_name}.py"

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.close()
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, code)
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)


def _zip_directory(dir_path: str) -> bytes:
    """Zip a directory into bytes."""
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.close()
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            base = os.path.abspath(dir_path)
            for root, dirs, files in os.walk(base):
                for fn in files:
                    full = os.path.join(root, fn)
                    arcname = os.path.relpath(full, base)
                    zf.write(full, arcname)
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)
