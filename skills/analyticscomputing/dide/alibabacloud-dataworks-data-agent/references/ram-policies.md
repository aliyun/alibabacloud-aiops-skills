# RAM Policies

This Skill interacts with DataWorks Data Agent APIs via aliyun CLI.
The aliyun CLI profile must have the following permissions.

## Required Permissions

| API Action | RAM Permission | Description |
|---|---|---|
| CreateAgentSession | `dataworks:CreateAgentSession` | Create a new Agent session |
| PromptAgentSession | `dataworks:PromptAgentSession` | Send prompt to a session |
| LoadAgentSession | `dataworks:LoadAgentSession` | Load session history |
| ListAgentSessions | `dataworks:ListAgentSessions` | List sessions for an agent |
| ListAgentSessionArtifacts | `dataworks:ListAgentSessionArtifacts` | List session artifacts |
| GetAgentSessionArtifactMeta | `dataworks:GetAgentSessionArtifactMeta` | Get artifact content |
| GetAgentSessionTokenUsage | `dataworks:GetAgentSessionTokenUsage` | Query token usage |
| CancelAgentSession | `dataworks:CancelAgentSession` | Cancel a session |

## RAM Policy Statement

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateAgentSession",
        "dataworks:PromptAgentSession",
        "dataworks:LoadAgentSession",
        "dataworks:ListAgentSessions",
        "dataworks:ListAgentSessionArtifacts",
        "dataworks:GetAgentSessionArtifactMeta",
        "dataworks:GetAgentSessionTokenUsage",
        "dataworks:CancelAgentSession"
      ],
      "Resource": "acs:dataworks:{#regionId}:{#accountId}:*"
    }
  ]
}
```

`{#regionId}` and `{#accountId}` are RAM template variables, automatically resolved to the caller's region and account UID.

## Notes

- No wildcard Agent management permissions (list-agents, create-agent, delete-agent) are required.
- The `Resource` field uses resource-level ARN `acs:dataworks:{#regionId}:{#accountId}:*` — RAM template variables restrict to caller's region and account.
- Credentials are managed by aliyun CLI profiles, not by this Skill.
