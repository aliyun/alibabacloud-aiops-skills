# Verification Method: alibabacloud-finops-inspect

**Scenario**: Cost-oriented health inspection across all regions
**Purpose**: Verification steps and criteria for successful inspection

---

## Pre-Execution Verification

### 1. Python Version Check
```bash
python3 --version
```
**Expected**: Python 3.10 or higher

### 2. Dependencies Check
```bash
pip3 list | grep alibabacloud
```
**Expected**: All required packages listed:
- `alibabacloud_credentials`
- `alibabacloud_tea_openapi`
- `alibabacloud_tea_util`
- `alibabacloud_ecs20140526`
- `alibabacloud_rds20140815`
- `alibabacloud_vpc20160428`
- `alibabacloud_slb20140515`
- `alibabacloud_alb20200616`
- `alibabacloud_nlb20220430`
- `alibabacloud_cms20190101`

### 3. Credential Validation
Run the inspection script. The first step should validate credentials.

**Expected**: Credentials loaded successfully via credential chain
**Failure**: If credentials are not found, the script should display a clear error message and stop

---

## Execution Verification

### 1. Region Discovery
**Check**: At least one enabled region is discovered
**Verification**: The inspection log should show the list of discovered regions
**Failure**: If no regions are found, verify the account has active services

### 2. Resource Collection
**Check**: Each specified resource type is queried with pagination
**Verification**:
- ECS: `DescribeInstances` returns instance list
- RDS: `DescribeDBInstances` returns instance list
- EIP: `DescribeEipAddresses` returns EIP list
- Disk: `DescribeDisks` returns disk list
- CLB: `DescribeLoadBalancers` returns CLB list
- ALB: `ListLoadBalancers` returns ALB list
- NLB: `ListLoadBalancers` returns NLB list
- NAT: `DescribeNatGateways` returns NAT list

### 3. Metric Aggregation
**Check**: CloudMonitor metrics are aggregated over the specified lookback period
**Verification**:
- For each Running ECS instance, 5 metrics are queried (CPU, Memory, IOPS, In/Out bandwidth)
- For each Running RDS instance, 4 metrics are queried (CPU, Memory, IOPS, Connections)
- For each InUse EIP, 2 metrics are queried (Inbound/Outbound traffic)

### 4. Judgment Accuracy
**Check**: Resources are correctly classified into severity levels
**Verification**:

| Resource | Metric Values | Expected Classification |
|----------|--------------|------------------------|
| ECS | CPU=2%, Memory=5%, Network=10 Kbps | Critical Idle (P1) |
| ECS | CPU=8%, Memory=30%, Network=100 Kbps | Low Utilization (P2) |
| ECS | CPU=25%, Memory=40%, Network=500 Kbps | Normal |
| ECS | Status=Stopped + PrePaid | Stopped but billed (P1) |
| EIP | Status=Available | Unbound EIP (P0) |
| EIP | Status=InUse + traffic=0 | Bound but zero traffic (P1) |
| Disk | Status=Available + created > 30 days | Unmounted disk old (P0) |
| CLB | No listeners | Idle LB (P0) |
| NAT | No EIP bound | Fully idle NAT (P0) |

### 5. Observation Window Handling
**Check**: Resources created within the last 7 days are handled correctly
**Verification**:
- Newly created ECS instances (< 7 days) should NOT be flagged as idle or low-utilization
- Serverless RDS instances should be flagged as "Serverless instance" not waste
- ECS instances without CloudMonitor agent should be flagged as "memory data missing"

---

## Report Verification

### 1. Report Structure
**Check**: The report contains all required sections
**Expected structure**:
1. Inspection Summary (resource counts, issue counts)
2. Per-Resource Detail Tables (grouped by resource type)
3. Recommendation Summary (sorted by priority: P0 -> P1 -> P2)
4. Error Summary (if any API calls failed)

### 2. No Credentials in Output
**Check**: The report contains NO AK/SK information
**Verification**: Search the report output for any string matching AK pattern (starts with `LTAI`)

### 3. Recommendation Completeness
**Check**: All identified issues have corresponding recommendations
**Verification**:
- Each P0 issue has an "Act Now" recommendation
- Each P1 issue has a "Recommended" recommendation
- Each P2 issue has an "Observe" recommendation
- All recommendations include a "please confirm before acting" warning

### 4. Error Summary Accuracy
**Check**: Any failed API calls are summarized at the end
**Verification**:
- Failed calls show the API name, region, and error message
- Failed calls do NOT abort the entire inspection
- Throttling events are logged separately

---

## Performance Verification

### 1. Throttling Handling
**Check**: API throttling is handled correctly
**Verification**:
- On `Throttling` error, the script retries with exponential backoff
- Maximum 3 retries before marking the call as failed
- Failed calls are logged in the error summary

### 2. Timeout Handling
**Check**: Network timeouts are handled correctly
**Verification**:
- On timeout, the script retries with increasing timeout (5s -> 10s -> 15s)
- Maximum 2 retries before marking the call as failed

### 3. Total Execution Time
**Check**: Total execution completes within 10 minutes
**Verification**:
- If execution exceeds 10 minutes, the script aborts gracefully
- Partial results are output before aborting

---

## Post-Execution Verification

### 1. Exit Code
**Check**: The script exits with appropriate exit code
**Expected**:
- Exit code 0: Successful completion
- Exit code 1: Credential failure
- Exit code 2: Partial completion (some API calls failed)

### 2. Output Files (if configured)
**Check**: If output file is specified, the report is written correctly
**Verification**:
- File exists at the specified path
- File content matches the console output
- File encoding is UTF-8
