---
name: alibabacloud-ecs-instance-clone-guide
description: |
  Read-only guidance for cloning an Alibaba Cloud ECS instance or copying its environment: pick the clone path (console clone, cross-region image copy, cross-account image share, replace operating system or buy from image), verify instance facts read-only, then guide the customer through console steps, scope, fees, risks and post-clone checks.
  Use when a customer wants to clone or copy a server, replicate an environment, or asks what cloning covers, costs, or whether a reported clone failure is real.
  Triggers: "clone ECS instance", "copy a server to another account", "one more server with the same configuration", "clone stuck at 0%", "page shows clone failed", "image cannot be exported", "does the clone include the data disk".
  Do NOT use for security-group rule diagnosis, IP/EIP retention, CloudMonitor agent data, on-premises image export, instance resize, batch scaling or refunds.
metadata:
  openclaw:
    requires:
      env: []
      bins: [aliyun, python3]
---

# ECS Instance Clone Guide

Answer the customer questions this tier is made of, in the customer's own
words: "I want to clone this ECS server / copy the environment to another
account / build one more machine with the same configuration - how?", "does
the clone take my data disk too, must I stop the source, does it touch the
original server?", "what will it cost?", "the clone has sat at 0% for half
an hour - is it stuck?", "the page says clone failed - may I retry?", "the
copied machine boots the wrong disk / the IP changed / monitoring jumped".

**Two core capabilities, split by user intent:**

1. **Clone guidance** - select the clone path (same-account same-region
   console clone vs the custom-image chain for cross-region / cross-account:
   image -> copy -> share -> land via new purchase or replace operating
   system), then walk the customer step by step through console entries,
   expected results, fallbacks, scope, fees, risks, progress triage, the
   post-clone checklist, platform limits and sibling-area handoffs.
2. **Read-only verification** - collect instance facts (existence, status,
   zone, type, image ID, IPs, security groups) and guard against the
   fake-failure loss pattern: a "clone failed" page can hide resources that
   were actually created, so existence is verified before any retry.

Every change is executed by the customer in the console; this skill never
performs write operations and never executes commands inside instances.

## Data Flows and External Calls

This section declares every outbound data flow of the shipped code. The
skill contacts exactly the destinations below and nothing else.

- **Alibaba Cloud ECS OpenAPI - regional endpoints
  `ecs.<region-id>.aliyuncs.com`, HTTPS, API version `2014-05-26`.** The
  scripts never sign an HTTP request themselves: they invoke the `aliyun`
  CLI as a subprocess (argument-list form, never a shell) for the two
  whitelisted read-only actions `DescribeInstances` and
  `DescribeInstanceStatus`. What is sent per call is the action name plus
  query parameters only - `RegionId`, an optional exact `InstanceName`
  filter, `MaxResults`/`NextToken` for pagination, or the `InstanceId.N`
  batch list - plus the per-run `--user-agent` observability label
  `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}` (a random 32-hex
  session id, not an account identifier). Authentication is attached by the
  aliyun CLI from its default credential chain (environment or its own
  config file); the scripts neither read, print, cache, nor forward any
  AccessKey, SecretKey or session token, and error text from the CLI is
  credential-masked before display.
- **Alibaba Cloud STS - `sts.aliyuncs.com`, HTTPS.** One read-only
  `get-caller-identity` query through the same CLI layer, used only to check
  the credential works and to derive the account UID label printed in every
  report.
- **No other network destination exists.** `scripts/axes/instance_clone_guide/clone_guidance.py`
  performs zero network calls: it only renders the deterministic guidance
  data embedded in `scripts/axes/instance_clone_guide/_constants.py`. Nothing in this package runs
  anything inside a customer instance, and nothing uploads or downloads
  customer data.

## Absolute Rules

Read and follow these rules on every run. They are mandatory; weaker
wording elsewhere does not relax them.

1. **ABSOLUTE PROHIBITION on write operations.** This skill is read-only by
   permission and by design. Its scripts, and the agent operating them,
   MUST NOT call any API that creates, updates, deletes or changes cloud
   resources - any `Create*`, `Modify*`, `Delete*`, `Release*`, `Reset*`,
   `Replace*SystemDisk*`, `Attach*`, `Detach*`, `Reboot*`, `Start*`, `Stop*`
   action, whether via a bundled script, a hand-written `aliyun` CLI
   command, the SDK, or `curl` - and MUST NOT generate, display or execute
   such an action for the user to run. The customer performs every console
   change themselves after the guidance's risk notice.
2. **API whitelist (deny by default).** The only actions this skill may
   invoke are `ecs:DescribeInstances`, `ecs:DescribeInstanceStatus` (product
   `ecs`, version `2014-05-26`) and `sts:GetCallerIdentity` (`sts` /
   `2015-04-01`). `_cli.call()` enforces the whitelist and rejects anything
   else; never work around it. Image-side and snapshot-side reads are NOT
   part of this skill: those facts come from customer console screenshots.
3. **No commands inside customer instances.** The skill never executes
   anything inside a guest OS. Guest-side facts are obtained by asking the
   customer to run the read-only listing commands from
   `references/instance-clone-guide__post-clone-checklist.md` and paste the output back, or by a
   sibling-area handoff.
4. **Risk-notice gate for guided high-risk steps.** Before guiding any
   replace-operating-system, snapshot deletion or instance-rebuild step:
   state the impact in plain words (the operating-system replacement clears
   the target system disk), advise the manual snapshot pre-backup, and get
   the customer's explicit acknowledgment. Only then describe the next
   console step. This gate is guidance-level; it is not this skill
   executing anything.
5. **Evidence only, no fabrication.** Every fact in every answer comes from
   a real read-only query result, from the deterministic script output, or
   from knowledge embedded in `references/`. Never invent instance IDs,
   image IDs, statuses, progress percentages, prices, time promises, or
   console behavior. Empty or failed results are stated as findings
   ("not found is a valid finding"), not guessed around.
6. **Scope discipline.** Stay inside "clone an instance / copy an
   environment". When the real dispute moves to security-group rules, IP
   retention, CloudMonitor agents, on-premises export, resize, batch
   orchestration, refunds or Apsara Stack (dedicated cloud), output the
   matching handoff wording from `scripts/axes/instance_clone_guide/clone_guidance.py --handoff` and
   stop.
7. **Credential hygiene.** Resolve authentication exclusively through the
   aliyun CLI default credential chain. Never ask for, accept, read, print
   or handle an AccessKey ID, AccessKey Secret or session token; masked
   CLI error text only may be shown.

## Trigger Conditions

Customer-symptom phrasing (translate the wording of the ticket into these
natural English forms):

| Customer says | Capability |
|---|---|
| "clone ECS instance", "copy a server to another account", "one more server with the same configuration", "replicate the environment", "build a new instance from my image" | 1 Clone guidance |
| "does the clone include the data disk", "image shows 300G but my disk is 5T", "must I stop the source", "will it affect the original server", "clone cost" | 1 Clone guidance (scope/fees) |
| "clone stuck at 0% for half an hour", "taking much longer than usual" | 1 Clone guidance (progress triage) |
| "page shows clone failed - can I retry?", "verify the target exists first" | 2 Read-only verification |
| "image cannot be exported", "migrate my server down to the IDC" | 1, then handoff (limits) |
| "after cloning the IP changed", "monitoring data jumps", "website broke after switching the cloned security group" | recognize + handoff, plus read-only facts where in scope |

## Execution Principle (script-only, no fallback)

All cloud reads MUST be performed through the bundled scripts. There are
exactly three entry points:

| Allowed invocation | Purpose |
|---|---|
| `python3 scripts/axes/instance_clone_guide/sts_token.py` | Identity + UID label (run first) |
| `python3 scripts/axes/instance_clone_guide/clone_readiness_check.py` | Read-only instance facts |
| `python3 scripts/axes/instance_clone_guide/clone_guidance.py` | Plan / triage / checklist / FAQ / handoff (offline, no network) |

**MUST NOT** (each is a structural violation, even if the output looks
correct): hand-write any `aliyun ecs ...` / `aliyun sts ...` command for
diagnosis; import the SDK or call the OpenAPI over HTTP directly; write
ad-hoc helper scripts; wrap the entry scripts with stdout/stderr redirection
to files; retry a failed command in a different shape. If a script fails,
stop and report the error verbatim (see Error Handling).

## Observability

Every API call made by this skill carries a per-run User-Agent label so
Alibaba Cloud-side tracing attributes the request to this skill:

- Template: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`
- `{session-id}` is a freshly generated 32-character hex string
  (`uuid.uuid4().hex`), one value shared by ALL calls of a single script
  run; it contains no account or resource identifiers.
- The label is attached via the aliyun CLI `--user-agent` parameter inside
  the shared layer `scripts/axes/instance_clone_guide/_cli.py`, so every CLI invocation of every
  entry script includes it automatically.
- The session id is echoed once to stderr per run for incident correlation.

## Prerequisites

- Alibaba Cloud CLI 3.x installed and configured through its default
  credential chain (`aliyun configure`). Installation:
  https://help.aliyun.com/document_detail/121541.html
- Python 3.9+; standard library only (`scripts/requirements.txt` lists no
  third-party dependency).
- The RAM grants of `references/ram-policies.md` attached to the calling
  identity: three read-only actions, no wildcard, nothing else.
- A `RegionId` is required for every read: ask the customer for the region
  shown in their console region selector if not stated.

## Authentication

The scripts never accept a credential argument and never prompt for one.
They run `aliyun sts get-caller-identity` through `scripts/axes/instance_clone_guide/_cli.py` (plugin
mode, lowercase-hyphenated command; RPC products such as `ecs` keep
PascalCase actions), which authenticates via the default credential chain
(environment variables or `~/.aliyun/config.json`, per the CLI's own
resolution). If the identity check fails, guide the customer to configure
the CLI (`aliyun configure`) and stop; NEVER ask them to paste an AccessKey
ID, AccessKey Secret or session token into the conversation.

The derived account UID is printed in every report: all read-only evidence
covers exactly that account and the one queried region.

## User Confirmation

- Running the read-only scripts needs no confirmation, but before executing
  any script restate the scope in one sentence: the account UID, the region,
  the instances involved, and what will be checked.
- Customer-side high-risk guided steps (replace operating system, snapshot
  deletion, rebuilding from snapshot) MUST carry the rule 4 risk-notice gate
  with the customer's explicit acknowledgment before the next guided step.
- NEVER ask the user to confirm credential values; if credentials are
  missing, direct them to `aliyun configure`.

## Input Parameters

| Parameter | Required | Source | Used by |
|---|---|---|---|
| `--region-id` | yes | customer or console screenshot | `clone_readiness_check.py` (every read is single-region) |
| `--instance-ids` (comma list) / `--instance-name` (exact name) | no (strongly recommended) | customer | existence, status, count verification |
| `--account-relation` same / cross | yes for planning | customer statement | `clone_guidance.py --plan` |
| `--region-relation` same / cross | yes for planning | customer statement | `clone_guidance.py --plan` |
| `--target` existing-instance / new-purchase | yes for planning | customer statement | landing-step selection |
| `--goal` clone / export-offline / batch-scale | no | customer statement | scope gate (handoff branches) |
| `--progress`, `--baseline`, `--first-image` | for triage | customer screenshot + narration | `clone_guidance.py --triage` |
| `--profile` | no | environment | multi-account runs: one profile per account, never cross-imported |

## Orchestration

```text
customer symptom (account? region? target? goal?)
        |
        v
[capability 2] sts_token.py -> clone_readiness_check.py (region-scoped reads)
        |          facts: exists? status? count? image ID? SGs? IPs?
        v
[capability 1] clone_guidance.py --plan / --triage / --topic / --handoff
        |          deterministic path + risk notices + fees + evidence list
        v
customer performs console steps (after risk-notice gate) -- skill never writes
        |
        v
re-verify read-only (clone_readiness_check.py) + post-clone checklist
```

## Module Index

| File | When to load |
|---|---|
| `references/instance-clone-guide__clone-solution-matrix.md` | path selection and the four chain steps with their traps |
| `references/instance-clone-guide__clone-scope-and-billing.md` | data-disk / downtime / source-impact scope, fee composition, export limits |
| `references/instance-clone-guide__progress-triage.md` | slow or 0% clone/image tasks, escalation packet |
| `references/instance-clone-guide__post-clone-checklist.md` | after any clone completes or is reported failed |
| `references/instance-clone-guide__handoff-map.md` | symptom belongs to a sibling area |
| `references/ram-policies.md` | permission setup and `NoPermission` / `ImplicitDeny` follow-up |

## Available Scripts

| Script | Purpose |
|---|---|
| `scripts/axes/instance_clone_guide/clone_readiness_check.py` | The ONLY cloud-reading entry: whitelisted `DescribeInstances` + `DescribeInstanceStatus` for one region of the current account; existence/count verdicts, table + detail lines + degradation log; `--json` for structured output. |
| `scripts/axes/instance_clone_guide/clone_guidance.py` | Offline engine: `--plan` solution matrix, `--triage` progress branches, `--checklist` post-clone list, `--topic`/`--list-topics` embedded FAQ, `--handoff` sibling-area matcher, `--selftest` pure-function boundary checks. No network calls. |
| `scripts/axes/instance_clone_guide/sts_token.py` | Identity verification + UID traceability label (read-only). |
| `scripts/axes/instance_clone_guide/_cli.py` (internal) | Shared layer: API whitelist, argument-list subprocess only with per-call timeout, transient-error retry, credential masking, pagination, session-id User-Agent. |
| `scripts/axes/instance_clone_guide/_constants.py` (internal) | All guidance data embedded as constants (MUST 1.1.2: no data files in scripts/). |

## Execution Flow

1. **Step 1 - Scope restatement**: parse the symptom into account relation,
   region relation, target carrier, goal; echo them back with the region and
   instance IDs. Missing planning inputs are asked in ONE short message;
   never guessed.
2. **Step 2 - Identity**: run `scripts/axes/instance_clone_guide/sts_token.py`; confirm the UID owns
   the discussed resources (cross-account cases: the other account is a
   customer self-check boundary).
3. **Step 3 - Facts**: run `scripts/axes/instance_clone_guide/clone_readiness_check.py --region-id
   <region> [--instance-ids ...]`; relay the found/not-found verdicts and
   the region instance count.
4. **Step 4 - Plan or triage**: `scripts/axes/instance_clone_guide/clone_guidance.py --plan ...` for
   the path, `--triage ...` for a slow/stuck task, `--topic <key>` for
   scope/fee/limit questions, `--handoff "<sentence>"` when the request
   drifts out of clone scope.
5. **Step 5 - Guide with the gate**: deliver each console step with its
   expected result and fallback; apply the rule 4 risk-notice gate before
   any high-risk step; state fees first; never promise durations.
6. **Step 6 - Re-verify**: after the customer acts, re-run step 3 and walk
   `--checklist`; on contradiction between the page and the reads, output
   the verified facts + the missing self-check items + the escalation
   wording - no success/failure verdict beyond the evidence.

## Error Handling

| Case | Contract output | Agent action |
|---|---|---|
| `NoPermission` / `ImplicitDeny` on any read | `[WARN]` line + degraded report, run continues where possible | point to the exact missing action in `references/ram-policies.md`; hand the customer the smallest policy fragment; NEVER attempt another route to the data |
| `InvalidParameter` / `MissingParameter` | `[WARN]` + continue; or `STATUS: FAIL` when a required input is unusable | fix the input from the customer's own wording (region ID format `cn-...`, exact instance name) |
| `Throttling.User` | handled inside `_cli.py`: up to 3 attempts, linear 2s/4s backoff | none; if it persists, report verbatim |
| `InternalError` / `ServiceUnavailable` / timeout | same backoff-retry inside `_cli.py` | if retries exhaust, report verbatim, degrade with `[WARN]` |
| requested instance absent from the region | `NOT FOUND` verdict line - a valid finding, exit 0 | re-check region selector and account; NEVER conclude "it was deleted", NEVER re-clone on this evidence alone |

## Status and Next-Action Contract

Both cloud-side scripts and the guidance engine end with `STATUS:` and
`NEXT_ACTION:` lines (stderr in `--json` mode, where the `status` /
`next_action` fields are also embedded in the JSON). `STATUS: OK` = every
declared evidence call succeeded; `STATUS: DEGRADED` = at least one call or
data source failed but partial evidence was collected (the Graceful
Degradation Log lists each `[WARN|DEGRADE]` reason verbatim); `STATUS: FAIL`
= the run produced no usable evidence. Exit codes: 0 = OK/DEGRADED, 1 =
FAIL. Usage errors (argparse) exit 2. `NEXT_ACTION` names the single most
useful follow-up step and is advisory: it always stays inside this skill's
read-only + guidance boundary, and the agent MUST NOT treat it as permission
to touch anything outside it.

## Important Notes

- The permission model of this skill: read-only cloud queries plus manual
  guidance; the customer executes all changes in the console; no command
  execution inside instances. If the customer wants the agent to act FOR
  them, state this boundary and give the console entry instead.
- Read-only data boundary: one account (the credential's) and one region
  (the `--region-id`) per run. Cross-account and cross-region facts are
  customer self-check items. Human agents hit the same wall - say so.
- Image/snapshot task progress is invisible to this skill (not in the
  verified read surface): progress comes from the customer's screenshot.
- Page status and the platform's real result can disagree BOTH ways (a real
  ticket reported failure while 25 instances had been created): existence is
  only ever concluded from read-only queries and console listings.
- Duration judgments are relative to the customer's own normal completion
  time; there is no official timing standard in this tier's evidence. The
  region behind one "slow region" explanation was masked in the evidence
  and stays generic.
- Quoted agent wordings (the three export restrictions, the snapshot price
  example) are marked in the references; verify them against the official
  documents before repeating them as rules.
- Windows clone specifics and "can this spec run my workload" capacity
  verdicts are out of scope for this release (no evidence base); state the
  boundary, do not improvise.
- `DescribeAvailableResource` is a verified read-only API for this tier,
  but its RAM permission point was not supplied by the contract; until that
  point is confirmed it is neither called nor declared (see
  `references/ram-policies.md`). Zone-inventory checks are console
  self-service for now.
- No ticket identifiers are quoted to customers; references to "a real
  ticket in this tier" are the evidence base, not something to paste.
- Markdown links are relative paths; official help-center URLs are listed
  in the references (verify them before quoting - captured during tier
  research).

## Final Answer Contract

The final answer to the user MUST:

1. Lead with the scope restatement: account UID + region + instance IDs,
   and the data boundary in one line.
2. Relay the scripts' `Summary` / verdict lines faithfully, including the
   `STATUS` outcome (`OK` / `DEGRADED` / `FAIL`) and every
   `[WARN|DEGRADE]` reason; never soften a degradation.
3. Quote only real returned values or embedded-knowledge wording; declare
   every auto-filled parameter (e.g. the default profile used); NEVER
   mention internal mechanics (User-Agent, session-id, retry/backoff, the
   masking layer).
4. Give next steps ONLY as manual guidance: numbered console steps with
   expected results and fallbacks, the risk-notice gate before any
   high-risk step, fee composition up front, and the post-clone checklist.
   Never promise a duration, never a capacity verdict, never an outcome on
   the customer's behalf.
5. For out-of-scope demands, state the boundary, deliver the matching
   `--handoff` wording with the collected evidence list, and stop.
6. End with the concrete human action and where to do it (console entry,
   Billing Management console, or support ticket with the escalation
   packet), never with an offer that this skill could do it for them.

## Examples

1. **Input**: "I need one more server with the same configuration as
   i-bp1clonesrc001 (cn-hangzhou), but in my other account 1234567890123456,
   same region. Steps, costs, and will the source be affected?"
   **Expected**: scope restatement (cross-account, same-region, goal clone)
   -> `sts_token.py` -> `clone_readiness_check.py --region-id cn-hangzhou
   --instance-ids i-bp1clonesrc001` -> `clone_guidance.py --plan
   --account-relation cross --region-relation same --target new-purchase`
   -> chain: custom image (tick data disks) -> share to the UID -> buy from
   shared image in the other account; fees (free image, billable snapshots,
   new instance in target account); source unaffected + low-peak + snapshot
   first; the other account's visibility is a customer self-check item.
2. **Input**: "The clone page shows FAILED for i-bp1target99 in
   cn-hangzhou. Should I just run it again?"
   **Expected**: DO NOT retry -> `clone_readiness_check.py --region-id
   cn-hangzhou --instance-ids i-bp1target99` -> relay FOUND (exists despite
   the failure page) or NOT-FOUND verdict lines + the region count; if
   found: stop, record IDs/time, explain the duplicate-charge risk,
   escalation wording for the status-display issue; if not found: re-check
   region/account, then continue guidance.
3. **Input**: "My clone has been stuck at 0% for 40 minutes; it normally
   takes 5. It is the first custom image on this account, region
   cn-shanghai."
   **Expected**: `clone_guidance.py --triage --progress 0 --baseline
   much-longer --first-image yes` -> branch `stuck-zero-long`: wait
   explanation is NOT enough -> collected evidence + escalation packet;
   existence re-check before any retry; no time promise.
