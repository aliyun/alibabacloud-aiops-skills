# Introduction

This article introduces DataWorks' support for Databricks data synchronization capabilities.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| schema | The selected Schema to be synchronized. | Y | None | Y | Linkage logic: Switching clears table |
| table | The selected table to be synchronized. One job only supports synchronizing one table. | Y | None | Y | |
| column | The set of column names to be synchronized in the configured table, using JSON array to describe field information. * Supports column pruning, i.e., you can export partial columns. * Supports column reordering, i.e., columns can be exported not in the order of the table Schema. * Supports constant configuration, following Databricks SQL syntax format. For example, `["id", "1", "'const name'", "null", "upper('abc_lower')", "2.3" , "true"]`: * id is a regular column name. * 1 is an integer constant. * 'const name' is a string constant (needs to be enclosed in single quotes). * null is a null pointer. * upper('abc_lower') is a function expression. * 2.3 is a floating point number. * true is a boolean value. * column must explicitly specify the set of columns to be synchronized and cannot be empty. | Y | None | Y | |
| readMode | Data read mode. | Y | jdbc | Y | Display condition: Displayed when not in lake mode (hidden when lake mode subType='file'); Frontend default value: `jdbc`; Frontend option: `JDBC (supports data condition filtering)` → `jdbc` |
| splitPk | When Databricks Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. The data synchronization system will launch concurrent tasks for data synchronization to improve efficiency: * It is recommended to use the table primary key as splitPk, because table primary keys are typically more uniform, and the resulting shards are less likely to have data hotspots. * Currently splitPk only supports integer data sharding, and does not support floating point, string, date, and other types. If you specify an unsupported type, Databricks Reader will report an error. | N | None | Y | Display condition: Displayed when readMode=`jdbc`; Linkage logic: After selecting a table, the default value of splitPk is automatically populated |
| where | Filter condition. Databricks Reader concatenates SQL based on the specified column, table, and where conditions, and extracts data accordingly. In actual business scenarios, you typically select data from the current day for synchronization, and can specify the where condition as `gmt_create>$bizdate`. The where condition can effectively perform incremental business synchronization. If this value is empty, it means synchronizing all information in the full table. | N | None | Y | Display condition: Displayed when lake mode (subType='file') or readMode=`jdbc` |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType": "databricks",
      "parameter": {
        "datasource": "",
        "schema": "",
        "table": "",
        "readMode": "jdbc",
        "where": "",
        "splitPk": "",
        "column": [
          "c1",
          "c2"
        ]
      },
      "name": "Reader",
      "category": "reader"
    }
```
