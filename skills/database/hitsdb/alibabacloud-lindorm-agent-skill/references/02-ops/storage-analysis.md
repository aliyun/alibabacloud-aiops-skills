# 存储分析场景

当用户关心 Lindorm 实例的存储使用情况、冷热数据分布、存储增长趋势时，按本指南执行。

## 触发条件

用户的典型表达：
- "磁盘还剩多少？"
- "存储快满了吗？"
- "冷热存储分别用了多少？"
- "存储增长趋势如何？"
- "ld-xxx 使用了多少存储？"
- "热存储使用率是多少？"

## 核心能力

- **存储详情查询**：总容量、已用容量、冷热分布
- **存储使用率监控**：热存储/冷存储使用率趋势
- **存储增长分析**：历史趋势、增长速率
- **冷热分层建议**：何时启用冷存储、冷热数据迁移策略

## 执行流程

### 流程 1：获取存储详情（快照数据）

**适用场景**：用户想快速了解当前存储使用情况。

**执行命令**：

```bash
# V1 实例
aliyun hitsdb get-lindorm-fs-used-detail \
    --instance-id <instance-id>

# V2 实例（instanceType=lindorm_v2）
aliyun hitsdb get-lindorm-v2-storage-usage \
    --instance-id <instance-id>
```

**输出呈现**：

先给结论性摘要：
- 总容量（热+冷）
- 已用容量（热+冷）
- 使用率（%）
- 冷热分布占比
- 告警状态（是否接近阈值）

再按需展开详细字段。

**关键字段说明**：

**V1 实例**（`get-lindorm-fs-used-detail`）：

| 字段 | 含义 | 单位 |
|------|------|------|
| `FsCapacity` | 文件引擎总容量 | bytes |
| `FsCapacityHot` | 热存储容量 | bytes |
| `FsCapacityCold` | 冷存储容量 | bytes |
| `FsUsedHot` | 热存储已使用 | bytes |
| `FsUsedCold` | 冷存储已使用 | bytes |
| `FsUsedOnLindormTable` | Lindorm 宽表已使用 | bytes |
| `FsUsedOnLindormTableData` | 宽表数据量 | bytes |
| `FsUsedOnLindormTableWAL` | WAL 日志量 | bytes |

**V1 计算公式**：

- **总容量** = `FsCapacityHot` + `FsCapacityCold`
- **已用容量** = `FsUsedHot` + `FsUsedCold`
- **存储使用率** = (已用容量 / 总容量) × 100%
- **热存储使用率** = (`FsUsedHot` / `FsCapacityHot`) × 100%
- **冷存储使用率** = (`FsUsedCold` / `FsCapacityCold`) × 100%

**V2 实例**（`get-lindorm-v2-storage-usage`）：

| 字段 | 含义 | 单位 |
|------|------|------|
| `UsageByDiskCategory[]` | 按磁盘类型的使用详情数组 | — |
| └ `diskType` | 磁盘类型 | `PerformanceCloudStorage`（热）/ `CapacityCloudStorage`（冷） |
| └ `capacity` | 磁盘容量 | bytes |
| └ `used` | 已使用量 | bytes |
| └ `usedLindormTable` | 宽表已使用 | bytes |
| └ `usedLindormTsdb` | 时序已使用 | bytes |
| `CapacityByDiskCategory[]` | 按磁盘类别的容量信息 | — |
| └ `category` | 类别 | `PERF_CLOUD_ESSD_PL1` / `REMOTE_CAP_OSS` 等 |
| └ `capacity` | 容量 | GB |

**V2 计算公式**：

- **热存储使用率** = `PerformanceCloudStorage.used` / `PerformanceCloudStorage.capacity` × 100%
- **冷存储使用率** = `CapacityCloudStorage.used` / `CapacityCloudStorage.capacity` × 100%
- **总使用量** = Σ 各 diskType 的 `used`

**示例输出**：

```
【存储使用情况】实例 ld-uf6l5kr48wqm6rf1h

【总容量】800GB（热存储 500GB + 冷存储 300GB）
【已用容量】520GB（65%）
  - 热存储已用：320GB（64%）
  - 冷存储已用：200GB（67%）
【状态】⚠️ 热存储接近阈值（推荐 < 80%）

【存储分布】
- Lindorm 宽表：480GB（数据 450GB + WAL 30GB）
- 其他：40GB

【建议】热存储使用率较高，建议：
1. 检查是否可将历史数据迁移到冷存储
2. 考虑扩容热存储或启用自动冷热分层

📍 在控制台查看存储详情：
1. 控制台：https://lindorm.console.aliyun.com/
2. 点击实例 ID "ld-xxx"
3. 左侧菜单：存储信息
4. 查看：
   - 总存储容量
   - 热存储使用量/使用率
   - 冷存储使用量/使用率
   - 存储增长趋势（最近 7 天/30 天）

📍 在 ClusterManager 查看详细存储分析：
1. 控制台 → ld-xxx → 数据库连接 → "通过 ClusterManager 访问"
2. 存储分析 → 查看：
   - 表级存储占用 Top 10
   - 列族存储分布
   - 数据膨胀分析

需要查看存储增长趋势吗？
```

---

### 流程 2：查询存储使用率（实时监控）

**适用场景**：用户想查看最新的存储使用率（通过云监控）。

**执行命令**：

```bash
# 热存储使用率
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name hot_storage_used_percent \
    --dimensions '[{"instanceId":"<instance-id>"}]'

# 冷存储使用率
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cold_storage_used_percent \
    --dimensions '[{"instanceId":"<instance-id>"}]'
```

**输出呈现**：
- 当前热存储使用率
- 当前冷存储使用率
- 是否接近告警阈值（80%）

---

### 流程 3：查询存储历史趋势

**适用场景**：用户想分析存储增长趋势、预测何时需要扩容。

**执行命令**：

```bash
# 热存储已使用量（过去 7 天，每小时 1 个点）
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name hot_storage_used_bytes \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<7天前 格式: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<当前时间 格式: YYYY-MM-DD HH:MM:SS>" \
    --period 3600

# 冷存储已使用量（过去 7 天，每小时 1 个点）
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name cold_storage_used_bytes \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<7天前 格式: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<当前时间 格式: YYYY-MM-DD HH:MM:SS>" \
    --period 3600
```

**分析要点**：
- 计算日均增长量（GB/天）
- 预测存储耗尽时间（按当前增长速率）
- 判断增长趋势（线性/指数/平稳）

**示例输出**：

```
【存储增长趋势】实例 ld-uf6l5kr48wqm6rf1h（过去 7 天）

【热存储】
- 7 天前：280GB
- 当前：320GB
- 增长量：40GB（日均 5.7GB）
- 趋势：线性增长
- 预测：按当前速率，热存储将在 32 天后达到 80% 阈值

【冷存储】
- 7 天前：195GB
- 当前：200GB
- 增长量：5GB（日均 0.7GB）
- 趋势：平稳

【建议】
- 短期：热存储增长较快，建议 1 个月内扩容或启用自动冷热分层
- 长期：冷存储增长平稳，暂无压力

如需更多细节，可参考官方存储管理指南：
https://help.aliyun.com/zh/lindorm/user-guide/storage-management

📚 冷热分层配置指南：
https://help.aliyun.com/zh/lindorm/user-guide/hot-and-cold-separation/

需要帮您配置冷热分层策略吗？
```

---

## 存储相关监控指标

### 热存储指标

| 指标名称 | 描述 | 单位 | 告警阈值 |
|----------|------|------|----------|
| `hot_storage_total_bytes` | 热存储总容量 | bytes | - |
| `hot_storage_used_bytes` | 热存储已使用 | bytes | - |
| `hot_storage_used_percent` | 热存储使用率 | % | > 80% |

### 冷存储指标

| 指标名称 | 描述 | 单位 | 告警阈值 |
|----------|------|------|----------|
| `cold_storage_total_bytes` | 冷存储总容量 | bytes | - |
| `cold_storage_used_bytes` | 冷存储已使用 | bytes | - |
| `cold_storage_used_percent` | 冷存储使用率 | % | > 80% |

### 其他存储指标

| 指标名称 | 描述 | 单位 |
|----------|------|------|
| `storage_total_bytes` | 存储空间总量 | bytes |
| `storage_used_bytes` | 存储空间使用量 | bytes |
| `storage_used_percent` | 存储空间使用比例 | % |
| `table_hot_storage_used_bytes` | 宽表热存储使用量 | bytes |
| `table_cold_storage_used_bytes` | 宽表冷存储使用量 | bytes |
| `tsdb_hot_storage_used_bytes` | 时序热存储使用量 | bytes |
| `tsdb_cold_storage_used_bytes` | 时序冷存储使用量 | bytes |

---

## 存储使用率阈值与告警

Lindorm 默认磁盘使用率阈值为 **80%**。

| 存储使用率 | 状态 | 影响 | 建议 |
|-----------|------|------|------|
| < 60% | ✅ 正常 | 无影响 | 持续监控 |
| 60% - 80% | ⚠️ 关注 | 无影响 | 考虑扩容计划 |
| 80% - 90% | ⚠️ 告警 | 写入性能下降 | 尽快扩容或清理数据 |
| 90% - 95% | 🚨 严重告警 | 写入性能严重下降 | 立即扩容或清理数据 |
| ≥ 95% | 🔴 系统禁止写入 | 系统自动禁止数据写入（硬限制） | 必须扩容后才能恢复写入 |

---

## 冷热分层优化建议

### 何时启用冷存储？

| 场景 | 建议 |
|------|------|
| 历史数据访问频率低（< 1 次/天） | 启用冷存储，设置自动冷热分层策略 |
| 热存储使用率 > 60% | 考虑将历史数据迁移到冷存储 |
| 成本优化 | 冷存储成本仅为标准型云存储的 20%（约1/5），适合长期归档 |

### 开通冷存储（容量型云存储）

> ⚠️ **警告**：开通过程中需要**滚动重启实例**，可能会导致部分业务的读写请求出现**延迟波动或连接中断**，建议在**业务低峰期**操作。

**前提条件：**
- 实例存储类型为**本地 HDD 盘**时，**不支持**开通容量型云存储
- 云存储类型（性能型/标准型）实例支持开通

**控制台开通路径：**

1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)
2. 在页面左上角，选择实例所属的**地域**
3. 在实例列表页，单击**目标实例ID**或者目标实例所在行操作列的**管理**
4. 在左侧导航栏，选择**冷存储**
5. 单击**开通**
6. 设置**容量型云存储容量**
7. 阅读并勾选服务协议，单击**立即购买**

**存储类型说明：**

| 存储类型 | 用途 | 是否支持冷热分层 |
|---------|------|-----------------|
| 性能型云存储 | 热存储，低延迟（< 10ms） | ✅ 支持（需开通容量型作为冷存储） |
| 标准型云存储 | 热存储，中等延迟 | ✅ 支持（需开通容量型作为冷存储） |
| 容量型云存储 | 冷存储，低成本（标准型云存储的 20%） | ✅ 作为冷存储介质 |
| 本地 HDD 盘 | 本地存储 | ❌ 不支持冷热分层 |

> **注意**：容量型云存储与性能型/标准型云存储可以**并存**，无需变更现有存储类型。

### 冷热分层策略

- **自动分层**：设置时间策略（如数据写入 30 天后自动转冷）
- **手动分层**：通过 Lindorm 表属性配置冷热分层规则
- **查询优化**：冷数据查询延迟较高（通常 > 100ms），热数据查询延迟低（< 10ms）

📍 配置冷热分层：
1. 通过 Lindorm SQL：
   ```sql
   ALTER TABLE metrics SET COLD_DATA_AGE = 2592000;  -- 30 天后转冷
   ```

2. 通过 HBase Shell：
   ```bash
   alter 'metrics', {NAME => 'cf', COLD_DATA_AGE => 2592000}
   ```

### 冷存储性能说明

| 指标 | 热存储（性能型） | 冷存储（容量型） |
|------|----------------|-----------------|
| 查询延迟 | < 10ms | > 100ms |
| 存储成本 | 基准 | 仅为标准型云存储的 20% |
| 适用场景 | 高频访问 | 低频访问（< 1次/天） |
| 读取 IOPS | 高 | 限流（每 25GiB 容量 1 IOPS） |

如需更多细节，可参考官方配置指南：
https://help.aliyun.com/zh/lindorm/user-guide/hot-and-cold-separation/

📚 冷热分离最佳实践：
https://help.aliyun.com/zh/lindorm/user-guide/enable-cold-storage

---

## 缺参处理

### 缺 instance-id

**追问策略**：先用 `aliyun hitsdb get-instance-summary` 确认地域，再用 `aliyun hitsdb get-lindorm-instance-list --region <region>` 让用户选择实例。

### 缺 时间范围（存储趋势分析）

**默认策略**：使用过去 7 天，并告知用户。

---

## 错误处理

| 错误 | 原因 | 引导用户 |
|------|------|----------|
| **无存储详情** | 实例未开通文件引擎或实例状态异常 | 检查实例状态和引擎配置 |
| **指标无数据** | 时间范围内无数据或指标名错误 | 调整时间范围或确认指标名 |
| **权限不足** | Access Key 无 Lindorm 权限 | 提示需要 `AliyunLindormReadOnlyAccess` 权限 |

---

## 常见场景速查

| 用户描述 | 执行流程 |
|----------|----------|
| "磁盘还剩多少？" | 流程 1：获取存储详情 |
| "存储快满了吗？" | 流程 2：查询存储使用率 |
| "存储增长趋势如何？" | 流程 3：查询存储历史趋势 |
| "冷热存储分别用了多少？" | 流程 1：获取存储详情（区分冷热） |
| "什么时候需要扩容？" | 流程 3：分析增长趋势并预测 |
