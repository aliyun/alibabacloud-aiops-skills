# Diagnosis Execution Detailed Workflow

This document contains the detailed execution steps for SysOM deep diagnosis on PAI products (Steps 4–8).

All `aliyun` CLI **business commands** (SysOM, EAS, DLC API calls) **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis`. System commands (`version`, `configure`, `plugin`) do NOT use `--user-agent`.

---

## Step 4 — Ambiguous Problem Clarification (Inversion Gate)

Before entering the diagnosis pipeline, **the following required parameters MUST be confirmed**. If the user's question does not include `region` or `instance`, you must ask the user — **do NOT guess or use default values**. The `product` field is auto-inferred from the `instance` prefix (`eas-` → `EAS`, `dlc` → `DLC`); only ask the user when inference fails.

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `region` | Region of the PAI resource | `cn-hangzhou`, `cn-beijing`, `cn-shanghai` |
| `instance` | PAI instance ID — EAS service ID or DLC job ID | `eas-m-bp79exq2lzbd0ctdfu`, `dlcxxxxxxxx` |
| `product` | PAI sub-product type | `EAS` or `DLC` |

### Clarification Flow

**4a. Check if the user's input already contains region, instance, and product**

Extract these parameters from the user's problem description. Common expressions include:
- "EAS service eas-m-bp79xxx in Hangzhou" → `region=cn-hangzhou`, `instance=eas-m-bp79xxx`, `product=EAS` (inferred)
- "DLC job dlcyyy123 in Beijing" → `region=cn-beijing`, `instance=dlcyyy123`, `product=DLC` (inferred)

**4b. Product Auto-Inference**

The `product` field is determined automatically from the `instance` prefix — do NOT ask the user to confirm unless inference fails:

| Instance Prefix | Inferred Product |
|----------------|-----------------|
| `eas-` (e.g., `eas-m-xxx`) | `EAS` |
| `dlc` (no hyphen, e.g., `dlcxxxxxxxx`) | `DLC` |
| Anything else | Cannot infer — must ask user |

Only when the prefix is unrecognizable, ask:

> 🔍 I couldn't determine the product type from your instance ID `<instance>`. Is this a **PAI EAS** service or a **PAI DLC** job?

**4c. If region, instance, or anomaly time is missing, ask the user**

> 🔍 To perform SysOM deep diagnosis on PAI, I need to confirm the following:
>
> - **Instance ID**: Please provide the EAS service ID (`eas-m-xxxxxxxx`) or DLC job ID (`dlcxxxxxxxx`)
> - **Region**: The Alibaba Cloud region where the resource is located (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`)
> - **When did the anomaly occur?**: Is the issue happening right now, or did it occur at a specific time in the past? (This determines whether to use real-time or historical diagnosis mode)

**4d. Also extract optional context**

- **Time range inference** (see below)
- `uid`: If the user mentioned an account ID

**⚠️ CRITICAL: Time Inference and Historical Diagnosis Recommendation**

When the user's description contains **any temporal reference** — even vague ones — you **MUST** proactively infer the time range and recommend historical diagnosis mode. Do NOT silently default to real-time diagnosis when the problem clearly occurred in the past.

**Time inference examples:**

| User Description | Inferred Action |
|-----------------|----------------|
| "The EAS service had high latency this morning" | Ask: "When exactly did the latency spike happen this morning? I'll use historical diagnosis to analyze that time window." |
| "Yesterday afternoon the DLC job slowed down" | Ask: "Around what time yesterday afternoon? I'll run historical diagnosis for that period." |
| "The service crashed around 3am" | Convert to Unix timestamps for today's 3am (±30min buffer), recommend historical diagnosis |
| "DLC training has been stuck for the past 2 hours" | Calculate `start_time = now - 2h`, recommend historical diagnosis |
| "The EAS service is slow right now" | No time inference needed, use real-time diagnosis (default) |

**Rules:**
1. If the user mentions a **past event** (crash, OOM, latency spike that already happened), you **MUST** ask for the specific time and recommend historical diagnosis
2. If the user describes an **ongoing issue** ("right now", "currently"), use real-time diagnosis
3. When asking for time, also provide the option: "Or would you prefer a real-time diagnosis to check the current state?"
4. Convert natural language time references to Unix timestamps using the current time as reference

---

## Step 5 — SysOM Role Initialization

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

Ensures the SysOM service role has been created. This step is idempotent and can be executed repeatedly.

> **Note**: PAI EAS / DLC are fully managed services. There is no separate "Cloud Assistant online check" or "instance support check" — SysOM accesses these resources through the PAI platform side. Therefore Steps 5/7 in the ECS workflow (`describe-cloud-assistant-status` / `check-instance-support`) do NOT apply here.

---

## Step 6 — Resource Validation

Before invoking diagnosis, you **MUST** validate the resource based on the inferred `product`. Both EAS and DLC require validation — proceed to 6A or 6B accordingly.

> **⚠️ The `instance` field in params JSON always uses the original instance ID directly (`eas-m-xxx` or `dlcxxxxxxxx`) — this step is purely for validation.**

---

### 6A. EAS — Verify Service Exists

#### 6A-1. Call ListServices

```bash
aliyun eas list-services \
  --region <region> \
  --filter <eas_service_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

> **⚠️ `list-services` does NOT support a `--service-id` parameter.** Use `--filter` instead, which performs **fuzzy matching by service name**. The EAS service ID (e.g., `eas-m-xxx`) is passed to `--filter` as a search hint.

#### 6A-2. Verify Service Exists

From the returned `Services` array, find the entry whose `ServiceId` **exactly matches** the user-provided ID. Do NOT blindly trust the first result — `--filter` is fuzzy and may return multiple services.

If a matching entry is found, the EAS service is valid — proceed to Step 7.

#### 6A-3. Failure Handling

| Scenario | Action |
|----------|--------|
| `ListServices` returns empty `Services` array or no entry matches the `ServiceId` | Inform user the service ID does not exist in `<region>`; stop pipeline |
| `ListServices` returns Forbidden / permission error | Guide user to grant `eas:ListServices` permission |
| API timeout / network error | Retry once; if still failing, ask user whether to continue |

---

### 6B. DLC — Verify Resource Type is Lingjun

#### 6B-1. Call GetJob

```bash
aliyun pai-dlc get-job \
  --region <region> \
  --job-id <dlc_job_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

#### 6B-2. Check ResourceType

From the response, check the `ResourceType` field:

- `Lingjun` → resource type is supported, proceed to Step 7
- Any other value (e.g., `ECS`, `Lingjun-Share`) → **STOP** the pipeline and inform the user:

> ⚠️ SysOM diagnosis currently only supports DLC jobs running on **Lingjun** resources. Your job `<dlc_job_id>` uses `<ResourceType>`, which is not yet supported.

#### 6B-3. Failure Handling

| Scenario | Action |
|----------|--------|
| `GetJob` returns job not found / empty response | Inform user the DLC job ID does not exist; stop pipeline |
| `ResourceType` is not `Lingjun` | Inform user that SysOM does not support this resource type; stop pipeline |
| `GetJob` returns Forbidden / permission error | Guide user to grant `pai-dlc:GetJob` permission |
| API timeout / network error | Retry once; if still failing, ask user whether to continue |

---

## Step 7 — Invoke Diagnosis and Poll Results

### 7a. Diagnosis Mode Decision

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
| `uid` | `None` | Account ID owning the resource |

### 7b. Build params JSON

Use **snake_case** keys (consistent with SDK). Required base fields (**ALL must be included**):

```json
{
  "instance": "<eas_service_id_or_dlc_job_id>",
  "region": "<region>",
  "product": "<EAS_or_DLC>",
  "start_time": 0,
  "end_time": 0,
  "type": "ocd",
  "ai_roadmap": true,
  "enable_sysom_link": false
}
```

> **⚠️ Anti-confusion Warnings:**
>
> 1. **`"type": "ocd"` is REQUIRED inside params JSON** — do NOT omit it. `--service-name ocd` (CLI argument) and `"type": "ocd"` (params JSON field) are two different levels of parameters, both mandatory:
>    - `--service-name ocd` → tells CLI which diagnosis service endpoint to call
>    - `"type": "ocd"` → tells the diagnosis engine which diagnosis type to execute internally
>
> 2. **`"product": "<EAS|DLC>"` is REQUIRED inside params JSON** — this is the key field that tells the SysOM diagnosis engine which PAI sub-product is being diagnosed. Omitting it will cause the engine to fall back to ECS mode and produce wrong results.
>
> 3. **The `instance` field uses the original instance ID directly — `eas-m-xxx` for EAS, `dlcxxxxxxxx` for DLC.** Do NOT convert to ServiceName or any other identifier.

Conditional fields (add to JSON only when non-empty):
- `"uid": <integer>` — add when user provides an account ID
- `"ocd_description": "<string>"` — user's problem description. **Format constraints**: must be in English, no Chinese characters, no spaces — use underscores (`_`) to join words. Example: `"high_latency_first_token"`, `"GPU_OOM_killed"`

**Impact of diagnosis mode on params**:
- **Real-time**: `start_time: 0`, `end_time: 0`
- **Historical**: `start_time: <unix_ts>`, `end_time: <unix_ts>`
- **Forced real-time** (`enable_diagnosis=true`): force `start_time` to `0` even if user provided a value

### 7c. Invoke Diagnosis

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"instance":"<eas_service_id_or_dlc_job_id>","region":"<region>","product":"<EAS|DLC>","start_time":<start_time>,"end_time":<end_time>,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

> **Note on `--channel ecs`**: Although the underlying PAI compute resources differ from ECS, the SysOM diagnosis dispatch channel is still `ecs` (the engine routes by `product` field internally). Do NOT change `--channel` to `eas` or `dlc`.

Extract `task_id` from the response.

> **⚠️ [CRITICAL] `Sysom.TaskInProgress` Error Handling:**
> If `invoke-diagnosis` returns a `Sysom.TaskInProgress` error, this means a diagnosis task is already running. You **MUST**:
> 1. Extract the existing `task_id` from the error message using string match (pattern: `ocd(<task_id>)` or similar identifier in the message body)
> 2. Immediately proceed to the polling flow below with the extracted `task_id`
> 3. **NEVER** treat `TaskInProgress` as a fatal failure or abort the workflow
> 4. **NEVER** re-invoke `invoke-diagnosis` — proceed directly to polling with the extracted task_id

### 7d. Poll Diagnosis Results

Interval: 10 seconds, max 60 attempts:

```bash
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

Check the `status` field in the response:
- `Ready` / `Running` → **MUST** continue polling at 10s intervals
- `Success` → diagnosis complete, proceed to Step 8
- `Fail` → diagnosis failed, inform the user

> **⛔ [CRITICAL] Mandatory Polling Rules (MUST OBEY — violations will produce incorrect results):**
>
> **Rule 1: `Running` status is NORMAL — keep polling.**
> The diagnosis engine typically takes 1–5 minutes to complete. Receiving multiple consecutive `Running` responses is expected behavior. You **MUST** continue polling every 10 seconds without hesitation. `Running` is NOT an error, NOT a sign of failure, and MUST NOT trigger early termination or fallback behavior.
>
> **Rule 2: NEVER abandon polling early.**
> Do NOT stop polling before reaching `Success`, `Fail`, or the 60-attempt limit (10 minutes total). Do NOT "give up" after a few `Running` responses. Do NOT conclude that the task is "stuck" based on consecutive `Running` statuses.
>
> **Rule 3: NEVER fall back to manual analysis.**
> If polling is ongoing or timed out, you MUST NOT attempt to manually diagnose the issue by analyzing `ListServices` output, instance metadata, or any other data source. The SysOM diagnosis report is the **ONLY** valid source of root cause and remediation information for this skill.
>
> **Rule 4: NEVER fabricate diagnosis results.**
> If the task has not reached `Success` status, you MUST NOT output any `summary.overall_status`, `summary.root_cause`, or `summary.suggestions` values. These fields come **exclusively** from the completed diagnosis result JSON. Generating, guessing, or inferring these fields from other sources is STRICTLY FORBIDDEN.
>
> **Rule 5: FORBIDDEN actions during polling (both executing and suggesting to the user):**
> 1. **FORBIDDEN** to invoke any commands on PAI underlying nodes (PAI is fully managed; no instance-level shell access is permitted via this skill)
> 2. **FORBIDDEN** to call PAI EAS / DLC management APIs other than `ListServices` (already used in Step 6)
> 3. **FORBIDDEN** to attempt "alternative diagnosis methods" or initiate new diagnosis tasks
> 4. **FORBIDDEN** to call any command not listed in this skill's Command Tables
> 5. **FORBIDDEN** to suggest any of the above actions to the user as "alternatives" or "fallback options"
>
> **The ONLY permitted action**: continue calling `aliyun sysom get-diagnosis-result` to poll, or stop after timeout.
>
> **Timeout handling**: If still incomplete after 60 polling attempts, you **MUST and can ONLY** output the following template, then stop:
>
> ```
> ⏳ SysOM diagnosis task timed out
> - Task ID: <task_id>
> - Current status: <status>
> - Suggestion: Please continue waiting for the diagnosis to complete.
> ```
>
> **FORBIDDEN to add alternative suggestions, manual analysis, or fabricated conclusions in timeout output. Actions that cannot be performed must not be suggested.**

---

## Step 8 — Result Parsing and Output

### Key Field Interpretation

| Field | Meaning | How Agent Should Use It |
|-------|---------|------------------------|
| `summary.overall_status` | Overall status (Info/Warn/Critical) | Determine problem severity |
| `summary.root_cause` | SysOM root cause analysis | Kernel-level / runtime root cause evidence |
| `summary.suggestions` | Remediation suggestion list | Incorporate directly into recommendations |
| `issues[]` | Issues found by each sub-diagnostic item | Analyze item by item to locate specific subsystem |
| `diagnose_mode` | Diagnosis mode identifier | Distinguish real-time vs. historical diagnosis |
| `product` | Echoed product field | Confirm engine routed to correct PAI sub-product |

---

## SysOM Diagnosis Capability Coverage on PAI

| Subsystem | Diagnostic Tool | Diagnostic Content | Applicable To |
|-----------|----------------|-------------------|---------------|
| CPU | monitor | User-space/kernel-space CPU usage analysis, CPU saturation | EAS / DLC |
| Memory | memgraph | Memory panoramic analysis, memory leak detection, OOM diagnosis | EAS / DLC |
| IO | iofsstat, iodiagnose | IO traffic attribution, IO latency, iowait analysis | EAS / DLC |
| Network | packetdrop, netjitter | Packet loss, network jitter analysis | EAS / DLC |
| Load | loadtask | System load anomaly, load jitter | EAS / DLC |
| Scheduling | delay | CPU scheduling jitter, scheduling latency | EAS / DLC |
| GPU | gpu_diag | GPU utilization, GPU memory, GPU hang detection | EAS (GPU) / DLC |
| Inference Latency | inference_latency | EAS request latency / QPS attribution | EAS only |
| Training Throughput | training_throughput | Per-step time, communication overhead, hang detection | DLC only |
| Health Score | healthy_score | Overall resource health scoring | EAS / DLC |
