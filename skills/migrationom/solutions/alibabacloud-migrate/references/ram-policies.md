# RAM Permission Requirements for AWS-to-Alibaba Cloud Migration

This document outlines the Resource Access Management (RAM) permissions required for each migration scenario.

---

## 1. Server Migration (AMI Export + ImportImage)

### ECS ImportImage Permissions

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| ecs:ImportImage | ecs:ImportImage | * | Import image from OSS |
| ecs:DescribeImages | ecs:DescribeImages | * | Query image status during import |
| ecs:DeleteImage | ecs:DeleteImage | acs:ecs:*:*:image/* | Delete imported image |
| ecs:RunInstances | ecs:RunInstances | acs:ecs:*:*:instance/* | Create ECS from imported image |
| ecs:StartInstance | ecs:StartInstance | acs:ecs:*:*:instance/* | Start ECS instance |
| ecs:StopInstance | ecs:StopInstance | acs:ecs:*:*:instance/* | Stop ECS instance |
| ecs:DescribeInstances | ecs:DescribeInstances | * | Query instance status |
| ecs:DeleteInstance | ecs:DeleteInstance | acs:ecs:*:*:instance/* | Delete ECS instance |

### OSS Permissions (for Image Import Source)

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| oss:PutObject | oss:PutObject | acs:oss:*:*:<import-bucket>/* | Upload image file to OSS |
| oss:GetObject | oss:GetObject | acs:oss:*:*:<import-bucket>/* | ECS service reads image from OSS |
| oss:GetBucketInfo | oss:GetBucketInfo | acs:oss:*:*:<import-bucket> | Verify bucket exists and region |
| oss:DeleteObject | oss:DeleteObject | acs:oss:*:*:<import-bucket>/* | Clean up image file after import |

> **Note**: The ECS service internally reads the image file from OSS during import. Ensure the RAM user performing `ImportImage` has `oss:GetObject` on the bucket containing the image.

---

## 2. Database Migration (DTS)

### DTS API Permissions

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| CreateMigrationJob | dts:CreateMigrationJob | * | Create DTS migration job |
| ConfigureMigrationJob | dts:ConfigureMigrationJob | acs:dts:*:*:migrationjob/* | Configure migration job settings |
| StartMigrationJob | dts:StartMigrationJob | acs:dts:*:*:migrationjob/* | Start migration job |
| StopMigrationJob | dts:StopMigrationJob | acs:dts:*:*:migrationjob/* | Stop migration job |
| DescribeMigrationJobStatus | dts:DescribeMigrationJobStatus | acs:dts:*:*:migrationjob/* | Query migration job status |
| DescribeMigrationJobs | dts:DescribeMigrationJobs | * | List migration jobs |
| DeleteMigrationJob | dts:DeleteMigrationJob | acs:dts:*:*:migrationjob/* | Delete migration job |
| DescribeDtsJobs | dts:DescribeDtsJobs | * | Query DTS job details |

### RDS Permissions (Destination Database)

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| rds:CreateDBInstance | rds:CreateDBInstance | acs:rds:*:*:dbinstance/* | Create destination RDS instance |
| rds:DescribeDBInstances | rds:DescribeDBInstances | * | Query RDS instances |
| rds:DescribeDBInstanceAttribute | rds:DescribeDBInstanceAttribute | acs:rds:*:*:dbinstance/* | Get instance attributes |
| rds:DeleteDBInstance | rds:DeleteDBInstance | acs:rds:*:*:dbinstance/* | Clean up RDS instance |

---

## 3. Storage Migration (OSS)

### OSS API Permissions

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| oss:PutBucket | oss:PutBucket | acs:oss:*:*:<bucket-name> | Create OSS bucket |
| oss:GetBucketInfo | oss:GetBucketInfo | acs:oss:*:*:<bucket-name> | Get bucket information |
| oss:ListBuckets | oss:ListBuckets | * | List all buckets |
| oss:PutObject | oss:PutObject | acs:oss:*:*:<bucket-name>/* | Upload objects |
| oss:GetObject | oss:GetObject | acs:oss:*:*:<bucket-name>/* | Download objects |
| oss:DeleteObject | oss:DeleteObject | acs:oss:*:*:<bucket-name>/* | Delete objects |
| oss:ListObjects | oss:ListObjects | acs:oss:*:*:<bucket-name> | List bucket objects |
| oss:DeleteBucket | oss:DeleteBucket | acs:oss:*:*:<bucket-name> | Delete bucket |
| oss:AbortMultipartUpload | oss:AbortMultipartUpload | acs:oss:*:*:<bucket-name>/* | Abort multipart upload |

### HCS-MGW (Hybrid Cloud Storage Migration Gateway)

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| hcs-mgw:CreateGateway | hcs-mgw:CreateGateway | * | Create migration gateway |
| hcs-mgw:DescribeGateways | hcs-mgw:DescribeGateways | * | Query gateways |
| hcs-mgw:DeleteGateway | hcs-mgw:DeleteGateway | acs:hcs-mgw:*:*:gateway/* | Delete gateway |

---

## 4. Network Setup (VPC)

### VPC API Permissions

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| vpc:CreateVpc | vpc:CreateVpc | * | Create VPC |
| vpc:DescribeVpcs | vpc:DescribeVpcs | * | Query VPCs |
| vpc:CreateVSwitch | vpc:CreateVSwitch | * | Create VSwitch |
| vpc:DescribeVSwitches | vpc:DescribeVSwitches | * | Query VSwitches |
| vpc:DeleteVpc | vpc:DeleteVpc | acs:vpc:*:*:vpc/* | Delete VPC |
| vpc:DeleteVSwitch | vpc:DeleteVSwitch | acs:vpc:*:*:vswitch/* | Delete VSwitch |
| vpc:AssociateVpcCidrBlock | vpc:AssociateVpcCidrBlock | acs:vpc:*:*:vpc/* | Associate CIDR block |

### Security Group Permissions

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| ecs:CreateSecurityGroup | ecs:CreateSecurityGroup | * | Create security group |
| ecs:DescribeSecurityGroups | ecs:DescribeSecurityGroups | * | Query security groups |
| ecs:AuthorizeSecurityGroup | ecs:AuthorizeSecurityGroup | acs:ecs:*:*:securitygroup/* | Add security group rules |
| ecs:RevokeSecurityGroup | ecs:RevokeSecurityGroup | acs:ecs:*:*:securitygroup/* | Remove security group rules |
| ecs:DeleteSecurityGroup | ecs:DeleteSecurityGroup | acs:ecs:*:*:securitygroup/* | Delete security group |

---

## 5. Serverless Migration (FC)

> **CRITICAL — FC RAM Role Requirement:**
> Any FC function that accesses other Alibaba Cloud services (OSS, SLS, Tablestore, MNS, RDS, etc.) **MUST** have a RAM Role assigned via the `role` parameter on `alicloud_fcv3_function`. Without this role, the function will receive `AccessDenied` errors at runtime — even if the deploying user has full permissions.
>
> ```hcl
> # 1. Create RAM Role trusting FC service
> resource "alicloud_ram_role" "fc_role" {
>   name     = "<project>-fc-role"
>   document = jsonencode({
>     Version   = "1"
>     Statement = [{ Action = "sts:AssumeRole", Effect = "Allow",
>       Principal = { Service = ["fc.aliyuncs.com"] } }]
>   })
> }
>
> # 2. Create a least-privilege custom policy scoped to what the function actually needs.
> #    Adjust actions and resources to match your function's requirements.
> #    Example: OSS read/write on a specific bucket + SLS log write.
> resource "alicloud_ram_policy" "fc_policy" {
>   name        = "<project>-fc-policy"
>   description = "Least-privilege policy for FC function runtime"
>   document    = jsonencode({
>     Version = "1"
>     Statement = [
>       {
>         Effect   = "Allow"
>         Action   = ["oss:PutObject", "oss:GetObject", "oss:ListObjects"]
>         Resource = ["acs:oss:*:*:<target-bucket>/*", "acs:oss:*:*:<target-bucket>"]
>       },
>       {
>         Effect   = "Allow"
>         Action   = ["log:PostLogStoreLogs", "log:GetLogStore"]
>         Resource = ["acs:log:*:*:project/<sls-project>/logstore/<logstore-name>"]
>       }
>     ]
>   })
> }
>
> resource "alicloud_ram_role_policy_attachment" "fc_role_policy" {
>   role_name   = alicloud_ram_role.fc_role.name
>   policy_name = alicloud_ram_policy.fc_policy.name
>   policy_type = "Custom"
> }
>
> # 3. Reference role ARN in function
> resource "alicloud_fcv3_function" "example" {
>   # ...
>   role = alicloud_ram_role.fc_role.arn   # CRITICAL: without this, runtime AccessDenied
> }
> ```
>
> At runtime, FC injects temporary STS credentials into `context.credentials` (Python) / `context.Credentials` (Go). **Always use these** instead of hardcoding AK/SK.

### Function Compute API Permissions

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| fc:CreateFunction | fc:CreateFunction | acs:fc:*:*:functions/* | Create function |
| fc:ListFunctions | fc:ListFunctions | * | List functions |
| fc:CreateTrigger | fc:CreateTrigger | acs:fc:*:*:functions/*/triggers/* | Create trigger |
| fc:ListTriggers | fc:ListTriggers | acs:fc:*:*:functions/* | List triggers |
| fc:GetFunction | fc:GetFunction | acs:fc:*:*:functions/* | Get function details |
| fc:InvokeFunction | fc:InvokeFunction | acs:fc:*:*:functions/* | Invoke function |
| fc:DeleteFunction | fc:DeleteFunction | acs:fc:*:*:functions/* | Delete function |
| fc:UpdateFunction | fc:UpdateFunction | acs:fc:*:*:functions/* | Update function |
| fc:DeleteTrigger | fc:DeleteTrigger | acs:fc:*:*:functions/*/triggers/* | Delete trigger |

---

## 6. DNS Migration

### Alibaba Cloud DNS Permissions

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| alidns:AddDomainRecord | alidns:AddDomainRecord | * | Add DNS record |
| alidns:DescribeDomainRecords | alidns:DescribeDomainRecords | * | Query DNS records |
| alidns:UpdateDomainRecord | alidns:UpdateDomainRecord | * | Update DNS record |
| alidns:DeleteDomainRecord | alidns:DeleteDomainRecord | * | Delete DNS record |
| alidns:DescribeDomains | alidns:DescribeDomains | * | List domains |
| alidns:AddDomain | alidns:AddDomain | * | Add domain |
| alidns:DeleteDomain | alidns:DeleteDomain | * | Delete domain |

### CDN Permissions (if applicable)

| Action | RAM Permission | Resource | Description |
|--------|---------------|----------|-------------|
| cdn:AddCdnDomain | cdn:AddCdnDomain | * | Add CDN domain |
| cdn:DescribeUserDomains | cdn:DescribeUserDomains | * | Query CDN domains |
| cdn:DeleteCdnDomain | cdn:DeleteCdnDomain | * | Delete CDN domain |
| cdn:StartCdnDomain | cdn:StartCdnDomain | * | Start CDN domain |
| cdn:StopCdnDomain | cdn:StopCdnDomain | * | Stop CDN domain |

---

## System Managed Policies (Last Resort Only)

> **⚠️ WARNING — Do NOT use FullAccess policies in production.**
> System `*FullAccess` policies grant unrestricted control over the entire service, far exceeding what migration requires. They violate the principle of least privilege and create serious blast-radius risk if credentials are compromised.
>
> **Use the custom least-privilege policy in the next section instead.**
> Only fall back to managed policies if a specific API call is blocked and you cannot determine the exact action name — and remove them immediately after the operation completes.

<details>
<summary>Managed policy names (reference only — do not attach to production RAM users)</summary>

| Policy Name | Covers | Risk |
|-------------|--------|------|
| AliyunECSFullAccess | ECS | Full control over all instances, images, disks |
| AliyunDTSFullAccess | DTS | Full control over all migration/sync jobs |
| AliyunOSSFullAccess | OSS | Full control over all buckets and objects |
| AliyunVPCFullAccess | VPC | Full control over all network resources |
| AliyunFCFullAccess | FC | Full control over all functions and triggers |
| AliyunDNSFullAccess | DNS | Full control over all domains and records |
| AliyunRDSFullAccess | RDS | Full control over all database instances |
| AliyunCDNFullAccess | CDN | Full control over all CDN domains |
| AliyunIaCServiceFullAccess | IaCService | Full Terraform execution capability |

</details>

### How to Attach a Policy (use with custom policy name)

```bash
# Attach custom policy to RAM user
aliyun ram AttachPolicyToUser \
  --PolicyName MigrationOperatorPolicy \
  --PolicyType Custom \
  --UserName <ram-user-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Custom Least-Privilege Policy

For all environments, use a custom policy with the minimum required permissions. This is the **recommended approach** — do not substitute with `*FullAccess` managed policies.

### Migration Operator Policy (complete)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "ECSMigration",
      "Effect": "Allow",
      "Action": [
        "ecs:ImportImage",
        "ecs:DescribeImages",
        "ecs:DeleteImage",
        "ecs:RunInstances",
        "ecs:StartInstance",
        "ecs:StopInstance",
        "ecs:DescribeInstances",
        "ecs:DeleteInstance",
        "ecs:DescribeDisks",
        "ecs:DescribeInstanceTypes",
        "ecs:CreateSecurityGroup",
        "ecs:DescribeSecurityGroups",
        "ecs:AuthorizeSecurityGroup",
        "ecs:RevokeSecurityGroup",
        "ecs:DeleteSecurityGroup"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VPCNetwork",
      "Effect": "Allow",
      "Action": [
        "vpc:CreateVpc",
        "vpc:DescribeVpcs",
        "vpc:DeleteVpc",
        "vpc:CreateVSwitch",
        "vpc:DescribeVSwitches",
        "vpc:DeleteVSwitch",
        "vpc:AssociateVpcCidrBlock",
        "vpc:CreateNatGateway",
        "vpc:DescribeNatGateways",
        "vpc:DeleteNatGateway",
        "vpc:AllocateEipAddress",
        "vpc:AssociateEipAddress",
        "vpc:UnassociateEipAddress",
        "vpc:ReleaseEipAddress"
      ],
      "Resource": "*"
    },
    {
      "Sid": "OSSStorage",
      "Effect": "Allow",
      "Action": [
        "oss:PutBucket",
        "oss:GetBucketInfo",
        "oss:ListBuckets",
        "oss:PutObject",
        "oss:GetObject",
        "oss:ListObjects",
        "oss:DeleteObject",
        "oss:DeleteBucket",
        "oss:AbortMultipartUpload",
        "oss:ListMultipartUploads",
        "oss:PutBucketLifecycle",
        "oss:GetBucketLifecycle",
        "oss:PutBucketPolicy",
        "oss:GetBucketPolicy"
      ],
      "Resource": "acs:oss:*:*:*"
    },
    {
      "Sid": "RDSDatabase",
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBInstance",
        "rds:DescribeDBInstances",
        "rds:DescribeDBInstanceAttribute",
        "rds:ModifyDBInstanceSpec",
        "rds:DeleteDBInstance",
        "rds:CreateDatabase",
        "rds:DescribeDatabases",
        "rds:CreateAccount",
        "rds:DescribeAccounts",
        "rds:GrantAccountPrivilege",
        "rds:ModifySecurityIps",
        "rds:DescribeDBInstanceIPArrayList"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DTSMigration",
      "Effect": "Allow",
      "Action": [
        "dts:CreateMigrationJob",
        "dts:ConfigureMigrationJob",
        "dts:StartMigrationJob",
        "dts:StopMigrationJob",
        "dts:DescribeMigrationJobStatus",
        "dts:DescribeMigrationJobs",
        "dts:DeleteMigrationJob",
        "dts:DescribeDtsJobs"
      ],
      "Resource": "*"
    },
    {
      "Sid": "FunctionCompute",
      "Effect": "Allow",
      "Action": [
        "fc:CreateFunction",
        "fc:ListFunctions",
        "fc:GetFunction",
        "fc:UpdateFunction",
        "fc:DeleteFunction",
        "fc:InvokeFunction",
        "fc:CreateTrigger",
        "fc:ListTriggers",
        "fc:GetTrigger",
        "fc:UpdateTrigger",
        "fc:DeleteTrigger"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RAMForFCRole",
      "Effect": "Allow",
      "Action": [
        "ram:CreateRole",
        "ram:GetRole",
        "ram:DeleteRole",
        "ram:AttachPolicyToRole",
        "ram:DetachPolicyFromRole",
        "ram:ListPoliciesForRole",
        "ram:CreatePolicy",
        "ram:GetPolicy",
        "ram:DeletePolicy",
        "ram:CreatePolicyVersion",
        "ram:GetPolicyVersion"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DNS",
      "Effect": "Allow",
      "Action": [
        "alidns:AddDomain",
        "alidns:DescribeDomains",
        "alidns:DeleteDomain",
        "alidns:AddDomainRecord",
        "alidns:DescribeDomainRecords",
        "alidns:UpdateDomainRecord",
        "alidns:DeleteDomainRecord"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CDN",
      "Effect": "Allow",
      "Action": [
        "cdn:AddCdnDomain",
        "cdn:DescribeUserDomains",
        "cdn:ModifyCdnDomain",
        "cdn:DeleteCdnDomain",
        "cdn:StartCdnDomain",
        "cdn:StopCdnDomain"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IaCService",
      "Effect": "Allow",
      "Action": [
        "iacservice:ValidateModule",
        "iacservice:ExecuteTerraformPlan",
        "iacservice:ExecuteTerraformApply",
        "iacservice:ExecuteTerraformDestroy",
        "iacservice:GetExecuteState"
      ],
      "Resource": "*"
    }
  ]
}
```

### Create Custom Policy via CLI

```bash
# Create custom policy
aliyun ram CreatePolicy \
  --PolicyName MigrationOperatorPolicy \
  --PolicyType Custom \
  --Description "Least-privilege policy for cloud migration operations" \
  --PolicyDocument '{"Version":"1","Statement":[...]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Security Best Practices

1. **Use RAM Roles for EC2/ ECS**: Instead of storing credentials, use RAM roles attached to ECS instances.

2. **Enable MFA**: Require multi-factor authentication for RAM users with migration permissions.

3. **Rotate Access Keys**: Regularly rotate access keys for RAM users performing migrations.

4. **Use Resource-Level Permissions**: Where possible, scope permissions to specific resources (e.g., specific VPC IDs, bucket names).

5. **Audit with ActionTrail**: Enable ActionTrail to log all API calls for compliance and troubleshooting.

6. **Principle of Least Privilege**: Start with custom least-privilege policies, only add managed policies if necessary.

7. **Separate Environments**: Use different RAM users/roles for development, testing, and production migrations.

---

## IaCService (Terraform Online Runtime)

Required for using `terraform_runtime_online.sh` to provision infrastructure via Terraform.

**Managed Policy**: `AliyunIaCServiceFullAccess`

**Custom Policy (Minimum)**:
```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iacservice:ValidateModule",
        "iacservice:ExecuteTerraformPlan",
        "iacservice:ExecuteTerraformApply",
        "iacservice:ExecuteTerraformDestroy",
        "iacservice:GetExecuteState"
      ],
      "Resource": "*"
    }
  ]
}
```
