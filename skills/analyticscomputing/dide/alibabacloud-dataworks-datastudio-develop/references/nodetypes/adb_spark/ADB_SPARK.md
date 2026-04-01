# ADB Spark (ADB_SPARK)

## Overview

- Compute engine: `ADB_SPARK`
- Content format: json
- Extension: `.adb.spark.json`
- Data source type: `adb_spark`
- Description: AnalyticDB Spark job configuration

The ADB Spark node is used to develop and schedule AnalyticDB Spark tasks in DataWorks. It supports multi-language development with Java, Scala, and Python, and is suitable for large-scale data processing, real-time data analysis, complex queries, and machine learning scenarios. Through this node, you can incorporate Spark jobs into the DataWorks periodic scheduling system and orchestrate them with other types of data development tasks.

## Content Structure

The node content is a JSON configuration for Spark jobs; the server-side will clear custom fields. Depending on the language type, the main configuration parameters are as follows:

**Java / Scala Jobs:**

| Parameter | Description |
|-----------|-------------|
| Main Jar Resource | Storage path of the JAR package on OSS |
| Main Class | Main class of the task in the JAR package, e.g., `org.apache.spark.examples.SparkPi` |
| Parameters | Parameters passed to the code, supports scheduling parameters `${var}` |
| Configuration | Spark runtime parameters, e.g., `spark.driver.resourceSpec:medium` |

**Python Jobs:**

| Parameter | Description |
|-----------|-------------|
| Main Program Package | Storage path of the Python script on OSS |
| Parameters | Parameters passed to the code, e.g., data file paths |
| Configuration | Spark runtime parameter configuration |

## Prerequisites

- An AnalyticDB for MySQL cluster (Enterprise Edition, Lakehouse Edition, or Basic Edition) has been created in the same region as the DataWorks workspace, with a Job-type resource group configured.
- The DataWorks workspace has enabled the new Data Studio (Data Development).
- The DataWorks resource group and the AnalyticDB cluster are in the same VPC, and the IP whitelist has been configured.
- The AnalyticDB cluster has been added as a compute resource (type: AnalyticDB for Spark) to the workspace and has passed the resource group connectivity test.
- If using OSS to store JAR packages or Python files, ensure OSS and the cluster are in the same region.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_adb_spark",
        "script": {
          "path": "example_adb_spark",
          "runtime": {
            "command": "ADB Spark"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Restrictions

- Only workspaces with the new Data Studio (Data Development) enabled are supported.
- The AnalyticDB cluster must have a Job-type resource group configured; otherwise, Spark jobs cannot be submitted.
- Debug runs require configuring compute resources, resource groups, and compute CU runtime properties.

## Reference

- [ADB Spark Node - Alibaba Cloud Documentation](https://help.aliyun.com/zh/dataworks/user-guide/adb-spark-node)
