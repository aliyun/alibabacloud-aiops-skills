# SSH Remote Execution (SSH)

## Overview

- Compute engine: `GENERAL`
- Content format: shell
- Extension: `.ssh.sh`
- Description: Remotely access hosts via SSH data source and execute scripts

The SSH node allows DataWorks to remotely access hosts such as ECS through a specified SSH data source and trigger script execution on the remote host, enabling periodic scheduling of scripts. It is suitable for scenarios that require running tasks on remote servers.

## Prerequisites

- An SSH data source has been created (only JDBC connection string method is supported).
- Ensure the data source has network connectivity with the resource group.
- The RAM account must have Developer or Workspace Admin role permissions.

## Restrictions

- Only Serverless resource groups are supported for execution.
- Supported in specific regions (East China, North China, South China, and some overseas regions).
- Code length limit is 128KB.
- Supports standard Shell syntax; interactive syntax is not supported.
- When SSH tasks exit abnormally, operations on the underlying remote host are not affected.
- Ensure sufficient ECS disk space for temporary file generation.
- Avoid multiple tasks operating on the same file simultaneously to prevent node errors.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_ssh",
        "script": {
          "path": "example_ssh",
          "runtime": {
            "command": "SSH"
          },
          "content": "#!/bin/bash\necho \"Hello from SSH node\"\nhostname"
        }
      }
    ]
  }
}
```

## Reference

- [SSH Node](https://help.aliyun.com/zh/dataworks/user-guide/ssh-node)
