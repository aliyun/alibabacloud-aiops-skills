# Introduction

The SQL Server data source provides you with bidirectional read and write capabilities for SQL Server. It supports SQL Server 2016, 2014, 2012, 2008 R2, 2008, Azure SQL Database, and other versions. Offline sync supports reading view tables.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the selected table to be synced. | Y | None | Y | Linkage logic: After selecting a table, retrieve table structure information (columns, indexes) for conflict detection column and conflict update column data source initialization |
| column | The fields in the destination table to write data to, separated by commas. For example `"column":["id","name","age"]`. To write all columns sequentially, use `*`, for example `"column":["*"]`. | Y | None | Y | Not recommended to configure as `["*"]` |
| preSql | The SQL statements that must be executed first before the data synchronization task. Wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements, for example, to clear old data. | N | None | Y | Display condition: Always displayed; Component type: textarea; placeholder: "Please enter the SQL statement to be executed first before the data synchronization task" |
| postSql | The SQL statements executed after the data synchronization task. Wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements, for example, to add a timestamp. | N | None | Y | Display condition: Always displayed; Component type: textarea; placeholder: "Please enter the SQL statement to be executed after the data synchronization task" |
| writeMode | Import mode, supports insert and upsert. In insert mode, primary key/unique index conflicts are treated as dirty data but the original data is preserved; in upsert mode, primary key/unique index conflicts update the columns specified in updateColumn. | Y | insert | Y | Frontend options: `insert: Insert data using insert method` -> `insert`; `upsert: Merge Into logic` -> `upsert`; Controlled by feature flag (featureControl.writeMode), only supports insert by default |
| conflictMode | Conflict write mode. When writeMode is set to upsert, the conflictMode parameter must be specified. | N (Required when writeMode=upsert) | ignore | Y | Display condition: Only displayed when writeMode is upsert; Frontend options: `replace (update)` -> `replace`; `ignore` -> `ignore`; Prerequisite: The current table must have a unique index or primary key, otherwise selecting replace will show error "The current table has neither a unique index nor a primary key, cannot use the replace strategy for upsert conflicts" |
| uniqueIndexColumns | Conflict detection columns, used to identify whether the same record exists in the destination table. Data integration will determine whether to perform an "insert" or "update" operation based on these fields. | N (Required when writeMode=upsert) | None | Y | Display condition: Only displayed when writeMode is upsert; Multi-select component, can select multiple unique indexes; Tooltips: "Select columns for conflict detection, you can select multiple unique indexes."; Format example `"uniqueIndexColumns":[["col_1","col_2"],["col_1","col_3"]]` |
| updateColumn | Conflict update columns. When it is found that the same record already exists in the destination table, specifies which fields need to be updated. | N | None | Y | Display condition: Only displayed when writeMode is upsert and conflictMode is not ignore; Multi-select component with "Select All" option; Tooltips: "Please select the columns to update on conflict. If no columns are selected, all columns are updated by default."; Format example `"updateColumn":["col_1","col_2"]` |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and SQL Server, and improve overall throughput. | N | 1,024 | N | Setting this too large may cause OOM exceptions in the data synchronization process; only supported in script mode |
| driverVersion | SQL Server driver version. You can specify to use version 12.10 which supports Active Directory Service Principal authentication. | N | 4.0 | N | Only supported in script mode |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "sqlserver",
  "parameter": {
    "datasource": "sql_server_target",
    "column": ["id", "name"],
    "table": "dbo.target_table",
    "preSql": [],
    "postSql": []
  },
  "name": "Writer",
  "category": "writer"
}
```
