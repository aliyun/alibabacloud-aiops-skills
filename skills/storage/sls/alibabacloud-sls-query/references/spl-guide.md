# SPL 使用指南

## 1. SPL 适用场景

- 本 skill 只覆盖查询分析里的扫描查询 SPL
- 不覆盖 Logtail 采集处理、写入处理器、实时消费、数据加工等非查询分析场景

## 2. 基本语法

```text
<data-source> | <spl-cmd> | <spl-cmd> | ...
```

- 查询分析里常见数据源是 `*`
- 扫描查询时，`<data-source>` 也可以写索引查询语句
- 如果 `<data-source>` 写的是索引查询语句，那么它会先过滤数据，再把结果交给后面的 SPL 指令
- SPL 管道后不能接 SQL，反之亦然
- 末尾分号可选

## 3. 写 SPL 时必须记住

- 字段默认是 `VARCHAR`
- 做数值比较或计算前先 `cast()` / `try_cast()`
- 字符串常量用单引号
- 字段名包含 `.` `:` `-` 空格等特殊字符时，用双引号
- 非扫描场景默认字段名大小写敏感
- SPL 不做转义处理，`\n` 默认是字面量，不会自动转成换行
- 正则使用 RE2，不支持后向引用和环视

## 4. 推荐流水线顺序

```text
where -> parse -> extend -> project
```

扫描聚合场景常用：

```text
where -> parse -> extend -> stats -> sort -> limit
```

## 5. 高频指令

### `where`
按布尔表达式过滤数据。

```spl
* | where status = '500'
* | where cast(status as BIGINT) >= 500
```

### `extend`
计算新字段，复杂表达式先在这里处理。

```spl
* | extend latency_ms = try_cast(latency as BIGINT)
```

### `parse-json` / `parse-regexp` / `parse-csv` / `parse-kv`
从弱结构化字段里提取结构化字段。

### `stats`
做聚合统计。

```spl
* | stats pv = count(*) by ip
* | extend latency_ms = try_cast(latency as BIGINT) | stats avg_latency = avg(latency_ms) by api
```

关键限制：
- `stats` 里聚合函数只能直接作用于字段，不能直接写表达式
- 如果要 `sum(cast(bytes as BIGINT))`，先在 `extend` 里算出字段再聚合
- 虽然 `stats` 可以做聚合，但在查询分析场景下，除非用户明确要求 SPL，或者已经处于扫描查询/流水线处理中，否则默认优先使用 SQL 来生成分析语句

### `sort` / `limit`
对聚合结果排序和截断。

## 6. 何时优先用扫描查询 SPL

- 字段未建索引，但需要做临时分析
- 需要 `parse` / `extend` / `stats` 这类流水线处理
- 需要在扫描场景里替代索引查询做更灵活的过滤

如果只是常规聚合统计，且字段已经具备索引和统计，优先普通 SQL，不要默认切到 SQL SCAN。
如果某些过滤条件本身可以用索引查询表达，优先把这些条件前置到第一级管道前，再在后面接 SPL。

## 7. 带点字段的处理

如果字段名里有 `.`，先判断它是不是 JSON 子 key 的索引展示形式，而不是真实名字。
常见替代写法：

```spl
* | where json_extract_scalar(fieldA, '$.xxx') = 'value'
```

## 本地源文档

- `./spl/overview.yaml`
- `./spl/where.yaml`
- `./spl/extend.yaml`
- `./spl/parse-json.yaml`
- `./spl/parse-regexp.yaml`
- `./spl/parse-csv.yaml`
- `./spl/parse-kv.yaml`
- `./spl/stats.yaml`
- `./spl/sort.yaml`
- `./spl/limit.yaml`
