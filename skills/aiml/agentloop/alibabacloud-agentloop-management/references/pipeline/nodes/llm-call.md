# llm-call (LLM invocation)

> Call a large language model on every row, with prompt-template rendering, model
> selection, and output-format parsing.

## Function

`llm-call` is the base node for every LLM processing task in a Pipeline.

The core flow:

1. **Extract**: read the field values named by `fields` from the input row
2. **Render**: substitute those values into the `{{column}}` placeholders of the
   prompt template to build the full prompt
3. **Invoke**: run inference on the selected LLM
4. **Parse**: parse the LLM output according to `format` and store it in a new
   column

Each row is handled independently. The node only adds columns; it never removes
existing columns and never changes the row count.

**Use cases**:

- **AI evaluation**: score question/answer pairs on several quality dimensions
  (JSON output)
- **AI labeling**: classify text or tag entities (JSON output)
- **AI synthesis**: generate rewritten, expanded, or translated data from the
  source rows
- **AI filtering**: let the LLM judge data quality, then filter with a downstream
  `where`
- **General tasks**: summarization, classification, entity extraction, or anything
  else a prompt can express

## Node configuration

```json
{
  "id": "node_1",
  "type": "llm-call",
  "parameters": {
    "prompt": "<prompt-template-or-reference>",
    "fields": "<columns-used-for-rendering>",
    "format": "raw | json",
    "model": "<model-id>",
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
| `format` | String | No | `"raw"` | Output parsing format: `raw` returns the text as-is; `json` guarantees valid JSON |
| `model` | String | No | System default model | LLM model identifier, such as `qwen-turbo` or `qwen-plus` |
| `as` | String | No | `"__llm_result"` | Output column name |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |

> **Prompt authoring guide**:
>
> - Placeholders use the `{{column}}` syntax and the column names must match those
>   declared in `fields`
> - Validation is automatic: every `{{column}}` in the prompt must be declared in
>   `fields`, and vice versa
> - When JSON output is needed, state that clearly in the prompt and set
>   `format: "json"`
> - Register a very long prompt as a named template and reference it with
>   `@<path>` (for example `@eval/requirement_understanding_v1.md`)
>
> **Template reference formats**:
>
> | `prompt` value | Description |
> |----------------|-------------|
> | `@eval/requirement_understanding_v1.md` | References a registered named template |
> | `@anno/template.md` | References a labeling template |
> | `Translate the following...{{content}}` | Inline prompt text |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- Every column declared in `fields` must be present

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | — | Pass-through / added | `*` keeps every column (including derived ones); when set, only the listed columns are emitted |
| `{as}` | varchar or json | Added | `format=raw` yields varchar; `format=json` yields json (always valid JSON) |

**`format=json` output guarantee**:

| LLM result | `{as}` column value |
|------------|--------------------|
| Success with valid JSON | Returned as-is, for example `{"score":4,"reason":"..."}` |
| Success with invalid JSON | `{"__raw":"the raw LLM output..."}` |
| Invocation failed | `{"__error":"timeout"}` |

**`format=raw` output**:

| LLM result | `{as}` column value |
|------------|--------------------|
| Success | The raw LLM output text |
| Invocation failed | An error description string |

**Row-count change**:

M → N (M = N) — a 1:1 transformation; the LLM is called once per row and no rows
are added or dropped.

## Effect preview

**Before** (3 rows):

| question | output |
|----------|--------|
| What is machine learning? | Machine learning is an important branch of artificial intelligence |
| How do I learn Python? | Start with the official tutorial, then build projects |
| 1+1=? | 2 |

**After** (3 rows) — `prompt = "Please evaluate…"`, `fields = "question,output"`,
`format = "json"`, `as = "eval"`:

| question | output | eval |
|----------|--------|------|
| What is machine learning? | Machine learning is… | `{"score":4,"reason":"accurate but not detailed enough"}` |
| How do I learn Python? | Start with the official tutorial… | `{"score":5,"reason":"specific and practical advice"}` |
| 1+1=? | 2 | `{"score":3,"reason":"correct but far too short"}` |

> The row count is unchanged (3 → 3) and every row gains an `eval` column.
> `format = "json"` guarantees the output is always valid JSON. Combine it with the
> `where` node to filter by score.

## Examples

### Example 1: AI quality evaluation (JSON output)

```json
{
  "id": "n7",
  "type": "llm-call",
  "parameters": {
    "prompt": "Evaluate the following Q&A pair. Question: {{question}} Answer: {{output}} Output JSON: {\"score\":<score>,\"reason\":\"<reason>\"} Output pure JSON only.",
    "fields": "question,output",
    "format": "json",
    "as": "eval"
  }
}
```

The evaluation result lands in the `eval` column.

### Example 2: AI labeling (named template plus explicit model)

```json
{
  "id": "n7",
  "type": "llm-call",
  "parameters": {
    "prompt": "@anno/template_v1.md",
    "fields": "output",
    "format": "json",
    "model": "qwen-plus",
    "as": "anno"
  }
}
```

References a pre-registered prompt template and runs it on `qwen-plus`.

### Example 3: text translation (raw mode)

```json
{
  "id": "n7",
  "type": "llm-call",
  "parameters": {
    "prompt": "Translate the following into English: {{content}}",
    "fields": "content",
    "as": "translation"
  }
}
```

`format` is omitted (defaulting to `raw`) and the translation lands in the
`translation` column.

### Example 4: complete pipeline (dedup → sample → evaluate + label)

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-semantic", "parameters": { "field": "question", "threshold": "0.1" } },
    { "id": "n4", "type": "semantic-cluster", "parameters": { "field": "__dedup_emb", "n": 100 } },
    { "id": "n5", "type": "sample", "parameters": { "by": "__cluster_id", "n": 3 } },
    { "id": "n6", "type": "llm-call", "parameters": { "prompt": "@eval/prompt.md", "fields": "question,input,output", "format": "json", "as": "eval" } },
    { "id": "n7", "type": "llm-call", "parameters": { "prompt": "@anno/prompt.md", "fields": "output", "format": "json", "model": "qwen-plus", "as": "anno" } }
  ]
}
```

Three-stage dedup → cluster sampling → two LLM calls (evaluation and labeling).

## Notes

**Recommended usage**:
- **Strongly prefer running it after dedup and sampling** — LLM calls are slow
  (usually seconds per row) and billed per token, so reducing the volume first can
  cut cost by more than 90%
- Recommended pipeline order: dedup → cluster sampling → `llm-call`
- The same `llm-call` node covers evaluation, labeling, synthesis, and filtering
  simply by changing the prompt

**Best practices**:
- **Prompt design**: when JSON output is needed, end the prompt with an "output
  pure JSON only" constraint and set `format = "json"`
- **Template reuse**: register a very long prompt as a named template
  (`@eval/prompt.md`) for version control and reuse
- **Result extraction**: `format = "json"` guarantees valid JSON, so unpack fields
  with `extend` plus `json_extract` and then filter with `where`
- **Idempotency**: the LLM output for the same input is not guaranteed to be
  identical (parameters such as temperature affect it)

**Edge cases**:

| Case | Behavior |
|------|----------|
| `prompt` is missing or empty | Validation fails |
| `fields` is missing or empty | Validation fails |
| A column in `fields` is absent from the input | Runtime error |
| `format` is neither `raw` nor `json` | Validation fails |
| The named template (`@path`) does not exist | Runtime error |
| A column value is NULL | The LLM may return an incomplete result |
| The LLM call times out | `format=raw` returns error text; `format=json` returns `{"__error":"timeout"}` |

## Related nodes

| Node | Relationship |
|------|--------------|
| `where` | After LLM evaluation, `where` can filter by score |
| `sample` | Prefer running `llm-call` after `sample` to control invocation cost |
| `extend` | A later `extend` can unpack and compute on the JSON output of `llm-call` |
