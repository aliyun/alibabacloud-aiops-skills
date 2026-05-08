# Introduction

Data Lake Formation (DLF) is a fully managed unified metadata and data storage and management platform that provides metadata management, storage management, permission management, storage analysis, and storage optimization features. DataWorks Data Integration supports reading from and writing to DLF data sources, and supports Paimon tables, Format tables, and Iceberg tables. This data source only supports use in Data Integration.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | DLF data source name. | Y | None | Y | |
| tableType | Table type. **Must be selected before fetching the table list.** | N | table | Y | Frontend options: `Paimon table` → `table`; `Format table` → `format-table`; `Iceberg table` → `iceberg-table`; Frontend default value: table; Linkage logic: Switching clears table, tableColumn, and triggers a table switch event; **The tableType parameter must be passed when calling getTableListPost to filter table types** |
| table | Table name. | Y | None | Y | Prerequisite: tableType must be selected first |
| column | Column names. | Y | None | Y | |
| where | Filter condition. | N | None | Y | Display condition: Supported when tableType=table (Paimon table); The fields used must participate in the column mapping for synchronization |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "dlf",
  "parameter": {
    "datasource": "dlf_source",
    "table": "source_table",
    "tableType": "table",
    "column": ["id", "col1", "col2", "col3"],
    "where": "id > 1"
  },
  "name": "Reader",
  "category": "reader"
}
```
