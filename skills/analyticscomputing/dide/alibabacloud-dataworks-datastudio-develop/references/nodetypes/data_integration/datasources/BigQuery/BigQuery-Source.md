# Introduction

The BigQuery data source provides you with the ability to read from BigQuery, allowing you to configure data synchronization tasks using both wizard mode and script mode. This article introduces DataWorks' support for BigQuery data synchronization capabilities.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | N |  |
| dataset | Dataset, the BigQuery dataset. | Y | None | N |  |
| table | The selected table name to be synchronized. | Y | None | N |  |
| column | The BigQuery data to read, with fields separated by commas. For example "column": \["id", "name", "age"\]. | Y | None | N |  |
| where | Filter condition. BigQuery Reader concatenates SQL based on the specified **column**, **table**, and **where** conditions, and extracts data accordingly. For example, during testing, you can specify the **where** condition as `LIMIT 10`. In actual business scenarios, you typically select data from the current day for synchronization, and can specify the **where** condition as `gmt_create>$bizdate`: * The **where** condition can effectively perform incremental business synchronization. * If the **where** condition is not configured or is empty, no filtering is applied. | N | None | N |  |
| partition | Configure partition information. You can synchronize specific partitions and support synchronizing multiple partitions at once. | N | None | N |  |
| splitPk | If a partition has been specified, the **splitPk** field does not take effect. If **splitPk** is specified, it indicates that you want to use the field represented by **splitPk** for data sharding. The data synchronization system will launch concurrent tasks for data synchronization to improve efficiency. | N | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "bigquery"
  "parameter":
  {
    "datasource":"bq_test1",
    "table": "partition_1107",
    "where": "xxx=3",
    "dataSet": "database_0724",
    "partition": [
      "_PARTITIONTIME='2023-11-07'"
     ],
    "column":
    [
      "id",
      "table_id",
      "table_no",
      "table_name",
      "table_status"
    ]
  },
  "name": "Reader",
  "category": "reader"
}
```
