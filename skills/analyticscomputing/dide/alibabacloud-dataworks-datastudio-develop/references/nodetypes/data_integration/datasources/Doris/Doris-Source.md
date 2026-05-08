# Introduction

DataWorks Data Integration supports using Doris Writer to import table data into Doris. This article introduces the Doris data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the table selected for synchronization. A single data integration task can only read data from one table. | Y | None | Y | Linkage logic: selecting a table auto-fills the default value of splitPk |
| column | The set of column names in the configured table that need to be synchronized, described using a JSON array. By default, all columns are configured, for example `[ * ]`. * Supports column pruning: you can select partial columns for export. * Supports column reordering: columns can be exported in an order different from the table schema. * Supports constant configuration: you need to follow the Doris SQL syntax format. | Y | None | Y | |
| splitPk | When Doris Reader performs data extraction, if **splitPk** is specified, it indicates that you want to use the field represented by **splitPk** for data sharding. * It is recommended to use the table primary key for **splitPk**. * Currently, **splitPk** only supports integer data sharding. * If **splitPk** is not specified, a single channel is used to synchronize the table data. | N | None | Y | Linkage logic: selecting a table auto-fills the default value of splitPk (from `tableColumn.splitPk[0]`) |
| where | Filter condition. In actual business scenarios, the current day's data is often selected for synchronization. * The **where** condition can effectively perform incremental business synchronization. | N | None | Y | |
| querySql | In some business scenarios, the where configuration item is insufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. After configuring this item, the data synchronization system will ignore the tables, columns, and splitPk configuration items. When you configure **querySql**, Doris Reader directly ignores the table, column, where, and splitPk condition configurations. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType": "doris",//Plugin name.
      "parameter": {
        "column": [//Column names.
          "id"
        ],
        "connection": [
          {
            "querySql": [
              "select a,b from join1 c join join2 d on c.id = d.id;"
            ],
            "datasource": ""//Data source name.
          }
        ],
        "where": "",//Filter condition.
        "splitPk": "",//Split key.
        "encoding": "UTF-8"//Encoding format.
      },
      "name": "Reader",
      "category": "reader"
    }
```
