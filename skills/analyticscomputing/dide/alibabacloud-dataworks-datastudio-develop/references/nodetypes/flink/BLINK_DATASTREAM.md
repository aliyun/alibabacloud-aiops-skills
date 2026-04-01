# Blink DataStream（BLINK_DATASTREAM）

## Overview

- Compute engine: `FLINK`
- Content format: sql
- Extension: `.json`
- Data source type: `flink`
- Code: 2019
- Description: Blink DataStream node (legacy), used to submit custom Flink DataStream jobs

> **Note**: BLINK_DATASTREAM is a legacy node type. For new projects, it is recommended to use Flink SQL nodes (FLINK_SQL_STREAM / FLINK_SQL_BATCH) first, and only use the DataStream API when SQL cannot meet the requirements.

The Blink DataStream node is used in DataWorks to submit custom Java/Scala jobs written with the Flink DataStream API. Unlike SQL nodes, DataStream nodes allow developers to implement more complex data processing logic through programming, such as custom windows, complex event processing (CEP), async I/O, and other advanced features.

## Prerequisites

- Alibaba Cloud Realtime Compute service has been activated
- Flink/Blink project association has been configured in the DataWorks workspace
- The DataStream job has been packaged as a JAR file and uploaded to resource management

## Core Features

### Job Configuration

The content of a DataStream node is a JSON configuration specifying the JAR package, main class, arguments, and other information:

```json
{
  "jobType": "FLINK_DATASTREAM",
  "mainClass": "com.example.MyFlinkJob",
  "jarUri": "res:my_flink_job.jar",
  "args": "--input kafka_topic --output holo_table",
  "configuration": {
    "parallelism.default": "4",
    "taskmanager.memory.process.size": "2048m"
  }
}
```

### Applicable Scenarios

- Complex business logic that cannot be expressed in SQL
- Requires DataStream API advanced features (e.g., ProcessFunction, CEP)
- Custom Source/Sink connector
- Requires fine-grained control over state management and fault-tolerance mechanisms

## Restrictions

- Legacy node type; newer DataWorks versions may no longer support creation
- Java/Scala development skills are required
- JAR packages must be uploaded to DataWorks resource management in advance
- Debugging and troubleshooting are more difficult than SQL nodes

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_blink_datastream",
        "script": {
          "path": "example_blink_datastream",
          "runtime": {
            "command": "BLINK_DATASTREAM"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```
