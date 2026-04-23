# Related APIs - IPS Alert Event Analysis

## APIs Used in This Skill

| Product | API Action | CLI Command | Description | Key Parameters |
|---------|-----------|-------------|-------------|----------------|
| Cloud Firewall (cloudfw) | DescribeRiskEventStatistic | `aliyun cloudfw describe-risk-event-statistic` | Query IPS alert statistics including attack counts, block counts, and severity distribution | `--StartTime`, `--EndTime` |
| Cloud Firewall (cloudfw) | DescribeRiskEventGroup | `aliyun cloudfw describe-risk-event-group` | Query detailed IPS alert event list with filtering, pagination, and grouping | `--CurrentPage`, `--PageSize`, `--StartTime`, `--EndTime`, `--DataType`, `--Direction`, `--SrcIP`, `--DstIP`, `--VulLevel` |
| Cloud Firewall (cloudfw) | DescribeRiskEventTopAttackAsset | `aliyun cloudfw describe-risk-event-top-attack-asset` | Query top attacked assets ranking by attack count | `--StartTime`, `--EndTime` |
| Cloud Firewall (cloudfw) | DescribeRiskEventTopAttackType | `aliyun cloudfw describe-risk-event-top-attack-type` | Query top attack types ranking with protection stats | `--StartTime`, `--EndTime`, `--Direction` |
| Cloud Firewall (cloudfw) | DescribeRiskEventTopAttackApp | `aliyun cloudfw describe-risk-event-top-attack-app` | Query top attacked applications ranking | `--StartTime`, `--EndTime` |
| Cloud Firewall (cloudfw) | DescribeDefaultIPSConfig | `aliyun cloudfw describe-default-ipsconfig` | Query IPS protection configuration (run mode, rule switches) | (none required) |
| Cloud Firewall (cloudfw) | DescribeSignatureLibVersion | `aliyun cloudfw describe-signature-lib-version` | Query IPS rule library version and update time | (none required) |

**Product**: Cloud Firewall
**API Version**: 2017-12-07
**Product Code**: cloudfw

All commands must include `--user-agent AlibabaCloud-Agent-Skills` and `--region {RegionId}`.
