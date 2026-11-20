# Project service logs

Project service-log configuration controls selected SLS-generated logs for a
source Project and routes them into a storage Project in the **same region**.
The storage Project can be the source Project, another existing Project, or the
automatically created `log-service-<primary-account-id>-<region>` Project.
Do not assume that default name is the configured destination.

## Categories and stores

| Console category | Typical `loggingDetails[].type` | Default Store / purpose |
| --- | --- | --- |
| Important logs | `consumergroup_log`, `logtail_alarm`, `logtail_profile`, `logtail_status`; configurations may also contain `metering` | `internal-diagnostic_log`: consumption lag and collector health/statistics |
| Task runtime logs | For example `scheduled_sql_alert`, `etl_alert`; inspect actual configuration for other task types | `internal-diagnostic_log`: task errors/delays, including supported import, Scheduled SQL and delivery jobs |
| Detailed logs | `operation_log` | `internal-operation_log`: resource changes and data read/write requests |

Read only the reference matching the investigation:

- [`internal-diagnostic_log` topics](diagnostic-logs/entry.md): choose consumer
  lag, collector diagnostics or task execution evidence, then load that topic's
  fields and examples.
- [Detailed operation logs](operation-log.md): API/resource operations, caller,
  latency and data-access evidence in `internal-operation_log`.

`loggingDetails[].type` selects collection configuration; it is not necessarily
the stored `__topic__`. In particular, the current transformation/import/delivery
runtime topic is `etl_metrics`; do not substitute `etl_alert` from configuration
examples. The [official field reference](https://help.aliyun.com/zh/sls/log-types)
documents the topic schemas.

For alert evaluations and notification events, use
[alert history](alert-history.md), which covers both Project execution history
and global alert-center history. These Stores have independent activation and
discovery paths and are not controlled by the service-log switches below.

`internal-diagnostic_log` has a fixed 30-day retention. Detailed logs default to
30 days. These built-in Stores are automatically managed by the service-log
module: do not directly modify their configuration or indexes, delete their
indexes, or delete the Stores. Use only supported service-log module settings
for changes; see [managed Store safety rules](entry.md#safety-rules-for-managed-built-in-stores).
They accept service logs, not arbitrary application writes.
Sources: [Service logs](https://help.aliyun.com/zh/sls/overview-24/),
[Manage service logs](https://help.aliyun.com/zh/sls/manage-service-logs).

## Discover the destination

Use the source Project and its region for the configuration read. CLI cloud calls
use the [shared User-Agent](../../SKILL.md#observability); keep the same profile
for subsequent destination reads.

```bash
aliyun sls logging get \
  --project SOURCE_PROJECT \
  --profile PROFILE --region SOURCE_REGION \
  --format json
```

Illustrative response (only three categories shown):

```json
{
  "loggingProject": "service-log-storage-project",
  "loggingDetails": [
    {"type": "logtail_alarm", "logstore": "internal-diagnostic_log"},
    {"type": "scheduled_sql_alert", "logstore": "internal-diagnostic_log"},
    {"type": "operation_log", "logstore": "internal-operation_log"}
  ]
}
```

Use `loggingProject` as the query Project and the matching entry's `logstore` as
the query Store. Select the entry by its `type`, rather than taking the first
entry or treating every entry as collector logs. Verify destination access and
indexes before querying, and filter by the original source Project where the
schema supports it; a destination can aggregate many Projects.

An absent category means this configuration does not enable it. A denied or
failed read is an evidence gap, not proof that collection is disabled.
`logging get` is not an inventory of every SLS observability source.
In particular, do not use it to discover `internal-alert-history`,
`internal-alert-center-log` or `internal-etl-log`.
See [GetLogging](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogging).

## Enable, change or disable

### Console

Open the source **Project → Service logs → Settings** (follow the activation
prompt if not enabled).

- Enable: select important, task runtime and/or detailed logs and choose the
  storage Project.
- Change: adjust the category switches and/or the same-region storage Project.
- Disable all Project service logs: turn off all selected categories and save.

Only logs generated after activation are collected. Changing the destination
routes new data there; existing data stays in the old destination without
migration. Disabling collection leaves historical data until retention expiry.
Deleting a storage Project is not the procedure for stopping collection.
Source: [Manage service logs](https://help.aliyun.com/zh/sls/manage-service-logs).

### CLI

Inspect local help before preparing a write:

```bash
aliyun sls logging create --help --show-nested
aliyun sls logging update --help --show-nested
aliyun sls logging delete --help
```

`create` enables configuration; `update` **replaces** it. Both require
`--project SOURCE_PROJECT`, `--logging-project STORAGE_PROJECT` and
`--logging-details` containing a JSON array of `{type, logstore}` mappings.
For example, the mapping below enables collector alarms and heartbeats only;
it is not the full important/task runtime category set:

```json
[
  {"type": "logtail_alarm", "logstore": "internal-diagnostic_log"},
  {"type": "logtail_status", "logstore": "internal-diagnostic_log"}
]
```

To update, first retrieve existing configuration, preserve all desired mappings
including unchanged ones, and add/remove only the requested categories.
Preview a prepared create/update with `--cli-dry-run` before executing, and read back with
`logging get` afterward. Follow the user's requested change scope; preparing
diagnostic context does not call these writes.

To stop collection through the Project logging configuration:

```bash
aliyun sls logging delete \
  --project SOURCE_PROJECT \
  --profile PROFILE --region SOURCE_REGION \
  --cli-dry-run
```

Remove `--cli-dry-run` only when executing the requested shutdown. This removes
the logging configuration, not stored history, alert-history recording or
ETL diagnostic recording. Those sources have independent activation paths.
