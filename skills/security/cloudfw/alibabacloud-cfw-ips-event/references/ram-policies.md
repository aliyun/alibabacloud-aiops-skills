# RAM Policies - IPS Alert Event Analysis

## Required Permissions

| API Action | RAM Permission | Description |
|-----------|---------------|-------------|
| DescribeRiskEventStatistic | yundun-cloudfirewall:DescribeRiskEventStatistic | Query IPS alert statistics (attack counts, severity distribution) |
| DescribeRiskEventGroup | yundun-cloudfirewall:DescribeRiskEventGroup | Query IPS alert event details with filtering and pagination |
| DescribeRiskEventTopAttackAsset | yundun-cloudfirewall:DescribeRiskEventTopAttackAsset | Query top attacked assets ranking |
| DescribeRiskEventTopAttackType | yundun-cloudfirewall:DescribeRiskEventTopAttackType | Query top attack types ranking |
| DescribeRiskEventTopAttackApp | yundun-cloudfirewall:DescribeRiskEventTopAttackApp | Query top attacked applications ranking |
| DescribeDefaultIPSConfig | yundun-cloudfirewall:DescribeDefaultIPSConfig | Query IPS protection configuration status |
| DescribeSignatureLibVersion | yundun-cloudfirewall:DescribeSignatureLibVersion | Query IPS rule library version information |

## Minimum RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-cloudfirewall:DescribeRiskEventStatistic",
        "yundun-cloudfirewall:DescribeRiskEventGroup",
        "yundun-cloudfirewall:DescribeRiskEventTopAttackAsset",
        "yundun-cloudfirewall:DescribeRiskEventTopAttackType",
        "yundun-cloudfirewall:DescribeRiskEventTopAttackApp",
        "yundun-cloudfirewall:DescribeDefaultIPSConfig",
        "yundun-cloudfirewall:DescribeSignatureLibVersion"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policy Alternative

Instead of creating a custom policy, you can attach the system policy:

**AliyunYundunCloudFirewallReadOnlyAccess**

This system policy grants read-only access to all Cloud Firewall resources, which includes all the permissions required by this skill.
