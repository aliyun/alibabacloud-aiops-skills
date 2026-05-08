# Introduction

The DM (Dameng) data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to DM databases, enabling rapid resolution of massive data computation problems. This article introduces the DM data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| schema | The name of the Schema selected for synchronization. | Y | None | Y | Linkage logic: switching clears table and splitPk |
| table | The table selected for synchronization. | Y | None | Y | Linkage logic: selecting a table auto-fills the default value of splitPk |
| column | The set of column names in the configured table that need to be synchronized, described using a JSON array. By default, all columns are configured, for example \[ \* \]: * Supports column pruning, meaning you can select partial columns for export. * Supports column reordering, meaning columns can be exported in an order different from the table schema. * Supports constant configuration, you need to follow the JSON format `["id","1", "'bazhen.csy'", "null", "to_char(a + 1)", "2.3" , "true"]`. * id is a regular column name. * 1 is an integer constant. * 'bazhen.csy' is a string constant. * null is a null pointer. * to_char(a + 1) is a function expression. * 2.3 is a floating-point number. * true is a boolean value. * column must explicitly specify the set of columns to synchronize and cannot be empty. | Y | None | Y | |
| splitPk | When DM Reader performs data extraction, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. The data synchronization system will launch concurrent tasks for data synchronization to improve efficiency: * It is recommended to use the table primary key for splitPk, as the primary key is typically evenly distributed, and the resulting shards are less likely to have data hotspots. * Currently, splitPk only supports integer data sharding; it does not support floating-point, string, date, or other types. If you specify an unsupported type, DM Reader will report an error. * If splitPk is not specified, it will be treated as no sharding for the single table, and DM Reader will use a single channel to synchronize all data. | N | None | Y | Linkage logic: selecting a table auto-fills the default value of splitPk |
| where | Filter condition. DM Reader concatenates SQL based on the specified column, table, and where conditions, and performs data extraction based on that SQL. For example, during testing, you can specify the where condition as limit 10. In actual business scenarios, you typically select the current day's data for synchronization and can specify the where condition as `gmt_create>$bizdate`: * The where condition can effectively perform incremental business synchronization. * If the where condition is not configured or is empty, full table data synchronization is performed. | N | None | Y | |
| fetchSize | This configuration item defines the number of records fetched per batch between the plugin and the database server. This value determines the number of network interactions between the data synchronization system and the server, and can improve data extraction performance. **Note** A fetchSize value that is too large (>2048) may cause OOM in the data synchronization process. | N | 1,024 | Y | |
| addQuote | Whether to add double-quote escaping to table names. | N | true | Y | Frontend default value: `true` |
| querySql | In some business scenarios, the where configuration item is insufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. When you configure this item, the data synchronization system will ignore the column, table, and other configurations, and directly use the content of this configuration item to filter data. For example, if you need to synchronize data after a multi-table join, use `select a,b from table_a join table_b on table_a.id = table_b.id`. When you configure querySql, DM Reader directly ignores the column, table, and where condition configurations. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "category": "reader",
            "name": "Reader",
            "parameter": {
                "datasource": "dm_datasource",
                "table": "table",
                "column": [
                    "*"
                ],
                "preSql": [
                    "delete from XXX;"
                ],
                "fetchSize": 2048
            },
            "stepType": "dm"
        }
```
