# RAM Policy Configuration

This document describes the minimum read-only RAM permissions required by `alibabacloud-cloudfw-vpc-firewall-diagnosis`.

The skill is a read-only diagnostic tool. It must not require create, modify, delete, or wildcard write permissions.

## Minimum Read-only Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudfw:DescribeTrFirewallsV2List",
        "cloudfw:DescribeVpcFirewallList",
        "cloudfw:DescribeVpcFirewallPrecheckDetail",
        "cloudfw:DescribeFirewallTask",
        "cloudfw:DescribeTrFirewallPolicyBackUpAssociationList",
        "cloudfw:DescribeVpcFirewallControlPolicy",
        "actiontrail:LookupEvents",
        "cbn:ListTransitRouters",
        "cbn:ListTransitRouterRouteTables",
        "cbn:ListTransitRouterRouteEntries",
        "cbn:ListTransitRouterVpcAttachments",
        "cbn:ListTransitRouterVpnAttachments",
        "cbn:DescribeCenRouteMaps",
        "vpc:DescribeVpcs",
        "vpc:DescribeVpcAttribute",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Purpose

| Action | Purpose | Scenario |
|---|---|---|
| `cloudfw:DescribeTrFirewallsV2List` | Query VPC firewall list and key status fields. | Creation failure diagnosis. |
| `cloudfw:DescribeVpcFirewallList` | Query VPC boundary firewall information. | Supplementary creation status check. |
| `cloudfw:DescribeVpcFirewallPrecheckDetail` | Query precheck details. The CLI uses `--Region`. | Creation failure diagnosis. |
| `cloudfw:DescribeFirewallTask` | Query route policy task status and `ErrorDetail`. | Route policy configuration failure. |
| `cloudfw:DescribeTrFirewallPolicyBackUpAssociationList` | Query rollback target route table. | Auto-drainage closure pre-check. |
| `cloudfw:DescribeVpcFirewallControlPolicy` | Query VPC firewall ACL policies. | Closure pre-check ACL risk review. |
| `actiontrail:LookupEvents` | Query operation history. | Failure timeline and evidence correlation. |
| `cbn:ListTransitRouters` | Query transit routers. | Transit router discovery. |
| `cbn:ListTransitRouterRouteTables` | Query transit router route tables. | Route table identification. |
| `cbn:ListTransitRouterRouteEntries` | Query route entries. | Route conflict and closure pre-check. |
| `cbn:ListTransitRouterVpcAttachments` | Query VPC attachments. | ECMP and scope diagnosis. |
| `cbn:DescribeCenRouteMaps` | Query CEN route maps. | Silent rollback or route map consistency diagnosis. |
| `vpc:DescribeVpcs` / `vpc:DescribeVpcAttribute` | Query VPC attributes. | Resource context validation. |
| `sts:GetCallerIdentity` | Validate the current profile identity. | Environment validation. |

## Explicitly Excluded Permissions

Do not grant actions matching these write patterns:

- `cloudfw:Create*`, `cloudfw:Modify*`, `cloudfw:Delete*`
- `cbn:Create*`, `cbn:Modify*`, `cbn:Delete*`, `cbn:Attach*`, `cbn:Detach*`
- `vpc:Create*`, `vpc:Modify*`, `vpc:Delete*`
- Any product-level wildcard write permission such as `cloudfw:*`, `cbn:*`, or `*:*`

## CLI Mapping

CLI examples in this skill use lowercase-hyphenated plugin actions, for example:

```bash
aliyun sts get-caller-identity \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --RegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```
