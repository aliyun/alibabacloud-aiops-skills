# RAM 权限策略

## 所需权限概览

本技能为**纯路由技能**，仅需要只读权限用于资源查询和信息收集。
具体诊断操作由后端技能执行，其权限需求请参见对应后端技能文档。

### ECS 云服务器权限（只读）

| Action | 说明 |
|--------|-----|
| `ecs:DescribeInstances` | 查询实例列表和详情 |
| `ecs:DescribeInstanceAttribute` | 查询实例属性 |

### VPC 专有网络权限（只读）

| Action | 说明 |
|--------|-----|
| `vpc:DescribeVpcs` | 查询 VPC 信息 |
| `vpc:DescribeEipAddresses` | 查询 EIP 绑定信息 |

---

## 推荐 RAM 策略

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 权限说明

本路由技能的所有操作均为**只读** API 调用：
- ECS 实例信息查询（用于资源识别）
- VPC 网络信息查询（用于资源定位）

### 后端技能权限

具体诊断操作的权限需求由各后端技能定义：

| 后端技能 | 权限文档位置 |
|---------|-------------|
| `alibabacloud-ecs-diagnose` | 该技能的 references/ram-policies.md |
| `alibabacloud-network-reachability-analysis` | 该技能的 references/ram-policies.md |
| `alibabacloud-das-agent` | 该技能的 references/ram-policies.md |

> **注意**: 如需执行云助手命令（`ecs:RunCommand`）、网络可达性分析（`nis:*`）、
> 或监控数据查询（`cms:*`），请确保已安装对应后端技能并配置相应权限。
