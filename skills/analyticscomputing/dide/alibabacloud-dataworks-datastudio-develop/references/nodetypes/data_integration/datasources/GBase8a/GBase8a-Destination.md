# Introduction

The GBase8a data source provides you with a bidirectional channel for reading from and writing to GBase8a. This article introduces the GBase8a data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | N |  |
| table | The name of the table to be synchronized and written, described using a JSON array. **Note** table must be included in the connection configuration unit. | Y | None | N |  |
| column | The fields in the target table that need to be written with data, separated by English commas. For example, `"column": ["id", "name", "age"]`. **Note** The column configuration item must be specified and cannot be empty. | Y | None | N |  |
| preSql | Before writing data to the target table, the standard statements here will be executed first. If the SQL contains a table name that needs to be operated on, please use `@table` to represent it, so that the variable can be replaced with the actual table name when the SQL statement is actually executed. | N | None | N |  |
| postSql | After writing data to the target table, the standard statements here will be executed. | N | None | N |  |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and GBase8a, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization process. | N | 1,024 | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"gbase8a",//Plugin name.
            "parameter":{
                "datasource": "Data source name",
                "username": "",
                "password": "",
                "column": [//Fields.
                    "id",
                    "name"
                ],
                "connection": [
                    {
                        "table": [//Table name.
                            "Gbase8a_table"
                        ],
                        "datasource":""
                    }
                ],
                "preSql": [ //SQL statements executed before the data synchronization task.
                    "delete from @table where db_id = -1"
                ],
                "postSql": [//SQL statements executed after the data synchronization task.
                    "update @table set db_modify_time = now() where db_id = 1"
                ]
            },
            "name":"Writer",
            "category":"writer"
        }
```
