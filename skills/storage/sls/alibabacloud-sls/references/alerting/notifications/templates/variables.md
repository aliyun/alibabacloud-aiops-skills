# Notification-template variables

Load this file only when a
[custom content template](manage-content-templates.md) must show query
results, alert metadata, or recovery state. Read
[template syntax](syntax.md) for control flow and filters.

## Choose the smallest useful variable

| Variable | Use |
| --- | --- |
| `alert.alert_name`, `alert.alert_id`, `alert.project`, `alert.region` | Identify the rule and its owner. |
| `alert.status`, `alert.severity`, `alert.fire_time`, `alert.resolve_time` | Show event status (`firing` / `resolved`), priority, and timing. |
| `alert.labels`, `alert.annotations` | Show identity/routing data and descriptive context. |
| `alert.fire_results` | Final post-join rows that passed evaluation; at most 100 rows are included. |
| `alert.fire_results_count` | Total number of firing rows, which can be greater than the included array. |
| `alert.results` | Per-query inputs and intermediate `QueryData`, including query text, source, time range, and raw results. |
| `alert.results[n].start_time`, `alert.results[n].end_time` | Query start and end times as integer Unix timestamps in seconds; empty for a resource-data (`meta`) query. |
| `alert.results[n].raw_results` | Actual result rows for query `n`; at most 100 rows are included. |
| `alert.results[n].raw_result_count` | Total result rows for query `n` (integer), possibly more than the included array. |
| `alert.results[n].fire_result` | First row from the firing result associated with query `n`. |
| `alert.query_url` or `alert.results[n].query_url` | Link recipients to the source query when inline evidence is truncated. |

`fire_results` is the final set after any join; `results` preserves each query's
own metadata and raw rows. Both `fire_results` and `raw_results` can be
truncated when their serialized value exceeds 2 KB and long fields exceed
1 KB. Use the corresponding count field to state the total, and link to the
query rather than promising a complete log dump in the notification.
For query-result fields, see the [official alert output structure](https://help.aliyun.com/zh/sls/alarm-output-data-structure).

## Example

```text
{{ alert.alert_name }} ({{ alert.status | format_status }})
Matched {{ alert.fire_results_count }} rows; showing the included sample:
{% for result in alert.fire_results %}
- host={{ result.host }}, count={{ result.count }}
{% endfor %}
Query: {{ alert.query_url }}
Query window: {{ alert.results[0].start_time }} - {{ alert.results[0].end_time }} (Unix seconds)
```

For a non-standard key such as `__tag__:__namespace__`, use bracket access:

```text
{{ alert.annotations["__tag__:__namespace__"] }}
```

An absent variable or invalid reference renders as an empty string, which can
hide a typo. Match names exactly against the documented fields and query schema;
use firing and resolved event samples when available. Use `to_json` when a
channel needs a JSON value, and ensure the outer template remains valid for that
channel. Read
[notification channels](../action-policies/channels.md) for format constraints.

See the [official new-template variable reference](https://help.aliyun.com/zh/sls/variables-in-new-alert-templates).
