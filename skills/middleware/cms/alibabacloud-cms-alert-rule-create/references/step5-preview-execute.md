# Step 5: 预览与执行

## 目的

展示配置摘要，确认后执行 CLI 命令。

---

## 核心规则

> **必须先向用户展示配置摘要并等待确认，然后再执行 CLI 命令。**

---

## 强制用户确认（关键要求）

> **必须展示配置摘要并获得用户的明确确认后，才能调用 `PutResourceMetricRule`。**
> 即使所有参数已明确，也不要直接执行。

### 配置摘要模板

向用户展示以下摘要以获取确认：

```
告警规则配置摘要：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 产品：        {product_name}
- Namespace：   {namespace}
- 指标：        {metric_name}（{metric_description}）
- 统计方式：    {statistics}
- 阈值：        {comparison_operator} {threshold}{unit}
- 评估周期：    连续 {times} 个周期，每个周期 {period} 秒
- 严重级别：    {severity_level}
- 资源范围：    {resource_description}（例如"全部资源"或特定实例 ID）
- 联系人组：    {contact_group}
- 规则名称：    {rule_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

是否继续创建此告警规则？（是/否）
```

### 确认流程

- **用户确认** → 执行 `PutResourceMetricRule`
- **用户要求修改** → 返回相关步骤进行修改
- **用户取消** → 停止执行

> **警告**：跳过此确认步骤违反工作流规范。必须始终等待用户的明确批准。

---

## CMS 1.0 CLI

### 完整命令模板

```bash
aliyun cms put-resource-metric-rule \
  --rule-id "<rule-id>" \
  --rule-name "<rule-name>" \
  --namespace "<namespace>" \
  --metric-name "<metric-name>" \
  --resources '<resources-json>' \
  --escalations-<level>-comparison-operator "<operator>" \
  --escalations-<level>-statistics "Average" \
  --escalations-<level>-threshold <threshold> \
  --escalations-<level>-times <times> \
  --contact-groups "<contact-group>" \
  --silence-time 300 \
  --effective-interval "00:00-23:59" \
  --interval 60 \
  --region "<region-id>"
```

### 严重级别参数

将 `<level>` 替换为相应的严重级别：

| 严重级别 | 参数前缀 | 示例 |
|----------|----------|------|
| Critical | `--escalations-critical-*` | `--escalations-critical-threshold 85` |
| Warn | `--escalations-warn-*` | `--escalations-warn-threshold 99.9` |
| Info | `--escalations-info-*` | `--escalations-info-threshold 50` |

### 比较运算符

| 运算符 | 描述 |
|--------|------|
| `GreaterThanThreshold` | 值 > 阈值 |
| `GreaterThanOrEqualToThreshold` | 值 >= 阈值 |
| `LessThanThreshold` | 值 < 阈值 |
| `LessThanOrEqualToThreshold` | 值 <= 阈值 |

### 示例：Critical 级别告警

```bash
aliyun cms put-resource-metric-rule \
  --rule-id "ecs-cpu-alert-$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)" \
  --rule-name "ECS CPU利用率告警" \
  --namespace "acs_ecs_dashboard" \
  --metric-name "CPUUtilization" \
  --resources '[{"resource":"i-xxx"}]' \
  --escalations-critical-comparison-operator "GreaterThanThreshold" \
  --escalations-critical-statistics "Average" \
  --escalations-critical-threshold 85 \
  --escalations-critical-times 3 \
  --contact-groups "运维组" \
  --silence-time 300 \
  --effective-interval "00:00-23:59" \
  --interval 60 \
  --region "cn-hangzhou"
```

### 示例：Warn 级别告警

```bash
aliyun cms put-resource-metric-rule \
  --rule-id "oss-availability-alert-$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)" \
  --rule-name "OSS可用性告警" \
  --namespace "acs_oss_dashboard" \
  --metric-name "Availability" \
  --resources '[{"resource":"_ALL"}]' \
  --escalations-warn-comparison-operator "LessThanThreshold" \
  --escalations-warn-statistics "Value" \
  --escalations-warn-threshold 99.9 \
  --escalations-warn-times 1 \
  --contact-groups "infrastructure" \
  --silence-time 300 \
  --effective-interval "00:00-23:59" \
  --interval 60 \
  --region "cn-hangzhou"
```

### 参数说明

| 参数 | 描述 | 必填 |
|------|------|------|
| `--rule-id` | 唯一规则 ID，可自动生成 | 是 |
| `--rule-name` | 告警名称 | 是 |
| `--namespace` | 云产品命名空间 | 是 |
| `--metric-name` | 指标名称 | 是 |
| `--resources` | 实例范围 JSON（全部资源使用 `[{"resource":"_ALL"}]`） | 是 |
| `--escalations-<level>-*` | 严重级别配置 | 是 |
| `--contact-groups` | 联系人组 | 是 |
| `--silence-time` | 静默期（秒） | 否 |
| `--effective-interval` | 生效时间范围 | 否 |
| `--interval` | 检查间隔（秒，默认：60） | 否 |
| `--region` | 地域 ID | 是 |

---

## 下一步

→ `step6-verification.md`
