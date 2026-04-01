# MaxCompute Table（ODPS_TABLE）

## Overview

- Compute engine: `ODPS`
- Content format: json
- Extension: `.json`
- Code: 16
- Data source type: `odps`
- Label type: TABLE
- Description: MaxCompute table definition

The MaxCompute table node is used to define MaxCompute table structures in JSON format, including column definitions, partition columns, lifecycle, etc. This node enables version management and automated deployment of table structures.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Content Structure

```json
{
  "name": "table name",
  "columns": [
    {"name": "column name", "type": "data type"}
  ],
  "partitions": [
    {"name": "partition column name", "type": "STRING"}
  ],
  "lifecycle": 90
}
```

### Supported Data Types

Common data types supported by MaxCompute include: BIGINT, STRING, DOUBLE, BOOLEAN, DATETIME, DECIMAL, INT, FLOAT, TIMESTAMP, BINARY, ARRAY, MAP, STRUCT, etc.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_table",
        "script": {
          "path": "example_odps_table",
          "runtime": {
            "command": "ODPS_TABLE"
          },
          "content": "{\"name\":\"example_table\",\"columns\":[{\"name\":\"id\",\"type\":\"BIGINT\"},{\"name\":\"name\",\"type\":\"STRING\"}]}"
        }
      }
    ]
  }
}
```
