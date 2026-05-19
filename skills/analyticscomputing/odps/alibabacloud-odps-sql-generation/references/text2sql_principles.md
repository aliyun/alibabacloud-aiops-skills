# Text2SQL 通用生成原则

自然语言问题 + 表结构生成 SELECT 查询时读取此文件。本文只负责意图解析、schema 映射、结果粒度、JOIN、聚合、过滤和输出契约；MaxCompute 语法、函数、分区格式和 SET 参数由 `maxcompute_select_guide.md` 覆盖。

---

## 1. 生成顺序

1. 确认可用表和字段：只使用上下文提供的 schema，不臆造表名、列名、枚举值、日期上下文或 join key。
2. 确定结果粒度：一行代表实体明细、时间粒度、分组结果，还是排名结果。
3. 选择最小查询：只 SELECT 必要列，只 JOIN 必要表，不默认 DISTINCT，不加无关业务过滤。
4. 一次性写出 MaxCompute 可执行 SQL：本文只做逻辑规划；最终语法以 `maxcompute_select_guide.md` 为准，不产出 ANSI SQL 中间稿。

如果没有可用表，或 schema 无法回答问题，返回空 SQL 并说明缺失信息。

---

## 2. Schema 映射

- 优先使用表描述、字段注释和值域提示；注释比字段名更贴近用户意图时，按注释选列并写入 assumptions。
- 用户提到实体属性（名称、状态、年龄、类目等）时，选择承载该属性的实体表，即使用户没有直接说表名。
- 没有现成指标时才派生计算，例如收入可由 `price * quantity` 得到；派生逻辑写入 explanation 或 assumptions。
- 两表无可靠 join path 时不要硬连；可查桥表/关系表，仍不确定则返回空 SQL 或写明假设。

---

## 3. 聚合与过滤

- 问记录/订单/事件数量通常用 `COUNT(*)`；问用户/客户/商品数量通常用 `COUNT(DISTINCT entity_id)`，除非 schema 已保证一行一个实体。
- 聚合查询中，SELECT 的非聚合列必须进入 GROUP BY；聚合结果过滤用 HAVING。
- 比率、分类、条件计数用 `CASE WHEN` 或方言层提供的等价函数，并明确分子分母。
- 有值域提示时优先按值域解析过滤值；不要编造枚举。
- 相对时间必须依赖提供的日期上下文；没有日期上下文时使用占位符并写入 assumptions。
- 表结构标记分区列时，时间范围优先落到分区列；如果方言要求分区过滤但用户未给时间范围，按方言层选择最新分区、占位符或全表扫描开关，并写入 assumptions。

---

## 4. JOIN 与排名

- 先确定主表：通常是问题主体实体或事实表。
- 需要保留主表所有行时使用 LEFT JOIN，例如"所有用户及其订单数"。
- 只需要匹配行时使用 INNER JOIN，例如"下过单的用户"。
- 每个 JOIN 必须有显式 ON 条件；禁止逗号隐式 JOIN。
- 警惕一对多 JOIN 放大指标；聚合前先把多端表压到目标粒度。
- 全局 Top/Bottom 用 ORDER BY + LIMIT；用户未给 N 时按上下文决定是否加 LIMIT，并写入 assumptions。
- "每组 Top N"、"每个实体最新一条" 使用 `ROW_NUMBER()` / `RANK()` 窗口函数，不要用全局 LIMIT 代替。

---

## 5. 输出契约

如果用户或调用方指定了输出格式，优先遵守该格式。否则，自然语言生成 SELECT 时返回纯 JSON，不要包 markdown code fence：

```json
{
  "sql": "<generated SELECT query>",
  "explanation": "<brief explanation>",
  "tables": ["table1"],
  "assumptions": ["assumption if any"]
}
```

无法回答时：

```json
{
  "sql": "",
  "explanation": "Cannot generate SQL: <reason>",
  "tables": [],
  "assumptions": []
}
```

SQL 排版要求：主要子句分行，JOIN 的 ON 条件缩进，WHERE 条件逐行列出，SQL 关键字大写，字符串字面量用单引号。

---

## 6. 反模式

- `SELECT *`，除非模板或用户明确要求透传所有列。
- 编造表、字段、枚举值、日期上下文或 join key。
- 没有 ON 条件的 JOIN；用全局 LIMIT 代替每组 Top N。
- 聚合查询遗漏 GROUP BY；用 WHERE 过滤聚合结果。
- 不必要的 DISTINCT。
- 在问题未要求时加额外业务过滤。
