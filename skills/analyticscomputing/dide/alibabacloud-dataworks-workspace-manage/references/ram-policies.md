# DataWorks Workspace Management - RAM Permission Policies

This document lists the RAM permission policy configurations required to use the DataWorks Workspace Management Skill.

---

## Complete Permission Policy

The following policy includes all workspace management related permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateProject",
        "dataworks:UpdateProject",
        "dataworks:DeleteProject",
        "dataworks:GetProject",
        "dataworks:ListProjects",
        "dataworks:CreateProjectMember",
        "dataworks:DeleteProjectMember",
        "dataworks:GrantMemberProjectRoles",
        "dataworks:RevokeMemberProjectRoles",
        "dataworks:GetProjectMember",
        "dataworks:ListProjectMembers",
        "dataworks:GetProjectRole",
        "dataworks:ListProjectRoles"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permission Policies by Function

### 1. Workspace Read-Only Permission

Suitable for scenarios that only need to view workspace information:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:GetProject",
        "dataworks:ListProjects",
        "dataworks:GetProjectMember",
        "dataworks:ListProjectMembers",
        "dataworks:GetProjectRole",
        "dataworks:ListProjectRoles"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Workspace Management Permission

Suitable for administrators who need to create, update, and delete workspaces:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateProject",
        "dataworks:UpdateProject",
        "dataworks:DeleteProject",
        "dataworks:GetProject",
        "dataworks:ListProjects"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Member Management Permission

Suitable for scenarios that need to manage workspace members:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateProjectMember",
        "dataworks:DeleteProjectMember",
        "dataworks:GrantMemberProjectRoles",
        "dataworks:RevokeMemberProjectRoles",
        "dataworks:GetProjectMember",
        "dataworks:ListProjectMembers",
        "dataworks:GetProjectRole",
        "dataworks:ListProjectRoles"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Resource-Level Permission Control

To restrict access to specific workspaces, you can use resource-level permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:GetProject",
        "dataworks:UpdateProject",
        "dataworks:ListProjectMembers",
        "dataworks:CreateProjectMember"
      ],
      "Resource": [
        "acs:dataworks:*:*:project/12345",
        "acs:dataworks:*:*:project/67890"
      ]
    }
  ]
}
```

Resource format description:
- `acs:dataworks:{region}:{accountId}:project/{projectId}`
- Use `*` to represent all regions or all accounts
- Can specify multiple workspace IDs

---

## Permission Details

| Permission | Description | Corresponding CLI Command |
|------------|-------------|---------------------------|
| `dataworks:CreateProject` | Create new DataWorks workspace | `CreateProject` |
| `dataworks:UpdateProject` | Update workspace configuration | `UpdateProject` |
| `dataworks:DeleteProject` | Delete workspace (irrecoverable) | `DeleteProject` |
| `dataworks:GetProject` | Query workspace details | `GetProject` |
| `dataworks:ListProjects` | List workspaces under current account | `ListProjects` |
| `dataworks:CreateProjectMember` | Add member to workspace | `CreateProjectMember` |
| `dataworks:DeleteProjectMember` | Remove member from workspace | `DeleteProjectMember` |
| `dataworks:GrantMemberProjectRoles` | Grant roles to member | `GrantMemberProjectRoles` |
| `dataworks:RevokeMemberProjectRoles` | Revoke roles from member | `RevokeMemberProjectRoles` |
| `dataworks:GetProjectMember` | Query member details | `GetProjectMember` |
| `dataworks:ListProjectMembers` | List all workspace members | `ListProjectMembers` |
| `dataworks:GetProjectRole` | Query role details | `GetProjectRole` |
| `dataworks:ListProjectRoles` | List all workspace roles | `ListProjectRoles` |

---

## System Policies

Alibaba Cloud provides the following DataWorks-related system policies:

| Policy Name | Description |
|-------------|-------------|
| `AliyunDataWorksFullAccess` | DataWorks full access permission |
| `AliyunDataWorksReadOnlyAccess` | DataWorks read-only permission |

### Attach System Policy

```bash
# Attach full access permission
aliyun ram attach-policy-to-user \
  --policy-name AliyunDataWorksFullAccess \
  --policy-type System \
  --user-name <ram-user-name>

# Attach read-only permission
aliyun ram attach-policy-to-user \
  --policy-name AliyunDataWorksReadOnlyAccess \
  --policy-type System \
  --user-name <ram-user-name>
```

---

## Create Custom Policy

### Create via Console

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Select **Permission Management** > **Permission Policies**
3. Click **Create Permission Policy**
4. Select **Script Editor**, paste the above policy JSON
5. Fill in the policy name, such as `DataWorksWorkspaceManage`
6. Click **OK** to create the policy

### Create via CLI

```bash
# Create policy file
cat > dataworks-workspace-policy.json << 'EOF'
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateProject",
        "dataworks:UpdateProject",
        "dataworks:DeleteProject",
        "dataworks:GetProject",
        "dataworks:ListProjects",
        "dataworks:CreateProjectMember",
        "dataworks:DeleteProjectMember",
        "dataworks:GrantMemberProjectRoles",
        "dataworks:RevokeMemberProjectRoles",
        "dataworks:GetProjectMember",
        "dataworks:ListProjectMembers",
        "dataworks:GetProjectRole",
        "dataworks:ListProjectRoles"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create RAM policy
aliyun ram create-policy \
  --policy-name DataWorksWorkspaceManage \
  --policy-document "$(cat dataworks-workspace-policy.json)" \
  --description "DataWorks workspace management permissions"

# Attach policy to user
aliyun ram attach-policy-to-user \
  --policy-name DataWorksWorkspaceManage \
  --policy-type Custom \
  --user-name <ram-user-name>
```

---

## Best Practices

1. **Principle of Least Privilege** — Grant only the minimum permissions needed to complete tasks
2. **Use Custom Policies** — Create fine-grained custom policies based on actual needs
3. **Regular Audits** — Regularly check and clean up unnecessary permissions
4. **Use Resource-Level Control** — Restrict access to specific workspaces where possible
5. **Separate Responsibilities** — Use different permission policies for different roles

---

## Frequently Asked Questions

### Q: Why am I receiving Forbidden.RAM error?

A: The current user does not have permission to perform this operation. Please check:
1. Whether the user has been granted the corresponding RAM policy
2. Whether the policy includes the required Actions
3. Whether Resource restricts the access scope

### Q: How to view current user's permissions?

```bash
# View user's policies
aliyun ram list-policies-for-user --user-name <ram-user-name>

# View policy details
aliyun ram get-policy \
  --policy-name DataWorksWorkspaceManage \
  --policy-type Custom
```

### Q: What additional permissions are needed to delete a workspace?

Deleting a workspace is a high-risk operation. In addition to `dataworks:DeleteProject` permission, it is recommended to ensure the user has the workspace admin role permission.

---

## Related Documentation

- [Alibaba Cloud RAM Permission Policy Syntax](https://help.aliyun.com/zh/ram/user-guide/policy-structure-and-syntax)
- [DataWorks Permission System Overview](https://help.aliyun.com/zh/dataworks/user-guide/permission-system-overview)
- [RAM Access Control](https://help.aliyun.com/zh/ram/)
