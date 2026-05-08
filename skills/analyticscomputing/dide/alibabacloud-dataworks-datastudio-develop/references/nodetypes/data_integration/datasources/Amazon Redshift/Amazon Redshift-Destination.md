# Introduction

The Amazon Redshift data source provides you with a bidirectional channel for reading from and writing to Amazon Redshift, allowing you to configure data synchronization tasks using both wizard mode and script mode. This article introduces the Amazon Redshift data synchronization capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the table to write to. | Y | None | Y | |
| column | The columns in the destination table to write data to, separated by commas. For example, **"column":\["id","name","age"\]**. To write all columns sequentially, use (\*), for example, **"column":\["\*"\]**. | Y | None | Y | |
| preSql | SQL statements executed before the data synchronization task starts. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple. | N | None | Y | |
| postSql | SQL statements executed after the data synchronization task completes. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple. | N | None | Y | |
| batchSize | The maximum number of records imported per batch. | N | 2048 | Y | |
| writeMode | Currently only supports insert. | N | insert | Y | Frontend default value: `insert`; Frontend option: `insert into (Redshift does not support primary key/unique key constraints)` → actual value is `insert` |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "redshift",//Plugin name.
  "parameter":
  {
    "postSql":["delete from XXX;"],
    "preSql":["delete from XXX;"],
    "datasource":"redshift_datasource",//Data source name.
    "table": "redshift_table_name",//Table name.
    "writeMode": "insert",
    "batchSize": 2048,
    "column":
    [
      "id",
      "table_id",
      "table_no",
      "table_name",
      "table_status"
    ]
  },
  "name": "Writer",
  "category": "writer"
}
```
