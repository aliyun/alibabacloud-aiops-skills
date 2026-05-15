# ContextStore Store Management

All ContextStore commands use the CMS product and API version `2024-03-30`:

```bash
aliyun cms --api-version 2024-03-30 <subcommand> [flags]
```

Required parameters:

- `--workspace` for all commands.
- `--context-store-name` for all commands except `list-context-stores`.

Use `--cli-dry-run` to inspect method, URL, and request body before sending a request.

## Create Stores

### Memory Store

```bash
aliyun cms --api-version 2024-03-30 create-context-store \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-type memory \
  --description "<description>"
```

### Memory Store From an Existing Logstore

```bash
aliyun cms --api-version 2024-03-30 create-context-store \
  --workspace <workspace> \
  --context-store-name <memory_store_name> \
  --context-type memory \
  --config '{"source":{"project":"<source_project>","logstore":"<source_logstore>"}}'
```

### Experience Store

Experience stores require a source trace logstore. `startTime` format is `yyyy-MM-dd'T'HH:mm:ss'Z'`.

```bash
aliyun cms --api-version 2024-03-30 create-context-store \
  --workspace <workspace> \
  --context-store-name <experience_store_name> \
  --context-type experience \
  --description "<description>" \
  --config '{
    "source": {
      "project": "<source_project>",
      "logstore": "<source_logstore>",
      "startTime": "<start_time_utc>"
    },
    "metadataField": {
      "project": "attributes.project",
      "agentId": "attributes.agent_id",
      "errorType": "analysis.error_type"
    }
  }'
```

Constraints:

- `config.source.project` and `config.source.logstore` must be in the same region as the workspace.
- `metadataField` is supported only for experience stores.
- `contextType`, `contextStoreName`, and `config.source` are not mutable after creation.

## Query, List, Update, Delete Stores

```bash
aliyun cms --api-version 2024-03-30 get-context-store \
  --workspace <workspace> \
  --context-store-name <context_store_name>
```

```bash
aliyun cms --api-version 2024-03-30 list-context-stores \
  --workspace <workspace> \
  --context-type <memory_or_experience> \
  --max-results <max_results>
```

```bash
aliyun cms --api-version 2024-03-30 update-context-store \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --description "<new_description>" \
  --config '{"metadataField":{"project":"attributes.project","errorType":"analysis.error_type"}}'
```

```bash
aliyun cms --api-version 2024-03-30 delete-context-store \
  --workspace <workspace> \
  --context-store-name <context_store_name>
```

Deletion removes system-managed datasets and internal logstores created for the store. User-provided source logstores are not deleted.

## Store-Level API Keys

API keys are scoped to one ContextStore and cannot be reused across stores. The `create-context-store-api-key` response returns the secret value only once.

```bash
aliyun cms --api-version 2024-03-30 create-context-store-api-key \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --name <api_key_name>
```

```bash
aliyun cms --api-version 2024-03-30 list-context-store-api-keys \
  --workspace <workspace> \
  --context-store-name <context_store_name>
```

```bash
aliyun cms --api-version 2024-03-30 delete-context-store-api-key \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --name <api_key_name>
```
