# ClickHouse

方言族：独立方言

## 1. 分区查询语法

```sql
-- WHERE 子句（ClickHouse 分区由 ORDER BY key 决定，无显式分区语法）
SELECT COUNT(*) FROM table_name WHERE dt = '20240602';
```

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| JSON | 不支持原生 JSON | — |
| ARRAY 元素 | `col[index]`（0-based） | `tags[0]` |
| ARRAY 长度 | `length(col)` | `length(tags)` |
| ARRAY 展开 | `arrayJoin(col)` | `SELECT arrayJoin(tags) FROM table_name` |
| MAP 访问 | `col['key']` | `properties['name']` |
| MAP 键 | `mapKeys(col)` | `mapKeys(properties)` |

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | — |
| COUNT DISTINCT | `uniq(col)` 更高效 | `COUNT(DISTINCT col)` 也可用但较慢 |
| 字符串聚合 | `groupArray(col)` | 返回数组而非字符串 |

## 4. NULL 处理

```sql
ifNull(col, default_value)
```

## 5. DECIMAL 格式化

```sql
-- 复杂的嵌套表达式（约 30 行），处理 scale 补齐
CAST(if(position(...)))
```

## 6. BOOLEAN 表示

`1` / `0`（ClickHouse 无原生 BOOLEAN，用 UInt8 表示）

## 7. 校验算法

| 算法 | 函数 | 可用性 |
|------|------|--------|
| MD5 | `lower(hex(MD5(col)))` | ✅ 需要 lower+hex 包装 |
| CRC32 | — | ❌ 返回类型不同（与其他方言不兼容） |
| LENGTH | `lengthUTF8(col)` | ✅ 返回字符数（CHAR_COUNT 模式） |

## 8. 已知陷阱

| 陷阱 | 说明 | 处理 |
|------|------|------|
| 无 CRC32 兼容 | CRC32 返回类型与其他方言不同 | 弱内容校验使用 MD5 |
| 无原生 JSON | 不支持 JSON 类型 | 跨方言校验 JSON 字段需排除或用字符串比对 |
| BOOLEAN 格式 | `1`/`0` vs Hive 的 `true`/`false` | 弱内容校验可能报差异 |
| Nullable 类型 | ClickHouse 使用 Nullable 包装类型 | JOIN 时默认值处理可能不同 |
| MD5 格式 | 需要 `lower(hex(MD5(col)))` 包装 | 系统已自动处理 |
| **ScopeFilter 部分支持** | ❌ partitionCreateTime 不可用 ✅ partitionModifiedTime 可用（`modification_time`） | 仅 BY_MODIFY_TIME 可用（SDK 层）；LAST_N_PARTITION / LAST_N_DAY 不可用；Worker 白名单也未放行 |
