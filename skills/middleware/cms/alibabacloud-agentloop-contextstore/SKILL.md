---
name: alibabacloud-agentloop-contextstore
description: |
  Operate Alibaba Cloud CloudMonitor Service (CMS) AgentLoop ContextStore by using aliyun CLI with api version 2024-03-30. Use when users mention CloudMonitor, CMS, AgentLoop, agent loop, context, memory, experience, ContextStore, context store, 上下文库, 记忆库, 经验库, or ask to create/query/update/delete stores, write/search/update/delete context records, manage store API keys, or debug aliyun cms ContextStore commands.
---

# AgentLoop ContextStore Skill

## Scenario Description

This skill operates ContextStore resources under Alibaba Cloud CloudMonitor Service (CMS) AgentLoop. ContextStore persists long-running agent context in two store types:

- `memory`: user preferences, facts, episode summaries, and conversation-derived memories.
- `experience`: troubleshooting or task execution experience summarized from agent traces.

Architecture: `Aliyun CLI` + `CMS AgentLoop` + `ContextStore` + optional source `Log Service project/logstore` + store-level `API Key`.

Always confirm the target store `contextType` before data operations. Memory and experience stores share the same CLI product and subcommands, but their write schemas, filter field paths, and formatted outputs are different.

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low, run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update, or see `references/cli-installation-guide.md` for installation instructions.

```bash
aliyun version
```

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up to date.

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

**Pre-check: CMS plugin >= 0.2.4 required**
> ContextStore subcommands and correct typed-value handling for `experience` / `metadata` / `config.metadataField` require the CMS plugin at version `0.2.4` or later. Earlier versions silently coerce nested numbers, booleans, arrays, and null values to strings. Verify and install if necessary:
>
> ```bash
> aliyun plugin show --name cms
> # If missing or older than 0.2.4:
> aliyun plugin install --names cms --version 0.2.4
> # Or install the latest:
> aliyun plugin install --names cms
> ```

## Environment Variables

No ContextStore-specific environment variables are required. Aliyun CLI credentials and region may come from a configured CLI profile, Alibaba Cloud environment variables, STS, OAuth, or an ECS RAM role.

Never read, echo, or print secret environment variable values. Use `aliyun configure list` only to check whether a valid profile or identity is available.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

ContextStore operations require CMS AgentLoop permissions for store, context, and API key APIs. See `references/ram-policies.md` for the full action list and a policy template.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL.
> 2. If the `ram-permission-diagnose` skill is installed in the current environment, invoke it to guide the user through requesting the necessary permissions. Otherwise, surface the missing RAM action(s) plus the policy template from `references/ram-policies.md` and ask the user to attach the policy to the current RAM identity via the [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/).
> 3. Pause and wait until the user confirms that the required permissions have been granted before retrying.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** -- Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
| --- | --- | --- | --- |
| `--region` | Optional | Region override for the current CLI command. Confirm when the user does not want the configured default region. | CLI configured region |
| `--workspace` | Required | AgentLoop workspace ID. | None |
| `--context-store-name` | Required except `list-context-stores` | ContextStore name. | None |
| `--context-type` | Required for create/write flows | Store type: `memory` or `experience`. | None |
| `--memory-type` | Required for memory writes only | Memory write type: `short` or `long`. Never use for experience writes. | None |
| `--context-id` | Required for single-record get/update/delete | Context record ID. | None |
| `--items` | Required for `add-contexts` | JSON array of records to write. Schema depends on `contextType`. | None |
| `--filter` | Optional | JSON filter for `search-context` or `delete-contexts`. Field paths depend on `contextType`. | None |
| `--query` | Required for search | Semantic search query. | None |
| `--limit` | Optional | Maximum search results. | Service default |
| `--retrieval-option` | Optional | Experience search options: `reranker`, `llm_rank`, or both comma-separated. | None |
| `--config` | Optional/Required by flow | Store configuration. Required for experience stores and memory stores sourced from an existing logstore. | None |
| `--name` | Required for API key commands | Store-level API key name. | None |

## Core Workflow

> **[MUST] Enable AI-Mode** -- AI-mode is required for Agent Skill execution. Run the following commands before any CLI invocation:
>
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-contextstore"
> ```
>
> **[MUST] Disable AI-Mode at EVERY exit point** -- Before delivering the final response for ANY reason, always disable AI-mode first. This applies to workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
>
> ```bash
> aliyun configure ai-mode disable
> ```
>
> If a previous run left AI-mode enabled (e.g. due to crash, session interruption, or a forgotten exit), check current state with `aliyun configure ai-mode show` and run `aliyun configure ai-mode disable` once before the new workflow starts.

1. Classify the intent: store management, memory data, experience data, API key management, filter construction, or verification.
2. Confirm all user-customizable parameters from the table above.
3. Run the CLI and credential pre-checks. Stop if CLI version or credentials are not valid.
4. If the store type is unknown, query it before choosing a data schema:

```bash
aliyun cms --api-version 2024-03-30 get-context-store \
  --workspace <workspace> \
  --context-store-name <context_store_name>
```

5. For uncertain JSON, run a dry run before the real request:

```bash
aliyun cms --api-version 2024-03-30 <subcommand> \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --cli-dry-run
```

6. Execute the matching operation:
   - Store and API key operations: see `references/store-management.md`.
   - Memory and experience data operations: see `references/context-data-operations.md`.
   - Filter syntax: see `references/filter-syntax.md`.
7. Verify success with the command-specific checks in `references/verification-method.md`.
8. Disable AI-mode before returning the final response.

## Success Verification Method

Use `references/verification-method.md` for command validation, non-destructive store checks, data write/search checks, API key checks, and cleanup verification.

## Cleanup

Confirm destructive cleanup parameters before execution. Prefer narrow deletes (single record) over batch deletes; use store deletion only when the user explicitly confirms the entire store should be removed.

Single record:

```bash
aliyun cms --api-version 2024-03-30 delete-context \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --context-id <context_id>
```

Batch (mutually exclusive flags `--context-ids` or `--filter`; never both, never a request body):

```bash
aliyun cms --api-version 2024-03-30 delete-contexts \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --context-ids "<context_id_1>,<context_id_2>"

aliyun cms --api-version 2024-03-30 delete-contexts \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --filter '<filter_json>'
```

Records with `immutable: true` (memory) or `metadata.immutable: true` (experience) are skipped server-side and not counted in `deletedCount`.

Whole store (irreversible; system-managed datasets and internal logstores are removed; user-provided source logstores are NOT removed):

```bash
aliyun cms --api-version 2024-03-30 delete-context-store \
  --workspace <workspace> \
  --context-store-name <context_store_name>
```

API key:

```bash
aliyun cms --api-version 2024-03-30 delete-context-store-api-key \
  --workspace <workspace> \
  --context-store-name <context_store_name> \
  --name <api_key_name>
```

## Command Tables

All supported ContextStore commands, parameter rules, and validation helpers are listed in `references/related-commands.md`.

## Best Practices

1. Always include `--api-version 2024-03-30`; otherwise ContextStore subcommands may not be available.
2. Confirm `contextType` before writing, filtering, updating, or interpreting formatted output.
3. Use `--memory-type short` or `--memory-type long` only for memory writes; never pass it for experience writes.
4. Keep memory `categories`, `immutable`, and `expirationDate` at the item top level; keep experience `categories` and `immutable` inside `metadata`.
5. Quote complex JSON arguments with single quotes in shell, and use double quotes inside JSON.
6. Treat API key creation output as secret material. The plaintext secret is returned only once by `create-context-store-api-key`; never paste it into conversation history, and ask the user to store it securely outside the session.
7. Use `--cli-dry-run` before destructive operations or complex JSON requests.
8. Immutable records cannot be updated or deleted; bulk delete skips them and they do not appear in `deletedCount`.
9. Use `delete-contexts` only with `--context-ids` or `--filter`; it does not accept a request body, and the two flags are mutually exclusive.
10. `contextType`, `contextStoreName`, and `config.source` are immutable after store creation. To change the source logstore or store type, create a new store and migrate data.
11. **CMS plugin >= 0.2.4 prerequisite**: earlier plugin versions silently stringify typed values inside `experience` / `metadata` / `config.metadataField`. Verify with `aliyun plugin show --name cms` before any write operation; upgrade with `aliyun plugin install --names cms --version 0.2.4` (or omit `--version` for latest).
12. Do not write the legacy `triggerCondition` field for new experience records; the v1 schema uses `experience` (object) plus `metadata` (object).

## Common Mistakes to Avoid

| Wrong | Right | Why |
| --- | --- | --- |
| `aliyun cms add-contexts ...` (no `--api-version`) | `aliyun cms --api-version 2024-03-30 add-contexts ...` | Subcommand only exists in this API version |
| Memory write without `--memory-type` | `--memory-type short` or `--memory-type long` | Required for memory writes |
| Experience write with `--memory-type long` | Omit `--memory-type` for experience | Forbidden for experience writes |
| Experience with `categories` / `immutable` at item top level | Put them inside `metadata` | Memory uses top-level; experience uses metadata |
| Experience filter `{"serviceName":"x"}` | `{"metadata.serviceName":"x"}` | Experience metadata fields use `metadata.` prefix |
| `delete-contexts --body '{...}'` | `delete-contexts --context-ids "id1,id2"` or `--filter '{...}'` | `delete-contexts` does not accept a body |
| `metadata.traceStartNs: 1775799927869697848` (number) | `"traceStartNs": "1775799927869697848"` (string) | Bare numbers above 2^53 lose precision via Go float64 parsing |
| `echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET` | `aliyun configure list` | Never read or print AK/SK secrets |

## Reference Links

| Reference | Contents |
| --- | --- |
| `references/store-management.md` | Create, get, list, update, delete stores and manage store API keys. |
| `references/context-data-operations.md` | Memory and experience write/search/update/delete schemas and examples. |
| `references/filter-syntax.md` | Shared filter operators and memory versus experience field paths. |
| `references/related-commands.md` | Supported CLI command table and help validation commands. |
| `references/verification-method.md` | Success checks, dry-run checks, and command validation workflow. |
| `references/ram-policies.md` | Required RAM actions and policy template. |
| `references/cli-installation-guide.md` | Aliyun CLI installation and configuration guide. |
