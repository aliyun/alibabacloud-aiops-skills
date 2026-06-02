---
name: alibabacloud-aes-sysom-pai-diagnosis
description: |
  Perform SysOM deep diagnosis on Alibaba Cloud PAI products (EAS / DLC) to identify
  root causes of instance-level issues. Use when users report:
  - EAS instance anomalies, GPU OOM (out of memory), GPU memory out-of-bounds errors
  - Slow first-token latency, uneven request scheduling across model service instances
  - OOM (Out Of Memory), insufficient memory, processes being killed
  - Abnormally high system load, high IO latency, network jitter, packet loss
  - Instance crashes, unexpected restarts, kernel oops
  - DLC training job hangs, communication timeouts, per-step throughput degradation
  - Any issue related to EAS instance health, DLC job health, or underlying
    compute resource performance
---

# alibabacloud-aes-sysom-pai-diagnosis

> **Skill Name**: alibabacloud-aes-sysom-pai-diagnosis
> **Goal**: Perform SysOM deep diagnosis on Alibaba Cloud PAI products (EAS / DLC) to identify root causes of instance-level performance and health issues.

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
> ALL user-customizable parameters (e.g., RegionId, instance IDs, product type,
> time ranges, etc.) MUST be confirmed with the user. Do NOT assume or use default
> values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| `region` | Required | Region of the PAI resource (e.g., `cn-hangzhou`) | None, must be provided by user |
| `instance` | Required | PAI instance ID (EAS service ID `eas-m-xxx` or DLC job ID `dlcxxxxxxxx`) | None, must be provided by user |
| `product` | Required | PAI sub-product type, one of `EAS` or `DLC` | Auto-inferred from `instance` prefix (`eas-` → `EAS`, `dlc` → `DLC`); only ask user when inference fails |
| `start_time` | Optional | Diagnosis start timestamp (Unix seconds) | `0` (real-time) |
| `end_time` | Optional | Diagnosis end timestamp (Unix seconds) | `0` |
| `enable_diagnosis` | Optional | Force real-time diagnosis (highest priority) | `false` |
| `uid` | Optional | Account ID owning the resource | `None` |
| `ocd_description` | Optional | User's problem description in English, with words joined by underscores (`_`). No Chinese characters, no spaces. Example: `GPU_OOM_instance_restart` | `None` |

### Product Auto-Inference Rule

The `product` field MUST be present in the params JSON. The value is determined as follows:

1. If the user explicitly specifies `product` (`EAS` or `DLC`), use the user value
2. Otherwise, infer from the `instance` prefix:
   - `eas-` → `EAS`
   - `dlc` (no hyphen, e.g., `dlcxxxxxxxx`) → `DLC`
3. If inference is ambiguous or fails, you **MUST** explicitly ask the user to choose between `EAS` and `DLC`

---

## Core Workflow

The workflow has two phases with 8 steps. All `aliyun` CLI **business commands** (SysOM, EAS, DLC API calls) **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis`. System commands (`version`, `configure`, `plugin`) do NOT use `--user-agent`.

### Phase 1: Environment Setup (Steps 0–3)

**Step 0 — Enable AI-Mode and Update Plugins**

Before executing any CLI commands, enable AI-Mode, set User-Agent, and update plugins:

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis"
aliyun plugin update
```

> **⚠️ The above three commands must be executed before all CLI operations, and only need to be run once.**

**Step 1 — CLI Version Check**

```bash
aliyun version
```

Verify version >= 3.3.1. If not met, refer to `references/cli-installation-guide.md` for installation.

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

**Step 4 — Ambiguous Problem Clarification (Inversion Gate)**

Must confirm `region`, `instance`, and **when the anomaly occurred**. If not provided by the user, ask explicitly. `product` is auto-inferred from the `instance` prefix (`eas-` → `EAS`, `dlc` → `DLC`); only ask user when inference fails. Also extract optional time range.

> **⚠️ Time Inference Rule**: When the user's description contains **any temporal reference** (e.g., "this morning", "yesterday afternoon", "around 3pm", "last night"), you **MUST** proactively ask for the specific time range and recommend **historical diagnosis mode**. Do NOT silently default to real-time diagnosis when the problem clearly occurred in the past.

**Step 5 — SysOM Role Initialization**

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

**Step 6 — Resource Validation**

Before invoking diagnosis, you **MUST** validate the resource based on the inferred `product`:

#### 6A. EAS — Verify Service Exists

```bash
aliyun eas list-services \
  --region <region> \
  --filter <eas_service_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

From the returned `Services` array, verify that an entry with a matching `ServiceId` exists. If no match is found, inform the user that the service ID is invalid and stop the pipeline.

#### 6B. DLC — Verify Resource Type is Lingjun

```bash
aliyun pai-dlc get-job \
  --region <region> \
  --job-id <dlc_job_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

Check the `ResourceType` field in the response:
- `Lingjun` → proceed to Step 7
- Any other value → **STOP** and inform the user: "SysOM diagnosis currently only supports DLC jobs running on Lingjun resources. Your job uses `<ResourceType>`, which is not yet supported."

> **⚠️ The `instance` field in params JSON uses the original instance ID directly (`eas-m-xxx` or `dlcxxxxxxxx`) — this step is purely for validation.**

**Step 7 — Invoke Diagnosis and Poll Results**

#### Diagnosis Mode Decision Rules

```
if enable_diagnosis == true:
    mode = real-time diagnosis    # enable_diagnosis has highest priority
elif start_time != 0:
    mode = historical diagnosis   # time range specified, retrospective analysis
else:
    mode = real-time diagnosis    # default
```

- **Real-time**: `start_time=0`, `end_time=0`
- **Historical**: `start_time=<unix_ts>`, `end_time=<unix_ts>`
- **Forced real-time**: when `enable_diagnosis=true`, force `start_time` to 0 even if provided

#### Build params JSON

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
  "enable_sysom_link": false,
  "ocd_description": "<user_problem_description_in_english_with_underscores>"
}
```

> **⚠️ Anti-confusion Warning: `"type": "ocd"` and `"product": "<EAS|DLC>"` are BOTH REQUIRED fields inside the params JSON — do NOT omit either!**
>
> - `--service-name ocd` (CLI argument) → tells CLI which diagnosis service endpoint to call
> - `"type": "ocd"` (params JSON field) → tells the diagnosis engine which diagnosis type to execute internally
> - `"product": "EAS"` or `"product": "DLC"` (params JSON field) → tells the diagnosis engine which PAI sub-product to target
>
> All three are mandatory; do NOT omit any of them.

> **⚠️ The `instance` field uses the original instance ID directly — `eas-m-xxx` for EAS, `dlcxxxxxxxx` for DLC.** Do NOT convert to ServiceName or any other identifier.

Conditional fields (add only when non-empty):
- `uid`: account ID owning the resource (integer)
- `ocd_description`: user's problem description (string). **Format constraints**: must be in English, no Chinese characters, no spaces — use underscores (`_`) to join words. Example: `high_latency_first_token`, `GPU_OOM_killed`

#### Invoke Diagnosis

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"instance":"<eas_service_id_or_dlc_job_id>","region":"<region>","product":"<EAS|DLC>","start_time":<start_time>,"end_time":<end_time>,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

Extract `task_id` from the response.

> **⚠️ [CRITICAL] `Sysom.TaskInProgress` Error Handling:**
> If `invoke-diagnosis` returns a `Sysom.TaskInProgress` error, this means a diagnosis task is already running. You **MUST**:
> 1. Extract the existing `task_id` from the error message using string match (pattern: `ocd(<task_id>)` or similar identifier in the message body)
> 2. Immediately proceed to the polling flow with the extracted `task_id`
> 3. **NEVER** treat `TaskInProgress` as a fatal failure or abort the workflow

#### Poll Results (interval: 10s, max: 60 attempts)

```bash
aliyun sysom get-diagnosis-result --task-id <task_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

Check the `status` field in the response:
- `Ready` / `Running` → **MUST** continue polling at 10s intervals
- `Success` → diagnosis complete, proceed to Step 8
- `Fail` → diagnosis failed, inform the user

> **⛔ [CRITICAL] Mandatory Polling Rules (MUST OBEY — violations will produce incorrect results):**
>
> 1. **`Running` status is NORMAL** — it simply means the diagnosis engine is still working. You **MUST** continue polling every 10 seconds. `Running` is NOT an error and MUST NOT trigger early termination.
> 2. **NEVER abandon polling early** — do NOT stop polling before reaching `Success`, `Fail`, or the 60-attempt limit. Do NOT "give up" after a few `Running` responses.
> 3. **NEVER fall back to manual analysis** — if polling is ongoing or timed out, you MUST NOT attempt to manually diagnose the issue by analyzing `ListServices` output, instance metadata, or any other data source. The diagnosis report is the ONLY valid source of root cause information.
> 4. **NEVER fabricate diagnosis results** — if the task has not reached `Success` status, you MUST NOT output any `summary.overall_status`, `summary.root_cause`, or `summary.suggestions` values. These fields come exclusively from the completed diagnosis result.
> 5. **Timeout handling** — if still incomplete after 60 polling attempts, output ONLY this template and stop:
>    ```
>    ⏳ SysOM diagnosis task timed out
>    - Task ID: <task_id>
>    - Current status: <status>
>    - Suggestion: Please continue waiting for the diagnosis to complete.
>    ```
>    FORBIDDEN to add alternative suggestions, manual analysis, or fabricated conclusions in timeout output.

**Step 8 — Result Parsing and Output**

Parse the returned JSON and present `summary.overall_status`, `summary.root_cause`, `summary.suggestions`, `issues[]`, and other key information to the user.

---

## Success Verification

For verification methods of each phase, see [references/verification-method.md](references/verification-method.md).

---

## Cleanup

The diagnosis operations in this skill are **read-only** and do not modify the PAI service / job state — no cleanup is needed.

PAI EAS / DLC are **fully managed services** — there is no agent to install or uninstall.

**After all CLI operations are complete, you MUST disable AI-Mode:**

```bash
aliyun configure ai-mode disable
```

---

## Command Tables

For the full CLI command list, see [references/related-commands.md](references/related-commands.md).

---

## Best Practices

1. **Product auto-inferred silently**: `product` is determined from the `instance` prefix (`eas-` → `EAS`, `dlc` → `DLC`) — only ask user when the prefix is unrecognizable
2. **Resource validation is mandatory**: EAS calls `ListServices` to verify existence; DLC calls `GetJob` to verify existence AND check `ResourceType` is `Lingjun`
3. **Instance ID used directly in params**: Both EAS (`eas-m-xxx`) and DLC (`dlcxxxxxxxx`) instance IDs are passed as-is in the `instance` field — do NOT convert to ServiceName
4. **Use real-time diagnosis mode by default**: Unless the user explicitly specifies a time range, default to real-time diagnosis
5. **Credential security**: Never print or echo AK/SK values in conversation
6. **All business CLI commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis`** (system commands like `version`, `configure`, `plugin` do not use `--user-agent`)
7. **Remediation suggestions may involve high-risk operations**: Follow the Human-in-the-loop protocol and wait for user confirmation
8. **No enrollment / agent installation needed**: PAI EAS and DLC are managed services; SysOM accesses them through the platform side, not via instance-level agents

---

## Unsupported Scenarios

- Non-PAI products (use `alibabacloud-aes-sysom-os-diagnosis` for ECS instances)
- PAI products other than EAS and DLC (e.g., DSW, MaxCompute) — current skill scope is EAS / DLC only
- Pure configuration issues (e.g., model version mismatch, EAS routing config — no OS-level diagnosis needed)

---

## Error Handling

| Error Scenario | CLI Response | Agent Action |
|----------------|-------------|--------------|
| Invalid EAS ServiceId | `ListServices` returns empty | Inform user the service ID does not exist in the region, stop pipeline |
| Invalid DLC JobId | `GetJob` returns not found | Inform user the DLC job ID does not exist, stop pipeline |
| DLC ResourceType not Lingjun | `GetJob` returns non-Lingjun type | Inform user SysOM only supports Lingjun resources, stop pipeline |
| Unknown product / ambiguous prefix | Cannot infer from `instance` | Explicitly ask user to choose `EAS` or `DLC` |
| Role authorization failure | `initial-sysom` returns error | Prompt user to check SysOM service activation status |
| Diagnosis invocation failure | `invoke-diagnosis` returns error | Check credential, permission, and `product` field correctness |
| Diagnosis timeout | `get-diagnosis-result` polling timeout | Output timeout template, suggest user retry later |
| Insufficient permissions | API returns Forbidden | Read `references/ram-policies.md` and guide user to request permissions |

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy list |
| [references/related-commands.md](references/related-commands.md) | Full CLI command list |
| [references/verification-method.md](references/verification-method.md) | Success verification methods for each phase |
| [references/diagnose-workflow.md](references/diagnose-workflow.md) | Detailed diagnosis workflow (Steps 4–8) |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Test acceptance criteria |
