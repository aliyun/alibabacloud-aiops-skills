# Hologres to MaxCompute Data Sync（HOLOGRES_SYNC_DATA_TO_MC）

## Overview

- Compute engine: `HOLO`
- Content format: json
- Extension: `.hologres.data.sync.json`
- Data source type: `hologres`
- Code: 1070
- Description: Hologres to MaxCompute data sync node

The HOLOGRES_SYNC_DATA_TO_MC node is used to reverse-sync data from the Hologres real-time data warehouse to MaxCompute. This node is suitable for archiving processed results from the real-time data warehouse to the offline data warehouse, or exporting aggregated data from Hologres to MaxCompute for further offline analysis and long-term storage.

## Prerequisites

- Hologres and MaxCompute compute engines have been bound in the DataWorks workspace
- Hologres source tables and MaxCompute target tables have been created
- Hologres and MaxCompute data source connections have been configured
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### Configuration Structure

The node content is in JSON format, defining the data sync configuration from Hologres to MaxCompute:

```json
{
  "type": "HOLOGRES_SYNC_DATA_TO_MC",
  "source": {
    "datasource": "hologres_datasource",
    "table": "holo_source_table"
  },
  "target": {
    "datasource": "odps_datasource",
    "table": "mc_target_table",
    "partition": "ds=${bizdate}",
    "writeMode": "OVERWRITE"
  },
  "columnMapping": [
    {"source": "user_id", "target": "user_id"},
    {"source": "total_amount", "target": "total_amount"},
    {"source": "update_time", "target": "update_time"}
  ]
}
```

### Applicable Scenarios

- **Data archival**: Archive hot data from Hologres to MaxCompute cold storage
- **Offline analysis**: Export real-time processing results to MaxCompute for complex offline analysis
- **Data backup**: Back up critical Hologres data to MaxCompute
- **Cross-engine sharing**: Make Hologres data available to downstream tasks based on MaxCompute

### Write Modes

- **OVERWRITE**: Overwrite data in the target partition
- **APPEND**: Append data to the target partition

## Restrictions

- Hologres and MaxCompute must be in the same region
- When syncing large data volumes, pay attention to the impact on Hologres source query performance
- The sync configuration is in JSON format, with extension `.hologres.data.sync.json`

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_hologres_sync_data_to_mc",
        "script": {
          "path": "example_hologres_sync_data_to_mc",
          "runtime": {
            "command": "HOLOGRES_SYNC_DATA_TO_MC"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Sync Data from Hologres to MaxCompute](https://help.aliyun.com/zh/dataworks/user-guide/synchronize-data-from-hologres-to-maxcompute)
