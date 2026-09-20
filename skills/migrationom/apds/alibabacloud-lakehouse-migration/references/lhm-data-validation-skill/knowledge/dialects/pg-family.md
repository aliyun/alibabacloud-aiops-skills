# PostgreSQL 方言族（衍生）

包含：Hologres、GaussDB、ADBPG

均继承 PostgresDialect，共享 PG 族的核心行为。基准方言详见 `postgres.md`。

## 共性（继承自 PostgreSQL）

- **NULL 处理**: `COALESCE(col::text, 'default')`
- **DECIMAL 格式化**: `TRIM(TO_CHAR(...))` — **前导零问题**（v1.17.2+ 已修复）
- **CRC32**: ❌ 不支持
- **MD5**: `md5(col)` ✅
- **LENGTH**: `length(col)` ✅ 字符数
- **BOOLEAN**: `t` / `f`
- **ARRAY 索引**: 1-based
- **ScopeFilter**: ❌ 不支持（partitionCreateTime 和 partitionModifiedTime 均不可用，SDK 只返回 partitionId）

## Hologres

### 特殊行为

| 维度 | 说明 |
|------|------|
| 连接方式 | PostgreSQL 协议兼容，psycopg2 直连 |
| 分区语法 | 标准 WHERE 子句 |
| JSON 类型 | 支持 JSONB，语法同 PG |

### 已知陷阱

无额外陷阱，共享 PG 族所有已知问题（DECIMAL 前导零、BOOLEAN 格式、无 CRC32）。

---

## GaussDB

### 特殊行为

| 维度 | 说明 |
|------|------|
| 分区语法 | 标准 WHERE 子句 |
| JSON 类型 | 支持 JSONB，语法同 PG |

### 已知陷阱

无额外陷阱，共享 PG 族所有已知问题。

---

## ADBPG (AnalyticDB PostgreSQL)

### 特殊行为

| 维度 | 说明 |
|------|------|
| 分区语法 | 标准 WHERE 子句 |
| JSON 类型 | 支持 JSONB，语法同 PG |
| DECIMAL 格式化 | 与 PG 相同（前导零问题已修复） |

### 已知陷阱

无额外陷阱，共享 PG 族所有已知问题。

---

## PG 族跨方言校验速查

当 PG 族方言与以下方言搭配时需注意：

| 对方方言 | 关键差异 |
|---------|---------|
| Hive/MaxCompute | BOOLEAN 格式不同（`t`/`f` vs `true`/`false`）；ARRAY 索引不同（1-based vs 0-based）；NULL 处理函数不同（COALESCE vs NVL） |
| MySQL/StarRocks | BOOLEAN 格式不同（`t`/`f` vs `1`/`0`）；NULL 处理函数不同（COALESCE vs IFNULL） |
| Presto | ARRAY 索引相同（均 1-based）；函数名不同（string_agg vs array_join） |
