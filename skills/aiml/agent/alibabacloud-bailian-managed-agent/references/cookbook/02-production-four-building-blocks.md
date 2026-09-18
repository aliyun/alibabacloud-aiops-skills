

> Execution safety: legacy shell examples below illustrate wire fields. When using real credentials, construct and send JSON in-process from a secret store/environment; do not interpolate secrets into command arguments, print request bodies, enable shell tracing, or use a receiver that echoes Authorization. Verify only that an allowlisted service authenticates successfully. A sandbox check should return a boolean placeholder check, never raw `printenv` output. See [CLI/API routing](../workflows/cli-api-routing.md).

> This recipe covers productionizing on Bailian Managed Agents: MCP toolkit integration (marketplace registration), config injection (session environment variables + the Vault secret store), platform-managed triggering (Deployment: manual / cron / initial_events), human approval (HITL), resource lifecycle management, and the current data-residency behavior. Examples uniformly use curl; every key API shape is field-tested (2026-09, Bailian cn-beijing region).
>
> **The deep dive on credential injection (the Vault placeholder security model, the egress gateway, allowed_hosts) has been split into [08-vault-secret-injection-and-egress-gateway.md](08-vault-secret-injection-and-egress-gateway.md)** — this recipe only wires credentials up the shortest way.

## Scenario: Yunling Tea's morning-brief bot

"Yunling Tea" is a fictional chain tea-drink brand. The first thing its operations team does every morning is scan the industry: what new products competitors launched, what is stirring in the supply chain, whether any negative press involves tea drinks. Repetitive, time-consuming, easy to miss — a textbook task for automation. We will build a **morning-brief bot** chaining together the production building blocks:

| Need | Capability |
|---|---|
| Runs automatically at 7:30 every morning, unattended | **Deployment** (cron-scheduled triggers) |
| Carries the day's task instructions at trigger time | **Deployment** (`initial_events` delivered at trigger) |
| Search industry news | **MCP toolkit** (the marketplace WebSearch service) |
| Push the brief to the company GitHub repo | **Vault secret store** (injecting `GITHUB_TOKEN`, placeholder + egress-gateway replacement; see 08) |
| On major negative press, stop and wait for human confirmation | **HITL** (`requires_action` + polling) |
| Change the prompt seasonally, deactivate at quarter end, clean up resources | **Version management + resource lifecycle** |

End-to-end flow: create a vault, store a GitHub token credential, create an agent mounting the WebSearch toolkit → pilot with a manually created session first (tool calls really happen, the credential chain really works) → then put "scheduled + trigger-and-run" onto a Deployment → verify version pinning and the operations verbs (pause / archive) → finally clean up in dependency order.

> Why Vault instead of session environment variables on the scheduled chain? Because **Deployments do not support `environment_variables`** (field-tested: passed and silently ignored; the triggered session has no such variable) — `vault_ids` is currently the only credential-injection path for unattended chains. Prefer environment variables when your app creates sessions itself (see Step 4).

## Prerequisites

- A Bailian workspace and its workspace ID.
- One DashScope API Key (one key covers all resources in the workspace).
- A GitHub PAT (for demo; a fake value `GITHUB_TOKEN` below — this recipe only verifies the "injection" act, and a fake token is safer).

Agreed environment variables:

```bash
export BASE="https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
export API_KEY="<your DashScope API Key>"
export GITHUB_TOKEN="ghp_DUMMY_TOKEN_FOR_SMOKE_TEST"
```

> Note: Bailian is currently single-region, `cn-beijing` only. Every request carries `Authorization: Bearer $API_KEY`; responses carry `x-request-id` for troubleshooting (the request body also echoes a `request_id` field).

## The theory: two extension lines + one trigger line

For extending an agent, production really uses two **mutually independent** lines:

- **MCP toolkits**: the agent declares one (or more) services from the Bailian MCP marketplace; at runtime the platform calls that service's tools on the agent's behalf. Fits "service on the public internet, hosted by the Bailian marketplace" — you handle no connection details and (usually) no keys.
- **Config / credential injection (two routes, layered by sensitivity)**:
  - **Session environment variables** (`environment_variables`, the default recommendation): pass key-value pairs at session creation; they reach the sandbox process **as plaintext**, and the agent reads real values via `os.environ` in bash / python. Fits non-sensitive config and interactive sessions — simplest, nothing to pre-create. Limitation: Deployments do not support them (see above).
  - **Vault secret store**: secrets are stored in the vault beforehand; sessions carry only `vault_ids`. Inside the sandbox you get a **placeholder** (`BMA_SECRET_PLACEHOLDER_*`); the real value is swapped into the `Authorization` header only when the egress gateway hits that secret's `allowed_hosts` allowlist. Fits highly sensitive secrets and unattended chains. Full security model in [08-vault-secret-injection-and-egress-gateway.md](08-vault-secret-injection-and-egress-gateway.md).

The combination is the full picture: platform-level external capabilities via MCP; user-level private credentials via Vault (secrets) or environment variables (config).

There is also a third mode, not expanded in 01: **custom tools** — your own services. The agent throws the call back to your app as a `function_call` event; you compute and backfill with `function_call_output`. Use this only when the service is reachable on your intranet.

This recipe adds the **trigger line**: in 01's world, sessions are created by your app and messages sent by your app — the role of "who sends the task at 7:30 in the morning" could only be a cron script you write yourself. **Deployment** absorbs that role into the platform: declaratively configure "which agent, pinned to which version, which messages delivered at trigger, which credentials attached, what schedule" — after that, scheduled triggering, session creation, and initial_events delivery are all done by the platform; your app only comes to look at results.

> **Security boundary (the 2026-09 model)**: once a token is stored in a vault it **never enters the sandbox** — `printenv` shows only the placeholder, secret plaintext never appears in model context or the event stream; on egress the gateway swaps it per the `allowed_hosts` allowlist. That is an order of magnitude safer than the old "plaintext environment-variable injection" (the old docs' warning that "printenv can read the real value; use the prompt to stop the agent printing credentials" is obsolete). But two boundaries still hold: the gateway replaces only the `Authorization` header; and sandbox outbound HTTPS goes through a gateway MITM, so strict TLS verification fails (`curl -k` fixes it) — details and pitfalls in 08.

---

## Step 1 · Create the vault

A vault has two key fields: `display_name` (for console display) and `metadata` (for your own internal user ID and the like).

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/vaults" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Yunling Tea Operations",
    "metadata": {
      "internal_user_id": "u_yunling_ops",
      "team": "operations"
    }
  }'
```

The response returns an `id` (like `vlt_01M1G0W54ARXJ4W61B0N4281TK`). Note it down:

```bash
export VAULT_ID="vlt_xxx"
```

## Step 2 · Store the GitHub token credential

Credentials hang under a vault; the endpoint is **nested**: `/vaults/{vault_id}/credentials` (there is no top-level `/credentials` endpoint — field-tested 404).

Each credential = variable name + value + an **egress allowlist**. `auth.type` currently supports only `environment_variable` (field-tested: `static_bearer` / `mcp_oauth` return `CREDENTIAL_AUTH_TYPE_ERROR`). **`allowed_hosts` is required** and must nest inside `auth.networking` (a 2026-09 breaking change: omitting it → 409 `CREDENTIAL_AUTH_NETWORKING_ERROR` "egress network address cannot be empty"):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/vaults/$VAULT_ID/credentials" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "GitHub PAT (morning-brief push)",
    "auth": {
      "type": "environment_variable",
      "secret_name": "GITHUB_TOKEN",
      "secret_value": "'"$GITHUB_TOKEN"'",
      "networking": { "allowed_hosts": ["api.github.com", "github.com", "*.github.com"] }
    }
  }'
```

Key points:

- `secret_name`: the variable name. **Inside the sandbox, `os.environ["GITHUB_TOKEN"]` yields the placeholder `BMA_SECRET_PLACEHOLDER_GITHUB_TOKEN`** — the real value is swapped into the `Authorization` header by the gateway only when an outbound request hits an allowlisted host (full chain in [08](08-vault-secret-injection-and-egress-gateway.md)).
- `secret_value`: the real secret. **Write-only, never echoed** — on GET, `auth` contains only `secret_name` / `type` / `networking`, no value.
- `networking.allowed_hosts`: the **allowlist of domains the secret may travel to**, wildcards supported (`*.github.com`). The token is only swapped into requests heading to these hosts — requests to other domains keep the placeholder, preventing leakage.
- The response `id` looks like `vcrd_01M1G0W5BYXJDRD32NMB16ER1Z` (prefix `vcrd_`, not `cred_`).

```bash
export CRED_ID="vcrd_xxx"
```

## Step 3 · Create the agent: mount the MCP toolkit

This step prepares three things separately: **declaring the MCP server and toolkit in the agent definition**, **the credential in the vault** (done in Step 2), and **wiring via `vault_ids` at session / deployment creation** (Steps 4 / 5).

Create the agent first. For `model` use a field-tested ID (`qwen3.8-max` / `qwen3.7-max` / `qwen3.7-plus`; note generic IDs like `qwen3-max` are rejected with 400). Declare the marketplace service in `mcp_servers` with `type` as `official` and `name` as **the marketplace service's code**; enable in `tools` via `mcp_toolkit`:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "morning-briefing",
    "description": "Yunling Tea industry morning-brief bot: scheduled industry-news search and digest",
    "model": { "id": "qwen3.7-plus" },
    "system": "You are the morning-brief assistant for Yunling Tea (a chain tea-drink brand) [v1]. On receiving a task: 1) use bailian_web_search to search major developments in the tea-drink / food-service industry over the past 24 hours; 2) digest the findings into a morning brief of at most 5 items, one sentence each with a source. Start your output with the [v1] marker. Never print credential values. Verify allowed-host authentication without echoing credentials.",
    "mcp_servers": [
      { "type": "official", "name": "WebSearch" }
    ],
    "tools": [
      {
        "type": "builtin_toolkit",
        "default_config": { "enabled": true, "permission_policy": { "type": "always_allow" } },
        "configs": [ { "name": "bash", "enabled": true } ]
      },
      {
        "type": "mcp_toolkit",
        "mcp_server_name": "WebSearch",
        "default_config": { "enabled": true },
        "configs": [ { "name": "bailian_web_search", "enabled": true } ]
      }
    ]
  }'
```

Two key details from field tests:

> **`configs` must enable tools one by one.** `mcp_toolkit` mirrors 01's `builtin_toolkit`: `default_config.enabled: true` alone is not enough — every tool you want (here `bailian_web_search`) must be explicitly `enabled: true` in `configs[]`, otherwise at runtime the agent simply **does not have the tool** — no error, just absent.

> **`mcp_servers.name` is not validated at declaration.** A name absent from the marketplace (say `amap-maps`, field-tested not in the marketplace listing) still returns 200 at creation; the tool silently goes missing at runtime and the agent replies "I have no available tools". To troubleshoot: send a message that forces tool use and check the event stream for `mcp_call`. List available services via the CLI: `bl mcp list` (lists the account's activated MCP servers, with code / tools).

Marketplace services are called via the platform proxy, with endpoints like `https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/mcps/{code}/sse`; you usually provide no credentials. For services needing your own key, store the key in a vault and connect directly from bash with an `Authorization` header (bash sees the placeholder; the real value is swapped by the egress gateway — see [08](08-vault-secret-injection-and-egress-gateway.md)).

```bash
export AGENT_ID="agent_xxx"
```

If besides MCP tools you also need scripts (reading credentials, processing files), add the `builtin_toolkit` from 01 to `tools` (bash/read/write etc.); the two coexist fine. A pure-MCP agent can even skip the environment — a session with an empty `environment_id` still runs.

## Step 4 · Manual pilot: create a session to verify tools and the credential chain

Before scheduling anything, run one turn the plain way and verify two things: **tool calls really happen, and the credential chain really works**.

### 4.1 First choice: session environment variables (non-sensitive config / interactive sessions)

When your app creates the session itself, **config injection's first choice is `environment_variables`** — plaintext key-value pairs straight into the sandbox, no vault to pre-create; the agent's bash / python reads real values via `os.environ`:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "'"$AGENT_ID"'",
    "title": "Morning briefing pilot",
    "environment_variables": { "BRIEF_MAX_ITEMS": "5", "LOG_LEVEL": "info" }
  }'
```

Verify: have the agent run `printenv BRIEF_MAX_ITEMS` → outputs `5` (the **real value**). Both the creation response and GET echo the field — put non-sensitive content only.

> Interactive session + non-sensitive config → environment variables suffice. **When you need secret-grade security (no plaintext inside the sandbox) or the Deployment unattended chain** → use the vault wiring below.

### 4.2 Required for the scheduled chain: vault_ids wiring

Deployments do not support `environment_variables`, so the scheduled chain (Step 5) can only rely on the vault. Wire the secret into the runtime with `vault_ids` at session creation (the field is just `agent`, taking the Agent ID string; the session locks a full snapshot of that agent's current version):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "'"$AGENT_ID"'",
    "title": "Morning briefing pilot",
    "vault_ids": [ "'"$VAULT_ID"'" ]
  }'
```

```bash
export SESSION_ID="sesn_xxx"
```

> Note: `sessions.create` **accepts no initial-input field**, so the standard pattern is two-step driving — "create the session, then separately POST one `message` event". (For "trigger with the first message attached", use the Deployment below, which supports `initial_events`, delivered at trigger time.)

Send a message to verify **placeholder injection** — have it run `printenv GITHUB_TOKEN` verbatim:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/events" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          { "type": "text", "text": "Check whether GITHUB_TOKEN starts with BMA_SECRET_PLACEHOLDER_ and report only true or false; never print the value" }
        ]
      }
    ]
  }'
```

Observe via the SSE live stream (consumption per 01's 5.2; the `event:` line is always `message`; comment lines include `:connected` / `:HTTP_STATUS/200` / `:keepalive`):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 300 -N "$BASE/sessions/$SESSION_ID/events/stream" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: text/event-stream"
```

Field-tested event stream (the secret-placeholder verification turn, 2026-09 model):

```text
session_status   {"session_status": "running"}
message          (user message echo)
model_request_start
tool_call        bash  {"command": "printenv GITHUB_TOKEN", ...}
tool_call_output bash  {"stdout":"BMA_SECRET_PLACEHOLDER_GITHUB_TOKEN\n","exit_code":0}
message          (assistant reports the output)
session_status   {"stop_reason": {"type": "end_turn"}, "session_status": "idle"}
```

**Seeing the placeholder is the mark of successful injection** (before 2026-09 this printed the real value; that verification style is obsolete). End-to-end verification of the secret (that egress replacement really happens) uses 08's Step 5: send a request to an allowlisted host and check that the recipient receives the real value. The real GitHub push chain is the same — the agent puts the placeholder into the `Authorization` header calling `api.github.com`, the gateway swaps in the real PAT, and GitHub authenticates.

Send another message to trigger the MCP tool ("use the tool to search the latest tea-industry news"); MCP calls produce a **dedicated event type**, parallel to `tool_call`:

```text
mcp_call        role=assistant  data: {"name": "bailian_web_search",
                                 "server_label": "WebSearch",
                                 "arguments": "{\"query\": \"tea industry latest news\", \"count\": 10}",
                                 "call_id": "call_xxx"}
mcp_call_output role=tool       data: {"output": "<JSON returned by the MCP server>"}
```

That is: builtin tools go through `tool_call` / `tool_call_output`; MCP tools go through `mcp_call` / `mcp_call_output`. The turn ends at `session_status = idle` with `stop_reason.type == end_turn`.

Pilot passed — both foundations hold. Next, hand "who sends the message at 7:30 every morning" over to the platform.

## Step 5 · Deployment: hand scheduling to the platform

A Deployment is a resource at the same level as agent / environment / session: declare "which agent version pinned, what is delivered at trigger, which credentials attached, what schedule" — then triggering, session creation, and initial_events delivery are all done by the platform.

### 5.1 Create: version-pinned agent + initial_events + vault_ids

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/deployments" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "morning-briefing-prod",
    "description": "Yunling Tea industry morning brief: manual-trigger pilot",
    "agent": { "id": "'"$AGENT_ID"'", "version": 1 },
    "initial_events": [
      {
        "type": "message",
        "role": "user",
        "content": [
          { "type": "text", "text": "Here is today's briefing task: 1) use bailian_web_search to search \"tea industry latest news\" and pick the 3 most notable items into a brief, one sentence each; 2) check whether GITHUB_TOKEN starts with BMA_SECRET_PLACEHOLDER_ and report only true or false, never its value; 3) deliver the final morning brief." }
        ]
      }
    ],
    "vault_ids": [ "'"$VAULT_ID"'" ],
    "metadata": { "team": "operations", "purpose": "daily-briefing" }
  }'
```

Three field-tested points:

> **`agent` must be an object `{id, version}`; an ID string is rejected** (field-tested: a string returns `400 PARAMS_ILLEGAL`). This differs from `sessions.create` (a string there = pin latest). A Deployment is a long-lived resource — **explicitly pin the agent version at creation**; the response echoes the full snapshot of that version (system / tools / model) expanded. Version semantics in 5.4.

> **`initial_events` is the input array delivered at trigger time**, shaped exactly like the `input` for sending messages to a session. It fills the gap left by `sessions.create` rejecting initial input: in the triggered session, the first user message is precisely this — "trigger and run", no extra message from your app.

> **`vault_ids` wires at the deployment level**: every session spawned by a trigger automatically carries these credentials (injection behaves exactly as with a manually created session).

Omitting `schedule` gives **manual mode** (triggerable only via `POST /run`); filling it gives scheduled mode (5.5). A successful creation (200) echoes all fields, `status` is `"active"`, and the id looks like `depl_01M1G17AQRZF6AT160HGYZ4VSC` (prefix `depl_`).

```bash
export DEPLOYMENT_ID="depl_xxx"
```

### 5.2 Trigger: run and deployment_run

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/deployments/$DEPLOYMENT_ID/run" \
  -H "Authorization: Bearer $API_KEY"
```

Returns a `deployment_run` (prefix `drun_`); `session_id` is `null` until the session spawns asynchronously:

```json
{
  "id": "drun_01M1G17Y77XSFWPZ76MDN8HRKF",
  "type": "deployment_run",
  "agent": { "id": "agent_01M1G0W5Y10SPRSECDPXG5TKZV", "version": 1 },
  "status": "running",
  "error": null,
  "deployment_id": "depl_01M1G17AQRZF6AT160HGYZ4VSC",
  "session_id": null,
  "trigger_source": "manual",
  "started_at": "2026-09-02T03:05:16.763Z",
  "finished_at": null
}
```

Seconds later, query the trigger history for the `session_id` (also the production way to tell "done yet" — `status` becomes `succeeded`, `finished_at` carries a value):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 "$BASE/deployments/$DEPLOYMENT_ID/runs" \
  -H "Authorization: Bearer $API_KEY"
```

The response shape matches the versions API: `{data: [...], next_page, request_id}`, newest first. `trigger_source` distinguishes `"manual"` from `"schedule"` (cron).

### 5.3 Trigger-and-run: full evidence from one trigger

Pull events for the triggered session (`GET /sessions/{id}/events?order=asc`, or SSE); field-tested 26 events, key frames:

```text
session_status   running
message          (user) Here is today's briefing task: 1) use bailian_web_search to search...   ← initial_events delivered
mcp_call         bailian_web_search  {"query": "tea industry latest news", "count": 10}
tool_call        bash  printenv GITHUB_TOKEN
mcp_call_output  (industry-news JSON returned by WebSearch)
tool_call_output (BMA_SECRET_PLACEHOLDER_GITHUB_TOKEN)
message          (assistant) **[v1] Yunling Tea morning brief · 2026-09-02** + 3 industry items
session_status   idle  stop_reason={"type": "end_turn"}
```

One trigger proves three things at once: **initial_events enter the session as the first user message**, **the MCP tool really gets called**, and **the vault secret is injected into the deployment-spawned session (placeholder inside the sandbox, gateway-swapped on egress)**. Your app never sent a single message — that is the full meaning of "the trigger line absorbed into the platform".

### 5.4 Version semantics: pinning and the drift trap

A Deployment pins `{id, version}` at creation; later agent upgrades **do not affect** it. Field test: bump morning-briefing's prompt from v1 to v2 (`POST /agents/{id}`, name + current version required — see 03), then trigger the same deployment:

```text
deployment_run.agent.version = 1          ← still v1
session output prefix = [v1]              ← running v1's prompt
```

To upgrade the version a deployment runs, update via `POST /deployments/{id}` (PATCH semantics; omitted fields stay). But there is a **field-tested production trap** here:

> **On update without the `agent` field, the agent drifts to the latest version.** Field test: changing only `description` (no agent in the body) moved `agent.version` in the response from 1 to 2 — the prompt silently upgraded. Safe practice: **always carry `agent {id, version}` explicitly on every deployment update**:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/deployments/$DEPLOYMENT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Yunling Tea industry morning brief: manual-trigger pilot (description updated)",
    "agent": { "id": "'"$AGENT_ID"'", "version": 2 }
  }'
```

(Explicitly passing `agent {id, version: 1}` also pins the version back to v1, field-tested.)

Mnemonic contrast: **a session pins the snapshot of "the latest or specified version at creation"; a deployment pins "the explicitly specified version at creation", but on update, omitting agent drifts it to latest**.

### 5.5 cron: scheduled triggering

Adding `schedule` to a deployment makes it scheduled. Field test uses an every-minute expression to verify scheduling (swap in the business schedule for real use):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/deployments" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "morning-briefing-cron",
    "agent": { "id": "'"$AGENT_ID"'", "version": 1 },
    "initial_events": [ ... same as above ... ],
    "schedule": { "type": "cron", "expression": "* * * * *", "timezone": "Asia/Shanghai" }
  }'
```

Field-tested behavior (expression `* * * * *`, every minute):

- **Fires punctually on the minute**; a new run with `trigger_source: "schedule"` appears in the runs listing, fully isomorphic to the manual run above (same session creation, same initial_events delivery).
- The response's `schedule` object carries **`next_run_at` / `last_run_at`** — to tell "the scheduled task is alive and when it next runs", just read the deployment object instead of computing cron yourself.
- For the real morning-brief case: `"expression": "30 7 * * *"` (daily 07:30), `"timezone": "Asia/Shanghai"`.

### 5.6 Operations verbs: pause / unpause / archive

| Verb | Endpoint | Field-tested behavior |
|---|---|---|
| Pause scheduling | `POST /deployments/{id}/pause` | `status: "paused"`, `paused_reason: {type: "manual"}`; **cron stops firing, `next_run_at` frozen** |
| Resume | `POST /deployments/{id}/unpause` | `status: "active"`, resumes from the next scheduled point; **triggers missed while paused are not caught up** (field test: pause spanned two whole minutes; after resume, the 03:11 slot was not made up) |
| Archive | `POST /deployments/{id}/archive` | `archived_at` set, `next_run_at` cleared (schedule released); GET still works, **listings filter archived items by default** |
| Delete | `DELETE /deployments/{id}` | **405 not supported** — same as agents: archive-only, no delete |

Three easily confused points (all field-tested):

> **pause blocks only scheduling, not manual triggers**: `POST /run` on a paused deployment still returns 200 and runs normally. For "stop the schedule but keep emergency manual triggers", pause is exactly right.

> **archive is the real deactivation**: `POST /run` on an archived deployment returns `409 DEPLOYMENT_STATE_CONFLICT "deployment archived"` — not even manual triggers work.

> **No 409 on concurrent triggers**: two consecutive `POST /run` calls (under 1 second apart, the previous still running) both return 200, each creating its own run and finishing. There is no "concurrent-trigger conflict rejection" — concurrency control is your trigger side's job (or adjust the schedule in an update).

### 5.7 Observation surface summary

| What you want to know | Where to look |
|---|---|
| Is the scheduled task alive; when does it next run | `GET /deployments/{id}`'s `status` + `schedule.next_run_at` |
| Has a trigger finished | `GET /deployments/{id}/runs`'s `status` / `finished_at` |
| What did a trigger do | the run's `session_id` → `GET /sessions/{id}/events` (or SSE) |
| Did it fail | the run's `error` field + the session event stream's `session_status` |

For "notify me when it's done" needs, this recipe's approach is **active query** (polling runs / reading the deployment object); platform-side event push (Webhook) is field-tested in 06 — subscribe to events like `session.status_idled` and let the platform POST your receiver.

## Step 6 · Human approval in production (HITL)

Human approval (HITL) in production should not depend on long connections. The review wait window can be minutes to hours; holding an SSE connection the whole time neither scales horizontally (connections bind to instances, no free scheduling) nor survives service restarts (one deploy drops all in-flight approvals). The right shape: **let the session park in the waiting state; your service fetches status, decides, and backfills results when needed.**

Managed Agents sessions natively support this "stop and wait for you" semantics — when the agent needs human confirmation of a tool call, the session goes idle with `requires_action` and stays there until you backfill the decision.

**Two recommended approaches:**

### Option A: poll historical events + `requires_action`

Your service periodically pulls historical events and checks whether the session is parked in the "needs human / tool intervention" state. In that state, the last event has `session_status` idle and `stop_reason` `requires_action`, with `pending_batch_id` and `pending_call_ids` attached.

```bash
# pull the latest historical event (last one in reverse order)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/sessions/$SESSION_ID/events?order=desc&limit=1" \
  -H "Authorization: Bearer $API_KEY"
```

Polling logic (pseudocode):

```text
Every N seconds:
  GET /sessions/{id}/events?order=desc&limit=1
  read the last event's session_status / stop_reason
  if stop_reason == requires_action:
      extract pending_batch_id and pending_call_ids; fetch tool_approval_request for arguments
      escalate it into your human review queue
  if stop_reason == end_turn:
      the turn is complete; stop polling
```

Once a human decides, approve or deny the tool call with a `tool_approval_response` event:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/events" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "type": "tool_approval_response",
        "role": "user",
        "content": [{"type": "data", "data": {
          "batch_id": "<stop_reason.pending_batch_id>",
          "call_id": "<one stop_reason.pending_call_ids entry>",
          "result": "allow"
        }}]
      }
    ]
  }'
```

Read [tutorial 06](../tutorials/06-tool-approval.md) for the authoritative approval round trip. After submission, inspect errors and continuation; HTTP 200 alone does not establish acceptance.

For denial, set `result` to `deny`, optionally with a `deny_message` explaining why. For backfilling a self-hosted function's result, use `function_call_output` (with `call_id` + `output`).

In the morning-brief scenario: before the agent writes a "PR alert" into the company repo upon spotting suspected major negative press, have it call a confirmation-requiring action (a custom tool or a pre-write confirmation); the session parks at `requires_action`; your polling service detects it and pushes to the on-call ops group; a human clicks allow/deny; you backfill `tool_approval_response`; the agent continues.

> On cost caps: sessions currently **offer no cost-cap (budget) field**, nor a notification event for hitting one. For cost control, do trigger-frequency and concurrency limiting at the Deployment layer, backed by after-the-fact usage reconciliation.

### Option B: Deployment trigger + post-hoc query

If the trigger is "scheduled" or "an external system manually fires one task", just use Step 5's Deployment: the external system only calls `POST /deployments/{id}/run` (or leaves it to cron), then collects results via `GET /deployments/{id}/runs` — `status` reaching `succeeded` means done; take the `session_id` to inspect artifacts. No long connection anywhere.

## Step 7 · Data residency and region

Current behavior: Bailian Managed Agents is **single-region (`cn-beijing`)**; both agent inference and sandbox execution happen in that region. There is therefore no inference-region selection parameter, and no per-session region override at `sessions.create`.

So this section **needs no extra configuration**: data residency is guaranteed by the single-region fact itself. If your compliance requirement is "data must not leave a certain region", the current shape already satisfies it; for multi-region options, follow Bailian's official future releases.

## Step 8 · Resource lifecycle: list / retrieve / update / archive / delete

Every resource has a set of verbs, but **not every resource supports the full set** (field-tested):

| Resource | List / get | Update | Archive | Delete |
|---|---|---|---|---|
| agents | GET `/agents`, `/agents/{id}` | `POST /agents/{id}` (auto-bumps version) | `POST /agents/{id}/archive` | **not supported** (DELETE returns 405) |
| environments | GET `/environments`, `/{id}` | `POST /environments/{id}` | `POST /{id}/archive` | DELETE works |
| sessions | GET `/sessions`, `/{id}` | — | `POST /{id}/archive` | DELETE works |
| deployments | GET `/deployments`, `/{id}` (listings filter archived by default) | `POST /deployments/{id}` (watch agent drift, see 5.4) | `POST /{id}/archive` | **not supported** (DELETE 405) |
| vaults | GET `/vaults`, `/{id}` | `POST /vaults/{id}` | `POST /{id}/archive` | DELETE works |
| credentials | GET `/vaults/{id}/credentials` | — | — | `DELETE /vaults/{vid}/credentials/{cid}` |

List agents:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/agents?limit=5" \
  -H "Authorization: Bearer $API_KEY"
```

Get one agent:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/agents/$AGENT_ID" \
  -H "Authorization: Bearer $API_KEY"
```

Update the agent. Three notes (all field-tested): the update verb is **`POST /agents/{id}`, not `PATCH` (405)**; the body **must carry the current `version`** for optimistic concurrency; and **must carry `name`** (else `AGENT_005 agent name cannot be empty`). On success version auto-increments:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "morning-briefing",
    "version": 1,
    "system": "You are the morning-brief assistant for Yunling Tea (a chain tea-drink brand) [v2]. ... (new prompt)"
  }'
```

View version history:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/agents/$AGENT_ID/versions" \
  -H "Authorization: Bearer $API_KEY"
```

**archive vs. delete**: `archive` keeps records for audit while tearing down containers and stopping metering; `delete` is permanent removal. Prefer `archive` in production. Agents and deployments are archive-only — version history / trigger history are the point of their existence; that is by design.

## Step 9 · Cleanup

Cleanup has a **dependency order**, plus one field-tested trap: **deleting a vault does not cascade-delete its credentials**. Delete the vault first and the credential endpoint still works (orphaned data). The correct order is child before parent:

```bash
# 1. Delete the pilot session (DELETE works, returns 200)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X DELETE "$BASE/sessions/$SESSION_ID" -H "Authorization: Bearer $API_KEY"

# 2. Archive the deployment (DELETE returns 405, archive only; archiving releases the schedule)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/deployments/$DEPLOYMENT_ID/archive" -H "Authorization: Bearer $API_KEY"

# 3. Delete the environment (DELETE works)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X DELETE "$BASE/environments/$ENV_ID" -H "Authorization: Bearer $API_KEY"

# 4. Archive the agent (DELETE returns 405, archive only)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID/archive" -H "Authorization: Bearer $API_KEY"

# 5. Delete the credential (child) first, then the vault (parent) — order matters
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X DELETE "$BASE/vaults/$VAULT_ID/credentials/$CRED_ID" -H "Authorization: Bearer $API_KEY"
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X DELETE "$BASE/vaults/$VAULT_ID" -H "Authorization: Bearer $API_KEY"
```

Sessions spawned by deployments are equally deletable: collect every `session_id` from `GET /deployments/{id}/runs` and DELETE one by one (note: a running session cannot be deleted; wait for idle).

## Wrap-up

This recipe erected the production-operations skeleton:

- **MCP toolkits** (`mcp_servers` official + per-tool `mcp_toolkit` configs) let the agent call marketplace external services via the platform proxy; watch `mcp_call` / `mcp_call_output` in the event stream.
- **Config injection has two layers**: non-sensitive config via **session environment variables** (`environment_variables`, plaintext straight into the sandbox; first choice for interactive sessions); highly sensitive secrets via **Vault** (placeholder injection + egress-gateway swap per the `allowed_hosts` allowlist — the token never passes your app side, never enters agent config, never enters the sandbox) — the scheduled chain (Deployment) supports only the latter.
- **Deployment** absorbs triggering into the platform: `agent {id, version}` pins the version explicitly, `initial_events` delivers the first message at trigger, cron runs it automatically, `pause` (blocks scheduling, not manual) / `unpause` (no catch-up) / `archive` (full deactivation) manage the lifecycle, and `GET runs` collects results.
- Two production HITL routes: **poll `requires_action` + `tool_approval_response`**, or **Deployment trigger + post-hoc run queries**.
- Lifecycle verbs differ per resource: **agents and deployments are archive-only**; session / environment / vault can be deleted; **credential before vault** (no cascade).

Six current behaviors to keep in mind: **Deployment updates drift the agent to latest when agent is omitted** (always carry `{id, version}` explicitly on updates); **no conflict limit on concurrent triggers** (rate-limit yourself); **sessions have no cost-cap field** (throttle at the Deployment layer as backstop); **single region `cn-beijing`**; **`mcp_servers.name` gets no existence check** (a typo fails silently); **sandbox egress goes through a gateway MITM** (strict-TLS clients fail; `curl -k` / `verify=False` fixes).

The full security deep dive on secrets (placeholder model, gateway swap behavior, `allowed_hosts` semantics, TLS pitfalls) → [08-vault-secret-injection-and-egress-gateway.md](08-vault-secret-injection-and-egress-gateway.md).
