# Related APIs - Exposure Detection & Analysis

## APIs Used in This Skill

| Product | API Action | CLI Command | Description | Key Parameters |
|---------|-----------|-------------|-------------|----------------|
| Cloudfw | DescribeInternetOpenStatistic | `aliyun cloudfw describe-internet-open-statistic` | Query internet exposure statistics (open IPs, ports, risks) | --StartTime, --EndTime |
| Cloudfw | DescribeInternetOpenIp | `aliyun cloudfw describe-internet-open-ip` | Query exposed public IP list with risk info (paginated) | --CurrentPage, --PageSize, --StartTime, --EndTime, --SearchItem, --AssetsType |
| Cloudfw | DescribeInternetOpenPort | `aliyun cloudfw describe-internet-open-port` | Query exposed port list with risk assessment (paginated) | --CurrentPage, --PageSize, --StartTime, --EndTime, --Port |
| Cloudfw | DescribeAssetList | `aliyun cloudfw describe-asset-list` | Query protected asset list with firewall status (paginated) | --CurrentPage, --PageSize, --Status, --ResourceType, --SearchItem, --NewResourceTag, --IpVersion |
| Cloudfw | DescribeAssetRiskList | `aliyun cloudfw describe-asset-risk-list` | Query detailed risk reasons per IP | --IpVersion, --IpAddrList |
| Cloudfw | DescribeVulnerabilityProtectedList | `aliyun cloudfw describe-vulnerability-protected-list` | Query vulnerability protection coverage (paginated) | --CurrentPage, --PageSize, --StartTime, --EndTime, --VulnLevel |
| Cloudfw | DescribeRiskEventGroup | `aliyun cloudfw describe-risk-event-group` | Query intrusion event groups (paginated) | --CurrentPage, --PageSize, --StartTime, --EndTime, --DataType, --Direction, --SrcIP, --DstIP, --VulLevel |
| Cloudfw | DescribeControlPolicy | `aliyun cloudfw describe-control-policy` | Query internet border ACL policies (paginated) | --Direction, --CurrentPage, --PageSize |

## API Version

All Cloud Firewall APIs use version: `2017-12-07`

## Endpoint Format

The CLI resolves endpoints automatically based on the `--region` flag.
Manual endpoint: `cloudfw.{regionId}.aliyuncs.com`

## API Style

All Cloud Firewall APIs use **RPC** style with `POST` method.
The CLI handles this automatically — no style configuration needed.
