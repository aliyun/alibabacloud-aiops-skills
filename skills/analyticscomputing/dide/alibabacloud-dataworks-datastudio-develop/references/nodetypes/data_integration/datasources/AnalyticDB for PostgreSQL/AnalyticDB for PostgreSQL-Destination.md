# Introduction

The AnalyticDB for PostgreSQL data source provides bidirectional functionality for reading from and writing to AnalyticDB for PostgreSQL. This article introduces DataWorks' support for AnalyticDB for PostgreSQL data synchronization capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| schema | The Schema name of the data table to write. | Required when "Table and Schema Separation" configuration is enabled | None | Y | Display condition: When "Table and Schema Separation" configuration is enabled; Linkage logic: Switching clears table |
| table | The selected table name to be synchronized. | Y | None | Y | Linkage logic: After selecting a table, conflict detection column information is loaded (for uniqueIndexColumn and updateColumn) |
| column | The columns in the destination table to write data to, separated by commas. For example `"column":["id","name","age"]`. To write all columns sequentially, use \*, for example `"column":["*"]`. | Y | None | Y |  |
| writeMode | Select the import mode. | Y | copy | Y | Frontend default value: `copy`; Frontend options: `insert (uses insert into ... values ... statement to write data to PostgreSQL)` → `insert`, `copy (uses copy from command to complete mutual copy between table and file)` → `copy` |
| conflictMode | The handling strategy when write data conflicts occur. | Y | reject | Y | **Required field**; Frontend default value: `reject`; Frontend options: `replace (update)` → `replace`, `ignore (ignore)` → `ignore`, `reject (throw exception on conflict)` → `reject` |
| uniqueIndexColumn | Select the columns for conflict detection. When a primary key exists, only the primary key can be selected; when no primary key exists, select a unique index. | N | None | Y | Display condition: When writeMode=insert and conflictMode=replace and the table has a unique index; Options are dynamically loaded from table indexes |
| updateColumn | Select the columns to update when a conflict occurs. If no columns are selected, all non-distribution key columns are updated by default. | N | All non-distribution key columns | Y | Display condition: When writeMode=insert and conflictMode=replace and the table has a unique index; Multi-select |
| preSql | SQL statements executed first before the data synchronization task starts. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple. | N | None | Y |  |
| postSql | SQL statements executed after the data synchronization task completes. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple. | N | None | Y |  |
| addQuote | Whether to add double-quote escaping to table names. | N | None | Y | Display condition: When "Table and Schema Separation" is not enabled |
| encoding | Client connection database encoding configuration. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "parameter": {
                "postSql": [],//Post-import completion statements.
                "datasource": "test_004",//Data source name.
                "column": [//Column names of the destination table.
                    "id",
                    "name",
                    "sex",
                    "salary",
                    "age"
                ],
                "table": "public.person",//Destination table name.
                "preSql": []//Pre-import preparation statements.
            },
            "name": "Writer",
            "category": "writer",
            "stepType": "adbpg"
        }
```
