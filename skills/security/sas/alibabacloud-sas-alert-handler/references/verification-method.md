# Verification Method

## Success Verification Methods

This document describes how to verify whether each step has been executed successfully.

---

## Step 1: Query Alert List Verification

### Verification Command

```bash
aliyun sas DescribeSuspEvents \
  --Lang zh \
  --From sas \
  --CurrentPage 1 \
  --PageSize 5 \
  --Levels "serious,suspicious,remind" \
  --Dealed N \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null | jq '.Count, .TotalCount'
```

### Success Indicators

- Returns JSON formatted data
- Contains `SuspEvents` array
- `Count` field shows number of items on current page
- `TotalCount` field shows total number of items

### Failure Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `NoPermission` | Missing permissions | Grant `yundun-sas:DescribeSuspEvents` permission |
| Empty array | No alerts matching criteria | Adjust query conditions (e.g., Dealed=Y to query handled alerts) |

---

## Step 2: Query Available Handling Operations Verification

### Verification Command

```bash
aliyun sas DescribeSecurityEventOperations \
  --SecurityEventId {AlertID} \
  --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null | jq '.SecurityEventOperationsResponse[] | {OperationCode, UserCanOperate}'
```

### Success Indicators

- Returns `SecurityEventOperationsResponse` array
- Each element contains `OperationCode` and `UserCanOperate`
- Operations with `UserCanOperate=true` can be executed

### Failure Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `SecurityEventNotExists` | Alert ID does not exist | Verify the alert ID is correct |
| All `UserCanOperate=false` | Version not supported | Upgrade Cloud Security Center edition |

---

## Step 3: Handling Operation Verification

### Verification Command

```bash
# Check return after handling
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 {AlertID} \
  --OperationCode {OperationCode} \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null | jq '.HandleSecurityEventsResponse.TaskId'
```

### Success Indicators

- Returns `TaskId` (non-empty number)
- No error messages

### Failure Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `NoPermission` | Missing handling permission | Grant `yundun-sas:HandleSecurityEvents` permission |
| `InvalidSecurityEventId` | Invalid alert ID | Check alert ID format |
| `OperationNotSupported` | Operation not supported | Check if `UserCanOperate` is true |

---

## Step 4: Query Handling Status Verification

### Verification Command

```bash
aliyun sas DescribeSecurityEventOperationStatus \
  --TaskId {TaskID} \
  --SecurityEventIds.1 {AlertID} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null | jq '.SecurityEventOperationStatusResponse'
```

### Success Indicators

- `TaskStatus` is `Success`
- `SecurityEventOperationStatuses[].Status` is `Success`
- `ErrorCode` format is `{Operation}.Success`

### Processing Status

If `TaskStatus=Processing`:

```bash
# Retry after 2 seconds
sleep 2
aliyun sas DescribeSecurityEventOperationStatus \
  --TaskId {TaskID} \
  --SecurityEventIds.1 {AlertID} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

### Polling Logic

```bash
#!/bin/bash
TASK_ID="290511xx"
EVENT_ID="7009607xx"
MAX_RETRY=5
RETRY=0

while [ $RETRY -lt $MAX_RETRY ]; do
  RESULT=$(aliyun sas DescribeSecurityEventOperationStatus \
    --TaskId $TASK_ID \
    --SecurityEventIds.1 $EVENT_ID \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null)
  
  STATUS=$(echo $RESULT | jq -r '.SecurityEventOperationStatusResponse.TaskStatus')
  
  if [ "$STATUS" = "Success" ] || [ "$STATUS" = "Failure" ]; then
    echo "Final status: $STATUS"
    echo $RESULT | jq '.SecurityEventOperationStatusResponse'
    break
  fi
  
  echo "Status: $STATUS, retrying in 2s..."
  sleep 2
  RETRY=$((RETRY + 1))
done

if [ $RETRY -eq $MAX_RETRY ]; then
  echo "Timeout: status still processing after ${MAX_RETRY} retries"
fi
```

---

## Handling Result Verification

### Verify Alert Status Change

After successful handling, re-query the alert to confirm status change:

```bash
aliyun sas DescribeSuspEvents \
  --Id {AlertID} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null | jq '.SuspEvents[0] | {Id, EventStatus, Dealed: (.Dealed // "unknown")}'
```

### Status Reference Table

| Handling Operation | Expected EventStatus | Description |
|--------------------|----------------------|-------------|
| ignore | 2 | Ignored |
| manual_handled | 32 | Completed |
| advance_mark_mis_info | 8 | Marked as false positive |
| mark_mis_info | 8 | Marked as false positive |
| block_ip | 32 | Completed |
| kill_and_quara | 32 or 16 | Completed or processing |

---

## Common Error Codes Summary

| ErrorCode | Meaning | Recommended Action |
|-----------|---------|--------------------|
| `ignore.Success` | Ignore successful | No action required |
| `block_ip.Success` | IP block successful | No action required |
| `kill_and_quara.Success` | Kill and quarantine successful | No action required |
| `kill_and_quara.ProcessNotExist` | Process does not exist | Use virus_quara_bin to quarantine file |
| `kill_and_quara.AgentOffline` | Client offline | Retry after client comes online |
| `advance_mark_mis_info.Success` | Whitelist successful | No action required |
| `*.Failure` | Operation failed | Check detailed error message |

---

## End-to-End Verification Script

```bash
#!/bin/bash
# End-to-end verification script

echo "=== Step 1: Query Alert List ==="
EVENTS=$(aliyun sas DescribeSuspEvents \
  --Lang zh --From sas --PageSize 5 --Dealed N \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null)

COUNT=$(echo $EVENTS | jq '.Count')
echo "Found $COUNT pending alerts"

if [ "$COUNT" -eq 0 ]; then
  echo "No pending alerts, exiting"
  exit 0
fi

# Get the first alert ID
EVENT_ID=$(echo $EVENTS | jq -r '.SuspEvents[0].Id')
echo "Selected alert ID: $EVENT_ID"

echo ""
echo "=== Step 2: Query Available Operations ==="
OPS=$(aliyun sas DescribeSecurityEventOperations \
  --SecurityEventId $EVENT_ID --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler 2>/dev/null)

echo "Available operations:"
echo $OPS | jq '.SecurityEventOperationsResponse[] | select(.UserCanOperate==true) | .OperationCode'

echo ""
echo "Verification complete! To execute handling, please manually run the HandleSecurityEvents command"
```
