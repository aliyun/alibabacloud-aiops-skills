# Verify an alert query

## Validate a new or changed query

A source query over a representative window can show the columns, aliases and value types
available to the trigger expression. Existing representative results can supply the same
context. Reproducing a historical execution uses its recorded absolute query window.

For log queries and SQL over metric data, see [query execution](../../../query/query-execution.md#logstore).
Use the rule's alert-compatible statement. [Result precision](../../../query/query-execution.md#result-precision)
and [SQL row limits](../../../query/sql/README.md#result-limits-and-pagination) affect which
conclusions a result supports; an output limit may omit entities.

For direct metric expressions, the corresponding metric query can provide results for the
same window. For `meta` sources, the registered resource and Tag filter determine the records.

A query through the CLI profile does not establish the permissions of the rule's
[cross-account query role](cross-account.md).
