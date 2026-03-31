# Migration Parameter Reference

All parameters are confirmed at the **end of Phase 2** (Migration Plan Generation).

- **Autonomous mode**: Agent selects defaults and presents a single summary block alongside the Phase 2 checkpoint for one-time review. The user can adjust any value before execution begins. Parameters are NOT asked one-by-one.
- **Interactive mode**: Confirm each parameter before writing any Terraform HCL.

| Parameter | Required | Description | Agent Default (Autonomous) |
|-----------|----------|-------------|---------------------------|
| `RegionId` | Yes | Target Alibaba Cloud region | Inferred from source region proximity |
| `VpcCidrBlock` | Yes | VPC CIDR block | `10.0.0.0/16` |
| `VSwitchCidrBlock` | Yes | VSwitch CIDR block | `10.0.1.0/24` |
| `ZoneId` | Yes | Availability zone | First available zone in region |
| `ImageName` | Yes | Name for imported ECS image | `<project>-aws-migrated-<date>` |
| `SystemDiskSize` | Yes | System disk size (GiB, must be ≥ source) | Source disk size + 10 GiB buffer |
| `InstanceType` | No | ECS instance type | Closest match to source EC2 spec |
| `DiskImageFormat` | No | Image format: `VHD` or `VMDK` | `VHD` (best compatibility) |
| `OSSBucketName` | Yes | OSS bucket for image staging | `<project>-image-import-<region>` |
| `S3BucketName` | Conditional | S3 bucket for AMI export | `<project>-ami-export-<account>` |
| `DBInstanceClass` | Conditional | ApsaraDB RDS instance class | Closest match to source RDS spec |
| `BucketName` | Conditional | OSS bucket name (storage migration) | Same as source S3 bucket name |
| `DomainName` | Conditional | Domain name (DNS migration) | Same as source Route53 zone |
