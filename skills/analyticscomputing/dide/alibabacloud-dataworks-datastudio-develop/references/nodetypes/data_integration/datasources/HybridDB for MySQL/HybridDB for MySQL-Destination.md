# Introduction

The HybridDB for MySQL data source provides you with bidirectional capabilities for reading from and writing to HybridDB for MySQL. This article introduces the HybridDB for MySQL data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the table selected for synchronization. | Y | None | Y | |
| writeMode | Write mode: * insert: insert into (reports dirty data when primary key/constraint conflict occurs). * update: on duplicate key update (updates data when primary key/unique key conflict occurs). * replace: replace into (deletes first then inserts when primary key/constraint conflict occurs). Not recommended as it may cause data write failures or even produce dirty data. | N | 'insert' | Y | Frontend options: 'insert' → 'insert into (reports dirty data when primary key/constraint conflict occurs)'; 'update' → 'on duplicate key update (updates data when primary key/unique key conflict occurs)'; 'replace' → 'replace into (deletes first then inserts when primary key/constraint conflict occurs)'. Linkage logic: when 'update', displays updateColumn parameter; when 'replace', displays a warning message. |
| updateColumn | The columns to update when a primary key conflict occurs. When you need to update only certain columns, please fill in all columns that need to be updated in the text box. If left empty or not filled in, all columns will be updated when a primary key conflict occurs. | N | None | Y | Display condition: displayed when writeMode is 'update'; Frontend options: dynamically fetched from the columns of the selected table. |
| column | The fields in the target table that need to be written with data, separated by English commas. For example `"column":["id","name","age"]`. To write all columns sequentially, use \*, for example `"column":["*"]`. | Y | None | Y | |
| preSql | SQL statements that must be executed before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements, such as clearing old data. | N | None | Y | |
| postSql | SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements, such as adding a timestamp. | N | None | Y | |
| encoding | The encoding configuration for writing files. | N | None | Y | Frontend default value: '' (Use Database Encoding); Frontend options: 'Use Database Encoding' (value is '') and 150+ encoding list. |
| socketTimeout | Socket timeout. | N | 3600000 | Y | Frontend default value: 3600000; Unit: milliseconds. |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and HybridDB for MySQL, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization process. | N | 256 | Y | |
| session | Session configuration. | N | None | Y | |
| dbRule | Database rule. | N | None | N | |
| dbNamePattern | Database name pattern. | N | None | N | |
| tableRule | Table rule. | N | None | N | |
| tableNamePattern | Table name pattern. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "parameter": {
                "postSql": [],//Complete statements after import.
                "datasource": "px_aliyun_hy***",//Data source name.
                "column": [//Destination column names.
                    "id",
                    "name",
                    "sex",
                    "salary",
                    "age",
                    "pt"
                ],
                "writeMode": "insert",//Write mode.
                "batchSize": 256,//Number of records submitted in a single batch.
                "encoding": "UTF-8",//Encoding format.
                "table": "person_copy",//Target table name.
                "preSql": []//Preparation statements before import.
            },
            "name": "Writer",
            "category": "writer",
            "stepType": "hybriddb"
        }
```
