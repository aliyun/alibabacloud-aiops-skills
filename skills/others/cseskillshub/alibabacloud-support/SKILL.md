---
name: alibabacloud-support
description: |
  Manage Alibaba Cloud (Aliyun) after-sales support tickets from the conversation:
  resolve the real product and issue category through the Workorder OpenAPI, apply
  the bundled per-category collection rules, build a redacted non-blocking draft,
  then list recent tickets and create, view, reply to, close and rate tickets. Use
  when a customer asks to open, follow up on, reply to, close or rate an Alibaba
  Cloud support ticket, asks for the ticket list, status or engineer reply, or
  wants human support instead of self-service.
  Triggers: "submit a ticket", "create a support ticket", "list my tickets",
  "view ticket status", "reply to the engineer", "close the ticket",
  "rate the ticket", "transfer to human support", "escalate to Alibaba Cloud support",
  "support case". Do not use for product knowledge, troubleshooting or solution
  discussion that carries no ticket intent.
compatibility: Requires Python 3.9+ and aliyun CLI >= 3.3.3 (verified against 3.4.5 + aliyun-cli-workorder 0.9.0); install or upgrade with `brew install aliyun-cli` (macOS) or `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` (Linux), then confirm with `aliyun version`. The aliyun CLI is required for catalog, ticket API operations and the doctor Workorder probe; rules status, match --local-only and draft are local. Product collection rules ship inside this skill package and are never fetched at runtime. Workorder authentication uses the aliyun CLI default credential chain; this skill never stores, reads or prints AccessKey credentials.
metadata:
  version: "1.8.0"
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
      - {name: ALIBABACLOUD_SUPPORT_HOME, required: false, description: "Local directory for confirmation tokens and non-rule state; rules live in the skill package and this variable does not affect them."}
      - {name: ALIBABACLOUD_SUPPORT_CLI_PATH, required: false, description: "Optional absolute path to the aliyun executable, used when the current process has not refreshed PATH."}
      - {name: ALIBABACLOUD_SUPPORT_CLI_ENCODING, required: false, description: "Optional explicit utf-8 or gb18030 decoding of aliyun CLI output, needed only when the CLI output really does not match the system preferred code page."}
      - {name: ALIBABA_CLOUD_REGION_ID, required: false, description: "Optional region used for the aliyun CLI call; defaults to cn-hangzhou, resolved through the default credential chain."}
      - {name: SKILL_SESSION_ID, required: false, description: "Optional 32-character hex session identifier reused by child processes for the User-Agent tracing value; generated automatically when absent."}
---

# Alibaba Cloud Support Ticket Assistant

All Workorder operations go through `scripts/aliyun_support.py`. ABSOLUTE PROHIBITION on
calling `aliyun workorder ...` directly, on editing the installed `SKILL.md` or
`scripts/aliyun_support.py` at the customer site, on downloading or executing
runtime updates of this skill, and on sending any credential, UID or raw customer
content to any external destination. The client is the only place that builds CLI
commands, redacts content, binds confirmation tokens and reconciles ambiguous writes.

## Prerequisites

- **Python 3.9+** — required for `scripts/aliyun_support.py` (entry script).
- **aliyun CLI >= 3.3.3** — required for every Workorder OpenAPI call (`list-products`, `list-categories`, `create-ticket`, `list-tickets`, `get-ticket`, `reply-ticket`, `close-ticket`, `evaluate-ticket`, `list-ticket-notes`). The plugin-mode command surface this skill invokes was introduced in aliyun CLI 3.3.3 and hardened in 3.4.x; the current verified combination is aliyun CLI 3.4.5 with the `aliyun-cli-workorder` 0.9.0 plugin. Install or upgrade with `brew install aliyun-cli` / `brew upgrade aliyun-cli` on macOS, or `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` on Linux; confirm with `aliyun version`. If the installed version is below 3.3.3 the entry script returns an `not-installed` diagnostic and no CLI process is spawned.

## Data Flows and External Calls

The destinations below are the complete set of network endpoints present in this
skill's shipped code. There are no others.

- **Workorder OpenAPI** (via the aliyun CLI plugin mode, `aliyun workorder <plugin-command>`)
  — `ListProducts`, `ListCategories`, `ListTickets`, `GetTicket`, `ListTicketNotes`,
  `CreateTicket`, `ReplyTicket`, `CloseTicket`, `EvaluateTicket`. Requests carry the
  operation name, paging parameters and the ticket fields the user supplied and confirmed
  (title, category id, description, reply content, rating), plus a tracing `User-Agent`.
  Authentication uses the caller's default aliyun CLI credential chain.
- **No other network destination exists.** Product collection rules are read from
  `references/products/*.json` inside this skill package. The skill never calls GitHub,
  never calls OSS, and never fetches or executes content that was not installed together
  with the skill.

**Ticket-write boundary:** this skill never creates, modifies, deletes or bills any cloud
resource. Its only write operations are Workorder ticket records (create, reply, close,
rate), and each one requires the user's explicit confirmation of the full preview before
submission. All catalog lookups, ticket status queries and rule verification are read
paths that make no state change outside the ticket record itself.

## Execution Principle

1. Every customer-visible write is prepared, previewed and confirmed one ticket at a time.
   MANDATORY: run the matching `preview-*` command, show the complete preview, and only then
   use the returned `confirmationToken` for the write command.
2. Information collection never blocks a ticket. Values that already appear in the
   conversation are reused; missing suggestions are asked at most once, and if the customer
   skips them the draft and the ticket are still produced. ABSOLUTE PROHIBITION on asking for
   a UID, account id, CreatorId or identity number — ticket ownership comes from the aliyun
   CLI default credential chain.
3. Ambiguous results are never retried. A timeout, interrupt, abnormal exit or unverifiable
   response for `CreateTicket` triggers exactly one non-mutating reconciliation via `ListTickets`
   plus `GetTicket`, and nothing else; other ambiguous writes stop with an explicit "do not
   retry" instruction.
4. Rule matching and drafting are always offline. When a bundled rule cannot be verified or
   does not map to the real category, `match` and `draft` fall back to the built-in
   `DEFAULT_ISSUE` generic template without changing the real `category` returned by the
   Workorder OpenAPI. ABSOLUTE PROHIBITION on inventing categories, on reusing a category id
   across runs, or on substituting a rule-declared category for the OpenAPI result.

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
  reason `skill_version_unavailable`. `rules status`, `match --local-only` and `draft` stay
  available because they make no cloud call.
- **session-id**: a 32-character hex string. It is read from `SKILL_SESSION_ID` when that
  variable already holds a valid 32-hex value, otherwise `uuid.uuid4().hex` generates one and
  writes it back to the process environment so nested processes share the same session id.

`scripts/aliyun_support.py` prints a single machine-readable JSON document on stdout and
progress or degradation notes on stderr. `rules status` reports `source`, `sourceType`,
`networkFetchDisabled`, `skillVersion`, `contentDigest`, `listedCount`, `acceptedCount`,
`rejectedCount`, `rejectedFiles`, `usableCount`, `partial`, `degraded` and `manifestError`,
so any rule degradation is visible in the output, never only in prose.

## Credentials

The Workorder API is authenticated only by the aliyun CLI default credential chain
(environment variables or `~/.aliyun/config.json`). ABSOLUTE PROHIBITION on hardcoding,
asking for, echoing, transcribing or repairing credential values, on putting secrets in
command arguments, temporary files or ticket bodies, and on printing AccessKey, STS token,
bearer token, cookie or private key material. Confirmation tokens are random, expiring local
handles, not credentials. The confirmation-token cache and every state file are written with
`0600` permissions under `ALIBABACLOUD_SUPPORT_HOME`.

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
| `rules status` | — | — |
| `match` | `--product-id`, `--category-id` (from the live catalog in this run) | `--local-only` (with `--input` and `--product`) |
| `draft` | `--input` (a JSON file, or `-` for stdin) | — |
| `catalog products` | — | `--name`, `--language zh\|en\|jp` (default `zh`) |
| `catalog categories` | `--product-id` | `--name`, `--language` |
| `ticket get` | `--ticket-id` | — |
| `ticket list` | — | `--days` (1-3650, default 30), `--page-number`, `--page-size` (10-100), `--keyword`, `--ticket-id` |
| `ticket preview-create` / `ticket create` | `--category-id`, `--title`, `--content-file` | `--severity` (1 or 2, default 1), `--confirmation-token` (write only) |
| `ticket preview-reply` / `ticket reply` | `--ticket-id`, `--content-file` | `--confirmation-token` |
| `ticket preview-evaluate` / `ticket evaluate` | `--ticket-id`, `--score` (1-5), `--solved` (`true`/`false`) | `--content-file`, `--confirmation-token` |
| `ticket preview-close` / `ticket close` | `--ticket-id` | `--confirmation-token` |

`--content-file -` and `--input -` read the content from standard input, so customer text
never has to be written to a local file or exposed as a process argument beyond the CLI call
itself. `match --local-only` is the explicit offline path used only when the caller cannot
obtain a real category id from the OpenAPI in this run; a ticket created after local-only
must state honestly that the real classification is unverified.

## Module Index

- `references/ram-policies.md` — verified permission model, the measured STS probe result and
  the least-privilege policy for the ticket operations this skill uses.
- `references/api-reference.md` — the nine Workorder operations, their plugin-mode commands,
  parameters, verified response envelope and the exact CLI form the client builds.
- `references/error-handling.md` — exit code and `Success` semantics, deterministic versus
  indeterminate failures, and the create-timeout reconciliation contract.
- `references/rule-sources.md` — the bundled rule loader layout, manifest integrity checks,
  per-file and cross-file isolation rules, and the `DEFAULT_ISSUE` generic-template fallback.
- `references/manifest.json` — the semantic version source for the User-Agent `skill-version`
  component; must equal the script `VERSION` constant and `rules-manifest.json`'s
  `skillVersion`.
- `references/rules-manifest.json` and `references/products/*.json` — the packaged product
  collection rules and their per-file `size` and `sha256` record. Loaded at every `match`
  and `draft`; never fetched over the network.

## Orchestration

```
customer problem
   └─ doctor (readiness gate)
   └─ catalog products → catalog categories → live ProductId and CategoryId
   └─ match --product-id --category-id → real category and either a specific
      collection rule or the DEFAULT_ISSUE generic fallback
   └─ draft → validated, redacted, non-blocking ticket body
   └─ preview-* → customer confirmation → create | reply | evaluate | close
   └─ ticket get / ticket list → status, engineer reply, clickable ticket URL
```

There is no runtime rule download and no runtime client update anywhere in this chain.

## Execution Flow

### 1. Quiet preflight

```bash
python3 scripts/aliyun_support.py doctor
python3 scripts/aliyun_support.py rules status
```

Continue only when `readiness.readyForTicketOperations` is `true`. `rules status`,
`match --local-only` and `draft` work without the CLI. The capability probe is a single
offline `aliyun workorder --help` listing, so it sends no request and needs no credential;
`capabilityMatrix[].available` reflects the plugin command surface, and
`permissionVerified: false` means the write permissions were deliberately not probed.

### 2. Resolve the real product and category from the live catalog

Extract a short, non-sensitive product keyword from the customer's original problem — never
the full log, message or resource identifier — then query the live catalog:

```bash
python3 scripts/aliyun_support.py catalog products --name <short-keyword>
python3 scripts/aliyun_support.py catalog categories --product-id <ProductId-from-this-run>
```

The real `ProductId` and `ProductName` live inside each directory's `ProductList`; never
treat the directory id as the product id. If the name filter returns nothing, refetch
without the filter. Select the product and category from the results: if the match is high
confidence and unique, use it; if multiple plausible candidates remain, ask one clarifying
question; if still ambiguous, keep the generic draft and tell the customer to pick the
category in the console. ABSOLUTE PROHIBITION on auto-picking the first row, on inventing a
generic category id, or on reusing a historical category id across runs.

### 3. Match the bundled rules against the real category

```bash
python3 scripts/aliyun_support.py match --product-id <ProductId-from-step-2> --category-id <CategoryId-from-step-2>
```

`match` re-runs the two catalog queries under the hood, verifies the id, ownership and
displayed name against the real OpenAPI result, then applies the loader described in
`references/rule-sources.md`: a rule maps only when the real product name matches the rule's
product or an alias AND the real category name (after NFKC, casefold, whitespace and known
product-prefix normalisation, plus a secondary "strip one trailing qualified parenthesis"
attempt) matches the rule's issue type name or `categoryHints`. Unique mapping yields the
specific `collect` list; no mapping, ambiguity, per-file rejection, or cross-file alias
conflict yields `DEFAULT_ISSUE`, while `category` keeps the OpenAPI-verified values.

If authentication or the CLI is unavailable and the customer explicitly accepts an
unverified classification, use the offline path instead:

```bash
python3 scripts/aliyun_support.py match --local-only --product <product-name-from-customer>
```

The local-only branch calls no OpenAPI, loads no specific rule and returns the generic
template. Any draft produced this way MUST be labelled "real classification not verified"
and MUST NOT be submitted through `ticket create` in the same run.

### 4. Collect information and build the draft

Pass `match.category` through unchanged; do not substitute values from the customer's text
or from the rules:

```bash
python3 scripts/aliyun_support.py draft --input - <<'JSON'
{
  "category": {
    "productId": "<ProductId-from-step-2>",
    "productName": "<real-product-name>",
    "categoryId": "<CategoryId-from-step-2>",
    "categoryName": "<real-category-name>"
  },
  "summary": "The instance cannot be reached over SSH since 2026-10-08 16:30 +08:00",
  "stepsTried": ["confirmed the security group allows the target port"],
  "values": {
    "instanceId": "i-example",
    "regionId": "cn-hangzhou",
    "errorMessage": "Connection timed out"
  }
}
JSON
```

The draft is `ready: true` even when suggested fields are missing; `suggestedMissing` only
improves quality and never blocks. When `match` returned `ruleMatched: false`, `draft`
reuses the same loader with the same fallback reason, keeps the real `category` unchanged
and switches the collection template to `DEFAULT_ISSUE`. `fallbackReason` is one of
`manifest_invalid`, `size_mismatch`, `sha256_mismatch`, `duplicate_json_key`, `schema_rejected`,
`utf8_invalid`, `file_too_large`, `unsafe_file_type`, `io_error`, `missing_file`,
`unlisted_rule`, `product_alias_conflict`, `category_missing`, `no_rule_mapping` or
`ambiguous_mapping` and must be reported honestly in the assistant reply. If a password,
AccessKey secret, token, cookie, Authorization header or private key is detected, stop and
do not produce a submittable draft. When the customer request omits key values (region,
instance or resource id, symptom detail, occurrence time), either ask one clarifying
question for them, or continue automatically — and in the automatic path the final answer
MUST state explicitly which values the customer never provided and that they were auto-filled
with the documented defaults (`cn-hangzhou` region, the generic `DEFAULT_ISSUE` template),
then present the ready draft. In the automatic path the narrative fields (symptom description,
steps tried, impact scope, time) must reuse the generic `DEFAULT_ISSUE` template wording and
only restate what the customer actually said — never invent concrete symptom specifics
(protocols, error strings, console behaviour) the customer did not report. Never phrase the outcome as "the missing information still
needs to be collected": say plainly that the missing values were defaulted, no value was
invented, and the draft proceeds regardless.

### 5. Preview and wait for confirmation

```bash
python3 scripts/aliyun_support.py ticket preview-create \
  --category-id <CategoryId-from-step-2> --severity 1 --title <TITLE> --content-file -
```

Show product, category, severity, title and the complete redacted body. `preview-create`
returns `preview.content` — the exact body to replay — next to a separate
`preview.clientRequestId`, a visible `[client request id] <24 hex characters>` value derived
from the random confirmation token; it is not a credential and exists only to reconcile a
timed-out creation. Show the request id together with the preview, and never remove, replace
or reuse it. The client appends `[client request id] <value>` as the last line of the body
inside the create request itself, so replay `preview.content` unchanged and never add the
marker line yourself. Titles are normalized to start with `[aliyun-support]`, and the token
is bound to the normalized title and the final body.

### 6. Create the ticket

After the customer confirms exactly that preview, replay `preview.content` unchanged:

```bash
python3 scripts/aliyun_support.py ticket create \
  --category-id <CategoryId-from-step-2> --severity 1 --title <TITLE> --content-file - \
  --confirmation-token <CONFIRMATION_TOKEN>
```

Render the ticket number as a clickable link to `ticketUrl`, for example
`[000MOCKTICKET](https://smartservice.console.aliyun.com/service/ticket-detail?ticketId=000MOCKTICKET)`;
never return only the bare number or the raw JSON. If the response says success but no
verifiable ticket id can be extracted, the client does not claim creation: it reconciles the
result through the two non-mutating queries `ListTickets` and `GetTicket` inside a narrow time
window, matching creation time, title, the full body including this request marker, category
and severity. `creationState` is `reconciled_after_timeout` or
`reconciled_after_indeterminate_result` only for a unique complete match; zero, several,
incomplete pages or an interrupted reconciliation stop with an explicit prohibition on
automatic retry and require manual verification through `ticket list` or the console.

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

## Bundled Rule Integrity

`references/rules-manifest.json` is the only trusted index and has exactly the four top-level
fields `schemaVersion` (integer 1), `skillVersion` (must equal the script `VERSION` constant
and `references/manifest.json`), `contentDigest` (64-char lowercase hex) and `files`. Every
key of `files` matches the pattern `products/[a-z0-9][a-z0-9_-]*.json`, every value is an
object with only `size` (decimal integer) and `sha256` (64-char lowercase hex), and the
content digest is recomputed at every load as `SHA-256(Σ (path + "\0" + decimal-size + "\0"
+ lowercase-sha256 + "\n"))` over entries sorted by their UTF-8 path bytes — a subset is
never used to regenerate the digest. If the manifest is missing, has duplicate JSON keys,
carries an unknown field, an unsupported schema or skillVersion, or its digest cannot be
reproduced, or `references/products` is a symlink, the entire rule set is invalid: `rules
status` returns `manifestError: manifest_invalid` and `match`/`draft` run on
`DEFAULT_ISSUE`. When the manifest is valid, every listed file is verified in isolation
as a direct regular file matching `size`, `sha256`, UTF-8 encoding, absence of duplicate
JSON keys, supported schema and content safety, so a single damaged file only isolates
that file. After per-file checks, cross-file product-name and alias conflicts are
detected using NFKC + casefold + whitespace-removal normalisation: every participating
file of a conflict is isolated together, never "first one wins". JSON files present on
disk but absent from the manifest are not loaded and are reported with
`reasonCode: unlisted_rule`. ABSOLUTE PROHIBITION on relaxing any of these checks at the
customer site; the rules content is upgraded only by reinstalling a newer skill package.

## Safety Boundaries

- Bundled rules may declare only product aliases, issue types, match keywords, category
  hints and collection fields. Unknown fields, URLs, commands, scripts, SQL, regular
  expressions, execution instructions, passwords, passphrases, private keys, AccessKey
  secrets, ClientSecrets, raw API keys or any secret content are rejected at load time.
  Non-secret credential-related collection fields are allowed only for
  `authorizationStatus`, `authorizationScope`, `tokenUsage`, `apiKeyPrefix` and `apiKeyType`
  and must not carry example values.
- Customer problems, collected values, drafts, replies and credentials are never written
  into the rule package, and rule loading makes no network calls.
- All Workorder calls go through the aliyun CLI in plugin mode (`aliyun workorder
  list-products`, `aliyun workorder create-ticket`, …) with `--retry-count 0`, an explicit
  read timeout, no shell and no command history. Verified with `--cli-dry-run`, every
  Workorder operation is sent as `POST` and customer content travels in the request body,
  not in a URL query parameter. `CreateTicket`, `ReplyTicket`, `CloseTicket` and
  `EvaluateTicket` are never retried; the only follow-up to an indeterminate create is the
  non-mutating reconciliation described in step 6.
- The aliyun CLI offers no standard-input or file transport for RPC string parameters, so
  the redacted title, body, reply or evaluation text is briefly visible in the local
  `aliyun` process arguments. If that local exposure is not acceptable, stop the write
  and use the console.
- Batch creation, batch reply, batch close and batch evaluation are prohibited, as is any
  attachment upload; attachments stay in the console.
- The client never patches itself, never downloads another skill and never executes
  content fetched from outside the installed skill package at runtime. Encoding, PATH,
  authentication or API problems are solved only with the documented commands, flags and
  environment variables.

## Error Handling

Run `doctor` to see the Python, CLI, bundled rule and legacy environment state. A missing
or unusable CLI returns `readiness.state` `cli_missing` or `cli_unusable` and blocks only
the CLI-dependent capabilities. After authentication, treat the exit code and the boolean
`Success` as primary and keep the redacted `Code`, `Message` and `RequestId`; `0` and `200`
both count as success. Only an explicit `Success: false` is a deterministic API rejection;
a missing or invalid `Success`, or `Success: true` with an error `Code`, is indeterminate
and forbids retry. Distinguish `api_probe_failed` causes — expired login, network failure
and insufficient RAM permission — from `workorder_access_unavailable`, and never fall back
to another credential silently. When the bundled rule set cannot be verified, `match` and
`draft` keep running on the built-in generic template and `rules status` reports the
isolation reason honestly.

## Important Notes

- Ticket operations act on the account behind the default credential chain; state results
  as belonging to that account instead of claiming a global view.
- Ticket status labels come back in Chinese from Workorder and are translated by the
  console, for example `completed`, `awaiting your rating` and `closed`; the client
  compares both `Status.Value` and `Status.Label` before it allows any write.
- Three values must equal each other in this release and are checked at import time: the
  script `VERSION` constant, `references/manifest.json` `version` (the User-Agent source)
  and `references/rules-manifest.json` `skillVersion` (the rule package source). A drift
  in any of the three invalidates every cloud call and every rule load, so a release
  that bumps one must bump all three.
- Timeouts are bounded on every network, CLI and subprocess call; `--days`, `--page-size`
  and content lengths are range-checked instead of paging indefinitely.

## Examples

- "The ECS instance in cn-hangzhou cannot be reached over SSH since this afternoon; please
  submit a ticket for me." → `doctor`, `rules status`, `catalog products --name ecs`,
  `catalog categories --product-id <ProductId>`, `match --product-id <ProductId>
  --category-id <CategoryId>`, `draft`, `ticket preview-create`, customer confirmation,
  `ticket create`, then the clickable ticket link.
- "List my tickets from the last 30 days and show me the engineer reply of 000MOCKTICKET."
  → `doctor`, `ticket list`, `ticket get`, verbatim engineer reply, no write.
- "The engineer answered, please reply that the port is open now and then close it." →
  two separate previews, two confirmations, then `ticket reply` and `ticket preview-close`
  / `ticket close`, never in one batch.
- "I have no idea which category this belongs to, my ACK cluster just cannot schedule
  pods." → `catalog products --name ack`, `catalog categories --product-id <ack-id>`, ask
  one clarifying question to disambiguate the category, `match --product-id <ack-id>
  --category-id <CategoryId>` (if the response maps to no specific rule, `match` still
  returns the real category with `DEFAULT_ISSUE`), then `draft` and the write chain.
