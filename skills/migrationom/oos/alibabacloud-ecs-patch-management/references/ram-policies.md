# RAM Policies: ECS Patch Management via OOS

This document lists all RAM permissions required for scanning and installing OS patches on ECS instances using Alibaba Cloud OOS (Operation Orchestration Service).

---

## Required RAM Policies

### 1. OOS Service Permissions

| Action | Description | Required For |
|--------|-------------|--------------|
| `oos:StartExecution` | Start an OOS execution | Scanning and installing patches |
| `oos:ListExecutions` | List OOS executions | Checking execution status |
| `oos:GetExecution` | Get execution details | Checking execution result |
| `oos:ListExecutionLogs` | List execution logs | Viewing patch operation logs |
| `oos:ListTaskExecutions` | List task executions | Monitoring task progress |
| `oos:CancelExecution` | Cancel an execution | Stopping patch operations |
| `oos:ListTemplates` | List available templates | Verifying template availability |
| `oos:GetTemplate` | Get template details | Verifying template configuration |

### 2. ECS Instance Permissions

| Action | Description | Required For |
|--------|-------------|--------------|
| `ecs:DescribeInstances` | Query ECS instance information | Verifying target instances exist |
| `ecs:DescribeInvocations` | Query Cloud Assistant invocations | Checking Cloud Assistant command execution |
| `ecs:DescribeInvocationResults` | Query Cloud Assistant invocation results | Checking patch installation results |
| `ecs:SendCommand` | Send Cloud Assistant commands | Executing patch commands on instances |

### 3. Snapshot Permissions (Optional - when `whetherCreateSnapshot=true`)

| Action | Description | Required For |
|--------|-------------|--------------|
| `ecs:CreateSnapshot` | Create a disk snapshot | Creating pre-patch snapshots |
| `ecs:DeleteSnapshot` | Delete a disk snapshot | Cleaning up old snapshots |
| `ecs:DescribeSnapshots` | Query snapshot information | Verifying snapshot status |

### 4. Patch Baseline Permissions

| Action | Description | Required For |
|--------|-------------|--------------|
| `oos:ListPatchBaselines` | List patch baselines | Viewing available patch baselines |
| `oos:GetPatchBaseline` | Get patch baseline details | Verifying patch baseline configuration |
| `oos:ListInstancePatches` | List instance patches | Querying patch status on instances |
| `oos:ListInstancePatchStates` | List instance patch states | Checking patch compliance states |

---

## Pre-built Policy

Alibaba Cloud provides a pre-built policy that covers most OOS operations:

- **`AliyunOOSFullAccess`** — Full access to OOS service
- **`AliyunECSFullAccess`** — Full access to ECS service (includes Cloud Assistant and Snapshot operations)

For production environments, it is recommended to create a custom policy with the minimum required permissions listed above.

---

## Custom Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oos:StartExecution",
        "oos:ListExecutions",
        "oos:GetExecution",
        "oos:ListExecutionLogs",
        "oos:ListTaskExecutions",
        "oos:CancelExecution",
        "oos:ListTemplates",
        "oos:GetTemplate",
        "oos:ListPatchBaselines",
        "oos:GetPatchBaseline",
        "oos:ListInstancePatches",
        "oos:ListInstancePatchStates"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInvocations",
        "ecs:DescribeInvocationResults",
        "ecs:SendCommand"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:CreateSnapshot",
        "ecs:DeleteSnapshot",
        "ecs:DescribeSnapshots"
      ],
      "Resource": ["*"]
    }
  ]
}
```

---

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
