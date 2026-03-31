# Verification Methods - Cloud Security Center Incident Management

This document provides detailed verification steps to confirm all skill features work correctly.

## Prerequisites Verification

### 1. Python SDK Installation

```bash
# Verify SDK is installed
python3 -c "from alibabacloud_tea_openapi.client import Client; print('SDK OK')"
```

**Expected**: Output `SDK OK`

### 2. Credential Configuration

```bash
# Verify credentials are available (does not print AK/SK)
python3 -c "from alibabacloud_credentials.client import Client; c=Client(); print('Credentials OK')"
```

**Expected**: Output `Credentials OK`

---

## Core Feature Verification

### Test 1: List Security Incidents

```bash
# Basic query
python3 scripts/siem_client.py list-incidents --page 1 --size 5
```

**Expected**:
- Returns JSON with `RequestId`, `Incidents`, `PageNumber`, `PageSize`, `TotalCount`
- `Incidents` is an array

```bash
# Filter by threat level (Serious + High)
python3 scripts/siem_client.py list-incidents --threat-level 5,4 --size 10
```

**Expected**:
- Returned incidents have `ThreatLevel` value of `4` or `5`

```bash
# Filter by status (Unhandled)
python3 scripts/siem_client.py list-incidents --status 0 --size 10
```

**Expected**:
- Returned incidents have `IncidentStatus` value of `0`

---

### Test 2: Get Incident Details

```bash
# Get a UUID first
python3 scripts/siem_client.py list-incidents --size 1 | jq -r '.Incidents[0].IncidentUuid'

# Query incident details
python3 scripts/siem_client.py get-incident <UUID>
```

**Expected**:
- Returns JSON with `RequestId` and `Incident` object
- `Incident` contains complete incident information

---

### Test 3: Query Event Trend

```bash
# Query 7-day trend
python3 scripts/siem_client.py event-trend --days 7
```

**Expected**:
- Returns JSON with `RequestId` and `Data` object
- `Data` contains event counts by threat level

---

## Automated Verification Script

```bash
#!/bin/bash
echo "=== Cloud Security Center Incident Management - Verification ==="

# 1. List incidents
echo ">>> Test: List incidents"
RESULT=$(python3 scripts/siem_client.py list-incidents --size 5 2>&1)
if echo "$RESULT" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✓ List incidents PASSED"
  UUID=$(echo "$RESULT" | jq -r '.Incidents[0].IncidentUuid // empty')
else
  echo "✗ List incidents FAILED"
  exit 1
fi

# 2. Get incident details
if [ -n "$UUID" ]; then
  echo ">>> Test: Get incident details"
  DETAIL=$(python3 scripts/siem_client.py get-incident "$UUID" 2>&1)
  if echo "$DETAIL" | jq -e '.RequestId' > /dev/null 2>&1; then
    echo "✓ Get incident details PASSED"
  else
    echo "✗ Get incident details FAILED"
  fi
fi

# 3. Event trend
echo ">>> Test: Event trend"
TREND=$(python3 scripts/siem_client.py event-trend --days 7 2>&1)
if echo "$TREND" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✓ Event trend PASSED"
else
  echo "✗ Event trend FAILED"
fi

echo "=== Verification Complete ==="
```

---

## Troubleshooting

### Issue 1: Permission Error

```json
{"Code": "Forbidden.RAM", "Message": "User not authorized..."}
```

**Resolution**: Configure RAM permissions. See [ram-policies.md](ram-policies.md)

### Issue 2: Empty Data

**Resolution**:
1. Verify incidents exist within the time range
2. Check if filter conditions are too strict
3. Try removing all filter parameters

### Issue 3: SDK Import Error

```bash
pip install alibabacloud-tea-openapi alibabacloud-credentials alibabacloud-tea-util
```

### Issue 4: Credential Error

```json
{"Code": "InvalidAccessKeyId.NotFound", "Message": "..."}
```

**Resolution**: Configure credentials via `aliyun configure` or environment variables

---

## Verification Checklist

- [ ] Python SDK installed successfully
- [ ] Credentials configured and valid
- [ ] `list-incidents` returns valid response
- [ ] Pagination parameters work (`--page`, `--size`)
- [ ] Filter parameters work (`--threat-level`, `--status`)
- [ ] Time range parameter works (`--days`)
- [ ] `get-incident` returns incident details
- [ ] `event-trend` returns trend data
- [ ] Multi-region support works (`--region ap-southeast-1`)
