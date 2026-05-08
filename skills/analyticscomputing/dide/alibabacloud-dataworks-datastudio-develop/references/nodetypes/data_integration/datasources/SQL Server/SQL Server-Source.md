# Introduction

The SQL Server data source provides you with bidirectional read and write capabilities for SQL Server. It supports SQL Server 2016, 2014, 2012, 2008 R2, 2008, Azure SQL Database, and other versions. Offline sync supports reading view tables.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the selected table to be synced. One job can only support syncing one table. | Y | None | Y | Linkage logic: After selecting a table, the table structure is automatically retrieved, and splitPk is auto-filled with the first column of the table (the original splitPk is preserved during initialization; after switching tables, the first column of the new table is used) |
| column | The collection of column names to be synced in the configured table, using JSON array to describe field information. Defaults to all columns configuration, for example `["*"]`. Supports column pruning, column reordering, and constant configuration (such as integer constant `1`, string constant `'mingya.wmy'`, function expression `to_char(a+1)`, etc.). column must explicitly specify the collection of columns to sync; it cannot be empty. | Y | None | Y | Not recommended to configure as `["*"]` |
| splitPk | The split field for data extraction. The data synchronization system will start concurrent tasks for data synchronization to improve efficiency. It is recommended to use the table primary key as the split key. | N | None | Y | Only supports integer data splitting; does not support string, float, date, or other types. Specifying an unsupported type will result in an error |
| where | Filter condition. Data is extracted by concatenating SQL based on the specified column, table, and where conditions. | N | None | Y | Display condition: Always displayed; Linkage logic: When the where condition is empty, it is treated as syncing all information in the entire table; Can effectively perform business incremental sync; Does not currently support the limit keyword for filtering; SQL syntax varies depending on the selected data source; Includes documentation link: "Click here to view system parameter documentation" |
| useReadOnly | Whether to use read-only replicas. | N | None | Y | Display condition: Displayed when the hasReadOnly property in the data source configuration is true; Frontend options: Enable/Disable read-only replica |
| querySql | Custom filter SQL. After configuring this item, the data synchronization system will ignore the table, column, and where configuration items and directly use the content of this configuration to filter data. | N | None | N | Applicable to complex scenarios such as syncing data after multi-table joins; only supported in script mode |
| fetchSize | The number of records retrieved per batch by the plugin and the database server. This value determines the number of network interactions between data integration and the server, and can improve data extraction performance. | N | 1024 | N | A fetchSize value that is too large (>2048) may cause OOM in the data synchronization process; only supported in script mode |

> Y = Yes, N = No

## Configuration Example

General read example:

```json
{
  "stepType": "sqlserver",
  "parameter": {
    "datasource": "sql_server_source",
    "column": ["id", "name"],
    "where": "",
    "splitPk": "id",
    "table": "dbo.test_table"
  },
  "name": "Reader",
  "category": "reader"
}
```

Example using querySql:

```json
{
  "stepType": "sqlserver",
  "parameter": {
    "connection": [
      {
        "querySql": ["select name from dbo.test_table"],
        "datasource": "sql_server_source"
      }
    ],
    "datasource": "sql_server_source",
    "column": ["name"],
    "where": "",
    "splitPk": "id"
  },
  "name": "Reader",
  "category": "reader"
}
```
