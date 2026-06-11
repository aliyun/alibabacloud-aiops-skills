# RAM Policies - alibabacloud-dns-resolve-diagnose

All operations in this skill are read-only queries. The following minimum RAM permissions are required.

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

## Permission Usage

| Action | Purpose |
|--------|---------|
| `alidns:DescribeDomains` | Query domain list (verify domain belongs to current account) |
| `alidns:DescribeDomainInfo` | Query domain details (DNS servers, version, line type) |
| `alidns:DescribeDomainRecords` | Query DNS record configuration (core diagnostic data) |
| `alidns:DescribeGtmInstances` | Query GTM instance list (legacy) |
| `alidns:DescribeDnsGtmInstances` | Query GTM instance list (new) |
| `alidns:DescribeDnsGtmInstance` | Query GTM instance details |
| `alidns:DescribeGtmInstance` | Query GTM instance details (legacy) |
| `alidns:DescribeDnsGtmAccessStrategies` | Query GTM access strategies |
| `domain:QueryDomainByDomainName` | Query domain registration info (expiry, real-name status) |
| `pvtz:DescribeZones` | Query PrivateZone list |
| `pvtz:DescribeZoneRecords` | Query PrivateZone records |
| `pvtz:DescribeZoneInfo` | Query Zone details (including VPC bindings) |

## System Policies (Alternative)

- `AliyunDNSReadOnlyAccess` - Alibaba Cloud DNS read-only access
- `AliyunPvtzReadOnlyAccess` - PrivateZone read-only access
