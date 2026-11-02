# Python runtime

Requires Python 3.10+. Install [scripts/requirements.txt](../scripts/requirements.txt) from the skill directory, preferably in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
python3 -m pip check
```

On Windows PowerShell, activate `.venv\Scripts\Activate.ps1`. Use the same interpreter for installation and execution. Direct dependencies are pinned; pip resolves transitive dependencies.

Run commands from this skill's directory. Use `python3 scripts/model_qa.py` for both model types. The former `scripts/context_model_qa.py` path only forwards to this entry point for existing callers. Append `--help` to any command. All commands are read-only cloud operations; `--save-file` writes a local query record.

| Command | Capability |
| --- | --- |
| `context-model list` | One page of models; filters `--keyword`, `--name`, `--project-name`; paginate using total. |
| `context-model catalog overview/get/search` | Context Model definition discovery and reads, including example queries. |
| `context-model catalog resolve` | Resolve all locations using exactly one of `--schema` or `--source`. |
| `source-model status` | Project model generation status. |
| `source-model readiness` | Check model generation for the Project and the selected Logstore's node state. |
| `source-model catalog overview/get/search` | Shared definition discovery/reads scoped to a Project; no example-query selector. |
| `query` | Log/SQL query; `meta/logs/timeRange`; optional `--save-file`. |
| `index get` | Read index configuration. |

## Endpoints and credentials

- Context commands require `--endpoint` or `SLS_CONTEXT_MODEL_ENDPOINT`, plus `--name` for catalog operations.
- Source commands require `--region` and `--project`. Readiness additionally requires `--logstore`.
- Log/index commands require `--region`, `--project`, `--logstore`.
- Source/log/index commands default to the regional SLS endpoint and accept their own `--endpoint` override. They never inherit `SLS_CONTEXT_MODEL_ENDPOINT`. The SDK adds the Project host prefix.

Use `alibabacloud-credentials`' default credential chain. Environment credentials use `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, optionally `ALIBABA_CLOUD_SECURITY_TOKEN`. Configuration files, RAM roles and OIDC are also SDK providers. Do not assume `aliyun configure` or an internal CLI profile is interchangeable with this SDK chain. Never put credentials in command arguments or answers. Check credential availability with boolean presence checks; do not print credential files or dump environment values into tool output.

The SDK signs requests and refreshes credentials. Requests use HTTPS with a 10-second connection timeout and a 60-second read timeout (`--timeout` overrides read timeout). No DataAgent token, ToolService proxy or internal CLI is required. See [RAM permissions](ram-policies.md) for the actions required by each read operation.

| API action | HTTP path |
| --- | --- |
| ListContextModel | GET `/context-models` |
| QueryContextModel | POST `/context-models/{name}/query` |
| GetSourceModelStatus | GET `/source-models/status` on the Project host |
| QuerySourceModel | POST `/source-models/query` on the Project host |
| GetLogsV2 | POST `/logstores/{store}/logs` on the Project host |
| GetIndex | GET `/logstores/{store}/index` on the Project host |

Model APIs use the SLS SDK's generic `execute` path, so they do not depend on generated convenience methods being present. Service rollout, account permissions and network reachability still determine availability. The action inventory is [related_apis.yaml](../related_apis.yaml).

## Time and query parameters

`--time-range` accepts `last_15m`, `last_1h`, `now-1h~now`, `today`, `yesterday`, or `<RFC3339-start>~<RFC3339-end>` with time zones. It takes precedence over `--from/--to`. The latter also accept Unix timestamps in seconds, milliseconds, microseconds or nanoseconds. Start is inclusive and end exclusive; start must precede end.

Relative units are `s/m/h/d/w/M/y`: `M` means 30 days, `y` 365 days. Calendar-month arithmetic and time-rounding syntax are not supported. `today/yesterday` use the system time zone unless `--timezone` is set (e.g. `Asia/Shanghai`); an explicit IANA zone accounts for daylight-saving calendar boundaries. Reuse the returned absolute timestamps in `timeRange.from/to` across related queries.

`--lines` defaults to 100 and `--offset` to 0 for raw searches. SQL uses LIMIT. `--power-sql` enables Dedicated SQL. `--force-accurate` adds `set session allow_incomplete=false;` and retries an Incomplete response once with the same query and window.

`--save-file` prepares local storage before querying, saves the actual request plus response atomically, and never replaces an existing path. Files contain query data and use private file permissions. It also records Incomplete responses for diagnosis; [export_query_evidence.py](../scripts/export_query_evidence.py) only exports complete records with matching request/response windows. Exported evidence is ordinary Markdown, compatible with external hosts.

## Catalog outputs and reuse

- Context Model responses identify the `model`; Source Model responses identify the `project`.
- Get/search return original Member definitions and preserve unknown fields. Schema/metric/overview groups expose `source`, an origin tag rather than a Schema name. This replaces the older misleading `sourceSchema` field. Terms and example queries retain their own Member bindings.
- Search is local lexical retrieval (Chinese characters/bigrams and English identifiers), not the internal CLI's remote reranking service. `retrieval.method=lexical` makes this explicit. `retrieval.limited` reports the result limit separately from byte truncation. The default limit is 20, maximum 200. Inspect definitions with the host agent and use overview/get when wording does not match.
- Search requires a complete model read, validates recoverable identities/bindings, excludes unaccepted metrics/terms, and matches unaccepted Schema fields by factual name/type only. It preserves returned definitions, including their confidence, for inspection.
- Budgets count UTF-8 JSON bytes. Search retains omitted Member names grouped by Element for retrieval with get and fails when even recovery metadata exceeds `--max-bytes`. Get/overview may exceed a tiny budget to preserve required identity and recovery metadata.
- Get, search, resolve and readiness node reads require `responseStatus.result=Success` and `level=Info`; partial tables are not complete definitions or mappings. Overview is best-effort discovery only.

Success returns JSON and exit code 0; failures return `error.code/message` (and requestId when available) with nonzero exit. Query responses with `meta.progress == "Incomplete"` and readiness responses with `available:false` are valid responses that require inspection; neither establishes successful business analysis.

## Code boundaries and names

| Module | Responsibility |
| --- | --- |
| `model_qa.py` | CLI arguments and dispatch; common log-query execution and evidence recording. |
| `contextmodel/` | Named Context Model API calls and storage resolution through Schema/storage_link. |
| `sourcemodel/` | Project-scoped Source Model API calls, generation status and selected Logstore readiness. |
| `slsmodel/` | Shared definitions, lexical retrieval, bindings, response decoding and output budgets; no model-specific API routing or physical-location resolution. |
| `sls_api.py` | Shared SDK transport, credentials, endpoint validation, log queries and index reads. |
| `query_time.py`, `query_evidence.py`, `export_query_evidence.py` | Shared time windows, local query records and external-host Markdown evidence. |

For library reuse, copy `slsmodel` and the desired `contextmodel` or `sourcemodel` package. Each adapter works without the other, the CLI or SDK dependencies, using an injected `ModelTransport`. Within `slsmodel`, `DefinitionCatalog` reads original definitions; `ModelCatalog` adds identity fields and output budgets. Both adapters reuse those same implementations.

- `context_model_name` / `model_name`: the Context Model name/UUID; Source Models are addressed by `project`.
- `schema_name`: a Schema Element name (`kind=log_set`) inside either model type, never the Context Model name.
- `source_tag` / `source_tags`: semantic `metadata.tags.source` values. The CLI flags remain `--source`/`--sources`, and JSON retains `source`.
- `query_model`: SPL against model definitions; `search_text`: lexical retrieval input; `query_logs` / `log_query`: queries against actual log data.

`ContextModelCatalog.resolve_storage(schema_name=..., source_tag=...)` accepts exactly one selector. Its helpers `contextmodel.storage.resolve_by_schema` and `resolve_by_source_tag` follow logical definitions to physical storage. `SourceModelCatalog` uses the selected Project/Logstore directly and has no storage-resolution method.

Python library callers should use these explicit names instead of the former `Catalog`, client `query`/`status`, catalog `resolve`, and `members`/`sources` keyword arguments. Use `DefinitionCatalog`, `query_model`/`get_generation_status`, `resolve_storage`, and `member_names`/`source_tags` respectively. Command flags, JSON field names and API error codes remain unchanged.

Output helpers now live in `slsmodel.output` and receive an explicit identity dictionary, such as `{"model": model_name}` or `{"project": project}`. Local log evidence uses `query_evidence.LogQueryRecord`; it is separate from model-definition queries.
