# Introduction

The KingbaseES data source provides you with a bidirectional channel for reading from and writing to KingbaseES. This article introduces the KingbaseES data synchronization capabilities of DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the table to be synchronized. | Y | None | Y | Linkage logic: After selecting a table, column information is automatically fetched and the column mapping component is notified to update the Schema, while the first column is taken as the default value for splitPk. |
| where | Filter condition. In actual business scenarios, you often select the current day's data for synchronization, specifying the where condition as `gmt_create>$bizdate`. The where condition can effectively perform business incremental synchronization. If the where statement is not filled in, data synchronization is treated as full data synchronization. | N | None | Y | |
| splitPk | A field in the KingbaseES table used as the split field for synchronization. The split field helps with multi-concurrent synchronization of the KingbaseES table. The split field must be a numeric integer field. If there is no such type, it can be left blank. | N | None | Y | Linkage logic: After selecting a table, the first column of the table is automatically taken as the default value (non-initialization scenario). |
| column | The collection of column names to be synchronized in the configured table, using JSON array to describe field information. By default, all columns are configured, for example `["*"]`. Supports column pruning and column reordering. column must explicitly specify the collection of columns to be synchronized and cannot be empty. | Y | None | Y | |
| username | Username. | N | None | N | |
| password | Password. | N | None | N | |
| jdbcUrl | The JDBC URL for connecting to KingbaseES. For example, jdbc:kingbase8://127.0.0.1:30215?currentschema=TEST. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "kingbasees",
  "parameter": {
    "username": "",
    "password": "",
    "column": [],
    "table": "",
    "jdbcUrl": "",
    "splitPk": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
