# Incomplete and inaccurate query results

Use this reference only when the JSON response has `meta.progress == "Incomplete"`.

## Handling

- Retry the original query with the fixed time window. If it remains `Incomplete`, try query optimization or time slicing.
- Put existing filters that can be expressed as index searches in the search prefix, preserving their matching semantics, to reduce the data volume for subsequent scans or SQL calculations.
- If using SCAN and index configuration confirms that statistical analysis is enabled for all business fields used by the SQL, remove `set session mode=scan;`, check expressions against indexed field types, and retry.
- Do not automatically switch an ordinary index query to SCAN because its results are incomplete.
- Use time slicing only when the slice results can be combined to reconstruct the original query result. The windows must cover the original time range without overlap.

Do not modify indexes or resource configuration automatically.
