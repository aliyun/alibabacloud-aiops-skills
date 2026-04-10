# RAM Policies for OpenClaw ECS DingTalk Deployment

This document lists all RAM permissions required for deploying OpenClaw on Alibaba Cloud ECS with DingTalk integration.

## Required RAM Permissions

### Overview

This skill requires permissions across multiple Alibaba Cloud products:
- **ECS**: Instance, security group, and image management
- **VPC**: Virtual network and VSwitch management
- **VPC (EIP)**: Elastic IP address management
- **STS**: Identity verification
- **Model Studio (Bailian)**: Workspace and API Key management for Bailian LLM service

### System Policies (Not Recommended for Production)

> **Warning**: These `FullAccess` policies grant broad permissions that exceed the minimum required for this Skill. Using them in production environments violates the principle of least privilege. For production use, please use the custom policy in the "Detailed API-Level Permissions" section below.

| Policy Name | Purpose | Attached To |
|-------------|---------|-------------|
| `AliyunECSFullAccess` | Full access to ECS resources | RAM User/Role |
| `AliyunVPCFullAccess` | Full access to VPC resources | RAM User/Role |
| `AliyunEIPFullAccess` | Full access to EIP resources | RAM User/Role |
| `AliyunSTSAssumeRoleAccess` | STS identity verification | RAM User/Role |

### Detailed API-Level Permissions (Recommended)

For production environments following the least-privilege principle, create a custom policy with these specific permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeAvailableResource",
        "ecs:DescribeImages",
        "ecs:RunInstances",
        "ecs:StartInstance",
        "ecs:DescribeInstances",
        "ecs:DeleteInstance",
        "ecs:CreateSecurityGroup",
        "ecs:AuthorizeSecurityGroup",
        "ecs:DeleteSecurityGroup",
        "ecs:RunCommand",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:CreateVpc",
        "vpc:CreateVSwitch",
        "vpc:DeleteVpc",
        "vpc:DeleteVSwitch",
        "vpc:AllocateEipAddress",
        "vpc:AssociateEipAddress",
        "vpc:ReleaseEipAddress"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "modelstudio:ListWorkspaces",
        "modelstudio:ListApiKeys",
        "modelstudio:CreateApiKey"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Details by Step

### Step 1: ECS Instance Creation

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `GetCallerIdentity` | `sts:GetCallerIdentity` | Verify account identity |
| `DescribeAvailableResource` | `ecs:DescribeAvailableResource` | Check zone availability |
| `CreateVpc` | `vpc:CreateVpc` | Create VPC network |
| `CreateVSwitch` | `vpc:CreateVSwitch` | Create VSwitch |
| `CreateSecurityGroup` | `ecs:CreateSecurityGroup` | Create security group |
| `AuthorizeSecurityGroup` | `ecs:AuthorizeSecurityGroup` | Configure firewall rules |
| `DescribeImages` | `ecs:DescribeImages` | Query Ubuntu image |
| `RunInstances` | `ecs:RunInstances` | Create ECS instance |
| `AllocateEipAddress` | `vpc:AllocateEipAddress` | Create EIP |
| `AssociateEipAddress` | `vpc:AssociateEipAddress` | Bind EIP to instance |
| `StartInstance` | `ecs:StartInstance` | Start instance |
| `DescribeInstances` | `ecs:DescribeInstances` | Query instance status |

### Step 2: Bailian API Key Retrieval

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `ListWorkspaces` | `modelstudio:ListWorkspaces` | List Bailian workspaces to get workspace ID |
| `ListApiKeys` | `modelstudio:ListApiKeys` | Query existing API Keys in workspace |
| `CreateApiKey` | `modelstudio:CreateApiKey` | Create new API Key if none exists |

### Step 3: Cloud Assistant Commands

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `RunCommand` | `ecs:RunCommand` | Execute remote commands |
| `DescribeInvocations` | `ecs:DescribeInvocations` | Query command results |

### Resource Cleanup

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `DeleteInstance` | `ecs:DeleteInstance` | Delete ECS instance |
| `ReleaseEipAddress` | `vpc:ReleaseEipAddress` | Release EIP |
| `DeleteSecurityGroup` | `ecs:DeleteSecurityGroup` | Delete security group |
| `DeleteVSwitch` | `vpc:DeleteVSwitch` | Delete VSwitch |
| `DeleteVpc` | `vpc:DeleteVpc` | Delete VPC |

## How to Attach Policies

### Option 1: Creating Custom Policy (Recommended - Least Privilege)

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions** > **Policies**
3. Click **Create Policy**
4. Select **Script** mode
5. Copy and paste the JSON policy from "Detailed API-Level Permissions" section above
6. Name the policy: `OpenClawDeploymentPolicy`
7. Click **OK** to create
8. Navigate to **Identities** > **Users**
9. Find your RAM user and click **Add Permissions**
10. Select **Custom Policy** and choose `OpenClawDeploymentPolicy`
11. Click **OK** to attach

### Option 2: Using System Policies (Not Recommended for Production)

> **Warning**: This option uses `FullAccess` policies that grant more permissions than necessary. Only use this for quick testing or development environments, not for production.

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Identities** > **Users**
3. Find your RAM user and click **Add Permissions**
4. Select the following policies:
    - `AliyunECSFullAccess`
    - `AliyunVPCFullAccess`
    - `AliyunEIPFullAccess`
    - `AliyunSTSAssumeRoleAccess`
5. Click **OK** to attach

## Permission Verification

After attaching permissions, verify access using the CLI:

```bash
# Verify STS access
aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills

# Verify ECS access
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills

# Verify VPC access
aliyun vpc describe-vpcs --region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

If any command returns a `Forbidden` error, the corresponding permission is missing.

## Common Permission Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `Forbidden.RAM` | RAM user lacks permission for the action | Attach the required policy listed above |
| `Forbidden.RiskControl` | Account restricted by risk control | Contact Alibaba Cloud support |
| `InvalidAccessKeyId.NotFound` | Access Key ID invalid | Verify credentials are correct |
| `NoPermission` | No permission for the resource | Check resource ownership or attach policy |

## Security Best Practices

1. **Use RAM users instead of root account**: Never use the Alibaba Cloud root account for API access
2. **Apply least privilege principle**: Use custom policies instead of `FullAccess` policies in production
3. **Rotate access keys regularly**: Change access keys every 90 days
4. **Enable MFA**: Add multi-factor authentication to RAM users
5. **Audit API calls**: Enable ActionTrail to track all API operations
6. **Scope permissions by resource**: Use resource-level permissions when possible (requires ARN specification)

## Additional Resources

- [RAM Policy Syntax](https://www.alibabacloud.com/help/en/ram/user-guide/policy-structure-and-syntax)
- [ECS API Permissions](https://www.alibabacloud.com/help/en/ecs/developer-reference/api-permissions)
- [VPC API Permissions](https://www.alibabacloud.com/help/en/vpc/developer-reference/api-permissions)
- [RAM Console](https://ram.console.aliyun.com/)
