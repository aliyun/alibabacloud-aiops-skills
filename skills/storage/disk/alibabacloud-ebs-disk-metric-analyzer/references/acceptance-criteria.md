# Acceptance Criteria: alibabacloud-ebs-disk-metric-analyzer

**Scenario**: EBS Disk Monitoring and Metric Analysis
**Purpose**: Skill testing acceptance criteria and validation patterns

---

## Correct CLI Command Patterns

### 1. Product Name Verification

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops
```
- Product name is `ebs` (lowercase)
- Product exists in Aliyun CLI

#### ❌ INCORRECT
```bash
aliyun EBS describe-metric-data --metric-name disk_read_iops
```
- **Error**: Product names are case-sensitive and must be lowercase
- **Fix**: Use `ebs` not `EBS`

```bash
aliyun elastic-block-storage describe-metric-data --metric-name disk_read_iops
```
- **Error**: Product name is `ebs`, not the full service name
- **Fix**: Use `ebs` not `elastic-block-storage`

---

### 2. Command/Action Verification

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops
```
- Action is `describe-metric-data` (plugin mode: lowercase with hyphens)
- Matches the API `DescribeMetricData` (PascalCase converted to kebab-case)

#### ❌ INCORRECT
```bash
aliyun ebs DescribeMetricData --metric-name disk_read_iops
```
- **Error**: Using API-style PascalCase instead of plugin mode kebab-case
- **Fix**: Use `describe-metric-data` not `DescribeMetricData`

```bash
aliyun ebs get-metric-data --metric-name disk_read_iops
```
- **Error**: Action name does not exist
- **Fix**: Use `describe-metric-data` not `get-metric-data`

```bash
aliyun ebs query-metric-data --metric-name disk_read_iops
```
- **Error**: Action name does not exist
- **Fix**: Use `describe-metric-data` not `query-metric-data`

---

### 3. Required Parameter Verification

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id cn-hangzhou
```
- `--metric-name` is present (required parameter)
- Valid metric name from the allowed list

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data --biz-region-id cn-hangzhou
```
- **Error**: Missing required parameter `--metric-name`
- **Fix**: Add `--metric-name` with a valid metric name

```bash
aliyun ebs describe-metric-data --metric disk_read_iops
```
- **Error**: Parameter name is `--metric-name` not `--metric`
- **Fix**: Use `--metric-name` not `--metric`

---

### 4. Parameter Name Verification

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 60 \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --group-by-labels DiskId \
  --biz-region-id cn-hangzhou
```
- All parameter names match `--help` output exactly
- Uses kebab-case (hyphens between words)

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --startTime 2024-01-15T10:00:00Z \
  --endTime 2024-01-15T11:00:00Z
```
- **Error**: Using camelCase parameter names instead of kebab-case
- **Fix**: Use `--start-time` and `--end-time`, not `--startTime` and `--endTime`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --region-id cn-hangzhou
```
- **Error**: Parameter is `--biz-region-id` not `--region-id`
- **Fix**: Use `--biz-region-id`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimension "{\"DiskId\": [\"d-bp1234567890\"]}"
```
- **Error**: Parameter is `--dimensions` (plural) not `--dimension`
- **Fix**: Use `--dimensions` with an 's'

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --aggregation AVG_OVER_TIME
```
- **Error**: Parameter is `--aggre-ops` not `--aggregation`
- **Fix**: Use `--aggre-ops` for time aggregation

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by DiskId
```
- **Error**: Parameter is `--group-by-labels` not `--group-by`
- **Fix**: Use `--group-by-labels`

---

### 5. Metric Name Values

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops
aliyun ebs describe-metric-data --metric-name disk_write_bps
aliyun ebs describe-metric-data --metric-name disk_bps_percent
aliyun ebs describe-metric-data --metric-name disk_iops_percent
aliyun ebs describe-metric-data --metric-name disk_read_block_size
aliyun ebs describe-metric-data --metric-name disk_write_block_size
```
- All values are from the 8 allowed metric names
- Exact case-sensitive match

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data --metric-name DISK_READ_IOPS
```
- **Error**: Metric names are case-sensitive (lowercase)
- **Fix**: Use `disk_read_iops` not `DISK_READ_IOPS`

```bash
aliyun ebs describe-metric-data --metric-name disk_iops
```
- **Error**: Metric name does not exist
- **Fix**: Use `disk_read_iops` or `disk_write_iops` or `disk_iops_percent`

```bash
aliyun ebs describe-metric-data --metric-name read_iops
```
- **Error**: Metric name does not exist
- **Fix**: Use `disk_read_iops` (includes "disk_" prefix)

---

### 6. Time Format Verification

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z
```
- ISO 8601 format: `yyyy-MM-ddTHH:mm:ssZ`
- Uses UTC+0 timezone (Z suffix)

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time "2024-01-15 10:00:00"
```
- **Error**: Not ISO 8601 format (missing 'T' separator and 'Z' timezone)
- **Fix**: Use `2024-01-15T10:00:00Z`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 1705315200
```
- **Error**: Unix timestamp not accepted (requires ISO 8601 string)
- **Fix**: Convert to `2024-01-15T10:00:00Z`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00+08:00
```
- **Error**: Must use UTC+0 (Z), not other timezones
- **Fix**: Convert to UTC and use `2024-01-15T02:00:00Z`

---

### 7. Period Value Verification

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 5
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 10
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 60
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 300
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 600
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 3600
```
- All values are from the allowed list: 5, 10, 60, 300, 600, 3600

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 30
```
- **Error**: 30 is not an allowed period value
- **Fix**: Use 60 (closest allowed value)

```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 1800
```
- **Error**: 1800 is not an allowed period value
- **Fix**: Use 600 or 3600

```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --period "60s"
```
- **Error**: Period must be integer, not string with unit
- **Fix**: Use `60` not `"60s"`

---

### 8. Dimensions JSON Format

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}"

aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions "{\"DiskId\": [\"d-bp111\", \"d-bp222\"], \"DeviceType\": [\"data\"]}"

aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions "{\"DeviceCategory\": [\"cloud_essd\"]}"
```
- JSON format with escaped quotes in shell
- Array values (even for single item)
- Valid dimension keys: DiskId, DeviceType, DeviceCategory, EcsInstanceId, Azone

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions '{"DiskId": "d-bp1234567890"}'
```
- **Error**: Value must be array, not string
- **Fix**: Use `{"DiskId": ["d-bp1234567890"]}`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions {"DiskId": ["d-bp1234567890"]}
```
- **Error**: JSON must be quoted in shell
- **Fix**: Use `"{\"DiskId\": [\"d-bp1234567890\"]}"`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions "{\"disk_id\": [\"d-bp1234567890\"]}"
```
- **Error**: Dimension key is case-sensitive (should be `DiskId` not `disk_id`)
- **Fix**: Use `DiskId` (PascalCase)

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions "{\"VolumeId\": [\"d-bp1234567890\"]}"
```
- **Error**: Invalid dimension key (`VolumeId` not supported)
- **Fix**: Use `DiskId`, not `VolumeId`

---

### 9. Aggregation Operator Values

#### ✅ CORRECT
```bash
# Time aggregation
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-ops AVG_OVER_TIME
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-ops SUM_OVER_TIME
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-ops MAX_OVER_TIME
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-ops MIN_OVER_TIME
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-ops COUNT_OVER_TIME

# Cross-disk aggregation
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-over-line-ops AVG
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-over-line-ops SUM
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-over-line-ops MAX
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-over-line-ops MIN
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-over-line-ops COUNT
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-over-line-ops NON
```
- All values match allowed enum values exactly

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-ops AVERAGE
```
- **Error**: Use `AVG_OVER_TIME` not `AVERAGE`
- **Fix**: Use one of the allowed values: SUM_OVER_TIME, COUNT_OVER_TIME, AVG_OVER_TIME, MAX_OVER_TIME, MIN_OVER_TIME

```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-over-line-ops NONE
```
- **Error**: Use `NON` not `NONE`
- **Fix**: Use `NON` for no aggregation

```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --aggre-ops avg_over_time
```
- **Error**: Values are case-sensitive (must be uppercase)
- **Fix**: Use `AVG_OVER_TIME` not `avg_over_time`

---

### 10. Group By Labels Values

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels DiskId

aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels DeviceType

aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels DeviceCategory

aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels EcsInstanceId

aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels Azone

# Multiple labels (space-separated)
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels DiskId DeviceType
```
- Valid label names: DiskId, DeviceType, DeviceCategory, EcsInstanceId, Azone
- Multiple labels separated by spaces (not commas)

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels disk_id
```
- **Error**: Label names are case-sensitive (PascalCase)
- **Fix**: Use `DiskId` not `disk_id`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels InstanceId
```
- **Error**: Label name is `EcsInstanceId` not `InstanceId`
- **Fix**: Use `EcsInstanceId`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels "DiskId,DeviceType"
```
- **Error**: Multiple labels should be space-separated, not comma-separated
- **Fix**: Use `--group-by-labels DiskId DeviceType`

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels Region
```
- **Error**: `Region` is not a valid group-by label
- **Fix**: Use one of: DiskId, DeviceType, DeviceCategory, EcsInstanceId, Azone

---

### 11. Region ID Format

#### ✅ CORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --biz-region-id cn-hangzhou
aliyun ebs describe-metric-data --metric-name disk_read_iops --biz-region-id cn-shanghai
aliyun ebs describe-metric-data --metric-name disk_read_iops --biz-region-id cn-beijing
aliyun ebs describe-metric-data --metric-name disk_read_iops --biz-region-id ap-southeast-1
aliyun ebs describe-metric-data --metric-name disk_read_iops --biz-region-id us-west-1
```
- Valid Alibaba Cloud region IDs
- Format: `{area}-{location}` or `{area}-{location}-{number}`

#### ❌ INCORRECT
```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --biz-region-id hangzhou
```
- **Error**: Missing country prefix
- **Fix**: Use `cn-hangzhou` not `hangzhou`

```bash
aliyun ebs describe-metric-data --metric-name disk_read_iops --biz-region-id cn_hangzhou
```
- **Error**: Region IDs use hyphens, not underscores
- **Fix**: Use `cn-hangzhou` not `cn_hangzhou`

---

## Response Validation Patterns

### 1. Successful Response Structure

#### ✅ CORRECT Response
```json
{
  "TotalCount": 1,
  "DataList": [
    {
      "Labels": "{\"DiskId\": \"d-bp1234567890\"}",
      "Datapoints": "{\"1705315200\": 150, \"1705315260\": 148}"
    }
  ],
  "RequestId": "11B55F58-D3A4-4A9B-9596-342420D0****"
}
```
- Contains `RequestId` (always present on success)
- `TotalCount` matches `DataList` length
- `Labels` is JSON string (needs parsing)
- `Datapoints` is JSON string with timestamp-value pairs

#### ❌ INCORRECT Interpretation
```json
{
  "Code": "InvalidParameter",
  "Message": "The parameter MetricName is invalid."
}
```
- **Error**: This is an error response, not success
- **Check**: Verify metric name is from allowed list

---

### 2. Empty Results vs. Errors

#### ✅ CORRECT (Empty but Valid)
```json
{
  "TotalCount": 0,
  "DataList": [],
  "RequestId": "11B55F58-D3A4-4A9B-9596-342420D0****"
}
```
- Valid response with no data (disk doesn't exist or no activity)

#### ❌ ERROR Response
```json
{
  "Code": "Forbidden",
  "Message": "User is not authorized to operate."
}
```
- Permission error - check RAM policies

---

## Common Error Patterns and Fixes

| Error Code | Cause | Fix |
|------------|-------|-----|
| `InvalidParameter: The parameter MetricName is invalid` | Wrong metric name | Use one of 8 allowed metric names |
| `InvalidParameter.Format` | Wrong parameter format | Check ISO 8601 time format, JSON format |
| `MissingParameter: metric-name` | Required parameter missing | Add `--metric-name` |
| `Forbidden` | Missing RAM permissions | Grant `ebs:DescribeMetricData` permission |
| `InvalidApi.NotFound` | Wrong product/action name | Use `ebs describe-metric-data` |
| `RequestTimeout` | Query too large | Reduce time range or increase period |

---

## Testing Checklist

Before considering the skill complete, verify:

- [ ] Command uses plugin mode format (`describe-metric-data`, not `DescribeMetricData`)
- [ ] Product name is lowercase (`ebs`)
- [ ] All parameter names match `--help` output exactly
- [ ] Required parameter `--metric-name` is present
- [ ] Metric names are from allowed list of 8 metrics
- [ ] Time format is ISO 8601 with UTC+0 (Z suffix)
- [ ] Period values are from allowed list (5, 10, 60, 300, 600, 3600)
- [ ] Dimensions JSON uses escaped quotes and array values
- [ ] Dimension keys are PascalCase (DiskId, not disk_id)
- [ ] Aggregation operators match allowed enum values exactly
- [ ] Group-by labels are PascalCase and space-separated
- [ ] Region IDs use standard Alibaba Cloud format
- [ ] Response contains RequestId on success
- [ ] Empty DataList is handled gracefully

---

## Reference

- [Alibaba Cloud CLI Documentation](https://www.alibabacloud.com/help/en/cli)
- [EBS DescribeMetricData API](https://api.aliyun.com/api/ebs/2021-07-30/DescribeMetricData)
- Command verification: `aliyun ebs describe-metric-data --help`
