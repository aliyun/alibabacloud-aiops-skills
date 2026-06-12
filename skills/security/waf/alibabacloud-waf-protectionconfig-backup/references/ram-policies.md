# RAM Policies

## Required Permissions

### WAF 3.0 (API 2021-10-01)

| Action | Description |
|--------|-------------|
| `waf:DescribeInstance` | Query WAF 3.0 instance info |
| `waf:DescribeDefenseResources` | List defense resources |
| `waf:DescribeDefenseResourceGroups` | List defense resource groups |
| `waf:DescribeDefenseTemplates` | List defense templates |
| `waf:DescribeDefenseRules` | List defense rules |
| `waf:DescribeTemplateResources` | List template-resource bindings |
| `waf:DescribeMajorProtectionBlackIps` | List major protection black IPs |
| `waf:DescribeAddresses` | List address book entries |

### WAF 2.0 (API 2019-09-10)

| Action | Description |
|--------|-------------|
| `waf:DescribeInstanceInfo` | Query WAF 2.0 instance info |
| `waf:DescribeDomainNames` | List domains in WAF 2.0 |
| `waf:DescribeProtectionModuleRules` | List protection module rules |
| `waf:DescribeProtectionModuleStatus` | Query protection module status |
| `waf:DescribeProtectionModuleMode` | Query protection module mode |
| `waf:DescribeDomainRuleGroup` | Query domain rule group |

---

## IAM Policy JSON (WAF 3.0 + WAF 2.0 Combined)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:DescribeInstance",
        "waf:DescribeDefenseResources",
        "waf:DescribeDefenseResourceGroups",
        "waf:DescribeDefenseTemplates",
        "waf:DescribeDefenseRules",
        "waf:DescribeTemplateResources",
        "waf:DescribeMajorProtectionBlackIps",
        "waf:DescribeAddresses",
        "waf:DescribeInstanceInfo",
        "waf:DescribeDomainNames",
        "waf:DescribeProtectionModuleRules",
        "waf:DescribeProtectionModuleStatus",
        "waf:DescribeProtectionModuleMode",
        "waf:DescribeDomainRuleGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

## WAF 3.0 Only Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:DescribeInstance",
        "waf:DescribeDefenseResources",
        "waf:DescribeDefenseResourceGroups",
        "waf:DescribeDefenseTemplates",
        "waf:DescribeDefenseRules",
        "waf:DescribeTemplateResources",
        "waf:DescribeMajorProtectionBlackIps",
        "waf:DescribeAddresses"
      ],
      "Resource": "*"
    }
  ]
}
```

## WAF 2.0 Only Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:DescribeInstanceInfo",
        "waf:DescribeDomainNames",
        "waf:DescribeProtectionModuleRules",
        "waf:DescribeProtectionModuleStatus",
        "waf:DescribeProtectionModuleMode",
        "waf:DescribeDomainRuleGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

> All permissions are read-only (Describe* actions). No write or modification permissions are required.
