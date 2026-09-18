# Tutorial 06: Human Approval for High-Risk Operations — Make the Agent Stop and Wait for Your Nod

| Item | Value |
| --- | --- |
| **Goal** | When a session enters the pending-approval state, correctly extract the tool call awaiting confirmation, send back the approval or denial, and let the session run to completion — plus proactively interrupt runaway turns |
| **Capabilities involved** | `stop_reason.requires_action` / `tool_approval_request` events / `tool_approval_response` responses / `permission_policy` config / `interrupt` events / the Event stream |
| **Difficulty** | Expert |
| **Prerequisites** | [02-integrate-to-your-system.md](02-integrate-to-your-system.md) done (able to send and receive events, able to parse `session_status`) |
| **Estimated time** | 20-30 minutes |
| **Source** | Real-server field tests (E2E runs through the allow / deny / interrupt chains) + probing the server's error enums |

> **Scope note**: this tutorial covers **how to configure approvals and how to respond correctly once a request arrives**.
> Configuration: when creating/updating an Agent, add `"permission_policy": {"type": "always_ask"}` inside `tools[*].configs[*]` for that tool (`always_allow` means approval-free, which is also the default).
> This field currently has **no official documentation** (recorded in neither the OpenAPI spec nor the SDK); the form above is verified working against the real server.
>
> **Important**: the `type: "tool_confirmation"` emitted by dashscope SDK 1.27.3's `user_tool_confirmation`
> constructor is **rejected by the server with 400** — the SDK lags behind the server.
> Build the approval response by hand as this tutorial does (the server's 400 error lists the legal enums, and tool_confirmation is not among them).

## Scenario

An Agent calling tools on its own is efficiency — but no enterprise will let it unconditionally drop databases, send external notifications, or touch payments. The control point is **tool-call approval**: when the Agent wants to invoke a tool, it stops first and executes only after a human nods.

This is the most persuasive piece in front of an enterprise security review, and the reason the `requires_action` branch exists. If integration code only treats "session back to `idle`" as completion, the session **silently hangs in the waiting-for-approval state** — the task looks "finished but produced nothing" — one of the hardest failure classes to diagnose during integration.

## Final artifacts

An event loop that handles the approval round trip: pending approval received → call details extracted → approve/deny → the session runs on to a real finish. Plus one Agent with the approval policy configured (`permission_policy`).

## Steps

### 0. Configure which tools require approval

```bash
export CMA_BASE="https://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
```

Add `permission_policy` to high-risk tools in the Agent's tool config (field-tested form; not yet in official docs):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/agents" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Assistant with approvals",
    "model": {"id": "qwen3.8-max"},
    "system": "...",
    "tools": [
      {
        "type": "builtin_toolkit",
        "default_config": {"enabled": false},
        "configs": [
          {"name": "bash", "enabled": true, "permission_policy": {"type": "always_ask"}},
          {"name": "read", "enabled": true},
          {"name": "write", "enabled": true, "permission_policy": {"type": "always_ask"}}
        ]
      }
    ]
  }'
```

`permission_policy` values: `{"type": "always_ask"}` (human approval required before every call) or `{"type": "always_allow"}` (approval-free, the default). Granularity is **per tool** — bash requires approval, read does not, so write them separately. Field-probing notes: a string value fails with a Jackson deserialization error (so it is an object), and an empty object fails with `permission_policy.type cannot be empty (allowed values always_allow / always_ask)` — the server's own error spells out the legal enum.

### 1. Recognize the "waiting for you" state

When the session returns to `idle`, the `session_status` event carries `stop_reason`. Its `type` has three values: `end_turn` (truly finished) / `requires_action` (**waiting for you**) / `retries_exhausted` (retries exhausted, documented officially).

**In approval scenarios `requires_action` carries two extra fields** (field-tested structure; there is no `event_ids` key; `end_turn` is just `{"type": "end_turn"}`):

| Field | Notes |
| --- | --- |
| `pending_call_ids` | List of call IDs awaiting approval (`call_` prefix) |
| `pending_batch_id` | Approval batch ID — **required when sending the response**; omitting it fails silently (see the trap in step 3) |

The data sits in the event's `content[*].data` (`GET /sessions/{id}` also has stop_reason at the root):

```json
{"type": "session_status",
 "content": [{"type": "data",
              "data": {"session_status": "idle",
                       "stop_reason": {"type": "requires_action",
                                       "pending_batch_id": "a124338d-…:13d6f34c…",
                                       "pending_call_ids": ["call_6fd840ee…"]}}}]}
```

**`idle` + `requires_action` is not the end — it is a pause.** Your completion logic must distinguish the two.

### 2. Extract the pending call

The most reliable source of the two key values (`batch_id` and `call_id`) is `stop_reason` itself: `pending_batch_id` + `pending_call_ids`. You can also search the event stream / `GET /sessions/{id}/events` for events of type **`tool_approval_request`** (the server-initiated approval request — note: not `tool_confirmation`):

```python
pending_batch, pending_call = None, None
for ev in client.sessions.events.list(session_id, types=["tool_approval_request"],
                                      order="desc", limit=10).data:
    for block in ev.content or []:
        data = getattr(block, "data", None)
        if isinstance(data, dict) and "call_id" in data:
            pending_batch, pending_call = data["batch_id"], data["call_id"]
            break
    if pending_call:
        break
```

The `tool_approval_request` event's `content[*].data` contains (field-tested sample):

```json
{"type": "tool_approval_request", "role": "assistant", "thread_id": "thrd_…",
 "content": [{"type": "data",
              "data": {"tool_type": "builtin", "name": "bash",
                       "arguments": "{\"command\": \"echo hello\", …}",
                       "call_id": "call_6fd840ee…", "batch_id": "a124338d-…:13d6…"}}]}
```

That is what the approval card shows: which tool, what arguments, when it was raised. In the SDK the constructor parameter is named `tool_use_id` while the actual JSON field is **`call_id`** — pure REST integrations should look for `call_id`.

**How to verify**: you obtain a non-empty `call_id` and `batch_id`. If not, this `requires_action` is not waiting on tool approval — go back and check which fields `stop_reason` actually carries.

### 3. Send back the approval or denial

The response event type is **`tool_approval_response`**. dashscope SDK 1.27.3's `user_tool_confirmation` constructor is **unusable** (it sends `type: "tool_confirmation"`, rejected by the server with 400 — not in the legal enum), so build it by hand:

```python
def tool_approval_response(batch_id, call_id, result, deny_message=None):
    data = {"batch_id": batch_id, "call_id": call_id, "result": result}
    if deny_message and result == "deny":
        data["deny_message"] = deny_message
    return {"role": "user", "type": "tool_approval_response",
            "content": [{"type": "data", "data": data}]}

# Approve
client.sessions.events.send(session_id,
    [tool_approval_response(pending_batch, pending_call, "allow")])

# Deny (deny_message travels back to the Agent via tool_call_output, telling it why not, so it can switch approach)
client.sessions.events.send(session_id,
    [tool_approval_response(pending_batch, pending_call, "deny",
                            deny_message="This operation must be run manually in the backend; output a to-do list instead")])
```

**The data triple is mandatory: `batch_id` + `call_id` + `result`.**

- `batch_id` comes from `stop_reason.pending_batch_id` (or the `tool_approval_request` event)
- **`result` accepts only `"allow"` or `"deny"`**. With `"approve"` the SDK constructor raises `ValueError` locally; over pure REST the HTTP call still returns 200 and the error appears only in the event stream's `error` event (`literal_error`)
- `deny_message` only matters when denying. Field-tested: after a denial the Agent's `tool_call_output` reads
  `"Permission to use bash has been rejected. Rejection message: <your deny_message>"`;
  when you offer an alternative, the Agent follows it (field-tested: it switched approach — no infinite retry)

**The biggest trap: HTTP 200 ≠ the approval was accepted.** On malformed data (missing `batch_id` / `call_id`, illegal result) or no matching pending item, the POST still returns 200; the error appears only in the event stream's `error` event (`code: "invalid_tool_approval"`), and the session bounces back to the same `requires_action` — the top cause of the "silent hang" warned about at the start of this tutorial. **You must keep consuming the event stream to confirm.**

**Expected result**: after sending, the session re-enters `running`.
**How to verify**: keep consuming the event stream — you can see the approved tool actually execute (real stdout inside `tool_call_output`), or, after a denial, the Agent take a different approach (the final reply reflects the deny_message guidance).

Pure-REST wire format (assemble it this way in Java and other languages):

```json
{"input": [{"role": "user", "type": "tool_approval_response",
            "content": [{"type": "data",
                         "data": {"batch_id": "<stop_reason.pending_batch_id>",
                                  "call_id": "<call_id>", "result": "allow"}}]}]}
```

When denying, add `"deny_message": "..."` in `data`.

### 4. Wire the round trip back into the event loop

Approval is not a one-shot action — one task may trigger it several times. The event loop must handle it repeatedly:

```python
def run_with_approval(session_id, approve_fn, max_rounds=10):
    """approve_fn(call_id) -> ("allow" | "deny", deny_message or None)

    approve_fn is your business approval logic: check permissions, send a Feishu card
    and wait for a human click, or auto-allow by rule.
    """
    for _ in range(max_rounds):
        stop_reason = None
        with client.sessions.events.stream(session_id, timeout=600.0) as stream:
            for ev in stream:
                stop_reason = handle_event(ev)      # see tutorial 02 / code-python.md
                if stop_reason:
                    break

        if stop_reason.get("type") != "requires_action":
            return stop_reason                     # end_turn / retries_exhausted / abnormal

        batch_id = stop_reason.get("pending_batch_id")
        call_ids = stop_reason.get("pending_call_ids") or []
        if not batch_id or not call_ids:
            raise RuntimeError(f"Session {session_id}: pending items are not tool approvals; inspect stop_reason manually")

        for call_id in call_ids:
            result, deny_message = approve_fn(call_id)
            client.sessions.events.send(session_id,
                [tool_approval_response(batch_id, call_id, result, deny_message)])

    raise RuntimeError(f"Session {session_id}: approval round trips exceeded {max_rounds}; manual intervention required")
```

**Never omit `max_rounds`.** Broken approval logic (say, always deny while the Agent forever retries the same tool) becomes an infinite round trip that keeps billing runtime.

### 5. Proactively interrupt a runaway turn

The Agent went off the rails, or the user hit "stop" — use `interrupt`:

```python
from dashscope.agentstudio import user_interrupt

client.sessions.events.send(session_id, [user_interrupt()])
```

The wire format is minimal, no content: `{"input": [{"role": "user", "type": "interrupt"}]}`

Interrupt is **best-effort** (SDK source docstring verbatim: `Cancel the agent's current turn (best-effort)`):
after sending, the current turn stops as soon as possible, but instant effect is not guaranteed. In the UI do not show "stopped"; "stopping" is the honest label.
Field-tested reference: interrupting a running `sleep 25` at second 12 returned the session to `idle`
**0.3 seconds later** — the stream shows one `tool_call_output` (output `"The tool call was interrupted."`) plus one closing assistant message, and the final `stop_reason` is a plain `end_turn` (**there is no dedicated interrupted event type or state**; detecting an interrupt means checking the stream for the interrupt echo and the cut-off tool_call_output).

After an interrupt the session is back to `idle` and **can still receive new messages** — it does not terminate the session, it only cancels the current turn (field-tested: sending a new message after an interrupt gets a normal reply ending in end_turn).

### 6. Production notes

- **Approval needs a timeout backstop**: what if nobody ever clicks? Define a timeout policy (auto-deny on timeout, hand off to a human ticket); never let the session hang indefinitely while billing
- **Approval authority is judged on your side**: Bailian only delivers the request to you; the permission model is your business responsibility
- **Audit every approval action**: who, when, which `call_id` was approved, what the `deny_message` said. Event history keeps the Agent-side record, but "which employee clicked" is known only to you
- **Do not build approvals around popups**: in async shapes nobody is online; approval requests must land in tickets / IM cards
- **In fleet scenarios, target precisely**: when the Agent has a multi-agent fleet, both approval responses and `user_interrupt` must carry `session_thread_id` (a top-level field on the **client-sent direction**, whose value is the sub-thread's `thread_id`, i.e. the `sthr_` prefix), otherwise they may land on another thread. See [07-multiagent-coordinator.md](07-multiagent-coordinator.md) step 6

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| Task "finished" but no results | Only treated `idle` as success, missing `requires_action` | Branch on `stop_reason.type` into the three cases |
| `ValueError` thrown after sending the confirmation | `result` was set to `approve` | Only `allow` or `deny` |
| Pure-REST request rejected by the server (HTTP 400) | Event type written as `tool_confirmation` (old SDK / old docs name) | Use `tool_approval_response`; the `user_tool_confirmation` constructor (dashscope 1.27.3) is currently unusable |
| Confirmation sent, POST returned 200, session unmoved | Missing `batch_id` (or call_id mismatch) — the error appears only in the stream's `error` event and the session bounces back to the same `requires_action` | Consume the stream for `error` events; take `batch_id` from `stop_reason.pending_batch_id`, `call_id` from `pending_call_ids` |
| Approval round trips never stop | After denial the Agent retries the same tool (field-tested: a deny_message offering an alternative avoids this) | Set `max_rounds`; put the alternative in `deny_message` |
| Interrupted but still producing output | Interrupt is best-effort | UI shows "stopping"; update state only after `session_status` |
| Session unusable after an interrupt | Misread semantics | An interrupt only cancels the current turn; the session is back to `idle` and still accepts messages (field-tested) |
| Approval configured but never triggered | `permission_policy` in the wrong place or wrong type | Put it inside `tools[*].configs[*]`, object form `{"type": "always_ask"}`; on mistakes the server's error lists the legal enum |
| Customer asks how long the approval wait times out | The timeout policy is not public | Define your own business timeout: auto-deny on timeout, hand off to a human ticket |

## Going further

- Event-loop skeleton and the three branches → [02-integrate-to-your-system.md](02-integrate-to-your-system.md) step 5
- Full Python / Java implementations → [../integration/code-python.md](../integration/code-python.md) / [../integration/code-java.md](../integration/code-java.md)
- Full table of the 6 client-sent event types → the Event section of [../product/concepts.md](../product/concepts.md)
- Security and compliance talking points → [../product/faq.md](../product/faq.md)
