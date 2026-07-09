# CLI Command Reference

## Installation

```bash
# macOS
brew install aliyun-cli

# Universal
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash

# Post-install
aliyun configure set --auto-plugin-install true
aliyun plugin update

# Verify
aliyun version   # >= 3.3.3
```

## Command Format

```bash
aliyun bpstudio execute-operation-sync \
  --service-type ai_agent \
  --operation <Operation> \
  --region cn-hangzhou \
  --attributes '<JSON>'
```

> uid is auto-injected by gateway — never pass in attributes.

## Operations

### SendMessage

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| prompt | String | Yes | Product/resource description to draw |
| sessionId | Long | No | Omit for new session; pass to iterate |
| scene | String | No | Reserved — currently no available values |

```bash
# New session
aliyun bpstudio execute-operation-sync \
  --service-type ai_agent \
  --operation SendMessage \
  --region cn-hangzhou \
  --attributes '{"prompt": "一台 ECS + 一台 RDS + SLB，同一 VPC"}'

# Continue existing session
aliyun bpstudio execute-operation-sync \
  --service-type ai_agent \
  --operation SendMessage \
  --region cn-hangzhou \
  --attributes '{"prompt": "再加一个 Redis", "sessionId": 1001}'
```

Response:
```json
{ "Code": 200, "Data": { "Status": "SUCCESS", "Arguments": { "triggered": true, "sessionId": 1001, "requestId": "xxx-xxx" } } }
```

### ListMessage

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| sessionId | Long | Yes | From SendMessage response |
| limit | Integer | No | Max messages to return (default: 50) |

```bash
aliyun bpstudio execute-operation-sync \
  --service-type ai_agent \
  --operation ListMessage \
  --region cn-hangzhou \
  --attributes '{"sessionId": 1001}'
```

Response (fields trimmed for agent readability):
```json
{
  "Data": {
    "Status": "SUCCESS",
    "Arguments": {
      "hasMore": false,
      "hasNext": false,
      "lastMessageId": 5002,
      "messageList": [
        {
          "messageId": 5001,
          "sessionId": 1001,
          "senderType": "customer",
          "senderId": "120012345678****",
          "content": "...",
          "status": "done",
          "messageSendTime": 1700000000000
        },
        {
          "messageId": 5002,
          "sessionId": 1001,
          "senderType": "robot",
          "senderId": "robot",
          "content": "...Markdown summary with resource table, validation, next steps...",
          "status": "done",
          "prompt": "...",
          "messageSendTime": 1700000090000
        }
      ]
    }
  }
}
```

**Polling**: check `messageList` last robot message `status`; `"ongoing"` = still generating, `"done"` = complete. Poll every **5s**, max 30 times.

### ListSession

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| pageNumber | Integer | No | Page number (from 1, default: 1) |
| pageSize | Integer | No | Page size (default: 10) |
| createNew | Boolean | No | true = create new session and return list |

```bash
aliyun bpstudio execute-operation-sync \
  --service-type ai_agent \
  --operation ListSession \
  --region cn-hangzhou \
  --attributes '{"pageNumber": 1, "pageSize": 10, "createNew": false}'
```

Response (fields trimmed for agent readability):
```json
{
  "Data": {
    "Status": "SUCCESS",
    "Arguments": {
      "list": [
        {
          "id": 1001,
          "uid": "120012345678****",
          "status": "robot",
          "titleSummary": "帮我生成架构图...",
          "gmtCreate": 1700000000000,
          "gmtModified": 1700000000000
        }
      ],
      "pageInfo": { "current": 1, "start": 0, "hasNext": true, "pageSize": 10, "total": 42 }
    }
  }
}
```

- `status`: `"robot"` = active session, `"end"` = closed session

## Credentials

```bash
# Configure (outside agent session)
aliyun configure

# Verify
aliyun configure list
```
