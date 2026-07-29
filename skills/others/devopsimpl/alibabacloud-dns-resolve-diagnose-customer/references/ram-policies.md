# RAM Policies - alibabacloud-dns-resolve-diagnose-customer

All operations in this Skill are read-only queries and require the following minimum RAM permissions.

## Custom Policy (Recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "alidns:DescribeDomains",
        "alidns:DescribeDomainInfo",
        "alidns:DescribeDomainRecords",
        "alidns:DescribeGtmInstances",
        "alidns:DescribeDnsGtmInstances",
        "alidns:DescribeDnsGtmInstance",
        "alidns:DescribeGtmInstance",
        "alidns:DescribeDnsGtmAccessStrategies",
        "domain:QueryDomainByDomainName",
        "pvtz:DescribeZones",
        "pvtz:DescribeZoneRecords",
        "pvtz:DescribeZoneInfo"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Purpose Description

| Action | Purpose |
|--------|---------|
| `alidns:DescribeDomains` | Query domain list (verify whether a domain exists in the current account) |
| `alidns:DescribeDomainInfo` | Query domain details (DNS servers, edition, line type) |
| `alidns:DescribeDomainRecords` | Query DNS record configuration (core diagnostic basis) |
| `alidns:DescribeGtmInstances` | Query GTM instance list (legacy version) |
| `alidns:DescribeDnsGtmInstances` | Query GTM instance list (new version) |
| `alidns:DescribeDnsGtmInstance` | Query GTM instance details |
| `alidns:DescribeGtmInstance` | Query GTM instance details (legacy version) |
| `alidns:DescribeDnsGtmAccessStrategies` | Query GTM access strategies |
| `domain:QueryDomainByDomainName` | Query domain registration info (validity period, real-name status) |
| `pvtz:DescribeZones` | Query PrivateZone list |
| `pvtz:DescribeZoneRecords` | Query PrivateZone DNS records |
| `pvtz:DescribeZoneInfo` | Query Zone details (including VPC bindings) |

## System Policies (Alternative)

- `AliyunDNSReadOnlyAccess` - Alibaba Cloud DNS read-only permissions
- `AliyunPvtzReadOnlyAccess` - PrivateZone read-only permissions
