# Verification Method

Before API examples, initialize and reuse the manifest-derived `USER_AGENT` as
described in [SKILL.md](../SKILL.md#observability).

Verify only the requested items and all their confirmed regions. Reuse captured
responses before making duplicate queries. `--cli-query` examples below are useful
for spot checks; retain the full response for validators and RequestId diagnostics.
Exit/HTTP success does not establish valid business fields or complete coverage.

## Module 1: Security Overview

```bash
# Verify security score retrieval
aliyun sas describe-secure-suggestion \
  --cal-type home_security_score \
  --user-agent "$USER_AGENT" \
  --cli-query "Score"
# NOTE: DescribeScreenScoreThread is currently unavailable (CalType not supported).
# Once supported, verify with:
#   START=$(python3 -c "import time; print(int((time.time()-86400*7)*1000))")
#   END=$(python3 -c "import time; print(int(time.time()*1000))")
#   aliyun sas describe-screen-score-thread \
#     --cal-type home_security_score \
#     --start-time "$START" --end-time "$END" \
#     --user-agent "$USER_AGENT" \
#     --cli-query "Data.SocreThread[-1]"

# Verify vulnerability fix count
aliyun sas describe-vul-fix-statistics \
  --region cn-shanghai \
  --user-agent "$USER_AGENT" \
  --cli-query "FixTotal"

# Verify baseline risk statistics
aliyun sas get-check-risk-statistics \
  --region cn-shanghai \
  --user-agent "$USER_AGENT" \
  --cli-query "Summary.{RiskCheck: RiskCheckCnt, RiskWarning: RiskWarningCnt, HandledTotal: HandledCheckTotal, HandledToday: HandledCheckToday}"

# Verify handled alert count
aliyun sas get-defence-count \
  --region cn-shanghai \
  --user-agent "$USER_AGENT" \
  --cli-query "SuspiciousDealtCount"
```

**Expected**: Score must be present, finite and within 0–100; zero is valid. Validate the saved full response with `python3 scripts/overview_response.py score < response.json`. Null/missing fields mean failed validation even with HTTP 200. Counts must be numeric; missing values are not zero.

## Module 2: Usage Info

```bash
# Verify distinct service/postpay opening dates and instance expiry
aliyun sas describe-version-config \
  --user-agent "$USER_AGENT" \
  --cli-query "{OpenTime: OpenTime, PostPayOpenTime: PostPayOpenTime, ReleaseTime: ReleaseTime}"

# Verify host asset info (multi-region)
aliyun sas describe-cloud-center-instances \
  --region cn-shanghai --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent "$USER_AGENT" \
  --cli-query "PageInfo.TotalCount"
aliyun sas describe-cloud-center-instances \
  --region ap-southeast-1 --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent "$USER_AGENT" \
  --cli-query "PageInfo.TotalCount"

# Verify uninstalled clients count
aliyun sas list-uninstall-aegis-machines \
  --region cn-shanghai \
  --current-page 1 --page-size 1 \
  --user-agent "$USER_AGENT" \
  --cli-query "TotalCount"
```

**Expected**:
- Run `python3 scripts/overview_response.py times < response.json` on the full response.
- Opening dates produce independent elapsed days; ReleaseTime only supplies instance expiry.
- Missing/invalid dates remain unknown with reasons; valid values display timezone (UTC).
- Asset counts are numeric. TotalCount is numeric.
- Module 2b: run `python3 scripts/host_inventory.py --regions <confirmed regions> --user-agent "$USER_AGENT"` from the skill directory. Require `complete=true`; compare collected_count with total_count for each region. Single-page TotalCount checks above do not verify CPU-core totals.

## Module 3: Security Operations

### 3a. Risk Governance

```bash
# Verify risk governance suggestions (includes AI risk, CSPM, key config, system vulns)
aliyun sas describe-secure-suggestion \
  --cal-type home_security_score \
  --user-agent "$USER_AGENT" \
  --cli-query "Suggestions[].{Type: SuggestType, SubType: Detail[].SubType}"
# Verify SS_SAS_SYS_VUL appears in output with SubTypes:
#   SSI_SAS_SYS_VUL_HIGH, SSI_SAS_SYS_VUL_MEDIUM, SSI_SAS_SYS_VUL_LOW
```

**Expected**: Returns array of suggestions with SuggestType and SubType fields, including `SS_SAS_SYS_VUL` for system vulnerabilities.

### 3b. Security Protection — WAF

```bash
# Verify WAF Instance ID retrieval (multi-region)
aliyun waf-openapi describe-instance \
  --region cn-hangzhou \
  --user-agent "$USER_AGENT" \
  --cli-query "InstanceId"
aliyun waf-openapi describe-instance \
  --region ap-southeast-1 \
  --user-agent "$USER_AGENT" \
  --cli-query "InstanceId"

# Verify WAF flow chart (use InstanceId from above, per region)
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
```

**Expected**: WAF `DescribeInstance` returns a valid InstanceId. `DescribeFlowChart` returns flow data with `WafBlockSum` fields.

### 3c. Security Response

Reuse DescribeSecureSuggestion with cal-type home_security_score. Inspect
Suggestions entries with SuggestType SS_SAS_ALARM and their Detail entries for
SSI_SAS_ALARM_HIGH / MEDIUM / LOW. Validate the count field (RiskCount when returned
by this overview schema) as a nonnegative integer before aggregation. Retain region
coverage if the entries are regional. Unknown subtypes remain visible separately.

An absent alarm group/subtype or count is unknown unless a documented response
contract proves it means zero. A real numeric zero is valid. Do not label this
module N/A unconditionally. Public metadata also lists older SS_ALARM/ALARM_* enums;
if the response uses that schema, identify the mismatch instead of coercing it into
the newer overview structure. Do not parse Description text into invented counts.

## Module 4: Asset Risk Trend

For every confirmed SAS region, verify evidence for both host inputs:
`DescribeCloudCenterInstances` with `MachineTypes=ecs` -> `PageInfo.TotalCount`,
and `DescribeFieldStatistics` -> `GroupedFields.RiskInstanceCount`. Reuse matching
validated responses from this session or query the missing inputs. An
`InstanceCount=0` from the statistics API does not replace the required host-total
query. Count-only requests use one page (`CurrentPage=1, PageSize=1`); they do not
require fetching the full inventory or calculating CPU cores.

```bash
# Verify host assets (ECS)
aliyun sas describe-cloud-center-instances \
  --region cn-shanghai \
  --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent "$USER_AGENT" \
  --cli-query "PageInfo.TotalCount"

aliyun sas describe-field-statistics \
  --region cn-shanghai \
  --user-agent "$USER_AGENT" \
  --cli-query "GroupedFields.RiskInstanceCount"

# Verify container assets
aliyun sas describe-container-field-statistics \
  --region cn-shanghai \
  --user-agent "$USER_AGENT" \
  --cli-query "{Clusters: ClusterCount, RiskClusters: RiskClusterCount}"

# Verify cloud product assets
aliyun sas get-cloud-asset-summary \
  --region cn-shanghai \
  --user-agent "$USER_AGENT" \
  --cli-query "GroupedFields.{Total: InstanceCountTotal, Risk: InstanceRiskCountTotal}"
```

Repeat each applicable query above for every other confirmed SAS region.

**Expected**: counts are finite nonnegative integers and risk count does not exceed
total count for the same scope. Zero total means ratio is not applicable, not 0%.
If either host input is missing/failed in any requested region, mark host-risk
incomplete and the module partial; never claim all requested items succeeded.
Trend values must cover the confirmed time range/regions; missing regions stay partial.
For trend verification, use Module 4d in SKILL.md with the confirmed time window and
check timestamps/order and all required series. Never claim trend completion from
only the current asset-count queries above.

## Module 5: Billing & Subscription

```bash
# Verify billing mode and subscription status
aliyun sas describe-version-config \
  --user-agent "$USER_AGENT" \
  --cli-query "{IsPostpay: IsPostpay, Version: Version, ReleaseTime: ReleaseTime, PostPaySwitch: PostPayModuleSwitch, Trial: IsTrialVersion}"

# Verify bill details only when requested; bss:QueryBill is required
BILLING_CYCLE=$(python3 scripts/query_parameters.py billing --cycle "$BILLING_CYCLE") || exit 2
aliyun bssopenapi query-bill \
  --region cn-shanghai \
  --billing-cycle "$BILLING_CYCLE" --product-code sas \
  --user-agent "$USER_AGENT"
# On denial, record the failed item/region/action and keep independent results
```

**Expected**: Validate the full saved version response with
`python3 scripts/overview_response.py billing < response.json`.
Report subscription evidence, IsPostpay, trial and module switches independently.
Missing fields must stay unknown; malformed switches or conflicting evidence
produce a partial result. See [billing-semantics.md](billing-semantics.md).

## Quick Full Check

Run the checks for selected items; a full overview requires all selected capabilities,
including Security Response and trend data. Apply the per-item acceptance matrix,
then create a result manifest and run the coverage validator below. Missing fields,
failed pages or failed regions prevent complete success even if commands exit zero.

## Permission scope checks

Run `python3 -m unittest discover -s tests -p test_permissions.py -v` offline.
A score-only request requires no WAF/BSS permission; billing configuration uses
SAS only; requested bills require BSS. With a real denial, verify the final report
names the unavailable item and marks coverage partial instead of returning zero.

## Availability verification

Follow [service-prerequisites.md](service-prerequisites.md). Exercise free/basic,
paid, trial, mixed billing, overdue and missing-field responses. WAF 2.0 and a
confirmed absent instance must differ from failed discovery. Verify that a blocked
capability does not prevent independent requested queries. Offline configuration
fixtures are covered by test_billing.py and the prerequisite contract checks.

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

## CLI contract verification

Run `python3 scripts/check_cli_contract.py` and require an empty failures object.
Read full help descriptions for enums, time units and value formats; a banner-only
response must fail verification. See cli-installation-guide.md for plugin recovery.

## Parameter dependencies

Follow [query-parameters.md](query-parameters.md). Test same-region WAF ID binding,
missing discovery output, invalid months/days, seconds vs milliseconds, and missing
required inputs with test_query_parameters.py. Preserve explicitly supplied months
and region scope; never expand scope or execute a placeholder.

## Final result manifest

After validating each item's actual fields, record its status and evidence (region /
page coverage, relevant fields, error code/RequestId or confirmed unavailability).
Use item keys from `scripts/query_permissions.py`. Example partial result:

```json
{
  "score": {"status": "success", "evidence": "Score=0 validated, RequestId retained"},
  "bills": {"status": "failed", "evidence": "Example: Forbidden for bss:QueryBill; no bill data available"}
}
```

`python3 scripts/verify_overview.py --expected score bills < results.json` must
return overall=partial and exit 2. Missing requested items become unknown; all
not-applicable results remain explicitly not-applicable. A manifest is a coverage
check, not a replacement for validating raw fields.

Offline regression: `python3 -m unittest discover -s tests -v`. The fixtures do not
execute Agent evaluations or real cloud queries; record those separately if run.
