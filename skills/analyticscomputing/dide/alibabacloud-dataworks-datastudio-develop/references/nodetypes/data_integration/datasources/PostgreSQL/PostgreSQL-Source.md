# Introduction

The PostgreSQL data source provides you with a bidirectional channel for reading from and writing to PostgreSQL, making it convenient for you to configure data synchronization tasks through wizard mode and script mode. This article introduces the PostgreSQL data synchronization capabilities of DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| table | The name of the table to be synchronized. | Y | None | Y |  |
| column | The collection of column names to be synchronized in the configured table, using JSON array to describe field information. By default, all columns are configured, for example \[ \* \]. * Supports column pruning, meaning you can select partial columns for synchronization. * Supports column reordering, meaning columns can be synchronized without following the table schema order. * Supports constant configuration, you need to follow MySQL SQL syntax format, for example `["id", "table","1", "'mingya.wmy'", "'null'", "to_char(a+1)", "2.3" , "true"]` . * id is a regular column name. * table is a column name containing reserved words. * 1 is an integer constant. * 'mingya.wmy' is a string constant (note that a pair of single quotes is required). * 'null' is a string constant. * to_char(a+1) is a string length calculation function. * 2.3 is a floating-point number. * true is a boolean value. * column must explicitly specify the collection of columns to be synchronized and cannot be empty. | Y | None | Y |  |
| splitPk | When PostgreSQL Reader extracts data, if splitPk is specified, it means you want to use the field represented by splitPk for data sharding. Data synchronization will start concurrent tasks to improve data synchronization performance: * It is recommended that splitPk users use the table primary key, because the table primary key is usually relatively uniform, so the shards split out are less likely to have data hotspots. * splitPk only supports integer data sharding, and does not support string, floating-point, date, and other types. If you specify an unsupported type, the splitPk function is ignored and single-channel synchronization is used. * If splitPk is not filled in, including not providing splitPk or splitPk value is empty, data synchronization is treated as using a single channel to synchronize the table data. | N | None | Y |  |
| where | Filter condition. PostgreSQL Reader assembles SQL based on the specified column, table, and where conditions, and extracts data based on that SQL. For example, during testing, you can use the where condition to specify an actual business scenario, usually selecting the current day's data for synchronization, specifying the where condition as `id>2 and sex=1`: * The where condition can effectively perform business incremental synchronization. * If the where condition is not configured or is empty, full table data synchronization is performed. | N | None | Y |  |
| querySql (Advanced mode, not provided in wizard mode) | In some business scenarios, the where configuration item is not sufficient to describe the filter conditions. You can use this configuration item to customize the filter SQL. When this item is configured, the data synchronization system will ignore the tables, columns, and splitPk configuration items, and directly use the content of this configuration to filter data. For example, if you need to synchronize data after a multi-table JOIN, use `select a,b from table_a join table_b on table_a.id = table_b.id`. When you configure querySql, PostgreSQL Reader directly ignores the configuration of table, column, and where conditions. | N | None | Y |  |
| fetchSize | This configuration item defines the number of data records fetched in each batch between the plugin and the database server. This value determines the number of network interactions between data integration and the server, and can significantly improve data extraction performance. **Note** A fetchSize value that is too large (>2048) may cause OOM in the data synchronization process. | N | 512 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"postgresql",//Plugin name.
            "parameter":{
                "datasource":"",//Data source.
                "column":[//Fields.
                    "col1",
                    "col2"
                ],
                "where":"",//Filter condition.
                "splitPk":"",//Use the field represented by splitPk for data sharding, data synchronization will start concurrent tasks for data synchronization.
                "table":""//Table name.
            },
            "name":"Reader",
            "category":"reader"
        }
```
