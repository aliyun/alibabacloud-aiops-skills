# Acceptance Criteria

**Scenario**: LoongCollector cloud-side ops (onboarding, config, machine group, Lens, basic troubleshooting)
**Purpose**: unified acceptance (U1-U6) + CLI command correctness patterns

---

## 1. Unified acceptance matrix (U1-U6)

> Source: `loongcollector-oncall/knowledge/base/collection-config/config-model.md` (CRD/API unified checklist). CRD path is detection-only; API path uses `aliyun sls`.

| ID | Check | Pass condition (API path) | Failure route |
|---|---|---|---|
| U1 | Config object | `get-logtail-pipeline-config` returns; inputs and flushers non-empty | back to config create/modify |
| U2 | Group binding | `get-applied-configs` (group->config) and `get-applied-machine-groups` (config->group) agree | back to apply/bind |
| U3 | Applied state | API read succeeds and recent update readable (CRD: `status.success=true` + `lastAppliedConfig` non-empty) | check management plane, permission, double-write |
| U4 | Heartbeat & version | `list-machines` contains target; `lastHeartbeatTime` within threshold; version readable (Lens if needed) | heartbeat playbook |
| U5 | Data arrival | new data in the acceptance window; if no new source logs, mark "not verifiable" | check input path, processing, send, source logs |
| U6 | Field & index | key fields present, searchable/aggregatable, correct type | back to config/index coupling |

Polling: 15s x up to 4 for U5/U6; stop on first hit; on repeated empty, conclude "source produced no new logs" — do not extend sleeping.

Every U1-U6 result must come from a read issued **after** the change: re-read each created or modified object with its own `get-*` (`get-log-store`, `get-machine-group`, `get-logtail-pipeline-config`, `get-index`), both binding directions, and `list-machines` for heartbeat. Snapshots taken during Observe describe the pre-change state and never satisfy acceptance.

---

## 2. Correct CLI command patterns

### 2.1 Product — `sls` exists; commands come from the `aliyun-cli-sls` plugin
- CORRECT: `aliyun sls get-logs-v2 ...`
- INCORRECT: `aliyun log ...`, `aliyunlog log get_logs ...`, `starops sls query ...`

### 2.2 Command — subcommand exists (verify with `aliyun sls <cmd> --help`)
- CORRECT: `get/create/update-logtail-pipeline-config`, `get-applied-configs`, `get-applied-machine-groups`, `create-log-store`, `list-log-stores` (plural), `list-machine-group` (singular), `list-machines`
- INCORRECT: classic `get-config`/`list-config`/`update-config` used as Pipeline aliases, fictional `get-machine-group-applied-configs`/`get-config-applied-machine-groups`, singular `list-logstore`, `config-apply list`, deprecated `get-logs`, or `update-machine-group-machine`

### 2.3 Parameters — each flag exists for the command
- CORRECT: `get-logs-v2 --project --logstore --from --to --query` (`--from`/`--to` are UNIX seconds)
- CORRECT: `create-machine-group --project --group-name --machine-identify-type --machine-list`
- CORRECT: `apply-config-to-machine-group --project --machine-group --config-name`
- CORRECT: `create-logtail-pipeline-config --project --config-name --inputs --flushers [--processors --global --log-sample]`
- CORRECT: create-name flags are `--project-name` / `--logstore-name` / `--group-name`; read/query flags are `--project` / `--logstore` / `--machine-group`; index `--line` JSON uses `chn`, not `includeChinese`
- INCORRECT: `--machine-group-name` (use `--machine-group`), `--config` (use `--config-name` on pipeline config commands), `--time-range` (get-logs-v2 uses `--from`/`--to`)

### 2.4 Enum / format
- CORRECT: `--machine-identify-type ip` or `userdefined`
- CORRECT: `--inputs '[{"Type":"input_file","FilePaths":["/var/log/app/*.log"]}]'` (single-quoted JSON list)
- INCORRECT: passing inputs as separate flags, or unquoted JSON

### 2.5 Observability / safety
- CORRECT: every cloud-API command has `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/<session-id>` and `--region <r>`
- CORRECT: one direct `aliyun sls ...` command per tool call, with literal parameters
- CORRECT: write commands run `--cli-dry-run` first, except when Get-before-Create proves exact equality; that idempotent path skips dry-run/write, runs the corresponding atomic get/list verification, and emits `[Idempotent-Skip] ...` in final Changes
- CORRECT: every R2/R3/R4 target has an executed `normalize_diff.py` result (`--kind auto` outside config/index); every coupled config/index plan follows snapshots → `validate_pipeline.py` → `normalize_diff.py --kind config` → `normalize_diff.py --kind index`
- INCORRECT: handwritten/raw diffs; wrapping cloud calls in variables/functions/scripts/compound shell; `--user-agent` on `aliyun version`/`configure`/`plugin`; printing AK/SK

### 2.6 Processor rename / index type
- CORRECT: all-extended `processor_json` -> `processor_rename` chain.
- CORRECT: `processor_rename` uses equal-length arrays `SourceKeys` and `DestKeys`.
- CORRECT: the coupled index removes each old source key and adds its destination key; status destinations use `long` by default.
- CORRECT: user-facing `float` fields use SLS index type `double`.
- INCORRECT: mixing `processor_parse_json_native` with `processor_rename`; using `SourceKey`/`DestKey` or `processor_rename_native`.

---

## 3. Lens query acceptance
- No `select *`; fields from the topic allowlist.
- `logtail_alarm` filtered by `project` (not `config_name` in where); `alarm_message` present when an `alarm_type` is reported.
- version routing: `>=3` -> `loongcollector_metric`; `<3` -> `logtail_profile`/`logtail_metric`.
- `meta.progress` checked; `Incomplete` immediately emits `[Query: Incomplete] attempt=<n>/4`, runs no intervening cloud query, and retries the identical request up to 4 total attempts at 15s intervals. A fourth Incomplete ends as `INCOMPLETE`, never Complete.

## 4. Approval and troubleshooting acceptance
- A pending confirmation ends the turn with the question and `[AWAITING: R2_CONFIRMATION]`. Only actual user messages count as replies; three asks without a decision end with `[BLOCKED: R2_CONFIRMATION_TIMEOUT]`. Explicit rejection ends with `[CANCELLED: R2_CONFIRMATION_REJECTED]`. No write follows either state.
- Troubleshooting always emits every applicable field-complete Heartbeat, Alarm, Collection, Binding, and Pipeline evidence line from `SKILL.md` §10, using `N/A` plus attempted command/error when a resource is missing.
