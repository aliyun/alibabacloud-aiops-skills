---
name: alibabacloud-agentloop-dataset
description: Operate Alibaba Cloud AgentLoop Dataset resources with aliyun CLI and the AgentLoop API version 2026-05-20. Use when requests concern AgentLoop datasets, data rows, Dataset schemas, embedding fields, semantic search, ExecuteQuery, AgentSpace data, 数据集, 数据写入, 数据查询, 语义检索, or ask to create/list/get/update AgentLoop datasets, append structured rows, run read-only SQL or SearchExpr queries, inspect query results, or debug aliyun agentloop Dataset commands.
---

# AgentLoop Dataset Skill

## Scenario

Operate the public AgentLoop Dataset surface through `aliyun agentloop`:

- Manage Dataset resources and schemas.
- Append typed structured rows without constructing INSERT SQL.
- Query data with read-only `execute-query`.
- Run full-text, semantic, SQL, or search-pipe-SQL retrieval.

Do not expose or operate service deployment, database, cache, or other internal implementation details. Do not manage AgentSpaces unless the user separately requests that scope.

Treat commands and parameters exposed by the installed public AgentLoop CLI plugin as the external capability boundary. Do not expose a capability found only in backend development code until it appears in the published CLI help or public API contract.

## CLI Prerequisites

**Require Aliyun CLI 3.3.3 or later.**

```bash
aliyun version
```

**Require the AgentLoop plugin 0.7.1 or later.** This version exposes all Dataset commands used by this skill, including `add-dataset-data` and the extended `execute-query` parameters.

```bash
aliyun plugin show --name agentloop
```

If the AgentLoop plugin is missing or older than 0.7.1, install it through the configured Aliyun CLI plugin source, then verify it before continuing:

```bash
aliyun plugin install --names agentloop
aliyun plugin show --name agentloop
```

Use the plugin ID `agentloop` for installation; successful output identifies the installed package as `aliyun-cli-agentloop`. If the Aliyun CLI itself is missing or below 3.3.3, stop and ask the user to upgrade the CLI through their organization-approved process outside this session. Do not download or install CLI binaries from this Skill.

## Authentication

Use an existing Aliyun CLI profile, Alibaba Cloud environment credentials, STS, OAuth, or an instance RAM role.

Security rules:

- Never read, echo, print, or paste AccessKey IDs, AccessKey secrets, security tokens, or other credentials.
- Never ask the user to pass literal credentials in a command or conversation.
- Never run `aliyun configure set` with literal credential values.
- Use only `aliyun configure list` to check whether a usable identity and region are configured.

```bash
aliyun configure list
```

If no valid identity is available, stop and ask the user to configure credentials outside this session. Do not continue to a Dataset request.

## RAM Permissions

Dataset operations use the six concrete RAM actions listed in `references/ram-policies.md` and support Dataset resource ARNs. Do not use a wildcard action pattern in a policy.

On any permission failure:

1. Capture the API action, denied RAM action, and request ID without exposing credentials.
2. Read `references/ram-policies.md`.
3. If `ram-permission-diagnose` is installed, invoke it. Otherwise show the missing action and the least-privilege policy template.
4. Pause until the user confirms that permission was granted before retrying.

## Parameter Confirmation

Confirm user-customizable values before executing a cloud request. Reuse explicit values already supplied by the user; do not ask again.

| Parameter | Required for | Rule |
| --- | --- | --- |
| `--region` | All operations when the configured region is not explicitly accepted | Dataset and AgentSpace must be in this region. |
| `--agent-space` | All commands | Confirm the exact AgentSpace name. |
| `--dataset-name` | All Dataset commands in this skill | Use 4-63 ASCII characters matching `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`; do not use uppercase letters, hyphens, spaces, or leading, trailing, or consecutive underscores. |
| `--description` | Optional create/update description | Keep the UTF-8 encoded value at 255 bytes or fewer. |
| `--schema` | Create; optional update | Confirm field names, types, Chinese tokenization, JSON keys, and embedding use. The only supported public embedding model value is `agentloop-embedding-v4`. |
| `--data-array` | Structured writes | Confirm the rows or the source from which they are constructed. |
| `--query` | `execute-query` | This Skill permits only read-only SELECT or SearchExpr query text. The public API accepts one raw query string and exposes no bind-parameter option; the default query-text cap is 10 MiB. |
| `--from`, `--to` | Optional SELECT time window | Use non-negative Unix seconds over `__time__`; `to` is exclusive and, when both are non-zero, `from` must be less than `to`. |
| `--offset`, `--length` | Optional SELECT result window | Use non-negative integers only for SELECT; `length` cannot exceed the configured SELECT maximum, which defaults to 100,000. |
| `--max-output-length` | Optional SELECT truncation | `0` or omitted returns full values. |
| `--biz-version` | Optional SELECT against an existing snapshot | This CLI flag serializes to the request-body field `version`; confirm the exact version and omit it for current data. |
| `--client-token` | Optional create/update/write idempotency | Generate one non-secret UUID and reuse it for retries of the same logical request. |

## Observability

Generate one session ID before the first AgentLoop API request in a skill session. Generate it once, require exactly 32 lowercase hexadecimal characters, and reuse it for the entire session:

```bash
SESSION_ID="$(openssl rand -hex 16)"
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-agentloop-dataset/${SESSION_ID}"
```

The canonical CLI template is:

```bash
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-dataset/{session-id}"
```

Observability rules:

- Append `--user-agent "${USER_AGENT}"` to every `aliyun agentloop` invocation, including dry runs, retries, mutations, and verification calls. Command examples omit this repeated global flag for readability; add it before execution.
- Never generate a new session ID for an individual command or retry.
- If one workflow also uses an Alibaba Cloud SDK or Terraform, propagate the same session ID through that client's custom user-agent mechanism. Keep one session ID across CLI, SDK, and Terraform calls in the same session.
- Treat the session ID as non-secret correlation metadata. Do not substitute a request ID, account ID, AccessKey ID, or client token.
- Do not mutate global Aliyun CLI configuration to set the user agent; pass the session-scoped user agent explicitly on each request.

## Core Workflow

Execute the workflow:

1. Classify the intent: Dataset management, schema change, structured write, read-only SQL/search, or verification.
2. Confirm the target region, AgentSpace, Dataset, and operation-specific inputs.
3. Run CLI, plugin, and credential checks. Stop if any prerequisite fails.
4. Read the relevant reference:
   - Dataset CRUD and schemas: `references/dataset-management.md`
   - Structured writes and data mutations: `references/data-operations.md`
   - Search and SELECT syntax: `references/query-syntax.md`
5. For complex JSON, run the same command with `--cli-dry-run` first and inspect the serialized URL, query parameters, and body.
6. Execute the approved command.
7. Verify the result using `references/verification-method.md`.
8. Report the request ID and verification evidence without exposing credentials or secret values.

## Dataset and Schema Rules

- Treat Dataset names as unique within the target AgentSpace. A duplicate create is rejected.
- Respect the AgentSpace Dataset quota. The service fallback is 100 Datasets per AgentSpace, but the AgentSpace may supply a different quota.
- Keep create/update request bodies at 1 MiB or less.
- Require a non-empty schema.
- Use only `text`, `long`, `double`, and `json` field types.
- Use `chn` for text tokenization. It has no useful effect on non-text fields.
- Use `embedding` only on `text` or `json` fields. When present, its value must be exactly `agentloop-embedding-v4`; do not use an internal backend model name or invent another alias.
- Use `jsonKeys` only under a top-level `json` field. Each indexed child uses `type` and optional `chn`; do not add child `embedding` or another `jsonKeys` level unless current CLI help explicitly exposes those fields.
- Keep each top-level field name non-empty and at 50 UTF-8 bytes or fewer. The backend does not impose the Dataset-name pattern on fields, but prefer `lower_snake_case` to simplify SQL and case-insensitive structured writes.
- Never define reserved fields: `id`, `__time__`, `__dataset_seq`, `__effective_seq`, or `__expired_seq`.
- Keep the effective column budget within 300: three service columns plus one per top-level field plus one per generated embedding column.
- Treat schema updates as add-only. Omitted existing fields remain; changing or removing an existing definition is rejected. Fetch the current schema before constructing an update.

## Structured Write Rules

Prefer `add-dataset-data` for row appends. It avoids SQL quoting errors and validates values against the Dataset schema.

- `dataArray` must be non-empty and every entry must be an object.
- Field matching is case-insensitive, but do not send duplicate case variants.
- Unknown fields fail the request; omitted schema fields become `null`.
- `text` values must be strings, `long` values integers, `double` values finite numbers, and `json` values valid JSON.
- Omit `id` to generate one. If supplied, it must be a UUID string.
- Omit `__time__` to use the current time. If supplied, it must be a non-null, non-negative Unix timestamp in seconds.
- Never send `__dataset_seq`.
- One request is atomic: either all rows commit or none do. The request-body limit is 100 MiB; there is no separate fixed row-count limit for `add-dataset-data`.

## Query Safety

- Always pass `--type SQL`; it is the only supported statement type.
- This Skill uses `execute-query` only for read-only SELECT or SearchExpr queries. Never send INSERT, UPDATE, DELETE, DDL, or multiple statements through this command.
- The public `execute-query` contract carries raw query text and has no bind-parameter field. Do not compose SQL from untrusted text; use `add-dataset-data` for user-provided values whenever it can express the write.
- The `agentloop:ExecuteQuery` RAM action is not statement-level read-only. This Skill's SELECT-only boundary is an instruction, not a service-side control.
- Keep the `execute-query` body within the default 100 MiB cap and the query text within the default 10 MiB cap.
- Use single-dataset statements. Do not assume cross-Dataset queries or joins are supported.
- Prefer explicit columns and explicit result limits. A SELECT without a limit defaults to 1,000 rows; the configured maximum defaults to 100,000 for SQL `LIMIT` and `--length`.
- Use `columns` with each `rows` entry by position; the response is row-based, not an array of objects.
- Use `semantic_distance(field, 'query', 'l2')` with an explicit distance type. The field must have embedding enabled.
- Keep SearchExpr `similarity()` thresholds in `[0, 1]` and `topk()` values as integers from 1 through 100,000.
- Do not insert user-provided values into SQL. Use `add-dataset-data` for writes.

## Command Index

All public Dataset CLI commands, parameters, and help checks are in `references/related-commands.md`.

## Common Mistakes

| Wrong | Right | Reason |
| --- | --- | --- |
| `aliyun cms ... dataset ...` | `aliyun agentloop ...` | This skill uses the AgentLoop 2026-05-20 public API. |
| `--type sql` without checking | `--type SQL` | The service currently requires `SQL`. |
| Create with an empty schema | Supply at least one typed field | Empty schemas are rejected. |
| Update an existing field type | Add a new top-level field or update description | Schema evolution is add-only. |
| Put JSON in a `text` field | Declare/use a `json` field | Structured writes validate field types. |
| Expect `response.data` | Zip `columns` with each entry in `rows` | Query responses are row-based. |
| Use `execute-query` for a data mutation | Use `add-dataset-data` for row appends | This Skill permits `execute-query` only for read-only queries. |
| `semantic_distance(field, 'q')` | `semantic_distance(field, 'q', 'l2')` | Current Dataset execution requires an explicit distance type. |
| `--version v1` | `--biz-version v1` | Global `--version` selects the OpenAPI version; the Dataset snapshot selector is `--biz-version`. |
| Reuse a new client token on retry | Reuse the original token for the same logical request | Idempotency depends on a stable token. |

## References

| File | Use |
| --- | --- |
| `references/dataset-management.md` | Create, list, get, update, and schema construction. |
| `references/data-operations.md` | Structured row append and typed values. |
| `references/query-syntax.md` | Read-only SQL, SearchExpr, semantic retrieval, windows, and response shape. |
| `references/related-commands.md` | Supported command and parameter inventory. |
| `references/verification-method.md` | Dry-run and post-operation verification. |
| `references/ram-policies.md` | RAM actions, resource ARN, and policy examples. |
