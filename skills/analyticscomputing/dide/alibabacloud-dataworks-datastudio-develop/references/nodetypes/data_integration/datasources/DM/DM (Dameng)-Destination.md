# Introduction

The DM (Dameng) data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to DM databases, enabling rapid resolution of massive data computation problems. This article introduces the DM data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| schema | The Schema name of the target table. | Y | None | Y | Linkage logic: switching clears table |
| table | Target table name. | Y | None | Y | |
| column | The fields in the target table that need to be written with data, separated by English commas. | Y | None | Y | |
| preSql | SQL statements executed before the data synchronization task starts. | N | None | Y | |
| postSql | SQL statements executed after the data synchronization task completes. | N | None | Y | |
| batchSize | The number of records submitted in a single batch. | N | 1,024 | Y | |
| addQuote | Whether to add double-quote escaping to table names. | N | true | Y | Frontend default value: `true` |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "dm",
            "parameter": {
                "datasource": "dm_datasource",
                "table": "table",
                "column": [
                   "id",
                  "name"
                ],
                "preSql": [
                    "delete from XXX;"
                ]
            },
            "name": "Writer",
            "category": "writer"
        }
```
