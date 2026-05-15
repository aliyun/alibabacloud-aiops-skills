# Context Data Operations

Memory and experience stores share ContextStore data subcommands, but their item schemas and filter fields are different. Query `get-context-store` first when the store type is unknown.

## Prerequisites

- Aliyun CLI >= 3.3.3 with the CMS plugin >= 0.2.4 installed (see SKILL.md "Installation").
- Always `--cli-dry-run` before a real write to confirm the serialized HTTP body matches your intent.

## Legacy Field Note

The CLI `--items` structure still exposes `triggerCondition`, which belonged to a previous experience schema. The current v1 experience schema uses `experience` (object) plus `metadata` (object). Do not write or update `triggerCondition` for new experience records.

## Memory Writes

Memory writes require `--context-type memory` and `--memory-type`.

`--memory-type short` writes short-term message events. At least one of `userId`, `agentId`, `appId`, or `runId` is required. `infer: true` lets the service asynchronously extract long-term memory. Short-term memory defaults to a 30-day TTL.

```bash
aliyun cms --api-version 2024-03-30 add-contexts \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-type memory \
  --memory-type short \
  --items '[{
    "messages": [{"role":"user","content":"<message_content>"}],
    "userId": "<user_id>",
    "agentId": "<agent_id>",
    "metadata": {"source":"dialog"},
    "infer": true,
    "customInstructions": "<memory_extraction_instruction>"
  }]'
```

`--memory-type long` writes long-term memory directly.

```bash
aliyun cms --api-version 2024-03-30 add-contexts \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-type memory \
  --memory-type long \
  --items '[{
    "content": "<long_term_memory_text>",
    "userId": "<user_id>",
    "agentId": "<agent_id>",
    "metadata": {"source":"user_confirmed","topic":"debugging_preference"},
    "categories": ["preference"],
    "immutable": false,
    "expirationDate": "<yyyy-mm-dd>"
  }]'
```

Memory field placement:

- `categories`, `immutable`, and `expirationDate` are item top-level fields.
- User metadata keys can be filtered directly, such as `topic` or `source`.
- When user metadata conflicts with system fields (`userId` / `agentId` / `appId` / `runId` / `categories` / `immutable` / `hash` / `createdAt` / `updatedAt` / `expirationDate`), the user-provided value takes precedence.

## Memory Get, Search, Update, Delete

```bash
aliyun cms --api-version 2024-03-30 get-context \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-id <context_id>
```

`formatted=true` is the default and returns assembled text plus metadata for agent prompts. Use `--formatted=false` to inspect raw content and payload.

```bash
aliyun cms --api-version 2024-03-30 search-context \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --query "<search_query>" \
  --limit <limit> \
  --filter '{
    "userId": "<user_id>",
    "categories": {"contains": "preference"},
    "createdAt": {"gte": "<start_time_utc>"}
  }'
```

```bash
aliyun cms --api-version 2024-03-30 update-context \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-id <context_id> \
  --content "<updated_memory_text>" \
  --payload '{"topic":"debugging_preference","categories":["preference"]}'
```

`--payload` uses JSON merge-patch semantics. Omitted fields remain unchanged.

```bash
aliyun cms --api-version 2024-03-30 delete-context \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-id <context_id>
```

```bash
aliyun cms --api-version 2024-03-30 delete-contexts \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-ids "<context_id_1>,<context_id_2>"
```

```bash
aliyun cms --api-version 2024-03-30 delete-contexts \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --filter '{"userId":"<user_id>"}'
```

## Experience Writes

Experience writes use `--context-type experience` and must not include `--memory-type`.

```bash
aliyun cms --api-version 2024-03-30 add-contexts \
  --workspace <workspace> \
  --context-store-name <experience_store_name> \
  --context-type experience \
  --items '[{
    "experience": {
      "userQuestion": "<user_question>",
      "taskDescription": "<task_description>",
      "taskType": "troubleshooting",
      "complexity": "medium",
      "confidence": 0.95,
      "experience": "<experience_summary>",
      "taskPlanning": "<task_plan>"
    },
    "metadata": {
      "traceId": "<trace_id>",
      "version": "v1",
      "serviceName": "<service_name>",
      "sessionId": "<session_id>",
      "traceStartNs": "1775799927869697848",
      "traceEndNs": "1775799959938866990",
      "categories": ["debugging"],
      "immutable": false,
      "qualityScore": null,
      "humanLabel": null
    }
  }]'
```

Experience field placement:

- `categories`, `immutable`, and other semantic fields belong inside `metadata`.
- `experience.experience` is the main experience body.
- `experience.userQuestion` and `experience.taskDescription` participate in semantic recall.
- `metadata.version` identifies the schema version, currently `v1`.
- Do not pass `triggerCondition` for new experience records; it is a legacy field.
- `metadata.traceStartNs` / `metadata.traceEndNs` are nanosecond timestamps that exceed Go float64 safe range — **pass them as JSON strings** (as shown above). The CLI parses the string as int64 and serializes it as a precise number in the HTTP body. Plain numeric input would lose the last few digits. Other numeric fields (`confidence`, `qualityScore`, etc.) stay below 2^53 and are safe as plain numbers.

## Experience Get, Search, Update, Delete

```bash
aliyun cms --api-version 2024-03-30 get-context \
  --workspace <workspace> \
  --context-store-name <experience_store_name> \
  --context-id <context_id>
```

`formatted=true` is the default and returns an XML string in `context`, while retaining the full metadata object for display and debugging. Use `--formatted=false` to get the raw `experience` and `metadata` objects.

```bash
aliyun cms --api-version 2024-03-30 search-context \
  --workspace <workspace> \
  --context-store-name <experience_store_name> \
  --query "<search_query>" \
  --limit <limit> \
  --retrieval-option "reranker,llm_rank" \
  --filter '{
    "metadata.serviceName": "<service_name>",
    "metadata.taskType": {"in":["troubleshooting","knowledge_retrieval"]},
    "metadata.confidence": {"gte": 0.8}
  }'
```

`--retrieval-option` accepts `reranker`, `llm_rank`, or both comma-separated. When both are used, execution order is `reranker` then `llm_rank`.

```bash
aliyun cms --api-version 2024-03-30 update-context \
  --workspace <workspace> \
  --context-store-name <experience_store_name> \
  --context-id <context_id> \
  --experience '{"confidence": 0.98}' \
  --metadata '{"qualityScore": 4.5, "humanLabel": "verified"}'
```

`--experience` and `--metadata` are merged independently. Updating recall text such as `userQuestion` or `taskDescription` causes the service to regenerate embedding.

```bash
aliyun cms --api-version 2024-03-30 delete-context \
  --workspace <workspace> \
  --context-store-name <experience_store_name> \
  --context-id <context_id>
```

```bash
aliyun cms --api-version 2024-03-30 delete-contexts \
  --workspace <workspace> \
  --context-store-name <experience_store_name> \
  --filter '{"metadata.serviceName":"<service_name>","metadata.confidence":{"lt":0.5}}'
```

Records with `immutable: true` or `metadata.immutable: true` cannot be updated or deleted. Bulk delete skips immutable records and does not count them in `deletedCount`.
