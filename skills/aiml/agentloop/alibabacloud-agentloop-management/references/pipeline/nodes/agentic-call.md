# agentic-call (agent invocation)

> Call a digital employee to hold a conversation about every row, with
> prompt-template rendering and employee configuration.

## Function

`agentic-call` is the base node for calling a digital employee (a data-insight
agent) from a Pipeline.

How it differs from `llm-call`: `llm-call` is a single pure LLM inference call,
while `agentic-call` invokes a digital employee the user has built. A digital
employee encapsulates a complete SOP analysis flow and skill capabilities, so it
can perform multi-step reasoning, knowledge-base retrieval, tool calls, and other
complex tasks.

The core flow:

1. **Extract**: read the field values named by `fields` from the input row
2. **Render**: substitute those values into the `{{column}}` placeholders of the
   prompt template to build the full message
3. **Invoke**: trigger one independent digital-employee conversation per row
4. **Return**: take the plain-text reply of the conversation and store it in a new
   column

Each row is handled independently. The node only adds columns; it never removes
existing columns and never changes the row count.

**Use cases**:

- **Intelligent analysis**: have a digital employee run SOP analysis and root-cause
  location on alerts, logs, or metrics
- **Knowledge Q&A**: answer domain questions from the digital employee's knowledge
  base
- **Data insight**: launch an independent intelligent analysis per row and collect
  the textual insight
- **Batch conversation**: trigger agent calls in parallel across many rows to
  gather analysis results in bulk

## Node configuration

```json
{
  "id": "node_1",
  "type": "agentic-call",
  "parameters": {
    "prompt": "<prompt-template-or-reference>",
    "fields": "<columns-used-for-rendering>",
    "employee": "<digital-employee-name>",
    "skill": "<skill-id>",
    "as": "<output-column-name>",
    "output": "<output-column-list>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | String | **Yes** | - | The prompt template, using `{{column}}` placeholders. Inline text or an `@<path>` reference to a registered template |
| `fields` | String | **Yes** | - | Input columns used for rendering, comma separated. Every column must have a matching `{{column}}` placeholder in the prompt |
| `employee` | String | **Yes** | - | Digital-employee name, such as `skill_bench_analysis` or `apsara-ops` |
| `skill` | String | No | `"sop"` | Digital-employee skill identifier |
| `as` | String | No | `"__agentic_result"` | Output column name |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |

> **Prompt authoring guide**:
>
> - Placeholders use the `{{column}}` syntax and the column names must match those
>   declared in `fields`
> - Validation is automatic: every `{{column}}` in the prompt must be declared in
>   `fields`, and vice versa
> - Register a very long prompt as a named template and reference it with `@<path>`
>
> **Template reference formats**:
>
> | `prompt` value | Description |
> |----------------|-------------|
> | `@analysis/alert_diagnosis.md` | References a registered named template |
> | `Analyze the {{metric_name}} anomaly on {{host_name}}` | Inline prompt text |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- Every column declared in `fields` must be present

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | — | Pass-through / added | `*` keeps every column (including derived ones); when set, only the listed columns are emitted |
| `{as}` | varchar | Added | The plain-text reply from the digital employee; NULL when the conversation fails |

**Row-count change**:

M → N (M = N) — a 1:1 transformation; one digital-employee conversation is
triggered per row and no rows are added or dropped.

## Effect preview

**Before** (3 rows):

| host_name | metric_name | alert_level |
|-----------|-------------|-------------|
| web-server-01 | cpu_usage | critical |
| db-server-02 | disk_io | warning |
| app-server-03 | memory | critical |

**After** (3 rows) — `employee = "skill_bench_analysis"`,
`prompt = "Analyze…"`, `fields = "host_name,metric_name"`, `as = "analysis"`:

| host_name | metric_name | alert_level | analysis |
|-----------|-------------|-------------|----------|
| web-server-01 | cpu_usage | critical | CPU usage on web-server-01 stayed above 95%; the root cause is… |
| db-server-02 | disk_io | warning | db-server-02 shows intermittent disk-IO spikes; check… |
| app-server-03 | memory | critical | Memory usage on app-server-03 reached 98%, with a memory-leak risk… |

> The row count is unchanged (3 → 3) and every row gains an `analysis` column
> holding the digital employee's reply text.

## Examples

### Example 1: metric-anomaly analysis

```json
{
  "id": "n7",
  "type": "agentic-call",
  "parameters": {
    "prompt": "Analyze the cause of the {{metric_name}} anomaly on {{host_name}}",
    "fields": "host_name,metric_name",
    "employee": "skill_bench_analysis",
    "as": "analysis"
  }
}
```

Calls the `skill_bench_analysis` digital employee to root-cause each alert row.

### Example 2: SOP knowledge Q&A (with an explicit skill)

```json
{
  "id": "n7",
  "type": "agentic-call",
  "parameters": {
    "prompt": "{{question}}",
    "fields": "question",
    "employee": "apsara-ops",
    "skill": "sop",
    "as": "answer"
  }
}
```

Calls the `sop` skill of the `apsara-ops` digital employee to answer business
questions.

### Example 3: use a named template

```json
{
  "id": "n7",
  "type": "agentic-call",
  "parameters": {
    "prompt": "@analysis/alert_diagnosis.md",
    "fields": "host_name,metric_name,metric_value",
    "employee": "skill_bench_analysis",
    "as": "diagnosis"
  }
}
```

Analyzes using a pre-registered prompt template.

### Example 4: complete pipeline (filter → sample → agent analysis)

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "host_name": "a", "metric_name": "b", "alert_level": "c", "metric_value": "d" } },
    { "id": "n2", "type": "where", "parameters": { "filter": "alert_level = 'critical'" } },
    { "id": "n3", "type": "sample", "parameters": { "n": 50 } },
    { "id": "n4", "type": "agentic-call", "parameters": { "prompt": "Analyze the {{metric_name}} anomaly on {{host_name}}; the current value is {{metric_value}}", "fields": "host_name,metric_name,metric_value", "employee": "skill_bench_analysis", "as": "analysis" } }
  ]
}
```

Filter the critical alerts, sample to control the volume, then have the digital
employee analyze them one by one.

## Notes

**Recommended usage**:
- **Strongly prefer running it after filtering and sampling** — a digital-employee
  call is slower than a plain LLM call (multi-step reasoning and knowledge
  retrieval) and is billed per invocation, so reducing the volume first cuts cost
  substantially
- Recommended pipeline order: filter → sample → `agentic-call`
- Each row's message opens its own conversation thread, so contexts stay isolated

**Best practices**:
- **Employee choice**: pick the digital employee and skill that match the business
  scenario; different employees carry different knowledge bases and SOP flows
- **Template reuse**: register a very long prompt as a named template
  (`@analysis/alert_diagnosis.md`) for version control
- **Result extraction**: the output is plain text (varchar); to extract structured
  data, follow it with `extend` plus `regexp_extract` or `json_parse`
- **Idempotency**: the digital employee's output for the same input is not
  guaranteed to be identical (the model and knowledge-base version affect it)
- **Timeout**: a single request times out after 10 minutes, so keep the prompt
  concise and explicit for complex analysis tasks

**Edge cases**:

| Case | Behavior |
|------|----------|
| `prompt` is missing or empty | Validation fails |
| `fields` is missing or empty | Validation fails |
| `employee` is missing or empty | Validation fails |
| A column in `fields` is absent from the input | Runtime error |
| The named template (`@path`) does not exist | Runtime error |
| A column value is NULL | The digital employee may return an incomplete result |
| The digital-employee conversation times out | Returns NULL |
| The digital employee does not exist | Returns NULL |

## Related nodes

| Node | Relationship |
|------|--------------|
| `llm-call` | Also an AI processing node. `llm-call` is for pure LLM inference, `agentic-call` for a digital-employee conversation |
| `where` | Filter with `where` before `agentic-call` to lower the invocation count |
| `sample` | Prefer running `agentic-call` after `sample` to control invocation cost |
| `extend` | A later `extend` can extract and compute on the text output of `agentic-call` |
