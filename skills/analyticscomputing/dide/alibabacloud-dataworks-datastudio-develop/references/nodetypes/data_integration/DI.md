# Data Integration - Offline Sync（DI）

## Overview

- Code: `23`
- Compute engine: `DI`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: Offline data sync task (DIJob), the recommended data integration node type

DI (Data Integration) is the offline data sync service of DataWorks, providing stable, efficient, and elastically scalable data transfer capabilities between heterogeneous data sources. It supports both wizard mode (visual configuration) and script mode (JSON script) for development.

Help documentation: https://help.aliyun.com/zh/dataworks/user-guide/develop-an-offline-synchronization-node

## Features

- **Sync mode**: Supports full sync, incremental sync, and combined full-incremental sync
- **Sync range**: Supports single-table sync, whole-database sync, and sharded-database/sharded-table sync
- **Data sources**: Supports dozens of data sources including MySQL, MaxCompute (ODPS), Hologres, PostgreSQL, Oracle, SQL Server, OSS, FTP, Kafka, Elasticsearch, etc.
- **Field mapping**: Supports column mapping configuration between source and target
- **Concurrency control**: Supports configuring the number of parallel read/write channels
- **Speed limit**: Supports transfer speed throttling
- **Dirty data handling**: Supports setting a dirty data record count threshold
- **Transfer semantics**: At-least-once delivery (may produce duplicates); exactly-once is not supported

## Content Structure（DIJob JSON）

`script.content` is a DIJob JSON string with the following top-level structure:

| Field | Type | Required | Description |
|------|------|------|------|
| `type` | string | Yes | Fixed value `"job"` |
| `version` | string | Yes | Version number, recommended `"2.0"` |
| `steps` | array | Yes | Steps array, must contain at least one Reader and one Writer |
| `order` | object | Yes | Step execution order, defines from/to relationships via `hops` |
| `setting` | object | No | Runtime parameters (concurrency count, speed limit, dirty data threshold, etc.) |

Each step contains `stepType` (data source type), `name` (step name), `category` (`reader` or `writer`), and `parameter` (data source parameters).

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_di",
        "script": {
          "path": "example_di",
          "runtime": {
            "command": "DI"
          },
          "content": "{\"type\":\"job\",\"version\":\"2.0\",\"steps\":[],\"order\":{\"hops\":[]},\"setting\":{\"speed\":{\"concurrent\":1}}}"
        }
      }
    ]
  }
}
```

## Restrictions

- The number of columns in the Reader and Writer must be consistent, mapped one-to-one in order.
- The data source name in `parameter.datasource` must exactly match the data source name registered in DataWorks.
- The DI node spec does not require a `datasource` field; data source information is configured in `parameter.datasource` within the code JSON.
- Setting `concurrent` too high may put pressure on the source database; adjust according to actual conditions.
- When dirty data causes a task failure, data that has already been successfully written will not be rolled back.
- For production environments, it is recommended to set `errorLimit.record` to 0 to ensure data quality.

For detailed Reader/Writer configuration, refer to the [DI Data Sync Development Guide](../di-guide.md).
