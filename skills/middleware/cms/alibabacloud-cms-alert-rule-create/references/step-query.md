# Step: 查询告警规则

## 目的

查询和列出已有的 CMS 告警规则，支持灵活筛选。

---

## 适用场景

当用户想要：
- 列出已有告警规则（按产品、状态或名称）
- 搜索特定告警规则
- 检查告警规则状态
- 验证某条规则是否已存在

---

## CLI 命令

```bash
aliyun cms describe-metric-rule-list [filters]
```

## 可用筛选条件

| 参数 | CLI 标志 | 描述 | 示例 |
|------|----------|------|------|
| Namespace | `--namespace` | 按云产品过滤 | `acs_ecs_dashboard` |
| MetricName | `--metric-name` | 按指标过滤 | `cpu_total` |
| RuleName | `--rule-name` | 按规则名称过滤（模糊匹配） | `ECS-CPU` |
| AlertState | `--alert-state` | 按告警状态过滤 | `OK`、`ALARM`、`INSUFFICIENT_DATA` |
| EnableState | `--enable-state` | 按启用状态过滤 | `true`、`false` |
| RuleIds | `--rule-ids` | 查询特定规则（逗号分隔） | `rule-id-1,rule-id-2` |
| Page | `--page` | 页码（默认：1） | `1` |
| PageSize | `--page-size` | 每页条数（默认：10） | `50` |

---

## 常用查询示例

### 列出某产品的所有规则
```bash
aliyun cms describe-metric-rule-list --namespace acs_ecs_dashboard --page-size 50
```

### 按名称查找规则
```bash
aliyun cms describe-metric-rule-list --rule-name "CPU"
```

### 列出处于 ALARM 状态的规则
```bash
aliyun cms describe-metric-rule-list --alert-state ALARM
```

### 查看特定规则
```bash
aliyun cms describe-metric-rule-list --rule-ids "rule-id-xxx"
```

---

## 响应格式化

以清晰的表格格式向用户展示查询结果：

| 字段 | 描述 |
|------|------|
| RuleId | 告警规则 ID |
| RuleName | 告警规则名称 |
| Namespace | 云产品命名空间 |
| MetricName | 监控指标 |
| AlertState | 当前状态（OK / ALARM / INSUFFICIENT_DATA） |
| EnableState | 是否启用 |
| ContactGroups | 通知联系人组 |
| Resources | 监控资源范围 |

---

## 工作流程

1. 识别用户的查询意图和所需筛选条件
2. 使用相应筛选条件构建 CLI 命令
3. 执行查询
4. 格式化并向用户展示结果
5. 如果用户想要执行操作（修改/删除），告知本技能仅支持创建 — 建议使用控制台进行修改
