# Verification Method - Elasticsearch Instance Management

This document describes how to verify the success of each operation in the Elasticsearch instance management workflow.

## Table of Contents

- [1. Verify Instance Creation](#1-verify-instance-creation)
- [2. Verify Instance Query (DescribeInstance)](#2-verify-instance-query-describeinstance)
- [3. Verify Instance List (ListInstance)](#3-verify-instance-list-listinstance)
- [4. Verify Instance Restart](#4-verify-instance-restart)
- [5. Verify List All Nodes](#5-verify-list-all-nodes)
- [6. Verify Instance Update (Upgrade/Downgrade)](#6-verify-instance-update-upgradedowngrade)
- [7. End-to-End Verification Script](#7-end-to-end-verification-script)
- [Error Handling](#error-handling)
- [References](#references)

---

## 1. Verify Instance Creation

After creating an Elasticsearch instance, verify the creation was successful:

### Step 1: Check the Creation Response

The `create-instance` command returns an `instanceId` if successful:

```json
{
  "RequestId": "838D9D11-8EEF-46D8-BF0D-BC8FC2B0C2F3",
  "Result": {
    "instanceId": "es-cn-xxx****"
  }
}
```

**Verification**: Ensure the response contains a valid `instanceId`.

### Step 2: Query Instance Status

```bash
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Status Progression:**
1. `activating` - Instance is being created
2. `active` - Instance is ready for use

### Step 3: Wait for Active Status

Poll the instance status until it becomes `active`:

```bash
# Check instance status (repeat until status is "active")
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result.status" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria:**
- Response contains `instanceId`
- Instance status transitions to `active` (may take 10-30 minutes)
- `domain` and `kibanaDomain` fields are populated

---

## 2. Verify Instance Query (DescribeInstance)

### Verification Command

```bash
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Success Criteria

1. **Response Status**: HTTP 200
2. **Required Fields Present**:
   - `instanceId`
   - `status`
   - `esVersion`
   - `domain`

### Example Verification

```bash
# Verify instance exists and check key fields
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result.{ID:instanceId,Status:status,Version:esVersion,Domain:domain}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "ID": "es-cn-xxx****",
  "Status": "active",
  "Version": "7.10_with_X-Pack",
  "Domain": "es-cn-xxx****.elasticsearch.aliyuncs.com"
}
```

---

## 3. Verify Instance List (ListInstance)

### Verification Command

```bash
aliyun elasticsearch list-instance \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Success Criteria

1. **Response Status**: HTTP 200
2. **Headers contain total count**: `X-Total-Count` field
3. **Result array**: Contains instance objects

### Example Verification

```bash
# List all instances and verify count
aliyun elasticsearch list-instance \
  --region cn-hangzhou \
  --cli-query "length(Result)" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Verify Specific Instance in List

```bash
# Check if a specific instance is in the list
aliyun elasticsearch list-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result[0].instanceId" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria:**
- Returns the expected `instanceId`
- Instance is visible in the list

---

## 4. Verify Instance Restart

### Step 1: Execute Restart

```bash
aliyun elasticsearch restart-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: Check Response

**Expected Response:**
```json
{
  "RequestId": "F99407AB-2FA9-489E-A259-40CF6DC****",
  "Result": {
    "instanceId": "es-cn-xxx****",
    "status": "active"
  }
}
```

### Step 3: Monitor Restart Progress

```bash
# Poll status until back to "active"
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result.status" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Status Progression:**
1. `activating` - Restart in progress
2. `active` - Restart complete

### Success Criteria

1. Initial response contains `RequestId`
2. Instance status changes to `activating`
3. Instance status returns to `active` after restart completes
4. Instance is accessible after restart

---

## 5. Verify List All Nodes

### Verification Command

```bash
aliyun elasticsearch list-all-node \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Success Criteria

1. **Response Status**: HTTP 200
2. **Result array**: Contains node objects with required fields
3. **Node health**: All nodes should be GREEN for healthy cluster

### Example Verification

```bash
# List all nodes with summary
aliyun elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result[].{Host:host,Type:nodeType,Health:health,CPU:cpuPercent}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
[
  {
    "Host": "10.15.XX.XX",
    "Type": "WORKER",
    "Health": "GREEN",
    "CPU": "4.2%"
  }
]
```

### Verify Node Count Matches Instance Configuration

```bash
# Get node count from instance info
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result.nodeAmount" \
  --user-agent AlibabaCloud-Agent-Skills

# Compare with actual node count (WORKER nodes)
aliyun elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "length(Result[?nodeType=='WORKER'])" \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## 6. Verify Instance Update (Upgrade/Downgrade)

### Step 1: Pre-check Instance Status

Before updating, verify the instance is in `active` status:

```bash
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --cli-query "Result.status" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: `"active"`

### Step 2: Execute Update and Check Response

**Expected Response:**
```json
{
  "RequestId": "F99407AB-2FA9-489E-A259-40CF6DC****",
  "Result": {
    "instanceId": "es-cn-xxx****",
    "status": "activating"
  }
}
```

**Verification**: Ensure the response contains `RequestId` and `Result.instanceId`.

### Step 3: Monitor Update Progress

```bash
# Poll status until back to "active"
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --cli-query "Result.{Status:status,Nodes:nodeAmount,Spec:nodeSpec}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Status Progression:**
1. `activating` - Configuration change in progress
2. `active` - Configuration change complete

### Step 4: Verify New Configuration

After the instance returns to `active`, verify the configuration has been updated:

```bash
# Check instance configuration details
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --cli-query "Result.{NodeAmount:nodeAmount,NodeSpec:nodeSpec,Master:masterConfiguration,Warm:warmNodeConfiguration,Client:clientNodeConfiguration,Kibana:kibanaConfiguration}" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Success Criteria

1. Pre-check confirms instance status is `active`
2. Update response contains `RequestId` and `Result.instanceId`
3. Instance status transitions to `activating` during update
4. Instance status returns to `active` after update completes
5. Instance configuration matches the requested changes

---

## 7. End-to-End Verification Script

Complete verification workflow:

```bash
#!/bin/bash

REGION="cn-hangzhou"
INSTANCE_ID="es-cn-xxx****"
USER_AGENT="--user-agent AlibabaCloud-Agent-Skills"

echo "=== Step 1: Verify Instance Exists ==="
aliyun elasticsearch describe-instance \
  --region $REGION \
  --instance-id $INSTANCE_ID \
  $USER_AGENT

echo ""
echo "=== Step 2: Verify Instance in List ==="
aliyun elasticsearch list-instance \
  --region $REGION \
  --instance-id $INSTANCE_ID \
  --cli-query "Result[0].{ID:instanceId,Status:status}" \
  $USER_AGENT

echo ""
echo "=== Step 3: Verify Instance Status ==="
STATUS=$(aliyun elasticsearch describe-instance \
  --region $REGION \
  --instance-id $INSTANCE_ID \
  --cli-query "Result.status" \
  $USER_AGENT | tr -d '"')

if [ "$STATUS" == "active" ]; then
  echo "✅ Instance is active and healthy"
else
  echo "⚠️ Instance status: $STATUS"
fi
```

---

## Error Handling

### Common Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `InstanceNotFound` | Instance does not exist | Verify instance ID is correct |
| `InstanceActivating` | Instance is not ready | Wait for instance to become active |
| `Forbidden.RAM` | Insufficient permissions | Check RAM policy |
| `InvalidParameter` | Invalid parameter value | Check parameter format |

### Troubleshooting Commands

```bash
# Check if CLI is configured correctly
aliyun configure list

# Test API connectivity
aliyun elasticsearch list-instance --region cn-hangzhou --size 1 --user-agent AlibabaCloud-Agent-Skills

# Debug with verbose logging
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --log-level debug \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## References

- [Elasticsearch Status Codes](https://help.aliyun.com/document_detail/64893.html)
- [Error Handling](https://help.aliyun.com/document_detail/64913.html)
