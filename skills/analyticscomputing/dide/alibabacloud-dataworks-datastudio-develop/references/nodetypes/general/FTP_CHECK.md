# FTP File Check (FTP_CHECK)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.json`
- Description: FTP file check node that verifies the availability of files on FTP servers

The FTP Check node is used to detect whether a specified file exists or is ready on an FTP server before workflow execution. Once the check conditions are met, the node returns a success status and triggers downstream task execution.

## Prerequisites

- An FTP data source has been created, and network connectivity between the data source and the resource group is ensured.

## Restrictions

- Check logic is configured via parameters; `script.content` is empty.
- FTP data sources with Protocol configured as SFTP and key-based authentication are not supported.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_ftp_check",
        "script": {
          "path": "example_ftp_check",
          "runtime": {
            "command": "FTP_CHECK"
          },
          "content": ""
        }
      }
    ]
  }
}
```
