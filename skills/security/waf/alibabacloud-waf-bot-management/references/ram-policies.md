# RAM Policies for WAF Bot Management

## Overview

This document describes the RAM (Resource Access Management) permissions required to use the WAF Bot management skill for assessment, configuration, and verification operations.

## Recommended System Policies

### Read-Only Access (Assessment Only)

For Step 1 (Current State Assessment) and Step 4 (Verification), attach the following system policy:

- **AliyunWAFReadOnlyAccess**: Grants read-only access to WAF resources, including instance queries, defense template queries, rule queries, and log status queries.

### Read-Write Access (Full Workflow)

For the complete workflow including Step 3 (CLI Auto-Configuration) and Step 5 (Tuning), attach:

- **AliyunWAFReadWriteAccess**: Grants full read-write access to WAF resources, including creating/modifying defense templates, rules, and address books.

## Custom Policy: Least-Privilege for Bot Management

If you prefer least-privilege access, create a custom policy with the following permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:DescribeInstance",
        "waf:DescribeDefenseTemplates",
        "waf:DescribeBotRuleLabels",
        "waf:DescribeUserWafLogStatus",
        "waf:DescribeDefenseResources",
        "waf:DescribeDomains",
        "waf:DescribeAddresses",
        "waf:DescribeDefenseRules",
        "waf:DescribeRuleHitsTopRuleId",
        "waf:DescribeRuleHitsTopClientIp",
        "waf:DescribeSecurityEventTimeSeriesMetric",
        "waf:DescribeFlowTopUrl",
        "waf:DescribeRuleHitsTopUa"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "waf:CreateDefenseTemplate",
        "waf:CreateDefenseRule",
        "waf:CreateDefenseResource",
        "waf:AddAddress",
        "waf:ModifyTemplateResources",
        "waf:ModifyDefenseTemplateStatus",
        "waf:ModifyDefenseRule",
        "waf:ModifyDefenseRuleStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

## SLS Permissions (Optional)

For deep log analysis in Step 4, additional SLS (Simple Log Service) permissions may be required:

- **AliyunLogReadOnlyAccess**: Grants read-only access to SLS projects and logstores.

## How to Attach Policies

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Users** → Select the target user
3. Click **Add Permissions**
4. Search for and select the appropriate system or custom policy
5. Click **OK** to confirm

## Troubleshooting

| Error Code | Cause | Solution |
|------------|-------|----------|
| Forbidden.RAM | Insufficient permissions | Attach AliyunWAFReadWriteAccess or the custom policy above |
| InvalidAccessKeyId | Invalid credentials | Run `aliyun configure` to refresh credentials |
| NoPermission | Missing specific API permission | Check if the custom policy covers the required action |
