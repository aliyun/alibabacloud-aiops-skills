# Tutorial 02: Wiring a Working Agent into Your Own Business System

| Item | Value |
| --- | --- |
| **Goal** | Cross from "runs in the CLI" to "callable from a business system": grab remote IDs → verify auth → pick the shape → land the first HTTP call → go to production |
| **Capabilities involved** | Session / Event (SSE) / File mounting / Deployment / stop_reason branch handling |
| **Difficulty** | Intermediate |
| **Prerequisites** | [01-ai-native-quickstart.md](01-ai-native-quickstart.md) or existing Agent/Environment IDs from API, console or CLI; code-only requests may use configurable placeholders |
| **Estimated time** | 30-45 minutes (including the three-shape selection) |
| **Source** | Official API docs + **every endpoint, request body, and event field on this page is evidence-backed by field tests** (including raw SSE output and the full Deployment lifecycle) |

For customer systems, use HTTP API or a verified SDK directly. Do not embed CLI subprocesses in business code or require CLI installation before generating code. Read [CLI/API routing](../workflows/cli-api-routing.md) if provisioning is also requested.

## Why this step is needed

The CLI world and the code world **do not use the same identifiers**:

| | CLI side | Code side |
| --- | --- | --- |
| What you operate on | The logical name in `agents.yaml`, e.g. `agents.web-designer` | The remote ID, e.g. `agent_xxx` / `env_xxx` |
| Who maintains it | The local state file | The Bailian server |

So the first integration task is not writing code — it is **swapping logical names for remote IDs**.
This is where most people get stuck.

## Steps

### 1. Get the remote IDs (three routes, pick one)

**Route A: call the API to list resources (recommended)** — one command accomplishes both
"get the IDs" and "verify auth":

```bash
export DASHSCOPE_API_KEY="sk-xxx"
export BAILIAN_WORKSPACE_ID="llm-xxx"        # the dropdown at the top-right corner of the console
export CMA_BASE="https://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/agents" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq '.data[] | {id, name}'

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/environments" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq '.data[] | {id, name}'
```

Use actual IDs returned for the intended workspace and resource; a matching prefix alone is not validation. **A 200 here means the Key, workspace ID, and
region trio are all correctly paired** — every later call builds on it. If you get
`401 InvalidApiKey`, fix auth before moving on.

**Route B: read the CLI's local state** — `bl managed-agent state list` shows tracked resources and
their remote IDs. For the exact flags (whether `--output json` is supported etc.), defer to
`bl managed-agent state list --help`; don't reconstruct from memory.

**Route C: copy from the console** — copy the ID from the resource detail page at
https://agent.console.aliyun.com/managed-agent. Fits one-off integrations.

> Once you have the IDs, **store them in business config** (a config center / environment
> variables), not scattered in code. Changing an Agent's config is "update + new version number" —
> the ID itself never changes, so this config is stable.

### 2. Optional authorized live smoke test (code-only requests skip this)

**Burn in one iron rule first: sending a message and receiving events are two separate endpoints.**

| What you want | Endpoint | Returns |
| --- | --- | --- |
| Send a message | `POST /sessions/{id}/events` | **Always JSON**, and it echoes back only the event you just submitted |
| Receive the live stream | `GET /sessions/{id}/events/stream` | SSE (`text/event-stream`) |
| Query back / backfill history | `GET /sessions/{id}/events` | A JSON event list, paginated |

Adding `Accept: text/event-stream` to the `POST` does **not** make it streaming (field-tested: the
response header stays `content-type: application/json`) — the most common trap of the integration
stage.

```bash
# ① Create a Session (agent + environment_id required)
SESSION_ID=$(curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"agent":"agent_xxx","environment_id":"env_xxx","title":"Integration smoke test"}' | jq -r '.id')
echo "$SESSION_ID"        # shaped like sesn_01M... (sesn_ + ULID)

# ② Attach the SSE listener (in the background) first, then send — order matters; see below
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 300 -N -s "${CMA_BASE}/sessions/${SESSION_ID}/events/stream" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" &
sleep 2

# ③ Send the message (returns immediately, non-blocking)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions/${SESSION_ID}/events" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","type":"message",
       "content":[{"type":"text","text":"Introduce yourself in one sentence"}]}]}'
```

`curl -N` disables buffering — without it you won't see streaming. The terminal should print
`data:{...}` lines one by one; field-tested verbatim:

```
:connected

id:1
event:message
data:{"type":"session_status","content":[{"type":"data","data":{"session_status":"running"}}]}

id:2
event:message
data:{"type":"message","role":"user","thread_id":"thrd_01M...","content":[{"type":"text","text":"..."}]}

... reasoning / model_request_start / model_request_end / message ...

id:7
event:message
data:{"type":"session_status","content":[{"type":"data","data":{"stop_reason":{"type":"end_turn"},"session_status":"idle"}}]}
```

Three details you must know:

- **The SSE `event:` name is uniformly `message` for every event**; the real kind lives in the JSON
  body's `type` field. Dispatching on the SSE `event:` name routes everything into one branch — you
  must parse the JSON and dispatch on `type`.
- **`stream` does not replay historical events**: connecting pushes only events generated
  afterwards. Field-tested: reconnecting to an already-`idle` session yields just `:connected` and
  nothing more. So attach the listener before sending; after a disconnect-reconnect, backfill the
  gap with `GET /sessions/{id}/events` — reconnecting alone is not enough.
- The SSE line prefix `id:N` is an **integer incrementing from 1**, usable as the ordering
  reference within the current connection.

**Seeing `idle` with `stop_reason.type == end_turn` and the expected output verifies the turn; `requires_action` is still pending** — what remains is
translating it into business code.

### 3. Pick the integration shape

**Answer one question first: before the result is out, is anyone staring at a screen waiting?**
This answer matters more than the shape — it decides whether to keep long-lived connections,
whether to build a task table, and thereby the whole architecture.

| | Scenario 1: strong interaction (use it as a **cloud agent**) | Scenario 2: weak interaction (use it as a **service**) |
| --- | --- | --- |
| Someone waiting online | Yes, and they want to watch the process | No; only the final result matters |
| Listen to SSE? | **Yes**, and manage the connection lifecycle | **No**; just query status back |
| Required infrastructure | SSE proxy, response buffering off, reconnect | Task table + idempotency key + failure alerts |
| Matching shapes | A | B (you trigger) / C (auto-triggered on schedule) |

**Scenario 2 does not mean single-turn**: sessions are stateful server-side and events are
persisted, so you can "send one turn → poll back to `idle` → collect the result → send the next
turn" without ever holding a long connection.

The two coexisting is common (the same Agent can serve both); build the one carrying the main
traffic first. Selection details, event-driven embedding, and other variants are in
[../integration/patterns.md](../integration/patterns.md).

With the macro scenario fixed, look at the traps of each concrete shape:

| Shape | Scenario | Judging signal | Key constraints |
| --- | --- | --- | --- |
| **A synchronous / streaming** | Strong interaction | A conversational UI exists; the user is waiting | Long tasks hit **your own** gateway/proxy read timeout (Nginx `proxy_read_timeout` defaults to 60s), while the platform-side SSE can run for minutes; the key never ships to the frontend |
| **B async tasks** | Weak interaction | Tasks run long (minutes and up); the user need not wait online | You must build a task table mapping `business ticket no. ↔ session_id` |
| **C scheduled unattended** | Weak interaction | Nobody triggers it; runs on a cycle | Use a Deployment, not a session; artifact write-back is your own design |

#### Shape A: synchronous / streaming conversation

Chain: `frontend ⇄ your business service (proxying) ⇄ CMA event stream`

```
① User speaks → ② Business service looks up / creates session_id → ③ GET events/stream attaches the SSE listener
→ ④ POST events submits the utterance → ⑤ As messages arrive, pass the text through to the frontend
→ ⑥ session_status(idle) ends the turn
```

Key points:
- **Listen before sending**: `stream` does not replay history; POST-then-connect loses the earlier events.
- **Session reuse**: one user's consecutive conversation reuses the same `session_id`; context carries forward automatically — no need to replay history yourself.
- **Gateway config**: Nginx needs `proxy_buffering off;`, or SSE gets buffered into one lump response.
- **The frontend holds no key**: the business service acts as the proxy layer, passing text through only, never credentials.
- To keep it simple, skip streaming: POST the message, then poll `GET /sessions/{id}/events` until `session_status: idle` appears — fits internal short-task interfaces. Note the POST's return contains **only the echo of the message you just submitted**, not the model output.

#### Shape B: async tasks (submit-then-query)

Chain: `submit and get a ticket no. immediately → background consumes events → write back on completion → notify`

```
① Business submits → create Session + POST events (returns immediately, async by nature)
→ ② Persist {business ticket no., session_id, status: running}
→ ③ Background worker polls GET /sessions/{id}/events for increments, or holds a long-lived SSE
→ ④ On session_status(idle) → check stop_reason → write back the result + archive the session
```

Key points:
- **`session_id` must be persisted**: it is the only handle for troubleshooting and replay; lose it and nothing is traceable.
- **Poll for increments** with `GET /sessions/{id}/events` pagination: the response's top level is `data` / `next_page` / `request_id`; pass the previous page's `next_page` (**an opaque cursor string, not a page number**) verbatim as the next request's `page` parameter. Track what you have processed yourself; don't replay everything each time.
- **You can also read the session object to detect completion**: `GET /sessions/{id}` returns `status` and `stop_reason` at the root — polling this one endpoint suffices to tell the turn ended, no need to pull the full event list first.
- **Archive when the task ends** (`POST /sessions/{id}/archive`; field-tested: returns 200 and flips `status` to `terminated`) — runtime billing accrues only while running; after archiving, `GET /sessions/{id}/events` still returns 200 and event history stays queryable.
- **Timeout fallback**: set a business-side max wait; on timeout mark it failed and alert — never wait forever.

#### Shape C: scheduled unattended

Chain: `Deployment (schedule + initial_events) → the server triggers on time → the Agent produces → write back`

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/deployments" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily order summary",
    "agent": {"id": "agent_xxx", "version": 12},
    "environment_id": "env_xxx",
    "schedule": {"type": "cron", "expression": "0 9 * * 1-5", "timezone": "Asia/Shanghai"},
    "initial_events": [{"type":"message","role":"user",
      "content":[{"type":"text","text":"Summarize yesterday's order data"}]}]
  }'
```

Key points (all endpoints below field-tested returning 200):
- **The only required fields are `name` / `agent` / `initial_events`**; `environment_id` and `schedule` are both optional (no `schedule` means manual triggering only). Inside `agent`, `id` is required and `version` optional.
- **Pin `agent.version`**: the official schema explicitly says "omitted means the latest version" — the behavior drifts the moment the Agent changes. Always pin in production.
- **The cron is executed by the Bailian server**: if the business side already runs a cron for the same thing, confirm no double-triggering before going live.
- **How artifacts return to the business system is your own design**: have the Agent proactively call your write-back API (credentials in a Vault — Deployments do not support session-level `environment_variables`; on the scheduled path `vault_ids` is the only injection route, while app-created sessions should prefer `environment_variables` for non-sensitive config; the two-path layering is in [../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md)), or have the business side periodically pull run records via `GET /deployments/{id}/runs` and collect artifacts from there.
- During integration testing, trigger manually with `POST /deployments/{id}/run` instead of waiting for the schedule (it returns a `deployment_run` object carrying `status` and `trigger_source: manual`); it genuinely starts a Session and genuinely bills.
- **Deployments cannot be deleted** (field-tested: `DELETE` returns `405 Method Not Allowed`). Stopping one takes exactly two routes: `POST /deployments/{id}/pause` to pause (`status` becomes `paused`), or archive. Don't count on delete-and-recreate.

### 4. Switch to code

Write code only after the chain is verified; translate from the curl calls that already work,
field by field:

- Full Python implementation (all three shapes) → [../integration/code-python.md](../integration/code-python.md)
- Full Java implementation (all three shapes) → [../integration/code-java.md](../integration/code-java.md)
- Other languages: wrap the endpoints and request bodies per [../integration/api-endpoints.md](../integration/api-endpoints.md) yourself; the event-parsing logic carries over as-is

### 5. Event parsing: the three branches you must handle

Whatever the shape or language, the event-loop skeleton is the same. Note **the dispatch key is
the JSON body's `type` field**, not the SSE `event:` name (which is always `message`):

```
switch (event.type):
  message                                    → accumulate body text in arrival order
  reasoning                                  → reasoning trace; render if you show it
  tool_call / tool_call_output               → render if you show the execution trace, else log only
  function_call / function_call_output       → same as above
  mcp_call / mcp_call_output                 → same as above
  thread_* (5 kinds)                         → appears only in multi-agent formations; split by thread (see below)
  error                                      → log the error (with code / message)
  session_status                             → branch on stop_reason (see below)
  default                                    → log and ignore; never throw and break the stream
```

> **Do not sort by `sequence_number`**: the field exists but is field-tested to be `null` on every
> event. Order by the SSE `id:` incrementing integer (valid only within the current connection) or
> the event's `created_at`.

**The server pushes at least 23 event types** (22 in the SDK enum + the approval event
`tool_approval_request`; the full enumeration is in the Event section of
[../product/concepts.md](../product/concepts.md)), so the `default` branch is not optional —
unknown types must be safely skipped, never thrown to break the stream.

**Sessions have three statuses**: `idle` / `running` / `terminated` (per the official docs; the SDK
enum additionally has `rescheduling`, never observed in a real session — don't write a branch for
it). Only `idle` and `terminated` count as the end of a turn.

**In the event stream, `session_status` and `stop_reason` hide in the event's `content[*].data`**,
not at the event root. Iterate each block of `content` and read the two keys from its `data` object:

```json
{"type": "session_status",
 "content": [{"type": "data",
              "data": {"session_status": "idle", "stop_reason": {"type": "end_turn"}}}]}
```

Note the `session_status` event **carries no `thread_id`**, and the opening one contains only
`{"session_status":"running"}` with no `stop_reason` — confirm the `session_status` value before
judging completion.

**There is another route**: `GET /sessions/{id}` returns `status` (session status) and `stop_reason`
(why the current turn ended; `null` while running) directly at the **root**. Async polling via this
endpoint is the cheapest:

```json
{"id": "sesn_01M...", "status": "idle", "stop_reason": {"type": "end_turn"},
 "stats": {"active_seconds": 5.3, "duration_seconds": 22.5}, "usage": {"input_tokens": 15584}}
```

Note `stop_reason` **is an object, not a string** — what you read is `stop_reason.type`. All three
values **must have branches**:

| stop_reason.type | Meaning | Business action |
| --- | --- | --- |
| `end_turn` | The model ended normally | Collect the result; mark success |
| `requires_action` | Client intervention needed; carries `pending_call_ids` + `pending_batch_id` | **Must be handled**: usually send back a `tool_approval_response` to approve the tool call ([06-tool-approval.md](06-tool-approval.md)), not re-create the session |
| `retries_exhausted` | Retries exhausted | Mark failed + alert; never treat as success |

Treating `idle` alone as success is the most easily planted hidden failure of the integration stage.

**The client can send more than `message`** — 6 kinds in total: `message` / `interrupt` (cancel the
current turn) / `tool_approval_response` (tool approval; no usable SDK constructor, hand-roll it) /
`tool_call_output` / `function_call_output` (feed tool results back) / `define_outcome` (declare the
acceptance goal). Handling `requires_action` relies on the `tool_approval_response` among them.

**If the Agent has a multi-agent formation**, one stream mixes output from every member.
Server-pushed events carry **`thread_id`** (shaped like `thrd_01M...`); you must group by it before
rendering — `events.list()` has no thread-dimension filter, so the splitting is client-side only.
Without splitting, member texts interleave on the UI and failures can't be attributed.

> **Don't mix up the two field names**: on server events it is `thread_id`; when the client sends an
> event targeting a thread, the field is `session_thread_id` (the SDK's
> `user_message(..., session_thread_id=...)` likewise). Different direction, different name. Also,
> single-agent sessions' events carry `thread_id` too (just one thread), but session-level events
> like `session_status` do not. The full recipe is in [07-multiagent-coordinator.md](07-multiagent-coordinator.md) step 5.

### 6. Pre-production self-check

- [ ] The key is read only from environment variables / a secret service — never hardcoded, never shipped to the frontend, never written into `agents.yaml`
- [ ] All three `stop_reason` branches are implemented (especially `requires_action`)
- [ ] Unknown event types cannot crash the flow, and dispatch keys on the JSON `type`, not the SSE `event:` name
- [ ] In SSE scenarios: the listener attaches before sending, and reconnects backfill the gap via `GET /events`
- [ ] The shape is right; long tasks won't hit gateway timeouts
- [ ] Both `session_id` and the response header `x-request-id` are logged
- [ ] One Session per user / per task; no cross-user reuse
- [ ] Sessions are archived promptly on completion, with a per-session turn cap (against runaway loops burning quota)
- [ ] Scheduled / event-triggered scenarios have a business idempotency key

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| `401` + `{"code":"InvalidApiKey","message":"Invalid API-key provided."}` | Key invalid, or the Key does not belong to this workspace | One key accesses only its own workspace; check that `BAILIAN_WORKSPACE_ID` is paired correctly |
| `404` though the path looks right | The base URL is missing `/api/v1/agentstudio`, or the region is something other than `cn-beijing` | Only `cn-beijing` is currently supported; field-tested, both cases return 404 with an empty body |
| POSTing a message returns only your own sentence, no model reply | Treating `POST /events` as a synchronous Q&A endpoint | It echoes only the submitted event. Model output comes via `GET /events/stream` (live) or `GET /events` (query back) |
| Added `Accept: text/event-stream` yet still one lump of JSON | `POST /events` does not support streaming; the response header is always `application/json` | Switch to `GET /sessions/{id}/events/stream` |
| SSE connects, shows only `:connected`, then nothing | The stream does not replay history; the session is already `idle` with nothing new to push | Attach the listener before sending; backfill history via `GET /sessions/{id}/events` |
| No streaming over SSE; everything dumps at the end | curl lacks `-N`, or the gateway buffers responses | Add `-N`; set `proxy_buffering off` on Nginx |
| Dispatching on the SSE `event:` name sends every event into one branch | Every event's `event:` name is `message` | Parse the `data:` JSON and dispatch on its `type` field |
| Sorting by `sequence_number` scrambles everything | The field is field-tested to be always `null` | Use the SSE `id:` or the event's `created_at` |
| The Agent says it cannot find the mounted file | The prompt wrote the `mount_path` value as-is | `mount_path` must start with `/uploads/`; the real in-container path = `/mnt/session` + the `mount_path` value — write the full real path in the prompt |
| A freshly uploaded file fails to mount | The security scan has not finished | Wait until the status goes from `checking` to `available` before mounting |
| Sending to a session returns `400 invalid_parameter: Session is archived` | The session was archived into the `terminated` terminal state | Terminal states are unrecoverable; create a new session to continue |
| A scheduled task's behavior suddenly changed | The Deployment didn't pin `agent.version`, and the Agent was modified | Pin the version number |
| Trying to delete a Deployment but `DELETE` returns 405 | The resource does not support deletion | Pause with `POST /deployments/{id}/pause` or archive it |

## Going further

- More integration shapes: event-driven embedding, multi-tenant isolation → [../integration/patterns.md](../integration/patterns.md)
- Full endpoint table and request-body fields → [../integration/api-endpoints.md](../integration/api-endpoints.md)
- Concept background on the event model and state machine → [../product/concepts.md](../product/concepts.md)
- Resources not provisioned yet → [../workflows/provision.md](../workflows/provision.md)
