# 函数选型指南

先按场景选函数分类，再回读 skill 内部的对应 YAML。

## 高频分类

- 数据统计：`./functions/aggregate.yaml`
- 字符串处理：`./functions/string.yaml`
- 正则匹配：`./functions/regex.yaml`
- 时间处理：`./functions/datetime.yaml`
- 类型转换：`./functions/type_conversion.yaml`
- 条件判断：`./functions/conditional.yaml`
- JSON 提取：`./functions/json.yaml`
- 数值计算：`./functions/math.yaml`
- URL 解析：`./functions/url.yaml`
- 数组 / Map：`./functions/array.yaml`、`./functions/map.yaml`
- 窗口分析：`./functions/window.yaml`
- 漏斗分析：`./functions/window_funnel.yaml`
- Lambda 表达式：`./functions/lambda.yaml`

## 语言差异

- SQL + SPL 都支持：字符串、正则、时间、类型转换、条件、JSON、数学、URL、编码、哈希、数组、Map 等大部分基础函数
- 仅 SQL：窗口函数、位运算、空间函数、HyperLogLog、统计函数、漏斗函数等
- 仅 SPL：`ip_to_province`、`ip_to_city`、`ip_to_country`、`ip_to_geo`

## 高频提醒

- 数值比较前必须先 `cast()` 或 `try_cast()`
- 想避免转换失败时整条报错，用 `try_cast()`
- 时间分组优先 `date_trunc()` 或 `date_format()`
- JSON 字段优先 `json_extract()` / `json_extract_scalar()`
- SPL 做转义相关处理，优先看 `ascii_escape`、`ascii_unescape`、`unicode_unescape`
- SPL 中某些函数能力和 SQL 不完全对齐，拿不准时回读对应函数 YAML

## 常见模板

### 类型转换
```sql
* | SELECT count(*) FROM log WHERE cast(status as BIGINT) >= 500
```

```spl
* | where try_cast(status as BIGINT) >= 500
```

### JSON 提取
```sql
* | SELECT json_extract_scalar(payload, '$.user.id') AS user_id, count(*) FROM log GROUP BY user_id
```

### 正则提取
```sql
* | SELECT regexp_extract(message, 'code:(\d+)', 1) AS code, count(*) FROM log GROUP BY code
```

### SPL 地域分析
```spl
* | extend province = ip_to_province(client_ip) | stats pv = count(*) by province
```

## 本地源文档

- `./functions/overview.yaml`
- `./functions/README.md`
- `./functions/*.yaml`
