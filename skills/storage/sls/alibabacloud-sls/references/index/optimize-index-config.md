# Optimize Index Configuration

Index optimization usually aims to:

- **Reduce indexing traffic to lower costs.**
- **Improve write capacity**, especially for Logstores with very high write traffic,
  shard counts near the limit, and per-shard write throughput already near capacity.

[Index operations](manage-index-config.md#changes) describe how to apply changes.
The query workload and sample fields help identify which settings can be reduced
while keeping the required queries usable.

For online verification, use the [query example](../query/query-execution.md#logstore)
and [result precision](../query/query-execution.md#result-precision) with the user's statement
over data covered by the [effective index settings](index-configuration.md#configuration-changes-and-historical-data).

## Principles

- **Missing query or SQL fields**: compare [field coverage](index-configuration.md#field-coverage)
  and [analytics requirements](index-configuration.md#indexed-sql-analysis) with the workload
  before adding indexes or changing settings. Reuse automatically discovered fields that
  already meet the requirements.
- **No-token fields**: for identifier-like fields that do not need tokenization, such as
  `request_id`, `trace_id`, `span_id`, `user_id`, or exact-match IDs, remove unnecessary token
  delimiters. Keep tokenization minimal for exact-match fields.
- **Chinese indexing**: prefer `chn: false`. Enable Chinese tokenization only when the user
  needs Chinese keyword search on that field; it substantially reduces tokenization and
  write throughput.
- **Long unstructured text**: for long, unstructured fields that are unlikely to be used in SQL
  analysis, such as `content`, `message`, or `raw_payload`, set `doc_value: false` to reduce
  storage overhead.
- **Deep JSON fields**: control JSON index depth carefully. For very deep JSON fields, avoid
  indexing excessive depth; generally do not exceed 5 levels unless the user explicitly needs it.
- **Field types**: use the [type-inference guidance](generate-index-from-logs.md#type-inference)
  for new fields. Do not change an existing type solely because current samples look numeric.

## Tradeoffs

Reducing tokenization, analytics, JSON depth or Chinese tokenization can lower overhead,
but can also change matching or make existing queries unavailable. The required queries
determine which tradeoffs fit the task.
