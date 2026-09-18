# Storage Analysis Scenarios

Follow this guide when users care about Lindorm instance storage usage, hot/cold data distribution, or storage growth trends.

## Trigger Conditions

Typical user expressions:
- "How much disk space is left?"
- "Is storage almost full?"
- "How much hot storage and cold storage are used respectively?"
- "What is the storage growth trend?"
- "How much storage does ld-xxx use?"
- "What is the hot storage usage percentage?"

## Core Capabilities

- **Storage detail query**: total capacity, used capacity, and hot/cold distribution
- **Storage usage monitoring**: hot storage and cold storage usage trends
- **Storage growth analysis**: historical trend and growth rate
- **Hot/cold tiering suggestions**: when to enable cold storage and hot/cold data migration strategy

## Execution Flow

### Step 0: Determine the Instance Architecture

For a known instance ID, always query instance details before choosing the storage API:

```bash
aliyun lindorm v1 instance describe <instance-id> --lindorm-region <region> --output json
```

The underlying `GetLindormInstance` action is shared by V1 and V2, so this command is the architecture probe for both. Read `service_type` or `arch_version`, then choose `v1 instance storage` or `v2 instance storage`. Do not guess the architecture from the instance ID or storage fields.

### Flow 1: Obtain Storage Details, Snapshot Data

**Applicable scenario**: The user wants to quickly understand current storage usage.

**Execution commands**:

```bash
# V1 instance
aliyun lindorm v1 instance storage <instance-id> --lindorm-region <region>

# V2 instance, instanceType=lindorm_v2
aliyun lindorm v2 instance storage <instance-id> --lindorm-region <region>
```

**Output presentation**:

Give a conclusion summary first:
- Total capacity, hot + cold
- Used capacity, hot + cold
- Usage percentage
- Hot/cold distribution ratio
- Alert status, whether close to threshold

Then expand detailed fields as needed.

**Key field descriptions**:

**V1 instance**, `v1 instance storage`, backed by GetLindormFsUsedDetail:

| Field | Meaning | Unit |
|------|------|------|
| `fs_capacity` | Total file-engine capacity | bytes |
| `fs_capacity_hot` | Hot storage capacity | bytes |
| `fs_capacity_cold` | Cold storage capacity | bytes |
| `fs_used_hot` | Used hot storage | bytes |
| `fs_used_cold` | Used cold storage | bytes |
| `used_on_lindorm_table` | Storage used by the Lindorm wide table engine | bytes |
| `used_on_lindorm_table_data` | Wide table data size | bytes |
| `used_on_lindorm_table_wal` | WAL size | bytes |

**V1 formulas**:

- **Total capacity** = `fs_capacity_hot` + `fs_capacity_cold`
- **Used capacity** = `fs_used_hot` + `fs_used_cold`
- **Storage usage percentage** = used capacity / total capacity × 100%
- **Hot storage usage percentage** = `fs_used_hot` / `fs_capacity_hot` × 100%
- **Cold storage usage percentage** = `fs_used_cold` / `fs_capacity_cold` × 100%

**V2 instance**, `v2 instance storage`, backed by GetLindormV2StorageUsage:

| Field | Meaning | Unit |
|------|------|------|
| `usage_by_disk_category[]` | Usage details grouped by disk type | — |
| └ `diskType` | Disk type | `PerformanceCloudStorage`, hot / `CapacityCloudStorage`, cold |
| └ `capacity` | Disk capacity | bytes |
| └ `used` | Used capacity | bytes |
| └ `usedLindormTable` | Capacity used by the wide table engine | bytes |
| └ `usedLindormTsdb` | Capacity used by the time series engine | bytes |
| `capacity_by_disk_category[]` | Capacity grouped by disk category | — |
| └ `category` | Category | `PERF_CLOUD_ESSD_PL1`, `REMOTE_CAP_OSS`, and others |
| └ `capacity` | Capacity | GB |

> Note: The two V2 arrays are maps passed through from the underlying API. Fields inside the arrays preserve their original API casing, such as `diskType` and `usedLindormTable`; only top-level fields use snake_case.

**V2 formulas**:

- **Hot storage usage percentage** = `PerformanceCloudStorage.used` / `PerformanceCloudStorage.capacity` × 100%
- **Cold storage usage percentage** = `CapacityCloudStorage.used` / `CapacityCloudStorage.capacity` × 100%
- **Total usage** = the sum of `used` across all disk types

**Example output**:

```
[Storage Usage] Instance ld-uf6l5kr48wqm6rf1h

[Total Capacity] 800GB, hot storage 500GB + cold storage 300GB
[Used Capacity] 520GB, 65%
  - Hot storage used: 320GB, 64%
  - Cold storage used: 200GB, 67%
[Status] ⚠️ Hot storage is approaching the threshold; recommended < 80%.

[Storage Distribution]
- Lindorm wide table engine: 480GB, data 450GB + WAL 30GB
- Other: 40GB

[Suggestions] Hot storage usage is high:
1. Check whether historical data can be migrated to cold storage.
2. Consider expanding hot storage or enabling automatic hot/cold tiering.

📍 View storage details in the console:
1. Open https://lindorm.console.aliyun.com/.
2. Click instance ID "ld-xxx".
3. In the left navigation pane, click Storage Information.
4. View:
   - Total storage capacity
   - Hot storage usage and percentage
   - Cold storage usage and percentage
   - Storage growth trend for the past 7 or 30 days

📍 View detailed storage analysis in ClusterManager:
1. Console → ld-xxx → Database Connection → Access through ClusterManager.
2. Storage Analysis → view:
   - Top 10 tables by storage usage
   - Column family storage distribution
   - Data bloat analysis

Do you need to view the storage growth trend?
```

---

### Flow 2: Query Storage Usage Percentage, Real-time Monitoring

**Applicable scenario**: The user wants to view the latest storage usage percentage through CloudMonitor.

**Execution commands**:

```bash
# Hot storage usage percentage.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name hot_storage_used_percent \
    --dimensions '[{"instanceId":"<instance-id>"}]'

# Cold storage usage percentage.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cold_storage_used_percent \
    --dimensions '[{"instanceId":"<instance-id>"}]'
```

**Output presentation**:
- Current hot storage usage percentage
- Current cold storage usage percentage
- Whether it is close to the alert threshold, 80%

---

### Flow 3: Query Historical Storage Trend

**Applicable scenario**: The user wants to analyze storage growth trends and predict when scaling is needed.

**Execution commands**:

```bash
# Hot storage used bytes, one data point per hour for the past 7 days.
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name hot_storage_used_bytes \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<7 days ago format: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<current time format: YYYY-MM-DD HH:MM:SS>" \
    --period 3600

# Cold storage used bytes, one data point per hour for the past 7 days.
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name cold_storage_used_bytes \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<7 days ago format: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<current time format: YYYY-MM-DD HH:MM:SS>" \
    --period 3600
```

**Analysis points**:
- Calculate average daily growth, GB/day
- Predict storage exhaustion time based on current growth rate
- Determine growth trend, such as linear, exponential, or stable

**Example output**:

```text
[Storage Growth Trend] Instance ld-uf6l5kr48wqm6rf1h, past 7 days

[Hot Storage]
- 7 days ago: 280GB
- Current: 320GB
- Growth: 40GB, daily average 5.7GB
- Trend: linear growth
- Prediction: At the current rate, hot storage will reach the 80% threshold in 32 days.

[Cold Storage]
- 7 days ago: 195GB
- Current: 200GB
- Growth: 5GB, daily average 0.7GB
- Trend: stable

[Suggestions]
- Short term: Hot storage is growing quickly. It is recommended to scale out or enable automatic hot/cold tiering within 1 month.
- Long term: Cold storage growth is stable and has no current pressure.

For more details, see the official storage management guide:
https://help.aliyun.com/zh/lindorm/user-guide/storage-management

Hot/cold tiering configuration guide:
https://help.aliyun.com/zh/lindorm/user-guide/hot-and-cold-separation/

Do you need help configuring a hot/cold tiering policy?
```

---

## Storage-related Monitoring Metrics

### Hot Storage Metrics

| Metric Name | Description | Unit | Alert Threshold |
|----------|------|------|----------|
| `hot_storage_total_bytes` | Total hot storage capacity | bytes | - |
| `hot_storage_used_bytes` | Used hot storage | bytes | - |
| `hot_storage_used_percent` | Hot storage usage percentage | % | > 80% |

### Cold Storage Metrics

| Metric Name | Description | Unit | Alert Threshold |
|----------|------|------|----------|
| `cold_storage_total_bytes` | Total cold storage capacity | bytes | - |
| `cold_storage_used_bytes` | Used cold storage | bytes | - |
| `cold_storage_used_percent` | Cold storage usage percentage | % | > 80% |

### Other Storage Metrics

| Metric Name | Description | Unit |
|----------|------|------|
| `storage_total_bytes` | Total storage space | bytes |
| `storage_used_bytes` | Used storage space | bytes |
| `storage_used_percent` | Storage usage percentage | % |
| `table_hot_storage_used_bytes` | Wide table hot storage usage | bytes |
| `table_cold_storage_used_bytes` | Wide table cold storage usage | bytes |
| `tsdb_hot_storage_used_bytes` | Time series hot storage usage | bytes |
| `tsdb_cold_storage_used_bytes` | Time series cold storage usage | bytes |

---

## Storage Usage Thresholds and Alerts

The default Lindorm disk usage threshold is **80%**.

| Storage Usage | Status | Impact | Suggestion |
|-----------|------|------|------|
| < 60% | ✅ Normal | No impact | Continue monitoring |
| 60% - 80% | ⚠️ Attention | No impact | Consider a scaling plan |
| 80% - 90% | ⚠️ Alert | Write performance decreases | Scale out or clean up data as soon as possible |
| 90% - 95% | 🚨 Critical alert | Write performance decreases severely | Scale out or clean up data immediately |
| ≥ 95% | 🔴 System prohibits writes | The system automatically prohibits data writes, hard limit | Scaling is required before writes can resume |

---

## Hot/cold Tiering Optimization Suggestions

### When to Enable Cold Storage?

| Scenario | Suggestion |
|------|------|
| Historical data access frequency is low, less than once per day | Enable cold storage and configure an automatic hot/cold tiering policy |
| Hot storage usage > 60% | Consider migrating historical data to cold storage |
| Cost optimization | Cold storage costs only 20% of standard cloud storage, about one fifth, and is suitable for long-term archiving |

### Enable Cold Storage, Capacity Cloud Storage

> ⚠️ **Warning**: Enabling cold storage requires a **rolling restart of the instance**, which may cause **latency fluctuation or connection interruptions** for some business read/write requests. Operate during off-peak hours.

**Prerequisites:**
- If the instance storage type is **local HDD disk**, **capacity cloud storage is not supported**.
- Cloud storage type instances, performance or standard, support enabling capacity cloud storage.

**Console enablement path:**

1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
2. In the upper-left corner of the page, select the **region** where the instance resides.
3. On the instance list page, click the **target instance ID** or **Manage** in the Actions column of the target instance row.
4. In the left-side navigation pane, select **Cold Storage**.
5. Click **Enable**.
6. Set the **capacity cloud storage capacity**.
7. Read and select the service agreement, and click **Buy Now**.

**Storage type description:**

| Storage Type | Purpose | Supports Hot/cold Tiering |
|---------|------|-----------------|
| Performance cloud storage | Hot storage, low latency < 10ms | ✅ Supported, capacity storage must be enabled as cold storage |
| Standard cloud storage | Hot storage, medium latency | ✅ Supported, capacity storage must be enabled as cold storage |
| Capacity cloud storage | Cold storage, low cost, 20% of standard cloud storage | ✅ Used as cold storage medium |
| Local HDD disk | Local storage | ❌ Hot/cold tiering is not supported |

> **Note**: Capacity cloud storage and performance/standard cloud storage can **coexist**. You do not need to change the existing storage type.

### Hot/cold Tiering Policy

- **Automatic tiering**: Set a time policy, such as automatically moving data to cold storage 30 days after writing.
- **Manual tiering**: Configure hot/cold tiering rules through Lindorm table properties.
- **Query optimization**: Cold data query latency is high, usually > 100ms. Hot data query latency is low, < 10ms.

Configuration path for hot/cold tiering:
1. Through Lindorm SQL:
   ```sql
   ALTER TABLE metrics SET COLD_DATA_AGE = 2592000;  -- Move to cold storage after 30 days.
   ```

2. Through HBase Shell:
   ```bash
   alter 'metrics', {NAME => 'cf', COLD_DATA_AGE => 2592000}
   ```

### Cold Storage Performance Description

| Metric | Hot Storage, Performance Type | Cold Storage, Capacity Type |
|------|----------------|-----------------|
| Query latency | < 10ms | > 100ms |
| Storage cost | Baseline | Only 20% of standard cloud storage |
| Applicable scenario | High-frequency access | Low-frequency access, less than once per day |
| Read IOPS | High | Throttled, 1 IOPS per 25 GiB capacity |

For more details, see the official configuration guide:
https://help.aliyun.com/zh/lindorm/user-guide/hot-and-cold-separation/

Hot/cold separation best practices:
https://help.aliyun.com/zh/lindorm/user-guide/enable-cold-storage

---

## Missing Parameter Handling

### Missing instance-id

**Follow-up strategy**: First run `aliyun lindorm summary` to identify the region, then run `aliyun lindorm instance list --lindorm-region <region>` and let the user select an instance.

### Missing Time Range, Storage Trend Analysis

**Default strategy**: Use the past 7 days and tell the user.

---

## Error Handling

| Error | Cause | Guide User |
|------|------|----------|
| **No storage details** | File engine is not enabled for the instance or instance status is abnormal | Check instance status and engine configuration |
| **No metric data** | No data in the time range or incorrect metric name | Adjust the time range or confirm the metric name |
| **Insufficient permissions** | AccessKey has no Lindorm permission | Indicate that `AliyunLindormReadOnlyAccess` permission is required |

---

## Common Scenario Quick Reference

| User Description | Execution Flow |
|----------|----------|
| "How much disk space is left?" | Flow 1: Obtain storage details |
| "Is storage almost full?" | Flow 2: Query storage usage percentage |
| "What is the storage growth trend?" | Flow 3: Query historical storage trend |
| "How much hot and cold storage is used respectively?" | Flow 1: Obtain storage details, distinguish hot and cold |
| "When do I need to scale out?" | Flow 3: Analyze growth trend and predict |
