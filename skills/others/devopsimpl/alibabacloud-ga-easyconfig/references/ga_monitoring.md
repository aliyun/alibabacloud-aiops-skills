# CloudMonitor Metrics and Alarms Reference

This document describes how to query GA metrics through Alibaba Cloud CloudMonitor and provides common alarm rule templates.

---

## 1. Common GA Metrics (Namespace: acs_ga)

| Metric | Meaning | Dimensions |
|---|---|---|
| `InboundTraffic` | Inbound traffic (bps) | userId, instanceId |
| `OutboundTraffic` | Outbound traffic (bps) | userId, instanceId |
| `InboundPackets` | Inbound packet rate (pps) | userId, instanceId |
| `OutboundPackets` | Outbound packet rate (pps) | userId, instanceId |
| `ActiveFlowCount` | Active connections | userId, instanceId |
| `NewFlowCount` | New connections | userId, instanceId |
| `DropConnectionCount` | Dropped connections | userId, instanceId |
| `DropPacketCount` | Dropped packets | userId, instanceId |
| `Latency` | Latency (ms) | userId, instanceId, listenerId |
| `UnHealthyServerCount` | Unhealthy endpoints | userId, instanceId, listenerId, endpointGroupId |
| `HealthyServerCount` | Healthy endpoints | userId, instanceId, listenerId, endpointGroupId |

> Verify actual metric names and dimensions in the [CloudMonitor GA documentation](https://help.aliyun.com/zh/cms/support/global-acceleration-monitoring-metrics).

---

## 2. Query Accelerator-Level Traffic

```bash
GA_ID="ga-bp1xxxx"
START_TIME=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

aliyun cms describe-metric-list \
  --biz-region-id cn-hangzhou \
  --namespace acs_ga \
  --metric-name InboundTraffic \
  --dimensions "{\"instanceId\":\"$GA_ID\"}" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 | jq '.Datapoints | fromjson | .[] | {timestamp: .timestamp, Average: .Average, Value: .Value}'
```

---

## 3. Query Listener-Level Latency

```bash
LISTENER_ID="lsr-bp1xxxx"

aliyun cms describe-metric-list \
  --biz-region-id cn-hangzhou \
  --namespace acs_ga \
  --metric-name Latency \
  --dimensions "{\"instanceId\":\"$GA_ID\",\"listenerId\":\"$LISTENER_ID\"}" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 | jq '.Datapoints | fromjson | .[] | {timestamp: .timestamp, Average: .Average}'
```

---

## 4. Query Endpoint Group Health

```bash
EPG_ID="epg-bp1xxxx"

aliyun cms describe-metric-list \
  --biz-region-id cn-hangzhou \
  --namespace acs_ga \
  --metric-name UnHealthyServerCount \
  --dimensions "{\"instanceId\":\"$GA_ID\",\"listenerId\":\"$LISTENER_ID\",\"endpointGroupId\":\"$EPG_ID\"}" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 | jq '.Datapoints | fromjson | .[-1] | {timestamp: .timestamp, Average: .Average}'
```

---

## 5. Common Monitoring Scripts

### Latest inbound traffic

```bash
#!/bin/bash
GA_ID="${1:?Please provide GA accelerator ID}"

aliyun cms describe-metric-last \
  --biz-region-id cn-hangzhou \
  --namespace acs_ga \
  --metric-name InboundTraffic \
  --dimensions "{\"instanceId\":\"$GA_ID\"}" | jq '.Datapoints | fromjson | .[0] | {
    Timestamp: .timestamp,
    InboundTrafficBps: .Average
  }'
```

### Traffic trend in the last hour

```bash
#!/bin/bash
GA_ID="${1:?Please provide GA accelerator ID}"
START_TIME=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

aliyun cms describe-metric-list \
  --biz-region-id cn-hangzhou \
  --namespace acs_ga \
  --metric-name InboundTraffic \
  --dimensions "{\"instanceId\":\"$GA_ID\"}" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 300 | jq '.Datapoints | fromjson | map({time: .timestamp, value: .Average})'
```

---

## 6. Create Alarm Rules

### Traffic drop to zero

```bash
aliyun cms create-metric-rule-template \
  --name "GA-Traffic-Drop" \
  --description "GA inbound traffic drop alarm" \
  --alert-templates RuleName=GA_InboundTraffic_Drop Namespace=acs_ga MetricName=InboundTraffic Statistics=Average ComparisonOperator=LessThanOrEqualToThreshold Threshold=0 EvaluationCount=3 Period=60 ContactGroups.1=ga-ops
```

### Unhealthy endpoint alarm

```bash
aliyun cms put-resource-metric-rule \
  --rule-name "GA-UnhealthyEndpoint" \
  --namespace acs_ga \
  --metric-name UnHealthyServerCount \
  --resources "[{\"instanceId\":\"$GA_ID\",\"listenerId\":\"$LISTENER_ID\",\"endpointGroupId\":\"$EPG_ID\"}]" \
  --statistics Average \
  --comparison-operator GreaterThanThreshold \
  --threshold 0 \
  --evaluation-count 1 \
  --period 60 \
  --contact-groups "ga-ops"
```

---

## 7. List Alarm Rules

```bash
aliyun cms describe-metric-rule-list \
  --namespace acs_ga \
  --page-size 50 | jq '.Alarm[].Name'
```

---

## 8. Skill Integration Notes

After the GA accelerator is created, optionally ask:

```
Question: Do you want to configure basic monitoring alarms for this accelerator?
- Option 1: No (default)
- Option 2: Yes, configure traffic drop alarm
- Option 3: Yes, configure unhealthy endpoint alarm
- Option 4: Yes, configure all basic alarms

If yes:
1. Ask for the alarm contact group (ContactGroup).
2. Call cms CreateMetricRuleTemplate or PutResourceMetricRule.
3. Call DescribeMetricRuleList to verify rule creation.
```

---

## 9. Notes

1. Permissions required: `cms:DescribeMetricList`, `cms:PutResourceMetricRule`, etc.
2. CloudMonitor data typically has 1–3 minutes latency and is not suitable for real-time failure detection.
3. Verify the actual namespace (`acs_ga` or others) in the official documentation.
4. Configure alarm silence periods to avoid alert storms caused by jitter.
