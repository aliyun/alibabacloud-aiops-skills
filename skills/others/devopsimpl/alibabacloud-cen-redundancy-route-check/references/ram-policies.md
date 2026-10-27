# Minimum Read-Only RAM Permissions

The RAM code for CEN is `cen`, while its OpenAPI product code is `cbn`; the two differ. For VPC, both the RAM code and the product code are `vpc`.

## Action List

| Service | RAM Action | Purpose |
|---|---|---|
| CEN | `cen:DescribeCens` | Query CEN instances |
| CEN | `cen:DescribeCenAttachedChildInstances` | Query attached network instances |
| CEN | `cen:ListTransitRouters` | Query TRs |
| CEN | `cen:ListTransitRouterPeerAttachments` | Query cross-region connections |
| CEN | `cen:ListTransitRouterVpcAttachments` | Query VPC connections |
| CEN | `cen:ListTransitRouterVbrAttachments` | Query VBR connections |
| CEN | `cen:ListTransitRouterVpnAttachments` | Query VPN connections |
| CEN | `cen:ListTransitRouterRouteTables` | Query TR route tables |
| CEN | `cen:ListTransitRouterRouteEntries` | Query TR route entries |
| CEN | `cen:DescribeCenRegionDomainRouteEntries` | Query CEN 1.0 regional routes |
| CEN | `cen:DescribeCenRouteMaps` | Query route maps |
| CEN | `cen:DescribeRouteConflict` | Query conflicting routes of network instances |
| VPC | `vpc:DescribeRouteTableList` | Query VPC route tables |
| VPC | `vpc:DescribeRouteEntryList` | Query VPC route entries |

## Custom Policy Example

Resource-level authorization varies by Action. The example below uses `Resource: "*"`; administrators should narrow it further according to the official RAM permission documentation.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cen:DescribeCens",
        "cen:DescribeCenAttachedChildInstances",
        "cen:ListTransitRouters",
        "cen:ListTransitRouterPeerAttachments",
        "cen:ListTransitRouterVpcAttachments",
        "cen:ListTransitRouterVbrAttachments",
        "cen:ListTransitRouterVpnAttachments",
        "cen:ListTransitRouterRouteTables",
        "cen:ListTransitRouterRouteEntries",
        "cen:DescribeCenRegionDomainRouteEntries",
        "cen:DescribeCenRouteMaps",
        "cen:DescribeRouteConflict"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeRouteTableList",
        "vpc:DescribeRouteEntryList"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

1. Keep the error code, RequestId, product, Action, and region; never record credentials.
2. Mark affected resources as "Unable to confirm" and withhold any overall healthy verdict.
3. Request the missing Actions based on this file; resume from the failed step after authorization is granted.

## Official References

- [CEN RAM permissions](https://www.alibabacloud.com/help/en/cen/developer-reference/api-cbn-2017-09-12-ram)
- [VPC RAM permissions](https://www.alibabacloud.com/help/en/vpc/developer-reference/api-vpc-2016-04-28-ram)
