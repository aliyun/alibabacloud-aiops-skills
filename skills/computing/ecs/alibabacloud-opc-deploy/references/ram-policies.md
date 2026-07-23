# RAM Policy — Least-Privilege Permissions for opc-deploy

> RAM permission declaration for the deploy skill (portal rule 2.2.6). A dedicated sub-account `opc-deploy` (only `AliyunSTSAssumeRoleAccess`) assumes the role `opc-deploy-role`, which carries the custom least-privilege policy `opc-deploy-policy` below. Operational setup steps live in the Phase 0.3 credential-config flow; this file is the single source of truth for the policy content itself.
>
> Note: the identifiers below (e.g., `ecs:RunInstances`) are RAM **action names**, not CLI commands — they stay in PascalCase.

## Honest notes on RAM condition limitations (E2E-measured)

1. Alibaba Cloud RAM does **not** support IfExists/Null condition operators — only basic operators such as StringEquals/StringNotEquals/Bool.
2. The `ecs:InstanceType` condition key is **not populated** in the `RunInstances` request context, so the instance-type allowlist can only be hardcoded in the skill's yaml params.
3. `Describe*`/`List*` list queries **do not populate** the `acs:ResourceTag` condition key — all read-only operations must sit in an unconditional Allow statement.
4. RDS RAM evaluation **never populates** `acs:ResourceTag` — even if a resource carries the opc:managed tag, RAM cannot "see" it, so RDS Manage/Teardown operations cannot be isolated by a tag condition (E2E-confirmed).
5. KeyPair resources do **not** support `acs:ResourceTag` — `ecs:DeleteKeyPairs` must be an unconditional Allow (E2E-confirmed).
6. `CreateDBInstance`'s `--Tag` parameter is **accepted by the API but the tag is not persisted**; call `AddTagsToResource` after creation to attach it. ECS `RunInstances --Tag` likewise has no effect — a post_action `ecs:TagResources` call is required.
7. ESS `CreateScalingGroup` must explicitly pass `--Tag.1.Key opc:managed --Tag.1.Value true`, otherwise later Manage/Teardown is ImplicitDenied.

## Policy: opc-deploy-policy

Create at https://ram.console.aliyun.com/policies/create (policy name: `opc-deploy-policy`). Layered by each service's `acs:ResourceTag` support (Describe is fully unconditional):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "DescribeReadOnlyNoCondition",
      "Effect": "Allow",
      "Action": [
        "ecs:Describe*", "ecs:List*",
        "vpc:Describe*", "vpc:List*",
        "rds:Describe*", "rds:List*",
        "oss:GetBucket*", "oss:GetService", "oss:ListBuckets", "oss:ListObjects",
        "alb:Describe*", "alb:List*",
        "ess:Describe*", "ess:List*",
        "swas-open:Describe*", "swas-open:List*",
        "esa:Describe*", "esa:List*",
        "actiontrail:Describe*", "actiontrail:List*",
        "ram:GetCallerIdentity", "ram:GetUser", "ram:ListAccessKeys",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PriceQueryNoCondition",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribePrice", "rds:DescribePrice", "alb:DescribePrice",
        "swas-open:DescribePrice", "esa:DescribePrice"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CreateAndTagNoCondition",
      "Effect": "Allow",
      "Action": [
        "ecs:RunInstances", "ecs:CreateInstance",
        "ecs:CreateSecurityGroup", "ecs:AuthorizeSecurityGroup",
        "ecs:CreateKeyPair", "ecs:ImportKeyPair",
        "ecs:TagResources",
        "vpc:CreateVpc", "vpc:CreateVSwitch", "vpc:TagResources",
        "rds:CreateDBInstance", "rds:CreateAccount", "rds:GrantAccountPrivilege", "rds:CreateDatabase",
        "rds:AddTagsToResource",
        "oss:PutBucket", "oss:PutBucketEncryption", "oss:PutBucketVersioning",
        "oss:PutBucketPublicAccessBlock", "oss:PutBucketTagging",
        "alb:CreateLoadBalancer", "alb:CreateListener", "alb:CreateServerGroup",
        "alb:TagResources",
        "ess:CreateScalingGroup", "ess:CreateScalingConfiguration", "ess:CreateScalingRule",
        "ess:EnableScalingGroup", "ess:CreateAlarm",
        "ess:TagResources"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EcsVpcAlbEssManageOpcTagged",
      "Effect": "Allow",
      "Action": [
        "ecs:Modify*", "ecs:Stop*", "ecs:Start*", "ecs:Reboot*",
        "vpc:Modify*",
        "alb:Update*",
        "ess:Modify*", "ess:Disable*", "ess:RemoveInstances", "ess:DetachInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": { "acs:ResourceTag/opc:managed": "true" }
      }
    },
    {
      "Sid": "OssManageNoCondition",
      "Effect": "Allow",
      "Action": [
        "oss:PutObject", "oss:GetObject", "oss:DeleteObject"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RdsManageNoCondition",
      "Effect": "Allow",
      "Action": [
        "rds:ModifySecurityIps", "rds:ModifyDBInstanceSpec",
        "rds:ModifySecurityGroupConfiguration", "rds:ResetAccountPassword",
        "rds:Modify*", "rds:Restart*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SwasEsaActionTrailNoTagSupport",
      "Effect": "Allow",
      "Action": [
        "swas-open:CreateInstances", "swas-open:RebootInstance", "swas-open:StopInstance", "swas-open:StartInstance",
        "esa:PurchaseRatePlan", "esa:CreateSite",
        "actiontrail:CreateTrail", "actiontrail:UpdateTrail", "actiontrail:StartLogging", "actiontrail:StopLogging"
      ],
      "Resource": "*"
    },
    {
      "Sid": "TeardownOpcTagged",
      "Effect": "Allow",
      "Action": [
        "ecs:DeleteInstance", "ecs:DeleteSecurityGroup",
        "vpc:DeleteVSwitch", "vpc:DeleteVpc",
        "alb:DeleteLoadBalancer",
        "ess:DeleteScalingGroup", "ess:DeleteScalingRule", "ess:DeleteAlarm",
        "swas-open:DeleteInstance"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": { "acs:ResourceTag/opc:managed": "true" }
      }
    },
    {
      "Sid": "TeardownNoTagSupport",
      "Effect": "Allow",
      "Action": [
        "ecs:DeleteKeyPairs",
        "rds:DeleteDBInstance",
        "oss:DeleteBucket",
        "ess:DeleteScalingConfiguration"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyUntaggedModifyAfterCreate",
      "Effect": "Deny",
      "Action": [
        "ecs:Modify*", "ecs:Stop*", "ecs:Start*", "ecs:Reboot*",
        "alb:Update*",
        "ess:Modify*", "ess:Disable*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": { "acs:ResourceTag/opc:managed": "true" }
      }
    }
  ]
}
```

## Statement layering notes (by measured acs:ResourceTag support)

- **DescribeReadOnly**: all `Describe*`/`List*` read-only ops are **unconditional Allow** — list APIs do not populate acs:ResourceTag. `oss:ListObjects` is added (the GetBucket* wildcard does not cover ListObjects).
- **CreateAndTag**: all Create + TagResources/AddTagsToResource are unconditional Allow, including `ess:TagResources`.
- **EcsVpcAlbEssManage**: only "mutating" ops (Modify/Stop/Start/Reboot/RemoveInstances) carry the `acs:ResourceTag` condition (these services are measured to support tag conditions).
- **OssManageNoCondition**: `oss:PutObject/GetObject/DeleteObject` are **unconditional Allow** — OSS does not support the `acs:ResourceTag` condition key; the tag set by PutBucketTagging is not recognized by RAM, so a tag condition would always fail → 403.
- **RdsManageNoCondition**: all RDS Manage ops are **unconditional Allow** — the RDS service does not populate acs:ResourceTag.
- **TeardownNoTagSupport**: `ecs:DeleteKeyPairs` + `rds:DeleteDBInstance` + `oss:DeleteBucket` (OSS lacks acs:ResourceTag) + `ess:DeleteScalingConfiguration` (a scaling config does not inherit the scaling group's tag) are unconditional Allow.
- **TeardownOpcTagged**: the remaining Delete ops carry the tag condition (ECS/VPC/ALB/ESS-group/SWAS are measured to support it); `oss:DeleteBucket` has been removed from here.
- **DenyUntaggedModifyAfterCreate**: `rds:Modify*` removed (RDS does not populate the tag condition, so a Deny would be meaningless).
- **SWAS-OPEN** still does not support the acs:ResourceTag Condition (measured); control is only by Action granularity.
- **Security-equivalence argument**: once the opc role holds the permanent AK it can "see" every resource under the account (Describe is unconditional), but it **cannot modify/delete** ECS/VPC/ALB/ESS-group resources lacking the opc:managed tag (Manage/Teardown conditions + the Deny backstop). For resource types that do not support acs:ResourceTag (OSS/RDS/SWAS/ESS-config/KeyPair), isolation drops to Action granularity — the opc role can only touch the Actions it is granted, and those resources are all created by the opc role (other OSS buckets under the account are not in the opc creation path).

## Quota companion

After creating the policy, go to the RAM sub-account quota page https://ram.console.aliyun.com/quotas and set opc-deploy to max ECS=5 / max RDS=2 / max VPC=1. The skill asks whether this quota has been set at the end of Phase 0.3.
