# Acceptance Criteria

**Scenario**: LoongCollector install + cloud-side ops (onboarding, config, machine group, Lens, basic troubleshooting)
**Purpose**: install stage gate + unified acceptance (U1-U6) + CLI command correctness patterns

## 0. Installation acceptance

| Environment | Pass | When collection is requested |
|---|---|---|
| ECS / self-host | `loongcollectord status` → `loongcollector is running` | onboarding.cloud + U1-U6 |
| ACK | addon `loongcollector` active; `loongcollector-ds` Ready via CS addon resources | reuse `k8s-log-${cid}` / `k8s-group-${cid}`; **SLS API default**; U1-U6 |
| Self-k8s | `loongcollector-ds` Running | reuse values Project / official group; SLS API by default, CRD when requested; U1-U6 |

Collector readiness completes an installation-only request. It does not establish collection success. For collection requests, perform the applicable U1-U6 checks; empty U5 results are not verifiable collection success.

---

## 1. Unified acceptance matrix (U1-U6)

CRD path is detection-only; API path uses `aliyun sls`.

For U5, report whether new data arrived, the acceptance window and any reason collection could not be verified.

| ID | Check | Pass condition (API path) | Failure route |
|---|---|---|---|
| U1 | Config object | `logtail-pipeline-config get` returns; inputs and flushers non-empty | back to config create/modify |
| U2 | Group binding | `machine-group get-applied-configs` (group->config) and `logtail-pipeline-config get-applied-machine-groups` (config->group) agree | back to apply/bind |
| U3 | Applied state | API read succeeds and recent update readable; CRD write path: `status.success=true` + `lastAppliedConfig` non-empty | check management plane, permission, double-write, controller |
| U4 | Heartbeat & version | `machine-group list-machines` contains target; `lastHeartbeatTime` within threshold; version readable (Lens if needed) | heartbeat playbook |
| U5 | Data arrival | new data in the acceptance window; if no new source logs, mark "not verifiable". State the observed data status and reason. | check input path, processing, send, source logs |
| U6 | Field & index | key fields present, searchable/aggregatable, correct type | back to config/index coupling |

Polling: 15s x up to 4 for U5/U6; stop on first hit; on repeated empty, conclude "source produced no new logs" — do not extend sleeping.

Every U1-U6 result must come from a read issued **after** the change: re-read each created or modified object with its own `<group> get` (`logstore get`, `machine-group get`, `logtail-pipeline-config get`, `index get`), both binding directions, and `machine-group list-machines` for heartbeat. Snapshots taken during Observe describe the pre-change state and never satisfy acceptance.

---

## 2. Correct CLI command patterns

### 2.1 Product — `sls` exists; commands come from the `aliyun-cli-sls` plugin
- CORRECT: `aliyun sls query ...`
- INCORRECT: `aliyun log ...`, `aliyunlog log get_logs ...`, `starops sls query ...`

### 2.2 Command — operation exists (verify with `aliyun sls <group> <operation> --help` or `aliyun sls query --help`)
- CORRECT: `logtail-pipeline-config get/create/update`, `machine-group get-applied-configs`, `logtail-pipeline-config get-applied-machine-groups`, `logstore create`, `logstore list`, `machine-group list`, `machine-group list-machines`
- INCORRECT: classic `get-config`/`list-config`/`update-config` used as Pipeline aliases, fictional `get-machine-group-applied-configs`/`get-config-applied-machine-groups`, singular `list-logstore`, `config-apply list`, deprecated `get-logs`, or `update-machine-group-machine`

### 2.3 Parameters — each flag exists for the command
- CORRECT: `query --project --logstore --from --to --query --format json`; `--from`/`--to` accept timestamps, RFC3339, local dates/times and relative times. Use fixed absolute endpoints for retries, or `--time-range` for a single query.
- CORRECT: `machine-group create --project --machine-group --machine-identify-type --machine-list`
- CORRECT: `logtail-pipeline-config apply-to-machine-group --project --machine-group --logtail-pipeline-config`
- CORRECT: `logtail-pipeline-config create --project --logtail-pipeline-config --inputs --flushers [--processors --global --log-sample]`
- CORRECT: resource selectors are `--project`, `--logstore`, `--machine-group` and `--logtail-pipeline-config`; index `--line` JSON uses `chn`, not `includeChinese`
- INCORRECT: `--machine-group-name` (use `--machine-group`), `--config` (use `--logtail-pipeline-config` on pipeline config commands), or combining `--time-range` with `--from`/`--to`

### 2.4 Enum / format
- CORRECT: `--machine-identify-type ip` or `userdefined`
- CORRECT: `--machine-list '["app-server-1","app-server-2"]'`; use `machine-group add-members` / `machine-group remove-members` for member-only changes.
- CORRECT: `--inputs '[{"Type":"input_file","FilePaths":["/var/log/app/*.log"]}]'` (single-quoted JSON list)
- CORRECT: `--inputs '[{"Type":"input_agentsight","ProbeConfig":{}}]'` with `--flushers '[{"Type":"flusher_sls","Logstore":"ebpf-event"}]' --global '{}'` for Agentloop
- INCORRECT: passing inputs as separate flags, or unquoted JSON
- INCORRECT: treating existing `runtime-ebpf-agentsight-config` as overwrite; Agentloop create is lock-and-skip
- INCORRECT: SPL mask `"mode":"builtin"` (must be `buildin`)

### 2.5 Observability / safety
- CORRECT: cloud operations inherit the shared `ALIBABA_CLOUD_USER_AGENT` and use `--region <r>`
- CORRECT: one direct `aliyun sls ...` command per tool call, with literal parameters
- CORRECT: write commands run `--cli-dry-run` first, except when Get-before-Create proves exact equality; that idempotent path skips dry-run/write, runs the corresponding atomic get/list verification, and records the skipped operation and verification. The `config.modify` and AgentSight exceptions in `workflow.md` §6 still apply
- CORRECT: render and validate Pipeline targets with `render_pipeline.py` and `validate_pipeline.py`; coupled config/index changes should follow the sequence in `index-coupling.md`. Showing changes as diffs is recommended; `normalize_diff.py` supports `--kind config`, `--kind index` and `--kind auto`.
- INCORRECT: wrapping cloud calls in variables/functions/scripts/compound shell; printing AK/SK

### 2.6 Processor rename / index type
- CORRECT: all-extended `processor_json` -> `processor_rename` chain.
- CORRECT: `processor_rename` uses equal-length arrays `SourceKeys` and `DestKeys`.
- CORRECT: the coupled index removes each old source key and adds its destination key; status destinations use `long` by default.
- CORRECT: user-facing `float` fields use SLS index type `double`.
- CORRECT: a `text` key's `token` is a JSON **array** of delimiter strings. On `IndexInfoInvalid: field token is of error format`, repair only via `aliyun sls index update` / `index create` (rewrite `--keys` as an array, or pass keys from a task-workspace JSON file). If CLI-side repair still fails, stop and report the unresolved parameter.
- INCORRECT: mixing `processor_parse_json_native` with `processor_rename`; using `SourceKey`/`DestKey` or `processor_rename_native`.
- INCORRECT: `pip install aliyun-log-python-sdk`, `import aliyun.log`, `LogClient`, or reading `~/.aliyun/config.json` to work around a CLI index error.

---

## 3. Lens query acceptance
- No `select *`; fields from the topic allowlist.
- `logtail_alarm` filtered by `project` (not `config_name` in where); `alarm_message` present when an `alarm_type` is reported.
- version routing: `>=3` -> `loongcollector_metric`; `<3` -> `logtail_profile`/`logtail_metric`.
- `meta.progress` checked; `Incomplete` runs no intervening cloud query and retries the identical request up to 4 total attempts at 15s intervals. A fourth Incomplete ends as `INCOMPLETE`, never Complete. `Complete` is reported as `Complete`; do not emit `INCOMPLETE` unless Incomplete actually occurred.

## 4. Authorization and troubleshooting acceptance
- Installation, collection changes and resource changes require user authorization. Do not execute declined or deferred changes. Showing changes as diffs is recommended.
- Troubleshooting should follow the check sequence in `troubleshooting.md`. Complete independent reads, including `machine-group get-applied-configs`, even if the business Project is not found; permission failures follow `workflow.md` §2.
- If `logging get` yields no usable Lens entry, ask for the Lens Project/Logstore. After the user supplies it, query `logtail_alarm` and the version-routed metrics. If Lens remains unavailable, report the evidence gap and the findings from completed checks.
- You may use the Heartbeat, Alarm, Collection, Binding and Pipeline evidence templates in `troubleshooting.md`. Distinguish missing resources, failed reads and unexecuted checks; do not present them as successful observations.
- Onboarding/Verify summaries should identify the Project full name, Logstore, machine group and config name.
