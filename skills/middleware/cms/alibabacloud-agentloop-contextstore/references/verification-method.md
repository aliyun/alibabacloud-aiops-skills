# Verification Method

Use this workflow to validate the generated ContextStore commands before running user-impacting operations.

## 1. Local CLI Checks

```bash
aliyun version
aliyun plugin show --name cms
aliyun configure list
```

Expected:

- `aliyun version` is `3.3.3` or later.
- `aliyun plugin show --name cms` reports `Version: 0.2.4` or later. If older, upgrade with `aliyun plugin install --names cms` (or pin with `--version 0.2.4`). Earlier versions stringify typed values inside `experience` / `metadata` / `config.metadataField` and will silently corrupt writes.
- `aliyun configure list` shows a valid profile or identity without revealing secrets.

## 2. Command Surface Validation

Validate the subcommand and parameter surface before using a command in a workflow:

```bash
aliyun cms --api-version 2024-03-30 <subcommand> help
```

Subcommands to validate:

- `create-context-store`
- `get-context-store`
- `list-context-stores`
- `update-context-store`
- `delete-context-store`
- `add-contexts`
- `get-context`
- `search-context`
- `update-context`
- `delete-context`
- `delete-contexts`
- `create-context-store-api-key`
- `list-context-store-api-keys`
- `delete-context-store-api-key`

Check that each parameter used by the workflow appears in the help output, including `--workspace`, `--context-store-name`, `--context-type`, `--memory-type`, `--items`, `--filter`, `--query`, `--context-id`, `--context-ids`, `--retrieval-option`, `--experience`, and `--metadata`.

## 3. Dry-Run Validation

For complex JSON or destructive commands, append `--cli-dry-run` and inspect method, URL, query parameters, and body.

```bash
aliyun cms --api-version 2024-03-30 add-contexts \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --context-type memory \
  --memory-type long \
  --items '[{"content":"<content>","userId":"<user_id>"}]' \
  --cli-dry-run
```

Expected:

- JSON stays intact after shell parsing.
- `--api-version 2024-03-30` is present.
- Memory write includes `--memory-type`; experience write omits it.
- Typed values inside `experience` / `metadata` (numbers, booleans, arrays, null, nested objects) appear with their original types in the dry-run `Body:` output. If they appear stringified, the CMS plugin is older than `0.2.4`; upgrade with `aliyun plugin install --names cms`.
- `metadata.traceStartNs` / `metadata.traceEndNs` were passed as JSON strings (the only fields large enough to require it).

## 4. Store Verification

After creating or updating a store:

```bash
aliyun cms --api-version 2024-03-30 get-context-store \
  --workspace <workspace> \
  --context-store-name <context_store_name>
```

Expected:

- The response includes the requested store name.
- `contextType` matches the intended type.
- Mutable fields such as `description` or `metadataField` reflect updates.

## 5. Data Verification

After `add-contexts`, capture the returned context IDs, then verify one record:

```bash
aliyun cms --api-version 2024-03-30 get-context \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --context-id <context_id> \
  --formatted=false
```

Then verify retrieval:

```bash
aliyun cms --api-version 2024-03-30 search-context \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --query "<search_query>" \
  --limit 5
```

Expected:

- `get-context` returns the written content or raw `experience` and `metadata`.
- `search-context` returns relevant records for the semantic query.

## 6. API Key Verification

After creating an API key, do not expose the returned secret in chat. Verify key metadata by listing keys:

```bash
aliyun cms --api-version 2024-03-30 list-context-store-api-keys \
  --workspace <workspace> \
  --context-store-name <context_store_name>
```

Expected:

- The key name appears in the list.
- Secret material is not required for verification.

## 7. Cleanup Verification

After deleting a context or store, run the corresponding get/list command and confirm the deleted object no longer appears. Do not run cleanup against production resources unless the user explicitly confirms the exact IDs or store name.
