# Python Integration Implementation (Three Shapes, Official SDK)

Companion tutorial: [../tutorials/02-integrate-to-your-system.md](../tutorials/02-integrate-to-your-system.md)

> **Every signature on this page comes from field testing**: real signatures pulled with `inspect`
> after `pip install dashscope` (field-tested version 1.27.3) — not doc transcription, not guesswork.
> If an SDK upgrade makes things disagree with this page, the field test wins; report the drift.
> To avoid the SDK dependency entirely, call REST directly — endpoints in [api-endpoints.md](api-endpoints.md),
> event-parsing essentials at the end of this page.

## Installation and client

```bash
pip install dashscope          # Managed Agents requires v1.26.2 or above
```

```python
from dashscope.agentstudio import Client

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
    workspace=os.environ["BAILIAN_WORKSPACE_ID"],   # note the parameter name is workspace, not workspace_id
    region="cn-beijing",
    timeout=60.0,                                    # optional
    max_retries=2,                                   # default 2
)
```

Every `Client.__init__` parameter is keyword-only: `api_key` / `workspace` / `region` / `base_url` /
`uid` / `timeout` / `max_retries` / `http_client`. Use `AsyncClient` for async, with an async request hook and `httpx.AsyncClient`:

```python
async def set_async_skill_user_agent(request):
    request.headers["User-Agent"] = skill_ua

async_http = httpx.AsyncClient(event_hooks={"request": [set_async_skill_user_agent]})
# Pass http_client=async_http to dashscope.agentstudio.AsyncClient.
# Close SDK/HTTP clients at application shutdown.
```

Verify the installed SDK accepts these HTTPX transports before a cloud call; otherwise use REST with the same header. See [UA propagation](../workflows/user-agent.md).

Resource entry points: `client.agents` / `environments` / `sessions` (with `sessions.events`) / `files` /
`deployments` / `deployment_runs` / `skills` / `vaults` (with `vaults.credentials`).

## Event contract (shared by all three shapes — read this first)

In the SDK, events and messages are the same `Message` structure; the `type` field tells them apart.

**The server pushes at least 23 event types** (22 in the SDK enum + `tool_approval_request`, which is
outside the enum) — not just the handful shown in typical doc examples. Handle only the ones you care
about; everything else must be safely ignored:

| Group | type |
| --- | --- |
| Body and reasoning | `message`, `reasoning` |
| Tools | `tool_call`, `tool_call_output`, `function_call`, `function_call_output`, `mcp_call`, `mcp_call_output`, `tool_approval_request` (approval request; outside the SDK enum) |
| Session and status | `session_status`, `session_updated`, `error` |
| Sub-threads | `thread_created`, `thread_status`, `thread_message_sent`, `thread_message_received`, `thread_context_compacted` |
| Model and outcome | `model_request_start`, `model_request_end`, `outcome_evaluation` |
| Client-event echoes | `message`, `interrupt`, `tool_approval_response`, `tool_call_output`, `function_call_output`, `define_outcome` |

**The client can send 6 kinds** (not just `message`); the SDK provides constructor functions:

```python
from dashscope.agentstudio import (
    user_message,              # (text_or_blocks, *, session_thread_id=None, metadata=None)
    user_interrupt,            # (*, session_thread_id=None, metadata=None) cancels the current turn
    user_tool_result,          # (*, tool_use_id, content, is_error=False, ...)
    user_custom_tool_result,   # (*, custom_tool_use_id, content, is_error=False, ...)
    user_define_outcome,       # (*, description, rubric=None, max_iterations=None, ...)
)
# No usable SDK constructor exists for tool-approval responses: user_tool_confirmation sends
# type=tool_confirmation, which the server rejects with 400 (not in the legal enum).
# Hand-roll tool_approval_response instead — see the "Handling tool approval" section
# and ../tutorials/06-tool-approval.md
```

**Four session statuses**: `idle` / `running` / `rescheduling` / `terminated`.
`rescheduling` is an intermediate state (a reschedule is in progress), **not a terminal one**.

**`stop_reason` is a dict, not a string** — shaped like `{"type": "end_turn"}` — hidden in a data
block of the `session_status` event; **the root of `sessions.retrieve()`'s return also carries
`stop_reason`** (in the weak-interaction polling shape, read it directly instead of digging through
the event stream). The SDK wraps both values as properties:

```python
ev.session_status      # -> "idle" / "running" / "rescheduling" / "terminated" / None
ev.stop_reason         # -> {"type": "end_turn"} / None
```

With plain REST you must extract `session_status` and `stop_reason` from `event["content"][*]["data"]` yourself.

## Event dispatching

```python
import logging

log = logging.getLogger(__name__)

TOOL_EVENTS = {
    "tool_call", "tool_call_output", "function_call", "function_call_output",
    "mcp_call", "mcp_call_output",
    "tool_approval_request",                     # approval request (outside the SDK enum) — this is what pops the approval card in your UI
}
THREAD_EVENTS = {                               # pushed only in multi-agent formations
    "thread_created", "thread_status", "thread_message_sent",
    "thread_message_received", "thread_context_compacted",
}
TERMINAL_STATUSES = {"idle", "terminated"}      # neither rescheduling nor running counts as terminal


class NeedsAction(RuntimeError):
    """Client intervention required (approval, missing info); must be handled separately."""


def handle_event(ev, on_text=None, on_tool=None):
    """Return the type string of stop_reason to signal the turn ended; return None to continue.

    In multi-agent formations, one stream mixes output from every member: tell threads
    apart with ev.thread_id (main thread has the thrd_ prefix, member sub-threads sthr_;
    a few events like session_status lack the field — missing means the coordinator's
    main thread). Mind the direction: the top-level field is named session_thread_id
    only when the client **sends** targeted events. See tutorials/07-multiagent-coordinator.md.
    """
    ev_type = getattr(ev, "type", None)
    thread_key = getattr(ev, "thread_id", None) or "main"

    if ev_type == "message" and getattr(ev, "role", None) == "assistant":
        for block in ev.content or []:
            if getattr(block, "type", None) == "text" and on_text:
                on_text(getattr(block, "text", "") or "")

    elif ev_type == "reasoning":
        pass                                     # reasoning trace; render here if you show it

    elif ev_type in TOOL_EVENTS:
        (on_tool or (lambda e: log.info("tool event: %s", ev_type)))(ev)

    elif ev_type in THREAD_EVENTS:
        log.info("formation thread event %s thread=%s", ev_type, thread_key)

    elif ev_type == "error":
        log.error("server error event: code=%s message=%s",
                  getattr(ev, "code", None), getattr(ev, "message", None))

    elif ev_type == "session_status":
        if ev.session_status in TERMINAL_STATUSES:
            reason = ev.stop_reason or {}
            return reason.get("type") or ev.session_status

    else:
        log.debug("ignoring event type: %s", ev_type)   # most of the 23 types don't matter to business logic — ignore, don't crash

    return None


def assert_success(stop_reason, session_id):
    """All three branches must be handled: checking only idle silently deadlocks on requires_action."""
    if stop_reason == "end_turn":
        return
    if stop_reason == "requires_action":
        raise NeedsAction(f"session {session_id} needs client intervention")
    if stop_reason == "retries_exhausted":
        raise RuntimeError(f"session {session_id} exhausted retries; treat as failure and alert")
    raise RuntimeError(f"session {session_id} ended abnormally: {stop_reason}")
```

## Completing a customer deliverable

These snippets show API contracts and application seams (`session_store`, `task_repo`). When asked for runnable files, include implementations or explicit interfaces/dependencies for those seams. Apply a total business deadline in addition to per-request timeouts. On reconnect, backfill history and subscribe without sending the original message again; keep the Session alive while awaiting approval. Do not interpret pagination's `next_page=None` as a durable incremental checkpoint.

## Shape A: synchronous / streaming conversation (**strong-interaction** scenario)

`client.sessions.events.stream()` returns an iterable `EventStream` that supports the `with` context.

```python
AGENT_ID = os.environ["CMA_AGENT_ID"]           # agent_xxx
ENV_ID = os.environ["CMA_ENVIRONMENT_ID"]       # env_xxx


def chat_stream(user_id, text, session_store):
    """session_store: your business-side user_id -> session_id mapping (Redis/DB)."""
    session_id = session_store.get(user_id)
    if not session_id:
        session = client.sessions.create(
            agent=AGENT_ID,
            environment_id=ENV_ID,
            title=f"Session of user {user_id}",
            environment_variables={"API_BASE_URL": API_BASE_URL, "LOG_LEVEL": "info"},
                                                 # non-sensitive config injected in plaintext (os.environ reads the real values); non-sensitive content only
            metadata={"user_id": str(user_id)},   # one Session per user; never share across users
        )
        session_id = session.id
        session_store.set(user_id, session_id)

    stop_reason = None
    with client.sessions.events.stream(session_id, timeout=600.0) as stream:
        # Open the stream before sending: SSE has no history replay — send-then-stream misses the first frames
        client.sessions.events.send(session_id, [user_message(text)])
        for ev in stream:
            chunks = []
            stop_reason = handle_event(ev, on_text=chunks.append)
            for chunk in chunks:
                yield chunk                       # pass through to the frontend
            if stop_reason:
                break

    assert_success(stop_reason, session_id)
```

FastAPI mounting:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.post("/chat")
def chat(user_id: str, text: str):
    return StreamingResponse(
        (f"data: {json.dumps({'text': c}, ensure_ascii=False)}\n\n"
         for c in chat_stream(user_id, text, session_store)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # disable Nginx buffering
    )
```

**The key never ships to the frontend**; the business service passes text through only.

### Handling tool approval (the right way for `requires_action`)

A `stop_reason` of `requires_action` means the agent is waiting for tool approval; it additionally
carries `pending_batch_id` + `pending_call_ids` (**there is no `event_ids`**). The server
simultaneously pushes a `tool_approval_request` event (outside the SDK enum) describing the tool
and arguments awaiting approval. For sending the approval response back, **there is no usable SDK
constructor** (`user_tool_confirmation` sends `type: "tool_confirmation"`, which the server rejects
with 400) — hand-roll the dict:

```python
def tool_approval_response(batch_id, call_id, result, deny_message=None):
    data = {"batch_id": batch_id, "call_id": call_id, "result": result}
    if deny_message and result == "deny":
        data["deny_message"] = deny_message
    return {"role": "user", "type": "tool_approval_response",
            "content": [{"type": "data", "data": data}]}

client.sessions.events.send(session_id, [
    tool_approval_response(batch_id=stop_reason["pending_batch_id"],
                           call_id=stop_reason["pending_call_ids"][0], result="allow"),
    # deny: result="deny", deny_message="This operation requires a human"
])
# stream() again to keep consuming subsequent events
```

**The data trio `batch_id` + `call_id` + `result` is mandatory**; `result` accepts only `"allow"` / `"deny"`.
Biggest trap: **HTTP 200 does not mean the approval was accepted** — a malformed body or no matching
pending call still gets a 200 on the POST; the error surfaces only in an `error` event on the event
stream, and the session bounces back to `requires_action` silently deadlocked. After sending, you
must keep consuming the stream to confirm.

To cancel the running turn, use `user_interrupt()` (best-effort; not guaranteed to take effect instantly).
The full approval round-trip loop is in [../tutorials/06-tool-approval.md](../tutorials/06-tool-approval.md).

## Shape B: async tasks (submit-then-query, **weak-interaction** scenario)

```python
def submit_task(biz_order_no, prompt, file_path=None, task_repo=None):
    """Submit and return immediately; do not wait for the result."""
    resources = None
    if file_path:
        uploaded = client.files.upload(file_path)          # accepts a path / file object
        wait_file_available(uploaded.id)
        resources = [{"type": "file", "file_id": uploaded.id,
                      "mount_path": "/uploads/input.txt"}]
        # mount_path must start with /uploads/; the sandbox path = /mnt/session + mount_path —
        # in the example above the agent actually sees /mnt/session/uploads/input.txt, and the
        # prompt must state the real path (.csv is rejected at upload; the whitelist is
        # .txt/.md/.json/.xlsx/.pdf/.png only — rename CSV to .txt first)
        prompt = f"{prompt}\nInput file path: /mnt/session/uploads/input.txt"

    session = client.sessions.create(
        agent=AGENT_ID, environment_id=ENV_ID, title=f"Task {biz_order_no}",
        resources=resources, metadata={"biz_order_no": biz_order_no},
    )
    task_repo.save(biz_order_no=biz_order_no, session_id=session.id, status="submitting")
    # Persist the ID before sending. On an ambiguous send timeout, reconcile this Session;
    # do not create another Session or blindly resend the business operation.
    client.sessions.events.send(session.id, [user_message(prompt)])
    task_repo.update(biz_order_no, status="running")
    return session.id


def wait_file_available(file_id, timeout=120.0, interval=2.0):
    """After upload, the file must pass the security scan before it can be mounted."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        info = client.files.retrieve(file_id)
        if info.status == "available":
            return info
        if info.status in ("rejected", "type_rejected"):
            raise RuntimeError(f"file failed the security scan: {info.status}")
        time.sleep(interval)
    raise TimeoutError(f"file {file_id} scan timed out")


def poll_task(biz_order_no, task_repo, max_wait=3600):
    """One fresh Session per business task; inspect current status, then collect history once."""
    task = task_repo.get(biz_order_no)
    session_id = task.session_id
    deadline = time.monotonic() + max_wait
    stop_reason = None
    while time.monotonic() < deadline:
        info = client.sessions.retrieve(session_id)
        if info.status in ("idle", "terminated"):
            stop_reason = (info.stop_reason or {}).get("type")
            if stop_reason:
                break
            if info.status == "terminated":
                task_repo.update(biz_order_no, status="failed")
                return
        time.sleep(min(5, max(0, deadline - time.monotonic())))

    if stop_reason is None:
        task_repo.update(biz_order_no, status="timeout")
        return                          # caller decides cancellation; do not destroy recovery state
    if stop_reason == "requires_action":
        task_repo.update(biz_order_no, status="needs_action")
        return                          # KEEP Session alive so approval can resume it
    if stop_reason != "end_turn":
        task_repo.update(biz_order_no, status="failed")
        return

    texts, cursor = [], None
    seen_cursors = set()
    while True:
        if time.monotonic() >= deadline:
            task_repo.update(biz_order_no, status="timeout")
            return
        page = client.sessions.events.list(session_id, page=cursor, limit=100, order="asc")
        for ev in page.data:
            handle_event(ev, on_text=texts.append)   # only assistant message text, not the user echo
        cursor = page.next_page
        if not cursor:
            break                       # last page; never start again at page=None in this collection
        if cursor in seen_cursors:
            raise RuntimeError("repeated event page cursor")
        seen_cursors.add(cursor)

    task_repo.update(biz_order_no, status="success", result="".join(texts))
    # Archive only after result/artifact collection and according to the caller's retention policy.
    # Never archive unconditionally in finally: that terminates sessions awaiting human approval.

```

`sessions.events.list()` accepts `types=[...]` to fetch only the types you care about, which cuts
parsing cost significantly. **But multiple values are broken**: the SDK joins the list into a comma
string (`types=a,b`), which the server does not recognize and silently returns empty — field-tested,
`types=["message","error"]` returns 0 rows. Either call once per single value, or drop `types`
and pull everything.

## Shape C: scheduled unattended runs (Deployment, **weak-interaction** scenario)

```python
def create_daily_deployment(agent_version):
    return client.deployments.create(
        name="Daily order summary",
        agent={"id": AGENT_ID, "version": agent_version},   # pin the version in production to prevent behavior drift
        environment_id=ENV_ID,
        schedule={"type": "cron", "expression": "0 9 * * 1-5",
                  "timezone": "Asia/Shanghai"},             # omitting schedule = manual trigger; with a schedule, timezone is required (missing → 400)
        initial_events=[user_message("Summarize yesterday's order data")],      # 1-50 entries
    )


def trigger_now(deployment_id):
    return client.deployments.run(deployment_id)             # for integration testing; no need to wait for the schedule


def collect_runs(deployment_id, processed_run_ids):
    """Use run_id as the idempotency key to prevent double processing."""
    page = client.deployments.list_runs(deployment_id, limit=50)
    for run in page.data:
        if run.id in processed_run_ids:
            continue
        yield client.deployment_runs.retrieve(run.id)   # single-run query is GET /deployment_runs/{id}
```

Pause / resume with `client.deployments.pause(id)` / `.unpause(id)` — do not delete-and-recreate.

## Other common calls

```python
# List resources (also verifies the auth key matches the workspace)
for a in client.agents.list(limit=20).data:
    print(a.id, a.name)

# Create an environment: the base image already ships pandas/numpy/ffmpeg etc.
# (~190 pip packages + node/ruby and other toolchains) — only declare packages the
# base lacks; cargo/go groups install nothing even when declared (silently ineffective)
client.environments.create(
    name="data-sandbox",
    config={"type": "cloud",
            "packages": {"pip": ["polars"]},
            "networking": {"type": "unrestricted"}},
)

# Update an Agent: version is required; the server validates it as an optimistic lock —
# a mismatch conflicts (409). The semantics are partial replace: pass only the fields
# you want changed; omitted fields stay unchanged
client.agents.update(AGENT_ID, version=current_version, system_prompt="...")

# Vault: note the field is display_name
vault = client.vaults.create(display_name="Production credentials")
# A credential (secret) must carry auth.networking.allowed_hosts (required since 2026-09):
# client.vaults.credentials.create(vault_id=vault.id,
#     display_name="MY_API_KEY", auth={
#         "type": "environment_variable", "secret_name": "MY_API_KEY",
#         "secret_value": "<real secret value>",
#         "networking": {"allowed_hosts": ["api.example.com"]}})
# Injection semantics in cookbook/08: inside the sandbox os.environ yields the placeholder
# BMA_SECRET_PLACEHOLDER_MY_API_KEY; the real value substitutes the Authorization header
# only when the egress gateway hits allowed_hosts
```

## Exception handling

```python
from dashscope.agentstudio import (
    AgentStudioError,        # base class (attributes code / message / request_id / status_code / raw)
    APIStatusError,          # common base of status-code errors (parent of most classes below)
    AuthenticationError,     # 401, invalid key or workspace mismatch
    PermissionDeniedError,   # 403
    NotFoundError,           # 404
    InvalidRequestError,     # 400
    ConflictError,           # 409 (e.g. Agent version mismatch)
    RateLimitError,          # 429, rate-limited; retry with backoff
    OverloadedError,         # 503
    InternalServerError,     # 500 / 502 / 504
    APITimeoutError, APIConnectionError,
    StreamError, StreamClosedError,   # SSE stream failures; reconnect or degrade to polling
)
# These are all 14 exception classes in the SDK (counted via inspect in a live field test);
# HTTP 400/401/403/404/409/429/5xx map automatically to the matching class by status code —
# 401/404/400 verified live. There is no dedicated "approval rejected" exception —
# approval-response errors surface only in error events on the event stream (the POST always
# returns 200); see "Handling tool approval".

try:
    ...
except RateLimitError:
    ...      # retry with backoff
except AgentStudioError as e:
    log.exception("CMA call failed")    # keep x-request-id in the log for support tickets
```

## Related

- Full endpoint table and fields → [api-endpoints.md](api-endpoints.md)
- Shape selection and more shapes → [patterns.md](patterns.md)
- Java implementation → [code-java.md](code-java.md)
