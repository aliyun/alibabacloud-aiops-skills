# Introduction

The TiDB data source provides you with offline read capabilities. This article introduces the data synchronization capabilities of DataWorks for TiDB.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| table | The name of the selected table to be synced. Advanced usage examples for configuring table ranges: * You can read from sharded tables by configuring ranges, for example `'table_[0-99]'` reads `'table_0'`, `'table_1'`, `'table_2'` through `'table_99'`. * If your table numeric suffixes have consistent length, for example `'table_000'`, `'table_001'`, `'table_002'` through `'table_999'`, you can configure it as `'"table": ["table_00[0-9]", "table_0[10-99]", "table_[100-999]"]'`. | Y | None | Y |  |
| column | The collection of column names to be synced in the configured table, using JSON array to describe field information. Defaults to all columns configuration, for example `[ * ]`. * Supports column pruning: You can select partial columns for export. * Supports column reordering: Columns can be exported not in the table schema order. * Supports constant configuration: You need to follow MySQL SQL syntax format, for example `["id","table","1","'test_constant'","'null'","to_char(a+1)","2.3","true"]`. * `id` is a regular column name. * `table` is a column name containing a reserved word. * `1` is an integer constant. * `'test_constant'` is a string constant (note that it needs to be enclosed in single quotes). * About null: * `" "` means empty. * `null` means null. * `'null'` means the string "null". * `to_char(a+1)` is a string length calculation function. * `2.3` is a floating point number. * `true` is a boolean value. * `column` must explicitly specify the collection of columns to sync; it cannot be empty. | Y | None | Y |  |
| splitPk | When TiDB Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will then start concurrent tasks to improve data synchronization efficiency. * It is recommended to use the table primary key as splitPk, because the primary key is usually relatively uniform, so the resulting shards are less likely to have data hotspots. * Currently, splitPk only supports integer data splitting. String, float, date, and other types are not supported. If you specify an unsupported type, the splitPk function is ignored, and a single channel is used for synchronization. * If splitPk is not filled in, including not providing splitPk or splitPk value being empty, data synchronization uses a single channel to sync the table data. | N | None | Y |  |
| where | Filter condition. In real business scenarios, you often select the current day's data for synchronization, specifying the where condition as `gmt_create>$bizdate`. * The where condition can effectively perform business incremental sync. If the where statement is not filled in, including not providing the where key or value, data synchronization treats it as syncing all data. * The limit syntax is not supported in the where condition. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType": "tidb",
      "parameter":
      {
        "column":
        [
          "id",
          "name"
        ],
        "where": "",
        "splitPk": "id",
        "connection":
        [
          {
            "selectedDatabase": "test_database",
            "datasource": "test_datasource",
            "table":
            [
              "test_table"
            ]
          }
        ]
      },
      "name": "Reader",
      "category": "reader"
    }
```
