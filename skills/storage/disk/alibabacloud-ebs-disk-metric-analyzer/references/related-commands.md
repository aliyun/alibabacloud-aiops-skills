# Related CLI Commands

This document lists all Alibaba Cloud CLI commands used in the `alibabacloud-ebs-disk-metric-analyzer` skill.

---

## EBS (Elastic Block Storage) Commands

### Core Command

| Product | CLI Command | Description | API Version |
|---------|------------|-------------|-------------|
| EBS | `aliyun ebs describe-metric-data` | Query monitoring metric data for cloud disks | 2021-07-30 |

---

## Command Details

### `aliyun ebs describe-metric-data`

Query single or multiple disk monitoring metrics with optional aggregation and grouping.

**Usage**:
```bash
aliyun ebs describe-metric-data [parameters]
```

**Required Parameters**:
- `--metric-name` (string) - Metric name to query

**Optional Parameters**:
- `--biz-region-id` (string) - Region ID (e.g., cn-hangzhou)
- `--start-time` (string) - Query start time (ISO 8601 format: yyyy-MM-ddTHH:mm:ssZ)
- `--end-time` (string) - Query end time (ISO 8601 format: yyyy-MM-ddTHH:mm:ssZ)
- `--period` (integer) - Data granularity in seconds (5, 10, 60, 300, 600, 3600)
- `--dimensions` (string) - JSON filter for disk dimensions
- `--aggre-ops` (string) - Time aggregation method
- `--aggre-over-line-ops` (string) - Cross-disk aggregation method
- `--group-by-labels` (array) - Fields for grouping

**Supported Metric Names**:
1. `disk_bps_percent` - Disk bandwidth utilization percentage
2. `disk_iops_percent` - Disk IOPS utilization percentage
3. `disk_read_block_size` - Average read block size
4. `disk_read_bps` - Read bandwidth (bytes per second)
5. `disk_read_iops` - Read IOPS
6. `disk_write_block_size` - Average write block size
7. `disk_write_bps` - Write bandwidth (bytes per second)
8. `disk_write_iops` - Write IOPS

**Time Aggregation Methods** (`--aggre-ops`):
- `SUM_OVER_TIME` - Sum over time
- `COUNT_OVER_TIME` - Count over time
- `AVG_OVER_TIME` - Average over time
- `MAX_OVER_TIME` - Maximum over time
- `MIN_OVER_TIME` - Minimum over time
- `SUM_OVER_TIME_LCRO` - Sum over left-closed, right-open interval
- `AVG_OVER_TIME_LCRO` - Average over left-closed, right-open interval
- `SUM_OVER_TIME_LORC` - Sum over left-open, right-closed interval
- `AVG_OVER_TIME_LORC` - Average over left-open, right-closed interval

**Cross-Disk Aggregation Methods** (`--aggre-over-line-ops`):
- `NON` - No aggregation (default)
- `SUM` - Sum across disks
- `AVG` - Average across disks
- `COUNT` - Count across disks
- `MAX` - Maximum across disks
- `MIN` - Minimum across disks

**Dimension Filters** (`--dimensions` JSON fields):
- `DiskId` - Disk ID (e.g., ["d-bp1234567890"])
- `DeviceType` - Disk type (["system"] or ["data"])
- `DeviceCategory` - Disk category (e.g., ["cloud_essd"])
- `EcsInstanceId` - ECS instance ID (e.g., ["i-bp1234567890"])
- `Azone` - Availability zone (e.g., ["cn-hangzhou-a"])

**Group By Labels** (`--group-by-labels`):
- `DiskId`
- `DeviceType`
- `DeviceCategory`
- `EcsInstanceId`
- `Azone`

**Period and Time Range Limits**:
| Period (seconds) | Max Time Range |
|------------------|----------------|
| 5 | 12 hours |
| 10 | 24 hours |
| 60 | 7 days |
| 300 | 30 days |
| 600 | 30 days |
| 3600 | 30 days |

**Example: Query single disk read IOPS**:
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 60 \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou
```

**Example: Query multiple disks with aggregation**:
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_write_bps \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-15T23:59:59Z \
  --period 300 \
  --dimensions "{\"DeviceType\": [\"data\"]}" \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --biz-region-id cn-shanghai
```

**Example: Group by disk category**:
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_iops_percent \
  --period 3600 \
  --aggre-ops MAX_OVER_TIME \
  --group-by-labels DeviceCategory \
  --biz-region-id cn-beijing
```

---

## Configuration Commands

### AI-Mode Configuration (Required for Skill Execution)

| Command | Description |
|---------|-------------|
| `aliyun configure ai-mode enable` | Enable AI-mode for agent skill execution |
| `aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-metric-analyzer"` | Set user-agent for skill tracking |
| `aliyun configure ai-mode disable` | Disable AI-mode after skill completion |

### Credential Configuration

| Command | Description |
|---------|-------------|
| `aliyun configure list` | Check configured credential profiles |
| `aliyun configure` | Interactive credential configuration (use outside of skill session) |

### Plugin Management

| Command | Description |
|---------|-------------|
| `aliyun plugin update` | Update all CLI plugins to latest versions |
| `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |

---

## Global Flags

These flags work with all `aliyun ebs` commands:

| Flag | Description | Example |
|------|-------------|---------|
| `--cli-dry-run` | Print request without sending API call | `--cli-dry-run` |
| `--cli-query` | Filter output with JMESPath | `--cli-query "DataList[0].Datapoints"` |
| `--endpoint` | Override service endpoint | `--endpoint https://ebs.cn-hangzhou.aliyuncs.com` |
| `--log-level` | Set log level (DEBUG, INFO, WARN, ERROR) | `--log-level DEBUG` |
| `--pager, --all-pages` | Merge pages for pageable APIs | `--pager` |
| `-q, --quiet` | Suppress output | `-q` |
| `--region` | Override region ID | `--region cn-shanghai` |
| `-h, --help` | Show command help | `-h` |

---

## Complementary Commands (Not in This Skill)

These related EBS commands may be useful for extended analysis:

| Product | CLI Command | Description |
|---------|------------|-------------|
| EBS | `aliyun ebs describe-disks` | List and describe cloud disks |
| EBS | `aliyun ebs describe-disk-replica-pairs` | Query disk replica pairs |
| EBS | `aliyun ebs describe-disk-replica-groups` | Query disk replica groups |
| ECS | `aliyun ecs describe-disks` | Describe ECS-attached disks |
| ECS | `aliyun ecs describe-instances` | List ECS instances (to get DiskId associations) |

---

## Command Validation

All commands in this document have been validated using:
```bash
aliyun ebs describe-metric-data --help
```

Verification Date: 2024-01-15
CLI Version: 3.3.2+

---

## Reference

- [Alibaba Cloud CLI Documentation](https://www.alibabacloud.com/help/en/cli)
- [EBS API Reference](https://api.aliyun.com/api/ebs/2021-07-30)
- [OpenAPI Explorer - DescribeMetricData](https://api.aliyun.com/api/ebs/2021-07-30/DescribeMetricData)
