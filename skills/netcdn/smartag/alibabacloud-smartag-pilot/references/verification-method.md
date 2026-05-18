# Verification Method: alibabacloud-smartag-pilot

Post-execution verification steps to confirm the skill ran correctly.

---

## Configuration Query Verification

### Step 1: API Response Validity

Verify that API calls returned valid JSON and no network/timeout errors:

```bash
# Quick connectivity test - should return JSON with Regions (plugin mode)
aliyun smartag describe-regions \
  --endpoint smartag.cn-shanghai.aliyuncs.com \
  --read-timeout 30 \
  --connect-timeout 15
```

**Expected**: JSON response containing `Regions.Region[]` array.
**Failure indicators**: timeout, connection refused, non-JSON output.

### Step 2: Instance Count Verification

After querying all regions, verify total instance count matches console:

```bash
# Count instances per region (plugin mode)
aliyun smartag describe-smart-access-gateways \
  --endpoint smartag.<RegionId>.aliyuncs.com \
  --biz-region-id <RegionId> \
  --page-size 50
```

**Check**: `TotalCount` in response should match the report summary.

### Step 3: Report File Existence

```bash
# Verify report file was generated
ls -la <workspace>/SAG_*.md
```

**Expected**: File exists, size > 0, recent modification timestamp.

---

## Status Inspection Verification (状态巡检)

### Step 1: Coverage Check

All applicable inspection items should have a result (green/yellow/red). Missing items indicate API failures that should be noted in the report.

### Step 2: Status Cross-Validation

```bash
# Verify device online status matches console (plugin mode)
aliyun smartag describe-smart-access-gateways \
  --endpoint smartag.<RegionId>.aliyuncs.com \
  --biz-region-id <RegionId> \
  --smart-ag-id <sag-id>
```

**Check**: `Status` field in response matches the inspection result.

### Step 3: Report Completeness

Inspection report should contain:
- Instance identifier and region
- Inspection timestamp
- Overall status classification
- Summary counts (normal/attention/critical)
- Details for each non-green item
- Recommendations section

---

## Common Verification Failures

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Zero instances returned | Wrong region or expired instances | Verify RegionId, check console |
| Missing device info in report | Instance has no bound device (empty SN) | Expected for unbound hardware/software instances |
| Partial API failures in batch | Rate limiting or transient errors | Re-run; check for Throttling errors in output |
| Report file not found | Workspace path incorrect | Check output_path variable |
