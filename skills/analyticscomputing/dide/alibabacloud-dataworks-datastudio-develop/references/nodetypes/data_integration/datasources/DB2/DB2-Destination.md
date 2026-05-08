# Introduction

The DB2 data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to DB2 databases, capable of quickly solving computation problems for massive data. This article introduces DataWorks' support for DB2 data synchronization capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The selected table to be synchronized. | Y | None | Y | |
| column | The columns in the destination table to write data to, separated by commas. For example: `"column": ["id", "name", "age"]`. To write all columns sequentially, use (\*). For example `"column": ["*"]`. | Y | None | Y | |
| preSql | SQL statements executed first before the data synchronization task starts. | N | None | Y | |
| postSql | SQL statements executed after the data synchronization task completes. | N | None | Y | |
| batchSize | The batch size for one-time submission of records. | N | 1,024 | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"db2",//Plugin name.
            "parameter":{
                "postSql":[],//SQL statements executed after the data synchronization task.
                "password":"",//Password.
                "jdbcUrl":"jdbc:db2://ip:port/database",//JDBC connection information for DB2 database.
                "column":[
                    "id"
                ],
                "batchSize":1024,//The batch size for one-time submission of records.
                "table":"",//Table name.
                "username":"",//Username.
                "preSql":[]//SQL statements executed before the data synchronization task.
            },
            "name":"Writer",
            "category":"writer"
        }
```
