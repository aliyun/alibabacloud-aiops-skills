# Introduction

The MySQL data source provides you with a bidirectional channel for reading from and writing to MySQL. This article introduces the MySQL data synchronization capabilities of DataWorks.

# Source
## Parameter Description
| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name, must be exactly consistent with the created data source name. | Y | None | Y | |
| table | The table name to be synchronized. Supports range matching for sharded tables (such as `'table_[0-99]'` or combined ranges). | Y | None | Y | Linkage logic: after selecting a table, the first shard key of the table is automatically fetched as the splitPk default value; when switching tables, the original column mapping is cleared |
| column | Synchronization column collection (JSON array). Supports column pruning, column reordering, and constant configuration. Must be explicitly specified and cannot be empty. | Y | None | Y | Configuring as `["*"]` is not recommended |
| splitPk | Data sharding field (primary key recommended). Only supports integer types; if not filled, single-channel synchronization is used. | N | None | Y | Frontend default value: after selecting a table, auto-filled with the first shard key of the table; linkage logic: when switching tables in non-initialization state, auto-overwritten with the new table's splitPk |
| where | Filter condition (commonly used for incremental synchronization, such as `gmt_create>$bizdate`). If not filled, full synchronization is performed. Does not support `limit`. | N | None | Y | |
| encoding | Encoding format. | N | None | Y | Frontend default value: uses database encoding; frontend options: UTF-8, GBK, GB2312, etc. |
| socketTimeout | Socket timeout (milliseconds). | N | None | Y | Frontend default value: 3600000 (1 hour) |
| useReadOnly | Whether to use read-only connection. | N | None | Y | Display condition: when the data source supports read-only attribute (hasReadOnly is true); frontend default value: true; linkage logic: when true, displays canReadPrimary field (whether to read from master when slave read fails) |
| splitFactor | Split factor. Number of splits = concurrency × splitFactor. Recommended value 1~100; too large may cause OOM. | N | 5 | N | Frontend default value: 5; recommended value 1~100, too large may cause OOM |
| querySql | Custom SQL (advanced mode). When configured, table/column/where/splitPk will be ignored. Parameter name is strictly case-sensitive. | N | None | N | |
| useSpecialSecret | Whether to use respective account passwords for multi-source data sources. true/false. | N | false | N | |
| masterSlave | Master/slave database selection. | N | None | Y | |
| slaveDelayLimit | Slave delay time (seconds). | N | None | Y | |
| checkSlave | Slave check. | N | None | Y | Frontend default value: true |

## Configuration Example

```json
{
  "stepType": "mysql",
  "parameter": {
      "datasource": "",
      "table": "",
      "column": [
         "col0",
         "col1",
         "col2",
         "col3"
      ],
      "splitPk": "",
      "splitFactor": "5",
      "where": "",
      "querySql": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
