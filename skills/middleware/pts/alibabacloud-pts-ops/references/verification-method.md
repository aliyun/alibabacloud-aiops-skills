# PTS Verification Methods

This document provides verification steps to confirm successful execution of PTS operations.

## 1. Verify CLI Authentication

Before executing any PTS commands, verify that CLI authentication is properly configured:

```bash
# Check CLI version (must be >= 3.3.1)
aliyun version

# Test authentication by listing regions
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Returns a list of regions without authentication errors.

## 2. Verify PTS Scenario Creation

### 2.1 Verify PTS Native Scenario Created

After creating a PTS scenario, verify it exists:

```bash
# List all PTS scenarios
aliyun pts list-pts-scene \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: The newly created scenario should appear in the `PtsSceneViewList` array.

### 2.2 Verify Scenario Details

Get detailed information about the created scenario:

```bash
# Get scenario details
aliyun pts get-pts-scene \
  --scene-id <SceneId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Returns complete scenario configuration including:
- Scene name
- API configurations (URLs, methods, headers)
- Load configuration
- Duration settings

## 3. Verify JMeter Scenario Creation

### 3.1 Verify JMeter Scenario Created

After creating a JMeter scenario, verify it exists:

```bash
# List all JMeter scenarios
aliyun pts list-open-jmeter-scenes \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: The newly created JMeter scenario should appear in the response.

### 3.2 Verify JMeter Scenario Details

Get detailed information about the created JMeter scenario:

```bash
# Get JMeter scenario details
aliyun pts get-open-jmeter-scene \
  --scene-id <SceneId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Returns complete JMeter scenario configuration including:
- Scene name
- JMX file information
- Concurrency settings
- Duration settings

## 4. Verify Stress Testing Execution

> **CRITICAL WARNING:** `start-pts-scene` may return `Success: true` even when the stress test fails to actually launch. This "false success" can occur due to:
> - Missing configuration fields (e.g., `TimeoutInSecond`, `AdvanceSetting`)
> - Target site protection blocking traffic
> - Account quota limits
> 
> **Always verify actual execution status using the methods below.**

### 4.1 Verify PTS Task Started

After starting a PTS stress testing task:

**Step 1: Check running status**
```bash
aliyun pts get-pts-scene-running-status \
  --scene-id <SceneId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Status Values:**
- `SYNCING` - Data uploading, preparing agents
- `RUNNING` - Test is actively running
- `STOPPED` - Test has stopped (check if it ran successfully or failed immediately)

**Step 2: Verify with running data (REQUIRED)**
```bash
# The --plan-id is REQUIRED and comes from start-pts-scene response
aliyun pts get-pts-scene-running-data \
  --scene-id <SceneId> \
  --plan-id <PlanId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key Indicators of Successful Execution:**
| Field | Expected Value |
|-------|----------------|
| `AliveAgents` | > 0 (agents are running) |
| `Concurrency` | Matches configured value |
| `TotalRequestCount` | > 0 and increasing |
| `TotalRealQps` | > 0 (requests being processed) |

**Indicators of Failed Execution:**
| Field | Failure Indicator |
|-------|-------------------|
| `AliveAgents` | 0 |
| `TotalRequestCount` | 0 |
| `Status` | Immediately `STOPPED` |

### 4.2 Verify JMeter Task Started

After starting a JMeter stress testing task:

```bash
# The response from start-testing-jmeter-scene includes a report ID
# Use it to check status via get-jmeter-report-details
aliyun pts get-jmeter-report-details \
  --report-id <ReportId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Returns report details showing test is in progress or completed.

## 5. Verify Stress Testing Results

### 5.1 Verify PTS Report

After the stress test completes:

```bash
# Get PTS report details
aliyun pts get-pts-report-details \
  --scene-id <SceneId> \
  --plan-id <PlanId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Returns complete report including:
- Total requests
- Average response time
- Success rate
- TPS (Transactions Per Second)
- Error details (if any)

### 5.2 Verify JMeter Report

After the JMeter test completes:

```bash
# Get JMeter report details
aliyun pts get-jmeter-report-details \
  --report-id <ReportId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Returns complete JMeter report including:
- Test duration
- Throughput
- Response times
- Error rates

## 6. Verify Scenario Deletion

### 6.1 Verify PTS Scenario Deleted

After deleting a PTS scenario:

```bash
# Try to get the deleted scenario
aliyun pts get-pts-scene \
  --scene-id <DeletedSceneId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Should return an error indicating the scenario does not exist.

### 6.2 Verify JMeter Scenario Deleted

After deleting a JMeter scenario:

```bash
# Try to get the deleted JMeter scenario
aliyun pts get-open-jmeter-scene \
  --scene-id <DeletedSceneId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Should return an error indicating the scenario does not exist.

## 7. Common Error Handling

### Authentication Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| InvalidAccessKeyId.NotFound | Access Key ID is invalid | Check and update credentials |
| SignatureDoesNotMatch | Access Key Secret is incorrect | Verify credentials |
| Forbidden.RAM | Insufficient permissions | Attach appropriate RAM policy |

### API Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| SceneNotExist | Scene ID does not exist | Verify the scene ID |
| InvalidParameter | Invalid parameter value | Check parameter format |
| QuotaExceeded | Resource quota exceeded | Contact support or upgrade |

## 8. Debug Commands

Enable debug logging to troubleshoot issues:

```bash
# Run command with debug logging
aliyun pts list-pts-scene \
  --page-number 1 \
  --page-size 10 \
  --log-level debug \
  --user-agent AlibabaCloud-Agent-Skills
```

**Output includes**: Request/response headers, body content, timestamps.
