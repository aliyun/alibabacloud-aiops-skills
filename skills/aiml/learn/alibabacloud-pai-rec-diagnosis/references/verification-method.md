# Verification Methods

This document provides detailed verification procedures to confirm successful execution of PAI-Rec Engine Diagnosis and Configuration Validation operations.

## Workflow 1: Engine Interface Diagnosis Verification

### Step 1: Verify Service Information Retrieval

**Command:**
```bash
aliyun eas describe-service \
  --cluster-id <cluster-id> \
  --service-name <service-name>
```

**Success Criteria:**
- ✅ Command returns HTTP 200 status
- ✅ Response contains valid JSON structure
- ✅ `ServiceName` matches input
- ✅ `Resource` field is present and non-empty
- ✅ `ServiceConfig` contains environment variables

**What to Check:**
```json
{
  "ServiceName": "embedding_recall",
  "Resource": "eas-r-1v4qb1yan3qmnjwxqe",
  "ServiceConfig": {
    "envs": {
      "REGION": "cn-hangzhou",
      "INSTANCE_ID": "pairec-cn-xxxxx",
      "CONFIG_NAME": "my_config",
      "PAIREC_ENVIRONMENT": "product"
    }
  }
}
```

**Failure Indicators:**
- ❌ Service not found error
- ❌ Missing Resource field
- ❌ Empty ServiceConfig
- ❌ Missing required environment variables

---

### Step 2: Verify Request ID Extraction

**Manual Check:**

From API response JSON:
```json
{
    "code": 299,
    "msg": "items size not enough",
    "request_id": "941b4e14-d1c5-489f-a184-b2b17f8b4fdb",
    "size": 0,
    "items": []
}
```

**Success Criteria:**
- ✅ `request_id` field exists in response
- ✅ `request_id` is a valid UUID or identifier format
- ✅ Value is non-empty

**Common Formats:**
- UUID: `941b4e14-d1c5-489f-a184-b2b17f8b4fdb`
- Custom ID: May vary by implementation

---

### Step 3: Verify Service Log Retrieval

**Command:**
```bash
aliyun eas describe-service-log \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  --keyword <request-id> \
  --start-time <start-time-utc> \
  --end-time <end-time-utc>
```

**Success Criteria:**
- ✅ Command completes without errors
- ✅ Returns log entries array
- ✅ At least one log entry contains the request_id
- ✅ Logs are within specified time range

**Expected Response Structure:**
```json
{
  "Logs": [
    "2025-04-28 08:15:23 [INFO] request_id=941b4e14-d1c5-489f-a184-b2b17f8b4fdb ...",
    "2025-04-28 08:15:23 [ERROR] request_id=941b4e14-d1c5-489f-a184-b2b17f8b4fdb items size not enough"
  ],
  "TotalCount": 2,
  "PageNum": 1
}
```

**Verification Steps:**

1. **Check log count:**
   ```bash
   # Expected: TotalCount > 0
   ```

2. **Verify keyword match:**
   ```bash
   # Each log entry should contain the request_id
   grep "941b4e14-d1c5-489f-a184-b2b17f8b4fdb"
   ```

3. **Check timestamp range:**
   ```bash
   # Log timestamps should be between start-time and end-time
   ```

**Failure Indicators:**
- ❌ Empty Logs array (no matching logs found)
- ❌ Request ID not found in any log entry
- ❌ All logs outside time range
- ❌ Permission denied errors

**Troubleshooting:**
- If no logs found, expand time window
- Verify request_id format matches exactly
- Check service name is correct
- Ensure logs haven't been rotated/deleted

---

### Step 4: Verify Engine Configuration List Retrieval

**Command:**
```bash
aliyun pairecservice list-engine-configs \
  --instance-id <instance-id> \
  --environment <Prod|Pre> \
  --status Released \
  --name <config-name>
```

**Success Criteria:**
- ✅ Returns list of configurations
- ✅ At least one config with `Status: Released`
- ✅ Environment matches request
- ✅ Config name matches (if specified)

**Expected Response:**
```json
{
  "EngineConfigs": [
    {
      "EngineConfigId": "config-12345",
      "Name": "my_config",
      "Version": "v1.2.3",
      "Status": "Released",
      "Environment": "Prod",
      "GmtCreateTime": "2025-04-20T10:00:00Z"
    }
  ],
  "TotalCount": 1
}
```

**Verification Checks:**

1. **Status verification:**
   ```bash
   # Ensure Status = "Released"
   ```

2. **Environment mapping:**
   ```bash
   # Service "product" → Config "Prod"
   # Service "prepub" → Config "Pre"
   ```

3. **Multiple versions:**
   ```bash
   # If multiple configs, select latest by GmtCreateTime
   ```

**Failure Indicators:**
- ❌ No configurations found
- ❌ All configs in Draft/Archived status
- ❌ Environment mismatch
- ❌ Empty EngineConfigs array

---

### Step 5: Verify Configuration Details Retrieval

**Command:**
```bash
aliyun pairecservice get-engine-config \
  --instance-id <instance-id> \
  --engine-config-id <config-id>
```

**Success Criteria:**
- ✅ Returns configuration object
- ✅ `ConfigValue` field is present
- ✅ ConfigValue contains valid JSON/YAML
- ✅ All metadata fields populated

**Expected Response:**
```json
{
  "EngineConfig": {
    "EngineConfigId": "config-12345",
    "Name": "my_config",
    "Version": "v1.2.3",
    "ConfigValue": "{\"recall\": [...], \"rank\": [...]}",
    "Status": "Released",
    "Environment": "Prod"
  }
}
```

**Verification Checks:**

1. **ConfigValue parsing:**
   ```bash
   # Verify valid JSON/YAML format
   echo "$CONFIG_VALUE" | jq .
   ```

2. **Required sections:**
   - Recall configurations
   - Ranking configurations
   - Filter settings
   - Scene definitions

**Failure Indicators:**
- ❌ Config not found
- ❌ Empty ConfigValue
- ❌ Invalid JSON/YAML format
- ❌ Missing required sections

---

### Step 6: Verify Comprehensive Analysis

**Manual Verification:**

The comprehensive analysis should include:

1. **API Response Analysis:**
   - ✅ Error code identified and explained
   - ✅ Error message interpreted
   - ✅ Response data structure analyzed

2. **Log Analysis:**
   - ✅ Request trace found in logs
   - ✅ Processing flow identified
   - ✅ Error location pinpointed
   - ✅ Stack trace (if available) analyzed

3. **Configuration Analysis:**
   - ✅ Relevant config sections identified
   - ✅ Settings affecting behavior explained
   - ✅ Potential misconfigurations highlighted

4. **Root Cause Identification:**
   - ✅ Primary cause determined
   - ✅ Contributing factors listed
   - ✅ Evidence from logs/config provided

5. **Recommendations:**
   - ✅ Specific fixes suggested
   - ✅ Configuration changes proposed
   - ✅ Prevention measures recommended

**Quality Checklist:**
- [ ] All three components (API response, logs, config) analyzed
- [ ] Clear explanation of the issue
- [ ] Specific evidence cited
- [ ] Actionable recommendations provided
- [ ] Related configuration sections highlighted

---

## Workflow 2: Configuration Validation Verification

### Step 1: Verify Configuration Version Listing

**Command:**
```bash
aliyun pairecservice list-engine-configs \
  --instance-id <instance-id> \
  --environment <Prod|Pre> \
  --name <config-name>
```

**Success Criteria:**
- ✅ Returns list of all versions
- ✅ Each version has required metadata
- ✅ Versions sorted (typically by creation time)
- ✅ User can select appropriate version

**Expected Display:**
```
Available Versions:
1. Version: v1.3.0 | Status: Released | Created: 2025-04-28 | ID: config-30000
2. Version: v1.2.3 | Status: Released | Created: 2025-04-20 | ID: config-12345
3. Version: v1.2.2 | Status: Archived | Created: 2025-04-10 | ID: config-11111
```

**Verification Points:**
- ✅ All versions displayed
- ✅ Status clearly shown
- ✅ Timestamps readable
- ✅ IDs provided for selection

---

### Step 2: Verify Configuration Validation Execution

**Success Criteria:**
- ✅ Configuration retrieved successfully
- ✅ All validation checks executed
- ✅ Results clearly categorized
- ✅ Issues prioritized appropriately

**Expected Validation Output Structure:**

```
✅ Structure Validation: PASSED
  - Valid JSON format
  - All required fields present
  - Correct data types

⚠️  Configuration Logic: WARNINGS (2)
  - Recall limit set to 1000 (recommended: 500 for better performance)
  - Filter threshold 0.1 may be too permissive

❌ Resource References: ERRORS (1)
  - Table 'user_features_v2' not accessible in Prod environment

✅ Performance Settings: PASSED
  - Timeout: 500ms (within recommended range)
  - Concurrency: 10 (appropriate)

⚠️  Environment Consistency: WARNINGS (1)
  - Using Pre environment model endpoint in Prod config
```

**Validation Categories:**

1. **Structure Validation:**
   - [ ] JSON/YAML syntax valid
   - [ ] Schema compliance checked
   - [ ] Required fields verified
   - [ ] Data types validated

2. **Configuration Logic:**
   - [ ] Recall settings analyzed
   - [ ] Ranking logic validated
   - [ ] Filter rules checked
   - [ ] Scene configurations verified

3. **Resource References:**
   - [ ] Table names validated
   - [ ] Feature availability checked
   - [ ] Model endpoints verified
   - [ ] OSS paths validated

4. **Performance Settings:**
   - [ ] Timeout values reasonable
   - [ ] Concurrency limits appropriate
   - [ ] Cache settings optimal
   - [ ] Batch sizes validated

5. **Environment Consistency:**
   - [ ] Config matches target environment
   - [ ] No cross-environment references
   - [ ] Resource availability verified

---

### Step 3: Verify Validation Results Quality

**Quality Metrics:**

1. **Completeness:**
   - ✅ All config sections analyzed
   - ✅ All validation checks executed
   - ✅ No sections skipped

2. **Clarity:**
   - ✅ Issues clearly described
   - ✅ Severity levels assigned
   - ✅ Evidence provided

3. **Actionability:**
   - ✅ Specific problems identified
   - ✅ Recommendations provided
   - ✅ Fix steps suggested

4. **Accuracy:**
   - ✅ No false positives
   - ✅ Critical issues flagged
   - ✅ Context considered

**Validation Report Checklist:**
- [ ] Summary section (pass/warning/error counts)
- [ ] Detailed findings for each category
- [ ] Specific line/section references
- [ ] Recommendations for each issue
- [ ] Priority/severity indicators

---

## Overall Success Verification

### For Diagnosis Workflow

**Complete Checklist:**
- [ ] Service information retrieved successfully
- [ ] Request ID extracted from API response
- [ ] Service logs queried successfully
- [ ] Relevant log entries found (request_id matched)
- [ ] Engine configuration list retrieved
- [ ] Specific configuration details obtained
- [ ] Comprehensive analysis performed
- [ ] Root cause identified
- [ ] Recommendations provided

**Time Tracking:**
- Service info: < 5 seconds
- Log query: < 30 seconds
- Config retrieval: < 10 seconds
- Total workflow: < 2 minutes

---

### For Validation Workflow

**Complete Checklist:**
- [ ] Configuration versions listed
- [ ] User selected or provided version ID
- [ ] Configuration details retrieved
- [ ] All validation categories checked
- [ ] Issues categorized by severity
- [ ] Recommendations generated
- [ ] Report formatted clearly

**Time Tracking:**
- List versions: < 5 seconds
- Get config: < 5 seconds
- Validation: < 30 seconds
- Total workflow: < 1 minute

---

## Common Verification Failures

### Issue: No Logs Found

**Symptoms:**
- Empty Logs array
- TotalCount = 0

**Debugging Steps:**
1. Verify request_id format exactly matches
2. Expand time window (try ±2 hours)
3. Remove keyword filter and search all logs
4. Check if logs have been rotated
5. Verify service name and cluster ID

**Resolution:**
```bash
# Try without keyword first
aliyun eas describe-service-log \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  --start-time <start-time> \
  --end-time <end-time>
```

---

### Issue: Configuration Not Found

**Symptoms:**
- Empty EngineConfigs array
- "Config not found" error

**Debugging Steps:**
1. List all configs without filters
2. Verify instance ID is correct
3. Check environment mapping (product→Prod)
4. Verify config name spelling
5. Check if config was deleted

**Resolution:**
```bash
# List all configs to verify
aliyun pairecservice list-engine-configs \
  --instance-id <instance-id>
```

---

### Issue: Invalid ConfigValue

**Symptoms:**
- JSON parsing error
- Empty ConfigValue
- Malformed YAML

**Debugging Steps:**
1. Check ConfigValue is not null
2. Verify encoding (UTF-8)
3. Test JSON/YAML parsing separately
4. Check for escape characters
5. Verify complete response received

**Resolution:**
```bash
# Save and validate separately
aliyun pairecservice get-engine-config \
  --instance-id <instance-id> \
  --engine-config-id <config-id> \
  > config.json

# Validate JSON
jq . config.json
```

---

## Automated Verification Script

For automated verification, use this script structure:

```bash
#!/bin/bash

# Verification script for PAI-Rec diagnosis workflow

CLUSTER_ID="cn-hangzhou"
SERVICE_NAME="embedding_recall"
REQUEST_ID="941b4e14-d1c5-489f-a184-b2b17f8b4fdb"
INSTANCE_ID="pairec-cn-xxxxx"

echo "=== Step 1: Verify Service Info ==="
SERVICE_INFO=$(aliyun eas describe-service \
  --cluster-id "$CLUSTER_ID" \
  --service-name "$SERVICE_NAME")

if echo "$SERVICE_INFO" | jq -e '.Resource' > /dev/null; then
  echo "✅ Service info retrieved"
else
  echo "❌ Failed to get service info"
  exit 1
fi

echo "=== Step 2: Verify Logs ==="
LOGS=$(aliyun eas describe-service-log \
  --cluster-id "$CLUSTER_ID" \
  --service-name "$SERVICE_NAME" \
  --keyword "$REQUEST_ID")

LOG_COUNT=$(echo "$LOGS" | jq -r '.TotalCount // 0')
if [ "$LOG_COUNT" -gt 0 ]; then
  echo "✅ Found $LOG_COUNT log entries"
else
  echo "❌ No logs found"
  exit 1
fi

echo "=== Step 3: Verify Config ==="
CONFIGS=$(aliyun pairecservice list-engine-configs \
  --instance-id "$INSTANCE_ID" \
  --status Released)

CONFIG_COUNT=$(echo "$CONFIGS" | jq -r '.EngineConfigs | length')
if [ "$CONFIG_COUNT" -gt 0 ]; then
  echo "✅ Found $CONFIG_COUNT configurations"
else
  echo "❌ No configurations found"
  exit 1
fi

echo "=== All Verifications Passed ==="
```

---

## Related Documentation

- [Related Commands](related-commands.md) - CLI command reference
- [RAM Policies](ram-policies.md) - Permission requirements
- [Troubleshooting Guide](troubleshooting-guide.md) - Common issues and solutions
