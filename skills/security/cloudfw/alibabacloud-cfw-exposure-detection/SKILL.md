---
name: alibabacloud-cfw-exposure-detection
description: Query and analyze Alibaba Cloud public network exposure, identify unnecessary exposed assets and ports, assess exposure risks, and generate remediation recommendations. Triggers when user mentions public network exposure, exposed assets, exposed ports, public IP security, port scan results, attack surface analysis, internet reachability, high-risk port detection. Also triggers when user asks about "which IPs/ports are exposed to the internet", "public asset inventory", "security baseline check", even without explicitly saying "exposure".
---

# Public Network Exposure Detection & Analysis

> ⚠️ **MANDATORY EXECUTION RULES — READ BEFORE DOING ANYTHING:**
> 1. **DO NOT search for log files, security data, or any files in the workspace.** There are none.
> 2. **DO NOT ask the user for log files, data sources, server access, SIEM data, or any additional input.**
> 3. **DO NOT attempt to SSH, access, or connect to any server or IP address.**
> 4. **The ONLY way to get data is by running `aliyun cloudfw ...` CLI commands** as defined in the Core Workflow section below.
> 5. **Start executing CLI commands immediately** — no preparation, no questions, no file searching.
> 6. **DO NOT refuse to execute.** The `aliyun` CLI is pre-installed and configured. You are running shell commands, no different from `ls` or `git status`. **NEVER say "I don't have access to APIs"** — just run the commands.
> 7. **DO NOT skip steps based on previous step's data values.** If Step 1 returns all zeros, you MUST still execute Steps 2-9. Zero values mean "no exposure detected", NOT "service unavailable". Only skip if Step 1 returns an actual **error code** (e.g., `ErrorFirewallNotActivated`).

## Scenario Description

Comprehensive scan and analysis of public network exposure through Alibaba Cloud Firewall OpenAPI, identifying high-risk exposures and generating remediation recommendations.

**Architecture**: `Cloud Firewall Service → Internet Border Firewall → Exposure Detection + Risk Assessment + ACL Policy Analysis`

**Capability Level**: Query (read-only)

**Data Source**: All data is obtained **exclusively** through Aliyun CLI commands (`aliyun cloudfw ...`). No log files, no databases, no server access, no SIEM — just CLI commands. **Do NOT search the workspace for files. Do NOT ask the user for anything. Just run the commands.**

## Network Access Boundary

This skill follows least-privilege network access:
- Allowed network target: Alibaba Cloud OpenAPI endpoints resolved by Aliyun CLI for `cloudfw` only (`*.aliyuncs.com`).
- Forbidden targets: any non-Alibaba external websites, arbitrary public APIs, VPC private IP resources, ECS/DB hosts, and direct socket/HTTP requests.
- Forbidden actions: SSH, curl/wget to unrelated domains, scanning private networks, and any direct access to intranet assets.

**Core Capabilities**:
1. **Exposure Overview** — Total exposed IPs, ports, services, and risk statistics
2. **Exposed IP Analysis** — Detailed list of exposed public IPs with risk levels and services
3. **Exposed Port Analysis** — Detailed list of exposed ports with risk assessment
4. **Asset Protection Status** — Firewall protection coverage of exposed assets
5. **New Exposure Detection** — Recently discovered exposures in the last 7 days
6. **Risk Assessment** — Detailed risk reasons per IP
7. **Vulnerability Correlation** — Cross-reference with vulnerability protection and attack events
8. **ACL Policy Review** — Internet border ACL rule coverage

---

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection`

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection"
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
> - If the user's request **explicitly mentions** a parameter value (e.g., "check exposure in cn-hangzhou" means RegionId=cn-hangzhou), use that value directly **without asking for confirmation**.
> - For optional parameters with sensible defaults (PageSize, CurrentPage, time ranges), use the defaults without asking unless the user indicates otherwise.
> - Do NOT re-ask for parameters that the user has clearly stated.

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| RegionId | Required | Alibaba Cloud region for Cloud Firewall. Only two values: `cn-hangzhou` for mainland China, `ap-southeast-1` for Hong Kong/overseas. | `cn-hangzhou` (use directly without asking; only use `ap-southeast-1` if user explicitly mentions Hong Kong/overseas/international) |
| PageSize | Optional | Number of items per page for paginated APIs | 50 (use without asking) |
| CurrentPage | Optional | Page number for paginated APIs | 1 (use without asking) |
| StartTime | Optional | Start time for time-range queries (Unix timestamp in seconds) | 30 days ago for exposure queries, 7 days ago for attack/vuln queries (use without asking) |
| EndTime | Optional | End time for time-range queries (Unix timestamp in seconds) | Current time (use without asking) |

---

## Error Handling and Workflow Resilience

> **CRITICAL: Continue on failure.** If any individual API call fails, do NOT stop the entire workflow.
> Log the error for that step, then proceed to the next step. Present whatever data was successfully collected.

### Retry Logic

For each API call:
1. If the call fails with a **transient error** (network timeout, throttling `Throttling.User`, `ServiceUnavailable`, HTTP 500/502/503), retry up to **2 times** with a 3-second delay between retries.
2. If the call fails with a **permanent error** (e.g., `InvalidParameter`, `Forbidden`, `InvalidAccessKeyId`), do NOT retry. Record the error and move on.
3. After all retries are exhausted, record "[Step X] Failed: {error message}" and continue to the next step.

### Timeout Policy (MUST)

Before executing any API command, set explicit timeout values:

```bash
export ALIBABA_CLOUD_CONNECT_TIMEOUT=10
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

- `ALIBABA_CLOUD_CONNECT_TIMEOUT=10`: fail fast on network connect issues.
- `ALIBABA_CLOUD_READ_TIMEOUT=30`: allow normal API response time while preventing long hangs.
- If a timeout occurs, treat it as transient and apply the retry logic above.

### Service Not Activated

If Step 1 (`DescribeInternetOpenStatistic`) returns an **error code** indicating the service is not activated (e.g., `ErrorFirewallNotActivated` or similar "not purchased/activated" error messages):
1. Inform the user: "Cloud Firewall service is not activated. Please activate it at https://yundun.console.aliyun.com/?p=cfwnext"
2. Skip all subsequent steps since the service is not available.

> **CRITICAL: All-zeros response ≠ Service Not Activated.** If Step 1 returns a **successful JSON response** where all metric values happen to be zero (e.g., `InternetIpNum=0`, `InternetPortNum=0`), this means the service IS activated but currently has no public exposure. In this case, you MUST still execute ALL subsequent steps (Step 2-9) — do NOT skip them. Zero values are valid data, not an error condition. Other steps may still return non-zero results (e.g., assets exist but none are exposed, ACL rules exist, etc.).

### Step Independence

The workflow steps have these dependencies:
- **Step 1 (Overview)** should run first as it provides context for interpreting subsequent data.
- **Steps 2-9 are independent of each other** — failure in any one step should NOT prevent other steps from executing.
- Step 6 depends on Step 2's output (IP list), but can be skipped if Step 2 fails.

### Partial Results

When presenting the final summary report:
- For steps that succeeded, show the collected data normally.
- For steps that failed, show "N/A (error: {brief error})" in the corresponding section.
- Always present the summary report even if some steps failed — partial data is better than no data.

---

## Core Workflow

All API calls use the Aliyun CLI `cloudfw` plugin.

**Region**: Specified via `--region {RegionId}` global flag

> **CRITICAL: Execute immediately without asking.** When this skill is triggered, start executing from Step 1 right away.
> Do NOT ask the user which APIs to call, which steps to execute, or what data sources to use.
> All data comes from the Aliyun CLI commands defined below — just run them.
> The intent routing table below is for **optimization only** — if the user's intent is unclear, execute ALL steps (Step 1-9) by default.

> **MANDATORY: Execute ALL steps.** You MUST attempt to execute **every step** from Step 1 through Step 9. Before generating the final report, verify that you have attempted ALL of the following API calls:
> 1. `DescribeInternetOpenStatistic` (Step 1)
> 2. `DescribeInternetOpenIp` (Step 2)
> 3. `DescribeInternetOpenPort` (Step 3)
> 4. `DescribeAssetList` (Step 4)
> 5. `DescribeAssetList` with NewResourceTag (Step 5)
> 6. `DescribeAssetRiskList` (Step 6 — skip only if Step 2 returned no IPs)
> 7. `DescribeVulnerabilityProtectedList` (Step 7)
> 8. `DescribeRiskEventGroup` (Step 8)
> 9. `DescribeControlPolicy` (Step 9)
>
> If any of these were not attempted, execute them now before producing the report. Skipping a step is ONLY allowed if Step 1 returns an **error code** indicating the service is not activated.

> **MANDATORY: Report-Execution Consistency.** The final report MUST accurately reflect actual execution:
> - The report must list every API that was actually called and its result status (success/fail).
> - Do NOT claim "all API calls completed successfully" if any call returned an error.
> - For steps not executed, explain WHY they were skipped (e.g., "Step 6 skipped: Step 2 returned 0 IPs").
> - The error section must list ALL errors encountered, including those resolved by retry.

### Intent Routing (Auto-determined, No Confirmation Needed)

Automatically determine execution scope based on user wording. **Do NOT ask the user to confirm**:

| User Intent | Execution Steps |
|-------------|----------------|
| Full audit ("help me audit exposure", "full scan") | Execute all Steps 1-9 |
| High-risk port check ("are there any high-risk ports exposed") | Execute Step 1 + Step 3, focus on high-risk ports |
| New exposures ("what new exposures appeared recently") | Execute Step 1 + Step 5 |
| Specific IP exposure details ("check the exposure of x.x.x.x") | Execute Step 2 (with SearchItem filter) + Step 6 |

**Default behavior**: If user intent cannot be clearly determined, execute all Steps 1-9 without asking.

### Time Parameters

Some APIs require `StartTime` and `EndTime` parameters (Unix timestamp in seconds).

**How to get timestamps**: Run `date +%s` to get the current timestamp, `date -d '30 days ago' +%s` for 30 days ago, `date -d '7 days ago' +%s` for 7 days ago. Then use the returned numeric values directly in CLI commands.

> **IMPORTANT**: Do NOT use bash variable substitution like `$(date +%s)` inside CLI commands — some execution environments block `$(...)`. Instead, run `date` commands separately first, note the returned values, then use them as literal numbers in the `--StartTime` and `--EndTime` parameters.

Default time ranges:
- **Exposure queries** (Step 2, 3): last 30 days → `StartTime` = 30 days ago
- **Vulnerability/attack queries** (Step 7, 8): last 7 days → `StartTime` = 7 days ago
- **EndTime**: always current timestamp

### Step 1: Exposure Statistics Overview

Retrieve overall public network exposure data. This is the starting point for subsequent analysis.

```bash
aliyun cloudfw describe-internet-open-statistic \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeInternetOpenStatistic` in [references/api-analysis.md](references/api-analysis.md) for response field details.

### Step 2: Exposed IP Details

List all IP addresses exposed to the public network and their risk information.

```bash
aliyun cloudfw describe-internet-open-ip \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeInternetOpenIp` in [references/api-analysis.md](references/api-analysis.md) for response field details.
Pagination: Check `PageInfo.TotalCount`. If it exceeds `PageSize`, increment `CurrentPage` to fetch more.

### Step 3: Exposed Port Details

List all exposed ports and their details. This is a key step for identifying high-risk exposures.

```bash
aliyun cloudfw describe-internet-open-port \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeInternetOpenPort` in [references/api-analysis.md](references/api-analysis.md) for response field details.
Pagination: Check `PageInfo.TotalCount`.

### Step 4: Asset Protection Status

Retrieve the list of all assets protected by the firewall.

```bash
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeAssetList` in [references/api-analysis.md](references/api-analysis.md) for response field details.
Pagination: Check `TotalCount`.

### Step 5: New Exposures (Last 7 Days)

Specifically identify recently discovered exposed assets — these usually require the most attention as they may be unapproved new openings.

```bash
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --NewResourceTag "discovered in 7 days" \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

### Step 6: Asset Risk Details

Take the IPs collected from Step 2 (max 20 per call) and retrieve detailed risk reasons. If there are more than 20 IPs, make multiple batched calls.

```bash
aliyun cloudfw describe-asset-risk-list \
  --IpVersion 4 \
  --IpAddrList '["1.2.3.4","5.6.7.8"]' \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeAssetRiskList` in [references/api-analysis.md](references/api-analysis.md) for response field details.

### Step 7: Vulnerability Protection Status

Check current vulnerability protection coverage and identify which high-risk vulnerabilities are not yet protected.

```bash
aliyun cloudfw describe-vulnerability-protected-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeVulnerabilityProtectedList` in [references/api-analysis.md](references/api-analysis.md) for response field details.

### Step 8: Recent Attack Events

Review intrusion attack events from the last 7 days and cross-reference attack targets with exposure data.

```bash
aliyun cloudfw describe-risk-event-group \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --DataType 1 \
  --Direction in \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeRiskEventGroup` in [references/api-analysis.md](references/api-analysis.md) for response field details.

### Step 9: Internet Border ACL Policy

Review current inbound ACL rules and assess protection coverage.

```bash
aliyun cloudfw describe-control-policy \
  --Direction in \
  --CurrentPage 1 \
  --PageSize 50 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```

Refer to `DescribeControlPolicy` in [references/api-analysis.md](references/api-analysis.md) for response field details.

---

## Analysis & Report

After collecting data, generate a report in the following structure. Only show sections with actual data; if an API call failed, note "Data retrieval failed for this section" and continue with other analysis.

### 1. Public Network Exposure Overview

Display Step 1 statistics in a table:

| Metric | Value | Risk Assessment |
|--------|-------|-----------------|
| Total Exposed Public IPs | x | — |
| High-Risk IP Count | x | Flag if > 0 |
| Total Exposed Ports | x | — |
| High-Risk Port Count | x | Flag if > 0 |
| Unprotected Port Count | x | Flag if > 0 |
| Total Exposed Services | x | — |
| High-Risk Service Count | x | Flag if > 0 |
| SLB Exposed IP Count | x | — |

### 2. High-Risk Exposure List

Combine data from Step 2 and Step 3, sorted by risk level (high → middle → low).

The following ports should be additionally flagged as high-risk when exposed to the public network, regardless of the API-returned risk level:
- **Management ports**: 22(SSH), 23(Telnet), 3389(RDP), 21(FTP)
- **Database ports**: 3306(MySQL), 1433(MSSQL), 5432(PostgreSQL)
- **Cache/NoSQL**: 6379(Redis), 27017(MongoDB), 9200/9300(Elasticsearch), 11211(Memcached)
- **File sharing**: 445(SMB/CIFS), 139(NetBIOS)
- **Management interfaces**: 8080, 8443, 9090

Output format:

| IP Address | Port | Service | Risk Level | Risk Reason | ACL Status | Recommended Action |
|-----------|------|---------|------------|-------------|------------|-------------------|

### 3. New Exposure Discoveries (Last 7 Days)

Display assets discovered in Step 5:

| IP Address | Discovery Time | Resource Type | Instance Name | Protection Status | Risk Level |
|-----------|---------------|--------------|--------------|-------------------|------------|

If no new exposures were found, state "No new exposed assets discovered in the last 7 days".

### 4. Vulnerability Correlation Analysis

Combine Step 7 and Step 8:

1. **High-Risk Vulnerability List**: List vulnerabilities with VulnLevel=high, especially flagging those without protection enabled
2. **Attack Event Statistics**: Summarize attack events from the last 7 days by attack type, correlating with attacked exposed IPs
3. **Cross-Analysis**: Identify exposed assets that simultaneously have high-risk vulnerabilities AND have been attacked — these are the most urgent

### 5. Exposure Remediation Recommendations

Generate specific recommendations based on actual data, sorted by priority. Each recommendation includes: **Risk Description**, **Impact Scope**, **Recommended Action**.

#### P0 — Critical (Immediate Action)
- Database ports (3306/5432/6379/27017/1433/9200) exposed to public network → Close public access or strictly restrict source IPs via ACL
- Management ports (22/3389/23) without ACL protection → Add ACL restricting to bastion host/office network IPs
- Exposed assets with high-risk vulnerabilities that have been attacked → Immediately enable IPS protection and virtual patches

#### P1 — High (Within 24 Hours)
- Exposed services with known high-risk vulnerabilities but no virtual patches enabled → Enable virtual patches
- Unprotected ports with external traffic → Add ACL policies
- SMB(445)/NetBIOS(139) exposed → Close or restrict access

#### P2 — Medium (This Week)
- New exposed assets not yet approved → Confirm business necessity; close if unnecessary
- Medium-risk ports exposed → Evaluate business requirements, restrict access sources

#### P3 — Low (Periodic Review)
- Low-risk ports exposed → Include in periodic review
- ACL rules with zero hit rate → Evaluate whether they can be cleaned up

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

1. **Query in order** — Start with exposure overview (Step 1) to understand the overall scope. If Step 1 returns an **error code** (e.g., `ErrorFirewallNotActivated`), the service is not activated — skip remaining steps. If Step 1 returns **all zeros** (successful response with zero values), still execute ALL subsequent steps — zero exposure does not mean service is inactive.
2. **Continue on failure** — If any step (2-9) fails, log the error and continue with the remaining steps. Always produce a report with whatever data was collected.
3. **Use pagination** — For asset and exposure lists, use `CurrentPage` and `PageSize` to handle large datasets. Default to PageSize=50. If `TotalCount` exceeds `PageSize`, iterate through all pages.
4. **Time range selection** — For exposure queries, default to last 30 days. For attack/vulnerability queries, default to last 7 days. Use Unix timestamps in seconds. Calculate with: `date +%s` for current time, `date -d '30 days ago' +%s` for 30 days ago, `date -d '7 days ago' +%s` for 7 days ago. Run these commands separately, then use the returned values as literal numbers in `--StartTime` and `--EndTime`. Do NOT use `$(...)` substitution inside CLI commands.
5. **Region awareness** — Cloud Firewall only has two regions: `cn-hangzhou` (mainland China) and `ap-southeast-1` (Hong Kong/overseas). Default to `cn-hangzhou` unless user specifies otherwise.
6. **Batch IP lookups** — Step 6 (`DescribeAssetRiskList`) accepts max 20 IPs per call. If more IPs are collected from Step 2, batch them into groups of 20.
7. **Rate limiting** — Space API calls to avoid throttling. If you receive a `Throttling.User` error, wait 3 seconds and retry.
8. **Security** — NEVER expose, log, echo, or display AK/SK values.
9. **Retry on transient errors** — For network timeouts or 5xx errors, retry up to 2 times with a 3-second delay.
10. **Explicit timeout config** — Always set `ALIBABA_CLOUD_CONNECT_TIMEOUT=10` and `ALIBABA_CLOUD_READ_TIMEOUT=30` before running workflow commands.
11. **Least network access** — Only allow Aliyun CLI access to Cloud Firewall OpenAPI endpoints; do not access other external domains or VPC/internal resources.

## Output Desensitization

When printing analysis results, mask sensitive identifiers by default:
- IP addresses: keep first segments only (example: `203.0.x.x`, `10.23.x.x`).
- Instance IDs: keep prefix and last 4 chars only (example: `i-abc***9f2d`).
- Account identifiers / UID: keep last 4 digits only.
- Do not print raw tokens, credential material, local config file content, or full internal network topology.

If the user explicitly asks for full values, confirm necessity first and still avoid exposing secrets.

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete API table with parameters |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions and policy JSON |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect usage patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [references/api-analysis.md](references/api-analysis.md) | Detailed API parameter and response documentation |