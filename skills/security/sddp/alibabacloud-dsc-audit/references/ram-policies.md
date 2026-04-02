# Data Security Center RAM Permission Configuration

## Required Permissions List

Using this skill requires the following RAM permissions:

| API | RAM Permission | Description |
|-----|----------------|-------------|
| DescribeRiskRules | `yundun-sddp:DescribeRiskRules` | Query security risk events |
| PreHandleAuditRisk | `yundun-sddp:PreHandleAuditRisk` | Handle security risk events |

## Custom Policy Examples

### Minimum Privilege Policy (Recommended)

Grant only the minimum permissions required for this skill:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sddp:DescribeRiskRules",
        "yundun-sddp:PreHandleAuditRisk"
      ],
      "Resource": "*"
    }
  ]
}
```

### Read-Only Query Policy

Allow only querying risk events, no handling:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sddp:DescribeRiskRules"
      ],
      "Resource": "*"
    }
  ]
}
```

## Configuration Steps

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permission Management** > **Permission Policies**
3. Click **Create Permission Policy**
4. Select **Script Edit** mode
5. Paste the policy content above
6. Name the policy (e.g., `DSCAuditPolicy`)
7. Attach the policy to the RAM user or role that needs to use this skill

## Permission Verification

Run the following command to verify the current user has the required permissions:

```bash
# Test query permission using aliyun CLI
aliyun sddp DescribeRiskRules --region cn-zhangjiakou --CurrentPage 1 --PageSize 1
```

If results are returned instead of a permission error, the query permission is granted.

## Important Notes

1. **Principle of Least Privilege**: Grant only the permissions actually needed for this skill
2. **Permission Separation**: Query and handling permissions can be granted separately to different roles
3. **Audit Trail**: RAM operations are recorded in ActionTrail for security auditing
4. **Regular Review**: Periodically check permission configurations and remove permissions that are no longer needed
