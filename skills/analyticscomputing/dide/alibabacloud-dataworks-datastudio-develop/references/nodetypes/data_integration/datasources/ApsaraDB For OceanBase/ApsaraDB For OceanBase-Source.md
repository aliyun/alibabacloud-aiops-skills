# Introduction

The ApsaraDB for OceanBase data source provides bidirectional functionality for reading from and writing to ApsaraDB for OceanBase data. You can use the ApsaraDB for OceanBase data source to configure synchronization tasks to sync data. This article introduces DataWorks' support for ApsaraDB for OceanBase data synchronization capabilities.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| searchDbType | The database type to search. | Required when subType is oms or dms | None | Y | Display condition: Outside elastic environment and data source subType is oms or dms; Not displayed inside elastic environment; Linkage logic: Switching clears table |
| table | The selected table to be synchronized. Described using JSON array, supports reading multiple tables simultaneously. When configuring multiple tables, you must ensure that the Schema structure of all tables is consistent. ApsaraDB For OceanBase Reader does not check whether the table logic is uniform. **Note** table must be included in the connection configuration unit. | Y | None | Y | Linkage logic: After selecting a table, the default value of splitPk is automatically populated |
| column | The set of column names to be synchronized in the configured table, using JSON array to describe field information. Defaults to all columns, for example \[ \* \]. * Supports column pruning: can export partial columns. * Supports column reordering: can export columns not in the order of the table Schema information. * Supports constant configuration: for example `'123'`. * Supports function columns: for example `date('now')`. * column must explicitly specify the set of columns to be synchronized and cannot be empty. | Y | None | Y |  |
| splitPk | When ApsaraDB For OceanBase Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will launch concurrent tasks to improve synchronization efficiency. * It is recommended to use the table primary key as splitPk, because table primary keys are typically more uniform, and the resulting shards are less likely to have data hotspots. * Currently splitPk only supports integer data sharding, and does not support string, floating point, date, and other types. If you specify an unsupported type, ApsaraDB For OceanBase Reader will report an error. * If splitPk is set to an empty value, the system treats it as not allowing single-table sharding, and uses single-channel extraction. | N | None | Y | Linkage logic: After selecting a table, splitPk default value is automatically populated (from tableColumn.splitPk[0]); User's original value is preserved during echo display |
| where | ApsaraDB For OceanBase Reader concatenates SQL based on the specified column, table, and where conditions, and extracts data accordingly. For example, during testing, you can specify the where condition as `limit 10`. In actual business scenarios, you typically select data from the current day for synchronization, specifying the where condition as `gmt_create>$bizdate`. * The where condition can effectively perform incremental business synchronization. * If the where condition is not configured or is empty, full table synchronization is performed. | N | None | Y |  |
| querySql | In some business scenarios, the where configuration item is not sufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. When this item is configured, the data synchronization system ignores tables, columns, and splitPk configuration items, and directly uses the content of this configuration to filter data. When you configure querySql, ApsaraDB For OceanBase Reader directly ignores the table, column, where, and splitPk condition configurations. | N | None | N |  |
| weakRead | Consistency read configuration. | N | true | Y | Frontend default value: `true` (weak consistency); Frontend options: `Weak consistency` → `true`, `Strong consistency` → `false` |
| readByPartition | Whether to read data by partition. | N | false | Y | Frontend default value: `false` (No); Frontend options: `Yes` → `true`, `No` → `false` |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "apsaradb_for_OceanBase", //Plugin name
            "parameter": {
                "datasource": "", //Data source name
                "where": "",
                "column": [ //Fields
                    "id",
                    "name"
                ],
                "splitPk": ""
            },
            "name": "Reader",
            "category": "reader"
        }
```
