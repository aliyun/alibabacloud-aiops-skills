# Required RAM Permissions

This skill requires read-only access to Alibaba Cloud WAF 3.0 and Simple Log Service. Use a dedicated RAM identity and the narrowest resource scope supported by the customer's environment. The wildcard resource examples below are a compatibility fallback, not a recommendation to grant broader access than necessary.

## Required WAF actions

| Action | Purpose |
| --- | --- |
| `waf:DescribeInstance` | Read WAF instance information |
| `waf:DescribeDomains` | List protected domains |
| `waf:DescribeDefenseTemplates` | List defense templates |
| `waf:DescribeDefenseRules` | List defense rules by type |
| `waf:DescribeDefenseRule` | Read one defense rule |
| `waf:DescribeApiSecEvents` | List API Security events |
| `waf:DescribeApiSecAbnormals` | List API Security risks |
| `waf:DescribeApiSecMatchedHosts` | List API Security protected hosts |
| `waf:DescribeApiSecRules` | List API Security rules |
| `waf:DescribeApiSecAbnormalDomainStatistic` | Read domain-level API Security statistics |
| `waf:DescribeApiSecEventDetail` | Read one API Security event |

## Required SLS actions

| Action | Purpose |
| --- | --- |
| `log:GetLogs` | Query WAF traffic logs |
| `log:ListProject` | Discover accessible SLS projects |
| `log:ListLogStores` | Discover logstores in a project |

## Read-only policy example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:DescribeInstance",
        "waf:DescribeDomains",
        "waf:DescribeDefenseTemplates",
        "waf:DescribeDefenseRules",
        "waf:DescribeDefenseRule",
        "waf:DescribeApiSecEvents",
        "waf:DescribeApiSecAbnormals",
        "waf:DescribeApiSecMatchedHosts",
        "waf:DescribeApiSecRules",
        "waf:DescribeApiSecAbnormalDomainStatistic",
        "waf:DescribeApiSecEventDetail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogs",
        "log:ListProject",
        "log:ListLogStores"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission handling

- Use an existing managed identity or authenticated CLI context. Never request, inspect, print, persist, transform, or pass cloud credentials.
- Do not request write, update, delete, or policy-management actions for report generation.
- When an action is denied, report the exact denied action, continue only with unaffected evidence, and mark dependent checks as unverifiable.
- Ask the customer's cloud administrator to narrow `Resource` values when the service and account support resource-level authorization for the required action.
