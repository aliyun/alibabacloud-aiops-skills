---
name: alibabacloud-bailian-memory
description: |
  Manages conversation memories and user profiles in Alibaba Cloud Bailian (Model Studio)
  Memory Library via DashScope REST APIs. Covers memory extraction from conversations,
  direct content saving, semantic memory search, memory fragment maintenance,
  user profile queries and updates, plus memory project and profile schema administration.
  Use when the user requests memory library ("记忆库") operations
  such as "add memory", "search memory" or "user profile".
  Prerequisites: (1) Configure DashScope API Key (2) Activate Bailian Memory Library service.
  Do NOT use for Bailian RAG knowledge base retrieval or document search.
---

# Bailian Memory Library

Manage conversation memories and user profiles in Alibaba Cloud Bailian (Model Studio) Memory Library through DashScope REST APIs. The Memory Library automatically extracts key information from conversations and stores them as memory fragments, enabling agents to reference user preferences and historical context across sessions.

**Architecture:** `Agent → Python Scripts → DashScope REST API → Memory Library (Memories + User Profiles)`

**Scope:** This skill covers 12 memory and user-profile operations plus 7 management operations of the Memory Library (see Core Workflows). All memory writes are asynchronous: the request is accepted immediately and extraction runs in the background, returning an `event_id`. Memory projects (create/list/get/update) and profile schemas (create/list/update) are managed directly by this skill; project/schema deletion is not covered — use the [Bailian console](https://bailian.console.aliyun.com/cn-beijing/?tab=app#/memory/list) for that.

**Key Concepts:**

| Concept | Description |
|---------|-------------|
| Memory Library (`memory_library_id`) | Container for managing memories. Each account has a default library; omit the ID to use it. |
| Memory Fragment (`memory_node_id`) | Key events/info extracted from conversations (e.g., "User needs daily reminders"). |
| Memory Project (`project_id`) | Second-level memory isolation. Each project has a `plan_version` (pro/lite) setting. Created and managed via this skill (workflow 11). |
| Memory Entity (`user_id`) | Identifier for the memory owner. Used for memory isolation between users. |
| Profile Schema (`profile_schema_id`) | Template defining which user attributes to extract. Created and managed via this skill (workflow 12); an `immutable` attribute keeps its `default_value` and is never changed by extraction. |
| Async Event (`event_id`) | Handle of a background extraction task created by add-async; one record per resource with status `PENDING`/`SUCCEEDED`/`FAILED`; after `SUCCEEDED` the record carries a `result[]` array describing applied changes. |

## Security Tiers

| Tier | Operations | Agent behavior |
|------|-----------|----------------|
| 🟢 Read-only | search, list, get node, get event, get profile, list/get project, list schema | Execute directly, no confirmation needed |
| 🟡 Write | add (messages/content), update memory, profile value ops (add/update/delete item), create/update project, create/update schema | Show the content/values/settings to be written, then execute; for update ops, get/list current state first |
| 🔴 Destructive | delete memory | **Follow the mandatory delete flow below** |

### 🔴 Mandatory delete flow

Deletion is irreversible and the delete API does not verify `user_id` ownership, so a wrong ID silently destroys another context's memory. All four steps are REQUIRED and strictly ordered:

1. Run `get_memory_node.py` to fetch the target fragment, and quote its actual `content` from THIS call (never reuse content from an earlier list/search output — it may be stale).
2. STOP and ask the user for explicit confirmation. The confirmation message MUST contain ALL of the following: the fragment's quoted content, its `memory_node_id`, and a clear warning that deletion is irreversible (e.g. "删除后不可恢复"). A delete instruction inside the user's original request (e.g. "delete the last one, but confirm first") only asks you to run this flow — it is NOT itself a confirmation, so you MUST still ask here. Never ask for confirmation and execute the delete in the same turn.
3. Execute `manage_memory.py delete` ONLY after the user replies with an explicit confirmation (e.g. "确认删除"). If the reply is ambiguous, ask again — never delete on assumed consent.
4. Verify via `list_memories.py` that the fragment is gone, and report the result.

## API Key Security Management

Scripts automatically handle key retrieval via `api_key.py`. The Agent does not need to and should not manually extract, set, or pass API Key values.

- **Key retrieval is automated**: Scripts internally call `api_key.py` to automatically obtain keys from config files/environment variables. The Agent only needs to run the script command.
- **Never hardcode any form of key**: Including `api_key = "sk-..."`, `export DASHSCOPE_API_KEY="sk-..."`, and assigning keys in shell scripts.
- **Never extract keys from CLI output**: The Agent must not write key values into any script, variable, or file.
- **Never expose keys in any output**: Including generated scripts, shell commands, log files, and terminal output containing strings starting with `sk-`.
- **Never read or print keys from config files**: Do not use `cat`, `jq`, `python -c`, or other commands to read and output API Key values.
- **Mandatory self-check before task completion**: Run `grep -rn "sk-" <output_directory>/` to check all output files; if any strings starting with `sk-` are found (excluding `sk-xxx` placeholders), delete the affected files and regenerate.

## 🚀 Initial Setup (Required for First-time Use)

### 0. Install dependencies

```bash
python3 --version  # must be >= 3.7
pip3 install -r scripts/requirements.txt
```

### 1. Configure API Key

API Keys are managed by the unified `scripts/api_key.py` module, with the following retrieval priority:
1. Alibaba Cloud CLI config `~/.aliyun/config.json` current profile's `dashscope.api_key`
2. Environment variable `DASHSCOPE_API_KEY`
3. Auto-create and save when Alibaba Cloud CLI is available (`generate_api_key()`)

Manual environment variable configuration:
```bash
export DASHSCOPE_API_KEY=sk-xxx
```

| Item | Description |
|------|-------------|
| **Key Format** | `sk-xxx` (standard DashScope API Key) |
| **Not Supported** | `sk-sp-xxx` (Coding Plan Key, does not support memory services) |
| **Environment** | This skill targets the production gateway by default. The API key must belong to the **same environment as the endpoint** — a mismatched key returns 401 `InvalidApiKey` no matter how the request is formed |
| **Get Key** | Bailian console API-Key page (production environment by default; for pre-release testing, use the key issued by the corresponding environment) |

For API Key auto-create/delete via Alibaba Cloud CLI (`aliyun plugin install --names aliyun-cli-modelstudio --enable-pre`), see `references/related-commands.md`.

### 2. Activate Bailian Memory Library Service

**Before using this skill, the memory library service must be activated in the Bailian console:**

1. Visit [Bailian Memory Library page](https://bailian.console.aliyun.com/cn-beijing/?tab=app#/memory/list)
2. Click **"Activate Now"** and wait for the service to take effect (usually 1-2 minutes)

**Authentication:** All API calls use Bearer token, managed internally by `scripts/memory_client.py`.

**Endpoint:** Scripts call the production gateway by default:
`https://dashscope.aliyuncs.com/api/v2/apps/memory`. For testing against the pre-release environment, set `BAILIAN_MEMORY_BASE_URL` to the pre-release gateway URL — the API key must belong to the same environment as the endpoint.

## Parameter Confirmation

Confirm with the user only where a wrong value causes data loss or cross-user contamination; use documented defaults for tuning values (asking for every optional parameter creates needless friction):

| Must confirm | Why |
|--------------|-----|
| `user_id` | Wrong value writes/reads another user's memory silently |
| `memory_node_id` for update/delete | Update overwrites, delete destroys — irreversible on the wrong target |
| `content` / `messages` to be written | It becomes persistent memory |
| `op_type` + `item_id` for profile value ops | update/delete target an existing value item — show current values (get profile with need_detail) first |
| `profile_schema_id` | From list_profile_schemas or creation output; cannot be guessed |
| `attributes_operations` with op=delete | Removing a schema attribute affects extraction — show the current schema state first |

| Use defaults unless user specifies | Default |
|------------------------------------|---------|
| `memory_library_id` | Default library |
| `project_id` | Default project |
| `top_k` | 10 |
| `page_num` / `page_size` | 1 / 10 |

Never invent IDs. If an ID is unknown, list/query first or ask the user.

## Observability (MUST follow for every API call)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every DashScope REST API call MUST include the `User-Agent` header:**

```
User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-bailian-memory/{session-id}
```

Scripts read `SKILL_SESSION_ID` from the environment (default empty string) and include it in the User-Agent header automatically:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_content.py --user-id "user_123" --content "..."
```

## Data Contract

Fields passed between capabilities (do not mix them up — most are look-alike IDs):

| Field | Type | Produced by | Consumed by |
|-------|------|-------------|-------------|
| `memory_node_id` | string | search / list (after async extraction completes) | get node, update, delete |
| `event_id` | string | add_memory_messages / add_memory_content | get_event |
| `attribute_id` | string | get_user_profile (`attributes[].id`) | update_user_profile (profile value ops), manage_profile_schema update |
| `item_id` | integer | get_user_profile `--need-detail` (`value_items[].item_id`) | update_user_profile (op_type update/delete) |
| `profile_schema_id` | string | manage_profile_schema create/list | add_memory_messages (`--profile-schema`), get_user_profile, update_user_profile, manage_profile_schema update |
| `project_id` | string | manage_memory_project create/list | add_memory_messages, add_memory_content, search, list, manage_memory_project get/update |
| `memory_library_id` | string | **Bailian console** (not this skill) | all scripts (optional) |
| `user_id` | string | caller/business system | all memory & profile scripts (profile value ops take it as `--entity-id`) |

### Flows

- Async extract: `add_memory_messages` → `event_id` (fire-and-forget; `get_event` only on demand) → `list_memories`/`search_memory` to see results
- Async direct save: `add_memory_content` → `event_id` (same fire-and-forget semantics)
- Profile: `manage_profile_schema create` → `profile_schema_id` → `add_memory_messages(--profile-schema)` → `get_user_profile` → (correction needed) `get_user_profile --need-detail` for `attribute_id`/`item_id` → `update_user_profile` op
- Project: `manage_memory_project create` → `project_id` → `add_memory_messages(--project-ids)` / `search_memory(--project-id)`

### Constraints

- `project_id` ≠ `memory_library_id`: project is second-level isolation inside a library. Passing one as the other returns NotFound.
- `add_memory_messages`: `--project-id` and `--project-ids` are mutually exclusive.
- `add_memory_content`: binds to exactly one project — no `--project-ids`; no `--profile-schema` (profile extraction depends on conversation messages, which this mode does not take).
- `update_user_profile` operates on ONE value item per call: `--op-type add` appends `--value`; `--op-type update`/`delete` require `--item-id` from `get_user_profile --need-detail`. Invalid op_type values are rejected.
- `manage_profile_schema` update: `immutable` of an existing attribute cannot be changed; op=add with `immutable=true` requires `default_value`.

## Core Workflows

All scripts are in `scripts/` and print raw API JSON to stdout (errors go to stderr with non-zero exit). Prefix every command with `SKILL_SESSION_ID={session-id}`.

### Routing: pick the workflow by user intent

| User intent | Workflow |
|-------------|----------|
| "Remember what we discussed" / persist facts from a conversation | 1. add_memory_messages (LLM extraction) |
| "Save this exact text as a memory" / import a known note | 2. add_memory_content (verbatim, no extraction) |
| Answer a question that depends on user preferences/history | 4. search_memory FIRST, then answer citing results |
| Browse/audit what is stored for a user | 5. list_memories (→ 6. get node for one detail) |
| "That memory is wrong/outdated" | 6. get node → 7. update |
| "Forget this" / remove a memory | 8. 🔴 delete flow |
| "What do we know about this user?" (structured attributes) | 9. get profile |
| "His city/job in the profile is wrong" | 9. get profile `--need-detail` → 10. profile value op |
| Set up / adjust memory isolation ("create a project", "switch project to lite") | 11. manage projects |
| Define / adjust which user attributes to extract ("create a profile schema", "add an attribute") | 12. manage schemas |

### 1. Add Memory — extract from conversation, async (🟡, default write path)

Use to extract memories from conversation messages via LLM. Accepted immediately
(fire-and-forget); extraction runs in the background.

```bash
python3 scripts/add_memory_messages.py --user-id "<user_id>" \
  --messages '[{"role":"user","content":"I prefer Python"},{"role":"assistant","content":"Noted!"}]'
# Multi-project extraction
python3 scripts/add_memory_messages.py --user-id "<user_id>" --messages '<json>' --project-ids "p1,p2"
# Also extract user profile attributes (schema from workflow 12 or the console)
python3 scripts/add_memory_messages.py --user-id "<user_id>" --messages '<json>' --profile-schema "<schema_id>"
```

Output: `request_id`, `event_id`, `events[]` (initial status `PENDING`). `messages` supports roles `user`/`assistant`/`tool` and standard OpenAI `tool_calls`/`tool_call_id`.

### 2. Add Memory — save content as-is, async (🟡)

Use to store a known text directly without LLM extraction. Binds to exactly one
project; profile extraction is not available in this mode (it requires conversation messages).

```bash
python3 scripts/add_memory_content.py --user-id "<user_id>" --content "<text>"
```

Output: `request_id`, `event_id`, `events[]` with `resource_type` prefixed `custom_` (custom_observation).

### 3. Check Async Event (🟢, usually NOT needed)

Async writes are fire-and-forget — do NOT poll by default. Query only when
(a) the user explicitly asks to confirm the write, or (b) a later step depends
on extraction completion (e.g. immediately searching the just-written content).

```bash
python3 scripts/get_event.py --event-id "<event_id>"
```

Output: one record per resource; `status` is `PENDING`/`SUCCEEDED`/`FAILED`. On `FAILED`, read the record's `detail` field (`errorCode: errorMessage`) and report it to the user — do not silently retry. After `SUCCEEDED` each record carries a `result[]` array describing the applied changes (`content`, `event` ADD/UPDATE/DELETE, `memory_node_id` for observation memories, `old_content` for updates); for full fragment details use list/search.

### 4. Search Memory (🟢)

```bash
python3 scripts/search_memory.py --user-id "<user_id>" --query "<search_text>"
python3 scripts/search_memory.py --user-id "<user_id>" --query "<text>" --top-k 5
```

Output: `request_id`, `plan_version`, `memory_nodes[]` (`memory_node_id`, `content`, `memory_type`, `score`, `status`, timestamps). Results are already relevance-filtered server-side (plan_version=pro, min_score=0.3 — tuning and billing parameters are server-controlled and not adjustable here). If no results, report that plainly; do not retry with rephrased queries more than once.

### 5. List Memories (🟢)

```bash
python3 scripts/list_memories.py --user-id "<user_id>" --page-num 1 --page-size 10
```

Output: `memory_nodes[]`, `total`, `page_size`, `page_num`.

### 6. Get Memory Node (🟢)

```bash
python3 scripts/get_memory_node.py --memory-node-id "<memory_node_id>"
```

Output: `memory_node` with full detail (`content`, `memory_type`, `status`, `meta_data`, ...). Always use this to show the target before update/delete confirmation.

### 7. Update Memory (🟡)

Overwrites the fragment content. Show old (via get) and new content before executing.

```bash
python3 scripts/manage_memory.py update --memory-node-id "<id>" --user-id "<user_id>" --content "<new_content>"
```

Output: `request_id`. `--meta-data` merges incrementally (unspecified keys remain unchanged).

### 8. Delete Memory (🔴)

Follow the mandatory delete flow in Security Tiers — get, confirm, delete, verify.

```bash
python3 scripts/get_memory_node.py --memory-node-id "<id>"        # 1. fetch & quote target content
# 2. STOP — quote content + memory_node_id, warn that deletion is irreversible,
#    and wait for the user's explicit confirmation (a prior "delete X" instruction is NOT a confirmation)
python3 scripts/manage_memory.py delete --memory-node-id "<id>"   # 3. run ONLY after user confirms
python3 scripts/list_memories.py --user-id "<user_id>"            # 4. verify
```

### 9. Get User Profile (🟢)

```bash
python3 scripts/get_user_profile.py --user-id "<user_id>" --profile-schema-id "<schema_id>"
# Expand value_items (each with item_id, consumed by workflow 10 update/delete)
python3 scripts/get_user_profile.py --user-id "<user_id>" --profile-schema-id "<schema_id>" --need-detail
```

Output: `profile` with `schema_name`, `schema_description`, `attributes[]`. Default mode joins values into one string per attribute (`id`, `name`, `value`; `value` is null until extracted); `--need-detail` returns `value_items[]` (`item_id`, `value`, `status`) per attribute instead. Profile data accumulates over multiple conversations — an empty value is normal early on, not an error. The `id` field is the `attribute_id` used by workflow 10.

### 10. Update User Profile Value (🟡)

Operates on ONE value item per call. Use when the user explicitly states new facts
that should correct the profile. Show current values (via get `--need-detail`) and
the intended change before executing.

```bash
# Add a new value item (no item_id needed)
python3 scripts/update_user_profile.py --entity-id "<user_id>" --profile-schema-id "<schema_id>" \
  --attribute-id "<attr_id>" --op-type add --value "swimming"
# Update an existing value item (item_id from get --need-detail)
python3 scripts/update_user_profile.py --entity-id "<user_id>" --profile-schema-id "<schema_id>" \
  --attribute-id "<attr_id>" --op-type update --item-id 5634 --value "volleyball"
# Delete an existing value item
python3 scripts/update_user_profile.py --entity-id "<user_id>" --profile-schema-id "<schema_id>" \
  --attribute-id "<attr_id>" --op-type delete --item-id 5634
```

Output: `request_id`. Other value items remain unchanged; verify via `get_user_profile.py --need-detail`.

### 11. Manage Memory Projects (🟢 list/get, 🟡 create/update)

```bash
# Create
python3 scripts/manage_memory_project.py create --name "observation-project" \
  --plan-version pro --expired-in-days 30
# List / detail
python3 scripts/manage_memory_project.py list
python3 scripts/manage_memory_project.py get --project-id "<project_id>"
# Update (at least one updatable field required)
python3 scripts/manage_memory_project.py update --project-id "<project_id>" --plan-version lite
```

Output: create returns `project_id`; list/get return project detail incl. `plan_version`. Before update, run get and show current settings — PATCH overwrites each provided field, so the user must see the values being replaced to give informed confirmation.

### 12. Manage Profile Schemas (🟢 list, 🟡 create/update)

```bash
# Create (an attribute with immutable=true requires default_value)
python3 scripts/manage_profile_schema.py create --name "basic-user-profile" \
  --attributes '[{"name":"Name","immutable":true,"default_value":"Zhang San"},{"name":"Hobbies"}]'
# List
python3 scripts/manage_profile_schema.py list
# Update (attribute changes via attributes-operations; op=update/delete require attribute_id)
python3 scripts/manage_profile_schema.py update --profile-schema-id "<schema_id>" \
  --attributes-operations '[{"op":"add","name":"Favorite Music"},{"op":"delete","attribute_id":"<attr_id>"}]'
```

Output: create returns `profile_schema_id`; list returns `profile_schemas[]` (`profile_schema_id`, `name`, `description`, `plan_version`). attribute_id for update/delete ops comes from `get_user_profile` output (`attributes[].id`). Before an update with op=delete, show the current schema attributes.

## Result Presentation

- Answering scenarios: cite memory `content` in natural language ordered by `score`; do not expose `memory_node_id` or other internal IDs.
- Management scenarios (user wants to update/delete/audit): list `memory_node_id` alongside content, since the user needs the ID to act.
- Empty search results: state plainly that nothing was found; never fabricate memories.

## Usage Example

**User:** "Customer customer_zhang_001 is reaching out again. Check what preferences I should keep in mind, and after the chat save the key points of this conversation."

**Flow:**

1. Recall first — `search_memory.py --user-id customer_zhang_001 --query "communication preferences service restrictions"` → 2 nodes: "Prefers communication in Chinese" (score 0.71), "Refuses marketing pushes" (score 0.65)
2. Answer citing content by score: "This customer prefers communicating in Chinese and explicitly refuses marketing pushes — avoid promotional pitches in this conversation." (no internal IDs shown)
3. After the conversation — `add_memory_messages.py --user-id customer_zhang_001 --messages '<conversation JSON of this round>'` → returns `event_id`, fire-and-forget, no polling
4. Report: "Memory extraction for this conversation has been submitted (processing in the background)." — only if the user asks "Is it saved?" run `get_event.py` and report per-resource status.

## Error Handling

| Error | Cause → Action |
|-------|----------------|
| 401 `InvalidApiKey` | Key invalid/unconfigured, or a key whose environment does not match the endpoint (e.g. a pre-release key against the production gateway) → guide user through Initial Setup step 1 |
| 403 `Forbidden` | Memory service not activated → guide user through Initial Setup step 2; if it occurs during API key auto-creation, check RAM permissions per `references/ram-policies.md` |
| 404 `NotFound` | Wrong `memory_node_id`/`event_id`/`profile_schema_id`, or `project_id` passed as `memory_library_id` → re-check via list/get |

For other codes see `references/error-handling.md`. Do not guess error meanings; report the API message as returned.

## Success Verification

After completing workflows, verify using commands in `references/verification-method.md`.

**Quick checklist:**
- [ ] API key authentication successful (no 401 errors)
- [ ] Async extract (messages) — `event_id` returned; extracted fragments visible via list/search afterwards
- [ ] Async direct save (content) — `event_id` returned with `custom_*` resource_type
- [ ] Search returns relevant results with `score`/`memory_type`/`plan_version`
- [ ] Node get shows the expected fragment detail
- [ ] Update modifies content (verify via get)
- [ ] Deletion removes fragment (verify via list)
- [ ] User profile contains extracted attributes (may need multiple conversations)
- [ ] Profile value op reflected in a subsequent get `--need-detail` (added/updated/deleted item)
- [ ] Project create returns `project_id`; update reflected in a subsequent get
- [ ] Schema create returns `profile_schema_id`; attribute operations reflected in extraction behavior

## Cleanup

```bash
# List to get IDs, then delete each (follow the 🔴 delete flow)
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py --user-id "<user_id>"
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory.py delete --memory-node-id "<memory_id>"
```

## Best Practices

1. **Use meaningful `user_id` values** — descriptive identifiers (e.g., `customer_12345`) make memory ownership auditable.
2. **Writes are asynchronous** — extraction runs in the background, so a write returns an `event_id` rather than the extracted fragments. Choose by intent: extract from conversation → `add_memory_messages.py`; store known text as-is → `add_memory_content.py`. To confirm a write, check the event or verify via list/search.
3. **Batch per conversation round** — add memories per round rather than concatenating everything into one call, to preserve memory granularity.
4. **Handle rate limits** — SearchMemory 300 QPM, all endpoints combined 3000 QPM. The client auto-retries with backoff; for bulk operations, add delays between calls.
5. **Search with specific queries** — targeted query text with `top_k` 3-10 beats broad terms; the server already filters low-relevance results.
6. **Profile data accumulates** — do not expect all attributes from a single conversation; empty values early on are normal.
7. **Prefer defaults for management settings** — when creating projects/schemas, only set `plan_version`/`instruction_type` when the user explicitly requires them; server defaults (pro/default) fit most cases.
8. **API key security** — retrieval is fully automated via `scripts/api_key.py`; never hardcode, export, extract, or expose key values.

## Reference Links

| Reference | Contents |
|-----------|----------|
| `references/api-endpoints.md` | Detailed documentation for the 16 REST API endpoints used by this skill |
| `references/error-handling.md` | Error codes, retry strategies, and troubleshooting guide |
| `references/ram-policies.md` | RAM permissions required for API Key auto-create/delete via CLI |
| `references/verification-method.md` | Success verification steps per workflow |
| `references/acceptance-criteria.md` | Test acceptance criteria and correct patterns |
| `references/related-commands.md` | Complete command reference for all scripts |
| [Bailian Console](https://bailian.console.aliyun.com/) | Obtain DASHSCOPE_API_KEY; delete profile schemas & memory projects |
| [Memory Library Docs](https://help.aliyun.com/zh/model-studio/memory-library) | Official product documentation |
| [Memory API Reference](https://help.aliyun.com/zh/model-studio/long-term-memory-api-reference) | Official API reference |
