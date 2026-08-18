# Pipeline create spec format

Use this JSON format with:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" create --spec pipeline.json
```

Add `--execute` only after dry-run review. Add `--allow-scheduled` only for
Scheduled Pipelines.

## Top-level fields

| Field | Required | Notes |
|---|---:|---|
| `agent_space` | Yes | AgentSpace where the Pipeline is created |
| `region` | Yes | Alibaba Cloud region, for example `cn-hangzhou` |
| `pipeline_name` | Yes | 3-63 lowercase letters, digits, and hyphens |
| `description` | No | Maximum 256 characters |
| `source` | Yes | Only LogStore is accepted |
| `nodes` | Yes | Ordered list of Pipeline nodes |
| `sink` | Yes | Only the dataset sink is accepted |
| `execute_policy` | Yes | `run_once` or `scheduled` |

## Example

```json
{
  "agent_space": "example-space",
  "region": "cn-hangzhou",
  "pipeline_name": "quality-data-pipeline",
  "description": "Build a quality dataset from Agent logs",
  "source": {
    "type": "LogStore",
    "logstore": {
      "project": "example-project",
      "logstore": "example-logstore",
      "query": "serviceName:example-agent"
    }
  },
  "nodes": [
    {
      "id": "select-fields",
      "type": "project",
      "parameters": {
        "question": "user_query",
        "answer": "agent_response"
      }
    }
  ],
  "sink": {
    "type": "dataset",
    "dataset": {
      "agent_space": "example-space",
      "name": "quality_dataset"
    }
  },
  "execute_policy": {
    "mode": "run_once",
    "window": {
      "start": "2026-07-30T09:00:00+08:00",
      "end": "2026-07-30T10:00:00+08:00"
    }
  }
}
```

## Source

Accepted shape:

```json
{
  "type": "LogStore",
  "logstore": {
    "project": "example-project",
    "logstore": "example-logstore",
    "query": "*"
  }
}
```

The wrapper passes this to CLI `--source`.

## Sink

Accepted shape:

```json
{
  "type": "dataset",
  "dataset": {
    "agent_space": "example-space",
    "name": "example-dataset"
  }
}
```

The wrapper converts it to:

```json
{
  "type": "dataset",
  "dataset": {
    "agentSpace": "example-space",
    "dataset": "example-dataset"
  }
}
```

## Execute policy

RunOnce:

```json
{
  "mode": "run_once",
  "window": {
    "start": "2026-07-30T09:00:00+08:00",
    "end": "2026-07-30T10:00:00+08:00"
  }
}
```

Scheduled:

```json
{
  "mode": "scheduled",
  "start": "2026-07-30T09:00:00+08:00",
  "interval": "1h"
}
```

The wrapper converts timezone-bearing ISO-8601 timestamps to Unix seconds.
Unix seconds are also accepted. Millisecond-looking timestamps are rejected.

Creating a RunOnce Pipeline immediately triggers one run over `window`. Do not
follow the create with `run-pipeline` for the same window; that returns
`409 ResourceExist: A run already exists`.

## Supported node types

Shallow validation covers:

`project`, `extend`, `where`, `limit`, `make-instance`, `dedup-exact`,
`dedup-fuzzy`, `dedup-semantic`, `embedding`, `doc-stats`,
`semantic-cluster`, `sample`, `llm-call`, `agentic-call`.

Reject `ai-gen` and use `llm-call` instead. Reject `make-conversation`.

Use `parameters` objects exactly as the AgentLoop Pipeline API expects. Read
`references/pipeline/nodes/OVERVIEW.md` and the selected
`references/pipeline/nodes/<node>.md` files for JSON parameter names. Do not copy
SPL flags such as `-field` or positional syntax from
`references/pipeline/operators/` directly into JSON.

Important Layer 1 JSON details:

- `llm-call.fields` is a comma-separated string, for example
  `"question,output"`, not a JSON array.
- `agentic-call` requires `employee`; optional `skill` defaults to `"sop"`.
- `where` uses `filter`, not `condition`.
- `sample` requires exactly one of `ratio` or `n`.
- A dot-notation subfield must not be the value of a `project` mapping. See
  "Referencing nested source fields" below.

## Referencing nested source fields

A `project` value is a raw column name, not an expression. Pointing it at a
dot-notation subfield fails:

```json
{ "id": "pick", "type": "project", "parameters": { "input": "eval_info.input" } }
```

This returns `SPLSyntaxError: bad extend expression`, with or without inner
quoting (`"eval_info.input"` and `"\"eval_info.input\""` both fail). The reason is
the translation rule in `references/pipeline/nodes/project.md`: a renaming
mapping `"a":"b"` becomes an assignment on `b`, so the dot name lands in an
expression position where it does not parse.

Verified pattern: project the raw JSON column, then extract in a later `extend`:

```json
{
  "nodes": [
    { "id": "pick", "type": "project", "parameters": { "eval_info": "eval_info" } },
    {
      "id": "unpack",
      "type": "extend",
      "parameters": {
        "input": "json_extract_scalar(eval_info, '$.input')",
        "output": "json_extract_scalar(eval_info, '$.output')"
      }
    }
  ]
}
```

A quoted dot-notation column does work inside a `where` `filter` and inside an
`extend` expression, as the OT-AI example below shows with
`"attributes.gen_ai.span.kind"`. That works because the trace LogStore exposes
those flattened names as real columns. For any other LogStore, do not assume a
dot name is a real column: confirm it against sampled source rows first, and
otherwise use the `json_extract_scalar` path above. This is the most common trap
when cleaning a non-trace LogStore.

## Example: OT-AI trace QA extraction

A runnable shape aligned with the live `eval-test` pipeline. It cleans `gen_ai.*`
trace spans into a question/answer Dataset. Expressions are trimmed to show the
node chain; see `references/pipeline/trace/ot-ai-trace-recipe.md` for the full SPL
recipes (per-span-kind CASE WHEN, nested `json_extract_scalar`, multi-source
fallback).

```json
{
  "agent_space": "eval-test",
  "region": "cn-beijing",
  "pipeline_name": "ot-ai-qa-extract",
  "description": "Extract OT-AI trace QA pairs",
  "source": {
    "type": "LogStore",
    "logstore": {
      "project": "proj-xtrace-<id>-cn-beijing",
      "logstore": "logstore-tracing",
      "query": "*"
    }
  },
  "nodes": [
    {
      "id": "kind_filter",
      "type": "where",
      "parameters": {
        "filter": "\"attributes.gen_ai.span.kind\" IS NOT NULL AND \"attributes.gen_ai.span.kind\" != '' AND \"attributes.gen_ai.span.kind\" IN ('ENTRY', 'LLM', 'TOOL', 'AGENT')"
      }
    },
    {
      "id": "preprocess",
      "type": "extend",
      "parameters": {
        "llm_answer_text": "CASE WHEN \"attributes.gen_ai.span.kind\" = 'LLM' THEN json_extract_scalar(json_extract_scalar(attributes, '$[\"gen_ai.output.messages\"]'), '$[0].parts[0].content') ELSE CAST(NULL AS VARCHAR) END",
        "llm_input_tokens": "CASE WHEN \"attributes.gen_ai.span.kind\" = 'LLM' THEN CAST(\"attributes.gen_ai.usage.input_tokens\" AS BIGINT) ELSE CAST(NULL AS BIGINT) END",
        "has_tool_span": "CASE WHEN \"attributes.gen_ai.span.kind\" = 'TOOL' THEN CAST(1 AS BIGINT) ELSE CAST(0 AS BIGINT) END"
      }
    },
    {
      "id": "assemble",
      "type": "make-instance",
      "parameters": {
        "by": "traceid",
        "llm_answer": "last(llm_answer_text)",
        "span_kind_list": "array(\"attributes.gen_ai.span.kind\")",
        "total_input_tokens": "sum(llm_input_tokens)",
        "tool_call_count": "sum(has_tool_span)",
        "start_time": "first(__time__)"
      }
    },
    {
      "id": "derive",
      "type": "extend",
      "parameters": {
        "answer": "llm_answer",
        "has_tool_call": "IF(tool_call_count > 0, 'true', 'false')"
      }
    },
    {
      "id": "filter_valid",
      "type": "where",
      "parameters": {
        "filter": "answer IS NOT NULL AND answer != ''"
      }
    },
    {
      "id": "output",
      "type": "project",
      "parameters": {
        "answer": "answer",
        "input_tokens": "total_input_tokens",
        "has_tool_call": "has_tool_call",
        "timestamp": "start_time",
        "trace_id": "traceid"
      }
    }
  ],
  "sink": {
    "type": "dataset",
    "dataset": {
      "agent_space": "eval-test",
      "name": "qa-dataset"
    }
  },
  "execute_policy": {
    "mode": "scheduled",
    "start": "2026-07-23T10:00:00+08:00",
    "interval": "1h"
  }
}
```

Note the OT-AI specifics: `where` uses `filter`; each `extend` column keys off
`attributes.gen_ai.span.kind` with CASE WHEN; nested content is read with
double `json_extract_scalar`; time ordering comes from `make-instance`
aggregators such as `first(..., __time__)`, not a `sort` node.
