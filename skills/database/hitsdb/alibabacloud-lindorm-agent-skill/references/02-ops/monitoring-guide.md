# 监控与报警场景

覆盖 Lindorm 监控数据查询、指标说明和报警配置。

## 触发条件

- "CPU 使用率多少？"
- "最近 3 小时的 CPU 趋势"
- "怎么配置报警？"
- "存储快满了，能设置自动通知吗？"

---

## 查询监控数据

### 查询最新数据

```bash
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name <metric-name> \
    --dimensions '[{"instanceId":"<instance-id>"}]'
```

**返回值说明**：
- `Datapoints` 是 JSON **字符串**（不是数组），需要二次解析
- 每个数据点含 `instanceId`、`host`（节点名，如 table-1/search-1/zk-1）、`userId`、`timestamp`、`Average`/`Maximum`/`Minimum`
- 一个实例会返回**多个数据点**（每个节点一个），需要聚合或筛选 host

### 查询历史趋势

```bash
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name <metric-name> \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<start-time>" \
    --end-time "<end-time>" \
    --period <period>
```

**返回值说明**：
- `Datapoints` 同样是 JSON 字符串，需二次解析
- 按 period 聚合后无 `host` 维度，返回全实例级别的聚合值
- 每个数据点含 `timestamp`、`Average`/`Maximum`/`Minimum`

**参数**：
- `--namespace`：固定 `acs_lindorm`
- `--metric-name`：见下方指标分类，V2 实例部分指标无数据或需换算
- `--dimensions`：JSON 数组格式，必须指定 `instanceId`
- `--start-time` / `--end-time`：时间格式见 SKILL.md →「时间格式」

**period 建议**：

| 时间范围 | period | 说明 |
|---------|--------|------|
| ≤ 1 小时 | 60 | 1 分钟粒度 |
| ≤ 24 小时 | 300 | 5 分钟粒度 |
| > 24 小时 | 3600 | 1 小时粒度 |

**相对时间处理**：用户说"最近 3 小时"时，先执行 `date "+%Y-%m-%d %H:%M:%S"` 获取当前时间，再计算 start/end。默认时间范围：最近 1 小时。

**数据保留**：云监控最多保留 30 天，更长周期需开通日志服务存储。

---

## 指标说明

> 统一使用**无前缀指标**（如 `cpu_idle`），兼容性最佳。`lindorm_multi_` 前缀指标仅 `lindorm_multizone` 实例可用，其他实例类型不可用。

### CPU 指标

| 指标 | 描述 | 单位 | 正常范围 | 告警阈值 |
|------|------|------|---------|---------|
| `cpu_idle` | CPU 空闲率 | % | > 20% | < 20% |
| `cpu_user` | CPU 用户使用率 | % | < 80% | > 80% |
| `cpu_system` | CPU 系统使用率 | % | < 30% | > 30% |
| `cpu_wio` | CPU IO 等待 | % | < 30% | > 30% |

CPU 空闲率 < 20%：CPU 瓶颈；cpu_wio > 30%：磁盘 IO 瓶颈

> **CPU + Load 综合判断**：Load > CPU 核数 = 处理排队、亚健康状态；CPU 利用率不高但 Load 偏高 = 磁盘使用率过高（与 cpu_wio 配合判断）

### 内存指标

| 指标 | 描述 | 单位 | V1 | V2 |
|------|------|------|----|----|
| `mem_used_percent` | 内存使用率 | % | ✅ | ⚠️ 无数据 |
| `mem_total` | 内存总量 | bytes | ✅ | ✅ |
| `mem_free` | 空闲内存 | bytes | ✅ | ✅ |
| `mem_buff_cache` | 缓存大小 | bytes | ✅ | ✅ |

V2 内存使用率需用 `1 - mem_free / mem_total` 计算。

> **Java 内存特性**：Lindorm 与 HBase 均为 Java 实现，70%-85% 内存使用率是健康常态（JVM BlockCache/MemStore/HDFS 页缓存），92% 以上才需关注。不建议对 80% 设置报警。
>
> **宽表引擎堆内存报警**：宽表计算节点内存使用比率 ≥ 85%~90% 且持续 30~60 分钟时建议报警。堆内存短期波动是正常的（GC 会回收），只有持续过高才需关注。

### QPS 指标

| 指标 | 描述 | 单位 |
|------|------|------|
| `read_ops` | 读请求量 | ops/s |
| `write_ops` | 写请求量 | ops/s |
| `get_num_ops` | Get 每秒请求数 | ops/s |
| `put_num_ops` | Put 每秒请求数 | ops/s |
| `scan_num_ops` | Scan 每秒请求数 | ops/s |

> **QPS 指标解读**：
> - BatchGet 无论包含多少行都只算一次点查调用，因此使用 BatchGet 时 avg RT 会高于单行 Get
> - Scan 请求会被拆分为子调用以流式返回，Scan QPS ≠ 实际 Scan 请求数，Scan RT 是每个子调用的平均耗时

### 延迟指标

| 指标 | 描述 | 单位 | 正常范围 | 告警阈值 | V2 |
|------|------|------|---------|---------|-----|
| `read_rt` | 读平均延迟 | ms | < 10ms | > 50ms | ✅ |
| `write_rt` | 写平均延迟 | ms | < 10ms | > 50ms | ✅ |
| `get_rt_avg` | Get 平均延迟 | ms | < 10ms | > 50ms | ✅ |
| `put_rt_avg` | Put 平均延迟 | ms | < 10ms | > 50ms | ✅ |
| `get_rt_p99` | Get P99 延迟 | ms | < 50ms | > 100ms | ⚠️ 无数据 |
| `put_rt_p99` | Put P99 延迟 | ms | < 50ms | > 100ms | ⚠️ 无数据 |
| `scan_rt_avg` | Scan 平均延迟 | ms | < 50ms | > 200ms | ✅ |
| `scan_rt_p99` | Scan P99 延迟 | ms | < 200ms | > 500ms | ✅ |

### 存储指标

| 指标 | 描述 | 单位 | 告警阈值 | V2 |
|------|------|------|---------|-----|
| `hot_storage_used_percent` | 热存储使用率 | % | > 80% | ⚠️ 无数据 |
| `hot_storage_used_bytes` | 热存储使用量 | bytes | — | ✅ |
| `cold_storage_used_percent` | 冷存储使用率 | % | > 80% | ⚠️ 无数据 |
| `cold_storage_used_bytes` | 冷存储使用量 | bytes | — | ✅ |
| `storage_used_percent` | 总存储使用率 | % | > 80% | ⚠️ 无数据 |
| `storage_used_bytes` | 总存储使用量 | bytes | — | ✅ |

V2 存储使用率需通过 `get-lindorm-v2-storage-usage` API 获取，云监控无数据。

> ⚠️ **存储硬限制**：热存储或冷存储水位 ≥ 95% 时，系统自动禁止数据写入。建议容量告警线设置在 75%~80%，提前扩容避免影响业务。

### 网络与负载指标

| 指标 | 描述 | 单位 |
|------|------|------|
| `bytes_in` | 网络流入 | bytes/s |
| `bytes_out` | 网络流出 | bytes/s |
| `load_one` | 1 分钟平均负载 | — |
| `load_five` | 5 分钟平均负载 | — |
| `handler_queue_size` | Handler 队列长度 | — |
| `compaction_queue_size` | Compaction 队列长度 | — |

> **Compaction 队列判断**：长期稳定在某值 = 健康（白天高峰积压、晚上低谷自动处理是正常周期）；持续上涨且无下降趋势 = 资源不足需扩容。长期积压会导致文件数增多、读 RT 升高，严重时出现反压写导致写 RT 增加甚至超时。

> **网络/磁盘限流**：不同规格实例有不同的网络带宽和磁盘 IOPS 上限（参见[实例规格族](https://help.aliyun.com/zh/lindorm/product-overview/instance-types)和[块存储性能](https://help.aliyun.com/zh/block-storage/product-overview/block-storage-performance)），读写流量超过云盘带宽上限会限流导致业务受损。

### 引擎专用指标

| 引擎 | 指标前缀 | 关键指标 |
|------|---------|---------|
| LSQL（宽表SQL） | `lql_` | `lql_select_ops`、`lql_upsert_ops`、`lql_select_avg_rt`、`lql_select_p99_rt`、`lql_connection` |
| 搜索引擎 | `search_` | `search_cpu_idle`、`search_mem_used_percent`、`search_select_1minRate`、`search_select_p99_rt` |
| 时序引擎 | `tsdb_` | `tsdb_datapoints_added`、`tsdb_disk_used`、`tsdb_jvm_used_percent` |
| 文件引擎 | `Lindorm_File_` | `Lindorm_File_ReadBandwidth`、`Lindorm_File_WriteBandwidth`、`Lindorm_File_ReadLatency`、`Lindorm_File_WriteLatency` |

引擎专用指标需对应引擎已开通才返回数据。完整 323 个指标可通过 `aliyun cms describe-metric-meta-list --namespace acs_lindorm` 查询。

### 业务词到指标映射

| 用户说 | 指标 |
|--------|------|
| CPU 使用率 | `cpu_idle`（空闲率，使用率 = 100 - cpu_idle） |
| 内存使用率 | `mem_used_percent`（V1）/ `1 - mem_free / mem_total`（V2） |
| QPS | `read_ops` + `write_ops` |
| 延迟/RT | `read_rt` 或 `write_rt` |
| P99 延迟 | `get_rt_p99` / `put_rt_p99`（V1）/ —（V2 无数据） |
| 存储使用率 | `hot_storage_used_percent`（V1）/ `get-lindorm-v2-storage-usage` API（V2） |
| 网络流量 | `bytes_in` + `bytes_out` |
| 负载 | `load_one` |

---

## 宽表引擎指标解读

### Region 数量建议

每个 Region 都占用元数据内存，数量过多会导致内存不足。

| 机器内存 | 单机建议 Region 数 |
|---------|-------------------|
| 8 GB | < 500 |
| 16 GB | < 1000 |
| 32 GB | < 2000 |
| 64 GB | < 3000 |
| 128 GB | < 5000 |

可通过宽表计算节点内存使用量 / 内存总量判断是否存在内存不足问题。减少 Region 数的方法：减少表数量、减少建表时预分区个数。

### 其他宽表指标解读

| 指标 | 含义 | 判断 |
|------|------|------|
| HandlerQueue 长度 | 请求排队数 | > 0 = 请求排队，服务器资源无法承载当前请求量，建议升级配置增加 CPU |
| Compaction 队列长度 | Compaction 任务排队数 | 长期稳定某值 = 健康；持续上涨 = 资源不足需扩容。长期积压会导致文件数增多、读 RT 升高，严重时反压写导致写 RT 增加甚至超时 |
| Region 平均文件数 | 分片内平均文件数 | 越多读 RT 越大；文件总数过多可能导致 Full GC 或 OOM |
| Region 最大文件数 | 单 Region 最大文件数 | 超限会反压写导致写超时（具体限制见[数据请求的限制](https://help.aliyun.com/zh/lindorm/product-overview/quotas-and-limits#p-fq0-foz-ocy)） |
| 写流量（KB/s） | 写入宽表引擎的流量 | 列转 KeyValue 形式，实际写入量大于业务写入量。写入吞吐过大可能导致 Compaction 积压 |

### 写入吞吐建议

写入吞吐过大可能导致 Compaction 积压，影响实例稳定性。

| 配置 | 建议写入吞吐 |
|------|-------------|
| 4C8G | < 5 MB/s |
| 8C16G | < 10 MB/s |
| 16C32G | < 30 MB/s |
| 32C64G | < 60 MB/s |

实际使用时结合 `compaction_queue_size` 和 Region 平均文件数综合判断。

---

## 报警配置

**⚠️ 安全边界：Agent 只查询数据、提供建议，不直接创建报警规则**（涉及联系人手机号/邮箱等敏感信息且需验证）

### 报警规则类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **阈值报警** | 指标数值越界触发 | CPU 使用率 > 80% 持续 5 分钟 |
| **事件报警** | 系统事件触发 | NodeDown（节点宕机）、RegionError（Region 异常） |

事件报警无法通过指标阈值捕获，是运维关键能力。

### 配置路径

1. **Lindorm 控制台**：实例详情 → 告警管理 → 创建报警规则
2. **云监控控制台**：报警服务 → 报警规则 → 创建报警规则 → 选择产品"Lindorm"

### 报警规则关键参数

| 参数 | 说明 | 可选值 |
|------|------|--------|
| 统计周期 | 数据聚合粒度 | 60s / 300s / 900s / 1800s / 3600s / 86400s |
| 统计方法 | 数据聚合方式 | Average / Maximum / Minimum / Sum |
| 比较运算符 | 阈值比较方式 | >= / > / <= / < / != |
| 连续次数 | 连续满足条件的次数 | 1-100（推荐 1-3） |
| 静默期 | 触发后的通知静默时间 | 5min - 24h |
| 报警级别 | 三级独立阈值 | Critical / Warn / Info |

> **cpu_idle 报警方向**：cpu_idle 是空闲率，报警条件应设为 `cpu_idle ≤ 阈值`（即使用率 ≥ 100 - 阈值）

### 推荐阈值

| 指标 | V1 | V2 | Info（提醒） | Warn（警告） | Critical（严重） |
|------|----|----|-------------|-------------|----------------|
| CPU 使用率 | `cpu_idle ≤ 30` | `cpu_idle ≤ 30` | ≤ 30%（持续 30min） | ≤ 20%（持续 5min） | ≤ 5%（持续 3min） |
| 内存使用率 | `mem_used_percent` | `1 - mem_free/mem_total` | ≥ 85%（持续 30min） | ≥ 92%（持续 5min） | — |
| 热存储使用率 | `hot_storage_used_percent` | `get-lindorm-v2-storage-usage` API | ≥ 70% | ≥ 80% | ≥ 90% |
| P99 延迟 | `get_rt_p99` | —（无数据） | ≥ 50ms | ≥ 100ms | ≥ 200ms |

> V2 存储报警：云监控无 `hot_storage_used_percent` / `storage_used_percent` 数据，需通过 `get-lindorm-v2-storage-usage` API 获取，或在控制台配置基于存储空间的报警规则。

### 通知渠道

| 渠道 | 说明 | 适用级别 |
|------|------|---------|
| 短信 | 手机号需验证 | Warn / Critical |
| 邮件 | 邮箱需验证 | Info / Warn / Critical |
| 钉钉 | 群机器人 Webhook | Warn / Critical |
| 电话 | 语音报警 | Critical |
| Webhook | 自定义 HTTP 回调 | 全级别 |
| 阿里云 App | App 内推送 | Info / Warn / Critical |

联系人管理路径：云监控控制台 → 通知管理 → 联系人/联系组

### 常见报警问题

- **未收到通知**：检查联系人是否已验证、报警条件是否真正触发、通知时段是否覆盖、通知策略是否关联规则
- **报警过多**：提高阈值、增加持续时间、配置静默期（5min-24h）、使用复合条件（多指标同时满足才报警）

---

## 错误处理

| 错误 | 原因 | 引导 |
|------|------|------|
| 无数据点 | 时间范围内实例未运行或无流量 | 调整时间范围或检查实例状态 |
| 权限不足 | AK 无云监控权限 | 需要 `AliyunCloudMonitorReadOnlyAccess` |
| 指标不存在 | 指标名错误或该实例类型不支持 | 先验证指标可用性 |

---

## 官方文档

- 报警配置：https://help.aliyun.com/zh/lindorm/user-guide/manage-alerts
- 创建报警规则：https://help.aliyun.com/zh/lindorm/user-guide/create-an-alert-rule
- 监控指标说明：https://help.aliyun.com/zh/lindorm/user-guide/instance-monitoring
- 监控报警最佳实践：https://help.aliyun.com/zh/lindorm/user-guide/monitoring-alarm-best-practices

---

## 关联场景

- 性能诊断后排查具体慢SQL → `slow-query-analysis.md`
- 存储分析 → `storage-analysis.md`
- 扩缩容 → `instance-management.md`