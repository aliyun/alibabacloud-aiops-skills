# Verification Method - IPS Alert Event Analysis

## Authentication Pre-check

Before executing skill commands, verify that the Aliyun CLI has a valid profile available in the default credential chain:

```bash
# 1. Check CLI version (must be >= 3.3.1)
aliyun version

# 2. Check credential profile status (do not display raw credentials)
aliyun configure list
```

**Expected**: `aliyun configure list` shows at least one valid profile (AK, STS, or OAuth identity).
**If failed**: Configure credentials outside this session via local `aliyun configure`, then re-run this check.

---

## How to Verify Skill Execution Success

### Step 1: Verify DescribeRiskEventStatistic

```bash
START_TS=$(date -d "1 day ago" +%s)
NOW_TS=$(date +%s)

aliyun cloudfw DescribeRiskEventStatistic \
  --StartTime ${START_TS} \
  --EndTime ${NOW_TS} \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "TotalAttackCnt": 100,
  "TotalDropCnt": 80,
  "TotalWarnCnt": 15,
  "TotalMonitorCnt": 5,
  "TotalHighCnt": 10,
  "TotalMediumCnt": 30,
  "TotalLowCnt": 60,
  "TotalUntreatedCnt": 20
}
```

**Success Criteria**: Response contains `RequestId` and all `Total*Cnt` fields with numeric values (including zero).

### Step 2: Verify DescribeRiskEventGroup

```bash
aliyun cloudfw DescribeRiskEventGroup \
  --CurrentPage 1 \
  --PageSize 10 \
  --StartTime ${START_TS} \
  --EndTime ${NOW_TS} \
  --DataType 1 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "TotalCount": 5,
  "DataList": [
    {
      "EventName": "...",
      "EventCount": 10,
      "SrcIP": "x.x.x.x",
      "DstIP": "y.y.y.y",
      "VulLevel": 3,
      "RuleResult": 2,
      "Direction": "in",
      "AttackType": 7,
      "FirstTime": 1711324800,
      "LastTime": 1711411200
    }
  ]
}
```

**Success Criteria**: Response contains `RequestId`, `TotalCount`, and `DataList` array (may be empty if no events in the time range).

### Step 3: Verify DescribeRiskEventTopAttackAsset

```bash
aliyun cloudfw DescribeRiskEventTopAttackAsset \
  --StartTime ${START_TS} \
  --EndTime ${NOW_TS} \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "Assets": [
    {
      "Ip": "x.x.x.x",
      "ResourceInstanceName": "instance-name",
      "ResourceInstanceId": "i-xxxxx",
      "ResourceType": "EcsEIP",
      "RegionNo": "cn-hangzhou",
      "AttackCnt": 50,
      "DropCnt": 40
    }
  ]
}
```

**Success Criteria**: Response contains `RequestId` and `Assets` array.

### Step 4: Verify DescribeDefaultIPSConfig

```bash
aliyun cloudfw DescribeDefaultIPSConfig \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "RunMode": 1,
  "BasicRules": 1,
  "PatchRules": 1,
  "CtiRules": 1,
  "AiRules": 1,
  "RuleClass": 1,
  "MaxSdl": 4
}
```

**Success Criteria**: Response contains `RequestId` and `RunMode` field with value 0 or 1.

### Step 5: Verify DescribeSignatureLibVersion

```bash
aliyun cloudfw DescribeSignatureLibVersion \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "TotalCount": 2,
  "Version": [
    {
      "Type": "ips",
      "Version": "IPS-2603-01",
      "UpdateTime": 1711324800
    },
    {
      "Type": "intelligence",
      "Version": "INT-2603-01",
      "UpdateTime": 1711324800
    }
  ]
}
```

**Success Criteria**: Response contains `RequestId`, `TotalCount`, and `Version` array with at least one entry.

---

## Common Errors

| Error Code | Cause | Resolution |
|-----------|-------|------------|
| `InvalidAccessKeyId.NotFound` | Credential profile is missing or invalid | Configure a valid local CLI profile (`aliyun configure`) and re-run |
| `SignatureDoesNotMatch` | Active credential signature is invalid | Reconfigure local CLI credentials, then validate using `aliyun configure list` |
| `Forbidden` | Insufficient RAM permissions | Attach required permissions (see `ram-policies.md`) or use system policy `AliyunYundunCloudFirewallReadOnlyAccess` |
| `Throttling.User` | API rate limit exceeded | Wait 3 seconds and retry; reduce request frequency |
| `ServiceUnavailable` | Cloud Firewall service temporarily unavailable | Wait 3 seconds and retry (up to 2 retries) |
| `InvalidParameter` | Invalid parameter value (e.g., wrong time format, invalid VulLevel) | Check parameter types and values; time must be Unix timestamp in seconds |
| `InvalidRegionId` | Wrong region specified | Use `cn-hangzhou` (mainland China) or `ap-southeast-1` (Hong Kong/overseas) |
| `InstanceNotFound` | Cloud Firewall not activated | Activate Cloud Firewall service in Alibaba Cloud console |
| `HTTP 500/502/503` | Server-side error | Retry up to 2 times with 3-second delay |
