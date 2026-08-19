# Verification Methods for EBS Monitoring Skill

Detailed verification steps to ensure successful execution of EBS monitoring operations.

## General Verification Checklist

After any EBS monitoring API call, verify the following:

### 1. Response Status

**Check**: `RequestId` is present in the response.

```bash
# Verify RequestId exists
echo $response | jq -e '.RequestId'
```

**Expected**: A non-empty string like `"11B55F58-D3A4-4A9B-9596-342420D0****"`.

**If missing**: The API call failed. Check the error message and follow error handling procedures.

---

### 2. Data Presence

**Check**: `DataList` (for metrics) or `Datas` (for reports) contains expected entries.

```bash
# For describe-metric-data
echo $response | jq '.DataList | length'
# Expected: > 0

# For get-report
echo $response | jq '.Datas | length'
# Expected: > 0 (after CloudLens is enabled for 10+ minutes)
```

**If empty**:
- For metrics: Widen the dimension filter or check the time range
- For reports: Ensure CloudLens for EBS is enabled and has been active for at least 10 minutes

---

### 3. Time Range Alignment

**Check**: `Datapoints` timestamps match the requested time range.

```bash
# Extract first and last timestamps
echo $response | jq '.DataList[0].Datapoints | keys | [first, last]'
# Expected: Timestamps within [StartTime, EndTime]
```

**Note**: Timestamps are Unix epoch seconds. Convert to human-readable:
```bash
date -d @1705315200  # Linux
date -r 1705315200    # macOS
```

---

### 4. Metric Value Validation

**Check**: Metric values are within expected ranges.

| Metric | Expected Range | Notes |
|--------|----------------|-------|
| `disk_bps_percent` | 0-100 | Percentage |
| `disk_iops_percent` | 0-100 | Percentage |
| `disk_read_bps` | >= 0 | Bytes per second |
| `disk_write_bps` | >= 0 | Bytes per second |
| `disk_read_iops` | >= 0 | Operations per second |
| `disk_write_iops` | >= 0 | Operations per second |

```bash
# Check for percentage metrics within 0-100
echo $response | jq '.DataList[].Datapoints | from_entries | to_entries[].value | select(. < 0 or . > 100)'
# Expected: No output (all values valid)
```

---

### 5. Warning Review

**Check**: `Warnings` array is empty or review any warnings.

```bash
echo $response | jq '.Warnings'
# Expected: [] or array of warning messages
```

**If warnings present**: Review the warning messages — they may indicate incomplete data or other issues.

---

## Cross-Check Report vs Raw Data — Business-Level Consistency Audit

**[MUST]** Before delivering any report, recompute every quantitative claim against the raw API payload.

### Audit Checklist

1. **Disk Count Verification**
   - Locate the disk-count card by its `Datas[].Title` and read its `Data[]` series
   - Verify the reported value matches the newest `DataPoints` timestamp of that series, not an arbitrary one
   - Check week-over-week trend calculation

2. **Capacity Verification**
   - Locate the capacity card by `Title` (note: verified titles use `size`, not `capacity`) and confirm the unit you state (TiB vs GiB) matches what the card represents
   - Check trend calculation

3. **Category Distribution Verification**
   - For a percentage breakdown, group the series by timestamp and verify each timestamp's total is ~100% (allow rounding tolerance) — do **not** sum values taken from different timestamps
   - Check that `Labels` values (e.g. `cloud_essd`, `cloud_essd_entry`, `cloud_auto`, `local_ssd_pro`) match the categories you report

4. **Time Alignment Verification**
   - Verify all `DataPoints` keys are Unix **seconds** within the report period
   - A series may be missing days entirely; when you quote a "current" figure, state the timestamp it came from and use the same timestamp across series

5. **Aggregation Verification**
   - If aggregating across multiple disks, verify the aggregation logic
   - Check SUM/AVG/MAX/MIN operations are correctly applied

### Verification Commands

```bash
# Verify a card's series and its latest values
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  | jq '.Datas[] | select(.Title == "<title>") | .Data[]
        | {label: .Labels, latest: (.DataPoints | to_entries | max_by(.key | tonumber) | .value)}'

# Verify a percentage breakdown sums to ~100% at EVERY timestamp
# Group by timestamp first — series end on different days, so summing each
# series' own latest value produces a bogus total.
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  | jq -r '.Datas[] | select(.Title == "disk_count_percent_by_category")
           | [.Data[] | .DataPoints | to_entries[]] | group_by(.key)
           | map({date: (.[0].key | tonumber | strftime("%Y-%m-%d")),
                  series: length, total: (map(.value) | add)})[]
           | "\(.date) series=\(.series) total=\(.total)"'
# Expected: every total ~100 (allow 99-101 for rounding)
```

> Verified against a live response: cards are identified by `Datas[].Title`, series live at `Datas[].Data[]`, `Labels` is a real JSON object, and `DataPoints` keys are Unix **seconds**. Expressions that read `Datas[].DataPoints` return nothing.
>
> **Series are sparse and end on different days.** In the verified payload the `local_ssd_pro` series stopped two days before `cloud_essd`. Summing each series' own newest value therefore yielded 104.54 instead of ~100 — a false discrepancy. Always group by timestamp before comparing or summing series.

**Rule**: If any quantitative claim in the report does not match the raw data, **do NOT publish the report**. Regenerate or correct the report.

---

## Retry Discipline Audit — Mechanical Trace Check

**[MUST]** FAIL the run if the trace contains >= 3 consecutive `describe-metric-data` calls without the Hard Stop sentinel between call #2 and call #3.

### Audit Procedure

1. **Count consecutive API calls** for the same metric query
2. **Check for Hard Stop output** between retry #2 and retry #3
3. **Verify Parameter Confirmation gate** was re-entered after Hard Stop

### Trace Validation

```bash
# Count describe-metric-data calls in session
grep -c "aliyun ebs describe-metric-data" session_log.txt

# Check for Hard Stop template
grep -c "Hard Stop" session_log.txt

# Check for Parameter Confirmation re-entry
grep -c "Parameter Confirmation" session_log.txt
```

### Rules

- **1st call**: Initial query
- **2nd call (retry #1)**: Allowed with adjustment announcement
- **3rd call (retry #2)**: Allowed with both adjustments applied
- **4th call (retry #3)**: **FORBIDDEN** unless Hard Stop was output and user re-confirmed

**Violation**: A 3rd silent retry (4th call) without Hard Stop = workflow failure.

---

## Scenario-Specific Verification

### Scenario 1-5: Disk Metrics Queries

After querying metrics:

1. Verify `RequestId` present
2. Verify `DataList` has entries matching the dimension filter
3. Parse `Datapoints` and verify timestamp range
4. Check metric values are reasonable (no negative IOPS, percentages 0-100)
5. If aggregation was requested, verify aggregation was applied

### Scenario 6-8: Resource Overview Reports

After retrieving reports:

1. Verify `RequestId` present
2. Verify `Datas` array is not empty (after CloudLens warmup)
3. Iterate through `Datas[]` and, for each card, verify:
   - a non-empty `Title` identifying the card
   - each `Data[]` series carries a `Labels` object and a `DataPoints` map keyed by Unix seconds
4. Cross-check quantitative claims (see Cross-Check Audit above)

### Scenario 9: Dashboard Navigation

After providing dashboard URLs:

1. Verify URLs are correctly formatted
2. Verify URLs point to the correct console pages:
   - CloudMonitor → Product Monitoring → Block Storage
   - ECS Console → EBS Lens → Resource Overview
   - ECS Console → EBS Lens → Disk Analysis
3. If optional summary was retrieved, verify it matches Scenario 6 verification steps

---

## Failure Indicators

The following indicate a failed verification:

| Indicator | Action |
|-----------|--------|
| Missing `RequestId` | API call failed — check error handling |
| Empty `DataList` with valid `RequestId` | No data — widen filter or check time range |
| Empty `Datas` with valid `RequestId` | CloudLens not ready — wait or verify enabled |
| Metric values outside expected range | Data quality issue — review and potentially re-query |
| Timestamps outside requested range | Time alignment issue — re-query with correct range |
| >= 3 retries without Hard Stop | **Workflow failure** — retry discipline violated |
| Report claims don't match raw data | **Do NOT publish** — cross-check failed |

---

## Verification Scripts

### Full Metric Query Verification

```bash
#!/bin/bash
# Verify a describe-metric-data response

response=$(cat)  # Read from stdin

# 1. Check RequestId
request_id=$(echo "$response" | jq -r '.RequestId')
if [ "$request_id" = "null" ] || [ -z "$request_id" ]; then
  echo "FAIL: Missing RequestId"
  exit 1
fi

# 2. Check DataList
data_count=$(echo "$response" | jq '.DataList | length')
if [ "$data_count" -eq 0 ]; then
  echo "WARN: Empty DataList"
fi

# 3. Check for warnings
warnings=$(echo "$response" | jq '.Warnings | length')
if [ "$warnings" -gt 0 ]; then
  echo "WARN: $warnings warning(s) present"
  echo "$response" | jq '.Warnings'
fi

echo "PASS: Basic verification passed"
```

### Report Verification

```bash
#!/bin/bash
# Verify a get-report response

response=$(cat)  # Read from stdin

# 1. Check RequestId
request_id=$(echo "$response" | jq -r '.RequestId')
if [ "$request_id" = "null" ] || [ -z "$request_id" ]; then
  echo "FAIL: Missing RequestId"
  exit 1
fi

# 2. Check Datas
datas_count=$(echo "$response" | jq '.Datas | length')
if [ "$datas_count" -eq 0 ]; then
  echo "WARN: Empty Datas (CloudLens may not be ready)"
fi

# 3) Verify each card has a title and at least one series with data
echo "$response" | jq -e '[.Datas[] | select(.Title == null or ([.Data[]? | select((.DataPoints | length) > 0)] | length) == 0)] | length == 0' > /dev/null || {
  echo "FAIL: some report cards lack a Title or carry no data points"
  exit 1
}

echo "PASS: Report verification passed"
```
