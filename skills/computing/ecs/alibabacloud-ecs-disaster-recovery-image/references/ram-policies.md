# RAM Policies -- alibabacloud-ecs-disaster-recovery-image

This document lists the RAM permissions required by this Skill for the entire cross-AZ disaster recovery flow. Use the principle of least privilege and grant only the Actions listed below.

## Required Permissions

| Action | Resource | Used In | Description |
|--------|----------|---------|-------------|
| `ecs:DescribeInstances` | `acs:ecs:*:*:instance/*` | Step 1, Step 6 | Query configuration of source and new instances (type, network, billing mode, etc.) |
| `ecs:DescribeDisks` | `acs:ecs:*:*:disk/*` | Step 1, Step 6 | Query disks attached to source and new instances (DiskId, Category, PerformanceLevel, Size, Device) |
| `ecs:CreateImage` | `acs:ecs:*:*:instance/*`<br>`acs:ecs:*:*:image/*` | Step 2 | Create a whole-instance image (system disk + data disks) from the source instance |
| `ecs:DescribeImages` | `acs:ecs:*:*:image/*` | Step 3 | Poll image creation progress until status becomes Available |
| `ecs:DescribeAvailableResource` | `*` | Step 4 | Check whether the target zone supports the desired instance type and system disk category |
| `ecs:DescribeVSwitches` | `acs:vpc:*:*:vswitch/*` | Step 4 | List VSwitches in the source VPC for the target zone |
| `ecs:RunInstances` | `acs:ecs:*:*:instance/*`<br>`acs:ecs:*:*:image/*`<br>`acs:vpc:*:*:vswitch/*`<br>`acs:ecs:*:*:securitygroup/*` | Step 5 | Create the new instance from the image in the target zone |
| `vpc:CreateVSwitch` | `acs:vpc:*:*:vpc/*`<br>`acs:vpc:*:*:vswitch/*` | Step 4 (conditional) | Create a new VSwitch when none exists in the target zone within the source VPC |

## Recommended Policy (JSON)

Attach the following policy directly to the RAM user or role executing this Skill:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeImages",
        "ecs:DescribeAvailableResource",
        "ecs:DescribeVSwitches",
        "ecs:CreateImage",
        "ecs:RunInstances"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:CreateVSwitch",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policy Reference (if you prefer not to author a custom policy)

| System Policy | Coverage | Notes |
|---------------|----------|-------|
| `AliyunECSFullAccess` | Full read/write on ECS resources | Covers all ECS-related operations in this Skill |
| `AliyunVPCFullAccess` | Full read/write on VPC resources | Covers VSwitch query and creation |

> For security reasons, **do NOT** grant `AliyunECSFullAccess` and `AliyunVPCFullAccess` directly. Prefer the least-privilege custom policy above.

## Permission Sanity Check

Before starting the flow, you can quickly verify that the current identity holds the most critical permissions with the following command:

```bash
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

If it returns `Forbidden.RAM` or `NoPermission`, follow the "Permission Failure Handling" process to grant the missing permissions to the identity.
