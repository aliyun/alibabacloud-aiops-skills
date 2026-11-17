# Model-based data analysis

Use the semantic definitions in an SLS Source Model or Context Model to explore the model, establish business calculation rules, execute queries, and validate results to answer the user's business question.

## Model concepts

- **Source Model**: organized by SLS Project, containing semantic definitions and query data sources for modeled logs.
- **Context Model**: organizes related definitions for modeled Logstores in one or more Projects for business analysis, managed under an independent model name.

| Model content | Description |
| --- | --- |
| Schema | Logstore description and field definitions: field names, types, and business meanings |
| Overview details | Business descriptions and analysis guidance for the Logstore, which may include business retrieval rules, differences in calculation rules, applicable conditions, and limitations |
| Metrics | Metric definitions: names, business meanings, and established calculation logic |
| Terms | Business term definitions, which may include identification or calculation logic |
| Example queries (Context Model only) | Defined questions and query statements |
| Query data sources | Physical storage and mappings from Schema to physical storage, used to determine where queries execute |

Model content is organized into Elements. Semantic Elements such as Schema and metrics hold a group of definitions of the same kind. Each definition is called a Member, such as a field or metric.

## 1. Establish the analysis goal and explore the model

Clarify the analysis goal, objects of analysis, and existing constraints around the user's business question. Preserve model names/UUIDs, Project/Logstore, time ranges, and other information supplied by the user or context as existing constraints. Use model exploration to confirm business calculation rules and data sources, developing and refining answer branches as exploration and evidence collection progress.

An answer branch is a unit of evidence that can be validated independently and support one sub-conclusion. Create separate branches for different sub-conclusions; multiple queries or data sources needed for the same sub-conclusion remain in one branch. Construct queries, validate evidence, and record data sources for each branch, then combine the answers.

Typical scenarios:

- Querying metrics or statistics: each branch addresses an independent question, such as metric statistics, trend analysis, or data comparison.
- Investigating a phenomenon or cause: develop branches from exploration findings, with each branch verifying a specific question.

**Model selection**

Explicit user choices take precedence over context defaults. Ask the user to clarify an unclear path or conflicting information; do not select another model or resource on your own.

| Model | Selection criteria and reference |
| --- | --- |
| Source Model | When the user explicitly selects a Source Model, or no model has been selected but a current Project/Logstore is available, read [Source Model exploration and definition reads](model-data-qa/source-model.md). |
| Context Model | When a Context Model name/UUID is supplied, or the user explicitly requests a business model, read [Context Model exploration and definition reads](model-data-qa/context-model.md). |

**Exploration and clarification principles**

For the current analysis goal and information gaps, prepare the model as described for the selected model, read relevant definitions as needed, and determine the actual query location. Follow these principles during exploration:

- Before deriving retrieval or calculation rules or choosing an investigation direction yourself, read the original overview details for the relevant Logstore, if present, to understand business background, retrieval rules, and applicability limits.
- When business calculation rules or analysis scope require a user decision, explain the verified options and their differences and ask the user to choose.

## 2. Construct queries and gather additional evidence as needed

### 2.1 Construct queries

Construct queries for each answer branch from the user's question and the relevant model definitions already obtained. Check the objects being counted, business calculation rules, and applicability.

- **Reuse existing logic**: when example queries or metrics match the question's counting unit and any requested state selection, use their retrieval and calculation logic to assemble the query.
- **Construct a query yourself**: otherwise, write the query from confirmed definitions.

**Query structure**

A complete query has the form `<search-prefix> | <SQL-analysis-statement>`. The default search prefix is `*`, and SQL reads the current Logstore through `FROM log`. When SQL analysis is unnecessary, the query consists only of the search prefix.

Specify the log time range through command parameters; there is no need to filter `__time__` for the same range again in the search prefix or SQL.

**Mapping metrics and terms**
| Content form | Query mapping |
| --- | --- |
| Metric `generator`: text divided by labels | Use `Metric Expression` as a `SELECT` calculation expression; optional `Log Search Filter` and `SQL WHERE Condition` supply the search prefix and SQL `WHERE`, respectively |
| Metric `generator`: a SQL calculation expression, possibly containing `FILTER (WHERE ...)` | Use the expression in `SELECT`. When `FILTER` filters the input of the whole metric and can be split equivalently, use the entire string argument of its `search(...)` as the search prefix and put the remaining SQL predicates in `WHERE`; do not add a `WHERE` condition when there are no SQL predicates. Keep aggregate-local `FILTER` in the calculation expression |
| Term `description` | The description may be followed by `Log Search Filter` and `SQL WHERE Condition`; use the same mapping as above |

- Query construction must preserve the original definition's calculation logic, filters, literals, and units.
- Combine multiple metrics into one `SELECT` only when their effective search prefixes and `WHERE` conditions are identical; otherwise, execute them separately.

**Assembling filters**

When constructing filters yourself, use the search prefix, SQL `WHERE`, or both:

- **Search prefix**: common forms include keyword searches (`term`) and field searches (`field:value`); fields with `long` or `double` indexes also support numeric comparisons (`field > value`) and range searches (`field in [min max]`). **For fields indexed as `text`, `field:value` matches tokenized content and does not guarantee equality of the complete field value.**
- **SQL `WHERE`**: further filter logs matched by the search prefix using field values, such as complete string equality, `LIKE` / `NOT LIKE` pattern matching, or regular expressions.

Wildcard searches in the search prefix, such as `field:abc*`, have a limit on the number of matching terms. Do not use them to replace SQL `LIKE` / `NOT LIKE` conditions or add such wildcard searches while retaining those conditions.

**Controlling result rows**

SLS SQL returns at most 100 rows by default when `LIMIT` is omitted. When more rows are needed, explicitly set the appropriate `LIMIT` in the final SQL.

### 2.2 Gather additional evidence as needed

**Index configuration**

Read the index configuration when you need to confirm search and statistical analysis capabilities, index types, tokenization, or other matching rules.

```bash
aliyun sls get-index \
  --region "<region>" --project "<project>" --logstore "<logstore>"
```

**Log samples**

Read a small number of relevant logs when you need to confirm actual data structures, field paths, values, or formats.

- Set `--query` to confirmed keywords or field filters, such as `error` or `k1:v1 AND k2:v2`; use `*` when no reliable condition is available.
- Use the established time range for `--time-range` and bound the number of samples with `--lines`.

```bash
python3 "<skill-dir>/scripts/model_qa.py" query \
  --region "<region>" --project "<project>" --logstore "<logstore>" \
  --query "<search-prefix>" --time-range "<time-range>" \
  --lines <bounded-sample-rows>
```

Samples are for internal verification. Do not copy them in full into the final answer; cite only necessary, redacted evidence.

### 2.3 References to use as needed

| Document | Description |
| --- | --- |
| [SLS function reference](model-data-qa/sql/functions.md) | SLS-specific usage differences for period comparison, bucketing, JSON, regular expressions, approximate aggregates, and IP geolocation functions. |
| [Cross-Logstore JOIN](model-data-qa/sql/join.md) | Execution conditions, join criteria, and SQL templates for queries joining multiple Logstores. |
| [Scan analysis (SCAN)](model-data-qa/sql/scan.md) | Syntax and limits for querying fields without indexes or statistical analysis enabled. |

## 3. Execute, validate, and handle exceptions

### 3.1 Execute queries

Determine each answer branch's query time range from the question and existing evidence; ask the user to clarify when it cannot be determined.

- Time boundaries: `query` includes the start time and excludes the end time. For a complete calendar period, pass the start of the next period as the end time.
- `--time-range`: specify a relative range, such as `last_15m`, `last_1h`, `now-1h~now`, `today`, or `yesterday`, or an explicit range. An explicit range uses `<start-time>~<end-time>`, with timezone-aware RFC3339 values at both ends.
- Window reuse: for comparisons over the same window or cross-source aggregation, reuse the same fixed start and end times to avoid window drift from repeatedly resolving relative times.

```bash
query_suffix="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')" && \
python3 "<skill-dir>/scripts/model_qa.py" query \
  --region "<region>" --project "<project>" --logstore "<logstore>" \
  --query "<complete-query>" \
  --time-range "<time-range>" \
  --save-file "<absolute-temp-directory>/<query-purpose>-${query_suffix}.json"
```

**Additional usage**

- `--from "<FROM_TS>" --to "<TO_TS>"`: replace `--time-range` when start and end timestamps are already available.
- `--lines`: optional, defaults to 100 rows, and applies only when the query contains just a search prefix.

### 3.2 Validate results

After successfully receiving a query response, confirm:

1. **Execution status**: `meta.progress == "Complete"` means this query completed in full. Do not interpret query failures or incomplete results as no data.
2. **Result shape**: fields and result shape meet the question's requirements. When all groups or a complete time series are needed, confirm that the return limit has not truncated the results.

`logs: []` means only that the current query returned no rows; it does not mean the numeric value 0. A scalar aggregate returning 0 is an actual calculated result.

The top-level `timeRange.from/to` in a successful query response is the actual execution window in Unix seconds. Use it for the execution scope and chart window in the answer; do not derive the window again.

### 3.3 Handle exceptions

Handle exceptions using CLI errors, the top-level `error` in a failed response, or the query response's `meta.progress`. Do not work around exceptions by switching data sources, removing filters, shortening the user's requested time range, or changing business calculation rules. Stop when recovery is not possible and explain the known cause, queries not completed, and necessary additional information.

| Exception | Action |
| --- | --- |
| Parameter, SQL, function, or JOIN error | Correct the reported error; consult the [SLS function reference](model-data-qa/sql/functions.md) or [Cross-Logstore JOIN](model-data-qa/sql/join.md) as needed |
| Field parsing or index configuration error | Correct it from existing field information; gather more evidence if information is insufficient, and consult [Scan analysis (SCAN)](model-data-qa/sql/scan.md) when scanning is necessary |
| Throttling, busy service, or request processing timeout | Wait and retry with the same query and time range; stop and report persistent failure |
| `meta.progress == "Incomplete"` | Investigate and recover using [Incomplete and inaccurate query results](model-data-qa/sql/incomplete.md) |
| Authentication failure, permission denial, or missing resource | Correct an unambiguous parameter error; stop and report if it cannot be corrected |

## 4. Deliver results

### 4.1 Organize the answer

The suggested answer structure has "Conclusions" and "Query evidence" sections.

- Draw conclusions only from query results that passed validation. Claim complete coverage only when all required queries passed validation; otherwise, state the gaps and limit the conclusion's scope. Explain approximation or data-processing limits that affect the conclusion.
- Combine cross-source results only when their calculation rules, filters, and time windows match and the results can be combined. Results from individual sources cannot replace evidence of record-level joins.
- In "Query evidence", show the complete executed queries supporting the main conclusions in Markdown code blocks, with their data sources (Region/Project/Logstore) and actual time windows. Use short business titles describing the query purpose; if a corresponding chart is delivered, use the same title for both.
- Do not expose endpoints, credentials, internal Element identifiers, or unredacted diagnostic information.

### 4.2 Deliver charts

When results suit a chart (trends, TopN/category comparisons, proportions across a few categories, multi-column details, or flows across time and categories), use chart capabilities available in the current environment. Reuse validated results and their actual time windows, and place charts near the corresponding conclusions without changing query calculation rules or adding queries for charts. Fall back to Markdown tables when charts are unavailable. Do not chart scalars or other unsuitable results.

### 4.3 Extract query execution information

You can use the following command with absolute paths to saved query records supporting the main conclusions to extract complete queries, data sources, actual time windows, and execution parameters for the "Query evidence" section.

```bash
python3 "<skill-dir>/scripts/export_query_evidence.py" \
  "<absolute-path-to-query-record-1>.json" \
  "<absolute-path-to-query-record-2>.json"
```
