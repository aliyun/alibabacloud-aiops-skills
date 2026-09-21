# StarRocks

方言族：MySQL 族（继承 MysqlDialect，但分区语法和部分行为独立）

## 1. 分区查询语法

```sql
-- StarRocks 特有：PARTITION 子句（非 WHERE）
SELECT COUNT(*) FROM table_name PARTITION(20240602);

-- 也支持 WHERE（但分区裁剪效率不同）
SELECT COUNT(*) FROM table_name WHERE dt = '20240602';
```

**与 Hive/MaxCompute 的关键差异**: StarRocks 使用 `PARTITION(name)` 语法，Hive 使用 `WHERE pt = 'value'`。跨方言校验时分区条件语法不兼容。

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| JSON 子字段 | `get_json_string(col, '$.field')` | `get_json_string(metadata, '$.id')` |
| STRUCT 子字段 | 不支持原生 STRUCT | — |
| ARRAY 元素 | 不支持原生 ARRAY | — |

**注意**: StarRocks 对复杂类型支持有限，JSON 通过 `get_json_string`/`get_json_int` 等函数访问。

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | — |
| COUNT DISTINCT | 标准 | — |
| 字符串聚合 | `GROUP_CONCAT(col SEPARATOR ',')` | MySQL 风格 |

## 4. NULL 处理

```sql
IFNULL(col, default_value)
```

## 5. DECIMAL 格式化

```sql
CAST(CAST(col AS CHAR) AS DECIMAL(p,s))
```

无 DECIMAL 前导零问题。

## 6. BOOLEAN 表示

`1` / `0`（MySQL 风格，与 Hive/MaxCompute 的 `true`/`false` 不同）

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `md5(col)` | ✅ 标准实现 |
| CRC32 | `crc32(col)` | ✅ 标准实现 |
| LENGTH | `char_length(col)` | ✅ 返回字符数（CHAR_COUNT 模式） |

## 8. 已知陷阱

| 陷阱 | 说明 | 处理 |
|------|------|------|
| 分区语法不同 | `PARTITION(name)` vs Hive 的 `WHERE pt=value` | 校验时分区条件由系统生成，需确认方言适配正确 |
| BOOLEAN 格式 | `1`/`0` vs Hive 的 `true`/`false` | 弱内容校验可能因序列化格式不同而报差异 |
| 复杂类型有限 | 无原生 ARRAY/STRUCT | 跨方言校验时复杂类型字段可能需要排除 |
| CHECKSUM 支持 | 需确认 StarRocks 版本是否支持 | 旧版本可能不支持弱内容校验 |
| **ScopeFilter 部分支持** | ❌ partitionCreateTime 不可用 ✅ partitionModifiedTime 可用（`VisibleVersionTime`） | 仅 BY_MODIFY_TIME 可用；LAST_N_PARTITION / LAST_N_DAY 不可用（Worker 白名单也未放行） |
