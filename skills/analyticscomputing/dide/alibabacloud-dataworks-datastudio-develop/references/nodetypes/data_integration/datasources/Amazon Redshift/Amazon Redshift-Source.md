# Introduction

The Amazon Redshift data source provides you with a bidirectional channel for reading from and writing to Amazon Redshift, allowing you to configure data synchronization tasks using both wizard mode and script mode. This article introduces the Amazon Redshift data synchronization capabilities.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the table to be synchronized. | Y | None | Y | Linkage logic: After selecting a table, the default value of splitPk is automatically retrieved |
| column | The list of columns to be synchronized, separated by commas. For example, **"column":\["id","name","age"\]**. To synchronize all columns, use (\*), for example, **"column":\["\*"\]**. | Y | None | Y | |
| where | Filter condition. The system concatenates an SQL statement based on the specified **column**, **table**, and **where** conditions, and extracts data accordingly. For example, during testing, you can specify the **where** condition as `limit 10`. In actual business scenarios, you typically select data from the current day for synchronization, and can specify the **where** condition as **gmt_create\>$bizdate**: * The **where** condition can effectively perform incremental business synchronization. * If the **where** condition is not configured or is empty, full table synchronization is performed. | N | None | Y | |
| splitPk | If **splitPk** is specified, it indicates that you want to use the field represented by **splitPk** for data sharding. The data synchronization system will launch concurrent tasks for data synchronization to improve efficiency. | N | None | Y | Linkage logic: After selecting a table, the default value of splitPk is automatically populated |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "redshift"
  "parameter":
  {
    "datasource":"redshift_datasource",
    "table": "redshift_table_name",
    "where": "xxx=3",
    "splitPk": "id",
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
