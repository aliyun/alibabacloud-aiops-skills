# doc-stats (document statistics)

> Compute document-level statistics for a text field and emit a normalized
> statistics JSON column.

## Function

Computes several document-level metrics (character count, word count, line count,
and so on) for the given text field and emits them together as one JSON column. It
provides normalized text measurements for data-quality monitoring, filtering, and
Pipeline run statistics.

Each record is measured independently, so the input and output row counts match (a
1:1 transformation).

**Use cases**:

- Data-quality checks: filter out records whose text is too short or too long
- Pipeline run statistics: understand the text-length distribution at each stage
- Dataset metadata: attach normalized text statistics to every record

## Syntax

```
| doc-stats -field=<column> [as <name>]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | The text field to measure |
| `as` | Field | No | `__doc_stats` | Name of the statistics output column (an instruction primitive, without the `-` prefix) |

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- The field named by `-field` must be present

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Input | Every upstream column passes through |
| `{{as}}` | json | Derived | The document-statistics JSON containing the metrics defined below |

**Metrics (structure inside the JSON)**:

| Key | Type | Description |
|-----|------|-------------|
| `doc_len_char` | bigint | Character count of the text |
| `doc_len_words` | bigint | Word count of the text (split on spaces) |
| `line_counts` | bigint | Line count of the text (split on newlines) |

> **Example output**: `{"doc_len_char": 42, "doc_len_words": 8, "line_counts": 1}`

**Input-to-output relationship**:

M:N (M = N) — a 1:1 transformation; each row is measured independently and no rows
are added or dropped.

## Effect preview

**Before** (3 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is a branch of AI |
| How do I learn Python? Any getting-started resources? | Getting started | Start with the official tutorial then build a project |
| AI | In brief | Artificial intelligence |

**After** (3 rows) — `| doc-stats -field=question`:

| question | input | output | __doc_stats |
|----------|-------|--------|-------------|
| What is machine learning? | Please explain | Machine learning is… | `{"doc_len_char":25,"doc_len_words":4,"line_counts":1}` |
| How do I learn Python? Any getting-started resources? | Getting started | Start with… | `{"doc_len_char":52,"doc_len_words":8,"line_counts":1}` |
| AI | In brief | Artificial intelligence | `{"doc_len_char":2,"doc_len_words":1,"line_counts":1}` |

> The row count is unchanged (3 → 3) and every row gains a `__doc_stats` JSON
> column. Combine it with
> `where json_extract_scalar(__doc_stats, '$.doc_len_char') > 5` to filter text that
> is too short.

## Examples

### Example 1: basic document statistics

```
* | project question,input,output
  | doc-stats -field=question
```

Measures the `question` field and writes the result to `__doc_stats`.

### Example 2: custom output column name

```
* | project question,input,output
  | doc-stats -field=question as question_stats
```

### Example 3: pipeline composition (dedup → sample → AI → statistics)

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | dedup-semantic -field=question -threshold='0.1'
  | semantic-cluster -field=__dedup_emb -n=100
  | sample -n=1 by __cluster_id
  | llm-call -prompt='@eval/prompt.md' -fields=question,output as eval
  | doc-stats -field=question
```

Appends document statistics at the end of the full Pipeline as Dataset metadata
fields.

### Example 4: combined with filtering

```
* | project question,input,output
  | doc-stats -field=question
  | where json_extract_scalar(__doc_stats, '$.doc_len_char') > 10
```

Compute the statistics, then drop text that is too short.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Design position**: this operator is a standardized convenience wrapper,
  equivalent to computing the three statistics columns by hand with `extend` and then
  assembling them into JSON with `map`. It provides uniform metric naming and JSON
  output so users do not have to hand-write the SQL function calls.
- **JSON output format**: the metrics are aggregated into a single JSON column
  rather than split into several independent derived columns. The benefits are
  (1) no column explosion, since one JSON column carries every metric; (2) the shape
  matches the `stats` field of the Dataset model; (3) extensibility — a new metric
  only adds a key to the JSON without changing the output column structure.
- **Extensibility**: more metrics can be added later (distinct word count, average
  word length, special-character ratio, language detection, and so on) with no
  impact on the user-facing interface, only a new key inside the JSON.
- **NULL handling**: `coalesce(field, '')` is the fallback, so a NULL field value
  yields `{doc_len_char: 0, doc_len_words: 1, line_counts: 1}` (splitting an empty
  string produces one empty element).
- **No remote-function dependency**: every computation uses built-in SQL functions
  (`length`, `split`, `cardinality`), so `enable_remote_functions` is not required.

## SQL implementation template

### Standard mode

```sql
WITH
_doc_stats AS (
    SELECT 
        cast(map(
            array['doc_len_char', 'doc_len_words', 'line_counts'],
            array[
                cast(length(coalesce({{field}}, '')) as bigint),
                cast(cardinality(split(coalesce({{field}}, ''), ' ')) as bigint),
                cast(cardinality(split(coalesce({{field}}, ''), chr(10))) as bigint)
            ]
        ) as json) AS {{as}}
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _doc_stats
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{field}}` | `-field` | - | The text field name |
| `{{as}}` | `as` | `__doc_stats` | Output column name |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `length(text) → bigint` | Character count of a string (built-in SQL function) |
| `split(text, delimiter) → array(varchar)` | Split a string on a delimiter (built-in SQL function) |
| `cardinality(array) → bigint` | Number of elements in an array (built-in SQL function) |
| `chr(code) → varchar` | The character for a Unicode code point; `chr(10)` is a newline (built-in SQL function) |

## Edge cases

| Case | Handling |
|------|----------|
| The `-field` column does not exist | The engine raises a parameter-validation error |
| The `-field` value is NULL | `coalesce(field, '')` is the fallback, giving `{doc_len_char: 0, doc_len_words: 1, line_counts: 1}` |
| The input is empty (0 rows) | An empty result set is returned normally |
| The text is an empty string | `doc_len_char=0`, `doc_len_words=1` (splitting an empty string produces one empty element), `line_counts=1` |
| The text contains non-UTF-8 characters | `length` counts characters; the behavior depends on how the SQL engine handles the character set |
