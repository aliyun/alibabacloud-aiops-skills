# Introduction

Vertica is a columnar storage-based MPP architecture database. The Vertica data source provides you with bidirectional read and write capabilities for Vertica. This article introduces the data synchronization capabilities of DataWorks for Vertica.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| table | The selected table to be synced. Described using a JSON array, supports reading multiple tables simultaneously. When configuring multiple tables, you need to ensure that the schema structure of the multiple tables is consistent. Vertica Reader does not check whether the table logic is unified. **Note** table must be included in the connection configuration unit. | Y | None | Y |  |
| column | The collection of column names to be synced in the configured table, using JSON array to describe field information. Defaults to all columns configuration, for example \[ \* \]. * Supports column pruning, i.e., you can select partial columns for export. * Supports column reordering, i.e., columns can be exported not in the table schema order. * Supports constant configuration. * column must explicitly specify the collection of columns to sync; it cannot be empty. | Y | None | Y |  |
| splitPk | When Vertica Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will then start concurrent tasks to improve data synchronization efficiency. * It is recommended to use the table primary key as splitPk, because the primary key is usually relatively uniform, so the resulting shards are less likely to have data hotspots. * Currently, splitPk only supports integer data splitting. String, float, date, and other types are not supported. If you specify an unsupported type, Vertica Reader will report an error. * If splitPk is set to empty, the underlying system treats it as not allowing single table sharding, so a single channel is used for extraction. | N | None | Y |  |
| where | Filter condition. Vertica Reader concatenates SQL based on the specified column, table, and where conditions, and extracts data based on that SQL. For example, during testing, you can specify where conditions. In real business scenarios, you usually select the current day's data for synchronization, and can specify the where condition as `gmt_create > $bizdate`. * The where condition can effectively perform business incremental sync. * If the where condition is not configured or is empty, it is treated as full table data sync. | N | None | Y |  |
| querySql | In some business scenarios, the where configuration item is not sufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. After configuring this item, the data synchronization system will ignore the tables, columns, and splitPk configuration items and directly use the content of this configuration to filter data. When you configure querySql, Vertica Reader directly ignores the table, column, and where condition configurations. | N | None | Y |  |
| fetchSize | This configuration item defines the number of records retrieved per batch by the plugin and the database server. This value determines the number of network interactions between data integration and the server, and can significantly improve data extraction performance. **Note** A fetchSize value that is too large (>2048) may cause OOM in the data synchronization process. | N | 1,024 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
"stepType": "vertica", //Plugin name.
"parameter": {
"datasource": "", //Data source name.
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
]
}
]
},
"name": "Reader",
"category": "reader"
}
```
