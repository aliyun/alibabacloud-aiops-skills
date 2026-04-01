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

## Scenario Description

One-click query of Alibaba Cloud Firewall overall status, including asset management coverage, border firewall switch status across Internet/VPC/NAT boundaries, and traffic overview.

**Architecture**: `Cloud Firewall Service → Internet Border Firewall + VPC Border Firewall + NAT Border Firewall → Asset Protection + Traffic Analysis`

**Capability Level**: Query (read-only)

**Data Source**: All data is obtained **exclusively** through Aliyun CLI commands (`aliyun cloudfw ...`). No log files, no databases, no server access, no SIEM — just CLI commands. **Do NOT search the workspace for files. Do NOT ask the user for anything. Just run the commands.**

**Core Capabilities**:
1. **Asset Overview** — Display managed asset counts and types
2. **Internet Border Firewall Status** — Switch status, protected/unprotected IP counts
3. **VPC Border Firewall Status** — Switch status and protection coverage per VPC firewall
4. **NAT Border Firewall Status** — Switch status and protection coverage
5. **Traffic Overview** — Recent traffic trends and peak bandwidth

---

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, print, cat, or display AK/SK values under any circumstances
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
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

**User-Agent**: All commands must include `--user-agent AlibabaCloud-Agent-Skills`
**Region**: Specified via `--region {RegionId}` global flag

> **CRITICAL: Execute immediately without asking.** When this skill is triggered, start executing from Step 1 right away.
> Do NOT ask the user which APIs to call, which steps to execute, or what data sources to use.
> All data comes from the Aliyun CLI commands defined below — just run them.

### Time Parameters

Some APIs (Step 3.2, Step 6.2) require `StartTime` and `EndTime` parameters (Unix timestamp in seconds).

**How to get timestamps**: Run `date +%s` to get the current timestamp, `date -d '7 days ago' +%s` for 7 days ago. Then use the returned numeric values directly in CLI commands.

> **IMPORTANT**: Do NOT use bash variable substitution like `$(date +%s)` inside CLI commands — some execution environments block `$(...)`. Instead, run `date` commands separately first, note the returned values, then use them as literal numbers in the `--StartTime` and `--EndTime` parameters.

### Step 1: Query Instance Info (Cloud Firewall Version)

```bash
aliyun cloudfw DescribeUserBuyVersion \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: `Version` (edition), `InstanceId`, `ExpireTime`, `IpNumber` (max protected IPs), `AclExtension` (ACL quota).

### Step 2: Asset Overview

#### 2.1 Query Asset Statistics

```bash
aliyun cloudfw DescribeAssetStatistic \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: Total assets, protected count, unprotected count, by resource type (EIP, SLB, ECS, etc.)

#### 2.2 Query Asset List (Paginated)

```bash
aliyun cloudfw DescribeAssetList \
  --CurrentPage 1 \
  --PageSize 10 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: `Assets[]` with `InternetAddress`, `IntranetAddress`, `ResourceType`, `ProtectStatus`, `RegionID`, `Name`.

#### 2.2.1 Query Unprotected Assets

> **IMPORTANT**: When the user asks about unprotected/unmanaged assets, assets not covered by the firewall, or protection gaps, you MUST use the `Status` filter parameter set to `"close"` to query only unprotected assets:

```bash
aliyun cloudfw DescribeAssetList \
  --CurrentPage 1 \
  --PageSize 50 \
  --Status close \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
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

```bash
aliyun cloudfw DescribeInternetOpenStatistic \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: Total public IPs, open port count, risk level distribution, recently exposed assets.

#### 3.2 Query Internet Defense Traffic Trend

```bash
aliyun cloudfw DescribeInternetDropTrafficTrend \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --SourceCode China \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

`SourceCode` values: `China` (mainland), `Other` (overseas).

### Step 4: VPC Border Firewall Status

#### 4.1 Query CEN Enterprise Edition (TR Firewalls)

```bash
aliyun cloudfw DescribeTrFirewallsV2List \
  --CurrentPage 1 \
  --PageSize 20 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: `VpcTrFirewalls[]` with `FirewallSwitchStatus` (`opened`/`closed`/`opening`/`closing`), `CenId`, `RegionNo`, `VpcId`.

#### 4.2 Query CEN Basic Edition VPC Firewalls

```bash
aliyun cloudfw DescribeVpcFirewallCenList \
  --CurrentPage 1 \
  --PageSize 20 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: `VpcFirewalls[]` with `FirewallSwitchStatus`, `CenId`, `LocalVpc`, `PeerVpc`.

#### 4.3 Query Express Connect VPC Firewalls

```bash
aliyun cloudfw DescribeVpcFirewallList \
  --CurrentPage 1 \
  --PageSize 20 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: `VpcFirewalls[]` with `FirewallSwitchStatus`, `VpcFirewallId`, `LocalVpc`, `PeerVpc`, `Bandwidth`.

### Step 5: NAT Border Firewall Status

```bash
aliyun cloudfw DescribeNatFirewallList \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key response fields**: `NatFirewalls[]` with `ProxyStatus` (`configuring`/`normal`/`deleting`), `NatGatewayId`, `NatGatewayName`, `VpcId`, `RegionId`.

### Step 6: Traffic Overview

#### 6.1 Query Total Traffic Statistics

```bash
aliyun cloudfw DescribePostpayTrafficTotal \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 6.2 Query Internet Traffic Trend

```bash
aliyun cloudfw DescribeInternetTrafficTrend \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --SourceCode China \
  --TrafficType TotalTraffic \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

**TrafficType values**: `TotalTraffic`, `InTraffic`, `OutTraffic`.

### Output Summary Format

After gathering all data, present a summary report. **Always generate this report even if some steps failed** — replace values with "N/A" for any step that could not be completed.

```
============================================
   Cloud Firewall Status Overview Report
============================================

1. Instance Info
   - Edition: {Version}
   - Expiry: {ExpireTime}
   - Max Protected IPs: {IpNumber}

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

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

Quick verification: If all CLI commands return valid JSON responses without error codes, the skill executed successfully.

---

## API and Command Tables

Use [references/related-apis.md](references/related-apis.md) as the single source of truth for API tables and command mappings.

---

## Best Practices

1. **Query in order** — Start with instance info (Step 1) to confirm the service is active before querying details. If Step 1 fails with a service-not-activated error, stop and guide the user.
2. **Continue on failure** — If any step (2-6) fails, log the error and continue with the remaining steps. Always produce a summary with whatever data was collected.
3. **Use pagination** — For asset lists, use `CurrentPage` and `PageSize` to handle large datasets. Default to PageSize=10 for general queries, PageSize=50 for filtered queries (e.g., unprotected assets).
4. **Time range selection** — For traffic trends, default to the last 7 days. Use Unix timestamps in seconds. Calculate with: `date -d '7 days ago' +%s` for start time and `date +%s` for end time. Run these commands separately, then use the returned values as literal numbers in `--StartTime` and `--EndTime`. Do NOT use `$(...)` substitution inside CLI commands.
5. **Region awareness** — Cloud Firewall only has two regions: `cn-hangzhou` (mainland China) and `ap-southeast-1` (Hong Kong/overseas). Default to `cn-hangzhou` unless user specifies otherwise.
6. **Error handling** — If `DescribeUserBuyVersion` returns an error, the Cloud Firewall service may not be activated. Prompt the user to activate it at https://yundun.console.aliyun.com/?p=cfwnext
7. **Rate limiting** — Space API calls to avoid throttling. If you receive a `Throttling.User` error, wait 3 seconds and retry.
8. **Security** — NEVER expose, log, echo, or display AK/SK values.
9. **Retry on transient errors** — For network timeouts or 5xx errors, retry up to 2 times with a 3-second delay.

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete API table with parameters |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions and policy JSON |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect usage patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
