# EMR PySpark（EMR_PYSPARK）

## Overview

- Compute engine: `EMR`
- Content format: python
- Extension: `.py`
- Data source type: `emr`
- Code: 269
- Description: Run PySpark jobs on EMR clusters

Write Python business logic in DataWorks and submit it to EMR clusters via spark-submit for execution. Suitable for distributed data processing scenarios using Python, such as machine learning, big data analysis, etc. Supports both EMR semi-managed and fully-managed (Serverless Spark) clusters.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Spark service installed
- Only Serverless resource groups are supported

## Restrictions

- Only supports submitting the entire Python file as a single Spark job; running selected code snippets is not supported
- Supports DataLake and Custom cluster types for EMR compute resources, as well as EMR Serverless Spark compute resources
- Usage with semi-managed clusters requires submitting a ticket for evaluation

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_pyspark",
        "script": {
          "path": "example_emr_pyspark",
          "runtime": {
            "command": "EMR_PYSPARK"
          },
          "content": "print('hello')"
        }
      }
    ]
  }
}
```

## Reference

- [EMR PySpark Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-pyspark-node)
