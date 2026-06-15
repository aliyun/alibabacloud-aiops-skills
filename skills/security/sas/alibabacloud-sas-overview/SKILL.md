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
    "vulnerability fix", "baseline risk", "handled alerts",
    "host assets", "uninstalled clients",
    "risk governance", "WAF blocks", "asset risk trend",
    "SAS billing", "订阅状态", "账单"
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

## Observability

**User-Agent Template**:
```
AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
```

**Session-ID Generation Rule**:
- Generate a UUID v4 (e.g., `550e8400-e29b-41d4-a716-446655440000`) at the start of each skill execution session.
- The same `{session-id}` MUST be used for ALL `aliyun` CLI commands within a single session, ensuring all requests from one execution can be correlated in logs.
- Each new skill invocation MUST generate a fresh session-id.

**Usage**: Pass the full UA string via the `--user-agent` flag on every `aliyun` CLI command:
```bash
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
aliyun sas describe-version-config --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/$SESSION_ID"
```

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.

> **Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

Install required CLI plugins:

```bash
aliyun plugin install --names aliyun-cli-sas aliyun-cli-waf-openapi aliyun-cli-bssopenapi
```

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
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## Parameters

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, WAF InstanceId, BillingCycle, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| Regions | Yes | SAS regions to aggregate data from | `cn-shanghai`, `ap-southeast-1` |
| WAF Instance ID | Auto-fetched | Auto-fetched via WAF `DescribeInstance` for `DescribeFlowChart` | Auto |
| Billing Cycle | Only for billing | Billing month in `YYYY-MM` format | Current month |
| Time Range | No | Days of history for score/trend queries | `7` (last 7 days) |

## RAM Permissions

See [references/ram-policies.md](references/ram-policies.md) for the full RAM policy JSON.

Required: `AliyunYundunSASReadOnlyAccess`, `AliyunWAFReadOnlyAccess`, `AliyunBSSReadOnlyAccess`.

## Core Workflow

Based on the user's query, execute the relevant module(s) below. Each module — and each data item within a module — can be executed independently. For APIs marked **multi-region**, always query both `cn-shanghai` and `ap-southeast-1`, then **sum** the results.

### Module 1: Security Overview

```bash
# 1a. Security Score (region-agnostic)
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: Score field from response as current security score
#
# NOTE: DescribeScreenScoreThread is currently unavailable (CalType not supported).
# Once supported, switch to the command below for score + historical trend:
#   START=$(python3 -c "import time; print(int((time.time()-86400*7)*1000))")
#   END=$(python3 -c "import time; print(int(time.time()*1000))")
#   aliyun sas describe-screen-score-thread \
#     --cal-type home_security_score \
#     --start-time "$START" --end-time "$END" \
#     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
#   Extract: Data.SocreThread[-1] = current score, full SocreThread list = historical trend

# 1b. Fixed Vulnerabilities (multi-region: sum FixTotal)
aliyun sas describe-vul-fix-statistics --region cn-shanghai --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
aliyun sas describe-vul-fix-statistics --region ap-southeast-1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}

# 1c. Baseline Risk Statistics (multi-region: sum each Summary field)
aliyun sas get-check-risk-statistics --region cn-shanghai --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
aliyun sas get-check-risk-statistics --region ap-southeast-1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: Summary.RiskCheckCnt, Summary.RiskWarningCnt,
#          Summary.HandledCheckTotal, Summary.HandledCheckToday
# Sum each field across regions

# 1d. Handled Alerts (multi-region: sum SuspiciousDealtCount)
aliyun sas get-defence-count --region cn-shanghai --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
aliyun sas get-defence-count --region ap-southeast-1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
```

### Module 2: Usage Info

```bash
# 2a. Service Duration + Subscription (region-agnostic)
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Check IsPaidUser first:
#   IsPaidUser == true  → Extract CreateTime, calculate (now - CreateTime) as days
#   IsPaidUser == false → Service duration not applicable, display N/A
# Extract: ReleaseTime → subscription expiry (pre-pay only)

# 2b. Host Asset Info (multi-region: sum TotalCount and Cores)
aliyun sas describe-cloud-center-instances \
  --region cn-shanghai --machine-types ecs --current-page 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
aliyun sas describe-cloud-center-instances \
  --region ap-southeast-1 --machine-types ecs --current-page 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: PageInfo.TotalCount (sum across regions) for host count
# Extract: Sum all instances' Cores field for total core count
# Optionally list host details if user requests

# 2c. Uninstalled Clients (multi-region: sum TotalCount)
aliyun sas list-uninstall-aegis-machines --region cn-shanghai --current-page 1 --page-size 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
aliyun sas list-uninstall-aegis-machines --region ap-southeast-1 --current-page 1 --page-size 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
```

### Module 3: Security Operations

#### 3a. Risk Governance (region-agnostic, single API call)

```bash
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
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

```bash
# Step 1: Get WAF Instance ID (per region)
aliyun waf-openapi describe-instance --region cn-shanghai --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
aliyun waf-openapi describe-instance --region ap-southeast-1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: InstanceId from each region's response

# Step 2: Query WAF flow chart using each region's InstanceId
START_SEC=$(python3 -c "import time; print(int(time.time()-86400*7))")
aliyun waf-openapi describe-flow-chart \
  --region cn-shanghai \
  --instance-id "<InstanceId from cn-shanghai>" \
  --start-timestamp "$START_SEC" \
  --interval 3600 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
aliyun waf-openapi describe-flow-chart \
  --region ap-southeast-1 \
  --instance-id "<InstanceId from ap-southeast-1>" \
  --start-timestamp "$START_SEC" \
  --interval 3600 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Sum all WafBlockSum values from both regions
```

#### 3c. Security Response (region-agnostic, same API as 3a)

```bash
aliyun sas describe-secure-suggestion --cal-type home_security_score --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Process Suggestions[] where SuggestType == "SS_SAS_ALARM":
#   SSI_SAS_ALARM_HIGH   → Emergency alarm events count
#   SSI_SAS_ALARM_MEDIUM → Suspicious alarm events count
#   SSI_SAS_ALARM_LOW    → Reminder alarm events count
```

### Module 4: Asset Risk Trend

```bash
# 4a. Host Assets (multi-region)
aliyun sas describe-cloud-center-instances \
  --region cn-shanghai --machine-types ecs --current-page 1 --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: PageInfo.TotalCount

aliyun sas describe-field-statistics \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: GroupedFields.RiskInstanceCount
# Repeat for ap-southeast-1, sum both

# 4b. Container Assets (multi-region)
aliyun sas describe-container-field-statistics \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: ClusterCount, RiskClusterCount
# Repeat for ap-southeast-1, sum both

# 4c. Cloud Product Assets (multi-region)
aliyun sas get-cloud-asset-summary \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Extract: GroupedFields.InstanceCountTotal, GroupedFields.InstanceRiskCountTotal
# Repeat for ap-southeast-1, sum both

# 4d. Trend Chart Data (multi-region)
START_MS=$(python3 -c "import time; print(int((time.time()-86400*7)*1000))")
END_MS=$(python3 -c "import time; print(int(time.time()*1000))")
aliyun sas describe-chart-data \
  --region cn-shanghai \
  --chart-id CID_ASSET_RISK_TREND \
  --report-id -1 \
  --time-start "$START_MS" --time-end "$END_MS" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Returns time series: host / container / cloud risk counts
```

### Module 5: Billing & Subscription

```bash
# 5a. Query billing mode (from Module 2a response, can reuse cached result)
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# Check IsPaidUser field to determine billing mode:
#
# If IsPaidUser == true → Pre-pay (subscription) user:
#   Extract CreateTime → purchase date (convert ms timestamp to YYYY-MM-DD)
#   Extract ReleaseTime → expiry date (convert ms timestamp to YYYY-MM-DD)
#
# If IsPaidUser == false → Post-pay user:
#   Extract PostPayModuleSwitch (JSON string — must parse)
#   Map codes to product names using the table below:
#     POST_HOST → Host and Container Security
#     VUL → Vulnerability Fixing
#     CSPM → CSPM
#     CTDR → Agentic SOC
#     AGENTLESS → Agentless Detection
#     SERVERLESS → Serverless Asset Protection
#     RASP → Application Protection
#     SDK → Malicious File Detection
#     CTDR_STORAGE → Log Management
#     ANTI_RANSOMWARE → Anti-ransomware
#   Value 1 = Enabled, 0 = Disabled

# 5c. Billing Details (try each region, skip on permission error)
BILLING_CYCLE=$(date +%Y-%m)
aliyun bssopenapi query-bill \
  --region cn-shanghai \
  --billing-cycle "$BILLING_CYCLE" --product-code sas \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# If the above returns a permission error, do NOT silently skip — inform the user (see Data Processing Rules §1)

aliyun bssopenapi query-bill \
  --region ap-southeast-1 \
  --billing-cycle "$BILLING_CYCLE" --product-code sas \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session-id}
# If the above returns a permission error, do NOT silently skip — inform the user (see Data Processing Rules §1)
# Aggregate results from whichever regions succeeded, and explicitly report any skipped regions
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

## Data Processing Rules

1. **Multi-region aggregation**: APIs requiring regions must query `cn-shanghai` + `ap-southeast-1` separately, then **sum** the numeric results.
   - **Permission error handling**: If a region returns a permission error (e.g., `Forbidden` or `NoPermission`), do NOT silently skip it. You MUST explicitly inform the user which regions succeeded and which failed, including the missing permission. Example: "Data retrieved from cn-shanghai, but ap-southeast-1 returned permission denied (missing sas:DescribeSecureSuggestion). Results only reflect cn-shanghai."
2. **Timestamps**: SAS APIs use **millisecond** timestamps. WAF APIs use **second** timestamps.
3. **PostPayModuleSwitch**: Is a **JSON string** — must `JSON.parse()` / `json.loads()` before reading.
4. **Score extraction**: Use `Score` field from `DescribeSecureSuggestion` response as current score. Note: `Score` is returned as a **string** (e.g., `"90.0"`), not a number — cast to float before comparison or display. Note: `DescribeScreenScoreThread` is currently unavailable (CalType not supported); once supported, switch to using the **last element** of `Data.SocreThread[]` as current score and the **full list** as historical trend.
5. **Security Response**: Extracted from `DescribeSecureSuggestion` where `SuggestType == "SS_SAS_ALARM"`. SubTypes: `SSI_SAS_ALARM_HIGH` (emergency), `SSI_SAS_ALARM_MEDIUM` (suspicious), `SSI_SAS_ALARM_LOW` (reminder).
6. **Timestamp formatting**: Convert ms timestamps to `YYYY-MM-DD HH:mm:ss` for display.

## Success Verification

See [references/verification-method.md](references/verification-method.md) for step-by-step verification commands.

## Cleanup

This skill is read-only (query operations only). No resources are created, so no cleanup is needed.

## Best Practices

1. Always query **both** `cn-shanghai` and `ap-southeast-1` for multi-region APIs before aggregating.
2. Cache the `DescribeVersionConfig` response — it is used by both Module 2 and Module 5.
3. Use `--cli-query` (JMESPath) to extract specific fields and reduce output noise.
4. Set `--page-size 1` when only `TotalCount` is needed (e.g., `ListUninstallAegisMachines`).
5. WAF `DescribeFlowChart` requires a valid WAF instance ID — auto-fetch via `DescribeInstance` first; query both `cn-shanghai` and `ap-southeast-1`.
6. Billing queries (`QueryBill`) require `--region` — try each region (`cn-shanghai`, `ap-southeast-1`) in turn; skip any region that returns a permission error.
7. All timestamps returned by SAS are in **milliseconds** — divide by 1000 for human-readable conversion.

## Reference Links

| Document | Content |
|----------|---------|
| [references/related-apis.md](references/related-apis.md) | Full API and CLI command reference table |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions and policies |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect CLI patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
