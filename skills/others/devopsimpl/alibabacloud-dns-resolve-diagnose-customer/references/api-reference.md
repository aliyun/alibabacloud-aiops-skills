# DNS Diagnosis OpenAPI Reference

## Alibaba Cloud CLI General Usage

```bash
aliyun <product-code> <api-name> --<param-name> <value>
```

## Alidns (Alibaba Cloud DNS)

### describe-domains - Domain List

```bash
aliyun alidns describe-domains \
    --KeyWord example \
    --PageSize 100 \
    --SearchMode LIKE
```

Key response fields: `Domains.Domain[]` → `DomainName`, `DomainId`, `RecordCount`, `VersionCode`, `DnsServers`

### describe-domain-info - Domain Details

```bash
aliyun alidns describe-domain-info \
    --DomainName example.com \
    --NeedDetailAttributes true
```

Key response fields: `DomainName`, `DnsServers`, `VersionCode`(`mianfei`=Free Edition), `LineType`, `MinTtl`, `InBlackHole`, `RecordLines`

### describe-domain-records - DNS Records

```bash
aliyun alidns describe-domain-records \
    --DomainName example.com \
    --RRKeyWord www \
    --Type A \
    --PageSize 500
```

Key response fields: `DomainRecords.Record[]` → `RecordId`, `RR`, `Type`, `Value`, `TTL`, `Priority`, `Line`, `Status`(Enable/Disable), `Weight`, `Locked`, `CreateTimestamp`, `UpdateTimestamp`

## Domain (Domain Name Service)

### query-domain-by-domain-name - Domain Registration Info

```bash
aliyun domain query-domain-by-domain-name \
    --DomainName example.com
```

Key response fields: `DomainName`, `DomainStatus`(1=Urgent Renewal/2=Urgent Redemption/3=Normal), `ExpirationDate`, `DnsList`, `RealNameStatus`(NONAUDIT/SUCCEED/FAILED/AUDITING)

> Only domains registered under the current account can be queried.

## GTM (Global Traffic Manager)

### describe-dns-gtm-instances - GTM Instance List (New Version)

```bash
aliyun alidns describe-dns-gtm-instances \
    --Keyword example \
    --PageSize 100
```

### describe-gtm-instances - GTM Instance List (Legacy Version)

```bash
aliyun alidns describe-gtm-instances \
    --Keyword example
```

Key response fields: `InstanceId`, `InstanceName`, `Cname`, `UserDomainName`, `LbaStrategy`, `Ttl`, `ExpireTime`

### describe-dns-gtm-instance - GTM Instance Details

```bash
aliyun alidns describe-dns-gtm-instance \
    --InstanceId gtm-cn-xxxxx
```

## PrivateZone (Internal DNS Resolution)

### describe-zones - Zone List

```bash
aliyun pvtz describe-zones \
    --Keyword example.com \
    --SearchMode LIKE \
    --PageSize 100
```

Key response fields: `Zones.Zone[]` → `ZoneId`, `ZoneName`, `RecordCount`, `IsPtr`, `ProxyPattern`

### describe-zone-records - Zone DNS Records

```bash
aliyun pvtz describe-zone-records \
    --ZoneId <zone-id> \
    --PageSize 100
```

Key response fields: `Records.Record[]` → `RecordId`, `Rr`, `Type`, `Value`, `Ttl`, `Priority`, `Line`, `Weight`, `Status`(ENABLE/DISABLE)

### describe-zone-info - Zone Details (with VPC Bindings)

```bash
aliyun pvtz describe-zone-info \
    --ZoneId <zone-id>
```

Key response fields: `ZoneId`, `ZoneName`, `BindVpcs.Vpc[]` → `VpcId`, `VpcName`, `RegionId`

## STS (Temporary Credentials)

### assume-role - Obtain Temporary Credentials

```bash
aliyun sts assume-role \
    --RoleArn acs:ram::123456789:role/dns-diag-role \
    --RoleSessionName dns-diag-session \
    --DurationSeconds 3600
```

Response fields: `Credentials.AccessKeyId`, `Credentials.AccessKeySecret`, `Credentials.SecurityToken`, `Credentials.Expiration`

## Required RAM Permissions

Minimum permission policy for customer self-service diagnosis:

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
