# doc-stats (document statistics)

> Compute document-level statistics for a text field and emit a normalized
> statistics JSON.

## Function

The `doc-stats` node computes several document-level metrics (character count,
word count, line count, and so on) for the given text field and emits them
together as one JSON column.

Each record is computed independently and the row count does not change.

**Use cases**:

- Data-quality checks: filter out records whose text is too short or too long
- Pipeline run statistics: understand the text-length distribution at each stage
- Dataset metadata: attach normalized text statistics to every record

## Node configuration

```json
{
  "id": "node_1",
  "type": "doc-stats",
  "parameters": {
    "field": "<field-name>",
    "as": "<output-column-name>",
    "output": "<output-column-list>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `field` | String | **Yes** | - | The text field to measure |
| `as` | String | No | `"__doc_stats"` | Name of the statistics output column |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- The field named by `field` must be present

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns named by `output` | - | Pass-through | `*` keeps every raw input column |
| `{as}` | json | Added | The document-statistics JSON |

**Metrics (structure inside the JSON)**:

| Key | Type | Description |
|-----|------|-------------|
| `doc_len_char` | bigint | Character count of the text |
| `doc_len_words` | bigint | Word count of the text (split on spaces) |
| `line_counts` | bigint | Line count of the text |

> **Example output**: `{"doc_len_char": 42, "doc_len_words": 8, "line_counts": 1}`

**Row-count change**:

M -> N (M = N) - a 1:1 transformation that neither adds nor drops rows.

## Effect preview

**Before** (3 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is a branch of AI |
| How do I learn Python? Any getting-started resources? | Getting started | Start with the official tutorial then build a project |
| AI | In brief | Artificial intelligence |

**After** (3 rows) - `field = "question"`:

| question | input | output | __doc_stats |
|----------|-------|--------|-------------|
| What is machine learning? | Please explain | Machine learning is... | `{"doc_len_char":25,"doc_len_words":4,"line_counts":1}` |
| How do I learn Python? Any... | Getting started | Start with... | `{"doc_len_char":52,"doc_len_words":8,"line_counts":1}` |
| AI | In brief | Artificial intelligence | `{"doc_len_char":2,"doc_len_words":1,"line_counts":1}` |

> The row count is unchanged (3 -> 3) and every row gains a statistics JSON column.
> Combine it with the `where` node to filter text that is too short or too long by
> character count.

## Examples

### Example 1: basic document statistics

```json
{
  "id": "n5",
  "type": "doc-stats",
  "parameters": {
    "field": "question"
  }
}
```

Measures the `question` field and writes the result to `__doc_stats`.

### Example 2: custom output column name

```json
{
  "id": "n5",
  "type": "doc-stats",
  "parameters": {
    "field": "question",
    "as": "question_stats"
  }
}
```

### Example 3: combined with filtering

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "output": "c" } },
    { "id": "n2", "type": "doc-stats", "parameters": { "field": "question" } },
    { "id": "n3", "type": "where", "parameters": { "filter": "json_extract_scalar(__doc_stats, '$.doc_len_char') > '10'" } }
  ]
}
```

Compute the statistics, then drop text that is too short.

## Notes

**Recommended usage**:
- Combine it with the `where` node for data-quality filtering: measure first, then
  filter text that is too short or too long
- It can also sit at the end of the pipeline to attach normalized text metadata to
  the Dataset output
- Measuring the output text after LLM processing helps monitor quality

**Best practices**:
- Use `json_extract_scalar` to pull a specific metric, for example
  `json_extract_scalar(__doc_stats, '$.doc_len_char')`
- Use the `as` parameter to rename the output column (default `__doc_stats`) so
  several fields can be measured separately
- The operator needs no remote function and is extremely cheap, so it is safe to
  place anywhere in the pipeline

**Edge cases**:

| Case | Behavior |
|------|----------|
| `field` is missing | Validation fails |
| The `field` value is NULL | The statistics are `{"doc_len_char": 0, "doc_len_words": 1, "line_counts": 1}` |
| The text is an empty string | Handled like NULL |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `where` | After the statistics are computed, `where` can filter on them |
| `llm-call` | Measure the quality metrics of the output text after AI processing |

## Implementation note

> `doc-stats` is not packaged as a standalone SPL operator. The API translation
> emits an equivalent `extend` expression directly.

**API to SPL translation example**:

```json
{ "field": "question", "as": "question_stats" }
```

translates to:

```
extend question_stats=cast(map(array['doc_len_char','doc_len_words','line_counts'],array[cast(length(coalesce(question,'')) as bigint),cast(cardinality(split(coalesce(question,''),' ')) as bigint),cast(cardinality(split(coalesce(question,''),chr(10))) as bigint)]) as json)
```
