# Azure Service → Alibaba Cloud Mapping Index

This index provides a quick reference for mapping Azure services to Alibaba Cloud equivalents.

## Usage Guide

1. **Identify Azure resource type** from your Terraform configuration or ARM templates
2. **Find the resource** in the tables below
3. **Check migration difficulty**:
   - **Low**: Direct 1:1 mapping with minimal configuration changes
   - **Medium**: Functional equivalent with some configuration adjustments
   - **High**: Significant architectural changes required
4. **Refer to the detailed reference file** for:
   - Complete Terraform code examples
   - Configuration differences
   - Migration considerations
   - Best practices

---

## Networking Services

| Azure Service | Resource Type | Alibaba Cloud Service | Reference File | Migration Difficulty |
|---------------|---------------|----------------------|----------------|---------------------|
| Virtual Network | `azurerm_virtual_network` | VPC | `networking.md` | Low |
| Subnet | `azurerm_subnet` | VSwitch | `networking.md` | Low |
| Network Security Group | `azurerm_network_security_group` | Security Group | `networking.md` | Low |
| Public IP | `azurerm_public_ip` | EIP | `networking.md` | Low |
| NAT Gateway | `azurerm_nat_gateway` | NAT Gateway | `networking.md` | Low |
| Load Balancer | `azurerm_lb` | SLB | `networking.md` | Low |
| Application Gateway | `azurerm_application_gateway` | ALB | `networking.md` | Medium |
| Azure DNS | `azurerm_dns_zone` | Alibaba Cloud DNS | `networking.md` | Medium |
| Front Door | `azurerm_frontdoor` | CDN / DCDN | `networking.md` | High |
| ExpressRoute | `azurerm_express_route_circuit` | Express Connect | `networking.md` | High |
| VPN Gateway | `azurerm_virtual_network_gateway` | VPN Gateway | `networking.md` | Medium |

---

## Compute Services

| Azure Service | Resource Type | Alibaba Cloud Service | Reference File | Migration Difficulty |
|---------------|---------------|----------------------|----------------|---------------------|
| Virtual Machines | `azurerm_linux_virtual_machine` | ECS | `compute.md` | Low |
| Azure Functions | `azurerm_function_app` | Function Compute | `compute.md` | Medium |
| Container Instances | `azurerm_container_group` | ECI (Elastic Container Instance) | `compute.md` | Low |
| AKS | `azurerm_kubernetes_cluster` | ACK Managed | `compute.md` | Medium |
| App Service | `azurerm_app_service` | Web+ / ECS | `compute.md` | Medium |
| Batch | `azurerm_batch_account` | Batch Compute | `compute.md` | High |

**Note:** For detailed VM size mappings and Terraform examples, see [compute.md](compute.md).

---

## Database Services

| Azure Service | Resource Type | Alibaba Cloud Service | Reference File | Migration Difficulty |
|---------------|---------------|----------------------|----------------|---------------------|
| Azure SQL Server logical server | `azurerm_mssql_server` | ApsaraDB RDS SQL Server instance | `database.md` | Medium |
| Azure SQL Database | `azurerm_mssql_database` | Database on ApsaraDB RDS SQL Server | `database.md` | Medium |

---
