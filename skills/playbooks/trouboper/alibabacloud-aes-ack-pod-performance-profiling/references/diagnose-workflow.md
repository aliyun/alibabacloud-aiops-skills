# Diagnosis Execution Detailed Workflow

This document contains the detailed execution steps for SysOM ACK Pod diagnosis (Steps 4–9), referenced from the Core Workflow in SKILL.md.

All non-system `aliyun` CLI commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling`. System commands (`configure`, `version`, `plugin`) **MUST NOT** use the `--user-agent` flag.

> **⛔ MANDATORY EXECUTION CHAIN — DO NOT SKIP, DO NOT REORDER, DO NOT EXPLORE ALTERNATIVES**
>
> Once Step 4 parameter clarification completes, you MUST execute the following four API calls in order. Each is a hard requirement; skipping any constitutes a workflow failure:
>
> 1. **Step 5** — `aliyun cs GET /clusters/<cluster_id>` (cs.DescribeClusterDetail)
> 2. **Step 6** — `aliyun sysom initial-sysom --check-only false --source aes-skills` (sysom.InitialSysom) — REQUIRED
> 3. **Step 7** — `.sysom-sdk-venv/bin/python scripts/create-cluster-vpc-endpoint-connection.py ...` (cs.CreateClusterVpcEndpointConnection via SDK) — REQUIRED
> 4. **Step 8** — `aliyun sysom invoke-diagnosis ...` (sysom.InvokeDiagnosis) followed by polling via `aliyun sysom get-diagnosis-result --task-id <task_id>` (sysom.GetDiagnosisResult) — REQUIRED
>
> **⛔ CRITICAL: The diagnosis API is `sysom invoke-diagnosis`, NOT the CS cluster diagnosis endpoint.**
> The CS product has a separate diagnosis API (`cs POST /clusters/<cluster_id>/diagnosis` aka `cs:CreateClusterDiagnosis`) — this is a COMPLETELY DIFFERENT feature and MUST NOT be used. If you call `cs:CreateClusterDiagnosis` or `aliyun cs POST /clusters/.../diagnosis`, the workflow FAILS. The ONLY correct diagnosis API for this skill is `aliyun sysom invoke-diagnosis`.
>
> **STRICTLY FORBIDDEN** behaviors that have caused real eval failures:
>
> - **FORBIDDEN** to use `cs:CreateClusterDiagnosis` / `aliyun cs POST /clusters/<cluster_id>/diagnosis` for diagnosis. This is the WRONG API. This skill uses SysOM diagnosis (`sysom invoke-diagnosis`), NOT CS cluster diagnosis.
> - **FORBIDDEN** to call `aliyun sysom --help` / `aliyun sysom <subcommand> --help` for "discovery". The only sysom subcommands this skill uses are `initial-sysom`, `invoke-diagnosis`, `get-diagnosis-result`. Do NOT read help for any other sysom subcommand.
> - **FORBIDDEN** to invoke any sysom subcommand other than the three above. In particular, the following MUST NOT be called: `list-abnormaly-events`, `describe-metric-list`, `get-resources`, `list-pods-of-instance`, or any other sysom subcommand not listed in this workflow.
> - **FORBIDDEN** to substitute any mandatory call with a "more convenient" alternative from sysom help or any CS product API.
> - **FORBIDDEN** to terminate the workflow after Step 5 / Step 6 / Step 7 without proceeding through Step 8 (invoke-diagnosis + polling).
> - **FORBIDDEN** to declare success without `task_id` having been obtained AND polled to a terminal state.
> - **FORBIDDEN** to skip Steps 6 and 7 when Step 5 succeeds. Even if Step 5 returns valid cluster info, you MUST still execute Steps 6, 7, and 8 in order.

---

## Step 4 — Parameter Clarification (Inversion Gate)

Before entering the diagnosis pipeline, **the following required parameters MUST be confirmed**. If the user's question does not include this information, you must ask the user — **do NOT guess or use default values**.

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `cluster_id` | ACK cluster ID | `c0ee8f62dd10541c598af3627d5b6cda7` |
| `namespace` | Kubernetes namespace | `default`, `kube-system` |
| `pod` | Pod name | `test-app-64cdcb7b98-gchks` |

### Clarification Flow

**4a. Check if the user's input already contains cluster_id, namespace, and pod**

Extract these parameters from the user's problem description. Common expressions include:
- "Pod test-app in cluster c0ee8f62... namespace default" (all three provided)
- "Pod xxx keeps crashing" (need to ask for cluster_id and namespace)

**4b. If any required parameter is missing, ask the user**

> 🔍 To perform SysOM ACK Pod diagnosis, I need to confirm the following:
>
> - **Cluster ID**: ACK cluster ID (format: `c` followed by 32 hex characters)
> - **Namespace**: The Kubernetes namespace where the Pod is located
> - **Pod Name**: The exact Pod name to diagnose
>
> Please provide these parameters.

**4c. Also extract optional context**

- `description`: The problem symptoms described by the user (supports Chinese)
- **Time range inference** (see below)

**⚠️ CRITICAL: Time Inference and Historical Diagnosis Recommendation**

When the user's description contains **any temporal reference** — even vague ones — you **MUST** proactively infer the time range and recommend historical diagnosis mode.

**Time inference examples:**

| User Description | Inferred Action |
|-----------------|----------------|
| "Pod OOM killed this morning" | Ask: "When exactly did the OOM happen this morning? I'll use historical diagnosis to analyze that time window." |
| "Yesterday afternoon the Pod had high CPU" | Ask: "Around what time yesterday afternoon? I'll run historical diagnosis for that period." |
| "Pod restarted around 3am" | Convert to Unix timestamps for today's 3am (±30min buffer), recommend historical diagnosis |
| "The Pod has been slow for the past 2 hours" | Calculate start_time = now - 2h, recommend historical diagnosis |
| "The Pod is crashing right now" | No time inference needed, use real-time diagnosis (default) |

**Rules:**
1. If the user mentions a **past event**, you **MUST** ask for the specific time and recommend historical diagnosis
2. If the user describes an **ongoing issue** ("right now", "currently"), use real-time diagnosis
3. When asking for time, also provide the option: "Or would you prefer a real-time diagnosis to check the current state?"
4. Convert natural language time references to Unix timestamps using the current time as reference

---

## Step 5 — Cluster Information Retrieval

> **API invoked**: `cs.DescribeClusterDetail` (POP code `cs`, version `2015-12-15`).
> Invoke via the CLI ROA path form `aliyun cs GET /clusters/<cluster_id>` (plugin-mode compliant). The traditional PascalCase RPC form is **prohibited under SA-2.11**.

```bash
# API: DescribeClusterDetail (cs:2015-12-15) — ROA path form
aliyun cs GET /clusters/<cluster_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

### Purpose
- Verify the cluster exists and is in `running` state
- Extract `region_id` for use in subsequent steps
- Extract `profile` to validate cluster type — **MUST be `"Default"`**
- Record cluster name for reference

### Cluster Type Validation (Hard STOP gate)

Extract the `profile` field from the `DescribeClusterDetail` response:

- `profile == "Default"` → standard ACK managed cluster, **proceed** with diagnosis.
- `profile != "Default"` (e.g., `"acs"`, `"Serverless"`, `"Edge"`, etc.) → **STOP immediately**. Output the following and terminate:

```
❌ Unsupported cluster type
- Cluster ID: <cluster_id>
- Cluster profile: <profile>
- This skill ONLY supports diagnosis on standard ACK managed clusters (profile = "Default").
- ACS clusters, ASK (Serverless Kubernetes) clusters, Edge clusters, and other non-Default profile clusters are NOT supported.
- Please provide a standard ACK cluster ID to proceed.
```

**FORBIDDEN** to proceed to Step 6 / 7 / 8 when `profile != "Default"`.

### Failure Handling — Hard STOP gate (fail-closed)

On ANY non-success response (404 / `ErrorClusterNotFound` / `Forbidden.RAM` / network error / cluster state not `running`), the workflow MUST stop immediately. The following are STRICTLY FORBIDDEN on Step 5 failure:

1. **FORBIDDEN** to synthesize, guess, or hard-code a `region` value when the response did not provide one.
2. **FORBIDDEN** to proceed to Step 6 / 7 / 8 without a verified `region_id`.
3. **FORBIDDEN** to create template diagnosis artifacts, fake `task_id`, or placeholder JSON output.
4. **FORBIDDEN** to silently retry with a different `cluster_id` without explicit user input.
5. **FORBIDDEN** to use any `cs` diagnosis API (e.g., `cs POST /clusters/<id>/diagnosis` aka `cs:CreateClusterDiagnosis`) as a fallback. The CS diagnosis API is a DIFFERENT feature — this skill uses SysOM `sysom invoke-diagnosis` exclusively.

**The ONLY permitted action on failure**: report the error verbatim to the user and request a corrected `cluster_id` (or appropriate RAM permission grant for `cs:DescribeClusterDetail`).

> **⛔ After Step 5 succeeds — CONTINUE TO STEP 6, do NOT diagnose via CS**:
> When Step 5 returns valid cluster details, the NEXT action is Step 6 (`sysom initial-sysom`). Do NOT attempt any CS-based diagnosis (`cs POST /clusters/<id>/diagnosis`, `cs:CreateClusterDiagnosis`). The diagnosis is performed through SysOM APIs (Steps 6→7→8), NEVER through the CS product.

---

## Step 6 — SysOM Role Initialization

> **⛔ MUST EXECUTE — this is NOT optional.** Skipping this call causes downstream `invoke-diagnosis` calls to fail with authorization errors.

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

Ensures the SysOM service role has been created. This step is idempotent and can be executed repeatedly.

---

## Step 7 — Create Cluster VPC Endpoint Connection (SDK Call)

> **API invoked**: `cs.CreateClusterVpcEndpointConnection` (POP code `cs`, version `2015-12-15`). The CLI does NOT support this action; the SDK script is the only mechanism.
>
> **⛔ MUST EXECUTE — this is NOT optional.** Without this call, the subsequent `invoke-diagnosis` cannot reach the cluster. The script is **idempotent** — safe to re-run.
>
> **[AUTO-EXECUTE]** Although this is a write operation that modifies network configuration, it runs automatically WITHOUT user confirmation, since it is a mandatory precondition for diagnosis.

> **⛔ HOW TO EXECUTE: You must run the following command in the terminal (shell).** This is a LOCAL Python script in this workspace — you must execute it as a shell command. Reading API documentation, web-fetching API metadata, or finding the API name in a list is NOT execution. The API call only happens when you run this script.

**Prerequisites** (run once if the venv does not exist):
```bash
bash scripts/setup-sdk.sh
```

**Execute VPC endpoint creation** (MANDATORY — run this in the terminal):
```bash
.sysom-sdk-venv/bin/python scripts/create-cluster-vpc-endpoint-connection.py \
  --region "<region>" \
  --cluster-id "<cluster_id>"
```

**Expected output on success**: `[OK] Cluster VPC endpoint connection created successfully.`

> **⚠️ `--dry-run` flag**: Only pass `--dry-run` (no value) when testing. For real execution, OMIT the flag entirely — do NOT pass `--dry-run false` or `--dry-run "false"` (the flag is boolean `store_true` and does not accept a value).

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute the script** — using the system `python3` is FORBIDDEN.
> If the venv is missing, run `bash scripts/setup-sdk.sh` first.

> **FORBIDDEN behaviors for Step 7:**
> - **FORBIDDEN** to skip this step. The VPC endpoint MUST be created before `invoke-diagnosis`.
> - **FORBIDDEN** to treat web-fetched API metadata or documentation listings as evidence of execution. The script must be RUN in the terminal.
> - **FORBIDDEN** to use `aliyun cs` CLI for this operation — the CLI does NOT support it. Only the SDK script works.
> - **FORBIDDEN** to proceed to Step 8 without running this script and seeing `[OK]` output.

---

## Step 8 — Invoke Diagnosis and Poll Results

> **⛔ MUST EXECUTE — this is NOT optional.** Both the `invoke-diagnosis` call AND the polling via `get-diagnosis-result` are required. The workflow is NOT complete until polling reaches a terminal status.

### 8a. Diagnosis Mode Decision

Based on the user's input parameter combination, determine the diagnosis mode:

```
if enable_diagnosis == true:
    mode = real-time diagnosis    # enable_diagnosis has highest priority
elif start_time != 0:
    mode = historical diagnosis   # time range specified, retrospective analysis
else:
    mode = real-time diagnosis    # default (enable_diagnosis defaults to true)
```

### 8b. Build params JSON

Required base fields (**ALL must be included**). Pick exactly one of the two templates below based on the mode decision in 8a.

**Real-time mode template** (default — when no time window was provided):

```json
{
  "product": "ACK",
  "region": "<region_id>",
  "instance": "ack-<cluster_id>",
  "cluster_id": "<cluster_id>",
  "namespace": "<namespace>",
  "pod": "<pod_name>",
  "description": "<sanitized_description>",
  "start_time": 0,
  "end_time": 0,
  "enable_diagnosis": true
}
```

**Historical mode template** (REQUIRED whenever the user described a past event with any temporal reference):

```json
{
  "product": "ACK",
  "region": "<region_id>",
  "instance": "ack-<cluster_id>",
  "cluster_id": "<cluster_id>",
  "namespace": "<namespace>",
  "pod": "<pod_name>",
  "description": "<sanitized_description>",
  "start_time": <unix_start_ts>,
  "end_time": <unix_end_ts>,
  "enable_diagnosis": false
}
```

> **⚠️ `description` field format constraint**: MUST match the regex `^[a-zA-Z0-9_-]*$` (only ASCII letters, digits, underscore `_`, and hyphen `-` are allowed). Spaces, Chinese characters, dots, tildes, and other special symbols are **rejected** by the API with `Sysom.InvalidParameter`. **If the source description contains spaces, replace each space with an underscore `_`** (e.g., `"pod oom"` → `"pod_oom"`, `"high cpu load"` → `"high_cpu_load"`).

**Field descriptions:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `product` | **Required** | string | Fixed value `"ACK"` — indicates ACK Pod-level diagnosis |
| `region` | **Required** | string | Region from `DescribeClusterDetail` response (`region_id` field) |
| `instance` | **Required** | string | Fixed format `ack-<cluster_id>` (e.g. `ack-cd5b0b91bc05540b1a4c1ddb37f5175c8`). Must match `^[a-zA-Z0-9_-]*$` |
| `cluster_id` | **Required** | string | ACK cluster ID |
| `namespace` | **Required** | string | Pod's Kubernetes namespace |
| `pod` | **Required** | string | Pod name to diagnose |
| `start_time` | **Required** | integer | 0 for real-time, Unix timestamp for historical |
| `end_time` | **Required** | integer | 0 for real-time, Unix timestamp for historical |
| `enable_diagnosis` | **Required** | boolean | `true` for real-time (highest priority), `false` for historical |
| `description` | Optional | string | Problem description keyword. **MUST match regex `^[a-zA-Z0-9_-]*$`** (ASCII letters, digits, `_`, `-` only). Replace any space with `_`. Examples: `"pod_oom"`, `"high_cpu"`, `"high_load"` |

### 8c. Invoke Diagnosis

> **⚠️ HARD RULE — `description` sanitization is MANDATORY for every `invoke-diagnosis` call**: the value embedded in `--params` MUST match `^[a-zA-Z0-9_-]*$`. Replace any space with `_` and strip any Chinese / Unicode / punctuation BEFORE invoking the API. Non-conforming values cause `Sysom.InvalidParameter`.

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"product":"ACK","region":"<region_id>","instance":"ack-<cluster_id>","cluster_id":"<cluster_id>","namespace":"<namespace>","pod":"<pod_name>","description":"<sanitized_description>","start_time":<start_time>,"end_time":<end_time>,"enable_diagnosis":<enable_diagnosis>}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

Extract `task_id` from the response.

**Special handling for `Sysom.TaskInProgress`**: If this error is returned, it means a diagnosis task is already running on the target instance. The error response body does **NOT** contain a `task_id` field (it only includes Code, Message, HostId, Recommend, RequestId). Therefore:

1. Wait 30 seconds, then retry `invoke-diagnosis` (max 3 retries total).
2. If a retry succeeds, extract `task_id` from the successful response and proceed to polling.
3. If all 3 retries still return `TaskInProgress`, **STOP** and output:

```
⚠️ An existing diagnosis task is running on this instance.
- Instance: ack-<cluster_id>
- Error: Sysom.TaskInProgress
- Suggestion: Please wait for the running task to complete (typically 3–5 minutes), then retry.
```

> **⛔ FORBIDDEN** (applies to both the retry loop above AND the case where all retries are exhausted):
> - Do NOT guess or fabricate a `task_id` value (e.g., using cluster_id, instance ID, RequestId, or pod name as task_id). The `task_id` MUST come from a successful `invoke-diagnosis` response.
> - Do NOT write custom SDK scripts or use alternative methods to invoke diagnosis. The ONLY permitted invocation is the CLI command shown above.
> - Do NOT proceed to `get-diagnosis-result` without a valid `task_id` obtained from a successful response.

### 8d. Poll Diagnosis Results

Interval: 10 seconds, max 60 attempts:

```bash
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

Check the `status` field in the response:
- `Ready` / `Running` → continue polling
- `Success` → diagnosis complete, proceed to Step 9
- `Fail` → diagnosis failed, inform the user

> **⛔ Behavioral Constraints During Polling (MUST OBEY):**
>
> During polling while waiting for diagnosis results, the following actions are **STRICTLY FORBIDDEN (both executing and suggesting to the user)**:
> 1. **FORBIDDEN** to execute kubectl commands on the cluster
> 2. **FORBIDDEN** to call ECS monitoring, CloudMonitor, or other APIs
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
> **FORBIDDEN to add any "alternative diagnosis method" suggestions in the timeout output.**

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

### Output Format

Present the diagnosis results in a structured format:

```
## 🔍 SysOM ACK Pod Diagnosis Results

**Pod**: <namespace>/<pod_name>
**Cluster**: <cluster_id>
**Diagnosis Mode**: Real-time / Historical (<time_range>)
**Overall Status**: <overall_status>

### Root Cause
<root_cause_analysis>

### Issues Found
<issues_list>

### Recommendations
<suggestions>
```

---

## SysOM ACK Pod Diagnosis Capability Coverage

| Category | Diagnostic Content |
|----------|-------------------|
| CPU | Container CPU throttling, cgroup CPU quota analysis, CPU saturation |
| Memory | Container OOM analysis, memory cgroup limit detection, memory leak |
| IO | Container IO latency, disk throughput bottleneck |
| Network | Pod network jitter, packet loss, connection timeout |
| Scheduling | Pod scheduling delay, resource contention |
| Runtime | Container runtime issues, image pull failures |
| Health | Overall Pod health scoring |
