# Verification Method - Cloud Firewall Status Overview

## Authentication Pre-check

Before running any API calls, verify CLI credential status using the default credential chain:

```bash
aliyun configure list
```

Check the output for a valid profile (AK, STS, or OAuth identity). Do not print or handle raw AK/SK values.

## How to Verify Skill Execution Success

### Step 1: Verify Instance Info Query

Run the following to confirm Cloud Firewall instance exists:

```bash
aliyun cloudfw describe-user-buy-version \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Expected**: Response contains instance version info (e.g., `Version`, `InstanceId`).

### Step 2: Verify Asset Statistics Query

```bash
aliyun cloudfw describe-asset-statistic \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Expected**: Response includes asset counts (total, protected, unprotected).

### Step 3: Verify Asset List Query

```bash
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 10 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Expected**: Response includes `Assets` array with asset details (IP, region, status, type).

### Step 4: Verify Internet Border Firewall Status

```bash
aliyun cloudfw describe-internet-open-statistic \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Expected**: Response includes open IP count, protected count, risk statistics.

### Step 5: Verify VPC Firewall Summary

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --CurrentPage 1 \
  --PageSize 20 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Expected**: Response includes list of TR firewalls with switch status.

### Step 6: Verify NAT Firewall List

```bash
aliyun cloudfw describe-nat-firewall-list \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Expected**: Response includes NAT firewall list with proxy status.

### Step 7: Verify Traffic Trend Query

```bash
aliyun cloudfw describe-postpay-traffic-total \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Expected**: Response includes traffic summary data.

## Common Errors

| Error Code | Meaning | Resolution |
|-----------|---------|------------|
| `ErrorFirewallNotActivated` | Cloud Firewall not purchased | Activate Cloud Firewall at https://yundun.console.aliyun.com/?p=cfwnext |
| `Forbidden` | Insufficient permissions | Attach required RAM policies (see ram-policies.md) |
| `InvalidAccessKeyId.NotFound` | Credential profile is missing or invalid | Configure a valid profile in local CLI (`aliyun configure`) and re-run |
| `SignatureDoesNotMatch` | Active credential signature is invalid | Reconfigure local CLI credentials and re-run with `aliyun configure list` validation |
| `InvalidParameter` | Wrong parameter value | Check parameter format |
| `Throttling.User` | Rate limit exceeded | Wait 3 seconds and retry |
