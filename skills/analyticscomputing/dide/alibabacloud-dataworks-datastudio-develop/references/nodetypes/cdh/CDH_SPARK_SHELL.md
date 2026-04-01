# CDH Spark Shell (CDH_SPARK_SHELL)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: shell
- Extension: `.sh`
- Data source type: `cdh`
- Description: Runs Spark-related scripts in Shell mode on CDH clusters

Used to execute scripts via Spark Shell mode on Cloudera CDH clusters. Similar to CDH_SPARK but focused on batch submission scenarios for interactive Spark scripts.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- CDH cluster has Spark service deployed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_spark_shell",
        "script": {
          "path": "example_cdh_spark_shell",
          "runtime": {
            "command": "CDH_SPARK_SHELL"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```
