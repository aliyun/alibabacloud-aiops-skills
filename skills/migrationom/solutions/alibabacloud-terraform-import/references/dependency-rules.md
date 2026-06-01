# Resource Dependency Rules

Resource dependency layer diagram and import order constraints.

---

## Dependency Layer Diagram

```
Layer 0 (no dependencies, can import in parallel)
├── alicloud_vpc
├── alicloud_oss_bucket
├── alicloud_dns_domain
├── alicloud_ram_user
├── alicloud_ram_role
├── alicloud_ram_policy
├── alicloud_kms_key
├── alicloud_key_pair
└── alicloud_image

Layer 1 (depends on Layer 0)
├── alicloud_vswitch              -> depends on alicloud_vpc
├── alicloud_security_group       -> depends on alicloud_vpc
├── alicloud_route_table          -> depends on alicloud_vpc
├── alicloud_eip_address          -> no dependency (can parallel with Layer 0)
├── alicloud_oss_bucket_acl       -> depends on alicloud_oss_bucket
├── alicloud_oss_bucket_policy    -> depends on alicloud_oss_bucket
├── alicloud_dns_record           -> depends on alicloud_dns_domain
└── alicloud_ram_user_policy_attachment -> depends on alicloud_ram_user + alicloud_ram_policy

Layer 2 (depends on Layer 1)
├── alicloud_nat_gateway          -> depends on alicloud_vpc + alicloud_vswitch
├── alicloud_vpn_gateway          -> depends on alicloud_vpc
├── alicloud_slb_load_balancer    -> depends on alicloud_vswitch (intranet)
├── alicloud_alb_load_balancer    -> depends on alicloud_vpc + alicloud_vswitch
├── alicloud_alb_server_group     -> depends on alicloud_vpc
├── alicloud_security_group_rule  -> depends on alicloud_security_group
└── alicloud_route_entry          -> depends on alicloud_route_table

Layer 3 (depends on Layer 2)
├── alicloud_instance             -> depends on alicloud_vswitch + alicloud_security_group
├── alicloud_db_instance          -> depends on alicloud_vswitch
├── alicloud_kvstore_instance     -> depends on alicloud_vswitch
├── alicloud_mongodb_instance     -> depends on alicloud_vswitch
├── alicloud_polardb_cluster      -> depends on alicloud_vswitch
├── alicloud_nas_file_system      -> no dependency (can parallel with Layer 0)
├── alicloud_snat_entry           -> depends on alicloud_nat_gateway
├── alicloud_forward_entry        -> depends on alicloud_nat_gateway
├── alicloud_eip_association      -> depends on alicloud_eip_address + instance
├── alicloud_slb_listener         -> depends on alicloud_slb_load_balancer
└── alicloud_alb_listener         -> depends on alicloud_alb_load_balancer

Layer 4 (depends on Layer 3)
├── alicloud_disk                 -> no dependency (can parallel with Layer 0)
├── alicloud_disk_attachment      -> depends on alicloud_disk + alicloud_instance
├── alicloud_db_database          -> depends on alicloud_db_instance
├── alicloud_db_account           -> depends on alicloud_db_instance
├── alicloud_slb_attachment       -> depends on alicloud_slb_load_balancer + alicloud_instance
├── alicloud_alb_server_group     -> depends on alicloud_alb_load_balancer (server binding)
├── alicloud_nas_mount_target     -> depends on alicloud_nas_file_system + alicloud_vswitch
└── alicloud_polardb_database     -> depends on alicloud_polardb_cluster

Layer 5 (depends on Layer 4)
├── alicloud_ess_scaling_group    -> depends on alicloud_vswitch
├── alicloud_cs_managed_kubernetes -> depends on alicloud_vpc + alicloud_vswitch
└── alicloud_fc_service           -> no dependency (can parallel with Layer 0)

Layer 6 (depends on Layer 5)
├── alicloud_ess_scaling_configuration -> depends on alicloud_ess_scaling_group
├── alicloud_ess_scaling_rule          -> depends on alicloud_ess_scaling_group
├── alicloud_cs_kubernetes_node_pool   -> depends on alicloud_cs_managed_kubernetes
└── alicloud_fc_function               -> depends on alicloud_fc_service
```

---

## Recommended Import Order

Execute imports in the following order to avoid dependency errors:

```
Batch 1: VPC, OSS Bucket, DNS Domain, RAM resources, KMS keys
Batch 2: VSwitch, Security Group, Route Table, EIP
Batch 3: NAT Gateway, SLB, ALB, Security Group Rules
Batch 4: ECS Instance, RDS, Redis, MongoDB, NAS
Batch 5: Disk Attachment, EIP Association, SNAT/DNAT, SLB Listener, DB Accounts
Batch 6: Auto Scaling Groups, ACK Clusters
Batch 7: Scaling Configurations, Node Pools, FC Functions
```

---

## Key Dependency Attributes Per Resource

### alicloud_vswitch
```hcl
vpc_id    = alicloud_vpc.<name>.id      # Must reference, never hardcode
zone_id   = "cn-hangzhou-h"             # Fixed value, does not reference other resources
```

### alicloud_security_group
```hcl
vpc_id = alicloud_vpc.<name>.id
```

### alicloud_instance
```hcl
vswitch_id      = alicloud_vswitch.<name>.id
security_groups = [alicloud_security_group.<name>.id]
# Note: security_groups is a list, can reference multiple security groups
```

### alicloud_nat_gateway
```hcl
vpc_id     = alicloud_vpc.<name>.id
vswitch_id = alicloud_vswitch.<name>.id  # Required for Enhanced type
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
instance_type = "EcsInstance"  # Or "Nat", "SlbInstance", etc.
```

### alicloud_db_instance
```hcl
vswitch_id = alicloud_vswitch.<name>.id
# Note: RDS does not directly reference security groups; access is controlled via security_ips whitelist
```

### alicloud_slb_load_balancer (intranet)
```hcl
vswitch_id   = alicloud_vswitch.<name>.id
address_type = "intranet"
```

### alicloud_slb_attachment
```hcl
load_balancer_id = alicloud_slb_load_balancer.<name>.id
instance_ids     = [alicloud_instance.<name>.id]
# Note: instance_ids is a list
```

---

## Circular Dependency Detection

The following combinations are prone to circular dependencies and require special attention:

1. **ECS + Security Group**: ECS references security group; security group rules reference ECS private IP
   - Solution: Use CIDR in security group rules instead of instance IP, or use security group ID cross-referencing

2. **SLB + ECS**: SLB backend references ECS; ECS security group rules reference SLB
   - Solution: Use SLB IP range in security group rules, don't directly reference SLB resource

3. **NAT + EIP**: NAT Gateway needs EIP; EIP association needs NAT Gateway ID
   - Solution: Import NAT Gateway first, then import EIP association

---

## Cross-VPC Resource References

When resources span VPCs (e.g., VPC Peering), additional attention is needed:

```hcl
# VPC Peering connection
resource "alicloud_vpc_peer_connection" "peer_<name>" {
  peer_connection_name = "<name>"
  vpc_id               = alicloud_vpc.vpc_a.id
  accepting_ali_uid    = "<peer-account-id>"
  accepting_region_id  = "cn-beijing"
  accepting_vpc_id     = "<peer-vpc-id>"
}
```

---

## Multi-Region Resources

When managing resources across multiple Regions, use provider alias:

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
