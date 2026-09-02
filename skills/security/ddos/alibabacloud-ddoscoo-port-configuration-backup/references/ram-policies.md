# Least-Privilege RAM Policies

Every Action uses the `yundun-ddoscoo:` prefix. Narrow the resource scope
further when the account policy permits it. A permission failure means unknown
state and must never be converted to an empty value or followed by a write.

## Export read permissions

~~~json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddoscoo:DescribeInstances",
        "yundun-ddoscoo:DescribeInstanceDetails",
        "yundun-ddoscoo:DescribeInstanceSpecs",
        "yundun-ddoscoo:DescribeInstanceStatistics",
        "yundun-ddoscoo:DescribeNetworkRules",
        "yundun-ddoscoo:DescribeHealthCheckList",
        "yundun-ddoscoo:DescribeNetworkRuleAttributes",
        "yundun-ddoscoo:DescribeLayer4RulePolicy",
        "yundun-ddoscoo:DescribeLayer4Rules",
        "yundun-ddoscoo:DescribePortProxyEnable",
        "yundun-ddoscoo:DescribePortPayloadRuleList",
        "yundun-ddoscoo:DescribeL4ProxyWhiteList",
        "yundun-ddoscoo:DescribeLayer4SwitchAndDefense",
        "yundun-ddoscoo:DescribePortAutoCcStatus"
      ],
      "Resource": "*"
    }
  ]
}
~~~

## Additional import write permissions

~~~json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddoscoo:CreatePort",
        "yundun-ddoscoo:ModifyPort",
        "yundun-ddoscoo:DeletePort",
        "yundun-ddoscoo:ConfigLayer4Remark",
        "yundun-ddoscoo:ModifyHealthCheckConfig",
        "yundun-ddoscoo:ModifyNetworkRuleAttribute",
        "yundun-ddoscoo:ConfigLayer4Rule",
        "yundun-ddoscoo:ConfigLayer4RuleBakMode",
        "yundun-ddoscoo:ConfigLayer4RulePolicy",
        "yundun-ddoscoo:ConfigPortPayloadRule",
        "yundun-ddoscoo:DeletePortPayloadRule",
        "yundun-ddoscoo:ConfigPortPayloadModuleEnable",
        "yundun-ddoscoo:ConfigL4ProxyWhiteList",
        "yundun-ddoscoo:DeleteL4ProxyWhiteList",
        "yundun-ddoscoo:ConfigLayer4SwitchAndDefense",
        "yundun-ddoscoo:ModifyPortAutoCcStatus"
      ],
      "Resource": "*"
    }
  ]
}
~~~

Revoke temporary write permissions after import. Before deleting a port or a
manual Payload rule, freshly prove the exact manual ownership. Do not grant or
use website, scenario-specific protection, or Protection for Infrastructure
write permissions.
