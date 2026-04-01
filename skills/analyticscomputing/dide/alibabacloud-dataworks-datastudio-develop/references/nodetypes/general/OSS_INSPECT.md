# OSS Object Inspection (OSS_INSPECT)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.json`
- Description: OSS object inspection node that verifies the availability of objects on OSS storage

The OSS Inspect node is used to detect whether a specified object (file) exists or is ready on OSS storage before workflow execution. Once the check conditions are met, the node returns a success status and triggers downstream task execution, ensuring that the required OSS data is in place.

## Prerequisites

- An OSS data source has been created, and network connectivity between the data source and the resource group is ensured.

## Restrictions

- Check logic is configured via parameters; `script.content` is empty.
- Only Serverless resource groups are supported for execution.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_oss_inspect",
        "script": {
          "path": "example_oss_inspect",
          "runtime": {
            "command": "OSS_INSPECT"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Reference

- [OSS Sensor Node](https://help.aliyun.com/zh/dataworks/user-guide/oss-sensor-node)
