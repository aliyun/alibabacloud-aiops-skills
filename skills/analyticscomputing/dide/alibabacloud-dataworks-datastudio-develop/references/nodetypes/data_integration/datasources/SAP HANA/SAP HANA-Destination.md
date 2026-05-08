# Introduction

The SAP HANA data source provides you with bidirectional read and write capabilities for SAP HANA. This article introduces the data synchronization capabilities of DataWorks for SAP HANA.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| table | The name of the selected table to be synced. | Y | None | Y |  |
| column | The fields in the destination table to write data to, separated by commas, for example `"column": ["id", "name", "age"]`. To write all columns sequentially, use an asterisk (\*), for example `"column":["*"]`. **Note** When a source field name contains a slash (/), you need to escape it using backslash plus double quotes (\\"your_column_name\\"), for example, if the field name is /abc/efg, the escaped field name is \\"/abc/efg\\". | Y | None | Y |  |
| preSql | The SQL statements that must be executed first before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements. For example, to clear old data in the table before execution: ```shell truncate table tablename ``` **Note** When there are multiple SQL statements, SQL transaction atomicity is not supported. | N | None | Y |  |
| postSql | The SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements. For example, to add a timestamp: `ALTER TABLE tablename ADD colname TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`. | N | None | Y |  |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and the data source, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization process. | N | 1024 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"saphana",//Plugin name.
            "parameter":{
                "postSql":[],//Post-import statements.
                "datasource":"",//Data source.
                "column":[//Column names.
                    "id",
                    "value"
                ],
                "batchSize":1024,//The number of records submitted in a single batch.
                "table":"",//Table name.
                "preSql":[
                     "delete from XXX;" //Pre-import statements.
                   ]
            },
            "name":"Writer",
            "category":"writer"
        }
```
