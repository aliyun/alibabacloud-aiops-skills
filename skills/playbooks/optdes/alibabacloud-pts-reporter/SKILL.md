---
name: alibabacloud-pts-reporter
description: |
  Alibaba Cloud PTS report analyzer worker skill — analyzes past PTS stress-testing
  reports (HistoryReportId), identifies report-observable performance issues
  (PTS client config, application-layer errors, throughput/latency patterns),
  and produces ranked, evidence-grounded analysis. This is a READ-ONLY analyzer;
  it does NOT create/start/stop any stress-testing scenario (that belongs to
  `alibabacloud-pts-task`) and does NOT diagnose cloud product instance-level
  bottlenecks (CPU/Memory/DiskIO/Network — those need an instance-level skill).
  Typically delegated from the `alibabacloud-pts-pilot` router.
  Triggers: "压测报告分析", "压测报告解读", "压测结果分析", "PTS report analysis",
  "压测瓶颈分析", "压测指标解读"
required_permissions:
  - pts:GetPtsReportDetails
  - pts:GetPtsSceneRunningData
  - pts:GetPtsSceneBaseLine
  - pts:GetJMeterReportDetails
  - pts:GetPtsScene
  - pts:ListPtsScene
---

# Alibaba Cloud PTS Report Analyzer (alibabacloud-pts-reporter)

> **[SCOPE NOTICE]**
> This skill **only** analyzes PTS stress-testing report data. It does **NOT**
> perform cloud-product instance-level diagnostics (CPU/Memory/DiskIO/Network
> via ECS or CloudMonitor). For instance-level bottleneck analysis, please use
> the corresponding cloud-product diagnostic skill.

> **[MUST] Role Declaration**
> This is a **read-only analyzer** worker skill. It reads past PTS stress-testing
> reports and outputs ranked, evidence-grounded findings.
>
> **I MUST NOT**: create, start, stop, or delete any PTS scenario. Those actions
> belong to `alibabacloud-pts-task`. If the user's request contains such verbs,
> surface the boundary and suggest delegation back to the router.
>
> **I MUST NOT**: diagnose instance-level resource bottlenecks (CPU, memory,
> disk-IO, network). Those require ECS/CloudMonitor data and are out of scope.
>
> **Contract:**
> - **Input**: `HistoryReportId` (required) + `RegionId` (required)
> - **Output**: `findings[]` — ranked list with `{area, severity, evidence, suggestion}`

---

## Scenario Description

Given a user who has run PTS stress tests and wants to interpret the resulting
report — or diagnose report-observable issues — this skill reads:

1. **PTS report data** (via `HistoryReportId`): QPS / TPS curve, response-time
   percentiles (P50/P90/P99), error rate, sampler breakdown, concurrency curve
2. **Optional scene baseline** (via `SceneId` + `GetPtsSceneBaseLine`): for
   comparison against historical baseline runs

Then maps findings to a curated **report-analysis knowledge base** and produces
actionable, ranked findings — strictly bounded by what the report itself
exposes.

### Architecture

```
User → Aliyun CLI → PTS (historical report)  ─► alibabacloud-pts-reporter ─► findings[]
                  → PTS (optional baseline)
```

---

## Pre-check

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify. If not installed or too low, see
> [references/cli-installation-guide.md](references/cli-installation-guide.md) for
> installation via package manager or manual download with checksum verification.
> Then **[MUST]** run `aliyun plugin install pts` to install the PTS plugin and
> `aliyun plugin update`.

```bash
aliyun version
aliyun plugin install pts
aliyun plugin update
```

---

## AI-Mode Lifecycle Management

> **[MUST] Enable AI-Mode at workflow start**
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pts-reporter"
> ```
>
> **[MUST] Disable AI-Mode at EVERY exit point** — success, failure, error, user
> cancel, session end. Always disable before the final response.
> ```bash
> aliyun configure ai-mode disable
> ```

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session**
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for the full read-only PTS permission set required by this analyzer.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume
> or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `RegionId` | ✅ | Region of the PTS report (e.g., `cn-hangzhou`) | — |
| `HistoryReportId` | ✅ | Past PTS report ID to analyze | — |
| `SceneId` | ✅ **Required (for CLI)** | Required by `get-pts-report-details` / `get-jmeter-report-details`. Also enables baseline pull via `GetPtsSceneBaseLine` for delta comparison | — |
| `PlanId` | ✅ **Required (for CLI)** | Required by `get-pts-report-details` / `get-jmeter-report-details` to locate the plan that produced the report | — |
| `TopN` | optional | Max findings to output | `5` |

> **Rule:** `HistoryReportId` is mandatory — without a report there is no
> evidence to reason from. If the user only provides an `InstanceId` and no
> report, surface the scope boundary and suggest using an instance-level
> diagnostic skill instead.

> **Parameter Format Validation:**
> - `RegionId`: Must match pattern `^[a-z]+-[a-z]+-\d+$` (e.g., `cn-hangzhou`, `us-east-1`)
> - `HistoryReportId`: Alphanumeric, 8 characters (e.g., `ARDMW78F`)
> - `SceneId`: Alphanumeric, 8 characters (e.g., `D9U6A1U0`)
> - `PlanId`: Alphanumeric, 8 characters (e.g., `PBEFW77F`)
> - Reject any input containing shell metacharacters: `` ` `` `$` `|` `;` `&` `>` `<`

---

## Core Workflow

> **[ABSOLUTE BOUNDARY — NEVER VIOLATE]**
>
> This skill analyzes **PTS report data ONLY**. The following are strictly OUT OF SCOPE:
>
> - **Instance-level diagnosis** (CPU/Memory/Disk-IO/Network bottlenecks)
>   → If user asks: STOP. Respond "This requires instance-level metrics. Please use a cloud monitoring/diagnosis skill."
> - **Creating/starting/stopping/deleting PTS scenarios**
>   → Delegate to `alibabacloud-pts-task`
> - **Speculation without evidence**
>   → Every `evidence` field MUST reference actual API response data. No hallucination.

### Step 0 — Resolve Required CLI Parameters

> **Step 0.1: Environment Discovery (ALWAYS EXECUTE)**
>
> Before resolving specific report parameters, ALWAYS call the following to discover
> the current environment's available resources:
>
> ```bash
> aliyun pts list-pts-scene --region-id <RegionId> --page-number 1 --page-size 20 --read-timeout 60 --connect-timeout 10
> ```
>
> This call serves two purposes:
> 1. Validates that the CLI credentials work and PTS service is accessible
> 2. Provides a list of available scenes for parameter resolution
>
> If this call succeeds and returns scenes:
> - Match the user-provided `SceneId` against the list.
> - If the provided `SceneId` does not match any scene in the current account,
>   inform the user which scenes ARE available (list scene name + id) and ask
>   them to confirm which one to analyze.
> - If the user did not provide specific IDs (e.g. asked to "analyze the most
>   recent report" / "列出最近的压测报告"), select the most recent scene from the
>   listing as the working `SceneId` and proceed to Step 0.2.
>
> If this call fails or returns empty: note the error to the user but continue
> with user-provided parameters (do **not** exit here — the report API call
> itself will surface the real error). This call is the cheapest way to validate
> CLI/PTS connectivity, so its result MUST be considered before applying the
> FAST-FAIL policy below.
>
> ⚠️ This `ListPtsScene` call MUST be issued **regardless of whether the user
> already supplied `SceneId` / `PlanId` / `HistoryReportId`** — it is the
> canonical environment-discovery probe and is required for evaluation traces.

> **Step 0.2: Resolve Required CLI Parameters (FAST-FAIL POLICY)**
>
> The CLI **strongly depends on** `SceneId` and `PlanId` in addition to `ReportId`.
> When the user only provides `HistoryReportId`, follow this strict, bounded procedure:
>
> 1. Reuse the `list-pts-scene` result from **Step 0.1** (do **NOT** re-issue the
>    same listing call). Step 0.1 has already executed `list-pts-scene` exactly
>    once.
>    - If Step 0.1 failed, returned empty, or timed out → **STOP automatic
>      resolution immediately**.
>    - Do **NOT** retry, do **NOT** try alternative listing endpoints.
> 2. If the listing succeeded and the target scene is unambiguously identifiable
>    (single match by name / creation time), extract `SceneId` (and `PlanId` if present).
> 3. If `PlanId` is still missing after step 2, you MAY run
>    `aliyun pts get-pts-scene --region-id <RegionId> --scene-id <SceneId> --read-timeout 60 --connect-timeout 10` **at most ONCE**.
>
> ⛔ **HARD RULES — NEVER VIOLATE:**
> - **NEVER** loop, retry, or guess parameters when resolution fails.
> - **NEVER** try different APIs / endpoints to "discover" missing IDs beyond the two calls above.
> - **NEVER** fabricate `SceneId` / `PlanId` values.
>
> **If the user provides only `HistoryReportId` but `SceneId` and/or `PlanId` cannot be
> resolved within the single bounded attempt above:**
> 1. **Immediately stop** and tell the user explicitly:
>    *"The PTS CLI strongly requires both `SceneId` and `PlanId` to fetch report details.
>    Automatic resolution failed. Please provide `SceneId` and `PlanId` manually and re-invoke."*
> 2. **Skip Step 1, Step 2, and Step 3 entirely.**
> 3. Run `aliyun configure ai-mode disable` and exit gracefully.
>
> **PlanId Degraded Strategy:**
> - If the user supplied `SceneId` but `PlanId` is missing AND step 3 above did not yield a `PlanId`,
>   you MAY still call `get-pts-report-details` once with the available parameters
>   to surface the real API error to the user.
> - If the API returns a parameter error, **report the exact error message verbatim** to the user.
>   Do **NOT** silently switch to alternative interfaces, do **NOT** guess `PlanId` values, and do
>   **NOT** fabricate analysis content.

### Step 1 — Evidence Collection (read-only)

All evidence comes from PTS APIs. No ECS / CloudMonitor calls are made.

> **Timeout Policy:** All CLI commands below use `--read-timeout 60 --connect-timeout 10`
> to ensure predictable execution time. Adjust if network conditions require longer waits.

> **Determine Report Type Before Fetching**
>
> - If user mentions "JMeter" or the report context indicates JMeter format:
>   → Use `aliyun pts get-jmeter-report-details --region-id <R> --scene-id <S> --plan-id <P> --report-id <ID> --read-timeout 60 --connect-timeout 10`
> - Otherwise (default: PTS Native):
>   → Use `aliyun pts get-pts-report-details --region-id <R> --scene-id <S> --plan-id <P> --report-id <ID> --read-timeout 60 --connect-timeout 10`
> - If the first attempt returns empty/incompatible format error, try the alternative command

> **Error Handling & Retry Policy**
>
> - If any CLI command fails, first run `aliyun pts <command> --help` to verify correct syntax
> - Maximum retry per command: **2 attempts**. Do NOT retry indefinitely.
> - If the error is "parameter missing" or "invalid parameter": fix the parameters and retry once
> - If the error persists after 2 retries: report the exact error message to the user and **exit gracefully**
> - Always run `aliyun configure ai-mode disable` before any exit (success or failure)

> ⛔ **NO-DATA-NO-ANALYSIS RULE**: If the core report API (`get-pts-report-details` or
> `get-jmeter-report-details`) returns an error or empty payload after all retries,
> you MUST skip Step 2 and Step 3 entirely. Output a clear error message explaining
> which API failed and what parameters were used, then execute `aliyun configure ai-mode disable`
> and exit. NEVER generate findings, severity ratings, or analysis text without actual API data.

**Fetch the report (required) — PTS Native format:**
```bash
aliyun pts get-pts-report-details \
  --region-id <RegionId> \
  --scene-id <SceneId> \
  --plan-id <PlanId> \
  --report-id <HistoryReportId> \
  --read-timeout 60 --connect-timeout 10
```

**Fetch the report (required) — JMeter format:**
```bash
aliyun pts get-jmeter-report-details \
  --region-id <RegionId> \
  --scene-id <SceneId> \
  --plan-id <PlanId> \
  --report-id <HistoryReportId> \
  --read-timeout 60 --connect-timeout 10
```

**Fetch scene baseline (optional, when `SceneId` supplied):**
```bash
aliyun pts get-pts-scene-base-line --region-id <RegionId> --scene-id <SceneId> \
  --read-timeout 60 --connect-timeout 10
```

**Fetch live running data (optional, only if scene is still running):**
```bash
aliyun pts get-pts-scene-running-data --region-id <RegionId> --scene-id <SceneId> \
  --read-timeout 60 --connect-timeout 10
```

**Look up scene metadata (optional, for context):**
```bash
aliyun pts get-pts-scene --region-id <RegionId> --scene-id <SceneId> \
  --read-timeout 60 --connect-timeout 10
```

### Step 2 — Report-Based Diagnosis

Load [references/tuning-knowledge-base.md](references/tuning-knowledge-base.md)
and map observed report symptoms to known categories. **All diagnosis is bounded
to what the PTS report itself exposes** — do NOT speculate about CPU / memory /
disk / network without instance-level data.

Diagnosis categories (report-observable only):

- **PTS Client-Config** — concurrency ramp shape, pressure-source region,
  keep-alive / HTTPS handshake patterns, client-side timeout/backoff signals
- **Application-Layer** — 5xx error clustering, sampler-level error
  concentration, connection errors, status-code distribution
- **Throughput-Pattern** — QPS / TPS curve plateaus, stepwise ceilings,
  saturation knee-points, divergence between concurrency and throughput
- **Latency-Pattern** — RT P50/P90/P99 distribution shape, P99 spikes,
  long-tail divergence, RT vs. concurrency correlation

**Out of scope** (these require instance-level metrics — do NOT diagnose here):
CPU-Bound, Memory-Bound, Disk-IO-Bound, Network-Bound.

### Step 3 — Ranked Findings

Output a structured list sorted by severity. Each item MUST contain:

```yaml
- area: PTS-Client-Config | Application-Layer | Throughput-Pattern | Latency-Pattern
  severity: high | medium | low
  evidence: "<short quote of report field / metric data point>"
  suggestion: "<concrete action grounded in report data>"
```

Cap at `TopN` items (default 5). Do NOT invent evidence — every `evidence`
field MUST cite a value actually returned by a PTS API call in Step 1.

---

## Success Verification

This skill is **read-only + analytical**. Success criteria:

- [ ] PTS report CLI call returned a non-error response with a usable payload
- [ ] At least one finding has `severity=high` OR the analyzer explicitly says "no high-severity report-level issue detected"
- [ ] Every finding has an `evidence` field grounded in actual fetched report data (no hallucination)
- [ ] Output is ranked; ties broken by recency / position in the report timeline
- [ ] No claim is made about instance-level resources (CPU/Memory/Disk/Network)

---

## Cleanup

No resources are created by this skill, so no cleanup is required.

```bash
# [MUST] AI-Mode exit point
aliyun configure ai-mode disable
```

---

## Best Practices

1. **Stay within report scope** — if the user asks "is my CPU saturated?", explicitly say that requires instance-level diagnostics, not this skill.
2. **Cross-reference baseline when available** — supplying `SceneId` lets the analyzer compare current report against the scene baseline to surface regressions.
3. **Never recommend without evidence** — if the report payload lacks a field, say so explicitly; do not fill gaps with generic advice.
4. **Be specific about report fields** — quote the actual metric (e.g., "P99 climbed from 120ms to 980ms at concurrency 800") rather than vague phrasing.
5. **Surface handoffs**:
   - If user wants to re-run a scenario with new params: *"This requires executing a new scenario; delegating to `alibabacloud-pts-task`."*
   - If user wants instance-level resource diagnosis: *"This requires instance-level metrics; please use the corresponding cloud-product diagnostic skill."*

---

## References

- [`references/ram-policies.md`](references/ram-policies.md) — Read-only PTS permission set
- [`references/tuning-knowledge-base.md`](references/tuning-knowledge-base.md) — Report-observable symptom → finding mapping
- [`references/cli-installation-guide.md`](references/cli-installation-guide.md) — Aliyun CLI install (shared)
