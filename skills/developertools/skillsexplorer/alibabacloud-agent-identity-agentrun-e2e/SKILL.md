---
name: alibabacloud-agent-identity-agentrun-e2e
description: >
  Stand up a working Alibaba Cloud agent that authenticates its end users and
  proves its permissions hold, then tear it back down. Use when someone wants
  to deploy an AgentRun-hosted agent governed by AgentIdentity, see for
  themselves that only signed-in users reach it, that each tool receives the
  credentials it needs without any secret in the code, and that authorization
  rules actually block what they should — or when they want to remove the
  resources such a trial created. Covers first-time setup on an empty account,
  re-verification after a change, and cleanup.
  也响应"AgentRun 端到端测试""AgentIdentity 全流程验证""AgentRun 部署 Agent"等中文请求。
license: Apache-2.0
compatibility: >
  Requires macOS or Linux (zsh/bash), Python >= 3.10, conda (miniforge or
  miniconda), Alibaba Cloud CLI (aliyun) >= 3.3.3 — older versions lack the
  plugin-mode commands this skill calls; upgrade with `brew upgrade aliyun-cli`
  or from https://github.com/aliyun/aliyun-cli/releases. Also needs an Alibaba
  Cloud account with AgentRun, AgentIdentity, RAM and OSS permissions (see
  references/ram-policies.md) and network access to Alibaba Cloud endpoints.
metadata:
  version: "1.0.0"
  layer: application
  category: deployment
  lifecycle: stable
  tags: "agentrun,agent-identity,end-to-end,deployment,testing"
---

# Alibaba Cloud AgentRun + AgentIdentity End-to-End Deployment & Test

Orchestrates the full e2e workflow: CLI credential setup → identity provider
registration → OAuth2 credential chain → console MCP registration → sample
build & Runtime deployment → inbound/WAT/Cedar verification → local-tool
credential injection → DingTalk MCP → cleanup.

The runtime code lives in the [agent-identity-dev-kit](https://github.com/aliyun/agent-identity-dev-kit)
repository under `agent_identity_python_samples/`. Users only need the public
kit repository and an Alibaba Cloud account; this skill orchestrates the rest.

## Execution Rules

1. Blocks marked `<!-- AGENT:AUTO -->` — execute directly in the terminal, no user confirmation needed.
2. Blocks marked `<!-- AGENT:WAIT:description -->` — STOP and wait for the user's response before proceeding.
3. Cloud credentials come from the aliyun CLI profile (never a secrets file, and never read or exported by any script). If the CLI is not configured, guide the user through `aliyun configure`; verify with `aliyun sts get-caller-identity` before any cloud call. Python SDKs resolve the same profile through the credential chain's `cli_profile` provider — never pass, print or export an AccessKey pair.
4. On command failure, stop and report the error (with logs) to the user. Do NOT retry automatically; retry only after the user confirms. Match errors against `references/troubleshooting.md` first.
5. Terminal sessions lose exported variables between calls. Durable state lives in files under the skill state directory; scripts re-read them on every run. All scripts source `scripts/lib/common.sh`.
6. Follow the phases in order; do NOT skip, merge, or simplify steps. Present each WAIT step to the user exactly as written.
7. Background services (nohup) are started and stopped INSIDE the scripts — never append `&` to a terminal call yourself.
8. Automate everything that can be automated — including cloning the kit repository and installing missing tools — and tell the user in one line what you did. Ask the user to act ONLY where their person is strictly required: entering secrets, console UI steps, and account-level decisions.
9. Environment variables in deployment templates are minimal: required variables only. Never add debug switches (e.g. AGENTRUN_SDK_DEBUG) or empty placeholders (e.g. OAUTH_SCOPES="").
10. MCP tool registration MUST go through the AgentRun console. The CreateTool API creates a tool whose data-plane route never activates (verified: identical payloads, API-created tool returns 500 missing X-AgentRun-Mcp-Tool-Arn and later vanishes; console-created works). Do not attempt API registration.
11. OAuth2 authorization links expire within minutes. Whenever a link is returned: (a) IMMEDIATELY open it in the user's browser yourself — run `open "<url>"` on macOS or `xdg-open "<url>"` on Linux — do not rely on the user noticing the chat message in time; (b) also print the link in the message as a fallback. Access tokens expire after 1 hour, so re-authorization prompts on later runs are expected — treat them as normal, not as failures.
12. Resource naming is the USER's decision. At every resource-creation step, either ask the user for the name (offer a suggested default) or, when the name is fixed by the sample code (e.g. the `test-provider-api-key` credential provider), state the required name and the reason explicitly. Never silently pick names. More generally: before each step, tell the user what it will create/change and why — the user must always know what is being done on their account.
13. Every message that starts, advances, blocks, or closes a phase follows the mandatory shape in "Output Format" below. Dropping the progress header or the two sections on such a message is a defect, even when the content is correct.
14. All aliyun CLI calls use plugin mode: kebab-case commands and flags (`aliyun sts get-caller-identity`, `aliyun ram attach-policy-to-role --policy-type ...`). Phase 1 enables `auto-plugin-install` and pre-installs the needed plugins; without that, a missing plugin makes the CLI prompt for confirmation and then abort on `failed to read user input: EOF`.
15. Every cloud call carries the skill's User-Agent (see "Observability" below). Do not strip it or issue raw calls that bypass it.

## Output Format

Every message that starts, advances, blocks, or closes a phase MUST use the
shape below. That is the hard requirement, and it covers the whole main path.

For a reply that merely reacts inside an already-running flow — a how-to
question, a failure report, a refusal — keep the same shape whenever the flow is
underway, so the user never loses their place. When such a question arrives in a
fresh session with no phase started yet, answering directly is acceptable;
announce the phase as soon as the workflow resumes.

**Self-check before sending any message: if it starts, advances, blocks, or
closes a phase, does it begin with `【进度：`? If not, rewrite it.**

The user-facing tokens below are Chinese by design: the workflow addresses a
Chinese-speaking operator, and these are literal output strings. Reproduce each
one exactly as written — never translate, localise or reword them.

| Literal token | Role in the message |
|---|---|
| `【进度：` | opens the mandatory progress header |
| `下一步：` | introduces the next concrete action inside the header |
| `受阻` | marks a blocked phase in the header |
| `本步骤说明` | heading of the first mandatory section |
| `需要您提供/操作` | heading of the second mandatory section |

```text
【进度：Phase <X.Y> | 下一步：<the next concrete action>】

**本步骤说明**

<One or two concise, professional sentences: what this step does and why.
Explain any term in plain language on first use. Never write meta-labels such
as `素人版` or internal walkthrough vocabulary.>

**需要您提供/操作**

1. <Exactly what is needed from the user.>
```

How to fill the header when the message is not a plain step forward:

| Situation | Header | First section holds | Second section holds |
|---|---|---|---|
| Normal step | `Phase X.Y \| 下一步：…` | what this step does, why | what you need from the user |
| Command failed / blocked | `Phase X.Y 受阻 \| 下一步：<what unblocks it>` | root cause + evidence | the options for the user |
| Explaining or answering mid-flow | `Phase X.Y \| 下一步：<how the flow resumes>` | the answer itself | `无，我继续执行下一步。` if nothing is needed |
| Refusing an unsafe request | `Phase X.Y \| 下一步：<the safe path>` | the refusal and why | what the user should do instead |
| Phase not yet determined | `Phase 0 \| 下一步：…` | — | — |

Single exemption: the user explicitly tells you NOT to start or run anything and
only wants a conceptual answer. Then answer plainly, use no header, and begin no
phase.

Whatever the shape, two content rules always hold: never claim a human-only or
external action has completed when it has not, and never ask the user to hand
you a credential.

Keep all output formal, concise, and readable. No casual asides, no internal
jargon, no exposing skill-machinery labels to the user.

## Observability

Every cloud call this skill makes is attributable to the skill and to a single
run, so an operator can find this skill's calls in ActionTrail.

**Session id.** One id per run, generated by `skill_session_id()` in
`scripts/lib/common.sh` and cached at `<state-dir>/session_id` so every script
of the same run reuses it. Resolution order:

1. `SKILL_SESSION_ID` from the environment, when the caller supplies one;
2. the cached id in the state dir;
3. a freshly generated `uuidgen` value (lower-cased), falling back to
   `<UTC-timestamp>-<pid>` where `uuidgen` is unavailable.

`E2E_FRESH=1` clears the cached id along with the rest of the run state, so a
from-zero run gets a new session.

**User-Agent template.** Built by `ua_string()`:

```
AlibabaCloud-Agent-Skills/<skill-name>/<session-id>
```

For this skill that resolves to, for example:

```
AlibabaCloud-Agent-Skills/alibabacloud-agent-identity-agentrun-e2e/9f1c...
```

**How it is applied.**

| Call path | Mechanism |
|---|---|
| aliyun CLI | `--user-agent "$(ua_string)"` on every invocation |
| Tea SDKs (AgentIdentity, IMS) | `user_agent=` on `open_api_models.Config` |
| oss2 | `app_name=OSS_UA` on `oss2.Bucket` / `oss2.Service` |

`py_sdk` exports `SKILL_SESSION_ID` and `SKILL_UA` before running Python, which
is where the SDK call sites read the value from.

## Architecture & Resource Overview

```
End user (OIDC ID Token)
  → AgentRun data-plane gateway (validates the ID Token, injects
    X-Workload-Access-Token)
  → Runtime (sample main.py: reads the WAT and forwards it on MCP calls;
    also seeds the Agent Identity SDK context for local tools)
  → AgentRun-hosted MCP tool (Hook: Cedar authorization + OAuth2
    credential injection)
  → Upstream MCP server
```

The sample (`agentrun-e2e_sample`) demonstrates the manual WAT pass-through
pattern: it extracts `X-Workload-Access-Token` from the inbound request and
sets it both on the MCP call config (Config headers) and in the Agent
Identity SDK context (ContextVar + env fallback) so that `@requires_*`
decorated local tools can exchange credentials. Public agentrun-sdk has no
built-in WAT forwarding — the sample code is the reference implementation.

| Resource | How it is created | Phase |
|---|---|---|
| aliyun CLI credential (AK profile) | User runs `aliyun configure` [WAIT] + verify [AUTO] | 0 |
| OIDC identity provider (user-provided IdP) | AgentIdentity API [AUTO] — `01_prepare_identities.sh` (user provides the Discovery URL; name asked per Rule 12) | 2.1 |
| RAM OAuth2 app | Console [WAIT] (the console path is the only one verified end to end for the scopes the sample needs; an app registered through the IMS API has not been shown to work) | 2.2 |
| AgentIdentity OAuth2 provider | Console [WAIT] (callback_url is write-only via API; authorization flow not verified end-to-end) | 2.2 |
| OAuth2 callback backfill into the RAM app | IMS API [AUTO] — re-run `01_prepare_identities.sh` with E2E_RAM_APP_ID + E2E_CALLBACK_URL | 2.2 |
| AgentRun model service | Console [WAIT] | 2.3 |
| AgentRun MCP tool (bound to the OAuth2 provider) | **Console only** [WAIT] | 2.4 |
| API Key credential provider (Group A) | AgentIdentity API [AUTO] — `01_prepare_identities.sh` (fixed name `test-provider-api-key`, reused if exists) | 2.5 |
| OSS test file (Group C) | oss2 [AUTO] — `02_oss_testfile.sh` | 2.6 |
| Role permissions for the runtime's workload identity | aliyun CLI (attach AliyunOSSReadOnlyAccess) [AUTO] — runs AFTER deploy (the identity is auto-created at deploy time) | 3.5 |
| Cedar policy set + policies | AgentIdentity API [AUTO] (binding via console [WAIT]) | 4 |
| DingTalk MCP tool (Group E) | Console — same flow as 2.4 (URL from https://mcp.dingtalk.com) [WAIT] | 2.4 |
| AgentRun Runtime (code-package upload) | Console [WAIT] (build [AUTO]) | 3 |

Notes on workload identity: deploying a Runtime with AgentIdentity credential
config auto-creates a platform-managed workload identity (name
`agentrun-<runtime-id>`, role `agentrole-xxxxx`). Do NOT create one manually.
The gateway-issued WAT binds to that identity; its role needs the cloud
permissions your local tools require (e.g. OSS read for the sample).

## Prerequisites

1. **Alibaba Cloud account** — master account or RAM user with AgentRun,
   AgentIdentity, RAM and OSS access.
2. **Local tooling** — conda, Python >= 3.10, aliyun CLI. Phase 1
   auto-installs whatever is missing (via Homebrew when available).
3. **OIDC identity provider** — the user must have their own IdP and be able
   to issue a test ID Token for one user (e.g. `sub=testuser`). For
   throwaway testing a self-hosted discovery+JWKS pair on a public OSS
   bucket works, but the user-provided path is the default.

## Phase 0: Project & CLI Setup

**What**: secure the two inputs every later step needs — the sample project
and working cloud credentials (CLI-first; there is no secrets file).

<!-- AGENT:AUTO -->
Locate the sample project; clone the kit repository automatically if absent:

```bash
source scripts/lib/common.sh
if dir=$(resolve_project_dir); then
  save_project_dir "$dir"
  echo "FOUND: $dir"
else
  echo "kit repository not found locally — cloning..."
  git clone https://github.com/aliyun/agent-identity-dev-kit.git
  if dir=$(resolve_project_dir); then
    save_project_dir "$dir"
    echo "FOUND: $dir"
  else
    echo "SAMPLE_NOT_IN_REPO"
  fi
fi
```

<!-- AGENT:WAIT:Only if it printed SAMPLE_NOT_IN_REPO -->
The sample is not in the repository yet (or lives under a different directory
name). Ask the user for the local sample path (set `E2E_SAMPLE_NAME` when the
directory name differs from the default). If the user has NO local copy at
all: the sample belongs to the agent-identity-dev-kit repo — clone
https://github.com/aliyun/agent-identity-dev-kit.git; if the sample directory
is still absent there, ask the user to obtain the team's sample bundle first:

```bash
source scripts/lib/common.sh && save_project_dir "<path-from-user>"
```

<!-- AGENT:AUTO -->
Verify the aliyun CLI credential (install via `brew install aliyun-cli` if
missing; install is automatic). Plugin mode requires CLI >= 3.3.3 — Phase 1
enforces the version and installs the plugins, so run this check after it when
starting from a bare machine:

```bash
aliyun sts get-caller-identity
```

<!-- AGENT:WAIT:If sts get-caller-identity failed or the account is wrong -->
The CLI is not configured (or points at the wrong account). Ask the user to
run `aliyun configure` interactively (choose AK mode, paste their AccessKey
pair, region = the deployment region), then re-run the check. Never ask the
user to paste the AccessKey into the chat. Note: OAuth login mode works for
read-only calls but cannot perform RAM write operations
(`ram attach-policy-to-role` and similar) — prefer AK mode for this workflow;
see `references/ram-policies.md` section 3.

## Phase 1: Environment Detection

<!-- AGENT:AUTO -->
```bash
bash scripts/00_detect_env.sh
```

Detects/installs conda + aliyun CLI, enforces the CLI >= 3.3.3 requirement,
pre-installs the `sts` / `ram` CLI plugins, selects a Python >= 3.10
environment, and records the toolchain plus the observability session id into
the state directory. Failure stops the run.

Tell the user that this step also sets `auto-plugin-install` to `true` in their
aliyun CLI profile (Rule 12: they must know what is changed on their machine).
This is a persistent, machine-wide CLI setting, and it is the only mechanism
that suppresses the plugin-install prompt — passing `--auto-plugin-install` per
command was field-tested and does NOT suppress it. Without the setting, a
missing plugin aborts a non-interactive run with
`failed to read user input: EOF`. To undo it afterwards:
`aliyun configure set --auto-plugin-install false`.
For a FROM-ZERO verification run, prefix it with `E2E_FRESH=1` — this wipes
business state from any previous run (stale env.sh keys like an old
E2E_RAM_APP_ID would otherwise leak into the new run via load_e2e_env;
the wheels cache is kept — the crcmod manylinux wheel is unobtainable
elsewhere).

## Phase 2: Cloud Resource Preparation

**Naming (collect FIRST — Rule 12):** ask the user for the
resource names (or one prefix). AgentRun/AgentIdentity resource names must
START WITH A LETTER — numeric-only date prefixes are rejected (use
`<word>-<date>` style like `mcp-0816`, never `08-16-mcp`). Also collect the
user's IdP Discovery URL (where to get it: references/console-guides.md 2.1).

Resources are prepared per the table above. Present the console steps from
`references/console-guides.md` one by one; after each user step, verify via
CLI/API where possible and record the value (provider names, tool names,
model names) into the state directory.

<!-- AGENT:AUTO -->
Create/reuse the API-creatable identity resources (IdP registration + API
Key provider; re-run the same script later for the callback backfill).
Idempotent — existing resources are detected and reused, never duplicated:

```bash
E2E_IDP_NAME=<idp-name> E2E_IDP_DISCOVERY_URL=<discovery-url> \
  bash scripts/01_prepare_identities.sh
```

Key points baked into the guides (all verified in the field):

- Region must be explicit everywhere. Both agentrun-sdk and
  agent-identity-cli default to cn-beijing; the deployment env MUST include
  `AGENT_IDENTITY_REGION_ID=<region>` or local-tool credential fetch fails.
- The MCP tool registration page auto-fills `"transportType": "sse"` in its
  JSON example — replace the whole block with the verified streamable-http
  form from the guide.
- The three-way OAuth2 handshake order matters: RAM app (console) →
  AgentIdentity provider (console, yields the callback URL) → backfill the
  callback into the RAM app via API: re-run
  `E2E_RAM_APP_ID=<app-id> E2E_CALLBACK_URL=<url> bash scripts/01_prepare_identities.sh`.
- Do NOT create a workload identity manually — the Runtime deployment
  auto-creates one.
- All remote MCP tools (Alibaba Cloud API MCP for B/D, DingTalk Document
  MCP for E) are registered together in Phase 2.4 — one console flow per
  tool, upstream URLs obtained via the paths in console-guides.md (never
  just ask the user for "the URL" without telling them where it comes from).

## Phase 3: Build & Deploy

<!-- AGENT:AUTO -->
Build the deployment zip (cross-platform dependency vendoring — the exact
pip invocation matters, see `references/packaging.md`):

```bash
bash scripts/03_build.sh
```

The build script implements the verified pip pipeline: a FULLY-PINNED
constraints file (the 2026-08-16 known-good lock — partial pinning caused
runtime crashes), multi manylinux platform tags, locally built wheels
for the sdist-only transitive deps (crcmod auto-repacked from prior build
artifacts), and a post-install version self-check. Do not simplify it.

<!-- AGENT:WAIT:Runtime creation -->
Guide the user through AgentRun console → create agent via code package
(`references/agentrun-deploy.md`): upload the zip, startup command
`python3 main.py`, port 9000, execution role default, credential config =
AgentIdentity provider authentication → the IdP from Phase 2.1, and the
minimal environment variable set:

```json
{
  "PYTHONPATH": "/opt/python:/code/python",
  "MODEL_SERVICE_NAME": "<model card title>",
  "MODEL_NAME": "<model tag inside the card>",
  "TOOL_NAME": "<hosted MCP tool name(s), comma-separated>",
  "AGENT_IDENTITY_REGION_ID": "<region>",
  "ENABLE_WEATHER_TOOL": "1",
  "ENABLE_OSS_TOOL": "1",
  "ENABLE_TIME_TOOL": "1",
  "ENABLE_SCHEDULE_TOOL": "1"
}
```

<!-- AGENT:AUTO -->
Verify deployment & capture the invocation endpoint (note the exact path —
`/invocations/openai/v1/chat/completions` — the plain `/invocations` suffix
404s inside the app):

```bash
bash scripts/04_reachability.sh
```

<!-- AGENT:AUTO -->
Attach the OSS read policy to the workload-identity role that the deploy
just auto-created (Group C prerequisite — finds the role via the workload
identity list, no console needed):

```bash
bash scripts/05_attach_role_policy.sh
```

## Phase 4: Verification Matrix

Run `references/testing-checklist.md` in order. Each case lists the exact
curl, the expected success picture, and the failure signature to compare
against `references/troubleshooting.md`:

1. Inbound: no token → 401 `no ID token provided`; valid token → 200.
2. Group B (hosted MCP): first call returns an OAuth2 authorization link →
   user clicks immediately → next call returns the filtered tool list.
3. Group D (Cedar): create the policy via AgentIdentity API [AUTO], bind the
   policy set to the tool in console [WAIT], then observe partial evaluation
   (unpermitted tools vanish from the list) and parameter-level 403 vs pass.
4. Group A/C (local tools): weather / OSS read / schedule / time — each
   returns its success picture via SDK credential injection.
5. Group E (DingTalk): `create_document` returns a real document URL.

<!-- AGENT:AUTO -->
Cedar demo policies (tool-level + parameter-level `when` condition) are
created by:

```bash
bash scripts/06_cedar_setup.sh
```

## Phase 5: DingTalk MCP Wiring (Group E, optional)

The DingTalk tool was registered back in Phase 2.4. Here, after the Runtime
is deployed: append the DingTalk tool name to the Runtime's `TOOL_NAME`
(comma-separated) and redeploy, then verify with the checklist's Group E
case (first use returns an authorization link; afterwards `create_document`
returns a real document URL).

## Phase 6: Cleanup

<!-- AGENT:WAIT:confirm cleanup -->
```bash
bash scripts/07_cleanup.sh
```

Deletes cloud resources created by this run (Cedar policies, OSS test file,
API-key provider if created by the skill) and prints a console checklist for
the resources that cannot be deleted via API (MCP tools, runtime, providers).
Never touches resources the user brought (IdP, RAM app, model service).

## References

- `references/console-guides.md` — step-by-step console flows (IdP, OAuth2
  handshake, model, MCP registration incl. the verified JSON block, API-key
  provider, DingTalk marketplace).
- `references/packaging.md` — the verified cross-platform build pipeline and
  why each flag exists.
- `references/agentrun-deploy.md` — runtime creation field guide (env vars,
  credential config, invocation path).
- `references/testing-checklist.md` — the verification matrix with commands,
  expected outputs, and success pictures.
- `references/troubleshooting.md` — field-verified failure signatures and
  fixes (indexed by issue).
- `references/cleanup.md` — what is deleted how, and what stays.
- `references/ram-policies.md` — the RAM actions the operator needs, a
  least-privilege policy document, and the one role the skill grants a policy to.
