# Introduction

The Oracle data source provides you with a bidirectional channel for reading from and writing to Oracle, making it convenient for you to configure data synchronization tasks through wizard mode and script mode. This article introduces the Oracle data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. | Y | None | Y | |
| selectedDatabase | Selected database name (schema). | Depends on data source type | None | Y | Display condition: displayed when the data source supports it; linkage logic: switching clears table and triggers table switch event |
| table | Destination table name. If the table's schema information is inconsistent with the above configuration, please use the `schema.table` format. | Y | None | Y | After selecting a table, column information is automatically fetched |
| column | Destination table write fields (JSON array). Use `["*"]` for writing all columns. | Y | None | Y | |
| preSql | SQL statements that need to be executed first before the data synchronization task. | N | None | Y | Supports multiple SQL statements |
| postSql | SQL statements executed after the data synchronization task. | N | None | Y | Supports multiple SQL statements |
| encoding | Encoding format. | N | None | Y | |
| session | Database connection session parameters. | N | None | Y | Supports multiple entries |
| socketTimeout | Socket timeout (milliseconds). | N | None | Y | |

## Configuration Example

```json
{
            "stepType":"oracle",
            "parameter":{
                "postSql":[],
                "datasource":"",
                "session":[],
                "column":[
                    "id",
                    "name"
                ],
                "encoding":"UTF-8",
                "table":"",
                "preSql":[]
            },
            "name":"Writer",
            "category":"writer"
        }
```
