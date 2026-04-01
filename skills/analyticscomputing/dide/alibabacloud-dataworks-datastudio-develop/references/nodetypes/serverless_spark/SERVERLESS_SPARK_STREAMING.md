# Serverless Spark Streaming (SERVERLESS_SPARK_STREAMING)

## Overview

- Compute engine: `EMR`
- Content format: shell
- Extension: `.sh`
- Data source type: `emr`
- Code: 2102
- Description: Serverless Spark Streaming node, stream processing jobs based on EMR Serverless Spark

The Serverless Spark Streaming node is used in DataWorks to submit and manage real-time stream processing jobs based on Spark Structured Streaming. It uses Shell scripts to write `spark-submit` commands, submitting stream processing jobs to the Serverless Spark cluster, enabling continuous consumption and processing of real-time data.

## Prerequisites

- An EMR Serverless Spark compute resource has been bound, Ensure the resource group has network connectivity with the compute resource
- Only Serverless resource groups are supported for running this task type
- The Spark Streaming job JAR package has been uploaded to OSS or DataWorks resource management
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### Script Format

The node content is a Shell script, typically containing the `spark-submit` command for streaming jobs:

```bash
#!/bin/bash
# Spark Streaming job submission
spark-submit \
  --class com.example.MyStreamingJob \
  --master yarn \
  --deploy-mode cluster \
  --driver-memory 2g \
  --executor-memory 4g \
  --executor-cores 2 \
  --num-executors 5 \
  --conf spark.streaming.kafka.maxRatePerPartition=1000 \
  --conf spark.sql.streaming.checkpointLocation=oss://my-bucket/checkpoint/ \
  my_streaming_job.jar \
  --bootstrap-servers kafka-broker:9092 \
  --topic user_events \
  --output-table hologres_sink_table
```

### Applicable Scenarios

- **Real-time ETL**: Consume data from Kafka/DataHub and process/write to target tables in real time
- **Real-time monitoring**: Continuously monitor data streams and trigger alerts
- **Real-time aggregation**: Window aggregation based on Spark Structured Streaming
- **Data sync**: Sync data from one storage to another in real time

### Differences from Flink Streaming Nodes

| Feature | Spark Streaming | Flink Streaming |
|------|----------------|-----------------|
| Processing model | Micro-batch | True stream processing |
| Latency | Second-level | Millisecond-level |
| Programming model | Spark API | Flink SQL / DataStream |
| Applicable scenarios | Near-real-time ETL, micro-batch processing | Low-latency real-time computation |

## Restrictions

- Streaming tasks run continuously after startup until manually stopped or abnormally terminated
- Only Serverless resource groups are supported for execution
- Checkpoints must be properly configured to ensure fault tolerance
- Job JAR packages must be uploaded in advance

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_serverless_spark_streaming",
        "script": {
          "path": "example_serverless_spark_streaming",
          "runtime": {
            "command": "SERVERLESS_SPARK_STREAMING"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```
