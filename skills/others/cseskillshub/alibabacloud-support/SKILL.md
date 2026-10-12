---
name: alibabacloud-support
description: |
  Manage Alibaba Cloud (Aliyun) after-sales support tickets from the conversation:
  match the reported problem against the published ticket rules, build a redacted
  non-blocking draft, then query the product catalog, list recent tickets, create,
  view, reply to, close and rate tickets through the Workorder OpenAPI. Use when a
  customer asks to open, follow up on, reply to, close or rate an Alibaba Cloud
  support ticket, asks for the ticket list, status or engineer reply, or wants human
  support instead of self-service.
  Triggers: "submit a ticket", "create a support ticket", "list my tickets",
  "view ticket status", "reply to the engineer", "close the ticket",
  "rate the ticket", "transfer to human support", "escalate to Alibaba Cloud support",
  "support case". Do not use for product knowledge, troubleshooting or solution
  discussion that carries no ticket intent.
compatibility: Requires Python 3.9+. The aliyun CLI with the workorder product plugin is required only for catalog and ticket API operations; when the CLI is absent, the agent may help install and configure it only after explicit customer consent. Rules load from the pinned aliyun/alibabacloud-aiops-skills master commit, then an anonymous HTTPS OSS fallback. Workorder authentication uses the aliyun CLI default credential chain; this skill never stores, reads or prints AccessKey credentials.
metadata:
  openclaw:
    emoji: "🎧"
    homepage: https://www.aliyun.com/service
    primaryEnv: ALIBABACLOUD_SUPPORT_HOME
    requires:
      env: []
      bins: [python3, aliyun]
      os: [darwin, linux, windows]
    install:
      - {kind: brew, formula: aliyun-cli, bins: [aliyun]}
    envVars:
      - {name: ALIBABACLOUD_SUPPORT_HOME, required: false, description: "Local directory for the rule cache, confirmation tokens and update state; defaults to a directory under the user home."}
      - {name: ALIBABACLOUD_SUPPORT_RULES_OSS_URL, required: false, description: "Optional official OSS bucket root HTTPS address that overrides the anonymous rule fallback source."}
      - {name: ALIBABACLOUD_SUPPORT_RULES_OSS_PREFIX, required: false, description: "Optional OSS object prefix for the rule fallback; the built-in value is empty because rules live directly under products/."}
      - {name: ALIBABACLOUD_SUPPORT_CLI_PATH, required: false, description: "Optional absolute path to the aliyun executable, used when the current process has not refreshed PATH."}
      - {name: ALIBABACLOUD_SUPPORT_CLI_ENCODING, required: false, description: "Optional explicit utf-8 or gb18030 decoding of aliyun CLI output, needed only when the CLI output really does not match the system preferred code page."}
      - {name: ALIBABA_CLOUD_REGION_ID, required: false, description: "Optional region used for the aliyun CLI call; defaults to cn-hangzhou, resolved through the default credential chain."}
      - {name: SKILL_SESSION_ID, required: false, description: "Optional 32-character hex session identifier reused by child processes for the User-Agent tracing value; generated automatically when absent."}
---

# Alibaba Cloud Support Ticket Assistant

All Workorder operations go through `scripts/aliyun_support.py`. ABSOLUTE PROHIBITION on
calling `aliyun workorder ...` directly, on editing the installed `SKILL.md` or
`scripts/aliyun_support.py` at the customer site, and on sending any credential, UID or raw
customer content to the rule sources. The client is the only place that builds CLI commands,
redacts content, binds confirmation tokens and reconciles ambiguous writes.

## Execution Principle

1. Every customer-visible write is prepared, previewed and confirmed one ticket at a time.
   MANDATORY: run the matching `preview-*` command, show the complete preview, and only then
   use the returned `confirmationToken` for the write command.
2. Information collection never blocks a ticket. Values that already appear in the
   conversation are reused; missing suggestions are asked once at most, and if the customer
   skips them the draft and the ticket are still produced. ABSOLUTE PROHIBITION on asking for
   a UID, account id, CreatorId or identity number — ticket ownership comes from the aliyun
   CLI default credential chain.
3. Ambiguous results are never retried. A timeout, interrupt, abnormal exit or unverifiable
   response for `CreateTicket` triggers one automated query-based reconciliation and nothing
   else; other ambiguous writes stop with an explicit "do not retry" instruction.
4. Degradation is silent for the customer only when the published result still holds: rule
   sources, self-update and optional fields may fail, and the workflow continues with the
   built-in generic template.

## Observability

Every aliyun CLI invocation carries:

- **User-Agent**: `--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id} skill-version/{version}`, with
  `SKILL_NAME` = `alibabacloud-support`; the same value is exported to the child process
  through `ALIBABACLOUD_USER_AGENT` and `ALIBABA_CLOUD_USER_AGENT`.
- **skill-version**: MANDATORY source of the version component is `references/manifest.json`
  (`version`, a semantic version string). The client reads it lazily when it builds the first
  User-Agent, that is before the first cloud call, caches it for the run, and propagates it in
  the User-Agent of every Workorder call. ABSOLUTE PROHIBITION on hardcoding, inferring or
  placeholder-substituting that version: when the manifest is missing, unreadable or declares no
  valid semantic version, `catalog` and `ticket` stop with `success: false`, exit code 1 and zero
  cloud calls, while `doctor` reports it truthfully as
  `workorderAccess.reason = skill_version_unavailable`,
  `readiness.state = workorder_access_unavailable`,
  `readiness.nextAction = request_skill_reinstallation_consent`, and every capability probe
  reason `skill_version_unavailable`. `rules update`, `match` and `draft` stay available because
  they make no cloud call.
- **session-id**: a 32-character hex string. It is read from `SKILL_SESSION_ID` when that
  variable already holds a valid 32-hex value, otherwise `uuid.uuid4().hex` generates one and
  writes it back to the process environment so nested processes share the same session id.

`scripts/aliyun_support.py` prints a single machine-readable JSON document on stdout and
progress or degradation notes on stderr; `rules update` and `self-update` report
`sourceType`, `sourceCommit`, `githubError`, `ossError`, `degraded` and `effectiveSource`, so
a fallback is always visible in the output, never only in prose.

## Credentials

The Workorder API is authenticated only by the aliyun CLI default credential chain
(environment variables or `~/.aliyun/config.json`). ABSOLUTE PROHIBITION on hardcoding,
asking for, echoing, transcribing or repairing credential values, on putting secrets in
command arguments, temporary files or ticket bodies, and on printing AccessKey, STS token,
bearer token, cookie or private key material. Confirmation tokens are random, expiring local
handles, not credentials. The credential cache and every state file are written with `0600`
permissions under `ALIBABACLOUD_SUPPORT_HOME`.

## User Confirmation

- Installing the aliyun CLI, repairing it, or writing the local OAuth configuration requires
  a separate, explicit customer agreement. The first request to "submit a ticket" is not
  consent to install anything. After a refusal or no answer, continue with a local draft and
  point to the Alibaba Cloud console instead of pressing again.
- `aliyun configure --mode OAuth --profile default` can only be run by the customer in their
  own interactive terminal. The agent must not execute it, capture its output, record the
  authorization URL, complete the login, or read the browser session.
- Each write is bound to the exact bytes of its own preview: the token is single-use, expires
  after 30 minutes, and is invalidated when the content or the ticket status changes. Reply,
  close and evaluate re-read the ticket status immediately before the call and stop if it
  moved to a terminal state.

## Trigger Conditions

Use this skill when the customer expresses any ticket intent: create or submit a ticket,
report a fault, escalate to Alibaba Cloud support or a human agent, check the ticket list,
status or engineer reply, add missing information, close or rate a ticket. Do not use it for
pure product knowledge questions, self-service troubleshooting, or plan discussions.
Batch operations are never triggered: creating, replying, closing or rating several tickets
in one run is out of scope.

## Input Parameters

| Command | Required | Optional |
|---|---|---|
| `doctor` | — | `--home` |
| `self-update status` / `self-update update` | — | `--force` |
| `rules status` / `rules update` | — | `--oss-url`, `--oss-prefix`, `--force` |
| `match` | `--input` (a file, or `-` for stdin) | `--product` |
| `draft` | `--input` (a JSON file, or `-` for stdin) | — |
| `catalog products` | — | `--name`, `--language zh|en|jp` (default `zh`) |
| `catalog categories` | `--product-id` | `--name`, `--language` |
| `ticket get` | `--ticket-id` | — |
| `ticket list` | — | `--days` (1-3650, default 30), `--page-number`, `--page-size` (10-100), `--keyword`, `--ticket-id` |
| `ticket preview-create` / `ticket create` | `--category-id`, `--title`, `--content-file` | `--severity` (1 or 2, default 1), `--confirmation-token` (write only) |
| `ticket preview-reply` / `ticket reply` | `--ticket-id`, `--content-file` | `--confirmation-token` |
| `ticket preview-evaluate` / `ticket evaluate` | `--ticket-id`, `--score` (1-5), `--solved` (`true`/`false`) | `--content-file`, `--confirmation-token` |
| `ticket preview-close` / `ticket close` | `--ticket-id` | `--confirmation-token` |

`--content-file -` and `--input -` read the content from standard input, so customer text
never has to be written to a local file or exposed as a process argument beyond the CLI call
itself.

## Module Index

- `references/ram-policies.md` — verified permission model, the measured STS probe result and
  the least-privilege policy for the ticket operations this skill uses.
- `references/api-reference.md` — the nine Workorder operations, their plugin-mode commands,
  parameters, verified response envelope and the exact CLI form the client builds.
- `references/error-handling.md` — exit code and `Success` semantics, deterministic versus
  indeterminate failures, the create-timeout reconciliation contract and the degraded rule
  sources.
- `references/rule-sources.md` — the fixed GitHub-then-OSS rule order, the integrity checks,
  the snapshot cache layout and the built-in generic template fallback.

## Orchestration

```
customer problem
   └─ doctor (readiness gate) ─┬─ self-update status ─┐
                               ├─ rules update ───────┤  best effort, never blocking
                               └─ catalog ────────────┘
   └─ match → resolved issue type or generic fallback
   └─ draft → validated, redacted, non-blocking ticket body
   └─ catalog products → catalog categories → live CategoryId
   └─ preview-* → customer confirmation → create | reply | evaluate | close
   └─ ticket get / ticket list → status, engineer reply, clickable ticket URL
```

## Execution Flow

### 1. Quiet preflight

```bash
python3 scripts/aliyun_support.py doctor
python3 scripts/aliyun_support.py self-update status
python3 scripts/aliyun_support.py rules update
```

Continue only when `readiness.readyForTicketOperations` is `true`; `rules update`, `match` and
`draft` work without the CLI. The capability probe is a single offline `aliyun workorder
--help` listing, so it sends no request and needs no credential;
`capabilityMatrix[].available` reflects the plugin command surface, and
`permissionVerified: false` means the write permissions were deliberately not probed.
`rules update` also performs one best-effort client self-update check per seven-day cycle: it
only downloads `SKILL.md` and `scripts/aliyun_support.py` from the pinned commit, validates
frontmatter, the semver of the script `VERSION` constant, compilation and the `APP_NAME`
match, installs only a strictly higher version, and keeps a `0600` transaction record with the
backup location and SHA-256 so an interrupted update is recovered or rolled back before any
other command runs.

### 2. Understand the problem and match the rules

```bash
printf '%s' '<customer problem>' | python3 scripts/aliyun_support.py match --input -
```

Use a specific issue type only when the match is confident and unique; otherwise ask one
clarifying question. If the product is missing from the rules, or the product exists without a
matching scenario, keep working with the returned `fallback` generic template and report
`ruleMatched: false` and `fallbackReason` honestly.

### 3. Collect information and build the draft

```bash
python3 scripts/aliyun_support.py draft --input - <<'JSON'
{
  "product": "ecs",
  "issueType": "General issue",
  "summary": "The instance cannot be reached over SSH",
  "impact": "One test instance is unavailable",
  "stepsTried": ["confirmed the security group allows the target port"],
  "values": {
    "instanceId": "i-example",
    "regionId": "cn-hangzhou",
    "occurredAt": "2026-10-09 16:30:00 +08:00",
    "errorMessage": "Connection timed out"
  }
}
JSON
```

The draft is `ready: true` even when suggested fields are missing; `suggestedMissing` only
improves quality. Keep the product name the customer used, and set `issueType` to
`General issue` for a fallback draft. If a password, AccessKey secret, token, cookie,
Authorization header or private key is detected, stop and do not produce a submittable draft.
When the customer request omits key values (region, instance or resource id, symptom detail,
occurrence time), either ask one clarifying question for them, or continue automatically —
and in the automatic path the final answer MUST state explicitly which values the customer
never provided and that they were auto-filled with the documented defaults (`cn-hangzhou` as
the region, the generic template with `General issue`), then present the ready draft. Never
phrase the outcome as "the missing information still needs to be collected": say plainly that
the missing values were defaulted, no value was invented, and the draft proceeds regardless.

### 4. Query the live catalog

```bash
python3 scripts/aliyun_support.py catalog products --name ecs
python3 scripts/aliyun_support.py catalog categories --product-id <PRODUCT_ID> --name <KEYWORD>
```

Never persist a category id; resolve it for every creation.

### 5. Preview and wait for confirmation

```bash
python3 scripts/aliyun_support.py ticket preview-create \
  --category-id <CATEGORY_ID> --severity 1 --title <TITLE> --content-file -
```

Show product, category, severity, title and the complete redacted body. `preview-create`
returns `preview.content` — the exact body to replay — next to a separate
`preview.clientRequestId`, a visible `[client request id] <24 hex characters>` value derived
from the random confirmation token; it is not a credential and exists only to reconcile a
timed-out creation. Show the request id together with the preview, and never remove, replace
or reuse it. The client appends `[client request id] <value>` as the last line of the body
inside the create request itself, so replay `preview.content` unchanged and never add the
marker line yourself. Titles are normalized to start with `[aliyun-support]`, and the token is
bound to the normalized title and the final body.

### 6. Create the ticket

After the customer confirms exactly that preview, replay `preview.content` unchanged:

```bash
python3 scripts/aliyun_support.py ticket create \
  --category-id <CATEGORY_ID> --severity 1 --title <TITLE> --content-file - \
  --confirmation-token <CONFIRMATION_TOKEN>
```

Render the ticket number as a clickable link to `ticketUrl`, for example
`[000MOCKTICKET](https://smartservice.console.aliyun.com/service/ticket-detail?ticketId=000MOCKTICKET)`;
never return only the bare number or the raw JSON. If the response says success but no
verifiable ticket id can be extracted, the client does not claim creation: it reconciles the
result through the two queries `ListTickets` and `GetTicket` inside a narrow time window,
matching the
creation time, title, the full body including this request marker, category and severity.
`creationState` is `reconciled_after_timeout` or `reconciled_after_indeterminate_result` only
for a unique complete match; zero, several, incomplete pages or an interrupted reconciliation
stop with an explicit prohibition on automatic retry and require manual verification.

### 7. Follow up on an existing ticket

```bash
python3 scripts/aliyun_support.py ticket list --days 30 --page-number 1 --page-size 20
python3 scripts/aliyun_support.py ticket get --ticket-id <TICKET_ID>
python3 scripts/aliyun_support.py ticket preview-reply --ticket-id <TICKET_ID> --content-file -
python3 scripts/aliyun_support.py ticket reply --ticket-id <TICKET_ID> --content-file - --confirmation-token <TOKEN>
python3 scripts/aliyun_support.py ticket preview-evaluate --ticket-id <TICKET_ID> --score 5 --solved true --content-file -
python3 scripts/aliyun_support.py ticket evaluate --ticket-id <TICKET_ID> --score 5 --solved true --content-file - --confirmation-token <TOKEN>
python3 scripts/aliyun_support.py ticket preview-close --ticket-id <TICKET_ID>
python3 scripts/aliyun_support.py ticket close --ticket-id <TICKET_ID> --confirmation-token <TOKEN>
```

`ticket get` returns both `GetTicket` and the full `ListTicketNotes` conversation. Quote
engineer replies verbatim, never rewrite them, and only point to the console for attachments.
Evaluate one ticket at a time with an explicit 1-5 score and an explicit `solved` value.

## Windows Conventions

The `python3`, `printf` and heredoc forms above apply to macOS, Linux and Git Bash only. On
Windows CMD and PowerShell do not copy them. In QoderWork-like Windows environments use the
single-line `py scripts/aliyun_support.py ...` form, write non-ASCII input to a UTF-8 file
first and pass `--input <file>` or `--content-file <file>`, and never mix CMD
`%USERPROFILE%`, PowerShell `$env:USERPROFILE` and Git Bash `$HOME` syntax in one flow. When
the current process cannot see `aliyun`, use `doctor.setupGuidance.fullPathFallbackByShell`
for the matching shell or let the customer set `ALIBABACLOUD_SUPPORT_CLI_PATH`; do not
reinstall. `content.txt`, `reply.txt`, `evaluation.txt` and the JSON inputs must be UTF-8 and
must never contain credentials; preview, token and write must reuse the identical file bytes.
If the customer cannot accept that content briefly exists as a local file, fall back to Git
Bash standard input or the console.

## Safety Boundaries

- Remote rules may declare only product aliases, issue types, match keywords, category hints
  and collection fields. Unknown keys, URLs, commands, scripts, SQL, regular expressions,
  credentials or secret content are rejected, and collection fields must never ask for the
  raw value of a password, private key, cookie, Authorization header or AccessKey secret. The
  only credential-related non-secret fields allowed are `authorizationStatus`,
  `authorizationScope`, `tokenUsage`, `apiKeyPrefix` and `apiKeyType`, and their labels must
  match that meaning without example values.
- The rule order is fixed: the GitHub repository, branch and directory are compiled in and
  cannot be overridden by environment variables or flags; the master commit is resolved first
  and every content and raw request is pinned to that 40-character SHA. OSS accepts only an
  official bucket-root HTTPS address with anonymous `ListObjectsV2` and `GetObject`, and only
  direct `products/*.json` objects. Cross-origin redirects, path traversal, nested paths,
  wrong file types, duplicate objects, blob SHA mismatches, excess counts or oversized objects
  are rejected. GitHub content is verified by Git blob SHA-1; the rule set also gets a local
  content digest and a `manifest.json` that records the exact file set, per-file SHA-256 and
  size. A missing or damaged snapshot falls back only to a previously verified snapshot, and
  if neither is usable the client runs on an empty rule set with the built-in generic template.
- Customer problems, collected values, drafts, replies and credentials are never uploaded to
  the rule sources and never written into the rule cache.
- All Workorder calls go through the aliyun CLI in plugin mode (`aliyun workorder
  list-products`, `aliyun workorder create-ticket`, …) with `--retry-count 0`, an explicit
  read timeout, no shell and no command history. Verified with `--cli-dry-run`, every
  Workorder operation is sent as `POST` and customer content travels in the request body, not
  in a URL query parameter. `CreateTicket`, `ReplyTicket`, `CloseTicket` and `EvaluateTicket`
  are never retried.
- The aliyun CLI offers no standard-input or file transport for RPC string parameters, so the
  redacted title, body, reply or evaluation text is briefly visible in the local `aliyun`
  process arguments. If that local exposure is not acceptable, stop the write and use the
  console.
- Batch creation, batch reply, batch close and batch evaluation are prohibited, as is any
  attachment upload; attachments stay in the console.
- The client never patches itself at the customer site: encoding, PATH, authentication or API
  problems are solved with the documented commands, flags and environment variables, and a
  fixed client version reaches the customer only through a validated release or self-update.

## Error Handling

Run `doctor` to see the Python, CLI, rule cache, OSS configuration, legacy environment and
client-update state. A missing or unusable CLI returns `readiness.state` `cli_missing` or
`cli_unusable` and blocks only the CLI-dependent capabilities. After authentication, treat
the exit code and the boolean `Success` as primary and keep the redacted `Code`, `Message` and
`RequestId`; `0` and `200` both count as success. Only an explicit `Success: false` is a
deterministic API rejection; a missing or invalid `Success`, or `Success: true` with an error
`Code`, is indeterminate and forbids retry. Distinguish `api_probe_failed` causes — expired
login, network failure and insufficient RAM permission — from `workorder_access_unavailable`,
and never fall back to another credential silently. When both rule sources fail, the client
returns the degraded generic template and keeps `match` and `draft` working; a failed
self-update never blocks rules, catalog or ticket work.

## Important Notes

- Ticket operations act on the account behind the default credential chain; state results as
  belonging to that account instead of claiming a global view.
- Ticket status labels come back in Chinese from Workorder and are translated by the console,
  for example `completed`, `awaiting your rating` and `closed`; the client compares both
  `Status.Value` and `Status.Label` before it allows any write.
- The script `VERSION` constant is the single version authority for this release; the
  `SKILL.md` frontmatter intentionally carries no version field.
- Timeouts are bounded on every network, CLI and subprocess call; `--days`, `--page-size` and
  content lengths are range-checked instead of paging indefinitely.

## Examples

- "The ECS instance in cn-hangzhou cannot be reached over SSH since this afternoon; please
  submit a ticket for me." → `doctor`, `rules update`, `match`, `draft`, `catalog products`,
  `catalog categories`, `ticket preview-create`, customer confirmation, `ticket create`, then
  the clickable ticket link.
- "List my tickets from the last 30 days and show me the engineer reply of 000MOCKTICKET." →
  `doctor`, `ticket list`, `ticket get`, verbatim engineer reply, no write.
- "The engineer answered, please reply that the port is open now and then close it." → two
  separate previews, two confirmations, then `ticket reply` and `ticket preview-close` /
  `ticket close`, never in one batch.
