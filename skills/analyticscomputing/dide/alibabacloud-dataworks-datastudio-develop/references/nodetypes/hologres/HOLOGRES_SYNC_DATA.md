# MaxCompute to Hologres Data Sync（HOLOGRES_SYNC_DATA）

## Overview

- Compute engine: `HOLO`
- Content format: json
- Extension: `.hologres.data.sync.json`
- Data source type: `hologres`
- Code: 1095
- Description: MaxCompute to Hologres data sync node

The HOLOGRES_SYNC_DATA node is used to sync data from MaxCompute (ODPS) to the Hologres real-time data warehouse. Through configuration, MaxCompute offline data can be efficiently imported into Hologres, bridging offline to real-time data. Both full and incremental sync modes are supported.

## Prerequisites

- Hologres and MaxCompute compute engines have been bound in the DataWorks workspace
- MaxCompute source tables and Hologres target tables have been created
- MaxCompute and Hologres data source connections have been configured
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### Configuration Structure

The node content is in JSON format, defining the data sync configuration from MaxCompute to Hologres:

```json
{
  "type": "HOLOGRES_SYNC_DATA",
  "source": {
    "datasource": "odps_datasource",
    "table": "mc_source_table",
    "partition": "ds=${bizdate}"
  },
  "target": {
    "datasource": "hologres_datasource",
    "table": "holo_target_table",
    "writeMode": "INSERT_OR_REPLACE"
  },
  "columnMapping": [
    {"source": "user_id", "target": "user_id"},
    {"source": "user_name", "target": "user_name"},
    {"source": "amount", "target": "amount"}
  ]
}
```

### Sync Modes

- **Full sync**: Imports all data from the specified MaxCompute partition into Hologres at once
- **Incremental sync**: Combined with scheduling parameters (e.g., `${bizdate}`), incrementally syncs new data by partition
- **Overwrite**: Clears the target table data before writing
- **Append**: Appends new records on top of existing data

### Field Mapping

Supports field mapping configuration between source and target tables, allowing field renaming and type conversion.

## Restrictions

- MaxCompute and Hologres must be in the same region
- It is recommended to configure concurrency appropriately when syncing large data volumes
- The sync configuration is in JSON format, with extension `.hologres.data.sync.json`

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_hologres_sync_data",
        "script": {
          "path": "example_hologres_sync_data",
          "runtime": {
            "command": "HOLOGRES_SYNC_DATA"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Sync Data from MaxCompute to Hologres](https://help.aliyun.com/zh/dataworks/user-guide/synchronize-data-from-maxcompute-to-hologres)
