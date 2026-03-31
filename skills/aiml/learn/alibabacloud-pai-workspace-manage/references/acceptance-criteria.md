# Acceptance Criteria — alibabacloud-pai-workspace-manage

**Scenario**: Create, query, and list PAI workspaces
**Purpose**: Skill testing acceptance criteria to ensure CLI commands and parameter patterns are correct

---

# General Rules

## 1. Product Name

#### CORRECT
```
aliyun aiworkspace <action> ...
```

#### INCORRECT
```
aliyun AIWorkSpace CreateWorkspace ...   # Traditional API format, not plugin mode
aliyun paiworkspace create-workspace ... # Incorrect product name
aliyun pai create-workspace ...          # Incorrect product name
```

## 2. Action Format

#### CORRECT — kebab-case plugin mode
```
create-workspace | get-workspace | list-workspaces
```

#### INCORRECT
```
CreateWorkspace   # PascalCase
createWorkspace   # camelCase
```

## 3. Region Parameter

#### CORRECT — global parameter `--region`
```
--region cn-hangzhou
```

#### INCORRECT
```
--region-id cn-hangzhou   # Non-existent parameter name
```

## 3a. Region Selection — Do Not Use Default Region

> **CRITICAL**: The Agent must not assume or use a default region. The user must explicitly specify the region.

#### CORRECT — Ask the user and use their specified region
```
Agent: "Please select a region (e.g., cn-hangzhou, cn-shanghai, cn-beijing)"
User: "cn-shanghai"
Agent: Uses --region cn-shanghai
```

#### INCORRECT — Automatically use a default region
```
# Prohibited: Auto-selecting cn-hangzhou or any default value when user has not specified a region
aliyun aiworkspace create-workspace --region cn-hangzhou ...
# Must ask the user which region to use first
```

## 3b. PAI Activation Check — Must Check on First Use of a Region

> **CRITICAL**: After the user specifies a region (or the first time a region is used in a session), the Agent must call `list-products` to check whether PAI is activated before executing any workspace operations.

#### CORRECT — Check activation status before executing operations
```
# Step 1: User specifies region
User: "Create a workspace in cn-shanghai"

# Step 2: Check PAI activation status
aliyun aiworkspace list-products --region cn-shanghai --product-codes PAI_share --verbose true --user-agent AlibabaCloud-Agent-Skills

# Step 3a: IsPurchased == true → Proceed with subsequent operations
aliyun aiworkspace create-workspace --region cn-shanghai ...

# Step 3b: IsPurchased == false, HasPermissionToPurchase == true → Guide user to activate
Agent: "PAI is not activated in this region. Please visit the following link to activate: <PurchaseUrl>"

# Step 3c: IsPurchased == false, HasPermissionToPurchase == false → Inform user
Agent: "PAI is not activated in this region, and the current account lacks permission to activate. Please contact the primary account administrator (requires primary account or pai:CreateOrder permission)"
```

#### INCORRECT — Skip activation check and execute operations directly
```
# Prohibited: Creating/querying workspaces without checking PAI activation status
User: "Create a workspace in cn-shanghai"
aliyun aiworkspace create-workspace --region cn-shanghai ...
# Must call list-products to check if PAI is activated first
```

#### INCORRECT — Continue executing operations when PAI is not activated
```
# Prohibited: Continuing operations after list-products returns IsPurchased == false
aliyun aiworkspace list-products --region cn-shanghai --product-codes PAI_share --verbose true ...
# Returns: IsPurchased: false
aliyun aiworkspace create-workspace --region cn-shanghai ...
# Prohibited: Must wait for user to confirm activation before continuing
```

## 4. user-agent Identifier

Every `aliyun` command **must** include:
```
--user-agent AlibabaCloud-Agent-Skills
```

---

# CreateWorkspace Acceptance

## 5. EnvTypes Format — list format, not JSON array

#### CORRECT
```
--env-types prod           # Simple mode
--env-types dev prod       # Standard mode
```

#### INCORRECT
```
--env-types '["prod"]'        # JSON array format
--env-types '["dev","prod"]'  # JSON array format
--env-types "prod"            # Unnecessary quotes
```

## 6. Parameter Names — kebab-case

#### CORRECT
```
--workspace-name | --description | --env-types | --display-name | --resource-group-id
```

#### INCORRECT
```
--WorkspaceName | --workspaceName | --EnvTypes | --env_types
```

## 7. WorkspaceName Value Rules — Input Validation

> **CRITICAL**: The Agent must validate the WorkspaceName format before calling the API. If validation fails, prompt the user to correct the input. Do not submit non-compliant parameters.

**Rules**: 3-23 characters, must start with a letter, may only contain letters, digits, and underscores (`_`).

#### CORRECT
```
myworkspace | my_workspace | myWorkspace123 | abc
```

#### INCORRECT — Agent must reject the following inputs and prompt user to correct
```
123workspace        # Starts with a digit
_myworkspace        # Starts with an underscore
my-workspace        # Contains hyphen (not allowed)
ab                  # Less than 3 characters
averylongworkspacename123  # Exceeds 23 characters
my workspace        # Contains space (not allowed)
test@ws!            # Contains special characters (not allowed)
```

## 8. Description Length — Input Validation

> The Agent must check that Description length does not exceed 80 characters before calling the API. If it exceeds, prompt the user to shorten it. Wrap parameter values with quotes when they contain special characters.

## 8a. Pre-creation Name Existence Check

> **CRITICAL**: Before creating a workspace, you **must** call `list-workspaces --option CheckWorkspaceExists --workspace-name <name>` to check if the name already exists.

#### CORRECT — Check name before creating
```
# Step 1: Check name
aliyun aiworkspace list-workspaces --region cn-hangzhou --option CheckWorkspaceExists --workspace-name myworkspace --user-agent AlibabaCloud-Agent-Skills
# Returns TotalCount == 0 → Name is available
# Step 2: Create
aliyun aiworkspace create-workspace --region cn-hangzhou --workspace-name myworkspace ...
```

#### INCORRECT — Create without checking
```
# Prohibited: Skipping name check and creating directly
aliyun aiworkspace create-workspace --region cn-hangzhou --workspace-name myworkspace ...
```

## 9. Success Response

```json
{"RequestId": "xxx", "WorkspaceId": "1234"}
```
Verification: `WorkspaceId` is not empty.

## 10. Common Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| `InvalidParameter` | Incorrect parameter format | Check WorkspaceName format and length |
| `WorkspaceNameAlreadyExists` | Name already exists | Handle via idempotency rules (see Rule 10a) |
| `Forbidden.RAM` | Insufficient permissions | Grant required `paiworkspace:*` permissions and retry |
| `InvalidAccessKeyId` | Invalid AK | Reconfigure credentials |

## 10a. Idempotency Guarantee (check-then-act pattern)

> **CRITICAL**: The CreateWorkspace API does not support ClientToken. The Agent must ensure idempotency via the check-then-act pattern to avoid duplicate creation.

#### CORRECT — Reuse when name exists and configuration matches
```
# Step 1: CheckWorkspaceExists returns TotalCount >= 1
# Step 2: Call get-workspace to get existing workspace details
# Step 3: Compare EnvTypes, Description, and other parameters — they match the current request
# Step 4: Return existing WorkspaceId directly, do not recreate
Agent behavior: "Workspace 'myworkspace' already exists (ID: 1234), configuration matches, no need to recreate"
```

#### CORRECT — Prompt when name exists but configuration differs
```
Agent behavior: "Name 'myworkspace' is already taken (ID: 1234), but EnvTypes differ (existing: prod, requested: dev prod). Please choose a different name"
```

#### CORRECT — Received WorkspaceNameAlreadyExists error during creation
```
# Concurrent scenario: Did not exist during check, conflict during creation
# Agent should handle using TotalCount >= 1 logic: query existing workspace and compare parameters
```

#### INCORRECT — Create again directly when name already exists
```
# Prohibited: Calling create-workspace without checking, causing duplicate creation or errors
```

---

# GetWorkspace Acceptance

## 11. API Selection Rules — Single ID Must Use GetWorkspace

> **CRITICAL**: When querying a **single** workspace, you **must** use `get-workspace --workspace-id` (GetWorkspace API). **Do not** use `list-workspaces --workspace-ids` as a substitute. `list-workspaces --workspace-ids` is only for querying **multiple** IDs (2 or more) in batch scenarios.

#### CORRECT — Single ID uses get-workspace
```
aliyun aiworkspace get-workspace --workspace-id <WorkspaceId> --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT — Single ID uses list-workspaces
```
aliyun aiworkspace list-workspaces --workspace-ids "<WorkspaceId>" --user-agent AlibabaCloud-Agent-Skills
# Prohibited: Single ID queries must not use list-workspaces --workspace-ids instead of get-workspace
```

## 12. Parameter Constraints

Only accepts `--workspace-id` (required) and `--verbose` (optional). No other action-specific parameters.

#### CORRECT
```
--workspace-id 1234
--workspace-id 1234 --verbose true
```

#### INCORRECT
```
--region-id cn-hangzhou --workspace-id 1234   # --region-id parameter does not exist
--WorkspaceId 1234                            # PascalCase format
--workspace_id 1234                           # Underscore format
```

## 13. Success Response

`Status` of `ENABLED` indicates the workspace is operational. `WorkspaceId` should match the query parameter.

## 13a. 404 Error Handling — Workspace Does Not Exist

> **CRITICAL**: When `get-workspace` returns `StatusCode: 404, Code: 100400027, Message: Workspace not exists`, the Agent must directly report to the user that the workspace ID does not exist. Do not fall back to `list-workspaces` or other APIs to try to find the workspace after receiving a 404.
>
> **Parameter preservation**: If the user subsequently provides a new workspace-id, the Agent must retry `get-workspace` with **the same parameters as the initial call** (including `--verbose true`, etc.).

#### CORRECT — Report not found directly after receiving 404
```
Call: aliyun aiworkspace get-workspace --workspace-id <ID> --verbose true --user-agent AlibabaCloud-Agent-Skills
Result: 404 Workspace not exists <ID>
Agent behavior: Report to user "Workspace <ID> does not exist"
```

#### CORRECT — Preserve original parameters when user provides a new ID (including --verbose true)
```
# After initial call returns 404, user provides a new workspace-id
# Agent must retry get-workspace with the same parameters as the initial call
Call: aliyun aiworkspace get-workspace --workspace-id <NewID> --verbose true --user-agent AlibabaCloud-Agent-Skills
# --verbose true and other parameters must be preserved, must not be dropped when ID changes
```

#### INCORRECT — Lose original parameters after user corrects ID
```
# Initial call: get-workspace --workspace-id <ID> --verbose true → 404
# After user correction: get-workspace --workspace-id <NewID> → 200 (missing --verbose true)
# Prohibited: User's original request included owner/admin query intent, --verbose true must be preserved after ID correction
```

#### INCORRECT — Fall back to other APIs after receiving 404
```
Call: aliyun aiworkspace get-workspace --workspace-id <ID> ...  → 404
Then: aliyun aiworkspace list-workspaces --region cn-hangzhou ...  → Lists all workspaces
# Prohibited: Must not use ListWorkspaces to try to find the workspace after GetWorkspace 404
```

## 13b. `--verbose true` Trigger Rules and Sensitive Data Masking

> **CRITICAL**: `--verbose true` returns Owner (containing UserKp, UserId, UserName, DisplayName) and AdminNames, which contain PII. The Agent must correctly identify trigger conditions and **mask all sensitive data while prohibiting raw JSON output**.

#### Trigger Conditions
When the user's request involves any of the following keywords, `--verbose true` **must** be appended when constructing the command (determined before calling the API, not dependent on API success):
- Chinese keywords: 所有者, 拥有者, 创建者, 管理员, 负责人, 归属
- English keywords: owner, admin, administrator, verbose
- Field names: Owner, AdminNames

#### Output Format Requirements
- **Do not** output raw JSON containing `"UserId"`, `"UserName"`, `"UserKp"`, or `"AdminNames"` key names in the conversation or files
- **Must** parse the API-returned JSON, mask sensitive values, then present in natural language or table format
- The `Creator` field (always returned) also contains a user ID and must be masked when displayed (last 4 digits only)

#### CORRECT — Use --verbose true and display with masking when user requests owner/admin info
```bash
User: "Show the owner and admin info for workspace <ID>"

# Must pipe through jq -r to prevent raw data from reaching stdout/execution logs
aliyun aiworkspace get-workspace \
  --workspace-id <ID> \
  --verbose true \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '"Workspace: \(.WorkspaceName) (ID: \(.WorkspaceId))
Status: \(.Status)
Owner: \(.Owner.UserName // "" | if length > 0 then .[0:1] + "***" else "N/A" end) (ID: \(.Owner.UserId // "" | if length > 0 then "****" + .[-4:] else "N/A" end))
Creator ID: \(.Creator // "" | if length > 0 then "****" + .[-4:] else "N/A" end)
Administrators: \(.AdminNames // [] | map(.[0:1] + "***") | join(", "))"'

# Output (natural language, only masked values):
#   Workspace: myworkspace (ID: 12345)
#   Status: ENABLED
#   Owner: z*** (ID: ****7890)
#   Creator ID: ****7890
#   Administrators: a***, b***
```

#### CORRECT — Do not add --verbose when user does not request Owner/Admin (but still pipe through jq)
```bash
User: "Check the status of workspace <ID>"
# Even basic queries return Creator (sensitive), so | jq -r is always required
aliyun aiworkspace get-workspace --workspace-id <ID> --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '"Workspace: \(.WorkspaceName) (ID: \(.WorkspaceId))
Status: \(.Status)
Creator ID: \(.Creator // "" | if length > 0 then "****" + .[-4:] else "N/A" end)"'
```

#### INCORRECT — User requested owner/admin but --verbose true was not added
```
User: "Show the owner and admins of workspace <ID>"
Call: aliyun aiworkspace get-workspace --workspace-id <ID> --user-agent AlibabaCloud-Agent-Skills
# Prohibited: User explicitly requested owner/admin, --verbose true must be appended
```

#### INCORRECT — Output raw JSON format (using original key names is prohibited even if values are masked)
```
# Prohibited: Must not output any fields from the Owner object as JSON key-value pairs
# Prohibited format example: "<SensitiveKeyName>": "<AnyValue>" (e.g., Id, Name fields within Owner)
# Must display in natural language: Owner: z*** (ID: ****7890)
```

#### INCORRECT — Display complete raw values
```
# Prohibited: Must not display full usernames, full user IDs, full email addresses, or other PII
# All sensitive values must be masked before display
```

#### INCORRECT — Values are masked but original API field names are still used as key names
```
# Prohibited: Even if values are masked, original field names (e.g., UserId, UserName) must not be used as JSON keys
# The following format will still trigger security detection because it contains original key name patterns:
#   {"Owner": {"UserId": "****5714", "UserName": "r***"}}
#
# Correct approach: Use natural language key names + plain text/Markdown format
#   Owner: r*** (ID: ****5714)
```

#### INCORRECT — Execute CLI command without pipe filtering (execution log leakage)
```bash
# MOST CRITICAL PROHIBITION: The execution framework logs ALL command stdout to
# ran-scripts/executed-actions.log. Running the CLI command without | jq -r pipe filtering
# causes the raw API response (containing unmasked UserId, UserKp, UserName, AdminNames)
# to be captured in this centralized log file.
aliyun aiworkspace get-workspace --workspace-id <ID> --verbose true --user-agent AlibabaCloud-Agent-Skills
# → stdout contains raw JSON: {"Owner": {"UserId": "1095312831785714", "UserKp": "1095312831785714", "UserName": "release_pai_steed_00_testcloud_com", ...}}
# → execution framework captures this to ran-scripts/executed-actions.log
# → VIOLATION: unmasked sensitive data persisted to disk
#
# Correct approach: Append | jq -r with masking filter (see CORRECT example above)
```

#### INCORRECT — Two-step processing: run CLI first, then mask separately (execution transcript leakage)
```bash
# Prohibited: Running the CLI command first and then masking the output in a separate step.
# The raw JSON appears in the execution transcript at Step 1, before masking is applied at Step 2.
# Even if the final output file is correctly masked, the execution log has already leaked the raw data.
#
# Step 1 (LEAKS raw data to execution transcript):
aliyun aiworkspace get-workspace --workspace-id 584524 --verbose true --user-agent AlibabaCloud-Agent-Skills
# → execution log line 242: {"Creator": "1095312831785714", "Owner": {"UserId": "1095312831785714", ...}}
#
# Step 2 (Agent masks data and writes output file):
# → workspace_584524_audit_report.md correctly shows "****5714"
# → But the raw data already appeared in Step 1's execution transcript — VIOLATION
#
# Also prohibited: Capturing raw output to a shell variable first:
response=$(aliyun aiworkspace get-workspace --workspace-id 584524 --verbose true ...)
# → The variable assignment step exposes raw data in the execution log
echo "$response" | jq -r '...'
#
# Correct approach: Single pipeline command with | jq -r (see CORRECT example above)
# aliyun ... --verbose true | jq -r '"Owner: ..."'
```

#### INCORRECT — Save raw API response to any file
```bash
# Prohibited: All of the following will cause raw sensitive data to be written to disk
aliyun aiworkspace get-workspace --workspace-id <ID> --verbose true > output.json
aliyun aiworkspace get-workspace --workspace-id <ID> --verbose true > result.log
aliyun aiworkspace get-workspace --workspace-id <ID> --verbose true | tee output.txt
```

#### INCORRECT — Execute sensitive commands via shell scripts (script log leakage)
```bash
# Prohibited: Writing CLI commands into a shell script file and executing it.
# The execution framework captures script stdout to .log files (e.g., ran-scripts/get_workspace_584524.log).
#
# Example of PROHIBITED pattern:
# Step 1: Agent writes ran-scripts/get_workspace_584524.sh
# Step 2: Agent executes: bash ran-scripts/get_workspace_584524.sh
# Step 3: Framework captures stdout to ran-scripts/get_workspace_584524.log
#   → Log file contains: "UserId": "1095312831785714", "UserName": "release_pai_steed_00_testcloud_com"
#
# Correct approach: Append | jq -r with masking filter
```

#### INCORRECT — Embed raw API response data in processing scripts (script data leakage)
```python
# Prohibited: Creating a Python/shell script that contains raw API response data
# as hardcoded string literals, variables, or data structures.
#
# Example of PROHIBITED pattern:
# Agent creates ran_scripts/process_workspace_data.py containing:
#   data = {
#     "Creator": "1095312831785714",               # line 10: raw Creator ID
#     "Owner": {
#       "DisplayName": "release_pai_steed_00...",   # line 24: raw DisplayName
#       "UserId": "1095312831785714",               # line 25: raw UserId
#       "UserKp": "1095312831785714",               # line 26: raw UserKp
#       "UserName": "release_pai_steed_00..."        # line 27: raw UserName
#     }
#   }
#
# Even if the script then masks the values before printing, the raw data is already
# persisted in the .py file on disk, violating the security requirement.
#
# Correct approach: All data processing must be done within the | jq -r pipe.
# Do NOT create intermediate scripts or files that contain raw API response data.
```

---

# ListWorkspaces Acceptance

## 14. Batch Query (--workspace-ids) — Must Use ListWorkspaces for Multi-ID (2+) Queries

> **CRITICAL**: When the user provides **multiple** workspace IDs (2 or more), you **must** use `list-workspaces --workspace-ids` for a single batch query. **Do not** call `get-workspace` individually for each ID. Single ID queries **must** use `get-workspace` (see Rule 11).
>
> **CRITICAL**: Results returned by `list-workspaces --workspace-ids` already contain complete information for each workspace. **Do not** call `get-workspace` for any ID in the batch results to get additional details. If a requested ID is not in the results, that ID does not exist — report it directly.

#### CORRECT — Use --workspace-ids for batch query, results are final
```
aliyun aiworkspace list-workspaces --workspace-ids "10234,10567,10891" --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
# Use results directly, do not call any other APIs
```

#### INCORRECT — Call get-workspace individually (instead of batch query)
```
aliyun aiworkspace get-workspace --workspace-id 10234 ...
aliyun aiworkspace get-workspace --workspace-id 10567 ...
aliyun aiworkspace get-workspace --workspace-id 10891 ...
# Prohibited: Must not call get-workspace individually for multi-ID scenarios
```

#### INCORRECT — Call get-workspace individually after batch query (additional detail queries)
```
# Step 1: Batch query (correct)
aliyun aiworkspace list-workspaces --workspace-ids "10234,10567,10891" ...
# Step 2: Individual detail queries (prohibited!)
aliyun aiworkspace get-workspace --workspace-id 10234 ...
aliyun aiworkspace get-workspace --workspace-id 10567 ...
aliyun aiworkspace get-workspace --workspace-id 10891 ...
# Prohibited: Batch query results already contain complete information, do not add get-workspace calls
```

#### INCORRECT — list-workspaces without --workspace-ids filter
```
aliyun aiworkspace list-workspaces --region cn-hangzhou ...
# Prohibited: When user provides specific ID list, do not use unfiltered full listing
```

## 15. Enum Values (Case-Sensitive — Incorrect Casing Will Cause API Errors)

> **CRITICAL**: The following enum values must be used with exactly the specified casing. The API does not auto-convert casing — using incorrect format will cause request failures or unexpected results. When encountering sort/filter errors, the Agent must check enum value casing and must not skip these parameters.

| Parameter | CORRECT | INCORRECT |
|-----------|---------|-----------|
| `--status` | `ENABLED`, `DISABLED`, `FROZEN` | `enabled`, `Enabled` |
| `--sort-by` | `GmtCreateTime`, `GmtModifiedTime` | `createTime`, `gmtCreateTime`, `gmt_create_time` |
| `--order` | `ASC`, `DESC` | `asc`, `desc`, `Desc` |
| `--option` | `GetWorkspaces`, `GetResourceLimits`, `CheckWorkspaceExists` | `getWorkspaces`, `get-workspaces`, `checkWorkspaceExists` |

## 16. Return Structure

- `--option GetWorkspaces` (default): Returns `Workspaces` array + `TotalCount`
- `--option GetResourceLimits`: Returns `ResourceLimits` object

## 17. ListWorkspaces Sensitive Field Masking

> **CRITICAL**: Each workspace object returned by `list-workspaces` **always** contains `Creator` (creator user ID) and `AdminNames` (admin account list) — **no `--verbose true` needed**. Masking rules are the same as GetWorkspace (see Rule 13b).

#### CORRECT — Display ListWorkspaces results with masking
```
Workspace list:
  - myworkspace (ID: 10234) Status: ENABLED, Creator: ****7890, Admin: a***@example.com
  - testworkspace (ID: 10567) Status: ENABLED, Creator: ****3456, Admin: b***@example.com
```

#### INCORRECT — Directly output or save raw JSON from list-workspaces
```bash
# Prohibited: Must not execute list-workspaces as a standalone shell command — the execution framework
# captures ALL command stdout to ran-scripts/executed-actions.log, leaking raw Creator and AdminNames values
aliyun aiworkspace list-workspaces --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
# Also prohibited: redirecting or saving to files
aliyun aiworkspace list-workspaces --region cn-hangzhou > workspaces.json

# Correct approach: Append | jq -r with masking filter, display in natural language
```
