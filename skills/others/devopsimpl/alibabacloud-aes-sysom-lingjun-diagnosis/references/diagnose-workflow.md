# Diagnosis Execution Detailed Workflow (lingjun)

This document contains the detailed execution steps for SysOM deep diagnosis on **lingjun nodes** (Steps 4–9), referenced from the Core Workflow in SKILL.md.

All `aliyun` CLI commands that call OpenAPI **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}`, reusing the single session-id generated in Step 0 (see the Observability section in `SKILL.md`). Local/system commands (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`) **MUST NOT** carry `--user-agent`.

---

## Step 4 — Parameter Collection (No Confirmation Round)

Only the following two parameters are blocking. If the user's question does not include them, ask for them — **do NOT guess or use default values**. Once both are known, start the pipeline immediately: **do NOT open a confirmation round** asking the user to approve the parameters, the diagnosis mode, or the workflow.

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `region` | Region of the lingjun node | `cn-hangzhou`, `cn-beijing`, `cn-shanghai` |
| `instance_id` | lingjun node ID | `e01-cn-xxxxx` |

### lingjun Node ID Validation

This skill only diagnoses lingjun nodes. The node ID starts with `e01-` (e.g., `e01-cn-xxxxx`), and the diagnosis channel is always `eflo` (see Step 8).

If the user provides an ECS instance ID (starting with `i-`), inform them that this skill only covers lingjun nodes and ask for the correct lingjun node ID.

### Missing-Parameter Flow

**4a. Check if the user's input already contains region and instance_id**

Extract these two parameters from the user's problem description. Common expressions include:
- "lingjun node e01-cn-xxx in Beijing" (region=cn-beijing, instance_id=e01-cn-xxx)
- "the lingjun machine e01-cn-yyy in Hangzhou is slow" (region=cn-hangzhou, instance_id=e01-cn-yyy)

**4b. If either parameter is missing, ask for it — and only for it**

> 🔍 To run the SysOM deep diagnosis I still need:
>
> - **lingjun Node ID**: Please provide the lingjun node ID (format: `e01-cn-xxxxx`)
> - **Region**: The Alibaba Cloud region where the node is located (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`)

> **⛔ After asking, STOP and wait for the user's reply.** Do NOT proceed to Step 5 in the same turn using a region pulled from the CLI profile default (`aliyun configure list` → `Region` column), from an environment variable, or guessed from the node ID. A wrong region diagnoses the wrong resource; noting "used the default region" afterwards does not fix it. Resume only once the user has supplied the missing value.

**4c. Also extract optional context (never ask about these)**

- `ocd_description`: The problem symptoms described by the user
- **Time range inference** (see below)
- `uid`: If the user mentioned an account ID

**⚠️ CRITICAL: Time Inference and Historical Diagnosis**

When the user's description contains **any temporal reference** — even vague ones — **infer the time range yourself** and run historical diagnosis mode. Do NOT stop to ask for an exact timestamp, and do NOT silently default to real-time diagnosis when the problem clearly occurred in the past. Always state the window you used when reporting the result.

**Time inference examples:**

| User Description | Inferred Action |
|-----------------|----------------|
| "The lingjun node crashed this morning" | Historical diagnosis over this morning's window (e.g. 00:00–now, or a ±1h window around the mentioned hour) |
| "Yesterday afternoon there was high CPU" | Historical diagnosis over yesterday 12:00–18:00 |
| "It went down around 3am" | Convert to Unix timestamps for today's 3am (±30min buffer), historical diagnosis |
| "The lingjun node rebooted unexpectedly last night" | Historical diagnosis over last night's window (e.g. 20:00–06:00) |
| "There's been high load for the past 2 hours" | start_time = now - 2h, historical diagnosis |
| "The lingjun node is slow right now" | No time inference needed, use real-time diagnosis (default) |

**Rules:**
1. If the user mentions a **past event** (crash, reboot, spike that already happened), infer a reasonable window and run historical diagnosis — do not ask first
2. If the user describes an **ongoing issue** ("right now", "currently"), use real-time diagnosis
3. Report the inferred `start_time` / `end_time` together with the result, so the user can ask for a different window afterwards
4. Convert natural language time references to Unix timestamps using the current time as reference

**⚠️ IMPORTANT: `ocd_description` MUST be in English only**

The SysOM API restricts `ocd_description` to only `[a-zA-Z0-9_.~-]` characters. You must translate the user's problem description into short English keywords connected by underscores.

| User Description | ocd_description Value |
|-----------------|----------------------|
| High load / abnormal system load | `high_load` |
| CPU spike / high CPU usage | `high_cpu` |
| Memory leak / out of memory | `memory_leak` |
| High IO latency / slow disk | `io_latency` |
| Network packet loss / network jitter | `network_packet_loss` |
| Crash / kernel panic | `kernel_panic` |
| OOM / process killed | `oom_killed` |
| Overall server health check | `health_check` |

---

## Step 5 — Cloud Assistant Online Check

```bash
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <region> \
  --instance-id <instance_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

> **Note**: This check uses the ECS Cloud Assistant API — pass the **lingjun node ID** (`e01-cn-xxxxx`) as `--instance-id`.

Check the `InstanceCloudAssistantStatusSet.InstanceCloudAssistantStatus` array in the returned JSON, find the `CloudAssistantStatus` field for the target node:

- `"true"` → Cloud Assistant is online, proceed to Step 6
- `"false"` → Inform user that Cloud Assistant is offline, terminate the pipeline
- **API call failure** (e.g. `403 Forbidden.RAM` on `ecs:DescribeCloudAssistantStatus`, `aliyun-cli-ecs` plugin unavailable, or any other error) → tell the user the Cloud Assistant pre-check was skipped, then **continue to Step 6**

> **⚠️ This is a non-fatal pre-check.** Only an explicit `"false"` terminates the pipeline. A failed call MUST NOT terminate it, and MUST NOT be reported as a diagnosis failure — the real capability gates are Step 7 (`check-instance-support`) and Step 8 (`invoke-diagnosis`).

---

## Step 6 — SysOM Role Initialization

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

Ensures the SysOM service role has been created. This step is idempotent and can be executed repeatedly.

---

## Step 7 — Instance Support Check

```bash
aliyun sysom check-instance-support \
  --instances <instance_id> \
  --biz-region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

Verify the target lingjun node meets:
- Operating system is Linux
- Kernel version is compatible with SysOM diagnosis

If the node is not supported (`support: false`), report the returned reason to the user, explain that the node must first be onboarded to SysOM (Agent installation) in the SysOM console, and **stop** — this skill does not perform enrollment and MUST NOT call `install-agent` or any other product's API to work around it. When the user asks to bypass this gate (`skip_support_check`), skip Step 7 and let Step 8 act as the authoritative gate.

---

## Step 8 — Invoke Diagnosis and Poll Results

### 8a. Diagnosis Mode Decision

Based on the user's input parameter combination, determine the diagnosis mode:

```
if enable_diagnosis == true:
    mode = real-time diagnosis    # enable_diagnosis has highest priority, force start_time to 0
elif start_time != 0:
    mode = historical diagnosis   # time range specified, retrospective analysis
else:
    mode = real-time diagnosis    # default
```

#### Optional Parameters and Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `start_time` | `0` | Diagnosis start timestamp (Unix seconds) |
| `end_time` | `0` | Diagnosis end timestamp (Unix seconds) |
| `enable_diagnosis` | `false` | Force real-time diagnosis |
| `ocd_description` | `""` | Problem description for intent recognition (English only) |
| `uid` | `None` | Account ID owning the lingjun node |
| `skip_support_check` | `false` | Skip node support check (speeds up workflow) |

### 8b. Build params JSON

Use **snake_case** keys (consistent with SDK). Required base fields (**ALL must be included**):

```json
{
  "instance": "<instance_id>",
  "region": "<region>",
  "start_time": 0,
  "end_time": 0,
  "type": "ocd",
  "ai_roadmap": true,
  "enable_sysom_link": false
}
```

> **⚠️ Anti-confusion Warning: `"type": "ocd"` is a REQUIRED field inside the params JSON — do NOT omit it!**
>
> `--service-name ocd` (CLI argument) and `"type": "ocd"` (params JSON field) are **two different levels of parameters**, both are mandatory:
> - `--service-name ocd` → tells CLI which diagnosis service endpoint to call
> - `"type": "ocd"` → tells the diagnosis engine which diagnosis type to execute internally
>
> **Do NOT omit `"type": "ocd"` from params just because `--service-name` already specifies `ocd`!**

Conditional fields (add to JSON only when non-empty / when applicable):
- `"ocd_description": "<english_keywords>"` — add when user's problem description is not empty
- `"uid": <integer>` — add when user provides an account ID

lingjun-mandatory field:
- `"product": "LINGJUN"` — **MUST always be included for lingjun nodes**

**Impact of diagnosis mode on params**:
- **Real-time**: `start_time: 0`, `end_time: 0`
- **Historical**: `start_time: <unix_ts>`, `end_time: <unix_ts>`
- **Forced real-time** (`enable_diagnosis=true`): force `start_time` to `0` even if user provided a value

### 8c. Channel Selection

This skill only targets lingjun nodes, so the channel is fixed:

| Node Type | ID Pattern | `--channel` Value | Required `product` in params |
|-----------|------------|-------------------|------------------------------|
| lingjun node | Starts with `e01-` (e.g., `e01-cn-xxxxx`) | `eflo` | `"LINGJUN"` |

### 8d. Invoke Diagnosis


**lingjun node example**

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel eflo \
  --params '{"instance":"<instance_id>","region":"<region>","start_time":<start_time>,"end_time":<end_time>,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false,"product":"LINGJUN","ocd_description":"<ocd_description>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

> **⚠️ `--channel eflo` and `"product": "LINGJUN"` are both mandatory — omitting either will cause the diagnosis to fail or be routed to the wrong engine.**

Extract `task_id` from the response.

**Special handling**: If `Sysom.TaskInProgress` error is returned, it means a diagnosis task is already in progress. Extract the existing `task_id` from the error message (regex match `ocd(<task_id>)`) and proceed directly to polling.

### 8e. Poll Diagnosis Results

Interval: 10 seconds, max 60 attempts:

```bash
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

Check the `status` field in the response:
- `Ready` / `Running` → continue polling
- `Success` → diagnosis complete, proceed to Step 9
- `Fail` → diagnosis failed, inform the user with the `Fail` template below

> **⛔ Behavioral Constraints During Polling (MUST OBEY):**
>
> During polling while waiting for diagnosis results, the following actions are **STRICTLY FORBIDDEN (both executing and suggesting to the user)**:
> 1. **FORBIDDEN** to invoke Cloud Assistant to execute commands on the lingjun node (e.g., `top`, `vmstat`, `dmesg`, `iostat`)
> 2. **FORBIDDEN** to call CloudMonitor or any other monitoring APIs
> 3. **FORBIDDEN** to attempt "alternative diagnosis methods" or initiate new diagnosis tasks
> 4. **FORBIDDEN** to call any command not listed in this skill's [Command Tables]
> 5. **FORBIDDEN** to suggest any of the above actions to the user as "alternatives" or "fallback options"
> 6. **FORBIDDEN** to delegate polling to a background job / monitor / scheduled task and end the turn with "I will parse the result once the monitor catches Success or Fail" — polling is your own foreground work in this turn, and a deferred promise is not a result
>
> **The ONLY permitted action**: continue calling `aliyun sysom get-diagnosis-result` to poll, or stop after timeout.
>
> **⛔ Turn-completion rule:** the turn may end in exactly one of three states — `Success` → the Step 9 report · `Fail` → the failure template · 60 attempts exhausted → the timeout template. **Never end a turn while the status is still `Ready` / `Running`**, and never replace one of these three outputs with a status update about polling still being in flight.
>
> **Timeout handling**: If still incomplete after 60 polling attempts, you **MUST and can ONLY** output the following template, then stop. Output it **in the same language the user used** — do NOT hand a Chinese-speaking user an English-only notice.
>
> ```
> ⏳ SysOM diagnosis task timed out
> - Task ID: <task_id>
> - Current status: <status>
> - Suggestion: Please continue waiting for the diagnosis to complete.
> ```
>
> **⚠️ Do NOT claim or imply that any diagnosis conclusion was obtained.** A timed-out task produced no result — state only the task ID, the status, and the suggestion to keep waiting.
>
> **The single permitted addition:** when the user declined monitoring / enrollment / alerts, the mandatory closing statement (see SKILL.md Phase 3) is appended after this template, in the user's language — e.g. `As requested, monitoring and alert configuration are skipped — this was a one-time diagnosis.` The same applies to the `Fail` template below.
>
> **FORBIDDEN to add any "alternative diagnosis method" suggestions in the timeout output. Actions that cannot be performed must not be suggested.**
>
> **`Fail` handling**: When `status` is `Fail`, output the following template (again **in the user's language**), then stop — the same constraints apply:
>
> ```
> ❌ SysOM diagnosis task failed
> - Task ID: <task_id>
> - Reason: <error message from the response, verbatim>
> - Suggestion: Please retry the diagnosis later.
> ```

---

## Step 9 — Result Parsing and Output

### Key Field Interpretation

| Field | Meaning | Where it goes in the report |
|-------|---------|-----------------------------|
| `summary.overall_status` | Overall status (Info/Warn/Critical) | Section 1 — Overall status |
| `summary.root_cause` | SysOM root cause analysis | Section 2 — Root cause |
| `issues[]` | Issues found by each sub-diagnostic item | Section 3 — Issue list, one line per item with a severity prefix |
| `summary.suggestions` | Remediation suggestion list | Section 4 — Suggested fix steps, numbered |
| `diagnose_mode` | Diagnosis mode identifier | Section 5 — Diagnosis mode (historical mode also states the time window) |

### Mandatory Report Layout

The five sections above are **always** output, in that order, even if a section is empty (write `none` instead of dropping the heading). Use the user's language, translating the section labels below as needed.

---

> ## 🔍 SysOM Diagnosis Report — `<instance_id>` (`<region>`)
>
> **Overall status**: `<summary.overall_status>`
>
> ### Root cause
> `<summary.root_cause>`
>
> ### Issue list
> - **[Critical]** `<issue title>` — `<measured values>`
> - **[Warn]** `<issue title>` — `<measured values>`
>
> ### Suggested fix steps
> 1. `<immediate mitigation>`
> 2. `<cleanup>`
> 3. `<configuration tuning>`
> 4. `<long-term fix>`
>
> ### Diagnosis mode
> `<real-time | historical (start_time–end_time)>` · task_id: `<task_id>`

---

**Content rules:**

1. Severity prefixes are fixed: `[Critical]` / `[Warn]` / `[Info]`, mapped from each item's severity in `issues[]`
2. Every issue line carries the measured values returned by the API (IOPS, utilization, load average, PID, file path, kernel function name) — no vague wording such as "IO is busy"
3. Suggestions are ordered from immediate mitigation to long-term fix; high-risk actions (`kill`, service restart, file deletion) stay suggestions until the user confirms
4. **Never fabricate a root cause**: on `Fail` or polling timeout use the failure/timeout templates in Step 8 instead of this layout, and report only task_id, status and the next step
5. When Step 7 returned `support: false`, no report is produced at all — state the API reason and stop

---

## SysOM Diagnosis Capability Coverage

| Subsystem | Diagnostic Tool | Diagnostic Content |
|-----------|----------------|-------------------|
| CPU | monitor | User-space/kernel-space CPU usage analysis, CPU saturation detection |
| Memory | memgraph | Memory panoramic analysis, memory leak detection, OOM diagnosis |
| IO | iofsstat, iodiagnose | IO traffic attribution analysis, IO latency diagnosis, iowait analysis |
| Network | packetdrop, netjitter | Packet loss diagnosis, network jitter analysis |
| Load | loadtask | System load anomaly analysis, load jitter diagnosis |
| Scheduling | delay | CPU scheduling jitter, scheduling latency diagnosis |
| Crash | vmcore | Crash cause analysis, kernel panic diagnosis |
| Health Score | healthy_score | Overall server health scoring |
