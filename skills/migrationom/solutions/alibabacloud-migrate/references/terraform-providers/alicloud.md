# ALICLOUD Provider 产品线和资源清单

**Provider 版本**: 1.274.0
**评估时间**: 2026-03-24T09:48:02.635767

## 📊 总体统计

- **产品线数量**: 145
- **资源总数**: 1114
- **已弃用资源**: 75

## 📦 产品线分类统计

| 产品线分类 | 产品数 | 占比 |
|------------|--------|------|
| 安全 | 14 | 9.7% |
| 网络 | 23 | 15.9% |
| 企业IT治理 | 15 | 10.3% |
| 存储 | 7 | 4.8% |
| 数据库 | 19 | 13.1% |
| 云通信 | 5 | 3.4% |
| 视频云 | 2 | 1.4% |
| 云原生 | 13 | 9.0% |
| 弹性计算 | 7 | 4.8% |
| CDN及边缘云 | 3 | 2.1% |
| 计算平台和AI | 17 | 11.7% |
| 其它 | 20 | 13.8% |

## 📋 详细产品线和资源列表

## 安全 (14 个产品)

### Threat Detection

**产品代码**: `threat_detection`
**产品线分类**: 安全
**资源数**: 23

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_threat_detection_anti_brute_force_rule` | ✅ | Provides a Threat Detection Anti Brute Force Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_anti_brute_force_rule.html.markdown) |
| `alicloud_threat_detection_asset_bind` | ✅ | Provides a Threat Detection Asset Bind resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_asset_bind.html.markdown) |
| `alicloud_threat_detection_asset_selection_config` | ✅ | Provides a Threat Detection Asset Selection Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_asset_selection_config.html.markdown) |
| `alicloud_threat_detection_attack_path_sensitive_asset_config` | ✅ | Provides a Threat Detection Attack Path Sensitive Asset Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_attack_path_sensitive_asset_config.html.markdown) |
| `alicloud_threat_detection_backup_policy` | ✅ | Provides a Threat Detection Backup Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_backup_policy.html.markdown) |
| `alicloud_threat_detection_baseline_strategy` | ✅ | Provides a Threat Detection Baseline Strategy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_baseline_strategy.html.markdown) |
| `alicloud_threat_detection_check_config` | ✅ | Provides a Threat Detection Check Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_check_config.html.markdown) |
| `alicloud_threat_detection_client_file_protect` | ✅ | Provides a Threat Detection Client File Protect resource. Client core file pr... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_client_file_protect.html.markdown) |
| `alicloud_threat_detection_client_user_define_rule` | ✅ | Provides a Threat Detection Client User Define Rule resource. Malicious Behav... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_client_user_define_rule.html.markdown) |
| `alicloud_threat_detection_cycle_task` | ✅ | Provides a Threat Detection Cycle Task resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_cycle_task.html.markdown) |
| `alicloud_threat_detection_file_upload_limit` | ✅ | Provides a Threat Detection File Upload Limit resource. User-defined file upl... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_file_upload_limit.html.markdown) |
| `alicloud_threat_detection_honey_pot` | ✅ | Provides a Threat Detection Honey Pot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honey_pot.html.markdown) |
| `alicloud_threat_detection_honeypot_node` | ✅ | Provides a Threat Detection Honeypot Node resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honeypot_node.html.markdown) |
| `alicloud_threat_detection_honeypot_preset` | ✅ | Provides a Threat Detection Honeypot Preset resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honeypot_preset.html.markdown) |
| `alicloud_threat_detection_honeypot_probe` | ✅ | Provides a Threat Detection Honeypot Probe resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_honeypot_probe.html.markdown) |
| `alicloud_threat_detection_image_event_operation` | ✅ | Provides a Threat Detection Image Event Operation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_image_event_operation.html.markdown) |
| `alicloud_threat_detection_instance` | ✅ | Provides a Threat Detection Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_instance.html.markdown) |
| `alicloud_threat_detection_log_meta` | ✅ | Provides a Threat Detection Log Meta resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_log_meta.html.markdown) |
| `alicloud_threat_detection_malicious_file_whitelist_config` | ✅ | Provides a Threat Detection Malicious File Whitelist Config resource. malicio... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_malicious_file_whitelist_config.html.markdown) |
| `alicloud_threat_detection_oss_scan_config` | ✅ | Provides a Threat Detection Oss Scan Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_oss_scan_config.html.markdown) |
| `alicloud_threat_detection_sas_trail` | ✅ | Provides a Threat Detection Sas Trail resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_sas_trail.html.markdown) |
| `alicloud_threat_detection_vul_whitelist` | ✅ | Provides a Threat Detection Vul Whitelist resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_vul_whitelist.html.markdown) |
| `alicloud_threat_detection_web_lock_config` | ✅ | Provides a Threat Detection Web Lock Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/threat_detection_web_lock_config.html.markdown) |

---

### Cloud Firewall

**产品代码**: `cloud_firewall`
**产品线分类**: 安全
**资源数**: 20 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloud_firewall_address_book` | ✅ | Provides a Cloud Firewall Address Book resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_address_book.html.markdown) |
| `alicloud_cloud_firewall_ai_traffic_analysis_status` | ✅ | Provides a Cloud Firewall Ai Traffic Analysis Status resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_ai_traffic_analysis_status.html.markdown) |
| `alicloud_cloud_firewall_control_policy` | ✅ | Provides a Cloud Firewall Control Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_control_policy.html.markdown) |
| `alicloud_cloud_firewall_control_policy_order` | ✅ | Provides a Cloud Firewall Control Policy Order resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_control_policy_order.html.markdown) |
| `alicloud_cloud_firewall_instance` | ⚠️ 弃用 → `alicloud_cloud_firewall_instance_v2` | Provides a Cloud Firewall Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_instance.html.markdown) |
| `alicloud_cloud_firewall_instance_member` | ✅ | Provides a Cloud Firewall Instance Member resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_instance_member.html.markdown) |
| `alicloud_cloud_firewall_instance_v2` | ✅ | Provides a Cloud Firewall Instance V2 resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_instance_v2.html.markdown) |
| `alicloud_cloud_firewall_ips_config` | ✅ | Provides a Cloud Firewall IPS Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_ips_config.html.markdown) |
| `alicloud_cloud_firewall_nat_firewall` | ✅ | Provides a Cloud Firewall Nat Firewall resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_nat_firewall.html.markdown) |
| `alicloud_cloud_firewall_nat_firewall_control_policy` | ✅ | Provides a Cloud Firewall Nat Firewall Control Policy resource. Nat firewall ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_nat_firewall_control_policy.html.markdown) |
| `alicloud_cloud_firewall_policy_advanced_config` | ✅ | Provides a Cloud Firewall Policy Advanced Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_policy_advanced_config.html.markdown) |
| `alicloud_cloud_firewall_private_dns` | ✅ | Provides a Cloud Firewall Private Dns resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_private_dns.html.markdown) |
| `alicloud_cloud_firewall_threat_intelligence_switch` | ✅ | Provides a Cloud Firewall Threat Intelligence Switch resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_threat_intelligence_switch.html.markdown) |
| `alicloud_cloud_firewall_user_alarm_config` | ✅ | Provides a Cloud Firewall User Alarm Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_user_alarm_config.html.markdown) |
| `alicloud_cloud_firewall_vpc_cen_tr_firewall` | ✅ | Provides a Cloud Firewall Vpc Cen Tr Firewall resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_cen_tr_firewall.html.markdown) |
| `alicloud_cloud_firewall_vpc_firewall` | ✅ | Provides a Cloud Firewall Vpc Firewall resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall.html.markdown) |
| `alicloud_cloud_firewall_vpc_firewall_acl_engine_mode` | ✅ | Provides a Cloud Firewall Vpc Firewall Acl Engine Mode resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_acl_engine_mode.html.markdown) |
| `alicloud_cloud_firewall_vpc_firewall_cen` | ✅ | Provides a Cloud Firewall Vpc Firewall Cen resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_cen.html.markdown) |
| `alicloud_cloud_firewall_vpc_firewall_control_policy` | ✅ | Provides a Cloud Firewall Vpc Firewall Control Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_control_policy.html.markdown) |
| `alicloud_cloud_firewall_vpc_firewall_ips_config` | ✅ | Provides a Cloud Firewall Vpc Firewall Ips Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_firewall_vpc_firewall_ips_config.html.markdown) |

---

### Ram

**产品代码**: `ram`
**产品线分类**: 安全
**资源数**: 16 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ram_access_key` | ✅ | Provides a RAM Access Key resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_access_key.html.markdown) |
| `alicloud_ram_account_alias` | ✅ | Provides a RAM Account Alias resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_account_alias.html.markdown) |
| `alicloud_ram_account_password_policy` | ✅ | Provides a RAM password policy configuration for entire account. Only one res... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_account_password_policy.html.markdown) |
| `alicloud_ram_group` | ✅ | Provides a RAM Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_group.html.markdown) |
| `alicloud_ram_group_membership` | ⚠️ 弃用 → `alicloud_ram_user_group_attachment` | Provides a RAM Group membership resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_group_membership.html.markdown) |
| `alicloud_ram_group_policy_attachment` | ✅ | Provides a RAM Group Policy Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_group_policy_attachment.html.markdown) |
| `alicloud_ram_login_profile` | ✅ | Provides a RAM Login Profile resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_login_profile.html.markdown) |
| `alicloud_ram_password_policy` | ✅ | Provides a RAM Password Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_password_policy.html.markdown) |
| `alicloud_ram_policy` | ✅ | Provides a RAM Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_policy.html.markdown) |
| `alicloud_ram_role` | ✅ | Provides a RAM Role resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_role.html.markdown) |
| `alicloud_ram_role_policy_attachment` | ✅ | Provides a RAM Role Policy Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_role_policy_attachment.html.markdown) |
| `alicloud_ram_saml_provider` | ✅ | Provides a RAM Saml Provider resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_saml_provider.html.markdown) |
| `alicloud_ram_security_preference` | ✅ | Provides a RAM Security Preference resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_security_preference.html.markdown) |
| `alicloud_ram_user` | ✅ | Provides a RAM User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_user.html.markdown) |
| `alicloud_ram_user_group_attachment` | ✅ | Provides a RAM User Group Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_user_group_attachment.html.markdown) |
| `alicloud_ram_user_policy_attachment` | ✅ | Provides a RAM User Policy Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_user_policy_attachment.html.markdown) |

---

### Bastion Host

**产品代码**: `bastion_host`
**产品线分类**: 安全
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_bastionhost_host` | ✅ | Provides a Bastion Host Host resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host.html.markdown) |
| `alicloud_bastionhost_host_account` | ✅ | Provides a Bastion Host Host Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account.html.markdown) |
| `alicloud_bastionhost_host_account_share_key_attachment` | ✅ | Provides a Bastion Host Account Share Key Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account_share_key_attachment.html.markdown) |
| `alicloud_bastionhost_host_account_user_attachment` | ✅ | Provides a Bastion Host Host Account Attachment resource to add list host acc... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account_user_attachment.html.markdown) |
| `alicloud_bastionhost_host_account_user_group_attachment` | ✅ | Provides a Bastion Host Host Account Attachment resource to add list host acc... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_account_user_group_attachment.html.markdown) |
| `alicloud_bastionhost_host_attachment` | ✅ | Provides a Bastion Host Host Attachment resource to add host into one host gr... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_attachment.html.markdown) |
| `alicloud_bastionhost_host_group` | ✅ | Provides a Bastion Host Host Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_group.html.markdown) |
| `alicloud_bastionhost_host_group_account_user_attachment` | ✅ | Provides a Bastion Host Host Account Attachment resource to add list host acc... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_group_account_user_attachment.html.markdown) |
| `alicloud_bastionhost_host_group_account_user_group_attachment` | ✅ | Provides a Bastion Host Host Account Attachment resource to add list host acc... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_group_account_user_group_attachment.html.markdown) |
| `alicloud_bastionhost_host_share_key` | ✅ | Provides a Bastion Host Share Key resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_host_share_key.html.markdown) |
| `alicloud_bastionhost_instance` | ✅ | Cloud Bastion Host instance resource ("Yundun_bastionhost" is the short term ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_instance.html.markdown) |
| `alicloud_bastionhost_user` | ✅ | Provides a Bastion Host User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_user.html.markdown) |
| `alicloud_bastionhost_user_attachment` | ✅ | Provides a Bastion Host User Attachment resource to add user to one user group. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_user_attachment.html.markdown) |
| `alicloud_bastionhost_user_group` | ✅ | Provides a Bastion Host User Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bastionhost_user_group.html.markdown) |

---

### Kms

**产品代码**: `kms`
**产品线分类**: 安全
**资源数**: 11

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_kms_alias` | ✅ | Create an alias for the master key (CMK). | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_alias.html.markdown) |
| `alicloud_kms_application_access_point` | ✅ | Provides a KMS Application Access Point resource. An application access point... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_application_access_point.html.markdown) |
| `alicloud_kms_ciphertext` | ✅ | Encrypt a given plaintext with KMS. The produced ciphertext stays stable acro... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_ciphertext.html.markdown) |
| `alicloud_kms_client_key` | ✅ | Provides a KMS Client Key resource. Client key (of Application Access Point). | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_client_key.html.markdown) |
| `alicloud_kms_instance` | ✅ | Provides a KMS Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_instance.html.markdown) |
| `alicloud_kms_key` | ✅ | Provides a KMS Key resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_key.html.markdown) |
| `alicloud_kms_key_version` | ✅ | Provides a Alikms Key Version resource. For information about Alikms Key Vers... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_key_version.html.markdown) |
| `alicloud_kms_network_rule` | ✅ | Provides a KMS Network Rule resource. Network rules that can be bound by Appl... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_network_rule.html.markdown) |
| `alicloud_kms_policy` | ✅ | Provides a KMS Policy resource. Permission policies which can be bound to the... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_policy.html.markdown) |
| `alicloud_kms_secret` | ✅ | Provides a KMS Secret resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_secret.html.markdown) |
| `alicloud_kms_value_added_service` | ✅ | Provides a KMS Value Added Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kms_value_added_service.html.markdown) |

---

### Waf

**产品代码**: `waf`
**产品线分类**: 安全
**资源数**: 9 | **已弃用**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_waf_certificate` | ✅ | Provides a WAF Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_certificate.html.markdown) |
| `alicloud_waf_domain` | ⚠️ 弃用 → `alicloud_wafv3_domain` | Provides a WAF Domain resource to create domain in the Web Application Firewall. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_domain.html.markdown) |
| `alicloud_waf_instance` | ⚠️ 弃用 → `alicloud_wafv3_instance` | Provides a WAF Instance resource to create instance in the Web Application Fi... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_instance.html.markdown) |
| `alicloud_waf_protection_module` | ✅ | Provides a Web Application Firewall(WAF) Protection Module resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/waf_protection_module.html.markdown) |
| `alicloud_wafv3_defense_resource_group` | ✅ | Provides a WAFV3 Defense Resource Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_defense_resource_group.html.markdown) |
| `alicloud_wafv3_defense_rule` | ✅ | Provides a WAFV3 Defense Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_defense_rule.html.markdown) |
| `alicloud_wafv3_defense_template` | ✅ | Provides a WAFV3 Defense Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_defense_template.html.markdown) |
| `alicloud_wafv3_domain` | ✅ | Provides a WAFV3 Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_domain.html.markdown) |
| `alicloud_wafv3_instance` | ✅ | Provides a Wafv3 Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/wafv3_instance.html.markdown) |

---

### Aligreen

**产品代码**: `aligreen`
**产品线分类**: 安全
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_aligreen_audit_callback` | ✅ | Provides a Aligreen Audit Callback resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_audit_callback.html.markdown) |
| `alicloud_aligreen_biz_type` | ✅ | Provides a Aligreen Biz Type resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_biz_type.html.markdown) |
| `alicloud_aligreen_callback` | ✅ | Provides a Aligreen Callback resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_callback.html.markdown) |
| `alicloud_aligreen_image_lib` | ✅ | Provides a Aligreen Image Lib resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_image_lib.html.markdown) |
| `alicloud_aligreen_keyword_lib` | ✅ | Provides a Aligreen Keyword Lib resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_keyword_lib.html.markdown) |
| `alicloud_aligreen_oss_stock_task` | ✅ | Provides a Aligreen Oss Stock Task resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/aligreen_oss_stock_task.html.markdown) |

---

### Ddoscoo

**产品代码**: `ddoscoo`
**产品线分类**: 安全
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ddoscoo_domain_precise_access_rule` | ✅ | Provides a DdosCoo Domain Precise Access Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_domain_precise_access_rule.html.markdown) |
| `alicloud_ddoscoo_domain_resource` | ✅ | Provides a Ddos Coo Domain Resource resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_domain_resource.html.markdown) |
| `alicloud_ddoscoo_instance` | ✅ | Provides a BGP-line Anti-DDoS Pro(DdosCoo) Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_instance.html.markdown) |
| `alicloud_ddoscoo_port` | ✅ | Provides a Ddos Coo Port resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_port.html.markdown) |
| `alicloud_ddoscoo_scheduler_rule` | ✅ | Provides a DdosCoo Scheduler Rule resource. For information about DdosCoo Sch... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_scheduler_rule.html.markdown) |
| `alicloud_ddoscoo_web_cc_rule` | ✅ | Provides a DdosCoo Web Cc Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddoscoo_web_cc_rule.html.markdown) |

---

### Original Ssl Certificate

**产品代码**: `original_ssl_certificate`
**产品线分类**: 安全
**资源数**: 4 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cas_certificate` | ⚠️ 弃用 → `alicloud_ssl_certificates_service_certificate` | Provides a CAS Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cas_certificate.html.markdown) |
| `alicloud_ssl_certificates_service_certificate` | ✅ | Provides a SSL Certificates Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_certificates_service_certificate.html.markdown) |
| `alicloud_ssl_certificates_service_pca_cert` | ✅ | Provides a SSL Certificates Pca Cert resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_certificates_service_pca_cert.html.markdown) |
| `alicloud_ssl_certificates_service_pca_certificate` | ✅ | Provides a SSL Certificates Pca Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_certificates_service_pca_certificate.html.markdown) |

---

### Sddp

**产品代码**: `sddp`
**产品线分类**: 安全
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_sddp_config` | ✅ | Provides a Data Security Center Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_config.html.markdown) |
| `alicloud_sddp_data_limit` | ✅ | Provides a Data Security Center Data Limit resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_data_limit.html.markdown) |
| `alicloud_sddp_instance` | ✅ | Provides a Data Security Center Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_instance.html.markdown) |
| `alicloud_sddp_rule` | ✅ | Provides a Data Security Center Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sddp_rule.html.markdown) |

---

### Ddosbgp

**产品代码**: `ddosbgp`
**产品线分类**: 安全
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ddos_bgp_policy` | ✅ | Provides a Ddos Bgp Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddos_bgp_policy.html.markdown) |
| `alicloud_ddosbgp_instance` | ✅ | Provides a Anti-DDoS Pro (DdosBgp) Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddosbgp_instance.html.markdown) |
| `alicloud_ddosbgp_ip` | ✅ | Provides a Anti-DDoS Pro (DdosBgp) Ip resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddosbgp_ip.html.markdown) |

---

### Ddos Basic

**产品代码**: `ddos_basic`
**产品线分类**: 安全
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ddos_basic_defense_threshold` | ✅ | Provides a Ddos Basic defense threshold resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddos_basic_defense_threshold.html.markdown) |
| `alicloud_ddos_basic_threshold` | ✅ | Provides a Ddos Basic Threshold resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ddos_basic_threshold.html.markdown) |

---

### Security Center

**产品代码**: `security_center`
**产品线分类**: 安全
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_security_center_group` | ✅ | Provides a Security Center Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_center_group.html.markdown) |
| `alicloud_security_center_service_linked_role` | ✅ | Using this resource can create SecurityCenter service-linked role : `AliyunSe... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_center_service_linked_role.html.markdown) |

---

### Cloudauth

**产品代码**: `cloudauth`
**产品线分类**: 安全
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloudauth_face_config` | ✅ | Provides a Cloudauth Face Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloudauth_face_config.html.markdown) |

---

## 网络 (23 个产品)

### Virtual Private Cloud

**产品代码**: `vpc`
**产品线分类**: 网络
**资源数**: 36 | **已弃用**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cen_instance_grant` | ✅ | Provides a CEN child instance grant resource, which allow you to authorize a ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_instance_grant.html.markdown) |
| `alicloud_havip` | ⚠️ 弃用 → `alicloud_vpc_ha_vip` | Provides a HaVip resource, see [What is HAVIP](https://www.alibabacloud.com/h... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/havip.html.markdown) |
| `alicloud_havip_attachment` | ✅ | Provides a VPC Ha Vip Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/havip_attachment.html.markdown) |
| `alicloud_network_acl` | ✅ | Provides a VPC Network Acl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_acl.html.markdown) |
| `alicloud_network_acl_attachment` | ⚠️ 弃用 → `alicloud_network_acl` | Provides a network acl attachment resource to associate network acls to vswit... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_acl_attachment.html.markdown) |
| `alicloud_network_acl_entries` | ⚠️ 弃用 → `alicloud_network_acl` | Provides a network acl entries resource to create ingress and egress entries. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_acl_entries.html.markdown) |
| `alicloud_route_entry` | ✅ | Provides a Route Entry resource. A Route Entry represents a route item of one... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/route_entry.html.markdown) |
| `alicloud_route_table` | ✅ | Provides a VPC Route Table resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/route_table.html.markdown) |
| `alicloud_route_table_attachment` | ✅ | Provides a VPC Route Table Attachment resource. Routing table associated reso... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/route_table_attachment.html.markdown) |
| `alicloud_vpc` | ✅ | Provides a VPC VPC resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc.html.markdown) |
| `alicloud_vpc_dhcp_options_set` | ✅ | Provides a VPC Dhcp Options Set resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_dhcp_options_set.html.markdown) |
| `alicloud_vpc_dhcp_options_set_attachment` | ✅ | Provides a VPC Dhcp Options Set Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_dhcp_options_set_attachment.html.markdown) |
| `alicloud_vpc_flow_log` | ✅ | Provides a VPC Flow Log resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_flow_log.html.markdown) |
| `alicloud_vpc_gateway_endpoint` | ✅ | Provides a VPC Gateway Endpoint resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_gateway_endpoint.html.markdown) |
| `alicloud_vpc_gateway_endpoint_route_table_attachment` | ✅ | Provides a VPC Gateway Endpoint Route Table Attachment resource. VPC gateway ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_gateway_endpoint_route_table_attachment.html.markdown) |
| `alicloud_vpc_gateway_route_table_attachment` | ✅ | Provides a VPC Gateway Route Table Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_gateway_route_table_attachment.html.markdown) |
| `alicloud_vpc_ha_vip` | ✅ | Provides a VPC Ha Vip resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ha_vip.html.markdown) |
| `alicloud_vpc_ipv4_cidr_block` | ✅ | Provides a VPC Ipv4 Cidr Block resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv4_cidr_block.html.markdown) |
| `alicloud_vpc_ipv4_gateway` | ✅ | Provides a Vpc Ipv4 Gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv4_gateway.html.markdown) |
| `alicloud_vpc_ipv6_address` | ✅ | Provides a VPC Ipv6 Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_address.html.markdown) |
| `alicloud_vpc_ipv6_egress_rule` | ✅ | Provides a VPC Ipv6 Egress Rule resource. IPv6 address addition only active e... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_egress_rule.html.markdown) |
| `alicloud_vpc_ipv6_gateway` | ✅ | Provides a Vpc Ipv6 Gateway resource. Gateway Based on Internet Protocol Vers... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_gateway.html.markdown) |
| `alicloud_vpc_ipv6_internet_bandwidth` | ✅ | Provides a VPC Ipv6 Internet Bandwidth resource. Public network bandwidth of ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipv6_internet_bandwidth.html.markdown) |
| `alicloud_vpc_network_acl_attachment` | ✅ | Provides a VPC Network Acl Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_network_acl_attachment.html.markdown) |
| `alicloud_vpc_peer_connection` | ✅ | Provides a Vpc Peer Peer Connection resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_peer_connection.html.markdown) |
| `alicloud_vpc_peer_connection_accepter` | ✅ | Provides a Vpc Peer Peer Connection Accepter resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_peer_connection_accepter.html.markdown) |
| `alicloud_vpc_prefix_list` | ✅ | Provides a Vpc Prefix List resource. This resource is used to create a prefix... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_prefix_list.html.markdown) |
| `alicloud_vpc_public_ip_address_pool` | ✅ | Provides a VPC Public Ip Address Pool resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_public_ip_address_pool.html.markdown) |
| `alicloud_vpc_public_ip_address_pool_cidr_block` | ✅ | Provides a VPC Public Ip Address Pool Cidr Block resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_public_ip_address_pool_cidr_block.html.markdown) |
| `alicloud_vpc_route_entry` | ✅ | Provides a VPC Route Entry resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_route_entry.html.markdown) |
| `alicloud_vpc_traffic_mirror_filter` | ✅ | Provides a VPC Traffic Mirror Filter resource. Traffic mirror filter criteria. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_filter.html.markdown) |
| `alicloud_vpc_traffic_mirror_filter_egress_rule` | ✅ | Provides a VPC Traffic Mirror Filter Egress Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_filter_egress_rule.html.markdown) |
| `alicloud_vpc_traffic_mirror_filter_ingress_rule` | ✅ | Provides a VPC Traffic Mirror Filter Ingress Rule resource. Traffic mirror en... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_filter_ingress_rule.html.markdown) |
| `alicloud_vpc_traffic_mirror_session` | ✅ | Provides a VPC Traffic Mirror Session resource. Traffic mirroring session. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_traffic_mirror_session.html.markdown) |
| `alicloud_vpc_vswitch_cidr_reservation` | ✅ | Provides a Vpc Vswitch Cidr Reservation resource. The reserved network segmen... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_vswitch_cidr_reservation.html.markdown) |
| `alicloud_vswitch` | ✅ | Provides a VPC Vswitch resource. ## Module Support | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vswitch.html.markdown) |

---

### Cen

**产品代码**: `cen`
**产品线分类**: 网络
**资源数**: 34

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cen_bandwidth_limit` | ✅ | Provides a CEN cross-regional interconnection bandwidth resource. To connect ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_bandwidth_limit.html.markdown) |
| `alicloud_cen_bandwidth_package` | ✅ | Provides a CEN bandwidth package resource. The CEN bandwidth package is an ab... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_bandwidth_package.html.markdown) |
| `alicloud_cen_bandwidth_package_attachment` | ✅ | Provides a CEN bandwidth package attachment resource. The resource can be use... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_bandwidth_package_attachment.html.markdown) |
| `alicloud_cen_child_instance_route_entry_to_attachment` | ✅ | Provides a Cen Child Instance Route Entry To Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_child_instance_route_entry_to_attachment.html.markdown) |
| `alicloud_cen_flowlog` | ✅ | Provides a CEN Flow Log resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_flowlog.html.markdown) |
| `alicloud_cen_instance` | ✅ | Provides a Cloud Enterprise Network (CEN) Cen Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_instance.html.markdown) |
| `alicloud_cen_instance_attachment` | ✅ | Provides a CEN child instance attachment resource that associate the network(... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_instance_attachment.html.markdown) |
| `alicloud_cen_inter_region_traffic_qos_policy` | ✅ | Provides a Cloud Enterprise Network (CEN) Inter Region Traffic Qos Policy res... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_inter_region_traffic_qos_policy.html.markdown) |
| `alicloud_cen_inter_region_traffic_qos_queue` | ✅ | Provides a Cloud Enterprise Network (CEN) Inter Region Traffic Qos Queue reso... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_inter_region_traffic_qos_queue.html.markdown) |
| `alicloud_cen_private_zone` | ✅ | Provides a Cloud Enterprise Network (CEN) Private Zone resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_private_zone.html.markdown) |
| `alicloud_cen_route_entry` | ✅ | Provides a CEN route entry resource. Cloud Enterprise Network (CEN) supports ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_route_entry.html.markdown) |
| `alicloud_cen_route_map` | ✅ | This topic provides an overview of the route map function of Cloud Enterprise... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_route_map.html.markdown) |
| `alicloud_cen_route_service` | ✅ | Provides a CEN Route Service resource. The virtual border routers (VBRs) and ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_route_service.html.markdown) |
| `alicloud_cen_traffic_marking_policy` | ✅ | Provides a Cloud Enterprise Network (CEN) Traffic Marking Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_traffic_marking_policy.html.markdown) |
| `alicloud_cen_transit_route_table_aggregation` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Route Table Aggregation res... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_route_table_aggregation.html.markdown) |
| `alicloud_cen_transit_router` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router.html.markdown) |
| `alicloud_cen_transit_router_cidr` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Cidr resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_cidr.html.markdown) |
| `alicloud_cen_transit_router_ecr_attachment` | ✅ | Provides a CEN Transit Router Ecr Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_ecr_attachment.html.markdown) |
| `alicloud_cen_transit_router_grant_attachment` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Grant Attachment res... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_grant_attachment.html.markdown) |
| `alicloud_cen_transit_router_multicast_domain` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Multicast Domain res... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain.html.markdown) |
| `alicloud_cen_transit_router_multicast_domain_association` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Multicast Domain Ass... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_association.html.markdown) |
| `alicloud_cen_transit_router_multicast_domain_member` | ✅ | Provides a Cen Transit Router Multicast Domain Member resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_member.html.markdown) |
| `alicloud_cen_transit_router_multicast_domain_peer_member` | ✅ | Provides a Cen Transit Router Multicast Domain Peer Member resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_peer_member.html.markdown) |
| `alicloud_cen_transit_router_multicast_domain_source` | ✅ | Provides a Cen Transit Router Multicast Domain Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_multicast_domain_source.html.markdown) |
| `alicloud_cen_transit_router_peer_attachment` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Peer Attachment reso... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_peer_attachment.html.markdown) |
| `alicloud_cen_transit_router_prefix_list_association` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Prefix List Associat... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_prefix_list_association.html.markdown) |
| `alicloud_cen_transit_router_route_entry` | ✅ | Provides a CEN transit router route entry resource.[What is Cen Transit Route... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_entry.html.markdown) |
| `alicloud_cen_transit_router_route_table` | ✅ | Provides a CEN transit router route table resource.[What is Cen Transit Route... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_table.html.markdown) |
| `alicloud_cen_transit_router_route_table_association` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Route Table Associat... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_table_association.html.markdown) |
| `alicloud_cen_transit_router_route_table_propagation` | ✅ | Provides a CEN transit router route table propagation resource.[What is Cen T... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_route_table_propagation.html.markdown) |
| `alicloud_cen_transit_router_vbr_attachment` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router VBR Attachment resou... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_vbr_attachment.html.markdown) |
| `alicloud_cen_transit_router_vpc_attachment` | ✅ | Provides a Cen Transit Router Vpc Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_vpc_attachment.html.markdown) |
| `alicloud_cen_transit_router_vpn_attachment` | ✅ | Provides a Cloud Enterprise Network (CEN) Transit Router Vpn Attachment resou... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_transit_router_vpn_attachment.html.markdown) |
| `alicloud_cen_vbr_health_check` | ✅ | This topic describes how to configure the health check feature for a Cloud En... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cen_vbr_health_check.html.markdown) |

---

### Ga

**产品代码**: `ga`
**产品线分类**: 网络
**资源数**: 24

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ga_accelerator` | ✅ | Provides a Global Accelerator (GA) Accelerator resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_accelerator.html.markdown) |
| `alicloud_ga_accelerator_spare_ip_attachment` | ✅ | Provides a Global Accelerator (GA) Accelerator Spare Ip Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_accelerator_spare_ip_attachment.html.markdown) |
| `alicloud_ga_access_log` | ✅ | Provides a Global Accelerator (GA) Access Log resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_access_log.html.markdown) |
| `alicloud_ga_acl` | ✅ | Provides a Global Accelerator (GA) Acl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_acl.html.markdown) |
| `alicloud_ga_acl_attachment` | ✅ | Provides a Global Accelerator (GA) Acl Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_acl_attachment.html.markdown) |
| `alicloud_ga_acl_entry_attachment` | ✅ | Provides a Global Accelerator (GA) Acl Entry Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_acl_entry_attachment.html.markdown) |
| `alicloud_ga_additional_certificate` | ✅ | Provides a Global Accelerator (GA) Additional Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_additional_certificate.html.markdown) |
| `alicloud_ga_bandwidth_package` | ✅ | Provides a Global Accelerator (GA) Bandwidth Package resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_bandwidth_package.html.markdown) |
| `alicloud_ga_bandwidth_package_attachment` | ✅ | Provides a Global Accelerator (GA) Bandwidth Package Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_bandwidth_package_attachment.html.markdown) |
| `alicloud_ga_basic_accelerate_ip` | ✅ | Provides a Global Accelerator (GA) Basic Accelerate IP resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_accelerate_ip.html.markdown) |
| `alicloud_ga_basic_accelerate_ip_endpoint_relation` | ✅ | Provides a Global Accelerator (GA) Basic Accelerate Ip Endpoint Relation reso... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_accelerate_ip_endpoint_relation.html.markdown) |
| `alicloud_ga_basic_accelerator` | ✅ | Provides a Global Accelerator (GA) Basic Accelerator resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_accelerator.html.markdown) |
| `alicloud_ga_basic_endpoint` | ✅ | Provides a Global Accelerator (GA) Basic Endpoint resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_endpoint.html.markdown) |
| `alicloud_ga_basic_endpoint_group` | ✅ | Provides a Global Accelerator (GA) Basic Endpoint Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_endpoint_group.html.markdown) |
| `alicloud_ga_basic_ip_set` | ✅ | Provides a Global Accelerator (GA) Basic Ip Set resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_basic_ip_set.html.markdown) |
| `alicloud_ga_custom_routing_endpoint` | ✅ | Provides a Global Accelerator (GA) Custom Routing Endpoint resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint.html.markdown) |
| `alicloud_ga_custom_routing_endpoint_group` | ✅ | Provides a Global Accelerator (GA) Custom Routing Endpoint Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint_group.html.markdown) |
| `alicloud_ga_custom_routing_endpoint_group_destination` | ✅ | Provides a Global Accelerator (GA) Custom Routing Endpoint Group Destination ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint_group_destination.html.markdown) |
| `alicloud_ga_custom_routing_endpoint_traffic_policy` | ✅ | Provides a Global Accelerator (GA) Custom Routing Endpoint Traffic Policy res... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_custom_routing_endpoint_traffic_policy.html.markdown) |
| `alicloud_ga_domain` | ✅ | Provides a Ga Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_domain.html.markdown) |
| `alicloud_ga_endpoint_group` | ✅ | Provides a Global Accelerator (GA) Endpoint Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_endpoint_group.html.markdown) |
| `alicloud_ga_forwarding_rule` | ✅ | Provides a Global Accelerator (GA) Forwarding Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_forwarding_rule.html.markdown) |
| `alicloud_ga_ip_set` | ✅ | Provides a Global Accelerator (GA) Ip Set resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_ip_set.html.markdown) |
| `alicloud_ga_listener` | ✅ | Provides a Global Accelerator (GA) Listener resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ga_listener.html.markdown) |

---

### Express Connect

**产品代码**: `express_connect`
**产品线分类**: 网络
**资源数**: 17 | **已弃用**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_express_connect_ec_failover_test_job` | ✅ | Provides a Express Connect Ec Failover Test Job resource. Express Connect Fai... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_ec_failover_test_job.html.markdown) |
| `alicloud_express_connect_grant_rule_to_cen` | ✅ | Provides a Express Connect Grant Rule To Cen resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_grant_rule_to_cen.html.markdown) |
| `alicloud_express_connect_physical_connection` | ✅ | Provides a Express Connect Physical Connection resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_physical_connection.html.markdown) |
| `alicloud_express_connect_router_interface` | ✅ | Provides a Express Connect Router Interface resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_interface.html.markdown) |
| `alicloud_express_connect_traffic_qos` | ✅ | Provides a Express Connect Traffic Qos resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos.html.markdown) |
| `alicloud_express_connect_traffic_qos_association` | ✅ | Provides a Express Connect Traffic Qos Association resource. Express Connect ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos_association.html.markdown) |
| `alicloud_express_connect_traffic_qos_queue` | ✅ | Provides a Express Connect Traffic Qos Queue resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos_queue.html.markdown) |
| `alicloud_express_connect_traffic_qos_rule` | ✅ | Provides a Express Connect Traffic Qos Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_traffic_qos_rule.html.markdown) |
| `alicloud_express_connect_vbr_pconn_association` | ✅ | Provides a Express Connect Vbr Pconn Association resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_vbr_pconn_association.html.markdown) |
| `alicloud_express_connect_virtual_border_router` | ✅ | Provides a Express Connect Virtual Border Router resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_virtual_border_router.html.markdown) |
| `alicloud_express_connect_virtual_physical_connection` | ✅ | Provides a Express Connect Virtual Physical Connection resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_virtual_physical_connection.html.markdown) |
| `alicloud_router_interface` | ⚠️ 弃用 → `alicloud_express_connect_router_interface` | Provides a VPC router interface resource aim to build a connection between tw... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/router_interface.html.markdown) |
| `alicloud_router_interface_connection` | ⚠️ 弃用 → `alicloud_express_connect_router_interface` | Provides a VPC router interface connection resource to connect two router int... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/router_interface_connection.html.markdown) |
| `alicloud_vpc_bgp_group` | ✅ | Provides a Express Connect Bgp Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_bgp_group.html.markdown) |
| `alicloud_vpc_bgp_network` | ✅ | Provides a Express Connect Bgp Network resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_bgp_network.html.markdown) |
| `alicloud_vpc_bgp_peer` | ✅ | Provides a Express Connect Bgp Peer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_bgp_peer.html.markdown) |
| `alicloud_vpc_vbr_ha` | ✅ | Provides a Express Connect Vbr Ha resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_vbr_ha.html.markdown) |

---

### Alidns

**产品代码**: `alidns`
**产品线分类**: 网络
**资源数**: 16 | **已弃用**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_alidns_access_strategy` | ✅ | Provides a DNS Access Strategy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_access_strategy.html.markdown) |
| `alicloud_alidns_address_pool` | ✅ | Provides a Alidns Address Pool resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_address_pool.html.markdown) |
| `alicloud_alidns_custom_line` | ✅ | Provides a Alidns Custom Line resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_custom_line.html.markdown) |
| `alicloud_alidns_domain` | ✅ | Provides a Alidns domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_domain.html.markdown) |
| `alicloud_alidns_domain_attachment` | ✅ | Provides bind the domain name to the Alidns instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_domain_attachment.html.markdown) |
| `alicloud_alidns_domain_group` | ✅ | Provides a Alidns Domain Group resource. For information about Alidns Domain ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_domain_group.html.markdown) |
| `alicloud_alidns_gtm_instance` | ✅ | Provides a Alidns Gtm Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_gtm_instance.html.markdown) |
| `alicloud_alidns_instance` | ✅ | Create an Alidns Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_instance.html.markdown) |
| `alicloud_alidns_monitor_config` | ✅ | Provides a DNS Monitor Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_monitor_config.html.markdown) |
| `alicloud_alidns_record` | ✅ | Provides a Alidns Record resource. For information about Alidns Domain Record... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alidns_record.html.markdown) |
| `alicloud_dns` | ⚠️ 弃用 → `alicloud_alidns_domain` | Provides a DNS resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns.html.markdown) |
| `alicloud_dns_domain` | ⚠️ 弃用 → `alicloud_alidns_domain` | Provides a DNS domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_domain.html.markdown) |
| `alicloud_dns_domain_attachment` | ⚠️ 弃用 → `alicloud_alidns_domain_attachment` | Provides bind the domain name to the DNS instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_domain_attachment.html.markdown) |
| `alicloud_dns_group` | ⚠️ 弃用 → `alicloud_alidns_domain_group` | Provides a DNS Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_group.html.markdown) |
| `alicloud_dns_instance` | ⚠️ 弃用 → `alicloud_alidns_instance` | Create an DNS Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_instance.html.markdown) |
| `alicloud_dns_record` | ⚠️ 弃用 → `alicloud_alidns_record` | Provides a DNS Record resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dns_record.html.markdown) |

---

### Application Load Balancer

**产品代码**: `alb`
**产品线分类**: 网络
**资源数**: 15

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_alb_acl` | ✅ | Provides a Application Load Balancer (ALB) Acl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_acl.html.markdown) |
| `alicloud_alb_acl_entry_attachment` | ✅ | For information about acl entry attachment and how to use it, see [Configure ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_acl_entry_attachment.html.markdown) |
| `alicloud_alb_ascript` | ✅ | Provides a Application Load Balancer (ALB) A Script resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_ascript.html.markdown) |
| `alicloud_alb_health_check_template` | ✅ | Provides a Application Load Balancer (ALB) Health Check Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_health_check_template.html.markdown) |
| `alicloud_alb_listener` | ✅ | Provides a Application Load Balancer (ALB) Listener resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_listener.html.markdown) |
| `alicloud_alb_listener_acl_attachment` | ✅ | Provides a ALB Listener Acl Attachment resource. Associating ACL to listening. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_listener_acl_attachment.html.markdown) |
| `alicloud_alb_listener_additional_certificate_attachment` | ✅ | Provides a Application Load Balancer (ALB) Listener Additional Certificate At... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_listener_additional_certificate_attachment.html.markdown) |
| `alicloud_alb_load_balancer` | ✅ | Provides a Application Load Balancer (ALB) Load Balancer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer.html.markdown) |
| `alicloud_alb_load_balancer_access_log_config_attachment` | ✅ | Provides a Application Load Balancer (ALB) Load Balancer Access Log Config At... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_access_log_config_attachment.html.markdown) |
| `alicloud_alb_load_balancer_common_bandwidth_package_attachment` | ✅ | Provides a Alb Load Balancer Common Bandwidth Package Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_common_bandwidth_package_attachment.html.markdown) |
| `alicloud_alb_load_balancer_security_group_attachment` | ✅ | Provides a Application Load Balancer (ALB) Load Balancer Security Group Attac... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_security_group_attachment.html.markdown) |
| `alicloud_alb_load_balancer_zone_shifted_attachment` | ✅ | Provides a Application Load Balancer (ALB) Load Balancer Zone Shifted Attachm... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_load_balancer_zone_shifted_attachment.html.markdown) |
| `alicloud_alb_rule` | ✅ | Provides a Application Load Balancer (ALB) Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_rule.html.markdown) |
| `alicloud_alb_security_policy` | ✅ | Provides a ALB Security Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_security_policy.html.markdown) |
| `alicloud_alb_server_group` | ✅ | Provides a Application Load Balancer (ALB) Server Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alb_server_group.html.markdown) |

---

### Server Load Balancer

**产品代码**: `slb`
**产品线分类**: 网络
**资源数**: 15 | **已弃用**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_slb` | ⚠️ 弃用 → `alicloud_slb_load_balancer` | Provides an Application Load Balancer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb.html.markdown) |
| `alicloud_slb_acl` | ✅ | An access control list contains multiple IP addresses or CIDR blocks. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_acl.html.markdown) |
| `alicloud_slb_acl_entry_attachment` | ✅ | For information about acl entry attachment and how to use it, see [Configure ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_acl_entry_attachment.html.markdown) |
| `alicloud_slb_attachment` | ⚠️ 弃用 → `alicloud_slb_backend_server` | Add a group of backend servers (ECS instance) to the Server Load Balancer or ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_attachment.html.markdown) |
| `alicloud_slb_backend_server` | ✅ | Add a group of backend servers (ECS or ENI instance) to the Server Load Balan... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_backend_server.html.markdown) |
| `alicloud_slb_ca_certificate` | ✅ | A Load Balancer CA Certificate is used by the listener of the protocol https. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_ca_certificate.html.markdown) |
| `alicloud_slb_domain_extension` | ✅ | HTTPS listeners of guaranteed-performance SLB support configuring multiple ce... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_domain_extension.html.markdown) |
| `alicloud_slb_listener` | ✅ | Provides a Classic Load Balancer (SLB) Load Balancer Listener resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_listener.html.markdown) |
| `alicloud_slb_load_balancer` | ✅ | Provides an Application Load Balancer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_load_balancer.html.markdown) |
| `alicloud_slb_master_slave_server_group` | ✅ | A master slave server group contains two ECS instances. The master slave serv... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_master_slave_server_group.html.markdown) |
| `alicloud_slb_rule` | ✅ | Provides a Lindorm Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_rule.html.markdown) |
| `alicloud_slb_server_certificate` | ✅ | A Load Balancer Server Certificate is an ssl Certificate used by the listener... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_server_certificate.html.markdown) |
| `alicloud_slb_server_group` | ✅ | Provides a Load Balancer Virtual Backend Server Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_server_group.html.markdown) |
| `alicloud_slb_server_group_server_attachment` | ✅ | Provides a Load Balancer Virtual Backend Server Group Server Attachment resou... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_server_group_server_attachment.html.markdown) |
| `alicloud_slb_tls_cipher_policy` | ✅ | Provides a SLB Tls Cipher Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/slb_tls_cipher_policy.html.markdown) |

---

### Api Gateway

**产品代码**: `api_gateway`
**产品线分类**: 网络
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_api_gateway_access_control_list` | ✅ | Provides a Api Gateway Access Control List resource. Access control list. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_access_control_list.html.markdown) |
| `alicloud_api_gateway_acl_entry_attachment` | ✅ | Provides an ACL entry attachment resource for attaching ACL entry to an API G... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_acl_entry_attachment.html.markdown) |
| `alicloud_api_gateway_api` | ✅ | Provides an api resource.When you create an API, you must enter the basic inf... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_api.html.markdown) |
| `alicloud_api_gateway_app` | ✅ | Provides an app resource.It must create an app before calling a third-party A... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_app.html.markdown) |
| `alicloud_api_gateway_app_attachment` | ✅ | Provides an app attachment resource.It is used for authorizing a specific api... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_app_attachment.html.markdown) |
| `alicloud_api_gateway_backend` | ✅ | Provides a Api Gateway Backend resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_backend.html.markdown) |
| `alicloud_api_gateway_group` | ✅ | Provides an api group resource.To create an API, you must firstly create a gr... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_group.html.markdown) |
| `alicloud_api_gateway_instance` | ✅ | Provides a Api Gateway Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_instance.html.markdown) |
| `alicloud_api_gateway_instance_acl_attachment` | ✅ | Provides an Instance ACL attachment resource for attaching an ACL to a specif... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_instance_acl_attachment.html.markdown) |
| `alicloud_api_gateway_log_config` | ✅ | Provides a Api Gateway Log Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_log_config.html.markdown) |
| `alicloud_api_gateway_model` | ✅ | Provides a Api Gateway Model resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_model.html.markdown) |
| `alicloud_api_gateway_plugin` | ✅ | Provides a Api Gateway Plugin resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_plugin.html.markdown) |
| `alicloud_api_gateway_plugin_attachment` | ✅ | Provides a plugin attachment resource.It is used for attaching a specific plu... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_plugin_attachment.html.markdown) |
| `alicloud_api_gateway_vpc_access` | ✅ | Provides an Api Gateway Vpc Access resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/api_gateway_vpc_access.html.markdown) |

---

### Nlb

**产品代码**: `nlb`
**产品线分类**: 网络
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_nlb_hd_monitor_region_config` | ✅ | Provides a Network Load Balancer (NLB) Hd Monitor Region Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_hd_monitor_region_config.html.markdown) |
| `alicloud_nlb_listener` | ✅ | Provides a Network Load Balancer (NLB) Listener resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_listener.html.markdown) |
| `alicloud_nlb_listener_additional_certificate_attachment` | ✅ | Provides a NLB Listener Additional Certificate Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_listener_additional_certificate_attachment.html.markdown) |
| `alicloud_nlb_load_balancer` | ✅ | Provides a Network Load Balancer (NLB) Load Balancer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_load_balancer.html.markdown) |
| `alicloud_nlb_load_balancer_security_group_attachment` | ✅ | Provides a NLB Load Balancer Security Group Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_load_balancer_security_group_attachment.html.markdown) |
| `alicloud_nlb_load_balancer_zone_shifted_attachment` | ✅ | Provides a Network Load Balancer (NLB) Load Balancer Zone Shifted Attachment ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_load_balancer_zone_shifted_attachment.html.markdown) |
| `alicloud_nlb_loadbalancer_common_bandwidth_package_attachment` | ✅ | Provides a NLB Loadbalancer Common Bandwidth Package Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_loadbalancer_common_bandwidth_package_attachment.html.markdown) |
| `alicloud_nlb_security_policy` | ✅ | Provides a NLB Security Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_security_policy.html.markdown) |
| `alicloud_nlb_server_group` | ✅ | Provides a Network Load Balancer (NLB) Server Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_server_group.html.markdown) |
| `alicloud_nlb_server_group_server_attachment` | ✅ | Provides a Network Load Balancer (NLB) Server Group Server Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nlb_server_group_server_attachment.html.markdown) |

---

### Vpn Gateway

**产品代码**: `vpn_gateway`
**产品线分类**: 网络
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ssl_vpn_client_cert` | ✅ | Provides a SSL VPN client cert resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_vpn_client_cert.html.markdown) |
| `alicloud_ssl_vpn_server` | ✅ | Provides a SSL VPN server resource. [Refer to details](https://www.alibabaclo... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ssl_vpn_server.html.markdown) |
| `alicloud_vpn_connection` | ✅ | Provides a VPN connection resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_connection.html.markdown) |
| `alicloud_vpn_customer_gateway` | ✅ | Provides a VPN customer gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_customer_gateway.html.markdown) |
| `alicloud_vpn_gateway` | ✅ | Provides a VPN gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_gateway.html.markdown) |
| `alicloud_vpn_gateway_vco_route` | ✅ | Provides a VPN Gateway Vco Route resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_gateway_vco_route.html.markdown) |
| `alicloud_vpn_gateway_vpn_attachment` | ✅ | Provides a VPN Gateway Vpn Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_gateway_vpn_attachment.html.markdown) |
| `alicloud_vpn_ipsec_server` | ✅ | Provides a VPN Ipsec Server resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_ipsec_server.html.markdown) |
| `alicloud_vpn_pbr_route_entry` | ✅ | Provides a VPN Pbr Route Entry resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_pbr_route_entry.html.markdown) |
| `alicloud_vpn_route_entry` | ✅ | Provides a VPN Route Entry resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpn_route_entry.html.markdown) |

---

### Cloud Storage Gateway

**产品代码**: `cloud_storage_gateway`
**产品线分类**: 网络
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloud_storage_gateway_express_sync` | ✅ | Provides a Cloud Storage Gateway Express Sync resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_express_sync.html.markdown) |
| `alicloud_cloud_storage_gateway_express_sync_share_attachment` | ✅ | Provides a Cloud Storage Gateway Express Sync Share Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_express_sync_share_attachment.html.markdown) |
| `alicloud_cloud_storage_gateway_gateway` | ✅ | Provides a Cloud Storage Gateway Gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway.html.markdown) |
| `alicloud_cloud_storage_gateway_gateway_block_volume` | ✅ | Provides a Cloud Storage Gateway Gateway Block Volume resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_block_volume.html.markdown) |
| `alicloud_cloud_storage_gateway_gateway_cache_disk` | ✅ | Provides a Cloud Storage Gateway Gateway Cache Disk resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_cache_disk.html.markdown) |
| `alicloud_cloud_storage_gateway_gateway_file_share` | ✅ | Provides a Cloud Storage Gateway Gateway File Share resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_file_share.html.markdown) |
| `alicloud_cloud_storage_gateway_gateway_logging` | ✅ | Provides a Cloud Storage Gateway Gateway Logging resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_logging.html.markdown) |
| `alicloud_cloud_storage_gateway_gateway_smb_user` | ✅ | Provides a Cloud Storage Gateway Gateway SMB User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_gateway_smb_user.html.markdown) |
| `alicloud_cloud_storage_gateway_storage_bundle` | ✅ | Provides a Cloud Storage Gateway Storage Bundle resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_storage_gateway_storage_bundle.html.markdown) |

---

### Private Zone

**产品代码**: `private_zone`
**产品线分类**: 网络
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_pvtz_endpoint` | ✅ | Provides a Private Zone Endpoint resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_endpoint.html.markdown) |
| `alicloud_pvtz_rule` | ✅ | Provides a Private Zone Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_rule.html.markdown) |
| `alicloud_pvtz_rule_attachment` | ✅ | Provides a Private Zone Rule Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_rule_attachment.html.markdown) |
| `alicloud_pvtz_user_vpc_authorization` | ✅ | Provides a Private Zone User Vpc Authorization resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_user_vpc_authorization.html.markdown) |
| `alicloud_pvtz_zone` | ✅ | Provides a Private Zone resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_zone.html.markdown) |
| `alicloud_pvtz_zone_attachment` | ✅ | Provides vpcs bound to Alicloud Private Zone resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_zone_attachment.html.markdown) |
| `alicloud_pvtz_zone_record` | ✅ | Provides a Private Zone Record resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pvtz_zone_record.html.markdown) |

---

### Vpc Ipam

**产品代码**: `vpc_ipam`
**产品线分类**: 网络
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_vpc_ipam_ipam` | ✅ | Provides a Vpc Ipam Ipam resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam.html.markdown) |
| `alicloud_vpc_ipam_ipam_pool` | ✅ | Provides a Vpc Ipam Ipam Pool resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_pool.html.markdown) |
| `alicloud_vpc_ipam_ipam_pool_allocation` | ✅ | Provides a Vpc Ipam Ipam Pool Allocation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_pool_allocation.html.markdown) |
| `alicloud_vpc_ipam_ipam_pool_cidr` | ✅ | Provides a Vpc Ipam Ipam Pool Cidr resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_pool_cidr.html.markdown) |
| `alicloud_vpc_ipam_ipam_resource_discovery` | ✅ | Provides a Vpc Ipam Ipam Resource Discovery resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_resource_discovery.html.markdown) |
| `alicloud_vpc_ipam_ipam_scope` | ✅ | Provides a Vpc Ipam Ipam Scope resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_ipam_scope.html.markdown) |
| `alicloud_vpc_ipam_service` | ✅ | Provides a Vpc Ipam Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_ipam_service.html.markdown) |

---

### Private Link

**产品代码**: `private_link`
**产品线分类**: 网络
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_privatelink_vpc_endpoint` | ✅ | Provides a Private Link Vpc Endpoint resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint.html.markdown) |
| `alicloud_privatelink_vpc_endpoint_connection` | ✅ | Provides a Private Link Vpc Endpoint Connection resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_connection.html.markdown) |
| `alicloud_privatelink_vpc_endpoint_service` | ✅ | Provides a Private Link Vpc Endpoint Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_service.html.markdown) |
| `alicloud_privatelink_vpc_endpoint_service_resource` | ✅ | Provides a Private Link Vpc Endpoint Service Resource resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_service_resource.html.markdown) |
| `alicloud_privatelink_vpc_endpoint_service_user` | ✅ | Provides a Private Link Vpc Endpoint Service User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_service_user.html.markdown) |
| `alicloud_privatelink_vpc_endpoint_zone` | ✅ | Provides a Private Link Vpc Endpoint Zone resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/privatelink_vpc_endpoint_zone.html.markdown) |

---

### Express Connect Router

**产品代码**: `express_connect_router`
**产品线分类**: 网络
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_express_connect_router_express_connect_router` | ✅ | Provides a Express Connect Router Express Connect Router resource. Express Co... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_express_connect_router.html.markdown) |
| `alicloud_express_connect_router_grant_association` | ✅ | Provides a Express Connect Router Grant Association resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_grant_association.html.markdown) |
| `alicloud_express_connect_router_tr_association` | ✅ | Provides a Express Connect Router Express Connect Router Tr Association resou... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_tr_association.html.markdown) |
| `alicloud_express_connect_router_vbr_child_instance` | ✅ | Provides a Express Connect Router Express Connect Router Vbr Child Instance r... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_vbr_child_instance.html.markdown) |
| `alicloud_express_connect_router_vpc_association` | ✅ | Provides a Express Connect Router Express Connect Router Vpc Association reso... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/express_connect_router_vpc_association.html.markdown) |

---

### Nat Gateway

**产品代码**: `nat_gateway`
**产品线分类**: 网络
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_forward_entry` | ✅ | Provides a forward resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/forward_entry.html.markdown) |
| `alicloud_nat_gateway` | ✅ | Provides a resource to create a VPC NAT Gateway. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nat_gateway.html.markdown) |
| `alicloud_snat_entry` | ✅ | Provides a NAT Gateway Snat Entry resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/snat_entry.html.markdown) |
| `alicloud_vpc_nat_ip` | ✅ | Provides a Nat Gateway Nat Ip resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_nat_ip.html.markdown) |
| `alicloud_vpc_nat_ip_cidr` | ✅ | Provides a Nat Gateway Nat Ip Cidr resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vpc_nat_ip_cidr.html.markdown) |

---

### Cddc

**产品代码**: `cddc`
**产品线分类**: 网络
**资源数**: 4 | **已弃用**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cddc_dedicated_host` | ⚠️ 弃用 | Provides a ApsaraDB for MyBase Dedicated Host resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_host.html.markdown) |
| `alicloud_cddc_dedicated_host_account` | ⚠️ 弃用 | Provides a ApsaraDB for MyBase Dedicated Host Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_host_account.html.markdown) |
| `alicloud_cddc_dedicated_host_group` | ⚠️ 弃用 | Provides a ApsaraDB for MyBase Dedicated Host Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_host_group.html.markdown) |
| `alicloud_cddc_dedicated_propre_host` | ⚠️ 弃用 | Provides a CDDC Dedicated Propre Host resource. MyBase proprietary cluster ho... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cddc_dedicated_propre_host.html.markdown) |

---

### Eip

**产品代码**: `eip`
**产品线分类**: 网络
**资源数**: 4 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_eip` | ⚠️ 弃用 → `alicloud_eip_address` | Provides an elastic IP resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip.html.markdown) |
| `alicloud_eip_address` | ✅ | Provides a EIP Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip_address.html.markdown) |
| `alicloud_eip_association` | ✅ | Provides a EIP Association resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip_association.html.markdown) |
| `alicloud_eip_segment_address` | ✅ | Provides a EIP Segment Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eip_segment_address.html.markdown) |

---

### Apig

**产品代码**: `apig`
**产品线分类**: 网络
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_apig_environment` | ✅ | Provides a APIG Environment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/apig_environment.html.markdown) |
| `alicloud_apig_gateway` | ✅ | Provides a APIG Gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/apig_gateway.html.markdown) |
| `alicloud_apig_http_api` | ✅ | Provides a APIG Http Api resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/apig_http_api.html.markdown) |

---

### Gwlb

**产品代码**: `gwlb`
**产品线分类**: 网络
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_gwlb_listener` | ✅ | Provides a GWLB Listener resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gwlb_listener.html.markdown) |
| `alicloud_gwlb_load_balancer` | ✅ | Provides a GWLB Load Balancer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gwlb_load_balancer.html.markdown) |
| `alicloud_gwlb_server_group` | ✅ | Provides a GWLB Server Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gwlb_server_group.html.markdown) |

---

### Eipanycast

**产品代码**: `eipanycast`
**产品线分类**: 网络
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_eipanycast_anycast_eip_address` | ✅ | Provides a Eipanycast Anycast Eip Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eipanycast_anycast_eip_address.html.markdown) |
| `alicloud_eipanycast_anycast_eip_address_attachment` | ✅ | Provides a Eipanycast Anycast Eip Address Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eipanycast_anycast_eip_address_attachment.html.markdown) |

---

### Database Gateway

**产品代码**: `database_gateway`
**产品线分类**: 网络
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_database_gateway_gateway` | ✅ | Provides a Database Gateway Gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/database_gateway_gateway.html.markdown) |

---

### Rdc

**产品代码**: `rdc`
**产品线分类**: 网络
**资源数**: 1 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_rdc_organization` | ⚠️ 弃用 | Provides a RDC Organization resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rdc_organization.html.markdown) |

---

## 企业IT治理 (15 个产品)

### Cloud Monitor Service

**产品代码**: `cloud_monitor_service`
**产品线分类**: 企业IT治理
**资源数**: 21

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloud_monitor_service_agent_config` | ✅ | Provides a Cloud Monitor Service Agent Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_agent_config.html.markdown) |
| `alicloud_cloud_monitor_service_basic_public` | ✅ | Provides a Cloud Monitor Service Basic Public resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_basic_public.html.markdown) |
| `alicloud_cloud_monitor_service_enterprise_public` | ✅ | Provides a Cloud Monitor Service Enterprise Public resource. Hybrid Cloud Mon... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_enterprise_public.html.markdown) |
| `alicloud_cloud_monitor_service_group_monitoring_agent_process` | ✅ | Provides a Cloud Monitor Service Group Monitoring Agent Process resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_group_monitoring_agent_process.html.markdown) |
| `alicloud_cloud_monitor_service_hybrid_double_write` | ✅ | Provides a Cloud Monitor Service Hybrid Double Write resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_hybrid_double_write.html.markdown) |
| `alicloud_cloud_monitor_service_monitoring_agent_process` | ✅ | Provides a Cloud Monitor Service Monitoring Agent Process resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_monitor_service_monitoring_agent_process.html.markdown) |
| `alicloud_cms_alarm` | ✅ | Provides a Cloud Monitor Service Alarm resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_alarm.html.markdown) |
| `alicloud_cms_alarm_contact` | ✅ | Creates or modifies an alarm contact. For information about alarm contact and... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_alarm_contact.html.markdown) |
| `alicloud_cms_alarm_contact_group` | ✅ | Provides a CMS Alarm Contact Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_alarm_contact_group.html.markdown) |
| `alicloud_cms_dynamic_tag_group` | ✅ | Provides a Cloud Monitor Service Dynamic Tag Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_dynamic_tag_group.html.markdown) |
| `alicloud_cms_event_rule` | ✅ | Provides a Cloud Monitor Service Event Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_event_rule.html.markdown) |
| `alicloud_cms_group_metric_rule` | ✅ | Provides a Cloud Monitor Service Group Metric Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_group_metric_rule.html.markdown) |
| `alicloud_cms_hybrid_monitor_fc_task` | ✅ | Provides a Cloud Monitor Service Hybrid Monitor Fc Task resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_hybrid_monitor_fc_task.html.markdown) |
| `alicloud_cms_hybrid_monitor_sls_task` | ✅ | Provides a Cloud Monitor Service Hybrid Monitor Sls Task resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_hybrid_monitor_sls_task.html.markdown) |
| `alicloud_cms_metric_rule_black_list` | ✅ | Provides a Cloud Monitor Service Metric Rule Black List resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_metric_rule_black_list.html.markdown) |
| `alicloud_cms_metric_rule_template` | ✅ | Provides a Cloud Monitor Service Metric Rule Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_metric_rule_template.html.markdown) |
| `alicloud_cms_monitor_group` | ✅ | Provides a Cloud Monitor Service Monitor Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_monitor_group.html.markdown) |
| `alicloud_cms_monitor_group_instances` | ✅ | Provides a Cloud Monitor Service Monitor Group Instances resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_monitor_group_instances.html.markdown) |
| `alicloud_cms_namespace` | ✅ | Provides a Cloud Monitor Service Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_namespace.html.markdown) |
| `alicloud_cms_site_monitor` | ✅ | Provides a Cloud Monitor Service Site Monitor resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_site_monitor.html.markdown) |
| `alicloud_cms_sls_group` | ✅ | Provides a Cloud Monitor Service Sls Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cms_sls_group.html.markdown) |

---

### Resource Manager

**产品代码**: `resource_manager`
**产品线分类**: 企业IT治理
**资源数**: 21

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_resource_manager_account` | ✅ | Provides a Resource Manager Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_account.html.markdown) |
| `alicloud_resource_manager_auto_grouping_rule` | ✅ | Provides a Resource Manager Auto Grouping Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_auto_grouping_rule.html.markdown) |
| `alicloud_resource_manager_control_policy` | ✅ | Provides a Resource Manager Control Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_control_policy.html.markdown) |
| `alicloud_resource_manager_control_policy_attachment` | ✅ | Provides a Resource Manager Control Policy Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_control_policy_attachment.html.markdown) |
| `alicloud_resource_manager_delegated_administrator` | ✅ | Provides a Resource Manager Delegated Administrator resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_delegated_administrator.html.markdown) |
| `alicloud_resource_manager_delivery_channel` | ✅ | Provides a Resource Manager Delivery Channel resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_delivery_channel.html.markdown) |
| `alicloud_resource_manager_folder` | ✅ | Provides a Resource Manager Folder resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_folder.html.markdown) |
| `alicloud_resource_manager_handshake` | ✅ | Provides a Resource Manager Handshake resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_handshake.html.markdown) |
| `alicloud_resource_manager_message_contact` | ✅ | Provides a Resource Manager Message Contact resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_message_contact.html.markdown) |
| `alicloud_resource_manager_multi_account_delivery_channel` | ✅ | Provides a Resource Manager Multi Account Delivery Channel resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_multi_account_delivery_channel.html.markdown) |
| `alicloud_resource_manager_policy` | ✅ | Provides a Resource Manager Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_policy.html.markdown) |
| `alicloud_resource_manager_policy_attachment` | ✅ | Provides a Resource Manager Policy Attachment resource to attaches a policy t... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_policy_attachment.html.markdown) |
| `alicloud_resource_manager_policy_version` | ✅ | Provides a Resource Manager Policy Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_policy_version.html.markdown) |
| `alicloud_resource_manager_resource_directory` | ✅ | Provides a Resource Manager Resource Directory resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_resource_directory.html.markdown) |
| `alicloud_resource_manager_resource_group` | ✅ | Provides a Resource Manager Resource Group resource. If you need to group clo... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_resource_group.html.markdown) |
| `alicloud_resource_manager_resource_share` | ✅ | Provides a Resource Manager Resource Share resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_resource_share.html.markdown) |
| `alicloud_resource_manager_role` | ✅ | Provides a Resource Manager role resource. Members are resource containers in... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_role.html.markdown) |
| `alicloud_resource_manager_saved_query` | ✅ | Provides a Resource Manager Saved Query resource. ResourceCenter Saved Query. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_saved_query.html.markdown) |
| `alicloud_resource_manager_service_linked_role` | ✅ | Provides a Resource Manager Service Linked Role. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_service_linked_role.html.markdown) |
| `alicloud_resource_manager_shared_resource` | ✅ | Provides a Resource Manager Shared Resource resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_shared_resource.html.markdown) |
| `alicloud_resource_manager_shared_target` | ✅ | Provides a Resource Manager Shared Target resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/resource_manager_shared_target.html.markdown) |

---

### Arms

**产品代码**: `arms`
**产品线分类**: 企业IT治理
**资源数**: 17 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_arms_addon_release` | ✅ | Provides a ARMS Addon Release resource. Release package of observability addon. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_addon_release.html.markdown) |
| `alicloud_arms_alert_contact` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Alert Contact reso... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_alert_contact.html.markdown) |
| `alicloud_arms_alert_contact_group` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Alert Contact Grou... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_alert_contact_group.html.markdown) |
| `alicloud_arms_alert_robot` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Alert Robot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_alert_robot.html.markdown) |
| `alicloud_arms_dispatch_rule` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Alert Dispatch Rul... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_dispatch_rule.html.markdown) |
| `alicloud_arms_env_custom_job` | ✅ | Provides a ARMS Env Custom Job resource. Custom jobs in the arms environment. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_custom_job.html.markdown) |
| `alicloud_arms_env_feature` | ✅ | Provides a ARMS Env Feature resource. Feature of the arms environment. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_feature.html.markdown) |
| `alicloud_arms_env_pod_monitor` | ✅ | Provides a ARMS Env Pod Monitor resource. PodMonitor for the arms environment. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_pod_monitor.html.markdown) |
| `alicloud_arms_env_service_monitor` | ✅ | Provides a ARMS Env Service Monitor resource. ServiceMonitor for the arms env... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_env_service_monitor.html.markdown) |
| `alicloud_arms_environment` | ✅ | Provides a ARMS Environment resource. The arms environment. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_environment.html.markdown) |
| `alicloud_arms_grafana_workspace` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Grafana Workspace ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_grafana_workspace.html.markdown) |
| `alicloud_arms_integration_exporter` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Integration Export... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_integration_exporter.html.markdown) |
| `alicloud_arms_prometheus` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Prometheus resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_prometheus.html.markdown) |
| `alicloud_arms_prometheus_alert_rule` | ✅ | Provides a Application Real-Time Monitoring Service (ARMS) Prometheus Alert R... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_prometheus_alert_rule.html.markdown) |
| `alicloud_arms_prometheus_monitoring` | ✅ | Provides a ARMS Prometheus Monitoring resource. Including serviceMonitor, pod... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_prometheus_monitoring.html.markdown) |
| `alicloud_arms_remote_write` | ⚠️ 弃用 | Provides a Application Real-Time Monitoring Service (ARMS) Remote Write resou... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_remote_write.html.markdown) |
| `alicloud_arms_synthetic_task` | ✅ | Provides a ARMS Synthetic Task resource. Cloud Synthetic task resources. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/arms_synthetic_task.html.markdown) |

---

### Smartag

**产品代码**: `smartag`
**产品线分类**: 企业IT治理
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloud_connect_network` | ✅ | Provides a cloud connect network resource. Cloud Connect Network (CCN) is ano... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_connect_network.html.markdown) |
| `alicloud_cloud_connect_network_attachment` | ✅ | Provides a Cloud Connect Network Attachment resource. This topic describes ho... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_connect_network_attachment.html.markdown) |
| `alicloud_cloud_connect_network_grant` | ✅ | Provides a Cloud Connect Network Grant resource. If the CEN instance to be at... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_connect_network_grant.html.markdown) |
| `alicloud_sag_acl` | ✅ | Provides a Sag Acl resource. Smart Access Gateway (SAG) provides the access c... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_acl.html.markdown) |
| `alicloud_sag_acl_rule` | ✅ | Provides a Sag Acl Rule resource. This topic describes how to configure an ac... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_acl_rule.html.markdown) |
| `alicloud_sag_client_user` | ✅ | Provides a Sag ClientUser resource. This topic describes how to manage accoun... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_client_user.html.markdown) |
| `alicloud_sag_dnat_entry` | ✅ | Provides a Sag DnatEntry resource. This topic describes how to add a DNAT ent... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_dnat_entry.html.markdown) |
| `alicloud_sag_qos` | ✅ | Provides a Sag Qos resource. Smart Access Gateway (SAG) supports quintuple-ba... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_qos.html.markdown) |
| `alicloud_sag_qos_car` | ✅ | Provides a Sag Qos Car resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_qos_car.html.markdown) |
| `alicloud_sag_qos_policy` | ✅ | Provides a Sag qos policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_qos_policy.html.markdown) |
| `alicloud_sag_snat_entry` | ✅ | Provides a Sag SnatEntry resource. This topic describes how to add a SNAT ent... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sag_snat_entry.html.markdown) |
| `alicloud_smartag_flow_log` | ✅ | Provides a Smartag Flow Log resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/smartag_flow_log.html.markdown) |

---

### Config

**产品代码**: `config`
**产品线分类**: 企业IT治理
**资源数**: 12 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_config_aggregate_compliance_pack` | ✅ | Provides a Cloud Config Aggregate Compliance Pack resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_compliance_pack.html.markdown) |
| `alicloud_config_aggregate_config_rule` | ✅ | Provides a Cloud Config Aggregate Config Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_config_rule.html.markdown) |
| `alicloud_config_aggregate_delivery` | ✅ | Provides a Config Aggregate Delivery resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_delivery.html.markdown) |
| `alicloud_config_aggregate_remediation` | ✅ | Provides a Cloud Config (Config) Aggregate Remediation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregate_remediation.html.markdown) |
| `alicloud_config_aggregator` | ✅ | Provides a Cloud Config (Config) Aggregator resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_aggregator.html.markdown) |
| `alicloud_config_compliance_pack` | ✅ | Provides a Cloud Config Compliance Pack resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_compliance_pack.html.markdown) |
| `alicloud_config_configuration_recorder` | ✅ | Provides a Alicloud Config Configuration Recorder resource. Cloud Config is a... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_configuration_recorder.html.markdown) |
| `alicloud_config_delivery` | ✅ | Provides a Config Delivery resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_delivery.html.markdown) |
| `alicloud_config_delivery_channel` | ⚠️ 弃用 → `alicloud_config_delivery` | Please use new resource [alicloud_config_delivery](https://registry.terraform... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_delivery_channel.html.markdown) |
| `alicloud_config_remediation` | ✅ | Provides a Config Remediation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_remediation.html.markdown) |
| `alicloud_config_report_template` | ✅ | Provides a Cloud Config (Config) Report Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_report_template.html.markdown) |
| `alicloud_config_rule` | ✅ | Provides a Config Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/config_rule.html.markdown) |

---

### Oos

**产品代码**: `oos`
**产品线分类**: 企业IT治理
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_oos_application` | ✅ | Provides a OOS Application resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_application.html.markdown) |
| `alicloud_oos_application_group` | ✅ | Provides a OOS Application Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_application_group.html.markdown) |
| `alicloud_oos_default_patch_baseline` | ✅ | Provides a Oos Default Patch Baseline resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_default_patch_baseline.html.markdown) |
| `alicloud_oos_execution` | ✅ | Provides a OOS Execution resource. For information about Alicloud OOS Executi... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_execution.html.markdown) |
| `alicloud_oos_parameter` | ✅ | Provides a OOS Parameter resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_parameter.html.markdown) |
| `alicloud_oos_patch_baseline` | ✅ | Provides a Operation Orchestration Service (OOS) Patch Baseline resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_patch_baseline.html.markdown) |
| `alicloud_oos_secret_parameter` | ✅ | Provides a Operation Orchestration Service (OOS) Secret Parameter resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_secret_parameter.html.markdown) |
| `alicloud_oos_service_setting` | ✅ | Provides a OOS Service Setting resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_service_setting.html.markdown) |
| `alicloud_oos_state_configuration` | ✅ | Provides a OOS State Configuration resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_state_configuration.html.markdown) |
| `alicloud_oos_template` | ✅ | Provides a OOS Template resource. For information about Alicloud OOS Template... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oos_template.html.markdown) |

---

### Event Bridge

**产品代码**: `event_bridge`
**产品线分类**: 企业IT治理
**资源数**: 7 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_event_bridge_api_destination` | ✅ | Provides a Event Bridge Api Destination resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_api_destination.html.markdown) |
| `alicloud_event_bridge_connection` | ✅ | Provides a Event Bridge Connection resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_connection.html.markdown) |
| `alicloud_event_bridge_event_bus` | ✅ | Provides a Event Bridge Event Bus resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_event_bus.html.markdown) |
| `alicloud_event_bridge_event_source` | ⚠️ 弃用 → `alicloud_event_bridge_event_source_v2` | Provides a Event Bridge Event Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_event_source.html.markdown) |
| `alicloud_event_bridge_event_source_v2` | ✅ | Provides a Event Bridge Event Source V2 resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_event_source_v2.html.markdown) |
| `alicloud_event_bridge_rule` | ✅ | Provides a Event Bridge Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_rule.html.markdown) |
| `alicloud_event_bridge_service_linked_role` | ✅ | Provides a Event Bridge Service Linked Role resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/event_bridge_service_linked_role.html.markdown) |

---

### Ros

**产品代码**: `ros`
**产品线分类**: 企业IT治理
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ros_change_set` | ✅ | Provides a ROS Change Set resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_change_set.html.markdown) |
| `alicloud_ros_stack` | ✅ | Provides a ROS Stack resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_stack.html.markdown) |
| `alicloud_ros_stack_group` | ✅ | Provides a ROS Stack Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_stack_group.html.markdown) |
| `alicloud_ros_stack_instance` | ✅ | Provides a ROS Stack Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_stack_instance.html.markdown) |
| `alicloud_ros_template` | ✅ | Provides a ROS Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_template.html.markdown) |
| `alicloud_ros_template_scratch` | ✅ | Provides a ROS Template Scratch resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ros_template_scratch.html.markdown) |

---

### Service Catalog

**产品代码**: `service_catalog`
**产品线分类**: 企业IT治理
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_service_catalog_portfolio` | ✅ | Provides a Service Catalog Portfolio resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_portfolio.html.markdown) |
| `alicloud_service_catalog_principal_portfolio_association` | ✅ | Provides a Service Catalog Principal Portfolio Association resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_principal_portfolio_association.html.markdown) |
| `alicloud_service_catalog_product` | ✅ | Provides a Service Catalog Product resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_product.html.markdown) |
| `alicloud_service_catalog_product_portfolio_association` | ✅ | Provides a Service Catalog Product Portfolio Association resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_product_portfolio_association.html.markdown) |
| `alicloud_service_catalog_product_version` | ✅ | Provides a Service Catalog Product Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_product_version.html.markdown) |
| `alicloud_service_catalog_provisioned_product` | ✅ | Provides a Service Catalog Provisioned Product resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_catalog_provisioned_product.html.markdown) |

---

### Actiontrail

**产品代码**: `actiontrail`
**产品线分类**: 企业IT治理
**资源数**: 5 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_actiontrail` | ⚠️ 弃用 → `alicloud_actiontrail_trail` | Provides a new resource to manage [Action Trail](https://www.alibabacloud.com... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail.html.markdown) |
| `alicloud_actiontrail_advanced_query_template` | ✅ | Provides a Actiontrail Advanced Query Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_advanced_query_template.html.markdown) |
| `alicloud_actiontrail_global_events_storage_region` | ✅ | Provides a Global events storage region resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_global_events_storage_region.html.markdown) |
| `alicloud_actiontrail_history_delivery_job` | ✅ | Provides a Action Trail History Delivery Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_history_delivery_job.html.markdown) |
| `alicloud_actiontrail_trail` | ✅ | Provides a Actiontrail Trail resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/actiontrail_trail.html.markdown) |

---

### Quotas

**产品代码**: `quotas`
**产品线分类**: 企业IT治理
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_quotas_quota_alarm` | ✅ | Provides a Quotas Quota Alarm resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_quota_alarm.html.markdown) |
| `alicloud_quotas_quota_application` | ✅ | Provides a Quotas Quota Application resource. Details of Quota Application. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_quota_application.html.markdown) |
| `alicloud_quotas_template_applications` | ✅ | Provides a Quotas Template Applications resource. Template Batch Application. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_template_applications.html.markdown) |
| `alicloud_quotas_template_quota` | ✅ | Provides a Quotas Template Quota resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_template_quota.html.markdown) |
| `alicloud_quotas_template_service` | ✅ | Provides a Quotas Template Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quotas_template_service.html.markdown) |

---

### Tag

**产品代码**: `tag`
**产品线分类**: 企业IT治理
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_tag_associated_rule` | ✅ | Provides a TAG Associated Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_associated_rule.html.markdown) |
| `alicloud_tag_meta_tag` | ✅ | Provides a Tag Meta Tag resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_meta_tag.html.markdown) |
| `alicloud_tag_policy` | ✅ | Provides a TAG Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_policy.html.markdown) |
| `alicloud_tag_policy_attachment` | ✅ | Provides a Tag Policy Attachment resource to attaches a policy to an object. ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tag_policy_attachment.html.markdown) |

---

### Governance

**产品代码**: `governance`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_governance_account` | ✅ | Provides a Governance Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/governance_account.html.markdown) |
| `alicloud_governance_baseline` | ✅ | Provides a Governance Baseline resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/governance_baseline.html.markdown) |

---

### Ims

**产品代码**: `ims`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ims_oidc_provider` | ✅ | Provides a IMS Oidc Provider resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ims_oidc_provider.html.markdown) |

---

### Dbaudit

**产品代码**: `dbaudit`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_yundun_dbaudit_instance` | ✅ | Cloud DBaudit instance resource ("Yundun_dbaudit" is the short term of this p... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/yundun_dbaudit_instance.html.markdown) |

---

## 存储 (7 个产品)

### Object Storage Service

**产品代码**: `oss`
**产品线分类**: 存储
**资源数**: 28

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_oss_access_point` | ✅ | Provides a OSS Access Point resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_access_point.html.markdown) |
| `alicloud_oss_account_public_access_block` | ✅ | Provides a OSS Account Public Access Block resource. Blocking public access a... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_account_public_access_block.html.markdown) |
| `alicloud_oss_bucket` | ✅ | Provides a resource to create a oss bucket and set its attribution. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket.html.markdown) |
| `alicloud_oss_bucket_access_monitor` | ✅ | Provides a OSS Bucket Access Monitor resource. Enables or disables access tra... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_access_monitor.html.markdown) |
| `alicloud_oss_bucket_acl` | ✅ | Provides a OSS Bucket Acl resource. The Access Control List (ACL) of a specif... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_acl.html.markdown) |
| `alicloud_oss_bucket_archive_direct_read` | ✅ | Provides a OSS Bucket Archive Direct Read resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_archive_direct_read.html.markdown) |
| `alicloud_oss_bucket_cname` | ✅ | Provides a OSS Bucket Cname resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_cname.html.markdown) |
| `alicloud_oss_bucket_cname_token` | ✅ | Provides a OSS Bucket Cname Token resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_cname_token.html.markdown) |
| `alicloud_oss_bucket_cors` | ✅ | Provides a OSS Bucket Cors resource. Cross-Origin Resource Sharing (CORS) all... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_cors.html.markdown) |
| `alicloud_oss_bucket_data_redundancy_transition` | ✅ | Provides a OSS Bucket Data Redundancy Transition resource. Create a storage r... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_data_redundancy_transition.html.markdown) |
| `alicloud_oss_bucket_https_config` | ✅ | Provides a OSS Bucket Https Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_https_config.html.markdown) |
| `alicloud_oss_bucket_logging` | ✅ | Provides a OSS Bucket Logging resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_logging.html.markdown) |
| `alicloud_oss_bucket_meta_query` | ✅ | Provides a OSS Bucket Meta Query resource. Enables the metadata management fe... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_meta_query.html.markdown) |
| `alicloud_oss_bucket_object` | ✅ | Provides a resource to put a object(content or file) to a oss bucket. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_object.html.markdown) |
| `alicloud_oss_bucket_overwrite_config` | ✅ | Provides a OSS Bucket Overwrite Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_overwrite_config.html.markdown) |
| `alicloud_oss_bucket_policy` | ✅ | Provides a OSS Bucket Policy resource.  Authorization policy of a bucket. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_policy.html.markdown) |
| `alicloud_oss_bucket_public_access_block` | ✅ | Provides a OSS Bucket Public Access Block resource. Blocking public access at... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_public_access_block.html.markdown) |
| `alicloud_oss_bucket_referer` | ✅ | Provides a OSS Bucket Referer resource. Bucket Referer configuration (Hotlink... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_referer.html.markdown) |
| `alicloud_oss_bucket_replication` | ✅ | Provides an independent replication configuration resource for OSS bucket. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_replication.html.markdown) |
| `alicloud_oss_bucket_request_payment` | ✅ | Provides a OSS Bucket Request Payment resource. Whether to enable pay-by-requ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_request_payment.html.markdown) |
| `alicloud_oss_bucket_response_header` | ✅ | Provides a OSS Bucket Response Header resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_response_header.html.markdown) |
| `alicloud_oss_bucket_server_side_encryption` | ✅ | Provides a OSS Bucket Server Side Encryption resource. Server-side encryption... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_server_side_encryption.html.markdown) |
| `alicloud_oss_bucket_style` | ✅ | Provides a OSS Bucket Style resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_style.html.markdown) |
| `alicloud_oss_bucket_transfer_acceleration` | ✅ | Provides a OSS Bucket Transfer Acceleration resource. Transfer acceleration c... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_transfer_acceleration.html.markdown) |
| `alicloud_oss_bucket_user_defined_log_fields` | ✅ | Provides a OSS Bucket User Defined Log Fields resource. Used to personalize t... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_user_defined_log_fields.html.markdown) |
| `alicloud_oss_bucket_versioning` | ✅ | Provides a OSS Bucket Versioning resource. Configures the versioning state fo... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_versioning.html.markdown) |
| `alicloud_oss_bucket_website` | ✅ | Provides a OSS Bucket Website resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_website.html.markdown) |
| `alicloud_oss_bucket_worm` | ✅ | Provides a OSS Bucket Worm resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/oss_bucket_worm.html.markdown) |

---

### Hbr

**产品代码**: `hbr`
**产品线分类**: 存储
**资源数**: 15 | **已弃用**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_hbr_cross_account` | ✅ | Provides a Hybrid Backup Recovery (HBR) Cross Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_cross_account.html.markdown) |
| `alicloud_hbr_ecs_backup_client` | ✅ | Provides a Hybrid Backup Recovery (HBR) Ecs Backup Client resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_ecs_backup_client.html.markdown) |
| `alicloud_hbr_ecs_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | Provides a HBR Ecs Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_ecs_backup_plan.html.markdown) |
| `alicloud_hbr_hana_backup_client` | ✅ | Provides a Hybrid Backup Recovery (HBR) Hana Backup Client resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_hana_backup_client.html.markdown) |
| `alicloud_hbr_hana_backup_plan` | ✅ | Provides a Hybrid Backup Recovery (HBR) Hana Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_hana_backup_plan.html.markdown) |
| `alicloud_hbr_hana_instance` | ✅ | Provides a Hybrid Backup Recovery (HBR) Hana Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_hana_instance.html.markdown) |
| `alicloud_hbr_nas_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | Provides a HBR Nas Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_nas_backup_plan.html.markdown) |
| `alicloud_hbr_oss_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | Provides a HBR Oss Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_oss_backup_plan.html.markdown) |
| `alicloud_hbr_ots_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | Provides a HBR Ots Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_ots_backup_plan.html.markdown) |
| `alicloud_hbr_policy` | ✅ | Provides a Hybrid Backup Recovery (HBR) Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_policy.html.markdown) |
| `alicloud_hbr_policy_binding` | ✅ | Provides a Hybrid Backup Recovery (HBR) Policy Binding resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_policy_binding.html.markdown) |
| `alicloud_hbr_replication_vault` | ✅ | Provides a Hybrid Backup Recovery (HBR) Replication Vault resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_replication_vault.html.markdown) |
| `alicloud_hbr_restore_job` | ✅ | Provides a Hybrid Backup Recovery (HBR) Restore Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_restore_job.html.markdown) |
| `alicloud_hbr_server_backup_plan` | ⚠️ 弃用 → `alicloud_hbr_policy` | Provides a Hybrid Backup Recovery (HBR) Server Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_server_backup_plan.html.markdown) |
| `alicloud_hbr_vault` | ✅ | Provides a Hybrid Backup Recovery (HBR) Vault resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbr_vault.html.markdown) |

---

### Nas

**产品代码**: `nas`
**产品线分类**: 存储
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_nas_access_group` | ✅ | Provides a File Storage (NAS) Access Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_access_group.html.markdown) |
| `alicloud_nas_access_point` | ✅ | Provides a File Storage (NAS) Access Point resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_access_point.html.markdown) |
| `alicloud_nas_access_rule` | ✅ | Provides a NAS Access Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_access_rule.html.markdown) |
| `alicloud_nas_auto_snapshot_policy` | ✅ | Provides a NAS Auto Snapshot Policy resource. Automatic snapshot policy. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_auto_snapshot_policy.html.markdown) |
| `alicloud_nas_data_flow` | ✅ | Provides a File Storage (NAS) Data Flow resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_data_flow.html.markdown) |
| `alicloud_nas_file_system` | ✅ | Provides a File Storage (NAS) File System resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_file_system.html.markdown) |
| `alicloud_nas_fileset` | ✅ | Provides a File Storage (NAS) Fileset resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_fileset.html.markdown) |
| `alicloud_nas_lifecycle_policy` | ✅ | Provides a File Storage (NAS) Lifecycle Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_lifecycle_policy.html.markdown) |
| `alicloud_nas_mount_target` | ✅ | Provides a File Storage (NAS) Mount Target resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_mount_target.html.markdown) |
| `alicloud_nas_protocol_mount_target` | ✅ | Provides a File Storage (NAS) Protocol Mount Target resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_protocol_mount_target.html.markdown) |
| `alicloud_nas_protocol_service` | ✅ | Provides a File Storage (NAS) Protocol Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_protocol_service.html.markdown) |
| `alicloud_nas_recycle_bin` | ✅ | Provides a File Storage (NAS) Recycle Bin resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_recycle_bin.html.markdown) |
| `alicloud_nas_smb_acl_attachment` | ✅ | Provides a Nas Smb Acl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_smb_acl_attachment.html.markdown) |
| `alicloud_nas_snapshot` | ✅ | Provides a File Storage (NAS) Snapshot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/nas_snapshot.html.markdown) |

---

### Ebs

**产品代码**: `ebs`
**产品线分类**: 存储
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ebs_dedicated_block_storage_cluster` | ✅ | Provides a Ebs Dedicated Block Storage Cluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_dedicated_block_storage_cluster.html.markdown) |
| `alicloud_ebs_disk_replica_group` | ✅ | Provides a Elastic Block Storage(EBS) Disk Replica Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_disk_replica_group.html.markdown) |
| `alicloud_ebs_disk_replica_pair` | ✅ | Provides a Elastic Block Storage(EBS) Disk Replica Pair resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_disk_replica_pair.html.markdown) |
| `alicloud_ebs_enterprise_snapshot_policy` | ✅ | Provides a EBS Enterprise Snapshot Policy resource. enterprise snapshot policy. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_enterprise_snapshot_policy.html.markdown) |
| `alicloud_ebs_enterprise_snapshot_policy_attachment` | ✅ | Provides a EBS Enterprise Snapshot Policy Attachment resource. Enterprise-lev... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_enterprise_snapshot_policy_attachment.html.markdown) |
| `alicloud_ebs_replica_group_drill` | ✅ | Provides a EBS Replica Group Drill resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_replica_group_drill.html.markdown) |
| `alicloud_ebs_replica_pair_drill` | ✅ | Provides a EBS Replica Pair Drill resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_replica_pair_drill.html.markdown) |
| `alicloud_ebs_solution_instance` | ✅ | Provides a EBS Solution Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ebs_solution_instance.html.markdown) |

---

### Redis Oss Compatible

**产品代码**: `redis_oss_compatible`
**产品线分类**: 存储
**资源数**: 7 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_kvstore_account` | ✅ | Provides a Tair (Redis OSS-Compatible) And Memcache (KVStore) Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_account.html.markdown) |
| `alicloud_kvstore_audit_log_config` | ✅ | Provides a Tair (Redis OSS-Compatible) And Memcache (KVStore) Audit Log Confi... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_audit_log_config.html.markdown) |
| `alicloud_kvstore_backup_policy` | ⚠️ 弃用 → `alicloud_kvstore_instance` | Provides a Backup Policy for Tair (Redis OSS-Compatible) And Memcache (KVStor... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_backup_policy.html.markdown) |
| `alicloud_kvstore_connection` | ✅ | Operate the public network ip of the specified resource. How to use it, see [... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_connection.html.markdown) |
| `alicloud_kvstore_instance` | ✅ | Provides  Tair (Redis OSS-Compatible) And Memcache (KVStore) Classic Instance... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/kvstore_instance.html.markdown) |
| `alicloud_redis_backup` | ✅ | Provides a Tair (Redis OSS-Compatible) And Memcache (KVStore) Backup resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/redis_backup.html.markdown) |
| `alicloud_redis_tair_instance` | ✅ | Provides a Tair (Redis OSS-Compatible) And Memcache (KVStore) Tair Instance r... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/redis_tair_instance.html.markdown) |

---

### Dbfs

**产品代码**: `dbfs`
**产品线分类**: 存储
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_dbfs_auto_snap_shot_policy` | ✅ | Provides a Dbfs Auto Snap Shot Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_auto_snap_shot_policy.html.markdown) |
| `alicloud_dbfs_instance` | ✅ | Provides a DBFS Dbfs Instance resource. An instance of a database file system... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_instance.html.markdown) |
| `alicloud_dbfs_instance_attachment` | ✅ | Provides a Database File System (DBFS) Instance Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_instance_attachment.html.markdown) |
| `alicloud_dbfs_service_linked_role` | ✅ | Using this data source can create Dbfs service-linked roles(SLR). Dbfs may ne... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_service_linked_role.html.markdown) |
| `alicloud_dbfs_snapshot` | ✅ | Provides a Database File System (DBFS) Snapshot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbfs_snapshot.html.markdown) |

---

### Dfs

**产品代码**: `dfs`
**产品线分类**: 存储
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_dfs_access_group` | ✅ | Provides a DFS Access Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_access_group.html.markdown) |
| `alicloud_dfs_access_rule` | ✅ | Provides a DFS Access Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_access_rule.html.markdown) |
| `alicloud_dfs_file_system` | ✅ | Provides a Apsara File Storage for HDFS (DFS) File System resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_file_system.html.markdown) |
| `alicloud_dfs_mount_point` | ✅ | Provides a Apsara File Storage for HDFS (DFS) Mount Point resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_mount_point.html.markdown) |
| `alicloud_dfs_vsc_mount_point` | ✅ | Provides a Apsara File Storage for HDFS (DFS) Vsc Mount Point resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dfs_vsc_mount_point.html.markdown) |

---

## 数据库 (19 个产品)

### Relational Database Service

**产品代码**: `rds`
**产品线分类**: 数据库
**资源数**: 25 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_db_account` | ⚠️ 弃用 → `alicloud_rds_account` | Provides an RDS account resource and used to manage databases. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_account.html.markdown) |
| `alicloud_db_account_privilege` | ✅ | Provides an RDS account privilege resource and used to grant several database... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_account_privilege.html.markdown) |
| `alicloud_db_backup_policy` | ✅ | Provides an RDS instance backup policy resource and used to configure instanc... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_backup_policy.html.markdown) |
| `alicloud_db_connection` | ✅ | Provides an RDS connection resource to allocate an Internet connection string... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_connection.html.markdown) |
| `alicloud_db_database` | ✅ | Provides a RDS Database resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_database.html.markdown) |
| `alicloud_db_instance` | ✅ | Provides an RDS instance resource. A DB instance is an isolated database envi... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_instance.html.markdown) |
| `alicloud_db_read_write_splitting_connection` | ✅ | Provides an RDS read write splitting connection resource to allocate an Intra... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_read_write_splitting_connection.html.markdown) |
| `alicloud_db_readonly_instance` | ✅ | Provides an RDS readonly instance resource, see [What is DB Readonly Instance... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/db_readonly_instance.html.markdown) |
| `alicloud_rds_account` | ✅ | Provides a RDS Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_account.html.markdown) |
| `alicloud_rds_backup` | ✅ | Provides a RDS Backup resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_backup.html.markdown) |
| `alicloud_rds_clone_db_instance` | ✅ | Provides an RDS Clone DB Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_clone_db_instance.html.markdown) |
| `alicloud_rds_custom` | ✅ | Provides a RDS Custom resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_custom.html.markdown) |
| `alicloud_rds_custom_deployment_set` | ✅ | Provides a RDS Custom Deployment Set resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_custom_deployment_set.html.markdown) |
| `alicloud_rds_custom_disk` | ✅ | Provides a RDS Custom Disk resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_custom_disk.html.markdown) |
| `alicloud_rds_db_instance_endpoint` | ✅ | Provide RDS cluster instance endpoint connection resources, see [What is RDS ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_instance_endpoint.html.markdown) |
| `alicloud_rds_db_instance_endpoint_address` | ✅ | Provide RDS cluster instance endpoint public connection resources. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_instance_endpoint_address.html.markdown) |
| `alicloud_rds_db_node` | ✅ | Provide RDS cluster instance to increase node resources, see [What is RDS DB ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_node.html.markdown) |
| `alicloud_rds_db_proxy` | ✅ | Information about RDS database exclusive agent and its usage, see [What is RD... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_proxy.html.markdown) |
| `alicloud_rds_db_proxy_public` | ✅ | Provides a RDS database proxy public network address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_db_proxy_public.html.markdown) |
| `alicloud_rds_ddr_instance` | ✅ | Provide RDS remote disaster recovery instance resources. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_ddr_instance.html.markdown) |
| `alicloud_rds_instance_cross_backup_policy` | ✅ | Provides an RDS instance emote disaster recovery strategy policy resource and... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_instance_cross_backup_policy.html.markdown) |
| `alicloud_rds_parameter_group` | ✅ | Provides a RDS Parameter Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_parameter_group.html.markdown) |
| `alicloud_rds_service_linked_role` | ✅ | Provides a RDS Service Linked Role. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_service_linked_role.html.markdown) |
| `alicloud_rds_upgrade_db_instance` | ✅ | Provides a RDS Upgrade DB Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_upgrade_db_instance.html.markdown) |
| `alicloud_rds_whitelist_template` | ✅ | Provide a whitelist template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_whitelist_template.html.markdown) |

---

### Gpdb

**产品代码**: `gpdb`
**产品线分类**: 数据库
**资源数**: 17 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_gpdb_account` | ✅ | Provides a GPDB Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_account.html.markdown) |
| `alicloud_gpdb_backup_policy` | ✅ | Provides a GPDB Backup Policy resource. Describe the instance backup strategy. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_backup_policy.html.markdown) |
| `alicloud_gpdb_connection` | ✅ | Provides a connection resource to allocate an Internet connection string for ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_connection.html.markdown) |
| `alicloud_gpdb_database` | ✅ | Provides a GPDB Database resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_database.html.markdown) |
| `alicloud_gpdb_db_instance_ip_array` | ✅ | Provides a GPDB DB Instance IP Array resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_db_instance_ip_array.html.markdown) |
| `alicloud_gpdb_db_instance_plan` | ✅ | Provides a AnalyticDB for PostgreSQL (GPDB) DB Instance Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_db_instance_plan.html.markdown) |
| `alicloud_gpdb_db_resource_group` | ✅ | Provides a AnalyticDB for PostgreSQL (GPDB) Db Resource Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_db_resource_group.html.markdown) |
| `alicloud_gpdb_elastic_instance` | ⚠️ 弃用 → `alicloud_gpdb_instance` | Provides a AnalyticDB for PostgreSQL instance resource which storage type is ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_elastic_instance.html.markdown) |
| `alicloud_gpdb_external_data_service` | ✅ | Provides a AnalyticDB for PostgreSQL (GPDB) External Data Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_external_data_service.html.markdown) |
| `alicloud_gpdb_hadoop_data_source` | ✅ | Provides a GPDB Hadoop Data Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_hadoop_data_source.html.markdown) |
| `alicloud_gpdb_instance` | ✅ | Provides a AnalyticDB for PostgreSQL instance resource supports replica set i... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_instance.html.markdown) |
| `alicloud_gpdb_jdbc_data_source` | ✅ | Provides a AnalyticDB for PostgreSQL (GPDB) Jdbc Data Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_jdbc_data_source.html.markdown) |
| `alicloud_gpdb_remote_adb_data_source` | ✅ | Provides a GPDB Remote ADB Data Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_remote_adb_data_source.html.markdown) |
| `alicloud_gpdb_streaming_data_service` | ✅ | Provides a AnalyticDB for PostgreSQL (GPDB) Streaming Data Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_streaming_data_service.html.markdown) |
| `alicloud_gpdb_streaming_data_source` | ✅ | Provides a GPDB Streaming Data Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_streaming_data_source.html.markdown) |
| `alicloud_gpdb_streaming_job` | ✅ | Provides a GPDB Streaming Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_streaming_job.html.markdown) |
| `alicloud_gpdb_supabase_project` | ✅ | Provides a AnalyticDB for PostgreSQL (GPDB) Supabase Project resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/gpdb_supabase_project.html.markdown) |

---

### Polardb

**产品代码**: `polardb`
**产品线分类**: 数据库
**资源数**: 16

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_polar_db_extension` | ✅ | Provides a Polar Db Extension resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polar_db_extension.html.markdown) |
| `alicloud_polardb_account` | ✅ | Provides a Polar Db Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_account.html.markdown) |
| `alicloud_polardb_account_privilege` | ✅ | Provides a PolarDB account privilege resource and used to grant several datab... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_account_privilege.html.markdown) |
| `alicloud_polardb_backup_policy` | ✅ | Provides a PolarDB cluster backup policy resource and used to configure clust... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_backup_policy.html.markdown) |
| `alicloud_polardb_cluster` | ✅ | Provides an PolarDB cluster resource. An PolarDB cluster is an isolated database | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_cluster.html.markdown) |
| `alicloud_polardb_cluster_endpoint` | ✅ | Provides a PolarDB endpoint resource to manage cluster endpoint of PolarDB cl... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_cluster_endpoint.html.markdown) |
| `alicloud_polardb_database` | ✅ | Provides a Polar Db Database resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_database.html.markdown) |
| `alicloud_polardb_endpoint` | ✅ | Provides a PolarDB endpoint resource to manage custom endpoint of PolarDB clu... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_endpoint.html.markdown) |
| `alicloud_polardb_endpoint_address` | ✅ | Provides a PolarDB endpoint address resource to allocate an Internet endpoint... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_endpoint_address.html.markdown) |
| `alicloud_polardb_global_database_network` | ✅ | Provides a PolarDB Global Database Network resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_global_database_network.html.markdown) |
| `alicloud_polardb_global_security_ip_group` | ✅ | Provides a Polardb Global Security Ip Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_global_security_ip_group.html.markdown) |
| `alicloud_polardb_parameter_group` | ✅ | Provides a Polar Db Parameter Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_parameter_group.html.markdown) |
| `alicloud_polardb_primary_endpoint` | ✅ | Provides a PolarDB endpoint resource to manage primary endpoint of PolarDB cl... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_primary_endpoint.html.markdown) |
| `alicloud_polardb_zonal_account` | ✅ | Provides a PolarDB Zonal account resource and used to manage databases. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_zonal_account.html.markdown) |
| `alicloud_polardb_zonal_db_cluster` | ✅ | Provides an PolarDB zonal cluster resource. An PolarDB zonal cluster is an is... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_zonal_db_cluster.html.markdown) |
| `alicloud_polardb_zonal_endpoint` | ✅ | Provides a PolarDB Zonal endpoint resource to manage custom endpoint of Polar... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/polardb_zonal_endpoint.html.markdown) |

---

### MongoDB

**产品代码**: `mongodb`
**产品线分类**: 数据库
**资源数**: 12 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_mongodb_account` | ✅ | Provides a Mongodb Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_account.html.markdown) |
| `alicloud_mongodb_audit_policy` | ✅ | Provides a Mongodb Audit Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_audit_policy.html.markdown) |
| `alicloud_mongodb_global_security_ip_group` | ✅ | Provides a Mongodb Global Security IP Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_global_security_ip_group.html.markdown) |
| `alicloud_mongodb_instance` | ✅ | Provides a MongoDB instance resource supports replica set instances only. the... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_instance.html.markdown) |
| `alicloud_mongodb_node` | ✅ | Provides a Mongodb Node resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_node.html.markdown) |
| `alicloud_mongodb_private_srv_network_address` | ✅ | Provides a Mongodb Private Srv Network Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_private_srv_network_address.html.markdown) |
| `alicloud_mongodb_public_network_address` | ✅ | Provides an Alicloud MongoDB public network address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_public_network_address.html.markdown) |
| `alicloud_mongodb_replica_set_role` | ✅ | Provides an Alicloud MongoDB replica set role resource to modify the connecti... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_replica_set_role.html.markdown) |
| `alicloud_mongodb_serverless_instance` | ⚠️ 弃用 | Provides a MongoDB Serverless Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_serverless_instance.html.markdown) |
| `alicloud_mongodb_sharding_instance` | ✅ | Provides a MongoDB Sharding Instance resource supports replica set instances ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_sharding_instance.html.markdown) |
| `alicloud_mongodb_sharding_network_private_address` | ✅ | Provides a MongoDB Sharding Network Private Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_sharding_network_private_address.html.markdown) |
| `alicloud_mongodb_sharding_network_public_address` | ✅ | Provides a MongoDB Sharding Network Public Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mongodb_sharding_network_public_address.html.markdown) |

---

### Adb

**产品代码**: `adb`
**产品线分类**: 数据库
**资源数**: 8 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_adb_account` | ✅ | Provides a AnalyticDB for MySQL (ADB) Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_account.html.markdown) |
| `alicloud_adb_backup_policy` | ✅ | Provides a [ADB](https://www.alibabacloud.com/help/en/analyticdb-for-mysql/la... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_backup_policy.html.markdown) |
| `alicloud_adb_cluster` | ⚠️ 弃用 → `alicloud_adb_db_cluster` | Provides a ADB cluster resource. An ADB cluster is an isolated database | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_cluster.html.markdown) |
| `alicloud_adb_connection` | ✅ | Provides an ADB connection resource to allocate an Internet connection string... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_connection.html.markdown) |
| `alicloud_adb_db_cluster` | ✅ | Provides a AnalyticDB for MySQL (ADB) DBCluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_db_cluster.html.markdown) |
| `alicloud_adb_db_cluster_lake_version` | ✅ | Provides a AnalyticDB for MySQL (ADB) DB Cluster Lake Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_db_cluster_lake_version.html.markdown) |
| `alicloud_adb_lake_account` | ✅ | Provides a ADB Lake Account resource. Account of the DBClusterLakeVesion. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_lake_account.html.markdown) |
| `alicloud_adb_resource_group` | ✅ | Provides a AnalyticDB for MySQL (ADB) Resource Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/adb_resource_group.html.markdown) |

---

### Dts

**产品代码**: `dts`
**产品线分类**: 数据库
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_dts_consumer_channel` | ✅ | Provides a DTS Consumer Channel resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_consumer_channel.html.markdown) |
| `alicloud_dts_instance` | ✅ | Provides a Dts Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_instance.html.markdown) |
| `alicloud_dts_job_monitor_rule` | ✅ | Provides a DTS Job Monitor Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_job_monitor_rule.html.markdown) |
| `alicloud_dts_migration_instance` | ✅ | Provides a DTS Migration Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_migration_instance.html.markdown) |
| `alicloud_dts_migration_job` | ✅ | Provides a DTS Migration Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_migration_job.html.markdown) |
| `alicloud_dts_subscription_job` | ✅ | Provides a DTS Subscription Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_subscription_job.html.markdown) |
| `alicloud_dts_synchronization_instance` | ✅ | Provides a DTS Synchronization Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_synchronization_instance.html.markdown) |
| `alicloud_dts_synchronization_job` | ✅ | Provides a DTS Synchronization Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dts_synchronization_job.html.markdown) |

---

### Dms Enterprise

**产品代码**: `dms_enterprise`
**产品线分类**: 数据库
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_dms_enterprise_authority_template` | ✅ | Provides a DMS Enterprise Authority Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_authority_template.html.markdown) |
| `alicloud_dms_enterprise_instance` | ✅ | Provides a DMS Enterprise Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_instance.html.markdown) |
| `alicloud_dms_enterprise_logic_database` | ✅ | Provides a DMS Enterprise Logic Database resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_logic_database.html.markdown) |
| `alicloud_dms_enterprise_proxy` | ✅ | Provides a DMS Enterprise Proxy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_proxy.html.markdown) |
| `alicloud_dms_enterprise_proxy_access` | ✅ | Provides a DMS Enterprise Proxy Access resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_proxy_access.html.markdown) |
| `alicloud_dms_enterprise_user` | ✅ | Provides a DMS Enterprise User resource. For information about Alidms Enterpr... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_user.html.markdown) |
| `alicloud_dms_enterprise_workspace` | ✅ | Provides a DMS Enterprise Workspace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_enterprise_workspace.html.markdown) |

---

### Ots

**产品代码**: `ots`
**产品线分类**: 数据库
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ots_instance` | ✅ | This resource will help you to manager a [Table Store](https://www.alibabaclo... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_instance.html.markdown) |
| `alicloud_ots_instance_attachment` | ✅ | This resource will help you to bind a VPC to an OTS instance. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_instance_attachment.html.markdown) |
| `alicloud_ots_search_index` | ✅ | Provides an OTS search index resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_search_index.html.markdown) |
| `alicloud_ots_secondary_index` | ✅ | Provides an OTS secondary index resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_secondary_index.html.markdown) |
| `alicloud_ots_table` | ✅ | Provides an OTS table resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_table.html.markdown) |
| `alicloud_ots_tunnel` | ✅ | Provides an OTS tunnel resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ots_tunnel.html.markdown) |

---

### Cassandra

**产品代码**: `cassandra`
**产品线分类**: 数据库
**资源数**: 3 | **已弃用**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cassandra_backup_plan` | ⚠️ 弃用 | Provides a Cassandra Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cassandra_backup_plan.html.markdown) |
| `alicloud_cassandra_cluster` | ⚠️ 弃用 | Provides a Cassandra cluster resource supports replica set clusters only. The... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cassandra_cluster.html.markdown) |
| `alicloud_cassandra_data_center` | ⚠️ 弃用 | Provides a Cassandra dataCenter resource supports replica set dataCenters onl... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cassandra_data_center.html.markdown) |

---

### Lindorm

**产品代码**: `lindorm`
**产品线分类**: 数据库
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_lindorm_instance` | ✅ | Provides a Lindorm Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/lindorm_instance.html.markdown) |
| `alicloud_lindorm_instance_v2` | ✅ | Provides a Lindorm Instance V2 resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/lindorm_instance_v2.html.markdown) |
| `alicloud_lindorm_public_network` | ✅ | Provides a Lindorm Public Network resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/lindorm_public_network.html.markdown) |

---

### Drds

**产品代码**: `drds`
**产品线分类**: 数据库
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_drds_instance` | ✅ | Distributed Relational Database Service (DRDS) is a lightweight (stateless), ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/drds_instance.html.markdown) |
| `alicloud_drds_polardbx_instance` | ✅ | Provides a Distributed Relational Database Service (DRDS) Polardbx Instance r... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/drds_polardbx_instance.html.markdown) |

---

### Selectdb

**产品代码**: `selectdb`
**产品线分类**: 数据库
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_selectdb_db_cluster` | ✅ | Provides a SelectDB DBCluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/selectdb_db_cluster.html.markdown) |
| `alicloud_selectdb_db_instance` | ✅ | Provides a SelectDB DBInstance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/selectdb_db_instance.html.markdown) |

---

### Dbs

**产品代码**: `dbs`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_dbs_backup_plan` | ✅ | Provides a DBS Backup Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dbs_backup_plan.html.markdown) |

---

### Dms

**产品代码**: `dms`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_dms_airflow` | ✅ | Provides a Dms Airflow resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dms_airflow.html.markdown) |

---

### Graph Database

**产品代码**: `graph_database`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_graph_database_db_instance` | ✅ | Provides a Graph Database Db Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/graph_database_db_instance.html.markdown) |

---

### Hbase

**产品代码**: `hbase`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_hbase_instance` | ✅ | Provides a HBase instance resource supports replica set instances only. The H... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hbase_instance.html.markdown) |

---

### Milvus

**产品代码**: `milvus`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_milvus_instance` | ✅ | Provides a Milvus Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/milvus_instance.html.markdown) |

---

### Rds Ai

**产品代码**: `rds_ai`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_rds_ai_instance` | ✅ | Provides a Rds Ai Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rds_ai_instance.html.markdown) |

---

### Tsdb

**产品代码**: `tsdb`
**产品线分类**: 数据库
**资源数**: 1 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_tsdb_instance` | ⚠️ 弃用 | Provides a Time Series Database (TSDB) Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/tsdb_instance.html.markdown) |

---

## 云通信 (5 个产品)

### Alikafka

**产品代码**: `alikafka`
**产品线分类**: 云通信
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_alikafka_consumer_group` | ✅ | Provides a Ali Kafka Consumer Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_consumer_group.html.markdown) |
| `alicloud_alikafka_instance` | ✅ | Provides an AliKafka instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_instance.html.markdown) |
| `alicloud_alikafka_instance_allowed_ip_attachment` | ✅ | Provides a AliKafka Instance Allowed Ip Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_instance_allowed_ip_attachment.html.markdown) |
| `alicloud_alikafka_sasl_acl` | ✅ | Provides a Alikafka Sasl Acl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_sasl_acl.html.markdown) |
| `alicloud_alikafka_sasl_user` | ✅ | Provides an AliKafka Sasl User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_sasl_user.html.markdown) |
| `alicloud_alikafka_scheduled_scaling_rule` | ✅ | Provides a Alikafka Scheduled Scaling Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_scheduled_scaling_rule.html.markdown) |
| `alicloud_alikafka_topic` | ✅ | Provides a Alikafka Topic resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/alikafka_topic.html.markdown) |

---

### Amqp

**产品代码**: `amqp`
**产品线分类**: 云通信
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_amqp_binding` | ✅ | Provides a RabbitMQ (AMQP) Binding resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_binding.html.markdown) |
| `alicloud_amqp_exchange` | ✅ | Provides a RabbitMQ (AMQP) Exchange resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_exchange.html.markdown) |
| `alicloud_amqp_instance` | ✅ | Provides a RabbitMQ (AMQP) Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_instance.html.markdown) |
| `alicloud_amqp_queue` | ✅ | Provides a RabbitMQ (AMQP) Queue resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_queue.html.markdown) |
| `alicloud_amqp_static_account` | ✅ | Provides a Amqp Static Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_static_account.html.markdown) |
| `alicloud_amqp_virtual_host` | ✅ | Amqp Virtual Host. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/amqp_virtual_host.html.markdown) |

---

### Rocketmq

**产品代码**: `rocketmq`
**产品线分类**: 云通信
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_rocketmq_account` | ✅ | Provides a RocketMQ Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_account.html.markdown) |
| `alicloud_rocketmq_acl` | ✅ | Provides a RocketMQ Acl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_acl.html.markdown) |
| `alicloud_rocketmq_consumer_group` | ✅ | Provides a RocketMQ Consumer Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_consumer_group.html.markdown) |
| `alicloud_rocketmq_instance` | ✅ | Provides a RocketMQ Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_instance.html.markdown) |
| `alicloud_rocketmq_topic` | ✅ | Provides a RocketMQ Topic resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/rocketmq_topic.html.markdown) |

---

### Ons

**产品代码**: `ons`
**产品线分类**: 云通信
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ons_group` | ✅ | Provides an ONS group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ons_group.html.markdown) |
| `alicloud_ons_instance` | ✅ | Provides an ONS instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ons_instance.html.markdown) |
| `alicloud_ons_topic` | ✅ | Provides an ONS topic resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ons_topic.html.markdown) |

---

### Sms

**产品代码**: `sms`
**产品线分类**: 云通信
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_sms_short_url` | ✅ | Provides a SMS Short Url resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sms_short_url.html.markdown) |

---

## 视频云 (2 个产品)

### Live

**产品代码**: `live`
**产品线分类**: 视频云
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_live_caster` | ✅ | Provides a Live Caster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/live_caster.html.markdown) |
| `alicloud_live_domain` | ✅ | Provides a Live Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/live_domain.html.markdown) |

---

### Vod

**产品代码**: `vod`
**产品线分类**: 视频云
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_vod_domain` | ✅ | Provides a VOD Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vod_domain.html.markdown) |
| `alicloud_vod_editing_project` | ✅ | Provides a VOD Editing Project resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/vod_editing_project.html.markdown) |

---

## 云原生 (13 个产品)

### Auto Scaling

**产品代码**: `auto_scaling`
**产品线分类**: 云原生
**资源数**: 15 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ess_alarm` | ✅ | Provides a ESS alarm task resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_alarm.html.markdown) |
| `alicloud_ess_alb_server_group_attachment` | ✅ | Attaches/Detaches alb server group to a specified scaling group. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_alb_server_group_attachment.html.markdown) |
| `alicloud_ess_attachment` | ✅ | Attaches several ECS instances to a specified scaling group or remove them fr... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_attachment.html.markdown) |
| `alicloud_ess_eci_scaling_configuration` | ✅ | Provides a ESS eci scaling configuration resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_eci_scaling_configuration.html.markdown) |
| `alicloud_ess_instance_refresh` | ✅ | Provides a ESS instance refresh resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_instance_refresh.html.markdown) |
| `alicloud_ess_lifecycle_hook` | ✅ | Provides a ESS lifecycle hook resource. More about Ess lifecycle hook, see [L... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_lifecycle_hook.html.markdown) |
| `alicloud_ess_notification` | ✅ | Provides a ESS notification resource. More about Ess notification, see [Autos... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_notification.html.markdown) |
| `alicloud_ess_scaling_configuration` | ✅ | Provides a ESS scaling configuration resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scaling_configuration.html.markdown) |
| `alicloud_ess_scaling_group` | ✅ | Provides a ESS scaling group resource which is a collection of ECS instances ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scaling_group.html.markdown) |
| `alicloud_ess_scaling_rule` | ✅ | Provides a ESS scaling rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scaling_rule.html.markdown) |
| `alicloud_ess_scalinggroup_vserver_groups` | ✅ | Attaches/Detaches vserver groups to a specified scaling group. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scalinggroup_vserver_groups.html.markdown) |
| `alicloud_ess_schedule` | ⚠️ 弃用 → `alicloud_ess_scheduled_task` | Ess Schedule | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_schedule.html.markdown) |
| `alicloud_ess_scheduled_task` | ✅ | Provides a ESS schedule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_scheduled_task.html.markdown) |
| `alicloud_ess_server_group_attachment` | ✅ | Attaches/Detaches server group to a specified scaling group. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_server_group_attachment.html.markdown) |
| `alicloud_ess_suspend_process` | ✅ | Suspend/Resume processes to a specified scaling group. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ess_suspend_process.html.markdown) |

---

### Cr

**产品代码**: `cr`
**产品线分类**: 云原生
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cr_chain` | ✅ | Provides a CR Chain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_chain.html.markdown) |
| `alicloud_cr_chart_namespace` | ✅ | Provides a CR Chart Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_chart_namespace.html.markdown) |
| `alicloud_cr_chart_repository` | ✅ | Provides a CR Chart Repository resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_chart_repository.html.markdown) |
| `alicloud_cr_ee_instance` | ✅ | Provides a CR Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_instance.html.markdown) |
| `alicloud_cr_ee_namespace` | ✅ | Provides a Container Registry Enterprise Edition Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_namespace.html.markdown) |
| `alicloud_cr_ee_repo` | ✅ | Provides a Container Registry Enterprise Edition Repository resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_repo.html.markdown) |
| `alicloud_cr_ee_sync_rule` | ✅ | Provides a Container Registry Sync Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_ee_sync_rule.html.markdown) |
| `alicloud_cr_endpoint_acl_policy` | ✅ | Provides a CR Endpoint Acl Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_endpoint_acl_policy.html.markdown) |
| `alicloud_cr_namespace` | ✅ | This resource will help you to manager Container Registry namespaces, see [Wh... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_namespace.html.markdown) |
| `alicloud_cr_repo` | ✅ | This resource will help you to manager Container Registry repositories, see [... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_repo.html.markdown) |
| `alicloud_cr_scan_rule` | ✅ | Provides a CR Scan Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_scan_rule.html.markdown) |
| `alicloud_cr_storage_domain_routing_rule` | ✅ | Provides a CR Storage Domain Routing Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_storage_domain_routing_rule.html.markdown) |
| `alicloud_cr_vpc_endpoint_linked_vpc` | ✅ | Provides a CR Vpc Endpoint Linked Vpc resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cr_vpc_endpoint_linked_vpc.html.markdown) |

---

### Edas

**产品代码**: `edas`
**产品线分类**: 云原生
**资源数**: 11

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_edas_application` | ✅ | Creates an EDAS ecs application on EDAS, see [What is EDAS Application](https... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_application.html.markdown) |
| `alicloud_edas_application_deployment` | ✅ | Deploys applications on EDAS, see [What is EDAS Application Deployment](https... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_application_deployment.html.markdown) |
| `alicloud_edas_application_scale` | ✅ | This operation is provided to scale out an EDAS application, see [What is EDA... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_application_scale.html.markdown) |
| `alicloud_edas_cluster` | ✅ | Provides an EDAS cluster resource, see [What is EDAS Cluster](https://www.ali... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_cluster.html.markdown) |
| `alicloud_edas_deploy_group` | ✅ | Provides an EDAS deploy group resource, see [What is EDAS Deploy Group](https... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_deploy_group.html.markdown) |
| `alicloud_edas_instance_cluster_attachment` | ✅ | Provides an EDAS instance cluster attachment resource, see [What is EDAS Inst... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_instance_cluster_attachment.html.markdown) |
| `alicloud_edas_k8s_application` | ✅ | Create an EDAS k8s application.For information about EDAS K8s Application and... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_k8s_application.html.markdown) |
| `alicloud_edas_k8s_cluster` | ✅ | Provides an EDAS K8s cluster resource. For information about EDAS K8s Cluster... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_k8s_cluster.html.markdown) |
| `alicloud_edas_k8s_slb_attachment` | ✅ | Binds SLBs to an EDAS k8s application. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_k8s_slb_attachment.html.markdown) |
| `alicloud_edas_namespace` | ✅ | Provides a EDAS Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_namespace.html.markdown) |
| `alicloud_edas_slb_attachment` | ✅ | Binds SLB to an EDAS application. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/edas_slb_attachment.html.markdown) |

---

### Container Service for Kubernetes

**产品代码**: `ack`
**产品线分类**: 云原生
**资源数**: 10 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cs_autoscaling_config` | ✅ | This resource will help you configure auto scaling for the kubernetes cluster... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_autoscaling_config.html.markdown) |
| `alicloud_cs_edge_kubernetes` | ✅ | This resource will help you to manage a Edge Kubernetes Cluster in Alibaba Cl... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_edge_kubernetes.html.markdown) |
| `alicloud_cs_kubernetes` | ✅ | This resource will help you to manage a Kubernetes Cluster in Alibaba Cloud K... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes.html.markdown) |
| `alicloud_cs_kubernetes_addon` | ✅ | This resource will help you to manage addon in Kubernetes Cluster, see [What ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_addon.html.markdown) |
| `alicloud_cs_kubernetes_autoscaler` | ⚠️ 弃用 → `alicloud_cs_kubernetes_autoscaler` | This resource will help you to manager cluster-autoscaler in Kubernetes Cluster. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_autoscaler.html.markdown) |
| `alicloud_cs_kubernetes_node_pool` | ✅ | Provides a Container Service for Kubernetes (ACK) Nodepool resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_node_pool.html.markdown) |
| `alicloud_cs_kubernetes_permissions` | ✅ | This resource will help you implement RBAC authorization for the kubernetes c... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_permissions.html.markdown) |
| `alicloud_cs_kubernetes_policy_instance` | ✅ | Provides a Container Service for Kubernetes (ACK) Policy Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_kubernetes_policy_instance.html.markdown) |
| `alicloud_cs_managed_kubernetes` | ✅ | This resource will help you to manage a ManagedKubernetes Cluster in Alibaba ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_managed_kubernetes.html.markdown) |
| `alicloud_cs_serverless_kubernetes` | ✅ | This resource will help you to manager a Serverless Kubernetes Cluster, see [... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cs_serverless_kubernetes.html.markdown) |

---

### Fcv3

**产品代码**: `fcv3`
**产品线分类**: 云原生
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_fcv3_alias` | ✅ | Provides a FCV3 Alias resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_alias.html.markdown) |
| `alicloud_fcv3_async_invoke_config` | ✅ | Provides a FCV3 Async Invoke Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_async_invoke_config.html.markdown) |
| `alicloud_fcv3_concurrency_config` | ✅ | Provides a FCV3 Concurrency Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_concurrency_config.html.markdown) |
| `alicloud_fcv3_custom_domain` | ✅ | Provides a Function Compute Service V3 (FCV3) Custom Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_custom_domain.html.markdown) |
| `alicloud_fcv3_function` | ✅ | Provides a Function Compute Service V3 (FCV3) Function resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_function.html.markdown) |
| `alicloud_fcv3_function_version` | ✅ | Provides a FCV3 Function Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_function_version.html.markdown) |
| `alicloud_fcv3_layer_version` | ✅ | Provides a FCV3 Layer Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_layer_version.html.markdown) |
| `alicloud_fcv3_provision_config` | ✅ | Provides a FCV3 Provision Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_provision_config.html.markdown) |
| `alicloud_fcv3_trigger` | ✅ | Provides a FCV3 Trigger resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_trigger.html.markdown) |
| `alicloud_fcv3_vpc_binding` | ✅ | Provides a FCV3 Vpc Binding resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv3_vpc_binding.html.markdown) |

---

### Function Compute

**产品代码**: `fc`
**产品线分类**: 云原生
**资源数**: 8 | **已弃用**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_fc_alias` | ⚠️ 弃用 → `alicloud_fcv3_alias` | Creates a Function Compute service alias. Creates an alias that points to the... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_alias.html.markdown) |
| `alicloud_fc_custom_domain` | ⚠️ 弃用 → `alicloud_fcv3_custom_domain` | Provides an Alicloud Function Compute custom domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_custom_domain.html.markdown) |
| `alicloud_fc_function` | ⚠️ 弃用 → `alicloud_fcv3_function` | Provides a Alicloud Function Compute Function resource. Function allows you t... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_function.html.markdown) |
| `alicloud_fc_function_async_invoke_config` | ⚠️ 弃用 → `alicloud_fcv3_async_invoke_config` | Manages an asynchronous invocation configuration for a FC Function or Alias. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_function_async_invoke_config.html.markdown) |
| `alicloud_fc_layer_version` | ⚠️ 弃用 | Provides a Function Compute Layer Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_layer_version.html.markdown) |
| `alicloud_fc_service` | ⚠️ 弃用 → `alicloud_fcv3_function` | Provides a Alicloud Function Compute Service resource. The resource is the ba... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_service.html.markdown) |
| `alicloud_fc_trigger` | ⚠️ 弃用 → `alicloud_fcv3_trigger` | Provides an Alicloud Function Compute Trigger resource. Based on trigger, exe... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fc_trigger.html.markdown) |
| `alicloud_fcv2_function` | ✅ | Provides a FCV2 Function resource. Function is the unit of system scheduling ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fcv2_function.html.markdown) |

---

### Sae

**产品代码**: `sae`
**产品线分类**: 云原生
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_sae_application` | ✅ | Provides a Serverless App Engine (SAE) Application resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_application.html.markdown) |
| `alicloud_sae_application_scaling_rule` | ✅ | Provides a Serverless App Engine (SAE) Application Scaling Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_application_scaling_rule.html.markdown) |
| `alicloud_sae_config_map` | ✅ | Provides a Serverless App Engine (SAE) Config Map resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_config_map.html.markdown) |
| `alicloud_sae_grey_tag_route` | ✅ | Provides a Serverless App Engine (SAE) GreyTagRoute resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_grey_tag_route.html.markdown) |
| `alicloud_sae_ingress` | ✅ | Provides a Serverless App Engine (SAE) Ingress resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_ingress.html.markdown) |
| `alicloud_sae_load_balancer_internet` | ✅ | Provides an Alicloud Serverless App Engine (SAE) Application Load Balancer At... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_load_balancer_internet.html.markdown) |
| `alicloud_sae_load_balancer_intranet` | ✅ | Provides an Alicloud Serverless App Engine (SAE) Application Load Balancer At... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_load_balancer_intranet.html.markdown) |
| `alicloud_sae_namespace` | ✅ | Provides a Serverless App Engine (SAE) Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sae_namespace.html.markdown) |

---

### Simple Application Server

**产品代码**: `simple_application_server`
**产品线分类**: 云原生
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_simple_application_server_custom_image` | ✅ | Provides a Simple Application Server Custom Image resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_custom_image.html.markdown) |
| `alicloud_simple_application_server_disk` | ✅ | Provides a Simple Application Server Disk resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_disk.html.markdown) |
| `alicloud_simple_application_server_firewall_rule` | ✅ | Provides a Simple Application Server Firewall Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_firewall_rule.html.markdown) |
| `alicloud_simple_application_server_instance` | ✅ | Provides a Simple Application Server Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_instance.html.markdown) |
| `alicloud_simple_application_server_snapshot` | ✅ | Provides a Simple Application Server Snapshot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/simple_application_server_snapshot.html.markdown) |

---

### Fnf

**产品代码**: `fnf`
**产品线分类**: 云原生
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_fnf_execution` | ✅ | Provides a Serverless Workflow Execution resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fnf_execution.html.markdown) |
| `alicloud_fnf_flow` | ✅ | Provides a Serverless Workflow Flow resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fnf_flow.html.markdown) |
| `alicloud_fnf_schedule` | ✅ | Provides a Serverless Workflow Schedule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/fnf_schedule.html.markdown) |

---

### Mscsub

**产品代码**: `mscsub`
**产品线分类**: 云原生
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_msc_sub_contact` | ✅ | Provides a Msc Sub Contact resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/msc_sub_contact.html.markdown) |
| `alicloud_msc_sub_subscription` | ✅ | Provides a Msc Sub Subscription resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/msc_sub_subscription.html.markdown) |
| `alicloud_msc_sub_webhook` | ✅ | Provides a Msc Sub Webhook resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/msc_sub_webhook.html.markdown) |

---

### Service Mesh

**产品代码**: `service_mesh`
**产品线分类**: 云原生
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_service_mesh_extension_provider` | ✅ | Provides a Service Mesh Extension Provider resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_mesh_extension_provider.html.markdown) |
| `alicloud_service_mesh_service_mesh` | ✅ | Provides a Service Mesh Service Mesh resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_mesh_service_mesh.html.markdown) |
| `alicloud_service_mesh_user_permission` | ✅ | Provides a Service Mesh UserPermission resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/service_mesh_user_permission.html.markdown) |

---

### Ack One

**产品代码**: `ack_one`
**产品线分类**: 云原生
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ack_one_cluster` | ✅ | Provides a Ack One Cluster resource. Fleet Manager Cluster. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ack_one_cluster.html.markdown) |
| `alicloud_ack_one_membership_attachment` | ✅ | Provides an Ack One Membership Attachment resource. Fleet Manager Membership ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ack_one_membership_attachment.html.markdown) |

---

### Video Surveillance System

**产品代码**: `video_surveillance_system`
**产品线分类**: 云原生
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_video_surveillance_system_group` | ✅ | Provides a Video Surveillance System Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/video_surveillance_system_group.html.markdown) |

---

## 弹性计算 (7 个产品)

### Elastic Compute Service

**产品代码**: `ecs`
**产品线分类**: 弹性计算
**资源数**: 49 | **已弃用**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_auto_provisioning_group` | ✅ | Provides a ECS auto provisioning group resource which is a solution that uses... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/auto_provisioning_group.html.markdown) |
| `alicloud_disk` | ⚠️ 弃用 → `alicloud_disk` | Provides a ECS disk resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/disk.html.markdown) |
| `alicloud_disk_attachment` | ⚠️ 弃用 → `alicloud_ecs_disk_attachment` | Provides an Alicloud ECS Disk Attachment as a resource, to attach and detach ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/disk_attachment.html.markdown) |
| `alicloud_ecs_activation` | ✅ | Provides a ECS Activation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_activation.html.markdown) |
| `alicloud_ecs_auto_snapshot_policy` | ✅ | Provides a ECS Auto Snapshot Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_auto_snapshot_policy.html.markdown) |
| `alicloud_ecs_auto_snapshot_policy_attachment` | ✅ | Provides a ECS Auto Snapshot Policy Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_auto_snapshot_policy_attachment.html.markdown) |
| `alicloud_ecs_capacity_reservation` | ✅ | Provides a Ecs Capacity Reservation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_capacity_reservation.html.markdown) |
| `alicloud_ecs_command` | ✅ | Provides a ECS Command resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_command.html.markdown) |
| `alicloud_ecs_dedicated_host` | ✅ | This resouce used to create a dedicated host and store its initial version. F... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_dedicated_host.html.markdown) |
| `alicloud_ecs_dedicated_host_cluster` | ✅ | Provides a ECS Dedicated Host Cluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_dedicated_host_cluster.html.markdown) |
| `alicloud_ecs_deployment_set` | ✅ | Provides a ECS Deployment Set resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_deployment_set.html.markdown) |
| `alicloud_ecs_disk` | ✅ | Provides an ECS Disk resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_disk.html.markdown) |
| `alicloud_ecs_disk_attachment` | ✅ | Provides an Alicloud ECS Disk Attachment as a resource, to attach and detach ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_disk_attachment.html.markdown) |
| `alicloud_ecs_elasticity_assurance` | ✅ | Provides a ECS Elasticity Assurance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_elasticity_assurance.html.markdown) |
| `alicloud_ecs_hpc_cluster` | ✅ | Provides a ECS Hpc Cluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_hpc_cluster.html.markdown) |
| `alicloud_ecs_image_component` | ✅ | Provides a ECS Image Component resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_image_component.html.markdown) |
| `alicloud_ecs_image_pipeline` | ✅ | Provides a ECS Image Pipeline resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_image_pipeline.html.markdown) |
| `alicloud_ecs_image_pipeline_execution` | ✅ | Provides a ECS Image Pipeline Execution resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_image_pipeline_execution.html.markdown) |
| `alicloud_ecs_instance_set` | ✅ | Provides a ECS Instance Set resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_instance_set.html.markdown) |
| `alicloud_ecs_invocation` | ✅ | Provides a ECS Invocation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_invocation.html.markdown) |
| `alicloud_ecs_key_pair` | ✅ | Provides a ECS Key Pair resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_key_pair.html.markdown) |
| `alicloud_ecs_key_pair_attachment` | ✅ | Provides a ECS Key Pair Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_key_pair_attachment.html.markdown) |
| `alicloud_ecs_launch_template` | ✅ | Provides a ECS Launch Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_launch_template.html.markdown) |
| `alicloud_ecs_network_interface` | ✅ | Provides a ECS Network Interface resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_network_interface.html.markdown) |
| `alicloud_ecs_network_interface_attachment` | ✅ | Provides a ECS Network Interface Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_network_interface_attachment.html.markdown) |
| `alicloud_ecs_network_interface_permission` | ✅ | Provides a ECS Network Interface Permission resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_network_interface_permission.html.markdown) |
| `alicloud_ecs_prefix_list` | ✅ | Provides a ECS Prefix List resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_prefix_list.html.markdown) |
| `alicloud_ecs_ram_role_attachment` | ✅ | Provides a ECS Ram Role Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_ram_role_attachment.html.markdown) |
| `alicloud_ecs_session_manager_status` | ✅ | Provides a ECS Session Manager Status resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_session_manager_status.html.markdown) |
| `alicloud_ecs_snapshot` | ✅ | Provides a ECS Snapshot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_snapshot.html.markdown) |
| `alicloud_ecs_snapshot_group` | ✅ | Provides a ECS Snapshot Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_snapshot_group.html.markdown) |
| `alicloud_ecs_storage_capacity_unit` | ✅ | Provides a ECS Storage Capacity Unit resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecs_storage_capacity_unit.html.markdown) |
| `alicloud_image` | ✅ | Provides a ECS Image resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image.html.markdown) |
| `alicloud_image_copy` | ✅ | Copies a custom image from one region to another. You can use copied images t... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_copy.html.markdown) |
| `alicloud_image_export` | ✅ | Export a custom image to the OSS bucket in the same region as the custom image. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_export.html.markdown) |
| `alicloud_image_import` | ✅ | Provides a ECS Image Import resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_import.html.markdown) |
| `alicloud_image_share_permission` | ✅ | Manage image sharing permissions. You can share your custom image to other Al... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/image_share_permission.html.markdown) |
| `alicloud_instance` | ✅ | Provides a ECS instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/instance.html.markdown) |
| `alicloud_key_pair` | ⚠️ 弃用 → `alicloud_ecs_key_pair` | Provides a key pair resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/key_pair.html.markdown) |
| `alicloud_key_pair_attachment` | ⚠️ 弃用 → `alicloud_ecs_key_pair_attachment` | Provides a key pair attachment resource to bind key pair for several ECS inst... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/key_pair_attachment.html.markdown) |
| `alicloud_launch_template` | ⚠️ 弃用 → `alicloud_ecs_launch_template` | Provides an ECS Launch Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/launch_template.html.markdown) |
| `alicloud_network_interface` | ⚠️ 弃用 → `alicloud_ecs_network_interface` | Provides an ECS Elastic Network Interface resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_interface.html.markdown) |
| `alicloud_network_interface_attachment` | ⚠️ 弃用 → `alicloud_ecs_network_interface_attachment` | Provides an Alicloud ECS Elastic Network Interface Attachment as a resource t... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/network_interface_attachment.html.markdown) |
| `alicloud_ram_role_attachment` | ⚠️ 弃用 → `alicloud_ecs_ram_role_attachment` | Provides a RAM role attachment resource to bind role for several ECS instances. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ram_role_attachment.html.markdown) |
| `alicloud_reserved_instance` | ✅ | Provides an Reserved Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/reserved_instance.html.markdown) |
| `alicloud_security_group` | ✅ | Provides a ECS Security Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_group.html.markdown) |
| `alicloud_security_group_rule` | ✅ | Provides a Security Group Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/security_group_rule.html.markdown) |
| `alicloud_snapshot` | ⚠️ 弃用 → `alicloud_ecs_snapshot` | Provides an ECS snapshot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/snapshot.html.markdown) |
| `alicloud_snapshot_policy` | ⚠️ 弃用 → `alicloud_ecs_auto_snapshot_policy` | Provides an ECS snapshot policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/snapshot_policy.html.markdown) |

---

### Ens

**产品代码**: `ens`
**产品线分类**: 弹性计算
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ens_disk` | ✅ | Provides a ENS Disk resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_disk.html.markdown) |
| `alicloud_ens_disk_instance_attachment` | ✅ | Provides a ENS Disk Instance Attachment resource. Disk instance mount. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_disk_instance_attachment.html.markdown) |
| `alicloud_ens_eip` | ✅ | Provides a ENS Eip resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_eip.html.markdown) |
| `alicloud_ens_eip_instance_attachment` | ✅ | Provides a Ens Eip Instance Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_eip_instance_attachment.html.markdown) |
| `alicloud_ens_image` | ✅ | Provides a ENS Image resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_image.html.markdown) |
| `alicloud_ens_instance` | ✅ | Provides a Ens Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_instance.html.markdown) |
| `alicloud_ens_instance_security_group_attachment` | ✅ | Provides a ENS Instance Security Group Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_instance_security_group_attachment.html.markdown) |
| `alicloud_ens_key_pair` | ✅ | Provides a ENS Key Pair resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_key_pair.html.markdown) |
| `alicloud_ens_load_balancer` | ✅ | Provides a ENS Load Balancer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_load_balancer.html.markdown) |
| `alicloud_ens_nat_gateway` | ✅ | Provides a ENS Nat Gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_nat_gateway.html.markdown) |
| `alicloud_ens_network` | ✅ | Provides a ENS Network resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_network.html.markdown) |
| `alicloud_ens_security_group` | ✅ | Provides a ENS Security Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_security_group.html.markdown) |
| `alicloud_ens_snapshot` | ✅ | Provides a ENS Snapshot resource. Snapshot. When you use it for the first tim... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_snapshot.html.markdown) |
| `alicloud_ens_vswitch` | ✅ | Provides a ENS Vswitch resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ens_vswitch.html.markdown) |

---

### Message Service

**产品代码**: `message_service`
**产品线分类**: 弹性计算
**资源数**: 10 | **已弃用**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_message_service_endpoint` | ✅ | Provides a Message Service Endpoint resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_endpoint.html.markdown) |
| `alicloud_message_service_endpoint_acl` | ✅ | Provides a Message Service Endpoint Acl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_endpoint_acl.html.markdown) |
| `alicloud_message_service_event_rule` | ✅ | Provides a Message Service Event Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_event_rule.html.markdown) |
| `alicloud_message_service_queue` | ✅ | Provides a Message Service Queue resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_queue.html.markdown) |
| `alicloud_message_service_service` | ✅ | Provides a Message Service Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_service.html.markdown) |
| `alicloud_message_service_subscription` | ✅ | Provides a Message Service Subscription resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_subscription.html.markdown) |
| `alicloud_message_service_topic` | ✅ | Provides a Message Service Topic resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/message_service_topic.html.markdown) |
| `alicloud_mns_queue` | ⚠️ 弃用 → `alicloud_message_service_queue` | Provides a MNS queue resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mns_queue.html.markdown) |
| `alicloud_mns_topic` | ⚠️ 弃用 → `alicloud_message_service_topic` | Provides a MNS topic resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mns_topic.html.markdown) |
| `alicloud_mns_topic_subscription` | ⚠️ 弃用 → `alicloud_message_service_subscription` | Provides a MNS topic subscription resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mns_topic_subscription.html.markdown) |

---

### Ehpc

**产品代码**: `ehpc`
**产品线分类**: 弹性计算
**资源数**: 4 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ehpc_cluster` | ⚠️ 弃用 → `alicloud_ehpc_cluster_v2` | Provides a Ehpc Cluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_cluster.html.markdown) |
| `alicloud_ehpc_cluster_v2` | ✅ | Provides a Ehpc Cluster V2 resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_cluster_v2.html.markdown) |
| `alicloud_ehpc_job_template` | ✅ | Provides a Ehpc Job Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_job_template.html.markdown) |
| `alicloud_ehpc_queue` | ✅ | Provides a Ehpc Queue resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ehpc_queue.html.markdown) |

---

### Eci

**产品代码**: `eci`
**产品线分类**: 弹性计算
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_eci_container_group` | ✅ | Provides ECI Container Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eci_container_group.html.markdown) |
| `alicloud_eci_image_cache` | ✅ | An ECI Image Cache can help user to solve the time-consuming problem of image... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eci_image_cache.html.markdown) |
| `alicloud_eci_virtual_node` | ✅ | Provides a ECI Virtual Node resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eci_virtual_node.html.markdown) |

---

### Das

**产品代码**: `das`
**产品线分类**: 弹性计算
**资源数**: 1 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_das_switch_das_pro` | ⚠️ 弃用 | Provides a DAS Switch Das Pro resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/das_switch_das_pro.html.markdown) |

---

### Ocean Base

**产品代码**: `ocean_base`
**产品线分类**: 弹性计算
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ocean_base_instance` | ✅ | Provides a Ocean Base Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ocean_base_instance.html.markdown) |

---

## CDN及边缘云 (3 个产品)

### Dcdn

**产品代码**: `dcdn`
**产品线分类**: CDN及边缘云
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_dcdn_domain` | ✅ | Provides a DCDN Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_domain.html.markdown) |
| `alicloud_dcdn_domain_config` | ✅ | Provides a DCDN Accelerated Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_domain_config.html.markdown) |
| `alicloud_dcdn_er` | ✅ | Provides a DCDN Er resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_er.html.markdown) |
| `alicloud_dcdn_ipa_domain` | ✅ | Provides a DCDN Ipa Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_ipa_domain.html.markdown) |
| `alicloud_dcdn_kv` | ✅ | Provides a Dcdn Kv resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_kv.html.markdown) |
| `alicloud_dcdn_kv_namespace` | ✅ | Provides a Dcdn Kv Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_kv_namespace.html.markdown) |
| `alicloud_dcdn_waf_domain` | ✅ | Provides a DCDN Waf Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_domain.html.markdown) |
| `alicloud_dcdn_waf_policy` | ✅ | Provides a DCDN Waf Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_policy.html.markdown) |
| `alicloud_dcdn_waf_policy_domain_attachment` | ✅ | Provides a DCDN Waf Policy Domain Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_policy_domain_attachment.html.markdown) |
| `alicloud_dcdn_waf_rule` | ✅ | Provides a Dcdn Waf Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/dcdn_waf_rule.html.markdown) |

---

### Cdn

**产品代码**: `cdn`
**产品线分类**: CDN及边缘云
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cdn_domain_config` | ✅ | Provides a Cdn Domain Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_domain_config.html.markdown) |
| `alicloud_cdn_domain_new` | ✅ | Provides a CDN Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_domain_new.html.markdown) |
| `alicloud_cdn_fc_trigger` | ✅ | Provides a CDN Fc Trigger resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_fc_trigger.html.markdown) |
| `alicloud_cdn_real_time_log_delivery` | ✅ | Provides a CDN Real Time Log Delivery resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cdn_real_time_log_delivery.html.markdown) |

---

### Scdn

**产品代码**: `scdn`
**产品线分类**: CDN及边缘云
**资源数**: 2 | **已弃用**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_scdn_domain` | ⚠️ 弃用 | Provides a SCDN Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/scdn_domain.html.markdown) |
| `alicloud_scdn_domain_config` | ⚠️ 弃用 | Provides a SCDN Accelerated Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/scdn_domain_config.html.markdown) |

---

## 计算平台和AI (17 个产品)

### Esa

**产品代码**: `esa`
**产品线分类**: 计算平台和AI
**资源数**: 49

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_esa_cache_reserve_instance` | ✅ | Provides a ESA Cache Reserve Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_cache_reserve_instance.html.markdown) |
| `alicloud_esa_cache_rule` | ✅ | Provides a ESA Cache Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_cache_rule.html.markdown) |
| `alicloud_esa_certificate` | ✅ | Provides a ESA Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_certificate.html.markdown) |
| `alicloud_esa_client_ca_certificate` | ✅ | Provides a ESA Client Ca Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_client_ca_certificate.html.markdown) |
| `alicloud_esa_client_certificate` | ✅ | Provides a ESA Client Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_client_certificate.html.markdown) |
| `alicloud_esa_compression_rule` | ✅ | Provides a ESA Compression Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_compression_rule.html.markdown) |
| `alicloud_esa_custom_scene_policy` | ✅ | Provides a ESA Custom Scene Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_custom_scene_policy.html.markdown) |
| `alicloud_esa_edge_container_app` | ✅ | Provides a ESA Edge Container App resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_edge_container_app.html.markdown) |
| `alicloud_esa_edge_container_app_record` | ✅ | Provides a ESA Edge Container App Record resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_edge_container_app_record.html.markdown) |
| `alicloud_esa_http_incoming_request_header_modification_rule` | ✅ | Provides a ESA Http Incoming Request Header Modification Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_incoming_request_header_modification_rule.html.markdown) |
| `alicloud_esa_http_incoming_response_header_modification_rule` | ✅ | Provides a ESA Http Incoming Response Header Modification Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_incoming_response_header_modification_rule.html.markdown) |
| `alicloud_esa_http_request_header_modification_rule` | ✅ | Provides a ESA Http Request Header Modification Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_request_header_modification_rule.html.markdown) |
| `alicloud_esa_http_response_header_modification_rule` | ✅ | Provides a ESA Http Response Header Modification Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_http_response_header_modification_rule.html.markdown) |
| `alicloud_esa_https_application_configuration` | ✅ | Provides a ESA Https Application Configuration resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_https_application_configuration.html.markdown) |
| `alicloud_esa_https_basic_configuration` | ✅ | Provides a ESA Https Basic Configuration resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_https_basic_configuration.html.markdown) |
| `alicloud_esa_image_transform` | ✅ | Provides a ESA Image Transform resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_image_transform.html.markdown) |
| `alicloud_esa_kv` | ✅ | Provides a ESA Kv resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_kv.html.markdown) |
| `alicloud_esa_kv_account` | ✅ | Provides a ESA Kv Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_kv_account.html.markdown) |
| `alicloud_esa_kv_namespace` | ✅ | Provides a ESA Kv Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_kv_namespace.html.markdown) |
| `alicloud_esa_list` | ✅ | Provides a ESA List resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_list.html.markdown) |
| `alicloud_esa_load_balancer` | ✅ | Provides a ESA Load Balancer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_load_balancer.html.markdown) |
| `alicloud_esa_network_optimization` | ✅ | Provides a ESA Network Optimization resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_network_optimization.html.markdown) |
| `alicloud_esa_origin_ca_certificate` | ✅ | Provides a ESA Origin Ca Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_ca_certificate.html.markdown) |
| `alicloud_esa_origin_client_certificate` | ✅ | Provides a ESA Origin Client Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_client_certificate.html.markdown) |
| `alicloud_esa_origin_pool` | ✅ | Provides a ESA Origin Pool resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_pool.html.markdown) |
| `alicloud_esa_origin_protection` | ✅ | Provides a ESA Origin Protection resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_protection.html.markdown) |
| `alicloud_esa_origin_rule` | ✅ | Provides a ESA Origin Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_origin_rule.html.markdown) |
| `alicloud_esa_page` | ✅ | Provides a ESA Page resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_page.html.markdown) |
| `alicloud_esa_rate_plan_instance` | ✅ | Provides a ESA Rate Plan Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_rate_plan_instance.html.markdown) |
| `alicloud_esa_record` | ✅ | Provides a ESA Record resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_record.html.markdown) |
| `alicloud_esa_redirect_rule` | ✅ | Provides a ESA Redirect Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_redirect_rule.html.markdown) |
| `alicloud_esa_rewrite_url_rule` | ✅ | Provides a ESA Rewrite Url Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_rewrite_url_rule.html.markdown) |
| `alicloud_esa_routine` | ✅ | Provides a ESA Routine resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_routine.html.markdown) |
| `alicloud_esa_routine_related_record` | ✅ | Provides a ESA Routine Related Record resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_routine_related_record.html.markdown) |
| `alicloud_esa_routine_route` | ✅ | Provides a ESA Routine Route resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_routine_route.html.markdown) |
| `alicloud_esa_scheduled_preload_execution` | ✅ | Provides a ESA Scheduled Preload Execution resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_scheduled_preload_execution.html.markdown) |
| `alicloud_esa_scheduled_preload_job` | ✅ | Provides a ESA Scheduled Preload Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_scheduled_preload_job.html.markdown) |
| `alicloud_esa_site` | ✅ | Provides a ESA Site resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_site.html.markdown) |
| `alicloud_esa_site_delivery_task` | ✅ | Provides a ESA Site Delivery Task resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_site_delivery_task.html.markdown) |
| `alicloud_esa_site_origin_client_certificate` | ✅ | Provides a ESA Site Origin Client Certificate resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_site_origin_client_certificate.html.markdown) |
| `alicloud_esa_transport_layer_application` | ✅ | Provides a ESA Transport Layer Application resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_transport_layer_application.html.markdown) |
| `alicloud_esa_url_observation` | ✅ | Provides a ESA Url Observation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_url_observation.html.markdown) |
| `alicloud_esa_version` | ✅ | Provides a ESA Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_version.html.markdown) |
| `alicloud_esa_video_processing` | ✅ | Provides a ESA Video Processing resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_video_processing.html.markdown) |
| `alicloud_esa_waf_rule` | ✅ | Provides a ESA Waf Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waf_rule.html.markdown) |
| `alicloud_esa_waf_ruleset` | ✅ | Provides a ESA Waf Ruleset resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waf_ruleset.html.markdown) |
| `alicloud_esa_waiting_room` | ✅ | Provides a ESA Waiting Room resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waiting_room.html.markdown) |
| `alicloud_esa_waiting_room_event` | ✅ | Provides a ESA Waiting Room Event resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waiting_room_event.html.markdown) |
| `alicloud_esa_waiting_room_rule` | ✅ | Provides a ESA Waiting Room Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/esa_waiting_room_rule.html.markdown) |

---

### Pai Workspace

**产品代码**: `pai_workspace`
**产品线分类**: 计算平台和AI
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_pai_workspace_code_source` | ✅ | Provides a PAI Workspace Code Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_code_source.html.markdown) |
| `alicloud_pai_workspace_dataset` | ✅ | Provides a PAI Workspace Dataset resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_dataset.html.markdown) |
| `alicloud_pai_workspace_datasetversion` | ✅ | Provides a PAI Workspace Datasetversion resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_datasetversion.html.markdown) |
| `alicloud_pai_workspace_experiment` | ✅ | Provides a PAI Workspace Experiment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_experiment.html.markdown) |
| `alicloud_pai_workspace_member` | ✅ | Provides a PAI Workspace Member resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_member.html.markdown) |
| `alicloud_pai_workspace_model` | ✅ | Provides a PAI Workspace Model resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_model.html.markdown) |
| `alicloud_pai_workspace_model_version` | ✅ | Provides a PAI Workspace Model Version resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_model_version.html.markdown) |
| `alicloud_pai_workspace_run` | ✅ | Provides a PAI Workspace Run resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_run.html.markdown) |
| `alicloud_pai_workspace_user_config` | ✅ | Provides a PAI Workspace User Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_user_config.html.markdown) |
| `alicloud_pai_workspace_workspace` | ✅ | Provides a PAI Workspace Workspace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_workspace_workspace.html.markdown) |

---

### Click House

**产品代码**: `click_house`
**产品线分类**: 计算平台和AI
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_click_house_account` | ✅ | Provides a Click House Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_account.html.markdown) |
| `alicloud_click_house_backup_policy` | ✅ | Provides a Click House Backup Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_backup_policy.html.markdown) |
| `alicloud_click_house_db_cluster` | ✅ | Provides a Click House DBCluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_db_cluster.html.markdown) |
| `alicloud_click_house_enterprise_db_cluster` | ✅ | Provides a Click House Enterprise Db Cluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster.html.markdown) |
| `alicloud_click_house_enterprise_db_cluster_account` | ✅ | Provides a Click House Enterprise Db Cluster Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_account.html.markdown) |
| `alicloud_click_house_enterprise_db_cluster_backup_policy` | ✅ | Provides a Click House Enterprise Db Cluster Backup Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_backup_policy.html.markdown) |
| `alicloud_click_house_enterprise_db_cluster_computing_group` | ✅ | Provides a Click House Enterprise Db Cluster Computing Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_computing_group.html.markdown) |
| `alicloud_click_house_enterprise_db_cluster_public_endpoint` | ✅ | Provides a Click House Enterprise Db Cluster Public Endpoint resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_public_endpoint.html.markdown) |
| `alicloud_click_house_enterprise_db_cluster_security_ip` | ✅ | Provides a Click House Enterprise Db Cluster Security I P resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/click_house_enterprise_db_cluster_security_ip.html.markdown) |

---

### Data Works

**产品代码**: `data_works`
**产品线分类**: 计算平台和AI
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_data_works_data_source` | ✅ | Provides a Data Works Data Source resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_data_source.html.markdown) |
| `alicloud_data_works_data_source_shared_rule` | ✅ | Provides a Data Works Data Source Shared Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_data_source_shared_rule.html.markdown) |
| `alicloud_data_works_di_alarm_rule` | ✅ | Provides a Data Works Di Alarm Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_di_alarm_rule.html.markdown) |
| `alicloud_data_works_di_job` | ✅ | Provides a Data Works Di Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_di_job.html.markdown) |
| `alicloud_data_works_dw_resource_group` | ✅ | Provides a Data Works Dw Resource Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_dw_resource_group.html.markdown) |
| `alicloud_data_works_folder` | ✅ | Provides a Data Works Folder resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_folder.html.markdown) |
| `alicloud_data_works_network` | ✅ | Provides a Data Works Network resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_network.html.markdown) |
| `alicloud_data_works_project` | ✅ | Provides a Data Works Project resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_project.html.markdown) |
| `alicloud_data_works_project_member` | ✅ | Provides a Data Works Project Member resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/data_works_project_member.html.markdown) |

---

### Max Compute

**产品代码**: `max_compute`
**产品线分类**: 计算平台和AI
**资源数**: 8 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_max_compute_quota` | ✅ | Provides a Max Compute Quota resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_quota.html.markdown) |
| `alicloud_max_compute_quota_plan` | ✅ | Provides a Max Compute Quota Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_quota_plan.html.markdown) |
| `alicloud_max_compute_quota_schedule` | ✅ | Provides a Max Compute Quota Schedule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_quota_schedule.html.markdown) |
| `alicloud_max_compute_role` | ✅ | Provides a Max Compute Role resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_role.html.markdown) |
| `alicloud_max_compute_role_user_attachment` | ✅ | Provides a Max Compute Role User Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_role_user_attachment.html.markdown) |
| `alicloud_max_compute_tenant_role_user_attachment` | ✅ | Provides a Max Compute Tenant Role User Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_tenant_role_user_attachment.html.markdown) |
| `alicloud_max_compute_tunnel_quota_timer` | ⚠️ 弃用 | Provides a Max Compute Tunnel Quota Timer resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/max_compute_tunnel_quota_timer.html.markdown) |
| `alicloud_maxcompute_project` | ✅ | Provides a Max Compute Project resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/maxcompute_project.html.markdown) |

---

### Brain Industrial

**产品代码**: `brain_industrial`
**产品线分类**: 计算平台和AI
**资源数**: 3 | **已弃用**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_brain_industrial_pid_loop` | ⚠️ 弃用 | Provides a Brain Industrial Pid Loop resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/brain_industrial_pid_loop.html.markdown) |
| `alicloud_brain_industrial_pid_organization` | ⚠️ 弃用 | Provides a Brain Industrial Pid Organization resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/brain_industrial_pid_organization.html.markdown) |
| `alicloud_brain_industrial_pid_project` | ⚠️ 弃用 | Provides a Brain Industrial Pid Project resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/brain_industrial_pid_project.html.markdown) |

---

### Datahub

**产品代码**: `datahub`
**产品线分类**: 计算平台和AI
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_datahub_project` | ✅ | The project is the basic unit of resource management in Datahub Service and i... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/datahub_project.html.markdown) |
| `alicloud_datahub_subscription` | ✅ | The subscription is the basic unit of resource usage in Datahub Service under... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/datahub_subscription.html.markdown) |
| `alicloud_datahub_topic` | ✅ | The topic is the basic unit of Datahub data source and is used to define one ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/datahub_topic.html.markdown) |

---

### Realtime Compute

**产品代码**: `realtime_compute`
**产品线分类**: 计算平台和AI
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_realtime_compute_deployment` | ✅ | Provides a Realtime Compute Deployment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/realtime_compute_deployment.html.markdown) |
| `alicloud_realtime_compute_job` | ✅ | Provides a Realtime Compute Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/realtime_compute_job.html.markdown) |
| `alicloud_realtime_compute_vvp_instance` | ✅ | Provides a Realtime Compute Vvp Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/realtime_compute_vvp_instance.html.markdown) |

---

### Emr

**产品代码**: `emr`
**产品线分类**: 计算平台和AI
**资源数**: 2 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_emr_cluster` | ⚠️ 弃用 → `alicloud_emrv2_cluster` | Provides a EMR Cluster resource. With this you can create, read, and release ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/emr_cluster.html.markdown) |
| `alicloud_emrv2_cluster` | ✅ | Provides a EMR cluster resource. This resource is based on EMR's new version ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/emrv2_cluster.html.markdown) |

---

### Star Rocks

**产品代码**: `star_rocks`
**产品线分类**: 计算平台和AI
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_star_rocks_instance` | ✅ | Provides a Star Rocks Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/star_rocks_instance.html.markdown) |
| `alicloud_star_rocks_node_group` | ✅ | Provides a Star Rocks Node Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/star_rocks_node_group.html.markdown) |

---

### Compute Nest

**产品代码**: `compute_nest`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_compute_nest_service_instance` | ✅ | Provides a Compute Nest Service Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/compute_nest_service_instance.html.markdown) |

---

### Elasticsearch

**产品代码**: `elasticsearch`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_elasticsearch_instance` | ✅ | Provides a Elasticsearch Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/elasticsearch_instance.html.markdown) |

---

### Hologram

**产品代码**: `hologram`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_hologram_instance` | ✅ | Provides a Hologres (Hologram) Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/hologram_instance.html.markdown) |

---

### Open Search

**产品代码**: `open_search`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_open_search_app_group` | ✅ | Provides a Open Search App Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/open_search_app_group.html.markdown) |

---

### Pai Flow

**产品代码**: `pai_flow`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_pai_flow_pipeline` | ✅ | Provides a Pai Flow Pipeline resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_flow_pipeline.html.markdown) |

---

### Pai

**产品代码**: `pai`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_pai_service` | ✅ | Provides a PAI Service resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/pai_service.html.markdown) |

---

### Quick Bi

**产品代码**: `quick_bi`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_quick_bi_user` | ✅ | Provides a Quick BI User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/quick_bi_user.html.markdown) |

---

## 其它 (20 个产品)

### Sls

**产品代码**: `sls`
**产品线分类**: 其它
**资源数**: 25 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_log_alert` | ✅ | Log alert is a unit of log service, which is used to monitor and alert the us... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_alert.html.markdown) |
| `alicloud_log_alert_resource` | ✅ | Using this resource can init SLS Alert resources automatically. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_alert_resource.html.markdown) |
| `alicloud_log_audit` | ✅ | SLS log audit exists in the form of log service app. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_audit.html.markdown) |
| `alicloud_log_dashboard` | ✅ | The dashboard is a real-time data analysis platform provided by the log servi... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_dashboard.html.markdown) |
| `alicloud_log_etl` | ✅ | The data transformation of the log service is a hosted, highly available, and... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_etl.html.markdown) |
| `alicloud_log_ingestion` | ✅ | Log service ingestion, this service provides the function of importing logs o... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_ingestion.html.markdown) |
| `alicloud_log_machine_group` | ✅ | Log Service manages all the ECS instances whose logs need to be collected by ... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_machine_group.html.markdown) |
| `alicloud_log_oss_export` | ✅ | Log service data delivery management, this service provides the function of d... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_oss_export.html.markdown) |
| `alicloud_log_oss_shipper` | ⚠️ 弃用 → `alicloud_log_oss_export` | Log service data delivery management, this service provides the function of d... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_oss_shipper.html.markdown) |
| `alicloud_log_project` | ✅ | Provides a SLS Project resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_project.html.markdown) |
| `alicloud_log_resource` | ✅ | Log resource is a meta store service provided by log service, resource can be... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_resource.html.markdown) |
| `alicloud_log_resource_record` | ✅ | Log resource is a meta store service provided by log service, resource can be... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_resource_record.html.markdown) |
| `alicloud_log_store` | ✅ | Provides a SLS Log Store resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_store.html.markdown) |
| `alicloud_log_store_index` | ✅ | Log Service provides the LogSearch/Analytics function to query and analyze la... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/log_store_index.html.markdown) |
| `alicloud_logtail_attachment` | ✅ | The Logtail access service is a log collection agent provided by Log Service. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/logtail_attachment.html.markdown) |
| `alicloud_logtail_config` | ✅ | The Logtail access service is a log collection agent provided by Log Service. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/logtail_config.html.markdown) |
| `alicloud_sls_alert` | ✅ | Provides a SLS Alert resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_alert.html.markdown) |
| `alicloud_sls_collection_policy` | ✅ | Provides a Log Service (SLS) Collection Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_collection_policy.html.markdown) |
| `alicloud_sls_etl` | ✅ | Provides a Log Service (SLS) Etl resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_etl.html.markdown) |
| `alicloud_sls_index` | ✅ | Provides a Log Service (SLS) Index resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_index.html.markdown) |
| `alicloud_sls_logtail_config` | ✅ | Provides a Log Service (SLS) Logtail Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_logtail_config.html.markdown) |
| `alicloud_sls_logtail_pipeline_config` | ✅ | Provides a Log Service (SLS) Logtail Pipeline Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_logtail_pipeline_config.html.markdown) |
| `alicloud_sls_machine_group` | ✅ | Provides a Log Service (SLS) Machine Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_machine_group.html.markdown) |
| `alicloud_sls_oss_export_sink` | ✅ | Provides a Log Service (SLS) Oss Export Sink resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_oss_export_sink.html.markdown) |
| `alicloud_sls_scheduled_sql` | ✅ | Provides a Log Service (SLS) Scheduled Sql resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/sls_scheduled_sql.html.markdown) |

---

### Ecd

**产品代码**: `ecd`
**产品线分类**: 其它
**资源数**: 14 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ecd_ad_connector_directory` | ✅ | Provides a ECD Ad Connector Directory resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_ad_connector_directory.html.markdown) |
| `alicloud_ecd_ad_connector_office_site` | ✅ | Provides a ECD Ad Connector Office Site resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_ad_connector_office_site.html.markdown) |
| `alicloud_ecd_bundle` | ✅ | Provides a ECD Bundle resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_bundle.html.markdown) |
| `alicloud_ecd_command` | ✅ | Provides a ECD Command resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_command.html.markdown) |
| `alicloud_ecd_custom_property` | ✅ | Provides a ECD Custom Property resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_custom_property.html.markdown) |
| `alicloud_ecd_desktop` | ✅ | Provides a ECD Desktop resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_desktop.html.markdown) |
| `alicloud_ecd_image` | ✅ | Provides a ECD Image resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_image.html.markdown) |
| `alicloud_ecd_nas_file_system` | ✅ | Provides a ECD Nas File System resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_nas_file_system.html.markdown) |
| `alicloud_ecd_network_package` | ✅ | Provides a ECD Network Package resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_network_package.html.markdown) |
| `alicloud_ecd_policy_group` | ✅ | Provides a Elastic Desktop Service (ECD) Policy Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_policy_group.html.markdown) |
| `alicloud_ecd_ram_directory` | ⚠️ 弃用 | Provides a ECD Ram Directory resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_ram_directory.html.markdown) |
| `alicloud_ecd_simple_office_site` | ✅ | Provides a ECD Simple Office Site resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_simple_office_site.html.markdown) |
| `alicloud_ecd_snapshot` | ✅ | Provides a ECD Snapshot resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_snapshot.html.markdown) |
| `alicloud_ecd_user` | ✅ | Provides a Elastic Desktop Service (ECD) User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecd_user.html.markdown) |

---

### Eflo

**产品代码**: `eflo`
**产品线分类**: 其它
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_eflo_cluster` | ✅ | Provides a Eflo Cluster resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_cluster.html.markdown) |
| `alicloud_eflo_er` | ✅ | Provides a Eflo Er resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_er.html.markdown) |
| `alicloud_eflo_experiment_plan` | ✅ | Provides a Eflo Experiment Plan resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_experiment_plan.html.markdown) |
| `alicloud_eflo_experiment_plan_template` | ✅ | Provides a Eflo Experiment Plan Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_experiment_plan_template.html.markdown) |
| `alicloud_eflo_hyper_node` | ✅ | Provides a Eflo Hyper Node resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_hyper_node.html.markdown) |
| `alicloud_eflo_invocation` | ✅ | Provides a Eflo Invocation resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_invocation.html.markdown) |
| `alicloud_eflo_node` | ✅ | Provides a Eflo Node resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_node.html.markdown) |
| `alicloud_eflo_node_group` | ✅ | Provides a Eflo Node Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_node_group.html.markdown) |
| `alicloud_eflo_node_group_attachment` | ✅ | Provides a Eflo Node Group Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_node_group_attachment.html.markdown) |
| `alicloud_eflo_resource` | ✅ | Provides a Eflo Resource resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_resource.html.markdown) |
| `alicloud_eflo_subnet` | ✅ | Provides a Eflo Subnet resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_subnet.html.markdown) |
| `alicloud_eflo_vpd` | ✅ | Provides a Eflo Vpd resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_vpd.html.markdown) |
| `alicloud_eflo_vpd_grant_rule` | ✅ | Provides a Eflo Vpd Grant Rule resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_vpd_grant_rule.html.markdown) |
| `alicloud_eflo_vsc` | ✅ | Provides a Eflo Vsc resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eflo_vsc.html.markdown) |

---

### Cloud Sso

**产品代码**: `cloud_sso`
**产品线分类**: 其它
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloud_sso_access_assignment` | ✅ | Provides a Cloud SSO Access Assignment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_access_assignment.html.markdown) |
| `alicloud_cloud_sso_access_configuration` | ✅ | Provides a Cloud SSO Access Configuration resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_access_configuration.html.markdown) |
| `alicloud_cloud_sso_access_configuration_provisioning` | ✅ | Provides a Cloud SSO Access Configuration Provisioning resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_access_configuration_provisioning.html.markdown) |
| `alicloud_cloud_sso_delegate_account` | ✅ | Provides a Cloud SSO Delegate Account resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_delegate_account.html.markdown) |
| `alicloud_cloud_sso_directory` | ✅ | Provides a Cloud SSO Directory resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_directory.html.markdown) |
| `alicloud_cloud_sso_group` | ✅ | Provides a Cloud SSO Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_group.html.markdown) |
| `alicloud_cloud_sso_scim_server_credential` | ✅ | Provides a Cloud SSO SCIM Server Credential resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_scim_server_credential.html.markdown) |
| `alicloud_cloud_sso_user` | ✅ | Provides a Cloud Sso User resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_user.html.markdown) |
| `alicloud_cloud_sso_user_attachment` | ✅ | Provides a Cloud SSO User Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_user_attachment.html.markdown) |
| `alicloud_cloud_sso_user_provisioning` | ✅ | Provides a Cloud SSO User Provisioning resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_sso_user_provisioning.html.markdown) |

---

### Cloud Phone

**产品代码**: `cloud_phone`
**产品线分类**: 其它
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloud_phone_image` | ✅ | Provides a Cloud Phone Image resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_image.html.markdown) |
| `alicloud_cloud_phone_instance` | ✅ | Provides a Cloud Phone Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_instance.html.markdown) |
| `alicloud_cloud_phone_instance_group` | ✅ | Provides a Cloud Phone Instance Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_instance_group.html.markdown) |
| `alicloud_cloud_phone_key_pair` | ✅ | Provides a Cloud Phone Key Pair resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_key_pair.html.markdown) |
| `alicloud_cloud_phone_policy` | ✅ | Provides a Cloud Phone Policy resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_phone_policy.html.markdown) |

---

### Mse

**产品代码**: `mse`
**产品线分类**: 其它
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_mse_cluster` | ✅ | Provides a MSE Cluster resource. It is a one-stop microservice platform for t... | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_cluster.html.markdown) |
| `alicloud_mse_engine_namespace` | ✅ | Provides a Microservice Engine (MSE) Engine Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_engine_namespace.html.markdown) |
| `alicloud_mse_gateway` | ✅ | Provides a Microservice Engine (MSE) Gateway resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_gateway.html.markdown) |
| `alicloud_mse_nacos_config` | ✅ | Provides a Microservice Engine (MSE) Nacos Config resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_nacos_config.html.markdown) |
| `alicloud_mse_znode` | ✅ | Provides a Microservice Engine (MSE) Znode resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mse_znode.html.markdown) |

---

### Direct Mail

**产品代码**: `direct_mail`
**产品线分类**: 其它
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_direct_mail_domain` | ✅ | Provides a Direct Mail Domain resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_domain.html.markdown) |
| `alicloud_direct_mail_mail_address` | ✅ | Provides a Direct Mail Mail Address resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_mail_address.html.markdown) |
| `alicloud_direct_mail_receivers` | ✅ | Provides a Direct Mail Receivers resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_receivers.html.markdown) |
| `alicloud_direct_mail_tag` | ✅ | Provides a Direct Mail Tag resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/direct_mail_tag.html.markdown) |

---

### Schedulerx

**产品代码**: `schedulerx`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_schedulerx_app_group` | ✅ | Provides a Schedulerx App Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/schedulerx_app_group.html.markdown) |
| `alicloud_schedulerx_job` | ✅ | Provides a Schedulerx Job resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/schedulerx_job.html.markdown) |
| `alicloud_schedulerx_namespace` | ✅ | Provides a Schedulerx Namespace resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/schedulerx_namespace.html.markdown) |

---

### Cbwp

**产品代码**: `cbwp`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_common_bandwidth_package` | ✅ | Provides a EIP Bandwidth Plan (CBWP) Common Bandwidth Package resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/common_bandwidth_package.html.markdown) |
| `alicloud_common_bandwidth_package_attachment` | ✅ | Provides a CBWP Common Bandwidth Package Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/common_bandwidth_package_attachment.html.markdown) |

---

### Eais

**产品代码**: `eais`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_eais_client_instance_attachment` | ✅ | Provides a EAIS Client Instance Attachment resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eais_client_instance_attachment.html.markdown) |
| `alicloud_eais_instance` | ✅ | Provides a EAIS Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/eais_instance.html.markdown) |

---

### Ecp

**产品代码**: `ecp`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_ecp_instance` | ✅ | Provides a Elastic Cloud Phone (ECP) Instance resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecp_instance.html.markdown) |
| `alicloud_ecp_key_pair` | ✅ | Provides a Elastic Cloud Phone (ECP) Key Pair resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/ecp_key_pair.html.markdown) |

---

### Mhub

**产品代码**: `mhub`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_mhub_app` | ✅ | Provides a MHUB App resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mhub_app.html.markdown) |
| `alicloud_mhub_product` | ✅ | Provides a MHUB Product resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/mhub_product.html.markdown) |

---

### Bpstudio

**产品代码**: `bpstudio`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_bp_studio_application` | ✅ | Provides a Cloud Architect Design Tools Application resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/bp_studio_application.html.markdown) |

---

### Chatbot

**产品代码**: `chatbot`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_chatbot_publish_task` | ✅ | Provides a Chatbot Publish Task resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/chatbot_publish_task.html.markdown) |

---

### Cloud Control

**产品代码**: `cloud_control`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_cloud_control_resource` | ✅ | Provides a Cloud Control Resource resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/cloud_control_resource.html.markdown) |

---

### Imm

**产品代码**: `imm`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_imm_project` | ✅ | Provides a Intelligent Media Management Project resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/imm_project.html.markdown) |

---

### Imp

**产品代码**: `imp`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_imp_app_template` | ✅ | Provides a Apsara Agile Live (IMP) App Template resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/imp_app_template.html.markdown) |

---

### Iot

**产品代码**: `iot`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_iot_device_group` | ✅ | Provides a Iot Device Group resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/iot_device_group.html.markdown) |

---

### Market Place

**产品代码**: `market_place`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_market_order` | ✅ | Provides a market order resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/market_order.html.markdown) |

---

### Open Api Explorer

**产品代码**: `open_api_explorer`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `alicloud_open_api_explorer_api_mcp_server` | ✅ | Provides a Open Api Explorer Api Mcp Server resource. | [doc](https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r/open_api_explorer_api_mcp_server.html.markdown) |

---
