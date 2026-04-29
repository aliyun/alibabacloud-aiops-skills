# Error Handling Guide

This document contains detailed error handling procedures for alert operations.

---

## Common Error Scenarios

| Error Scenario | ErrorCode | Handling Method |
|----------------|-----------|------------------|
| UserCanOperate=false | - | Inform user operation not supported, may be version limitation |
| Handling timeout (>10s) | - | Mark as failed, continue to next alert |
| Agent offline | *.AgentOffline | Inform user client is offline, cannot handle |
| Process not exist | *.ProcessNotExist | Suggest using virus_quara_bin |
| Insufficient permissions | NoPermission | Inform user to contact main account for authorization |
| Alert not exist | SecurityEventNotExists | See detailed handling process below |

---

## Alert Not Found Handling Process

When the user-provided alert ID returns no data (`DescribeSecurityEventOperations` returns `SecurityEventNotExists`), follow this process:

### Step 1: Search in handled alerts for the specified ID (Required)

> **⚠️ IMPORTANT: When user specifies an alert ID, must first search in handled alerts**

```bash
# Search for specified ID in handled alerts
aliyun sas DescribeSuspEvents \
  --Lang zh \
  --From sas \
  --CurrentPage 1 \
  --PageSize 100 \
  --Dealed Y \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null | grep -A 20 -B 5 "{AlertID}"
```

### Step 2: Result Determination

| Query Result | Handling Method |
|--------------|------------------|
| **Alert ID found** | Directly inform user alert has been handled, display handling details |
| **Alert ID not found** | Proceed to Step 3 to inform alert does not exist |

### Handled Alert Display Format
```
Alert {ID} has been handled, details:

[Alert] ID: 702173474
- Name: ECS unusual account login
- Type: Unusual Login
- Severity: suspicious
- Status: Marked as false positive (EventStatus: 8)
- Handling Time: 2026-03-24 10:30:15
- Handling Result: advance_mark_mis_info.User.Success
- Whitelist Rule: Login Source IP equals 124.115.231.154

This alert has already been handled, no repeated action needed.
```

### Step 3: Inform alert does not exist

If also not found in handled alerts, inform user the alert does not exist:
```
Alert {AlertID} does not exist. Possible reasons:

1. Alert ID entered incorrectly
2. Alert has been deleted
3. Alert has expired

Please confirm the alert ID is correct.
```

### Step 4: Display current pending alerts list

Proactively query and display current pending alerts to help user find the correct alert:

```bash
aliyun sas DescribeSuspEvents \
  --Lang zh \
  --From sas \
  --CurrentPage 1 \
  --PageSize 10 \
  --Dealed N \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null | jq '.SuspEvents[] | {Id, Name: .AlarmEventNameDisplay, Level, InternetIp, EventStatus, LastTime}'
```

Display format:
```
Current pending alerts list:

| ID | Name | Severity | Asset IP | Status | Time |
|----|------|----------|----------|--------|------|
| 7019098xx | ECS login from unusual location | suspicious | 47.110.xxx.xxx | Pending | 2026-03-23 16:26:23 |
| 6712310xx | Scorpion Virus | serious | 121.43.xxx.xxx | Pending | 2026-03-23 00:49:04 |
```

### Step 5: Guide user selection

```
Please confirm:
1. Is the alert ID correct?
2. If you need to handle an alert from the list above, please tell me the alert ID
```

---

## Handling Status ErrorCode Reference

### TaskStatus Values

| Status | Description | Next Action |
|--------|-------------|-------------|
| Pending | Waiting | Wait for processing to start |
| Processing | In progress | Wait 2 seconds and retry query |
| Success | Successful | Processing complete |
| Failure | Failed | Check ErrorCode |

### Common ErrorCode Patterns

**Success Examples:**
- `ignore.Success`
- `kill_and_quara.Success`
- `advance_mark_mis_info.Success`
- `block_ip.Success`

**Failure Examples:**
- `kill_and_quara.ProcessNotExist` - Process does not exist
- `kill_and_quara.AgentOffline` - Client offline
- `block_ip.Failure` - Block failed

---

## Polling Logic for Status Query

1. If `TaskStatus=Processing`: Wait 2 seconds and retry, maximum 5 retries
2. If still not complete after 10 seconds → Mark as failed
3. `TaskStatus=Success` and `Status=Success` → Handling successful
4. `TaskStatus=Failure` or `Status=Failed` → Handling failed

```bash
# Status query command
aliyun sas DescribeSecurityEventOperationStatus \
  --TaskId {TaskID} \
  --SecurityEventIds.1 {AlertID} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

---

## Results Summary Format

After handling is complete, display detailed results for each alert:

```
========== Handling Results Summary ==========

✅ Successfully Handled: 3 items

  [Alert 7009607xx]
  - Name: ECS login from unusual location
  - Action: Block IP
  - Result: Success
  - Details: Blocked IP 140.205.xx.xx, valid for 7 days

  [Alert 7008619xx]
  - Name: Trojan Program
  - Action: Kill and Quarantine Virus
  - Result: Success

❌ Handling Failed: 1 item

  [Alert 7008557xx]
  - Name: Virus Program
  - Action: Kill and Quarantine Virus
  - Result: Failed
  - Reason: AgentOffline (client offline)
  - Suggestion: Wait for client to come online and retry

==========================================

Total: Handled 4 items, Success 3 items, Failed 1 item
```
