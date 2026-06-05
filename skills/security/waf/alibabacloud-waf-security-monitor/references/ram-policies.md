# RAM Permission Policies

## Minimum Permission List

### WAF 3.0 (waf-openapi)

Read-only WAF OpenAPI permissions required by this skill:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf-openapi:DescribeInstance",
        "waf-openapi:DescribeDomains",
        "waf-openapi:DescribeCloudResourceList",
        "waf-openapi:DescribeCerts",
        "waf-openapi:DescribeDefenseTemplates",
        "waf-openapi:DescribeDefenseRuleStatistics",
        "waf-openapi:DescribeApisecEvents",
        "waf-openapi:DescribeFlowChart",
        "waf-openapi:DescribePeakTrend",
        "waf-openapi:DescribeAlarmList",
        "waf-openapi:DescribePauseProtectionStatus",
        "waf-openapi:DescribeDDoSStatus",
        "waf-openapi:DescribeMajorProtectionBlackIps",
        "waf-openapi:DescribeFlowTopResource",
        "waf-openapi:DescribeFlowTopUrl",
        "waf-openapi:DescribeResponseCodeTrendGraph"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Read-Only Permission Note

All permissions above are **read-only**, supporting only query (Describe/List) operations. No create, modify, or delete operations are included.

## Permission Categories

| Category | API Actions | Operation Type |
|----------|------------|----------------|
| Asset Management | DescribeInstance, DescribeDomains, DescribeCloudResourceList | Read-only |
| Defense Templates | DescribeDefenseTemplates | Read-only |
| Attack Events | DescribeDefenseRuleStatistics, DescribeApisecEvents | Read-only |
| Traffic Analysis | DescribeFlowChart, DescribePeakTrend | Read-only |
| Protection Status | DescribeAlarmList, DescribePauseProtectionStatus, DescribeDDoSStatus | Read-only |
| Certificate | DescribeCerts | Read-only |
| Major Protection | DescribeMajorProtectionBlackIps | Read-only |
| Top Analysis | DescribeFlowTopResource, DescribeFlowTopUrl | Read-only |
| Status Codes | DescribeResponseCodeTrendGraph | Read-only |
