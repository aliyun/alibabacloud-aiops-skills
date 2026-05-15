# AWS Storage Services -> Alibaba Cloud Mapping

## S3 Buckets -> OSS Buckets

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|------------------------|----------------------|-------|
| `aws_s3_bucket` | `alicloud_oss_bucket` | Low | Bucket name, storage class, tags, and force destroy map directly where supported. |
| `aws_s3_bucket_acl` / `aws_s3_bucket.acl` | `alicloud_oss_bucket_acl` | Low | Prefer the standalone ACL resource; do not use deprecated inline `acl` on `alicloud_oss_bucket`. |
| `aws_s3_bucket_versioning` | `alicloud_oss_bucket_versioning` | Low | Map `Enabled` to enabled OSS versioning. |
| `aws_s3_bucket_server_side_encryption_configuration` | `alicloud_oss_bucket_server_side_encryption` | Low | Map AES256/SSE-KMS to OSS server-side encryption settings supported by the provider. |
| `aws_s3_bucket_public_access_block` | OSS bucket ACL/policy controls | Medium | Preserve private access intent; use bucket ACL and bucket policy when needed. |
| `aws_s3_bucket_policy` | `alicloud_oss_bucket_policy` | Medium | IAM policy JSON needs service/action/resource translation. |

## Required Target Properties

When Phase 2 writes `target_resources[]` for S3 buckets, include the feature-specific companion resources so Phase 4 does not infer deprecated inline fields:

| Source Pattern | Target Resource | Required `target_resources[].properties` | Forbidden |
|----------------|-----------------|-------------------------------------------|-----------|
| `aws_s3_bucket` with private ACL | `alicloud_oss_bucket` + `alicloud_oss_bucket_acl` | Bucket name, region, tags; ACL resource with `acl = "private"` and bucket reference | Inline `acl` on `alicloud_oss_bucket` |
| Versioning enabled | `alicloud_oss_bucket_versioning` | Bucket reference and enabled versioning status | Dropping versioning because it is not on the base bucket |
| SSE AES256 or KMS | `alicloud_oss_bucket_server_side_encryption` | Bucket reference plus provider-supported SSE algorithm/KMS settings | Plaintext storage or placeholder encryption values |

## Backend Mapping

AWS S3 Terraform backends map to Alibaba Cloud OSS backends:

| AWS S3 Backend Field | Alibaba OSS Backend Field | Notes |
|----------------------|---------------------------|-------|
| `bucket` | `bucket` | Use the mapped OSS state bucket. |
| `key` | `prefix` | Preserve the state path. |
| `region` | `region` | Use the target Alibaba Cloud region. |
| `dynamodb_table` | No direct backend field | Record as a migration note; OSS backend locking differs. |

Phase 4 must write a real `backend "oss"` block in `versions.tf` when `state_backend.target_type` is `oss`.
