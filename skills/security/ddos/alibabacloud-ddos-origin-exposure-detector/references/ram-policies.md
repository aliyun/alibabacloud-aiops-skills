# RAM Policies — ddos-origin-exposure-detector

The minimum RAM permissions required to run this skill. Read-only policies are recommended.

## Required permissions

| API | Action | Description |
|-----|--------|-------------|
| ddoscoo DescribeInstances | `yundun-ddoscoo:DescribeInstances` | Query the account's Anti-DDoS instance list (instance existence check) |
| ddoscoo DescribeWebRules | `yundun-ddoscoo:DescribeWebRules` | Query layer-7 website forwarding rules (domain/CNAME/origin/port) |
| ddoscoo DescribeNetworkRules | `yundun-ddoscoo:DescribeNetworkRules` | Query layer-4 port forwarding rules (port/origin/protocol) |
| ddoscoo DescribeDomains (optional) | `yundun-ddoscoo:DescribeDomains` | Query the configured protected-domain list |
| Cms DescribeSiteMonitorISPCityList | `cms:DescribeSiteMonitorISPCityList` | Query the probe-point list (get city/isp codes, optional) |
| Cms CreateInstantSiteMonitor | `cms:CreateInstantSiteMonitor` | Create a one-off probe task (DNS/HTTP/TCP probing) |
| Cms DescribeSiteMonitorLog | `cms:DescribeSiteMonitorLog` | Read probe task results |

## Custom policy JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddoscoo:DescribeInstances",
        "yundun-ddoscoo:DescribeWebRules",
        "yundun-ddoscoo:DescribeNetworkRules",
        "yundun-ddoscoo:DescribeDomains"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeSiteMonitorISPCityList",
        "cms:CreateInstantSiteMonitor",
        "cms:DescribeSiteMonitorLog"
      ],
      "Resource": "*"
    }
  ]
}
```

## System policy reference
- `AliyunYundunDDoSReadOnlyAccess` (Anti-DDoS read-only)
- `AliyunCloudMonitorFullAccess` or a custom read-only + one-off probe permission
