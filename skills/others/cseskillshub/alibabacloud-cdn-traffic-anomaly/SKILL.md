---
name: alibabacloud-cdn-traffic-anomaly
description: |
  Read-only diagnostics for Alibaba Cloud CDN traffic and bandwidth anomalies.
  Use when CDN traffic or bandwidth suddenly spikes, the CDN bill jumps
  unexpectedly, traffic theft or hotlink abuse is suspected, or bps/flow/QPS
  trends need baseline comparison to locate anomalous time windows. Pulls usage
  data via aliyun CLI to locate anomalous windows, then forensically analyzes
  CDN offline access logs (four-dimension Top statistics, 13 theft rules,
  T1~T6 classification) and outputs an analysis report; never stops domains
  or changes any configuration.
  Triggers: "traffic spike", "bandwidth anomaly", "traffic theft",
  "unusual CDN traffic", "hotlink abuse", "CDN bill surge",
  "traffic suddenly increased", "bandwidth spike analysis".
---

# CDN Traffic Anomaly Diagnosis

Diagnose CDN traffic/bandwidth anomalies: "traffic suddenly increased", "bandwidth spiked last night", "CDN bill jumped, suspect traffic theft", "is someone hotlinking my resources", "locate the abnormal time window".

Core approach: confirm identity and target domain, pull bps/flow/QPS usage data for the requested time window, compute a baseline (mean/median), locate anomalous intervals by peak/baseline comparison, then run offline-log forensics on the anomalous window (four-dimension Top statistics, 13 theft-abuse rules, T1~T6 scenario classification) and output a structured conclusion with evidence-based suggestions.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating API — e.g. `StopCdnDomain`, `DeleteCdnDomain`, `SetDomainServerCertificate`, `Modify*`, `RefreshObjectCaches`, `PushObjectCache`, or any configuration change. This includes scripts "for the user to run manually". If the user asks to stop a domain, block hotlinkers, or change configuration, only output the manual remediation workflow and declare this skill is read-only.
2. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. Credentials are resolved automatically by the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
3. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by the usage-data APIs. If a query fails or returns empty, record it and state the limitation — never invent traffic numbers.
4. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <Code>: <Message>` to stderr and continue with the remaining queries — never silently skip or abort the whole diagnosis. The final report is still produced with the data at hand.

## Observability

All OpenAPI calls (invoked through the aliyun CLI) include:
- **User-Agent**: `--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`
- **SKILL_NAME**: `alibabacloud-cdn-traffic-anomaly`
- **session-id**: 32-character hex string generated per diagnostic session (one `uuid.uuid4().hex` per script run) and attached to every CLI command in the same run.

The entry script implements this automatically: `_SESSION_ID = uuid.uuid4().hex` and `_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-cdn-traffic-anomaly/{_SESSION_ID}"` are concatenated into the `--user-agent` argument of every `aliyun` invocation.

## Prerequisites

1. **aliyun CLI 3.x** — required: all CDN usage-data queries and the identity check are invoked via the `aliyun` CLI plugin mode (e.g. `aliyun cdn describe-domain-bps-data`, `aliyun sts get-caller-identity`). No direct HTTP signing, no external Python SDK.
2. **Python 3.9+** — standard library only, no third-party dependencies.
3. **Alibaba Cloud credentials** — resolved automatically by the aliyun CLI default credential chain (environment variables or `~/.aliyun/config.json`). Do not read, print, or pass AK/SK/STS tokens explicitly.
4. **Target inputs**: CDN domain name (required) and optional time window (`--days`, default 7). UID can be omitted — it is derived via `aliyun sts get-caller-identity` for traceability only. Auto-fill first, ask second: never ask the user for UID when it can be derived; only ask for the domain when it truly cannot be inferred.

   **Auto-fill declaration requirement**: Whenever any parameter is auto-filled (time window, UID, or interval), the Agent MUST explicitly declare this in the response or report metadata, e.g. "Time window auto-defaulted to last 7 days" or "UID auto-derived via sts:GetCallerIdentity: 1772241626973633".

## Authentication

Credentials are resolved automatically by the aliyun CLI default credential chain (environment or `~/.aliyun/config.json`). Do not read, print, or pass AK/SK/STS tokens explicitly.

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-cdn-traffic-anomaly

# Verify caller identity (informational only; credentials always come from the CLI default chain)
aliyun sts get-caller-identity
```

**Identity Verification Failure**: If `sts get-caller-identity` fails, the default credential chain is not configured. Guide the user to run `aliyun configure` — never ask for AK/SK.

## Diagnostic Flow

### Step 1: Confirm Identity and Target Domain

Confirm the CDN domain to analyze. If the user omitted the domain but the intent is clear and the domain can be discovered, derive it and declare the derivation; otherwise ask one brief clarifying question (domain + time window).

### Step 2: Pull Usage Data for the Time Window

```bash
cd $SKILL_DIR && python3 scripts/cdn_traffic_anomaly.py --domain <DOMAIN> [--days 7] [--interval 3600]
```

The entry script pulls, in order and each with `[WARN]`-and-continue error handling:

| Query | CLI command | Purpose |
|-------|-------------|---------|
| Caller identity | `aliyun sts get-caller-identity` | Traceability (UID label only) |
| Usage series | `aliyun cdn describe-domain-usage-data` | bps + traf (traffic, bytes/interval) per interval (primary). The API only accepts `--field bps|traf|acc` (`flow` is rejected with `InvalidParameterField`) |
| BPS series | `aliyun cdn describe-domain-bps-data` | Bandwidth trend backup |
| QPS series | `aliyun cdn describe-domain-qps-data` | Request-rate correlation |
| Real-time bps | `aliyun cdn describe-domain-real-time-bps-data` | Last-hour fine-grained view |
| Origin bps | `aliyun cdn describe-domain-src-bps-data` | Origin (return-to-source) bandwidth trend; backs the T6 origin-amplification assessment. On failure: `[WARN]`-continue, T6 falls back to MISS-ratio judgment only and the report marks the degradation |

All responses are parsed tolerantly (layer-by-layer `.get`); no field structure is assumed hardcoded.

### Step 3: Baseline Comparison

For each retrieved series the script computes:
- **Baseline**: mean and median of all data points in the window
- **Peak**: maximum value and its timestamp
- **Threshold**: `max(mean * PEAK_MEAN_RATIO, median * PEAK_MEDIAN_RATIO)` (constants embedded in the script; see [references/anomaly-detection-flow.md](references/anomaly-detection-flow.md))

### Step 4: Locate Anomalous Time Windows

Intervals whose value exceeds the threshold are grouped into contiguous anomalous windows (start time, end time, peak value, multiple over baseline). The verdict is graded: `normal` / `suspicious` / `anomalous` per the ratio rules in [references/anomaly-detection-flow.md](references/anomaly-detection-flow.md).

### Step 5: Offline-Log Forensics on the Anomalous Window

Once anomalous windows are located (or the user directly provides a suspect window), drill into the actual access logs with:

```bash
cd $SKILL_DIR && python3 scripts/cdn_traffic_analysis.py --domain <DOMAIN> \
    --start-time "YYYY-MM-DD HH:MM:SS" --end-time "YYYY-MM-DD HH:MM:SS"
```

The script calls `aliyun cdn describe-cdn-domain-logs` (the only cloud API it uses), downloads the gzip offline logs, then locally computes:

1. **Four-dimension Top statistics** (each with both request-count and traffic metrics): URL, IP + /24 subnet, Referer, User-Agent.
2. **Commonality analysis**: status codes, cache hit ratio, HTTP methods, hourly distribution, response-size buckets, per-IP request-frequency buckets.
3. **13 theft-abuse rules** (thresholds embedded as constants): per-IP high frequency, single-Referer concentration, large-file traffic share, same-second concurrency, identical/empty UA share, uniform request intervals, wide IP dispersal with consistent per-IP volume, etc. A rule only scores when both the ratio signal and the absolute-volume gate pass (prevents false positives on tiny samples).
4. **T1~T6 scenario classification** by concentration (see Fault Scenarios below) and evidence-based recommendations.

Notes: offline logs are downloadable ~3~4 hours after the fact; logs are split per hour, so align the window to whole hours. If the user reports a suspected theft but no anomalous window is found, still run this step on the reported window before concluding "no anomaly".

### Step 6: Conclusion and Suggestions

Generate the report per [references/report-template.md](references/report-template.md), including: window metadata, per-metric statistics, anomalous windows, four-dimension Top tables, rule hits, scenario verdict, and evidence-based suggestions (e.g. Referer/UA/IP protection, bandwidth cap — as manual guidance only, never executed by this skill).

**Mandatory cross-validation before recommending protection**: verify the suggested rule does not harm the real business scenario (e.g. do not recommend Referer anti-hotlink for a download/SDK/API business whose clients legitimately send empty Referers). See [references/anomaly-detection-flow.md](references/anomaly-detection-flow.md).

## Limitations

- **R03 (overseas-IP ratio) has no script support**: this public-cloud build performs no IP geolocation lookup (read-only, no third-party services). R03 is manual evaluation only — the qualitative report MUST NOT cite overseas-traffic-ratio conclusions unless the user themselves provides region/geo information.
- Offline access logs become downloadable roughly 3~4 hours after the fact; windows within that lag cannot be forensically analyzed yet.
- When `describe-domain-src-bps-data` fails, the T6 origin-amplification assessment degrades to MISS-ratio judgment only (explicitly marked in the report).

## Fault Scenarios

| Code | Scenario | Signal | Action |
|------|----------|--------|--------|
| T1 | URL concentration (hotlink abuse on specific resources) | Top URL/pattern share ≥ 30% of requests/traffic | URL authentication (Type A/B/C), hotlink protection; manual guidance only |
| T2 | IP / subnet concentration (scraper, attack botnet) | Top IP or /24 subnet share ≥ 30% | IP blacklist / rate limiting guidance; manual only |
| T3 | Referer anomaly (off-site hotlinking) | Empty or off-site Referer share ≥ 50%/30% | Referer whitelist/anti-hotlink — but cross-check the business scenario first (downloads/SDKs legitimately send empty Referer) |
| T4 | User-Agent anomaly (scripted clients) | Suspicious/identical UA share ≥ 30% | UA blacklist guidance; manual only |
| T5 | Dispersed traffic (benign spike) | All four dimensions dispersed; matches a business event | No protection needed; confirm with the business owner; consider bandwidth cap only for cost control |
| T6 | Origin amplification (low cache hit) | MISS ratio ≥ 50%, corroborated by a rising origin-bps trend from `describe-domain-src-bps-data` when available; if that query failed, judgment is MISS-ratio only and the report states so | Cache-TTL / cacheability tuning guidance; manual only |
| T0 | No data / query degraded | API empty or errored | Record each `[WARN]`, verify domain and RAM permission (see [references/ram-policies.md](references/ram-policies.md)), report the limitation honestly |

Regardless of the scenario, always include the **safety-net advice**: configure a bandwidth cap and billing alerts so a future anomaly cannot silently blow up the bill (guidance only; this skill never applies it).

## Constraints

- **Read-only operations**: only Describe-class usage-data/log queries and `sts:GetCallerIdentity`; never stops domains, modifies configuration, submits refresh/preload jobs, or deletes anything.
- **ABSOLUTE PROHIBITION**: no mutating API of any kind, including "helper scripts for the user".
- **Solutions must be evidence-based**: based on retrieved usage data or official documentation only.
- **Credentials**: CLI default credential chain only; AK/SK never read, printed, or passed.

## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/cdn_traffic_anomaly.py` | Pull bps/flow/QPS usage data, compute baseline/peak, locate anomalous windows, output JSON or text report |
| `scripts/cdn_traffic_analysis.py` | Offline-log forensics: DescribeCdnDomainLogs → download gzip logs → four-dimension Top statistics, 13 theft rules, T1~T6 classification, recommendations |

CLI options for `cdn_traffic_anomaly.py`: `--domain <DOMAIN>` (required), `--days <N>` (default 7), `--interval <300|3600|86400>` (default 3600), `--json` (JSON output), `--quiet` (suppress analysis, final report only), `--no-raw` (trim `api_raw_responses` to per-query summaries to save downstream tokens; recommended when the output is consumed by an Agent).

CLI options for `cdn_traffic_analysis.py`: `--domain <DOMAIN>` (required), `--start-time` / `--end-time` (default: yesterday, whole day, UTC), `--top-n <N>` (default 5), `--log-dir <DIR>` (local log cache directory, default `scripts/.cdn_logs`), `--max-files <N>` (default 24), `--json`, `--quiet`, `--keep-logs` (keep downloaded gzip files; otherwise cleaned up).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Default credential chain not configured | Run `aliyun configure`; never ask the user for AK/SK |
| `Forbidden` / `NoPermission` | RAM policy missing a Describe permission | Record the missing action, continue with remaining queries, point to [references/ram-policies.md](references/ram-policies.md) |
| `InvalidDomainName.Malformed` / `InvalidParameter` | Wrong domain or parameter value | Log `[WARN]`, verify domain spelling, continue |
| `Throttling.User` | Request rate limited | Log `[WARN]`, continue with remaining queries |
| `InternalError` / `ServiceUnavailable` | Transient service-side failure | Log `[WARN]`, continue; do not conclude "service down" from a single call |
| Empty data series | No traffic in the window (offline domain, wrong name) | Report "no data" honestly (exit 2, `error_code=NoUsageData` / `NoLogsInWindow`), verify the domain and window |

All errors follow the `Code: Message` format raised as `RuntimeError` inside the script and degraded with `[WARN]` on stderr; the report is always emitted with whatever data succeeded. Non-JSON multi-line SDKError text from the real aliyun CLI is handled too: the scripts regex-extract `Code:` / `Message:` before falling back to the raw text.

### Exit-code contract (both scripts)

| Exit code | Meaning |
|-----------|---------|
| 0 | Analysis completed with usable data (may be partially degraded) |
| 1 | Real error: critical API error (e.g. `InvalidDomain.NotFound`, `InvalidAccessKeyId.NotFound`) or all log downloads failed |
| 2 | Benign no-data: no usage data / no offline logs in the window. Not an error — tell the user and verify the domain/window |

### Stable `error_code` field (both scripts)

Every JSON (and text) result carries a stable `error_code` field for programmatic branching: `InvalidDomain.NotFound` | `InvalidAccessKeyId.NotFound` | `NoLogsInWindow` (analysis) | `AllDownloadsFailed` (analysis) | `NoUsageData` (anomaly) | `""` (normal). Other raw API codes pass through verbatim on error paths.

### Output contract for Agents

With `--json`, **stdout carries ONLY the JSON document**; all progress and `[WARN]` diagnostics go to stderr. Branch on `ok` + `error_code` + exit code instead of parsing free text. Text reports open with an `[EXECUTIVE SUMMARY]` block (verdict, peak multiple / risk level, scenario, strongest evidence) so non-technical users see the conclusion first.
