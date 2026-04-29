# RAM 权限

本技能所需的最小权限。这是一个**写操作技能**，用于创建告警规则、联系人和联系人组（CMS 1.0），以及创建/查询高级告警规则（CMS 2.0）。

## CMS 1.0 告警权限

| 权限 | 用途 | 使用阶段 |
|------|------|----------|
| `cms:DescribeProjectMeta` | 列出云产品 namespace | 步骤 1/2 |
| `cms:DescribeMetricMetaList` | 查询 namespace 下的可用指标 | 步骤 2 |
| `cms:DescribeContactGroupList` | 查询已有的联系人组 | 步骤 4 |
| `cms:PutContact` | 创建新的告警联系人 | 步骤 4 |
| `cms:PutContactGroup` | 创建新的联系人组 | 步骤 4 |
| `cms:PutResourceMetricRule` | 创建告警规则 | 步骤 5 |
| `cms:DescribeMetricRuleList` | 验证规则创建 / 查询规则 | 步骤 6 / 查询 |

## CMS 2.0 告警权限

| 权限 | 用途 | 使用阶段 |
|------|------|----------|
| `cms:ManageAlertRules` | 创建/更新/删除 CMS 2.0 告警规则（Prometheus/APM/UModel） | 步骤 5（执行） |
| `cms:QueryAlertRules` | 查询 CMS 2.0 告警规则 | 查询 / 重复预检 |
| `cms:ListAlertWebhooks` | 查询可用的 webhook 以配置通知 | 步骤 4（Webhook 查询） |

## 实例查询权限（可选，仅限 CMS 1.0）

仅在列出云资源实例以创建 CMS 1.0 告警时需要：

| 权限 | 用途 | 使用阶段 |
|------|------|----------|
| `ecs:DescribeInstances` | 列出 ECS 实例 | 步骤 1 |
| `rds:DescribeDBInstances` | 列出 RDS 实例 | 步骤 1 |
| `slb:DescribeLoadBalancers` | 列出 SLB 实例 | 步骤 1 |
