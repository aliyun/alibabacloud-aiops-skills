# make-instance (instance building)

> Aggregate discrete event-level logs by a grouping key into row-level sample
> instances for the downstream Pipeline nodes.

## Function

An AI Agent produces many discrete log rows at runtime, each holding only one
fragment of the interaction. The downstream Pipeline nodes (dedup, sample,
llm-call, and so on) expect every row to be one complete sample instance.

`make-instance` is a pure-CPU data-assembly node. It aggregates several event rows
into one wide-table sample row by the grouping key the user specifies. It offers
three families of built-in functions (value selection, computation, and
combination) for quick assembly, and it also accepts standard SQL aggregate
expressions for advanced needs.

**Use cases**:

- Build row-level samples from AI Agent runtime logs (event level → sample level)
- Reshape OpenTelemetry trace span data into a wide table
- Aggregate at various granularities (span, trace, session, or user)
- Serve as the first Pipeline node, preparing the input for downstream dedup,
  sample, and llm-call

## Node configuration

```json
{
  "id": "assemble",
  "type": "make-instance",
  "parameters": {
    "question": "first(question)",
    "answer": "last(output)",
    "model": "any(model)",
    "max_latency": "max(latency_ms)",
    "total_input": "sum(token_input)",
    "total_output": "sum(token_output)",
    "tool_count": "count(tool_name)",
    "tools": "array_distinct(tool_name)",
    "tool_chain": "join(tool_name, ' → ')",
    "tool_info": "json_pack(tool_name, tool_args, tool_success)",
    "by": "session_id,trace_id"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `by` | String | **Yes** | - | Grouping keys, comma separated |
| *All other parameters* | String | **Yes** (at least one) | - | Column definitions: the key is the output column alias, the value is a function call or SQL expression |
| `output` | String | No | `*` | Output columns of the node, comma separated |

> Every column definition must be an explicit function call (such as
> `model=any(model)`); a bare field name is not supported.

## Built-in functions

`make-instance` groups its built-in functions by the three basic assembly needs:

| Family | Essence | Problem solved | Typical use | Available functions |
|--------|---------|----------------|-------------|---------------------|
| **Value selection** | N rows → 1 value | Many rows per group, keep one representative value | Semantic fields such as question, output, model | ★`any` ★`first` ★`last` `max` `min` `max_by` `min_by` |
| **Computation** | N rows → 1 number | Numeric values per group that need a summary | Token-usage totals, latency analysis, call counts | `sum` `avg` `count` `count_if` `bool_or` `bool_and` |
| **Combination** | N rows → 1 structure | Many values per group that must be kept and packed | Tool-call chains, event sequences, structured detail | ★`array` ★`array_distinct` ★`join` ★`json_pack` `histogram` `map_agg` |

> ★ = built-in syntactic sugar, expanded automatically into a SQL aggregate
> expression; the rest are standard SQL aggregate functions passed through as-is.

**Function quick reference**

| Family | Function | Usage | Description | Example | Result |
|--------|----------|-------|-------------|---------|--------|
| **Value selection** | ★ `any` | `any(col)` | Any non-empty value in the group | `model=any(model)` | `qwen-max` |
| | ★ `any` | `any(col, 'empty-marker')` | Same, with the second argument naming the string treated as empty (default `''`) | `status=any(status, 'N/A')` | `success` |
| | ★ `first` | `first(col)` | Earliest non-empty value by `__time__` | `question=first(question)` | `Analyze the error logs of the last 7 days…` |
| | ★ `first` | `first(col, order_col)` | Earliest non-empty value by the given column | `q=first(question, startTime)` | Same as above |
| | ★ `last` | `last(col)` | Latest non-empty value by `__time__` | `answer=last(output)` | `Found 42 errors in total…` |
| | ★ `last` | `last(col, order_col)` | Latest non-empty value by the given column | `a=last(output, endTime)` | Same as above |
| | `max` | `max(col)` | Maximum value | `max_lat=max(latency_ms)` | `14000` |
| | `min` | `min(col)` | Minimum value | `min_lat=min(latency_ms)` | `1850` |
| | `max_by` | `max_by(col, ord)` | `col` where `ord` is greatest | `m=max_by(model, __time__)` | `qwen-max` |
| | `min_by` | `min_by(col, ord)` | `col` where `ord` is smallest | `m=min_by(model, __time__)` | `qwen-max` |
| **Computation** | `sum` | `sum(col)` | Sum | `total=sum(token_input)` | `8280` |
| | `avg` | `avg(col)` | Average | `avg_lat=avg(latency_ms)` | `6350.0` |
| | `count` | `count(col)` | Count of non-NULL values | `n=count(tool_name)` | `4` |
| | `count_if` | `count_if(condition)` | Conditional count | `errs=count_if(success='false')` | `0` |
| | `bool_or` | `bool_or(condition)` | Whether any row in the group satisfies the condition | `has_err=bool_or(success='false')` | `false` |
| | `bool_and` | `bool_and(condition)` | Whether every row in the group satisfies the condition | `all_ok=bool_and(success='true')` | `true` |
| **Combination** | ★ `array` | `array(col [, order_by])` | Collect into a JSON array, dropping empties; an order field can be given | `evts=array(event_type)` | `["user_query","tool_call",…]` |
| | ★ `array_distinct` | `array_distinct(col [, order_by])` | Collect into a deduplicated JSON array, dropping empties; an order field can be given | `tools=array_distinct(tool_name)` | `["search_logs","analyze_pattern"]` |
| | ★ `join` | `join(col, sep [, order_by])` | Concatenate text, dropping empties; an order field can be given | `chain=join(tool_name,' → ')` | `search_logs → analyze_pattern → …` |
| | ★ `json_pack` | `json_pack(c1, c2, ...)` | Pack several fields into a JSON object | `info=json_pack(name, args)` | `[{"name":"search_logs","args":…},…]` |
| | `histogram` | `histogram(col)` | Value-frequency distribution (a MAP) | `dist=histogram(event_type)` | `{"tool_call":2,"tool_result":2,…}` |
| | `map_agg` | `map_agg(key, val)` | Aggregate into a MAP keyed by `key` | `tok=map_agg(model, tokens)` | `{"qwen-max":8280}` |

> These three families cover the vast majority of scenarios. Advanced users can
> also write any SQL aggregate expression to define the logic freely (for example
> `total=sum(cast(a as bigint)) + sum(cast(b as bigint))`), as long as it satisfies
> aggregate-function syntax.

### Parameter details for the combination functions

#### join(col, sep [, order_by])

Concatenates every non-empty value in the group with a separator.

| Parameter | Required | Description |
|-----------|----------|-------------|
| col | Yes | The column or expression to concatenate |
| sep | No | Separator (default `', '`) |
| order_by | No | Sort key: a field name or any SQL expression; when set, the aggregation runs in ascending order of this key |

> `order_by` accepts any valid SQL expression (a field name, function call,
> arithmetic expression, and so on). The expression must produce a
> lexicographically sortable varchar value (it is cast to varchar internally). The
> expression is passed through to the SLS query engine, which validates it.

Examples:
- `join(tool_name, ' → ')` — concatenate in the default order
- `join(tool_name, ' → ', __time__)` — concatenate in ascending time order
- `join(tool_name, ' → ', coalesce(startTime, 0))` — order by an expression
- `join(tool_name, ' → ', cast(startTime as bigint))` — order after a cast

#### array(col [, order_by])

Collects every non-empty value in the group into an array.

| Parameter | Required | Description |
|-----------|----------|-------------|
| col | Yes | The column or expression to collect |
| order_by | No | Sort key: a field name or any SQL expression; when set, array elements are ordered ascending by this key |

Examples:
- `array(event_type)` — collect into an array
- `array(event_type, startTime)` — order by time
- `array(event_type, startTime + duration)` — order by an arithmetic expression

#### array_distinct(col [, order_by])

Collects every distinct non-empty value in the group into an array.

| Parameter | Required | Description |
|-----------|----------|-------------|
| col | Yes | The column or expression to collect |
| order_by | No | Sort key: a field name or any SQL expression; when set, array elements are ordered ascending by this key |

Examples:
- `array_distinct(tool_name)` — collect distinct values
- `array_distinct(tool_name, __time__)` — order by time, then deduplicate
- `array_distinct(tool_name, cast(startTime as bigint))` — order by an expression, then deduplicate

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- The grouping-key fields named by `by` must be present
- Every source field referenced by a column definition must be present

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns named by `by` | — | Pass-through | The grouping keys |
| Every key in the column definitions | Determined by the function | Added | The aggregation result column |

> `make-instance` does not pass through raw columns other than the grouping keys.
> The output schema is fully determined by `by` plus the column definitions.

**Row-count change**:

M → N (M ≥ N) — many event rows collapse into one row per group, so the output row
count equals the number of groups.

## Effect preview

### Raw data (10 discrete event log rows)

A user asks the AI Agent to "analyze the error logs of the last 7 days". The Agent
calls two tools in turn and returns a final conclusion. The run produces these 10
discrete events:

| # | __time__ | session_id | trace_id | event_type | question | output | model | tool_name | tool_args | tool_success | latency_ms | token_input | token_output |
|---|----------|------------|----------|------------|----------|--------|-------|-----------|-----------|--------------|------------|-------------|--------------|
| 1 | 10:00:01 | sess_a1 | trc_7f01 | user_query | Analyze the error logs of the last 7 days and suggest improvements | | | | | | | | |
| 2 | 10:00:01 | sess_a1 | trc_7f01 | system_prompt | | | | | | | | 320 | |
| 3 | 10:00:02 | sess_a1 | trc_7f01 | llm_request | | | qwen-max | | | | | 1580 | 120 |
| 4 | 10:00:04 | sess_a1 | trc_7f01 | tool_call | | | qwen-max | search_logs | {"query":"level:ERROR","days":7} | | | 200 | 65 |
| 5 | 10:00:06 | sess_a1 | trc_7f01 | tool_result | | {"total":42,"top":"NullPointer"} | | search_logs | | true | 1850 | | |
| 6 | 10:00:07 | sess_a1 | trc_7f01 | tool_call | | | qwen-max | analyze_pattern | {"error_type":"NullPointer"} | | | 180 | 50 |
| 7 | 10:00:10 | sess_a1 | trc_7f01 | tool_result | | {"root_cause":"missing null check","fix":"use Optional"} | | analyze_pattern | | true | 3200 | | |
| 8 | 10:00:12 | sess_a1 | trc_7f01 | llm_request | | | qwen-max | | | | | 2800 | 520 |
| 9 | 10:00:15 | sess_a1 | trc_7f01 | assistant | | 42 errors in the last 7 days; NullPointerException accounts for 66.7%; wrap with Optional… | qwen-max | | | | | 3200 | 680 |
| 10 | 10:00:15 | sess_a1 | trc_7f01 | completion | | | qwen-max | | | | 14000 | | |

> Data characteristics: `question` has a value only on row 1, `output` is spread
> across rows 5, 7, and 9, `model` appears on four rows, `tool_name` appears four
> times (with repeats), and the token counts are scattered.

### Node configuration

```json
{
  "id": "assemble",
  "type": "make-instance",
  "parameters": {
    "question": "first(question)",
    "answer": "last(output)",
    "model": "any(model)",
    "max_latency": "max(latency_ms)",
    "total_input": "sum(token_input)",
    "total_output": "sum(token_output)",
    "avg_latency": "avg(latency_ms)",
    "llm_calls": "count(model)",
    "tool_count": "count(tool_name)",
    "err_tools": "count_if(tool_success = 'false')",
    "tools": "array_distinct(tool_name)",
    "events": "array(event_type)",
    "tool_chain": "join(tool_name, ' → ')",
    "tool_detail": "json_pack(tool_name, tool_args, tool_success)",
    "by": "session_id,trace_id"
  }
}
```

### After (wide table, 1 row x 16 columns)

10 narrow rows become 1 wide row. Compared with the raw data above, every column is
aggregated from the 10 rows by the function given:

| session_id | trace_id | question | answer | model | max_latency | total_input | total_output | avg_latency | llm_calls | tool_count | err_tools | tools | events | tool_chain | tool_detail |
|------------|----------|----------|--------|-------|-------------|-------------|--------------|-------------|-----------|------------|-----------|-------|--------|------------|-------------|
| sess_a1 | trc_7f01 | Analyze the error logs of the last 7 days and suggest improvements | 42 errors in the last 7 days; NullPointerException accounts for 66.7%; wrap with Optional… | qwen-max | 14000 | 8280 | 1435 | 6350.0 | 6 | 4 | 0 | ["search_logs","analyze_pattern"] | ["user_query","system_prompt","llm_request","tool_call","tool_result",…] | search_logs → search_logs → analyze_pattern → analyze_pattern | [{"tool_name":"search_logs","tool_args":…,"tool_success":"true"},…] |

Aggregation logic per column:

| Column | Family | Function | Data source |
|--------|--------|----------|-------------|
| session_id | Grouping key | — | Grouping key passed through |
| trace_id | Grouping key | — | Grouping key passed through |
| question | Value selection | `first(question)` | Only row 1 has a value; takes the earliest non-empty value |
| answer | Value selection | `last(output)` | Rows 5, 7, and 9 have values; takes the latest, the assistant output on row 9 |
| model | Value selection | `any(model)` | Rows 3, 4, 6, 8, 9, and 10 have values; takes any non-empty one |
| max_latency | Value selection | `max(latency_ms)` | Only rows 5, 7, and 10 have values; takes the maximum, 14000 |
| total_input | Computation | `sum(token_input)` | 320+1580+200+180+2800+3200 = 8280 |
| total_output | Computation | `sum(token_output)` | 120+65+50+520+680 = 1435 |
| avg_latency | Computation | `avg(latency_ms)` | (1850+3200+14000)/3 = 6350.0 |
| llm_calls | Computation | `count(model)` | Rows where model is non-empty = 6 |
| tool_count | Computation | `count(tool_name)` | Rows where tool_name is non-empty = 4 |
| err_tools | Computation | `count_if(tool_success='false')` | No failed tool call, so 0 |
| tools | Combination | `array_distinct(tool_name)` | 4 calls deduplicated into 2 tools |
| events | Combination | `array(event_type)` | Collects all 10 event types in time order |
| tool_chain | Combination | `join(tool_name, ' → ')` | The 4 calls concatenated in time order |
| tool_detail | Combination | `json_pack(tool_name, tool_args, tool_success)` | Each row's tool name, arguments, and result packed into a JSON object |

> 10 discrete events become 1 complete sample instance, exercising all three
> families: value selection, computation, and combination. Missing fields become
> NULL automatically with no extra handling. The whole process is **pure CPU**,
> with no LLM or GPU dependency.

## Examples

### Example 1: minimal usage

```json
{
  "id": "assemble",
  "type": "make-instance",
  "parameters": {
    "question": "any(question)",
    "output": "any(output)",
    "model": "any(model)",
    "by": "session_id,trace_id"
  }
}
```

Aggregates at trace granularity, taking any non-empty value per column.

### Example 2: value selection plus statistics plus packing

```json
{
  "id": "assemble",
  "type": "make-instance",
  "parameters": {
    "question": "first(question)",
    "answer": "last(output)",
    "model": "any(model)",
    "max_latency": "max(latency_ms)",
    "total_tokens": "sum(token_input)",
    "tool_count": "count(tool_name)",
    "tools": "array_distinct(tool_name)",
    "tool_chain": "join(tool_name, ' → ')",
    "by": "session_id,trace_id"
  }
}
```

### Example 3: complete pipeline (instance building → cleaning → sampling → AI evaluation), filtering to the valid event types before assembly

```json
{
  "nodes": [
    { "id": "filter_events",
      "type": "where",
      "parameters": {
        "filter": "event_type IN ('user_query','system_prompt','tool_call','tool_result','assistant_content','completion')"
      }
    },
    {
      "id": "extract", "type": "extend",
      "parameters": {
        "session_id": "json_extract_scalar(attributes, '$.gen_ai.session.id')",
        "span_kind": "json_extract_scalar(attributes, '$.gen_ai.span.kind')",
        "question": "json_extract_scalar(attributes, '$.input.value')",
        "answer": "json_extract_scalar(attributes, '$.output.value')",
        "model": "json_extract_scalar(attributes, '$.gen_ai.request.model')",
        "tool_name": "json_extract_scalar(attributes, '$.gen_ai.tool.name')",
        "input_tokens": "json_extract_scalar(attributes, '$.gen_ai.usage.input_tokens')"
      }
    },
    {
      "id": "filter_events", "type": "where",
      "parameters": { "filter": "span_kind IN ('AGENT','LLM','TOOL')" }
    },
    {
      "id": "assemble", "type": "make-instance",
      "parameters": {
        "question": "first(question)",
        "answer": "last(answer)",
        "model": "last(model)",
        "total_tokens": "sum(input_tokens)",
        "tools": "array_distinct(tool_name)",
        "tool_chain": "join(tool_name, ' → ')",
        "by": "session_id,traceId"
      }
    },
    { "id": "filter_empty", "type": "where", "parameters": { "filter": "question IS NOT NULL AND length(question) > 0" } },
    { "id": "exact", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "fuzzy", "type": "dedup-fuzzy", "parameters": { "field": "question", "threshold": "3" } },
    { "id": "take", "type": "sample", "parameters": { "n": 50 } },
    { "id": "eval", "type": "llm-call", "parameters": { "prompt": "@eval/quality.md", "fields": "question,answer", "format": "json", "as": "eval" } },
    { "id": "stats", "type": "doc-stats", "parameters": { "field": "question" } }
  ]
}
```

### Example 4: OT trace in practice — two-step conversion plus full-text merge

A real scenario: 28 OT spans (AGENT, LLM, TOOL, EXTERNAL, and so on) → filter the
irrelevant events → assemble into 1 wide row → merge into a `full_text` column for
downstream AI evaluation.

```json
{
  "nodes": [
    {
      "id": "extract", "type": "extend",
      "parameters": {
        "session_id": "json_extract_scalar(attributes, '$.gen_ai.session.id')",
        "span_kind": "json_extract_scalar(attributes, '$.gen_ai.span.kind')",
        "model": "json_extract_scalar(attributes, '$.gen_ai.request.model')",
        "input_tokens": "json_extract_scalar(attributes, '$.gen_ai.usage.input_tokens')",
        "output_tokens": "json_extract_scalar(attributes, '$.gen_ai.usage.output_tokens')",
        "tool_name": "json_extract_scalar(attributes, '$.gen_ai.tool.name')",
        "tool_args": "json_extract_scalar(attributes, '$.gen_ai.tool.call.arguments')",
        "input_value": "json_extract_scalar(attributes, '$.input.value')",
        "output_value": "json_extract_scalar(attributes, '$.output.value')",
        "agent_id": "json_extract_scalar(attributes, '$.agent.id')",
        "dur_ms": "cast(duration as bigint) / 1000000"
      }
    },
    {
      "id": "filter_events", "type": "where",
      "parameters": { "filter": "span_kind IN ('AGENT','LLM','TOOL')" }
    },
    {
      "id": "assemble", "type": "make-instance",
      "parameters": {
        "question": "min_by(input_value, startTime)",
        "answer": "max_by(output_value, endTime)",
        "model": "max_by(model, endTime)",
        "total_input_tokens": "sum(cast(input_tokens as bigint))",
        "total_output_tokens": "sum(cast(output_tokens as bigint))",
        "llm_calls": "count_if(span_kind = 'LLM')",
        "tool_calls": "count_if(span_kind = 'TOOL')",
        "e2e_latency": "max(dur_ms)",
        "models": "array_distinct(model)",
        "tools": "array_distinct(tool_name)",
        "tool_chain": "join(tool_name, ' → ')",
        "by": "session_id,traceId"
      }
    },
    {
      "id": "compose", "type": "extend",
      "parameters": {
        "full_text": "concat('## User input', chr(10), substr(question, 1, 500), chr(10), chr(10), '## Final output', chr(10), answer)"
      }
    },
    { "id": "filter_empty", "type": "where", "parameters": { "filter": "question IS NOT NULL AND length(question) > 0" } },
    { "id": "eval", "type": "llm-call", "parameters": { "prompt": "@eval/quality.md", "fields": "full_text", "format": "json", "as": "eval" } }
  ]
}
```

> The first step (`extend` + `where` + `make-instance`) handles field extraction,
> event filtering, and assembly (28 rows → 1 row); the second step (`extend`)
> merges question and answer into `full_text` so that `llm-call` can evaluate the
> whole thing. The entire process is pure CPU.

## Notes

**Recommended usage**:

- Place it at the very front of the Pipeline (or right after the `extend` that
  extracts fields) as the entry point from event level to sample level
- Follow it with a `where` that drops rows with empty values, then continue into
  dedup, sample, and llm-call

**Best practices**:

- For OT trace data, first use `extend` to pull flat fields out of the attributes
  JSON, then aggregate with `make-instance`
- The value-selection family covers about 80% of scenarios; add computation and
  combination functions as needed
- Advanced users can write SQL aggregate expressions directly and mix them with the
  syntactic-sugar functions

**Edge cases**:

| Case | Behavior |
|------|----------|
| Some events in a group lack a given field | Aggregate functions handle NULL naturally without erroring |
| A `by` grouping-key value is NULL | That event does not take part in grouping |
| A column definition uses a bare field name | Validation fails; an explicit function is required |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `extend` | Use it before, to pull flat fields out of JSON attributes for `make-instance` to reference |
| `where` | Use it after, to drop rows with empty values from the `make-instance` output |
| `dedup-exact` | Use it after, to exact-dedup the assembled samples |
| `sample` | Use it after, to sample the assembled samples |
| `llm-call` | Use it after, to evaluate or label the assembled samples with AI |
