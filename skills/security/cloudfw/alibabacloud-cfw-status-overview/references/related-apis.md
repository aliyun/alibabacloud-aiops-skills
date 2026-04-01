# Related APIs - Cloud Firewall Status Overview

## APIs Used in This Skill

| Product | API Action | CLI Command | Description | Key Parameters |
|---------|-----------|-------------|-------------|----------------|
| Cloudfw | DescribeAssetList | `aliyun cloudfw DescribeAssetList` | Query protected asset list (paginated) | --CurrentPage, --PageSize, --Status, --ResourceType, --RegionNo, --IpVersion, --MemberUid, --SearchItem |
| Cloudfw | DescribeAssetStatistic | `aliyun cloudfw DescribeAssetStatistic` | Query asset protection statistics | --Lang |
| Cloudfw | DescribeUserBuyVersion | `aliyun cloudfw DescribeUserBuyVersion` | Query user's purchased version/instance info | --InstanceId |
| Cloudfw | DescribeInternetOpenStatistic | `aliyun cloudfw DescribeInternetOpenStatistic` | Query internet exposure statistics | --StartTime, --EndTime |
| Cloudfw | DescribeVpcFirewallSummaryInfo | `aliyun cloudfw DescribeVpcFirewallSummaryInfo` | Query VPC firewall summary info | --Lang |
| Cloudfw | DescribeTrFirewallsV2List | `aliyun cloudfw DescribeTrFirewallsV2List` | List CEN Enterprise Edition TR firewalls | --CurrentPage, --PageSize, --FirewallSwitchStatus, --RegionNo |
| Cloudfw | DescribeVpcFirewallCenList | `aliyun cloudfw DescribeVpcFirewallCenList` | List CEN Basic Edition VPC firewalls | --CurrentPage, --PageSize, --FirewallSwitchStatus, --RegionNo, --VpcId, --CenId |
| Cloudfw | DescribeVpcFirewallList | `aliyun cloudfw DescribeVpcFirewallList` | List Express Connect VPC firewalls | --CurrentPage, --PageSize, --FirewallSwitchStatus, --RegionNo, --VpcId |
| Cloudfw | DescribeNatFirewallList | `aliyun cloudfw DescribeNatFirewallList` | List NAT border firewalls | --Lang, --NatGatewayId, --ProxyId, --Status, --RegionNo, --MemberUid |
| Cloudfw | DescribeInternetTrafficTrend | `aliyun cloudfw DescribeInternetTrafficTrend` | Query internet traffic trend | --StartTime, --EndTime, --Direction, --SourceCode, --TrafficType |
| Cloudfw | DescribePostpayTrafficTotal | `aliyun cloudfw DescribePostpayTrafficTotal` | Query total traffic statistics | --Lang |
| Cloudfw | DescribeInternetDropTrafficTrend | `aliyun cloudfw DescribeInternetDropTrafficTrend` | Query internet defense/block trend | --Direction, --StartTime, --EndTime, --SourceCode |

## API Version

All Cloud Firewall APIs use version: `2017-12-07`

## Endpoint Format

The CLI resolves endpoints automatically based on the `--region` flag.
Manual endpoint: `cloudfw.{regionId}.aliyuncs.com`

## API Style

All Cloud Firewall APIs use **RPC** style with `POST` method.
The CLI handles this automatically — no style configuration needed.
