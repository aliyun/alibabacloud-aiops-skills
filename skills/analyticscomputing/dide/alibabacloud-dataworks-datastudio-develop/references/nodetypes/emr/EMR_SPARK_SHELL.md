# EMR Spark Shell（EMR_SPARK_SHELL）

## Overview

- Compute engine: `EMR`
- Content format: shell
- Extension: `.sh`
- Data source type: `emr`
- Code: 258
- Description: Run Spark Shell scripts on EMR clusters

Execute Spark Shell interactive commands on EMR clusters via shell scripts, suitable for scenarios that require using Spark Shell (Scala) for data exploration and processing.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Spark service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_spark_shell",
        "script": {
          "path": "example_emr_spark_shell",
          "runtime": {
            "command": "EMR_SPARK_SHELL"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```
