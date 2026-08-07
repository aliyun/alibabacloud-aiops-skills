# Live-Debug Module

> Global conventions (credentials, Observability / User-Agent, output format, error codes, command prefix) - see [../SKILL.md](../SKILL.md).
> RAM permissions - see the `references/ram-policies.md` section listed in [../SKILL.md](../SKILL.md#credentials).
> Run `aliyun cms2 apm service-task --help` for full flag lists and examples.

## Scope

Construct and manage Live-Debug ServiceTask APIs for JVM and Python runtime diagnostics. Supports create/list/get/delete tasks, SLS result queries, Java commands (OGNL, decompile, thread, memory, search, inspect) and probes (LOG/SNAPSHOT); Python probes only (LOG/SNAPSHOT/METRIC/SPAN/SPAN_TAG). Use when the user mentions live-debug, wants to disable/clear probes, build serviceTask calls, inspect a running JVM, or add dynamic logging/snapshots/metrics/spans.

---

# Live-Debug

Manage live-debug tasks on target instances via scripts (create / list / get / delete) and query the execution results.

Two task categories are supported:
- **Command (active probing)**: one-shot execution, results reported asynchronously. **Java/JVM only; not supported for Python.**
- **Probe (code enhancement)**: continuously effective bytecode instrumentation that captures and reports data when triggered. Java supports `LOG`/`SNAPSHOT`; Python supports `LOG`/`SNAPSHOT`/`METRIC`/`SPAN`/`SPAN_TAG`.

> **Important: taskConfig uses a flat JSON structure.** Pass a single command/probe object directly; do **not** wrap it in a `commands` or `probes` array.
>
> **To disable a probe, use DeleteServiceTask.** Do not create a new task with `enabled:false` - that does not affect probes that have already been dispatched.

## Prerequisite Parameters

Confirm the following parameters before making a call:

| Parameter | Description | Example |
|------|------|------|
| workspace | ARMS workspace ID | `agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9` |
| serviceId | Application / service ID | `ggxw4lnjuz@f2fd3a6265a254a052afb` |
| targetIp | Target instance IP (optional; defaults to `*`, matching all instances) | `10.0.0.1` |
| regionId | Onboarding region | `cn-hangzhou` |
| SLS project | SLS project used for result queries | `proj-xtrace-xxxxxxxxxxxxxxxxxxxxxx-cn-hangzhou` |

**Acquisition order:**

1. **Read the `.arms-info` file in the project root first.** It stores parameters in `key=value` format, for example:
   ```
   workspace=agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9
   serviceId=ggxw4lnjuz@f2fd3a6265a254a052afb
   regionId=cn-hangzhou
   targetIp=10.0.0.1
   slsProject=proj-xtrace-xxxxxxxxxxxxxxxxxxxxxx-cn-hangzhou
   ```
2. If `.arms-info` does not exist or is missing some parameters, ask the user for the missing values. If the workspace is unknown, run `aliyun cms2 workspace list` and pick an existing workspace that matches the naming the user requires (e.g. `agentloop-{32 hex chars}`); never invent a workspace ID. If `targetIp` is missing, use the default `*`.

Defaults can be overridden via environment variables:
- `LIVE_DEBUG_REGION_ID` - onboarding region (from `regionId` in `.arms-info`). Used as the CMS CLI `--region` argument **and** passed to `aliyun sls --region` on SLS queries. When unset: CMS infers it from the workspace suffix, SLS infers it from the project-name suffix (e.g. `...-cn-hangzhou`).
- `LIVE_DEBUG_CMS_ENDPOINT` - CMS API endpoint (optional; passed as the CMS CLI `--endpoint`, overriding the region-derived result).
- `LIVE_DEBUG_CMS2` - how the CMS CLI is invoked (default `aliyun cms2`, i.e. the aliyuncms2 plugin of the Alibaba Cloud CLI; for local debugging it can be set to `aliyuncms2` or an absolute binary path).
- `LIVE_DEBUG_SLS_PROJECT` - SLS project.
- `LIVE_DEBUG_SLS_LOGSTORE` - SLS logstore (default `logstore-apm-logs`).
- `LIVE_DEBUG_SESSION_ID` - the session-id for the current workflow (32 lowercase hexadecimal characters; generation rules in [../SKILL.md](../SKILL.md#session-id-rule)). When set, the scripts automatically append `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-livedebug/{session-id}"` to all `aliyun cms2` / `aliyun sls` calls.
- `LIVE_DEBUG_USER_AGENT` - a full user-agent string override (takes precedence over `LIVE_DEBUG_SESSION_ID`).

> **Agent must-do:** after reading `.arms-info`, export `LIVE_DEBUG_REGION_ID=<regionId>` (and `LIVE_DEBUG_SLS_PROJECT=<slsProject>`) before calling any script. **Do not rely** on the local `aliyun configure` default region - it may point to a different region and cause SLS to return `ProjectNotExist`. Per this skill's Observability rules, also export `LIVE_DEBUG_SESSION_ID=<session-id>` so the CLI calls the scripts emit carry a unified User-Agent.

## Workflow

Maps to the OpenAPI `ServiceTaskController` (CMS `2024-03-30`):

| Operation | API | CLI command | Script |
|------|-----|---------|------|
| Create | `POST /serviceTask/{workspace}/{serviceId}/task` | `aliyun cms2 apm service-task create` | `send_command.sh` |
| List | `GET /serviceTask/{workspace}/{serviceId}/tasks` | `aliyun cms2 apm service-task list` | `list_tasks.sh` |
| Get one | `GET /serviceTask/{workspace}/{serviceId}/task/{taskId}` | `aliyun cms2 apm service-task get` | `get_task.sh` |
| Delete | `DELETE /serviceTask/{workspace}/{serviceId}/task/{taskId}` | `aliyun cms2 apm service-task delete` | `delete_task.sh` |
| Bulk-delete probes | list + delete combination | - | `delete_all_probes.sh` |
| Query results | SLS query | `aliyun sls get-logs-v2` | `query_task.sh` |

All scripts call CMS through the CMS CLI (`aliyun cms2`, i.e. aliyuncms2) `apm service-task` commands, reusing the Alibaba Cloud CLI credential system. CLI output is uniformly wrapped as `{"success":true,"data":{...}}`, and the scripts always use `-o json`.

### 1. Create a task (CreateServiceTask)

```bash
scripts/live-debug/send_command.sh \
  <workspace> <serviceId> [targetIp] <taskType> '<taskConfigJson>'
```

Pass `taskConfigJson` as the raw JSON object; the CLI serializes it into the `taskConfig` string field automatically - no manual escaping needed. `targetIp` can be omitted, in which case `*` is used to match all instances. **Do not pass a taskId**; after a successful create, read the task ID from `data.taskId` in the output:

```json
{"success": true, "data": {"requestId": "xxx", "taskId": "yyy"}}
```

HTTP body form after CLI assembly (for reference only - in the HTTP body `taskConfig` is an **escaped JSON string**; when passing to the script or CLI `--task-config`, always pass the unescaped object JSON):

```json
{
  "type": "live_debug_log_probe",
  "ip": "*",
  "taskConfig": "{\"probeType\":\"LOG\",\"language\":\"python\",\"target\":{\"typeName\":\"app.service.order\",\"methodName\":\"OrderService.create_order\",\"location\":\"exit\",\"instanceIds\":[\"*\"]},\"action\":{\"type\":\"LOG\",\"template\":\"id={order_id}\"},\"ttl\":\"30m\",\"captureCount\":100}"
}
```

Equivalent direct CLI call:

```bash
aliyun cms2 apm service-task create \
  --workspace <workspace> --service-id <serviceId> \
  --type <taskType> --ip '<targetIp>' \
  --task-config '<taskConfigJson>' \
  --region <regionId> -o json
```

### 2. List tasks (ListServiceTask)

```bash
scripts/live-debug/list_tasks.sh \
  <workspace> <serviceId> <taskType> [maxResults]
```

- `taskType` is **required and exact-matched** (e.g. `live_debug_log_probe`). The server filters by type, so a single call returns only tasks of that type.
- `maxResults` is optional, default `100` (API cap is 100).
- Response field: `data.serviceTasks[]`, each item containing `taskId` / `type` / `serviceId` / `ip` / `createTime` / `updateTime` / `taskConfig`.

To see all probes under a service, list once per probe type, or use `delete_all_probes.sh --dry-run`.

Equivalent direct CLI call:

```bash
aliyun cms2 apm service-task list \
  --workspace <workspace> --service-id <serviceId> \
  --type <taskType> --max-results 100 \
  --region <regionId> -o json
```

### 3. Get a single task (GetServiceTask)

```bash
scripts/live-debug/get_task.sh \
  <workspace> <serviceId> <taskId> <taskType>
```

- The `type` query parameter is required and must match the task's actual type.
- Response: a `data.serviceTask` object (same fields as a list item).

Equivalent direct CLI call:

```bash
aliyun cms2 apm service-task get \
  --workspace <workspace> --service-id <serviceId> \
  --task-id <taskId> --type <taskType> \
  --region <regionId> -o json
```

### 4. Delete a task (DeleteServiceTask) - disable/uninstall a probe

```bash
scripts/live-debug/delete_task.sh \
  <workspace> <serviceId> <taskId> <taskType>
```

Deleting removes the task on the server and triggers `syncToConfigServer`, so the corresponding probe on the Agent side stops working. This is the **correct way to stop a dispatched probe**.

Equivalent direct CLI call:

```bash
aliyun cms2 apm service-task delete \
  --workspace <workspace> --service-id <serviceId> \
  --task-id <taskId> --type <taskType> \
  --region <regionId> -o json
```

Bulk-clear all probes under a service:

```bash
# Preview only
scripts/live-debug/delete_all_probes.sh \
  <workspace> <serviceId> --dry-run

# Actually delete
scripts/live-debug/delete_all_probes.sh \
  <workspace> <serviceId>
```

Covers: `live_debug_log_probe` / `live_debug_snapshot_probe` / `live_debug_metric_probe` / `live_debug_span_probe` / `live_debug_span_tag_probe`.

### 5. Query capture results (SLS)

Query task status and capture results via SLS logs. `query_task.sh` **always** passes `--region` to `aliyun sls` (from `LIVE_DEBUG_REGION_ID`, or the project-name suffix); it never uses the CLI default region:

```bash
# Recommended: explicitly pass regionId / slsProject from .arms-info
LIVE_DEBUG_REGION_ID=cn-hangzhou \
LIVE_DEBUG_SLS_PROJECT=proj-xtrace-xxxxxxxxxxxxxxxxxxxxxx-cn-hangzhou \
  scripts/live-debug/query_task.sh \
  <taskId> [project] [logstore] [minutes]
```

- `taskId` - the taskId returned at create time (required).
- `project` - SLS project (optional; defaults to the `LIVE_DEBUG_SLS_PROJECT` environment variable).
- `logstore` - SLS logstore (optional; default `logstore-apm-logs`).
- `minutes` - how many minutes to look back (optional; default 5).
- **region** - determined by `LIVE_DEBUG_REGION_ID` (`regionId` from `.arms-info`); when unset, inferred from the project suffix. SLS projects are region-isolated, so a wrong region returns `ProjectNotExist`.

The script looks back N minutes from now as the query range and outputs two sections:
- **Task Status** - probe/command installation status and funnel metrics (`livedebug.report_type = 'status'`).
- **Capture Results** - the data actually captured (`livedebug.report_type != 'status'`).

**taskType format:**
- Command types: `live_debug_` + the lowercase command type, e.g. `live_debug_get_memory_info` (Java only).
- Probe types: `live_debug_log_probe`, `live_debug_snapshot_probe`; Python also supports `live_debug_metric_probe`, `live_debug_span_probe`, `live_debug_span_tag_probe`.

**Full taskType enums (taskType / List-Get-Delete `type`):**

| taskType | Kind | Language |
|----------|------|----------|
| `live_debug_log_probe` | Probe LOG | Java / Python |
| `live_debug_snapshot_probe` | Probe SNAPSHOT | Java / Python |
| `live_debug_metric_probe` | Probe METRIC | **Python** |
| `live_debug_span_probe` | Probe SPAN | **Python** |
| `live_debug_span_tag_probe` | Probe SPAN_TAG | **Python** |
| `live_debug_evaluate_expression` | Command EVALUATE_EXPRESSION | Java |
| `live_debug_decompile` | Command DECOMPILE | Java |
| `live_debug_get_memory_info` | Command GET_MEMORY_INFO | Java |
| `live_debug_get_thread_info` | Command GET_THREAD_INFO | Java |
| `live_debug_inspect_object` | Command INSPECT_OBJECT | Java |
| `live_debug_search_type` | Command SEARCH_TYPE | Java |
| `live_debug_search_method` | Command SEARCH_METHOD | Java |
| `live_debug_get_runtime_info` | Command GET_RUNTIME_INFO | Java |

---

## I. Probe types (code enhancement)

A Probe is a continuously effective bytecode-instrumentation task that fires automatically when the target method is invoked. taskConfig uses a flat structure: pass a single probe object directly.

### Common Probe structure

```json
{
  "probeType": "LOG|SNAPSHOT|METRIC|SPAN|SPAN_TAG",
  "language": "java|python",
  "target": { ... },
  "action": { ... },
  "trigger": { ... },
  "rateLimit": { ... },
  "ttl": "1h",
  "captureCount": 100,
  "enabled": true
}
```

### target - locate the target method

| Field | Type | Required | Description |
|------|------|------|------|
| typeName | string | Yes | Fully-qualified class name (e.g. `com.example.UserService`) |
| methodName | string | Yes | Method name |
| sourceFile | string | No | Source file name (recommended) |
| location | string | No | Hook point: `enter`/`exit`/`exception`/`line:N` (default `exit`) |
| overloadSignature | string | No | JVM method descriptor, to distinguish overloads |
| instanceIds | string[] | Strongly recommended | List of instance IDs to apply to; `["*"]` means all |
| instanceIps | string[] | No | List of IPs to apply to (AND-combined with instanceIds) |

**Python target differences:**
- `typeName` is the module name (`sys.modules` key), e.g. `app.service.order`. Note: if the module to enhance is the main module (e.g. the file contains a `__main__` entry), its module name should be `__main__`.
- `methodName` is the function's `__qualname__`; for a method write `OrderService.create_order`, for a plain function just write the function name.
- A line-level probe can rely on only `sourceFile` + `location:"line:N"`; `sourceFile` may be a relative path or the `__file__` suffix of the actually-loaded module.
- `location` supports `enter`/`exit`/`exception`/`line:N`; `SPAN` supports function-level only and cannot be used at line level.
- When `instanceIds`/`instanceIps` are empty, a Python probe will not take effect; use `["*"]` for full rollout.

### trigger - trigger condition (optional)

| Field | Type | Default | Description |
|------|------|------|------|
| condition | string | - | Condition expression; captures only when true (Java e.g. `args[0].totalAmount > 10000`; Python e.g. `amount > 10000`) |
| callerPattern | string | - | Caller class-name filter |

**Python expression syntax:**
- Template interpolation uses `{expression}`, not Java's `${expression}`; the expression is a restricted Python `eval`.
- Directly use parameter names, local variable names, and module global variables in the current frame, e.g. `{order_id}`, `{amount * count}`, `{self.user_id}`.
- At `exit`/`exception`, `{@return}`, `{@duration}` (milliseconds), and `{@exception}` are additionally available; the implementation normalizes `@return` into an executable variable.
- Do not use Java-style expressions in Python probes, such as OGNL, `@Class@method()`, `args[0]`, `returnValue`, `durationMs`.
- Available built-in functions: `len/str/int/float/bool/repr/type/abs/min/max/sum/sorted/list/dict/tuple/set/isinstance/hasattr/getattr/enumerate/zip/range/round`.
- A function-level `trigger.condition` is evaluated at the corresponding hook point; if the condition references `@return` or `@exception`, only place it on an `exit`/`exception` probe.

### rateLimit - rate control (optional)

| Field | Type | Default | Description |
|------|------|------|------|
| maxExecutionsPerSecond | int | 100 | Token-bucket maximum executions per second |
| samplingProbability | double | 1.0 | Random pass-through probability (0-1) |
| executionTimeoutMs | int | 100 | Per-capture timeout (ms) |

Python additionally has per-type default rate limits: `LOG`/`METRIC`/`SPAN`/`SPAN_TAG` about 5000/s, `SNAPSHOT` about 1/s; line-level probes also have a global ~100/s guard.

### Lifecycle

Specify at least one of `ttl` and `captureCount`; whichever condition is met first terminates the task. `ttl` supports `ms/s/m/h/d` units (e.g. `"1h"`, `"30m"`).

---

### Java LOG_PROBE - dynamic logging

**taskType:** `live_debug_log_probe`

Emits dynamic logs when the target method executes, by evaluating expressions spliced into a template. Does not serialize the object graph.

**action fields:**

| Field | Type | Required | Description |
|------|------|------|------|
| type | string | Yes | Fixed `"LOG"` |
| template | string | Yes | Java log template, `${expression}` syntax |
| templateSegments | array | Yes | Server-preparsed segment array |

Each templateSegments item has a `type` (`TEXT` or `EXPRESSION`) and a `value`. The Agent iterates the segments: TEXT is appended verbatim, EXPRESSION is evaluated then appended.

#### Example 1: log method arguments and duration

```json
{"probeType":"LOG","language":"java","target":{"typeName":"com.example.service.UserServiceImpl","methodName":"findById","location":"exit","instanceIds":["*"]},"action":{"type":"LOG","template":"userId=${args[0]} cost=${durationMs}ms","templateSegments":[{"type":"TEXT","value":"userId="},{"type":"EXPRESSION","value":"args[0]"},{"type":"TEXT","value":" cost="},{"type":"EXPRESSION","value":"durationMs"},{"type":"TEXT","value":"ms"}]},"ttl":"1h","captureCount":100}
```

#### Example 2: log with a condition filter

```json
{"probeType":"LOG","language":"java","target":{"typeName":"com.example.service.OrderService","methodName":"createOrder","location":"exit","instanceIds":["*"]},"trigger":{"condition":"args[0].totalAmount > 10000"},"action":{"type":"LOG","template":"Large order: amount=${args[0].totalAmount} user=${args[0].userId}","templateSegments":[{"type":"TEXT","value":"Large order: amount="},{"type":"EXPRESSION","value":"args[0].totalAmount"},{"type":"TEXT","value":" user="},{"type":"EXPRESSION","value":"args[0].userId"}]},"ttl":"30m"}
```

#### Example 3: method-entry log

```json
{"probeType":"LOG","language":"java","target":{"typeName":"com.example.controller.ApiController","methodName":"handleRequest","location":"enter","instanceIds":["*"]},"action":{"type":"LOG","template":"Request received: ${args[0].getRequestURI()}","templateSegments":[{"type":"TEXT","value":"Request received: "},{"type":"EXPRESSION","value":"args[0].getRequestURI()"}]},"rateLimit":{"maxExecutionsPerSecond":10},"ttl":"1h"}
```

#### Example 4: exception-path log

```json
{"probeType":"LOG","language":"java","target":{"typeName":"com.example.service.PaymentService","methodName":"processPayment","location":"exception","instanceIds":["*"]},"action":{"type":"LOG","template":"Payment failed: ${exception.message} orderId=${args[0].orderId}","templateSegments":[{"type":"TEXT","value":"Payment failed: "},{"type":"EXPRESSION","value":"exception.message"},{"type":"TEXT","value":" orderId="},{"type":"EXPRESSION","value":"args[0].orderId"}]},"ttl":"2h"}
```

---

### Java SNAPSHOT_PROBE - method snapshot

**taskType:** `live_debug_snapshot_probe`

Captures a method snapshot (arguments, return value, this object, exception, call stack, etc.) when the target method executes, serializing the object graph before reporting.

**action fields:**

| Field | Type | Required | Description |
|------|------|------|------|
| type | string | Yes | Fixed `"SNAPSHOT"` |
| capture | string[] | Yes | Array of capture-dimension enums |
| captureExpressions | string[] | No | List of extra expressions to evaluate |
| captureConfig | object | No | Object-graph serialization budget config |

**capture enum values:**

| Value | Description |
|----|------|
| ARGS | Serialize method arguments |
| RETURN | Serialize the return value |
| THIS | Serialize the current instance |
| EXCEPTION | Record an exception summary |
| LOCALS | Capture local variables (requires debug info) |
| STACK | Capture the call stack |
| EXECUTION_DETAIL | Aggregate sub-calls within the method body |

**captureConfig options:**

| Field | Default | Description |
|------|--------|------|
| maxDepth | 3 | Max object-serialization depth |
| maxCollectionSize | 100 | Max elements per collection/array |
| maxStringLength | 1024 | Max string length |
| maxFieldCount | 50 | Max fields per object |
| maxTotalSizeBytes | 65536 | Max bytes per snapshot |
| stackTraceDepth | 50 | Max call-stack depth |
| redactedFieldPatterns | `[".*password.*",".*token.*",".*secret.*"]` | Redaction field regexes |

#### Example 1: capture method arguments and return value

```json
{"probeType":"SNAPSHOT","language":"java","target":{"typeName":"com.example.service.UserServiceImpl","methodName":"findById","location":"exit","instanceIds":["*"]},"action":{"type":"SNAPSHOT","capture":["ARGS","RETURN","STACK"]},"ttl":"1h","captureCount":50}
```

#### Example 2: full snapshot (including this)

```json
{"probeType":"SNAPSHOT","language":"java","target":{"typeName":"com.example.service.OrderService","methodName":"createOrder","location":"exit","instanceIds":["*"]},"action":{"type":"SNAPSHOT","capture":["ARGS","RETURN","THIS","EXCEPTION","STACK"],"captureConfig":{"maxDepth":5,"maxCollectionSize":50,"maxStringLength":2048}},"ttl":"30m","captureCount":20}
```

#### Example 3: condition filter with extra expressions

```json
{"probeType":"SNAPSHOT","language":"java","target":{"typeName":"com.example.service.PaymentService","methodName":"processPayment","location":"exit","instanceIds":["*"]},"trigger":{"condition":"returnValue != null && returnValue.status == 'FAILED'"},"action":{"type":"SNAPSHOT","capture":["ARGS","RETURN","EXCEPTION","STACK"],"captureExpressions":["args[0].orderId","args[0].amount","returnValue.errorCode"]},"ttl":"2h","captureCount":100}
```

#### Example 4: line-level probe

```json
{"probeType":"SNAPSHOT","language":"java","target":{"typeName":"com.example.service.UserServiceImpl","methodName":"findById","sourceFile":"UserServiceImpl.java","location":"line:42","instanceIds":["*"]},"action":{"type":"SNAPSHOT","capture":["ARGS","LOCALS","STACK"]},"ttl":"1h","captureCount":10}
```

#### Example 5: rate-limiting under high QPS

```json
{"probeType":"SNAPSHOT","language":"java","target":{"typeName":"com.example.gateway.RouteHandler","methodName":"handle","location":"exit","instanceIds":["*"]},"action":{"type":"SNAPSHOT","capture":["ARGS","RETURN"]},"rateLimit":{"samplingProbability":0.01,"maxExecutionsPerSecond":10},"ttl":"1h"}
```

---

## II. Python Probe types (code enhancement)

Python live-debug supports Probes only, not Commands (active probing). When creating a task via `send_command.sh`, still pass a flat single-probe taskConfig - no top-level `probes` array, and do not pass a `taskId` manually; the `{ "probes": [...] }` structure is only used by the underlying ConfigServer / local `DynamicInstrumentation.apply_config()`.

Python `ttl` supports `30s`/`5m`/`2h`/`1d` or a plain number of seconds; do not use the `ms` unit. Default rate limits: `LOG`/`METRIC`/`SPAN`/`SPAN_TAG` are 5000/s, `SNAPSHOT` is 1/s, and line-level probes additionally have a global 100/s guard.

### Python LOG_PROBE

**taskType:** `live_debug_log_probe`

The template uses `{expr}`; expressions directly reference Python parameter/local-variable names.

> **Python LOG only renders the template message** - it does not capture the object graph or the call stack, and ignores the `capture` dimensions (aligned with Java's `emitLog`). To capture arguments/return value/stack/custom expressions, use `SNAPSHOT`.

```json
{"probeType":"LOG","language":"python","target":{"typeName":"app.service.order","methodName":"OrderService.create_order","location":"exit","instanceIds":["*"]},"action":{"type":"LOG","template":"create_order id={order_id} amount={amount} ret={@return} cost={@duration}ms"},"ttl":"30m","captureCount":100}
```

Line-level log:

```json
{"probeType":"LOG","language":"python","target":{"sourceFile":"app/service/order.py","location":"line:42","instanceIds":["*"]},"trigger":{"condition":"amount >= 1000"},"action":{"type":"LOG","template":"big order id={order_id} amount={amount}"},"ttl":"30m"}
```

### Python SNAPSHOT_PROBE

**taskType:** `live_debug_snapshot_probe`

The `capture` enum matches Java: `ARGS`/`RETURN`/`THIS`/`EXCEPTION`/`LOCALS`/`STACK`/`EXECUTION_DETAIL`. The default object-graph budget matches Java: `maxDepth=3`, `maxCollectionSize=100`, `maxStringLength=1024`, `maxFieldCount=50`, `maxTotalSizeBytes=65536`, `stackTraceDepth=50`.

> **`capture` must explicitly list the dimensions to capture** (aligned with Java): omitting it or passing `[]` means no object graph is captured - only the listed dimensions are captured. `STACK` is opt-in and is only captured when explicitly included - the call stack is no longer captured automatically by default.

**action fields:**

| Field | Type | Required | Description |
|------|------|------|------|
| type | string | Yes | Fixed `"SNAPSHOT"` |
| capture | string[] | Yes | Array of capture-dimension enums (see table above) |
| captureExpressions | string[] | No | List of extra Python expressions; each is evaluated and serialized before reporting |
| captureConfig | object | No | Object-graph serialization budget config |

The `captureExpressions` syntax matches `trigger.condition` / the LOG template (restricted Python `eval`, directly referencing parameter names/local variables/global variables; `@return`/`@duration`/`@exception` available at `exit`/`exception`). Each expression is evaluated independently and its result is written to `context.evaluatedExpressions` in the capture result, each item being `{name, type, value, notCapturedReason}`; on evaluation failure `value=null` and `notCapturedReason` records the reason, without affecting other dimensions. `captureExpressions` and `capture` are independent - expressions are still evaluated and reported even when `capture:[]`.

```json
{"probeType":"SNAPSHOT","language":"python","target":{"typeName":"app.service.order","methodName":"OrderService.create_order","location":"exit","instanceIds":["*"]},"action":{"type":"SNAPSHOT","capture":["ARGS","LOCALS","RETURN","STACK"],"captureConfig":{"maxDepth":3,"maxCollectionSize":100,"maxStringLength":1024}},"ttl":"30m","captureCount":20}
```

With custom expressions (report only the fields of interest, combined with a condition filter):

```json
{"probeType":"SNAPSHOT","language":"python","target":{"typeName":"app.service.order","methodName":"OrderService.create_order","location":"exit","instanceIds":["*"]},"trigger":{"condition":"@return is None or amount > 10000"},"action":{"type":"SNAPSHOT","capture":["ARGS"],"captureExpressions":["order_id","amount * count","self.user_id","@return"]},"ttl":"30m","captureCount":50}
```

### Python METRIC_PROBE

**taskType:** `live_debug_metric_probe`

Both `valueExpression` and the values of `tags` are Python expressions. `metricType` supports `COUNTER`/`GAUGE`/`HISTOGRAM`/`SUMMARY`.

```json
{"probeType":"METRIC","language":"python","target":{"typeName":"app.service.order","methodName":"OrderService.create_order","location":"exit","instanceIds":["*"]},"action":{"type":"METRIC","metricName":"livedebug.order.amount","metricType":"HISTOGRAM","valueExpression":"amount","tags":{"is_vip":"str(user_id == 'vip')"}},"ttl":"1h"}
```

### Python SPAN_PROBE

**taskType:** `live_debug_span_probe`

Function-level probes only; creates a new OTel Span for the duration of the target function's execution, marking it ERROR and recording an exception event on failure.

```json
{"probeType":"SPAN","language":"python","target":{"typeName":"app.service.order","methodName":"OrderService.create_order","location":"enter","instanceIds":["*"]},"action":{"type":"SPAN","spanName":"dyn.create_order","spanTags":{"order.id":"str(order_id)","order.amount":"str(amount)"}},"ttl":"1h"}
```

### Python SPAN_TAG_PROBE

**taskType:** `live_debug_span_tag_probe`

Appends attributes to the currently active Span; if no Span is being recorded, it neither errors nor creates a new Span. Note that `tags` is an array, each item being `{key,value}`.

```json
{"probeType":"SPAN_TAG","language":"python","target":{"typeName":"app.service.order","methodName":"OrderService.create_order","location":"exit","instanceIds":["*"]},"action":{"type":"SPAN_TAG","tags":[{"key":"order.id","value":"str(order_id)"},{"key":"order.result","value":"str(@return)"}]},"ttl":"1h"}
```

---

## III. Command types (active probing)

A Command is a one-shot, asynchronously-executed operation that is destroyed once complete. taskConfig uses a flat structure: pass a single command object directly.

> **Note:** the top level of a Command's taskConfig must include the `"instanceIds":["*"]` field, otherwise the API returns an `instanceIds is required` error.
> **Python does not support Commands.** If the target language is Python, you can only build the Probe tasks from the previous section - do not generate active-probing requests such as `EVALUATE_EXPRESSION`, `SEARCH_TYPE`, `DECOMPILE`, `GET_THREAD_INFO`.

### EVALUATE_EXPRESSION

OGNL expression evaluation. Automatically infers the ClassLoader from `@ClassName@` references.

**taskType:** `live_debug_evaluate_expression`

| Parameter | Type | Required | Default | Description |
|------|------|------|------|------|
| expression | string | Yes | - | OGNL expression |
| classLoaderHash | string | No | - | ClassLoader hashCode (hex) |
| classLoaderClass | string | No | - | ClassLoader class name |
| expand | int | No | 1 | Object expansion depth |

```json
{"commandType":"EVALUATE_EXPRESSION","language":"java","params":{"expression":"@java.lang.System@getProperty(\"java.home\")"},"instanceIds":["*"]}
```

```json
{"commandType":"EVALUATE_EXPRESSION","language":"java","params":{"expression":"@com.example.AppConfig@INSTANCE.getUrl()","expand":2},"instanceIds":["*"]}
```

---

### DECOMPILE

Decompile an already-loaded class to view the runtime source code.

**taskType:** `live_debug_decompile`

| Parameter | Type | Required | Default | Description |
|------|------|------|------|------|
| className | string | Yes | - | Fully-qualified class name |
| methodName | string | No | - | Decompile only this method |
| classLoaderHash | string | No | - | ClassLoader hashCode |
| classLoaderClass | string | No | - | ClassLoader class name |
| regex | boolean | No | false | Regex matching |
| lineNumber | boolean | No | true | Line-number annotations |
| sourceOnly | boolean | No | false | Source only |

```json
{"commandType":"DECOMPILE","language":"java","params":{"className":"com.example.service.UserServiceImpl"},"instanceIds":["*"]}
```

```json
{"commandType":"DECOMPILE","language":"java","params":{"className":"com.example.service.UserServiceImpl","methodName":"findById"},"instanceIds":["*"]}
```

---

### GET_MEMORY_INFO

JVM memory information (heap / non-heap / buffer pools).

**taskType:** `live_debug_get_memory_info`

No parameters.

```json
{"commandType":"GET_MEMORY_INFO","language":"java","params":{},"instanceIds":["*"]}
```

---

### GET_THREAD_INFO

Thread diagnostics, 4 modes. Priority: threadId > topN > blocking > all.

**taskType:** `live_debug_get_thread_info`

| Parameter | Type | Required | Default | Description |
|------|------|------|------|------|
| threadId | long | No | - | Single-thread detail |
| topN | int | No | - | Top N by CPU (-1 = all, sorted by CPU) |
| blocking | boolean | No | false | Deadlock/blocking detection |
| sampleInterval | int | No | 200 | CPU sampling interval (ms) |
| state | string | No | - | Filter by state |
| lockedMonitors | boolean | No | false | Locked-monitor info |
| lockedSynchronizers | boolean | No | false | Synchronizer info |

```json
{"commandType":"GET_THREAD_INFO","language":"java","params":{},"instanceIds":["*"]}
```

```json
{"commandType":"GET_THREAD_INFO","language":"java","params":{"topN":5,"sampleInterval":500},"instanceIds":["*"]}
```

```json
{"commandType":"GET_THREAD_INFO","language":"java","params":{"threadId":51,"lockedMonitors":true,"lockedSynchronizers":true},"instanceIds":["*"]}
```

```json
{"commandType":"GET_THREAD_INFO","language":"java","params":{"blocking":true},"instanceIds":["*"]}
```

```json
{"commandType":"GET_THREAD_INFO","language":"java","params":{"state":"BLOCKED"},"instanceIds":["*"]}
```

---

### INSPECT_OBJECT

Inspect runtime object instances. By default fetches Beans from the Spring container; JVMTI heap scanning is optional.

**taskType:** `live_debug_inspect_object`

| Parameter | Type | Required | Default | Description |
|------|------|------|------|------|
| className | string | Yes | - | Fully-qualified target class name |
| expression | string | No | - | OGNL expression (reference the instance array via `instances`) |
| classLoaderHash | string | No | - | ClassLoader hashCode |
| classLoaderClass | string | No | - | ClassLoader class name |
| expand | int | No | 1 | Expansion depth |
| limit | int | No | 10 | Max instances (-1 = unlimited) |
| useVmTool | boolean | No | false | Use the JVMTI native library |

```json
{"commandType":"INSPECT_OBJECT","language":"java","params":{"className":"com.example.service.UserServiceImpl","expand":2},"instanceIds":["*"]}
```

```json
{"commandType":"INSPECT_OBJECT","language":"java","params":{"className":"com.example.service.UserServiceImpl","expression":"instances[0].getUserCount()"},"instanceIds":["*"]}
```

```json
{"commandType":"INSPECT_OBJECT","language":"java","params":{"className":"com.zaxxer.hikari.HikariDataSource","expression":"instances[0].getHikariPoolMXBean()","expand":3},"instanceIds":["*"]}
```

```json
{"commandType":"INSPECT_OBJECT","language":"java","params":{"className":"com.example.cache.LocalCache","useVmTool":true,"limit":5},"instanceIds":["*"]}
```

---

### SEARCH_TYPE

Search already-loaded classes.

**taskType:** `live_debug_search_type`

| Parameter | Type | Required | Default | Description |
|------|------|------|------|------|
| classPattern | string | Yes | - | Class-name pattern (`*` wildcard) |
| regex | boolean | No | false | Regex matching |
| detail | boolean | No | false | Class detail |
| field | boolean | No | false | Field info (requires detail=true) |
| classLoaderHash | string | No | - | ClassLoader hashCode |
| classLoaderClass | string | No | - | ClassLoader class name |
| limit | int | No | 100 | Max classes in detail mode |

```json
{"commandType":"SEARCH_TYPE","language":"java","params":{"classPattern":"*UserService*"},"instanceIds":["*"]}
```

```json
{"commandType":"SEARCH_TYPE","language":"java","params":{"classPattern":"com.example.service.UserServiceImpl","detail":true,"field":true},"instanceIds":["*"]}
```

---

### SEARCH_METHOD

Search a class's methods.

**taskType:** `live_debug_search_method`

| Parameter | Type | Required | Default | Description |
|------|------|------|------|------|
| classPattern | string | Yes | - | Class-name pattern |
| methodPattern | string | No | - | Method-name pattern |
| regex | boolean | No | false | Regex matching |
| detail | boolean | No | false | Method detail |
| classLoaderHash | string | No | - | ClassLoader hashCode |
| classLoaderClass | string | No | - | ClassLoader class name |
| limit | int | No | 100 | Max matching classes |

```json
{"commandType":"SEARCH_METHOD","language":"java","params":{"classPattern":"com.example.service.UserServiceImpl"},"instanceIds":["*"]}
```

```json
{"commandType":"SEARCH_METHOD","language":"java","params":{"classPattern":"com.example.service.UserServiceImpl","methodPattern":"find*","detail":true},"instanceIds":["*"]}
```

---

### GET_RUNTIME_INFO

JVM runtime information, 9 sections.

**taskType:** `live_debug_get_runtime_info`

| Parameter | Type | Required | Default | Description |
|------|------|------|------|------|
| sections | string[] | No | all | List of sections to return |

Allowed values: `RUNTIME` / `CLASS_LOADING` / `COMPILATION` / `GARBAGE_COLLECTORS` / `MEMORY_MANAGERS` / `MEMORY` / `OPERATING_SYSTEM` / `THREAD` / `FILE_DESCRIPTOR`

```json
{"commandType":"GET_RUNTIME_INFO","language":"java","params":{},"instanceIds":["*"]}
```

```json
{"commandType":"GET_RUNTIME_INFO","language":"java","params":{"sections":["GARBAGE_COLLECTORS","MEMORY"]},"instanceIds":["*"]}
```

---

## instanceIds placement

| Task category | `instanceIds` location | Example |
|----------|-------------------|------|
| Probe | **`target.instanceIds`** | `"target":{"instanceIds":["*"], ...}` |
| Command | **taskConfig top level** | `"instanceIds":["*"]` (sibling of `commandType`) |

Misplacing it causes the probe to have no effect, or the Command to fail creation with `instanceIds is required`.

## Diagnostic scenario quick reference

| Scenario | Category | taskType | Key config |
|------|------|----------|----------|
| Java method-argument log | Probe | log_probe | template contains `${args[0]}` |
| Python method-argument log | Probe | log_probe | template contains `{paramName}` |
| Method snapshot capture | Probe | snapshot_probe | capture: ARGS+RETURN+STACK |
| Auto-capture on exception | Probe | snapshot_probe | location=exception |
| Line-level variable observation | Probe | snapshot_probe | location=line:N, capture: LOCALS |
| Python dynamic metric | Probe | metric_probe | valueExpression + tags |
| Python dynamic Span | Probe | span_probe | function-level target + spanName/spanTags |
| Python Span tagging | Probe | span_tag_probe | tags array |
| Inspect app configuration | Command | inspect_object | className pointing to the config class |
| CPU spike | Command | get_thread_info | topN=10, sampleInterval=1000 |
| Memory leak | Command | get_memory_info | watch the growing region |
| Deadlock detection | Command | get_thread_info | blocking=true |
| Class conflict | Command | search_type | classPattern + detail=true |
| Confirm a method signature | Command | search_method | detail=true |
| Inspect AOP enhancement | Command | decompile | view runtime bytecode |
| Dynamic diagnostics | Command | evaluate_expression | OGNL expression |
| JVM health overview | Command | get_runtime_info | all, or MEMORY+GC+THREAD |
| List dispatched probes | List | list_tasks.sh | exact-list by taskType |
| Disable/uninstall a single probe | Delete | delete_task.sh | needs taskId + taskType |
| Clear all probes on a service | Delete | delete_all_probes.sh | list+delete per probe type |

## Troubleshooting

| Symptom | Likely cause | Recommended action |
|------|----------|----------|
| `instanceIds is required` | Command top level missing `instanceIds` | Add `["*"]` at the taskConfig top level |
| `ProjectNotExist` | SLS region is wrong | Set `LIVE_DEBUG_REGION_ID` to the same region as the project |
| List empty but the task exists | `type` does not match the actual taskType | List by exact type separately |
| Probe still active after creating `enabled:false` | Does not affect dispatched tasks | Use DeleteServiceTask |
| Python probe has no data | `instanceIds` empty, wrong module name, or no traffic | Set `["*"]`; verify `typeName`/`methodName`; send traffic then check Status |
| SPAN creation fails or has no effect | Used `line:N` | Switch to a function-level `enter`/`exit` |
| Python ttl error | Used the `ms` unit | Use `s`/`m`/`h`/`d` or a plain number of seconds |
| Created but never any Capture Results | Not installed, filter too strict, or no traffic | Check Task Status first; verify target; widen the query window and retry |

## End-to-end example (Python LOG)

```bash
# 0. Environment
export LIVE_DEBUG_REGION_ID=cn-hangzhou
export LIVE_DEBUG_SLS_PROJECT=proj-xtrace-xxxxxxxxxxxxxxxxxxxxxx-cn-hangzhou
WORKSPACE=agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9
SERVICE_ID='ggxw4lnjuz@f2fd3a6265a254a052afb'

# 1. Create
RESP=$(scripts/live-debug/send_command.sh \
  "$WORKSPACE" "$SERVICE_ID" "*" \
  live_debug_log_probe \
  '{"probeType":"LOG","language":"python","target":{"typeName":"app.service.order","methodName":"OrderService.create_order","location":"exit","instanceIds":["*"]},"action":{"type":"LOG","template":"id={order_id} ret={@return}"},"ttl":"30m","captureCount":50}')
echo "$RESP"
TASK_ID=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["taskId"])')

# 2. Confirm the task
scripts/live-debug/get_task.sh \
  "$WORKSPACE" "$SERVICE_ID" "$TASK_ID" live_debug_log_probe

# 3. Trigger business traffic, then query results
scripts/live-debug/query_task.sh \
  "$TASK_ID" "$LIVE_DEBUG_SLS_PROJECT" logstore-apm-logs 10

# 4. Clean up
scripts/live-debug/delete_task.sh \
  "$WORKSPACE" "$SERVICE_ID" "$TASK_ID" live_debug_log_probe
```

## General notes

- **Do not pass a taskId** when creating; the CLI outputs `{"success":true,"data":{"requestId":...,"taskId":...}}`, and you use `data.taskId` to query results or delete afterward.
- **To disable a probe you must Delete** (`delete_task.sh` / `delete_all_probes.sh`); creating `enabled:false` has no effect.
- The `type` query parameter of List/Get/Delete is **required** and must match the task's actual `taskType`.
- List filters **exactly by type**; there is no "list all live_debug_* at once" API.
- **taskConfig uses a flat JSON structure**: pass a single command/probe object directly, without wrapping it in a `commands` or `probes` array.
- **Command types are Java-only**, and the taskConfig top level must include `"instanceIds":["*"]`, otherwise the API returns an `instanceIds is required` error.
- For **Probe types**, `instanceIds` goes inside the `target` object.
- `classLoaderHash` takes precedence over `classLoaderClass`; when `classLoaderClass` matches multiple, it returns FAILED plus the list.
- Commands default to a 30000ms timeout, returning `state=TIMEOUT` on timeout.
- Probes control their lifecycle via `ttl` + `captureCount`; you can also actively Delete to disable them immediately.
- Built-in variables available in Java Probe expressions: `args` (argument array), `returnValue` (return value), `exception` (exception object), `durationMs` (method duration), `this` (current instance).
- Python Probe expressions directly use parameter/local-variable names; `@return`, `@duration`, `@exception` are additionally available at `exit`/`exception`.
