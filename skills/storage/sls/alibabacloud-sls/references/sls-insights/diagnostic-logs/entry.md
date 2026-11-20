# Diagnostic log topics

`internal-diagnostic_log` contains several independent schemas. First resolve its
storage Project/Store through [service-log discovery](../service-logs.md#discover-the-destination),
then select the relevant topic below. Load only the topic reference needed for
the investigation.

| `__topic__` | Evidence | Reference |
| --- | --- | --- |
| `consumergroup_log` | Consumer-group lag by Logstore and shard | [Consumer lag](consumergroup_log.md) |
| `logtail_alarm` | Collector error types, counts and sampled error details | [Collector alarms](logtail_alarm.md) |
| `logtail_profile` | File/Logstore collection and sending statistics | [Collection statistics](logtail_profile.md) |
| `logtail_status` | Collector heartbeat, resource use and internal metrics | [Collector status](logtail_status.md) |
| `scheduled_sql_alert` | Completed Scheduled SQL instance outcomes and delay | [Scheduled SQL](scheduled_sql_alert.md) |
| `etl_metrics` | Current transformation, import and delivery task progress/errors | [Connector runtime metrics](etl_metrics.md) |

Use `__topic__` in queries to avoid mixing schemas. Field names are
case-sensitive in the documented schema: for example, diagnostic records use
`project`, while several topics use `LogStore` with capital letters. Inspect
actual records and indexes before constructing filters or aggregations.

Read [query and analysis](../../query/entry.md) for execution, time bounds,
indexes and result completeness. Query examples in the topic files are index
search expressions, not executed requests; use the discovered storage Project
and bound the incident interval through the CLI's time parameters.

These are managed built-in logs: follow
[managed Store safety rules](../entry.md#safety-rules-for-managed-built-in-stores).
Source: [Service log types](https://help.aliyun.com/zh/sls/log-types).
