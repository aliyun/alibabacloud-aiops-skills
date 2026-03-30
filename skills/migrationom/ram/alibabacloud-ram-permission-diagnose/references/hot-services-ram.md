# Popular Services RAM Action Reference

> Used for Step 3 built-in knowledge priority. The following Actions are grouped by common task scenarios and can be used directly to generate minimum-privilege policies.

## ECS (Elastic Compute Service)

### Common Action Groups

| Scenario | Required Actions | Resource Pattern |
|----------|-----------------|-----------------|
| List / describe instances | `ecs:DescribeInstances`, `ecs:DescribeInstanceStatus` | `acs:ecs:*:*:instance/*` |
| Start / stop instances | `ecs:StartInstance`, `ecs:StopInstance`, `ecs:RebootInstance` | `acs:ecs:*:*:instance/*` |
| Create instances | `ecs:RunInstances`, `ecs:DescribeImages`, `ecs:DescribeSecurityGroups` | `acs:ecs:*:*:*` |
| Change instance type | `ecs:ModifyInstanceSpec`, `ecs:DescribeResourcesModification` | `acs:ecs:*:*:instance/*` |
| Disk snapshots | `ecs:CreateSnapshot`, `ecs:DescribeSnapshots`, `ecs:DescribeDisks` | `acs:ecs:*:*:disk/*` |
| Security group management | `ecs:DescribeSecurityGroups`, `ecs:AuthorizeSecurityGroup`, `ecs:RevokeSecurityGroup` | `acs:ecs:*:*:securitygroup/*` |

### Recommended System Policies
- Read-only operations: `AliyunECSReadOnlyAccess`
- Operational access (no create/delete): `AliyunECSOperatorAccess`
- Full control: `AliyunECSFullAccess`

---

## OSS (Object Storage Service)

### Common Action Groups

| Scenario | Required Actions | Resource Pattern |
|----------|-----------------|-----------------|
| Read objects | `oss:GetObject`, `oss:HeadObject` | `acs:oss:*:*:<bucket-name>/*` |
| Upload objects | `oss:PutObject`, `oss:InitiateMultipartUpload`, `oss:UploadPart` | `acs:oss:*:*:<bucket-name>/*` |
| Delete objects | `oss:DeleteObject` | `acs:oss:*:*:<bucket-name>/*` |
| List objects | `oss:ListObjects`, `oss:ListBuckets` | `acs:oss:*:*:<bucket-name>` |
| Bucket management | `oss:CreateBucket`, `oss:DeleteBucket`, `oss:GetBucketInfo` | `acs:oss:*:*:*` |

### Recommended System Policies
- Read-only: `AliyunOSSReadOnlyAccess`
- Full control: `AliyunOSSFullAccess`

---

## RDS (Relational Database Service)

### Common Action Groups

| Scenario | Required Actions | Resource Pattern |
|----------|-----------------|-----------------|
| Query instances / databases | `rds:DescribeDBInstances`, `rds:DescribeDBInstanceAttribute` | `acs:rds:*:*:dbinstance/*` |
| Create database accounts | `rds:CreateAccount`, `rds:DescribeAccounts` | `acs:rds:*:*:dbinstance/*` |
| Backup management | `rds:CreateBackup`, `rds:DescribeBackups` | `acs:rds:*:*:dbinstance/*` |
| Change instance type | `rds:ModifyDBInstanceSpec` | `acs:rds:*:*:dbinstance/*` |
| Whitelist management | `rds:ModifySecurityIps`, `rds:DescribeDBInstanceIPArrayList` | `acs:rds:*:*:dbinstance/*` |

### Recommended System Policies
- Read-only: `AliyunRDSReadOnlyAccess`
- Full control: `AliyunRDSFullAccess`

---

## FC (Function Compute)

### Common Action Groups

| Scenario | Required Actions | Resource Pattern |
|----------|-----------------|-----------------|
| Invoke functions | `fc:InvokeFunction` | `acs:fc:*:*:services/*/functions/*` |
| Query functions | `fc:GetFunction`, `fc:ListFunctions`, `fc:GetService` | `acs:fc:*:*:services/*` |
| Deploy functions | `fc:CreateFunction`, `fc:UpdateFunction`, `fc:CreateService` | `acs:fc:*:*:*` |
| Trigger management | `fc:CreateTrigger`, `fc:UpdateTrigger`, `fc:ListTriggers` | `acs:fc:*:*:services/*/functions/*/triggers/*` |

### Recommended System Policies
- Read-only: `AliyunFCReadOnlyAccess`
- Full control: `AliyunFCFullAccess`

---

## SLB (Server Load Balancer)

### Common Action Groups

| Scenario | Required Actions | Resource Pattern |
|----------|-----------------|-----------------|
| Query instances | `slb:DescribeLoadBalancers`, `slb:DescribeLoadBalancerAttribute` | `acs:slb:*:*:loadbalancer/*` |
| Listener management | `slb:CreateLoadBalancerHTTPListener`, `slb:StartLoadBalancerListener` | `acs:slb:*:*:loadbalancer/*` |
| Backend servers | `slb:AddBackendServers`, `slb:RemoveBackendServers` | `acs:slb:*:*:loadbalancer/*` |

### Recommended System Policies
- Read-only: `AliyunSLBReadOnlyAccess`
- Full control: `AliyunSLBFullAccess`

---

## VPC (Virtual Private Cloud)

### Common Action Groups

| Scenario | Required Actions | Resource Pattern |
|----------|-----------------|-----------------|
| Query VPCs / VSwitches | `vpc:DescribeVpcs`, `vpc:DescribeVSwitches` | `acs:vpc:*:*:vpc/*` |
| Security groups / routing | `vpc:DescribeRouteTables`, `vpc:DescribeRouteEntryList` | `acs:vpc:*:*:routetable/*` |
| EIP management | `vpc:AllocateEipAddress`, `vpc:AssociateEipAddress`, `vpc:DescribeEipAddresses` | `acs:vpc:*:*:eip/*` |

### Recommended System Policies
- Read-only: `AliyunVPCReadOnlyAccess`
- Full control: `AliyunVPCFullAccess`

---

## SLS (Log Service)

### Common Action Groups

| Scenario | Required Actions | Resource Pattern |
|----------|-----------------|-----------------|
| Query logs | `log:GetLogStore`, `log:GetLogs`, `log:ListLogStores` | `acs:log:*:*:project/*` |
| Write logs | `log:PostLogStoreLogs` | `acs:log:*:*:project/*/logstore/*` |
| Project management | `log:CreateProject`, `log:ListProject` | `acs:log:*:*:*` |

### Recommended System Policies
- Read-only: `AliyunLogReadOnlyAccess`
- Full control: `AliyunLogFullAccess`
