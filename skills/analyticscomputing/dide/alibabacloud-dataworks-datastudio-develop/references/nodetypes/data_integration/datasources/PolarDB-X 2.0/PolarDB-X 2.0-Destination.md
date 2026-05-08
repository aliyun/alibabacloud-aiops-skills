# Introduction

The PolarDB-X 2.0 data source provides you with a bidirectional channel for reading from and writing to PolarDB-X 2.0. This article introduces the PolarDB-X 2.0 data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. This name must be consistent with the PolarDB-X 2.0 data source name created in the Data Source Management interface. | Y | None | Y | |
| table | The name of the table to be synchronized. | Y | None | Y | Linkage logic: after selecting a table, column information is automatically fetched and the column mapping component is notified to update the Schema. |
| writeMode | Select the import mode, supports three methods: * **insert into**: When a primary key/unique index conflict occurs, the conflicting rows cannot be written and will appear as dirty data. * **replace into**: When no primary key/unique index conflict is encountered, the behavior is consistent with insert into. When a conflict occurs, the original row is deleted first, and then a new row is inserted. That is, the new row replaces all fields of the original row. * **insert ignore**: When a primary key/unique index conflict occurs, the conflicting data is ignored. | N | 'insert' | Y | Frontend options: 'insert' → 'insert into (report dirty data on primary key/constraint conflict)'; 'replace' → 'replace into (overwrite entire row data on primary key/constraint conflict)'; 'insert ignore' → 'insert ignore (ignore conflicting data on primary key/constraint conflict)'. Selecting replace displays a warning prompt. |
| column | The fields in the destination table that need to have data written to them, separated by English commas, for example **"column": \["id", "name", "age"\]** . To write to all columns in order, use an asterisk (\*), for example **"column": \["\*"\]** . | Y | None | Y | |
| preSql | The SQL statements that need to be executed first before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements. For example, clearing old data in the table before execution. **Note** When there are multiple SQL statements, transactions are not supported. | N | None | Y | |
| postSql | The SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements. For example, adding a certain timestamp. **Note** When there are multiple SQL statements, transactions are not supported. | N | None | Y | |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and PolarDB-X 2.0, and improve overall throughput. However, if this value is set too large, it may cause out of memory. | N | 1024 | Y | Frontend default value: 1024; unit: records. |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"PolarDB-X 2.0",//Plugin name.
            "parameter":{
                "postSql":[],//Post-import preparation statements.
                "datasource":"",//Data source.
                "column":[//Column names.
                    "id",
                    "value"
                ],
                "writeMode":"insert",//Write mode, you can set it to insert or replace.
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
