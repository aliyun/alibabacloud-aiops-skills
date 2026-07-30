# Required RAM Permissions

The **automated mode** (Cloud Assistant) of this Skill remotely executes diagnostic commands on ECS instances via Cloud Assistant, which involves remote command execution permissions. Manual mode requires no permissions.

> **Security note**: The `ecs:RunCommand` action allows executing arbitrary scripts on ECS instances. This Skill only executes diagnostic commands (mtr, ping, curl), and requires user confirmation before each RunCommand invocation via a PreToolUse Hook.

## Custom Policy (Recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocationResults"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunCommand"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note**: The action names above use the canonical PascalCase RAM notation and can be used in RAM policies as-is. Refer to [Alibaba Cloud RAM documentation](https://www.alibabacloud.com/help/en/ram) for details.

## System Policies

- `AliyunECSReadOnlyAccess` — Covers read-only operations (DescribeInstances, DescribeCloudAssistantStatus, DescribeInvocationResults)
- `ecs:RunCommand` requires a custom policy; no built-in system policy covers it

## Permission Descriptions

| API Action (RPC API) | Type | Purpose |
|-----------|------|---------|
| `ecs:DescribeInstances` | Read-only | Query ECS instance basic info (confirm instance exists and status is Running) |
| `ecs:DescribeCloudAssistantStatus` | Read-only | Check whether Cloud Assistant agent is installed and running on the target ECS |
| `ecs:DescribeInvocationResults` | Read-only | Retrieve remote command execution results (stdout/stderr/status) |
| `ecs:RunCommand` | **Execute** | Remotely execute diagnostic scripts on ECS (install mtr, run MTR/ping/curl) |

## Least Privilege Recommendations

To restrict the scope of RunCommand execution, you can specify instance ARNs in the Resource field:

```json
{
  "Effect": "Allow",
  "Action": ["ecs:RunCommand"],
  "Resource": [
    "acs:ecs:cn-hangzhou:*:instance/i-bp1xxxxxxxxxxxx"
  ]
}
```
