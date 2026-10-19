# Bounded AgentHub discovery

For an approved bounded read-only discovery evaluation, use
`scripts/discover_column_encryption.py --profile default --expected-role-arn <approved-role-arn> --budget-seconds 300 --output-dir outputs`.
This is not a general replacement for user-specified query filters.

Real-cloud and AgentHub native CLI Mock evaluations use the same original runner.
The Mock case additionally requires the platform's enabled Mock environment and
both fail-closed product guards before any RPC; never enable or edit Mock yourself.
`LIVE_DISCOVERY_PASS` is a historical runner status. With platform-injected CLI
responses it means simulated discovery passed, not that live resources were verified.

The trusted platform must provision `EVAL_ROLE_ARN` and the named CLI profile.
Never set the binding variable yourself to pass the check. Binding metadata is
platform evidence, not independent STS identity verification. CLI version/mode
checks and per-request mode stability use the existing transport; no credentials
are read, copied or configured. Only StsToken and RamRoleArn are accepted here.

The runner calls the existing read-only query implementation in-process. It
checks a monotonic deadline before every RPC, including subsequent pages, and
does not kill/retry an in-flight request. The budget starts when the runner
starts, includes runtime checks, and stops *new requests*, not all wall time.
Each call retains its real action, parameters, response and duration. A unique
private output directory contains evidence.json and summary.txt; no cloud writes
or cleanup occur. No KMS API is included in this bounded probe.

Discovery uses the first returned template and at most three returned regions,
preferring Zhangjiakou then Hangzhou. It checks at most 12 distinct instances,
immediately probes eligible ones (at most two), and selects at most three
databases and three tables per database. A candidate must explicitly have
NotEncrypted status. Names (including schema.table) are passed unchanged.
Completed bounded probes can find no candidate; they do not prove all assets
were searched. Evidence retains listed counts and checked scopes. Template 98
fallback remains possible and strict template attribution is not established.

Report the actual stdout and evidence without changing any state, scope or value.
Include status, checked scope, candidate path, pagination, stop reason and the
actual evidence path. Follow the evaluation's report format; in a Mock run,
explicitly disclose simulation, the unvisited scope and unverified live resources.
Do not translate or rewrite failure statuses into success, or treat an answer
marker as invocation evidence. If the platform mandates an execution log, record
the real command and evidence path there. End after the requested report.
Do not write temporary traversal scripts,
swallow failures, reread missing result files, or duplicate the report.
DISCOVERY_INCOMPLETE, QUERY_FAILED, ENVIRONMENT_BLOCKED and empty instance scope
are not success. A successful runner invocation alone is not evidence of each
API: inspect evidence.json when evaluating business coverage. The platform's
nested-call grading must be checked on the next online run; do not fabricate
query command traces to satisfy old command-pattern assertions.
