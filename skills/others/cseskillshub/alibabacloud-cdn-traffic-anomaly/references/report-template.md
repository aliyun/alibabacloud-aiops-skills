# Report Template

Use this template when merging script output into the final diagnosis report (Step 6 of the diagnostic flow). Fill every placeholder from actual script output; leave a section as "not available (reason)" when data is missing — never fabricate.

```markdown
## CDN Traffic Anomaly Diagnosis Report

### 0. Executive Summary (conclusion first)
- Verdict: {anomalous/suspicious/normal/insufficient-data/no-data} — {one plain-language sentence}
- Peak: {ratio}x baseline on {series}; anomalous window {start ~ end} (or "none detected")
- (After forensics) Abuse: {ABUSE SUSPECTED / no abuse pattern} (risk {high|medium|low}); scenario {T1~T6} — {strongest evidence one-liner}

### Request Context
- Domain: {domain}
- Analysis window: {start_time} ~ {end_time} (timezone: UTC)
- Caller UID (derived via sts:GetCallerIdentity): {uid}
- Auto-filled parameters: {auto_fill_declaration, e.g. "time window auto-defaulted to last 7 days"}

### 1. Usage Baseline Comparison
| Metric | Baseline (mean/median) | Peak | Peak time | Multiple over baseline | Verdict |
|--------|------------------------|------|-----------|------------------------|---------|
| bps    | {bps_mean} / {bps_median} | {bps_peak} | {bps_peak_time} | {ratio} | normal/suspicious/anomalous |
| flow   | ... | ... | ... | ... | ... |
| QPS    | ... | ... | ... | ... | ... |

Anomalous windows: {window_list with start/end/peak/multiple, or "none detected"}

### 2. Offline-Log Forensics (on the anomalous window)
- Log files analyzed: {n_files} (parsed {parsed_lines}/{total_lines} lines)
- Total requests: {total_requests}; total traffic: {total_traffic}

#### Four-dimension Top statistics
| Dimension | Top entry | Requests (share) | Traffic (share) |
|-----------|-----------|------------------|-----------------|
| URL       | {url}     | {n} ({pct})      | {b} ({pct})     |
| IP / subnet | {ip}    | ...              | ...             |
| Referer   | {refer}   | ...              | ...             |
| User-Agent | {ua}     | ...              | ...             |

#### Commonality analysis
- Status codes: {status_distribution}
- Cache hit ratio: {hit_pct} HIT / {miss_pct} MISS
- Hourly distribution: {hour_summary} (hour buckets follow log-line timestamps, +0800 Beijing time; the query window is UTC)
- Response-size buckets: {size_bucket_summary}
- Per-IP frequency: {machine_ips} machine-like IPs ({machine_ratio} of requests)

### 3. Theft-Abuse Determination
- Matched rules ({n}): {matched_rule_list, e.g. R02, R04, R10}
- Risk level: {high|medium|low} (score {score})
- Key evidence: {top_signals}

### 4. Scenario Verdict
- Classification: {T1~T6/T0} — {scenario_label}
- Findings: {findings}
- Confidence: {high/medium/low} — basis: {basis, e.g. "full-hour offline logs, N requests sampled"}

### 5. Recommendations (manual guidance only — this skill applies nothing)
1. {recommendation_1, scenario-specific, cross-validated against the business type}
2. {recommendation_2}
3. Safety net: configure a bandwidth cap and billing alerts.

### 6. Limitations / Warnings
- {each [WARN] recorded during the run, e.g. degraded queries, empty windows}
```

## Field rules

- All numbers come directly from script stdout/JSON; do not round beyond readability.
- The script text reports already open with an `[EXECUTIVE SUMMARY]` block; mirror it as section 0 of the merged report so the conclusion comes first.
- Branch on the stable `error_code` field and exit codes (0 = success, 1 = error, 2 = benign no-data) when deciding whether to run the next stage.
- If a query degraded (`[WARN]`), the corresponding table row shows "not available: Code Message".
- Recommendations must reference only real CDN capabilities — see [protection-capabilities.md](protection-capabilities.md).
- Keep the safety-net item (bandwidth cap + billing alerts) in every report, even for benign verdicts.
