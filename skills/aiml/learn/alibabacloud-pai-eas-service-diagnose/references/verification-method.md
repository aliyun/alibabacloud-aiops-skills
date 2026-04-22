# Verification Method

This document describes how to verify that PAI-EAS service diagnosis is executed correctly.

## Diagnosis Verification Flow

### Step 1: Verify Service Status Query

```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Response JSON contains `Status`, `RunningInstance`, `TotalInstance` fields
- Status value is a valid value such as `Running`, `Creating`, `Failed`

### Step 2: Verify Event Query

```bash
aliyun eas describe-service-event \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Response JSON contains `Events` array
- Each event contains `Time`, `Type`, `Reason`, `Message` fields

### Step 3: Verify Log Query

```bash
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --keyword "error" \
  --limit 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Response JSON contains log content
- Keyword filtering works correctly

### Step 4: Verify Instance Status Query

```bash
aliyun eas list-service-instances \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Response JSON contains `Instances` array
- Each instance contains `InstanceId`, `Status` fields

### Step 5: Verify Diagnosis Report

```bash
aliyun eas describe-service-diagnosis \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Response JSON contains diagnostic information
- May contain `DiagnosisItems` array

---

## Diagnosis Result Verification

### Service Startup Failure Diagnosis

**Expected behavior**:
1. Query service status, get `Message` field
2. Query event list, filter `Warning` type events
3. Query logs, use `error|fail` keyword filter
4. Return diagnostic result and possible causes

**Verification points**:
- Correctly identifies service status as `Failed`
- Obtains failure reason (`Message` field)
- Returns relevant error logs

### Slow Service Response Diagnosis

**Expected behavior**:
1. Check if instance count is sufficient
2. Check instance resource utilization
3. Query slow query/timeout logs

**Verification points**:
- Returns CPU/memory utilization
- Identifies potential performance bottlenecks

### Frequent Instance Restart Diagnosis

**Expected behavior**:
1. Query `Restarted` events
2. Check container `RestartCount`
3. Query health check related logs

**Verification points**:
- Returns restart count
- Identifies restart cause (OOM, health check, etc.)

### Service Inaccessible Diagnosis

**Expected behavior**:
1. Check service status
2. Get service endpoints
3. Check gateway status

**Verification points**:
- Returns service endpoint information
- Returns gateway status

---

## Error Scenario Verification

### Service Does Not Exist

```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name non-existent-service \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Returns error message indicating service does not exist

### Insufficient Permissions

**Expected result**:
- Returns `Forbidden` or permission-related error
- Prompts user to check RAM permissions

### Invalid Region

```bash
aliyun eas describe-service \
  --cluster-id invalid-region \
  --service-name my-service \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Returns error message indicating invalid region

---

## Diagnosis Suggestion Verification

### OOMKilled Scenario

**Expected diagnosis suggestions**:
- Increase memory specification
- Check for memory leaks
- Use model quantization

### ImagePullBackOff Scenario

**Expected diagnosis suggestions**:
- Check if image address is correct
- Check image registry permissions
- Use VPC internal image address

### CrashLoopBackOff Scenario

**Expected diagnosis suggestions**:
- Check startup command
- Check dependency services
- Check configuration files

### Health Check Failure Scenario

**Expected diagnosis suggestions**:
- Increase initial delay time
- Check health check path
- Check port configuration
