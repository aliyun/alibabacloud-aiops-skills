# RAM Permissions

The skill is read-only. It only queries ECS, VPC, CBN, VPC Peering, NAT Gateway,
VPN Gateway, and Express Connect metadata through Alibaba Cloud APIs.

## Required Read-Only Permissions

Use a custom RAM policy that allows these actions:

- `ecs:DescribeInstances`
- `ecs:DescribeNetworkInterfaces`
- `ecs:DescribeSecurityGroups`
- `ecs:DescribeSecurityGroupAttribute`
- `vpc:DescribeVpcs`
- `vpc:DescribeVSwitches`
- `vpc:DescribeRouteTableList`
- `vpc:DescribeRouteEntryList`
- `vpc:DescribeNetworkAcls`
- `vpc:DescribeNatGateways`
- `vpc:DescribeForwardTableEntries`
- `vpc:DescribeSnatTableEntries`
- `vpc:DescribeVpnGateways`
- `vpc:DescribeVpnConnections`
- `vpc:DescribeVirtualBorderRouters`
- `cbn:DescribeCens`
- `cbn:DescribeCenAttachedChildInstances`
- `cbn:DescribeCenChildInstanceRouteEntries`
- `cbn:DescribeCenRegionDomainRouteEntries`
- `cbn:DescribeCenRouteMaps`
- `cbn:ListTransitRouters`
- `cbn:ListTransitRouterRouteTables`
- `cbn:ListTransitRouterRouteEntries`
- `cbn:ListTransitRouterRouteTableAssociations`
- `cbn:ListTransitRouterRouteTablePropagations`
- `cbn:ListTransitRouterVpcAttachments`
- `cbn:DescribeTransitRouterVpcAttachment`
- `vpcpeer:ListVpcPeerConnections`

## Permission Error Handling

When one product permission is missing, keep all other checks running:

- ECS permission missing: skip instance, ENI, and security group details.
- VPC permission missing: skip route table, VSwitch, ACL, and NAT details.
- CBN permission missing: skip CEN and Transit Router checks.
- VPN permission missing: keep route checks and report that VPN Gateway status
  could not be verified.

Always include the failed API action in the final report so the user can update
the RAM policy.
