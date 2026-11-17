---
name: alibabacloud-ecs-high-frequency-issues
area: service-escalation-guide
description: |
  Read-only ECS service-process guide: prepares ECS support-ticket follow-up (escalation) and service-complaint material packages and routes the case to the right official or human channel.
  Use when an ECS support ticket gets no response, is stuck or unhandled, or when the customer wants to escalate a ticket or file a service complaint.
  Triggers: "ECS ticket no response", "nobody is following up on my ECS ticket", "my ECS ticket is stuck", "ECS ticket still not handled", "escalate my ECS support ticket", "complain about ECS support", "ECS ticket progress".
  Do NOT use: technical faults -> area:disk-expand-diagnosis / area:instance-state-diagnosis / area:resource-bottleneck; punishment appeals -> area:punishment-appeal-guide; refunds -> area:unsubscribe-refund; suggestions -> product feedback channel (human; no published skill owns suggestion intake).
metadata:
  openclaw:
    requires:
      # No environment variable is required: the skill runs on the aliyun CLI
      # configuration file alone.
      env: []
      # Both binaries evidenced in the shipped code must be installed.
      bins: [aliyun, python3]
---

# ECS Ticket Follow-up and Service Complaint Guide

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Guide-type, strictly read-only skill for one service-process area: the customer already opened an ECS support ticket and now says "no reply / nobody is following up / it has been days and nothing is handled" (follow-up and escalation), or wants to complain about the support service itself (handling speed, conclusions, communication attitude). Typical customer wording: "my ECS ticket gets no response", "nobody is following up on my ECS ticket", "escalate my ECS support ticket", "I want to complain about ECS support".

The skill classifies the demand, structures the follow-up or complaint materials into a complete package, optionally corroborates the affected instances with two read-only ECS queries, and delivers routing guidance. It never resolves the underlying fault, never promises an outcome, and never touches the ticket system.

## Data Flows and External Calls

This section declares every outbound data flow of the shipped code. The skill contacts exactly the destinations below and nothing else.

- **ECS OpenAPI (regional endpoints `ecs.<region>.aliyuncs.com`, API version `2014-05-26`)** — only when the optional evidence step runs. Two read-only actions, `DescribeInstances` and `DescribeInstanceStatus`, invoked through the `aliyun` CLI as a subprocess (argument-list form, never `shell=True`). What is sent per call: `RegionId`, optional instance-ID filters, page number / page size, and the per-run `--user-agent` observability label (a random 32-hex identifier, not an account identifier).
- **STS OpenAPI (`sts.aliyuncs.com`, API version `2015-04-01`)** — one read-only `GetCallerIdentity` call (plugin-mode command `aliyun sts get-caller-identity`), used only as a credential pre-check and local traceability label.
- **No other destinations.** No HTTP signing in Python, no SDK, no telemetry, no third-party hosts. Credentials are attached by the aliyun CLI from its own default credential chain; the scripts never read, print, cache or forward any AccessKey, SecretKey or STS token.

**Read-only guarantee.** The skill is strictly read-only: it performs only the whitelisted Describe/Get queries above. It never changes cloud resources, never changes tickets, and never submits anything on the customer's behalf.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write or execute any command or script that calls a mutating cloud API — e.g. `Modify*`, `Create*`, `Delete*`, `Release*`, `Reset*`, `Revoke*`, `Attach*`, `Detach*`, `Start*`, `Stop*`, `Reboot*`, `Run*` — including "commands for the user to run manually" through this skill. This skill only outputs guidance text.
2. **API WHITELIST:** The only permitted OpenAPI actions are `DescribeInstances` and `DescribeInstanceStatus` (product `ecs`, version `2014-05-26`, invoked ONLY inside `scripts/areas/service_escalation_guide/ecs_service_escalation.py`), plus `GetCallerIdentity` (`sts`). Everything else — including any ticket-system or account-management API — is out of scope and MUST never be called. This skill has **no** ticket-system integration: it cannot query, follow up, expedite, upgrade, prioritize or withdraw a support ticket, and it must never claim otherwise.
3. **NO PROMISES (this tier's core rule):** Never state or imply a response deadline, a handling time limit, an escalation success, a responsibility finding, a compensation or refund outcome, or any other commitment the skill cannot deliver. Never say "they should reply within X" / "I have expedited it" / "you will get compensation". Quote only the customer's own words for expectations, and reword undeliverable demands per `references/service-escalation-guide__escalation-package.md`.
4. **PROGRESS SOURCE LABELING:** Ticket progress (received / replying / queued / which handler) is invisible to this skill. Any progress fact in the output must be labeled **customer-stated**, never system-verified; the two read-only ECS queries evidence *resource facts* (existence, region, state), never ticket progress.
5. **NO FABRICATION OF OFFICIAL CHANNELS:** Do not invent console button paths, entry names, URLs, hotline numbers, service-plan tiers or deadline figures. Unless the customer pasted the entry or it was verified against official documentation within the session, use the generic steps from `references/service-escalation-guide__support-process-guidance.md` and state "confirm the current entry in the official console or with human support".
6. **ABSOLUTE PROHIBITION (credential handling):** Never read, print or pass AccessKey/SecretKey/STS tokens explicitly; credentials resolve only through the aliyun CLI default credential chain. Never ask the user to paste credentials; on a credential failure guide them to verify the default credential chain with `aliyun sts get-caller-identity`.
7. **NO FABRICATION:** Every cloud fact must come from script output; every process statement must come from the embedded references. When a query fails or returns empty, record the limitation — never invent values, IDs, states or timelines.
8. **EXECUTION RULE FOR ERRORS:** On any API error, the script logs `[WARN] <Code>: <Message>` to stderr and continues; the material package is still produced with whatever evidence succeeded, and the gap is declared in the output.
9. **SCOPE BOUNDARY — identify, then hand off:** Technical faults, punishment appeals, refunds, invoices, account transfer, callback demands, product suggestions and test/misfiled tickets are NOT handled here. Run `--screen`, say plainly that this skill does not handle that area, and hand off with the target skill name and the retained service-process materials.

## Trigger Conditions

Use this skill when the customer's own wording matches the phrases the `description` advertises:

- "ECS ticket no response"
- "nobody is following up on my ECS ticket"
- "my ECS ticket is stuck"
- "ECS ticket still not handled"
- "escalate my ECS support ticket"
- "complain about ECS support"
- "ECS ticket progress"

Match on customer symptom wording, not on product vocabulary. The customer is describing a *service process*, so also screen for (and route OUT of this skill) hidden technical areas: disk full or "no space left on device", "inode" / "too many small files" (→ `area:disk-expand-diagnosis`), "expansion did not take effect" (→ `area:disk-expand-diagnosis`), instance cannot start / stuck in an intermediate state (→ `area:instance-state-diagnosis`), disk IO slow (→ `area:resource-bottleneck`). Generic words such as "complaint" or "progress" must appear together with an ECS / support-ticket context before this skill applies.

## Execution Principle

CRITICAL — MANDATORY EXECUTION: every classification, package build and cloud read MUST be produced by running the scripts under `scripts/`. You are strictly prohibited from assembling your own `aliyun` CLI commands, calling ECS APIs directly, or writing helper scripts — the entry script embeds the whitelist, retry, degradation and observability guarantees. If a script fails, read its `STATUS` / `NEXT_ACTION` and report the error; do not fall back to manual commands. The Agent's only permitted intelligence: map the customer's wording onto script parameters, and relay the script output faithfully.

## Observability

All OpenAPI calls (invoked through the aliyun CLI by the scripts) include:

- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-ecs-high-frequency-issues`.
- **session-id**: a 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every CLI command of that run, so all calls of one run can be correlated. The shared CLI layer implements this automatically: the value is generated lazily on the first call and cached for the rest of the run.

## Prerequisites

1. **aliyun CLI 3.x** — every OpenAPI call goes through it (built-in metadata mode for `ecs`, plugin mode for `sts get-caller-identity`).
2. **Python 3.9+** — standard library only; see `scripts/requirements.txt`.
3. **Credentials** — resolved automatically by the aliyun CLI default credential chain; do not read, print or pass AccessKeys or tokens explicitly.

## Authentication

```bash
cd $SKILL_DIR
python3 scripts/areas/service_escalation_guide/sts_token.py
```

Verifies the caller identity (read-only). **If it fails** because no credential is configured, guide the user to verify the default credential chain with `aliyun sts get-caller-identity` — never ask for a key pair. Codes to expect on bad credentials: `InvalidAccessKeyId` / `SignatureDoesNotMatch`. Authorization gaps on ECS reads surface as `NoPermission` / `ImplicitDeny`; the run then degrades per Absolute Rule 8 and the package is still produced.

## User Confirmation

Every cloud call this skill can make is read-only, so no per-command confirmation gate exists. Confirmation discipline applies to scope instead: before running `--collect-evidence`, restate which region and which instance IDs will be read and proceed only when the request already names them (an explicit request to check those instances is the authorization); when neither the customer nor the conversation pins the region, ask once instead of guessing. Before delivering any package, confirm with the customer that every stated fact (ticket number, timestamps, timeline) is their own account of events — the skill verifies none of it.

## Input Parameters

| Parameter | CLI flag | Required | Notes |
|---|---|---|---|
| Demand area | `--intent` (`escalate` / `complaint`) | Yes for `--build-package`; for `--screen` pass `--text` instead | From Step 1; "other" → hand off, no package |
| Ticket number | `--ticket-id` | Strongly recommended | **Pass-through text from the customer.** This skill cannot query it; never claim verification |
| First submission time | `--submitted` | Recommended | Customer-stated, e.g. `2026-09-10 14:00 +08` |
| Waited so far | `--waited` | Recommended | Customer-stated, e.g. `4 days` |
| Replies received | `--replies` | Optional | One-line summary; `none` is a valid value |
| Business impact | `--impact` | Recommended | Why it is urgent; the skill does not reprioritize the ticket itself |
| Expected outcome | `--expectation` | Recommended | Must be deliverable; the script flags promise-shaped demands (Rule 3) |
| Complaint subject | `--subject` | `complaint` intent | timeliness / outcome / attitude / other |
| Region id | `--region-id` | Only with `--collect-evidence` | e.g. `cn-hangzhou`; never guessed |
| Instance ids | `--instance-ids i-a i-b` | Optional filter | Read-only corroboration only |

Missing recommended fields never block output: the script emits the half package plus a `MISSING INPUTS` list (see `references/service-escalation-guide__escalation-package.md`).

## Orchestration

Step 1: screen the demand → Step 2: resolve any open technical area first → Step 3: build the material package → Step 4 (optional): read-only resource corroboration → Step 5: deliver per the Output Contract.

| Module | File | Responsibility |
|---|---|---|
| M1: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only permission set actually used |
| M2: Escalation package | [references/service-escalation-guide__escalation-package.md](references/service-escalation-guide__escalation-package.md) | Field definitions, material checklist, expectation discipline, no-promise rules |
| M3: Handoff matrix | [references/service-escalation-guide__handoff-matrix.md](references/service-escalation-guide__handoff-matrix.md) | Out-of-scope symptom → target skill + handoff wording |
| M4: Support process guidance | [references/service-escalation-guide__support-process-guidance.md](references/service-escalation-guide__support-process-guidance.md) | Generic self-help steps, expectation management, verified-facts-only policy |

## Execution Flow

1. **Step 1 — Classify.** Run `python3 scripts/areas/service_escalation_guide/ecs_service_escalation.py --screen --text "<customer original wording>"`. Relay the areas it reports (escalation / complaint / technical / adjacent-commercial / unclear); if two areas apply, handle the open technical area first, then the service-process materials.
2. **Step 2 — Gate.** If `--screen` returns only technical or adjacent areas, do not build a package: deliver the handoff wording from `references/service-escalation-guide__handoff-matrix.md` plus the retained facts.
3. **Step 3 — Build materials.** Collect the fields the customer already gave (never invent timestamps, ticket numbers or reply counts), then run `--build-package --intent escalate|complaint ...`. Keep producing the half package plus its `MISSING INPUTS` list instead of interrogating the customer first.
4. **Step 4 — Optional corroboration.** Only when affected instances are named and the region is pinned: run `--collect-evidence --region-id <r> [--instance-ids ...]`. Success: attach the resource fact sheet, labeled as a point-in-time read at query time. Failure: attach the recorded gap and continue (Rule 8).
5. **Step 5 — Deliver.** Follow the Output Contract: customer-stated timeline, resource facts (if any), missing inputs, generic next steps per M4, limitations block, `STATUS` relayed from the script.
6. **Step 6 — Boundary requests.** If the customer asks the skill to chase the ticket, raise priority, or promise compensation: state what this skill cannot do (Rule 2 + Rule 3), hand the finished package over for their own submission, and point to human support without promising any result.

## Output Contract

Every script ends with `STATUS: OK|DEGRADED|FAIL` and a `NEXT_ACTION:` line; exit codes: `0` = OK/DEGRADED, `1` = FAIL (required input missing), `2` = argparse usage error only. The final answer to the customer MUST relay the script outcome honestly and contain, in order:

1. The demand area found and the materials package (verbatim fields; every timeline/progress item marked *customer-stated*);
2. Optional resource facts from `--collect-evidence`, with the query time and region declared; any auto-filled or omitted parameter must be stated explicitly;
3. The `MISSING INPUTS` list, if any;
4. Next steps — generic self-help wording from M4 with the "confirm the official entry" caveat (Rule 5), or the handoff wording from M3;
5. The limitations block the script prints verbatim: no ticket-status query, no expediting, no reprioritization, no submission on the customer's behalf, no deadlines promised, no responsibility or compensation findings;
6. `STATUS` and `NEXT_ACTION` from the script.

## Important Notes

- **Duplicate tickets are not faster**: when the customer threatens to re-submit, the package says "follow-up on ticket <id>" and cites the customer's own timeline; never encourage parallel tickets.
- **Service-tier promises belong to humans**: differences in response levels, dedicated support and satisfaction callbacks must not be explained from memory; say the official plan terms need confirmation via official channels.
- **Emotional messages**: relay only facts from the structured package; never mirror blame or promise accountability outcomes.
- **Empty or failed reads**: `--collect-evidence` degrades with `[WARN]` and continues; an instance not found in the given region is reported as *not found there*, never as *does not exist*.

## Available Scripts

| Script | Purpose |
|---|---|
| `scripts/areas/service_escalation_guide/ecs_service_escalation.py` | Single entry: `--screen` (area classification), `--build-package` (material package + missing-input list), `--collect-evidence` (read-only ECS fact sheet); `--json` optional |
| `scripts/areas/service_escalation_guide/sts_token.py` | Read-only caller-identity check via `aliyun sts get-caller-identity` |
| `scripts/areas/service_escalation_guide/_cli.py` | Shared CLI layer: argument-list subprocess only, per-call timeout, retry with backoff, credential masking, session-id User-Agent |
| `scripts/areas/service_escalation_guide/_constants.py` | Endpoints, limits and embedded process knowledge (no data files per platform rule 1.1.2) |

## Error Handling

| Situation | Handling |
|---|---|
| Missing `--intent` (or `--region-id` / `--text` for its mode) | Script exits `1` with `STATUS: FAIL`; relay `NEXT_ACTION` (what to ask the customer) |
| No material supplied for the package | Half package is still emitted with `STATUS: DEGRADED` and the `MISSING INPUTS` list (never a FAIL) |
| `NoPermission` / `ImplicitDeny` on an ECS read | Name the missing action from [references/ram-policies.md](references/ram-policies.md); continue without the fact sheet |
| Region or instance id mismatch | Report *not found in the region queried*; suggest confirming the region; never conclude the resource is gone |
| `Throttling.User` / `InternalError` / timeout | Retried inside `_cli.py` (backoff, per-call timeout); persistent failure degrades with `[WARN]` and continues |
| No credentials configured | Guide `aliyun sts get-caller-identity`; do not touch keys explicitly |

## Examples

**Example 1 — follow-up with full materials**

> User: "I opened an ECS ticket three days ago about my instance and nobody is following up on my ECS ticket. Can you push it?"

1. `python3 scripts/areas/service_escalation_guide/ecs_service_escalation.py --screen --text "nobody is following up on my ECS ticket, three days no progress"` → escalation area, no technical symptom.
2. `python3 scripts/areas/service_escalation_guide/ecs_service_escalation.py --build-package --intent escalate --ticket-id 0001ABCX --submitted "2026-09-15 10:20" --waited "3 days" --impact "production website unreachable during the wait" --expectation "a progress update today and reassignment if the engineer is unavailable"`
3. Deliver: package + MISSING INPUTS (replies summary) + generic next steps + limitations. State plainly that nothing was pushed by this skill.

**Example 2 — complaint with an open technical area**

> User: "The disk-full ticket has no reply for a week, this support attitude is terrible, I want to complain."

1. `--screen` returns escalation + complaint + technical (disk-full) areas → handle the open technical area first: hand off to `area:disk-expand-diagnosis` with the ticket number and timeline attached; say a complaint does not substitute for fault diagnosis.
2. `--build-package --intent complaint --subject timeliness ...` still runs so nothing is lost; relay both outputs per the contract.

**Example 3 — demand outside scope**

> User: "Replying to my ticket is too slow — I want a refund and someone should call me."

1. `--screen` returns adjacent/commercial areas only → no package is built.
2. Handoff wording from `references/service-escalation-guide__handoff-matrix.md`: refunds → `area:unsubscribe-refund`, callback → `the customer's account manager or a console ticket asking for a callback (no callback is promised here)`; keep the ticket facts collected so far in the reply so nothing is repeated by the customer.
