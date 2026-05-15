# Azure Networking Services → Alibaba Cloud Mapping

## Quick Reference: Service Mapping

| Azure Service | Alibaba Cloud Service | Primary Function | Migration Complexity | Notes |
|--------------|----------------------|------------------|---------------------|-------|
| Virtual Network | VPC | Virtual network | Low | Single CIDR per VPC |
| Subnet | VSwitch | Network segment | Low | Must specify availability zone |
| Network Security Group | Security Group | Firewall rules | Low | Different association model |
| Public IP Address | EIP (Elastic IP) | Public IP | Low | Always static |
| NAT Gateway | NAT Gateway | Outbound internet | Low | Requires SNAT entries |
| Load Balancer | SLB / NLB | Layer 4 load balancing | Low-Medium | Different configuration |
| Application Gateway | ALB | Layer 7 load balancing | Medium | Separate resources |
| VPN Gateway | VPN Gateway | Site-to-Site VPN | Low | Similar IPsec configuration |
| ExpressRoute | Express Connect | Dedicated connection | Medium | Different setup process |
| Azure DNS | Alibaba Cloud DNS | DNS hosting | Low | Similar record types |
| Azure Firewall | Cloud Firewall | Managed firewall | Medium | Different feature set |
| Traffic Manager | Global Traffic Manager | DNS-based routing | Low | Similar capabilities |

## Virtual Network → VPC

### Resource Type Mapping

| Azure Resource | Alibaba Cloud Resource | Terraform Resource |
|----------------|------------------------|-------------------|
| `azurerm_virtual_network` | VPC | `alicloud_vpc` |
| `azurerm_subnet` | VSwitch | `alicloud_vswitch` |
| `azurerm_network_security_group` | Security Group | `alicloud_security_group` |
| `azurerm_network_security_rule` | Security Group Rule | `alicloud_security_group_rule` |
| `azurerm_route_table` | Route Table | `alicloud_route_table` |
| `azurerm_route` | Route Entry | `alicloud_route_entry` |
| `azurerm_virtual_network_peering` | VPC Peering | `alicloud_vpc_peer_connection` |
| `azurerm_network_watcher` | VPC Flow Logs | `alicloud_vpc_flow_log` |

### Configuration Parameter Mapping

| Azure Parameter | Alibaba Cloud Parameter | Notes |
|----------------|------------------------|-------|
| `address_space` | `cidr_block` | Single CIDR per VPC (Azure supports multiple) |
| `dns_servers` | Built-in DNS | Alibaba Cloud provides automatic DNS resolution |
| `location` | `region` (implicit) | Region determined by provider configuration |
| `ddos_protection_plan` | Anti-DDoS Pro | Separate service, not VPC parameter |
| `subnet.address_prefixes` | `vswitch.cidr_block` | Single CIDR per VSwitch |
| `subnet.service_endpoints` | PrivateLink | Use `alicloud_privatelink_vpc_endpoint` |

### Terraform Migration Example

```hcl
# Azure Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "main-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    Name = "main-vpc"
  }
}

# Alibaba Cloud VPC
resource "alicloud_vpc" "main" {
  vpc_name   = "main-vpc"
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "main-vpc"
  }
}
```

### Key Differences

1. **DNS**: Azure: Automatic DNS within VNet; Alibaba: DNS enabled by default
2. **Address Space**: Azure: Multiple address spaces supported; Alibaba: Single CIDR block per VPC
3. **Peering**: Both support VPC/VNet peering; similar configuration

---

## Subnet → VSwitch

### Terraform Migration Example

```hcl
# Azure Subnets
resource "azurerm_subnet" "public" {
  count                = 2
  name                 = "public-subnet-${count.index + 1}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(azurerm_virtual_network.main.address_space[0], 8, count.index)]

  # Service endpoints
  service_endpoints = ["Microsoft.Storage", "Microsoft.Sql"]
}

resource "azurerm_subnet" "private" {
  count                = 2
  name                 = "private-subnet-${count.index + 1}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(azurerm_virtual_network.main.address_space[0], 8, count.index + 10)]
}

# Alibaba Cloud VSwitches
data "alicloud_zones" "available" {
  available_resource_creation = "VSwitch"
}

resource "alicloud_vswitch" "public" {
  count      = 2
  vpc_id     = alicloud_vpc.main.id
  cidr_block = cidrsubnet(alicloud_vpc.main.cidr_block, 8, count.index)
  zone_id    = data.alicloud_zones.available.zones[count.index].id
  vswitch_name = "public-vswitch-${count.index + 1}"

  tags = {
    Name = "public-vswitch-${count.index + 1}"
    Type = "Public"
  }
}

resource "alicloud_vswitch" "private" {
  count      = 2
  vpc_id     = alicloud_vpc.main.id
  cidr_block = cidrsubnet(alicloud_vpc.main.cidr_block, 8, count.index + 10)
  zone_id    = data.alicloud_zones.available.zones[count.index].id
  vswitch_name = "private-vswitch-${count.index + 1}"

  tags = {
    Name = "private-vswitch-${count.index + 1}"
    Type = "Private"
  }
}
```

### Key Differences

1. **Naming**: Azure: Subnet; Alibaba: VSwitch (Virtual Switch)
2. **Zone Assignment**: Azure: Subnets span availability zones; Alibaba: VSwitch must specify zone_id (required)
3. **Service Endpoints**: Azure: Service endpoints per subnet; Alibaba: PrivateLink or VPC endpoint configuration

---

## Network Security Group → Security Group

### Terraform Migration Example

```hcl
# Azure Network Security Group
resource "azurerm_network_security_group" "web" {
  name                = "web-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    Name = "web-sg"
  }
}

resource "azurerm_network_security_rule" "allow_http" {
  name                        = "AllowHTTP"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "80"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.web.name
}

resource "azurerm_network_security_rule" "allow_https" {
  name                        = "AllowHTTPS"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.web.name
}

resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public[0].id
  network_security_group_id = azurerm_network_security_group.web.id
}

# Alibaba Cloud Security Group
resource "alicloud_security_group" "web" {
  security_group_name = "web-sg"
  description         = "Web server security group"
  vpc_id              = alicloud_vpc.main.id

  tags = {
    Name = "web-sg"
  }
}

resource "alicloud_security_group_rule" "allow_http" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "80/80"
  security_group_id = alicloud_security_group.web.id
  cidr_ip           = "0.0.0.0/0"
  priority          = 1
  description       = "HTTP from internet"
}

resource "alicloud_security_group_rule" "allow_https" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "443/443"
  security_group_id = alicloud_security_group.web.id
  cidr_ip           = "0.0.0.0/0"
  priority          = 1
  description       = "HTTPS from internet"
}

resource "alicloud_security_group_rule" "allow_all_egress" {
  type              = "egress"
  ip_protocol       = "all"
  port_range        = "-1/-1"
  security_group_id = alicloud_security_group.web.id
  cidr_ip           = "0.0.0.0/0"
  priority          = 1
  description       = "Allow all outbound"
}
```

### Configuration Parameter Mapping (Security Group)

| Azure Parameter | Alibaba Cloud Parameter | Notes |
|----------------|------------------------|-------|
| `priority` | `priority` | Azure: 100-4096, Alibaba: 1-100 (both lower = higher) |
| `direction` | `type` | `Inbound` → `ingress`, `Outbound` → `egress` |
| `access` | `policy` | `Allow` → `accept`, `Deny` → `drop` |
| `protocol` | `ip_protocol` | `Tcp` → `tcp`, `Udp` → `udp`, `*` → `all` |
| `source_port_range` | Not supported | Alibaba only filters destination ports |
| `destination_port_range` | `port_range` | `80` → `80/80`, `80-443` → `80/443`, `*` → `-1/-1` |
| `source_address_prefix` | `cidr_ip` or `source_security_group_id` | CIDR or security group reference |
| `destination_address_prefix` | Not needed for egress | Direction determines source/destination |

### Key Differences

1. **Association Model**: Azure: NSG → Subnet or NIC (network-level); Alibaba: Security Group → ECS Instance (instance-level)
2. **Rule Priority**: Azure: 100-4096; Alibaba: 1-100 — recalculate priority values
3. **Port Range Format**: Azure: Separate source/destination fields; Alibaba: Single `port_range` field (format: "start/end")
4. **Default Rules**: Azure: Implicit allow within VNet + deny inbound from internet; Alibaba: Default allow all outbound, deny all inbound
5. **Deny Rules**: Azure: Explicit deny rules supported; Alibaba: Use `policy = "drop"` for deny rules
6. **Rule Limits**: Azure: 1000 rules per NSG; Alibaba: 100 ingress + 100 egress rules per SG

---

## Public IP → EIP (Elastic IP)

### Terraform Migration Example

```hcl
# Azure Public IP
resource "azurerm_public_ip" "web" {
  name                = "web-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = {
    Name = "web-public-ip"
  }
}

resource "azurerm_network_interface" "web" {
  name                = "web-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.public[0].id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.web.id
  }
}

# Alibaba Cloud EIP
resource "alicloud_eip_address" "web" {
  address_name         = "web-eip"
  bandwidth            = "100"
  internet_charge_type = "PayByTraffic"

  tags = {
    Name = "web-public-ip"
  }
}

resource "alicloud_eip_association" "web" {
  allocation_id = alicloud_eip_address.web.id
  instance_id   = alicloud_instance.web.id
  instance_type = "EcsInstance"
}
```

### Key Differences

1. **Allocation**: Azure: Static or Dynamic; Alibaba: Always static once allocated
2. **Association**: Azure: Via Network Interface; Alibaba: Direct with ECS, NAT, or SLB
3. **Bandwidth**: Azure: Based on VM size; Alibaba: Configurable bandwidth per EIP

---

## NAT Gateway → NAT Gateway

### Terraform Migration Example

```hcl
# Azure NAT Gateway
resource "azurerm_public_ip" "nat" {
  name                = "nat-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_nat_gateway" "main" {
  name                    = "main-nat"
  location                = azurerm_resource_group.main.location
  resource_group_name     = azurerm_resource_group.main.name
  sku_name                = "Standard"
  idle_timeout_in_minutes = 10
}

resource "azurerm_nat_gateway_public_ip_association" "main" {
  nat_gateway_id       = azurerm_nat_gateway.main.id
  public_ip_address_id = azurerm_public_ip.nat.id
}

resource "azurerm_subnet_nat_gateway_association" "private" {
  subnet_id      = azurerm_subnet.private[0].id
  nat_gateway_id = azurerm_nat_gateway.main.id
}

# Alibaba Cloud NAT Gateway
resource "alicloud_nat_gateway" "main" {
  vpc_id           = alicloud_vpc.main.id
  nat_gateway_name = "main-nat"
  payment_type     = "PayAsYouGo"
  vswitch_id       = alicloud_vswitch.public[0].id
  nat_type         = "Enhanced"
}

resource "alicloud_eip_address" "nat" {
  address_name         = "nat-eip"
  bandwidth            = "100"
  internet_charge_type = "PayByTraffic"
}

resource "alicloud_eip_association" "nat" {
  allocation_id = alicloud_eip_address.nat.id
  instance_id   = alicloud_nat_gateway.main.id
  instance_type = "Nat"
}

resource "alicloud_snat_entry" "default" {
  snat_table_id     = alicloud_nat_gateway.main.snat_table_ids[0]
  source_vswitch_id = alicloud_vswitch.private[0].id
  snat_ip           = alicloud_eip_address.nat.ip_address
}
```

### Key Differences

1. **Gateway Types**: Azure: Standard NAT Gateway; Alibaba: Enhanced NAT Gateway (Standard type is deprecated)
2. **SNAT Configuration**: Azure: Automatic for associated subnets; Alibaba: Explicit SNAT entry per VSwitch
3. **EIP Binding**: Azure: Public IP during creation; Alibaba: EIP associated separately

---

## Load Balancer → SLB / NLB

### Resource Type Mapping

| Azure Resource | Alibaba Cloud Resource | Terraform Resource | Notes |
|----------------|------------------------|-------------------|-------|
| `azurerm_lb` | SLB (Classic Load Balancer) | `alicloud_slb_load_balancer` | L4/L7 通用 |
| `azurerm_lb` | NLB (Network Load Balancer) | `alicloud_nlb_load_balancer` | 高性能 L4，推荐替代 SLB 的 TCP/UDP 场景 |
| `azurerm_lb_backend_address_pool` | SLB Backend Server Group | `alicloud_slb_server_group` | VServer Group |
| `azurerm_lb_backend_address_pool` | NLB Server Group | `alicloud_nlb_server_group` | NLB 后端服务器组 |
| `azurerm_lb_backend_address_pool_address` | SLB Backend Server | `alicloud_slb_backend_server` | 后端服务器挂载 |
| `azurerm_lb_probe` | Health Check (inline) | N/A (inline in listener) | SLB: 健康检查内嵌在 listener 中 |
| `azurerm_lb_probe` | NLB Health Check | `alicloud_nlb_health_check_template` | NLB: 独立健康检查模板 |
| `azurerm_lb_rule` | SLB Listener | `alicloud_slb_listener` | 包含协议、端口、健康检查配置 |
| `azurerm_lb_rule` | NLB Listener | `alicloud_nlb_listener` | TCP/UDP 监听 |
| `azurerm_lb_nat_rule` | SLB Forwarding Rule | `alicloud_slb_rule` | 转发规则 |
| `azurerm_lb_outbound_rule` | NAT Gateway SNAT | `alicloud_snat_entry` | 阿里云使用 NAT 网关实现出方向 |

### Configuration Parameter Mapping (SLB)

| Azure Parameter | Alibaba Cloud Parameter | Notes |
|----------------|------------------------|-------|
| `sku` (Basic/Standard) | `load_balancer_spec` | 如 `slb.s1.small`, `slb.s2.small` 等 |
| `frontend_ip_configuration.public_ip_address_id` | `address_type = "internet"` | 公网类型自动分配或绑定 EIP |
| `frontend_ip_configuration` (internal) | `address_type = "intranet"` + `vswitch_id` | 内网需指定 VSwitch |
| `lb_rule.protocol` | `listener.protocol` | `Tcp` → `tcp`, `Udp` → `udp` |
| `lb_rule.frontend_port` | `listener.frontend_port` | 直接映射 |
| `lb_rule.backend_port` | `listener.backend_port` | 直接映射 |
| `lb_rule.idle_timeout_in_minutes` | `listener.established_timeout` | 单位为秒（SLB TCP） |
| `lb_probe.protocol` | `listener.health_check_type` | `Http` → `http`, `Tcp` → `tcp` |
| `lb_probe.interval_in_seconds` | `listener.health_check_interval` | 直接映射（秒） |
| `lb_probe.number_of_probes` | `listener.unhealthy_threshold` | 不健康阈值 |

### Terraform Migration Example (Layer 4 Load Balancer)

```hcl
# Azure Load Balancer
resource "azurerm_public_ip" "lb" {
  name                = "lb-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_lb" "main" {
  name                = "main-lb"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"

  frontend_ip_configuration {
    name                 = "PublicIPAddress"
    public_ip_address_id = azurerm_public_ip.lb.id
  }
}

resource "azurerm_lb_backend_address_pool" "main" {
  loadbalancer_id = azurerm_lb.main.id
  name            = "BackEndAddressPool"
}

resource "azurerm_lb_probe" "http" {
  loadbalancer_id = azurerm_lb.main.id
  name            = "http-probe"
  protocol        = "Http"
  request_path    = "/health"
  port            = 80
}

resource "azurerm_lb_rule" "http" {
  loadbalancer_id                = azurerm_lb.main.id
  name                           = "HTTPRule"
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "PublicIPAddress"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.main.id]
  probe_id                       = azurerm_lb_probe.http.id
}

# Alibaba Cloud SLB (Classic)
resource "alicloud_slb_load_balancer" "main" {
  load_balancer_name = "main-slb"
  load_balancer_spec = "slb.s2.small"
  address_type       = "internet"
  vswitch_id         = alicloud_vswitch.public[0].id
}

resource "alicloud_slb_listener" "http" {
  load_balancer_id = alicloud_slb_load_balancer.main.id
  backend_port     = 80
  frontend_port    = 80
  protocol         = "http"
  bandwidth        = 10

  health_check              = "on"
  health_check_uri          = "/health"
  health_check_connect_port = 80
  healthy_threshold         = 2
  unhealthy_threshold       = 2
  health_check_timeout      = 5
  health_check_interval     = 10
}

resource "alicloud_slb_backend_server" "main" {
  load_balancer_id = alicloud_slb_load_balancer.main.id

  backend_servers {
    server_id = alicloud_instance.web[0].id
    weight    = 100
  }

  backend_servers {
    server_id = alicloud_instance.web[1].id
    weight    = 100
  }
}
```

### Load Balancer Type Comparison

| Feature | Azure Load Balancer | Azure App Gateway | Alibaba SLB | Alibaba ALB | Alibaba NLB |
|---------|-------------------|------------------|------------|------------|-------------|
| OSI Layer | Layer 4 | Layer 7 | Layer 4 | Layer 7 | Layer 4 |
| Protocol | TCP, UDP | HTTP, HTTPS | TCP, UDP, HTTP, HTTPS | HTTP, HTTPS, QUIC | TCP, UDP |
| SSL Termination | No | Yes | Yes | Yes | No |
| Path-based Routing | No | Yes | Limited | Yes | No |
| Host-based Routing | No | Yes | Limited | Yes | No |
| WebSocket | Yes | Yes | Yes | Yes | Yes |
| Health Check | HTTP, HTTPS, TCP | HTTP, HTTPS | HTTP, HTTPS, TCP | HTTP, HTTPS | HTTP, TCP |
| Session Persistence | Source IP | Cookie | Cookie, Source IP | Cookie, Header | Source IP |
| Best For | Simple L4 LB | Web apps | General purpose | Modern web apps | High performance |

### Key Differences

1. **Architecture**: Azure LB (L4) vs App Gateway (L7) are separate; Alibaba: SLB (unified L4/L7), ALB (advanced L7), NLB (high-performance L4)
2. **Resource Structure**: Azure: LB → Frontend → Backend → Probe → Rule (separate); Alibaba: SLB → Listener (includes health check + forwarding) → Backend Servers (fewer resources)
3. **Health Checks**: Azure: Separate `azurerm_lb_probe`; Alibaba: Inline in `alicloud_slb_listener`
4. **Outbound Connectivity**: Azure: LB can provide SNAT; Alibaba: Use NAT Gateway separately

---

## Application Gateway → ALB

### Resource Type Mapping

| Azure Resource | Alibaba Cloud Resource | Terraform Resource | Notes |
|----------------|------------------------|-------------------|-------|
| `azurerm_application_gateway` | ALB (Application Load Balancer) | `alicloud_alb_load_balancer` | L7 负载均衡实例 |
| App Gateway `backend_address_pool` | ALB Server Group | `alicloud_alb_server_group` | 后端服务器组（独立资源） |
| App Gateway `http_listener` | ALB Listener | `alicloud_alb_listener` | HTTP/HTTPS 监听 |
| App Gateway `request_routing_rule` | ALB Forwarding Rule | `alicloud_alb_rule` | 转发规则（路径/域名） |
| App Gateway `backend_http_settings` | Server Group 配置 | 内嵌在 `alicloud_alb_server_group` | 后端协议、超时等 |
| App Gateway `ssl_certificate` | ALB SSL 证书 | `alicloud_alb_listener` + `alicloud_ssl_certificates_service_certificate` | 证书独立管理 |
| App Gateway `url_path_map` | ALB Rule Conditions | `alicloud_alb_rule` | 路径条件匹配 |
| App Gateway `redirect_configuration` | ALB Rule Actions | `alicloud_alb_rule` (redirect action) | 重定向动作 |
| App Gateway `health_probe` | Health Check Config | 内嵌在 `alicloud_alb_server_group` | 健康检查内嵌在 Server Group |
| `azurerm_web_application_firewall_policy` | WAF | `alicloud_wafv3_instance` | 阿里云 WAF 为独立服务 |

### Configuration Parameter Mapping (ALB)

| Azure Parameter | Alibaba Cloud Parameter | Notes |
|----------------|------------------------|-------|
| `sku.name` (Standard_v2) | `load_balancer_edition` | `Basic`, `Standard`, `SuperLarge` |
| `sku.capacity` | 自动弹性 | ALB 无需指定容量，自动弹性扩缩 |
| `gateway_ip_configuration.subnet_id` | `zone_mappings.vswitch_id` | 需配置多个可用区 |
| `backend_http_settings.port` | `server_group.protocol` + port in servers | 在 server group 和 server 层配置 |
| `backend_http_settings.cookie_based_affinity` | `sticky_session_config` | 在 server group 中配置 |
| `backend_http_settings.request_timeout` | `server_group.timeout` | 超时配置 |
| `http_listener.protocol` | `listener_protocol` | `Http` → `HTTP`, `Https` → `HTTPS` |
| `http_listener.frontend_port` | `listener_port` | 直接映射 |
| `request_routing_rule.rule_type` | `default_actions` / `alicloud_alb_rule` | Basic → default_actions, PathBasedRouting → alb_rule |

### Required Target Properties and Forbidden Mappings

When Phase 2 maps `azurerm_application_gateway`, select ALB in `target_resources[].type` and include decisive ALB properties:

| Source Pattern | Target Resource | Required `target_resources[].properties` | Forbidden |
|----------------|----------------|-------------------------------------------|-----------|
| `azurerm_application_gateway` with public frontend IP | `alicloud_alb_load_balancer` | `address_type = "Internet"`, `zone_mappings` with at least 2 VSwitch references, `load_balancer_edition` when derived from SKU | `alicloud_slb_load_balancer`, `alicloud_nlb_load_balancer` |
| `azurerm_application_gateway` with internal frontend only | `alicloud_alb_load_balancer` | intranet/private `address_type`, `zone_mappings` with VSwitch references | `alicloud_slb_load_balancer`, `alicloud_nlb_load_balancer` |

Application Gateway is Layer 7. Do not map it to Classic SLB or NLB unless the assessment explicitly states that the source is not using L7 behavior and the user approves the downgrade.

### Terraform Migration Example

```hcl
# Azure Application Gateway (L7)
resource "azurerm_public_ip" "appgw" {
  name                = "appgw-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_application_gateway" "main" {
  name                = "main-appgw"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 2
  }

  gateway_ip_configuration {
    name      = "gateway-ip-config"
    subnet_id = azurerm_subnet.appgw.id
  }

  frontend_port {
    name = "http-port"
    port = 80
  }

  frontend_ip_configuration {
    name                 = "frontend-ip-config"
    public_ip_address_id = azurerm_public_ip.appgw.id
  }

  backend_address_pool {
    name = "backend-pool"
  }

  backend_http_settings {
    name                  = "http-settings"
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 30
  }

  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "frontend-ip-config"
    frontend_port_name             = "http-port"
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = "routing-rule"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "backend-pool"
    backend_http_settings_name = "http-settings"
    priority                   = 100
  }
}

# Alibaba Cloud ALB
resource "alicloud_alb_load_balancer" "main" {
  load_balancer_name    = "main-alb"
  load_balancer_edition = "Standard"
  load_balancer_billing_config {
    pay_type = "PayAsYouGo"
  }

  vpc_id       = alicloud_vpc.main.id
  address_type = "Internet"

  zone_mappings {
    vswitch_id = alicloud_vswitch.public[0].id
    zone_id    = alicloud_vswitch.public[0].zone_id
  }

  zone_mappings {
    vswitch_id = alicloud_vswitch.public[1].id
    zone_id    = alicloud_vswitch.public[1].zone_id
  }
}

resource "alicloud_alb_server_group" "app" {
  server_group_name = "app-sg"
  vpc_id            = alicloud_vpc.main.id
  protocol          = "HTTP"

  health_check_config {
    health_check_enabled         = true
    health_check_connect_port    = 80
    health_check_interval        = 10
    health_check_path            = "/health"
    health_check_protocol        = "HTTP"
    health_check_timeout         = 5
    healthy_threshold            = 2
    unhealthy_threshold          = 2
    health_check_http_version    = "HTTP1.1"
    health_check_codes           = ["http_2xx"]
  }

  sticky_session_config {
    sticky_session_enabled = false
  }
}

resource "alicloud_alb_listener" "http" {
  load_balancer_id  = alicloud_alb_load_balancer.main.id
  listener_port     = 80
  listener_protocol = "HTTP"

  default_actions {
    type = "ForwardGroup"
    forward_group_config {
      server_group_tuples {
        server_group_id = alicloud_alb_server_group.app.id
      }
    }
  }
}
```

### Key Differences

1. **Configuration Structure**: Azure: All-in-one Application Gateway; Alibaba: Separate resources for ALB, server groups, listeners
2. **Zone Configuration**: Azure: Subnet-based; Alibaba: Explicit zone mappings with VSwitches
3. **WAF Integration**: Azure: Integrated WAF SKU; Alibaba: Separate WAF service

---

## Azure DNS → Alibaba Cloud DNS

### Terraform Migration Example

```hcl
# Azure DNS
resource "azurerm_dns_zone" "main" {
  name                = "example.com"
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_dns_a_record" "www" {
  name                = "www"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  records             = [azurerm_public_ip.web.ip_address]
}

resource "azurerm_dns_cname_record" "api" {
  name                = "api"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record              = azurerm_lb.main.frontend_ip_configuration[0].public_ip_address
}

# Alibaba Cloud DNS
resource "alicloud_alidns_domain" "main" {
  domain_name = "example.com"
}

resource "alicloud_alidns_record" "www" {
  domain_name = alicloud_alidns_domain.main.domain_name
  rr          = "www"
  type        = "A"
  value       = alicloud_eip_address.web.ip_address
  ttl         = 300
}

resource "alicloud_alidns_record" "api" {
  domain_name = alicloud_alidns_domain.main.domain_name
  rr          = "api"
  type        = "CNAME"
  value       = alicloud_alb_load_balancer.main.dns_name
  ttl         = 300
}
```

### Key Differences

1. **Record Specification**: Azure: `name` (subdomain); Alibaba: `rr` (relative record, subdomain only)
2. **Record Types**: Both support standard DNS record types; similar routing policies

---

## Migration Checklist

### Pre-Migration
- [ ] Document VNet CIDR blocks
- [ ] Inventory all subnets and zones
- [ ] List NSG rules and associations
- [ ] Document routing tables
- [ ] Identify NAT Gateways and public IPs
- [ ] List load balancers and backend pools
- [ ] Export DNS records

### During Migration
- [ ] Create VPC with same CIDR
- [ ] Create VSwitches in appropriate zones
- [ ] Migrate NSG rules to Security Groups
- [ ] Set up NAT Gateway and SNAT entries
- [ ] Create load balancers (SLB or ALB)
- [ ] Migrate DNS records

### Post-Migration
- [ ] Verify network connectivity
- [ ] Test security group rules
- [ ] Validate NAT Gateway routing
- [ ] Test load balancer health checks
- [ ] Update DNS TTLs for quick rollback
- [ ] Monitor network performance
