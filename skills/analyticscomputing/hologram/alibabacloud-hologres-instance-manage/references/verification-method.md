# Success Verification Method

This document provides detailed verification steps to confirm successful execution of Hologres instance management operations.

## Scenario Goal Verification

### Task 1: Verify ListInstances Operation

**Expected Outcome**: Successfully retrieve a list of all Hologres instances in the account.

**Verification Command:**
```bash
# Execute ListInstances and verify response
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators:**
1. HTTP status code is `200`
2. Response contains `"Success": "true"` or `"Success": true`
3. `InstanceList` field is present (may be empty array if no instances exist)
4. No `ErrorCode` or `ErrorMessage` in response

**Verification Script:**
```bash
#!/bin/bash
# Verify ListInstances operation

RESPONSE=$(aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills 2>&1)

# Check if response contains success indicator
if echo "$RESPONSE" | grep -q '"Success"'; then
  SUCCESS=$(echo "$RESPONSE" | grep -o '"Success"[[:space:]]*:[[:space:]]*[^,}]*' | head -1)
  if echo "$SUCCESS" | grep -qiE 'true'; then
    echo "✅ ListInstances: SUCCESS"
    # Count instances
    COUNT=$(echo "$RESPONSE" | grep -o '"InstanceId"' | wc -l)
    echo "   Found $COUNT instance(s)"
  else
    echo "❌ ListInstances: FAILED"
    echo "   Response: $RESPONSE"
  fi
else
  echo "❌ ListInstances: ERROR"
  echo "   Response: $RESPONSE"
fi
```

---

### Task 2: Verify GetInstance Operation

**Expected Outcome**: Successfully retrieve detailed information about a specific Hologres instance.

**Prerequisites:**
- You must have a valid instance ID (obtain from ListInstances first)

**Verification Command:**
```bash
# First, get an instance ID from ListInstances
INSTANCE_ID=$(aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills \
  | grep -o '"InstanceId":"[^"]*"' | head -1 | cut -d'"' -f4)

# Then verify GetInstance with that ID
if [ -n "$INSTANCE_ID" ]; then
  aliyun hologram GET /api/v1/instances/$INSTANCE_ID \
    --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
fi
```

**Success Indicators:**
1. HTTP status code is `200`
2. Response contains `"Success": true`
3. `Instance` object is present with detailed fields
4. `Instance.InstanceId` matches the requested ID
5. `Instance.InstanceStatus` field is present

**Verification Script:**
```bash
#!/bin/bash
# Verify GetInstance operation

# Get first instance ID
INSTANCE_ID=$(aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills 2>/dev/null \
  | grep -o '"InstanceId":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$INSTANCE_ID" ]; then
  echo "⚠️  No instances found to verify GetInstance"
  exit 0
fi

echo "Testing GetInstance with ID: $INSTANCE_ID"

RESPONSE=$(aliyun hologram GET /api/v1/instances/$INSTANCE_ID \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills 2>&1)

# Check for success
if echo "$RESPONSE" | grep -q '"Success"[[:space:]]*:[[:space:]]*true'; then
  echo "✅ GetInstance: SUCCESS"
  
  # Extract key fields
  NAME=$(echo "$RESPONSE" | grep -o '"InstanceName":"[^"]*"' | cut -d'"' -f4)
  STATUS=$(echo "$RESPONSE" | grep -o '"InstanceStatus":"[^"]*"' | cut -d'"' -f4)
  TYPE=$(echo "$RESPONSE" | grep -o '"InstanceType":"[^"]*"' | cut -d'"' -f4)
  
  echo "   Instance Name: $NAME"
  echo "   Status: $STATUS"
  echo "   Type: $TYPE"
else
  echo "❌ GetInstance: FAILED"
  echo "   Response: $RESPONSE"
fi
```

---

## Complete Verification Suite

Run all verifications in sequence:

```bash
#!/bin/bash
# Complete verification suite for Hologres Instance Management skill

echo "=========================================="
echo "Hologres Instance Management Verification"
echo "=========================================="
echo ""

# Step 1: Verify credentials
echo "Step 1: Checking credentials..."
if aliyun configure list | grep -q "AK\|STS"; then
  echo "✅ Credentials configured"
else
  echo "❌ No valid credentials found"
  exit 1
fi
echo ""

# Step 2: Verify ListInstances
echo "Step 2: Testing ListInstances..."
RESPONSE=$(aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills 2>&1)

if echo "$RESPONSE" | grep -qiE '"Success"[[:space:]]*:[[:space:]]*"?true'; then
  echo "✅ ListInstances: SUCCESS"
  INSTANCE_COUNT=$(echo "$RESPONSE" | grep -o '"InstanceId"' | wc -l)
  echo "   Found $INSTANCE_COUNT instance(s)"
  
  # Get first instance ID for GetInstance test
  INSTANCE_ID=$(echo "$RESPONSE" | grep -o '"InstanceId":"[^"]*"' | head -1 | cut -d'"' -f4)
else
  echo "❌ ListInstances: FAILED"
  echo "$RESPONSE"
  exit 1
fi
echo ""

# Step 3: Verify GetInstance (if instances exist)
if [ -n "$INSTANCE_ID" ]; then
  echo "Step 3: Testing GetInstance with ID: $INSTANCE_ID..."
  RESPONSE=$(aliyun hologram GET /api/v1/instances/$INSTANCE_ID \
    --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills 2>&1)
  
  if echo "$RESPONSE" | grep -qiE '"Success"[[:space:]]*:[[:space:]]*true'; then
    echo "✅ GetInstance: SUCCESS"
    STATUS=$(echo "$RESPONSE" | grep -o '"InstanceStatus":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "   Instance Status: $STATUS"
  else
    echo "❌ GetInstance: FAILED"
    echo "$RESPONSE"
  fi
else
  echo "Step 3: Skipped (no instances to test GetInstance)"
fi
echo ""

echo "=========================================="
echo "Verification Complete"
echo "=========================================="
```

---

## Error Scenarios and Resolution

### Permission Denied

**Symptom:**
```json
{
  "ErrorCode": "NoPermission",
  "ErrorMessage": "RAM user permission is insufficient, please grant AliyunHologresReadOnlyAccess permission."
}
```

**Resolution:**
1. Grant `hologram:ListInstances` and `hologram:GetInstance` permissions
2. Or attach `AliyunHologresReadOnlyAccess` system policy

### Instance Not Found

**Symptom:**
```json
{
  "ErrorCode": "InstanceNotFound",
  "ErrorMessage": "Instance does not exist"
}
```

**Resolution:**
1. Verify the instance ID is correct
2. Check if the instance exists in the specified region
3. Use ListInstances to get valid instance IDs

### Invalid Credentials

**Symptom:**
```json
{
  "ErrorCode": "InvalidAccessKeyId.NotFound",
  "ErrorMessage": "Specified access key is not found"
}
```

**Resolution:**
1. Run `aliyun configure list` to check current configuration
2. Reconfigure credentials with valid access keys
3. Verify the access key is active in RAM Console

---

## Automated Health Check

Add this to your monitoring scripts:

```bash
#!/bin/bash
# Health check for Hologres API access

check_hologres_api() {
  local result
  result=$(aliyun hologram POST /api/v1/instances \
    --header "Content-Type=application/json" \
    --body '{}' \
    --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills 2>&1)
  
  if echo "$result" | grep -qiE '"Success"[[:space:]]*:[[:space:]]*"?true'; then
    return 0
  else
    return 1
  fi
}

if check_hologres_api; then
  echo "Hologres API: OK"
  exit 0
else
  echo "Hologres API: FAILED"
  exit 1
fi
```
