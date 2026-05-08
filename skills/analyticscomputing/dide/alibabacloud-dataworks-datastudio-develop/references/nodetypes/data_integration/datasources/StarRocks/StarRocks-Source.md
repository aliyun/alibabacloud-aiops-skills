# Introduction

The StarRocks data source provides you with bidirectional read and write capabilities for StarRocks. This article introduces the data synchronization capabilities of DataWorks for StarRocks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | StarRocks data source name. | Y | None | Y |  |
| selectedDatabase | StarRocks database name. | N | The database name configured in the StarRocks data source. | Y |  |
| column | The collection of column names to be synced in the configured table. | Y | None | Y |  |
| where | Filter condition. In real business scenarios, you often select the current day's data for synchronization, specifying the where condition as `gmt_create>$bizdate`. * The where condition can effectively perform business incremental sync. * Without a where statement, including not providing the where key or value, data synchronization treats it as syncing all data. | N | None | Y |  |
| table | The name of the selected table to be synced. | Y | None | Y |  |
| splitPk | When StarRocks Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will then start concurrent tasks to improve data synchronization efficiency. It is recommended to use the table primary key as splitPk, because the primary key is usually relatively uniform, so the resulting shards are less likely to have data hotspots. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
    "stepType": "starrocks",
    "parameter": {
        "selectedDatabase": "didb1",
        "datasource": "starrocks_datasource",
        "column": [
            "id",
            "name"
        ],
        "where": "id>100",
        "table": "table1",
        "splitPk": "id"
    },
    "name": "Reader",
    "category": "reader"
}
```
