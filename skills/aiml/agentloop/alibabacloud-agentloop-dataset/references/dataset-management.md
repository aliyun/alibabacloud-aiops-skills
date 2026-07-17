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
