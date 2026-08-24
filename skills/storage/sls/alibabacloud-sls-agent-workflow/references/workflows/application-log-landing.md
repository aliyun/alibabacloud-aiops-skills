# Application Log Landing

Use this workflow when application code, a logging framework, Producer, or mobile client must send logs to an existing SLS target and make them usable for queries or analysis.

## Desired outcome

The intended data reaches the target Logstore, required fields are queryable, and a representative query proves the result. Any downstream analysis must use verified data.

## Compose the landing

Establish the source, target, and definition of success. Ask only for missing information that changes the route.

Use `alibabacloud-sls-sdk-guidance` for the application integration. Require an existing writable Project and Logstore because the current suite has no standalone resource-management or host-agent collection specialist.

After data arrives, use [Index and query readiness](index-query-readiness.md) only when independent index work is needed. Use `alibabacloud-sls-query` for any additional exact result and `alibabacloud-sls-data-agent` only for requested exploratory analysis or visualization. Reuse equivalent acceptance evidence.

`alibabacloud-sls-query` can prepare and validate an alert query, but the current suite cannot create or verify a managed SLS alert resource. Mark that stage as unsupported rather than deployed.

## Completion evidence

Collect the resolved target, integration status, data-arrival proof, effective index, representative result, and requested analysis output. Distinguish deployed resources from recommendations and identify the smallest remaining gap.
