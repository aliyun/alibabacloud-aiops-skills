# Multi-Agent: Coordinating a Team of Specialists

> This recipe shows how to use the `multiagent` coordinator pattern of Bailian Managed Agents to organize a team of specialist sub-agents that collaborate on a sales proposal, and how to observe and live-render each sub-agent's run precisely via the Session Threads API and the Session-level event stream. Examples uniformly use curl (REST).

Using Bailian Managed Agents' multi-agent coordinator pattern, we automate sales-proposal writing for the fictional company Northstar (selling a workflow-automation platform to mid-market operations teams). The status quo: sales reps hand-craft a custom proposal for every prospect — research what companies in that segment typically care about, pick two relevant cases from the case library, compute pricing from the internal rules sheet, and assemble a two-page document. Every step uses a different data source and different judgment.

One coordinator Agent runs three specialists: the researcher uses web search to find what the segment typically prioritizes; the case-study picker reads the case library and picks the two best matches; the pricing modeler reads only the rules file and the seat count. Add one more, a checker, that runs an alignment self-check before the coordinator starts writing. The coordinator sequences them and writes the proposal.

---

## 0. Environment variables and models

```bash
export BASE="https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
export API_KEY="<your DashScope API Key>"
```

All requests carry `Authorization: Bearer $API_KEY`. The multi-agent `multiagent` configuration and Session event stream are Managed Agents capabilities; currently `cn-beijing` only.

For the model ID use a field-tested one: `qwen3.8-max` / `qwen3.7-max` / `qwen3.7-plus` (generic IDs like `qwen3-max` are rejected with 400). Every roster member is a full Agent, **so different models can be mixed by role** — flagship models for high-value writing/coordination, cheaper tiers for mechanical file-reading and rule-application; cost separation is just a matter of different model IDs. This example uniformly uses `qwen3.7-plus`.

Two traps that come up repeatedly in multi-agent scenarios, stated up front:

> **The builtin toolkit has no web search.** The 6 configurable core tools of `builtin_toolkit` are `bash`, `read`, `write`, `edit`, `glob`, `grep` (`download_file` is officially offline — stop adding it; `mark_artifacts` is auto-injected by the runtime, no declaration needed). Declaring `"name": "web_search"` is rejected outright (`400 AGENT_010 unknown builtin tool: web_search`). For a researcher that goes online, the only sanctioned route is mounting an MCP marketplace search service (this example uses the marketplace `WebSearch` service, tool name `bailian_web_search`).

> **`default_config.enabled: true` does not deliver the tools to the model.** Both `builtin_toolkit` and `mcp_toolkit` require every tool explicitly `enabled: true` in `configs[]`, otherwise the agent holds only the platform-injected `mark_artifacts` (01 covered this trap; it applies to multi-agent members too).

---

## 1. Define the three specialist sub-agents

Each sub-agent has its own system prompt, output shape, and **only the tools it needs**. The researcher has search only; the case-study picker reads only the local library; the pricing modeler reads only `pricing_rules.md`. Role-scoped tooling prevents the pricing modeler from pulling competitor numbers off the web, and keeps the whole case library out of the coordinator's context.

Bailian's orchestration tools are **auto-injected** by the platform in multiagent mode — no `tools` declaration needed (field-tested: the coordinator receives `create_agent` / `list_agents` / `wait_for_agents`; workers receive `submit_result`).

> Note down the `id` (shaped like `agent_<ULID>`) returned by each `POST /agents` below — they go into the coordinator's roster later.

### 1.1 The researcher: prospect_researcher (search MCP only)

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prospect_researcher",
    "description": "Researches what companies in a given industry segment and size tier typically prioritize.",
    "model": { "id": "qwen3.7-plus" },
    "system": "You are an industry researcher. Given a prospect'\''s industry segment and size tier, use the bailian_web_search tool to research: the segment'\''s strategic priorities, recent moves/trends, and common operational pain points. When done, return strict JSON: {\"priorities\":[...],\"recent_moves\":[...],\"pain_points\":[...],\"sources\":[...]}. Research only; do not write the proposal.",
    "mcp_servers": [ { "type": "official", "name": "WebSearch" } ],
    "tools": [
      { "type": "builtin_toolkit", "default_config": { "enabled": false },
        "configs": [ { "name": "read", "enabled": true } ] },
      { "type": "mcp_toolkit", "mcp_server_name": "WebSearch",
        "default_config": { "enabled": true },
        "configs": [ { "name": "bailian_web_search", "enabled": true } ] }
    ]
  }'
```

`mcp_servers.name` is the marketplace service's code (existence is not validated at declaration time — a wrong name fails silently; 02 covered the troubleshooting method). Marketplace services are called via the platform's proxy; you provide no credentials. To confirm which tool names a service offers: `bl mcp tools --server WebSearch`.

### 1.2 The case-study picker: case_study_picker (local library only)

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "case_study_picker",
    "description": "Selects the two most relevant case studies for a given prospect.",
    "model": { "id": "qwen3.7-plus" },
    "system": "The case library lives at /mnt/session/uploads/case_studies/; every file is a customer story. Given the prospect'\''s industry/size/priorities, read through the whole library, score each case for fit with the prospect'\''s priorities, and pick the two best matches. Return strict JSON: {\"picks\":[{\"file\":...,\"customer\":...,\"why_relevant\":...},...]}. You may only read local files; no internet access.",
    "tools": [
      { "type": "builtin_toolkit", "default_config": { "enabled": false },
        "configs": [
          { "name": "read", "enabled": true },
          { "name": "glob", "enabled": true },
          { "name": "grep", "enabled": true }
        ] }
    ]
  }'
```

### 1.3 The pricing modeler: pricing_modeler (rules file only)

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pricing_modeler",
    "description": "Builds two or three pricing options from the rules file and a seat count.",
    "model": { "id": "qwen3.7-plus" },
    "system": "The pricing rules live at /mnt/session/uploads/pricing_rules.md. Given a seat count and a usage tier, build exactly three tiers from the rules file alone: conservative (annual billing, lower unit price), flexible (monthly billing, higher unit price), and if seats>500 append an enterprise option (with platform fee). Give each tier a year-one total. Return strict JSON: {\"options\":[{\"name\":...,\"structure\":...,\"year_one_total\":...},...]}. No internet access; do not cite external competitor prices.",
    "tools": [
      { "type": "builtin_toolkit", "default_config": { "enabled": false },
        "configs": [ { "name": "read", "enabled": true } ] }
    ]
  }'
```

---

## 2. Add a checker: proposal self-check before writing

Each of the three specialists hands in one local conclusion, and none of them owns "whether the three conclusions together make sense". So the roster gets one more sub-agent, `proposal_checker`: before the coordinator starts writing, it gates whether the case picks and the pricing framework align with the prospect's priorities.

The coordinator delegates to it once before writing; it reads the research findings, case picks, and pricing framework, judges whether the three are mutually consistent and whether they hit the prospect's most pressing pain points, then returns one verdict plus revision suggestions. It is an ordinary worker like the other specialists: delegable, message-passing, running in its own thread and context.

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "proposal_checker",
    "description": "Sanity-checks whether the picked case studies and pricing framework match the prospect priorities before writing.",
    "model": { "id": "qwen3.7-plus" },
    "system": "You are the proposal checker; run one alignment check before the coordinator starts writing. You will receive: the prospect profile and priorities, the two picked case studies, and the three-tier pricing framework. Judge: do the picked cases hit the prospect'\''s most pressing pain points? Is the pricing tiering self-consistent with the seat/usage tier? Anything misaligned with the priorities? Return strict JSON: {\"aligned\":true|false,\"issues\":[...],\"suggestions\":[...]}. Judgment only — do not edit drafts or write the proposal.",
    "tools": []
  }'
```

> The checker is pure judgment and mounts no tools (leave `tools` as an empty array; 03 verified that a pure-LLM agent without tools runs fine). It carries judgment-type work, so you can set its `model.id` to a stronger model than the other workers for better judgment — capability/cost tiering is achieved by choosing different model IDs; the `model` field has no effort-style reasoning-tier parameter.

> **Note**: member types of `multiagent.agents[]` (field-tested): `{"type":"agent","id":...}` references an already-created sub-agent, optionally with `version` to pin a version (see §3.4); `{"type":"self"}` makes the coordinator itself delegable, **at most 1** — writing two fails with `AGENT_010 multiagent.agents can contain at most one entry of type self`.

---

## 3. Give the team its materials and wire up the coordinator

### 3.1 Materials list

**7 short case studies** (covering healthcare / manufacturing / logistics / retail / financial services / public sector), enough to watch the picker choose the two that fit the prospect. Each case carries title/industry/employees/summary:

- **St. Clair Health**: regional hospital network, 6200 staff, credentialing and prior-authorization flows scattered across 11 systems → consolidated into 3 automated flows; prior-auth turnaround down 58%, $1.9M saved per year.
- **BlueRidge Health Plan**: regional payer, 2800 staff, 19% of claims-exception queue emails needed rework → exception routing automated end to end; rework down to 6%, claims 11 days faster on average.
- **Calder Manufacturing**: industrial, 3100 staff, purchase-order approvals averaged 9 days → PO cycle down to 2.1 days, maverick spend down 14%.
- **Northwind Logistics**: 3PL, 4400 staff, carrier onboarding took 3 weeks each → down to 4 days; 22% more carriers activated in Q1.
- **Harborview Retail Group**: specialty retail, 5600 staff, store inventory exceptions handled via Slack + spreadsheets → exception triage automated across 140 stores; stockouts down 31%.
- **Aperture Payments**: financial services, 1900 staff, KYC and merchant onboarding averaged 6 business days → SLA down to 36 hours, 2.4x throughput with the same headcount.
- **Summit County Government**: public sector, 3700 staff, building permits moved as paper packs across five departments → one digital intake with parallel review; median permit time 41 → 17 days.

**Product and pricing materials**:

- **PRODUCT one-pager**: Northstar is a workflow-automation platform for mid-market operations teams; core capabilities — visual flow building, 200+ SaaS connectors, role-based approvals, SOC 2 Type II; typical results 40-60% reduction in manual tickets, first workflow live in 3 weeks.
- **PRICING rules**: $65/seat/month, or $52/seat/month billed annually; usage tiers light 1.0x / standard 1.15x / heavy 1.30x multiplied onto the unit price; enterprise tier (>500 seats) adds a $48,000/year platform fee and drops the annual unit price to $44/month; all options include onboarding; the enterprise tier includes a dedicated CSM.

### 3.2 Upload the 9 files

Upload the 7 case .md files, `product_one_pager.md`, and `pricing_rules.md` one by one. Upload uses multipart; after upload you must poll `GET /files/{id}` until `status=available` before mounting.

```bash
# Upload one by one; here one case file as the example
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -X POST "$BASE/files" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@st_clair_health.md"
# Take file_id from the response, then poll:
# curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 "$BASE/files/<file_id>" -H "Authorization: Bearer $API_KEY"  -> status=available
```

Repeat for all 9 files, noting each `file_id`.

### 3.3 Create the Environment (sandbox)

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/environments" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "northstar-proposal-env",
    "config": {
      "type": "cloud",
      "networking": { "type": "unrestricted" }
    }
  }'
```

> The researcher's MCP search is proxied by the platform and does not use the sandbox network, but the picker and the pricing modeler must read mounted files (sandbox tools), so the Environment is still required. `networking.type` currently takes `unrestricted` (all outbound allowed); for tighter egress or allowlist policies, follow Bailian's official capabilities. The response `id` is shaped like `env_<...>`.

### 3.4 Create the coordinator Agent (attach the roster)

The coordinator references the four sub-agents above (three specialists + the checker):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "proposal_coordinator",
    "description": "Assembles a tailored sales proposal by orchestrating specialists.",
    "model": { "id": "qwen3.7-plus" },
    "system": "You are the proposal coordinator, responsible for assembling a tailored sales proposal. Given a prospect name and profile, orchestrate the team in order:\n1) Send the industry and size to prospect_researcher.\n2) When the researcher returns, send industry/size/priorities to case_study_picker.\n3) Send the seat count and usage tier to pricing_modeler.\n4) Before writing, send the research findings, case picks, and pricing framework together to proposal_checker for the alignment check. If the check finds misalignment, adjust the cases or pricing tiers per its suggestions before continuing.\n5) Read /mnt/session/uploads/product_one_pager.md, then write /mnt/session/outputs/proposal.md containing: Executive summary (tied to prospect priorities) / How we help (from the one-pager) / Proof (the two cases) / Investment (pricing options) / Next steps. Keep it within two pages.\nYou do no specialist work yourself; you only decide ordering, handoffs, and the final writing.",
    "tools": [
      { "type": "builtin_toolkit", "default_config": { "enabled": false },
        "configs": [
          { "name": "read",  "enabled": true },
          { "name": "write", "enabled": true }
        ] }
    ],
    "multiagent": {
      "type": "coordinator",
      "agents": [
        { "type": "agent", "id": "<agent_id_prospect_researcher>" },
        { "type": "agent", "id": "<agent_id_case_study_picker>" },
        { "type": "agent", "id": "<agent_id_pricing_modeler>" },
        { "type": "agent", "id": "<agent_id_proposal_checker>" }
      ]
    }
  }'
```

The coordinator's returned `id` (`agent_<ULID>`) becomes `$AGENT_ID`.

> **Roster-member version semantics (field-tested, three controlled experiments)**:
>
> | Roster member form | Version actually used at runtime |
> |---|---|
> | `{ "type": "agent", "id": "agent_xxx" }` (no version) | **The member's latest version at the moment of each delegation (create_agent)** |
> | `{ "type": "agent", "id": "agent_xxx", "version": N }` | **Pinned to version N**, no matter how the sub-agent changes afterwards |
>
> "Without version" pins neither at coordinator creation nor at Session creation — field-tested: with the coordinator untouched, after upgrading pricing_modeler from v1 to v2, a new Session's delegated pricing thread used v2 directly; upgrading to v3 after Session creation but before sending the message still yielded threads on v3. In other words, **editing a sub-agent requires no coordinator update**; conversely, if you want "frozen, reproducible team configuration", write `version` explicitly on the member — the platform accepts and echoes it (when GETting the coordinator, the member object carries `version: N`).
>
> These semantics are the dual of 03's Session version pinning: the Session's `agent` field pins the coordinator's own version snapshot, the roster's `version` pins the member reference; leave either unwritten and it means "take the latest".

### 3.5 Start the Session (mount the 9 file resources)

`mount_path` **must start with `/uploads/`**; the actual in-sandbox path is `/mnt/session` + mount_path. The 7 cases mount at `/uploads/case_studies/<slug>.md`, the other two at the `/uploads/` root. The instruction text below uses the **actual paths** `/mnt/session/uploads/...`.

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "'"$AGENT_ID"'",
    "environment_id": "'"$ENV_ID"'",
    "title": "Meridian Health proposal",
    "resources": [
      { "type": "file", "file_id": "<file_st_clair>",   "mount_path": "/uploads/case_studies/st_clair_health.md" },
      { "type": "file", "file_id": "<file_blueridge>",  "mount_path": "/uploads/case_studies/blueridge_health_plan.md" },
      { "type": "file", "file_id": "<file_calder>",     "mount_path": "/uploads/case_studies/calder_manufacturing.md" },
      { "type": "file", "file_id": "<file_northwind>",  "mount_path": "/uploads/case_studies/northwind_logistics.md" },
      { "type": "file", "file_id": "<file_harborview>", "mount_path": "/uploads/case_studies/harborview_retail.md" },
      { "type": "file", "file_id": "<file_aperture>",   "mount_path": "/uploads/case_studies/aperture_payments.md" },
      { "type": "file", "file_id": "<file_summit>",     "mount_path": "/uploads/case_studies/summit_county_gov.md" },
      { "type": "file", "file_id": "<file_product>",    "mount_path": "/uploads/product_one_pager.md" },
      { "type": "file", "file_id": "<file_pricing>",    "mount_path": "/uploads/pricing_rules.md" }
    ]
  }'
```

> The field is just `agent` (passing the ID string locks a snapshot of that Agent's current latest version; to pin an older version pass `{"id": ..., "version": N}` — covered in 03). The response's `agent` field echoes the **full config snapshot** (system and tools included, but not multiagent — the roster does not enter the Session snapshot; member versions resolve at delegation per the table above). Also note: the `file_id` echoed in `resources[]` differs from what you submitted — the platform generates a new session-scoped file id per file at mount time; the original upload id remains valid. The response `id` is shaped like `sesn_<ULID>`; note it as `$SESSION_ID`.

---

## 4. Launch the proposal and observe

Session creation carries no initial input, so the flow is **create the Session first, then send a `message` event** to drive it to work.

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/events" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      { "type": "message", "role": "user",
        "content": [ { "type": "text", "text": "Build a proposal for Meridian Health, a regional healthcare system with ~8500 employees. Estimate 600 seats at heavy usage. Write to /mnt/session/outputs/proposal.md." } ] }
    ]
  }'
```

The prospect profile: **Meridian Health**, a regional healthcare system, 8500 employees, estimated **600 seats**, **heavy** usage.

The whole flow took about 4 minutes field-tested: the coordinator first delegated the researcher (6 web searches), then on the researcher's return delegated the picker (glob + read xN over the case library) and the pricing modeler (read the rules file) in parallel, finally delegated the checker, then read the one-pager and wrote proposal.md (4 drafts iterated field-tested — the checker's suggestions directly drove the rewrites), and registered the artifact via `mark_artifacts`.

### 4.1 Streaming observation (one Session-level stream, split by thread_id)

SSE is a **Session-level single stream** — the coordinator and all sub-agents' outputs converge into the same stream. **There is no thread-level SSE endpoint**: `GET /sessions/{sid}/threads/{tid}/events/stream` field-tested returns `404 {"type":"api_error","message":"not support"}`. For streaming there is only this one Session stream; to watch a single thread, use §4.2's Thread Events polling.

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 300 -N "$BASE/sessions/$SESSION_ID/events/stream" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: text/event-stream"
```

First comes `:connected`, then `event: message` frames (interleaved with `:keepalive`). **Every event carries `thread_id` at the top level** — the splitting key: the coordinator's primary thread has the `thrd_` prefix, and every delegated sub-agent is a `sthr_`-prefixed Session Thread.

The four multi-agent-specific event types (structures per field tests):

- **`thread_created`**: a sub-thread appears. `thread_id` is the new `sthr_...`; `content[0].data` is `{"agent_name": "prospect_researcher", "session_thread_id": "sthr_..."}`.
- **`thread_message_sent`**: a message sent from some thread. The sender's `thread_id` (`thrd_` for the coordinator, `sthr_` for workers), `content[].text` is the message body, `metadata.to_session_thread_id` / `to_agent_name` point at the receiver.
- **`thread_message_received`**: the same message from the peer's viewpoint. `thread_id` is the receiving thread; `metadata.from_session_thread_id` / `from_agent_name` point at the sender (for a message from the coordinator, `from_agent_name` is `"coordinator"`).
- **`thread_status`**: thread state transitions. `content[0].data` is `{"agent_name": ..., "thread_status": "running"|"idle", ...}`, ending with `stop_reason: {"type": "end_turn"}`.

Regular events (`tool_call` / `tool_call_output` / `mcp_call` / `mcp_call_output` / `model_request_start|end` / `reasoning` / `message` / `session_status`) are as in 01/02, only now all carrying `thread_id`. The coordinator's auto-injected orchestration tools look like this in the event stream:

```jsonc
// Coordinator delegation (on the primary thrd_ thread)
{ "type": "tool_call", "thread_id": "thrd_...",
  "content": [ { "type": "data", "data": {
      "name": "create_agent",
      "arguments": { "name": "prospect_researcher", "task": "Research what a regional ..." } } } ] }
// Coordinator polling-wait and query
{ "name": "wait_for_agents", "arguments": {} }
{ "name": "list_agents",     "arguments": {} }
// Worker side (on the sthr_ thread) formally submitting the result
{ "name": "submit_result", "arguments": { "content": "{\"picks\":[...]}" } }
// submit_result's output
{ "output": "{\"status\":\"submitted\"}" }
```

> **The worker's return channel (field-tested)**: a worker's final assistant text is automatically returned to the coordinator as `thread_message_sent`; `submit_result` is a separate explicit submission tool, and the two often arrive one after the other (LLMs double-send for safety). **A sub-agent's system prompt needs no "return via send_to_parent" instruction** — no tool of that name exists, and writing it may only make the model hesitate; just say "return strict JSON".

> If you prefer not to hold a long connection, poll the event history: `GET /sessions/$SESSION_ID/events?order=asc`. Note the **single-page cap of 100 events** (a larger `limit` still returns only 100); page through with the response's `next_page` cursor: `...&page=<next_page>`. One full multi-agent turn produced 168 events field-tested — two pages.

### 4.2 Session Threads API: one row per sub-agent

Structured observation of the multi-agent run does not have to go through the event stream — the four **Session Threads** endpoints give you a thread-level list, detail, events, and archive directly (this API group is not yet in the official public docs; all behaviors below are field-tested):

**List: `GET /sessions/{session_id}/threads`**

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 "$BASE/sessions/$SESSION_ID/threads" \
  -H "Authorization: Bearer $API_KEY"
```

```json
{
  "data": [
    {
      "id": "sthr_01M1EQS476Q26XFQYVXTRHH7NX",
      "type": "session_thread",
      "session_id": "sesn_01M1EQQY3G5P104HX11359J7H5",
      "parent_thread_id": "thrd_01M1EQQYDH4MCA5RFJ38WWQGMP",
      "agent": { "id": "agent_01M1EQPS01DZ755FG98P36KRDE", "version": 1 },
      "status": "running",
      "created_at": "2026-09-01T15:00:39Z",
      "updated_at": "2026-09-01T15:01:00Z",
      "archived_at": null
    }
  ],
  "request_id": "req_..."
}
```

One Thread per delegated sub-agent instance. A few fields deserve calling out:

- `parent_thread_id`: the delegator's thread. Under the coordinator's primary thread it is `thrd_...`; if some worker delegated its own sub-agent, that thread's parent is the former's `sthr_...` (multi-level delegation).
- `agent.version`: **the member version this thread actually runs** — the §3.4 table's "no version means latest-at-delegation" is directly checkable here. If the roster left the version unpinned and the sub-agent was upgraded to v2 mid-way, this field reads v2 in the new Session.
- `status`: `running` / `idle` / `terminated`. Polling this endpoint during a batch run gives you a live "sub-agent workbench".

Query parameters `limit` / `page` behave like other list endpoints; archived Threads are not returned by default.

**Get: `GET /sessions/{session_id}/threads/{thread_id}`** — single-Thread detail, fields as in List (plus a `request_id`). Two boundaries (field-tested): **the coordinator's primary thread (`thrd_` prefix) is not in the threads collection** — GETting with its id also returns `400 invalid_parameter "Invalid request"`; the threads resource only addresses delegated sub-threads, the primary thread being just a `thread_id` value on the event stream. **An archived Thread returns the same 400** (List does not carry it either) — archiving removes it from the addressable space, but the Thread's events remain queryable (below).

**Events: `GET /sessions/{session_id}/threads/{thread_id}/events`** — the single thread's event sequence, i.e., the §4.1 stream sliced by `thread_id`: from `thread_created` (task received) to `thread_status` (idle + stop_reason), with its own model calls and tool calls in between. Field-tested, without `limit` it returns the thread's full events (33 in some runs); with `limit` the response carries a `next_page` cursor. **This is the shortest path to "what did this one sub-agent do"** — no need to filter 168 Session events by thread_id.

**Archive: `POST /sessions/{session_id}/threads/{thread_id}/archive`**

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/threads/sthr_xxx/archive" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

The body can be omitted. Success returns the archived Thread object (`archived_at` filled, `updated_at` refreshed); List no longer returns it afterwards; repeat archiving is idempotent. Use: in long sessions, clear out historical worker threads so the threads list holds only active ones — event data is unaffected.

### 4.3 What each specialist returned

Walking the four sub-threads' `thread_message_sent` via Thread Events (or `submit_result`'s `arguments.content`) yields every specialist's raw JSON:

- Researcher: `priorities` / `pain_points` / `sources` — external intelligence (6 `bailian_web_search` calls; in the event stream they are `mcp_call` / `mcp_call_output`, `server_label` being `WebSearch`).
- Picker: `picks` — `glob` the directory, `read` every case, score and pick two (field-tested: St. Clair Health + Aperture Payments — healthcare-first, fully correct).
- Pricing modeler: `options` — after `read`ing the rules file, computed for 600 seats x heavy 1.30x (field-tested conservative tier $486,720 = 52 x 1.3 x 600 x 12, matching the rules file to the digit).
- Checker: `aligned` / `issues` / `suggestions` — one alignment verdict plus revision suggestions.

The three reports differ sharply — the researcher delivers external intelligence, the picker scores local cases, the pricing modeler does pure rule computation, the checker gives one alignment verdict. **Each sub-agent uses only its own tools in its own thread** — direct evidence of role-scoped authority.

### 4.4 Client side: render one stream into a team workbench

The previous three sections covered the server-side observation surface. To consume this stream on the client, there is one core data structure — **a bucketed dictionary keyed by `thread_id`** — plus four field-tested behaviors; the rendering logic is simpler than you'd think:

1. **Deduplicate by event `id`.** All 168 frames this turn were unique; SSE offers no cursor / resume token, and a reconnected stream may replay old frames — dedupe by `id` (01's conclusion, equally valid in multi-agent).
2. **Assistant text arrives whole; no incremental assembly needed.** Some tutorial ecosystems tell you to "accumulate tokens by `sequence_number` for a live preview" — that mechanism does not appear on this platform: this turn's 17 assistant messages had `sequence_number` **all `null`**, with no multi-frame increments under the same id; every text arrives whole in one frame (`status: "completed"`) — 01's single-agent field-test conclusion holds again in multi-agent. Parse as "if `sequence_number` exists, accumulate in order; otherwise treat it as whole" for maximum robustness. The multi-agent "live feel" actually comes mostly from structural events: `thread_created` (who started), `thread_status` (who finished), `mcp_call` / `tool_call` (who is doing what).
3. **`session_status` is the only session-level event.** This turn's only 2 events without `thread_id` were exactly those (running and idle+stop_reason); treat them as session state during splitting — they belong to no thread.
4. **The primary thread has no `thread_created`.** The `thrd_` thread exists before the stream starts — when first meeting some `thrd_` event, just register it as the coordinator.

Assembled, these give a ~50-line team workbench (the script was replay-verified on field-test logs):

```python
#!/usr/bin/env python3
# watch_team.py — render one Session-level stream into a team workbench
# Usage: curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 300 -N "$BASE/sessions/$SESSION_ID/events/stream" \
#          -H "Authorization: Bearer $API_KEY" -H "Accept: text/event-stream" \
#        | python3 watch_team.py
import json, sys

threads = {}   # thread_id -> {name, status, last}
seen = set()   # event-id dedup (a reconnected stream may replay old frames)

def feed(line):
    d = json.loads(line)
    if d.get("id") in seen:
        return
    seen.add(d.get("id"))
    t, typ = d.get("thread_id"), d.get("type")      # session_status has no thread_id

    if typ == "session_status":                      # session-level event
        s = (d.get("content") or [{}])[0].get("data", {}).get("session_status")
        print(f"=== session {s} ===")
        return
    if typ == "thread_created":                      # sub-thread born, carries agent_name
        name = (d.get("content") or [{}])[0].get("data", {}).get("agent_name")
        threads[t] = {"name": name, "status": "running", "last": ""}
        print(f"[{name}] started")
        return
    if t not in threads:                             # the primary thread has no thread_created
        if not (t and t.startswith("thrd_")):
            return
        threads[t] = {"name": "coordinator", "status": "running", "last": ""}
    if typ == "thread_status":
        s = (d.get("content") or [{}])[0].get("data", {}).get("thread_status")
        threads[t]["status"] = s
        print(f"[{threads[t]['name']}] {s}")
    elif typ in ("tool_call", "mcp_call"):           # the main source of the live feel
        data = (d.get("content") or [{}])[0].get("data", {})
        print(f"[{threads[t]['name']}] {data.get('name', typ)}")
    elif typ == "message" and d.get("role") == "assistant":
        threads[t]["last"] = "".join(c.get("text", "") for c in d.get("content") or [])
        print(f"[{threads[t]['name']}] {threads[t]['last'][:80]!r}")

for ln in sys.stdin:                                 # one line per frame: data:{...}
    ln = ln.rstrip("\n")
    if ln.startswith("data:"):
        feed(ln[5:])
```

Against this turn's stream, its live team timeline looks like this (excerpt):

```
=== session running ===
[coordinator] 'OK, I will coordinate the team through the pipeline to build the sales proposal for Meridian Health.…'
[prospect_researcher] started
[coordinator] create_agent
[prospect_researcher] bailian_web_search        x6
[prospect_researcher] submit_result
[prospect_researcher] idle
[case_study_picker] started
[pricing_modeler] started
[case_study_picker] glob / read
[pricing_modeler] read
[proposal_checker] started
[coordinator] write / write / write / write       <- the checker's suggestions drove 4 rewrites
[coordinator] mark_artifacts
=== session idle ===
```

**Disconnection and the authoritative record**: the stream does not replay — frames produced before the connection was established are never backfilled, not even on reconnect. So the authoritative state is always `GET /sessions/{id}/events` (`order=asc` + `next_page` paging, single-page cap 100; this turn's 168 events take two pages); when only individual threads matter, `GET .../threads/{tid}/events` (§4.2) is the cheaper single-thread alignment.

Finally, choosing the observation surface:

| Want | Use |
|---|---|
| Whole-team live progress (one connection) | Session-level SSE stream + this section's bucketed dictionary |
| A "who's running / who's done" workbench | Poll `GET /sessions/{id}/threads` (status + `agent.version`) |
| Dig into what one sub-agent did | `GET .../threads/{tid}/events` (single-thread, full) |
| Authoritative record / post-hoc attribution | `GET /sessions/{id}/events` paged, full pull |

---

## 5. Read the proposal, plus one real failure post-mortem

Artifact retrieval: find the `tool_call` writing `proposal.md` in the coordinator's primary-thread events (tool `write`, path `/mnt/session/outputs/proposal.md`; `arguments.content` is the full text — this example also registered it via `mark_artifacts`, so a file_id is immediately available), or find the file by name in the Files listing.

> Field-tested reminder: the correct parameter for scope-filtering the Files listing is `GET /files?scope_type=session&scope_id=<sesn_...>` — passing `session_id` is silently ignored and returns the whole workspace's file list (rely on each item's `scope` field to tell ownership apart).

**One field-tested failure must be told here**: the same coordinator configuration ran twice —

- **Run 1**: all three workers were correct (verifiable in the event stream), but in the coordinator-written proposal.md the case names became "Community Health Network" and "Bayshore Medical Group" — neither in the case library — and the pricing table became $39,000/$58,500/$78,000 — **the coordinator hallucinated while summarizing a long context**.
- **Run 2**: same configuration, same input; proposal.md contained the correct St. Clair Health + Aperture Payments.

The only difference between the runs was sampling randomness. Three lessons follow:

1. **Right workers ≠ right team.** After multi-agent splits research/picking/pricing across specialists, the last mile — "summary writing" — remains a high hallucination-risk zone; the coordinator deserves the strongest model, and prompting it to "quote the experts' returned data verbatim; do not rewrite numbers" also helps.
2. **Attribution via the Threads API.** When things go wrong, inspect thread by thread with `GET /threads/{id}/events`: the picker's picks were right, the pricing modeler's options were right, the error was in the coordinator's write arguments — **the blame lands precisely on the coordinator**. When a single agent errs you have only one undifferentiated log; multi-agent leaves the responsibility cross-sections behind.
3. **Evaluation belongs in the pipeline.** The previous recipe's version-rollback methodology applies here too: before launch, run one round with a fixed prospect profile and assert on proposal.md (case names must be in the case-library whitelist; pricing must match the rules-sheet computation), then decide to ship.

---

## 6. Why three (+ one checker) sub-agents instead of one

A single agent with all the tools could also write the proposal, but **role-scoped tooling** brings real gains:

- The pricing modeler has **only the rules file** and no internet channel at all — it cannot pull competitor prices; pricing always derives from internal rules.
- The case-study picker reads 7 files here, hundreds in production — that volume stays in **the sub-agent's context** instead of flooding the coordinator's.
- The coordinator only decides **ordering and handoffs** and does no specialist work itself, keeping its context clean.

The added `proposal_checker` extends the same idea: before writing, it pulls the cases and pricing back into alignment with the prospect's priorities, catching inconsistency before the writing starts — in this example it drove 4 rewrites by the coordinator. The checking runs in its own thread, and both its judgment basis and its suggestions stay reviewable in the event log. The cost is one more worker thread — one more round of delegation and return, one more run of overhead. If some prospect scenarios don't need this self-check, drop it from the roster; the coordinator proceeds straight to writing.

---

## 7. Cleanup (archive)

Uniformly use archive (keeps audit, stops billing). Mind the order: **a running Session cannot be DELETEd** (returns `400 invalid_parameter`) — wait for idle or archive first; Agents support archive only:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/archive" -H "Authorization: Bearer $API_KEY"
# Or delete: curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X DELETE "$BASE/sessions/$SESSION_ID" -H "Authorization: Bearer $API_KEY" (must be idle)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/environments/$ENV_ID/archive"  -H "Authorization: Bearer $API_KEY"
# Archive the coordinator and each sub-agent one by one
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID/archive"      -H "Authorization: Bearer $API_KEY"
```

Archived sub-agents can no longer be referenced into a new coordinator's roster; historical threads of existing Sessions are unaffected (their event data is retained with the Session).
