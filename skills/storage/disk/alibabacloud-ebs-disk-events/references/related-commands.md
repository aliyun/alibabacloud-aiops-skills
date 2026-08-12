# Related CLI Commands

This document lists the Alibaba Cloud CLI commands used in the `alibabacloud-ebs-disk-events` Skill.

---

## EBS (Block Storage) Commands

### Core Commands

| Product | CLI Command | Description | API Version |
|---------|------------|-------------|-------------|
| EBS | `aliyun ebs describe-events` | Query cloud disk risk events | 2021-07-30 |

---

## Command Details

### `aliyun ebs describe-events`

Query risk events for one or more cloud disks, supporting filtering by event name, resource, status, level, and time range, with pagination support.

**Usage**:

```bash
aliyun ebs describe-events [parameters]
```

**Required Parameters**:

- `--RegionId` (string) - Region ID, e.g., `cn-hangzhou`

**Optional Parameters**:

- `--EventName` (string) - Event name
- `--ResourceId` (string) - Resource ID (cloud disk ID)
- `--ResourceType` (string) - Resource type, value `disk`
- `--Status` (string) - Event status
- `--StartTime` (string) - Event start time (ISO 8601, UTC+0, format `yyyy-MM-ddTHH:mm:ssZ`)
- `--EndTime` (string) - Event end time (ISO 8601, UTC+0)
- `--EventLevel` (string) - Event level
- `--MaxResults` (integer) - Maximum number of entries per page, range 1~100, default 10
- `--NextToken` (string) - Pagination token

**Event Name (EventName) Values**:

| Value | Description |
|-------|-------------|
| `NoSnapshot` | Data Protection |
| `BurstIOTriggered` | Burst IO |
| `CostOptimizationNeeded` | Cost Optimization |
| `DiskSpecNotMatchedWithInstance` | Instance and Disk Spec Mismatch |
| `DiskIONo4kAligned` | Non-4K Aligned IO |
| `DiskIOHang` | Disk IO Hang |
| `InstanceIOPSExceedInstanceMaxLimit` | Instance IOPS Reached Limit |
| `InstanceBPSExceedInstanceMaxLimit` | Instance BPS Reached Limit |
| `DiskIOPSExceedInstanceMaxLimit` | Disk IOPS Reached Instance Limit |
| `DiskBPSExceedInstanceMaxLimit` | Disk BPS Reached Instance Limit |
| `DiskIOPSExceedDiskMaxLimit` | Disk IOPS Reached Disk Limit |
| `DiskBPSExceedDiskMaxLimit` | Disk BPS Reached Disk Limit |

**Event Level (EventLevel) Values**:

- `INFO`: Notification
- `WARN`: Warning
- `CRITICAL`: Critical

**Event Status (Status) Values**:

- `WillExecute`: Pending
- `Executing`: In Progress
- `Executed`: Processed
- `Ignore`: Ignored
- `Expired`: Expired
- `Deleted`: Deleted

**Example 1: Query All Events in a Region**

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 10
```

**Example 2: Query Events by Disk ID**

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --ResourceId d-bp67acfmxazb4p**** \
  --ResourceType disk \
  --MaxResults 20
```

**Example 3: Query IO Hang Events by Event Name**

```bash
aliyun ebs describe-events \
  --RegionId cn-shanghai \
  --EventName DiskIOHang \
  --MaxResults 50
```

**Example 4: Filter by Event Level and Status**

```bash
aliyun ebs describe-events \
  --RegionId cn-beijing \
  --EventLevel WARN \
  --Status WillExecute \
  --MaxResults 100
```

**Example 5: Query by Time Range**

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --StartTime 2024-01-15T00:00:00Z \
  --EndTime 2024-01-15T23:59:59Z \
  --MaxResults 100
```

**Example 6: Paginated Query**

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 100 \
  --NextToken AAAAAdDWBF2****
```

---

## Configuration Commands

### Observability (Session Tracking)

> **[MUST]** All `aliyun` CLI commands in this skill MUST include the `--user-agent` flag for request traceability. The deprecated `aliyun configure ai-mode` mechanism is no longer used.

**User-Agent Template** (placeholder format):

```
AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/{session-id}
```

**Session-ID Generation Rule**:

- Generate once per skill invocation, 32-char lowercase hex string
- If the environment variable `SKILL_SESSION_ID` is already set, reuse it without regenerating
- Preferred: `openssl rand -hex 16`; Alternative: `uuidgen | tr -d '-' | head -c 32 | tr 'A-F' 'a-f'`

**Usage Example**:

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"
```

### Credential Configuration

| Command | Description |
|---------|-------------|
| `aliyun configure list` | View configured credential profiles |
| `aliyun configure` | Interactive credential configuration (use outside of Skill session) |

### Plugin Management

| Command | Description |
|---------|-------------|
| `aliyun plugin install --names aliyun-cli-ebs` | Install EBS plugin |
| `aliyun plugin update` | Update all plugins to the latest version |
| `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |

---

## Global Flags

The following flags can be used with all `aliyun ebs` commands:

| Flag | Description | Example |
|------|-------------|---------|
| `--dryrun` | Print request only, do not send API call | `--dryrun` |
| `--cli-query` | Filter output using JMESPath | `--cli-query "ResourceEvents[].EventName"` |
| `--endpoint` | Override service endpoint | `--endpoint https://ebs.cn-hangzhou.aliyuncs.com` |
| `--log-level` | Set log level | `--log-level DEBUG` |
| `--pager, --all-pages` | Merge paginated results | `--pager` |
| `--user-agent` | Override User-Agent header (Observability required) | `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-events/${SKILL_SESSION_ID}"` |
| `-q, --quiet` | Quiet output | `-q` |
| `--region` | Override region ID | `--region cn-shanghai` |
| `-h, --help` | Show command help | `-h` |

---

## Auxiliary Commands (Not in Core Workflow)

These related commands may be used for extended analysis:

| Product | CLI Command | Description |
|---------|------------|-------------|
| EBS | `aliyun ebs describe-disks` | List and view cloud disk details |
| EBS | `aliyun ebs describe-metric-data` | Query cloud disk monitoring metrics |
| ECS | `aliyun ecs describe-disks` | View disks attached to ECS instances |
| ECS | `aliyun ecs describe-instances` | List ECS instances |

---

## Command Verification

Use the following command to verify command availability:

```bash
aliyun ebs describe-events --help
```

Verification date: 2026-07-30  
CLI version: 3.4.7  
EBS plugin version: 0.7.0

---

## References

- [Alibaba Cloud CLI Documentation](https://www.alibabacloud.com/help/en/cli)
- [EBS API Reference](https://api.aliyun.com/api/ebs/2021-07-30)
- [OpenAPI Explorer - DescribeEvents](https://api.aliyun.com/api/ebs/2021-07-30/DescribeEvents)
