# Introduction

The PolarDB-X 2.0 data source provides you with a bidirectional channel for reading from and writing to PolarDB-X 2.0. This article introduces the PolarDB-X 2.0 data synchronization capabilities of DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. This name must be consistent with the PolarDB-X 2.0 data source name created in the Data Source Management interface. | Y | None | Y | |
| table | The name of the table to be synchronized. Only single table is supported. | Y | None | Y | Linkage logic: after selecting a table, column information is automatically fetched and the column mapping component is notified to update the Schema, while the first column is taken as the splitPk default value. |
| column | The collection of column names to be synchronized in the configured table, using JSON array to describe field information. By default, all columns are configured, for example `["*"]`. * Supports column pruning: you can select partial columns for synchronization. * Supports column reordering: columns can be synchronized without following the table Schema order. * Supports constant configuration: you need to follow the format such as `["id","table","1","'mingya.wmy'","'null'","to_char(a+1)","2.3","true"]`. * **id** is a regular column name. * **table** is a column name containing reserved words. * **1** is an integer constant. * **'mingya.wmy'** is a string constant (note that a pair of single quotes is required). * About **null** : * **" "** means empty. * **null** means null. * **'null'** means the string "null". * **to_char(a+1)** is a string length calculation function. * **2.3** is a floating-point number. * **true** is a boolean value. * **column** must explicitly specify the collection of columns to be synchronized and cannot be empty. | Y | None | Y | |
| where | Filter condition. In actual business scenarios, you often select the current day's data for synchronization, specifying the **where** condition as `gmt_create>$bizdate` . * The **where** condition can effectively perform business incremental synchronization. If the **where** condition is not filled in, including not providing the **key** or **value** of **where** , data synchronization is treated as full data synchronization. * You cannot specify the **where** condition as `LIMIT 10`, which does not conform to the PolarDB-X 2.0 SQL **WHERE** clause constraint. | N | None | Y | |
| splitPk | When using PolarDB-X 2.0 Reader to extract data, you can use the **splitPk** field for data sharding to achieve concurrent data synchronization and improve synchronization efficiency. * (Recommended) Set **splitPk** to the table primary key. Shards split by the table primary key are relatively uniform and less likely to have data hotspots. * **splitPk** only supports integer data sharding, and does not support string, floating-point, date, and other types. If an unsupported type is used, the platform will ignore the **splitPk** function and use single-channel data synchronization. * If the **splitPk** parameter is not configured (i.e., the Reader script does not include this parameter) or the **splitPk** parameter value is empty, the platform will use single-channel data synchronization. | N | None | Y | Linkage logic: after selecting a table, the first column is automatically taken as the default value. |
| checkSlave | Database master-slave delay check. When the data source uses a PolarDB-X 2.0 read-only instance, before the task starts, it checks the delay time between the read-only instance and the primary instance to avoid data loss caused by master-slave delay. | N | true | Y | Linkage logic: when true, slaveDelayLimit is displayed. |
| slaveDelayLimit | In seconds, checks the delay time between the read-only instance and the primary instance. When the delay time exceeds this configuration, the task fails. | N | 300 | Y | Display condition: displayed when checkSlave is true; frontend default value: 300; unit: seconds. |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"polardbx20",//Plugin name.
            "parameter":{
               "connection": [
                  {
                      "datasource":"",
                      "table": [
                          "t1"
                      ]
                  }
              ],
              "column": [
                  "c1",
                  "c2",
                  "'const'"
              ],
              "where": "",
              "splitPk": "",
              "checkSlave": "true",
              "slaveDelayLimit": "300"
            },
            "name":"Reader",
            "category":"reader"
        }
```
