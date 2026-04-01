# CDH MapReduce (CDH_MR)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: empty (no code)
- Extension: none
- Data source type: `cdh`
- Description: Runs MapReduce jobs on CDH clusters

Used to submit and run Hadoop MapReduce jobs on Cloudera CDH clusters. MapReduce jobs specify the JAR package and main class through configuration parameters; the node itself does not contain code content.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- CDH cluster has MapReduce/YARN service deployed
- JAR resources needed for the MapReduce job have been uploaded

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_mr",
        "script": {
          "path": "example_cdh_mr",
          "runtime": {
            "command": "CDH_MR"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Restrictions\n\n- The node content format is empty; job logic must be specified through associated JAR resources and runtime parameters
