# AWS Networking Services → Alibaba Cloud Mapping

## VPC (Virtual Private Cloud)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_vpc` | `alicloud_vpc` | Low | DNS enabled by default in Alibaba |
| `aws_subnet` | `alicloud_vswitch` | Low | Zone assignment: `availability_zone` → `zone_id` |
| `aws_security_group` | `alicloud_security_group` | Low | Separate rule resources in Alibaba |
| `aws_security_group_rule` | `alicloud_security_group_rule` | Low | Port range format: `80` → `80/80` |
| `aws_vpc_security_group_ingress_rule` | `alicloud_security_group_rule` (type=ingress) | Low | Standalone ingress rule resource |
| `aws_vpc_security_group_egress_rule` | `alicloud_security_group_rule` (type=egress) | Low | Standalone egress rule resource |
| `aws_internet_gateway` | See IGW + route pattern below | Medium | Alibaba Cloud has no standalone IGW resource; internet egress is modeled with NAT Gateway/EIP/SNAT/route when source routes traffic through IGW |
| `aws_route_table` | `alicloud_route_table` | Low | Similar configuration |
| `aws_route_table_association` | `alicloud_route_table_attachment` | Low | `subnet_id` → `vswitch_id` |
| `aws_network_acl` | `alicloud_network_acl` | Low | Similar rule structure |
| `aws_network_acl_rule` | `alicloud_network_acl_entries` | Low | Entries defined in single resource |
| `aws_network_interface` | `alicloud_ecs_network_interface` | Low | Similar configuration |
| `aws_flow_log` | `alicloud_vpc_flow_log` | Low | Delivers to SLS instead of CloudWatch |
| `aws_vpc_dhcp_options` | `alicloud_vpc_dhcp_options_set` | Low | Requires separate attachment resource |
| `aws_vpc_ipv4_cidr_block_association` | `alicloud_vpc_ipv4_cidr_block` | Low | Secondary CIDR block |
| `aws_ec2_transit_gateway` | `alicloud_cen_transit_router` | Medium | Part of CEN; connection-based pricing |
| `aws_vpc_peering_connection` | `alicloud_vpc_peer_connection` | Low | Cross-AZ free in Alibaba |
| `aws_default_vpc` | No equivalent | N/A | Alibaba Cloud has no default VPC concept |
| `aws_default_subnet` | No equivalent | N/A | Alibaba Cloud has no default VSwitch concept |
| `aws_default_security_group` | No equivalent | N/A | Alibaba Cloud has no default SG concept |

### IGW + Default Route Pattern

Alibaba Cloud has no standalone Internet Gateway resource. Do not map `aws_internet_gateway` to a target resource by itself. Interpret it together with routes, public IPs, NAT gateways, load balancers, and subnet intent.

When the source has `aws_route` with `destination_cidr_block = "0.0.0.0/0"` pointing to an Internet Gateway (`gateway_id = aws_internet_gateway.xxx.id`), use these conditional mappings:

1. Public ingress resources: if instances or load balancers have public IPs, map the public entry point to `alicloud_eip_address` + `alicloud_eip_association`, public `alicloud_alb_load_balancer`, public `alicloud_nlb_load_balancer`, or public `alicloud_slb_load_balancer` as appropriate.
2. Private subnet outbound access: if the source uses `aws_nat_gateway`, map NAT to `alicloud_nat_gateway` + EIP association + `alicloud_snat_entry`.
3. Route tables: create `alicloud_route_entry` only when a concrete Alibaba next hop exists, such as `NatGateway`, `NetworkInterface`, `VpcPeer`, `Attachment`, or another supported next hop. Do not invent a route entry for an Internet Gateway.

### Required Target Properties and Forbidden Mappings

When Phase 2 maps internet connectivity, write the selected target pattern into `target_resources[]` based on source intent. Do not collapse private subnet NAT requirements to EIP-only, and do not force NAT Gateway for public ingress-only subnets.

| Source Pattern | Target Resources | Required `target_resources[].properties` | Forbidden |
|----------------|------------------|-------------------------------------------|-----------|
| `aws_internet_gateway` only | No direct target resource | Record that Alibaba Cloud has no standalone IGW resource | `alicloud_nat_gateway` without NAT intent |
| Public subnet route to IGW plus public instance/LB | EIP association or public load balancer resources | Public address type or EIP binding on the resource that needs internet ingress | Synthetic `alicloud_route_entry` to IGW |
| `aws_nat_gateway` plus private subnet default route | `alicloud_nat_gateway`, `alicloud_eip_address`, `alicloud_eip_association`, `alicloud_snat_entry`, optional `alicloud_route_entry` when required | NAT Gateway depends on VPC/VSwitch; EIP binds to NAT Gateway; SNAT entry references private VSwitches needing outbound internet; route entry uses `nexthop_type = "NatGateway"` only when explicitly generated | EIP-only route for private subnet outbound access, `nexthop_type = "Eip"` for NAT semantics |

---

## NAT Gateway & EIP

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Pricing Difference |
|--------------|----------------------|---------------------|-------------------|
| `aws_nat_gateway` | `alicloud_nat_gateway` (Internet/VPC) | Low | Instance: $0.059/hr (AWS) vs $0.043/hr (Alibaba) |
| - | - | - | Capacity: $0.059/GB data processing (AWS) vs $0.043/CU-hour (Alibaba, pay by max CU) |
| `aws_eip` | `alicloud_eip_address` | Low | Retention: $0.005/hr (AWS) vs $0.006/hr (Alibaba) |
| `aws_eip_association` | `alicloud_eip_association` | Low | Free (AWS) vs $0.149 per association exceeding daily limit (Alibaba) |
| - | `alicloud_snat_entry` | Medium | Explicit SNAT per VSwitch (no AWS equivalent) |
| - | `alicloud_forward_entry` | Medium | DNAT rule per port (no direct AWS equivalent; AWS uses NLB/ALB) |

### EIP & Bandwidth Options

**EIP Pricing Models**:
- **Pay-by-Data-Transfer**: Retention fee ($0.006/hr) + Internet data transfer fee (tiered, BGP/BGP Pro)
- **Pay-by-Bandwidth**: Retention fee ($0.006/hr) + Bandwidth fee (tiered with 5 Mbit/s threshold)
- **Subscription**: Bandwidth fee only (monthly)

**Additional Options** (Alibaba Cloud):
- **Internet Shared Bandwidth**: Shared bandwidth pool across multiple EIPs
- **Data Transfer Plan** (Int'l only): Subscription-based data transfer package
- **IP Address Pool**: $0.007/IP-hour retention fee

**AWS Comparison**:
- Single pricing model: $0.005/hr per EIP
- Data transfer charged separately (to Internet, tiered)
- BYOIP (Amazon-provided contiguous IPv4 block): $0.008/IP-hour

---

## Load Balancer (SLB)

> **Note**: AWS uses a single resource `aws_lb` with `load_balancer_type` to distinguish ALB/NLB/GWLB. Alibaba Cloud uses separate resource types per load balancer type (`alicloud_alb_*`, `alicloud_nlb_*`, `alicloud_gwlb_*`, `alicloud_slb_*`). The same 1-to-many split applies to associated resources (server group, listener, etc.).

### Load Balancer Instance

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_lb` (`load_balancer_type = "application"`) | `alicloud_alb_load_balancer` | Medium | LCU-based pricing |
| `aws_lb` (`load_balancer_type = "network"`) | `alicloud_nlb_load_balancer` | Medium | LCU-based pricing |
| `aws_lb` (`load_balancer_type = "gateway"`) | `alicloud_gwlb_load_balancer` | Medium | LCU-based pricing |
| `aws_elb` | `alicloud_slb_load_balancer` | Low | Classic; Instance + LCU pricing |

### Required Target Properties and Forbidden Mappings

When Phase 2 maps load balancers, write the selected generation into `target_resources[].type` and the decisive arguments into `target_resources[].properties`:

| Source Pattern | Target Resource | Required `target_resources[].properties` | Forbidden |
|----------------|----------------|-------------------------------------------|-----------|
| `aws_lb` with `load_balancer_type = "application"` | `alicloud_alb_load_balancer` | `address_type`, `zone_mappings` with at least 2 VSwitches when HA/public mapping is required | `alicloud_slb_load_balancer`, `alicloud_nlb_load_balancer` |
| `aws_lb` with `load_balancer_type = "network"` | `alicloud_nlb_load_balancer` | `address_type`, zone/VSwitch mapping fields required by provider docs | `alicloud_slb_load_balancer`, `alicloud_alb_load_balancer` |
| `aws_elb` classic | `alicloud_slb_load_balancer` | `address_type`, listener/server-group properties from source | `alicloud_alb_load_balancer` unless source is being intentionally upgraded to L7 ALB and assessment documents it |

If the source is internet-facing, set `address_type` to the Alibaba Cloud public/Internet value required by the selected resource. Do not leave public/private load balancer selection implicit.

### Server Group / Target Group

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_lb_target_group` (for ALB) | `alicloud_alb_server_group` | Medium | |
| `aws_lb_target_group` (for NLB) | `alicloud_nlb_server_group` | Medium | |
| `aws_lb_target_group` (for GWLB) | `alicloud_gwlb_server_group` | Medium | |
| `aws_lb_target_group_attachment` | `alicloud_nlb_server_group_server_attachment` | Low | NLB uses explicit attachment |

### Listener

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_lb_listener` (for ALB) | `alicloud_alb_listener` | Medium | |
| `aws_lb_listener` (for NLB) | `alicloud_nlb_listener` | Medium | |
| `aws_lb_listener` (for GWLB) | `alicloud_gwlb_listener` | Medium | |
| `aws_lb_listener` (for CLB) | `alicloud_slb_listener` | Low | |
| `aws_lb_listener_rule` | `alicloud_alb_rule` | Medium | ALB only |
| `aws_lb_listener_certificate` | `alicloud_alb_listener_additional_certificate_attachment` | Low | ALB only |

### Global Accelerator

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_globalaccelerator_accelerator` | `alicloud_ga_accelerator` | High | CU-based pricing |
| `aws_globalaccelerator_listener` | `alicloud_ga_listener` | High | |
| `aws_globalaccelerator_endpoint_group` | `alicloud_ga_endpoint_group` | High | |

**Pricing Comparison**:

| Load Balancer Type | AWS | Alibaba Cloud | Notes |
|-------------------|-----|---------------|-------|
| **ALB** | Instance: $0.0252/hr<br>LCU: $0.008/LCU-hour<br>+ Mutual TLS: $0.0056/hr per Trust Store | Basic: $0.007/hr<br>Standard: $0.021/hr<br>WAF-enabled: $0.035/hr<br>LCU: $0.007/LCU-hour | Pay by maximum LCU |
| **NLB** | Instance: $0.0252/hr<br>NLCU: $0.006/NLCU-hour | Instance: $0.02/hr<br>LCU: $0.005/LCU-hour | Pay by maximum LCU/NLCU |
| **CLB (Classic)** | Instance: $0.028/hr<br>Data processing: $0.008/GB | Instance: $0.021/hr<br>Pay-by-LCU or Pay-by-specification | Outdated, migration recommended |
| **GWLB** | Instance: $0.0252/hr<br>GLCU: $0.004/GLCU-hour | Instance: $0.014/hr<br>LCU: $0.004/LCU-hour | Pay by maximum LCU/GLCU |

**Global Accelerator (GA)**:

| Feature | AWS | Alibaba Cloud |
|---------|-----|---------------|
| Instance fee | $0.025/hr | $0.02/hr (L4/L7), $15/month (subscription) |
| Capacity unit | - | $0.057/CU-hour (pay by max CU, ~1GB≈1CU, not charged for L3 basic) |
| Internet data transfer | DT premium fee + EC2 data transfer out (tiered) | Internet data transfers fee (BGP/BGP Pro, tiered) |
| Cross-region transfer | Inter-region fee | Pay-by-dominant-data-transfer (CDT Gold/Platinum) |
| Protocol support | L4 only | L3/L4/L7 |
| Source | On AWS only | On/non Alibaba Cloud |

---

## DNS (Route 53)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_route53_zone` | `alicloud_alidns_domain` | Medium | Domain registration |
| `aws_route53_record` | `alicloud_alidns_record` | Medium | `name` (FQDN) vs `rr` (subdomain) |

---

## VPN & Direct Connect

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_vpn_gateway` | `alicloud_vpn_gateway` | Low | IPsec site-to-site |
| `aws_vpn_connection` | `alicloud_vpn_connection` | Low | Per-connection fee (AWS) vs instance fee (Alibaba) |
| `aws_vpn_connection_route` | `alicloud_vpn_route_entry` | Low | Static route for VPN |
| `aws_ec2_client_vpn_endpoint` | `alicloud_ssl_vpn_server` | Medium | SSL client access |
| `aws_ec2_client_vpn_authorization_rule` | `alicloud_ssl_vpn_client_cert` | Medium | Client authorization model differs |
| `aws_vpn_gateway_attachment` | `alicloud_vpn_gateway_vpn_attachment` | Low | VPN to VPC binding |
| `aws_customer_gateway` | `alicloud_vpn_customer_gateway` | Low | Customer gateway device |
| `aws_dx_connection` | `alicloud_express_connect_physical_connection` | High | Dedicated/hosted connection |
| `aws_dx_gateway` | `alicloud_express_connect_router_express_connect_router` | High | Express Connect Router (ECR) |
| `aws_dx_private_virtual_interface` | `alicloud_express_connect_virtual_border_router` | High | VBR replaces virtual interface concept |

### Site-to-Site VPN Pricing

**Scenario 1: Bind to VPC directly** (without Transit Router):

| Component | AWS | Alibaba Cloud |
|-----------|-----|---------------|
| Instance fee | - | $0.087/hr + Connection bandwidth fee |
| Connection fee | $0.05/connection-hour | - |
| IP address fee | - | - |
| Data transfer | to Internet (tiered) | $0.117/GB |

**Scenario 2: Enterprise-grade networking** (with Transit Router/Gateway):

| Component | AWS (TGW) | Alibaba Cloud (TR) |
|-----------|-----------|-------------------|
| IPsec connection fee | - | $0.05/hr per connection (China mainland)<br>$0.06/hr per connection (outside China mainland, SAU Riyadh: $0.06/hr) |
| TR/TGW connection fee | $0.07/hr per connection | $0.05/hr per connection (China mainland)<br>$0.06/hr per connection (outside China mainland) |
| Data processing fee | $0.02/GB | $0.02/GB |
| Internet data transfer | to Internet (tiered) | $0.117/GB |

### Client VPN (SSL-VPN) Pricing

| Component | AWS | Alibaba Cloud |
|-----------|-----|---------------|
| Endpoint/Instance fee | $0.15/hr per endpoint | $0.087/hr + Connection bandwidth fee |
| Connection fee | $0.05/hr per connection | Specification fee (see pricing page) |
| Data transfer | to Internet (tiered) | $0.117/GB |

**Notes**:
- Alibaba SSL-VPN: Pay-as-you-go not available in domestic site; subscription not available in Int'l site
- AWS charges per endpoint and per connection
- Alibaba charges specification-based fees

---

## PrivateLink / VPC Endpoint

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_vpc_endpoint` (Interface) | `alicloud_privatelink_vpc_endpoint` | Medium | Interface endpoint type |
| `aws_vpc_endpoint` (Gateway) | `alicloud_vpc_gateway_endpoint` | Medium | Gateway endpoint (S3/DynamoDB → OSS/OTS) |
| `aws_vpc_endpoint` (GWLB) | `alicloud_gwlb_listener` | Medium | GWLB endpoint concept differs |
| `aws_vpc_endpoint` (Resource) | No equivalent | N/A | AWS only feature |
| `aws_vpc_endpoint_service` | `alicloud_privatelink_vpc_endpoint_service` | Medium | Service provider side |
| `aws_vpc_endpoint_connection_accepter` | `alicloud_privatelink_vpc_endpoint_connection` | Medium | Connection management |
| - | `alicloud_privatelink_vpc_endpoint_zone` | Medium | Zone configuration (Alibaba-specific) |
| - | `alicloud_privatelink_vpc_endpoint_service_resource` | Medium | Service resource binding (Alibaba-specific) |

### Pricing Comparison

**Endpoint Instance Fee**:

| Endpoint Type | AWS | Alibaba Cloud |
|--------------|-----|---------------|
| Interface endpoint | $0.013/hr | $0.01/hr |
| GWLB endpoint | $0.013/hr | $0.013/hr |
| Resource endpoint | $0.026/hr | - (not available) |

**Data Transfer Fee** (charged for both inbound and outbound):

| Endpoint Type | AWS | Alibaba Cloud |
|--------------|-----|---------------|
| Interface endpoint | ≤1 PB: $0.01/GB<br>(1,5] PB: $0.006/GB<br>> 5 PB: $0.004/GB | $0.01/GB (flat rate) |
| GWLB endpoint | $0.0035/GB | $0.0035/GB (same) |
| Resource endpoint | Same tiered as Interface | - |

**Cross-Region Connectivity**:
- AWS: $0.05/region per hour
- Alibaba Cloud: Not separately charged (included in data transfer)

**Payer**:
- AWS: Service consumer only
- Alibaba Cloud: Service consumer or service provider (configurable)

---

## Data Transfer & CDT

### Overview

| Transfer Type | AWS | Alibaba Cloud | Notes |
|--------------|-----|---------------|-------|
| **Intra-region** | Inbound: $0.01/GB<br>Outbound: $0.01/GB | Free (within same region) | Alibaba: Cross-AZ free within region |
| **Cross-region** | Inter-region fee (region-pair based) | Pay-by-dominant-data-transfer<br>(CDT Gold/Platinum or Cross-border Gold) | Two pricing options in Alibaba |
| **Internet** | To Internet (tiered by volume) | BGP/BGP Pro tiered pricing | See detailed comparison below |

### Internet Data Transfer - Tiered Pricing

**Asia Pacific (Singapore)**:

| Tier | AWS Pricing | Alibaba Cloud Pricing | Notes |
|------|------------|---------------------|-------|
| 0-10 TB | $0.12/GB | $0.10/GB | Alibaba: 200 GB free<br>AWS: 100 GB free |
| 10-50 TB | $0.085/GB | $0.07/GB | 17.6% cheaper |
| 50-150 TB | $0.082/GB | $0.065/GB | 20.7% cheaper |
| > 150 TB | $0.08/GB | $0.055/GB | 31.3% cheaper |

**Europe (Frankfurt)**:

| Tier | AWS Pricing | Alibaba Cloud Pricing | Notes |
|------|------------|---------------------|-------|
| 0-10 TB | $0.09/GB | $0.074/GB | Alibaba: 200 GB free<br>AWS: 100 GB free |
| 10-50 TB | $0.085/GB | $0.065/GB | 23.5% cheaper |
| 50-150 TB | $0.07/GB | $0.060/GB | 14.3% cheaper |
| > 150 TB | $0.05/GB | $0.040/GB | 20% cheaper |

**North America (US)**:

| Tier | AWS Pricing | Alibaba Cloud Pricing | Notes |
|------|------------|---------------------|-------|
| 0-10 TB | $0.09/GB | $0.074/GB | Alibaba: 200 GB free<br>AWS: 100 GB free |
| 10-50 TB | $0.085/GB | $0.065/GB | 23.5% cheaper |
| 50-150 TB | $0.07/GB | $0.060/GB | 14.3% cheaper |
| > 150 TB | $0.05/GB | $0.040/GB | 20% cheaper |

**Key Observations**:
- **Free tier**: Alibaba Cloud offers 200 GB free vs AWS 100 GB free
- **Price advantage**: Alibaba Cloud is 14-31% cheaper across all tiers
- **Regional consistency**: Europe and US pricing identical for both providers
- **Highest cost**: Singapore region for both providers

---

## Transit Router (TR) / Transit Gateway (TGW)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_ec2_transit_gateway` | `alicloud_cen_transit_router` | Medium | Part of CEN; requires `alicloud_cen_instance` |
| `aws_ec2_transit_gateway_vpc_attachment` | `alicloud_cen_transit_router_vpc_attachment` | Medium | VPC attachment |
| `aws_ec2_transit_gateway_peering_attachment` | `alicloud_cen_transit_router_peer_attachment` | Medium | Cross-region peering |
| `aws_ec2_transit_gateway_route_table` | `alicloud_cen_transit_router_route_table` | Medium | Route table |
| `aws_ec2_transit_gateway_route` | `alicloud_cen_transit_router_route_entry` | Medium | Route entry |
| `aws_ec2_transit_gateway_route_table_association` | `alicloud_cen_transit_router_route_table_association` | Medium | Route table association |
| `aws_ec2_transit_gateway_route_table_propagation` | `alicloud_cen_transit_router_route_table_propagation` | Medium | Route propagation |

### Pricing Comparison

| Component | AWS (TGW) | Alibaba Cloud (TR) |
|-----------|-----------|-------------------|
| **Connection fee** | $0.07/hr per connection | China mainland: $0.05/hr per connection<br>Outside China mainland: $0.06/hr per connection |
| **Data processing fee** | $0.02/GB | $0.02/GB (same) |
| **Cross-region data transfer** | Inter-region fee (region-pair based) | Pay-by-dominant-data-transfer<br>(CDT Gold/Platinum or Cross-border Gold) |

---

## Migration Checklist

### Pre-Migration
- [ ] Document VPC CIDR blocks
- [ ] Inventory all subnets and availability zones
- [ ] List security group rules
- [ ] Document routing tables
- [ ] Identify NAT Gateways and EIPs
- [ ] List load balancers and target groups
- [ ] Export DNS records

### During Migration
- [ ] Create VPC with same CIDR
- [ ] Create VSwitches in appropriate zones
- [ ] Migrate security group rules
- [ ] Set up NAT Gateway and SNAT entries
- [ ] Create load balancers
- [ ] Migrate DNS records

### Post-Migration
- [ ] Verify network connectivity
- [ ] Test security group rules
- [ ] Validate NAT Gateway routing
- [ ] Test load balancer health checks
- [ ] Update DNS TTLs for quick rollback
- [ ] Monitor network performance
