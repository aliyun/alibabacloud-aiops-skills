# 复杂类型（STRUCT/JSON/ARRAY）双端 SQL 语法参考

## 概述

当校验表包含复杂类型字段时，内置指标（SUM/AVG/MIN/MAX/COUNT）通常无法直接用于复杂类型。
需要为双端分别生成正确的字段访问语法，然后通过自定义指标表达式进行聚合比对。

---

## 1. JSON/SUPER 字段访问语法

| 操作 | Redshift | MaxCompute | Hive | MySQL | PostgreSQL | StarRocks |
|------|----------|-----------|------|-------|-----------|-----------|
| 访问子字段 | `col.field`（SUPER） | `get_json_object(col, '$.field')` | `get_json_object(col, '$.field')` | `JSON_EXTRACT(col, '$.field')` | `col->>'field'`（JSONB） | `get_json_string(col, '$.field')` |
| 嵌套访问 | `col.a.b.c` | `get_json_object(col, '$.a.b.c')` | `get_json_object(col, '$.a.b.c')` | `JSON_EXTRACT(col, '$.a.b.c')` | `col#>>'{a,b,c}'` | `get_json_string(col, '$.a.b.c')` |
| 数组元素 | `col.arr[0]` | `get_json_object(col, '$.arr[0]')` | `get_json_object(col, '$.arr[0]')` | `JSON_EXTRACT(col, '$.arr[0]')` | `col->'arr'->>0` | `get_json_string(col, '$.arr[0]')` |
| 序列化 | `JSON_SERIALIZE(col)` | `to_json(col)` 或 `CAST(col AS STRING)` | `to_json(col)` | `JSON_EXTRACT(col, '$')` | `col::text`（JSONB） | `CAST(col AS STRING)` |
| 数组长度 | `json_array_length(col)` | `size(col)`（ARRAY 类型） | `size(col)` | `JSON_LENGTH(col)` | `jsonb_array_length(col)` | `json_length(col)` |

## 2. STRUCT 字段访问语法

| 操作 | Redshift | MaxCompute | Hive | PostgreSQL |
|------|----------|-----------|------|-----------|
| 访问子字段 | `col.field`（SUPER） | `col.field` | `col.field` | `(col).field` 或 `col->>'field'`（JSONB） |
| 嵌套访问 | `col.a.b` | `col.a.b` | `col.a.b` | `(col).a.b` |

## 3. ARRAY 操作语法

| 操作 | Redshift | MaxCompute | Hive | PostgreSQL |
|------|----------|-----------|------|-----------|
| 元素数量 | `json_array_length(col)` | `size(col)` | `size(col)` | `array_length(col, 1)` |
| 排序 | 不支持 sort_array | `sort_array(col)` | `sort_array(col)` | 不支持 sort_array |
| 展开 | 不支持 LATERAL VIEW | `LATERAL VIEW explode(col) t AS val` | `LATERAL VIEW explode(col) t AS val` | `unnest(col)` |
| 元素访问 | `col[0]` | `col[0]` | `col[0]` | `col[1]`（1-based） |

## 4. 聚合函数对照

| 聚合 | Redshift | MaxCompute | Hive | 校验用途 |
|------|----------|-----------|------|---------|
| SUM | `SUM(col)` | `SUM(col)` | `SUM(col)` | 数值求和 |
| AVG | `AVG(col)` 注意 float 精度 | `AVG(col)` 精确 DECIMAL | `AVG(col)` | 均值比对 |
| COUNT DISTINCT | `COUNT(DISTINCT col)` | `COUNT(DISTINCT col)` | `COUNT(DISTINCT col)` | 去重计数 |
| MIN/MAX | 标准 | 标准 | 标准 | 范围比对 |
| 字符串聚合 | `LISTAGG(col, ',')` | `WM_CONCAT(',', col)` | `concat_ws(',', collect_list(col))` | 字符串集合比对 |
| 收集为数组 | 不支持 | `COLLECT_LIST(col)` / `COLLECT_SET(col)` | `collect_list(col)` / `collect_set(col)` | 集合比对 |

## 5. 自定义指标表达式示例

### 场景：校验 Redshift SUPER 类型的 JSON 子字段

自定义指标（Redshift 端）:
```sql
max(JSON_SERIALIZE(metadata.id)) as max_metadata_id,
min(JSON_SERIALIZE(metadata.id)) as min_metadata_id,
count(distinct JSON_SERIALIZE(metadata.type)) as distinct_type_count,
sum(length(JSON_SERIALIZE(metadata))) as sum_metadata_len
```

自定义指标（MaxCompute 端）:
```sql
max(get_json_object(metadata, '$.id')) as max_metadata_id,
min(get_json_object(metadata, '$.id')) as min_metadata_id,
count(distinct get_json_object(metadata, '$.type')) as distinct_type_count,
sum(length(metadata)) as sum_metadata_len
```

### 场景：校验 STRUCT 数组展开后的元素集合

自定义指标（MaxCompute 端）:
```sql
size(tags) as tag_count,
size(array_distinct(tags)) as distinct_tag_count
```

自定义指标（Redshift 端，受限）:
```sql
json_array_length(JSON_SERIALIZE(tags)) as tag_count
```

### 场景：校验 MAP 类型的键值对

自定义指标（MaxCompute 端）:
```sql
size(map_keys(properties)) as key_count,
size(map_values(properties)) as value_count
```

自定义指标（Redshift 端，受限）:
```sql
length(JSON_SERIALIZE(properties)) as json_len
```

## 6. 类型转换语法

| 场景 | Redshift | MaxCompute | Hive |
|------|----------|-----------|------|
| 转字符串 | `CAST(col AS VARCHAR)` 或 `col::text` | `CAST(col AS STRING)` | `CAST(col AS STRING)` |
| 转数值 | `CAST(col AS DECIMAL(p,s))` | `CAST(col AS DECIMAL(p,s))` | `CAST(col AS DECIMAL(p,s))` |
| NULL 替换 | `COALESCE(col, default)` | `NVL(col, default)` | `NVL(col, default)` |
| 安全转换 | 不支持 TRY_CAST | `TRY_CAST(col AS type)`（2.0+） | 不支持 TRY_CAST |

## 7. 生成自定义指标的规则

为每个子字段 `sub_field`，根据类型生成不同的聚合指标：

| 子字段类型 | 可生成的指标 |
|-----------|------------|
| 数值型 | `max({access_expr})`, `min({access_expr})`, `sum(cast({access_expr} as bigint))`, `avg(cast({access_expr} as double))` |
| 字符串型 | `max({access_expr})`, `min({access_expr})`, `count(distinct {access_expr})`, `sum(length({access_expr}))` |
| 布尔型 | `sum(case when {access_expr} then 1 else 0 end)` |
| 数组型 | `size({access_expr})`, `size(array_distinct({access_expr}))` |
| MAP 型 | `size(map_keys({access_expr}))`, `length({serialize_expr})` |
