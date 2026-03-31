# RAM Policies — PAI Workspace Management

## Overview

The following RAM permissions are required to execute this Skill. Following the principle of least privilege, only permissions needed for creating, querying, and listing workspaces are granted.

## Permission List

| Product | RAM Action | Resource Scope | Description |
|---------|------------|----------------|-------------|
| PAI AIWorkSpace | `paiworkspace:CreateWorkspace` | `*` | Create PAI workspace |
| PAI AIWorkSpace | `paiworkspace:GetWorkspace` | `*` | Query workspace details (for verification) |
| PAI AIWorkSpace | `paiworkspace:ListWorkspaces` | `*` | List workspaces |

## RAM Policy JSON

Attach the following policy to the RAM user or RAM role:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "paiworkspace:CreateWorkspace",
        "paiworkspace:GetWorkspace",
        "paiworkspace:ListWorkspaces"
      ],
      "Resource": "*"
    }
  ]
}
```

## Action Details

| Action | Access Level | Required |
|--------|-------------|----------|
| `paiworkspace:CreateWorkspace` | Write | Required |
| `paiworkspace:GetWorkspace` | Read | Recommended (for post-creation verification) |
| `paiworkspace:ListWorkspaces` | List | Recommended (for listing workspaces) |

## Notes

- **RAM user vs. root account**: It is strongly recommended to use a RAM user rather than the primary account's Access Key.
- **Least privilege**: If you only need to create workspaces, grant only `paiworkspace:CreateWorkspace`.
- **Resource group permissions**: If `ResourceGroupId` is specified, `resourcemanager:GetResourceGroup` permission may also be required.
- Create custom policies in the RAM console: https://ram.console.aliyun.com/policies
