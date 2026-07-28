# RocketMQ Metrics Catalogue

All metrics live under a **single CMS namespace `acs_rocketmq`**, shared between 4.x classic and 5.x serverless instances. **Do not use `acs_rocketmq5`** — that namespace is empty and `describe-metric-meta-list` returns `TotalCount: 0`.

Version differences are indicated by the `5.0` prefix in metric descriptions (e.g. `InstanceSendApiCallTps`, `InstanceStorageSize`). 4.x instances querying 5.0-only metrics return empty `Datapoints`; the renderer displays `N/A` and does not penalize the health score.

## 1. Metrics covered by this skill (32 in total)

`inspect.sh` issues a fixed `22 + 7 + 3 = 32` API calls per instance, covering three primary dimensions.

### Instance dimension (22 metrics, `dimensions = userId,instanceId`)

| Section | MetricName | Stat | Unit | 5.x only |
|---------|------------|------|------|----------|
| Traffic & TPS | `InstanceApiCallTps` | Sum | count/s | — |
| Traffic & TPS | `InstanceApiCallTpsMax` | Sum | count/s | — |
| Traffic & TPS | `InstanceTpsUtilization` | Value | % | — |
| Traffic & TPS | `InstanceSendApiCallTps` | Maximum | count/s | ✅ |
| Traffic & TPS | `InstanceSendTpsUtilization` | Value | % | ✅ |
| Traffic & TPS | `InstanceReceiveApiCallTps` | Maximum | count/s | ✅ |
| Traffic & TPS | `InstanceReceiveTpsUtilization` | Value | % | ✅ |
| Traffic & TPS | `SendMessageCountPerInstance` | Sum | count/m | — |
| Traffic & TPS | `ReceiveMessageCountPerInstance` | Sum | count/m | — |
| Clients/connections | `InstanceOnlineClients` | Sum | count | — |
| Clients/connections | `InstanceOnlineClientsUtilization` | Maximum | % | — |
| Clients/connections | `InstanceActiveConnection` | Maximum | count/s | — |
| Throttling | `ThrottledSendRequestsPerInstance` | Sum | count/m | — |
| Throttling | `ThrottledReceiveRequestsPerInstance` | Sum | count/m | — |
| Public bandwidth | `InstanceTrafficRX` | Maximum | bit/s | — |
| Public bandwidth | `InstanceTrafficTX` | Maximum | bit/s | — |
| Public bandwidth | `InstanceTrafficRXUtilization` | Maximum | % | — |
| Public bandwidth | `InstanceTrafficTXUtilization` | Maximum | % | — |
| Public bandwidth | `InstanceDropTrafficRX` | Maximum | bit/s | — |
| Public bandwidth | `InstanceDropTrafficTX` | Maximum | bit/s | — |
| Public bandwidth | `InstanceInternetFlowoutBandwidth` | Sum | B/s | ✅ |
| Storage | `InstanceStorageSize` | Sum | B | ✅ |

### Group dimension (7 metrics, `dimensions = userId,instanceId,groupId`)

| MetricName | Stat | Unit | Meaning |
|------------|------|------|---------|
| `ConsumerLag` | Sum | count | Consumer lag (backlog) |
| `ConsumerLagLatencyPerGid` | Maximum | ms | Consume latency |
| `ReadyMessages` | Sum | count | Ready (queued, not yet delivered) messages |
| `ReadyMessageQueueTime` | Maximum | ms | Ready message queue time |
| `ReceiveMessageCountPerGid` | Sum | count/m | Messages received per minute |
| `SendDLQMessageCountPerGid` | Sum | count/m | DLQ messages per minute |
| `ThrottledReceiveRequestsPerGid` | Sum | count/m | Receive throttling per minute |

### Topic dimension (3 metrics, `dimensions = userId,instanceId,topic`)

| MetricName | Stat | Unit | Meaning |
|------------|------|------|---------|
| `SendMessageCountPerTopic` | Sum | count/m | Producer sends per minute |
| `ReceiveMessageCountPerTopic` | Sum | count/m | Consumer receives per minute |
| `ThrottledSendRequestsPerTopic` | Sum | count/m | Send throttling per minute |

> The renderer automatically **filters out** topics whose name starts with `%RETRY%`, `%DLQ%`, or `%SYS%` (RocketMQ internal topics).

## 2. Metrics NOT used by this skill (17, available on demand)

### Group × Topic fine-grained (4 metrics, `dimensions = userId,instanceId,groupId,topic`)

`ConsumerLagPerGidTopic`, `ReadyMessageQueueTimePerGidTopic`, `ReadyMessagesPerGidTopic`, `SendDLQMessageCountPerGidTopic`

> One group typically subscribes to multiple topics, so fine-grained metrics multiply by `group_count × topic_count` and create report noise. Pull on demand when investigating a specific lag/latency:
> ```bash
> aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} cms describe-metric-list --namespace acs_rocketmq \
>   --metric-name ConsumerLagPerGidTopic --period 60 \
>   --start-time '2026-06-02T07:00:00Z' --end-time '2026-06-02T08:00:00Z' \
>   --dimensions '[{"instanceId":"xxx","groupId":"GID_x","topic":"T_y"}]'
> ```

### Topic+Group reverse-grouped (3 metrics, `dimensions = userId,instanceId,topic,groupId`)

`ConsumerLagLatencyPerGidTopic`, `ReceiveMessageCountPerGidTopic`, `ThrottledReceiveRequestsPerGidTopic`

> Functionally equivalent to the prior group, only `dimensions` ordering differs.

### Cross-cluster migration (10 metrics, `dimensions` includes `sinkInstanceId,taskId`)

`SinkClusterAverageProcessTimePerTask` / `*PerTopic`, `SinkClusterMessagesInPerTask` / `*PerTopic`,
`SourceClusterConsumerLagPerTask` / `*PerTopic`, `SourceClusterConsumerLagLatencyPerTask` / `*PerTopic`,
`SourceClusterMessagesOutPerTask` / `*PerTopic`

> Only populated when using Alibaba Cloud RocketMQ's migration service (source/sink cluster replication). Not relevant to ordinary inspection.

## 3. Discovering metrics yourself

If new metrics are added or this document drifts, run locally:

```bash
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} cms describe-metric-meta-list --namespace acs_rocketmq --page-size 200 \
  | jq -r '.Resources.Resource[] | "\(.Dimensions)\t\(.MetricName)\t\(.Statistics)\t\(.Unit)\t\(.Description)"' \
  | sort
```
