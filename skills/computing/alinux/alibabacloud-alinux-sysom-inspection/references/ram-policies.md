# RAM Policies: alibabacloud-alinux-sysom-inspection

This Skill uses the sysom-osops CLI. Remote diagnosis is routed through SysOM
OpenAPI gateway actions.

## Required Permissions

| API | RAM Action | Used by | Description |
|-----|------------|---------|-------------|
| InitialSysom | `sysom:InitialSysom` | Credential validation inside remote commands | Verify credential validity and SysOM role authorization |
| InvokeAgentCli | `sysom:InvokeAgentCli` | All remote diagnosis commands | Gateway action for catalog queries, diagnosis execution, and task polling |
| CreateServiceLinkedRole | `ram:CreateServiceLinkedRole` | First-time SysOM service activation | Create the SysOM service-linked role (SLR). Only needed on first activation. |

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sysom:InitialSysom",
        "sysom:InvokeAgentCli"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ram:CreateServiceLinkedRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ram:ServiceName": "sysom.aliyuncs.com"
        }
      }
    }
  ]
}
```

## Notes

- `sysom-osops memory classify` runs locally and does not require cloud
  permissions.
- Remote commands across memory, IO, network, load, and Java memory require the
  permissions above.
- `ram:CreateServiceLinkedRole` is only required when activating SysOM for the
  first time. Once the service-linked role exists, subsequent calls succeed
  without this permission.
- Avoid broader wildcard permissions when a custom least-privilege policy can be
  attached to the RAM user or ECS RAM Role.
- Do not paste AK/SK values into the conversation. Configure credentials outside
  the Agent session.
