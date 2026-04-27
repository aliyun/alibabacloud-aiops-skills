# RAM 权限清单

本 Skill 执行所需的 RAM 权限（最小权限原则）:

## 必需权限

`ecs:DescribeInstances` — 确认实例存在并获取基本信息（状态、名称、操作系统类型）

`ecs:DescribeInstanceAttribute` — 获取实例详细属性，用于操作系统类型检测和分支选择

`ecs:DescribeInstanceHistoryEvents` — 查询实例历史维护事件，判断是否为平台触发重启

`ecs:DescribeCloudAssistantStatus` — 验证云助手运行状态，确保远程诊断命令可执行

`ecs:RunCommand` — 通过云助手执行诊断脚本（Linux Shell 或 Windows PowerShell）

`ecs:DescribeInvocations` — 获取云助手命令执行结果，提取诊断输出

## 权限说明

- **权限范围**: 仅包含诊断所需的只读和命令执行权限
- **写操作**: 无（本 Skill 不修改实例配置）
- **通配符**: 未使用（遵循最小权限原则）

## 自定义策略示例

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeInstanceHistoryEvents",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:RunCommand",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    }
  ]
}
```

## 使用场景

此权限配置适用于 ECS 实例故障诊断场景:
- 检查平台维护事件
- 通过云助手远程执行诊断命令
- 获取系统日志和崩溃转储文件信息
- 分析重启/崩溃根因
