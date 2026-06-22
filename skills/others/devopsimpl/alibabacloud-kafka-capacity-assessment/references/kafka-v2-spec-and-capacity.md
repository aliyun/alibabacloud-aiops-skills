# Kafka v2 Instance Specification and Capacity Policy

## 1. Instance Edition Identification

| Edition | Deployment Model | Description | Identification Logic |
|:---|:---|:---|:---|
| Standard Edition (High-Write) | Shared instance (logical isolation) | Does not support TopicTTL, ACL, SSL, cross-AZ deployment, or performance tuning | `Series` field returned by `GetInstanceList` API equals `v2` and `SpecType` field equals `normal` |
| Professional Edition (High-Write) | Dedicated instance (exclusive physical cluster) | Supports all advanced features; supports multi-AZ deployment | `Series` field returned by `GetInstanceList` API equals `v2` and `SpecType` field equals `professional` |
| Professional Edition (High-Read) | Dedicated instance | Peak read-to-write ratio of 3:1; optimized for read-heavy workloads | `Series` field returned by `GetInstanceList` API equals `v2` and `SpecType` field equals `professionalForHighRead` |

---

## 2. Instance Specifications and Partition Limits

> "Partition count" in the tables below refers to the number of Kafka partitions in the instance.
> Retrieve the instance specification via the `IoMaxSpec` field returned by the `GetInstanceList` API.

### Standard Edition (High-Write)

| Throughput Specification | Included Partitions | Maximum Partitions |
|:---|:---|:---|
| `alikafka.hw.2xlarge` | 1,000 | 4,000 |
| `alikafka.hw.3xlarge` | 1,000 | 4,200 |
| `alikafka.hw.6xlarge` | 1,000 | 4,400 |
| `alikafka.hw.9xlarge` | 1,000 | 4,600 |
| `alikafka.hw.12xlarge` | 1,000 | 4,800 |

### Professional Edition (High-Write)

| Throughput Specification | Included Partitions | Maximum Partitions |
|:---|:---|:---|
| `alikafka.hw.2xlarge` | 1,000 | 4,000 |
| `alikafka.hw.3xlarge` | 1,000 | 4,200 |
| `alikafka.hw.6xlarge` | 1,000 | 4,400 |
| `alikafka.hw.9xlarge` | 1,000 | 4,600 |
| `alikafka.hw.12xlarge` | 1,000 | 4,800 |
| `alikafka.hw.16xlarge` | 2,000 | 5,000 |
| `alikafka.hw.20xlarge` | 2,000 | 6,000 |
| `alikafka.hw.25xlarge` | 2,000 | 7,000 |
| `alikafka.hw.30xlarge` | 2,000 | 8,000 |
| `alikafka.hw.60xlarge` | 2,000 | 9,000 |
| `alikafka.hw.80xlarge` | 2,000 | 10,000 |
| `alikafka.hw.100xlarge` | 3,000 | 12,000 |
| `alikafka.hw.120xlarge` | 3,000 | 14,000 |
| `alikafka.hw.150xlarge` | 3,000 | 16,000 |
| `alikafka.hw.180xlarge` | 3,000 | 18,000 |
| `alikafka.hw.200xlarge` | 3,000 | 20,000 |
| `alikafka.hw2.220xlarge` | 4,000 | 24,000 |
| `alikafka.hw2.300xlarge` | 4,000 | 26,000 |
| `alikafka.hw2.400xlarge` | 4,000 | 28,000 |
| `alikafka.hw2.500xlarge` | 4,000 | 30,000 |
| `alikafka.hw2.600xlarge` | 5,000 | 32,000 |
| `alikafka.hw2.700xlarge` | 5,000 | 34,000 |
| `alikafka.hw2.800xlarge` | 5,000 | 36,000 |
| `alikafka.hw2.900xlarge` | 5,000 | 38,000 |
| `alikafka.hw2.1000xlarge` | 5,000 | 40,000 |

### Professional Edition (High-Read)

| Throughput Specification | Included Partitions | Maximum Partitions |
|:---|:---|:---|
| `alikafka.hr.2xlarge` | 1,000 | 4,000 |
| `alikafka.hr.3xlarge` | 1,000 | 4,200 |
| `alikafka.hr.6xlarge` | 1,000 | 4,400 |
| `alikafka.hr.9xlarge` | 1,000 | 4,600 |
| `alikafka.hr.12xlarge` | 1,000 | 4,800 |
| `alikafka.hr.16xlarge` | 2,000 | 5,000 |
| `alikafka.hr.20xlarge` | 2,000 | 6,000 |
| `alikafka.hr.25xlarge` | 2,000 | 7,000 |
| `alikafka.hr.30xlarge` | 2,000 | 8,000 |
| `alikafka.hr.60xlarge` | 2,000 | 9,000 |
| `alikafka.hr.80xlarge` | 2,000 | 10,000 |
| `alikafka.hr.100xlarge` | 3,000 | 12,000 |
| `alikafka.hr.120xlarge` | 3,000 | 14,000 |
| `alikafka.hr.150xlarge` | 3,000 | 16,000 |
| `alikafka.hr.180xlarge` | 3,000 | 18,000 |
| `alikafka.hr.200xlarge` | 3,000 | 20,000 |
| `alikafka.hr2.220xlarge` | 4,000 | 24,000 |
| `alikafka.hr2.300xlarge` | 4,000 | 26,000 |
| `alikafka.hr2.400xlarge` | 4,000 | 28,000 |
| `alikafka.hr2.500xlarge` | 4,000 | 30,000 |
| `alikafka.hr2.600xlarge` | 5,000 | 32,000 |
| `alikafka.hr2.700xlarge` | 5,000 | 34,000 |
| `alikafka.hr2.800xlarge` | 5,000 | 36,000 |
| `alikafka.hr2.900xlarge` | 5,000 | 38,000 |
| `alikafka.hr2.1000xlarge` | 5,000 | 40,000 |

---

## 3. Capacity Limits and Calculation Formulas

> Instance capacity dimensions include network throughput, disk space, connection count, Kafka API request rate, consumer group count, and topic count. Each dimension has its own calculation method; refer to the sub-sections below.

### 3.1 Network Throughput Limit

Call the `GetInstanceList` API and inspect the `IoMaxWrite` and `IoMaxRead` fields in the response to determine the instance's **actual business throughput limits**.

### 3.2 Disk Space Limit

Call the `GetInstanceList` API and inspect the `DiskSize` field. Note that the interpretation of this field differs by edition within v2 instances:
- **Standard Edition (High-Write) storage**: `DiskSize` is the total cluster storage. Divide by the number of nodes to get usable capacity per node. For example, if `DiskSize` is 300 GB with the default 3-node deployment, the usable capacity is 300 GB ÷ 3 = 100 GB.
- **Professional Edition storage**: `DiskSize` is the directly usable business capacity. For example, if `DiskSize` is 300 GB, the business has 300 GB of usable storage (an additional 600 GB is provisioned transparently as replica storage).

> Note: the `instance_disk_capacity` metric reflects the actual disk utilization rate.

### 3.3 Connection Count Limit (Per Node)

In the formulas below, `F` = actual business produce throughput (MB/s), `//` = integer division (floor).

| Connection Type | Formula | Maximum |
|:---|:---|:---|
| TCP connections per node (public + private network) | `C = min(10000, 1000 + (F // 100) * 1000)` | 10,000 |
| Public network (SSL) connections per node | `C = min(1000, 200 + (F // 100) * 100)` | 1,000 |

> The `InstanceMaxConnection` metric reports the maximum total connection count per node (public + private); `InstanceMaxInternetConnection` reports the public-network-only connection count per node.

---

## 4. Disk Cleanup Policy

### Cloud Storage Topics

| Disk Utilization | Cleanup Policy |
|:---|:---|
| `< 75%` | Expired messages (beyond retention period) are deleted in a batch at 04:00 AM daily |
| `[75%, 85%)` | Expired messages are deleted periodically until utilization drops below 75% |
| `[85%, 90%)` | **Retention period is ignored**; messages are purged in chronological order of server storage time |
| `≥ 90%` | **Write protection is triggered**; new writes are suspended |

### Local Storage Topics

| Disk Utilization | Cleanup Policy |
|:---|:---|
| `< 83%` | Messages are deleted strictly according to the user-configured TTL |
| `[83%, 88%)` | **Retention period is ignored**; up to 10% of stored messages per partition are purged in chronological order |
| `≥ 88%` | **Write protection is triggered**; new writes are suspended |

> **Recommended healthy utilization threshold**: Keep daily disk utilization below 70%. Since a single Kafka instance can host both Cloud Storage Topics and Local Storage Topics simultaneously, 80% serves as a general warning threshold during routine disk utilization checks.

---

## 5. CloudMonitor Metrics (v2 Series Only)

When performing a capacity check, **query only the metrics listed below**. Do not query metrics that do not appear in this table. Most v2 metric names end with the suffix `V2` (a small number have no suffix). The Namespace is always `acs_kafka`.

| MetricName | Description | Bottleneck Criterion |
|:---|:---|:---|
| `InstanceMessageInputRatioV2` | Produce traffic as a percentage of instance specification limit | Approaching 100% means produce throughput is nearing the specification ceiling |
| `instance_message_input` | Actual business inbound throughput of the instance (B/s) — i.e., message produce volume | Exceeds the `IoMaxWrite` field returned by `GetInstanceList` means inbound traffic has exceeded the limit |
| `InstanceMessageOutputRatioV2` | Consume traffic as a percentage of instance specification limit | Approaching 100% means consume throughput is nearing the specification ceiling |
| `instance_message_output` | Actual business outbound throughput of the instance (B/s) — i.e., message consume volume | Exceeds the `IoMaxRead` field returned by `GetInstanceList` means outbound traffic has exceeded the limit |
| `PartitionInstanceRatioV2` | Partition count as a percentage of instance specification limit | Approaching 100% means partition count is nearing the ceiling |
| `instance_disk_capacity` | Instance disk utilization | **Exceeding 80%** indicates the disk is near capacity; Kafka dynamic cleanup begins |
| `InstanceMaxConnection` | Maximum connections per node (public + private network) | Compare against the connection limit calculated by the formula in Section 3.3 |
| `InstanceMaxInternetConnection` | Maximum connections per node (public network only) | Compare against the public-network connection limit calculated by the formula in Section 3.3 |

### Dimensions Query Format

```json
[{"instanceId": "alikafka_post-cn-xxxxx"}]
```

---

## 6. Capacity Bottleneck Troubleshooting Examples

Based on the symptoms reported by the user, infer the likely metric approaching its limit:

| Symptom | Probable Bottleneck Metric | Investigation Method |
|:---|:---|:---|
| Messages deleted before retention period expires | Disk space | Query `instance_disk_capacity`; check if it is approaching 80% |
| Message backlog | Network throughput | Query `InstanceMessageInputRatioV2` and `InstanceMessageOutputRatioV2` |
| Reduced producer send throughput | Produce traffic | Query `InstanceMessageInputRatioV2` |
| Reduced consumer consumption rate | Consume traffic | Query `InstanceMessageOutputRatioV2` |
| Clients unable to connect to broker | Connection count | Query `InstanceMaxConnection` / `InstanceMaxInternetConnection`; check if approaching the formula-calculated limit |
| Full disk causing write suspension | Disk space | Query `instance_disk_capacity`; check if ≥ 90% (Cloud Storage) or ≥ 88% (Local Storage) |
