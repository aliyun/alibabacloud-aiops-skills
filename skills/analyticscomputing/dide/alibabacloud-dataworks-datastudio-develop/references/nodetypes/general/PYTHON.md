# Python Script (PYTHON)

## Overview

- Compute engine: `GENERAL`
- Content format: python
- Extension: `.py`
- Description: Run Python 3 scripts on DataWorks scheduling resource groups

The Python node is used for writing and scheduling Python 3 scripts, suitable for scenarios such as data processing, ETL helper logic, and calling external APIs. Scripts run in the Python 3 environment built into the scheduling resource group.

## Prerequisites

- The RAM account must be added to the workspace with Developer or Workspace Admin role permissions.

## Restrictions

- The runtime environment is Python 3; Python 2 syntax is not supported.
- Serverless resource group supports a maximum of 64 CU per task; 16 CU or less is recommended.
- Only pre-installed Python third-party libraries on the resource group can be used; additional dependencies must be uploaded via resource references.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_python",
        "script": {
          "path": "example_python",
          "runtime": {
            "command": "PYTHON"
          },
          "content": "import sys\nprint('Hello DataWorks')\nprint(f'Python version: {sys.version}')"
        }
      }
    ]
  }
}
```

## Reference

- [Python Node](https://help.aliyun.com/zh/dataworks/user-guide/python-node)
