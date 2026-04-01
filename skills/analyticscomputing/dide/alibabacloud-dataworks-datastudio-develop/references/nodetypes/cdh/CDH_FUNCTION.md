# CDH Function (CDH_FUNCTION)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: empty (no code)
- Extension: none
- Data source type: `cdh`
- Label type: FUNCTION
- Description: Manages custom functions on CDH clusters

Used to register and manage custom functions (UDFs) on CDH clusters in DataWorks. Registered functions can be called in CDH Hive SQL, Spark SQL, and other nodes.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- JAR resources that the function implementation depends on have been uploaded

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_function",
        "script": {
          "path": "example_cdh_function",
          "runtime": {
            "command": "CDH_FUNCTION"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Restrictions\n\n- The node content format is empty; function definitions specify the class name and associated JAR resources through metadata configuration
