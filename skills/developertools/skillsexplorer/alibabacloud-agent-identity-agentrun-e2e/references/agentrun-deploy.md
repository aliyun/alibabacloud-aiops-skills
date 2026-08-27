# AgentRun Runtime Deployment: Field Guide

The Runtime is created through the AgentRun console with a code package.
This guide lists every field with its verified value. Console labels are quoted
verbatim in Chinese — that is what the page shows — with an English gloss.

## Where

AgentRun console → `Agent 运行时` (Agent runtimes) → `创建` (create) →
`代码创建 Agent` (create Agent from code)

## Field-by-Field

| Field (console label) | English gloss | Value | Notes |
|---|---|---|---|
| `Agent 名称` | Agent name | e.g. `agent-e2e` | Any name; recorded as the runtime name |
| `描述` | description | optional | |
| `代码来源` | code source | `上传代码包` (upload code package) | Upload the zip built by `03_build.sh` |
| `运行时` | runtime | Python 3.12 | Must match the build's `--python-version 3.12` |
| `启动命令` | start command | `python3 main.py` | Default |
| `启动端口` | start port | `9000` | Default |
| `执行角色` | execution role | default (`aliyunagentrundefault...`) | Default is fine |
| `凭证配置` | credential config | **`AgentIdentity 身份提供商认证`** (AgentIdentity identity-provider authentication) → the IdP from 2.1 | This arms inbound OIDC + auto-creates the workload identity |
| `协议声明` | protocol declaration | skip | Not needed; the invocation path works without it |
| `环境变量` | environment variables | see below | JSON mode; paste whole |

## Environment Variables (minimal set — verified)

```json
{
  "PYTHONPATH": "/opt/python:/code/python",
  "MODEL_SERVICE_NAME": "<model card title>",
  "MODEL_NAME": "<model tag inside the card>",
  "TOOL_NAME": "<hosted MCP tool name(s), comma-separated>",
  "AGENT_IDENTITY_REGION_ID": "<region, e.g. cn-hangzhou>",
  "ENABLE_WEATHER_TOOL": "1",
  "ENABLE_OSS_TOOL": "1",
  "ENABLE_TIME_TOOL": "1",
  "ENABLE_SCHEDULE_TOOL": "1"
}
```

Rules (skill Execution Rule 9):
- `AGENT_IDENTITY_REGION_ID` is REQUIRED — both SDKs default to cn-beijing
  and local-tool credential fetch silently fails against the wrong region.
- `PYTHONPATH` must be included when pasting in JSON mode (it replaces the
  form values).
- NEVER add debug switches (`AGENTRUN_SDK_DEBUG`) or empty placeholders
  (`OAUTH_SCOPES=""`).
- Drop `SANDBOX_NAME` if the form pre-adds it (unused).
- A workload identity env is NOT needed — deploy auto-creates the identity.

## After Deploy

1. `04_reachability.sh` — constructs and probes the endpoint. Expected:
   `401 no ID token provided` (route + inbound auth armed).
2. `05_attach_role_policy.sh` — grants OSS read to the auto-created
   workload-identity role (Group C prerequisite).

## Invocation

```
POST https://<account>.agentrun-data.<region>.aliyuncs.com/agent-runtimes/
     <runtime>/endpoints/Default/invocations/openai/v1/chat/completions
Authorization: Bearer <id-token-from-user-idp>
Content-Type: application/json

{"messages":[{"role":"user","content":"..."}],"stream":false}
```

The OpenAI-style path after `/invocations` is required — the bare
`/invocations` 404s inside the app.

## Redeploys

Editing env vars or re-uploading the zip redeploys in place. Notes:
- The auto-created workload identity is per-runtime and survives redeploys.
- Stored OAuth2 tokens are keyed to the user+provider; a redeploy does not
  clear them, but tokens expire after 1 hour regardless — re-authorization
  prompts are normal on later runs.
