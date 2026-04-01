# CDH Shell (CDH_SHELL)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: shell
- Extension: `.sh`
- Data source type: `cdh`
- Description: Executes Shell scripts on CDH clusters

Used to execute Shell scripts on the gateway node of Cloudera CDH clusters. Can invoke various command-line tools on the CDH cluster (such as hdfs, hadoop, etc.), suitable for file operations, cluster management, and custom script tasks.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_shell",
        "script": {
          "path": "example_cdh_shell",
          "runtime": {
            "command": "CDH_SHELL"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```
