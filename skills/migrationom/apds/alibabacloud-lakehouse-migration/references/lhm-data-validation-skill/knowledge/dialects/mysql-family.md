# MySQL 方言族

包含：MySQL、ADB MySQL、Doris（Doris 继承 StarRocks，但行为接近 MySQL）

## MySQL / ADB MySQL

继承自 MysqlDialect，行为与 MySQL 标准一致。

### 1. 分区查询语法

```sql
SELECT COUNT(*) FROM table_name WHERE pt = '20240602';
```

### 2. 复杂类型语法

| 类型 | 访问语法 |
|------|---------|
| JSON 子字段 | `JSON_EXTRACT(col, '$.field')` |
| JSON 数组长度 | `JSON_LENGTH(col)` |
| 无原生 ARRAY/STRUCT | — |

### 3. 聚合函数

| 函数 | 语法 |
|------|------|
| 字符串聚合 | `GROUP_CONCAT(col SEPARATOR ',')` |

### 4. NULL 处理

```sql
IFNULL(col, default_value)
```

### 5. DECIMAL 格式化

```sql
CAST(CAST(col AS CHAR) AS DECIMAL(p,s))
```

### 6. BOOLEAN 表示

`1` / `0`

### 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `md5(col)` | ✅ |
| CRC32 | `crc32(col)` | ✅ |
| LENGTH | `char_length(col)` | ✅ 字符数 |

### 8. 已知陷阱

| 陷阱 | 说明 |
|------|------|
| BOOLEAN 格式 | `1`/`0` vs Hive 的 `true`/`false` vs PG 的 `t`/`f` |
| UNSIGNED INT | 大值可能溢出目标端 BIGINT |

---

## Doris

继承 StarRocksDialect，行为与 StarRocks 基本一致。参见 `starrocks.md`。

关键差异：
- 分区语法同 StarRocks（`PARTITION(name)`）
- NULL 处理同 MySQL（`IFNULL`）
- LENGTH 使用 `char_length`
