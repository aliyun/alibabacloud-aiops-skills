# Managed Agents API Endpoint Quick Reference

Sources: the official API docs `https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/introduction`
and the docs index `https://docs.agent.bailian.aliyun.com/llms.txt`.

> This page lists only **endpoints and paths** for fast lookup. **Concrete request-body fields, enums, and response structures defer to the official doc pages** —
> every resource has a matching `.md` doc page and OpenAPI JSON; pull them on demand when writing code; do not infer fields from this page.
> The event-contract parts (event type enums, the `session_status` event shape) come from official Python SDK field testing;
> where they disagree with doc examples, the field test wins.

Local evaluation adapters can use [api-contracts.yaml](api-contracts.yaml) for scenario-scoped REST metadata; it is not a substitute for the live OpenAPI schema.

## Base URL and auth

```
https://{workspace_id}.{region}.maas.aliyuncs.com/api/v1/agentstudio
```

- `workspace_id`: visible in the dropdown at the top-right corner of the Bailian console
- `region`: currently only `cn-beijing` is supported
- Auth header: `Authorization: Bearer <your-api-key>`; one key can access every resource under its workspace
- Request bodies are JSON (`Content-Type: application/json`); file upload is `multipart/form-data`
- Every response carries `x-request-id`; attaching it to support tickets speeds up diagnosis
- List pagination: `limit` (default 20, max 100, **over-limit returns 400 rather than truncating**), `page` (omit on the first call; pass the previous response's `next_page` afterwards; no `next_page` in the response means the last page)

## Webhook example URL

Use `https://www.baidu.com` for endpoint-creation examples and evaluation tasks. Verify the created resource's URL and subscriptions; do not require notification delivery to this sample website. Use a customer-controlled receiver for production delivery and signature tests.

## Full endpoint table

All paths below are relative to `/api/v1/agentstudio`.

| Resource | Method + path | Purpose |
| --- | --- | --- |
| **Agent** | `POST /agents` | Create |
| | `GET /agents/{agent_id}` | Get |
| | `GET /agents` | List |
| | `POST /agents/{agent_id}` | Update (**partial replace**: passed fields replace, omitted fields unchanged; auto-generates a new version number each time; must carry the current `version` as an optimistic lock) |
| | `GET /agents/{agent_id}/versions` | List historical versions |
| | `POST /agents/{agent_id}/archive` | Archive |
| **Environment** | `POST /environments` | Create |
| | `GET /environments/{environment_id}` / `GET /environments` | Get / list |
| | `POST /environments/{environment_id}` | Update |
| | `DELETE /environments/{environment_id}` | Hard delete |
| | `POST /environments/{environment_id}/archive` | Archive |
| **Session** | `POST /sessions` | Create (binds Agent + Environment, locking a snapshot of the agent's latest version at that moment; supports `environment_variables` plaintext injection of session env vars) |
| | `GET /sessions/{session_id}` / `GET /sessions` | Get / list |
| | `POST /sessions/{session_id}` | Update metadata (e.g. rename) |
| | `DELETE /sessions/{session_id}` | Hard delete (metadata + event history + resource copies all wiped, unrecoverable) |
| | `POST /sessions/{session_id}/archive` | Archive (turns `terminated`; event history retained) |
| **Event** | `POST /sessions/{session_id}/events` | Send an event (user message / tool receipt); triggers the agent into `running` |
| | `GET /sessions/{session_id}/events` | List event history |
| | `GET /sessions/{session_id}/events/stream` | Subscribe to the real-time SSE event stream |
| **Session Thread**<br>(formation-specific; REST field-test: usable, **not yet in the official public docs**) | `GET /sessions/{session_id}/threads` | List delegated sub-threads (one row per member, with `status` / `agent.version`) |
| | `GET /sessions/{session_id}/threads/{thread_id}` | Single-thread detail (adds a `request_id`) |
| | `GET /sessions/{session_id}/threads/{thread_id}/events` | Single-thread event sequence — **the shortest path to "what did one member do"** |
| | `POST /sessions/{session_id}/threads/{thread_id}/archive` | Archive the thread (unaddressable after archiving, but events remain queryable) |
| **Session resources** | `POST /sessions/{session_id}/resources` | Runtime dynamic file mounting (takes effect immediately; no session restart needed) |
| | `GET /sessions/{session_id}/resources` | List mounted resources |
| | `GET /sessions/{session_id}/resources/{id}` | Query a single resource |
| | `DELETE /sessions/{session_id}/resources/{id}` | Unmount (cleans up the in-session copy; the original file is unchanged) |
| **File** | `POST /files` | Upload (`multipart/form-data`) |
| | `GET /files/{file_id}` / `GET /files` | Metadata / list |
| | `GET /files/{file_id}/content` | Download content (**note the `/content` suffix — `/download` 404s**; and only session artifacts with `downloadable=true` can be downloaded — accessing directly-uploaded files returns 403 code 11900007) |
| | `DELETE /files/{file_id}` | Hard delete (File supports deletion only, not archiving) |
| **Skill** | `POST /skills` | Upload a skill package to create |
| | `GET /skills/{skill_id}` / `GET /skills` | Get / list |
| | `DELETE /skills/{skill_id}` | Hard delete |
| | `POST /skills/{skill_id}/versions` | Upload a new version |
| | `GET /skills/{skill_id}/versions[/{version}]` | List / get versions |
| | `GET /skills/{skill_id}/versions/{version}/content` | Get the skill package download URL |
| **Vault** | `POST /vaults`, `GET`, `POST /{id}`, `DELETE /{id}`, `POST /{id}/archive` | Vault CRUD + archive |
| **Credential** | `GET /vaults/{vault_id}/credentials`; `GET`/`POST` `…/credentials/{id}`; `POST …/credentials/{id}/archive`; `DELETE …/credentials/{id}` | CRUD + archive for individual secrets inside a vault. **Mounted under the vault sub-path — the top-level `/credentials` 404s** (the official OpenAPI's top-level form does not match the live API); update must carry the full `auth` value; ID prefix `vcrd_`. **2026-09 breaking change**: `auth.networking.allowed_hosts` is **required** (missing → 409 `CREDENTIAL_AUTH_NETWORKING_ERROR` "egress network addresses cannot be empty"); credentials now use **placeholder injection** (inside the sandbox `os.environ` yields `BMA_SECRET_PLACEHOLDER_<variable-name>`; the real value only substitutes the `Authorization` header when the egress gateway hits `allowed_hosts`) — see [../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md) |
| **Deployment** | `POST /deployments` | Create (binds Agent + trigger mode) |
| | `GET /deployments/{id}` / `GET /deployments` | Get / list |
| | `POST /deployments/{id}` | Update (passed fields replace; omitted fields unchanged) |
| | `POST /deployments/{id}/pause` / `/unpause` | Pause scheduled triggering / resume to `active` |
| | `POST /deployments/{id}/run` | Manually trigger one run |
| | `POST /deployments/{id}/archive` | Archive to a terminal state (no further update or triggering) |
| | `GET /deployments/{id}/runs` | Run history of this Deployment (the run object directly carries `session_id`) |
| | `GET /deployment_runs/{run_id}` | Single-run detail (**not `/deployments/{id}/runs/{run_id}` — that 404s**) |
| | `GET /deployment_runs` | Workspace-level all runs (including those of archived Deployments; `run_id` is globally unique) |
| **Webhook**<br>(REST field-test: usable; the whitepaper marks it `[coming soon]`) | `POST /webhook_endpoints` | Create (the response contains `signing_secret`, **which appears exactly this once**) |
| | `GET /webhook_endpoints` | List (with `last_success_at` / `last_failure_at` / `consecutive_fail`) |
| | `POST /webhook_endpoints/{id}/test` | Deliver a synthetic `webhook.test` as a go-live self-check |
| | `POST /webhook_endpoints/{id}/reset_secret` | Rotate the signing secret (the old one dies immediately) |
| | `GET /webhook_endpoints/{id}` / `PUT /webhook_endpoints/{id}` | Get one / update (`PUT` changes `description` / `url` / `events`; also `POST /{id}/enable`, `POST /{id}/disable`, `GET /{id}/events`) |
| | `DELETE /webhook_endpoints/{id}` | Hard delete |

## Five high-frequency request bodies (official examples; fields defer to the doc pages)

**Creating a coordinator formation Agent** (`POST /agents`; the request body **has no `type` field** —
a coordinator is just a normal Agent carrying an extra `multiagent`):

```json
{
  "name": "dev-coordinator",
  "model": {"id": "qwen3.8-max"},
  "system": "Decompose requirements and dispatch them to members...",
  "multiagent": {
    "type": "coordinator",
    "agents": [
      {"type": "self"},
      {"type": "agent", "id": "agent_coder", "version": 3}
    ]
  }
}
```

| Field | Required | Description |
| --- | --- | --- |
| `multiagent.type` | No | Currently only `coordinator` |
| `multiagent.agents` | No | Roster of 1-20 entries; passing `[]` clears the formation and reverts to a single agent |
| Entry `type` | Yes | `agent` (references another Agent) or `self` (the coordinator itself; at most one)|
| Entry `id` | Required when `type=agent` | The member Agent ID |
| Entry `version` | No | Latest if omitted; pin it for production |

Note: the SDK's `system_prompt` parameter maps to the wire field `system`; the `model` parameter is a string while the wire form is `{"id": "…"}`.
Update a formation with `POST /agents/{id}` and **carry the current `version` as the optimistic lock**.

**Two high-frequency 400s and one silent failure of `POST /agents` (REST field tests)**:

| Symptom | Cause | The correct way |
| --- | --- | --- |
| `400 AGENT_010 model does not exist` | Used a nonexistent model ID (`qwen3-max` is field-test rejected) | Field-tested to accept `qwen3.8-max` / `qwen3.7-max` / `qwen3.7-plus` / `qwen3.6-plus` / `qwen3.6-flash`, plus `auto`, `glm-5.2`, `deepseek-v4-pro`, etc. (**a flash tier exists**; the full list defers to the console dropdown) |
| `400 AGENT_010 MCP Server validation failed` | An `mcp_servers` entry with `type: customer` whose service name was never registered in the console | Register in the console first, then write the config; `type: official` (marketplace) is, counterintuitively, not validated — a mistyped name only surfaces at runtime |
| Creation succeeds but the agent says "I have no tools available", with `TOOL_NOT_FOUND ... Available tools: ['mark_artifacts']` | Only wrote `default_config.enabled: true` without listing tools individually in `configs[]` | In `configs[]` write one entry per tool you use: `{"name": "bash", "enabled": true}`; MCP tools likewise, additionally requiring `mcp_toolkit.mcp_server_name` |

**Formation agents need no orchestration-tool declarations**: the coordinator's `create_agent` / `list_agents` / `wait_for_agents` and the members'
`submit_result` are auto-injected by the platform in multiagent mode.

**Creating an Environment** (only `name` required):

```json
{
  "name": "data-sandbox",
  "description": "Data analysis sandbox",
  "config": {
    "type": "cloud",
    "packages": {
      "pip": ["polars"],
      "npm": ["typescript"]
    },
    "networking": {"type": "unrestricted"}
  },
  "scope": "organization",
  "metadata": {"owner": "data-team"}
}
```

> The example deliberately omits pandas / numpy / ffmpeg — **the base image already ships them** (pandas 2.2.3, numpy, openpyxl, ffmpeg 5.1.9
> + roughly 190 pip packages + node/ruby/cargo/go toolchains; the bare environment is field-tested usable), so re-declaring them proves nothing;
> to verify package installation works, pick something the base lacks (e.g. polars). See [../tutorials/05-environment-packages.md](../tutorials/05-environment-packages.md).

| Field | Required | Mutable | Description |
| --- | --- | --- | --- |
| `name` | Yes | Yes | Unique within the workspace |
| `config.type` | No | **No** | Currently only `cloud` (Bailian-hosted); **immutable after creation** |
| `config.packages` | No | Yes | Declared grouped by package manager; **installation is async, ~2 minutes** (creation returns immediately; no status field to poll). Field-tested groups: `apt` / `pip` / `npm` / `gem` install; **`cargo` / `go` declarations install nothing (silently ineffective, no error)**; the official docs list only apt / pip / npm. Updates are **whole-list replaces** (unlisted packages are removed) with a **minutes-level propagation delay** (field test: a new session 13 seconds later still saw the old environment; effective after 184 seconds)|
| `config.networking.type` | No | Yes | `unrestricted` allows all outbound access; **settable only via API — not shown in the console** |
| `scope` | No | Yes | Defaults to `organization` (shared by workspace members); **settable only via API** |
| `metadata` | No | Yes | Custom key-value pairs; no effect on runtime behavior |

**Archive = immediate deactivation** (field-tested): after archiving you cannot create sessions bound to it (404), and **already-bound idle sessions can no longer receive messages** (404 not_found)
— the official docs' "bound sessions keep working" disagrees with the field test. `DELETE` works after archiving and is a hard, unrecoverable delete; to keep the config, archive instead
(hidden from the default list; `include_archived=true` makes it visible). Sandbox specs (CPU / memory / disk) and the per-session duration cap are not public in the official docs.

**Creating a Session** (requires `agent` + `environment_id`):

```json
{
  "agent": "agent_xxx",
  "environment_id": "env_xxx",
  "title": "Q3 sales data analysis",
  "resources": [
    {"type": "file", "file_id": "file_xxx", "mount_path": "/uploads/data.txt"}
  ],
  "environment_variables": {"API_BASE_URL": "https://new.example.com", "LOG_LEVEL": "info"},
  "vault_ids": ["vlt_xxx"],
  "metadata": {"biz_ticket_id": "1234"}
}
```

`mount_path` **must start with `/uploads/`** (otherwise session creation fails with `invalid_parameter: Invalid resource`). The real sandbox path =
`/mnt/session` + `mount_path` — in the example above the agent actually sees `/mnt/session/uploads/data.txt`, and **the system prompt must state the real path**.
Note the `.csv` extension is rejected at upload time (415 code 11900014; the whitelist is `.txt` `.md` `.json` `.xlsx` `.pdf` `.png`) —
rename CSV data to `.txt` before uploading.

**The two credential-injection paths (REST field-test, 2026-09-03) — completely different security levels**:

| | `environment_variables` (session env vars) | `vault_ids` (Vault) |
| --- | --- | --- |
| How values are passed | Plaintext key-value pairs at session creation; **echoed verbatim in the create response** (GET echoes too) | Credentials are pre-stored in the Vault; the session passes only vault IDs |
| `os.environ` inside the sandbox | **Real values** (readable directly via `printenv`) | **Placeholder** `BMA_SECRET_PLACEHOLDER_<variable-name>` |
| Where the real value appears | Inside the sandbox process (and the event stream, if the agent prints it) | Only in the vault (encrypted) + the instant the egress gateway hits `allowed_hosts` and substitutes the `Authorization` header |
| Fits | Non-sensitive config: API endpoints, log levels, feature flags | High-sensitivity secrets: API keys, tokens |
| Deployment support | ❌ **not supported** (silently ignored when passed; the triggered session lacks the variable) | ✅ `vault_ids` wires at the deployment level |

The full Vault chain (placeholders, `allowed_hosts`, gateway substitution behavior) is in
[../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md).

**Sending a message event** (`POST /sessions/{id}/events`):

```json
{
  "input": [
    {
      "role": "user",
      "type": "message",
      "content": [{"type": "text", "text": "Analyze the Q3 sales trends in /mnt/session/uploads/data.txt"}]
    }
  ]
}
```

POST always returns JSON (echoing only the events you sent). The real-time event stream uses the **dedicated endpoint** `GET /sessions/{session_id}/events/stream`
(adding `Accept: text/event-stream` to the POST does **not** turn it into SSE); history and polling use `GET /sessions/{session_id}/events`.

Besides `message`, `input[].type` can send 5 more kinds: `interrupt` (cancel the current turn), `tool_approval_response` (tool approval response),
`tool_call_output`, `function_call_output` (fill in tool results), and `define_outcome` (declare the acceptance goal).
An approval response's `content[*].data` requires `batch_id` + `call_id` + `result` (`allow`/`deny`), plus `deny_message` when denying —
take `batch_id`/`call_id` from `stop_reason`'s `pending_batch_id`/`pending_call_ids` (the official OpenAPI's
`tool_confirmation` is lagging wording, field-tested as rejected by the server with 400; the full protocol is in [../tutorials/06-tool-approval.md](../tutorials/06-tool-approval.md)).

**The shape of the `session_status` event** (this is what tells you whether the turn has ended):

```json
{
  "type": "session_status",
  "content": [
    {"type": "data",
     "data": {"session_status": "idle", "stop_reason": {"type": "end_turn"}}}
  ]
}
```

- `session_status` and `stop_reason` live in the event's `content[*].data` (not at the event root); **the root of `GET /sessions/{id}` also carries `stop_reason`** (weak-interaction polling scenarios read it directly instead of digging through the event stream)
- `stop_reason` is an **object**, not a string — read `stop_reason.type`: `end_turn` / `requires_action` / `retries_exhausted`;
  the approval scenario's `requires_action` additionally carries `pending_call_ids` + `pending_batch_id` (required when sending the approval response back; see [../tutorials/06-tool-approval.md](../tutorials/06-tool-approval.md))
- Session states, four kinds: `idle` / `running` / `rescheduling` / `terminated`; treat only `idle` and `terminated` as "finished" —
  `rescheduling` is a transient state (in the SDK enum; not listed in the official state machine; never reproduced in field tests)
- The SDK event enum has 22 types; field tests show the server also pushes the out-of-enum `tool_approval_request` (approval request) — safely ignore everything unrecognized (enum in [../product/concepts.md](../product/concepts.md))

**Creating a Deployment** (requires `name` + `agent` + `initial_events`):

```json
{
  "name": "daily-order-summary",
  "agent": {"id": "agent_xxx", "version": 12},
  "environment_id": "env_xxx",
  "schedule": {"type": "cron", "expression": "0 9 * * 1-5", "timezone": "Asia/Shanghai"},
  "initial_events": [
    {"type": "message", "role": "user", "content": [{"type": "text", "text": "Summarize yesterday's order data"}]}
  ],
  "resources": [],
  "vault_ids": []
}
```

- Omitting `schedule` = manual triggering; `type` currently only `cron`; **`schedule.timezone` is required** (missing → 400 PARAMS_MISSING)
- Omitting `agent.version` takes the latest version; **pin the version for production** to keep scheduled-task behavior from drifting when the Agent changes
- **Deployments do not support `environment_variables`** (REST field test: POST accepts it without error but silently ignores it; the triggered session lacks the variable) — injecting credentials on scheduled pipelines can only wire `vault_ids`
- `initial_events` takes 1-50 items (empty array / 51 items both 400). `next_run_at` / `last_run_at` live **inside the `schedule` object**
  (not at the top level; values are UTC) — usable to verify the next trigger time

## ID prefixes (for identifying objects in log triage)

| Prefix | Object |
| --- | --- |
| `agent_` | Agent |
| `env_` | Environment |
| `sesn_` | Session (format `sesn_<ULID>`) |
| `sesrsc_` | Session mounted resource |
| `file_` | File |
| `vlt_` | Vault |
| `vcrd_` | Credential (a secret inside a vault) |
| `skill_` / `skillver_` | Skill / Skill version |
| `depl_` / `drun_` | Deployment / Deployment Run |
| `thrd_` / `sthr_` | Main thread / member sub-thread |
| `call_` | Tool call |

## Error response shapes

Three coexist in field testing (distinguish by trigger scenario):

```json
// (1) Business error (most common): code inside the error object, no status_code in the body, request_id is a UUID
{"type": "error", "error": {"code": "AGENT_010", "message": "..."}, "request_id": "5f3a..."}
// (2) 401 auth failure: code at the top level
{"request_id": "...", "code": "InvalidApiKey", "message": "..."}
// (3) Gateway 404 (nonexistent path): Spring style
{"timestamp": "...", "status": 404, "error": "Not Found", "path": "/api/v1/agentstudio/..."}
```

The `code` of a 400 varies by endpoint (`AGENT_010` / `invalid_parameter` / `PARAMS_MISSING`, etc.) — there is no unified
`InvalidParameter`. For more error codes, check skill `bailian-docs-llm-wiki` first.

## Related

- Getting started and minimal examples → [api-quickstart.md](api-quickstart.md)
- Choosing an integration shape → [patterns.md](patterns.md)
