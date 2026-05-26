# 资源依赖关系规则

资源依赖层级图和 import 顺序约束。

---

## 依赖层级图

```
Layer 0（无依赖，可并行 import）
├── alicloud_vpc
├── alicloud_oss_bucket
├── alicloud_dns_domain
├── alicloud_ram_user
├── alicloud_ram_role
├── alicloud_ram_policy
├── alicloud_kms_key
├── alicloud_key_pair
└── alicloud_image

Layer 1（依赖 Layer 0）
├── alicloud_vswitch              → 依赖 alicloud_vpc
├── alicloud_security_group       → 依赖 alicloud_vpc
├── alicloud_route_table          → 依赖 alicloud_vpc
├── alicloud_eip_address          → 无依赖（可与 Layer 0 并行）
├── alicloud_oss_bucket_acl       → 依赖 alicloud_oss_bucket
├── alicloud_oss_bucket_policy    → 依赖 alicloud_oss_bucket
├── alicloud_dns_record           → 依赖 alicloud_dns_domain
└── alicloud_ram_user_policy_attachment → 依赖 alicloud_ram_user + alicloud_ram_policy

Layer 2（依赖 Layer 1）
├── alicloud_nat_gateway          → 依赖 alicloud_vpc + alicloud_vswitch
├── alicloud_vpn_gateway          → 依赖 alicloud_vpc
├── alicloud_slb_load_balancer    → 依赖 alicloud_vswitch（内网）
├── alicloud_alb_load_balancer    → 依赖 alicloud_vpc + alicloud_vswitch
├── alicloud_alb_server_group     → 依赖 alicloud_vpc
├── alicloud_security_group_rule  → 依赖 alicloud_security_group
└── alicloud_route_entry          → 依赖 alicloud_route_table

Layer 3（依赖 Layer 2）
├── alicloud_instance             → 依赖 alicloud_vswitch + alicloud_security_group
├── alicloud_db_instance          → 依赖 alicloud_vswitch
├── alicloud_kvstore_instance     → 依赖 alicloud_vswitch
├── alicloud_mongodb_instance     → 依赖 alicloud_vswitch
├── alicloud_polardb_cluster      → 依赖 alicloud_vswitch
├── alicloud_nas_file_system      → 无依赖（可与 Layer 0 并行）
├── alicloud_snat_entry           → 依赖 alicloud_nat_gateway
├── alicloud_forward_entry        → 依赖 alicloud_nat_gateway
├── alicloud_eip_association      → 依赖 alicloud_eip_address + 实例
├── alicloud_slb_listener         → 依赖 alicloud_slb_load_balancer
└── alicloud_alb_listener         → 依赖 alicloud_alb_load_balancer

Layer 4（依赖 Layer 3）
├── alicloud_disk                 → 无依赖（可与 Layer 0 并行）
├── alicloud_disk_attachment      → 依赖 alicloud_disk + alicloud_instance
├── alicloud_db_database          → 依赖 alicloud_db_instance
├── alicloud_db_account           → 依赖 alicloud_db_instance
├── alicloud_slb_attachment       → 依赖 alicloud_slb_load_balancer + alicloud_instance
├── alicloud_alb_server_group     → 依赖 alicloud_alb_load_balancer（服务器绑定）
├── alicloud_nas_mount_target     → 依赖 alicloud_nas_file_system + alicloud_vswitch
└── alicloud_polardb_database     → 依赖 alicloud_polardb_cluster

Layer 5（依赖 Layer 4）
├── alicloud_ess_scaling_group    → 依赖 alicloud_vswitch
├── alicloud_cs_managed_kubernetes → 依赖 alicloud_vpc + alicloud_vswitch
└── alicloud_fc_service           → 无依赖（可与 Layer 0 并行）

Layer 6（依赖 Layer 5）
├── alicloud_ess_scaling_configuration → 依赖 alicloud_ess_scaling_group
├── alicloud_ess_scaling_rule          → 依赖 alicloud_ess_scaling_group
├── alicloud_cs_kubernetes_node_pool   → 依赖 alicloud_cs_managed_kubernetes
└── alicloud_fc_function               → 依赖 alicloud_fc_service
```

---

## 推荐 import 顺序

按以下顺序执行 import，避免依赖错误：

```
批次 1：VPC、OSS Bucket、DNS 域名、RAM 资源、KMS 密钥
批次 2：VSwitch、安全组、路由表、EIP
批次 3：NAT 网关、SLB、ALB、安全组规则
批次 4：ECS 实例、RDS、Redis、MongoDB、NAS
批次 5：云盘挂载、EIP 绑定、SNAT/DNAT、SLB 监听、数据库账号
批次 6：弹性伸缩组、ACK 集群
批次 7：伸缩配置、节点池、FC 函数
```

---

## 各资源的关键依赖属性

### alicloud_vswitch
```hcl
vpc_id    = alicloud_vpc.<name>.id      # 必须引用，不能硬编码
zone_id   = "cn-hangzhou-h"             # 固定值，不引用其他资源
```

### alicloud_security_group
```hcl
vpc_id = alicloud_vpc.<name>.id
```

### alicloud_instance
```hcl
vswitch_id      = alicloud_vswitch.<name>.id
security_groups = [alicloud_security_group.<name>.id]
# 注意：security_groups 是列表，可引用多个安全组
```

### alicloud_nat_gateway
```hcl
vpc_id     = alicloud_vpc.<name>.id
vswitch_id = alicloud_vswitch.<name>.id  # Enhanced 类型必须指定
```

### alicloud_snat_entry
```hcl
snat_table_id     = split(",", alicloud_nat_gateway.<name>.snat_table_ids)[0]
source_vswitch_id = alicloud_vswitch.<name>.id
snat_ip           = alicloud_eip_address.<name>.ip_address
```

### alicloud_eip_association
```hcl
allocation_id = alicloud_eip_address.<name>.id
instance_id   = alicloud_instance.<name>.id
instance_type = "EcsInstance"  # 或 "Nat"、"SlbInstance" 等
```

### alicloud_db_instance
```hcl
vswitch_id = alicloud_vswitch.<name>.id
# 注意：RDS 不直接引用安全组，通过 security_ips 白名单控制访问
```

### alicloud_slb_load_balancer（内网）
```hcl
vswitch_id   = alicloud_vswitch.<name>.id
address_type = "intranet"
```

### alicloud_slb_attachment
```hcl
load_balancer_id = alicloud_slb_load_balancer.<name>.id
instance_ids     = [alicloud_instance.<name>.id]
# 注意：instance_ids 是列表
```

---

## 循环依赖检测

以下组合容易产生循环依赖，需要特别注意：

1. **ECS + 安全组**：ECS 引用安全组，安全组规则引用 ECS 的私有 IP
   - 解决：安全组规则使用 CIDR 而非实例 IP，或使用安全组 ID 互引

2. **SLB + ECS**：SLB 后端引用 ECS，ECS 安全组规则引用 SLB
   - 解决：安全组规则使用 SLB 的 IP 段，不直接引用 SLB 资源

3. **NAT + EIP**：NAT 网关需要 EIP，EIP 绑定需要 NAT 网关 ID
   - 解决：先 import NAT 网关，再 import EIP 绑定关系

---

## 跨 VPC 资源引用

当资源跨 VPC 时（如 VPC Peering），需要额外注意：

```hcl
# VPC Peering 连接
resource "alicloud_vpc_peer_connection" "peer_<name>" {
  peer_connection_name = "<name>"
  vpc_id               = alicloud_vpc.vpc_a.id
  accepting_ali_uid    = "<peer-account-id>"
  accepting_region_id  = "cn-beijing"
  accepting_vpc_id     = "<peer-vpc-id>"
}
```

---

## 多 Region 资源

当需要管理多个 Region 的资源时，使用 provider alias：

```hcl
provider "alicloud" {
  alias      = "beijing"
  region     = "cn-beijing"
  access_key = var.access_key
  secret_key = var.secret_key
}

resource "alicloud_vpc" "vpc_beijing" {
  provider   = alicloud.beijing
  vpc_name   = "prod-beijing"
  cidr_block = "172.16.0.0/12"
}
```
