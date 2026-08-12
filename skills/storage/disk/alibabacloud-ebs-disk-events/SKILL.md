---
name: alibabacloud-ebs-disk-events
description: |
  Alibaba Cloud EBS Disk Risk Events Skill. Query and analyze cloud disk risk events via the DescribeEvents API, supporting filtering by disk, event name, level, status, and time range.
  Triggers: "EBS events", "disk events", "cloud disk risk events", "DescribeEvents", "EBS disk events", "IOHang event", "NoSnapshot event", "cost optimization event", "query disk events", "filtering disk events".
---

# Alibaba Cloud EBS Disk Risk Events Analysis

This skill is used to query and analyze Alibaba Cloud Elastic Block Storage (EBS) disk risk events. Based on the EBS `DescribeEvents` API, it supports filtering and paginated querying by disk, event name, event level, event status, and time range.

## Scenario Description

Cloud disk events reported by CloudLens for EBS help users discover and handle the following issues in a timely manner:

- **NoSnapshot (Data Protection)**: Long-term absence of snapshots poses a risk of data loss.
- **CostOptimizationNeeded**: ESSD AutoPL disk provisioned performance does not match actual workload.
- **DiskIOHang (IO Hang)**: Disk IO latency is too high, causing system instability or downtime.
- **DiskSpecNotMatchedWithInstance**: The total disk specification exceeds the instance specification limit.
- **IOPS/BPS Limit Reached**: Instance or disk IOPS/BPS reaches the instance or disk specification limit.
- **DiskIONo4kAligned (Non-4K Aligned IO)**: May affect cloud disk IO performance.
- **BurstIOTriggered**: Burst IO occurs on the disk and may incur burst performance costs.

**Architecture**: EBS CloudLens / Block Storage Data Insights + DescribeEvents API + Cloud Disk Resources.

**Supported Event Types (EventType)**:

- `Notification`: Usage-triggered, the event can automatically recover immediately after being reported.
- `Alert`: Usage-triggered, manual recovery operations are required.
- `SystemException`: Underlying-triggered, severe events affecting user usage.

**Supported Event Levels (EventLevel)**:

- `INFO`: Notification
- `WARN`: Warning
- `CRITICAL`: Critical

**Event Statuses (Status)**:

- `WillExecute`: Pending
- `Executing`: In Progress
- `Executed`: Processed
- `Ignore`: Ignored
- `Expired`: Expired
- `Deleted`: Deleted

---

## Installation

**Pre-check: Aliyun CLI >= 3.3.3**

> Run `aliyun version` to confirm the version is >= 3.3.3. If it is not installed or the version is too low,
> refer to `references/cli-installation-guide.md` for platform-specific installation methods
> (Homebrew for macOS, binary package download for Linux/Windows).

**Pre-check: Install/Update EBS Plugin**

> [MUST] Run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] Run `aliyun plugin install --names aliyun-cli-ebs` to install the Block Storage plugin.
> [MUST] Run `aliyun plugin update` to keep the plugin up to date.

---

## Authentication

> **Pre-check: Alibaba Cloud credentials required**
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
> Check whether a valid profile exists in the output (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from the [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/manage/ak)
> 2. Complete configuration outside of this session (via `aliyun configure` in the terminal or environment variables in the shell profile)
> 3. Resume only after `aliyun configure list` shows a valid profile

---

## RAM Policy

This skill requires the following Alibaba Cloud RAM permissions. See `references/ram-policies.md` for the complete permission policy.

**Required API Permission**:

- `ebs:DescribeEvents` - Query cloud disk risk events

> **[MUST] Permission Failure Handling**: If any command or API call fails due to permission errors, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this skill
> 2. Use the `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted before continuing

---

## Observability

> **[MUST] Session Tracking** — All `aliyun` CLI commands in this skill MUST include a `--user-agent` header for traceability. The legacy `aliyun configure ai-mode` mechanism is deprecated and MUST NOT be used.

### User-Agent Template

```
AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/{session-id}
```

| Placeholder | Description |
|-------------|-------------|
| `{session-id}` | 32-char lowercase hex string, generated once per skill invocation (see rules below) |

### Session-ID Generation Rule

- **Generate exactly one** session-id per skill invocation, at the start of the Core Workflow (before the first CLI command).
- **Format**: 32-char lowercase hex string (e.g., `a1b2c3d4e5f67890a1b2c3d4e5f67890`)
- **Reuse**: If the environment variable `SKILL_SESSION_ID` is already set, reuse that value instead of generating a new one.
- **Persistence**: Do NOT regenerate session-id between steps of the same invocation.
- **Generation** (pick one):
  ```bash
  # Preferred
  openssl rand -hex 16
  # Alternative
  uuidgen | tr -d '-' | head -c 32 | tr 'A-F' 'a-f'
  ```

### Usage

Every `aliyun ebs describe-events` command in this skill MUST append the `--user-agent` flag with the template above:

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters (e.g., `RegionId`, `EventName`, `ResourceId`, `Status`, `EventLevel`, time ranges, etc.) MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

### Parameter Description

| Parameter Name | Required/Optional | Description | Default Value | Example |
|----------------|-------------------|-------------|---------------|---------|
| `--RegionId` | **Required** | Region ID | None | `cn-hangzhou` |
| `--EventName` | Optional | Event name | None | `DiskIOHang` |
| `--ResourceId` | Optional | Resource ID (disk ID) | None | `d-bp67acfmxazb4p****` |
| `--ResourceType` | Optional | Resource type, value `disk` | None | `disk` |
| `--Status` | Optional | Event status | None | `WillExecute` |
| `--StartTime` | Optional | Event start time (ISO 8601, UTC+0) | None | `2023-06-01T03:00:00Z` |
| `--EndTime` | Optional | Event end time (ISO 8601, UTC+0) | None | `2023-06-01T04:00:00Z` |
| `--EventLevel` | Optional | Event level | None | `WARN` |
| `--MaxResults` | Optional | Maximum number of entries per page (1~100) | `10` | `10` |
| `--NextToken` | Optional | Pagination token | None | `AAAAAdDWBF2****` |

### Event Name (EventName) Values

| Event Name | Description |
|------------|-------------|
| `NoSnapshot` | Data Protection |
| `BurstIOTriggered` | Burst IO |
| `CostOptimizationNeeded` | Cost Optimization |
| `DiskSpecNotMatchedWithInstance` | Instance and Disk Spec Mismatch |
| `DiskIONo4kAligned` | Non-4K Aligned IO |
| `DiskIOHang` | Disk IO Hang Detected |
| `InstanceIOPSExceedInstanceMaxLimit` | Instance IOPS Reached Limit |
| `InstanceBPSExceedInstanceMaxLimit` | Instance BPS Reached Limit |
| `DiskIOPSExceedInstanceMaxLimit` | Disk IOPS Reached Instance Limit |
| `DiskBPSExceedInstanceMaxLimit` | Disk BPS Reached Instance Limit |
| `DiskIOPSExceedDiskMaxLimit` | Disk IOPS Reached Disk Limit |
| `DiskBPSExceedDiskMaxLimit` | Disk BPS Reached Disk Limit |

---

## Core Workflow

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Generate Session-ID** — Generate a session-id for observability tracking (see [Observability](#observability) for the full rule).
> All CLI commands in this workflow MUST include the `--user-agent` header.
> ```bash
> # Reuse SKILL_SESSION_ID if already set; otherwise generate a new one
> if [ -z "${SKILL_SESSION_ID:-}" ]; then
>   export SKILL_SESSION_ID=$(openssl rand -hex 16)
> fi
> echo "Session ID: ${SKILL_SESSION_ID}"
> ```

### Scenario 1: Query All Disk Events in a Region

```bash
# Confirm parameter: RegionId
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 10 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

**Expected Output**:

```json
{
  "RequestId": "473469C7-AA6F-4DC5-B3DB-A3DC0DE3****",
  "TotalCount": 1,
  "NextToken": "AAAAAdDWBF2****",
  "ResourceEvents": [
    {
      "EventType": "Alert",
      "EventName": "DiskIOHang",
      "ResourceId": "d-bp67acfmxazb4p****",
      "ResourceType": "disk",
      "Status": "WillExecute",
      "StartTime": "1684204822000",
      "EndTime": "1679538083000",
      "Description": "可通过购买4296预配置IOPS以获得成本优化，根据您过往7天使用情况，预计成本可以下降16%。",
      "RecommendAction": "AdjustProvision",
      "RecommendParams": "4296",
      "EventLevel": "INFO",
      "ExtraAttributes": "{\"EcsInstanceId\":\"i-uf6dkn9qpcw6y94g7ag7\",\"Adapter\":\"hda\"}"
    }
  ]
}
```

### Scenario 2: Query Events by Disk ID

```bash
# Confirm parameters: RegionId, ResourceId
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --ResourceId d-bp67acfmxazb4p**** \
  --ResourceType disk \
  --MaxResults 20 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

### Scenario 3: Query IO Hang Events by Event Name

```bash
# Confirm parameters: RegionId, EventName
aliyun ebs describe-events \
  --RegionId cn-shanghai \
  --EventName DiskIOHang \
  --MaxResults 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

### Scenario 4: Filter by Event Level and Status

```bash
# Confirm parameters: RegionId, EventLevel, Status
aliyun ebs describe-events \
  --RegionId cn-beijing \
  --EventLevel WARN \
  --Status WillExecute \
  --MaxResults 100 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

### Scenario 5: Query by Time Range

```bash
# Confirm parameters: RegionId, StartTime, EndTime
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --StartTime 2024-01-15T00:00:00Z \
  --EndTime 2024-01-15T23:59:59Z \
  --MaxResults 100 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

### Scenario 6: Paginated Query

```bash
# Confirm parameters: RegionId, NextToken (use NextToken returned from previous call)
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 100 \
  --NextToken AAAAAdDWBF2**** \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

### Scenario 7: Multi-Condition Combined Query

```bash
# Confirm parameters: RegionId, EventName, EventLevel, Status, time range
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --EventName DiskIOHang \
  --EventLevel WARN \
  --Status WillExecute \
  --StartTime 2024-01-15T00:00:00Z \
  --EndTime 2024-01-15T23:59:59Z \
  --MaxResults 100 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

> **[MUST] Session Tracking at EVERY exit point** — Before delivering the final response for ANY reason, record the session-id for traceability. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> The session-id `${SKILL_SESSION_ID}` can be referenced in CLI debug logs and Alibaba Cloud service-side traces.

---

## Success Verification Method

After querying events, verify the following:

1. **Response Status**: Check that the response contains `RequestId`, indicating a successful API call.
2. **Event List**: Check whether the `ResourceEvents` array contains the expected events.
3. **TotalCount**: Confirm that `TotalCount` is consistent with the number of returned entries.
4. **Field Completeness**: Check that each event contains key fields such as `EventName`, `EventType`, `EventLevel`, `Status`, `ResourceId`, and `StartTime`.
5. **Time Range**: Confirm that `StartTime`/`EndTime` timestamps (in milliseconds) fall within the query range.
6. **Extra Attributes**: When needed, parse the `ExtraAttributes` JSON to obtain the attached ECS instance ID (`EcsInstanceId`) and mount point (`Adapter`).

For detailed verification steps, see `references/verification-method.md`.

---

## Cleanup

This skill only queries event data and does not create any resources. No cleanup is required.

---

## Best Practices

1. **Filter on Demand**: Use `EventName`, `ResourceId`, `Status`, and `EventLevel` to reduce the amount of returned data.
2. **Paginated Querying**: Use `MaxResults` and `NextToken` together when the number of events is large.
3. **Time Range**: Use `StartTime` and `EndTime` to limit the query window and avoid returning too many historical events.
4. **Focus on Alert and SystemException**: These two event types usually require manual handling and should be prioritized.
5. **Parse ExtraAttributes**: Use `EcsInstanceId` and `Adapter` to quickly locate the affected ECS instance and mount point.
6. **Follow Recommended Actions**: Execute recommended operations based on `RecommendAction` and `RecommendParams` (e.g., modify specification, create snapshot, resize disk).
7. **Time Zone Awareness**: Time parameters in the API use UTC+0 (ISO 8601 format), and returned timestamps are millisecond-level Unix timestamps.
8. **Least Privilege**: Only grant the read-only permission `ebs:DescribeEvents`.
9. **Confirm Recovery in Time**: For Alert-type events, observe whether the event status changes to recovered/processed after handling.
10. **Monitor Quotas**: Be aware of API call frequency and avoid frequent full pulls.

---

## Reference Links

| Reference File | Description |
|----------------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | Complete RAM permission policy for EBS event APIs |
| [references/related-commands.md](references/related-commands.md) | All CLI commands used in this skill |
| [references/verification-method.md](references/verification-method.md) | Detailed verification steps and commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Test patterns and acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |

---

## Common Issues and Solutions

**Issue**: `InvalidApi.NotFound` or command does not exist
- **Solution**: Confirm that the `aliyun-cli-ebs` plugin is installed, and use `aliyun ebs describe-events` (lowercase-hyphenated command name).

**Issue**: `Forbidden` or `Forbidden.Action`
- **Solution**: The current account lacks the `ebs:DescribeEvents` permission. Please request the permission as described in `references/ram-policies.md`.

**Issue**: `InvalidParameter` or invalid parameter
- **Solution**: Check whether `EventName`, `Status`, and `EventLevel` are from the allowed value lists; check whether the time format is ISO 8601 with the `Z` suffix.

**Issue**: `ResourceEvents` is empty
- **Solution**: Confirm that disks exist in the specified region, events were reported within the time range, or try relaxing the filter conditions.

**Issue**: `InvalidParameter.TooManyDataQueried`
- **Solution**: Narrow the time range, or reduce `MaxResults` and use pagination.

---

## Advanced Usage

### Filter Output with JMESPath

```bash
# Output only the event name list
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --cli-query "ResourceEvents[].EventName" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

### Parse Event Details with jq

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --ResourceId d-bp67acfmxazb4p**** \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}" \
  | jq '.ResourceEvents[] | {EventName, EventType, EventLevel, Status, ResourceId}'
```

---

**For more information**:
- [EBS Risk Events Overview](https://help.aliyun.com/zh/ecs/user-guide/risk-events-overview)
- [DescribeEvents API Documentation](https://help.aliyun.com/zh/ecs/developer-reference/api-ebs-2021-07-30-describeevents)
- [OpenAPI Explorer - DescribeEvents](https://api.aliyun.com/api/ebs/2021-07-30/DescribeEvents)
