# Logstore

A Logstore is identified by its region, Project and name. Index configuration
shows searchable and analyzable fields; `doc_value` indicates indexed SQL analytics.
Log samples provide field values and business context; they do not establish
indexing or analytics support.

```sh
aliyun sls query --project PROJECT --logstore STORE \
  --time-range last_1h --query '* | select count(*) as requests' --format json
```

[Query execution](../../query/query-execution.md#logstore) and
[index inspection](../../index/manage-index-config.md#read-an-index) cover further command details.
[SQL](../queries/sql.md), [SPL](../queries/spl.md) and
[variables](../features/variables.md) describe query construction and controls.
