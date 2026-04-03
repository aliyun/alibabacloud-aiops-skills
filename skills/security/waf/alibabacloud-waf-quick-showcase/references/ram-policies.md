# RAM Permissions Required

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| VPC | vpc:CreateVpc | * | 创建专有网络 VPC |
| VPC | vpc:DescribeVpcs | * | 查询 VPC 列表和状态 |
| VPC | vpc:CreateVSwitch | * | 创建交换机 |
| VPC | vpc:DescribeVSwitches | * | 查询交换机列表和状态 |
| ECS | ecs:CreateSecurityGroup | * | 创建安全组 |
| ECS | ecs:AuthorizeSecurityGroup | * | 添加安全组入方向规则 |
| ECS | ecs:DescribeSecurityGroups | * | 查询安全组列表 |
| ECS | ecs:RunInstances | * | 创建并启动 ECS 实例 |
| ECS | ecs:DescribeInstances | * | 查询 ECS 实例列表和状态 |
| WAF | waf:CreatePostpaidInstance | * | 创建 WAF 按量付费实例 |
| WAF | waf:DescribeInstance | * | 查询 WAF 实例详情 |
| WAF | waf:SyncProductInstance | * | 同步云产品资产到 WAF |
| WAF | waf:DescribeProductInstances | * | 查询已同步的云产品资产 |
| WAF | waf:CreateCloudResource | * | 云产品接入 WAF |
| WAF | waf:DescribeCloudResources | * | 查询已接入 WAF 的云产品 |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:CreateVpc",
        "vpc:DescribeVpcs",
        "vpc:CreateVSwitch",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:CreateSecurityGroup",
        "ecs:AuthorizeSecurityGroup",
        "ecs:DescribeSecurityGroups",
        "ecs:RunInstances",
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "waf:CreatePostpaidInstance",
        "waf:DescribeInstance",
        "waf:SyncProductInstance",
        "waf:DescribeProductInstances",
        "waf:CreateCloudResource",
        "waf:DescribeCloudResources"
      ],
      "Resource": "*"
    }
  ]
}
```

## 系统策略（不推荐 - 权限过大）

> ⚠️ **安全警告：FullAccess 系统策略包含所有产品 Action**
>
> 以下系统策略虽然可以使用，但**违背最小权限原则**，存在安全风险：
> - **AliyunVPCFullAccess**: 包含 VPC 所有操作（创建、删除、修改等全部权限）
> - **AliyunECSFullAccess**: 包含 ECS 所有操作（包括释放实例、磁盘等危险操作）
> - **AliyunYundunWAFFullAccess**: 包含 WAF 所有操作（包括释放实例、删除配置等）
>
> **强烈建议**: 使用上方自定义 RAM Policy，仅授予必要的 15 个权限。
>
> 如果确实需要使用系统策略，请确保：
> 1. 仅在测试环境或临时场景下使用
> 2. 定期审计这些账号的操作日志
> 3. 不要将 AK/SK 用于生产环境
> 4. 了解 FullAccess 权限可能被滥用的风险

~~如果不想手动配置权限，可以绑定以下系统策略:~~

~~| 产品 | 系统策略名称 | 说明 |~~
~~|------|------------|------|~~
~~| VPC | AliyunVPCFullAccess | VPC 完整权限 |~~
~~| ECS | AliyunECSFullAccess | ECS 完整权限 |~~
~~| WAF | AliyunYundunWAFFullAccess | WAF 完整权限 |~~

## Best Practices

1. **最小权限原则**: 仅授予必要的权限，**避免使用 FullAccess 系统策略**
2. **资源范围限定**: 在生产环境中，建议将 `Resource` 限定为具体的资源 ARN
3. **定期审计**: 定期检查和清理不再使用的权限
4. **使用 STS 临时凭证**: 对于临时任务，建议使用 STS Token 而非永久 AK
5. **权限分离**: 开发和测试环境使用不同的 RAM 角色，避免权限混用
