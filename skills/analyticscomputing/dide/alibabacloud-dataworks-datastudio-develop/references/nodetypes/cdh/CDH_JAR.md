# CDH JAR Resource (CDH_JAR)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: json
- Extension: `.json`
- Data source type: `cdh`
- Label type: RESOURCE
- Description: Manages JAR resource files on CDH clusters

Used to register and manage JAR resources used by CDH clusters in DataWorks. Registered JAR resources can be referenced by CDH MapReduce, CDH Spark, and other nodes.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- The JAR files to upload have been prepared

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_jar",
        "script": {
          "path": "example_cdh_jar",
          "runtime": {
            "command": "CDH_JAR"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
