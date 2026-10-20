# OpenAgent client API permissions

Client API access and cloud resource execution are separate permission boundaries.
This Skill uses only these seven OpenAgent actions:

| Purpose | OpenAgent RAM actions |
| --- | --- |
| Read conversations, messages, and Run state | `openagent:ListSessions`, `openagent:GetSession`, `openagent:ListMessages`, `openagent:GetRun` |
| Submit work or reply in a conversation | `openagent:CreateSession`, `openagent:SendMessage` |
| Cancel the exact Run requested by the user | `openagent:CancelRun` |

`setup configure` saves only local connection settings and needs no cloud API permission.
`SendMessage` is required even for a query-only business request; it does not restrict execution to reads.

Cloud-side tools separately need the execution identity's effective permissions for the exact product actions and resources, together with the user's concrete authorization for changes. OpenAgent client API access grants neither those resource permissions nor that authorization.
