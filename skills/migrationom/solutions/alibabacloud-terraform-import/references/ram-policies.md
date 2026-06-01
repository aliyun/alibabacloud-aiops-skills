# RAM Permission Reference

Permissions required by this Skill are divided into **general permissions** and **per-product permissions**. General permissions are always required; per-product permissions are selected based on the resource types the user actually imports — only the permissions for the specific products being imported are needed.

---

## Quick Setup

The system policy `ReadOnlyAccess` (read-only access to all resources) covers all API calls made by this Skill. For fine-grained control, create a custom policy using the lists below.

---

## General Permissions (always required)

### STS (Identity Verification)

| Action | Purpose |
|--------|---------|
| `sts:GetCallerIdentity` | Phase 2 credential identity verification |

### ResourceCenter (optional but recommended)

When missing, the Skill automatically falls back to native product APIs without affecting the core import flow.

| Action | Purpose |
|--------|---------|
| `resourcecenter:ListResourceTypes` | Query supported resource types |
| `resourcecenter:SearchResources` | Search resources (Phase 4 resource discovery) |
| `resourcecenter:ListResourceRelationships` | Query resource relationships (Phase 5 dependency graph) |

### IaCService (optional)

When missing, the Skill uses a static mapping table without affecting the core import flow.

| Action | Purpose |
|--------|---------|
| `iacservice:ListResourceTypes` | Build Terraform resource type mapping table |

---

## Per-Product Permissions (select based on imported resource types)

Only authorize for the products you actually import. For example, if only importing ECS instances, you only need ECS and VPC (network dependency) permissions.

### VPC (Networking)

| Action | Purpose |
|--------|---------|
| `vpc:DescribeVpcs` | Discover and get VPC details |
| `vpc:DescribeVSwitches` | Discover and get VSwitch details |
| `vpc:DescribeEipAddresses` | Discover and get EIP details |
| `vpc:DescribeNatGateways` | Discover and get NAT Gateway details |
| `vpc:DescribeSnatTableEntries` | Get SNAT entries |
| `vpc:DescribeRouteTableList` | Get route tables |
| `vpc:DescribeVpnGateways` | Discover VPN Gateways |

### ECS (Compute)

| Action | Purpose |
|--------|---------|
| `ecs:DescribeInstances` | Discover and get ECS instance details |
| `ecs:DescribeSecurityGroups` | Discover security groups |
| `ecs:DescribeSecurityGroupAttribute` | Get security group rules |
| `ecs:DescribeDisks` | Discover and get disk details |
| `ecs:DescribeImages` | Get custom images |
| `ecs:DescribeKeyPairs` | Get key pairs |

### OSS (Storage)

| Action | Purpose |
|--------|---------|
| `oss:ListBuckets` | Discover OSS Buckets |
| `oss:GetBucketInfo` | Get Bucket details |
| `oss:GetBucketAcl` | Get Bucket ACL |
| `oss:GetBucketVersioning` | Get versioning configuration |
| `oss:GetBucketLifecycle` | Get lifecycle rules |
| `oss:GetBucketCors` | Get CORS configuration |
| `oss:GetBucketEncryption` | Get encryption configuration |

### RDS (Relational Database)

| Action | Purpose |
|--------|---------|
| `rds:DescribeDBInstances` | Discover RDS instances |
| `rds:DescribeDBInstanceAttribute` | Get instance details |
| `rds:DescribeDatabases` | Get database list |
| `rds:DescribeAccounts` | Get account list |
| `rds:DescribeDBInstanceIPArrayList` | Get IP whitelist |
| `rds:DescribeDBInstanceNetInfo` | Get connection addresses |

### KVStore (Redis)

| Action | Purpose |
|--------|---------|
| `r-kvstore:DescribeInstances` | Discover Redis instances |
| `r-kvstore:DescribeInstanceAttribute` | Get instance details |
| `r-kvstore:DescribeSecurityIps` | Get IP whitelist |

### DDS (MongoDB)

| Action | Purpose |
|--------|---------|
| `dds:DescribeDBInstances` | Discover MongoDB instances |
| `dds:DescribeDBInstanceAttribute` | Get instance details |
| `dds:DescribeSecurityIps` | Get IP whitelist |

### SLB (Classic Load Balancer)

| Action | Purpose |
|--------|---------|
| `slb:DescribeLoadBalancers` | Discover SLB instances |
| `slb:DescribeLoadBalancerAttribute` | Get instance details |
| `slb:DescribeLoadBalancerListeners` | Get listener list |
| `slb:DescribeHealthStatus` | Get backend health status |

### ALB (Application Load Balancer)

| Action | Purpose |
|--------|---------|
| `alb:ListLoadBalancers` | Discover ALB instances |
| `alb:ListListeners` | Get listener list |
| `alb:ListServerGroups` | Get server groups |

### Alidns (DNS)

| Action | Purpose |
|--------|---------|
| `alidns:DescribeDomains` | Discover domains |
| `alidns:DescribeDomainRecords` | Get DNS records |
| `alidns:DescribeDomainGroups` | Get domain groups |

### RAM (Access Control)

| Action | Purpose |
|--------|---------|
| `ram:ListUsers` | Discover RAM users |
| `ram:ListRoles` | Discover RAM roles |
| `ram:ListPolicies` | Discover custom policies |
| `ram:ListPoliciesForUser` | Get user-attached policies |

### KMS (Key Management)

| Action | Purpose |
|--------|---------|
| `kms:ListKeys` | Discover KMS keys |
| `kms:DescribeKey` | Get key details |

### NAS (File Storage)

| Action | Purpose |
|--------|---------|
| `nas:DescribeFileSystems` | Discover file systems |
| `nas:DescribeMountTargets` | Get mount targets |

### CS (Container Service ACK)

| Action | Purpose |
|--------|---------|
| `cs:DescribeClusters` | Discover ACK clusters |
| `cs:DescribeClusterNodePools` | Get node pools |

### FC (Function Compute)

| Action | Purpose |
|--------|---------|
| `fc:ListServices` | Discover FC services |
| `fc:ListFunctions` | Get function list |

### ESS (Auto Scaling)

| Action | Purpose |
|--------|---------|
| `ess:DescribeScalingGroups` | Discover scaling groups |
| `ess:DescribeScalingConfigurations` | Get scaling configurations |

---

## Custom Policy Example (ECS + VPC only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "resourcecenter:ListResourceTypes",
        "resourcecenter:SearchResources",
        "resourcecenter:ListResourceRelationships",
        "iacservice:ListResourceTypes",
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:DescribeEipAddresses",
        "vpc:DescribeNatGateways",
        "vpc:DescribeRouteTableList",
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeDisks"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Notes

- All permissions are **read-only** (Describe/List/Get), no resource creation, modification, or deletion is involved
- The `terraform import` command itself only reads cloud resource state and writes to local state; it does not modify cloud resources
- If using the `ReadOnlyAccess` system policy, all above permissions are already included
- In per-product permissions, network resources (VPC) are typically imported as dependencies of other resources, so it is recommended to always authorize them
