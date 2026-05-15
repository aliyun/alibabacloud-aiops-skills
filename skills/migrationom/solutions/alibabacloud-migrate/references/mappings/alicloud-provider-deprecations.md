# Alibaba Cloud Provider Deprecation Guardrails

Use this file during Phase 4 code generation together with the full provider catalog in `../alibabacloud-terraform-deploy/references/alicloud-providers.md` or the published deprecated-resource source.

Before writing Terraform and again before validation:

1. Check generated `resource "alicloud_*"` and `data "alicloud_*"` declarations against this file.
2. Check the full provider catalog when available.
3. Treat deprecated entries, invalid aliases, and catalog misses as Phase 4 failures.
4. Fix `.migration-report/alibabacloud-mapped-resources.json` or generated Terraform before continuing.

Columns: **type** (`resource` / `data source` / `invalid alias` / `attribute`), **name** (`alicloud_*` or `resource.attribute`), **status** (`deprecated -> alicloud_X`, `deprecated`, `invalid -> alicloud_X`, or `unsupported -> attribute`), **action**.

## Deprecated Resources

| type | name | status | action |
| --- | --- | --- | --- |
| resource | `alicloud_actiontrail` | deprecated -> `alicloud_actiontrail_trail` | Use replacement. |
| resource | `alicloud_slb` | deprecated -> `alicloud_slb_load_balancer` | Use replacement for SLB generation. |
| resource | `alicloud_cs_kubernetes` | deprecated | Do not generate; remap to a supported ACK resource based on target intent. |
| resource | `alicloud_cs_serverless_kubernetes` | deprecated -> `alicloud_cs_managed_kubernetes` | Use replacement. |
| resource | `alicloud_ram_role_attachment` | deprecated -> `alicloud_ecs_ram_role_attachment` | Use replacement only when attaching a RAM role to ECS instances; do not use for policy attachment. |
| resource | `alicloud_eip` | deprecated -> `alicloud_eip_address` | Use replacement. |
| resource | `alicloud_fc_function` | deprecated -> `alicloud_fcv3_function` | Use replacement for Function Compute v3. |
| resource | `alicloud_fc_service` | deprecated -> `alicloud_fcv3_function` | Use Function Compute v3 resources; do not generate legacy FC service resources. |
| resource | `alicloud_db_account` | deprecated -> `alicloud_rds_account` | Use replacement. |

## Invalid Common Aliases

These names are not valid provider resources. They usually come from guessing service names rather than checking the provider catalog.

| type | name | status | action |
| --- | --- | --- | --- |
| invalid alias | `alicloud_ecs_instance` | invalid -> `alicloud_instance` | Use `alicloud_instance` for ECS instances. |
| invalid alias | `alicloud_rds_instance` | invalid -> `alicloud_db_instance` | Use `alicloud_db_instance` for RDS instances. |

## Invalid Or Deprecated Attributes

| type | name | status | action |
| --- | --- | --- | --- |
| attribute | `alicloud_cs_managed_kubernetes.worker_vswitch_ids` | unsupported -> `vswitch_ids` | Use `vswitch_ids` with at least two VSwitches in different zones. |
| attribute | `alicloud_ram_role.document` | deprecated -> `assume_role_policy_document` | Use `assume_role_policy_document` for RAM role trust policies. |
| attribute | `alicloud_db_database.name` | deprecated -> `data_base_name` | Use `data_base_name` for database names. |
| attribute | `alicloud_oss_bucket.acl` | deprecated -> `alicloud_oss_bucket_acl` | Use a separate `alicloud_oss_bucket_acl` resource for bucket ACL. |
