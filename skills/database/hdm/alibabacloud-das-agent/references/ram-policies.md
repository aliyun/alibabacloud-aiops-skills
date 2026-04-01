# RAM Policies

This document describes the RAM (Resource Access Management) permissions required for the DAS Agent skill.

## Required API Permissions

The skill requires the following specific API permission:

| Product | Action | Description |
|---------|--------|-------------|
| `das` | `Chat` | Call the DAS Agent Chat API to send natural language queries and receive diagnostic results |

### Granting Permissions

To grant the required permissions:

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Create or select an existing RAM user/role
3. Attach the managed `das:Chat` policy

For detailed instructions, see the [Alibaba Cloud RAM documentation](https://www.alibabacloud.com/help/en/ram/user-guide/grant-permissions-to-a-ram-user).

## API Endpoints

The skill accesses the following Alibaba Cloud API endpoint:

| Service | Endpoint | Action |
|---------|----------|--------|
| DAS | `das.cn-shanghai.aliyuncs.com` | `Chat` |

## Credential Configuration

Credentials are resolved via the [Alibaba Cloud default credential chain](https://www.alibabacloud.com/help/en/sdk/developer-reference/v2-manage-python-access-credentials). Supported sources include:

- Environment variables
- Local profile files (`~/.aliyun/config.json` or `~/.alibabacloud/credentials.ini`)
- ECS RAM Role metadata (when running on Alibaba Cloud ECS)

Refer to the official documentation for setup instructions.
