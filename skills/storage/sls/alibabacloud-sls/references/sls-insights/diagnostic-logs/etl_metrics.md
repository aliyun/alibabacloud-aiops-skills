# Connector runtime metrics: `etl_metrics`

Use for current data-transformation, import and delivery task progress and
errors. Reporting is once per minute while the related data source has data;
no data means no report. An empty query alone does not establish a failed task.

| Field | Meaning |
| --- | --- |
| `project`, `job_name`, `instance_id` | Owning Project, job and running instance |
| `metric_type` | `ConnectorMetrics` |
| `_etl_:connector_meta` | Source/target identity and connector task metadata |
| `_etl_:connector_metrics` | Progress, processing volume, failures and request metrics |

Within `_etl_:connector_meta`, inspect `action` (`ingest` for reading or
`deliver` for writing), `connector`, `instance`, `task_id` and `task_name`.
Within `_etl_:connector_metrics`, useful values include:

| Subfield | Interpretation |
| --- | --- |
| `state` | `0`: normal; `1`: error that may slow progress; `2`: failure blocking progress |
| `error` | Error details, absent when no error is recorded |
| `lags`, `desc` | Ingest progress and its source-dependent interpretation |
| `events`, `failed` | Processed and failed record counts |
| `native_bytes`, `events_bytes`, `pub_net_bytes` | Original, parsed and public-network data volumes |
| `req_count`, `rep_time`, `rate_limit_hits` | Request count, average request latency and rate-limit occurrences |

For ingest tasks, `lags` means seconds for SLS/CMS, but consumer lag for Kafka.
Use `connector` and `desc` to interpret it; do not apply one unit to all sources.
Check actual schemas for units not specified here and for JSON/index layout.

Example filter:

```text
__topic__: etl_metrics and project: "example-project" and job_name: "example-job"
```

This topic is in the discovered diagnostic Store. It is distinct from the
configuration type `etl_alert` and the dedicated
[`internal-etl-log`](../etl-logs.md) used for transformation preview/legacy
diagnostics.

Source: [Service log types — task runtime metrics](https://help.aliyun.com/zh/sls/log-types).
