---
name: alibabacloud-agent-identity-agentrun-e2e
description: >
  Deploy and test an Alibaba Cloud agent with end-user authentication and
  tool authorization, then clean up test resources. Use when someone wants
  to deploy an AgentRun-hosted agent governed by AgentIdentity and verify
  that only signed-in users reach it, that each tool receives the
  credentials it needs without any secret in the code, and that authorization
  rules allow or deny expected operations — or when they want to remove the
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
repository under `agent_identity_python_samples/`. The prerequisites and
phases below describe the additional inputs and setup required.

## Execution Rules

Run shell blocks in Bash from the Skill directory. Supply the same absolute
`TMPDIR` on every invocation so each script reads the same run state.

1. Blocks marked `<!-- AGENT:AUTO -->` — execute directly in the terminal, no user confirmation needed.
2. Blocks marked `<!-- AGENT:WAIT:description -->` — STOP and wait for the user's response before proceeding.
3. CLI calls use the configured aliyun profile; Python SDKs use their default credential chain. Ensure both resolve to the intended account; credential environment overrides can change the SDK identity. If the CLI is not configured, guide the user through `aliyun configure`; verify with `aliyun sts get-caller-identity` before cloud preparation. Do not use a separate secrets file or pass, print or export an AccessKey pair.
4. On command failure, stop and report the error (with logs) to the user. Do NOT retry automatically; retry only after the user confirms. Match errors against `references/troubleshooting.md` first.
5. Terminal sessions lose exported variables between calls. Durable state lives in files under the skill state directory; scripts re-read them on every run. All scripts source `scripts/lib/common.sh`.
6. Follow the phases in order; do NOT skip, merge, or simplify steps. Present each WAIT step to the user exactly as written.
7. Background services (nohup) are started and stopped INSIDE the scripts — never append `&` to a terminal call yourself.
8. Automate everything that can be automated — including cloning the kit repository and installing missing tools — and tell the user in one line what you did. Ask the user to act ONLY where their person is strictly required: entering secrets, console UI steps, and account-level decisions.
9. Environment variables in deployment templates are minimal: required variables only. Never add debug switches (e.g. AGENTRUN_SDK_DEBUG) or empty placeholders (e.g. OAUTH_SCOPES="").
10. Register MCP tools through the AgentRun console. This workflow uses the console registration path verified for tool activation and AgentIdentity configuration.
11. OAuth2 authorization links expire within minutes. Whenever a link is returned: (a) IMMEDIATELY open it in the user's browser yourself — run `open "<url>"` on macOS or `xdg-open "<url>"` on Linux — do not rely on the user noticing the chat message in time; (b) also print the link in the message as a fallback. Access-token expiry depends on the provider configuration, so later runs may require authorization again.
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
Explain any term in plain language on first use. Avoid informal labels and
internal vocabulary.>

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
3. a freshly generated random 32-character lowercase hexadecimal ID.

Supplied and cached IDs must use the same format.

`E2E_FRESH=1` clears the cached id and run configuration only when no created
resources remain pending cleanup, so a new run gets a new session.

**User-Agent template.** Built by `ua_string()`:

```
AlibabaCloud-Agent-Skills/<skill-name>/<session-id> skill-version/<version>
```

For this skill that resolves to, for example:

```
AlibabaCloud-Agent-Skills/alibabacloud-agent-identity-agentrun-e2e/0123456789abcdef0123456789abcdef skill-version/1.0.0
```

Read the version from `references/manifest.json` and stop before cloud calls
if the manifest or session ID is invalid.

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
| aliyun CLI credential (AK profile) | User runs `aliyun configure` [WAIT] + verify [AUTO] | 1 |
| OIDC identity provider (user-provided IdP) | AgentIdentity API [AUTO] — `01_prepare_identities.sh` (user provides the Discovery URL; name asked per Rule 12) | 2.1 |
| RAM OAuth2 app | Console [WAIT] — configure the scopes required by the sample | 2.2 |
| AgentIdentity OAuth2 provider | Console [WAIT] | 2.2 |
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
   installs missing tools through Homebrew. Without Homebrew, prepare conda
   and the CLI before running Phase 1.
3. **OIDC identity provider** — the user must have their own IdP and be able
   to issue a test ID Token for one user (e.g. `sub=testuser`). For
   isolated testing a self-hosted discovery+JWKS pair on a public OSS
   bucket works, but the user-provided path is the default.

## Phase 0: Project Location

Locate the sample project. CLI setup and verification follow in Phase 1.

<!-- AGENT:AUTO -->
Locate the sample project; clone the kit repository automatically if absent:

```bash
source scripts/lib/common.sh
if dir=$(resolve_project_dir); then
  save_project_dir "$dir"
  echo "FOUND: $dir"
else
  echo "kit repository not found locally — cloning..."
  git clone https://github.com/aliyun/agent-identity-dev-kit.git || exit $?
  if dir=$(resolve_project_dir); then
    save_project_dir "$dir"
    echo "FOUND: $dir"
  else
    echo "SAMPLE_NOT_IN_REPO"
  fi
fi
```

<!-- AGENT:WAIT:Only if it printed SAMPLE_NOT_IN_REPO -->
The sample directory was not found (it may use a different directory
name). Ask the user for the local sample path (set `E2E_SAMPLE_NAME` when the
directory name differs from the default). If the user has NO local copy at
all: the sample belongs to the agent-identity-dev-kit repo — clone
https://github.com/aliyun/agent-identity-dev-kit.git; if the sample directory
is still absent there, verify that the selected repository revision includes
the sample, or ask the user for an existing sample directory:

```bash
source scripts/lib/common.sh && save_project_dir "<path-from-user>"
```

## Phase 1: Environment Detection

<!-- AGENT:AUTO -->
```bash
bash scripts/00_detect_env.sh
```

Detects/installs conda + aliyun CLI, enforces the CLI >= 3.3.3 requirement,
pre-installs the `sts` / `ram` CLI plugins, selects a Python >= 3.10
environment, and records the toolchain plus the observability session id into
the state directory and verifies the CLI profile. Failure stops the run.

<!-- AGENT:WAIT:If sts get-caller-identity failed or the account is wrong -->
Ask the user to run `aliyun configure` locally with the deployment region,
then rerun the environment check and confirm the active account. This workflow
uses an AccessKey profile; see `references/ram-policies.md` section 3. Never
ask the user to paste AccessKey values into the conversation.

<!-- AGENT:AUTO -->
After the check succeeds, save the regions used by later scripts and the console:

```bash
source scripts/lib/common.sh
save_kv AGENTRUN_REGION "<deployment-region>"
save_kv E2E_OSS_REGION "<object-region>"
```

Tell the user that this step also sets `auto-plugin-install` to `true` in their
aliyun CLI profile (Rule 12: they must know what is changed on their machine).
This persistent CLI profile setting prevents interactive installation prompts
for missing plugins. Without the setting, a
missing plugin aborts a non-interactive run with
`failed to read user input: EOF`. To undo it afterwards:
`aliyun configure set --auto-plugin-install false`.
For a new verification run, prefix the environment check with `E2E_FRESH=1`
only after the previous run has no resources pending cleanup. This resets saved
configuration, the session id, and prior build artifacts; the wheels cache is kept.

## Phase 2: Cloud Resource Preparation

**Naming (collect FIRST — Rule 12):** ask the user for the
resource names (or one prefix). Use names starting with a letter and follow
the field-specific console rules (use
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
E2E_IDP_NAME="<idp-name>" E2E_IDP_DISCOVERY_URL="<discovery-url>" \
  bash scripts/01_prepare_identities.sh
```

<!-- AGENT:AUTO -->
After console preparation, prepare or reuse the OSS test object:

```bash
bash scripts/02_oss_testfile.sh
```

Configuration requirements:

- Use the saved regions consistently. The deployment environment must include
  `AGENT_IDENTITY_REGION_ID=<deployment-region>` for local-tool credentials.
- The MCP tool registration page auto-fills `"transportType": "sse"` in its
  JSON example — replace the whole block with the verified streamable-http
  form from the guide.
- The three-way OAuth2 handshake order matters: RAM app (console) →
  AgentIdentity provider (console, yields the callback URL) → backfill the
  callback into the RAM app via API: re-run
  `E2E_RAM_APP_ID="<app-id>" E2E_CALLBACK_URL="<url>" bash scripts/01_prepare_identities.sh`.
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

The build script applies version constraints, multiple manylinux platform tags,
locally built wheels for source-only dependencies, and post-install version checks.
For crcmod, it rebuilds the official pure-Python wheel and removes earlier
cached crcmod wheels with unverified compatibility tags.
Dependencies are installed under the sample's `python/` directory to preserve
its source files. If dependencies already exist in the sample root, use a clean
checkout and save its path as shown in Phase 0 before building.

<!-- AGENT:WAIT:Runtime creation -->
Guide the user through AgentRun console → create agent via code package
(`references/agentrun-deploy.md`): upload the zip, startup command
`python3 main.py`, port 9000, execution role default, credential config =
AgentIdentity provider authentication → the IdP from Phase 2.1, and the
minimal environment variable set:

```json
{
  "PYTHONPATH": "/code/python:/opt/python",
  "MODEL_SERVICE_NAME": "<model card title>",
  "MODEL_NAME": "<model tag inside the card>",
  "TOOL_NAME": "<Alibaba-Cloud-API-MCP-tool-name>",
  "AGENT_IDENTITY_REGION_ID": "<region>",
  "ENABLE_WEATHER_TOOL": "1",
  "ENABLE_OSS_TOOL": "1",
  "ENABLE_TIME_TOOL": "1",
  "ENABLE_SCHEDULE_TOOL": "1"
}
```

Before changing a reused Runtime, follow the backup requirements in
`references/agentrun-deploy.md` under "Redeploys". Preserve unrelated settings.

<!-- AGENT:AUTO -->
After READY, save the exact Runtime name and region, then verify deployment
and capture the invocation endpoint (note the exact path —
`/invocations/openai/v1/chat/completions` — the plain `/invocations` suffix
404s inside the app):

```bash
source scripts/lib/common.sh
save_kv E2E_RUNTIME_NAME "<runtime-name>"
save_kv AGENTRUN_REGION "<deployment-region>"
bash scripts/04_reachability.sh
```

<!-- AGENT:AUTO -->
Attach the OSS read policy to the Runtime's automatically created workload-identity
role. For a reused Runtime, record whether the script reports an existing grant
or a new attachment; only a new attachment should be removed during cleanup.

```bash
bash scripts/05_attach_role_policy.sh
```

## Phase 4: Verification Matrix

Run T1–T5 in `references/testing-checklist.md` in order. Each case lists the exact
curl, the expected success picture, and the failure signature to compare
against `references/troubleshooting.md`:

1. Inbound: no token → 401 `no ID token provided`; valid token → 200.
2. Group B (hosted MCP): first call returns an OAuth2 authorization link →
   user clicks immediately → next call returns the available tool list.
3. Group D (Cedar): create the policy via AgentIdentity API [AUTO], bind the
   policy set to the tool in console [WAIT], then observe partial evaluation
   (unpermitted tools vanish from the list) and parameter-level 403 vs pass.
4. Group A/C (local tools): weather / OSS read / schedule / time — each
   returns its success picture via SDK credential injection.

At T3, run `06_cedar_setup.sh` with `E2E_CEDAR_STAGE=tool`; at T4, run it
with `E2E_CEDAR_STAGE=param` before testing the matching and denied calls.
Follow the checklist commands. The unconditional tool permit must not remain
active during the parameter test.

## Phase 5: DingTalk MCP Wiring (Group E, optional)

The DingTalk tool was registered back in Phase 2.4. Here, after the Runtime
is deployed: append the DingTalk tool name to the Runtime's `TOOL_NAME`
(comma-separated) and redeploy. After READY, verify that the Runtime handling
the current T6 request has loaded the updated tools and provides the actual
document-creation function and input schema. Use that request's tool-schema
response or Runtime logs correlated to the same invocation and instance;
control-plane configuration or another instance's startup log alone is
insufficient. If the request still sees the old tool list, report that the update
has not taken effect for that request and do not create a document. Then follow
checklist T6 with the verified function and schema. Complete authorization if
requested, then open the returned document URL and verify its title and body.

## Phase 6: Cleanup

Restore the original tool permission settings and bindings, and remove this
run's policy-set binding before cleanup. Restore and verify reused Runtime code
and configuration as described in `references/cleanup.md`; preserve reused resources.
If step 05 added OSS read access to a reused
Runtime's role, remove only that new grant as described in `references/cleanup.md`.

<!-- AGENT:WAIT:confirm cleanup -->
```bash
bash scripts/07_cleanup.sh
```

Deletes Cedar policies and OSS test resources created by this run, and
prints a console checklist for MCP tools, Runtime and credential providers.
Never touches resources the user brought (IdP, RAM app, model service).
Failed deletions remain recorded and cause a nonzero exit; resolve the reported
failure and rerun with the same state directory.

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
- `references/troubleshooting.md` — known failure signatures and
  fixes (indexed by issue).
- `references/cleanup.md` — what is deleted how, and what stays.
- `references/ram-policies.md` — the RAM actions the operator needs, an
  operator policy example, and the one role the skill grants a policy to.
