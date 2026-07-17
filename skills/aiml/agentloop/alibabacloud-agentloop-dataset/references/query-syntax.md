# Dataset Query Syntax

All query modes use `execute-query` with `--type SQL`. The service detects SQL, SearchExpr, or SearchExpr piped into SQL.

## Backend-Enforced Limits

| Input or operation | Constraint |
| --- | --- |
| Request body | Default cap: 100 MiB. |
| Query text | Default cap: 10 MiB. |
| SELECT without a limit | Defaults to 1,000 rows. |
| SQL `LIMIT` | Non-negative integer, maximum 100,000 by default; `LIMIT ALL` is unsupported. |
| `--offset` / `--length` | Non-negative; `length` has the same configured maximum as SQL `LIMIT`, 100,000 by default. |
| `--from` / `--to` | Non-negative Unix seconds; when both are non-zero, `from < to`; `to` remains exclusive. |
| `--max-output-length` | Non-negative; `0` or omission returns full values. |
| SearchExpr `similarity()` | Threshold in `[0, 1]`, using `<`, `<=`, `>`, or `>=`. |
| SearchExpr `topk()` | Integer from 1 through 100,000, using `<` or `<=`. |

Treat the request-body, query-text, default SELECT, and maximum SELECT values as service defaults that deployments can configure downward or upward. Use the values reported by an API error when they differ.

## Response Shape

Successful queries return:

```json
{
  "requestId": "<request_id>",
  "meta": {
    "affectedRows": 0,
    "elapsedMillisecond": 12,
    "progress": "Complete",
    "count": 2
  },
  "columns": ["id", "question", "score"],
  "columnTypes": ["text", "text", "double"],
  "rows": [
    ["<uuid_1>", "How?", 0.95],
    ["<uuid_2>", "Why?", 0.91]
  ]
}
```

Interpret `rows[i][j]` with `columns[j]`. Do not expect a `data` object array.

## SQL SELECT

```bash
aliyun agentloop execute-query \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --type SQL \
  --query "SELECT id, __time__, question, score FROM <dataset_name> WHERE score >= 0.8 ORDER BY score DESC LIMIT 20"
```

Use only the target Dataset. Prefer explicit columns and LIMIT. `SELECT *` expands to `id`, `__time__`, and public schema fields without exposing physical embedding columns.

## Result and Time Windows

Use request parameters rather than rewriting a SELECT when the user wants an external result window:

```bash
aliyun agentloop execute-query \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --type SQL \
  --query "SELECT id, question FROM <dataset_name> ORDER BY __time__ DESC" \
  --from <inclusive_unix_seconds> \
  --to <exclusive_unix_seconds> \
  --offset 0 \
  --length 20 \
  --max-output-length 4096
```

- `from` and `to` filter the `__time__` system field. Zero or omission means no corresponding bound; negative values are rejected, and non-zero bounds must satisfy `from < to`.
- `offset` and `length` apply only to top-level SELECT results and must be non-negative. `length` cannot exceed the configured SELECT maximum, which defaults to 100,000.
- `max-output-length` truncates long text/JSON output values and reports truncation metadata. Omit it or pass `0` for full values.
- `--biz-version <version>` reads an existing immutable Dataset snapshot and serializes to the request-body field `version`. Do not use the global `--version` flag for a Dataset snapshot. Omit `--biz-version` for current data. The AgentLoop CLI 0.7.1 does not expose snapshot create/list/delete commands.

## SearchExpr

SearchExpr supports field comparisons, boolean logic, parentheses, and field-value sugar:

```bash
aliyun agentloop execute-query \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --type SQL \
  --query "question:error AND score >= 0.8"
```

Supported forms include:

- Comparisons: `=`, `!=`, `>`, `>=`, `<`, `<=`
- Boolean logic: `AND`, `OR`, `NOT`, and parentheses
- Exact value: `field:value`, `field:'value'`, or `field:"value"`
- Existence: `field:*`
- Prefix: `field:prefix*`

Do not use fieldless terms, `IN`, `BETWEEN`, `LIKE`, `IS NULL`, arbitrary functions, subqueries, or a JSON filter DSL on the SearchExpr side.

## Semantic SearchExpr

The target field must have `embedding` enabled. Keep `similarity()` thresholds in `[0, 1]`. Keep `topk()` thresholds integral and between 1 and 100,000.

```bash
# Distance threshold: smaller values are closer.
aliyun agentloop execute-query \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --type SQL \
  --query "similarity(question, '<semantic_query>') < 0.3"

# Top-K semantic retrieval.
aliyun agentloop execute-query \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --type SQL \
  --query "topk(question, '<semantic_query>') <= 10"
```

Combine `similarity()` or `topk()` with other SearchExpr conditions using `AND`, not `OR`.

## Search Pipe SQL

Place SearchExpr on the left of a top-level pipe and a SELECT on the right:

```bash
aliyun agentloop execute-query \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --type SQL \
  --query "question:error AND score >= 0.8 | SELECT id, question, score FROM <dataset_name> ORDER BY score DESC LIMIT 10"
```

The SQL side of a pipe must be SELECT.

## SQL Semantic Distance

Use an explicit distance type with current Dataset execution:

```bash
aliyun agentloop execute-query \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --type SQL \
  --query "SELECT id, question, semantic_distance(question, '<semantic_query>', 'l2') AS distance FROM <dataset_name> ORDER BY distance ASC LIMIT 10"
```

Accepted distance families are:

- `l2`, `euclidean`, or `distance`
- `cosine`, `cos`, or `similarity`
- `ip`, `dot`, or `inner_product`

Use `l2` unless the user explicitly chooses another supported distance meaning.

## Read-only SQL Scope

This Skill sends only SELECT or SearchExpr queries through `execute-query`. The public request supplies raw query text and `ExecuteQuery` authorization is not statement-level read-only, so do not rely on RAM or the CLI to block a mutation.

- No JOIN or cross-Dataset access.
- No UNION, INTERSECT, or EXCEPT.
- Use explicit columns and a bounded LIMIT.
- Build query text only from documented read-only patterns and confirmed Dataset schema fields. Do not accept a user-supplied SQL template or add user-provided text to the statement.
