# Data Push (DATA_PUSH)

## Overview

- Compute engine: `GENERAL`
- Content format: json
- Extension: `.json`
- Description: Push data query results from upstream nodes to DingTalk groups, Feishu groups, WeCom groups, Teams, or email

The Data Push node can push data query results from other nodes in a workflow to DingTalk groups, Feishu groups, WeCom groups, Teams, or email by configuring push targets. The node obtains upstream node outputs through context parameters and supports displaying data in Markdown or table format.

## Prerequisites

- DataWorks service has been activated and a workspace has been created.
- A Serverless resource group (must be created after June 28, 2024) is available.
- The resource group has public network access enabled.

## Content Structure

`script.content` is the JSON configuration for the push task.

## Restrictions

- The upstream node must be a SQL query node or an assignment node.
- Directly fetching data from ODPS SQL is not currently supported; an assignment node must be used as an intermediary.
- Push content size limits:
  - DingTalk/Feishu: up to 20KB.
  - WeCom: 20 messages per bot per minute.
  - Teams: up to 28KB.
  - Email: Only one email body is supported.
- Supported in the following regions only: China East 1 (Hangzhou), China East 2 (Shanghai), China North 2 (Beijing), and 9 other regions.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_data_push",
        "script": {
          "path": "example_data_push",
          "runtime": {
            "command": "DATA_PUSH"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Reference

- [Data Push Node](https://help.aliyun.com/zh/dataworks/user-guide/data-push-node)
