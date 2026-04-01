# Real-time Data Sync（RI）

## Overview

- Code: `900`
- Compute engine: `DI`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: Real-time data sync task

RI (Real-time Integration) is the real-time data sync service of DataWorks, supporting second-level latency CDC (Change Data Capture) to capture source data changes and sync them to the target in real time. Unlike offline sync (DI) which uses batch periodic scheduling, RI runs continuously in streaming mode, suitable for scenarios requiring high data timeliness.

Help documentation: https://help.aliyun.com/zh/dataworks/user-guide/create-and-manage-real-time-synchronization-nodes

## Features

- **Real-time sync**: Second-level latency, continuously captures source data changes
- **Sync range**: Supports single-table real-time sync and whole-database real-time sync
- **Data sources**: Supports real-time sync from relational databases such as MySQL, PostgreSQL, Oracle, SQL Server, etc. to targets such as MaxCompute, Hologres, Kafka, Elasticsearch, etc.

## Content Structure

`script.content` is a DIJob JSON string with the same structure as DI nodes:

| Field | Type | Required | Description |
|------|------|------|------|
| `type` | string | Yes | Fixed value `"job"` |
| `version` | string | Yes | Version number, recommended `"2.0"` |
| `steps` | array | Yes | Steps array, contains Reader and Writer |
| `order` | object | Yes | Step execution order |
| `setting` | object | No | Runtime parameters configuration |

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_ri",
        "script": {
          "path": "example_ri",
          "runtime": {
            "command": "RI"
          },
          "content": "{\"type\":\"job\",\"version\":\"2.0\",\"steps\":[],\"order\":{\"hops\":[]},\"setting\":{\"speed\":{\"concurrent\":1}}}"
        }
      }
    ]
  }
}
```

## Restrictions

- Real-time sync tasks are long-running tasks, which differ from the periodic scheduling approach of offline sync.
- Must be used with CDC-capable data sources (e.g., MySQL binlog, PostgreSQL WAL, etc.).
- The Reader/Writer configuration is similar to DI nodes. For details, refer to the [DI Data Sync Development Guide](../di-guide.md).
