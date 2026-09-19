# 08 · Advanced: Vault Secret Injection and the Egress Gateway

> Execution safety: legacy shell examples below illustrate wire fields. When using real credentials, construct and send JSON in-process from a secret store/environment; do not interpolate secrets into command arguments, print request bodies, enable shell tracing, or use a receiver that echoes Authorization. Verify only that an allowlisted service authenticates successfully. A sandbox check should return a boolean placeholder check, never raw `printenv` output. See [CLI/API routing](../workflows/cli-api-routing.md).


> This recipe covers the **secret-safety chain** of Bailian Managed Agents: the Vault secret store's placeholder injection, the `allowed_hosts` egress allowlist, the egress gateway's Authorization-header swap, and the selection layering between session environment variables (`environment_variables`) and the Vault.
> All key conclusions were verified end to end via REST field tests (**2026-09-03**, Bailian cn-beijing region).
>
> Warning: **2026-09 breaking change**: Vault credentials moved from "plaintext injection into sandbox environment variables" to "**placeholder injection + egress-gateway swap**".
> If you wrote verification steps per the old docs — "after credential injection, `printenv` reads the real value" — **that behavior no longer exists**; see Step 4 for the verification method.

## Scenario: who needs this recipe

- Your agent must call external APIs at runtime (your own services, third-party SaaS) and carry an API Key / Token;
- You do not want the secret in plaintext anywhere in: your application code, the Agent config and its version history, the sandbox process, the model context, or the event-stream logs;
- You are running a security-compliance review and must explain clearly "where in the chain the secret exists, and in what form".

If you need no secrets and only want to pass **non-sensitive config** (API base URLs, log levels, feature flags) → just use
[session environment variables `environment_variables`](#choosing-between-the-two-injection-paths); no need to read the whole recipe.

## The model: placeholder injection

Since 2026-09, the Vault credential security model is "**the secret never enters the sandbox; it is swapped at the gateway when used**":

```
(1) Configure (once)            (2) Sandbox reads             (3) Sandbox sends             (4) Egress gateway decides
+------------------+    +-----------------------+    +----------------------+    +-------------------------+
| Vault credential |    | token = os.environ    |    | GET /v1/data         |    | hits allowed_hosts?     |
|  name: MY_API_KEY | -> |   ["MY_API_KEY"]      | -> | Authorization: Bearer| -> |  yes -> swap in the real |
|  value: sk-...(enc)|   | # what you get is the |    |   BMA_SECRET_PLACE-  |    |        value and forward |
|  allowed_hosts:  |    |   placeholder:         |    |   HOLDER_MY_API_KEY  |    |  no  -> placeholder     |
|  api.example.com |    |   BMA_SECRET_PLACE-    |    | Host: api.example.com|    |       passes through    |
|                  |    |   HOLDER_MY_API_KEY    |    |                      |    |  (real secret not leaked)|
+------------------+    +-----------------------+    +----------------------+    +-------------------------+
```

The real secret exists in only two places: **the credential store (encrypted at rest)** and **the instant the egress gateway swaps it in for an allowlisted host**; every other observable position along the chain
(sandbox process, event stream, model context) sees only the placeholder. Even if the agent is prompt-injected into sending the credential to a malicious domain,
the gateway will not swap — the recipient gets nothing but a meaningless placeholder.

### Gateway behavior boundaries confirmed by field tests

| Behavior | Field-tested result |
| --- | --- |
| Which header gets swapped | **Only `Authorization`**. Placeholders in other headers of the same request (`X-Api-Key`, `Api-Key`, ...) **pass through unchanged** |
| How the credential to swap is located | **By matching the request host against `allowed_hosts`**, not by parsing the placeholder variable name — sending a garbage `BMA_SECRET_PLACEHOLDER_NOTEXIST` to an allowlisted host still gets swapped to that host's credential's real value |
| Multiple credentials for one host | The swap is ambiguous (field-tested: one of them was picked). **Recommend at most one credential per host** |
| Requests to non-allowlisted hosts | **Not blocked** (the network passes as usual); the Authorization header just keeps the placeholder — `allowed_hosts` governs "who the secret may be sent to", not "whether the network may go out" |
| Gateway interception method | **Transparent MITM**: no proxy environment variables inside the sandbox; outbound HTTPS is intercepted at the network layer (the TLS handshake receives the gateway's self-signed certificate) |
| Gateway certificate | Archived observation: one tested environment lacked a trusted gateway CA. Verify current workspace behavior and configure trust; see Step 5 |
| Interception scope | **All sessions** (ordinary sessions without a Vault also egress through the gateway; field-tested, strict TLS fails equally) |

### Choosing between the two injection paths

| | Session environment variables `environment_variables` | Vault secrets |
| --- | --- | --- |
| How values are passed | Plaintext key-value pairs at session creation; echoed verbatim in the create response | Credentials pre-stored in the Vault; sessions/deployments carry `vault_ids` |
| `os.environ` inside the sandbox | **Real value** | **Placeholder** `BMA_SECRET_PLACEHOLDER_<variable name>` |
| Where the real value appears | Inside the sandbox process (and the event stream, if the agent prints it) | Only the credential store (encrypted) + the instant of the gateway swap |
| Fits | **Non-sensitive config**: API base URLs, log levels, flags, tenant IDs | **Highly sensitive secrets**: API Keys, Tokens, AccessKeys |
| Deployment support | No (passed and silently ignored, field-tested) | Yes — `vault_ids` wires at the deployment level |

Rule of thumb: **what doesn't need maximum safety goes through environment variables; what does goes into the Vault**. Scheduled / unattended chains (Deployments) currently have only the Vault route.

## Prerequisites

- A Bailian workspace and its ID, plus one DashScope API Key;
- An Agent with the bash tool (bash enabled per tool in the builtin toolkit's `configs[]`; see the Agent-creation steps in 01 / 02);
- A customer-controlled service that verifies authentication and returns only success/failure. Never send a real secret to a public echo service or return authorization headers to the Agent.

Agreed environment variables:

```bash
export BASE="https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
export API_KEY="<your DashScope API Key>"
export AGENT_ID="agent_xxx"          # the agent with the bash tool
export MY_API_KEY="sk-DUMMY_KEY_FOR_SMOKE_TEST"   # a fake value for the demo
```

## Step 1 · Create the vault

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/vaults" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Production secret vault",
    "metadata": { "team": "operations" }
  }'
```

The response `id` is shaped like `vlt_01M1KPMXH45N5QQ00PQX8H9T9Q`:

```bash
export VAULT_ID="vlt_xxx"
```

## Step 2 · Create the secret (credential): `allowed_hosts` required

Credentials hang under a vault; the endpoint is **nested**: `/vaults/{vault_id}/credentials` (there is no top-level `/credentials` — 404).

**New structure**: `allowed_hosts` must be written **inside** `auth.networking`, and it is **required**:

```python
import os
import httpx

# Construct the body in memory; no secret-bearing shell arguments, files or response dumps.
with httpx.Client(headers={
    "Authorization": "Bearer " + os.environ["DASHSCOPE_API_KEY"],
    "User-Agent": os.environ["BAILIAN_MANAGED_AGENT_SKILL_UA"],
}, timeout=30) as http:
    response = http.post(os.environ["CMA_BASE"] + "/vaults/" + os.environ["VAULT_ID"] + "/credentials", json={
        "display_name": "Business API credential",
        "auth": {"type": "environment_variable", "secret_name": "MY_API_KEY",
                 "secret_value": os.environ["MY_API_KEY"],
                 "networking": {"allowed_hosts": [os.environ["BUSINESS_API_HOST"]]}},
    })
    response.raise_for_status()
    print({"credential_id": response.json()["id"]})
```

Key points:

- `secret_name`: the environment variable name; inside the sandbox, `os.environ` under this name yields the **placeholder**.
- `secret_value`: the real secret. **Write-only, never echoed** — on GET, `auth` contains only `secret_name` / `type` / `networking`.
- `networking.allowed_hosts`: the **egress allowlist, required**. Wildcards supported (`*.example.com`). **This is "declaring at config time, once, which domains the secret may travel to"**.
- `networking.type`: optional; field-tested, passing `limited` is also accepted, but the behavior is decided by `allowed_hosts`.
- The response `id` carries the `vcrd_` prefix (not `cred_`).

Two field-tested traps (2026-09-03):

> **Omitting `allowed_hosts` -> 409 `CREDENTIAL_AUTH_NETWORKING_ERROR` "egress network address cannot be empty"**.
> Old structures (only `networking: {type: "unrestricted"}`, top-level `allowed_hosts`, or no networking at all) are all rejected — that is the error surface of this breaking change.

> **`auth.type` still supports only `environment_variable`** (field-tested: `secret` / `static_bearer` / `mcp_oauth` all return 409 `CREDENTIAL_AUTH_TYPE_ERROR`).

```bash
export CRED_ID="vcrd_xxx"
```

## Step 3 · Create a session with the vault attached

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "'"$AGENT_ID"'",
    "title": "Secret-injection verification",
    "vault_ids": [ "'"$VAULT_ID"'" ]
  }'
```

The wiring inside a Deployment is exactly the same (`vault_ids` sits on the deployment; every session created by a trigger carries it automatically) —
see [02-production-four-building-blocks.md](02-production-four-building-blocks.md) Step 5.

## Step 4 · Verification one: only the placeholder inside the sandbox

Send a message asking for a boolean prefix check, without printing the environment variable:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/events" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      { "type": "message", "role": "user",
        "content": [ { "type": "text", "text": "Check whether MY_API_KEY starts with BMA_SECRET_PLACEHOLDER_ and report only true or false; never print its value" } ] }
    ]
  }'
```

2026-09-18 smoke-test result: the synthetic `AUDIT_SYNTHETIC_TOKEN` prefix check returned `True`; the value was not printed.

**Note: this is the watershed versus the old behavior** — before 2026-09 this would have printed the real value; now there is **only the placeholder**.
So "verifying that secret injection succeeded" can no longer rely on `printenv` reading the real value; the correct approach is Step 5's end-to-end request verification.

## Step 5 · Verify the credential against its intended service

Use an authenticated, read-only endpoint on the service in `allowed_hosts`. Have it return an authentication success/failure indicator, never the received Authorization header. In a synthetic smoke test, use a fake credential and assert only the boolean placeholder prefix in the sandbox; this tests injection but **does not prove egress substitution**.

The 2026-09 archived experiment used a **dummy** value and an echo service to observe substitution. It is historical evidence, not a reusable test procedure with a real credential. Returning echoed headers would copy the substituted secret into tool output, event history and model context, defeating the purpose of the Vault.

### TLS verification

An archived workspace showed an untrusted egress-gateway certificate. Do not turn `curl -k` / `verify=False` into a default integration recipe. Obtain the supported gateway CA and configure the trust store, or diagnose the target workspace's certificate chain with the platform. A failure in one archived environment is not proof that every current session needs TLS verification disabled.

## Step 6 · Session environment variables: the first choice for non-sensitive config

Config that needs no secret-grade protection goes straight into **session creation**, plaintext all the way to the sandbox:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "'"$AGENT_ID"'",
    "environment_id": "'"$ENV_ID"'",
    "title": "Customer inquiry #1234",
    "environment_variables": {
      "API_BASE_URL": "https://new.example.com",
      "LOG_LEVEL": "info"
    }
  }'
```

Field-tested behavior (2026-09-03):

- Inside the sandbox, `printenv API_BASE_URL` → `https://new.example.com` (the **real value**, directly usable by the agent's bash / python);
- Both the create response and `GET /sessions/{id}` echo the field **verbatim** (a sibling of `metadata`) — note this means it is visible to anyone with session-read permission; put only non-sensitive content there;
- **Deployments do not support it**: `POST /deployments` with `environment_variables` does not error but is silently ignored; the sessions generated by triggers lack these variables (field-tested). Injection on scheduled chains can only go through `vault_ids`.

When writing the agent's prompt, just reference the variable names directly, e.g.: "call the API at `$API_BASE_URL`, with log level per `$LOG_LEVEL`".

## Step 7 · Operations and cleanup

- Rotation: the Vault API offers no explicit rotation endpoint (to be verified); directly `POST .../credentials/{id}` to update `secret_value` is the current means (the update must carry the complete `auth` value).
- Cleanup order: **delete the credential (child) before the vault (parent)** — deleting a vault does not cascade-delete its credentials (orphaned data, field-tested); for the full lifecycle verbs see [02-production-four-building-blocks.md](02-production-four-building-blocks.md) Steps 8-9.
- On the Webhook side there are `vault.created / archived / deleted` and `vault_credential.created / archived / deleted` events usable for control-plane monitoring — see [06-webhook-event-notifications.md](06-webhook-event-notifications.md).

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| Creating a credential returns 409 `CREDENTIAL_AUTH_NETWORKING_ERROR` "egress network address cannot be empty" | `allowed_hosts` missing, or not nested inside `auth.networking` | Write the new structure: `"networking": {"allowed_hosts": ["api.example.com"]}` |
| `printenv` shows `BMA_SECRET_PLACEHOLDER_*`; suspected "injection failure" | That is the correct behavior of the new model | Verify with an end-to-end request (Step 5): the allowlisted host receiving the real value means injection succeeded |
| curl exits 60 in the sandbox / requests raises SSLError | Egress-gateway MITM; the certificate is not in the sandbox CA store | Configure the supported gateway CA/trust store; do not default to disabling verification |
| The receiving service says it still got the placeholder | (a) The target host is not in that credential's `allowed_hosts`; (b) the placeholder was put in a header other than Authorization (e.g. `X-Api-Key`, which the gateway does not swap); (c) multiple credentials configured for that host, ambiguous swap | (a) Add the target host to the allowlist; (b) put the credential in the `Authorization` header; (c) configure at most one credential per host |
| Sessions triggered by a Deployment lack `environment_variables` | Deployments do not support that parameter (silently ignored, field-tested) | Use `vault_ids` on scheduled chains; or have your application create the session first, then send messages |
| Want to verify whether the secret leaked into the event stream | Only placeholders are printed inside the sandbox | Searching the event stream for the real value should yield 0 hits; searching `BMA_SECRET_PLACEHOLDER` shows the placeholders |

## Related

- The full productionization chain (MCP + Vault + Deployment + HITL) → [02-production-four-building-blocks.md](02-production-four-building-blocks.md)
- Credential-injection selection table and the Session request body → [../integration/api-endpoints.md](../integration/api-endpoints.md)
- Vault concepts and resource relationships → [../product/concepts.md](../product/concepts.md)
- Vault events on the Webhook side → [06-webhook-event-notifications.md](06-webhook-event-notifications.md)
