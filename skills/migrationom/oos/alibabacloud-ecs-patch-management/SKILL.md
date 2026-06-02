---
name: alibabacloud-ecs-patch-management
description: |
  Alibaba Cloud ECS Patch Management Skill. Use for scanning and installing OS patches on ECS instances via OOS (Operation Orchestration Service).
  Triggers: "patch management", "scan patches", "install patches", "OS update", "security patches", "ACS-ECS-BulkyApplyPatchBaseline", "oos patch", "系统补丁扫描", "系统补丁安装".
---

# ECS Patch Management

Scan and install operating system patches on Alibaba Cloud ECS instances using the OOS `ACS-ECS-BulkyApplyPatchBaseline` template.

## Architecture

**ECS + OOS + Cloud Assistant + Snapshot (optional)**

- **OOS Template**: `ACS-ECS-BulkyApplyPatchBaseline` — built-in public template for batch patch operations
- **Cloud Assistant**: Executes patch commands on ECS instances (requires Cloud Assistant client installed)
- **Snapshot Service**: Creates pre-patch disk snapshots for rollback safety (optional)
- **Patch Baseline**: Defines which patches to scan/install (uses default system baseline or custom)

## Pre-check: Aliyun CLI >= 3.3.3 Required

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## Pre-check: Alibaba Cloud Credentials Required

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
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

## AI-Mode Lifecycle Management

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-patch-management"
> ```
> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

## RAM Policy

Required permissions for this skill:

| Service | Actions | Purpose |
|---------|---------|---------|
| OOS | `StartExecution`, `ListExecutions`, `CancelExecution`, `ListTemplates`, `GetTemplate` | Manage patch executions |
| OOS | `ListPatchBaselines`, `GetPatchBaseline`, `ListInstancePatches`, `ListInstancePatchStates` | Patch baseline and status queries |
| ECS | `DescribeInstances`, `DescribeInvocations`, `DescribeInvocationResults`, `InvokeCommand` | Instance verification and Cloud Assistant |
| ECS | `CreateSnapshot`, `DescribeSnapshots` | Snapshot management (optional) |

Full details: [references/ram-policies.md](references/ram-policies.md)

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameters Requiring User Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance IDs, action type,
> snapshot settings, etc.) MUST be confirmed with the user. Do NOT assume or use
> default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `regionId` | Yes | Alibaba Cloud region ID (e.g., `cn-hangzhou`, `cn-shanghai`) | None |
| `instanceIds` | Yes | Target ECS instance IDs (e.g., `["i-bp1example0000000001"]`) | None |
| `action` | Yes | Operation type: `scan` (scan only) or `install` (scan + install) | None |
| `rebootIfNeed` | No (install only) | Whether to reboot the instance if patches require it | `false` |
| `whetherCreateSnapshot` | No (install only) | Whether to create a snapshot before installing patches | `false` |
| `retentionDays` | No (install only) | Snapshot retention in days. **Recommended: 7–30** (API range: 1–65536) | `7` |

> Parameter names above match the JSON field names used in `--parameters` (top-level keys are camelCase). Note that the nested `targets` object uses PascalCase keys (`ResourceIds`, `RegionId`, `Type`) — see the examples in Step 3 below.

## Core Workflow

### Step 0: Enable AI-Mode

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-patch-management"

# [MUST] Register a shell trap so AI-mode is disabled on EVERY exit path
# (success, error, signal, Ctrl-C, abnormal termination). This is the
# fail-safe complement to the explicit `disable` call in Step 7.
trap 'aliyun configure ai-mode disable' EXIT
```

### Step 1: Verify CLI and Credentials

```bash
aliyun version
aliyun configure list
```

### Step 2: Verify Target Instances

Confirm the target ECS instances exist and are in `Running` status:

```bash
aliyun ecs describe-instances \
  --region <RegionId> \
  --instance-ids '<InstanceIds_JSON>' \
  --cli-query 'Instances.Instance[].{InstanceId:InstanceId, Status:Status, OSName:OSName}'
```

> **Prerequisite**: Target ECS instances must have the Cloud Assistant client installed and running. Most Alibaba Cloud public images include it by default.

### Step 3: Start Patch Execution

> **[MUST] Honor the user's requested action.** If the user explicitly asks to **install** patches (e.g., "装补丁", "安装补丁", "install patches"), you **MUST** execute `action=install`. Do NOT skip the install call because a prior scan returned zero missing patches. The scan is advisory only — the install action has its own detection logic and the user's explicit intent always takes precedence.

> **[MUST] StartExecution is asynchronous.** The response only confirms that the execution has been **submitted**, not that it has finished. The response returns an `ExecutionId` in the format `exec-xxx` (e.g., `exec-example0000000001`). You **MUST** capture this `ExecutionId` and poll `ListExecutions` (Step 4) until `Status` reaches a terminal value (`Success` or `Failed`) before considering the operation complete. Do NOT treat a successful StartExecution response as proof that the patch operation succeeded.

> **[MUST] Idempotency via `ClientToken`.** `StartExecution` is a write operation. A network timeout, a transport-layer error, or an Agent retry loop can cause the same call to be issued more than once, which would otherwise create **duplicate executions** (and, for `install`, duplicate snapshots/reboots). You **MUST** pass a `--client-token` derived deterministically from the request inputs so that retries with the same inputs converge on the same execution.
>
> **Generation rule** — compute a stable hash over the canonical inputs (action, region, sorted instance IDs, and the install-only knobs that change behavior):
>
> ```bash
> # Generate a deterministic ClientToken (≤ 64 chars) from the canonical inputs.
> # Use the SAME formula across retries — the server deduplicates within ~24h.
> CLIENT_TOKEN="patch-$(printf '%s|%s|%s|%s|%s|%s' \
>   "<action>" "<RegionId>" "<sorted_comma_joined_InstanceIds>" \
>   "<rebootIfNeed_or_empty>" "<whetherCreateSnapshot_or_empty>" "<retentionDays_or_empty>" \
>   | shasum -a 256 | cut -c1-32)"
> # Example output: patch-9f3c1a8b7e6d5c4f3a2b1d0e9c8b7a6f
> ```
>
> Pass the resulting value as `--client-token "$CLIENT_TOKEN"` on every `start-execution` call. If you must retry after a transient failure, **reuse the same token**; do NOT regenerate it.

#### Option A: Scan Only

```bash
aliyun oos start-execution \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --client-token "$CLIENT_TOKEN" \
  --parameters '{"regionId":"<RegionId>","action":"scan","targets":{"ResourceIds":<InstanceIds_JSON>,"RegionId":"<RegionId>","Type":"ResourceIds"}}'
```

#### Option B: Install Patches

> **🚨 DANGER — Destructive operation requiring explicit user confirmation.**
> `action=install` will modify system packages on the target instance(s) and, if
> `rebootIfNeed=true`, may **reboot** them, causing service downtime.
>
> Before executing the command below, you **MUST**:
> 1. Display the full execution plan to the user — `regionId`, the exact list of
>    target instance IDs (and **count**), `rebootIfNeed`, `whetherCreateSnapshot`,
>    `retentionDays` — in a single confirmation message.
> 2. State explicitly: *"About to install patches on N instance(s) in <region>.
>    Reboot=<true/false>. Snapshot=<true/false>. Proceed?"*
> 3. Wait for the user to reply with an affirmative (`yes` / `确认` / `proceed`).
>    Do **NOT** infer consent from earlier turns or default to yes on silence.
> 4. If the user changes any parameter, regenerate `CLIENT_TOKEN` and re-confirm.

```bash
aliyun oos start-execution \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --client-token "$CLIENT_TOKEN" \
  --parameters '{"regionId":"<RegionId>","action":"install","rebootIfNeed":<true/false>,"whetherCreateSnapshot":<true/false>,"retentionDays":<number>,"targets":{"ResourceIds":<InstanceIds_JSON>,"RegionId":"<RegionId>","Type":"ResourceIds"}}'
```

**Example — Scan for instance `i-bp1example0000000001` in `cn-hangzhou`:**

```bash
CLIENT_TOKEN="patch-$(printf 'scan|cn-hangzhou|i-bp1example0000000001|||' | shasum -a 256 | cut -c1-32)"

aliyun oos start-execution \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --client-token "$CLIENT_TOKEN" \
  --parameters '{"regionId":"cn-hangzhou","action":"scan","targets":{"ResourceIds":["i-bp1example0000000001"],"RegionId":"cn-hangzhou","Type":"ResourceIds"}}'
```

**Example — Install patches with snapshot and auto-reboot:**

```bash
CLIENT_TOKEN="patch-$(printf 'install|cn-hangzhou|i-bp1example0000000001|true|true|7' | shasum -a 256 | cut -c1-32)"

aliyun oos start-execution \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --client-token "$CLIENT_TOKEN" \
  --parameters '{"regionId":"cn-hangzhou","action":"install","rebootIfNeed":true,"whetherCreateSnapshot":true,"retentionDays":7,"targets":{"ResourceIds":["i-bp1example0000000001"],"RegionId":"cn-hangzhou","Type":"ResourceIds"}}'
```

### Step 4: Monitor Execution Status

Extract the `ExecutionId` (format: `exec-xxx`) from Step 3's response, then poll `ListExecutions` until the execution reaches a terminal status:

```bash
aliyun oos list-executions \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --execution-id <ExecutionId> \
  --cli-query 'Executions.Execution[0].{ExecutionId:ExecutionId, Status:Status, StartDate:StartDate, EndDate:EndDate}'
```

**Terminal statuses** (stop polling when `Status` matches one of these):

| Status | Meaning | Next action |
|--------|---------|-------------|
| `Success` | Execution finished successfully | Proceed to Step 5 (logs) and Step 6 (verify patches) |
| `Failed` | Execution failed | Inspect logs in Step 5 to diagnose the failure |
| `Cancelled` | Execution was cancelled | No further action; re-run if needed |

**Non-terminal statuses** (keep polling): `Started`, `Running`, `Queued`, `Waiting`. Continue polling at a reasonable interval (e.g., every 10–30 seconds) until a terminal status is reached. Only consider the patch operation complete once `Status` is `Success` or `Failed`.

### Step 5: View Execution Logs

```bash
aliyun oos list-execution-logs \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --execution-id <ExecutionId>
```

### Step 6: Verify Patch Results

After a `scan` or `install` execution reaches `Success`, two complementary APIs report patch state on each instance:

#### 6a. `ListInstancePatches` — per-patch detail on a single instance

Returns the full list of individual patches detected on the instance, with metadata such as patch name/KB, classification, severity, and per-patch status (e.g., `Installed`, `Missing`, `NotApplicable`). Use this to inspect **which** patches are present, missing, or failed.

```bash
aliyun oos list-instance-patches \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --instance-id <InstanceId>
```

#### 6b. `ListInstancePatchStates` — per-state count summary across instances

Returns aggregate counts of patches grouped by state for each instance (e.g., `InstalledCount`, `MissingCount`, `FailedCount`, `NotApplicableCount`). Use this to quickly assess **how many** patches fall into each category without enumerating individual patches.

```bash
aliyun oos list-instance-patch-states \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --instance-ids '<InstanceIds_JSON>'
```

**When to use which:**
- Need a high-level compliance summary (e.g., "instance i-xxx still has 3 missing patches")? → `ListInstancePatchStates`
- Need to identify specific patches (e.g., "which CVEs are still missing")? → `ListInstancePatches`

### Step 7: Disable AI-Mode

```bash
aliyun configure ai-mode disable
```

> **[MUST] Always disable AI-mode** at every exit point — success, failure, error, or cancellation.

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

**Quick verification checklist:**

| Step | Check | Command |
|------|-------|---------|
| 1 | CLI version >= 3.3.3 | `aliyun version` |
| 2 | Credentials valid | `aliyun configure list` |
| 3 | Instance running | `aliyun ecs describe-instances` |
| 4 | Execution started | Response contains `ExecutionId` |
| 5 | Execution succeeded | `Status` = `Success` via `list-executions` |
| 6 | Patches applied | `list-instance-patches` shows reduced `Missing` count |

## Cleanup

### Cancel a Running Execution

```bash
aliyun oos cancel-execution \
  --region <RegionId> \
  --execution-id <ExecutionId>
```

### Snapshot Lifecycle

Snapshots created with `whetherCreateSnapshot=true` are **automatically deleted**
when their `retentionDays` window expires. Do **not** delete them manually —
relying on the retention window keeps the cleanup deterministic and avoids
accidentally removing a snapshot that another rollback workflow still needs.

To inspect existing snapshots (read-only):

```bash
aliyun ecs describe-snapshots \
  --region <RegionId> \
  --instance-id <InstanceId>
```

## Best Practices

1. **Always scan before install** — Run `action: scan` first to understand what patches are available before committing to installation. **However, if the user explicitly requests patch installation, you MUST still execute `action=install` regardless of scan results.** A scan showing zero missing patches does NOT mean you can skip the install — the user's explicit intent takes priority. The `install` action performs its own internal scan and may detect patches the standalone scan did not. Never substitute a scan for an install when the user asked for installation.
2. **Enable snapshots for production** — Set `whetherCreateSnapshot: true` with an appropriate `retentionDays` for production instances to enable rollback. Snapshots auto-expire — no manual cleanup needed.
3. **Schedule during maintenance windows** — Patch installation may require reboots. Coordinate with business stakeholders.
4. **Test on non-production first** — Always validate patches on a staging/dev instance before applying to production.
5. **Monitor execution logs** — Use `list-execution-logs` to track real-time progress and troubleshoot failures.
6. **Handle reboot carefully** — Set `rebootIfNeed: true` only when you can tolerate instance downtime. For critical services, use `rebootIfNeed: false` and reboot manually.
7. **Keep retentionDays reasonable** — Recommended 7–30 days. Longer retention increases storage costs.

## Reference Links

| Resource | Path |
|----------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| RAM Policies | [references/ram-policies.md](references/ram-policies.md) |
| Related Commands | [references/related-commands.md](references/related-commands.md) |
| Verification Methods | [references/verification-method.md](references/verification-method.md) |
| Acceptance Criteria | [references/acceptance-criteria.md](references/acceptance-criteria.md) |

## Related Documentation

- [OOS Official Documentation](https://help.aliyun.com/zh/oos/)
- [ACS-ECS-BulkyApplyPatchBaseline Template](https://help.aliyun.com/zh/oos/user-guide/acs-ecs-bulkyapplypatchbaseline)
- [Patch Management Overview](https://help.aliyun.com/zh/oos/user-guide/patch-management)
- [Cloud Assistant](https://help.aliyun.com/zh/ecs/user-guide/cloud-assistant-overview)
