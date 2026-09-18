# Tutorial 05: Preinstall Dependencies into the Sandbox (only what the base image lacks)

| Item | Value |
| --- | --- |
| **Goal** | Create an Environment with pip / apt / npm dependencies preinstalled, and verify the Agent can call them directly inside the sandbox |
| **Capabilities involved** | Environment / `config.packages` / `config.networking` / `scope` / builtin tool bash / base-image preinstall list |
| **Difficulty** | Advanced |
| **Prerequisites** | An API Key and workspace ID; one working Agent |
| **Estimated time** | 20-30 minutes (including 2-3 minutes waiting for packages to install) |
| **Source** | Official API docs (cloud-hosted Environment) + official Python SDK field tests |

## Scenario

The sandbox base image ships with more than you would expect: **a bare environment field-tested to already have pandas / numpy / openpyxl / ffmpeg**, plus about 190 pip packages (spacy, bokeh, beautifulsoup4, cryptography, ...) and the node / npm / ruby / gem / cargo / go / rg toolchains. So **check what the base image has first, and only configure what is missing** — dependencies are declared on the Environment, installed automatically at creation, and every session bound to it comes up ready to use.

Four key judgment points in this tutorial: **self-checks must have discriminating power** (verifying with a package the base image already has "succeeds" whether or not you declared it), **`config.type` is immutable after creation** (get it wrong and you must recreate), **updating packages is a full replacement with minutes-level propagation delay**, and **networking policy and scope are API-only — invisible in the console**.

## Final artifacts

One Environment with the declared dependencies installed (`env_xxx`) + one session verifying those dependencies work.

## Steps

### 1. Check the base image first, then write the list

The first step is not writing the dependency list — it is **spinning up a session to see what the base image already ships** (fastest: have the Agent run `pip3 list | wc -l && which node npm rg cargo go` with bash). Common data-analysis packages and ffmpeg are all in the base image and need no declaration; what actually needs configuring is what the base lacks — this tutorial uses `polars` as the example.

Declaring dependencies on the Environment is the official approach: they are installed automatically at creation, ready in every session bound to it. Do not rely on "installing on the fly inside a session" — ad-hoc installs are not reliably reproducible, and every session would reinstall them anyway.

Group the list by package manager. **The SDK supports six groups** (official docs list only apt / pip / npm); field-tested status:

| Group | Field-tested status | Notes |
| --- | --- | --- |
| `apt` | ✅ installs (field-tested: `sl` lands in `/usr/local/bin/`) | system-level binaries |
| `pip` | ✅ installs (field-tested: `polars` 1.44.1) | Python libraries |
| `npm` | ✅ installs (field-tested: `tsc` 7.0.2) | Node packages |
| `gem` | ✅ installs (field-tested: `bundler` 2.6.9; the base has only default 2.3.7, no command) | Ruby packages |
| `cargo` | ❌ **declared but never installed** (silently ignored, no error; `cargo install --list` is empty) | — |
| `go` | ❌ **declared but never installed** (silently ignored; both bare names and `@latest` tried) | — |

The last three appear only in the SDK's `Packages` definition and are absent from official docs; field testing shows gem works while cargo / go are currently decorative. **Do not route Rust / Go dependencies through this path** — there is no reliable preinstall channel today.

### 2. Create the Environment

```bash
export CMA_BASE="https://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"

ENV_ID=$(curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/environments" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "data-sandbox",
    "description": "Data-analysis sandbox: incremental dependencies on top of the base image",
    "config": {
      "type": "cloud",
      "packages": {
        "pip": ["polars"]
      },
      "networking": {"type": "unrestricted"}
    },
    "scope": "organization"
  }' | jq -r '.id')
echo "$ENV_ID"        # like env_xxx
```

The example deliberately picks `polars`, which the base lacks — **declare only the increments** (pandas / numpy / ffmpeg already in the base need no re-declaration), so the verification below actually discriminates.

Python SDK equivalent:

```python
client.environments.create(
    name="data-sandbox",
    config={"type": "cloud",
            "packages": {"pip": ["polars"]},
            "networking": {"type": "unrestricted"}},
)
```

Field essentials:

| Field | Mutable | Notes |
| --- | --- | --- |
| `config.type` | **No** | Currently only `cloud` (Bailian-managed). **Immutable after creation** |
| `config.packages` | Yes | Auto-installed by `apt` / `gem` / `pip` / `npm` group (`cargo` / `go` currently silently ignored, see step 1); updates use **full-replacement** semantics |
| `config.networking.type` | Yes | `unrestricted` allows all outbound access. **API-only — not shown in the console** |
| `scope` | Yes | Defaults to `organization`, usable by all workspace members. **API-only** |
| `metadata` | Yes | Custom key-value pairs; no effect on runtime behavior |

**Expected result**: an `env_xxx` comes back. Creation is **immediate** — the response carries no building / ready status field; package installation runs asynchronously (**within about 2 minutes**), so do not jump straight to step 3 to verify.
**How to verify**: `curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/environments/${ENV_ID}" -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq`

### 3. Verify the dependencies actually installed (do not skip)

Creation success ≠ dependency install success. A mistyped package name or a version absent from the index can leave a dependency missing — and you find out only when the Agent hits `ModuleNotFoundError` mid-task.

**Self-check with a package the base lacks** (that is exactly why the example chose polars — self-checking with pandas "succeeds" whether declared or not, which verifies nothing). Mind the order when consuming: the SSE stream only delivers events **after you connect**, so you must **connect the stream first, then send the message**:

```bash
# ① Create the session
SESSION_ID=$(curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"agent\":\"agent_xxx\",\"environment_id\":\"${ENV_ID}\",\"title\":\"Environment self-check\"}" | jq -r '.id')

# ② Connect the SSE stream in the background (the Agent's output arrives on this stream)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" -s -N --max-time 300 "${CMA_BASE}/sessions/${SESSION_ID}/events/stream" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" > stream.log &
STREAM_PID=$!
sleep 3

# ③ Then send the message (this POST's response is just a JSON receipt, not the stream)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions/${SESSION_ID}/events" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","type":"message","content":[{"type":"text",
       "text":"Run with bash and report the output verbatim: python -c \"import polars; print(polars.__version__)\""}]}]}'

# ④ Wrap up once session_status: idle is seen
kill $STREAM_PID
```

**Expected result**: `tool_call_output` carries the real version number (field-tested: `1.44.1`).
**How to verify**: seeing the version number means pass; seeing `ModuleNotFoundError` means it did not install — **wait two or three minutes first** (installation is asynchronous); if it still fails, go back to step 2 and check the package name. Missed events can be recovered via `GET /sessions/{id}/events`.

**Bake this self-check into your routine** — run it after every `packages` change; it is far cheaper than debugging dependency issues inside a business task.

### 4. About egress

`config.networking.type: unrestricted` allows all outbound access. Two things to note:

- **Settable only via the API** — the console does not show this config item. To open egress on a console-created environment, update it via the API
- Only the `unrestricted` value has been observed; **the egress allowlist granularity is not publicly documented**. When a customer asks for "specific domains only", state honestly that product-team confirmation is required — do not invent configuration

### 5. Reuse and reconfiguration

Environments are managed independently of Agents and **can be bound and reused by many sessions** — do not build one environment per Agent; build per dependency combination: one data-analysis environment, one audio/video environment, and you are covered.

Changing the configuration:

- Add/remove dependencies → `POST /environments/{id}` to update `config.packages`. Two traps: **the submitted list is a full replacement** (packages not listed get removed, not appended); an update returning 200 **does not mean it has taken effect** — there is a minutes-level propagation delay (field-tested: a session created 13 seconds after the update still saw the old packages; normal after 3 minutes), with no status to query and no error during the window — wait a few minutes after changing, then verify; existing old sessions are unaffected
- Change `config.type` → **cannot be changed** (field-tested: submitting another value is rejected outright); the only path is a new environment and switching the Agent / Deployment over
- No longer needed → `POST /environments/{id}/archive`. Archiving is **an immediate deactivation**: the environment disappears from the default listing (recoverable via `GET /environments?include_archived=true`), new binding sessions cannot be created, and **already-bound idle sessions can no longer receive new messages** (field-tested: sending a message returns 404 `not_found`; the official docs say "bound sessions remain usable" — go with the field test: do not archive while sessions you still need are bound)
- Truly wiping the config → `DELETE /environments/{id}`, a hard delete with no recovery (field-tested: 200, then GET 404 "environment not found")

**To keep the configuration, never delete; to deactivate, do not count on bound sessions still running after archiving.**

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| Agent reports `ModuleNotFoundError` | Package name mistyped or undeclared | Self-check per step 3; verify `config.packages` |
| `ffmpeg: command not found` | A system-level package was written into the `pip` group | Binaries go in `apt`, Python libraries in `pip` (note ffmpeg ships with the base image — usually no need to declare) |
| New sessions still see old packages after an update | Minutes-level propagation delay, no status to query | Wait a few minutes, then create a session to verify (field-tested: 13 seconds — no; 3 minutes — yes) |
| Cannot find the networking policy option in the console | `networking` is API-only | Update via `POST /environments/{id}` |
| Want to change `type` to something else | `config.type` is immutable after creation | Create a new environment; switch the Agent / Deployment `environment_id` |
| Bound sessions get 404 on new messages after archiving | Archiving deactivates immediately; bound sessions can no longer receive messages | Do not archive while sessions you still need are bound; let them finish first |
| Declared cargo / go packages never installed | These two groups are currently silently ignored | Route Rust / Go dependencies through another channel (e.g. have the Agent install with bash on the fly) |
| Customer asks how much CPU / memory / disk | **Not publicly documented** | State honestly that product-team confirmation is needed; **do not estimate** |
| Customer asks how long a single session can run | Same as above — not public | Same as above |

## Compliance note (must be stated in customer proposals)

The sandbox container is governed by Article 6 of the Alibaba Cloud Product Terms of Service: **the customer bears the consequences of software they install themselves and of its use** (the agreement's original context is pirated software; Bailian's official docs generalize the wording to "self-installed software"; the original agreement is at
[terms.aliyun.com](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud201802281451_77479.html)).
Flag this clause whenever a proposal involves preinstalling third-party software.

## Going further

- Mounting data files into sessions on this environment → [03-mount-files.md](03-mount-files.md)
- Scheduled tasks bound to this environment → [04-scheduled-deployment.md](04-scheduled-deployment.md)
- Full Environment fields and semantics → the Environment section of [../product/concepts.md](../product/concepts.md)
- Full request-body fields → [../integration/api-endpoints.md](../integration/api-endpoints.md)
- Declarative environment creation via CLI → [../workflows/provision.md](../workflows/provision.md)
