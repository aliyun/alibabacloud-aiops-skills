# Verification Methods for EBS Disk Metric Analysis

This document provides detailed verification steps to ensure successful execution of EBS disk monitoring queries.

---

## Overview

After querying disk metrics using `aliyun ebs describe-metric-data`, verify the results to ensure data accuracy and completeness.

---

## Step 1: Verify API Response Structure

### Check for Successful API Call

Every successful API response contains a `RequestId` field:

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id cn-hangzhou \
  | jq '.RequestId'
```

**Expected Output**:
```
"11B55F58-D3A4-4A9B-9596-342420D0****"
```

**If Missing**: The API call failed. Check error messages in the response.

---

## Step 2: Verify Data List Presence

### Check DataList Array

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.DataList | length'
```

**Expected Output**:
- `1` or more: Data found
- `0`: No data (disk may not exist, no activity, or dimension filters exclude all disks)

**Troubleshooting Empty DataList**:
1. Verify disk exists in the region:
   ```bash
   aliyun ecs describe-disks --region cn-hangzhou --disk-ids '["d-bp1234567890"]'
   ```
2. Check if disk was active during the time range
3. Verify dimension filters are correct

---

## Step 3: Verify Datapoints Content

### Extract and Parse Datapoints

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 60 \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.DataList[0].Datapoints | fromjson'
```

**Expected Output**:
```json
{
  "1705315200": 150,
  "1705315260": 148,
  "1705315320": 152,
  "1705315380": 145,
  ...
}
```

**Verification Checks**:
1. **Timestamps**: Unix timestamps should fall within the requested time range
2. **Metric Values**: Values should be reasonable for the metric type
3. **Data Density**: Number of datapoints should match `(end_time - start_time) / period`

### Validate Timestamp Range

```bash
# Extract first and last timestamps
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 60 \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.DataList[0].Datapoints | fromjson | keys | [first, last]'
```

**Expected**: Timestamps near or within the query range.

---

## Step 4: Verify Metric Value Ranges

### Percentage Metrics (0-100%)

For metrics ending in `_percent`:
- `disk_bps_percent`
- `disk_iops_percent`

**Validation**:
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_iops_percent \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.DataList[0].Datapoints | fromjson | to_entries | map(select(.value < 0 or .value > 100))'
```

**Expected Output**: `[]` (empty array means all values are in valid range 0-100)

### Throughput Metrics (Non-negative)

For BPS and IOPS metrics, values should be ≥ 0:

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_bps \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.DataList[0].Datapoints | fromjson | to_entries | map(select(.value < 0))'
```

**Expected Output**: `[]` (no negative values)

---

## Step 5: Verify Aggregation Results

### Time Aggregation Verification

When using `--aggre-ops`, verify aggregated values are within expected ranges:

```bash
# Query with AVG_OVER_TIME aggregation
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 60 \
  --aggre-ops AVG_OVER_TIME \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.DataList[0].Datapoints | fromjson'
```

**Check**: Aggregated values should be within the range of raw values.

### Cross-Disk Aggregation Verification

When using `--aggre-over-line-ops`, verify the result:

```bash
# Query multiple disks with AVG aggregation
aliyun ebs describe-metric-data \
  --metric-name disk_write_bps \
  --dimensions "{\"DeviceType\": [\"data\"]}" \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --biz-region-id cn-hangzhou \
  | jq '.DataList | length'
```

**Expected**:
- `1` when aggregating across all disks (no grouping)
- `N` when grouping by a dimension (N = number of unique values in that dimension)

---

## Step 6: Verify Group By Results

### Check Grouping Labels

When using `--group-by-labels`, verify each group has correct labels:

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_iops_percent \
  --period 300 \
  --group-by-labels DeviceCategory \
  --biz-region-id cn-hangzhou \
  | jq '.DataList[].Labels | fromjson'
```

**Expected Output**:
```json
{"DeviceCategory": "cloud_essd"}
{"DeviceCategory": "cloud_ssd"}
{"DeviceCategory": "cloud_efficiency"}
```

**Verification**: Each Labels object should contain the grouped field(s).

---

## Step 7: Check for Warnings

### Review Warnings Array

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-15T23:59:59Z \
  --period 5 \
  --dimensions "{\"DiskId\": [\"d-bp1234567890\"]}" \
  --biz-region-id cn-hangzhou \
  | jq '.Warnings'
```

**Common Warnings**:
- `"not complete."` - Data may be incomplete for some time points
- Typically occurs when:
  - Disk was inactive during part of the time range
  - Data collection was interrupted
  - Requested time range is very recent (data not yet fully aggregated)

**Action**:
- If warnings appear, verify data completeness by checking for gaps in timestamps
- Consider adjusting time range or accepting partial data

---

## Step 8: Verify Total Count

### Check TotalCount Field

```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels DiskId \
  --biz-region-id cn-hangzhou \
  | jq '.TotalCount'
```

**Expected**:
- Should match `DataList` array length
- Indicates total number of result series returned

**Verification**:
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --group-by-labels DiskId \
  --biz-region-id cn-hangzhou \
  | jq '[.TotalCount, (.DataList | length)] | .[0] == .[1]'
```

**Expected Output**: `true`

---

## Step 9: End-to-End Verification Script

### Complete Verification Example

```bash
#!/bin/bash

METRIC_NAME="disk_read_iops"
DISK_ID="d-bp1234567890"
REGION="cn-hangzhou"
START_TIME="2024-01-15T10:00:00Z"
END_TIME="2024-01-15T11:00:00Z"
PERIOD=60

echo "=== Querying EBS Metric Data ==="
RESPONSE=$(aliyun ebs describe-metric-data \
  --metric-name "$METRIC_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period "$PERIOD" \
  --dimensions "{\"DiskId\": [\"$DISK_ID\"]}" \
  --biz-region-id "$REGION")

echo "$RESPONSE" | jq .

echo ""
echo "=== Verification Results ==="

# Check 1: RequestId present
REQUEST_ID=$(echo "$RESPONSE" | jq -r '.RequestId')
if [ "$REQUEST_ID" != "null" ] && [ -n "$REQUEST_ID" ]; then
  echo "✅ RequestId present: $REQUEST_ID"
else
  echo "❌ RequestId missing - API call failed"
  exit 1
fi

# Check 2: DataList not empty
DATA_COUNT=$(echo "$RESPONSE" | jq '.DataList | length')
if [ "$DATA_COUNT" -gt 0 ]; then
  echo "✅ DataList contains $DATA_COUNT series"
else
  echo "⚠️  DataList is empty - no data found"
fi

# Check 3: Datapoints present
if [ "$DATA_COUNT" -gt 0 ]; then
  DATAPOINTS=$(echo "$RESPONSE" | jq -r '.DataList[0].Datapoints')
  POINT_COUNT=$(echo "$DATAPOINTS" | jq 'fromjson | length')
  echo "✅ Datapoints contains $POINT_COUNT time series values"
fi

# Check 4: Warnings
WARNINGS=$(echo "$RESPONSE" | jq -r '.Warnings // [] | length')
if [ "$WARNINGS" -eq 0 ]; then
  echo "✅ No warnings"
else
  echo "⚠️  $WARNINGS warning(s) present:"
  echo "$RESPONSE" | jq -r '.Warnings[]'
fi

# Check 5: TotalCount matches DataList
TOTAL_COUNT=$(echo "$RESPONSE" | jq '.TotalCount')
if [ "$TOTAL_COUNT" -eq "$DATA_COUNT" ]; then
  echo "✅ TotalCount ($TOTAL_COUNT) matches DataList length ($DATA_COUNT)"
else
  echo "⚠️  TotalCount ($TOTAL_COUNT) does not match DataList length ($DATA_COUNT)"
fi

echo ""
echo "=== Verification Complete ==="
```

**Usage**:
```bash
chmod +x verify-metric-query.sh
./verify-metric-query.sh
```

---

## Common Issues and Verification

| Issue | Verification Command | Expected Result |
|-------|---------------------|-----------------|
| Empty DataList | `jq '.DataList \| length'` | `> 0` |
| Missing Datapoints | `jq '.DataList[0].Datapoints \| fromjson \| length'` | `> 0` |
| Out-of-range timestamps | `jq '.DataList[0].Datapoints \| fromjson \| keys'` | Timestamps within query range |
| Invalid percentage values | `jq '.DataList[0].Datapoints \| fromjson \| to_entries \| map(select(.value < 0 or .value > 100))'` | `[]` for `*_percent` metrics |
| Negative values | `jq '.DataList[0].Datapoints \| fromjson \| to_entries \| map(select(.value < 0))'` | `[]` |
| Warnings present | `jq '.Warnings'` | `null` or `[]` |
| TotalCount mismatch | `jq '[.TotalCount, (.DataList \| length)]'` | Both values equal |

---

## Reference

- [EBS DescribeMetricData API Documentation](https://api.aliyun.com/api/ebs/2021-07-30/DescribeMetricData)
- [JMESPath Tutorial](https://jmespath.org/tutorial.html)
- [jq Manual](https://stedolan.github.io/jq/manual/)
