# 08 · Advanced: Vault Secret Injection and the Egress Gateway

> Execution safety: legacy shell examples below illustrate wire fields. When using real credentials, construct and send JSON in-process from a secret store/environment; do not interpolate secrets into command arguments, print request bodies, enable shell tracing, or use a receiver that echoes credential-bearing headers. Verify only that an allowlisted service authenticates successfully. A sandbox check should return a boolean placeholder check, never raw `printenv` output. See [CLI/API routing](../workflows/cli-api-routing.md).


> This recipe covers the **secret-safety chain** of Bailian Managed Agents: the Vault secret store's placeholder injection, the `allowed_hosts` egress allowlist, the egress gateway's replacement of matching placeholders in all HTTP request headers, and the selection layering between session environment variables (`environment_variables`) and the Vault.
> The original REST field tests ran on **2026-09-03** in Bailian cn-beijing. Header replacement scope was updated on **2026-11-02** and rechecked on **2026-11-10** against the [current official credential documentation](https://docs.bailian.console.aliyun.com/zh/model-studio/managed-agents-credential). The local-signing guidance below records the user's **2026-11-10** clarification; no new cloud test was run for these updates.
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

The diagram uses `Authorization` as an example. `X-API-Key` and other request headers support the same placeholder replacement.

### Current gateway replacement scope (2026-11-02)

| Location or condition | Behavior |
| --- | --- |
| HTTP request headers | Matching credential placeholders are replaced in **all headers**, including `Authorization`, `X-API-Key`, and custom headers, when the destination matches the credential's `allowed_hosts` |
| Request body or query parameters | Placeholders remain unchanged |
| Destination outside `allowed_hosts` | Header placeholders remain unchanged; the allowlist controls credential substitution, not general network access |

Read the credential by its configured environment-variable name and use that value in the header required by the target service. Do not construct placeholder strings manually.

### Archived gateway observations (2026-09-03, cn-beijing)

These observations preserve the original test's scope. Its Authorization-only result is superseded by the current scope above. Host-only selection and same-host ambiguity have not been retested and must not be presented as current rules or used to require one credential per host. The TLS observations are also specific to the tested environment.

| Behavior | Archived result |
| --- | --- |
| Which header was swapped | In that test only `Authorization` was substituted; other header placeholders passed through. **Superseded by the 2026-11-02 scope update** |
| How the credential to swap is located | **By matching the request host against `allowed_hosts`**, not by parsing the placeholder variable name — sending a garbage `BMA_SECRET_PLACEHOLDER_NOTEXIST` to an allowlisted host still gets swapped to that host's credential's real value |
| Multiple credentials for one host | In that test one credential was picked ambiguously; not a current configuration recommendation |
| Requests to non-allowlisted hosts | The request passed through with its header placeholder unchanged |
| Gateway interception method | **Transparent MITM**: no proxy environment variables inside the sandbox; outbound HTTPS is intercepted at the network layer (the TLS handshake receives the gateway's self-signed certificate) |
| Gateway certificate | Archived observation: one tested environment lacked a trusted gateway CA. Verify current workspace behavior and configure trust; see Step 5 |
| Interception scope | **All sessions** (ordinary sessions without a Vault also egress through the gateway; field-tested, strict TLS fails equally) |

### Choosing between the two injection paths

| | Session environment variables `environment_variables` | Vault secrets |
| --- | --- | --- |
| How values are passed | Plaintext key-value pairs at session creation; echoed verbatim in the create response | Credentials pre-stored in the Vault; sessions/deployments carry `vault_ids` |
| `os.environ` inside the sandbox | **Real value** | **Placeholder** `BMA_SECRET_PLACEHOLDER_<variable name>` |
| Where the real value appears | Inside the sandbox process (and the event stream, if the agent prints it) | Only the credential store (encrypted) + the instant of the gateway swap |
| Authentication placement | Values can be used directly by code, including local signing/HMAC | A matching placeholder must reach an HTTP request header unchanged; request-body/query placeholders and locally derived signatures are not substituted |
| Fits | **Non-sensitive config**, or a deliberate compatibility choice when a verified SDK/CLI needs the real secret inside the process | **Secrets passed directly in request headers**: API Keys and bearer tokens that do not require local cryptographic derivation |
| Deployment support | No (passed and silently ignored, field-tested) | Yes — `vault_ids` wires at the deployment level |

Choose by **how authentication uses the secret**, then by the acceptable exposure. Prefer Vault for direct header credentials; a sensitive key needed for local computation does not become compatible just by storing it in Vault. The archived Deployment test did not support `environment_variables`; do not assume that binding a Vault makes a signing SDK work in a scheduled run. Verify current support or have the application create the Session with the required inputs.

### SDK/CLI local signing and HMAC (user clarification, 2026-11-10)

Some SDKs/CLIs use a secret to calculate an HMAC or signature **before** sending the HTTP request. If they read a Vault placeholder, they calculate the signature with the placeholder bytes. The gateway replaces matching header placeholders; it does not recalculate a signature from the original secret. Even a signature carried in `Authorization` remains wrong. Adding `allowed_hosts` or changing the header name cannot repair that computation. This is the user's clarification and an implication of the documented replacement mechanism, not a new live test or evidence that a particular service failed this way.

Check the client implementation or its authentication contract first:

- **Raw API key / bearer token placed directly in a header:** keep Vault and the intended destination allowlist.
- **Local HMAC/signature, or credentials required in a body/query:** for a Session-scoped compatibility solution, supply the necessary real values through `environment_variables` when creating the Session, within the user's authorized resource and credential scope. Where secrets must remain outside the sandbox, use an already available trusted signing service instead; do not claim the placeholder route supports local signing.
- **Authentication mechanism unknown, or no authentication failure evidence:** investigate before proposing a credential-path change. A tool's use of an SDK/CLI alone does not prove it signs locally, and a generic timeout does not prove a signature error.

Plaintext environment injection is **not equivalent to Vault isolation**. Sandbox code can read the real value; Session create/GET responses can contain it, and printing it can expose it to events or model context. When preparing this option:

1. Construct the creation request inside the application process from its secret store or existing protected environment. Do not put secret values in the prompt, shell command arguments, source files, `agents.yaml`, experiment manifests or the repository. Instructions to the Agent name only the environment variables.
2. Handle create/GET responses inside that process and emit only allowlisted metadata such as Session ID/status. Do not dump `environment_variables`, request/response bodies, SDK debug output or exception payloads into logs or diagnosis reports. The platform's response field still exists; application-side omission is not server-side secrecy.
3. Pass the real value to the SDK in memory, or to the CLI through its supported environment input rather than command arguments. Avoid environment/config dumps and persisted credential files. Prefer appropriately scoped, short-lived credentials when available.
4. Verify a read-only authenticated operation against the intended service and report only its result/error code. Do not print the secret, signature material or credential-bearing request headers. Keep the original Vault-backed setup for unrelated tools.

## Prerequisites

- A Bailian workspace and its ID, plus one DashScope API Key;
- An Agent with the bash tool (bash enabled per tool in the builtin toolkit's `configs[]`; see the Agent-creation steps in 01 / 02);
- A customer-controlled service that verifies authentication and returns only success/failure. Never send a real secret to a public echo service or return credential-bearing headers to the Agent.

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

Use an authenticated, read-only endpoint on the service in `allowed_hosts`. Have it return an authentication success/failure indicator, never received credential-bearing headers. In a synthetic smoke test, use a fake credential and assert only the boolean placeholder prefix in the sandbox; this tests injection but **does not prove egress substitution**.

For a service using `X-API-Key`, code running inside the session can use:

```python
import os
import requests

token = os.environ["MY_API_KEY"]  # The sandbox receives a placeholder.
response = requests.get(
    "https://api.example.com/v1/data",  # Use the intended allowlisted service.
    headers={"X-API-Key": token},
    timeout=30,
)
response.raise_for_status()
print(response.status_code)  # Do not print headers or a credential-echo response.
```

If the service uses bearer authentication, use `headers={"Authorization": f"Bearer {token}"}`. Both header forms are in scope; putting `token` into a JSON body or query parameter does not trigger substitution.

The 2026-09 archived experiment used a **dummy** value and an echo service to observe substitution. It is historical evidence, not a reusable test procedure with a real credential. Returning echoed headers would copy the substituted secret into tool output, event history and model context, defeating the purpose of the Vault.

### TLS verification

An archived workspace showed an untrusted egress-gateway certificate. Do not turn `curl -k` / `verify=False` into a default integration recipe. Obtain the supported gateway CA and configure the trust store, or diagnose the target workspace's certificate chain with the platform. A failure in one archived environment is not proof that every current session needs TLS verification disabled.

## Step 6 · Session environment variables: config and local-signing compatibility

Non-sensitive config goes straight into **session creation**, plaintext all the way to the sandbox. The shell example below contains only non-sensitive values; for signing credentials use the in-process handling rules above, not this shell-body pattern:

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
- Both the create response and `GET /sessions/{id}` echo the field **verbatim** (a sibling of `metadata`) — it is visible to identities with session-read permission. Use non-sensitive values by default; the local-signing branch deliberately accepts this additional exposure and requires response/log filtering;
- **Deployment limitation in this archived test**: `POST /deployments` with `environment_variables` did not error but was silently ignored; the sessions generated by triggers lacked these variables. Verify the current contract before using it. Vault remains suitable for compatible header authentication; for local signing, consider application-controlled Session creation rather than assuming `vault_ids` supplies real signing keys.

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
| The receiving service says it still got the placeholder | The destination does not match `allowed_hosts` (including a redirect outside it), the placeholder is in a request body/query parameter, or the code used the wrong credential variable | Verify the intended destination and allowlist, then read the configured credential variable and put its value in the header the service requires; `X-API-Key` and custom headers are supported |
| A signing SDK/CLI reports a signature mismatch while reading a Vault placeholder | Possible local HMAC/signature computation over placeholder bytes; confirm with client implementation and actual error evidence | For confirmed local signing, use the scoped plaintext Session environment path above or a trusted signer; moving the derived signature to another header does not fix it |
| Sessions triggered by a Deployment lack `environment_variables` | Archived test: Deployments silently ignored that parameter; verify current support | Use `vault_ids` for compatible header authentication; for local signing, have the application create the Session with the necessary environment values, then send messages |
| Want to verify whether the secret leaked into the event stream | Only placeholders are printed inside the sandbox | Searching the event stream for the real value should yield 0 hits; searching `BMA_SECRET_PLACEHOLDER` shows the placeholders |

## Related

- The full productionization chain (MCP + Vault + Deployment + HITL) → [02-production-four-building-blocks.md](02-production-four-building-blocks.md)
- Credential-injection selection table and the Session request body → [../integration/api-endpoints.md](../integration/api-endpoints.md)
- Vault concepts and resource relationships → [../product/concepts.md](../product/concepts.md)
- Vault events on the Webhook side → [06-webhook-event-notifications.md](06-webhook-event-notifications.md)
