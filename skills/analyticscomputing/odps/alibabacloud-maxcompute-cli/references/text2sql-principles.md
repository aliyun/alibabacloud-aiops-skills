> Loaded on demand — intent parsing, schema mapping, JOIN/aggregation/filter rules for NL→SQL. Skip unless the agent is generating SQL from a natural-language question.

# Text2SQL general generation principles

Read this file when generating a SELECT query from a natural-language question plus a table schema. This file only covers intent parsing, schema mapping, result granularity, JOINs, aggregation, filtering, and the output contract. MaxCompute syntax, function names, partition format, and `SET` parameters are covered by [maxcompute-select-guide.md](maxcompute-select-guide.md). For partition discovery via the CLI, see [partition-guide.md](partition-guide.md).

---

## 1. Generation order

1. Confirm the project, schema, tables, columns, and date context needed by the question. Do not invent table names, column names, enum values, dates, or join keys. If required schema or date context is missing, ask for it before generating executable SQL or running a query.
2. Decide result granularity: each output row represents an entity row, a time bucket, a group, or a ranking row.
3. Choose the minimal query: SELECT only the columns required, JOIN only the tables required, do not add `DISTINCT` by default, do not add unrelated business filters.
4. Write MaxCompute-executable SQL in one pass: this file only handles logical planning; the final syntax follows [maxcompute-select-guide.md](maxcompute-select-guide.md). Do not produce an intermediate ANSI-SQL draft.

If no usable table is available, or the schema cannot answer the question, ask a concise clarification. If a structured response is required, return empty SQL and explain what is missing. Do not execute SQL that contains unresolved assumptions or placeholders.

---

## 2. Schema mapping

- Prefer table descriptions, column comments, and value-domain hints. When a comment establishes the mapping more clearly than the column name, use that evidence and explain the mapping when it matters.
- When the user mentions an entity attribute (name, status, age, category, etc.), select a verified table that carries that attribute. If several candidates would change the result, ask the user to choose.
- Business metric formulas, eligibility rules, thresholds, currencies, and reporting dates must come from an authoritative definition in the provided context or explicit user confirmation. Do not derive a metric such as revenue, conversion, retention, or a high-value segment from column names alone.
- If two tables have no reliable join path, check for a bridge or relationship table. If the path remains uncertain, ask for clarification rather than executing an assumed JOIN.

---

## 3. Aggregation and filtering

- Use `COUNT(*)` only when each source row represents one requested record,
  order, event, or other counted unit. When the table is at line-item or another
  lower granularity, count a verified entity key instead. For users, customers,
  products, or other entities that can repeat, use `COUNT(DISTINCT entity_id)`
  unless the schema guarantees one entity per row.
- In aggregate queries, every non-aggregate column in `SELECT` must appear in `GROUP BY`. Filter aggregate results with `HAVING`, not `WHERE`.
- For ratios, classifications, conditional counts: use `CASE WHEN` (or the dialect-equivalent), and make the numerator and denominator explicit.
- When value-domain hints are available, resolve filter values from them — never invent enum values.
- Resolve relative time references from the date, time zone, and business-calendar context required by the requested granularity. Ask when a missing value would change the result; do not silently choose today, yesterday, or the latest partition.
- When the schema marks a column as a partition column, push confirmed time-range filters down to that column. If a partition filter is required but the requested range is unknown, stop and ask for the range. A clearly marked placeholder is acceptable only when the user asked for a template, and it must never be executed.

---

## 4. JOIN and ranking

- Pick the driving table first: usually the entity at the heart of the question, or the fact table.
- When you need to keep all rows of the driving table, use `LEFT JOIN` — e.g. "all users and their order count".
- When you only need matched rows, use `INNER JOIN` — e.g. "users who placed an order".
- Every JOIN must have an explicit `ON` condition. Do not use comma-implicit JOINs.
- Watch for one-to-many JOINs that inflate metrics. Pre-aggregate the many-side to the target granularity before the JOIN.
- For global Top/Bottom: `ORDER BY ... LIMIT N`. Use the requested or confirmed value of N; ask when it materially affects the result. Do not truncate output with an arbitrary limit.
- For "Top N per group" / "latest row per entity", use window functions `ROW_NUMBER()` / `RANK()`. Do not substitute a global `LIMIT`.

---

## 5. Output contract

Follow the user's requested output exactly, including whether they want SQL only, an explanation, a table, JSON, or execution results. Do not wrap the answer in an additional format the user did not request. When the user explicitly requests structured output, this shape is available:

```json
{
  "sql": "<generated SELECT query>",
  "explanation": "<brief explanation>",
  "tables": ["table1"],
  "assumptions": ["assumption if any"]
}
```

For structured output when the query cannot yet be generated:

```json
{
  "sql": "",
  "explanation": "Cannot generate SQL: <reason>",
  "tables": [],
  "assumptions": []
}
```

When the user does not specify a format, present the SQL and a concise note on
the verified tables, filters, and any unresolved choice. Execute it only when
the request includes execution and all required values are resolved.

SQL formatting: major clauses on separate lines; `JOIN ... ON` conditions indented; `WHERE` conditions one per line; SQL keywords UPPERCASE; string literals in single quotes.

---

## 6. Anti-patterns

- `SELECT *`, unless a template or the user explicitly asks for all columns.
- Inventing table names, columns, enum values, date context, or join keys.
- JOIN without an `ON` condition; substituting a global `LIMIT` for a per-group Top-N.
- Aggregate query missing `GROUP BY`; using `WHERE` to filter aggregate results.
- Unnecessary `DISTINCT`.
- Adding business filters that the question did not ask for.
- Inventing business metric formulas, segment thresholds, currency precision, reporting dates, or retention definitions.
- Executing SQL with unresolved placeholders or assumptions.
