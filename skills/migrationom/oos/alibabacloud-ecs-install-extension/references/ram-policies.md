# RAM Policies for ECS Extension Installation

Required RAM permissions for the ECS Extension Installation skill.

## Permission List

| Permission | Action | Description |
|------------|--------|-------------|
| `bss:DescribeOrderDetail` | Query | Query order details for extension billing verification |
| `ecs:DescribeCloudAssistantStatus` | Query | Check Cloud Assistant status on target instances |
| `ecs:DescribeInstances` | Query | Verify instance information (status, region, etc.) |
| `ecs:DescribeInvocations` | Query | List Cloud Assistant command invocations |
| `ecs:DescribeInvocationResults` | Query | View Cloud Assistant command execution results |
| `ecs:RunCommand` | Write | Execute Cloud Assistant commands during installation |
| `oos:GetApplicationGroup` | Query | Get OOS application group information |
| `oos:GetTemplate` | Query | Get detailed information of a specific OOS template |
| `oos:ListInstancePackageStates` | Query | Query instance extension package installation status |
| `oos:ListTemplates` | Query | List available OOS templates (extension packages) |
| `oos:StartExecution` | Write | Start an OOS execution to install the extension |
| `oos:UpdateInstancePackageState` | Write | Update instance extension package state |
| `oss:GetObject` | Read | Download extension package files from OSS |

## Minimum Permission Policy

Use this policy when you only need extension installation functionality:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:DescribeOrderDetail",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInstances",
        "ecs:DescribeInvocations",
        "ecs:DescribeInvocationResults",
        "ecs:RunCommand",
        "oos:GetApplicationGroup",
        "oos:GetTemplate",
        "oos:ListInstancePackageStates",
        "oos:ListTemplates",
        "oos:StartExecution",
        "oos:UpdateInstancePackageState",
        "oss:GetObject"
      ],
      "Resource": "*"
    }
  ]
}
```

## Full Permission Policy (Recommended)

Recommended for production use with additional query and monitoring permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:DescribeOrderDetail",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInstances",
        "ecs:DescribeInvocations",
        "ecs:DescribeInvocationResults",
        "ecs:RunCommand",
        "oos:GetApplicationGroup",
        "oos:GetTemplate",
        "oos:ListExecutions",
        "oos:ListInstancePackageStates",
        "oos:ListTemplates",
        "oos:StartExecution",
        "oos:UpdateInstancePackageState",
        "oss:GetObject"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note:** `oos:ListExecutions` is used to query execution status and history, which is helpful for tracking installation progress. `ecs:DescribeInvocationResults` is used to view Cloud Assistant command execution results. `ecs:DescribeCloudAssistantStatus` checks if Cloud Assistant is installed and running on the instance. `oos:ListInstancePackageStates` and `oos:UpdateInstancePackageState` are used for managing extension package states on instances. `oss:GetObject` is required when the extension package needs to be downloaded from OSS. `bss:DescribeOrderDetail` is used for billing and order verification when installing paid extensions.

## Permission Verification Command

After attaching the policy, verify permissions:

```bash
# Verify OOS template query permission
aliyun oos list-templates \
  --biz-region-id cn-hangzhou \
  --template-type Package \
  --share-type Public \
  --max-results 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension

# Verify ECS instance query permission
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --max-results 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

If all commands return data successfully, permissions are correctly configured.

## Common Permission Errors and Troubleshooting

### Error: `Forbidden.RAM` / `NoPermission`

**Cause:** The RAM user does not have the required permissions.

**Solution:**
1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Find the target RAM user
3. Click "Add Permissions"
4. Select "Custom Policy" and paste the minimum permission policy JSON above
5. Or select system policies: `AliyunOOSFullAccess` + `AliyunECSFullAccess` (broader permissions)

### Error: `Forbidden` on `oos:StartExecution`

**Cause:** Missing OOS execution permission.

**Solution:** Ensure the policy includes `oos:StartExecution` action.

### Error: `Forbidden` on `ecs:RunCommand`

**Cause:** Cloud Assistant command execution permission is missing.

**Solution:** Ensure the policy includes `ecs:RunCommand` action. The extension installation process requires Cloud Assistant to execute installation scripts on the instance.

### Error: `InvalidAccount.NotFound`

**Cause:** Incorrect AccessKey or the account does not exist.

**Solution:**
- Check if AccessKey ID is correct
- Verify if the AccessKey is active in the RAM console
- Reconfigure credentials outside of this session using `aliyun configure` interactively or via environment variables

### Using Predefined System Policies

If custom policies are not convenient, you can directly attach the following system policies:

| System Policy | Description |
|---------------|-------------|
| `AliyunOOSFullAccess` | Full OOS permissions (includes ListTemplates, GetTemplate, StartExecution, etc.) |
| `AliyunECSFullAccess` | Full ECS permissions (includes RunCommand, DescribeInstances, etc.) |

Attach method:
```bash
# Attach through RAM console or CLI
aliyun ram attach-policy-to-user \
  --policy-type System \
  --policy-name AliyunOOSFullAccess \
  --user-name <your-ram-username> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

> **Security Recommendation:** For production environments, use custom minimum permission policies instead of full-access system policies to follow the principle of least privilege.
