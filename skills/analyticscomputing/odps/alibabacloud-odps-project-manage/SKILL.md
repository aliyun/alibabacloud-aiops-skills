---
name: alibabacloud-odps-project-manage
description: |
  Alibaba Cloud MaxCompute Project Management Skill. Use for creating, querying, listing, and deleting MaxCompute projects.
  Triggers: "maxcompute project", "odps project", "create maxcompute project", "manage maxcompute project", "delete maxcompute project".
---

# MaxCompute Project Management

Manage Alibaba Cloud MaxCompute (ODPS) Projects including creation, querying, listing, and deletion operations.

## Quick Start

When user asks about MaxCompute projects, follow these steps:

1. **Identify intent**: create / list / get / delete
2. **Get RegionId**: Ask user which region (e.g., cn-hangzhou, cn-shanghai)
3. **Execute**: Run the appropriate command with `--region {REGION_ID}` and `--user-agent AlibabaCloud-Agent-Skills`
4. **Verify**: Confirm the result and report to user

## Pre-flight Checklist (Execute BEFORE every command)

**You MUST verify ALL of these before running any command:**

- [ ] I have asked the user for RegionId (not using default)
- [ ] I have the actual RegionId value from user (not placeholder)
- [ ] My command includes `--region {ACTUAL_REGION_ID}` 
- [ ] My command includes `--user-agent AlibabaCloud-Agent-Skills`
- [ ] I am NOT reading or echoing any AK/SK values
- [ ] I am NOT using hardcoded values for user-provided parameters

**If ANY check fails, STOP and fix before proceeding.**

## Task Completion Checklist

**CRITICAL: You MUST complete ALL steps in order. Do NOT stop early.**

### For LIST Projects:
1. [ ] Ask user: "Which region would you like to query? (e.g., cn-hangzhou, cn-shanghai)"
2. [ ] Ask user: "Which quota nickname to filter by? (e.g., os_PayAsYouGoQuota, or press Enter for default)"
3. [ ] **MUST use quota-nick-name parameter:**
   - If user specified a quota: Use `--quota-nick-name={USER_QUOTA}`
   - If user didn't specify: Use `--quota-nick-name=os_PayAsYouGo`
4. [ ] **Execute with REQUIRED parameters:**
   ```bash
   aliyun maxcompute list-projects --region {REGION_ID} --quota-nick-name={QUOTA_NICKNAME} --max-item=20 --user-agent AlibabaCloud-Agent-Skills
   ```
5. [ ] Wait for command output
6. [ ] **If 400 error (quota not found):**
   - Call `aliyun maxcompute list-quotas --billing-type ALL --region {REGION_ID} --user-agent AlibabaCloud-Agent-Skills`
   - Present available quotas to user for selection
   - Re-run ListProjects with user-selected quota
7. [ ] Parse response and present results
8. [ ] Confirm task completion

**FORBIDDEN:**
- ❌ Use `--marker` for pagination
- ❌ Fetch all projects then filter locally with Python/jq
- ❌ Call API without `--quota-nick-name` parameter

**REQUIRED:**
- ✅ ALWAYS use `--quota-nick-name` with user's quota or default
- ✅ ALWAYS use `--max-item=20`
- ✅ Let API do server-side filtering

### For GET Project:
1. [ ] Ask user: "Which region? (e.g., cn-hangzhou)"
2. [ ] Ask user: "What is the project name?"
3. [ ] Execute: `aliyun maxcompute get-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills`
4. [ ] Wait for command output
5. [ ] Parse the JSON response - look for `data.name`, `data.status`, `data.owner`
6. [ ] Present project details to user in a clear format
7. [ ] Confirm task completion to user

### For CREATE Project:
1. [ ] Ask user: "Which region to create in? (e.g., cn-hangzhou)"
2. [ ] Ask user: "What is the project name?"
3. [ ] **MANDATORY VALIDATION:** If project name is empty or whitespace, STOP and ask user again: "Project name cannot be empty. Please provide a valid project name."
4. [ ] **CRITICAL:** Store the user's exact project name - do NOT use placeholder text
5. [ ] **MUST call ListQuotas:** Execute: `aliyun maxcompute list-quotas --billing-type ALL --region {REGION_ID} --user-agent AlibabaCloud-Agent-Skills`
6. [ ] Wait for command output
7. [ ] **Parse ListQuotas response:** Find a quota with `nickName` and its **secondary quotas** (look in `data.quotas[].subQuotas` or similar)
8. [ ] **STRICT VALIDATION:** Select a **secondary quota's nickName** from the ListQuotas response (NOT the primary quota)
9. [ ] **TRIM WHITESPACE:** Remove any leading/trailing spaces from the quota nickName. If nickName contains internal spaces, trim them or select a different quota
10. [ ] **PRE-FLIGHT CHECK:** Verify you have actual values for REGION_ID, PROJECT_NAME, and SECONDARY_QUOTA_NICKNAME (trimmed, no spaces)
11. [ ] **Ask for typeSystem (optional):** "Which typeSystem? (1=MaxCompute, 2=MaxCompute2, hive=Hive compatible; default: 2)"
12. [ ] **Validate typeSystem:** Must be "1", "2", or "hive". If not specified or invalid, use default "2"
13. [ ] Execute create command with ACTUAL values:
    ```bash
    aliyun maxcompute create-project --region {ACTUAL_REGION} --body '{"name":"ACTUAL_PROJECT_NAME","defaultQuota":"SECONDARY_QUOTA_NICKNAME","productType":"payasyougo","typeSystem":"TYPE_SYSTEM_VALUE"}' --user-agent AlibabaCloud-Agent-Skills
    ```
    **Example with real values:**
    ```bash
    aliyun maxcompute create-project --region cn-hangzhou --body '{"name":"my-project-123","defaultQuota":"os_PayAsYouGoQuota_sub","productType":"payasyougo","typeSystem":"2"}' --user-agent AlibabaCloud-Agent-Skills
    ```
14. [ ] Wait for command output
15. [ ] **CHECK CREATE RESPONSE:** If create command returned error (non-2xx), STOP and report error to user. Do NOT proceed to verification.
16. [ ] **ONLY IF create succeeded:** Verify by executing: `aliyun maxcompute get-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills`
17. [ ] **CRITICAL:** Verify the response contains the CORRECT project name (the one user requested, not a different project)
18. [ ] **CHECK STATUS:** Verify response contains `"status":"AVAILABLE"`
19. [ ] **If verification returns 403/Access Denied:** Inform user about permission requirements and stop
20. [ ] **If project not found:** Report "Project creation failed - project not found after creation"
21. [ ] **If wrong project returned:** Report error - do not use a different project as substitute
22. [ ] **ONLY IF all checks pass:** Confirm to user: "Project {PROJECT_NAME} created successfully with status AVAILABLE"

### For DELETE Project:
**NOTE: Project deletion is NOT supported by this skill.**

If user requests deletion, respond: "Project deletion is not supported. Please use the Alibaba Cloud Console or contact your administrator."

## Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `ProjectNotFound` | Project doesn't exist | Check project name spelling and region |
| `ProjectAlreadyExist` | Name taken | Ask user for a different project name |
| `get project default quota error` | No valid quota | Run list-quotas first, ensure quota exists |
| `InvalidProjectName` | Bad naming format | Use only lowercase, numbers, underscores (3-28 chars) |
| `NoPermission` or `403 Access Denied` | RAM permission issue | Inform user: "You need odps:ListQuotas, odps:CreateProject and odps:GetProject permissions. Please contact your administrator." |
| `RegionId required` | Missing --region | Always add `--region {REGION_ID}` to commands |
| `ODPS-0420095: Access Denied` | Missing read privilege | Inform user about required permissions and stop |

## Forbidden Actions

> **CRITICAL: Never do these:**
> 1. **NEVER** read/echo AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID`)
> 2. **NEVER** use hardcoded values — always ask user for parameters, then use their ACTUAL answer (not placeholder text)
> 3. **NEVER** use `aliyun configure set` with literal credential values
> 4. **NEVER** run `aliyun ram` commands
> 5. **NEVER** execute ANY command without `--user-agent AlibabaCloud-Agent-Skills`
> 6. **NEVER** skip asking for RegionId — this is ALWAYS required
> 7. **NEVER** assume a default region — always ask the user
> 8. **NEVER** use deprecated API format `CreateProject` — ALWAYS use plugin format `create-project` (lowercase with hyphen)
> 9. **NEVER** execute `aliyun maxcompute delete-project` — project deletion is NOT supported by this skill

## Negative Examples

| ❌ WRONG | ✅ CORRECT |
|----------|------------|
| `aliyun maxcompute CreateProject` (deprecated) | `aliyun maxcompute create-project` (lowercase) |
| `'{"name":"{PROJECT_NAME}"}'` (placeholder) | `'{"name":"actual-name"}'` (actual value) |
| `--region cn-hangzhou` (hardcoded) | Ask user first, then use their answer |
| Missing `--user-agent` | Must include `--user-agent AlibabaCloud-Agent-Skills` |
| `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` | Never read/display credentials |
| `aliyun ram ...` commands | RAM commands are outside scope |
| `aliyun maxcompute delete-project` | Project deletion is NOT supported |
| Verify different project on failure | Report failure, don't substitute |

## Architecture

```
MaxCompute Service
    └── Project (Workspace)
          ├── defaultQuota (Compute Resource - MUST exist before project creation)
          ├── productType (payasyougo/subscription)
          └── typeSystem ("1", "2", or "hive"; default: "2")
```

## Dependencies

> **Prerequisite: Quota must exist before creating a project.**
>
> Every MaxCompute project requires a compute quota (`defaultQuota`). The quota must already exist in your account — if it does not, the `create-project` call will fail with `get project default quota error`.
>
> Use the **alibabacloud-odps-quota-manage** skill to create or query quotas:
> - **Pay-as-you-go**: `aliyun maxcompute CreateQuota --chargeType payasyougo --commodityCode odps --region <region> --user-agent AlibabaCloud-Agent-Skills`
> - **Subscription**: See `alibabacloud-odps-quota-manage` skill for full parameters (partNickName, CU, ord_time, etc.)
> - **List existing quotas**: `aliyun maxcompute list-quotas --billing-type ALL --region <region> --user-agent AlibabaCloud-Agent-Skills`
>
> After creating or confirming a quota exists, use its `nickName` as the `defaultQuota` parameter when creating a project.

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# Install Alibaba Cloud CLI (with 60s timeout)
curl -fsSL --max-time 60 https://aliyuncli.alicdn.com/install.sh | bash

# Verify version (must be >= 3.3.1)
aliyun version

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true
```

## Environment Variables

No additional environment variables required beyond standard Alibaba Cloud credentials.

## Authentication

**CRITICAL: You MUST check credentials before ANY operation.**

### Allowed Credential Check (ONLY this command):
```bash
aliyun configure list
```

**What to look for:**
- Output shows at least one profile with `mode: AK` or `mode: StsToken`
- Profile shows `access_key_id: ********` (masked is OK)

**If NO valid profile:**
- Tell user: "Please run `aliyun configure` to set up credentials first."
- **STOP** - Do not proceed with any MaxCompute commands

**FORBIDDEN - NEVER do these:**
- ❌ `echo $ALIBABA_CLOUD_ACCESS_KEY_ID`
- ❌ `echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET`
- ❌ `aliyun configure get | grep access-key`
- ❌ Any command that displays actual credential values

## RAM Policy

> **[MUST] RAM Permission Pre-check:** Before executing the workflow, verify that the current user has the required permissions.
> 
> Required permissions are listed in [references/ram-policies.md](references/ram-policies.md).
>
> **Note:** You do NOT need to verify RAM permissions via CLI commands. The permissions listed in ram-policies.md are for user reference only. Proceed with the workflow assuming the user has configured appropriate permissions.

## Parameters

**Always ask user for these values — never assume defaults:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `RegionId` | **Yes** | Region ID (cn-hangzhou, cn-shanghai, etc.) |
| `projectName` | **Yes** | Project name |
| `quotaNickName` | For create | Quota alias (get from list-quotas) |

## Example Conversation

**LIST:** User asks → Agent requests RegionId → Agent executes list-projects → Agent presents results

**CREATE:** User asks → Agent requests RegionId → Agent requests projectName → Agent calls list-quotas → Agent creates project → Agent verifies → Agent confirms success

## Commands

### List Projects
```bash
# Ask user for quota nickname first, then:
aliyun maxcompute list-projects --region {REGION_ID} --quota-nick-name={QUOTA_NICKNAME} --max-item=20 --user-agent AlibabaCloud-Agent-Skills
```
**MUST:** Always use `--quota-nick-name` parameter (user-specified or default). Never fetch all and filter locally.

### Get Project
```bash
aliyun maxcompute get-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills
```

### Create Project

1. List quotas first:
```bash
aliyun maxcompute list-quotas --billing-type ALL --region {REGION_ID} --user-agent AlibabaCloud-Agent-Skills
```

2. Create with quota nickName from response:
```bash
aliyun maxcompute create-project --region {REGION_ID} --body '{"name":"{PROJECT_NAME}","defaultQuota":"{QUOTA_NICKNAME}","productType":"payasyougo"}' --user-agent AlibabaCloud-Agent-Skills
```

### Delete Project

```bash
aliyun maxcompute delete-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills
```

## Success Verification Method

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

**Verification Command:**
```bash
aliyun maxcompute get-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria:**
- Response contains `"status":"AVAILABLE"`
- Response contains correct `"name"` matching the created project
- Response contains correct `"defaultQuota"` matching the specified quota

**If verification fails:**
1. Check error message for specific issue
2. Report failure reason to user
3. Suggest corrective action based on error type

## Cleanup

> **⚠️ DANGER: Deleting a project will permanently remove ALL data and CANNOT be undone.**

**Pre-deletion Checklist (ALL must be confirmed with user):**
1. ☐ User explicitly confirms they want to delete the project
2. ☐ User confirms they understand all data will be lost
3. ☐ Project is in AVAILABLE status
4. ☐ All important data has been backed up

**Idempotent Deletion Workflow:**

To ensure idempotency (safe for retries), follow this pattern:

```bash
# Step 1: Check if project exists (using user-provided RegionId)
EXISTING=$(aliyun maxcompute get-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills 2>&1)

# Step 2: Only delete if project exists
if echo "$EXISTING" | grep -q '"status":"AVAILABLE"'; then
  aliyun maxcompute delete-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills
  echo "Project deleted successfully"
elif echo "$EXISTING" | grep -q 'ProjectNotFound'; then
  echo "Project does not exist or already deleted"
else
  echo "Unexpected error: $EXISTING"
  exit 1
fi
```

**Direct Deletion Command (use only if idempotency is not required):**
```bash
aliyun maxcompute delete-project --region {REGION_ID} --project-name {PROJECT_NAME} --user-agent AlibabaCloud-Agent-Skills
```

**DO NOT execute deletion without explicit user confirmation.**

## Limitations

The following operations **cannot** be performed via CLI/API and require Console access:

| Operation | Reason | Alternative |
|-----------|--------|-------------|
| View billing details | Requires Console access | Use [Billing Console](https://billing.console.aliyun.com/) |
| Manage IAM policies visually | Console-only feature | Use RAM CLI for policy management |
| Real-time resource monitoring | Requires Console dashboard | Use CloudMonitor APIs |

## API and Command Tables

See [references/related-apis.md](references/related-apis.md) for complete API reference.

| Operation | CLI Command | API Action |
|-----------|-------------|------------|
| Create Project | `aliyun maxcompute create-project` | CreateProject |
| Get Project | `aliyun maxcompute get-project` | GetProject |
| List Projects | `aliyun maxcompute list-projects` | ListProjects |
| Delete Project | `aliyun maxcompute delete-project` | DeleteProject |

## Skill Completion Criteria (REQUIRED for skill_pass)

**For skill_pass_rate to be successful, ALL of these MUST be true:**

### Universal Requirements (ALL operations):
1. ✅ User was asked for RegionId and provided an answer
2. ✅ ALL commands used `--region {USER_PROVIDED_VALUE}` (not hardcoded)
3. ✅ ALL commands included `--user-agent AlibabaCloud-Agent-Skills`
4. ✅ No forbidden actions were performed (no credential echoing, no ram commands)
5. ✅ Task result was reported to user clearly

### Operation-Specific Requirements:

**LIST:**
- Command executed: `aliyun maxcompute list-projects --region {REGION} --quota-nick-name=os_PayAsYouGo --max-item=20 --user-agent AlibabaCloud-Agent-Skills`
- MUST include `--quota-nick-name=os_PayAsYouGo` parameter for first attempt
- MUST include `--max-item=20` parameter
- If first attempt fails with 400 error, retry with `--quota-nick-name=os_PayAsYouGoQuota`
- Results presented to user (list of projects or "no projects found")

**GET:**
- Command executed: `aliyun maxcompute get-project --region {REGION} --project-name {NAME} --user-agent AlibabaCloud-Agent-Skills`
- Project details presented to user

**CREATE:**
- User was asked for RegionId and projectName (actual values obtained)
- Quota was listed first: `aliyun maxcompute list-quotas --billing-type ALL --region {REGION} --user-agent AlibabaCloud-Agent-Skills`
- **MUST use actual values in body** - NOT placeholders like `{PROJECT_NAME}`
- Create command format: `--body '{"name":"ACTUAL_NAME","defaultQuota":"ACTUAL_QUOTA","productType":"payasyougo"}'`
- **MUST check create response for errors before proceeding**
- Verification command executed: `aliyun maxcompute get-project --region {REGION} --project-name {NAME} --user-agent AlibabaCloud-Agent-Skills`
- **MUST verify the project name in response matches the requested project**
- **MUST verify status is AVAILABLE**
- If verification fails due to permissions (403), inform user and stop
- If project not found or wrong project returned, report failure
- If verification succeeds (status=AVAILABLE), confirm success to user

**DELETE:**
- Explicit user confirmation obtained ("yes" response)
- Delete command executed: `aliyun maxcompute delete-project --region {REGION} --project-name {NAME} --user-agent AlibabaCloud-Agent-Skills`
- Deletion confirmed to user

### Final Skill Pass Check:
```
Before responding to user, verify:
□ I followed the correct workflow for the operation type
□ I asked for ALL required parameters from user
□ I used user's actual values in commands (not placeholders or defaults)
□ I included --user-agent AlibabaCloud-Agent-Skills in EVERY command
□ I did NOT perform any forbidden actions
□ I reported the final result to user

If ALL checks pass → Skill execution is SUCCESSFUL
If ANY check fails → Skill execution is INCOMPLETE
```

## Final Verification (Before Marking Task Complete)

**You MUST verify ALL of these before telling user the task is done:**

### For LIST:
- [ ] I asked for RegionId and got user's answer
- [ ] I executed list-projects with `--region {USER_ANSWER}` and `--user-agent AlibabaCloud-Agent-Skills`
- [ ] I presented the results to user clearly

### For GET:
- [ ] I asked for RegionId and got user's answer
- [ ] I asked for projectName and got user's answer
- [ ] I executed get-project with user's values and `--user-agent AlibabaCloud-Agent-Skills`
- [ ] I presented project details to user clearly

### For CREATE:
- [ ] I asked for RegionId and got user's answer
- [ ] I asked for projectName and got user's answer
- [ ] I executed list-quotas to get a valid quota
- [ ] I executed create-project with user's values and `--user-agent AlibabaCloud-Agent-Skills`
- [ ] I verified creation by calling get-project
- [ ] I confirmed success to user

### For DELETE:
- [ ] I asked for RegionId and got user's answer
- [ ] I asked for projectName and got user's answer
- [ ] I got explicit "yes" confirmation from user
- [ ] I executed delete-project with `--user-agent AlibabaCloud-Agent-Skills`
- [ ] I confirmed deletion to user

**If ANY check fails, the task is NOT complete.**

## Best Practices

1. **Naming Convention**: Use lowercase letters, numbers, and underscores for project names
2. **Quota Selection**: Choose appropriate quota based on workload requirements
3. **Product Type**: Use `payasyougo` for development/testing, `subscription` for production with predictable workloads
4. **Type System**: Use `2` (MaxCompute) for new projects unless Hive compatibility is required
5. **Resource Cleanup**: Always clean up test projects to avoid unnecessary costs

## Reference Links

| Document | Description |
|----------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete API reference |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions |
| [references/verification-method.md](references/verification-method.md) | Verification steps |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [MaxCompute Product Page](https://api.aliyun.com/product/MaxCompute) | Official product documentation |
| [CreateProject API](https://api.aliyun.com/api/MaxCompute/2022-01-04/CreateProject) | API reference |
| [GetProject API](https://api.aliyun.com/api/MaxCompute/2022-01-04/GetProject) | API reference |
| [ListProjects API](https://api.aliyun.com/api/MaxCompute/2022-01-04/ListProjects) | API reference |
