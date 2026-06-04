# RAM Policies for OOS Template Generation Skill

This document lists all RAM permissions required by the `alibabacloud-oos-template-generation` skill.

## Required Permissions

### Core Permissions (Required)

| API Action | Permission | Purpose |
|------------|------------|---------|
| `ListActions` | `oos:ListActions` | Query available Action list and property definitions |
| `ValidateTemplateContent` | `oos:ValidateTemplateContent` | Validate template syntax and semantics |

## Policy JSON Template

### Minimum Policy (Template Generation Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oos:ListActions",
        "oos:ValidateTemplateContent"
      ],
      "Resource": "*"
    }
  ]
}
```

### Extended Policy (Template Management + Execution)

If you need to create, execute, or manage templates after generation, additional permissions are required:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oos:ListActions",
        "oos:ValidateTemplateContent",
        "oos:CreateTemplate",
        "oos:UpdateTemplate",
        "oos:DeleteTemplate",
        "oos:GetTemplate",
        "oos:ListTemplates",
        "oos:StartExecution",
        "oos:GetExecution",
        "oos:ListExecutions",
        "oos:CancelExecution"
      ],
      "Resource": "*"
    }
  ]
}
```

### Cloud Product Permissions

Depending on the cloud product Actions used in the template, additional product-specific permissions are required:

| Policy | Description | Corresponding Action Examples |
|--------|-------------|-------------------------------|
| `AliyunECSFullAccess` | ECS service full access | ACS::ECS::RebootInstance, ACS::ECS::StartInstance |
| `AliyunRDSFullAccess` | RDS service full access | ACS::RDS::RestartInstance |
| `AliyunVPCFullAccess` | VPC service full access | ACS::ExecuteAPI (VPC related) |
| `AliyunOSSFullAccess` | OSS service full access | ACS::ExecuteAPI (OSS related) |
| `AliyunSLBFullAccess` | SLB service full access | ACS::ExecuteAPI (SLB related) |

## Applying Permissions

### Option 1: Using RAM Console (Recommended)

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Policies** > **Create Policy**
3. Choose **JSON** mode
4. Copy the appropriate policy JSON above
5. Save the policy with name: `OOS-TemplateGeneration-Policy`
6. Navigate to **Users** or **Roles**
7. Attach the `OOS-TemplateGeneration-Policy` to the target user/role

### Option 2: Using Aliyun CLI

Create policy file `oos-template-gen-policy.json` with the JSON above, then:

```bash
# Create the policy
aliyun ram create-policy \
  --policy-name OOS-TemplateGeneration-Policy \
  --policy-document "$(cat oos-template-gen-policy.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Attach to a user
aliyun ram attach-policy-to-user \
  --policy-name OOS-TemplateGeneration-Policy \
  --policy-type Custom \
  --user-name <your-ram-user-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Attach to a role
aliyun ram attach-policy-to-role \
  --policy-name OOS-TemplateGeneration-Policy \
  --policy-type Custom \
  --role-name <your-ram-role-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

## Permission Verification

After applying permissions, verify they work correctly:

```bash
# Test ListActions permission
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Test ValidateTemplateContent permission
aliyun oos validate-template-content \
  --biz-region-id cn-hangzhou \
  --content '{"FormatVersion":"OOS-2019-06-01","Description":{"en":"test","zh-cn":"test"},"Tasks":[{"Name":"test","Action":"ACS::Sleep","Properties":{"Duration":"PT1S"}}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

## Troubleshooting Permission Issues

### Error: "Forbidden.RAM"

**Cause**: Current account lacks required permissions

**Solution**:
1. Check which API action failed
2. Verify the corresponding permission exists in your policy
3. Re-attach the policy or add missing permissions

### Error: "InvalidAccessKeyId.NotFound"

**Cause**: Invalid or deleted AccessKey

**Solution**: Reconfigure credentials using `aliyun configure`

## Security Best Practices

1. **Use RAM users** instead of root account for daily operations
2. **Apply least privilege** — only grant `oos:ListActions` + `oos:ValidateTemplateContent` for template generation
3. **Rotate Access Keys** regularly (recommended every 90 days)
4. **Use ECS RAM Roles** for applications running on ECS instances
5. **Audit permission usage** via ActionTrail logs

## Related Links

- [RAM Product Documentation](https://help.aliyun.com/zh/ram/)
- [OOS API Reference](https://help.aliyun.com/zh/oos/developer-reference/api-overview)
