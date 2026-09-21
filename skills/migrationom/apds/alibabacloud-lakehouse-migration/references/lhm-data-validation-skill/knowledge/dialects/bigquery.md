# BigQuery

方言族：独立方言

## 1. 分区查询语法

```sql
-- WHERE 子句（分区表通过 _PARTITIONDATE 或分区列过滤）
SELECT COUNT(*) FROM table_name WHERE _PARTITIONDATE = '2024-06-02';
SELECT COUNT(*) FROM table_name WHERE dt = '20240602';
```

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| JSON 子字段 | `JSON_EXTRACT_SCALAR(col, '$.field')` | `JSON_EXTRACT_SCALAR(metadata, '$.id')` |
| STRUCT 子字段 | `col.field` | `address.city` |
| ARRAY 元素 | `col[OFFSET(0)]`（0-based，需 OFFSET 关键字） | `tags[OFFSET(0)]` |
| ARRAY 长度 | `ARRAY_LENGTH(col)` | `ARRAY_LENGTH(tags)` |
| ARRAY 展开 | `UNNEST(col)` | `SELECT t FROM table_name, UNNEST(tags) AS t` |

**注意**: BigQuery ARRAY 索引需要 `OFFSET(n)` 或 `ORDINAL(n)`（1-based）关键字，不能直接 `col[0]`。

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | — |
| COUNT DISTINCT | 标准 | — |
| 字符串聚合 | `STRING_AGG(col, ',')` | BigQuery 风格 |
| ARRAY 聚合 | `ARRAY_AGG(col)` | — |

## 4. NULL 处理

```sql
IFNULL(CAST(col AS STRING), 'default_value')
-- 数值类型不需要 CAST
IFNULL(col, 0)
```

## 5. DECIMAL 格式化

```sql
FORMAT('%.6f', col)
```

## 6. BOOLEAN 表示

`true` / `false`（与 Hive/MaxCompute 相同）

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `to_hex(md5(col))` | ✅ 需要 to_hex 包装 |
| CRC32 | — | ❌ 不支持 |
| LENGTH | `LENGTH(col)` | ✅ 返回字符数（CHAR_COUNT 模式） |

## 8. 已知陷阱

| 陷阱 | 说明 | 处理 |
|------|------|------|
| 无 CRC32 | 不支持 CRC32 函数 | 弱内容校验使用 MD5 |
| ARRAY 索引语法 | 需要 `OFFSET(n)` 而非直接 `[n]` | 跨方言校验自定义指标时需注意 |
| STRUCT/TIME 类型 | STRUCT(RECORD) 子字段和 TIME 类型格式化需特殊处理 | 检查 BigQuery 版本是否支持 |
| MD5 格式 | 需要 `to_hex(md5(col))` 包装 | 系统已自动处理 |
| TRY_CAST | BigQuery 支持 SAFE_CAST（失败返回 NULL） | 与标准 CAST 行为不同 |
| **ScopeFilter 部分支持** | ❌ partitionCreateTime 不可用 ✅ partitionModifiedTime 可用（`last_modified_time`） | 仅 BY_MODIFY_TIME 可用（SDK 层）；Worker 白名单未放行 |
