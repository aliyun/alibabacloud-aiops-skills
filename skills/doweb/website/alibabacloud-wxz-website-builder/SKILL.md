---
name: alibabacloud-wxz-website-builder
description: Use when building or modifying websites with AI Staff via Alibaba Cloud OpenAPI. Supports conversation creation, async chat with requirement collection, PRD generation, code generation, and incremental SSE event polling.
---

Category: service

# AI Staff Website Builder

## Validation

```bash
mkdir -p output/alibabacloud-wxz-website-builder
for f in skills/ai/service/alibabacloud-wxz-website-builder/scripts/*.py; do
  python3 -m py_compile "$f"
done
echo "py_compile_ok" > output/alibabacloud-wxz-website-builder/validate.txt
```

Pass criteria: command exits 0 and `output/alibabacloud-wxz-website-builder/validate.txt` is generated.

## Output And Evidence

- Save list/summarize outputs under `output/alibabacloud-wxz-website-builder/`.
- Keep conversation IDs and event summaries in each evidence file.

## Prerequisites

```bash
pip install -r requirements.txt
```

- All dependencies are pinned to exact versions in `requirements.txt`.
- Credentials are resolved via the default credential chain (no explicit AK/SK needed).

## Authentication

This skill relies on the Alibaba Cloud default credential chain. Do NOT set AK/SK explicitly. The SDK automatically resolves credentials in the following order:

1. Environment variables: `ALIBABACLOUD_ACCESS_KEY_ID` / `ALIBABACLOUD_ACCESS_KEY_SECRET`
2. Shared config file: `~/.alibabacloud/credentials`
3. RAM role / ECS metadata service (when running on Alibaba Cloud instances)

Region: `ALIBABACLOUD_REGION_ID` defaults to `cn-hangzhou`.

### How to obtain AccessKey (if user doesn't have one)

If the user has no AccessKey yet, guide them through these steps (see `references/ak-setup-guide.md` for full details):

1. **Login**: Open https://www.aliyun.com and log in (or register)
2. **Create RAM user**: Go to https://ram.console.aliyun.com/users → "Create User" → check "OpenAPI Access" → save the AK/SK immediately (Secret is only shown once!)
3. **Grant permissions**: Add a custom policy with the following Actions (least-privilege):
   - `zero2staff:CreateAIStaffConversation`
   - `zero2staff:CreateAIStaffChat`
   - `zero2staff:ListAIStaffChatEvents`
   - `zero2staff:ListAIStaffChatMessages`
   - `zero2staff:GetAIStaffPreviewUrl`
4. **Configure**: Write to `~/.alibabacloud/credentials` or set environment variables

**CRITICAL**: When guiding the user, remind them:
- Do NOT use root account AccessKey — always use RAM sub-user
- Save the AccessKey Secret immediately — it's only shown once during creation
- Never commit AccessKey to git

If the user encounters auth errors, refer to the troubleshooting table in `references/ak-setup-guide.md`.

---

# Application Lifecycle

The complete flow has 3 phases. Follow them **sequentially**.

**IMPORTANT — Agent-driven polling**: The `chat` command fires the request and returns immediately. The **agent** then drives the polling loop via the `poll` command. Between each poll, the agent **MUST** show the user a progress message so they know what's happening (use `progressDetail` for rich messages).

```
Phase 1: Create Conversation
        ↓
Phase 2: Fire requirement chat → poll → HITL → Fire resume → poll → ... → PRD ready
        ↓
Phase 3: Fire code generation → Show link → poll loop with progress → Get preview URL → Done
```

## Phase 0: Auth Setup

Ensure Alibaba Cloud credentials are configured via the default credential chain (see Authentication section above).

## Phase 1: Create Conversation

**MUST** create a conversation before any chat operation:

```bash
CONV=$(python scripts/aistaff_api.py create-conversation --text "build a popmart homepage")
CONV_ID=$(echo $CONV | jq -r '.ConversationId')
CHAT_ID=$(echo $CONV | jq -r '.ChatId')
SITE_ID=$(echo $CONV | jq -r '.SiteId')
```

Returns flat JSON: `{ConversationId, SiteId, ChatId, SectionId, BotId, Title}`.

## Phase 2: Requirement Collection + PRD

This phase collects requirements and generates a PRD. The platform may ask multiple HITL rounds (basic info → features → language, etc.). To keep things fast:

- **Only the first HITL round** should be shown to the user (basic project info).
- **All subsequent HITL rounds** must be auto-filled with the form's default/pre-selected values and resumed immediately — do NOT ask the user.

### Step 1: Fire requirement collection

```bash
python scripts/aistaff_api.py chat \
  --text "build a popmart homepage" \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID
```

Tell user: **"Analyzing your requirements, please wait..."**

### Step 2: Poll until first HITL form arrives

Call `poll` every 5 seconds until `phase` is `waiting_for_input`:

```bash
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --last-event-id 0
```

Between each poll, show the user a progress message based on `phase`:
- `processing` → "Analyzing requirements..."
- `fetching_reference` → "Fetching reference site info..."
- `waiting_for_input` → First HITL form arrived, proceed to Step 3.

### Step 3: First HITL — collect answers from user

Extract `questions` from the `metaData.arguments` of the `message.tool` event where `name: "AskUserQuestion"`. Present these questions to the user via the AskUserQuestion tool (typically: app name, business description, target users, reference site).

### Step 4: Fire resume with `--phase generate_prd`

**CRITICAL**: On the first HITL resume, **always** pass `--phase generate_prd --user-navigation generate_prd`.

```bash
python scripts/aistaff_api.py chat \
  --text '{"App Name": "POP MART Official", "Main Service": "Trendy Toys", "Target Users": "Gen Z trendsetters", "Reference Site": "None"}' \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --chat-id $CHAT_ID \
  --chat-status interrupt \
  --phase generate_prd \
  --user-navigation generate_prd \
  --hidden --without-refer
```

The `--text` JSON keys **MUST match the `header` values** from the form.

Tell user: **"Requirements received, generating product plan..."**

### Step 5: Poll loop — auto-fill subsequent HITL rounds until PRD is ready

Poll every 5 seconds. Based on `phase` / `summary`, take action:

- `phase == "waiting_for_input"` (another HITL question) → **Auto-fill immediately** using the `answers` field from the `AskUserQuestion` event, then fire resume again. Tell user: **"Refining requirement details..."**
- `phase == "generating_prd"` → Tell user: **"Generating PRD, please wait..."**
- `phase == "fetching_reference"` → Tell user: **"Fetching reference materials..."**
- `summary.chatStatus == "success"` + `summary.hasPrd == true` → PRD ready, proceed to Phase 3.
- `summary.chatStatus == "fail"` → Ask user whether to retry.

```bash
# Poll:
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID --biz-id $SITE_ID --last-event-id $LAST_EVENT_ID

# Auto-fill (use the "answers" field from the AskUserQuestion event):
python scripts/aistaff_api.py chat \
  --text '{"Core Features": ["Product Showcase", "Brand Story", "News"]}' \
  --conversation-id $CONV_ID --biz-id $SITE_ID --chat-id $CHAT_ID \
  --chat-status interrupt --phase generate_prd \
  --user-navigation generate_prd --hidden --without-refer
```

**Key rule**: The platform's `AskUserQuestion` event always includes an `answers` field with sensible defaults. For rounds after the first, always use these defaults directly instead of prompting the user.

## Phase 3: Code Generation

When PRD is ready:

### Step 1: Fire code generation

```bash
python scripts/aistaff_api.py chat \
  --text "Confirm app generation" \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --phase generate_code \
  --without-refer
```

### Step 2: Show site link immediately

**MUST show before and after code generation:**

```
https://wanwang.aliyun.com/webdesign/home#/ai/manage/prd?conversationId=<CONV_ID>
```

Tell user: **"Code generation started. This typically takes 2-5 minutes. You can check the project via the link above while I track the progress..."**

### Step 3: Poll loop with progress updates

Poll every 10 seconds. Show the user progress between each poll:

```bash
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID --biz-id $SITE_ID --last-event-id $LAST_EVENT_ID
```

Progress messages (use `progressDetail` for rich messages):
- `phase == "processing"` + `latestFile` exists → "Generating code... Writing: {latestFile.semantic} ({filesWrittenCount} files generated)"
- `phase == "processing"` + no `latestFile` → "Generating code... N events processed"
- `phase == "processing"` + `lastMessage` exists → Also show the assistant's latest message as context
- `phase == "success"` → Site is ready! Proceed to Step 4.
- `phase == "fail"` → Ask user whether to retry.

### Step 4: Get preview URL

**MUST** call this after code generation completes (`summary.chatStatus == "success"`). Starts the preview sandbox and returns the live preview URL.

```bash
PREVIEW=$(python scripts/aistaff_api.py get-preview-url --conversation-id $CONV_ID)
PREVIEW_URL=$(echo $PREVIEW | jq -r '.urlMap.https // .urlMap.http // empty')
```

Tell user: **"Site built! Getting preview URL..."**

The first call may take a few seconds as the sandbox starts up. If the preview URL is not yet available, retry after 10 seconds (up to 3 retries). Show the preview URL: **"Preview URL: {PREVIEW_URL}"**

**`--restart`**: Pass `--restart` to restart the app in the sandbox (e.g., after a modification). Not needed for the initial build.

### Step 5: Handle completion

- `summary.chatStatus == "success"` → Site is ready. Show site link + preview URL.
- `summary.chatStatus == "fail"` or `summary.hasError == true` → **Ask user** whether to retry. Do NOT auto-retry.

## After Initial Generation

* Use `chat` with `--conversation-id` to modify the site.
* Each modification uses the same chat + poll pattern.
* After each modification completes, call `get-preview-url --restart` to refresh the preview.
* Show the site link + preview URL again after each modification.

---

# Decision Table

| `summary.chatStatus` | `summary.hasPrd` | Phase | Action |
|----------------------|-------------------|-------|--------|
| `interrupt` | — | 2 (first round) | Parse AskUserQuestion, collect answers **from user**, resume with `--phase generate_prd` |
| `interrupt` | — | 2 (subsequent) | **Auto-fill** with default `answers` from the AskUserQuestion event, resume immediately — do NOT ask user |
| `success` | `true` | 2 | PRD ready → proceed to Phase 3 |
| `success` | `false` | 3 | Site is ready → call `get-preview-url` → show link + preview URL |
| `fail` | — | any | Ask user whether to retry |
| `unknown` | — | any | Poll timed out → use `list-messages` fallback |

---

# Available Commands

## create-conversation

```bash
python scripts/aistaff_api.py create-conversation --text "user question"
```

Returns: `{ConversationId, SiteId, ChatId, SectionId, BotId, Title}`.

## chat

Fire an async chat message and return immediately. Automatically drains old SSE events before firing. Use `poll` afterwards to track progress.

```bash
python scripts/aistaff_api.py chat --text "description" --conversation-id <ID> --biz-id <ID> [options]
```

**Key parameters:**
- `--text TEXT`: Message text or form answers JSON (required)
- `--conversation-id ID` / `--biz-id ID`: Required identifiers
- `--chat-id ID` + `--chat-status interrupt`: For HITL resume
- `--phase {requirement_collect,generate_prd,generate_code}`: Phase to enter
- `--user-navigation TARGET`: Navigation target (use `generate_prd` with `--phase generate_prd`)
- `--hidden` / `--without-refer`: Hide message / skip reference context
- `--verbose`: Show debug info

Returns: `{conversationId, chatId, status: "fired", error}`.

## poll

**Single-shot status check** — fetches new events once + checks message status, then returns immediately. Designed for agent-driven polling loops.

```bash
python scripts/aistaff_api.py poll --conversation-id <ID> --biz-id <ID> [--last-event-id N]
```

**Key parameters:**
- `--last-event-id N`: Cursor from previous poll (default: 0). Pass the `lastEventId` from the previous `poll` result.
- `--max-output-events N`: Limit events in output (default: 10, 0=unlimited)

**Returns:** `{conversationId, lastEventId, newEvents, phase, summary, progressDetail, events}`

**`summary` fields:** `chatStatus`, `hasError`, `errorMsg`, `hasPrd`, `toolsCalled`

**`progressDetail` fields** — use these to build informative progress messages:
- `filesWrittenCount`: Total files generated so far
- `activeTools`: Tools currently in progress (status=`wait`). Empty when all completed
- `latestFile`: `{path, semantic, status}` — most recent file being written (show `semantic` to user)
- `allFiles`: Complete list of files written, each with `path` and `semantic`
- `lastMessage`: Latest assistant text message (truncated to 200 chars)
- `toolProgress`: Per-tool status list with `name`, `status` (`wait`/`done`), `semantic`

**Suggested progress messages:**
- `latestFile.status == "wait"`: "Generating: {latestFile.semantic}..."
- `latestFile.status == "done"` + `activeTools` empty: "{filesWrittenCount} files completed, waiting for next step..."
- `filesWrittenCount > 0` + `activeTools` not empty: "Generating code... {filesWrittenCount} files done, writing: {latestFile.semantic}"
- `lastMessage` not empty: Show it as additional context

**`phase` values:**
| Phase | Meaning | Suggested user message |
|-------|---------|----------------------|
| `processing` | General processing | "Processing..." |
| `fetching_reference` | Fetching reference site | "Fetching reference site info..." |
| `waiting_for_input` | HITL form ready | (parse form and handle) |
| `generating_prd` | PRD generation in progress | "Generating PRD..." |
| `success` | Completed successfully | "Done!" |
| `fail` | Failed | (ask user whether to retry) |

## list-messages

Query the latest chat messages. Returns the last N messages (default: 10).

```bash
python scripts/aistaff_api.py list-messages --conversation-id <ID> [--tail 10]
```

**Key usage**: Use this to check `ChatStatus` of the last message when poll shows no progress.

## get-preview-url

Get the live preview URL after code generation. Starts the sandbox if needed.

```bash
python scripts/aistaff_api.py get-preview-url --conversation-id <ID> [--restart]
```

**Parameters:** `--conversation-id ID` (required), `--restart` (restart app in sandbox, useful after modifications)

**Returns:** `{urlMap: {https: "...", http: "...", sessionId: "..."}}`

**MUST** call after `chatStatus == "success"` in Phase 3. First call may take a few seconds (sandbox startup). If URL is empty, retry after 10s (up to 3 retries).

---

# SSE Event Constraints

- Each new chat round may wipe previous SSE events. The `chat` command **automatically drains** old events before firing.
- When using `poll`, pass the `lastEventId` from the previous poll result to avoid re-processing events.
- During code generation, the platform may auto-trigger multiple "magic fix" rounds. The `poll` command detects this via event summary.

---

# Error Handling

| Error | Action |
|-------|--------|
| Auth error | Ensure credentials are configured via default credential chain (env vars, config file, or RAM role) |
| `summary.chatStatus == "fail"` | **Ask user** whether to retry. Do NOT auto-retry |
| Poll shows no progress for 5+ minutes | Use `list-messages` to check actual status |
