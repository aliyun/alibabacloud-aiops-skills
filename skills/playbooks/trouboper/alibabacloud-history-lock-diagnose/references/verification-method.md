# Verification Method

## Diagnosis Flow Verification

### 1. Credential and Environment Verification

**Verification Steps:**
1. Check Alibaba Cloud CLI version
2. Verify credential configuration
3. Confirm DAS service is connected

**Verification Commands:**
```bash
# Check CLI version (must be >= 3.3.1)
aliyun version

# Verify credential configuration
aliyun configure list
```

**Success Criteria:**
- ✅ CLI version >= 3.3.1
- ✅ Valid credential configuration displayed (AK, STS, or OAuth)
- ✅ Target instance is connected to DAS and shows "Connected"

---

### 2. Instance Information Verification

**Verification Steps:**
1. Check whether the instance exists
2. Confirm the instance engine type is MySQL
3. Retrieve instance details

**Verification Commands:**

For RDS MySQL:
```bash
aliyun rds describe-db-instance-attribute \
  --region {RegionId} \
  --db-instance-id {InstanceId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

For PolarDB MySQL:
```bash
aliyun polardb describe-db-cluster-attribute \
  --region {RegionId} \
  --db-cluster-id {ClusterId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

**Success Criteria:**
- ✅ Instance exists and is in "Running" status
- ✅ Engine type is MySQL
- ✅ Instance version supports lock analysis (RDS MySQL 5.6/5.7/8.0 or PolarDB MySQL 5.6/8.0)

---

### 3. DAS Deadlock History Query Verification

**Verification Steps:**
1. Call the DAS API to retrieve deadlock history records
2. Confirm the returned data contains lock events

**Verification Method (Python SDK):**
```python
from alibabacloud_das20200116.client import Client as DASClient
from alibabacloud_das20200116 import models as das_models
from alibabacloud_credentials.client import Client as CredentialClient
import json

credential = CredentialClient()
config = open_api_models.Config(
    credential=credential,
    endpoint='das.cn-shanghai.aliyuncs.com'
)
client = DASClient(config)

request = das_models.GetDeadLockHistoryRequest(
    instance_id='{InstanceId}',
    start_time={StartTime},  # Unix timestamp (milliseconds)
    end_time={EndTime},
    source='AUTO'
)
response = client.get_dead_lock_history(request)

# Verify response
data = json.loads(response.data)
assert response.success == 'true'
assert data['total'] >= 0
print(f"Found {data['total']} deadlock records")
```

**Success Criteria:**
- ✅ API call succeeded (Code: 200, Success: true)
- ✅ Deadlock record list returned (may be empty)
- ✅ Each record contains required fields such as textId and lockTime

---

### 4. Slow Log Query Verification

**Verification Steps:**
1. Query slow logs within the specified time range
2. Confirm slow logs contain lock wait information

**Verification Method (Python SDK):**
```python
request = das_models.DescribeSlowLogRecordsRequest(
    instance_id='{InstanceId}',
    start_time='{StartTime}',
    end_time='{EndTime}',
    page_no=1,
    page_size=30
)
response = client.describe_slow_log_records(request)

# Verify response
assert response.success == 'true'
for log in response.data.list:
    if hasattr(log, 'lock_time') and log.lock_time > 0:
        print(f"Lock wait found: {log.sql_text}")
        print(f"Lock wait duration: {log.lock_time}ms")
```

**Success Criteria:**
- ✅ Slow log records retrieved successfully
- ✅ Slow SQL with lock waits identified (lock_time > 0)
- ✅ SQL text and lock wait duration can be extracted

---

### 5. Performance Data Verification

**Verification Steps:**
1. Query instance performance data
2. Confirm lock-related metrics are available

**Verification Command (RDS):**
```bash
aliyun rds describe-performance-datas \
  --region {RegionId} \
  --db-instance-id {InstanceId} \
  --key GroupBySession \
  --start-time {StartTime} \
  --end-time {EndTime} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

**Success Criteria:**
- ✅ Performance metric data returned
- ✅ Session and transaction related metrics included

---

### 6. Diagnosis Report Completeness Verification

**Verification Steps:**
Check whether the diagnosis report contains the following key information:

**Required Information Checklist:**
- [ ] Lock wait timeline (occurrence time, duration)
- [ ] Blocking chain analysis (who blocked whom)
- [ ] SQL statements involved
- [ ] Lock type (row lock, table lock, MDL lock, etc.)
- [ ] Blocker source process/session information
- [ ] Related table and index information
- [ ] Resolution recommendations

**Success Criteria:**
- ✅ All required information is complete
- ✅ Blocking chain relationships are clear
- ✅ Actionable resolution recommendations are provided

---

## Common Issue Verification

### Issue 1: No Deadlock Records Found

**Possible Causes:**
1. Deadlock detection is not enabled on the instance (innodb_deadlock_detect)
2. Deadlock log printing is not enabled (innodb_print_all_deadlocks)
3. Incorrect time range setting
4. DAS service is not connected or in abnormal status

**Troubleshooting Steps:**
```bash
# Check instance parameter configuration
aliyun rds describe-parameters \
  --region {RegionId} \
  --db-instance-id {InstanceId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

### Issue 2: No Lock Wait Information in Slow Logs

**Possible Causes:**
1. Lock wait duration did not exceed the slow log threshold
2. Slow log feature is not enabled
3. No slow logs in the query time range

**Troubleshooting Steps:**
- Check the slow log threshold setting (long_query_time)
- Confirm slow log feature is enabled
- Expand the query time range

### Issue 3: Insufficient Permissions

**Error Message:**
```
You are not authorized to do this action.
```

**Troubleshooting Steps:**
1. Confirm required RAM permissions: hdm:GetDasSQLLogHotData, hdm:GetDeadLockHistory, hdm:GetDeadLockDetail, hdm:CreateLatestDeadLockAnalysis, hdm:DescribeSqlLogConfig, hdm:GetMySQLAllSessionAsync
2. Grant the required permissions via RAM console
3. Retry after permissions take effect

---

## Automated Verification Script

Create `scripts/validate-diagnosis.py` for automated verification:

```python
#!/usr/bin/env python3
"""Validate lock diagnosis result completeness"""

import json
import sys

def validate_diagnosis_report(report_file):
    """Validate diagnosis report"""
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    required_fields = [
        'lock_timeline',
        'blocking_chain',
        'sql_statements',
        'lock_type',
        'blocker_info',
        'recommendations'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in report:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"Diagnosis report missing required fields: {', '.join(missing_fields)}")
        return False
    
    print("Diagnosis report completeness validation passed")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python validate-diagnosis.py <report_file>")
        sys.exit(1)
    
    success = validate_diagnosis_report(sys.argv[1])
    sys.exit(0 if success else 1)
```
