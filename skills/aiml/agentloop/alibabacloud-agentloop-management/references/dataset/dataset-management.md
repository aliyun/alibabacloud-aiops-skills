# Dataset Management

Use the AgentLoop product and its fixed API version `2026-05-20`:

```bash
aliyun agentloop <subcommand> [flags]
```

## Backend-Enforced Limits

| Input or resource | Constraint |
| --- | --- |
| Dataset name | 4-63 ASCII characters matching `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`; no uppercase letters, hyphens, spaces, or leading, trailing, or consecutive underscores. |
| Dataset identity | The name must be unique within the target AgentSpace for the caller. |
| Dataset count | Creation is limited by the AgentSpace Dataset quota; the service fallback is 100, but an AgentSpace-provided quota takes precedence. |
| Description | At most 255 UTF-8 bytes. Empty is allowed. |
| Create/update body | The serialized JSON request body must be at most 1 MiB. |
| Schema | Must contain at least one top-level field on create. |
| Top-level field name | Non-empty and at most 50 UTF-8 bytes. Reserved system names are rejected. The backend does not require the Dataset-name pattern for fields; prefer `lower_snake_case` for reliable SQL usage. |
| Effective columns | At most 300, calculated as three service columns plus one per top-level field plus one per generated embedding column. |

Validate these constraints before dry-run. Do not retry a duplicate-name or quota failure without changing the name, deleting an unused Dataset, or obtaining a quota adjustment.

## Schema Shape

The schema is a JSON object keyed by field name. Supported types are `text`, `long`, `double`, and `json`.

```json
{
  "question": {
    "type": "text",
    "chn": true,
    "embedding": "agentloop-embedding-v4"
  },
  "answer": {
    "type": "text",
    "chn": true
  },
  "score": {
    "type": "double"
  },
  "metadata": {
    "type": "json",
    "jsonKeys": {
      "source": {"type": "text"},
      "latency_ms": {"type": "long"}
    }
  }
}
```

Use `embedding` only for top-level `text` or `json`. The only supported public value is `agentloop-embedding-v4`; internal backend model names are not valid public schema values. Each `jsonKeys` child uses `type` and optional `chn`; the current CLI does not expose child `embedding` or a deeper `jsonKeys` level. Do not define `id`, `__time__`, `__dataset_seq`, `__effective_seq`, or `__expired_seq`. Avoid top-level field names that differ only by case because structured row writes resolve fields case-insensitively.

## Create

```bash
aliyun agentloop create-dataset \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --description "<description>" \
  --schema '{
    "question":{"type":"text","chn":true,"embedding":"agentloop-embedding-v4"},
    "answer":{"type":"text","chn":true},
    "score":{"type":"double"},
    "metadata":{"type":"json","jsonKeys":{"source":{"type":"text"},"latency_ms":{"type":"long"}}}
  }' \
  --client-token <client_token>
```

Before executing, append `--cli-dry-run` and verify that the body contains `datasetName`, `description`, and the typed `schema` object.

Also verify that the serialized body is no larger than 1 MiB, the description is no larger than 255 UTF-8 bytes, and the effective-column calculation does not exceed 300.

## Get

`get-dataset` returns the full public schema.

```bash
aliyun agentloop get-dataset \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name>
```

## List and Paginate

`--dataset-name` is an optional name filter. `maxResults` defaults to 100 and accepts 1-100.

```bash
aliyun agentloop list-datasets \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <optional_name_filter> \
  --max-results 100
```

For the next page, reuse the prior response's `nextToken` without modifying it:

```bash
aliyun agentloop list-datasets \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --max-results 100 \
  --next-token '<next_token>'
```

Do not change the name filter between pages because the pagination token is bound to the list conditions.

## Update Description

Keep the new description at 255 UTF-8 bytes or fewer.

```bash
aliyun agentloop update-dataset \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --description "<new_description>" \
  --client-token <client_token>
```

## Add Schema Fields

Fetch the Dataset first. Build `--schema` from only new top-level fields; omitted existing fields remain unchanged.

```bash
aliyun agentloop update-dataset \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --schema '{"reviewer":{"type":"text"},"review_score":{"type":"double"}}' \
  --client-token <client_token>
```

Do not change or remove existing field definitions. In particular, do not change an existing field's type, `chn`, `embedding`, or nested `jsonKeys` structure.

## Delete

`delete-dataset` removes the Dataset and every row in it. There is no undo, no soft-delete window, and no per-row deletion command: this is the only supported way to remove Dataset data, so it is also the command reached for when the intent is merely "clean up test rows".

```bash
aliyun agentloop delete-dataset \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name>
```

Measured surface: `--agent-space` and `--dataset-name` are the only required flags. **`delete-dataset` accepts no `--client-token`**, unlike create, update, and `add-dataset-data`. A retry after an ambiguous failure is therefore not idempotent-by-token; re-check with `get-dataset` instead of blindly resending.

Required protocol before executing:

1. Run `get-dataset` and show the user the exact Dataset name, AgentSpace, region, and schema that will be destroyed.
2. Report the row count so the user sees the size of what is being deleted:
   ```bash
   aliyun agentloop execute-query \
     --region <region_id> \
     --agent-space <agent_space_name> \
     --dataset-name <dataset_name> \
     --type SQL \
     --query 'SELECT COUNT(*) AS row_count FROM <dataset_name>'
   ```
3. Get explicit confirmation for that one named Dataset. Do not accept a prior approval given for a different Dataset, and do not accept a pattern or wildcard as authorization.
4. Delete one Dataset per command. Never loop over `list-datasets` output to delete in bulk, even when the user asks for a cleanup.
5. Verify with `get-dataset`, which must then report the Dataset as absent.

Check for dependents first. A Pipeline whose sink is this Dataset keeps writing to a name that no longer exists, and an evaluation task reading it will fail. Search for a Pipeline sink pointing at the Dataset before deleting it, and tell the user what will break.

Deleting and recreating a Dataset under the same name is not a schema-migration tool. Schema updates are add-only by design; if the user wants to change a field type, say so explicitly rather than silently proposing delete-then-recreate, because the rows are lost.

## Structural Migration After Materialization

An add-only schema update changes the schema definition; it does not backfill rows already written. If a Pipeline or bulk import populated a Dataset without required fields such as raw `input`, raw `output`, or lineage, do not treat an in-place schema extension as a repair:

1. Freeze the corrected output and consumer field contract.
2. Preserve the existing Dataset as migration evidence.
3. Create a versioned Dataset with the complete corrected schema.
4. Create a versioned Pipeline or import job that emits every required field.
5. Preview and reconcile the new target against the original source using `references/pipeline/verification-method.md`.
6. Smoke-test downstream Evaluation or Experiment variable mapping.
7. Switch consumers only after acceptance. Delete the old Dataset only when the user explicitly authorizes cleanup.

Rerunning corrected output into the old Dataset can mix old null rows with new rows and can duplicate source records. A create/update `clientToken` is not a Dataset-row deduplication key.
