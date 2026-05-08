# Introduction

The PolarDB data source provides you with a bidirectional channel for reading from and writing to PolarDB. You can configure synchronization tasks through wizard mode and script mode.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| searchDbType | Search database type. | Conditionally required | None | Y | Display condition: only displayed when the data source subtype `subType` is `'oms'` or `'dms'`. Component: `SearchDbTypeRadio` (radio button). Linkage logic: switching clears `table` and triggers `model.onTableChange` |
| table | The name of the table to be synchronized. | Y | None | Y | Linkage logic: after table switch, `splitPk` is automatically filled with `tableColumn.splitPk[0]` |
| useReadonly | If you want read-write separation and read data from the PolarDB cluster's replica, set this parameter to true. If not configured, the default is false, meaning data is read from the primary instance. | N | false | Y | Display condition: only displayed when the data source's `hasReadOnly` attribute is `true`. |
| column | The collection of column names to be synchronized in the configured table, using JSON array to describe field information. By default, all columns are configured, for example \[\*\]. * Supports column pruning, meaning you can select partial columns for export. * Supports column reordering, meaning columns can be exported without following the table Schema order. * Supports constant configuration, you need to follow SQL syntax format, for example `["id", "table","1","'mingya.wmy'","'null'", "to_char(a+1)","2.3","true"]`. * id is a regular column name. * table is a column name containing reserved words. * 1 is an integer constant. * 'mingya.wmy' is a string constant (note that a pair of single quotes is required). * 'null' is a string constant. * to_char(a+1) is a string length calculation function. * 2.3 is a floating-point number. * true is a boolean value. * column must explicitly specify the collection of columns to be synchronized and cannot be empty. | Y | None | Y | |
| where | Filter condition. In actual business scenarios, you often select the current day's data for synchronization, specifying the where condition as `gmt_create>$bizdate`. * The where condition can effectively perform business incremental synchronization. If the where statement is not filled in, including not providing the key or value of where, data synchronization is treated as full data synchronization. * Specifying the where condition as limit 10 does not conform to the WHERE clause constraint and is not recommended. | N | None | Y | Linkage: commonly used for incremental synchronization with `gmt_create > $bizdate`. Component: `WhereItem` |
| splitPk | When PolarDB Reader extracts data, if splitPk is specified, it means you want to use the field represented by splitPk for data sharding. Data synchronization will start concurrent tasks to improve data synchronization efficiency. * It is recommended that splitPk users use the table primary key, because the table primary key is usually relatively uniform, so the shards split out are less likely to have data hotspots. * Currently splitPk only supports integer data sharding, and does not support string, floating-point, date, and other types. If you specify an unsupported type, the splitPk function is ignored and single-channel synchronization is used. * If splitPk is not filled in, including not providing splitPk or splitPk value is empty, data synchronization is treated as using a single channel to synchronize the table data. | N | None | Y | Frontend option: dropdown selection (only displays integer fields). Linkage logic: after selecting a table, the first primary key is automatically filled. Component: `SplitPk` |
| splitFactor | Split factor, which can configure the number of splits for synchronized data. If multi-concurrency is configured, splitting will be done by concurrency × splitFactor. For example, if concurrency=5 and splitFactor=5, then 5×5=25 splits will be made and executed on 5 concurrent threads. **Note** Recommended value range: 1~100, too large may cause out of memory. | N | 5 | Y | Frontend default value: 5. Component: `SplitFactor` |
| querySql (Advanced mode, not provided in wizard mode) | In some business scenarios, the where configuration item is not sufficient to describe the filter conditions. You can use this configuration item to customize the filter SQL. When this item is configured, the data synchronization system will ignore the column, table, and where configuration items, and directly use the content of this configuration to filter data. For example, if you need to synchronize data after a multi-table join, use `select a,b from table_a join table_b on table_a.id = table_b.id`. When you configure querySql, PolarDB Reader directly ignores the configuration of column, table, and where conditions. querySql takes priority over table, column, where, and splitPk options. The datasource will use it to parse the username, password, and other information. | N | None | N | Display condition: only script mode/advanced mode supports this parameter, wizard mode does not display it. Linkage: after configuration, table, column, where, and splitPk are ignored |

> Y = Yes, N = No

## Configuration Example

```json
{
            "parameter": {
                "datasource": "test_005",//Data source name.
                "column": [//Source column names.
                    "id",
                    "name",
                    "age",
                    "sex",
                    "salary",
                    "interest"
                ],
                "where": "id=1001",//Filter condition.
                "splitPk": "id",//Split key.
                "table": "PolarDB_person",//Source table name.
              	"useReadonly": "false"//Whether to read data from the replica.
            },
            "name": "Reader",
            "category": "reader",
            "stepType": "polardb"
        }
```
