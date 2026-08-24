# make-instance (instance assembly)

> Aggregate discrete event-level logs into row-level sample instances by grouping key,
> ready for downstream Pipeline operators.

## Function

An AI agent produces a large volume of discrete logs at runtime (user questions, system
prompts, LLM responses, tool calls and results, and so on), where each log record holds
only one fragment of the interaction. Downstream Pipeline operators (dedup, sample,
llm-call, and others) expect each row to be one complete sample instance.

`make-instance` is a **pure-CPU data assembly operator**. It aggregates many event rows
into a single wide-table sample row by the grouping key the user specifies (session_id,
trace_id, and so on). Three families of built-in functions (selection, computation, and
composition) cover everything from simple value picking to complex structural
aggregation, and the operator is tolerant of broken data - missing fields become NULL
instead of errors.

`make-instance` is the **first step** of a Pipeline data flow: it assembles discrete
runtime events into sample rows so the row-level operators that follow (`dedup`,
`sample`, `llm-call`, and so on) can consume them normally.

**Use cases**:

- Building row-level samples from AI agent runtime logs (event level -> sample level)
- Reshaping OpenTelemetry trace span data into a wide table
- Aggregating at several granularities (span, trace, session, user)
- Serving as the first operator of a data-cleaning or evaluation Pipeline, preparing the
  input for downstream dedup, sample, and llm-call

**How it differs from related operators**:

| Dimension | make-trace (existing) | make-conversation (in development) | **make-instance (this operator)** |
|-----------|----------------------|-----------------------------------|----------------------------------|
| **Nature** | Builds an OT trace tree | Builds a semantic conversation skeleton | Assembles discrete log events into complete samples |
| **Dependencies** | Strictly depends on OT parent-child relationships | LLM / GPU semantic processing | **Pure CPU, no external dependencies** |
| **Robustness** | Low - a broken trace makes it useless | Medium - tolerant, but depends on semantic understanding | **High - very robust, missing data raises no error** |
| **Input requirements** | Standard OT span data | An event stream plus specific field conventions | **Any log data with a custom grouping key** |
| **Output format** | A trace tree (nested JSON) | Conversation skeleton plus a profile JSONB | **A flat wide-table row (one row per sample)** |
| **Compute cost** | Heavy (tree building, CPU) | Heavy (LLM/function calling, GPU) | **Light (GROUP BY plus aggregation, CPU)** |
| **Purpose** | Reconstruct the observability trace | Structured conversation analysis | **Prepare row-level sample data for downstream Pipeline operators** |

## Syntax

```
| make-instance <alias>=<func(args)>, <alias>=<func(args)>, ... by <key1>[,<key2>,...]
```

> **Implementation note**: at the SPL layer `make-instance` reuses the existing `stats`
> command syntax, and the API Node layer handles the syntactic-sugar translation. The
> syntax above is the logical syntax from the Pipeline user's point of view.

## Parameters

Every column definition uses the `alias=expression` form, and each column must use an
explicit function call.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| Column definitions | `alias=func(args)` | **Yes** | - | A comma-separated list of column definitions, at least one |
| `by` | Fields | **Yes** | - | Grouping keys, comma-separated - an instruction primitive, without the `-` prefix |

> **Instruction primitive**: `by` is an SPL instruction primitive. It carries **no `-`
> prefix**, is separated from its value by a space, and **must come after every column
> definition (at the very end)**.
> Each column definition must be an explicit function call (such as
> `model=any(model)`); bare field names are not supported.

## Built-in functions

`make-instance` offers three families of built-in functions matching the three basic
needs of data assembly:

| Family | Nature | Problem solved | Typical use | Available functions |
|--------|--------|----------------|-------------|---------------------|
| **Selection** | N rows -> 1 value | Keep one representative value out of the group's rows | Semantic fields such as question, output, model | [built-in]`any` [built-in]`first` [built-in]`last` `max` `min` `max_by` `min_by` |
| **Computation** | N rows -> 1 number | Summarize numeric values across the group | Summing token usage, latency analysis, call counting | `sum` `avg` `count` `count_if` `bool_or` `bool_and` |
| **Composition** | N rows -> 1 structure | Keep and pack several values from the group | Tool-call chains, event sequences, structured detail | [built-in]`array` [built-in]`array_distinct` [built-in]`join` [built-in]`json_pack` `histogram` `map_agg` |

> [built-in] = built-in syntactic sugar that the API layer expands into a SQL aggregate
> expression; the rest are standard SQL aggregate functions passed through unchanged.

**Function overview**

| Family | Function | Usage | Description | Example | Result |
|--------|----------|-------|-------------|---------|--------|
| **Selection** | [built-in] `any` | `any(col)` | Any non-empty value in the group | `model=any(model)` | `qwen-max` |
| | [built-in] `any` | `any(col, 'empty')` | The same, with the second argument naming the string treated as empty (default `''`) | `status=any(status, 'N/A')` | `success` |
| | [built-in] `first` | `first(col)` | The earliest non-empty value by `__time__` | `question=first(question)` | `Analyze the error logs of the last 7 days...` |
| | [built-in] `first` | `first(col, order_col)` | The earliest non-empty value by the given column | `q=first(question, startTime)` | The same as above |
| | [built-in] `last` | `last(col)` | The latest non-empty value by `__time__` | `answer=last(output)` | `Found 42 errors in total...` |
| | [built-in] `last` | `last(col, order_col)` | The latest non-empty value by the given column | `a=last(output, endTime)` | The same as above |
| | `max` | `max(col)` | The maximum | `max_lat=max(latency_ms)` | `14000` |
| | `min` | `min(col)` | The minimum | `min_lat=min(latency_ms)` | `1850` |
| | `max_by` | `max_by(col, ord)` | col where ord is largest | `m=max_by(model, __time__)` | `qwen-max` |
| | `min_by` | `min_by(col, ord)` | col where ord is smallest | `m=min_by(model, __time__)` | `qwen-max` |
| **Computation** | `sum` | `sum(col)` | Sum | `total=sum(token_input)` | `8280` |
| | `avg` | `avg(col)` | Average | `avg_lat=avg(latency_ms)` | `6350.0` |
| | `count` | `count(col)` | Count of non-NULL values | `n=count(tool_name)` | `4` |
| | `count_if` | `count_if(condition)` | Conditional count | `errs=count_if(success='false')` | `0` |
| | `bool_or` | `bool_or(condition)` | Whether any row in the group satisfies the condition | `has_err=bool_or(success='false')` | `false` |
| | `bool_and` | `bool_and(condition)` | Whether every row in the group satisfies the condition | `all_ok=bool_and(success='true')` | `true` |
| **Composition** | [built-in] `array` | `array(col)` | Collect a JSON array in time order, dropping empties | `evts=array(event_type)` | `["user_query","tool_call",...]` |
| | [built-in] `array_distinct` | `array_distinct(col)` | Collect a deduplicated JSON array, dropping empties | `tools=array_distinct(tool_name)` | `["search_logs","analyze_pattern"]` |
| | [built-in] `join` | `join(col, 'sep')` | Concatenate text in time order, dropping empties | `chain=join(tool_name,' -> ')` | `search_logs -> analyze_pattern -> ...` |
| | [built-in] `json_pack` | `json_pack(c1, c2, ...)` | Assemble several fields into a JSON object | `info=json_pack(name, args)` | `[{"name":"search_logs","args":...},...]` |
| | `histogram` | `histogram(col)` | Value-frequency distribution (a MAP) | `dist=histogram(event_type)` | `{"tool_call":2,"tool_result":2,...}` |
| | `map_agg` | `map_agg(key, val)` | Aggregate into a MAP by key | `tok=map_agg(model, tokens)` | `{"qwen-max":8280}` |

> These three families cover the vast majority of scenarios. Advanced users can also
> write any SQL aggregate expression to define the logic freely (for example
> `total=sum(cast(a as bigint)) + sum(cast(b as bigint))`) as long as it is valid
> aggregate-function syntax.

## Input and output

**Input**:

- Any columns emitted by the upstream operator (usually AI agent runtime event logs)
- The grouping-key fields named by `by` must be present
- Every source field referenced in the column definitions must be present

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| The columns named by `by` | - | Input | The grouping keys, passed through |
| Each alias in the column definitions | Determined by the function | Derived | The aggregation result column |

> `make-instance` **does not pass through** original columns other than the grouping
> keys. The output columns are determined entirely by `by` plus the column definitions.

**Input-to-output relationship**:

M:N (M >= N) - M raw events aggregate into N sample instances. Events sharing a group
collapse into one row, so the output row count equals the number of groups.

## Effect preview

### Scenario: an AIOps agent handling one user request

The user asks the agent to "analyze the error logs of the last 7 days and suggest
optimizations". The agent goes through four stages - **thinking -> calling search_logs ->
calling analyze_pattern -> producing a conclusion** - and emits 10 discrete event logs.

### Raw data (narrow table, 10 rows x 13 columns)

| # | __time__ | session_id | trace_id | event_type | question | output | model | tool_name | tool_args | tool_success | latency_ms | token_input | token_output |
|---|----------|------------|----------|------------|----------|--------|-------|-----------|-----------|--------------|------------|-------------|--------------|
| 1 | 10:00:01 | sess_a1 | trc_7f01 | user_query | Analyze the error logs of the last 7 days and suggest optimizations | | | | | | | | |
| 2 | 10:00:01 | sess_a1 | trc_7f01 | system_prompt | | | | | | | | 320 | |
| 3 | 10:00:02 | sess_a1 | trc_7f01 | llm_request | | | qwen-max | | | | | 1580 | 120 |
| 4 | 10:00:04 | sess_a1 | trc_7f01 | tool_call | | | qwen-max | search_logs | {"query":"level:ERROR","days":7} | | | 200 | 65 |
| 5 | 10:00:06 | sess_a1 | trc_7f01 | tool_result | | {"total":42,"top":"NullPointer"} | | search_logs | | true | 1850 | | |
| 6 | 10:00:07 | sess_a1 | trc_7f01 | tool_call | | | qwen-max | analyze_pattern | {"error_type":"NullPointer"} | | | 180 | 50 |
| 7 | 10:00:10 | sess_a1 | trc_7f01 | tool_result | | {"root_cause":"missing null check","fix":"use Optional"} | | analyze_pattern | | true | 3200 | | |
| 8 | 10:00:12 | sess_a1 | trc_7f01 | llm_request | | | qwen-max | | | | | 2800 | 520 |
| 9 | 10:00:15 | sess_a1 | trc_7f01 | assistant | | 42 errors in the last 7 days; NullPointerException accounts for 66.7%; wrap the value in Optional... | qwen-max | | | | | 3200 | 680 |
| 10 | 10:00:15 | sess_a1 | trc_7f01 | completion | | | qwen-max | | | | 14000 | | |

> Data characteristics: only row 1 has a `question`; `output` is spread across rows 5,
> 7, and 9; `model` appears 6 times and is always qwen-max; `tool_name` appears 4 times
> (search_logs twice, analyze_pattern twice); token counts are spread across rows.

### Operator command

```
| make-instance
    question=first(question),
    answer=last(output),
    model=any(model),
    max_latency=max(latency_ms),
    total_input=sum(token_input),
    total_output=sum(token_output),
    avg_latency=avg(latency_ms),
    llm_calls=count(model),
    tool_count=count(tool_name),
    err_tools=count_if(tool_success = 'false'),
    tools=array_distinct(tool_name),
    events=array(event_type),
    tool_chain=join(tool_name, ' -> '),
    tool_detail=json_pack(tool_name, tool_args, tool_success)
    by session_id,trace_id
```

### After (wide table, 1 row x 16 columns)

10 narrow rows **->** 1 wide row. Compared with the raw data above, every column is
aggregated from those 10 rows by the function it names:

| session_id | trace_id | question | answer | model | max_latency | total_input | total_output | avg_latency | llm_calls | tool_count | err_tools | tools | events | tool_chain | tool_detail |
|------------|----------|----------|--------|-------|-------------|-------------|--------------|-------------|-----------|------------|-----------|-------|--------|------------|-------------|
| sess_a1 | trc_7f01 | Analyze the error logs of the last 7 days and suggest optimizations | 42 errors in the last 7 days; NullPointerException accounts for 66.7%; wrap the value in Optional... | qwen-max | 14000 | 8280 | 1435 | 6350.0 | 6 | 4 | 0 | ["search_logs","analyze_pattern"] | ["user_query","system_prompt","llm_request","tool_call","tool_result",...] | search_logs -> search_logs -> analyze_pattern -> analyze_pattern | [{"tool_name":"search_logs","tool_args":...,"tool_success":"true"},...] |

Aggregation logic per column:

| Column | Family | Function | Where the data comes from |
|--------|--------|----------|---------------------------|
| session_id | Grouping key | - | Passed through |
| trace_id | Grouping key | - | Passed through |
| question | Selection | `first(question)` | Only row 1 has a value; takes the earliest non-empty value |
| answer | Selection | `last(output)` | Rows 5, 7, and 9 have values; takes the latest - the assistant output in row 9 |
| model | Selection | `any(model)` | Rows 3, 4, 6, 8, 9, and 10 have values; takes any non-empty one |
| max_latency | Selection | `max(latency_ms)` | Only rows 5, 7, and 10 have values; takes the maximum - 14000 |
| total_input | Computation | `sum(token_input)` | 320+1580+200+180+2800+3200 = 8280 |
| total_output | Computation | `sum(token_output)` | 120+65+50+520+680 = 1435 |
| avg_latency | Computation | `avg(latency_ms)` | (1850+3200+14000)/3 = 6350.0 |
| llm_calls | Computation | `count(model)` | Rows with a non-empty model = 6 |
| tool_count | Computation | `count(tool_name)` | Rows with a non-empty tool_name = 4 |
| err_tools | Computation | `count_if(tool_success='false')` | No failed tool calls -> 0 |
| tools | Composition | `array_distinct(tool_name)` | 4 calls deduplicated -> 2 tools |
| events | Composition | `array(event_type)` | Collects all 10 event types in time order |
| tool_chain | Composition | `join(tool_name, ' -> ')` | 4 calls concatenated in time order |
| tool_detail | Composition | `json_pack(tool_name, tool_args, tool_success)` | Each row's tool name, arguments, and result assembled into a JSON object |

> The whole process is **pure CPU** with no LLM or GPU dependency. Missing fields become
> NULL automatically and broken-chain events are tolerated, with no extra intervention
> needed.

## Examples

### Example 1: simplest usage (selection plus grouping)

```
* | make-instance
    question=any(question),
    output=any(output),
    model=any(model)
    by session_id,trace_id
```

### Example 2: selection plus statistics plus packing

```
* | make-instance
    question=first(question),
    output=last(output),
    model=any(model),
    max_latency=max(latency_ms),
    total_tokens=sum(token_input),
    tool_count=count(tool_name),
    tools=array_distinct(tool_name),
    tool_chain=join(tool_name, ' -> ')
    by session_id,trace_id
```

### Example 3: reshaping OT trace span data plus a full Pipeline

```
* | where event_type IN ('user_query','system_prompt','tool_call','tool_result','assistant_content','completion')
  | extend
      session_id=json_extract_scalar(attributes, '$.gen_ai.session.id'),
      span_kind=json_extract_scalar(attributes, '$.gen_ai.span.kind'),
      model=json_extract_scalar(attributes, '$.gen_ai.request.model'),
      input_tokens=json_extract_scalar(attributes, '$.gen_ai.usage.input_tokens'),
      output_tokens=json_extract_scalar(attributes, '$.gen_ai.usage.output_tokens'),
      tool_name=json_extract_scalar(attributes, '$.gen_ai.tool.name'),
      input_value=json_extract_scalar(attributes, '$.input.value'),
      output_value=json_extract_scalar(attributes, '$.output.value')
  | make-instance
      question=first(input_value),
      answer=last(output_value),
      model=last(model),
      total_input=sum(input_tokens),
      total_output=sum(output_tokens),
      tools=array_distinct(tool_name),
      tool_chain=join(tool_name, ' -> ')
      by session_id,traceId
  | where question IS NOT NULL AND length(question) > 0
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | sample -n=50
  | llm-call -prompt='@eval/quality.md' -fields=question,answer -format=json as eval
  | doc-stats -field=question
```

### Example 4: aggregating at several granularities

**Trace granularity** (one row per request, the most common):

```
* | make-instance
    question=first(question), output=last(output), model=any(model),
    max_latency=max(latency_ms), tool_count=count(tool_name)
    by session_id,trace_id
```

**Session granularity** (one row per session):

```
* | make-instance
    first_question=first(question), last_output=last(output),
    round_count=count(trace_id), total_tokens=sum(token_input),
    questions=array(question)
    by session_id
```

**User granularity** (one row per user):

```
* | make-instance
    session_count=count(session_id),
    total_rounds=count(trace_id),
    agents_used=array_distinct(agent_name)
    by user_id
```

### Example 5: OT trace in practice - 28 spans -> 1 wide row -> a consolidated full text

A real scenario: an AI agent (an AIOps assistant) handles the user request "filter the
logs containing /family/member/viewMember" and emits 28 OT spans covering AGENT, LLM,
TOOL, EXTERNAL, and other kinds:

```
session_id = thread-tb9msq-kfbqdenu0nyj
traceId    = 6cdc842e34e8a9c9a6f433d24ce2b06a

[AGENT]  orchestration:session         - input: the user's original question, output: the final answer
[AGENT]  base_agent:run:sql_generation - an agent subtask
[LLM]    llm:qwen-flash                - 721/11 tokens
[LLM]    llm:qwen3-coder-plus x3       - 11837/262, 11899/188, 18433/448 tokens
[TOOL]   tool:Think                    - the reasoning step
[TOOL]   tool:QuerySLSLogs             - a tool call querying the logs
[EXTERNAL] x8                          - GetThread, UpdateThread, GetIndex, and so on
[Other]  controlplane, HTTP, ...       - infrastructure spans
```

**Step 1: field extraction -> event filtering -> data assembly** (28 rows -> 1 wide row)

```
* | where event_type IN ('user_query','system_prompt','tool_call','tool_result','assistant_content','completion')
  | extend
      session_id=json_extract_scalar(attributes, '$.gen_ai.session.id'),
      span_kind=json_extract_scalar(attributes, '$.gen_ai.span.kind'),
      model=json_extract_scalar(attributes, '$.gen_ai.request.model'),
      input_tokens=json_extract_scalar(attributes, '$.gen_ai.usage.input_tokens'),
      output_tokens=json_extract_scalar(attributes, '$.gen_ai.usage.output_tokens'),
      tool_name=json_extract_scalar(attributes, '$.gen_ai.tool.name'),
      tool_args=json_extract_scalar(attributes, '$.gen_ai.tool.call.arguments'),
      input_value=json_extract_scalar(attributes, '$.input.value'),
      output_value=json_extract_scalar(attributes, '$.output.value'),
      agent_id=json_extract_scalar(attributes, '$.agent.id'),
      dur_ms=cast(duration as bigint) / 1000000
  | where span_kind IN ('AGENT','LLM','TOOL')
  | make-instance
      question=min_by(input_value, startTime),
      answer=max_by(output_value, endTime),
      model=max_by(model, endTime),
      total_input_tokens=sum(cast(input_tokens as bigint)),
      total_output_tokens=sum(cast(output_tokens as bigint)),
      llm_calls=count_if(span_kind = 'LLM'),
      tool_calls=count_if(span_kind = 'TOOL'),
      e2e_latency=max(dur_ms),
      models=array_distinct(model),
      tools=array_distinct(tool_name),
      tool_chain=join(tool_name, ' -> '),
      process=array_join(array_agg(
          case
              when span_kind = 'LLM'   then concat('[LLM] ', model, ' (', coalesce(input_tokens,'?'), '/', coalesce(output_tokens,'?'), ' tokens, ', cast(dur_ms as varchar), 'ms)')
              when span_kind = 'TOOL'  then concat('[Tool] ', tool_name, '(', substr(coalesce(tool_args,''), 1, 60), ')')
              when span_kind = 'AGENT' then concat('[Agent] ', substr(coalesce(agent_id,''), 1, 50), ' -> ', substr(coalesce(output_value,''), 1, 80))
              else null
          end
          order by startTime
      ) filter (where span_kind in ('LLM','TOOL','AGENT')), '\n')
      by session_id,traceId
```

**28 rows -> 1 wide row of output**:

| Column | Family | Value |
|--------|--------|-------|
| session_id | Grouping key | `thread-tb9msq-kfbqdenu0nyj` |
| traceId | Grouping key | `6cdc842e34e8a9c9a6f433d24ce2b06a` |
| question | Selection | `app_lb_id:alb-xl0fyvx5lv1gv1yeu5 body_bytes_sent:1127 client_ip:23.55.36.85...` (the log sample the user pasted in) |
| answer | Selection | `I can see the query results, which show the request records whose path contains /family/member/viewMember. Here is the query that filters those records: ...` |
| model | Selection | `qwen3-coder-plus` |
| total_input_tokens | Computation | `42890` |
| total_output_tokens | Computation | `909` |
| llm_calls | Computation | `4` |
| tool_calls | Computation | `2` |
| e2e_latency | Computation | `21015` |
| models | Composition | `["qwen-flash","qwen3-coder-plus"]` |
| tools | Composition | `["Think","QuerySLSLogs"]` |
| tool_chain | Composition | `Think -> QuerySLSLogs` |
| process | Composition | *(shown below)* |

**The `process` column** (the complete processing trace, multi-line text):

```
[Agent] blueprint.vibeops.system.vibeops_main@v1.1.0 -> filter the records whose request_uri contains /family/member/viewMember...
[LLM] qwen-flash (721/11 tokens, 362ms)
[LLM] qwen3-coder-plus (11837/262 tokens, 5425ms)
[Tool] Think({"thought":"the user wants to filter request_uri values containing \"/family/member/viewMembe)
[LLM] qwen3-coder-plus (11899/188 tokens, 4289ms)
[Tool] QuerySLSLogs({"logstore":"hapi-gw-access-log","project":"hapi-prod","quer)
[LLM] qwen3-coder-plus (18433/448 tokens, 7790ms)
[Agent] agent.sls.sql.sql_generation@v1.0.0 -> I can see the query results...
[Agent] blueprint.vibeops.system.vibeops_main@v1.1.0 -> I can see the query results...
```

> The `process` column is built from standard SQL aggregate expressions (CASE plus
> array_agg plus array_join), demonstrating how advanced users can compose SQL freely.

**Step 2: wide table -> consolidated full text** (1 row -> 1 row, a column transformation)

Append an `extend` after `make-instance` to merge question, process, and answer into a
`full_text` column:

```
  | extend full_text=concat(
        '## User input', chr(10),
        substr(question, 1, 500), chr(10), chr(10),
        '## Processing trace', chr(10),
        process, chr(10), chr(10),
        '## Final output', chr(10),
        answer)
```

**What the `full_text` column looks like**:

```
## User input
app_lb_id:alb-xl0fyvx5lv1gv1yeu5
body_bytes_sent:1127
client_ip:23.55.36.85
...

## Processing trace
[Agent] blueprint.vibeops.system.vibeops_main@v1.1.0 -> filter the records whose request_uri contains /family/member/viewMember...
[LLM] qwen-flash (721/11 tokens, 362ms)
[LLM] qwen3-coder-plus (11837/262 tokens, 5425ms)
[Tool] Think({"thought":"the user wants to filter request_uri values containing "/family/member/viewMembe)
[LLM] qwen3-coder-plus (11899/188 tokens, 4289ms)
[Tool] QuerySLSLogs({"logstore":"hapi-gw-access-log","project":"hapi-prod","quer)
[LLM] qwen3-coder-plus (18433/448 tokens, 7790ms)
[Agent] agent.sls.sql.sql_generation@v1.0.0 -> I can see the query results...

## Final output
I can see the query results, which show the request records whose path contains `/family/member/viewMember`.
Here is the query that filters those records: ...
```

> **How the two steps divide responsibility**: step 1 (`extend` plus `where` plus
> `make-instance`) handles field extraction, event filtering, and data assembly (28 rows
> -> 1 row); step 2 (`extend`) handles the row-level column transformation, merging
> several columns into `full_text` so a downstream `llm-call` can evaluate the whole
> thing. The entire process is pure CPU with no LLM or GPU dependency.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

### SPL-layer implementation

At this stage `make-instance` **adds no new SPL operator**; it reuses the existing
`stats` command syntax. The API Node layer is responsible for:

1. Translating the three families of syntactic-sugar functions into standard SQL
   aggregate expressions
2. Passing SQL functions through unchanged
3. Assembling the result into a `stats ... by ...` SPL output

The SPL layer may implement a standalone `make-instance` operator later, at which point
the API translation layer only needs to change the command name emitted by `to_spl()`.

### Syntactic-sugar translation rules

There are 7 syntactic-sugar functions, and only the non-SQL functions get a lightweight
string translation. Only one level of nesting is supported (`any(join(...))` is not).

#### Selection family

| Syntactic sugar | SQL translation |
|-----------------|-----------------|
| `any(col)` | `ARBITRARY(NULLIF(col, ''))` |
| `any(col, 'default')` | `ARBITRARY(NULLIF(col, 'default'))` |
| `first(col)` | `MIN_BY(NULLIF(col, ''), __time__)` |
| `first(col, ordering)` | `MIN_BY(NULLIF(col, ''), ordering)` |
| `last(col)` | `MAX_BY(NULLIF(col, ''), __time__)` |
| `last(col, ordering)` | `MAX_BY(NULLIF(col, ''), ordering)` |

#### Composition family

| Syntactic sugar | SQL translation |
|-----------------|-----------------|
| `join(col, sep)` | `array_join(filter(array_agg(col), x -> x IS NOT NULL AND x != ''), sep)` |
| `join(col, sep, order_by)` | `array_join(transform(array_sort(filter(array_agg(concat(cast({order_by} as varchar), chr(31), col)), x -> x IS NOT NULL AND x != '' AND length(x) > strpos(x, chr(31)))), x -> substr(x, strpos(x, chr(31)) + 1)), sep)` |
| `array(col)` | `filter(array_agg(col), x -> x IS NOT NULL AND x != '')` |
| `array(col, order_by)` | `transform(array_sort(filter(array_agg(concat(cast({order_by} as varchar), chr(31), col)), x -> x IS NOT NULL AND x != '' AND length(x) > strpos(x, chr(31)))), x -> substr(x, strpos(x, chr(31)) + 1))` |
| `array_distinct(col)` | `array_distinct(filter(array_agg(col), x -> x IS NOT NULL AND x != ''))` |
| `array_distinct(col, order_by)` | `array_distinct(transform(array_sort(filter(array_agg(concat(cast({order_by} as varchar), chr(31), col)), x -> x IS NOT NULL AND x != '' AND length(x) > strpos(x, chr(31)))), x -> substr(x, strpos(x, chr(31)) + 1)))` |
| `json_pack(c1, c2, ...)` | `CAST(MAP(ARRAY['c1','c2',...], ARRAY[c1,c2,...]) AS JSON)` |

> **order_by accepts any SQL expression**: the `order_by` argument is not limited to a
> field name; it can be any valid SQL expression (`coalesce(startTime, 0)`,
> `cast(startTime as bigint)`, `startTime + duration`, and so on).
> The parser tracks parenthesis depth so commas inside nested function calls are not
> split by mistake.
> Translation mode: the current workaround wraps the expression in
> `cast({order_by_expr} as varchar)`; once SLS supports this natively, the same
> expression works inside an `ORDER BY {order_by_expr}` clause.
>
> `{ts}` = the value of the `timestamp` parameter, `__time__` by default.
>
> **Current stage (workaround)**: SLS stats mode does not yet support
> `ARRAY_AGG(col ORDER BY field) FILTER(WHERE ...)`. When `order_by` is given, the
> translator uses the workaround
> `concat(cast(order_by as varchar), chr(31), col)` -> `array_agg` -> `filter` ->
> `array_sort` -> `transform` (stripping the prefix) -> `array_join`; when it is absent,
> the backward-compatible lambda-filter form is kept.
>
> **Future plan**: once SLS stats mode supports
> `ARRAY_AGG(col ORDER BY field) FILTER(WHERE ...)` natively, switch to the native
> implementation and emit an `ORDER BY` clause directly, dropping the prefix plus
> array_sort workaround.

## SQL implementation template

### Standard mode (translated into stats)

```sql
-- make-instance is translated into a stats command, and the final SQL is equivalent to:
SELECT
    {{by_columns}},
    {{#each columns}}
    {{this.sql_expression}} AS {{this.alias}},
    {{/each}}
FROM ##sourceTable##
GROUP BY {{by_columns}}
```

### Rendering example

Input:

```
make-instance question=first(question), model=any(model), max_lat=max(latency_ms),
              tools=array_distinct(tool_name) by session_id,trace_id
```

Translated SPL (the stats command):

```
stats MIN_BY(NULLIF(question, ''), __time__) AS question,
      ARBITRARY(NULLIF(model, '')) AS model,
      max(latency_ms) AS max_lat,
      array_distinct(filter(array_agg(CASE WHEN tool_name IS NOT NULL AND tool_name != '' THEN tool_name ELSE NULL END), x -> x IS NOT NULL)) AS tools
      by session_id, trace_id
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{by_columns}}` | `by` | - | The grouping keys |
| `{{columns}}` | Column definitions | - | The translated SQL aggregate expressions plus aliases |
| `{ts}` | `timestamp` | `__time__` | The time-ordering field |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `ARBITRARY(x)` | PrestoSQL built-in; returns any non-NULL value in the group |
| `NULLIF(x, y)` | SQL standard; returns NULL when x equals y |
| `MIN_BY(x, ordering)` | PrestoSQL built-in; the value of x where ordering is smallest |
| `MAX_BY(x, ordering)` | PrestoSQL built-in; the value of x where ordering is largest |
| `array_agg(x)` | PrestoSQL built-in; collects values into an array |
| `array_distinct(array)` | PrestoSQL built-in; deduplicates an array |
| `array_join(array, sep)` | PrestoSQL built-in; joins an array into a string |
| `filter(array, lambda)` | PrestoSQL built-in; filters array elements by a lambda |
| `CAST(MAP(...) AS JSON)` | PrestoSQL built-in; converts a MAP to JSON |

## Edge cases

| Case | Handling |
|------|----------|
| A `by` grouping-key value is NULL | The event takes no part in grouping (it is filtered out) |
| A referenced field is empty across the whole group | The aggregate function returns NULL |
| The input is empty (0 rows) | An empty result set is returned |
| The group has only 1 event | Processed normally; aggregate functions work on a single row too |
| Events of certain event_types are missing | Tolerated; missing fields become NULL or an empty array |
| A column definition uses a bare field name | The validate stage reports an error; an explicit function call is required |
| Syntactic-sugar functions are nested | The validate stage reports an error; only one level is supported |
