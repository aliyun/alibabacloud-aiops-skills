# Report-Analysis Knowledge Base — alibabacloud-pts-reporter

> Curated symptom → finding mapping used in Core Workflow Step 2.
> All categories are bounded to **what a PTS report itself exposes** —
> instance-level resource bottlenecks (CPU / Memory / Disk-IO / Network) are
> explicitly out of scope and live in a separate cloud-product diagnostic skill.
>
> Every diagnostic rule below cites only PTS report fields (QPS/TPS curve,
> RT percentiles, error code distribution, sampler breakdown, concurrency
> curve, baseline delta).

---

## 1. PTS Client-Config

**Symptoms (from report fields)**
- Report shows `ConnectTimeout` / client-side backoff events while sampler
  success rate stays high on retries
- QPS fails to rise even though concurrency keeps ramping (and no 5xx
  cluster appears — see Application-Layer for that case)
- Handshake-heavy traffic: every request triggers a new TLS handshake (no
  keep-alive), inflating P50 RT artificially

**Likely causes**
- PTS concurrency ramp too steep — pressure source can't open connections fast enough
- HTTPS without keep-alive — TLS handshake on every request
- Pressure source region too far from target — base latency floor too high
- Misconfigured think-time / pacing leading to bursty traffic

**Findings (ranked)**
1. Flatten concurrency ramp; switch to stepwise model to find true knee-point
2. Enable keep-alive on the sampler so connections are reused
3. Select a pressure source region closer to the target Region
4. Adjust pacing / think-time to smooth request distribution

**Data source (PTS report fields)**: `Concurrency` curve, `ConnectTimeout`
counts, sampler-level connection metrics, sampler URL scheme, scene
`PressureSource` config (via `GetPtsScene`)

---

## 2. Application-Layer

**Symptoms (from report fields)**
- 5xx error rate clusters at a specific QPS threshold in the report
- Error codes concentrate on a single sampler / API in the sampler breakdown
- 4xx vs 5xx ratio shifts as load grows
- `ConnectionRefused` / `ReadTimeout` codes appear in the error distribution

**Likely causes**
- DB connection pool undersized in the application
- Upstream dependency saturating under its own load
- Synchronous call chain without timeout / circuit-breaker
- Application-level rate limiter / WAF kicking in

**Findings (ranked)**
1. Tune DB pool / HTTP client pool (max size, timeout) on the failing sampler
2. Add circuit breaker / bulkhead per upstream identified by the sampler
3. Convert hot synchronous calls to async / batch
4. Verify rate-limit / WAF rules against the failing sampler URL

**Data source (PTS report fields)**: per-sampler error count, error-code
distribution, success-rate-vs-time curve, response-time vs. error correlation

---

## 3. Throughput-Pattern

**Symptoms (from report fields)**
- QPS / TPS curve plateaus while concurrency continues to climb
- Stepwise ceilings — throughput jumps to a level then flatlines repeatedly
- Throughput curve oscillates with high variance instead of converging
- Saturation knee-point appears earlier than the configured baseline target
- Large delta vs `GetPtsSceneBaseLine` (current run regresses against baseline)

**Likely causes**
- Server-side capacity reached (further diagnosis requires instance-level skill — surface handoff)
- A dependency in the call chain is the rate-limiter
- Sampler logic introduces a serialization bottleneck

**Findings (ranked)**
1. Flag the knee-point QPS as the report-observed ceiling for this configuration
2. If baseline supplied, quantify the regression (`current_peak_qps / baseline_peak_qps`)
3. Recommend an instance-level diagnostic run to locate the actual resource bottleneck (handoff)
4. Suggest sampler-level subdivision to isolate which API caps the throughput

**Data source (PTS report fields)**: `TPS` / `QPS` time series, `Concurrency`
time series, baseline delta from `GetPtsSceneBaseLine`

---

## 4. Latency-Pattern

**Symptoms (from report fields)**
- P99 spikes while P50 stays flat — long-tail divergence
- RT percentiles climb roughly linearly with concurrency (queuing)
- P90 / P99 jump in discrete steps at specific QPS levels
- RT distribution shape becomes bimodal (two clusters of slow vs fast requests)
- Baseline delta shows P99 regressed materially (e.g., +50%) at the same load

**Likely causes**
- Long-tail GC / lock contention (further diagnosis requires instance-level skill — surface handoff)
- Connection pool queue building up
- Upstream dependency adding tail latency
- Cold-cache / warm-up effect at start of run

**Findings (ranked)**
1. Quote the P99 spike value and the QPS at which it appears
2. If baseline supplied, quantify the P99 regression vs baseline
3. Recommend an instance-level diagnostic run if the tail is suspected to be GC / contention (handoff)
4. Suggest a warm-up phase before the main load if the spike concentrates at run start

**Data source (PTS report fields)**: per-sampler `RT_P50` / `RT_P90` / `RT_P99`
time series, RT histogram, baseline delta from `GetPtsSceneBaseLine`

---

## Severity Classification

| Severity | Criteria (report-only) |
|----------|------------------------|
| **high** | Error rate > 1% at target QPS, OR P99 regression > 50% vs baseline, OR throughput knee below target |
| **medium** | Error rate 0.1–1%, OR P99 regression 20–50% vs baseline, OR throughput plateau within 20% of target |
| **low** | Purely preventive observation (e.g., handshake-heavy pattern with no SLA breach) |

---

## Anti-Patterns (DO NOT suggest)

| Don't | Why |
|-------|-----|
| Diagnose CPU / Memory / Disk / Network bottlenecks | Out of scope — needs instance-level metrics, use a separate skill |
| "Scale up the instance" without instance-level evidence | This skill has no instance data; surface a handoff instead |
| Recommend based on a metric not present in the report payload | Hallucination |
| Suggest PTS scenario changes inside this skill | That's `alibabacloud-pts-task`'s territory — announce handoff |
| Suggest credential / network ACL changes | Out of scope; refer to security skills |
