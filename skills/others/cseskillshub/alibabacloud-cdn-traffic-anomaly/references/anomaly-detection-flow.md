# Anomaly Detection Flow

End-to-end methodology for CDN traffic/bandwidth anomaly diagnosis. Adapted from the internal 0.5.0 diagnosis tree: locate the anomalous time window first, then forensically analyze offline logs, then classify and advise.

## Overview

```
User report (spike / bill jump / suspected theft)
        │
        ▼
Step 1  Confirm identity & target domain (sts:GetCallerIdentity, ask only when needed)
        │
        ▼
Step 2  Pull usage series (bps / flow / QPS / real-time bps / origin bps) for the window
        │
        ▼
Step 3  Baseline comparison → locate anomalous time windows
        │
        ▼
Step 4  Offline-log forensics on the anomalous window
        │  four-dimension Top statistics → 13 theft rules → T1~T6
        ▼
Step 5  Cross-validate with the business scenario (prevent false protection)
        │
        ▼
Step 6  Report + recommendations, always with bandwidth-cap / billing-alert safety net
```

## Step 3: Baseline comparison thresholds

For each usage series in the requested window:

- Baseline = mean and median of all data points.
- Anomaly threshold = `max(mean × 3.0, median × 4.0)` (embedded constants `PEAK_MEAN_RATIO`, `PEAK_MEDIAN_RATIO`).
- Intervals above the threshold are merged into contiguous anomalous windows.
- Verdict grading: peak/baseline ratio `≥ 3.0` → `anomalous`; `≥ 2.0` → `suspicious`; otherwise `normal`. Fewer than 6 data points → `insufficient-data`; empty series → `no-data`.

## Step 4: Offline-log forensics

Data source: `DescribeCdnDomainLogs` → gzip offline access logs (downloadable ~3~4 hours after the fact, split per hour).

### 4.1 Four-dimension dual-metric Top statistics

For each of the four dimensions — **URL**, **IP + /24 subnet**, **Referer**, **User-Agent** — compute both:
- Request-count share (concentration of request volume), and
- Traffic share (concentration of transferred bytes).

A dimension that is concentrated on BOTH metrics is a strong theft signal; concentration on traffic only suggests large-object abuse; on requests only suggests CC-style probing.

### 4.2 Commonality dimensions

Status-code distribution, cache hit ratio (HIT/MISS), HTTP methods, hourly distribution, response-size buckets, and per-IP request-frequency buckets (machine-like IPs ≥ 1000 requests, narrow-band frequency clustering).

### 4.3 The 13 theft-abuse rules

Each rule fires only when BOTH its ratio signal and its absolute-volume gate pass (dual gate prevents false positives on tiny samples; total samples < 100 forces the verdict to low).

| # | Rule | Signal |
|---|------|--------|
| R01 | Wide IP dispersal with consistent per-IP volume | ≥ 100 unique IPs, low per-IP volume CV, AND a dual absolute-volume gate (total ≥ 1000 requests AND ≥ 3 req/IP on average); below the gate the rule is skipped and marked so — on tiny samples (e.g. 300 reqs / 250 IPs at 1-2 req/IP) the CV is ~0 by construction and would false-positive |
| R02 | Per-IP high frequency | Any single IP ≥ 500 requests in the window |
| R03 | Overseas-IP ratio mismatch | Manual evaluation only — no script support in this build (no IP geo lookup; read-only, no third-party). The qualitative report must NOT cite overseas-traffic-ratio conclusions unless the user provides region/geo information |
| R04 | Empty-Referer dominance | Empty/direct Referer ≥ 50% with absolute-volume gate (weak variant at ≥ 30%) |
| R05 | Single Referer domain concentration | One Referer domain ≥ 40% share with absolute-volume gate |
| R06 | Top-1 Referer dominance | Dominant single Referer (manual review: competitor or aggregator site) |
| R07 | Large-file traffic concentration | Large-file size bucket ≥ 50% of traffic and ≥ 100 MB absolute |
| R08 | URI with regularly varying parameters | Parameterized URL pattern ≥ 30% share with absolute-volume gate |
| R09 | Uniform request intervals | Per-IP inter-request interval CV ≤ 0.3 (scripted pacing) |
| R10 | Same-second concurrency | ≥ 20 requests from one IP in the same second |
| R11 | Suspicious-UA dominance | Non-browser/tool-like UAs ≥ 30% with absolute-volume gate |
| R12 | Identical-UA dominance | One fully identical UA ≥ 50% (mainstream browser UAs excluded) |
| R13 | Empty UA | Empty or '-' UA ≥ 30% with absolute-volume gate |

Risk score: dual-gate scoring (ratio signal + absolute-volume gate) → `high` (score ≥ 60), `medium` (≥ 30), `low` otherwise; samples < 100 requests force the level to `low`.

### 4.4 T1~T6 scenario classification

Classified by which dimension concentrates the traffic (share ≥ 30%):

| Code | Scenario | Determining signal |
|------|----------|--------------------|
| T1 | URL concentration | Top URL/URL-pattern request or traffic share ≥ 30% |
| T2 | IP / subnet concentration | Top IP or /24 subnet share ≥ 30% |
| T3 | Referer anomaly | Empty or off-site Referer share dominant |
| T4 | User-Agent anomaly | Suspicious or identical UA share ≥ 30% |
| T5 | Dispersed traffic | No dimension concentrates → likely benign spike; confirm with the business owner |
| T6 | Origin amplification | MISS ratio ≥ 50%, corroborated by a rising origin-bps trend (`DescribeDomainSrcBpsData`) when available; if that query failed, MISS-ratio judgment only (marked in the report) → cache configuration issue |

Priority: T1 → T2 → T3 → T4 → T6 → T5 (first concentrated dimension wins; T5 is the fallback).

## Step 5: Mandatory business-scenario cross-validation (prevent collateral damage)

**Never recommend a protection rule without verifying it does not block legitimate traffic.**

| Business scenario | Referer anti-hotlink | URL authentication | IP blacklist | UA blacklist |
|-------------------|----------------------|--------------------|--------------|--------------|
| Embedded web resources (img/CSS/JS) | Effective | Usable | Limited | Limited |
| APP / client downloads (.apk/.ipa/.exe) | NOT applicable (clients send no Referer) | **Recommended** | Limited | Usually ineffective |
| Video / streaming | Partial | **Recommended** | Limited | Usually ineffective |
| API backends | NOT applicable | Usable | Limited | Limited |
| Mini-programs | NOT applicable | Usable | Limited | Match fixed platform UAs only |

Rules of thumb:
- Download / SDK / API businesses legitimately send empty Referers → do NOT lead with Referer anti-hotlink; prefer URL authentication.
- UA blacklists are useless when attackers spoof mainstream browser UAs.
- IP blacklists are ineffective against distributed attacks (2000+ IPs, low per-IP volume) or proxy pools.
- Referer and UA can be forged: they are basic defenses, not strong ones.

### Empty-Referer × User-Agent cross-validation decision tree

When the empty-Referer share is high, do not conclude from the Referer dimension alone — cross-check the Top UA distribution:

```
Empty-Referer share high (R04 / T3 signal)
        │
        ▼
Inspect Top User-Agents of the empty-Referer traffic
        │
        ├─ UA highly consistent (one dominant identical/suspicious UA)
        │      → Strong attack signal: scripted direct access; proceed with
        │        T3/T4 handling (UA-based guidance + URL authentication)
        │
        └─ UA dispersed, or dominated by legitimate clients
           (okhttp / Dalvik / custom App UAs / mainstream browsers)
               → Abandon the Referer dimension: these are normal app/direct
                 clients. Switch to URL authentication and/or the IP dimension.
                 NEVER recommend blocking empty Referers outright — it causes
                 collateral damage to legitimate clients.
```

## Step 6: Safety-net recommendations (always include)

Regardless of the scenario verdict, always advise:
1. **Bandwidth cap** on the domain (CDN console) so a future anomaly cannot silently blow up the bill. The domain goes offline when exceeded — a deliberate cost-control trade-off.
2. **Billing alerts** so abnormal charges are noticed early.
3. If CDN-native capabilities are insufficient (rate limiting, WAF rules, bot management, JS challenge), state honestly that CDN does not provide them and that ESA/DDoS-pro products are the upgrade path — do not invent CDN features.

## Cross-skill linkages

- Bandwidth up but request count flat → cache-hit issue (T6 direction), check MISS ratio.
- Bill anomaly but traffic normal → billing-mode mismatch; compare peak-95 vs pay-by-traffic vs pay-by-bandwidth.
- Domain sandboxed/offline after an attack → out of scope for this read-only skill; advise the user to contact support.

## Output contract (exit codes, error_code, stdout purity)

- Exit codes (both scripts): `0` = completed with usable data; `1` = real error (critical API error or all downloads failed); `2` = benign no-data (no usage data / no offline logs in the window — not an error).
- Stable `error_code` field: `InvalidDomain.NotFound` | `InvalidAccessKeyId.NotFound` | `NoLogsInWindow` | `AllDownloadsFailed` | `NoUsageData` | `""` (normal); other raw API codes pass through verbatim on error paths.
- `--json` stdout purity: JSON only on stdout, diagnostics on stderr; branch on `ok` + `error_code` + exit code.
- Both text reports open with an `[EXECUTIVE SUMMARY]` block (conclusion first, plain language).
