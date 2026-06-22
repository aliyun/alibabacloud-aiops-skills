# Kafka v3 Instance Specification, Elastic Strategy, and Capacity Policy

## 1. Instance Series Identification

v3 series instances are **Serverless** instances and include the following editions:

| Edition | Instance Type | Deployment Architecture | SLA | Recommended Use Case | Identification Logic |
|:---|:---|:---|:---|:---|:---|
| Serverless Basic | Shared instance | Single availability zone | 99.9% | Testing / stable-traffic workloads | `Series` field returned by `GetInstanceList` equals `v3` and `SpecType` field equals `basic` |
| Serverless Standard | Dedicated instance | Single availability zone | 99.95% | Standard production environments | `Series` field returned by `GetInstanceList` equals `v3` and `SpecType` field equals `normal` |
| Serverless Professional | Dedicated instance | **3-AZ multi-availability zone** | 99.99% | High-availability / mission-critical enterprise workloads | `Series` field returned by `GetInstanceList` equals `v3` and `SpecType` field equals `professional` |

> Key capacity parameters are `ReservedPublishCapacity` (reserved produce capacity) and `ReservedSubscribeCapacity` (reserved consume capacity), both in MB/s.
> **Important notes:**
> 1. The `ReservedPublishCapacity` value represents the **cluster-level inbound throughput**, which includes replica replication traffic. To obtain the actual business inbound throughput, divide by the replica factor (default: 3). Unless otherwise noted, "reserved produce capacity" throughout this document refers to the **cluster-level inbound throughput**.
> 2. `ReservedSubscribeCapacity` does not have this relationship — the value returned by CloudMonitor already represents the actual business outbound throughput.

---

## 2. Reserved Capacity and Elastic Ceiling Strategy (Key Differentiator)

> v3 Standard and Professional instances include an elastic ceiling policy. After purchase, the instance has both a "reserved capacity" and an "elastic ceiling" for network throughput.

### 2.1 Basic Edition

**Does not support elastic scaling.** Users must manually scale the **reserved capacity** up or down.

- Reserved produce capacity: 300–51,300 MB/s; each adjustment must be a multiple of 300 MB/s
- Reserved consume capacity: 100–17,100 MB/s; each adjustment must be a multiple of 100 MB/s
- Purchasable consume-to-produce capacity ratio: Reserved consume / Reserved produce ≤ 1:1

### 2.2 Standard Edition

- Reserved produce capacity: 60–51,300 MB/s; each adjustment must be a multiple of 30 MB/s
- Reserved consume capacity: 20–17,100 MB/s; each adjustment must be a multiple of 10 MB/s
- Purchasable consume-to-produce capacity ratio: Reserved consume / Reserved produce ≤ 3:1

Elastic ceiling is calculated as a multiple of the reserved capacity:

| Reserved Capacity Range | Elastic Ceiling Formula |
|:---|:---|
| (0, 512] MB/s | Reserved capacity × 2 |
| (512, 5,120] MB/s | Reserved capacity × 2 |
| (5,120, 10,240] MB/s | Reserved capacity × 1.5 |
| > 10,240 MB/s | Reserved capacity × 1.2 |

### 2.3 Professional Edition

- Reserved produce capacity: 60–51,300 MB/s; each adjustment must be a multiple of 30 MB/s
- Reserved consume capacity: 20–17,100 MB/s; each adjustment must be a multiple of 10 MB/s
- Purchasable consume-to-produce capacity ratio: Reserved consume / Reserved produce ≤ 3:1

Elastic ceiling is calculated as a multiple of the reserved capacity. Smaller reserved capacity tiers enjoy a higher elastic multiplier:

| Reserved Capacity Range | Elastic Ceiling Formula |
|:---|:---|
| (0, 512] MB/s | **Fixed at 1 GB/s (1,024 MB/s)** |
| (512, 5,120] MB/s | Reserved capacity × 2 |
| (5,120, 10,240] MB/s | Reserved capacity × 1.5 |
| > 10,240 MB/s | Reserved capacity × 1.2 |

### 2.4 Scaling Considerations

- **Connection impact**: Scaling operations change the node count. Clients will briefly disconnect and reconnect, potentially causing a small number of errors. It is recommended to configure retry logic to re-send any messages that fail during the scaling window.

### 2.5 Throttling Determination

| Scenario | Determination |
|:---|:---|
| Traffic within reserved capacity | Normal billing; no throttling |
| Traffic exceeds reserved capacity but is within elastic ceiling | Elastic overage charges apply; **no throttling** |
| Traffic exceeds elastic ceiling | **Throttling occurs**; upgrade is required |

---

## 3. Partition Allocation Strategy and Limits

> Partition allocation limits are the same across all v3 editions (Basic, Standard, and Professional).

- When reserved produce capacity ≤ 1 GB/s: cluster has 3,000 partition replicas
- When reserved produce capacity > 1 GB/s: every additional 100 MB/s adds 300 partition replicas to the cluster
- Maximum partition replicas per topic: 600
- Maximum cluster partition replicas: 30,000

---

## 4. Capacity Limits and Calculation Formulas

> **Key prerequisite**: v3 (Serverless) instances are deployed with 3 nodes by default. Because the node count is not fixed, use "utilization ratio" type metrics to determine whether a limit is being approached. Network throughput may be assessed using the aggregate value across all nodes. Actual business throughput = nominal throughput / 3.
> However, v3 instances have an elastic mechanism; it is necessary to distinguish between "reserved capacity" and "elastic ceiling."

### 4.1 Network Throughput Limit

- Reserved capacity = `ReservedPublishCapacity` (produce) / `ReservedSubscribeCapacity` (consume)
- Elastic ceiling = calculated from reserved capacity and instance edition (Basic / Standard / Professional) according to the elastic strategy in Section 2
- Actual business throughput limit = elastic ceiling / 3 (per-node dimension)

### 4.2 Connection Count Limit (Per Node)

In the formulas below, `F` = reserved capacity (MB/s), `//` = integer division (floor).

| Connection Type | Formula | Maximum |
|:---|:---|:---|
| TCP connections per node (public + private network) | `C = min(10000, 2000 + (F // 300) * 1000)` | 10,000 |
| Public network (SSL) connections per node | `C = min(1000, 200 + (F // 300) * 100)` | 1,000 |
| Connection establishment rate | 150 connections/sec | — |
| Public network connection establishment rate | 10 connections/sec | — |

### 4.3 Request Rate Limit

| Request Type | Basic Edition Formula | Standard / Professional Edition Formula |
|:---|:---|:---|
| PRODUCE request rate | `R = 10000 + (F // 300) * 5000` | `R = 10000 + (F // 60) * 2000` |
| FETCH request rate | `R = 5000 + (F // 100) * 2500` | `R = 5000 + (F // 20) * 1000` |
| OFFSET_COMMIT request rate | `R = min(1000, 100 + (F // 100) * 100)` | Same as Basic |
| Metadata request rate | `R = min(1000, 100 + (F // 100) * 100)` | Same as Basic |

### 4.4 Other Limits

| Limit | Value |
|:---|:---|
| Maximum message size | 10 MB |
| Message format version | > V1 (client version ≥ 2.4 recommended) |
| Consumer Groups per cluster | 2,000 |
| Partition creation/deletion rate | 900 partitions per 10 seconds |

---

## 5. Disk Cleanup Policy

**Serverless instances** always delete messages according to the user-configured TTL; no disk-utilization-triggered forced cleanup applies. Disk cleanup policy is not a concern, but watch for abnormally rising disk utilization that may cause messages to expire earlier than expected.

---

## 6. CloudMonitor Metrics (v3 Series Only)

When performing a capacity check, **query only the metrics listed below**. Do not query metrics that do not appear in this table. All v3 metric names end with the suffix `V3`. The Namespace is always `acs_kafka`. When there is no business traffic, a metric may return no data or a value of 0. If either occurs, note in the report that the reliability of that metric's findings is reduced for this analysis cycle.

| MetricName | Description | Bottleneck Criterion |
|:---|:---|:---|
| `InstanceMessageInputRatioV3` | Produce traffic as a percentage of the elastic ceiling | A value in [0%, 100%] means reserved capacity is exceeded (overage charges apply but no throttling); **exceeding 100%** means the elastic ceiling is exceeded and **throttling is occurring** |
| `InstanceMessageInputV3` | Actual business inbound throughput of the instance (B/s) — i.e., message produce volume | Represents the **actual business inbound throughput** |
| `ClusterMessageInputV3` | Cluster-level inbound throughput (including replica replication traffic) (B/s) | Exceeds the `ReservedPublishCapacity` field returned by `GetInstanceList` means inbound traffic has exceeded the reserved limit |
| `InstanceMessageOutputRatioV3` | Consume traffic as a percentage of the elastic ceiling | Same as `InstanceMessageInputRatioV3` |
| `InstanceMessageOutputV3` | Actual business outbound throughput of the instance (B/s) — i.e., message consume volume | Represents the **actual business outbound throughput** |
| `InstanceMaxConnectionRatioV3` | Connection utilization per node (public + private network) | Approaching 100% means connections are nearing the limit |
| `InstanceMaxInternetConnectionRatioV3` | Connection utilization per node (public network only) | Approaching 100% means public-network connections are nearing the limit |
| `InstanceThrottleTimeP99InputV3` | P99 produce throttle duration | **Greater than 0** means active produce throttling is occurring; upgrade is recommended |
| `InstanceThrottleTimeP99OutputV3` | P99 consume throttle duration | **Greater than 0** means active consume throttling is occurring; upgrade is recommended |

### Dimensions Query Format

```json
[{"instanceId": "alikafka_serverless_cn-xxxxx"}]
```

---

## 7. Capacity Bottleneck Troubleshooting Guide

Based on the symptoms reported by the user, infer the likely metric approaching its limit:

| Symptom | Probable Bottleneck Metric | Investigation Method |
|:---|:---|:---|
| Message backlog (v3) | Elastic ceiling / throttling | Query `InstanceMessageInputRatioV3` and `InstanceThrottleTimeP99InputV3`; Ratio > 100% or ThrottleTime > 0 indicates throttling |
| Reduced producer send throughput (v3) | Produce traffic exceeds elastic ceiling | Query whether `InstanceMessageInputRatioV3` > 100% or `InstanceThrottleTimeP99InputV3` > 0 |
| Reduced consumer consumption rate (v3) | Consume traffic exceeds elastic ceiling | Query whether `InstanceMessageOutputRatioV3` > 100% or `InstanceThrottleTimeP99OutputV3` > 0 |
| Clients unable to connect (v3) | Connection count at limit | Query whether `InstanceMaxConnectionRatioV3` and `InstanceMaxInternetConnectionRatioV3` are approaching 100% |
| Unexpectedly high elastic overage charges (v3) | Traffic exceeds reserved capacity but is within elastic ceiling | Query `InstanceMessageInputRatioV3` and `InstanceMessageOutputRatioV3`; any value > 0% means elastic overage charges are being incurred |

> To determine whether instance traffic is exceeding its limit, query both the "elastic ceiling ratio" metric (`InstanceMessageInputRatioV3` or `InstanceMessageOutputRatioV3`) and the "throttle duration" metric (`InstanceThrottleTimeP99InputV3` or `InstanceThrottleTimeP99OutputV3`). If either metric exceeds its threshold, the instance has reached a capacity bottleneck.

### v3 Instance Upgrade Recommendation Logic

1. If `InstanceMessageInputRatioV3` > 100% or `InstanceThrottleTimeP99InputV3` > 0:
   - Recommend increasing `ReservedPublishCapacity` (reserved produce capacity)
2. If `InstanceMessageOutputRatioV3` > 100% or `InstanceThrottleTimeP99OutputV3` > 0:
   - Recommend increasing `ReservedSubscribeCapacity` (reserved consume capacity)
3. If connection utilization is approaching 100%:
   - Recommend increasing reserved capacity (the connection count limit scales with reserved capacity)
4. For Basic Edition instances experiencing throttling: recommend increasing reserved capacity, or upgrading to Standard / Professional Edition to gain elastic scaling capability
