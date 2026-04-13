---
name: alibabacloud-dataworks-data-ops
description: |
  DataWorks Operations Center assistant for task and workflow operations, alert rule creation and management.
  Covers troubleshooting, failure recovery, baseline assurance, monitoring and alerting.
  Supports periodic, manual, and triggered tasks/workflows (excludes real-time/streaming tasks).
  Uses aliyun CLI to call dataworks-public OpenAPI (2024-05-18).
  Trigger keywords: query task, task instance, instance log, workflow, workflow instance, alert rule,
  operations center, task failure, instance status, upstream/downstream dependency, rerun,
  monitoring alert, custom monitoring, alert rule, task instance, workflow instance, operation log,
  baseline assurance, failure recovery, DataWorks operations.
  Do NOT trigger: data source management, compute resources, resource groups, data development,
  MaxCompute table management, ECS/RDS/OSS operations, workspace member management,
  data quality, data lineage, data preview.
---

# DataWorks Data Operations

DataWorks Operations Center assistant for task and workflow operations, alert rule creation and management.
Supports periodic, manual, and triggered tasks/workflows (excludes real-time/streaming tasks).

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

## Environment Variables

The aliyun CLI default timeout may cause indefinite hangs. You [MUST] set the following environment variables before executing any API command:

| Variable | Description | Default |
|------|------|-------|
| `ALIBABA_CLOUD_CONNECT_TIMEOUT` | Connection timeout in milliseconds | 10000 |
| `ALIBABA_CLOUD_READ_TIMEOUT` | Read timeout in milliseconds | 30000 |

For large-volume queries (e.g., paginated task instance lists with 500+ results), `ALIBABA_CLOUD_READ_TIMEOUT` may be increased to 60000 ms.

If an API call times out, [MUST] retry once with a doubled read timeout value. If the second attempt also fails, report the timeout to the user and suggest checking network connectivity, project ID validity, or RAM permissions.

No other special environment variable requirements.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Permissions

This skill requires the following RAM permissions:

### Task Management

| API | Permission Action | Description |
|-----|------------|------|
| GetTask | `dataworks:GetTask` | Get task details |
| ListTasks | `dataworks:ListTasks` | Query task list |
| ListUpstreamTasks | `dataworks:ListUpstreamTasks` | Query upstream task list |
| ListDownstreamTasks | `dataworks:ListDownstreamTasks` | Query downstream task list |
| ListTaskOperationLogs | `dataworks:ListTaskOperationLogs` | Query task operation logs |

### Task Instance Management

| API | Permission Action | Description |
|-----|------------|------|
| ListTaskInstances | `dataworks:ListTaskInstances` | Query task instance list |
| GetTaskInstance | `dataworks:GetTaskInstance` | Get task instance details |
| GetTaskInstanceLog | `dataworks:GetTaskInstanceLog` | Get task instance logs |
| ListUpstreamTaskInstances | `dataworks:ListUpstreamTaskInstances` | Query upstream task instances |
| ListDownstreamTaskInstances | `dataworks:ListDownstreamTaskInstances` | Query downstream task instances |
| ListTaskInstanceOperationLogs | `dataworks:ListTaskInstanceOperationLogs` | Query task instance operation logs |

### Workflow (Operations Center, read-only)

| API | Permission Action | Description |
|-----|------------|------|
| GetWorkflow | `dataworks:GetWorkflow` | Get workflow details |
| ListWorkflows | `dataworks:ListWorkflows` | Query workflow list |

### Workflow Instance (Operations Center, read-only)

| API | Permission Action | Description |
|-----|------------|------|
| ListWorkflowInstances | `dataworks:ListWorkflowInstances` | Query workflow instance list |
| GetWorkflowInstance | `dataworks:GetWorkflowInstance` | Get workflow instance details |

### Alert Rules (Custom Monitoring, read-only)

| API | Permission Action | Description |
|-----|------------|------|
| ListAlertRules | `dataworks:ListAlertRules` | Query alert rule list |
| GetAlertRule | `dataworks:GetAlertRule` | Get alert rule details |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., ProjectId, RegionId, bizdate, instance IDs, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-------|----------|------|-------|
| Region | Required | Target region | None |
| ProjectId | Required | DataWorks Workspace ID | None |
| Bizdate | Required (instance-related) | Business date (millisecond timestamp) | Today's business date |

Instance status enum values (used for `--status` parameter):
- `NotRun` - Not Run
- `Running` - Running
- `Failure` - Failed
- `Success` - Success
- `WaitTime` - Waiting for Time
- `WaitResource` - Waiting for Resources

Workflow instance type enum values (used for `--type` parameter):
- `Normal` - Normal Scheduling
- `Manual` - Manual Run
- `SmokeTest` - Smoke Test
- `SupplementData` - Backfill Data
- `ManualWorkflow` - Manual Workflow
- `TriggerWorkflow` - Trigger Workflow

## Core Workflows

### 0. Confirm Target Region

Confirm the target region with the user. Common regions:
- `cn-hangzhou` - East China 1 (Hangzhou)
- `cn-shanghai` - East China 2 (Shanghai)
- `cn-beijing` - North China 2 (Beijing)
- `cn-shenzhen` - South China 1 (Shenzhen)

---

### Task Management

```bash
# Query task list
aliyun dataworks-public list-tasks \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  [--name <TASK_NAME>] \
  [--page-size <SIZE>] \
  --user-agent AlibabaCloud-Agent-Skills

# Get task details
aliyun dataworks-public get-task \
  --region <REGION> \
  --id <TASK_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

> For more command parameters and the full command list, see [references/related-commands.md](references/related-commands.md)

---

### Task Instance Management

```bash
# Query task instance list (filter by status)
aliyun dataworks-public list-task-instances \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  --bizdate <BIZDATE_TIMESTAMP> \
  [--status NotRun|Running|Failure|Success|WaitTime|WaitResource] \
  [--task-name <TASK_NAME>] \
  --user-agent AlibabaCloud-Agent-Skills

# Get task instance log
aliyun dataworks-public get-task-instance-log \
  --region <REGION> \
  --id <TASK_INSTANCE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

> For more commands (instance details, upstream/downstream instances, operation logs, etc.) see [references/related-commands.md](references/related-commands.md)

---

### Workflow (Operations Center, read-only)

```bash
# Query workflow list
aliyun dataworks-public list-workflows \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  [--name <WORKFLOW_NAME>] \
  --user-agent AlibabaCloud-Agent-Skills

# Get workflow details
aliyun dataworks-public get-workflow \
  --region <REGION> \
  --id <WORKFLOW_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### Workflow Instance (Operations Center, read-only)

```bash
# Query workflow instance list
aliyun dataworks-public list-workflow-instances \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  --biz-date <BIZDATE_TIMESTAMP> \
  [--type Normal|Manual|SmokeTest|SupplementData|ManualWorkflow|TriggerWorkflow] \
  --user-agent AlibabaCloud-Agent-Skills

# Get workflow instance details
aliyun dataworks-public get-workflow-instance \
  --region <REGION> \
  --id <WORKFLOW_INSTANCE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### Alert Rules (Custom Monitoring, read-only)

```bash
# Query alert rule list
aliyun dataworks-public list-alert-rules \
  --region <REGION> \
  --page-number <PAGE_NUMBER> \
  --page-size <PAGE_SIZE> \
  [--name <RULE_NAME>] \
  [--owner <OWNER_UID>] \
  [--receiver <RECEIVER_UID>] \
  [--task-ids <ID1> <ID2> ...] \
  [--types <TYPE1> <TYPE2> ...] \
  --user-agent AlibabaCloud-Agent-Skills

# Get alert rule details
aliyun dataworks-public get-alert-rule \
  --region <REGION> \
  --id <ALERT_RULE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### Command Examples

```bash
# Step 1: Query failed task instances
aliyun dataworks-public list-task-instances \
  --region cn-hangzhou \
  --project-id 240863 \
  --bizdate 1775404800000 \
  --status Failure \
  --page-size 100 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: View instance log
aliyun dataworks-public get-task-instance-log \
  --region cn-hangzhou \
  --id <INSTANCE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

## Success Verification

1. **Query Verification**: `ListTaskInstances` returns a `TaskInstances` list, containing instance ID, status, task name, and other information
2. **Log Verification**: `GetTaskInstanceLog` returns a `TaskInstanceLog` field containing log content

For detailed verification steps, see [references/verification-method.md](references/verification-method.md)

## Cleanup

This skill does not create resources. No cleanup required.

## Best Practices

1. **Business Date Calculation**: `Bizdate` is typically the millisecond timestamp for 00:00:00 the day before the scheduling date
2. **Paginated Queries**: Use `--page-number` and `--page-size` for pagination, maximum 500 per page
3. **Pre-operation Check**: It is recommended to check instance logs first to confirm the status and avoid repeated failures

## References

| Document | Description |
|------|------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/related-commands.md](references/related-commands.md) | CLI command quick reference |
| [references/verification-method.md](references/verification-method.md) | Success verification methods |
| [related_apis.yaml](related_apis.yaml) | Full API list |
