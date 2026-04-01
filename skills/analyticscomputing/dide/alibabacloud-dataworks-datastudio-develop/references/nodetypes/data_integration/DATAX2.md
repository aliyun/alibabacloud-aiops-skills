# DataX2 Data Sync（DATAX2）

## Overview

- Code: `20`
- Compute engine: `DI`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: DataX2 Data sync task

DataX2 is the upgraded version of DataX. Its content structure is similar to DI nodes, using the DIJob JSON format. For new projects, it is recommended to use the DI (code 23) node type instead.

## Content Structure

`script.content` is a DIJob JSON string containing the following required fields:

| Field | Type | Required | Description |
|------|------|------|------|
| `type` | string | Yes | Fixed value `"job"` |
| `version` | string | Yes | Version number, recommended `"2.0"` |
| `steps` | array | Yes | Steps array, contains Reader and Writer |
| `order` | object | Yes | Step execution order |

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_datax2",
        "script": {
          "path": "example_datax2",
          "runtime": {
            "command": "DATAX2"
          },
          "content": "{\"type\":\"job\",\"version\":\"2.0\",\"steps\":[],\"order\":{\"hops\":[]},\"setting\":{\"speed\":{\"concurrent\":1}}}"
        }
      }
    ]
  }
}
```

## Restrictions

- DATAX2 is a transitional node type. For new projects, it is recommended to use DI nodes instead.
- The content structure and configuration are largely consistent with DI nodes. For Reader/Writer configuration, refer to the [DI Data Sync Development Guide](../di-guide.md).
