# Introduction

The AnalyticDB for MySQL 3.0 data source provides you with a bidirectional channel for reading from and writing to AnalyticDB for MySQL 3.0. Offline synchronization supports reading view (VIEW) tables. ADB Lakehouse edition data sources do not support configuring and running synchronization tasks on public resource groups; if the instance configured for an ADB data source is switched from Data Warehouse edition to Lakehouse edition, synchronization tasks running on public resource groups using that data source will fail.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The selected table to be synchronized. | Y | None | Y | Linkage logic: After selecting a table, splitPk is automatically retrieved and populated (using the first sharding key of the table) |
| column | The set of column names to be synchronized in the configured table, using JSON array to describe field information. Defaults to all columns, for example `["*"]`. Supports column pruning, column reordering, and constant configuration (such as integer constant `1`, string constant `'bazhen.csy'`, function expression `to_char(a+1)`, etc.). column must explicitly specify the set of columns to be synchronized and cannot be empty. | Y | None | Y | Not recommended to configure as `["*"]` |
| splitPk | The sharding field for data extraction. The data synchronization system will launch concurrent tasks for data synchronization to improve efficiency. It is recommended to use the table primary key as the split key. | N | First sharding key of the table | Y | Linkage logic: After table switch, the first sharding key is automatically populated; Only supports integer data sharding, does not support string, floating point, date, and other types |
| where | Filter condition. In actual business scenarios, you can select data from the current day for synchronization, for example `gmt_create>$bizdate`. | N | None | Y | When the where clause is not specified, full data synchronization is performed; The where condition cannot be specified as limit 10 |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "analyticdb_for_mysql",
  "parameter": {
    "datasource": "adb_mysql_source",
    "table": "source_table",
    "column": ["id", "value", "table"],
    "where": "",
    "splitPk": "",
    "encoding": "UTF-8"
  },
  "name": "Reader",
  "category": "reader"
}
```
