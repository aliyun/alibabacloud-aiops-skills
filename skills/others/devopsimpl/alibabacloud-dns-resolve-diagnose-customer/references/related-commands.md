# Related CLI Commands - alibabacloud-dns-resolve-diagnose-customer

## Alidns (Alibaba Cloud DNS)

| CLI Command | Description |
|-------------|-------------|
| `aliyun alidns describe-domains --KeyWord <domain> --PageSize 100 --SearchMode LIKE` | Query domain list |
| `aliyun alidns describe-domain-info --DomainName <domain> --NeedDetailAttributes true` | Query domain details |
| `aliyun alidns describe-domain-records --DomainName <domain> --RRKeyWord <rr> --PageSize 500` | Query DNS records |
| `aliyun alidns describe-gtm-instances --Keyword <domain>` | Query GTM instance list (legacy version) |
| `aliyun alidns describe-dns-gtm-instances --Keyword <domain> --PageSize 100` | Query GTM instance list (new version) |
| `aliyun alidns describe-dns-gtm-instance --InstanceId <id>` | Query GTM instance details |
| `aliyun alidns describe-dns-gtm-access-strategies --InstanceId <id>` | Query GTM access strategies |

## Domain (Domain Name Service)

| CLI Command | Description |
|-------------|-------------|
| `aliyun domain query-domain-by-domain-name --DomainName <domain>` | Query domain registration info |

## PrivateZone (Internal DNS Resolution)

| CLI Command | Description |
|-------------|-------------|
| `aliyun pvtz describe-zones --Keyword <domain> --SearchMode LIKE --PageSize 100` | Query Zone list |
| `aliyun pvtz describe-zone-records --ZoneId <id> --PageSize 100` | Query Zone DNS records |
| `aliyun pvtz describe-zone-info --ZoneId <id>` | Query Zone details (including VPC bindings) |

## STS (Temporary Credentials)

| CLI Command | Description |
|-------------|-------------|
| `aliyun sts assume-role --RoleArn <arn> --RoleSessionName dns-diag-session --DurationSeconds 3600` | Obtain temporary credentials (cross-account) |
