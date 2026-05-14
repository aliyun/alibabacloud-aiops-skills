# FC (Function Compute) Reference

Script: `scripts/fc.py` | API style: ROA | Version: FC/2023-03-30

FC is suited for short-lived, Serverless compute tasks. Billed by invocation count plus execution duration; short tasks are the most cost-effective.

The Account ID is fetched automatically via STS GetCallerIdentity, so no manual configuration is required.

## End-to-end Workflow

```
1. Cost confirmation -> 2. create_and_invoke(script_path/script_content) -> automatic steps:
   wrap script (base64) -> create function (with timestamped name) -> [enable asyncTask config when async]
   -> invoke (auto Sync/Async) -> wait for result -> auto cleanup (async config + function)
```

> **Invocation strategy**: timeout <= 60s triggers a sync invocation automatically; timeout > 60s triggers an async invocation plus GetAsyncTask polling.
> Using `create_and_invoke` or `invoke_function_and_wait` hides the sync/async details: asyncTask config, polling fault tolerance, and resource cleanup are all handled for you.

## API Quick Reference

### create_function(...) -> dict

Create a function. Code is supplied through `code_inline` (most common), `code_dir`, or `code_zip_path`.

```python
from fc import create_function

result = create_function(
    function_name="acf-task",             # required, function name
    runtime="python3.10",                 # python3.10 | python3.9 | nodejs18 | custom | ...
    handler="index.handler",              # entry point: module.function_name
    code_inline=script_content,           # inline code string (auto-zipped)
    code_dir=None,                        # local directory path (auto-zipped)
    code_zip_path=None,                   # path to a pre-built zip file
    memory_size=512,                      # memory in MB (128~32768); see ratio constraint below
    cpu=0.35,                             # vCPU (0.05~16); see ratio constraint below
    timeout=300,                          # timeout in seconds (max 86400 for async)
    disk_size=512,                        # disk in MB (512 | 10240)
    gpu_memory_size=None,                 # GPU memory in MB (requires a GPU instance)
    environment_variables=None,           # dict of environment variables
    description="Created by Alibaba Cloud Compute Provision skill",
    region=None,
    account_id=None,
)
```

> **⛔ Memory/CPU ratio constraint**: FC requires `Memory(GB) / CPU(core)` to be between **1 and 4**. The defaults (`memory_size=512`, `cpu=0.35` → ratio 1.43) are safe. If you change one, check the ratio. Common safe combos: `128MB/0.05cpu`, `512MB/0.35cpu`, `1024MB/0.5cpu`, `2048MB/1cpu`. Using `memory_size=128` with `cpu=0.35` will fail (ratio 0.36 < 1).

### invoke_function(...) -> dict

Invoke a function. **When timeout > 60 seconds the call is automatically switched to async.**

```python
from fc import invoke_function

# Short task (<=60s) -> auto sync invocation, returns the result directly
result = invoke_function(
    function_name="acf-task",
    payload={"key": "value"},             # event data (str or dict)
    timeout=30,                           # <=60 -> Sync, >60 -> Async (auto-detected)
    # invocation_type="Sync",             # may also be set manually to override auto-detection
    log_type="Tail",                      # None | Tail (returns execution log, Sync only)
    qualifier=None,
    region=None,
    account_id=None,
)

# Long task (>60s) -> auto async invocation, returns {taskId, invocationType: "Async"}
result = invoke_function(
    function_name="acf-task",
    payload={"key": "value"},
    timeout=600,                          # >60 -> auto async
    async_task_id="my-custom-id",         # optional, custom task ID (auto-generated if omitted)
)
# result["taskId"] -> used for get_async_task lookups
```

### invoke_function_and_wait(...) -> dict

**Recommended entry point.** Invokes a function and waits for the result. Short tasks return synchronously; long tasks switch to async automatically and poll GetAsyncTask.

For async invocations the following are handled automatically:
1. `put_async_invoke_config` is called automatically to enable asyncTask (a precondition for GetAsyncTask).
2. A 3-second wait before polling (to absorb task registration latency).
3. `AsyncTaskNotFound` errors are retried automatically without breaking the polling loop.

```python
from fc import invoke_function_and_wait

result = invoke_function_and_wait(
    function_name="acf-task",
    payload={"input": "data"},
    timeout=600,                          # function timeout in seconds (>60 -> auto async)
    poll_interval=5,                      # async polling interval in seconds
    region=None,
    account_id=None,
)
```

### get_async_task(function_name, task_id, ...) -> dict

Query the status of an async task. Status values: `Running` | `Succeeded` | `Failed` | `Stopped` | `Expired` | `Retrying`.

```python
from fc import get_async_task

task = get_async_task("acf-task", "my-task-id")
# task -> {taskId, status, startedTime, endTime, durationMs, taskErrorMessage, returnPayload, ...}
```

### create_and_invoke(...) -> dict

**Recommended one-stop entry point.** Automatically wraps the script, generates a function name, creates the function, invokes and waits, and cleans up.

```python
from fc import create_and_invoke

# Option 1: pass a script file path directly (recommended; auto-detects .sh / .py and base64-wraps it)
result = create_and_invoke(
    script_path="/path/to/script.sh",     # auto read, base64-wrap, infer type
    # function_name=None,                 # if omitted, auto-generated: acf-task-20260423-143052-a1b2c3
    memory_size=512,
    cpu=0.35,
    timeout=60,
    # auto_cleanup=True,                  # delete_function is called automatically after execution by default
)

# Option 2: pass raw script content (auto base64-wrapped)
result = create_and_invoke(
    script_content="echo hello world",    # raw shell script
    script_type="shell",                  # "shell" | "python"
    timeout=60,
)

# Option 3: pass already-wrapped handler code (wrapping is skipped when `def handler(` is detected)
result = create_and_invoke(
    script_content=handler_code,          # already contains def handler(event, context)
    timeout=600,                          # >60s -> auto async + poll-and-wait
    auto_cleanup=False,                   # keep the function instead of deleting it
)
```

| Parameter | Description |
|------|------|
| `function_name` | Function name. `None` triggers auto-generation `acf-task-{timestamp}-{uuid6}` |
| `script_path` | Local script file path; the file is read and wrapped according to its extension |
| `script_content` | Script content string; mutually exclusive with `script_path` |
| `script_type` | `"shell"` \| `"python"`; auto-inferred when `script_path` is provided |
| `memory_size` | Memory in MB. Default `512`. Must satisfy Memory(GB)/CPU ratio ∈ [1, 4] |
| `cpu` | vCPU cores. Default `0.35`. Must satisfy Memory(GB)/CPU ratio ∈ [1, 4] |
| `auto_cleanup` | Defaults to `True`; cleans up after execution (deletes the async config first, then the function) |

> **Tip**: For simple scripts, use the defaults (`memory_size=512, cpu=0.35`) — they are safe and cheap. Only increase memory/CPU for compute-heavy or memory-heavy tasks.

### wrap_shell_script(script, timeout) -> str

Embeds a shell script safely into the FC handler via **base64 encoding**, eliminating escaping issues with triple quotes, backticks, `$`, and other special characters. The subprocess timeout is derived from the FC timeout automatically (timeout - 20s safety margin). The result includes `elapsed_s` and `env` diagnostics.

```python
from fc import wrap_shell_script

handler_code = wrap_shell_script("echo 'hello $USER'", timeout=60)
# -> in handler: base64.b64decode("...").decode() then execute
# -> returns: {stdout, stderr, returncode, elapsed_s, env}
```

### wrap_python_script(script, timeout) -> str

Embeds a Python script into the FC handler via base64 encoding. stdout/stderr are captured through StringIO.

```python
from fc import wrap_python_script

handler_code = wrap_python_script("print('hello')\nresult = 1+1", timeout=60)
```

### create_script_executor(...) -> str

**Reusable executor.** Creates a generic function that can run different scripts repeatedly through the payload, without recreating the function each time.

```python
from fc import create_script_executor, invoke_function_and_wait, delete_function

# 1. Create the executor (once)
executor_name = create_script_executor(
    memory_size=1024, cpu=1, timeout=600,
)

# 2. Run different scripts via payload (reused many times)
r1 = invoke_function_and_wait(executor_name, payload={"script": "echo hello", "type": "shell"}, timeout=30)
r2 = invoke_function_and_wait(executor_name, payload={"script": "print(1+1)", "type": "python"}, timeout=30)

# The payload also accepts base64 (handy for scripts with special characters):
import base64
b64 = base64.b64encode("echo 'special $chars'".encode()).decode()
r3 = invoke_function_and_wait(executor_name, payload={"script_b64": b64, "type": "shell"}, timeout=30)

# 3. Delete when finished
delete_function(executor_name)
```

### put_async_invoke_config(function_name, ...) -> dict

Enables or configures async task tracking on a function. **This is a precondition for `GetAsyncTask`**; without it async tasks have no recorded state.

> `invoke_function_and_wait` and `create_and_invoke` already call this automatically, so manual use is rarely needed.

```python
from fc import put_async_invoke_config

put_async_invoke_config(
    function_name="acf-task",
    async_task=True,                      # enable async task tracking
    max_async_retry_attempts=0,           # number of retry attempts on failure (0 = no retry)
)
```

### delete_async_invoke_config(function_name, ...) -> dict

Deletes the async invocation config. `create_and_invoke` calls this automatically when `auto_cleanup=True`.

### Other APIs

- `get_function(function_name, region, account_id)` -> dict - retrieve function details
- `list_functions(prefix, limit, region, account_id)` -> dict - list functions
- `delete_function(function_name, region, account_id)` -> dict - delete a function
- `list_regions()` -> list - return the list of commonly used available regions

## Wrapping a Script as a handler

When `create_and_invoke` is called with `script_path` or raw `script_content`, the wrapping is **performed automatically**, so no manual handler construction is required.

If manual wrapping is needed, use `wrap_shell_script` / `wrap_python_script`:

```python
from fc import wrap_shell_script, wrap_python_script

# Shell script - base64 safe encoding, no escaping issues
handler_code = wrap_shell_script('echo "hello $USER" && ls -la', timeout=60)

# Python script - captures stdout/stderr
handler_code = wrap_python_script('import math\nprint(math.pi)', timeout=60)
```

The wrapped handler returns a unified shape:
```json
{
    "stdout": "...",
    "stderr": "...",
    "returncode": 0,
    "elapsed_s": 1.234,
    "env": {"python": "3.10.x", "cwd": "/"}
}
```

> **Why base64**: embedding the script directly inside `"""script"""` breaks when the script contains triple quotes, `$`, or backticks.
> After base64 encoding all characters are safe; the handler restores the original via `base64.b64decode()` before executing it.

> **Timeout safety margin**: in `wrap_shell_script` / `wrap_python_script` the subprocess timeout is `FC_timeout - 20s`.
> For example, with FC timeout=120s the script effectively has 100s; the remaining 20s are reserved for handler initialization and result serialization.
> Mention this limit to the user during cost estimation.

## Cost Confirmation (Mandatory)

**Before creating a function you must estimate costs and obtain user confirmation; do not call create_function without it.**

FC is billed by invocation count plus execution duration (no describe_price API; estimate using public unit prices):

| Billing item | Unit price |
|--------|------|
| Invocations | CNY 0.0133 per 10,000 calls (first 1,000,000 per month free) |
| vCPU time | CNY 0.00003167 per vCPU-second |
| Memory time | CNY 0.00000397 per GB-second |
| GPU time | Charged separately based on GPU memory |

Estimation formula:
```
estimated_cost = vCPU * exec_seconds * CNY 0.00003167 + memory_GB * exec_seconds * CNY 0.00000397 + invocation_cost
```

Cost display template:
```
[FC cost estimate]
  Spec: 0.35 vCPU, 512MB memory
  Estimated execution time: ~10 seconds
  vCPU cost: 0.35 x 10 x CNY 0.00003167 = CNY 0.00011
  Memory cost: 0.5 x 10 x CNY 0.00000397 = CNY 0.00002
  Invocation cost: CNY 0 (within free quota)
  Estimated total: CNY 0.00013
  Billing mode: pay-as-you-go, stops automatically once execution finishes

Proceed with creation?
```

> FC short-task costs are extremely low, but estimation and disclosure to the user are still required.

## Sync vs Async Invocation

| Aspect | Sync | Async |
|--------|-----------|------------|
| Maximum timeout | 600 seconds (10 minutes) | 86400 seconds (24 hours) |
| Auto-switch threshold | timeout <= 60s | timeout > 60s |
| Return mode | Returns the result directly | Returns a taskId; poll via GetAsyncTask |
| Required configuration | None | Requires `PutAsyncInvokeConfig(asyncTask=true)` (handled automatically) |
| SDK body_type | `json` (parses JSON response) | `none` (async returns an empty body, not parsed) |
| Logs | Retrieved via x-fc-log-type: Tail | Retrieved via the logTail field within GetAsyncTask events |
| Use cases | Quick computations, simple scripts | Long-running training, batch jobs, data processing |

> `invoke_function_and_wait` handles all of the differences above (asyncTask config, body_type, polling fault tolerance) and is the recommended way to invoke functions.

### Internal Async Invocation Flow

When managing async invocations manually, keep in mind (`invoke_function_and_wait` / `create_and_invoke` already wrap all of this):

```
1. put_async_invoke_config(fn, asyncTask=True)   <- required, otherwise GetAsyncTask returns 404
2. invoke_function(fn, invocation_type="Async")   <- returns taskId
3. time.sleep(3)                                  <- task registration has some latency
4. poll get_async_task(fn, taskId)                <- tolerate AsyncTaskNotFound and retry
5. stop on status Succeeded/Failed/Stopped/Expired
6. cleanup: delete_async_invoke_config -> delete_function
```

## Resource Limits

| Dimension | Limit |
|------|------|
| vCPU | 16 max |
| Memory | 32 GB max |
| Sync invocation timeout | 600 seconds max (10 minutes) |
| Async invocation timeout | 86400 seconds max (24 hours) |
| Code package size | <= 50 MB compressed |
| Disk | 512 MB or 10 GB |

## Documentation Search

When you encounter unfamiliar parameters, unknown error codes, or need the latest API documentation, use `scripts/doc_search.py` to search the official Alibaba Cloud docs:

```python
from doc_search import search_and_format

# Search FC-related docs
print(search_and_format("CreateFunction runtime supported list", product="fc"))
print(search_and_format("InvokeFunction async invocation", product="fc"))
print(search_and_format("Function Compute GPU instance", product="fc"))

# Search by error code
print(search_and_format("ResourceExhausted concurrency limit", product="fc"))
```

The search returns titles, summaries, and links; use the web_fetch tool to view the full documentation content.

## Choosing a Usage Pattern

| Scenario | Recommended API | Notes |
|------|----------|------|
| Run a one-off script | `create_and_invoke(script_path=...)` | Auto wrap, create, configure asyncTask, execute, and clean up |
| Run multiple different scripts on the same function | `create_script_executor` + `invoke_function_and_wait` | Create once, reuse via payload, asyncTask managed automatically |
| Fine-grained control over function lifecycle | `create_function` + `put_async_invoke_config` + `invoke_function` + `get_async_task` + `delete_function` | Manual management; for async you **must** enable asyncTask first |

## Common Error Handling

| Error | Cause | Resolution |
|------|------|------|
| FunctionNotFound | The function does not exist | Verify that function_name is correct |
| FunctionAlreadyExists | Function name conflict | Use auto-naming (`function_name=None`) or delete the existing function first |
| AsyncTaskNotFound | GetAsyncTask returns 404 | asyncTask config is not enabled or the task is not registered yet. `invoke_function_and_wait` already handles this (enables config + retry tolerance) |
| Empty body JSON parse failure | Async invocation/DELETE returns an empty body | SDK body_type should be `"none"` rather than `"json"`. Already handled inside `invoke_function` and `delete_function` |
| ResourceExhausted | Concurrency limit exceeded | Wait and retry, or request a quota increase |
| RequestTimeout | Execution timed out | Increase timeout (>60s switches to async automatically) |
| CodeSizeExceed | Code package too large | Trim the code or deploy via OSS |
