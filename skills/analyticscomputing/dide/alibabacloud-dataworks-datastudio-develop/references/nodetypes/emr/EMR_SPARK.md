# EMR Spark Job（EMR_SPARK）

## Overview

- Compute engine: `EMR`
- Content format: shell
- Extension: `.sh`
- Data source type: `emr`
- Code: 228
- Description: Submit Spark jobs on EMR clusters

Write spark-submit commands via shell scripts to submit and run Spark jobs (such as Spark applications in JAR package form) on EMR clusters, suitable for submitting and scheduling custom Spark applications.

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
        "name": "example_emr_spark",
        "script": {
          "path": "example_emr_spark",
          "runtime": {
            "command": "EMR_SPARK"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Spark Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-spark-node)
