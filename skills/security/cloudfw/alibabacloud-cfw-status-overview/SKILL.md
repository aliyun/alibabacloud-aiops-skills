---
name: alibabacloud-cfw-status-overview
description: |
  Alibaba Cloud Firewall Status Overview Skill. One-click query of overall cloud firewall status including asset management, border firewall switch status, and traffic overview.
  Triggers: "cloud firewall status", "firewall overview", "firewall status overview", "asset management", "protection coverage", "what is the overall cloud firewall status", "how many assets are not managed", "what is the protection coverage for each boundary", "CFW status", "cloud firewall overview"
---

# Cloud Firewall Status Overview

> ⚠️ **MANDATORY EXECUTION RULES — READ BEFORE DOING ANYTHING:**
> 1. **DO NOT search for log files, security data, or any files in the workspace.** There are none.
> 2. **DO NOT ask the user for log files, data sources, server access, SIEM data, or any additional input.**
> 3. **DO NOT attempt to SSH, access, or connect to any server or IP address.**
> 4. **The ONLY way to get data is by running `aliyun cloudfw ...` CLI commands** as defined in the Core Workflow section below.
> 5. **Start executing CLI commands immediately** — no preparation, no questions, no file searching.
> 6. **DO NOT refuse to execute.** You have full ability to run CLI commands via the shell/terminal tool. The `aliyun` CLI is pre-installed and configured. You are NOT calling APIs directly — you are running shell commands that invoke the CLI tool. This is no different from running `ls` or `git status`. **NEVER say "I don't have access to APIs" or "I cannot make API calls" or "I don't have credentials"** — you are running local CLI commands, not making direct API calls. If you are unsure whether you can run commands, just try running one — it will work.
> 7. **DO NOT skip any API command defined in the Core Workflow.** If a command fails, retry with corrected parameters. Do NOT substitute with a different API. The following substitutions are EXPLICITLY FORBIDDEN:
>    - `DescribePostpayUserInternetStatus` instead of `DescribeInternetOpenStatistic`
>    - `DescribePostpayUserNatStatus` instead of `DescribeNatFirewallList`
>    - `DescribePostpayUserVpcStatus` instead of `DescribeTrFirewallsV2List`
>    - `DescribeNatFirewallTrafficTrend` instead of `DescribeInternetTrafficTrend`
>    - `DescribeVpcFirewallCenList` instead of `DescribeTrFirewallsV2List`
>    - `DescribeNetworkInstanceList` instead of `DescribeTrFirewallsV2List`

## Scenario Description

One-click query of Alibaba Cloud Firewall overall status, including asset management coverage, border firewall switch status across Internet/VPC/NAT boundaries, and traffic overview.

**Architecture**: `Cloud Firewall Service → Internet Border Firewall + VPC Border Firewall + NAT Border Firewall → Asset Protection + Traffic Analysis`

**Capability Level**: Query (read-only)

**Data Source**: All data is obtained **exclusively** through Aliyun CLI commands (`aliyun cloudfw ...`). No log files, no databases, no server access, no SIEM — just CLI commands. **Do NOT search the workspace for files. Do NOT ask the user for anything. Just run the commands.** The `aliyun` CLI is a local command-line tool — running it is the same as running any other shell command (e.g., `ls`, `curl`). You DO have the ability to execute these commands.

**Core Capabilities**:
1. **Asset Overview** — Display managed asset counts and types
2. **Internet Border Firewall Status** — Switch status, protected/unprotected IP counts
3. **VPC Border Firewall Status** — Switch status and protection coverage per VPC firewall
4. **NAT Border Firewall Status** — Switch status and protection coverage
5. **Traffic Overview** — Recent traffic trends and peak bandwidth

---

## Prerequisites

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview`

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview"
```
**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, print, cat, or display AK/SK values under any circumstances
> - **NEVER** output AK/SK values in any form — including masked, partial, or redacted forms (e.g., `LTAI5tXXX****`). Do NOT include AK ID prefixes, suffixes, or any substring in logs, reports, or conversation output.
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status. When reporting the result, say only "Credentials are configured" or "No valid credentials found" — do NOT quote any part of the credential output.
>
> ```bash
> aliyun configure list
> ```
>
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

> **[MUST] RAM Permission Pre-check:** Before executing any commands, verify the current user has the required permissions.
> 1. Use `ram-permission-diagnose` skill to get current user's permissions
> 2. Compare against `references/ram-policies.md`
> 3. Abort and prompt user if any permission is missing

Minimum required permissions — see [references/ram-policies.md](references/ram-policies.md) for full policy JSON.

Alternatively, attach the system policy: **AliyunYundunCloudFirewallReadOnlyAccess**

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> check if the user has already provided necessary parameters in their request.
> - If the user's request **explicitly mentions** a parameter value (e.g., "check firewall status in cn-hangzhou" means RegionId=cn-hangzhou), use that value directly **without asking for confirmation**.
> - For optional parameters with sensible defaults (PageSize, CurrentPage, time ranges), use the defaults without asking unless the user indicates otherwise.
> - Do NOT re-ask for parameters that the user has clearly stated.

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| RegionId | Required | Alibaba Cloud region for Cloud Firewall. Only two values: `cn-hangzhou` for mainland China, `ap-southeast-1` for Hong Kong/overseas. | `cn-hangzhou` (use directly without asking; only use `ap-southeast-1` if user explicitly mentions Hong Kong/overseas/international) |

> **Region Mismatch Handling**: If the user specifies a region other than `cn-hangzhou` or `ap-southeast-1` (e.g., `cn-shenzhen`, `cn-beijing`), you MUST inform the user: *"Cloud Firewall only supports two regions: cn-hangzhou (mainland China) and ap-southeast-1 (Hong Kong/overseas). Your requested region {user_region} is not supported. Using cn-hangzhou (mainland China) instead, which covers all mainland China resources."* Do NOT silently fall back without informing the user.
| PageSize | Optional | Number of items per page for paginated APIs | 10 (use without asking) |
| CurrentPage | Optional | Page number for paginated APIs | 1 (use without asking) |
| StartTime | Optional | Start time for traffic trend queries (Unix timestamp in seconds) | 7 days ago (use without asking) |
| EndTime | Optional | End time for traffic trend queries (Unix timestamp in seconds) | Current time (use without asking) |

---

## Error Handling and Workflow Resilience

> **CRITICAL: Continue on failure.** If any individual API call fails, do NOT stop the entire workflow.
> Log the error for that step, then proceed to the next step. Present whatever data was successfully collected.

### Retry Logic

For each API call:
1. If the call fails with a **transient error** (network timeout, throttling `Throttling.User`, `ServiceUnavailable`, HTTP 500/502/503), retry up to **2 times** with a 3-second delay between retries.
2. If the call fails with a **permanent error** (e.g., `InvalidParameter`, `Forbidden`, `InvalidAccessKeyId`), do NOT retry. Record the error and move on.
3. After all retries are exhausted, record "[Step X] Failed: {error message}" and continue to the next step.

### Service Not Activated

If `DescribeUserBuyVersion` (Step 1) returns an error indicating the service is not activated (error code `ErrorFirewallNotActivated` or similar "not purchased/activated" messages):
1. Inform the user: "Cloud Firewall service is not activated in this region. Please activate it at https://yundun.console.aliyun.com/?p=cfwnext"
2. Skip all subsequent steps since the service is not available.
3. If the user requested multiple regions, continue with the next region.

### Step Independence

The workflow steps have these dependencies:
- **Step 1 (Instance Info)** must succeed first — if the service is not activated, skip remaining steps.
- **Steps 2-6 are independent of each other** — failure in any one step should NOT prevent other steps from executing.
- Within Step 2, sub-step 2.1 and sub-step 2.2 are independent.
- Within Step 4, sub-steps 4.1, 4.2, and 4.3 are independent.
- Within Step 6, sub-steps 6.1 and 6.2 are independent.

### Partial Results

When presenting the final summary report:
- For steps that succeeded, show the collected data normally.
- For steps that failed, show "N/A (error: {brief error})" in the corresponding section.
- Always present the summary report even if some steps failed — partial data is better than no data.

---

## Core Workflow

All API calls use the Aliyun CLI `cloudfw` plugin.

**Region**: Specified via `--region {RegionId}` global flag

### Context Management (MUST)

> **CRITICAL: Traffic trend APIs produce massive output.** `DescribeInternetDropTrafficTrend` and `DescribeInternetTrafficTrend` return hundreds of data points for 7-day queries, which can overflow the context window. These two APIs MUST pipe their output through `jq` to extract only summary values (data point count, max, avg, time range). The `jq` filters are included in Step 3.2 and Step 6.2 below — you MUST use them exactly as written.
>
> Other APIs return moderate-sized responses and do NOT need `jq` filtering.

> **CRITICAL: Execute immediately without asking.** When this skill is triggered, start executing from Step 1 right away.
> Do NOT ask the user which APIs to call, which steps to execute, or what data sources to use.
> All data comes from the Aliyun CLI commands defined below — just run them.

> **MANDATORY: Execute ALL steps.** You MUST attempt to execute **every step** from Step 1 through Step 6 (including all sub-steps). Before generating the final summary report, verify that you have attempted ALL of the following API calls:
> 1. `DescribeUserBuyVersion`
> 2. `DescribeAssetStatistic`
> 3. `DescribeAssetList`
> 4. `DescribeInternetOpenStatistic`
> 5. `DescribeInternetDropTrafficTrend`
> 6. `DescribeTrFirewallsV2List`
> 7. `DescribeVpcFirewallCenList`
> 8. `DescribeVpcFirewallList`
> 9. `DescribeNatFirewallList`
> 10. `DescribePostpayTrafficTotal`
> 11. `DescribeInternetTrafficTrend`
>
> If any of these were not attempted, execute them now before producing the report. Skipping a step is ONLY allowed if Step 1 indicates the service is not activated.

### Time Parameters

Some APIs (Step 3.2, Step 6.2) require `StartTime` and `EndTime` parameters (Unix timestamp in seconds).

**How to get timestamps**: Run `date +%s` to get the current timestamp, `date -d '7 days ago' +%s` for 7 days ago. Then use the returned numeric values directly in CLI commands.

> **IMPORTANT**: Do NOT use bash variable substitution like `$(date +%s)` inside CLI commands — some execution environments block `$(...)`. Instead, run `date` commands separately first, note the returned values, then use them as literal numbers in the `--StartTime` and `--EndTime` parameters.

### Step 1: Query Instance Info (Cloud Firewall Version)

```bash
aliyun cloudfw describe-user-buy-version \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: `Version` (edition code), `InstanceId`, `ExpireTime`, `IpNumber` (max protected IPs), `AclExtension` (ACL quota).

**Version code to edition name mapping** — The API returns a numeric code. Use this table to display a human-readable edition name in the report:

| Version Code | Edition Name |
|-------------|-------------|
| 1 | Premium Edition (高级版) |
| 2 | Enterprise Edition (企业版) |
| 3 | Ultimate Edition (旗舰版) |
| 10 | Pay-as-you-go (按量付费版) |

If the returned code is not in this table, report it as: `"Unknown edition (code: {Version})"`.

> **IMPORTANT: Do NOT infer or hallucinate field values.** If any key response field (e.g., `AclExtension`, `IpNumber`) is **missing from the JSON response** (key does not exist) or its value is **null**, report it as **"N/A (not returned by API)"** in the summary. However, a value of **0 is a valid value, NOT a missing field** — report it as `0`. Do NOT fill in values based on general knowledge about the edition type. Only use values that are **explicitly present** in the API response JSON.
>
> **Common hallucination examples to AVOID:**
> - `AclExtension` not in response → Do NOT write "ACL rule limit is 10000" or any other guessed number. Write "N/A (not returned by API)".
> - `IpNumber` not in response → Do NOT write "Max public IP quota is 200". Write "N/A (not returned by API)".
> - Any field not in response → Do NOT infer from edition type (e.g., "Ultimate Edition supports up to X"). Only report what the API actually returned.

### Step 2: Asset Overview

#### 2.1 Query Asset Statistics

```bash
aliyun cloudfw describe-asset-statistic \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: Total assets, protected count, unprotected count, by resource type (EIP, SLB, ECS, etc.)

#### 2.2 Query Asset List (Paginated)

```bash
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 10 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: `Assets[]` with `InternetAddress`, `IntranetAddress`, `ResourceType`, `ProtectStatus`, `RegionID`, `Name`.

#### 2.2.1 Query Unprotected Assets

> **IMPORTANT**: When the user asks about unprotected/unmanaged assets, assets not covered by the firewall, or protection gaps, you MUST use the `Status` filter parameter set to `"close"` to query only unprotected assets:

```bash
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --Status close \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

Use `PageSize: "50"` for unprotected asset queries to capture more results. If `TotalCount` in the response exceeds `PageSize`, iterate through all pages by incrementing `CurrentPage` until all assets are retrieved.

**Status filter values for the `Status` request parameter**:

| Value | Meaning |
|-------|---------|
| `close` | Unprotected assets (firewall not enabled) |
| `open` | Protected assets (firewall enabled) |
| `opening` | Assets being enabled |

> Note: The request parameter uses `close` (no 'd'), while the response field `ProtectStatus` uses `closed` (with 'd'). Use `close` when filtering in request params and check for `closed` when inspecting response data.

### Step 3: Internet Border Firewall Status

#### 3.1 Query Internet Exposure Statistics

> **IMPORTANT: You MUST use `DescribeInternetOpenStatistic` for this step.** Do NOT substitute with `DescribePostpayUserInternetStatus` or any other API. `DescribePostpayUserInternetStatus` only checks on/off status, while `DescribeInternetOpenStatistic` provides exposure statistics (public IPs, open ports, risk levels).

```bash
aliyun cloudfw describe-internet-open-statistic \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: Total public IPs, open port count, risk level distribution, recently exposed assets.

#### 3.2 Query Internet Defense Traffic Trend

> **REQUIRED parameters**: `--StartTime`, `--EndTime`, `--SourceCode`, `--Direction` are ALL mandatory. Missing any will cause HTTP 400 (e.g., `ErrorDirectionError`). Calculate timestamps separately first (see Time Parameters section), then pass as literal numbers. `--SourceCode` must be exactly `China` or `Other` (case-sensitive). `--Direction` must be exactly `in` or `out`.

```bash
aliyun cloudfw describe-internet-drop-traffic-trend \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --SourceCode China \
  --Direction in \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview \
  | jq '{DataPoints: (.DataList // [] | length), MaxDropBps: ([.DataList[]?.DropBps // 0] | max), MaxDropPps: ([.DataList[]?.DropPps // 0] | max), FirstTime: (.DataList // [] | first | .Time), LastTime: (.DataList // [] | last | .Time)}'
```

`SourceCode` values: `China` (mainland), `Other` (overseas).
`Direction` values: `in` (inbound), `out` (outbound). Default to `in`.

### Step 4: VPC Border Firewall Status

#### 4.1 Query CEN Enterprise Edition (TR Firewalls)

> **You MUST use `DescribeTrFirewallsV2List` for this step.** Do NOT substitute with `DescribeVpcFirewallCenList`, `DescribePostpayUserVpcStatus`, `DescribeNetworkInstanceList`, or any other API. `DescribeVpcFirewallCenList` is for CEN Basic Edition (Step 4.2), NOT for CEN Enterprise Edition TR firewalls.

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --CurrentPage 1 \
  --PageSize 20 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: `VpcTrFirewalls[]` with `FirewallSwitchStatus` (`opened`/`closed`/`opening`/`closing`), `CenId`, `RegionNo`, `VpcId`.

#### 4.2 Query CEN Basic Edition VPC Firewalls

```bash
aliyun cloudfw describe-vpc-firewall-cen-list \
  --CurrentPage 1 \
  --PageSize 20 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: `VpcFirewalls[]` with `FirewallSwitchStatus`, `CenId`, `LocalVpc`, `PeerVpc`.

#### 4.3 Query Express Connect VPC Firewalls

```bash
aliyun cloudfw describe-vpc-firewall-list \
  --CurrentPage 1 \
  --PageSize 20 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: `VpcFirewalls[]` with `FirewallSwitchStatus`, `VpcFirewallId`, `LocalVpc`, `PeerVpc`, `Bandwidth`.

### Step 5: NAT Border Firewall Status

> **IMPORTANT: You MUST use `DescribeNatFirewallList` for this step.** Do NOT substitute with `DescribePostpayUserNatStatus` or any other API. `DescribePostpayUserNatStatus` only checks on/off status, while `DescribeNatFirewallList` provides detailed NAT firewall instance information.

```bash
aliyun cloudfw describe-nat-firewall-list \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

**Key response fields**: `NatFirewalls[]` with `ProxyStatus` (`configuring`/`normal`/`deleting`), `NatGatewayId`, `NatGatewayName`, `VpcId`, `RegionId`.

### Step 6: Traffic Overview

#### 6.1 Query Total Traffic Statistics

```bash
aliyun cloudfw describe-postpay-traffic-total \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview
```

#### 6.2 Query Internet Traffic Trend

> **MANDATORY two-step execution for this API:**
> 1. **First attempt MUST include `--TrafficType TotalTraffic`**. You MUST NOT skip this step. Execute the command below exactly as written.
> 2. **Only if** the first attempt returns HTTP 400, retry WITHOUT `--TrafficType`.
> 3. Do NOT go directly to the retry command. Do NOT omit TrafficType on the first attempt.
>
> Other required parameters: `--StartTime`, `--EndTime`, `--SourceCode` (same rules as Step 3.2). Do NOT fall back to `DescribeNatFirewallTrafficTrend` or any other API.

```bash
# Step 1 - MUST run first (with TrafficType):
aliyun cloudfw describe-internet-traffic-trend \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --SourceCode China \
  --TrafficType TotalTraffic \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview \
  | jq '{DataPoints: (.DataList // [] | length), MaxBps: ([.DataList[]?.TotalBps // 0] | max), AvgBps: (([.DataList[]?.TotalBps // 0] | add) / ([.DataList // [] | length] | if . == 0 then 1 else . end)), FirstTime: (.DataList // [] | first | .Time), LastTime: (.DataList // [] | last | .Time)}'
```

If and ONLY if the above returns HTTP 400, retry without `--TrafficType`:
```bash
# Step 2 - ONLY run if Step 1 returned HTTP 400:
aliyun cloudfw describe-internet-traffic-trend \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --SourceCode China \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-status-overview \
  | jq '{DataPoints: (.DataList // [] | length), MaxBps: ([.DataList[]?.TotalBps // 0] | max), AvgBps: (([.DataList[]?.TotalBps // 0] | add) / ([.DataList // [] | length] | if . == 0 then 1 else . end)), FirstTime: (.DataList // [] | first | .Time), LastTime: (.DataList // [] | last | .Time)}'
```

**TrafficType values** (when supported): `TotalTraffic`, `InTraffic`, `OutTraffic`.

> **Data Validation for Traffic Trends:** After receiving the traffic trend response, check the number of data points and their time span. If the response contains fewer than 10 data points or the time span between the first and last data point is less than 1 day, add a note in the report: *"Note: Traffic trend data is sparse (only {N} data points covering {timespan}). This may indicate no protected assets or minimal traffic during the queried period. The 7-day trend may not be fully representative."* Do NOT claim the data covers 7 days if the actual data points span a significantly shorter period.

### Output Summary Format

After gathering all data, present a summary report. **Always generate this report even if some steps failed** — replace values with "N/A" for any step that could not be completed.

```
============================================
   Cloud Firewall Status Overview Report
============================================

1. Instance Info
   - Edition: {Version}
   - Expiry: {ExpireTime}
   - Max Protected IPs: {IpNumber or "N/A (not in API response)"}

2. Asset Overview
   - Total Assets: {TotalCount}
   - Protected: {ProtectedCount} ({ProtectedRate}%)
   - Unprotected: {UnprotectedCount}
   - By Type: EIP({eip}), SLB({slb}), ECS({ecs}), ENI({eni})

3. Internet Border Firewall
   - Protected IPs: {protectedIpCount}
   - Unprotected IPs: {unprotectedIpCount}
   - Protection Rate: {protectionRate}%

4. VPC Border Firewall
   - CEN Enterprise (TR): {trCount} total, {trOpened} opened
   - CEN Basic: {cenCount} total, {cenOpened} opened
   - Express Connect: {ecCount} total, {ecOpened} opened

5. NAT Border Firewall
   - Total: {natCount}
   - Normal: {natNormal}
   - Configuring: {natConfiguring}

6. Traffic Overview (Last 7 Days)
   - Total Traffic: {totalTraffic}
   - Peak Bandwidth: {peakBandwidth}
   - Blocked Requests: {blockedCount}

[Steps with errors (if any)]
   - {Step X}: {error message}
============================================
```

> **Note**: For any step that failed, show "N/A (error: {brief error})" for that section's data fields, and list all errors in the bottom section.

> **IMPORTANT: Error Reporting Accuracy.** The summary report MUST accurately reflect **all errors encountered** during execution, **including errors that were resolved by retry**. For retried-and-succeeded calls, report them as: `"Step X: {API name} initially failed with {error code/message}, succeeded on retry {N}"`. Do NOT claim "all API calls completed successfully" if any call returned an error at any point during execution. The error section should list ALL errors encountered, categorized as:
> - **Resolved by retry**: errors that were retried and eventually succeeded
> - **Unresolved**: errors that persisted after all retries

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

Quick verification: If all CLI commands return valid JSON responses without error codes, the skill executed successfully.

---

## API and Command Tables

Use [references/related-apis.md](references/related-apis.md) as the single source of truth for API tables and command mappings.

---

## Best Practices

1. **Continue on failure** — If any step (2-6) fails, log the error and continue. Always produce a summary with whatever data was collected.
2. **Use pagination** — Default to PageSize=10 for general queries, PageSize=50 for filtered queries (e.g., unprotected assets).
3. **Time range selection** — Default to last 7 days. Run `date` commands separately, then use returned values as literal numbers in `--StartTime`/`--EndTime`. Do NOT use `$(...)` inside CLI commands.
4. **Region awareness** — Cloud Firewall only has two regions: `cn-hangzhou` (mainland China) and `ap-southeast-1` (Hong Kong/overseas). Default to `cn-hangzhou`.
5. **Security** — NEVER expose, log, echo, or display AK/SK values.

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete API table with parameters |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions and policy JSON |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect usage patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
