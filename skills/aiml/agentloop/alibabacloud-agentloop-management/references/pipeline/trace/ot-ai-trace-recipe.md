# OT-AI Trace Pipeline Recipe

A dedicated recipe and methodology for cleaning OpenTelemetry AI (`gen_ai.*`)
traces into a structured Dataset.

This file only adds what is specific to OT-AI trace sources. **General node
composition, orchestration principles, and time-ordered aggregation are not
repeated here; read the existing references instead**:

- Per-operator SPL syntax: `references/pipeline/operators/<operator>.md`
- End-to-end composition scenarios, the full data-flow picture, and
  orchestration principles (schema first, assemble early, reduce before enrich,
  coarse to fine): `references/pipeline/operators/OVERVIEW.md`
- Time-ordered aggregation with `join(col, sep, order_by)`:
  `references/pipeline/operators/make-instance.md`
- OT-AI field vocabulary (span kinds, `gen_ai.*` attributes):
  `references/pipeline/trace/ot-ai-collection-spec.md`

Payload field casing is governed by
`references/pipeline/pipeline-cli-map.md` and
`references/pipeline/spec-format.md` (for example, the `where` node parameter is
`filter`, not `condition`).

---

## 1. Methodology: from an unfamiliar trace to a Dataset (CLI only, no scripts)

When facing an unfamiliar trace source, derive the target schema in four steps.
Sample with the aliyun CLI throughout; do not introduce SLR or the SLS SDK.

### Step 1: Sample the raw traces

Credential mode: **an existing aliyun CLI profile** (never SLR). Prefer the
installed `alibabacloud-sls-cli-guidance` skill to query SLS; without that skill,
use the native command:

```bash
aliyun sls GetLogs --project <sls-project> --logstore <logstore> \
  --from <unix-seconds> --to <unix-seconds> --query '*' --line 50
```

20-50 rows are enough. The goal is a sample that covers several span kinds.

### Step 2: Topology analysis (the agent reads the sample directly)

Do not write a script; induce the structure straight from the sample:

- The value distribution of `attributes.gen_ai.span.kind` (commonly `ENTRY`,
  `LLM`, `TOOL`, `AGENT`; the full vocabulary is in
  `references/pipeline/trace/ot-ai-collection-spec.md`)
- Span count per trace, the parent/child chain (`parentSpanId` → `spanId`), and
  the service name `servicename`
- The time relationship between multiple LLM calls inside one trace (this decides
  whether time-ordered aggregation is needed)

### Step 3: Attribute probing

Group by span kind, then enumerate the key attributes from the sample and record
their quality:

- Occurrence rate, value type, and a value example (first 200 characters)
- Key business fields: `gen_ai.input.messages`, `gen_ai.output.messages`,
  `gen_ai.request.model`, `gen_ai.usage.*_tokens`, `duration`
- Data quality: NULL rate, **SLS truncation** (values ending in `...`), and
  nested JSON depth

### Step 4: Derive the target schema mapping table

Produce a field mapping table and use it as the basis for node design:

| Target field | Type | Semantics | Source span kind | Extraction logic (SPL outline) |
|---|---|---|---|---|
| question | varchar | User question | ENTRY/AGENT/LLM | Multi-source fallback, first non-empty |
| answer | varchar | Final answer | ENTRY/AGENT/LLM | Same, by priority |
| model | varchar | Model name | LLM | `gen_ai.request.model` or spanname |
| total_tokens | bigint | Token total | LLM | sum(input)+sum(output) |
| trace_id | varchar | Correlation | all | traceid |

Confirm the derived table with the user before moving on to the node recipes
below. (Optional: write the table plus the topology findings into a lightweight
CONTEXT note so a later iteration can resume from it; this is not a mandatory
step.)

---

## 2. Standard node skeleton

The typical chain from OT-AI trace to a QA/sample Dataset (identical to the live
`eval-test` pipeline):

```
where(kind_filter) → extend(preprocess) → make-instance(assemble)
  → where(trace_match) → extend(derive) → where(filter_valid) → project(output)
```

Key point: **do not use a `sort` node for ordering** (this skill does not support
sort). Preserve order inside `make-instance` with `join(col, sep, startTime)` or
`first(col, startTime)` instead — see
`references/pipeline/operators/make-instance.md`.

---

## 3. OT-AI specific SPL recipes

The three patterns below are specific to OT-AI traces and are not covered by the
general references.

### Recipe A: per-span-kind CASE WHEN preprocess

One log row is one span, and different kinds carry different fields. Use `extend`
to extract the matching field for each kind and set NULL for the other kinds, so
a later aggregation by traceid can collapse them:

```json
{
  "id": "preprocess",
  "type": "extend",
  "parameters": {
    "llm_model": "CASE WHEN \"attributes.gen_ai.span.kind\" = 'LLM' THEN CASE WHEN \"attributes.gen_ai.request.model\" IS NOT NULL AND \"attributes.gen_ai.request.model\" != '' THEN \"attributes.gen_ai.request.model\" ELSE spanname END ELSE CAST(NULL AS VARCHAR) END",
    "llm_input_tokens": "CASE WHEN \"attributes.gen_ai.span.kind\" = 'LLM' THEN CAST(\"attributes.gen_ai.usage.input_tokens\" AS BIGINT) ELSE CAST(NULL AS BIGINT) END",
    "has_tool_span": "CASE WHEN \"attributes.gen_ai.span.kind\" = 'TOOL' THEN CAST(1 AS BIGINT) ELSE CAST(0 AS BIGINT) END"
  }
}
```

At aggregation time: `model=first(llm_model)`,
`total_input_tokens=sum(llm_input_tokens)`, `tool_call_count=sum(has_tool_span)`.

### Recipe B: drill into nested JSON with `json_extract_scalar`

`gen_ai.input.messages` and `gen_ai.output.messages` are nested JSON strings and
must be parsed level by level. To read the text of the first output message:

```
json_extract_scalar(json_extract_scalar(attributes, '$["gen_ai.output.messages"]'), '$[0].parts[0].content')
```

The outer `json_extract_scalar(attributes, '$["gen_ai.output.messages"]')` first
pulls the whole messages JSON out as a string; the inner call then locates
`$[0].parts[0].content`. For deeper structures (such as a tool_calls array inside
messages), keep stacking `json_extract_scalar(..., '$[n].xxx')`.

### Recipe C: multi-source fallback

The same business meaning (such as the user question) can appear on different
spans (ENTRY, AGENT, LLM) or at different message indexes. Fall back by
priority:

```
CASE
  WHEN cardinality(filter(span_kind_list, x -> x = 'ENTRY')) > 0 AND entry_question IS NOT NULL AND entry_question != '' THEN entry_question
  WHEN cardinality(filter(span_kind_list, x -> x = 'AGENT')) > 0 AND agent_question IS NOT NULL AND agent_question != '' THEN agent_question
  ELSE llm_question
END
```

Here `entry_question`, `agent_question`, and `llm_question` are extracted by
recipe A under their own span kinds, and
`span_kind_list=array("attributes.gen_ai.span.kind")` is produced by the
make-instance aggregation. When the message index is uncertain, use a nested
CASE WHEN inside recipe A to try `$[4]` → `$[3]` → ... → `$[0]` for
`role='user'`.

---

## 4. Verification

Verify with the CLI, not with scripts of your own. Once the spec is written, first
run the wrapper `create` without `--execute` to pass dry-run casing validation. To
see the real cleaning result, run the wrapper `preview` with a bounded time window
and `--execute`; it reuses the same spec file and reports whether the returned
columns cover the declared output columns. Watch out for AI-node cost. The
procedure is in `references/pipeline/pipeline.md`. A complete runnable example is
the OT-AI QA extraction example in `references/pipeline/spec-format.md`.
