# Incomplete and Inexact Query Results

Use this guidance only when the JSON response has `meta.progress == "Incomplete"`.

## Recovery

- Retry the original query with the same fixed time window. If it remains `Incomplete`, try query optimization or time partitioning.
- Move existing filters that can be expressed as indexed searches into the search prefix, preserving their matching semantics to reduce data scanned or processed by SQL.
- If the query currently uses SCAN and the index configuration confirms that all business fields used in the SQL have analytics enabled, remove `set session mode=scan;`, check expressions against indexed field types, and retry.
- Do not automatically switch an ordinary indexed query to SCAN because its results are incomplete.
- Use time partitioning only when partial results can be combined to reproduce the original query result. The windows must cover the original time range without overlap.

Do not automatically modify indexes or resource configuration.
