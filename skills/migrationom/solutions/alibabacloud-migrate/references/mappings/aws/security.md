# AWS Security Services → Alibaba Cloud Mapping

## IAM (Identity & Access Management)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_iam_user` | `alicloud_ram_user` | Low | Similar user model |
| `aws_iam_group` | `alicloud_ram_group` | Low | Similar group model |
| `aws_iam_role` | `alicloud_ram_role` | Medium | Trust policy format differs |
| `aws_iam_policy` | `alicloud_ram_policy` | Medium | Policy language similar but not identical |
| `aws_iam_user_policy_attachment` | `alicloud_ram_user_policy_attachment` | Low | Same concept |
| `aws_iam_role_policy_attachment` | `alicloud_ram_role_policy_attachment` | Low | Same concept |
| `aws_iam_group_policy_attachment` | `alicloud_ram_group_policy_attachment` | Low | Same concept |
| `aws_iam_group_membership` | `alicloud_ram_group_membership` | Low | Same concept |
| `aws_iam_instance_profile` | `alicloud_ram_role_attachment` | Medium | Instance profile → role attachment to ECS |
| `aws_iam_access_key` | `alicloud_ram_access_key` | Low | Same concept |
| `aws_iam_account_password_policy` | `alicloud_ram_account_password_policy` | Low | Similar password policy |
| `aws_iam_saml_provider` | `alicloud_ram_saml_provider` | Low | SAML federation |
| `aws_iam_openid_connect_provider` | No direct equivalent | Medium | Use RAM role with OIDC trust |
| `aws_iam_service_linked_role` | `alicloud_ram_role` (service-linked) | Low | Similar concept |

### Key Attribute Differences

| Attribute | AWS IAM | Alibaba Cloud RAM |
|-----------|---------|-------------------|
| Policy document | JSON with `Effect/Action/Resource` | Same structure, different action prefixes |
| Action prefix | `s3:GetObject` | `oss:GetObject` |
| Resource ARN | `arn:aws:s3:::bucket/*` | `acs:oss:*:*:bucket/*` |
| Principal | `arn:aws:iam::123:root` | RAM user/role ARN |
| Max policies per user | 10 managed | 5 system + 5 custom |

### RAM Role Trust Policy Field

> **IMPORTANT**: `alicloud_ram_role` uses `assume_role_policy_document` (NOT the deprecated `document` field) to define the trust policy JSON.
> The field value is a JSON string with `Statement[].Principal.Service` specifying the trusted service.

### Required Target Properties and Forbidden Mappings

When Phase 2 writes `target_resources[]`, set concrete target properties so Phase 4 does not infer deprecated fields:

| Source Pattern | Target Resource | Required `target_resources[].properties` | Forbidden |
|----------------|----------------|-------------------------------------------|-----------|
| `aws_iam_role` with trust policy | `alicloud_ram_role` | `assume_role_policy_document` containing mapped `Statement[].Principal.Service` | `document` |
| `aws_iam_role_policy_attachment` | `alicloud_ram_role_policy_attachment` | `role_name`, `policy_name`, `policy_type` | `alicloud_ram_role_attachment` |
| `aws_iam_policy` | `alicloud_ram_policy` | `policy_document`, `policy_name`, `description` when available | AWS action/resource prefixes left unchanged when Alibaba equivalents exist |

`alicloud_ram_role_attachment` is only for attaching a RAM role to ECS instances. It is not a replacement for `aws_iam_role_policy_attachment`.

### Service Principal Mapping (Trust Policy)

When migrating `aws_iam_role` trust policies, map `Principal.Service` values:

| AWS Service Principal | Alibaba Cloud Service Principal | Notes |
|-----------------------|-------------------------------|-------|
| `ecs-tasks.amazonaws.com` | `cs.aliyuncs.com` | Container service (ECS Task → ACK) |
| `ec2.amazonaws.com` | `ecs.aliyuncs.com` | Compute instance |
| `lambda.amazonaws.com` | `fc.aliyuncs.com` | Serverless function |
| `elasticmapreduce.amazonaws.com` | `emr.aliyuncs.com` | EMR / E-MapReduce |
| `rds.amazonaws.com` | `rds.aliyuncs.com` | Database service |
| `s3.amazonaws.com` | `oss.aliyuncs.com` | Object storage |
| `logs.amazonaws.com` | `log.aliyuncs.com` | Logging service |
| `monitoring.amazonaws.com` | `cloudmonitor.aliyuncs.com` | Monitoring |
| `events.amazonaws.com` | `eventbridge.aliyuncs.com` | Event bridge |

> **Pattern**: AWS uses `<service>.amazonaws.com`; Alibaba Cloud uses `<service>.aliyuncs.com`. When unsure, use `<alicloud_service_short_name>.aliyuncs.com`.

---

## KMS (Key Management Service)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_kms_key` | `alicloud_kms_key` | Low | Similar key management |
| `aws_kms_alias` | `alicloud_kms_alias` | Low | Same concept |
| `aws_kms_grant` | No direct equivalent | Medium | Use RAM policy for access control |
| `aws_kms_key_policy` | `alicloud_kms_policy` | Medium | Policy-based access |
| `aws_kms_ciphertext` | `alicloud_kms_ciphertext` | Low | Encryption operation |
| `aws_kms_external_key` | `alicloud_kms_key` (BYOK) | Medium | BYOK import support |
| `aws_secretsmanager_secret` | `alicloud_kms_secret` | Low | Secrets management integrated into KMS |
| `aws_secretsmanager_secret_version` | `alicloud_kms_secret` (auto-versioned) | Low | Versioning built-in |

---

## CloudHSM

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_cloudhsm_v2_cluster` | `alicloud_kms_instance` (HSM) | High | KMS dedicated instance with HSM |
| `aws_cloudhsm_v2_hsm` | `alicloud_kms_instance` | High | Managed HSM via KMS |

---

## Certificate Management

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_acm_certificate` | `alicloud_ssl_certificates_service_certificate` | Medium | Certificate provisioning |
| `aws_acm_certificate_validation` | No direct equivalent | Medium | Validation handled differently |
| `aws_acmpca_certificate_authority` | `alicloud_ssl_certificates_service_pca_certificate` | Medium | Private CA |
| `aws_acmpca_certificate` | `alicloud_ssl_certificates_service_pca_cert` | Medium | Private certificate |

---

## WAF (Web Application Firewall)

> **Note**: AWS WAF Classic (`aws_waf_*`) is deprecated. Use WAFv2 (`aws_wafv2_*`). Alibaba Cloud WAF 3.0 (`alicloud_wafv3_*`) is the current version.

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_wafv2_web_acl` | `alicloud_wafv3_instance` | Medium | ACL-based (AWS) vs instance-based (Alibaba) |
| `aws_wafv2_rule_group` | `alicloud_wafv3_defense_template` | Medium | Rule group → defense template |
| `aws_wafv2_ip_set` | `alicloud_wafv3_defense_rule` | Medium | IP set as defense rule |
| `aws_wafv2_web_acl_association` | `alicloud_wafv3_domain` | Medium | Associate WAF with domain |
| `aws_wafv2_regex_pattern_set` | `alicloud_wafv3_defense_rule` | Medium | Regex as defense rule |

---

## DDoS Protection

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_shield_protection` | `alicloud_ddoscoo_instance` | Medium | Shield Advanced → Anti-DDoS Pro/Premium |
| `aws_shield_protection_group` | `alicloud_ddoscoo_domain_resource` / `alicloud_ddoscoo_port` | Medium | Group → per-resource config |
| `aws_shield_subscription` | `alicloud_ddoscoo_instance` | Medium | Subscription-based |
| - | `alicloud_ddos_basic_defense_threshold` | N/A | Basic DDoS (free tier, Alibaba-specific) |
| - | `alicloud_ddosbgp_instance` | N/A | Anti-DDoS Origin (BGP-based, Alibaba-specific) |

---

## Cloud Firewall

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_networkfirewall_firewall` | `alicloud_cloud_firewall_instance` | Medium | Managed network firewall |
| `aws_networkfirewall_firewall_policy` | `alicloud_cloud_firewall_control_policy` | Medium | Policy → control policy |
| `aws_networkfirewall_rule_group` | `alicloud_cloud_firewall_control_policy` | Medium | Rule group → control policy |
| `aws_networkfirewall_logging_configuration` | No direct equivalent | Medium | Logging via SLS |
| - | `alicloud_cloud_firewall_address_book` | N/A | Address book (Alibaba-specific) |
| - | `alicloud_cloud_firewall_vpc_firewall` | N/A | VPC-to-VPC firewall (Alibaba-specific) |
| - | `alicloud_cloud_firewall_vpc_firewall_cen` | N/A | VPC firewall via CEN (Alibaba-specific) |

---

## Security Posture & Threat Detection

> **Note**: AWS splits security posture across multiple services (Inspector, GuardDuty, Security Hub, Detective, Config). Alibaba Cloud consolidates these into **Cloud Security Center** (threat detection) with CWPP, CSPM, and CTDR capabilities.

| AWS Service | Alibaba Cloud Service | Migration Difficulty | Notes |
|-------------|----------------------|---------------------|-------|
| AWS Inspector (`aws_inspector2_enabler`) | `alicloud_threat_detection_instance` (CWPP) | Medium | Host & container vulnerability scanning |
| AWS GuardDuty (`aws_guardduty_detector`) | `alicloud_threat_detection_instance` (CTDR) | Medium | Threat detection & response |
| AWS Security Hub (`aws_securityhub_account`) | `alicloud_threat_detection_instance` (CSPM) | Medium | Security posture management |
| AWS Detective (`aws_detective_graph`) | `alicloud_threat_detection_instance` (CTDR) | Medium | Threat investigation |
| AWS Config (`aws_config_config_rule`) | `alicloud_threat_detection_check_config` | Medium | Configuration compliance |
| AWS Macie (`aws_macie2_account`) | No direct equivalent | High | Use Data Security Center for DLP |

---

## Bastion Host (PAM)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| AWS Systems Manager Session Manager | `alicloud_bastionhost_instance` | Medium | SSM session → dedicated bastion host |
| - | `alicloud_bastionhost_host` | N/A | Host registration (Alibaba-specific) |
| - | `alicloud_bastionhost_user` | N/A | Bastion user management (Alibaba-specific) |
| - | `alicloud_bastionhost_host_account` | N/A | Host account binding (Alibaba-specific) |

---

## Identity Service (IDaaS)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|-------------|----------------------|---------------------|-------|
| `aws_cognito_user_pool` | Alibaba Cloud IDaaS (EIAM) | High | User pool → IDaaS application |
| `aws_cognito_user_pool_client` | Alibaba Cloud IDaaS (EIAM) | High | App client → IDaaS app config |
| `aws_cognito_identity_pool` | No direct equivalent | High | Federated identity via RAM role |

---

## SSO (Single Sign-On)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|-------------|----------------------|---------------------|-------|
| AWS IAM Identity Center | `alicloud_cloud_sso_directory` | Medium | SSO directory |
| - | `alicloud_cloud_sso_user` | N/A | SSO user (Alibaba-specific) |
| - | `alicloud_cloud_sso_group` | N/A | SSO group (Alibaba-specific) |
| - | `alicloud_cloud_sso_access_configuration` | N/A | Access config (Alibaba-specific) |
| - | `alicloud_cloud_sso_access_assignment` | N/A | Access assignment (Alibaba-specific) |

---

## Migration Checklist

### Pre-Migration
- [ ] Export IAM users, groups, roles, and policies
- [ ] Document KMS keys and encryption configuration
- [ ] List all secrets in Secrets Manager
- [ ] Export WAF rules and IP sets
- [ ] Document DDoS protection settings
- [ ] List SSL certificates
- [ ] Document security posture tool configurations

### During Migration
- [ ] Create RAM users, groups, and roles
- [ ] Translate IAM policies to RAM format (action/resource prefix changes)
- [ ] Recreate KMS keys (keys cannot be exported; re-encrypt data)
- [ ] Migrate secrets to KMS Secret Manager
- [ ] Configure WAF v3 defense templates and rules
- [ ] Set up Anti-DDoS protection
- [ ] Import or re-issue SSL certificates
- [ ] Enable Cloud Security Center

### Post-Migration
- [ ] Verify RAM policy permissions
- [ ] Test encryption/decryption with new KMS keys
- [ ] Validate WAF rules against test traffic
- [ ] Confirm DDoS protection is active
- [ ] Verify SSL certificate bindings
- [ ] Review Cloud Security Center alerts
