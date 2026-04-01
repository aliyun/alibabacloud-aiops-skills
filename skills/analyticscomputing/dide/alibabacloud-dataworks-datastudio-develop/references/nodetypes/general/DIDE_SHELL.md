# Shell Script (DIDE_SHELL)

## Overview

- Compute engine: `GENERAL`
- Content format: shell
- Extension: `.sh`
- Description: Run standard Bash Shell scripts on DataWorks scheduling resource groups

The Shell node supports standard Shell script execution, suitable for scenarios such as file operations, OSS/NAS data interaction, and batch data processing. The node has ossutil pre-installed for direct OSS storage operations, and supports resource references, scheduling parameter configuration, and RAM role association.

## Prerequisites

- The RAM account must be added to the workspace with Developer or Workspace Admin role permissions.

## Restrictions

- Supports standard Shell syntax; interactive syntax is not supported.
- Serverless resource group supports a maximum of 64 CU per task; 16 CU or less is recommended.
- Avoid launching too many subprocesses, as this may affect other tasks on the same resource group.
- When calling other scripts, the Shell node must wait for the called script to complete.
- Scheduling parameters only support positional parameter format (`$1`, `$2`, etc.); custom variable names are not supported.
- Resources must be published before they can be referenced; the resource reference annotation `##@resource_reference{resource_name}` is a required identifier and must not be manually modified.
- ossutil is pre-installed; no manual installation is required.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_dide_shell",
        "script": {
          "path": "example_dide_shell",
          "runtime": {
            "command": "DIDE_SHELL"
          },
          "content": "#!/bin/bash\necho \"Hello DataWorks\"\ndate"
        }
      }
    ]
  }
}
```

## Reference

- [Shell Node](https://help.aliyun.com/zh/dataworks/user-guide/shell-node)
