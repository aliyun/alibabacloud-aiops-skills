# Introduction

Vertica is a columnar storage-based MPP architecture database. The Vertica data source provides you with bidirectional read and write capabilities for Vertica. This article introduces the data synchronization capabilities of DataWorks for Vertica.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| jdbcUrl | Describes the JDBC connection information to the destination database. jdbcUrl is included in the connection configuration unit: * Only one value can be configured for one database. Multiple primary databases for the same database are not supported (dual-primary data import scenario). * The jdbcUrl format is consistent with the official Vertica format and can include additional parameter information. For example, `jdbc:vertica://127.0.0.1:3306/database`. | Y | None | Y |  |
| username | The username for the data source. | Y | None | Y |  |
| password | The password for the specified username of the data source. | Y | None | Y |  |
| table | The name of the selected table to be synced, described using a JSON array. **Note** table must be included in the connection configuration unit. | Y | None | Y |  |
| column | The fields in the destination table to write data to, separated by commas, for example `"column": ["id", "name", "age"]`. | Y | None | Y |  |
| preSql | Standard statements executed before writing data to the destination table. If the SQL contains a table name that needs to be operated on, please use `@table` to represent it, so that when the SQL statement is actually executed, the variable is replaced with the actual table name. | N | None | Y |  |
| postSql | Standard statements executed after writing data to the destination table. | N | None | Y |  |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and Vertica, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization process. | N | 1,024 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
"stepType":"vertica",//Plugin name.
"parameter":{
"datasource": "Data source name",
"column": [//Fields.
"id",
"name"
],
"connection": [
{
"table": [//Table name.
"vertica_table"
]
}
],
"preSql": [ //SQL statements executed first before the data synchronization task.
"delete from @table where db_id = -1"
],
"postSql": [//SQL statements executed first after the data synchronization task.
"update @table set db_modify_time = now() where db_id = 1"
]
},
"name":"Writer",
"category":"writer"
}
```
