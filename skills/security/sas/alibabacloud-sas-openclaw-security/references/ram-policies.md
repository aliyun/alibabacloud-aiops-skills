# RAM Permission Policy Reference

This Skill calls Alibaba Cloud Security Center (SAS), Elastic Compute Service (ECS), and AI Security Center (AISC) via the aliyun CLI, operating in the AIOps domain. The running account (RAM user or RAM role) must be granted the following minimum permissions.

## Required RAM Actions

### Security Center (SAS)

| Action | Caller | Purpose |
|--------|--------|---------|
| `yundun-sas:DescribePropertyScaDetail` | `sas_client` | Query SCA component instance list |
| `yundun-sas:DescribeVulList` | `sas_client` | Query vulnerability list |
| `yundun-sas:ModifyPushAllTask` | `sas_client` | Push vulnerability and baseline check tasks |
| `yundun-sas:DescribeCheckWarningSummary` | `sas_client` | Query baseline check summary |
| `yundun-sas:DescribeCheckWarnings` | `sas_client` | Query baseline check details |
| `yundun-sas:DescribeSuspEvents` | `sas_client` | Query alert events |
| `yundun-sas:GetAssetDetailByUuid` | `sas_client` | Query asset details by UUID |

### Elastic Compute Service (ECS)

| Action | Caller | Purpose |
|--------|--------|---------|
| `ecs:CreateCommand` | `ecs_client` | Create a Cloud Assistant command |
| `ecs:RunCommand` | `ecs_client` | Dispatch a command via Cloud Assistant |
| `ecs:DescribeInvocationResults` | `ecs_client` | Query Cloud Assistant command execution results |

### AI Security Center (AISC)

| Action | Caller | Purpose |
|--------|--------|---------|
| `aisc:GetAIAgentPluginKey` | `aisc_client` | Retrieve the AI Security Assistant installation key |


## Authorization Notes

- **Read-only operations** (`Describe*`, `Get*`): Do not modify any resources. Low risk; can be opened to `Resource: "*"` as needed.
- **Write operations** (`ModifyPushAllTask`, `ecs:RunCommand`): Trigger task dispatching or execute commands on remote machines. It is recommended to restrict the ECS Resource to a specific instance ARN:
  ```
  acs:ecs:<region>:<account-id>:instance/<instance-id>
  ```

## Reference Documentation

- [Security Center RAM Authentication](https://help.aliyun.com/zh/security-center/developer-reference/api-authentication-rules)
- [ECS RAM Authentication](https://help.aliyun.com/zh/ecs/developer-reference/authentication-rules-for-ecs-api)
- [RAM Custom Policies](https://help.aliyun.com/zh/ram/user-guide/create-a-custom-policy)
