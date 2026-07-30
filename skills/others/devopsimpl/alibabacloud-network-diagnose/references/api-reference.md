# API Reference

This skill uses read-only Alibaba Cloud APIs through aliyun CLI plugin mode.
Runtime commands are built by `scripts/net_common.py`, which converts API action
names to lowercase hyphenated plugin-mode commands and applies timeout and
user-agent options.

## ECS

- `DescribeInstances`: query ECS instance state, VPC ID, VSwitch ID, private IPs,
  security groups, and zone.
- `DescribeNetworkInterfaces`: query ENIs and private IP sets.
- `DescribeSecurityGroups`: query security group type. Enterprise security
  groups are stateless and do not have default outbound allow.
- `DescribeSecurityGroupAttribute`: query ingress and egress security group
  rules.

## VPC

- `DescribeVpcs`: query VPC metadata.
- `DescribeVSwitches`: query VSwitch metadata and route table association.
- `DescribeRouteTableList`: list route tables for a VPC.
- `DescribeRouteEntryList`: list routes in a route table.
- `DescribeNetworkAcls`: query network ACLs and bound VSwitches.
- `DescribeNatGateways`: query NAT Gateway status and table IDs.
- `DescribeForwardTableEntries`: query DNAT rules.
- `DescribeSnatTableEntries`: query SNAT rules.
- `DescribeVpnGateways`: query VPN Gateway status.
- `DescribeVpnConnections`: query IPsec connection tunnel status.
- `DescribeVirtualBorderRouters`: query Express Connect VBR status.

## CBN and Transit Router

- `DescribeCens`: list CEN instances.
- `DescribeCenAttachedChildInstances`: list CEN child network instances.
- `DescribeCenChildInstanceRouteEntries`: query child-instance route entries.
- `DescribeCenRegionDomainRouteEntries`: query regional CEN route entries.
- `DescribeCenRouteMaps`: query CEN route map policies.
- `ListTransitRouters`: list Transit Routers.
- `ListTransitRouterRouteTables`: list TR route tables.
- `ListTransitRouterRouteEntries`: list TR routes.
- `ListTransitRouterRouteTableAssociations`: query association forwarding.
- `ListTransitRouterRouteTablePropagations`: query route propagation.
- `ListTransitRouterVpcAttachments`: query VPC attachments and zone mappings.
- `DescribeTransitRouterVpcAttachment`: query one VPC attachment.

## VPC Peering

- `ListVpcPeerConnections`: query VPC peering connection status.

## Required CLI Options

Every CLI call must include:

```text
--read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

The session id is generated once per diagnosis session and reused for all cloud
interactions in that session.
