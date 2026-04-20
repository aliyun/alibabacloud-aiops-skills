---
name: alibabacloud-aes-sysom-os-diagnosis
description: |
  Perform SysOM deep OS-level diagnosis on Alibaba Cloud ECS instances to identify
  root causes of performance issues (CPU spikes, memory leaks, IO latency, etc.).
  Use when users report ECS instance performance problems, need kernel-level
  troubleshooting, or want to set up continuous automated diagnosis with instance
  enrollment and DingTalk alert notifications.
---

# alibabacloud-aes-sysom-os-diagnosis

> **Skill Name**: alibabacloud-aes-sysom-os-diagnosis
> **Goal**: Perform SysOM deep OS-level diagnosis on Alibaba Cloud ECS instances, with optional instance enrollment and DingTalk alert configuration.

---

## Credential Security

> **[CRITICAL] Credential Security Rules:**
> - **NEVER** print, echo, or display AccessKey ID / AccessKey Secret values in conversation or command output (even partial masking of `LTAI_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list --user-agent AlibabaCloud-Agent-Skills
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list --user-agent AlibabaCloud-Agent-Skills` shows a valid profile

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
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| `region` | Required | Region of the ECS instance (e.g., `cn-hangzhou`) | None, must be provided by user |
| `instance_id` | Required | ECS instance ID (e.g., `i-bp1xxxxxxxx`) | None, must be provided by user |
| `ocd_description` | Optional | Problem description (English only, e.g., `high_cpu`) | `""` |
| `start_time` | Optional | Diagnosis start timestamp (Unix seconds) | `0` (real-time) |
| `end_time` | Optional | Diagnosis end timestamp (Unix seconds) | `0` |
| `enable_diagnosis` | Optional | Force real-time diagnosis (highest priority) | `false` |
| `uid` | Optional | Account ID owning the instance | `None` |
| `skip_support_check` | Optional | Skip instance support check (speeds up workflow) | `false` |
| `cluster_id` | Optional | ACK cluster ID (required for cluster enrollment) | None |

---

## Core Workflow

The workflow has four phases with 14 steps. All `aliyun` CLI commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills`.

### Phase 1: Environment Setup (Steps 0–3)

**Step 0 — Enable AI-Mode and Update Plugins**

Before executing any CLI commands, enable AI-Mode, set User-Agent, and update plugins:

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-os-diagnosis"
aliyun plugin update
```

> **⚠️ The above three commands must be executed before all CLI operations, and only need to be run once.**

**Step 1 — CLI Version Check**

```bash
aliyun version --user-agent AlibabaCloud-Agent-Skills
```

Verify version >= 3.3.1. If not met, refer to `references/cli-installation-guide.md` for installation.

**Step 2 — Enable Auto Plugin Installation**

```bash
aliyun configure set --auto-plugin-install true --user-agent AlibabaCloud-Agent-Skills
```

**Step 3 — Credential Verification**

```bash
aliyun configure list --user-agent AlibabaCloud-Agent-Skills
```

If no valid credentials exist, **STOP** and guide the user to configure credentials outside the session.

---

### Phase 2: Diagnosis Execution (Steps 4–9)

For detailed workflow, see [references/diagnose-workflow.md](references/diagnose-workflow.md).

**Step 4 — Ambiguous Problem Clarification (Inversion Gate)**

Must confirm `region` and `instance_id`. If not provided by the user, ask explicitly. Also extract optional `ocd_description` (must be translated to English), time range, etc.

> **⚠️ Time Inference Rule**: When the user's description contains **any temporal reference** (e.g., "this morning", "yesterday afternoon", "around 3pm", "last night"), you **MUST** proactively ask for the specific time range and recommend **historical diagnosis mode**. Do NOT silently default to real-time diagnosis when the problem clearly occurred in the past.

**Step 5 — Cloud Assistant Online Check**

```bash
aliyun ecs describe-cloud-assistant-status --biz-region-id <region> --instance-id <instance_id> --user-agent AlibabaCloud-Agent-Skills
```

Check if `CloudAssistantStatus` is `true` in the response. If offline, terminate the pipeline.

**Step 6 — SysOM Role Initialization**

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills
```

**Step 7 — Instance Support Check**

```bash
aliyun sysom check-instance-support --instances <instance_id> --biz-region <region> --user-agent AlibabaCloud-Agent-Skills
```

**Step 8 — Invoke Diagnosis and Poll Results**

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

Conditional fields (add only when non-empty):
- `ocd_description`: problem description in English (e.g., `high_cpu`)
- `uid`: account ID owning the instance (integer)

#### Invoke Diagnosis

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"instance":"<instance_id>","region":"<region>","start_time":<start_time>,"end_time":<end_time>,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false,"ocd_description":"<ocd_description>"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

Extract `task_id` from the response. If `Sysom.TaskInProgress` error is returned, extract the existing `task_id` from the error message and proceed to polling.

#### Poll Results (interval: 10s, max: 60 attempts)

```bash
aliyun sysom get-diagnosis-result --task-id <task_id> --user-agent AlibabaCloud-Agent-Skills
```

**Step 9 — Result Parsing and Output**

Parse the returned JSON and present `summary.overall_status`, `summary.root_cause`, `summary.suggestions`, `issues[]`, and other key information to the user.

---

### Phase 3: Enrollment Recommendation (Steps 10–12)

For detailed workflow, see [references/manage-and-alert-workflow.md](references/manage-and-alert-workflow.md).

**Step 10 — Enrollment Recommendation and Intent Collection (Inversion Double Gate)**

This step contains two strictly separated gates that **MUST be executed in order — merging, skipping, or simplifying is FORBIDDEN**.

**10A — Prominent Enrollment Recommendation (First Gate)**

**⚠️ Mandatory Rule: After presenting diagnosis results, you MUST immediately output the following recommendation content verbatim. Do NOT abbreviate, omit, or rephrase in your own words.**

Replace `<instance_id>` with the actual instance ID, then output the following content **word-for-word**:

<verbatim_output>

> ## 🔔 Recommendation: Enroll Instance for 24/7 Automated Diagnosis
>
> The diagnosis just performed was a one-time manual operation. If you want SysOM to **continuously protect** this instance, we recommend **instance enrollment**.
>
> ### After enrollment, you will get:
>
> - 🔍 **Automated Diagnosis**: When the instance experiences performance issues like CPU spikes, memory leaks, or IO latency, SysOM will **automatically trigger deep diagnosis** without manual intervention
> - 📲 **DingTalk Alerts**: Diagnosis reports will be **automatically pushed to DingTalk group bots**, notifying the ops team immediately
> - 🛡️ **Continuous Monitoring**: 24/7 uninterrupted protection, shifting from "investigate after problems occur" to "automatically told the root cause when problems occur"
>
> **Would you like to enroll instance `<instance_id>`?**

</verbatim_output>

**After outputting the above, STOP. Wait for user reply. Do NOT ask about enrollment method in 10A.**

- User **declines** → end the pipeline
- User **agrees** → proceed to Step 10B

**10B — Ask Enrollment Method (Second Gate)**

Only after the user explicitly agrees in 10A, output the following (replace `<instance_id>` and `<region>` with actual values):

<verbatim_output>

> ### Please choose an enrollment method
>
> **A. Enroll current instance only**
> Only enroll the instance just diagnosed: `<instance_id>` (`<region>`)
>
> **B. Enroll ACK cluster**
> If this instance belongs to an ACK cluster, you can enroll **all nodes** in the cluster with one click.
> Newly added nodes will be automatically enrolled — no manual action needed.
> 👉 Please provide the **ACK Cluster ID** (e.g., `c9d7f3fc3d42********c1100ffb19d`)
>
> **C. Enroll multiple specified instances**
> Batch enroll multiple instances.
> 👉 Please provide the instance list in the format `InstanceID:Region`, separated by spaces
> Example: `i-xxx:cn-beijing i-yyy:cn-hangzhou`
>
> Please choose A / B / C, or tell me your requirements directly.

</verbatim_output>

**After outputting the above, STOP. Wait for user reply.**

**Step 11 — Execute Enrollment**

> **Fixed parameter values for `--agent-id`, `--agent-version`, `--config-id` in enrollment commands are listed in the "Fixed Parameters" table in [references/related-commands.md](references/related-commands.md).**

```bash
# Instance mode
aliyun sysom install-agent \
  --instances instance=<instance_id> region=<region> \
  --install-type InstallAndUpgrade \
  --agent-id <agent-id> \
  --agent-version <agent-version> \
  --user-agent AlibabaCloud-Agent-Skills

# Cluster mode
aliyun sysom install-agent-for-cluster \
  --cluster-id <cluster_id> \
  --agent-id <agent-id> \
  --agent-version <agent-version> \
  --config-id <config-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Step 12 — Enrollment Status Confirmation**

```bash
# Instance mode — poll instance status (interval: 10s, max: 60 attempts)
aliyun sysom list-instance-status --instance <instance_id> --biz-region <region> --user-agent AlibabaCloud-Agent-Skills

# Cluster mode — get full cluster list, then match target cluster by cluster_id
aliyun sysom list-clusters --user-agent AlibabaCloud-Agent-Skills
# From the returned cluster list, match the target cluster by cluster_id field and check its cluster_status
```

> **⚠️ Enrollment success criteria: status `Running` means enrollment is complete — stop polling immediately and proceed to the next step.**

---

### Phase 4: Alert Configuration (Steps 13–15)

For detailed workflow, see [references/manage-and-alert-workflow.md](references/manage-and-alert-workflow.md).

**Step 13 — Collect DingTalk Webhook and Create Alert Destination (Inversion Gate + SDK Call)**

After successful enrollment, you **MUST immediately collect the DingTalk bot Webhook URL** from the user to create an alert destination. This feature is **NOT supported by CLI** — use SDK scripts under `scripts/`.

Ask the user:

<verbatim_output>

> 📲 Please provide the DingTalk group bot **Webhook URL** for receiving alert notifications.
> Format: `https://oapi.dingtalk.com/robot/send?access_token=xxx`
>
> 💡 How to get it: DingTalk Group Settings → Bot Management → Add Bot → Custom Bot → Optional keyword: alert → Copy Webhook URL

</verbatim_output>

After the user provides the Webhook, initialize the SDK environment and create the alert destination:

```bash
# Initialize SDK environment (first time only, can skip afterwards)
bash scripts/setup-sdk.sh

# Create alert destination (stdout outputs destination_id)
.sysom-sdk-venv/bin/python scripts/create-alert-destination.py '<user-provided-webhook-url>'
```

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute scripts** — using system `python3` is FORBIDDEN (signature algorithm depends on specific SDK version).

On success, stdout outputs `destination_id` (a pure number). Record this value for use in Step 15.

**Step 14 — Alert Item Selection (Inversion Gate)**

```bash
aliyun sysom list-alert-items --user-agent AlibabaCloud-Agent-Skills
```

Display the alert items list (categorized by NODE/POD), supporting quick selection (`all`, `node-all`, `pod-all`) and numbered selection.

**Step 15 — Create Alert Strategy (SDK Call)**

After the user selects alert items, **create the alert strategy directly** with `destinations` set to the destination ID from Step 13.

> **⚠️ CLI does NOT support the `destinations` parameter — you MUST use the SDK script to create alert strategies.**

```bash
.sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
  --name "aliyun-aes-skills-create-<YYYYMMDDHHmm>" \
  --items "<alert_item_1>,<alert_item_2>" \
  --clusters "<clusters_value>" \
  --destinations "<destination_id>"
```

- Instance mode → `--clusters` value is `default`
- Cluster mode → `--clusters` value is `<cluster_name>` (note: name, NOT ID)
- `--destinations` → destination ID from Step 13 (multiple IDs comma-separated, e.g., `1,2`)
- `--items` → alert item names comma-separated

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute scripts** — using system `python3` is FORBIDDEN.

---

## Success Verification

For verification methods of each phase, see [references/verification-method.md](references/verification-method.md).

---

## Cleanup

The diagnosis operations in this skill are **read-only** and do not modify instance state — no cleanup is needed.

To uninstall an enrolled Agent, use `aliyun sysom uninstall-agent` (see [references/related-commands.md](references/related-commands.md) for parameters).

**After all CLI operations are complete, you MUST disable AI-Mode:**

```bash
aliyun configure ai-mode disable
```

---

## Command Tables

For the full CLI command list, see [references/related-commands.md](references/related-commands.md).

---

## Best Practices

1. **Check Cloud Assistant status before diagnosis**: SysOM diagnosis depends on Cloud Assistant being online — always confirm in Step 5
2. **Use real-time diagnosis mode**: Unless the user explicitly specifies a time range, default to real-time diagnosis
3. **Use English keywords for ocd_description**: API only supports `[a-zA-Z0-9_.~-]` characters
4. **Use double gate for enrollment recommendation**: Recommend first, then ask method — avoid information overload
5. **Cluster enrollment batch limit**: When exceeding 50 instances, the first batch installs only 50; the rest are installed automatically
6. **clusters parameter for alert strategy**: Use `default` for instance mode, use cluster **name** (not ID) for cluster mode
7. **Alert destinations via SDK**: Alert destination APIs are not supported by CLI — must use Python SDK (`alibabacloud_sysom20231230`)
8. **destinations parameter for alert strategy**: After creating an alert destination, include `destinations` (destination ID list) in `create-alert-strategy` — alerts will be pushed to DingTalk via SysOM
9. **Credential security**: Never print or echo AK/SK values in conversation
10. **All CLI commands must include `--user-agent AlibabaCloud-Agent-Skills`**
11. **Remediation suggestions may involve high-risk operations**: Follow the Human-in-the-loop protocol and wait for user confirmation

---

## Unsupported Scenarios

- Non-Linux instances (Windows instances are not supported)
- Instances with incompatible kernel versions (checked via check-instance-support)
- Pure configuration issues (e.g., security group rules, VPC routing — no OS-level diagnosis needed)

---

## Error Handling

| Error Scenario | CLI Response | Agent Action |
|----------------|-------------|--------------|
| Instance not supported by SysOM | check-instance-support returns unsupported | Inform user that kernel-level diagnosis is not supported, fall back to standard diagnosis |
| Role authorization failure | initial-sysom returns error | Prompt user to check SysOM service activation status |
| Diagnosis invocation failure | invoke-diagnosis returns error | Check credential and permission configuration |
| Diagnosis timeout | get-diagnosis-result polling timeout | Suggest user retry later |
| Insufficient permissions | API returns Forbidden | Read `references/ram-policies.md` and guide user to request permissions |
| SDK not installed | `ModuleNotFoundError: No module named 'alibabacloud_sysom20231230'` | Prompt user to run `pip install alibabacloud_sysom20231230` |
| Alert destination creation failure | SDK returns error | Check Webhook URL format and credential permissions |

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy list |
| [references/related-commands.md](references/related-commands.md) | Full CLI command list |
| [references/verification-method.md](references/verification-method.md) | Success verification methods for each phase |
| [references/diagnose-workflow.md](references/diagnose-workflow.md) | Detailed diagnosis workflow (Steps 4–9) |
| [references/manage-and-alert-workflow.md](references/manage-and-alert-workflow.md) | Detailed enrollment and alert workflow (Steps 10–15) |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Test acceptance criteria |
