# Introduction

Data Lake Formation (DLF) is a fully managed unified metadata and data storage and management platform that provides metadata management, storage management, permission management, storage analysis, and storage optimization features. DataWorks Data Integration supports reading from and writing to DLF data sources, and supports Paimon tables, Format tables, and Iceberg tables. This data source only supports use in Data Integration.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | DLF data source name. | Y | None | Y | |
| tableType | Table type. **Must be selected before fetching the table list.** | N | table | Y | Frontend options: `Paimon table` → `table`; `Format table` → `format-table`; `Iceberg table` → `iceberg-table`; Frontend default value: table; Linkage logic: Switching clears table, tableColumn, truncatePartitionConfig, transformationRules, and triggers a table switch event; **The tableType parameter must be passed when calling getTableListPost to filter table types** |
| table | Table name. | Y | None | Y | Prerequisite: tableType must be selected first; Supports automatically creating the destination table from the source table structure |
| column | Column names. | Y | None | Y | |
| emptyString | When source data is an empty string, whether to convert it to a Null value before writing. | N | In-Elastic true, Outside-Elastic false | Y | Display condition: Displayed when not an Iceberg table and not a Format table |
| truncatePartitionConfig | Configuration for clearing partitions before writing. | N | None | Y | Display condition: Displayed when not an Iceberg table, not a Format table, and there are partition columns |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "dlf",
  "parameter": {
    "datasource": "dlf_target",
    "table": "target_table",
    "tableType": "table",
    "column": ["id", "col1", "col2", "col3"]
  },
  "name": "Writer",
  "category": "writer"
}
```
