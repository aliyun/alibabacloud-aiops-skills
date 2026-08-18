# Experience Store Management (ContextStore)

An "experience library" is an AgentLoop **ContextStore** created with `--context-type experience`. Manage it with the AgentLoop product and its fixed API version `2026-05-20`:

```bash
aliyun agentloop <subcommand> [flags]
```

This file covers the store lifecycle (create, list, get, update, delete) and API Key management. It requires the aliyun CLI with the `aliyun-cli-agentloop` plugin. Recalling content from an existing store does not use these commands; that is the local recall CLI described in [references/experience/experience.md](experience.md).

## Command Map

| Goal | Command |
| --- | --- |
| Create a store | `create-context-store` |
| List stores in an AgentSpace | `list-context-stores` |
| Inspect one store | `get-context-store` |
| Update config, description, or mining status | `update-context-store` |
| Delete a store | `delete-context-store` |
| Manage recall API Keys | `create-context-store-api-key`, `get-context-store-api-key`, `list-context-store-api-keys`, `delete-context-store-api-key` |
| Server-side search (connectivity check) | `search-context` |

## Backend-Enforced Rules for `experience` Stores

CLI flag validation only checks the top-level required flags. The `experience`-specific config rules below are enforced by the backend at create time, so validate them before dry-run instead of discovering them through 400 errors:

| Input | Constraint |
| --- | --- |
| `--agent-space` | Required. 2-64 characters. The AgentSpace must already exist; `list-context-stores` returns an empty list (not an error) for a nonexistent AgentSpace, while `get-agent-space` reports `AgentSpaceNotExist`. |
| `--context-store-name` | Required. 2-64 characters matching `^[a-z0-9_]+$`: lowercase letters, digits, and underscores only. **Hyphens are rejected.** Must be unique within the AgentSpace. |
| `--context-type` | Required. Use `experience` for an experience library; `memory` is a separate type. |
| `--config` | **Required for `experience`.** Omitting it fails with a backend error even though the flag is optional in CLI help. |
| `config.serviceNames` | **Must be a non-empty string array** for `experience`. These are the service names whose traces feed experience mining. |
| `config.source` | **Required for `experience`.** Object `{"agentSpace": string, "startTime": string}` describing where and since when the mining pipeline reads data. Use the same AgentSpace name unless mining from another space, and a start-time string accepted by the backend. |
| `config.miningInterval` | Optional string controlling the mining schedule. |
| `config.metadataField` | Optional string map for custom metadata field mapping. |

## Create an Experience Store

Name the store with underscores, not hyphens. A hyphenated name fails at create time with `400 InvalidParams` and the message `contextStoreName may only contain lowercase letters, digits, and underscores`. This is a backend check that CLI flag validation and `--cli-dry-run` do not catch, and it is the opposite of the Pipeline convention, where `--pipeline-name` requires hyphens and rejects underscores. See the resource-name table in the router `SKILL.md`. A valid name looks like `harness_exp_store`, not `harness-exp-store`.

```bash
aliyun agentloop create-context-store \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --context-store-name <store_name> \
  --context-type experience \
  --description "<description>" \
  --config '{
    "serviceNames": ["<service_name>"],
    "source": {"agentSpace": "<agent_space_name>", "startTime": "<start_time>"}
  }' \
  --client-token <client_token>
```

Before executing, append `--cli-dry-run` and verify the body contains `contextStoreName`, `contextType`, and a `config` object with a non-empty `serviceNames` array and a `source` object.

## List and Get

```bash
aliyun agentloop list-context-stores \
  --agent-space <agent_space_name> \
  --context-type experience

aliyun agentloop get-context-store \
  --agent-space <agent_space_name> \
  --context-store-name <store_name>
```

`list-context-stores` supports `--context-store-name` (exact match), `--max-results` (default 20, max 100), and `--next-token` paging.

## Update

```bash
aliyun agentloop update-context-store \
  --agent-space <agent_space_name> \
  --context-store-name <store_name> \
  --config '{...}' \
  --description "<description>"
```

`--config` is a full overwrite: passing it replaces the whole config object, so fetch the current config with `get-context-store` and resend the complete object with your change applied. `--context-type` is normally immutable after create. `--status` applies only to `experience` stores and toggles the mining state; its legal values are defined by the backend.

## Delete

Deletion is destructive and removes the store and its mined experience content. Run `get-context-store` first, show the user what will be deleted, and proceed only after explicit confirmation.

```bash
aliyun agentloop delete-context-store \
  --agent-space <agent_space_name> \
  --context-store-name <store_name>
```

## API Keys for Recall

API Key auth is what the local recall CLI uses in `AGENTLOOP_BEARER_API_KEY` mode:

```bash
aliyun agentloop create-context-store-api-key \
  --agent-space <agent_space_name> \
  --context-store-name <store_name> \
  --name <key_display_name>

aliyun agentloop list-context-store-api-keys \
  --agent-space <agent_space_name> \
  --context-store-name <store_name>
```

`get-context-store-api-key --name <key_display_name>` returns the key value. Treat it as a secret: write it directly into `recall.env` (gitignored), never echo it into chat, logs, or command arguments.

## Recall Endpoint Format

The SearchContext endpoint of a store — the value for `AGENTLOOP_RECALL_ENDPOINT` in `recall.env` (AK/SK mode) — follows the ROA path used by the service:

```text
https://agentloop.<region_id>.aliyuncs.com/agentspace/<agent_space_name>/contextstore/<store_name>/context/search
```

In API Key mode the CLI reuses the same origin but posts to `/v2/memories/search`; see [references/experience/search-context-cli.md](search-context-cli.md).

## Connectivity Check

To verify a store answers searches without configuring `recall.env`, use the server-side command with your aliyun CLI credentials:

```bash
aliyun agentloop search-context \
  --agent-space <agent_space_name> \
  --context-store-name <store_name> \
  --query "<probe text>" \
  --limit 5 --threshold "0.1"
```

An empty `results` array with HTTP 200 means the store is reachable but has no matching mined content yet; mining runs on the configured `source`/`miningInterval`, so a freshly created store is expected to return empty.
