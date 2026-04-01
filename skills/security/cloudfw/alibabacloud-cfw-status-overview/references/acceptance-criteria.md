# Acceptance Criteria: alibabacloud-cfw-status-overview

**Scenario**: Cloud Firewall Status Overview
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Invocation Patterns

### 1. Command Format — verify product and API name

#### ✅ CORRECT
```bash
aliyun cloudfw DescribeAssetList \
  --CurrentPage 1 \
  --PageSize 10 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT — Wrong product name
```bash
aliyun cloudfirewall DescribeAssetList --region cn-hangzhou
```
**Why**: Product name is `cloudfw`, not `cloudfirewall` or `cfw`.

#### ❌ INCORRECT — Kebab-case API name
```bash
aliyun cloudfw describe-asset-list --region cn-hangzhou
```
**Why**: Cloud Firewall CLI uses PascalCase API names (e.g., `DescribeAssetList`).

#### ❌ INCORRECT — Missing --user-agent
```bash
aliyun cloudfw DescribeAssetList --CurrentPage 1 --PageSize 10 --region cn-hangzhou
```
**Why**: All commands must include `--user-agent AlibabaCloud-Agent-Skills`.

#### ❌ INCORRECT — Using old Python SDK pattern
```bash
python3 scripts/call_api.py \
  --api-name DescribeAssetList \
  --api-version 2017-12-07 \
  --endpoint cloudfw.cn-hangzhou.aliyuncs.com
```
**Why**: The skill uses Aliyun CLI directly, not a Python SDK wrapper script.

### 2. Parameter Format

#### ✅ CORRECT — PascalCase CLI flags
```bash
aliyun cloudfw DescribeAssetList \
  --CurrentPage 1 \
  --PageSize 50 \
  --Status close \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT — Kebab-case parameter names
```bash
aliyun cloudfw DescribeAssetList --current-page 1 --page-size 10
```
**Why**: Parameters use PascalCase (e.g., `--CurrentPage`, `--PageSize`).

#### ❌ INCORRECT — Using --region-id instead of --region
```bash
aliyun cloudfw DescribeAssetList --region-id cn-hangzhou
```
**Why**: The CLI global flag is `--region`, not `--region-id`.

#### ❌ INCORRECT — JSON params format (old SDK pattern)
```bash
--params '{"CurrentPage": "1", "PageSize": "10"}'
```
**Why**: CLI uses individual flags, not a JSON params string.

### 3. Authentication — never expose credentials

#### ✅ CORRECT — Verify credential profile via default credential chain
```bash
aliyun configure list
```

#### ❌ INCORRECT — Reading or printing raw credentials
```bash
aliyun configure get           # FORBIDDEN: may expose credential details
cat ~/.aliyun/config.json      # FORBIDDEN: may expose credential details
```

#### ❌ INCORRECT — Any command that prints environment credentials
```bash
echo $CLOUD_ACCESS_KEY                # FORBIDDEN: example of secret output
printenv | grep -i credential         # FORBIDDEN: may reveal secrets
env | grep -i access_key              # FORBIDDEN: may reveal secrets
```

### 4. API Names — verify exact casing

#### ✅ CORRECT
```
DescribeAssetList
DescribeAssetStatistic
DescribeUserBuyVersion
DescribeInternetOpenStatistic
DescribeVpcFirewallSummaryInfo
DescribeTrFirewallsV2List
DescribeVpcFirewallCenList
DescribeVpcFirewallList
DescribeNatFirewallList
DescribeInternetTrafficTrend
DescribePostpayTrafficTotal
DescribeInternetDropTrafficTrend
```

#### ❌ INCORRECT
```
describeAssetList          # Wrong casing
Describe_Asset_List        # Wrong format
DescribeAssets             # Wrong API name
describe-asset-list        # Kebab-case not supported
```
