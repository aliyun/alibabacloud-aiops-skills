# Related Aliyun CLI Commands

Every actual cloud API command execution MUST append the `--user-agent` flag defined in the SKILL.md Observability section and MUST complete all pagination.

| Stage | CLI Command | OpenAPI | Key Parameters |
|---|---|---|---|
| CEN instance | `aliyun cbn describe-cens` | `DescribeCens` | `--filter`, `--page-number`, `--page-size` |
| Attached instances | `aliyun cbn describe-cen-attached-child-instances` | `DescribeCenAttachedChildInstances` | `--cen-id`, `--page-number`, `--page-size` |
| TR | `aliyun cbn list-transit-routers` | `ListTransitRouters` | `--cen-id`, `--biz-region-id` |
| Cross-region connection | `aliyun cbn list-transit-router-peer-attachments` | `ListTransitRouterPeerAttachments` | `--cen-id`, `--transit-router-id`, `--next-token` |
| VPC connection | `aliyun cbn list-transit-router-vpc-attachments` | `ListTransitRouterVpcAttachments` | `--cen-id`, `--transit-router-id`, `--vpc-id` |
| VBR connection | `aliyun cbn list-transit-router-vbr-attachments` | `ListTransitRouterVbrAttachments` | `--cen-id`, `--transit-router-id` |
| VPN connection | `aliyun cbn list-transit-router-vpn-attachments` | `ListTransitRouterVpnAttachments` | `--cen-id`, `--transit-router-id` |
| TR route tables | `aliyun cbn list-transit-router-route-tables` | `ListTransitRouterRouteTables` | `--transit-router-id`, `--next-token` |
| TR route entries | `aliyun cbn list-transit-router-route-entries` | `ListTransitRouterRouteEntries` | `--transit-router-route-table-id`, `--transit-router-route-entry-status` |
| CEN 1.0 routes | `aliyun cbn describe-cen-region-domain-route-entries` | `DescribeCenRegionDomainRouteEntries` | `--cen-id`, `--cen-region-id`, `--status` |
| Route Map | `aliyun cbn describe-cen-route-maps` | `DescribeCenRouteMaps` | `--cen-id`, `--cen-region-id`, `--transmit-direction` |
| Conflicting routes | `aliyun cbn describe-route-conflict` | `DescribeRouteConflict` | Network instance, region, route table, type |
| VPC route tables | `aliyun vpc describe-route-table-list` | `DescribeRouteTableList` | `--biz-region-id`, `--vpc-id` |
| VPC route entries | `aliyun vpc describe-route-entry-list` | `DescribeRouteEntryList` | `--biz-region-id`, `--route-table-id`, `--destination-cidr-block` |

## Pagination Rules

- `PageNumber/PageSize`: start from page 1 and continue until a page returns fewer items than PageSize or the total count is covered.
- `NextToken/MaxResults`: omit NextToken on the first request; then pass the previously returned value until NextToken is empty.
- Deduplicate each page by stable resource ID.
- If any page fails, record the page, error code, and RequestId, and mark the related scope as "Unable to confirm".

## Command Discovery and Validation

```bash
aliyun cbn <command> --help
aliyun vpc <command> --help
```

Use only plugin-mode lowercase kebab-case commands; never rewrite them into the traditional `aliyun Cbn ApiName` format.
