# Network Migration Reference

Complete guide for setting up Alibaba Cloud networking during AWS migration.

## 1. VPC Setup

Create VPC and VSwitch infrastructure for migration.

### 1.1 Create VPC

```bash
aliyun vpc CreateVpc \
  --RegionId <region> \
  --CidrBlock 10.0.0.0/8 \
  --VpcName migration-vpc \
  --Description "VPC for AWS migration" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `RegionId` | Yes | Region where VPC is created | `cn-hangzhou` |
| `CidrBlock` | Yes | VPC CIDR block (must be /8 to /24) | `10.0.0.0/8` |
| `VpcName` | No | VPC name | `migration-vpc` |
| `Description` | No | VPC description | `VPC for AWS migration` |

**Response:**
```json
{
  "VpcId": "vpc-bp1abc123def456789",
  "VRouterId": "vrt-bp1abc123def456789",
  "RouteTableId": "vtb-bp1abc123def456789"
}
```

### 1.2 Create VSwitch

```bash
aliyun vpc CreateVSwitch \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --ZoneId <zone-id> \
  --CidrBlock 10.0.0.0/24 \
  --VSwitchName migration-vsw \
  --Description "VSwitch for migration" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `RegionId` | Yes | Region where VSwitch is created | `cn-hangzhou` |
| `VpcId` | Yes | VPC ID from CreateVpc | `vpc-bp1abc123def456789` |
| `ZoneId` | Yes | Availability zone | `cn-hangzhou-i` |
| `CidrBlock` | Yes | VSwitch CIDR (must be within VPC CIDR) | `10.0.0.0/24` |
| `VSwitchName` | No | VSwitch name | `migration-vsw` |
| `Description` | No | VSwitch description | `VSwitch for migration` |

**Response:**
```json
{
  "VSwitchId": "vsw-bp1abc123def456789"
}
```

### 1.3 Create Multiple VSwitches (Multi-AZ)

For high availability, create VSwitches in multiple zones:

```bash
# VSwitch in Zone A
aliyun vpc CreateVSwitch \
  --RegionId cn-hangzhou \
  --VpcId vpc-bp1abc123def456789 \
  --ZoneId cn-hangzhou-i \
  --CidrBlock 10.0.1.0/24 \
  --VSwitchName migration-vsw-a \
  --user-agent AlibabaCloud-Agent-Skills

# VSwitch in Zone B
aliyun vpc CreateVSwitch \
  --RegionId cn-hangzhou \
  --VpcId vpc-bp1abc123def456789 \
  --ZoneId cn-hangzhou-j \
  --CidrBlock 10.0.2.0/24 \
  --VSwitchName migration-vsw-b \
  --user-agent AlibabaCloud-Agent-Skills
```

### 1.4 Describe VPC

```bash
aliyun vpc DescribeVpcs \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 1.5 Describe VSwitches

```bash
aliyun vpc DescribeVSwitches \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 1.6 Terraform Alternative for VPC and VSwitch

```hcl
resource "alicloud_vpc" "migration" {
  vpc_name   = "<vpc-name>"
  cidr_block = "<cidr-block>"
}

resource "alicloud_vswitch" "migration" {
  vpc_id       = alicloud_vpc.migration.id
  cidr_block   = "<vswitch-cidr-block>"
  zone_id      = "<zone-id>"
  vswitch_name = "<vswitch-name>"
}

resource "alicloud_security_group" "migration" {
  name   = "<security-group-name>"
  vpc_id = alicloud_vpc.migration.id
}

resource "alicloud_security_group_rule" "ingress_ssh" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "22/22"
  cidr_ip           = "0.0.0.0/0"
  security_group_id = alicloud_security_group.migration.id
  priority          = 1
}

resource "alicloud_security_group_rule" "ingress_http" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "80/80"
  cidr_ip           = "0.0.0.0/0"
  security_group_id = alicloud_security_group.migration.id
  priority          = 1
}

resource "alicloud_security_group_rule" "ingress_https" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "443/443"
  cidr_ip           = "0.0.0.0/0"
  security_group_id = alicloud_security_group.migration.id
  priority          = 1
}
```

## 2. Security Group

Create and configure security groups for migrated ECS instances.

### 2.1 Create Security Group

```bash
aliyun ecs CreateSecurityGroup \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --SecurityGroupName migration-sg \
  --Description "Security group for migrated ECS" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "SecurityGroupId": "sg-bp1abc123def456789"
}
```

### 2.2 Ingress Rules (Allow Inbound Traffic)

**Allow SSH (Linux):**
```bash
aliyun ecs AuthorizeSecurityGroup \
  --RegionId <region> \
  --SecurityGroupId <security-group-id> \
  --IpProtocol tcp \
  --PortRange 22/22 \
  --SourceCidrIp 0.0.0.0/0 \
  --Description "Allow SSH" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Allow RDP (Windows):**
```bash
aliyun ecs AuthorizeSecurityGroup \
  --RegionId <region> \
  --SecurityGroupId <security-group-id> \
  --IpProtocol tcp \
  --PortRange 3389/3389 \
  --SourceCidrIp 0.0.0.0/0 \
  --Description "Allow RDP" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Allow HTTP:**
```bash
aliyun ecs AuthorizeSecurityGroup \
  --RegionId <region> \
  --SecurityGroupId <security-group-id> \
  --IpProtocol tcp \
  --PortRange 80/80 \
  --SourceCidrIp 0.0.0.0/0 \
  --Description "Allow HTTP" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Allow HTTPS:**
```bash
aliyun ecs AuthorizeSecurityGroup \
  --RegionId <region> \
  --SecurityGroupId <security-group-id> \
  --IpProtocol tcp \
  --PortRange 443/443 \
  --SourceCidrIp 0.0.0.0/0 \
  --Description "Allow HTTPS" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Allow ICMP (Ping):**
```bash
aliyun ecs AuthorizeSecurityGroup \
  --RegionId <region> \
  --SecurityGroupId <security-group-id> \
  --IpProtocol icmp \
  --PortRange -1/-1 \
  --SourceCidrIp 0.0.0.0/0 \
  --Description "Allow ICMP" \
  --user-agent AlibabaCloud-Agent-Skills
```

### 2.3 Egress Rules (Allow Outbound Traffic)

By default, all outbound traffic is allowed. To restrict:

```bash
aliyun ecs AuthorizeSecurityGroupEgress \
  --RegionId <region> \
  --SecurityGroupId <security-group-id> \
  --IpProtocol tcp \
  --PortRange 443/443 \
  --DestCidrIp 0.0.0.0/0 \
  --Description "Allow HTTPS outbound" \
  --user-agent AlibabaCloud-Agent-Skills
```

### 2.4 Describe Security Group Rules

```bash
aliyun ecs DescribeSecurityGroupAttribute \
  --RegionId <region> \
  --SecurityGroupId <security-group-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

## 3. VPN Gateway

Set up VPN Gateway for hybrid connectivity during migration.

### 3.1 Create VPN Gateway

```bash
aliyun vpc CreateVpnGateway \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --Bandwidth <bandwidth-mbps> \
  --VpnGatewayName migration-vpngw \
  --Description "VPN Gateway for AWS migration" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `RegionId` | Yes | Region | `cn-hangzhou` |
| `VpcId` | Yes | VPC ID | `vpc-bp1abc123def456789` |
| `Bandwidth` | Yes | VPN bandwidth in Mbps (10, 20, 50, 100, 200, 500) | `50` |
| `VpnGatewayName` | No | VPN Gateway name | `migration-vpngw` |
| `Description` | No | Description | `VPN Gateway for AWS migration` |

**Response:**
```json
{
  "VpnGatewayId": "vpn-bp1abc123def456789",
  "OrderInstanceId": "order-bp1abc123def456789"
}
```

### 3.2 Create Customer Gateway (AWS Side)

```bash
aliyun vpc CreateCustomerGateway \
  --RegionId <region> \
  --IpAddress <aws-vpn-ip> \
  --Name aws-customer-gw \
  --Description "AWS VPN Gateway" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `RegionId` | Yes | Region | `cn-hangzhou` |
| `IpAddress` | Yes | Public IP of AWS VPN Gateway | `54.123.45.67` |
| `Name` | No | Customer Gateway name | `aws-customer-gw` |
| `Description` | No | Description | `AWS VPN Gateway` |

**Response:**
```json
{
  "CustomerGatewayId": "cgw-bp1abc123def456789"
}
```

### 3.3 Create IPsec Connection

```bash
aliyun vpc CreateVpnConnection \
  --RegionId <region> \
  --VpnGatewayId <vpn-gateway-id> \
  --CustomerGatewayId <customer-gateway-id> \
  --Name aws-vpn-connection \
  --Description "VPN connection to AWS" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `RegionId` | Yes | Region | `cn-hangzhou` |
| `VpnGatewayId` | Yes | VPN Gateway ID | `vpn-bp1abc123def456789` |
| `CustomerGatewayId` | Yes | Customer Gateway ID | `cgw-bp1abc123def456789` |
| `Name` | No | Connection name | `aws-vpn-connection` |
| `Description` | No | Description | `VPN connection to AWS` |

**Response:**
```json
{
  "VpnConnectionId": "vco-bp1abc123def456789"
}
```

### 3.4 Configure IPsec Parameters

```bash
aliyun vpc ModifyVpnConnectionAttribute \
  --RegionId <region> \
  --VpnConnectionId <vpn-connection-id> \
  --LocalSubnet 10.0.0.0/8 \
  --RemoteSubnet 172.31.0.0/16 \
  --IpsecConfig.IpsecEncAlg AES-128-CBC \
  --IpsecConfig.IpsecAuthAlg SHA1 \
  --IpsecConfig.IpsecLifetime 86400 \
  --IpsecConfig.IpsecPfs group2 \
  --IkeConfig.IkeEncAlg AES-128-CBC \
  --IkeConfig.IkeAuthAlg SHA1 \
  --IkeConfig.IkeLifetime 86400 \
  --IkeConfig.IkePfs group2 \
  --IkeConfig.IkeVersion IKEv1 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 3.5 Describe VPN Connection

```bash
aliyun vpc DescribeVpnConnection \
  --RegionId <region> \
  --VpnConnectionId <vpn-connection-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

## 4. Express Connect

Dedicated connection for high-bandwidth migration.

### 4.1 Create Physical Connection

```bash
aliyun vpc CreatePhysicalConnection \
  --RegionId <region> \
  --AccessPointId <access-point-id> \
  --LineOperator <line-operator> \
  --Bandwidth <bandwidth> \
  --Name migration-express \
  --Description "Express Connect for migration" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Note:** Express Connect requires physical circuit setup through Alibaba Cloud sales team.

### 4.2 Create Virtual Border Router (VBR)

```bash
aliyun vpc CreateVirtualBorderRouter \
  --RegionId <region> \
  --PhysicalConnectionId <physical-connection-id> \
  --VlanId <vlan-id> \
  --LocalGatewayIp <local-gateway-ip> \
  --PeerGatewayIp <peer-gateway-ip> \
  --PeeringSubnetMask <subnet-mask> \
  --Name migration-vbr \
  --user-agent AlibabaCloud-Agent-Skills
```

### 4.3 Create CEN Instance

```bash
aliyun cen CreateCen \
  --CenName migration-cen \
  --Description "CEN for Express Connect" \
  --user-agent AlibabaCloud-Agent-Skills
```

### 4.4 Attach VPC to CEN

```bash
aliyun cen AttachCenChildInstance \
  --CenId <cen-id> \
  --ChildInstanceId <vpc-id> \
  --ChildInstanceType VPC \
  --ChildInstanceRegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 4.5 Attach VBR to CEN

```bash
aliyun cen AttachCenChildInstance \
  --CenId <cen-id> \
  --ChildInstanceId <vbr-id> \
  --ChildInstanceType VBR \
  --ChildInstanceRegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

## 5. CEN (Cloud Enterprise Network)

Multi-region and cross-cloud networking.

### 5.1 Create CEN Instance

```bash
aliyun cen CreateCen \
  --CenName global-migration-cen \
  --Description "Global CEN for multi-region migration" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "CenId": "cen-bp1abc123def456789"
}
```

### 5.2 Attach VPCs to CEN

```bash
aliyun cen AttachCenChildInstance \
  --CenId <cen-id> \
  --ChildInstanceId <vpc-id-1> \
  --ChildInstanceType VPC \
  --ChildInstanceRegionId cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills

aliyun cen AttachCenChildInstance \
  --CenId <cen-id> \
  --ChildInstanceId <vpc-id-2> \
  --ChildInstanceType VPC \
  --ChildInstanceRegionId cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills
```

### 5.3 Publish Routes to CEN

```bash
aliyun cen PublishRouteEntriesToCen \
  --CenId <cen-id> \
  --ChildInstanceId <vpc-id> \
  --ChildInstanceType VPC \
  --ChildInstanceRegionId <region> \
  --RouteTableId <route-table-id> \
  --DestinationCidrBlock 10.0.0.0/8 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 5.5 Describe CEN

```bash
aliyun cen DescribeCens \
  --CenId <cen-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

## 6. DNS Migration

Migrate from Route 53 to Alibaba Cloud DNS.

### 6.1 Export Route 53 Zone

```bash
# Using AWS CLI
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --output json > route53-records.json
```

### 6.2 Create DNS Domain

```bash
aliyun alidns AddDomain \
  --DomainName example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "DomainId": "12345678",
  "DomainName": "example.com"
}
```

### 6.3 Add DNS Records

**A Record:**
```bash
aliyun alidns AddDomainRecord \
  --DomainName example.com \
  --RR @ \
  --Type A \
  --Value <ecs-public-ip> \
  --user-agent AlibabaCloud-Agent-Skills
```

**CNAME Record:**
```bash
aliyun alidns AddDomainRecord \
  --DomainName example.com \
  --RR www \
  --Type CNAME \
  --Value example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

**MX Record:**
```bash
aliyun alidns AddDomainRecord \
  --DomainName example.com \
  --RR @ \
  --Type MX \
  --Value 10 mx.example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

**TXT Record:**
```bash
aliyun alidns AddDomainRecord \
  --DomainName example.com \
  --RR @ \
  --Type TXT \
  --Value "v=spf1 include:spf.example.com ~all" \
  --user-agent AlibabaCloud-Agent-Skills
```

### 6.4 Describe DNS Records

```bash
aliyun alidns DescribeDomainRecords \
  --DomainName example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

### 6.5 Terraform Alternative for DNS Records

```hcl
resource "alicloud_alidns_record" "www" {
  domain_name = "<domain-name>"
  rr          = "<record-prefix>"
  type        = "<record-type>"
  value       = "<record-value>"
  ttl         = <ttl-in-seconds>
}
```

**Example - A Record:**
```hcl
resource "alicloud_alidns_record" "www_a" {
  domain_name = "example.com"
  rr          = "www"
  type        = "A"
  value       = "<ecs-public-ip>"
  ttl         = 600
}
```

**Example - CNAME Record:**
```hcl
resource "alicloud_alidns_record" "www_cname" {
  domain_name = "example.com"
  rr          = "blog"
  type        = "CNAME"
  value       = "www.example.com"
  ttl         = 600
}
```

**Example - MX Record:**
```hcl
resource "alicloud_alidns_record" "mx" {
  domain_name = "example.com"
  rr          = "@"
  type        = "MX"
  value       = "10 mx.example.com"
  ttl         = 600
}
```

**Example - TXT Record:**
```hcl
resource "alicloud_alidns_record" "txt" {
  domain_name = "example.com"
  rr          = "@"
  type        = "TXT"
  value       = "v=spf1 include:spf.example.com ~all"
  ttl         = 600
}
```

### 6.5 Update Name Servers

1. Get Alibaba Cloud DNS name servers:
```bash
aliyun alidns DescribeDomainInfo \
  --DomainName example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

2. Update domain registrar with new name servers

3. Lower TTL on Route 53 records before migration (e.g., 300 seconds)

4. Monitor DNS propagation

## 7. CDN Migration

Migrate from CloudFront to Alibaba Cloud CDN.

### 7.1 Add CDN Domain

```bash
aliyun cdn AddCdnDomain \
  --DomainName www.example.com \
  --SourceType oss \
  --SourceContent <oss-bucket-name>.oss-<region>.aliyuncs.com \
  --Scope global \
  --CertType free \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `DomainName` | Yes | CDN domain name | `www.example.com` |
| `SourceType` | Yes | Origin type: `oss`, `ipaddr`, `domain` | `oss` |
| `SourceContent` | Yes | Origin address | `my-bucket.oss-cn-hangzhou.aliyuncs.com` |
| `Scope` | No | CDN scope: `global`, `domestic`, `overseas` | `global` |
| `CertType` | No | Certificate type: `free`, `upload` | `free` |

**Response:**
```json
{
  "DomainId": "12345678",
  "DomainName": "www.example.com",
  "Cname": "www.example.com.w.kunlun.com"
}
```

### 7.2 Terraform Alternative for CDN Domain

```hcl
resource "alicloud_cdn_domain_new" "migration" {
  domain_name = "<domain-name>"
  cdn_type    = "<cdn-type>"
  scope       = "<scope>"

  sources {
    content  = "<origin-content>"
    type     = "<origin-type>"
    priority = "<priority>"
  }
}
```

**Example - OSS Origin:**
```hcl
resource "alicloud_cdn_domain_new" "oss_origin" {
  domain_name = "www.example.com"
  cdn_type    = "web"
  scope       = "global"

  sources {
    content  = "<oss-bucket-name>.oss-<region>.aliyuncs.com"
    type     = "oss"
    priority = "20"
  }
}
```

**Example - Custom Origin:**
```hcl
resource "alicloud_cdn_domain_new" "custom_origin" {
  domain_name = "api.example.com"
  cdn_type    = "web"
  scope       = "global"

  sources {
    content  = "<origin-server-ip-or-domain>"
    type     = "ipaddr"
    priority = "20"
  }
}
```

### 7.2 Configure CDN Cache Rules

```bash
aliyun cdn SetCdnDomainStagingConfig \
  --DomainName www.example.com \
  --Functions '[{"functionArgs":[{"argName":"cacheTTL","argValue":"3600"}],"functionName":"Cache"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

### 7.3 Configure CDN HTTPS

```bash
aliyun cdn SetCdnDomainSSLCertificate \
  --DomainName www.example.com \
  --CertName my-cert \
  --CertType upload \
  --SSLProtocol TLSv1.2 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 7.4 Start CDN Domain

```bash
aliyun cdn StartCdnDomain \
  --DomainName www.example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

### 7.5 Describe CDN Domain

```bash
aliyun cdn DescribeCdnDomainDetail \
  --DomainName www.example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

### 7.6 Update DNS to Point to CDN

```bash
aliyun alidns UpdateDomainRecord \
  --RecordId <record-id> \
  --RR www \
  --Type CNAME \
  --Value www.example.com.w.kunlun.com \
  --user-agent AlibabaCloud-Agent-Skills
```

## 8. Load Balancer Setup

### 8.1 Create SLB Instance

```bash
aliyun slb CreateLoadBalancer \
  --RegionId <region> \
  --LoadBalancerName migration-slb \
  --AddressType internet \
  --VpcId <vpc-id> \
  --VSwitchId <vswitch-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "LoadBalancerId": "lb-bp1abc123def456789",
  "Address": "47.100.123.45"
}
```

### 8.2 Create Listener

```bash
aliyun slb CreateLoadBalancerHTTPListener \
  --RegionId <region> \
  --LoadBalancerId <lb-id> \
  --ListenerPort 80 \
  --BackendServerPort 80 \
  --Scheduler wrr \
  --user-agent AlibabaCloud-Agent-Skills
```

### 8.3 Add Backend Servers

```bash
aliyun slb AddBackendServers \
  --RegionId <region> \
  --LoadBalancerId <lb-id> \
  --BackendServers '[{"ServerId":"i-bp1abc123","Weight":100},{"ServerId":"i-bp1def456","Weight":100}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

## 9. Cleanup

### 9.1 Delete VPN Resources

```bash
# Delete VPN Connection
aliyun vpc DeleteVpnConnection \
  --RegionId <region> \
  --VpnConnectionId <vpn-connection-id> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete Customer Gateway
aliyun vpc DeleteCustomerGateway \
  --CustomerGatewayId <customer-gateway-id> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete VPN Gateway
aliyun vpc DeleteVpnGateway \
  --RegionId <region> \
  --VpnGatewayId <vpn-gateway-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 9.2 Delete CEN Resources

```bash
# Detach VPC from CEN
aliyun cen DetachCenChildInstance \
  --CenId <cen-id> \
  --ChildInstanceId <vpc-id> \
  --ChildInstanceType VPC \
  --ChildInstanceRegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete CEN
aliyun cen DeleteCen \
  --CenId <cen-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 9.3 Delete CDN Domain

```bash
aliyun cdn DeleteCdnDomain \
  --DomainName www.example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

### 9.4 Delete DNS Records

```bash
aliyun alidns DeleteDomainRecord \
  --RecordId <record-id> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete domain
aliyun alidns DeleteDomain \
  --DomainName example.com \
  --user-agent AlibabaCloud-Agent-Skills
```

### 9.5 Delete SLB

```bash
aliyun slb DeleteLoadBalancer \
  --RegionId <region> \
  --LoadBalancerId <lb-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 9.6 Delete VSwitch

```bash
aliyun vpc DeleteVSwitch \
  --VSwitchId <vswitch-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 9.7 Delete VPC

```bash
aliyun vpc DeleteVpc \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

## 10. Best Practices

1. **Plan CIDR carefully**: Avoid overlap with existing networks
2. **Use multiple VSwitches**: Deploy across multiple AZs for HA
3. **Security group least privilege**: Only open required ports
4. **Test VPN before migration**: Verify connectivity before cutover
5. **Lower DNS TTL**: Reduce TTL 24-48 hours before migration
6. **Monitor CDN metrics**: Track cache hit ratio, bandwidth, requests
7. **Use CEN for multi-region**: Simplify network management
8. **Document network topology**: Keep updated network diagrams
9. **Test rollback**: Know how to revert DNS and network changes
10. **Clean up unused resources**: Delete VPN, CEN after migration complete

## 11. Related APIs

| Category | API | CLI Command |
|----------|-----|-------------|
| VPC | CreateVpc | `aliyun vpc CreateVpc ... --user-agent AlibabaCloud-Agent-Skills` |
| VPC | CreateVSwitch | `aliyun vpc CreateVSwitch ... --user-agent AlibabaCloud-Agent-Skills` |
| VPC | DeleteVpc | `aliyun vpc DeleteVpc ... --user-agent AlibabaCloud-Agent-Skills` |
| VPC | DeleteVSwitch | `aliyun vpc DeleteVSwitch ... --user-agent AlibabaCloud-Agent-Skills` |
| Security Group | CreateSecurityGroup | `aliyun ecs CreateSecurityGroup ... --user-agent AlibabaCloud-Agent-Skills` |
| Security Group | AuthorizeSecurityGroup | `aliyun ecs AuthorizeSecurityGroup ... --user-agent AlibabaCloud-Agent-Skills` |
| VPN | CreateVpnGateway | `aliyun vpc CreateVpnGateway ... --user-agent AlibabaCloud-Agent-Skills` |
| VPN | CreateCustomerGateway | `aliyun vpc CreateCustomerGateway ... --user-agent AlibabaCloud-Agent-Skills` |
| VPN | CreateVpnConnection | `aliyun vpc CreateVpnConnection ... --user-agent AlibabaCloud-Agent-Skills` |
| CEN | CreateCen | `aliyun cen CreateCen ... --user-agent AlibabaCloud-Agent-Skills` |
| CEN | AttachCenChildInstance | `aliyun cen AttachCenChildInstance ... --user-agent AlibabaCloud-Agent-Skills` |
| DNS | AddDomain | `aliyun alidns AddDomain ... --user-agent AlibabaCloud-Agent-Skills` |
| DNS | AddDomainRecord | `aliyun alidns AddDomainRecord ... --user-agent AlibabaCloud-Agent-Skills` |
| CDN | AddCdnDomain | `aliyun cdn AddCdnDomain ... --user-agent AlibabaCloud-Agent-Skills` |
| SLB | CreateLoadBalancer | `aliyun slb CreateLoadBalancer ... --user-agent AlibabaCloud-Agent-Skills` |
