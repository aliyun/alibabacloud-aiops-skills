# Diagnosis Execution Detailed Workflow

This document contains the detailed execution steps for SysOM deep diagnosis (Steps 4–9), referenced from the Core Workflow in SKILL.md.

All `aliyun` CLI commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills`.

---

## Step 4 — Ambiguous Problem Clarification (Inversion Gate)

Before entering the diagnosis pipeline, **the following two required parameters MUST be confirmed**. If the user's question does not include this information, you must ask the user — **do NOT guess or use default values**.

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `region` | Region of the ECS instance | `cn-hangzhou`, `cn-beijing`, `cn-shanghai` |
| `instance_id` | ECS instance ID | `i-bp1xxxxxxxxxxxxxxx` |

### Clarification Flow

**4a. Check if the user's input already contains region and instance_id**

Extract these two parameters from the user's problem description. Common expressions include:
- "instance i-bp1xxx in Hangzhou" (region=cn-hangzhou, instance_id=i-bp1xxx)
- "instance i-bp1xxx in Beijing" (region=cn-beijing, instance_id=i-bp1xxx)

**4b. If either parameter is missing, ask the user**

> 🔍 To perform SysOM deep diagnosis, I need to confirm the following:
>
> - **Instance ID**: Please provide the ECS instance ID (format: `i-bp1xxxxxxxx`)
> - **Region**: The Alibaba Cloud region where the instance is located (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`)

**4c. Also extract optional context**

- `ocd_description`: The problem symptoms described by the user
- **Time range inference** (see below)
- `uid`: If the user mentioned an account ID

**⚠️ CRITICAL: Time Inference and Historical Diagnosis Recommendation**

When the user's description contains **any temporal reference** — even vague ones — you **MUST** proactively infer the time range and recommend historical diagnosis mode. Do NOT silently default to real-time diagnosis when the problem clearly occurred in the past.

**Time inference examples:**

| User Description | Inferred Action |
|-----------------|----------------|
| "The server crashed this morning" | Ask: "When exactly did the crash happen this morning? I'll use historical diagnosis to analyze that time window." |
| "Yesterday afternoon there was high CPU" | Ask: "Around what time yesterday afternoon? I'll run historical diagnosis for that period." |
| "It went down around 3am" | Convert to Unix timestamps for today's 3am (±30min buffer), recommend historical diagnosis |
| "The instance rebooted unexpectedly last night" | Ask for approximate time, recommend historical diagnosis |
| "There's been high load for the past 2 hours" | Calculate start_time = now - 2h, recommend historical diagnosis |
| "The server is slow right now" | No time inference needed, use real-time diagnosis (default) |

**Rules:**
1. If the user mentions a **past event** (crash, reboot, spike that already happened), you **MUST** ask for the specific time and recommend historical diagnosis
2. If the user describes an **ongoing issue** ("right now", "currently"), use real-time diagnosis
3. When asking for time, also provide the option: "Or would you prefer a real-time diagnosis to check the current state?"
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
  --user-agent AlibabaCloud-Agent-Skills
```

Check the `InstanceCloudAssistantStatusSet.InstanceCloudAssistantStatus` array in the returned JSON, find the `CloudAssistantStatus` field for the target instance:

- `"true"` → Cloud Assistant is online, proceed to Step 6
- `"false"` → Inform user that Cloud Assistant is offline, terminate the pipeline
- API call failure → Ask user whether to continue

---

## Step 6 — SysOM Role Initialization

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills
```

Ensures the SysOM service role has been created. This step is idempotent and can be executed repeatedly.

---

## Step 7 — Instance Support Check

```bash
aliyun sysom check-instance-support \
  --instances <instance_id> \
  --biz-region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

Verify the target instance meets:
- Operating system is Linux
- Kernel version is compatible with SysOM diagnosis

If the instance is not supported, a clear failure reason is returned — suggest falling back to standard diagnosis.

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
| `uid` | `None` | Account ID owning the instance |
| `skip_support_check` | `false` | Skip instance support check (speeds up workflow) |

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

Conditional fields (add to JSON only when non-empty):
- `"ocd_description": "<english_keywords>"` — add when user's problem description is not empty
- `"uid": <integer>` — add when user provides an account ID

**Impact of diagnosis mode on params**:
- **Real-time**: `start_time: 0`, `end_time: 0`
- **Historical**: `start_time: <unix_ts>`, `end_time: <unix_ts>`
- **Forced real-time** (`enable_diagnosis=true`): force `start_time` to `0` even if user provided a value

### 8c. Invoke Diagnosis

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"instance":"<instance_id>","region":"<region>","start_time":<start_time>,"end_time":<end_time>,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false,"ocd_description":"<ocd_description>"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

Extract `task_id` from the response.

**Special handling**: If `Sysom.TaskInProgress` error is returned, it means a diagnosis task is already in progress. Extract the existing `task_id` from the error message (regex match `ocd(<task_id>)`) and proceed directly to polling.

### 8d. Poll Diagnosis Results

Interval: 10 seconds, max 60 attempts:

```bash
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills
```

Check the `status` field in the response:
- `Ready` / `Running` → continue polling
- `Success` → diagnosis complete, proceed to Step 9
- `Fail` → diagnosis failed, inform the user

> **⛔ Behavioral Constraints During Polling (MUST OBEY):**
>
> During polling while waiting for diagnosis results, the following actions are **STRICTLY FORBIDDEN (both executing and suggesting to the user)**:
> 1. **FORBIDDEN** to invoke Cloud Assistant to execute commands on the instance (e.g., `top`, `vmstat`, `dmesg`, `iostat`)
> 2. **FORBIDDEN** to call ECS monitoring, CloudMonitor, or other APIs
> 3. **FORBIDDEN** to attempt "alternative diagnosis methods" or initiate new diagnosis tasks
> 4. **FORBIDDEN** to call any command not listed in this skill's [Command Tables]
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
> **FORBIDDEN to add any "alternative diagnosis method" suggestions in the timeout output. Actions that cannot be performed must not be suggested.**

---

## Step 9 — Result Parsing and Output

### Key Field Interpretation

| Field | Meaning | How Agent Should Use It |
|-------|---------|------------------------|
| `summary.overall_status` | Overall status (Info/Warn/Critical) | Determine problem severity |
| `summary.root_cause` | SysOM root cause analysis | Kernel-level root cause evidence |
| `summary.suggestions` | Remediation suggestion list | Incorporate directly into recommendations |
| `issues[]` | Issues found by each sub-diagnostic item | Analyze item by item to locate specific subsystem |
| `diagnose_mode` | Diagnosis mode identifier | Distinguish real-time vs. historical diagnosis |

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
