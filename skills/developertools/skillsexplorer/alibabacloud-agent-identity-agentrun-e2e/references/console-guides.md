# Console Guides: Field-Verified Step-by-Step Flows

Every flow below was walked in the console during verification. Present them
to the user one step at a time (skill Execution Rules); verify results after
each step where an API/CLI check exists.

**Naming (Execution Rule 12):** at every step that creates a named resource,
first ask the user what to name it (offer a default suggestion). Two names
are FIXED by the sample code and must be stated as-is with the reason:

| Fixed name | Where | Why fixed |
|---|---|---|
| `test-provider-api-key` | API Key credential provider (2.5) | `weather_search.py` references this provider by name |
| `test-provider-for-mcp-oauth` | OAuth2 credential provider (2.2 step 2) | `get_current_time.py` references this name. Recommend creating the OAuth2 provider with EXACTLY this name — the same provider can also be bound to the MCP tools (one provider serves both the hosted-MCP chain and the local time tool) |

Everything else (IdP registration name, RAM app display name, OAuth2
provider name, MCP tool name, runtime name, policy set name) is the user's
choice — collect them up front or per step, and record each in the state.

## 2.1 Register the OIDC Identity Provider (inbound)

**Prefer the API path**: `E2E_IDP_NAME=<name> E2E_IDP_DISCOVERY_URL=<url>
bash scripts/01_prepare_identities.sh` creates (or reuses) the registration
automatically. The console flow below is the fallback.

AgentIdentity console → `身份提供商` → `创建身份提供商`. The page is OIDC-only —
there is NO "type" field to pick. Fields exactly as they appear on the page:

| Field (console label) | Value |
|---|---|
| `身份提供商名称` | User-chosen name (3–128 chars; letters, digits, `_`, `-`, `.`) |
| `描述` | Optional |
| `元数据地址` | The user's IdP discovery URL — an HTTPS URL ending with `/.well-known/openid-configuration`, no query parameters |
| `允许的受众` | Select `允许所有受众` (Allow all) — simplest. The alternative `指定受众白名单` requires listing every token `aud`; an unconfigured whitelist rejects ALL audience requests |

The user also needs a way to issue a test ID Token for one subject (e.g.
`sub=testuser`) from their IdP.

**Standard path note:** real users bring their own IdP — the skill only
needs these two things from them. A self-hosted discovery+JWKS pair on a
public OSS bucket is a testing-only fallback.

## 2.2 OAuth2 Three-Way Handshake (outbound credential chain)

Order matters — the callback URL only exists after step 2:

1. **RAM console** → `权限管理` → `OAuth 应用（公测）` → `创建应用`. Fields in order,
   exactly as the page shows:

   | Field (console label) | Value |
   |---|---|
   | `应用名称` | User-chosen (1–64 chars; auto-suffixed `@app.<account>.onaliyun.com`) |
   | `显示名称` | REQUIRED, 1–24 chars — suggest the same name |
   | `OAuth 协议版本` | **2.1** — the page DEFAULTS TO 2.0; you must switch it manually. Immutable after creation |
   | `应用类型` | Web `应用` |
   | `Access Token 有效期` | Default 3600 s |
   | `Refresh Token 有效期` | Default 2592000 s |
   | `回调地址` | Leave empty (filled back in step 3) |
   | `OAuth 范围` | Check `openid`, `aliuid`, `profile`. Then search the `筛选 OAuth 范围` box for `mcp`: check `/acs/mcp-server` if present; if the list offers no such scope, proceed with the three and record it |

   After creation, note the `应用` ID (Client ID).
2. **AgentIdentity console** → `出站` → `凭证提供商` → `创建凭证提供商`. Fields
   exactly as the page shows:

   | Field (console label) | Value |
   |---|---|
   | `凭证库` | default (leave as-is) — encrypts and stores tokens fetched via this provider |
   | `凭证提供商名称` | User-chosen (3–128 chars; letters/digits/`-`/`_`/`.`; unique per vault) |
   | `授权方式` | USER_FEDERATION `用户授权` (default-selected; immutable after creation) |
   | `回调地址` | Pre-generated on the page — copy it (also shown after creation) |
   | `描述` | Optional (≤128 chars) |
   | `供应商` | `阿里云` (Alibaba Cloud card; alternatives: `钉钉` / `飞书` / `自定义`) |
   | `客户端 ID` | Dropdown → select the RAM OAuth app created in step 1 |

   After saving, copy the generated callback URL (format
   `https://agentidentitydata.cn-hangzhou.aliyuncs.com/oauth2/callback/<uuid>`).
3. Backfill the callback into the **RAM app** — prefer the API (field-
   verified): re-run
   `E2E_RAM_APP_ID=<app-id> E2E_CALLBACK_URL=<url> bash scripts/01_prepare_identities.sh`
   (it verifies the backfill character-exact). Manual fallback: RAM app →
   `编辑` → `添加回调地址` → paste. Character-exact — a mismatched callback is
   the classic silent breaker of the whole chain.

## 2.3 Model Service (the agent's LLM)

Ask the user FIRST whether they already have a model service to reuse — NEVER
assume one exists and never tell the user what their account "already has";
the agent's memory of prior runs is not a source of truth about the user's
account. If the user has one, record the two values below. If not, walk them
through creation:

AgentRun console → `模型管理` → `添加大语言模型` (modal). Fields as the page
shows:

| Field (console label) | Value |
|---|---|
| `名称` | REQUIRED — must START with a letter or underscore (letters/digits/`_`/`-` only, no Chinese). A numeric date prefix like `08-16-model` is REJECTED — put the prefix after the word instead (e.g. `model-0816`) |
| `描述` | Optional |
| `工作空间` | `默认工作空间` (default) |
| `服务提供商` | `阿里云` |
| `API端点` | `https://dashscope.aliyuncs.com/compatible-mode/v1` (pre-filled) |
| `具体模型配置` | Keep the default selection (all listed models); the deploy env picks ONE via `MODEL_NAME` |
| `凭证配置` | Either `使用已有凭证` (if the account has one) or `API密钥` (paste the DashScope `sk-` key; link `获取百炼API KEY` on the page) |

After creation record BOTH:

- **service name** = the card title (env `MODEL_SERVICE_NAME`)
- **model name** = the model tag to use (env `MODEL_NAME`; e.g. `qwen-plus`) — must be among the card's selected models

These are two different values; swapping them fails with "model not found".

## 2.4 Register ALL Remote MCP Tools (console ONLY)

Register EVERY hosted MCP tool this run needs in this one phase — typically
two upstreams (Alibaba Cloud API MCP for Groups B/D, DingTalk Document MCP for
Group E). Each tool is one pass through the same console flow below.

### Where each upstream URL comes from (give the user these paths — never
just ask for "the URL")

**Never transcribe URLs/IDs** the agent must NOT retype these values
from screenshots (O/0, l/I/L confusions are guaranteed); always have the
USER copy-paste the value from the source page.

| Upstream | How to get the Streamable-HTTP URL |
|---|---|
| Alibaba Cloud API MCP (Groups B/D) | Open **https://api.aliyun.com/mcp** (API MCP Server page). **Configure OAuth on that page FIRST**: OAuth `配置` → select `自定义` OAuth → choose the RAM OAuth app created in 2.2 (shown as `<app-name>@app.<account>.onaliyun.com`). This aligns the upstream with the Provider chain — without it the B/D authorization flow cannot work. (The alternative `阿里云官方` OAuth requires an admin to install the official API MCP Server app under RAM → OAuth `应用` → `第三方应用` — the yellow warning on the page refers to that path.) Then copy the `公网` Streamable HTTP Endpoint: `https://openapi-mcp.cn-hangzhou.aliyuncs.com/id/<instance-id>/mcp` |
| DingTalk Document MCP (Group E) | Open https://mcp.dingtalk.com → log in with a DingTalk account → pick the document service → `复制` Streamable HTTP URL (`https://mcp-gw.dingtalk.com/server/<id>?key=...`). The `?key=` is personal — treat it as a secret |

### Console flow (repeat once per tool)

AgentRun console → `工具与Skills` → `创建` → **first select the "MCP" type
card** (the page offers `技能` / `MCP` / `函数调用` / `工具市场`) → `创建方式` = `远程连接`:

| Field (console label) | Value |
|---|---|
| `MCP 名称` | REQUIRED — must START with a letter or underscore (a numeric prefix like `08-16-mcp` is REJECTED — use the date-suffix style `mcp-0816` / `dingtalk-0816`) |
| `描述` | Optional (≤256 chars) |
| `MCP 配置` | Replace the template block with the verified JSON below (the page's example may show `"transportType": "sse"` — replace the WHOLE block) |
| `MCP 代理` | No manual action — turning on Agent Identity auth auto-enables the proxy (`一键部署` fills the Hook config) |
| `Agent Identity 身份认证` | ON → click `一键部署` |
| `凭证提供商` | Two-step dropdown: first pick the provider TYPE (OAuth2), then select the provider created in 2.2 |
| `Agent Identity 权限控制` | Recommend OFF at creation — ON with no bound policy set rejects ALL calls to the tool; enable + bind in Phase 4 |
| `访问凭证` | Auto-disabled once Agent Identity auth is on (shows `匿名访问`) — expected, leave as-is |

**Verified JSON block** — the console example pre-fills `"transportType":
"sse"`; replace the WHOLE block:

```json
{
  "mcpServers": {
    "<server-key>": {
      "transportType": "streamable-http",
      "url": "<upstream-mcp-url>"
    }
  }
}
```

**Never register MCP tools via the CreateTool API**: identical payloads
produce a tool whose data-plane route never activates (500 missing
X-AgentRun-Mcp-Tool-Arn) and which later self-deletes. Console only.

## 2.5 API Key Credential Provider (Group A)

AgentIdentity console → `出站` → `凭证提供商` → `创建`: type **API Key**, name
exactly `test-provider-api-key` (the sample's weather tool references this
name). Key value is arbitrary — the mock tool only verifies non-empty
injection.

**Name collision = reuse:** the name is fixed by the sample code and unique
per account. If the console says it already exists (a prior run created it),
do NOT create another — verify it exists (agent check or console) and reuse
it as-is.

## 2.6 OSS Test File (Group C)

Automated — `scripts/02_oss_testfile.sh` creates bucket
`e2e-test-<account>` + `hello.txt` and reads it back.

## 3. Runtime Creation

See `agentrun-deploy.md` for the full field guide.

## 4.x Bind the Cedar Policy Set (console, exact flow — verified 08-16)

Binding happens on the **AgentIdentity side** (policy set → associate the
AgentRun MCP resource), NOT by picking a policy set inside the tool's edit
page. Exact flow, in order:

1. AgentRun console → `工具与Skills` → the MCP tool → `编辑` → enable
   **`Agent Identity 权限控制`** → **`保存`** (just the switch — there is no
   policy-set picker on this page).
2. On the saved page, click **`前往 Agent Identity 控制台`** (the jump link
   the page offers).
3. AgentIdentity console → `权限` → `策略集` → open the policy set (e.g.
   `policy-0816`).
4. Click **`关联资源` / `绑定资源`** → choose **AgentRun MCP** → select the tool
   (e.g. `mcp-0816`).
5. Choose the **`执行模式`** → **`拦截模式`** (enforcing) → confirm the binding.
6. Done. Verify by listing tools: unpermitted subtools vanish from the list
   (partial evaluation) and out-of-condition calls are rejected.

## Group E: DingTalk MCP wiring

The DingTalk tool itself is registered in 2.4 (upstream URL from
mcp.dingtalk.com, same console flow). After the Runtime is deployed: append
the DingTalk tool name to the Runtime's `TOOL_NAME` (comma-separated),
redeploy, then verify with the checklist's Group E case — first use asks for
authorization (the usual link); after that, `create_document` returns a real
document URL.
