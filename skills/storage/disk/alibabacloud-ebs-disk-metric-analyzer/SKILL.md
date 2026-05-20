---
name: alibabacloud-ebs-disk-metric-analyzer
description: |
  Alibaba Cloud EBS Disk Monitoring and Metric Analysis Skill. Query and analyze monitoring metrics for single or multiple cloud disks, supporting time-series aggregation and cross-disk analysis.
  Triggers: "EBS monitoring", "disk metrics", "cloud disk performance", "IOPS analysis", "BPS analysis", "disk monitoring data", "metric aggregation".
---

# Alibaba Cloud EBS Disk Monitoring and Metric Analysis

This skill enables you to query and analyze monitoring metrics for Alibaba Cloud Elastic Block Storage (EBS) disks. It supports querying single or multiple disks, performing time-series aggregation, and cross-disk metric analysis.

## Scenario Description

Monitor and analyze cloud disk performance metrics to:
- Track disk IOPS (read/write operations per second)
- Monitor disk bandwidth (BPS - bytes per second)
- Analyze disk performance trends over time
- Compare performance across multiple disks
- Aggregate metrics by disk type, instance, or availability zone
- Identify performance bottlenecks and optimization opportunities

**Architecture**: EBS Monitoring Service + Cloud Monitor + EBS Disks (System/Data Disks)

**Supported Metrics**:
- `disk_bps_percent` - Disk bandwidth utilization percentage
- `disk_iops_percent` - Disk IOPS utilization percentage
- `disk_read_block_size` - Average read block size
- `disk_read_bps` - Read bandwidth (bytes per second)
- `disk_read_iops` - Read IOPS
- `disk_write_block_size` - Average write block size
- `disk_write_bps` - Write bandwidth (bytes per second)
- `disk_write_iops` - Write IOPS

**Aggregation Capabilities**:
- **Time Dimension**: SUM, COUNT, AVG, MAX, MIN over time periods
- **Cross-Disk Dimension**: Aggregate metrics across multiple disks by SUM, AVG, COUNT, MAX, MIN
- **Grouping**: Group by DiskId, DeviceType, DeviceCategory, EcsInstanceId, or Availability Zone

---

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

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

---

## RAM Policy

This skill requires the following Alibaba Cloud RAM permissions. See `references/ram-policies.md` for the complete permission policy.

**Required API Permissions**:
- `ebs:DescribeMetricData` - Query disk monitoring metrics

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, DiskId, MetricName, time ranges,
> aggregation methods, etc.) MUST be confirmed with the user. Do NOT assume or use
> default values without explicit user approval.

### Required and Optional Parameters

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| `--metric-name` | **Required** | Metric to query (e.g., disk_read_iops, disk_write_bps) | N/A |
| `--biz-region-id` | **Required** | Region ID (e.g., cn-hangzhou, cn-shanghai) | N/A |
| `--start-time` | Optional | Query start time in ISO 8601 format (yyyy-MM-ddTHH:mm:ssZ) | Last period if both start/end empty |
| `--end-time` | Optional | Query end time in ISO 8601 format (yyyy-MM-ddTHH:mm:ssZ) | Current time |
| `--period` | Optional | Data granularity in seconds (5, 10, 60, 300, 600, 3600) | 5 |
| `--dimensions` | Optional | JSON filter for DiskId, DeviceType, DeviceCategory, EcsInstanceId, Azone | Empty (all disks) |
| `--aggre-ops` | Optional | Time aggregation method (AVG_OVER_TIME, SUM_OVER_TIME, MAX_OVER_TIME, etc.) | No aggregation |
| `--aggre-over-line-ops` | Optional | Cross-disk aggregation (NON, SUM, AVG, COUNT, MAX, MIN) | NON |
| `--group-by-labels` | Optional | Group by labels (DiskId, DeviceType, DeviceCategory, EcsInstanceId, Azone) | No grouping |

---

## Core Workflow

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-metric-analyzer"
> ```

### Scenario 1: Query Single Disk Metrics

Query read IOPS for a specific disk over the last hour:

```bash
# Confirm with user: RegionId, DiskId, MetricName, time range
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 60 \
  --dimensions "{\"DiskId\": [\"d-bp1234567890abcde\"]}" \
  --biz-region-id cn-hangzhou
```

**Expected Output**:
```json
{
  "TotalCount": 1,
  "DataList": [
    {
      "Labels": "{\"DiskId\": \"d-bp1234567890abcde\"}",
      "Datapoints": "{\"1705315200\": 150, \"1705315260\": 148, \"1705315320\": 152, ...}"
    }
  ],
  "RequestId": "11B55F58-D3A4-4A9B-9596-342420D0****"
}
```

### Scenario 2: Query Multiple Disks with Aggregation

Query average write bandwidth across multiple data disks:

```bash
# Confirm with user: RegionId, MetricName, DeviceType, aggregation method
aliyun ebs describe-metric-data \
  --metric-name disk_write_bps \
  --start-time 2024-01-15T09:00:00Z \
  --end-time 2024-01-15T10:00:00Z \
  --period 300 \
  --dimensions "{\"DeviceType\": [\"data\"]}" \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --biz-region-id cn-shanghai
```

### Scenario 3: Group Metrics by Disk Category

Analyze IOPS utilization grouped by disk category (e.g., cloud_essd):

```bash
# Confirm with user: RegionId, MetricName, grouping dimension
aliyun ebs describe-metric-data \
  --metric-name disk_iops_percent \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-15T23:59:59Z \
  --period 3600 \
  --aggre-ops MAX_OVER_TIME \
  --group-by-labels DeviceCategory \
  --biz-region-id cn-beijing
```

### Scenario 4: Compare Performance Across Availability Zones

Compare disk performance across different availability zones:

```bash
# Confirm with user: RegionId, MetricName, grouping by Azone
aliyun ebs describe-metric-data \
  --metric-name disk_bps_percent \
  --start-time 2024-01-14T00:00:00Z \
  --end-time 2024-01-15T00:00:00Z \
  --period 600 \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --group-by-labels Azone \
  --biz-region-id cn-hangzhou
```

### Scenario 5: Multi-Dimension Filtering

Query specific disks attached to specific ECS instances:

```bash
# Confirm with user: RegionId, DiskIds, EcsInstanceId
aliyun ebs describe-metric-data \
  --metric-name disk_read_bps \
  --start-time 2024-01-15T12:00:00Z \
  --end-time 2024-01-15T13:00:00Z \
  --period 60 \
  --dimensions "{\"DiskId\": [\"d-bp11111\", \"d-bp22222\"], \"EcsInstanceId\": [\"i-bp1234567890\"]}" \
  --aggre-ops AVG_OVER_TIME \
  --biz-region-id cn-shenzhen
```

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

---

## Success Verification Method

After querying metrics, verify:

1. **Response Status**: Check that `RequestId` is present (indicates successful API call)
2. **Data Presence**: Verify `DataList` contains expected entries
3. **Time Range**: Confirm `Datapoints` timestamps match the requested time range
4. **Metric Values**: Validate metric values are within expected ranges (e.g., percentages 0-100)
5. **No Warnings**: Check that `Warnings` array is empty or review any warnings

For detailed verification steps, see `references/verification-method.md`.

---

## Cleanup

This skill only queries monitoring data and does not create any resources. No cleanup is required.

---

## Best Practices

1. **Choose Appropriate Period**: Use smaller periods (5s, 10s) for short-term analysis, larger periods (300s, 3600s) for long-term trends
2. **Time Range Limits**: Respect period-specific time range limits (e.g., 5s period supports max 12 hours)
3. **Use Filters Wisely**: Apply `dimensions` filters to reduce data volume and improve query performance
4. **Aggregation Selection**: Choose aggregation methods based on analysis goals (AVG for trends, MAX for peak detection, SUM for totals)
5. **Group by Relevant Dimensions**: Group by DeviceCategory to compare disk types, by Azone for regional analysis
6. **Handle Warnings**: Review the `Warnings` array if present - it may indicate incomplete data
7. **Time Zone Awareness**: All timestamps use UTC+0 (ISO 8601 format)
8. **Batch Queries**: For multiple disks, use array filters in `dimensions` instead of multiple API calls
9. **Result Parsing**: Parse JSON `Datapoints` field to extract timestamp-value pairs programmatically
10. **Monitor Quota**: Be aware of API rate limits when querying large time ranges or many disks

---

## Reference Links

| Reference File | Description |
|---------------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | Complete RAM permission policy for EBS monitoring APIs |
| [references/related-commands.md](references/related-commands.md) | All EBS CLI commands used in this skill |
| [references/verification-method.md](references/verification-method.md) | Detailed verification steps and commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Test patterns and acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Alibaba Cloud CLI installation guide |

---

## Common Issues and Solutions

**Issue**: "InvalidParameter: The parameter MetricName is invalid"
- **Solution**: Verify metric name matches one of the 8 supported metrics exactly (case-sensitive)

**Issue**: "InvalidParameter: Period exceeds time range limit"
- **Solution**: Reduce time range or increase period granularity (e.g., use 300s instead of 5s for longer ranges)

**Issue**: Empty DataList returned
- **Solution**: Check that disks exist in the specified region and match the dimension filters

**Issue**: Incomplete data warning
- **Solution**: Metrics may not be available for all time points; adjust time range or check disk activity during the period

---

## Advanced Usage

### Using JMESPath Queries

Filter output using `--cli-query` to extract specific data:

```bash
# Extract only datapoints from first result
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  --cli-query "DataList[0].Datapoints"
```

### Combining with Other Tools

Pipe results to `jq` for advanced JSON processing:

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_write_bps \
  --dimensions "{\"DeviceType\": [\"data\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.DataList[].Datapoints | fromjson | to_entries | .[] | {timestamp: .key, value: .value}'
```

---

**For more information**:
- [Alibaba Cloud EBS Documentation](https://www.alibabacloud.com/help/en/ebs)
- [OpenAPI Explorer - DescribeMetricData](https://api.aliyun.com/api/ebs/2021-07-30/DescribeMetricData)
