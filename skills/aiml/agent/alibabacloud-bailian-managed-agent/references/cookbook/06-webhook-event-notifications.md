# 06 · Advanced: Webhook Event Notifications — Let It Tell You When the Task Finishes

> This recipe covers the Webhook mechanism of Bailian Managed Agents: turning "something happened" (a session finished, a deployment run ended, a resource changed) into a proactive HTTP push, instead of you polling endlessly. All key behaviors are field-tested (2026-09, cn-beijing region; the receiving end was a Python script on a public-internet server).
>
> Relation to the rest of the series: 02's Deployment solves "the task runs on schedule", 04's SSE solves "a human watching live", and this recipe solves "notify me when it's done" — the three combined give the complete unattended closed loop.

## Scenario: Shibei E-commerce's reconciliation notifier

"Shibei E-commerce" is a fictional cross-border e-commerce company that reconciles every night: a reconciliation bot (a cron-triggered Deployment) checks the day's order ledger. The ops teammate's ask is plain:

> "Once the task is launched I shouldn't have to babysit it — when it finishes, or when it crashes, send my server a notification."

Before Webhooks there was only pull mode: periodically polling `GET /deployments/{id}/runs`, `GET /sessions/{id}`, asking "done yet? done yet?". The Webhook inverts it — you subscribe to events, and the platform POSTs your receiver when they happen:

```
Pull mode (polling):    you -> platform   "done yet?"   xN times
Push mode (webhook):  platform -> you     "done"        x1 time
```

## 1. What a Webhook is

- **A workspace-level standalone resource**: on par with agent, session, deployment; id prefix `wep_`. At most 20 per workspace.
- **Subscribes to named events**: 32 total, in 9 categories; `*` wildcards are not supported:

| Category | Events |
|---|---|
| Session control plane | session.created / updated / archived / deleted |
| Session run state | session.status_run_started / status_idled / status_terminated |
| Session Thread | session.thread_created / thread_run_started / thread_idled / thread_terminated |
| Agent | agent.created / updated / archived |
| Deployment | deployment.created / updated / archived / paused / unpaused |
| Deployment Run | deployment_run.started / failed / succeeded |
| Environment | environment.created / updated / archived / deleted |
| Vault | vault.created / archived / deleted |
| Vault Credential | vault_credential.created / archived / deleted |

- **Events carry no resource content**: the body holds only the resource id and the event type; to learn the reconciliation outcome, take `data.id` and query the corresponding endpoint.

## 2. Create a Webhook

For this repository's endpoint-creation examples and evaluation tasks, use **`https://www.baidu.com`**. The requested test convention avoids placeholder endpoints rejected by the platform. This example verifies resource creation and read-back only; it does not claim that Baidu receives or processes Webhook notifications. For the receiver implementation, delivery test and signature verification in later sections, first replace the sample URL with the customer's actual controlled receiver.

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "$BASE/webhook_endpoints" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{
    "description": "Shibei E-commerce reconciliation-task notifier",
    "url": "https://www.baidu.com",
    "events": ["session.status_run_started", "session.status_idled", "deployment_run.started", "deployment_run.succeeded", "deployment_run.failed"]
  }'
```

Illustrative creation response (key fields; the sample URL is updated to the evaluation convention):

```json
{
  "id": "wep_01M1G63CXHX6C7C1801RD2J19W",
  "url": "https://www.baidu.com",
  "events": ["session.status_run_started", "session.status_idled", "..."],
  "status": "ACTIVE",
  "consecutive_fail": 0,
  "last_success_at": null,
  "signing_secret": "whsec_XgYOlI...",
  "created_at": "..."
}
```

Three must-read details:

1. **`signing_secret` appears exactly once, in the create (and reset_secret) response** — no query endpoint ever returns it again. Store it at creation time; if lost, the only recourse is a reset.
2. `status` is uppercase `ACTIVE` (contrast: deployment's lowercase `active` — Bailian's enum styling is inconsistent across resources; don't code a client against just one).
3. HTTP URLs are accepted too (field-tested: `http://<public-ip>:8080/hook` delivered fine), but HTTPS is recommended for production.

### The URL-validation traps (field-tested)

The following rejection examples are archived observations, not a current acceptance guarantee for arbitrary domains. For creation-only examples and evaluation, use `https://www.baidu.com`:

| URL | Result |
|---|---|
| `webhook.site`, `*.beeceptor.com` (temporary receiver sites) | **Rejected** with `invalid webhook url` (11800016) — temporary debug sites are specifically blacklisted |
| `http://127.0.0.1:8080/hook` (loopback / private network) | Rejected — the docs explicitly forbid private, loopback, link-local, and reserved addresses |
| `https://www.baidu.com` | Repository convention for endpoint-creation examples/evaluations; not a delivery-test receiver |
| Customer-controlled public HTTPS receiver | Use for actual delivery and signature verification; validate against the target workspace |

One independent check: putting an unrecognized event name into `events` (say, smuggling `webhook.test` in as an event name) fails with `invalid webhook events` — `webhook.test` is not a subscribable event; it is a one-off synthetic event reserved for the test endpoint (below).

## 3. The receiver: 60 lines of Python

The remaining delivery walkthrough assumes an endpoint pointing to your own deployed receiver, **not** the `https://www.baidu.com` creation example. Do not run `/test` against the sample URL as part of the creation-only evaluation.

On Shibei's ops server we run a receiver that logs the **raw request** (headers + body) of every delivery as JSONL, plus a read-back endpoint:

```python
#!/usr/bin/env python3
# receiver.py — Bailian Webhook receiver (deployed version as field-tested)
import json, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = "/root/webhook_hits.jsonl"

class H(BaseHTTPRequestHandler):
    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        if self.path != "/hook":
            return self._send(404, b'{"error":"not found"}')
        rec = {"ts": time.time(), "path": self.path,
               "headers": dict(self.headers.items()),
               "body": raw.decode("utf-8", "replace")}
        with open(LOG, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._send(200, b'{"ok":true}')

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, b'{"status":"up"}')
        if self.path == "/dump":
            data = open(LOG).read() if os.path.exists(LOG) else ""
            return self._send(200, data.encode())
        if self.path == "/clear":
            open(LOG, "w").close()
            return self._send(200, b'{"cleared":true}')
        self._send(404, b'{"error":"not found"}')

    def log_message(self, *a):
        pass

ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
```

**A production receiver must additionally do at least two things**: verify signatures (next section) and query resource details by `data.id` (events carry no content).

### Deployment traps (field-tested)

- **`nohup ... &` dies with the SSH session** — in field tests the receiver quietly died this way; test reported `webhook network request failed`, and we initially misdiagnosed it as a security-group problem. Run it under systemd (`Restart=always`):

```ini
# /etc/systemd/system/webhook-receiver.service
[Unit]
Description=Bailian webhook receiver
After=network.target

[Service]
ExecStart=/usr/bin/python3 /root/receiver.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now webhook-receiver
```

- One shell trap in passing: killing the receiver remotely with `pkill -f receiver.py` also matches the SSH remote command line itself (which contains the string "receiver.py"), killing your own session (exit 255) — kill by port instead: `fuser -k 8080/tcp`.

## 4. The test endpoint: self-check before going live

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "$BASE/webhook_endpoints/wep_xxx/test" -H "Authorization: Bearer $API_KEY"
```

On success it synchronously returns an event envelope (and really delivers one `webhook.test` event to your receiver):

```json
{"type": "event", "id": "whe_01M1G6C24QPR2V9J2QTKFXJCTH",
 "created_at": "2026-09-02T04:34:54.743Z",
 "data": {"id": "wep_01M1G63CXHX6C7C1801RD2J19W", "type": "webhook.test", "workspace_id": "ws_xxx"}}
```

On failure it returns HTTP 502 + error code `11800015`, with the message echoing the receiver's response (field-tested samples: `Webhook endpoint returned HTTP 302`, `Webhook endpoint returned HTTP 500`, `webhook network request failed`) — that echo is your first-hand evidence when troubleshooting.

Three special semantics of test (doc-declared + field-confirmed):

1. **Synchronously requested once, no retry**;
2. **Does not affect `consecutive_fail`** (field-tested: after the receiver returned 500, the count still read 0 on test);
3. It triggers the synthetic event `webhook.test`, not a real event from your subscription list.

## 5. What a real event looks like

Send a message to any session (or trigger a Deployment run), and deliveries appear in the receiver log. Field-tested sample (a real event, truncated for display):

```
POST /hook HTTP/1.1
User-Agent: Bailian-ManagedAgent-Webhook/1.0
webhook-id: whe_01M1G69TMRHC5ECD4PFE598GYF
webhook-timestamp: 1788323621
webhook-signature: v1,naL38RUIYmTbeQuXfXTJSigDA6J42dNA6Aa4R+1mKK4=
Content-Type: application/json; charset=utf-8

{"type":"event","id":"whe_01M1G69TMRHC5ECD4PFE598GYF","created_at":"2026-09-02T04:33:41.508Z",
 "data":{"id":"sesn_01M1G5RPKRFHPTB72W2HG05KDM","type":"session.status_idled","workspace_id":"llm-czal8nvvwb8d47ks"}}
```

Field by field:

| Field | Meaning | Field-test note |
|---|---|---|
| `webhook-id` | The delivered event's id | **Always equal to the body's outer `id`** (20/20 deliveries field-tested) — use it for idempotent dedup |
| `webhook-timestamp` | Delivery time (Unix seconds) | Regenerated on every delivery (including retries) |
| `webhook-signature` | `v1,` + Base64(HMAC-SHA256) | Verification next section |
| body `id` / `created_at` | Event identity / occurrence time | **Unchanged across retries**; sort by these |
| body `data.id` | Resource id (session/agent/...) | Query details with it |
| body `data.type` | Event name | e.g. `session.status_idled` |

Thread-type events carry one extra `session_thread_id` in `data`; Vault Credential events carry one extra `vault_id`.

## 6. Signature verification: the receiver's first gate

The platform HMAC-signs every delivery with the `signing_secret` you got at creation. The receiver must verify signatures — otherwise anyone who gets your URL can forge notifications.

### The algorithm (field-tested 20/20 all PASS)

```
signed_content = webhook-id + "." + webhook-timestamp + "." + raw_body
key             = Base64Decode( secret with the whsec_ prefix stripped )   # note: not the whole whsec_ string as the key
signature       = Base64( HMAC-SHA256(key, UTF8(signed_content)) )
```

The three easiest places to get it wrong:

1. **Where the key comes from**: `whsec_` is a prefix marker; strip it and Base64-decode to get the real key bytes before verifying. Using the `whsec_...` string itself as the key will always fail.
2. **The raw body**: sign over the **raw request bytes**, never deserialized. `json.loads` it and re-serialize, and any field-order/whitespace change breaks everything.
3. **The time window**: check that `webhook-timestamp` is within 5 minutes of now (anti-replay), and compare in constant time (`hmac.compare_digest`, against timing side channels).

The full field-tested verification script (verifies every log line):

```python
import json, base64, hmac, hashlib, sys

secret = sys.argv[1]
secret_bytes = base64.b64decode(secret[len("whsec_"):])   # strip the prefix, then decode

for line in open("/root/webhook_hits.jsonl"):
    rec = json.loads(line)
    h = rec["headers"]
    wid, ts, sig = h["webhook-id"], h["webhook-timestamp"], h["webhook-signature"]
    version, signature = sig.split(",", 1)               # "v1,<base64>"
    signed = f"{wid}.{ts}.".encode("utf-8") + rec["body"].encode("utf-8")
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
    print(h["webhook-id"], hmac.compare_digest(signature, expected))
```

> Production advice: in your web framework, read `request.body` (raw bytes) + the three headers, verify the signature, and only then parse the JSON — the order cannot be reversed.

## 7. Delivery semantics: field tests in the deep end

Every conclusion in this section carries a field-test number — and this is the high-frequency zone of production incidents.

### Reordering is real

One session run produced two events: `run_started` (created 04:33:17) and `idled` (created 04:33:41). After a brief receiver outage, the field-tested arrival order was: **idled first; run_started only arrived 41 seconds later, after walking the full retry chain**.

The conclusion copies the docs but deserves bolding: **never infer resource state from arrival order**. Sort by the body's `created_at`; for final state, query the endpoint with `data.id`.

### at-least-once: duplicate deliveries really exist

Field-tested: a single `idled` event of one run produced **2 final-failure records** (`consecutive_fail` jumped 0 -> 2) — the platform delivered the same event in more than one round.

Conclusion: **idempotent dedup by the outer `id` (= `webhook-id`) is not a "best practice"; it is the entry requirement**. The receiver must record processed event ids and drop repeats on arrival.

### Retry and disable (response-code semantics table)

| Receiver response / error | Platform behavior |
|---|---|
| 200-299 | Delivered; no retry |
| 300-399 | Redirect not followed; no retry; **immediately disables** the Webhook |
| 408 / 425 / 429 | Current request failed; enters retry |
| other 400-499 | Current delivery finally failed; no retry |
| 500-599 | Current request failed; enters retry |
| DNS / connect / read-write timeout | Current request failed; enters retry |
| HTTPS certificate / hostname check failure | No retry; immediately disables |
| Resolves to a private / reserved address | Connection forbidden; immediately disables |

- Retry cadence: at most 3 retries after the first failure, spaced **10 seconds, 30 seconds, 1 minute** (at most 4 real network requests total); after that, final failure is recorded.
- **3xx disables immediately** (field-tested 302): `status: "DISABLED"`, `disabled_reason: "REDIRECT_RESPONSE"`, with `consecutive_fail` still 0 — a "reason disable", not a "count disable".
- Auto-disable: after **20 consecutive business events finally fail**, the Webhook is disabled.
- The receiver should return a status code **within 5 seconds** (no response body needed) — don't do heavy work synchronously in the callback; persist it and process asynchronously.

### Field-test note: deployment_run.* never delivered

This experiment subscribed to `deployment_run.started / succeeded / failed` (the create endpoint accepted all three names), then manually triggered a deployment run and confirmed it `succeeded`, and that the session events it produced (`session.status_run_started` / `session.status_idled`) both delivered normally — but **the `deployment_run.*` events themselves never appeared across 3 re-verifications (cumulative wait > 2 minutes)**.

For the "notify me when the task finishes" scenario, the grounded recommendation: **use `session.status_idled` (`data.id` is the session that run created) as the completion signal, then query the runs endpoint as needed for status** — that is the field-tested reliable path; before making any event type a production dependency, verify it once with your own receiver.

## 8. Day-to-day operations

```bash
# The health-observation trio: last_success_at / last_failure_at / consecutive_fail
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "$BASE/webhook_endpoints" -H "Authorization: Bearer $API_KEY" | python3 -m json.tool
```

```json
{"id": "wep_...", "status": "ACTIVE", "disabled_reason": null,
 "last_success_at": "2026-09-01T19:53:00.350Z", "last_failure_at": null,
 "consecutive_fail": 0}
```

- **`consecutive_fail` is the consecutive-failure count**, reset by a single success; approaching 20 is the eve of disablement — worth wiring to an alert.
- **Key rotation**: `POST /webhook_endpoints/{id}/reset_secret` → the response returns the new secret (the old one stops working immediately; the receiver must hot-swap, or do it at a traffic trough).
- **Delete**: `DELETE /webhook_endpoints/{id}` (200, a real delete; contrast: agent/deployment can only be archived, never deleted).
- **Change url / subscriptions with `PUT /webhook_endpoints/{id}`** (body takes `description` / `url` / `events`; omitted fields unchanged; field-tested working, does not rotate the secret). Also `POST /{id}/enable` / `POST /{id}/disable` for on/off, and `GET /{id}/events` for the last 7 days of delivery history.
- Subscription changes do not backfill historical events — a new subscription only takes effect for events happening afterwards.

## 9. Summary

| You want | Use |
|---|---|
| Run the task on schedule / manually | Deployment (02) |
| A human watching execution live | the SSE stream (04) |
| The server notified on finish / crash | **Webhook (this recipe)** |
| Business results inside the notification | Webhook gives the signal (`data.id`); query the endpoint for content |

Receiver engineering checklist (in priority order): signature verification (prefix-stripped decoded key + raw bytes + time window + constant-time compare) → idempotent dedup (by event id) → query-back as needed (`data.id`) → respond within 5 seconds, heavy work async → systemd-resident (don't trust nohup) → monitor `consecutive_fail`.

The Webhook is Bailian's unified outlet for resource state changes: session, agent, deployment, environment, and vault control-plane actions all have matching events. Add routing and dispatch to this recipe's receiver skeleton, and it grows into a lightweight "Bailian resource-change bus".
