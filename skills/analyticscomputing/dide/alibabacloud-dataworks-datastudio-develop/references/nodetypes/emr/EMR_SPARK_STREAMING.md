# EMR Spark Streaming（EMR_SPARK_STREAMING）

## Overview

- Compute engine: `EMR`
- Content format: shell
- Extension: `.sh`
- Data source type: `emr`
- Code: 264
- Description: Submit Spark Streaming stream processing jobs on EMR clusters

Submit Spark Streaming jobs on EMR clusters via shell scripts, suitable for real-time or near-real-time stream data processing scenarios such as log collection and analysis, real-time metric computation, etc.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Spark service installed

## Restrictions

- Spark Streaming jobs are long-running tasks; ensure that the scheduling period and timeout are configured appropriately

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_spark_streaming",
        "script": {
          "path": "example_emr_spark_streaming",
          "runtime": {
            "command": "EMR_SPARK_STREAMING"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Spark Streaming Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-spark-streaming-node)
