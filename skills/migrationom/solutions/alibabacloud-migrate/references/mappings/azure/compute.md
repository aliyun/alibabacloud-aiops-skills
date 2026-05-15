# Azure Compute Services → Alibaba Cloud Mapping

## Quick Reference: Service Mapping

| Azure Service | Alibaba Cloud Service | Primary Use Case | Migration Complexity |
|--------------|----------------------|------------------|---------------------|
| Virtual Machines | ECS (Elastic Compute Service) | IaaS compute instances | Low |
| Azure Functions | Function Compute (FC) | Serverless functions | Low-Medium |
| Container Instances | ECI (Elastic Container Instance) | Serverless containers | Low |
| AKS | ACK (Container Service for Kubernetes) | Managed Kubernetes | Medium |
| App Service | Web+ / ECS | PaaS web hosting | Medium-High |
| Virtual Machine Scale Sets | Auto Scaling + ECS | Auto-scaling VMs | Medium |
| Azure Batch | Batch Compute | HPC batch jobs | Medium |

## Virtual Machines → ECS (Elastic Compute Service)

### Resource Type Mapping

| Azure Resource | Alibaba Cloud Resource | Terraform Resource |
|----------------|------------------------|-------------------|
| `azurerm_linux_virtual_machine` | ECS Instance (Linux) | `alicloud_instance` |
| `azurerm_windows_virtual_machine` | ECS Instance (Windows) | `alicloud_instance` |
| `azurerm_network_interface` | ENI (Elastic Network Interface) | Embedded in `alicloud_instance` |
| `azurerm_virtual_machine_extension` | Cloud Assistant Command | `alicloud_ecs_command` |
| `azurerm_ssh_public_key` | ECS Key Pair | `alicloud_ecs_key_pair` |
| `azurerm_proximity_placement_group` | Deployment Set | `alicloud_ecs_deployment_set` |

### VM Size Mapping

| Azure VM Size | vCPU | Memory | Use Case | Alibaba Cloud Instance Type | vCPU | Memory | Instance Family |
|--------------|------|--------|----------|----------------------------|------|--------|-----------------|
| Standard_B1s | 1 | 1 GB | Burstable | ecs.t6-c1m1.large | 2 | 1 GB | t6 (Burstable) |
| Standard_B2s | 2 | 4 GB | Burstable | ecs.t6-c1m2.large | 2 | 2 GB | t6 (Burstable) |
| Standard_D2s_v5 | 2 | 8 GB | General Purpose | ecs.g7.large | 2 | 8 GB | g7 (General Purpose) |
| Standard_D4s_v5 | 4 | 16 GB | General Purpose | ecs.g7.xlarge | 4 | 16 GB | g7 (General Purpose) |
| Standard_D8s_v5 | 8 | 32 GB | General Purpose | ecs.g7.2xlarge | 8 | 32 GB | g7 (General Purpose) |
| Standard_F2s_v2 | 2 | 4 GB | Compute Optimized | ecs.c7.large | 2 | 4 GB | c7 (Compute Optimized) |
| Standard_F4s_v2 | 4 | 8 GB | Compute Optimized | ecs.c7.xlarge | 4 | 8 GB | c7 (Compute Optimized) |
| Standard_E2s_v5 | 2 | 16 GB | Memory Optimized | ecs.r7.large | 2 | 16 GB | r7 (Memory Optimized) |
| Standard_E4s_v5 | 4 | 32 GB | Memory Optimized | ecs.r7.xlarge | 4 | 32 GB | r7 (Memory Optimized) |
| Standard_NV6 | 6 | 56 GB | GPU (NVIDIA) | ecs.gn6i-c4g1.xlarge | 4 | 15 GB | gn6i (GPU T4) |

### Configuration Parameter Mapping

| Azure Parameter | Alibaba Cloud Parameter | Notes |
|----------------|------------------------|-------|
| `size` | `instance_type` | Instance specification |
| `admin_username` / `admin_password` | Not directly mapped | Use `password` or `key_name` |
| `os_disk.storage_account_type` | `system_disk_category` | `Premium_LRS` → `cloud_essd`, `StandardSSD_LRS` → `cloud_ssd` |
| `os_disk.disk_size_gb` | `system_disk_size` | System disk size in GB |
| `source_image_reference` | `image_id` | Image reference or ID |
| `network_interface_ids` | `vswitch_id` + `security_groups` | Directly assign to instance |
| `custom_data` | `user_data` | Base64 encoding handled automatically |
| `identity` | `role_name` | RAM role for instance |
| `boot_diagnostics` | Not available | Use Cloud Monitor instead |
| `zone` | `availability_zone` | Availability zone assignment |

### Terraform Migration Example

```hcl
# Azure Virtual Machine
resource "azurerm_linux_virtual_machine" "web" {
  name                = "web-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = "Standard_D2s_v5"

  admin_username      = "adminuser"

  network_interface_ids = [
    azurerm_network_interface.web.id,
  ]

  admin_ssh_key {
    username   = "adminuser"
    public_key = file("~/.ssh/id_rsa.pub")
  }

  os_disk {
    name                 = "web-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 40
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(file("init.sh"))

  tags = {
    Name = "web-server"
  }
}

# Alibaba Cloud ECS
resource "alicloud_instance" "web" {
  image_id             = "ubuntu_20_04_x64_20G_alibase_20240819.vhd"
  instance_type        = "ecs.g6.large"
  vswitch_id           = alicloud_vswitch.main.id
  security_groups      = [alicloud_security_group.web.id]
  instance_name        = "web-server"

  system_disk_category = "cloud_essd"
  system_disk_size     = 40

  user_data            = file("init.sh")

  # SSH key pair
  key_name             = alicloud_ecs_key_pair.main.key_name

  tags = {
    Name = "web-server"
  }
}

resource "alicloud_ecs_key_pair" "main" {
  key_pair_name   = "web-key"
  public_key      = file("~/.ssh/id_rsa.pub")
}
```

### Key Differences

1. **Image Selection**:
   - Azure: Publisher/Offer/SKU model
   - Alibaba: Image ID or name from marketplace

2. **Network Assignment**:
   - Azure: Separate Network Interface resource
   - Alibaba: Direct VSwitch assignment

3. **SSH Key Management**:
   - Azure: Inline `admin_ssh_key` block
   - Alibaba: Separate `alicloud_ecs_key_pair` resource

4. **Disk Configuration**:
   - Azure: `os_disk` with storage account type
   - Alibaba: `system_disk_*` parameters

---

## Azure Functions → Function Compute

### Runtime Support Comparison

| Runtime | Azure Functions | Alibaba Cloud FC | Migration Notes |
|---------|----------------|------------------|-----------------|
| Node.js | 18, 20 | 18, 20 | Compatible |
| Python | 3.9, 3.10, 3.11 | 3.9, 3.10 | Compatible |
| Java | 11, 17, 21 | 11, 17 | Compatible |
| .NET | 6, 8 (isolated) | Custom Runtime | Use custom runtime |
| PowerShell | 7.2 | Custom Runtime | Use custom runtime |

### Terraform Migration Example

```hcl
# Azure Functions
resource "azurerm_storage_account" "function" {
  name                     = "funcstorageacct"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_service_plan" "function" {
  name                = "function-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1"  # Consumption plan
}

resource "azurerm_linux_function_app" "processor" {
  name                = "data-processor"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  storage_account_name       = azurerm_storage_account.function.name
  storage_account_access_key = azurerm_storage_account.function.primary_access_key
  service_plan_id            = azurerm_service_plan.function.id

  site_config {
    application_stack {
      node_version = "18"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "node"
    "ENV"                      = "production"
  }

  tags = {
    Name = "data-processor"
  }
}

# Alibaba Cloud Function Compute
resource "alicloud_fc_service" "main" {
  name        = "main-service"
  description = "Main FC service"

  vpc_config {
    vswitch_ids       = alicloud_vswitch.private[*].id
    security_group_id = alicloud_security_group.function.id
  }
}

resource "alicloud_fc_function" "processor" {
  service     = alicloud_fc_service.main.name
  name        = "data-processor"
  filename    = "function.zip"
  handler     = "index.handler"
  runtime     = "nodejs18"
  timeout     = 300
  memory_size = 512

  environment_variables = {
    ENV = "production"
  }
}

resource "alicloud_fc_trigger" "http" {
  service  = alicloud_fc_service.main.name
  function = alicloud_fc_function.processor.name
  name     = "http-trigger"
  type     = "http"

  config = jsonencode({
    authType = "anonymous"
    methods  = ["GET", "POST"]
  })
}
```

### Key Differences

1. **Service Structure**:
   - Azure: Functions belong to App Service Plan
   - Alibaba: Functions belong to FC Service

2. **Storage Requirements**:
   - Azure: Requires separate Storage Account
   - Alibaba: Storage managed internally

3. **Triggers**:
   - Azure: Configured in function.json
   - Alibaba: Explicit trigger resources

4. **Consumption Plan**:
   - Azure: Y1 SKU for consumption
   - Alibaba: Pay-per-invocation by default

---

## Container Instances → ECI (Elastic Container Instance)

### Terraform Migration Example

```hcl
# Azure Container Instances
resource "azurerm_container_group" "app" {
  name                = "app-container"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"

  container {
    name   = "nginx"
    image  = "nginx:latest"
    cpu    = "0.5"
    memory = "1.5"

    ports {
      port     = 80
      protocol = "TCP"
    }
  }

  ip_address_type = "Public"
  dns_name_label  = "app-container"

  tags = {
    Name = "app-container"
  }
}

# Alibaba Cloud ECI
resource "alicloud_eci_container_group" "app" {
  container_group_name = "app-container"
  cpu                  = 0.5
  memory               = 1.5
  restart_policy       = "Always"

  security_group_id    = alicloud_security_group.app.id
  vswitch_id           = alicloud_vswitch.main.id

  containers {
    name  = "nginx"
    image = "nginx:latest"

    ports {
      port     = 80
      protocol = "TCP"
    }
  }

  # Public IP
  internet_ip = true

  tags = {
    Name = "app-container"
  }
}
```

### Key Differences

1. **Networking**:
   - Azure: Automatic VNet injection or public IP
   - Alibaba: Explicit VSwitch assignment

2. **Resource Specification**:
   - Azure: Per-container CPU/memory
   - Alibaba: Container group level CPU/memory

3. **DNS**:
   - Azure: `dns_name_label` for custom DNS
   - Alibaba: No built-in DNS label

---

## AKS → ACK Managed Kubernetes

### Terraform Migration Example

```hcl
# Azure AKS
resource "azurerm_kubernetes_cluster" "main" {
  name                = "main-cluster"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "main-aks"
  kubernetes_version  = "1.28.3"

  default_node_pool {
    name                = "default"
    node_count          = 2
    vm_size             = "Standard_D2s_v5"
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count           = 1
    max_count           = 5
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "172.16.0.0/16"
    dns_service_ip    = "172.16.0.10"
  }

  tags = {
    Name = "main-cluster"
  }
}

# Alibaba Cloud ACK
resource "alicloud_cs_managed_kubernetes" "main" {
  name_prefix          = "main-cluster"
  cluster_spec         = "ack.pro.small"
  version              = "1.28.3-aliyun.1"

  vswitch_ids          = alicloud_vswitch.private[*].id
  pod_vswitch_ids      = alicloud_vswitch.pod[*].id

  worker_instance_types = ["ecs.g6.large"]
  worker_number        = 2
  password             = var.worker_password

  # Auto-scaling configuration
  worker_auto_renew         = true
  worker_auto_renew_period  = 1

  service_cidr         = "172.16.0.0/16"

  # API server access
  slb_internet_enabled = true

  addons {
    name   = "terway-eniip"
    config = ""
  }

  addons {
    name   = "csi-plugin"
    config = ""
  }

  addons {
    name   = "csi-provisioner"
    config = ""
  }

  addons {
    name   = "nginx-ingress-controller"
    config = jsonencode({
      "IngressSlbNetworkType" = "internet"
    })
  }
}
```

### Key Differences

1. **Kubernetes Version**:
   - Azure: Standard K8s versions
   - Alibaba: Versions with `-aliyun.1` suffix

2. **Networking**:
   - Azure: Azure CNI or kubenet
   - Alibaba: Terway (ENI-based) or Flannel

3. **Node Pools**:
   - Azure: Explicit node pool configuration
   - Alibaba: Worker nodes configured in cluster

4. **Identity**:
   - Azure: System-assigned or user-assigned managed identity
   - Alibaba: RAM roles configured separately

5. **Add-ons**:
   - Azure: Managed via separate resources
   - Alibaba: Configured in cluster resource

---

## App Service → Web+ / ECS

### Migration Considerations

Azure App Service is a Platform-as-a-Service (PaaS) offering. Alibaba Cloud has two options:

1. **Web+**: Similar PaaS offering (recommended for ease of migration)
2. **ECS with application deployment**: More control but requires manual setup

### Terraform Migration Example (Web+)

```hcl
# Azure App Service
resource "azurerm_service_plan" "main" {
  name                = "app-plan"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "P1v2"
}

resource "azurerm_linux_web_app" "main" {
  name                = "my-app"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    always_on = true

    application_stack {
      node_version = "18-lts"
    }
  }

  app_settings = {
    "NODE_ENV" = "production"
  }

  tags = {
    Name = "my-app"
  }
}

# Alibaba Cloud Web+ (Note: Terraform support is limited)
# Alternative: Deploy to ECS with application deployment tools
resource "alicloud_instance" "web" {
  image_id             = "ubuntu_20_04_x64_20G_alibase_20240819.vhd"
  instance_type        = "ecs.c6.large"
  vswitch_id           = alicloud_vswitch.main.id
  security_groups      = [alicloud_security_group.web.id]
  instance_name        = "web-app"

  system_disk_category = "cloud_essd"
  system_disk_size     = 40

  # Use user_data to install Node.js and deploy app
  user_data = base64encode(templatefile("deploy.sh", {
    app_name = "my-app"
  }))

  tags = {
    Name = "web-app"
  }
}
```

### Key Differences

1. **PaaS vs IaaS**:
   - Azure App Service: Fully managed PaaS
   - Alibaba Web+: Similar PaaS but less Terraform support
   - Alternative: Deploy to ECS with automation scripts

2. **Scaling**:
   - Azure: Built-in auto-scaling
   - Alibaba: Configure auto-scaling groups for ECS

3. **Deployment**:
   - Azure: ZIP deploy, Docker, or Git
   - Alibaba: Similar options but different tooling

---

## Migration Checklist

### Pre-Migration
- [ ] Inventory all VMs, Functions, and container workloads
- [ ] Document VM sizes and configurations
- [ ] Review managed identities and service principals
- [ ] Identify custom images (need to be rebuilt)
- [ ] List all Function triggers and integrations

### During Migration
- [ ] Create equivalent ECS instances with appropriate types
- [ ] Migrate Functions to Function Compute
- [ ] Convert ACI workloads to ECI
- [ ] Migrate container images to Alibaba Container Registry
- [ ] Update application configurations for new endpoints

### Post-Migration
- [ ] Verify all compute resources are running
- [ ] Test application functionality
- [ ] Monitor performance metrics
- [ ] Update DNS records
- [ ] Decommission Azure resources after validation

## Common Migration Patterns

### Pattern 1: Lift and Shift (VMs → ECS)
- Minimal changes
- Recreate instances with similar specs
- Update network and security configurations
- **Timeline**: 1-2 weeks

### Pattern 2: Serverless Migration (Functions → Function Compute)
- Code changes minimal for supported runtimes
- Update trigger configurations
- Test thoroughly (different event structures)
- **Timeline**: 2-3 weeks

### Pattern 3: Container Modernization (AKS → ACK)
- Similar Kubernetes experience
- Update network and storage configurations
- Migrate workloads using kubectl
- **Timeline**: 3-5 weeks
