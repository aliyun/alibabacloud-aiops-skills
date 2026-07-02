# RAM Policies

Complete list of all RAM permissions required by this skill. It is recommended to attach a policy containing the following Actions to the RAM user executing this skill.

## Minimum Policy (Export/Backup Only)

Read-only permissions, safe to grant to audit/inspection roles.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddoscoo:DescribeInstances",
        "yundun-ddoscoo:DescribeInstanceSpecs",
        "yundun-ddoscoo:DescribeInstanceStatistics",
        "yundun-ddoscoo:DescribeDomains",
        "yundun-ddoscoo:DescribeDomainResource",
        "yundun-ddoscoo:DescribeWebRules",
        "yundun-ddoscoo:DescribeL7RsPolicy",
        "yundun-ddoscoo:DescribeL7UsKeepalive",
        "yundun-ddoscoo:DescribeHeaders",
        "yundun-ddoscoo:DescribeCnameReuses",
        "yundun-ddoscoo:DescribeWebCCProtectSwitch",
        "yundun-ddoscoo:DescribeDomainCcProtectSwitch",
        "yundun-ddoscoo:DescribeWebCCRulesV2",
        "yundun-ddoscoo:DescribeWebCCRules",
        "yundun-ddoscoo:DescribeWebPreciseAccessRule",
        "yundun-ddoscoo:DescribeWebAreaBlockConfigs",
        "yundun-ddoscoo:DescribeWebCacheConfigs",
        "yundun-ddoscoo:DescribeCdnLinkageRules",
        "yundun-ddoscoo:DescribeSchedulerRules",
        "yundun-ddoscoo:DescribeDomainSecurityProfile",
        "yundun-ddoscoo:DescribeL7GlobalRule",
        "yundun-ddoscoo:DescribeL7CCCookie",
        "yundun-ddoscoo:DescribeL7MutualAuthConf",
        "yundun-ddoscoo:DescribeGmCertList",
        "yundun-ddoscoo:DescribeCerts"
      ],
      "Resource": "*"
    }
  ]
}
```

## Full Policy (Export + Import)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddoscoo:DescribeInstances",
        "yundun-ddoscoo:DescribeInstanceSpecs",
        "yundun-ddoscoo:DescribeInstanceStatistics",
        "yundun-ddoscoo:DescribeDomains",
        "yundun-ddoscoo:DescribeDomainResource",
        "yundun-ddoscoo:DescribeWebRules",
        "yundun-ddoscoo:DescribeL7RsPolicy",
        "yundun-ddoscoo:DescribeL7UsKeepalive",
        "yundun-ddoscoo:DescribeHeaders",
        "yundun-ddoscoo:DescribeCnameReuses",
        "yundun-ddoscoo:DescribeWebCCProtectSwitch",
        "yundun-ddoscoo:DescribeDomainCcProtectSwitch",
        "yundun-ddoscoo:DescribeWebCCRulesV2",
        "yundun-ddoscoo:DescribeWebCCRules",
        "yundun-ddoscoo:DescribeWebPreciseAccessRule",
        "yundun-ddoscoo:DescribeWebAreaBlockConfigs",
        "yundun-ddoscoo:DescribeWebCacheConfigs",
        "yundun-ddoscoo:DescribeCdnLinkageRules",
        "yundun-ddoscoo:DescribeSchedulerRules",
        "yundun-ddoscoo:DescribeDomainSecurityProfile",
        "yundun-ddoscoo:DescribeL7GlobalRule",
        "yundun-ddoscoo:DescribeL7CCCookie",
        "yundun-ddoscoo:DescribeL7MutualAuthConf",
        "yundun-ddoscoo:DescribeGmCertList",
        "yundun-ddoscoo:DescribeCerts",
        "yundun-ddoscoo:CreateDomainResource",
        "yundun-ddoscoo:ModifyWebRule",
        "yundun-ddoscoo:AssociateWebCert",
        "yundun-ddoscoo:ModifyOcspStatus",
        "yundun-ddoscoo:ModifyTlsConfig",
        "yundun-ddoscoo:ConfigL7RsPolicy",
        "yundun-ddoscoo:ConfigL7UsKeepalive",
        "yundun-ddoscoo:ModifyHeaders",
        "yundun-ddoscoo:ModifyCnameReuse",
        "yundun-ddoscoo:EnableWebCC",
        "yundun-ddoscoo:DisableWebCC",
        "yundun-ddoscoo:EnableWebCCRule",
        "yundun-ddoscoo:DisableWebCCRule",
        "yundun-ddoscoo:ModifyWebCCGlobalSwitch",
        "yundun-ddoscoo:ConfigWebCCTemplate",
        "yundun-ddoscoo:ConfigWebCCRuleV2",
        "yundun-ddoscoo:ModifyWebAIProtectMode",
        "yundun-ddoscoo:ModifyWebAIProtectSwitch",
        "yundun-ddoscoo:ModifyWebPreciseAccessRule",
        "yundun-ddoscoo:ModifyWebPreciseAccessSwitch",
        "yundun-ddoscoo:ModifyWebAreaBlock",
        "yundun-ddoscoo:ModifyWebAreaBlockSwitch",
        "yundun-ddoscoo:ConfigWebIpSet",
        "yundun-ddoscoo:ModifyWebIpSetSwitch",
        "yundun-ddoscoo:ModifyWebCacheSwitch",
        "yundun-ddoscoo:ModifyWebCacheMode",
        "yundun-ddoscoo:ModifyWebCacheCustomRule",
        "yundun-ddoscoo:CreateSchedulerRule",
        "yundun-ddoscoo:ModifySchedulerRule",
        "yundun-ddoscoo:ConfigDomainSecurityProfile",
        "yundun-ddoscoo:ConfigL7GlobalRule",
        "yundun-ddoscoo:ConfigL7CCCookieEnable",
        "yundun-ddoscoo:ConfigL7MutualAuthentication",
        "yundun-ddoscoo:ConfigGmCert",
        "yundun-ddoscoo:ConfigGmCertEnable",
        "yundun-ddoscoo:ConfigGmCertOnly"
      ],
      "Resource": "*"
    }
  ]
}
```

## Resource Group Restriction

If you use resource groups to isolate production/testing environments, you can restrict the `Resource` field:

```json
"Resource": "acs:ram:*:*:resourcegroup/<RESOURCE_GROUP_ID>"
```
