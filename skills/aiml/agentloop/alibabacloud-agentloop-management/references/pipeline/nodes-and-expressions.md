# Pipeline Nodes and Expressions

## Contents

- [Node Inventory](#node-inventory)
- [Raw-Preserving Question Extraction](#raw-preserving-question-extraction)
- [Node Ordering and Cost](#node-ordering-and-cost)
- [Projection and Privacy Warnings](#projection-and-privacy-warnings)

## Node Inventory

The public Pipeline guide currently documents 13 sequential node types:

| Node | Purpose | Placement guidance |
| --- | --- | --- |
| `project` | Select and rename source fields; declare the working schema. | Usually first. Undeclared fields do not survive the projection. |
| `extend` | Calculate a new field or overwrite an existing field with an expression. | After required source fields exist. |
| `where` | Keep rows matching a filter expression. | Filter invalid/empty rows before expensive nodes. |
| `make-instance` | Group discrete events into one row-level sample. | Before row-level deduplication or evaluation. |
| `dedup-exact` | Remove exact text duplicates. | Before fuzzy or semantic deduplication. |
| `dedup-fuzzy` | Remove near-duplicate text by edit distance. | After exact deduplication. |
| `dedup-semantic` | Remove semantic duplicates and produce a reusable vector column. | After cheaper deduplication. |
| `embedding` | Generate an embedding extension column. | Before a node that needs a vector if no upstream node produced one. |
| `doc-stats` | Add character, word, or line statistics. | Usually late in the flow. |
| `semantic-cluster` | Assign a semantic cluster ID from embeddings. | Before grouped sampling. |
| `sample` | Sample by ratio or count, optionally by group. | Before AI calls to control volume and cost. |
| `llm-call` | Render a prompt, invoke an LLM, and parse output. | After filtering/deduplication/sampling. |
| `agentic-call` | Invoke a digital employee/agent for multi-step processing. | After volume reduction; account for cost and latency. |

Use current CLI help and the official node page for any node parameter not shown below. Do not invent parameter names from an internal implementation or another product.

## Raw-Preserving Question Extraction

### Contract

For a trace record where `input` contains system wrappers plus the real user question, preserve:

```text
input       raw source input
output      raw source output
question    derived clean user question
trace_id    stable source lineage
session_id  optional conversation lineage
service_name and start_time where available
```

`question` is a derived convenience field; it is not a substitute for raw `input` or `output`.

### Minimal node chain

Confirm the source's actual case-sensitive field names before using this example:

```json
{
  "nodes": [
    {
      "id": "project-source-contract",
      "type": "project",
      "parameters": {
        "input": "input",
        "output": "output",
        "question": "input",
        "trace_id": "trace_id",
        "session_id": "session_id",
        "service_name": "service_name",
        "start_time": "start_time"
      }
    },
    {
      "id": "extract-real-question",
      "type": "extend",
      "parameters": {
        "question": "trim(if(regexp_like(question, '(?s)<userQuery>.*</userQuery>'), regexp_extract(question, '(?s)<userQuery>(.*?)</userQuery>', 1), regexp_replace(question, '(?s)^.*</(system_reminder|memory|game_cases)>', '')))"
      }
    },
    {
      "id": "drop-empty-question",
      "type": "where",
      "parameters": {
        "filter": "length(trim(question)) > 0"
      }
    }
  ]
}
```

Why the order matters:

1. `project` explicitly retains raw evidence and seeds `question` from `input`.
2. `extend` prefers a structured `<userQuery>...</userQuery>` value.
3. If no structured tag exists, the fallback removes the prefix through the last recognized wrapper closing tag.
4. If no wrapper exists, `regexp_replace` leaves a normal raw question unchanged.
5. `where` removes only rows whose derived question is empty after trimming.

### Required preview cases

Use synthetic values when raw traces may be sensitive:

| Input shape | Expected `question` | Raw fields |
| --- | --- | --- |
| `<system_reminder>...</system_reminder><game_cases>...</game_cases>\n\nWhere am I?` | `Where am I?` | `input` and `output` remain present and unchanged. |
| `prefix <userQuery>How do I build a tower-defense level?</userQuery> suffix` | `How do I build a tower-defense level?` | `input` and `output` remain present and unchanged. |
| `Make the sky feel eerie.` | `Make the sky feel eerie.` | `input` and `output` remain present and unchanged. |
| Wrappers only, no user text | filtered by `where` | Source exclusion is counted and explained. |

If wrapper formats can be nested, reordered, malformed, or contain multiple user messages, do not assume this expression is complete. Add cases, preview them, version the transform, and preserve raw input for later correction.

## Node Ordering and Cost

Prefer:

```text
project/extend/where
-> make-instance when events must be assembled
-> exact/fuzzy/semantic deduplication
-> semantic clustering and sampling
-> llm-call or agentic-call
-> statistics
```

This order is guidance, not a substitute for the actual data dependency graph. Every downstream field must be emitted by an earlier node. Put paid or high-latency AI nodes after deterministic volume reduction whenever the business goal permits it.

## Projection and Privacy Warnings

- `project` is an allow-list. A field omitted there can be silently unavailable to all later nodes and the sink.
- Preview the exact expected field set, not merely the derived `question` value.
- A real-data `--cli-dry-run` or verbose preview may expose raw conversations in terminal history. Validate serialization with synthetic content, then run structural checks that do not echo raw values.
- Perform required redaction before embedding or writing sensitive content. Dataset rows cannot be assumed to support per-row repair or deletion later.

Official node reference: <https://help.aliyun.com/zh/cms/cloudmonitor-2-0/overview-of-the-pipeline-node/>
