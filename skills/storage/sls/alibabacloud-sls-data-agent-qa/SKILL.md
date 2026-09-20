---
name: alibabacloud-sls-data-agent-qa
description: "Query and analyze real data through SLS Context Models to answer business questions. Use when the user asks business data questions using an SLS Context Model. Not for inspecting or managing the models themselves."
metadata:
  name_cn: SLS 业务模型问数
  name_en: SLS Context Model Data QA
  description_cn: 基于 SLS 业务模型查询和分析真实数据，回答业务问题。
  description_en: Query and analyze real data through SLS Context Models to answer business questions.
---
# SLS Context Model Data QA

A Context Model is a semantic layer maintained on top of SLS logs. It contains:

| Model content | Description |
| --- | --- |
| Schema | Logstore descriptions and field definitions: names, types, and business meanings |
| Overview details | Logstore content, business uses, and analysis guidance |
| Metrics | Metric definitions: names, business meanings, and explicit calculation logic |
| Terms | Business term definitions, optionally including identification or calculation logic |
| Example queries | Predefined question-query pairs that can be executed directly |
| Data sources | Physical storage definitions and storage mappings that together determine where queries run |

Semantic content is organized into Elements and Members: a parent Element holds a group of definitions of the same kind, and each definition (such as a field or metric) is a Member.

Before running commands, follow [Python runtime](references/python-runtime.md) to prepare dependencies and credentials.

To answer a business question, follow the workflow below to explore the model, execute queries, validate results, and compose the answer.

## 1. Identify the Context Model and Analysis Objective

Context Model is currently available only in selected regions, such as cn-beijing. If the current endpoint reports that the service is unavailable, explain the reason and ask the user for the model's endpoint or region.

Use the Context Model and model endpoint specified by the user or supplied in context. If the model is missing, list candidates with the following command and ask the user to confirm; paginate according to the returned total rather than treating the first page as the complete list. If the endpoint is missing and cannot be determined from a user-provided region, ask the user to supply it.

```bash
python3 scripts/context_model_qa.py context-model list \
  --endpoint "<context-model-endpoint>" --page 1 --size 20
```

Once the model is selected, clarify the user's analysis objective, target, and known constraints. Explore the model to confirm business definitions and data sources, then develop and refine answer branches as exploration and evidence gathering proceed.

An answer branch is a unit of evidence that can be validated independently and supports one sub-conclusion. Create separate branches for distinct sub-conclusions; multiple queries or data sources needed for the same sub-conclusion remain in one branch. Construct queries, validate evidence, and record sources for each branch, then combine them into the answer.

Typical scenarios:

- Metrics or statistics: each branch addresses a distinct question, such as a metric calculation, trend analysis, or data comparison.
- Investigating an observation or its cause: develop branches from discovered clues, with each branch verifying a specific question.

## 2. Explore the Model, Read Definitions, and Resolve Query Locations

### 2.1 Exploration and Clarification

Explore relevant Elements and Members as needed for the current analysis objective, and confirm the locations required to execute queries. Avoid unrelated content. During exploration:

- Continue exploring to verify information available in the model.
- Read relevant overview details as needed to understand business data and develop the analysis approach.
- When business definitions or analysis scope require a user decision, explain the available options and their differences using verified information, then ask the user to choose.

### 2.2 Model Overview

When candidate Schemas or Elements are unclear, use `catalog overview` to obtain a map of the model.

```bash
python3 scripts/context_model_qa.py context-model catalog overview \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>"
```

Use the result to locate Element and Member names; it does not return the full Member definitions. The default output budget is 28672 bytes. When `truncated: true`, use `omittedSources` / `omittedMembers` to narrow `--sources` / `--members` or increase `--max-bytes`; omission does not mean absence. `modelScope` contains model-level terms not bound to a specific Schema/source. `sources` contains usable semantics assigned to a specific Schema/source. `unresolved` contains content that cannot be reliably assigned to either scope and must not be used as a basis for the current data analysis.

### 2.3 Member Definitions

After locating a candidate Element, use `catalog get` to retrieve the Member definitions needed for the current question. To read only selected Members, pass their exact names with `--members`; omit it to read all Members of that Element.

```bash
# Example: read Schema fields. For other types, use --overview-element,
# --metric-element, --term-element, or --example-query-element. Select exactly one type.
python3 scripts/context_model_qa.py context-model catalog get \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>" --schema-element "<element>" \
  --members "member1,member2"
```

- `members` contains the available definitions actually returned. `missingMembers` lists Members requested through `--members` that do not exist.
- For a Member with `confidence`, `confidence.status` indicates whether its semantics (such as field descriptions or metric definitions) have been accepted. Both `auto_applied` and `manually_applied` mean accepted and can be trusted directly. `not_applied` means not yet accepted: treat it as a candidate clue and verify it against actual data before using it to define a query. Factual attributes such as field types are not subject to this restriction.

### 2.4 Query Locations

After identifying the Schema for an answer branch, use `catalog resolve` to obtain the locations required for log queries.

```bash
python3 scripts/context_model_qa.py context-model catalog resolve \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>" --schema "<schema-element>"
```

- `datasources` contains candidate query locations for the current answer branch, not automatically separate branches. Each entry is a set of location parameters; `store` maps to the subsequent query command's `--logstore` parameter.
- Log queries and index reads use the resolved `region/project/store`. Pass a custom log endpoint separately when needed; do not reuse the model endpoint.
- If a data source has a nonempty `search_filter`, parenthesize it and the business query's search prefix separately, then combine them with `AND`. If the original prefix is `*`, use the filter directly.
- If the user specifies a single resource, query only that resource. If the user specifies a resource set, query every location within that scope.
- If the investigation target's location is unknown, query all relevant candidates.
- Ask the user when scope is unclear, candidates are too numerous, or the aggregation method is uncertain. Do not select a "primary" data source on your own.

## 3. Construct Queries and Gather Additional Evidence

### 3.1 Semantic Basis

For each answer branch, choose its semantic basis in the following order; do not proceed to a later option when an earlier one applies. When using model Schemas, metrics, terms, or example queries, rely on definitions already retrieved.

1. **Example query**: when its meaning matches the question, use the original query. Literal values may be replaced based on the question or verified evidence, without changing the business definition.
2. **Metric**: assemble a complete query using the generator mapping in Section 3.2.
3. **Term**: when the question contains a defined term, express its identification or calculation logic as filters or expressions.
4. **Query from Schema fields**: when none of the above applies, construct a query from field names, types, and descriptions.

Gather additional evidence as needed when the information required to construct a query is missing.

### 3.2 Query Assembly

**Query structure**

A complete query takes the form `<search-prefix> | <SQL-statement>`. The default search prefix is `*`. SQL reads the current Logstore through `FROM log`. When SQL analysis is unnecessary, the query contains only the search expression.

Specify the log time range through command parameters; do not repeat the same `__time__` filter in the search prefix or SQL.

**Metric generator mapping**

A metric generator consists of an aggregate expression and an optional `FILTER (WHERE ...)`. To construct a query from a generator:

1. Put the aggregate expression in `SELECT` and add an alias that reflects its business meaning.
2. If `FILTER` contains `search(...)`, use its entire string argument as the search prefix.
3. If `FILTER` contains other SQL predicates, put them in `WHERE`; otherwise omit `WHERE`.

Preserve the generator's filters, literals, aggregate functions, and units. After moving the string argument of `search(...)` to the search prefix, do not split it, duplicate it, or derive additional `WHERE` conditions from it.

Combine multiple metrics in one `SELECT` only when their mapped search prefixes and `WHERE` conditions are identical; otherwise execute them separately.

**Custom filters**

When constructing filters, prefer narrowing the analysis with the search prefix while preserving matching semantics. Text matching in the search prefix depends on index tokenization. To require an exact match of the entire field value, use `=` in SQL `WHERE`.

**Row limits**

SLS SQL returns at most 100 rows by default when `LIMIT` is omitted. If more results are needed, set an explicit `LIMIT` in the final SQL.

### 3.3 Additional Evidence

**Index configuration**

Read the index configuration when you need to verify search and analytics capabilities, index types, tokenization, or other matching rules.

```bash
python3 scripts/context_model_qa.py index get \
  --region "<region>" --project "<project>" --logstore "<logstore>"
```

**Log samples**

Read a small number of relevant logs when you need to verify actual data structure, field paths, values, or formats.

- Set `--query` to verified keywords or field filters, such as `error` or `k1:v1 AND k2:v2`; use `*` if no reliable filter is available.
- Prefer the current question's time range for `--time-range`; use `--lines` to bound the number of sample rows.

```bash
python3 scripts/context_model_qa.py query \
  --region "<region>" --project "<project>" --logstore "<logstore>" \
  --query "<search-prefix>" --time-range "<time-range>" \
  --lines <bounded-sample-rows>
```

Samples are for internal verification. Do not copy them wholesale into the final answer; cite only necessary, redacted evidence.

### 3.4 References as Needed

| Document | Purpose |
| --- | --- |
| [SLS function reference](references/sql/functions.md) | SLS-specific behavior for time comparisons, bucketing, JSON, regex, approximate aggregations, and IP geolocation. |
| [Cross-Logstore JOIN](references/sql/join.md) | Execution requirements, join relationships, and SQL templates for cross-Logstore queries. |
| [Scan analysis (SCAN)](references/sql/scan.md) | Syntax and limitations for fields without indexes or analytics enabled. |

## 4. Execute Queries, Validate Results, and Handle Errors

### 4.1 Execute Queries

Choose a bounded time range for each answer branch based on the question and available evidence.

- Use `--time-range` for a relative range (such as `last_15m`, `last_1h`, `now-1h~now`, `today`, or `yesterday`) or an explicit interval. Explicit intervals use `<start-time>~<end-time>`, with both endpoints in RFC3339 format including a time zone.
- For comparisons within one window or aggregation across sources, reuse a fixed time window. For comparisons across periods, define and align each window separately.

Ask the user if the time range cannot be determined.

```bash
python3 scripts/context_model_qa.py query \
  --region "<region>" --project "<project>" --logstore "<logstore>" \
  --query "<complete-query>" \
  --time-range "<time-range>"
```

If start and end timestamps are already available, replace the time parameter above with:

```bash
--from "<FROM_TS>" --to "<TO_TS>"
```

For log searches, add `--lines <bounded-result-rows>` as needed; the default is 100 rows. SQL row limits are controlled by `LIMIT`.

### 4.2 Validate Results

After successfully obtaining a query response, confirm:

1. `meta.progress == "Complete"`, indicating that the query completed fully.
2. The returned fields and result shape match the current question. When all groups or time-series points are required, verify that row limits have not truncated the results.

`logs: []` means no rows were returned, not the numeric value 0. A scalar aggregate returning 0 is an actual calculated result. Never interpret a failed or incomplete query as no data.

The top-level `timeRange.from/to` in a successful query response records the actual query window in Unix seconds. Use this window for the answer's execution scope and chart time range; do not derive it again.

### 4.3 Handle Errors

Handle errors based on script messages, the top-level `error` in a failed response, or `meta.progress` in a query response. Do not bypass errors by switching data sources, removing filters, shortening the user's requested time range, or changing business definitions. If recovery is impossible, stop and explain the known cause, unfinished queries, and any additional information required.

| Error | Action |
| --- | --- |
| Parameter, SQL, function, or JOIN error | Correct the issue reported by the error; consult the [SLS function reference](references/sql/functions.md) or [Cross-Logstore JOIN](references/sql/join.md) as needed. |
| Field parsing or index configuration error | Correct the issue using known field information. Gather more evidence if needed; consult [Scan analysis (SCAN)](references/sql/scan.md) when scanning is necessary. |
| Throttling, service busy, or request timeout | Wait and retry with the same query and time range. Stop and report persistent failures. |
| `meta.progress == "Incomplete"` | Diagnose and recover using [Incomplete and inexact query results](references/sql/incomplete.md). |
| Authentication failure, access denied, or resource not found | Correct clear parameter errors; otherwise stop and report. |

## 5. Deliver the Answer and Charts

### 5.1 Answer Rules

Base data conclusions only on query results that passed validation.

- State the business definitions used (citing metric, term, or example-query names) and actual execution scope (project/logstore and time window). Include the executed queries for numerical and statistical conclusions, and key evidence for investigative conclusions.
- For multiple branches or data sources, identify each result's source and status: available, no rows, failed, or not executed. Claim complete coverage only when all required queries pass validation; qualify the scope of conclusions when coverage is partial.
- Aggregate across sources only when definitions, filters, and time windows match and the results can be combined. Separate per-source results do not establish unverified relationships between records.
- Disclose approximations, coverage limits, and data-processing constraints that affect the conclusions.
- Do not expose endpoints, credentials, internal element identifiers, exploration queries, or unredacted diagnostic information.

### 5.2 Chart Delivery

When validated results are suitable for visualization (trends, TopN/category comparisons, shares across a few categories, details with multiple columns, or flows across time and categories), read [chart-delivery.md](references/chart-delivery.md) and follow it to deliver charts or tables. Do not chart scalar results or results unsuitable for visualization.
