# RAM authorization

## required_permissions

These actions are documented for the SysAgent operations below. The API references list Resource `"*"` for these actions; that does not authorize wildcard actions.

| RAM action | Why it is used |
| --- | --- |
| [`sysom:CreateCopilotSession`](https://help.aliyun.com/zh/alinux/api-sysom-2023-12-30-createcopilotsession) | Create a session when submitting new work without a session ID. |
| [`sysom:GetCopilotSession`](https://help.aliyun.com/zh/alinux/api-sysom-2023-12-30-getcopilotsession) | Read session metadata and refresh execution state. |
| [`sysom:ListCopilotSessions`](https://help.aliyun.com/zh/alinux/api-sysom-2023-12-30-listcopilotsessions) | Run the read-only readiness probe (`session list --limit 1`) and look up sessions when a task receipt is unavailable. |
| [`sysom:GenerateCopilotStreamResponse`](https://help.aliyun.com/zh/alinux/api-sysom-2023-12-30-generatecopilotstreamresponse) | Submit or observe cloud work through the SysAgent stream. |

The plugin uses [STS GetCallerIdentity](https://help.aliyun.com/zh/ram/developer-reference/api-sts-2015-04-01-getcalleridentity) internally to identify the caller and isolate local execution state. The Skill's separate STS troubleshooting probe is optional. The API reference does not list an authorization action for this call; do not request an additional RAM grant based on the API name.

On AccessDenied, keep the denied operation and request ID, explain the affected step, and ask the user's administrator to verify the exact permission and service availability. Do not repeat login, switch to another account, or request administrator or wildcard action access as a workaround. Permission to call the service is separate from the user's approval for a cloud-side change.
