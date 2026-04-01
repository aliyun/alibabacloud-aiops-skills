# RAM Policies - Cloud Firewall Status Overview

## Required Permissions

The following RAM permissions are required to execute all APIs in this skill:

| API Action | RAM Permission | Description |
|-----------|---------------|-------------|
| DescribeAssetList | yundun-cloudfirewall:DescribeAssetList | Query protected asset list |
| DescribeAssetStatistic | yundun-cloudfirewall:DescribeAssetStatistic | Query asset statistics |
| DescribeUserBuyVersion | yundun-cloudfirewall:DescribeUserBuyVersion | Query instance version info |
| DescribeInternetOpenStatistic | yundun-cloudfirewall:DescribeInternetOpenStatistic | Query internet exposure stats |
| DescribeVpcFirewallSummaryInfo | yundun-cloudfirewall:DescribeVpcFirewallSummaryInfo | Query VPC firewall summary |
| DescribeTrFirewallsV2List | yundun-cloudfirewall:DescribeTrFirewallsV2List | List CEN Enterprise firewalls |
| DescribeVpcFirewallCenList | yundun-cloudfirewall:DescribeVpcFirewallCenList | List CEN Basic firewalls |
| DescribeVpcFirewallList | yundun-cloudfirewall:DescribeVpcFirewallList | List Express Connect firewalls |
| DescribeNatFirewallList | yundun-cloudfirewall:DescribeNatFirewallList | List NAT firewalls |
| DescribeInternetTrafficTrend | yundun-cloudfirewall:DescribeInternetTrafficTrend | Query internet traffic trend |
| DescribePostpayTrafficTotal | yundun-cloudfirewall:DescribePostpayTrafficTotal | Query total traffic stats |
| DescribeInternetDropTrafficTrend | yundun-cloudfirewall:DescribeInternetDropTrafficTrend | Query defense/block trend |

## Minimum RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-cloudfirewall:DescribeAssetList",
        "yundun-cloudfirewall:DescribeAssetStatistic",
        "yundun-cloudfirewall:DescribeUserBuyVersion",
        "yundun-cloudfirewall:DescribeInternetOpenStatistic",
        "yundun-cloudfirewall:DescribeVpcFirewallSummaryInfo",
        "yundun-cloudfirewall:DescribeTrFirewallsV2List",
        "yundun-cloudfirewall:DescribeVpcFirewallCenList",
        "yundun-cloudfirewall:DescribeVpcFirewallList",
        "yundun-cloudfirewall:DescribeNatFirewallList",
        "yundun-cloudfirewall:DescribeInternetTrafficTrend",
        "yundun-cloudfirewall:DescribePostpayTrafficTotal",
        "yundun-cloudfirewall:DescribeInternetDropTrafficTrend"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policy Alternative

You can also attach the system policy `AliyunYundunCloudFirewallReadOnlyAccess` which grants read-only access to all Cloud Firewall resources.
