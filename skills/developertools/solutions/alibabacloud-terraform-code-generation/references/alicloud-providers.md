# Alibaba Cloud Terraform provider catalog

Total entries: **1854** (resources: 1120, data sources: 734; deprecated: 117).

Built from `aliyun/terraform-provider-alicloud@master` by `scripts/build_alicloud_providers.py`. Re-run the script to refresh.

Columns — **type** (resource / data source), **name** (`alicloud_*`), **status** (empty = supported; `⚠️ 弃用 → alicloud_X` = deprecated, use X; `⚠️ 弃用` = deprecated without a direct replacement), **doc** (GitHub source, used by Step 4.2 WebFetch).

## APIG

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_apig_environment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/apig_environment.html.markdown) |
| resource | `alicloud_apig_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/apig_gateway.html.markdown) |
| resource | `alicloud_apig_http_api` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/apig_http_api.html.markdown) |

## Ack One

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_ack_one_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ack_one_cluster.html.markdown) |
| resource | `alicloud_ack_one_membership_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ack_one_membership_attachment.html.markdown) |

## Actiontrail

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_actiontrail_global_events_storage_region` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/actiontrail_global_events_storage_region.html.markdown) |
| data source | `alicloud_actiontrail_history_delivery_jobs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/actiontrail_history_delivery_jobs.html.markdown) |
| data source | `alicloud_actiontrail_trails` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/actiontrail_trails.html.markdown) |
| data source | `alicloud_actiontrails` | ⚠️ 弃用 → `alicloud_actiontrail_trails` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/actiontrails.html.markdown) |
| resource | `alicloud_actiontrail` | ⚠️ 弃用 → `alicloud_actiontrail_trail` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail.html.markdown) |
| resource | `alicloud_actiontrail_advanced_query_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_advanced_query_template.html.markdown) |
| resource | `alicloud_actiontrail_global_events_storage_region` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_global_events_storage_region.html.markdown) |
| resource | `alicloud_actiontrail_history_delivery_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_history_delivery_job.html.markdown) |
| resource | `alicloud_actiontrail_trail` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_trail.html.markdown) |

## AliKafka

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_alikafka_consumer_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alikafka_consumer_groups.html.markdown) |
| data source | `alicloud_alikafka_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alikafka_instances.html.markdown) |
| data source | `alicloud_alikafka_sasl_acls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alikafka_sasl_acls.html.markdown) |
| data source | `alicloud_alikafka_sasl_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alikafka_sasl_users.html.markdown) |
| data source | `alicloud_alikafka_topics` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alikafka_topics.html.markdown) |
| resource | `alicloud_alikafka_consumer_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_consumer_group.html.markdown) |
| resource | `alicloud_alikafka_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_instance.html.markdown) |
| resource | `alicloud_alikafka_instance_allowed_ip_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_instance_allowed_ip_attachment.html.markdown) |
| resource | `alicloud_alikafka_sasl_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_sasl_acl.html.markdown) |
| resource | `alicloud_alikafka_sasl_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_sasl_user.html.markdown) |
| resource | `alicloud_alikafka_scheduled_scaling_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_scheduled_scaling_rule.html.markdown) |
| resource | `alicloud_alikafka_topic` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_topic.html.markdown) |

## Alidns

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_alidns_access_strategies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_access_strategies.html.markdown) |
| data source | `alicloud_alidns_address_pools` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_address_pools.html.markdown) |
| data source | `alicloud_alidns_custom_lines` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_custom_lines.html.markdown) |
| data source | `alicloud_alidns_domain_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_domain_groups.html.markdown) |
| data source | `alicloud_alidns_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_domains.html.markdown) |
| data source | `alicloud_alidns_gtm_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_gtm_instances.html.markdown) |
| data source | `alicloud_alidns_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_instances.html.markdown) |
| data source | `alicloud_alidns_records` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alidns_records.html.markdown) |
| data source | `alicloud_dns_domain_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_domain_groups.html.markdown) |
| data source | `alicloud_dns_domain_records` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_domain_records.html.markdown) |
| data source | `alicloud_dns_domain_txt_guid` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_domain_txt_guid.html.markdown) |
| data source | `alicloud_dns_domains` | ⚠️ 弃用 → `alicloud_alidns_domains` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_domains.html.markdown) |
| data source | `alicloud_dns_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_groups.html.markdown) |
| data source | `alicloud_dns_instances` | ⚠️ 弃用 → `alicloud_alidns_instances` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_instances.html.markdown) |
| data source | `alicloud_dns_records` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_records.html.markdown) |
| data source | `alicloud_dns_resolution_lines` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dns_resolution_lines.html.markdown) |
| resource | `alicloud_alidns_access_strategy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_access_strategy.html.markdown) |
| resource | `alicloud_alidns_address_pool` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_address_pool.html.markdown) |
| resource | `alicloud_alidns_custom_line` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_custom_line.html.markdown) |
| resource | `alicloud_alidns_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_domain.html.markdown) |
| resource | `alicloud_alidns_domain_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_domain_attachment.html.markdown) |
| resource | `alicloud_alidns_domain_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_domain_group.html.markdown) |
| resource | `alicloud_alidns_gtm_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_gtm_instance.html.markdown) |
| resource | `alicloud_alidns_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_instance.html.markdown) |
| resource | `alicloud_alidns_monitor_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_monitor_config.html.markdown) |
| resource | `alicloud_alidns_record` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_record.html.markdown) |
| resource | `alicloud_dns` | ⚠️ 弃用 → `alicloud_alidns_domain` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns.html.markdown) |
| resource | `alicloud_dns_domain` | ⚠️ 弃用 → `alicloud_alidns_domain` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_domain.html.markdown) |
| resource | `alicloud_dns_domain_attachment` | ⚠️ 弃用 → `alicloud_alidns_domain_attachment` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_domain_attachment.html.markdown) |
| resource | `alicloud_dns_group` | ⚠️ 弃用 → `alicloud_alidns_domain_group` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_group.html.markdown) |
| resource | `alicloud_dns_instance` | ⚠️ 弃用 → `alicloud_alidns_instance` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_instance.html.markdown) |
| resource | `alicloud_dns_record` | ⚠️ 弃用 → `alicloud_alidns_record` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_record.html.markdown) |

## Aligreen

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_aligreen_audit_callback` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_audit_callback.html.markdown) |
| resource | `alicloud_aligreen_biz_type` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_biz_type.html.markdown) |
| resource | `alicloud_aligreen_callback` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_callback.html.markdown) |
| resource | `alicloud_aligreen_image_lib` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_image_lib.html.markdown) |
| resource | `alicloud_aligreen_keyword_lib` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_keyword_lib.html.markdown) |
| resource | `alicloud_aligreen_oss_stock_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_oss_stock_task.html.markdown) |

## AnalyticDB for MySQL (ADB)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_adb_clusters` | ⚠️ 弃用 → `alicloud_adb_db_clusters` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/adb_clusters.html.markdown) |
| data source | `alicloud_adb_db_cluster_lake_versions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/adb_db_cluster_lake_versions.html.markdown) |
| data source | `alicloud_adb_db_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/adb_db_clusters.html.markdown) |
| data source | `alicloud_adb_resource_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/adb_resource_groups.html.markdown) |
| data source | `alicloud_adb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/adb_zones.html.markdown) |
| resource | `alicloud_adb_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_account.html.markdown) |
| resource | `alicloud_adb_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_backup_policy.html.markdown) |
| resource | `alicloud_adb_cluster` | ⚠️ 弃用 → `alicloud_adb_db_cluster` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_cluster.html.markdown) |
| resource | `alicloud_adb_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_connection.html.markdown) |
| resource | `alicloud_adb_db_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_db_cluster.html.markdown) |
| resource | `alicloud_adb_db_cluster_lake_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_db_cluster_lake_version.html.markdown) |
| resource | `alicloud_adb_lake_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_lake_account.html.markdown) |
| resource | `alicloud_adb_resource_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_resource_group.html.markdown) |

## AnalyticDB for PostgreSQL (GPDB)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_gpdb_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/gpdb_accounts.html.markdown) |
| data source | `alicloud_gpdb_data_backups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/gpdb_data_backups.html.markdown) |
| data source | `alicloud_gpdb_db_instance_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/gpdb_db_instance_plans.html.markdown) |
| data source | `alicloud_gpdb_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/gpdb_instances.html.markdown) |
| data source | `alicloud_gpdb_log_backups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/gpdb_log_backups.html.markdown) |
| data source | `alicloud_gpdb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/gpdb_zones.html.markdown) |
| resource | `alicloud_gpdb_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_account.html.markdown) |
| resource | `alicloud_gpdb_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_backup_policy.html.markdown) |
| resource | `alicloud_gpdb_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_connection.html.markdown) |
| resource | `alicloud_gpdb_database` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_database.html.markdown) |
| resource | `alicloud_gpdb_db_instance_ip_array` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_db_instance_ip_array.html.markdown) |
| resource | `alicloud_gpdb_db_instance_plan` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_db_instance_plan.html.markdown) |
| resource | `alicloud_gpdb_db_resource_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_db_resource_group.html.markdown) |
| resource | `alicloud_gpdb_elastic_instance` | ⚠️ 弃用 → `alicloud_gpdb_instance` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_elastic_instance.html.markdown) |
| resource | `alicloud_gpdb_external_data_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_external_data_service.html.markdown) |
| resource | `alicloud_gpdb_hadoop_data_source` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_hadoop_data_source.html.markdown) |
| resource | `alicloud_gpdb_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_instance.html.markdown) |
| resource | `alicloud_gpdb_jdbc_data_source` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_jdbc_data_source.html.markdown) |
| resource | `alicloud_gpdb_remote_adb_data_source` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_remote_adb_data_source.html.markdown) |
| resource | `alicloud_gpdb_streaming_data_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_streaming_data_service.html.markdown) |
| resource | `alicloud_gpdb_streaming_data_source` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_streaming_data_source.html.markdown) |
| resource | `alicloud_gpdb_streaming_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_streaming_job.html.markdown) |
| resource | `alicloud_gpdb_supabase_project` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_supabase_project.html.markdown) |

## Anti-DDoS Pro (DdosBgp)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ddosbgp_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ddosbgp_instances.html.markdown) |
| data source | `alicloud_ddosbgp_ips` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ddosbgp_ips.html.markdown) |
| resource | `alicloud_ddos_bgp_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddos_bgp_policy.html.markdown) |
| resource | `alicloud_ddosbgp_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddosbgp_instance.html.markdown) |
| resource | `alicloud_ddosbgp_ip` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddosbgp_ip.html.markdown) |

## Anti-DDoS Pro (DdosCoo)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ddoscoo_domain_resources` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ddoscoo_domain_resources.html.markdown) |
| data source | `alicloud_ddoscoo_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ddoscoo_instances.html.markdown) |
| data source | `alicloud_ddoscoo_ports` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ddoscoo_ports.html.markdown) |
| resource | `alicloud_ddoscoo_domain_precise_access_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_domain_precise_access_rule.html.markdown) |
| resource | `alicloud_ddoscoo_domain_resource` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_domain_resource.html.markdown) |
| resource | `alicloud_ddoscoo_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_instance.html.markdown) |
| resource | `alicloud_ddoscoo_port` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_port.html.markdown) |
| resource | `alicloud_ddoscoo_scheduler_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_scheduler_rule.html.markdown) |
| resource | `alicloud_ddoscoo_web_cc_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_web_cc_rule.html.markdown) |

## Anycast Elastic IP Address (Eipanycast)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_eipanycast_anycast_eip_addresses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eipanycast_anycast_eip_addresses.html.markdown) |
| resource | `alicloud_eipanycast_anycast_eip_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eipanycast_anycast_eip_address.html.markdown) |
| resource | `alicloud_eipanycast_anycast_eip_address_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eipanycast_anycast_eip_address_attachment.html.markdown) |

## Api Gateway

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_api_gateway_apis` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_apis.html.markdown) |
| data source | `alicloud_api_gateway_apps` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_apps.html.markdown) |
| data source | `alicloud_api_gateway_backends` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_backends.html.markdown) |
| data source | `alicloud_api_gateway_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_groups.html.markdown) |
| data source | `alicloud_api_gateway_log_configs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_log_configs.html.markdown) |
| data source | `alicloud_api_gateway_models` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_models.html.markdown) |
| data source | `alicloud_api_gateway_plugins` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_plugins.html.markdown) |
| data source | `alicloud_api_gateway_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/api_gateway_service.html.markdown) |
| resource | `alicloud_api_gateway_access_control_list` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_access_control_list.html.markdown) |
| resource | `alicloud_api_gateway_acl_entry_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_acl_entry_attachment.html.markdown) |
| resource | `alicloud_api_gateway_api` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_api.html.markdown) |
| resource | `alicloud_api_gateway_app` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_app.html.markdown) |
| resource | `alicloud_api_gateway_app_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_app_attachment.html.markdown) |
| resource | `alicloud_api_gateway_backend` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_backend.html.markdown) |
| resource | `alicloud_api_gateway_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_group.html.markdown) |
| resource | `alicloud_api_gateway_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_instance.html.markdown) |
| resource | `alicloud_api_gateway_instance_acl_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_instance_acl_attachment.html.markdown) |
| resource | `alicloud_api_gateway_log_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_log_config.html.markdown) |
| resource | `alicloud_api_gateway_model` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_model.html.markdown) |
| resource | `alicloud_api_gateway_plugin` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_plugin.html.markdown) |
| resource | `alicloud_api_gateway_plugin_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_plugin_attachment.html.markdown) |
| resource | `alicloud_api_gateway_vpc_access` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_vpc_access.html.markdown) |

## Application Load Balancer (ALB)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_alb_acls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_acls.html.markdown) |
| data source | `alicloud_alb_ascripts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_ascripts.html.markdown) |
| data source | `alicloud_alb_health_check_templates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_health_check_templates.html.markdown) |
| data source | `alicloud_alb_listeners` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_listeners.html.markdown) |
| data source | `alicloud_alb_load_balancers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_load_balancers.html.markdown) |
| data source | `alicloud_alb_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_rules.html.markdown) |
| data source | `alicloud_alb_security_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_security_policies.html.markdown) |
| data source | `alicloud_alb_server_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_server_groups.html.markdown) |
| data source | `alicloud_alb_system_security_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_system_security_policies.html.markdown) |
| data source | `alicloud_alb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/alb_zones.html.markdown) |
| resource | `alicloud_alb_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_acl.html.markdown) |
| resource | `alicloud_alb_acl_entry_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_acl_entry_attachment.html.markdown) |
| resource | `alicloud_alb_ascript` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_ascript.html.markdown) |
| resource | `alicloud_alb_health_check_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_health_check_template.html.markdown) |
| resource | `alicloud_alb_listener` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_listener.html.markdown) |
| resource | `alicloud_alb_listener_acl_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_listener_acl_attachment.html.markdown) |
| resource | `alicloud_alb_listener_additional_certificate_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_listener_additional_certificate_attachment.html.markdown) |
| resource | `alicloud_alb_load_balancer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer.html.markdown) |
| resource | `alicloud_alb_load_balancer_access_log_config_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_access_log_config_attachment.html.markdown) |
| resource | `alicloud_alb_load_balancer_common_bandwidth_package_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_common_bandwidth_package_attachment.html.markdown) |
| resource | `alicloud_alb_load_balancer_security_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_security_group_attachment.html.markdown) |
| resource | `alicloud_alb_load_balancer_zone_shifted_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_zone_shifted_attachment.html.markdown) |
| resource | `alicloud_alb_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_rule.html.markdown) |
| resource | `alicloud_alb_security_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_security_policy.html.markdown) |
| resource | `alicloud_alb_server_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_server_group.html.markdown) |

## Application Real-Time Monitoring Service (ARMS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_arms_addon_releases` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_addon_releases.html.markdown) |
| data source | `alicloud_arms_alert_contact_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_alert_contact_groups.html.markdown) |
| data source | `alicloud_arms_alert_contacts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_alert_contacts.html.markdown) |
| data source | `alicloud_arms_alert_robots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_alert_robots.html.markdown) |
| data source | `alicloud_arms_dispatch_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_dispatch_rules.html.markdown) |
| data source | `alicloud_arms_env_custom_jobs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_env_custom_jobs.html.markdown) |
| data source | `alicloud_arms_env_features` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_env_features.html.markdown) |
| data source | `alicloud_arms_env_pod_monitors` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_env_pod_monitors.html.markdown) |
| data source | `alicloud_arms_env_service_monitors` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_env_service_monitors.html.markdown) |
| data source | `alicloud_arms_environments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_environments.html.markdown) |
| data source | `alicloud_arms_integration_exporters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_integration_exporters.html.markdown) |
| data source | `alicloud_arms_prometheis` | ⚠️ 弃用 → `alicloud_arms_prometheus` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_prometheis.html.markdown) |
| data source | `alicloud_arms_prometheus` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_prometheus.html.markdown) |
| data source | `alicloud_arms_prometheus_alert_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_prometheus_alert_rules.html.markdown) |
| data source | `alicloud_arms_prometheus_monitorings` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_prometheus_monitorings.html.markdown) |
| data source | `alicloud_arms_remote_writes` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/arms_remote_writes.html.markdown) |
| resource | `alicloud_arms_addon_release` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_addon_release.html.markdown) |
| resource | `alicloud_arms_alert_contact` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_alert_contact.html.markdown) |
| resource | `alicloud_arms_alert_contact_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_alert_contact_group.html.markdown) |
| resource | `alicloud_arms_alert_robot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_alert_robot.html.markdown) |
| resource | `alicloud_arms_dispatch_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_dispatch_rule.html.markdown) |
| resource | `alicloud_arms_env_custom_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_custom_job.html.markdown) |
| resource | `alicloud_arms_env_feature` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_feature.html.markdown) |
| resource | `alicloud_arms_env_pod_monitor` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_pod_monitor.html.markdown) |
| resource | `alicloud_arms_env_service_monitor` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_service_monitor.html.markdown) |
| resource | `alicloud_arms_environment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_environment.html.markdown) |
| resource | `alicloud_arms_grafana_workspace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_grafana_workspace.html.markdown) |
| resource | `alicloud_arms_integration_exporter` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_integration_exporter.html.markdown) |
| resource | `alicloud_arms_prometheus` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_prometheus.html.markdown) |
| resource | `alicloud_arms_prometheus_alert_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_prometheus_alert_rule.html.markdown) |
| resource | `alicloud_arms_prometheus_monitoring` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_prometheus_monitoring.html.markdown) |
| resource | `alicloud_arms_remote_write` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_remote_write.html.markdown) |
| resource | `alicloud_arms_synthetic_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_synthetic_task.html.markdown) |

## Apsara Agile Live (IMP)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_imp_app_templates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/imp_app_templates.html.markdown) |
| resource | `alicloud_imp_app_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/imp_app_template.html.markdown) |

## Apsara Devops(RDC)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_rdc_organizations` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rdc_organizations.html.markdown) |
| resource | `alicloud_rdc_organization` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rdc_organization.html.markdown) |

## Apsara File Storage for HDFS (DFS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_dfs_access_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dfs_access_groups.html.markdown) |
| data source | `alicloud_dfs_access_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dfs_access_rules.html.markdown) |
| data source | `alicloud_dfs_file_systems` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dfs_file_systems.html.markdown) |
| data source | `alicloud_dfs_mount_points` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dfs_mount_points.html.markdown) |
| data source | `alicloud_dfs_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dfs_zones.html.markdown) |
| resource | `alicloud_dfs_access_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_access_group.html.markdown) |
| resource | `alicloud_dfs_access_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_access_rule.html.markdown) |
| resource | `alicloud_dfs_file_system` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_file_system.html.markdown) |
| resource | `alicloud_dfs_mount_point` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_mount_point.html.markdown) |
| resource | `alicloud_dfs_vsc_mount_point` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_vsc_mount_point.html.markdown) |

## ApsaraDB for MyBase (CDDC)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cddc_dedicated_host_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cddc_dedicated_host_accounts.html.markdown) |
| data source | `alicloud_cddc_dedicated_host_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cddc_dedicated_host_groups.html.markdown) |
| data source | `alicloud_cddc_dedicated_hosts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cddc_dedicated_hosts.html.markdown) |
| data source | `alicloud_cddc_host_ecs_level_infos` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cddc_host_ecs_level_infos.html.markdown) |
| data source | `alicloud_cddc_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cddc_zones.html.markdown) |
| resource | `alicloud_cddc_dedicated_host` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_host.html.markdown) |
| resource | `alicloud_cddc_dedicated_host_account` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_host_account.html.markdown) |
| resource | `alicloud_cddc_dedicated_host_group` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_host_group.html.markdown) |
| resource | `alicloud_cddc_dedicated_propre_host` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_propre_host.html.markdown) |

## ApsaraVideo VoD (VOD)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_vod_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vod_domains.html.markdown) |
| resource | `alicloud_vod_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vod_domain.html.markdown) |
| resource | `alicloud_vod_editing_project` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vod_editing_project.html.markdown) |

## Auto Scaling

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ess_alarms` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ess_alarms.html.markdown) |
| data source | `alicloud_ess_lifecycle_hooks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ess_lifecycle_hooks.html.markdown) |
| data source | `alicloud_ess_notifications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ess_notifications.html.markdown) |
| data source | `alicloud_ess_scaling_configurations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ess_scaling_configurations.html.markdown) |
| data source | `alicloud_ess_scaling_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ess_scaling_groups.html.markdown) |
| data source | `alicloud_ess_scaling_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ess_scaling_rules.html.markdown) |
| data source | `alicloud_ess_scheduled_tasks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ess_scheduled_tasks.html.markdown) |
| resource | `alicloud_ess_alarm` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_alarm.html.markdown) |
| resource | `alicloud_ess_alb_server_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_alb_server_group_attachment.html.markdown) |
| resource | `alicloud_ess_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_attachment.html.markdown) |
| resource | `alicloud_ess_eci_scaling_configuration` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_eci_scaling_configuration.html.markdown) |
| resource | `alicloud_ess_instance_refresh` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_instance_refresh.html.markdown) |
| resource | `alicloud_ess_lifecycle_hook` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_lifecycle_hook.html.markdown) |
| resource | `alicloud_ess_notification` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_notification.html.markdown) |
| resource | `alicloud_ess_scaling_configuration` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scaling_configuration.html.markdown) |
| resource | `alicloud_ess_scaling_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scaling_group.html.markdown) |
| resource | `alicloud_ess_scaling_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scaling_rule.html.markdown) |
| resource | `alicloud_ess_scalinggroup_vserver_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scalinggroup_vserver_groups.html.markdown) |
| resource | `alicloud_ess_schedule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_schedule.html.markdown) |
| resource | `alicloud_ess_scheduled_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scheduled_task.html.markdown) |
| resource | `alicloud_ess_server_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_server_group_attachment.html.markdown) |
| resource | `alicloud_ess_suspend_process` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_suspend_process.html.markdown) |

## Bastion Host

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_bastionhost_host_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bastionhost_host_accounts.html.markdown) |
| data source | `alicloud_bastionhost_host_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bastionhost_host_groups.html.markdown) |
| data source | `alicloud_bastionhost_host_share_keys` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bastionhost_host_share_keys.html.markdown) |
| data source | `alicloud_bastionhost_hosts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bastionhost_hosts.html.markdown) |
| data source | `alicloud_bastionhost_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bastionhost_instances.html.markdown) |
| data source | `alicloud_bastionhost_user_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bastionhost_user_groups.html.markdown) |
| data source | `alicloud_bastionhost_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bastionhost_users.html.markdown) |
| resource | `alicloud_bastionhost_host` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host.html.markdown) |
| resource | `alicloud_bastionhost_host_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account.html.markdown) |
| resource | `alicloud_bastionhost_host_account_share_key_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account_share_key_attachment.html.markdown) |
| resource | `alicloud_bastionhost_host_account_user_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account_user_attachment.html.markdown) |
| resource | `alicloud_bastionhost_host_account_user_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account_user_group_attachment.html.markdown) |
| resource | `alicloud_bastionhost_host_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_attachment.html.markdown) |
| resource | `alicloud_bastionhost_host_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_group.html.markdown) |
| resource | `alicloud_bastionhost_host_group_account_user_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_group_account_user_attachment.html.markdown) |
| resource | `alicloud_bastionhost_host_group_account_user_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_group_account_user_group_attachment.html.markdown) |
| resource | `alicloud_bastionhost_host_share_key` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_share_key.html.markdown) |
| resource | `alicloud_bastionhost_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_instance.html.markdown) |
| resource | `alicloud_bastionhost_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_user.html.markdown) |
| resource | `alicloud_bastionhost_user_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_user_attachment.html.markdown) |
| resource | `alicloud_bastionhost_user_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_user_group.html.markdown) |

## Brain Industrial

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_brain_industrial_pid_loops` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/brain_industrial_pid_loops.html.markdown) |
| data source | `alicloud_brain_industrial_pid_organizations` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/brain_industrial_pid_organizations.html.markdown) |
| data source | `alicloud_brain_industrial_pid_projects` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/brain_industrial_pid_projects.html.markdown) |
| data source | `alicloud_brain_industrial_service` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/brain_industrial_service.html.markdown) |
| resource | `alicloud_brain_industrial_pid_loop` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/brain_industrial_pid_loop.html.markdown) |
| resource | `alicloud_brain_industrial_pid_organization` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/brain_industrial_pid_organization.html.markdown) |
| resource | `alicloud_brain_industrial_pid_project` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/brain_industrial_pid_project.html.markdown) |

## Bss Open Api

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_bss_open_api_pricing_modules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bss_open_api_pricing_modules.html.markdown) |
| data source | `alicloud_bss_openapi_products` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bss_openapi_products.html.markdown) |

## CDN

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cdn_blocked_regions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cdn_blocked_regions.html.markdown) |
| data source | `alicloud_cdn_ip_info` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cdn_ip_info.html.markdown) |
| data source | `alicloud_cdn_real_time_log_deliveries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cdn_real_time_log_deliveries.html.markdown) |
| data source | `alicloud_cdn_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cdn_service.html.markdown) |
| resource | `alicloud_cdn_domain_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_domain_config.html.markdown) |
| resource | `alicloud_cdn_domain_new` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_domain_new.html.markdown) |
| resource | `alicloud_cdn_fc_trigger` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_fc_trigger.html.markdown) |
| resource | `alicloud_cdn_real_time_log_delivery` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_real_time_log_delivery.html.markdown) |

## Cassandra

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cassandra_backup_plans` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cassandra_backup_plans.html.markdown) |
| data source | `alicloud_cassandra_clusters` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cassandra_clusters.html.markdown) |
| data source | `alicloud_cassandra_data_centers` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cassandra_data_centers.html.markdown) |
| data source | `alicloud_cassandra_zones` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cassandra_zones.html.markdown) |
| resource | `alicloud_cassandra_backup_plan` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cassandra_backup_plan.html.markdown) |
| resource | `alicloud_cassandra_cluster` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cassandra_cluster.html.markdown) |
| resource | `alicloud_cassandra_data_center` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cassandra_data_center.html.markdown) |

## Certificate Management Service (Original SSL Certificate)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cas_certificates` | ⚠️ 弃用 → `alicloud_ssl_certificates_service_certificates` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cas_certificates.html.markdown) |
| data source | `alicloud_ssl_certificates_service_certificates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ssl_certificates_service_certificates.html.markdown) |
| resource | `alicloud_cas_certificate` | ⚠️ 弃用 → `alicloud_ssl_certificates_service_certificate` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cas_certificate.html.markdown) |
| resource | `alicloud_ssl_certificates_service_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_certificates_service_certificate.html.markdown) |
| resource | `alicloud_ssl_certificates_service_pca_cert` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_certificates_service_pca_cert.html.markdown) |
| resource | `alicloud_ssl_certificates_service_pca_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_certificates_service_pca_certificate.html.markdown) |

## Chatbot

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_chatbot_agents` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/chatbot_agents.html.markdown) |
| resource | `alicloud_chatbot_publish_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/chatbot_publish_task.html.markdown) |

## Classic Load Balancer (SLB)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_slb_acls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_acls.html.markdown) |
| data source | `alicloud_slb_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_attachments.html.markdown) |
| data source | `alicloud_slb_backend_servers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_backend_servers.html.markdown) |
| data source | `alicloud_slb_ca_certificates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_ca_certificates.html.markdown) |
| data source | `alicloud_slb_domain_extensions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_domain_extensions.html.markdown) |
| data source | `alicloud_slb_listeners` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_listeners.html.markdown) |
| data source | `alicloud_slb_load_balancers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_load_balancers.html.markdown) |
| data source | `alicloud_slb_master_slave_server_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_master_slave_server_groups.html.markdown) |
| data source | `alicloud_slb_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_rules.html.markdown) |
| data source | `alicloud_slb_server_certificates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_server_certificates.html.markdown) |
| data source | `alicloud_slb_server_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_server_groups.html.markdown) |
| data source | `alicloud_slb_tls_cipher_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_tls_cipher_policies.html.markdown) |
| data source | `alicloud_slb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slb_zones.html.markdown) |
| data source | `alicloud_slbs` | ⚠️ 弃用 → `alicloud_slb_load_balancers` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/slbs.html.markdown) |
| resource | `alicloud_slb` | ⚠️ 弃用 → `alicloud_slb_load_balancer` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb.html.markdown) |
| resource | `alicloud_slb_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_acl.html.markdown) |
| resource | `alicloud_slb_acl_entry_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_acl_entry_attachment.html.markdown) |
| resource | `alicloud_slb_attachment` | ⚠️ 弃用 → `alicloud_slb_backend_server` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_attachment.html.markdown) |
| resource | `alicloud_slb_backend_server` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_backend_server.html.markdown) |
| resource | `alicloud_slb_ca_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_ca_certificate.html.markdown) |
| resource | `alicloud_slb_domain_extension` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_domain_extension.html.markdown) |
| resource | `alicloud_slb_listener` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_listener.html.markdown) |
| resource | `alicloud_slb_load_balancer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_load_balancer.html.markdown) |
| resource | `alicloud_slb_master_slave_server_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_master_slave_server_group.html.markdown) |
| resource | `alicloud_slb_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_rule.html.markdown) |
| resource | `alicloud_slb_server_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_server_certificate.html.markdown) |
| resource | `alicloud_slb_server_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_server_group.html.markdown) |
| resource | `alicloud_slb_server_group_server_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_server_group_server_attachment.html.markdown) |
| resource | `alicloud_slb_tls_cipher_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_tls_cipher_policy.html.markdown) |

## Click House

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_click_house_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/click_house_accounts.html.markdown) |
| data source | `alicloud_click_house_backup_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/click_house_backup_policies.html.markdown) |
| data source | `alicloud_click_house_db_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/click_house_db_clusters.html.markdown) |
| data source | `alicloud_click_house_regions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/click_house_regions.html.markdown) |
| resource | `alicloud_click_house_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_account.html.markdown) |
| resource | `alicloud_click_house_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_backup_policy.html.markdown) |
| resource | `alicloud_click_house_db_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_db_cluster.html.markdown) |
| resource | `alicloud_click_house_enterprise_db_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster.html.markdown) |
| resource | `alicloud_click_house_enterprise_db_cluster_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_account.html.markdown) |
| resource | `alicloud_click_house_enterprise_db_cluster_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_backup_policy.html.markdown) |
| resource | `alicloud_click_house_enterprise_db_cluster_computing_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_computing_group.html.markdown) |
| resource | `alicloud_click_house_enterprise_db_cluster_public_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_public_endpoint.html.markdown) |
| resource | `alicloud_click_house_enterprise_db_cluster_security_ip` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_security_ip.html.markdown) |

## Cloud Architect Design Tools (BPStudio)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_bp_studio_applications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/bp_studio_applications.html.markdown) |
| resource | `alicloud_bp_studio_application` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bp_studio_application.html.markdown) |

## Cloud Config (Config)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_config_aggregate_compliance_packs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_aggregate_compliance_packs.html.markdown) |
| data source | `alicloud_config_aggregate_config_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_aggregate_config_rules.html.markdown) |
| data source | `alicloud_config_aggregate_deliveries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_aggregate_deliveries.html.markdown) |
| data source | `alicloud_config_aggregators` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_aggregators.html.markdown) |
| data source | `alicloud_config_compliance_packs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_compliance_packs.html.markdown) |
| data source | `alicloud_config_configuration_recorders` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_configuration_recorders.html.markdown) |
| data source | `alicloud_config_deliveries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_deliveries.html.markdown) |
| data source | `alicloud_config_delivery_channels` | ⚠️ 弃用 → `alicloud_config_deliveries` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_delivery_channels.html.markdown) |
| data source | `alicloud_config_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/config_rules.html.markdown) |
| resource | `alicloud_config_aggregate_compliance_pack` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_compliance_pack.html.markdown) |
| resource | `alicloud_config_aggregate_config_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_config_rule.html.markdown) |
| resource | `alicloud_config_aggregate_delivery` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_delivery.html.markdown) |
| resource | `alicloud_config_aggregate_remediation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_remediation.html.markdown) |
| resource | `alicloud_config_aggregator` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregator.html.markdown) |
| resource | `alicloud_config_compliance_pack` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_compliance_pack.html.markdown) |
| resource | `alicloud_config_configuration_recorder` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_configuration_recorder.html.markdown) |
| resource | `alicloud_config_delivery` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_delivery.html.markdown) |
| resource | `alicloud_config_delivery_channel` | ⚠️ 弃用 → `alicloud_config_delivery` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_delivery_channel.html.markdown) |
| resource | `alicloud_config_remediation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_remediation.html.markdown) |
| resource | `alicloud_config_report_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_report_template.html.markdown) |
| resource | `alicloud_config_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_rule.html.markdown) |

## Cloud Control

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cloud_control_prices` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_control_prices.html.markdown) |
| data source | `alicloud_cloud_control_products` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_control_products.html.markdown) |
| data source | `alicloud_cloud_control_resource_types` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_control_resource_types.html.markdown) |
| resource | `alicloud_cloud_control_resource` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_control_resource.html.markdown) |

## Cloud DBAudit (DBAudit)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_yundun_dbaudit_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/yundun_dbaudit_instances.html.markdown) |
| resource | `alicloud_yundun_dbaudit_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/yundun_dbaudit_instance.html.markdown) |

## Cloud Enterprise Network (CEN)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cen_bandwidth_limits` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_bandwidth_limits.html.markdown) |
| data source | `alicloud_cen_bandwidth_packages` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_bandwidth_packages.html.markdown) |
| data source | `alicloud_cen_child_instance_route_entry_to_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_child_instance_route_entry_to_attachments.html.markdown) |
| data source | `alicloud_cen_flowlogs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_flowlogs.html.markdown) |
| data source | `alicloud_cen_instance_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_instance_attachments.html.markdown) |
| data source | `alicloud_cen_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_instances.html.markdown) |
| data source | `alicloud_cen_inter_region_traffic_qos_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_inter_region_traffic_qos_policies.html.markdown) |
| data source | `alicloud_cen_inter_region_traffic_qos_queues` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_inter_region_traffic_qos_queues.html.markdown) |
| data source | `alicloud_cen_private_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_private_zones.html.markdown) |
| data source | `alicloud_cen_region_route_entries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_region_route_entries.html.markdown) |
| data source | `alicloud_cen_route_entries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_route_entries.html.markdown) |
| data source | `alicloud_cen_route_maps` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_route_maps.html.markdown) |
| data source | `alicloud_cen_route_services` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_route_services.html.markdown) |
| data source | `alicloud_cen_traffic_marking_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_traffic_marking_policies.html.markdown) |
| data source | `alicloud_cen_transit_route_table_aggregations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_route_table_aggregations.html.markdown) |
| data source | `alicloud_cen_transit_router_available_resources` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_available_resources.html.markdown) |
| data source | `alicloud_cen_transit_router_cidrs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_cidrs.html.markdown) |
| data source | `alicloud_cen_transit_router_multicast_domain_associations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_multicast_domain_associations.html.markdown) |
| data source | `alicloud_cen_transit_router_multicast_domain_members` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_multicast_domain_members.html.markdown) |
| data source | `alicloud_cen_transit_router_multicast_domain_peer_members` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_multicast_domain_peer_members.html.markdown) |
| data source | `alicloud_cen_transit_router_multicast_domain_sources` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_multicast_domain_sources.html.markdown) |
| data source | `alicloud_cen_transit_router_multicast_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_multicast_domains.html.markdown) |
| data source | `alicloud_cen_transit_router_peer_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_peer_attachments.html.markdown) |
| data source | `alicloud_cen_transit_router_prefix_list_associations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_prefix_list_associations.html.markdown) |
| data source | `alicloud_cen_transit_router_route_entries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_route_entries.html.markdown) |
| data source | `alicloud_cen_transit_router_route_table_associations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_route_table_associations.html.markdown) |
| data source | `alicloud_cen_transit_router_route_table_propagations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_route_table_propagations.html.markdown) |
| data source | `alicloud_cen_transit_router_route_tables` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_route_tables.html.markdown) |
| data source | `alicloud_cen_transit_router_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_service.html.markdown) |
| data source | `alicloud_cen_transit_router_vbr_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_vbr_attachments.html.markdown) |
| data source | `alicloud_cen_transit_router_vpc_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_vpc_attachments.html.markdown) |
| data source | `alicloud_cen_transit_router_vpn_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_router_vpn_attachments.html.markdown) |
| data source | `alicloud_cen_transit_routers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_transit_routers.html.markdown) |
| data source | `alicloud_cen_vbr_health_checks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cen_vbr_health_checks.html.markdown) |
| resource | `alicloud_cen_bandwidth_limit` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_bandwidth_limit.html.markdown) |
| resource | `alicloud_cen_bandwidth_package` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_bandwidth_package.html.markdown) |
| resource | `alicloud_cen_bandwidth_package_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_bandwidth_package_attachment.html.markdown) |
| resource | `alicloud_cen_child_instance_route_entry_to_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_child_instance_route_entry_to_attachment.html.markdown) |
| resource | `alicloud_cen_flowlog` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_flowlog.html.markdown) |
| resource | `alicloud_cen_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_instance.html.markdown) |
| resource | `alicloud_cen_instance_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_instance_attachment.html.markdown) |
| resource | `alicloud_cen_inter_region_traffic_qos_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_inter_region_traffic_qos_policy.html.markdown) |
| resource | `alicloud_cen_inter_region_traffic_qos_queue` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_inter_region_traffic_qos_queue.html.markdown) |
| resource | `alicloud_cen_private_zone` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_private_zone.html.markdown) |
| resource | `alicloud_cen_route_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_route_entry.html.markdown) |
| resource | `alicloud_cen_route_map` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_route_map.html.markdown) |
| resource | `alicloud_cen_route_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_route_service.html.markdown) |
| resource | `alicloud_cen_traffic_marking_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_traffic_marking_policy.html.markdown) |
| resource | `alicloud_cen_transit_route_table_aggregation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_route_table_aggregation.html.markdown) |
| resource | `alicloud_cen_transit_router` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router.html.markdown) |
| resource | `alicloud_cen_transit_router_cidr` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_cidr.html.markdown) |
| resource | `alicloud_cen_transit_router_ecr_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_ecr_attachment.html.markdown) |
| resource | `alicloud_cen_transit_router_grant_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_grant_attachment.html.markdown) |
| resource | `alicloud_cen_transit_router_multicast_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain.html.markdown) |
| resource | `alicloud_cen_transit_router_multicast_domain_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_association.html.markdown) |
| resource | `alicloud_cen_transit_router_multicast_domain_member` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_member.html.markdown) |
| resource | `alicloud_cen_transit_router_multicast_domain_peer_member` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_peer_member.html.markdown) |
| resource | `alicloud_cen_transit_router_multicast_domain_source` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_source.html.markdown) |
| resource | `alicloud_cen_transit_router_peer_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_peer_attachment.html.markdown) |
| resource | `alicloud_cen_transit_router_prefix_list_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_prefix_list_association.html.markdown) |
| resource | `alicloud_cen_transit_router_route_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_entry.html.markdown) |
| resource | `alicloud_cen_transit_router_route_table` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_table.html.markdown) |
| resource | `alicloud_cen_transit_router_route_table_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_table_association.html.markdown) |
| resource | `alicloud_cen_transit_router_route_table_propagation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_table_propagation.html.markdown) |
| resource | `alicloud_cen_transit_router_vbr_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_vbr_attachment.html.markdown) |
| resource | `alicloud_cen_transit_router_vpc_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_vpc_attachment.html.markdown) |
| resource | `alicloud_cen_transit_router_vpn_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_vpn_attachment.html.markdown) |
| resource | `alicloud_cen_vbr_health_check` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_vbr_health_check.html.markdown) |

## Cloud Firewall

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cloud_firewall_address_books` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_address_books.html.markdown) |
| data source | `alicloud_cloud_firewall_control_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_control_policies.html.markdown) |
| data source | `alicloud_cloud_firewall_instance_members` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_instance_members.html.markdown) |
| data source | `alicloud_cloud_firewall_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_instances.html.markdown) |
| data source | `alicloud_cloud_firewall_nat_firewalls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_nat_firewalls.html.markdown) |
| data source | `alicloud_cloud_firewall_tls_inspect_ca_certificates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_tls_inspect_ca_certificates.html.markdown) |
| data source | `alicloud_cloud_firewall_vpc_cen_tr_firewalls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_vpc_cen_tr_firewalls.html.markdown) |
| data source | `alicloud_cloud_firewall_vpc_firewall_cens` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_vpc_firewall_cens.html.markdown) |
| data source | `alicloud_cloud_firewall_vpc_firewall_control_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_vpc_firewall_control_policies.html.markdown) |
| data source | `alicloud_cloud_firewall_vpc_firewalls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_firewall_vpc_firewalls.html.markdown) |
| resource | `alicloud_cloud_firewall_address_book` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_address_book.html.markdown) |
| resource | `alicloud_cloud_firewall_ai_traffic_analysis_status` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_ai_traffic_analysis_status.html.markdown) |
| resource | `alicloud_cloud_firewall_control_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_control_policy.html.markdown) |
| resource | `alicloud_cloud_firewall_control_policy_order` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_control_policy_order.html.markdown) |
| resource | `alicloud_cloud_firewall_instance` | ⚠️ 弃用 → `alicloud_cloud_firewall_instance_v2` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_instance.html.markdown) |
| resource | `alicloud_cloud_firewall_instance_member` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_instance_member.html.markdown) |
| resource | `alicloud_cloud_firewall_instance_v2` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_instance_v2.html.markdown) |
| resource | `alicloud_cloud_firewall_ips_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_ips_config.html.markdown) |
| resource | `alicloud_cloud_firewall_nat_firewall` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_nat_firewall.html.markdown) |
| resource | `alicloud_cloud_firewall_nat_firewall_control_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_nat_firewall_control_policy.html.markdown) |
| resource | `alicloud_cloud_firewall_nat_firewall_control_policy_order` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_nat_firewall_control_policy_order.html.markdown) |
| resource | `alicloud_cloud_firewall_policy_advanced_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_policy_advanced_config.html.markdown) |
| resource | `alicloud_cloud_firewall_private_dns` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_private_dns.html.markdown) |
| resource | `alicloud_cloud_firewall_threat_intelligence_switch` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_threat_intelligence_switch.html.markdown) |
| resource | `alicloud_cloud_firewall_user_alarm_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_user_alarm_config.html.markdown) |
| resource | `alicloud_cloud_firewall_vpc_cen_tr_firewall` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_cen_tr_firewall.html.markdown) |
| resource | `alicloud_cloud_firewall_vpc_firewall` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall.html.markdown) |
| resource | `alicloud_cloud_firewall_vpc_firewall_acl_engine_mode` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_acl_engine_mode.html.markdown) |
| resource | `alicloud_cloud_firewall_vpc_firewall_cen` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_cen.html.markdown) |
| resource | `alicloud_cloud_firewall_vpc_firewall_control_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_control_policy.html.markdown) |
| resource | `alicloud_cloud_firewall_vpc_firewall_control_policy_order` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_control_policy_order.html.markdown) |
| resource | `alicloud_cloud_firewall_vpc_firewall_ips_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_ips_config.html.markdown) |

## Cloud Monitor Service

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cloud_monitor_service_hybrid_double_writes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_monitor_service_hybrid_double_writes.html.markdown) |
| data source | `alicloud_cloud_monitor_service_metric_alarm_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_monitor_service_metric_alarm_rules.html.markdown) |
| data source | `alicloud_cms_alarm_contact_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_alarm_contact_groups.html.markdown) |
| data source | `alicloud_cms_alarm_contacts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_alarm_contacts.html.markdown) |
| data source | `alicloud_cms_dynamic_tag_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_dynamic_tag_groups.html.markdown) |
| data source | `alicloud_cms_event_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_event_rules.html.markdown) |
| data source | `alicloud_cms_group_metric_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_group_metric_rules.html.markdown) |
| data source | `alicloud_cms_hybrid_monitor_datas` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_hybrid_monitor_datas.html.markdown) |
| data source | `alicloud_cms_hybrid_monitor_fc_tasks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_hybrid_monitor_fc_tasks.html.markdown) |
| data source | `alicloud_cms_hybrid_monitor_sls_tasks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_hybrid_monitor_sls_tasks.html.markdown) |
| data source | `alicloud_cms_metric_rule_black_lists` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_metric_rule_black_lists.html.markdown) |
| data source | `alicloud_cms_metric_rule_templates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_metric_rule_templates.html.markdown) |
| data source | `alicloud_cms_monitor_group_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_monitor_group_instances.html.markdown) |
| data source | `alicloud_cms_monitor_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_monitor_groups.html.markdown) |
| data source | `alicloud_cms_namespaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_namespaces.html.markdown) |
| data source | `alicloud_cms_service` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_service.html.markdown) |
| data source | `alicloud_cms_site_monitors` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_site_monitors.html.markdown) |
| data source | `alicloud_cms_sls_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cms_sls_groups.html.markdown) |
| resource | `alicloud_cloud_monitor_service_agent_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_agent_config.html.markdown) |
| resource | `alicloud_cloud_monitor_service_basic_public` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_basic_public.html.markdown) |
| resource | `alicloud_cloud_monitor_service_enterprise_public` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_enterprise_public.html.markdown) |
| resource | `alicloud_cloud_monitor_service_group_monitoring_agent_process` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_group_monitoring_agent_process.html.markdown) |
| resource | `alicloud_cloud_monitor_service_hybrid_double_write` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_hybrid_double_write.html.markdown) |
| resource | `alicloud_cloud_monitor_service_monitoring_agent_process` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_monitoring_agent_process.html.markdown) |
| resource | `alicloud_cms_alarm` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_alarm.html.markdown) |
| resource | `alicloud_cms_alarm_contact` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_alarm_contact.html.markdown) |
| resource | `alicloud_cms_alarm_contact_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_alarm_contact_group.html.markdown) |
| resource | `alicloud_cms_dynamic_tag_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_dynamic_tag_group.html.markdown) |
| resource | `alicloud_cms_event_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_event_rule.html.markdown) |
| resource | `alicloud_cms_group_metric_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_group_metric_rule.html.markdown) |
| resource | `alicloud_cms_hybrid_monitor_fc_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_hybrid_monitor_fc_task.html.markdown) |
| resource | `alicloud_cms_hybrid_monitor_sls_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_hybrid_monitor_sls_task.html.markdown) |
| resource | `alicloud_cms_metric_rule_black_list` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_metric_rule_black_list.html.markdown) |
| resource | `alicloud_cms_metric_rule_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_metric_rule_template.html.markdown) |
| resource | `alicloud_cms_monitor_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_monitor_group.html.markdown) |
| resource | `alicloud_cms_monitor_group_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_monitor_group_instances.html.markdown) |
| resource | `alicloud_cms_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_namespace.html.markdown) |
| resource | `alicloud_cms_site_monitor` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_site_monitor.html.markdown) |
| resource | `alicloud_cms_sls_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_sls_group.html.markdown) |

## Cloud Phone

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_cloud_phone_image` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_image.html.markdown) |
| resource | `alicloud_cloud_phone_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_instance.html.markdown) |
| resource | `alicloud_cloud_phone_instance_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_instance_group.html.markdown) |
| resource | `alicloud_cloud_phone_key_pair` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_key_pair.html.markdown) |
| resource | `alicloud_cloud_phone_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_policy.html.markdown) |

## Cloud SSO

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cloud_sso_access_assignments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_access_assignments.html.markdown) |
| data source | `alicloud_cloud_sso_access_configurations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_access_configurations.html.markdown) |
| data source | `alicloud_cloud_sso_directories` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_directories.html.markdown) |
| data source | `alicloud_cloud_sso_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_groups.html.markdown) |
| data source | `alicloud_cloud_sso_scim_server_credentials` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_scim_server_credentials.html.markdown) |
| data source | `alicloud_cloud_sso_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_service.html.markdown) |
| data source | `alicloud_cloud_sso_user_provisioning_events` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_user_provisioning_events.html.markdown) |
| data source | `alicloud_cloud_sso_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_sso_users.html.markdown) |
| resource | `alicloud_cloud_sso_access_assignment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_access_assignment.html.markdown) |
| resource | `alicloud_cloud_sso_access_configuration` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_access_configuration.html.markdown) |
| resource | `alicloud_cloud_sso_access_configuration_provisioning` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_access_configuration_provisioning.html.markdown) |
| resource | `alicloud_cloud_sso_delegate_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_delegate_account.html.markdown) |
| resource | `alicloud_cloud_sso_directory` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_directory.html.markdown) |
| resource | `alicloud_cloud_sso_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_group.html.markdown) |
| resource | `alicloud_cloud_sso_scim_server_credential` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_scim_server_credential.html.markdown) |
| resource | `alicloud_cloud_sso_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_user.html.markdown) |
| resource | `alicloud_cloud_sso_user_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_user_attachment.html.markdown) |
| resource | `alicloud_cloud_sso_user_provisioning` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_user_provisioning.html.markdown) |

## Cloud Storage Gateway

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cloud_storage_gateway_express_syncs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_express_syncs.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_gateway_block_volumes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_gateway_block_volumes.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_gateway_cache_disks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_gateway_cache_disks.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_gateway_file_shares` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_gateway_file_shares.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_gateway_smb_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_gateway_smb_users.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_gateways.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_service.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_stocks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_stocks.html.markdown) |
| data source | `alicloud_cloud_storage_gateway_storage_bundle` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_storage_gateway_storage_bundle.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_express_sync` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_express_sync.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_express_sync_share_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_express_sync_share_attachment.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_gateway_block_volume` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_block_volume.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_gateway_cache_disk` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_cache_disk.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_gateway_file_share` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_file_share.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_gateway_logging` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_logging.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_gateway_smb_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_smb_user.html.markdown) |
| resource | `alicloud_cloud_storage_gateway_storage_bundle` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_storage_bundle.html.markdown) |

## Cloudauth

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cloudauth_face_configs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloudauth_face_configs.html.markdown) |
| resource | `alicloud_cloudauth_face_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloudauth_face_config.html.markdown) |

## Cms

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_cms_workspace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_workspace.html.markdown) |

## Compute Nest

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_compute_nest_service_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/compute_nest_service_instances.html.markdown) |
| resource | `alicloud_compute_nest_service_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/compute_nest_service_instance.html.markdown) |

## Container Registry (CR)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cr_chains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_chains.html.markdown) |
| data source | `alicloud_cr_chart_namespaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_chart_namespaces.html.markdown) |
| data source | `alicloud_cr_chart_repositories` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_chart_repositories.html.markdown) |
| data source | `alicloud_cr_ee_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_ee_instances.html.markdown) |
| data source | `alicloud_cr_ee_namespaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_ee_namespaces.html.markdown) |
| data source | `alicloud_cr_ee_repos` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_ee_repos.html.markdown) |
| data source | `alicloud_cr_ee_sync_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_ee_sync_rules.html.markdown) |
| data source | `alicloud_cr_endpoint_acl_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_endpoint_acl_policies.html.markdown) |
| data source | `alicloud_cr_endpoint_acl_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_endpoint_acl_service.html.markdown) |
| data source | `alicloud_cr_namespaces` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_namespaces.html.markdown) |
| data source | `alicloud_cr_repos` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_repos.html.markdown) |
| data source | `alicloud_cr_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_service.html.markdown) |
| data source | `alicloud_cr_vpc_endpoint_linked_vpcs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cr_vpc_endpoint_linked_vpcs.html.markdown) |
| resource | `alicloud_cr_chain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_chain.html.markdown) |
| resource | `alicloud_cr_chart_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_chart_namespace.html.markdown) |
| resource | `alicloud_cr_chart_repository` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_chart_repository.html.markdown) |
| resource | `alicloud_cr_ee_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_instance.html.markdown) |
| resource | `alicloud_cr_ee_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_namespace.html.markdown) |
| resource | `alicloud_cr_ee_repo` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_repo.html.markdown) |
| resource | `alicloud_cr_ee_sync_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_sync_rule.html.markdown) |
| resource | `alicloud_cr_endpoint_acl_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_endpoint_acl_policy.html.markdown) |
| resource | `alicloud_cr_namespace` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_namespace.html.markdown) |
| resource | `alicloud_cr_repo` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_repo.html.markdown) |
| resource | `alicloud_cr_scan_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_scan_rule.html.markdown) |
| resource | `alicloud_cr_storage_domain_routing_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_storage_domain_routing_rule.html.markdown) |
| resource | `alicloud_cr_vpc_endpoint_linked_vpc` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_vpc_endpoint_linked_vpc.html.markdown) |

## Container Service for Kubernetes (ACK)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ack_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ack_service.html.markdown) |
| data source | `alicloud_cs_cluster_credential` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_cluster_credential.html.markdown) |
| data source | `alicloud_cs_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_clusters.html.markdown) |
| data source | `alicloud_cs_edge_kubernetes_clusters` | ⚠️ 弃用 → `alicloud_cs_clusters` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_edge_kubernetes_clusters.html.markdown) |
| data source | `alicloud_cs_kubernetes_addon_metadata` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_kubernetes_addon_metadata.html.markdown) |
| data source | `alicloud_cs_kubernetes_addons` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_kubernetes_addons.html.markdown) |
| data source | `alicloud_cs_kubernetes_clusters` | ⚠️ 弃用 → `alicloud_cs_clusters` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_kubernetes_clusters.html.markdown) |
| data source | `alicloud_cs_kubernetes_node_pools` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_kubernetes_node_pools.html.markdown) |
| data source | `alicloud_cs_kubernetes_permissions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_kubernetes_permissions.html.markdown) |
| data source | `alicloud_cs_kubernetes_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_kubernetes_version.html.markdown) |
| data source | `alicloud_cs_managed_kubernetes_clusters` | ⚠️ 弃用 → `alicloud_cs_clusters` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_managed_kubernetes_clusters.html.markdown) |
| data source | `alicloud_cs_serverless_kubernetes_clusters` | ⚠️ 弃用 → `alicloud_cs_clusters` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cs_serverless_kubernetes_clusters.html.markdown) |
| resource | `alicloud_cs_autoscaling_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_autoscaling_config.html.markdown) |
| resource | `alicloud_cs_edge_kubernetes` | ⚠️ 弃用 → `alicloud_cs_managed_kubernetes` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_edge_kubernetes.html.markdown) |
| resource | `alicloud_cs_kubernetes` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes.html.markdown) |
| resource | `alicloud_cs_kubernetes_addon` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_addon.html.markdown) |
| resource | `alicloud_cs_kubernetes_autoscaler` | ⚠️ 弃用 → `alicloud_cs_autoscaling_config` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_autoscaler.html.markdown) |
| resource | `alicloud_cs_kubernetes_node_pool` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_node_pool.html.markdown) |
| resource | `alicloud_cs_kubernetes_permissions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_permissions.html.markdown) |
| resource | `alicloud_cs_kubernetes_policy_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_policy_instance.html.markdown) |
| resource | `alicloud_cs_managed_kubernetes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_managed_kubernetes.html.markdown) |
| resource | `alicloud_cs_serverless_kubernetes` | ⚠️ 弃用 → `alicloud_cs_managed_kubernetes` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_serverless_kubernetes.html.markdown) |

## DAS

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_das_switch_das_pro` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/das_switch_das_pro.html.markdown) |

## DCDN

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_dcdn_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dcdn_domains.html.markdown) |
| data source | `alicloud_dcdn_ipa_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dcdn_ipa_domains.html.markdown) |
| data source | `alicloud_dcdn_kv_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dcdn_kv_account.html.markdown) |
| data source | `alicloud_dcdn_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dcdn_service.html.markdown) |
| data source | `alicloud_dcdn_waf_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dcdn_waf_domains.html.markdown) |
| data source | `alicloud_dcdn_waf_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dcdn_waf_policies.html.markdown) |
| data source | `alicloud_dcdn_waf_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dcdn_waf_rules.html.markdown) |
| resource | `alicloud_dcdn_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_domain.html.markdown) |
| resource | `alicloud_dcdn_domain_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_domain_config.html.markdown) |
| resource | `alicloud_dcdn_er` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_er.html.markdown) |
| resource | `alicloud_dcdn_ipa_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_ipa_domain.html.markdown) |
| resource | `alicloud_dcdn_kv` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_kv.html.markdown) |
| resource | `alicloud_dcdn_kv_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_kv_namespace.html.markdown) |
| resource | `alicloud_dcdn_waf_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_domain.html.markdown) |
| resource | `alicloud_dcdn_waf_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_policy.html.markdown) |
| resource | `alicloud_dcdn_waf_policy_domain_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_policy_domain_attachment.html.markdown) |
| resource | `alicloud_dcdn_waf_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_rule.html.markdown) |

## DMS Enterprise

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_dms_enterprise_databases` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dms_enterprise_databases.html.markdown) |
| data source | `alicloud_dms_enterprise_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dms_enterprise_instances.html.markdown) |
| data source | `alicloud_dms_enterprise_logic_databases` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dms_enterprise_logic_databases.html.markdown) |
| data source | `alicloud_dms_enterprise_proxies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dms_enterprise_proxies.html.markdown) |
| data source | `alicloud_dms_enterprise_proxy_accesses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dms_enterprise_proxy_accesses.html.markdown) |
| data source | `alicloud_dms_enterprise_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dms_enterprise_users.html.markdown) |
| data source | `alicloud_dms_user_tenants` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dms_user_tenants.html.markdown) |
| resource | `alicloud_dms_enterprise_authority_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_authority_template.html.markdown) |
| resource | `alicloud_dms_enterprise_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_instance.html.markdown) |
| resource | `alicloud_dms_enterprise_logic_database` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_logic_database.html.markdown) |
| resource | `alicloud_dms_enterprise_proxy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_proxy.html.markdown) |
| resource | `alicloud_dms_enterprise_proxy_access` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_proxy_access.html.markdown) |
| resource | `alicloud_dms_enterprise_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_user.html.markdown) |
| resource | `alicloud_dms_enterprise_workspace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_workspace.html.markdown) |

## Data Security Center (SDDP)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_sddp_configs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sddp_configs.html.markdown) |
| data source | `alicloud_sddp_data_limits` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sddp_data_limits.html.markdown) |
| data source | `alicloud_sddp_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sddp_instances.html.markdown) |
| data source | `alicloud_sddp_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sddp_rules.html.markdown) |
| resource | `alicloud_sddp_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_config.html.markdown) |
| resource | `alicloud_sddp_data_limit` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_data_limit.html.markdown) |
| resource | `alicloud_sddp_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_instance.html.markdown) |
| resource | `alicloud_sddp_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_rule.html.markdown) |

## Data Transmission Service (DTS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_dts_consumer_channels` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dts_consumer_channels.html.markdown) |
| data source | `alicloud_dts_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dts_instances.html.markdown) |
| data source | `alicloud_dts_migration_jobs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dts_migration_jobs.html.markdown) |
| data source | `alicloud_dts_subscription_jobs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dts_subscription_jobs.html.markdown) |
| data source | `alicloud_dts_synchronization_jobs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dts_synchronization_jobs.html.markdown) |
| resource | `alicloud_dts_consumer_channel` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_consumer_channel.html.markdown) |
| resource | `alicloud_dts_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_instance.html.markdown) |
| resource | `alicloud_dts_job_monitor_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_job_monitor_rule.html.markdown) |
| resource | `alicloud_dts_migration_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_migration_instance.html.markdown) |
| resource | `alicloud_dts_migration_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_migration_job.html.markdown) |
| resource | `alicloud_dts_subscription_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_subscription_job.html.markdown) |
| resource | `alicloud_dts_synchronization_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_synchronization_instance.html.markdown) |
| resource | `alicloud_dts_synchronization_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_synchronization_job.html.markdown) |

## Data Works

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_data_works_folders` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/data_works_folders.html.markdown) |
| data source | `alicloud_data_works_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/data_works_service.html.markdown) |
| resource | `alicloud_data_works_data_source` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_data_source.html.markdown) |
| resource | `alicloud_data_works_data_source_shared_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_data_source_shared_rule.html.markdown) |
| resource | `alicloud_data_works_di_alarm_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_di_alarm_rule.html.markdown) |
| resource | `alicloud_data_works_di_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_di_job.html.markdown) |
| resource | `alicloud_data_works_dw_resource_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_dw_resource_group.html.markdown) |
| resource | `alicloud_data_works_folder` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_folder.html.markdown) |
| resource | `alicloud_data_works_network` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_network.html.markdown) |
| resource | `alicloud_data_works_project` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_project.html.markdown) |
| resource | `alicloud_data_works_project_member` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_project_member.html.markdown) |

## Database Backup(DBS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_dbs_backup_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dbs_backup_plans.html.markdown) |
| resource | `alicloud_dbs_backup_plan` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbs_backup_plan.html.markdown) |

## Database File System (DBFS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_dbfs_auto_snap_shot_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dbfs_auto_snap_shot_policies.html.markdown) |
| data source | `alicloud_dbfs_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dbfs_instances.html.markdown) |
| data source | `alicloud_dbfs_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/dbfs_snapshots.html.markdown) |
| resource | `alicloud_dbfs_auto_snap_shot_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_auto_snap_shot_policy.html.markdown) |
| resource | `alicloud_dbfs_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_instance.html.markdown) |
| resource | `alicloud_dbfs_instance_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_instance_attachment.html.markdown) |
| resource | `alicloud_dbfs_service_linked_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_service_linked_role.html.markdown) |
| resource | `alicloud_dbfs_snapshot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_snapshot.html.markdown) |

## Database Gateway

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_database_gateway_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/database_gateway_gateways.html.markdown) |
| resource | `alicloud_database_gateway_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/database_gateway_gateway.html.markdown) |

## Datahub Service (DataHub)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_datahub_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/datahub_service.html.markdown) |
| resource | `alicloud_datahub_project` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/datahub_project.html.markdown) |
| resource | `alicloud_datahub_subscription` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/datahub_subscription.html.markdown) |
| resource | `alicloud_datahub_topic` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/datahub_topic.html.markdown) |

## Ddos Basic

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_ddos_basic_defense_threshold` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddos_basic_defense_threshold.html.markdown) |
| resource | `alicloud_ddos_basic_threshold` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddos_basic_threshold.html.markdown) |

## Direct Mail

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_direct_mail_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/direct_mail_domains.html.markdown) |
| data source | `alicloud_direct_mail_mail_addresses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/direct_mail_mail_addresses.html.markdown) |
| data source | `alicloud_direct_mail_receiverses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/direct_mail_receiverses.html.markdown) |
| data source | `alicloud_direct_mail_tags` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/direct_mail_tags.html.markdown) |
| resource | `alicloud_direct_mail_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_domain.html.markdown) |
| resource | `alicloud_direct_mail_mail_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_mail_address.html.markdown) |
| resource | `alicloud_direct_mail_receivers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_receivers.html.markdown) |
| resource | `alicloud_direct_mail_tag` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_tag.html.markdown) |

## Distributed Relational Database Service (DRDS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_drds_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/drds_instances.html.markdown) |
| resource | `alicloud_drds_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/drds_instance.html.markdown) |
| resource | `alicloud_drds_polardbx_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/drds_polardbx_instance.html.markdown) |

## Dms

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_dms_airflow` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_airflow.html.markdown) |

## E-MapReduce (EMR)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_emr_clusters` | ⚠️ 弃用 → `alicloud_emrv2_clusters` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/emr_clusters.html.markdown) |
| data source | `alicloud_emr_disk_types` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/emr_disk_types.html.markdown) |
| data source | `alicloud_emr_instance_types` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/emr_instance_types.html.markdown) |
| data source | `alicloud_emr_main_versions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/emr_main_versions.html.markdown) |
| data source | `alicloud_emrv2_cluster_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/emrv2_cluster_instances.html.markdown) |
| data source | `alicloud_emrv2_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/emrv2_clusters.html.markdown) |
| resource | `alicloud_emr_cluster` | ⚠️ 弃用 → `alicloud_emrv2_cluster` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/emr_cluster.html.markdown) |
| resource | `alicloud_emrv2_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/emrv2_cluster.html.markdown) |

## ECS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_disks` | ⚠️ 弃用 → `alicloud_ecs_disks` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/disks.html.markdown) |
| data source | `alicloud_ecs_activations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_activations.html.markdown) |
| data source | `alicloud_ecs_auto_snapshot_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_auto_snapshot_policies.html.markdown) |
| data source | `alicloud_ecs_capacity_reservations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_capacity_reservations.html.markdown) |
| data source | `alicloud_ecs_commands` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_commands.html.markdown) |
| data source | `alicloud_ecs_dedicated_host_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_dedicated_host_clusters.html.markdown) |
| data source | `alicloud_ecs_dedicated_hosts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_dedicated_hosts.html.markdown) |
| data source | `alicloud_ecs_deployment_sets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_deployment_sets.html.markdown) |
| data source | `alicloud_ecs_disks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_disks.html.markdown) |
| data source | `alicloud_ecs_elasticity_assurances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_elasticity_assurances.html.markdown) |
| data source | `alicloud_ecs_hpc_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_hpc_clusters.html.markdown) |
| data source | `alicloud_ecs_image_components` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_image_components.html.markdown) |
| data source | `alicloud_ecs_image_pipelines` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_image_pipelines.html.markdown) |
| data source | `alicloud_ecs_invocations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_invocations.html.markdown) |
| data source | `alicloud_ecs_key_pairs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_key_pairs.html.markdown) |
| data source | `alicloud_ecs_launch_templates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_launch_templates.html.markdown) |
| data source | `alicloud_ecs_network_interface_permissions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_network_interface_permissions.html.markdown) |
| data source | `alicloud_ecs_network_interfaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_network_interfaces.html.markdown) |
| data source | `alicloud_ecs_prefix_lists` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_prefix_lists.html.markdown) |
| data source | `alicloud_ecs_snapshot_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_snapshot_groups.html.markdown) |
| data source | `alicloud_ecs_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_snapshots.html.markdown) |
| data source | `alicloud_ecs_storage_capacity_units` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecs_storage_capacity_units.html.markdown) |
| data source | `alicloud_images` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/images.html.markdown) |
| data source | `alicloud_instance_type_families` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/instance_type_families.html.markdown) |
| data source | `alicloud_instance_types` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/instance_types.html.markdown) |
| data source | `alicloud_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/instances.html.markdown) |
| data source | `alicloud_key_pairs` | ⚠️ 弃用 → `alicloud_ecs_key_pairs` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/key_pairs.html.markdown) |
| data source | `alicloud_network_interfaces` | ⚠️ 弃用 → `alicloud_ecs_network_interfaces` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/network_interfaces.html.markdown) |
| data source | `alicloud_regions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/regions.html.markdown) |
| data source | `alicloud_security_group_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/security_group_rules.html.markdown) |
| data source | `alicloud_security_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/security_groups.html.markdown) |
| data source | `alicloud_snapshots` | ⚠️ 弃用 → `alicloud_ecs_snapshots` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/snapshots.html.markdown) |
| data source | `alicloud_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/zones.html.markdown) |
| resource | `alicloud_auto_provisioning_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/auto_provisioning_group.html.markdown) |
| resource | `alicloud_disk` | ⚠️ 弃用 → `alicloud_ecs_disk` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/disk.html.markdown) |
| resource | `alicloud_disk_attachment` | ⚠️ 弃用 → `alicloud_ecs_disk_attachment` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/disk_attachment.html.markdown) |
| resource | `alicloud_ecs_activation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_activation.html.markdown) |
| resource | `alicloud_ecs_auto_snapshot_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_auto_snapshot_policy.html.markdown) |
| resource | `alicloud_ecs_auto_snapshot_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_auto_snapshot_policy_attachment.html.markdown) |
| resource | `alicloud_ecs_capacity_reservation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_capacity_reservation.html.markdown) |
| resource | `alicloud_ecs_command` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_command.html.markdown) |
| resource | `alicloud_ecs_dedicated_host` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_dedicated_host.html.markdown) |
| resource | `alicloud_ecs_dedicated_host_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_dedicated_host_cluster.html.markdown) |
| resource | `alicloud_ecs_deployment_set` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_deployment_set.html.markdown) |
| resource | `alicloud_ecs_disk` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_disk.html.markdown) |
| resource | `alicloud_ecs_disk_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_disk_attachment.html.markdown) |
| resource | `alicloud_ecs_disk_encryption_by_default` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_disk_encryption_by_default.html.markdown) |
| resource | `alicloud_ecs_elasticity_assurance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_elasticity_assurance.html.markdown) |
| resource | `alicloud_ecs_hpc_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_hpc_cluster.html.markdown) |
| resource | `alicloud_ecs_image_component` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_image_component.html.markdown) |
| resource | `alicloud_ecs_image_pipeline` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_image_pipeline.html.markdown) |
| resource | `alicloud_ecs_image_pipeline_execution` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_image_pipeline_execution.html.markdown) |
| resource | `alicloud_ecs_instance_set` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_instance_set.html.markdown) |
| resource | `alicloud_ecs_invocation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_invocation.html.markdown) |
| resource | `alicloud_ecs_key_pair` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_key_pair.html.markdown) |
| resource | `alicloud_ecs_key_pair_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_key_pair_attachment.html.markdown) |
| resource | `alicloud_ecs_launch_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_launch_template.html.markdown) |
| resource | `alicloud_ecs_network_interface` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_network_interface.html.markdown) |
| resource | `alicloud_ecs_network_interface_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_network_interface_attachment.html.markdown) |
| resource | `alicloud_ecs_network_interface_permission` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_network_interface_permission.html.markdown) |
| resource | `alicloud_ecs_prefix_list` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_prefix_list.html.markdown) |
| resource | `alicloud_ecs_ram_role_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_ram_role_attachment.html.markdown) |
| resource | `alicloud_ecs_session_manager_status` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_session_manager_status.html.markdown) |
| resource | `alicloud_ecs_snapshot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_snapshot.html.markdown) |
| resource | `alicloud_ecs_snapshot_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_snapshot_group.html.markdown) |
| resource | `alicloud_ecs_storage_capacity_unit` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_storage_capacity_unit.html.markdown) |
| resource | `alicloud_image` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image.html.markdown) |
| resource | `alicloud_image_copy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_copy.html.markdown) |
| resource | `alicloud_image_export` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_export.html.markdown) |
| resource | `alicloud_image_import` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_import.html.markdown) |
| resource | `alicloud_image_share_permission` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_share_permission.html.markdown) |
| resource | `alicloud_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/instance.html.markdown) |
| resource | `alicloud_key_pair` | ⚠️ 弃用 → `alicloud_ecs_key_pair` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/key_pair.html.markdown) |
| resource | `alicloud_key_pair_attachment` | ⚠️ 弃用 → `alicloud_ecs_key_pair_attachment` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/key_pair_attachment.html.markdown) |
| resource | `alicloud_launch_template` | ⚠️ 弃用 → `alicloud_ecs_launch_template` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/launch_template.html.markdown) |
| resource | `alicloud_network_interface` | ⚠️ 弃用 → `alicloud_ecs_network_interface` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_interface.html.markdown) |
| resource | `alicloud_network_interface_attachment` | ⚠️ 弃用 → `alicloud_ecs_network_interface_attachment` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_interface_attachment.html.markdown) |
| resource | `alicloud_ram_role_attachment` | ⚠️ 弃用 → `alicloud_ecs_ram_role_attachment` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_role_attachment.html.markdown) |
| resource | `alicloud_reserved_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/reserved_instance.html.markdown) |
| resource | `alicloud_security_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_group.html.markdown) |
| resource | `alicloud_security_group_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_group_rule.html.markdown) |
| resource | `alicloud_snapshot` | ⚠️ 弃用 → `alicloud_ecs_snapshot` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/snapshot.html.markdown) |
| resource | `alicloud_snapshot_policy` | ⚠️ 弃用 → `alicloud_ecs_auto_snapshot_policy` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/snapshot_policy.html.markdown) |

## EDAS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_edas_applications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/edas_applications.html.markdown) |
| data source | `alicloud_edas_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/edas_clusters.html.markdown) |
| data source | `alicloud_edas_deploy_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/edas_deploy_groups.html.markdown) |
| data source | `alicloud_edas_namespaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/edas_namespaces.html.markdown) |
| data source | `alicloud_edas_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/edas_service.html.markdown) |
| resource | `alicloud_edas_application` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_application.html.markdown) |
| resource | `alicloud_edas_application_deployment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_application_deployment.html.markdown) |
| resource | `alicloud_edas_application_scale` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_application_scale.html.markdown) |
| resource | `alicloud_edas_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_cluster.html.markdown) |
| resource | `alicloud_edas_deploy_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_deploy_group.html.markdown) |
| resource | `alicloud_edas_instance_cluster_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_instance_cluster_attachment.html.markdown) |
| resource | `alicloud_edas_k8s_application` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_k8s_application.html.markdown) |
| resource | `alicloud_edas_k8s_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_k8s_cluster.html.markdown) |
| resource | `alicloud_edas_k8s_slb_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_k8s_slb_attachment.html.markdown) |
| resource | `alicloud_edas_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_namespace.html.markdown) |
| resource | `alicloud_edas_slb_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_slb_attachment.html.markdown) |

## EIP Bandwidth Plan (CBWP)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_common_bandwidth_packages` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/common_bandwidth_packages.html.markdown) |
| resource | `alicloud_common_bandwidth_package` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/common_bandwidth_package.html.markdown) |
| resource | `alicloud_common_bandwidth_package_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/common_bandwidth_package_attachment.html.markdown) |

## ENS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ens_key_pairs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ens_key_pairs.html.markdown) |
| resource | `alicloud_ens_disk` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_disk.html.markdown) |
| resource | `alicloud_ens_disk_instance_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_disk_instance_attachment.html.markdown) |
| resource | `alicloud_ens_eip` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_eip.html.markdown) |
| resource | `alicloud_ens_eip_instance_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_eip_instance_attachment.html.markdown) |
| resource | `alicloud_ens_image` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_image.html.markdown) |
| resource | `alicloud_ens_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_instance.html.markdown) |
| resource | `alicloud_ens_instance_security_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_instance_security_group_attachment.html.markdown) |
| resource | `alicloud_ens_key_pair` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_key_pair.html.markdown) |
| resource | `alicloud_ens_load_balancer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_load_balancer.html.markdown) |
| resource | `alicloud_ens_nat_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_nat_gateway.html.markdown) |
| resource | `alicloud_ens_network` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_network.html.markdown) |
| resource | `alicloud_ens_security_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_security_group.html.markdown) |
| resource | `alicloud_ens_snapshot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_snapshot.html.markdown) |
| resource | `alicloud_ens_vswitch` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_vswitch.html.markdown) |

## ESA

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_esa_sites` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/esa_sites.html.markdown) |
| data source | `alicloud_esa_waf_rulesets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/esa_waf_rulesets.html.markdown) |
| resource | `alicloud_esa_cache_reserve_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_cache_reserve_instance.html.markdown) |
| resource | `alicloud_esa_cache_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_cache_rule.html.markdown) |
| resource | `alicloud_esa_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_certificate.html.markdown) |
| resource | `alicloud_esa_client_ca_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_client_ca_certificate.html.markdown) |
| resource | `alicloud_esa_client_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_client_certificate.html.markdown) |
| resource | `alicloud_esa_compression_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_compression_rule.html.markdown) |
| resource | `alicloud_esa_custom_response_code_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_custom_response_code_rule.html.markdown) |
| resource | `alicloud_esa_custom_scene_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_custom_scene_policy.html.markdown) |
| resource | `alicloud_esa_edge_container_app` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_edge_container_app.html.markdown) |
| resource | `alicloud_esa_edge_container_app_record` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_edge_container_app_record.html.markdown) |
| resource | `alicloud_esa_http_incoming_request_header_modification_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_incoming_request_header_modification_rule.html.markdown) |
| resource | `alicloud_esa_http_incoming_response_header_modification_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_incoming_response_header_modification_rule.html.markdown) |
| resource | `alicloud_esa_http_request_header_modification_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_request_header_modification_rule.html.markdown) |
| resource | `alicloud_esa_http_response_header_modification_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_response_header_modification_rule.html.markdown) |
| resource | `alicloud_esa_https_application_configuration` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_https_application_configuration.html.markdown) |
| resource | `alicloud_esa_https_basic_configuration` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_https_basic_configuration.html.markdown) |
| resource | `alicloud_esa_image_transform` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_image_transform.html.markdown) |
| resource | `alicloud_esa_kv` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_kv.html.markdown) |
| resource | `alicloud_esa_kv_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_kv_account.html.markdown) |
| resource | `alicloud_esa_kv_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_kv_namespace.html.markdown) |
| resource | `alicloud_esa_list` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_list.html.markdown) |
| resource | `alicloud_esa_load_balancer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_load_balancer.html.markdown) |
| resource | `alicloud_esa_network_optimization` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_network_optimization.html.markdown) |
| resource | `alicloud_esa_origin_ca_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_ca_certificate.html.markdown) |
| resource | `alicloud_esa_origin_client_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_client_certificate.html.markdown) |
| resource | `alicloud_esa_origin_pool` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_pool.html.markdown) |
| resource | `alicloud_esa_origin_protection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_protection.html.markdown) |
| resource | `alicloud_esa_origin_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_rule.html.markdown) |
| resource | `alicloud_esa_page` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_page.html.markdown) |
| resource | `alicloud_esa_rate_plan_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_rate_plan_instance.html.markdown) |
| resource | `alicloud_esa_record` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_record.html.markdown) |
| resource | `alicloud_esa_redirect_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_redirect_rule.html.markdown) |
| resource | `alicloud_esa_rewrite_url_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_rewrite_url_rule.html.markdown) |
| resource | `alicloud_esa_routine` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_routine.html.markdown) |
| resource | `alicloud_esa_routine_related_record` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_routine_related_record.html.markdown) |
| resource | `alicloud_esa_routine_route` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_routine_route.html.markdown) |
| resource | `alicloud_esa_scheduled_preload_execution` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_scheduled_preload_execution.html.markdown) |
| resource | `alicloud_esa_scheduled_preload_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_scheduled_preload_job.html.markdown) |
| resource | `alicloud_esa_site` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_site.html.markdown) |
| resource | `alicloud_esa_site_delivery_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_site_delivery_task.html.markdown) |
| resource | `alicloud_esa_site_origin_client_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_site_origin_client_certificate.html.markdown) |
| resource | `alicloud_esa_transport_layer_application` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_transport_layer_application.html.markdown) |
| resource | `alicloud_esa_url_observation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_url_observation.html.markdown) |
| resource | `alicloud_esa_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_version.html.markdown) |
| resource | `alicloud_esa_video_processing` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_video_processing.html.markdown) |
| resource | `alicloud_esa_waf_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waf_rule.html.markdown) |
| resource | `alicloud_esa_waf_ruleset` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waf_ruleset.html.markdown) |
| resource | `alicloud_esa_waiting_room` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waiting_room.html.markdown) |
| resource | `alicloud_esa_waiting_room_event` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waiting_room_event.html.markdown) |
| resource | `alicloud_esa_waiting_room_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waiting_room_rule.html.markdown) |

## Eflo

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_eflo_subnets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eflo_subnets.html.markdown) |
| data source | `alicloud_eflo_vpds` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eflo_vpds.html.markdown) |
| resource | `alicloud_eflo_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_cluster.html.markdown) |
| resource | `alicloud_eflo_er` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_er.html.markdown) |
| resource | `alicloud_eflo_experiment_plan` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_experiment_plan.html.markdown) |
| resource | `alicloud_eflo_experiment_plan_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_experiment_plan_template.html.markdown) |
| resource | `alicloud_eflo_hyper_node` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_hyper_node.html.markdown) |
| resource | `alicloud_eflo_invocation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_invocation.html.markdown) |
| resource | `alicloud_eflo_node` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_node.html.markdown) |
| resource | `alicloud_eflo_node_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_node_group.html.markdown) |
| resource | `alicloud_eflo_node_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_node_group_attachment.html.markdown) |
| resource | `alicloud_eflo_resource` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_resource.html.markdown) |
| resource | `alicloud_eflo_subnet` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_subnet.html.markdown) |
| resource | `alicloud_eflo_vpd` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_vpd.html.markdown) |
| resource | `alicloud_eflo_vpd_grant_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_vpd_grant_rule.html.markdown) |
| resource | `alicloud_eflo_vsc` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_vsc.html.markdown) |

## Elastic Accelerated Computing Instances (EAIS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_eais_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eais_instances.html.markdown) |
| resource | `alicloud_eais_client_instance_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eais_client_instance_attachment.html.markdown) |
| resource | `alicloud_eais_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eais_instance.html.markdown) |

## Elastic Block Storage(EBS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ebs_dedicated_block_storage_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ebs_dedicated_block_storage_clusters.html.markdown) |
| data source | `alicloud_ebs_disk_replica_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ebs_disk_replica_groups.html.markdown) |
| data source | `alicloud_ebs_disk_replica_pairs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ebs_disk_replica_pairs.html.markdown) |
| data source | `alicloud_ebs_regions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ebs_regions.html.markdown) |
| resource | `alicloud_ebs_dedicated_block_storage_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_dedicated_block_storage_cluster.html.markdown) |
| resource | `alicloud_ebs_disk_replica_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_disk_replica_group.html.markdown) |
| resource | `alicloud_ebs_disk_replica_pair` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_disk_replica_pair.html.markdown) |
| resource | `alicloud_ebs_enterprise_snapshot_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_enterprise_snapshot_policy.html.markdown) |
| resource | `alicloud_ebs_enterprise_snapshot_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_enterprise_snapshot_policy_attachment.html.markdown) |
| resource | `alicloud_ebs_replica_group_drill` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_replica_group_drill.html.markdown) |
| resource | `alicloud_ebs_replica_pair_drill` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_replica_pair_drill.html.markdown) |
| resource | `alicloud_ebs_solution_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_solution_instance.html.markdown) |

## Elastic Cloud Phone (ECP)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ecp_instance_types` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecp_instance_types.html.markdown) |
| data source | `alicloud_ecp_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecp_instances.html.markdown) |
| data source | `alicloud_ecp_key_pairs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecp_key_pairs.html.markdown) |
| data source | `alicloud_ecp_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecp_zones.html.markdown) |
| resource | `alicloud_ecp_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecp_instance.html.markdown) |
| resource | `alicloud_ecp_key_pair` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecp_key_pair.html.markdown) |

## Elastic Container Instance (ECI)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_eci_container_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eci_container_groups.html.markdown) |
| data source | `alicloud_eci_image_caches` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eci_image_caches.html.markdown) |
| data source | `alicloud_eci_virtual_nodes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eci_virtual_nodes.html.markdown) |
| data source | `alicloud_eci_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eci_zones.html.markdown) |
| resource | `alicloud_eci_container_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eci_container_group.html.markdown) |
| resource | `alicloud_eci_image_cache` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eci_image_cache.html.markdown) |
| resource | `alicloud_eci_virtual_node` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eci_virtual_node.html.markdown) |

## Elastic Desktop Service (ECD)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ecd_ad_connector_directories` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_ad_connector_directories.html.markdown) |
| data source | `alicloud_ecd_ad_connector_office_sites` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_ad_connector_office_sites.html.markdown) |
| data source | `alicloud_ecd_bundles` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_bundles.html.markdown) |
| data source | `alicloud_ecd_commands` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_commands.html.markdown) |
| data source | `alicloud_ecd_custom_properties` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_custom_properties.html.markdown) |
| data source | `alicloud_ecd_desktop_types` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_desktop_types.html.markdown) |
| data source | `alicloud_ecd_desktops` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_desktops.html.markdown) |
| data source | `alicloud_ecd_images` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_images.html.markdown) |
| data source | `alicloud_ecd_nas_file_systems` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_nas_file_systems.html.markdown) |
| data source | `alicloud_ecd_network_packages` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_network_packages.html.markdown) |
| data source | `alicloud_ecd_policy_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_policy_groups.html.markdown) |
| data source | `alicloud_ecd_ram_directories` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_ram_directories.html.markdown) |
| data source | `alicloud_ecd_simple_office_sites` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_simple_office_sites.html.markdown) |
| data source | `alicloud_ecd_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_snapshots.html.markdown) |
| data source | `alicloud_ecd_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_users.html.markdown) |
| data source | `alicloud_ecd_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ecd_zones.html.markdown) |
| resource | `alicloud_ecd_ad_connector_directory` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_ad_connector_directory.html.markdown) |
| resource | `alicloud_ecd_ad_connector_office_site` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_ad_connector_office_site.html.markdown) |
| resource | `alicloud_ecd_bundle` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_bundle.html.markdown) |
| resource | `alicloud_ecd_command` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_command.html.markdown) |
| resource | `alicloud_ecd_custom_property` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_custom_property.html.markdown) |
| resource | `alicloud_ecd_desktop` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_desktop.html.markdown) |
| resource | `alicloud_ecd_image` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_image.html.markdown) |
| resource | `alicloud_ecd_nas_file_system` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_nas_file_system.html.markdown) |
| resource | `alicloud_ecd_network_package` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_network_package.html.markdown) |
| resource | `alicloud_ecd_policy_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_policy_group.html.markdown) |
| resource | `alicloud_ecd_ram_directory` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_ram_directory.html.markdown) |
| resource | `alicloud_ecd_simple_office_site` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_simple_office_site.html.markdown) |
| resource | `alicloud_ecd_snapshot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_snapshot.html.markdown) |
| resource | `alicloud_ecd_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_user.html.markdown) |

## Elastic High Performance Computing (Ehpc)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ehpc_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ehpc_clusters.html.markdown) |
| data source | `alicloud_ehpc_job_templates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ehpc_job_templates.html.markdown) |
| resource | `alicloud_ehpc_cluster` | ⚠️ 弃用 → `alicloud_ehpc_cluster_v2` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_cluster.html.markdown) |
| resource | `alicloud_ehpc_cluster_v2` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_cluster_v2.html.markdown) |
| resource | `alicloud_ehpc_job_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_job_template.html.markdown) |
| resource | `alicloud_ehpc_queue` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_queue.html.markdown) |

## Elastic IP Address (EIP)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_eip_addresses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eip_addresses.html.markdown) |
| data source | `alicloud_eips` | ⚠️ 弃用 → `alicloud_eip_addresses` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/eips.html.markdown) |
| resource | `alicloud_eip` | ⚠️ 弃用 → `alicloud_eip_address` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip.html.markdown) |
| resource | `alicloud_eip_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip_address.html.markdown) |
| resource | `alicloud_eip_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip_association.html.markdown) |
| resource | `alicloud_eip_segment_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip_segment_address.html.markdown) |

## Elasticsearch

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_elasticsearch` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/elasticsearch.html.markdown) |
| data source | `alicloud_elasticsearch_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/elasticsearch_zones.html.markdown) |
| resource | `alicloud_elasticsearch_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/elasticsearch_instance.html.markdown) |

## Enterprise Mobile Application Studio (MHUB)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_mhub_apps` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mhub_apps.html.markdown) |
| data source | `alicloud_mhub_products` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mhub_products.html.markdown) |
| resource | `alicloud_mhub_app` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mhub_app.html.markdown) |
| resource | `alicloud_mhub_product` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mhub_product.html.markdown) |

## Event Bridge

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_event_bridge_event_buses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/event_bridge_event_buses.html.markdown) |
| data source | `alicloud_event_bridge_event_sources` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/event_bridge_event_sources.html.markdown) |
| data source | `alicloud_event_bridge_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/event_bridge_rules.html.markdown) |
| data source | `alicloud_event_bridge_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/event_bridge_service.html.markdown) |
| resource | `alicloud_event_bridge_api_destination` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_api_destination.html.markdown) |
| resource | `alicloud_event_bridge_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_connection.html.markdown) |
| resource | `alicloud_event_bridge_event_bus` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_event_bus.html.markdown) |
| resource | `alicloud_event_bridge_event_source` | ⚠️ 弃用 → `alicloud_event_bridge_event_source_v2` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_event_source.html.markdown) |
| resource | `alicloud_event_bridge_event_source_v2` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_event_source_v2.html.markdown) |
| resource | `alicloud_event_bridge_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_rule.html.markdown) |
| resource | `alicloud_event_bridge_service_linked_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_service_linked_role.html.markdown) |

## Express Connect

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_express_connect_access_points` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_access_points.html.markdown) |
| data source | `alicloud_express_connect_grant_rule_to_cens` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_grant_rule_to_cens.html.markdown) |
| data source | `alicloud_express_connect_physical_connection_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_physical_connection_service.html.markdown) |
| data source | `alicloud_express_connect_physical_connections` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_physical_connections.html.markdown) |
| data source | `alicloud_express_connect_router_interfaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_router_interfaces.html.markdown) |
| data source | `alicloud_express_connect_vbr_pconn_associations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_vbr_pconn_associations.html.markdown) |
| data source | `alicloud_express_connect_virtual_border_routers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_virtual_border_routers.html.markdown) |
| data source | `alicloud_express_connect_virtual_physical_connections` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/express_connect_virtual_physical_connections.html.markdown) |
| data source | `alicloud_router_interfaces` | ⚠️ 弃用 → `alicloud_express_connect_router_interfaces` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/router_interfaces.html.markdown) |
| data source | `alicloud_vpc_bgp_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_bgp_groups.html.markdown) |
| data source | `alicloud_vpc_bgp_networks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_bgp_networks.html.markdown) |
| data source | `alicloud_vpc_bgp_peers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_bgp_peers.html.markdown) |
| resource | `alicloud_express_connect_ec_failover_test_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_ec_failover_test_job.html.markdown) |
| resource | `alicloud_express_connect_grant_rule_to_cen` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_grant_rule_to_cen.html.markdown) |
| resource | `alicloud_express_connect_physical_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_physical_connection.html.markdown) |
| resource | `alicloud_express_connect_router_interface` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_interface.html.markdown) |
| resource | `alicloud_express_connect_traffic_qos` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos.html.markdown) |
| resource | `alicloud_express_connect_traffic_qos_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos_association.html.markdown) |
| resource | `alicloud_express_connect_traffic_qos_queue` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos_queue.html.markdown) |
| resource | `alicloud_express_connect_traffic_qos_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos_rule.html.markdown) |
| resource | `alicloud_express_connect_vbr_pconn_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_vbr_pconn_association.html.markdown) |
| resource | `alicloud_express_connect_virtual_border_router` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_virtual_border_router.html.markdown) |
| resource | `alicloud_express_connect_virtual_physical_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_virtual_physical_connection.html.markdown) |
| resource | `alicloud_router_interface` | ⚠️ 弃用 → `alicloud_express_connect_router_interface` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/router_interface.html.markdown) |
| resource | `alicloud_router_interface_connection` | ⚠️ 弃用 → `alicloud_express_connect_router_interface` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/router_interface_connection.html.markdown) |
| resource | `alicloud_vpc_bgp_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_bgp_group.html.markdown) |
| resource | `alicloud_vpc_bgp_network` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_bgp_network.html.markdown) |
| resource | `alicloud_vpc_bgp_peer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_bgp_peer.html.markdown) |
| resource | `alicloud_vpc_vbr_ha` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_vbr_ha.html.markdown) |

## Express Connect Router

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_express_connect_router_express_connect_router` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_express_connect_router.html.markdown) |
| resource | `alicloud_express_connect_router_grant_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_grant_association.html.markdown) |
| resource | `alicloud_express_connect_router_tr_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_tr_association.html.markdown) |
| resource | `alicloud_express_connect_router_vbr_child_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_vbr_child_instance.html.markdown) |
| resource | `alicloud_express_connect_router_vpc_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_vpc_association.html.markdown) |

## File Storage (NAS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_nas_access_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_access_groups.html.markdown) |
| data source | `alicloud_nas_access_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_access_rules.html.markdown) |
| data source | `alicloud_nas_auto_snapshot_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_auto_snapshot_policies.html.markdown) |
| data source | `alicloud_nas_data_flows` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_data_flows.html.markdown) |
| data source | `alicloud_nas_file_systems` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_file_systems.html.markdown) |
| data source | `alicloud_nas_filesets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_filesets.html.markdown) |
| data source | `alicloud_nas_lifecycle_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_lifecycle_policies.html.markdown) |
| data source | `alicloud_nas_mount_targets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_mount_targets.html.markdown) |
| data source | `alicloud_nas_protocols` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_protocols.html.markdown) |
| data source | `alicloud_nas_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_service.html.markdown) |
| data source | `alicloud_nas_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_snapshots.html.markdown) |
| data source | `alicloud_nas_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nas_zones.html.markdown) |
| resource | `alicloud_nas_access_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_access_group.html.markdown) |
| resource | `alicloud_nas_access_point` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_access_point.html.markdown) |
| resource | `alicloud_nas_access_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_access_rule.html.markdown) |
| resource | `alicloud_nas_auto_snapshot_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_auto_snapshot_policy.html.markdown) |
| resource | `alicloud_nas_data_flow` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_data_flow.html.markdown) |
| resource | `alicloud_nas_file_system` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_file_system.html.markdown) |
| resource | `alicloud_nas_fileset` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_fileset.html.markdown) |
| resource | `alicloud_nas_lifecycle_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_lifecycle_policy.html.markdown) |
| resource | `alicloud_nas_mount_target` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_mount_target.html.markdown) |
| resource | `alicloud_nas_protocol_mount_target` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_protocol_mount_target.html.markdown) |
| resource | `alicloud_nas_protocol_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_protocol_service.html.markdown) |
| resource | `alicloud_nas_recycle_bin` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_recycle_bin.html.markdown) |
| resource | `alicloud_nas_smb_acl_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_smb_acl_attachment.html.markdown) |
| resource | `alicloud_nas_snapshot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_snapshot.html.markdown) |

## Function Compute Service (FC)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_fc_custom_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fc_custom_domains.html.markdown) |
| data source | `alicloud_fc_functions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fc_functions.html.markdown) |
| data source | `alicloud_fc_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fc_service.html.markdown) |
| data source | `alicloud_fc_services` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fc_services.html.markdown) |
| data source | `alicloud_fc_triggers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fc_triggers.html.markdown) |
| data source | `alicloud_fc_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fc_zones.html.markdown) |
| resource | `alicloud_fc_alias` | ⚠️ 弃用 → `alicloud_fcv3_alias` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_alias.html.markdown) |
| resource | `alicloud_fc_custom_domain` | ⚠️ 弃用 → `alicloud_fcv3_custom_domain` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_custom_domain.html.markdown) |
| resource | `alicloud_fc_function` | ⚠️ 弃用 → `alicloud_fcv3_function` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_function.html.markdown) |
| resource | `alicloud_fc_function_async_invoke_config` | ⚠️ 弃用 → `alicloud_fcv3_async_invoke_config` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_function_async_invoke_config.html.markdown) |
| resource | `alicloud_fc_layer_version` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_layer_version.html.markdown) |
| resource | `alicloud_fc_service` | ⚠️ 弃用 → `alicloud_fcv3_function` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_service.html.markdown) |
| resource | `alicloud_fc_trigger` | ⚠️ 弃用 → `alicloud_fcv3_trigger` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_trigger.html.markdown) |
| resource | `alicloud_fcv2_function` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv2_function.html.markdown) |

## Function Compute Service V3 (FCV3)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_fcv3_functions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fcv3_functions.html.markdown) |
| data source | `alicloud_fcv3_triggers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fcv3_triggers.html.markdown) |
| resource | `alicloud_fcv3_alias` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_alias.html.markdown) |
| resource | `alicloud_fcv3_async_invoke_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_async_invoke_config.html.markdown) |
| resource | `alicloud_fcv3_concurrency_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_concurrency_config.html.markdown) |
| resource | `alicloud_fcv3_custom_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_custom_domain.html.markdown) |
| resource | `alicloud_fcv3_function` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_function.html.markdown) |
| resource | `alicloud_fcv3_function_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_function_version.html.markdown) |
| resource | `alicloud_fcv3_layer_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_layer_version.html.markdown) |
| resource | `alicloud_fcv3_provision_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_provision_config.html.markdown) |
| resource | `alicloud_fcv3_trigger` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_trigger.html.markdown) |
| resource | `alicloud_fcv3_vpc_binding` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_vpc_binding.html.markdown) |

## GWLB

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_gwlb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/gwlb_zones.html.markdown) |
| resource | `alicloud_gwlb_listener` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gwlb_listener.html.markdown) |
| resource | `alicloud_gwlb_load_balancer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gwlb_load_balancer.html.markdown) |
| resource | `alicloud_gwlb_server_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gwlb_server_group.html.markdown) |

## Global Accelerator (GA)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ga_accelerator_spare_ip_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_accelerator_spare_ip_attachments.html.markdown) |
| data source | `alicloud_ga_accelerators` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_accelerators.html.markdown) |
| data source | `alicloud_ga_acls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_acls.html.markdown) |
| data source | `alicloud_ga_additional_certificates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_additional_certificates.html.markdown) |
| data source | `alicloud_ga_bandwidth_packages` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_bandwidth_packages.html.markdown) |
| data source | `alicloud_ga_basic_accelerate_ip_endpoint_relations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_basic_accelerate_ip_endpoint_relations.html.markdown) |
| data source | `alicloud_ga_basic_accelerate_ips` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_basic_accelerate_ips.html.markdown) |
| data source | `alicloud_ga_basic_accelerators` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_basic_accelerators.html.markdown) |
| data source | `alicloud_ga_basic_endpoints` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_basic_endpoints.html.markdown) |
| data source | `alicloud_ga_custom_routing_endpoint_group_destinations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_custom_routing_endpoint_group_destinations.html.markdown) |
| data source | `alicloud_ga_custom_routing_endpoint_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_custom_routing_endpoint_groups.html.markdown) |
| data source | `alicloud_ga_custom_routing_endpoint_traffic_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_custom_routing_endpoint_traffic_policies.html.markdown) |
| data source | `alicloud_ga_custom_routing_endpoints` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_custom_routing_endpoints.html.markdown) |
| data source | `alicloud_ga_custom_routing_port_mappings` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_custom_routing_port_mappings.html.markdown) |
| data source | `alicloud_ga_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_domains.html.markdown) |
| data source | `alicloud_ga_endpoint_group_ip_address_cidr_blocks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_endpoint_group_ip_address_cidr_blocks.html.markdown) |
| data source | `alicloud_ga_endpoint_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_endpoint_groups.html.markdown) |
| data source | `alicloud_ga_forwarding_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_forwarding_rules.html.markdown) |
| data source | `alicloud_ga_ip_sets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_ip_sets.html.markdown) |
| data source | `alicloud_ga_listeners` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ga_listeners.html.markdown) |
| resource | `alicloud_ga_accelerator` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_accelerator.html.markdown) |
| resource | `alicloud_ga_accelerator_spare_ip_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_accelerator_spare_ip_attachment.html.markdown) |
| resource | `alicloud_ga_access_log` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_access_log.html.markdown) |
| resource | `alicloud_ga_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_acl.html.markdown) |
| resource | `alicloud_ga_acl_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_acl_attachment.html.markdown) |
| resource | `alicloud_ga_acl_entry_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_acl_entry_attachment.html.markdown) |
| resource | `alicloud_ga_additional_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_additional_certificate.html.markdown) |
| resource | `alicloud_ga_bandwidth_package` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_bandwidth_package.html.markdown) |
| resource | `alicloud_ga_bandwidth_package_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_bandwidth_package_attachment.html.markdown) |
| resource | `alicloud_ga_basic_accelerate_ip` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_accelerate_ip.html.markdown) |
| resource | `alicloud_ga_basic_accelerate_ip_endpoint_relation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_accelerate_ip_endpoint_relation.html.markdown) |
| resource | `alicloud_ga_basic_accelerator` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_accelerator.html.markdown) |
| resource | `alicloud_ga_basic_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_endpoint.html.markdown) |
| resource | `alicloud_ga_basic_endpoint_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_endpoint_group.html.markdown) |
| resource | `alicloud_ga_basic_ip_set` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_ip_set.html.markdown) |
| resource | `alicloud_ga_custom_routing_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint.html.markdown) |
| resource | `alicloud_ga_custom_routing_endpoint_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint_group.html.markdown) |
| resource | `alicloud_ga_custom_routing_endpoint_group_destination` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint_group_destination.html.markdown) |
| resource | `alicloud_ga_custom_routing_endpoint_traffic_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint_traffic_policy.html.markdown) |
| resource | `alicloud_ga_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_domain.html.markdown) |
| resource | `alicloud_ga_endpoint_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_endpoint_group.html.markdown) |
| resource | `alicloud_ga_forwarding_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_forwarding_rule.html.markdown) |
| resource | `alicloud_ga_ip_set` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_ip_set.html.markdown) |
| resource | `alicloud_ga_listener` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_listener.html.markdown) |

## Governance

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_governance_baselines` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/governance_baselines.html.markdown) |
| resource | `alicloud_governance_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/governance_account.html.markdown) |
| resource | `alicloud_governance_baseline` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/governance_baseline.html.markdown) |

## Graph Database

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_graph_database_db_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/graph_database_db_instances.html.markdown) |
| resource | `alicloud_graph_database_db_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/graph_database_db_instance.html.markdown) |

## HBase

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_hbase_instance_types` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbase_instance_types.html.markdown) |
| data source | `alicloud_hbase_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbase_instances.html.markdown) |
| data source | `alicloud_hbase_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbase_zones.html.markdown) |
| resource | `alicloud_hbase_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbase_instance.html.markdown) |

## Hologres (Hologram)

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_hologram_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hologram_instance.html.markdown) |

## Hybrid Backup Recovery (HBR)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_hbr_backup_jobs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_backup_jobs.html.markdown) |
| data source | `alicloud_hbr_ecs_backup_clients` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_ecs_backup_clients.html.markdown) |
| data source | `alicloud_hbr_ecs_backup_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_ecs_backup_plans.html.markdown) |
| data source | `alicloud_hbr_hana_backup_clients` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_hana_backup_clients.html.markdown) |
| data source | `alicloud_hbr_hana_backup_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_hana_backup_plans.html.markdown) |
| data source | `alicloud_hbr_hana_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_hana_instances.html.markdown) |
| data source | `alicloud_hbr_nas_backup_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_nas_backup_plans.html.markdown) |
| data source | `alicloud_hbr_oss_backup_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_oss_backup_plans.html.markdown) |
| data source | `alicloud_hbr_ots_backup_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_ots_backup_plans.html.markdown) |
| data source | `alicloud_hbr_ots_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_ots_snapshots.html.markdown) |
| data source | `alicloud_hbr_replication_vault_regions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_replication_vault_regions.html.markdown) |
| data source | `alicloud_hbr_restore_jobs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_restore_jobs.html.markdown) |
| data source | `alicloud_hbr_server_backup_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_server_backup_plans.html.markdown) |
| data source | `alicloud_hbr_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_service.html.markdown) |
| data source | `alicloud_hbr_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_snapshots.html.markdown) |
| data source | `alicloud_hbr_udm_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_udm_snapshots.html.markdown) |
| data source | `alicloud_hbr_vaults` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/hbr_vaults.html.markdown) |
| resource | `alicloud_hbr_cross_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_cross_account.html.markdown) |
| resource | `alicloud_hbr_ecs_backup_client` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_ecs_backup_client.html.markdown) |
| resource | `alicloud_hbr_ecs_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_ecs_backup_plan.html.markdown) |
| resource | `alicloud_hbr_hana_backup_client` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_hana_backup_client.html.markdown) |
| resource | `alicloud_hbr_hana_backup_plan` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_hana_backup_plan.html.markdown) |
| resource | `alicloud_hbr_hana_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_hana_instance.html.markdown) |
| resource | `alicloud_hbr_nas_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_nas_backup_plan.html.markdown) |
| resource | `alicloud_hbr_oss_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_oss_backup_plan.html.markdown) |
| resource | `alicloud_hbr_ots_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_ots_backup_plan.html.markdown) |
| resource | `alicloud_hbr_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_policy.html.markdown) |
| resource | `alicloud_hbr_policy_binding` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_policy_binding.html.markdown) |
| resource | `alicloud_hbr_replication_vault` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_replication_vault.html.markdown) |
| resource | `alicloud_hbr_restore_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_restore_job.html.markdown) |
| resource | `alicloud_hbr_server_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_server_backup_plan.html.markdown) |
| resource | `alicloud_hbr_vault` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_vault.html.markdown) |

## IMS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ims_oidc_providers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ims_oidc_providers.html.markdown) |
| resource | `alicloud_ims_oidc_provider` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ims_oidc_provider.html.markdown) |

## Intelligent Media Management (IMM)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_imm_projects` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/imm_projects.html.markdown) |
| resource | `alicloud_imm_project` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/imm_project.html.markdown) |

## Internet of Things (Iot)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_iot_device_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/iot_device_groups.html.markdown) |
| data source | `alicloud_iot_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/iot_service.html.markdown) |
| resource | `alicloud_iot_device_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/iot_device_group.html.markdown) |

## KMS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_kms_aliases` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_aliases.html.markdown) |
| data source | `alicloud_kms_ciphertext` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_ciphertext.html.markdown) |
| data source | `alicloud_kms_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_instances.html.markdown) |
| data source | `alicloud_kms_key_versions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_key_versions.html.markdown) |
| data source | `alicloud_kms_keys` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_keys.html.markdown) |
| data source | `alicloud_kms_plaintext` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_plaintext.html.markdown) |
| data source | `alicloud_kms_secret_versions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_secret_versions.html.markdown) |
| data source | `alicloud_kms_secrets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_secrets.html.markdown) |
| data source | `alicloud_kms_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kms_service.html.markdown) |
| resource | `alicloud_kms_alias` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_alias.html.markdown) |
| resource | `alicloud_kms_application_access_point` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_application_access_point.html.markdown) |
| resource | `alicloud_kms_ciphertext` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_ciphertext.html.markdown) |
| resource | `alicloud_kms_client_key` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_client_key.html.markdown) |
| resource | `alicloud_kms_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_instance.html.markdown) |
| resource | `alicloud_kms_key` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_key.html.markdown) |
| resource | `alicloud_kms_key_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_key_version.html.markdown) |
| resource | `alicloud_kms_network_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_network_rule.html.markdown) |
| resource | `alicloud_kms_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_policy.html.markdown) |
| resource | `alicloud_kms_secret` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_secret.html.markdown) |
| resource | `alicloud_kms_value_added_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_value_added_service.html.markdown) |

## Lindorm

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_lindorm_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/lindorm_instances.html.markdown) |
| resource | `alicloud_lindorm_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/lindorm_instance.html.markdown) |
| resource | `alicloud_lindorm_instance_v2` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/lindorm_instance_v2.html.markdown) |
| resource | `alicloud_lindorm_public_network` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/lindorm_public_network.html.markdown) |

## Live

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_live_caster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/live_caster.html.markdown) |
| resource | `alicloud_live_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/live_domain.html.markdown) |

## Log Service (SLS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_log_alert_resource` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/log_alert_resource.html.markdown) |
| data source | `alicloud_log_projects` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/log_projects.html.markdown) |
| data source | `alicloud_log_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/log_service.html.markdown) |
| data source | `alicloud_log_stores` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/log_stores.html.markdown) |
| data source | `alicloud_sls_alerts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sls_alerts.html.markdown) |
| data source | `alicloud_sls_etls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sls_etls.html.markdown) |
| data source | `alicloud_sls_indexs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sls_indexs.html.markdown) |
| data source | `alicloud_sls_logtail_configs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sls_logtail_configs.html.markdown) |
| data source | `alicloud_sls_machine_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sls_machine_groups.html.markdown) |
| resource | `alicloud_log_alert` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_alert.html.markdown) |
| resource | `alicloud_log_alert_resource` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_alert_resource.html.markdown) |
| resource | `alicloud_log_audit` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_audit.html.markdown) |
| resource | `alicloud_log_dashboard` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_dashboard.html.markdown) |
| resource | `alicloud_log_etl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_etl.html.markdown) |
| resource | `alicloud_log_ingestion` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_ingestion.html.markdown) |
| resource | `alicloud_log_machine_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_machine_group.html.markdown) |
| resource | `alicloud_log_oss_export` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_oss_export.html.markdown) |
| resource | `alicloud_log_oss_shipper` | ⚠️ 弃用 → `alicloud_log_oss_export` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_oss_shipper.html.markdown) |
| resource | `alicloud_log_project` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_project.html.markdown) |
| resource | `alicloud_log_resource` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_resource.html.markdown) |
| resource | `alicloud_log_resource_record` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_resource_record.html.markdown) |
| resource | `alicloud_log_store` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_store.html.markdown) |
| resource | `alicloud_log_store_index` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_store_index.html.markdown) |
| resource | `alicloud_logtail_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/logtail_attachment.html.markdown) |
| resource | `alicloud_logtail_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/logtail_config.html.markdown) |
| resource | `alicloud_sls_alert` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_alert.html.markdown) |
| resource | `alicloud_sls_collection_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_collection_policy.html.markdown) |
| resource | `alicloud_sls_etl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_etl.html.markdown) |
| resource | `alicloud_sls_index` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_index.html.markdown) |
| resource | `alicloud_sls_logtail_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_logtail_config.html.markdown) |
| resource | `alicloud_sls_logtail_pipeline_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_logtail_pipeline_config.html.markdown) |
| resource | `alicloud_sls_machine_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_machine_group.html.markdown) |
| resource | `alicloud_sls_oss_export_sink` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_oss_export_sink.html.markdown) |
| resource | `alicloud_sls_scheduled_sql` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_scheduled_sql.html.markdown) |

## Market Place

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_market_product` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/market_product.html.markdown) |
| data source | `alicloud_market_products` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/market_products.html.markdown) |
| resource | `alicloud_market_order` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/market_order.html.markdown) |

## Max Compute

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_maxcompute_projects` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/maxcompute_projects.html.markdown) |
| data source | `alicloud_maxcompute_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/maxcompute_service.html.markdown) |
| resource | `alicloud_max_compute_quota` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_quota.html.markdown) |
| resource | `alicloud_max_compute_quota_plan` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_quota_plan.html.markdown) |
| resource | `alicloud_max_compute_quota_schedule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_quota_schedule.html.markdown) |
| resource | `alicloud_max_compute_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_role.html.markdown) |
| resource | `alicloud_max_compute_role_user_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_role_user_attachment.html.markdown) |
| resource | `alicloud_max_compute_tenant_role_user_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_tenant_role_user_attachment.html.markdown) |
| resource | `alicloud_max_compute_tunnel_quota_timer` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_tunnel_quota_timer.html.markdown) |
| resource | `alicloud_maxcompute_project` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/maxcompute_project.html.markdown) |

## Message Center (MscSub)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_msc_sub_contact_verification_message` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/msc_sub_contact_verification_message.html.markdown) |
| data source | `alicloud_msc_sub_contacts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/msc_sub_contacts.html.markdown) |
| data source | `alicloud_msc_sub_subscriptions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/msc_sub_subscriptions.html.markdown) |
| data source | `alicloud_msc_sub_webhooks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/msc_sub_webhooks.html.markdown) |
| resource | `alicloud_msc_sub_contact` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/msc_sub_contact.html.markdown) |
| resource | `alicloud_msc_sub_subscription` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/msc_sub_subscription.html.markdown) |
| resource | `alicloud_msc_sub_webhook` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/msc_sub_webhook.html.markdown) |

## Message Service

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_message_service_queues` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/message_service_queues.html.markdown) |
| data source | `alicloud_message_service_subscriptions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/message_service_subscriptions.html.markdown) |
| data source | `alicloud_message_service_topics` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/message_service_topics.html.markdown) |
| data source | `alicloud_mns_queues` | ⚠️ 弃用 → `alicloud_message_service_queues` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mns_queues.html.markdown) |
| data source | `alicloud_mns_service` | ⚠️ 弃用 → `alicloud_message_service_service` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mns_service.html.markdown) |
| data source | `alicloud_mns_topic_subscriptions` | ⚠️ 弃用 → `alicloud_message_service_subscriptions` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mns_topic_subscriptions.html.markdown) |
| data source | `alicloud_mns_topics` | ⚠️ 弃用 → `alicloud_message_service_topics` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mns_topics.html.markdown) |
| resource | `alicloud_message_service_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_endpoint.html.markdown) |
| resource | `alicloud_message_service_endpoint_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_endpoint_acl.html.markdown) |
| resource | `alicloud_message_service_event_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_event_rule.html.markdown) |
| resource | `alicloud_message_service_queue` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_queue.html.markdown) |
| resource | `alicloud_message_service_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_service.html.markdown) |
| resource | `alicloud_message_service_subscription` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_subscription.html.markdown) |
| resource | `alicloud_message_service_topic` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_topic.html.markdown) |
| resource | `alicloud_mns_queue` | ⚠️ 弃用 → `alicloud_message_service_queue` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mns_queue.html.markdown) |
| resource | `alicloud_mns_topic` | ⚠️ 弃用 → `alicloud_message_service_topic` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mns_topic.html.markdown) |
| resource | `alicloud_mns_topic_subscription` | ⚠️ 弃用 → `alicloud_message_service_subscription` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mns_topic_subscription.html.markdown) |

## Microservice Engine (MSE)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_mse_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mse_clusters.html.markdown) |
| data source | `alicloud_mse_engine_namespaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mse_engine_namespaces.html.markdown) |
| data source | `alicloud_mse_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mse_gateways.html.markdown) |
| data source | `alicloud_mse_nacos_configs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mse_nacos_configs.html.markdown) |
| data source | `alicloud_mse_znodes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mse_znodes.html.markdown) |
| resource | `alicloud_mse_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_cluster.html.markdown) |
| resource | `alicloud_mse_engine_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_engine_namespace.html.markdown) |
| resource | `alicloud_mse_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_gateway.html.markdown) |
| resource | `alicloud_mse_nacos_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_nacos_config.html.markdown) |
| resource | `alicloud_mse_znode` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_znode.html.markdown) |

## Milvus

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_milvus_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/milvus_instance.html.markdown) |

## MongoDB

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_mongodb_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mongodb_accounts.html.markdown) |
| data source | `alicloud_mongodb_audit_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mongodb_audit_policies.html.markdown) |
| data source | `alicloud_mongodb_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mongodb_instances.html.markdown) |
| data source | `alicloud_mongodb_serverless_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mongodb_serverless_instances.html.markdown) |
| data source | `alicloud_mongodb_sharding_network_private_addresses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mongodb_sharding_network_private_addresses.html.markdown) |
| data source | `alicloud_mongodb_sharding_network_public_addresses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mongodb_sharding_network_public_addresses.html.markdown) |
| data source | `alicloud_mongodb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/mongodb_zones.html.markdown) |
| resource | `alicloud_mongodb_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_account.html.markdown) |
| resource | `alicloud_mongodb_audit_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_audit_policy.html.markdown) |
| resource | `alicloud_mongodb_global_security_ip_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_global_security_ip_group.html.markdown) |
| resource | `alicloud_mongodb_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_instance.html.markdown) |
| resource | `alicloud_mongodb_node` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_node.html.markdown) |
| resource | `alicloud_mongodb_private_srv_network_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_private_srv_network_address.html.markdown) |
| resource | `alicloud_mongodb_public_network_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_public_network_address.html.markdown) |
| resource | `alicloud_mongodb_replica_set_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_replica_set_role.html.markdown) |
| resource | `alicloud_mongodb_serverless_instance` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_serverless_instance.html.markdown) |
| resource | `alicloud_mongodb_sharding_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_sharding_instance.html.markdown) |
| resource | `alicloud_mongodb_sharding_network_private_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_sharding_network_private_address.html.markdown) |
| resource | `alicloud_mongodb_sharding_network_public_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_sharding_network_public_address.html.markdown) |

## NAT Gateway

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_forward_entries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/forward_entries.html.markdown) |
| data source | `alicloud_nat_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nat_gateways.html.markdown) |
| data source | `alicloud_snat_entries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/snat_entries.html.markdown) |
| data source | `alicloud_vpc_nat_ip_cidrs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_nat_ip_cidrs.html.markdown) |
| data source | `alicloud_vpc_nat_ips` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_nat_ips.html.markdown) |
| resource | `alicloud_forward_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/forward_entry.html.markdown) |
| resource | `alicloud_nat_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nat_gateway.html.markdown) |
| resource | `alicloud_snat_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/snat_entry.html.markdown) |
| resource | `alicloud_vpc_nat_ip` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_nat_ip.html.markdown) |
| resource | `alicloud_vpc_nat_ip_cidr` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_nat_ip_cidr.html.markdown) |

## Network Load Balancer (NLB)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_nlb_listeners` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nlb_listeners.html.markdown) |
| data source | `alicloud_nlb_load_balancers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nlb_load_balancers.html.markdown) |
| data source | `alicloud_nlb_security_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nlb_security_policies.html.markdown) |
| data source | `alicloud_nlb_server_group_server_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nlb_server_group_server_attachments.html.markdown) |
| data source | `alicloud_nlb_server_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nlb_server_groups.html.markdown) |
| data source | `alicloud_nlb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/nlb_zones.html.markdown) |
| resource | `alicloud_nlb_hd_monitor_region_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_hd_monitor_region_config.html.markdown) |
| resource | `alicloud_nlb_listener` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_listener.html.markdown) |
| resource | `alicloud_nlb_listener_additional_certificate_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_listener_additional_certificate_attachment.html.markdown) |
| resource | `alicloud_nlb_load_balancer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_load_balancer.html.markdown) |
| resource | `alicloud_nlb_load_balancer_security_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_load_balancer_security_group_attachment.html.markdown) |
| resource | `alicloud_nlb_load_balancer_zone_shifted_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_load_balancer_zone_shifted_attachment.html.markdown) |
| resource | `alicloud_nlb_loadbalancer_common_bandwidth_package_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_loadbalancer_common_bandwidth_package_attachment.html.markdown) |
| resource | `alicloud_nlb_security_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_security_policy.html.markdown) |
| resource | `alicloud_nlb_server_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_server_group.html.markdown) |
| resource | `alicloud_nlb_server_group_server_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_server_group_server_attachment.html.markdown) |

## OSS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_oss_bucket_objects` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oss_bucket_objects.html.markdown) |
| data source | `alicloud_oss_buckets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oss_buckets.html.markdown) |
| data source | `alicloud_oss_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oss_service.html.markdown) |
| resource | `alicloud_oss_access_point` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_access_point.html.markdown) |
| resource | `alicloud_oss_account_public_access_block` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_account_public_access_block.html.markdown) |
| resource | `alicloud_oss_bucket` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket.html.markdown) |
| resource | `alicloud_oss_bucket_access_monitor` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_access_monitor.html.markdown) |
| resource | `alicloud_oss_bucket_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_acl.html.markdown) |
| resource | `alicloud_oss_bucket_archive_direct_read` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_archive_direct_read.html.markdown) |
| resource | `alicloud_oss_bucket_cname` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_cname.html.markdown) |
| resource | `alicloud_oss_bucket_cname_token` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_cname_token.html.markdown) |
| resource | `alicloud_oss_bucket_cors` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_cors.html.markdown) |
| resource | `alicloud_oss_bucket_data_redundancy_transition` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_data_redundancy_transition.html.markdown) |
| resource | `alicloud_oss_bucket_https_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_https_config.html.markdown) |
| resource | `alicloud_oss_bucket_logging` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_logging.html.markdown) |
| resource | `alicloud_oss_bucket_meta_query` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_meta_query.html.markdown) |
| resource | `alicloud_oss_bucket_object` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_object.html.markdown) |
| resource | `alicloud_oss_bucket_overwrite_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_overwrite_config.html.markdown) |
| resource | `alicloud_oss_bucket_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_policy.html.markdown) |
| resource | `alicloud_oss_bucket_public_access_block` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_public_access_block.html.markdown) |
| resource | `alicloud_oss_bucket_referer` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_referer.html.markdown) |
| resource | `alicloud_oss_bucket_replication` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_replication.html.markdown) |
| resource | `alicloud_oss_bucket_request_payment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_request_payment.html.markdown) |
| resource | `alicloud_oss_bucket_response_header` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_response_header.html.markdown) |
| resource | `alicloud_oss_bucket_server_side_encryption` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_server_side_encryption.html.markdown) |
| resource | `alicloud_oss_bucket_style` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_style.html.markdown) |
| resource | `alicloud_oss_bucket_transfer_acceleration` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_transfer_acceleration.html.markdown) |
| resource | `alicloud_oss_bucket_user_defined_log_fields` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_user_defined_log_fields.html.markdown) |
| resource | `alicloud_oss_bucket_versioning` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_versioning.html.markdown) |
| resource | `alicloud_oss_bucket_website` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_website.html.markdown) |
| resource | `alicloud_oss_bucket_worm` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_worm.html.markdown) |

## Ocean Base

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ocean_base_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ocean_base_instances.html.markdown) |
| resource | `alicloud_ocean_base_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ocean_base_instance.html.markdown) |

## Open Api Explorer

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_open_api_explorer_api_mcp_server` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/open_api_explorer_api_mcp_server.html.markdown) |

## Open Search

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_open_search_app_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/open_search_app_groups.html.markdown) |
| resource | `alicloud_open_search_app_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/open_search_app_group.html.markdown) |

## Operation Orchestration Service (OOS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_oos_application_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_application_groups.html.markdown) |
| data source | `alicloud_oos_applications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_applications.html.markdown) |
| data source | `alicloud_oos_executions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_executions.html.markdown) |
| data source | `alicloud_oos_parameters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_parameters.html.markdown) |
| data source | `alicloud_oos_patch_baselines` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_patch_baselines.html.markdown) |
| data source | `alicloud_oos_secret_parameters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_secret_parameters.html.markdown) |
| data source | `alicloud_oos_state_configurations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_state_configurations.html.markdown) |
| data source | `alicloud_oos_templates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/oos_templates.html.markdown) |
| resource | `alicloud_oos_application` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_application.html.markdown) |
| resource | `alicloud_oos_application_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_application_group.html.markdown) |
| resource | `alicloud_oos_default_patch_baseline` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_default_patch_baseline.html.markdown) |
| resource | `alicloud_oos_execution` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_execution.html.markdown) |
| resource | `alicloud_oos_parameter` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_parameter.html.markdown) |
| resource | `alicloud_oos_patch_baseline` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_patch_baseline.html.markdown) |
| resource | `alicloud_oos_secret_parameter` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_secret_parameter.html.markdown) |
| resource | `alicloud_oos_service_setting` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_service_setting.html.markdown) |
| resource | `alicloud_oos_state_configuration` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_state_configuration.html.markdown) |
| resource | `alicloud_oos_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_template.html.markdown) |

## Other

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/account.html.markdown) |
| data source | `alicloud_file_crc64_checksum` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/file_crc64_checksum.html.markdown) |

## PAI

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_pai_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_service.html.markdown) |

## PAI Workspace

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_pai_workspace_code_source` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_code_source.html.markdown) |
| resource | `alicloud_pai_workspace_dataset` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_dataset.html.markdown) |
| resource | `alicloud_pai_workspace_datasetversion` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_datasetversion.html.markdown) |
| resource | `alicloud_pai_workspace_experiment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_experiment.html.markdown) |
| resource | `alicloud_pai_workspace_member` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_member.html.markdown) |
| resource | `alicloud_pai_workspace_model` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_model.html.markdown) |
| resource | `alicloud_pai_workspace_model_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_model_version.html.markdown) |
| resource | `alicloud_pai_workspace_run` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_run.html.markdown) |
| resource | `alicloud_pai_workspace_user_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_user_config.html.markdown) |
| resource | `alicloud_pai_workspace_workspace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_workspace.html.markdown) |

## Pai Flow

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_pai_flow_pipeline` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_flow_pipeline.html.markdown) |

## PolarDB

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_polardb_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_accounts.html.markdown) |
| data source | `alicloud_polardb_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_clusters.html.markdown) |
| data source | `alicloud_polardb_databases` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_databases.html.markdown) |
| data source | `alicloud_polardb_endpoints` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_endpoints.html.markdown) |
| data source | `alicloud_polardb_global_database_networks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_global_database_networks.html.markdown) |
| data source | `alicloud_polardb_node_classes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_node_classes.html.markdown) |
| data source | `alicloud_polardb_parameter_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_parameter_groups.html.markdown) |
| data source | `alicloud_polardb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/polardb_zones.html.markdown) |
| resource | `alicloud_polar_db_extension` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polar_db_extension.html.markdown) |
| resource | `alicloud_polardb_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_account.html.markdown) |
| resource | `alicloud_polardb_account_privilege` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_account_privilege.html.markdown) |
| resource | `alicloud_polardb_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_backup_policy.html.markdown) |
| resource | `alicloud_polardb_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_cluster.html.markdown) |
| resource | `alicloud_polardb_cluster_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_cluster_endpoint.html.markdown) |
| resource | `alicloud_polardb_database` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_database.html.markdown) |
| resource | `alicloud_polardb_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_endpoint.html.markdown) |
| resource | `alicloud_polardb_endpoint_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_endpoint_address.html.markdown) |
| resource | `alicloud_polardb_global_database_network` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_global_database_network.html.markdown) |
| resource | `alicloud_polardb_global_security_ip_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_global_security_ip_group.html.markdown) |
| resource | `alicloud_polardb_parameter_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_parameter_group.html.markdown) |
| resource | `alicloud_polardb_primary_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_primary_endpoint.html.markdown) |
| resource | `alicloud_polardb_zonal_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_zonal_account.html.markdown) |
| resource | `alicloud_polardb_zonal_db_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_zonal_db_cluster.html.markdown) |
| resource | `alicloud_polardb_zonal_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_zonal_endpoint.html.markdown) |

## Private Link

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_privatelink_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/privatelink_service.html.markdown) |
| data source | `alicloud_privatelink_vpc_endpoint_connections` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/privatelink_vpc_endpoint_connections.html.markdown) |
| data source | `alicloud_privatelink_vpc_endpoint_service_resources` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/privatelink_vpc_endpoint_service_resources.html.markdown) |
| data source | `alicloud_privatelink_vpc_endpoint_service_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/privatelink_vpc_endpoint_service_users.html.markdown) |
| data source | `alicloud_privatelink_vpc_endpoint_services` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/privatelink_vpc_endpoint_services.html.markdown) |
| data source | `alicloud_privatelink_vpc_endpoint_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/privatelink_vpc_endpoint_zones.html.markdown) |
| data source | `alicloud_privatelink_vpc_endpoints` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/privatelink_vpc_endpoints.html.markdown) |
| resource | `alicloud_privatelink_vpc_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint.html.markdown) |
| resource | `alicloud_privatelink_vpc_endpoint_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_connection.html.markdown) |
| resource | `alicloud_privatelink_vpc_endpoint_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_service.html.markdown) |
| resource | `alicloud_privatelink_vpc_endpoint_service_resource` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_service_resource.html.markdown) |
| resource | `alicloud_privatelink_vpc_endpoint_service_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_service_user.html.markdown) |
| resource | `alicloud_privatelink_vpc_endpoint_zone` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_zone.html.markdown) |

## Private Zone

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_pvtz_endpoints` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/pvtz_endpoints.html.markdown) |
| data source | `alicloud_pvtz_resolver_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/pvtz_resolver_zones.html.markdown) |
| data source | `alicloud_pvtz_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/pvtz_rules.html.markdown) |
| data source | `alicloud_pvtz_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/pvtz_service.html.markdown) |
| data source | `alicloud_pvtz_zone_records` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/pvtz_zone_records.html.markdown) |
| data source | `alicloud_pvtz_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/pvtz_zones.html.markdown) |
| resource | `alicloud_pvtz_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_endpoint.html.markdown) |
| resource | `alicloud_pvtz_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_rule.html.markdown) |
| resource | `alicloud_pvtz_rule_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_rule_attachment.html.markdown) |
| resource | `alicloud_pvtz_user_vpc_authorization` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_user_vpc_authorization.html.markdown) |
| resource | `alicloud_pvtz_zone` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_zone.html.markdown) |
| resource | `alicloud_pvtz_zone_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_zone_attachment.html.markdown) |
| resource | `alicloud_pvtz_zone_record` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_zone_record.html.markdown) |

## Quick BI

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_quick_bi_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/quick_bi_users.html.markdown) |
| resource | `alicloud_quick_bi_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quick_bi_user.html.markdown) |

## Quotas

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_quotas_quota_alarms` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/quotas_quota_alarms.html.markdown) |
| data source | `alicloud_quotas_quota_applications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/quotas_quota_applications.html.markdown) |
| data source | `alicloud_quotas_quotas` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/quotas_quotas.html.markdown) |
| data source | `alicloud_quotas_template_applications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/quotas_template_applications.html.markdown) |
| resource | `alicloud_quotas_quota_alarm` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_quota_alarm.html.markdown) |
| resource | `alicloud_quotas_quota_application` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_quota_application.html.markdown) |
| resource | `alicloud_quotas_template_applications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_template_applications.html.markdown) |
| resource | `alicloud_quotas_template_quota` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_template_quota.html.markdown) |
| resource | `alicloud_quotas_template_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_template_service.html.markdown) |

## RAM

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ram_account_alias` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_account_alias.html.markdown) |
| data source | `alicloud_ram_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_groups.html.markdown) |
| data source | `alicloud_ram_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_policies.html.markdown) |
| data source | `alicloud_ram_policy_document` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_policy_document.html.markdown) |
| data source | `alicloud_ram_role_policy_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_role_policy_attachments.html.markdown) |
| data source | `alicloud_ram_roles` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_roles.html.markdown) |
| data source | `alicloud_ram_saml_providers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_saml_providers.html.markdown) |
| data source | `alicloud_ram_system_policys` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_system_policys.html.markdown) |
| data source | `alicloud_ram_users` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ram_users.html.markdown) |
| resource | `alicloud_ram_access_key` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_access_key.html.markdown) |
| resource | `alicloud_ram_account_alias` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_account_alias.html.markdown) |
| resource | `alicloud_ram_account_password_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_account_password_policy.html.markdown) |
| resource | `alicloud_ram_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_group.html.markdown) |
| resource | `alicloud_ram_group_membership` | ⚠️ 弃用 → `alicloud_ram_user_group_attachment` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_group_membership.html.markdown) |
| resource | `alicloud_ram_group_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_group_policy_attachment.html.markdown) |
| resource | `alicloud_ram_login_profile` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_login_profile.html.markdown) |
| resource | `alicloud_ram_password_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_password_policy.html.markdown) |
| resource | `alicloud_ram_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_policy.html.markdown) |
| resource | `alicloud_ram_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_role.html.markdown) |
| resource | `alicloud_ram_role_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_role_policy_attachment.html.markdown) |
| resource | `alicloud_ram_saml_provider` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_saml_provider.html.markdown) |
| resource | `alicloud_ram_security_preference` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_security_preference.html.markdown) |
| resource | `alicloud_ram_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_user.html.markdown) |
| resource | `alicloud_ram_user_group_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_user_group_attachment.html.markdown) |
| resource | `alicloud_ram_user_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_user_policy_attachment.html.markdown) |

## RDS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_db_instance_class_infos` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/db_instance_class_infos.html.markdown) |
| data source | `alicloud_db_instance_classes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/db_instance_classes.html.markdown) |
| data source | `alicloud_db_instance_engines` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/db_instance_engines.html.markdown) |
| data source | `alicloud_db_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/db_instances.html.markdown) |
| data source | `alicloud_db_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/db_zones.html.markdown) |
| data source | `alicloud_instance_keywords` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/instance_keywords.html.markdown) |
| data source | `alicloud_rds_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_accounts.html.markdown) |
| data source | `alicloud_rds_backups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_backups.html.markdown) |
| data source | `alicloud_rds_character_set_names` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_character_set_names.html.markdown) |
| data source | `alicloud_rds_class_details` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_class_details.html.markdown) |
| data source | `alicloud_rds_collation_time_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_collation_time_zones.html.markdown) |
| data source | `alicloud_rds_cross_region_backups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_cross_region_backups.html.markdown) |
| data source | `alicloud_rds_cross_regions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_cross_regions.html.markdown) |
| data source | `alicloud_rds_modify_parameter_logs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_modify_parameter_logs.html.markdown) |
| data source | `alicloud_rds_parameter_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_parameter_group.html.markdown) |
| data source | `alicloud_rds_slots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/rds_slots.html.markdown) |
| resource | `alicloud_db_account` | ⚠️ 弃用 → `alicloud_rds_account` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_account.html.markdown) |
| resource | `alicloud_db_account_privilege` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_account_privilege.html.markdown) |
| resource | `alicloud_db_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_backup_policy.html.markdown) |
| resource | `alicloud_db_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_connection.html.markdown) |
| resource | `alicloud_db_database` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_database.html.markdown) |
| resource | `alicloud_db_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_instance.html.markdown) |
| resource | `alicloud_db_read_write_splitting_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_read_write_splitting_connection.html.markdown) |
| resource | `alicloud_db_readonly_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_readonly_instance.html.markdown) |
| resource | `alicloud_rds_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_account.html.markdown) |
| resource | `alicloud_rds_backup` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_backup.html.markdown) |
| resource | `alicloud_rds_clone_db_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_clone_db_instance.html.markdown) |
| resource | `alicloud_rds_custom` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_custom.html.markdown) |
| resource | `alicloud_rds_custom_deployment_set` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_custom_deployment_set.html.markdown) |
| resource | `alicloud_rds_custom_disk` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_custom_disk.html.markdown) |
| resource | `alicloud_rds_custom_disk_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_custom_disk_attachment.html.markdown) |
| resource | `alicloud_rds_db_instance_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_instance_endpoint.html.markdown) |
| resource | `alicloud_rds_db_instance_endpoint_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_instance_endpoint_address.html.markdown) |
| resource | `alicloud_rds_db_node` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_node.html.markdown) |
| resource | `alicloud_rds_db_proxy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_proxy.html.markdown) |
| resource | `alicloud_rds_db_proxy_public` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_proxy_public.html.markdown) |
| resource | `alicloud_rds_ddr_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_ddr_instance.html.markdown) |
| resource | `alicloud_rds_instance_cross_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_instance_cross_backup_policy.html.markdown) |
| resource | `alicloud_rds_parameter_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_parameter_group.html.markdown) |
| resource | `alicloud_rds_service_linked_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_service_linked_role.html.markdown) |
| resource | `alicloud_rds_upgrade_db_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_upgrade_db_instance.html.markdown) |
| resource | `alicloud_rds_whitelist_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_whitelist_template.html.markdown) |

## ROS

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ros_change_sets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ros_change_sets.html.markdown) |
| data source | `alicloud_ros_regions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ros_regions.html.markdown) |
| data source | `alicloud_ros_stack_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ros_stack_groups.html.markdown) |
| data source | `alicloud_ros_stack_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ros_stack_instances.html.markdown) |
| data source | `alicloud_ros_stacks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ros_stacks.html.markdown) |
| data source | `alicloud_ros_template_scratches` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ros_template_scratches.html.markdown) |
| data source | `alicloud_ros_templates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ros_templates.html.markdown) |
| resource | `alicloud_ros_change_set` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_change_set.html.markdown) |
| resource | `alicloud_ros_stack` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_stack.html.markdown) |
| resource | `alicloud_ros_stack_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_stack_group.html.markdown) |
| resource | `alicloud_ros_stack_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_stack_instance.html.markdown) |
| resource | `alicloud_ros_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_template.html.markdown) |
| resource | `alicloud_ros_template_scratch` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_template_scratch.html.markdown) |

## RabbitMQ (AMQP)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_amqp_bindings` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/amqp_bindings.html.markdown) |
| data source | `alicloud_amqp_exchanges` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/amqp_exchanges.html.markdown) |
| data source | `alicloud_amqp_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/amqp_instances.html.markdown) |
| data source | `alicloud_amqp_queues` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/amqp_queues.html.markdown) |
| data source | `alicloud_amqp_static_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/amqp_static_accounts.html.markdown) |
| data source | `alicloud_amqp_virtual_hosts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/amqp_virtual_hosts.html.markdown) |
| resource | `alicloud_amqp_binding` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_binding.html.markdown) |
| resource | `alicloud_amqp_exchange` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_exchange.html.markdown) |
| resource | `alicloud_amqp_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_instance.html.markdown) |
| resource | `alicloud_amqp_queue` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_queue.html.markdown) |
| resource | `alicloud_amqp_static_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_static_account.html.markdown) |
| resource | `alicloud_amqp_virtual_host` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_virtual_host.html.markdown) |

## Rds Ai

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_rds_ai_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_ai_instance.html.markdown) |

## Realtime Compute

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_realtime_compute_deployment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/realtime_compute_deployment.html.markdown) |
| resource | `alicloud_realtime_compute_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/realtime_compute_job.html.markdown) |
| resource | `alicloud_realtime_compute_vvp_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/realtime_compute_vvp_instance.html.markdown) |

## Resource Manager

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_resource_manager_account_deletion_check_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_account_deletion_check_task.html.markdown) |
| data source | `alicloud_resource_manager_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_accounts.html.markdown) |
| data source | `alicloud_resource_manager_control_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_control_policies.html.markdown) |
| data source | `alicloud_resource_manager_control_policy_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_control_policy_attachments.html.markdown) |
| data source | `alicloud_resource_manager_delegated_administrators` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_delegated_administrators.html.markdown) |
| data source | `alicloud_resource_manager_folders` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_folders.html.markdown) |
| data source | `alicloud_resource_manager_handshakes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_handshakes.html.markdown) |
| data source | `alicloud_resource_manager_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_policies.html.markdown) |
| data source | `alicloud_resource_manager_policy_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_policy_attachments.html.markdown) |
| data source | `alicloud_resource_manager_policy_versions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_policy_versions.html.markdown) |
| data source | `alicloud_resource_manager_resource_directories` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_resource_directories.html.markdown) |
| data source | `alicloud_resource_manager_resource_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_resource_groups.html.markdown) |
| data source | `alicloud_resource_manager_resource_shares` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_resource_shares.html.markdown) |
| data source | `alicloud_resource_manager_roles` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_roles.html.markdown) |
| data source | `alicloud_resource_manager_shared_resources` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_shared_resources.html.markdown) |
| data source | `alicloud_resource_manager_shared_targets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/resource_manager_shared_targets.html.markdown) |
| resource | `alicloud_resource_manager_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_account.html.markdown) |
| resource | `alicloud_resource_manager_auto_grouping_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_auto_grouping_rule.html.markdown) |
| resource | `alicloud_resource_manager_control_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_control_policy.html.markdown) |
| resource | `alicloud_resource_manager_control_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_control_policy_attachment.html.markdown) |
| resource | `alicloud_resource_manager_delegated_administrator` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_delegated_administrator.html.markdown) |
| resource | `alicloud_resource_manager_delivery_channel` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_delivery_channel.html.markdown) |
| resource | `alicloud_resource_manager_folder` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_folder.html.markdown) |
| resource | `alicloud_resource_manager_handshake` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_handshake.html.markdown) |
| resource | `alicloud_resource_manager_message_contact` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_message_contact.html.markdown) |
| resource | `alicloud_resource_manager_multi_account_delivery_channel` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_multi_account_delivery_channel.html.markdown) |
| resource | `alicloud_resource_manager_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_policy.html.markdown) |
| resource | `alicloud_resource_manager_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_policy_attachment.html.markdown) |
| resource | `alicloud_resource_manager_policy_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_policy_version.html.markdown) |
| resource | `alicloud_resource_manager_resource_directory` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_resource_directory.html.markdown) |
| resource | `alicloud_resource_manager_resource_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_resource_group.html.markdown) |
| resource | `alicloud_resource_manager_resource_share` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_resource_share.html.markdown) |
| resource | `alicloud_resource_manager_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_role.html.markdown) |
| resource | `alicloud_resource_manager_saved_query` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_saved_query.html.markdown) |
| resource | `alicloud_resource_manager_service_linked_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_service_linked_role.html.markdown) |
| resource | `alicloud_resource_manager_shared_resource` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_shared_resource.html.markdown) |
| resource | `alicloud_resource_manager_shared_target` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_shared_target.html.markdown) |

## RocketMQ

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_rocketmq_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_account.html.markdown) |
| resource | `alicloud_rocketmq_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_acl.html.markdown) |
| resource | `alicloud_rocketmq_consumer_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_consumer_group.html.markdown) |
| resource | `alicloud_rocketmq_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_instance.html.markdown) |
| resource | `alicloud_rocketmq_topic` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_topic.html.markdown) |

## RocketMQ (Ons)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ons_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ons_groups.html.markdown) |
| data source | `alicloud_ons_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ons_instances.html.markdown) |
| data source | `alicloud_ons_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ons_service.html.markdown) |
| data source | `alicloud_ons_topics` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ons_topics.html.markdown) |
| resource | `alicloud_ons_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ons_group.html.markdown) |
| resource | `alicloud_ons_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ons_instance.html.markdown) |
| resource | `alicloud_ons_topic` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ons_topic.html.markdown) |

## SCDN

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_scdn_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/scdn_domains.html.markdown) |
| resource | `alicloud_scdn_domain` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/scdn_domain.html.markdown) |
| resource | `alicloud_scdn_domain_config` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/scdn_domain_config.html.markdown) |

## Schedulerx

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_schedulerx_namespaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/schedulerx_namespaces.html.markdown) |
| resource | `alicloud_schedulerx_app_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/schedulerx_app_group.html.markdown) |
| resource | `alicloud_schedulerx_job` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/schedulerx_job.html.markdown) |
| resource | `alicloud_schedulerx_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/schedulerx_namespace.html.markdown) |

## Security Center

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_security_center_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/security_center_groups.html.markdown) |
| resource | `alicloud_security_center_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_center_group.html.markdown) |
| resource | `alicloud_security_center_service_linked_role` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_center_service_linked_role.html.markdown) |

## SelectDB

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_selectdb_db_clusters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/selectdb_db_clusters.html.markdown) |
| data source | `alicloud_selectdb_db_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/selectdb_db_instances.html.markdown) |
| resource | `alicloud_selectdb_db_cluster` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/selectdb_db_cluster.html.markdown) |
| resource | `alicloud_selectdb_db_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/selectdb_db_instance.html.markdown) |

## Serverless App Engine (SAE)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_sae_application_scaling_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_application_scaling_rules.html.markdown) |
| data source | `alicloud_sae_applications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_applications.html.markdown) |
| data source | `alicloud_sae_config_maps` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_config_maps.html.markdown) |
| data source | `alicloud_sae_grey_tag_routes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_grey_tag_routes.html.markdown) |
| data source | `alicloud_sae_ingresses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_ingresses.html.markdown) |
| data source | `alicloud_sae_instance_specifications` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_instance_specifications.html.markdown) |
| data source | `alicloud_sae_namespaces` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_namespaces.html.markdown) |
| data source | `alicloud_sae_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sae_service.html.markdown) |
| resource | `alicloud_sae_application` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_application.html.markdown) |
| resource | `alicloud_sae_application_scaling_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_application_scaling_rule.html.markdown) |
| resource | `alicloud_sae_config_map` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_config_map.html.markdown) |
| resource | `alicloud_sae_grey_tag_route` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_grey_tag_route.html.markdown) |
| resource | `alicloud_sae_ingress` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_ingress.html.markdown) |
| resource | `alicloud_sae_load_balancer_internet` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_load_balancer_internet.html.markdown) |
| resource | `alicloud_sae_load_balancer_intranet` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_load_balancer_intranet.html.markdown) |
| resource | `alicloud_sae_namespace` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_namespace.html.markdown) |

## Serverless Workflow (FnF)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_fnf_executions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fnf_executions.html.markdown) |
| data source | `alicloud_fnf_flows` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fnf_flows.html.markdown) |
| data source | `alicloud_fnf_schedules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fnf_schedules.html.markdown) |
| data source | `alicloud_fnf_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/fnf_service.html.markdown) |
| resource | `alicloud_fnf_execution` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fnf_execution.html.markdown) |
| resource | `alicloud_fnf_flow` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fnf_flow.html.markdown) |
| resource | `alicloud_fnf_schedule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fnf_schedule.html.markdown) |

## Service Catalog

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_service_catalog_end_user_products` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_catalog_end_user_products.html.markdown) |
| data source | `alicloud_service_catalog_launch_options` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_catalog_launch_options.html.markdown) |
| data source | `alicloud_service_catalog_portfolios` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_catalog_portfolios.html.markdown) |
| data source | `alicloud_service_catalog_product_as_end_users` | ⚠️ 弃用 → `alicloud_service_catalog_end_user_products` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_catalog_product_as_end_users.html.markdown) |
| data source | `alicloud_service_catalog_product_versions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_catalog_product_versions.html.markdown) |
| data source | `alicloud_service_catalog_provisioned_products` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_catalog_provisioned_products.html.markdown) |
| resource | `alicloud_service_catalog_portfolio` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_portfolio.html.markdown) |
| resource | `alicloud_service_catalog_principal_portfolio_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_principal_portfolio_association.html.markdown) |
| resource | `alicloud_service_catalog_product` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_product.html.markdown) |
| resource | `alicloud_service_catalog_product_portfolio_association` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_product_portfolio_association.html.markdown) |
| resource | `alicloud_service_catalog_product_version` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_product_version.html.markdown) |
| resource | `alicloud_service_catalog_provisioned_product` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_provisioned_product.html.markdown) |

## Service Mesh

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_service_mesh_extension_providers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_mesh_extension_providers.html.markdown) |
| data source | `alicloud_service_mesh_service_meshes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_mesh_service_meshes.html.markdown) |
| data source | `alicloud_service_mesh_versions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/service_mesh_versions.html.markdown) |
| resource | `alicloud_service_mesh_extension_provider` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_mesh_extension_provider.html.markdown) |
| resource | `alicloud_service_mesh_service_mesh` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_mesh_service_mesh.html.markdown) |
| resource | `alicloud_service_mesh_user_permission` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_mesh_user_permission.html.markdown) |

## Short Message Service (SMS)

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_sms_short_url` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sms_short_url.html.markdown) |

## Simple Application Server

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_simple_application_server_custom_images` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/simple_application_server_custom_images.html.markdown) |
| data source | `alicloud_simple_application_server_disks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/simple_application_server_disks.html.markdown) |
| data source | `alicloud_simple_application_server_firewall_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/simple_application_server_firewall_rules.html.markdown) |
| data source | `alicloud_simple_application_server_images` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/simple_application_server_images.html.markdown) |
| data source | `alicloud_simple_application_server_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/simple_application_server_instances.html.markdown) |
| data source | `alicloud_simple_application_server_plans` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/simple_application_server_plans.html.markdown) |
| data source | `alicloud_simple_application_server_snapshots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/simple_application_server_snapshots.html.markdown) |
| resource | `alicloud_simple_application_server_custom_image` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_custom_image.html.markdown) |
| resource | `alicloud_simple_application_server_disk` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_disk.html.markdown) |
| resource | `alicloud_simple_application_server_firewall_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_firewall_rule.html.markdown) |
| resource | `alicloud_simple_application_server_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_instance.html.markdown) |
| resource | `alicloud_simple_application_server_snapshot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_snapshot.html.markdown) |

## Smart Access Gateway (Smartag)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_cloud_connect_networks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/cloud_connect_networks.html.markdown) |
| data source | `alicloud_sag_acls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/sag_acls.html.markdown) |
| data source | `alicloud_smartag_flow_logs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/smartag_flow_logs.html.markdown) |
| resource | `alicloud_cloud_connect_network` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_connect_network.html.markdown) |
| resource | `alicloud_cloud_connect_network_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_connect_network_attachment.html.markdown) |
| resource | `alicloud_cloud_connect_network_grant` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_connect_network_grant.html.markdown) |
| resource | `alicloud_sag_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_acl.html.markdown) |
| resource | `alicloud_sag_acl_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_acl_rule.html.markdown) |
| resource | `alicloud_sag_client_user` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_client_user.html.markdown) |
| resource | `alicloud_sag_dnat_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_dnat_entry.html.markdown) |
| resource | `alicloud_sag_qos` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_qos.html.markdown) |
| resource | `alicloud_sag_qos_car` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_qos_car.html.markdown) |
| resource | `alicloud_sag_qos_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_qos_policy.html.markdown) |
| resource | `alicloud_sag_snat_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_snat_entry.html.markdown) |
| resource | `alicloud_smartag_flow_log` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/smartag_flow_log.html.markdown) |

## Star Rocks

| type | name | status | doc |
| --- | --- | --- | --- |
| resource | `alicloud_star_rocks_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/star_rocks_instance.html.markdown) |
| resource | `alicloud_star_rocks_node_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/star_rocks_node_group.html.markdown) |

## TAG

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_tag_meta_tags` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/tag_meta_tags.html.markdown) |
| resource | `alicloud_tag_associated_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_associated_rule.html.markdown) |
| resource | `alicloud_tag_meta_tag` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_meta_tag.html.markdown) |
| resource | `alicloud_tag_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_policy.html.markdown) |
| resource | `alicloud_tag_policy_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_policy_attachment.html.markdown) |

## Table Store (OTS)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ots_instance_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ots_instance_attachments.html.markdown) |
| data source | `alicloud_ots_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ots_instances.html.markdown) |
| data source | `alicloud_ots_search_index` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ots_search_index.html.markdown) |
| data source | `alicloud_ots_secondary_indexes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ots_secondary_indexes.html.markdown) |
| data source | `alicloud_ots_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ots_service.html.markdown) |
| data source | `alicloud_ots_tables` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ots_tables.html.markdown) |
| data source | `alicloud_ots_tunnels` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ots_tunnels.html.markdown) |
| resource | `alicloud_ots_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_instance.html.markdown) |
| resource | `alicloud_ots_instance_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_instance_attachment.html.markdown) |
| resource | `alicloud_ots_search_index` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_search_index.html.markdown) |
| resource | `alicloud_ots_secondary_index` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_secondary_index.html.markdown) |
| resource | `alicloud_ots_table` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_table.html.markdown) |
| resource | `alicloud_ots_tunnel` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_tunnel.html.markdown) |

## Tair (Redis OSS-Compatible) And Memcache (KVStore)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_kvstore_accounts` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kvstore_accounts.html.markdown) |
| data source | `alicloud_kvstore_connections` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kvstore_connections.html.markdown) |
| data source | `alicloud_kvstore_instance_classes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kvstore_instance_classes.html.markdown) |
| data source | `alicloud_kvstore_instance_engines` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kvstore_instance_engines.html.markdown) |
| data source | `alicloud_kvstore_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kvstore_instances.html.markdown) |
| data source | `alicloud_kvstore_permission` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kvstore_permission.html.markdown) |
| data source | `alicloud_kvstore_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/kvstore_zones.html.markdown) |
| resource | `alicloud_kvstore_account` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_account.html.markdown) |
| resource | `alicloud_kvstore_audit_log_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_audit_log_config.html.markdown) |
| resource | `alicloud_kvstore_backup_policy` | ⚠️ 弃用 → `alicloud_kvstore_instance` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_backup_policy.html.markdown) |
| resource | `alicloud_kvstore_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_connection.html.markdown) |
| resource | `alicloud_kvstore_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_instance.html.markdown) |
| resource | `alicloud_redis_backup` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/redis_backup.html.markdown) |
| resource | `alicloud_redis_tair_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/redis_tair_instance.html.markdown) |

## Threat Detection

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_threat_detection_anti_brute_force_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_anti_brute_force_rules.html.markdown) |
| data source | `alicloud_threat_detection_assets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_assets.html.markdown) |
| data source | `alicloud_threat_detection_backup_policies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_backup_policies.html.markdown) |
| data source | `alicloud_threat_detection_baseline_strategies` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_baseline_strategies.html.markdown) |
| data source | `alicloud_threat_detection_check_item_configs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_check_item_configs.html.markdown) |
| data source | `alicloud_threat_detection_check_structures` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_check_structures.html.markdown) |
| data source | `alicloud_threat_detection_honey_pots` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_honey_pots.html.markdown) |
| data source | `alicloud_threat_detection_honeypot_images` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_honeypot_images.html.markdown) |
| data source | `alicloud_threat_detection_honeypot_nodes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_honeypot_nodes.html.markdown) |
| data source | `alicloud_threat_detection_honeypot_presets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_honeypot_presets.html.markdown) |
| data source | `alicloud_threat_detection_honeypot_probes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_honeypot_probes.html.markdown) |
| data source | `alicloud_threat_detection_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_instances.html.markdown) |
| data source | `alicloud_threat_detection_log_shipper` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_log_shipper.html.markdown) |
| data source | `alicloud_threat_detection_vul_whitelists` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_vul_whitelists.html.markdown) |
| data source | `alicloud_threat_detection_web_lock_configs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/threat_detection_web_lock_configs.html.markdown) |
| resource | `alicloud_threat_detection_anti_brute_force_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_anti_brute_force_rule.html.markdown) |
| resource | `alicloud_threat_detection_asset_bind` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_asset_bind.html.markdown) |
| resource | `alicloud_threat_detection_asset_selection_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_asset_selection_config.html.markdown) |
| resource | `alicloud_threat_detection_attack_path_sensitive_asset_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_attack_path_sensitive_asset_config.html.markdown) |
| resource | `alicloud_threat_detection_backup_policy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_backup_policy.html.markdown) |
| resource | `alicloud_threat_detection_baseline_strategy` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_baseline_strategy.html.markdown) |
| resource | `alicloud_threat_detection_check_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_check_config.html.markdown) |
| resource | `alicloud_threat_detection_client_file_protect` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_client_file_protect.html.markdown) |
| resource | `alicloud_threat_detection_client_user_define_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_client_user_define_rule.html.markdown) |
| resource | `alicloud_threat_detection_cycle_task` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_cycle_task.html.markdown) |
| resource | `alicloud_threat_detection_file_upload_limit` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_file_upload_limit.html.markdown) |
| resource | `alicloud_threat_detection_honey_pot` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honey_pot.html.markdown) |
| resource | `alicloud_threat_detection_honeypot_node` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honeypot_node.html.markdown) |
| resource | `alicloud_threat_detection_honeypot_preset` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honeypot_preset.html.markdown) |
| resource | `alicloud_threat_detection_honeypot_probe` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honeypot_probe.html.markdown) |
| resource | `alicloud_threat_detection_image_event_operation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_image_event_operation.html.markdown) |
| resource | `alicloud_threat_detection_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_instance.html.markdown) |
| resource | `alicloud_threat_detection_log_meta` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_log_meta.html.markdown) |
| resource | `alicloud_threat_detection_malicious_file_whitelist_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_malicious_file_whitelist_config.html.markdown) |
| resource | `alicloud_threat_detection_oss_scan_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_oss_scan_config.html.markdown) |
| resource | `alicloud_threat_detection_sas_trail` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_sas_trail.html.markdown) |
| resource | `alicloud_threat_detection_vul_whitelist` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_vul_whitelist.html.markdown) |
| resource | `alicloud_threat_detection_web_lock_config` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_web_lock_config.html.markdown) |

## Time Series Database (TSDB)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_tsdb_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/tsdb_instances.html.markdown) |
| data source | `alicloud_tsdb_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/tsdb_zones.html.markdown) |
| resource | `alicloud_tsdb_instance` | ⚠️ 弃用 | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tsdb_instance.html.markdown) |

## VPC

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_enhanced_nat_available_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/enhanced_nat_available_zones.html.markdown) |
| data source | `alicloud_havips` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/havips.html.markdown) |
| data source | `alicloud_network_acls` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/network_acls.html.markdown) |
| data source | `alicloud_route_entries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/route_entries.html.markdown) |
| data source | `alicloud_route_tables` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/route_tables.html.markdown) |
| data source | `alicloud_vpc_dhcp_options_sets` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_dhcp_options_sets.html.markdown) |
| data source | `alicloud_vpc_flow_log_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_flow_log_service.html.markdown) |
| data source | `alicloud_vpc_flow_logs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_flow_logs.html.markdown) |
| data source | `alicloud_vpc_ipv4_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipv4_gateways.html.markdown) |
| data source | `alicloud_vpc_ipv6_addresses` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipv6_addresses.html.markdown) |
| data source | `alicloud_vpc_ipv6_egress_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipv6_egress_rules.html.markdown) |
| data source | `alicloud_vpc_ipv6_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipv6_gateways.html.markdown) |
| data source | `alicloud_vpc_ipv6_internet_bandwidths` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipv6_internet_bandwidths.html.markdown) |
| data source | `alicloud_vpc_peer_connections` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_peer_connections.html.markdown) |
| data source | `alicloud_vpc_prefix_lists` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_prefix_lists.html.markdown) |
| data source | `alicloud_vpc_public_ip_address_pool_cidr_blocks` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_public_ip_address_pool_cidr_blocks.html.markdown) |
| data source | `alicloud_vpc_public_ip_address_pools` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_public_ip_address_pools.html.markdown) |
| data source | `alicloud_vpc_traffic_mirror_filter_egress_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_traffic_mirror_filter_egress_rules.html.markdown) |
| data source | `alicloud_vpc_traffic_mirror_filter_ingress_rules` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_traffic_mirror_filter_ingress_rules.html.markdown) |
| data source | `alicloud_vpc_traffic_mirror_filters` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_traffic_mirror_filters.html.markdown) |
| data source | `alicloud_vpc_traffic_mirror_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_traffic_mirror_service.html.markdown) |
| data source | `alicloud_vpc_traffic_mirror_sessions` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_traffic_mirror_sessions.html.markdown) |
| data source | `alicloud_vpcs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpcs.html.markdown) |
| data source | `alicloud_vswitches` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vswitches.html.markdown) |
| resource | `alicloud_cen_instance_grant` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_instance_grant.html.markdown) |
| resource | `alicloud_havip` | ⚠️ 弃用 → `alicloud_vpc_ha_vip` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/havip.html.markdown) |
| resource | `alicloud_havip_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/havip_attachment.html.markdown) |
| resource | `alicloud_network_acl` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_acl.html.markdown) |
| resource | `alicloud_network_acl_attachment` | ⚠️ 弃用 → `alicloud_network_acl` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_acl_attachment.html.markdown) |
| resource | `alicloud_network_acl_entries` | ⚠️ 弃用 → `alicloud_network_acl` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_acl_entries.html.markdown) |
| resource | `alicloud_route_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/route_entry.html.markdown) |
| resource | `alicloud_route_table` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/route_table.html.markdown) |
| resource | `alicloud_route_table_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/route_table_attachment.html.markdown) |
| resource | `alicloud_vpc` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc.html.markdown) |
| resource | `alicloud_vpc_dhcp_options_set` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_dhcp_options_set.html.markdown) |
| resource | `alicloud_vpc_dhcp_options_set_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_dhcp_options_set_attachment.html.markdown) |
| resource | `alicloud_vpc_flow_log` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_flow_log.html.markdown) |
| resource | `alicloud_vpc_gateway_endpoint` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_gateway_endpoint.html.markdown) |
| resource | `alicloud_vpc_gateway_endpoint_route_table_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_gateway_endpoint_route_table_attachment.html.markdown) |
| resource | `alicloud_vpc_gateway_route_table_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_gateway_route_table_attachment.html.markdown) |
| resource | `alicloud_vpc_ha_vip` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ha_vip.html.markdown) |
| resource | `alicloud_vpc_ipv4_cidr_block` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv4_cidr_block.html.markdown) |
| resource | `alicloud_vpc_ipv4_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv4_gateway.html.markdown) |
| resource | `alicloud_vpc_ipv6_address` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_address.html.markdown) |
| resource | `alicloud_vpc_ipv6_egress_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_egress_rule.html.markdown) |
| resource | `alicloud_vpc_ipv6_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_gateway.html.markdown) |
| resource | `alicloud_vpc_ipv6_internet_bandwidth` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_internet_bandwidth.html.markdown) |
| resource | `alicloud_vpc_network_acl_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_network_acl_attachment.html.markdown) |
| resource | `alicloud_vpc_peer_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_peer_connection.html.markdown) |
| resource | `alicloud_vpc_peer_connection_accepter` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_peer_connection_accepter.html.markdown) |
| resource | `alicloud_vpc_prefix_list` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_prefix_list.html.markdown) |
| resource | `alicloud_vpc_public_ip_address_pool` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_public_ip_address_pool.html.markdown) |
| resource | `alicloud_vpc_public_ip_address_pool_cidr_block` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_public_ip_address_pool_cidr_block.html.markdown) |
| resource | `alicloud_vpc_route_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_route_entry.html.markdown) |
| resource | `alicloud_vpc_traffic_mirror_filter` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_filter.html.markdown) |
| resource | `alicloud_vpc_traffic_mirror_filter_egress_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_filter_egress_rule.html.markdown) |
| resource | `alicloud_vpc_traffic_mirror_filter_ingress_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_filter_ingress_rule.html.markdown) |
| resource | `alicloud_vpc_traffic_mirror_session` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_session.html.markdown) |
| resource | `alicloud_vpc_vswitch_cidr_reservation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_vswitch_cidr_reservation.html.markdown) |
| resource | `alicloud_vswitch` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vswitch.html.markdown) |

## VPN Gateway

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_ssl_vpn_client_certs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ssl_vpn_client_certs.html.markdown) |
| data source | `alicloud_ssl_vpn_servers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/ssl_vpn_servers.html.markdown) |
| data source | `alicloud_vpn_connections` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_connections.html.markdown) |
| data source | `alicloud_vpn_customer_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_customer_gateways.html.markdown) |
| data source | `alicloud_vpn_gateway_vco_routes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_gateway_vco_routes.html.markdown) |
| data source | `alicloud_vpn_gateway_vpn_attachments` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_gateway_vpn_attachments.html.markdown) |
| data source | `alicloud_vpn_gateway_zones` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_gateway_zones.html.markdown) |
| data source | `alicloud_vpn_gateways` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_gateways.html.markdown) |
| data source | `alicloud_vpn_ipsec_servers` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_ipsec_servers.html.markdown) |
| data source | `alicloud_vpn_pbr_route_entries` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpn_pbr_route_entries.html.markdown) |
| resource | `alicloud_ssl_vpn_client_cert` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_vpn_client_cert.html.markdown) |
| resource | `alicloud_ssl_vpn_server` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_vpn_server.html.markdown) |
| resource | `alicloud_vpn_connection` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_connection.html.markdown) |
| resource | `alicloud_vpn_customer_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_customer_gateway.html.markdown) |
| resource | `alicloud_vpn_gateway` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_gateway.html.markdown) |
| resource | `alicloud_vpn_gateway_vco_route` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_gateway_vco_route.html.markdown) |
| resource | `alicloud_vpn_gateway_vpn_attachment` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_gateway_vpn_attachment.html.markdown) |
| resource | `alicloud_vpn_ipsec_server` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_ipsec_server.html.markdown) |
| resource | `alicloud_vpn_pbr_route_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_pbr_route_entry.html.markdown) |
| resource | `alicloud_vpn_route_entry` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_route_entry.html.markdown) |

## Video Surveillance System

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_video_surveillance_system_groups` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/video_surveillance_system_groups.html.markdown) |
| data source | `alicloud_vs_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vs_service.html.markdown) |
| resource | `alicloud_video_surveillance_system_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/video_surveillance_system_group.html.markdown) |

## Vpc Ipam

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_vpc_ipam_ipam_pool_allocations` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipam_ipam_pool_allocations.html.markdown) |
| data source | `alicloud_vpc_ipam_ipam_pool_cidrs` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipam_ipam_pool_cidrs.html.markdown) |
| data source | `alicloud_vpc_ipam_ipam_pools` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipam_ipam_pools.html.markdown) |
| data source | `alicloud_vpc_ipam_ipam_scopes` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipam_ipam_scopes.html.markdown) |
| data source | `alicloud_vpc_ipam_ipams` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/vpc_ipam_ipams.html.markdown) |
| resource | `alicloud_vpc_ipam_ipam` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam.html.markdown) |
| resource | `alicloud_vpc_ipam_ipam_pool` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_pool.html.markdown) |
| resource | `alicloud_vpc_ipam_ipam_pool_allocation` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_pool_allocation.html.markdown) |
| resource | `alicloud_vpc_ipam_ipam_pool_cidr` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_pool_cidr.html.markdown) |
| resource | `alicloud_vpc_ipam_ipam_resource_discovery` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_resource_discovery.html.markdown) |
| resource | `alicloud_vpc_ipam_ipam_scope` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_scope.html.markdown) |
| resource | `alicloud_vpc_ipam_service` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_service.html.markdown) |

## Web Application Firewall(WAF)

| type | name | status | doc |
| --- | --- | --- | --- |
| data source | `alicloud_waf_certificates` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/waf_certificates.html.markdown) |
| data source | `alicloud_waf_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/waf_domains.html.markdown) |
| data source | `alicloud_waf_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/waf_instances.html.markdown) |
| data source | `alicloud_wafv3_domains` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/wafv3_domains.html.markdown) |
| data source | `alicloud_wafv3_instances` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/d/wafv3_instances.html.markdown) |
| resource | `alicloud_waf_certificate` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_certificate.html.markdown) |
| resource | `alicloud_waf_domain` | ⚠️ 弃用 → `alicloud_wafv3_domain` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_domain.html.markdown) |
| resource | `alicloud_waf_instance` | ⚠️ 弃用 → `alicloud_wafv3_instance` | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_instance.html.markdown) |
| resource | `alicloud_waf_protection_module` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_protection_module.html.markdown) |
| resource | `alicloud_wafv3_defense_resource_group` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_defense_resource_group.html.markdown) |
| resource | `alicloud_wafv3_defense_rule` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_defense_rule.html.markdown) |
| resource | `alicloud_wafv3_defense_template` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_defense_template.html.markdown) |
| resource | `alicloud_wafv3_domain` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_domain.html.markdown) |
| resource | `alicloud_wafv3_instance` |  | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_instance.html.markdown) |
