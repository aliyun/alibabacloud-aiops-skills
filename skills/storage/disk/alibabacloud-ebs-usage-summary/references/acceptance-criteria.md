# Acceptance Criteria for EBS Monitoring Skill

Testing acceptance criteria for the `alibabacloud-ebs-usage-summary` skill.

---

## Correct CLI Command Patterns

### 1. Product — Verify `ebs` exists

✅ **CORRECT**
```bash
aliyun ebs describe-metric-data --help
aliyun ebs get-report --help
aliyun ebs list-reports --help
```

❌ **INCORRECT**
```bash
aliyun ecs describe-disks  # Wrong product for EBS monitoring metrics
aliyun cms describe-metric-list  # CloudMonitor API, not EBS-specific
```

---

### 2. Commands — Verify action names

All `aliyun ebs` commands run in **plugin mode**: lowercase-hyphenated command names and flags.

✅ **CORRECT**
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id> \
  --period 60

aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default

aliyun ebs list-reports \
  --biz-region-id <region-id> \
  --page-size 10
```

❌ **INCORRECT**
```bash
aliyun ebs describe_metric_data  # Underscores instead of hyphens
aliyun ebs get_report  # Underscores instead of hyphens
aliyun ebs getreport  # Missing hyphen separator
```

---

### 3. Parameters — Verify each parameter exists

#### describe-metric-data Parameters

✅ **CORRECT**
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id> \
  --start-time <start-time> \
  --end-time <end-time> \
  --period 60 \
  --dimensions '{"DiskId": ["<disk-id>"]}' \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --group-by-labels DiskId
```

> `--dimensions` values stay PascalCase because they are **JSON payload keys** defined by the API, not CLI flags.

❌ **INCORRECT**
```bash
aliyun ebs describe-metric-data \
  --metricName disk_read_iops \  # camelCase flag not supported
  --region-id <region-id> \  # Should be --biz-region-id
  --starttime <start-time>  # Should be --start-time
```

#### get-report Parameters

All three `ebs` commands take the region as `--biz-region-id` (the CLI reserves the bare `--region` global flag for endpoint overrides).

✅ **CORRECT**
```bash
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type history \
  --report-id <report-id>
```

❌ **INCORRECT**
```bash
aliyun ebs get-report \
  --region-id <region-id> \  # Should be --biz-region-id
  --type present \  # Should be --report-type
  --app default  # Should be --app-name
```

---

## Correct Metric Names

✅ **CORRECT** (8 supported metrics)
- `disk_bps_percent`
- `disk_iops_percent`
- `disk_read_block_size`
- `disk_read_bps`
- `disk_read_iops`
- `disk_write_block_size`
- `disk_write_bps`
- `disk_write_iops`

❌ **INCORRECT**
- `disk_read_ops` (should be `disk_read_iops`)
- `disk_write_ops` (should be `disk_write_iops`)
- `disk_throughput` (should be `disk_read_bps` or `disk_write_bps`)
- `disk_utilization` (should be `disk_bps_percent` or `disk_iops_percent`)

---

## Correct Dimension Filters

Dimension keys are API JSON keys and stay PascalCase. Replace every `<...>` with a real resolved identifier.

✅ **CORRECT**
```json
{"DiskId": ["<disk-id>"]}
{"DeviceType": ["data", "system"]}
{"DeviceCategory": ["cloud_essd", "cloud_essd_entry"]}
{"EcsInstanceId": ["<instance-id>"]}
{"Azone": ["<zone-id>"]}
{"DiskId": ["<disk-id-1>", "<disk-id-2>"], "DeviceType": ["data"]}
```

❌ **INCORRECT**
```json
{"diskId": ["<disk-id>"]}  # Lowercase 'd' in key
{"DiskId": "<disk-id>"}  # Should be array, not string
{"disk_id": ["<disk-id>"]}  # Wrong key format
```

---

## Correct Aggregation Methods

### Time Aggregation (--aggre-ops)

✅ **CORRECT**
- `AVG_OVER_TIME`
- `SUM_OVER_TIME`
- `MAX_OVER_TIME`
- `MIN_OVER_TIME`
- `COUNT_OVER_TIME`

❌ **INCORRECT**
- `AVERAGE` (should be `AVG_OVER_TIME`)
- `SUM` (should be `SUM_OVER_TIME` for time dimension)
- `avg_over_time` (must be uppercase)

### Cross-Disk Aggregation (--aggre-over-line-ops)

✅ **CORRECT**
- `NON` (no aggregation)
- `SUM`
- `AVG`
- `COUNT`
- `MAX`
- `MIN`

❌ **INCORRECT**
- `NONE` (should be `NON`)
- `AVERAGE` (should be `AVG`)
- `sum` (must be uppercase)

---

## Correct Time Formats

✅ **CORRECT** (ISO 8601)
```
2024-01-15T10:00:00Z
2024-01-15T10:00:00+08:00
2024-01-15T02:00:00Z
```

❌ **INCORRECT**
```
2024-01-15 10:00:00  # Missing 'T' and timezone
2024/01/15T10:00:00Z  # Slashes instead of hyphens
Jan 15, 2024 10:00  # Wrong format
1705312800  # Unix timestamp (should be ISO 8601)
```

---

## Correct Period Values

✅ **CORRECT**
- `5` (5 seconds, max 12 hours range)
- `10` (10 seconds, max 24 hours range)
- `60` (1 minute, max 7 days range)
- `300` (5 minutes, max 30 days range)
- `600` (10 minutes, max 30 days range)
- `3600` (1 hour, max 30 days range)

❌ **INCORRECT**
- `1` (not supported)
- `30` (not supported)
- `120` (not supported)
- `900` (not supported, use `600` or `3600`)

---

## Correct Report Type Values

✅ **CORRECT**
- `present` (latest report)
- `history` (specific historical report, requires `--report-id`)

❌ **INCORRECT**
- `latest` (should be `present`)
- `current` (should be `present`)
- `historical` (should be `history`)

---

## Scenario Acceptance Tests

### Scenario 1: Query Single Disk Metrics

**Test Case**: Query read IOPS for a specific disk over the last hour.

✅ **CORRECT Command**
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id> \
  --start-time <start-time> \
  --end-time <end-time> \
  --period 60 \
  --dimensions '{"DiskId": ["<disk-id>"]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

**Expected**: Returns DataList with Datapoints for the specified disk.

---

### Scenario 6: Get Latest Resource Overview Report

**Test Case**: Fetch the most recent weekly resource overview.

✅ **CORRECT Command**
```bash
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

**Expected**: Returns a `Datas` array of report cards; each card wraps a `Data[]` array of series, and each series carries a `Labels` object plus a `DataPoints` map keyed by Unix seconds.

---

### Scenario 7: List Historical Reports

**Test Case**: List previously generated weekly reports.

✅ **CORRECT Command**
```bash
aliyun ebs list-reports \
  --biz-region-id <region-id> \
  --page-size 10 \
  --page-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

**Expected**: Returns HistoryReports array with ReportId, ReportTime, etc.

---

### Scenario 9: Monitoring Dashboard Quick View

**Test Case**: Provide console dashboard URLs.

✅ **CORRECT Output**
```
| Dashboard | URL | Description |
|-----------|-----|-------------|
| CloudMonitor — EBS Monitoring | https://cloudmonitor.console.aliyun.com/ | Real-time monitoring |
| ECS Console — EBS Lens Resource Overview | https://ecs.console.aliyun.com/ | Weekly overview |
| ECS Console — EBS Lens Disk Analysis | https://ecs.console.aliyun.com/ | Per-disk analysis |
```

**Expected**: URLs are correctly formatted and point to valid console pages.

---

## Anti-Patterns to Avoid

### 1. Silent Retry Without Adjustment

❌ **INCORRECT**
```bash
# First call times out
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 5 --start-time ... --end-time ...
# Retry with same parameters (FORBIDDEN)
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 5 --start-time ... --end-time ...
```

✅ **CORRECT**
```bash
# First call times out
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 5 --start-time ... --end-time ...
# Retry with adjustment (shorter window or larger period)
echo "Original query timed out, retrying with period=60..."
aliyun ebs describe-metric-data --metric-name disk_read_iops --period 60 --start-time ... --end-time ...
```

---

### 2. Hardcoding User-Specific Parameters

❌ **INCORRECT**
```bash
aliyun ebs describe-metric-data \
  --biz-region-id cn-hangzhou \  # Region assumed without user confirmation
  --dimensions '{"DiskId": ["d-example"]}'  # Disk ID copied from documentation
```

✅ **CORRECT**
```bash
# First, emit the parameter checklist with the values derived from the user's request:
# "Please confirm: RegionId=<region from request>, DiskId=<resolved id>, MetricName=<requested metric>"
# Then execute after confirmation, substituting the confirmed values
```

---

### 3. Missing --user-agent

❌ **INCORRECT**
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id>
# Missing --user-agent
```

✅ **CORRECT**
```bash
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

---

### 4. Using a Non-Plugin Invocation Form

❌ **INCORRECT**
```bash
aliyun ebs get_report --biz-region-id <region-id>  # Underscores in command name
aliyun ebs describe-metric-data --metricName disk_read_iops  # camelCase flag
```

✅ **CORRECT**
```bash
aliyun ebs get-report --biz-region-id <region-id>
aliyun ebs describe-metric-data --metric-name disk_read_iops
```

---

## Summary

| Category | Key Points |
|----------|------------|
| **Product** | Use `ebs`, not `ecs` or `cms` |
| **Invocation Mode** | Plugin mode only — lowercase-hyphenated commands (`describe-metric-data`, `get-report`, `list-reports`) |
| **Parameters** | Lowercase-hyphenated flags (`--biz-region-id`, `--biz-region-id`, `--report-type`); only `--dimensions` JSON keys stay PascalCase |
| **Metrics** | 8 supported metrics (disk_read_iops, disk_write_bps, etc.) |
| **Time Format** | ISO 8601: `yyyy-MM-ddTHH:mm:ssZ` |
| **Periods** | 5, 10, 60, 300, 600, 3600 seconds |
| **Observability** | Always include `--user-agent` with session-id |
| **Parameter Confirmation** | Always confirm with user before execution |
| **Placeholders** | Never ship a documentation `<...>` value or sample ID to a real call |
