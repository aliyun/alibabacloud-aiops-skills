# RAM Policies Reference

## Required RAM Permissions

The `alibabacloud-ecs-code-deploy` skill requires the following Alibaba Cloud RAM permissions for the configured AccessKey (AK/SK) or STS Token.

> **⚠️ Least-privilege principle**: This skill's RAM permission strategy follows the
> "minimum permissions necessary" rule. The **recommended primary policy** is the custom
> least-privilege policy below. `FullAccess` system policies are listed only as a
> convenience fallback for development/testing — production deployments MUST use the
> custom policy.

### Recommended (PRIMARY): Custom Least-Privilege Policy

This policy enumerates only the specific Actions the skill actually invokes (verified
against `deploy_toolkit.py` and `aliyun appmanager` source). No wildcard `*` is used.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "ECSInstanceLifecycle",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateInstance",
        "ecs:RunInstances",
        "ecs:StartInstance",
        "ecs:StopInstance",
        "ecs:DeleteInstance",
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:ModifyInstanceAttribute",
        "ecs:AllocatePublicIpAddress",
        "ecs:DescribeRegions",
        "ecs:DescribeZones",
        "ecs:DescribeAvailableResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSCloudAssistant",
      "Effect": "Allow",
      "Action": [
        "ecs:RunCommand",
        "ecs:InvokeCommand",
        "ecs:DescribeInvocations",
        "ecs:DescribeInvocationResults",
        "ecs:DescribeCloudAssistantStatus"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSSecurityAndStorage",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateSecurityGroup",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:AuthorizeSecurityGroup",
        "ecs:JoinSecurityGroup",
        "ecs:CreateDisk",
        "ecs:DescribeDisks",
        "ecs:AttachDisk"
      ],
      "Resource": "*"
    },
    {
      "Sid": "OSSArtifactUpload",
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:GetObject",
        "oss:ListObjects",
        "oss:ListBuckets",
        "oss:CreateBucket",
        "oss:GetBucketInfo",
        "oss:GetBucketLocation"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VPCNetwork",
      "Effect": "Allow",
      "Action": [
        "vpc:CreateVpc",
        "vpc:CreateVSwitch",
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:DescribeVpcAttribute"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ComputeNestServiceInstance",
      "Effect": "Allow",
      "Action": [
        "computenest:CreateServiceInstance",
        "computenest:DeleteServiceInstance",
        "computenest:GetServiceInstance",
        "computenest:ListServiceInstances",
        "computenest:UpdateServiceInstance",
        "computenest:ContinueDeployServiceInstance",
        "computenest:GetServiceTemplateParameterConstraints"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note on omitted Actions**:
> - `oss:DeleteObject` is **not included** — the skill only uploads deploy artifacts; cleanup is performed by `aliyun appmanager <type> delete`, which goes through `computenest:DeleteServiceInstance` rather than direct OSS DELETE.
> - No wildcard Action (e.g. `ecs:*`, `oss:*`, `computenest:*`) is used.

### Fallback (DEV / TESTING ONLY): System FullAccess Policies

> **⛔ NOT RECOMMENDED FOR PRODUCTION**: These policies grant broad permissions that
> exceed what the skill actually needs and violate the least-privilege principle. Use
> them ONLY for quick local prototyping, then switch to the custom policy above before
> any non-throwaway use.

| Policy Name | Type | Purpose (subset actually used by this skill) |
|-------------|------|----------------------------------------------|
| `AliyunECSFullAccess` | System | ECS instance / SG / disk lifecycle + Cloud Assistant |
| `AliyunOSSFullAccess` | System | Upload deployment artifacts |
| `AliyunVPCFullAccess` | System | Create VPC / vSwitch for new ECS |
| `AliyunCloudAssistantFullAccess` | System | Run shell commands on ECS via Cloud Assistant |

### Permission Verification

The `deploy_toolkit.py check` script verifies credential validity by calling `aliyun appmanager app status`. If this call returns `Forbidden` or `NoPermission`, the user's RAM role/policy is insufficient.

**Common permission errors and resolutions:**

| Error Code | Cause | Fix |
|-----------|-------|-----|
| `Forbidden.RAM` | Missing RAM policy | Attach the custom policy above (or required policies) |
| `NoPermission` | Action not allowed | Verify the failing Action is enumerated in the custom policy |
| `InvalidAccessKeyId.NotFound` | AK does not exist | Regenerate AK in RAM console |
| `SignatureDoesNotMatch` | Secret key mismatch | Re-configure with correct SK |

### Credential Types Supported

| Type | Config Method | Use Case |
|------|--------------|----------|
| AK (long-term) | `aliyun configure --mode AK` (interactive) | Development/testing |
| STS Token (temporary) | `aliyun configure --mode StsToken` (interactive) | Production (recommended) |
| ECS RAM Role | `aliyun configure --mode EcsRamRole --ram-role-name <role>` | Running on ECS itself |

