# Introduction

The MariaDB data source provides you with a bidirectional channel for reading from and writing to MariaDB. This article introduces the MariaDB data synchronization capabilities of DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | N |  |
| table | The name of the table to be synchronized. A data integration task can only synchronize data to one destination table. **table** advanced usage examples for range configuration are as follows: * You can read from sharded tables by configuring ranges, for example **'table_\[0-99\]'** means reading **'table_0'** , **'table_1'** , **'table_2'** through **'table_99'** . * If the numeric suffixes of your tables have consistent lengths, for example **'table_000'** , **'table_001'** , **'table_002'** through **'table_999'** , you can configure it as **'"table": \["table_00\[0-9\]", "table_0\[10-99\]", "table_\[100-999\]"\]'** . **Note** The task will read all matched tables, specifically reading the columns specified by the **column** configuration item in these tables. If a table does not exist, or the column to be read does not exist, the task will fail. | Y | None | N |  |
| column | The collection of column names to be synchronized in the configured table, using JSON array to describe field information. By default, all columns are configured, for example \[ \* \]. * Supports column pruning: you can select partial columns for export. * Supports column reordering: columns can be exported without following the table schema order. * Supports constant configuration: you need to follow MariaDB SQL syntax format, for example **\["id","table","1","'mingya.wmy'","'null'","to_char(a+1)","2.3","true"\]** . * **id** is a regular column name. * **table** is a column name containing reserved words. * **1** is an integer constant. * **'mingya.wmy'** is a string constant (note that a pair of single quotes is required). * About **null** : * **" "** means empty. * **null** means null. * **'null'** means the string "null". * **to_char(a+1)** is a string length calculation function. * **2.3** is a floating-point number. * **true** is a boolean value. * **column** must explicitly specify the collection of columns to be synchronized and cannot be empty. | Y | None | N |  |
| splitPk | When MariaDB Reader extracts data, if **splitPk** is specified, it means you want to use the field represented by **splitPk** for data sharding. Data synchronization will then start concurrent tasks for data synchronization, improving data synchronization efficiency. * It is recommended that **splitPk** users use the table primary key, because the table primary key is usually relatively uniform, so the shards split out are less likely to have data hotspots. * Currently **splitPk** only supports integer data sharding, and does not support string, floating-point, date, and other types. If you specify an unsupported type, the **splitPk** function is ignored and single-channel synchronization is used. * If **splitPk** is not filled in, including not providing **splitPk** or **splitPk** value is empty, data synchronization is treated as using a single channel to synchronize the table data. | N | None | N |  |
| where | Filter condition. In actual business scenarios, you often select the current day's data for synchronization, specifying the **where** condition as **gmt_create\>$bizdate** . * The **where** condition can effectively perform business incremental synchronization. If the **where** statement is not filled in, including not providing the **key** or **value** of **where** , data synchronization is treated as full data synchronization. * You cannot specify the **where** condition as limit 10, which does not conform to the MariaDB SQL **where** clause constraint. | N | None | N |  |
| **querySql** (Advanced mode, wizard mode does not support configuration of this parameter) | In some business scenarios, the **where** configuration item is not sufficient to describe the filter conditions. You can define the filter SQL through this configuration item. When this item is configured, the data synchronization system will ignore the **tables** , **columns** , and **splitPk** configuration items, and directly use the content of this configuration item to filter data. For example, if you need to synchronize data after a multi-table join, use **select a,b from table_a join table_b on table_a.id = table_b.id** . When you configure **querySql** , MariaDB Reader directly ignores the configuration of **table, column, where** and **splitPk** conditions. **querySql** takes priority over **table** , **column** , **where** , and **splitPk** options. **datasource** uses it to parse the username, password, and other information. **Note** **querySql** is case-sensitive. For example, writing it as **querysql** will not take effect. | N | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"mariadb",//Plugin name.
            "parameter":{
                "column":[//Column names.
                    "id"
                ],
                "connection":[
                    {   "querySql":["select a,b from join1 c join join2 d on c.id = d.id;"], //Use string format to write querySql in connection.
                        "datasource":"",//Data source.
                        "table":[//Table name, even if there is only one table, it must be written in [] array format.
                            "xxx"
                        ]
                    }
                ],
                "where":"",//Filter condition.
                "splitPk":"",//Split key.
                "encoding":"UTF-8"//Encoding format.
            },
            "name":"Reader",
            "category":"reader"
        }
```
