# Index and Query Readiness

Use this workflow when data already exists but its index must support known fields, filters, aggregations, SQL/SPL statements, or cost and throughput constraints.

## Desired outcome

The effective index supports the real query workload, proven by representative queries against the target Logstore.

## Compose the work

Start from representative logs and the real query workload; matching a sample schema alone may produce an unusable or unnecessarily expensive index.

- Use `alibabacloud-sls-index-config-management` to inspect, generate, create, update, delete, or optimize an independent index configuration.
- Require indexed fields to exist in delivered data. Changing an upstream collection pipeline is outside the current suite and must not be represented as an index-only change.
- Use `alibabacloud-sls-query` after the effective index is available to execute representative searches or analytics and expose any remaining mismatch in field type, statistics, syntax, or time range.

## Completion evidence

Report the effective index read back from SLS and the representative queries and results. Index JSON without a successful write and read-back remains a proposal.
