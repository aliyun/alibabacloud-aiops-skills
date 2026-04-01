# Serverless Spark Batch (SERVERLESS_SPARK_BATCH)

## Overview

- Compute engine: `EMR`
- Content format: shell
- Extension: `.sh`
- Data source type: `emr`
- Code: 2100
- Description: Serverless Spark Batch node, batch processing jobs based on EMR Serverless Spark

The Serverless Spark Batch node is used in DataWorks to submit and schedule EMR Serverless Spark batch processing jobs. It uses Shell scripts to write `spark-submit` commands, submitting Spark JAR or PySpark jobs to the Serverless Spark cluster for execution, without the need to manage underlying cluster infrastructure.

## Prerequisites

- An EMR Serverless Spark compute resource has been bound, Ensure the resource group has network connectivity with the compute resource
- Only Serverless resource groups are supported for running this task type
- The Spark job JAR package or Python file has been uploaded to OSS or DataWorks resource management
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### Script Format

The node content is a Shell script, typically containing the `spark-submit` command:

```bash
#!/bin/bash
# Spark Batch job submission
spark-submit \
  --class com.example.MySparkJob \
  --master yarn \
  --deploy-mode cluster \
  --driver-memory 2g \
  --executor-memory 4g \
  --executor-cores 2 \
  --num-executors 10 \
  --conf spark.sql.shuffle.partitions=200 \
  my_spark_job.jar \
  --input oss://my-bucket/input/ \
  --output oss://my-bucket/output/ \
  --date ${bizdate}
```

### Scheduling Parameters

Supports defining dynamic parameters using `${variable_name}` syntax:

```bash
spark-submit \
  --class com.example.ETLJob \
  my_etl.jar \
  --date ${bizdate} \
  --partition ${partition_value}
```

### Applicable Scenarios

- **Large-scale ETL**: Batch data processing based on the Spark engine
- **Machine learning**: Submit Spark MLlib training jobs
- **Data analysis**: Complex distributed computing tasks
- **Custom jobs**: Complex business logic that cannot be fulfilled by SQL

### Resource Configuration

Control resource allocation through `spark-submit` parameters:

| Parameter | Description |
|------|------|
| `--driver-memory` | Driver process memory |
| `--executor-memory` | Memory per Executor |
| `--executor-cores` | CPU cores per Executor |
| `--num-executors` | Number of Executors |

## Restrictions

- Only Serverless resource groups are supported for execution
- Job JAR packages or dependency files must be uploaded in advance
- The `spark-submit` parameters in the Shell script must comply with Serverless Spark specifications

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_serverless_spark_batch",
        "script": {
          "path": "example_serverless_spark_batch",
          "runtime": {
            "command": "SERVERLESS_SPARK_BATCH"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Serverless Spark Batch Node](https://help.aliyun.com/zh/dataworks/user-guide/serverless-spark-batch-node)
