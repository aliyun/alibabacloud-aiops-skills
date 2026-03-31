---
name: alibabacloud-cms-alert-rule-create
description: |
  Create Alibaba Cloud CMS alert rules via CLI (write-operation skill). Supports CMS 1.0 cloud resource monitoring for ALL CMS-integrated cloud products.
  This skill performs write operations: creating alert rules, contacts, and contact groups.
  Use when: creating monitoring alerts, setting up alarm rules, configuring CMS alert policies for any cloud product,
  or managing cloud monitoring notifications.
  Triggers: "create alert", "setup monitoring", "configure alarm", "CMS alert",
  "cloud monitor rule", "告警规则", "创建告警", "监控报警".
---

# Alibaba Cloud Alert Rule Creation

This skill creates CMS 1.0 alert rules for cloud resource monitoring using CloudMonitor metrics. Supports **all CMS-integrated cloud products** through dynamic metric discovery.

---

## Workflow

| Step | Description | CMS 1.0 | Reference |
|------|-------------|---------|-----------|
| 1 | Context Lock | namespace, region, instances | `step1-context-lock.md` |
| 2 | Query Generation | Call describe-metric-meta-list to discover metrics for namespace, match to user intent | `step2-query-generation.md` |
| 3 | Detection Config | threshold, frequency (default 1min) | `step3-detection-config.md` |
| 4 | Notification | Query contacts → select or create | `step4-notification.md` |
| 5 | Preview & Execute | Show summary → confirm → CLI | `step5-preview-execute.md` |
| 6 | Verification | Check status | `step6-verification.md` |

---

## Pre-flight Checklist (MANDATORY)

> **Before creating ANY alert, complete these API calls to ensure correct workflow execution.**

| Step | Required API Call | CLI Command | Purpose |
|------|-------------------|-------------|---------|
| 1 | `DescribeProjectMeta` | `aliyun cms describe-project-meta` | List cloud product namespaces (when product is unclear) |
| 2 | `DescribeMetricMetaList` | `aliyun cms describe-metric-meta-list --namespace <ns>` | Metric Discovery: Get available metrics (fallback: metrics.md) |
| 4 | `DescribeContactGroupList` | `aliyun cms describe-contact-group-list` | Query existing contact groups |
| 5 | `PutResourceMetricRule` | `aliyun cms put-resource-metric-rule ...` | Create the alert rule |

> **These API calls are required for every alert creation. Always query contacts via the designated tools, even if the values seem known.**

---

## Critical Rules

### 1. Contact Query Before Create (MANDATORY)

> **This step is REQUIRED and CANNOT be skipped.**

1. **MUST call `describe-contact-group-list`** before creating any CMS alert
2. User provided contact name → Fuzzy match against existing groups
3. If no match → Help user create new contact group

### 2. Resources Parameter (MANDATORY)

> **The `--resources` parameter MUST always be explicitly passed. Never omit this parameter.**

- **All resources**: `--resources '[{"resource":"_ALL"}]'`
- **Specific instances**: `--resources '[{"resource":"i-xxx"}]'` or `--resources '[{"resource":"i-xxx"},{"resource":"i-yyy"}]'`

This applies to **ALL products** (ECS, RDS, SLB, OSS, MongoDB, etc.).

### 3. Required API Calls Summary

| Step 1 | Step 2 | Step 4 | Step 5 |
|--------|--------|--------|--------|
| `describe-project-meta` (when product unclear) | `describe-metric-meta-list` (MANDATORY) | `describe-contact-group-list` (MANDATORY) | `put-resource-metric-rule` |

### 4. Contact Group Fuzzy Matching

When user mentions a contact group, apply these matching rules:

| User Input | Match Strategy | Common Mappings |
|------------|---------------|------------------|
| "运维组" / "ops" | Contains/keyword | → `运维组`, `ops-alert-group`, `SRE-Team` |
| "基础设施组" | Contains/keyword | → `infrastructure`, `infrastructure-team` |
| "DBA团队" | Contains/keyword | → `DBA-Alert-Group`, `dba-team` |
| "网络组" | Contains/keyword | → `network-ops`, `network-sre` |
| Exact name | Direct match | Use exact name if found |

### 5. CLI Command Timeout

All `aliyun` CLI commands MUST be executed with a timeout to prevent hanging:
- **Default timeout**: 30 seconds for query operations (describe/list/get)
- **Extended timeout**: 60 seconds for write operations (put/create/update)
- If a command does not return within the timeout, retry once before reporting failure.

### 6. Duplicate Alert Pre-check

Before creating an alert rule, check if a rule with the same configuration already exists:
- Call `describe-metric-rule-list --namespace <ns> --metric-name <metric>` and check for matching rules
- If a duplicate exists, inform the user and ask whether to skip or create with a new name

### 7. Network Access Restriction

This skill only accesses Alibaba Cloud OpenAPI endpoints. Allowed domains:
- `cms.aliyuncs.com` — CloudMonitor API
- `ecs.aliyuncs.com` — ECS instance query
- `rds.aliyuncs.com` — RDS instance query
- `slb.aliyuncs.com` — SLB instance query

No other external network access is required or permitted.

### 8. Dynamic Metric Discovery

> **MUST call `describe-metric-meta-list` API to discover metrics for the target namespace. DO NOT hardcode metric names. Use `metrics.md` only as fallback when API is unavailable.**

1. Call `describe-project-meta` to list all available namespaces (when product is unclear)
2. Call `describe-metric-meta-list --namespace <ns>` to get available metrics
3. Match returned metrics to user's intent (CPU, memory, disk, network, etc.)
4. Fall back to `metrics.md` only when API call fails

### 9. CLI Self-Discovery

When unsure about CLI command syntax, arguments, or available subcommands, use `--help` to discover:

```bash
# List all available CMS commands
aliyun cms --help

# Show detailed usage for a specific command
aliyun cms <command> --help
# Example:
aliyun cms describe-metric-meta-list --help
```

This is the preferred way to resolve CLI uncertainties rather than guessing parameters.

### 10. Mandatory Confirmation Before Execution

> **MUST present configuration summary and get explicit user confirmation BEFORE calling `PutResourceMetricRule`.**

Even if all parameters are clear, DO NOT execute directly. Always show a configuration summary including: Product, Metric, Threshold, Severity, Resources scope, and Contact Group. Wait for user's explicit "Yes" or confirmation before proceeding.

---

## Severity Levels

| Level | Parameter Prefix | Example |
|-------|-----------------|---------|
| Critical | `--escalations-critical-*` | `--escalations-critical-threshold 85` |
| Warn | `--escalations-warn-*` | `--escalations-warn-threshold 99.9` |
| Info | `--escalations-info-*` | `--escalations-info-threshold 50` |

---

## Reference Files

| File | Purpose |
|------|---------|
| `related_apis.yaml` | API lookup before CLI calls |
| `references/step1-context-lock.md` | Context lock |
| `references/step2-query-generation.md` | Query generation |
| `references/step3-detection-config.md` | Detection config |
| `references/step4-notification.md` | Notification |
| `references/step5-preview-execute.md` | Preview & execute |
| `references/step6-verification.md` | Verification |
| `references/metrics.md` | Common metrics quick reference (fallback) |

---

## Prerequisites

```bash
# Verify aliyun CLI is configured
aliyun configure get

# Set User-Agent for all CLI calls (REQUIRED)
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"
```

**Important**: All `aliyun` CLI calls in this skill MUST include the User-Agent header. Set the environment variable before executing any commands.
