# EMR Streaming SQL（EMR_STREAMING_SQL）

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 266
- Description: Run Streaming SQL queries on EMR clusters

Define and run stream processing tasks on EMR clusters using SQL, suitable for scenarios that describe stream data processing logic with SQL syntax, lowering the barrier to stream processing development.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Spark service installed with Structured Streaming support

## Restrictions

- Stream processing jobs are long-running tasks; ensure that the scheduling period and timeout are configured appropriately

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_streaming_sql",
        "script": {
          "path": "example_emr_streaming_sql",
          "runtime": {
            "command": "EMR_STREAMING_SQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```
