# Introduction

The ClickHouse data source provides you with a bidirectional channel for reading from and writing to ClickHouse. This article introduces DataWorks' support for ClickHouse data synchronization capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. The value must be consistent with the name of the added data source. | Y | None | Y | |
| table | The table name to write synchronized data to. | Y | None | Y | |
| column | The columns in the destination table to write data to, separated by commas. This configuration item must be specified and cannot be empty. | Y | None | Y | |
| writeMode | The SQL statement used when writing to ClickHouse. | Y | insert | Y | Frontend option: `insert into (report dirty data on primary key/constraint conflict)` → `insert`; Frontend default value: insert |
| preSql | Standard SQL statements executed first before writing data to the destination table. | N | None | Y | Supports multiple SQL statements |
| postSql | Standard SQL statements executed after writing data to the destination table. | N | None | Y | Supports multiple SQL statements |
| batchByteSize | The byte size for one-time batch submission. | N | 16777216 | Y | Unit: bytes; Frontend default value: 16777216 |
| batchSize | The batch size for one-time submission of records, which can reduce network interaction times and improve overall throughput. Setting this too large may cause OOM errors in the synchronization process. | N | 65536 | Y | Unit: records; Frontend default value: 65536 |
| strategyOnError | The handling strategy for batch write exceptions. | Y | singleInsert | Y | Frontend options: `Attempt single-row write, count as dirty data if single-row write still fails` → `singleInsert`; `Exit synchronization task with failure` → `exit`; `Count batch data as dirty data` → `batchDirtyData`; Frontend default value: singleInsert |

## Configuration Example

```json
{
            "stepType": "clickhouse",
            "parameter": {
                "postSql": [
                    "update @table set db_modify_time = now() where db_id = 1"
                ],
                "datasource": "example",
                "column": [
                    "id",
                    "name"
                ],
                "writeMode": "insert",
                "encoding": "UTF-8",
                "batchSize": 1024,
                "table": "ClickHouse_table",
                "preSql": [
                    "delete from @table where db_id = -1"
                ]
            },
            "name": "Writer",
            "category": "writer"
        }
```
