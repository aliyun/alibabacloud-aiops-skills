# CDH Spark Job (CDH_SPARK)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: shell
- Extension: `.sh`
- Data source type: `cdh`
- Description: Submits Spark jobs on CDH clusters

Used to submit and run Spark jobs on Cloudera CDH clusters via Shell scripts. The script can contain spark-submit commands to submit Spark JAR packages or Python scripts.

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
        "name": "example_cdh_spark",
        "script": {
          "path": "example_cdh_spark",
          "runtime": {
            "command": "CDH_SPARK"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```
