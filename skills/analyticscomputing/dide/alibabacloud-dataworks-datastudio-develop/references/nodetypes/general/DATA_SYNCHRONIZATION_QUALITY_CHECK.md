# Data Sync Quality Check (DATA_SYNCHRONIZATION_QUALITY_CHECK)

## Overview

- Compute engine: `GENERAL`
- Content format: json
- Extension: `.json`
- Description: Data sync quality check node that verifies data quality of sync tasks

The Data Sync Quality Check node is used to perform quality verification on sync results after a data sync task completes. It can check the data consistency between the source and target, ensuring no data loss or anomalies occurred during the sync process.

## Content Structure

`script.content` is the JSON configuration for quality checks:

```json
{
  "type": "Quality check JSON configuration"
}
```

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_data_synchronization_quality_check",
        "script": {
          "path": "example_data_synchronization_quality_check",
          "runtime": {
            "command": "DATA_SYNCHRONIZATION_QUALITY_CHECK"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
