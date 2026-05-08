# Introduction

The PolarDB data source provides you with a bidirectional channel for reading from and writing to PolarDB. You can configure synchronization tasks through wizard mode and script mode.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| selectedDatabase | Select the destination database/Schema. | Conditionally required | None | Y | Display condition: only displayed when `databaseSelectSupport` includes PolarDB type. Linkage logic: switching clears `table` and triggers table switch event |
| table | The name of the table to be synchronized. | Y | None | Y | Linkage logic: after table switch, column mapping state is cleared; switching `selectedDatabase` also clears `table` |
| writeMode | Select the import mode, which can support: * insert (i.e., insert into in wizard mode) * update (i.e., on duplicate key update in wizard mode) * replace (i.e., replace into in wizard mode) For detailed introduction and scenario examples of different methods, please refer to **writeMode (Primary Key Conflict) Parameter Details** below. **Note** When the destination is PolarDB PG, only insert mode is supported. If you need to update data and avoid primary key conflict issues, please delete existing duplicate data before offline synchronization, and then perform synchronization. Recommended solutions are as follows: * Method 1: Configure a `TRUNCATE` statement in the **preSql** (i.e., **Pre-import Preparation Statement** in wizard mode) parameter to clear the destination table first. * Method 2: Process the destination table in advance at the upstream node of the offline synchronization node to ensure no primary key conflicts during data synchronization. | N | insert | Y | Frontend options: insert/update/replace. Special limitation: PG kernel only supports insert |
| column | The fields in the destination table that need to have data written to them, separated by English commas. For example `"column": ["id", "name", "age"]`. To write to all columns in order, use an asterisk (\*). For example `"column": [" *"]`. | Y | None | Y | |
| preSql | The SQL statements that need to be executed first before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements, such as clearing old data. | N | None | Y | |
| postSql | The SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements, such as adding a certain timestamp. | N | None | Y | |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and PolarDB, and improve overall throughput. However, setting this value too large may cause OOM in the data synchronization runtime process. | N | 256 | Y | Frontend default value: public cloud 256, in-elastic 2048 |
| updateColumn | When writeMode is configured as update, the fields to be updated when a primary key/unique index conflict occurs. Fields are separated by English commas, for example `"updateColumn": ["name", "age"]`. **Note** Currently only supports PolarDB for MySQL. | N | None | Y | Display condition: only displayed when `writeMode = update`. Frontend default value: empty (means update all columns) |
| encoding | The encoding configuration for writing files. | N | UTF-8 | Y | |
| socketTimeout | Socket timeout setting. | N | None | Y | |
| session | Session configuration. | N | None | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "parameter": {
                "postSql": [],//Post-import completion statements.
                "datasource": "test_005",//Data source name.
                "column": [//Destination column names.
                    "id",
                    "name",
                    "age",
                    "sex",
                    "salary",
                    "interest"
                ],
                "writeMode": "insert",//Write mode.
                "batchSize": 256,//The number of records submitted in a single batch.
                "table": "PolarDB_person_copy",//Destination table name.
                "preSql": []//Pre-import preparation statements.
            },
            "name": "Writer",
            "category": "writer",
            "stepType": "polardb"
        }
```
