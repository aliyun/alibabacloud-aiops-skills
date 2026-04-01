# RAM Policies for ECS Diagnostics Skill

This document lists all RAM permissions required by the `alibabacloud-ecs-diagnose` skill.

## Required Permissions

### Basic Diagnostics: Cloud Platform Checks (Read-Only)

| API Action | Permission | Purpose |
|------------|------------|---------|
| `DescribeInstances` | `ecs:DescribeInstances` | Query instance details |
| `DescribeInstanceAttribute` | `ecs:DescribeInstanceAttribute` | Query instance attributes |
| `DescribeInstanceStatus` | `ecs:DescribeInstanceStatus` | Query instance status |
| `DescribeInstancesFullStatus` | `ecs:DescribeInstancesFullStatus` | Query full instance status |
| `DescribeInstanceHistoryEvents` | `ecs:DescribeInstanceHistoryEvents` | Query system events |
| `DescribeSecurityGroupAttribute` | `ecs:DescribeSecurityGroupAttribute` | Query security group rules |
| `DescribeVpcs` | `vpc:DescribeVpcs` | Query VPC information |
| `DescribeEipAddresses` | `vpc:DescribeEipAddresses` | Query EIP binding status |
| `DescribeMetricLast` | `cms:DescribeMetricLast` | Query monitoring metrics |

### Deep Diagnostics: System & Service Checks

| API Action | Permission | Purpose |
|------------|------------|---------|
| `RunCommand` | `ecs:RunCommand` | Execute commands via Cloud Assistant |
| `DescribeInvocationResults` | `ecs:DescribeInvocationResults` | Query command execution results |

## Policy JSON Template

### Minimum Read-Only Policy (Basic Diagnostics Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeInstanceHistoryEvents",
        "ecs:DescribeSecurityGroupAttribute"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricLast"
      ],
      "Resource": "*"
    }
  ]
}
```

### Full Diagnostics Policy (Basic + Deep)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeInstanceHistoryEvents",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:RunCommand",
        "ecs:DescribeInvocationResults"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricLast"
      ],
      "Resource": "*"
    }
  ]
}
```

## Applying Permissions

### Option 1: Using RAM Console (Recommended for Production)

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Policies** → **Create Policy**
3. Choose **JSON** mode
4. Copy the appropriate policy JSON above
5. Save the policy with name: `ECS-Diagnostics-Policy`
6. Navigate to **Users** or **Roles**
7. Attach the `ECS-Diagnostics-Policy` to the target user/role

### Option 2: Using Aliyun CLI

Create policy file `ecs-diagnostics-policy.json` with the JSON above, then:

```bash
# Create the policy
aliyun ram create-policy \
  --policy-name ECS-Diagnostics-Policy \
  --policy-document file://ecs-diagnostics-policy.json \
  --user-agent AlibabaCloud-Agent-Skills

# Attach to a user
aliyun ram attach-policy-to-user \
  --policy-name ECS-Diagnostics-Policy \
  --policy-type Custom \
  --user-name <your-ram-user-name> \
  --user-agent AlibabaCloud-Agent-Skills

# Attach to a role
aliyun ram attach-policy-to-role \
  --policy-name ECS-Diagnostics-Policy \
  --policy-type Custom \
  --role-name <your-ram-role-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

## Least Privilege Principle

- If you only need **Basic Diagnostics**, use the **Minimum Read-Only Policy**
- If you need **both Basic and Deep Diagnostics**, use the **Full Diagnostics Policy**
- Never grant more permissions than necessary
- Regularly audit and review permission usage

## Permission Verification

After applying permissions, verify they work correctly:

```bash
# Test ECS read permission
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills

# Test VPC read permission
aliyun vpc describe-vpcs \
  --region-id cn-hangzhou \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills

# Test CMS read permission
aliyun cms describe-metric-last \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --user-agent AlibabaCloud-Agent-Skills

# Test Cloud Assistant permission (only if Deep Diagnostics is needed)
aliyun ecs describe-invocation-results \
  --region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
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

### Error: "Forbidden.Risk"

**Cause**: Account locked due to security risk

**Solution**: Contact Alibaba Cloud support to unlock account

## Security Best Practices

1. **Use RAM users instead of root account** for daily operations
2. **Enable MFA (Multi-Factor Authentication)** for sensitive operations
3. **Rotate AccessKeys regularly** (recommended every 90 days)
4. **Use RAM roles** for applications running on ECS instances
5. **Audit permission usage** via ActionTrail logs
6. **Apply IP restrictions** if accessing from fixed locations
7. **Use resource-level permissions** when possible (though this skill requires `*` for flexibility)

## Related Links

- [RAM Product Documentation](https://www.alibabacloud.com/help/ram)
- [ECS API Reference](https://www.alibabacloud.com/help/ecs/developer-reference/api-overview)
- [VPC API Reference](https://www.alibabacloud.com/help/vpc/developer-reference/api-overview)
- [Cloud Monitor API Reference](https://www.alibabacloud.com/help/cms/developer-reference/api-overview)
