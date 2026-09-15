# Throttling Attribution Decision Tree

Route the reported symptom to a verdict before concluding. Evidence order:
captured error code > measured peaks > symptom pattern. All watermark
figures must come from the console/CloudMonitor verification channels
(references/throttling-rules.md sec.4) - never invented.

## Decision tree

```
Q1. Did the client capture an HTTP 503 with a throttle-family error code
    (DownloadTrafficRateLimitExceeded / UploadTrafficRateLimitExceeded /
    TotalQpsLimitExceeded / MetaOperationQpsLimitExceeded /
    ActiveRequestLimitExceeded / CpuLimitExceeded / PartitionQpsLimitted)
    or a SlowDown marker, or an HTTP 429 QpsLimitExceeded?
    +- YES -> verdict: server-throttle-confirmed.
    |        Route by code: bandwidth codes -> region bandwidth table;
    |        QPS codes -> QPS defaults + prefix dispersion check;
    |        PartitionQpsLimitted (EC 0026-00000028) -> hotspot partition,
    |        disperse key prefixes; 429 QpsLimitExceeded -> client sends
    |        too many requests over a period, lower the rate and retry.
    |        ServiceUnavailable alone = server busy, retry with backoff.
    `- NO  -> Q2.

Q2. Is the measured peak QPS/bandwidth ABOVE the official default of the
    bucket's region (references/throttling-rules.md sec.1/sec.2)?
    +- YES -> verdict: region-quota-pressure-likely. Requests beyond the
    |        default are rejected with 503 even when no code was captured.
    `- NO  -> Q3.

Q3. Do object keys use sequential prefixes (timestamps / alphabetical),
    AND does the incident show 503/SlowDown/slowdown symptoms or the peak
    sits near (>= 80%) the sequential QPS default (2,000)?
    +- YES -> verdict: hotspot-partition-likely. One partition sustains
    |        ~2,000 req/s; hash or reverse the prefixes first.
    `- NO  -> Q4.

Q4. Is the dominant symptom client-side TIMEOUT (or slow transfer) while
    the server side shows NO 5xx and no throttle error code?
    +- YES -> verdict: client-or-network-likely. Check DNS resolution,
    |        cross-region/cross-border link quality, and the client's own
    |        bandwidth; verify with OSS access logs that the server
    |        returned no errors. Do NOT conclude throttling.
    `- NO  -> Q5.

Q5. Symptom present (503/slow) but no code and no measurements?
    +- YES -> verdict: throttle-suspected-unverified. Verify against the
    |        console bandwidth/QPS watermark of the incident window and
    |        the x-oss-qos-delay-time header before concluding.
    `- NO  -> verdict: evidence-insufficient. Collect the error code,
             measured peaks, and time window first.
```

## Symptom shortcuts (from historical tickets)

- "Occasional 503 at a fixed hour" -> throttle window: correlate with the
  minute-level QPS/bandwidth watermark; bursty public traffic often means
  CDN caching gaps or a scheduled job.
- "Upload suddenly slow, other buckets fine, OSS side shows no throttle"
  -> compare across buckets/regions first; single-bucket slowness without
  server errors usually sits in the client-to-OSS path.
- "Bandwidth cap reached on several buckets in one region" -> the cap is
  account+region scoped; heavy buckets squeeze each other - resource pool
  QoS / quota increase is the structural answer.
- "Received a CloudMonitor Bucket/User...ThresholdExceeded alarm" -> the
  throttling already happened server-side (reporting threshold is 0.8x the
  throttle threshold); correlate the alarm window with the incident before
  any other attribution (see references/throttling-rules.md sec.3a).
- "Slow reads but no 503" -> bandwidth throttling only RAISES latency; QPS
  throttling REJECTS requests with 503. Latency-only symptoms point at
  bandwidth pressure rather than QPS pressure.
- "Timeout only from overseas clients" -> cross-border link limits, not
  throttling; evaluate transfer acceleration (separate skill) or a closer
  region.

## What this tree does NOT answer

- Single-request error codes unrelated to throttling (403/404/signature):
  defer to the transfer-error-code skill.
- Which acceleration product to buy: defer to the transfer-acceleration
  skill.
- Actually raising a quota or creating a resource pool: manual ticket
  process only (references/quota-increase.md).
