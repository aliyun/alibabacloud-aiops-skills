# AgentRun Runtime Deployment: Field Guide

The Runtime is created through the AgentRun console with a code package.
This guide lists the fields used by this sample. Console labels are quoted
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
| `环境变量` | environment variables | see below | JSON mode; preserve unrelated settings when reusing a Runtime |

## Environment Variables (minimal set — verified)

```json
{
  "PYTHONPATH": "/code/python:/opt/python",
  "MODEL_SERVICE_NAME": "<model card title>",
  "MODEL_NAME": "<model tag inside the card>",
  "TOOL_NAME": "<Alibaba-Cloud-API-MCP-tool-name>",
  "AGENT_IDENTITY_REGION_ID": "<region, e.g. cn-hangzhou>",
  "ENABLE_WEATHER_TOOL": "1",
  "ENABLE_OSS_TOOL": "1",
  "ENABLE_TIME_TOOL": "1",
  "ENABLE_SCHEDULE_TOOL": "1"
}
```

Rules (skill Execution Rule 9):
- Set `AGENT_IDENTITY_REGION_ID` to the deployment region so local tools request
  credentials from the correct region.
- `PYTHONPATH` must be included when pasting in JSON mode (it replaces the
  form values).
- NEVER add debug switches (`AGENTRUN_SDK_DEBUG`) or empty placeholders
  (`OAUTH_SCOPES=""`).
- Drop `SANDBOX_NAME` if the form pre-adds it (unused).
- A workload identity env is NOT needed — deploy auto-creates the identity.

## After Deploy

Wait for READY. Save `E2E_RUNTIME_NAME` and `AGENTRUN_REGION` using the commands
in SKILL.md Phase 3 before running the following scripts.

1. `04_reachability.sh` — constructs and probes the endpoint. Expected:
   `401 no ID token provided` (route + inbound auth armed).
2. `05_attach_role_policy.sh` — grants OSS read to the auto-created
   workload-identity role (Group C prerequisite). For a reused Runtime, retain
   whether the output reports an existing policy or a new attachment. Cleanup
   removes only a grant added by this run.

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

Editing environment variables or uploading a ZIP redeploys in place. Before
changing a reused Runtime, retain a deployable copy of its original ZIP or an
accessible original OSS bucket and object reference that can be redeployed.
Keep that code source available until restoration is verified. Language and
startup-command values alone cannot restore the code package.

Record the original `codeChecksum` from AgentRun console → `Agent 运行时` →
the Runtime → `概览`, plus its environment, credential, role, network, and log
configuration. If a restorable code source cannot be obtained, use a separate
test Runtime instead of overwriting the existing one. Preserve unrelated
settings and verify restoration as described in `cleanup.md` before cleanup.

Notes:
- The auto-created workload identity is per-runtime and survives redeploys.
- Stored OAuth2 tokens are keyed to the user+provider; a redeploy does not
  clear them. Token expiry depends on the provider configuration; later runs
  may require authorization again.
