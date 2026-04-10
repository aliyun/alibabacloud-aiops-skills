# Bailian API Key Guide

## 1. Activate Bailian Service

1. Log in to the [Bailian Console](https://bailian.console.aliyun.com/)
2. If not activated, follow the on-screen prompts to activate the Model Studio (Bailian) service
3. New users may enjoy a free token quota (specific quota and validity period subject to the latest official promotions)

## 2. Obtain an API Key via CLI

The Bailian API Key can be fully obtained via `aliyun modelstudio` CLI commands — no console operation needed.

### 2.1 Install Model Studio CLI Plugin

```bash
aliyun plugin install --names aliyun-cli-modelstudio
```

### 2.2 List Workspaces (must run first)

`workspace-id` is a required parameter for creating API Keys, so you must obtain it first:

```bash
aliyun modelstudio list-workspaces
```

Record the `WorkspaceId` from the result (e.g., `ws-xxxxxxxx`).

### 2.3 Create a New API Key

Use the `workspace-id` obtained in the previous step:

```bash
aliyun modelstudio create-api-key --workspace-id ${workspace_id} --description "My API Key"
```

Record the `ApiKeyValue` (in `sk-xxx` format) from the response. **The full API Key value is only returned at creation time** — `list-api-keys` always returns masked values (`sk-***`), so it cannot be used to retrieve a usable key. If you lose the key, delete the old one and create a new one.


