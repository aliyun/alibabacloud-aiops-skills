---
name: alibabacloud-cfw-ips-event
description: Query and analyze security events and alerts detected by Alibaba Cloud Firewall IPS (Intrusion Prevention System), helping quickly locate threats and provide remediation recommendations. Triggers when user mentions IPS alerts, intrusion detection, intrusion prevention, attack events, security alerts, threat detection, attack analysis, IDS/IPS, being attacked, any attacks, security incidents, security warnings, server under attack, machine alarms. Also triggers when user asks about "any recent attacks", "which assets were attacked", "does this IP have attack behavior", "security alerts for a specific server/machine", "which IPs attacked a specific IP", even without explicitly saying "IPS".
---

# IPS Alert Event Analysis

> **Skill Scope Notes:**
> - This skill is designed to use Aliyun CLI `cloudfw` commands as its primary data source.
> - It does not depend on local log files, SIEM exports, or direct host access.
> - It does not require SSH or direct connections to server IPs.
> - For IP-focused investigations, prefer `DescribeRiskEventGroup` with `--SrcIP` or `--DstIP`.

## Scenario Description

Query and analyze IPS (Intrusion Prevention System) security events and alerts detected by Alibaba Cloud Firewall, helping quickly locate threats and provide remediation recommendations.

**Architecture**: `Cloud Firewall Service → IPS Engine → Event Detection + Attack Analysis + Protection Configuration`

**Capability Level**: Query (read-only)

**Data Source**: All data is obtained **exclusively** through Aliyun CLI commands (`aliyun cloudfw ...`). No log files, no databases, no server access, no SIEM — just CLI commands. **Do NOT search the workspace for files. Do NOT ask the user for anything. Just run the commands.**

**Core Capabilities**:
1. **Alert Overview** — IPS alert statistics including attack counts, block counts, and severity distribution
2. **Alert Event Details** — Detailed list of IPS alert events with source/destination, attack type, and handling status
3. **Top Attacked Assets** — Ranking of most attacked assets
4. **Attack Type Analysis** — Distribution of attack types and applications
5. **IPS Configuration Status** — Current IPS run mode, rule switches, and rule library version
6. **Remediation Recommendations** — Prioritized security recommendations based on alert data

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
> - If the user's request **explicitly mentions** a parameter value (e.g., "check IPS alerts for the last 7 days" means use 7-day time range), use that value directly **without asking for confirmation**.
> - For optional parameters with sensible defaults (PageSize, CurrentPage, time ranges), use the defaults without asking unless the user indicates otherwise.
> - Do NOT re-ask for parameters that the user has clearly stated.

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| RegionId | Required | Alibaba Cloud region for Cloud Firewall. Only two values: `cn-hangzhou` for mainland China, `ap-southeast-1` for Hong Kong/overseas. | `cn-hangzhou` (use directly without asking; only use `ap-southeast-1` if user explicitly mentions Hong Kong/overseas/international) |
| StartTime | Required for most APIs | Start time for alert queries (Unix timestamp in seconds) | 24 hours ago for "today", 7 days ago for "recently"/"this week" (use without asking) |
| EndTime | Required for most APIs | End time for alert queries (Unix timestamp in seconds) | Current time (use without asking) |
| PageSize | Optional | Number of items per page for paginated APIs | 50 (use without asking) |
| CurrentPage | Optional | Page number for paginated APIs | 1 (use without asking) |

## Input Validation (MUST)

Treat all Agent-provided inputs as untrusted. Validate before building CLI commands.

Validation rules:
- `RegionId`: must be exactly one of `cn-hangzhou` or `ap-southeast-1`.
- `StartTime` / `EndTime`: must be 10-digit Unix seconds (`^[0-9]{10}$`), and `StartTime < EndTime`.
- `CurrentPage`: positive integer (`>=1`).
- `PageSize`: integer in range `1-100`.
- `SrcIP` / `DstIP`: must be valid IPv4 format only (`a.b.c.d`, each octet `0-255`).

Safe command construction rules:
- Never concatenate raw user text into shell commands.
- Only pass validated values into fixed CLI flag templates.
- If any validation fails, stop execution and return a clear validation error.

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

Before any API call, explicitly set CLI timeouts:

```bash
export ALIBABA_CLOUD_CONNECT_TIMEOUT=10
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

- `ALIBABA_CLOUD_CONNECT_TIMEOUT=10`: fast fail for connect timeout.
- `ALIBABA_CLOUD_READ_TIMEOUT=30`: prevent long-running hangs per request.
- Timeout errors are treated as transient errors and follow retry logic.

### No Alert Events

If Step 1 (`DescribeRiskEventStatistic`) returns all zeros:
1. Inform the user: "No IPS alert events detected in the specified time range."
2. Still proceed with Step 6 and Step 7 to report IPS configuration status.

### Step Independence

The workflow steps have these dependencies:
- **Step 1 (Statistics)** should run first to provide context.
- **Steps 2-7 are independent of each other** — failure in any one step should NOT prevent other steps from executing.

### Partial Results

When presenting the final summary report:
- For steps that succeeded, show the collected data normally.
- For steps that failed, show "N/A (error: {brief error})" in the corresponding section.
- Always present the summary report even if some steps failed — partial data is better than no data.

---

## Core Workflow

All API calls use the Aliyun CLI `cloudfw` plugin.
Request/response schemas are maintained only in [references/api-analysis.md](references/api-analysis.md). Do not duplicate field-by-field descriptions in this file.

**User-Agent**: All commands must include `--user-agent AlibabaCloud-Agent-Skills`
**Region**: Specified via `--region {RegionId}` global flag

> **CRITICAL: Execute immediately without asking.** When this skill is triggered, start executing from Step 1 right away.
> Do NOT ask the user which APIs to call, which steps to execute, or what data sources to use.
> All data comes from the Aliyun CLI commands defined below — just run them.
> The intent routing table below is for **optimization only** — if the user's intent is unclear, execute ALL steps (Step 1-7) by default.

### Intent Routing (Auto-determined, No Confirmation Needed)

Automatically determine execution scope based on user wording. **Do NOT ask the user to confirm**:

| User Intent | Execution Steps |
|-------------|----------------|
| Full alert analysis ("what IPS alerts today", "recent security events") | Execute all Steps 1-7 |
| Attacked asset investigation ("which assets were attacked most") | Execute Step 1 + Step 3 |
| Specific source IP alerts ("what alerts did this IP trigger") | Execute Step 2 (with `--SrcIP` filter) |
| Specific target asset/server alerts ("check attacks on x.x.x.x", "server 10.0.1.88 security alerts") | Execute Step 1 + Step 2 (with `--DstIP` filter) + Step 6 + Step 7 |
| Attack trend/types ("are attacks increasing recently") | Execute Step 1 + Step 4 + Step 5 |
| IPS configuration check ("what mode is IPS in", "rule library version") | Execute Step 6 + Step 7 |

**Default behavior**: If user intent cannot be clearly determined, execute all Steps 1-7 without asking.

### Time Parameters

Some APIs require `StartTime` and `EndTime` parameters (Unix timestamp in seconds).

**How to get timestamps**: Run `date +%s` to get the current timestamp, `date -d '1 day ago' +%s` for 24 hours ago, `date -d '7 days ago' +%s` for 7 days ago. Then use the returned numeric values directly in CLI commands.

> **IMPORTANT**: Do NOT use bash variable substitution like `$(date +%s)` inside CLI commands — some execution environments block `$(...)`. Instead, run `date` commands separately first, note the returned values, then use them as literal numbers in the `--StartTime` and `--EndTime` parameters.

Default time ranges:
- User says "today" → `StartTime` = 24 hours ago
- User says "recently"/"this week" → `StartTime` = 7 days ago
- No time range specified → default to 7 days ago
- `EndTime` → always current timestamp

### Step 1: IPS Alert Statistics Overview

Retrieve overall alert statistics to understand the current security posture.

```bash
aliyun cloudfw DescribeRiskEventStatistic \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: IPS Alert Event Details

Retrieve grouped alert event list. This is the core data for analysis.

```bash
aliyun cloudfw DescribeRiskEventGroup \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --DataType 1 \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

Optional filter parameters (auto-added based on user intent, no confirmation needed):
- By direction: `--Direction in` or `--Direction out`
- By source IP: `--SrcIP x.x.x.x` (query "attacks initiated by a specific IP")
- By target IP: `--DstIP x.x.x.x` (query "attacks on a specific server/IP", **supports private IPs like 10.x.x.x**)
- By vulnerability level: `--VulLevel 3` (1=low, 2=medium, 3=high)

> **Key**: When a user mentions a specific server or IP being attacked, use the `--DstIP` filter to query all attack records for that IP — no need to access the server itself.

Pagination: Check `TotalCount`. If it exceeds 50, increment `CurrentPage`.

### Step 3: Top Attacked Assets Ranking

Identify which assets are attack hotspots.

```bash
aliyun cloudfw DescribeRiskEventTopAttackAsset \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 4: Top Attack Types Ranking

Understand the main threat types being faced.

```bash
aliyun cloudfw DescribeRiskEventTopAttackType \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --Direction in \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

If outbound attack types are also needed, make another call with `--Direction out`.

Note: This API requires the `Direction` parameter, otherwise it will return an error.

### Step 5: Top Attacked Applications Ranking

Understand which application-layer targets are being attacked.

```bash
aliyun cloudfw DescribeRiskEventTopAttackApp \
  --StartTime {StartTime} \
  --EndTime {EndTime} \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 6: IPS Protection Configuration Status

Check the current IPS run mode and protection capabilities.

```bash
aliyun cloudfw DescribeDefaultIPSConfig \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 7: IPS Rule Library Version

```bash
aliyun cloudfw DescribeSignatureLibVersion \
  --region {RegionId} \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Analysis & Report

After collecting data, generate a report in the following structure. Center the analysis around alert events, covering three dimensions: "who is attacking", "what is being attacked", and "how effective is the response". Only show sections with actual data; if an API call failed, note it and continue.

### 1. IPS Alert Posture Overview

Combine Step 1 statistics and Step 6 IPS configuration to display the current security posture:

**Alert Statistics (Time Range: x):**

| Metric | Value |
|--------|-------|
| Total Attack Events | x |
| Blocked | x |
| Observed/Alerted | x |
| Untreated | x |
| High / Medium / Low Severity | x / x / x |

**IPS Configuration Status:**

| Configuration Item | Status |
|-------------------|--------|
| Run Mode | Observe/Block |
| Basic Protection | Enabled/Disabled |
| Virtual Patches | Enabled/Disabled |
| Threat Intelligence | Enabled/Disabled |
| AI Engine | Enabled/Disabled |
| Rule Library Version | x (update time) |

If IPS is in observe mode and there are high-severity events, prominently flag: "IPS is currently in observe mode — high-severity attacks are NOT being blocked".

### 2. High-Severity Alert Events (Immediate Action Required)

From Step 2, filter events with VulLevel=3 (high) or VulLevel=2 (medium with high event count), sorted by event count in descending order:

| Event Name | Attack Type | Source IP | Source Location | Target IP | Target Asset | Event Count | Handling Status | First Seen | Last Seen |
|-----------|------------|----------|----------------|----------|-------------|------------|----------------|-----------|----------|

Handling status explanation:
- **Observed** (RuleResult=1): IPS detected but did not block — requires manual confirmation on whether blocking is needed
- **Blocked** (RuleResult=2): Automatically blocked by IPS

### 3. Attack Hotspot Analysis

#### Top Attacked Assets

Combine Step 3 data to display attack status by asset:

| Rank | Target IP | Resource Name | Resource Type | Region | Attack Count | Blocked | Block Rate |
|------|----------|--------------|--------------|--------|-------------|---------|------------|

Focus on assets with low block rates — this means many attacks are only being observed, not blocked.

#### Attack Type Distribution

Combine Step 4 data:

| Attack Type | Attack Count | Blocked | Block Rate |
|------------|-------------|---------|------------|

#### Attack Application Distribution

Combine Step 5 data:

| Application | Attack Count | Blocked | Block Rate |
|------------|-------------|---------|------------|

### 4. Attack Source Analysis

Summarize source IP dimensions from Step 2 event data:

| Source IP | Source Country/City | Attack Count | Primary Attack Type | Target Asset Count | Handling Status |
|----------|-------------------|-------------|-------------------|-------------------|----------------|

Flag cases where the same source IP attacks multiple assets — this typically indicates organized scanning or attacks.

### 5. Remediation Recommendations

Generate specific recommendations based on actual data, sorted by priority. Each recommendation includes: **Risk Description**, **Impact Scope**, **Recommended Action**.

#### P0 — Critical (Immediate Action)
- High-severity events in "observe" mode, not blocked → Switch IPS to block mode, or manually block the attacking source IP
- Same source IP attacking multiple assets in volume → Add that IP to Cloud Firewall ACL blacklist
- IPS in observe mode with active high-severity attacks → Switch to block mode

#### P1 — High (Within 24 Hours)
- Medium-severity events recurring and not blocked → Check target asset vulnerabilities and remediate
- Basic protection/virtual patches not enabled → Recommend enabling to enhance protection
- Attacked assets with low block rate → Check IPS rule coverage

#### P2 — Medium (This Week)
- Multiple attack types targeting the same asset → Conduct security hardening review for that asset
- Threat intelligence/AI engine rules not enabled → Recommend enabling
- Rule library version outdated → Update to the latest version

#### P3 — Low (Periodic Review)
- Low-severity events persisting → Include in periodic review, assess whether they are false positives
- Optimize IPS whitelist to reduce business false positives

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

1. **Query in order** — Start with alert statistics (Step 1) to understand the overall security posture. If all values are zero, report that no alerts were detected in the time range.
2. **Continue on failure** — If any step (2-7) fails, log the error and continue with the remaining steps. Always produce a report with whatever data was collected.
3. **Use pagination** — For alert event lists (Step 2), use `CurrentPage` and `PageSize`. Default to PageSize=50. If `TotalCount` exceeds `PageSize`, iterate through all pages.
4. **Time range selection** — Default to last 24 hours for "today", last 7 days for "recently"/"this week". Use Unix timestamps in seconds. Calculate with: `date +%s` for current time, `date -d '1 day ago' +%s` for 24 hours ago, `date -d '7 days ago' +%s` for 7 days ago. Run these commands separately, then use the returned values as literal numbers in `--StartTime` and `--EndTime`. Do NOT use `$(...)` substitution inside CLI commands.
5. **Region awareness** — Cloud Firewall only has two regions: `cn-hangzhou` (mainland China) and `ap-southeast-1` (Hong Kong/overseas). Default to `cn-hangzhou` unless user specifies otherwise.
6. **Direction parameter** — Step 4 (`DescribeRiskEventTopAttackType`) requires the `Direction` parameter. Default to `in` (inbound). Query `out` separately if needed.
7. **Rate limiting** — Space API calls to avoid throttling. If you receive a `Throttling.User` error, wait 3 seconds and retry.
8. **Security** — NEVER expose, log, echo, or display AK/SK values.
9. **Retry on transient errors** — For network timeouts or 5xx errors, retry up to 2 times with a 3-second delay.
10. **Validate all inputs first** — Reject invalid `RegionId`, timestamp, pagination, and IP values before command execution.
11. **Set explicit timeout env vars** — Always set `ALIBABA_CLOUD_CONNECT_TIMEOUT=10` and `ALIBABA_CLOUD_READ_TIMEOUT=30` before workflow commands.

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
