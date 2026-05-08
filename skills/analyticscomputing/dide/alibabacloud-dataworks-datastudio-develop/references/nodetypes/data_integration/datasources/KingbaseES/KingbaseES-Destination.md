# Introduction

The KingbaseES data source provides you with a bidirectional channel for reading from and writing to KingbaseES. This article introduces the KingbaseES data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the table to be synchronized. | Y | None | Y | Linkage logic: After selecting a table, the column mapping state is automatically cleared. |
| column | The fields in the destination table that need to have data written to them, separated by English commas, for example `"column": ["id", "name", "age"]`. To write to all columns in order, use an asterisk (\*), for example `"column":["*"]`. | Y | None | Y | |
| preSql | The SQL statements that need to be executed first before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements. | N | None | Y | |
| postSql | The SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements. | N | None | Y | |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and the data source, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization runtime process. | N | 1024 | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"kingbasees",//Plugin name.
            "parameter":{
                "postSql":[],//Post-import preparation statements.
                "datasource":"",//Data source.
                "column":[//Column names.
                    "id",
                    "value"
                ],
                "batchSize":1024,//The number of records submitted in a single batch.
                "table":"",//Table name.
                "preSql":[
                     "delete from XXX;" //Pre-import preparation statements.
                   ]
            },
            "name":"Writer",
            "category":"writer"
        }
```
