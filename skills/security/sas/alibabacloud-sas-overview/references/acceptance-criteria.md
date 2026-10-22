# Acceptance Criteria: alibabacloud-sas-overview

Before API examples, initialize and reuse the manifest-derived `USER_AGENT` as
described in [SKILL.md](../SKILL.md#observability).

**Scenario**: SAS Overview Data Query
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — SAS commands use `sas` product code

#### CORRECT
```bash
aliyun sas describe-version-config --user-agent "$USER_AGENT"
aliyun sas describe-cloud-center-instances --region cn-shanghai --machine-types ecs --current-page 1 --page-size 20 --user-agent "$USER_AGENT"
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

## 2. Multi-Region Aggregation — Cover exactly the confirmed regions

#### CORRECT
```bash
# Query cn-shanghai
aliyun sas describe-vul-fix-statistics --region cn-shanghai --user-agent "$USER_AGENT"
# Query ap-southeast-1
aliyun sas describe-vul-fix-statistics --region ap-southeast-1 --user-agent "$USER_AGENT"
# Sum: FixTotal(cn-shanghai) + FixTotal(ap-southeast-1)
```

#### INCORRECT
```bash
# Wrong: querying only one region when both were requested
aliyun sas describe-vul-fix-statistics --region cn-shanghai --user-agent "$USER_AGENT"
# Wrong: using default region without specifying
aliyun sas describe-vul-fix-statistics --user-agent "$USER_AGENT"
```

## 3. Region-Agnostic APIs — Do not pass region

#### CORRECT
```bash
# No --region flag for region-agnostic APIs
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent "$USER_AGENT"
aliyun sas describe-version-config --user-agent "$USER_AGENT"
# NOTE: DescribeScreenScoreThread is also region-agnostic, but currently unavailable (CalType not supported)
```

#### INCORRECT
```bash
# Wrong: passing region to region-agnostic API
aliyun sas describe-secure-suggestion --region cn-shanghai --cal-type home_security_score --user-agent "$USER_AGENT"
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
  --user-agent "$USER_AGENT"
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
aliyun waf-openapi describe-instance --region cn-hangzhou --user-agent "$USER_AGENT"
aliyun waf-openapi describe-instance --region ap-southeast-1 --user-agent "$USER_AGENT"
# Extract InstanceId from each region's response

# Step 2: Query flow chart with each region's InstanceId
START_SEC=$(python3 scripts/query_parameters.py window --days "$TIME_RANGE_DAYS" --unit seconds) || exit 2
aliyun waf-openapi describe-flow-chart \
  --region cn-hangzhou \
  --instance-id "<InstanceId from cn-hangzhou>" \
  --start-timestamp "$START_SEC" \
  --interval 3600 \
  --user-agent "$USER_AGENT"
aliyun waf-openapi describe-flow-chart \
  --region ap-southeast-1 \
  --instance-id "<InstanceId from ap-southeast-1>" \
  --start-timestamp "$START_SEC" \
  --interval 3600 \
  --user-agent "$USER_AGENT"
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

## 6. Billing — independent subscription, pay-as-you-go and trial evidence

CORRECT: use `scripts/overview_response.py billing` and the decision table in
[billing-semantics.md](billing-semantics.md); inspect IsPostpay and parse module
switches independently of subscription expiry. Report malformed/missing data.
INCORRECT: infer postpay from IsPaidUser=false, discard postpay switches when
subscription evidence exists, or treat missing module keys as disabled.

## 7. Security Score Extraction — Use DescribeSecureSuggestion Score (DescribeScreenScoreThread currently unavailable)

#### CORRECT
```python
# Current: use DescribeSecureSuggestion
from scripts.overview_response import security_score
result = security_score(suggestion_response)
# Only use result["score"] when result["status"] == "ok".

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

## 8. Service Duration — Separate opening dates and instance expiry

CORRECT: validate the saved response with `scripts/overview_response.py times`.
Use OpenTime for service elapsed days, PostPayOpenTime for pay-as-you-go elapsed
days, and ReleaseTime for instance expiry. All three are millisecond timestamps;
display the timezone explicitly. A valid date remains usable in mixed billing mode.

INCORRECT: use undocumented CreateTime, suppress all duration for postpay,
label ReleaseTime as postpay expiry, or turn missing/zero/future opening dates into
zero elapsed days. Unknown dates need a reason; other valid dates can still display.

## 9. User-Agent — Every cloud query must include the session UA

#### CORRECT
```bash
aliyun sas describe-version-config --user-agent "$USER_AGENT"
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

## Host inventory completeness (83995440 / 83995423)

CORRECT: fetch all pages, count each Uuid once, add Cores across instances,
and add TotalCount once per region. Use scripts/host_inventory.py.
INCORRECT: sum only the first 20 hosts, sum TotalCount for every page, or
report a complete total after a failed/empty/repeated page.

Offline regression: `python3 -m unittest discover -s tests -p 'test_pagination.py'`.
Covers 0/20/21/45 hosts, two regions, incomplete pages, duplicates and changing totals.

## Silent failures (83703067 / 83703050)

CORRECT: HTTP 200 + Score=null is a failed score query; keep RequestId.
INCORRECT: convert null to zero, claim success because Suggestions exists, or
treat missing counts as zero. Empty data is only legitimate when the API contract
explicitly defines it as such. Validate only fields needed for the requested item.

Regression: `python3 -m unittest discover -s tests -p test_score.py`.

## Scope-specific permissions

CORRECT: require BSS read access for requested bills, report denial explicitly and
continue independent SAS/WAF items. Billing configuration needs SAS access only.
INCORRECT: require BSS for a score query, silently skip denied bills, or call denied
billing zero spend. Use the permission-scope regression tests.

## Service availability

CORRECT: check capability-level evidence using service-prerequisites.md; preserve
free/basic queries, trials and mixed billing. WAF statistics require WAF 3.0.
INCORRECT: gate the whole overview on a paid SAS edition, interpret an unknown
configuration as unopened, or buy/upgrade automatically.

## Transient error recovery

Follow [query-errors.md](query-errors.md). Verify bad-file-descriptor recovery,
timeout exhaustion, permission/parameter rejection without retry, invalid JSON,
and rejection of write commands with `test_query_errors.py`. A retry must preserve
all confirmed arguments and session UA; exhausted data remains unavailable.

## Account-site navigation

Use [console-sites.md](console-sites.md). Check international and China account
paths independently, including an international account querying China assets.
No unconditional China console link may appear in the Skill or installation guide.
Missing account-site context requires clarification; language/region is not a proxy.
Offline link regression: `python3 -m unittest discover -s tests -p test_console_sites.py -v`.

## Chinese intent and progress

Exercise the triggering fixtures for Chinese score/assets/uninstalled clients/trend/
billing/WAF statistics; remediation and configuration prompts remain negative cases.
During multi-region work, verify start, page/module, retry and final-state updates
without invented percentages or credentials. `test_progress.py` checks actual script
progress and JSON separation offline. Trigger fixture checks validate their structure;
actual Agent selection must be measured by the evaluation runner separately.

## Parameter dependencies

Follow [query-parameters.md](query-parameters.md). Test same-region WAF ID binding,
missing discovery output, invalid months/days, seconds vs milliseconds, and missing
required inputs with test_query_parameters.py. Preserve explicitly supplied months
and region scope; never expand scope or execute a placeholder.

## Per-item acceptance and whole-workflow completion

| Item | Business success evidence | Failure / incomplete evidence |
|---|---|---|
| score | Finite Score in 0..100, including zero | Null/missing/invalid Score, even HTTP 200 |
| vul-fixes / baseline / handled-alerts | Required nonnegative count fields for each confirmed region | Missing field/region; do not zero-fill |
| service | Separately validated opening/expiry dates | Unknown dates stay unknown with reasons |
| hosts | All pages, stable totals, unique Uuid, valid Cores | Failed/empty/repeated page or changed total |
| uninstalled | Valid TotalCount for every confirmed region | Missing/failed regional count |
| governance / security-response | Expected suggestion/detail schema and valid counts; recognized groups mapped | Missing group/count or schema mismatch stays unknown |
| waf | WAF 3.0, same-region discovery, valid flow counts/time coverage | Failed discovery/query; confirmed absent instance is not-applicable |
| host-risk | Per-region DescribeCloudCenterInstances PageInfo.TotalCount (MachineTypes=ecs) and DescribeFieldStatistics RiskInstanceCount; matching scope, nonnegative counts, risk <= total | Missing either input prevents completion; total=0 makes ratio not-applicable |
| container-risk / cloud-risk | Matching scope, nonnegative counts, risk <= total | Missing count; total=0 makes ratio not-applicable |
| trend | Valid series, timestamps and confirmed regional/time coverage | Missing series/region or unverified coverage |
| billing-config | Independent validated billing/edition/trial evidence | Missing/malformed/conflicting fields remain partial |
| bills | Correct month/account/site, all pages, no duplicate bill/currency aggregation | Permission/runtime error or incomplete coverage; not zero spend |

CORRECT: evaluate each requested item first, then validate the result manifest with
`scripts/verify_overview.py`. Report successful, failed/unknown and not-applicable
items with evidence; preserve partial results and the next diagnostic step.
INCORRECT: claim all modules passed from command exit codes, hide a failed region,
or run all modules to verify a score-only request. Unknown never equals zero.

Implementation mapping and test boundaries: [requirement-results.md](requirement-results.md).

## Host-risk totals versus full inventory

CORRECT: for an asset-risk-trend request, query host totals using
DescribeCloudCenterInstances with MachineTypes=ecs, CurrentPage=1 and PageSize=1
in every confirmed region, and pair PageInfo.TotalCount with that region's
DescribeFieldStatistics RiskInstanceCount. Reuse validated matching responses
when already obtained in this session. Report missing inputs as incomplete and
preserve successful container/cloud/trend results. Only a request for inventory
details or CPU-core totals requires the full-pagination checks from Module 2b.

INCORRECT: skip DescribeCloudCenterInstances because DescribeFieldStatistics
returned InstanceCount=0; claim host-risk completion without its required total;
or require CPU-core aggregation in a trend-only evaluation.
