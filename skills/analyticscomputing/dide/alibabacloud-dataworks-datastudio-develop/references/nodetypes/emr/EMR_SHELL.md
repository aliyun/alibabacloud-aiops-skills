# EMR Shell（EMR_SHELL）

## Overview

- Compute engine: `EMR`
- Content format: shell
- Extension: `.sh`
- Data source type: `emr`
- Code: 257
- Description: Run shell scripts on EMR clusters

Execute shell scripts on the Master node of EMR clusters, suitable for running system commands, file operations, cluster management, and other general shell tasks in the EMR cluster environment.

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
        "name": "example_emr_shell",
        "script": {
          "path": "example_emr_shell",
          "runtime": {
            "command": "EMR_SHELL"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Shell Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-shell-node)
