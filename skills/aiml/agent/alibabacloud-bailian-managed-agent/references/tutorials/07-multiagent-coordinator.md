# Tutorial 07: Make Multiple Agents Collaborate via a Coordinator Fleet

| Item | Value |
| --- | --- |
| **Goal** | Configure a coordinator fleet (coordinator + member Agents), run one collaborative task end to end, and tell "which member is doing what" in the event stream by thread |
| **Capabilities involved** | `multiagent.coordinator` / MultiAgent Roster / `thread_id` (event thread field) / the five `thread_*` event types / `session_thread_id` (client-side targeted send) |
| **Difficulty** | Expert |
| **Prerequisites** | [02-integrate-to-your-system.md](02-integrate-to-your-system.md) done (able to send and receive events, able to parse `session_status`); at least one single-agent Agent already working |
| **Estimated time** | 30-40 minutes |
| **Source** | Official API docs (the `multiagent` field) + a real fleet E2E run (full analysis of a 59-frame event stream) + SDK source (`MultiAgentConfig` / `SessionThread`) |

> **Scope note**: this tutorial covers **how to configure, how to read the event stream, and how to target a specific member**.
> The following cannot be read from either official docs or the SDK, are **out of scope here — verify before answering customer questions**:
> the rules by which the coordinator picks a member, whether members run in parallel or serially,
> whether members share one Environment sandbox, whether members inherit the coordinator's Vault and mounted files,
> the billing basis of fleet tasks, and the full enum of `thread_status` values (field-tested observations: `running` / `idle`).
>
> **Direction convention (the single easiest thing to get wrong)**: the thread field on **server events** is called `thread_id`
> (main thread `thrd_` prefix, member sub-threads `sthr_` prefix); the top-level field used when the **client sends** events (targeted approval / interrupt)
> is called `session_thread_id`. The two names refer to the same thing, in opposite directions.

## Scenario

A single Agent doing everything gets an ever-longer, self-interfering prompt — stuff "write code" and "review code" into the same system prompt and it does neither well. The value of a fleet is **each member doing exactly one thing, with its own prompt and toolset**.

The configuration itself is simple (one `multiagent` field); the real difficulty is on the **integration side**: once the fleet runs, every member's output is mixed into **the same event stream**. Without splitting by thread your UI is porridge, and when something breaks you cannot tell which member failed.

## Final artifacts

One working coordinator Agent + consuming code that splits the event stream by `thread_id` into one transcript per member.

## Steps

### 1. Get every member running standalone first (not skippable)

**Debugging a fleet costs multiples of a single Agent** — one run has several threads interleaving output, and when one member's prompt is badly written, you first suspect the orchestration.

So first verify each member standalone as an ordinary Agent:

```bash
bl managed-agent session run --agent <member-Agent> --prompt "<a task within that member's responsibility>" --output json
```

**How to verify**: every member, run standalone, produces results matching its responsibility — only then proceed.

### 2. Note down member IDs and versions

```bash
export CMA_BASE="https://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/agents?limit=50" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq '.data[] | {id, name, version}'
```

In roster entries, omitting `version` takes the latest — meaning **a single edit to a member Agent by anyone changes fleet behavior**. Pin versions in production, for the same reason as scheduled tasks (see [04-scheduled-deployment.md](04-scheduled-deployment.md) step 2).

### 3. Create the coordinator

**The coordinator is not a special Agent type.** It is an ordinary Agent with one extra `multiagent` field — so it still needs its own `model` and `system_prompt`:

```bash
COORD_ID=$(curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/agents" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dev coordinator",
    "model": {"id": "qwen3.8-max"},
    "system": "You decompose requirements and dispatch them to members: implementation work goes to the coding member, quality control to the review member. Summarize member results into the final reply.",
    "multiagent": {
      "type": "coordinator",
      "agents": [
        {"type": "self"},
        {"type": "agent", "id": "agent_coder", "version": 3},
        {"type": "agent", "id": "agent_reviewer", "version": 2}
      ]
    }
  }' | jq -r '.id')
```

Python SDK equivalent:

```python
coordinator = client.agents.create(
    name="Dev coordinator",
    model="qwen3.8-max",
    system_prompt="You decompose requirements and dispatch them to members: ...",
    multiagent={
        "type": "coordinator",
        "agents": [
            {"type": "self"},
            {"type": "agent", "id": "agent_coder", "version": 3},
            {"type": "agent", "id": "agent_reviewer", "version": 2},
        ],
    },
)
```

Field essentials (SDK field tests; the table is exhaustive):

| Field | Notes |
| --- | --- |
| `multiagent.type` | Currently only `coordinator` (coordinator topology) |
| `multiagent.agents` | The fleet roster, **1-20 entries**; passing an empty array `[]` clears the fleet and reverts to single-agent |
| Entry `type: "agent"` | References another Agent; `id` required, `version` optional (omitted = latest) |
| Entry `type: "self"` | The coordinator itself also participates as an executor; **at most one** |

**Dispatch rules can only live in the coordinator's system prompt.** The `multiagent` field has only the `type` and `agents` keys, and roster entries only `type` / `id` / `version` — there is no "routing rule" or "trigger condition" config item anywhere. To make dispatch more accurate, edit the coordinator's prompt; do not hunt for fields that do not exist.

**Expected result**: an Agent object with `multiagent` comes back.
**How to verify**: `curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/agents/${COORD_ID}" -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq '.multiagent'`
— confirm the roster entry count matches expectations.

### 4. Run once, print the raw event stream first

A fleet adds 5 event types. **On the first run, print before writing parsing logic**:

```python
with client.sessions.events.stream(session_id, timeout=900.0) as stream:
    for ev in stream:
        print(ev.type, "|thread=", getattr(ev, "thread_id", None),
              "|data=", [getattr(b, "data", None) for b in (ev.content or [])])
```

Note it reads `thread_id` — **the top-level thread field on server events**. The coordinator dispatches via platform-injected orchestration tools
(`create_agent` / `list_agents` / `wait_for_agents` on the coordinator side, `submit_result` on the member side, appearing as ordinary `tool_call`s in the corresponding thread's stream). **These tools need no declaration in `tools`**.

| Event | Meaning | Observed |
| --- | --- | --- |
| `thread_created` | The coordinator dispatched work and created a sub-thread | ✅ |
| `thread_status` | Sub-thread status change | ✅ (running / idle observed) |
| `thread_message_sent` | The coordinator sends a message to a member | ✅ |
| `thread_message_received` | A member returns results to the coordinator | ✅ |
| `thread_context_compacted` | The sub-thread's context got compacted (appears on long tasks) | Not triggered on short tasks |

**The real structure of thread_* events (field-tested samples)** — metadata sits in `content[*].data`, and the nested key inside data happens to be named `session_thread_id` (easy to confuse with the top-level field — keep them distinct):

```json
{"type": "thread_created", "thread_id": "sthr_01M1G6Z2…",
 "content": [{"type": "data",
              "data": {"agent_name": "verify-t01-web-designer",
                       "session_thread_id": "sthr_01M1G6Z2…"}}]}
```

- `thread_created` data: `agent_name` + `session_thread_id` (**no thread title, no parent_thread_id**)
- `thread_status` data: `agent_name` + `thread_status` + `session_thread_id`,
  plus `stop_reason: {"type": "end_turn"}` when idle
- `thread_message_sent`: the top-level `thread_id` is the **sending** thread; the receiver is in the event's `metadata`
  (`to_session_thread_id` / `to_agent_name`)
- `thread_message_received`: the top-level `thread_id` is the **receiving** thread; the source is in `metadata`
  (`from_session_thread_id` / `from_agent_name`). Note: on the member→coordinator direction the event content is a
  **JSON-wrapped string** (carrying the member's status/agent/last_result); parsing it as plain text double-displays member output

The server-side thread object fields (per the SDK's `SessionThread` definition, consistent with it):
`id` / `session_id` / `parent_thread_id` / `title` / `status` / `created_at` / `updated_at`.
The event stream never shows `parent_thread_id` / `title`, but **the thread objects themselves are directly queryable** —
there is a set of Session Threads endpoints absent from the official public docs (REST field-tested working):

| Endpoint | Use |
| --- | --- |
| `GET /sessions/{sid}/threads` | Lists the delegated sub-threads, one row per member (with `status`, `agent.id`/`version`, `parent_thread_id`) — the cheapest way to build a "who's running / who's done" dashboard |
| `GET /sessions/{sid}/threads/{tid}` | Single-thread detail (one extra `request_id`) |
| `GET /sessions/{sid}/threads/{tid}/events` | The single thread's event sequence — **the shortest path to "what did this one member do"**, no filtering through hundreds of Session events |
| `POST /sessions/{sid}/threads/{tid}/archive` | Archives the thread |

Three boundaries (field-tested): **the coordinator's main thread (`thrd_` prefix) is not in the threads collection** — GET with its id returns
`400 invalid_parameter`; threads addresses only delegated sub-threads. **Archived threads also return 400** (absent from List too),
though their events remain queryable. **There is no thread-level SSE** (`.../threads/{tid}/events/stream` returns `404 not support`) —
the only real-time stream is the Session one, so real-time splitting still has to happen client-side by `thread_id` as below.

**Prefix mnemonic**: main-thread (coordinator) events have `thread_id` with the `thrd_` prefix; member sub-threads use `sthr_`.

### 5. Split the stream by thread_id (the core of fleet integration)

**Almost every event carries a top-level `thread_id`** (main thread `thrd_` prefix, member sub-threads `sthr_`;
field-tested: 57 of 59 frames carried it — the only two without were `session_status` events). If you see `session_thread_id` elsewhere —
that is the **client-sent** direction's field (see step 6); it does not exist at the top level of server events.

For history queries, the official spec declares only `types` and the time range (`created_at[gt]/[gte]/[lt]/[lte]`) as filters on
`GET /sessions/{id}/events`; field-tested, appending the **undocumented** `thread_id` query parameter also filters by thread
(`?thread_id=sthr_xxx` returns exactly that thread's events; works with curl, not exposed in the SDK). Real-time splitting therefore happens client-side:

```python
from collections import defaultdict

def run_coordinator(session_id, timeout=900.0):
    """Split the fleet session's event stream into one transcript per thread."""
    transcripts = defaultdict(list)      # thread_key -> [text fragments]
    stop_reason = None

    with client.sessions.events.stream(session_id, timeout=timeout) as stream:
        for ev in stream:
            # The thread field on server events is thread_id; a few events like session_status lack it — bucket as "main"
            key = getattr(ev, "thread_id", None) or "main"

            if ev.type == "thread_created":
                transcripts[key].append("[new thread]")
            elif ev.type in ("message", "reasoning"):
                for block in ev.content or []:
                    if getattr(block, "text", None):
                        transcripts[key].append(block.text)
            elif ev.type == "session_status":
                stop_reason = (ev.stop_reason or {}).get("type")   # the SDK already extracts content[*].data for you
                if stop_reason:
                    break

    return transcripts, stop_reason
```

Two field-tested reminders: do not also collect `thread_message_received` as text — its content is a JSON-wrapped string,
and collecting it double-displays member output in the main thread (the member's own `message` events are already in its sub-thread);
and do not key the split on `session_thread_id` (that field does not exist at the event top level — everything collapses into the `"main"` porridge;
field-tested: copying the wrong field name verbatim sent all 59 frames into one key, exactly the scene of the three traps below).

**Without splitting you hit three traps**:
- Multiple members' text interleaves on the UI and reads like gibberish
- On errors you cannot tell which member failed
- A member's intermediate conclusion gets shown to the user as the final answer

**The final answer lives on the main thread** (`thrd_` prefix). Member output is process; only what the coordinator summarizes is the result —
field-tested: the coordinator's final `message` event lands on the main thread. In the UI, collapse member threads into "execution details"
and show only the main thread by default.

**How to verify**: print `transcripts.keys()` — the thread count matches the roster members actually dispatched
(field-tested: main thread + sub-threads of 2 dispatched members + "main" holding the session_status events).

### 6. Target a specific member

**Client-sent** events can carry a top-level `session_thread_id` (value = the target sub-thread's `thread_id`,
the one with the `sthr_` prefix), selecting which thread they act on. **Member interrupts must target the intended thread**. Main-Agent tool approval is separate; current official docs do not support sub-agent tool approvals:

```python
from dashscope.agentstudio import user_interrupt

# Interrupt only one member, not the whole session (field-tested: the sub-thread stops, the coordinator gets notified, the main thread wraps up)
client.sessions.events.send(session_id, [
    user_interrupt(session_thread_id=thread_id),
])
```

**Approval scope correction (2026-09-18):** the [official tool guide](https://docs.agent.bailian.aliyun.com/zh/managed-agents/build-agent/tools.md) explicitly limits approvals to the main Agent. Do not infer member approval support from the general `session_thread_id` targeting field. Route sensitive work through a main-Agent approval or an application-side control. Client-sent targeting uses `session_thread_id`; server events use `thread_id`.

### 7. Editing the fleet and reverting to single-agent

- Add/remove members → `POST /agents/{id}` updating `multiagent.agents`, **must carry the existing `name` and current `version` as the optimistic lock**
  (field-tested: no version → 400 `version cannot be empty`; wrong version → 409 `version conflict, re-fetch and update`;
  only the right one takes effect)
- Revert to single-agent → pass `"agents": []` (an empty array clears the roster; field-tested readback `multiagent: null`) — no need to delete and recreate the Agent
- **An update without the `multiagent` field does not clear the fleet** (field-tested: the roster stays as-is; the official update spec says
  "omitted means cleared" — the opposite of the field test; do not trust that line)
- After changes, **re-pin member versions** — it is easy to miss `version` on newly added members

### 8. Go-live self-check

- [ ] Every member verified standalone
- [ ] Every `type: "agent"` roster entry has a pinned `version`
- [ ] Event consumption splits by `thread_id` (server events), and the UI distinguishes the main thread (`thrd_`) from member threads (`sthr_`)
- [ ] Sensitive member operations have application-side controls; current tool approvals only cover the main Agent
- [ ] Timeouts raised (a fleet is many round trips, far slower than a single Agent — field-tested: a small two-member task ~48 seconds vs. seconds for single)
- [ ] The coordinator's system prompt states the dispatch rules explicitly (the only place dispatch is controllable)


## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| Cannot find an API to "create a coordinator-type Agent" | No such type exists | An ordinary Agent plus the `multiagent` field; a top-level `type` at creation is silently ignored (the echo is always `"agent"`) |
| Text interleaves into gibberish on the UI | No splitting by `thread_id` (or `session_thread_id` misused — that field is absent at the event top level, everything collapses into one key) | Group per step 5; collapse member threads in the display |
| A member's intermediate conclusion shown as the final answer | Main thread not distinguished | Take the final answer from the main thread (`thrd_` prefix); member output is execution detail only |
| Fleet behavior changed inexplicably | Someone edited a member Agent; the roster had no pinned version | Add `version` to roster entries |
| Dispatch inaccurate, always the same member | Looking for routing config in `multiagent` | No such field; edit the coordinator's system prompt |
| Update fails with 409 version conflict | Optimistic lock: `version` is not the latest | GET the current version again, then update |
| No reaction after approving | Wrong targeting field or protocol (see tutorial 06: needs `tool_approval_response` + `batch_id`) | Target with `session_thread_id`; hand-build the protocol per tutorial 06 |
| Session times out | Fleet round trips are many; far slower than single-agent | Raise the stream timeout; move long tasks to the async shape (tutorial 02, Shape B) |
| Want to query "which threads this session has" | **No thread query API** (the managed-agents API has no thread endpoints) | Aggregate from the event stream's `thread_id`; for history, the undocumented `GET /sessions/{id}/events?thread_id=` works (field-tested) |
| Customer asks whether members run in parallel, and how billing works | **Not public** | State honestly that product-team confirmation is needed; do not estimate |

## Going further

- Fleet fields and object semantics → the MultiAgent section of [../product/concepts.md](../product/concepts.md)
- Event-loop skeleton and the three branches → [02-integrate-to-your-system.md](02-integrate-to-your-system.md) step 5
- The full tool-approval round trip → [06-tool-approval.md](06-tool-approval.md)
- Full request-body fields → [../integration/api-endpoints.md](../integration/api-endpoints.md)
- Why the whitepaper still marks this "coming soon" → [../product/faq.md](../product/faq.md) (the official docs are already live; the whitepaper is an old snapshot)
