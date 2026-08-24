# agentic-call (agent invocation)

> Call a digital employee (an agentic agent) to hold one intelligent conversation per
> row, with prompt-template rendering and employee configuration.

## Function

`agentic-call` is the base operator (a scalar instruction) for calling a digital
employee (a data-insight agent) from a Pipeline.

How it differs from `llm-call`: `llm-call` is a single, pure LLM inference call, whereas
`agentic-call` invokes a digital employee that the user has built. The employee
encapsulates a complete SOP analysis flow and skill capabilities, so it can perform
multi-step reasoning, knowledge-base retrieval, tool calls, and other complex tasks.

The core flow:

1. **Extract**: pull the values of the columns named by `-fields` from the input row
2. **Render**: substitute those values into the prompt template's placeholders to build
   the complete message
3. **Call**: each row triggers an independent conversation with the digital employee
   (creating a Thread plus a Chat)
4. **Return**: extract the plain-text reply from the conversation and store it as a new
   column

As a scalar instruction, `agentic-call` processes each row independently: it **only adds
a new column, never drops existing columns, and never changes the row count**. Each
message creates its own Thread, which is not reused after the conversation ends.

**Use cases**:

- **Intelligent analysis**: have a digital employee run SOP analysis and root-cause
  location on alerts, logs, and metrics
- **Knowledge Q&A**: answer business-domain questions from the digital employee's
  knowledge base
- **Data insight**: run an independent intelligent analysis per row to obtain
  structured insight
- **Batch conversation**: trigger agent calls in parallel across many rows to collect
  analysis results in bulk

## Syntax

```
| agentic-call -prompt=<template> -fields=<columns> -employee=<name> [-skill=<skill>] [as <name>]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-prompt` | String | **Yes** | - | The prompt template, using `{{column}}` as placeholders. Accepts inline text or an `@<path>` reference to a registered template |
| `-fields` | FieldList | **Yes** | - | The input columns used for rendering, comma-separated. Every column must have a matching `{{column}}` placeholder in `-prompt` |
| `-employee` | String | **Yes** | - | Digital-employee name, such as `skill_bench_analysis` or `apsara-ops` |
| `-skill` | String | No | `sop` | The digital employee's skill identifier, passed through Chat Variables |
| `as` | Field | No | `__agentic_result` | Output column name (an instruction primitive, without the `-` prefix) |

> **Prompt authoring guide**:
>
> - Placeholders use the `{{column}}` syntax, with names matching those declared in
>   `-fields`: `{{host_name}}`, `{{metric_name}}`
> - The engine validates automatically: every `{{var}}` in the prompt must be declared
>   in `-fields`, and every column in `-fields` must appear in the prompt as
>   `{{column}}`
> - Register very long prompts as named templates and reference them with `@<path>`

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- Every column declared in `-fields` must be present

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Input | Every upstream column passes through |
| `{{as}}` | varchar | Derived | The plain-text reply from the digital-employee conversation; NULL when the conversation fails |

**Input-to-output relationship**:

M:N (M = N) - a 1:1 scalar transformation; each row triggers one digital-employee
conversation and no rows are added or dropped.

## Effect preview

**Before** (3 rows):

| host_name | metric_name | alert_level |
|-----------|-------------|-------------|
| web-server-01 | cpu_usage | critical |
| db-server-02 | disk_io | warning |
| app-server-03 | memory | critical |

**After** (3 rows) - `| agentic-call -prompt='Analyze why the {{metric_name}} metric of {{host_name}} is abnormal' -fields=host_name,metric_name -employee='skill_bench_analysis' as analysis`:

| host_name | metric_name | alert_level | analysis |
|-----------|-------------|-------------|----------|
| web-server-01 | cpu_usage | critical | CPU usage on web-server-01 has stayed above 95%; the root cause is... |
| db-server-02 | disk_io | warning | Disk IO on db-server-02 shows intermittent spikes; check... |
| app-server-03 | memory | critical | Memory usage on app-server-03 has reached 98%, suggesting a memory leak... |

> The row count is unchanged (3 -> 3) and every row gains an `analysis` column holding
> the digital employee's conversation reply.

## Examples

### Example 1: metric anomaly analysis

```
* | project host_name, metric_name
  | agentic-call 
    -prompt='Analyze why the {{metric_name}} metric of {{host_name}} is abnormal'
    -fields=host_name,metric_name
    -employee='skill_bench_analysis'
    as analysis
```

Calls the `skill_bench_analysis` digital employee to run root-cause analysis on each
alert row.

### Example 2: SOP knowledge Q&A (with an explicit skill)

```
* | project question
  | agentic-call 
    -prompt='{{question}}'
    -fields=question
    -employee='apsara-ops'
    -skill='sop'
    as answer
```

Calls the `sop` skill of the `apsara-ops` digital employee to answer business
questions.

### Example 3: using a named template

```
* | project host_name, metric_name, metric_value
  | agentic-call 
    -prompt='@analysis/alert_diagnosis.md'
    -fields=host_name,metric_name,metric_value
    -employee='skill_bench_analysis'
    as diagnosis
```

References a pre-registered prompt template for the analysis.

### Example 4: pipeline composition (sampling -> agent analysis)

```
* | project host_name, metric_name, alert_level, metric_value
  | where alert_level = 'critical'
  | sample -n=50
  | agentic-call 
    -prompt='Analyze the {{metric_name}} anomaly on {{host_name}}; the current value is {{metric_value}}'
    -fields=host_name,metric_name,metric_value
    -employee='skill_bench_analysis'
    as analysis
```

Filter critical alerts first, sample to control the volume, then have the digital
employee analyze each row.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Positioning**: `agentic-call` is the base operator for calling a digital employee
  from a Pipeline. It complements `llm-call` (pure LLM inference): `llm-call` targets
  simple prompt-in / text-out scenarios, while `agentic-call` targets scenarios that
  need SOP analysis flows, knowledge bases, tool calls, and other complex capabilities.
- **Relationship with `llm-call`**: the two share the same prompt-template rendering
  mechanism (`-prompt` plus `-fields`) but call different remote functions underneath:
  `llm-call` calls `ai_gen_with_template()` and `agentic-call` calls `agentic_call()`.
- **Output type**: `agentic-call` always returns `varchar` (the digital employee's
  plain-text reply); unlike `llm-call`, it has no `format=json` structured-output
  parsing. To extract structured data from the reply, process it downstream with
  `extend` plus `json_parse()` or `regexp_extract()`.
- **Scalar semantics**: as a scalar instruction, `agentic-call` processes each row
  independently and only adds the `{{as}}` column; it drops no existing columns and does
  not change the row count.
- **Conversation isolation**: each message creates its own Thread (`CreateThread`),
  which is not reused after the conversation ends. This guarantees context isolation
  between rows.
- **params encapsulation**: the last argument of the underlying `agentic_call()`
  function is a JSON `params` object. The Pipeline operator layer packs the `-employee`
  and `-skill` parameters into that JSON, hiding the low-level detail.
- **Performance and cost**: digital-employee calls are usually slower than plain LLM
  calls (they involve multi-step reasoning and knowledge retrieval), with a per-request
  timeout of 10 minutes. Using them after filtering and sampling is strongly
  recommended.
- **Idempotency**: the digital-employee output for the same input is not guaranteed to
  be identical (the model and knowledge-base version affect it).

## SQL implementation template

```sql
set session enable_remote_functions = true;
WITH
_agentic_ AS (
    SELECT 
        agentic_call(
            '{{prompt_text}}',
            ARRAY[{{placeholders}}],
            ARRAY[{{fields}}],
            '{{params_json}}'
        ) AS {{as}}
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _agentic_
```

> `{{as}}` has type `varchar`.
> On a successful conversation it holds the reply text; on failure it is NULL.

### Full SPL to SQL expansion example

The SPL command:

```
| agentic-call -prompt='Analyze why the {{metric_name}} metric of {{host_name}} is abnormal' -fields=host_name,metric_name -employee='skill_bench_analysis' -skill='sop' as analysis
```

v the engine expands it to:

```sql
set session enable_remote_functions = true;
WITH
_agentic_ AS (
    SELECT
        agentic_call(
            'Analyze why the {{metric_name}} metric of {{host_name}} is abnormal',
            ARRAY['{{host_name}}', '{{metric_name}}'],
            ARRAY["host_name", "metric_name"],
            '{"employee_name": "skill_bench_analysis", "skill": "sop"}'
        ) AS analysis
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _agentic_
```

### With a named template

The SPL command:

```
| agentic-call -prompt='@analysis/alert_diagnosis.md' -fields=host_name,metric_name -employee='skill_bench_analysis' as diagnosis
```

v the engine expands it to:

```sql
set session enable_remote_functions = true;
WITH
_agentic_ AS (
    SELECT
        agentic_call(
            'sls://builtin_prompt/analysis/alert_diagnosis.md',
            ARRAY['{{host_name}}', '{{metric_name}}'],
            ARRAY["host_name", "metric_name"],
            '{"employee_name": "skill_bench_analysis"}'
        ) AS diagnosis
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _agentic_
```

## Prompt rendering rules

> **Template path translation**:
> When `-prompt` starts with `@` it references a named template, which the engine
> translates into an `sls://builtin_prompt/` path:
> | SPL `-prompt` | Translated `template` argument |
> |---------------|-------------------------------|
> | `'@analysis/alert_diagnosis.md'` | `'sls://builtin_prompt/analysis/alert_diagnosis.md'` |
> | `'inline text...'` | Passed through unchanged |
>
> **Field array generation**:
> The `agentic_call` function supports template rendering natively, and the SPL
> translation engine generates the placeholder array and the column-reference array
> from `-fields`:
>
> **Input**:
> - `-prompt='Analyze why the {{metric_name}} metric of {{host_name}} is abnormal'`
> - `-fields=host_name,metric_name`
>
> **Generated**:
> ```sql
> agentic_call(
>     '{{prompt_text}}',                                -- inline text or a named-template reference
>     ARRAY['{{host_name}}', '{{metric_name}}'],        -- placeholder array
>     ARRAY["host_name", "metric_name"],                -- column-reference array
>     '{{params_json}}'                                 -- employee configuration JSON
> )
> ```
>
> **params JSON construction**:
> The engine builds the `params` JSON string from the `-employee` and `-skill`
> parameters:
> - `-employee='skill_bench_analysis'` alone -> `'{"employee_name": "skill_bench_analysis"}'`
> - `-employee='skill_bench_analysis' -skill='sop'` -> `'{"employee_name": "skill_bench_analysis", "skill": "sop"}'`

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{prompt_text}}` | `-prompt` | - | Inline text is passed straight through; a named-template reference (`@<path>`) is translated by the engine into `sls://builtin_prompt/<path>` |
| `{{placeholders}}` | Generated from `-fields` | - | The placeholder-name array. For example `-fields=host_name,metric_name` -> `'{{host_name}}', '{{metric_name}}'` |
| `{{fields}}` | Generated from `-fields` | - | The column-reference array (double-quoted identifiers). For example `-fields=host_name,metric_name` -> `"host_name", "metric_name"` |
| `{{params_json}}` | Built from `-employee` and `-skill` | - | The digital-employee configuration JSON string |
| `{{as}}` | `as` | `__agentic_result` | Output column name |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `agentic_call(template, placeholders, columns, params) -> varchar` | Start one conversation with a digital employee (remote function). `template` is inline template text or an `sls://` reference path, `placeholders` is an `ARRAY[varchar]` of placeholder names, `columns` is an `ARRAY[varchar]` of the matching column values, and `params` is the JSON configuration string |

## Edge cases

| Case | Handling |
|------|----------|
| `-prompt` is empty | The engine raises a parameter-validation error |
| `-fields` is empty | The engine raises a parameter-validation error (at least one column is required) |
| `-employee` is empty | The engine raises a parameter-validation error |
| A column in `-fields` is absent from the input | The engine raises a parameter-validation error |
| A column in `-fields` has no matching `{{column}}` in the prompt | The engine raises a parameter-validation error |
| The prompt contains a `{{var}}` that is not in `-fields` | The engine raises a parameter-validation error |
| The named template (`@name`) does not exist | The engine raises a parameter-validation error noting the template is not registered |
| A column value is NULL | `agentic_call` renders the NULL into the template and may return an incomplete result |
| The input is empty (0 rows) | An empty result set is returned normally |
| The digital-employee conversation times out | `{{as}}` is NULL (the per-request timeout is 10 minutes) |
| The digital employee does not exist | `{{as}}` is NULL |
| The message content is empty | `{{as}}` is NULL |
| Concurrency limiting | Call concurrency is controlled by the SLS engine |
