# EMR Hive CLI（EMR_HIVE_CLI）

## Overview

- Compute engine: `EMR`
- Content format: empty (no code)
- Extension: none
- Data source type: `emr`
- Code: 265
- Description: Execute Hive operations on EMR clusters via Hive CLI command line

Execute Hive commands on EMR clusters through the Hive command-line interface (CLI), suitable for scenarios that require Hive CLI-specific features or interactive commands.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Hive service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_hive_cli",
        "script": {
          "path": "example_emr_hive_cli",
          "runtime": {
            "command": "EMR_HIVE_CLI"
          },
          "content": ""
        }
      }
    ]
  }
}
```
