# Azure Synapse

方言族：独立方言

## 1. 分区查询语法

```sql
SELECT COUNT(*) FROM table_name WHERE dt = '20240602';
```

## 2. 复杂类型语法

| 类型 | 访问语法 |
|------|---------|
| JSON | `JSON_VALUE(col, '$.field')` |
| 无原生 ARRAY/STRUCT | — |

## 3. 聚合函数

| 函数 | 语法 |
|------|------|
| 字符串聚合 | `STRING_AGG(col, ',')` |

## 4. NULL 处理

```sql
ISNULL(col, default_value)
```

## 5. DECIMAL 格式化

```sql
CAST(CAST(col AS DECIMAL(p,s)) AS VARCHAR)
```

## 6. BOOLEAN 表示

`1` / `0`

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `LOWER(CONVERT(VARCHAR(32), HASHBYTES('MD5', col), 2))` | ✅ |
| CRC32 | — | ❌ 不支持 |
| LENGTH | `LEN(col)` | ✅ 字符数 |

## 8. 已知陷阱

| 陷阱 | 说明 |
|------|------|
| 无 CRC32 | 弱内容校验使用 MD5 |
| NULL 函数不同 | 使用 `ISNULL` 而非 `COALESCE` 或 `NVL` |
| MD5 格式复杂 | 需要 `LOWER(CONVERT(VARCHAR(32), HASHBYTES('MD5', col), 2))` |
| BOOLEAN 格式 | `1`/`0` vs Hive 的 `true`/`false` |
