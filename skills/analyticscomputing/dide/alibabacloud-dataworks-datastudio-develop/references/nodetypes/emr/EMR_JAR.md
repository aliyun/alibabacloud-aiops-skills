# EMR JAR Resource（EMR_JAR）

## Overview

- Compute engine: `EMR`
- Content format: json
- Extension: `.json`
- Data source type: `emr`
- Code: 231
- LabelType：RESOURCE
- Description: Manage JAR resources used by EMR clusters in DataWorks

Used to register and manage JAR package resources used on EMR clusters. These can be referenced by EMR Spark, EMR MR, and other nodes, suitable for scenarios requiring additional JAR dependencies such as custom UDFs, Spark applications, etc.

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
        "name": "example_emr_jar",
        "script": {
          "path": "example_emr_jar",
          "runtime": {
            "command": "EMR_JAR"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
