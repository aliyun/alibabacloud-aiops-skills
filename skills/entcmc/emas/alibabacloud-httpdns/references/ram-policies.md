# RAM Permissions

HTTPDNS domain resource authorization reference:
https://help.aliyun.com/document_detail/435245.html

## Minimum actions

| API | RAM action | Resource shape |
| --- | --- | --- |
| `GetAccountInfo` | `httpdns:GetAccountInfo` | `acs:httpdns:*:$accountid:*` |
| `AddDomain` | `httpdns:AddDomain` | `acs:httpdns:*:$accountid:domain/$domainName` |
| `DeleteDomain` | `httpdns:DeleteDomain` | `acs:httpdns:*:$accountid:domain/$domainName` |
| `DescribeDomains` | `httpdns:DescribeDomains` | `acs:httpdns:*:$accountid:domain/*` |
| `ListDomains` | `httpdns:ListDomains` | `acs:httpdns:*:$accountid:domain/*` |
| `GetResolveStatistics` | `httpdns:GetResolveStatistics` | `acs:httpdns:*:$accountid:domain/$domainName` |
| `GetResolveCountSummary` | `httpdns:GetResolveCountSummary` | `acs:httpdns:*:$accountid:*` |
| `RefreshResolveCache` | `httpdns:RefreshResolveCache` | `acs:httpdns:*:$accountid:domain/*` |

## Policy template

Scope resources down to specific account IDs and domains whenever possible.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "httpdns:GetAccountInfo",
        "httpdns:DescribeDomains",
        "httpdns:ListDomains",
        "httpdns:GetResolveCountSummary"
      ],
      "Resource": "acs:httpdns:*:<account-id>:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "httpdns:AddDomain",
        "httpdns:DeleteDomain",
        "httpdns:GetResolveStatistics",
        "httpdns:RefreshResolveCache"
      ],
      "Resource": "acs:httpdns:*:<account-id>:domain/*"
    }
  ]
}
```

For read-only usage analysis, remove `AddDomain`, `DeleteDomain`, and
`RefreshResolveCache`.

