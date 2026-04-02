# DataWorks Workspace Management - Operation Verification Methods

This document provides verification steps and expected results after each operation is completed.

## ⛔ PROHIBITED OPERATIONS

> The following operations are **PROHIBITED** via this Skill:
> - `UpdateProject` - Update workspace
> - `DeleteProject` - Delete workspace
> - `DeleteProjectMember` - Remove workspace member
> - `RevokeMemberProjectRoles` - Revoke member roles
>
> Users must perform these operations manually via the DataWorks Console.

---

## Workspace Operation Verification

### 1. Create Workspace Verification

**Operation**: `aliyun dataworks-public CreateProject`

**Verification Steps**:

```bash
# Step 1: Create workspace
aliyun dataworks-public CreateProject \
  --Name test_workspace_001 \
  --DisplayName "Test Workspace" \
  --Description "Workspace for verification testing" \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Step 2: Get project ID from response
# Expected response contains: "Id": <project-id>

# Step 3: Verify workspace has been created
aliyun dataworks-public GetProject \
  --Id <project-id> \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Access URL After Successful Creation**:

After a workspace is successfully created, it can be accessed via the following URL:
```
https://dataworks.data.aliyun.com/{regionId}/sc?defaultProjectId={projectId}
```

Example (Hangzhou region, project ID 12345):
```
https://dataworks.data.aliyun.com/cn-hangzhou/sc?defaultProjectId=12345
```

**Expected Result**:
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "Project": {
    "Id": 12345,
    "Name": "test_workspace_001",
    "DisplayName": "Test Workspace",
    "Description": "Workspace for verification testing",
    "Status": "Available"
  }
}
```

**Common Error Handling**:

| Error Code | Description | Solution |
|------------|-------------|----------|
| `9990010001` | DataWorks service not enabled | Visit https://dataworks.console.aliyun.com/ to complete activation and retry |

**Verification Points**:
- [ ] Return status code is 200
- [ ] Returned workspace name matches the one specified during creation
- [ ] Workspace status is `Available`
- [ ] Workspace can be accessed normally via access URL

---

### 2. Query Workspace List Verification

**Operation**: `aliyun dataworks-public ListProjects`

**Verification Steps**:

```bash
aliyun dataworks-public ListProjects \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Expected Result**:
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "PagingInfo": {
    "PageNumber": 1,
    "PageSize": 10,
    "TotalCount": 5
  },
  "Projects": [
    {
      "Id": 12345,
      "Name": "workspace_001",
      "DisplayName": "Workspace 1",
      "Status": "Available"
    }
  ]
}
```

**Verification Points**:
- [ ] Return status code is 200
- [ ] Returned list contains expected workspaces
- [ ] Pagination information is correct

---

## Member Management Operation Verification

### 5. Add Workspace Member Verification

**Operation**: `aliyun dataworks-public CreateProjectMember`

**UserId Format Description**:

Alibaba Cloud account ID, RAM sub-account ID, and RAM role ID are all supported as UserId:

| Account Type | UserId Format | Example |
|--------------|---------------|---------|
| Alibaba Cloud Account (Main) | Use UID directly | `123456789012345678` |
| RAM Sub-account | Use UID directly | `234567890123456789` |
| RAM Role | Add `ROLE_` prefix | `ROLE_345678901234567890` |

**Verification Steps**:

```bash
# Step 1: Add member (using Alibaba Cloud account or RAM sub-account)
aliyun dataworks-public CreateProjectMember \
  --ProjectId <project-id> \
  --UserId <user-uid> \
  --RoleCodes '["role_project_dev"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Step 2: Verify member has been added
aliyun dataworks-public GetProjectMember \
  --ProjectId <project-id> \
  --UserId <user-uid> \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Adding RAM Role as Member**:

Newly created RAM roles cannot be added directly via API. They need to be refreshed and synced in the console first:

1. Visit workspace console:
   ```
   https://dataworks.data.aliyun.com/{regionId}/sc?defaultProjectId={projectId}
   ```
2. Go to **Workspace Members and Roles** page
3. Click **Add Member** button
4. In the popup, click **Refresh** in the prompt "You can go to RAM console to create a sub-account, and click refresh to sync to this page"
5. After sync is complete, add RAM role member via API

```bash
# Add RAM role as member (must refresh and sync in console first)
aliyun dataworks-public CreateProjectMember \
  --ProjectId <project-id> \
  --UserId ROLE_<ram-role-id> \
  --RoleCodes '["role_project_dev"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Expected Result**:
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "ProjectMember": {
    "ProjectId": 12345,
    "UserId": "234567890123456789",
    "Roles": [
      {
        "Code": "role_project_dev",
        "Name": "Developer"
      }
    ]
  }
}
```

**Verification Points**:
- [ ] Return status code is 200
- [ ] Member's role list contains granted roles
- [ ] RAM role has been refreshed and synced in console before adding

---

### 6. Query Member List Verification

**Operation**: `aliyun dataworks-public ListProjectMembers`

**Verification Steps**:

```bash
aliyun dataworks-public ListProjectMembers \
  --ProjectId <project-id> \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Expected Result**:
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "PagingInfo": {
    "TotalCount": 3
  },
  "ProjectMembers": [
    {
      "UserId": "234567890123456789",
      "Roles": [...]
    }
  ]
}
```

**Verification Points**:
- [ ] Return status code is 200
- [ ] Member list contains newly added member
- [ ] Total member count is correct

---

### 7. Grant Member Roles Verification

**Operation**: `aliyun dataworks-public GrantMemberProjectRoles`

**Verification Steps**:

```bash
# Step 1: Grant new roles
aliyun dataworks-public GrantMemberProjectRoles \
  --ProjectId <project-id> \
  --UserId <user-id> \
  --RoleCodes '["role_project_pe"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Step 2: Verify roles have been granted
aliyun dataworks-public GetProjectMember \
  --ProjectId <project-id> \
  --UserId <user-id> \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Expected Result**:
- Member's role list now contains the newly granted role

**Verification Points**:
- [ ] Return status code is 200
- [ ] Member role list contains `role_project_pe`

---

---

## Role Management Operation Verification

### 10. Query Role List Verification

**Operation**: `aliyun dataworks-public ListProjectRoles`

**Verification Steps**:

```bash
aliyun dataworks-public ListProjectRoles \
  --ProjectId <project-id> \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

**Expected Result**:
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "ProjectRoles": [
    {
      "Code": "role_project_owner",
      "Name": "Project Owner",
      "Type": "System"
    },
    {
      "Code": "role_project_admin",
      "Name": "Workspace Admin",
      "Type": "System"
    },
    {
      "Code": "role_project_dev",
      "Name": "Developer",
      "Type": "System"
    }
  ]
}
```

**Verification Points**:
- [ ] Return status code is 200
- [ ] Contains system preset roles
- [ ] Role information is complete (Code, Name, Type)

---

## Error Handling Verification

### Common Error Codes and Handling

| Error Code | Description | Verification Method |
|------------|-------------|---------------------|
| `9990010001` | DataWorks service not enabled | Create workspace under account without service enabled |
| `InvalidProject.NotFound` | Workspace not found | Query non-existent project ID |
| `InvalidProjectMember.NotFound` | Member not found | Query non-existent member ID |
| `Forbidden.RAM` | Insufficient permissions | Execute operation with user without permissions |
| `InvalidParameter` | Parameter error | Pass invalid parameter value |

---

## Verification Checklist

After completing all verifications, ensure the following items have passed:

- [ ] Workspace created successfully and can be queried
- [ ] Workspace list query returns correct results
- [ ] Member added successfully and assigned correct roles
- [ ] Member list query returns all members
- [ ] Role grant operation took effect
- [ ] Error handling meets expectations
