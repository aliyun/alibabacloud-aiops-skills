# Data Quality Monitor (DATA_QUALITY_MONITOR)

## Overview

- Compute engine: `GENERAL`
- Content format: json
- Extension: `.json`
- Description: Data quality monitor node that configures monitoring rules via JSON

The Data Quality Monitor node is used to embed quality check rules into the data processing pipeline, performing monitoring checks on data tables or datasets. Monitoring rules can be configured to validate metrics such as data completeness and consistency, ensuring data quality meets expectations.

## Content Structure

`script.content` is the JSON configuration for monitoring rules:

```json
{
  "type": "Monitoring rule JSON configuration"
}
```

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_data_quality_monitor",
        "script": {
          "path": "example_data_quality_monitor",
          "runtime": {
            "command": "DATA_QUALITY_MONITOR"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
