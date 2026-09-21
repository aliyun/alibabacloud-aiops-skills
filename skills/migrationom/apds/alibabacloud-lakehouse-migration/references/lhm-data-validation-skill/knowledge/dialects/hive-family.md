# Hive 方言族（衍生）

包含：Impala、Databricks、EMR Serverless Spark

均继承 HiveDialect，共享 Hive 族的核心行为。基准方言详见 `hive.md`。

## 共性（继承自 Hive）

- **NULL 处理**: `NVL(col, default)`
- **DECIMAL 格式化**: `replace(format_number(...), ',', '')`
- **MD5**: `md5(col)` ✅
- **LENGTH**: 字符数
- **BOOLEAN**: `true` / `false`
- **ARRAY 索引**: 0-based
- **复杂类型**: `col.field`、`col[index]`、`LATERAL VIEW explode(col)`
- **ScopeFilter**: Impala/Databricks/EMR Spark 均不支持分区时间元数据（仅 Hive 本尊支持）

---

## Impala

### 特殊行为

| 维度 | 说明 |
|------|------|
| LENGTH 函数 | `length(col)` 返回**字节数**而非字符数（与其他方言不同） |
| NULL 处理 | `IF(col IS NULL, default, CAST(col AS STRING))`（IF 不短路） |
| CRC32 | ✅ 支持（继承 Hive） |
| 分区语法 | 标准 WHERE 子句 |

### 已知陷阱

| 陷阱 | 说明 |
|------|------|
| LENGTH 返回字节数 | Impala 的 `length()` 是 BYTE_COUNT 模式，其他方言的 `length()` 是 CHAR_COUNT |
| IF 不短路 | `IF(col IS NULL, ...)` 不会短路求值，可能导致异常 |

---

## Databricks

### 特殊行为

| 维度 | 说明 |
|------|------|
| CRC32 | TEXT 类型不支持 CRC32（`sum(crc32(text))` 无 cast），其他类型支持 |
| LENGTH | 字符数 |
| 分区语法 | 标准 WHERE 子句 |

### 已知陷阱

| 陷阱 | 说明 |
|------|------|
| TEXT 类型 CRC32 | TEXT 类型 CRC32 不做类型转换，可能与其他方言结果不同 |

---

## EMR Serverless Spark

### 特殊行为

| 维度 | 说明 |
|------|------|
| NULL 处理 | `IFNULL(col, default)`（与 Hive 的 NVL 不同） |
| CRC32 | TEXT 类型不支持（同 Databricks），其他类型支持 |
| LENGTH | 字符数 |
| 分区语法 | 标准 WHERE 子句 |

### 已知陷阱

| 陷阱 | 说明 |
|------|------|
| NULL 处理函数 | 使用 IFNULL 而非 NVL |

---

## Hive 族跨方言校验速查

当 Hive 族方言与以下方言搭配时需注意：

| 对方方言 | 关键差异 |
|---------|---------|
| PG 族 | BOOLEAN 格式不同；ARRAY 索引不同；NULL 处理函数不同 |
| StarRocks | 分区语法不同（WHERE vs PARTITION）；BOOLEAN 格式不同 |
| ClickHouse | 函数名差异（size vs length） |
| Presto | ARRAY 索引不同（0-based vs 1-based）；函数名不同（size vs cardinality） |
