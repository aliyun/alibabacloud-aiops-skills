# Thresholds & Health Score Algorithm

## Threshold file

- **Default template (read-only)**: `<skill_root>/assets/thresholds.default.yaml`
- **User-editable file**: `<skill_root>/thresholds.yaml`

`inspect.sh` startup logic:
1. If the user file is missing, copy from the default template and print a one-time hint. The current run continues with default values.
2. If the user file exists, load it directly (no hint).

Edits to the user file take effect on the next invocation — no restart required.

## Default thresholds

Each metric has two thresholds: `warn` (yellow, −5 points) and `critical` (red, −15 points). Metrics set to `null` are shown but not scored.

### Instance dimension

| Metric | warn | critical | Note |
|--------|------|----------|------|
| `InstanceTpsUtilization` | 80 | 95 | Instance TPS utilization (%) |
| `InstanceSendTpsUtilization` | 80 | 95 | Send TPS utilization (%, 5.0 only) |
| `InstanceReceiveTpsUtilization` | 80 | 95 | Receive TPS utilization (%, 5.0 only) |
| `InstanceOnlineClientsUtilization` | 80 | 95 | Online client utilization (%) |
| `ThrottledSendRequestsPerInstance` | 1 | 100 | Instance send throttles per minute |
| `ThrottledReceiveRequestsPerInstance` | 1 | 100 | Instance receive throttles per minute |
| `InstanceTrafficRXUtilization` | 80 | 95 | Public RX bandwidth utilization (%) |
| `InstanceTrafficTXUtilization` | 80 | 95 | Public TX bandwidth utilization (%) |
| `InstanceDropTrafficRX` | 1 | 1000 | Public RX drop bit/s (anything >0 is suspicious) |
| `InstanceDropTrafficTX` | 1 | 1000 | Public TX drop bit/s (anything >0 is suspicious) |

Display-only (not scored): `InstanceApiCallTps`, `InstanceApiCallTpsMax`, `InstanceSendApiCallTps`, `InstanceReceiveApiCallTps`, `SendMessageCountPerInstance`, `ReceiveMessageCountPerInstance`, `InstanceOnlineClients`, `InstanceActiveConnection`, `InstanceTrafficRX/TX`, `InstanceInternetFlowoutBandwidth`, `InstanceStorageSize`.

### Group dimension

| Metric | warn | critical | Note |
|--------|------|----------|------|
| `ConsumerLag` | 10,000 | 100,000 | Consumer backlog count |
| `ConsumerLagLatencyPerGid` | 30,000 | 300,000 | Consume latency ms (30s / 5min) |
| `ReadyMessageQueueTime` | 30,000 | 300,000 | Ready message queue time ms |
| `SendDLQMessageCountPerGid` | 1 | 50 | DLQ messages per minute (anything >0 noteworthy) |
| `ThrottledReceiveRequestsPerGid` | 1 | 100 | Group receive throttles per minute |

Display-only: `ReadyMessages`, `ReceiveMessageCountPerGid`.

### Topic dimension

| Metric | warn | critical | Note |
|--------|------|----------|------|
| `ThrottledSendRequestsPerTopic` | 1 | 100 | Topic send throttles per minute |

Display-only: `SendMessageCountPerTopic`, `ReceiveMessageCountPerTopic`.

### Resource quotas (not from CMS; counted via management APIs)

Per official limits documentation: [4.x limits](https://help.aliyun.com/zh/apsaramq-for-rocketmq/cloud-message-queue-rocketmq-4-x-series/product-overview/limits) / [5.x limits](https://help.aliyun.com/zh/apsaramq-for-rocketmq/cloud-message-queue-rocketmq-5-x-series/product-overview/usage-limits)

| Quota item | 4.x limit | 5.x limit | warn% | critical% |
|------------|-----------|-----------|-------|-----------|
| Group count | 1,000 | 5,000 | 80% | 95% |
| Topic count | no explicit cap | 5,000 | 80% | 95% |

Quota evaluation is percentage-based: `current / limit`; exceeding `warn_pct` deducts 5, `critical_pct` deducts 15. For 4.x the topic count's limit is `null` (only displayed, not scored).

Data sources:
- 4.x: `aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} ons ons-group-list` / `ons-topic-list`
- 5.x: `aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} rocketmq list-consumer-groups` / `list-topics`

### Region quota (per-region total instance count)

Per AliCloud docs, each region allows at most **1,000** RocketMQ instances (4.x + 5.x combined). The inspector aggregates the count by region.

| Quota item | warn% | critical% |
|------------|-------|-----------|
| Region instance count | 80% | 95% |

### Consumer runtime (per group, 5.x inflight only)

5.x docs say each consumer group's **in-processing** message count must be ≤ 2,500. Sourced from `get-consumer-group-lag.totalLag.inflightCount`.

| Metric | warn | critical |
|--------|------|----------|
| `inflight_count` | 2,000 | 2,400 |

## Health score algorithm

Each instance starts at **100**:
- Each **warn** match → deduct **5** points
- Each **critical** match → deduct **15** points
- Floored at 0 (cannot go negative)

Across dimensions the deductions accumulate. Example: an instance with 3 critical groups and 2 warn topics deducts `3*15 + 2*5 = 55` points → final score 45.

### Tiers

| Score | Status |
|-------|--------|
| ≥ 80 | Healthy |
| 60 – 79 | Watch |
| < 60 | Critical |

## Special handling

- **5.0-only metrics on 4.x instances return empty datapoints** → displayed as N/A, not scored.
- **Instances with no groups / topics** → that dimension is skipped, instance-dimension score not affected.
- **Metric fetch failed (API error)** → marked `ERR`, listed in the report's "Failed metric fetches" section, not scored but flagged for manual review.

> Conservative biases: throttling / drop-packet / DLQ thresholds trip on a single occurrence because well-behaved business traffic should not produce them. If your workload tolerates occasional throttling, raise the `warn` value to 10–50.
