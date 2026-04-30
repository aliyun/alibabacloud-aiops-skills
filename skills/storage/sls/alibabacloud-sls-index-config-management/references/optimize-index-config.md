# Optimize Index Configuration

Adjust an existing SLS index config for a query, SQL statement, write throughput, or storage cost.

## Process

1. Run `get-index` and save the current index config as a backup.
2. Analyze the user's requirement, the current index config, and any relevant context such as
   query statements, SQL statements, sample fields, cost concerns, or write-throughput concerns.
3. Generate the complete optimized `line` / `keys` config.
4. Produce an optimization report explaining what changed and why.
5. Provide the `update-index` CLI command that submits the complete optimized config.

## Principles

- **Missing fields in query**: if a query references a field that is not in `keys`, add that field
  to the field index.
- **Missing SQL fields**: if SQL uses a field in `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, or an
  aggregation, the field index needs `doc_value: true`.
- **No-token fields**: for identifier-like fields that do not need tokenization, such as
  `request_id`, `trace_id`, `span_id`, `user_id`, or exact-match IDs, remove unnecessary token
  delimiters. Keep tokenization minimal for exact-match fields.
- **Chinese indexing**: prefer `chn: false`. Enable Chinese tokenization only when the user
  explicitly needs Chinese keyword search on that field.
- **Long unstructured text**: for long, unstructured fields that are unlikely to be used in SQL
  analysis, such as `content`, `message`, or `raw_payload`, set `doc_value: false` to reduce
  storage overhead.
- **Deep JSON fields**: control JSON index depth carefully. For very deep JSON fields, avoid
  indexing excessive depth; generally do not exceed 5 levels unless the user explicitly needs it.
- **Integer fields**: if all observed values for a field are integers, prefer `long` over `text`.

## Guardrails

- Keep the user's required query or SQL working; do not remove needed indexes to save cost unless
  the user accepts that tradeoff.
- `update-index` replaces the full config. Submit the complete final `line` / `keys` config, not
  only the optimized field.
- Explain any behavior change, especially removing tokenization, disabling `doc_value`, reducing
  JSON depth, or turning off Chinese tokenization.

## Output

- Optimized `line` / `keys` JSON files.
- Brief optimization report: only list meaningful changes and why.
- Complete `aliyun sls update-index ...` command.
