# Monitoring and Alerting Scenarios

Covers Lindorm monitoring data queries, metric descriptions, and alert configuration.

## Trigger Conditions

- "What is the CPU utilization?"
- "CPU trend in the last 3 hours"
- "How do I configure alerts?"
- "Storage is almost full. Can automatic notifications be configured?"

---

## Query Monitoring Data

### Query Latest Data

```bash
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name <metric-name> \
    --dimensions '[{"instanceId":"<instance-id>"}]'
```

**Return value description**:
- `Datapoints` is a JSON **string**, not an array, and requires secondary parsing.
- Each data point contains `instanceId`, `host`, which is the node name such as table-1/search-1/zk-1, `userId`, `timestamp`, and `Average`/`Maximum`/`Minimum`.
- One instance returns **multiple data points**, one for each node. Aggregation or host filtering is required.

### Query Historical Trend

```bash
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name <metric-name> \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<start-time>" \
    --end-time "<end-time>" \
    --period <period>
```

**Return value description**:
- `Datapoints` is also a JSON string and requires secondary parsing.
- After aggregation by period, there is no `host` dimension, and the returned value is instance-level aggregation.
- Each data point contains `timestamp` and `Average`/`Maximum`/`Minimum`.

**Parameters**:
- `--namespace`: Fixed value `acs_lindorm`.
- `--metric-name`: See the metric categories below. Some metrics have no data for V2 instances or require conversion.
- `--dimensions`: JSON array format. `instanceId` must be specified.
- `--start-time` / `--end-time`: For the time format, see SKILL.md → "Time format".

**Recommended period**:

| Time Range | period | Description |
|---------|--------|------|
| ≤ 1 hour | 60 | 1-minute granularity |
| ≤ 24 hours | 300 | 5-minute granularity |
| > 24 hours | 3600 | 1-hour granularity |

**Relative time handling**: When the user says "last 3 hours", first run `date "+%Y-%m-%d %H:%M:%S"` to get the current time, and then calculate start and end. Default time range: last 1 hour.

**Data retention**: CloudMonitor retains data for up to 30 days. Longer periods require Log Service storage.

---

## Metric Descriptions

> Use **metrics without prefixes** consistently, such as `cpu_idle`, for best compatibility. Metrics with the `lindorm_multi_` prefix are only available for `lindorm_multizone` instances and are unavailable for other instance types.

### CPU Metrics

| Metric | Description | Unit | Normal Range | Alert Threshold |
|------|------|------|---------|---------|
| `cpu_idle` | CPU idle rate | % | > 20% | < 20% |
| `cpu_user` | CPU user utilization | % | < 80% | > 80% |
| `cpu_system` | CPU system utilization | % | < 30% | > 30% |
| `cpu_wio` | CPU I/O wait | % | < 30% | > 30% |

CPU idle rate < 20% indicates a CPU bottleneck. `cpu_wio > 30%` indicates a disk I/O bottleneck.

> **Combined CPU and Load judgment**: Load greater than CPU cores means processing is queued and the instance is in a sub-healthy state. CPU utilization not high but Load high usually indicates excessive disk utilization, and should be judged together with `cpu_wio`.

### Memory Metrics

| Metric | Description | Unit | V1 | V2 |
|------|------|------|----|----|
| `mem_used_percent` | Memory usage percentage | % | ✅ | ⚠️ No data |
| `mem_total` | Total memory | bytes | ✅ | ✅ |
| `mem_free` | Free memory | bytes | ✅ | ✅ |
| `mem_buff_cache` | Cache size | bytes | ✅ | ✅ |

For V2, calculate memory usage by using `1 - mem_free / mem_total`.

> **Java memory characteristics**: Lindorm and HBase are both Java implementations. 70% to 85% memory usage is usually healthy because of JVM BlockCache, MemStore, and HDFS page cache. Attention is usually required only when usage exceeds 92%. It is not recommended to set an alert at 80%.
>
> **Wide table engine heap memory alert**: It is recommended to alert when the memory usage ratio of wide table compute nodes is ≥ 85% to 90% and lasts for 30 to 60 minutes. Short-term heap memory fluctuation is normal because GC reclaims memory. Only sustained high usage needs attention.

### QPS Metrics

| Metric | Description | Unit |
|------|------|------|
| `read_ops` | Read request volume | ops/s |
| `write_ops` | Write request volume | ops/s |
| `get_num_ops` | Get requests per second | ops/s |
| `put_num_ops` | Put requests per second | ops/s |
| `scan_num_ops` | Scan requests per second | ops/s |

> **QPS metric interpretation**:
> - BatchGet is counted as one point-query call regardless of how many rows it contains. Therefore, avg RT is higher than that of single-row Get when BatchGet is used.
> - Scan requests are split into sub-calls for streaming return. Scan QPS is not equal to the actual number of Scan requests, and Scan RT is the average latency of each sub-call.

### Latency Metrics

| Metric | Description | Unit | Normal Range | Alert Threshold | V2 |
|------|------|------|---------|---------|-----|
| `read_rt` | Average read latency | ms | < 10ms | > 50ms | ✅ |
| `write_rt` | Average write latency | ms | < 10ms | > 50ms | ✅ |
| `get_rt_avg` | Average Get latency | ms | < 10ms | > 50ms | ✅ |
| `put_rt_avg` | Average Put latency | ms | < 10ms | > 50ms | ✅ |
| `get_rt_p99` | Get P99 latency | ms | < 50ms | > 100ms | ⚠️ No data |
| `put_rt_p99` | Put P99 latency | ms | < 50ms | > 100ms | ⚠️ No data |
| `scan_rt_avg` | Average Scan latency | ms | < 50ms | > 200ms | ✅ |
| `scan_rt_p99` | Scan P99 latency | ms | < 200ms | > 500ms | ✅ |

### Storage Metrics

| Metric | Description | Unit | Alert Threshold | V2 |
|------|------|------|---------|-----|
| `hot_storage_used_percent` | Hot storage usage percentage | % | > 80% | ⚠️ No data |
| `hot_storage_used_bytes` | Hot storage usage | bytes | — | ✅ |
| `cold_storage_used_percent` | Cold storage usage percentage | % | > 80% | ⚠️ No data |
| `cold_storage_used_bytes` | Cold storage usage | bytes | — | ✅ |
| `storage_used_percent` | Total storage usage percentage | % | > 80% | ⚠️ No data |
| `storage_used_bytes` | Total storage usage | bytes | — | ✅ |

For V2, storage usage percentage must be obtained through the `get-lindorm-v2-storage-usage` API. CloudMonitor has no data.

> ⚠️ **Storage hard limit**: When the hot storage or cold storage watermark is ≥ 95%, the system automatically prohibits data writes. It is recommended to set capacity alert thresholds at 75% to 80% and scale out in advance to avoid business impact.

### Network and Load Metrics

| Metric | Description | Unit |
|------|------|------|
| `bytes_in` | Network inbound traffic | bytes/s |
| `bytes_out` | Network outbound traffic | bytes/s |
| `load_one` | 1-minute average load | — |
| `load_five` | 5-minute average load | — |
| `handler_queue_size` | Handler queue length | — |
| `compaction_queue_size` | Compaction queue length | — |

> **Compaction queue judgment**: A long-term stable value is healthy. It is normal for backlog to appear during daytime peaks and be automatically processed at night during low traffic. Continuous increase with no downward trend indicates insufficient resources and requires scale-out. Long-term backlog increases the number of files and read RT. In severe cases, write backpressure increases write RT or causes timeouts.

> **Network/disk throttling**: Different instance specifications have different network bandwidth and disk IOPS limits. See [instance specification families](https://help.aliyun.com/zh/lindorm/product-overview/instance-types) and [block storage performance](https://help.aliyun.com/zh/block-storage/product-overview/block-storage-performance). Read/write traffic exceeding the cloud disk bandwidth limit causes throttling and business impact.

### Engine-specific Metrics

| Engine | Metric Prefix | Key Metrics |
|------|---------|---------|
| LSQL, wide table SQL | `lql_` | `lql_select_ops`, `lql_upsert_ops`, `lql_select_avg_rt`, `lql_select_p99_rt`, `lql_connection` |
| Search engine | `search_` | `search_cpu_idle`, `search_mem_used_percent`, `search_select_1minRate`, `search_select_p99_rt` |
| Time series engine | `tsdb_` | `tsdb_datapoints_added`, `tsdb_disk_used`, `tsdb_jvm_used_percent` |
| File engine | `Lindorm_File_` | `Lindorm_File_ReadBandwidth`, `Lindorm_File_WriteBandwidth`, `Lindorm_File_ReadLatency`, `Lindorm_File_WriteLatency` |

Engine-specific metrics return data only when the corresponding engine is enabled. You can query the complete 323 metrics by running `aliyun cms describe-metric-meta-list --namespace acs_lindorm`.

### Business Terms to Metrics Mapping

| User Says | Metric |
|--------|------|
| CPU utilization | `cpu_idle`, idle rate. Utilization = 100 - cpu_idle. |
| Memory utilization | `mem_used_percent`, V1 / `1 - mem_free / mem_total`, V2 |
| QPS | `read_ops` + `write_ops` |
| Latency / RT | `read_rt` or `write_rt` |
| P99 latency | `get_rt_p99` / `put_rt_p99`, V1 / —, no data for V2 |
| Storage usage percentage | `hot_storage_used_percent`, V1 / `get-lindorm-v2-storage-usage` API, V2 |
| Network traffic | `bytes_in` + `bytes_out` |
| Load | `load_one` |

---

## Wide Table Engine Metric Interpretation

### Region Count Recommendation

Each Region consumes metadata memory. Too many Regions may cause insufficient memory.

| Machine Memory | Recommended Regions per Machine |
|---------|-------------------|
| 8 GB | < 500 |
| 16 GB | < 1000 |
| 32 GB | < 2000 |
| 64 GB | < 3000 |
| 128 GB | < 5000 |

You can determine whether memory is insufficient by checking wide table compute node memory usage / total memory. Methods to reduce the number of Regions: reduce the number of tables and reduce the number of pre-splits during table creation.

### Other Wide Table Metric Interpretation

| Metric | Meaning | Judgment |
|------|------|------|
| HandlerQueue length | Number of queued requests | > 0 means requests are queued and server resources cannot handle the current request volume. Upgrade the configuration to add CPU. |
| Compaction queue length | Number of queued Compaction tasks | A long-term stable value is healthy. Continuous increase means insufficient resources and scale-out is required. Long-term backlog increases file count and read RT. In severe cases, write backpressure increases write RT or causes timeouts. |
| Average file count per Region | Average number of files in a shard | More files mean higher read RT. Too many total files may cause Full GC or OOM. |
| Maximum file count per Region | Maximum number of files in a single Region | Exceeding the limit causes write backpressure and write timeout. For specific limits, see [data request limits](https://help.aliyun.com/zh/lindorm/product-overview/quotas-and-limits#p-fq0-foz-ocy). |
| Write traffic, KB/s | Traffic written to the wide table engine | Columns are converted to KeyValue form, so actual write volume is greater than business write volume. Excessive write throughput may cause Compaction backlog. |

### Write Throughput Recommendation

Excessive write throughput may cause Compaction backlog and affect instance stability.

| Configuration | Recommended Write Throughput |
|------|-------------|
| 4C8G | < 5 MB/s |
| 8C16G | < 10 MB/s |
| 16C32G | < 30 MB/s |
| 32C64G | < 60 MB/s |

In actual use, judge together with `compaction_queue_size` and the average file count per Region.

---

## Alert Configuration

**⚠️ Safety boundary: The Agent only queries data and provides suggestions. It does not directly create alert rules** because this involves sensitive information such as contact phone numbers and email addresses and requires verification.

### Alert Rule Types

| Type | Description | Example |
|------|------|------|
| **Threshold alert** | Triggered when metric values cross thresholds | CPU utilization > 80% for 5 minutes |
| **Event alert** | Triggered by system events | NodeDown, RegionError |

Event alerts cannot be captured by metric thresholds and are a key O&M capability.

### Configuration Path

1. **Lindorm console**: Instance details → Alert Management → Create Alert Rule.
2. **CloudMonitor console**: Alert Service → Alert Rules → Create Alert Rule → Select product "Lindorm".

### Key Alert Rule Parameters

| Parameter | Description | Optional Values |
|------|------|--------|
| Statistical period | Data aggregation granularity | 60s / 300s / 900s / 1800s / 3600s / 86400s |
| Statistical method | Data aggregation method | Average / Maximum / Minimum / Sum |
| Comparison operator | Threshold comparison method | >= / > / <= / < / != |
| Consecutive count | Number of consecutive times the condition is met | 1 to 100, recommended 1 to 3 |
| Silence period | Notification silence time after triggering | 5min to 24h |
| Alert level | Three independent thresholds | Critical / Warn / Info |

> **cpu_idle alert direction**: `cpu_idle` is the idle rate. The alert condition should be set to `cpu_idle ≤ threshold`, meaning utilization ≥ 100 - threshold.

### Recommended Thresholds

| Metric | V1 | V2 | Info | Warn | Critical |
|------|----|----|-------------|-------------|----------------|
| CPU utilization | `cpu_idle ≤ 30` | `cpu_idle ≤ 30` | ≤ 30% for 30min | ≤ 20% for 5min | ≤ 5% for 3min |
| Memory utilization | `mem_used_percent` | `1 - mem_free/mem_total` | ≥ 85% for 30min | ≥ 92% for 5min | — |
| Hot storage usage percentage | `hot_storage_used_percent` | `get-lindorm-v2-storage-usage` API | ≥ 70% | ≥ 80% | ≥ 90% |
| P99 latency | `get_rt_p99` | —, no data | ≥ 50ms | ≥ 100ms | ≥ 200ms |

> V2 storage alerts: CloudMonitor has no `hot_storage_used_percent` / `storage_used_percent` data. You must obtain it through the `get-lindorm-v2-storage-usage` API, or configure storage-space-based alert rules in the console.

### Notification Channels

| Channel | Description | Applicable Level |
|------|------|---------|
| SMS | Phone number must be verified | Warn / Critical |
| Email | Email address must be verified | Info / Warn / Critical |
| DingTalk | Group robot Webhook | Warn / Critical |
| Phone call | Voice alert | Critical |
| Webhook | Custom HTTP callback | All levels |
| Alibaba Cloud App | In-app push | Info / Warn / Critical |

Contact management path: CloudMonitor console → Notification Management → Contacts / Contact Groups.

### Common Alert Issues

- **No notification received**: Check whether contacts are verified, whether alert conditions are actually triggered, whether the notification period covers the event time, and whether the notification policy is associated with the rule.
- **Too many alerts**: Increase thresholds, extend duration, configure a silence period from 5 minutes to 24 hours, or use composite conditions, where multiple metrics must be met simultaneously before alerting.

---

## Error Handling

| Error | Cause | Guidance |
|------|------|------|
| No data points | The instance was not running or had no traffic in the time range | Adjust the time range or check instance status |
| Insufficient permissions | AK has no CloudMonitor permission | `AliyunCloudMonitorReadOnlyAccess` is required |
| Metric does not exist | Metric name is incorrect or the instance type does not support it | Verify metric availability first |

---

## Official Documentation

- Alert configuration: https://help.aliyun.com/zh/lindorm/user-guide/manage-alerts
- Create an alert rule: https://help.aliyun.com/zh/lindorm/user-guide/create-an-alert-rule
- Monitoring metric description: https://help.aliyun.com/zh/lindorm/user-guide/instance-monitoring
- Monitoring and alerting best practices: https://help.aliyun.com/zh/lindorm/user-guide/monitoring-alarm-best-practices

---

## Related Scenarios

- Troubleshoot specific slow SQL after performance diagnosis → `slow-query-analysis.md`
- Storage analysis → `storage-analysis.md`
- Scaling → `instance-management.md`