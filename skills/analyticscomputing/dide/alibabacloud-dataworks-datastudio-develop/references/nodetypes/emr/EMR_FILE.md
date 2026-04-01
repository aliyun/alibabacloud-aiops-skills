# EMR File Resource（EMR_FILE）

## Overview

- Compute engine: `EMR`
- Content format: json
- Extension: `.json`
- Data source type: `emr`
- Code: 232
- LabelType：RESOURCE
- Description: Manage file resources used by EMR clusters in DataWorks

Used to register and manage general file resources (such as configuration files, data files, etc.) used on EMR clusters. These can be referenced by EMR nodes and are suitable for scenarios that require external files in EMR jobs.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_file",
        "script": {
          "path": "example_emr_file",
          "runtime": {
            "command": "EMR_FILE"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
