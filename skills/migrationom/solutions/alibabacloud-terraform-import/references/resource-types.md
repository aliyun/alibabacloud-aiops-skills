# 特殊 import ID 格式速查

仅收录 import ID 格式复杂、容易出错的资源。其余资源的 import 格式直接查 provider 文档：
https://registry.terraform.io/providers/aliyun/alicloud/latest/docs

---

## 复合 ID 格式（用 `:` 分隔）

| 资源 | import ID 格式 | 说明 |
|------|---------------|------|
| `alicloud_route_entry` | `<route-table-id>:<cidr>:<nexthop-type>:<nexthop-id>` | 4 段 |
| `alicloud_security_group_rule` | `<sg-id>:<direction>:<ip-protocol>:<port-range>:<priority>:<cidr-ip>:<policy>` | 7 段，顺序不能错 |
| `alicloud_eip_association` | `<eip-id>:<instance-id>` | |
| `alicloud_snat_entry` | `<snat-table-id>:<snat-entry-id>` | snat-table-id 从 NAT 网关属性获取 |
| `alicloud_forward_entry` | `<forward-table-id>:<forward-entry-id>` | forward-table-id 从 NAT 网关属性获取 |
| `alicloud_disk_attachment` | `<disk-id>:<instance-id>` | |
| `alicloud_nas_mount_target` | `<fs-id>:<mount-target-domain>` | domain 是完整域名，非 ID |
| `alicloud_db_database` | `<db-instance-id>:<db-name>` | |
| `alicloud_db_account` | `<db-instance-id>:<account-name>` | |
| `alicloud_db_connection` | `<db-instance-id>:<connection-prefix>` | |
| `alicloud_polardb_database` | `<cluster-id>:<db-name>` | |
| `alicloud_ram_policy` | `<policy-name>:<policy-type>` | policy-type: `Custom` 或 `System` |
| `alicloud_ram_user_policy_attachment` | `<user-name>:<policy-name>:<policy-type>` | |
| `alicloud_slb_listener` | `<slb-id>:<protocol>_<port>` | 注意是下划线，如 `lb-xxx:http_80` |
| `alicloud_cs_kubernetes_node_pool` | `<cluster-id>:<nodepool-id>` | |
| `alicloud_fc_function` | `<service-name>:<function-name>` | |
| `alicloud_kms_alias` | `alias/<alias-name>` | 需带 `alias/` 前缀 |

---

## 非 ID 字段作为 import 标识

| 资源 | import 标识 | 说明 |
|------|------------|------|
| `alicloud_oss_bucket` | bucket 名称 | 不含 `oss://` 前缀 |
| `alicloud_oss_bucket_acl` | bucket 名称 | 同上 |
| `alicloud_oss_bucket_policy` | bucket 名称 | 同上 |
| `alicloud_oss_bucket_cors` | bucket 名称 | 同上 |
| `alicloud_dns_domain` | 域名字符串 | 如 `example.com` |
| `alicloud_ram_user` | 用户名 | 非 UID |
| `alicloud_ram_role` | 角色名 | 非 ARN |
| `alicloud_key_pair` | 密钥对名称 | 非 ID |
| `alicloud_fc_service` | 服务名称 | 非 ID |

---

## 需要从父资源属性获取的 ID

| 资源 | 如何获取 import 所需 ID |
|------|------------------------|
| `alicloud_snat_entry` | `snat_table_id` 从 `alicloud_nat_gateway.<name>.snat_table_ids` 获取（注意是逗号分隔的字符串，取第一个） |
| `alicloud_forward_entry` | `forward_table_id` 从 `alicloud_nat_gateway.<name>.forward_table_ids` 获取 |

```bash
# 获取 NAT 网关的 snat_table_id
aliyun vpc describe-nat-gateways --biz-region-id cn-hangzhou --nat-gateway-id ngw-xxx \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['NatGateways']['NatGateway'][0]['SnatTableIds']['SnatTableId'][0])"
```

---

## 密码/密钥字段处理

import 后以下字段无法从 API 读取，需在 HCL 中处理：

```hcl
# 方式 1：用变量
resource "alicloud_db_instance" "xxx" {
  # ...
}
variable "rds_password" { sensitive = true }

# 方式 2：ignore_changes（推荐，避免 plan diff）
lifecycle {
  ignore_changes = [password, account_password]
}
```

涉及资源：RDS（`password`）、Redis（`password`）、MongoDB（`account_password`）、ECS（`password`）
