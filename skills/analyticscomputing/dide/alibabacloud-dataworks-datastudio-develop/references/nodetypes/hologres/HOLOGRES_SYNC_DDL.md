# MaxCompute to Hologres Table Schema Sync（HOLOGRES_SYNC_DDL）

## Overview

- Compute engine: `HOLO`
- Content format: json
- Extension: `.hologres.ddl.sync.json`
- Data source type: `hologres`
- Code: 1094
- Description: MaxCompute to Hologres table schema (DDL) sync node

The HOLOGRES_SYNC_DDL node is used to automatically sync MaxCompute table schema definitions (DDL) to Hologres. This node reads the schema information of the MaxCompute source table (field names, field types, comments, etc.) and automatically creates or updates the corresponding table structure in Hologres, eliminating the need to manually recreate tables in Hologres.

## Prerequisites

- Hologres and MaxCompute compute engines have been bound in the DataWorks workspace
- MaxCompute source tables have been created
- MaxCompute and Hologres data source connections have been configured
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### Configuration Structure

The node content is in JSON format, defining the source and target configuration for table schema sync:

```json
{
  "type": "HOLOGRES_SYNC_DDL",
  "source": {
    "datasource": "odps_datasource",
    "table": "mc_source_table"
  },
  "target": {
    "datasource": "hologres_datasource",
    "table": "holo_target_table",
    "schema": "public"
  },
  "options": {
    "ifNotExists": true,
    "orientation": "column",
    "tableGroup": "default"
  }
}
```

### Sync Content

The table schema sync includes the following elements:

- **Field definitions**: Field names, data types (automatic type mapping)
- **Field comments**: COMMENT information from MaxCompute fields
- **Primary key constraints**: If the source table has primary key definitions, they are synced as well
- **Partition information**: Handling of MaxCompute partition fields

### Type Mapping

Common type mappings from MaxCompute to Hologres:

| MaxCompute Type | Hologres Type |
|----------------|--------------|
| STRING | TEXT |
| BIGINT | BIGINT |
| INT | INT |
| DOUBLE | DOUBLE PRECISION |
| DECIMAL | NUMERIC |
| BOOLEAN | BOOLEAN |
| DATETIME | TIMESTAMPTZ |
| DATE | DATE |

### Applicable Scenarios

- **Unified table creation**: After defining table structures in MaxCompute, automatically sync them to Hologres
- **Schema change sync**: Automatically update Hologres tables when MaxCompute table structures change
- **Batch table creation**: Combined with scheduling, sync the schema of a large number of tables

## Restrictions

- Only syncs table schema, not data (for data sync, use HOLOGRES_SYNC_DATA)
- MaxCompute and Hologres must be in the same region
- Some MaxCompute-specific data types may not be directly mappable to Hologres
- The sync configuration is in JSON format, with extension `.hologres.ddl.sync.json`

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_hologres_sync_ddl",
        "script": {
          "path": "example_hologres_sync_ddl",
          "runtime": {
            "command": "HOLOGRES_SYNC_DDL"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Sync Table Schema from MaxCompute to Hologres](https://help.aliyun.com/zh/dataworks/user-guide/synchronize-table-structures-from-maxcompute-to-hologres)
