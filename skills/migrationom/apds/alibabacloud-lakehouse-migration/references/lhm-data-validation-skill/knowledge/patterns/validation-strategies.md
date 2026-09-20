# 校验方案推荐规则

## 1. 校验算法选择规则

校验算法的选择取决于两端方言的能力交集，读取 `knowledge/dialects/` 中两端方言的档案后按以下规则决策：

| 场景 | 推荐算法 | 判断依据 |
|------|---------|---------|
| 两端均支持 CRC32 且实现兼容 | MD5 或 CRC32 | 对比两端 dialect 档案中 CRC32 行 |
| 任一端 CRC32 不兼容或不可用 | 仅用 MD5 | 如 Redshift（非标准多项式）、PG 系（不支持）、ClickHouse（返回类型不同）、BigQuery（不支持） |
| 两端 LENGTH 行为不同 | 注意字符数 vs 字节数 | 如 Impala LENGTH 返回字节数，其他方言返回字符数 |

### 常见方言组合速查

| 组合类型 | 弱内容校验算法 | 说明 |
|---------|-------------|------|
| Hive 族 ↔ MaxCompute | MD5 或 CRC32 均可 | CRC32 标准实现，全兼容 |
| Hive 族 ↔ Hive 族 | MD5 或 CRC32 均可 | 同族方言行为一致 |
| 任意 ↔ PG 族 | 仅 MD5 | PG 系不支持 CRC32 |
| 任意 ↔ Redshift | 仅 MD5 | Redshift CRC32 非标准 |
| 任意 ↔ ClickHouse | 仅 MD5 | ClickHouse CRC32 返回类型不同 |
| 任意 ↔ BigQuery | 仅 MD5 | BigQuery 不支持 CRC32 |
| MySQL 族 ↔ Hive 族 | MD5 或 CRC32 均可 | 全兼容 |

## 2. 按表特征推荐

| 表特征 | 推荐校验类型 | 分片策略 | 理由 |
|--------|-------------|---------|------|
| 字段数 < 10，无复杂类型 | COUNT + CHECKSUM(MD5) | 按分区 | 快速 + 准确 |
| 字段数 > 50，含 DECIMAL | COUNT + METRIC(MIX) + CHECKSUM(MD5) | 按分区 | MIX 模板覆盖最全 |
| 含 ARRAY/MAP/STRUCT | COUNT + METRIC + 自定义指标 | 按分区 | 复杂类型 CRC32 可能不兼容，需自定义指标展开 |
| 分区表（分区数 > 100） | COUNT + CHECKSUM（按分区分片） | PartitionChunk | 分片并行提升速度 |
| 大表（行数 > 1 亿） | COUNT + METRIC（抽样） | RangeChunk | 全量 CHECKSUM 耗时过长 |
| 无主键表 | COUNT + METRIC | — | 无法做全文比对 |

## 3. 按业务场景推荐

| 场景 | 推荐方案 | 阈值建议 | 说明 |
|------|---------|---------|------|
| 湖仓首次迁移（Hive→MC） | 三层递进（COUNT→METRIC→CHECKSUM） | 严格（100%） | 全量验证，CRC32 和 MD5 均可用 |
| 湖仓增量同步 | COUNT + METRIC | 宽松（97%） | 关注趋势，按分区分片 |
| 数仓入湖（Redshift→MC） | COUNT + METRIC + CHECKSUM(MD5) | 严格（100%） | 注意禁用 CRC32 |
| 定期巡检 | COUNT + METRIC（核心表） | 中等（99%） | 成本效益平衡 |
| 问题排查 | METRIC（自定义表达式） | 严格（100%） | 聚焦特定字段的聚合指标 |

## 4. 校验类型说明

| 校验类型 | 说明 | 适用场景 | 耗时 |
|---------|------|---------|------|
| 数据量校验 | 比对源端/目标端行数 | 快速筛查数据丢失/多余 | 分钟级 |
| 指标校验 | 比对 SUM/AVG/MIN/MAX/COUNT 等聚合指标 | 验证数据内容一致性 | 十分钟级 |
| 弱内容校验 | 逐行 MD5/CRC32 哈希比对 | 精确到行级的内容验证 | 小时级 |

> 全文比对、自定义SQL、空值率比对当前不支持。

## 5. 字段过滤策略

### 场景：排除特定类型字段

当用户说"时间戳/日期字段不用校验"时：

**方案 A：模板级排除（推荐）**
- 在指标校验模板中，不为 DATE 类型（dataTypeGroup=4）配置 metricRule
- 效果：所有 DATE/TIMESTAMP 类型的字段不参与指标校验

**方案 B：表级列选择**
- 在任务配置中，sourceColumns/targetColumns 只列出需要校验的列
- 效果：只有指定列参与校验
- 适用：表数量少、列名明确的场景

### 场景：MAP/ARRAY/STRUCT 复杂类型导致 GROUP BY 报错

MIX 模板（1001）会自动对表中所有字段生成 GROUP BY 聚合 SQL。**MAP、ARRAY、STRUCT 等复杂类型字段无法参与 GROUP BY**，会导致：
```
ODPS-0130071: column <col_map> should appear in GROUP BY key or be used in an aggregate function
```

**解决方法**：通过 sourceColumns/targetColumns 显式指定要校验的字段，排除复杂类型字段。

### 场景：自定义聚合字段需要服务代理

在 sourceColumns/targetColumns 中指定自定义聚合字段（如 `max(ifNull(id,0)) AS max_id`）时，系统需通过服务代理拉取客户侧表元数据。
- 如果服务代理未安装或不在线，返回 `E002R901: Agent is not active`
- 解决：前往控制台「迁移准备 → 资源组与服务代理 → 服务代理」安装
- 不指定自定义字段时使用模板默认聚合，无需服务代理

**方案 C：模板级列名排除**
- 在 metricRule 的 filterColumnName 中填入要排除的列名（逗号分隔）
- 效果：匹配列名的字段被跳过
- 适用：排除特定列名（如 create_time, update_time）

## 6. 差异容忍率配置

### threshold vs diffTolerateValues 的区别

| 配置项 | 含义 | 作用维度 | 值域 |
|--------|------|---------|------|
| threshold | 一致率阈值（多少行一致算通过） | 全局/表级 | 0-100（百分数） |
| diffTolerateValues | 指标值容忍率（SUM/AVG 差多少算通过） | 模板级/按聚合方法 | 小数（0.03 = 3%） |

### 常见客户表述 → 配置映射

| 客户说 | 应配置 | 值 |
|--------|--------|-----|
| "容忍 3% 的差异" | threshold | 97.0 |
| "指标值允许 3% 偏差" | diffTolerateValues | {"SUM": 0.03, "AVG": 0.03} |
| "DECIMAL 容忍 3%，其他精确" | 拆两个任务 | 任务 1: threshold=100(非DECIMAL), 任务 2: threshold=97(DECIMAL) |

### threshold=0.0 陷阱

threshold 传 0.0 会导致所有校验都判定为 PASSED（因为一致率 >= 0 永远成立）。
正确做法：不传 threshold（使用默认精确匹配）或传 100。
指标校验的 threshold 默认不传（None），由系统使用默认值。

## 7. MaxCompute 分区表注意事项

MaxCompute 分区表必须设置 global_params：
```
source_global_params = "odps.sql.allow.fullscan=true"
```
否则 MaxCompute 会拒绝全表扫描查询，导致校验失败。

## 8. 分块机制

校验任务在规划阶段会自动决定是否将大表拆分为多个分片（chunk）并行执行。**分块策略完全由系统自动决策，客户无需配置。**

### 当前实现

| 表类型 | 分块行为 | 说明 |
|--------|---------|------|
| 分区表 | 按分区分块（PartitionChunkProcessor） | 每个分区生成一个独立的校验步骤，并行执行 |
| 非分区表 | 不分块，整表校验 | 单步执行 |

### 对客户的影响

- **分区表校验耗时与分区数成正比**：分区越多，生成的校验步骤越多，但并行执行可加速
- **配合 ScopeFilter 可控制校验范围**：对分区数 > 1000 的大分区表，建议配置 ScopeFilter（如 LAST_N_PARTITION）只校验最近分区
- **分区倾斜风险**：如果某些分区数据量极大，可能导致整体耗时受最慢分区影响

### 注意事项

- 客户不需要（也无法）选择分块策略，系统自动处理
- 推荐方案时只需关注"是否需要配置 ScopeFilter 来控制分区范围"
- 非分区表的校验没有分片机制，大表校验可能耗时较长

## 9. ScopeFilter 增量分区过滤

### 用途

增量校验场景下，不需要校验全部分区，只需校验最近新增或修改的分区。ScopeFilter 自动筛选符合条件的分区参与校验。

### 5 种过滤类型

| 类型代码 | 名称 | 说明 | 参数 |
|---------|------|------|------|
| 0 | NONO（不筛选） | 校验所有分区 | 无 |
| 1 | LAST_N_PARTITION | 校验最近 N 个分区（按创建时间倒序） | `lastN`: 分区数量 |
| 2 | LAST_N_DAY | 校验最近 N 天内创建的分区 | `lastN`: 天数 |
| 3 | BY_MODIFY_TIME | 校验数据修改时间在指定范围内的分区 | `start` + `end`: 时间范围（yyyy-MM-dd HH:mm） |
| 4 | BY_CREATE_TIME | 校验创建时间在指定范围内的分区 | `start` + `end`: 时间范围（yyyy-MM-dd HH:mm） |

### 数据源支持矩阵

ScopeFilter 的可用性受**两层限制**：元数据 SDK 能否获取分区时间 + Worker 白名单是否放行。

#### 元数据 SDK 实际能力（teleport-meta）

| 数据源 | partitionCreateTime | partitionModifiedTime | 可用的过滤类型 |
|--------|-------------------|---------------------|--------------|
| MaxCompute | ✅ `getCreatedTime()` | ✅ `getLastDataModifiedTime()` | 1/2/3/4 全部 |
| Hive (Thrift) | ✅ `getCreateTime()` | ✅ `transient_lastDdlTime` | 1/2/3/4 全部 |
| Hive (MySQL) | ✅ `CREATE_TIME` | ✅ `transient_lastDdlTime` | 1/2/3/4 全部 |
| AWS Glue | ✅ `creationTime()` | ✅ `transient_lastDdlTime` | 1/2/3/4 全部 |
| DLF | ✅ `getCreatedAt()` | ✅ `getUpdatedAt()` | 1/2/3/4 全部 |
| StarRocks | ❌ null | ✅ `VisibleVersionTime` | 仅 3（BY_MODIFY_TIME） |
| ClickHouse | ❌ null | ✅ `modification_time` | 仅 3（BY_MODIFY_TIME） |
| BigQuery | ❌ null | ✅ `last_modified_time` | 仅 3（BY_MODIFY_TIME） |
| PostgreSQL | ❌ null | ❌ null | 不可用 |
| ADBPG | ❌ null | ❌ null | 不可用 |
| GaussDB | ❌ null | ❌ null | 不可用 |
| Hologres | ❌ null | ❌ null | 不可用 |
| Redshift | ❌ null | ❌ null | 不可用 |
| Azure Synapse | ❌ null | ❌ null | 不可用 |
| Databricks | ❌ null | ❌ null | 不支持分区迭代 |
| MySQL | — | — | 不支持分区迭代 |

#### Worker 白名单限制（ScopeFilterUtils）

当前 Worker 侧的硬编码白名单**比元数据 SDK 的实际能力更窄**：

| 过滤维度 | Worker 白名单 | 元数据 SDK 实际支持 |
|---------|-------------|-------------------|
| 分区级过滤（类型 1/2/3/4） | MaxCompute、Hive | MaxCompute、Hive、AWS Glue、DLF（SDK 层支持但 Worker 未放行） |
| 仅 BY_MODIFY_TIME（类型 3） | 同上 | **额外支持** StarRocks、ClickHouse、BigQuery（SDK 有 modifiedTime 但 Worker 未放行） |
| 表级过滤（非分区表） | MaxCompute、Hive、Databricks、Hologres、AzureSynapse、ClickHouse | — |

**注意**: 如果数据源不在 Worker 白名单中，ScopeFilter 会**静默跳过**（不报错），所有分区都会参与校验。用户可能不知道过滤没有生效。

**潜在扩展**: StarRocks/ClickHouse/BigQuery 的 partitionModifiedTime 已在 SDK 层可用，只需扩展 Worker 白名单即可支持 BY_MODIFY_TIME 过滤。但 LAST_N_PARTITION 和 LAST_N_DAY 仍不可用（缺少 partitionCreateTime）。

### 元数据依赖

| 过滤类型 | 依赖的元数据字段 | 来源 |
|---------|----------------|------|
| LAST_N_PARTITION | `partitionCreateTime` | `PartitionMeta.getPartitionCreateTime()` |
| LAST_N_DAY | `partitionCreateTime` | `PartitionMeta.getPartitionCreateTime()` |
| BY_MODIFY_TIME | `partitionModifiedTime` / `dataModifiedTime` | `PartitionMeta.getPartitionModifiedTime()` / `TableMeta.getDataModifiedTime()` |
| BY_CREATE_TIME | `partitionCreateTime` / `tableCreateTime` | `PartitionMeta.getPartitionCreateTime()` / `TableMeta.getTableCreateTime()` |

如果元数据 SDK 无法获取某个字段（返回 null），该分区会被跳过（视为最老）。

### 决策指引

| 场景 | 推荐过滤类型 | 参数 |
|------|------------|------|
| 每日增量同步，只校验最新分区 | LAST_N_PARTITION | lastN=1 |
| 每日增量同步，校验近 3 天以防遗漏 | LAST_N_PARTITION | lastN=3 |
| 周末补数后全量验证 | LAST_N_DAY | lastN=7 |
| 指定时间段的数据迁移验证 | BY_CREATE_TIME | start/end 指定 |
| 只关注最近有变更的数据 | BY_MODIFY_TIME | start/end 指定 |
| 首次全量迁移 | NONO（不筛选） | — |

### 配置示例

```json
{
  "scopeFilter": {
    "scopeFilterType": 1,
    "lastN": 3
  }
}
```

### 注意事项

1. ScopeFilter 只对**分区表**有效。非分区表只支持 BY_MODIFY_TIME 和 BY_CREATE_TIME 的表级过滤。
2. LAST_N_PARTITION 使用滑动窗口算法，按创建时间排序后取最近 N 个。如果分区创建时间为 null，该分区被视为最老而被跳过。
3. LAST_N_DAY 的截止时间为当天 00:00:00（系统时区）。
4. 当数据源不支持 ScopeFilter 时，不会报错——所有分区都会参与校验。用户可能不知道过滤没有生效。
5. 对于 Hive→MaxCompute 场景，两端都支持分区过滤，可以安全使用。
