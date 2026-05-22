---
name: alibabacloud-wxz-website-builder
description: Use when building or modifying websites with AI Staff (零号员工/万小智) via Alibaba Cloud OpenAPI. Supports conversation creation, async chat with requirement collection, PRD generation, code generation, and incremental SSE event polling.
---

Category: service

# AI Staff Website Builder (零号员工建站)

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
pip install alibabacloud_tea_openapi>=0.4.4 alibabacloud_tea_util>=0.3.14
```

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
Phase 3: Fire code generation → Show link → poll loop with progress → Site ready
```

## Phase 0: Auth Setup

Ensure Alibaba Cloud credentials are configured via the default credential chain (see Authentication section above).

## Phase 1: Create Conversation

**MUST** create a conversation before any chat operation:

```bash
CONV=$(python scripts/aistaff_api.py create-conversation --text "做个popmart首页")
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
  --text "做个popmart首页" \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID
```

Tell user: **"正在分析您的需求，请稍候..."**

### Step 2: Poll until first HITL form arrives

Call `poll` every 5 seconds until `phase` is `waiting_for_input`:

```bash
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --last-event-id 0
```

Between each poll, show the user a progress message based on `phase`:
- `processing` → "需求分析进行中..."
- `fetching_reference` → "正在获取参考网站信息..."
- `waiting_for_input` → First HITL form arrived, proceed to Step 3.

### Step 3: First HITL — collect answers from user

Extract `questions` from the `metaData.arguments` of the `message.tool` event where `name: "AskUserQuestion"`. Present these questions to the user via the AskUserQuestion tool (typically: app name, business description, target users, reference site).

### Step 4: Fire resume with `--phase generate_prd`

**CRITICAL**: On the first HITL resume, **always** pass `--phase generate_prd --user-navigation generate_prd`.

```bash
python scripts/aistaff_api.py chat \
  --text '{"应用名称": "POP MART 官网", "主营服务": "潮流玩具", "目标用户": "Z世代潮流青年", "参考网站": "无"}' \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --chat-id $CHAT_ID \
  --chat-status interrupt \
  --phase generate_prd \
  --user-navigation generate_prd \
  --hidden --without-refer
```

The `--text` JSON keys **MUST match the `header` values** from the form.

Tell user: **"已收到您的需求，正在生成产品方案..."**

### Step 5: Poll loop — auto-fill subsequent HITL rounds until PRD is ready

Poll every 5 seconds. Based on `phase` / `summary`, take action:

- `phase == "waiting_for_input"` (another HITL question) → **Auto-fill immediately** using the `answers` field from the `AskUserQuestion` event, then fire resume again. Tell user: **"正在完善需求细节..."**
- `phase == "generating_prd"` → Tell user: **"PRD 方案生成中，请稍候..."**
- `phase == "fetching_reference"` → Tell user: **"正在获取参考资料..."**
- `summary.chatStatus == "success"` + `summary.hasPrd == true` → PRD ready, proceed to Phase 3.
- `summary.chatStatus == "fail"` → Ask user whether to retry.

```bash
# Poll example:
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --last-event-id $LAST_EVENT_ID

# Auto-fill example (use the "answers" field from the AskUserQuestion event):
python scripts/aistaff_api.py chat \
  --text '{"核心功能": ["商品展示", "品牌故事", "新闻资讯"]}' \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --chat-id $CHAT_ID \
  --chat-status interrupt \
  --phase generate_prd \
  --user-navigation generate_prd \
  --hidden --without-refer
```

**Key rule**: The platform's `AskUserQuestion` event always includes an `answers` field with sensible defaults. For rounds after the first, always use these defaults directly instead of prompting the user.

## Phase 3: Code Generation

When PRD is ready:

### Step 1: Fire code generation

```bash
python scripts/aistaff_api.py chat \
  --text "确认生成应用" \
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

Tell user: **"代码生成已启动，通常需要 2-5 分钟。您可以先通过上面的链接查看项目，我会持续跟踪进度..."**

### Step 3: Poll loop with progress updates

Poll every 10 seconds. Show the user progress between each poll:

```bash
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --last-event-id $LAST_EVENT_ID
```

Progress messages to show (use `progressDetail` for rich messages):
- `phase == "processing"` + `progressDetail.latestFile` exists → "代码生成中...正在写入: {latestFile.semantic}（已生成 {filesWrittenCount} 个文件）"
- `phase == "processing"` + no `latestFile` → "代码生成中...已处理 N 个事件"
- `phase == "processing"` + `progressDetail.lastMessage` exists → Also show the assistant's latest message as context
- `phase == "success"` → Site is ready! Show link again.
- `phase == "fail"` → Ask user whether to retry.

### Step 4: Handle completion

- `summary.chatStatus == "success"` → Site is ready. Show site link again.
- `summary.chatStatus == "fail"` or `summary.hasError == true` → **Ask user** whether to retry. Do NOT auto-retry.

## After Initial Generation

* Use `chat` with `--conversation-id` to modify the site.
* Each modification uses the same chat + poll pattern.
* Show the site link again after each modification.

---

# Decision Table

| `summary.chatStatus` | `summary.hasPrd` | Phase | Action |
|----------------------|-------------------|-------|--------|
| `interrupt` | — | 2 (first round) | Parse AskUserQuestion, collect answers **from user**, resume with `--phase generate_prd` |
| `interrupt` | — | 2 (subsequent) | **Auto-fill** with default `answers` from the AskUserQuestion event, resume immediately — do NOT ask user |
| `success` | `true` | 2 | PRD ready → proceed to Phase 3 |
| `success` | `false` | 3 | Site is ready → show link |
| `fail` | — | any | Ask user whether to retry |
| `unknown` | — | any | Poll timed out → use `list-messages` fallback |

---

# Available Commands

## create-conversation

```bash
python scripts/aistaff_api.py create-conversation --text "用户问题"
```

Returns flat JSON: `{ConversationId, SiteId, ChatId, SectionId, BotId, Title}`.

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

**Returns JSON:**
```json
{
  "conversationId": "conv-xxx",
  "chatId": "chat-xxx",
  "status": "fired",
  "error": null
}
```

## poll

**Single-shot status check** — fetches new events once + checks message status, then returns immediately. Designed for agent-driven polling loops where the agent controls the pace and shows progress to the user between calls.

```bash
python scripts/aistaff_api.py poll --conversation-id <ID> --biz-id <ID> [--last-event-id N]
```

**Key parameters:**
- `--last-event-id N`: Cursor from previous poll (default: 0). Pass the `lastEventId` from the previous `poll` result to get only new events.
- `--max-output-events N`: Limit events in output (default: 10, 0=unlimited)

**Returns JSON:**
```json
{
  "conversationId": "conv-xxx",
  "lastEventId": 45,
  "newEvents": 3,
  "phase": "generating_prd",
  "summary": {
    "chatStatus": "processing",
    "hasError": false,
    "errorMsg": "",
    "hasPrd": false,
    "toolsCalled": ["FetchWebsiteInfo"]
  },
  "progressDetail": {
    "filesWrittenCount": 5,
    "activeTools": ["Write"],
    "latestFile": {
      "path": "/home/wuying/workspace/src/components/Hero.tsx",
      "semantic": "首页 Hero 轮播组件",
      "status": "wait"
    },
    "allFiles": [
      {"path": "/home/wuying/workspace/src/types/order.ts", "semantic": "订单类型定义"},
      {"path": "/home/wuying/workspace/src/components/Hero.tsx", "semantic": "首页 Hero 轮播组件"}
    ],
    "lastMessage": "好的，正在为您生成首页组件...",
    "toolProgress": [
      {"name": "Write", "status": "done", "semantic": "订单类型定义"},
      {"name": "Write", "status": "wait", "semantic": "首页 Hero 轮播组件"}
    ]
  },
  "events": ["(last 10 events)"]
}
```

**`progressDetail` fields** — use these to build informative progress messages:
- `filesWrittenCount`: Total number of files generated so far.
- `activeTools`: Tools currently in progress (status=`wait`). Empty when all tools have completed.
- `latestFile`: The most recent file being written — show `semantic` to the user (e.g. "正在生成: 首页 Hero 轮播组件").
- `allFiles`: Complete list of files written, each with `path` and `semantic`.
- `lastMessage`: Latest assistant text message (truncated to 200 chars).
- `toolProgress`: Per-tool status list with `name`, `status` (`wait`/`done`), and `semantic`.

**Suggested progress messages based on `progressDetail`:**
- If `latestFile` has `status == "wait"`: "正在生成: {latestFile.semantic}..."
- If `latestFile` has `status == "done"` and `activeTools` is empty: "已完成 {filesWrittenCount} 个文件，等待下一步..."
- If `filesWrittenCount > 0` and `activeTools` is not empty: "代码生成中...已生成 {filesWrittenCount} 个文件，正在写入: {latestFile.semantic}"
- If `lastMessage` is not empty: Show it as additional context.

**`phase` values:**
| Phase | Meaning | Suggested user message |
|-------|---------|----------------------|
| `processing` | General processing | "处理中..." |
| `fetching_reference` | Fetching reference site | "正在获取参考网站信息..." |
| `waiting_for_input` | HITL form ready | (parse form and handle) |
| `generating_prd` | PRD generation in progress | "PRD 方案生成中..." |
| `success` | Completed successfully | "完成!" |
| `fail` | Failed | (ask user whether to retry) |

## list-messages

Query the latest chat messages. Returns the last N messages (default: 10).

```bash
python scripts/aistaff_api.py list-messages --conversation-id <ID> [--tail 10]
```

**Key usage**: Use this to check `ChatStatus` of the last message when poll shows no progress.

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

---

# Complete Workflow Example

```bash
cd skills/ai/service/alibabacloud-wxz-website-builder

# Phase 1: Create conversation
CONV=$(python scripts/aistaff_api.py create-conversation --text "做个popmart首页")
CONV_ID=$(echo $CONV | jq -r '.ConversationId')
CHAT_ID=$(echo $CONV | jq -r '.ChatId')
SITE_ID=$(echo $CONV | jq -r '.SiteId')

# Phase 2 Step 1: Fire requirement collection
python scripts/aistaff_api.py chat \
  --text "做个popmart首页" \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID
# → Tell user: "正在分析您的需求，请稍候..."

# Phase 2 Step 2: Poll until first HITL form arrives
# (agent calls this every ~5s, shows progress between calls)
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --last-event-id 0
# → Check phase: "waiting_for_input" means form is ready

# Phase 2 Step 3: Parse AskUserQuestion → collect from user (FIRST round only)

# Phase 2 Step 4: Fire resume with user answers
python scripts/aistaff_api.py chat \
  --text '{"应用名称": "POP MART 官网", "主营服务": "潮流玩具", "目标用户": "Z世代潮流青年", "参考网站": "无"}' \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --chat-id $CHAT_ID \
  --chat-status interrupt \
  --phase generate_prd \
  --user-navigation generate_prd \
  --hidden --without-refer
# → Tell user: "已收到您的需求，正在生成产品方案..."

# Phase 2 Step 5: Poll loop (agent-driven, ~5s interval)
# - phase="waiting_for_input" → auto-fill with defaults, fire resume
#   → Tell user: "正在完善需求细节..."
# - phase="generating_prd" → Tell user: "PRD 方案生成中..."
# - summary.chatStatus="success" + summary.hasPrd=true → PRD ready, proceed

# Phase 3 Step 1: Fire code generation
python scripts/aistaff_api.py chat \
  --text "确认生成应用" \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --phase generate_code \
  --without-refer

# Phase 3 Step 2: Show link immediately
echo "Link: https://wanwang.aliyun.com/webdesign/home#/ai/manage/prd?conversationId=$CONV_ID"
# → Tell user: "代码生成已启动，通常需要 2-5 分钟..."

# Phase 3 Step 3: Poll loop with progress (~10s interval)
python scripts/aistaff_api.py poll \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID \
  --last-event-id $LAST_EVENT_ID
# → Use progressDetail.latestFile.semantic for rich messages
# → phase="success" → show link again, done!

# Modify site (optional, same chat+poll pattern)
python scripts/aistaff_api.py chat \
  --text "首页title改下" \
  --conversation-id $CONV_ID \
  --biz-id $SITE_ID
# → poll loop...
```
