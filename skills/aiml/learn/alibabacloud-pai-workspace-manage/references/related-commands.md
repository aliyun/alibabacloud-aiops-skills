# Related Commands — PAI Workspace Management

All commands use plugin mode format and include `--user-agent AlibabaCloud-Agent-Skills`.

> **Important**: CLI uses `--region` (global parameter) to specify the region, not `--region-id`. `--region` **must be specified by the user** — do not use default values.
> `--env-types` uses list format (e.g., `--env-types prod` or `--env-types dev prod`), not JSON arrays.

### Global Optional Parameters — Timeout & Retry

All `aliyun` commands support the following global parameters:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `--connect-timeout` | int | Connection timeout (seconds) | `--connect-timeout 10` |
| `--read-timeout` | int | I/O read timeout (seconds) | `--read-timeout 30` |
| `--retry-count` | int | Number of retries on failure | `--retry-count 3` |

> When encountering `timeout` or `context deadline exceeded` errors, increase `--read-timeout` (e.g., 30-60 seconds). You can also persist the configuration via `aliyun configure set --connect-timeout 10 --read-timeout 30`.

---

## 1. Create Workspace (CreateWorkspace)

### Simple Mode (production environment only)

```bash
aliyun aiworkspace create-workspace \
  --region <RegionId> \
  --workspace-name <WorkspaceName> \
  --description "<Description>" \
  --env-types prod \
  --user-agent AlibabaCloud-Agent-Skills
```

### Standard Mode (development + production environments)

```bash
aliyun aiworkspace create-workspace \
  --region <RegionId> \
  --workspace-name <WorkspaceName> \
  --description "<Description>" \
  --env-types dev prod \
  --display-name "<DisplayName>" \
  --user-agent AlibabaCloud-Agent-Skills
```

### With Resource Group

```bash
aliyun aiworkspace create-workspace \
  --region <RegionId> \
  --workspace-name <WorkspaceName> \
  --description "<Description>" \
  --env-types prod \
  --resource-group-id <ResourceGroupId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### create-workspace Parameter Reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--region` | string | Yes | Region ID (global parameter), **must be specified by the user**, do not use default values |
| `--workspace-name` | string | Yes | 3-23 characters, starts with a letter, may contain letters/digits/underscores, unique within the region |
| `--description` | string | Yes | Max 80 characters |
| `--env-types` | list | Yes | List format: `prod` (simple mode), `dev prod` (standard mode) |
| `--display-name` | string | No | Display name, defaults to WorkspaceName |
| `--resource-group-id` | string | No | Resource group ID |

---

## 2. Get Workspace Details (GetWorkspace)

> **[MUST] Single ID queries must use this command**: When querying **single** workspace details, you must use `get-workspace` (calls GetWorkspace API). Do not use `list-workspaces --workspace-ids` as a substitute for single ID queries.
> `get-workspace` only accepts `--workspace-id` and `--verbose` parameters. The region is specified via the global `--region` parameter.
>
> **[MUST] `--verbose true` trigger rules**: When the user's request involves keywords such as 所有者/拥有者/创建者/管理员/负责人/归属/owner/admin/administrator/verbose, `--verbose true` **must** be appended.

### Basic Query (when user does not request Owner/Admin info)

> **[MUST]** Even basic queries return `Creator` (sensitive). This command must **always** include `| jq -r` pipe filtering. The Agent must NEVER run the CLI command without `| jq -r` — not even as an intermediate step.

```bash
aliyun aiworkspace get-workspace \
  --workspace-id <WorkspaceId> \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '"Workspace: \(.WorkspaceName) (ID: \(.WorkspaceId))
Status: \(.Status)
Environment: \(.EnvTypes | join(", "))
Created: \(.GmtCreateTime)
Creator ID: \(.Creator // "" | if length > 0 then "****" + .[-4:] else "N/A" end)"'
```

### With Owner and Admin Info (must use when user requests owner/admin info)

> **[MUST]** Since `--verbose true` returns sensitive data, this command must **NEVER** be executed without `| jq -r` pipe filtering. The execution framework logs ALL command stdout to `ran-scripts/executed-actions.log`. By piping through `jq -r`, the raw JSON flows through the pipe internally and only the masked, natural-language output reaches stdout.

```bash
aliyun aiworkspace get-workspace \
  --workspace-id <WorkspaceId> \
  --verbose true \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '"Workspace: \(.WorkspaceName) (ID: \(.WorkspaceId))
Status: \(.Status)
Environment: \(.EnvTypes | join(", "))
Created: \(.GmtCreateTime)
Owner: \(.Owner.UserName // "" | if length > 0 then .[0:1] + "***" else "N/A" end) (ID: \(.Owner.UserId // "" | if length > 0 then "****" + .[-4:] else "N/A" end))
Creator ID: \(.Creator // "" | if length > 0 then "****" + .[-4:] else "N/A" end)
Administrators: \(.AdminNames // [] | map(.[0:1] + "***") | join(", "))"'
```

**Output example** (only masked values, no raw JSON, no original key names):
```
Workspace: myworkspace (ID: 12345)
Status: ENABLED
Environment: dev, prod
Created: 2021-01-21T17:12:35.232Z
Owner: z*** (ID: ****5714)
Creator ID: ****5714
Administrators: a***, b***
```

### get-workspace Parameter Reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--workspace-id` | string | Yes | Workspace ID, e.g., `1234` |
| `--verbose` | bool | Conditionally required | **Must** pass `true` when user requests owner/admin info. Returns Owner, AdminNames, and other fields that must be masked when displayed |

### Key Return Fields

| Field | Description | Possible Values | Sensitivity |
|-------|-------------|-----------------|-------------|
| `Status` | Workspace status | `ENABLED` / `INITIALIZING` / `FAILURE` / `DISABLED` / `FROZEN` / `UPDATING` | Non-sensitive |
| `EnvTypes` | Environment list | `["prod"]` or `["dev","prod"]` | Non-sensitive |
| `IsDefault` | Whether it is the default workspace | `true` / `false` | Non-sensitive |
| `GmtCreateTime` | Creation time (ISO8601 UTC) | `2021-01-21T17:12:35.232Z` | Non-sensitive |
| `Creator` | Creator user ID (always returned) | `"28815334567890"` | **Sensitive — must be masked** |
| `Owner` | Owner (returned when `--verbose true`) | `{UserKp, UserId, UserName, DisplayName}` | **Sensitive — must be masked** |
| `AdminNames` | Admin list (returned when `--verbose true`) | `["user@example.com"]` | **Sensitive — must be masked** |
| `ResourceGroupId` | Resource group ID | `rg-xxxxxxxx` | Non-sensitive |

> **[MUST] Sensitive field masking rules — raw sensitive data must not appear in stdout, on disk, or in conversation**:
>
> The execution framework logs ALL command stdout to `ran-scripts/executed-actions.log`. Therefore, CLI commands returning sensitive data must **NEVER** be executed without `| jq -r` pipe filtering. Pipe through `jq -r` with a masking filter so the raw JSON flows through the pipe internally and only the masked, natural-language result reaches stdout and execution logs.
>
> | Field | Masking Method | Display Format Example |
> |-------|---------------|----------------------|
> | `Owner.UserId` / `Creator` | Show only last 4 digits | `Owner ID: ****7890` |
> | `Owner.UserKp` | **Omit entirely, do not display** | — (not output) |
> | `Owner.UserName` | Show only first character + `***` | `Username: z***` |
> | `Owner.DisplayName` | Show only first character + `***` | `Display Name: Z***` |
> | Accounts in `AdminNames` | First character + `***` + domain | `Admin: a***@example.com` |
>
> **Correct display example**:
> ```
> Owner: z*** (ID: ****7890)
> Admin: a***@example.com
> ```
>
> **Prohibited behaviors** (any of the following will trigger security detection):
> - **Executing ANY `get-workspace` or `list-workspaces` command without `| jq -r` pipe filtering** — including basic queries (which return `Creator`). The execution framework captures stdout to execution logs, leaking raw API responses. This is the most critical prohibition
> - **Two-step processing** — running the CLI command first to get raw output, then separately masking it in a second step. The raw JSON appears in the execution transcript before masking is applied. The `| jq -r` MUST be part of the same single pipeline command
> - **Capturing raw output to shell variables** — e.g., `response=$(aliyun ...)` then processing `$response`. The variable assignment step exposes raw data in the execution log
> - **Embedding raw API response data in any script or code file** — e.g., writing a Python/shell script that contains raw JSON values as string literals, variables, or data structures (such as `ran_scripts/process_workspace_data.py`). All data processing must be done entirely within the `| jq -r` pipe; do NOT create intermediate processing scripts that contain raw data
> - Saving raw API responses to any file (`.json`, `.log`, `.txt`, or any other format)
> - Redirecting command output to files (`> file`, `>> file`, `| tee file`)
> - Executing commands via shell scripts saved to disk (e.g., `ran-scripts/*.sh`)
> - Displaying raw JSON snippets containing sensitive key names in the conversation
> - Creating intermediate files, log files, or output files containing unmasked sensitive values
> - **Even when values are masked**, using original API field names (such as `UserId`, `UserName`) as JSON keys or structured key names in output is prohibited. Replace with natural language key names (`Owner ID`, `Username`, etc.)
>
> **Correct approach**: **EVERY** execution of `get-workspace` or `list-workspaces` must be a **single pipeline command** with `| jq -r` appended. The Agent must NEVER run the CLI command first and then process the output in a separate step. All data extraction, masking, and formatting must happen inside the `jq` filter of the same pipeline. If saving to a file, redirect the **jq output** (not the CLI output) using `> file.md` at the end of the pipeline. See the command templates above.

### Error Responses

| StatusCode | Code | Meaning | Handling |
|------------|------|---------|----------|
| 404 | 100400027 | Workspace does not exist | Report to user that the ID does not exist. Do not fall back to `list-workspaces` to search |

---

## 3. List Workspaces (ListWorkspaces)

> **[MUST] Pipe filtering required**: Since `list-workspaces` **always** returns `Creator` and `AdminNames` (sensitive PII), these commands must be piped through `| jq -r` with a masking filter — just like `get-workspace --verbose true`. See the masking rules in the "Sensitive Fields in Workspaces Array Elements" section below. The command templates in this section show the CLI arguments only; in practice, they must include `| jq -r` pipe filtering for masking.

### List All Workspaces

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Filter by Name

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --workspace-name <WorkspaceName> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Filter by Status + Sort by Creation Time Descending

> **Enum values are case-sensitive**: `--sort-by` values must be camelCase `GmtCreateTime` or `GmtModifiedTime`, `--order` values must be all uppercase `ASC` or `DESC`, `--status` values must be all uppercase like `ENABLED`. Incorrect examples: `desc`, `gmtCreateTime`, `enabled`.

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --status ENABLED \
  --sort-by GmtCreateTime \
  --order DESC \
  --user-agent AlibabaCloud-Agent-Skills
```

### Paginated Query

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --page-number 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Batch Query by ID List (for multiple IDs, 2 or more)

> **[MUST] Must use this method for multi-ID (2+) scenarios**: When querying **multiple** specific workspaces, use `--workspace-ids` for a single batch query. **Do not** call `get-workspace` individually for each ID. **Single ID** queries must use `get-workspace` (see above).
>
> **[MUST] Returned results are final**: The `Workspaces` array from batch queries already contains complete information for each workspace (Status, EnvTypes, GmtCreateTime, etc.). **Do not** call `get-workspace` for any ID in the batch results to get additional details. If a requested ID is not in the results, that ID does not exist.

```bash
aliyun aiworkspace list-workspaces \
  --workspace-ids "10234,10567,10891" \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Get Resource Limits

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --option GetResourceLimits \
  --user-agent AlibabaCloud-Agent-Skills
```

### Check Workspace Name Existence (must call before creating)

> **[MUST] Must use this command to check name uniqueness before creating a workspace.** `TotalCount == 0` means the name is available; `TotalCount >= 1` means the name already exists, prompt the user to choose a different name.

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --option CheckWorkspaceExists \
  --workspace-name <WorkspaceName> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response examples**:

Name available (`TotalCount == 0`):
```json
{"TotalCount": 0, "RequestId": "xxx", "Workspaces": []}
```

Name already exists (`TotalCount >= 1`):
```json
{"TotalCount": 1, "RequestId": "xxx", "Workspaces": [{"WorkspaceName": "test"}]}
```

### Return Only Workspace IDs

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --fields Id \
  --user-agent AlibabaCloud-Agent-Skills
```

### list-workspaces Parameter Reference

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `--region` | string | Yes | Region ID (global parameter), **must be specified by the user**, do not use default values | - |
| `--workspace-name` | string | No | Fuzzy match by name | - |
| `--status` | string | No | Filter by status (all uppercase: `ENABLED` / `DISABLED` / `FROZEN`, etc.) | - |
| `--page-number` | int | No | Page number, starting from 1 | `1` |
| `--page-size` | int | No | Items per page | `20` |
| `--sort-by` | string | No | Sort field (case-sensitive): `GmtCreateTime` / `GmtModifiedTime` | `GmtCreateTime` |
| `--order` | string | No | Sort direction (all uppercase): `ASC` / `DESC` | `ASC` |
| `--verbose` | bool | No | Return detailed information | `false` |
| `--workspace-ids` | string | No | Query by ID list, comma-separated | - |
| `--resource-group-id` | string | No | Filter by resource group | - |
| `--module-list` | string | No | Comma-separated module list | `PAI` |
| `--option` | string | No | Query option: `GetWorkspaces`/`GetResourceLimits` | `GetWorkspaces` |
| `--fields` | string | No | Return field list, currently only supports `Id` | - |
| `--user-id` | string | No | User ID | - |

### Sensitive Fields in Workspaces Array Elements

> **[MUST]** Each workspace object returned by `list-workspaces` **always** contains `Creator` (creator user ID) and `AdminNames` (admin account list) — **no `--verbose true` needed**. These fields contain PII and follow the same masking rules as GetWorkspace:
>
> | Field | Always Returned | Masking Method | Display Format Example |
> |-------|----------------|---------------|----------------------|
> | `Creator` | Yes | Show only last 4 digits | `Creator ID: ****7890` |
> | `AdminNames` | Yes | First character + `***` + domain | `Admin: a***@example.com` |
>
> Do not output raw `Creator` or `AdminNames` values from `list-workspaces` responses. Since the execution framework logs ALL command stdout to `ran-scripts/executed-actions.log`, `list-workspaces` must also be piped through `| jq -r` with a masking filter — the raw JSON flows through the pipe internally and only the masked result reaches stdout. Example:
>
> ```bash
> aliyun aiworkspace list-workspaces \
>   --region <RegionId> \
>   --user-agent AlibabaCloud-Agent-Skills \
>   | jq -r '.Workspaces[] | "- \(.WorkspaceName) (ID: \(.WorkspaceId)) Status: \(.Status), Creator: \(.Creator // "" | if length > 0 then "****" + .[-4:] else "N/A" end), Admin: \(.AdminNames // [] | map(.[0:1] + "***") | join(", "))"'
> ```

### Status Enum Values

| Value | Description |
|-------|-------------|
| `ENABLED` | Active |
| `INITIALIZING` | Initializing |
| `FAILURE` | Failed |
| `DISABLED` | Manually disabled |
| `FROZEN` | Frozen due to overdue payment |
| `UPDATING` | Updating |

### SortBy Enum Values

| Value | Description |
|-------|-------------|
| `GmtCreateTime` | Sort by creation time (default) |
| `GmtModifiedTime` | Sort by modification time |

### Option Enum Values

| Value | Description |
|-------|-------------|
| `GetWorkspaces` | Get workspace list (default), returns `Workspaces` |
| `GetResourceLimits` | Get resource limit information, returns `ResourceLimits` |
| `CheckWorkspaceExists` | Check if a workspace with the specified name already exists, use with `--workspace-name` |

---

## 4. Check Product Activation Status (ListProducts)

> **[MUST] Must check on first use of a region**: After the user specifies a region (or the first time a region is used in a session), this command must be called first to check whether PAI is activated before executing subsequent workspace operations.

### Check PAI Activation Status

```bash
aliyun aiworkspace list-products \
  --region <RegionId> \
  --product-codes PAI_share \
  --verbose true \
  --user-agent AlibabaCloud-Agent-Skills
```

### list-products Parameter Reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--region` | string | Yes | Region ID (global parameter) |
| `--product-codes` | string | Yes | Product codes, comma-separated. Use `PAI_share` for PAI |
| `--verbose` | bool | Yes | Pass `true` to return detailed fields such as `PurchaseUrl` and `HasPermissionToPurchase` |

### Key Return Fields (Products Array Elements)

| Field | Type | Description |
|-------|------|-------------|
| `ProductCode` | string | Product code, e.g., `PAI_share` |
| `IsPurchased` | boolean | Whether the product is purchased/activated. `true` = activated, `false` = not activated |
| `PurchaseUrl` | string | Purchase/activation link. When `IsPurchased == false`, guide the user to visit this link to complete activation |
| `HasPermissionToPurchase` | boolean | Whether the current user has permission to purchase. When `false`, requires the primary account or a RAM user with `pai:CreateOrder` permission |
| `ProductId` | string | Product ID |

### Response Example

```json
{
  "RequestId": "xxx",
  "Products": [
    {
      "ProductCode": "PAI_share",
      "IsPurchased": true,
      "PurchaseUrl": "https://common-buy.aliyun.com/...",
      "HasPermissionToPurchase": true,
      "ProductId": ""
    }
  ]
}
```

### Result Handling Logic

| `IsPurchased` | `HasPermissionToPurchase` | Agent Behavior |
|---------------|--------------------------|----------------|
| `true` | — | PAI is activated, proceed with subsequent workflows |
| `false` | `true` | Show `PurchaseUrl` to user, prompt to complete activation in the console |
| `false` | `false` | Inform user they lack permission. Contact primary account administrator (requires primary account or `pai:CreateOrder` permission) |

> **[MUST]** When PAI is not activated (`IsPurchased == false`), do not proceed with creating/querying workspaces. Wait for the user to confirm activation before continuing.

---

## Common Region IDs

| Region | RegionId |
|--------|----------|
| China East 1 (Hangzhou) | cn-hangzhou |
| China East 2 (Shanghai) | cn-shanghai |
| China North 2 (Beijing) | cn-beijing |
| China South 1 (Shenzhen) | cn-shenzhen |
| Singapore | ap-southeast-1 |
