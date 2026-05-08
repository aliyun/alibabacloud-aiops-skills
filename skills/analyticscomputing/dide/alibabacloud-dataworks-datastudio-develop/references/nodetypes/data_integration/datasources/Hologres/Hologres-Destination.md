# Introduction

The Hologres data source provides you with a bidirectional channel for reading from and writing to Hologres. This article introduces the Hologres data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | The Hologres data source name configured in DataWorks. | Y | None | Y | |
| selectedDatabase | The name of the schema name within the Hologres instance. | Depends on data source type | None | Y | Linkage logic: switching clears table and transformationRules |
| table | The Hologres table name. Supports including Schema (e.g., `schema_name.table_name`). | Y | None | Y | Linkage logic: after selecting a table, partition column information is fetched and the partition default value is auto-filled; supports automatically creating the target table from the source table structure |
| column | Defines the data columns to import into the target table. Must include the primary key set of the target table. For example, `["*"]` means all columns. | Y | None | Y | |
| conflictMode | Data conflict handling strategy. | Y | ignore | Y | Frontend options: `Replace` → `replace`; `Ignore` → `ignore`; `Update` → `update`; Frontend default value: ignore |
| writeMode | Write mode. | N | insert | Y | Frontend options: `SQL(INSERT INTO)` → `insert`; `SDK` → `sdk`; Frontend default value: insert |
| truncate | Clear the Hologres table before synchronization. | N | false | Y | Frontend options: `Do Not Clear Target Table` → `false`; `Clear Target Table` → `true`; Frontend default value: false |
| maxConnectionCount | Maximum number of connections. | N | None | Y | |

## Configuration Example

```json
{
            "stepType": "holo",
            "parameter": {
                "selectedDatabase":"public",
                "schema": "public",
                "maxConnectionCount": 9,
                "truncate":true,
                "datasource": "<holo_sink_name>",
                "conflictMode": "ignore",
                "envType": 0,
                "column": [
                    "<column1>",
                    "<column2>",
                    "<columnN>"
                ],
                "tableComment": "",
                "table": "<holo_table_name>"
            }
}
```
