---
name: alibabacloud-aes-sysom-lingjun-diagnosis
description: |
  Perform SysOM deep OS-level diagnosis on Alibaba Cloud lingjun node to identify
  root causes of performance issues (CPU spikes, memory leaks, IO latency, etc.).
  Use when users report lingjun node performance problems, need kernel-level
  troubleshooting, or want to configure DingTalk alert notifications for SysOM
  diagnosis reports.
---
# alibabacloud-aes-sysom-lingjun-diagnosis

> **Skill Name**: alibabacloud-aes-sysom-lingjun-diagnosis
> **Goal**: Perform SysOM deep OS-level diagnosis on Alibaba Cloud lingjun node, with optional DingTalk alert configuration.
>
> **Not supported by this skill**: node enrollment / Agent installation (`aliyun sysom install-agent`). If the user asks for it, **state plainly that this skill does not support enrollment and stop** — do NOT substitute CloudMonitor (CMS/CMS2) or any other product's API.

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

## Observability
Every OpenAPI call made by this skill — whether through the `aliyun` CLI or the Python SDK — **MUST** carry a User-Agent that identifies both the skill and the current session, so that calls can be traced and audited.

### UA Template

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

Replace `{session-id}` with the session identifier generated for the current session. Example:

```bash
aliyun sysom get-diagnosis-result --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/3f9a1c2b4d5e6f708192a3b4c5d6e7f8
```

### session-id Generation Rule

| Item | Rule |
|------|------|
| Format | 32-character lowercase hexadecimal string, no hyphens (e.g., `3f9a1c2b4d5e6f708192a3b4c5d6e7f8`) |
| Generation timing | Generate **ONCE** at the start of the session (Step 0), before running any command |
| Reuse scope | The **same** value MUST be reused by every CLI OpenAPI command and every SDK script call throughout the session |
| Regeneration | **NEVER** regenerate mid-session — a new session gets a new value |
| Propagation to SDK | Pass the value to Python SDK scripts via the `SKILL_SESSION_ID` environment variable; the scripts build the same UA string from it |

Generate it with:

```bash
SKILL_SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
```

### Commands That MUST NOT Carry `--user-agent`

Local/system CLI commands do **not** issue OpenAPI requests and **MUST NOT** be given the `--user-agent` flag:

- `aliyun version`
- `aliyun configure list` / `aliyun configure set ...`
- `aliyun plugin update` / `aliyun plugin install ...`

> **⚠️ Adding `--user-agent` to these commands is incorrect and may cause the command to fail with an unknown-flag error.**

---

## RAM Policy

For the full list of RAM permissions required by this skill, see [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---
## Parameters

> **IMPORTANT: Do NOT interrogate the user about the diagnosis.** Once `region` and
> `instance_id` are known, start the diagnosis directly — do **NOT** ask the user to
> confirm parameters, diagnosis mode, or the workflow before running it.
>
> - **Only** `region` and `instance_id` are blocking: if either is missing from the request, ask for it explicitly (one question, no extra confirmation round)
> - All optional parameters below are derived from the user's description; never invent an `instance_id` or a `region`
> - **[MUST] `region` and `instance_id` can come ONLY from the user.** It is **FORBIDDEN** to substitute any of the following for a missing `region`:
>   - the default region of the CLI profile (the `Region` column of `aliyun configure list`)
>   - the `ALIBABA_CLOUD_REGION_ID` / `REGION` environment variable
>   - a guess derived from the node ID (`e01-cn-...` identifies neither the region nor the zone)
>
>   A silently substituted region points the diagnosis at the wrong resource, so "ask the user, then wait" is the **only** permitted behavior — asking and continuing in the same turn with an assumed value does NOT count as asking.
> - Report the parameters actually used together with the diagnosis result, instead of asking for approval beforehand

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| `region` | Required | Region of the lingjun node (e.g., `cn-hangzhou`) | None, must be provided by user |
| `instance_id` | Required | lingjun node ID (e.g., `e01-cn-xxxxx`) | None, must be provided by user |
| `ocd_description` | Optional | Problem description (English only, e.g., `high_cpu`) | `""` |
| `start_time` | Optional | Diagnosis start timestamp (Unix seconds) | `0` (real-time) |
| `end_time` | Optional | Diagnosis end timestamp (Unix seconds) | `0` |
| `enable_diagnosis` | Optional | Force real-time diagnosis (highest priority) | `false` |
| `uid` | Optional | Account ID owning the instance | `None` |
| `skip_support_check` | Optional | Skip instance support check (speeds up workflow) | `false` |

---

## Core Workflow
The workflow has three phases with 13 steps (Step 0–12). All `aliyun` CLI commands that call OpenAPI **MUST** include the UA declared in the [Observability](#observability) section; local/system commands **MUST NOT**.

### Phase 1: Environment Setup (Steps 0–3)

**Step 0 — Initialize session-id and Update Plugins**
Before executing any CLI commands, generate the session-id for this session (see [Observability](#observability)) and update plugins:

```bash
SKILL_SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
aliyun plugin update
```

> **⚠️ The session-id must be generated once at the very beginning and reused unchanged for every OpenAPI call in this session (CLI `--user-agent` and SDK scripts alike).**

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

### Phase 2: Diagnosis Execution (Steps 4–9)

For detailed workflow, see [references/diagnose-workflow.md](references/diagnose-workflow.md).

**Step 4 — Parameter Collection (No Confirmation Round)**

`region` and `instance_id` are the only blocking inputs. The `instance_id` must be a **lingjun node ID** (`e01-cn-xxxxx`). If either is missing from the user's request, ask for it explicitly; once both are known, **go straight to Step 5 — do NOT ask the user to confirm the parameters or to approve starting the diagnosis**. Also extract optional `ocd_description` (must be translated to English) and the time range from the description.

> **⛔ Missing `region` is a hard stop, not a default-value problem.** When the user did not state a region:
> 1. Ask one explicit question (e.g. `Which region is this node in? For example cn-hangzhou / cn-beijing / cn-wulanchabu`) and **stop the turn there**
> 2. Do **NOT** run Step 5 / Step 7 / Step 8 with a region taken from the CLI profile default, from an environment variable, or guessed from the node ID — that is the same class of error as inventing an `instance_id`
> 3. Resume at Step 5 only after the user has supplied the region
>
> Telling the user afterwards which region you assumed does **not** repair this — the question must come first.

> **⚠️ Time Inference Rule**: When the user's description contains **any temporal reference** (e.g., "this morning", "yesterday afternoon", "around 3pm", "last night"), **infer the concrete time range yourself** and run **historical diagnosis mode** — do NOT stop to ask for it, and do NOT silently fall back to real-time diagnosis. State the inferred range together with the result.

**Step 5 — Cloud Assistant Online Check**

```bash
aliyun ecs describe-cloud-assistant-status --biz-region-id <region> --instance-id <instance_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

> **Note**: This check uses the ECS Cloud Assistant API — pass the **lingjun node ID** (`e01-cn-xxxxx`) as `--instance-id`.

Check the `CloudAssistantStatus` field in the response:

- `"true"` → Cloud Assistant is online, proceed to Step 6
- `"false"` → Cloud Assistant is offline, inform the user and terminate the pipeline
- **Call failed** (e.g. `403 Forbidden.RAM` on `ecs:DescribeCloudAssistantStatus`, `aliyun-cli-ecs` plugin unavailable, or any other error) → tell the user the Cloud Assistant pre-check was skipped, then **continue to Step 6**

> **⚠️ This is a non-fatal pre-check.** Only an explicit `"false"` terminates the pipeline. A failed call MUST NOT terminate it — the real capability gates are Step 7 (`check-instance-support`) and Step 8 (`invoke-diagnosis`), which will surface a Cloud Assistant problem on their own.

**Step 6 — SysOM Role Initialization**

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

**Step 7 — Instance Support Check**

```bash
aliyun sysom check-instance-support --instances <instance_id> --biz-region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

> When `skip_support_check` is `true`, skip this step entirely and go to Step 8.

Check the `support` field of the target node in the response:

- `true` → the node is ready for kernel-level diagnosis, proceed to Step 8
- `false` (e.g. reason `"instance not support in sysom"`) → the node is **not yet capable** of kernel-level diagnosis, which normally means the `sysom` agent has never been installed on it. This skill does **not** install agents, so:
  1. Tell the user that kernel-level diagnosis is currently unavailable for this node, quoting the reason returned by the API
  2. Tell them the node must first be onboarded to SysOM (Agent installation) in the SysOM console, and that **this skill does not perform enrollment**
  3. **Stop the pipeline there.** Do NOT call `install-agent`, and do NOT substitute CloudMonitor (CMS/CMS2) or any other product's API
  4. If the user explicitly asks to bypass this gate (`skip_support_check`), skip Step 7 and let Step 8 be the authoritative gate
- **Call failed** (e.g. `403 Forbidden.RAM`, plugin unavailable) → tell the user the support check could not be completed, then continue to Step 8 — Step 8 is the authoritative gate

> **⚠️ `support: false` MUST NOT be treated as "diagnosis is unnecessary".** Report it as a blocked diagnosis with the API reason, never as a clean result.

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

Conditional fields (add only when non-empty / when applicable):
- `ocd_description`: problem description in English (e.g., `high_cpu`)
- `uid`: account ID owning the instance (integer)

#### lingjun-Specific Required Values

| Item | Value | Note |
|------|-------|------|
| `--channel` | `eflo` | Fixed value for lingjun nodes |
| `product` in params | `"LINGJUN"` | **MUST** be included for lingjun nodes |

#### Invoke Diagnosis

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel eflo \
  --params '{"instance":"<instance_id>","region":"<region>","start_time":<start_time>,"end_time":<end_time>,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false,"product":"LINGJUN","ocd_description":"<ocd_description>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

> **⚠️ `--channel eflo` and `"product": "LINGJUN"` are both mandatory for lingjun nodes — omitting either will cause the diagnosis to fail or be routed to the wrong engine.**

Extract `task_id` from the response. If `Sysom.TaskInProgress` error is returned, extract the existing `task_id` from the error message and proceed to polling.

#### Poll Results (interval: 10s, max: 60 attempts)

```bash
aliyun sysom get-diagnosis-result --task-id <task_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

> **⛔ Polling MUST complete inside this turn (MUST OBEY):**
> Do the polling yourself, in this turn. It is **STRICTLY FORBIDDEN** to hand polling off to a background job / monitor / scheduled task and end your turn with "I will report once it finishes" — a deferred promise is not a result, and the user is left with no answer.
> Your turn may end in exactly one of three states: `Success` → the Step 9 report · `Fail` → the failure template · 60 attempts exhausted → the timeout template. **Never end a turn while the status is still `Ready` / `Running`.**

**Step 9 — Result Parsing and Output**

Parse the returned JSON and present the result using the **mandatory report layout** below — five sections, always in this order. Write it **in the same language the user used** (the Chinese section labels are given after the template; keep the field mapping identical).

| Section | Source field |
|---------|--------------|
| Overall status | `summary.overall_status` (`Info` / `Warn` / `Critical`) |
| Root cause | `summary.root_cause` |
| Issue list | `issues[]`, one line per item, prefixed `[Critical]` / `[Warn]` / `[Info]` |
| Suggested fix steps | `summary.suggestions`, numbered, ordered from immediate mitigation to long-term fix |
| Diagnosis mode | `diagnose_mode` (for historical mode, also state the `start_time`–`end_time` window used) |

<verbatim_output>

> ## 🔍 SysOM Diagnosis Report — `<instance_id>` (`<region>`)
>
> **Overall status**: `<summary.overall_status>`
>
> ### Root cause
> `<summary.root_cause>`
>
> ### Issue list
> - **[Critical]** `<issue title>` — `<measured values: IOPS / utilization / load / PID / path / kernel function>`
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

</verbatim_output>

> **⚠️ Output rules (all mandatory):**
> - Keep all five sections even when a section is empty — write `none` rather than dropping the heading
> - Every conclusion must carry the measured values returned by the API (IOPS, utilization, load, PID, file path, kernel function name); no vague wording
> - **Never fabricate a root cause.** On `Fail` or polling timeout, output the failure/timeout template instead (see [references/diagnose-workflow.md](references/diagnose-workflow.md)) — report only task_id, status and next step
> - `support: false` from Step 7 is also **not** a report: state the API reason and stop, per Step 7
> - Suggestions that involve high-risk operations (`kill`, service restart, file deletion) are presented as suggestions only — wait for the user's confirmation before executing anything

---

### Phase 3: Alert Configuration (Steps 10–12)

For detailed workflow, see [references/alert-workflow.md](references/alert-workflow.md).

> **⛔ Channel Constraint (applies to ALL of Phase 3, MUST OBEY):**
> Alerting in this skill goes **exclusively** through the SysOM channel — `aliyun sysom list-alert-items` plus the `scripts/create-alert-destination.py` / `scripts/create-alert-strategy.py` SDK scripts.
> It is **STRICTLY FORBIDDEN** to fulfill "monitor / configure alerts" by calling CloudMonitor (CMS / CMS2) or any other product's APIs — including but not limited to workspaces, integration policies, contacts (`PutContact`), and alert rules. A `403 Forbidden` on such a call means you took the wrong channel, **not** that permissions are missing; do NOT ask for CMS/CMS2 permissions.
> If a request falls outside what the SysOM channel supports here (node enrollment / Agent installation, cluster-wide or multi-node operations), **state that this skill does not support it and stop** — do NOT substitute another product's API.

**When to run Phase 3**

| User intent in the request | Behavior |
|---------------------------|----------|
| Asks for DingTalk alerts / an alert strategy (with or without a Webhook URL) | Run Steps 10–12 immediately after the diagnosis result — do **NOT** ask whether they want it |
| Says nothing about alerts | End after Step 9; do **NOT** turn alert configuration into a question |
| Explicitly declines monitoring / alerts (e.g. "no monitoring needed") | End after Step 9 with the mandatory closing statement below |

> **⚠️ Mandatory Closing Statement on Decline:** Whenever the user has stated they do not want monitoring / enrollment / alerts, your closing message **MUST** explicitly state, **in the same language the user used**, that no alert configuration was performed and that this was a one-time diagnosis.
>
> - Example: `As requested, monitoring and alert configuration are skipped — this was a one-time diagnosis.`
>
> This statement is required **regardless of the diagnosis outcome** — on `Fail` or polling timeout, append it after the failure/timeout template. It is the only text permitted in addition to those templates.
>
> **Do NOT** re-pitch alert configuration after the user has declined.

**Step 10 — Collect DingTalk Webhook and Create Alert Destination (SDK Call)**

The Webhook URL is the only input that cannot be inferred. If the user already supplied it, use it as-is and do **NOT** ask again; ask only when alerts are requested but no Webhook URL was given. This feature is **NOT supported by CLI** — use SDK scripts under `scripts/`.

<verbatim_output>
> 📲 Please provide the DingTalk group bot **Webhook URL** for receiving alert notifications.
> Format: `https://oapi.dingtalk.com/robot/send?access_token=xxx`
>
> 💡 How to get it: DingTalk Group Settings → Bot Management → Add Bot → Custom Bot → Optional keyword: alert → Copy Webhook URL

</verbatim_output>

With the Webhook in hand, initialize the SDK environment and create the alert destination:

```bash
# Initialize SDK environment (first time only, can skip afterwards)
bash scripts/setup-sdk.sh

# Create alert destination (stdout outputs destination_id)
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-destination.py '<user-provided-webhook-url>'
```

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute scripts** — using system `python3` is FORBIDDEN (signature algorithm depends on specific SDK version).
>
> **⚠️ You MUST inject `SKILL_SESSION_ID=<session-id>`** with the session-id generated in Step 0 — the script builds its SDK User-Agent from it (see [Observability](#observability)).

On success, stdout outputs `destination_id` (a pure number). Record this value for use in Step 12.

**Step 11 — Alert Item Selection**
```bash
aliyun sysom list-alert-items --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

Display the alert items list (categorized by NODE/POD), supporting quick selection (`all`, `node-all`, `pod-all`) and numbered selection. If the user already told you which items to enable (e.g. "all", "all NODE items"), apply that selection directly and go to Step 12 without asking again.

**Step 12 — Create Alert Strategy (SDK Call)**
Once the alert items are known, **create the alert strategy directly** with `destinations` set to the destination ID from Step 10.

> **⚠️ CLI does NOT support the `destinations` parameter — you MUST use the SDK script to create alert strategies.**

```bash
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
  --name "aliyun-aes-skills-create-<YYYYMMDDHHmm>" \
  --items "<alert_item_1>,<alert_item_2>" \
  --clusters "<clusters_value>" \
  --destinations "<destination_id>"
```

- `--clusters` → always `default`
- `--destinations` → destination ID from Step 10 (multiple IDs comma-separated, e.g., `1,2`)
- `--items` → alert item names comma-separated

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute scripts** — using system `python3` is FORBIDDEN.
>
> **⚠️ `SKILL_SESSION_ID` MUST be the same session-id used by all CLI commands in this session.**

---

## Success Verification

For verification methods of each phase, see [references/verification-method.md](references/verification-method.md).

---

## Cleanup

The diagnosis operations in this skill are **read-only** and do not modify instance state — no cleanup is needed. The only resources this skill can create are the alert destination and the alert strategy, both removable from the SysOM console.

---

## Command Tables

For the full CLI command list, see [references/related-commands.md](references/related-commands.md).

---

## Best Practices

1. **Check Cloud Assistant status before diagnosis**: SysOM diagnosis depends on Cloud Assistant being online on the lingjun node — always attempt the Step 5 check, but treat it as a non-fatal pre-check: only an explicit `"false"` terminates the pipeline, while a failed call just skips the pre-check and continues
2. **Use real-time diagnosis mode**: Unless the user's description points at a past time window, default to real-time diagnosis
3. **Use English keywords for ocd_description**: API only supports `[a-zA-Z0-9_.~-]` characters
4. **Do not interrogate the user**: never open a parameter-confirmation round before diagnosing — ask only for a missing `region` / `instance_id`, or for a Webhook URL when alerts were requested without one
5. **Diagnosis only — no enrollment**: node enrollment / Agent installation (`install-agent`, `list-instance-status`, `uninstall-agent`) is not part of this skill; if asked, say it is unsupported and stop
6. **clusters parameter for alert strategy**: Always `default`
7. **Alert destinations via SDK**: Alert destination APIs are not supported by CLI — must use Python SDK (`alibabacloud_sysom20231230`)
8. **destinations parameter for alert strategy**: After creating an alert destination, include `destinations` (destination ID list) in `create-alert-strategy` — alerts will be pushed to DingTalk via SysOM
9. **Credential security**: Never print or echo AK/SK values in conversation
10. **UA and session-id**: Every OpenAPI CLI command and SDK call must carry `AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}`, with one session-id generated per session and reused unchanged; local commands (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`) must not carry `--user-agent`
11. **Remediation suggestions may involve high-risk operations**: Follow the Human-in-the-loop protocol and wait for user confirmation
12. **lingjun-only skill**: `--channel` is always `eflo` and params must always include `"product": "LINGJUN"`

---

## Unsupported Scenarios

- Non-Linux lingjun nodes (Windows is not supported)
- lingjun nodes with incompatible kernel versions (checked via check-instance-support)
- Non-lingjun instances (e.g., ECS instances `i-xxx`) — this skill only handles lingjun nodes (`e01-cn-xxxxx`)
- **Node enrollment / SysOM Agent installation** (`install-agent`, `list-instance-status`, `uninstall-agent`) — say plainly it is not supported and stop; never emulate it through CloudMonitor or another product's API
- Pure configuration issues (e.g., security group rules, VPC routing — no OS-level diagnosis needed)

---

## Error Handling

| Error Scenario | CLI Response | Agent Action |
|----------------|-------------|--------------|
| lingjun node not supported by SysOM | check-instance-support returns `support: false` | Inform user of the reason returned by the API, state that the node must first be onboarded to SysOM in the console and that this skill does not perform enrollment, then stop. Never report it as a clean diagnosis |
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
| [references/alert-workflow.md](references/alert-workflow.md) | Detailed alert configuration workflow (Steps 10–12) |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Test acceptance criteria |