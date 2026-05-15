# AWS Service → Alibaba Cloud Mapping Index

This index provides a quick reference for mapping AWS services to Alibaba Cloud equivalents.

## Usage Guide

1. **Identify AWS resource type** from your Terraform configuration
2. **Find the resource** in the tables above
3. **Check migration difficulty**:
   - **Low**: Direct 1:1 mapping with minimal configuration changes
   - **Medium**: Functional equivalent with some configuration adjustments
   - **High**: Significant architectural changes required
4. **Refer to the detailed reference file** for configuration differences, migration considerations, and pricing comparison
5. **Look up Terraform docs** for resource attributes and usage examples by constructing the URL from resource type:
   - AWS: `https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/{resource}` (e.g. `aws_instance` → `.../resources/instance`)
   - Alibaba Cloud: `https://registry.terraform.io/providers/aliyun/alicloud/latest/docs/resources/{resource}` (e.g. `alicloud_vpc` → `.../resources/vpc`)

---

## Networking Services

| AWS Service | Resource Type | Alibaba Cloud Service | Reference File | Migration Difficulty |
|-------------|---------------|----------------------|----------------|---------------------|
| VPC | `aws_vpc` | VPC | `networking.md` | Low |
| Subnet | `aws_subnet` | VSwitch | `networking.md` | Low |
| Security Group | `aws_security_group` | Security Group | `networking.md` | Low |
| Internet Gateway | `aws_internet_gateway` | See IGW + default route pattern | `networking.md` | Medium |
| NAT Gateway | `aws_nat_gateway` | NAT Gateway | `networking.md` | Low |
| ELB Classic | `aws_elb` | SLB Classic | `networking.md` | Low |
| ALB | `aws_lb` (application) | ALB | `networking.md` | Medium |
| NLB | `aws_lb` (network) | NLB | `networking.md` | Medium |
| Route 53 | `aws_route53_zone` | Alibaba Cloud DNS | `networking.md` | Medium |
| CloudFront | `aws_cloudfront_distribution` | CDN (DCDN) | `networking.md` | Medium |
| Direct Connect | `aws_dx_connection` | Express Connect | `networking.md` | High |
| VPN | `aws_vpn_gateway` | VPN Gateway | `networking.md` | Medium |

## Security & Identity Services

| AWS Service | Resource Type | Alibaba Cloud Service | Reference File | Migration Difficulty |
|-------------|---------------|----------------------|----------------|---------------------|
| IAM | `aws_iam_role` | RAM | `security.md` | Medium |
| KMS | `aws_kms_key` | KMS | `security.md` | Low |
| Secrets Manager | `aws_secretsmanager_secret` | KMS Secret | `security.md` | Low |
| WAF | `aws_wafv2_web_acl` | WAF 3.0 | `security.md` | Medium |
| Shield | `aws_shield_protection` | Anti-DDoS Pro/Premium | `security.md` | Medium |
| Network Firewall | `aws_networkfirewall_firewall` | Cloud Firewall | `security.md` | Medium |
| ACM | `aws_acm_certificate` | SSL Certificates Service | `security.md` | Medium |
| CloudHSM | `aws_cloudhsm_v2_cluster` | KMS (HSM) | `security.md` | High |
| Inspector | `aws_inspector2_enabler` | Cloud Security Center (CWPP) | `security.md` | Medium |
| GuardDuty | `aws_guardduty_detector` | Cloud Security Center (CTDR) | `security.md` | Medium |
| Security Hub | `aws_securityhub_account` | Cloud Security Center (CSPM) | `security.md` | Medium |
| Cognito | `aws_cognito_user_pool` | IDaaS (EIAM) | `security.md` | High |
| Bastion / SSM | AWS Systems Manager | Bastionhost | `security.md` | Medium |

---

## Storage Services

| AWS Service | Resource Type | Alibaba Cloud Service | Reference File | Migration Difficulty |
|-------------|---------------|----------------------|----------------|---------------------|
| S3 Bucket | `aws_s3_bucket` | OSS Bucket | `storage.md` | Low |
| S3 Bucket ACL | `aws_s3_bucket_acl` | OSS Bucket ACL | `storage.md` | Low |
| S3 Bucket Versioning | `aws_s3_bucket_versioning` | OSS Bucket Versioning | `storage.md` | Low |
| S3 Bucket Encryption | `aws_s3_bucket_server_side_encryption_configuration` | OSS Server-Side Encryption | `storage.md` | Low |
| S3 Bucket Policy | `aws_s3_bucket_policy` | OSS Bucket Policy | `storage.md` | Medium |

---

## Compute Services

| AWS Service | Resource Type | Alibaba Cloud Service | Reference File | Migration Difficulty |
|-------------|---------------|----------------------|----------------|---------------------||
| EC2 Instances | `aws_instance` | ECS | `compute.md` | Low |
| Launch Template | `aws_launch_template` | Launch Template | `compute.md` | Low |
| Auto Scaling Group | `aws_autoscaling_group` | Scaling Group | `compute.md` | Medium |
| Key Pair | `aws_key_pair` | Key Pair | `compute.md` | Low |

**Note:** For detailed instance type mappings and Terraform examples, see [compute.md](compute.md).

---
