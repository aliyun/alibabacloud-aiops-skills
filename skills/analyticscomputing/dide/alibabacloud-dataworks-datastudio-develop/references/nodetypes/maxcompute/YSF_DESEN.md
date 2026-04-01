# MaxCompute Data Masking（YSF_DESEN）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.mc.data.masking.sql`
- Code: 82
- Data source type: `odps`
- Description: MaxCompute data masking SQL

The data masking node is used to mask sensitive data in MaxCompute. It defines masking rules through SQL statements and automatically performs masking operations such as obfuscation and replacement on specified fields during data querying or processing.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource
- Data masking rules have been configured

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_ysf_desen",
        "script": {
          "path": "example_ysf_desen",
          "runtime": {
            "command": "YSF_DESEN"
          },
          "content": "SELECT * FROM my_table;"
        }
      }
    ]
  }
}
```
