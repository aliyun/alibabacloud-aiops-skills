# 07 · Advanced: Custom MCP and Skills — Mounting Your Team's Capability Assets onto the Agent

> In the first six recipes, agents used "platform-provided" capabilities: the builtin toolkit (01), MCP marketplace services (02/04/05). This recipe covers the reverse direction — **mounting capabilities you already own onto the agent**: register your already-running MCP Server into Bailian (custom MCP), and package and upload your team's operating procedures (Skills). The Skills API chain was field-tested end to end (2026-09, cn-beijing region); custom MCP registration is a console operation, walked through via the official entry points, with screenshot placeholders left in place.

## Scenario: Luming Publishing's manuscript-review assistant

"Luming Publishing" is a fictional book-publishing company whose content-operations department processes a large volume of submissions every month. They hold two ready-made assets:

1. **An editorial-standards knowledge base** — long since built on Bailian's knowledge indexing (RAG), exposing a standard MCP endpoint. The pain: only the application side could query this knowledge base before; Managed Agents could not use it.
2. **A manuscript health-check procedure** — the senior editors' "three looks": look at heading levels, look at paragraph length, look at absolutist wording. Previously a manual checklist; they want an agent to execute it automatically.

The ask is clear:

> "The knowledge base's MCP endpoint already exists — let the agent query it. The health-check procedure already exists — let the agent follow it."

That maps exactly onto this recipe's two topics: **custom MCP** (registering an existing service) and **custom Skills** (uploading your own procedures).

First, the coordinate system — an agent's external capabilities come in three tiers:

| Tier | Source | Maintained by | Introduced in |
|---|---|---|---|
| Builtin toolkit `builtin_toolkit` | platform built-in (6 configurable core tools) | Bailian | 01 |
| Marketplace MCP `type: official` | MCP marketplace services | Bailian marketplace hosted | 02 / 04 / 05 |
| **Own assets `type: customer`** | **your MCP Server, your Skill package** | **you** | **this recipe** |

## 1. Custom MCP: register your existing MCP Server into Bailian

### 1.1 Marketplace vs. custom

Bailian's MCP management has two tabs: **Marketplace** (Bailian-hosted, ready to use — the `WebSearch` used in 02 lives here) and **Custom** (for your own MCP servers or third-party services). Custom supports four integration types:

- **Plugin**, **Script deployment**, **AI gateway**, **Alibaba Cloud OpenAPI**

This recipe's focus scenario: **your MCP Server is already running** (Luming's knowledge-base RAG endpoint), and all that's missing is "one registration entry in Bailian". For that, pick **HTTP deployment** under **Script deployment** — note that this step is only a **registration** (telling Bailian the endpoint address and auth method); it does not actually deploy anything for you and **incurs no deployment fee**.

> **Screenshot placeholder 1**: the console's "Managed Agent -> MCP management -> Custom" page (`https://agent.console.aliyun.com/managed-agent/mcp-manage/custom`), with the "Create MCP" entry at the top right.
> Screenshot 1 was not included in this archive; follow the written steps above.

> **Screenshot placeholder 2**: the type-selection page after clicking "Create MCP" — choosing "Script deployment".
> Screenshot 2 was not included in this archive; follow the written steps above.

> **Screenshot placeholder 3**: inside Script deployment, choosing "HTTP deployment".
> Screenshot 3 was not included in this archive; follow the written steps above.

### 1.2 Example: registering a Bailian RAG knowledge base's MCP endpoint

Luming's editorial-standards knowledge base is built on Bailian knowledge indexing; its MCP endpoint is a workspace-level fixed address. The connection config filled in at registration:

```json
{
  "mcpServers": {
    "rag_mcp": {
      "type": "streamableHttp",
      "url": "https://${workspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/indices/rag/mcp",
      "headers": {
        "Authorization": "Bearer ${DASHSCOPE_API_KEY}"
      }
    }
  }
}
```

How to read the three fields:

- `type` takes `streamableHttp` (the MCP protocol's standard HTTP transport); the endpoint is a single URL, stateless calls;
- `${workspaceId}` in `url` is your Bailian workspace ID (visible at the console's top right, shaped like `llm-xxxx`);
- `headers` carries auth — the RAG endpoint uses a plain API Key (Bearer). **Note: the key you fill in at registration is stored in Bailian's MCP config, and the platform attaches it on the agent's behalf at call time** — no need to keep another copy in the agent's system prompt or a vault.

> This example also corrects a common misconception in passing: **"custom MCP" does not require writing an MCP Server from scratch**. Any service you already run that exposes an MCP protocol endpoint — a homegrown business-system API gateway, a third-party SaaS's MCP interface, or even another cloud product (like Bailian knowledge indexing) — can be registered this way. What Bailian does is "registration + proxied calls", not "hosted running".

> **Screenshot placeholder 4**: the form page for filling in the HTTP deployment config (name, URL, headers).
> Screenshot 4 was not included in this archive; follow the written steps above.

> **Screenshot placeholder 5**: the custom-MCP list/detail page after registration completes.
> Screenshot 5 was not included in this archive; follow the written steps above.

### 1.3 API mounting: `type: customer`

After registering (note down the **service name** you gave it), mount it on an agent — the same `mcp_servers` field as mounting a marketplace service in 02, only with `type` changed to `customer`:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{
    "name": "luming-editor",
    "model": {"id": "qwen3.8-max"},
    "mcp_servers": [
      {"type": "customer", "name": "rag_mcp"}
    ]
  }'
```

After mounting, tool enablement is exactly as with marketplace services: add an `mcp_toolkit` in `tools`, fill `mcp_server_name` with the registered name, and set `enabled: true` per tool in `configs[]` (forget the per-tool enablement and the tools go silently missing at runtime — the trap was expanded on in 02).

**One important field-tested difference — the two types validate at completely different times**:

| | `type: official` (marketplace) | `type: customer` (custom) |
|---|---|---|
| Validation at declaration | **No existence check** — a name absent from the marketplace still creates successfully | **Strictly validated** — an unregistered name fails immediately with 400 |
| Failure mode | Tools silently missing at runtime; the agent replies "I have no available tools" | Errors at creation, original message: `AGENT_010 "MCP Server validation failed: error querying MCP details"` |
| Troubleshooting difficulty | High (no error, just absent) | Low (surfaced immediately) |

So the correct order for custom MCP is iron law: **register in the console first, then write it into the agents config**. In passing: custom MCP currently has **no management API** (no matching endpoint in the API overview) — registration, renaming, and deletion all go through the console.

## 2. Skills: package and upload your team's procedures

MCP solves "the agent can call your services"; Skills solve "the agent works by your procedures". A Skill is just a zip package: inside are a **manual** (SKILL.md) plus **bundled resources** (scripts, templates, reference files) — packaged, uploaded, approved, and mounted onto an agent.

### 2.1 What a skill is

- The zip must be at most **10 MB** and **must have SKILL.md at the root**;
- SKILL.md is YAML frontmatter + Markdown body — the frontmatter declares `name` and `description`, and **the agent decides when to invoke the skill based on the description**;
- After upload it passes a **security scan** before it can be mounted (that is the source of the "review time needed"; field-tested below).

Luming's "manuscript health-check" skill, packaged from two files:

**SKILL.md** (the manual):

```markdown
---
name: manuscript-check
description: Manuscript health-check skill. Use when the user submits a manuscript and asks for a "health check", "review", or "pre-publication check": save the manuscript to a text file, run manuscript_check.py, apply the three checks (heading-level skips, paragraphs over 400 words, absolutist banned phrases), and organize the JSON output into a list of review comments.
---

# Manuscript health check

When executing a pre-publication health check on a manuscript, follow this procedure:

1. Save the submitted manuscript content to `/tmp/manuscript.txt`
2. Run `python3 manuscript_check.py /tmp/manuscript.txt`
3. Organize the JSON output into review comments: list each issue's type, paragraph, and recommendation

## Checks

- Heading-level skips (e.g. H1 straight to H3)
- Overlong paragraphs (over 400 words)
- Absolutist banned phrases ("best", "number one", "absolutely", "100 percent", "unprecedented", "one of a kind")
```

**manuscript_check.py** (bundled resource, excerpt):

```python
#!/usr/bin/env python3
"""Manuscript health check: heading levels, paragraph length, banned phrases. Outputs a JSON review list."""
import json, re, sys

BANNED = ["best", "number one", "absolutely", "100 percent", "unprecedented", "one of a kind"]

def check(path):
    text = open(path, encoding="utf-8").read()
    issues = []
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    prev_level = 0
    for i, para in enumerate(paras, 1):
        m = re.match(r"^(#{1,6})\s", para)
        if m:
            level = len(m.group(1))
            if prev_level and level > prev_level + 1:
                issues.append({"issue": "HEADING_SKIP",
                               "detail": f"para {i}: heading jumps from H{prev_level} to H{level}"})
            prev_level = level
        elif len(para) > 400:
            issues.append({"issue": "PARA_TOO_LONG",
                           "detail": f"para {i}: {len(para)} words (limit 400)"})
        for w in BANNED:
            if w in para:
                issues.append({"issue": "BANNED_WORD", "detail": f"para {i}: banned phrase '{w}'"})
    return {"paragraphs": len(paras), "issues": issues}

if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1]), ensure_ascii=False, indent=2))
```

Packaging (SKILL.md directly at the root — no extra directory layer):

```bash
zip manuscript-check.zip SKILL.md manuscript_check.py
```

### 2.2 The full upload chain (API field-tested)

**Step one: upload as an ordinary file first** (POST /files, multipart), take the `file_id`:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -s -X POST "$BASE/files" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@manuscript-check.zip"
```

```json
{"id": "file_zq9kyvmkkprtg0b32afk8rto", "filename": "manuscript-check.zip",
 "mime_type": "application/octet-stream", "size_bytes": 1695,
 "status": "checking", "created_at": "2026-09-02T12:56:45+08:00", ...}
```

Note that the zip file itself also enters review (`status: checking`).

**Step two: create the skill with the file_id** (POST /skills; the request body has just this one field):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "$BASE/skills" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"file_id": "file_zq9kyvmkkprtg0b32afk8rto"}'
```

```json
{
  "id": "skill_MWY3ZTY5ZDE3MGIzNDFkZWI2Zj",
  "name": "manuscript-check",
  "description": "Manuscript health-check skill. Use when the user submits a manuscript and asks for a \"health check\", \"review\", or \"pre-publication check\": ...",
  "source": "customer",
  "status": "checking",
  "latest_version": "1.0",
  "created_at": "2026-09-02T04:57:01Z",
  ...
}
```

Two points worth noting:

1. **`name` and `description` are parsed server-side from SKILL.md** — the request body has no such fields at all. Whatever the frontmatter says is what the skill is called; SKILL.md's `name` is also the directory name inside the sandbox later.
2. **The first version number is auto-assigned as "1.0"**.

**Step three: wait for review.** Field-tested timeline (2026-09-02):

```
12:57:01  POST /skills         -> status: checking
12:57:29 - 13:00:21  GET polling  -> checking (5 polls)
13:01:00  review approved       -> status: active   <- took 3 minutes 59 seconds
```

State machine: `checking` -> `active` (mountable) / `rejected` (not mountable; the version detail lists the issues by file path) -> `deleted`.

**Review is not second-scale** — when scripting uploads, don't expect "upload then mount immediately"; either poll `GET /skills/{skill_id}` until `active`, or make upload an async pipeline (upload -> notify -> mount).

**Step four: mount onto the agent**:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{
    "name": "luming-editor",
    "model": {"id": "qwen3.8-max"},
    "system": "You are the content-review assistant for Luming Publishing. On receiving a manuscript you must run the health check using the manuscript-check skill and organize the findings into review comments.",
    "tools": [{"type": "builtin_toolkit", "default_config": {"enabled": true},
      "configs": [{"name": "bash", "enabled": true}, {"name": "read", "enabled": true},
                  {"name": "write", "enabled": true}, {"name": "glob", "enabled": true},
                  {"name": "grep", "enabled": true}]}],
    "skills": [{"type": "customer", "skill_id": "skill_MWY3ZTY5ZDE3MGIzNDFkZWI2Zj", "version": "1.0"}]
  }'
```

Each `skills[]` entry has three fields: `type` (customer), `skill_id`, and **`version` (must pin exactly one existing version; `latest` is not supported)**. Field-tested error samples from mount validation:

- Mounting a skill in `checking` state → `400 AGENT_010 "Skill does not exist or is under security scanning: skill_xxx@1.0"`
- Mounting an active skill but writing version `9.9` → the same 400 (the error message concatenates `skill_id@version`, making it easy to spot which pair failed to match)

### 2.3 Runtime: how a skill actually gets "used" (event-stream field test)

Send a problematic manuscript (heading skips + banned phrases + an overlong paragraph) to the skill-mounted agent, and the event history shows the skill's working mechanism in full — **the most valuable field-test finding of this recipe**:

```
[05:03:33] tool_call        activate_skill  {"name": "manuscript-check"}
[05:03:33] tool_call_output {"name": "manuscript-check", "content": "<full SKILL.md text>"}
[05:03:44] tool_call        write           manuscript saved to /tmp/manuscript.txt
[05:03:47] tool_call        bash            "cd /root/workspace/skills/manuscript-check && python3 manuscript_check.py /tmp/manuscript.txt"
[05:03:47] tool_call_output the script's JSON result (6 issues)
[05:04:01] message          assistant       the synthesized review comments
```

Read it line by line:

1. **Skills are not pre-injected into the system prompt.** After the agent receives the message, the model itself decides to call a **hidden tool `activate_skill`**, whose argument is the skill name — only then does the full SKILL.md (the manual) enter the conversation context. The benefit is obvious: mounting ten skills still won't bloat the system prompt; loading is on demand.
2. **The zip is unpacked into the sandbox** at `/root/workspace/skills/<skill-name>/` (directory name = SKILL.md's name), and the script referenced in the manual runs directly via bash. So paths in SKILL.md's body should be written "relative to the skill directory" (the example above just uses `manuscript_check.py`); the agent `cd`s there itself first.
3. **The manual decides behavior; the script decides facts.** What the agent does with the script's JSON output is "organize + judge": in the field test, "Chapter 1 Introduction" triggered the mechanical match on the banned phrase "number one", and the agent handled it as — "chapter-numbering usage triggered the match; recommend confirming with the proofreader whether ordinal 'number one' counts as an exemption". **The script does the scanning; the model does the discretion** — that is the dividing line most worth thinking through when designing skills.

### 2.4 Version management (field-tested)

Upload a new version (`POST /skills/{skill_id}/versions`; the request body likewise holds only `file_id`):

```bash
# Edit SKILL.md (say, add "lowest price on the internet" to the banned list) -> repackage -> upload
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "$BASE/skills/skill_MWY3ZTY5ZDE3MGIzNDFkZWI2Zj/versions" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"file_id": "file_889syqcvxriijfzl5xe9kci9"}'
```

```json
{"id": "skillver_MTRiNWIwNDNiNWZjNDc5Y2", "version": null,
 "status": "checking", "type": "skill_version", "skill_id": "skill_MWY3...", ...}
```

Field-tested conclusions:

- **Version numbers auto-assigned in 0.1 steps**: `1.0` -> `1.1` -> `1.2`... (the create response's `version` is null, but the new version appears in the version list immediately);
- New versions likewise pass the security scan (checking -> active, duration on the same order as the initial release);
- **Mount pinning**: after new version `1.1` becomes active and `latest_version` advances, an agent already mounted on `1.0` is completely untouched (GET /agents re-verified `skills[0].version == "1.0"`). To move an agent to the new version you must explicitly update the agent config — the same philosophy as agent version pinning (01/03): **running things are immune to background changes**;
- The version list `GET /skills/{id}/versions` is ordered newest to oldest;
- `GET /skills/{id}/versions/{version}/content` returns an **OSS pre-signed download URL** — you can pull back the exact package you uploaded back then (an audit gem: skill content is traceable).

One practical note: stray files mixed into the skill package (say, a mistakenly packaged `SKILL_v2.md`) do not block upload, and review passes anyway — audit the package contents yourself before uploading; don't count on the review to gatekeep for you.

## 3. Operations and cleanup

```bash
# Status observation: the skill list (source filter: self-built vs. official)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "$BASE/skills?source=official&limit=10" -H "Authorization: Bearer $API_KEY"   # official marketplace skills
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "$BASE/skills" -H "Authorization: Bearer $API_KEY"                            # all

# Delete: hard delete, unrecoverable (skills have only DELETE, no archive)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X DELETE "$BASE/skills/skill_xxx" -H "Authorization: Bearer $API_KEY"        # 200
```

- **Skill deletion is a hard delete** — contrast: agent/deployment can only be archived, never deleted (the verb matrix in recipe 14 will update this row). Think it through before deleting: agents mounted on an old version lose their reference.
- Custom MCP's create/update/delete live in the console (no API); the skill CRUD lives in the API (fully tested in this recipe) — the two asset types have exactly opposite management entrances; don't mix them up.
- The `GET /skills` listing also shows the health of every skill under the workspace (including the official marketplace ones) — glance at it during inspections.

## 4. Summary

| You want | Use | Key actions |
|---|---|---|
| Platform built-in execution (bash / file I/O) | `builtin_toolkit` | recipe 01 |
| Generic public-internet services (search, document processing...) | marketplace MCP (`type: official`) | recipe 02 |
| **Your own MCP Server (knowledge base, business systems)** | **custom MCP (`type: customer`)** | **console registration (Script deployment -> HTTP deployment, registration-only, free) -> API mounting** |
| **Your team's operating procedures (checklists, scripts, templates)** | **custom Skill** | **package zip -> API upload -> pass review (minutes-scale) -> mount with pinned version** |

Remember the MCP/Skills division in one line: **MCP gives the agent "hands" (which services it can call); a Skill gives the agent an "SOP" (by which procedure it works)**. Luming's review assistant mounts both: the RAG MCP lets it query the editorial standards, and the manuscript-check skill lets it run the health check by the senior editors' three looks — hands and method together.

Engineering checklist (in priority order): write SKILL.md's description to say clearly "when to use" (the model routes on it) -> leave review-wait slack in the upload pipeline (field-tested ~4 minutes) -> mount pinned to a concrete version (never follow latest) -> write script paths in the manual as relative usages -> assess mounted references before deleting.

---

**Field-test quick reference for this recipe**: server-side SKILL.md frontmatter parsing; review took 3 minutes 59 seconds (checking -> active); version numbers auto-assigned in 0.1 steps; mount version pinning; the `activate_skill` on-demand injection mechanism; zip unpack path `/root/workspace/skills/<name>/`; `customer` MCP strictly validated at creation (400 original message in §1.3); hard skill deletion; the official/self-built skill `source` filter.
