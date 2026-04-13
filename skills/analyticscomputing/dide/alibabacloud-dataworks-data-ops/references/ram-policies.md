# RAM Permission List

RAM permissions required for this skill:

## Task Management Permissions

| Permission Action | Description |
|------------|------|
| `dataworks:GetTask` | Get task details |
| `dataworks:ListTasks` | Query task list |
| `dataworks:ListUpstreamTasks` | Query upstream task list |
| `dataworks:ListDownstreamTasks` | Query downstream task list |
| `dataworks:ListTaskOperationLogs` | Query task operation logs |

## Task Instance Management Permissions

| Permission Action | Description |
|------------|------|
| `dataworks:ListTaskInstances` | Query task instance list |
| `dataworks:GetTaskInstance` | Get task instance details |
| `dataworks:GetTaskInstanceLog` | Get task instance execution log |
| `dataworks:ListUpstreamTaskInstances` | Query upstream task instances |
| `dataworks:ListDownstreamTaskInstances` | Query downstream task instances |
| `dataworks:ListTaskInstanceOperationLogs` | Query task instance operation logs |

## Workflow (Operations Center) Permissions

| Permission Action | Description |
|------------|------|
| `dataworks:GetWorkflow` | Get workflow details |
| `dataworks:ListWorkflows` | Query workflow list |

## Workflow Instance (Operations Center) Permissions

| Permission Action | Description |
|------------|------|
| `dataworks:ListWorkflowInstances` | Query workflow instance list |
| `dataworks:GetWorkflowInstance` | Get workflow instance details |

## Alert Rule (Custom Monitoring) Permissions

| Permission Action | Description |
|------------|------|
| `dataworks:ListAlertRules` | Query alert rule list |
| `dataworks:GetAlertRule` | Get alert rule details |

## Recommended Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:GetTask",
        "dataworks:ListTasks",
        "dataworks:ListUpstreamTasks",
        "dataworks:ListDownstreamTasks",
        "dataworks:ListTaskOperationLogs",
        "dataworks:ListTaskInstances",
        "dataworks:GetTaskInstance",
        "dataworks:GetTaskInstanceLog",
        "dataworks:ListUpstreamTaskInstances",
        "dataworks:ListDownstreamTaskInstances",
        "dataworks:ListTaskInstanceOperationLogs",
        "dataworks:GetWorkflow",
        "dataworks:ListWorkflows",
        "dataworks:ListWorkflowInstances",
        "dataworks:GetWorkflowInstance",
        "dataworks:ListAlertRules",
        "dataworks:GetAlertRule"
      ],
      "Resource": "*"
    }
  ]
}
```

## Principle of Least Privilege

To restrict to a specific workspace, replace `Resource` with:

```json
"Resource": [
  "acs:dataworks:<region>:<account-id>:project/<project-id>"
]
```

## Permission Check Command

```bash
# Check current account identity
aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills
```
