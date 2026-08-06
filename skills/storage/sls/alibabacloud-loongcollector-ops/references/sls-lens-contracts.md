# SLS Lens (CloudLens for SLS) Run-Log Contracts

> Source: `loongcollector-oncall/knowledge/troubleshooting/user/data-access.md`, `monitoring-queries.md`, `knowledge/base/loongcollector/self-monitoring-metrics.md`. Channel: public `aliyun sls get-logs-v2` on the Lens logstore (default `internal-diagnostic_log`). SQL templates: `monitoring-queries.yaml`.

## 1. Entry discovery state machine

Discover the Lens `project/logstore` with `aliyun sls get-logging --project <business-project>` (CLI-004): `loggingProject` is the Lens project; the `loggingDetails[]` entry whose `type` is `logtail_status`/`logtail_profile`/`logtail_alarm` gives the Lens logstore (typically `internal-diagnostic_log`). `type operation_log` -> operation-record logstore (`internal-operation_log`). Resolve in this order:

```
SLS Lens entry
├─ get-logging returns loggingProject + a logtail_* logstore  -> verify access, then query
├─ user provided lens_project/lens_logstore                   -> verify access + internal-diagnostic_log, then query
├─ get-logging denied / only visible in console               -> guide user to copy entry; pause Lens sub-step
└─ not enabled / no permission / no entry                     -> continue machine-group + config + business-logstore checks;
                                                                 report "Lens evidence missing"; DO NOT fabricate "no alarms"
```

Forbidden: STAROps / `starops sls product-data-collection get` / ToolService JWT / console cookie; guessing `log-service-{uid}-{region}`; aborting the whole diagnosis because Lens discovery failed.

Enable guidance for users: https://help.aliyun.com/zh/sls/enable-the-log-collection-feature-1

## 2. Topic x version routing

Read collector major version first (see version discovery). Query the version-appropriate topic only.

| topic | versions | purpose | required select fields |
|---|---|---|---|
| `logtail_alarm` | all | alarms: parse/duplicate/quota/dir/permission | `__time__,project,logstore,source_ip,alarm_type,alarm_message,version,config_name` |
| `logtail_status` | all | instance status, CPU/mem, read/process/send | `__time__,instance_id,ip,project,status,cpu,memory,version,detail_metric` |
| `loongcollector_metric` | 3.x+ | pipeline in/proc/send/error/quota | `__time__,project,config_name,source_ip,send_bytes,processor_errors_total,flusher_errors_total` |
| `logtail_profile` | 1.x/2.x | config-level succeed/parse-fail/quota | `__time__,project,logstore,config_name,source_ip,succeed_lines,parse_failures,send_quota_error` |
| `logtail_metric` | 1.x/2.x | plugin-level in/out/discard/parse-error | `__time__,source_ip,label.project,label.config_name,label.plugin_name,value.proc_in_records_total,value.proc_parse_error_total` |

Major version `>=3` -> `loongcollector_metric`; `<3` -> `logtail_profile`/`logtail_metric`.

## 3. Version discovery chain (CLI-007)

1. When the config or machine group is known: `list-machines --project <p> --machine-group <g>` -> `machines[].binary` is the collector version (e.g. `3.3.4`). A config maps to its bound machine group via `get-applied-machine-groups`.
2. When only an IP is known: Lens `logtail_status.version` (via `get-logs-v2` on the Lens logstore).
3. User-provided version.

If version cannot be confirmed and a version-gated plugin is needed, ask the user; do not guess.

## 4. Query hard constraints

- Query via `aliyun sls get-logs-v2` with fixed Lens project/logstore, topic filter, and time window (`--from`/`--to` UNIX seconds).
- No `select *`; every selected field must be in the topic allowlist (see `self-monitoring-metrics.md` field lists).
- JSON subfields: `json_extract_scalar(<field>, '$.<key>')`; never `<field>.<key>` unless a runtime-verified independent indexed field exists.
- `logtail_alarm`: filter by `project` first (`__topic__:logtail_alarm and project:<project>`); add `logstore` only if volume is large; **never** put `config_name` in `where`. To view by config, put `config_name` in `select`/`group by` (e.g. `split_part(config_name,'$',2) as pipeline`). SQL containing both `__topic__:logtail_alarm` and `config_name:` in where is a violation.
- After matching an `alarm_type`, always output its `alarm_message`.
- `loongcollector_metric` config filter uses the full double-quoted format: `config_name:"##1.0##<project>$<config>"` (only this path may filter by config_name).
- `project` filter: write `project:<project>` (no quotes).
- Check `meta.progress`; on `Incomplete`, output `[Query: Incomplete] attempt=<n>/4`, preserve the marker in final Evidence, and retry the byte-for-byte identical atomic command after 15 seconds, up to 4 total attempts. If still incomplete, mark `INCOMPLETE`; never treat partial rows as complete statistics.
- "No alarms" must state the query window and account for the ~10-minute alarm reporting cycle.
- Every Lens result reports: Lens project, logstore, topic, time window, version route, and completeness status.

## 5. Symptom query order

- No data: machine-group/version -> `logtail_alarm` (by project) -> config/binding -> `logtail_status` -> version-matched pipeline topic -> business logstore.
- Heartbeat abnormal: `list-machines` -> `logtail_status`; if Lens unavailable, guide user to check host process/region/UserId/`user_defined_id` (user-run).

## 6. Lens acceptance cases

- Paths: user-provided entry, console-only, not-enabled, no-permission (and, if a public discovery API appears later, auto-discover).
- Lens project exists but `internal-diagnostic_log` missing or index absent.
- Empty result vs API failure are strictly distinct.
- 2.x must not query `loongcollector_metric`; 3.x uses full `config_name` format.
- Static-check failures: query contains `select *`, or `logtail_alarm and config_name:` in where, or matches an alarm without outputting `alarm_message`.
- When Lens is unavailable, basic resource + heartbeat diagnosis still completes with an explicit evidence gap.
