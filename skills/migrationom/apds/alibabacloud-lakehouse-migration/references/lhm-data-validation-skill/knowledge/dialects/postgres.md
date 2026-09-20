# PostgreSQL

方言族：PG 族基准（Redshift/GaussDB/Hologres/ADBPG 均继承）

## 1. 分区查询语法

```sql
-- 标准 WHERE 子句
SELECT COUNT(*) FROM table_name WHERE pt = '20240602';

-- PG 原生分区（继承表）
SELECT COUNT(*) FROM table_name_partition_20240602;
```

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| JSONB 子字段 | `col->>'field'` | `metadata->>'id'` |
| JSONB 嵌套 | `col#>>'{a,b,c}'` | `metadata#>>'{address,city}'` |
| JSONB 数组元素 | `col->'arr'->>0` | `metadata->'tags'->>0` |
| JSONB 数组长度 | `jsonb_array_length(col)` | `jsonb_array_length(metadata)` |
| ARRAY 元素 | `col[index]`（**1-based**，非 0-based） | `tags[1]` |
| ARRAY 长度 | `array_length(col, 1)` | `array_length(tags, 1)` |
| ARRAY 展开 | `unnest(col)` | `SELECT unnest(tags) FROM table_name` |

**注意**: PG 的 ARRAY 索引是 **1-based**（Hive/MaxCompute 是 0-based），跨方言校验时需注意。

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | — |
| COUNT DISTINCT | 标准 | — |
| 字符串聚合 | `string_agg(col, ',')` | PG 风格（非 GROUP_CONCAT 或 WM_CONCAT） |
| ARRAY 聚合 | `array_agg(col)` | — |

## 4. NULL 处理

```sql
COALESCE(col::text, 'default_value')
-- 数值类型不需要 ::text 转换
COALESCE(col, 0)
```

## 5. DECIMAL 格式化

```sql
-- PG 的 TO_CHAR 格式化
TRIM(TO_CHAR(col, '9999999999999999999999999999999999999990.999999'))
```

**已知问题**: TO_CHAR 格式化会将前导零替换为空格，TRIM 后 `0.1` 变成 `.1`。
**修复**: v1.17.2+ 已在 PostgresDialect.getDecimalFormatter 中修复（自动补前导零）。
**影响范围**: PostgreSQL、Redshift、GaussDB、Hologres、ADBPG。

## 6. BOOLEAN 表示

`t` / `f`（PG 风格，与 Hive 的 `true`/`false` 和 MySQL 的 `1`/`0` 均不同）

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `md5(col)` | ✅ 标准实现 |
| CRC32 | — | ❌ 不支持 |
| LENGTH | `length(col)` | ✅ 返回字符数（CHAR_COUNT 模式） |

## 8. 已知陷阱

| 陷阱 | 说明 | 处理 |
|------|------|------|
| DECIMAL 前导零 | TO_CHAR 格式化丢失前导零（0.1 → .1） | 升级到 v1.17.2+ |
| ARRAY 索引 1-based | PG 系 ARRAY 从 1 开始，Hive/MC 从 0 开始 | 跨方言校验时注意索引偏移 |
| BOOLEAN 格式 | `t`/`f` 与其他方言均不同 | 弱内容校验可能报差异，建议排除 BOOLEAN 字段 |
| 无 CRC32 | PG 系均不支持 CRC32 | 弱内容校验使用 MD5 |
| ::text 转换 | JSONB 的 `::text` 正常，但 Redshift SUPER 的 `::text` 返回 NULL | Redshift 需单独处理 |
| **ScopeFilter 不支持** | ❌ partitionCreateTime 和 partitionModifiedTime 均不可用（元数据 SDK 只返回 partitionId） | 所有分区都会参与校验，ScopeFilter 静默跳过 |
