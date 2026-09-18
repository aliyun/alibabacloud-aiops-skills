# Tutorial 01: One Sentence Lets Your Local Agent Run the Full Managed Agents Loop

| Item | Value |
| --- | --- |
| **Goal** | Walk the full closed loop — login → create Agent → attach skill → run session → collect artifacts — without writing a line of integration code |
| **Capabilities involved** | Agent / Environment / Session / Event / Skill / builtin tools (`write`) / automatic artifact scanning and download |
| **Difficulty** | Beginner |
| **Prerequisites** | A local Agent with CLI and tool-calling support (Qoder / Claude Code / Codex etc.); an Alibaba Cloud account |
| **Estimated time** | 10-15 minutes |
| **Source** | Official whitepaper "Appendix 1: the AI-Native quick-start experience"; steps and commands field-tested on CLI 1.18.1 |

## Scenario

A direct demonstration of the "zero-code / AI-Native" experience on top of All For API: hand a
natural-language instruction to your local Agent, and it performs every operation for you via the
Bailian CLI. Fits first-time Managed Agents users, and live demos for customers.

## Final artifacts

A "web design" Managed Agent created in Bailian + one successful session + the personal-homepage
file downloaded to your machine.

## Steps

### 1. Hand this instruction to your local Agent

Copy this directly to your local Agent (Qoder / Claude Code / Codex etc.):

```text
I want to use the "Managed Agents" application published on Alibaba Cloud Bailian.

Reference docs:
- CLI installation and login: https://bailian.aliyun.com/cli/install.md

Please help me with these steps:
1. First log in with the Bailian CLI: bl auth login --console
2. Create a web-design Managed Agent for me, configure the matching Skill capabilities, send a message asking the Agent to design a simple personal-homepage template as a test, and finally download the produced files for me.
```

**Expected result**: your local Agent decomposes this into a chain of tool calls and autonomously
executes the 5 steps below.

### 2. The 5 steps that actually happen behind the scenes (for explanation and troubleshooting)

1. **Install and log in to the CLI**: install the Bailian CLI per the docs, run
   `bl auth login --console` to open the authorization page and log in, obtaining workspace credentials.
2. **Initialize and define the Agent**: `bl managed-agent init` generates `agents.yaml` (the real
   template is in "What init generates" below), completed per the "web design" brief — model,
   system prompt, builtin tools (the default template has **no** `write`; add it yourself to
   produce files).
3. **Attach the skill and create**: under the agent's `skills:`, attach the official
   "frontend-design" skill via `type: official` + `skill_id` → `validate` offline check → `plan`
   preview → `apply --yes` formally creates the Agent in Bailian (saving auto-generates a version —
   field-tested: `version: 1` right after creation, incremented on every update).
4. **Start a session and run the test**:
   ```bash
   bl managed-agent session run --agent <agent name in agents.yaml> --prompt "Design a simple personal-homepage template"
   ```
   Note `--agent` takes the **local name from `agents.yaml`** (e.g. `web-designer`), not the remote
   `agent_01xxx` ID; passing a remote ID errors with `not found in config`.
   The cloud immediately spins up an isolated sandbox to run the Session. Events stream in real
   time: the Agent first reasons about the layout (`reasoning`), then calls `write` to generate
   HTML/CSS under the sandbox's `/mnt/session/outputs/` (`tool_call` → `tool_call_output`), until
   `session_status` becomes `idle`, marking completion. **Anything written under
   `/mnt/session/outputs/` is automatically scanned into a downloadable artifact** — no extra
   registration needed.
5. **Collect the artifacts**: artifacts do not land on your machine automatically; download them
   via the Files API with the `file_id` (see section 2b — one `scope_id` query lists every
   artifact of the session).

### 2a. What init generates (field-tested, verbatim)

```yaml
version: "1"
providers:
  bailian:
    api_key: ${DASHSCOPE_API_KEY}
    base_url: ${BAILIAN_BASE_URL}
defaults:
  provider: bailian
environments:
  dev:
    config:
      type: cloud
      networking:
        type: unrestricted
agents:
  assistant:
    description: "General-purpose assistant"
    model: qwen3.8-max
    instructions: |
      You are a helpful assistant.
    environment: dev
    tools:
      builtin: [bash, read, glob, grep]
```

The three spots to change:

```yaml
agents:
  web-designer:                       # rename to something meaningful; this name is what session run --agent takes
    model: qwen3.8-max                # the template default; field-tested working
    instructions: |
      You are a senior web designer and frontend engineer; produce a runnable single-file web page directly from the requirements.
    environment: dev
    tools:
      builtin: [bash, read, write, edit, glob, grep]   # you must add write yourself, or no files get written
    skills:
      - type: official
        skill_id: "skill_M2IyYmUyYmI3ZjI1NGJhZTkwZT"   # use the id, not the name (frontend-design)
        version: "1.0"
```

**The real story of builtin tools (field-tested + official statements)**:

- The 6 core tools that must be **explicitly configured** in `tools.builtin`: `bash`, `read`,
  `write`, `edit`, `glob`, `grep`.
- `mark_artifacts` is **not needed by default**: callable at runtime even unconfigured; it exists
  for when you **wrap a conversational UI** around your own business and need artifacts displayed
  against specific turns — plain artifact collection never needs it (see 2b).
- `download_file` is **officially decommissioned**; stop adding it to configs (existing configs are
  not force-cleaned yet, but do not rely on it).
- Typing other names (e.g. `web_search`) **passes `validate` and `plan` without complaint, but the
  server silently drops them** — after creation, double-check which tools actually took effect on
  the agent. Built-in `websearch` / `webfetch` are launched; `browser_use` is available through MCP.
  The marketplace service `WebSearch` (`bailian_web_search`) remains an alternative.
  See [launch status](../product/status.md) and verify current configuration fields.
- **One more trap when creating Agents via plain REST** (CLI users won't hit it; code writers will):
  writing only `default_config.enabled: true` in `tools[]` **does not actually deliver the tools** —
  you must list each one in `configs[]` as `{"name": "bash", "enabled": true}`. Miss it and you get
  `TOOL_NOT_FOUND: Tool 'bash' not found. Available tools: ['mark_artifacts']`, with the Agent
  concluding "I have no tools available". Full example in
  [../cookbook/01-get-started-data-analysis-agent.md](../cookbook/01-get-started-data-analysis-agent.md) Step 1.

**How to verify**: `bl managed-agent session events --session-id <id> --all` shows the full event
stream; artifacts retrieved per 2b open locally.

### 2b. Getting artifacts onto your machine (field-tested path)

The archived CLI 1.18.1 test had no download subcommand. Check current help and, if appropriate, try one update per [CLI/API routing](../workflows/cli-api-routing.md); if still unavailable, use the Files API in two steps: list the session's
artifacts by `scope_id` to get the `file_id`, then download.

**Precondition**: the Agent only needs to write files under the sandbox's `/mnt/session/outputs/` —
files landing there are **automatically scanned** into downloadable artifacts (field-tested: with
no registration tool called at all, the files still appear in the listing with `downloadable: true`).

```bash
# ① List all artifacts of this session (pass session_id as scope_id; results are sorted by created_at descending)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  "https://<workspace_id>.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio/files?scope_id=<session_id>" | jq '.data[] | {id, filename, size_bytes}'

# A field-tested response looks like:
# {"id":"file_9jy2...","filename":"auto_probe.txt","size_bytes":17}
# (each row also carries downloadable:true / status:available / scope:{type:session,id:sesn_...})

# ② Download (still downloadable after the session is archived; field-tested byte-identical before and after archiving)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  "https://<workspace_id>.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio/files/<file_id>/content" \
  -o index.html
```

To inspect file metadata first (`filename` / `mime_type` / `size_bytes` / `downloadable` / `status`),
call `GET /files/{file_id}` without the `/content` suffix.

> **When do you use the `mark_artifacts` tool?** It needs no configuration and no deliberate
> invocation by default — the path above never touches it. Only when you **wrap a conversational
> UI** around your own business and need "which files did this turn produce" displayed against the
> matching turn do you have the Agent call `mark_artifacts` to tag artifacts; the tags appear in
> the event stream's `tool_call_output` (carrying `file_id` and `path`). That is also why the init
> template's `tools.builtin` never contains it.

### 3. The manual version (when you want to understand each step)

```bash
bl auth login --console
bl managed-agent init
# Edit agents.yaml: model, system prompt, tools (remember write), attach the frontend-design Skill
bl managed-agent validate
bl managed-agent plan          # review the diff before continuing
bl managed-agent apply --yes
bl managed-agent session run --agent <agent name in agents.yaml> --prompt "Design a simple personal-homepage template"
# Then collect artifacts per 2b
```

To find the real ID of an official skill: `bl managed-agent skill-list --source official --output json`
(`--source` takes `custom` / `official` / `all`). Command flags defer to `bl <command> --help`.

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| `bl: command not found` | CLI not installed | Install per https://bailian.aliyun.com/cli/install.md; shared conventions in the skill `bailian-protocol` |
| Auth failure | Not logged in, or the key not effective yet | Re-run `bl auth login --console`, or set `DASHSCOPE_API_KEY` |
| Every `managed-agent` command returns `HTTP 404` | `BAILIAN_BASE_URL` was set to the root URL (`https://<ws>.cn-beijing.maas.aliyuncs.com`) | The CLI appends resource paths directly after it. Either `unset BAILIAN_BASE_URL` and let the CLI derive it, or set the full prefix including `/api/v1/agentstudio` |
| `apply` says `Refusing to apply N change(s) without confirmation` | `--yes` missing | Show the user the `plan` diff first; `apply --yes` after confirmation (exit code 2) |
| `session run` says `Agent 'agent_01xxx' not found in config` | `--agent` got a remote ID | Pass the local agent name from `agents.yaml` |
| The Agent cannot write files | The init template's `tools.builtin` lacks `write` by default | Add `write` manually |
| A configured tool is unusable by the Agent | The tool name is not on the real list (the 6 core ones: `bash`/`read`/`write`/`edit`/`glob`/`grep`; `download_file` is decommissioned); the server drops it silently and `validate` stays silent | Configure only the core 6; `mark_artifacts` works unconfigured; after creation, re-check the agent's `tools` |
| A file the Agent just wrote is missing from the artifact list (`GET /files?scope_id=...`) | The file was not written under `/mnt/session/outputs/`, or the scan has not caught up yet | State the output directory explicitly in the prompt; re-query after a few seconds |
| The session never ends | A long task is still running | Check the current step with `session events`; Sessions support interruption and resumption |
| Skill not found | Used the Skill's `name` instead of `skill_id`, or the custom skill has not passed review | Look up the real `id` via `skill-list` and fill it into `skill_id`; custom skills must be `active` before mounting |

## Going further

- Want it to run itself on schedule → add a Deployment; see [../workflows/provision.md](../workflows/provision.md)
- Want to integrate it into a business system → [02-integrate-to-your-system.md](02-integrate-to-your-system.md) (grab remote IDs → verify with curl → three shapes → Python/Java implementations)
