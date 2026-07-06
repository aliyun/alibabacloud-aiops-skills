---
name: alibabacloud-emas-apm-remotelog
description: |
  EMAS APM Remote Log (TLog) CLI Skill. Use for remote log retrieval, task management, and log query operations via Alibaba Cloud CLI.
  Triggers: "EMAS APM", "remote log", "tlog", "log retrieval", "log collection", "get-tlog-device-list", "create-tlog-task", "search-tlog", "mobile app log".
---

# EMAS APM Remote Log (TLog) CLI Skill

## Scenario Description

This skill enables remote log retrieval (TLog) operations for mobile applications managed by Alibaba Cloud EMAS APM (Application Performance Monitoring). It provides a complete workflow to:

1. **Resolve target devices** by device ID, user nickname, user ID, or custom ID
2. **Create remote log retrieval tasks** to trigger log collection from end-user devices
3. **Track task progress** including overall task status and per-device collection status
4. **Query log details** by device and time window with level and keyword filtering
5. **Query actively submitted logs** for user-initiated log uploads

**Architecture**: EMAS Console + Mobile App (with TLog SDK) + EMAS APM Service + Alibaba Cloud CLI (`emas-appmonitor` plugin)

**Key Components**:
- **Device Side**: Mobile apps integrated with EMAS TLog SDK (Android/iOS)
- **Server Side**: EMAS APM backend service for task dispatch and log storage
- **Client Side**: Alibaba Cloud CLI with `aliyun-cli-emas-appmonitor` plugin for API operations

## Installation

**Pre-check: Alibaba Cloud CLI >= 3.3.3 required**

```bash
aliyun version
# If not installed or version too low (script served by Alibaba Cloud official CDN over HTTPS):
curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash
aliyun version
```

> **Security note** — the one-liner above pipes a remote script directly into `bash`. The script is hosted on Alibaba Cloud's official CDN (`aliyuncli.alicdn.com`) and served over HTTPS, so transit is authenticated. However, if your environment requires inspecting installer scripts before execution (security-hardened CI, regulated workloads, multi-tenant hosts), use the safer two-step flow in [references/cli-installation-guide.md](references/cli-installation-guide.md#safer-installation-flow) — download → inspect → execute. Do **not** run this command with elevated privileges (e.g. as root); the installer does not require it.

**Pre-check: Alibaba Cloud CLI plugin update required**

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

**Install EMAS APM Plugin**

```bash
aliyun plugin install --names aliyun-cli-emas-appmonitor
aliyun plugin list | grep emas-appmonitor  # Verify version >= 0.3.1
```

> For detailed installation instructions, see [references/cli-installation-guide.md](references/cli-installation-guide.md)

## AI-Mode Lifecycle Management

> **[MUST] AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-emas-apm-remotelog"
> ```
> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first.
> ```bash
> aliyun configure ai-mode disable
> ```

## Credential Verification

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
>
> **Data Safety**: Do not save real AccessKeys in command-line parameters, scripts, or logs. Authentication is fully delegated to CLI profiles.

## RAM Policy

> **Required Permissions**: See [references/ram-policies.md](references/ram-policies.md) for the complete list of RAM permissions required by each API.
>
> **Quick Reference**:
>
> | Permission | API |
> |------------|-----|
> | `apm:GetTlogDeviceList` | Query available devices |
> | `apm:GetTlogDeviceInfo` | Get device details |
> | `apm:CreateTlogTask` | Create log retrieval task |
> | `apm:GetTlogTaskInfo` | Query task status |
> | `apm:GetTlogTaskCollections` | Query device collection status |
> | `apm:SearchTlog` | Query log details |
> | `apm:GetTlogCollectList` | Query active submission records |
>
> **System Policies**: `AliyunEMASFullAccess` or `AliyunEMASReadOnlyAccess`
>
> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameters Requiring User Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., AppKey, OS type, device identifiers,
> task names, time windows, etc.) MUST be confirmed with the user. Do NOT assume or use
> default values without explicit user approval.
>
> **[MUST] RegionId is fixed** — EMAS APM service is ONLY available in `cn-shanghai`.
> Always pass `--region cn-shanghai` regardless of the credential's default region
> (e.g., even if `aliyun configure list` shows `cn-hangzhou`). Do NOT ask the user
> to confirm RegionId, and do NOT try other regions on failure.

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `RegionId` | Yes (fixed) | EMAS APM service region — **must be `cn-shanghai`** (only supported region) | `cn-shanghai` |
| `AppKey` | Yes | Application key from EMAS console | `123456789` |
| `OS` | Yes | Mobile OS type: `android` or `iphoneos` | `android` |
| `UserNick` | Conditional | User nickname for device lookup | `testuser01` |
| `DeviceId` | Conditional | Device unique ID (UTDID) | `Z1234567890ABCDEF` |
| `Keyword` | Conditional | User ID or custom ID for lookup | `user_12345` |
| `TaskName` | Yes (create task) | Name for the log retrieval task | `task-2024-01-15-user01` |
| `Days` | Yes (create task) | Number of days of log history to retrieve | `1` |
| `OperatorName` | Yes (create task) | Operator name (AliYunName) | `admin` |
| `DeviceJson` | Yes (create task) | Device metadata JSON array | See workflow |
| `BeginDate` | Yes (query logs) | Start time in Unix milliseconds (13 digits) | `1700000000000` |
| `EndDate` | Yes (query logs) | End time in Unix milliseconds (13 digits) | `1700086400000` |
| `TaskId` | Conditional | Task ID returned from create operation | `tlog_task_xxxxx` |
| `PageIndex` | No | Page number for paginated results | `1` |
| `PageSize` | No | Number of results per page | `10` |
| `LevelJson` | No (query logs) | Log level filter as JSON array | `["error","warning"]` |
| `Keyword` | No (query logs) | Log content search keyword | `NullPointerException` |
| `SourceType` | Yes (collect list) | Source type: `USER` or `POSITIVE` | `POSITIVE` |

## Core Workflow

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or use
> default values without explicit user approval.

### Workflow 1: Known User — Create Retrieval Task and Query Logs

Use when you know a user's identity and need to retrieve their device logs.

#### Step 1: Resolve Device by Identity

```bash
# By user nickname (fuzzy/prefix match)
aliyun emas-appmonitor get-tlog-device-list \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --user-nick <UserNick> \
  --page-index 1 \
  --page-size 10

# By user ID or custom ID (exact match)
aliyun emas-appmonitor get-tlog-device-list \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --keyword <UserId> \
  --page-index 1 \
  --page-size 10

# By device ID (exact match)
aliyun emas-appmonitor get-tlog-device-list \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --utdid <DeviceId> \
  --page-index 1 \
  --page-size 10
```

**Optional**: Query single device details:

```bash
aliyun emas-appmonitor get-tlog-device-info \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --device-id <DeviceId>
```

#### Step 2: Preview Task Parameters (Dry-Run)

> **IMPORTANT**: `create-tlog-task` will create a real task and trigger device-side log collection.
> You MUST use `--cli-dry-run` first to preview the request body and confirm parameters.

```bash
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --ali-yun-name <OperatorName> \
  --days <Days> \
  --task-name <TaskName> \
  --source-type USER \
  --device-json '[{"appId":"<AppKey>@<OS>","appKey":"<AppKey>","deviceId":"<DeviceId>","os":"<OS>","osVersion":"<osVersion>","appVersion":"<appVersion>","userName":"<UserNick>","brand":"<brand>","deviceModel":"<deviceModel>","geo":"<geo>"}]' \
  --cli-dry-run
```

#### Step 3: Create Task (After Confirmation)

Remove `--cli-dry-run` after confirming parameters:

```bash
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --ali-yun-name <OperatorName> \
  --days <Days> \
  --task-name <TaskName> \
  --source-type USER \
  --device-json '[{"appId":"<AppKey>@<OS>","appKey":"<AppKey>","deviceId":"<DeviceId>","os":"<OS>","osVersion":"<osVersion>","appVersion":"<appVersion>","userName":"<UserNick>","brand":"<brand>","deviceModel":"<deviceModel>","geo":"<geo>"}]'
```

**Note**: On success, `Model` returns the `taskId` as a plain string (not a JSON object).

#### Step 4: Poll Task Status

Query overall task status:

```bash
aliyun emas-appmonitor get-tlog-task-info \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --task-id <TaskId>
```

| Status | Meaning |
|--------|---------|
| `NORMAL` | Task in progress |
| `SUCCEEDED` | Task completed successfully |
| `FAILED` | Task failed |
| `SUSPENDED` | Task expired |
| `CANCELLED` | Task cancelled |

> **[MUST] Defensive existence check** — `get-tlog-task-info` may return
> `Success: true` with an empty placeholder model even when the `taskId`
> does not exist (no `TaskNotFound` error). The placeholder looks like:
> `status=NORMAL`, `dayNum=0`, `progress="0/0/0/0"`, `collectionNums=0`,
> and a fresh `createTime` equal to "now". **Do NOT trust `Model.status`
> alone.** Confirm the task is real by ALL of:
> - `Model.dayNum > 0` (real tasks always have a configured day window)
> - `Model.taskName` / `Model.author` non-empty
> - `Model.createTime` is older than the request time (real tasks are not created at query time)
>
> If the placeholder pattern is detected, treat it as **task does not exist**: surface this clearly to the user, and do NOT proceed to `get-tlog-task-collections` or `search-tlog`. The most common cause is a malformed or truncated `taskId` (e.g. a hyphen in the taskId mistakenly parsed as a CLI flag delimiter — always pass `taskId` quoted).

Query per-device collection status:

```bash
aliyun emas-appmonitor get-tlog-task-collections \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --task-id <TaskId>
```

| Collection Status | Meaning |
|-------------------|---------|
| `START` | Task created, device has not pulled |
| `PULL_REPLIED` | Device has task, token not applied |
| `TOKEN_APPLIED` | Token issued, waiting for upload |
| `FILE_SENDED` | File metadata saved, waiting for parsing |
| `FINISHED` | Logs are queryable |
| `FAIL_OVER` | Collection failed |
| `SUSPENDED` | Task expired |
| `CANCELLED` | Task cancelled |

#### Step 5: Query Logs (When Device Status is FINISHED)

```bash
aliyun emas-appmonitor search-tlog \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --device-id <DeviceId> \
  --begin-date <BeginDate> \
  --end-date <EndDate> \
  --page-index 1 \
  --page-size 100 \
  --level-json '["debug","info","warning","error"]' \
  --keyword <Keyword>
```

**Time Window Rules**:
- `--begin-date`: Use `task.createTime - days * 86400000` to cover the full retrieval range
- `--end-date`: Use at least `task.modifyTime` (task completion time) or current time; do NOT use `task.createTime` as this will miss logs generated after the task was created
- All times are Unix milliseconds (13 digits)

### Workflow 2: Known TaskId — Query Task Progress and Logs

Use when you already have a `taskId` and need to check progress and retrieve logs.

```bash
# Step 1: Check overall task status
aliyun emas-appmonitor get-tlog-task-info \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --task-id <TaskId>

# Step 2: Check per-device collection status
aliyun emas-appmonitor get-tlog-task-collections \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --task-id <TaskId>

# Step 3: For devices with FINISHED status, query logs
aliyun emas-appmonitor search-tlog \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --device-id <DeviceId> \
  --begin-date <BeginDate> \
  --end-date <EndDate>
```

### Workflow 3: Query Actively Submitted Logs

For user-initiated log submissions (not manually triggered retrieval):

```bash
# Step 1: Query active submission records
aliyun emas-appmonitor get-tlog-collect-list \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --source-type POSITIVE \
  --page-index 1 \
  --page-size 20 \
  --device-id <DeviceId>

# Step 2: For records with FINISHED status, use deviceId + createTime window to query logs
aliyun emas-appmonitor search-tlog \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --device-id <DeviceId> \
  --begin-date <createTime - window> \
  --end-date <createTime + window>
```

**Note**: The `taskId` in active submission records is a system-generated association ID and CANNOT be queried via `get-tlog-task-info`.

### Workflow 4: Direct Log Query by Device and Time

When you already know the device and time range:

```bash
aliyun emas-appmonitor search-tlog \
  --region cn-shanghai \
  --app-key <AppKey> \
  --os <OS> \
  --device-id <DeviceId> \
  --begin-date <BeginDate> \
  --end-date <EndDate> \
  --level-json '["error","warning"]' \
  --keyword <Keyword>
```

## Success Verification

For each workflow step, verify success using the methods documented in [references/verification-method.md](references/verification-method.md):

| Step | Verification Method |
|------|--------------------|
| Plugin Installation | `aliyun plugin list \| grep emas-appmonitor` shows version >= 0.3.1 |
| Credentials | `aliyun configure list` shows valid profile |
| Device Resolution | Response `Success: true`, non-empty device list |
| Task Creation (Dry-Run) | Request body preview matches intended parameters |
| Task Creation (Actual) | `Model` returns a valid taskId string |
| Task Status | Status is one of: NORMAL, SUCCEEDED, FAILED, SUSPENDED, CANCELLED |
| Device Collection | At least one device reaches `FINISHED` status |
| Log Query | Response `Success: true`, log entries returned |
| Active Submission | Records returned with valid status and timestamps |

## Best Practices

1. **Always dry-run first**: Before creating a task, always use `--cli-dry-run` to preview and confirm request parameters.
2. **Use correct time windows**: For `search-tlog`, calculate `--begin-date` as `createTime - days * 86400000` and `--end-date` as at least `modifyTime` or current time.
3. **Poll with appropriate intervals**: Task collection may take minutes. Poll `get-tlog-task-info` every 30-60 seconds.
4. **Handle task IDs correctly**: Task IDs from `create-tlog-task` are plain strings. Active submission record `taskId`s are system-generated and cannot be queried with `get-tlog-task-info`.
5. **Use pagination**: For large result sets, use `--page-index` and `--page-size` to paginate through results.
6. **Filter logs efficiently**: Use `--level-json` and `--keyword` to narrow down log results.
7. **Security first**: Never embed credentials in scripts or command history. Rely on CLI profiles or environment variables.
8. **Check permissions**: If API calls fail with permission errors, refer to [references/ram-policies.md](references/ram-policies.md) and use the `ram-permission-diagnose` skill.

## Reference Files

| File | Description |
|------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission requirements for all APIs |
| [references/related-commands.md](references/related-commands.md) | Complete CLI command reference |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect usage patterns |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification procedures |

## Related Documentation

- [Alibaba Cloud CLI Documentation](https://help.aliyun.com/zh/cli/)
- [CLI Credential Configuration](https://help.aliyun.com/zh/cli/configure-credentials)
- [EMAS Mobile Monitoring Product](https://api.aliyun.com/product/emas-appmonitor)
- [CreateTlogTask API](https://api.aliyun.com/api/emas-appmonitor/2019-06-11/CreateTlogTask)
- [GetTlogDeviceList API](https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogDeviceList)
- [GetTlogDeviceInfo API](https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogDeviceInfo)
- [GetTlogCollectList API](https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogCollectList)
- [SearchTlog API](https://api.aliyun.com/api/emas-appmonitor/2019-06-11/SearchTlog)
- [GetTlogTaskCollections API](https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogTaskCollections)
- [GetTlogTaskInfo API](https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogTaskInfo)
