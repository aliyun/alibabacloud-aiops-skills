# Introduction

The MariaDB data source provides you with a bidirectional channel for reading from and writing to MariaDB. This article introduces the MariaDB data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | N |  |
| table | The name of the table to be synchronized. | Y | None | N |  |
| writeMode | Select the import mode, **supports insert into, on duplicate key update, and replace into** : * **insert into** : When a primary key/unique index conflict occurs, the conflicting rows cannot be written and will appear as dirty data. If you configure the task through script mode, please set **writeMode** to insert. * **on duplicate key update** : When no primary key/unique index conflict is encountered, the behavior is consistent with **insert into** . When a conflict occurs, the specified fields of the existing row will be replaced with the new row, and data will be written to MariaDB. If you configure the task through script mode, please set **writeMode** to update. * **replace into** : When no primary key/unique index conflict is encountered, the behavior is consistent with **insert into** . When a conflict occurs, the original row will be deleted first, and then the new row will be inserted. That is, the new row will replace all fields of the original row. If you configure the task through script mode, please set **writeMode** to **replace** . | N | insert into | N |  |
| column | The fields in the destination table that need to have data written to them, separated by English commas, for example **"column": \["id", "name", "age"\]** . To write to all columns in order, use an asterisk (\*), for example **"column": \["\*"\]** . | Y | None | N |  |
| preSql | The SQL statements executed first before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements. For example, clear the old data in the table before execution ( **truncate table tablename** ). **Note** When there are multiple SQL statements, transactions are not supported. | N | None | N |  |
| postSql | The SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements. For example, add a timestamp **ALTER TABLE tablename ADD colname TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP** . **Note** When there are multiple SQL statements, transactions are not supported. | N | None | N |  |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and MariaDB, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization runtime process. | N | 256 | N |  |
| updateColumn | When **writeMode** is configured as **update** , the fields to be updated when a primary key/unique index conflict occurs. Fields are separated by English commas, for example **"updateColumn":\["name", "age"\]** . | N | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"mariadb",//Plugin name.
            "parameter":{
                "postSql":[],//Post-import preparation statements.
                "datasource":"",//Data source.
                "column":[//Column names.
                    "id",
                    "value"
                ],
                "writeMode":"insert",//Write mode, you can set it to insert, replace, or update.
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
