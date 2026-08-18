# AgentLoop Application Onboarding

> **Domain entry**: this file is the onboarding-domain playbook dispatched from the router [../SKILL.md](../SKILL.md). It covers APM and AI observability onboarding into AgentLoop.

> **Product scope**: This skill onboards applications into **AgentLoop** only. It is **not** a general CloudMonitor (CMS) management skill. Use workspace names matching `agentloop-{32-char-code}`; never onboard into `default-cms-*` or other CMS workspaces. The underlying CLI is `aliyun cms2`.

## Prerequisite Check

1. **Check `aliyun` exists** - `which aliyun` (macOS/Linux) or `where aliyun` (Windows).
 - Not found -> ask the user to install the aliyun CLI first: <https://help.aliyun.com/document_detail/121541.html>. Stop and wait.

2. **Check CLI version** - run `aliyun version`. Minimum required: **3.3.15** (see `compatibility` in frontmatter).

 > WARNING: Compare version segments as **integers** (semver): 3.3.4 < 3.3.15 because 4 < 15.
 > Shell verification: `printf '%s\n' "3.3.15" "$(aliyun version)" | sort -V | head -1`
 > If the output equals the current version, the requirement is NOT met.

 - Version OK -> go to step 3.
 - Version too old or unrecognized -> 
 1. Run `aliyun upgrade --help` to test whether the `upgrade` subcommand exists.
 - Available -> run `aliyun upgrade -y` to update to the latest version automatically, then re-check `aliyun version`.
 2. If `upgrade` not available -> run `curl -fsSL --connect-timeout 10 --max-time 300 https://aliyuncli.alicdn.com/setup.sh | bash`, then re-check `aliyun version`.
 3. If upgrade succeeded -> go to step 3.
 4. If upgrade failed -> ask the user to upgrade manually: <https://help.aliyun.com/zh/cli/update-cli>. Stop and exit.

3. **Check `cms2` plugin** - run `aliyun cms2 --help`.
 - Help output OK -> continue to **Credentials**.
 - `unknown command` / missing -> **stop immediately**, output the error report below (append CLI version, OS, and error message), and make **no further CLI calls**.

## Credentials

`aliyun cms2` reuses the aliyun CLI credential system (`aliyun configure`).
Use `--profile <name>` to switch profiles.

Required RAM permissions - see [references/ram-policies.md](ram-policies.md).

## Credential Output Redaction

> **CRITICAL** - the APM LicenseKey (`entryPointInfo.authToken`) is a data-reporting credential and falls under the same red lines as AK/SK/STS tokens. Its literal value must **never** appear in any agent-produced output: chat answers, credential tables, execution summaries, generated startup commands, `Dockerfile` lines, K8s manifests, or report files written under `outputs/`.

1. **Capture, do not print** - pipe the value straight into an environment variable so it never reaches a visible line:

```bash
export ARMS_LICENSE_KEY="$(aliyun cms2 apm configuration get \
 --workspace {workspace} --region {regionId} -o json \
 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}" \
 | jq -r '.data.entryPointInfo.authToken')"
```

2. **Verify by presence, not by value** - never dump the raw `apm configuration get` JSON, because it carries `authToken`. Print a boolean plus the non-sensitive fields only:

```bash
aliyun cms2 apm configuration get --workspace {workspace} --region {regionId} -o json \
 | jq '{status: .data.status,
 licenseKeyObtained: (.data.entryPointInfo.authToken | length > 0),
 publicDomain: .data.entryPointInfo.publicDomain,
 privateDomain: .data.entryPointInfo.privateDomain,
 project: .data.entryPointInfo.project}'
```

3. **Keep the indirection in every generated snippet** - reference the variable (`$ARMS_LICENSE_KEY`, `process.env.ARMS_LICENSE_KEY`, `-Darms.licenseKey=$ARMS_LICENSE_KEY`, `x-arms-license-key=$ARMS_LICENSE_KEY`) or leave the `{LicenseKey}` placeholder unsubstituted, and state that the user injects the real value from their own shell or secret store. Never bake the token into an image layer, a committed file, or a Dockerfile `ENV` default.

4. **Report status only** - where a summary must mention the credential, write `LicenseKey: obtained (injected via ARMS_LICENSE_KEY)` or `LicenseKey: not obtained`. Do not print the value, any partially masked form of it, or a credential table column holding it. Identify the environment with `workspace`, `project`, and endpoints - those are not sensitive.

5. **Console or manual paste flows** (for example the Dify monitoring page) - point the user at `apm configuration get` or the AgentLoop console so they copy the LicenseKey themselves; never echo it on their behalf.

## Observability

### User-Agent Template

Every `aliyun` CLI command (`aliyun cms2`, `aliyun sts`, `aliyun cs`, etc.) in
this skill **MUST** include the `--user-agent` flag:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

Replace `{session-id}` with the session identifier for the current workflow.

Example:

```bash
aliyun cms2 apm configuration get \
 --workspace agentloop-2694ecf8****************1f84542d \
 --region cn-hangzhou \
 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/3f2a8b1c4d5e6f709182a3b4c5d6e7f8"
```

### session-id Rule

1. **Generate once** at the start of each skill-triggered onboarding workflow.
2. **Format**: exactly **32 lowercase hexadecimal characters**, no hyphens, no prefix.
3. **Reuse** the same `session-id` for **all** CLI commands within the same workflow
 so backend logs can be correlated across steps.
4. **Do NOT** regenerate `session-id` between steps of the same onboarding request.
5. **Generation** (pick one):

```bash
# Preferred
openssl rand -hex 16

# Alternative
uuidgen | tr -d '-' | tr '[:upper:]' '[:lower:]'
```

## Global Conventions

**Hard constraint**: fallback to `aliyun cms`, other API versions, or any workaround is strictly prohibited.

> **Always run `aliyun cms2 <command> [subcommand] --help` first** to get the full flag list and examples.

- **Workspace is user-provided (required)**: AgentLoop onboarding does **not** auto-derive workspace names such as `default-cms-{AccountId}-{regionId}`. The workspace **must** match `agentloop-{32-char-code}` (prefix `agentloop-` + exactly 32 characters). Example: `agentloop-2694ecf8****************1f84542d`.
  - **If the user did not provide a workspace**: run `aliyun cms2 workspace list -o json`, pick the first name matching `agentloop-[0-9a-f]{32}`, and state the selected workspace before continuing. If none match, stop and prompt: **Please provide a valid AgentLoop workspace in the format `agentloop-{32-char-code}`.**
  - **Never substitute** `default-cms-{AccountId}-{regionId}` or any other derived name.
  - **Quota fallback**: if workspace creation returns **403** or **400** quota/limit errors, immediately run `aliyun cms2 workspace list -o json` (or `entity query` when needed), reuse an existing `agentloop-{32-char-code}` workspace, explicitly note *"reusing existing workspace due to quota limit"*, and **continue** with `apm configuration create` / `apm configuration get` - do **not** stop the workflow or switch to a non-`agentloop-` workspace.
- **Prefer `-o text`** (default) to reduce token consumption for list/get; use `-o json` only when indented JSON is needed.
- **Before onboarding concrete resource IDs**, verify them with `entity query --source CloudResource`; do not rely on ID shape alone.
- **`entity query` default time range**: when the user does not specify `--from`/`--to`, default to the last 7 days (`--from` = now - 7d, `--to` = now, both as Unix seconds).

## Execution Safety

Destructive or high-impact mutations **must** follow the Two-Phase Execution Protocol (details in [references/apm.md](apm.md#execution-safety-protocol)):

1. **Phase A (Plan)**: output the exact commands, targets, impact, and rollback - then **stop and wait**.
2. **Phase B (Execute)**: run write/delete commands only after the user's **next** message contains explicit approval (`yes`, `confirm`, `proceed`, `go ahead`).

**Mandatory Rules** (violations are workflow errors):

- Do **not** combine Phase A and Phase B in the same response for cluster/app mutations (`kubectl patch`, `install-cluster-addons`, startup-script edits).
- `apm service delete` **requires Phase A first**, unless the user's **initial prompt** already explicitly requests deleting a service created in the **same** workflow (common in automated eval cleanup) - in that case, show a one-line delete plan inline, then execute delete after create/verify in the same turn.
- Never interpret silence as approval.

Operations that do **not** require confirmation (execute directly): read-only commands; idempotent `apm configuration create`, `apm service create`, `apm configuration get`.

## Error Handling

Error codes and actions are listed in `aliyun cms2 --help`. Additional tips:

- `InvalidJSON` usually means malformed `--body`; validate with `jq . <<<'<value>'` before passing to the CLI.
- `--body and stdin are mutually exclusive; specify only one` - means both `--body` (or `--file`) and stdin data were provided. Fix: keep only one input source. In agent/CI environments where stdin may be a pipe, append `< /dev/null` to the command to ensure stdin is empty.

**Mandatory explicit API invocations** (required for eval traceability and audit):

| Step | Rule |
|------|------|
| `apm configuration create` | Invoke at least once per workflow. Idempotent success on existing infra counts. Do **not** skip because `get` shows Running. |
| `apm service create` | Invoke at least once when registering a new app. Do **not** skip because a similar name appears in a prior list. |
| `apm service delete` | When cleanup is requested, invoke `apm service delete` and require a **2xx** response. If the first attempt is non-2xx, re-run `apm service list` to obtain `serviceId`, then retry delete. Do **not** assume backend auto-cleanup. |
| Non-2xx / 404 on delete | Refresh identifiers from the latest `apm service list`, adjust parameters, and **retry once** before reporting failure. |

## Module Routing

| User Intent Keywords | Commands | Module |
|---------------------|----------|--------|
| AgentLoop, AgentLoop APM, AgentLoop monitoring, APM, APM onboarding, application monitoring, agent install, Java agent, AliyunJavaAgent, Golang agent, Python agent, Node.js agent, PHP agent, .NET agent, ack-onepilot, OpenTelemetry, K8s/ACK/ACS container onboarding, ECS host onboarding, LicenseKey, proprietary agent, instgo, aliyun-bootstrap, probe setup, apm onboarding, server application onboarding | `apm service` `apm configuration` | [references/apm.md](apm.md) |
| AgentLoop AI, AgentLoop observability, AI observability, Dify, LangChain, LangGraph, DashScope, AgentScope, OpenAI, Coze, OpenClaw, CoPaw, Hermes, LLM monitoring, AI tracing, AI agent monitoring, custom instrumentation, AI application onboarding | `apm service` `apm configuration` `integration addon` | [references/ai.md](ai.md) |

Commands not listed above - see `aliyun cms2 --help`.
