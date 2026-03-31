# AWS Provider 产品线和资源清单

**Provider 版本**: 6.38.0
**评估时间**: 2026-03-24T09:48:03.368574

## 📊 总体统计

- **产品线数量**: 242
- **资源总数**: 1618
- **已弃用资源**: 9

## 📦 产品线分类统计

| 产品线分类 | 产品数 | 占比 |
|------------|--------|------|
| 安全 | 26 | 10.7% |
| 网络 | 23 | 9.5% |
| 企业IT治理 | 41 | 16.9% |
| 存储 | 14 | 5.8% |
| 数据库 | 18 | 7.4% |
| 云通信 | 16 | 6.6% |
| 视频云 | 3 | 1.2% |
| 云原生 | 16 | 6.6% |
| 弹性计算 | 12 | 5.0% |
| CDN及边缘云 | 2 | 0.8% |
| 计算平台和AI | 28 | 11.6% |
| 其它 | 43 | 17.8% |

## 📋 详细产品线和资源列表

## 安全 (26 个产品)

### Iam

**产品代码**: `iam`
**产品线分类**: 安全
**资源数**: 35

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_iam_access_key` | ✅ | Provides an IAM access key. This is a set of credentials that allow API reque... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_access_key.html.markdown) |
| `aws_iam_account_alias` | ✅ | Manages the account alias for the AWS Account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_account_alias.html.markdown) |
| `aws_iam_account_password_policy` | ✅ | Manages Password Policy for the AWS Account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_account_password_policy.html.markdown) |
| `aws_iam_group` | ✅ | Provides an IAM group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_group.html.markdown) |
| `aws_iam_group_membership` | ✅ | Provides a top level resource to manage IAM Group membership for IAM Users. For | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_group_membership.html.markdown) |
| `aws_iam_group_policies_exclusive` | ✅ | Terraform resource for maintaining exclusive management of inline policies as... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_group_policies_exclusive.html.markdown) |
| `aws_iam_group_policy` | ✅ | Provides an IAM policy attached to a group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_group_policy.html.markdown) |
| `aws_iam_group_policy_attachment` | ✅ | Attaches a Managed IAM Policy to an IAM group | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_group_policy_attachment.html.markdown) |
| `aws_iam_group_policy_attachments_exclusive` | ✅ | Terraform resource for maintaining exclusive management of managed IAM polici... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_group_policy_attachments_exclusive.html.markdown) |
| `aws_iam_instance_profile` | ✅ | Provides an IAM instance profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_instance_profile.html.markdown) |
| `aws_iam_openid_connect_provider` | ✅ | Provides an IAM OpenID Connect provider. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_openid_connect_provider.html.markdown) |
| `aws_iam_organizations_features` | ✅ | Manages centralized root access features across AWS member accounts managed u... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_organizations_features.html.markdown) |
| `aws_iam_outbound_web_identity_federation` | ✅ | Manages an AWS IAM (Identity & Access Management) Outbound Web Identity Feder... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_outbound_web_identity_federation.html.markdown) |
| `aws_iam_policy` | ✅ | Provides an IAM policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_policy.html.markdown) |
| `aws_iam_policy_attachment` | ✅ | Attaches a Managed IAM Policy to user(s), role(s), and/or group(s) | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_policy_attachment.html.markdown) |
| `aws_iam_role` | ✅ | Provides an IAM role. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_role.html.markdown) |
| `aws_iam_role_policies_exclusive` | ✅ | Terraform resource for maintaining exclusive management of inline policies as... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_role_policies_exclusive.html.markdown) |
| `aws_iam_role_policy` | ✅ | Provides an IAM role inline policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_role_policy.html.markdown) |
| `aws_iam_role_policy_attachment` | ✅ | Attaches a Managed IAM Policy to an IAM role | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_role_policy_attachment.html.markdown) |
| `aws_iam_role_policy_attachments_exclusive` | ✅ | Terraform resource for maintaining exclusive management of managed IAM polici... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_role_policy_attachments_exclusive.html.markdown) |
| `aws_iam_saml_provider` | ✅ | Provides an IAM SAML provider. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_saml_provider.html.markdown) |
| `aws_iam_security_token_service_preferences` | ✅ | Provides an IAM Security Token Service Preferences resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_security_token_service_preferences.html.markdown) |
| `aws_iam_server_certificate` | ✅ | Provides an IAM Server Certificate resource to upload Server Certificates. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_server_certificate.html.markdown) |
| `aws_iam_service_linked_role` | ✅ | Provides an [IAM service-linked role](https://docs.aws.amazon.com/IAM/latest/... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_service_linked_role.html.markdown) |
| `aws_iam_service_specific_credential` | ✅ | Provides an IAM Service Specific Credential. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_service_specific_credential.html.markdown) |
| `aws_iam_signing_certificate` | ✅ | Provides an IAM Signing Certificate resource to upload Signing Certificates. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_signing_certificate.html.markdown) |
| `aws_iam_user` | ✅ | Provides an IAM user. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user.html.markdown) |
| `aws_iam_user_group_membership` | ✅ | Provides a resource for adding an [IAM User][2] to [IAM Groups][1]. This | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user_group_membership.html.markdown) |
| `aws_iam_user_login_profile` | ✅ | Manages an IAM User Login Profile with limited support for password creation ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user_login_profile.html.markdown) |
| `aws_iam_user_policies_exclusive` | ✅ | Terraform resource for maintaining exclusive management of inline policies as... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user_policies_exclusive.html.markdown) |
| `aws_iam_user_policy` | ✅ | Provides an IAM policy attached to a user. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user_policy.html.markdown) |
| `aws_iam_user_policy_attachment` | ✅ | Attaches a Managed IAM Policy to an IAM user | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user_policy_attachment.html.markdown) |
| `aws_iam_user_policy_attachments_exclusive` | ✅ | Terraform resource for maintaining exclusive management of managed IAM polici... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user_policy_attachments_exclusive.html.markdown) |
| `aws_iam_user_ssh_key` | ✅ | Uploads an SSH public key and associates it with the specified IAM user. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_user_ssh_key.html.markdown) |
| `aws_iam_virtual_mfa_device` | ✅ | Provides an IAM Virtual MFA Device. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iam_virtual_mfa_device.html.markdown) |

---

### Security Hub

**产品代码**: `security_hub`
**产品线分类**: 安全
**资源数**: 15

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_securityhub_account` | ✅ | Enables Security Hub for this AWS account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_account.html.markdown) |
| `aws_securityhub_action_target` | ✅ | Creates Security Hub custom action. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_action_target.html.markdown) |
| `aws_securityhub_automation_rule` | ✅ | Terraform resource for managing an AWS Security Hub Automation Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_automation_rule.html.markdown) |
| `aws_securityhub_configuration_policy` | ✅ | Manages Security Hub configuration policy | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_configuration_policy.html.markdown) |
| `aws_securityhub_configuration_policy_association` | ✅ | Manages Security Hub configuration policy associations. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_configuration_policy_association.html.markdown) |
| `aws_securityhub_finding_aggregator` | ✅ | Manages a Security Hub finding aggregator. Security Hub needs to be enabled i... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_finding_aggregator.html.markdown) |
| `aws_securityhub_insight` | ✅ | Provides a Security Hub custom insight resource. See the [Managing custom ins... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_insight.html.markdown) |
| `aws_securityhub_invite_accepter` | ✅ | Accepts a Security Hub invitation. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_invite_accepter.html.markdown) |
| `aws_securityhub_member` | ✅ | Provides a Security Hub member resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_member.html.markdown) |
| `aws_securityhub_organization_admin_account` | ✅ | Manages a Security Hub administrator account for an organization. The AWS acc... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_organization_admin_account.html.markdown) |
| `aws_securityhub_organization_configuration` | ✅ | Manages the Security Hub Organization Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_organization_configuration.html.markdown) |
| `aws_securityhub_product_subscription` | ✅ | Subscribes to a Security Hub product. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_product_subscription.html.markdown) |
| `aws_securityhub_standards_control` | ✅ | Disable/enable Security Hub standards control in the current region. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_standards_control.html.markdown) |
| `aws_securityhub_standards_control_association` | ✅ | Terraform resource for managing an AWS Security Hub Standards Control Associa... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_standards_control_association.html.markdown) |
| `aws_securityhub_standards_subscription` | ✅ | Subscribes to a Security Hub standard. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securityhub_standards_subscription.html.markdown) |

---

### Cognito Idp

**产品代码**: `cognito_idp`
**产品线分类**: 安全
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cognito_identity_provider` | ✅ | Provides a Cognito User Identity Provider resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_identity_provider.html.markdown) |
| `aws_cognito_log_delivery_configuration` | ✅ | Manages an AWS Cognito IDP (Identity Provider) Log Delivery Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_log_delivery_configuration.html.markdown) |
| `aws_cognito_managed_login_branding` | ✅ | Manages branding settings for a user pool style and associates it with an app... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_managed_login_branding.html.markdown) |
| `aws_cognito_managed_user_pool_client` | ✅ | Use the `aws_cognito_user_pool_client` resource to manage a Cognito User Pool... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_managed_user_pool_client.html.markdown) |
| `aws_cognito_resource_server` | ✅ | Provides a Cognito Resource Server. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_resource_server.html.markdown) |
| `aws_cognito_risk_configuration` | ✅ | Provides a Cognito Risk Configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_risk_configuration.html.markdown) |
| `aws_cognito_user` | ✅ | Provides a Cognito User Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_user.html.markdown) |
| `aws_cognito_user_group` | ✅ | Provides a Cognito User Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_user_group.html.markdown) |
| `aws_cognito_user_in_group` | ✅ | Adds the specified user to the specified group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_user_in_group.html.markdown) |
| `aws_cognito_user_pool` | ✅ | Provides a Cognito User Pool resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_user_pool.html.markdown) |
| `aws_cognito_user_pool_client` | ✅ | Provides a Cognito User Pool Client resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_user_pool_client.html.markdown) |
| `aws_cognito_user_pool_domain` | ✅ | Provides a Cognito User Pool Domain resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_user_pool_domain.html.markdown) |
| `aws_cognito_user_pool_ui_customization` | ✅ | Provides a Cognito User Pool UI Customization resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_user_pool_ui_customization.html.markdown) |

---

### Guardduty

**产品代码**: `guardduty`
**产品线分类**: 安全
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_guardduty_detector` | ✅ | Provides a resource to manage an Amazon GuardDuty detector. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_detector.html.markdown) |
| `aws_guardduty_detector_feature` | ✅ | Provides a resource to manage a single Amazon GuardDuty [detector feature](ht... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_detector_feature.html.markdown) |
| `aws_guardduty_filter` | ✅ | Provides a resource to manage a GuardDuty filter. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_filter.html.markdown) |
| `aws_guardduty_invite_accepter` | ✅ | Provides a resource to accept a pending GuardDuty invite on creation, ensure ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_invite_accepter.html.markdown) |
| `aws_guardduty_ipset` | ✅ | Provides a resource to manage a GuardDuty IPSet. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_ipset.html.markdown) |
| `aws_guardduty_malware_protection_plan` | ✅ | Provides a resource to manage a GuardDuty malware protection plan. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_malware_protection_plan.html.markdown) |
| `aws_guardduty_member` | ✅ | Provides a resource to manage a GuardDuty member. To accept invitations in me... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_member.html.markdown) |
| `aws_guardduty_member_detector_feature` | ✅ | Provides a resource to manage a single Amazon GuardDuty [detector feature](ht... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_member_detector_feature.html.markdown) |
| `aws_guardduty_organization_admin_account` | ✅ | Manages a GuardDuty Organization Admin Account. The AWS account utilizing thi... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_organization_admin_account.html.markdown) |
| `aws_guardduty_organization_configuration` | ✅ | Manages the GuardDuty Organization Configuration in the current AWS Region. T... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_organization_configuration.html.markdown) |
| `aws_guardduty_organization_configuration_feature` | ✅ | Provides a resource to manage a single Amazon GuardDuty [organization configu... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_organization_configuration_feature.html.markdown) |
| `aws_guardduty_publishing_destination` | ✅ | Provides a resource to manage a GuardDuty PublishingDestination. Requires an ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_publishing_destination.html.markdown) |
| `aws_guardduty_threatintelset` | ✅ | Provides a resource to manage a GuardDuty ThreatIntelSet. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/guardduty_threatintelset.html.markdown) |

---

### Waf Classic Regional

**产品代码**: `waf_classic_regional`
**产品线分类**: 安全
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_wafregional_byte_match_set` | ✅ | Provides a WAF Regional Byte Match Set Resource for use with Application Load... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_byte_match_set.html.markdown) |
| `aws_wafregional_geo_match_set` | ✅ | Provides a WAF Regional Geo Match Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_geo_match_set.html.markdown) |
| `aws_wafregional_ipset` | ✅ | Provides a WAF Regional IPSet Resource for use with Application Load Balancer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_ipset.html.markdown) |
| `aws_wafregional_rate_based_rule` | ✅ | Provides a WAF Rate Based Rule Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_rate_based_rule.html.markdown) |
| `aws_wafregional_regex_match_set` | ✅ | Provides a WAF Regional Regex Match Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_regex_match_set.html.markdown) |
| `aws_wafregional_regex_pattern_set` | ✅ | Provides a WAF Regional Regex Pattern Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_regex_pattern_set.html.markdown) |
| `aws_wafregional_rule` | ✅ | Provides an WAF Regional Rule Resource for use with Application Load Balancer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_rule.html.markdown) |
| `aws_wafregional_rule_group` | ✅ | Provides a WAF Regional Rule Group Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_rule_group.html.markdown) |
| `aws_wafregional_size_constraint_set` | ✅ | Provides a WAF Regional Size Constraint Set Resource for use with Application... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_size_constraint_set.html.markdown) |
| `aws_wafregional_sql_injection_match_set` | ✅ | Provides a WAF Regional SQL Injection Match Set Resource for use with Applica... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_sql_injection_match_set.html.markdown) |
| `aws_wafregional_web_acl` | ✅ | Provides a WAF Regional Web ACL Resource for use with Application Load Balancer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_web_acl.html.markdown) |
| `aws_wafregional_web_acl_association` | ✅ | Manages an association with WAF Regional Web ACL. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_web_acl_association.html.markdown) |
| `aws_wafregional_xss_match_set` | ✅ | Provides a WAF Regional XSS Match Set Resource for use with Application Load ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafregional_xss_match_set.html.markdown) |

---

### Waf Classic

**产品代码**: `waf_classic`
**产品线分类**: 安全
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_waf_byte_match_set` | ✅ | Provides a WAF Byte Match Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_byte_match_set.html.markdown) |
| `aws_waf_geo_match_set` | ✅ | Provides a WAF Geo Match Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_geo_match_set.html.markdown) |
| `aws_waf_ipset` | ✅ | Provides a WAF IPSet Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_ipset.html.markdown) |
| `aws_waf_rate_based_rule` | ✅ | Provides a WAF Rate Based Rule Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_rate_based_rule.html.markdown) |
| `aws_waf_regex_match_set` | ✅ | Provides a WAF Regex Match Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_regex_match_set.html.markdown) |
| `aws_waf_regex_pattern_set` | ✅ | Provides a WAF Regex Pattern Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_regex_pattern_set.html.markdown) |
| `aws_waf_rule` | ✅ | Provides a WAF Rule Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_rule.html.markdown) |
| `aws_waf_rule_group` | ✅ | Provides a WAF Rule Group Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_rule_group.html.markdown) |
| `aws_waf_size_constraint_set` | ✅ | Use the `aws_waf_size_constraint_set` resource to manage WAF size constraint ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_size_constraint_set.html.markdown) |
| `aws_waf_sql_injection_match_set` | ✅ | Provides a WAF SQL Injection Match Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_sql_injection_match_set.html.markdown) |
| `aws_waf_web_acl` | ✅ | Provides a WAF Web ACL Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_web_acl.html.markdown) |
| `aws_waf_xss_match_set` | ✅ | Provides a WAF XSS Match Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/waf_xss_match_set.html.markdown) |

---

### Kms

**产品代码**: `kms`
**产品线分类**: 安全
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_kms_alias` | ✅ | Provides an alias for a KMS customer master key. AWS Console enforces 1-to-1 ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_alias.html.markdown) |
| `aws_kms_ciphertext` | ✅ | The KMS ciphertext resource allows you to encrypt plaintext into ciphertext | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_ciphertext.html.markdown) |
| `aws_kms_custom_key_store` | ✅ | Terraform resource for managing an AWS KMS (Key Management) Custom Key Store. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_custom_key_store.html.markdown) |
| `aws_kms_external_key` | ✅ | Manages a single-Region or multi-Region primary KMS key that uses external ke... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_external_key.html.markdown) |
| `aws_kms_grant` | ✅ | Provides a resource-based access control mechanism for a KMS customer master ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_grant.html.markdown) |
| `aws_kms_key` | ✅ | Manages a single-Region or multi-Region primary KMS key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_key.html.markdown) |
| `aws_kms_key_policy` | ✅ | Attaches a policy to a KMS Key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_key_policy.html.markdown) |
| `aws_kms_replica_external_key` | ✅ | Manages a KMS multi-Region replica key that uses external key material. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_replica_external_key.html.markdown) |
| `aws_kms_replica_key` | ✅ | Manages a KMS multi-Region replica key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kms_replica_key.html.markdown) |

---

### Macie

**产品代码**: `macie`
**产品线分类**: 安全
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_macie2_account` | ✅ | Provides a resource to manage an [AWS Macie Account](https://docs.aws.amazon.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_account.html.markdown) |
| `aws_macie2_classification_export_configuration` | ✅ | Provides a resource to manage an [Amazon Macie Classification Export Configur... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_classification_export_configuration.html.markdown) |
| `aws_macie2_classification_job` | ✅ | Provides a resource to manage an [AWS Macie Classification Job](https://docs.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_classification_job.html.markdown) |
| `aws_macie2_custom_data_identifier` | ✅ | Provides a resource to manage an [AWS Macie Custom Data Identifier](https://d... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_custom_data_identifier.html.markdown) |
| `aws_macie2_findings_filter` | ✅ | Provides a resource to manage an [Amazon Macie Findings Filter](https://docs.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_findings_filter.html.markdown) |
| `aws_macie2_invitation_accepter` | ✅ | Provides a resource to manage an [Amazon Macie Invitation Accepter](https://d... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_invitation_accepter.html.markdown) |
| `aws_macie2_member` | ✅ | Provides a resource to manage an [Amazon Macie Member](https://docs.aws.amazo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_member.html.markdown) |
| `aws_macie2_organization_admin_account` | ✅ | Provides a resource to manage an [Amazon Macie Organization Admin Account](ht... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_organization_admin_account.html.markdown) |
| `aws_macie2_organization_configuration` | ✅ | Provides a resource to manage Amazon Macie configuration settings for an orga... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/macie2_organization_configuration.html.markdown) |

---

### Waf

**产品代码**: `waf`
**产品线分类**: 安全
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_wafv2_api_key` | ✅ | Provides an AWS WAFv2 API Key resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_api_key.html.markdown) |
| `aws_wafv2_ip_set` | ✅ | Provides a WAFv2 IP Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_ip_set.html.markdown) |
| `aws_wafv2_regex_pattern_set` | ✅ | Provides an AWS WAFv2 Regex Pattern Set Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_regex_pattern_set.html.markdown) |
| `aws_wafv2_rule_group` | ✅ | Creates a WAFv2 Rule Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_rule_group.html.markdown) |
| `aws_wafv2_web_acl` | ✅ | Creates a WAFv2 Web ACL resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_web_acl.html.markdown) |
| `aws_wafv2_web_acl_association` | ✅ | Creates a WAFv2 Web ACL Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_web_acl_association.html.markdown) |
| `aws_wafv2_web_acl_logging_configuration` | ✅ | This resource creates a WAFv2 Web ACL Logging Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_web_acl_logging_configuration.html.markdown) |
| `aws_wafv2_web_acl_rule` | ✅ | Manages an individual rule within a WAFv2 Web ACL. This resource creates prop... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_web_acl_rule.html.markdown) |
| `aws_wafv2_web_acl_rule_group_association` | ✅ | Associates a WAFv2 Rule Group (custom or managed) with a Web ACL by adding a ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/wafv2_web_acl_rule_group_association.html.markdown) |

---

### Directory Service

**产品代码**: `directory_service`
**产品线分类**: 安全
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_directory_service_conditional_forwarder` | ✅ | Provides a conditional forwarder for managed Microsoft AD in AWS Directory Se... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_conditional_forwarder.html.markdown) |
| `aws_directory_service_directory` | ✅ | Provides a Simple or Managed Microsoft directory in AWS Directory Service. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_directory.html.markdown) |
| `aws_directory_service_log_subscription` | ✅ | Provides a Log subscription for AWS Directory Service that pushes logs to clo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_log_subscription.html.markdown) |
| `aws_directory_service_radius_settings` | ✅ | Manages a directory's multi-factor authentication (MFA) using a Remote Authen... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_radius_settings.html.markdown) |
| `aws_directory_service_region` | ✅ | Manages a replicated Region and directory for Multi-Region replication. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_region.html.markdown) |
| `aws_directory_service_shared_directory` | ✅ | Manages a directory in your account (directory owner) shared with another acc... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_shared_directory.html.markdown) |
| `aws_directory_service_shared_directory_accepter` | ✅ | Accepts a shared directory in a consumer account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_shared_directory_accepter.html.markdown) |
| `aws_directory_service_trust` | ✅ | Manages a trust relationship between two Active Directory Directories. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/directory_service_trust.html.markdown) |

---

### Network Firewall

**产品代码**: `network_firewall`
**产品线分类**: 安全
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_networkfirewall_firewall` | ✅ | Provides an AWS Network Firewall Firewall Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_firewall.html.markdown) |
| `aws_networkfirewall_firewall_policy` | ✅ | Provides an AWS Network Firewall Firewall Policy Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_firewall_policy.html.markdown) |
| `aws_networkfirewall_firewall_transit_gateway_attachment_accepter` | ✅ | Manages an AWS Network Firewall Firewall Transit Gateway Attachment Accepter. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_firewall_transit_gateway_attachment_accepter.html.markdown) |
| `aws_networkfirewall_logging_configuration` | ✅ | Provides an AWS Network Firewall Logging Configuration Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_logging_configuration.html.markdown) |
| `aws_networkfirewall_resource_policy` | ✅ | Provides an AWS Network Firewall Resource Policy Resource for a rule group or... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_resource_policy.html.markdown) |
| `aws_networkfirewall_rule_group` | ✅ | Provides an AWS Network Firewall Rule Group Resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_rule_group.html.markdown) |
| `aws_networkfirewall_tls_inspection_configuration` | ✅ | Terraform resource for managing an AWS Network Firewall TLS Inspection Config... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_tls_inspection_configuration.html.markdown) |
| `aws_networkfirewall_vpc_endpoint_association` | ✅ | Manages a firewall endpoint for an AWS Network Firewall firewall. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkfirewall_vpc_endpoint_association.html.markdown) |

---

### Shield

**产品代码**: `shield`
**产品线分类**: 安全
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_shield_application_layer_automatic_response` | ✅ | Terraform resource for managing an AWS Shield Application Layer Automatic Res... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_application_layer_automatic_response.html.markdown) |
| `aws_shield_drt_access_log_bucket_association` | ✅ | Terraform resource for managing an AWS Shield DRT Access Log Bucket Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_drt_access_log_bucket_association.html.markdown) |
| `aws_shield_drt_access_role_arn_association` | ✅ | Authorizes the Shield Response Team (SRT) using the specified role, to access... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_drt_access_role_arn_association.html.markdown) |
| `aws_shield_proactive_engagement` | ✅ | Terraform resource for managing a AWS Shield Proactive Engagement. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_proactive_engagement.html.markdown) |
| `aws_shield_protection` | ✅ | Enables AWS Shield Advanced for a specific AWS resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_protection.html.markdown) |
| `aws_shield_protection_group` | ✅ | Creates a grouping of protected resources so they can be handled as a collect... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_protection_group.html.markdown) |
| `aws_shield_protection_health_check_association` | ✅ | Creates an association between a Route53 Health Check and a Shield Advanced p... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_protection_health_check_association.html.markdown) |
| `aws_shield_subscription` | ✅ | Terraform resource for managing an AWS Shield Subscription. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/shield_subscription.html.markdown) |

---

### Ram

**产品代码**: `ram`
**产品线分类**: 安全
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ram_permission` | ✅ | Manages an AWS RAM (Resource Access Manager) Permission. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ram_permission.html.markdown) |
| `aws_ram_principal_association` | ✅ | Provides a Resource Access Manager (RAM) principal association. Depending if ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ram_principal_association.html.markdown) |
| `aws_ram_resource_association` | ✅ | Manages a Resource Access Manager (RAM) Resource Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ram_resource_association.html.markdown) |
| `aws_ram_resource_share` | ✅ | Manages a Resource Access Manager (RAM) Resource Share. To associate principa... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ram_resource_share.html.markdown) |
| `aws_ram_resource_share_accepter` | ✅ | Manage accepting a Resource Access Manager (RAM) Resource Share invitation. F... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ram_resource_share_accepter.html.markdown) |
| `aws_ram_resource_share_associations_exclusive` | ✅ | Terraform resource for maintaining exclusive management of principal and reso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ram_resource_share_associations_exclusive.html.markdown) |
| `aws_ram_sharing_with_organization` | ✅ | Manages Resource Access Manager (RAM) Resource Sharing with AWS Organizations... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ram_sharing_with_organization.html.markdown) |

---

### Acm Pca

**产品代码**: `acm_pca`
**产品线分类**: 安全
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_acmpca_certificate` | ✅ | Provides a resource to issue a certificate using AWS Certificate Manager Priv... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/acmpca_certificate.html.markdown) |
| `aws_acmpca_certificate_authority` | ✅ | Provides a resource to manage AWS Certificate Manager Private Certificate Aut... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/acmpca_certificate_authority.html.markdown) |
| `aws_acmpca_certificate_authority_certificate` | ✅ | Associates a certificate with an AWS Certificate Manager Private Certificate ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/acmpca_certificate_authority_certificate.html.markdown) |
| `aws_acmpca_permission` | ✅ | Provides a resource to manage an AWS Certificate Manager Private Certificate ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/acmpca_permission.html.markdown) |
| `aws_acmpca_policy` | ✅ | Attaches a resource based policy to a private CA. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/acmpca_policy.html.markdown) |

---

### Detective

**产品代码**: `detective`
**产品线分类**: 安全
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_detective_graph` | ✅ | Provides a resource to manage an [AWS Detective Graph](https://docs.aws.amazo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/detective_graph.html.markdown) |
| `aws_detective_invitation_accepter` | ✅ | Provides a resource to manage an [Amazon Detective Invitation Accepter](https... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/detective_invitation_accepter.html.markdown) |
| `aws_detective_member` | ✅ | Provides a resource to manage an [Amazon Detective Member](https://docs.aws.a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/detective_member.html.markdown) |
| `aws_detective_organization_admin_account` | ✅ | Manages a Detective Organization Admin Account. The AWS account utilizing thi... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/detective_organization_admin_account.html.markdown) |
| `aws_detective_organization_configuration` | ✅ | Manages the Detective Organization Configuration in the current AWS Region. T... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/detective_organization_configuration.html.markdown) |

---

### Inspector

**产品代码**: `inspector`
**产品线分类**: 安全
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_inspector2_delegated_admin_account` | ✅ | Terraform resource for managing an Amazon Inspector Delegated Admin Account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector2_delegated_admin_account.html.markdown) |
| `aws_inspector2_enabler` | ✅ | Terraform resource for enabling Amazon Inspector resource scans. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector2_enabler.html.markdown) |
| `aws_inspector2_filter` | ✅ | Terraform resource for managing an AWS Inspector Filter. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector2_filter.html.markdown) |
| `aws_inspector2_member_association` | ✅ | Terraform resource for associating accounts to existing Inspector instances. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector2_member_association.html.markdown) |
| `aws_inspector2_organization_configuration` | ✅ | Terraform resource for managing an Amazon Inspector Organization Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector2_organization_configuration.html.markdown) |

---

### Security Lake

**产品代码**: `security_lake`
**产品线分类**: 安全
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_securitylake_aws_log_source` | ✅ | Terraform resource for managing an Amazon Security Lake AWS Log Source. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securitylake_aws_log_source.html.markdown) |
| `aws_securitylake_custom_log_source` | ✅ | Terraform resource for managing an AWS Security Lake Custom Log Source. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securitylake_custom_log_source.html.markdown) |
| `aws_securitylake_data_lake` | ✅ | Terraform resource for managing an AWS Security Lake Data Lake. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securitylake_data_lake.html.markdown) |
| `aws_securitylake_subscriber` | ✅ | Terraform resource for managing an AWS Security Lake Subscriber. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securitylake_subscriber.html.markdown) |
| `aws_securitylake_subscriber_notification` | ✅ | Terraform resource for managing an AWS Security Lake Subscriber Notification. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/securitylake_subscriber_notification.html.markdown) |

---

### Cognito Identity

**产品代码**: `cognito_identity`
**产品线分类**: 安全
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cognito_identity_pool` | ✅ | Provides an AWS Cognito Identity Pool. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_identity_pool.html.markdown) |
| `aws_cognito_identity_pool_provider_principal_tag` | ✅ | Provides an AWS Cognito Identity Principal Mapping. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_identity_pool_provider_principal_tag.html.markdown) |
| `aws_cognito_identity_pool_roles_attachment` | ✅ | Provides an AWS Cognito Identity Pool Roles Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cognito_identity_pool_roles_attachment.html.markdown) |

---

### Fms

**产品代码**: `fms`
**产品线分类**: 安全
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_fms_admin_account` | ✅ | Provides a resource to associate/disassociate an AWS Firewall Manager adminis... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fms_admin_account.html.markdown) |
| `aws_fms_policy` | ✅ | Provides a resource to create an AWS Firewall Manager policy. You need to be ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fms_policy.html.markdown) |
| `aws_fms_resource_set` | ✅ | Terraform resource for managing an AWS FMS (Firewall Manager) Resource Set. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fms_resource_set.html.markdown) |

---

### Inspector Classic

**产品代码**: `inspector_classic`
**产品线分类**: 安全
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_inspector_assessment_target` | ✅ | Provides an Inspector Classic Assessment Target | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector_assessment_target.html.markdown) |
| `aws_inspector_assessment_template` | ✅ | Provides an Inspector Classic Assessment Template | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector_assessment_template.html.markdown) |
| `aws_inspector_resource_group` | ✅ | Provides an Amazon Inspector Classic Resource Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/inspector_resource_group.html.markdown) |

---

### Mainframe Modernization

**产品代码**: `mainframe_modernization`
**产品线分类**: 安全
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_m2_application` | ✅ | Terraform resource for managing an [AWS Mainframe Modernization Application](... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/m2_application.html.markdown) |
| `aws_m2_deployment` | ✅ | Terraform resource for managing an [AWS Mainframe Modernization Deployment.](... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/m2_deployment.html.markdown) |
| `aws_m2_environment` | ✅ | Terraform resource for managing an [AWS Mainframe Modernization Environment](... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/m2_environment.html.markdown) |

---

### Iam Access Analyzer

**产品代码**: `iam_access_analyzer`
**产品线分类**: 安全
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_accessanalyzer_analyzer` | ✅ | Manages an Access Analyzer Analyzer. More information can be found in the [Ac... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/accessanalyzer_analyzer.html.markdown) |
| `aws_accessanalyzer_archive_rule` | ✅ | Terraform resource for managing an AWS AccessAnalyzer Archive Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/accessanalyzer_archive_rule.html.markdown) |

---

### Acm

**产品代码**: `acm`
**产品线分类**: 安全
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_acm_certificate` | ✅ | The ACM certificate resource allows requesting and management of certificates | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/acm_certificate.html.markdown) |
| `aws_acm_certificate_validation` | ✅ | This resource represents a successful validation of an ACM certificate in con... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/acm_certificate_validation.html.markdown) |

---

### Cloudhsm

**产品代码**: `cloudhsm`
**产品线分类**: 安全
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudhsm_v2_cluster` | ✅ | Creates an Amazon CloudHSM v2 cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudhsm_v2_cluster.html.markdown) |
| `aws_cloudhsm_v2_hsm` | ✅ | Creates an HSM module in Amazon CloudHSM v2 cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudhsm_v2_hsm.html.markdown) |

---

### Elemental Mediapackage

**产品代码**: `elemental_mediapackage`
**产品线分类**: 安全
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_media_package_channel` | ✅ | Provides an AWS Elemental MediaPackage Channel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/media_package_channel.html.markdown) |

---

### Elemental Mediapackage Version 2

**产品代码**: `elemental_mediapackage_version_2`
**产品线分类**: 安全
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_media_packagev2_channel_group` | ✅ | Creates an AWS Elemental MediaPackage Version 2 Channel Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/media_packagev2_channel_group.html.markdown) |

---

## 网络 (23 个产品)

### Virtual Private Cloud

**产品代码**: `vpc`
**产品线分类**: 网络
**资源数**: 67

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_default_network_acl` | ✅ | Provides a resource to manage a VPC's default network ACL. This resource can ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/default_network_acl.html.markdown) |
| `aws_default_route_table` | ✅ | Provides a resource to manage a default route table of a VPC. This resource c... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/default_route_table.html.markdown) |
| `aws_default_security_group` | ✅ | Provides a resource to manage a default security group. This resource can man... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/default_security_group.html.markdown) |
| `aws_default_subnet` | ✅ | Provides a resource to manage a [default subnet](http://docs.aws.amazon.com/A... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/default_subnet.html.markdown) |
| `aws_default_vpc` | ✅ | Provides a resource to manage the [default AWS VPC](http://docs.aws.amazon.co... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/default_vpc.html.markdown) |
| `aws_default_vpc_dhcp_options` | ✅ | Provides a resource to manage the [default AWS DHCP Options Set](http://docs.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/default_vpc_dhcp_options.html.markdown) |
| `aws_ec2_managed_prefix_list` | ✅ | Provides a managed prefix list resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_managed_prefix_list.html.markdown) |
| `aws_ec2_managed_prefix_list_entry` | ✅ | Use the `aws_prefix_list_entry` resource to manage a managed prefix list entry. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_managed_prefix_list_entry.html.markdown) |
| `aws_ec2_network_insights_analysis` | ✅ | Provides a Network Insights Analysis resource. Part of the "Reachability Anal... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_network_insights_analysis.html.markdown) |
| `aws_ec2_network_insights_path` | ✅ | Provides a Network Insights Path resource. Part of the "Reachability Analyzer... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_network_insights_path.html.markdown) |
| `aws_ec2_subnet_cidr_reservation` | ✅ | Provides a subnet CIDR reservation resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_subnet_cidr_reservation.html.markdown) |
| `aws_ec2_traffic_mirror_filter` | ✅ | Provides an Traffic mirror filter. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_traffic_mirror_filter.html.markdown) |
| `aws_ec2_traffic_mirror_filter_rule` | ✅ | Provides an Traffic mirror filter rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_traffic_mirror_filter_rule.html.markdown) |
| `aws_ec2_traffic_mirror_session` | ✅ | Provides an Traffic mirror session. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_traffic_mirror_session.html.markdown) |
| `aws_ec2_traffic_mirror_target` | ✅ | Provides a Traffic mirror target. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_traffic_mirror_target.html.markdown) |
| `aws_egress_only_internet_gateway` | ✅ | [IPv6 only] Creates an egress-only Internet gateway for your VPC. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/egress_only_internet_gateway.html.markdown) |
| `aws_flow_log` | ✅ | Provides a VPC/Subnet/ENI/Transit Gateway/Transit Gateway Attachment Flow Log... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/flow_log.html.markdown) |
| `aws_internet_gateway` | ✅ | Provides a resource to create a VPC Internet Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/internet_gateway.html.markdown) |
| `aws_internet_gateway_attachment` | ✅ | Provides a resource to create a VPC Internet Gateway Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/internet_gateway_attachment.html.markdown) |
| `aws_main_route_table_association` | ✅ | Provides a resource for managing the main routing table of a VPC. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/main_route_table_association.html.markdown) |
| `aws_nat_gateway` | ✅ | Provides a resource to create a VPC NAT Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/nat_gateway.html.markdown) |
| `aws_nat_gateway_eip_association` | ✅ | Terraform resource for managing an AWS VPC NAT Gateway EIP Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/nat_gateway_eip_association.html.markdown) |
| `aws_network_acl` | ✅ | Provides an network ACL resource. You might set up network ACLs with rules si... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/network_acl.html.markdown) |
| `aws_network_acl_association` | ✅ | Provides an network ACL association resource which allows you to associate yo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/network_acl_association.html.markdown) |
| `aws_network_acl_rule` | ✅ | Creates an entry (a rule) in a network ACL with the specified rule number. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/network_acl_rule.html.markdown) |
| `aws_network_interface` | ✅ | Provides an Elastic network interface (ENI) resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/network_interface.html.markdown) |
| `aws_network_interface_attachment` | ✅ | Attach an Elastic network interface (ENI) resource with EC2 instance. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/network_interface_attachment.html.markdown) |
| `aws_network_interface_permission` | ✅ | Grant cross-account access to an Elastic network interface (ENI). | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/network_interface_permission.html.markdown) |
| `aws_network_interface_sg_attachment` | ✅ | This resource attaches a security group to an Elastic Network Interface (ENI). | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/network_interface_sg_attachment.html.markdown) |
| `aws_route` | ✅ | Provides a resource to create a routing table entry (a route) in a VPC routin... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route.html.markdown) |
| `aws_route_table` | ✅ | Provides a resource to create a VPC routing table. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route_table.html.markdown) |
| `aws_route_table_association` | ✅ | Provides a resource to create an association between a route table and a subn... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route_table_association.html.markdown) |
| `aws_security_group` | ✅ | Provides a security group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/security_group.html.markdown) |
| `aws_security_group_rule` | ✅ | Provides a security group rule resource. Represents a single `ingress` or `eg... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/security_group_rule.html.markdown) |
| `aws_subnet` | ✅ | Provides an VPC subnet resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/subnet.html.markdown) |
| `aws_vpc` | ✅ | Provides a VPC resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc.html.markdown) |
| `aws_vpc_block_public_access_exclusion` | ✅ | Terraform resource for managing an AWS EC2 (Elastic Compute Cloud) VPC Block ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_block_public_access_exclusion.html.markdown) |
| `aws_vpc_block_public_access_options` | ✅ | Terraform resource for managing an AWS VPC Block Public Access Options. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_block_public_access_options.html.markdown) |
| `aws_vpc_dhcp_options` | ✅ | Provides a VPC DHCP Options resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_dhcp_options.html.markdown) |
| `aws_vpc_dhcp_options_association` | ✅ | Provides a VPC DHCP Options Association resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_dhcp_options_association.html.markdown) |
| `aws_vpc_encryption_control` | ✅ | Manages a VPC Encryption Control. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_encryption_control.html.markdown) |
| `aws_vpc_endpoint` | ✅ | Provides a VPC Endpoint resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint.html.markdown) |
| `aws_vpc_endpoint_connection_accepter` | ✅ | Provides a resource to accept a pending VPC Endpoint Connection accept reques... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_connection_accepter.html.markdown) |
| `aws_vpc_endpoint_connection_notification` | ✅ | Provides a VPC Endpoint connection notification resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_connection_notification.html.markdown) |
| `aws_vpc_endpoint_policy` | ✅ | Provides a VPC Endpoint Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_policy.html.markdown) |
| `aws_vpc_endpoint_private_dns` | ✅ | Terraform resource for enabling private DNS on an AWS VPC (Virtual Private Cl... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_private_dns.html.markdown) |
| `aws_vpc_endpoint_route_table_association` | ✅ | Manages a VPC Endpoint Route Table Association | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_route_table_association.html.markdown) |
| `aws_vpc_endpoint_security_group_association` | ✅ | Provides a resource to create an association between a VPC endpoint and a sec... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_security_group_association.html.markdown) |
| `aws_vpc_endpoint_service` | ✅ | Provides a VPC Endpoint Service resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_service.html.markdown) |
| `aws_vpc_endpoint_service_allowed_principal` | ✅ | Provides a resource to allow a principal to discover a VPC endpoint service. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_service_allowed_principal.html.markdown) |
| `aws_vpc_endpoint_service_private_dns_verification` | ✅ | Terraform resource for managing an AWS VPC (Virtual Private Cloud) Endpoint S... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_service_private_dns_verification.html.markdown) |
| `aws_vpc_endpoint_subnet_association` | ✅ | Provides a resource to create an association between a VPC endpoint and a sub... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_endpoint_subnet_association.html.markdown) |
| `aws_vpc_ipv4_cidr_block_association` | ✅ | Provides a resource to associate additional IPv4 CIDR blocks with a VPC. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipv4_cidr_block_association.html.markdown) |
| `aws_vpc_ipv6_cidr_block_association` | ✅ | Provides a resource to associate additional IPv6 CIDR blocks with a VPC. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipv6_cidr_block_association.html.markdown) |
| `aws_vpc_network_performance_metric_subscription` | ✅ | Provides a resource to manage an Infrastructure Performance subscription. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_network_performance_metric_subscription.html.markdown) |
| `aws_vpc_peering_connection` | ✅ | Provides a resource to manage a VPC peering connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_peering_connection.html.markdown) |
| `aws_vpc_peering_connection_accepter` | ✅ | Provides a resource to manage the accepter's side of a VPC Peering Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_peering_connection_accepter.html.markdown) |
| `aws_vpc_peering_connection_options` | ✅ | Provides a resource to manage VPC peering connection options. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_peering_connection_options.html.markdown) |
| `aws_vpc_route_server` | ✅ | Provides a resource for managing a VPC (Virtual Private Cloud) Route Server. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_route_server.html.markdown) |
| `aws_vpc_route_server_endpoint` | ✅ | Provides a resource for managing a VPC (Virtual Private Cloud) Route Server E... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_route_server_endpoint.html.markdown) |
| `aws_vpc_route_server_peer` | ✅ | Provides a resource for managing a VPC (Virtual Private Cloud) Route Server P... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_route_server_peer.html.markdown) |
| `aws_vpc_route_server_propagation` | ✅ | Provides a resource for managing propagation between VPC (Virtual Private Clo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_route_server_propagation.html.markdown) |
| `aws_vpc_route_server_vpc_association` | ✅ | Provides a resource for managing association between VPC (Virtual Private Clo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_route_server_vpc_association.html.markdown) |
| `aws_vpc_security_group_egress_rule` | ✅ | Manages an outbound (egress) rule for a security group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_security_group_egress_rule.html.markdown) |
| `aws_vpc_security_group_ingress_rule` | ✅ | Manages an inbound (ingress) rule for a security group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_security_group_ingress_rule.html.markdown) |
| `aws_vpc_security_group_rules_exclusive` | ✅ | Terraform resource for managing an exclusive set of AWS VPC (Virtual Private ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_security_group_rules_exclusive.html.markdown) |
| `aws_vpc_security_group_vpc_association` | ✅ | Terraform resource for managing Security Group VPC Associations. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_security_group_vpc_association.html.markdown) |

---

### Api Gateway

**产品代码**: `api_gateway`
**产品线分类**: 网络
**资源数**: 26

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_api_gateway_account` | ✅ | Provides a settings of an API Gateway Account. Settings is applied region-wid... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_account.html.markdown) |
| `aws_api_gateway_api_key` | ✅ | Provides an API Gateway API Key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_api_key.html.markdown) |
| `aws_api_gateway_authorizer` | ✅ | Provides an API Gateway Authorizer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_authorizer.html.markdown) |
| `aws_api_gateway_base_path_mapping` | ✅ | Connects a custom domain name registered via `aws_api_gateway_domain_name` | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_base_path_mapping.html.markdown) |
| `aws_api_gateway_client_certificate` | ✅ | Provides an API Gateway Client Certificate. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_client_certificate.html.markdown) |
| `aws_api_gateway_deployment` | ✅ | Manages an API Gateway REST Deployment. A deployment is a snapshot of the RES... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_deployment.html.markdown) |
| `aws_api_gateway_documentation_part` | ✅ | Provides a settings of an API Gateway Documentation Part. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_documentation_part.html.markdown) |
| `aws_api_gateway_documentation_version` | ✅ | Provides a resource to manage an API Gateway Documentation Version. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_documentation_version.html.markdown) |
| `aws_api_gateway_domain_name` | ✅ | Registers a custom domain name for use with AWS API Gateway. Additional infor... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_domain_name.html.markdown) |
| `aws_api_gateway_domain_name_access_association` | ✅ | Creates a domain name access association resource between an access associati... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_domain_name_access_association.html.markdown) |
| `aws_api_gateway_gateway_response` | ✅ | Provides an API Gateway Gateway Response for a REST API Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_gateway_response.html.markdown) |
| `aws_api_gateway_integration` | ✅ | Provides an HTTP Method Integration for an API Gateway Integration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_integration.html.markdown) |
| `aws_api_gateway_integration_response` | ✅ | Provides an HTTP Method Integration Response for an API Gateway Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_integration_response.html.markdown) |
| `aws_api_gateway_method` | ✅ | Provides a HTTP Method for an API Gateway Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_method.html.markdown) |
| `aws_api_gateway_method_response` | ✅ | Provides an HTTP Method Response for an API Gateway Resource. More informatio... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_method_response.html.markdown) |
| `aws_api_gateway_method_settings` | ✅ | Manages API Gateway Stage Method Settings. For example, CloudWatch logging an... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_method_settings.html.markdown) |
| `aws_api_gateway_model` | ✅ | Provides a Model for a REST API Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_model.html.markdown) |
| `aws_api_gateway_request_validator` | ✅ | Manages an API Gateway Request Validator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_request_validator.html.markdown) |
| `aws_api_gateway_resource` | ✅ | Provides an API Gateway Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_resource.html.markdown) |
| `aws_api_gateway_rest_api` | ✅ | Manages an API Gateway REST API. The REST API can be configured via [importin... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_rest_api.html.markdown) |
| `aws_api_gateway_rest_api_policy` | ✅ | Provides an API Gateway REST API Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_rest_api_policy.html.markdown) |
| `aws_api_gateway_rest_api_put` | ✅ | Terraform resource for updating an AWS API Gateway REST API with a new API de... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_rest_api_put.html.markdown) |
| `aws_api_gateway_stage` | ✅ | Manages an API Gateway Stage. A stage is a named reference to a deployment, w... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_stage.html.markdown) |
| `aws_api_gateway_usage_plan` | ✅ | Provides an API Gateway Usage Plan. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_usage_plan.html.markdown) |
| `aws_api_gateway_usage_plan_key` | ✅ | Provides an API Gateway Usage Plan Key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_usage_plan_key.html.markdown) |
| `aws_api_gateway_vpc_link` | ✅ | Provides an API Gateway VPC Link. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/api_gateway_vpc_link.html.markdown) |

---

### Transit Gateway

**产品代码**: `transit_gateway`
**产品线分类**: 网络
**资源数**: 22

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ec2_transit_gateway` | ✅ | Manages an EC2 Transit Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway.html.markdown) |
| `aws_ec2_transit_gateway_connect` | ✅ | Manages an EC2 Transit Gateway Connect. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_connect.html.markdown) |
| `aws_ec2_transit_gateway_connect_peer` | ✅ | Manages an EC2 Transit Gateway Connect Peer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_connect_peer.html.markdown) |
| `aws_ec2_transit_gateway_default_route_table_association` | ✅ | Terraform resource for managing an AWS EC2 (Elastic Compute Cloud) Transit Ga... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_default_route_table_association.html.markdown) |
| `aws_ec2_transit_gateway_default_route_table_propagation` | ✅ | Terraform resource for managing an AWS EC2 (Elastic Compute Cloud) Transit Ga... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_default_route_table_propagation.html.markdown) |
| `aws_ec2_transit_gateway_metering_policy` | ✅ | Manages an EC2 Transit Gateway Metering Policy for Flexible Cost Allocation (... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_metering_policy.html.markdown) |
| `aws_ec2_transit_gateway_metering_policy_entry` | ✅ | Manages an EC2 Transit Gateway Metering Policy Entry. Each entry defines a tr... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_metering_policy_entry.html.markdown) |
| `aws_ec2_transit_gateway_multicast_domain` | ✅ | Manages an EC2 Transit Gateway Multicast Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_multicast_domain.html.markdown) |
| `aws_ec2_transit_gateway_multicast_domain_association` | ✅ | Associates the specified subnet and transit gateway attachment with the speci... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_multicast_domain_association.html.markdown) |
| `aws_ec2_transit_gateway_multicast_group_member` | ✅ | Registers members (network interfaces) with the transit gateway multicast group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_multicast_group_member.html.markdown) |
| `aws_ec2_transit_gateway_multicast_group_source` | ✅ | Registers sources (network interfaces) with the transit gateway multicast group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_multicast_group_source.html.markdown) |
| `aws_ec2_transit_gateway_peering_attachment` | ✅ | Manages an EC2 Transit Gateway Peering Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_peering_attachment.html.markdown) |
| `aws_ec2_transit_gateway_peering_attachment_accepter` | ✅ | Manages the accepter's side of an EC2 Transit Gateway Peering Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_peering_attachment_accepter.html.markdown) |
| `aws_ec2_transit_gateway_policy_table` | ✅ | Manages an EC2 Transit Gateway Policy Table. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_policy_table.html.markdown) |
| `aws_ec2_transit_gateway_policy_table_association` | ✅ | Manages an EC2 Transit Gateway Policy Table association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_policy_table_association.html.markdown) |
| `aws_ec2_transit_gateway_prefix_list_reference` | ✅ | Manages an EC2 Transit Gateway Prefix List Reference. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_prefix_list_reference.html.markdown) |
| `aws_ec2_transit_gateway_route` | ✅ | Manages an EC2 Transit Gateway Route. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_route.html.markdown) |
| `aws_ec2_transit_gateway_route_table` | ✅ | Manages an EC2 Transit Gateway Route Table. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_route_table.html.markdown) |
| `aws_ec2_transit_gateway_route_table_association` | ✅ | Manages an EC2 Transit Gateway Route Table association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_route_table_association.html.markdown) |
| `aws_ec2_transit_gateway_route_table_propagation` | ✅ | Manages an EC2 Transit Gateway Route Table propagation. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_route_table_propagation.html.markdown) |
| `aws_ec2_transit_gateway_vpc_attachment` | ✅ | Manages an EC2 Transit Gateway VPC Attachment. For examples of custom route t... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_vpc_attachment.html.markdown) |
| `aws_ec2_transit_gateway_vpc_attachment_accepter` | ✅ | Manages the accepter's side of an EC2 Transit Gateway VPC Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_transit_gateway_vpc_attachment_accepter.html.markdown) |

---

### Network Manager

**产品代码**: `network_manager`
**产品线分类**: 网络
**资源数**: 21

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_networkmanager_attachment_accepter` | ✅ | Manages an AWS Network Manager Attachment Accepter. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_attachment_accepter.html.markdown) |
| `aws_networkmanager_attachment_routing_policy_label` | ✅ | Associates a routing policy label to a Network Manager Cloud WAN's attachment... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_attachment_routing_policy_label.html.markdown) |
| `aws_networkmanager_connect_attachment` | ✅ | Manages an AWS Network Manager Connect Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_connect_attachment.html.markdown) |
| `aws_networkmanager_connect_peer` | ✅ | Manages an AWS Network Manager Connect Peer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_connect_peer.html.markdown) |
| `aws_networkmanager_connection` | ✅ | Manages a Network Manager Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_connection.html.markdown) |
| `aws_networkmanager_core_network` | ✅ | Manages a Network Manager Core Network. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_core_network.html.markdown) |
| `aws_networkmanager_core_network_policy_attachment` | ✅ | Manages a Network Manager Core Network Policy Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_core_network_policy_attachment.html.markdown) |
| `aws_networkmanager_customer_gateway_association` | ✅ | Manages a Network Manager Customer Gateway Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_customer_gateway_association.html.markdown) |
| `aws_networkmanager_device` | ✅ | Manages a Network Manager Device. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_device.html.markdown) |
| `aws_networkmanager_dx_gateway_attachment` | ✅ | Manages a Network Manager Direct Connect Gateway Attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_dx_gateway_attachment.html.markdown) |
| `aws_networkmanager_global_network` | ✅ | Manages a Network Manager Global Network. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_global_network.html.markdown) |
| `aws_networkmanager_link` | ✅ | Manages a Network Manager link. Use this resource to create a link for a site. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_link.html.markdown) |
| `aws_networkmanager_link_association` | ✅ | Manages a Network Manager link association. Associates a link to a device. A ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_link_association.html.markdown) |
| `aws_networkmanager_prefix_list_association` | ✅ | Associates an EC2 managed prefix list with a Network Manager Cloud WAN core n... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_prefix_list_association.html.markdown) |
| `aws_networkmanager_site` | ✅ | Manages a Network Manager site. Use this resource to create a site in a globa... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_site.html.markdown) |
| `aws_networkmanager_site_to_site_vpn_attachment` | ✅ | Manages a Network Manager site-to-site VPN attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_site_to_site_vpn_attachment.html.markdown) |
| `aws_networkmanager_transit_gateway_connect_peer_association` | ✅ | Manages a Network Manager transit gateway Connect peer association. Associate... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_transit_gateway_connect_peer_association.html.markdown) |
| `aws_networkmanager_transit_gateway_peering` | ✅ | Manages a Network Manager transit gateway peering connection. Creates a peeri... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_transit_gateway_peering.html.markdown) |
| `aws_networkmanager_transit_gateway_registration` | ✅ | Manages a Network Manager transit gateway registration. Registers a transit g... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_transit_gateway_registration.html.markdown) |
| `aws_networkmanager_transit_gateway_route_table_attachment` | ✅ | Manages a Network Manager transit gateway route table attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_transit_gateway_route_table_attachment.html.markdown) |
| `aws_networkmanager_vpc_attachment` | ✅ | Manages a Network Manager VPC attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmanager_vpc_attachment.html.markdown) |

---

### Direct Connect

**产品代码**: `direct_connect`
**产品线分类**: 网络
**资源数**: 19

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_dx_bgp_peer` | ✅ | Provides a Direct Connect BGP peer resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_bgp_peer.html.markdown) |
| `aws_dx_connection` | ✅ | Provides a Connection of Direct Connect. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_connection.html.markdown) |
| `aws_dx_connection_association` | ✅ | Associates a Direct Connect Connection with a LAG. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_connection_association.html.markdown) |
| `aws_dx_connection_confirmation` | ✅ | Provides a confirmation of the creation of the specified hosted connection on... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_connection_confirmation.html.markdown) |
| `aws_dx_gateway` | ✅ | Provides a Direct Connect Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_gateway.html.markdown) |
| `aws_dx_gateway_association` | ✅ | Associates a Direct Connect Gateway with a VGW or transit gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_gateway_association.html.markdown) |
| `aws_dx_gateway_association_proposal` | ✅ | Manages a Direct Connect Gateway Association Proposal, typically for enabling... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_gateway_association_proposal.html.markdown) |
| `aws_dx_hosted_connection` | ✅ | Provides a hosted connection on the specified interconnect or a link aggregat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_hosted_connection.html.markdown) |
| `aws_dx_hosted_private_virtual_interface` | ✅ | Provides a Direct Connect hosted private virtual interface resource. This res... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_hosted_private_virtual_interface.html.markdown) |
| `aws_dx_hosted_private_virtual_interface_accepter` | ✅ | Provides a resource to manage the accepter's side of a Direct Connect hosted ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_hosted_private_virtual_interface_accepter.html.markdown) |
| `aws_dx_hosted_public_virtual_interface` | ✅ | Provides a Direct Connect hosted public virtual interface resource. This reso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_hosted_public_virtual_interface.html.markdown) |
| `aws_dx_hosted_public_virtual_interface_accepter` | ✅ | Provides a resource to manage the accepter's side of a Direct Connect hosted ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_hosted_public_virtual_interface_accepter.html.markdown) |
| `aws_dx_hosted_transit_virtual_interface` | ✅ | Provides a Direct Connect hosted transit virtual interface resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_hosted_transit_virtual_interface.html.markdown) |
| `aws_dx_hosted_transit_virtual_interface_accepter` | ✅ | Provides a resource to manage the accepter's side of a Direct Connect hosted ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_hosted_transit_virtual_interface_accepter.html.markdown) |
| `aws_dx_lag` | ✅ | Provides a Direct Connect LAG. Connections can be added to the LAG via the [`... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_lag.html.markdown) |
| `aws_dx_macsec_key_association` | ✅ | Provides a MAC Security (MACSec) secret key resource for use with Direct Conn... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_macsec_key_association.html.markdown) |
| `aws_dx_private_virtual_interface` | ✅ | Provides a Direct Connect private virtual interface resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_private_virtual_interface.html.markdown) |
| `aws_dx_public_virtual_interface` | ✅ | Provides a Direct Connect public virtual interface resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_public_virtual_interface.html.markdown) |
| `aws_dx_transit_virtual_interface` | ✅ | Provides a Direct Connect transit virtual interface resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dx_transit_virtual_interface.html.markdown) |

---

### Vpc Lattice

**产品代码**: `vpc_lattice`
**产品线分类**: 网络
**资源数**: 15

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_vpclattice_access_log_subscription` | ✅ | Terraform resource for managing an AWS VPC Lattice Service Network or Service... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_access_log_subscription.html.markdown) |
| `aws_vpclattice_auth_policy` | ✅ | Terraform resource for managing an AWS VPC Lattice Auth Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_auth_policy.html.markdown) |
| `aws_vpclattice_domain_verification` | ✅ | Terraform resource for managing an AWS VPC Lattice Domain Verification. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_domain_verification.html.markdown) |
| `aws_vpclattice_listener` | ✅ | Terraform resource for managing an AWS VPC Lattice Listener. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_listener.html.markdown) |
| `aws_vpclattice_listener_rule` | ✅ | Terraform resource for managing an AWS VPC Lattice Listener Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_listener_rule.html.markdown) |
| `aws_vpclattice_resource_configuration` | ✅ | Terraform resource for managing an AWS VPC Lattice Resource Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_resource_configuration.html.markdown) |
| `aws_vpclattice_resource_gateway` | ✅ | Terraform resource for managing an AWS VPC Lattice Resource Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_resource_gateway.html.markdown) |
| `aws_vpclattice_resource_policy` | ✅ | Terraform resource for managing an AWS VPC Lattice Resource Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_resource_policy.html.markdown) |
| `aws_vpclattice_service` | ✅ | Terraform resource for managing an AWS VPC Lattice Service. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_service.html.markdown) |
| `aws_vpclattice_service_network` | ✅ | Terraform resource for managing an AWS VPC Lattice Service Network. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_service_network.html.markdown) |
| `aws_vpclattice_service_network_resource_association` | ✅ | Terraform resource for managing an AWS VPC Lattice Service Network Resource A... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_service_network_resource_association.html.markdown) |
| `aws_vpclattice_service_network_service_association` | ✅ | Terraform resource for managing an AWS VPC Lattice Service Network Service As... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_service_network_service_association.html.markdown) |
| `aws_vpclattice_service_network_vpc_association` | ✅ | Terraform resource for managing an AWS VPC Lattice Service Network VPC Associ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_service_network_vpc_association.html.markdown) |
| `aws_vpclattice_target_group` | ✅ | Terraform resource for managing an AWS VPC Lattice Target Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_target_group.html.markdown) |
| `aws_vpclattice_target_group_attachment` | ✅ | Provides the ability to register a target with an AWS VPC Lattice Target Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpclattice_target_group_attachment.html.markdown) |

---

### Route 53

**产品代码**: `route_53`
**产品线分类**: 网络
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_route53_cidr_collection` | ✅ | Provides a Route53 CIDR collection resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_cidr_collection.html.markdown) |
| `aws_route53_cidr_location` | ✅ | Provides a Route53 CIDR location resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_cidr_location.html.markdown) |
| `aws_route53_delegation_set` | ✅ | Provides a [Route53 Delegation Set](https://docs.aws.amazon.com/Route53/lates... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_delegation_set.html.markdown) |
| `aws_route53_health_check` | ✅ | Provides a Route53 health check. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_health_check.html.markdown) |
| `aws_route53_hosted_zone_dnssec` | ✅ | Manages Route 53 Hosted Zone Domain Name System Security Extensions (DNSSEC).... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_hosted_zone_dnssec.html.markdown) |
| `aws_route53_key_signing_key` | ✅ | Manages a Route 53 Key Signing Key. To manage Domain Name System Security Ext... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_key_signing_key.html.markdown) |
| `aws_route53_query_log` | ✅ | Provides a Route53 query logging configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_query_log.html.markdown) |
| `aws_route53_record` | ✅ | Provides a Route53 record resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_record.html.markdown) |
| `aws_route53_records_exclusive` | ✅ | Terraform resource for maintaining exclusive management of resource record se... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_records_exclusive.html.markdown) |
| `aws_route53_traffic_policy` | ✅ | Manages a Route53 Traffic Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_traffic_policy.html.markdown) |
| `aws_route53_traffic_policy_instance` | ✅ | Provides a Route53 traffic policy instance resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_traffic_policy_instance.html.markdown) |
| `aws_route53_vpc_association_authorization` | ✅ | Authorizes a VPC in a different account to be associated with a local Route53... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_vpc_association_authorization.html.markdown) |
| `aws_route53_zone` | ✅ | Manages a Route53 Hosted Zone. For managing Domain Name System Security Exten... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_zone.html.markdown) |
| `aws_route53_zone_association` | ✅ | Manages a Route53 Hosted Zone VPC association. VPC associations can only be m... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_zone_association.html.markdown) |

---

### Api Gateway V2

**产品代码**: `api_gateway_v2`
**产品线分类**: 网络
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_apigatewayv2_api` | ✅ | Manages an Amazon API Gateway Version 2 API. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_api.html.markdown) |
| `aws_apigatewayv2_api_mapping` | ✅ | Manages an Amazon API Gateway Version 2 API mapping. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_api_mapping.html.markdown) |
| `aws_apigatewayv2_authorizer` | ✅ | Manages an Amazon API Gateway Version 2 authorizer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_authorizer.html.markdown) |
| `aws_apigatewayv2_deployment` | ✅ | Manages an Amazon API Gateway Version 2 deployment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_deployment.html.markdown) |
| `aws_apigatewayv2_domain_name` | ✅ | Manages an Amazon API Gateway Version 2 domain name. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_domain_name.html.markdown) |
| `aws_apigatewayv2_integration` | ✅ | Manages an Amazon API Gateway Version 2 integration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_integration.html.markdown) |
| `aws_apigatewayv2_integration_response` | ✅ | Manages an Amazon API Gateway Version 2 integration response. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_integration_response.html.markdown) |
| `aws_apigatewayv2_model` | ✅ | Manages an Amazon API Gateway Version 2 [model](https://docs.aws.amazon.com/a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_model.html.markdown) |
| `aws_apigatewayv2_route` | ✅ | Manages an Amazon API Gateway Version 2 route. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_route.html.markdown) |
| `aws_apigatewayv2_route_response` | ✅ | Manages an Amazon API Gateway Version 2 route response. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_route_response.html.markdown) |
| `aws_apigatewayv2_routing_rule` | ✅ | Terraform resource for managing an AWS API Gateway V2 Routing Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_routing_rule.html.markdown) |
| `aws_apigatewayv2_stage` | ✅ | Manages an Amazon API Gateway Version 2 stage. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_stage.html.markdown) |
| `aws_apigatewayv2_vpc_link` | ✅ | Manages an Amazon API Gateway Version 2 VPC Link. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apigatewayv2_vpc_link.html.markdown) |

---

### Route 53 Resolver

**产品代码**: `route_53_resolver`
**产品线分类**: 网络
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_route53_resolver_config` | ✅ | Provides a Route 53 Resolver config resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_config.html.markdown) |
| `aws_route53_resolver_dnssec_config` | ✅ | Provides a Route 53 Resolver DNSSEC config resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_dnssec_config.html.markdown) |
| `aws_route53_resolver_endpoint` | ✅ | Provides a Route 53 Resolver endpoint resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_endpoint.html.markdown) |
| `aws_route53_resolver_firewall_config` | ✅ | Provides a Route 53 Resolver DNS Firewall config resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_firewall_config.html.markdown) |
| `aws_route53_resolver_firewall_domain_list` | ✅ | Provides a Route 53 Resolver DNS Firewall domain list resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_firewall_domain_list.html.markdown) |
| `aws_route53_resolver_firewall_rule` | ✅ | Provides a Route 53 Resolver DNS Firewall rule resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_firewall_rule.html.markdown) |
| `aws_route53_resolver_firewall_rule_group` | ✅ | Provides a Route 53 Resolver DNS Firewall rule group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_firewall_rule_group.html.markdown) |
| `aws_route53_resolver_firewall_rule_group_association` | ✅ | Provides a Route 53 Resolver DNS Firewall rule group association resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_firewall_rule_group_association.html.markdown) |
| `aws_route53_resolver_query_log_config` | ✅ | Provides a Route 53 Resolver query logging configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_query_log_config.html.markdown) |
| `aws_route53_resolver_query_log_config_association` | ✅ | Provides a Route 53 Resolver query logging configuration association resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_query_log_config_association.html.markdown) |
| `aws_route53_resolver_rule` | ✅ | Provides a Route53 Resolver rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_rule.html.markdown) |
| `aws_route53_resolver_rule_association` | ✅ | Provides a Route53 Resolver rule association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53_resolver_rule_association.html.markdown) |

---

### Vpn

**产品代码**: `vpn`
**产品线分类**: 网络
**资源数**: 11

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_customer_gateway` | ✅ | Provides a customer gateway inside a VPC. These objects can be connected to V... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/customer_gateway.html.markdown) |
| `aws_ec2_client_vpn_authorization_rule` | ✅ | Provides authorization rules for AWS Client VPN endpoints. For more informati... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_client_vpn_authorization_rule.html.markdown) |
| `aws_ec2_client_vpn_endpoint` | ✅ | Provides an AWS Client VPN endpoint for OpenVPN clients. For more information... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_client_vpn_endpoint.html.markdown) |
| `aws_ec2_client_vpn_network_association` | ✅ | Provides network associations for AWS Client VPN endpoints. For more informat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_client_vpn_network_association.html.markdown) |
| `aws_ec2_client_vpn_route` | ✅ | Provides additional routes for AWS Client VPN endpoints. For more information... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_client_vpn_route.html.markdown) |
| `aws_vpn_concentrator` | ✅ | Provides a resource to create a VPN Concentrator that aggregates multiple VPN... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpn_concentrator.html.markdown) |
| `aws_vpn_connection` | ✅ | Manages a Site-to-Site VPN connection. A Site-to-Site VPN connection is an In... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpn_connection.html.markdown) |
| `aws_vpn_connection_route` | ✅ | Provides a static route between a VPN connection and a customer gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpn_connection_route.html.markdown) |
| `aws_vpn_gateway` | ✅ | Provides a resource to create a VPC VPN Gateway. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpn_gateway.html.markdown) |
| `aws_vpn_gateway_attachment` | ✅ | Provides a Virtual Private Gateway attachment resource, allowing for an existing | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpn_gateway_attachment.html.markdown) |
| `aws_vpn_gateway_route_propagation` | ✅ | Requests automatic route propagation between a VPN gateway and a route table. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpn_gateway_route_propagation.html.markdown) |

---

### Elb Classic

**产品代码**: `elb_classic`
**产品线分类**: 网络
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_app_cookie_stickiness_policy` | ✅ | Provides an application cookie stickiness policy, which allows an ELB to wed ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/app_cookie_stickiness_policy.html.markdown) |
| `aws_elb` | ✅ | Provides an Elastic Load Balancer resource, also known as a "Classic | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elb.html.markdown) |
| `aws_elb_attachment` | ✅ | Attaches an EC2 instance to an Elastic Load Balancer (ELB). For attaching res... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elb_attachment.html.markdown) |
| `aws_lb_cookie_stickiness_policy` | ✅ | Provides a load balancer cookie stickiness policy, which allows an ELB to con... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_cookie_stickiness_policy.html.markdown) |
| `aws_lb_ssl_negotiation_policy` | ✅ | Provides a load balancer SSL negotiation policy, which allows an ELB to contr... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_ssl_negotiation_policy.html.markdown) |
| `aws_load_balancer_backend_server_policy` | ✅ | Attaches a load balancer policy to an ELB backend server. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/load_balancer_backend_server_policy.html.markdown) |
| `aws_load_balancer_listener_policy` | ✅ | Attaches a load balancer policy to an ELB Listener. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/load_balancer_listener_policy.html.markdown) |
| `aws_load_balancer_policy` | ✅ | Provides a load balancer policy, which can be attached to an ELB listener or ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/load_balancer_policy.html.markdown) |
| `aws_proxy_protocol_policy` | ✅ | Provides a proxy protocol policy, which allows an ELB to carry a client conne... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/proxy_protocol_policy.html.markdown) |

---

### Vpc Ipam

**产品代码**: `vpc_ipam`
**产品线分类**: 网络
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_vpc_ipam` | ✅ | Provides an IPAM resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam.html.markdown) |
| `aws_vpc_ipam_organization_admin_account` | ✅ | Enables the IPAM Service and promotes a delegated administrator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_organization_admin_account.html.markdown) |
| `aws_vpc_ipam_pool` | ✅ | Provides an IP address pool resource for IPAM. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_pool.html.markdown) |
| `aws_vpc_ipam_pool_cidr` | ✅ | Provisions a CIDR from an IPAM address pool. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_pool_cidr.html.markdown) |
| `aws_vpc_ipam_pool_cidr_allocation` | ✅ | Allocates (reserves) a CIDR from an IPAM address pool, preventing usage by IP... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_pool_cidr_allocation.html.markdown) |
| `aws_vpc_ipam_preview_next_cidr` | ✅ | Previews a CIDR from an IPAM address pool. Only works for private IPv4. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_preview_next_cidr.html.markdown) |
| `aws_vpc_ipam_resource_discovery` | ✅ | Provides an IPAM Resource Discovery resource. IPAM Resource Discoveries are r... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_resource_discovery.html.markdown) |
| `aws_vpc_ipam_resource_discovery_association` | ✅ | Provides an association between an Amazon IP Address Manager (IPAM) and a IPA... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_resource_discovery_association.html.markdown) |
| `aws_vpc_ipam_scope` | ✅ | Creates a scope for AWS IPAM. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/vpc_ipam_scope.html.markdown) |

---

### Elastic Load Balancing

**产品代码**: `elb`
**产品线分类**: 网络
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_lb` | ✅ | Provides a Load Balancer resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb.html.markdown) |
| `aws_lb_listener` | ✅ | Provides a Load Balancer Listener resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_listener.html.markdown) |
| `aws_lb_listener_certificate` | ✅ | Provides a Load Balancer Listener Certificate resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_listener_certificate.html.markdown) |
| `aws_lb_listener_rule` | ✅ | Provides a Load Balancer Listener Rule resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_listener_rule.html.markdown) |
| `aws_lb_target_group` | ✅ | Provides a Target Group resource for use with Load Balancer resources. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_target_group.html.markdown) |
| `aws_lb_target_group_attachment` | ✅ | Provides the ability to register instances and containers with an Application... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_target_group_attachment.html.markdown) |
| `aws_lb_trust_store` | ✅ | Provides a ELBv2 Trust Store for use with Application Load Balancer Listener ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_trust_store.html.markdown) |
| `aws_lb_trust_store_revocation` | ✅ | Provides a ELBv2 Trust Store Revocation for use with Application Load Balance... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lb_trust_store_revocation.html.markdown) |

---

### Global Accelerator

**产品代码**: `global_accelerator`
**产品线分类**: 网络
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_globalaccelerator_accelerator` | ✅ | Creates a Global Accelerator accelerator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/globalaccelerator_accelerator.html.markdown) |
| `aws_globalaccelerator_cross_account_attachment` | ✅ | Terraform resource for managing an AWS Global Accelerator Cross Account Attac... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/globalaccelerator_cross_account_attachment.html.markdown) |
| `aws_globalaccelerator_custom_routing_accelerator` | ✅ | Creates a Global Accelerator custom routing accelerator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/globalaccelerator_custom_routing_accelerator.html.markdown) |
| `aws_globalaccelerator_custom_routing_endpoint_group` | ✅ | Provides a Global Accelerator custom routing endpoint group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/globalaccelerator_custom_routing_endpoint_group.html.markdown) |
| `aws_globalaccelerator_custom_routing_listener` | ✅ | Provides a Global Accelerator custom routing listener. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/globalaccelerator_custom_routing_listener.html.markdown) |
| `aws_globalaccelerator_endpoint_group` | ✅ | Provides a Global Accelerator endpoint group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/globalaccelerator_endpoint_group.html.markdown) |
| `aws_globalaccelerator_listener` | ✅ | Provides a Global Accelerator listener. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/globalaccelerator_listener.html.markdown) |

---

### Gamelift

**产品代码**: `gamelift`
**产品线分类**: 网络
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_gamelift_alias` | ✅ | Provides a GameLift Alias resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/gamelift_alias.html.markdown) |
| `aws_gamelift_build` | ✅ | Provides an GameLift Build resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/gamelift_build.html.markdown) |
| `aws_gamelift_fleet` | ✅ | Provides a GameLift Fleet resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/gamelift_fleet.html.markdown) |
| `aws_gamelift_game_server_group` | ✅ | Provides an GameLift Game Server Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/gamelift_game_server_group.html.markdown) |
| `aws_gamelift_game_session_queue` | ✅ | Provides an GameLift Game Session Queue resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/gamelift_game_session_queue.html.markdown) |
| `aws_gamelift_script` | ✅ | Provides an GameLift Script resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/gamelift_script.html.markdown) |

---

### Cloud Map

**产品代码**: `cloud_map`
**产品线分类**: 网络
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_service_discovery_http_namespace` | ✅ | ```terraform | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/service_discovery_http_namespace.html.markdown) |
| `aws_service_discovery_instance` | ✅ | Provides a Service Discovery Instance resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/service_discovery_instance.html.markdown) |
| `aws_service_discovery_private_dns_namespace` | ✅ | Provides a Service Discovery Private DNS Namespace resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/service_discovery_private_dns_namespace.html.markdown) |
| `aws_service_discovery_public_dns_namespace` | ✅ | Provides a Service Discovery Public DNS Namespace resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/service_discovery_public_dns_namespace.html.markdown) |
| `aws_service_discovery_service` | ✅ | Provides a Service Discovery Service resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/service_discovery_service.html.markdown) |

---

### License Manager

**产品代码**: `license_manager`
**产品线分类**: 网络
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_licensemanager_association` | ✅ | Provides a License Manager association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/licensemanager_association.html.markdown) |
| `aws_licensemanager_grant` | ✅ | Provides a License Manager grant. This allows for sharing licenses with other... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/licensemanager_grant.html.markdown) |
| `aws_licensemanager_grant_accepter` | ✅ | Accepts a License Manager grant. This allows for sharing licenses with other ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/licensemanager_grant_accepter.html.markdown) |
| `aws_licensemanager_license_configuration` | ✅ | Provides a License Manager license configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/licensemanager_license_configuration.html.markdown) |

---

### Route 53 Recovery Control Config

**产品代码**: `route_53_recovery_control_config`
**产品线分类**: 网络
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_route53recoverycontrolconfig_cluster` | ✅ | Provides an AWS Route 53 Recovery Control Config Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoverycontrolconfig_cluster.html.markdown) |
| `aws_route53recoverycontrolconfig_control_panel` | ✅ | Provides an AWS Route 53 Recovery Control Config Control Panel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoverycontrolconfig_control_panel.html.markdown) |
| `aws_route53recoverycontrolconfig_routing_control` | ✅ | Provides an AWS Route 53 Recovery Control Config Routing Control. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoverycontrolconfig_routing_control.html.markdown) |
| `aws_route53recoverycontrolconfig_safety_rule` | ✅ | Provides an AWS Route 53 Recovery Control Config Safety Rule | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoverycontrolconfig_safety_rule.html.markdown) |

---

### Route 53 Recovery Readiness

**产品代码**: `route_53_recovery_readiness`
**产品线分类**: 网络
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_route53recoveryreadiness_cell` | ✅ | Provides an AWS Route 53 Recovery Readiness Cell. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoveryreadiness_cell.html.markdown) |
| `aws_route53recoveryreadiness_readiness_check` | ✅ | Provides an AWS Route 53 Recovery Readiness Readiness Check. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoveryreadiness_readiness_check.html.markdown) |
| `aws_route53recoveryreadiness_recovery_group` | ✅ | Provides an AWS Route 53 Recovery Readiness Recovery Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoveryreadiness_recovery_group.html.markdown) |
| `aws_route53recoveryreadiness_resource_set` | ✅ | Provides an AWS Route 53 Recovery Readiness Resource Set. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53recoveryreadiness_resource_set.html.markdown) |

---

### Route 53 Domains

**产品代码**: `route_53_domains`
**产品线分类**: 网络
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_route53domains_delegation_signer_record` | ✅ | Provides a resource to manage a [delegation signer record](https://docs.aws.a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53domains_delegation_signer_record.html.markdown) |
| `aws_route53domains_domain` | ✅ | Provides a resource to manage a domain. This resource registers, renews and d... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53domains_domain.html.markdown) |
| `aws_route53domains_registered_domain` | ✅ | Provides a resource to manage a domain that has been [registered](https://doc... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53domains_registered_domain.html.markdown) |

---

### Route 53 Profiles

**产品代码**: `route_53_profiles`
**产品线分类**: 网络
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_route53profiles_association` | ✅ | Terraform resource for managing an AWS Route 53 Profiles Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53profiles_association.html.markdown) |
| `aws_route53profiles_profile` | ✅ | Terraform resource for managing an AWS Route 53 Profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53profiles_profile.html.markdown) |
| `aws_route53profiles_resource_association` | ✅ | Terraform resource for managing an AWS Route 53 Profiles Resource Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/route53profiles_resource_association.html.markdown) |

---

### Cloudwatch Networkflow Monitor

**产品代码**: `cloudwatch_networkflow_monitor`
**产品线分类**: 网络
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_networkflowmonitor_monitor` | ✅ | Manages a Network Flow Monitor Monitor. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkflowmonitor_monitor.html.markdown) |
| `aws_networkflowmonitor_scope` | ✅ | Manages a Network Flow Monitor Scope. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkflowmonitor_scope.html.markdown) |

---

### Cloudwatch Network Monitor

**产品代码**: `cloudwatch_network_monitor`
**产品线分类**: 网络
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_networkmonitor_monitor` | ✅ | Terraform resource for managing an AWS Network Monitor Monitor. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmonitor_monitor.html.markdown) |
| `aws_networkmonitor_probe` | ✅ | Terraform resource for managing an AWS Network Monitor Probe. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/networkmonitor_probe.html.markdown) |

---

## 企业IT治理 (41 个产品)

### Workspaces Web

**产品代码**: `workspaces_web`
**产品线分类**: 企业IT治理
**资源数**: 18

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_workspacesweb_browser_settings` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Browser Settings resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_browser_settings.html.markdown) |
| `aws_workspacesweb_browser_settings_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Browser Settings Associ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_browser_settings_association.html.markdown) |
| `aws_workspacesweb_data_protection_settings` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Data Protection Setting... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_data_protection_settings.html.markdown) |
| `aws_workspacesweb_data_protection_settings_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Data Protection Setting... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_data_protection_settings_association.html.markdown) |
| `aws_workspacesweb_identity_provider` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Identity Provider. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_identity_provider.html.markdown) |
| `aws_workspacesweb_ip_access_settings` | ✅ | Terraform resource for managing an AWS WorkSpaces Web IP Access Settings reso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_ip_access_settings.html.markdown) |
| `aws_workspacesweb_ip_access_settings_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web IP Access Settings Asso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_ip_access_settings_association.html.markdown) |
| `aws_workspacesweb_network_settings` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Network Settings resour... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_network_settings.html.markdown) |
| `aws_workspacesweb_network_settings_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Network Settings Associ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_network_settings_association.html.markdown) |
| `aws_workspacesweb_portal` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Portal. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_portal.html.markdown) |
| `aws_workspacesweb_session_logger` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Session Logger. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_session_logger.html.markdown) |
| `aws_workspacesweb_session_logger_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Session Logger Associat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_session_logger_association.html.markdown) |
| `aws_workspacesweb_trust_store` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Trust Store. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_trust_store.html.markdown) |
| `aws_workspacesweb_trust_store_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web Trust Store Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_trust_store_association.html.markdown) |
| `aws_workspacesweb_user_access_logging_settings` | ✅ | Terraform resource for managing an AWS WorkSpaces Web User Access Logging Set... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_user_access_logging_settings.html.markdown) |
| `aws_workspacesweb_user_access_logging_settings_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web User Access Logging Set... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_user_access_logging_settings_association.html.markdown) |
| `aws_workspacesweb_user_settings` | ✅ | Terraform resource for managing an AWS WorkSpaces Web User Settings resource.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_user_settings.html.markdown) |
| `aws_workspacesweb_user_settings_association` | ✅ | Terraform resource for managing an AWS WorkSpaces Web User Settings Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspacesweb_user_settings_association.html.markdown) |

---

### Cloudwatch Logs

**产品代码**: `cloudwatch_logs`
**产品线分类**: 企业IT治理
**资源数**: 17

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudwatch_log_account_policy` | ✅ | Provides a CloudWatch Log Account Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_account_policy.html.markdown) |
| `aws_cloudwatch_log_anomaly_detector` | ✅ | Terraform resource for managing an AWS CloudWatch Logs Log Anomaly Detector. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_anomaly_detector.html.markdown) |
| `aws_cloudwatch_log_data_protection_policy` | ✅ | Provides a CloudWatch Log Data Protection Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_data_protection_policy.html.markdown) |
| `aws_cloudwatch_log_delivery` | ✅ | Terraform resource for managing an AWS CloudWatch Logs Delivery. A delivery i... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_delivery.html.markdown) |
| `aws_cloudwatch_log_delivery_destination` | ✅ | Terraform resource for managing an AWS CloudWatch Logs Delivery Destination. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_delivery_destination.html.markdown) |
| `aws_cloudwatch_log_delivery_destination_policy` | ✅ | Terraform resource for managing an AWS CloudWatch Logs Delivery Destination P... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_delivery_destination_policy.html.markdown) |
| `aws_cloudwatch_log_delivery_source` | ✅ | Terraform resource for managing an AWS CloudWatch Logs Delivery Source. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_delivery_source.html.markdown) |
| `aws_cloudwatch_log_destination` | ✅ | Provides a CloudWatch Logs destination resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_destination.html.markdown) |
| `aws_cloudwatch_log_destination_policy` | ✅ | Provides a CloudWatch Logs destination policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_destination_policy.html.markdown) |
| `aws_cloudwatch_log_group` | ✅ | Provides a CloudWatch Log Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_group.html.markdown) |
| `aws_cloudwatch_log_index_policy` | ✅ | Terraform resource for managing an AWS CloudWatch Logs Index Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_index_policy.html.markdown) |
| `aws_cloudwatch_log_metric_filter` | ✅ | Provides a CloudWatch Log Metric Filter resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_metric_filter.html.markdown) |
| `aws_cloudwatch_log_resource_policy` | ✅ | Provides a resource to manage a CloudWatch log resource policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_resource_policy.html.markdown) |
| `aws_cloudwatch_log_stream` | ✅ | Provides a CloudWatch Log Stream resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_stream.html.markdown) |
| `aws_cloudwatch_log_subscription_filter` | ✅ | Provides a CloudWatch Logs subscription filter resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_subscription_filter.html.markdown) |
| `aws_cloudwatch_log_transformer` | ✅ | Terraform resource for managing an AWS CloudWatch Logs Transformer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_log_transformer.html.markdown) |
| `aws_cloudwatch_query_definition` | ✅ | Provides a CloudWatch Logs query definition resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_query_definition.html.markdown) |

---

### Config

**产品代码**: `config`
**产品线分类**: 企业IT治理
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_config_aggregate_authorization` | ✅ | Manages an AWS Config Aggregate Authorization | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_aggregate_authorization.html.markdown) |
| `aws_config_config_rule` | ✅ | Provides an AWS Config Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_config_rule.html.markdown) |
| `aws_config_configuration_aggregator` | ✅ | Manages an AWS Config Configuration Aggregator | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_configuration_aggregator.html.markdown) |
| `aws_config_configuration_recorder` | ✅ | Provides an AWS Config Configuration Recorder. Please note that this resource... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_configuration_recorder.html.markdown) |
| `aws_config_configuration_recorder_status` | ✅ | Manages status (recording / stopped) of an AWS Config Configuration Recorder. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_configuration_recorder_status.html.markdown) |
| `aws_config_conformance_pack` | ✅ | Manages a Config Conformance Pack. More information about this collection of ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_conformance_pack.html.markdown) |
| `aws_config_delivery_channel` | ✅ | Provides an AWS Config Delivery Channel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_delivery_channel.html.markdown) |
| `aws_config_organization_conformance_pack` | ✅ | Manages a Config Organization Conformance Pack. More information can be found... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_organization_conformance_pack.html.markdown) |
| `aws_config_organization_custom_policy_rule` | ✅ | Manages a Config Organization Custom Policy Rule. More information about thes... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_organization_custom_policy_rule.html.markdown) |
| `aws_config_organization_custom_rule` | ✅ | Manages a Config Organization Custom Rule. More information about these rules... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_organization_custom_rule.html.markdown) |
| `aws_config_organization_managed_rule` | ✅ | Manages a Config Organization Managed Rule. More information about these rule... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_organization_managed_rule.html.markdown) |
| `aws_config_remediation_configuration` | ✅ | Provides an AWS Config Remediation Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_remediation_configuration.html.markdown) |
| `aws_config_retention_configuration` | ✅ | Provides a resource to manage the AWS Config retention configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/config_retention_configuration.html.markdown) |

---

### Service Catalog

**产品代码**: `service_catalog`
**产品线分类**: 企业IT治理
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_servicecatalog_budget_resource_association` | ✅ | Manages a Service Catalog Budget Resource Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_budget_resource_association.html.markdown) |
| `aws_servicecatalog_constraint` | ✅ | Manages a Service Catalog Constraint. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_constraint.html.markdown) |
| `aws_servicecatalog_organizations_access` | ✅ | Manages Service Catalog AWS Organizations Access, a portfolio sharing feature... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_organizations_access.html.markdown) |
| `aws_servicecatalog_portfolio` | ✅ | Provides a resource to create a Service Catalog Portfolio. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_portfolio.html.markdown) |
| `aws_servicecatalog_portfolio_share` | ✅ | Manages a Service Catalog Portfolio Share. Shares the specified portfolio wit... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_portfolio_share.html.markdown) |
| `aws_servicecatalog_principal_portfolio_association` | ✅ | Manages a Service Catalog Principal Portfolio Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_principal_portfolio_association.html.markdown) |
| `aws_servicecatalog_product` | ✅ | Manages a Service Catalog Product. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_product.html.markdown) |
| `aws_servicecatalog_product_portfolio_association` | ✅ | Manages a Service Catalog Product Portfolio Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_product_portfolio_association.html.markdown) |
| `aws_servicecatalog_provisioned_product` | ✅ | This resource provisions and manages a Service Catalog provisioned product. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_provisioned_product.html.markdown) |
| `aws_servicecatalog_provisioning_artifact` | ✅ | Manages a Service Catalog Provisioning Artifact for a specified product. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_provisioning_artifact.html.markdown) |
| `aws_servicecatalog_service_action` | ✅ | Manages a Service Catalog self-service action. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_service_action.html.markdown) |
| `aws_servicecatalog_tag_option` | ✅ | Manages a Service Catalog Tag Option. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_tag_option.html.markdown) |
| `aws_servicecatalog_tag_option_resource_association` | ✅ | Manages a Service Catalog Tag Option Resource Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalog_tag_option_resource_association.html.markdown) |

---

### Ssm

**产品代码**: `ssm`
**产品线分类**: 企业IT治理
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ssm_activation` | ✅ | Registers an on-premises server or virtual machine with Amazon EC2 so that it... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_activation.html.markdown) |
| `aws_ssm_association` | ✅ | Associates an SSM Document to an instance or EC2 tag. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_association.html.markdown) |
| `aws_ssm_default_patch_baseline` | ✅ | Terraform resource for registering an AWS Systems Manager Default Patch Basel... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_default_patch_baseline.html.markdown) |
| `aws_ssm_document` | ✅ | Provides an SSM Document resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_document.html.markdown) |
| `aws_ssm_maintenance_window` | ✅ | Provides an SSM Maintenance Window resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_maintenance_window.html.markdown) |
| `aws_ssm_maintenance_window_target` | ✅ | Provides an SSM Maintenance Window Target resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_maintenance_window_target.html.markdown) |
| `aws_ssm_maintenance_window_task` | ✅ | Provides an SSM Maintenance Window Task resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_maintenance_window_task.html.markdown) |
| `aws_ssm_parameter` | ✅ | Provides an SSM Parameter resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_parameter.html.markdown) |
| `aws_ssm_patch_baseline` | ✅ | Provides an SSM Patch Baseline resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_patch_baseline.html.markdown) |
| `aws_ssm_patch_group` | ✅ | Provides an SSM Patch Group resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_patch_group.html.markdown) |
| `aws_ssm_resource_data_sync` | ✅ | Provides a SSM resource data sync. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_resource_data_sync.html.markdown) |
| `aws_ssm_service_setting` | ✅ | This setting defines how a user interacts with or uses a service or a feature... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssm_service_setting.html.markdown) |

---

### Audit Manager

**产品代码**: `audit_manager`
**产品线分类**: 企业IT治理
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_auditmanager_account_registration` | ✅ | Terraform resource for managing AWS Audit Manager Account Registration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_account_registration.html.markdown) |
| `aws_auditmanager_assessment` | ✅ | Terraform resource for managing an AWS Audit Manager Assessment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_assessment.html.markdown) |
| `aws_auditmanager_assessment_delegation` | ✅ | Terraform resource for managing an AWS Audit Manager Assessment Delegation. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_assessment_delegation.html.markdown) |
| `aws_auditmanager_assessment_report` | ✅ | Terraform resource for managing an AWS Audit Manager Assessment Report. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_assessment_report.html.markdown) |
| `aws_auditmanager_control` | ✅ | Terraform resource for managing an AWS Audit Manager Control. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_control.html.markdown) |
| `aws_auditmanager_framework` | ✅ | Terraform resource for managing an AWS Audit Manager Framework. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_framework.html.markdown) |
| `aws_auditmanager_framework_share` | ✅ | Terraform resource for managing an AWS Audit Manager Framework Share. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_framework_share.html.markdown) |
| `aws_auditmanager_organization_admin_account_registration` | ✅ | Terraform resource for managing AWS Audit Manager Organization Admin Account ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/auditmanager_organization_admin_account_registration.html.markdown) |

---

### User Notifications

**产品代码**: `user_notifications`
**产品线分类**: 企业IT治理
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_notifications_channel_association` | ✅ | Terraform resource for managing an AWS User Notifications Channel Association... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_channel_association.html.markdown) |
| `aws_notifications_event_rule` | ✅ | Terraform resource for managing an AWS User Notifications Event Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_event_rule.html.markdown) |
| `aws_notifications_managed_notification_account_contact_association` | ✅ | Terraform resource for managing an AWS User Notifications Managed Notificatio... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_managed_notification_account_contact_association.html.markdown) |
| `aws_notifications_managed_notification_additional_channel_association` | ✅ | Terraform resource for managing an AWS User Notifications Managed Notificatio... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_managed_notification_additional_channel_association.html.markdown) |
| `aws_notifications_notification_configuration` | ✅ | Terraform resource for managing an AWS User Notifications Notification Config... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_notification_configuration.html.markdown) |
| `aws_notifications_notification_hub` | ✅ | Terraform resource for managing an AWS User Notifications Notification Hub. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_notification_hub.html.markdown) |
| `aws_notifications_organizational_unit_association` | ✅ | Terraform resource for managing an AWS User Notifications Organizational Unit... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_organizational_unit_association.html.markdown) |
| `aws_notifications_organizations_access` | ✅ | Terraform resource for managing AWS User Notifications Organizations Access. ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notifications_organizations_access.html.markdown) |

---

### Organizations

**产品代码**: `organizations`
**产品线分类**: 企业IT治理
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_organizations_account` | ✅ | Provides a resource to create a member account in the current organization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_account.html.markdown) |
| `aws_organizations_delegated_administrator` | ✅ | Provides a resource to manage an [AWS Organizations Delegated Administrator](... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_delegated_administrator.html.markdown) |
| `aws_organizations_organization` | ✅ | Provides a resource to create an organization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_organization.html.markdown) |
| `aws_organizations_organizational_unit` | ✅ | Provides a resource to create an organizational unit. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_organizational_unit.html.markdown) |
| `aws_organizations_policy` | ✅ | Provides a resource to manage an [AWS Organizations policy](https://docs.aws.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_policy.html.markdown) |
| `aws_organizations_policy_attachment` | ✅ | Provides a resource to attach an AWS Organizations policy to an organization ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_policy_attachment.html.markdown) |
| `aws_organizations_resource_policy` | ✅ | Provides a resource to manage a resource-based delegation policy that can be ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_resource_policy.html.markdown) |
| `aws_organizations_tag` | ✅ | Manages an individual Organizations resource tag. This resource should only b... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/organizations_tag.html.markdown) |

---

### Managed Grafana

**产品代码**: `managed_grafana`
**产品线分类**: 企业IT治理
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_grafana_license_association` | ✅ | Provides an Amazon Managed Grafana workspace license association resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/grafana_license_association.html.markdown) |
| `aws_grafana_role_association` | ✅ | Provides an Amazon Managed Grafana workspace role association resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/grafana_role_association.html.markdown) |
| `aws_grafana_workspace` | ✅ | Provides an Amazon Managed Grafana workspace resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/grafana_workspace.html.markdown) |
| `aws_grafana_workspace_api_key` | ✅ | Provides an Amazon Managed Grafana workspace API Key resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/grafana_workspace_api_key.html.markdown) |
| `aws_grafana_workspace_saml_configuration` | ✅ | Provides an Amazon Managed Grafana workspace SAML configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/grafana_workspace_saml_configuration.html.markdown) |
| `aws_grafana_workspace_service_account` | ✅ | will delete the current and create a new one. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/grafana_workspace_service_account.html.markdown) |
| `aws_grafana_workspace_service_account_token` | ✅ | will delete the current and create a new one. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/grafana_workspace_service_account_token.html.markdown) |

---

### Cloudwatch

**产品代码**: `cloudwatch`
**产品线分类**: 企业IT治理
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudwatch_composite_alarm` | ✅ | Provides a CloudWatch Composite Alarm resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_composite_alarm.html.markdown) |
| `aws_cloudwatch_contributor_insight_rule` | ✅ | Terraform resource for managing an AWS CloudWatch Contributor Insight Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_contributor_insight_rule.html.markdown) |
| `aws_cloudwatch_contributor_managed_insight_rule` | ✅ | Terraform resource for managing an AWS CloudWatch Contributor Managed Insight... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_contributor_managed_insight_rule.html.markdown) |
| `aws_cloudwatch_dashboard` | ✅ | Provides a CloudWatch Dashboard resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_dashboard.html.markdown) |
| `aws_cloudwatch_metric_alarm` | ✅ | Provides a CloudWatch Metric Alarm resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_metric_alarm.html.markdown) |
| `aws_cloudwatch_metric_stream` | ✅ | Provides a CloudWatch Metric Stream resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_metric_stream.html.markdown) |

---

### Location

**产品代码**: `location`
**产品线分类**: 企业IT治理
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_location_geofence_collection` | ✅ | Terraform resource for managing an AWS Location Geofence Collection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/location_geofence_collection.html.markdown) |
| `aws_location_map` | ✅ | Provides a Location Service Map. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/location_map.html.markdown) |
| `aws_location_place_index` | ✅ | Provides a Location Service Place Index. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/location_place_index.html.markdown) |
| `aws_location_route_calculator` | ✅ | Provides a Location Service Route Calculator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/location_route_calculator.html.markdown) |
| `aws_location_tracker` | ✅ | Provides a Location Service Tracker. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/location_tracker.html.markdown) |
| `aws_location_tracker_association` | ✅ | Terraform resource for managing an AWS Location Tracker Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/location_tracker_association.html.markdown) |

---

### Verified Access

**产品代码**: `verified_access`
**产品线分类**: 企业IT治理
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_verifiedaccess_endpoint` | ✅ | Terraform resource for managing an AWS EC2 (Elastic Compute Cloud) Verified A... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedaccess_endpoint.html.markdown) |
| `aws_verifiedaccess_group` | ✅ | Terraform resource for managing a Verified Access Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedaccess_group.html.markdown) |
| `aws_verifiedaccess_instance` | ✅ | Terraform resource for managing a Verified Access Instance. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedaccess_instance.html.markdown) |
| `aws_verifiedaccess_instance_logging_configuration` | ✅ | Terraform resource for managing a Verified Access Logging Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedaccess_instance_logging_configuration.html.markdown) |
| `aws_verifiedaccess_instance_trust_provider_attachment` | ✅ | Terraform resource for managing a Verified Access Instance Trust Provider Att... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedaccess_instance_trust_provider_attachment.html.markdown) |
| `aws_verifiedaccess_trust_provider` | ✅ | Terraform resource for managing a Verified Access Trust Provider. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedaccess_trust_provider.html.markdown) |

---

### Cloudformation

**产品代码**: `cloudformation`
**产品线分类**: 企业IT治理
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudformation_stack` | ✅ | Provides a CloudFormation Stack resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudformation_stack.html.markdown) |
| `aws_cloudformation_stack_instances` | ✅ | Manages CloudFormation stack instances for the specified accounts, within the... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudformation_stack_instances.html.markdown) |
| `aws_cloudformation_stack_set` | ✅ | Manages a CloudFormation StackSet. StackSets allow CloudFormation templates t... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudformation_stack_set.html.markdown) |
| `aws_cloudformation_stack_set_instance` | ✅ | Manages a CloudFormation StackSet Instance. Instances are managed in the acco... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudformation_stack_set_instance.html.markdown) |
| `aws_cloudformation_type` | ✅ | Manages a version of a CloudFormation Type. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudformation_type.html.markdown) |

---

### Cloudwatch Evidently

**产品代码**: `cloudwatch_evidently`
**产品线分类**: 企业IT治理
**资源数**: 4 | **已弃用**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_evidently_feature` | ⚠️ 弃用 | Provides a CloudWatch Evidently Feature resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/evidently_feature.html.markdown) |
| `aws_evidently_launch` | ⚠️ 弃用 | Provides a CloudWatch Evidently Launch resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/evidently_launch.html.markdown) |
| `aws_evidently_project` | ⚠️ 弃用 | Provides a CloudWatch Evidently Project resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/evidently_project.html.markdown) |
| `aws_evidently_segment` | ⚠️ 弃用 | Provides a CloudWatch Evidently Segment resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/evidently_segment.html.markdown) |

---

### Ssm Contacts

**产品代码**: `ssm_contacts`
**产品线分类**: 企业IT治理
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ssmcontacts_contact` | ✅ | Terraform resource for managing an AWS SSM Contact. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssmcontacts_contact.html.markdown) |
| `aws_ssmcontacts_contact_channel` | ✅ | Terraform resource for managing an AWS SSM Contacts Contact Channel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssmcontacts_contact_channel.html.markdown) |
| `aws_ssmcontacts_plan` | ✅ | Terraform resource for managing an AWS SSM Contact Plan. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssmcontacts_plan.html.markdown) |
| `aws_ssmcontacts_rotation` | ✅ | Provides a Terraform resource for managing a Contacts Rotation in AWS Systems... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssmcontacts_rotation.html.markdown) |

---

### Workspaces

**产品代码**: `workspaces`
**产品线分类**: 企业IT治理
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_workspaces_connection_alias` | ✅ | Terraform resource for managing an AWS WorkSpaces Connection Alias. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspaces_connection_alias.html.markdown) |
| `aws_workspaces_directory` | ✅ | Provides a WorkSpaces directory in AWS WorkSpaces Service. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspaces_directory.html.markdown) |
| `aws_workspaces_ip_group` | ✅ | Provides an IP access control group in AWS WorkSpaces Service | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspaces_ip_group.html.markdown) |
| `aws_workspaces_workspace` | ✅ | Provides a workspace in [AWS Workspaces](https://docs.aws.amazon.com/workspac... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workspaces_workspace.html.markdown) |

---

### Account Management

**产品代码**: `account_management`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_account_alternate_contact` | ✅ | Manages the specified alternate contact attached to an AWS Account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/account_alternate_contact.html.markdown) |
| `aws_account_primary_contact` | ✅ | Manages the specified primary contact information associated with an AWS Acco... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/account_primary_contact.html.markdown) |
| `aws_account_region` | ✅ | Enable (Opt-In) or Disable (Opt-Out) a particular Region for an AWS account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/account_region.html.markdown) |

---

### Cloudtrail

**产品代码**: `cloudtrail`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudtrail` | ✅ | Provides a CloudTrail resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudtrail.html.markdown) |
| `aws_cloudtrail_event_data_store` | ✅ | Provides a CloudTrail Event Data Store. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudtrail_event_data_store.html.markdown) |
| `aws_cloudtrail_organization_delegated_admin_account` | ✅ | Provides a resource to manage an AWS CloudTrail Delegated Administrator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudtrail_organization_delegated_admin_account.html.markdown) |

---

### Codecatalyst

**产品代码**: `codecatalyst`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codecatalyst_dev_environment` | ✅ | Terraform resource for managing an AWS CodeCatalyst Dev Environment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codecatalyst_dev_environment.html.markdown) |
| `aws_codecatalyst_project` | ✅ | Terraform resource for managing an AWS CodeCatalyst Project. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codecatalyst_project.html.markdown) |
| `aws_codecatalyst_source_repository` | ✅ | Terraform resource for managing an AWS CodeCatalyst Source Repository. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codecatalyst_source_repository.html.markdown) |

---

### Control Tower

**产品代码**: `control_tower`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_controltower_baseline` | ✅ | Terraform resource for managing an AWS Control Tower Baseline. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/controltower_baseline.html.markdown) |
| `aws_controltower_control` | ✅ | Allows the application of pre-defined controls to organizational units. For m... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/controltower_control.html.markdown) |
| `aws_controltower_landing_zone` | ✅ | Creates a new landing zone using Control Tower. For more information on usage... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/controltower_landing_zone.html.markdown) |

---

### Cloudwatch Observability Access Manager

**产品代码**: `cloudwatch_observability_access_manager`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_oam_link` | ✅ | Terraform resource for managing an AWS CloudWatch Observability Access Manage... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/oam_link.html.markdown) |
| `aws_oam_sink` | ✅ | Terraform resource for managing an AWS CloudWatch Observability Access Manage... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/oam_sink.html.markdown) |
| `aws_oam_sink_policy` | ✅ | Terraform resource for managing an AWS CloudWatch Observability Access Manage... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/oam_sink_policy.html.markdown) |

---

### Service Catalog Appregistry

**产品代码**: `service_catalog_appregistry`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_servicecatalogappregistry_application` | ✅ | Terraform resource for managing an AWS Service Catalog AppRegistry Application. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalogappregistry_application.html.markdown) |
| `aws_servicecatalogappregistry_attribute_group` | ✅ | Terraform resource for managing an AWS Service Catalog AppRegistry Attribute ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalogappregistry_attribute_group.html.markdown) |
| `aws_servicecatalogappregistry_attribute_group_association` | ✅ | Terraform resource for managing an AWS Service Catalog AppRegistry Attribute ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicecatalogappregistry_attribute_group_association.html.markdown) |

---

### Service Quotas

**产品代码**: `service_quotas`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_servicequotas_service_quota` | ✅ | Manages an individual Service Quota. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicequotas_service_quota.html.markdown) |
| `aws_servicequotas_template` | ✅ | Terraform resource for managing an AWS Service Quotas Template. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicequotas_template.html.markdown) |
| `aws_servicequotas_template_association` | ✅ | Terraform resource for managing an AWS Service Quotas Template Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/servicequotas_template_association.html.markdown) |

---

### Cloudwatch Synthetics

**产品代码**: `cloudwatch_synthetics`
**产品线分类**: 企业IT治理
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_synthetics_canary` | ✅ | Provides a Synthetics Canary resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/synthetics_canary.html.markdown) |
| `aws_synthetics_group` | ✅ | Provides a Synthetics Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/synthetics_group.html.markdown) |
| `aws_synthetics_group_association` | ✅ | Provides a Synthetics Group Association resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/synthetics_group_association.html.markdown) |

---

### Web Services Budgets

**产品代码**: `web_services_budgets`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_budgets_budget` | ✅ | Provides a budgets budget resource. Budgets use the cost visualization provid... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/budgets_budget.html.markdown) |
| `aws_budgets_budget_action` | ✅ | Provides a budget action resource. Budget actions are cost savings controls t... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/budgets_budget_action.html.markdown) |

---

### Compute Optimizer

**产品代码**: `compute_optimizer`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_computeoptimizer_enrollment_status` | ✅ | Manages AWS Compute Optimizer enrollment status. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/computeoptimizer_enrollment_status.html.markdown) |
| `aws_computeoptimizer_recommendation_preferences` | ✅ | Manages AWS Compute Optimizer recommendation preferences. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/computeoptimizer_recommendation_preferences.html.markdown) |

---

### Keyspaces

**产品代码**: `keyspaces`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_keyspaces_keyspace` | ✅ | Provides a Keyspaces Keyspace. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/keyspaces_keyspace.html.markdown) |
| `aws_keyspaces_table` | ✅ | Provides a Keyspaces Table. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/keyspaces_table.html.markdown) |

---

### Cloudwatch Observability Admin

**产品代码**: `cloudwatch_observability_admin`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_observabilityadmin_centralization_rule_for_organization` | ✅ | Manages an AWS CloudWatch Observability Admin Centralization Rule For Organiz... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/observabilityadmin_centralization_rule_for_organization.html.markdown) |
| `aws_observabilityadmin_telemetry_pipeline` | ✅ | Manages an AWS CloudWatch Observability Admin Telemetry Pipeline. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/observabilityadmin_telemetry_pipeline.html.markdown) |

---

### Resource Explorer

**产品代码**: `resource_explorer`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_resourceexplorer2_index` | ✅ | Provides a resource to manage a Resource Explorer index in the current AWS Re... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/resourceexplorer2_index.html.markdown) |
| `aws_resourceexplorer2_view` | ✅ | Provides a resource to manage a Resource Explorer view. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/resourceexplorer2_view.html.markdown) |

---

### Resource Groups

**产品代码**: `resource_groups`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_resourcegroups_group` | ✅ | Provides a Resource Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/resourcegroups_group.html.markdown) |
| `aws_resourcegroups_resource` | ✅ | Terraform resource for managing an AWS Resource Groups Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/resourcegroups_resource.html.markdown) |

---

### Cloudwatch Rum

**产品代码**: `cloudwatch_rum`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_rum_app_monitor` | ✅ | Provides a CloudWatch RUM App Monitor resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rum_app_monitor.html.markdown) |
| `aws_rum_metrics_destination` | ✅ | Provides a CloudWatch RUM Metrics Destination resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rum_metrics_destination.html.markdown) |

---

### Ssm Incident Manager Incidents

**产品代码**: `ssm_incident_manager_incidents`
**产品线分类**: 企业IT治理
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ssmincidents_replication_set` | ✅ | Provides a resource for managing a replication set in AWS Systems Manager Inc... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssmincidents_replication_set.html.markdown) |
| `aws_ssmincidents_response_plan` | ✅ | Provides a Terraform resource to manage response plans in AWS Systems Manager... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssmincidents_response_plan.html.markdown) |

---

### Cloudwatch Application Insights

**产品代码**: `cloudwatch_application_insights`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_applicationinsights_application` | ✅ | Provides a ApplicationInsights Application resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/applicationinsights_application.html.markdown) |

---

### Billing

**产品代码**: `billing`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_billing_view` | ✅ | Manages an AWS Billing View. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/billing_view.html.markdown) |

---

### Codestar Notifications

**产品代码**: `codestar_notifications`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codestarnotifications_notification_rule` | ✅ | Provides a CodeStar Notifications Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codestarnotifications_notification_rule.html.markdown) |

---

### Dlm

**产品代码**: `dlm`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_dlm_lifecycle_policy` | ✅ | Provides a [Data Lifecycle Manager (DLM) lifecycle policy](https://docs.aws.a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dlm_lifecycle_policy.html.markdown) |

---

### Cloudwatch Internet Monitor

**产品代码**: `cloudwatch_internet_monitor`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_internetmonitor_monitor` | ✅ | Provides a Internet Monitor Monitor resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/internetmonitor_monitor.html.markdown) |

---

### User Notifications Contacts

**产品代码**: `user_notifications_contacts`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_notificationscontacts_email_contact` | ✅ | Terraform resource for managing AWS User Notifications Contacts Email Contact. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/notificationscontacts_email_contact.html.markdown) |

---

### Recycle Bin

**产品代码**: `recycle_bin`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_rbin_rule` | ✅ | Terraform resource for managing an AWS RBin Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rbin_rule.html.markdown) |

---

### Serverless Application Repository

**产品代码**: `serverless_application_repository`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_serverlessapplicationrepository_cloudformation_stack` | ✅ | Deploys an Application CloudFormation Stack from the Serverless Application R... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/serverlessapplicationrepository_cloudformation_stack.html.markdown) |

---

### Ssm Quick Setup

**产品代码**: `ssm_quick_setup`
**产品线分类**: 企业IT治理
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ssmquicksetup_configuration_manager` | ✅ | Terraform resource for managing an AWS SSM Quick Setup Configuration Manager. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssmquicksetup_configuration_manager.html.markdown) |

---

## 存储 (14 个产品)

### Simple Storage Service

**产品代码**: `s3`
**产品线分类**: 存储
**资源数**: 26

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_s3_bucket` | ✅ | Provides a S3 bucket resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket.html.markdown) |
| `aws_s3_bucket_abac` | ✅ | Manages ABAC (Attribute Based Access Control) for an AWS S3 (Simple Storage) ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_abac.html.markdown) |
| `aws_s3_bucket_accelerate_configuration` | ✅ | Provides an S3 bucket accelerate configuration resource. See the [Requirement... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_accelerate_configuration.html.markdown) |
| `aws_s3_bucket_acl` | ✅ | Provides an S3 bucket ACL resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_acl.html.markdown) |
| `aws_s3_bucket_analytics_configuration` | ✅ | Provides a S3 bucket [analytics configuration](https://docs.aws.amazon.com/Am... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_analytics_configuration.html.markdown) |
| `aws_s3_bucket_cors_configuration` | ✅ | Provides an S3 bucket CORS configuration resource. For more information about... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_cors_configuration.html.markdown) |
| `aws_s3_bucket_intelligent_tiering_configuration` | ✅ | Provides an [S3 Intelligent-Tiering](https://docs.aws.amazon.com/AmazonS3/lat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_intelligent_tiering_configuration.html.markdown) |
| `aws_s3_bucket_inventory` | ✅ | Provides a S3 bucket [inventory configuration](https://docs.aws.amazon.com/Am... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_inventory.html.markdown) |
| `aws_s3_bucket_lifecycle_configuration` | ✅ | Provides an independent configuration resource for S3 bucket [lifecycle confi... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_lifecycle_configuration.html.markdown) |
| `aws_s3_bucket_logging` | ✅ | Provides an S3 bucket (server access) logging resource. For more information,... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_logging.html.markdown) |
| `aws_s3_bucket_metadata_configuration` | ✅ | Manages Amazon S3 Metadata for a bucket. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_metadata_configuration.html.markdown) |
| `aws_s3_bucket_metric` | ✅ | Provides a S3 bucket [metrics configuration](http://docs.aws.amazon.com/Amazo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_metric.html.markdown) |
| `aws_s3_bucket_notification` | ✅ | Manages a S3 Bucket Notification Configuration. For additional information, s... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_notification.html.markdown) |
| `aws_s3_bucket_object` | ✅ | Provides an S3 object resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_object.html.markdown) |
| `aws_s3_bucket_object_lock_configuration` | ✅ | Provides an S3 bucket Object Lock configuration resource. For more informatio... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_object_lock_configuration.html.markdown) |
| `aws_s3_bucket_ownership_controls` | ✅ | Provides a resource to manage S3 Bucket Ownership Controls. For more informat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_ownership_controls.html.markdown) |
| `aws_s3_bucket_policy` | ✅ | Attaches a policy to an S3 bucket resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_policy.html.markdown) |
| `aws_s3_bucket_public_access_block` | ✅ | Manages S3 bucket-level Public Access Block configuration. For more informati... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_public_access_block.html.markdown) |
| `aws_s3_bucket_replication_configuration` | ✅ | Provides an independent configuration resource for S3 bucket [replication con... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_replication_configuration.html.markdown) |
| `aws_s3_bucket_request_payment_configuration` | ✅ | Provides an S3 bucket request payment configuration resource. For more inform... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_request_payment_configuration.html.markdown) |
| `aws_s3_bucket_server_side_encryption_configuration` | ✅ | Provides a S3 bucket server-side encryption configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_server_side_encryption_configuration.html.markdown) |
| `aws_s3_bucket_versioning` | ✅ | Provides a resource for controlling versioning on an S3 bucket. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_versioning.html.markdown) |
| `aws_s3_bucket_website_configuration` | ✅ | Provides an S3 bucket website configuration resource. For more information, s... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_bucket_website_configuration.html.markdown) |
| `aws_s3_directory_bucket` | ✅ | Provides an Amazon S3 Express directory bucket resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_directory_bucket.html.markdown) |
| `aws_s3_object` | ✅ | Provides an S3 object resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_object.html.markdown) |
| `aws_s3_object_copy` | ✅ | Provides a resource for copying an S3 object. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_object_copy.html.markdown) |

---

### S3 Control

**产品代码**: `s3_control`
**产品线分类**: 存储
**资源数**: 16

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_s3_access_point` | ✅ | Provides a resource to manage an S3 Access Point. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_access_point.html.markdown) |
| `aws_s3_account_public_access_block` | ✅ | Manages S3 account-level Public Access Block configuration. For more informat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3_account_public_access_block.html.markdown) |
| `aws_s3control_access_grant` | ✅ | Provides a resource to manage an S3 Access Grant. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_access_grant.html.markdown) |
| `aws_s3control_access_grants_instance` | ✅ | Provides a resource to manage an S3 Access Grants instance, which serves as a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_access_grants_instance.html.markdown) |
| `aws_s3control_access_grants_instance_resource_policy` | ✅ | Provides a resource to manage an S3 Access Grants instance resource policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_access_grants_instance_resource_policy.html.markdown) |
| `aws_s3control_access_grants_location` | ✅ | Provides a resource to manage an S3 Access Grants location. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_access_grants_location.html.markdown) |
| `aws_s3control_access_point_policy` | ✅ | Provides a resource to manage an S3 Access Point resource policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_access_point_policy.html.markdown) |
| `aws_s3control_bucket` | ✅ | Provides a resource to manage an S3 Control Bucket. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_bucket.html.markdown) |
| `aws_s3control_bucket_lifecycle_configuration` | ✅ | Provides a resource to manage an S3 Control Bucket Lifecycle Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_bucket_lifecycle_configuration.html.markdown) |
| `aws_s3control_bucket_policy` | ✅ | Provides a resource to manage an S3 Control Bucket Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_bucket_policy.html.markdown) |
| `aws_s3control_directory_bucket_access_point_scope` | ✅ | Provides a resource to manage the access point scope for a directory bucket. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_directory_bucket_access_point_scope.html.markdown) |
| `aws_s3control_multi_region_access_point` | ✅ | Provides a resource to manage an S3 Multi-Region Access Point associated with... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_multi_region_access_point.html.markdown) |
| `aws_s3control_multi_region_access_point_policy` | ✅ | Provides a resource to manage an S3 Multi-Region Access Point access control ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_multi_region_access_point_policy.html.markdown) |
| `aws_s3control_object_lambda_access_point` | ✅ | Provides a resource to manage an S3 Object Lambda Access Point. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_object_lambda_access_point.html.markdown) |
| `aws_s3control_object_lambda_access_point_policy` | ✅ | Provides a resource to manage an S3 Object Lambda Access Point resource policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_object_lambda_access_point_policy.html.markdown) |
| `aws_s3control_storage_lens_configuration` | ✅ | Provides a resource to manage an S3 Storage Lens configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3control_storage_lens_configuration.html.markdown) |

---

### Backup

**产品代码**: `backup`
**产品线分类**: 存储
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_backup_framework` | ✅ | Provides an AWS Backup Framework resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_framework.html.markdown) |
| `aws_backup_global_settings` | ✅ | Provides an AWS Backup Global Settings resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_global_settings.html.markdown) |
| `aws_backup_logically_air_gapped_vault` | ✅ | Terraform resource for managing an AWS Backup Logically Air Gapped Vault. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_logically_air_gapped_vault.html.markdown) |
| `aws_backup_plan` | ✅ | Provides an AWS Backup plan resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_plan.html.markdown) |
| `aws_backup_region_settings` | ✅ | Provides an AWS Backup Region Settings resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_region_settings.html.markdown) |
| `aws_backup_report_plan` | ✅ | Provides an AWS Backup Report Plan resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_report_plan.html.markdown) |
| `aws_backup_restore_testing_plan` | ✅ | Terraform resource for managing an AWS Backup Restore Testing Plan. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_restore_testing_plan.html.markdown) |
| `aws_backup_restore_testing_selection` | ✅ | Terraform resource for managing an AWS Backup Restore Testing Selection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_restore_testing_selection.html.markdown) |
| `aws_backup_selection` | ✅ | Manages selection conditions for AWS Backup plan resources. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_selection.html.markdown) |
| `aws_backup_vault` | ✅ | Provides an AWS Backup vault resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_vault.html.markdown) |
| `aws_backup_vault_lock_configuration` | ✅ | Provides an AWS Backup vault lock configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_vault_lock_configuration.html.markdown) |
| `aws_backup_vault_notifications` | ✅ | Provides an AWS Backup vault notifications resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_vault_notifications.html.markdown) |
| `aws_backup_vault_policy` | ✅ | Provides an AWS Backup vault policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/backup_vault_policy.html.markdown) |

---

### Fsx

**产品代码**: `fsx`
**产品线分类**: 存储
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_fsx_backup` | ✅ | Provides a FSx Backup resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_backup.html.markdown) |
| `aws_fsx_data_repository_association` | ✅ | Manages a FSx for Lustre Data Repository Association. See [Linking your file ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_data_repository_association.html.markdown) |
| `aws_fsx_file_cache` | ✅ | Terraform resource for managing an Amazon File Cache cache. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_file_cache.html.markdown) |
| `aws_fsx_lustre_file_system` | ✅ | Manages a FSx Lustre File System. See the [FSx Lustre Guide](https://docs.aws... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_lustre_file_system.html.markdown) |
| `aws_fsx_ontap_file_system` | ✅ | Manages an Amazon FSx for NetApp ONTAP file system. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_ontap_file_system.html.markdown) |
| `aws_fsx_ontap_storage_virtual_machine` | ✅ | Manages a FSx Storage Virtual Machine. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_ontap_storage_virtual_machine.html.markdown) |
| `aws_fsx_ontap_volume` | ✅ | Manages a FSx ONTAP Volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_ontap_volume.html.markdown) |
| `aws_fsx_openzfs_file_system` | ✅ | Manages an Amazon FSx for OpenZFS file system. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_openzfs_file_system.html.markdown) |
| `aws_fsx_openzfs_snapshot` | ✅ | Manages an Amazon FSx for OpenZFS volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_openzfs_snapshot.html.markdown) |
| `aws_fsx_openzfs_volume` | ✅ | Manages an Amazon FSx for OpenZFS volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_openzfs_volume.html.markdown) |
| `aws_fsx_s3_access_point_attachment` | ✅ | Manages an Amazon FSx S3 Access Point attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_s3_access_point_attachment.html.markdown) |
| `aws_fsx_windows_file_system` | ✅ | Manages a FSx Windows File System. See the [FSx Windows Guide](https://docs.a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fsx_windows_file_system.html.markdown) |

---

### Ebs

**产品代码**: `ebs`
**产品线分类**: 存储
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ebs_default_kms_key` | ✅ | Provides a resource to manage the default customer master key (CMK) that your... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_default_kms_key.html.markdown) |
| `aws_ebs_encryption_by_default` | ✅ | Provides a resource to manage whether default EBS encryption is enabled for y... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_encryption_by_default.html.markdown) |
| `aws_ebs_fast_snapshot_restore` | ✅ | Terraform resource for managing an EBS (Elastic Block Storage) Fast Snapshot ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_fast_snapshot_restore.html.markdown) |
| `aws_ebs_snapshot` | ✅ | Creates a Snapshot of an EBS Volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_snapshot.html.markdown) |
| `aws_ebs_snapshot_block_public_access` | ✅ | Provides a resource to manage the state of the "Block public access for snaps... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_snapshot_block_public_access.html.markdown) |
| `aws_ebs_snapshot_copy` | ✅ | Creates a Snapshot of a snapshot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_snapshot_copy.html.markdown) |
| `aws_ebs_snapshot_import` | ✅ | Imports a disk image from S3 as a Snapshot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_snapshot_import.html.markdown) |
| `aws_ebs_volume` | ✅ | Manages a single EBS volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ebs_volume.html.markdown) |
| `aws_snapshot_create_volume_permission` | ✅ | Adds permission to create volumes off of a given EBS Snapshot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/snapshot_create_volume_permission.html.markdown) |
| `aws_volume_attachment` | ✅ | Provides an AWS EBS Volume Attachment as a top level resource, to attach and | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/volume_attachment.html.markdown) |

---

### Storage Gateway

**产品代码**: `storage_gateway`
**产品线分类**: 存储
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_storagegateway_cache` | ✅ | Manages an AWS Storage Gateway cache. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_cache.html.markdown) |
| `aws_storagegateway_cached_iscsi_volume` | ✅ | Manages an AWS Storage Gateway cached iSCSI volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_cached_iscsi_volume.html.markdown) |
| `aws_storagegateway_file_system_association` | ✅ | Associate an Amazon FSx file system with the FSx File Gateway. After the asso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_file_system_association.html.markdown) |
| `aws_storagegateway_gateway` | ✅ | Manages an AWS Storage Gateway file, tape, or volume gateway in the provider ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_gateway.html.markdown) |
| `aws_storagegateway_nfs_file_share` | ✅ | Manages an AWS Storage Gateway NFS File Share. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_nfs_file_share.html.markdown) |
| `aws_storagegateway_smb_file_share` | ✅ | Manages an AWS Storage Gateway SMB File Share. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_smb_file_share.html.markdown) |
| `aws_storagegateway_stored_iscsi_volume` | ✅ | Manages an AWS Storage Gateway stored iSCSI volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_stored_iscsi_volume.html.markdown) |
| `aws_storagegateway_tape_pool` | ✅ | Manages an AWS Storage Gateway Tape Pool. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_tape_pool.html.markdown) |
| `aws_storagegateway_upload_buffer` | ✅ | Manages an AWS Storage Gateway upload buffer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_upload_buffer.html.markdown) |
| `aws_storagegateway_working_storage` | ✅ | Manages an AWS Storage Gateway working storage. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/storagegateway_working_storage.html.markdown) |

---

### S3 Tables

**产品代码**: `s3_tables`
**产品线分类**: 存储
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_s3tables_namespace` | ✅ | Terraform resource for managing an Amazon S3 Tables Namespace. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3tables_namespace.html.markdown) |
| `aws_s3tables_table` | ✅ | Terraform resource for managing an Amazon S3 Tables Table. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3tables_table.html.markdown) |
| `aws_s3tables_table_bucket` | ✅ | Terraform resource for managing an Amazon S3 Tables Table Bucket. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3tables_table_bucket.html.markdown) |
| `aws_s3tables_table_bucket_policy` | ✅ | Terraform resource for managing an Amazon S3 Tables Table Bucket Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3tables_table_bucket_policy.html.markdown) |
| `aws_s3tables_table_bucket_replication` | ✅ | Manages Amazon S3 Tables Table Bucket Replication configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3tables_table_bucket_replication.html.markdown) |
| `aws_s3tables_table_policy` | ✅ | Terraform resource for managing an Amazon S3 Tables Table Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3tables_table_policy.html.markdown) |
| `aws_s3tables_table_replication` | ✅ | Manages Amazon S3 Tables Table Replication configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3tables_table_replication.html.markdown) |

---

### Efs

**产品代码**: `efs`
**产品线分类**: 存储
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_efs_access_point` | ✅ | Provides an Elastic File System (EFS) access point. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/efs_access_point.html.markdown) |
| `aws_efs_backup_policy` | ✅ | Provides an Elastic File System (EFS) Backup Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/efs_backup_policy.html.markdown) |
| `aws_efs_file_system` | ✅ | Provides an Elastic File System (EFS) File System resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/efs_file_system.html.markdown) |
| `aws_efs_file_system_policy` | ✅ | Provides an Elastic File System (EFS) File System Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/efs_file_system_policy.html.markdown) |
| `aws_efs_mount_target` | ✅ | Provides an Elastic File System (EFS) mount target. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/efs_mount_target.html.markdown) |
| `aws_efs_replication_configuration` | ✅ | Creates a replica of an existing EFS file system in the same or another regio... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/efs_replication_configuration.html.markdown) |

---

### S3 Vectors

**产品代码**: `s3_vectors`
**产品线分类**: 存储
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_s3vectors_index` | ✅ | Terraform resource for managing an Amazon S3 Vectors Index. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3vectors_index.html.markdown) |
| `aws_s3vectors_vector_bucket` | ✅ | Terraform resource for managing an Amazon S3 Vectors Vector Bucket. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3vectors_vector_bucket.html.markdown) |
| `aws_s3vectors_vector_bucket_policy` | ✅ | Terraform resource for managing an Amazon S3 Vectors Vector Bucket policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3vectors_vector_bucket_policy.html.markdown) |

---

### Cost Optimization Hub

**产品代码**: `cost_optimization_hub`
**产品线分类**: 存储
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_costoptimizationhub_enrollment_status` | ✅ | Terraform resource for managing AWS Cost Optimization Hub Enrollment Status. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/costoptimizationhub_enrollment_status.html.markdown) |
| `aws_costoptimizationhub_preferences` | ✅ | Terraform resource for managing AWS Cost Optimization Hub Preferences. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/costoptimizationhub_preferences.html.markdown) |

---

### S3 Glacier

**产品代码**: `s3_glacier`
**产品线分类**: 存储
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_glacier_vault` | ✅ | Provides a Glacier Vault Resource. You can refer to the [Glacier Developer Gu... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glacier_vault.html.markdown) |
| `aws_glacier_vault_lock` | ✅ | Manages a Glacier Vault Lock. You can refer to the [Glacier Developer Guide](... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glacier_vault_lock.html.markdown) |

---

### Cost And Usage Report

**产品代码**: `cost_and_usage_report`
**产品线分类**: 存储
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cur_report_definition` | ✅ | Manages Cost and Usage Report Definitions. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cur_report_definition.html.markdown) |

---

### Drs

**产品代码**: `drs`
**产品线分类**: 存储
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_drs_replication_configuration_template` | ✅ | Provides an Elastic Disaster Recovery replication configuration template reso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/drs_replication_configuration_template.html.markdown) |

---

### S3 On Outposts

**产品代码**: `s3_on_outposts`
**产品线分类**: 存储
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_s3outposts_endpoint` | ✅ | Provides a resource to manage an S3 Outposts Endpoint. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/s3outposts_endpoint.html.markdown) |

---

## 数据库 (18 个产品)

### Relational Database Service

**产品代码**: `rds`
**产品线分类**: 数据库
**资源数**: 29

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_db_cluster_snapshot` | ✅ | Manages an RDS database cluster snapshot for Aurora clusters. For managing RD... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_cluster_snapshot.html.markdown) |
| `aws_db_event_subscription` | ✅ | Provides a DB event subscription resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_event_subscription.html.markdown) |
| `aws_db_instance` | ✅ | Provides an RDS instance resource.  A DB instance is an isolated database | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_instance.html.markdown) |
| `aws_db_instance_automated_backups_replication` | ✅ | Manage cross-region replication of automated backups to a different AWS Regio... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_instance_automated_backups_replication.html.markdown) |
| `aws_db_instance_role_association` | ✅ | Manages an RDS DB Instance association with an IAM Role. Example use cases: | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_instance_role_association.html.markdown) |
| `aws_db_option_group` | ✅ | Provides an RDS DB option group resource. Documentation of the available opti... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_option_group.html.markdown) |
| `aws_db_parameter_group` | ✅ | Provides an RDS DB parameter group resource. Documentation of the available p... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_parameter_group.html.markdown) |
| `aws_db_proxy` | ✅ | Provides an RDS DB proxy resource. For additional information, see the [RDS U... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_proxy.html.markdown) |
| `aws_db_proxy_default_target_group` | ✅ | Provides a resource to manage an RDS DB proxy default target group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_proxy_default_target_group.html.markdown) |
| `aws_db_proxy_endpoint` | ✅ | Provides an RDS DB proxy endpoint resource. For additional information, see t... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_proxy_endpoint.html.markdown) |
| `aws_db_proxy_target` | ✅ | Provides an RDS DB proxy target resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_proxy_target.html.markdown) |
| `aws_db_snapshot` | ✅ | Manages an RDS database instance snapshot. For managing RDS database cluster ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_snapshot.html.markdown) |
| `aws_db_snapshot_copy` | ✅ | Manages an RDS database instance snapshot copy. For managing RDS database clu... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_snapshot_copy.html.markdown) |
| `aws_db_subnet_group` | ✅ | Provides an RDS DB subnet group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/db_subnet_group.html.markdown) |
| `aws_rds_certificate` | ✅ | Provides a resource to override the system-default Secure Sockets Layer/Trans... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_certificate.html.markdown) |
| `aws_rds_cluster` | ✅ | Manages a [RDS Aurora Cluster][2] or a [RDS Multi-AZ DB Cluster](https://docs... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_cluster.html.markdown) |
| `aws_rds_cluster_activity_stream` | ✅ | Manages RDS Aurora Cluster Database Activity Streams. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_cluster_activity_stream.html.markdown) |
| `aws_rds_cluster_endpoint` | ✅ | Manages an RDS Aurora Cluster Custom Endpoint. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_cluster_endpoint.html.markdown) |
| `aws_rds_cluster_instance` | ✅ | Provides an RDS Cluster Instance Resource. A Cluster Instance Resource defines | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_cluster_instance.html.markdown) |
| `aws_rds_cluster_parameter_group` | ✅ | Provides an RDS DB cluster parameter group resource. Documentation of the ava... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_cluster_parameter_group.html.markdown) |
| `aws_rds_cluster_role_association` | ✅ | Manages a RDS DB Cluster association with an IAM Role. Example use cases: | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_cluster_role_association.html.markdown) |
| `aws_rds_cluster_snapshot_copy` | ✅ | Manages an RDS database cluster snapshot copy. For managing RDS database inst... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_cluster_snapshot_copy.html.markdown) |
| `aws_rds_custom_db_engine_version` | ✅ | Provides an custom engine version (CEV) resource for Amazon RDS Custom. For a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_custom_db_engine_version.html.markdown) |
| `aws_rds_export_task` | ✅ | Terraform resource for managing an AWS RDS (Relational Database) Export Task. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_export_task.html.markdown) |
| `aws_rds_global_cluster` | ✅ | Manages an RDS Global Cluster, which is an Aurora global database spread acro... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_global_cluster.html.markdown) |
| `aws_rds_instance_state` | ✅ | Terraform resource for managing an AWS RDS (Relational Database) RDS Instance... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_instance_state.html.markdown) |
| `aws_rds_integration` | ✅ | Terraform resource for managing an AWS RDS (Relational Database) zero-ETL int... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_integration.html.markdown) |
| `aws_rds_reserved_instance` | ✅ | Manages an RDS DB Reserved Instance. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_reserved_instance.html.markdown) |
| `aws_rds_shard_group` | ✅ | Terraform resource for managing an Amazon Aurora Limitless Database DB shard ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rds_shard_group.html.markdown) |

---

### Redshift

**产品代码**: `redshift`
**产品线分类**: 数据库
**资源数**: 24

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_redshift_authentication_profile` | ✅ | Creates a Redshift authentication profile | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_authentication_profile.html.markdown) |
| `aws_redshift_cluster` | ✅ | Provides a Redshift Cluster Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_cluster.html.markdown) |
| `aws_redshift_cluster_iam_roles` | ✅ | Provides a Redshift Cluster IAM Roles resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_cluster_iam_roles.html.markdown) |
| `aws_redshift_cluster_snapshot` | ✅ | Creates a Redshift cluster snapshot | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_cluster_snapshot.html.markdown) |
| `aws_redshift_data_share_authorization` | ✅ | Terraform resource for managing an AWS Redshift Data Share Authorization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_data_share_authorization.html.markdown) |
| `aws_redshift_data_share_consumer_association` | ✅ | Terraform resource for managing an AWS Redshift Data Share Consumer Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_data_share_consumer_association.html.markdown) |
| `aws_redshift_endpoint_access` | ✅ | Creates a new Amazon Redshift endpoint access. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_endpoint_access.html.markdown) |
| `aws_redshift_endpoint_authorization` | ✅ | Creates a new Amazon Redshift endpoint authorization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_endpoint_authorization.html.markdown) |
| `aws_redshift_event_subscription` | ✅ | Provides a Redshift event subscription resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_event_subscription.html.markdown) |
| `aws_redshift_hsm_client_certificate` | ✅ | Creates an HSM client certificate that an Amazon Redshift cluster will use to... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_hsm_client_certificate.html.markdown) |
| `aws_redshift_hsm_configuration` | ✅ | Creates an HSM configuration that contains the information required by an Ama... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_hsm_configuration.html.markdown) |
| `aws_redshift_idc_application` | ✅ | Creates a new Amazon Redshift IDC application. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_idc_application.html.markdown) |
| `aws_redshift_integration` | ✅ | Terraform resource for managing a DynamoDB zero-ETL integration or S3 event i... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_integration.html.markdown) |
| `aws_redshift_logging` | ✅ | Terraform resource for managing an AWS Redshift Logging configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_logging.html.markdown) |
| `aws_redshift_parameter_group` | ✅ | Provides a Redshift Cluster parameter group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_parameter_group.html.markdown) |
| `aws_redshift_partner` | ✅ | Creates a new Amazon Redshift Partner Integration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_partner.html.markdown) |
| `aws_redshift_resource_policy` | ✅ | Creates a new Amazon Redshift Resource Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_resource_policy.html.markdown) |
| `aws_redshift_scheduled_action` | ✅ | ```terraform | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_scheduled_action.html.markdown) |
| `aws_redshift_snapshot_copy` | ✅ | Terraform resource for managing an AWS Redshift Snapshot Copy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_snapshot_copy.html.markdown) |
| `aws_redshift_snapshot_copy_grant` | ✅ | Creates a snapshot copy grant that allows AWS Redshift to encrypt copied snap... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_snapshot_copy_grant.html.markdown) |
| `aws_redshift_snapshot_schedule` | ✅ | ```terraform | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_snapshot_schedule.html.markdown) |
| `aws_redshift_snapshot_schedule_association` | ✅ | ```terraform | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_snapshot_schedule_association.html.markdown) |
| `aws_redshift_subnet_group` | ✅ | Creates a new Amazon Redshift subnet group. You must provide a list of one or... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_subnet_group.html.markdown) |
| `aws_redshift_usage_limit` | ✅ | Creates a new Amazon Redshift Usage Limit. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshift_usage_limit.html.markdown) |

---

### Dynamodb

**产品代码**: `dynamodb`
**产品线分类**: 数据库
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_dynamodb_contributor_insights` | ✅ | Provides a DynamoDB contributor insights resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_contributor_insights.html.markdown) |
| `aws_dynamodb_global_secondary_index` | ✅ | !> The resource type `aws_dynamodb_global_secondary_index` is an experimental... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_global_secondary_index.html.markdown) |
| `aws_dynamodb_global_table` | ✅ | Manages [DynamoDB Global Tables V1 (version 2017.11.29)](https://docs.aws.ama... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_global_table.html.markdown) |
| `aws_dynamodb_kinesis_streaming_destination` | ✅ | Enables a [Kinesis streaming destination](https://docs.aws.amazon.com/amazond... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_kinesis_streaming_destination.html.markdown) |
| `aws_dynamodb_resource_policy` | ✅ | Terraform resource for managing an AWS DynamoDB Resource Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_resource_policy.html.markdown) |
| `aws_dynamodb_table` | ✅ | Provides a DynamoDB table resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_table.html.markdown) |
| `aws_dynamodb_table_export` | ✅ | Terraform resource for managing an AWS DynamoDB Table Export. Terraform will ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_table_export.html.markdown) |
| `aws_dynamodb_table_item` | ✅ | Provides a DynamoDB table item resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_table_item.html.markdown) |
| `aws_dynamodb_table_replica` | ✅ | Provides a DynamoDB table replica resource for [DynamoDB Global Tables V2 (ve... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_table_replica.html.markdown) |
| `aws_dynamodb_tag` | ✅ | Manages an individual DynamoDB resource tag. This resource should only be use... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dynamodb_tag.html.markdown) |

---

### Elasticache

**产品代码**: `elasticache`
**产品线分类**: 数据库
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_elasticache_cluster` | ✅ | Provides an ElastiCache Cluster resource, which manages a Memcached cluster, ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_cluster.html.markdown) |
| `aws_elasticache_global_replication_group` | ✅ | Provides an ElastiCache Global Replication Group resource, which manages repl... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_global_replication_group.html.markdown) |
| `aws_elasticache_parameter_group` | ✅ | Provides an ElastiCache parameter group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_parameter_group.html.markdown) |
| `aws_elasticache_replication_group` | ✅ | Provides an ElastiCache Replication Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_replication_group.html.markdown) |
| `aws_elasticache_reserved_cache_node` | ✅ | Manages an ElastiCache Reserved Cache Node. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_reserved_cache_node.html.markdown) |
| `aws_elasticache_serverless_cache` | ✅ | Provides an ElastiCache Serverless Cache resource which manages memcached, re... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_serverless_cache.html.markdown) |
| `aws_elasticache_subnet_group` | ✅ | Provides an ElastiCache Subnet Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_subnet_group.html.markdown) |
| `aws_elasticache_user` | ✅ | Provides an ElastiCache user resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_user.html.markdown) |
| `aws_elasticache_user_group` | ✅ | Provides an ElastiCache user group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_user_group.html.markdown) |
| `aws_elasticache_user_group_association` | ✅ | Associate an existing ElastiCache user and an existing user group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticache_user_group_association.html.markdown) |

---

### Neptune

**产品代码**: `neptune`
**产品线分类**: 数据库
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_neptune_cluster` | ✅ | Provides an Neptune Cluster Resource. A Cluster Resource defines attributes t... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_cluster.html.markdown) |
| `aws_neptune_cluster_endpoint` | ✅ | Provides an Neptune Cluster Endpoint Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_cluster_endpoint.html.markdown) |
| `aws_neptune_cluster_instance` | ✅ | A Cluster Instance Resource defines attributes that are specific to a single ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_cluster_instance.html.markdown) |
| `aws_neptune_cluster_parameter_group` | ✅ | Manages a Neptune Cluster Parameter Group | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_cluster_parameter_group.html.markdown) |
| `aws_neptune_cluster_snapshot` | ✅ | Manages a Neptune database cluster snapshot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_cluster_snapshot.html.markdown) |
| `aws_neptune_event_subscription` | ✅ | ```terraform | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_event_subscription.html.markdown) |
| `aws_neptune_global_cluster` | ✅ | Manages a Neptune Global Cluster. A global cluster consists of one primary re... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_global_cluster.html.markdown) |
| `aws_neptune_parameter_group` | ✅ | Manages a Neptune Parameter Group | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_parameter_group.html.markdown) |
| `aws_neptune_subnet_group` | ✅ | Provides an Neptune subnet group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptune_subnet_group.html.markdown) |

---

### Dms

**产品代码**: `dms`
**产品线分类**: 数据库
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_dms_certificate` | ✅ | Provides a DMS (Data Migration Service) certificate resource. DMS certificate... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_certificate.html.markdown) |
| `aws_dms_endpoint` | ✅ | Provides a DMS (Data Migration Service) endpoint resource. DMS endpoints can ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_endpoint.html.markdown) |
| `aws_dms_event_subscription` | ✅ | Provides a DMS (Data Migration Service) event subscription resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_event_subscription.html.markdown) |
| `aws_dms_replication_config` | ✅ | Provides a DMS Serverless replication config resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_replication_config.html.markdown) |
| `aws_dms_replication_instance` | ✅ | Provides a DMS (Data Migration Service) replication instance resource. DMS re... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_replication_instance.html.markdown) |
| `aws_dms_replication_subnet_group` | ✅ | Provides a DMS (Data Migration Service) replication subnet group resource. DM... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_replication_subnet_group.html.markdown) |
| `aws_dms_replication_task` | ✅ | Provides a DMS (Data Migration Service) replication task resource. DMS replic... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_replication_task.html.markdown) |
| `aws_dms_s3_endpoint` | ✅ | Provides a DMS (Data Migration Service) S3 endpoint resource. DMS S3 endpoint... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dms_s3_endpoint.html.markdown) |

---

### Documentdb

**产品代码**: `documentdb`
**产品线分类**: 数据库
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_docdb_cluster` | ✅ | Manages a DocumentDB Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdb_cluster.html.markdown) |
| `aws_docdb_cluster_instance` | ✅ | Provides an DocumentDB Cluster Resource Instance. A Cluster Instance Resource... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdb_cluster_instance.html.markdown) |
| `aws_docdb_cluster_parameter_group` | ✅ | Manages a DocumentDB Cluster Parameter Group | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdb_cluster_parameter_group.html.markdown) |
| `aws_docdb_cluster_snapshot` | ✅ | Manages a DocumentDB database cluster snapshot for DocumentDB clusters. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdb_cluster_snapshot.html.markdown) |
| `aws_docdb_event_subscription` | ✅ | Provides a DocumentDB event subscription resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdb_event_subscription.html.markdown) |
| `aws_docdb_global_cluster` | ✅ | Manages an DocumentDB Global Cluster. A global cluster consists of one primar... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdb_global_cluster.html.markdown) |
| `aws_docdb_subnet_group` | ✅ | Provides an DocumentDB subnet group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdb_subnet_group.html.markdown) |

---

### Memorydb

**产品代码**: `memorydb`
**产品线分类**: 数据库
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_memorydb_acl` | ✅ | Provides a MemoryDB ACL. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/memorydb_acl.html.markdown) |
| `aws_memorydb_cluster` | ✅ | Provides a MemoryDB Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/memorydb_cluster.html.markdown) |
| `aws_memorydb_multi_region_cluster` | ✅ | Provides a MemoryDB Multi Region Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/memorydb_multi_region_cluster.html.markdown) |
| `aws_memorydb_parameter_group` | ✅ | Provides a MemoryDB Parameter Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/memorydb_parameter_group.html.markdown) |
| `aws_memorydb_snapshot` | ✅ | Provides a MemoryDB Snapshot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/memorydb_snapshot.html.markdown) |
| `aws_memorydb_subnet_group` | ✅ | Provides a MemoryDB Subnet Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/memorydb_subnet_group.html.markdown) |
| `aws_memorydb_user` | ✅ | Provides a MemoryDB User. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/memorydb_user.html.markdown) |

---

### Redshift Serverless

**产品代码**: `redshift_serverless`
**产品线分类**: 数据库
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_redshiftserverless_custom_domain_association` | ✅ | Terraform resource for managing an AWS Redshift Serverless Custom Domain Asso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftserverless_custom_domain_association.html.markdown) |
| `aws_redshiftserverless_endpoint_access` | ✅ | Creates a new Amazon Redshift Serverless Endpoint Access. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftserverless_endpoint_access.html.markdown) |
| `aws_redshiftserverless_namespace` | ✅ | Creates a new Amazon Redshift Serverless Namespace. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftserverless_namespace.html.markdown) |
| `aws_redshiftserverless_resource_policy` | ✅ | Creates a new Amazon Redshift Serverless Resource Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftserverless_resource_policy.html.markdown) |
| `aws_redshiftserverless_snapshot` | ✅ | Creates a new Amazon Redshift Serverless Snapshot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftserverless_snapshot.html.markdown) |
| `aws_redshiftserverless_usage_limit` | ✅ | Creates a new Amazon Redshift Serverless Usage Limit. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftserverless_usage_limit.html.markdown) |
| `aws_redshiftserverless_workgroup` | ✅ | Creates a new Amazon Redshift Serverless Workgroup. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftserverless_workgroup.html.markdown) |

---

### Dynamodb Accelerator

**产品代码**: `dynamodb_accelerator`
**产品线分类**: 数据库
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_dax_cluster` | ✅ | Provides a DAX Cluster resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dax_cluster.html.markdown) |
| `aws_dax_parameter_group` | ✅ | Provides a DAX Parameter Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dax_parameter_group.html.markdown) |
| `aws_dax_subnet_group` | ✅ | Provides a DAX Subnet Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dax_subnet_group.html.markdown) |

---

### Payment Cryptography Control Plane

**产品代码**: `payment_cryptography_control_plane`
**产品线分类**: 数据库
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_paymentcryptography_key` | ✅ | Terraform resource for managing an AWS Payment Cryptography Control Plane Key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/paymentcryptography_key.html.markdown) |
| `aws_paymentcryptography_key_alias` | ✅ | Terraform resource for managing an AWS Payment Cryptography Control Plane Key... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/paymentcryptography_key_alias.html.markdown) |

---

### Qldb

**产品代码**: `qldb`
**产品线分类**: 数据库
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_qldb_ledger` | ✅ | Provides an AWS Quantum Ledger Database (QLDB) resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/qldb_ledger.html.markdown) |
| `aws_qldb_stream` | ✅ | Provides an AWS Quantum Ledger Database (QLDB) Stream resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/qldb_stream.html.markdown) |

---

### Timestream For Influxdb

**产品代码**: `timestream_for_influxdb`
**产品线分类**: 数据库
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_timestreaminfluxdb_db_cluster` | ✅ | Terraform resource for managing an Amazon Timestream for InfluxDB read-replic... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/timestreaminfluxdb_db_cluster.html.markdown) |
| `aws_timestreaminfluxdb_db_instance` | ✅ | Terraform resource for managing an Amazon Timestream for InfluxDB database in... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/timestreaminfluxdb_db_instance.html.markdown) |

---

### Timestream Write

**产品代码**: `timestream_write`
**产品线分类**: 数据库
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_timestreamwrite_database` | ✅ | Provides a Timestream database resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/timestreamwrite_database.html.markdown) |
| `aws_timestreamwrite_table` | ✅ | Provides a Timestream table resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/timestreamwrite_table.html.markdown) |

---

### Documentdb Elastic

**产品代码**: `documentdb_elastic`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_docdbelastic_cluster` | ✅ | Manages an AWS DocDB (DocumentDB) Elastic Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/docdbelastic_cluster.html.markdown) |

---

### Neptune Analytics

**产品代码**: `neptune_analytics`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_neptunegraph_graph` | ✅ | The `aws_neptunegraph_graph` resource creates an Amazon Analytics Graph. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/neptunegraph_graph.html.markdown) |

---

### Redshift Data

**产品代码**: `redshift_data`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_redshiftdata_statement` | ✅ | Executes a Redshift Data Statement. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/redshiftdata_statement.html.markdown) |

---

### Timestream Query

**产品代码**: `timestream_query`
**产品线分类**: 数据库
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_timestreamquery_scheduled_query` | ✅ | Terraform resource for managing an AWS Timestream Query Scheduled Query. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/timestreamquery_scheduled_query.html.markdown) |

---

## 云通信 (16 个产品)

### Ses

**产品代码**: `ses`
**产品线分类**: 云通信
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ses_active_receipt_rule_set` | ✅ | Provides a resource to designate the active SES receipt rule set | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_active_receipt_rule_set.html.markdown) |
| `aws_ses_configuration_set` | ✅ | Provides an SES configuration set resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_configuration_set.html.markdown) |
| `aws_ses_domain_dkim` | ✅ | Provides an SES domain DKIM generation resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_domain_dkim.html.markdown) |
| `aws_ses_domain_identity` | ✅ | Provides an SES domain identity resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_domain_identity.html.markdown) |
| `aws_ses_domain_identity_verification` | ✅ | Represents a successful verification of an SES domain identity. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_domain_identity_verification.html.markdown) |
| `aws_ses_domain_mail_from` | ✅ | Provides an SES domain MAIL FROM resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_domain_mail_from.html.markdown) |
| `aws_ses_email_identity` | ✅ | Provides an SES email identity resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_email_identity.html.markdown) |
| `aws_ses_event_destination` | ✅ | Provides an SES event destination | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_event_destination.html.markdown) |
| `aws_ses_identity_notification_topic` | ✅ | Resource for managing SES Identity Notification Topics | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_identity_notification_topic.html.markdown) |
| `aws_ses_identity_policy` | ✅ | Manages a SES Identity Policy. More information about SES Sending Authorizati... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_identity_policy.html.markdown) |
| `aws_ses_receipt_filter` | ✅ | Provides an SES receipt filter resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_receipt_filter.html.markdown) |
| `aws_ses_receipt_rule` | ✅ | Provides an SES receipt rule resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_receipt_rule.html.markdown) |
| `aws_ses_receipt_rule_set` | ✅ | Provides an SES receipt rule set resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_receipt_rule_set.html.markdown) |
| `aws_ses_template` | ✅ | Provides a resource to create a SES template. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ses_template.html.markdown) |

---

### Sso Admin

**产品代码**: `sso_admin`
**产品线分类**: 云通信
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ssoadmin_account_assignment` | ✅ | Provides a Single Sign-On (SSO) Account Assignment resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_account_assignment.html.markdown) |
| `aws_ssoadmin_application` | ✅ | Terraform resource for managing an AWS SSO Admin Application. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_application.html.markdown) |
| `aws_ssoadmin_application_access_scope` | ✅ | Terraform resource for managing an AWS SSO Admin Application Access Scope. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_application_access_scope.html.markdown) |
| `aws_ssoadmin_application_assignment` | ✅ | Terraform resource for managing an AWS SSO Admin Application Assignment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_application_assignment.html.markdown) |
| `aws_ssoadmin_application_assignment_configuration` | ✅ | Terraform resource for managing an AWS SSO Admin Application Assignment Confi... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_application_assignment_configuration.html.markdown) |
| `aws_ssoadmin_customer_managed_policy_attachment` | ✅ | Provides a customer managed policy attachment for a Single Sign-On (SSO) Perm... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_customer_managed_policy_attachment.html.markdown) |
| `aws_ssoadmin_customer_managed_policy_attachments_exclusive` | ✅ | Terraform resource for managing exclusive AWS SSO Admin Customer Managed Poli... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_customer_managed_policy_attachments_exclusive.html.markdown) |
| `aws_ssoadmin_instance_access_control_attributes` | ✅ | Provides a Single Sign-On (SSO) ABAC Resource: https://docs.aws.amazon.com/si... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_instance_access_control_attributes.html.markdown) |
| `aws_ssoadmin_managed_policy_attachment` | ✅ | Provides an IAM managed policy for a Single Sign-On (SSO) Permission Set reso... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_managed_policy_attachment.html.markdown) |
| `aws_ssoadmin_managed_policy_attachments_exclusive` | ✅ | Terraform resource for managing exclusive AWS SSO Admin Managed Policy Attach... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_managed_policy_attachments_exclusive.html.markdown) |
| `aws_ssoadmin_permission_set` | ✅ | Provides a Single Sign-On (SSO) Permission Set resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_permission_set.html.markdown) |
| `aws_ssoadmin_permission_set_inline_policy` | ✅ | Provides an IAM inline policy for a Single Sign-On (SSO) Permission Set resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_permission_set_inline_policy.html.markdown) |
| `aws_ssoadmin_permissions_boundary_attachment` | ✅ | Attaches a permissions boundary policy to a Single Sign-On (SSO) Permission S... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_permissions_boundary_attachment.html.markdown) |
| `aws_ssoadmin_trusted_token_issuer` | ✅ | Terraform resource for managing an AWS SSO Admin Trusted Token Issuer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ssoadmin_trusted_token_issuer.html.markdown) |

---

### Sesv2

**产品代码**: `sesv2`
**产品线分类**: 云通信
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_sesv2_account_suppression_attributes` | ✅ | Manages AWS SESv2 (Simple Email V2) account-level suppression attributes. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_account_suppression_attributes.html.markdown) |
| `aws_sesv2_account_vdm_attributes` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Account VDM At... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_account_vdm_attributes.html.markdown) |
| `aws_sesv2_configuration_set` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Configuration ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_configuration_set.html.markdown) |
| `aws_sesv2_configuration_set_event_destination` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Configuration ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_configuration_set_event_destination.html.markdown) |
| `aws_sesv2_contact_list` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Contact List. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_contact_list.html.markdown) |
| `aws_sesv2_dedicated_ip_assignment` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Dedicated IP A... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_dedicated_ip_assignment.html.markdown) |
| `aws_sesv2_dedicated_ip_pool` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Dedicated IP P... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_dedicated_ip_pool.html.markdown) |
| `aws_sesv2_email_identity` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Email Identity. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_email_identity.html.markdown) |
| `aws_sesv2_email_identity_feedback_attributes` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Email Identity... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_email_identity_feedback_attributes.html.markdown) |
| `aws_sesv2_email_identity_mail_from_attributes` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Email Identity... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_email_identity_mail_from_attributes.html.markdown) |
| `aws_sesv2_email_identity_policy` | ✅ | Terraform resource for managing an AWS SESv2 (Simple Email V2) Email Identity... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_email_identity_policy.html.markdown) |
| `aws_sesv2_tenant` | ✅ | Manages an AWS SESv2 (Simple Email V2) Tenant. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_tenant.html.markdown) |
| `aws_sesv2_tenant_resource_association` | ✅ | Manages an AWS SESv2 (Simple Email V2) Tenant Resource Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sesv2_tenant_resource_association.html.markdown) |

---

### Pinpoint

**产品代码**: `pinpoint`
**产品线分类**: 云通信
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_pinpoint_adm_channel` | ✅ | Provides a Pinpoint ADM (Amazon Device Messaging) Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_adm_channel.html.markdown) |
| `aws_pinpoint_apns_channel` | ✅ | Provides a Pinpoint APNs Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_apns_channel.html.markdown) |
| `aws_pinpoint_apns_sandbox_channel` | ✅ | Provides a Pinpoint APNs Sandbox Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_apns_sandbox_channel.html.markdown) |
| `aws_pinpoint_apns_voip_channel` | ✅ | Provides a Pinpoint APNs VoIP Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_apns_voip_channel.html.markdown) |
| `aws_pinpoint_apns_voip_sandbox_channel` | ✅ | Provides a Pinpoint APNs VoIP Sandbox Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_apns_voip_sandbox_channel.html.markdown) |
| `aws_pinpoint_app` | ✅ | Provides a Pinpoint App resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_app.html.markdown) |
| `aws_pinpoint_baidu_channel` | ✅ | Provides a Pinpoint Baidu Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_baidu_channel.html.markdown) |
| `aws_pinpoint_email_channel` | ✅ | Provides a Pinpoint Email Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_email_channel.html.markdown) |
| `aws_pinpoint_email_template` | ✅ | Provides a Pinpoint Email Template resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_email_template.html.markdown) |
| `aws_pinpoint_event_stream` | ✅ | Provides a Pinpoint Event Stream resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_event_stream.html.markdown) |
| `aws_pinpoint_gcm_channel` | ✅ | Provides a Pinpoint GCM Channel resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_gcm_channel.html.markdown) |
| `aws_pinpoint_sms_channel` | ✅ | Use the `aws_pinpoint_sms_channel` resource to manage Pinpoint SMS Channels. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpoint_sms_channel.html.markdown) |

---

### Eventbridge

**产品代码**: `eventbridge`
**产品线分类**: 云通信
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudwatch_event_api_destination` | ✅ | Provides an EventBridge event API Destination resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_api_destination.html.markdown) |
| `aws_cloudwatch_event_archive` | ✅ | Provides an EventBridge event archive resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_archive.html.markdown) |
| `aws_cloudwatch_event_bus` | ✅ | Provides an EventBridge event bus resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_bus.html.markdown) |
| `aws_cloudwatch_event_bus_policy` | ✅ | Provides a resource to create an EventBridge resource policy to support cross... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_bus_policy.html.markdown) |
| `aws_cloudwatch_event_connection` | ✅ | Provides an EventBridge connection resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_connection.html.markdown) |
| `aws_cloudwatch_event_endpoint` | ✅ | Provides a resource to create an EventBridge Global Endpoint. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_endpoint.html.markdown) |
| `aws_cloudwatch_event_permission` | ✅ | Provides a resource to create an EventBridge permission to support cross-acco... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_permission.html.markdown) |
| `aws_cloudwatch_event_rule` | ✅ | Provides an EventBridge Rule resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_rule.html.markdown) |
| `aws_cloudwatch_event_target` | ✅ | Provides an EventBridge Target resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudwatch_event_target.html.markdown) |

---

### Sns

**产品代码**: `sns`
**产品线分类**: 云通信
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_sns_platform_application` | ✅ | Provides an SNS platform application resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sns_platform_application.html.markdown) |
| `aws_sns_sms_preferences` | ✅ | Provides a way to set SNS SMS preferences. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sns_sms_preferences.html.markdown) |
| `aws_sns_topic` | ✅ | Provides an SNS topic resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sns_topic.html.markdown) |
| `aws_sns_topic_data_protection_policy` | ✅ | Provides an SNS data protection topic policy resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sns_topic_data_protection_policy.html.markdown) |
| `aws_sns_topic_policy` | ✅ | Provides an SNS topic policy resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sns_topic_policy.html.markdown) |
| `aws_sns_topic_subscription` | ✅ | Provides a resource for subscribing to SNS topics. Requires that an SNS topic... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sns_topic_subscription.html.markdown) |

---

### Verified Permissions

**产品代码**: `verified_permissions`
**产品线分类**: 云通信
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_verifiedpermissions_identity_source` | ✅ | Terraform resource for managing an AWS Verified Permissions Identity Source. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedpermissions_identity_source.html.markdown) |
| `aws_verifiedpermissions_policy` | ✅ | Terraform resource for managing an AWS Verified Permissions Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedpermissions_policy.html.markdown) |
| `aws_verifiedpermissions_policy_store` | ✅ | This is a Terraform resource for managing an AWS Verified Permissions Policy ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedpermissions_policy_store.html.markdown) |
| `aws_verifiedpermissions_policy_template` | ✅ | Terraform resource for managing an AWS Verified Permissions Policy Template. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedpermissions_policy_template.html.markdown) |
| `aws_verifiedpermissions_schema` | ✅ | This is a Terraform resource for managing an AWS Verified Permissions Policy ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/verifiedpermissions_schema.html.markdown) |

---

### Eventbridge Schemas

**产品代码**: `eventbridge_schemas`
**产品线分类**: 云通信
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_schemas_discoverer` | ✅ | Provides an EventBridge Schema Discoverer resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/schemas_discoverer.html.markdown) |
| `aws_schemas_registry` | ✅ | Provides an EventBridge Custom Schema Registry resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/schemas_registry.html.markdown) |
| `aws_schemas_registry_policy` | ✅ | Terraform resource for managing an AWS EventBridge Schemas Registry Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/schemas_registry_policy.html.markdown) |
| `aws_schemas_schema` | ✅ | Provides an EventBridge Schema resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/schemas_schema.html.markdown) |

---

### Sqs

**产品代码**: `sqs`
**产品线分类**: 云通信
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_sqs_queue` | ✅ | Amazon SQS (Simple Queue Service) is a fully managed message queuing service ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sqs_queue.html.markdown) |
| `aws_sqs_queue_policy` | ✅ | Allows you to set a policy of an SQS Queue while referencing the ARN of the q... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sqs_queue_policy.html.markdown) |
| `aws_sqs_queue_redrive_allow_policy` | ✅ | Provides a SQS Queue Redrive Allow Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sqs_queue_redrive_allow_policy.html.markdown) |
| `aws_sqs_queue_redrive_policy` | ✅ | Allows you to set a redrive policy of an SQS Queue | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sqs_queue_redrive_policy.html.markdown) |

---

### End User Messaging Sms

**产品代码**: `end_user_messaging_sms`
**产品线分类**: 云通信
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_pinpointsmsvoicev2_configuration_set` | ✅ | Manages an AWS End User Messaging SMS Configuration Set. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpointsmsvoicev2_configuration_set.html.markdown) |
| `aws_pinpointsmsvoicev2_opt_out_list` | ✅ | Manages an AWS End User Messaging SMS opt-out list. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpointsmsvoicev2_opt_out_list.html.markdown) |
| `aws_pinpointsmsvoicev2_phone_number` | ✅ | Manages an AWS End User Messaging SMS phone number. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pinpointsmsvoicev2_phone_number.html.markdown) |

---

### Appintegrations

**产品代码**: `appintegrations`
**产品线分类**: 云通信
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appintegrations_data_integration` | ✅ | Provides an Amazon AppIntegrations Data Integration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appintegrations_data_integration.html.markdown) |
| `aws_appintegrations_event_integration` | ✅ | Provides an Amazon AppIntegrations Event Integration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appintegrations_event_integration.html.markdown) |

---

### Codeconnections

**产品代码**: `codeconnections`
**产品线分类**: 云通信
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codeconnections_connection` | ✅ | Terraform resource for managing an AWS CodeConnections Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codeconnections_connection.html.markdown) |
| `aws_codeconnections_host` | ✅ | Terraform resource for managing an AWS CodeConnections Host. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codeconnections_host.html.markdown) |

---

### Codestar Connections

**产品代码**: `codestar_connections`
**产品线分类**: 云通信
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codestarconnections_connection` | ✅ | Provides a CodeStar Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codestarconnections_connection.html.markdown) |
| `aws_codestarconnections_host` | ✅ | Provides a CodeStar Host. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codestarconnections_host.html.markdown) |

---

### Mq

**产品代码**: `mq`
**产品线分类**: 云通信
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_mq_broker` | ✅ | Manages an AWS MQ broker. Use to create and manage message brokers for Active... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/mq_broker.html.markdown) |
| `aws_mq_configuration` | ✅ | Manages an Amazon MQ configuration. Use this resource to create and manage br... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/mq_configuration.html.markdown) |

---

### Eventbridge Scheduler

**产品代码**: `eventbridge_scheduler`
**产品线分类**: 云通信
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_scheduler_schedule` | ✅ | Provides an EventBridge Scheduler Schedule resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/scheduler_schedule.html.markdown) |
| `aws_scheduler_schedule_group` | ✅ | Provides an EventBridge Scheduler Schedule Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/scheduler_schedule_group.html.markdown) |

---

### Eventbridge Pipes

**产品代码**: `eventbridge_pipes`
**产品线分类**: 云通信
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_pipes_pipe` | ✅ | Terraform resource for managing an AWS EventBridge Pipes Pipe. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/pipes_pipe.html.markdown) |

---

## 视频云 (3 个产品)

### Elemental Medialive

**产品代码**: `elemental_medialive`
**产品线分类**: 视频云
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_medialive_channel` | ✅ | Terraform resource for managing an AWS MediaLive Channel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/medialive_channel.html.markdown) |
| `aws_medialive_input` | ✅ | Terraform resource for managing an AWS MediaLive Input. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/medialive_input.html.markdown) |
| `aws_medialive_input_security_group` | ✅ | Terraform resource for managing an AWS MediaLive InputSecurityGroup. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/medialive_input_security_group.html.markdown) |
| `aws_medialive_multiplex` | ✅ | Terraform resource for managing an AWS MediaLive Multiplex. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/medialive_multiplex.html.markdown) |
| `aws_medialive_multiplex_program` | ✅ | Terraform resource for managing an AWS MediaLive MultiplexProgram. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/medialive_multiplex_program.html.markdown) |

---

### Elastic Transcoder

**产品代码**: `elastic_transcoder`
**产品线分类**: 视频云
**资源数**: 2 | **已弃用**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_elastictranscoder_pipeline` | ⚠️ 弃用 | Provides an Elastic Transcoder pipeline resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elastictranscoder_pipeline.html.markdown) |
| `aws_elastictranscoder_preset` | ⚠️ 弃用 | Provides an Elastic Transcoder preset resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elastictranscoder_preset.html.markdown) |

---

### Kinesis Video

**产品代码**: `kinesis_video`
**产品线分类**: 视频云
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_kinesis_video_stream` | ✅ | Provides a Kinesis Video Stream resource. Amazon Kinesis Video Streams makes ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesis_video_stream.html.markdown) |

---

## 云原生 (16 个产品)

### Lambda

**产品代码**: `lambda`
**产品线分类**: 云原生
**资源数**: 14

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_lambda_alias` | ✅ | Manages an AWS Lambda Alias. Use this resource to create an alias that points... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_alias.html.markdown) |
| `aws_lambda_capacity_provider` | ✅ | Manages an AWS Lambda Capacity Provider. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_capacity_provider.html.markdown) |
| `aws_lambda_code_signing_config` | ✅ | Manages an AWS Lambda Code Signing Config. Use this resource to define allowe... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_code_signing_config.html.markdown) |
| `aws_lambda_event_source_mapping` | ✅ | Manages an AWS Lambda Event Source Mapping. Use this resource to connect Lamb... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_event_source_mapping.html.markdown) |
| `aws_lambda_function` | ✅ | Manages an AWS Lambda Function. Use this resource to create serverless functi... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_function.html.markdown) |
| `aws_lambda_function_event_invoke_config` | ✅ | Manages an AWS Lambda Function Event Invoke Config. Use this resource to conf... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_function_event_invoke_config.html.markdown) |
| `aws_lambda_function_recursion_config` | ✅ | Manages an AWS Lambda Function Recursion Config. Use this resource to control... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_function_recursion_config.html.markdown) |
| `aws_lambda_function_url` | ✅ | Manages a Lambda function URL. Creates a dedicated HTTP(S) endpoint for a Lam... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_function_url.html.markdown) |
| `aws_lambda_invocation` | ✅ | Manages an AWS Lambda Function invocation. Use this resource to invoke a Lamb... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_invocation.html.markdown) |
| `aws_lambda_layer_version` | ✅ | Manages an AWS Lambda Layer Version. Use this resource to share code and depe... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_layer_version.html.markdown) |
| `aws_lambda_layer_version_permission` | ✅ | Manages an AWS Lambda Layer Version Permission. Use this resource to share La... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_layer_version_permission.html.markdown) |
| `aws_lambda_permission` | ✅ | Manages an AWS Lambda permission. Use this resource to grant external sources... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_permission.html.markdown) |
| `aws_lambda_provisioned_concurrency_config` | ✅ | Manages an AWS Lambda Provisioned Concurrency Configuration. Use this resourc... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_provisioned_concurrency_config.html.markdown) |
| `aws_lambda_runtime_management_config` | ✅ | Manages an AWS Lambda Runtime Management Config. Use this resource to control... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lambda_runtime_management_config.html.markdown) |

---

### Ecr

**产品代码**: `ecr`
**产品线分类**: 云原生
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ecr_account_setting` | ✅ | Provides a resource to manage AWS ECR account settings | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_account_setting.html.markdown) |
| `aws_ecr_lifecycle_policy` | ✅ | Manages an ECR repository lifecycle policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_lifecycle_policy.html.markdown) |
| `aws_ecr_pull_through_cache_rule` | ✅ | Provides an Elastic Container Registry Pull Through Cache Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_pull_through_cache_rule.html.markdown) |
| `aws_ecr_pull_time_update_exclusion` | ✅ | Manages an AWS ECR (Elastic Container Registry) Pull Time Update Exclusion. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_pull_time_update_exclusion.html.markdown) |
| `aws_ecr_registry_policy` | ✅ | Provides an Elastic Container Registry Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_registry_policy.html.markdown) |
| `aws_ecr_registry_scanning_configuration` | ✅ | Provides an Elastic Container Registry Scanning Configuration. Can't be compl... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_registry_scanning_configuration.html.markdown) |
| `aws_ecr_replication_configuration` | ✅ | Provides an Elastic Container Registry Replication Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_replication_configuration.html.markdown) |
| `aws_ecr_repository` | ✅ | Provides an Elastic Container Registry Repository. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_repository.html.markdown) |
| `aws_ecr_repository_creation_template` | ✅ | Provides an Elastic Container Registry Repository Creation Template. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_repository_creation_template.html.markdown) |
| `aws_ecr_repository_policy` | ✅ | Provides an Elastic Container Registry Repository Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecr_repository_policy.html.markdown) |

---

### App Runner

**产品代码**: `app_runner`
**产品线分类**: 云原生
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_apprunner_auto_scaling_configuration_version` | ✅ | Manages an App Runner AutoScaling Configuration Version. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_auto_scaling_configuration_version.html.markdown) |
| `aws_apprunner_connection` | ✅ | Manages an App Runner Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_connection.html.markdown) |
| `aws_apprunner_custom_domain_association` | ✅ | Manages an App Runner Custom Domain association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_custom_domain_association.html.markdown) |
| `aws_apprunner_default_auto_scaling_configuration_version` | ✅ | Manages the default App Runner auto scaling configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_default_auto_scaling_configuration_version.html.markdown) |
| `aws_apprunner_deployment` | ✅ | Manages an App Runner Deployment Operation. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_deployment.html.markdown) |
| `aws_apprunner_observability_configuration` | ✅ | Manages an App Runner Observability Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_observability_configuration.html.markdown) |
| `aws_apprunner_service` | ✅ | Manages an App Runner Service. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_service.html.markdown) |
| `aws_apprunner_vpc_connector` | ✅ | Manages an App Runner VPC Connector. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_vpc_connector.html.markdown) |
| `aws_apprunner_vpc_ingress_connection` | ✅ | Manages an App Runner VPC Ingress Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/apprunner_vpc_ingress_connection.html.markdown) |

---

### Auto Scaling

**产品代码**: `auto_scaling`
**产品线分类**: 云原生
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_autoscaling_attachment` | ✅ | Attaches a load balancer to an Auto Scaling group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_attachment.html.markdown) |
| `aws_autoscaling_group` | ✅ | Provides an Auto Scaling Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_group.html.markdown) |
| `aws_autoscaling_group_tag` | ✅ | Manages an individual Autoscaling Group (ASG) tag. This resource should only ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_group_tag.html.markdown) |
| `aws_autoscaling_lifecycle_hook` | ✅ | Provides an AutoScaling Lifecycle Hook resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_lifecycle_hook.html.markdown) |
| `aws_autoscaling_notification` | ✅ | Provides an AutoScaling Group with Notification support, via SNS Topics. Each of | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_notification.html.markdown) |
| `aws_autoscaling_policy` | ✅ | Provides an AutoScaling Scaling Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_policy.html.markdown) |
| `aws_autoscaling_schedule` | ✅ | Provides an AutoScaling Schedule resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_schedule.html.markdown) |
| `aws_autoscaling_traffic_source_attachment` | ✅ | Attaches a traffic source to an Auto Scaling group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscaling_traffic_source_attachment.html.markdown) |
| `aws_launch_configuration` | ✅ | Provides a resource to create a new launch configuration, used for autoscalin... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/launch_configuration.html.markdown) |

---

### Elastic Kubernetes Service

**产品代码**: `eks`
**产品线分类**: 云原生
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_eks_access_entry` | ✅ | Access Entry Configurations for an EKS Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_access_entry.html.markdown) |
| `aws_eks_access_policy_association` | ✅ | Access Entry Policy Association for an EKS Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_access_policy_association.html.markdown) |
| `aws_eks_addon` | ✅ | Manages an EKS add-on. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_addon.html.markdown) |
| `aws_eks_capability` | ✅ | Manages an EKS Capability for an EKS cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_capability.html.markdown) |
| `aws_eks_cluster` | ✅ | Manages an EKS Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_cluster.html.markdown) |
| `aws_eks_fargate_profile` | ✅ | Manages an EKS Fargate Profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_fargate_profile.html.markdown) |
| `aws_eks_identity_provider_config` | ✅ | Manages an EKS Identity Provider Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_identity_provider_config.html.markdown) |
| `aws_eks_node_group` | ✅ | Manages an EKS Node Group, which can provision and optionally update an Auto ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_node_group.html.markdown) |
| `aws_eks_pod_identity_association` | ✅ | Terraform resource for managing an AWS EKS (Elastic Kubernetes) Pod Identity ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eks_pod_identity_association.html.markdown) |

---

### Appconfig

**产品代码**: `appconfig`
**产品线分类**: 云原生
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appconfig_application` | ✅ | Provides an AppConfig Application resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_application.html.markdown) |
| `aws_appconfig_configuration_profile` | ✅ | Provides an AppConfig Configuration Profile resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_configuration_profile.html.markdown) |
| `aws_appconfig_deployment` | ✅ | Provides an AppConfig Deployment resource for an [`aws_appconfig_application`... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_deployment.html.markdown) |
| `aws_appconfig_deployment_strategy` | ✅ | Provides an AppConfig Deployment Strategy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_deployment_strategy.html.markdown) |
| `aws_appconfig_environment` | ✅ | Provides an AppConfig Environment resource for an [`aws_appconfig_application... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_environment.html.markdown) |
| `aws_appconfig_extension` | ✅ | Provides an AppConfig Extension resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_extension.html.markdown) |
| `aws_appconfig_extension_association` | ✅ | Associates an AppConfig Extension with a Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_extension_association.html.markdown) |
| `aws_appconfig_hosted_configuration_version` | ✅ | Provides an AppConfig Hosted Configuration Version resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appconfig_hosted_configuration_version.html.markdown) |

---

### Opensearch Serverless

**产品代码**: `opensearch_serverless`
**产品线分类**: 云原生
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_opensearchserverless_access_policy` | ✅ | Terraform resource for managing an AWS OpenSearch Serverless Access Policy. S... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearchserverless_access_policy.html.markdown) |
| `aws_opensearchserverless_collection` | ✅ | Terraform resource for managing an AWS OpenSearch Serverless Collection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearchserverless_collection.html.markdown) |
| `aws_opensearchserverless_lifecycle_policy` | ✅ | Terraform resource for managing an AWS OpenSearch Serverless Lifecycle Policy... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearchserverless_lifecycle_policy.html.markdown) |
| `aws_opensearchserverless_security_config` | ✅ | Terraform resource for managing an AWS OpenSearch Serverless Security Config. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearchserverless_security_config.html.markdown) |
| `aws_opensearchserverless_security_policy` | ✅ | Terraform resource for managing an AWS OpenSearch Serverless Security Policy.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearchserverless_security_policy.html.markdown) |
| `aws_opensearchserverless_vpc_endpoint` | ✅ | Terraform resource for managing an AWS OpenSearchServerless VPC Endpoint. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearchserverless_vpc_endpoint.html.markdown) |

---

### Secrets Manager

**产品代码**: `secrets_manager`
**产品线分类**: 云原生
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_secretsmanager_secret` | ✅ | Provides a resource to manage AWS Secrets Manager secret metadata. To manage ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/secretsmanager_secret.html.markdown) |
| `aws_secretsmanager_secret_policy` | ✅ | Provides a resource to manage AWS Secrets Manager secret policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/secretsmanager_secret_policy.html.markdown) |
| `aws_secretsmanager_secret_rotation` | ✅ | Provides a resource to manage AWS Secrets Manager secret rotation. To manage ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/secretsmanager_secret_rotation.html.markdown) |
| `aws_secretsmanager_secret_version` | ✅ | Provides a resource to manage AWS Secrets Manager secret version including it... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/secretsmanager_secret_version.html.markdown) |
| `aws_secretsmanager_tag` | ✅ | Manages an individual AWS Secrets Manager secret tag. This resource should on... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/secretsmanager_tag.html.markdown) |

---

### Batch

**产品代码**: `batch`
**产品线分类**: 云原生
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_batch_compute_environment` | ✅ | Creates a AWS Batch compute environment. Compute environments contain the Ama... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/batch_compute_environment.html.markdown) |
| `aws_batch_job_definition` | ✅ | Provides a Batch Job Definition resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/batch_job_definition.html.markdown) |
| `aws_batch_job_queue` | ✅ | Provides a Batch Job Queue resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/batch_job_queue.html.markdown) |
| `aws_batch_scheduling_policy` | ✅ | Provides a Batch Scheduling Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/batch_scheduling_policy.html.markdown) |

---

### Application Auto Scaling

**产品代码**: `application_auto_scaling`
**产品线分类**: 云原生
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appautoscaling_policy` | ✅ | Provides an Application AutoScaling Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appautoscaling_policy.html.markdown) |
| `aws_appautoscaling_scheduled_action` | ✅ | Provides an Application AutoScaling ScheduledAction resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appautoscaling_scheduled_action.html.markdown) |
| `aws_appautoscaling_target` | ✅ | Provides an Application AutoScaling ScalableTarget resource. To manage polici... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appautoscaling_target.html.markdown) |

---

### Ecr Public

**产品代码**: `ecr_public`
**产品线分类**: 云原生
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ecrpublic_repository` | ✅ | Provides a Public Elastic Container Registry Repository. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecrpublic_repository.html.markdown) |
| `aws_ecrpublic_repository_policy` | ✅ | Provides an Elastic Container Registry Public Repository Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecrpublic_repository_policy.html.markdown) |

---

### Emr Containers

**产品代码**: `emr_containers`
**产品线分类**: 云原生
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_emrcontainers_job_template` | ✅ | Manages an EMR Containers (EMR on EKS) Job Template. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emrcontainers_job_template.html.markdown) |
| `aws_emrcontainers_virtual_cluster` | ✅ | Manages an EMR Containers (EMR on EKS) Virtual Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emrcontainers_virtual_cluster.html.markdown) |

---

### Kinesis Analytics V2

**产品代码**: `kinesis_analytics_v2`
**产品线分类**: 云原生
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_kinesisanalyticsv2_application` | ✅ | Manages a Kinesis Analytics v2 Application. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesisanalyticsv2_application.html.markdown) |
| `aws_kinesisanalyticsv2_application_snapshot` | ✅ | Manages a Kinesis Analytics v2 Application Snapshot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesisanalyticsv2_application_snapshot.html.markdown) |

---

### Auto Scaling Plans

**产品代码**: `auto_scaling_plans`
**产品线分类**: 云原生
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_autoscalingplans_scaling_plan` | ✅ | Manages an AWS Auto Scaling scaling plan. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/autoscalingplans_scaling_plan.html.markdown) |

---

### Emr Serverless

**产品代码**: `emr_serverless`
**产品线分类**: 云原生
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_emrserverless_application` | ✅ | Manages an EMR Serverless Application. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emrserverless_application.html.markdown) |

---

### Kinesis Analytics

**产品代码**: `kinesis_analytics`
**产品线分类**: 云原生
**资源数**: 1 | **已弃用**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_kinesis_analytics_application` | ⚠️ 弃用 → `aws_kinesisanalyticsv2_application` | Provides a Kinesis Analytics Application resource. Kinesis Analytics is a man... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesis_analytics_application.html.markdown) |

---

## 弹性计算 (12 个产品)

### Elastic Compute Cloud

**产品代码**: `ec2`
**产品线分类**: 弹性计算
**资源数**: 29

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ami` | ✅ | The AMI resource allows the creation and management of a completely-custom | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ami.html.markdown) |
| `aws_ami_copy` | ✅ | The "AMI copy" resource allows duplication of an Amazon Machine Image (AMI), | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ami_copy.html.markdown) |
| `aws_ami_from_instance` | ✅ | The "AMI from instance" resource allows the creation of an Amazon Machine | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ami_from_instance.html.markdown) |
| `aws_ami_launch_permission` | ✅ | Adds a launch permission to an Amazon Machine Image (AMI). | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ami_launch_permission.html.markdown) |
| `aws_ec2_allowed_images_settings` | ✅ | Provides EC2 allowed images settings for an AWS account. This feature allows ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_allowed_images_settings.html.markdown) |
| `aws_ec2_availability_zone_group` | ✅ | Manages an EC2 Availability Zone Group, such as updating its opt-in status. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_availability_zone_group.html.markdown) |
| `aws_ec2_capacity_block_reservation` | ✅ | Provides an EC2 Capacity Block Reservation. This allows you to purchase capac... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_capacity_block_reservation.html.markdown) |
| `aws_ec2_capacity_reservation` | ✅ | Provides an EC2 Capacity Reservation. This allows you to reserve capacity for... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_capacity_reservation.html.markdown) |
| `aws_ec2_default_credit_specification` | ✅ | Terraform resource for managing an AWS EC2 (Elastic Compute Cloud) Default Cr... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_default_credit_specification.html.markdown) |
| `aws_ec2_fleet` | ✅ | Provides a resource to manage EC2 Fleets. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_fleet.html.markdown) |
| `aws_ec2_host` | ✅ | Provides an EC2 Host resource. This allows Dedicated Hosts to be allocated, m... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_host.html.markdown) |
| `aws_ec2_image_block_public_access` | ✅ | Provides a regional public access block for AMIs. This prevents AMIs from bei... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_image_block_public_access.html.markdown) |
| `aws_ec2_instance_connect_endpoint` | ✅ | Manages an EC2 Instance Connect Endpoint. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_instance_connect_endpoint.html.markdown) |
| `aws_ec2_instance_metadata_defaults` | ✅ | Manages regional EC2 instance metadata default settings. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_instance_metadata_defaults.html.markdown) |
| `aws_ec2_instance_state` | ✅ | Provides an EC2 instance state resource. This allows managing an instance pow... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_instance_state.html.markdown) |
| `aws_ec2_secondary_network` | ✅ | Provides an EC2 Secondary Network resource for RDMA networking. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_secondary_network.html.markdown) |
| `aws_ec2_secondary_subnet` | ✅ | Provides an EC2 Secondary Subnet resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_secondary_subnet.html.markdown) |
| `aws_ec2_serial_console_access` | ✅ | Provides a resource to manage whether serial console access is enabled for yo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_serial_console_access.html.markdown) |
| `aws_ec2_tag` | ✅ | Manages an individual EC2 resource tag. This resource should only be used in ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_tag.html.markdown) |
| `aws_eip` | ✅ | Provides an Elastic IP resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eip.html.markdown) |
| `aws_eip_association` | ✅ | Provides an AWS EIP Association as a top level resource, to associate and dis... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eip_association.html.markdown) |
| `aws_eip_domain_name` | ✅ | Assigns a static reverse DNS record to an Elastic IP addresses. See [Using re... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/eip_domain_name.html.markdown) |
| `aws_instance` | ✅ | Provides an EC2 instance resource. This allows instances to be created, updat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/instance.html.markdown) |
| `aws_key_pair` | ✅ | Provides an [EC2 key pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuid... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/key_pair.html.markdown) |
| `aws_launch_template` | ✅ | Provides an EC2 launch template resource. Can be used to create instances or ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/launch_template.html.markdown) |
| `aws_placement_group` | ✅ | Provides an EC2 placement group. Read more about placement groups | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/placement_group.html.markdown) |
| `aws_spot_datafeed_subscription` | ✅ | To help you understand the charges for your Spot instances, Amazon EC2 provid... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/spot_datafeed_subscription.html.markdown) |
| `aws_spot_fleet_request` | ✅ | Provides an EC2 Spot Fleet Request resource. This allows a fleet of Spot | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/spot_fleet_request.html.markdown) |
| `aws_spot_instance_request` | ✅ | Provides an EC2 Spot Instance Request resource. This allows instances to be | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/spot_instance_request.html.markdown) |

---

### Datasync

**产品代码**: `datasync`
**产品线分类**: 弹性计算
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_datasync_agent` | ✅ | Manages an AWS DataSync Agent deployed on premises. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_agent.html.markdown) |
| `aws_datasync_location_azure_blob` | ✅ | Manages a Microsoft Azure Blob Storage Location within AWS DataSync. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_azure_blob.html.markdown) |
| `aws_datasync_location_efs` | ✅ | Manages an AWS DataSync EFS Location. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_efs.html.markdown) |
| `aws_datasync_location_fsx_lustre_file_system` | ✅ | Manages an AWS DataSync FSx Lustre Location. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_fsx_lustre_file_system.html.markdown) |
| `aws_datasync_location_fsx_ontap_file_system` | ✅ | Terraform resource for managing an AWS DataSync Location FSx Ontap File System. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_fsx_ontap_file_system.html.markdown) |
| `aws_datasync_location_fsx_openzfs_file_system` | ✅ | Manages an AWS DataSync FSx OpenZfs Location. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_fsx_openzfs_file_system.html.markdown) |
| `aws_datasync_location_fsx_windows_file_system` | ✅ | Manages an AWS DataSync FSx Windows Location. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_fsx_windows_file_system.html.markdown) |
| `aws_datasync_location_hdfs` | ✅ | Manages an HDFS Location within AWS DataSync. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_hdfs.html.markdown) |
| `aws_datasync_location_nfs` | ✅ | Manages an NFS Location within AWS DataSync. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_nfs.html.markdown) |
| `aws_datasync_location_object_storage` | ✅ | Manages a Object Storage Location within AWS DataSync. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_object_storage.html.markdown) |
| `aws_datasync_location_s3` | ✅ | Manages an S3 Location within AWS DataSync. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_s3.html.markdown) |
| `aws_datasync_location_smb` | ✅ | Manages a SMB Location within AWS DataSync. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_location_smb.html.markdown) |
| `aws_datasync_task` | ✅ | Manages an AWS DataSync Task, which represents a configuration for synchroniz... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datasync_task.html.markdown) |

---

### Transfer Family

**产品代码**: `transfer_family`
**产品线分类**: 弹性计算
**资源数**: 13

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_transfer_access` | ✅ | Provides a AWS Transfer Access resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_access.html.markdown) |
| `aws_transfer_agreement` | ✅ | Provides a AWS Transfer AS2 Agreement resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_agreement.html.markdown) |
| `aws_transfer_certificate` | ✅ | Provides a AWS Transfer AS2 Certificate resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_certificate.html.markdown) |
| `aws_transfer_connector` | ✅ | Provides a AWS Transfer AS2 Connector resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_connector.html.markdown) |
| `aws_transfer_host_key` | ✅ | Manages a host key for a server. This is an [_additional server host key_](ht... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_host_key.html.markdown) |
| `aws_transfer_profile` | ✅ | Provides a AWS Transfer AS2 Profile resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_profile.html.markdown) |
| `aws_transfer_server` | ✅ | Provides a AWS Transfer Server resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_server.html.markdown) |
| `aws_transfer_ssh_key` | ✅ | Provides a AWS Transfer User SSH Key resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_ssh_key.html.markdown) |
| `aws_transfer_tag` | ✅ | Manages an individual Transfer Family resource tag. This resource should only... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_tag.html.markdown) |
| `aws_transfer_user` | ✅ | Provides a AWS Transfer User resource. Managing SSH keys can be accomplished ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_user.html.markdown) |
| `aws_transfer_web_app` | ✅ | Terraform resource for managing an AWS Transfer Family Web App. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_web_app.html.markdown) |
| `aws_transfer_web_app_customization` | ✅ | Terraform resource for managing an AWS Transfer Family Web App Customization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_web_app_customization.html.markdown) |
| `aws_transfer_workflow` | ✅ | Provides a AWS Transfer Workflow resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transfer_workflow.html.markdown) |

---

### Elastic Compute Service

**产品代码**: `ecs`
**产品线分类**: 弹性计算
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ecs_account_setting_default` | ✅ | Provides an ECS default account setting for a specific ECS Resource name with... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_account_setting_default.html.markdown) |
| `aws_ecs_capacity_provider` | ✅ | Provides an ECS cluster capacity provider. More information can be found on t... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_capacity_provider.html.markdown) |
| `aws_ecs_cluster` | ✅ | Provides an ECS cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_cluster.html.markdown) |
| `aws_ecs_cluster_capacity_providers` | ✅ | Manages the capacity providers of an ECS Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_cluster_capacity_providers.html.markdown) |
| `aws_ecs_express_gateway_service` | ✅ | Manages an ECS Express service. The Express service provides a simplified way... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_express_gateway_service.html.markdown) |
| `aws_ecs_service` | ✅ | Provides an ECS service - effectively a task that is expected to run until an... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_service.html.markdown) |
| `aws_ecs_tag` | ✅ | Manages an individual ECS resource tag. This resource should only be used in ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_tag.html.markdown) |
| `aws_ecs_task_definition` | ✅ | Manages a revision of an ECS task definition to be used in `aws_ecs_service`. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_task_definition.html.markdown) |
| `aws_ecs_task_set` | ✅ | Provides an ECS task set - effectively a task that is expected to run until a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ecs_task_set.html.markdown) |

---

### Ec2 Image Builder

**产品代码**: `ec2_image_builder`
**产品线分类**: 弹性计算
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_imagebuilder_component` | ✅ | Manages an Image Builder Component. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_component.html.markdown) |
| `aws_imagebuilder_container_recipe` | ✅ | Manages an Image Builder Container Recipe. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_container_recipe.html.markdown) |
| `aws_imagebuilder_distribution_configuration` | ✅ | Manages an Image Builder Distribution Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_distribution_configuration.html.markdown) |
| `aws_imagebuilder_image` | ✅ | Manages an Image Builder Image. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_image.html.markdown) |
| `aws_imagebuilder_image_pipeline` | ✅ | Manages an Image Builder Image Pipeline. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_image_pipeline.html.markdown) |
| `aws_imagebuilder_image_recipe` | ✅ | Manages an Image Builder Image Recipe. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_image_recipe.html.markdown) |
| `aws_imagebuilder_infrastructure_configuration` | ✅ | Manages an Image Builder Infrastructure Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_infrastructure_configuration.html.markdown) |
| `aws_imagebuilder_lifecycle_policy` | ✅ | Manages an Image Builder Lifecycle Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_lifecycle_policy.html.markdown) |
| `aws_imagebuilder_workflow` | ✅ | Terraform resource for managing an AWS EC2 Image Builder Workflow. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/imagebuilder_workflow.html.markdown) |

---

### Managed Streaming For Kafka

**产品代码**: `managed_streaming_for_kafka`
**产品线分类**: 弹性计算
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_msk_cluster` | ✅ | Manages an Amazon MSK cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_cluster.html.markdown) |
| `aws_msk_cluster_policy` | ✅ | Terraform resource for managing an AWS Managed Streaming for Kafka Cluster Po... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_cluster_policy.html.markdown) |
| `aws_msk_configuration` | ✅ | Manages an Amazon Managed Streaming for Kafka configuration. More information... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_configuration.html.markdown) |
| `aws_msk_replicator` | ✅ | Terraform resource for managing an AWS Managed Streaming for Kafka Replicator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_replicator.html.markdown) |
| `aws_msk_scram_secret_association` | ✅ | Associates SCRAM secrets stored in the Secrets Manager service with a Managed... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_scram_secret_association.html.markdown) |
| `aws_msk_serverless_cluster` | ✅ | Manages an Amazon MSK Serverless cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_serverless_cluster.html.markdown) |
| `aws_msk_single_scram_secret_association` | ✅ | Associates a single SCRAM secret with a Managed Streaming for Kafka (MSK) clu... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_single_scram_secret_association.html.markdown) |
| `aws_msk_topic` | ✅ | Manages an AWS Managed Streaming for Kafka Topic. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_topic.html.markdown) |
| `aws_msk_vpc_connection` | ✅ | Terraform resource for managing an AWS Managed Streaming for Kafka VPC Connec... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/msk_vpc_connection.html.markdown) |

---

### Oracle Database@Aws

**产品代码**: `oracle_database@aws`
**产品线分类**: 弹性计算
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_odb_cloud_autonomous_vm_cluster` | ✅ | Terraform resource managing cloud autonomous vm cluster in AWS for Oracle Dat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/odb_cloud_autonomous_vm_cluster.html.markdown) |
| `aws_odb_cloud_exadata_infrastructure` | ✅ | Terraform resource for managing exadata infrastructure resource in AWS for Or... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/odb_cloud_exadata_infrastructure.html.markdown) |
| `aws_odb_cloud_vm_cluster` | ✅ | Terraform to manage cloud vm cluster resource in AWS for Oracle Database@AWS.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/odb_cloud_vm_cluster.html.markdown) |
| `aws_odb_network` | ✅ | Terraform resource for managing odb Network resource in AWS for Oracle Databa... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/odb_network.html.markdown) |
| `aws_odb_network_peering_connection` | ✅ | Terraform  resource for managing oracle database network peering resource in ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/odb_network_peering_connection.html.markdown) |

---

### Elastic Beanstalk

**产品代码**: `elastic_beanstalk`
**产品线分类**: 弹性计算
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_elastic_beanstalk_application` | ✅ | Provides an Elastic Beanstalk Application Resource. Elastic Beanstalk allows | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elastic_beanstalk_application.html.markdown) |
| `aws_elastic_beanstalk_application_version` | ✅ | Provides an Elastic Beanstalk Application Version Resource. Elastic Beanstalk... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elastic_beanstalk_application_version.html.markdown) |
| `aws_elastic_beanstalk_configuration_template` | ✅ | Provides an Elastic Beanstalk Configuration Template, which are associated with | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elastic_beanstalk_configuration_template.html.markdown) |
| `aws_elastic_beanstalk_environment` | ✅ | Provides an Elastic Beanstalk Environment Resource. Elastic Beanstalk allows | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elastic_beanstalk_environment.html.markdown) |

---

### Managed Streaming For Kafka Connect

**产品代码**: `managed_streaming_for_kafka_connect`
**产品线分类**: 弹性计算
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_mskconnect_connector` | ✅ | Provides an Amazon MSK Connect Connector resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/mskconnect_connector.html.markdown) |
| `aws_mskconnect_custom_plugin` | ✅ | Provides an Amazon MSK Connect Custom Plugin Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/mskconnect_custom_plugin.html.markdown) |
| `aws_mskconnect_worker_configuration` | ✅ | Provides an Amazon MSK Connect Worker Configuration Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/mskconnect_worker_configuration.html.markdown) |

---

### Elemental Mediastore

**产品代码**: `elemental_mediastore`
**产品线分类**: 弹性计算
**资源数**: 2 | **已弃用**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_media_store_container` | ⚠️ 弃用 | Provides a MediaStore Container. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/media_store_container.html.markdown) |
| `aws_media_store_container_policy` | ⚠️ 弃用 → `aws_iam_policy_document` | Provides a MediaStore Container Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/media_store_container_policy.html.markdown) |

---

### Opensearch Ingestion

**产品代码**: `opensearch_ingestion`
**产品线分类**: 弹性计算
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_osis_pipeline` | ✅ | Terraform resource for managing an AWS OpenSearch Ingestion Pipeline. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/osis_pipeline.html.markdown) |

---

### Amazon Q Business

**产品代码**: `amazon_q_business`
**产品线分类**: 弹性计算
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_qbusiness_application` | ✅ | Provides a Q Business Application resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/qbusiness_application.html.markdown) |

---

## CDN及边缘云 (2 个产品)

### Cloudfront

**产品代码**: `cloudfront`
**产品线分类**: CDN及边缘云
**资源数**: 22

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudfront_anycast_ip_list` | ✅ | Terraform resource for managing a CloudFront Anycast IP List. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_anycast_ip_list.html.markdown) |
| `aws_cloudfront_cache_policy` | ✅ | Use the `aws_cloudfront_cache_policy` resource to create a cache policy for C... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_cache_policy.html.markdown) |
| `aws_cloudfront_connection_function` | ✅ | Manages an AWS CloudFront Connection Function. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_connection_function.html.markdown) |
| `aws_cloudfront_connection_group` | ✅ | Creates an Amazon CloudFront Connection Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_connection_group.html.markdown) |
| `aws_cloudfront_continuous_deployment_policy` | ✅ | Terraform resource for managing an AWS CloudFront Continuous Deployment Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_continuous_deployment_policy.html.markdown) |
| `aws_cloudfront_distribution` | ✅ | Creates an Amazon CloudFront web distribution. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_distribution.html.markdown) |
| `aws_cloudfront_distribution_tenant` | ✅ | Creates an Amazon CloudFront distribution tenant. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_distribution_tenant.html.markdown) |
| `aws_cloudfront_field_level_encryption_config` | ✅ | Provides a CloudFront Field-level Encryption Config resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_field_level_encryption_config.html.markdown) |
| `aws_cloudfront_field_level_encryption_profile` | ✅ | Provides a CloudFront Field-level Encryption Profile resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_field_level_encryption_profile.html.markdown) |
| `aws_cloudfront_function` | ✅ | Provides a CloudFront Function resource. With CloudFront Functions in Amazon ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_function.html.markdown) |
| `aws_cloudfront_key_group` | ✅ | The following example below creates a CloudFront key group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_key_group.html.markdown) |
| `aws_cloudfront_key_value_store` | ✅ | Terraform resource for managing an AWS CloudFront Key Value Store. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_key_value_store.html.markdown) |
| `aws_cloudfront_monitoring_subscription` | ✅ | Provides a CloudFront real-time log configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_monitoring_subscription.html.markdown) |
| `aws_cloudfront_multitenant_distribution` | ✅ | Creates an Amazon CloudFront multi-tenant distribution. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_multitenant_distribution.html.markdown) |
| `aws_cloudfront_origin_access_control` | ✅ | Manages an AWS CloudFront Origin Access Control, which is used by CloudFront ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_origin_access_control.html.markdown) |
| `aws_cloudfront_origin_access_identity` | ✅ | Creates an Amazon CloudFront origin access identity. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_origin_access_identity.html.markdown) |
| `aws_cloudfront_origin_request_policy` | ✅ | The following example below creates a CloudFront origin request policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_origin_request_policy.html.markdown) |
| `aws_cloudfront_public_key` | ✅ | The following example below creates a CloudFront public key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_public_key.html.markdown) |
| `aws_cloudfront_realtime_log_config` | ✅ | Provides a CloudFront real-time log configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_realtime_log_config.html.markdown) |
| `aws_cloudfront_response_headers_policy` | ✅ | Provides a CloudFront response headers policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_response_headers_policy.html.markdown) |
| `aws_cloudfront_trust_store` | ✅ | Manages an AWS CloudFront Trust Store. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_trust_store.html.markdown) |
| `aws_cloudfront_vpc_origin` | ✅ | Creates an Amazon CloudFront VPC origin. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfront_vpc_origin.html.markdown) |

---

### Cloudfront Keyvaluestore

**产品代码**: `cloudfront_keyvaluestore`
**产品线分类**: CDN及边缘云
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudfrontkeyvaluestore_key` | ✅ | Terraform resource for managing an AWS CloudFront KeyValueStore Key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfrontkeyvaluestore_key.html.markdown) |
| `aws_cloudfrontkeyvaluestore_keys_exclusive` | ✅ | Terraform resource for maintaining exclusive management of resource key value... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudfrontkeyvaluestore_keys_exclusive.html.markdown) |

---

## 计算平台和AI (28 个产品)

### Sagemaker Ai

**产品代码**: `sagemaker_ai`
**产品线分类**: 计算平台和AI
**资源数**: 34

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_sagemaker_app` | ✅ | Provides a SageMaker AI App resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_app.html.markdown) |
| `aws_sagemaker_app_image_config` | ✅ | Provides a SageMaker AI App Image Config resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_app_image_config.html.markdown) |
| `aws_sagemaker_code_repository` | ✅ | Provides a SageMaker AI Code Repository resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_code_repository.html.markdown) |
| `aws_sagemaker_data_quality_job_definition` | ✅ | Provides a SageMaker AI data quality job definition resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_data_quality_job_definition.html.markdown) |
| `aws_sagemaker_device` | ✅ | Provides a SageMaker AI Device resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_device.html.markdown) |
| `aws_sagemaker_device_fleet` | ✅ | Provides a SageMaker AI Device Fleet resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_device_fleet.html.markdown) |
| `aws_sagemaker_domain` | ✅ | Provides a SageMaker AI Domain resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_domain.html.markdown) |
| `aws_sagemaker_endpoint` | ✅ | Provides a SageMaker AI Endpoint resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_endpoint.html.markdown) |
| `aws_sagemaker_endpoint_configuration` | ✅ | Provides a SageMaker AI endpoint configuration resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_endpoint_configuration.html.markdown) |
| `aws_sagemaker_feature_group` | ✅ | Provides a SageMaker AI Feature Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_feature_group.html.markdown) |
| `aws_sagemaker_flow_definition` | ✅ | Provides a SageMaker AI Flow Definition resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_flow_definition.html.markdown) |
| `aws_sagemaker_hub` | ✅ | Provides a SageMaker AI Hub resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_hub.html.markdown) |
| `aws_sagemaker_human_task_ui` | ✅ | Provides a SageMaker AI Human Task UI resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_human_task_ui.html.markdown) |
| `aws_sagemaker_image` | ✅ | Provides a SageMaker AI Image resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_image.html.markdown) |
| `aws_sagemaker_image_version` | ✅ | Provides a SageMaker AI Image Version resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_image_version.html.markdown) |
| `aws_sagemaker_labeling_job` | ✅ | Manage an Amazon SageMaker labeling job. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_labeling_job.html.markdown) |
| `aws_sagemaker_mlflow_app` | ✅ | Provides a SageMaker AI MLflow App resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_mlflow_app.html.markdown) |
| `aws_sagemaker_mlflow_tracking_server` | ✅ | Provides a SageMaker AI MLFlow Tracking Server resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_mlflow_tracking_server.html.markdown) |
| `aws_sagemaker_model` | ✅ | Manages an Amazon SageMaker AI Model. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_model.html.markdown) |
| `aws_sagemaker_model_card` | ✅ | Manage an Amazon SageMaker Model Card. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_model_card.html.markdown) |
| `aws_sagemaker_model_card_export_job` | ✅ | Manage an Amazon SageMaker Model Card export job. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_model_card_export_job.html.markdown) |
| `aws_sagemaker_model_package_group` | ✅ | Provides a SageMaker AI Model Package Group resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_model_package_group.html.markdown) |
| `aws_sagemaker_model_package_group_policy` | ✅ | Provides a SageMaker AI Model Package Group Policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_model_package_group_policy.html.markdown) |
| `aws_sagemaker_monitoring_schedule` | ✅ | Provides a SageMaker AI monitoring schedule resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_monitoring_schedule.html.markdown) |
| `aws_sagemaker_notebook_instance` | ✅ | Provides a SageMaker AI Notebook Instance resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_notebook_instance.html.markdown) |
| `aws_sagemaker_notebook_instance_lifecycle_configuration` | ✅ | Provides a lifecycle configuration for SageMaker AI Notebook Instances. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_notebook_instance_lifecycle_configuration.html.markdown) |
| `aws_sagemaker_pipeline` | ✅ | Provides a SageMaker AI Pipeline resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_pipeline.html.markdown) |
| `aws_sagemaker_project` | ✅ | Provides a SageMaker AI Project resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_project.html.markdown) |
| `aws_sagemaker_servicecatalog_portfolio_status` | ✅ | Manages status of Service Catalog in SageMaker. Service Catalog is used to cr... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_servicecatalog_portfolio_status.html.markdown) |
| `aws_sagemaker_space` | ✅ | Provides a SageMaker AI Space resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_space.html.markdown) |
| `aws_sagemaker_studio_lifecycle_config` | ✅ | Provides a SageMaker AI Studio Lifecycle Config resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_studio_lifecycle_config.html.markdown) |
| `aws_sagemaker_user_profile` | ✅ | Provides a SageMaker AI User Profile resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_user_profile.html.markdown) |
| `aws_sagemaker_workforce` | ✅ | Provides a SageMaker AI Workforce resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_workforce.html.markdown) |
| `aws_sagemaker_workteam` | ✅ | Provides a SageMaker AI Workteam resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sagemaker_workteam.html.markdown) |

---

### Quicksight

**产品代码**: `quicksight`
**产品线分类**: 计算平台和AI
**资源数**: 25

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_quicksight_account_settings` | ✅ | Terraform resource for managing an AWS QuickSight Account Settings. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_account_settings.html.markdown) |
| `aws_quicksight_account_subscription` | ✅ | Terraform resource for managing an AWS QuickSight Account Subscription. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_account_subscription.html.markdown) |
| `aws_quicksight_analysis` | ✅ | Resource for managing a QuickSight Analysis. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_analysis.html.markdown) |
| `aws_quicksight_custom_permissions` | ✅ | Manages a QuickSight custom permissions profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_custom_permissions.html.markdown) |
| `aws_quicksight_dashboard` | ✅ | Resource for managing a QuickSight Dashboard. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_dashboard.html.markdown) |
| `aws_quicksight_data_set` | ✅ | Resource for managing a QuickSight Data Set. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_data_set.html.markdown) |
| `aws_quicksight_data_source` | ✅ | Resource for managing QuickSight Data Source | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_data_source.html.markdown) |
| `aws_quicksight_folder` | ✅ | Resource for managing a QuickSight Folder. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_folder.html.markdown) |
| `aws_quicksight_folder_membership` | ✅ | Terraform resource for managing an AWS QuickSight Folder Membership. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_folder_membership.html.markdown) |
| `aws_quicksight_group` | ✅ | Resource for managing QuickSight Group | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_group.html.markdown) |
| `aws_quicksight_group_membership` | ✅ | Resource for managing QuickSight Group Membership | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_group_membership.html.markdown) |
| `aws_quicksight_iam_policy_assignment` | ✅ | Terraform resource for managing an AWS QuickSight IAM Policy Assignment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_iam_policy_assignment.html.markdown) |
| `aws_quicksight_ingestion` | ✅ | Terraform resource for managing an AWS QuickSight Ingestion. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_ingestion.html.markdown) |
| `aws_quicksight_ip_restriction` | ✅ | Manages the content and status of IP rules. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_ip_restriction.html.markdown) |
| `aws_quicksight_key_registration` | ✅ | Registers customer managed keys in a Amazon QuickSight account. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_key_registration.html.markdown) |
| `aws_quicksight_namespace` | ✅ | Terraform resource for managing an AWS QuickSight Namespace. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_namespace.html.markdown) |
| `aws_quicksight_refresh_schedule` | ✅ | Resource for managing a QuickSight Refresh Schedule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_refresh_schedule.html.markdown) |
| `aws_quicksight_role_custom_permission` | ✅ | Manages the custom permissions that are associated with a role. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_role_custom_permission.html.markdown) |
| `aws_quicksight_role_membership` | ✅ | Terraform resource for managing an AWS QuickSight Role Membership. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_role_membership.html.markdown) |
| `aws_quicksight_template` | ✅ | Resource for managing a QuickSight Template. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_template.html.markdown) |
| `aws_quicksight_template_alias` | ✅ | Terraform resource for managing an AWS QuickSight Template Alias. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_template_alias.html.markdown) |
| `aws_quicksight_theme` | ✅ | Resource for managing a QuickSight Theme. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_theme.html.markdown) |
| `aws_quicksight_user` | ✅ | Resource for managing QuickSight User | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_user.html.markdown) |
| `aws_quicksight_user_custom_permission` | ✅ | Manages the custom permissions profile for a user. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_user_custom_permission.html.markdown) |
| `aws_quicksight_vpc_connection` | ✅ | Terraform resource for managing an AWS QuickSight VPC Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/quicksight_vpc_connection.html.markdown) |

---

### Glue

**产品代码**: `glue`
**产品线分类**: 计算平台和AI
**资源数**: 20

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_glue_catalog_database` | ✅ | Provides a Glue Catalog Database Resource. You can refer to the [Glue Develop... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_catalog_database.html.markdown) |
| `aws_glue_catalog_table` | ✅ | Provides a Glue Catalog Table Resource. You can refer to the [Glue Developer ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_catalog_table.html.markdown) |
| `aws_glue_catalog_table_optimizer` | ✅ | Terraform resource for managing an AWS Glue Catalog Table Optimizer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_catalog_table_optimizer.html.markdown) |
| `aws_glue_classifier` | ✅ | Provides a Glue Classifier resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_classifier.html.markdown) |
| `aws_glue_connection` | ✅ | Provides a Glue Connection resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_connection.html.markdown) |
| `aws_glue_crawler` | ✅ | Manages a Glue Crawler. More information can be found in the [AWS Glue Develo... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_crawler.html.markdown) |
| `aws_glue_data_catalog_encryption_settings` | ✅ | Provides a Glue Data Catalog Encryption Settings resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_data_catalog_encryption_settings.html.markdown) |
| `aws_glue_data_quality_ruleset` | ✅ | Provides a Glue Data Quality Ruleset Resource. You can refer to the [Glue Dev... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_data_quality_ruleset.html.markdown) |
| `aws_glue_dev_endpoint` | ✅ | Provides a Glue Development Endpoint resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_dev_endpoint.html.markdown) |
| `aws_glue_job` | ✅ | Provides a Glue Job resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_job.html.markdown) |
| `aws_glue_ml_transform` | ✅ | Provides a Glue ML Transform resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_ml_transform.html.markdown) |
| `aws_glue_partition` | ✅ | Provides a Glue Partition Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_partition.html.markdown) |
| `aws_glue_partition_index` | ✅ | ```terraform | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_partition_index.html.markdown) |
| `aws_glue_registry` | ✅ | Provides a Glue Registry resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_registry.html.markdown) |
| `aws_glue_resource_policy` | ✅ | Provides a Glue resource policy. Only one can exist per region. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_resource_policy.html.markdown) |
| `aws_glue_schema` | ✅ | Provides a Glue Schema resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_schema.html.markdown) |
| `aws_glue_security_configuration` | ✅ | Manages a Glue Security Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_security_configuration.html.markdown) |
| `aws_glue_trigger` | ✅ | Manages a Glue Trigger resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_trigger.html.markdown) |
| `aws_glue_user_defined_function` | ✅ | Provides a Glue User Defined Function Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_user_defined_function.html.markdown) |
| `aws_glue_workflow` | ✅ | Provides a Glue Workflow resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/glue_workflow.html.markdown) |

---

### Bedrock Agentcore

**产品代码**: `bedrock_agentcore`
**产品线分类**: 计算平台和AI
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_bedrockagentcore_agent_runtime` | ✅ | Manages an AWS Bedrock AgentCore Agent Runtime. Agent Runtime provides a cont... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_agent_runtime.html.markdown) |
| `aws_bedrockagentcore_agent_runtime_endpoint` | ✅ | Manages an AWS Bedrock AgentCore Agent Runtime Endpoint. Agent Runtime Endpoi... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_agent_runtime_endpoint.html.markdown) |
| `aws_bedrockagentcore_api_key_credential_provider` | ✅ | Manages an AWS Bedrock AgentCore API Key Credential Provider. API Key credent... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_api_key_credential_provider.html.markdown) |
| `aws_bedrockagentcore_browser` | ✅ | Manages an AWS Bedrock AgentCore Browser. Browser provides AI agents with web... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_browser.html.markdown) |
| `aws_bedrockagentcore_code_interpreter` | ✅ | Manages an AWS Bedrock AgentCore Code Interpreter. Code Interpreter provides ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_code_interpreter.html.markdown) |
| `aws_bedrockagentcore_gateway` | ✅ | Manages an AWS Bedrock AgentCore Gateway. With Gateway, developers can conver... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_gateway.html.markdown) |
| `aws_bedrockagentcore_gateway_target` | ✅ | Manages an AWS Bedrock AgentCore Gateway Target. Gateway targets define the e... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_gateway_target.html.markdown) |
| `aws_bedrockagentcore_memory` | ✅ | Manages an AWS Bedrock AgentCore Memory. Memory provides persistent storage f... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_memory.html.markdown) |
| `aws_bedrockagentcore_memory_strategy` | ✅ | Manages an AWS Bedrock AgentCore Memory Strategy. Memory strategies define ho... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_memory_strategy.html.markdown) |
| `aws_bedrockagentcore_oauth2_credential_provider` | ✅ | Manages an AWS Bedrock AgentCore OAuth2 Credential Provider. OAuth2 credentia... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_oauth2_credential_provider.html.markdown) |
| `aws_bedrockagentcore_token_vault_cmk` | ✅ | Manages the AWS KMS customer master key (CMK) for a token vault. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_token_vault_cmk.html.markdown) |
| `aws_bedrockagentcore_workload_identity` | ✅ | Manages an AWS Bedrock AgentCore Workload Identity. Workload Identity provide... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagentcore_workload_identity.html.markdown) |

---

### Datazone

**产品代码**: `datazone`
**产品线分类**: 计算平台和AI
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_datazone_asset_type` | ✅ | Terraform resource for managing an AWS DataZone Asset Type. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_asset_type.html.markdown) |
| `aws_datazone_domain` | ✅ | Terraform resource for managing an AWS DataZone Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_domain.html.markdown) |
| `aws_datazone_environment` | ✅ | Terraform resource for managing an AWS DataZone Environment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_environment.html.markdown) |
| `aws_datazone_environment_blueprint_configuration` | ✅ | Terraform resource for managing an AWS DataZone Environment Blueprint Configu... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_environment_blueprint_configuration.html.markdown) |
| `aws_datazone_environment_profile` | ✅ | Terraform resource for managing an AWS DataZone Environment Profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_environment_profile.html.markdown) |
| `aws_datazone_form_type` | ✅ | Terraform resource for managing an AWS DataZone Form Type. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_form_type.html.markdown) |
| `aws_datazone_glossary` | ✅ | Terraform resource for managing an AWS DataZone Glossary. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_glossary.html.markdown) |
| `aws_datazone_glossary_term` | ✅ | Terraform resource for managing an AWS DataZone Glossary Term. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_glossary_term.html.markdown) |
| `aws_datazone_project` | ✅ | Terraform resource for managing an AWS DataZone Project. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_project.html.markdown) |
| `aws_datazone_user_profile` | ✅ | Terraform resource for managing an AWS DataZone User Profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datazone_user_profile.html.markdown) |

---

### Lake Formation

**产品代码**: `lake_formation`
**产品线分类**: 计算平台和AI
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_lakeformation_data_cells_filter` | ✅ | Terraform resource for managing an AWS Lake Formation Data Cells Filter. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_data_cells_filter.html.markdown) |
| `aws_lakeformation_data_lake_settings` | ✅ | Manages Lake Formation principals designated as data lake administrators and ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_data_lake_settings.html.markdown) |
| `aws_lakeformation_identity_center_configuration` | ✅ | Manages an AWS Lake Formation Identity Center Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_identity_center_configuration.html.markdown) |
| `aws_lakeformation_lf_tag` | ✅ | Creates an LF-Tag with the specified name and values. Each key must have at l... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_lf_tag.html.markdown) |
| `aws_lakeformation_lf_tag_expression` | ✅ | Terraform resource for managing an AWS Lake Formation LF Tag Expression. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_lf_tag_expression.html.markdown) |
| `aws_lakeformation_opt_in` | ✅ | Terraform resource for managing an AWS Lake Formation Opt In. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_opt_in.html.markdown) |
| `aws_lakeformation_permissions` | ✅ | Grants permissions to the principal to access metadata in the Data Catalog an... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_permissions.html.markdown) |
| `aws_lakeformation_resource` | ✅ | Registers a Lake Formation resource (e.g., S3 bucket) as managed by the Data ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_resource.html.markdown) |
| `aws_lakeformation_resource_lf_tag` | ✅ | Terraform resource for managing an AWS Lake Formation Resource LF Tag. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_resource_lf_tag.html.markdown) |
| `aws_lakeformation_resource_lf_tags` | ✅ | Manages an attachment between one or more existing LF-tags and an existing La... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lakeformation_resource_lf_tags.html.markdown) |

---

### Opensearch

**产品代码**: `opensearch`
**产品线分类**: 计算平台和AI
**资源数**: 10

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_opensearch_application` | ✅ | Provides an AWS OpenSearch Application resource. OpenSearch Applications prov... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_application.html.markdown) |
| `aws_opensearch_authorize_vpc_endpoint_access` | ✅ | Terraform resource for managing an AWS OpenSearch Authorize Vpc Endpoint Access. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_authorize_vpc_endpoint_access.html.markdown) |
| `aws_opensearch_domain` | ✅ | Manages an Amazon OpenSearch Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_domain.html.markdown) |
| `aws_opensearch_domain_policy` | ✅ | Allows setting policy to an OpenSearch domain while referencing domain attrib... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_domain_policy.html.markdown) |
| `aws_opensearch_domain_saml_options` | ✅ | Manages SAML authentication options for an AWS OpenSearch Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_domain_saml_options.html.markdown) |
| `aws_opensearch_inbound_connection_accepter` | ✅ | Manages an [AWS Opensearch Inbound Connection Accepter](https://docs.aws.amaz... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_inbound_connection_accepter.html.markdown) |
| `aws_opensearch_outbound_connection` | ✅ | Manages an AWS Opensearch Outbound Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_outbound_connection.html.markdown) |
| `aws_opensearch_package` | ✅ | Manages an AWS Opensearch Package. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_package.html.markdown) |
| `aws_opensearch_package_association` | ✅ | Manages an AWS Opensearch Package Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_package_association.html.markdown) |
| `aws_opensearch_vpc_endpoint` | ✅ | Manages an [AWS Opensearch VPC Endpoint](https://docs.aws.amazon.com/opensear... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/opensearch_vpc_endpoint.html.markdown) |

---

### Bedrock Agents

**产品代码**: `bedrock_agents`
**产品线分类**: 计算平台和AI
**资源数**: 9

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_bedrockagent_agent` | ✅ | Terraform resource for managing an AWS Agents for Amazon Bedrock Agent. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_agent.html.markdown) |
| `aws_bedrockagent_agent_action_group` | ✅ | Terraform resource for managing an AWS Agents for Amazon Bedrock Agent Action... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_agent_action_group.html.markdown) |
| `aws_bedrockagent_agent_alias` | ✅ | Terraform resource for managing an AWS Agents for Amazon Bedrock Agent Alias. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_agent_alias.html.markdown) |
| `aws_bedrockagent_agent_collaborator` | ✅ | Terraform resource for managing an AWS Bedrock Agents Agent Collaborator. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_agent_collaborator.html.markdown) |
| `aws_bedrockagent_agent_knowledge_base_association` | ✅ | Terraform resource for managing an AWS Agents for Amazon Bedrock Agent Knowle... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_agent_knowledge_base_association.html.markdown) |
| `aws_bedrockagent_data_source` | ✅ | Terraform resource for managing an AWS Agents for Amazon Bedrock Data Source. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_data_source.html.markdown) |
| `aws_bedrockagent_flow` | ✅ | Terraform resource for managing an AWS Bedrock Agents Flow. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_flow.html.markdown) |
| `aws_bedrockagent_knowledge_base` | ✅ | Terraform resource for managing an AWS Agents for Amazon Bedrock Knowledge Base. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_knowledge_base.html.markdown) |
| `aws_bedrockagent_prompt` | ✅ | Terraform resource for managing an AWS Bedrock Agents Prompt. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrockagent_prompt.html.markdown) |

---

### Emr

**产品代码**: `emr`
**产品线分类**: 计算平台和AI
**资源数**: 8

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_emr_block_public_access_configuration` | ✅ | Terraform resource for managing an AWS EMR block public access configuration.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_block_public_access_configuration.html.markdown) |
| `aws_emr_cluster` | ✅ | Provides an Elastic MapReduce Cluster, a web service that makes it easy to pr... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_cluster.html.markdown) |
| `aws_emr_instance_fleet` | ✅ | Provides an Elastic MapReduce Cluster Instance Fleet configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_instance_fleet.html.markdown) |
| `aws_emr_instance_group` | ✅ | Provides an Elastic MapReduce Cluster Instance Group configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_instance_group.html.markdown) |
| `aws_emr_managed_scaling_policy` | ✅ | Provides a Managed Scaling policy for EMR Cluster. With Amazon EMR versions 5... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_managed_scaling_policy.html.markdown) |
| `aws_emr_security_configuration` | ✅ | Provides a resource to manage AWS EMR Security Configurations | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_security_configuration.html.markdown) |
| `aws_emr_studio` | ✅ | Provides an Elastic MapReduce Studio. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_studio.html.markdown) |
| `aws_emr_studio_session_mapping` | ✅ | Provides an Elastic MapReduce Studio Session Mapping. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/emr_studio_session_mapping.html.markdown) |

---

### App Mesh

**产品代码**: `app_mesh`
**产品线分类**: 计算平台和AI
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appmesh_gateway_route` | ✅ | Provides an AWS App Mesh gateway route resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appmesh_gateway_route.html.markdown) |
| `aws_appmesh_mesh` | ✅ | Provides an AWS App Mesh service mesh resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appmesh_mesh.html.markdown) |
| `aws_appmesh_route` | ✅ | Provides an AWS App Mesh route resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appmesh_route.html.markdown) |
| `aws_appmesh_virtual_gateway` | ✅ | Provides an AWS App Mesh virtual gateway resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appmesh_virtual_gateway.html.markdown) |
| `aws_appmesh_virtual_node` | ✅ | Provides an AWS App Mesh virtual node resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appmesh_virtual_node.html.markdown) |
| `aws_appmesh_virtual_router` | ✅ | Provides an AWS App Mesh virtual router resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appmesh_virtual_router.html.markdown) |
| `aws_appmesh_virtual_service` | ✅ | Provides an AWS App Mesh virtual service resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appmesh_virtual_service.html.markdown) |

---

### Athena

**产品代码**: `athena`
**产品线分类**: 计算平台和AI
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_athena_capacity_reservation` | ✅ | Terraform resource for managing an AWS Athena Capacity Reservation. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/athena_capacity_reservation.html.markdown) |
| `aws_athena_data_catalog` | ✅ | Provides an Athena data catalog. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/athena_data_catalog.html.markdown) |
| `aws_athena_database` | ✅ | Provides an Athena database. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/athena_database.html.markdown) |
| `aws_athena_named_query` | ✅ | Provides an Athena Named Query resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/athena_named_query.html.markdown) |
| `aws_athena_prepared_statement` | ✅ | Terraform resource for managing an Athena Prepared Statement. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/athena_prepared_statement.html.markdown) |
| `aws_athena_workgroup` | ✅ | Provides an Athena Workgroup. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/athena_workgroup.html.markdown) |

---

### Bedrock

**产品代码**: `bedrock`
**产品线分类**: 计算平台和AI
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_bedrock_custom_model` | ✅ | Manages an Amazon Bedrock custom model. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrock_custom_model.html.markdown) |
| `aws_bedrock_guardrail` | ✅ | Terraform resource for managing an Amazon Bedrock Guardrail. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrock_guardrail.html.markdown) |
| `aws_bedrock_guardrail_version` | ✅ | Terraform resource for managing an AWS Bedrock Guardrail Version. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrock_guardrail_version.html.markdown) |
| `aws_bedrock_inference_profile` | ✅ | Terraform resource for managing an AWS Bedrock Inference Profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrock_inference_profile.html.markdown) |
| `aws_bedrock_model_invocation_logging_configuration` | ✅ | Manages Bedrock model invocation logging configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrock_model_invocation_logging_configuration.html.markdown) |
| `aws_bedrock_provisioned_model_throughput` | ✅ | Manages [Provisioned Throughput](https://docs.aws.amazon.com/bedrock/latest/u... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bedrock_provisioned_model_throughput.html.markdown) |

---

### Kendra

**产品代码**: `kendra`
**产品线分类**: 计算平台和AI
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_kendra_data_source` | ✅ | Terraform resource for managing an AWS Kendra Data Source. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kendra_data_source.html.markdown) |
| `aws_kendra_experience` | ✅ | Terraform resource for managing an AWS Kendra Experience. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kendra_experience.html.markdown) |
| `aws_kendra_faq` | ✅ | Terraform resource for managing an AWS Kendra FAQ. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kendra_faq.html.markdown) |
| `aws_kendra_index` | ✅ | Provides an Amazon Kendra Index resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kendra_index.html.markdown) |
| `aws_kendra_query_suggestions_block_list` | ✅ | Use the `aws_kendra_index_block_list` resource to manage an AWS Kendra block ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kendra_query_suggestions_block_list.html.markdown) |
| `aws_kendra_thesaurus` | ✅ | Terraform resource for managing an AWS Kendra Thesaurus. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kendra_thesaurus.html.markdown) |

---

### Lex V2 Models

**产品代码**: `lex_v2_models`
**产品线分类**: 计算平台和AI
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_lexv2models_bot` | ✅ | Terraform resource for managing an AWS Lex V2 Models Bot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lexv2models_bot.html.markdown) |
| `aws_lexv2models_bot_locale` | ✅ | Terraform resource for managing an AWS Lex V2 Models Bot Locale. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lexv2models_bot_locale.html.markdown) |
| `aws_lexv2models_bot_version` | ✅ | Terraform resource for managing an AWS Lex V2 Models Bot Version. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lexv2models_bot_version.html.markdown) |
| `aws_lexv2models_intent` | ✅ | Terraform resource for managing an AWS Lex V2 Models Intent. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lexv2models_intent.html.markdown) |
| `aws_lexv2models_slot` | ✅ | Terraform resource for managing an AWS Lex V2 Models Slot. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lexv2models_slot.html.markdown) |
| `aws_lexv2models_slot_type` | ✅ | Terraform resource for managing an AWS Lex V2 Models Slot Type. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lexv2models_slot_type.html.markdown) |

---

### Data Exchange

**产品代码**: `data_exchange`
**产品线分类**: 计算平台和AI
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_dataexchange_data_set` | ✅ | Provides a resource to manage AWS Data Exchange DataSets. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dataexchange_data_set.html.markdown) |
| `aws_dataexchange_event_action` | ✅ | Terraform resource for managing an AWS Data Exchange Event Action. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dataexchange_event_action.html.markdown) |
| `aws_dataexchange_revision` | ✅ | Provides a resource to manage AWS Data Exchange Revisions. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dataexchange_revision.html.markdown) |
| `aws_dataexchange_revision_assets` | ✅ | Terraform resource for managing AWS Data Exchange Revision Assets. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dataexchange_revision_assets.html.markdown) |

---

### Elasticsearch

**产品代码**: `elasticsearch`
**产品线分类**: 计算平台和AI
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_elasticsearch_domain` | ✅ | Manages an AWS Elasticsearch Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticsearch_domain.html.markdown) |
| `aws_elasticsearch_domain_policy` | ✅ | Allows setting policy to an Elasticsearch domain while referencing domain att... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticsearch_domain_policy.html.markdown) |
| `aws_elasticsearch_domain_saml_options` | ✅ | Manages SAML authentication options for an AWS Elasticsearch Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticsearch_domain_saml_options.html.markdown) |
| `aws_elasticsearch_vpc_endpoint` | ✅ | Manages an [AWS Elasticsearch VPC Endpoint](https://docs.aws.amazon.com/elast... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/elasticsearch_vpc_endpoint.html.markdown) |

---

### Lex Model Building

**产品代码**: `lex_model_building`
**产品线分类**: 计算平台和AI
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_lex_bot` | ✅ | Provides an Amazon Lex Bot resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lex_bot.html.markdown) |
| `aws_lex_bot_alias` | ✅ | Provides an Amazon Lex Bot Alias resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lex_bot_alias.html.markdown) |
| `aws_lex_intent` | ✅ | Provides an Amazon Lex Intent resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lex_intent.html.markdown) |
| `aws_lex_slot_type` | ✅ | Provides an Amazon Lex Slot Type resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lex_slot_type.html.markdown) |

---

### Transcribe

**产品代码**: `transcribe`
**产品线分类**: 计算平台和AI
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_transcribe_language_model` | ✅ | Terraform resource for managing an AWS Transcribe LanguageModel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transcribe_language_model.html.markdown) |
| `aws_transcribe_medical_vocabulary` | ✅ | Terraform resource for managing an AWS Transcribe MedicalVocabulary. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transcribe_medical_vocabulary.html.markdown) |
| `aws_transcribe_vocabulary` | ✅ | Terraform resource for managing an AWS Transcribe Vocabulary. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transcribe_vocabulary.html.markdown) |
| `aws_transcribe_vocabulary_filter` | ✅ | Terraform resource for managing an AWS Transcribe VocabularyFilter. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/transcribe_vocabulary_filter.html.markdown) |

---

### Kinesis

**产品代码**: `kinesis`
**产品线分类**: 计算平台和AI
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_kinesis_resource_policy` | ✅ | Provides a resource to manage an Amazon Kinesis Streams resource policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesis_resource_policy.html.markdown) |
| `aws_kinesis_stream` | ✅ | Provides a Kinesis Stream resource. Amazon Kinesis is a managed service that | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesis_stream.html.markdown) |
| `aws_kinesis_stream_consumer` | ✅ | Provides a resource to manage a Kinesis Stream Consumer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesis_stream_consumer.html.markdown) |

---

### Rekognition

**产品代码**: `rekognition`
**产品线分类**: 计算平台和AI
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_rekognition_collection` | ✅ | Terraform resource for managing an AWS Rekognition Collection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rekognition_collection.html.markdown) |
| `aws_rekognition_project` | ✅ | Terraform resource for managing an AWS Rekognition Project. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rekognition_project.html.markdown) |
| `aws_rekognition_stream_processor` | ✅ | Terraform resource for managing an AWS Rekognition Stream Processor. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rekognition_stream_processor.html.markdown) |

---

### Cloudsearch

**产品代码**: `cloudsearch`
**产品线分类**: 计算平台和AI
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudsearch_domain` | ✅ | Provides an CloudSearch domain resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudsearch_domain.html.markdown) |
| `aws_cloudsearch_domain_service_access_policy` | ✅ | Provides an CloudSearch domain service access policy resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudsearch_domain_service_access_policy.html.markdown) |

---

### Comprehend

**产品代码**: `comprehend`
**产品线分类**: 计算平台和AI
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_comprehend_document_classifier` | ✅ | Terraform resource for managing an AWS Comprehend Document Classifier. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/comprehend_document_classifier.html.markdown) |
| `aws_comprehend_entity_recognizer` | ✅ | Terraform resource for managing an AWS Comprehend Entity Recognizer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/comprehend_entity_recognizer.html.markdown) |

---

### Connect Customer Profiles

**产品代码**: `connect_customer_profiles`
**产品线分类**: 计算平台和AI
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_customerprofiles_domain` | ✅ | Terraform resource for managing an Amazon Customer Profiles Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/customerprofiles_domain.html.markdown) |
| `aws_customerprofiles_profile` | ✅ | Terraform resource for managing an Amazon Customer Profiles Profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/customerprofiles_profile.html.markdown) |

---

### Data Pipeline

**产品代码**: `data_pipeline`
**产品线分类**: 计算平台和AI
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_datapipeline_pipeline` | ✅ | Provides a DataPipeline Pipeline resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datapipeline_pipeline.html.markdown) |
| `aws_datapipeline_pipeline_definition` | ✅ | Provides a DataPipeline Pipeline Definition resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/datapipeline_pipeline_definition.html.markdown) |

---

### Roles Anywhere

**产品代码**: `roles_anywhere`
**产品线分类**: 计算平台和AI
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_rolesanywhere_profile` | ✅ | Terraform resource for managing a Roles Anywhere Profile. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rolesanywhere_profile.html.markdown) |
| `aws_rolesanywhere_trust_anchor` | ✅ | Terraform resource for managing a Roles Anywhere Trust Anchor. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/rolesanywhere_trust_anchor.html.markdown) |

---

### Chime Sdk Media Pipelines

**产品代码**: `chime_sdk_media_pipelines`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_chimesdkmediapipelines_media_insights_pipeline_configuration` | ✅ | Terraform resource for managing an AWS Chime SDK Media Pipelines Media Insigh... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chimesdkmediapipelines_media_insights_pipeline_configuration.html.markdown) |

---

### Kinesis Firehose

**产品代码**: `kinesis_firehose`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_kinesis_firehose_delivery_stream` | ✅ | Provides a Kinesis Firehose Delivery Stream resource. Amazon Kinesis Firehose... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/kinesis_firehose_delivery_stream.html.markdown) |

---

### Resilience Hub

**产品代码**: `resilience_hub`
**产品线分类**: 计算平台和AI
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_resiliencehub_resiliency_policy` | ✅ | Terraform resource for managing an AWS Resilience Hub Resiliency Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/resiliencehub_resiliency_policy.html.markdown) |

---

## 其它 (43 个产品)

### Lightsail

**产品代码**: `lightsail`
**产品线分类**: 其它
**资源数**: 23

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_lightsail_bucket` | ✅ | Manages a Lightsail bucket. Use this resource to create and manage object sto... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_bucket.html.markdown) |
| `aws_lightsail_bucket_access_key` | ✅ | Manages a Lightsail bucket access key. Use this resource to create credential... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_bucket_access_key.html.markdown) |
| `aws_lightsail_bucket_resource_access` | ✅ | Manages a Lightsail bucket resource access. Use this resource to grant a Ligh... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_bucket_resource_access.html.markdown) |
| `aws_lightsail_certificate` | ✅ | Manages a Lightsail certificate. Use this resource to create and manage SSL/T... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_certificate.html.markdown) |
| `aws_lightsail_container_service` | ✅ | Manages a Lightsail container service. Use this resource to create and manage... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_container_service.html.markdown) |
| `aws_lightsail_container_service_deployment_version` | ✅ | Manages a Lightsail container service deployment version. Use this resource t... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_container_service_deployment_version.html.markdown) |
| `aws_lightsail_database` | ✅ | Manages a Lightsail database. Use this resource to create and manage fully ma... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_database.html.markdown) |
| `aws_lightsail_disk` | ✅ | Manages a Lightsail disk. Use this resource to create additional block storag... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_disk.html.markdown) |
| `aws_lightsail_disk_attachment` | ✅ | Manages a Lightsail disk attachment. Use this resource to attach additional s... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_disk_attachment.html.markdown) |
| `aws_lightsail_distribution` | ✅ | Manages a Lightsail content delivery network (CDN) distribution. Use this res... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_distribution.html.markdown) |
| `aws_lightsail_domain` | ✅ | Manages a Lightsail domain for DNS management. Use this resource to manage DN... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_domain.html.markdown) |
| `aws_lightsail_domain_entry` | ✅ | Manages a Lightsail domain entry (DNS record). Use this resource to define ho... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_domain_entry.html.markdown) |
| `aws_lightsail_instance` | ✅ | Manages a Lightsail Instance. Use this resource to create easy virtual privat... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_instance.html.markdown) |
| `aws_lightsail_instance_public_ports` | ✅ | Manages public ports for a Lightsail instance. Use this resource to open port... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_instance_public_ports.html.markdown) |
| `aws_lightsail_key_pair` | ✅ | Manages a Lightsail Key Pair for use with Lightsail Instances. Use this resou... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_key_pair.html.markdown) |
| `aws_lightsail_lb` | ✅ | Manages a Lightsail load balancer resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_lb.html.markdown) |
| `aws_lightsail_lb_attachment` | ✅ | Manages a Lightsail Load Balancer Attachment. Use this resource to attach Lig... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_lb_attachment.html.markdown) |
| `aws_lightsail_lb_certificate` | ✅ | Manages a Lightsail Load Balancer Certificate. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_lb_certificate.html.markdown) |
| `aws_lightsail_lb_certificate_attachment` | ✅ | Manages a Lightsail Load Balancer Certificate attachment to a Lightsail Load ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_lb_certificate_attachment.html.markdown) |
| `aws_lightsail_lb_https_redirection_policy` | ✅ | Manages HTTPS redirection for a Lightsail Load Balancer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_lb_https_redirection_policy.html.markdown) |
| `aws_lightsail_lb_stickiness_policy` | ✅ | Manages session stickiness for a Lightsail Load Balancer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_lb_stickiness_policy.html.markdown) |
| `aws_lightsail_static_ip` | ✅ | Manages a static IP address. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_static_ip.html.markdown) |
| `aws_lightsail_static_ip_attachment` | ✅ | Manages a static IP address attachment - relationship between a Lightsail sta... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/lightsail_static_ip_attachment.html.markdown) |

---

### Iot Core

**产品代码**: `iot_core`
**产品线分类**: 其它
**资源数**: 19

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_iot_authorizer` | ✅ | Creates and manages an AWS IoT Authorizer. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_authorizer.html.markdown) |
| `aws_iot_billing_group` | ✅ | Manages an AWS IoT Billing Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_billing_group.html.markdown) |
| `aws_iot_ca_certificate` | ✅ | Creates and manages an AWS IoT CA Certificate. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_ca_certificate.html.markdown) |
| `aws_iot_certificate` | ✅ | Creates and manages an AWS IoT certificate. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_certificate.html.markdown) |
| `aws_iot_domain_configuration` | ✅ | Creates and manages an AWS IoT domain configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_domain_configuration.html.markdown) |
| `aws_iot_event_configurations` | ✅ | Manages IoT event configurations. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_event_configurations.html.markdown) |
| `aws_iot_indexing_configuration` | ✅ | Managing [IoT Thing indexing](https://docs.aws.amazon.com/iot/latest/develope... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_indexing_configuration.html.markdown) |
| `aws_iot_logging_options` | ✅ | Provides a resource to manage [default logging options](https://docs.aws.amaz... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_logging_options.html.markdown) |
| `aws_iot_policy` | ✅ | Provides an IoT policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_policy.html.markdown) |
| `aws_iot_policy_attachment` | ✅ | Provides an IoT policy attachment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_policy_attachment.html.markdown) |
| `aws_iot_provisioning_template` | ✅ | Manages an IoT fleet provisioning template. For more info, see the AWS docume... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_provisioning_template.html.markdown) |
| `aws_iot_role_alias` | ✅ | Provides an IoT role alias. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_role_alias.html.markdown) |
| `aws_iot_thing` | ✅ | Creates and manages an AWS IoT Thing. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_thing.html.markdown) |
| `aws_iot_thing_group` | ✅ | Manages an AWS IoT Thing Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_thing_group.html.markdown) |
| `aws_iot_thing_group_membership` | ✅ | Adds an IoT Thing to an IoT Thing Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_thing_group_membership.html.markdown) |
| `aws_iot_thing_principal_attachment` | ✅ | Attaches Principal to AWS IoT Thing. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_thing_principal_attachment.html.markdown) |
| `aws_iot_thing_type` | ✅ | Creates and manages an AWS IoT Thing Type. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_thing_type.html.markdown) |
| `aws_iot_topic_rule` | ✅ | Creates and manages an AWS IoT topic rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_topic_rule.html.markdown) |
| `aws_iot_topic_rule_destination` | ✅ | ```terraform | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/iot_topic_rule_destination.html.markdown) |

---

### Connect

**产品代码**: `connect`
**产品线分类**: 其它
**资源数**: 17

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_connect_bot_association` | ✅ | Allows the specified Amazon Connect instance to access the specified Amazon L... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_bot_association.html.markdown) |
| `aws_connect_contact_flow` | ✅ | Provides an Amazon Connect Contact Flow resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_contact_flow.html.markdown) |
| `aws_connect_contact_flow_module` | ✅ | Provides an Amazon Connect Contact Flow Module resource. For more information... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_contact_flow_module.html.markdown) |
| `aws_connect_hours_of_operation` | ✅ | Provides an Amazon Connect Hours of Operation resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_hours_of_operation.html.markdown) |
| `aws_connect_instance` | ✅ | Provides an Amazon Connect instance resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_instance.html.markdown) |
| `aws_connect_instance_storage_config` | ✅ | Provides an Amazon Connect Instance Storage Config resource. For more informa... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_instance_storage_config.html.markdown) |
| `aws_connect_lambda_function_association` | ✅ | Provides an Amazon Connect Lambda Function Association. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_lambda_function_association.html.markdown) |
| `aws_connect_phone_number` | ✅ | Provides an Amazon Connect Phone Number resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_phone_number.html.markdown) |
| `aws_connect_phone_number_contact_flow_association` | ✅ | Associates a flow with a phone number claimed to an Amazon Connect instance. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_phone_number_contact_flow_association.html.markdown) |
| `aws_connect_queue` | ✅ | Provides an Amazon Connect Queue resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_queue.html.markdown) |
| `aws_connect_quick_connect` | ✅ | Provides an Amazon Connect Quick Connect resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_quick_connect.html.markdown) |
| `aws_connect_routing_profile` | ✅ | Provides an Amazon Connect Routing Profile resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_routing_profile.html.markdown) |
| `aws_connect_security_profile` | ✅ | Provides an Amazon Connect Security Profile resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_security_profile.html.markdown) |
| `aws_connect_user` | ✅ | Provides an Amazon Connect User resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_user.html.markdown) |
| `aws_connect_user_hierarchy_group` | ✅ | Provides an Amazon Connect User Hierarchy Group resource. For more informatio... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_user_hierarchy_group.html.markdown) |
| `aws_connect_user_hierarchy_structure` | ✅ | Provides an Amazon Connect User Hierarchy Structure resource. For more inform... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_user_hierarchy_structure.html.markdown) |
| `aws_connect_vocabulary` | ✅ | Provides an Amazon Connect Vocabulary resource. For more information see | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/connect_vocabulary.html.markdown) |

---

### Appsync

**产品代码**: `appsync`
**产品线分类**: 其它
**资源数**: 12

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appsync_api` | ✅ | Manages an [AWS AppSync Event API](https://docs.aws.amazon.com/appsync/latest... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_api.html.markdown) |
| `aws_appsync_api_cache` | ✅ | Provides an AppSync API Cache. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_api_cache.html.markdown) |
| `aws_appsync_api_key` | ✅ | Provides an AppSync API Key. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_api_key.html.markdown) |
| `aws_appsync_channel_namespace` | ✅ | Manages an [AWS AppSync Channel Namespace](https://docs.aws.amazon.com/appsyn... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_channel_namespace.html.markdown) |
| `aws_appsync_datasource` | ✅ | Provides an AppSync Data Source. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_datasource.html.markdown) |
| `aws_appsync_domain_name` | ✅ | Provides an AppSync Domain Name. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_domain_name.html.markdown) |
| `aws_appsync_domain_name_api_association` | ✅ | Provides an AppSync API Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_domain_name_api_association.html.markdown) |
| `aws_appsync_function` | ✅ | Provides an AppSync Function. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_function.html.markdown) |
| `aws_appsync_graphql_api` | ✅ | Provides an AppSync GraphQL API. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_graphql_api.html.markdown) |
| `aws_appsync_resolver` | ✅ | Provides an AppSync Resolver. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_resolver.html.markdown) |
| `aws_appsync_source_api_association` | ✅ | Terraform resource for managing an AWS AppSync Source API Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_source_api_association.html.markdown) |
| `aws_appsync_type` | ✅ | Provides an AppSync Type. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appsync_type.html.markdown) |

---

### Appstream 2.0

**产品代码**: `appstream_2.0`
**产品线分类**: 其它
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appstream_directory_config` | ✅ | Provides an AppStream Directory Config. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appstream_directory_config.html.markdown) |
| `aws_appstream_fleet` | ✅ | Provides an AppStream fleet. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appstream_fleet.html.markdown) |
| `aws_appstream_fleet_stack_association` | ✅ | Manages an AppStream Fleet Stack association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appstream_fleet_stack_association.html.markdown) |
| `aws_appstream_image_builder` | ✅ | Provides an AppStream image builder. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appstream_image_builder.html.markdown) |
| `aws_appstream_stack` | ✅ | Provides an AppStream stack. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appstream_stack.html.markdown) |
| `aws_appstream_user` | ✅ | Provides an AppStream user. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appstream_user.html.markdown) |
| `aws_appstream_user_stack_association` | ✅ | Manages an AppStream User Stack association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appstream_user_stack_association.html.markdown) |

---

### Chime

**产品代码**: `chime`
**产品线分类**: 其它
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_chime_voice_connector` | ✅ | Enables you to connect your phone system to the telephone network at a substa... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chime_voice_connector.html.markdown) |
| `aws_chime_voice_connector_group` | ✅ | Creates an Amazon Chime Voice Connector group under the administrator's AWS a... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chime_voice_connector_group.html.markdown) |
| `aws_chime_voice_connector_logging` | ✅ | Adds a logging configuration for the specified Amazon Chime Voice Connector. ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chime_voice_connector_logging.html.markdown) |
| `aws_chime_voice_connector_origination` | ✅ | Enable origination settings to control inbound calling to your SIP infrastruc... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chime_voice_connector_origination.html.markdown) |
| `aws_chime_voice_connector_streaming` | ✅ | Adds a streaming configuration for the specified Amazon Chime Voice Connector... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chime_voice_connector_streaming.html.markdown) |
| `aws_chime_voice_connector_termination` | ✅ | Enable Termination settings to control outbound calling from your SIP infrast... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chime_voice_connector_termination.html.markdown) |
| `aws_chime_voice_connector_termination_credentials` | ✅ | Adds termination SIP credentials for the specified Amazon Chime Voice Connector. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chime_voice_connector_termination_credentials.html.markdown) |

---

### Finspace

**产品代码**: `finspace`
**产品线分类**: 其它
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_finspace_kx_cluster` | ✅ | Terraform resource for managing an AWS FinSpace Kx Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/finspace_kx_cluster.html.markdown) |
| `aws_finspace_kx_database` | ✅ | Terraform resource for managing an AWS FinSpace Kx Database. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/finspace_kx_database.html.markdown) |
| `aws_finspace_kx_dataview` | ✅ | Terraform resource for managing an AWS FinSpace Kx Dataview. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/finspace_kx_dataview.html.markdown) |
| `aws_finspace_kx_environment` | ✅ | Terraform resource for managing an AWS FinSpace Kx Environment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/finspace_kx_environment.html.markdown) |
| `aws_finspace_kx_scaling_group` | ✅ | Terraform resource for managing an AWS FinSpace Kx Scaling Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/finspace_kx_scaling_group.html.markdown) |
| `aws_finspace_kx_user` | ✅ | Terraform resource for managing an AWS FinSpace Kx User. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/finspace_kx_user.html.markdown) |
| `aws_finspace_kx_volume` | ✅ | Terraform resource for managing an AWS FinSpace Kx Volume. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/finspace_kx_volume.html.markdown) |

---

### Amp

**产品代码**: `amp`
**产品线分类**: 其它
**资源数**: 7

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_prometheus_alert_manager_definition` | ✅ | Manages an Amazon Managed Service for Prometheus (AMP) Alert Manager Definition | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/prometheus_alert_manager_definition.html.markdown) |
| `aws_prometheus_query_logging_configuration` | ✅ | Manages an Amazon Managed Service for Prometheus (AMP) Query Logging Configur... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/prometheus_query_logging_configuration.html.markdown) |
| `aws_prometheus_resource_policy` | ✅ | Manages an Amazon Managed Service for Prometheus (AMP) Resource Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/prometheus_resource_policy.html.markdown) |
| `aws_prometheus_rule_group_namespace` | ✅ | Manages an Amazon Managed Service for Prometheus (AMP) Rule Group Namespace | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/prometheus_rule_group_namespace.html.markdown) |
| `aws_prometheus_scraper` | ✅ | will delete the current Scraper and create a new one. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/prometheus_scraper.html.markdown) |
| `aws_prometheus_workspace` | ✅ | Manages an Amazon Managed Service for Prometheus (AMP) Workspace. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/prometheus_workspace.html.markdown) |
| `aws_prometheus_workspace_configuration` | ✅ | Manages an AWS Managed Service for Prometheus Workspace Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/prometheus_workspace_configuration.html.markdown) |

---

### Codebuild

**产品代码**: `codebuild`
**产品线分类**: 其它
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codebuild_fleet` | ✅ | Provides a CodeBuild Fleet Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codebuild_fleet.html.markdown) |
| `aws_codebuild_project` | ✅ | Provides a CodeBuild Project resource. See also the [ | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codebuild_project.html.markdown) |
| `aws_codebuild_report_group` | ✅ | Provides a CodeBuild Report Groups Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codebuild_report_group.html.markdown) |
| `aws_codebuild_resource_policy` | ✅ | Provides a CodeBuild Resource Policy Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codebuild_resource_policy.html.markdown) |
| `aws_codebuild_source_credential` | ✅ | Provides a CodeBuild Source Credentials Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codebuild_source_credential.html.markdown) |
| `aws_codebuild_webhook` | ✅ | Manages a CodeBuild webhook, which is an endpoint accepted by the CodeBuild s... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codebuild_webhook.html.markdown) |

---

### Device Farm

**产品代码**: `device_farm`
**产品线分类**: 其它
**资源数**: 6

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_devicefarm_device_pool` | ✅ | Provides a resource to manage AWS Device Farm Device Pools. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devicefarm_device_pool.html.markdown) |
| `aws_devicefarm_instance_profile` | ✅ | Provides a resource to manage AWS Device Farm Instance Profiles. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devicefarm_instance_profile.html.markdown) |
| `aws_devicefarm_network_profile` | ✅ | Provides a resource to manage AWS Device Farm Network Profiles. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devicefarm_network_profile.html.markdown) |
| `aws_devicefarm_project` | ✅ | Provides a resource to manage AWS Device Farm Projects. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devicefarm_project.html.markdown) |
| `aws_devicefarm_test_grid_project` | ✅ | Provides a resource to manage AWS Device Farm Test Grid Projects. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devicefarm_test_grid_project.html.markdown) |
| `aws_devicefarm_upload` | ✅ | Provides a resource to manage AWS Device Farm Uploads. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devicefarm_upload.html.markdown) |

---

### Amplify

**产品代码**: `amplify`
**产品线分类**: 其它
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_amplify_app` | ✅ | Provides an Amplify App resource, a fullstack serverless app hosted on the [A... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/amplify_app.html.markdown) |
| `aws_amplify_backend_environment` | ✅ | Provides an Amplify Backend Environment resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/amplify_backend_environment.html.markdown) |
| `aws_amplify_branch` | ✅ | Provides an Amplify Branch resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/amplify_branch.html.markdown) |
| `aws_amplify_domain_association` | ✅ | Provides an Amplify Domain Association resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/amplify_domain_association.html.markdown) |
| `aws_amplify_webhook` | ✅ | Provides an Amplify Webhook resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/amplify_webhook.html.markdown) |

---

### Appfabric

**产品代码**: `appfabric`
**产品线分类**: 其它
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appfabric_app_authorization` | ✅ | Terraform resource for managing an AWS AppFabric App Authorization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appfabric_app_authorization.html.markdown) |
| `aws_appfabric_app_authorization_connection` | ✅ | Terraform resource for managing an AWS AppFabric App Authorization Connection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appfabric_app_authorization_connection.html.markdown) |
| `aws_appfabric_app_bundle` | ✅ | Terraform resource for managing an AWS AppFabric AppBundle. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appfabric_app_bundle.html.markdown) |
| `aws_appfabric_ingestion` | ✅ | Terraform resource for managing an AWS AppFabric Ingestion. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appfabric_ingestion.html.markdown) |
| `aws_appfabric_ingestion_destination` | ✅ | Terraform resource for managing an AWS AppFabric Ingestion Destination. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appfabric_ingestion_destination.html.markdown) |

---

### Ivs

**产品代码**: `ivs`
**产品线分类**: 其它
**资源数**: 5

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ivs_channel` | ✅ | Terraform resource for managing an AWS IVS (Interactive Video) Channel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ivs_channel.html.markdown) |
| `aws_ivs_playback_key_pair` | ✅ | Terraform resource for managing an AWS IVS (Interactive Video) Playback Key P... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ivs_playback_key_pair.html.markdown) |
| `aws_ivs_recording_configuration` | ✅ | Terraform resource for managing an AWS IVS (Interactive Video) Recording Conf... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ivs_recording_configuration.html.markdown) |
| `aws_ivschat_logging_configuration` | ✅ | Terraform resource for managing an AWS IVS (Interactive Video) Chat Logging C... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ivschat_logging_configuration.html.markdown) |
| `aws_ivschat_room` | ✅ | Terraform resource for managing an AWS IVS (Interactive Video) Chat Room. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ivschat_room.html.markdown) |

---

### Ce

**产品代码**: `ce`
**产品线分类**: 其它
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ce_anomaly_monitor` | ✅ | Provides a CE Anomaly Monitor. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ce_anomaly_monitor.html.markdown) |
| `aws_ce_anomaly_subscription` | ✅ | Provides a CE Anomaly Subscription. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ce_anomaly_subscription.html.markdown) |
| `aws_ce_cost_allocation_tag` | ✅ | Provides a CE Cost Allocation Tag. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ce_cost_allocation_tag.html.markdown) |
| `aws_ce_cost_category` | ✅ | Provides a CE Cost Category. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ce_cost_category.html.markdown) |

---

### Chime Sdk Voice

**产品代码**: `chime_sdk_voice`
**产品线分类**: 其它
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_chimesdkvoice_global_settings` | ✅ | Terraform resource for managing Amazon Chime SDK Voice Global Settings. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chimesdkvoice_global_settings.html.markdown) |
| `aws_chimesdkvoice_sip_media_application` | ✅ | A ChimeSDKVoice SIP Media Application is a managed object that passes values ... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chimesdkvoice_sip_media_application.html.markdown) |
| `aws_chimesdkvoice_sip_rule` | ✅ | A SIP rule associates your SIP media application with a phone number or a Req... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chimesdkvoice_sip_rule.html.markdown) |
| `aws_chimesdkvoice_voice_profile_domain` | ✅ | Terraform resource for managing an AWS Chime SDK Voice Profile Domain. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chimesdkvoice_voice_profile_domain.html.markdown) |

---

### Codeartifact

**产品代码**: `codeartifact`
**产品线分类**: 其它
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codeartifact_domain` | ✅ | Provides a CodeArtifact Domain Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codeartifact_domain.html.markdown) |
| `aws_codeartifact_domain_permissions_policy` | ✅ | Provides a CodeArtifact Domains Permissions Policy Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codeartifact_domain_permissions_policy.html.markdown) |
| `aws_codeartifact_repository` | ✅ | Provides a CodeArtifact Repository Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codeartifact_repository.html.markdown) |
| `aws_codeartifact_repository_permissions_policy` | ✅ | Provides a CodeArtifact Repostory Permissions Policy Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codeartifact_repository_permissions_policy.html.markdown) |

---

### Codecommit

**产品代码**: `codecommit`
**产品线分类**: 其它
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codecommit_approval_rule_template` | ✅ | Provides a CodeCommit Approval Rule Template Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codecommit_approval_rule_template.html.markdown) |
| `aws_codecommit_approval_rule_template_association` | ✅ | Associates a CodeCommit Approval Rule Template with a Repository. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codecommit_approval_rule_template_association.html.markdown) |
| `aws_codecommit_repository` | ✅ | Provides a CodeCommit Repository Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codecommit_repository.html.markdown) |
| `aws_codecommit_trigger` | ✅ | Provides a CodeCommit Trigger Resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codecommit_trigger.html.markdown) |

---

### Devops Guru

**产品代码**: `devops_guru`
**产品线分类**: 其它
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_devopsguru_event_sources_config` | ✅ | Terraform resource for managing an AWS DevOps Guru Event Sources Config. Curr... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devopsguru_event_sources_config.html.markdown) |
| `aws_devopsguru_notification_channel` | ✅ | Terraform resource for managing an AWS DevOps Guru Notification Channel. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devopsguru_notification_channel.html.markdown) |
| `aws_devopsguru_resource_collection` | ✅ | Terraform resource for managing an AWS DevOps Guru Resource Collection. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devopsguru_resource_collection.html.markdown) |
| `aws_devopsguru_service_integration` | ✅ | Terraform resource for managing an AWS DevOps Guru Service Integration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/devopsguru_service_integration.html.markdown) |

---

### X Ray

**产品代码**: `x_ray`
**产品线分类**: 其它
**资源数**: 4

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_xray_encryption_config` | ✅ | Creates and manages an AWS XRay Encryption Config. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/xray_encryption_config.html.markdown) |
| `aws_xray_group` | ✅ | Creates and manages an AWS XRay Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/xray_group.html.markdown) |
| `aws_xray_resource_policy` | ✅ | Terraform resource for managing an AWS X-Ray Resource Policy. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/xray_resource_policy.html.markdown) |
| `aws_xray_sampling_rule` | ✅ | Creates and manages an AWS XRay Sampling Rule. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/xray_sampling_rule.html.markdown) |

---

### Clean Rooms

**产品代码**: `clean_rooms`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cleanrooms_collaboration` | ✅ | Provides a AWS Clean Rooms collaboration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cleanrooms_collaboration.html.markdown) |
| `aws_cleanrooms_configured_table` | ✅ | Provides a AWS Clean Rooms configured table. Configured tables are used to re... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cleanrooms_configured_table.html.markdown) |
| `aws_cleanrooms_membership` | ✅ | Provides a AWS Clean Rooms membership. Memberships are used to join a Clean R... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cleanrooms_membership.html.markdown) |

---

### Codedeploy

**产品代码**: `codedeploy`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codedeploy_app` | ✅ | Provides a CodeDeploy application to be used as a basis for deployments | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codedeploy_app.html.markdown) |
| `aws_codedeploy_deployment_config` | ✅ | Provides a CodeDeploy deployment config for an application | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codedeploy_deployment_config.html.markdown) |
| `aws_codedeploy_deployment_group` | ✅ | Provides a CodeDeploy Deployment Group for a CodeDeploy Application | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codedeploy_deployment_group.html.markdown) |

---

### Codepipeline

**产品代码**: `codepipeline`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codepipeline` | ✅ | Provides a CodePipeline. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codepipeline.html.markdown) |
| `aws_codepipeline_custom_action_type` | ✅ | Provides a CodeDeploy CustomActionType | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codepipeline_custom_action_type.html.markdown) |
| `aws_codepipeline_webhook` | ✅ | Provides a CodePipeline Webhook. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codepipeline_webhook.html.markdown) |

---

### Sso Identity Store

**产品代码**: `sso_identity_store`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_identitystore_group` | ✅ | Terraform resource for managing an AWS IdentityStore Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/identitystore_group.html.markdown) |
| `aws_identitystore_group_membership` | ✅ | Terraform resource for managing an AWS IdentityStore Group Membership. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/identitystore_group_membership.html.markdown) |
| `aws_identitystore_user` | ✅ | This resource manages a User resource within an Identity Store. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/identitystore_user.html.markdown) |

---

### Sfn

**产品代码**: `sfn`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_sfn_activity` | ✅ | Provides a Step Function Activity resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sfn_activity.html.markdown) |
| `aws_sfn_alias` | ✅ | Provides a Step Function State Machine Alias. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sfn_alias.html.markdown) |
| `aws_sfn_state_machine` | ✅ | Provides a Step Function State Machine resource | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/sfn_state_machine.html.markdown) |

---

### Signer

**产品代码**: `signer`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_signer_signing_job` | ✅ | Creates a Signer Signing Job. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/signer_signing_job.html.markdown) |
| `aws_signer_signing_profile` | ✅ | Creates a Signer Signing Profile. A signing profile contains information abou... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/signer_signing_profile.html.markdown) |
| `aws_signer_signing_profile_permission` | ✅ | Creates a Signer Signing Profile Permission. That is, a cross-account permiss... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/signer_signing_profile_permission.html.markdown) |

---

### Workmail

**产品代码**: `workmail`
**产品线分类**: 其它
**资源数**: 3

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_workmail_default_domain` | ✅ | Manages the default mail domain for an AWS WorkMail organization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workmail_default_domain.html.markdown) |
| `aws_workmail_domain` | ✅ | Manages a mail domain registered to an AWS WorkMail organization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workmail_domain.html.markdown) |
| `aws_workmail_organization` | ✅ | Manages an AWS WorkMail Organization. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/workmail_organization.html.markdown) |

---

### Appflow

**产品代码**: `appflow`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_appflow_connector_profile` | ✅ | Provides an AppFlow connector profile resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appflow_connector_profile.html.markdown) |
| `aws_appflow_flow` | ✅ | Provides an AppFlow flow resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/appflow_flow.html.markdown) |

---

### Chatbot

**产品代码**: `chatbot`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_chatbot_slack_channel_configuration` | ✅ | Terraform resource for managing an AWS Chatbot Slack Channel Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chatbot_slack_channel_configuration.html.markdown) |
| `aws_chatbot_teams_channel_configuration` | ✅ | Terraform resource for managing an AWS Chatbot Microsoft Teams Channel Config... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/chatbot_teams_channel_configuration.html.markdown) |

---

### Cloud9

**产品代码**: `cloud9`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloud9_environment_ec2` | ✅ | Provides a Cloud9 EC2 Development Environment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloud9_environment_ec2.html.markdown) |
| `aws_cloud9_environment_membership` | ✅ | Provides an environment member to an AWS Cloud9 development environment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloud9_environment_membership.html.markdown) |

---

### Dsql

**产品代码**: `dsql`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_dsql_cluster` | ✅ | Terraform resource for managing an Amazon Aurora DSQL Cluster. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dsql_cluster.html.markdown) |
| `aws_dsql_cluster_peering` | ✅ | Terraform resource for managing an Amazon Aurora DSQL Cluster Peering. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/dsql_cluster_peering.html.markdown) |

---

### Outposts

**产品代码**: `outposts`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ec2_local_gateway_route` | ✅ | Manages an EC2 Local Gateway Route. More information can be found in the [Out... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_local_gateway_route.html.markdown) |
| `aws_ec2_local_gateway_route_table_vpc_association` | ✅ | Manages an EC2 Local Gateway Route Table VPC Association. More information ca... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_local_gateway_route_table_vpc_association.html.markdown) |

---

### Fis

**产品代码**: `fis`
**产品线分类**: 其它
**资源数**: 2

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_fis_experiment_template` | ✅ | Provides an FIS Experiment Template, which can be used to run an experiment. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fis_experiment_template.html.markdown) |
| `aws_fis_target_account_configuration` | ✅ | Manages an AWS FIS (Fault Injection Simulator) Target Account Configuration. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/fis_target_account_configuration.html.markdown) |

---

### Arc

**产品代码**: `arc`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_arcregionswitch_plan` | ✅ | Terraform resource for managing an Amazon ARC Region Switch plan. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/arcregionswitch_plan.html.markdown) |

---

### Bcm Data Exports

**产品代码**: `bcm_data_exports`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_bcmdataexports_export` | ✅ | Terraform resource for managing an AWS BCM Data Exports Export. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/bcmdataexports_export.html.markdown) |

---

### Cloud Control Api

**产品代码**: `cloud_control_api`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_cloudcontrolapi_resource` | ✅ | Manages a Cloud Control API Resource. The configuration and lifecycle handlin... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/cloudcontrolapi_resource.html.markdown) |

---

### Codeguru Profiler

**产品代码**: `codeguru_profiler`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codeguruprofiler_profiling_group` | ✅ | Terraform resource for managing an AWS CodeGuru Profiler Profiling Group. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codeguruprofiler_profiling_group.html.markdown) |

---

### Codeguru Reviewer

**产品代码**: `codeguru_reviewer`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_codegurureviewer_repository_association` | ✅ | Terraform resource for managing an AWS CodeGuru Reviewer Repository Association. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/codegurureviewer_repository_association.html.markdown) |

---

### Wavelength

**产品代码**: `wavelength`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_ec2_carrier_gateway` | ✅ | Manages an EC2 Carrier Gateway. See the AWS [documentation](https://docs.aws.... | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/ec2_carrier_gateway.html.markdown) |

---

### Invoicing

**产品代码**: `invoicing`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_invoicing_invoice_unit` | ✅ | Manages an AWS Invoice Unit for organizational billing. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/invoicing_invoice_unit.html.markdown) |

---

### Elemental Mediaconvert

**产品代码**: `elemental_mediaconvert`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_media_convert_queue` | ✅ | Provides an AWS Elemental MediaConvert Queue. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/media_convert_queue.html.markdown) |

---

### Mwaa

**产品代码**: `mwaa`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_mwaa_environment` | ✅ | Creates a MWAA Environment resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/mwaa_environment.html.markdown) |

---

### Savings Plans

**产品代码**: `savings_plans`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_savingsplans_savings_plan` | ✅ | Provides an AWS Savings Plan resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/savingsplans_savings_plan.html.markdown) |

---

### Swf

**产品代码**: `swf`
**产品线分类**: 其它
**资源数**: 1

#### 资源 (Resources)

| 资源名 | 状态 | 说明 | 文档 |
|--------|------|------|------|
| `aws_swf_domain` | ✅ | Provides an SWF Domain resource. | [doc](https://github.com/hashicorp/terraform-provider-aws/blob/master/website/docs/r/swf_domain.html.markdown) |

---
