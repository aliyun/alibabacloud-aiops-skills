# Integration Shapes and Selection

Integration design has **exactly one first decision point**: does the caller wait online for the result?

The answer determines the whole architecture — whether to keep long-lived connections, whether to build a task table, how to set timeouts, how the frontend behaves.
Pick the macro scenario first, then the concrete shape. Concrete endpoints and fields defer to [api-endpoints.md](api-endpoints.md);
the full landing walkthrough is [../tutorials/02-integrate-to-your-system.md](../tutorials/02-integrate-to-your-system.md).

| | Scenario 1: strong interaction | Scenario 2: weak interaction |
| --- | --- | --- |
| **Positioning** | Use it as a **cloud agent** | Use it as a **service** |
| **Caller** | Waits online, wants to watch the process | Does not wait; cares only about the final result |
| **Connection** | Must listen to the SSE event stream | No long connection needed; just query status back |
| **Required infrastructure** | SSE proxy, reconnect/degrade-to-polling | Task table (business id ↔ `session_id` ↔ status)|
| **Typical shapes** | Streaming conversation, synchronous Q&A | Async tasks, scheduled unattended runs, event-driven embedding |
| **Code implementations** | Shape A | Shape B (you trigger) / Shape C (auto-triggered on schedule)|

**The judging question**: ask the customer "before the result is out, is anyone staring at a screen waiting?"
Yes → Scenario 1; No → Scenario 2. Customers saying "both" is common — that means both coexist (the same agent can serve both),
and you build the one carrying the main traffic first.

---

# Scenario 1: strong interaction (cloud agent)

The caller waits online and **must manage the event-stream lifecycle**. The core cost is connection management, not business logic.

## Streaming (SSE) conversation

```
Frontend ⇄ Business service (forward/passthrough) ⇄ Agent event stream
```
- **Fits**: human-facing conversational UIs that must render as content is generated and show intermediate steps.
- **Constraints**: the business service must support long-lived connections; the gateway / load balancer must **disable response buffering**; disconnects must reconnect or degrade to polling.
- **Caution**: **never ship the Bailian key to the frontend** — always proxy through the business service.
- **CLI equivalents**: `session run` / `session send` (streaming by default).

## Synchronous Q&A (request-response)

```
Business service → create session → send message → wait for the full result → return to the frontend
```
- **Fits**: single-turn Q&A, short tasks (seconds to a dozen-plus seconds), internal-tool style interfaces.
- **Constraints**: longer tasks hit gateway/browser timeouts. **Do not use this shape for tasks over 30s** — move to Scenario 2.
- **CLI equivalent**: `session run --no-stream`.

## Key constraints of strong interaction

- The event loop must branch on `stop_reason.type` three ways; checking only `idle` silently deadlocks
- With tool approval pending, the session **returns to `idle` but `stop_reason.type` is `requires_action`** — that is a pause, not an end;
  you must send back a `tool_approval_response` (the `batch_id` + `call_id` + `result` trio) to continue (see [../tutorials/06-tool-approval.md](../tutorials/06-tool-approval.md))
- When the agent has a multi-agent formation, member output mixes into one stream — split by `thread_id` (main thread `thrd_` prefix;
  member sub-threads `sthr_` prefix; only client-sent targeted events use the top-level field `session_thread_id`)
- The user clicking "stop" uses the `interrupt` event, but it is best-effort — showing "stopping…" in the UI is more honest

---

# Scenario 2: weak interaction (as a service)

The caller does not wait. **Sessions are stateful server-side and events are persisted**, so the task advances without holding a connection —
send one turn → poll back to `idle` → collect the result → send the next turn if needed. **Weak interaction does not mean single-turn.**

The core cost is state management and idempotency, not connections.

## Async tasks (submit-then-query)

```
Business system submits the task → returns a task number immediately (store session_id) → background polls/consumes events → writes back the result + notifies on completion
```
- **Fits**: long-running tasks (document batch processing, deep analysis, multi-step operations).
- **Constraints**: you need a task table (business task id ↔ `session_id` ↔ status); handle timeouts and failure retries.
- **CLI equivalents**: `session run --output json` to get `session_id`, then `session events --all` to query back.

## Scheduled unattended runs

```
Deployment (schedule + initial_events) → the server triggers on time → the agent produces → write back / push
```
- **Fits**: daily reports, inspections, batch reconciliation, periodic data wrangling.
- **Constraints**: the `schedule` is executed by the Bailian server; if an external cron already does the same thing, confirm no double-triggering before going live.
- **Landing the outputs**: how results return to the business system is your design (the agent calls a write-back API proactively, or the business side periodically pulls session artifacts).
- **Full steps**: [../tutorials/04-scheduled-deployment.md](../tutorials/04-scheduled-deployment.md).

## Event-driven embedding

```
Business event (ticket created / document uploaded / alert) → business service calls the agent → parses the conclusion → writes back to business tables → triggers downstream flows
```
- **Fits**: embedding the agent into existing business flows with no standalone UI.
- **Constraints**: an **idempotency key** against duplicate processing is mandatory; agent conclusions need confidence/escalation strategy (low confidence → human),
  and high-risk actions must not be auto-executed directly.

## Key constraints of weak interaction

- **The `session_id` must be persisted** — otherwise the task is untraceable and unreplayable
- **The idempotency key is not optional**: worker restarts, overlapping pulls, and re-runs all cause the same result to be processed twice
- Nobody watching means **failures must alert** — a scheduled task silently failing for days is the most common incident
- Artifacts (files the agent writes to the sandbox's `/mnt/session/outputs/`) are auto-scanned into downloadable artifacts (retained 30 days, downloadable even after the session is archived), but **business data must be written back to the business system actively** — artifacts are staging, not a persistence layer; the sandbox filesystem itself is recycled with the session

---

# The orthogonal dimension: multi-tenant / multi-user isolation

This is not a third scenario — it is a design **layered on top of any of the shapes above**.

- One business user (or one task) maps to one Session; do **not** let multiple users share a Session.
- The business side stores the `user/task ↔ session_id` mapping itself; write the business key into `metadata` at session creation (e.g. `{"user_id": "..."}`) for easy reverse lookup.
- For task working context across sessions: MA Memory Store is launched built-in working memory. For UserId-scoped personalized memory: use the separate Bailian Memory Library. Do not substitute their contracts or treat memory as an authorization/isolation mechanism; preserve business-side user/tenant access controls. See [concepts](../product/concepts.md#memory-store-working-memory).
- For per-tenant isolation of config/credentials: non-sensitive config goes straight into `environment_variables` at session creation (one copy per session, plaintext passthrough into the sandbox); high-sensitivity secrets are isolated via different Environments / Vaults, or overridden at session creation (`--environment` / `--vault`). The two-path selection layering is in [../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md).

# Selection quick reference

| Business signature | Scenario | Shape |
| --- | --- | --- |
| Has a conversational UI, wants to watch the process | Strong interaction | Streaming (Shape A)|
| Internal interface, very short tasks (< 30s)| Strong interaction | Synchronous (Shape A)|
| Tasks longer than 30s | Weak interaction | Async (Shape B)|
| Nobody triggers it; runs on a cycle | Weak interaction | Scheduled (Shape C)|
| Embedded in existing business flows | Weak interaction | Event-driven (a Shape B variant)|
| Serving multiple customers / tenants | Either | Layer isolation design on top of any shape |

# Pre-delivery self-check

- [ ] The key appears nowhere in code, the frontend, or `agents.yaml`
- [ ] Unknown event types cannot crash the flow
- [ ] Long tasks will not hit timeouts (macro scenario chosen correctly)
- [ ] `session_id` is persisted and usable for troubleshooting and replay
- [ ] Rate limiting and turn caps are in place
- [ ] Failure paths have an explicit fallback (escalate to human / retry / alert)
- [ ] Weak interaction, additionally: the idempotency key is persisted and failure alerts are wired
