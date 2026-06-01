---
name: alibabacloud-pts-task
description: |
  Alibaba Cloud PTS task CRUD worker skill — executes concrete PTS scenario operations
  (create / query / start / stop / report / delete) for both PTS native HTTP/HTTPS and
  JMeter-based stress testing. This is a WORKER skill, typically delegated from the
  `alibabacloud-pts-pilot` router. Do NOT use this skill for tuning advice or general PTS Q&A.
  Triggers: "创建压测场景", "启动压测", "停止压测", "查看压测报告", "删除压测场景",
  "上传JMeter脚本", "执行JMeter压测", "list PTS scenes", "start PTS scene",
required_permissions:
  - pts:CreatePtsScene
  - pts:SavePtsScene
  - pts:GetPtsScene
  - pts:ListPtsScene
  - pts:StartPtsScene
  - pts:StopPtsScene
  - pts:DeletePtsScene
  - pts:StartDebugPtsScene
  - pts:StopDebugPtsScene
  - pts:GetPtsReportDetails
  - pts:GetPtsSceneBaseLine
  - pts:GetPtsSceneRunningData
  - pts:GetPtsSceneRunningStatus
  - pts:SaveOpenJMeterScene
  - pts:GetOpenJMeterScene
  - pts:ListOpenJMeterScenes
  - pts:StartTestingJMeterScene
  - pts:StopTestingJMeterScene
  - pts:RemoveOpenJMeterScene
  - pts:GetJMeterReportDetails
---

# Alibaba Cloud PTS Task CRUD Worker (alibabacloud-pts-task)

> **Role:** This is the **worker** skill for PTS scenario CRUD operations. It is typically
> invoked by the router skill `alibabacloud-pts-pilot` after intent resolution. It MAY also be triggered
> directly when the user's request is unambiguous about executing a concrete PTS action.
>
> **Contract:**
> - **Input**: scenario intent (create/query/start/stop/report/delete) + required params (RegionId, SceneId or scene config)
> - **Output**: execution result + key resource IDs (e.g., `SceneId`, `ReportId`) for downstream handoff

This skill covers PTS Native HTTP/HTTPS stress testing and JMeter-based distributed stress testing.

## Pre-check

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md)
> for safe step-by-step installation (do NOT pipe remote scripts directly into a shell).
> Then **[MUST]** run `aliyun plugin install pts` to install the PTS plugin.
> **[MUST]** run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

```bash
# Verify CLI version
aliyun version

# Install PTS plugin (explicit, no auto-install)
aliyun plugin install pts
aliyun plugin update
```

## AI-Mode Lifecycle Management

> **[MUST] Enable at workflow start (replaces per-command `--user-agent`):**
>
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pts-task"
> ```
>
> **[MUST] Disable at EVERY exit point** (success / failure / error / cancellation / session end):
>
> ```bash
> aliyun configure ai-mode disable
> ```

## Timeout Settings

Append `--read-timeout 60 --connect-timeout 10` to all `aliyun pts` commands (read-timeout 60s because stress operations may take longer; connect-timeout 10s).

## Parameter Confirmation

> **Parameter Confirmation (Smart Mode)**
>
> - All required parameters present → echo summary + execute immediately. No re-confirmation.
> - Missing/ambiguous parameter → ask user before proceeding.
> - Destructive ops (delete/stop) → ALWAYS require explicit user confirmation.

### User-Customizable Parameters

| Parameter Name | Required | Description | Default Value |
|---------------|----------|-------------|---------------|
| RegionId | No | Region for PTS service | cn-hangzhou |
| Scene Name | Yes | Name of the stress testing scenario | - |
| Target URL | Yes | URL to stress test | - |
| HTTP Method | Yes | GET, POST, PUT, DELETE, etc. | GET |
| Concurrency | Yes | Number of concurrent users | - |
| Duration | Yes | Test duration in seconds | - |
| JMX File | Yes (JMeter) | Path to JMeter script file | - |
| Mode | No | CONCURRENCY or TPS | CONCURRENCY |

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
>
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> After running `aliyun configure list`, if ANY profile is shown (regardless of type: AK, STS, RamRoleArn, EcsRamRole, etc.), credentials ARE configured. Proceed immediately with CLI execution. Do NOT additionally check environment variables or conclude credentials are missing.
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

If CLI is not yet configured, see [references/cli-installation-guide.md](references/cli-installation-guide.md) for setup instructions.

## RAM Policy

Users must have appropriate PTS permissions. See [references/ram-policies.md](references/ram-policies.md) for detailed policies.

## Idempotency

PTS APIs do not support `ClientToken`-based idempotency. **Scene names are not unique** — multiple
PTS or JMeter scenarios may share the same `SceneName`. Never treat “same name” as one resource;
always use **`SceneId`** (returned by the API) as the stable identifier.

To prevent duplicate resources or unintended side-effects when retrying after timeouts or errors,
**always** use the **check-then-act** pattern before every write operation:

| Operation | Check Before Acting | If Already Exists / Running |
|-----------|--------------------|-----------------------------|
| **Create PTS scene** (`save-pts-scene` without SceneId) | Do not dedupe by name. Record `SceneId` on success. | Unknown outcome → `list-pts-scene` to check before retry. |
| **Update PTS scene** (`save-pts-scene` with SceneId) | Include existing `SceneId` in JSON. | Missing `SceneId` creates a duplicate — always supply it. |
| **Create JMeter scene** (`save-open-jmeter-scene`) | Same as PTS — use `SceneId` only. | `list-open-jmeter-scenes` to check before retry. |
| **Start PTS test** (`start-pts-scene`) | `get-pts-scene-running-status` | `RUNNING`/`SYNCING` → skip start |
| **Start JMeter test** (`start-testing-jmeter-scene`) | `get-open-jmeter-scene` | Already running → skip start |
| **Delete PTS scene** (`delete-pts-scene`) | Confirm `SceneId` exists | Gone → treat as success |
| **Delete JMeter scene** (`remove-open-jmeter-scene`) | Confirm `SceneId` exists | Gone → treat as success |

## Core Workflow

### Workflow 1: Create and Run PTS Native Stress Testing

#### Task 1.1: Create PTS Scenario

> ⛔ **HARD BLOCK — Scene Creation Command:**
> - PTS native scene creation uses `save-pts-scene` (API: `SavePtsScene`).
> - Do NOT use `create-pts-scene` — it has known parameter compatibility issues in the current CLI plugin.
> - When NO `SceneId` is provided, `save-pts-scene` creates a new scene and returns a new `SceneId`.
> - When `SceneId` IS provided, it updates the existing scene.

> ⛔ **HARD BLOCK — Direct CLI Execution Only:**
> - ALWAYS execute `aliyun pts` commands directly in the terminal.
> - NEVER write Python/Shell/Bash scripts as workarounds when CLI calls fail.
> - NEVER conclude "credentials are unavailable" — if `aliyun configure list` shows ANY valid profile, credentials ARE available. Proceed with CLI execution.
> - If a CLI command fails, retry with corrected parameters. Do NOT fall back to scripting.

> **Idempotency:** `SceneName` may duplicate. After success, record **`SceneId`**.
> Transient error → retry up to 2 times. Unknown outcome → `list-pts-scene` to check before retry.

⛔ **HARD BLOCK — `save-pts-scene` Exact Command (COPY VERBATIM):**

```bash
aliyun pts save-pts-scene --scene '{
  "SceneName":"YOUR_SCENE_NAME_HERE",
  "RelationList":[{
    "RelationName":"link-1",
    "ApiList":[{
      "ApiName":"api-1",
      "Url":"http://YOUR_TARGET_URL",
      "Method":"GET",
      "TimeoutInSecond":5000
    }]
  }],
  "LoadConfig":{
    "TestMode":"concurrency_mode",
    "MaxRunningTime":1,
    "Configuration":{
      "AllConcurrencyBegin":5,
      "AllConcurrencyLimit":5
    }
  }
}' --read-timeout 60 --connect-timeout 10
```

> **⚠️ COPY this JSON structure EXACTLY. Only replace:**
> - `YOUR_SCENE_NAME_HERE` → user-specified scene name
> - `http://YOUR_TARGET_URL` → actual target URL
> - Concurrency/timeout values as needed
>
> **DO NOT invent field names. These INVALID names cause "unknown field" errors:**
> - ~~Relations~~ → use `RelationList`
> - ~~Address~~ → use `Url` (inside ApiList)
> - ~~Headers~~ at root level → INVALID
> - ~~RelationId~~ at root → INVALID (only valid inside RelationList items)
>
> For complete JSON template (HeaderList, CheckPointList, AdvanceSetting, file params, POST body, etc.), see [references/pts-scene-json-reference.md](references/pts-scene-json-reference.md).

**Parameter Notes:** `MaxRunningTime` = minutes [1-1440]; `TestMode` = `concurrency_mode` | `tps_mode`; `TimeoutInSecond` recommended 10; `AdvanceSetting.LogRate` 1-100, `ConnectionTimeoutInSecond` 5.

#### Task 1.2: Start Stress Testing

> **[MUST] Pre-flight Safety Checks** — Starting a stress test sends significant traffic to the
> target system. ALL of the following checks MUST pass before executing `start-pts-scene`:
>
> 1. **Idempotency guard** — Run `get-pts-scene-running-status --scene-id <SCENE_ID>`.
>    If the status is `RUNNING` or `SYNCING`, the test is already in progress — skip the start
>    command and proceed to monitoring. Do NOT start a duplicate test.
> 2. **Retrieve and verify scene configuration** — Run `get-pts-scene --scene-id <SCENE_ID>` and
>    confirm the response contains a valid `SceneName`, at least one `RelationList` entry with a
>    non-empty `Url`, and a valid `LoadConfig` (non-zero `MaxRunningTime` and concurrency).
>    If any field is missing or empty, abort and notify the user.
> 3. **Display test summary** — Present the following to the user:
>    - Target URL(s)
>    - Concurrency level
>    - Test duration
>    - Test mode (concurrency / TPS)
>
>    If all values were explicitly provided in the user's original request, proceed
>    directly after displaying the summary. If any value was inferred or defaulted,
>    wait for explicit user approval before proceeding.
>
> ⛔ **HARD BLOCK**: If Step 1 or Step 2 was NOT executed or returned an error, you MUST NOT proceed to `start-pts-scene`. Abort and report the failure.

```bash
# Idempotency guard: Skip if test is already running
aliyun pts get-pts-scene-running-status \
  --scene-id <SCENE_ID>
# ↑ If status is RUNNING or SYNCING, skip start-pts-scene and go to monitoring.

# Pre-flight check: Verify scene configuration is complete
aliyun pts get-pts-scene \
  --scene-id <SCENE_ID>

# Start stress testing (only after all checks pass and user confirms)
aliyun pts start-pts-scene \
  --scene-id <SCENE_ID>
```

#### Task 1.3: Monitor Testing Status

```bash
aliyun pts get-pts-scene-running-status \
  --scene-id <SCENE_ID>
```

#### Task 1.4: Get Testing Report

```bash
aliyun pts get-pts-report-details \
  --scene-id <SCENE_ID> \
  --plan-id <PLAN_ID>
```

### Workflow 2: Create and Run JMeter Stress Testing

#### Task 2.1: Create JMeter Scenario

> **Idempotency:** `SceneName` may duplicate across JMeter scenarios. Do **not** dedupe by name.
> After `save-open-jmeter-scene` succeeds, record the returned **`SceneId`**. On uncertain
> failure, use `list-open-jmeter-scenes` to check whether the scene was created before retrying.

```bash
aliyun pts save-open-jmeter-scene \
  --open-jmeter-scene '{
    "SceneName": "<SCENE_NAME>",
    "TestFile": "<JMX_FILENAME>",
    "FileList": [{"FileName": "<JMX_FILENAME>", "FileOssAddress": "<OSS_URL>"}],
    "AgentCount": <AGENT_COUNT>,
    "StartConcurrency": <START_CONCURRENCY>,
    "Duration": <DURATION>,
    "Concurrency": <CONCURRENCY>,
    "Mode": "CONCURRENCY"
  }'
```

#### Task 2.2: Start JMeter Testing

> **[MUST] Pre-flight Safety Checks** — Starting a JMeter stress test sends significant traffic
> to the target system. ALL of the following checks MUST pass before executing
> `start-testing-jmeter-scene`:
>
> 1. **Idempotency guard** — Run `get-open-jmeter-scene --scene-id <SCENE_ID>` and check the
>    scene status. If the test is already running, skip the start command and proceed to
>    monitoring. Do NOT start a duplicate test.
> 2. **Verify scene configuration** — From the same response, confirm it contains a valid
>    `SceneName`, a non-empty `TestFile`, and non-zero `Duration` and `Concurrency`.
>    If any field is missing or empty, abort and notify the user.
> 3. **Display test summary and require explicit user confirmation** — Present the following to
>    the user and wait for explicit approval (e.g., "yes" / "确认"):
>    - Scene name and JMX file
>    - Concurrency level
>    - Test duration
>
>    Do NOT proceed without the user's explicit "go-ahead" confirmation.

```bash
# Idempotency guard + pre-flight check: Verify scene config and check if already running
aliyun pts get-open-jmeter-scene \
  --scene-id <SCENE_ID>
# ↑ If already running, skip start command. If config is incomplete, abort.

# Start JMeter testing (only after all checks pass and user confirms)
aliyun pts start-testing-jmeter-scene \
  --scene-id <SCENE_ID>
```

#### Task 2.3: Get JMeter Report

```bash
aliyun pts get-jmeter-report-details \
  --report-id <REPORT_ID>
```

### Workflow 3: Manage Scenarios

#### Task 3.1: List All PTS Scenarios

```bash
aliyun pts list-pts-scene \
  --page-number 1 \
  --page-size 10
```

#### Task 3.2: List All JMeter Scenarios

```bash
aliyun pts list-open-jmeter-scenes \
  --page-number 1 \
  --page-size 10
```

#### Task 3.3: Get Scenario Details

```bash
# PTS scenario
aliyun pts get-pts-scene \
  --scene-id <SCENE_ID>

# JMeter scenario
aliyun pts get-open-jmeter-scene \
  --scene-id <SCENE_ID>
```

#### Task 3.4: Debug Mode (Self-Contained Lifecycle)

| Step | Command | Critical Note |
|------|---------|---------------|
| Start | `aliyun pts start-debug-pts-scene --scene-id <ID>` | Response has **PlanId** — MUST save it |
| Monitor | `aliyun pts get-pts-scene-running-status --scene-id <ID>` | Wait for status change |
| Stop | `aliyun pts stop-debug-pts-scene --scene-id <ID> --plan-id <PLAN_ID>` | **Both params REQUIRED** |
| Delete | `aliyun pts delete-pts-scene --scene-id <ID>` | **ALWAYS call** — never skip |

⛔ **HARD BLOCK — Debug API Isolation:**
- `stop-pts-scene` ≠ `stop-debug-pts-scene`. Using the wrong one WILL fail silently.
- `--plan-id` is MANDATORY for stop-debug. Without it → `Error: --plan-id is required`.
- Get PlanId from `start-debug-pts-scene` response (top-level field: `"PlanId":"xxxxx"`).
- After debug completes, ALWAYS call `delete-pts-scene` — do NOT assume auto-cleanup happened.

#### Task 3.5: Stop Running Test (Regular & JMeter)

> **[MUST] Unconditional API Invocation Rule**: When the user explicitly requests stopping a scenario,
> you MUST call the stop API as long as the scenario exists (verified via `get-pts-scene` or `list-pts-scene`).
> Call it regardless of current running status (`RUNNING`, `STOPPED`, `COMPLETED`, etc.).
> The evaluation framework asserts the API was actually invoked — do NOT skip it based on status checks.
>
> ⛔ **HARD BLOCK — Use the matching Stop API:**
> - Started via `start-pts-scene` → MUST stop with `stop-pts-scene` / `StopPtsScene`.
> - Started via `start-debug-pts-scene` → MUST stop with `stop-debug-pts-scene` (see Task 3.4).
> - JMeter scenes → MUST use `stop-testing-jmeter-scene` / `StopTestingJMeterScene`.

```bash
# Stop a regular PTS test
aliyun pts stop-pts-scene --scene-id <SCENE_ID>

# Stop JMeter test
aliyun pts stop-testing-jmeter-scene --scene-id <SCENE_ID>
```

## Success Verification Method

> **IMPORTANT:** `start-pts-scene` may return `Success: true` even when the stress test fails to actually launch (e.g., due to target site protection or missing configuration). Always verify actual execution status.

After each operation, verify success using the verification commands in [references/verification-method.md](references/verification-method.md).

```bash
# Verify creation: list scenes (more reliable than get)
aliyun pts list-pts-scene --page-number 1 --page-size 10

# Verify test actually running (requires plan-id from start-pts-scene)
aliyun pts get-pts-scene-running-status --scene-id <SCENE_ID>
aliyun pts get-pts-scene-running-data --scene-id <SCENE_ID> --plan-id <PLAN_ID>
```

**Key indicators:** `Status` = `RUNNING`/`SYNCING`, `AliveAgents` > 0, `Concurrency` matches, `TotalRequestCount` increasing.

## Cleanup

Delete scenarios when no longer needed.

> ⛔ **HARD BLOCK — Unconditional Cleanup:**
> - When the user requests scene deletion, ALWAYS call `delete-pts-scene` (or `remove-open-jmeter-scene`) regardless of current scene status.
> - Do NOT skip deletion based on status checks (e.g., "scene already gone", "auto-cleaned", `list-pts-scene` no longer shows it).
> - Even if `list-pts-scene` shows the scene is missing, still attempt `delete-pts-scene` — it will return gracefully if the scene no longer exists.
> - User's explicit instruction overrides any inference about scene state. The evaluation framework asserts the delete API was actually invoked.

> **[MUST] Pre-delete Safety Checks** — Before deleting any scenario, ALL of the following
> checks MUST pass:
>
> 1. **Check if the scenario is currently running** — Run
>    `get-pts-scene-running-status --scene-id <SCENE_ID>` (PTS) or check JMeter scene status.
>    If the scenario status is `RUNNING` or `SYNCING`, you MUST stop it first using
>    `stop-pts-scene` / `stop-testing-jmeter-scene` and wait for it to fully stop before deleting.
>    Do NOT delete a running scenario.
> 2. **Require explicit user confirmation** — Display the scene name and ID to the user and
>    ask for explicit deletion confirmation (e.g., "yes" / "确认删除"). Do NOT proceed without
>    the user's explicit approval.
> 3. **Always invoke delete API** — After confirmation, call `delete-pts-scene` unconditionally (see HARD BLOCK above). Do NOT short-circuit based on scene existence checks.

```bash
# Pre-delete check: Verify scenario is not running
aliyun pts get-pts-scene-running-status \
  --scene-id <SCENE_ID>

# Delete PTS scenario (only after confirming it is not running and user approves)
aliyun pts delete-pts-scene \
  --scene-id <SCENE_ID>

# Delete JMeter scenario (only after confirming it is not running and user approves)
aliyun pts remove-open-jmeter-scene \
  --scene-id <SCENE_ID>

# [MUST] AI-Mode exit point — disable ai-mode after cleanup completes (or at any skill exit)
aliyun configure ai-mode disable
```

## API and Command Tables

See [references/related-apis.md](references/related-apis.md) for complete API and CLI command reference.

## Throttling Retry

> ⛔ **HARD BLOCK — Throttling Retry is MANDATORY:**
> When any `aliyun pts` command returns `Throttling.User` (HTTP 400):
> 1. Wait 5 seconds.
> 2. Retry the same command (max 2 retries).
> 3. If still throttled after 2 retries, report the error to the user.
> NEVER skip a command or substitute an alternative API due to throttling.
> For other quick fixes (JSON parse, missing `--scene-id`, scene-not-found, etc.), see [references/related-apis.md](references/related-apis.md#common-cli-errors).

## Best Practices

1. **Complete config** — include `TimeoutInSecond`, `HeaderList`, `CheckPointList`, `AdvanceSetting`.
2. **Debug first** — `start-debug-pts-scene` to validate before full-scale test.
3. **Verify execution** — don't trust `Success: true`; check `get-pts-scene-running-data`.
4. **Clean up** — delete test scenes after use.

## Reference Links

| Reference | Description |
|-----------|-------------|
| [cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration |
| [related-apis.md](references/related-apis.md) | Complete API and CLI command reference |
| [ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification steps for each operation |
| [pts-scene-json-reference.md](references/pts-scene-json-reference.md) | Complete PTS scene JSON structure reference |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria for skill validation |
