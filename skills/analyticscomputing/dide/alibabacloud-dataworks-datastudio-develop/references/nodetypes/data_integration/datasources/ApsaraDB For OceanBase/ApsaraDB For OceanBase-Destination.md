# Introduction

The ApsaraDB for OceanBase data source provides bidirectional functionality for reading from and writing to ApsaraDB for OceanBase data. You can use the ApsaraDB for OceanBase data source to configure synchronization tasks to sync data. This article introduces DataWorks' support for ApsaraDB for OceanBase data synchronization capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| table | The table name to write synchronized data to. | Y | None | Y |  |
| column | The columns in the destination table to write data to, separated by commas. For example `"column": ["id", "name", "age"]`. | Y | None | Y |  |
| obWriteMode | Controls the mode used for writing data to the destination table. | Y | None | Y | **Required field**; Frontend options: `insert into (insert)` → `insert`, `on duplicate key update (update on conflict, MySQL tenant)` → `update`, `merge into matched then update (update on conflict, Oracle tenant)` → `merge` |
| onClauseColumns | Conflict detection columns, configured as primary key fields or unique constraint fields. Use commas to separate multiple fields. | Required when obWriteMode=merge | None | Y | Display condition: When obWriteMode=merge |
| obUpdateColumns | The fields to update when a write conflict occurs. Use commas to separate multiple fields. When not specified, all columns are updated on primary key conflict. | N | All fields | Y | Display condition: When obWriteMode=merge or update |
| preSql | Before writing data to the destination table, the SQL statements here will be executed first. If the SQL contains a table name that needs to be operated on, please use `@table` to represent it, so that the variable is replaced with the actual table name when the SQL statement is executed. | N | None | Y |  |
| postSql | After writing data to the destination table, the SQL statements here will be executed. | N | None | Y |  |
| batchSize | The batch size for one-time submission of records. This value can greatly reduce the number of network interactions between the data synchronization system and the server, and improve overall throughput. | N | 1,024 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"apsaradb_for_OceanBase",//Plugin name.
            "parameter":{
                "datasource": "Data source name",
                "column": [//Fields.
                    "id",
                    "name"
                ],
                "table": "apsaradb_for_OceanBase_table",//Table name.
                "preSql": [ //SQL statements executed first before the data synchronization task.
                    "delete from @table where db_id = -1"
                ],
                "postSql": [//SQL statements executed after the data synchronization task.
                    "update @table set db_modify_time = now() where db_id = 1"
                ],
                "obWriteMode": "insert",
            },
            "name":"Writer",
            "category":"writer"
        }
```
