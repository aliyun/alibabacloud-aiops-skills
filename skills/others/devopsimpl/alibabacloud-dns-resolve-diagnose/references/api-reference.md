# DNS Diagnostic OpenAPI Reference

## Aliyun CLI General Usage (Plugin Mode)

```bash
aliyun <product> <action-in-kebab-case> --<param> <value> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

## Alidns (Alibaba Cloud DNS)

### describe-domains - Domain List

```bash
aliyun alidns describe-domains \
    --KeyWord example \
    --PageSize 100 \
    --SearchMode LIKE \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `Domains.Domain[]` -> `DomainName`, `DomainId`, `RecordCount`, `VersionCode`, `DnsServers`

### describe-domain-info - Domain Details

```bash
aliyun alidns describe-domain-info \
    --DomainName example.com \
    --NeedDetailAttributes true \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `DomainName`, `DnsServers`, `VersionCode` (`mianfei`=free tier), `LineType`, `MinTtl`, `InBlackHole`, `RecordLines`

### describe-domain-records - DNS Records

```bash
aliyun alidns describe-domain-records \
    --DomainName example.com \
    --RRKeyWord www \
    --Type A \
    --PageSize 500 \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `DomainRecords.Record[]` -> `RecordId`, `RR`, `Type`, `Value`, `TTL`, `Priority`, `Line`, `Status` (Enable/Disable), `Weight`, `Locked`, `CreateTimestamp`, `UpdateTimestamp`

## Domain (Domain Service)

### query-domain-by-domain-name - Domain Registration Info

```bash
aliyun domain query-domain-by-domain-name \
    --DomainName example.com \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `DomainName`, `DomainStatus` (1=renewal urgent/2=redemption urgent/3=normal), `ExpirationDate`, `DnsList`, `RealNameStatus` (NONAUDIT/SUCCEED/FAILED/AUDITING)

> Can only query domains registered under the current account.

## GTM (Global Traffic Manager)

### describe-dns-gtm-instances - GTM Instance List (New)

```bash
aliyun alidns describe-dns-gtm-instances \
    --Keyword example \
    --PageSize 100 \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

### describe-gtm-instances - GTM Instance List (Legacy)

```bash
aliyun alidns describe-gtm-instances \
    --Keyword example \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `InstanceId`, `InstanceName`, `Cname`, `UserDomainName`, `LbaStrategy`, `Ttl`, `ExpireTime`

### describe-dns-gtm-instance - GTM Instance Details

```bash
aliyun alidns describe-dns-gtm-instance \
    --InstanceId gtm-cn-xxxxx \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

## PrivateZone (Internal DNS)

### describe-zones - Zone List

```bash
aliyun pvtz describe-zones \
    --Keyword example.com \
    --SearchMode LIKE \
    --PageSize 100 \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `Zones.Zone[]` -> `ZoneId`, `ZoneName`, `RecordCount`, `IsPtr`, `ProxyPattern`

### describe-zone-records - Zone Records

```bash
aliyun pvtz describe-zone-records \
    --ZoneId <zone-id> \
    --PageSize 100 \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `Records.Record[]` -> `RecordId`, `Rr`, `Type`, `Value`, `Ttl`, `Priority`, `Line`, `Weight`, `Status` (ENABLE/DISABLE)

### describe-zone-info - Zone Details (with VPC Bindings)

```bash
aliyun pvtz describe-zone-info \
    --ZoneId <zone-id> \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Key response fields: `ZoneId`, `ZoneName`, `BindVpcs.Vpc[]` -> `VpcId`, `VpcName`, `RegionId`

## STS (Security Token Service)

### assume-role - Get Temporary Credentials

```bash
aliyun sts assume-role \
    --RoleArn acs:ram::123456789:role/dns-diag-role \
    --RoleSessionName dns-diag-session \
    --DurationSeconds 3600 \
    --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Response fields: `Credentials.AccessKeyId`, `Credentials.AccessKeySecret`, `Credentials.SecurityToken`, `Credentials.Expiration`
