# Full ActionTrail Event Catalog for Network Products

This document compiles the event names, operation types and meanings recorded by ActionTrail for major Alibaba Cloud network products. Query either by exact match via `AttributeKey=EventName, AttributeValue=<event name>`, or fetch by `ServiceName` first and then apply a second-pass filter by prefix / resource type.

> **Column legend**
> - **Type**: Read = read-only query events (Describe/Get/List/Query); Write = mutating events (Create/Delete/Modify/Update/Add/Remove/Associate/Attach/Enable/Disable/Publish, etc.). Management events (ActionTrail Management) are all recorded by default and retained for 90 days.
> - **Description**: operation meaning derived from API naming and Alibaba Cloud official documentation, used to quickly judge the nature of an event.
>
> Update note: this catalog is sourced from Alibaba Cloud official public documentation (`help.aliyun.com/zh/actiontrail`, `alibabacloud.com/help/*/actiontrail/product-overview/audit-events-of-*`). Events may be added/deprecated as products evolve; if you encounter an unlisted event, run a broad query without EventName first and then filter manually.

## Section Index

> **Usage tip**: this document is about 1000 lines / 48KB; loading the whole file costs about 12k tokens. When using the `Read` tool, prefer reading the target section precisely with `offset + limit` from the table below instead of loading the whole file. Examples: for NAT gateway events use `Read(file, offset=106, limit=39)`; for ALB events use `Read(file, offset=468, limit=48)`.

| Section | Line Range | Read Parameter Example |
|---------|------------|------------------------|
| 1. Vpc (ServiceName=Vpc) | 60-63 | offset=60, limit=4 |
| 1.1 VPC instance and vSwitch | 64-85 | offset=64, limit=22 |
| 1.2 EIP / Elastic IP Address | 86-105 | offset=86, limit=20 |
| 1.3 NAT Gateway | 106-144 | offset=106, limit=39 |
| 1.4 VPN Gateway | 145-191 | offset=145, limit=47 |
| 1.5 Common Bandwidth | 192-206 | offset=192, limit=15 |
| 1.6 Express Connect | 207-251 | offset=207, limit=45 |
| 1.7 Routing | 252-270 | offset=252, limit=19 |
| 1.8 Network ACL | 271-283 | offset=271, limit=13 |
| 1.9 DHCP Options Set | 284-295 | offset=284, limit=12 |
| 1.10 Flow Log | 296-307 | offset=296, limit=12 |
| 1.11 IPv4 / IPv6 Gateways and Addresses | 308-340 | offset=308, limit=33 |
| 1.12 Traffic Mirroring | 341-358 | offset=341, limit=18 |
| 1.13 HaVip / Gateway Endpoint / Prefix List / Public IP Address Pool | 359-390 | offset=359, limit=32 |
| 1.14 Tags and Orders | 391-409 | offset=391, limit=19 |
| 2. Slb (ServiceName=Slb, Classic Load Balancer CLB) | 410-467 | offset=410, limit=58 |
| 3. ALB (ServiceName=ALB, Application Load Balancer) | 468-515 | offset=468, limit=48 |
| 4. NLB (ServiceName=Nlb, Network Load Balancer) | 516-547 | offset=516, limit=32 |
| 5. GWLB (ServiceName=GWLB, Gateway Load Balancer) | 548-566 | offset=548, limit=19 |
| 6. Cen (ServiceName=Cen) | 567-568 | offset=567, limit=2 |
| 6.1 CEN instance and network instances | 569-586 | offset=569, limit=18 |
| 6.2 Transit Router TR | 587-627 | offset=587, limit=41 |
| 6.3 Route tables and route entries | 628-646 | offset=628, limit=19 |
| 6.4 Prefix lists and CEN legacy routing | 647-667 | offset=647, limit=21 |
| 6.5 CEN bandwidth packages and rate limiting | 668-685 | offset=668, limit=18 |
| 7. Ga (ServiceName=Ga, Global Accelerator) | 686-725 | offset=686, limit=40 |
| 8. VpcPeer (ServiceName=VpcPeer, VPC Peering) | 726-744 | offset=726, limit=19 |
| 9. Privatelink (ServiceName=Privatelink) | 745-775 | offset=745, limit=31 |
| 10. PrivateZone (ServiceName=PrivateZone) | 776-800 | offset=776, limit=25 |
| 11. Eipanycast (ServiceName=Eipanycast, Anycast EIP) | 801-819 | offset=801, limit=19 |
| 12. CDT (ServiceName=CDT, Cloud Data Transfer) | 820-830 | offset=820, limit=11 |
| 13. Smartag (ServiceName=Smartag) | 831-832 | offset=831, limit=2 |
| 13.1 Gateway instances | 833-847 | offset=833, limit=15 |
| 13.2 Cloud Connect Network CCN | 848-860 | offset=848, limit=13 |
| 13.3 ACL and QoS | 861-888 | offset=861, limit=28 |
| 13.4 Routing and network configuration | 889-912 | offset=889, limit=24 |
| 14. flowbag (ServiceName=flowbag, Shared Flow Bag) | 913-924 | offset=913, limit=12 |
| 15. CMN (ServiceName=CMN, Cloud Network Management) | 925-935 | offset=925, limit=11 |
| Appendix A: Naming rules and reading tips | 936-980 | offset=936, limit=45 |
| Appendix B: Query suggestions | 981-end | offset=981 |

---

## 1. Vpc (ServiceName=`Vpc`)

The VPC event source covers 40+ sub-modules: VPC instance, vSwitch, EIP, NAT, VPN, Common Bandwidth, Express Connect, routing, ACL, DHCP, Flow Log, IPv4/IPv6 gateways, Traffic Mirroring, HaVip, Prefix List, Public IP Address Pool, Gateway Endpoint, etc.

### 1.1 VPC instance and vSwitch

| Event Name | Type | Description |
|------------|------|-------------|
| CreateVpc | Write | Create a VPC |
| DeleteVpc | Write | Delete a VPC |
| ModifyVpcAttribute | Write | Modify VPC name, description, CIDR and other attributes |
| DescribeVpcs | Read | Query VPC list |
| DescribeVpcAttribute | Read | Query detailed VPC attributes |
| AssociateVpcCidrBlock | Write | Attach a secondary CIDR block to a VPC |
| UnassociateVpcCidrBlock | Write | Remove a secondary CIDR block from a VPC |
| EnableVpcClassicLink | Write | Enable ClassicLink between VPC and classic network |
| DisableVpcClassicLink | Write | Disable ClassicLink |
| DescribeVpcClassicLink | Read | Query ClassicLink status |
| AttachClassicLinkVpc | Write | Attach a classic-network ECS instance to a VPC |
| DetachClassicLinkVpc | Write | Detach a classic-network ECS instance from a VPC |
| CreateVSwitch | Write | Create a vSwitch |
| DeleteVSwitch | Write | Delete a vSwitch |
| ModifyVSwitchAttribute | Write | Modify vSwitch name/description/CIDR |
| DescribeVSwitches | Read | Query vSwitch list |
| DescribeVSwitchAttributes | Read | Query detailed vSwitch attributes |

### 1.2 EIP / Elastic IP Address

| Event Name | Type | Description |
|------------|------|-------------|
| AllocateEipAddress | Write | Allocate one Elastic IP Address |
| AllocateEipAddressPro | Write | Allocate an EIP with a specified IP or from a specified pool |
| AllocateEipSegmentAddress | Write | Allocate a contiguous EIP segment |
| ReleaseEipAddress | Write | Release an EIP |
| ReleaseEipSegmentAddress | Write | Release an EIP segment |
| AssociateEipAddress | Write | Associate an EIP with ECS/SLB/NAT/HaVip/ENI, etc. |
| UnassociateEipAddress | Write | Disassociate an EIP |
| ModifyEipAddressAttribute | Write | Modify EIP name/bandwidth/description |
| ModifyEipForwardMode | Write | Switch EIP forwarding mode (NAT/SNAT) |
| DescribeEipAddresses | Read | Query EIP list |
| DescribeEipMonitorData | Read | Query EIP monitoring data |
| DescribeEipGatewayInfo | Read | Query EIP gateway information |
| MoveResourceGroup | Write | Move an EIP to another resource group |
| ConvertEipAddressResource | Write | Convert EIP billing method or specification |
| DeletionProtection | Write | Enable/disable EIP deletion protection |

### 1.3 NAT Gateway

| Event Name | Type | Description |
|------------|------|-------------|
| CreateNatGateway | Write | Create a NAT gateway |
| DeleteNatGateway | Write | Delete a NAT gateway |
| ModifyNatGatewayAttribute | Write | Modify NAT gateway name/description |
| ModifyNatGatewaySpec | Write | Modify NAT gateway specification (not for enhanced type) |
| UpdateNatGatewayNatType | Write | Convert standard NAT to enhanced NAT |
| DescribeNatGateways | Read | Query NAT gateway list |
| GetNatGatewayAttribute | Read | Query detailed NAT gateway attributes |
| CreateSnatEntry | Write | Create a SNAT entry (private -> public) |
| DeleteSnatEntry | Write | Delete a SNAT entry |
| ModifySnatEntry | Write | Modify SNAT entry name/public IP |
| DescribeSnatTableEntries | Read | Query SNAT entry list |
| CreateForwardEntry | Write | Create a DNAT/port-forwarding entry (public -> private) |
| DeleteForwardEntry | Write | Delete a DNAT entry |
| ModifyForwardEntry | Write | Modify a DNAT entry |
| DescribeForwardTableEntries | Read | Query DNAT entry list |
| CreateFullNatEntry | Write | Create a FullNAT entry (VPC <-> VPC) |
| DeleteFullNatEntry | Write | Delete a FullNAT entry |
| ModifyFullNatEntryAttribute | Write | Modify a FullNAT entry |
| ListFullNatEntries | Read | Query FullNAT entry list |
| CreateNatIp | Write | Allocate a NAT IP from a NAT IP CIDR |
| DeleteNatIp | Write | Release a NAT IP |
| ModifyNatIpAttribute | Write | Modify NAT IP name/description |
| ListNatIps | Read | Query NAT IP list |
| CreateNatIpCidr | Write | Add an IP CIDR to a NAT gateway (enhanced) |
| DeleteNatIpCidr | Write | Delete a NAT IP CIDR |
| ModifyNatIpCidrAttribute | Write | Modify NAT IP CIDR attributes |
| ListNatIpCidrs | Read | Query NAT IP CIDR list |
| AssociateEipAddressWithNatGateway | Write | Associate an EIP with a NAT gateway (enhanced) |
| DissociateEipAddressFromNatGateway | Write | Disassociate an EIP from a NAT gateway |
| CreateBandwidthPackage | Write | Create a NAT shared bandwidth package (standard) |
| DeleteBandwidthPackage | Write | Delete a NAT bandwidth package |
| AddBandwidthPackageIps | Write | Add IPs to a NAT bandwidth package |
| RemoveBandwidthPackageIps | Write | Remove IPs from a NAT bandwidth package |
| ConvertBandwidthPackage | Write | Convert a NAT bandwidth package to common bandwidth |

### 1.4 VPN Gateway

| Event Name | Type | Description |
|------------|------|-------------|
| CreateVpnGateway | Write | Create a VPN gateway |
| DeleteVpnGateway | Write | Delete a VPN gateway |
| ModifyVpnGatewayAttribute | Write | Modify VPN gateway name/description |
| DescribeVpnGateways | Read | Query VPN gateway list |
| GetVpnGatewayDiagnoseResult | Read | Query VPN diagnosis result |
| UpgradeVpnGatewayFirmware | Write | Upgrade VPN gateway firmware |
| DiagnoseVpnGateway | Write | Start a diagnosis on a VPN gateway |
| CreateVpnConnection | Write | Create an IPsec-VPN connection |
| DeleteVpnConnection | Write | Delete a VPN connection |
| ModifyVpnConnectionAttribute | Write | Modify a VPN connection (IKE/IPsec parameters) |
| DownloadVpnConnectionConfig | Read | Download the peer-side VPN configuration |
| DescribeVpnConnections | Read | Query VPN connection list |
| DescribeVpnConnection | Read | Query details of a single VPN connection |
| CreateVpnRouteEntry | Write | Create a VPN destination route |
| DeleteVpnRouteEntry | Write | Delete a VPN route |
| ModifyVpnRouteEntryWeight | Write | Modify VPN route weight |
| PublishVpnRouteEntry | Write | Publish a VPN route to the VPC |
| UnpublishVpnRouteEntry | Write | Withdraw a published VPN route |
| CreateVpnPbrRouteEntry | Write | Create a VPN policy-based route |
| DeleteVpnPbrRouteEntry | Write | Delete a VPN policy-based route |
| ModifyVpnPbrRouteEntryWeight | Write | Modify VPN policy-based route weight |
| CreateSslVpnServer | Write | Create an SSL-VPN server |
| DeleteSslVpnServer | Write | Delete an SSL-VPN server |
| ModifySslVpnServer | Write | Modify SSL-VPN server configuration |
| CreateSslVpnClientCert | Write | Create an SSL-VPN client certificate |
| DeleteSslVpnClientCert | Write | Delete an SSL-VPN client certificate |
| ModifySslVpnClientCert | Write | Modify an SSL-VPN client certificate |
| DescribeSslVpnClientCerts | Read | Query SSL-VPN client certificate list |
| CreateCustomerGateway | Write | Create a customer gateway (records the on-premises public IP) |
| DeleteCustomerGateway | Write | Delete a customer gateway |
| ModifyCustomerGatewayAttribute | Write | Modify customer gateway name/ASN |
| DescribeCustomerGateways | Read | Query customer gateway list |
| CreateIpsecServer | Write | Create an IPsec server (client access mode) |
| DeleteIpsecServer | Write | Delete an IPsec server |
| UpdateIpsecServer | Write | Modify IPsec server configuration |
| ListIpsecServers | Read | Query IPsec server list |
| CreateVpnAttachment | Write | Create a VPN attachment (used by TR/CEN) |
| DeleteVpnAttachment | Write | Delete a VPN attachment |
| CreateVpnGreTunnel | Write | Create a GRE tunnel |
| DeleteVpnGreTunnel | Write | Delete a GRE tunnel |
| UpdateVpnGreTunnelAttribute | Write | Modify GRE tunnel configuration |
| DescribeVpnGreTunnels | Read | Query GRE tunnel list |

### 1.5 Common Bandwidth

| Event Name | Type | Description |
|------------|------|-------------|
| CreateCommonBandwidthPackage | Write | Create a common bandwidth package |
| DeleteCommonBandwidthPackage | Write | Delete a common bandwidth package |
| AddCommonBandwidthPackageIp | Write | Add an EIP to a common bandwidth package |
| RemoveCommonBandwidthPackageIp | Write | Remove an EIP from a common bandwidth package |
| ModifyCommonBandwidthPackageAttribute | Write | Modify common bandwidth package name/description |
| ModifyCommonBandwidthPackageSpec | Write | Modify common bandwidth package specification |
| DescribeCommonBandwidthPackages | Read | Query common bandwidth package list |
| ConvertCommonBandwidthPackage | Write | Convert common bandwidth package billing type |
| EnableInstanceHighDefinitionMonitor | Write | Enable second-level monitoring |
| DisableInstanceHighDefinitionMonitor | Write | Disable second-level monitoring |

### 1.6 Express Connect

| Event Name | Type | Description |
|------------|------|-------------|
| CreatePhysicalConnection | Write | Create a physical connection |
| DeletePhysicalConnection | Write | Delete a physical connection |
| ModifyPhysicalConnectionAttribute | Write | Modify physical connection attributes |
| EnablePhysicalConnection | Write | Enable a physical connection |
| CancelPhysicalConnection | Write | Cancel a physical connection application |
| ConfirmPhysicalConnection | Write | Confirm activation of a physical connection |
| TerminatePhysicalConnection | Write | Terminate a physical connection |
| DescribePhysicalConnections | Read | Query physical connection list |
| CreateVirtualBorderRouter | Write | Create a virtual border router (VBR) |
| DeleteVirtualBorderRouter | Write | Delete a VBR |
| ModifyVirtualBorderRouterAttribute | Write | Modify VBR configuration |
| TerminateVirtualBorderRouter | Write | Terminate a VBR |
| RecoverVirtualBorderRouter | Write | Recover a VBR |
| DescribeVirtualBorderRouters | Read | Query VBR list |
| CreateVirtualPhysicalConnection | Write | Create a virtual physical connection (VPC) |
| DeleteVirtualPhysicalConnection | Write | Delete a virtual physical connection |
| CreateRouterInterface | Write | Create a router interface (RI) |
| DeleteRouterInterface | Write | Delete a router interface |
| ModifyRouterInterfaceAttribute | Write | Modify router interface configuration |
| ModifyRouterInterfaceSpec | Write | Modify router interface specification |
| ActivateRouterInterface | Write | Activate a router interface |
| DeactivateRouterInterface | Write | Deactivate a router interface |
| ConnectRouterInterface | Write | Initiate a router interface connection |
| DescribeRouterInterfaces | Read | Query router interface list |
| CreateBgpGroup | Write | Create a BGP group |
| DeleteBgpGroup | Write | Delete a BGP group |
| ModifyBgpGroupAttribute | Write | Modify BGP group configuration |
| DescribeBgpGroups | Read | Query BGP group list |
| CreateBgpPeer | Write | Create a BGP peer |
| DeleteBgpPeer | Write | Delete a BGP peer |
| ModifyBgpPeerAttribute | Write | Modify BGP peer configuration |
| DescribeBgpPeers | Read | Query BGP peer list |
| AddBgpNetwork | Write | Add a BGP advertised network |
| DeleteBgpNetwork | Write | Delete a BGP advertised network |
| DescribeBgpNetworks | Read | Query BGP advertised networks |
| CreateExpressCloudConnection | Write | Create an ECC cloud connection |
| DeleteExpressCloudConnection | Write | Delete an ECC |
| ModifyExpressCloudConnectionAttribute | Write | Modify ECC configuration |
| ModifyExpressCloudConnectionBandwidth | Write | Modify ECC bandwidth |
| DescribeExpressCloudConnections | Read | Query ECC list |

### 1.7 Routing

| Event Name | Type | Description |
|------------|------|-------------|
| CreateRouteTable | Write | Create a custom route table |
| DeleteRouteTable | Write | Delete a route table |
| ModifyRouteTableAttributes | Write | Modify route table name/description |
| DescribeRouteTables | Read | Query route table list |
| AssociateRouteTable | Write | Associate a route table with a vSwitch |
| UnassociateRouteTable | Write | Disassociate a route table from a vSwitch |
| AssociateRouteTableWithGateway | Write | Associate a route table with an IPv4 gateway |
| DissociateRouteTableFromGateway | Write | Disassociate a route table from a gateway |
| CreateRouteEntry | Write | Add a route entry |
| DeleteRouteEntry | Write | Delete a route entry |
| ModifyRouteEntry | Write | Modify a route entry |
| DescribeRouteEntryList | Read | Query route entry list |
| PublishRouteEntries | Write | Publish routes to CEN |
| UnpublishRouteEntries | Write | Withdraw published routes from CEN |

### 1.8 Network ACL

| Event Name | Type | Description |
|------------|------|-------------|
| CreateNetworkAcl | Write | Create a network ACL |
| DeleteNetworkAcl | Write | Delete a network ACL |
| ModifyNetworkAclAttributes | Write | Modify ACL name/description |
| DescribeNetworkAcls | Read | Query ACL list |
| AssociateNetworkAcl | Write | Associate an ACL with a vSwitch |
| UnassociateNetworkAcl | Write | Disassociate an ACL from a vSwitch |
| CopyNetworkAclEntries | Write | Copy ACL rules to another ACL |
| UpdateNetworkAclEntries | Write | Batch-update ACL ingress/egress rules |

### 1.9 DHCP Options Set

| Event Name | Type | Description |
|------------|------|-------------|
| CreateDhcpOptionsSet | Write | Create a DHCP options set |
| DeleteDhcpOptionsSet | Write | Delete a DHCP options set |
| UpdateDhcpOptionsSetAttribute | Write | Modify a DHCP options set |
| AttachDhcpOptionsSetToVpc | Write | Attach a DHCP options set to a VPC |
| DetachDhcpOptionsSetFromVpc | Write | Detach a DHCP options set |
| ReplaceVpcDhcpOptionsSet | Write | Replace the DHCP options set attached to a VPC |
| DescribeDhcpOptionsSets | Read | Query DHCP options set list |

### 1.10 Flow Log

| Event Name | Type | Description |
|------------|------|-------------|
| CreateFlowLog | Write | Create a flow log |
| DeleteFlowLog | Write | Delete a flow log |
| ActiveFlowLog | Write | Start flow log collection |
| DeactiveFlowLog | Write | Stop flow log collection |
| ModifyFlowLogAttribute | Write | Modify flow log configuration |
| DescribeFlowLogs | Read | Query flow log list |
| OpenFlowLogService | Write | Activate the flow log service (RAM authorization) |

### 1.11 IPv4 / IPv6 Gateways and Addresses

| Event Name | Type | Description |
|------------|------|-------------|
| CreateIpv4Gateway | Write | Create an IPv4 gateway |
| DeleteIpv4Gateway | Write | Delete an IPv4 gateway |
| UpdateIpv4GatewayAttribute | Write | Modify IPv4 gateway configuration |
| EnableVpcIpv4Gateway | Write | Enable a VPC IPv4 gateway |
| GetIpv4GatewayAttribute | Read | Query IPv4 gateway details |
| ListIpv4Gateways | Read | Query IPv4 gateway list |
| CreateIpv6Gateway | Write | Create an IPv6 gateway |
| DeleteIpv6Gateway | Write | Delete an IPv6 gateway |
| ModifyIpv6GatewayAttribute | Write | Modify IPv6 gateway configuration |
| ModifyIpv6GatewaySpec | Write | Modify IPv6 gateway specification |
| AllocateIpv6InternetBandwidth | Write | Allocate internet bandwidth for IPv6 |
| DeleteIpv6InternetBandwidth | Write | Release IPv6 internet bandwidth |
| ModifyIpv6InternetBandwidth | Write | Adjust IPv6 internet bandwidth |
| CreateIpv6EgressOnlyRule | Write | Create an IPv6 egress-only rule (inbound blocked) |
| DeleteIpv6EgressOnlyRule | Write | Delete an IPv6 egress-only rule |
| DescribeIpv6EgressOnlyRules | Read | Query egress-only rules |
| AllocateVpcIpv6Cidr | Write | Allocate an IPv6 CIDR to a VPC |
| DescribeIpv6Addresses | Read | Query IPv6 address list |
| ModifyIpv6AddressAttribute | Write | Modify IPv6 address attributes |
| CreateIPv6Translator | Write | Create an IPv6 translation service instance |
| DeleteIPv6Translator | Write | Delete an IPv6 translation service |
| ModifyIPv6TranslatorAttribute | Write | Modify IPv6 translation service attributes |
| ModifyIPv6TranslatorBandwidth | Write | Modify IPv6 translation service bandwidth |
| CreateIPv6TranslatorEntry | Write | Create an IPv6 translation mapping entry |
| DeleteIPv6TranslatorEntry | Write | Delete an IPv6 translation mapping entry |
| ModifyIPv6TranslatorEntry | Write | Modify an IPv6 translation mapping entry |
| DescribeIPv6Translators | Read | Query IPv6 translation service list |
| DescribeIPv6TranslatorEntries | Read | Query IPv6 translation mapping entries |

### 1.12 Traffic Mirroring

| Event Name | Type | Description |
|------------|------|-------------|
| CreateTrafficMirrorFilter | Write | Create a traffic mirror filter |
| DeleteTrafficMirrorFilter | Write | Delete a filter |
| UpdateTrafficMirrorFilterAttribute | Write | Modify filter attributes |
| CreateTrafficMirrorFilterRules | Write | Create filter rules |
| DeleteTrafficMirrorFilterRules | Write | Delete filter rules |
| UpdateTrafficMirrorFilterRuleAttribute | Write | Modify a filter rule |
| CreateTrafficMirrorSession | Write | Create a mirror session (source -> destination) |
| DeleteTrafficMirrorSession | Write | Delete a mirror session |
| UpdateTrafficMirrorSessionAttribute | Write | Modify mirror session attributes |
| AddSourcesToTrafficMirrorSession | Write | Add source ENIs to a mirror session |
| RemoveSourcesFromTrafficMirrorSession | Write | Remove source ENIs from a mirror session |
| ListTrafficMirrorFilters | Read | Query filter list |
| ListTrafficMirrorSessions | Read | Query mirror session list |

### 1.13 HaVip / Gateway Endpoint / Prefix List / Public IP Address Pool

| Event Name | Type | Description |
|------------|------|-------------|
| CreateHaVip | Write | Create a high-availability virtual IP |
| DeleteHaVip | Write | Delete a HaVip |
| ModifyHaVipAttribute | Write | Modify HaVip name/description |
| AssociateHaVip | Write | Associate a HaVip with an ECS instance |
| UnassociateHaVip | Write | Disassociate a HaVip |
| SetHaVipMasterInstance | Write | Set the master instance of a HaVip |
| DescribeHaVips | Read | Query HaVip list |
| CreateVpcGatewayEndpoint | Write | Create a VPC gateway endpoint (access OSS, etc.) |
| DeleteVpcGatewayEndpoint | Write | Delete a gateway endpoint |
| UpdateVpcGatewayEndpointAttribute | Write | Modify gateway endpoint attributes |
| AssociateRouteTablesWithVpcGatewayEndpoint | Write | Associate route tables with a gateway endpoint |
| DissociateRouteTablesFromVpcGatewayEndpoint | Write | Disassociate route tables from a gateway endpoint |
| ListVpcGatewayEndpoints | Read | Query gateway endpoint list |
| GetVpcGatewayEndpointAttribute | Read | Query gateway endpoint details |
| CreateVpcPrefixList | Write | Create a prefix list |
| DeleteVpcPrefixList | Write | Delete a prefix list |
| ModifyVpcPrefixList | Write | Modify prefix list entries |
| GetVpcPrefixListEntries | Read | Query prefix list entries |
| GetVpcPrefixListAssociations | Read | Query objects associated with a prefix list |
| RetryVpcPrefixListAssociation | Write | Retry a prefix list association operation |
| CreatePublicIpAddressPool | Write | Create a public IP address pool |
| DeletePublicIpAddressPool | Write | Delete a public IP address pool |
| UpdatePublicIpAddressPoolAttribute | Write | Modify address pool attributes |
| AddPublicIpAddressPoolCidrBlock | Write | Add a CIDR to an address pool |
| DeletePublicIpAddressPoolCidrBlock | Write | Delete a CIDR from an address pool |
| ListPublicIpAddressPools | Read | Query address pool list |
| ListPublicIpAddressPoolCidrBlocks | Read | Query address pool CIDR list |

### 1.14 Tags and Orders

| Event Name | Type | Description |
|------------|------|-------------|
| TagResources | Write | Tag resources |
| UnTagResources | Write | Remove resource tags |
| ListTagResources | Read | Query resource tags |
| Create | Write | Generic order: create instance (order API) |
| Modify | Write | Generic order: modify instance |
| Release | Write | Generic order: release instance |
| Renew | Write | Generic order: renew |
| RenewInstance | Write | Generic order: renew instance (legacy API) |
| RemainRefund | Write | Generic order: refund |
| DeletionProtection | Write | Enable/disable instance deletion protection |
| ModifyInstanceAutoRenewalAttribute | Write | Modify auto-renewal configuration |
| MoveResourceGroup | Write | Move resources to another resource group |

---

## 2. Slb (ServiceName=`Slb`, Classic Load Balancer CLB)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateLoadBalancer | Write | Create a CLB instance |
| DeleteLoadBalancer | Write | Delete a CLB instance |
| ModifyLoadBalancerInstanceSpec | Write | Modify CLB performance specification |
| ModifyLoadBalancerInternetSpec | Write | Modify CLB internet bandwidth/billing method |
| ModifyLoadBalancerPayType | Write | Modify CLB billing type (pay-as-you-go <-> subscription) |
| SetLoadBalancerName | Write | Set the CLB name |
| SetLoadBalancerStatus | Write | Set the CLB to active/inactive |
| SetLoadBalancerDeleteProtection | Write | Set deletion protection |
| SetLoadBalancerModificationProtection | Write | Set configuration-modification protection |
| CreateLoadBalancerHTTPListener | Write | Create an HTTP listener |
| CreateLoadBalancerHTTPSListener | Write | Create an HTTPS listener |
| CreateLoadBalancerTCPListener | Write | Create a TCP listener |
| CreateLoadBalancerUDPListener | Write | Create a UDP listener |
| SetLoadBalancerHTTPListenerAttribute | Write | Modify HTTP listener configuration |
| SetLoadBalancerHTTPSListenerAttribute | Write | Modify HTTPS listener configuration |
| SetLoadBalancerTCPListenerAttribute | Write | Modify TCP listener configuration |
| SetLoadBalancerUDPListenerAttribute | Write | Modify UDP listener configuration |
| DeleteLoadBalancerListener | Write | Delete a listener |
| StartLoadBalancerListener | Write | Start a listener |
| StopLoadBalancerListener | Write | Stop a listener |
| AddBackendServers | Write | Add ECS instances to the default backend |
| RemoveBackendServers | Write | Remove ECS instances from the default backend |
| SetBackendServers | Write | Set default backend weights |
| DescribeHealthStatus | Read | Query backend health status (probe results) |
| DescribeLoadBalancerAttribute | Read | Query detailed CLB attributes |
| DescribeLoadBalancers | Read | Query CLB list |
| CreateVServerGroup | Write | Create a vServer group |
| DeleteVServerGroup | Write | Delete a vServer group |
| ModifyVServerGroupBackendServers | Write | Modify vServer group backends |
| SetVServerGroupAttribute | Write | Modify vServer group attributes |
| AddVServerGroupBackendServers | Write | Add backends to a vServer group |
| RemoveVServerGroupBackendServers | Write | Remove backends from a vServer group |
| CreateMasterSlaveServerGroup | Write | Create a master-slave server group |
| DeleteMasterSlaveServerGroup | Write | Delete a master-slave server group |
| CreateRules | Write | Create HTTP/HTTPS forwarding rules |
| DeleteRules | Write | Delete forwarding rules |
| SetRule | Write | Modify a single forwarding rule |
| DescribeRules | Read | Query forwarding rule list |
| CreateDomainExtension | Write | Create an additional domain (HTTPS) |
| DeleteDomainExtension | Write | Delete an additional domain |
| SetDomainExtensionAttribute | Write | Modify additional domain configuration |
| UploadServerCertificate | Write | Upload a server certificate |
| DeleteServerCertificate | Write | Delete a server certificate |
| SetServerCertificateName | Write | Rename a server certificate |
| UploadCACertificate | Write | Upload a CA certificate |
| DeleteCACertificate | Write | Delete a CA certificate |
| SetCACertificateName | Write | Rename a CA certificate |
| CreateAccessControlList | Write | Create an access control list |
| DeleteAccessControlList | Write | Delete an access control list |
| AddAccessControlListEntry | Write | Add an entry to an ACL |
| RemoveAccessControlListEntry | Write | Remove an entry from an ACL |

---

## 3. ALB (ServiceName=`ALB`, Application Load Balancer)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateLoadBalancer | Write | Create an ALB instance |
| DeleteLoadBalancer | Write | Delete an ALB instance |
| UpdateLoadBalancerAttribute | Write | Modify ALB name/attributes |
| UpdateLoadBalancerEdition | Write | Upgrade ALB edition (Basic/Standard/WAF) |
| EnableLoadBalancerAccessLog | Write | Enable access logs |
| DisableLoadBalancerAccessLog | Write | Disable access logs |
| EnableDeletionProtection | Write | Enable deletion protection |
| DisableDeletionProtection | Write | Disable deletion protection |
| CreateListener | Write | Create a listener |
| DeleteListener | Write | Delete a listener |
| UpdateListenerAttribute | Write | Modify listener configuration |
| StartListener | Write | Start a listener |
| StopListener | Write | Stop a listener |
| CreateServerGroup | Write | Create a server group |
| DeleteServerGroup | Write | Delete a server group |
| UpdateServerGroupAttribute | Write | Modify server group attributes (including health checks) |
| AddServersToServerGroup | Write | Add backends to a server group |
| RemoveServersFromServerGroup | Write | Remove backends from a server group |
| ReplaceServersInServerGroup | Write | Replace backends in a server group |
| CreateRule | Write | Create a single forwarding rule |
| CreateRules | Write | Batch-create forwarding rules |
| DeleteRule | Write | Delete a single forwarding rule |
| DeleteRules | Write | Batch-delete forwarding rules |
| UpdateRuleAttribute | Write | Modify a single forwarding rule |
| UpdateRulesAttribute | Write | Batch-modify forwarding rules |
| CreateAcl | Write | Create an access control list |
| DeleteAcl | Write | Delete an ACL |
| UpdateAclAttribute | Write | Modify ACL attributes |
| AssociateAclsWithListener | Write | Associate ACLs with a listener |
| DissociateAclsFromListener | Write | Disassociate ACLs from a listener |
| AddEntriesToAcl | Write | Add entries to an ACL |
| RemoveEntriesFromAcl | Write | Remove entries from an ACL |
| CreateSecurityPolicy | Write | Create a TLS security policy |
| DeleteSecurityPolicy | Write | Delete a TLS security policy |
| UpdateSecurityPolicyAttribute | Write | Modify a TLS security policy |
| CreateHealthCheckTemplate | Write | Create a health check template |
| DeleteHealthCheckTemplates | Write | Delete health check templates |
| UpdateHealthCheckTemplateAttribute | Write | Modify a health check template |
| ApplyHealthCheckTemplateToServerGroup | Write | Apply a health check template to a server group |
| AttachCommonBandwidthPackageToLoadBalancer | Write | Attach common bandwidth to an ALB |
| DetachCommonBandwidthPackageFromLoadBalancer | Write | Detach common bandwidth from an ALB |

---

## 4. NLB (ServiceName=`Nlb`, Network Load Balancer)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateLoadBalancer | Write | Create an NLB instance |
| DeleteLoadBalancer | Write | Delete an NLB instance |
| UpdateLoadBalancerAttribute | Write | Modify NLB name/attributes |
| UpdateLoadBalancerAddressTypeConfig | Write | Modify address type (internet/internal) |
| UpdateLoadBalancerZones | Write | Modify zone configuration |
| EnableLoadBalancerIpv6Internet | Write | Enable IPv6 internet |
| DisableLoadBalancerIpv6Internet | Write | Disable IPv6 internet |
| CreateListener | Write | Create a listener |
| DeleteListener | Write | Delete a listener |
| UpdateListenerAttribute | Write | Modify listener configuration |
| StartListener | Write | Start a listener |
| StopListener | Write | Stop a listener |
| CreateServerGroup | Write | Create a server group |
| DeleteServerGroup | Write | Delete a server group |
| UpdateServerGroupAttribute | Write | Modify server group configuration (including health checks) |
| UpdateServerGroupServersAttribute | Write | Modify backend weights etc. in a server group |
| AddServersToServerGroup | Write | Add backends to a server group |
| RemoveServersFromServerGroup | Write | Remove backends from a server group |
| CreateSecurityPolicy | Write | Create a TLS security policy |
| DeleteSecurityPolicy | Write | Delete a TLS security policy |
| UpdateSecurityPolicyAttribute | Write | Modify a TLS security policy |
| AttachCommonBandwidthPackageToLoadBalancer | Write | Attach common bandwidth to an NLB |
| DetachCommonBandwidthPackageFromLoadBalancer | Write | Detach common bandwidth from an NLB |
| EnableLoadBalancerAccessLog | Write | Enable access logs |
| DisableLoadBalancerAccessLog | Write | Disable access logs |

---

## 5. GWLB (ServiceName=`GWLB`, Gateway Load Balancer)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateLoadBalancer | Write | Create a GWLB instance |
| DeleteLoadBalancer | Write | Delete a GWLB instance |
| UpdateLoadBalancerAttribute | Write | Modify GWLB attributes |
| UpdateLoadBalancerZones | Write | Modify zone configuration |
| CreateListener | Write | Create a listener |
| DeleteListener | Write | Delete a listener |
| UpdateListenerAttribute | Write | Modify listener configuration |
| CreateServerGroup | Write | Create a server group |
| DeleteServerGroup | Write | Delete a server group |
| UpdateServerGroupAttribute | Write | Modify server group configuration |
| AddServersToServerGroup | Write | Add backends to a server group |
| RemoveServersFromServerGroup | Write | Remove backends from a server group |

---

## 6. Cen (ServiceName=`Cen`, Cloud Enterprise Network)

### 6.1 CEN instance and network instances

| Event Name | Type | Description |
|------------|------|-------------|
| CreateCen | Write | Create a Cloud Enterprise Network instance |
| DeleteCen | Write | Delete a CEN instance |
| ModifyCenAttribute | Write | Modify CEN name/description |
| DescribeCens | Read | Query CEN list |
| AttachCenChildInstance | Write | Attach a network instance (VPC/VBR/CCN) to CEN |
| DetachCenChildInstance | Write | Detach a network instance from CEN |
| DescribeCenAttachedChildInstances | Read | Query attached network instances |
| DescribeCenAttachedChildInstanceAttribute | Read | Query attached instance details |
| DescribeChildInstanceRegions | Read | Query regions where instances can be attached |
| DescribeGrantRulesToCen | Read | Query cross-account grant rules |
| DescribeGrantRulesToResource | Read | Query the list of CENs a resource is granted to |
| GrantInstanceToCen | Write | Grant an instance to join another account's CEN (cross-account) |
| RevokeInstanceFromCen | Write | Revoke a cross-account grant |

### 6.2 Transit Router TR

| Event Name | Type | Description |
|------------|------|-------------|
| CreateTransitRouter | Write | Create a transit router (TR) |
| DeleteTransitRouter | Write | Delete a TR |
| UpdateTransitRouter | Write | Modify TR attributes |
| ListTransitRouters | Read | Query TR list |
| CreateTransitRouterVpcAttachment | Write | Create a TR-VPC attachment |
| DeleteTransitRouterVpcAttachment | Write | Delete a TR-VPC attachment |
| UpdateTransitRouterVpcAttachmentAttribute | Write | Modify TR-VPC attachment attributes |
| UpdateTransitRouterVpcAttachmentZones | Write | Modify TR-VPC attachment zones |
| ListTransitRouterVpcAttachments | Read | Query TR-VPC attachment list |
| CreateTransitRouterVbrAttachment | Write | Create a TR-VBR attachment |
| DeleteTransitRouterVbrAttachment | Write | Delete a TR-VBR attachment |
| UpdateTransitRouterVbrAttachmentAttribute | Write | Modify a TR-VBR attachment |
| ListTransitRouterVbrAttachments | Read | Query TR-VBR attachment list |
| CreateTransitRouterCidr | Write | Create a TR CIDR |
| DeleteTransitRouterCidr | Write | Delete a TR CIDR |
| ModifyTransitRouterCidr | Write | Modify a TR CIDR |
| ListTransitRouterCidr | Read | Query TR CIDRs |
| ListTransitRouterCidrAllocation | Read | Query TR CIDR allocations |
| CreateTransitRouterVpnAttachment | Write | Create a TR-VPN attachment |
| DeleteTransitRouterVpnAttachment | Write | Delete a TR-VPN attachment |
| UpdateTransitRouterVpnAttachmentAttribute | Write | Modify a TR-VPN attachment |
| ListTransitRouterVpnAttachments | Read | Query TR-VPN attachment list |
| CreateTransitRouterPeerAttachment | Write | Create an inter-region TR peering |
| DeleteTransitRouterPeerAttachment | Write | Delete an inter-region TR peering |
| UpdateTransitRouterPeerAttachmentAttribute | Write | Modify an inter-region TR peering |
| ListTransitRouterPeerAttachments | Read | Query inter-region TR peering list |
| CreateTransitRouterEcrAttachment | Write | Create a TR-ECR (Express Connect Router) attachment |
| DeleteTransitRouterEcrAttachment | Write | Delete a TR-ECR attachment |
| UpdateTransitRouterEcrAttachmentAttribute | Write | Modify a TR-ECR attachment |
| ListTransitRouterEcrAttachments | Read | Query TR-ECR attachment list |
| CreateTransitRouterMulticastDomain | Write | Create a TR multicast domain |
| DeleteTransitRouterMulticastDomain | Write | Delete a multicast domain |
| UpdateTransitRouterMulticastDomain | Write | Modify a multicast domain |
| ListTransitRouterMulticastDomains | Read | Query multicast domain list |
| AssociateTransitRouterMulticastDomain | Write | Associate a multicast domain |
| DisassociateTransitRouterMulticastDomain | Write | Disassociate a multicast domain |

### 6.3 Route tables and route entries

| Event Name | Type | Description |
|------------|------|-------------|
| CreateTransitRouterRouteTable | Write | Create a TR route table |
| DeleteTransitRouterRouteTable | Write | Delete a TR route table |
| UpdateTransitRouterRouteTable | Write | Modify TR route table attributes |
| ListTransitRouterRouteTables | Read | Query TR route table list |
| CreateTransitRouterRouteEntry | Write | Create a TR route entry |
| DeleteTransitRouterRouteEntry | Write | Delete a TR route entry |
| UpdateTransitRouterRouteEntry | Write | Modify a TR route entry |
| ListTransitRouterRouteEntries | Read | Query TR route entries |
| AssociateTransitRouterAttachmentWithRouteTable | Write | Associate an attachment with a route table |
| DissociateTransitRouterAttachmentFromRouteTable | Write | Disassociate an attachment from a route table |
| EnableTransitRouterRouteTablePropagation | Write | Enable route propagation |
| DisableTransitRouterRouteTablePropagation | Write | Disable route propagation |
| ListTransitRouterRouteTableAssociations | Read | Query route table associations |
| ListTransitRouterRouteTablePropagations | Read | Query route propagation relations |

### 6.4 Prefix lists and CEN legacy routing

| Event Name | Type | Description |
|------------|------|-------------|
| CreateTransitRouterPrefixListAssociation | Write | Associate a prefix list with a TR |
| DeleteTransitRouterPrefixListAssociation | Write | Remove a prefix list association |
| ListTransitRouterPrefixListAssociation | Read | Query prefix list associations |
| PublishRouteEntries | Write | Publish routes to CEN |
| WithdrawPublishedRouteEntries | Write | Withdraw published CEN routes |
| DescribePublishedRouteEntries | Read | Query published routes |
| CreateCenRouteMap | Write | Create a route map |
| DeleteCenRouteMap | Write | Delete a route map |
| ModifyCenRouteMap | Write | Modify a route map |
| DescribeCenRouteMaps | Read | Query route map list |
| ActiveFlowLog | Write | Start a CEN flow log |
| DeactiveFlowLog | Write | Stop a CEN flow log |
| CreateFlowlog | Write | Create a CEN flow log |
| DeleteFlowlog | Write | Delete a CEN flow log |
| ModifyFlowLogAttribute | Write | Modify flow log attributes |
| DescribeFlowlogs | Read | Query flow log list |

### 6.5 CEN bandwidth packages and rate limiting

| Event Name | Type | Description |
|------------|------|-------------|
| CreateCenBandwidthPackage | Write | Create a CEN bandwidth package |
| DeleteCenBandwidthPackage | Write | Delete a CEN bandwidth package |
| ModifyCenBandwidthPackageAttribute | Write | Modify bandwidth package name/description |
| ModifyCenBandwidthPackageSpec | Write | Modify bandwidth package specification |
| ModifyCenBandwidthPackageChargeType | Write | Modify bandwidth package billing type |
| AssociateCenBandwidthPackage | Write | Associate a bandwidth package with CEN |
| UnassociateCenBandwidthPackage | Write | Disassociate a bandwidth package from CEN |
| CreateCenInterRegionBandwidthLimit | Write | Create inter-region bandwidth rate limit |
| ModifyCenInterRegionBandwidthLimit | Write | Modify inter-region bandwidth rate limit |
| DeleteCenInterRegionBandwidthLimit | Write | Delete inter-region bandwidth rate limit |
| DescribeCenInterRegionBandwidthLimits | Read | Query inter-region bandwidth rate limits |

---

## 7. Ga (ServiceName=`Ga`, Global Accelerator)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateAccelerator | Write | Create a Global Accelerator instance |
| DeleteAccelerator | Write | Delete a Global Accelerator instance |
| UpdateAcceleratorAttribute | Write | Modify instance attributes |
| UpdateAcceleratorConfirm | Write | Confirm a configuration change |
| DescribeAccelerator | Read | Query instance details |
| ListAccelerators | Read | Query instance list |
| CreateListener | Write | Create a listener |
| DeleteListener | Write | Delete a listener |
| UpdateListener | Write | Modify a listener |
| DescribeListener | Read | Query listener details |
| ListListeners | Read | Query listener list |
| CreateEndpointGroup | Write | Create an endpoint group |
| DeleteEndpointGroup | Write | Delete an endpoint group |
| UpdateEndpointGroup | Write | Modify an endpoint group |
| DescribeEndpointGroup | Read | Query endpoint group details |
| ListEndpointGroups | Read | Query endpoint group list |
| AddEntriesToAcl | Write | Add entries to an ACL |
| RemoveEntriesFromAcl | Write | Remove entries from an ACL |
| CreateAcl | Write | Create an ACL |
| DeleteAcl | Write | Delete an ACL |
| UpdateAclAttribute | Write | Modify ACL attributes |
| CreateBandwidthPackage | Write | Create a GA bandwidth package |
| DeleteBandwidthPackage | Write | Delete a GA bandwidth package |
| UpdateBandwidthPackage | Write | Modify a GA bandwidth package |
| BandwidthPackageAddAccelerator | Write | Associate a bandwidth package with an accelerator |
| BandwidthPackageRemoveAccelerator | Write | Disassociate a bandwidth package from an accelerator |
| CreateBasicAccelerator | Write | Create a basic accelerator instance |
| DeleteBasicAccelerator | Write | Delete a basic accelerator instance |
| UpdateBasicAccelerator | Write | Modify a basic accelerator instance |
| CreateBasicEndpoint | Write | Create a basic accelerator endpoint |
| DeleteBasicEndpoint | Write | Delete a basic accelerator endpoint |
| CreateBasicEndpointGroup | Write | Create a basic accelerator endpoint group |
| DeleteBasicEndpointGroup | Write | Delete a basic accelerator endpoint group |

---

## 8. VpcPeer (ServiceName=`VpcPeer`)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateVpcPeerConnection | Write | Create a VPC peering connection |
| DeleteVpcPeerConnection | Write | Delete a peering connection |
| ModifyVpcPeerConnection | Write | Modify peering connection name/description/bandwidth |
| AcceptVpcPeerConnection | Write | Accept a peering connection initiated by the peer |
| RejectVpcPeerConnection | Write | Reject a peering connection |
| GetVpcPeerConnectionAttribute | Read | Query peering connection details |
| ListVpcPeerConnections | Read | Query peering connection list |
| ChangeResourceGroup | Write | Change the owning resource group |
| TagResources | Write | Tag resources |
| UnTagResources | Write | Remove tags |
| ListTagResources | Read | Query tags |
| MoveResourceGroup | Write | Move resource group |

---

## 9. Privatelink (ServiceName=`Privatelink`)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateVpcEndpoint | Write | Create an endpoint |
| DeleteVpcEndpoint | Write | Delete an endpoint |
| UpdateVpcEndpointAttribute | Write | Modify endpoint attributes |
| ListVpcEndpoints | Read | Query endpoint list |
| GetVpcEndpointAttribute | Read | Query endpoint details |
| CreateVpcEndpointService | Write | Create an endpoint service |
| DeleteVpcEndpointService | Write | Delete an endpoint service |
| UpdateVpcEndpointServiceAttribute | Write | Modify endpoint service attributes |
| ListVpcEndpointServices | Read | Query endpoint service list |
| AddUserToVpcEndpointService | Write | Add an allowlist account |
| RemoveUserFromVpcEndpointService | Write | Remove an allowlist account |
| ListVpcEndpointServiceUsers | Read | Query allowlist accounts |
| AddZoneToVpcEndpoint | Write | Add a zone to an endpoint |
| RemoveZoneFromVpcEndpoint | Write | Remove a zone from an endpoint |
| ListVpcEndpointZones | Read | Query endpoint zones |
| AttachSecurityGroupToVpcEndpoint | Write | Attach a security group to an endpoint |
| DetachSecurityGroupFromVpcEndpoint | Write | Detach a security group from an endpoint |
| ListVpcEndpointSecurityGroups | Read | Query endpoint security groups |
| CreateVpcEndpointServiceResource | Write | Add a backend resource to the service |
| DeleteVpcEndpointServiceResource | Write | Remove a backend resource from the service |
| ListVpcEndpointServiceResources | Read | Query service backend resources |
| CreateVpcEndpointConnection | Write | Establish an endpoint connection |
| DisableVpcEndpointConnection | Write | Reject/disable an endpoint connection |
| EnableVpcEndpointConnection | Write | Allow an endpoint connection |

---

## 10. PrivateZone (ServiceName=`PrivateZone`)

| Event Name | Type | Description |
|------------|------|-------------|
| AddZone | Write | Add a private zone |
| DeleteZone | Write | Delete a zone |
| UpdateZoneRemark | Write | Modify zone remark |
| DescribeZoneInfo | Read | Query zone details |
| DescribeZones | Read | Query zone list |
| BindZoneVpc | Write | Associate a zone with a VPC |
| UnbindZoneVpc | Write | Disassociate a zone from a VPC |
| AddZoneRecord | Write | Add a DNS record |
| DeleteZoneRecord | Write | Delete a DNS record |
| UpdateZoneRecord | Write | Modify a DNS record |
| DescribeZoneRecords | Read | Query DNS records |
| SetZoneRecordStatus | Write | Enable/disable a DNS record |
| SetProxyPattern | Write | Set the recursive resolution proxy mode |
| AddUserVpcAuthorization | Write | Add cross-account VPC authorization |
| DeleteUserVpcAuthorization | Write | Delete cross-account VPC authorization |
| DescribeUserVpcAuthorizations | Read | Query cross-account authorization list |
| UpdateRecordRemark | Write | Modify record remark (legacy version) |
| UpdateZoneRecordRemark | Write | Modify record remark (new version) |

---

## 11. Eipanycast (ServiceName=`Eipanycast`)

| Event Name | Type | Description |
|------------|------|-------------|
| AllocateAnycastEipAddress | Write | Allocate an Anycast EIP |
| ReleaseAnycastEipAddress | Write | Release an Anycast EIP |
| ModifyAnycastEipAddressAttributes | Write | Modify Anycast EIP attributes |
| AssociateAnycastEipAddress | Write | Associate an Anycast EIP |
| UnassociateAnycastEipAddress | Write | Disassociate an Anycast EIP |
| DescribeAnycastEipAddress | Read | Query Anycast EIP details |
| ListAnycastEipAddresses | Read | Query Anycast EIP list |
| ListAnycastPopLocations | Read | Query Anycast access point locations |
| ChangeResourceGroup | Write | Change the owning resource group |
| TagResources | Write | Tag resources |
| UnTagResources | Write | Remove tags |
| ListTagResources | Read | Query tags |

---

## 12. CDT (ServiceName=`CDT`, Cloud Data Transfer)

| Event Name | Type | Description |
|------------|------|-------------|
| OpenCdtService | Write | Activate the CDT service |
| CloseCdtService | Write | Close the CDT service |
| GetCdtServiceStatus | Read | Query CDT service status |
| ListCdtInternetTraffic | Read | Query internet traffic details |

---

## 13. Smartag (ServiceName=`Smartag`, Smart Access Gateway)

### 13.1 Gateway instances

| Event Name | Type | Description |
|------------|------|-------------|
| CreateSmartAccessGateway | Write | Create a Smart Access Gateway |
| DeleteSmartAccessGateway | Write | Delete a Smart Access Gateway |
| ModifySmartAccessGateway | Write | Modify Smart Access Gateway configuration |
| UpgradeSmartAccessGateway | Write | Upgrade the SAG version |
| BindSmartAccessGateway | Write | Bind a SAG to a CCN |
| UnbindSmartAccessGateway | Write | Unbind a SAG from a CCN |
| DescribeSmartAccessGateways | Read | Query SAG list |
| DescribeBindableSmartAccessGateways | Read | Query bindable SAG list |
| EnableSmartAgDpi | Write | Enable DPI deep packet inspection |
| DisableSmartAgDpi | Write | Disable DPI |

### 13.2 Cloud Connect Network CCN

| Event Name | Type | Description |
|------------|------|-------------|
| CreateCloudConnectNetwork | Write | Create a Cloud Connect Network (CCN) |
| DeleteCloudConnectNetwork | Write | Delete a CCN |
| ModifyCloudConnectNetwork | Write | Modify a CCN |
| DescribeCloudConnectNetworks | Read | Query CCN list |
| GrantSagInstanceToCcn | Write | Grant a SAG to join a CCN (cross-account) |
| RevokeSagInstanceFromCcn | Write | Revoke a cross-account grant |
| GrantInstanceToCbn | Write | Grant a CCN to join a CEN |
| RevokeInstanceFromCbn | Write | Revoke the grant for a CCN to join a CEN |

### 13.3 ACL and QoS

| Event Name | Type | Description |
|------------|------|-------------|
| CreateACL | Write | Create an ACL |
| DeleteACL | Write | Delete an ACL |
| ModifyACLAttribute | Write | Modify ACL attributes |
| DescribeACLs | Read | Query ACL list |
| DescribeACLAttribute | Read | Query ACL details |
| AddACLRule | Write | Add an ACL rule |
| ModifyACLRule | Write | Modify an ACL rule |
| DeleteACLRule | Write | Delete an ACL rule |
| DescribeACLRules | Read | Query ACL rules |
| AssociateACL | Write | Associate an ACL with a SAG |
| UnassociateACL | Write | Disassociate an ACL |
| CreateQos | Write | Create a QoS policy |
| DeleteQos | Write | Delete a QoS policy |
| ModifyQos | Write | Modify a QoS policy |
| DescribeQoses | Read | Query QoS list |
| CreateQosCar | Write | Create a QoS rate-limiting rule |
| DeleteQosCar | Write | Delete a QoS rate-limiting rule |
| ModifyQosCar | Write | Modify a QoS rate-limiting rule |
| DescribeQosCars | Read | Query QoS rate-limiting rules |
| CreateQosPolicy | Write | Create a QoS five-tuple policy |
| DeleteQosPolicy | Write | Delete a QoS policy |
| ModifyQosPolicy | Write | Modify a QoS policy |
| DescribeQosPolicies | Read | Query QoS policies |

### 13.4 Routing and network configuration

| Event Name | Type | Description |
|------------|------|-------------|
| AddNetworkLinkToSmartAccessGateway | Write | Add a network link to a SAG |
| RemoveNetworkLinkFromSmartAccessGateway | Write | Remove a network link from a SAG |
| CreateSmartAccessGatewayClientUser | Write | Create a SAG-APP client user |
| ModifySmartAccessGatewayClientUser | Write | Modify a SAG-APP client user |
| DeleteSmartAccessGatewayClientUser | Write | Delete a SAG-APP client user |
| DescribeSmartAccessGatewayClientUsers | Read | Query SAG-APP client users |
| AddDnatEntry | Write | Add a DNAT entry |
| DeleteDnatEntry | Write | Delete a DNAT entry |
| DescribeDnatEntries | Read | Query DNAT entries |
| AddSnatEntry | Write | Add a SNAT entry |
| DeleteSnatEntry | Write | Delete a SNAT entry |
| DescribeSnatEntries | Read | Query SNAT entries |
| CreateFlowlog | Write | Create a flow log |
| DeleteFlowlog | Write | Delete a flow log |
| ActiveFlowLog | Write | Start a flow log |
| DeactiveFlowLog | Write | Stop a flow log |
| DescribeFlowlogs | Read | Query flow logs |

---

## 14. flowbag (ServiceName=`flowbag`, Shared Flow Bag)

| Event Name | Type | Description |
|------------|------|-------------|
| CreateFlowBag | Write | Purchase a shared flow bag |
| RefundFlowBag | Write | Refund a shared flow bag |
| DescribeFlowBags | Read | Query flow bag list |
| DescribeFlowBagInstanceUsage | Read | Query flow bag usage |
| ModifyFlowBagAttribute | Write | Modify flow bag attributes |

---

## 15. CMN (ServiceName=`CMN`, Cloud Network Management)

| Event Name | Type | Description |
|------------|------|-------------|
| DescribeCmnDevices | Read | Query cloud network management device list |
| DescribeCmnDeviceDetail | Read | Query device details |
| DescribeCmnNetworkTopo | Read | Query network topology |
| DescribeCmnMonitoringData | Read | Query device monitoring data |

---

## Appendix A: Naming Rules and Reading Tips

Event names follow API PascalCase naming and can be decomposed into "verb + resource":

**Write-operation verbs**

| Verb | Meaning |
|------|---------|
| Create | Create a resource |
| Delete / Release / Terminate | Delete, release or terminate a resource |
| Modify / Update / Set | Modify attributes/configuration |
| Add / Remove | Add or remove sub-objects (e.g. ACL entries, backend servers) |
| Associate / Attach / Bind | Associate/bind a resource |
| Unassociate / Dissociate / Detach / Unbind | Disassociate/unbind |
| Enable / Disable | Enable/disable a feature |
| Active / Deactive | Start/stop (mostly used for flow logs) |
| Publish / Unpublish / Withdraw | Publish/withdraw (e.g. publishing routes to CEN) |
| Grant / Revoke | Grant/revoke permissions (cross-account scenarios) |
| Upgrade / Convert / Move / Change | Upgrade, convert or migrate |
| Accept / Reject / Confirm / Cancel | Accept, reject, confirm or cancel (peering/physical connection applications) |

**Read-operation verbs**

| Verb | Meaning |
|------|---------|
| Describe | Legacy query APIs (common in VPC/CLB/CEN traditional APIs) |
| Get | Query details of a single resource |
| List | New-generation query APIs (common in ALB/NLB/VpcPeer/PrivateLink/TR) |
| Query | Specific queries (rare) |

**Identifying products by resource prefix (within the Vpc ServiceName)**

| Prefix | Product |
|--------|---------|
| `Vpc`, `VSwitch`, `RouteTable`, `RouteEntry`, `Ipv4Gateway`, `Ipv6Gateway`, `NetworkAcl`, `Dhcp`, `FlowLog`, `HaVip`, `PrefixList`, `PublicIpAddressPool`, `GatewayEndpoint` | VPC core service |
| `Eip`, `EipAddress`, `EipSegment` | EIP |
| `Nat`, `Snat`, `Forward`, `FullNat` | NAT Gateway |
| `Vpn`, `Ssl`, `Ipsec`, `CustomerGateway`, `Gre` | VPN |
| `CommonBandwidthPackage` | Common Bandwidth |
| `PhysicalConnection`, `VirtualBorderRouter`, `RouterInterface`, `Bgp`, `ExpressCloudConnection` | Express Connect |
| `TrafficMirror` | Traffic Mirroring |
| `IPv6Translator` | IPv6 Translation Service |

---

## Appendix B: Query Suggestions

**B.1 Exact query for a single event**

```
--lookup-attribute EventName=ReleaseEipAddress
```

**B.2 Fetch by ServiceName, then filter in a second pass**

```
--lookup-attribute ServiceName=Vpc
# After getting the results, filter by event name prefix (Eip / Nat / Vpn / SnatEntry / ForwardEntry) to isolate the target sub-product
```

**B.3 By resource type**

```
--lookup-attribute ResourceType=ACS::VPC::NatGateway
```

**B.4 By specific resource instance**

```
--lookup-attribute ResourceName=eip-bp1234567890abcde
--lookup-attribute ResourceName=ngw-bp1x2y3z4
```

**B.5 Write operations only**

```
--lookup-attribute EventRW=Write
```

**B.6 Read operations only**

```
--lookup-attribute EventRW=Read
```

**B.7 Handling unlisted events**

If the target event name is not in this catalog, run a broad query without EventName (only ServiceName + time range), then filter manually from the results:

```bash
python scripts/lookup_events.py \
  --uid <UID> \
  --lookup-attribute ServiceName=Vpc \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-02T00:00:00Z \
  --max-results 50 --json
```
