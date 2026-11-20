# ETL diagnostic logs

`internal-etl-log` is a dedicated data-transformation Store, separate from
`internal-diagnostic_log` and the Project `logging` configuration.

## When to use it

- Data-transformation preview: inspect intermediate/preview output here rather
  than assuming preview writes to the configured business destination.
- Legacy data-transformation task failures: inspect task status and error
  details, including `message` and `reason` when present.

The service creates this Store in the current preview/task Project when the
corresponding transformation functionality is used. It accepts only its
dedicated data. The transformation module automatically manages its
configuration, indexes and lifecycle; do not directly modify its configuration
or indexes, delete its indexes, or delete the Store. Use the transformation
module's supported operations instead; see
[managed Store safety rules](entry.md#safety-rules-for-managed-built-in-stores).
Creating a normal Store with this name does not activate diagnostic recording.
Sources: [Transformation quick start](https://help.aliyun.com/zh/sls/quick-start),
[Legacy transformation FAQ](https://help.aliyun.com/zh/sls/data-transformation-faq/).

## Locate and inspect

Resolve the task or preview's owning Project and region, then inspect
`internal-etl-log` there. Do not look it up through `logging get`, and do not
assume it moved to a centralized service-log Project.

Follow [query and analysis](../query/entry.md). Inspect actual topics, fields
and indexes before filtering. Legacy diagnostics may include
`__tag__:__job_name__`, `__tag__:__schedule_id__`, `__topic__`, `message` and
`reason`; scope by task and incident window where available. Field schemas
depend on the transformation feature and version.

For current import, Scheduled SQL, delivery or transformation runtime signals,
also inspect the enabled task categories in
[`internal-diagnostic_log`](service-logs.md). Do not treat these two Stores as
interchangeable or infer successful task execution from an empty query.
