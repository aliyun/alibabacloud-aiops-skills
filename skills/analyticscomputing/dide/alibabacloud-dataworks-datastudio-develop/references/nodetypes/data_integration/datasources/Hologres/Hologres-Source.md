# Introduction

The Hologres data source provides you with a bidirectional channel for reading from and writing to Hologres. This article introduces the Hologres data synchronization capabilities supported by DataWorks.

# Source
## Parameter Description
| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | The Hologres data source name configured in DataWorks. | Y | None | Y | |
| selectedDatabase | The name of the database within the Hologres instance. | Depends on data source type | None | Y | Linkage logic: switching clears table, tableColumn, and tableDetail; Frontend options: fetched from the backend schemaInfos API, both label and value are schema names |
| table | The Hologres table name. If it is a partitioned table, please specify the parent table name. | Y | None | Y | Linkage logic: after selecting a table, partition column information (partitionColumns) is fetched and the partition default value is auto-filled; Frontend options: table name list fetched from the backend getTables API |
| column | Defines the data columns to read, for example `["*"]` means all columns. | Y | None | Y | |
| partition | The partition information where the data to be read is located. Must be specified down to the last level of partitioning. | Required for partitioned tables, not needed for non-partitioned tables | Auto-generated template based on table partition columns (first partition column value is bizdatekKey, others are empty) | Y | Linkage logic: partition default values are recalculated and filled after table is switched |
| where | When using WHERE for data filtering, fill in the specific WHERE clause content. Can achieve incremental data filtering based on time range. | N | None (empty string) | Y | |

## Configuration Example

```json
  {
            "stepType": "holo",
            "parameter": {
                "datasource": "holo_db",
                "envType": 1,
                "column": [
                    "tag",
                    "id",
                    "title",
                    "body"
                ],
                "where": "",
                "table": "holo_reader_basic_src"
            },
            "name": "Reader",
            "category": "reader"
        }
```
