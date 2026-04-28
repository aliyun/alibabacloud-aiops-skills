# Verification Method - Exposure Detection & Analysis

## Authentication Pre-check

Before running any API calls, verify CLI credential status using the default credential chain:

```bash
aliyun configure list
```

Check the output for a valid profile (AK, STS, or OAuth identity). Do not print or handle raw AK/SK values.

## How to Verify Skill Execution Success

### Step 1: Verify Exposure Statistics Query

Run the following to confirm internet exposure data is available:

```bash
aliyun cloudfw describe-internet-open-statistic \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

**Expected**: Response contains exposure statistics including `InternetIpNum`, `InternetPortNum`, `InternetRiskIpNum`, `InternetServiceNum`. If all values are zero, the service may not be activated or there are no public assets.

### Step 2: Verify Exposed IP Query

```bash
NOW_TS=$(date +%s)
THIRTY_DAYS_AGO_TS=$(date -d "30 days ago" +%s)

aliyun cloudfw describe-internet-open-ip \
  --CurrentPage 1 \
  --PageSize 10 \
  --StartTime ${THIRTY_DAYS_AGO_TS} \
  --EndTime ${NOW_TS} \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

**Expected**: Response includes `DataList` array with exposed IP details (PublicIp, RiskLevel, PortList, ServiceNameList) and `PageInfo` with `TotalCount`.

### Step 3: Verify Asset List Query

```bash
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 10 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

**Expected**: Response includes `Assets` array with asset details (InternetAddress, ProtectStatus, ResourceType, RiskLevel) and `TotalCount`.

### Step 4: Verify Default IPS Config Query

```bash
aliyun cloudfw describe-default-ips-config \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

**Expected**: Response contains IPS configuration status including `BasicRules`, `EnableAllPatch`, `RunMode` fields.

### Step 5: Verify Vulnerability Protection Query

```bash
SEVEN_DAYS_AGO_TS=$(date -d "7 days ago" +%s)
NOW_TS=$(date +%s)

aliyun cloudfw describe-vulnerability-protected-list \
  --CurrentPage 1 \
  --PageSize 10 \
  --StartTime ${SEVEN_DAYS_AGO_TS} \
  --EndTime ${NOW_TS} \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

**Expected**: Response includes `VulnList` array with vulnerability details (VulnName, VulnLevel, VulnStatus, CveId, AttackCnt).

### Step 6: Verify Control Policy Query

```bash
aliyun cloudfw describe-control-policy \
  --Direction in \
  --CurrentPage 1 \
  --PageSize 10 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

**Expected**: Response includes `Policys` array with ACL rules (Source, Destination, DestPort, Proto, AclAction, HitTimes).

## Common Errors

| Error Code | Meaning | Resolution |
|-----------|---------|------------|
| `ErrorFirewallNotActivated` | Cloud Firewall not purchased | Activate Cloud Firewall at https://yundun.console.aliyun.com/?p=cfwnext |
| `Forbidden` | Insufficient permissions | Attach required RAM policies (see ram-policies.md) |
| `InvalidAccessKeyId.NotFound` | Credential profile is missing or invalid | Configure a valid profile in local CLI (`aliyun configure`) and re-run |
| `SignatureDoesNotMatch` | Active credential signature is invalid | Reconfigure local CLI credentials and re-run with `aliyun configure list` validation |
| `InvalidParameter` | Wrong parameter value | Check parameter format (e.g., timestamps must be in seconds) |
| `Throttling.User` | Rate limit exceeded | Wait 3 seconds and retry |
| `InvalidTimeRange` | Invalid time range | Ensure StartTime < EndTime, both in Unix seconds |
