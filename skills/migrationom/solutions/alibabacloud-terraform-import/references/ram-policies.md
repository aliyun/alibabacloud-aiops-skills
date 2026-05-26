# RAM 权限说明

本 Skill 所需权限分为**通用权限**和**按需权限**两部分。通用权限始终需要；按需权限根据用户实际导入的资源类型选择，只导入哪些产品的资源就只需要对应产品的权限。

---

## 快捷方案

使用系统策略 `ReadOnlyAccess`（只读访问所有资源）可覆盖本 Skill 的全部 API 调用。若需精细控制，按以下列表创建自定义策略。

---

## 通用权限（始终需要）

### STS（身份验证）

| Action | 用途 |
|--------|------|
| `sts:GetCallerIdentity` | Phase 2 验证当前凭证身份 |

### ResourceCenter（资源中心，可选但推荐）

缺失时 Skill 自动降级使用原生产品 API，不影响核心导入流程。

| Action | 用途 |
|--------|------|
| `resourcecenter:ListResourceTypes` | 查询支持的资源类型 |
| `resourcecenter:SearchResources` | 搜索资源（Phase 4 资源发现） |
| `resourcecenter:ListResourceRelationships` | 查询资源关系（Phase 5 依赖图） |

### IaCService（可选）

缺失时 Skill 使用静态映射表，不影响核心导入流程。

| Action | 用途 |
|--------|------|
| `iacservice:ListResourceTypes` | 建立 Terraform 资源类型映射表 |

---

## 按需权限（根据导入的资源类型选择）

仅需为实际要导入的产品授权。例如只导入 ECS 实例，则只需 ECS 和 VPC（网络依赖）的权限。

### VPC（网络）

| Action | 用途 |
|--------|------|
| `vpc:DescribeVpcs` | 发现和获取 VPC 详情 |
| `vpc:DescribeVSwitches` | 发现和获取 VSwitch 详情 |
| `vpc:DescribeEipAddresses` | 发现和获取 EIP 详情 |
| `vpc:DescribeNatGateways` | 发现和获取 NAT 网关详情 |
| `vpc:DescribeSnatTableEntries` | 获取 SNAT 条目 |
| `vpc:DescribeRouteTableList` | 获取路由表 |
| `vpc:DescribeVpnGateways` | 发现 VPN 网关 |

### ECS（计算）

| Action | 用途 |
|--------|------|
| `ecs:DescribeInstances` | 发现和获取 ECS 实例详情 |
| `ecs:DescribeSecurityGroups` | 发现安全组 |
| `ecs:DescribeSecurityGroupAttribute` | 获取安全组规则 |
| `ecs:DescribeDisks` | 发现和获取云盘详情 |
| `ecs:DescribeImages` | 获取自定义镜像 |
| `ecs:DescribeKeyPairs` | 获取密钥对 |

### OSS（存储）

| Action | 用途 |
|--------|------|
| `oss:ListBuckets` | 发现 OSS Bucket |
| `oss:GetBucketInfo` | 获取 Bucket 详情 |
| `oss:GetBucketAcl` | 获取 Bucket ACL |
| `oss:GetBucketVersioning` | 获取版本控制配置 |
| `oss:GetBucketLifecycle` | 获取生命周期规则 |
| `oss:GetBucketCors` | 获取 CORS 配置 |
| `oss:GetBucketEncryption` | 获取加密配置 |

### RDS（关系型数据库）

| Action | 用途 |
|--------|------|
| `rds:DescribeDBInstances` | 发现 RDS 实例 |
| `rds:DescribeDBInstanceAttribute` | 获取实例详情 |
| `rds:DescribeDatabases` | 获取数据库列表 |
| `rds:DescribeAccounts` | 获取账号列表 |
| `rds:DescribeDBInstanceIPArrayList` | 获取白名单 |
| `rds:DescribeDBInstanceNetInfo` | 获取连接地址 |

### KVStore（Redis）

| Action | 用途 |
|--------|------|
| `r-kvstore:DescribeInstances` | 发现 Redis 实例 |
| `r-kvstore:DescribeInstanceAttribute` | 获取实例详情 |
| `r-kvstore:DescribeSecurityIps` | 获取白名单 |

### DDS（MongoDB）

| Action | 用途 |
|--------|------|
| `dds:DescribeDBInstances` | 发现 MongoDB 实例 |
| `dds:DescribeDBInstanceAttribute` | 获取实例详情 |
| `dds:DescribeSecurityIps` | 获取白名单 |

### SLB（传统负载均衡）

| Action | 用途 |
|--------|------|
| `slb:DescribeLoadBalancers` | 发现 SLB 实例 |
| `slb:DescribeLoadBalancerAttribute` | 获取实例详情 |
| `slb:DescribeLoadBalancerListeners` | 获取监听列表 |
| `slb:DescribeHealthStatus` | 获取后端健康状态 |

### ALB（应用型负载均衡）

| Action | 用途 |
|--------|------|
| `alb:ListLoadBalancers` | 发现 ALB 实例 |
| `alb:ListListeners` | 获取监听列表 |
| `alb:ListServerGroups` | 获取服务器组 |

### Alidns（云解析）

| Action | 用途 |
|--------|------|
| `alidns:DescribeDomains` | 发现域名 |
| `alidns:DescribeDomainRecords` | 获取解析记录 |
| `alidns:DescribeDomainGroups` | 获取域名分组 |

### RAM（访问控制）

| Action | 用途 |
|--------|------|
| `ram:ListUsers` | 发现 RAM 用户 |
| `ram:ListRoles` | 发现 RAM 角色 |
| `ram:ListPolicies` | 发现自定义策略 |
| `ram:ListPoliciesForUser` | 获取用户绑定策略 |

### KMS（密钥管理）

| Action | 用途 |
|--------|------|
| `kms:ListKeys` | 发现 KMS 密钥 |
| `kms:DescribeKey` | 获取密钥详情 |

### NAS（文件存储）

| Action | 用途 |
|--------|------|
| `nas:DescribeFileSystems` | 发现文件系统 |
| `nas:DescribeMountTargets` | 获取挂载点 |

### CS（容器服务 ACK）

| Action | 用途 |
|--------|------|
| `cs:DescribeClusters` | 发现 ACK 集群 |
| `cs:DescribeClusterNodePools` | 获取节点池 |

### FC（函数计算）

| Action | 用途 |
|--------|------|
| `fc:ListServices` | 发现 FC 服务 |
| `fc:ListFunctions` | 获取函数列表 |

### ESS（弹性伸缩）

| Action | 用途 |
|--------|------|
| `ess:DescribeScalingGroups` | 发现伸缩组 |
| `ess:DescribeScalingConfigurations` | 获取伸缩配置 |

---

## 自定义策略示例（仅导入 ECS + VPC）

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

## 注意事项

- 所有权限均为**只读**（Describe/List/Get），不涉及资源创建、修改或删除
- `terraform import` 命令本身只读取云上资源状态写入本地 state，不修改云上资源
- 若使用 `ReadOnlyAccess` 系统策略，以上全部权限已包含
- 按需权限中，网络类资源（VPC）通常作为其他资源的依赖被一并导入，建议默认授权
