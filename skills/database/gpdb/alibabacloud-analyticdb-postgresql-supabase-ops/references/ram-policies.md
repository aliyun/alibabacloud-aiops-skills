# RAM Policies for ADBPG Supabase Management

This document lists the RAM permissions required for ADBPG Supabase management operations.

## Required Permissions

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| ListSupabaseProjects | gpdb:ListSupabaseProjects | List Supabase instances |
| GetSupabaseProject | gpdb:GetSupabaseProject | Get Supabase instance details |
| GetSupabaseProjectApiKeys | gpdb:GetSupabaseProjectApiKeys | Get Supabase instance API Keys |
| GetSupabaseProjectDashboardAccount | gpdb:GetSupabaseProjectDashboardAccount | Get Supabase project Dashboard account info |
| CreateSupabaseProject | gpdb:CreateSupabaseProject | Create Supabase project |
| PauseSupabaseProject | gpdb:PauseSupabaseProject | Pause Supabase instance |
| ResumeSupabaseProject | gpdb:ResumeSupabaseProject | Resume Supabase instance |
| ResetSupabaseProjectPassword | gpdb:ResetSupabaseProjectPassword | Reset Supabase database password |
| ModifySupabaseProjectSecurityIps | gpdb:ModifySupabaseProjectSecurityIps | Modify Supabase project security IPs |
| DescribeRegions | gpdb:DescribeRegions | List available regions |
| DescribeVpcs | vpc:DescribeVpcs | List VPCs (optional before create) |
| DescribeVSwitches | vpc:DescribeVSwitches | List VSwitches (recommended when auto-selecting VSwitch) |

## RAM Policy Examples

### Read-Only Permissions (Query Operations)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "gpdb:ListSupabaseProjects",
        "gpdb:GetSupabaseProject",
        "gpdb:GetSupabaseProjectApiKeys",
        "gpdb:GetSupabaseProjectDashboardAccount",
        "gpdb:DescribeRegions"
      ],
      "Resource": "*"
    }
  ]
}
```

### Full Management Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "gpdb:ListSupabaseProjects",
        "gpdb:GetSupabaseProject",
        "gpdb:GetSupabaseProjectApiKeys",
        "gpdb:GetSupabaseProjectDashboardAccount",
        "gpdb:CreateSupabaseProject",
        "gpdb:PauseSupabaseProject",
        "gpdb:ResumeSupabaseProject",
        "gpdb:ResetSupabaseProjectPassword",
        "gpdb:ModifySupabaseProjectSecurityIps",
        "gpdb:DescribeRegions",
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    }
  ]
}
```

### VPC-Related Permissions (Required for Project Creation)

Creating a Supabase project requires VPC and VSwitch IDs. If the skill **discovers** them with `aliyun vpc describe-vpcs` / `describe-vswitches`, grant these read permissions in addition to GPDB:

```json
{
  "Version": "1",
  "Statement": [
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

## Permission Risk Levels

### Low-Risk Operations (No Special Approval Required)
- `ListSupabaseProjects` - List projects
- `GetSupabaseProject` - Get project details
- `GetSupabaseProjectApiKeys` - Get API Keys
- `GetSupabaseProjectDashboardAccount` - Get Dashboard account
- `ResumeSupabaseProject` - Resume paused project

### Medium-Risk Operations (Approval Recommended)
- `CreateSupabaseProject` - Create project (incurs costs)
- `PauseSupabaseProject` - Pause project (service unavailable)
- `ResetSupabaseProjectPassword` - Reset password (disconnects existing connections)
- `ModifySupabaseProjectSecurityIps` - Modify whitelist (affects access control)

## Reference Links

- [RAM Access Control Documentation](https://help.aliyun.com/product/28625.html)
- [GPDB Authorization Information](https://help.aliyun.com/document_detail/86923.html)
