# Integration Quick Reference: from official docs to your first running code

Goal: wire Bailian Managed Agents into the user's own business system.

> **Fact sources for the interfaces**: the official live API docs (verified) + actually executed calls.
> The full endpoint table and request-body shapes live in [api-endpoints.md](api-endpoints.md); this page covers **how to start, how to parse events, and what production demands**.
> When a field is in doubt, pull the official doc page to verify — **never assemble URLs and parameters from memory**.

## Official documentation entry points

| Content | Entry point |
| --- | --- |
| Product docs (overview / quick start / capabilities) | https://docs.agent.bailian.aliyun.com/zh/managed-agents |
| API overview and auth | https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/introduction |
| **Docs index (for agents)** | https://docs.agent.bailian.aliyun.com/llms.txt (full version: `llms-full.txt`) |
| Session event stream (SSE) and event types | https://docs.agent.bailian.aliyun.com/zh/managed-agents/sessions/event-stream |
| Billing description | https://docs.agent.bailian.aliyun.com/zh/managed-agents/pricing/billing |
| Console | https://agent.console.aliyun.com/managed-agent |
| Error codes | check skill `bailian-docs-llm-wiki` first; fall back to the official docs if not covered |

**The recommended posture when writing code**: appending `.md` to any doc URL yields the raw markdown
(e.g. `.../zh/api/managed-agents/session/create.md`); every API also has a matching OpenAPI description file
`https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/openapi/openapi-<resource>-<action>.json`
(e.g. `openapi-session-create.json`, `openapi-event-stream.json`, `openapi-event-send.json`;
**note the prefix `/zh/api/managed-agents/openapi/`** — field-test verified). Handing `llms.txt` to a coding agent and letting it pull pages on demand
is more accurate than humans flipping through docs assembling parameters. The OpenAPI JSONs expose the REST layer's required fields and value constraints — the most precise source for pure-REST integration.

## Three things you must obtain first

| Item | How to get it |
| --- | --- |
| API Key | Create in the Bailian console; in code read it from the environment variable `DASHSCOPE_API_KEY` |
| Workspace ID | The dropdown in the top-right corner of the Bailian console |
| Region | Currently only `cn-beijing` |

The base URL assembles from these two: `https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio`

## SDK

| Language | Install | Minimum version |
| --- | --- | --- |
| Python | `pip install dashscope` | v1.26.2 or later (the examples in this library are based on field-tested 1.27.3) |
| Java | Import the dashscope SDK per the official docs | v2.22.24 or later |

If an older version is installed, re-run the install command to upgrade — otherwise the Managed Agents module is missing. The REST API can be called directly without the SDK.

The Python module entry point (**field-test verified** — it is not `from dashscope import agentstudio`):

```python
from dashscope.agentstudio import Client, user_message

# Initialize once per run using ../workflows/user-agent.md.
import os
import httpx

skill_ua = os.environ["BAILIAN_MANAGED_AGENT_SKILL_UA"]
def set_skill_user_agent(request):
    request.headers["User-Agent"] = skill_ua

http_client = httpx.Client(event_hooks={"request": [set_skill_user_agent]})
client = Client(
    http_client=http_client,
    api_key=os.environ["DASHSCOPE_API_KEY"],
    workspace=os.environ["BAILIAN_WORKSPACE_ID"],   # the parameter is named workspace, not workspace_id
    region="cn-beijing",
)
```

> **SDK enum-lag reminder**: dashscope 1.27.3's event enum lacks `tool_approval_request` / `tool_approval_response`
> (approval request/response); approval scenarios need hand-assembled events (see [../tutorials/06-tool-approval.md](../tutorials/06-tool-approval.md)) —
> relying purely on "ignore unknown types" as the safety net misses approval requests and the session silently deadlocks.

## The minimal integration loop (three steps)

```
(1) Upload a file (optional) → (2) Create a Session (bind Agent + Environment, attach files, attach Vault)
→ (3) Send a message + subscribe to the SSE event stream until session_status turns idle
```

```python
# (1) Upload and mount (optional): mount_path must start with /uploads/
#     Fill /uploads/workspace/data.csv → the agent actually sees /mnt/session/uploads/workspace/data.csv
#     Mapping: real path = /mnt/session + mount_path
file = client.files.upload("sales_2025.txt")     # must wait for status to become available before mounting
                                                 # note: file types are whitelisted; .csv is rejected in field testing ("file type not allowed")

# (2) Create the session: locks a snapshot of the agent's current latest version
session = client.sessions.create(
    agent="agent_xxx",
    environment_id="env_xxx",
    title="Q3 sales analysis",
    resources=[{"type": "file", "file_id": file.id, "mount_path": "/uploads/workspace/data.txt"}],
    environment_variables={"API_BASE_URL": "https://new.example.com", "LOG_LEVEL": "info"},
                                                 # plaintext-injected sandbox env vars (the agent reads real values from os.environ);
                                                 # echoed verbatim in the create response — put only non-sensitive config here
    vault_ids=["vlt_xxx"],                    # high-sensitivity secrets go into the Vault (sandbox sees only placeholders; the egress gateway substitutes),
                                              # for the two-path selection see "The two credential-injection paths" in api-endpoints.md
    metadata={"biz_ticket_id": "1234"},       # business-side correlation key; does not affect model behavior
)

# (3) Send the message and consume the event stream (send-then-stream may miss the first few frames; ignorable for long tasks —
#     for the complete stream open the stream first, then send — SSE has no history replay)
client.sessions.events.send(session.id, [
    user_message("Analyze the Q3 sales trends in /mnt/session/uploads/workspace/data.txt")
])

with client.sessions.events.stream(session.id, timeout=600.0) as stream:
    for ev in stream:
        if ev.type == "message":
            for block in ev.content or []:
                if getattr(block, "type", None) == "text":
                    print(block.text, end="", flush=True)
        elif ev.type == "session_status":
            if ev.session_status in ("idle", "terminated"):
                reason = (ev.stop_reason or {}).get("type")   # stop_reason is a dict
                break
        # handle other event types as needed; unknown types must be safely ignored (the SDK enum has 22; the server also pushes the out-of-enum tool_approval_request)
```

Full implementations (event dispatch, approvals, async, scheduling) → [code-python.md](code-python.md) / [code-java.md](code-java.md).
The pure-REST curl request bodies are in [api-endpoints.md](api-endpoints.md).

## The event contract (required reading for parsing the event stream)

Events and messages share the same structure; the `type` field distinguishes kinds. **The server pushes at least 23 event types** (the SDK enum's 22 + the out-of-enum
`tool_approval_request`); the business side handles only the kinds it cares about and must safely ignore the rest (otherwise newly added types will crash the flow):

| Group | type | How the business side uses it |
| --- | --- | --- |
| Body | `message` | Concatenate and render in event **arrival order** (`sequence_number` is observed to be always null — do not rely on it) |
| Thinking | `reasoning` | Render if you show a "thinking" indicator; otherwise ignore |
| Tools | `tool_call` / `tool_call_output` / `function_call` / `function_call_output` / `mcp_call` / `mcp_call_output` / `tool_approval_request` | Show execution progress, audit trail; `tool_approval_request` is an approval request (out of the SDK enum; appears when `permission_policy` is configured) |
| Session | `session_status` / `session_updated` / `error` | `session_status` is the **loop exit condition**; `error` must be logged |
| Sub-threads | `thread_created` / `thread_status` / `thread_message_sent` / `thread_message_received` / `thread_context_compacted` | Multi-thread orchestration and context compaction; usually ignored |
| Model and objectives | `model_request_start` / `model_request_end` / `outcome_evaluation` | Usable for latency stats and objective attainment |
| Client-event echoes | `message` / `interrupt` / `tool_approval_response` | Confirm your own sent events were received (an approval response appears in event history as a role=user `tool_approval_response` frame) |

**The client can send 6 types** (more than just `message`):

| type | Purpose |
| --- | --- |
| `message` | Send a user message; the agent enters `running` |
| `tool_approval_response` | **Tool approval response** — the main instrument for handling `requires_action`: `content[*].data` requires `batch_id` + `call_id` + `result` (`allow`/`deny`), plus `deny_message` when denying (the official OpenAPI writing `tool_confirmation` is lagging wording; field-tested as rejected by the server with 400) |
| `tool_call_output` / `function_call_output` | Fill in tool execution results (tools executed on the business side's behalf) |
| `interrupt` | Cancel the current turn (best-effort) |
| `define_outcome` | Declare this turn's goal and scoring criteria (`description` / `rubric` / `max_iterations`) |

**Session states, 4 kinds**:

| State | Description |
| --- | --- |
| `idle` | Creation completed or a processing turn ended; can send messages, mount files, archive, delete |
| `running` | Processing; can interrupt, can approve tool calls |
| `rescheduling` | A **transient** state meaning "rescheduling in progress" — not a terminal state; do not exit the loop on it (the SDK enum has it; the official state machine does not list it and field tests never reproduced it) |
| `terminated` | Archived / deleted / unrecoverable error; **terminal and unrecoverable** — only a new session continues |

**`stop_reason` is a dict, not a string**, shaped like `{"type": "end_turn"}`, located inside the `session_status`
event's data block. Its three values drive the business branches:

- `end_turn` — the model ended on its own; collect the result normally
- `requires_action` — **needs client intervention** (usually awaiting tool approval; `stop_reason` also carries `pending_call_ids` +
  `pending_batch_id`); send back a `tool_approval_response` (take `batch_id`/`call_id` from those two fields; SDK 1.27.3 has no matching
  constructor — hand-assemble the event) to continue; the business side must handle this branch
- `retries_exhausted` — retries exhausted; treat as failure and alert

When parsing pure REST, both `session_status` and `stop_reason` must be taken from the event's `content[*].data`;
the SDK already wraps them as the `ev.session_status` / `ev.stop_reason` properties.
**The Session object returned by `sessions.retrieve()` also carries `stop_reason`** (the SDK wraps it as a `StopReason` object;
`.to_dict()` yields `{"type": "end_turn"}`) — weak-interaction polling scenarios can read it directly instead of digging through the event stream (field-test verified).

**Streaming and polling are two different endpoints, not one endpoint toggled by a header** (field-test verified):

| Purpose | Endpoint | Notes |
| --- | --- | --- |
| Subscribe to real-time push | `GET /sessions/{id}/events/stream` + `Accept: text/event-stream` | A dedicated SSE endpoint |
| Send events | `POST /sessions/{id}/events` | **The request-body field name is `input`** (not `events`); always returns JSON — adding `Accept: text/event-stream` does not turn it into SSE |
| Pull event history / poll increments | `GET /sessions/{id}/events` | Supports `order` (asc/desc), `created_at[gt]` / `[gte]` / `[lt]` / `[lte]` (ISO 8601), `limit` (max 100), `page` |

## The 8 things production integration must handle

1. **Auth**: read the key only from environment variables / a secret service; never hardcode, never ship it to the frontend. One key can access every resource in the whole workspace.
2. **Session isolation**: one business user / one task maps to one Session; store the mapping yourself; never let multiple users share one Session.
3. **Must handle `requires_action`**: treating "idle means success" misses the awaiting-intervention branch and the task silently deadlocks.
4. **Timeouts and disconnects**: tasks can run minutes to hours; on SSE disconnect you must reconnect or degrade to polling the event list.
5. **Event fault tolerance**: unknown event types must not crash the flow; persist the raw payload on parse failure for troubleshooting.
6. **Idempotency**: for scheduled / event-triggered scenarios use a business idempotency key against duplicate submissions.
7. **Observability**: log `session_id` and the response header `x-request-id`; attaching `x-request-id` to support tickets speeds up diagnosis.
8. **Cost control**: **a session accrues runtime fees only while running (0.5 CNY/hour, sub-hour pro-rated precisely by actual duration); idle is free**
   — official commercialized billing has three parts: session runtime fee + model invocation fee (tokens billed separately) + tool/MCP invocation fee,
   plus a 10-hour runtime free quota (valid 30 days). Archive sessions promptly when tasks finish, and cap per-session turns to keep runaway loops from burning quota.

## The three most frequent pitfalls

| Pitfall | The correct way |
| --- | --- |
| The system prompt states the mount-time filled path `/uploads/data.csv`; the agent cannot find the file | The real path = `/mnt/session` + `mount_path`; the prompt must state the full real path `/mnt/session/uploads/data.csv` |
| `mount_path` filled as `/workspace/data.csv`; session creation fails with `invalid_parameter: Invalid resource` | `mount_path` **must start with `/uploads/`** — write `/uploads/workspace/data.csv` |
| Mounting fails right after upload | After upload the file must pass a security review (`checking` → `available` before mounting; `rejected` / `type_rejected` mean failure) — roughly a dozen-plus seconds in field testing |

## Related

- **Step-by-step integration tutorial (recommended starting point)** → [../tutorials/02-integrate-to-your-system.md](../tutorials/02-integrate-to-your-system.md)
- Runnable implementations → [code-python.md](code-python.md) / [code-java.md](code-java.md)
- Full endpoint table and request bodies → [api-endpoints.md](api-endpoints.md)
- Choosing an integration shape → [patterns.md](patterns.md)
- Provision the resources first → [../workflows/provision.md](../workflows/provision.md)
- Concepts and the event model → [../product/concepts.md](../product/concepts.md)
