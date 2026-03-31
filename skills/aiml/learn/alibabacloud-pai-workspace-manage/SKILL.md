---
name: alibabacloud-pai-workspace-manage
description: |
  Alibaba Cloud PAI Workspace Management Skill. Create, query, and list workspaces on the Platform for AI (PAI).
  Triggers: "create PAI workspace", "query PAI workspace", "list workspaces", "PAI workspace", "create workspace", "get workspace", "list workspaces", "AIWorkSpace CreateWorkspace", "AIWorkSpace GetWorkspace", "AIWorkSpace ListWorkspaces"
---

# PAI Workspace Management

Create, query, and list workspaces on Alibaba Cloud Platform for AI (PAI). Workspaces serve as isolated management units for AI model training, data processing, and related tasks.

**Architecture**: PAI AIWorkSpace (Workspace)

**Workspace Modes**:
- **Simple Mode**: Production environment only (`prod`)
- **Standard Mode**: Development (`dev`) + Production (`prod`) environments

---

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
aliyun version
aliyun configure set --auto-plugin-install true
```

---

## Credential Verification

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> **Sensitive Data Masking:**
> - The following fields in API responses contain personally identifiable information and **MUST be masked** before displaying to the user:
>   - `Owner.UserId` / `Creator` — Show only last 4 digits, e.g., `****1234`
>   - `Owner.UserKp` — Never display, omit entirely
>   - `Owner.UserName` / `Owner.DisplayName` — Show only first character + `***`, e.g., `z***`
>   - Accounts in `AdminNames` — Mask as `u***@example.com` format
> - **[MUST] Raw sensitive data MUST NOT appear in stdout, execution logs, on disk, or in the conversation**: The execution framework logs ALL command stdout to execution logs/transcripts (e.g., `ran-scripts/executed-actions.log`). Therefore, **EVERY** execution of `get-workspace` or `list-workspaces` (including basic queries without `--verbose`) must include `| jq -r` pipe filtering — because `Creator` is **always** returned and is sensitive. There must be **NO execution step** where the raw API JSON appears in command output, even as an intermediate step. The `| jq -r` pipe must be part of a **single pipeline command**:
>
>   **Basic query** (without `--verbose`):
>   ```bash
>   aliyun aiworkspace get-workspace --workspace-id <ID> --region <RegionId> \
>     --user-agent AlibabaCloud-Agent-Skills \
>     | jq -r '"Workspace: \(.WorkspaceName) (ID: \(.WorkspaceId))
>   Status: \(.Status)
>   Environment: \(.EnvTypes | join(", "))
>   Created: \(.GmtCreateTime)
>   Creator ID: \(.Creator // "" | if length > 0 then "****" + .[-4:] else "N/A" end)"'
>   ```
>
>   **Verbose query** (with `--verbose true`):
>   ```bash
>   aliyun aiworkspace get-workspace --workspace-id <ID> --verbose true --region <RegionId> \
>     --user-agent AlibabaCloud-Agent-Skills \
>     | jq -r '"Workspace: \(.WorkspaceName) (ID: \(.WorkspaceId))
>   Status: \(.Status)
>   Owner: \(.Owner.UserName // "" | if length > 0 then .[0:1] + "***" else "N/A" end) (ID: \(.Owner.UserId // "" | if length > 0 then "****" + .[-4:] else "N/A" end))
>   Creator ID: \(.Creator // "" | if length > 0 then "****" + .[-4:] else "N/A" end)
>   Administrators: \(.AdminNames // [] | map(.[0:1] + "***") | join(", "))"'
>   ```
>
>   The raw API response flows through the pipe internally and never reaches shell stdout. Only `jq`'s output (with masked values and natural language keys) is captured by the execution framework. The following are **all prohibited**:
>   - Running the CLI command **without** `| jq` pipe filtering — even for basic queries (the `Creator` field is always returned and sensitive)
>   - **Two-step processing** — running the CLI command first to get raw output, then separately masking it. The raw JSON would appear in the execution transcript before masking is applied. The `| jq -r` MUST be part of the same single pipeline command
>   - **Capturing raw output to shell variables** — e.g., `response=$(aliyun ...)` then `echo "$response" | jq ...`. The variable assignment captures raw data into the execution log
>   - Output redirection (`> file.json`, `>> file.log`, `| tee file`)
>   - Executing commands via shell scripts saved to disk (e.g., `ran-scripts/*.sh`)
>   - **Embedding raw API response data in any script or code file** — e.g., writing a Python/shell script that contains raw JSON values as string literals, variables, or data structures (such as `ran_scripts/process_workspace_data.py`). All data processing must be done entirely within the `| jq -r` pipe; do NOT create intermediate processing scripts that contain raw data
>   - Displaying raw JSON snippets in the conversation
> - **[MUST] Original API field names MUST NOT be used as output keys**: Even when values are masked, using original API field names (such as `UserId`, `UserName`, `UserKp`, `AdminNames`) as JSON keys or structured output key names in any output (conversation or files) is **prohibited**. Use natural language key names instead:
>   - `UserId` / `Creator` → `Owner ID` or `Creator ID`
>   - `UserName` → `Username`
>   - `DisplayName` → `Display Name`
>   - `AdminNames` → `Administrators`
>
>   **Correct approach**: **EVERY** execution of `get-workspace` or `list-workspaces` must be a **single pipeline command** with `| jq -r` appended. The Agent must NEVER run the CLI command first and then process the output in a separate step — the raw JSON would appear in the execution transcript before masking is applied. All data extraction, masking, and formatting must happen inside the `jq` filter. If saving to a file, redirect the **jq output** (not the CLI output) using `> file.md` at the end of the pipeline. This rule applies to ALL queries — basic, verbose, and list.
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

## RAM Permissions

See `references/ram-policies.md` for required permissions (including Policy JSON and instructions).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, WorkspaceName, Description, EnvTypes, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Example |
|-----------|-------------------|-------------|---------|
| `--region` | Required | Region ID (global parameter), **must be specified by the user**, do not use default values | `cn-hangzhou` |
| `--workspace-name` | Required | Workspace name: 3-23 characters, starts with a letter, may contain letters/digits/underscores, unique within the region | `myworkspace` |
| `--description` | Required | Workspace description, max 80 characters | `My AI workspace` |
| `--env-types` | Required | Environment types (list format): `prod` (simple mode) or `dev prod` (standard mode) | `prod` |
| `--display-name` | Optional | Display name, defaults to WorkspaceName | `My Workspace` |
| `--resource-group-id` | Optional | Resource group ID, uses default resource group if not specified | `rg-xxxxxxxx` |

> **Note**: Once `--resource-group-id` is set, it **cannot be modified via CLI/code**. To change it, use the console or recreate the workspace.

---

## Timeout Configuration

API calls support timeout configuration (in seconds):

**Option 1: Command-line parameters** (applies to the current command only):
- `--connect-timeout <seconds>` — Connection timeout
- `--read-timeout <seconds>` — I/O read timeout

**Option 2: Persistent configuration** (applies globally, written to current profile):
```bash
aliyun configure set --connect-timeout 10 --read-timeout 30
```

> Command-line parameters take precedence over persistent configuration. If not set, the CLI uses built-in defaults. When encountering `timeout` or `context deadline exceeded` errors, increase `--read-timeout` (e.g., 30-60 seconds).

---

## Core Workflow

> See `references/related-commands.md` for all CLI command templates and parameter details.

### Prerequisite: Region Selection and PAI Activation Check

> **[MUST] Do not use a default region**: The Agent must not assume or use a default region. It must explicitly ask the user which region to use.
>
> **[MUST] Check PAI activation on first use of a region**: After the user specifies a region (or the first time a region is used in a session), the Agent must call `list-products` to check whether PAI is activated in that region before executing any subsequent workspace operations.

#### Step 1: Confirm Region

Ask the user which region to use. If the user has not specified one, provide the list of common regions for selection (see the Common Region IDs table in `references/related-commands.md`). **Do not** automatically select a default region.

#### Step 2: Check PAI Activation Status

Use `aliyun aiworkspace list-products` to check whether PAI and its dependent products are activated in the user-specified region:

```bash
aliyun aiworkspace list-products \
  --region <UserSpecifiedRegionId> \
  --product-codes PAI_share \
  --verbose true \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Step 3: Handle Check Results

Inspect the returned `Products` array for the matching product entry:

> **Decision logic**:
>
> 1. **`IsPurchased == true`** → PAI is activated, proceed with subsequent workflows
> 2. **`IsPurchased == false`** → PAI is not activated, guide the user to activate:
>    - Check the `HasPermissionToPurchase` field:
>      - `true` → User has permission. Show the `PurchaseUrl` link and prompt the user to complete activation in the console before continuing
>      - `false` → User lacks permission (requires the primary account or a RAM user with `pai:CreateOrder` permission). Inform the user to contact the primary account administrator
>    - **Do not** proceed with creating/querying workspaces when PAI is not activated

### Workflow 1: Create Workspace (CreateWorkspace)

Use `aliyun aiworkspace create-workspace` to create a workspace. Required parameters: `--region`, `--workspace-name`, `--description`, `--env-types`. Simple mode uses `--env-types prod`, standard mode uses `--env-types dev prod`. Optionally add `--display-name` and `--resource-group-id`.

#### Step 1: Input Parameter Validation

> **[MUST] Parameter format validation**: Before calling the API, the Agent must validate user-provided parameters as follows. If validation fails, prompt the user to correct the input. **Do not** submit non-compliant parameters:
>
> | Parameter | Validation Rules | Example |
> |-----------|-----------------|---------|
> | `--workspace-name` | 3-23 characters, must start with a **letter**, may only contain letters, digits, and underscores (`_`). Hyphens (`-`), spaces, Chinese characters, and other special characters are not allowed | `my_workspace_01` |
> | `--description` | Max 80 characters, wrap with quotes if containing special characters | `"My AI workspace"` |
> | `--env-types` | Must be `prod` or `dev prod`, list format | `prod` |
> | `--display-name` | Optional, no strict format restrictions | `My Workspace` |

#### Step 2: Name Existence Check (check-then-act idempotency pattern)

> **[MUST] Idempotency guarantee**: The CreateWorkspace API does not support ClientToken, so idempotency is ensured via a check-then-act pattern. Before creating, you **must** call `list-workspaces --option CheckWorkspaceExists --workspace-name <name>` to check if the name already exists.
>
> Decision logic:
> - `TotalCount == 0` → Name is available, proceed to Step 3 to create
> - `TotalCount >= 1` → Name already exists, perform the following:
>   1. Extract the existing `WorkspaceId` from the returned `Workspaces[0]`
>   2. Call `get-workspace --workspace-id <id>` to get full details
>   3. Compare the existing workspace's key parameters (`EnvTypes`, `Description`, etc.) with the current request parameters
>   4. **Match** → Treat as already created, return the existing `WorkspaceId` directly, **do not recreate**
>   5. **Mismatch** → Inform the user that the name is already taken with a different configuration, ask the user to choose a different name

#### Step 3: Execute Creation

After parameter validation passes and the name does not exist, execute the `create-workspace` command. On success, a `WorkspaceId` is returned. If the creation returns a `WorkspaceNameAlreadyExists` error (concurrent scenario), handle it using the `TotalCount >= 1` logic from Step 2.

### Workflow 2: Get Workspace Details (GetWorkspace)

> **[MUST] Single workspace queries must use `get-workspace`**: When querying the details of **one** specific workspace, you **must** use `aliyun aiworkspace get-workspace --workspace-id <id>`. **Do not** use `list-workspaces --workspace-ids` as a substitute. `get-workspace` calls the GetWorkspace API and returns the complete details of a single workspace.

Only accepts `--workspace-id` (required) and `--verbose` (optional). The region is specified via the global `--region` parameter. A `Status` of `ENABLED` indicates the workspace is ready.

> **[MUST] `--verbose true` trigger rules**: `--verbose true` returns Owner (UserKp, UserId, UserName, DisplayName) and AdminNames (admin account list). The Agent must follow these rules:
>
> 1. **Trigger conditions** — When the user's request involves any of the following keywords, `--verbose true` **must** be appended when constructing the command (determined before calling the API, not dependent on API success):
>    - Chinese keywords: 所有者, 拥有者, 创建者, 管理员, 负责人, 归属
>    - English keywords: owner, admin, administrator, verbose
>    - Field names: Owner, AdminNames
> 2. **When not triggered** — When the user only queries basic info (status, environment types, etc.), do not append `--verbose`
> 3. **Masking rules** — UserId/Creator: last 4 digits only (`****1234`); UserKp: omit entirely; UserName/DisplayName: first character only (`z***`); AdminNames entries: `u***@example.com`
> 4. **No raw sensitive data in stdout, execution logs, on disk, or in output** — **EVERY** execution of `get-workspace` (with or without `--verbose`) or `list-workspaces` must be a **single pipeline command** with `| jq -r` appended. The Agent must NEVER run the CLI command first and then mask the output separately — the raw JSON would appear in the execution transcript. No two-step processing, no variable capture (`response=$(aliyun ...)`), no intermediate scripts. All masking must happen inside the `jq` filter of the same pipeline. See the Sensitive Data Masking section and `references/related-commands.md` for templates

> **[MUST] 404 error handling**: When `get-workspace` returns `StatusCode: 404, Code: 100400027, Message: Workspace not exists`, the workspace ID does not exist. The Agent must **directly report to the user that the workspace does not exist**, including the original workspace-id specified by the user. **Do not** fall back to `list-workspaces` or other APIs to try to "find" the workspace after receiving a 404. **Do not** silently ignore the error. If the user subsequently provides a new workspace-id, the Agent must retry `get-workspace` with **the same parameters as the initial call** (including `--verbose true`, etc.).

### Workflow 3: List Workspaces (ListWorkspaces)

Use `aliyun aiworkspace list-workspaces` to list workspaces. Supports the following filter and sort parameters:

- `--workspace-name <name>` — Fuzzy match by name
- `--workspace-ids <id1,id2,...>` — **Batch query by ID list**, comma-separated (e.g., `--workspace-ids "123,456,789"`)
- `--status <STATUS>` — Filter by status, enum values (all uppercase): `ENABLED` | `INITIALIZING` | `FAILURE` | `DISABLED` | `FROZEN` | `UPDATING`
- `--sort-by <Field>` — Sort field (case-sensitive): `GmtCreateTime` (default) | `GmtModifiedTime`
- `--order <ORDER>` — Sort direction (all uppercase): `ASC` (default) | `DESC`
- `--page-number <n>` / `--page-size <n>` — Pagination parameters
- `--option GetResourceLimits` — Get resource limit information instead of workspace list
- `--option CheckWorkspaceExists` — Check if a workspace with the specified name already exists (pre-creation check, use with `--workspace-name`)

> **[MUST] API selection rules**: Use `get-workspace --workspace-id` (GetWorkspace API) for querying a **single** ID; use `list-workspaces --workspace-ids "id1,id2,..."` for querying **multiple** IDs (2 or more) in a single batch query (ListWorkspaces API). Do not call `get-workspace` individually for each ID.
>
> **[MUST] Batch query results are final**: The `Workspaces` array returned by `list-workspaces --workspace-ids` already contains complete information for each workspace (Status, EnvTypes, GmtCreateTime, etc.). **Do not** call `get-workspace` for any ID in the batch results to get additional details. If some IDs are not in the response, those IDs do not exist — report this to the user directly.

> **[MUST] Enum values are case-sensitive**: `--sort-by` must be `GmtCreateTime` or `GmtModifiedTime` (camelCase), `--order` must be `ASC` or `DESC` (all uppercase), `--status` must be all uppercase like `ENABLED`. Using incorrect casing (e.g., `desc`, `gmtCreateTime`, `enabled`) will cause API errors or unexpected results.

> **[MUST] ListWorkspaces sensitive field masking**: Each workspace object returned by `list-workspaces` **always** contains `Creator` (creator user ID) and `AdminNames` (admin account list) — **no `--verbose true` needed**. The Agent must mask these fields when displaying (`Creator`: last 4 digits only; `AdminNames`: first character + `***`). Do not output JSON containing the raw values, and do not save raw responses to files via redirection (`> file`) or scripts.

---

## Success Verification

| Verification Target | Method | Success Criteria |
|---------------------|--------|------------------|
| WorkspaceId returned | Parse create command response | `WorkspaceId` is not empty |
| Workspace status is normal | `get-workspace` command | `Status == "ENABLED"` |
| Visible in console | Log in to [PAI Console](https://pai.console.aliyun.com/) and verify manually | New workspace appears in the list |

> See `references/verification-method.md` for detailed verification methods

---

## Cleanup (Delete Workspace)

> **Warning**: Deleting a workspace is an **irreversible operation** that removes all resources within it. Proceed with caution.
>
> **Note**: Workspace deletion **cannot be performed directly via CLI** (the `aiworkspace` plugin does not currently support `delete-workspace`). Use the following methods:
> 1. **Console deletion**: Log in to [PAI Console](https://pai.console.aliyun.com/) -> Workspace List -> Select workspace -> Delete
> 2. **API call**: Use the `DELETE /api/v1/workspaces/{WorkspaceId}` endpoint (via SDK or direct HTTP call)

---

## Best Practices

1. **Naming conventions**: Use project names or team identifier prefixes for WorkspaceName, e.g., `nlp_prod`, `cv_dev` (note: hyphens are not supported, use underscores)
2. **Environment selection**: Use standard mode (`dev` + `prod`) for production projects to separate development and production resources
3. **Description**: Description should indicate the purpose, team, or project for easier management
4. **Region selection**: Choose the region closest to your data storage to minimize data transfer latency
5. **Resource group management**: Use different resource groups for multi-project scenarios to facilitate cost allocation and permission management
6. **DisplayName**: Use business-friendly names as the display name while using English identifiers for WorkspaceName

---

## Reference Documentation

| Document | Description |
|----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies, Policy JSON, and instructions |
| [references/related-commands.md](references/related-commands.md) | Complete CLI command templates, parameter tables, enum values, and return fields |
| [references/verification-method.md](references/verification-method.md) | Verification steps and scripts |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | CLI command acceptance criteria (correct/incorrect patterns) |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration |
| [ListWorkspaces API Doc](https://help.aliyun.com/zh/pai/developer-reference/api-aiworkspace-2021-02-04-listworkspaces) | ListWorkspaces API reference |
| [CreateWorkspace API Doc](https://help.aliyun.com/zh/pai/developer-reference/api-aiworkspace-2021-02-04-createworkspace) | CreateWorkspace API reference |
| [GetWorkspace API Doc](https://help.aliyun.com/zh/pai/developer-reference/api-aiworkspace-2021-02-04-getworkspace) | GetWorkspace API reference |
| [ListProducts API Doc](https://help.aliyun.com/zh/pai/developer-reference/api-aiworkspace-2021-02-04-listproducts) | ListProducts API reference (product activation status check) |
