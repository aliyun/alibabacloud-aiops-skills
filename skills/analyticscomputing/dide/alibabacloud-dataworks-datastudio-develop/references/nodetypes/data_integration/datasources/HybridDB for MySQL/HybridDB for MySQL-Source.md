# Introduction

The HybridDB for MySQL data source provides you with bidirectional capabilities for reading from and writing to HybridDB for MySQL. This article introduces the HybridDB for MySQL data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| searchDbType | Table selection mode: logical database or physical database. | N | 'logic' | Y | Display condition: displayed when the data source subtype is 'oms' or 'dms'; Frontend options: 'logic' → 'Logical Database'; 'physics' → 'Physical Database'; Linkage logic: switching clears table and triggers onTableChange. |
| table | The name of the table selected for synchronization. A single data integration task can only synchronize data to one target table. | Y | None | Y | Linkage logic: after selecting a table, column information is automatically fetched and the column mapping component is notified to update the Schema, and the first column is used as the default value for splitPk. |
| where | Filter condition. In actual business scenarios, the current day's data is often selected for synchronization, and the where condition is specified as `gmt_create>$bizdate`. * The where condition can effectively perform incremental business synchronization. If the where statement is not filled in, including not providing the where key or value, data synchronization will be treated as full data synchronization. | N | None | Y | |
| splitPk | When HybridDB for MySQL Reader performs data extraction, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will launch concurrent tasks to improve efficiency. * It is recommended to use the table primary key for splitPk, as the primary key is typically evenly distributed, and the resulting shards are less likely to have data hotspots. * Currently, splitPk only supports integer data sharding; it does not support string, floating-point, date, or other types. | N | None | Y | Linkage logic: after selecting a table, the first column of the table is automatically taken as the default value (non-initialization scenario). |
| splitFactor | Split factor. You can configure the number of splits for synchronized data. If multiple concurrency is configured, the data will be split into concurrency * splitFactor parts. For example, concurrency=5, splitFactor=5, then the data will be split into 5*5=25 parts, executed on 5 concurrent threads. | N | 5 | Y | Recommended range: 1-100. Setting it too large may cause out-of-memory errors. |
| useReadOnly | Read from standby database first. | N | true | Y | Display condition: displayed when the data source hasReadOnly is true. |
| canReadPrimary | The processing method when reading from the standby database fails. | N | false | Y | Display condition: displayed when the data source hasReadOnly is true and useReadOnly is true; Frontend options: true → 'Switch to Reading from Primary Database'; false → 'Task Fails Directly, Does Not Read Primary Database'. |
| column | The set of column names in the configured table that need to be synchronized, described using a JSON array. By default, all columns are configured, for example `["*"]`. * Supports column pruning: you can select partial columns for export. * Supports column reordering: columns can be exported in an order different from the table Schema. * Supports constant configuration. * column must explicitly specify the set of columns to synchronize and cannot be empty. | Y | None | Y | |
| querySql | In some business scenarios, the where configuration item is insufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. After configuring this item, the data synchronization system will ignore the column, table, and where configuration items, and directly use the content of this configuration to filter data. When you configure querySql, HybridDB for MySQL Reader directly ignores the column, table, where, and splitPk condition configurations. | N | None | N | |
| singleOrMulti | Indicates sharded databases and tables. In wizard mode, converting to script mode proactively generates this configuration `"singleOrMulti":"multi"`, but configuring a script task template will not directly generate this configuration. You need to add it manually; otherwise, only the first data source will be recognized. | Y | multi | Y | Only used by the frontend; the backend does not use this for sharded database/table determination. |

> Y = Yes, N = No

## Configuration Example

```json
{
            "parameter": {
                "datasource": "px_aliyun_hymysql",//Data source name.
                "column": [//Source column names.
                    "id",
                    "name",
                    "sex",
                    "salary",
                    "age",
                    "pt"
                ],
                "where": "id=10001",//Filter condition.
                "splitPk": "id",//Split key.
                "table": "person"//Source table name.
            },
            "name": "Reader",
            "category": "reader",
            "stepType": "hybriddb"
        }
```
