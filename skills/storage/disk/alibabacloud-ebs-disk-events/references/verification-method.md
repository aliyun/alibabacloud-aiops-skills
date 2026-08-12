# Verification Methods for alibabacloud-ebs-disk-events

This document provides detailed verification steps after executing the `alibabacloud-ebs-disk-events` Skill.

---

## Overview

After querying cloud disk events using `aliyun ebs describe-events`, the returned results should be verified for completeness and accuracy.

---

## Step 1: Verify API Call Success

### Check RequestId

Every successful API call returns a `RequestId`:

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 1 \
  | jq -r '.RequestId'
```

**Expected Output**:

```
473469C7-AA6F-4DC5-B3DB-A3DC0DE3****
```

**If missing**: The API call failed; check the error message.

---

## Step 2: Verify Event List

### Check the ResourceEvents Array

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 10 \
  | jq '.ResourceEvents | length'
```

**Expected Output**:

- `> 0`: Events were found
- `0`: No events found (filter conditions may be too strict or no events in the time range)

**Troubleshooting Empty List**:
1. Relax filter conditions (remove `EventName`, `Status`, etc.)
2. Expand the time range
3. Confirm that cloud disk resources exist in the specified region

---

## Step 3: Verify Key Fields

### Check Single Event Fields

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --ResourceId d-bp67acfmxazb4p**** \
  | jq '.ResourceEvents[0] | keys'
```

**Expected Fields**:

```json
[
  "Description",
  "EndTime",
  "EventLevel",
  "EventName",
  "EventType",
  "ExtraAttributes",
  "RecommendAction",
  "RecommendParams",
  "ResourceId",
  "ResourceType",
  "StartTime",
  "Status"
]
```

### Check Field Value Validity

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 10 \
  | jq '.ResourceEvents[] | {EventName, EventType, EventLevel, Status, ResourceId}'
```

**Verification Points**:

- `EventName` is within the allowed value list
- `EventType` is `Notification`, `Alert`, or `SystemException`
- `EventLevel` is `INFO`, `WARN`, or `CRITICAL`
- `Status` is within the allowed value list
- `ResourceId` matches the cloud disk ID format (starts with `d-`)

---

## Step 4: Verify Time Range

### Check StartTime/EndTime

The returned timestamps are millisecond-level Unix timestamps:

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --StartTime 2024-01-15T00:00:00Z \
  --EndTime 2024-01-15T23:59:59Z \
  | jq '.ResourceEvents[] | {EventName, StartTime, EndTime}'
```

**Verification Points**:

- `StartTime` should be greater than or equal to the millisecond timestamp of the query start time
- `EndTime` should be less than or equal to the millisecond timestamp of the query end time (if the event has not ended, it may be empty or a large value)

---

## Step 5: Parse ExtraAttributes

### Extract Mounted Instance ID and Mount Point

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --ResourceId d-bp67acfmxazb4p**** \
  | jq '.ResourceEvents[0].ExtraAttributes | fromjson'
```

**Expected Output**:

```json
{
  "EcsInstanceId": "i-uf6dkn9qpcw6y94g7ag7",
  "Adapter": "hda"
}
```

**Usage**:

- `EcsInstanceId`: Locate the ECS instance to which the cloud disk is attached
- `Adapter`: Locate the mount point device name

---

## Step 6: Verify Pagination

### Check TotalCount and NextToken

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 10 \
  | jq '{TotalCount, NextToken, EventCount: (.ResourceEvents | length)}'
```

**Verification Points**:

- `TotalCount` indicates the total number of matching events
- `ResourceEvents` length does not exceed `MaxResults`
- If `NextToken` is not empty, there is more data on the next page

### Pagination Verification

```bash
# First page
RESPONSE=$(aliyun ebs describe-events --RegionId cn-hangzhou --MaxResults 10)
NEXT_TOKEN=$(echo "$RESPONSE" | jq -r '.NextToken')

# If there is a next page, continue querying
if [ "$NEXT_TOKEN" != "null" ] && [ -n "$NEXT_TOKEN" ]; then
  aliyun ebs describe-events \
    --RegionId cn-hangzhou \
    --MaxResults 10 \
    --NextToken "$NEXT_TOKEN"
fi
```

---

## Step 7: End-to-End Verification Script

### Complete Verification Example

```bash
#!/bin/bash

REGION="cn-hangzhou"
DISK_ID="d-bp67acfmxazb4p****"

echo "=== Query EBS Disk Events ==="
RESPONSE=$(aliyun ebs describe-events \
  --RegionId "$REGION" \
  --ResourceId "$DISK_ID" \
  --ResourceType disk \
  --MaxResults 10)

echo "$RESPONSE" | jq .

echo ""
echo "=== Verification Results ==="

# Check 1: RequestId exists
REQUEST_ID=$(echo "$RESPONSE" | jq -r '.RequestId')
if [ "$REQUEST_ID" != "null" ] && [ -n "$REQUEST_ID" ]; then
  echo "OK: RequestId exists: $REQUEST_ID"
else
  echo "FAIL: RequestId missing - API call failed"
  exit 1
fi

# Check 2: ResourceEvents exists
EVENT_COUNT=$(echo "$RESPONSE" | jq '.ResourceEvents | length')
if [ "$EVENT_COUNT" -gt 0 ]; then
  echo "OK: ResourceEvents contains $EVENT_COUNT event(s)"
else
  echo "WARN: ResourceEvents is empty - no events found"
fi

# Check 3: TotalCount matches list length
TOTAL_COUNT=$(echo "$RESPONSE" | jq '.TotalCount')
if [ "$TOTAL_COUNT" -eq "$EVENT_COUNT" ]; then
  echo "OK: TotalCount ($TOTAL_COUNT) matches ResourceEvents length ($EVENT_COUNT)"
else
  echo "WARN: TotalCount ($TOTAL_COUNT) does not match ResourceEvents length ($EVENT_COUNT) (pagination may apply)"
fi

# Check 4: Key fields are complete
if [ "$EVENT_COUNT" -gt 0 ]; then
  FIRST_EVENT=$(echo "$RESPONSE" | jq '.ResourceEvents[0]')
  for key in EventName EventType EventLevel Status ResourceId StartTime; do
    if echo "$FIRST_EVENT" | jq -e ".$key" > /dev/null 2>&1; then
      echo "OK: Field $key exists"
    else
      echo "FAIL: Field $key missing"
    fi
  done
fi

echo ""
echo "=== Verification Complete ==="
```

**Usage**:

```bash
chmod +x verify-events.sh
./verify-events.sh
```

---

## Common Issue Verification

| Issue | Verification Command | Expected Result |
|-------|----------------------|-----------------|
| Empty list | `jq '.ResourceEvents \| length'` | `> 0` or confirm filter conditions/time range |
| Missing fields | `jq '.ResourceEvents[0] \| keys'` | Contains all key fields |
| Timestamp anomaly | `jq '.ResourceEvents[].StartTime'` | Within query range |
| NextToken not handled | `jq '.NextToken'` | Empty or continue pagination |
| Permission error | `jq '.Code'` | Should not be `Forbidden` |

---

## References

- [EBS DescribeEvents API Documentation](https://help.aliyun.com/zh/ecs/developer-reference/api-ebs-2021-07-30-describeevents)
- [JMESPath Tutorial](https://jmespath.org/tutorial.html)
- [jq Manual](https://stedolan.github.io/jq/manual/)
