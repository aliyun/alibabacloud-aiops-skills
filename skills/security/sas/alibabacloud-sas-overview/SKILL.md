---
name: alibabacloud-sas-overview
description: |
  Alibaba Cloud Security Center (SAS) Overview Data Query Skill.
  Retrieves security score, asset status, risk governance, asset risk trends, and billing info.
  Supports flexible scope: query a single data item, a specific module, or the full overview based on user intent.
  阿里云云安全中心（SAS）总览数据查询技能。
  可获取安全评分、资产状态、风险治理、资产风险趋势及账单信息。
  支持灵活查询范围：根据用户意图查询单个数据项、特定模块或完整总览。
  Triggers: "SAS overview", "security center overview", "SAS 总览", "云安全中心总览",
    "security score", "安全评分", "安全分",
    "fixed vulnerability statistics", "baseline risk", "handled alerts",
    "已修复漏洞统计", "基线风险统计", "已处理告警",
    "host assets", "uninstalled clients", "主机资产", "CPU 核数", "未安装客户端",
    "risk governance", "WAF blocks", "asset risk trend",
    "风险治理", "WAF 拦截统计", "资产风险趋势",
    "SAS billing", "订阅状态", "云安全中心账单", "按量模块开关"
  Out of scope: This Skill only covers SAS overview data queries. It does not perform remediation, modify configurations, or manage non-SAS services.
---

# SAS Overview Data Query

Retrieves the 5 core modules of the Security Center (SAS) overview dashboard:
1. **Security Overview** — score, fixed vulns, baseline risk, handled alerts
2. **Usage Info** — service days, asset scale, uninstalled clients
3. **Security Operations** — risk governance (AI risk, CSPM, key config, system vulns), security protection (WAF blocks), security response
4. **Asset Risk Trend** — host/container/cloud product risk ratios + trend chart
5. **Billing & Subscription** — post-pay switches, subscription validity, bills

> **Execution Scope**: Each module and data item can be queried independently.
> Match the scope to the user's request:
> - **Single data item** — e.g., "What is my security score?" → only command 1a
> - **Single module** — e.g., "Show asset risk trend" → all of Module 4
> - **Full overview** — e.g., "SAS overview" → all 5 modules

**Architecture**: `SAS + WAF + BssOpenApi`

## Service Availability — Check Only the Requested Capabilities

This overview has **no universal paid-edition prerequisite**. Basic SAS queries,
paid-feature availability, WAF availability and billing permission are separate.
Before querying a paid capability or a full overview, reuse `DescribeVersionConfig`
to inspect Version, IsPostpay, IsTrialVersion, PostPayStatus and module switches.
Do not infer that all features work from a paid edition, or that all queries fail
on a free edition. See [service-prerequisites.md](references/service-prerequisites.md)
for self-checks and the capability matrix. Never purchase or upgrade automatically.


## Execution Feedback

Respond in the user's language. Before queries, state the selected items, confirmed
regions and current step. At module/region boundaries and retries, report what has
completed and what is running; for pagination show collected/total when known.
Do not invent percentage completion. For a long call, acknowledge waiting without
claiming new results. Finish with completed, failed/unknown and not-applicable items,
including partial coverage and next steps. Never print credentials or raw responses
as progress. Script progress goes to stderr; stdout remains machine-readable JSON.
Example: "Querying Shanghai page 2: collected 20/45 hosts; Singapore has not started."

## Observability

**Manifest-derived User-Agent**: every cloud query must use
`AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/<session UUID> skill-version/<manifest version>`.
The top-level `version` in [references/manifest.json](references/manifest.json) is
this Skill's version (independent of CLI/API versions). Update it when releasing
Skill changes; do not hardcode a version in commands or use unresolved placeholders.

Before running any query examples, run this once from the installed Skill directory:

```bash
USER_AGENT=$(python3 scripts/user_agent.py) || exit 2
export USER_AGENT
```

The helper resolves the manifest relative to its own file, validates its non-empty
string version, generates a fresh UUID v4, and assembles the full UA at runtime.
A missing/invalid manifest stops initialization; never fall back to an unversioned UA.
Reuse this exact `USER_AGENT` for all calls, pagination and retries in this session.
When tools use separate shells, carry the generated value into each shell explicitly;
do not regenerate it per command. A new Skill invocation generates a new UUID.
All examples in this Skill and its references use `--user-agent "$USER_AGENT"`.
The inventory and retry helpers forward that value unchanged. The CLI contract
checker uses the same builder once per run for all help calls.

Local maintenance commands (`version`, `configure`, `plugin`) have their own flags;
`configure` and `plugin update` reject `--user-agent` on CLI 3.4.11.

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.

> **Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> With `--auto-plugin-install true` set, the required plugins (sas, waf-openapi, bssopenapi) are installed automatically on first use — no manual `aliyun plugin install` step is needed.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Use the RAM console for the account’s site: [international / China console links](references/console-sites.md). Confirm the site if unknown; asset region or prompt language does not determine it.
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## Parameters

> **Parameter confirmation**: use values already provided/approved in this session.
> Ask only for missing inputs needed by the selected scope. Proposed defaults below
> are candidates, not automatic values. A single-region request stays single-region.

| Parameter | Required when | Source / candidate |
|---|---|---|
| SAS Regions | Regional SAS items | Confirm cn-shanghai and/or ap-southeast-1 |
| WAF Regions | WAF statistics | Confirm cn-hangzhou and/or ap-southeast-1 |
| WAF InstanceId | DescribeFlowChart | Successful DescribeInstance in the same account and WAF region |
| BillingCycle | Bill details | Confirm YYYY-MM; resolve “this month” once using the user's timezone |
| TimeRangeDays | WAF / trend queries | Confirm a positive integer; candidate 7 days |
| Account site | Console navigation / billing | Explicit international or China site; independent of region |

Set `TIME_RANGE_DAYS` and `BILLING_CYCLE` to those confirmed values before the
examples. See [query-parameters.md](references/query-parameters.md) for required
flags, dependency checks and timestamp units. Never execute placeholder values.

## RAM Permissions

See [references/ram-policies.md](references/ram-policies.md) for the full RAM policy JSON.

Permissions are scope-specific: SAS items need SAS read actions; WAF statistics
need WAF read actions; bill details **require** `bss:QueryBill` (or
`AliyunBSSReadOnlyAccess`). Billing configuration alone uses SAS permissions.
Use `python3 scripts/query_permissions.py <items>` to list selected actions offline.
A denied service must not block independent items or appear as zero data.

## Service Regions

| Product | China service region | Outside-China service region |
|---------|----------------------|------------------------------|
| SAS | `cn-shanghai` | `ap-southeast-1` |
| WAF 3.0 | `cn-hangzhou` | `ap-southeast-1` |

These are service endpoints, not arbitrary ECS asset regions. Confirm which service
regions to query; do not copy SAS's Shanghai value into WAF commands. Discover the
WAF InstanceId separately in each confirmed WAF region. No WAF instance means
“not applicable”, not zero blocked requests. Endpoint errors are query failures.

## Core Workflow

Based on the user's query, execute the relevant module(s) below. Each module — and each data item within a module — can be executed independently. For APIs marked **multi-region**, query only the confirmed regions, then aggregate compatible validated results. The two-region examples apply when both regions were requested.

### Module 1: Security Overview

```bash
# 1a. Security Score (region-agnostic)
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent "$USER_AGENT"
# Validate the full saved response with: python3 scripts/overview_response.py score < response.json
# Exit 0/status=ok: display score (including zero). Exit 2/status=error: report failure.
# HTTP 200 with Score=null/missing is NOT success; do not substitute zero.
#
# NOTE: DescribeScreenScoreThread is currently unavailable (CalType not supported).
# Once supported, switch to the command below for score + historical trend:
#   START=$(python3 -c "import time; print(int((time.time()-86400*7)*1000))")
#   END=$(python3 -c "import time; print(int(time.time()*1000))")
#   aliyun sas describe-screen-score-thread \
#     --cal-type home_security_score \
#     --start-time "$START" --end-time "$END" \
#     --user-agent "$USER_AGENT"
#   Extract: Data.SocreThread[-1] = current score, full SocreThread list = historical trend

# 1b. Fixed Vulnerabilities (multi-region: sum FixTotal)
aliyun sas describe-vul-fix-statistics --region cn-shanghai --user-agent "$USER_AGENT"
aliyun sas describe-vul-fix-statistics --region ap-southeast-1 --user-agent "$USER_AGENT"

# 1c. Baseline Risk Statistics (multi-region: sum each Summary field)
aliyun sas get-check-risk-statistics --region cn-shanghai --user-agent "$USER_AGENT"
aliyun sas get-check-risk-statistics --region ap-southeast-1 --user-agent "$USER_AGENT"
# Extract: Summary.RiskCheckCnt, Summary.RiskWarningCnt,
#          Summary.HandledCheckTotal, Summary.HandledCheckToday
# Sum each field across regions

# 1d. Handled Alerts (multi-region: sum SuspiciousDealtCount)
aliyun sas get-defence-count --region cn-shanghai --user-agent "$USER_AGENT"
aliyun sas get-defence-count --region ap-southeast-1 --user-agent "$USER_AGENT"
```

### Module 2: Usage Info

```bash
# 2a. Service Duration + Subscription (region-agnostic)
aliyun sas describe-version-config --user-agent "$USER_AGENT"
# Validate the saved response: python3 scripts/overview_response.py times < response.json
# OpenTime → service opening; PostPayOpenTime → pay-as-you-go opening (ms).
# Report elapsed days separately, regardless of subscription/postpay coexistence.
# ReleaseTime → instance expiry; do not call it pay-as-you-go expiry.
# Missing/zero/invalid dates are unknown with a reason, never fabricated or forced N/A.
# Do not calculate duration from the undocumented legacy CreateTime field.

# 2b. Host Asset Info: fetch EVERY page before summing Cores.
# Run from this skill directory, after confirming the SAS regions.
python3 scripts/host_inventory.py --regions cn-shanghai ap-southeast-1 \
  --user-agent "$USER_AGENT"
# complete=true: total_count and total_cores cover both regions.
# Exit 2 / complete=false: report the failed region/page and partial counts;
# never present partial_cores as a full inventory. Do not add TotalCount per page.
# For host details, use the same page loop and retain each instance by Uuid.

# 2c. Uninstalled Clients (multi-region: sum TotalCount)
aliyun sas list-uninstall-aegis-machines --region cn-shanghai --current-page 1 --page-size 1 --user-agent "$USER_AGENT"
aliyun sas list-uninstall-aegis-machines --region ap-southeast-1 --current-page 1 --page-size 1 --user-agent "$USER_AGENT"
```

### Module 3: Security Operations

#### 3a. Risk Governance (region-agnostic, single API call)

```bash
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent "$USER_AGENT"
# Process Suggestions[] by SuggestType:
#   SS_AI_RISK → AI Risk
#     SSI_AISPM_RISK (AI security posture risks)
#     SSI_AI_VUL_RISK (AI application vulnerabilities)
#     SSI_AI_SENSITIVE_RISK (AI application plaintext keys)
#     Aggregate RiskCount by region
#   SS_SAS_CLOUD_HC → CSPM risks (aggregate by HIGH/MEDIUM/LOW and region)
#     Cloud: SSI_SAS_CLOUD_HC_HIGH / MEDIUM / LOW
#     Host:  SSI_SAS_HOST_HC_HIGH / MEDIUM / LOW
#   SS_KEY_CONFIG → Key Config (SubType not fixed; analyze Description for unknown SubTypes)
#     Aggregate RiskCount by region
#   SS_SAS_SYS_VUL → System Vulns (aggregate by HIGH/MEDIUM/LOW and region)
#     SSI_SAS_SYS_VUL_HIGH / SSI_SAS_SYS_VUL_MEDIUM / SSI_SAS_SYS_VUL_LOW
#   SS_SAS_EMG_VUL → Emergency Vulns (unfixed emergency vulnerabilities)
#     SSI_SAS_EMG_VUL
#   SS_SAS_APP_VUL → Application Vulns (aggregate by HIGH/MEDIUM and region)
#     SSI_SAS_APP_VUL_HIGH / SSI_SAS_APP_VUL_MEDIUM
#   SS_PRODUCT_CONNECT → Product Connection (asset protection not enabled)
#     SSI_PRODUCT_CONNECT (Description is JSON array with itemDescKey/itemDescText)
#   SS_SAS_ALARM → Security Response (see Module 3c)
#     SSI_SAS_ALARM_HIGH (emergency) / SSI_SAS_ALARM_MEDIUM (suspicious) / SSI_SAS_ALARM_LOW (reminder)
```

#### 3b. Security Protection — WAF Blocks (multi-region, two-step, WAF 3.0 only)

> **WAF Version Requirement**: This module uses WAF 3.0 API (Product: `waf-openapi`, Version: `2021-10-01`). WAF 2.0 instances (Version `2019-09-10`) are NOT compatible — fields such as `InstanceId` and `WafBlockSum` may be missing or structured differently. If the user's WAF instance is 2.0, inform them that this module is not supported for their instance version.
>
> **Region note**: `waf-openapi` (WAF 3.0) is a centralized-endpoint product — the China-site RegionId is `cn-hangzhou` (do NOT use `cn-shanghai`). The installed plugin help must report API `2021-10-01`. Do not mix WAF 2.0 parameters or add an unverified version override; update/check the plugin if its default differs.

```bash
# Step 1: Get WAF Instance ID (per region)
aliyun waf-openapi describe-instance --region cn-hangzhou --user-agent "$USER_AGENT"
aliyun waf-openapi describe-instance --region ap-southeast-1 --user-agent "$USER_AGENT"
# Extract: InstanceId from each region's response

# Step 2: Query WAF flow chart using each region's InstanceId
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
# Sum all WafBlockSum values from both regions
```

#### 3c. Security Response (region-agnostic, same API as 3a)

```bash
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent "$USER_AGENT"
# Process Suggestions[] where SuggestType == "SS_SAS_ALARM":
#   SSI_SAS_ALARM_HIGH   → Emergency alarm events count
#   SSI_SAS_ALARM_MEDIUM → Suspicious alarm events count
#   SSI_SAS_ALARM_LOW    → Reminder alarm events count
```

### Module 4: Asset Risk Trend

**Required host-risk inputs:** for each confirmed SAS region, obtain BOTH
`DescribeCloudCenterInstances.PageInfo.TotalCount` (with `MachineTypes=ecs`) and
`DescribeFieldStatistics.GroupedFields.RiskInstanceCount`. The latter API's
`InstanceCount` is not a substitute for the required TotalCount, even when zero.
Reuse a validated response from this session with the same account/region/filter
if available; otherwise execute both calls below. A count-only query needs only
`CurrentPage=1, PageSize=1`; full inventory pagination and CPU-core aggregation
belong to Module 2b when requested.

Validate both counts as nonnegative integers with matching scope and risk <= total.
Missing/failed input means host-risk is incomplete; preserve other results and do
not declare the whole module complete. With valid zero total, report ratio as
not applicable. Aggregate compatible regional counts before calculating the ratio.

```bash
# 4a. Host Assets (multi-region)
aliyun sas describe-cloud-center-instances \
  --region cn-shanghai --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent "$USER_AGENT"
# Extract: PageInfo.TotalCount

aliyun sas describe-field-statistics \
  --region cn-shanghai \
  --user-agent "$USER_AGENT"
# Extract: GroupedFields.RiskInstanceCount
# Repeat BOTH calls above for ap-southeast-1 when confirmed, then sum each metric.

# 4b. Container Assets (multi-region)
aliyun sas describe-container-field-statistics \
  --region cn-shanghai \
  --user-agent "$USER_AGENT"
# Extract: ClusterCount, RiskClusterCount
# Repeat for ap-southeast-1, sum both

# 4c. Cloud Product Assets (multi-region)
aliyun sas get-cloud-asset-summary \
  --region cn-shanghai \
  --user-agent "$USER_AGENT"
# Extract: GroupedFields.InstanceCountTotal, GroupedFields.InstanceRiskCountTotal
# Repeat for ap-southeast-1, sum both

# 4d. Trend Chart Data (multi-region)
START_MS=$(python3 scripts/query_parameters.py window --days "$TIME_RANGE_DAYS" --unit ms) || exit 2
END_MS=$(python3 -c "import time; print(int(time.time()*1000))")
aliyun sas describe-chart-data \
  --region cn-shanghai \
  --chart-id CID_ASSET_RISK_TREND \
  --report-id -1 \
  --time-start "$START_MS" --time-end "$END_MS" \
  --user-agent "$USER_AGENT"
# Returns time series: host / container / cloud risk counts
```

### Module 5: Billing & Subscription

```bash
# 5a. Query billing mode (from Module 2a response, can reuse cached result)
aliyun sas describe-version-config --user-agent "$USER_AGENT"
# Process the full response with: python3 scripts/overview_response.py billing < response.json
# IsPostpay indicates pay-as-you-go independently of subscription/trial evidence.
# Always parse PostPayModuleSwitch when supplied; do not gate it on IsPaidUser.
# Show coexistence, suspended service and unknown fields explicitly.
# See references/billing-semantics.md for the decision table and FAQ.

# 5c. Billing Details (BSS read permission required; failures remain visible)
BILLING_CYCLE=$(python3 scripts/query_parameters.py billing --cycle "$BILLING_CYCLE") || exit 2
aliyun bssopenapi query-bill \
  --region cn-shanghai \
  --billing-cycle "$BILLING_CYCLE" --product-code sas \
  --user-agent "$USER_AGENT"
# If the above returns a permission error, do NOT silently skip — inform the user (see Data Processing Rules §1)

aliyun bssopenapi query-bill \
  --region ap-southeast-1 \
  --billing-cycle "$BILLING_CYCLE" --product-code sas \
  --user-agent "$USER_AGENT"
# If the above returns a permission error, do NOT silently skip — inform the user (see Data Processing Rules §1)
# QueryBill is account-level: verify bill identity/coverage before combining endpoint results.
# Fetch all bill pages if reporting complete details/totals; do not sum duplicate bills.
# Explicitly report any failed requested coverage.
```

## Product Code Mapping

| Product Name | Code | Status Values |
|:---|:---|:---|
| Host and Container Security | `POST_HOST` | `1`: Enabled, `0`: Disabled |
| Vulnerability Fixing | `VUL` | `1`: Enabled, `0`: Disabled |
| CSPM | `CSPM` | `1`: Enabled, `0`: Disabled |
| Agentic SOC | `CTDR` | `1`: Enabled, `0`: Disabled |
| Agentless Detection | `AGENTLESS` | `1`: Enabled, `0`: Disabled |
| Serverless Asset Protection | `SERVERLESS` | `1`: Enabled, `0`: Disabled |
| Application Protection | `RASP` | `1`: Enabled, `0`: Disabled |
| Malicious File Detection | `SDK` | `1`: Enabled, `0`: Disabled |
| Log Management | `CTDR_STORAGE` | `1`: Enabled, `0`: Disabled |
| Anti-ransomware | `ANTI_RANSOMWARE` | `1`: Enabled, `0`: Disabled |

## Query Failures

Execute the workflow CLI queries through `scripts/cli_query.py -- aliyun ...` for
bounded transient retries (1s/2s waits, at most 3 attempts); host_inventory.py does
this internally. Permission, parameter and unsupported-service errors stop without
retry. Follow [query-errors.md](references/query-errors.md); report exhausted items
and continue independent requested queries, keeping partial results explicit.

## Data Processing Rules

1. **Multi-region aggregation**: query each confirmed service region separately. Sum compatible validated SAS/WAF counts only; account-level bills must not be blindly summed across endpoint regions.
   - **Permission error handling**: If a region returns a permission error (e.g., `Forbidden` or `NoPermission`), do NOT silently skip it. You MUST explicitly inform the user which regions succeeded and which failed, including the missing permission. Example: "Data retrieved from cn-shanghai, but ap-southeast-1 returned permission denied (missing sas:DescribeSecureSuggestion). Results only reflect cn-shanghai."
2. **Timestamps**: SAS APIs use **millisecond** timestamps. WAF APIs use **second** timestamps.
3. **PostPayModuleSwitch**: Is a **JSON string** — must `JSON.parse()` / `json.loads()` before reading.
4. **Score validation**: Run `scripts/overview_response.py score` on the complete JSON response when a score is requested. Missing/null/empty/non-numeric/non-finite scores are errors; retain RequestId for diagnosis. A real zero is valid. Do not infer a score from the presence of suggestions. **Score extraction**: Use `Score` field from `DescribeSecureSuggestion` response as current score. Note: `Score` is returned as a **string** (e.g., `"90.0"`), not a number — cast to float before comparison or display. Note: `DescribeScreenScoreThread` is currently unavailable (CalType not supported); once supported, switch to using the **last element** of `Data.SocreThread[]` as current score and the **full list** as historical trend.
5. **Security Response**: Extracted from `DescribeSecureSuggestion` where `SuggestType == "SS_SAS_ALARM"`. SubTypes: `SSI_SAS_ALARM_HIGH` (emergency), `SSI_SAS_ALARM_MEDIUM` (suspicious), `SSI_SAS_ALARM_LOW` (reminder).
6. **Timestamp formatting**: Convert millisecond timestamps to a readable date with explicit timezone (helpers use UTC).

## Success Verification

Verify **only the requested scope**, including every confirmed region/page and the
required business fields. HTTP/CLI success alone is insufficient. Record each item
as success, failed, unknown or not-applicable with validation evidence/reason; use
`scripts/verify_overview.py --expected <items>` on that result manifest to detect
missing items and partial completion. This checks coverage, not raw API semantics.
See [references/verification-method.md](references/verification-method.md) and
[acceptance-criteria.md](references/acceptance-criteria.md) for per-item checks.

## Cleanup

This skill is read-only (query operations only). No resources are created, so no cleanup is needed.

## Best Practices

1. Query every confirmed region before reporting full coverage; do not add unrequested regions.
2. Cache the `DescribeVersionConfig` response — it is used by both Module 2 and Module 5.
3. Use `--cli-query` (JMESPath) to extract specific fields and reduce output noise.
4. Set `--page-size 1` when only `TotalCount` is needed (e.g., `ListUninstallAegisMachines`).
5. WAF `DescribeFlowChart` requires a valid WAF instance ID — auto-fetch via `DescribeInstance` first; use the WAF service regions `cn-hangzhou` and `ap-southeast-1` that the user confirmed. Never reuse a SAS region or an InstanceId from a different WAF region.
6. Bill details require BSS read permission. Report denied regions/actions and partial coverage; keep independent SAS/WAF results. Never report a denied bill query as zero spend.
7. All timestamps returned by SAS are in **milliseconds** — divide by 1000 for human-readable conversion.

## Reference Links

| Document | Content |
|----------|---------|
| [references/billing-semantics.md](references/billing-semantics.md) | Billing evidence and coexistence FAQ |
| [references/related-apis.md](references/related-apis.md) | Full API and CLI command reference table |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions and policies |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect CLI patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
