# Introduction

The AnalyticDB for PostgreSQL data source provides bidirectional functionality for reading from and writing to AnalyticDB for PostgreSQL. This article introduces DataWorks' support for AnalyticDB for PostgreSQL data synchronization capabilities.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| schema | The Schema name of the data table to read. | Required when "Table and Schema Separation" configuration is enabled | None | Y | Display condition: When "Table and Schema Separation" configuration is enabled; Linkage logic: Switching clears table |
| table | The selected table name to be synchronized. | Y | None | Y | Linkage logic: After selecting a table, the default value of splitPk is automatically populated |
| column | The set of column names to be synchronized in the configured table, using JSON array to describe field information. Defaults to all columns, for example \[\*\]. * Supports column pruning, i.e., you can select partial columns for export. * Supports column reordering, i.e., columns can be exported not in the order of the table Schema. * Supports constant configuration, following SQL syntax format. For example, `["id", "table","1","'mingya.wmy'","'null'", "to_char(a+1)","2.3","true"]`. * id is a regular column name. * table is a column name containing a reserved word. * 1 is an integer constant. * 'mingya.wmy' is a string constant (note: needs to be enclosed in single quotes). * 'null' is a string constant. * to_char(a+1) is a string length calculation function. * 2.3 is a floating point number. * true is a boolean value. * column must explicitly specify the set of columns to be synchronized and cannot be empty. | Y | None | Y |  |
| splitPk | When AnalyticDB for PostgreSQL Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will launch concurrent tasks for data synchronization to improve efficiency. * Table primary keys are typically more uniform, and the resulting shards are less likely to have data hotspots, so it is recommended to use the table primary key as splitPk. * Currently splitPk only supports integer data sharding, and does not support string, floating point, date, and other types. If you specify an unsupported type, the splitPk feature is ignored and single-channel synchronization is used. * If splitPk is not specified, including not providing splitPk or having an empty splitPk value, data synchronization uses single-channel synchronization for the table data. | N | None | Y | Linkage logic: After selecting a table, splitPk default value is automatically populated (from tableColumn.splitPk[0]); User's original value is preserved during echo display |
| where | Filter condition. AnalyticDB for PostgreSQL Reader concatenates SQL based on the specified column, table, and where conditions, and extracts data accordingly. For example, during testing, you can specify the where condition for actual business scenarios, which often select the current day's data for synchronization, specifying the where condition as `id>2 and sex=1`. * The where condition can effectively perform incremental business synchronization. * If the where condition is not configured or is empty, full table synchronization is performed. | N | None | Y |  |
| addQuote | Whether to add double-quote escaping to table names. | N | None | Y | Display condition: When "Table and Schema Separation" is not enabled |
| useReadOnly | Whether to preferentially read data from read-only nodes. | N | None | Y | Display condition: When the data source has read-only nodes enabled |
| encoding | Client connection database encoding configuration. | N | None | Y |  |
| socketTimeout | Timeout for the connection between the client and the database, in milliseconds. | N | None | Y |  |
| fetchSize | This configuration item defines the number of records retrieved per batch between the plugin and the database server. This value determines the number of network interactions between Data Integration and the server, and can improve data extraction performance. **Note** A fetchSize value that is too large (>2048) may cause OOM in the data synchronization process. | N | 1024 | Y |  |
| querySql | In some business scenarios, the where configuration item is not sufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. When this item is configured, the data synchronization system ignores column, table, splitPk, and other configuration items, and directly uses the content of this configuration to filter data. For example, when you need to synchronize data after a multi-table join, use `select a,b from table_a join table_b on table_a.id = table_b.id`. When you configure querySql, AnalyticDB for PostgreSQL Reader directly ignores the column, table, and where condition configurations. | N | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "parameter": {
                "datasource": "test_004",//Data source name.
                "column": [//Column names of the source table.
                    "id",
                    "name",
                    "sex",
                    "salary",
                    "age"
                ],
                "where": "id=1001",//Filter condition.
                "splitPk": "id",//Split key.
                "table": "public.person"//Source table name.
            },
            "name": "Reader",
            "category": "reader",
            "stepType": "adbpg"
        }
```
