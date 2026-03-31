# Bailian API Key Guide

## 1. Activate Bailian Service

1. Log in to the [Bailian Console](https://bailian.console.aliyun.com/)
2. If not activated, follow the on-screen prompts to activate the Model Studio (Bailian) service
3. New users may enjoy a free token quota (specific quota and validity period subject to the latest official promotions)

## 2. Obtain an API Key via CLI

The Bailian API Key can be fully obtained via `aliyun maas` CLI commands — no console operation needed.

### 2.1 Install MaaS CLI Plugin

```bash
aliyun plugin install --names aliyun-cli-maas
```

### 2.2 List Workspaces (must run first)

`workspace-id` is a required parameter for querying and creating API Keys, so you must obtain it first:

```bash
aliyun maas list-workspaces --region cn-hangzhou
```

Record the `WorkspaceId` from the result (e.g., `ws-xxxxxxxx`).

### 2.3 Query Existing API Keys

Use the `workspace-id` obtained in the previous step to query existing keys:

```bash
aliyun maas list-api-keys --workspace-id ${workspace_id} --region cn-hangzhou
```

If an existing API Key is found, use its `ApiKeyValue` (in `sk-xxx` format).

### 2.4 Create a New API Key (only if none exists)

```bash
aliyun maas create-api-key --workspace-id ${workspace_id} --description "My API Key" --region cn-hangzhou
```

Record the `ApiKeyValue` (in `sk-xxx` format) from the response. The full API Key value is only visible at creation time.

## 3. Plan Recommendations

- The Coding Plan (Lite basic plan for trial) is recommended, which refreshes a specified quota every 5 hours to help control costs
- New users have a free quota (specific quota subject to the latest official policies)
- Charges apply per token usage after exceeding the free quota

## Reference Links

- [Bailian Console](https://bailian.console.aliyun.com/)
- [Bailian API Documentation](https://help.aliyun.com/zh/model-studio/)
