---
name: alibabacloud-sls-data-agent-qa
description: "Use the semantic definitions in SLS Source Models or Context Models to identify fields, metrics and business definitions, query and analyze log data, and answer business questions. Not for inspecting or managing models themselves."
metadata:
  name_cn: SLS Data Agent 问数
  name_en: SLS Data Agent QA
  description_cn: 基于 SLS 事实模型或业务模型查询和分析日志数据，回答业务问题。
  description_en: Query and analyze log data through SLS Source Models or Context Models to answer business questions.
---
# SLS Data Agent QA

Use the semantic definitions in SLS Source Models or Context Models to explore models, establish data selection criteria, execute queries and validate their results, and answer the user's business questions.

## Prerequisites

Requires Python 3.10+ and Alibaba Cloud credentials.

See [Python runtime](references/python-runtime.md) for dependency installation and endpoint configuration.

## Model concepts

- **Source Model**: A factual model organized by SLS Project, containing semantic definitions and query data sources for modeled logs.
- **Context Model**: A business model that organizes relevant definitions from modeled Logstores in one or more Projects for business analysis, managed under its own model name.

| Model content | Description |
| --- | --- |
| Schema | Logstore description and field definitions: field names, types and business meanings |
| Overview details | Business descriptions and analysis guidance for a Logstore, which may include data selection rules, differences in business definitions, applicable conditions and limitations |
| Metrics | Metric definitions: names, business meanings and calculation logic |
| Terms | Business term definitions, which may include matching or calculation logic |
| Example queries (Context Model only) | Predefined questions and queries |
| Query data sources | Physical storage locations and mappings from Schemas to those locations, used to determine where queries run |

Model content is organized into Elements. Semantic Elements, such as Schemas and metrics, contain definitions of the same type. Each definition is a Member, such as a field or a metric.

## 1. Establish the analysis goal and explore the model

Identify the analysis goal, the subjects to analyze and existing constraints from the user's business question. Preserve model names/UUIDs, Projects/Logstores, time ranges and other constraints supplied by the user or context. Explore the model to confirm business definitions and data sources, progressively developing and refining answer branches as evidence becomes available.

An answer branch is a unit of evidence that can be validated independently and supports one finding. Use separate branches for distinct findings; multiple queries or data sources needed for the same finding remain in one branch. Construct queries, validate evidence and record data sources for each branch, then combine the findings into the answer.

Typical scenarios:

- Metrics or statistics: each branch addresses an independent question, such as a metric calculation, trend analysis or data comparison.
- Investigating an observation or its cause: develop branches from discovered clues, with each branch investigating a specific issue.

**Model selection**

Explicit user choices take precedence over context defaults. If the model choice is unclear or information conflicts, ask the user to clarify; do not select another model or resource on your own.

| Model | Selection criteria and guidance |
| --- | --- |
| Source Model | When the user explicitly selects a Source Model, or no model has been selected but a current Project/Logstore is available, read [Exploring a Source Model and reading definitions](references/source-model.md). |
| Context Model | When a Context Model name/UUID is provided, or the user explicitly requests a business model, read [Exploring a Context Model and reading definitions](references/context-model.md). |

**Exploration and clarification**

Follow the preparation steps for the selected model, read relevant definitions as needed and determine the actual query location based on the analysis goal and information gaps. During exploration:

- Before deriving data selection criteria or deciding what to investigate, read the original overview details for the relevant Logstore, if present, to understand its business context, data selection rules and limitations.
- When business definitions or analysis scope require a user decision, explain the options and their differences using verified information and ask the user to choose.

## 2. Construct queries and gather supporting evidence as needed

### 2.1 Construct queries

For each answer branch, construct queries from the user's question and the relevant model definitions already obtained. Check what is being measured, the business definitions and the applicable scope.

- **Reuse existing logic**: When an applicable example query or metric exists, use its data selection and calculation logic to assemble the query.
- **Construct a query**: Otherwise, write the query from confirmed definitions.

**Query structure**

A complete query has the form `<search-prefix> | <SQL-statement>`. The default search prefix is `*`, and SQL reads the current Logstore through `FROM log`. When SQL analysis is unnecessary, the query contains only the search prefix.

Specify the log time range through command parameters; do not repeat the same range as a `__time__` filter in the search prefix or SQL.

**Mapping metrics and terms**

| Definition format | Query mapping |
| --- | --- |
| Metric `generator`: text divided into labeled sections | Use `Metric Expression` in the `SELECT` calculation. Optional `Log Search Filter` and `SQL WHERE Condition` sections map to the search prefix and SQL `WHERE`, respectively. |
| Metric `generator`: SQL calculation expression, possibly containing `FILTER (WHERE ...)` | Use the expression in `SELECT`. When `FILTER` selects the input for the entire metric and can be split without changing its meaning, use the complete string argument of `search(...)` as the search prefix and place the remaining SQL predicates in `WHERE`. If there are no SQL predicates, do not add a corresponding `WHERE` condition. Keep `FILTER` clauses that apply only to individual aggregates inside their calculation expressions. |
| Term `description` | The description may be followed by `Log Search Filter` and `SQL WHERE Condition`; apply the same mapping. |

- Do not change the original definition's calculation logic, filters, literals or units when constructing queries.
- Combine multiple metrics in one `SELECT` only when their effective search prefixes and `WHERE` conditions are identical; otherwise execute them separately.

**Assembling filters**

When constructing filters, use the search prefix, SQL `WHERE`, or both:

- **Search prefix**: Common forms include keyword searches (`term`) and field searches (`field:value`). Fields indexed as `long` or `double` also support numeric comparisons (`field > value`) and range searches (`field in [min max]`). **For fields indexed as `text`, `field:value` matches tokenized terms and does not guarantee equality with the full field value.**
- **SQL `WHERE`**: Further filter logs matched by the search prefix using field values, such as full-string equality, `LIKE` / `NOT LIKE` pattern matching or regular expressions.

Wildcard searches in the search prefix, such as `field:abc*`, have a limit on the number of matching terms. Do not use them to replace SQL `LIKE` / `NOT LIKE` conditions or append corresponding wildcard searches while retaining those conditions.

**Result row limits**

SLS SQL returns at most 100 rows by default when `LIMIT` is omitted. If more results are needed, specify an appropriate `LIMIT` in the final SQL.

### 2.2 Gather supporting evidence as needed

**Index configuration**

Inspect index configuration when you need to confirm search and statistical analysis capabilities, index types, tokenization or other matching rules.

```bash
python3 scripts/model_qa.py index get \
  --region "<region>" --project "<project>" --logstore "<logstore>"
```

**Log samples**

Read a small number of relevant logs when you need to confirm actual data structures, field paths, values or formats.

- For `--query`, use verified keywords or field filters, such as `error` or `k1:v1 AND k2:v2`; use `*` when no reliable filter is available.
- Use the established time range for `--time-range` and limit the number of sample rows with `--lines`.

```bash
python3 scripts/model_qa.py query \
  --region "<region>" --project "<project>" --logstore "<logstore>" \
  --query "<search-prefix>" --time-range "<time-range>" \
  --lines <bounded-sample-rows>
```

Samples are for internal verification. Do not copy them wholesale into the final answer; cite only necessary, redacted evidence.

### 2.3 References to consult as needed

| Document | Purpose |
| --- | --- |
| [SLS function reference](references/sql/functions.md) | SLS-specific usage of time comparisons, bucketing, JSON, regular expressions, approximate aggregations and IP geolocation functions. |
| [Cross-Logstore JOIN](references/sql/join.md) | Execution requirements, join criteria and SQL templates for queries across Logstores. |
| [Scan analysis (SCAN)](references/sql/scan.md) | Syntax and limitations for fields without indexes or statistical analysis enabled. |

## 3. Execute, validate and handle errors

### 3.1 Execute queries

Determine each answer branch's time range from the question and available evidence. Ask the user to clarify when it cannot be determined.

- Time boundaries: `query` includes the start and excludes the end. For a complete calendar period, use the start of the next period as the end.
- `--time-range`: Specify a relative range, such as `last_15m`, `last_1h`, `now-1h~now`, `today` or `yesterday`, or an explicit interval. Use `<start>~<end>` for an explicit interval, with both endpoints in RFC3339 format including time zones.
- Window reuse: Reuse the same fixed start and end for comparisons within one window or aggregation across sources, avoiding shifts caused by resolving relative ranges separately.

```bash
query_suffix="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')" && \
python3 scripts/model_qa.py query \
  --region "<region>" --project "<project>" --logstore "<logstore>" \
  --query "<complete-query>" \
  --time-range "<time-range>" \
  --save-file "<absolute-path-to-temp-directory>/<query-purpose>-${query_suffix}.json"
```

**Additional parameters**

- `--from "<FROM_TS>" --to "<TO_TS>"`: Use these instead of `--time-range` when start and end timestamps are already available.
- `--lines`: Optional, defaults to 100 rows, and applies only when the query contains a search prefix without SQL.

### 3.2 Validate results

After receiving a successful query response, verify:

1. **Execution status**: `meta.progress == "Complete"` means the query executed completely. Do not interpret failed or incomplete execution as no data.
2. **Result shape**: Fields and result structure meet the question's requirements. When all groups or a complete time series are needed, confirm that results were not truncated by the return limit.

`logs: []` means the current query returned no rows, not a numeric zero. A zero returned by a scalar aggregate is an actual calculation result.

The top-level `timeRange.from/to` in a successful query response records the actual execution window in Unix seconds. Use it for the execution range in the answer and for chart time windows; do not derive the window again.

### 3.3 Handle errors

Handle failures using CLI error messages, the top-level `error` in failed responses, or `meta.progress` in query responses. Do not evade errors by changing data sources, removing filters, shortening the user's requested time range or changing business definitions. If recovery is not possible, stop and explain the known cause, unfinished queries and required additional information.

| Error | Handling |
| --- | --- |
| Parameter, SQL, function or JOIN error | Correct it according to the error; consult the [SLS function reference](references/sql/functions.md) or [Cross-Logstore JOIN](references/sql/join.md) as needed. |
| Field parsing or index configuration error | Correct it using known field information. Gather supporting evidence if needed; consult [Scan analysis (SCAN)](references/sql/scan.md) when scanning is required. |
| Throttling, service busy or request processing timeout | Wait and retry with the same query and time range. Stop and report persistent failures. |
| `meta.progress == "Incomplete"` | Follow [Incomplete and inexact query results](references/sql/incomplete.md) to identify the cause and recover. |
| Authentication failure, permission denied or resource not found | Correct clear parameter errors; otherwise stop and report. |

## 4. Deliver results

### 4.1 Organize the answer

Organize the answer into conclusions and query evidence where appropriate.

- Base conclusions only on validated query results. Claim complete coverage only when all required queries pass validation; otherwise identify gaps and limit the scope of the conclusions. Explain approximations and data processing limitations that affect conclusions.
- Aggregate results across sources only when their definitions, filters and time windows are consistent and the results can be combined. Separate source results do not establish record-level relationships.
- In the query evidence, use Markdown code blocks to show the complete executed queries supporting the main conclusions, with their data sources and actual time windows. Use a short title that describes each query's business purpose; keep it consistent with the corresponding chart title, if any.
- Do not display endpoints, credentials, internal Element identifiers or unredacted diagnostic information.

**Query presentation**

- State the confirmed Region, Project and Logstore. Express the time window in Unix seconds; for executed queries, reuse `timeRange.from/to` from the response.
- Present complete queries in ordinary Markdown, without depending on internal `run_query` / `vibeops_object` rendering protocols.
- Label queries that were not executed or failed with their status.

### 4.2 Deliver charts

When results suit visualization, such as trends, TopN/category comparisons, shares across a few categories, multi-column details or flows by time and category, follow [Chart delivery](references/chart-delivery.md) and use the current host's chart capabilities near the corresponding conclusions. Use Markdown tables when chart capabilities are unavailable. Do not chart scalar results or results unsuitable for visualization.

### 4.3 Extract query execution details

Use the following command with the absolute paths to saved query record files supporting the main conclusions to extract complete queries, data sources, actual time windows and execution parameters for the query evidence.

```bash
python3 "<absolute-path-to-skill-directory>/scripts/export_query_evidence.py" \
  "<absolute-path-to-query-record-1.json>" \
  "<absolute-path-to-query-record-2.json>"
```
