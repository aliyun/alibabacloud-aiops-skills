# Introduction

The AnalyticDB for MySQL 3.0 data source provides you with a bidirectional channel for reading from and writing to AnalyticDB for MySQL 3.0. Offline synchronization supports reading view (VIEW) tables. ADB Lakehouse edition data sources do not support configuring and running synchronization tasks on public resource groups; if the instance configured for an ADB data source is switched from Data Warehouse edition to Lakehouse edition, synchronization tasks running on public resource groups using that data source will fail.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The selected table name to be synchronized. | Y | None | Y | Supports automatically creating the destination table from the source table structure |
| writeMode | The method of writing data. Supports insert, replace, and update modes. insert: ignores the current write data when primary key/unique index conflict occurs; replace: deletes the conflicting row first and then inserts a new row replacing all fields when conflict occurs; update: replaces all fields of the original row with the new row when conflict occurs. | N | insert | Y | Frontend options: `insert` (ignore on primary key conflict) → `insert`; `replace` (delete and replace on conflict) → `replace`; `update` (update on conflict) → `update`; Frontend default value: insert |
| column | The columns in the destination table to write data to, separated by commas, for example `"column": ["id", "name", "age"]`. To write all columns sequentially, use `*`, for example `"column": ["*"]`. | Y | None | Y | |
| preSql | SQL statements that need to be executed first before the data synchronization task starts. Wizard mode only allows executing one statement, while script mode supports multiple, such as clearing old data. | N | None | Y | |
| postSql | SQL statements executed after the data synchronization task completes. Wizard mode only allows executing one statement, while script mode supports multiple, such as adding a timestamp. | N | None | Y | |
| batchSize | The batch size for one-time submission of records. This value can greatly reduce the number of network interactions between the data synchronization system and MySQL, and improve overall throughput. | N | 1024 | Y | Unit: records |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "analyticdb_for_mysql",
  "parameter": {
    "datasource": "adb_mysql_target",
    "table": "target_table",
    "writeMode": "insert",
    "column": ["id", "value"],
    "preSql": [],
    "postSql": [],
    "batchSize": 2048,
    "encoding": "UTF-8"
  },
  "name": "Writer",
  "category": "writer"
}
```
