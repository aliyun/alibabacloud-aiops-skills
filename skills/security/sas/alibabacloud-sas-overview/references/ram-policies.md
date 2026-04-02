# RAM Policies

## Required Permissions

The following RAM permissions are required for all APIs used in this skill.

### SAS (Security Center)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:DescribeScreenScoreThread",
        "yundun-sas:DescribeVulFixStatistics",
        "yundun-sas:GetDefenceCount",
        "yundun-sas:GetCheckRiskStatistics",
        "yundun-sas:DescribeVersionConfig",
        "yundun-sas:ListUninstallAegisMachines",
        "yundun-sas:DescribeSecureSuggestion",
        "yundun-sas:DescribeCloudCenterInstances",
        "yundun-sas:DescribeFieldStatistics",
        "yundun-sas:DescribeContainerFieldStatistics",
        "yundun-sas:GetCloudAssetSummary",
        "yundun-sas:DescribeChartData"
      ],
      "Resource": "*"
    }
  ]
}
```

### WAF (Web Application Firewall)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribeFlowChart"
      ],
      "Resource": "*"
    }
  ]
}
```

### BssOpenApi (Billing)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:QueryBill"
      ],
      "Resource": "*"
    }
  ]
}
```

## Recommended System Policy

For read-only access, attach the following managed policies:

| Policy Name | Scope |
|-------------|-------|
| `AliyunYundunSASReadOnlyAccess` | SAS read-only |
| `AliyunWAFReadOnlyAccess` | WAF read-only |
| `AliyunBSSReadOnlyAccess` | Billing read-only |
