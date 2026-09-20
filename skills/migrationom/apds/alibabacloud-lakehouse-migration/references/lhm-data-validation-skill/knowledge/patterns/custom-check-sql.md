# 二次校验 SQL 模板库

> **注意**: 自定义SQL校验类型当前不支持。以下二次校验方案通过**指标校验的自定义表达式能力**实现。
> 在指标校验任务中，如果表达式包含 AS 关键字（如 `sum(col) AS sum_col`），系统会将其作为自定义指标。
> 因此二次校验设计的是**自定义指标表达式**，提交为指标校验任务。

## 模式 1：ARRAY 元素集合比对（忽略顺序）

**适用场景**: ARRAY 字段 CRC32/MD5 不一致，怀疑仅元素顺序不同

**原理**: 对 ARRAY 元素排序后再取哈希，或比对元素数量

**SQL 模板**:

源端（Redshift，无 sort_array）:
```sql
SELECT id, json_array_length(JSON_SERIALIZE(tags)) AS tag_count
FROM {table_name}
```

目标端（MaxCompute，有 sort_array）:
```sql
SELECT id, size(tags) AS tag_count
FROM {table_name}
```

**判定标准**:
- tag_count 一致 → 元素数量相同，大概率仅顺序不同
- tag_count 不一致 → 存在真实数据差异

**限制**: Redshift 无 sort_array，只能通过元素数量间接验证

---

## 模式 2：DECIMAL 精度统一比对

**适用场景**: 指标校验中 AVG/SUM 有微小差异（< 0.01%）

**原理**: 两端 CAST 为相同精度后比对

**SQL 模板**（双端通用）:
```sql
SELECT
  SUM(CAST({column_name} AS DECIMAL(38,6))) AS sum_val,
  COUNT(*) AS cnt,
  MIN(CAST({column_name} AS DECIMAL(38,6))) AS min_val,
  MAX(CAST({column_name} AS DECIMAL(38,6))) AS max_val
FROM {table_name}
```

**判定标准**:
- SUM 一致 + COUNT 一致 → 精度问题确认，数据本身一致
- SUM 不一致 → 存在真实数据差异

---

## 模式 3：NULL vs 空字符串分布比对

**适用场景**: NULL 和空字符串混淆导致的差异

**原理**: 分别统计 NULL/空字符串/有值 的数量

**SQL 模板**（双端通用）:
```sql
SELECT
  COUNT(*) AS total_count,
  SUM(CASE WHEN {column_name} IS NULL THEN 1 ELSE 0 END) AS null_count,
  SUM(CASE WHEN {column_name} = '' THEN 1 ELSE 0 END) AS empty_count,
  SUM(CASE WHEN {column_name} IS NOT NULL AND {column_name} != '' THEN 1 ELSE 0 END) AS value_count
FROM {table_name}
```

**判定标准**:
- null_count 一致 + empty_count 一致 + value_count 一致 → 分布完全一致
- null_count 不一致 → 存在 NULL 映射差异

---

## 模式 4：MAP 键集合比对

**适用场景**: MAP 类型字段不一致，怀疑键集合不同

**原理**: 提取 MAP 的键集合，排序后比对

**SQL 模板**:

MaxCompute 端:
```sql
SELECT id, size(map_keys({column_name})) AS key_count
FROM {table_name}
```

Redshift 端（无 OBJECT_KEYS，使用 JSON_SERIALIZE 替代）:
```sql
SELECT id, length(JSON_SERIALIZE({column_name})) AS json_len
FROM {table_name}
```

**限制**: Redshift 无 OBJECT_KEYS 函数，无法精确实现键集合比对

---

## 模式 5：时区归一化比对

**适用场景**: TIMESTAMP 字段差异值固定为 N 小时

**原理**: 两端统一转换为 UTC 后比对

**SQL 模板**:

Redshift 端:
```sql
SELECT id, CONVERT_TIMEZONE('UTC', {column_name}) AS utc_time
FROM {table_name}
```

MaxCompute 端:
```sql
SELECT id, FROM_UNIXTIME(UNIX_TIMESTAMP({column_name}) - {offset_hours} * 3600) AS utc_time
FROM {table_name}
```

---

## 模式 6：分组行数比对

**适用场景**: 数据量校验通过但怀疑特定分组数据丢失

**原理**: 按业务键 GROUP BY 后比对各组行数

**SQL 模板**（双端通用）:
```sql
SELECT {group_key}, COUNT(*) AS cnt
FROM {table_name}
GROUP BY {group_key}
```

**判定标准**:
- 各分组 cnt 一致 → 数据分布一致
- 某些分组 cnt 不一致 → 特定分组数据丢失

---

## 模式 7：自定义聚合指标比对

**适用场景**: 标准指标校验不足以覆盖的业务逻辑

**原理**: 利用指标校验的聚合能力，自定义聚合表达式

**常用自定义指标**:
```sql
-- 加权平均
SUM({amount} * {weight}) / SUM({weight}) AS weighted_avg

-- 去重计数
COUNT(DISTINCT {user_id}) AS unique_users

-- 条件计数
SUM(CASE WHEN {status} = 'active' THEN 1 ELSE 0 END) AS active_count

-- 字符串长度总和
SUM(LENGTH({text_column})) AS total_text_length

-- 最大值与最小值之差
MAX({value}) - MIN({value}) AS value_range
```

**使用方式**: 在指标校验任务的配置中，将上述表达式填入自定义指标字段（需包含 AS 别名）。系统会自动识别 AS 关键字并将其作为自定义聚合指标。双端需要分别提供各自方言的正确语法。
