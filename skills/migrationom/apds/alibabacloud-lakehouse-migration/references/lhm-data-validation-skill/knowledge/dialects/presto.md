# Presto

方言族：Presto 族基准（Amazon Athena 继承）

## 1. 分区查询语法

```sql
-- 标准 WHERE 子句
SELECT COUNT(*) FROM table_name WHERE dt = '20240602';
```

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| JSON 子字段 | `json_extract_scalar(col, '$.field')` | `json_extract_scalar(metadata, '$.id')` |
| ARRAY 元素 | `col[index]`（**1-based**，与 PG 相同） | `tags[1]` |
| ARRAY 长度 | `cardinality(col)` | `cardinality(tags)` |
| ARRAY 展开 | `UNNEST(col)` | `SELECT t FROM table_name CROSS JOIN UNNEST(tags) AS t` |
| MAP 访问 | `col['key']` | `properties['name']` |
| MAP 键 | `map_keys(col)` | `map_keys(properties)` |

**注意**: Presto ARRAY 索引 **1-based**（与 PG 相同，与 Hive/MaxCompute 的 0-based 不同）。

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | — |
| COUNT DISTINCT | 标准 | — |
| 字符串聚合 | `array_join(array_agg(col), ',')` | 需配合 array_agg |
| ARRAY 聚合 | `array_agg(col)` | — |

## 4. NULL 处理

```sql
COALESCE(CAST(col AS VARCHAR), 'default_value')
-- 数值类型不需要 CAST
COALESCE(col, 0)
```

## 5. DECIMAL 格式化

```sql
CAST(col AS DECIMAL(p,s))
-- 无特殊格式化（不像 PG 的 TO_CHAR）
```

## 6. BOOLEAN 表示

`true` / `false`（与 Hive/MaxCompute 相同）

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `lower(to_hex(md5(to_utf8(col))))` | ✅ 需要多层包装 |
| CRC32 | — | ❌ 不支持（Amazon Athena 也不支持） |
| LENGTH | `length(col)` | ✅ 返回字符数（CHAR_COUNT 模式） |

## 8. 已知陷阱

| 陷阱 | 说明 | 处理 |
|------|------|------|
| ARRAY 索引 1-based | 与 Hive/MaxCompute 的 0-based 不同 | 跨方言校验自定义指标时注意 |
| MD5 格式复杂 | 需要 `lower(to_hex(md5(to_utf8(col))))` 四层包装 | 系统已自动处理 |
| 无 CRC32 | 不支持 | 弱内容校验使用 MD5 |
| 函数名差异 | `cardinality` 而非 `size`，`array_join` 而非 `concat_ws` | 自定义指标表达式需注意 |
| VARCHAR vs STRING | Presto 用 VARCHAR，Hive 用 STRING | 类型映射需注意 |
