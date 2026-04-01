# MaxCompute Spark（ODPS_SPARK）

## Overview

- Compute engine: `ODPS`
- Content format: json
- Extension: `.mc.spark.json`
- Code: 225
- Data source type: `odps`
- Description: MaxCompute Spark job configuration

The MaxCompute Spark node supports running Spark offline jobs in DataWorks through Cluster mode, supporting three development languages: Java, Scala, and Python.

## Prerequisites

- The RAM account must have **Developer** or **Workspace Admin** role permissions
- If selecting Spark 3.x version, a Serverless resource group must be purchased

## Core Features

### Configuration Items

**Java/Scala jobs:**
- Spark version (1.x / 2.x / 3.x)
- Main JAR resource file
- Main Class (fully qualified class name)
- Configuration items, parameters, and associated JAR/File/Archives resources

**Python jobs:**
- Spark version (1.x / 2.x / 3.x)
- Main Python resource file
- Configuration items, parameters, and associated Python/File/Archives resources

> No need to upload the spark-defaults.conf file; its configurations should be added individually to the node configuration items.

## Content Structure

```json
{
  "mainClass": "entry class fully qualified name",
  "jars": ["JAR resource list"],
  "args": ["Runtime parameters"]
}
```

## Restrictions

- Executes in Cluster mode; a custom program entry `main` must be specified
- Python The default environment has limited dependency packages; a custom Python environment can be used
- Spark 3.x version requires Serverless resource group support

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_spark",
        "script": {
          "path": "example_odps_spark",
          "runtime": {
            "command": "ODPS_SPARK"
          },
          "content": "{\"mainClass\":\"com.example.SparkJob\",\"jars\":[\"spark_job.jar\"]}"
        }
      }
    ]
  }
}
```

## Reference

- [MaxCompute Spark Node](https://help.aliyun.com/zh/dataworks/user-guide/maxcompute-spark-node)
