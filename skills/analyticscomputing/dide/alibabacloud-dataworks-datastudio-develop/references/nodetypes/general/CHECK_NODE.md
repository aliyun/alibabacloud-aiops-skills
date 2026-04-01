# Check Node - New (CHECK_NODE)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.json`
- Description: New check node for verifying the availability of target objects

The Check node is used to verify the availability of target objects. It supports checking MaxCompute partitioned tables, FTP files, OSS files, HDFS files, OSS_HDFS files, and Kafka-to-MaxCompute real-time sync tasks. Once the check conditions are met, the node returns a success status and triggers downstream task execution, ensuring the timing accuracy and automated execution of the workflow.

## Prerequisites

- Data source-based check: The corresponding data source (MaxCompute, FTP, OSS, HDFS, or OSS_HDFS) must be created in advance.
- Real-time sync task-based check: Only Kafka to MaxCompute tasks published to the production environment are supported.
- Only supported on DataWorks Professional Edition or above.

## Restrictions

- Only Serverless resource groups are supported for execution.
- FTP data sources with Protocol configured as SFTP and key-based authentication are not supported.
- A single check node can only check one object; multiple dependencies require multiple nodes.
- The check interval range is 1-30 minutes.
- Maximum running duration is 24 hours; the number of checks depends on the interval.
- Available in limited regions: specific cities in East China, North China, South China, Southwest China, and Asia Pacific.
- Scheduling resources are continuously occupied during node execution until the check completes.
- Check logic is configured via parameters; `script.content` is empty.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_check_node",
        "script": {
          "path": "example_check_node",
          "runtime": {
            "command": "CHECK_NODE"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Reference

- [Check Node](https://help.aliyun.com/zh/dataworks/user-guide/check-node)
