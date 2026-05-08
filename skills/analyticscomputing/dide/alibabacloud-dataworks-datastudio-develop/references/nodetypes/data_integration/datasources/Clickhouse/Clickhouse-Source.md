# Introduction

The ClickHouse data source provides you with a bidirectional channel for reading from and writing to ClickHouse. This article introduces DataWorks' support for ClickHouse data synchronization capabilities.

# Source
## Parameter Description
| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. The value must be consistent with the name of the added data source. | Y | None | Y | |
| table | The selected table to be synchronized. | Y | None | Y | Linkage logic: After selecting a table, splitPk is automatically retrieved and populated (using the first sharding key of the table) |
| column | The fields to read, with multiple fields separated by commas. This configuration item must be specified and cannot be empty. | Y | None | Y | |
| splitPk | Data sharding field. When specified, concurrent tasks are launched to improve synchronization efficiency. | N | First sharding key of the table | Y | Linkage logic: After table switch, the first sharding key is automatically populated |
| where | Filter condition, commonly used for incremental business synchronization. When not specified, full data synchronization is performed by default. | N | None | Y | |

## Configuration Example

```json
{
            "stepType": "clickhouse",
            "parameter": {
                "datasource": "example",
                "column": [
                    "id",
                    "name"
                ],
                "where": "",
                "splitPk": "",
                "table": ""
            },
            "name": "Reader",
            "category": "reader"
        }
```
