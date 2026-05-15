---
name: alibabacloud-cms-dataset
description: |
  Alicloud CMS Dataset lifecycle management and querying skill.
  Covers listing, inspecting, creating, updating, deleting datasets and executing dataset queries
  via the aliyun CLI (CMS API version 2024-03-30).
  Triggers: "CMS dataset", "数据集", "创建数据集", "查询数据集", "dataset 查询",
  "ExecuteQuery", "CreateDataset", "GetDataset", "ListDatasets", "UpdateDataset", "DeleteDataset".
---

# CMS Dataset Lifecycle Management and Querying

Manage CloudMonitor (CMS) dataset resources — list, inspect, create, update, delete datasets and execute dataset-level queries — using the `aliyun` CLI.

**Architecture**: `CMS Workspace + Dataset (Schema + Fields) + ExecuteQuery`

---

## Installation

### Install Aliyun CLI

Run `aliyun version` to verify if version >= `3.3.3`. If not installed or outdated, follow the doc [references/cli-installation-guide.md](references/cli-installation-guide.md) to install or update.

### Ensure plugins up-to-date

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

## AI-Mode Lifecycle

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cms-dataset"
> ```

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> ```bash
> aliyun configure ai-mode disable
> ```

---

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

---

## RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for the full permission list.

Minimum required actions: `cms:ListDatasets`, `cms:GetDataset`, `cms:CreateDataset`, `cms:UpdateDataset`, `cms:DeleteDataset`, `cms:ExecuteQuery`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
| --- | --- | --- | --- |
| `workspace` | Required | CMS workspace ID | — |
| `dataset-name` | Required (except ListDatasets) | Dataset name (4-63 chars) | — |
| `region` | Optional | Region ID | CLI profile region |
| `schema` | Required (CreateDataset) | Schema JSON object | — |
| `description` | Optional | Dataset description | — |
| `query` | Required (ExecuteQuery) | Query text | — |
| `type` | Auto-filled (ExecuteQuery) | Query type placeholder. Always `SQL`, do not ask user | `SQL` |
| `max-results` | Optional (ListDatasets) | Max results per page | — |
| `next-token` | Optional (ListDatasets) | Pagination token for next page | — |

---

## Naming Rules

Dataset names and schema field names must satisfy:
- Length: 4-63 characters
- Start with a lowercase letter
- Only lowercase letters, digits, and underscores
- No leading/trailing underscore, no consecutive underscores

Regex: `^[a-z](?!.*__)[a-z0-9_]{2,61}[a-z0-9]$`

Invalid names must NOT be silently normalized. Ask the user for a valid replacement.

---

## Core Workflow

> **[CRITICAL] Product Binding:** All dataset operations in this skill use the **`cms` product ONLY**.
> The correct command pattern is `aliyun cms <action> --api-version 2024-03-30`.
> **DO NOT** use any other product for dataset operations — `dataworks`, `adb`, `sls`, `maxcompute`, `opensearch`, `pai`, `dashvector`, or any other service are **WRONG** for this scenario.
> If a command fails, check parameters and permissions — do NOT switch to a different product.

All commands use `--api-version 2024-03-30`. Do not pass `--endpoint` by default. Use `--region` (not `--region-id`) when specifying a region.

### 0. Verify Workspace Exists

> **[MUST]** Before executing any dataset operation, call `get-workspace` to verify the workspace exists. Do NOT skip this step or use ListDatasets to infer workspace existence.

```bash
aliyun cms get-workspace --api-version 2024-03-30 \
  --workspace <workspace>
```

If the workspace does not exist (returns error), create it via `put-workspace`:

```bash
aliyun cms put-workspace --api-version 2024-03-30 \
  --workspace-name <workspace> \
  --sls-project <sls-project>
```

`--sls-project` is required. If the user does not specify one, use the same value as the workspace name.

### 1. List Datasets

```bash
aliyun cms list-datasets --api-version 2024-03-30 \
  --workspace <workspace> \
  [--dataset-name <filter>] \
  [--max-results <n>] \
  [--next-token <token>]
```

### 2. Get Dataset

```bash
aliyun cms get-dataset --api-version 2024-03-30 \
  --workspace <workspace> \
  --dataset-name <dataset-name>
```

### 3. Create Dataset

**Safety:** Before creating, check whether the dataset already exists via ListDatasets. If the dataset already exists, inform the user and ask whether to proceed (the API will return an error for duplicates). Always call CreateDataset when the user requests creation — do not silently skip it.

Pass the schema JSON directly as a single-quoted string:

```bash
aliyun cms create-dataset --api-version 2024-03-30 \
  --workspace <workspace> \
  --dataset-name <dataset-name> \
  --schema '{"message_text":{"type":"text","chn":true,"embedding":"text-embedding-v4"},"service_name":{"type":"text","chn":false}}' \
  [--description "<description>"]
```

**Schema rules:**
- The `--schema` value is the field definitions object directly (not wrapped in an API body).
- Each top-level key is a field name. Each value has: `type`, optional `chn`, optional `embedding`, optional `jsonKeys`.
- Only `type: "text"` fields may enable `embedding`. Reject embedding on non-text fields.
- `jsonKeys` defines nested JSON key structures. Nested keys support `type` and `chn` only (no `embedding`):

```json
{
  "event_data": {
    "type": "text",
    "chn": false,
    "jsonKeys": {
      "source": {
        "type": "text",
        "chn": false
      },
      "message": {
        "type": "text",
        "chn": true
      }
    }
  }
}
```

### 4. Update Dataset

**Safety:** Read and show the current description before updating.

**Limitation:** UpdateDataset can only modify the description. Schema cannot be updated through this API. If the user needs to change the schema, they must delete and recreate the dataset.

```bash
# Show current state
aliyun cms get-dataset --api-version 2024-03-30 \
  --workspace <workspace> --dataset-name <dataset-name>

# Update after user confirms
aliyun cms update-dataset --api-version 2024-03-30 \
  --workspace <workspace> \
  --dataset-name <dataset-name> \
  --description "<new-description>"
```

### 5. Delete Dataset

**Safety:** Read and show the dataset, then ask for explicit confirmation identifying workspace and dataset name before deleting.

```bash
# Show dataset to confirm
aliyun cms get-dataset --api-version 2024-03-30 \
  --workspace <workspace> --dataset-name <dataset-name>

# Delete after explicit confirmation
aliyun cms delete-dataset --api-version 2024-03-30 \
  --workspace <workspace> \
  --dataset-name <dataset-name>
```

### 6. Execute Query

**Safety:** When possible, inspect the dataset schema first via GetDataset so field names come from the actual schema.

```bash
aliyun cms execute-query --api-version 2024-03-30 \
  --workspace <workspace> \
  --dataset-name <dataset-name> \
  --type SQL \
  --query '<query>'
```

- `--type` is a required placeholder. Always pass `SQL`.
- If the user provides a complete query, preserve it except for safe shell quoting.
- **Natural-language to query:** When the user describes an analysis intent in natural language instead of providing a query, first call GetDataset to retrieve the actual schema and field names, then generate a query based on those field names. Never guess field names without inspecting the schema.
- Present the full JSON response first, then summarize: progress, returned rows, affected rows, and elapsed time.

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for step-by-step verification commands for each operation.

---

## Cleanup

To remove a dataset created during this session:

```bash
aliyun cms delete-dataset --api-version 2024-03-30 \
  --workspace <workspace> \
  --dataset-name <dataset-name>
```

---

## Output Expectations

- Show complete JSON first for any API response.
- Then provide a short human-readable summary.
- For write previews: include workspace, dataset name, region, description, and full schema.
- For query results: include progress, row count, affected rows, and elapsed time.

---

## Command Tables

See [references/related-commands.md](references/related-commands.md) for the full command reference.

| Command | Description |
| --- | --- |
| `aliyun cms get-workspace` | Verify workspace exists |
| `aliyun cms put-workspace` | Create or update a workspace |
| `aliyun cms list-datasets` | List datasets in a workspace |
| `aliyun cms get-dataset` | Get dataset details and schema |
| `aliyun cms create-dataset` | Create a new dataset with schema |
| `aliyun cms update-dataset` | Update dataset description |
| `aliyun cms delete-dataset` | Delete a dataset |
| `aliyun cms execute-query` | Execute a query against a dataset |

---

## Best Practices

1. Always specify `--api-version 2024-03-30` — the default CMS version (`2019-01-01`) does not support dataset operations.
2. Validate dataset names and field names against the naming regex before calling CreateDataset.
3. Use GetDataset to inspect schema before generating queries — use actual field names, not guesses.
4. Pass schema JSON directly as a single-quoted string to avoid shell quoting issues.
5. Always confirm write operations (Create, Update, Delete) with the user before execution.
6. Check dataset existence before creating to avoid duplicates.
7. Use `--region` (not `--region-id`) when specifying a region explicitly.
8. Do not pass `--endpoint` unless explicitly required; if needed, use `cms.<region>.aliyuncs.com`.
9. For ExecuteQuery, always pass `--type SQL` as a required placeholder.
10. Prefer inline JSON for `--schema` to avoid temporary file management.
11. **Never switch products.** If a `cms` command fails, debug parameters/permissions — do not try `dataworks`, `adb`, `sls`, `maxcompute`, or other products. The "workspace" in this skill is a CMS workspace, not a DataWorks/SLS/MaxCompute project.
12. **Set explicit timeouts.** Use `--read-timeout 30 --connect-timeout 10` for metadata operations (list/get/create/update/delete). For ExecuteQuery use `--read-timeout 120 --connect-timeout 10` as queries may take longer.

---

## Reference Links

| Reference | Description |
| --- | --- |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission requirements |
| [references/related-commands.md](references/related-commands.md) | Full CLI command reference |
| [references/verification-method.md](references/verification-method.md) | Success verification steps |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect pattern examples |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
