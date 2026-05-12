---
name: alibabacloud-sase-pa-network-diagnosis
description: |
  SASE Private Access (PA) Network Diagnosis Skill. Creates and queries SASE Private Access
  network diagnosis tasks to troubleshoot connectivity issues between enterprise endpoints
  and origin servers through the SASE cluster.
  Supports FullLink diagnosis (endpoint to origin) and Application diagnosis (POP to origin).
  Triggers: "SASE network diagnosis", "Private Access diagnosis", "PA diagnosis",
  "FullLink diagnosis", "Application diagnosis", "network link troubleshooting",
  "SASE PA network diagnosis"
---

# SASE Private Access Network Diagnosis

Diagnose whether the enterprise network path through the SASE cluster to office applications is connected, providing link-level visibility and problem localization.

**Architecture**: `SASE Client → POP Entry Point → Connector/CEN/VPN → VPC → Origin Server`

## Diagnosis Types

| Type | Description | Use Case |
|------|-------------|----------|
| **FullLink** | Diagnose the full path: Endpoint → POP → Origin | Troubleshoot end-to-end connectivity issues |
| **Application** | Diagnose POP → Origin path only | Troubleshoot SASE cluster to origin network issues |

## Limitations

The following features **cannot be implemented via CLI or SDK** and require the [SASE Console](https://yundun.console.aliyun.com/):

| Feature | Reason | Workaround |
|---------|--------|------------|
| **Visual link diagram** | Console-only UI feature | Analyze NetworkLinkInfo JSON data from API response |
| **Delete diagnosis task** | No public API available | Operate in Console: Private Access > Network Diagnosis |
| **Retry diagnosis task** | No public API available | Re-create a new task with the same parameters |
| **List diagnosis tasks** | No list API available | Record DiagnoseId and query individually |
| **SASE App version check** | Client-side capability | Ensure SASE App >= 4.4.1 |
| **Diagnosis task concurrency limit** | Max 5 concurrent running tasks | Wait and retry on `DiagnosisTask.NumberExceedsLimit` error |

## Prerequisites

- SASE App version >= 4.4.1
- Network tunnel established (VPC/CEN/Connector/VPN)
- Office application added and zero-trust policy configured

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

> **Pre-check: Aliyun CLI plugin update required**
> - [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> - [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> ```bash
> aliyun configure set --auto-plugin-install true
> aliyun plugin update
> ```

> **CLI invocation rule**: Use Aliyun CLI plugin mode only. Commands MUST use lowercase kebab-case actions and parameters, for example `aliyun csas create-pa-diagnosis-task --diagnose-type FullLink ...`.
> Do NOT use PascalCase OpenAPI action names in CLI invocations, and do NOT use `--force` generic mode for these diagnosis APIs.

## Environment Variables

No skill-specific environment variables are required. Use an existing Aliyun CLI credential profile and verify it with `aliyun configure list`.

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
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Permissions

The following RAM permissions are required:

| Action | Description |
|--------|-------------|
| `csas:ListUserDevices` | Query user device list (to obtain DevTag) |
| `csas:CreatePADiagnosisTask` | Create Private Access diagnosis task |
| `csas:GetPADiagnosisTask` | Query Private Access diagnosis task details |

See [references/ram-policies.md](references/ram-policies.md) for full policy details.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `--diagnose-type` | Required | Diagnosis type: `FullLink` / `Application` | — |
| `--host` | Required | Target address (IP or domain) | — |
| `--port` | Required | Target port | — |
| `--protocol` | Required | Protocol: `TCP` / `UDP` | — |
| `--username` | Conditional | Username (required for FullLink) | — |
| `--dev-tag` | Conditional | Device ID (required for FullLink) | — |
| `--user-group-id` | Conditional | User group ID (required for Application) | — |
| `--pop-mode` | Required | POP selection mode: `AutoSelect` / `ManualSelect` | — |
| `--pop-id` | Conditional | POP entry point ID (required when `--pop-mode ManualSelect`) | — |
| `--udp-extra-configs` | Optional | UDP probe config object, for example `RequestContent=<request_content> ExpectedResponse=<expected_response>` | — |

## Core Workflow

> **[MUST] Enable AI-Mode at the start of Core Workflow (before any CLI invocation):**
> AI-mode is required for Agent Skill execution. Run the following commands before any CLI invocation in this skill:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sase-pa-network-diagnosis"
> ```
>
> **[MUST] Disable AI-Mode at EVERY exit point:**
> Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed. AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

> **CLI invocation rule**: Use plugin mode commands only: `create-pa-diagnosis-task`, `get-pa-diagnosis-task`, and `list-user-devices`.
> Do not use PascalCase API names or `--force` generic mode.

### Task 0: Query User Device DevTag (FullLink prerequisite)

> FullLink diagnosis requires `DevTag` (device ID), but users typically only know the username or hostname.
> Use `list-user-devices` to query the device list and filter for eligible devices to obtain `DeviceTag`.

**Device selection criteria** (ALL must be satisfied):

| Criteria | Description | Parameter / Field |
|----------|-------------|-------------------|
| Device online | SASE App must be connected | `--app-statuses Online` |
| Device type | Only Windows or macOS supported | `--device-types Windows macOS` |
| App version | SASE App >= 4.4.1 | Response field `AppVersion`, check client-side |

**Query eligible devices by username**:

```bash
aliyun csas list-user-devices \
  --current-page 1 --page-size 50 \
  --username <username> \
  --app-statuses Online \
  --device-types Windows macOS \
  --cli-query 'Devices[].{DeviceTag: DeviceTag, Hostname: Hostname, DeviceType: DeviceType, AppVersion: AppVersion}'
```

**Query eligible devices by hostname**:

```bash
aliyun csas list-user-devices \
  --current-page 1 --page-size 50 \
  --hostname <hostname> \
  --app-statuses Online \
  --device-types Windows macOS \
  --cli-query 'Devices[].{DeviceTag: DeviceTag, Hostname: Hostname, DeviceType: DeviceType, AppVersion: AppVersion}'
```

> **Version check**: The API does not support filtering by version. Check the `AppVersion` field in results to verify >= 4.4.1.
> If the version does not meet requirements, prompt the user to upgrade SASE App first.

> **Multiple devices handling**: A user may have multiple devices; the result is a list.
> - If only 1 device with a valid version, use its `DeviceTag` directly
> - If multiple devices, display the list and ask the user to confirm which device to use
> - If no eligible devices found, inform the user to check: device online status, device type support, and version compliance

### Task 1: Create FullLink Diagnosis Task

```bash
aliyun csas create-pa-diagnosis-task \
  --diagnose-type FullLink \
  --host <target_address> \
  --port <port> \
  --protocol TCP \
  --username <username> \
  --dev-tag <DeviceTag_from_Task0> \
  --pop-mode AutoSelect
```

### Task 2: Create Application Diagnosis Task

```bash
aliyun csas create-pa-diagnosis-task \
  --diagnose-type Application \
  --host <target_address> \
  --port <port> \
  --protocol TCP \
  --user-group-id <user_group_id> \
  --pop-mode ManualSelect \
  --pop-id <pop_id>
```

**UDP protocol example** (with probe config):

```bash
aliyun csas create-pa-diagnosis-task \
  --diagnose-type Application \
  --host <target_address> \
  --port <port> \
  --protocol UDP \
  --user-group-id <user_group_id> \
  --pop-mode ManualSelect \
  --pop-id <pop_id> \
  --udp-extra-configs RequestContent=<request_content> ExpectedResponse=<expected_response>
```

### Concurrency Limit and Retry

> **[IMPORTANT] Diagnosis task concurrency limit is 5.** When the number of running tasks reaches the limit, `create-pa-diagnosis-task` returns the following error:
>
> ```
> ErrorCode: DiagnosisTask.NumberExceedsLimit
> Message: The number of running diagnosis tasks exceeds the limit of 5.
>          Please wait for the tasks to complete.
> ```
>
> **When this error occurs, use bounded incremental backoff and retry:**
> 1. Retry task creation up to 5 times.
> 2. Wait longer before each retry: 30 seconds, 60 seconds, 90 seconds, 120 seconds, then 150 seconds.
> 3. If any retry succeeds, extract `DiagnoseId` and continue to polling. Do not skip the polling and result analysis steps after a successful create.
> 4. If all 5 retries fail, clearly tell the user that the SASE diagnosis concurrency limit is still full. Ask the user to open the SASE Console and manually end idle diagnosis tasks, or confirm whether to retry with another `--diagnose-type` (`FullLink` <-> `Application`) after providing the parameters required by that diagnosis type.
> 5. If the user cannot clear tasks or switch diagnosis type, run `aliyun configure ai-mode disable` and terminate the current workflow.
>
> **Note**: Do NOT expose the raw error message to the user. Instead, explain: "Other diagnosis tasks are currently running and the concurrency limit (5) has been reached. Waiting and retrying..."

Extract `DiagnoseId` from the successful response:

```bash
# Extract DiagnoseId
aliyun csas create-pa-diagnosis-task \
  --diagnose-type FullLink --host <target_address> --port <port> --protocol TCP \
  --username <username> --dev-tag <DeviceTag_from_Task0> --pop-mode AutoSelect \
  --cli-query 'DiagnosisTask.DiagnoseId' --quiet
```

### Task 3: Query Diagnosis Task Result

```bash
aliyun csas get-pa-diagnosis-task \
  --diagnose-id <diagnose_id>
```

### Task 4: Poll Until Task Completes

Poll manually with a bounded loop until `Status` contains `Finished` or `Failed`.
The CLI output may contain quotes, whitespace, or line breaks, so do not rely on exact string equality.

```bash
MAX_POLLS=20
POLL_INTERVAL=10
POLL_COUNT=0
STATUS=""

while [ "$POLL_COUNT" -lt "$MAX_POLLS" ]; do
  sleep "$POLL_INTERVAL"
  POLL_COUNT=$((POLL_COUNT + 1))
  STATUS=$(aliyun csas get-pa-diagnosis-task \
    --diagnose-id <diagnose_id> \
    --cli-query 'DiagnosisTask.Status' --quiet 2>/dev/null | tr -d '[:space:]"')
  echo "Current status: $STATUS"
  if echo "$STATUS" | grep -qE 'Finished|Failed'; then
    break
  fi
done

if ! echo "$STATUS" | grep -qE 'Finished|Failed'; then
  echo "Polling timed out after $((MAX_POLLS * POLL_INTERVAL)) seconds; retrieve the full task result once and explain that the task may still be running or status parsing failed."
fi
```

> **Polling safety**: Never poll more than `MAX_POLLS` times in one workflow. If polling times out, retrieve the full task result once with `get-pa-diagnosis-task`, summarize the current status, then stop or ask the user whether to continue waiting.

### Task 5: Retrieve Full Diagnosis Result and Analyze

> **[IMPORTANT] Must retrieve the complete result before performing comprehensive analysis.**
> The `Success` field only indicates whether the diagnosis task itself completed normally — **it does NOT indicate whether the network link is healthy**.
> Actual network issue information is distributed across `NetworkLinkInfo.Nodes`, `NetworkLinkInfo.Links`, `PolicyInfo`, and other fields.
> Example: `Success=true` but a Node has `Success=false` with `Error` containing zero-trust policy block info means the diagnosis process ran fine but the network is actually blocked.

**Step 1: Retrieve the full diagnosis result** (single call to get all fields):

```bash
aliyun csas get-pa-diagnosis-task \
  --diagnose-id <diagnose_id>
```

**Step 2: Comprehensively analyze the following fields from the full result**:

| Field Path | Meaning | Analysis Points |
|------------|---------|-----------------|
| `DiagnosisTask.Status` | Task status | Must be `Finished`; `Failed` means diagnosis itself errored |
| `DiagnosisTask.Result.Success` | Whether diagnosis flow completed | `true` only means the diagnosis process executed normally |
| `DiagnosisTask.Result.ErrorMessage` | Diagnosis-level error | Non-empty indicates diagnosis process error |
| `DiagnosisTask.Result.NetworkLinkInfo.Nodes` | Status of each network node | **Check each Node's `Success` and `Error` fields** to locate which link segment has issues |
| `DiagnosisTask.Result.NetworkLinkInfo.Links` | Inter-node link connectivity | Check each Link's status |
| `DiagnosisTask.Result.NetworkLinkInfo.Dns` | DNS resolution result | Verify domain resolves correctly |
| `DiagnosisTask.Result.PolicyInfo` | Zero-trust policy match | Check if policy allows access, block reason |

> **Analysis principle**: Even when `Success=true`, you MUST iterate through every Node's `Success` and `Error` fields in `Nodes`.
> When a node-level `Success=false` with non-empty `Error`, explain the specific issue for that link segment to the user (e.g., policy block, connection timeout, etc.).

## Verification

See [references/verification-method.md](references/verification-method.md)

## Cleanup

> **Note**: There is no public API to delete diagnosis tasks. To delete, go to [SASE Console](https://yundun.console.aliyun.com/) > Private Access > Network Diagnosis.

## Related Commands

See [references/related-commands.md](references/related-commands.md)

## Best Practices

1. **FullLink diagnosis** requires a specific device (DevTag) and username; **Application diagnosis** requires a user group (UserGroupId)
2. Choose a POP entry point closest to the target origin server to minimize network latency
3. FullLink supports auto-routing (`PopMode=AutoSelect`); Application requires manual POP selection
4. For UDP protocol, configure probe request and expected response to verify packet delivery
5. After creating a task, poll `get-pa-diagnosis-task` until Status becomes `Finished` or `Failed`
6. On diagnosis failure, use `ErrorMessage` and each Node's `Success/Error` in `NetworkLinkInfo` to locate the problematic segment
7. After resolving the issue, re-create a diagnosis task with the same parameters to verify

## References

| Document | Description |
|----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/related-commands.md](references/related-commands.md) | Related API command list |
| [references/verification-method.md](references/verification-method.md) | Verification method |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [Official Docs: Network Diagnosis](https://help.aliyun.com/zh/sase/user-guide/network-diagnostics) | Alibaba Cloud official guide |
| [CreatePADiagnosisTask API](https://api.aliyun.com/document/csas/2023-01-20/CreatePADiagnosisTask) | Create diagnosis task API doc |
| [GetPADiagnosisTask API](https://api.aliyun.com/document/csas/2023-01-20/GetPADiagnosisTask) | Query diagnosis task API doc |
