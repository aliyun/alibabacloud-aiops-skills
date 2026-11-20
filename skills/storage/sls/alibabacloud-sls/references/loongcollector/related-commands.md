# `aliyun sls` Command Table

Use the [shared observability setup](../../SKILL.md#observability) and append `--region <r>`. Use `--format json` when parsing responses. Write commands: try `--cli-dry-run` first unless get/list verifies the target state already matches, in which case record the skipped operation without dry-run/write. The `config.modify` and AgentSight exceptions in `workflow.md` §6 still apply. Read exact flags with `aliyun sls <group> <operation> --help` (or `aliyun sls query --help`). Machine-parsable contracts and gap status: `cli-contracts.yaml`.

| Domain | CLI command | Purpose | Risk |
|---|---|---|---|
| Project | `aliyun sls project create` | Create project | R2 |
| Project | `aliyun sls project get` | Get project | R0 |
| Project | `aliyun sls project list` | List projects | R0 |
| Project | `aliyun sls project update` | Update project (get first) | R2 |
| Project | `aliyun sls project delete` | Delete project | R4 |
| Logstore | `aliyun sls logstore create` | Create logstore | R2 |
| Logstore | `aliyun sls logstore get` | Get logstore | R0 |
| Logstore | `aliyun sls logstore list` | List logstores | R0 |
| Logstore | `aliyun sls logstore update` | Merge supplied settings into the current configuration; include retention values to preserve when changing retention | R2 |
| Logstore | `aliyun sls logstore delete` | Delete logstore | R4 |
| Index | `aliyun sls index create` | Create index | R2 |
| Index | `aliyun sls index get` | Get index | R0 |
| Index | `aliyun sls index update` | Update index (get first, merge keys) | R2 |
| Index | `aliyun sls index delete` | Delete index | R3 |
| MachineGroup | `aliyun sls machine-group create` | Create machine group | R2 |
| MachineGroup | `aliyun sls machine-group get` | Get machine group | R0 |
| MachineGroup | `aliyun sls machine-group list` | List machine groups | R0 |
| MachineGroup | `aliyun sls machine-group update` | Replace group configuration, preserving unchanged fields | R2 |
| MachineGroup | `aliyun sls machine-group list-members` | List configured identifiers/IPs | R0 |
| MachineGroup | `aliyun sls machine-group add-members` | Add configured members, preserving other settings | R2 |
| MachineGroup | `aliyun sls machine-group remove-members` | Remove configured members, preserving other settings | R2 |
| MachineGroup | `aliyun sls machine-group delete` | Delete machine group | R4 |
| MachineGroup | `aliyun sls machine-group list-machines` | List machines + heartbeat in a group | R0 |
| PipelineConfig | `aliyun sls logtail-pipeline-config create` | Create pipeline config | R2 |
| PipelineConfig | `aliyun sls logtail-pipeline-config get` | Get pipeline config | R0 |
| PipelineConfig | `aliyun sls logtail-pipeline-config list` | List pipeline configs | R0 |
| PipelineConfig | `aliyun sls logtail-pipeline-config update` | Update config (get first, full body) | R2 |
| PipelineConfig | `aliyun sls logtail-pipeline-config delete` | Delete pipeline config | R4 |
| Binding | `aliyun sls logtail-pipeline-config apply-to-machine-group` | Bind config to group | R2 |
| Binding | `aliyun sls logtail-pipeline-config remove-from-machine-group` | Unbind config from group | R3 |
| Binding | `aliyun sls machine-group get-applied-configs` | Configs applied to a group | R0 |
| Binding | `aliyun sls logtail-pipeline-config get-applied-machine-groups` | Groups a config is applied to | R0 |
| Query | `aliyun sls query` | Query business logstore / Lens run logs | R0 |
| Query | `aliyun sls logging get` | Discover Lens/service-log entry for a business project | R0 |

## Install and K8s (non-SLS)

Every `aliyun cs` cloud call also uses the shared User-Agent environment and `--region`. Addon name is `loongcollector`, never `loongcollector-ds`.

| Domain | Command | Purpose | Risk |
|---|---|---|---|
| ACK | `bash scripts/loongcollector/ensure_ack_prereq.sh --region <r> --profile <profile>` | First-use: `open-ack-service --type propayasgo` + CS RAM roles. Idempotent. Not a cluster create | R2 |
| ACK | `aliyun cs open-ack-service --type propayasgo` | Open ACK Pro+Basic. On `ErrorNotEnabled` / `cskpro` then retry the failed CS write once | R2 |
| ACK | `aliyun ram get-role` / `aliyun ram create-role` / `aliyun ram attach-policy-to-role` | CS service roles (`AliyunCSDefaultRole` …). 403 → RAM HITL | R2 |
| ACK | `aliyun cs create-cluster --biz-profile Default --cluster-spec ack.standard` | Only if the user asked to create a cluster. Never `--profile`. Then `ack.pro.small` | R2 |
| ACK | `aliyun cs describe-addon --addon-name loongcollector` | Addon metadata / latest version | R0 |
| ACK | `aliyun cs list-cluster-addon-instances` | Installed addons | R0 |
| ACK | `aliyun cs describe-cluster-addon-instance --addon-name loongcollector` | Addon state | R0 |
| ACK | `aliyun cs install-cluster-addons --biz-body name=loongcollector` | Install addon | R2 |
| ACK | `aliyun cs upgrade-cluster-addons --biz-body component_name=loongcollector` | Upgrade addon | R2 |
| ACK | `aliyun cs list-cluster-addon-instance-resources --instance-name loongcollector` | Helm objects + DS Ready (not kubectl) | R0 |
| ACK | `aliyun cs describe-cluster-user-kubeconfig --private-ip-address false --temporary-duration-minutes 15` | Opt-in CRD only; write 0600 tempfile; never print | R0 |
| ECS | `aliyun ecs run-command` + `aliyun ecs describe-invocation-results` | Run official `loongcollector.sh` via Cloud Assistant. User authorization is required for installation. Never workbench/OOS | R2 |
| Host | `ssh <alias> -- <cmd>` | Same script on self-hosted Linux | R2 |
| CRD | `kubectl apply -f <cr.yaml>` | Create/update `ClusterAliyunPipelineConfig` | R2 |
| CRD | `kubectl get clusteraliyunpipelineconfigs` | U1/U3 | R0 |
| CRD | `kubectl delete clusteraliyunpipelineconfigs <n>` | Remove CR (may delete cloud config) | R4 |

Render helpers: `scripts/loongcollector/render_loongcollector_install_cmd.py`, `scripts/loongcollector/render_crd.py`, `scripts/loongcollector/wait_cs_task.sh`, `scripts/loongcollector/ensure_ack_prereq.sh`.

## Gaps and fallbacks

- Member-only changes use `machine-group add-members` / `machine-group remove-members`. These commands read and update the group while preserving other settings; they are not server-side atomic membership operations.
- SLS Lens entry auto-discovery (CLI-004, confirmed): `logging get --project <business-project>`; use `loggingProject` plus the `loggingDetails[]` logtail entry, then `query`.
- Collector version discovery (CLI-007): use `machine-group list-machines ...` -> `machines[].binary` when a group is known; otherwise use Lens `logtail_status.version` or a user-provided version.

## Query time format

`query` accepts timestamps, RFC3339, local dates/times and relative times through
`--from`/`--to`, or a range through `--time-range`. Use fixed absolute endpoints
when retrying or comparing results. For example, compute a Unix-second window once:
```bash
python3 -c 'import time; end=int(time.time()); print(end-900, end)'
aliyun sls query --project <p> --logstore <l> --from <unix_from> --to <unix_to> \
  --query "<query>" --format json --region <r>
```

## Error recovery

Determine command success from its exit code: 0 means success; nonzero means failure.
On failure, inspect the available HTTP status, request ID, error code and error
message as described in [CLI error output](../troubleshooting.md#cli-error-output).
Use `classify_sls_error.py` to classify the diagnostics and follow
`references/loongcollector/workflow.md` §6:
- `ParameterInvalid` -> fix only the invalid request parameter, retry.
- `WriteQuotaExceed`/429 -> bounded exponential backoff, retry.
- `InternalServerError`/500 -> retry the identical atomic command.
- `Unauthorized`/`AccessDenied` -> `[Error: permission]`, report missing RAM Action, pause for permission diagnosis and explicit confirmation; if authorization is not confirmed, stop with `[BLOCKED: PERMISSION_REQUIRED]`.

Never switch account/profile, widen scope, or treat an error as success.
Fix local parameter errors before retrying. Missing diagnostic details alone
do not identify an infrastructure failure. If the CLI reports an infrastructure
failure below the API layer, retry the identical atomic command once, then report
the raw output and stop instead of guessing what the API would have returned.
