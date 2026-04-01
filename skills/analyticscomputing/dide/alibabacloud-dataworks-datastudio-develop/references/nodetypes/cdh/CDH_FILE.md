# CDH File Resource (CDH_FILE)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: json
- Extension: `.json`
- Data source type: `cdh`
- Label type: RESOURCE
- Description: Manages general file resources on CDH clusters

Used to register and manage general file resources (such as configuration files, data files, etc.) used by CDH clusters in DataWorks. Registered file resources can be referenced by CDH series compute nodes.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- The files to upload have been prepared

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_file",
        "script": {
          "path": "example_cdh_file",
          "runtime": {
            "command": "CDH_FILE"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
