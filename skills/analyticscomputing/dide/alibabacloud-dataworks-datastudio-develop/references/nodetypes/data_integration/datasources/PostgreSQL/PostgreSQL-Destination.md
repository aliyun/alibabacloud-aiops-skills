# Introduction

The PostgreSQL data source provides you with a bidirectional channel for reading from and writing to PostgreSQL, making it convenient for you to configure data synchronization tasks through wizard mode and script mode. This article introduces the PostgreSQL data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| table | The name of the table to be synchronized. | Y | None | Y |  |
| writeMode | Select the import mode. Currently, insert and copy are supported: * insert: Executes PostgreSQL's `insert into...values...` statement to write data to PostgreSQL. When a primary key/unique index conflict occurs in the data, the data row to be synchronized fails to write to PostgreSQL, and the current record becomes dirty data. It is recommended that you prioritize the insert mode. * copy: PostgreSQL provides the copy command for mutual copying between tables and files (standard output, standard input). Data integration supports using `copy from` to load data into a table. It is recommended that you try using this mode only when encountering performance issues. | N | insert | Y |  |
| column | The fields in the destination table that need to have data written to them, separated by English commas. For example `"column":["id","name","age"]`. To write to all columns in order, use an asterisk (\*), for example `"column":["*"]`. | Y | None | Y |  |
| preSql | The SQL statements that need to be executed first before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements, such as clearing old data. | N | None | Y |  |
| postSql | The SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode can support multiple SQL statements, such as adding a certain timestamp. | N | None | Y |  |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between data integration and PostgreSQL, and improve overall throughput. However, setting this value too large may cause OOM in the data integration runtime process. | N | 1,024 | Y |  |
| pgType | PostgreSQL-specific type conversion configuration, supports bigint[], double[], text[], Jsonb, and JSON types. Configuration example is as follows. ```json { "job": { "content": [{ "reader": {...}, "writer": { "parameter": { "column": [ // Destination table field list "bigint_arr", "double_arr", "text_arr", "jsonb_obj", "json_obj" ], "pgType": { // Special type settings, key is the destination table field name, value is the field type. "bigint_arr": "bigint[]", "double_arr": "double[]", "text_arr": "text[]", "jsonb_obj": "jsonb", "json_obj": "json" } } } }] } } ``` | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType":"postgresql",//Plugin name.
      "parameter":{
        "datasource":"",//Data source.
        "column":[// Fields.
          "col1",
          "col2"
        ],
        "table":"",//Table name.
        "preSql":[],//SQL statements executed first before the data synchronization task.
        "postSql":[],//SQL statements executed first after the data synchronization task.
      },
      "name":"Writer",
      "category":"writer"
    }
```
