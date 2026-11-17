---
name: alibabacloud-ecs-account-transfer-guide
description: |
  Guides cross-account ECS instance transfer and verified-entity change: eligibility verdict, condition checklist, image-share fallback (snapshot-first), post-transfer checks, blocker triage. The only write action is a confirmation-gated snapshot backup.
  Use when a customer wants to move ECS to another account, change the verified entity, merge accounts, or asks what happens to IPs, snapshots, or domains after transfer.
  Triggers: "transfer ECS to another account", "bought the server in the wrong account", "change the verified company entity", "merge two Alibaba Cloud accounts", "ECS account transfer failed", "real-name authentication type is inconsistent", "share custom image with another account".
  Do NOT use: disk expansion -> alibabacloud-ecs-disk-expand-diagnosis; stuck start/stop -> alibabacloud-ecs-instance-state-diagnosis; disk IO -> alibabacloud-ecs-disk-io-diagnosis; refunds -> human support.
metadata:
  openclaw:
    requires:
      # No environment variable is required: the skill runs on the aliyun CLI
      # configuration alone.
      env: []
      # Both binaries evidenced in the shipped code must be installed.
      bins: [aliyun, python3]
---

# ECS Cross-Account Transfer and Verified-Entity Change Guide

Scenario display name: **ECS cross-account transfer & entity-change guidance**.

This skill guides the single symptom axis of moving Alibaba Cloud ECS
resources between accounts: account-to-account instance transfer, real-name
entity (subject) change, "bought it in the wrong account", account merging,
and the cross-account migration fallback when a direct transfer is not
possible. Every rule was distilled from real support-ticket dialogues; the
five hard transfer conditions and the direction matrix below are the
recurring answers support gave, fixed into a checklist so nothing depends on
someone's memory.

What it does end to end:

1. decide **whether a direct transfer is possible at all** (direction of
   real-name types, same enterprise entity name, campaign/discount purchase,
   distribution relationship, region), with a three-way verdict and the
   doc anchor behind each reason;
2. run the **pre-transfer condition checklist** against live instance data
   (zone / VPC / vSwitch / security groups / bound EIP / key pair, target
   zone sellability) and tell the customer which facts remain manual;
3. when a direct transfer is impossible, guide the **shared-custom-image
   migration path** — cross-region copy first, share by account UID, then
   new purchase or Replace Operating System — under the **snapshot-first
   rule**: before any guidance or action that would permanently destroy the
   current system-disk data, the confirmation-gated snapshot backup runs
   first;
4. close with the **post-transfer checklist** (public IP/EIP, snapshots and
   images stay in the source account, DNS up to 48h, third-party IP
   bindings, discount loss) and route mixed-in products (domains move on
   their own track; managed databases do not move this way at all).

## Permission Model and Absolute Rules

This skill is NOT strictly query-only. It has exactly two call layers, and
they are enforced in code, not just on paper:

* **Layer A (automatic): query-class evidence.** `DescribeInstances`,
  `DescribeInstanceStatus`, `DescribeAvailableResource`, `GetCallerIdentity`
  — none of them changes any resource, so they run without per-call
  confirmation.
* **Layer B (confirmation gate): one snapshot backup.** The ECS
  `CreateSnapshot` action (parameters `DiskId` + `RegionId`) is the ONLY
  action in this skill with a write effect. The entry script refuses to
  invoke it until the user has approved this exact call and `--confirm yes`
  is passed; approval is valid for that single call only.

**ABSOLUTE PROHIBITION (violations break the permission model):**

1. Outside the whitelist in `references/ram-policies.md`, you MUST NOT
   generate, write, or execute any command or script that invokes a
   mutating or external-effect action — wildcard verb classes
   `Modify*`, `Delete*`, `Create*`, `Attach*`, `Detach*`, `Release*`,
   `Reset*`, `Replace*`, `Revoke*`, `Accept*`, `Apply*`, `Cancel*`,
   `Join*`, `Leave*`, `Reboot*`, `Start*`, `Stop*`, `Import*`, `Put*`,
   `Bind*`, `Unbind*` — with the single confirmed exception of Layer B
   (`CreateSnapshot`, behind the gate). This prohibition also covers
   "helper scripts" or step lists that tell the USER to run those actions
   as part of an automated flow: mutating console steps are handed over as
   described guidance only, never as generated command lines.
2. The transfer itself is NEVER automated. No transfer-initiation /
   approval / acceptance API exists in the verified evidence for this
   tier; the wizard is driven by the customer in the ECS console, and this
   skill judges, prepares, guides, and verifies around it without
   inventing calls.
3. In-guest execution (Cloud Assistant command dispatch) is NOT enabled in
   v1. If a customer asks to verify files inside the instance after
   migration, decline: transfer-eligibility facts all live account-side;
   ask them to paste readings instead. Any future enablement must obey the
   batch low-risk whitelist: one whitelisted display-only command per
   call, tell-then-confirm per call, anything off the whitelist refused
   without exception, failures degrade with `STATUS: DEGRADED`.
4. Destructive and commercial classes (instance release, snapshot/image
   deletion, refund, unsubscription, account cancellation) are never
   executed or scripted: console entry + risk statement + human steps only.
5. No cross-account data plane: with a credential from account A the skill
   only sees A's resources; facts about the other account come from its
   owner's own queries or declarations.

## Data Flows and External Calls

The bundled code contacts exactly two kinds of destinations and nothing
else:

* **Alibaba Cloud ECS OpenAPI** (`{region}.ecs.aliyuncs.com` via the aliyun
  CLI, RPC version `2014-05-26`): the three query-class actions above plus,
  behind the Layer B gate, `CreateSnapshot`. What leaves the machine per
  call is the action name plus parameters (region, instance/disk/zone
  filters, snapshot name, pagination) and the per-run `--user-agent`
  observability label `AlibabaCloud-Agent-Skills/alibabacloud-ecs-account-transfer-guide/<session-id>`
  (a random 32-hex identifier, not an account identifier).
* **Alibaba Cloud STS** (`sts.aliyuncs.com`): one `get-caller-identity`
  request without parameters to verify the credential and derive the
  account UID.

Authentication is attached by the aliyun CLI from its own default credential
chain; the scripts never read, print, cache, or forward any AccessKey,
Secret, or token value, and every CLI error string is credential-masked
before it can surface. No other host, port, or protocol is used; there are
no local state files and no outbound telemetry.

## Execution Principle (script-only, no fallback)

All cloud evidence and all guidance text MUST come from the bundled scripts
under `scripts/`. There are exactly two invocations:

| Allowed invocation | Purpose |
|--------------------|---------|
| `python3 scripts/axes/account_transfer_guide/sts_token.py` | verify the credential, print the account UID (run first) |
| `python3 scripts/axes/account_transfer_guide/transfer_guide.py` | single entry point for all modes |

**Prohibited — do NOT** reproduce any of this by other means (each is a
structural violation even if the output looks correct):

* assembling raw `aliyun ...` CLI commands (including "just one query" or a
  manual snapshot call) instead of running the entry script;
* running credential inspection commands — credentials resolve exclusively
  through the aliyun CLI default credential chain;
* writing ad-hoc helper scripts, inline SDK/curl/HTTP code, or answering
  eligibility/condition questions "from memory" without the embedded
  knowledge the scripts emit;
* executing any mutating API other than the Layer B gated snapshot backup.

If a script fails (non-zero exit, no structured output, permission error),
**stop and report the error verbatim** (credentials masked) — never fall
back to hand-built commands.

## Credentials

The aliyun CLI default credential chain resolves authentication: a
platform-injected temporary credential, the active CLI profile, or an
instance RAM role. The scripts take no credential arguments, never prompt
for or read key values, and mask credential material out of every error
line (`_cli.py`). When no valid credential exists the entry point explains
that `aliyun configure` is needed and stops with `STATUS: FAIL`; it does
not proceed on guesses.

## User Confirmation

Before any Layer B invocation (and before enabling any future guest-command
channel) you MUST:

1. tell the user, in one message, **what will run** (snapshot of the exact
   disk id), **its impact** (a snapshot appears in the account and accrues
   snapshot storage fees until the customer deletes it; nothing on the disk
   itself changes), and **reversibility** (a copy; removable by a human
   later);
2. obtain the user's explicit approval for that exact call;
3. re-run with `--confirm yes`. The gate is per call: a new disk or a
   repeated backup needs a new approval.

Running `--create-snapshot` without user approval is a permission-model
violation even if it succeeds. Without `--confirm yes` the script itself
refuses and echoes the impact statements, so the agent cannot "forget" to
tell the user.

## Trigger Conditions

Customer-symptom phrases (say the line, this skill answers):

- "transfer ECS to another account" / "move my server to a different account"
- "bought the server in the wrong account" / "accidentally registered a second account"
- "change the verified company entity" / "transfer to another company subject"
- "merge two Alibaba Cloud accounts"
- "ECS account transfer failed" / "transfer stuck in under review"
- "real-name authentication type is inconsistent"
- "the vSwitch cannot be selected" during a transfer
- "share custom image with another account"
- "will the public IP change after the transfer" / "snapshots disappeared after transfer"

Decision tree pointers (full matrix in `references/account-transfer-guide__transfer-conditions.md`):

1. Is the ask a cross-account move / entity change? No -> `--handoff` routes it.
2. Direct transfer possible? -> `--assess` (enterprise pairs need the same
   entity AND identical name; individual -> enterprise allowed; campaign
   instances and cross-region moves never).
3. Possible -> `--precheck` the five conditions, then guide the console
   wizard, then `--guide post-transfer`.
4. Not possible -> `--guide image-migration` with the snapshot-first rule.
5. Pasted console error mid-flow -> `--blocker`.

## Input Parameters

| Name | Required | Applies to | Notes |
|------|----------|-----------|-------|
| region id | yes (never guessed) | `--precheck`, `--create-snapshot` | Ask if the customer does not know; `sts_token.py` proves which account the credential sees |
| instance id / public ip | no | `--precheck` | Filter; when the customer cannot find IDs (real ticket pain), omit it and let the script list all |
| source-type / target-type | yes for `--assess` | `--assess` | individual / enterprise; "unknown" is allowed and degrades the verdict |
| entity-relation | enterprise pairs | `--assess` | same / different / unknown — identical NAME required for "same" |
| cross-region / campaign-instance / reseller-account | facts | `--assess` | yes / no / unknown |
| target-zone (+ target-instance-type / charge-type) | no | `--precheck` | sellability pre-check for the destination vSwitch zone |
| disk id + snapshot name | yes for the gate | `--create-snapshot` | `d-...` validated; name defaults when omitted |
| confirm | gate key | `--create-snapshot` | `yes` opens the per-call confirmation gate |
| profile | no | both scripts | passthrough to the aliyun CLI profile, optional |

Every auto-filled or defaulted value (snapshot name, pagination page size,
STS defensive region) is declared in the report; region and account-side
facts are NEVER auto-filled.

## Orchestration

```
Customer symptom (transfer / entity change / wrong account / merge)
    |
    +-- K7 routing? -- yes --> hand off (disk-expand / instance-state /
    |                           disk-io skills, database line, Billing
    |                           Center) -- stop, with a handoff summary
    +-- K1 --assess: direction x entity x campaign x reseller x region
    |       |- NOT_ELIGIBLE ----------> K3 --guide image-migration
    |       |                               (snapshot-first, gated backup,
    |       |                                cost + data-loss statements)
    |       |- NEEDS_MANUAL_REVIEW ---> collect facts / backend ticket
    |       |                               (report data to attach:
    |                               instance id + both UIDs + error text)
    |       |- ELIGIBLE --------> K2 --precheck (live queries, parallel-safe)
    |                             |   - instance IDs, zone, VPC, vSwitch,
    |                             |     security groups, EIP/keypair to detach
    |                             |   - optional zone sellability check
    |                             +--> console wizard guidance (human clicks,
    |                                  flow anchor) --> K4 --guide
    |                                  post-transfer (IP/EIP/snapshots/DNS)
    +-- any pasted error mid-flow --> K6 --blocker --> fix or ticket
```

## Module Index

| Module | File | Purpose |
| --- | --- | --- |
| M1 | [references/account-transfer-guide__transfer-conditions.md](references/account-transfer-guide__transfer-conditions.md) | five hard conditions, direction matrix, timing, blocker catalog, human console flow |
| M2 | [references/account-transfer-guide__migration-by-image.md](references/account-transfer-guide__migration-by-image.md) | image-share fallback steps, snapshot-first rule, fees/data-loss statements |
| M3 | [references/account-transfer-guide__post-transfer-checklist.md](references/account-transfer-guide__post-transfer-checklist.md) | IP/EIP/snapshots/DNS/third-party/filing/discount verification list |
| M4 | [references/account-transfer-guide__related-products-and-account-rules.md](references/account-transfer-guide__related-products-and-account-rules.md) | domain/EIP/database rules, account mechanics, routing order and handoff wording |
| M5 | [references/account-transfer-guide__help-links.md](references/account-transfer-guide__help-links.md) | evidenced official links only + the not-evidenced list that must never be faked |
| M6 | [references/ram-policies.md](references/ram-policies.md) | Layer A grant, Layer B gate wording, reserved actions, denial recovery |

## Execution Flow

1. **Scope check (MANDATORY first).** Does the request concern moving ECS
   resources across accounts, an entity change, or account merging? If it
   clearly belongs elsewhere, run `--handoff` with the customer's wording
   and use the routing table instead of continuing.
2. **Credential pre-check.** Run `python3 scripts/axes/account_transfer_guide/sts_token.py`; record the
   account UID (echo it to the customer — it doubles as the image-share
   target value). On credential errors, follow Credentials and stop.
3. **Collect the K1 facts** (both real-name types, same entity name?,
   cross-region?, campaign purchase?, reseller?) — ask, do not guess.
4. **Run `--assess`** and relay the verdict with its reason list and the
   doc anchor; hedged rows (single-source evidence) keep their hedge.
5. **Eligible path:** run `--precheck` (add `--target-zone` when the
   customer is at the vSwitch step) and walk the five conditions; hand the
   console wizard over as guidance (the customer clicks); finish with
   `--guide post-transfer`.
6. **Not-eligible path:** run `--guide image-migration`; before any step
   that would replace an existing system disk, execute the snapshot-first
   backup through the confirmation gate (User Confirmation section).
7. **Mid-flow errors:** pipe the pasted wording into `--blocker` and
   deliver the matched fix; on no match, emit the ticket package
   (instance id + both account UIDs + exact error text).
8. Summarize per the Final Answer Contract below; every claim either cites
   the script evidence or the embedded knowledge file.

## Observability

To label all CLI-generated cloud calls, a 32-character hexadecimal session
identifier is created at script start; format: `uuid.uuid4().hex`.

**User-Agent template:**

```
AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
```

- `{skill-name}`: fixed value `alibabacloud-ecs-account-transfer-guide`
- `{session-id}`: the random value generated per script run (32-hex)

Implementation: `scripts/axes/account_transfer_guide/_cli.py` generates the session-id once per process
(`uuid.uuid4().hex`), caches it, and attaches it to every call as
`--user-agent` via `user_agent()`, so all API requests of one diagnosis run
share a single traceable label. The label carries no account, resource, or
customer information.

## Available Scripts

| Path | Role |
| --- | --- |
| `scripts/axes/account_transfer_guide/transfer_guide.py` | single entry point; modes `--assess`, `--precheck`, `--create-snapshot` (gated), `--guide {image-migration,post-transfer,account-rules}`, `--blocker TEXT`, `--handoff TEXT`, `--list-links`; `--json` for machine output |
| `scripts/axes/account_transfer_guide/sts_token.py` | identity verification and UID derivation |
| `scripts/axes/account_transfer_guide/_cli.py` | shared call layer: argument-list subprocess only (never shell), per-call timeout, transient-error retry, credential masking, session-id User-Agent |
| `scripts/axes/account_transfer_guide/_constants.py` | embedded knowledge tables + API allowlist (no data files) |
| `scripts/requirements.txt` | dependency list — standard library only |

## Error Handling

| Situation | Symptom in output | What to do |
|-----------|-------------------|-------|
| NoPermission / ImplicitDeny on a query action | `[WARN]` line + entry in `errors`, run continues degraded | name the missing action, point at `references/ram-policies.md` Layer A; ask for the grant then re-run — never broaden scope silently |
| NoPermission on the gated snapshot | `STATUS: FAIL`, code shown | explain the grant path; do not work around via console click-through |
| Invalid parameter (bad region/instance/disk id) | `STATUS: FAIL` with the offending value | ask the customer to confirm the value; never invent one |
| Resource not found / empty result | explicit "no instance matched" line | verify region and account (`sts_token.py` in the other account) |
| Throttling (quota) | `[WARN] ... transient error ... retrying` then failure after retries | relay the hint, advise spacing calls out |
| CLI timeout / connection failure | `timed out after Ns` in `errors` | report verbatim; the affected section says it could not be verified — do NOT guess its content |
| Non-ECS symptom | `--handoff` routing verdict | hand off with the customer's original wording attached |

## Important Notes

1. The transfer wizard is driven by the customer in the console
   (about 30 minutes typical); this skill judges, prepares, and verifies — it
   never clicks for them and never claims a transfer succeeded without
   evidence.
2. Hedged rules stay hedged: enterprise-to-individual non-support, the
   once-per-half-year frequency, the reseller block, and the
   "no re-filing after IP change" wording are single-source; present them
   with "confirm against the official transfer-limitations / filing rules"
   — never as certain verdicts.
3. Snapshots and custom images never ride along with a transferred
   instance; EIP transfer is a separate restricted flow (post-paid EIPs,
   enterprise same-entity). State both BEFORE the transfer starts.
4. A discounted instance that transfers loses further discount
   eligibility — quote it proactively.
5. If the customer's real goal is refund/re-buy rather than transfer,
   route per M4: commercial flows are human steps.
6. Report honestly: unverified is written as unverified; failed queries
   keep their `errors` lines. An empty or failed query is never replaced
   with plausible numbers or facts.

## Examples

### Example 1: transfer possible, wizard blocked

**Input**: "The transfer to our other enterprise account keeps failing — at
the network step the vSwitch cannot be selected."

1. `sts_token.py` -> UID of the initiating account (confirm it is the right one).
2. `--assess --source-type enterprise --target-type enterprise --entity-relation same`
   -> eligible subject to the five conditions.
3. `--blocker "the vSwitch cannot be selected"` -> the same-zone rule fires.
4. `--precheck --region-id cn-hangzhou --instance-id i-xxx` -> instance zone
   and VPC printed.
5. Tell the customer: create/pick a vSwitch in that exact VPC + zone, retry
   the wizard; close with `--guide post-transfer`.

### Example 2: wrong account purchase, mixed resources

**Input**: "I bought a server and a domain in the wrong account — can you
move them to my other account?"

1. Routing: in scope (plus one rule card for the domain).
2. `--assess` with the campaign question first (likely a campaign purchase)
   -> campaign instances are not directly transferable.
3. `--guide image-migration`: create custom image -> share to the other
   account's UID -> new purchase there; state the data-loss + fee lines.
4. M4 card for the domain: online transfer (real-time, valid + verified)
   and offline transfer (~5 working days), links from M5.
5. Explain the 6-accounts-per-phone rule that caused the duplicate account.

### Example 3: after-transfer breakage

**Input**: "After the account transfer my site is down — the IP changed and
my snapshots are gone."

1. M3 checklist: the public IP changed because the EIP did not ride along
   (post-paid-only transfer path), snapshots stay in the SOURCE account
   (console path given), DNS needs repointing (up to 48h, probe link),
   third-party bindings on the old IP must be updated by the customer.
2. Output `--guide post-transfer` rows with the customer's facts filled in
   from the ticket text — no new cloud call can see the other account.

## Final Answer Contract

1. Open with the K1 verdict (or the routed handoff) as `--assess` /
   `--handoff` emitted it: `TRANSFER_ELIGIBLE` / `TRANSFER_NOT_ELIGIBLE` /
   `NEEDS_MANUAL_REVIEW` + reasons with their doc anchors; hedge exactly
   where the script hedges — never upgrade a caveat to a promise.
2. Query facts come from script output: quote real fields (instance IDs,
   zones, VPC/vSwitch, security groups, EIP/key pair, target UID); if a
   query failed, show the `[WARN]` / `errors` line and mark that section
   "could not be verified", never substitute plausible values.
3. Console steps are guidance with anchors, never generated command lines;
   any mutating outcome is framed as "you click this" with its risks.
4. Deliver the snapshot-first statement whenever an OS replacement is
   advised, and the post-transfer checklist at the end of every eligible
   transfer conversation.
5. Every auto-filled or defaulted value (snapshot name, page size, STS
   defensive region) is declared; region and account identities are never
   implied — they come from input or from `sts_token.py`.
6. End by restating: what was verified vs self-declared vs backend-needed,
   and the single next action.
7. Output contract: the final report mirrors the script's `Summary` and
   closes with `STATUS: OK|DEGRADED|FAIL` and one `NEXT_ACTION: ...` line.
   Script exit codes: 0 = OK/DEGRADED, 1 = diagnosed failure, 2 = argparse
   usage error only (unknown option — never a diagnosis outcome).
