# ActionTrail ServiceName Mapping for Network Products

> **Loading strategy**: The complete ServiceName mapping tables live in this file; the References section of SKILL.md points here and does not inline any mapping table itself. Consult this file whenever you must translate a user-facing product name into the exact ActionTrail ServiceName value before building a `--lookup-attribute ServiceName=...` filter.

## Network Products Sharing the `Vpc` Event Source (Key Point)

Audit events of the following products are all attributed to the `Vpc` ServiceName. Distinguish them by **event name prefix** or **resource type**. The complete per-product event list is held by the `network-events-catalog.md` reference, which SKILL.md loads directly.

| Product | ServiceName | Common Event Name Prefixes / Keywords | Resource Type |
|---------|-------------|---------------------------------------|---------------|
| VPC / Virtual Private Cloud | Vpc | CreateVpc, DeleteVpc, ModifyVpcAttribute, DescribeVpcs, AssociateVpcCidrBlock, UnassociateVpcCidrBlock, EnableVpcClassicLink, DisableVpcClassicLink | ACS::VPC::VPC |
| VSwitch | Vpc | CreateVSwitch, DeleteVSwitch, ModifyVSwitchAttribute, DescribeVSwitches | ACS::VPC::VSwitch |
| EIP / Elastic IP Address | Vpc | AllocateEipAddress, AllocateEipAddressPro, AllocateEipSegmentAddress, ReleaseEipAddress, AssociateEipAddress, UnassociateEipAddress, ModifyEipAddressAttribute, ModifyEipForwardMode, DescribeEipAddresses | ACS::VPC::EIPAddress |
| NAT Gateway | Vpc | CreateNatGateway, DeleteNatGateway, ModifyNatGatewayAttribute, ModifyNatGatewaySpec, UpdateNatGatewayNatType, DescribeNatGateways, GetNatGatewayAttribute | ACS::VPC::NatGateway |
| NAT - SNAT Entry | Vpc | CreateSnatEntry, DeleteSnatEntry, ModifySnatEntry, DescribeSnatTableEntries | ACS::VPC::SnatEntry |
| NAT - DNAT/Forward Entry | Vpc | CreateForwardEntry, DeleteForwardEntry, ModifyForwardEntry, DescribeForwardTableEntries | ACS::VPC::ForwardEntry |
| NAT - FullNAT Entry | Vpc | CreateFullNatEntry, DeleteFullNatEntry, ModifyFullNatEntryAttribute, ListFullNatEntries | ACS::VPC::FullNatEntry |
| NAT - NAT IP/CIDR | Vpc | CreateNatIp, DeleteNatIp, ModifyNatIpAttribute, CreateNatIpCidr, DeleteNatIpCidr | ACS::VPC::NatIp |
| NAT Bandwidth Package | Vpc | CreateBandwidthPackage, DeleteBandwidthPackage, AddBandwidthPackageIps, RemoveBandwidthPackageIps, ConvertBandwidthPackage | ACS::VPC::BandwidthPackage |
| VPN Gateway | Vpc | CreateVpnGateway, DeleteVpnGateway, ModifyVpnGatewayAttribute, DescribeVpnGateways, UpgradeVpnGatewayFirmware, DiagnoseVpnGateway | ACS::VPC::VpnGateway |
| VPN Connection | Vpc | CreateVpnConnection, DeleteVpnConnection, ModifyVpnConnectionAttribute, DownloadVpnConnectionConfig, DescribeVpnConnections | ACS::VPC::VpnConnection |
| VPN Route | Vpc | CreateVpnRouteEntry, DeleteVpnRouteEntry, ModifyVpnRouteEntryWeight, PublishVpnRouteEntry, CreateVpnPbrRouteEntry | ACS::VPC::VpnRouteEntry |
| SSL-VPN | Vpc | CreateSslVpnServer, DeleteSslVpnServer, ModifySslVpnServer, CreateSslVpnClientCert, DeleteSslVpnClientCert | ACS::VPC::SslVpnServer |
| Customer Gateway | Vpc | CreateCustomerGateway, DeleteCustomerGateway, ModifyCustomerGatewayAttribute, DescribeCustomerGateways | ACS::VPC::CustomerGateway |
| IPsec Server | Vpc | CreateIpsecServer, DeleteIpsecServer, UpdateIpsecServer, ListIpsecServers | ACS::VPC::IpsecServer |
| VPN Attachment / GRE | Vpc | CreateVpnAttachment, DeleteVpnAttachment, CreateVpnGreTunnel, DescribeVpnGreTunnels | ACS::VPC::VpnAttachment |
| Common Bandwidth | Vpc | CreateCommonBandwidthPackage, DeleteCommonBandwidthPackage, AddCommonBandwidthPackageIp, RemoveCommonBandwidthPackageIp, ModifyCommonBandwidthPackageAttribute, ModifyCommonBandwidthPackageSpec | ACS::VPC::CommonBandwidthPackage |
| Express Connect - Physical Connection | Vpc | CreatePhysicalConnection, DeletePhysicalConnection, ModifyPhysicalConnectionAttribute, EnablePhysicalConnection, CancelPhysicalConnection, ConfirmPhysicalConnection, TerminatePhysicalConnection | ACS::VPC::PhysicalConnection |
| Express Connect - Virtual Border Router (VBR) | Vpc | CreateVirtualBorderRouter, DeleteVirtualBorderRouter, ModifyVirtualBorderRouterAttribute, TerminateVirtualBorderRouter, RecoverVirtualBorderRouter | ACS::VPC::VBR |
| Express Connect - Router Interface | Vpc | CreateRouterInterface, DeleteRouterInterface, ModifyRouterInterfaceAttribute, ModifyRouterInterfaceSpec, ActivateRouterInterface, DeactivateRouterInterface, ConnectRouterInterface | ACS::VPC::RouterInterface |
| Express Connect - BGP | Vpc | CreateBgpGroup, DeleteBgpGroup, ModifyBgpGroupAttribute, CreateBgpPeer, DeleteBgpPeer, AddBgpNetwork, DeleteBgpNetwork | ACS::VPC::BgpGroup |
| Express Connect - ECC | Vpc | CreateExpressCloudConnection, DeleteExpressCloudConnection, ModifyExpressCloudConnectionAttribute, ModifyExpressCloudConnectionBandwidth | ACS::VPC::ExpressCloudConnection |
| Route Table | Vpc | CreateRouteTable, DeleteRouteTable, ModifyRouteTableAttributes, AssociateRouteTable, UnassociateRouteTable, AssociateRouteTableWithGateway, DissociateRouteTableFromGateway | ACS::VPC::RouteTable |
| Route Entry | Vpc | CreateRouteEntry, DeleteRouteEntry, ModifyRouteEntry, DescribeRouteEntryList | ACS::VPC::RouteEntry |
| Network ACL | Vpc | CreateNetworkAcl, DeleteNetworkAcl, ModifyNetworkAclAttributes, AssociateNetworkAcl, UnassociateNetworkAcl, CopyNetworkAclEntries, UpdateNetworkAclEntries | ACS::VPC::NetworkAcl |
| DHCP Options Set | Vpc | CreateDhcpOptionsSet, DeleteDhcpOptionsSet, UpdateDhcpOptionsSetAttribute, AttachDhcpOptionsSetToVpc, DetachDhcpOptionsSetFromVpc, ReplaceVpcDhcpOptionsSet | ACS::VPC::DhcpOptionsSet |
| Flow Log | Vpc | CreateFlowLog, DeleteFlowLog, ActiveFlowLog, DeactiveFlowLog, ModifyFlowLogAttribute, OpenFlowLogService | ACS::VPC::FlowLog |
| IPv4 Gateway | Vpc | CreateIpv4Gateway, DeleteIpv4Gateway, UpdateIpv4GatewayAttribute, EnableVpcIpv4Gateway, GetIpv4GatewayAttribute | ACS::VPC::Ipv4Gateway |
| IPv6 Gateway | Vpc | CreateIpv6Gateway, DeleteIpv6Gateway, ModifyIpv6GatewayAttribute, ModifyIpv6GatewaySpec, AllocateIpv6InternetBandwidth, DeleteIpv6InternetBandwidth, ModifyIpv6InternetBandwidth, CreateIpv6EgressOnlyRule, DeleteIpv6EgressOnlyRule | ACS::VPC::Ipv6Gateway |
| IPv6 Address | Vpc | AllocateVpcIpv6Cidr, DescribeIpv6Addresses, ModifyIpv6AddressAttribute | ACS::VPC::Ipv6Address |
| IPv6 Translation Service | Vpc | CreateIPv6Translator, DeleteIPv6Translator, ModifyIPv6TranslatorAttribute, ModifyIPv6TranslatorBandwidth, CreateIPv6TranslatorEntry, DeleteIPv6TranslatorEntry | ACS::VPC::Ipv6Translator |
| Traffic Mirroring | Vpc | CreateTrafficMirrorFilter, DeleteTrafficMirrorFilter, CreateTrafficMirrorFilterRules, CreateTrafficMirrorSession, DeleteTrafficMirrorSession, AddSourcesToTrafficMirrorSession, RemoveSourcesFromTrafficMirrorSession | ACS::VPC::TrafficMirrorSession |
| HaVip (High-Availability Virtual IP) | Vpc | CreateHaVip, DeleteHaVip, ModifyHaVipAttribute, AssociateHaVip, UnassociateHaVip, SetHaVipMasterInstance | ACS::VPC::HaVip |
| VPC Gateway Endpoint | Vpc | CreateVpcGatewayEndpoint, DeleteVpcGatewayEndpoint, UpdateVpcGatewayEndpointAttribute, AssociateRouteTablesWithVpcGatewayEndpoint, DissociateRouteTablesFromVpcGatewayEndpoint | ACS::VPC::VpcGatewayEndpoint |
| Prefix List | Vpc | CreateVpcPrefixList, DeleteVpcPrefixList, ModifyVpcPrefixList, GetVpcPrefixListEntries, RetryVpcPrefixListAssociation | ACS::VPC::PrefixList |
| Public IP Address Pool | Vpc | CreatePublicIpAddressPool, DeletePublicIpAddressPool, UpdatePublicIpAddressPoolAttribute, AddPublicIpAddressPoolCidrBlock, DeletePublicIpAddressPoolCidrBlock | ACS::VPC::PublicIpAddressPool |
| Global Acceleration (legacy GA) | Vpc | CreateGlobalAccelerationInstance, DeleteGlobalAccelerationInstance, ModifyGlobalAccelerationInstanceAttributes, AssociateGlobalAccelerationInstance, UnassociateGlobalAccelerationInstance | ACS::VPC::GlobalAcceleration |
| VPC Tags | Vpc | TagResources, UnTagResources, ListTagResources | - |
| Generic Orders | Vpc | Create, Modify, Release, Renew, RenewInstance, RemainRefund, DeletionProtection, ModifyInstanceAutoRenewalAttribute | - |

## Network Products with Dedicated ServiceName

| Product | ServiceName | Supported Since | Common Event Examples |
|---------|-------------|-----------------|------------------------|
| CLB / SLB / Classic Load Balancer | Slb | Before 2020 | CreateLoadBalancer, DeleteLoadBalancer, CreateLoadBalancerHTTPListener, DescribeHealthStatus, AddBackendServers, RemoveBackendServers, CreateRules |
| ALB / Application Load Balancer | ALB | 2021-08-24 | CreateLoadBalancer, CreateListener, CreateServerGroup, AddServersToServerGroup, CreateRule, UpdateListenerAttribute |
| NLB / Network Load Balancer | Nlb | 2022 | CreateLoadBalancer, CreateListener, CreateServerGroup, AddServersToServerGroup, UpdateNlbListenerAttribute |
| GWLB / Gateway Load Balancer | GWLB | 2024-09-20 | CreateLoadBalancer, CreateListener, CreateServerGroup |
| CEN / Cloud Enterprise Network | Cen | Before 2020 | All 160 events in network-events-catalog.md; common ones: CreateCen, DeleteCen, AttachCenChildInstance, DetachCenChildInstance, CreateTransitRouter, CreateTransitRouterVpcAttachment, CreateTransitRouterRouteTable, CreateTransitRouterRouteEntry |
| GA / Global Accelerator | Ga | 2021-03-16 | CreateAccelerator, DeleteAccelerator, CreateListener, CreateEndpointGroup, UpdateAcceleratorConfirm |
| Smart Access Gateway | Smartag | Before 2020 | All 188 events in network-events-catalog.md; common ones: CreateSmartAccessGateway, DeleteSmartAccessGateway, CreateCloudConnectNetwork, BindSmartAccessGateway, CreateACL, CreateQos |
| PrivateLink | Privatelink | Before 2020 | CreateVpcEndpoint, DeleteVpcEndpoint, CreateVpcEndpointService, AddZoneToVpcEndpoint, CreateVpcEndpointServiceResource |
| PrivateZone (Private DNS) | PrivateZone | 2021-01-13 | AddZone, DeleteZone, UpdateZoneRemark, AddZoneRecord, DeleteZoneRecord, BindZoneVpc |
| Anycast Elastic IP | Eipanycast | 2022-04-18 | AllocateAnycastEipAddress, ReleaseAnycastEipAddress, AssociateAnycastEipAddress, UnassociateAnycastEipAddress |
| VPC Peering | VpcPeer | 2023-01-08 | CreateVpcPeerConnection, DeleteVpcPeerConnection, AcceptVpcPeerConnection, RejectVpcPeerConnection, ModifyVpcPeerConnection, GetVpcPeerConnectionAttribute |
| CDT / Cloud Data Transfer | CDT | 2023-05-25 | OpenCdtService, CloseCdtService |
| Shared Flow Bag | flowbag | Before 2020 | CreateFlowBag, RefundFlowBag, DescribeFlowBags |
| CMN / Cloud Network Management | CMN | 2021-02-23 | - |

## Other Common Cloud Services

| Product | ServiceName |
|---------|-------------|
| ECS / Elastic Compute Service | Ecs |
| OSS / Object Storage Service | Oss |
| RDS Database | Rds |
| Redis | R-kvstore |
| RAM / Resource Access Management | Ram |
| Container Service | CS |
| Function Compute | FC |
| CDN | Cdn |
| WAF | waf-openapi |
| DDoS Protection (Anti-DDoS Pro) | ddoscoo |
| DDoS Native Protection | ddosbgp |
| Security Center | aegis |
| SLS / Log Service | SLS |
| Domains | Domain |
| Alibaba Cloud DNS | Alidns |
| API Gateway | CloudAPI |
| RocketMQ | Ons / RocketMQ |
| Short Message Service | Dysms |

## Smart Mapping Rules

When the product name provided by the user cannot be directly matched to a ServiceName, handle it by the following priority:

1. Exact match against the "Product" column in the tables above
2. Fuzzy match (e.g. user says "elastic IP" -> EIP -> Vpc)
3. If still undetermined, present the list of candidate ServiceName values to the user and ask for confirmation

## Event Filtering Best Practices

Because multiple network products share the `Vpc` ServiceName, a second-pass filter is required when querying:

1. **Prefer exact match on event name**: e.g. for EIP release events use `EventName=ReleaseEipAddress`
2. **Filter by event name prefix**: after fetching all Vpc events, filter by prefix (e.g. `Eip`, `Nat`, `Vpn`, `SnatEntry`, `ForwardEntry`) to isolate the target product
3. **Filter by resource name**: e.g. `ResourceName=eip-bp1234567890abcde` to pinpoint a specific resource
4. **Filter by resource type**: e.g. `ResourceType=ACS::VPC::NatGateway`

The complete event catalog is held by the `network-events-catalog.md` reference, which SKILL.md loads directly.
