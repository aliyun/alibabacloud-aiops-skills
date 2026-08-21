# `aliyun sls` Command Table

All commands: append `--region <r>` and `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/<session-id>`. Write commands: try `--cli-dry-run` first unless a matching get/list verification produced an `Idempotent-Skip`, in which case neither dry-run nor write is called. Read exact flags with `aliyun sls <cmd> --help`. Machine-parsable contracts and gap status: `cli-contracts.yaml`.

| Domain | CLI command | Purpose | Risk |
|---|---|---|---|
| Project | `aliyun sls create-project` | Create project | R2 |
| Project | `aliyun sls get-project` | Get project | R0 |
| Project | `aliyun sls list-project` | List projects | R0 |
| Project | `aliyun sls update-project` | Update project (get first) | R2 |
| Project | `aliyun sls delete-project` | Delete project | R4 |
| Logstore | `aliyun sls create-log-store` | Create logstore | R2 |
| Logstore | `aliyun sls get-log-store` | Get logstore | R0 |
| Logstore | `aliyun sls list-log-stores` | List logstores (plural) | R0 |
| Logstore | `aliyun sls update-log-store` | Update logstore (get first; requires both `--logstore` and `--logstore-name`) | R2 |
| Logstore | `aliyun sls delete-log-store` | Delete logstore | R4 |
| Index | `aliyun sls create-index` | Create index | R2 |
| Index | `aliyun sls get-index` | Get index | R0 |
| Index | `aliyun sls update-index` | Update index (get first, merge keys) | R2 |
| Index | `aliyun sls delete-index` | Delete index | R3 |
| MachineGroup | `aliyun sls create-machine-group` | Create machine group | R2 |
| MachineGroup | `aliyun sls get-machine-group` | Get machine group | R0 |
| MachineGroup | `aliyun sls list-machine-group` | List machine groups (singular) | R0 |
| MachineGroup | `aliyun sls update-machine-group` | Update group (overwrite; also member fallback) | R2 |
| MachineGroup | `aliyun sls delete-machine-group` | Delete machine group | R4 |
| MachineGroup | `aliyun sls list-machines` | List machines + heartbeat in a group | R0 |
| PipelineConfig | `aliyun sls create-logtail-pipeline-config` | Create pipeline config | R2 |
| PipelineConfig | `aliyun sls get-logtail-pipeline-config` | Get pipeline config | R0 |
| PipelineConfig | `aliyun sls list-logtail-pipeline-config` | List pipeline configs (singular) | R0 |
| PipelineConfig | `aliyun sls update-logtail-pipeline-config` | Update config (get first, full body) | R2 |
| PipelineConfig | `aliyun sls delete-logtail-pipeline-config` | Delete pipeline config | R4 |
| Binding | `aliyun sls apply-config-to-machine-group` | Bind config to group | R2 |
| Binding | `aliyun sls remove-config-from-machine-group` | Unbind config from group | R3 |
| Binding | `aliyun sls get-applied-configs` | Configs applied to a group | R0 |
| Binding | `aliyun sls get-applied-machine-groups` | Groups a config is applied to | R0 |
| Query | `aliyun sls get-logs-v2` | Query business logstore / Lens run logs | R0 |
| Query | `aliyun sls get-logging` | Discover Lens/service-log entry for a business project | R0 |

## Gaps and fallbacks

- `update-machine-group-machine` (incremental member add/remove): NO plugin subcommand (CLI-003). Fallback: `get-machine-group` -> merge `machine-list` -> `update-machine-group` (full overwrite); re-read before write to avoid concurrent clobber.
- SLS Lens entry auto-discovery (CLI-004, confirmed): `get-logging --project <business-project>`; use `loggingProject` plus the `loggingDetails[]` logtail entry, then `get-logs-v2`.
- Collector version discovery (CLI-007): use `list-machines ...` -> `machines[].binary` when a group is known; otherwise use Lens `logtail_status.version` or a user-provided version.

## Query time format

`get-logs-v2 --from/--to` are UNIX seconds (int). Compute the window in a separate local tool call, then replace `<unix_from>` and `<unix_to>` with those literal values in one direct cloud call:
```bash
python3 -c 'import time; end=int(time.time()); print(end-900, end)'
aliyun sls get-logs-v2 --project <p> --logstore <l> --from <unix_from> --to <unix_to> \
  --query "<query>" --region <r> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/<session-id>
```

## Error recovery

Preserve the exact error code and `requestID`; follow `SKILL.md` §6:
- `ParameterInvalid` -> `[Error: parameter]`, fix only the invalid request parameter, retry.
- `WriteQuotaExceed`/429 -> `[Error: throttling]`, bounded exponential backoff, retry.
- `InternalServerError`/500 -> `[Error: internal]`, retry the identical atomic command.
- `Unauthorized`/`AccessDenied` -> `[Error: permission]`, report missing RAM Action, pause for permission diagnosis and explicit confirmation; if authorization is not confirmed, stop with `[BLOCKED: PERMISSION_REQUIRED]`.

Never switch account/profile, widen scope, or treat an error as success.
If the CLI fails below the API layer (no `errorCode`/`requestID` in the response), retry the identical atomic command once, then report the raw output and stop instead of guessing what the API would have returned.
