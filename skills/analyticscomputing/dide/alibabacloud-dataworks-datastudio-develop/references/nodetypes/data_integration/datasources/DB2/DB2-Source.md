# Introduction

The DB2 data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to DB2 databases, capable of quickly solving computation problems for massive data. This article introduces DataWorks' support for DB2 data synchronization capabilities.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The selected table to be synchronized. One job only supports synchronizing one table. | Y | None | Y | Linkage logic: After selecting a table, the default value of splitPk is automatically populated |
| column | The set of column names to be synchronized in the configured table, using JSON array to describe field information. Defaults to all columns, for example \[ \* \]: * Supports column pruning, i.e., you can export partial columns. * Supports column reordering, i.e., columns can be exported not in the order of the table Schema. * Supports constant configuration, following DB2 SQL syntax format. For example, `["id", "1", "'const name'", "null", "upper('abc_lower')", "2.3" , "true"]`: * id is a regular column name. * 1 is an integer constant. * 'const name' is a string constant (needs to be enclosed in single quotes). * null is a null pointer. * upper('abc_lower') is a function expression. * 2.3 is a floating point number. * true is a boolean value. * column must explicitly specify the set of columns to be synchronized and cannot be empty. | Y | None | Y | |
| splitPk | When DB2 Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. The data synchronization system will launch concurrent tasks for data synchronization to improve efficiency: * It is recommended to use the table primary key as splitPk, because table primary keys are typically more uniform, and the resulting shards are less likely to have data hotspots. * Currently splitPk only supports integer data sharding, and does not support floating point, string, date, and other types. If you specify an unsupported type, DB2 Reader will report an error. | N | "" | Y | Linkage logic: After selecting a table, the default value of splitPk is automatically populated |
| where | Filter condition. DB2 Reader concatenates SQL based on the specified column, table, and where conditions, and extracts data accordingly. In actual business scenarios, you typically select data from the current day for synchronization, and can specify the where condition as `gmt_create>$bizdate`. The where condition can effectively perform incremental business synchronization. If this value is empty, it means synchronizing all information in the full table. | N | None | Y | |
| querySql | In some business scenarios, the where configuration item is not sufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. When this item is configured, the data synchronization system ignores table, column, and other configurations, and directly uses the content of this configuration to filter data. For example, when you need to synchronize data after a multi-table Join, use `select a,b from table_a join table_b on table_a.id = table_b.id`. When you configure querySql, DB2 Reader directly ignores the table, column, and where condition configurations. | N | None | N | |
| fetchSize | This configuration item defines the number of records retrieved per batch between the plugin and the database server. This value determines the number of network interactions between the data synchronization system and the server, and can significantly improve data extraction performance. **Note** A fetchSize value that is too large (>2048) may cause OOM in the data synchronization process. | N | 1024 | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"db2",//Plugin name
            "parameter":{
                "password":"",//Password
                "jdbcUrl":"",//JDBC connection information for DB2 database
                "column":[
                    "id"
                ],
                "where":"",//Filter condition.
                "splitPk":"",//Data sharding
                "table":"",//Table name
                "username":""//Username
            },
            "name":"Reader",
            "category":"reader"
        }
```
