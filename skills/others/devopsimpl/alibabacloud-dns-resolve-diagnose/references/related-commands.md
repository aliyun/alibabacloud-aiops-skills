# Related CLI Commands - alibabacloud-dns-resolve-diagnose

## Alidns (Alibaba Cloud DNS)

| CLI Command | Description |
|-------------|-------------|
| `aliyun alidns describe-domains --KeyWord <domain> --PageSize 100 --SearchMode LIKE --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query domain list |
| `aliyun alidns describe-domain-info --DomainName <domain> --NeedDetailAttributes true --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query domain details |
| `aliyun alidns describe-domain-records --DomainName <domain> --RRKeyWord <rr> --PageSize 500 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query DNS records |
| `aliyun alidns describe-gtm-instances --Keyword <domain> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query GTM instance list (legacy) |
| `aliyun alidns describe-dns-gtm-instances --Keyword <domain> --PageSize 100 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query GTM instance list (new) |
| `aliyun alidns describe-dns-gtm-instance --InstanceId <id> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query GTM instance details |
| `aliyun alidns describe-dns-gtm-access-strategies --InstanceId <id> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query GTM access strategies |

## Domain (Domain Service)

| CLI Command | Description |
|-------------|-------------|
| `aliyun domain query-domain-by-domain-name --DomainName <domain> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query domain registration info |

## PrivateZone (Internal DNS)

| CLI Command | Description |
|-------------|-------------|
| `aliyun pvtz describe-zones --Keyword <domain> --SearchMode LIKE --PageSize 100 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query zone list |
| `aliyun pvtz describe-zone-records --ZoneId <id> --PageSize 100 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query zone records |
| `aliyun pvtz describe-zone-info --ZoneId <id> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Query zone details (with VPC bindings) |

## STS (Security Token Service)

| CLI Command | Description |
|-------------|-------------|
| `aliyun sts assume-role --RoleArn <arn> --RoleSessionName dns-diag-session --DurationSeconds 3600 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}` | Get temporary credentials (cross-account) |
