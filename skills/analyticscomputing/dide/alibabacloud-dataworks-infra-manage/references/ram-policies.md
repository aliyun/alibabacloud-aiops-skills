# DataWorks Infrastructure RAM Policies

## Permission Matrix

### Data Source Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| CreateDataSource | dataworks:CreateDataSource | Write |
| GetDataSource | dataworks:GetDataSource | Read |
| ListDataSources | dataworks:ListDataSources | List |
| TestDataSourceConnectivity | dataworks:TestDataSourceConnectivity | Read |

### Compute Resource Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| CreateComputeResource | dataworks:CreateComputeResource | Write |
| GetComputeResource | dataworks:GetComputeResource | Read |
| ListComputeResources | dataworks:ListComputeResources | List |

### Resource Group Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| CreateResourceGroup | dataworks:CreateResourceGroup | Write |
| GetResourceGroup | dataworks:GetResourceGroup | Read |
| ListResourceGroups | dataworks:ListResourceGroups | List |
| AssociateProjectToResourceGroup | dataworks:AssociateProjectToResourceGroup | Write |
| DissociateProjectFromResourceGroup | dataworks:DissociateProjectFromResourceGroup | Write |
| ListResourceGroupAssociateProjects | dataworks:ListResourceGroupAssociateProjects | List |

### Workspace Member Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| ListProjectRoles | dataworks:ListProjectRoles | List |
| ListProjectMembers | dataworks:ListProjectMembers | List |
| GetProjectMember | dataworks:GetProjectMember | Read |
| CreateProjectMember | dataworks:CreateProjectMember | Write |
| DeleteProjectMember | dataworks:DeleteProjectMember | Write |
| GrantMemberProjectRoles | dataworks:GrantMemberProjectRoles | Write |
| RevokeMemberProjectRoles | dataworks:RevokeMemberProjectRoles | Write |

### VPC Permissions (required for resource group operations)

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| DescribeVpcs | vpc:DescribeVpcs | Read |
| DescribeVSwitches | vpc:DescribeVSwitches | Read |

## Role Requirements

| Operation | Required DataWorks Roles |
|------|---------------------|
| Create resource | Tenant Owner, Workspace Admin, Project Owner, Operator |
| View resource | Tenant Owner, Workspace Admin, Deployer, Developer, Project Owner, Operator |
| List resources | All roles |

## RAM Policy Examples

### Full Access

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateDataSource",
        "dataworks:GetDataSource",
        "dataworks:ListDataSources",
        "dataworks:TestDataSourceConnectivity",
        "dataworks:CreateComputeResource",
        "dataworks:GetComputeResource",
        "dataworks:ListComputeResources",
        "dataworks:CreateResourceGroup",
        "dataworks:GetResourceGroup",
        "dataworks:ListResourceGroups",
        "dataworks:AssociateProjectToResourceGroup",
        "dataworks:DissociateProjectFromResourceGroup",
        "dataworks:ListResourceGroupAssociateProjects",
        "dataworks:ListProjects",
        "dataworks:ListProjectRoles",
        "dataworks:ListProjectMembers",
        "dataworks:GetProjectMember",
        "dataworks:CreateProjectMember",
        "dataworks:DeleteProjectMember",
        "dataworks:GrantMemberProjectRoles",
        "dataworks:RevokeMemberProjectRoles"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    }
  ]
}
```

### Read-Only

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:GetDataSource",
        "dataworks:ListDataSources",
        "dataworks:GetComputeResource",
        "dataworks:ListComputeResources",
        "dataworks:GetResourceGroup",
        "dataworks:ListResourceGroups",
        "dataworks:ListResourceGroupAssociateProjects",
        "dataworks:ListProjectMembers",
        "dataworks:GetProjectMember",
        "dataworks:ListProjectRoles"
      ],
      "Resource": "*"
    }
  ]
}
```

### Resource Group Management

> Creating resource groups requires additionally attaching the `AliyunBSSOrderAccess` system policy.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateResourceGroup",
        "dataworks:GetResourceGroup",
        "dataworks:ListResourceGroups",
        "dataworks:AssociateProjectToResourceGroup",
        "dataworks:DissociateProjectFromResourceGroup",
        "dataworks:ListResourceGroupAssociateProjects",
        "dataworks:ListProjects"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:ViewOrder",
        "bss:PayOrder"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policies Reference

| Policy Name | Description |
|----------|------|
| AliyunDataWorksFullAccess | DataWorks full access |
| AliyunVPCReadOnlyAccess | VPC read-only access |
| AliyunBSSOrderAccess | BSS order access (required for creating resource groups) |

## References

- [DataWorks RAM Permission Documentation](https://help.aliyun.com/zh/dataworks/user-guide/manage-members-and-roles)
- [RAM Console](https://ram.console.aliyun.com/)
