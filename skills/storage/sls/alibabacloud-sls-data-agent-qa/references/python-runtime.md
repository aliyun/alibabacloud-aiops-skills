# Python Runtime

Requires Python 3.10+. The skill provides only the read-only operations needed to answer data questions. Dependencies are maintained in [scripts/requirements.txt](../scripts/requirements.txt). Only direct dependency versions are pinned; pip resolves and installs transitive dependencies.

## Installation and Commands

Install dependencies from the skill's directory, preferably in a dedicated virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`. If a suitable Python environment already exists, run the installation command directly. Use the same Python interpreter for installation and execution. If your environment exposes Python as `python` rather than `python3`, use `python` consistently in these commands.

The entry point `scripts/context_model_qa.py` handles command-line arguments, time parsing, SDK calls, and output. `contextmodel/` and `slsmodel/` contain model logic that can be reused independently.

From the skill's directory, run `python3 scripts/context_model_qa.py`, appending `--help` to any command to view its parameters:

```bash
python3 scripts/context_model_qa.py context-model list --endpoint "<context-model-endpoint>"
python3 scripts/context_model_qa.py context-model catalog overview --endpoint "<context-model-endpoint>" --name "<model-name>"
```

To upgrade dependencies, update `scripts/requirements.txt` and reinstall in a clean environment.

| Command | Capability |
| --- | --- |
| `context-model list` | Paginate through models; supports `--keyword`, `--name`, and `--project-name`. |
| `context-model catalog overview` | Organize the model map by source; use `--sources` for precise filtering. |
| `context-model catalog get` | Read all or selected Members of an Element, preserving unknown fields. |
| `context-model catalog resolve` | Resolve all physical storage locations from a Schema through `storage_link`. |
| `query` | Query logs or SQL; return `meta`, `logs`, and the actual `timeRange`. |
| `index get` | Read index configuration. |

Model commands require `--endpoint` (or the `SLS_CONTEXT_MODEL_ENDPOINT` environment variable). Log and index commands require `--region`, `--project`, and `--logstore`; pass `--endpoint` separately to override the regional endpoint. The model endpoint is not passed to log queries. All requests use HTTPS, with a 10-second connection timeout and a default 60-second read timeout, adjustable with `--timeout`.

Log queries support `--time-range last_15m` / `last_1h` / `now-1h~now` / `today` / `yesterday`, or RFC3339 start and end times with time zones. They also support `--from` and `--to` as Unix timestamps in seconds, milliseconds, microseconds, or nanoseconds. `--time-range` takes precedence over `--from/--to`. Relative units are `s/m/h/d/w/M/y`, where `M` means 30 days and `y` means 365 days. Calendar months and time-rounding syntax are not supported.

`today/yesterday` use the system time zone by default; set `--timezone Asia/Shanghai` to override it. For comparisons across sources, fix the window first and reuse `timeRange.from/to` to avoid drift from relative time ranges.

`--lines` defaults to 100 and `--offset` to 0; they control log search pagination only. SQL row limits use SQL `LIMIT`. `--power-sql` enables Dedicated SQL. `--force-accurate` inserts `set session allow_incomplete=false;` before the SQL and retries once with the same query and time range if the response is Incomplete.

## Credentials and Responses

Use the default credential chain from `alibabacloud-credentials`. For environment credentials, set `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET`; add `ALIBABA_CLOUD_SECURITY_TOKEN` for temporary credentials. The SDK also supports configuration files, RAM Role, OIDC, and other providers. The script does not read DataAgent tokens; do not assume that `aliyun configure` settings are interchangeable with Credentials SDK configuration.

Never put credentials in the skill, command arguments, or answers.

The SDK handles credential refresh and SLS request signing. The APIs used are:

- `ListContextModel`: `GET /context-models`
- `QueryContextModel`: `POST /context-models/{name}/query`
- `GetLogsV2`: `POST /logstores/{store}/logs`; map the server's `data` field to the script's `logs` output.
- `GetIndex`: `GET /logstores/{store}/index`

Model APIs use the SLS SDK's generic `execute` call. See [related_apis.yaml](../related_apis.yaml) for the API list. Availability at a target endpoint still depends on service rollout, network access, and account permissions. The script removes dependencies on the internal CLI and ToolService proxy; it does not replace server-side model capabilities.

Successful commands return JSON with exit code 0. Failures return a top-level `error` with a nonzero exit code. An `Incomplete` query response is returned as received, so exit code alone does not prove completion. Catalog overview performs best-effort discovery. Get/resolve require `responseStatus.result=Success` and `level=Info`; partial responses are not treated as complete definitions or mappings.

Catalog output budgets count UTF-8 bytes of JSON, excluding the trailing newline. If the budget is too small, required metadata and omitted names may exceed it; follow `hint` to narrow the selection or increase the budget.

## Dependency Check

Check that installed dependencies are compatible:

```bash
python3 -m pip check
```
