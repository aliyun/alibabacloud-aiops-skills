# Special Import ID Format Quick Reference

Only covers resources with complex import ID formats that are error-prone. For all other resources, check the provider docs directly:
https://registry.terraform.io/providers/aliyun/alicloud/latest/docs

---

## Composite ID Formats (separated by `:`)

| Resource | Import ID Format | Notes |
|------|---------------|------|
| `alicloud_route_entry` | `<route-table-id>:<cidr>:<nexthop-type>:<nexthop-id>` | 4 segments |
| `alicloud_security_group_rule` | `<sg-id>:<direction>:<ip-protocol>:<port-range>:<priority>:<cidr-ip>:<policy>` | 7 segments, order matters |
| `alicloud_eip_association` | `<eip-id>:<instance-id>` | |
| `alicloud_snat_entry` | `<snat-table-id>:<snat-entry-id>` | snat-table-id obtained from NAT Gateway attributes |
| `alicloud_forward_entry` | `<forward-table-id>:<forward-entry-id>` | forward-table-id obtained from NAT Gateway attributes |
| `alicloud_disk_attachment` | `<disk-id>:<instance-id>` | |
| `alicloud_nas_mount_target` | `<fs-id>:<mount-target-domain>` | domain is the full domain name, not an ID |
| `alicloud_db_database` | `<db-instance-id>:<db-name>` | |
| `alicloud_db_account` | `<db-instance-id>:<account-name>` | |
| `alicloud_db_connection` | `<db-instance-id>:<connection-prefix>` | |
| `alicloud_polardb_database` | `<cluster-id>:<db-name>` | |
| `alicloud_ram_policy` | `<policy-name>:<policy-type>` | policy-type: `Custom` or `System` |
| `alicloud_ram_user_policy_attachment` | `<user-name>:<policy-name>:<policy-type>` | |
| `alicloud_slb_listener` | `<slb-id>:<protocol>_<port>` | Note underscore, e.g., `lb-xxx:http_80` |
| `alicloud_cs_kubernetes_node_pool` | `<cluster-id>:<nodepool-id>` | |
| `alicloud_fc_function` | `<service-name>:<function-name>` | |
| `alicloud_kms_alias` | `alias/<alias-name>` | Must include `alias/` prefix |

---

## Non-ID Fields as Import Identifiers

| Resource | Import Identifier | Notes |
|------|------------|------|
| `alicloud_oss_bucket` | Bucket name | Without `oss://` prefix |
| `alicloud_oss_bucket_acl` | Bucket name | Same as above |
| `alicloud_oss_bucket_policy` | Bucket name | Same as above |
| `alicloud_oss_bucket_cors` | Bucket name | Same as above |
| `alicloud_dns_domain` | Domain string | e.g., `example.com` |
| `alicloud_ram_user` | Username | Not UID |
| `alicloud_ram_role` | Role name | Not ARN |
| `alicloud_key_pair` | Key pair name | Not ID |
| `alicloud_fc_service` | Service name | Not ID |

---

## IDs That Must Be Obtained from Parent Resource Attributes

| Resource | How to Get Required Import ID |
|------|------------------------|
| `alicloud_snat_entry` | `snat_table_id` obtained from `alicloud_nat_gateway.<name>.snat_table_ids` (note: comma-separated string, take the first one) |
| `alicloud_forward_entry` | `forward_table_id` obtained from `alicloud_nat_gateway.<name>.forward_table_ids` |

```bash
# Get NAT Gateway's snat_table_id
aliyun vpc describe-nat-gateways --biz-region-id cn-hangzhou --nat-gateway-id ngw-xxx \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['NatGateways']['NatGateway'][0]['SnatTableIds']['SnatTableId'][0])"
```

---

## Password/Secret Field Handling

After import, the following fields cannot be read from the API and must be handled in HCL:

```hcl
# Option 1: Use variables
resource "alicloud_db_instance" "xxx" {
  # ...
}
variable "rds_password" { sensitive = true }

# Option 2: ignore_changes (recommended, avoids plan diff)
lifecycle {
  ignore_changes = [password, account_password]
}
```

Affected resources: RDS (`password`), Redis (`password`), MongoDB (`account_password`), ECS (`password`)
