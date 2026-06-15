# Aliyun CLI Command List

All Aliyun CLI commands involved in this Skill, such as `aliyun hitsdb ...`, are used for cloud resource operations including instance management, connection address query, whitelist management, and monitoring. Use `lindorm-cli` to execute SQL. See `lindorm-cli-guide.md`.

## Lindorm Instance Management CLI

**Product name**: `hitsdb`, Lindorm product alias
**API Version**: `2020-06-15`

### Plugin Installation

```bash
# Install the Lindorm plugin.
aliyun plugin install --names hitsdb

# Enable automatic plugin installation, recommended.
aliyun configure set --auto-plugin-install true
```

### Query Commands

| CLI Command | Description | Required Parameters | Key Returned Fields |
|----------|------|---------|-------------|
| `aliyun hitsdb describe-regions` | Query supported region list | None | `Regions[]`: RegionId, LocalName, RegionEndpoint |
| `aliyun hitsdb get-instance-summary` | Query all-region instance overview, no `--region` required | None | `RegionalSummary[]`: RegionId, RunningCount, LockingCount, Total |
| `aliyun hitsdb get-lindorm-instance-list` | Query instance list, including ID, status, engine switches, and support for filtering by region/type | `--region` | `InstanceList[]`: InstanceId, InstanceAlias, InstanceStatus, ServiceType, Enable* engine switches |
| `aliyun hitsdb get-lindorm-instance` | Query configuration/version/status, including ServiceType, engine node count, and specifications. **Connection address is not included** | `--instance-id` | InstanceStatus, ServiceType, VpcId, `EngineList[]`: Engine, CoreCount, CpuCount, MemorySize, Specification, Version |
| `aliyun hitsdb get-lindorm-instance-engine-list` | Query connection addresses, including host:port and public/internal networks for each engine | `--instance-id` | `EngineList[]`: EngineType, `NetInfoList[]`: ConnectionString, Port, NetType, `"2"`=internal / `"0"`=public |
| `aliyun hitsdb get-lindorm-fs-used-detail` | Query storage details, V1 | `--instance-id` | FsCapacity, FsUsedHot/Cold, FsUsedOnLindormTable/TSDB/Search, `LStorageUsageList[]` |
| `aliyun hitsdb get-lindorm-v2-storage-usage` | Query storage details, V2 | `--instance-id` | `UsageByDiskCategory[]`: capacity, used, usedLindormTable/Tsdb/Search3/Column3/Vector3/Message3 |
| `aliyun hitsdb get-instance-ip-white-list` | Query IP whitelist | `--instance-id` | `GroupList[]`: GroupName, SecurityIpList |
| `aliyun hitsdb get-lindorm-v2-instance-details` | Query V2 instance details | `--instance-id` | Detailed configuration information of a V2 instance |

### Management Commands

| CLI Command | Description | Required Parameters |
|----------|------|---------|
| `aliyun hitsdb create-lindorm-instance` | Create instance | Multiple parameters. See --help. |
| `aliyun hitsdb create-lindorm-v2-instance` | Create V2 instance | Multiple parameters. See --help. |
| `aliyun hitsdb release-lindorm-instance` | Release instance | `--instance-id`, `--region` |
| `aliyun hitsdb upgrade-lindorm-instance` | Change instance specification | `--instance-id`, `--region` |
| `aliyun hitsdb update-instance-ip-white-list` | Update IP whitelist | `--instance-id`, `--region`, `--group-name`, `--security-ip-list` |
| `aliyun hitsdb update-lindorm-instance-attribute` | Update instance attributes | `--instance-id`, `--region` |

### Execution Examples

```bash
# Query regions.
aliyun hitsdb describe-regions

# Query instance overview, no region required, automatically returns all regions.
aliyun hitsdb get-instance-summary

# Query instance list, region required.
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# Query instance details, no region required.
aliyun hitsdb get-lindorm-instance --instance-id ld-uf6nbdlx5n34q6l6t

# Query engine list, no region required.
aliyun hitsdb get-lindorm-instance-engine-list --instance-id ld-uf6nbdlx5n34q6l6t

# Query V1 storage details, no region required.
aliyun hitsdb get-lindorm-fs-used-detail --instance-id ld-uf6cx7381qw2u5u8w

# Query V2 storage details, no region required.
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id ld-uf6nbdlx5n34q6l6t

# Query IP whitelist, no region required.
aliyun hitsdb get-instance-ip-white-list --instance-id ld-uf6nbdlx5n34q6l6t

# Query instance list with filters.
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai --service-type lindorm_v2 --support-engine 4
```

### Return Value Structure

#### get-lindorm-instance-list -> Query Instance List

Returns basic instance information. It does not include connection addresses or engine node counts/specifications.

```json
{
  "InstanceList": [
    {
      "InstanceId": "ld-xxx",
      "InstanceAlias": "instance-name",
      "InstanceStatus": "ACTIVATION",
      "ServiceType": "lindorm_v2",
      "InstanceStorage": "320",
      "VpcId": "vpc-xxx",
      "RegionId": "cn-shanghai",
      "EnableLts": true,
      "EnableStream": true,
      "EnableCompute": true,
      "EnableVector": false
    }
  ],
  "Total": 1
}
```

#### get-lindorm-instance -> Query Configuration / Version / Status

Returns the detailed configuration of a single instance, including engine node counts, specifications, and versions. **Connection addresses are not included**.

```json
{
  "InstanceId": "ld-xxx",
  "InstanceStatus": "ACTIVATION",
  "ServiceType": "lindorm_v2",
  "NetworkType": "vpc",
  "VpcId": "vpc-xxx",
  "DiskUsage": "15.3%",
  "DiskCategory": "cloud_essd",
  "EngineList": [
    {
      "Engine": "lindorm",
      "CoreCount": "2",
      "CpuCount": "4",
      "MemorySize": "16GB",
      "Specification": "lindorm.g.xlarge",
      "Version": "2.8.6.4"
    },
    {
      "Engine": "tsdb",
      "CoreCount": "2",
      "CpuCount": "4",
      "MemorySize": "16GB",
      "Specification": "lindorm.g.xlarge",
      "Version": "3.7.11"
    }
  ]
}
```

#### get-lindorm-instance-engine-list -> Query Connection Addresses

Returns connection addresses and network types of each engine. **Configuration/node count information is not included**.

```json
{
  "EngineList": [
    {
      "EngineType": "lindorm",
      "NetInfoList": [
        {
          "ConnectionString": "ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com",
          "Port": 30020,
          "NetType": "2",
          "AccessType": 1
        },
        {
          "ConnectionString": "ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com",
          "Port": 33060,
          "NetType": "2",
          "AccessType": 5
        }
      ]
    },
    {
      "EngineType": "tsdb",
      "NetInfoList": [
        {
          "ConnectionString": "ld-xxx-proxy-tsdb.lindorm.rds.aliyuncs.com",
          "Port": 8242,
          "NetType": "2",
          "AccessType": 1
        }
      ]
    }
  ]
}
```

**NetType description**: `"2"` = internal network, `"0"` = public network

#### get-instance-ip-white-list -> Query IP Whitelist

```json
{
  "InstanceId": "ld-xxx",
  "GroupList": [
    {
      "GroupName": "default",
      "SecurityIpList": "127.0.0.1"
    },
    {
      "GroupName": "office",
      "SecurityIpList": "140.205.0.0/24"
    }
  ]
}
```

#### get-lindorm-fs-used-detail -> V1 Storage Details

```json
{
  "FsCapacity": "429496729600",
  "FsUsedHot": "789543",
  "FsUsedCold": "0",
  "FsUsedOnLindormTable": "44093",
  "FsUsedOnLindormTSDB": "856",
  "FsUsedOnLindormSearch": "0",
  "FsUsedOnLindormTableData": "15452",
  "FsUsedOnLindormTableWAL": "10304",
  "LStorageUsageList": [
    {
      "DiskType": "StandardCloudStorage",
      "Capacity": "429496729600",
      "Used": "912591424",
      "UsedLindormTable": "43694",
      "UsedLindormTsdb": "356",
      "UsedLindormSearch": "310515",
      "UsedLindormMessage3": "433856",
      "UsedOther": "911803003"
    }
  ],
  "Valid": "true"
}
```

> All units are bytes.

#### get-lindorm-v2-storage-usage -> V2 Storage Details

```json
{
  "CapacityByDiskCategory": [
    { "category": "PERF_CLOUD_ESSD_PL1", "capacity": 960, "usedCapacity": 0, "mode": "CLOUD_STORAGE" },
    { "category": "LOCAL_BUFFER", "capacity": 480, "usedCapacity": 0, "mode": "REMOTE_STORAGE" },
    { "category": "REMOTE_CAP_OSS", "capacity": 100, "usedCapacity": 0, "mode": "REMOTE_STORAGE" }
  ],
  "UsageByDiskCategory": [
    {
      "diskType": "PerformanceCloudStorage",
      "capacity": 1030792151040,
      "used": 2506614016,
      "usedLindormTable": 662244,
      "usedLindormTsdb": 159406,
      "usedLindormSearch3": 363609,
      "usedLindormColumn3": 228742,
      "usedLindormVector3": 441015,
      "usedLindormMessage3": 208236,
      "usedLindormSpark": 2240333801,
      "usedOther": 264216963
    }
  ]
}
```

> `CapacityByDiskCategory` is in GB, and `UsageByDiskCategory` is in bytes.

---

### Parameter Descriptions

#### `--region` Region Parameter

| Region ID | Region Name |
|---------|---------|
| `cn-shanghai` | East China 2, Shanghai, default |
| `cn-beijing` | North China 2, Beijing |
| `cn-hangzhou` | East China 1, Hangzhou |
| `cn-shenzhen` | South China 1, Shenzhen |
| `cn-zhangjiakou` | North China 3, Zhangjiakou |
| `cn-qingdao` | North China 1, Qingdao |
| `cn-wulanchabu` | North China 6, Ulanqab |
| `cn-guangzhou` | South China 3, Guangzhou |
| `cn-chengdu` | Southwest China 1, Chengdu |

#### `--instance-id` Instance ID

Format: `ld-xxx`, starts with `ld-` followed by letters and digits.

#### `--service-type` Instance Type

For the complete list, see SKILL.md -> "Version identification".

| Value | Description |
|----|------|
| `lindorm` | Lindorm V1 single-zone instance |
| `lindorm_multizone` | Lindorm V1 multi-zone instance |
| `lindorm_multizone_basic` | Lindorm V1 multi-zone instance, basic edition |
| `lindorm_v2` | Lindorm V2 single-zone instance |
| `lindorm_v2_multizone` | Lindorm V2 multi-zone instance, basic edition |
| `lindorm_v2_multizone_ha` | Lindorm V2 multi-zone instance, high-availability edition |
| `serverless_lindorm` | Lindorm Serverless instance |
| `lindorm_standalone` | Lindorm single-node instance for development and testing |

#### `--support-engine` Engine Type, Bitmask

| Value | Engine Code | Description |
|----|---------|------|
| `1` | Search engine | `solr` / `lsearch` |
| `2` | Time series engine | `tsdb` |
| `4` | Wide table engine | `lindorm` / `lcolumn` |
| `8` | File engine | `file` |
| `15` = 1+2+4+8 | All engines | Wide table + time series + search + file |

#### Engine Type Details

For engine type details, see SKILL.md -> "Engine type details".

---

## CloudMonitor CLI

**Product name**: `cms`
**Namespace**: `acs_lindorm`

### Plugin Installation

```bash
# Install the CloudMonitor plugin.
aliyun plugin install --names cms
```

### Query Commands

| CLI Command | Description | Required Parameters |
|----------|------|---------|
| `aliyun cms describe-metric-meta-list` | Query metric list | `--namespace`, `--region`; `--region` is optional |
| `aliyun cms describe-metric-last` | Query latest data | `--namespace`, `--metric-name`, `--dimensions`; `--region` is optional and automatically located by instanceId |
| `aliyun cms describe-metric-data` | Query historical data | `--namespace`, `--metric-name`, `--dimensions`, `--start-time`, `--end-time`; `--region` is optional and automatically located by instanceId |

### Execution Examples

```bash
# Query Lindorm monitoring metric list.
aliyun cms describe-metric-meta-list --namespace acs_lindorm

# Query latest CPU idle rate data.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]'

# Query latest memory usage rate data.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name mem_used_percent \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]'

# Query historical monitoring data, specified time range.
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]' \
    --start-time "2026-04-14 08:00:00" \
    --end-time "2026-04-14 09:00:00" \
    --period 60
```

### Return Value Structure

#### describe-metric-meta-list -> Query Metric List

```json
{
  "Code": 200,
  "Resources": {
    "Resource": [
      {
        "MetricName": "cpu_idle",
        "Namespace": "acs_lindorm",
        "Description": "CPU idle rate",
        "Unit": "%",
        "Periods": "60,300",
        "Dimensions": "userId,instanceId,host",
        "Statistics": "Average,Maximum,Minimum"
      }
    ]
  }
}
```

#### describe-metric-last -> Query Latest Data

```json
{
  "Code": "200",
  "Period": "60",
  "Datapoints": "[{\"timestamp\":1776414660000,\"instanceId\":\"ld-xxx\",\"host\":\"table-1\",\"userId\":\"149xxx\",\"Average\":93.241,\"Maximum\":94.217,\"Minimum\":91.082}]"
}
```

> Note: `Datapoints` is a JSON **string** and requires secondary parsing. Each data point contains `host`, the node name, and `userId`.

#### describe-metric-data -> Query Historical Data

The returned structure is the same as `describe-metric-last`, and `Datapoints` contains data at multiple time points.

---

### Parameter Descriptions

#### `--dimensions` Dimension Parameter, JSON Array

**Format description**: On Linux/macOS, wrap it with single quotes and no escaping is required. On Windows CMD, use double quotes plus escaping.

```bash
# ✅ Recommended Linux/macOS format, single quotes, no escaping required.
--dimensions '[{"instanceId":"ld-xxx"}]'

# ✅ Windows CMD format, double quotes plus escaping.
--dimensions "[{\"instanceId\":\"ld-xxx\"}]"
```

Multi-dimension example:
```bash
--dimensions "[{\"instanceId\":\"ld-xxx\"},{\"instanceId\":\"ld-yyy\"}]"
```

#### `--start-time` / `--end-time` Time Parameters

For time format descriptions, see SKILL.md -> "Time format".

#### `--period` Collection Period, Seconds

| Value | Description |
|----|------|
| `60` | 1 minute, default |
| `300` | 5 minutes |
| `900` | 15 minutes |
| `3600` | 1 hour |

---

Common monitoring metrics are described in `references/02-ops/monitoring-guide.md`.

---

## JMESPath Query Filtering

Use `--cli-query` to filter output:

```bash
# Return only instance ID and name.
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai \
    --cli-query 'InstanceList[].[InstanceId,InstanceAlias,InstanceStatus]'

# Return only the engine type of a specific instance, no --region required.
aliyun hitsdb get-lindorm-instance-engine-list \
    --instance-id ld-uf6nbdlx5n34q6l6t \
    --cli-query 'EngineList[].[EngineType,NetInfoList[0].ConnectionString]'

# Return only the average monitoring data value.
aliyun cms describe-metric-last \
    --namespace acs_lindorm --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-xxx"}]' \
    --cli-query 'Datapoints'
```

---

## Paginated Query

Use `--pager` to merge multi-page results:

```bash
# Automatically merge all paginated instance list results.
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai --pager
```

---

## Error Handling

| Error Message | Cause | Solution |
|---------|------|---------|
| `Instance.IsNotValid` | Instance ID is invalid or does not exist | Use `get-lindorm-instance-list --region <region>` to confirm the instance ID |
| `InvalidParameter.InstanceId` | Instance ID format is incorrect | Use the `ld-xxx` format |
| `InstanceNotFound` | Instance does not exist | Check the region and instance ID |
| `Forbidden.RAM` | Insufficient permissions | Add the `AliyunLindormReadOnlyAccess` permission |
| `Throttling.User` | API throttling | Reduce the call frequency or retry later |

---

## Related Documents

- Lindorm API documentation: https://help.aliyun.com/zh/lindorm/developer-reference/api-reference
- CloudMonitor API documentation: https://help.aliyun.com/zh/cms/developer-reference/api-reference
- Aliyun CLI installation guide: `./cli-installation-guide.md`
- Lindorm CLI guide: `./lindorm-cli-guide.md`
- HBase Shell guide: `./hbase-shell-guide.md`