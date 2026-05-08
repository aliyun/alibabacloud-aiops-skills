# Introduction

The GBase8a data source provides you with a bidirectional channel for reading from and writing to GBase8a. This article introduces the GBase8a data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | If your DataWorks version supports adding a GBase8a data source, you can reference your added GBase8a data source by name here. | N | None | N |  |
| table | The table selected for synchronization. Described using a JSON array, supporting reading from multiple tables simultaneously. When configuring multiple tables, you must ensure that the schema structure of the multiple tables is consistent. GBase8a Reader does not check whether the table logic is uniform. **Note** table must be included in the connection configuration unit. | Y | None | N |  |
| column | The set of column names in the configured table that need to be synchronized, described using a JSON array. By default, all columns are configured, for example \[ \* \]. * Supports column pruning: you can select partial columns for export. * Supports column reordering: columns can be exported in an order different from the table schema. * Supports constant configuration: for example, `'123'`. * Supports function columns: for example, `date('now')`. * column must explicitly specify the set of columns to synchronize and cannot be empty. | Y | None | N |  |
| splitPk | When GBase8a Reader performs data extraction, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will launch concurrent tasks to improve efficiency. * It is recommended to use the table primary key for splitPk, as the primary key is typically evenly distributed, and the resulting shards are less likely to have data hotspots. * Currently, splitPk only supports integer data sharding; it does not support string, floating-point, date, or other types. If you specify an unsupported type, the splitPk function is ignored, and a single channel is used for synchronization. * If splitPk is set to empty, the underlying system will treat it as no sharding for the single table, and a single channel is used for extraction. | N | Empty | N |  |
| where | Filter condition. GBase8a Reader concatenates SQL based on the specified column, table, and where conditions, and performs data extraction based on that SQL. For example, during testing, you can specify the where condition as limit 10. In actual business scenarios, you typically select the current day's data for synchronization, and specify the where condition as `gmt_create>$bizdate`. * The where condition can effectively perform incremental business synchronization. * If the where condition is not configured or is empty, full table data synchronization is performed. | N | None | N |  |
| querySql | In some business scenarios, the where configuration item is insufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. After configuring this item, the data synchronization system will ignore the tables, columns, and splitPk configuration items, and directly use the content of this configuration to filter data. When you configure querySql, GBase8a Reader directly ignores the table, column, where, and splitPk condition configurations. | N | None | N |  |
| fetchSize | This configuration item defines the number of records fetched per batch between the plugin and the database server. This value determines the number of network interactions between Data Integration and the server, and can significantly improve data extraction performance. **Note** A fetchSize value that is too large (>2048) may cause OOM in the data synchronization process. | N | 1,024 | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "gbase8a", //Plugin name.
            "parameter": {
                "datasource": "", //Data source name.
                "username": "",
                "password": "",
                "where": "",
                "column": [ //Fields.
                    "id",
                    "name"
                ],
                "splitPk": "id",
                "connection": [
                    {
                        "table": [ //Table name.
                            "table"
                        ],
                        "datasource":""
                    }
                ]
            },
            "name": "Reader",
            "category": "reader"
        }
```
