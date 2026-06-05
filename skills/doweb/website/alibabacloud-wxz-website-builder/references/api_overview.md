# AI Staff OpenAPI Overview

Product code: `websitebuild`
API version: `2025-04-29`
Default endpoint: `websitebuild.aliyuncs.com`
Auth: AK/SK (RPC style, POST method)

> **Note:** The production endpoint is `webbuild.aliyuncs.com`. The suffix indicates the pre-production environment used during development. API actions retain the `AIStaff` prefix from the original `zero2staff` product.

## API Operations

### Conversation Management

| Action | Description | Key Parameters |
|--------|-------------|----------------|
| `CreateAIStaffConversation` | Create conversation with site instance, section, and initial chat | `Text` |

**CreateAIStaffConversation Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Text` | String | Yes | User question text (first 100 chars used as title) |

**CreateAIStaffConversation Response:**

Standard Alibaba Cloud response with `RequestId`, `AllowRetry`, and `Module` wrapper:

| Field | Type | Description |
|-------|------|-------------|
| `ConversationId` | String | Conversation ID |
| `SectionId` | String | Section ID |
| `SiteId` | String | Site instance ID (used as `BizId` in subsequent calls) |
| `ChatId` | String | Initial chat ID |
| `BotId` | String | Bot ID (e.g. Zero2) |
| `Title` | String | Conversation title (first 100 chars of Text) |

**Example Response:**

```json
{
  "RequestId": "817605ED-A552-13C0-AA42-09F9808BD41C",
  "AllowRetry": false,
  "Module": {
    "ConversationId": "18ECF2D9F5C939C7F42C66370D5396DD",
    "Title": "build a popmart homepage",
    "SiteId": "WS20260427195646000001",
    "BotId": "Zero2",
    "SectionId": "A1B5EAE8442FAF3F4A4951BF6BC35BCA",
    "ChatId": "E191C67E30C7F5C854CB44FE36C5857D"
  }
}
```

### Chat Operations

| Action | Description | Key Parameters |
|--------|-------------|----------------|
| `CreateAIStaffChat` | Fire async chat (returns immediately) | `ConversationId`, `Messages`, `BizId`, `ChatId` |
| `RetryAIStaffChat` | Retry a failed chat | `ConversationId`, `ChatId`, `BotId`, `SiteId`, `SectionId`, `MetaData` |

**CreateAIStaffChat Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ConversationId` | String | Yes | Conversation ID from CreateAIStaffConversation |
| `Messages` | Array (JSON) | Yes | List of message objects |
| `BizId` | String | Yes | Site/business ID (SiteId from create-conversation) |
| `ChatId` | String | No | Chat ID (required for HITL resume) |

**Message Object Structure (as sent by CLI):**

```json
{
  "ContentType": "text",
  "Content": "user text here",
  "MetaData": {
    "model": "qwen3.5",
    "phase": "generate_code",
    "user_navigation": "generate_prd",
    "__hidden__": true
  },
  "Role": "user",
  "Type": "question",
  "chatStatus": "interrupt",
  "withoutRefer": true
}
```

**MetaData fields:**

| Field | Description |
|-------|-------------|
| `model` | Model name (default: qwen3.5) |
| `phase` | Phase: `requirement_collect`, `generate_prd`, `generate_code` |
| `user_navigation` | Navigation target (e.g. `generate_prd`) |
| `__hidden__` | Hide message in UI (boolean) |

**Top-level message fields (outside MetaData):**

| Field | Description |
|-------|-------------|
| `chatStatus` | Set to `interrupt` when resuming from HITL |
| `withoutRefer` | Skip reference context (boolean) |

### SSE Event Operations

| Action | Description | Key Parameters |
|--------|-------------|----------------|
| `ListAIStaffChatEvents` | Fetch incremental SSE events (delta events filtered) | `ConversationId`, `BizId`, `ChatId`, `LastEventId` |

**ListAIStaffChatEvents Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ConversationId` | String | Yes | Conversation ID |
| `BizId` | String | Yes | Site/business ID |
| `ChatId` | String | No | Chat ID (server uses latest if omitted) |
| `LastEventId` | Integer | No | Last event ID for incremental fetch (default: 0) |

**ListAIStaffChatEvents Response:**

Response is wrapped in `Module` field:

| Field | Type | Description |
|-------|------|-------------|
| `ConversationId` | String | Conversation ID |
| `ChatId` | String | Current chat ID |
| `LastEventId` | Integer | Last event ID in the page (including filtered deltas) |
| `HasMore` | Boolean | `true` if more events remain beyond this page |
| `Events` | Array | List of SSE event objects (delta events excluded) |

**SSE Event Object:**

| Field | Type | Description |
|-------|------|-------------|
| `Id` | Integer | Event sequence ID |
| `Name` | String | Event type name |
| `Data` | String | JSON-encoded event data |

## SSE Event Types

| Event Name | Description |
|------------|-------------|
| `chat.processing` | Chat is being processed (contains `status: "processing"`) |
| `chat.completed` | Chat completed (check `status` field: `success`, `interrupt`, `fail`) |
| `chat.failed` | Chat failed |
| `message.completed` | Final message content (assistant text response) |
| `message.error` | Error message |
| `message.interrupt` | HITL interrupt — contains `toolFeedbacks` with AskUserQuestion forms |
| `message.tool` | Tool call event (contains tool name, arguments, status in `metaData`) |
| `done` | End-of-round marker (`[DONE]`) |

**Note:** `.delta` events (`message.delta`, `message.tool.delta`) are filtered out by the server. The `LastEventId` cursor still accounts for them to maintain incremental consistency.

### Tool Call Event Details

The `message.tool` event's `metaData` contains:

| Field | Description |
|-------|-------------|
| `name` | Tool name (e.g. `AskUserQuestion`, `GeneratePrd`, `Bash`, `Read`, `Skill`) |
| `arguments` | JSON-encoded arguments string |
| `id` | Tool call ID (e.g. `call_4b6a532969b644bfa18c775e`) |
| `type` | Always `function` |
| `status` | `wait` (pending), `done` (completed with result) |
| `result` | (present when status=done) The tool's return value |

### HITL Interrupt Event Details

The `message.interrupt` event's `metaData` contains:

| Field | Description |
|-------|-------------|
| `node` | Always `_AGENT_HOOK_HITL` |
| `type` | Always `toolFeedbacks` |
| `toolFeedbacks` | JSON array of tool feedback objects with AskUserQuestion details |

### Message Query

| Action | Description | Key Parameters |
|--------|-------------|----------------|
| `ListAIStaffChatMessages` | Query chat messages (cursor-based pagination) | `ConversationId`, `PageSize`, `StartCreateTime` |

**ListAIStaffChatMessages Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ConversationId` | String | Yes | Conversation ID |
| `PageSize` | Integer | No | Number of messages per page (10-100, default 20) |
| `StartCreateTime` | String | No | Cursor — ISO datetime string; omit for first page |

**ListAIStaffChatMessages Response:**

Response is wrapped in `Module` field:

| Field | Type | Description |
|-------|------|-------------|
| `Messages` | Array | List of message objects |

Each message object contains `Content`, `Role`, `ChatId`, `ChatStatus`, `CreateTime`, etc.

**Key usage:** When `ListAIStaffChatEvents` (SSE) times out or returns no new events, use this API to check the actual `ChatStatus` of the latest message.

### Preview URL

| Action | Description | Key Parameters |
|--------|-------------|----------------|
| `GetAIStaffPreviewUrl` | Get site preview URL (starts sandbox if needed) | `ConversationId`, `Restart` |

**GetAIStaffPreviewUrl Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ConversationId` | String | Yes | Conversation ID |
| `Restart` | Boolean | No | Whether to restart the app in the sandbox (default: false) |

**GetAIStaffPreviewUrl Response:**

Response is wrapped in `Module` field:

| Field | Type | Description |
|-------|------|-------------|
| `UrlMap` | Map<String, String> | Preview URL information (keys include `https`, `http`, `sessionId`) |

**Example Response:**

```json
{
  "RequestId": "817605ED-A552-13C0-AA42-09F9808BD41C",
  "Module": {
    "UrlMap": {
      "https": "https://xxx.aliyuncs.com/...",
      "http": "http://xxx.aliyuncs.com/...",
      "sessionId": "session-xxx"
    }
  }
}
```

**Key usage:** Call this after code generation completes (`chatStatus == "success"`). The first call starts the sandbox and may take a few seconds. Use `Restart=true` to restart the app after site modifications.

## RAM Actions

| Action | RAM Permission |
|--------|---------------|
| `CreateAIStaffConversation` | `zero2staff:CreateAIStaffConversation` |
| `CreateAIStaffChat` | `zero2staff:CreateAIStaffChat` |
| `RetryAIStaffChat` | `zero2staff:RetryAIStaffChat` |
| `ListAIStaffChatEvents` | `zero2staff:ListAIStaffChatEvents` |
| `ListAIStaffChatMessages` | `zero2staff:ListAIStaffChatMessages` |
| `GetAIStaffPreviewUrl` | `zero2staff:GetAIStaffPreviewUrl` |

## Error Codes

| Code | Description |
|------|-------------|
| `CHAT_NOT_FOUND` | No active chat in conversation |
| `ILLEGAL_ACCESS` | ToB chat not enabled |
| `SYSTEM_ERROR` | Internal server error |
| `GET_PREVIEW_URL_FAILED` | Failed to get preview URL (sandbox start failure) |

## Pagination

`ListAIStaffChatEvents` uses cursor-based pagination via `LastEventId`.

- `LastEventId`: cursor position — only events with ID > this value are returned.
- `HasMore`: `true` when there are more events beyond the current page. Use the returned `LastEventId` as cursor for the next call.

## Site Link Format

After conversation creation, the site management URL is:

```
https://wanwang.aliyun.com/webdesign/home#/ai/manage/prd?conversationId=<CONV_ID>
```
