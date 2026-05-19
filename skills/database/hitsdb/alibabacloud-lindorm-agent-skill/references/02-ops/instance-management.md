# 实例管理场景

覆盖实例查询（列表、详情、引擎、存储）与扩缩容知识告知。

## 触发条件

- "我有哪些 Lindorm 实例？"
- "列出 cn-shanghai 的所有实例"
- "ld-xxx 这个实例是什么配置？"
- "这个实例开了哪些引擎？"
- "磁盘还剩多少空间？"
- "实例存储快满了，怎么扩容？"
- "需要加配置，怎么操作？"

---

## 查询流程

### 流程 1：列出所有实例

**适用场景**：用户想查看某个地域下的所有实例，或不知道具体实例 ID。

**地域策略**：

- **默认行为**：用户未指定地域时，默认查询 `cn-shanghai`（华东2-上海），并**必须明确告知**"本次查询的是上海地域"
- **扩展查询**：用户说"所有地域/不确定/可能在其他地域"时，先执行 `get-instance-summary` 获取全地域概览，再按需逐地域查询

**执行命令**：

```bash
# 查询指定地域的实例列表（--region 必需）
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# 查询全地域实例概览（无需 --region）
aliyun hitsdb get-instance-summary

# 查询所有地域
aliyun hitsdb describe-regions
```

**关键字段说明**：

| 字段 | 含义 | 常见值 |
|------|------|--------|
| InstanceId | 实例 ID | `ld-xxx` |
| InstanceAlias | 实例别名 | 用户自定义名称 |
| InstanceStatus | 实例状态 | `ACTIVATION`（运行中）<br>`CREATING`（创建中）<br>`STOPPED`（已停止） |
| PayType | 付费类型 | `POSTPAY`（按量）<br>`PREPAY`（包年包月） |
| RegionId | 地域 ID | `cn-shanghai` |
| ZoneId | 可用区 ID | `cn-shanghai-e` |
| NetworkType | 网络类型 | `vpc` |

---

### 流程 2：查询实例详情

**适用场景**：用户想了解某个实例的完整配置信息。

**执行命令**：

```bash
aliyun hitsdb get-lindorm-instance --instance-id <instance-id>
```

**参数说明**：
- `--instance-id`：实例 ID（必填）
- `--region`：地域 ID（可选，根据 instance-id 自动定位）

**关键字段说明**：

| 分类 | 字段 | 含义 |
|------|------|------|
| **基本** | InstanceId / InstanceAlias / InstanceStatus / CreateTime / ExpireTime | 实例 ID、别名、状态、创建时间、到期时间 |
| **网络** | VpcId / VswitchId / NetworkType | VPC、交换机、网络类型 |
| **存储** | InstanceStorage / DiskCategory / DiskUsage / ColdStorage | 存储容量(GB)、磁盘类型、使用率(%)、冷存储容量 |
| **引擎** | EngineList / EnableLTS / EnableSearch | 引擎列表、时序/搜索开关 |

---

### 流程 3：查询实例引擎列表

**适用场景**：用户想知道实例开了哪些引擎、每个引擎的规格和版本。

**执行命令**：

```bash
aliyun hitsdb get-lindorm-instance-engine-list --instance-id <instance-id>
```

**关键字段说明**：

| 字段 | 含义 |
|------|------|
| EngineType | 引擎类型，详见 SKILL.md →「引擎类型」 |
| Version | 当前版本 |
| LatestVersion | 最新可升级版本 |
| CpuCount | CPU 核心数 |
| MemorySize | 内存大小（GB） |
| CoreCount | 节点数量 |

---

### 流程 4：查询存储详情

**适用场景**：用户想了解存储使用情况、冷热分层。

**执行命令**（根据版本选择）：

```bash
# V1 实例
aliyun hitsdb get-lindorm-fs-used-detail --instance-id <instance-id>

# V2 实例
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id <instance-id>
```

**关键字段说明**：

**V1 实例**（`get-lindorm-fs-used-detail`）：

| 字段 | 含义 |
|------|------|
| FsCapacity | 文件引擎总容量（bytes） |
| FsCapacityHot / FsCapacityCold | 热/冷存储容量（bytes） |
| FsUsedHot / FsUsedCold | 热/冷存储已使用（bytes） |
| FsUsedOnLindormTable | Lindorm 宽表已使用量 |
| FsUsedOnLindormTableData | 宽表数据量 |
| FsUsedOnLindormTableWAL | WAL 日志量 |

**V2 实例**（`get-lindorm-v2-storage-usage`）：

| 字段 | 含义 |
|------|------|
| UsageByDiskCategory[] | 按磁盘类型的使用详情数组 |
| └ diskType | 磁盘类型（`PerformanceCloudStorage` / `CapacityCloudStorage`） |
| └ capacity | 容量（bytes） |
| └ used | 已使用（bytes） |
| └ usedLindormTable | 宽表已使用 |
| └ usedLindormTsdb | 时序已使用 |
| CapacityByDiskCategory[] | 按磁盘类别的容量信息数组 |
| └ category | 类别（`PERF_CLOUD_ESSD_PL1` / `REMOTE_CAP_OSS` 等） |
| └ capacity | 容量（GB） |

---

## 扩缩容知识

**⚠️ 只读 Skill 不执行扩缩容变更命令**，以下为知识告知，引导用户在控制台操作。

### 扩容方式对比

| 瓶颈类型 | 方案 | 生效时间 | 业务影响 |
|---------|------|---------|---------|
| 存储不足 | 存储扩容（在线） | 5-10 分钟 | 无影响 |
| QPS 不足 | 增加节点数（水平扩展） | 10-20 分钟 | 无影响 |
| 单查询延迟高 | 升级节点规格（垂直扩展） | ~30 分钟（滚动重启） | 建议低峰操作 |

操作路径：Lindorm 控制台 → 实例详情 → 变配

### 扩缩容约束

- 缩容需满足：已使用空间 < 目标容量
- 24 小时内最多变配 3 次，两次间隔至少 1 小时
- 扩容失败（库存不足）时可换可用区或换规格

### 官方文档

- 管理存储空间：https://help.aliyun.com/zh/lindorm/user-guide/manage-storage-space/
- 变更容量型云存储容量：https://help.aliyun.com/zh/lindorm/user-guide/expand-cold-storage
- 计费模式说明：https://help.aliyun.com/zh/lindorm/product-overview/billing

---

## 缺参处理

| 缺参 | 策略 |
|------|------|
| 缺 region | 默认查询 `cn-shanghai`，主动告知本次查询地域；用户说"所有地域"时先用 `get-instance-summary` |
| 缺 instance-id | 先列出实例列表，让用户选择 |

---

## 错误处理

| 错误 | 原因 | 引导 |
|------|------|------|
| 实例不存在 | 实例 ID 错误或已释放 | 用 `get-lindorm-instance-list` 确认实例 ID |
| 地域不匹配 | 实例在其他地域 | 提示用户指定正确地域 |
| 权限不足 | AK 无 Lindorm 权限 | 需要 `AliyunLindormReadOnlyAccess` 权限 |

---

## 关联场景

- 扩容前性能分析 → `monitoring-guide.md`
- 存储使用详情 → `storage-analysis.md`
- 扩容后监控设置 → `monitoring-guide.md`