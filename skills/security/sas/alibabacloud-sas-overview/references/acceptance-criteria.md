# Acceptance Criteria: alibabacloud-sas-overview

**Scenario**: SAS Overview Data Query
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — SAS commands use `sas` product code

#### CORRECT
```bash
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills
aliyun sas describe-cloud-center-instances --region cn-shanghai --machine-types ecs --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Wrong: using uppercase API style
aliyun sas DescribeVersionConfig
# Wrong: missing user-agent
aliyun sas describe-version-config
# Wrong: wrong product code
aliyun security-center describe-version-config
```

## 2. Multi-Region Aggregation — Must query both cn-shanghai and ap-southeast-1

#### CORRECT
```bash
# Query cn-shanghai
aliyun sas describe-vul-fix-statistics --region cn-shanghai --user-agent AlibabaCloud-Agent-Skills
# Query ap-southeast-1
aliyun sas describe-vul-fix-statistics --region ap-southeast-1 --user-agent AlibabaCloud-Agent-Skills
# Sum: FixTotal(cn-shanghai) + FixTotal(ap-southeast-1)
```

#### INCORRECT
```bash
# Wrong: querying only one region
aliyun sas describe-vul-fix-statistics --region cn-shanghai --user-agent AlibabaCloud-Agent-Skills
# Wrong: using default region without specifying
aliyun sas describe-vul-fix-statistics --user-agent AlibabaCloud-Agent-Skills
```

## 3. Region-Agnostic APIs — Do not pass region

#### CORRECT
```bash
# No --region flag for region-agnostic APIs
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent AlibabaCloud-Agent-Skills
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills
# NOTE: DescribeScreenScoreThread is also region-agnostic, but currently unavailable (CalType not supported)
```

#### INCORRECT
```bash
# Wrong: passing region to region-agnostic API
aliyun sas describe-secure-suggestion --region cn-shanghai --cal-type home_security_score --user-agent AlibabaCloud-Agent-Skills
```

## 4. Time Parameters — Must use millisecond timestamps

#### CORRECT
```bash
# Millisecond timestamps for SAS APIs (e.g. DescribeChartData)
START=$(python3 -c "import time; print(int((time.time()-86400*7)*1000))")
END=$(python3 -c "import time; print(int(time.time()*1000))")

# DescribeChartData must include --report-id -1
aliyun sas describe-chart-data \
  --chart-id CID_ASSET_RISK_TREND --report-id -1 \
  --time-start "$START" --time-end "$END" \
  --user-agent AlibabaCloud-Agent-Skills
# NOTE: DescribeScreenScoreThread also uses ms timestamps, but is currently unavailable
```

#### INCORRECT
```bash
# Wrong: DescribeChartData without --report-id
aliyun sas describe-chart-data --chart-id CID_ASSET_RISK_TREND --time-start "$START" --time-end "$END"
```

## 5. WAF Block Stats — Two-step: DescribeInstance then DescribeFlowChart

#### CORRECT
```bash
# Step 1: Auto-fetch WAF Instance ID (per region)
aliyun waf-openapi describe-instance --region cn-shanghai --user-agent AlibabaCloud-Agent-Skills
aliyun waf-openapi describe-instance --region ap-southeast-1 --user-agent AlibabaCloud-Agent-Skills
# Extract InstanceId from each region's response

# Step 2: Query flow chart with each region's InstanceId
START_SEC=$(python3 -c "import time; print(int(time.time()-86400*7))")
aliyun waf-openapi describe-flow-chart \
  --region cn-shanghai \
  --instance-id "<InstanceId from cn-shanghai>" \
  --start-timestamp "$START_SEC" \
  --interval 3600 \
  --user-agent AlibabaCloud-Agent-Skills
aliyun waf-openapi describe-flow-chart \
  --region ap-southeast-1 \
  --instance-id "<InstanceId from ap-southeast-1>" \
  --start-timestamp "$START_SEC" \
  --interval 3600 \
  --user-agent AlibabaCloud-Agent-Skills
# Sum WafBlockSum across both regions
```

#### INCORRECT
```bash
# Wrong: hardcoding or asking user for WAF Instance ID without querying first
aliyun waf-openapi describe-flow-chart --instance-id "manually-provided-id" ...
# Wrong: using sas product for WAF API
aliyun sas describe-flow-chart --instance-id xxx
# Wrong: using millisecond timestamps (WAF uses seconds)
aliyun waf-openapi describe-flow-chart --instance-id xxx --start-timestamp 1710000000000 --interval 3600
# Wrong: skipping DescribeInstance and assuming InstanceId
```

## 6. Billing Mode — Branch on IsPaidUser before reading subscription fields

#### CORRECT
```python
import json
is_paid = response.get("IsPaidUser")

if is_paid:
    # Pre-pay (subscription) user → show CreateTime / ReleaseTime
    create_time = response.get("CreateTime")   # ms timestamp
    release_time = response.get("ReleaseTime") # ms timestamp
else:
    # Post-pay user → parse PostPayModuleSwitch
    post_pay_switch = response.get("PostPayModuleSwitch")  # JSON string
    switch_data = json.loads(post_pay_switch)
    for code, status in switch_data.items():
        print(f"{code}: {'Enabled' if status == 1 else 'Disabled'}")
```

#### INCORRECT
```python
# Wrong: always reading CreateTime/ReleaseTime without checking IsPaidUser
create_time = response["CreateTime"]
release_time = response["ReleaseTime"]

# Wrong: always reading PostPayModuleSwitch without checking IsPaidUser
switch_data = json.loads(response["PostPayModuleSwitch"])

# Wrong: treating PostPayModuleSwitch as a dict directly (it's a JSON string)
switch_data = response["PostPayModuleSwitch"]["POST_HOST"]
```

## 7. Security Score Extraction — Use DescribeSecureSuggestion Score (DescribeScreenScoreThread currently unavailable)

#### CORRECT
```python
# Current: use DescribeSecureSuggestion
score = suggestion_response["Score"]

# NOTE: DescribeScreenScoreThread is currently unavailable (CalType not supported).
# Once supported, switch to:
#   score_list = response["Data"]["SocreThread"]
#   current_score = score_list[-1]   # Last element = current score
#   score_trend = score_list          # Full list = historical trend
```

#### INCORRECT
```python
# Wrong: using DescribeScreenScoreThread which is currently unavailable
score_list = response["Data"]["SocreThread"]
# Wrong: looking for ScoreValue field
current_score = response["Data"]["ScoreValue"]
```

## 8. Service Duration — Must check IsPaidUser before calculating days

#### CORRECT
```python
is_paid = response.get("IsPaidUser")

if is_paid:
    # Pre-pay user → calculate service duration
    create_time = response.get("CreateTime")  # ms timestamp
    days = (time.time() * 1000 - create_time) / (1000 * 86400)
    print(f"累计使用天数: {int(days)}")
else:
    # Post-pay user → no subscription period
    print("累计使用天数: N/A")
```

#### INCORRECT
```python
# Wrong: always calculating days without checking IsPaidUser
create_time = response["CreateTime"]
days = (time.time() * 1000 - create_time) / (1000 * 86400)
# This gives meaningless results for post-pay users
```

## 9. User-Agent — Every aliyun command must include --user-agent

#### CORRECT
```bash
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Wrong: missing --user-agent
aliyun sas describe-version-config
```

## 10. Execution Scope — Only execute modules/items relevant to the user's query

#### CORRECT
```text
# User asks: "What is my security score?"
# → Execute ONLY Module 1, command 1a (DescribeSecureSuggestion; DescribeScreenScoreThread currently unavailable)

# User asks: "Show me asset risk trends"
# → Execute ONLY Module 4 (all sub-commands: 4a, 4b, 4c, 4d)

# User asks: "How many uninstalled clients?"
# → Execute ONLY Module 2, command 2c (ListUninstallAegisMachines)

# User asks: "Give me the full SAS overview"
# → Execute all 5 modules
```

#### INCORRECT
```text
# Wrong: User asks "What is my security score?" but agent runs all 5 modules
# Wrong: User asks "How many uninstalled clients?" but agent runs Modules 1-5
# Wrong: User asks about billing but agent also queries asset risk trends
```
