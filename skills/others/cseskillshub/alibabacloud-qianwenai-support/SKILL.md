---
name: alibabacloud-qianwenai-support
description: |
  Create, track, and manage QianWen support tickets from the conversation:
  submit a new ticket, check ticket status and engineer replies, follow up,
  close, and rate — so platform issues get resolved without leaving the chat.
  Triggers: "submit ticket", "create ticket", "list tickets", "view ticket",
  "reply ticket", "close ticket", "rate ticket", "transfer to human",
  "work order", "customer service", "human support", "open ticket",
  "check ticket", "cancel ticket", "evaluate ticket", "ticket list",
  "support request", "escalate to agent".
  Do NOT use for general model usage questions, API Key management,
  or billing inquiries — only when the user explicitly needs ticket operations.
compatibility: Works with a QianWen account authenticated via `qianwen auth login` (CLI device flow) or the `QIANWEN_ACCESS_TOKEN` environment variable.
metadata:
  version: "1.1"
  api_version: "1.0"
  keywords:
    - ticket
    - work order
    - support
    - customer service
    - transfer to human
    - qianwen support
    - qianwenai
    - submit ticket
    - create ticket
    - list tickets
    - view ticket
    - reply ticket
    - close ticket
    - rate ticket
---

# QianWen Support Ticket Management

Manage QianWen support tickets through the full lifecycle: create, list, view, reply, close, and rate. Auto-diagnoses common issues before creating tickets to avoid unnecessary submissions.

## Execution Principle

1. **Diagnose before ticket**: Run auto-diagnosis first; only create a ticket if auto-resolve fails or the issue is clearly a platform bug.
2. **User confirmation**: Always display the ticket draft and get explicit user confirmation before submitting.
3. **Terminal status guard**: NEVER reply to or close tickets in terminal status (closed/resolved/confirmed).
4. **Verbatim relay**: Customer service replies must be relayed verbatim — no summarizing, paraphrasing, or editing.

## Credentials

| Backend | Auth Method | Token Source |
|---------|------------|--------------|
| CLI | `qianwen auth login` (browser device flow) | system credential store |
| API | Bearer token | env `QIANWEN_ACCESS_TOKEN` or system credential store |

**NEVER output any credential value in plaintext.** Report only status (authenticated / expired).

**Alibaba Cloud AK/SK NOT supported:** Alibaba Cloud main-account or RAM sub-account AccessKeys (and STS tokens) CANNOT authenticate the QianWen CLI or the workorder API. A Bailian API Key (`sk-...`) works for model API calls only, NOT for ticket management.

### Two Credential Systems — Never Confuse

| Credential | Purpose | How to provide |
|------------|---------|----------------|
| **API Key** (`sk-...`) | Call model APIs in code | `$DASHSCOPE_API_KEY` env var |
| **CLI session** | Authorize CLI/API subcommands | `qianwen auth login` |

**Red line:** Never offer `$DASHSCOPE_API_KEY` to fix CLI/API `AUTH_REQUIRED` errors.

## Authentication Flow (TL;DR)

When `doctor` reports not authenticated, guide the user through this flow:

1. `qianwen auth status --format json` -> `authenticated: true` -> skip to commands
2. `qianwen auth login --init-only --format json` -> extract `verification_url` -> open in browser
3. `qianwen auth login --complete --format json` -> poll until `success` event

> **Full procedure** (two-phase login, JSON events, TTY handling): load `references/auth-flow.md`.

**Unauthenticated user guidance:** When neither CLI session nor API token is available, inform the user:
- CLI path: run `qianwen auth login` (opens browser device flow), then retry
- API path: set `QIANWEN_ACCESS_TOKEN` environment variable
- NEVER attempt ticket operations without valid credentials

## User Confirmation

**MANDATORY before any state-changing action:** creating, replying to, closing, or rating a ticket requires explicit user confirmation.

1. **Create**: display the full ticket draft (title, category, description) and wait for explicit confirmation. Never submit without it.
2. **Reply**: draft the reply from user instructions and get confirmation before submitting.
3. **Close / Rate**: state the target ticket ID and the action, then confirm before executing.

Read-only operations (doctor, list, view, categories) need no confirmation.

## Trigger Conditions

| Trigger Phrase | Action |
|---------------|--------|
| "submit ticket" / "create ticket" / "submit work order" | Create new ticket |
| "list tickets" / "view my tickets" | List tickets |
| "view ticket <id>" / "check ticket status" | View ticket detail |
| "reply ticket" / "respond to ticket" | Reply to ticket |
| "close ticket" / "cancel ticket" | Close/cancel ticket |
| "rate ticket" / "evaluate ticket" | Rate resolved ticket |
| "transfer to human" / "human support" | Create ticket (escalation) |
| "ticket" / "work order" with issue context | Create ticket after diagnosis |

**Do NOT trigger for:**
- General model usage questions (e.g., "how to call qwen-plus")
- API Key management (e.g., "my API key expired")
- Vague feedback without ticket intent (e.g., "product experience is bad")

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--backend` | No | `auto` (default), `cli`, or `api` |
| `--ticket-id` | For view/reply/close/rate | Ticket ID (e.g., `0005PYGCW`) |
| `--category-id` | For create | Category ID (fetch dynamically) |
| `--description` | For create | Ticket description (max 2000 chars) |
| `--message` | For reply | Reply content |
| `--rating` | For rate | 0 (unsatisfied), 1 (neutral), 2 (satisfied) |
| `--comment` | For rate | Optional rating comment |
| `--page` | For list | Page number (default: 1) |
| `--page-size` | For list | Items per page (default: 10, max: 10) |

## Module Index

| File | Purpose |
|------|---------|
| `scripts/qianwen_support.py` | Entry script — all ticket operations |
| `references/auth-flow.md` | Full authentication procedure |
| `references/ticket-categories.md` | Category ID listing (Model / App groups) |
| `references/category-selection.md` | Category selection strategy and runtime refresh |
| `references/api-reference.md` | QianWen HTTP API documentation |
| `references/ram-policies.md` | RAM permission declaration (none required) |

## Orchestration

```
User request
    │
    ▼
┌─────────────────────────────────┐
│  Step 1: Pre-flight (silent)    │
│  python3 scripts/               │
│    qianwen_support.py doctor    │
└─────────────┬───────────────────┘
              ▼
┌─────────────────────────────────┐
│  Step 2: Auto-Diagnosis         │
│  Resolve common issues first    │
└─────────────┬───────────────────┘
              │
    ┌─────────▼─────────┐
    │ Issue resolved?    │
    └─────────┬─────────┘
         Yes │    │ No
         ▼   │    ▼
    [Report] │  ┌─────────────────────────────────┐
             │  │  Step 3: Ticket Operation        │
             │  │  create / list / view / reply /  │
             │  │  close / rate                    │
             │  └─────────────┬───────────────────┘
             │                ▼
             │  ┌─────────────────────────────────┐
             │  │  Step 4: Report & Next Steps     │
             │  │  Ticket ID + link + status       │
             │  └─────────────────────────────────┘
```

## Execution Flow

Follow these numbered steps for every request:

1. **Step 1 — Pre-flight check (silent)**: run the entry script `doctor` to verify backend availability and authentication. Only surface issues to the user if a check blocks the operation.
2. **Step 2 — Auto-diagnosis**: classify the reported issue and try CLI auto-resolve (see Error Handling). Only proceed to a ticket if auto-resolve fails or the issue is clearly a platform bug.
3. **Step 3 — Ticket operation**: run the matching subcommand of the entry script (create / list / view / reply / close / rate / categories).
4. **Step 4 — Report and next steps**: present results with hyperlinked ticket IDs, status, and expected response time; invite rating after a successful close.

### Step 1: Pre-flight Checks (silent)

```bash
python3 scripts/qianwen_support.py doctor
```

### Step 2: Auto-Diagnosis

**CRITICAL: Two types of 401 — never confuse them.**

| 401 source | Cause | Correct fix | Wrong fix |
|---|---|---|---|
| `qianwen support` command / API returns 401 | CLI session token expired | `qianwen auth login` then verify with `qianwen auth status` | — |
| Model API (qwen-text, qwen-vision) returns 401 | API Key invalid/missing/mismatched | Report Key status (set/unset), never display Key value, guide user to regenerate on web portal | `qianwen auth login` (cannot fix model API 401) |

**Diagnosis decision tree:**
1. Identify the error source: which command or API returned the error?
2. Error from `qianwen support` commands -> CLI session issue -> `qianwen auth login`
3. Error from model API calls -> API Key issue -> do NOT run `qianwen auth login`
4. If unsure, run `qianwen doctor --format json` for environment diagnostics first

**Only create a ticket if auto-resolve fails or the issue is clearly a platform bug.**

### Optional Collaboration and Fallback

QianWen CLI accurately executes queries and operations; this Skill calls CLI directly for basic diagnostics and ticket management. Other QianWen Skills are **not more capable** and **not required dependencies**.

**Rules:**
1. When the corresponding domain Skill is detected and installed: prefer its specialized diagnostic flow.
2. When the corresponding domain Skill is not installed: execute this Skill's own read-only basic checks using QianWen CLI.
3. **Never block ticket management** (create, list, view, reply, close, rate) due to missing domain Skills.
4. **Never claim professional diagnostics** this Skill does not possess — be honest about what was checked.
5. When basic diagnostics cannot resolve the issue, display the ticket draft and obtain user confirmation before submitting.

### Step 3: Ticket Operations

#### List tickets

```bash
python3 scripts/qianwen_support.py list --page 1 --page-size 10
```

#### View ticket detail + messages

```bash
python3 scripts/qianwen_support.py view --ticket-id <id>
```

#### Fetch categories (always dynamic, never hardcode)

```bash
python3 scripts/qianwen_support.py categories
```

Use `references/ticket-categories.md` for the category listing and `references/category-selection.md` for selection strategy.

**Two category groups behave differently (match web frontend):**
- **Model categories** (Billing / Invoice / Feature Inquiry / API-SDK / Tool Integration): real ticket categories -> create ticket via `CreateTicketNew`.
- **App categories** (MiaoWu / WanXiang / WuKong / QianWen / Qoder / QoderWork): the web frontend does NOT create tickets for these; it redirects users to the app's official site. **ABSOLUTE PROHIBITION:** do not create a ticket with an App category ID; instead guide the user to the app's official site (helpUrl).

#### Create ticket

```bash
python3 scripts/qianwen_support.py create \
  --category-id <id> \
  --description "[QianWen-CLI] <summary>. <detailed description>..."
```

Description must start with `[QianWen-CLI]` prefix. First sentence becomes the ticket title. Max 2000 chars. The description template ([Symptom]/[Impact]/[Steps tried]/[Error details]/[Diagnostics]) is in `references/operations-guide.md`.

**ABSOLUTE PROHIBITION:** Never submit a ticket without showing the draft to the user and getting explicit confirmation first.

#### Reply to ticket

```bash
python3 scripts/qianwen_support.py reply --ticket-id <id> --message "<text>"
```

**MANDATORY:** Check ticket status first. If terminal (closed/resolved/confirmed), refuse and offer to create a new ticket.

#### Close ticket

```bash
python3 scripts/qianwen_support.py close --ticket-id <id>
```

After successful closure, always invite the user to rate.

#### Rate ticket

```bash
python3 scripts/qianwen_support.py rate --ticket-id <id> --rating <0-2> [--comment "<text>"]
```

Rating scale: 0 = unsatisfied, 1 = neutral, 2 = satisfied. Support fuzzy input (number extraction, sentiment inference, original text as comment; full rules in `references/operations-guide.md`).

### Step 4: Post-Operation

After ticket creation, report:
- Ticket ID with hyperlink: `https://platform.qianwenai.com/home/support/detail?id=<ticket-id>`
- Current status and expected response time (typically 24 hours)

### Viewing Customer Service Replies

When reading replies via `view`, first check terminal status. For terminal tickets (closed/resolved/confirmed): display the summary, inform that replying is impossible, and offer to create a new ticket.

**Rules:**
1. **Relay verbatim, never modify**: present engineer replies exactly as-is; no deleting, summarizing, paraphrasing, or reorganizing.
2. **Screenshot handling**: CLI cannot display images. If a reply contains screenshots, inform the user to view them on the web portal and provide the ticket link.

## Observability

- **User-Agent template (mandatory)**: every request issued by the scripts
  carries a User-Agent built from the template
  `AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`, where `{SKILL_NAME}`
  is this skill's frontmatter name — `alibabacloud-qianwenai-support` — and
  `{session-id}` is the session identifier described below. Resolved example:
  `AlibabaCloud-Agent-Skills/alibabacloud-qianwenai-support/4eefc3a1be2102b3eb41463c84e98e9b`.
- **session-id rule**: generated **once per session**, as a **32-char
  lowercase hex** string, and kept **consistent across all requests** of that
  session. The value is generated per script run (`uuid4().hex`) so that every
  request of one run reports the same id; it may be pinned externally via the
  `SKILL_SESSION_ID` environment variable, which is honoured only when it
  already is a valid 32-char lowercase hex string.
- Backend mode logged to stderr: `[WARN] Using API backend (CLI unavailable)`

## Error Handling

When a command fails, **classify first, recover, then retry**. Never silently skip to fallback. Core categories: `auth-failure` (re-login then retry), `not-installed` (show install command or API fallback), `network-timeout` (retry once, then web portal), `ticket-not-found` (verify via list), `terminal-status` (refuse, offer new ticket). Full table, retry parameters, cascading-failure rules, and exit codes: see `references/error-handling.md`.

> **Rule:** Never retry more than once. If the retry also fails, immediately fall back to the web portal guidance (`https://platform.qianwenai.com/home/support`). Do not create retry loops.

## Ticket Status Flow

| Status | Terminal? | Can reply? |
|--------|:---------:|:----------:|
| `created` / `assigned` / `dealing` / `processing` / `waiting_user` / `wait_feedback` | No | Yes (except `created`, waiting assignment) |
| `resolved` / `closed` / `confirmed` | **Yes** | **No** |

**ABSOLUTE PROHIBITION:** Tickets in terminal status (closed/resolved/confirmed) MUST NOT be replied to or closed. The script enforces this; the Agent must not attempt to bypass it. The CLI does not enforce terminal-status restrictions on reply/close (calls may return success), so the Agent/script MUST check status first and refuse proactively.

## Important Notes

### Web Portal Guidance

When guiding users to the QianWen ticket page, **always provide the specific ticket link**:
```
https://platform.qianwenai.com/home/support/detail?id=<ticket-id>
```

### Ticket ID Hyperlinks

**Every ticket ID in output MUST be formatted as a hyperlink.** Example:
- Correct: Ticket [0005PYGCW](https://platform.qianwenai.com/home/support/detail?id=0005PYGCW)
- Wrong: Ticket 0005PYGCW (no link)

### Reply Workflow

When a ticket has engineer replies, **MUST follow this three-step workflow**:
1. **Display engineer reply verbatim** — no summarizing, paraphrasing, or editing
2. **Wait for user instructions** — ask how to reply, wait for specific instructions
3. **Draft and confirm** — draft reply based on user instructions, get confirmation before submitting

### Authorization Requests — Immediate Stop

**When engineer requests authorization, immediately stop all other operations:**
1. Stop current workflow
2. Inform user: "Authorization operations are prohibited in Agent; must be done by you on the web portal"
3. Provide ticket link
4. Relay the specific authorization request verbatim

### Attachments — Strictly Prohibited

**ABSOLUTE PROHIBITION:** This skill MUST NOT upload any attachments (images, documents, logs, screenshots, archives, etc.). Always decline and direct users to the web portal.

### Batch Operations — Not Supported

**ABSOLUTE PROHIBITION:** This skill MUST NOT perform batch operations (batch create/reply/close/rate/export). Only one ticket at a time.

### Ticket Language

Ticket descriptions must be written in the support site's language regardless of the user's language. Customer original text, engineer replies, error logs, and code snippets are preserved verbatim without translation. Show both the English status and the localized name for clarity. Do not switch `--accept-language` away from the site default just because the user writes in another language.

### Sensitive Info Masking

When composing ticket descriptions or replies, always mask sensitive info:
- Email: `zephy*****@gmail.com`
- Phone: `138****1234`
- API Key / AccessKey: `sk-****xxxx`
- User ID: `08****94`

## Output Display Rules

Parse the JSON output and present a human-readable summary — never dump raw JSON. Add analysis AFTER the summary, separated with `---`. Full rules and examples: see `references/operations-guide.md`.

## Examples

### Example: Create ticket

```
User: qianwen support list keeps returning 401, please help me submit a ticket

Agent (internal):
1. python3 scripts/qianwen_support.py doctor -> backend: cli, authenticated: true
2. 401 from `qianwen support` command -> CLI session issue -> guide user to re-login
3. User confirms still failing -> fetch categories -> draft ticket

Agent (to user):
Ticket draft:
**Title**: [QianWen-CLI] support list command keeps returning 401
**Category**: CLI & SDK Issues
**Description**: [Symptom] ... [Diagnostics] ...
Submit this ticket? (yes/no)

User: yes

Agent (to user):
Ticket submitted!
**Ticket [0005PYGCW](https://platform.qianwenai.com/home/support/detail?id=0005PYGCW)**
**Status**: Created - Expected response within 24 hours.
```

### Example: List tickets

```
User: Help me check all my tickets

Agent (internal):
1. python3 scripts/qianwen_support.py list --page 1 --page-size 10

Agent (to user):
Your ticket list (page 1, 10 items):

| # | Ticket | Title | Status |
|---|------|------|------|
| 1 | [0007AB123](https://platform.qianwenai.com/home/support/detail?id=0007AB123) | qwen-vision API returns 401 | Created |
| 2 | [00069R8Z4Y](https://platform.qianwenai.com/home/support/detail?id=00069R8Z4Y) | support list returns 401 | Confirmed |

Showing latest 10. View next page? (yes/no)
```

### Example: Terminal status ticket

```
User: reply to ticket 00069R8Z4Y

Agent (internal):
1. python3 scripts/qianwen_support.py view --ticket-id 00069R8Z4Y
2. status: "confirmed" -> terminal status -> refuse reply

Agent (to user):
Ticket [00069R8Z4Y](https://platform.qianwenai.com/home/support/detail?id=00069R8Z4Y) status is Confirmed.
This ticket is in terminal status and cannot be replied to. **Create a new ticket instead?** (yes/no)
```

### Example: Model API 401 — correct handling (no auth login)

```
User: qwen-text returns 401, help me submit a ticket

Agent (internal):
1. doctor -> authenticated
2. 401 from model API (NOT from qianwen support) -> API Key issue
3. Do NOT run qianwen auth login
4. Draft ticket

Agent (to user):
Diagnosis: model API returns 401 and your API Key is set. This is likely a Key
permission or validity issue, NOT a CLI login problem (re-login cannot fix it).

Ticket draft:
**Title**: [QianWen-CLI] qwen-text API returns 401, Key is set
**Category**: Model > API/SDK
Submit this ticket? (yes/no)
```
