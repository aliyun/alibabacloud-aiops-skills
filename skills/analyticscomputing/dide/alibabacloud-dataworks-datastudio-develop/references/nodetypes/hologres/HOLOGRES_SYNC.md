# Hologres Data Sync（HOLOGRES_SYNC）

## Overview

- Compute engine: `HOLO`
- Content format: json
- Extension: `.json`
- Data source type: `hologres`
- Code: 1092
- Description: Hologres data sync node for general Hologres data sync configuration

The Hologres data sync node is used to configure Hologres-related data sync tasks. Through a JSON configuration file, it defines the data source, target, field mapping, and sync strategy to synchronize data between Hologres and other storage systems.

## Prerequisites

- A Hologres compute engine instance has been added on the DataWorks workspace configuration page
- Source and target data source connections required for data sync have been configured
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### Configuration Structure

The node content is a JSON sync configuration that defines the complete data sync workflow:

```json
{
  "type": "HOLOGRES_SYNC",
  "reader": {
    "datasource": "source_ds_name",
    "table": "source_table",
    "columns": ["col1", "col2", "col3"]
  },
  "writer": {
    "datasource": "hologres_ds_name",
    "table": "target_table",
    "columns": ["col1", "col2", "col3"],
    "writeMode": "INSERT_OR_REPLACE"
  },
  "settings": {
    "speed": {
      "channel": 3
    }
  }
}
```

### Applicable Scenarios

- Syncing data from external data sources to Hologres
- Syncing data between Hologres internal tables
- General scenarios requiring custom sync strategies

## Restrictions

- The sync configuration is in JSON format and must follow the specified schema
- The sync task performance is limited by the resource configuration of the source and target

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_hologres_sync",
        "script": {
          "path": "example_hologres_sync",
          "runtime": {
            "command": "HOLOGRES_DEVELOP"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
