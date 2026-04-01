# Data Service（DATASERVICE_STUDIO）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.json`
- Code: 238
- Data source type: `odps`
- Description: Data Service SQL

The Data Service node is used to define API query logic in DataWorks Data Service, exposing MaxCompute data as APIs through SQL configuration.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource
- DataWorks Data Service feature has been activated

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_dataservice_studio",
        "script": {
          "path": "example_dataservice_studio",
          "runtime": {
            "command": "DataService_studio"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
