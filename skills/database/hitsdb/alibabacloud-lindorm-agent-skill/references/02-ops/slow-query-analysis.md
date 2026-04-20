# 慢查询分析场景

当用户询问"有没有慢查询"、"查询慢是什么原因"、"怎么优化查询"、"怎么开启慢日志"时，按本指南执行。

## 触发条件

用户的典型表达：
- "有没有慢查询日志？"
- "怎么开启慢日志/慢查询记录"
- "查询慢，帮我分析原因"
- "Top 10 最慢的查询"
- "怎么优化查询性能？"

## 核心原则

**证据驱动的诊断流程**：
1. **先收集最小必要信息**（引擎类型、时间窗口、操作类型）
2. **用监控确认现象**（延迟指标趋势）
3. **要求用户提供证据**（慢 SQL、执行计划、慢日志）
4. **基于证据给针对性建议**（而非通用优化大全）
5. **提供可执行的优化代码**（从官方文档提取最佳实践）

> ⚠️ **禁止行为**：在缺少具体慢 SQL/执行计划/慢日志证据时，直接给出"5 类优化方案"或概率判断。

---

## 慢查询日志管理

> **版本要求**：
> - 实时定位/终止慢查询：宽表引擎 **2.6.3+**，Lindorm SQL **2.6.6+**
> - 慢查询回溯（慢日志记录）：宽表引擎 **2.8.2.13+**
>
> 以下 SQL 均通过 Lindorm SQL 客户端执行（MySQL Workbench / DBeaver / Navicat / ClusterManager 均可），**立即生效，无需重启实例**。

### 1. 实时定位当前慢查询

```sql
-- 查看当前正在执行的所有查询（含查询 ID / UUID）
SHOW PROCESSLIST;
```

**说明**：返回结果中的 `ID` 字段为 UUID，用于后续终止操作。

### 2. 终止慢查询

```sql
-- 终止指定查询（ID 从 SHOW PROCESSLIST 获取）
KILL QUERY '581f9ab8-68af-4c93-b73a-eb99679ed192';
```

### 3. 开启慢查询回溯（Slow Log 记录）

**Step 1：开启功能**
```sql
ALTER SYSTEM SET SLOW_QUERY_RECORD_ENABLE = true;
```

**Step 2：设置慢查询阈值（单位：毫秒）**
```sql
-- 示例：超过 10 秒记录（按业务需要调整，不建议设置过小）
ALTER SYSTEM SET SLOW_QUERY_TIME_MS = 10000;
```

**Step 3：查询慢日志视图**
```sql
-- 查看最近 10 条慢查询
SELECT * FROM lindorm._slow_query_ LIMIT 10;

-- 按时间筛选（query_start_time 为 Unix 毫秒时间戳）
SELECT COUNT(sql_query_s) AS num
FROM lindorm._slow_query_
WHERE query_start_time >= 1680152319000;
```

**慢日志视图字段说明**：

| 字段名 | 说明 |
|--------|------|
| `query_start_time` | 查询请求的发起时间（Unix 毫秒时间戳） |
| `query_id` | 查询请求 ID |
| `sql_query_id` | 查询请求的 SQL 语句（无 SQL 则为空） |
| `sql_query_s` | SQL 语句内容（无 SQL 则为空） |
| `duration_i` | 查询执行时间 |
| `status_s` | 查询最终状态（成功/失败） |
| `ip_s` | 发送查询请求的 IP 地址 |
| `server_s` | 查询执行的节点 |
| `query_s` | 执行的内部查询请求语句 |

> ⚠️ **注意事项**：
> - 慢日志记录默认只保留 **1 小时**
> - 频繁记录慢查询对实例性能有一定影响，性能敏感场景不宜将阈值设置过小
> - 视图名 `lindorm._slow_query_` 固定，不可修改

**官方文档**：https://help.aliyun.com/zh/lindorm/developer-reference/slow-query-diagnostics

---

## 执行流程

### Step 0：强制收集最小信息（缺参则追问，不下结论）

**必须确认的信息**：

| 信息项 | 为什么必须 | 追问话术 |
|--------|-----------|---------|
| **引擎类型** | 宽表 SQL / HBase API / 时序 / 搜索引擎的优化策略完全不同 | "您使用的是哪个引擎？宽表 SQL、HBase API、时序引擎还是搜索引擎？" |
| **发生时间窗口** | 需要确定查询趋势和关联事件 | "慢查询大概从什么时候开始？持续多久了？" |
| **慢的操作类型** | 读/写/Scan/聚合的排查方向不同 | "是查询慢还是写入慢？具体的操作类型是什么？" |
| **具体 SQL/操作**（如有） | 没有具体语句无法给出针对性建议 | "能否提供一条具体的慢 SQL 或操作代码？" |

**缺参时的标准回复**：
```
我需要先了解一些信息，才能帮您准确诊断：

1. 您使用的是哪个引擎？（宽表 SQL / HBase API / 时序 / 搜索）
2. 慢查询大概从什么时候开始？
3. 是读操作慢还是写操作慢？
4. 能否提供一条具体的慢 SQL 或操作示例？

有了这些信息，我可以帮您：
- 查询相关监控指标确认问题
- 分析具体的执行计划
- 给出针对性的优化建议
```

---

### Step 1：用监控确认现象（avg vs p99 + 趋势）

**Agent 先查询延迟指标**：

```bash
# P99 延迟（更能反映慢请求）
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name get_rt_p99 \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<start 格式: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<end 格式: YYYY-MM-DD HH:MM:SS>" \
    --period 60

# 平均延迟
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name read_rt \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<start 格式: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<end 格式: YYYY-MM-DD HH:MM:SS>" \
    --period 60
```

**Agent 分析后给客观描述**（不下结论、不给概率）：

```
【延迟指标观察】实例 ld-xxx（最近 1 小时）

- 平均延迟：35ms
- P99 延迟：180ms
- P99 与平均值差距：5.1 倍

【客观描述】
延迟分布存在明显长尾，部分请求耗时显著高于平均水平。

【下一步】
要确定具体原因，需要查看具体的慢查询证据。请选择以下任一方式：

方式 1（推荐）：提供具体慢 SQL
- 如果您知道哪条 SQL 慢，请提供 SQL 文本
- 我可以帮您分析执行计划

方式 2：查看 ClusterManager 慢查询日志
- 路径：控制台 → 实例 → ClusterManager → 查询分析 → 慢查询日志
- 找到 Top 慢查询后告诉我查询特征

方式 3：提供应用侧观察
- 您的应用日志中是否有具体报错或超时的操作？
```

---

### Step 2：要求用户提供证据（满足其一即可）

**证据类型**（至少提供一种）：

| 证据类型 | 适用场景 | 如何获取 |
|---------|---------|---------|
| **慢 SQL + EXPLAIN** | 宽表 SQL 慢查询 | 用户提供 SQL 文本，Agent 指导执行 EXPLAIN |
| **ClusterManager 慢日志** | 所有引擎 | 控制台 → ClusterManager → 查询分析 → 慢查询日志 |
| **HBase Scan/Get 参数** | HBase API 慢查询 | 用户提供代码中的 Scan/Get 配置 |
| **应用错误日志** | 有明确报错场景 | 应用侧的超时/错误日志 |

**未提供证据时的标准回复**：
```
目前我能看到延迟分布存在长尾，但无法确定具体原因。

请提供以下任一证据，我才能给出针对性优化建议：

选项 A：一条具体的慢 SQL（如果您知道是哪条）
选项 B：ClusterManager 中的 Top 慢查询截图/文本
选项 C：您的应用日志中相关的错误信息

⚠️ 注意：在没有具体证据的情况下，我不建议直接应用通用优化方案，
因为不同原因（全表扫描、热点、大查询等）的优化方向可能完全不同。
```

---

### Step 3：基于证据分类输出（只给命中的 1-2 条策略）

**收到证据后，根据证据类型选择对应优化方向**：

| 证据特征 | 问题类型 | 优化方向 |
|---------|---------|----------|
| EXPLAIN 显示 TABLE FULL SCAN，扫描行数大（> 100万） | 全表扫描 | 添加 RowKey 范围条件、创建二级索引 |
| 单行查询耗时长，返回数据量大（> 1MB） | 查询大量列 | 只 SELECT 需要的列，避免 `SELECT *` |
| 少量 RowKey 延迟极高，CPU 节点分布不均 | RowKey 热点 | RowKey 加盐/反转分散，创建全局索引 |
| 批量 Get/Scan 超时或内存溢出 | 大数据量批量查询 | 分批查询（batchSize 50-100），SQL 用 LIMIT 分页 |
| 查询非主键列性能极差，随数据量线性变慢 | 缺少索引 | 创建二级索引（`CREATE INDEX`）或全局索引（`CREATE GLOBAL INDEX`） |

> 根据用户提供的证据，**只输出命中的 1-2 条策略**，并给出对应的可执行 SQL/代码示例。

---

### Step 4：告知用户如何获取证据（如用户无法提供）

**给出精确路径，不让用户自己摸索**：

```
【查看具体慢查询日志】

虽然我已给您提供了通用优化方案，但如果您想查看**具体哪条查询最慢**，
请通过 ClusterManager 查看：

📍 确路径：
1. 登录控制台：https://lindorm.console.aliyun.com/
2. 点击实例 ID "ld-xxx" 进入实例详情
3. 左侧菜单：数据库连接 → 点击"通过 ClusterManager 访问"
4. 进入 ClusterManager → 查询分析 → 慢查询日志
5. 查看：
   - Top 10 最慢查询
   - 查询耗时、扫描行数
   - 查询发生时间

【查看到慢查询后】
告诉我具体的查询类型（Scan/Get/RowKey 特征），我来给出针对性优化方案。

📚 ClusterManager 使用文档：
https://help.aliyun.com/zh/lindorm/user-guide/log-in-to-the-cluster-management-system
```

---

### Step 5：综合性能诊断（有证据后）

**Agent 结合延迟指标 + CPU/内存/QPS，给出综合诊断**：

```bash
# 查询 CPU 空闲率
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"<instance-id>"}]'

# 查询内存使用率
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name mem_used_percent \
    --dimensions '[{"instanceId":"<instance-id>"}]'

# 查询 QPS
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name read_ops \
    --dimensions '[{"instanceId":"<instance-id>"}]'
```

**有证据后的综合分析示例**：

```
【综合诊断】实例 ld-xxx（最近 1 小时）

📊 性能指标：
- P99 延迟：180ms
- 平均延迟：35ms
- P99/avg 倍数：5.1x
- CPU 空闲率：65%
- 内存使用率：55%

🔍 用户提供的证据：
- 引擎类型：宽表 SQL
- 慢 SQL：SELECT * FROM orders WHERE status = 'pending'
- EXPLAIN 显示：TABLE FULL SCAN

✅ 诊断结论：
全表扫描导致的慢查询。表 orders 没有 status 列的索引，
查询需要扫描全表。

💡 针对性优化方案：
1. 【推荐】创建二级索引：
   CREATE INDEX idx_status ON orders(status) INCLUDE (order_id, amount);

2. 【临时】限制返回行数：
   SELECT * FROM orders WHERE status = 'pending' LIMIT 100;

3. 【长期】如 status 选择性低，考虑使用搜索索引支持多条件查询

请确认优化方案后，我可以提供完整的执行语句。
```

---

## 优化方案参考

当用户提供了具体证据后，Agent 从以下官方文档提取针对性优化建议：

| 证据类型 | 参考文档 | 提取内容 |
|---------|---------|---------|
| 全表扫描 | [SQL 常见问题](https://help.aliyun.com/zh/lindorm/developer-reference/sql-faq) | 低效查询规避、索引使用、最左匹配原则 |
| 热点问题 | [如何设计宽表主键](https://help.aliyun.com/zh/lindorm/user-guide/how-to-design-the-rowkey-field) | 加盐、反转、分区策略、避免热点 |
| 大查询 | [游标分页](https://help.aliyun.com/zh/lindorm/introduction-to-the-use-of-cursor-paging) | LIMIT 分页、游标分页、避免内存溢出 |
| 索引选择 | [二级索引](https://help.aliyun.com/zh/lindorm/user-guide/high-performance-native-secondary-indexes) | 二级索引 vs 搜索索引选择 |

> **原则**：只提取与用户证据匹配的方案，不要一次性给出所有优化方案。

---

## 官方文档索引（供 Agent 参考）

| 场景 | 官方文档 | 预期提取内容 |
|------|---------|-------------|
| **慢查询诊断** | [慢查询诊断](https://help.aliyun.com/zh/lindorm/developer-reference/slow-query-diagnostics) | 慢查询定位方法、诊断工具、优化建议 |
| **二级索引** | [二级索引](https://help.aliyun.com/zh/lindorm/user-guide/high-performance-native-secondary-indexes) | 索引类型、创建语法、使用场景 |
| **全局索引** | [CREATE INDEX](https://help.aliyun.com/zh/lindorm/developer-reference/te-create-index) | GLOBAL 关键字、索引类型区别、语法参数 |
| **主键/RowKey 设计** | [如何设计宽表主键](https://help.aliyun.com/zh/lindorm/user-guide/how-to-design-the-rowkey-field) | 加盐、反转、分区策略、避免热点 |
| **索引创建总览** | [CREATE INDEX 索引对比](https://help.aliyun.com/zh/lindorm/developer-reference/te-create-index) | 二级索引 vs 搜索索引 vs 列存索引选择 |
| **ClusterManager** | [ClusterManager 使用](https://help.aliyun.com/zh/lindorm/user-guide/log-in-to-the-cluster-management-system) | 访问路径、慢查询日志查看 |