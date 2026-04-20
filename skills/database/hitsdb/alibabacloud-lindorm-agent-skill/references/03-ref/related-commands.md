# CLI 命令列表

本 Skill 涉及的所有 aliyun CLI 命令。

## Lindorm 实例管理 CLI

**产品名**: `hitsdb`（Lindorm 产品别名）
**API Version**: `2020-06-15`

### 插件安装

```bash
# 安装 Lindorm 插件
aliyun plugin install --names hitsdb

# 启用自动插件安装（推荐）
aliyun configure set --auto-plugin-install true
```

### 查询命令

| CLI 命令 | 说明 | 必需参数 | 返回关键字段 |
|----------|------|---------|-------------|
| `aliyun hitsdb describe-regions` | 查询支持的地域列表 | 无 | `Regions[]`: RegionId, LocalName, RegionEndpoint |
| `aliyun hitsdb get-instance-summary` | 查询全地域实例概览（无需 `--region`） | 无 | `RegionalSummary[]`: RegionId, RunningCount, LockingCount, Total |
| `aliyun hitsdb get-lindorm-instance-list` | 查实例列表（ID、状态、引擎开关，支持按地域/类型筛选） | `--region` | `InstanceList[]`: InstanceId, InstanceAlias, InstanceStatus, ServiceType, Enable* 引擎开关 |
| `aliyun hitsdb get-lindorm-instance` | 查配置/版本/状态（ServiceType、引擎节点数、规格，**不含连接地址**） | `--instance-id` | InstanceStatus, ServiceType, VpcId, `EngineList[]`: Engine, CoreCount, CpuCount, MemorySize, Specification, Version |
| `aliyun hitsdb get-lindorm-instance-engine-list` | 查连接地址（各引擎 host:port、公网/内网） | `--instance-id` | `EngineList[]`: EngineType, `NetInfoList[]`: ConnectionString, Port, NetType(`"2"`=内网/`"0"`=公网) |
| `aliyun hitsdb get-lindorm-fs-used-detail` | 查询存储详情（V1） | `--instance-id` | FsCapacity, FsUsedHot/Cold, FsUsedOnLindormTable/TSDB/Search, `LStorageUsageList[]` |
| `aliyun hitsdb get-lindorm-v2-storage-usage` | 查询存储详情（V2） | `--instance-id` | `UsageByDiskCategory[]`: capacity, used, usedLindormTable/Tsdb/Search3/Column3/Vector3/Message3 |
| `aliyun hitsdb get-instance-ip-white-list` | 查询 IP 白名单 | `--instance-id` | `GroupList[]`: GroupName, SecurityIpList |
| `aliyun hitsdb get-lindorm-v2-instance-details` | 查询 V2 实例详情 | `--instance-id` | V2 实例的详细配置信息 |

### 管理命令

| CLI 命令 | 说明 | 必需参数 |
|----------|------|---------|
| `aliyun hitsdb create-lindorm-instance` | 创建实例 | 多个参数，见 --help |
| `aliyun hitsdb create-lindorm-v2-instance` | 创建 V2 实例 | 多个参数，见 --help |
| `aliyun hitsdb release-lindorm-instance` | 释放实例 | `--instance-id`, `--region` |
| `aliyun hitsdb upgrade-lindorm-instance` | 变配实例 | `--instance-id`, `--region` |
| `aliyun hitsdb update-instance-ip-white-list` | 更新 IP 白名单 | `--instance-id`, `--region`, `--group-name`, `--security-ip-list` |
| `aliyun hitsdb update-lindorm-instance-attribute` | 更新实例属性 | `--instance-id`, `--region` |

### 执行示例

```bash
# 查询地域
aliyun hitsdb describe-regions

# 查询实例概览（无需 region，自动返回所有地域）
aliyun hitsdb get-instance-summary

# 查询实例列表（需要指定地域）
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# 查询实例详情（无需 region）
aliyun hitsdb get-lindorm-instance --instance-id ld-uf6nbdlx5n34q6l6t

# 查询引擎列表（无需 region）
aliyun hitsdb get-lindorm-instance-engine-list --instance-id ld-uf6nbdlx5n34q6l6t

# 查询存储详情 V1（无需 region）
aliyun hitsdb get-lindorm-fs-used-detail --instance-id ld-uf6cx7381qw2u5u8w

# 查询存储详情 V2（无需 region）
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id ld-uf6nbdlx5n34q6l6t

# 查询 IP 白名单（无需 region）
aliyun hitsdb get-instance-ip-white-list --instance-id ld-uf6nbdlx5n34q6l6t

# 带过滤条件的实例列表查询
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai --service-type lindorm_v2 --support-engine 4
```

### 返回值结构

#### get-lindorm-instance-list → 查实例列表

返回实例基本信息，不含连接地址、不含引擎节点数/规格。

```json
{
  "InstanceList": [
    {
      "InstanceId": "ld-xxx",
      "InstanceAlias": "实例名称",
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

#### get-lindorm-instance → 查配置/版本/状态

返回单个实例的详细配置，含引擎节点数/规格/版本，**不含连接地址**。

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

#### get-lindorm-instance-engine-list → 查连接地址

返回各引擎的连接地址和网络类型，**不含配置/节点数信息**。

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

**NetType 说明**：`"2"` = 内网，`"0"` = 公网

#### get-instance-ip-white-list → 查 IP 白名单

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

#### get-lindorm-fs-used-detail → V1 存储详情

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

> 单位均为 bytes。

#### get-lindorm-v2-storage-usage → V2 存储详情

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

> `CapacityByDiskCategory` 单位为 GB，`UsageByDiskCategory` 单位为 bytes。

---

### 参数说明

#### `--region` 地域参数

| 地域 ID | 地域名称 |
|---------|---------|
| `cn-shanghai` | 华东2（上海）- 默认 |
| `cn-beijing` | 华北2（北京） |
| `cn-hangzhou` | 华东1（杭州） |
| `cn-shenzhen` | 华南1（深圳） |
| `cn-zhangjiakou` | 华北3（张家口） |
| `cn-qingdao` | 华北1（青岛） |
| `cn-wulanchabu` | 华北6（乌兰察布） |
| `cn-guangzhou` | 华南3（广州） |
| `cn-chengdu` | 西南1（成都） |

#### `--instance-id` 实例 ID

格式：`ld-xxx`（以 ld- 开头，后接字母数字）

#### `--service-type` 实例类型

完整列表见 SKILL.md →「版本判断」

| 值 | 说明 |
|----|------|
| `lindorm` | Lindorm V1 单可用区实例 |
| `lindorm_multizone` | Lindorm V1 多可用区实例 |
| `lindorm_multizone_basic` | Lindorm V1 多可用区（基础版） |
| `lindorm_v2` | Lindorm V2 单可用区实例 |
| `lindorm_v2_multizone` | Lindorm V2 多可用区（基础版） |
| `lindorm_v2_multizone_ha` | Lindorm V2 多可用区（高可用版） |
| `serverless_lindorm` | Lindorm Serverless 实例 |
| `lindorm_standalone` | Lindorm 单节点（开发测试） |

#### `--support-engine` 引擎类型（位掩码）

| 值 | 引擎代码 | 说明 |
|----|---------|------|
| `1` | 搜索引擎 | `solr` / `lsearch` |
| `2` | 时序引擎 | `tsdb` |
| `4` | 宽表引擎 | `lindorm` / `lcolumn` |
| `8` | 文件引擎 | `file` |
| `15` = 1+2+4+8 | 全部引擎 | 宽表 + 时序 + 搜索 + 文件 |

#### 引擎类型详情

引擎类型详情见 SKILL.md →「引擎类型详情」

---

## 云监控 CLI

**产品名**: `cms`
**Namespace**: `acs_lindorm`

### 插件安装

```bash
# 安装云监控插件
aliyun plugin install --names cms
```

### 查询命令

| CLI 命令 | 说明 | 必需参数 |
|----------|------|---------|
| `aliyun cms describe-metric-meta-list` | 查询指标列表 | `--namespace`, `--region` | `--region` 可选 |
| `aliyun cms describe-metric-last` | 查询最新数据 | `--namespace`, `--metric-name`, `--dimensions` | `--region` 可选，通过 instanceId 自动定位 |
| `aliyun cms describe-metric-data` | 查询历史数据 | `--namespace`, `--metric-name`, `--dimensions`, `--start-time`, `--end-time` | `--region` 可选，通过 instanceId 自动定位 |

### 执行示例

```bash
# 查询 Lindorm 监控指标列表
aliyun cms describe-metric-meta-list --namespace acs_lindorm

# 查询 CPU 空闲率最新数据
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]'

# 查询内存使用率最新数据
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name mem_used_percent \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]'

# 查询历史监控数据（指定时间范围）
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]' \
    --start-time "2026-04-14 08:00:00" \
    --end-time "2026-04-14 09:00:00" \
    --period 60
```

### 返回值结构

#### describe-metric-meta-list → 查指标列表

```json
{
  "Code": 200,
  "Resources": {
    "Resource": [
      {
        "MetricName": "cpu_idle",
        "Namespace": "acs_lindorm",
        "Description": "CPU空闲率",
        "Unit": "%",
        "Periods": "60,300",
        "Dimensions": "userId,instanceId,host",
        "Statistics": "Average,Maximum,Minimum"
      }
    ]
  }
}
```

#### describe-metric-last → 查最新数据

```json
{
  "Code": "200",
  "Period": "60",
  "Datapoints": "[{\"timestamp\":1776414660000,\"instanceId\":\"ld-xxx\",\"host\":\"table-1\",\"userId\":\"149xxx\",\"Average\":93.241,\"Maximum\":94.217,\"Minimum\":91.082}]"
}
```

> 注意：`Datapoints` 是 JSON **字符串**，需要二次解析。每个数据点含 `host`（节点名）和 `userId`。

#### describe-metric-data → 查历史数据

返回结构与 `describe-metric-last` 相同，`Datapoints` 含多个时间点的数据。

---

### 参数说明

#### `--dimensions` 维度参数（JSON 数组）

**格式说明**：Linux/macOS 用单引号包裹（无需转义），Windows CMD 用双引号+转义。

```bash
# ✅ Linux/macOS 推荐格式（单引号，无需转义）
--dimensions '[{"instanceId":"ld-xxx"}]'

# ✅ Windows CMD 格式（双引号+转义）
--dimensions "[{\"instanceId\":\"ld-xxx\"}]"
```

多维度示例：
```bash
--dimensions "[{\"instanceId\":\"ld-xxx\"},{\"instanceId\":\"ld-yyy\"}]"
```

#### `--start-time` / `--end-time` 时间参数

时间格式说明见 SKILL.md →「时间格式」

#### `--period` 采集周期（秒）

| 值 | 说明 |
|----|------|
| `60` | 1 分钟（默认） |
| `300` | 5 分钟 |
| `900` | 15 分钟 |
| `3600` | 1 小时 |

---

常用监控指标见 `references/02-ops/monitoring-guide.md`

---

## JMESPath 查询过滤

使用 `--cli-query` 过滤输出：

```bash
# 仅返回实例 ID 和名称
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai \
    --cli-query 'InstanceList[].[InstanceId,InstanceAlias,InstanceStatus]'

# 仅返回特定实例的引擎类型（无需 --region）
aliyun hitsdb get-lindorm-instance-engine-list \
    --instance-id ld-uf6nbdlx5n34q6l6t \
    --cli-query 'EngineList[].[EngineType,NetInfoList[0].ConnectionString]'

# 仅返回监控数据平均值
aliyun cms describe-metric-last \
    --namespace acs_lindorm --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-xxx"}]' \
    --cli-query 'Datapoints'
```

---

## 分页查询

使用 `--pager` 合并多页结果：

```bash
# 自动合并所有分页的实例列表
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai --pager
```

---

## 错误处理

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `Instance.IsNotValid` | 实例 ID 无效或不存在 | 使用 `get-lindorm-instance-list --region <region>` 确认实例 ID |
| `InvalidParameter.InstanceId` | 实例 ID 格式错误 | 使用 `ld-xxx` 格式 |
| `InstanceNotFound` | 实例不存在 | 检查地域和实例 ID |
| `Forbidden.RAM` | 权限不足 | 添加 `AliyunLindormReadOnlyAccess` 权限 |
| `Throttling.User` | API 限流 | 降低调用频率或稍后重试 |

---

## 相关文档

- Lindorm API 文档：https://help.aliyun.com/zh/lindorm/developer-reference/api-reference
- 云监控 API 文档：https://help.aliyun.com/zh/cms/developer-reference/api-reference
- Aliyun CLI 安装指南：`./cli-installation-guide.md`
- Lindorm CLI / HBase Shell 指南：`./lindorm-cli-guide.md`