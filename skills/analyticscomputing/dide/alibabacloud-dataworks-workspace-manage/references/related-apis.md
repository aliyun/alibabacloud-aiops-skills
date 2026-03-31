# DataWorks Workspace Management - API and CLI Command Reference

## API Version Information

- **Product Code**: dataworks-public
- **API Version**: 2024-05-18
- **Endpoint**: dataworks.{regionId}.aliyuncs.com

---

## Workspace Management APIs

### CreateProject - Create Workspace

| Property | Value |
|----------|-------|
| API Name | CreateProject |
| CLI Command | `aliyun dataworks-public CreateProject` |
| HTTP Method | POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| Name | String | Yes | Workspace unique identifier name |
| DisplayName | String | No | Workspace display name |
| Description | String | No | Workspace description |
| PaiTaskEnabled | Boolean | No | Enable PAI task scheduling |
| DevEnvironmentEnabled | Boolean | No | Enable development environment |
| DevRoleDisabled | Boolean | No | Disable development role |
| AliyunResourceGroupId | String | No | Alibaba Cloud resource group ID |
| AliyunResourceTags | Array | No | Alibaba Cloud resource tags |

**Access URL After Successful Creation**:

```
https://dataworks.data.aliyun.com/{regionId}/sc?defaultProjectId={projectId}
```

Example (Hangzhou region):
```
https://dataworks.data.aliyun.com/cn-hangzhou/sc?defaultProjectId=12345
```

**Common Error Codes**:

| Error Code | Description | Solution |
|------------|-------------|----------|
| `9990010001` | DataWorks service not enabled | Visit https://dataworks.console.aliyun.com/ to complete service activation and retry |

**CLI Example**

```bash
aliyun dataworks-public CreateProject \
  --Name my_workspace \
  --DisplayName "My Workspace" \
  --Description "Test workspace" \
  --PaiTaskEnabled true \
  --DevEnvironmentEnabled true \
  --DevRoleDisabled false \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### UpdateProject - Update Workspace

| Property | Value |
|----------|-------|
| API Name | UpdateProject |
| CLI Command | `aliyun dataworks-public UpdateProject` |
| HTTP Method | POST |
| API Style | RPC |
| Official Documentation | [UpdateProject](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-updateproject) |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| Id | Long | Yes | Workspace ID |
| DisplayName | String | No | New display name |
| Description | String | No | New description |
| Status | String | No | Workspace status (Available/Disabled) |
| DevRoleDisabled | Boolean | No | Disable development role |
| DevEnvironmentEnabled | Boolean | No | Enable development environment |

**Important Limitations**:

| Configuration | Limitation |
|---------------|------------|
| DevRoleDisabled | Once development role is enabled, **cannot be disabled** |
| DevEnvironmentEnabled | Once development environment is enabled, **cannot be disabled** |

> ⚠️ **Note**: Development role and development environment cannot be disabled via API once enabled. Please plan these configurations carefully when creating or updating a workspace.

**CLI Example**

```bash
aliyun dataworks-public UpdateProject \
  --Id 12345 \
  --DisplayName "Updated Name" \
  --Description "Updated description" \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### DeleteProject - Delete Workspace

| Property | Value |
|----------|-------|
| API Name | DeleteProject |
| CLI Command | `aliyun dataworks-public DeleteProject` |
| HTTP Method | POST |
| API Style | RPC |
| Official Documentation | [DeleteProject](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-deleteproject) |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| Id | Long | Yes | Workspace ID |

**Recycle Bin Mechanism**:

After deleting a workspace, it is not permanently deleted immediately but goes to the recycle bin:

| Stage | Description |
|-------|-------------|
| After deletion | Workspace goes to recycle bin, status becomes pending cleanup |
| Silent period | Workspace is retained in recycle bin for **14 days** |
| Permanent deletion | After 14 days, workspace is permanently deleted and **cannot be recovered** |

> ⚠️ **Warning**: Please ensure necessary data backup is completed before deletion. Data cannot be recovered after the 14-day silent period.

**CLI Example**

```bash
aliyun dataworks-public DeleteProject \
  --Id 12345 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### GetProject - Query Workspace Details

| Property | Value |
|----------|-------|
| API Name | GetProject |
| CLI Command | `aliyun dataworks-public GetProject` |
| HTTP Method | GET/POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| Id | Long | Yes | Workspace ID |

**CLI Example**

```bash
aliyun dataworks-public GetProject \
  --Id 12345 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### ListProjects - Query Workspace List

| Property | Value |
|----------|-------|
| API Name | ListProjects |
| CLI Command | `aliyun dataworks-public ListProjects` |
| HTTP Method | GET/POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| Ids | Array | No | Workspace ID list, JSON array format |
| Names | Array | No | Workspace name list, JSON array format |
| Status | String | No | Status filter: Available/Initializing/InitFailed/Forbidden/Deleting/DeleteFailed/Frozen/Updating/UpdateFailed |
| DevEnvironmentEnabled | Boolean | No | Enable development environment |
| DevRoleDisabled | Boolean | No | Disable development role |
| PaiTaskEnabled | Boolean | No | Enable PAI task scheduling |
| AliyunResourceGroupId | String | No | Resource group ID |
| AliyunResourceTags | Array | No | Tag list |
| PageNumber | Integer | No | Page number, default 1 |
| PageSize | Integer | No | Items per page, default 10, max 100 |

**CLI Examples**

```bash
# Query all workspaces
aliyun dataworks-public ListProjects \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Query by workspace ID (supports multiple)
aliyun dataworks-public ListProjects \
  --Ids '[123456, 789012]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Query by workspace name (supports multiple)
aliyun dataworks-public ListProjects \
  --Names '["my_workspace", "test_workspace"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Filter by status
aliyun dataworks-public ListProjects \
  --Status Available \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Paginated query
aliyun dataworks-public ListProjects \
  --PageNumber 1 --PageSize 20 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

## Workspace Member Management APIs

### CreateProjectMember - Add Workspace Member

| Property | Value |
|----------|-------|
| API Name | CreateProjectMember |
| CLI Command | `aliyun dataworks-public CreateProjectMember` |
| HTTP Method | POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| UserId | String | Yes | Member user ID |
| RoleCodes | Array | Yes | Role code list, JSON array format |

**UserId Format Description**:

Alibaba Cloud account ID, RAM sub-account ID, and RAM role ID are all supported as UserId:

| Account Type | UserId Format | Example |
|--------------|---------------|---------|
| Alibaba Cloud Account (Main) | Use UID directly | `123456789012345678` |
| RAM Sub-account | Use UID directly | `234567890123456789` |
| RAM Role | Add `ROLE_` prefix | `ROLE_345678901234567890` |

> ⚠️ **Important**: Newly created RAM roles cannot be directly added as workspace members via API. You need to first visit the "Workspace Members and Roles" page in the workspace console, click the "Add Member" button, and click "Refresh" in the popup to sync the RAM role before adding via API.
>
> Console URL: `https://dataworks.data.aliyun.com/{regionId}/sc?defaultProjectId={projectId}`

**CLI Examples**

```bash
# Add Alibaba Cloud account or RAM sub-account
aliyun dataworks-public CreateProjectMember \
  --ProjectId 12345 \
  --UserId 234567890123456789 \
  --RoleCodes '["role_project_dev", "role_project_pe"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com

# Add RAM role (must refresh and sync in console first)
aliyun dataworks-public CreateProjectMember \
  --ProjectId 12345 \
  --UserId ROLE_345678901234567890 \
  --RoleCodes '["role_project_dev"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### DeleteProjectMember - Remove Workspace Member

| Property | Value |
|----------|-------|
| API Name | DeleteProjectMember |
| CLI Command | `aliyun dataworks-public DeleteProjectMember` |
| HTTP Method | POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| UserId | String | Yes | Member user ID |

**CLI Example**

```bash
aliyun dataworks-public DeleteProjectMember \
  --ProjectId 12345 \
  --UserId 234567890123456789 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### GrantMemberProjectRoles - Grant Member Roles

| Property | Value |
|----------|-------|
| API Name | GrantMemberProjectRoles |
| CLI Command | `aliyun dataworks-public GrantMemberProjectRoles` |
| HTTP Method | POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| UserId | String | Yes | Member user ID |
| RoleCodes | Array | Yes | Role code list |

**CLI Example**

```bash
aliyun dataworks-public GrantMemberProjectRoles \
  --ProjectId 12345 \
  --UserId 234567890123456789 \
  --RoleCodes '["role_project_admin", "role_project_dev"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### RevokeMemberProjectRoles - Revoke Member Roles

| Property | Value |
|----------|-------|
| API Name | RevokeMemberProjectRoles |
| CLI Command | `aliyun dataworks-public RevokeMemberProjectRoles` |
| HTTP Method | POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| UserId | String | Yes | Member user ID |
| RoleCodes | Array | Yes | Role codes to revoke |

**CLI Example**

```bash
aliyun dataworks-public RevokeMemberProjectRoles \
  --ProjectId 12345 \
  --UserId 234567890123456789 \
  --RoleCodes '["role_project_admin"]' \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### GetProjectMember - Query Member Details

| Property | Value |
|----------|-------|
| API Name | GetProjectMember |
| CLI Command | `aliyun dataworks-public GetProjectMember` |
| HTTP Method | GET/POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| UserId | String | Yes | Member user ID |

**CLI Example**

```bash
aliyun dataworks-public GetProjectMember \
  --ProjectId 12345 \
  --UserId 234567890123456789 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### ListProjectMembers - Query Member List

| Property | Value |
|----------|-------|
| API Name | ListProjectMembers |
| CLI Command | `aliyun dataworks-public ListProjectMembers` |
| HTTP Method | GET/POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| PageNumber | Integer | No | Page number |
| PageSize | Integer | No | Items per page |
| RoleCodes | Array | No | Filter by role |

**CLI Example**

```bash
aliyun dataworks-public ListProjectMembers \
  --ProjectId 12345 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

## Workspace Role Management APIs

### GetProjectRole - Query Role Details

| Property | Value |
|----------|-------|
| API Name | GetProjectRole |
| CLI Command | `aliyun dataworks-public GetProjectRole` |
| HTTP Method | GET/POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| Code | String | Yes | Role code |

**CLI Example**

```bash
aliyun dataworks-public GetProjectRole \
  --ProjectId 12345 \
  --Code role_project_admin \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

### ListProjectRoles - Query Role List

| Property | Value |
|----------|-------|
| API Name | ListProjectRoles |
| CLI Command | `aliyun dataworks-public ListProjectRoles` |
| HTTP Method | GET/POST |
| API Style | RPC |

**Request Parameters**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| ProjectId | Long | Yes | Workspace ID |
| Type | String | No | Role type filter |
| PageNumber | Integer | No | Page number |
| PageSize | Integer | No | Items per page |

**CLI Example**

```bash
aliyun dataworks-public ListProjectRoles \
  --ProjectId 12345 \
  --region <region-id> \
  --endpoint dataworks.<region-id>.aliyuncs.com
```

---

## Preset Role Code Reference

| Role Code | Role Name | Permission Description |
|-----------|-----------|------------------------|
| `role_project_owner` | Project Owner | Has all workspace permissions, creator gets by default |
| `role_project_admin` | Workspace Admin | Manage members, configurations, all features |
| `role_project_dev` | Developer | Data development, task debugging, ad-hoc queries |
| `role_project_pe` | Operator | Task operations, instance management, monitoring alerts |
| `role_project_deploy` | Deployer | Task publishing, package management |
| `role_project_guest` | Guest | Read-only view permissions |
| `role_project_security` | Security Admin | Data security, sensitive data management |
| `role_project_data_analyst` | Data Analyst | Data analysis, ad-hoc queries |
| `role_project_model_designer` | Model Designer | Data model design |
| `role_project_data_governance_admin` | Data Governance Admin | Data quality, data standards |

---

## Official API Documentation Links

- [CreateProject](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-createproject)
- [UpdateProject](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-updateproject)
- [DeleteProject](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-deleteproject)
- [GetProject](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getproject)
- [ListProjects](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listprojects)
- [CreateProjectMember](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-createprojectmember)
- [DeleteProjectMember](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-deleteprojectmember)
- [GrantMemberProjectRoles](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-grantmemberprojectroles)
- [RevokeMemberProjectRoles](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-revokememberprojectroles)
