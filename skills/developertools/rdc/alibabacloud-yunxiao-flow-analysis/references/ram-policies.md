# RAM Policies: Yunxiao Flow Pipeline Troubleshooting

## Authentication Mode

> **Note:** This skill does **NOT** use Alibaba Cloud AK/SK credentials or the `aliyun` CLI.
> All API calls are authenticated via **Yunxiao Personal Access Token (PAT)**, passed through the `x-yunxiao-token` HTTP header.
> Therefore, no Alibaba Cloud RAM policies need to be attached to the user's RAM account for this skill to function.

## Yunxiao Flow Permission Requirements

Permissions are managed within the **Yunxiao (云效)** platform, not through Alibaba Cloud RAM. The user must have the following Yunxiao organization-level permissions:

| Permission Scope | Access Level | Description |
|-----------------|-------------|-------------|
| Flow Pipeline (流水线) | Read-only | View pipeline configurations and definitions |
| Flow Pipeline Runs (流水线运行记录) | Read-only | View pipeline run details, stages, jobs, and steps |
| Flow Pipeline Logs (流水线运行日志) | Read-only | View pipeline job step execution logs |
| Flow Deploy Orders (部署单) | Read-only | View VM deployment order details and machine status |
| Flow Deploy Machine Logs (部署机器日志) | Read-only | View individual machine deployment logs |
| Flow Web Terminal (调试终端) | Read-only | Connect to build container debug terminal (read-only commands only) |

## APIs Used

| API | HTTP Method | Description | Script |
|-----|------------|-------------|--------|
| GetPipelineRun | GET | Get pipeline run details (status, stages, jobs, steps) | `yunxiao_flow_get_pipeline_runs.py` |
| GetPipelineJobSteps | GET | Get step details under a specific job | `yunxiao_flow_get_pipeline_runs.py` |
| GetPipelineJobStepLog | GET | Get pipeline job step execution logs | `yunxiao_flow_get_job_step_log.py` |
| GetVmDeployOrder | GET | Get VM deployment order details and machine list | `yunxiao_flow_get_vm_deploy_order.py` |
| GetVmDeployMachineLog | GET | Get individual machine deployment logs | `yunxiao_flow_get_vm_deploy_machine_log.py` |
| WebTerminal (WebSocket) | WSS | Connect to build container debug terminal | `webTerminal.py` |

> All APIs are **read-only** operations. This skill does not perform any write, create, update, or delete operations on pipeline resources.

## How to Obtain a Personal Access Token (PAT)

1. Log in to [Yunxiao Console](https://devops.aliyun.com)
2. Navigate to **Personal Settings** > **Personal Access Tokens**
3. Create a new token with **Flow Pipeline read-only** permissions
4. Set the token via environment variable or command-line argument:
   ```bash
   export YUNXIAO_ACCESS_TOKEN="pt-xxxxxxxxxxxxx"
   ```

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any API call fails due to permission errors (HTTP 403 or authorization-related error messages) at any point during execution, follow this process:
> 1. Read this file (`references/ram-policies.md`) to get the full list of permissions required by this skill
> 2. Verify that the Yunxiao Personal Access Token has the necessary Flow Pipeline read-only permissions
> 3. Guide the user to check their token permissions in **Yunxiao Console > Personal Settings > Personal Access Tokens**
> 4. Pause and wait until the user confirms that the required permissions have been granted or a new token with correct permissions has been created

## Alibaba Cloud RAM Policy (Not Required)

Since this skill exclusively uses Yunxiao PAT authentication and does not invoke any Alibaba Cloud OpenAPI via AK/SK or STS Token, **no Alibaba Cloud RAM policy attachment is required**.

If users encounter access issues, the problem is typically related to:
- Expired or invalid PAT token
- Insufficient Yunxiao organization permissions for the token
- Incorrect organization ID or API domain mismatch
