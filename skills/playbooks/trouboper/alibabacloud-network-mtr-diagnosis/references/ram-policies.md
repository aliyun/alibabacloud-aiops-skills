# Required RAM Permissions

The **automated mode** (Cloud Assistant) of this Skill remotely executes diagnostic commands on ECS instances via Cloud Assistant, which involves remote command execution permissions. Manual mode requires no permissions.

> **Security note**: The `ecs:run-command` action allows executing arbitrary scripts on ECS instances. This Skill only executes diagnostic commands (mtr, ping, curl), and requires user confirmation before each run-command invocation via a PreToolUse Hook.

## Custom Policy (Recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:describe-instances",
        "ecs:describe-cloud-assistant-status",
        "ecs:describe-invocation-results"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:run-command"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note**: The JSON above uses plugin-mode (kebab-case) notation for readability. The actual RAM policy uses PascalCase notation. Refer to [Alibaba Cloud RAM documentation](https://www.alibabacloud.com/help/en/ram) for the canonical action names.

## System Policies

- `AliyunECSReadOnlyAccess` — Covers read-only operations (describe-instances, describe-cloud-assistant-status, describe-invocation-results)
- `ecs:run-command` requires a custom policy; no built-in system policy covers it

## Permission Descriptions

| API Action (plugin mode) | Type | Purpose |
|-----------|------|---------|
| `ecs:describe-instances` | Read-only | Query ECS instance basic info (confirm instance exists and status is Running) |
| `ecs:describe-cloud-assistant-status` | Read-only | Check whether Cloud Assistant agent is installed and running on the target ECS |
| `ecs:describe-invocation-results` | Read-only | Retrieve remote command execution results (stdout/stderr/status) |
| `ecs:run-command` | **Execute** | Remotely execute diagnostic scripts on ECS (install mtr, run MTR/ping/curl) |

## Least Privilege Recommendations

To restrict the scope of run-command execution, you can specify instance ARNs in the Resource field:

```json
{
  "Effect": "Allow",
  "Action": ["ecs:run-command"],
  "Resource": [
    "acs:ecs:cn-hangzhou:*:instance/i-bp1xxxxxxxxxxxx"
  ]
}
```
