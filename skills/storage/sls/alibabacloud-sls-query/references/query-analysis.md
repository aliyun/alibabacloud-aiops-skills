# 查询分析路由

## 1. 先分清三种能力

- 查询：核心是不做聚合，返回的是日志级结果
- 索引查询负责高效过滤日志，语法能力相对有限
- 如果查询命中的日志还要继续做字段增减、字段筛选、parse/extend/project 等逐行处理，这部分属于 SPL 能力，不属于索引查询本身
- 分析：核心是带聚合过程，通常会使用聚合函数、分组、统计计算
- 索引查询：典型的查询语法，用来过滤日志，返回原始日志。典型形式：`status: 200 and method: GET`
- SQL 分析：典型的分析语法，用来聚合、分组、统计。典型形式：`status: 200 | SELECT count(*) AS pv FROM log`
- SPL：在查询分析场景下，主要作为查询能力的补充，用来处理扫描模式下的复杂过滤、逐行处理、字段增减、字段筛选，以及在需要时做 `stats` 聚合。典型形式：`* | where status = '500' | extend latency_ms = cast(latency as BIGINT) | project latency_ms`

## 2. 选择规则

- 查询场景优先索引查询：效率最高，但语法能力相对有限
- 如果查询场景里需要复杂条件过滤、逐行处理、parse-json/parse-regexp/parse-kv/extend 等能力：用 SPL 作为索引查询的补充
- 分析场景优先 SQL：适合 count/sum/avg/group by/topN/窗口分析等聚合计算
- 分析场景优先普通 SQL；如果发现分析字段没有索引，普通 SQL 无法直接完成，再考虑 SQL SCAN
- SPL 虽然也支持 `stats`、`sort`、`limit` 等聚合相关指令，但除非用户明确要求 SPL，或者问题本身就是扫描查询/流水线处理场景，否则分析语句默认优先生成 SQL

## 3. 管道分层规则

- 只要语句里有 `|`，第一级管道前面的部分就是索引查询
- 这一级索引查询对后面的 SPL 和 SQL 都有效
- 作用是先用索引快速过滤，提前缩小后续处理的数据范围
- 因此只要某个过滤条件可以用索引查询表达，就应该尽量前置到 `|` 前面
- 对 SQL 来说，这通常是执行更快的关键：能前置的过滤条件尽量不要只写在后面的 SQL 里
- 对 SPL 来说也是一样：能前置的索引过滤先前置，再在后面做逐行处理

## 4. 前置条件

- 查询分析都依赖索引配置
- SQL 依赖字段开启统计
- 索引和统计通常只对配置后新写入的数据生效，历史数据需要重建索引
- 查询型 Logstore 不支持统计，因此不支持 SQL 分析
- SCAN 也不是“完全无索引”，查询部分仍依赖可用索引，至少要满足最小索引条件

## 5. 时间范围

- 不要默认把时间条件写进 query / SQL
- 时间范围通过 `--from` / `--to` flag 指定，值为 Unix 时间戳（秒）
- SQL 中的 `__time__` 更适合做格式化、分组，而不是作为主要过滤手段

## 6. 索引查询高频规则

- 大小写不敏感
- 支持 `AND` / `OR` / `NOT`
- 范围查询只适用于 `long` / `double` 类型字段
- 模糊查询不能以前缀 `*` 开头
- 短语精确匹配用 `#"..."`
- `key: *` 表示字段存在且非空

## 7. SQL 高价值提醒

- 语法是 `查询语句 | 分析语句`
- SLS SQL 基于 Presto SQL
- 在 Logstore 场景一般表名默认是 `log`
- SQL does not support `LIMIT count OFFSET offset` syntax; use `LIMIT offset, count` instead for pagination (e.g., `LIMIT 20, 20` for rows 21–40)
- 默认返回最多 100 行；更大结果要配合 `LIMIT`
- SQL 后不能继续接 SPL
- 如果过滤条件可以在 `|` 前用索引查询表达，优先前置，不要只放在 SQL 里

## 8. SCAN 模式

- 用于未建索引字段的兜底分析，不是优先方案
- 查询场景：优先索引查询，其次 SPL
- 分析场景：优先普通 SQL，其次 SQL SCAN
- 典型写法：`* | set session mode = scan; SELECT count(1) AS pv, api FROM log GROUP BY api`
- 限制：
  - 查询部分仍受索引影响
  - 所有字段视为 `varchar`
  - 单 Shard 扫描条数和总扫描行数有限制
  - 性能明显低于索引分析模式
  - 更适合临时分析或补救场景，不适合默认生成

## 9. 常见回答模板

### 只查日志
```text
status: 500 and service: payment
```

### 统计错误数
```sql
status: 500 | SELECT count(*) AS error_count FROM log
```

### 按小时聚合
```sql
status: 500 | SELECT date_format(__time__, '%Y-%m-%d %H:00:00') AS hour, count(*) AS error_count FROM log GROUP BY hour ORDER BY hour
```

### 先前置索引过滤，再做 SPL 处理
```spl
status: 500 and service: payment | where cast(latency as BIGINT) > 1000 | extend latency_ms = cast(latency as BIGINT) | project service, latency_ms, message
```

## 本地源文档

- `./query_analysis/overview.yaml`
- `./query_analysis/indexSearch.yaml`
- `./query_analysis/indexConfig.yaml`
- `./query_analysis/sql.yaml`
