# Acceptance Criteria: DataWorks Workspace Management

**Scenario**: DataWorks Workspace Lifecycle Management
**Purpose**: Skill testing acceptance criteria and correct/incorrect patterns

## ⛔ PROHIBITED OPERATIONS

> The following operations are **PROHIBITED** via this Skill:
> - `UpdateProject` - Update workspace
> - `DeleteProject` - Delete workspace
> - `DeleteProjectMember` - Remove workspace member
> - `RevokeMemberProjectRoles` - Revoke member roles
>
> Users must perform these operations manually via the DataWorks Console.

---

## Correct CLI Command Patterns

### 1. Correct Product Pattern

#### ✅ CORRECT: Use correct product name and PascalCase format
```bash
aliyun dataworks-public CreateProject
aliyun dataworks-public ListProjects
aliyun dataworks-public CreateProjectMember
```

#### ❌ INCORRECT: Wrong product name or format
```bash
aliyun dataworks create-project        # Wrong - product name should be dataworks-public
aliyun data-works-public create-project  # Wrong - product name misspelled
aliyun dw create-project               # Wrong - non-existent product abbreviation
aliyun dataworks-public create-project   # Wrong - CLI 3.3.1+ should use PascalCase
```

---

### 2. Correct Command Pattern

#### ✅ CORRECT: Use PascalCase command and parameter format (CLI 3.3.1+)
```bash
aliyun dataworks-public CreateProject
aliyun dataworks-public GetProject
aliyun dataworks-public ListProjects
aliyun dataworks-public CreateProjectMember
aliyun dataworks-public GrantMemberProjectRoles
aliyun dataworks-public GetProjectMember
aliyun dataworks-public ListProjectMembers
aliyun dataworks-public GetProjectRole
aliyun dataworks-public ListProjectRoles
```

#### ❌ INCORRECT: Wrong command format
```bash
aliyun dataworks-public create-project         # Wrong - CLI 3.3.1+ should use PascalCase
aliyun dataworks-public createProject          # Wrong - incorrect camelCase
aliyun dataworks-public create_project         # Wrong - incorrect underscore
aliyun dataworks-public projectCreate          # Wrong - incorrect command order
```

---

### 3. Correct Role Code Pattern

#### ✅ CORRECT: Use correct role codes and JSON array format
```bash
--RoleCodes '["role_project_owner"]'
--RoleCodes '["role_project_admin"]'
--RoleCodes '["role_project_dev"]'
--RoleCodes '["role_project_pe"]'
--RoleCodes '["role_project_deploy"]'
--RoleCodes '["role_project_guest"]'
--RoleCodes '["role_project_security"]'
--RoleCodes '["role_project_data_analyst"]'
--RoleCodes '["role_project_model_designer"]'
--RoleCodes '["role_project_data_governance_admin"]'
# Multi-role example
--RoleCodes '["role_project_dev", "role_project_pe"]'
```

#### ❌ INCORRECT: Wrong role code format
```bash
--RoleCodes ROLE_PROJECT_ADMIN           # Wrong - should be lowercase and JSON array
--RoleCodes ProjectAdmin                 # Wrong - incorrect format
--RoleCodes admin                        # Wrong - missing prefix
--RoleCodes role-project-admin           # Wrong - should use underscore not hyphen
--RoleCodes role_project_dev,role_project_pe  # Wrong - should use JSON array format
```

---

## Test Scenarios

### Scenario 1: Create Workspace

**Input**:
- Workspace name: `test_workspace_001`
- Display name: `Test Workspace`
- Enable PAI task: `true`

**Expected Command**:
```bash
aliyun dataworks-public CreateProject \
  --Name test_workspace_001 \
  --DisplayName "Test Workspace" \
  --PaiTaskEnabled true \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Expected Result**:
- Returns HTTP 200
- Response contains workspace ID

**Access URL After Successful Creation**:
```
https://dataworks.data.aliyun.com/{regionId}/sc?defaultProjectId={projectId}
```

Example (Hangzhou region):
```
https://dataworks.data.aliyun.com/cn-hangzhou/sc?defaultProjectId=12345
```

**Error Handling**:
- If error code `9990010001` is returned, it means DataWorks service is not enabled. Visit https://dataworks.console.aliyun.com/ to complete activation and retry

---

### Scenario 2: Add Member and Grant Roles

**Input**:
- Workspace ID: `12345`
- User ID: `234567890123456789`
- Roles: Developer, Operator

**UserId Format Description**:

| Account Type | UserId Format | Example |
|--------------|---------------|---------|
| Alibaba Cloud Account (Main) | Use UID directly | `123456789012345678` |
| RAM Sub-account | Use UID directly | `234567890123456789` |
| RAM Role | Add `ROLE_` prefix | `ROLE_345678901234567890` |

**Expected Command**:
```bash
aliyun dataworks-public CreateProjectMember \
  --ProjectId 12345 \
  --UserId 234567890123456789 \
  --RoleCodes '["role_project_dev", "role_project_pe"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Special Process for Adding RAM Role as Member**:

Newly created RAM roles cannot be added directly via API. They need to be refreshed and synced in the console first:
1. Visit `https://dataworks.data.aliyun.com/{regionId}/sc?defaultProjectId={projectId}`
2. Go to "Workspace Members and Roles" page
3. Click "Add Member" button
4. Click "Refresh" in the popup to sync RAM roles
5. After sync is complete, add via API

**Expected Result**:
- Returns HTTP 200
- Member successfully added to workspace
- Member has Developer and Operator roles

---

### Scenario 3: Modify Member Roles

**Input**:
- Workspace ID: `12345`
- User ID: `234567890123456789`
- New role: Workspace Admin

**Expected Command**:
```bash
aliyun dataworks-public GrantMemberProjectRoles \
  --ProjectId 12345 \
  --UserId 234567890123456789 \
  --RoleCodes '["role_project_admin"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Expected Result**:
- Returns HTTP 200
- Member role list includes Workspace Admin

---

## Error Handling Criteria

### Expected Error Handling

| Scenario | Expected Error Code | Description |
|----------|---------------------|-------------|
| DataWorks not enabled | `9990010001` | DataWorks service not enabled, visit https://dataworks.console.aliyun.com/ to complete activation |
| Workspace not found | `InvalidProject.NotFound` | Query/operate on non-existent workspace ID |
| Member not found | `InvalidProjectMember.NotFound` | Query/operate on non-existent member |
| Insufficient permissions | `Forbidden.RAM` | Current user does not have permission to perform this operation |
| Missing parameter | `MissingParameter` | Required parameter not provided |
| Invalid parameter | `InvalidParameter` | Parameter value does not meet requirements |
| Invalid role code | `InvalidRoleCode` | Specified role code does not exist |
| Duplicate addition | `ProjectMemberAlreadyExists` | Member already in workspace |

### Error Handling Verification Example

```bash
# Test non-existent project
aliyun dataworks-public GetProject \
  --Id 999999999 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Expected error return
# {
#   "Code": "InvalidProject.NotFound",
#   "Message": "The specified project does not exist."
# }
```

---

## Checklist

### CLI Command Verification Checklist

- [ ] Product name uses `dataworks-public`
- [ ] CLI version >= 3.3.1
- [ ] Commands use PascalCase format (e.g., `CreateProject`)
- [ ] Parameters use PascalCase format (e.g., `--ProjectId`)
- [ ] Role codes use JSON array format (e.g., `'["role_project_dev"]'`)
- [ ] Workspace names use underscores not hyphens
- [ ] Each command includes `--endpoint dataworks.<region-id>.aliyuncs.com` parameter

### Business Scenario Verification Checklist

- [ ] Workspace can be accessed normally via access URL after creation
- [ ] RAM role has been refreshed and synced in console before adding
- [ ] Development role and development environment configurations have been carefully planned (cannot be reverted once enabled)
- [ ] DataWorks service has been enabled

---

## Official References

- [DataWorks OpenAPI Documentation](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-overview)
- [Alibaba Cloud CLI Documentation](https://help.aliyun.com/zh/cli/)
