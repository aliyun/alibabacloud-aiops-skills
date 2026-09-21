# Redshift

方言族：PG 族（继承 PostgresDialect，但 SUPER 类型和 CRC32 行为独立）

## 1. 分区查询语法

```sql
-- 标准 WHERE 子句（Redshift 无原生分区表，通常用排序键替代）
SELECT COUNT(*) FROM table_name WHERE dt = '20240602';
```

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| SUPER 子字段 | `col.field` | `metadata.id` |
| SUPER 嵌套 | `col.a.b.c` | `metadata.address.city` |
| SUPER 数组元素 | `col.arr[0]` | `metadata.tags[0]` |
| SUPER 序列化 | `JSON_SERIALIZE(col)` | `JSON_SERIALIZE(metadata)` |
| 传统 JSON | `JSON_EXTRACT_PATH_TEXT(col, 'field')` | `JSON_EXTRACT_PATH_TEXT(data, 'id')` |
| ARRAY 长度 | `json_array_length(col)` | `json_array_length(metadata)` |
| ARRAY 排序 | **不支持** sort_array | — |
| ARRAY 展开 | **不支持** LATERAL VIEW | — |

**关键差异**: Redshift 无原生 ARRAY/STRUCT/MAP 类型，统一使用 SUPER 类型。访问语法是 PartiQL 风格（dot-path），与 Hive 的 `col.field` 看似相同但底层类型不同。

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | **AVG 使用 CONVERT(float, col)，精度约 7 位有效数字** |
| COUNT DISTINCT | 标准 | — |
| 字符串聚合 | `LISTAGG(col, ',')` | Oracle 风格（非 string_agg 或 GROUP_CONCAT） |
| MEDIAN | `MEDIAN(col)` | 独有函数 |

**AVG 精度差异**: Redshift AVG 使用 float（IEEE 754，约 7 位有效数字），MaxCompute/Hive AVG 使用精确 DECIMAL。跨方言校验时 AVG 通常有 < 0.01% 的微小差异。

## 4. NULL 处理

```sql
-- 默认继承 PG
COALESCE(col::text, 'default_value')

-- JSON/SUPER 类型特殊处理（v1.17.2+）
COALESCE(JSON_SERIALIZE(col), 'default_value')
```

**已知问题**: Redshift SUPER 类型的 `col::text` 返回 NULL（与 PG JSONB 的 `::text` 正常不同）。
**修复**: v1.17.2+ 已在 RedShiftDialect.ifNullFunction 中修复，JSON 类型使用 `JSON_SERIALIZE(col)` 替代 `col::text`。

## 5. DECIMAL 格式化

继承 PostgreSQL 的 `TRIM(TO_CHAR(...))` 方式，同样存在前导零问题（v1.17.2+ 已修复）。

## 6. BOOLEAN 表示

`t` / `f`（继承 PG 风格）

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `md5(col)` | ✅ 标准实现 |
| CRC32 | `crc32(col)` | ❌ **非标准多项式 + hex 字符串返回值** |
| LENGTH | `length(col)` | ✅ 返回字符数（CHAR_COUNT 模式） |

**CRC32 不兼容**: Redshift 的 CRC32 使用非标准多项式，且返回 hex 字符串（如 `'e3069283'`）而非无符号整数。与 MaxCompute/Hive 的标准 CRC32 完全不兼容。
**验证**: `crc32('123456789')` Redshift 返回 `'e3069283'`，标准值应为 `'cbf43926'`。

## 8. 已知陷阱

| 陷阱 | 说明 | 处理 |
|------|------|------|
| CRC32 不兼容 | 非标准多项式 + hex 返回值 | 弱内容校验必须使用 MD5 |
| SUPER 类型 ::text 返回 NULL | 与 PG JSONB 行为不同 | 升级到 v1.17.2+ |
| AVG float 精度 | 约 7 位有效数字 vs MC 精确 DECIMAL | 配置 diffTolerateValues |
| DECIMAL 前导零 | 继承 PG 的 TO_CHAR 问题 | 升级到 v1.17.2+ |
| 无 sort_array | 无法对 ARRAY 元素排序 | 二次校验只能通过元素数量间接验证 |
| 无 LATERAL VIEW | 无法展开 ARRAY | 二次校验受限 |
| BOOLEAN 格式 | `t`/`f` 与其他方言不同 | 弱内容校验可能报差异 |
| **ScopeFilter 不支持** | ❌ partitionCreateTime 和 partitionModifiedTime 均不可用 | 所有分区都会参与校验，ScopeFilter 静默跳过 |
