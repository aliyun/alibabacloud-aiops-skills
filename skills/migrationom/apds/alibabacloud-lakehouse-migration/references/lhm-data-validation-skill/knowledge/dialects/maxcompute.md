# MaxCompute (ODPS)

方言族：独立（非 JDBC，SDK 直连）

## 1. 分区查询语法

```sql
-- 标准 WHERE 子句
SELECT COUNT(*) FROM table_name WHERE pt = '20240602';

-- 全表扫描需设置参数
SET odps.sql.allow.fullscan = true;
```

**注意**: 分区表必须设置 `odps.sql.allow.fullscan=true` 才能全表扫描，否则查询失败。

## 2. 复杂类型语法

| 类型 | 访问语法 | 示例 |
|------|---------|------|
| JSON 子字段 | `get_json_object(col, '$.field')` | `get_json_object(metadata, '$.id')` |
| STRUCT 子字段 | `col.field` | `address.city` |
| ARRAY 元素 | `col[index]`（0-based） | `tags[0]` |
| ARRAY 长度 | `size(col)` | `size(tags)` |
| ARRAY 排序 | `sort_array(col)` | `sort_array(tags)` |
| ARRAY 展开 | `LATERAL VIEW explode(col) t AS val` | `LATERAL VIEW explode(tags) t AS tag` |
| MAP 键 | `map_keys(col)` | `map_keys(properties)` |
| MAP 值 | `map_values(col)` | `map_values(properties)` |
| MAP 访问 | `col['key']` | `properties['name']` |

**类型系统**: 2.0 版本需设置 `SET odps.sql.type.system.odps2 = true` 才能使用 ARRAY/MAP/STRUCT/JSON。

## 3. 聚合函数

| 函数 | 语法 | 特殊行为 |
|------|------|---------|
| SUM/AVG/MIN/MAX | 标准 | AVG 使用精确 DECIMAL 计算（非 float） |
| COUNT DISTINCT | 标准 | — |
| 字符串聚合 | `WM_CONCAT(',', col)` | 非标准函数名 |
| 收集为数组 | `COLLECT_LIST(col)` / `COLLECT_SET(col)` | — |
| 近似百分位 | `PERCENTILE_APPROX(col, 0.5)` | — |

## 4. NULL 处理

```sql
NVL(col, default_value)
```

## 5. DECIMAL 格式化

```sql
-- 使用 replace + format_number 去掉千分位逗号
replace(format_number(CAST(col AS DECIMAL(p,s)), s), ',', '')
```

无 DECIMAL 前导零问题（与 PG 系不同）。

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
| 全表扫描禁止 | 分区表未设 `odps.sql.allow.fullscan=true` 时查询失败 | 必须配置 global_params |
| 类型系统 1.0 | 默认 1.0 只支持 BIGINT/STRING/DATETIME/BOOLEAN | 设置 `odps.sql.type.system.odps2=true` |
| 隐式转换宽松 | STRING→NUMBER 隐式转换返回 NULL 而非报错 | 建议显式 CAST |
| TRY_CAST | 2.0+ 支持，失败返回 NULL | 1.0 不支持 |
| **ScopeFilter 支持** | ✅ 分区级过滤全部可用（partitionCreateTime + partitionModifiedTime 均可获取） | LAST_N_PARTITION / LAST_N_DAY / BY_MODIFY_TIME / BY_CREATE_TIME |
