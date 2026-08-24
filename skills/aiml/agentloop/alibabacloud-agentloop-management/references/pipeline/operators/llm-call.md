# llm-call (LLM invocation)

> Call a large language model to process each row intelligently, with prompt-template
> rendering, model selection, and output-format parsing.

## Function

`llm-call` is the base operator (a scalar instruction) behind every LLM processing task
in a Pipeline.

The core flow:

1. **Extract**: pull the values of the columns named by `-fields` from the input row
2. **Render**: substitute those values into the prompt template's placeholders to build
   the complete prompt
3. **Call**: invoke the configured LLM model for inference
4. **Parse**: parse the LLM output according to `-format` and store it as a new column

As a scalar instruction, `llm-call` processes each row independently: it **only adds a
new column, never drops existing columns, and never changes the row count**. The same
underlying capability serves different business goals purely through prompt
configuration.

**Use cases**:

- **AI evaluation**: score question-answer pairs on several quality dimensions and emit
  a JSON score
- **AI annotation**: classify text or tag entities and emit JSON labels
- **AI synthesis**: generate rewrites, expansions, translations, and other synthetic
  data from the original records
- **AI filtering**: let the LLM judge data quality, then filter with a downstream
  `where`
- **General tasks**: summarization, classification, entity extraction - any AI task a
  prompt can define

## Syntax

```
| llm-call -prompt=<template> -fields=<columns> [-format=<type>] [-model=<model>] [as <name>]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-prompt` | String | **Yes** | - | The prompt template, using `{{column}}` as placeholders. Accepts inline text or an `@<path>` reference to a registered template (such as `@eval/requirement_understanding_v1.md`) |
| `-fields` | FieldList | **Yes** | - | The input columns used for rendering, comma-separated. Every column must have a matching `{{column}}` placeholder in `-prompt` |
| `-format` | Enum | No | `raw` | Output parsing format:<br>- `raw` -> varchar - on success the raw LLM text, on failure an error description<br>- `json` -> json - valid JSON is returned as is; invalid JSON becomes `{"__raw":"..."}`; a failed call becomes `{"__error":"..."}` |
| `-model` | String | No | `qwen-turbo` | LLM model identifier, such as `qwen-turbo` or `qwen-plus` |
| `as` | Field | No | `__llm_result` | Output column name (an instruction primitive, without the `-` prefix) |

> **Prompt authoring guide**:
>
> - Placeholders use the `{{column}}` syntax, with names matching those declared in
>   `-fields`: `{{question}}`, `{{output}}`
> - The engine validates automatically: every `{{var}}` in the prompt must be declared
>   in `-fields`, and every column in `-fields` must appear in the prompt as
>   `{{column}}`
> - When JSON output is needed, state it explicitly in the prompt and set
>   `-format=json`
> - End the prompt with a constraint such as "Output pure JSON only, with no markdown
>   markers."
> - Register very long prompts as named templates and reference them with `@<path>`
>   (such as `@eval/requirement_understanding_v1.md`)

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- Every column declared in `-fields` must be present

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Input | Every upstream column passes through |
| `{{as}}` | Determined by `-format` | Derived | `-format=raw` -> varchar (the raw LLM text or an error description); `-format=json` -> json (always valid JSON) |

**Input-to-output relationship**:

M:N (M = N) - a 1:1 scalar transformation; each row calls the LLM independently and no
rows are added or dropped.

## Effect preview

**Before** (3 rows):

| question | output |
|----------|--------|
| What is machine learning? | Machine learning is an important branch of artificial intelligence |
| How do I learn Python? | Start with the official tutorial, then build a project |
| 1+1=? | 2 |

**After** (3 rows) - `| llm-call -prompt='Rate the answer quality. Question: {{question}} Answer: {{output}} Output JSON: {"score":n} Output pure JSON only.' -fields=question,output -format=json as eval`:

| question | output | eval |
|----------|--------|------|
| What is machine learning? | Machine learning is an important branch... | `{"score":4,"reason":"accurate but not detailed enough"}` |
| How do I learn Python? | Start with the official tutorial... | `{"score":5,"reason":"specific and practical advice"}` |
| 1+1=? | 2 | `{"score":3,"reason":"correct but too terse"}` |

> The row count is unchanged (3 -> 3) and every row gains an `eval` column
> (`format=json` guarantees valid JSON). Use
> `json_extract(eval, '$.score')` to pull the score out and `where` to filter
> low-scoring rows.

> **How downstream consumes the output**:
>
> `format=raw` - use the `{{as}}` column directly; its value is the LLM output text
> (or an error description when the call fails).
>
> `format=json` - the `{{as}}` column has type `json` and is **always valid**; access
> the result with `json_extract`:
>
> ```sql
> json_extract(eval, '$.score')                          -- extract a field
> json_extract(eval, '$["requirement_understanding"].score')  -- extract a nested field
> json_extract(eval, '$.__raw')                          -- when the LLM output is not JSON, it returns {"__raw":"raw LLM output..."}
> json_extract(eval, '$.__error')                        -- when the LLM call fails, it returns {"__error":"error description"}
> ```


## Examples

### Example 1: AI quality evaluation (JSON output)

```
* | project question,input,output
  | llm-call 
    -prompt='Evaluate the following question-answer pair. Question: {{question}} Answer: {{output}} Output JSON: {"score":n,"reason":"why"} Output pure JSON only.'
    -fields=question,output
    -format=json
    as eval
```

The evaluation result lands in the `eval` column. Pull the score out with
`json_extract(eval, '$.score')`.

### Example 2: AI annotation (named template plus explicit model)

```
* | project question,input,output
  | llm-call 
    -prompt='@anno/template_v1.md'
    -fields=output
    -format=json
    -model='qwen-plus'
    as anno
```

References a pre-registered prompt template and annotates with the `qwen-plus` model.

### Example 3: raw mode

```
* | project content
  | llm-call 
    -prompt='Translate the following content into English: {{content}}'
    -fields=content
    as translation
```

With no `-format` (the default is `raw`), the translation lands in the `translation`
column.

### Example 4: pipeline composition (dedup -> sample -> evaluate -> annotate -> expand)

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | dedup-semantic -field=question -threshold='0.1'
  | semantic-cluster -field=__dedup_emb -n=100
  | sample -n=3 by __cluster_id
  | llm-call -prompt='@eval/prompt.md' -fields=question,input,output -format=json as eval
  | llm-call -prompt='@anno/prompt.md' -fields=output -format=json -model='qwen-plus' as anno
  | llm-call -prompt='@synthetic/prompt.md' -fields=question,input,output -format=json as synthetic
```

Three-stage deduplication -> cluster sampling -> three LLM calls (evaluation,
annotation, expansion). The same operator serves different business logic through
different prompts.

### Example 5: the equivalent form of a higher-level wrapper operator

```
-- A higher-level wrapper operator (syntactic sugar):
* | project key1,key2,key3
  | correct_judge -fields=key1,key2,key3 as judge_result

-- Expands to the equivalent llm-call:
* | project key1,key2,key3
  | llm-call 
    -prompt='@eval/correct_judge.md'
    -fields=key1,key2,key3
    -format=json
    as judge_result
```

Every higher-level wrapper operator (`correct_judge`, `evaluator`, and so on) is
fundamentally an `llm-call` with a preset template and format.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Positioning**: `llm-call` is the **base operator** for every LLM call in a
  Pipeline. Any task built on a single LLM call (evaluation, annotation, generation,
  expansion, filtering, and so on) uses this operator and expresses its business goal
  through the prompt configuration. Higher-level wrapper operators (`correct_judge`,
  `evaluator`) are syntactic sugar and are expanded during translation into an
  `llm-call` with a preset template and format.
- **Relationship with `ai-gen`**: `llm-call` is the successor to `ai-gen`. The key
  differences: (1) the output is plain `varchar`, hiding the `ai_gen_with_template` ROW
  type so users do not need `.result`; (2) `format=json` always returns valid JSON, so
  no `coalesce` fallback is needed; (3) model selection (`-model`) is new. `ai-gen` can
  remain as a historical alias and be deprecated gradually.
- **Scalar semantics**: as a scalar instruction, `llm-call` processes each row
  independently and only adds the `{{as}}` column; it drops no existing columns and
  does not change the row count. This matches the semantics of the `extend` instruction
  in classic SPL. Narrow the output by appending a `project` later in the pipeline.
- **OutputParser roadmap**: `raw` and `json` are supported today. The following types
  can be added later (see the OutputParser definition in the Pipeline design document):

  | format | Description | Output type | Parsing strategy |
  |--------|-------------|-------------|------------------|
  | `score` | Numeric score | int | Extract an integer score from the LLM output (regex match) |
  | `float_score` | Floating-point score | double | Extract a floating-point score from the LLM output |
  | `code_block` | Code block | varchar | Extract the content of a Markdown code block (fenced with backticks) |
  | `tag_extract` | Tag extraction | varchar | Extract the content inside an XML/HTML tag |
  | `list` | List | array(varchar) | Parse a JSON array or split on newlines |
  | `regex` | Regex extraction | varchar | Custom regular-expression extraction (needs an extra `-pattern` parameter) |
  | `custom` | Custom | varchar | A custom parsing function |

- **Prompt rendering**: the translation engine scans every `{{column}}` placeholder in
  `-prompt` and matches it one-to-one with the `-fields` column names. Because
  `-fields` declares column names directly (rather than a key-value mapping), the
  placeholder name is the column name, which removes redundant mapping and lowers the
  risk of mistakes.
- **Template validation**: before rendering, the translation engine validates
  automatically that (1) every `{{column}}` in `-prompt` is declared in `-fields` and
  (2) every column in `-fields` appears in `-prompt` as `{{column}}`. Violating either
  rule raises a parameter-validation error.
- **Prompt template management**: when `-prompt` starts with `@`, the engine loads the
  matching template text from the template registry (the Meta Store). Templates are
  managed through the API (`add-prompt-template`, `delete-prompt-template`) and support
  both global and user-defined resources. The reference format is
  `resource://path/template_name`.
- **AI gateway**: every LLM call is routed through the AI gateway, which provides
  multi-account management, retry and fault tolerance (quota, timeout, KV cache), and
  rate limiting.
- **Performance and cost**: LLM calls are slow (usually seconds per row) and priced in
  proportion to token count. Calling `llm-call` after deduplication and sampling is
  strongly recommended to keep cost and latency under control. In the original
  pipeline, after three-stage deduplication plus cluster sampling, the data sent to the
  LLM is typically only 1% to 10% of the original volume.
- **Idempotency**: the LLM output for the same input is not guaranteed to be identical
  (temperature, sampling, and similar parameters affect it).
- **Out of scope**: multi-step LLM calls (several LLM calls with intermediate
  processing), data-structure transformations (changing the row count), and external
  resource dependencies (databases, file systems). Handle those by composing several
  `llm-call` operators in the pipeline or by implementing a dedicated remote function.

## SQL implementation template

### format=raw (default)

```sql
set session enable_remote_functions = true;
WITH
_llm_raw AS (
    SELECT 
        ai_gen_with_template(
            '{{prompt_text}}',
            ARRAY[{{placeholders}}],
            ARRAY[{{fields}}],
            '{{model}}'
        ) AS __llm_raw
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT 
    coalesce(try(__llm_raw.result), try(__llm_raw.error_msg)) AS {{as}}
    ##otherColumns##
FROM _llm_raw
```

> `{{as}}` has type `varchar`.
> On success it holds the generated text; on failure it holds an error description
> (such as `"timeout"` or `"rate_limit_exceeded"`).

### format=json

```sql
set session enable_remote_functions = true;
WITH
_llm_raw AS (
    SELECT 
        ai_gen_with_template(
            '{{prompt_text}}',
            ARRAY[{{placeholders}}],
            ARRAY[{{fields}}],
            '{{model}}'
        ) AS __llm_raw
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT 
    CASE 
        WHEN __llm_raw.error_msg IS NOT NULL 
        THEN cast(map(
            array['__error'], array[__llm_raw.error_msg]
        ) as json)
        WHEN try(json_parse(__llm_raw.result)) IS NOT NULL 
        THEN json_parse(__llm_raw.result)
        ELSE cast(map(
            array['__raw'], array[coalesce(__llm_raw.result, '')]
        ) as json)
    END AS {{as}}
    ##otherColumns##
FROM _llm_raw
```

> `{{as}}` has type `json` and is **always valid JSON**:
> - LLM success with valid JSON -> returned as is, for example `{"score":4,"reason":"..."}`
> - LLM success with invalid JSON (markdown, free text, and so on) -> `{"__raw":"raw text..."}`
> - LLM call failure -> `{"__error":"timeout"}`
>
> **Engine implementation note**: the final SELECT passes non-derived columns through
> with `##otherColumns##` plus the `{{as}}` derived column, excluding the intermediate
> `__llm_*` columns so they never leak into the output. When deriving columns, the
> `##otherColumns##` macro automatically removes upstream columns whose name collides
> with the current derived column.

### Full SPL to SQL expansion example

Suppose the named template `eval/requirement_understanding_v1.md` contains:

```
You are a professional AI evaluation expert. Evaluate the question-answer pair along
the following dimensions:
- requirement_understanding: does the question summary faithfully express the user's intent (0-5)
- format_compliance: is the output format clean and readable (0-5)

Question: {{question}}
Context: {{input}}
Answer: {{output}}

Output JSON:
{
  "requirement_understanding": {"score": n, "reason": "why"},
  "format_compliance": {"score": n, "reason": "why"}
}
Output pure JSON only.
```

The SPL command:

```
| llm-call -prompt='@eval/requirement_understanding_v1.md' -fields=question,input,output -format=json -model='qwen-turbo-latest' as eval
```

v the engine expands it to:

```sql
set session enable_remote_functions = true;
WITH
_llm_raw AS (
    SELECT
        ai_gen_with_template(
            'sls://builtin_prompt/eval/requirement_understanding_v1.md',
            ARRAY['{{question}}', '{{input}}', '{{output}}'],
            ARRAY["question", "input", "output"],
            'qwen-turbo-latest'
        ) AS __llm_raw
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT
    CASE
        WHEN __llm_raw.error_msg IS NOT NULL
        THEN cast(map(array['__error'], array[__llm_raw.error_msg]) as json)
        WHEN try(json_parse(__llm_raw.result)) IS NOT NULL
        THEN json_parse(__llm_raw.result)
        ELSE cast(map(array['__raw'], array[coalesce(__llm_raw.result, '')]) as json)
    END AS eval
    ##otherColumns##
FROM _llm_raw
```

Downstream result extraction:

```sql
json_extract(eval, '$["requirement_understanding"].score')   -- returns 4
json_extract(eval, '$["format_compliance"].reason')          -- returns "clear structure, clean formatting"
```

## Prompt rendering rules
> **Template path translation**:  
> When `-prompt` starts with `@` it references a named template, which the engine
> translates into an `sls://builtin_prompt/` path:
> | SPL `-prompt` | Translated `template` argument |
> |---------------|-------------------------------|
> | `'@eval/requirement_understanding_v1.md'` | `'sls://builtin_prompt/eval/requirement_understanding_v1.md'` |
> | `'@judge/language_detector.md'` | `'sls://builtin_prompt/judge/language_detector.md'` |
> | `'inline text...'` | Passed through unchanged |
> 
> **Field array generation**:  
> The `ai_gen_with_template` function supports template rendering natively, and the SPL
> translation engine generates the placeholder array and the column-reference array
> from `-fields`:
>
> **Input**:
> - `-prompt='...Question: {{question}} Context: {{input}} Answer: {{output}}...'`
> - `-fields=question,input,output`
>
> **Generated**:
> ```sql
> ai_gen_with_template(
>     '{{prompt_text}}',                                    -- inline text or a named-template reference
>     ARRAY['{{question}}', '{{input}}', '{{output}}'],     -- placeholder array
>     ARRAY["question", "input", "output"],                 -- column-reference array
>     '{{model}}'                                           -- model
> )
> ```
>
> **Validation rules**: before rendering, the engine checks consistency in both
> directions -
> - every `{{column}}` in the prompt must be declared in `-fields`
> - every column in `-fields` must appear in the prompt as `{{column}}`

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{prompt_text}}` | `-prompt` | - | Inline text is passed straight through; a named-template reference (`@<path>`) is translated by the engine into `sls://builtin_prompt/<path>` |
| `{{placeholders}}` | Generated from `-fields` | - | The placeholder-name array. For example `-fields=question,output` -> `'{{question}}', '{{output}}'` |
| `{{fields}}` | Generated from `-fields` | - | The column-reference array (double-quoted identifiers). For example `-fields=question,output` -> `"question", "output"` |
| `{{model}}` | `-model` | System default | The LLM model identifier. When absent, the engine uses the system default model |
| `{{as}}` | `as` | `__llm_result` | Output column name |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `ai_gen_with_template(template, placeholders, columns, model) -> ROW(result varchar, error_msg varchar)` | Call the LLM to generate text (remote function). `template` is inline template text or an `sls://` reference path, `placeholders` is an `ARRAY[varchar]` of placeholder names, `columns` is an `ARRAY[varchar]` of the matching column values, and `model` is the model identifier |
| `json_parse(str) -> json` | Parse a JSON string (built-in SQL). Combined with `try()` to validate the output when `format=json` |

## Edge cases

| Case | Handling |
|------|----------|
| `-prompt` is empty | The engine raises a parameter-validation error |
| `-fields` is empty | The engine raises a parameter-validation error (at least one column is required) |
| A column in `-fields` is absent from the input | The engine raises a parameter-validation error |
| A column in `-fields` has no matching `{{column}}` in the prompt | The engine raises a parameter-validation error (`-fields` declares a redundant column) |
| The `-format` value is outside the enum | The engine raises a parameter-validation error |
| The prompt contains a `{{var}}` that is not in `-fields` | The engine raises a parameter-validation error (the prompt references an undeclared column) |
| The named template (`@name`) does not exist | The engine raises a parameter-validation error noting the template is not registered |
| A column value is NULL | `ai_gen_with_template` renders the NULL into the template, and the LLM may return an incomplete result |
| The input is empty (0 rows) | An empty result set is returned normally |
| The LLM call times out | `format=raw`: `{{as}}` holds the timeout error text; `format=json`: `{{as}}` holds `{"__error":"timeout"}` |
| The LLM returns non-JSON (`format=json`) | `{{as}}` holds `{"__raw":"raw text..."}`, so valid JSON is always guaranteed |
| The LLM returns non-JSON (`format=raw`) | `{{as}}` keeps the raw text without validation |
| Concurrency limiting | Call concurrency is controlled by the AI gateway and the SLS engine |
