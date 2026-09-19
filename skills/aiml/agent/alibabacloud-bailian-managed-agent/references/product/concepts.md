# Core Concepts and Resource Relations

> Source labels: `official docs` = live product/API docs (https://docs.agent.bailian.aliyun.com/zh/managed-agents ,
> index https://docs.agent.bailian.aliyun.com/llms.txt ); `whitepaper` = the official whitepaper ([whitepaper-source.md](whitepaper-source.md));
> `SDK field-test` = evidence from the official Python SDK's (`pip install dashscope`) real signatures, enums, and source comments;
> `REST field-test` = conclusions from live probes directly against the API (evidence grade equal to SDK field-test);
> `CLI` = `bl managed-agent` command and field evidence; `unverified` = no authoritative basis yet.
> **Wording priority: current official docs > archived whitepaper > CLI help**, consistent with SKILL.md. Field tests establish behavior only for their recorded date, region, version and workspace; investigate conflicts instead of letting old probes override newer contracts.
> Dated user-provided launch corrections are recorded in [status.md](status.md); historical `coming soon` labels do not override current status.
> When speaking to users, verify anything marked `unverified` first — do not state it as fact.

## Only 6 core objects to master (whitepaper)

| Concept | Role | Description |
| --- | --- | --- |
| Agent | Reusable capability definition | The combined configuration of model + system prompt + tools + MCP services + Skill; referenced by ID after creation, reused across sessions; **every save auto-generates a new version** |
| Environment | Sandbox configuration | The cloud container sandbox where sessions run; dependencies can be preinstalled |
| Session | One run instance | One run in which the agent executes a task in a given environment and produces results; **state is held server-side**, supporting interruption and resumption |
| Event | Interaction record unit | Messages, tool results, and status changes between the application and the agent — all recorded as events and persisted server-side |
| Vault | Centralized auth management | A "safe"-style central store for external-service API keys / tokens; **placeholder injection**: the sandbox only sees placeholders; real values are substituted only when the egress gateway hits a whitelisted host (see the Vault section) |
| Deployment | Scheduled triggering | With a fixed Agent + Environment + Vault configuration, sessions are launched on schedule to provide a periodic service |

**Nine API-layer objects** (whitepaper, API First chapter): Agent / Environment / Session / Event / File / Skill / Vault / Credential / Deployment — after Webhook's official launch on 2026-08-26 the real count is ten resource classes (see the Webhook section).
Create, query, update, archive, and schedule are all open (support varies per object: Agent is archive-only with no delete; File/Skill are delete-only with no archive; Deployment is archive-only — do not read this as "every object has the full operation set").

## Resource relations at a glance

```
Agent (model + prompt + tools + MCP + Skill)
  ├─ runs in → Environment (cloud container sandbox, preinstallable dependencies)
  ├─ gets credentials from → Vault (placeholder injection: the sandbox only sees BMA_SECRET_PLACEHOLDER_*; the real value exists only for the instant the egress gateway substitutes it)
  ├─ mounts → File (standalone resource, lifecycle decoupled from the session, reusable across sessions)
  └─ one run = Session ──produces──> Event stream (SSE real-time / pollable, persisted server-side)
                └─ may carry environment_variables (plaintext-injected sandbox env vars, for non-sensitive config)

Deployment = a fixed combination of Agent + Environment + Vault + a schedule → each trigger launches one Session
```

On the CLI side (`bl managed-agent`) these resources are declared in `agents.yaml` and driven through the `validate → plan → apply → destroy` IaC chain.

## Agent
- **Whitepaper**: a reusable capability definition composed of "model + system prompt + tools + MCP services + Skill"; referenced by ID; every save auto-generates a new version.
- **CLI**: the `agents:` node in `agents.yaml`; state carries `resource-version` (matching "every save generates a version").
  The environment / vault / memory stores it uses can be declared on it and overridden per session (`--environment` / `--vault` / `--memory-stores`).
- **Model identifier (REST field-test)**: the wire shape of `model` is `{"id": "…"}` (the SDK's `model` parameter is a string).
  `model.id` values observed in a live workspace include `qwen3.8-max` / `qwen3.7-max` / `qwen3.7-plus` / `qwen3.6-plus` /
  `qwen3.6-flash`, plus `auto`, `glm-5.2`, `deepseek-v4-pro`, etc. — **a flash tier exists, and non-Qwen models are supported**.
  **`qwen3-max` does not exist in field testing** (`400 AGENT_010 model does not exist`); legacy DashScope IDs (`qwen-max` / `qwen-plus` /
  `qwen-flash`) were not individually field-tested — promise customers only field-tested IDs. The full usable list defers to the console dropdown / Bailian's official support list.
- **The critical tool-config semantics (REST field-test, the most frequent pitfall)**: `default_config.enabled: true` inside `tools[]`
  **does not actually deliver tools to the model**; you must list every tool you want **individually in `configs[]` with `enabled: true`**.
  Writing only `default_config` without listing `configs` leaves the agent with just the platform-auto-injected `mark_artifacts`,
  after which every call fails with `TOOL_NOT_FOUND: Tool 'bash' not found. Available tools: ['mark_artifacts']`,
  and the turn ends with an apology like "I have no tools available". One Agent can attach at most 1 `builtin_toolkit`.
- **Unverified**: whether run-control fields such as max turns and timeouts are configurable.

## Environment (runtime / sandbox)
- **Whitepaper**: the cloud container sandbox where sessions run; dependencies can be preinstalled; container-level full isolation supporting code execution, file read-write, and network access;
  recyclable at session end; the sandbox can be persisted as a whole; **network-isolated with credentials never entering the sandbox**.
- **Configuration fields (official docs)**:

  | Field | Required | Mutable | Description |
  | --- | --- | --- | --- |
  | Name | Yes | Yes | Unique identifier within the workspace |
  | Description | No | Yes | Purpose statement |
  | Hosting type `config.type` | No | **No** | Currently only `cloud` (Bailian-hosted); **immutable after creation** |
  | Preinstalled packages `config.packages` | No | Yes | Declared grouped by package manager, auto-installed at environment creation. Official docs and the API schema declare only `apt` / `pip` / `npm`; the SDK enum also has `gem` / `cargo` / `go`, field-tested: **gem installs, cargo/go are silently ignored** (no error, no install) — promise customers only apt/pip/npm/gem |
  | Network policy `config.networking` | No | Yes | `unrestricted` allows all outbound access (**settable only via API; not shown in the console**) |
  | Scope `scope` | No | Yes | Defaults to `organization`; usable by all workspace members (settable only via API) |
  | Metadata `metadata` | No | Yes | Custom key-value pairs; no effect on runtime behavior |

- **Reusable**: environments are managed independently of agents and **can be bound and reused by multiple sessions**.
- **Archive vs delete (official docs)**: archive → the environment is retained but hidden from the default list (`include_archived` brings it back);
  delete → a hard delete; the configuration is wiped and unrecoverable.
  ⚠ **The official docs say "bound sessions keep working", which contradicts field testing**: after archiving, the environment deactivates immediately — new sessions bound to it get 404,
  and already-bound idle sessions can no longer receive messages (404 not_found). **Speak to customers per the field-tested wording: archiving means deactivation.** To retire one, archive it outright — do not count on a grace period.
- **CLI**: the `environments:` node can declare `config` (packages / networking etc.); its `files:` sub-key **is silently ignored by the CLI**
  (zod strips unknown keys — writing it has no effect and raises no error; `validate` passes everything). The real places for CLI-declared file mounts are top-level `files:` and
  `deployments.<name>.resources` — and `validate` requires `mount_path` to start with `/mnt/` in both places
  (rejecting `/uploads/`), which **deadlocks** against the runtime API's required `/uploads/` prefix. CLI-declarative file mounting currently cannot run end to end; mount files via API / console.
- **Not public in the official docs**: sandbox specs (CPU / memory / disk), per-session duration cap, egress allowlist granularity (only `unrestricted` observed so far),
  and the exact persistence boundary. When customers ask about specs, state honestly "not public in the docs; needs confirmation from the product team" — **do not estimate**.
- **Compliance note (official docs)**: the sandbox container is governed by Article 6 of the *Alibaba Cloud Product Terms of Service*; software the customer installs and its consequences are the customer's responsibility
  (mention this whenever a customer solution involves installing third-party software).

## Session
- **Whitepaper**: one run instance with server-held state; supports the **interruption mechanism** and **tool-call approval**; keeps context and file-system state across turns;
  task duration can reach minutes to hours, with disconnect auto-recovery and checkpoint resumption. **Billed only while "running"; idle is free.**
- **CLI**: `session run` (create session + send message + stream; `--output json` returns `{ session_id, provider, agent, events }`),
  `session send`, `session get` / `list` / `delete`, `session events --all`; `--no-stream` replaces SSE with polling.
- **State machine (official docs' three states + SDK enum)**: the official docs and GET session's `status` enum have only
  `idle` / `running` / `terminated` — **three states**; `rescheduling` exists only in the SDK's `SessionStatus` enum
  and has never been observed in a real session — **do not write a branch for it** when integrating.
  | State | Trigger | Next state | Operations available |
  | --- | --- | --- | --- |
  | `idle` | Creation completed, or a processing turn ends | Message received → `running`; archive/delete → `terminated` | Send messages, mount files, archive, delete |
  | `running` | Message received; agent starts processing | Completion → `idle`; unrecoverable error → `terminated` | Interrupt, approve tool calls |
  | `terminated` | Archived, deleted, or unrecoverable error | **Terminal; not recoverable** | View event history; start a new session |

  Integration code should treat `terminated` as terminal, and inspect `stop_reason` on `idle`; an idle event without a reason is transient, not proof of completion.
- **`stop_reason` (SDK/REST field-test)**: produced when returning to `idle`; **a JSON object, not a string**, shaped like `{"type": "end_turn"}`.
  It appears both in `session_status` events' `content[*].data` and **at the root of `GET /sessions/{id}` (SDK `retrieve()`)** —
  Python SDK `sessions.retrieve()` returns a typed `StopReason`; normalize it with `.to_dict()` before using `.get()` (SSE event parsing may already return a dict).
  Weak-interaction scenarios need not pull the event stream; after the session ends, a single retrieve gets the final result; the GET root also carries
  `stats` (active_seconds / duration_seconds) and `usage` (token counts with cache fields) — these three fields are
  absent from the official GET schema; trust the field test. `type` takes three values: `end_turn` (the model ended on its own),
  `requires_action` (**needs client intervention**, shaped `{type, pending_call_ids, pending_batch_id}` —
  there is no `event_ids` key; the official docs' wording there disagrees with the field test — do not copy it), and `retries_exhausted` (retries exhausted).
  Integrations that check only `idle` miss the `requires_action` branch and the task silently deadlocks.
- **Archive vs delete (official docs)**: archive → `terminated` but **event history is retained and queryable**; delete → a hard delete; metadata / event history / resource copies are all wiped.
  Always use archive when an audit trail matters.
- **Snapshot semantics (official docs)**: creating a session **snapshots the agent's latest version at that moment**; later agent edits do not affect in-flight sessions.
- **Session environment variables `environment_variables` (REST field-test, 2026-09-03)**: key-value pairs can be passed at session creation and are **plaintext-injected** into the sandbox process
  environment — the agent reads real values straight from `os.environ` in bash / python; both the create response and GET echo the field verbatim.
  Layered with Vault secrets: **non-sensitive config (API endpoints, log levels, feature flags) via environment variables; high-sensitivity secrets (API keys, tokens) into the Vault** (placeholder injection; see the Vault section).
  Note **Deployment does not support this parameter** (silently ignored when passed; REST field-test) — credential injection on scheduled pipelines can only rely on `vault_ids`.
- **Integration implication**: in multi-user systems use Session as the user / task isolation unit; event history doubles as the audit and frontend-replay data source.

## Event
- **Whitepaper**: messages / tool calls / MCP calls / status changes are all recorded as events; SSE pushes them in real time and persists them server-side —
  **customers need no self-built storage**; poll for the full event list when not subscribing to the stream.
  Console filter dimensions: All / User / Agent / Tool / Tool_output / Error / Model / System.
- **Full event types (SDK field-test)**: the server pushes **at least 23** `type` values (22 SDK enum members + the approval event
  `tool_approval_request`, which the SDK does not enumerate yet); the official docs' examples list only a few.
  Handle only what you care about; safely ignore the rest (more will be added in later versions):

  | Group | type |
  | --- | --- |
  | Body and thinking | `message` (assistant output, streamable in chunks; **`sequence_number` is observed to be always null** — chunks can only be concatenated by arrival order, not accumulated by sequence number), `reasoning` |
  | Tools | `tool_call` / `tool_call_output`, `function_call` / `function_call_output`, `mcp_call` / `mcp_call_output` |
  | Session and status | `session_status` (carries `session_status` and `stop_reason`), `session_updated`, `error` |
  | Sub-threads | `thread_created`, `thread_status`, `thread_message_sent`, `thread_message_received`, `thread_context_compacted` (**pushed only in multi-agent formations**; see the MultiAgent section)|
  | Model and objectives | `model_request_start`, `model_request_end`, `outcome_evaluation` |
  | Client-event echoes | `message`, `interrupt`, `tool_approval_response`, `tool_call_output`, `function_call_output`, `define_outcome` |

- **The client can send 6 types (SDK field-test)** — more than just `message`:

  | type | Purpose | SDK constructor |
  | --- | --- | --- |
  | `message` | Send a message; the agent enters `running` after sending | `user_message` |
  | `interrupt` | Cancel the current turn | `user_interrupt` |
  | `tool_approval_response` | Tool-call approval (allow / deny) | **No usable constructor** — the SDK's `user_tool_confirmation` emits type `tool_confirmation` and lacks `batch_id`, which the server rejects with 400; **you must hand-assemble it** (`content[*].data` with `batch_id` + `call_id` + `result`) |
  | `tool_call_output` | Fill in a built-in tool's result | `user_tool_result` |
  | `function_call_output` | Fill in a custom tool's result | `user_custom_tool_result` |
  | `define_outcome` | Declare the acceptance goal for this task | `user_define_outcome` |

  The standard resolution for `stop_reason.type == "requires_action"` is to send back a hand-assembled `tool_approval_response` (data with
  `batch_id` + `call_id` + `result: allow|deny`) — not to recreate the session. Approval-chain details (including the
  "HTTP 200 does not mean the approval was accepted" pitfall) are in [../tutorials/06-tool-approval.md](../tutorials/06-tool-approval.md).
- **Block types (SDK field-test)**: event `content[*].type` takes `text` / `image` / `audio` / `data` / `file` / `refusal` / `error`;
  `role` takes `user` / `assistant` / `tool`.
- **Thread fields are directional (SDK/REST field-test, the most frequent confusion source)**: in **server-pushed events the top-level field is `thread_id`**
  (main thread `thrd_` prefix; member sub-threads `sthr_` prefix); only when the **client sends** a targeted event (approval, interrupt) is the top-level field named
  `session_thread_id`. The `content[*].data` of `thread_created` / `thread_status` events additionally embeds a key *named*
  `session_thread_id` — the two names point in opposite directions; do not mix them up. Ignorable for a single agent; in a formation, split member output by top-level `thread_id`
  (the event-list API has no official thread filter parameter; field-tested `?thread_id=` is undocumented but works; see the MultiAgent section).
- **Launched**: multimodal events (mixed image and text), Delta incremental returns and Agent Thinking events. Launch status: [2026-09-18 user confirmation](status.md); verify current event schemas before writing integration code.
- **CLI**: `initial_events` may use `user.message` / `system.message`; `user.define_outcome` is dropped by Bailian with a diagnostic.
- **Integration details** (event parsing, SSE vs polling, `requires_action` handling) are in
  [../integration/api-quickstart.md](../integration/api-quickstart.md).

## Vault (secret store)
- **Whitepaper**: centrally manage external services' API keys / tokens; plaintext is never echoed back. The sandbox receives placeholders rather than direct secret environment values (see below). This does not prevent a remote service from echoing a credential in its response.
- **CLI**: the `vaults:` node; sessions can override (`--vault`).
- **Two-level structure (official docs)** — Vault container + Credential (credentials are created under
  `/vaults/{vault_id}/credentials`, prefix `vcrd_`); each credential = display name + variable name + variable value + an **egress network allowlist**;
  tools reference credentials **by variable name**; after saving, plaintext is never echoed again. The rotation mechanism is still unpublished (unverified).
- **Placeholder injection model (2026-09 breaking change, REST field-test 2026-09-03)**:
  - Credential structure change: `auth.networking.allowed_hosts` is now **required** (omitting it → 409 `CREDENTIAL_AUTH_NETWORKING_ERROR`
    "egress network addresses cannot be empty"); `allowed_hosts` must be nested inside the `networking` object (the old top-level form no longer works).
  - Injection semantics change: in a session with a Vault attached, `os.environ` inside the sandbox yields **placeholders**
    `BMA_SECRET_PLACEHOLDER_<variable-name>`, **no longer real values**. Do not send requests to credential-echo services or log authentication headers: response bodies can still carry secrets into the sandbox, model context, and event history.
  - Egress gateway substitution: HTTPS requests leaving the sandbox pass through a **transparent MITM gateway** (no proxy env vars; intercepted at the network layer); when the request
    host hits that credential's `allowed_hosts`, the gateway **replaces the placeholder in the `Authorization` header with the real value** before forwarding;
    on a host miss the placeholder passes through as-is (real secrets are never leaked to non-whitelisted destinations).
  - Field-tested boundaries: substitution applies only to the `Authorization` header (other headers such as `X-Api-Key` are not substituted); the gateway locates the credential **by host**
    (it does not parse the placeholder variable name — with multiple credentials on one host the substitution behavior is ambiguous; recommend one credential per host); the archived test encountered a gateway certificate missing from the sandbox CA store. This is not a universal current limitation: retain TLS verification and configure a trusted CA when required (see cookbook/08 troubleshooting).
  - The full chain and the curl field-test walkthrough are in [../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md).
- **Non-sensitive config does not belong in the Vault**: session-level `environment_variables` (plaintext passthrough into the sandbox) is the simpler choice; see the Session section.

## File / Resource (files and resource mounting)
- **Whitepaper**: files are **standalone resources** mounted by `mount_path`; their lifecycle is **decoupled** from sessions and they can be reused by multiple sessions
  (typical: one master data file mounted into several analysis sessions).
- **Quotas (official docs)**: single file ≤ **10 MB**; per-workspace total capacity ≤ **100 GB**; retention **30 days**, after which automatic cleanup may occur
  (long-term retention requires periodic re-upload).
- **Review (official docs)**: after upload a file enters `checking`; it becomes mountable once it turns `available`; failures are `rejected` / `type_rejected`.
  Mounting immediately after upload fails — wait for the review to pass.
- **Mount path prefix (official API + field test, the most frequent pitfall)**: `mount_path` **must start with `/uploads/`** —
  filling `/workspace/...` yields `Invalid resource` at session creation, and at runtime append time it yields
  `Field 'mount_path' must be an absolute path under /uploads/'`. The real sandbox path = `/mnt/session` + `mount_path`:
  | What you fill in | What the agent actually sees |
  | --- | --- |
  | `/uploads/data.txt` | `/mnt/session/uploads/data.txt` |
  | `/uploads/sales.xlsx` | `/mnt/session/uploads/sales.xlsx` |
  **The system prompt must state the real path**; stating the filled-in value makes the agent unable to find the file.
  (A few official concept pages still say "prefix auto-added" with `/workspace/` examples — outdated wording contradicting the official API pages and the field test — teach per this table.)
- **Session isolation (official docs)**: at mount time the server makes an internal copy and mounts it into the sandbox (resource ID prefix `sesrsc_`); modifications inside the session do not affect the original file;
  unmounting cleans up only the in-session copy.
- **Runtime mounting (official docs, usable now)**: after session creation, `POST /sessions/{id}/resources` appends mounts that take effect immediately without restart;
  list / get / unmount endpoints also exist. **The whitepaper marks dynamic Resource add/remove as `[coming soon]`, but the official API docs already open it — present as launched.**
- **CLI**: files upload at `apply`; CLI `validate` requires `mount_path` in `deployments.<name>.resources` and top-level `files:`
  to start with `/mnt/` (rejecting `/uploads/`), which **deadlocks** against the runtime API's required `/uploads/` prefix
  — CLI-declarative file mounting currently cannot run; mount files via API / console (see [../tutorials/03-mount-files.md](../tutorials/03-mount-files.md)).
- `[coming soon]` (whitepaper): Github / Gitee repositories mounted by URL + PAT, cloned by default to `/data/workspace/<repo-name>` —
  a mount type **different** from file mounting; do not mix up the paths.
- **Files support deletion only, not archiving** (official docs); copies already mounted into sessions are unaffected by deleting the original file.

## Skill (Agent Skills)
- **Whitepaper**: package end-to-end task workflows as skills; the agent **decides autonomously when to invoke** one from its `SKILL.md` description; one skill can be reused by multiple agents.
  - Official skill marketplace: already includes PDF / Word / Excel / PowerPoint processing, bailian-cli, and more; ready out of the box.
  - Custom skills: upload a zip (**≤10MB, `SKILL.md` at the root**); automatic review: `checking` → `active` (mountable) / `rejected` (not mountable).
- **CLI**: `bl managed-agent skill-list --source official|custom|all`; `--source all --output json` fetches both catalogs in one call (with `source`, `description`) — ideal for letting an agent choose.
- **Version management (official docs)**: the Skill API supports uploading new versions, querying by version, listing all versions, and getting a package download URL for a given version;
  Skills support hard deletion only, not archiving.
- **Skill binding (REST field-test + official docs)**: each item under `agent.skills` is
  `{type: "official"|"customer", skill_id: "skill_…", version: "<specific version>"}` — using name fails,
  and you cannot pin latest; a specific version is mandatory; `GET /skills/{bad}` → **409** code 11300001 (not 404).

## Tool and MCP
- **Built-in tool set (`type: "builtin_toolkit"`, at most 1 per Agent)**:
  - **Six shell/file tools**: `bash` / `read` / `write` / `edit` / `glob` / `grep`.
    They must be listed individually in `configs[]` (see "The critical tool-config semantics" under Agent).
  - `mark_artifacts`: **auto-injected by the platform runtime** — callable without any config. Its purpose is marking "which files this turn produced" for chat UIs
    wrapped by the business side; **fetching outputs does not need it** (outputs go through `/mnt/session/outputs/` auto-scan + the Files API).
  - `download_file`: **officially announced as deprecated**. The whitepaper and the official `build-agent/tools` page still list it (docs lag the announcement);
    during the transition some workspaces can still call it, but **do not add it to docs or new configs, do not depend on it**.
  - An agent with Skills attached also gains `activate_skill` / `read_skill_file` at runtime.
  - **Do not assume a successful local validation proves a tool exists**;
    after creation, read back the agent's `tools` to confirm what actually took effect.
- **Internet access**: built-in `web_search` and `web_fetch` are launched and preferred for search and webpage reading; `browser_use` is available **through MCP**, not as a built-in tool. See [status.md](status.md). Only use the marketplace `WebSearch` MCP service (`bailian_web_search`) for an explicitly selected MCP integration or a verified built-in capability gap (example in [../cookbook/04-multi-agent-custom-proposals.md](../cookbook/04-multi-agent-custom-proposals.md) §1.1). Verify current configuration fields before execution.
- **MCP mounting (REST field-test, two steps)**:
  1. The Agent's top-level `mcp_servers: [{"type": "official"|"customer", "name": "<service name>"}]` declares the service to connect;
  2. Then add to `tools[]` a `{"type": "mcp_toolkit", "mcp_server_name": "<same name>", "configs": [{"name": "<tool name>", "enabled": true}]}`
     to **enable tools one by one** — skipping step 2 leaves the tools silently missing at runtime.
  - **The two types validate at completely different times**: `official` (marketplace) **does not check existence at declaration time**; a mistyped name still creates successfully,
    and the failure only shows up at runtime as "no tools available" — expensive to troubleshoot; `customer` (custom) **validates hard**; an unregistered name fails immediately with
    `400 AGENT_010 MCP Server validation failed: error querying MCP details`. So the iron rule for custom MCP: **register in the console first, then write it into the config**.
  - Marketplace services are called through the platform proxy and **need no credentials from you**; the secret filled in when registering a custom MCP is stored on the Bailian side and attached by the platform at call time —
    it does not go into the Vault or the prompt.
  - **Custom MCP currently has no management API**: registration, renaming, and deletion are console-only
    (`https://agent.console.aliyun.com/managed-agent/mcp-manage/custom`). Four integration types: plugin / script deployment / AI gateway / Alibaba Cloud OpenAPI;
    an already-running MCP endpoint can be registered via "script deployment → HTTP deployment", **incurring no deployment fee**.
  - For MCP marketplace search see skill `bailian-cli` (`bl mcp tools --server <name>` lists the tool names a service provides).

## Deployment (managed scheduling)
- **Whitepaper**: crystallize an agent into a managed deployment that launches sessions on a schedule with a fixed Agent + Environment + Vault configuration;
  supports **create, pause/resume, archive, trigger run (run), and run-record queries (list-runs / get-run)**; every run is recorded.
  The whitepaper marks Webhook `[coming soon]`, but **REST field-testing shows it usable**; see the Webhook subsection below.
- **CLI**: the `deployments:` node, on the same IaC chain as Agent (no imperative CRUD bypassing state).
  `initial_events` needs at least one `user.message` or `system.message`; the `schedule` is executed by the **Bailian server**;
  `apply` creates, `destroy` archives. Old state files simulating Deployments may record an empty `remote_id`; after upgrading, `plan` shows a materialize update.
- **Key fields (official docs + field test)**: required `name` + `agent` + `initial_events` (1-50 items);
  omitting `schedule` means manual triggering; passing it means `{type: "cron", expression, timezone}` (`type` currently only `cron`) —
  **when `schedule` is present, `timezone` is required** (missing → 400 PARAMS_MISSING; the official schema does not mark it required, but the field test shows it enforced);
  omitting `agent.version` takes the latest version — **for production, pin the version** to keep scheduled-task behavior from drifting when the Agent changes;
  the next trigger time lives in `schedule.next_run_at` / `schedule.last_run_at` (**not at the top level**), in UTC.
- **Positioning pitch**: Deployment is the shape of "letting the agent work on its own on schedule" — fits daily reports / inspections / batch processing; plain conversational integration only needs Session.

## MultiAgent (multi-agent collaboration, official docs already open)
- **How to configure**: pass the `multiagent` field when creating/updating an Agent — `type` currently supports only `coordinator` (coordinator topology);
  `agents` is the list of formation entries, 1-20 of them.
- **Formation entries**: `type: "agent"` (references another Agent; requires `id`, optional `version`, latest if omitted) or
  `type: "self"` (the coordinator itself; at most one in a formation).
- **Omitting `multiagent` or passing an empty array `[]`** = runs as a single agent (an empty array clears the formation).
- **The coordinator is not a special type** (SDK field-test): the `POST /agents` request body has no `type` field;
  a coordinator is just a normal Agent carrying `multiagent` — it also has its own `model` / `system` / `tools` / `skills`.
- **Dispatch rules can only live in the coordinator's system prompt** (inferred from the field structure): `multiagent` has only
  the two keys `type` and `agents`, and roster entries have only `type` / `id` / `version` — **no routing-rule configuration whatsoever**.
- **Orchestration tools are auto-injected by the platform** (REST field-test): **no need to declare them in `tools`** — the coordinator receives
  `create_agent` / `list_agents` / `wait_for_agents` at runtime, members (workers) receive `submit_result`,
  surfacing as ordinary `tool_call`s in the main-thread event stream.
- **The runtime object SessionThread** (SDK definition): fields are `id` / `session_id` / `parent_thread_id` /
  `title` / `status` / `created_at` / `updated_at`. `parent_thread_id` says "which thread spawned this one".
- **Session Threads API (REST field-test: usable, not yet in the official public docs)** — four endpoints, so thread-level observation need not rely only on event-stream aggregation:
  `GET /sessions/{id}/threads` (list; one row per member agent, with `status` and `agent.version`) /
  `GET /sessions/{id}/threads/{tid}` (detail) /
  `GET /sessions/{id}/threads/{tid}/events` (**the shortest path to see what one member did**) /
  `POST /sessions/{id}/threads/{tid}/archive` (archive).
  Three boundaries: **the coordinator's main thread (`thrd_` prefix) is not in the threads collection** — GET with its id returns `400 invalid_parameter`;
  **archived threads also return 400** (but their events remain queryable); **there is no thread-level SSE endpoint**
  (`.../threads/{tid}/events/stream` returns `404 not support`) — the only real-time stream is the Session one.
- **The 5 formation-specific event types** (within the 23 above): `thread_created` (thread spawned for a task) / `thread_status` /
  `thread_message_sent` (coordinator → member) / `thread_message_received` (member → coordinator) /
  `thread_context_compacted` (sub-thread context compaction).
- **Integration impact**: all members' output mixes into one SSE stream, each event carrying top-level `thread_id` — **real-time splitting must happen client-side**.
  When querying history, the official spec declares only ordering (`order`) and time-window (`created_at` four operators) filters — `types` is an
  undocumented parameter (single values work in field testing; the SDK's multi-value join has a bug that silently returns 0 rows); additionally, field testing shows
  `GET /sessions/{id}/events?thread_id=sthr_xxx`
  works as an **undocumented** parameter (curl yes, SDK not exposed), or just use `.../threads/{tid}/events` above.
  Client-sent events (approval, interrupt) can also carry `session_thread_id` to target a specific member thread.
- **Note**: the whitepaper marks MultiAgent `[coming soon]`, but the official docs already have the config page and API fields — **present as launched**.
- **Unverified** (neither official docs nor SDK state it; verify before answering customers): the rules by which the coordinator picks members, whether members run in parallel or serially,
  whether members share an Environment, whether they inherit Vaults and mounted files, formation billing wording, and the `thread_status` enum values.

## Webhook (event notifications, REST field-test: usable)
- **Positioning**: replaces "polling to ask if it finished" with platform-push. A **workspace-level standalone resource** on par with Agent / Session / Deployment,
  ID prefix `wep_`, **at most 20 per workspace**. The whitepaper marks it `[coming soon]`; the official changelog announced it live on **2026-08-26**, and field tests can create and receive.
- **Subscribes to named events — 32 across 9 categories, no `*` wildcard**: Session control plane (created / updated / archived / deleted),
  Session run status (status_run_started / status_idled / status_terminated),
  Session Thread (thread_created / thread_run_started / thread_idled / thread_terminated),
  Agent, Deployment, Deployment Run (started / failed / succeeded), Environment, Vault, Vault Credential.
- **The event body carries no resource content**: only the resource id and event type; to get results, query the corresponding API with `data.id`.
- **Endpoints (official API docs + field test)**: `POST /webhook_endpoints` (create) / `GET /webhook_endpoints` (list) /
  `GET /webhook_endpoints/{id}` (detail) / `PUT /webhook_endpoints/{id}` (update description / url / events; omitted fields unchanged) /
  `POST /{id}/enable`, `POST /{id}/disable` (toggle) /
  `POST /{id}/test` (sends a synthetic `webhook.test` self-check) / `POST /{id}/reset_secret` (rotate the secret; the old one dies immediately) /
  `GET /{id}/events` (delivery history, last 7 days) / `DELETE /{id}` (hard delete).
- **Three things you must know**:
  1. `signing_secret` **appears exactly once — in the create and reset_secret responses**; no query ever returns it again; store it at creation time;
  2. `status` is **uppercase** `ACTIVE` (Deployment's is lowercase `active` — enum styles differ per resource; clients must not pattern-match only one);
  3. URL validation is blacklist-style: `webhook.site` / `*.beeceptor.com` and similar temporary receivers are rejected (`invalid webhook url`, 11800016),
     as are private / loopback / link-local / reserved addresses. These are archived observations, not a guarantee that other public domains pass. For repository creation examples/evaluations, use `https://www.baidu.com` and verify creation/read-back only; ACTIVE subscriptions may deliver without a test call, so live creation must use a customer-controlled HTTPS receiver or a verified disabled/no-delivery configuration.
- **Delivery semantics (field-tested; receivers must design for this)**: **at-least-once** — duplicate deliveries really happen, **and so does out-of-order delivery** —
  receivers must be idempotent and treat query APIs such as `GET /sessions/{id}` as the source of truth; do not infer progress from arrival order.
  One more field-tested note: **the three `deployment_run.*` events were subscribed but never delivered** — do not rely solely on Webhook for scheduled-task completion notifications today.
- **Health observability**: the resource carries `last_success_at` / `last_failure_at` / `consecutive_fail`.
- Full walkthrough (receiver code, signature-verification algorithm, response-code retry semantics table) → [../cookbook/06-webhook-event-notifications.md](../cookbook/06-webhook-event-notifications.md)

## Memory Store (working memory)
- **Launched**: Memory Store is MA built-in memory, primarily for working memory and task context across sessions. Source: [2026-09-18 user confirmation](status.md); the whitepaper label is historical.
- **CLI**: `memory_stores:` is already declarable; an Agent can bind several (`--memory-stores` overrides).
- **Different product**: Bailian Memory Library primarily provides personalized memory scoped by a supplied `UserId`. It is not MA Memory Store. Do not reuse its API endpoints, identifiers or UserId semantics as the MA native Memory Store contract.
- Verify MA-specific current docs and CLI help for binding, lifecycle and read/write configuration; the launch confirmation does not establish those schemas. File mounting remains an option for persistent files, not a required replacement for an unavailable Memory Store.

## State (CLI-local state, not a product object)
- `state list` / `show` inspect tracked resources; `state import --address <provider.type.name> --remote-id <id>` adopts existing remote resources.
- `state rm` **removes only local tracking**; `destroy` **actually deletes/archives the remote resource** — keep the distinction crisp when explaining to users.

## Terminology consistency conventions

- Use "Managed Agents" or "CMA"; do not write the singular "Managed Agent" as a product name (external materials use the official name).
- Use "Flow Agent (agent app 2.5)" for the conversational-app form; never conflate it with Managed Agents.
- Use "Session" rather than "conversation thread"; use "Environment" for the runtime, saying "sandbox" only when explaining the isolation mechanism.
- Use "Deployment", not "scheduled task" (scheduling is merely one way a Deployment triggers).
