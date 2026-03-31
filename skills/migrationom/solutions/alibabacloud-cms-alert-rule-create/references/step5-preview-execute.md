# Step 5: Preview & Execute

## Purpose

Display configuration summary, execute CLI after confirmation.

---

## Core Rule

> **MUST display configuration summary to user and wait for confirmation BEFORE executing CLI.**

---

## Mandatory User Confirmation (CRITICAL)

> **MUST present configuration summary and get explicit user confirmation BEFORE calling `PutResourceMetricRule`.**
> DO NOT execute directly even if all parameters are clear.

### Configuration Summary Template

Present the following summary to the user for confirmation:

```
Alert Rule Configuration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Product:        {product_name}
- Namespace:      {namespace}
- Metric:         {metric_name} ({metric_description})
- Statistics:     {statistics}
- Threshold:      {comparison_operator} {threshold}{unit}
- Evaluation:     {times} consecutive periods of {period}s
- Severity:       {severity_level}
- Resources:      {resource_description} (e.g., "All Resources" or specific instance IDs)
- Contact Group:  {contact_group}
- Rule Name:      {rule_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Shall I proceed to create this alert rule? (Yes/No)
```

### Confirmation Flow

- **If user confirms** → Execute `PutResourceMetricRule`
- **If user requests changes** → Go back to the relevant step and modify
- **If user cancels** → Stop execution

> **WARNING**: Skipping this confirmation step is a violation of the workflow. ALWAYS wait for explicit user approval.

---

## CMS 1.0 CLI

### Complete Command Template

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

### Severity Level Parameters

Replace `<level>` with the appropriate severity:

| Severity | Parameter Prefix | Example |
|----------|-----------------|---------|
| Critical | `--escalations-critical-*` | `--escalations-critical-threshold 85` |
| Warn | `--escalations-warn-*` | `--escalations-warn-threshold 99.9` |
| Info | `--escalations-info-*` | `--escalations-info-threshold 50` |

### Comparison Operators

| Operator | Description |
|----------|-------------|
| `GreaterThanThreshold` | Value > threshold |
| `GreaterThanOrEqualToThreshold` | Value >= threshold |
| `LessThanThreshold` | Value < threshold |
| `LessThanOrEqualToThreshold` | Value <= threshold |

### Example: Critical Level Alert

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

### Example: Warn Level Alert

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

### Parameter Notes

| Parameter | Description | Required |
|-----------|-------------|----------|
| `--rule-id` | Unique rule ID, can be auto-generated | Yes |
| `--rule-name` | Alert name | Yes |
| `--namespace` | Cloud product namespace | Yes |
| `--metric-name` | Metric name | Yes |
| `--resources` | Instance scope JSON (`[{"resource":"_ALL"}]` for all resources) | Yes |
| `--escalations-<level>-*` | Severity level configuration | Yes |
| `--contact-groups` | Contact groups | Yes |
| `--silence-time` | Silence period (seconds) | No |
| `--effective-interval` | Effective time range | No |
| `--interval` | Check interval in seconds (default: 60) | No |
| `--region` | Region ID | Yes |

---

## Next Step

→ `step6-verification.md`
