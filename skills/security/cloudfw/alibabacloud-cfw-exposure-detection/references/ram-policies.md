# RAM Policies - Exposure Detection & Analysis

## Required Permissions

The following RAM permissions are required to execute all APIs in this skill:

| API Action | RAM Permission | Description |
|-----------|---------------|-------------|
| DescribeInternetOpenStatistic | yundun-cloudfirewall:DescribeInternetOpenStatistic | Query internet exposure statistics |
| DescribeInternetOpenIp | yundun-cloudfirewall:DescribeInternetOpenIp | Query exposed public IP list |
| DescribeInternetOpenPort | yundun-cloudfirewall:DescribeInternetOpenPort | Query exposed port list |
| DescribeAssetList | yundun-cloudfirewall:DescribeAssetList | Query protected asset list |
| DescribeAssetRiskList | yundun-cloudfirewall:DescribeAssetRiskList | Query asset risk details |
| DescribeVulnerabilityProtectedList | yundun-cloudfirewall:DescribeVulnerabilityProtectedList | Query vulnerability protection coverage |
| DescribeRiskEventGroup | yundun-cloudfirewall:DescribeRiskEventGroup | Query intrusion event groups |
| DescribeControlPolicy | yundun-cloudfirewall:DescribeControlPolicy | Query access control policies |

## Minimum RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-cloudfirewall:DescribeInternetOpenStatistic",
        "yundun-cloudfirewall:DescribeInternetOpenIp",
        "yundun-cloudfirewall:DescribeInternetOpenPort",
        "yundun-cloudfirewall:DescribeAssetList",
        "yundun-cloudfirewall:DescribeAssetRiskList",
        "yundun-cloudfirewall:DescribeVulnerabilityProtectedList",
        "yundun-cloudfirewall:DescribeRiskEventGroup",
        "yundun-cloudfirewall:DescribeControlPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policy Alternative

You can also attach the system policy `AliyunYundunCloudFirewallReadOnlyAccess` which grants read-only access to all Cloud Firewall resources.
