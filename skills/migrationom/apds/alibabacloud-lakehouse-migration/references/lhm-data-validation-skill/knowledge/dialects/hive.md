# Hive

方言族：Hive 族（大数据 SQL 基准方言，MaxCompute/Impala/Databricks/EMR Spark 均继承）

## 1. 分区查询语法

```sql
-- 标准 WHERE 子句
SELECT COUNT(*) FROM table_name WHERE pt = '20240602';
```

无全表扫描限制（与 MaxCompute 不同）。

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| JSON 子字段 | `get_json_object(col, '$.field')` | `get_json_object(metadata, '$.id')` |
| 多字段提取 | `json_tuple(col, 'f1', 'f2')` | 比多次 get_json_object 更高效 |
| STRUCT 子字段 | `col.field` | `address.city` |
| ARRAY 元素 | `col[index]`（0-based） | `tags[0]` |
| ARRAY 长度 | `size(col)` | `size(tags)` |
| ARRAY 排序 | `sort_array(col)` | `sort_array(tags)` |
| ARRAY 展开 | `LATERAL VIEW explode(col) t AS val` | `LATERAL VIEW explode(tags) t AS tag` |
| MAP 键 | `map_keys(col)` | `map_keys(properties)` |
| MAP 值 | `map_values(col)` | `map_values(properties)` |
| MAP 访问 | `col['key']` | `properties['name']` |

**注意**: Hive 无原生 JSON 类型，JSON 以 STRING 存储。

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | — |
| COUNT DISTINCT | 标准 | — |
| 字符串聚合 | `concat_ws(',', collect_list(col))` | 需配合 collect_list |
| 收集为数组 | `collect_list(col)` / `collect_set(col)` | — |
| 近似百分位 | `percentile_approx(col, 0.5)` | — |

## 4. NULL 处理

```sql
NVL(col, default_value)
```

## 5. DECIMAL 格式化

```sql
replace(format_number(CAST(col AS DECIMAL(p,s)), s), ',', '')
```

无 DECIMAL 前导零问题。

## 6. BOOLEAN 表示

`true` / `false`（小写字符串）

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `md5(col)` | ✅ 标准实现 |
| CRC32 | `crc32(col)` | ✅ 标准实现 |
| LENGTH | `length(col)` | ✅ 返回字符数（CHAR_COUNT 模式） |

## 8. 已知陷阱

| 陷阱 | 说明 | 处理 |
|------|------|------|
| 隐式类型转换 | STRING→NUMBER 隐式转换返回 NULL 而非报错 | 其他方言可能报错，造成差异 |
| CAST 失败行为 | CAST 失败返回 NULL 而非抛异常 | MaxCompute TRY_CAST 也是返回 NULL，但标准 CAST 行为不同 |
| 无原生 JSON 类型 | JSON 以 STRING 存储，类型推断可能不同 | 校验时按 STRING 处理 |
| **ScopeFilter 支持** | ✅ 分区级过滤全部可用（createTime 来自 HMS `getCreateTime()`，modifiedTime 来自 `transient_lastDdlTime`） | LAST_N_PARTITION / LAST_N_DAY / BY_MODIFY_TIME / BY_CREATE_TIME |
