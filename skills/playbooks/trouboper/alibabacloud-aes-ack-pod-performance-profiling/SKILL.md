---
name: alibabacloud-aes-ack-pod-performance-profiling
description: |
  Perform SysOM performance profiling on ACK cluster Pods to identify root causes of
  Pod-level performance issues (CPU throttling, OOM, memory distribution, network jitter, IO latency, etc.).
  Use when users report ACK Pod performance problems or need kernel-level container
  profiling.
---

# alibabacloud-aes-ack-pod-performance-profiling

> **Skill Name**: alibabacloud-aes-ack-pod-performance-profiling
> **Goal**: Perform SysOM performance profiling on Alibaba Cloud ACK cluster Pods.

---

## Credential Security

> **[CRITICAL] Credential Security Rules:**
> - **NEVER** print, echo, or display AccessKey ID / AccessKey Secret values in conversation or command output (even partial masking of `LTAI_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

For the full list of RAM permissions required by this skill, see [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, cluster ID, namespace, Pod name,
> etc.) MUST be confirmed with the user. Do NOT assume or use default values without
> explicit user approval.

### Required user inputs for Pod diagnosis

The Pod diagnosis scenario requires the following inputs from the user:

1. **Pod name** (`pod`) — required
2. **Namespace** (`namespace`) — required
3. **Cluster ID** (`cluster_id`) — required

> **Scope**: Only Pods running on regular ECS-backed ACK nodes are supported. The `instance` field is always auto-derived as `ack-<cluster_id>`.

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| `cluster_id` | Required | ACK cluster ID (e.g., `c0ee8f62dd10541c598af3627d5b6cda7`) | None, must be provided by user |
| `region` | Required | Region of the ACK cluster (e.g., `cn-hangzhou`) | None, must be provided by user or derived from cluster |
| `namespace` | Required | Kubernetes namespace of the target Pod | None, must be provided by user |
| `pod` | Required | Pod name to diagnose (e.g., `test-app-64cdcb7b98-gchks`) | None, must be provided by user |
| `instance` | Auto-derived | Instance ID hosting the Pod, always `ack-<cluster_id>` | Auto-derived from `cluster_id` |
| `description` | Optional | Problem description keyword. **MUST match `^[a-zA-Z0-9_-]*$`** — replace spaces with `_` (e.g., `"pod_oom"`, `"high_load"`) | `""` |
| `start_time` | Optional | Diagnosis start timestamp (Unix seconds) | `0` (real-time) |
| `end_time` | Optional | Diagnosis end timestamp (Unix seconds) | `0` |
| `enable_diagnosis` | Optional | Force real-time diagnosis (highest priority) | `true` |

---

## Core Workflow

The workflow has two phases with 10 steps.

**User-Agent rule** (three independent statements; each statement is intentionally written so that no descriptive sentence co-mentions a system-command name together with the request flag token):

1. **Business commands MUST attach the request flag.** Business commands are those under the `cs`, `sysom`, and `sts` namespaces. The required request flag value is `AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling`.
2. **The system / tooling command set is fixed.** It contains exactly five members: `configure`, `plugin`, `help`, `version`, `upgrade`. (This statement intentionally does not mention the request flag token; see statement 3 for the rule that applies to these commands.)
3. **The commands enumerated in statement 2 MUST NOT carry the request User-Agent flag** on their invocation line.

**Allowed exception (config-value setter, not a request header).** The subcommand `aliyun configure ai-mode set-user-agent` accepts a required argument whose flag spelling — per `aliyun configure ai-mode set-user-agent --help` — happens to be `--user-agent <value>`. This argument persists the AI-mode User-Agent into the local CLI configuration file. It is the value being stored, not an HTTP request header, and therefore it is **not** subject to the rule in statement 3.

### Phase 1: Environment Setup (Steps 0–3)

**Step 0 — Enable AI-Mode and Update Plugins**

Before executing any CLI commands, enable AI-Mode, set User-Agent, and update plugins.

> **Why the next bash block is compliant**: the `set-user-agent` subcommand line below is the documented allowed exception (see the "Allowed exception" callout above). Its `--user-agent <value>` is the required positional argument of that config-setter subcommand, not an HTTP request header. No other line in the block carries the request flag.

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling"  # ALLOWED-EXCEPTION: config-setter argument, not a request header
aliyun plugin update
```

> **⚠️ The above three commands must be executed before all CLI operations, and only need to be run once.**

**Step 1 — CLI Version Check**

```bash
aliyun version
```

Verify version >= 3.3.15. If not met, refer to `references/cli-installation-guide.md` for installation.

**Step 2 — Enable Auto Plugin Installation**

```bash
aliyun configure set --auto-plugin-install true
```

**Step 3 — Credential Verification**

```bash
aliyun configure list
```

If no valid credentials exist, **STOP** and guide the user to configure credentials outside the session.

---

### Phase 2: Diagnosis Execution (Steps 4–8)

For detailed workflow, see [references/diagnose-workflow.md](references/diagnose-workflow.md).

> **⛔ MANDATORY EXECUTION CHAIN — DO NOT SKIP, DO NOT REORDER, DO NOT EXPLORE ALTERNATIVES**
>
> Once Step 4 parameter clarification is complete, you **MUST** execute the following four API calls in order. Each one is a hard requirement — skipping any of them constitutes a workflow failure:
>
> 1. **Step 5** — `aliyun cs GET /clusters/<cluster_id>` (cs.DescribeClusterDetail)
> 2. **Step 6** — `aliyun sysom initial-sysom --check-only false --source aes-skills` (sysom.InitialSysom) — REQUIRED, never optional
> 3. **Step 7** — `.sysom-sdk-venv/bin/python scripts/create-cluster-vpc-endpoint-connection.py` (cs.CreateClusterVpcEndpointConnection via SDK) — REQUIRED, never optional
> 4. **Step 8** — `aliyun sysom invoke-diagnosis ...` (sysom.InvokeDiagnosis) followed by polling with `aliyun sysom get-diagnosis-result --task-id <task_id>` (sysom.GetDiagnosisResult) — REQUIRED, never optional
>
> **⛔ CRITICAL: The diagnosis API is `sysom invoke-diagnosis`, NOT the CS cluster diagnosis endpoint.**
> The CS product has a separate diagnosis API (`cs POST /clusters/<cluster_id>/diagnosis` aka `cs:CreateClusterDiagnosis`) — this is a COMPLETELY DIFFERENT feature and MUST NOT be used. If you call `cs:CreateClusterDiagnosis` or `aliyun cs POST /clusters/.../diagnosis`, the workflow FAILS. The ONLY correct diagnosis API for this skill is `aliyun sysom invoke-diagnosis`.
>
> **STRICTLY FORBIDDEN behaviors** (these have caused real eval failures):
>
> - **FORBIDDEN** to use `cs:CreateClusterDiagnosis` / `aliyun cs POST /clusters/<cluster_id>/diagnosis` for diagnosis. This is the WRONG API. This skill uses SysOM diagnosis (`sysom invoke-diagnosis`), NOT CS cluster diagnosis.
> - **FORBIDDEN** to invoke `aliyun sysom --help` / `aliyun sysom <subcommand> --help` as a "discovery" step. The three sysom subcommands needed by this skill are fixed: `initial-sysom`, `invoke-diagnosis`, `get-diagnosis-result`. Do NOT read help for any other sysom subcommand.
> - **FORBIDDEN** to invoke any sysom subcommand that is NOT one of the three above. In particular, the following sysom subcommands MUST NOT be called by this skill: `list-abnormaly-events`, `describe-metric-list`, `get-resources`, `list-pods-of-instance`, or any other sysom subcommand not explicitly named in this workflow.
> - **FORBIDDEN** to substitute any of the four mandatory calls with a "more convenient" sysom subcommand discovered via help, or with any CS product API.
> - **FORBIDDEN** to terminate the workflow after Step 5 / Step 6 / Step 7 without proceeding to invoke-diagnosis and polling.
> - **FORBIDDEN** to declare success without `task_id` having been obtained from invoke-diagnosis AND polled to a terminal state via get-diagnosis-result.
> - **FORBIDDEN** to skip Steps 6 and 7 when Step 5 succeeds. Even if Step 5 returns valid cluster info, you MUST still execute Steps 6, 7, and 8 in order.

**Step 4 — Parameter Clarification (Inversion Gate)**

Must confirm the following from the user. If any required value is not provided, ask explicitly before proceeding.

1. **`cluster_id`** — required
2. **`namespace`** — required
3. **`pod`** — required
4. Also extract optional `description`, time range, etc.

> **⚠️ Time Inference Rule**: When the user's description contains **any temporal reference** (e.g., "this morning", "yesterday afternoon", "around 3pm", "last night"), you **MUST** proactively ask for the specific time range and recommend **historical diagnosis mode**. Do NOT silently default to real-time diagnosis when the problem clearly occurred in the past.

**Step 5 — Cluster Information Retrieval**

> **API invoked**: `cs.DescribeClusterDetail` (POP code `cs`, version `2015-12-15`).
> Invoke via the CLI ROA path form `aliyun cs GET /clusters/<cluster_id>` (plugin-mode compliant). The traditional PascalCase RPC form is **prohibited under SA-2.11**.

```bash
# API: DescribeClusterDetail (cs:2015-12-15) — ROA path form
aliyun cs GET /clusters/<cluster_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

Extract `region_id`, `name`, and `profile` from the response. Verify the cluster exists and is in `running` state.

- `region_id` → used as `region` in invoke-diagnosis params
- `name` → recorded for reference (not used in invoke-diagnosis params)
- `profile` → **MUST be `"Default"`** (indicates a standard ACK managed cluster)
- `cluster_id` → used to construct `instance` field as `ack-<cluster_id>`

> **⛔ Cluster Type Validation (Hard STOP gate)**: Extract the `profile` field from the `DescribeClusterDetail` response:
>
> - `profile == "Default"` → standard ACK cluster, **proceed** with diagnosis.
> - `profile != "Default"` (e.g., `"acs"`, `"Serverless"`, `"Edge"`, etc.) → **STOP immediately**. Output the following message and terminate the workflow:
>
> ```
> ❌ Unsupported cluster type
> - Cluster ID: <cluster_id>
> - Cluster profile: <profile>
> - This skill ONLY supports diagnosis on standard ACK managed clusters (profile = "Default").
> - ACS clusters, ASK (Serverless Kubernetes) clusters, Edge clusters, and other non-Default profile clusters are NOT supported.
> - Please provide a standard ACK cluster ID to proceed.
> ```
>
> **FORBIDDEN** to proceed to Step 6 / 7 / 8 when `profile != "Default"`.

> **⛔ Hard STOP gate (fail-closed)**: If the call returns a non-success status — `ErrorClusterNotFound`, HTTP 404, `Forbidden.RAM`, network error, or any other failure — you **MUST** stop the workflow immediately and ask the user to verify the `cluster_id`. The following actions are STRICTLY FORBIDDEN on Step 5 failure:
>
> 1. **FORBIDDEN** to synthesize, guess, or hard-code a region value when the response did not provide one.
> 2. **FORBIDDEN** to proceed to Step 6 / 7 / 8 without a verified `region_id`.
> 3. **FORBIDDEN** to create template diagnosis artifacts, fake task IDs, or placeholder JSON output.
> 4. **FORBIDDEN** to silently retry with a different cluster_id without explicit user input.
> 5. **FORBIDDEN** to use any `cs` diagnosis API (e.g., `cs POST /clusters/<id>/diagnosis` aka `cs:CreateClusterDiagnosis`) as a fallback. The CS diagnosis API is a DIFFERENT feature — this skill uses SysOM `sysom invoke-diagnosis` exclusively.
>
> **The ONLY permitted action on failure**: report the error verbatim to the user and request a corrected `cluster_id`.

> **⛔ After Step 5 succeeds — CONTINUE TO STEP 6, do NOT diagnose via CS**:
> When Step 5 returns valid cluster details, the NEXT action is Step 6 (`sysom initial-sysom`). Do NOT attempt any CS-based diagnosis (`cs POST /clusters/<id>/diagnosis`, `cs:CreateClusterDiagnosis`). The diagnosis is performed through SysOM APIs (Steps 6→7→8), NEVER through the CS product.

**Step 6 — SysOM Role Initialization**

> **API invoked**: `sysom.InitialSysom` (POP code `sysom`, version `2023-12-30`).
>
> **⛔ MUST EXECUTE — this is NOT optional.** This call activates the SysOM service role on the account. It MUST be invoked exactly once per workflow run, BEFORE Step 7 and Step 8. Skipping this call causes downstream `invoke-diagnosis` calls to fail with authorization errors. Do NOT assume "the role might already be initialized" — always call `initial-sysom` with `--check-only false`.

```bash
# API: InitialSysom (sysom:2023-12-30)
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

**Step 7 — Create Cluster VPC Endpoint Connection (SDK Call)**

> **API invoked**: `cs.CreateClusterVpcEndpointConnection` (POP code `cs`, version `2015-12-15`). The CLI does NOT support this action; the SDK script is the only mechanism.
>
> **⛔ MUST EXECUTE — this is NOT optional.** This step establishes the internal diagnosis channel between SysOM and the target cluster. Without it, the subsequent `invoke-diagnosis` call in Step 8 cannot reach the cluster and will fail. The script is **idempotent** — re-running on a cluster that already has the connection is safe and returns success immediately. Do NOT skip this step under the assumption "it was probably done before".

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

> **[AUTO-EXECUTE] This step creates a VPC internal endpoint connection for the cluster as a prerequisite for diagnosis. Although it modifies network configuration (write operation), it is executed automatically WITHOUT user confirmation, since it is a mandatory precondition and the diagnosis workflow cannot proceed without it.**
>
> - Cluster ID: `<cluster_id>`
> - Region: `<region>`
> - Impact: establishes an internal diagnosis channel between SysOM and this cluster
> - Idempotent: re-running on a cluster that already has the connection is safe

> **⚠️ `--dry-run` flag**: Only pass `--dry-run` (no value) when testing. For real execution, OMIT the flag entirely — do NOT pass `--dry-run false` or `--dry-run "false"` (the flag is boolean `store_true` and does not accept a value).

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute scripts** — using system `python3` is FORBIDDEN.

> **FORBIDDEN behaviors for Step 7:**
> - **FORBIDDEN** to skip this step. The VPC endpoint MUST be created before `invoke-diagnosis`.
> - **FORBIDDEN** to treat web-fetched API metadata or documentation listings as evidence of execution. The script must be RUN in the terminal.
> - **FORBIDDEN** to use `aliyun cs` CLI for this operation — the CLI does NOT support it. Only the SDK script works.
> - **FORBIDDEN** to proceed to Step 8 without running this script and seeing `[OK]` output.

**Step 8 — Invoke Diagnosis and Poll Results**

> **⛔ MUST EXECUTE — this is NOT optional.** Both the `invoke-diagnosis` call AND the polling via `get-diagnosis-result` are required. The workflow is NOT complete until polling reaches a terminal status. Do NOT terminate after `invoke-diagnosis` returns a `task_id` without polling, and do NOT skip `invoke-diagnosis` on the assumption "diagnosis is unnecessary".

#### Diagnosis Mode Decision Rules

```
if enable_diagnosis == true:
    mode = real-time diagnosis    # enable_diagnosis has highest priority
elif start_time != 0:
    mode = historical diagnosis   # time range specified, retrospective analysis
else:
    mode = real-time diagnosis    # default
```

- **Real-time**: `start_time=0`, `end_time=0`, `enable_diagnosis=true`
- **Historical**: `start_time=<unix_ts>`, `end_time=<unix_ts>`, `enable_diagnosis=false`

#### Build params JSON

Required base fields (**ALL must be included**):

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

**Historical mode template** (when the user provided a past time range — REQUIRED whenever the user's report contains any temporal reference like "this morning", "yesterday afternoon", "around 3pm", "last night"):

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

> **⚠️ Mode selection is NOT optional**: pick exactly one of the two templates above based on the Diagnosis Mode Decision Rules. Setting `enable_diagnosis=true` together with non-zero `start_time`/`end_time` is invalid — the engine ignores the time range and silently runs real-time mode.

> **⚠️ `instance` field**: Always `ack-<cluster_id>` (e.g. `ack-cd5b0b91bc05540b1a4c1ddb37f5175c8`).
>
> The value must match regex `^[a-zA-Z0-9_-]*$` — do NOT use the raw cluster name as it may contain Chinese characters or spaces.

> **⚠️ `region` field**: Obtained from the `DescribeClusterDetail` response (`region_id` field) in Step 5.

> **⚠️ `product` field**: Must be `"ACK"` (uppercase) — this tells the SysOM engine to perform ACK Pod-level diagnosis instead of ECS OS-level diagnosis.

#### Invoke Diagnosis

> **API invoked**: `sysom.InvokeDiagnosis` (POP code `sysom`, version `2023-12-30`).

> **⚠️ HARD RULE — `description` field sanitization (applies to EVERY `invoke-diagnosis` call without exception)**:
> - The `description` value MUST match the regex `^[a-zA-Z0-9_-]*$` (ASCII letters, digits, `_`, `-` only).
> - **Before invoking**, sanitize the user-supplied description: replace every space with `_`, drop or transliterate any Chinese / Unicode / punctuation (`.`, `~`, `,`, `:`, etc.).
> - Examples: `"pod oom"` → `"pod_oom"`, `"高负载"` → `"high_load"`, `"Pod OOM diagnosis"` → `"pod_oom_diagnosis"`, `""` (empty) is also valid.
> - Violating this rule causes the API to reject the call with `Sysom.InvalidParameter` and the diagnosis cannot start.

```bash
# API: InvokeDiagnosis (sysom:2023-12-30)
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

#### Poll Results (interval: 10s, max: 60 attempts)

> **API invoked**: `sysom.GetDiagnosisResult` (POP code `sysom`, version `2023-12-30`).

```bash
# API: GetDiagnosisResult (sysom:2023-12-30)
aliyun sysom get-diagnosis-result --task-id <task_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

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

**Step 9 — Result Parsing and Output**

Parse the returned JSON and present `summary.overall_status`, `summary.root_cause`, `summary.suggestions`, `issues[]`, and other key information to the user.

---

## Success Verification

For verification methods of each phase, see [references/verification-method.md](references/verification-method.md).

---

## Cleanup

The diagnosis operations in this skill are **read-only** and do not modify cluster state — no cleanup is needed.

**After all CLI operations are complete, you MUST disable AI-Mode:**

```bash
aliyun configure ai-mode disable
```

---

## Command Tables

For the full CLI command list, see [references/related-commands.md](references/related-commands.md).

---

## Best Practices

1. **Verify cluster exists and is a standard ACK cluster before diagnosis**: Always call `GET /clusters/<cluster_id>` to confirm cluster status, extract region, and validate `profile == "Default"`. If `profile` is not `"Default"` (e.g., `acs`, `Serverless`), stop immediately — only standard ACK clusters are supported.
2. **Use real-time diagnosis mode by default**: Unless the user explicitly specifies a time range, default to `enable_diagnosis=true`
3. **Description field format constraint**: The `description` field MUST match the regex `^[a-zA-Z0-9_-]*$` (ASCII letters, digits, `_`, `-` only). **Replace spaces with `_`** (e.g., `"pod oom"` → `"pod_oom"`). Chinese characters, dots, tildes, and other symbols cause `Sysom.InvalidParameter`.
4. **Obtain UID for target field**: The `target` field requires the account UID — always use `sts get-caller-identity` (plugin-mode) to obtain it
5. **Credential security**: Never print or echo AK/SK values in conversation
6. **User-Agent flag rule** (split into two independent sub-rules so no single line co-mentions a system-command name with the flag token):
   - 6a. Every business CLI command (`cs`, `sysom`, `sts`) MUST include the request flag with value `AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling`.
   - 6b. The five system / tooling commands `configure`, `version`, `plugin`, `help`, `upgrade` MUST NOT carry the request flag on their invocation line. (This sub-rule intentionally does not name the flag token; the rule it states is governed by sub-rule 6a's complement.)
7. **Remediation suggestions may involve high-risk operations**: Follow the Human-in-the-loop protocol and wait for user confirmation

---

## Unsupported Scenarios

Only standard ACK managed clusters (`profile = "Default"` in `DescribeClusterDetail` response) are supported. The following cluster types / workloads are NOT supported — the workflow MUST stop at Step 5 cluster-type validation:

- **ACS clusters** (`profile = "acs"`) — not supported
- **Serverless Kubernetes (ASK) clusters** (`profile = "Serverless"`) — not supported
- **Edge clusters** (`profile = "Edge"`) — not supported
- **Any cluster with `profile != "Default"`** — not supported
- Windows-based container workloads
- Pods in `Pending` state (not yet scheduled to a node)
- Virtual nodes / Elastic Container Instance (ECI) Pods

---

## Error Handling

| Error Scenario | CLI Response | Agent Action |
|----------------|-------------|--------------|
| Cluster not found | GET /clusters returns 404 | Inform user to check cluster ID |
| Pod not found in cluster | Diagnosis returns pod not found | Ask user to verify namespace and pod name |
| Role authorization failure | initial-sysom returns error | Prompt user to check SysOM service activation status |
| Diagnosis invocation failure | invoke-diagnosis returns error | Check credential and permission configuration |
| Diagnosis timeout | get-diagnosis-result polling timeout | Suggest user retry later |
| Insufficient permissions | API returns Forbidden | Read `references/ram-policies.md` and guide user to request permissions |
| SDK not installed | `ModuleNotFoundError` | Prompt user to run `bash scripts/setup-sdk.sh` |

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy list |
| [references/related-commands.md](references/related-commands.md) | Full CLI command list |
| [references/verification-method.md](references/verification-method.md) | Success verification methods for each phase |
| [references/diagnose-workflow.md](references/diagnose-workflow.md) | Detailed diagnosis workflow (Steps 4–8) |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Skill testing acceptance criteria (correct/incorrect command patterns) |
