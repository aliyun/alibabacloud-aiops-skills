# 验证方法

执行操作后如何验证成功。

## 实例查询验证

### 验证实例列表查询成功

**作用**：查实例列表（ID、状态、引擎开关，支持按地域/类型筛选）

```bash
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai
```

**返回关键字段**：
- `InstanceList[]`：InstanceId, InstanceAlias, InstanceStatus, ServiceType
- `Enable*` 引擎开关：EnableLts, EnableStream, EnableCompute, EnableVector 等
- 不含连接地址、不含引擎节点数/规格

**成功标志**：
- `InstanceList` 数组非空

**失败标志**：
- `Forbidden.RAM`：权限不足
- `InvalidParameter`：参数错误

### 验证实例详情查询成功

**作用**：查配置/版本/状态（ServiceType、引擎节点数、规格，**不含连接地址**）

```bash
aliyun hitsdb get-lindorm-instance --instance-id ld-xxx
```

**返回关键字段**：
- 实例信息：InstanceId, InstanceStatus, ServiceType, VpcId, DiskUsage
- `EngineList[]`：Engine, CoreCount(节点数), CpuCount, MemorySize, Specification, Version
- 不含连接地址（需连接地址请用 `get-lindorm-instance-engine-list`）

**成功标志**：
- `InstanceStatus` 为 `ACTIVATION` 表示运行中

**验证步骤**：
1. 检查 `InstanceId` 与请求参数一致
2. 检查 `ServiceType` 判断 V1(`lindorm`)/V2(`lindorm_v2`)
3. 检查 `EngineList` 引擎列表的节点数和规格

## 监控查询验证

### 验证指标列表查询成功

```bash
aliyun cms describe-metric-meta-list --namespace acs_lindorm
```

**成功标志**：
- 返回 JSON 包含 `Resources` 数组
- 数组中包含指标对象，包含 `MetricName`, `Namespace`, `Description` 等字段

### 验证监控数据查询成功

```bash
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-xxx"}]'
```

**成功标志**：
- 返回 JSON 包含 `Datapoints` 字段
- `Datapoints` 包含数据点，包含 `instanceId`, `timestamp`, `Average` 等字段
- `Code` 为 `200` 表示成功

**验证步骤**：
1. 检查 `Datapoints` 字段不为空
2. 检查数据点中的 `instanceId` 与请求参数一致
3. 检查 `Average` 字段的数值范围合理（如 CPU 空闲率 0-100）

## 存储查询验证

### 验证存储详情查询成功

```bash
# V1 实例
aliyun hitsdb get-lindorm-fs-used-detail --instance-id ld-xxx

# V2 实例
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id ld-xxx
```

**成功标志**：
- 返回 JSON 包含存储容量相关字段
- 数值单位为 bytes

## IP 白名单验证

### 验证白名单查询成功

```bash
aliyun hitsdb get-instance-ip-white-list --instance-id ld-xxx
```

**成功标志**：
- 返回 JSON 包含 `GroupList` 数组
- 数组中包含 IP 地址或 CIDR 格式的白名单规则

## 连接验证

### 验证网络连通性

使用 telnet 或 nc 测试端口连通性：

```bash
# 测试 MySQL 协议端口（33060）
telnet <lindorm-host> 33060

# 测试 HBase API 端口（30020）
telnet <lindorm-host> 30020

# 测试时序引擎 HTTP 端口（8242）
curl http://<lindorm-host>:8242/api/v2/status
```

**成功标志**：
- telnet 显示 "Connected to xxx"
- curl 返回正常状态响应

## 验证清单

执行任何操作后，按以下清单验证：

| 操作 | 验证命令 | 成功标志 |
|------|---------|---------|
| 查实例列表 | `aliyun hitsdb get-lindorm-instance-list` | `InstanceList` 数组非空，含 InstanceId/Status/Enable* |
| 查配置/状态 | `aliyun hitsdb get-lindorm-instance` | `EngineList` 含 CoreCount/Specification/Version（不含连接地址） |
| 查连接地址 | `aliyun hitsdb get-lindorm-instance-engine-list` | `NetInfoList` 含 ConnectionString/Port/NetType |
| 查询存储详情 | `aliyun hitsdb get-lindorm-fs-used-detail` | 包含存储容量数据 |
| 查询 IP 白名单 | `aliyun hitsdb get-instance-ip-white-list` | 包含白名单规则 |
| 查询监控指标 | `aliyun cms describe-metric-meta-list` | `Resources` 数组非空 |
| 查询监控数据 | `aliyun cms describe-metric-last` | `Datapoints` 字段非空 |