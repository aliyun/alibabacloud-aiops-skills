# MMS OpenAPI Checklist

Scope: MaxCompute MMS APIs currently covered by this repository (`MaxCompute`, version `2022-01-04`).


| OpenAPI                   | Check | Description                                            |
| ------------------------- | ----- | ----------------------------------------------------- |
| ListMmsDataSources        |       | List data sources (supports filtering by name/type/region) |
| GetMmsDataSource          |       | View data source details (optionally with with-config) |
| CreateMmsFetchMetadataJob |       | Create a metadata inventory job                        |
| GetMmsFetchMetadataJob    |       | Query the status of a metadata inventory job           |
| ListMmsDbs                |       | List the source-side database inventory                |
| GetMmsDb                  |       | Query database details (including mapping fields)       |
| ListMmsTables             |       | List the table inventory (filterable by name/status, etc.) |
| GetMmsTable               |       | Query table details (including migration-related status) |
| ListMmsPartitions         |       | List the partition inventory                           |
| GetMmsPartition           |       | Query partition details                                |
| UpdateMmsDb               |       | Update database-level target mapping (project/schema)   |
| UpdateMmsTable            |       | Update table-level target mapping (project/schema/table) |
| CreateMmsJob              |       | Create a migration job (whole-database/table-level/partition-level) |
| ListMmsJobs               |       | List migration jobs                                    |
| GetMmsJob                 |       | Query migration job details                            |
| StartMmsJob               |       | Start/resume a stopped job                             |
| StopMmsJob                |       | Stop a job                                             |
| RetryMmsJob               |       | Retry a job                                            |
| ListMmsTasks              |       | List migration tasks                                   |
| GetMmsTask                |       | Query migration task details                           |
| ListMmsTaskLogs           |       | Query migration task logs                              |
| CreateMmsTimer            |       | Create a scheduled task (periodically triggered migration) |
| ListMmsTimers             |       | List scheduled tasks                                   |
| GetMmsTimer               |       | Query scheduled task details                           |
| UpdateMmsTimer            |       | Update scheduled task scheduling parameters            |
| ListMmsTimerLogs          |       | Query scheduled task execution logs                    |
| TriggerMmsTimer           |       | Manually trigger a scheduled task to run once          |
| GetMmsAsyncTask           |       | Query async task status and parse the object id        |


Notes:

- `Check` column is intentionally left blank for manual filling.
- API names are listed in OpenAPI CamelCase style; CLI usually maps to kebab-case commands.
