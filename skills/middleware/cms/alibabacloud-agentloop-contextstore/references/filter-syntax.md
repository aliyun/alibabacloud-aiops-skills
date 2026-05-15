# ContextStore Filter Syntax

`search-context` and `delete-contexts` share the same filter syntax.

## Operators

| Operation | Example |
| --- | --- |
| Exact match | `{"userId": "<user_id>"}` |
| Field exists | `{"agentId": "*"}` |
| Equal / not equal | `{"metadata.severity": {"eq": "high"}}`, `{"metadata.severity": {"ne": "low"}}` |
| Range | `{"createdAt": {"gte": "2026-04-01T00:00:00Z"}}` |
| Contains / case-insensitive contains | `{"metadata.topic": {"contains": "debug"}}`, `{"metadata.topic": {"icontains": "debug"}}` |
| In list | `{"metadata.taskType": {"in":["troubleshooting","knowledge_retrieval"]}}` |

## Logic

Top-level multiple keys are combined as `AND`. Explicit `AND`, `OR`, and `NOT` are supported. Maximum nesting depth is 4.

```json
{
  "AND": [
    {"userId": "<user_id>"},
    {"OR": [
      {"metadata.scene": "debugging"},
      {"metadata.scene": "monitoring"}
    ]},
    {"NOT": {"agentId": "deprecated-agent"}}
  ]
}
```

`NOT` takes one condition object, not an array.

## Memory Filter Fields

Use direct field names for system fields and user metadata:

- `userId`
- `agentId`
- `appId`
- `runId`
- `categories`
- `immutable`
- `createdAt`
- User metadata keys such as `topic` or `source`

Example:

```json
{
  "userId": "<user_id>",
  "categories": {"contains": "preference"},
  "createdAt": {"gte": "2026-04-01T00:00:00Z"}
}
```

## Experience Filter Fields

Use `metadata.<field>` for experience metadata fields:

- `metadata.serviceName`
- `metadata.taskType`
- `metadata.complexity`
- `metadata.confidence`
- `metadata.traceId`
- `metadata.version`
- `metadata.sessionId`
- `metadata.categories`
- `metadata.immutable`
- `createdAt`
- `updatedAt`

Example:

```json
{
  "metadata.serviceName": "sls-sop-daily",
  "metadata.taskType": {"in":["troubleshooting","knowledge_retrieval"]},
  "metadata.confidence": {"gte": 0.8}
}
```
