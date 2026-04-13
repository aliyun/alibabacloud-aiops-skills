# CLI Command Quick Reference

## DataWorks Operations Commands

## Task Management

### Query Task List

```bash
aliyun dataworks-public list-tasks \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  [--ids <ID1> <ID2> ...] \
  [--name <TASK_NAME>] \
  [--owner <OWNER_ACCOUNT_ID>] \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  [--project-env Prod|Dev] \
  [--sort-by "Id Desc"] \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Description:**

| Parameter | Type | Description |
|------|------|------|
| `--region` | String | Target region (required), e.g., cn-hangzhou |
| `--project-id` | Long | Workspace ID (required) |
| `--ids` | Array[Long] | Task ID list |
| `--name` | String | Task name (supports fuzzy matching) |
| `--owner` | String | Task owner account ID |
| `--page-size` | Integer | Items per page, default 10 |
| `--page-number` | Integer | Page number, default 1 |
| `--project-env` | String | Workspace environment: Prod/Dev |
| `--sort-by` | String | Sort order, e.g., "Id Desc", "ModifyTime Desc" |

### Get Task Details

```bash
aliyun dataworks-public get-task \
  --region <REGION> \
  --id <TASK_ID> \
  [--project-env Prod|Dev] \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Description:**

| Parameter | Type | Description |
|------|------|------|
| `--region` | String | Target region (required) |
| `--id` | Long | Task ID (required) |
| `--project-env` | String | Workspace environment: Prod/Dev |

### Query Upstream/Downstream Tasks

```bash
aliyun dataworks-public list-upstream-tasks \
  --region <REGION> \
  --id <TASK_ID> \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  [--project-env Prod|Dev] \
  --user-agent AlibabaCloud-Agent-Skills

aliyun dataworks-public list-downstream-tasks \
  --region <REGION> \
  --id <TASK_ID> \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  [--project-env Prod|Dev] \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Task Operation Logs

```bash
aliyun dataworks-public list-task-operation-logs \
  --region <REGION> \
  --id <TASK_ID> \
  [--date <UNIX_TIMESTAMP_MS>] \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  [--project-env Prod|Dev] \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Task Instance Management

### Query Task Instance List

```bash
aliyun dataworks-public list-task-instances \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  --bizdate <BIZDATE_TIMESTAMP> \
  [--status <STATUS>] \
  [--task-name <TASK_NAME>] \
  [--owner <OWNER_ACCOUNT_ID>] \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  [--project-env Prod|Dev] \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Description:**

| Parameter | Type | Description |
|------|------|------|
| `--region` | String | Target region (required), e.g., cn-hangzhou |
| `--project-id` | Long | Workspace ID (required) |
| `--bizdate` | Long | Business date, millisecond timestamp (required) |
| `--status` | String | Instance status: NotRun/Running/Failure/Success/WaitTime/WaitResource |
| `--task-name` | String | Task name (supports fuzzy search) |
| `--owner` | String | Task owner account ID |
| `--page-size` | Integer | Items per page, default 10 |
| `--page-number` | Integer | Page number, default 1 |
| `--project-env` | String | Workspace environment: Prod/Dev |

### Get Task Instance Details

```bash
aliyun dataworks-public get-task-instance \
  --region <REGION> \
  --id <TASK_INSTANCE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Get Instance Log

```bash
aliyun dataworks-public get-task-instance-log \
  --region <REGION> \
  --id <TASK_INSTANCE_ID> \
  [--run-number <RUN_NUMBER>] \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Description:**

| Parameter | Type | Description |
|------|------|------|
| `--region` | String | Target region (required) |
| `--id` | Long | Task instance ID (required) |
| `--run-number` | Integer | Run number, minimum 1, defaults to latest |

### Query Upstream/Downstream Task Instances

```bash
aliyun dataworks-public list-upstream-task-instances \
  --region <REGION> \
  --id <TASK_INSTANCE_ID> \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  --user-agent AlibabaCloud-Agent-Skills

aliyun dataworks-public list-downstream-task-instances \
  --region <REGION> \
  --id <TASK_INSTANCE_ID> \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Task Instance Operation Logs

```bash
aliyun dataworks-public list-task-instance-operation-logs \
  --region <REGION> \
  --id <TASK_INSTANCE_ID> \
  [--date <UNIX_TIMESTAMP_MS>] \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Workflow (Operations Center, read-only)

### Get Workflow Details

```bash
aliyun dataworks-public get-workflow \
  --region <REGION> \
  --id <WORKFLOW_ID> \
  [--env-type Prod|Dev] \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Workflow List

```bash
aliyun dataworks-public list-workflows \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  [--name <WORKFLOW_NAME>] \
  [--owner <OWNER_ACCOUNT_ID>] \
  [--ids <ID1> <ID2> ...] \
  [--tags <TAG1> <TAG2> ...] \
  [--trigger-type Scheduler|Manual|TriggerWorkflow] \
  [--env-type Prod|Dev] \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  [--sort-by "Id Desc"] \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Workflow Instance (Operations Center, read-only)

### Query Workflow Instance List

```bash
aliyun dataworks-public list-workflow-instances \
  --region <REGION> \
  --project-id <PROJECT_ID> \
  --biz-date <BIZDATE_TIMESTAMP> \
  [--name <INSTANCE_NAME>] \
  [--owner <OWNER_ACCOUNT_ID>] \
  [--type Normal|Manual|SmokeTest|SupplementData|ManualWorkflow|TriggerWorkflow] \
  [--workflow-id <WORKFLOW_ID>] \
  [--ids <ID1> <ID2> ...] \
  [--tags <TAG1> <TAG2> ...] \
  [--unified-workflow-instance-id <UNIFIED_ID>] \
  [--filter '<FILTER_JSON>'] \
  [--page-size <SIZE>] \
  [--page-number <NUMBER>] \
  [--sort-by "Id Desc"] \
  --user-agent AlibabaCloud-Agent-Skills
```

### Get Workflow Instance Details

```bash
aliyun dataworks-public get-workflow-instance \
  --region <REGION> \
  --id <WORKFLOW_INSTANCE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Common Query Commands

### Query Failed Instances

```bash
# Get business date (yesterday 00:00:00 timestamp)
BIZDATE=$(($(date -j -v-1d -f "%Y-%m-%d" "$(date +%Y-%m-%d)" "+%s") * 1000))

aliyun dataworks-public list-task-instances \
  --region cn-hangzhou \
  --project-id 240863 \
  --bizdate $BIZDATE \
  --status Failure \
  --page-size 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query by Task Name

```bash
aliyun dataworks-public list-task-instances \
  --region cn-hangzhou \
  --project-id <PROJECT_ID> \
  --bizdate <BIZDATE> \
  --task-name "ods_user_log" \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Alert Rules (Custom Monitoring, read-only)

### Query Alert Rule List

```bash
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
```

**Parameter Description:**

| Parameter | Type | Description |
|------|------|------|
| `--region` | String | Target region (required), e.g., cn-hangzhou |
| `--page-number` | Int | Page number (required), minimum 1 |
| `--page-size` | Int | Items per page (required), maximum 100 |
| `--name` | String | Custom rule name (supports filtering) |
| `--owner` | String | Rule owner Alibaba Cloud UID |
| `--receiver` | String | Alert receiver Alibaba Cloud UID |
| `--task-ids` | List | Scheduled task ID list |
| `--types` | List | Alert trigger type list |

### Get Alert Rule Details

```bash
aliyun dataworks-public get-alert-rule \
  --region <REGION> \
  --id <ALERT_RULE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Description:**

| Parameter | Type | Description |
|------|------|------|
| `--region` | String | Target region (required) |
| `--id` | String | Custom alert rule ID (required) |
