# Commands and query evidence

Run examples from the skill root. All operations here are read-only cloud operations; query records and exported evidence are local files.

## CLI operations

Use the shared [CLI installation guide](../cli-installation-guide.md), [profile configuration](../profile-configuration.md) and [region/endpoint guidance](../regions.md). Set the [shared session and User-Agent](../../SKILL.md#observability) before cloud calls.


| Operation | Command |
| --- | --- |
| List business models | `aliyun sls context-model list` |
| Read Project model generation status | `aliyun sls source-model status` |
| Discover definitions | `aliyun sls context-model catalog overview` or `source-model catalog overview` |
| Read original Member definitions | `aliyun sls context-model catalog get` or `source-model catalog get` |
| Resolve business-model query locations | `aliyun sls context-model catalog resolve` |
| Query logs or execute SQL | `aliyun sls query` |
| Read index configuration | `aliyun sls index get` |

Add `--format json` for machine-readable results. `--max-bytes`, `--sources`, Member selectors and storage-resolution selectors are documented by each command's `--help`. A command's successful exit does not establish complete business evidence: inspect omissions, missing Members, model bindings and query progress as described in the analysis workflow.

## Local helpers

Use the bundled helpers for definition search and Source Model readiness, with the same Aliyun CLI/plugin configuration as the direct commands.

| Command after `python3 scripts/semantic-model/model_qa.py` | Capability |
| --- | --- |
| `context-model catalog search` | Read definitions through `context-model query`, then perform local lexical retrieval, including example queries |
| `source-model catalog search` | Read definitions through `source-model query`, then perform local lexical retrieval; no example queries |
| `source-model readiness` | Read `source-model status` and, when needed, `source-model query`, then check Project generation and the target Logstore's node locally |

All three commands accept `--profile`, `--region`, `--endpoint` and `--timeout`. Source Model commands require the confirmed `--region` to keep routing and Logstore coordinate checks consistent. Context Model region is optional and can come from CLI configuration. Append `--help` for parameters.

The helper entry point does not expose list, status, overview, get, resolve, log query or index commands. Use CLI directly for those operations. Search preserves original definitions, acceptance states, recoverable omitted Member names and byte budgets; an empty lexical match does not establish absent knowledge. Readiness still checks both Project and Logstore generation state.

## Endpoints and credentials

- The helpers invoke `aliyun` from PATH with argument lists and `--format json`; model SPL is passed unchanged through `--query-file -` on stdin. They do not sign requests or read credential files.
- Pass `--profile` to select a CLI identity, or omit it to inherit normal CLI profile selection and credential configuration. Do not change the saved default merely to run this workflow.
- The supplied `--profile`, `--region` and `--endpoint` apply to every CLI invocation in a workflow. Source Model reads disable automatic cross-region discovery to preserve the confirmed routing and avoid additional discovery API calls.
- Context search accepts `--endpoint` or `SLS_CONTEXT_MODEL_ENDPOINT`; direct CLI commands do not read that environment variable. Without an explicit endpoint, CLI uses the selected region/profile configuration. Keep the Context Model service endpoint separate from physical log-query endpoints.
- Source Model, physical log and index commands use the confirmed region and service endpoint. Do not reuse a Context Model endpoint for physical log queries. The CLI handles the Project host prefix.
- `--timeout` is a deadline for each CLI subprocess, default 60 seconds. It is not a flag passed to `aliyun`. A timeout does not establish successful query completion. The helpers do not automatically retry.
- CLI calls inherit the shared session/User-Agent environment. If absent, the adapter creates a process-session ID and uses the root skill manifest version for its User-Agent.
- Nonzero CLI exit codes are failures. Model response completeness is checked separately using `responseStatus.result=Success`, `level=Info` and the original table validation. CLI failure diagnostics retain available error codes, request IDs, HTTP status and the CLI exit code; unstructured messages are not interpreted as proof that a model is missing.

See [RAM permissions](ram-policies.md) for separate model-read and Logstore-query access.

## Query windows and evidence

Use `aliyun sls query --format json --save-file "<absolute-workspace-output-path>"` for queries supporting conclusions. See [query execution](../query/query-execution.md) for time syntax and parameters.

- The start is inclusive and the end exclusive. Preserve a nonempty window. Reuse fixed Unix seconds or RFC3339 endpoints across comparisons and sources.
- CLI `--time-range` is mutually exclusive with `--from/--to`. Local dates use the system timezone; there is no `--timezone` flag. Resolve other timezones explicitly before execution.
- Raw searches use `--line` or `--limit` (0–100, default 100), plus `--offset`; SQL uses SQL `LIMIT`. Use `--power-sql true` when needed.
- CLI has no `--force-accurate` flag. To require strict SQL accuracy, add `set session allow_incomplete=false;` after the search prefix. If necessary, retry an Incomplete response once with the identical query and fixed time window; otherwise follow [incomplete-result recovery](sql/incomplete.md).
- Stdout contains `meta/data`. Saved records contain `request/response`: `request.from/to` are the resolved Unix-second execution window, and `response.meta/data` are the raw service result. Saved files are not overwritten.
- CLI records currently omit the region. Retain the confirmed query region and supply it to [export_query_evidence.py](../../scripts/semantic-model/export_query_evidence.py) with `--region`; export records from different regions separately. The exporter requires complete results and preserves exact SQL and saved timestamps. It also accepts original helper records (`meta/logs/timeRange/request`) and checks their request/response window consistency.
