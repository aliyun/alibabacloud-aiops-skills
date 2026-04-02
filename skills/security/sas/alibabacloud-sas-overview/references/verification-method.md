# Verification Method

After executing the skill, verify each module's data was retrieved successfully.

## Module 1: Security Overview

```bash
# Verify security score retrieval
aliyun sas describe-secure-suggestion \
  --cal-type home_security_score \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "Score"
# NOTE: DescribeScreenScoreThread is currently unavailable (CalType not supported).
# Once supported, verify with:
#   START=$(python3 -c "import time; print(int((time.time()-86400*7)*1000))")
#   END=$(python3 -c "import time; print(int(time.time()*1000))")
#   aliyun sas describe-screen-score-thread \
#     --cal-type home_security_score \
#     --start-time "$START" --end-time "$END" \
#     --user-agent AlibabaCloud-Agent-Skills \
#     --cli-query "Data.SocreThread[-1]"

# Verify vulnerability fix count
aliyun sas describe-vul-fix-statistics \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "FixTotal"

# Verify baseline risk statistics
aliyun sas get-check-risk-statistics \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "Summary.{RiskCheck: RiskCheckCnt, RiskWarning: RiskWarningCnt, HandledTotal: HandledCheckTotal, HandledToday: HandledCheckToday}"

# Verify handled alert count
aliyun sas get-defence-count \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "SuspiciousDealtCount"
```

**Expected**: All commands return numeric values without errors.

## Module 2: Usage Info

```bash
# Verify version config (IsPaidUser + CreateTime for days calculation)
aliyun sas describe-version-config \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "{IsPaidUser: IsPaidUser, CreateTime: CreateTime}"

# Verify host asset info (multi-region)
aliyun sas describe-cloud-center-instances \
  --region cn-shanghai --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "PageInfo.TotalCount"
aliyun sas describe-cloud-center-instances \
  --region ap-southeast-1 --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "PageInfo.TotalCount"

# Verify uninstalled clients count
aliyun sas list-uninstall-aegis-machines \
  --region cn-shanghai \
  --current-page 1 --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "TotalCount"
```

**Expected**:
- `IsPaidUser` is `true` or `false`
- If `IsPaidUser == true` (pre-pay): `CreateTime` is a non-zero ms timestamp → calculate `(now - CreateTime)` as days
- If `IsPaidUser == false` (post-pay): `CreateTime` not meaningful → display N/A for service duration
- Asset counts are numeric. TotalCount is numeric.

## Module 3: Security Operations

### 3a. Risk Governance

```bash
# Verify risk governance suggestions (includes AI risk, CSPM, key config, system vulns)
aliyun sas describe-secure-suggestion \
  --cal-type home_security_score \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "Suggestions[].{Type: SuggestType, SubType: Detail[].SubType}"
# Verify SS_SAS_SYS_VUL appears in output with SubTypes:
#   SSI_SAS_SYS_VUL_HIGH, SSI_SAS_SYS_VUL_MEDIUM, SSI_SAS_SYS_VUL_LOW
```

**Expected**: Returns array of suggestions with SuggestType and SubType fields, including `SS_SAS_SYS_VUL` for system vulnerabilities.

### 3b. Security Protection — WAF

```bash
# Verify WAF Instance ID retrieval (multi-region)
aliyun waf-openapi describe-instance \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "InstanceId"
aliyun waf-openapi describe-instance \
  --region ap-southeast-1 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "InstanceId"

# Verify WAF flow chart (use InstanceId from above, per region)
aliyun waf-openapi describe-flow-chart \
  --region cn-shanghai \
  --instance-id "<InstanceId from cn-shanghai>" \
  --start-timestamp "$(python3 -c 'import time; print(int(time.time()-86400*7))')" \
  --interval 3600 \
  --user-agent AlibabaCloud-Agent-Skills
aliyun waf-openapi describe-flow-chart \
  --region ap-southeast-1 \
  --instance-id "<InstanceId from ap-southeast-1>" \
  --start-timestamp "$(python3 -c 'import time; print(int(time.time()-86400*7))')" \
  --interval 3600 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: WAF `DescribeInstance` returns a valid InstanceId. `DescribeFlowChart` returns flow data with `WafBlockSum` fields.

### 3c. Security Response

Currently N/A — no verification needed.

## Module 4: Asset Risk Trend

```bash
# Verify host assets (ECS)
aliyun sas describe-cloud-center-instances \
  --region cn-shanghai \
  --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "PageInfo.TotalCount"

aliyun sas describe-field-statistics \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "GroupedFields.RiskInstanceCount"

# Verify container assets
aliyun sas describe-container-field-statistics \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "{Clusters: ClusterCount, RiskClusters: RiskClusterCount}"

# Verify cloud product assets
aliyun sas get-cloud-asset-summary \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "GroupedFields.{Total: InstanceCountTotal, Risk: InstanceRiskCountTotal}"
```

**Expected**: All commands return valid numeric counts.

## Module 5: Billing & Subscription

```bash
# Verify billing mode and subscription status
aliyun sas describe-version-config \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "{IsPaidUser: IsPaidUser, CreateTime: CreateTime, ReleaseTime: ReleaseTime, PostPaySwitch: PostPayModuleSwitch}"

# Verify billing details (try each region, skip on permission error)
BILLING_CYCLE=$(date +%Y-%m)
aliyun bssopenapi query-bill \
  --region cn-shanghai \
  --billing-cycle "$BILLING_CYCLE" --product-code sas \
  --user-agent AlibabaCloud-Agent-Skills
# If permission denied, skip and try next region
```

**Expected**:
- `IsPaidUser` is `true` or `false`
- If `true` (pre-pay): `CreateTime` and `ReleaseTime` are non-zero ms timestamps
- If `false` (post-pay): `PostPayModuleSwitch` is a parseable JSON string

## Quick Full Check

Run all verification commands together. If all return data without errors, the skill is working correctly.
