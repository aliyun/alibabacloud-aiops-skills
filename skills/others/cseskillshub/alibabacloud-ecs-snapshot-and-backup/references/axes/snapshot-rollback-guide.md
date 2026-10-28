---
name: alibabacloud-ecs-snapshot-rollback-guide
description: |
  Guides ECS snapshot rollback and system disk restoration: eligibility evidence,
  restore-point selection, a confirmation-gated pre-rollback backup, and manual
  console steps; the rollback itself is never executed by the skill.
  Use when an ECS disk must be restored to an earlier snapshot, or data is
  missing after a rollback or an expired snapshot.
  Triggers: "roll back disk to snapshot", "restore system disk from snapshot",
  "recover data lost after rollback", "snapshot expired and deleted",
  "rollback button no response", "stuck stopping during rollback",
  "connection refused after rollback", "NoPermission snapshot rollback".
  Do NOT use: snapshot management, deletion or billing ->
  alibabacloud-ebs-disk-snapshot-management; disaster recovery ->
  alibabacloud-ecs-disaster-recovery-snapshot; instance stuck stopping/starting ->
  alibabacloud-ecs-instance-state-diagnosis.
metadata:
  openclaw:
    requires:
      env: []
      bins: [aliyun, python3]
---

# ECS Snapshot Rollback & System Disk Restoration Guide

Helps a customer answer "can this disk be rolled back to which snapshot, what
will that cost me in data, and how do I actually do it" — then guides the
manual rollback and handles its aftermath. Typical customer wordings: "roll
back the disk to yesterday's snapshot", "restore the system disk to the state
before the ransomware", "my snapshot expired and was deleted, can you recover
it", "I rolled back and my site is connection refused", "the rollback button
does nothing".

The skill gathers cloud evidence (instances, disks, snapshot chains), renders
the two mandatory risk points verbatim, offers a confirmation-gated
pre-rollback fallback snapshot, can dispatch confirmation-gated
**non-mutating** observation commands inside the guest to compare disk
contents before/after a rollback, and hands every foreign symptom (cleanup,
passwords, boot repair, capacity growth, policies) to the right workflow via
`references/transfer-matrix.md`.

## Absolute Rules

1. **ABSOLUTE PROHIBITION — the rollback is never executed.** The disk
   rollback operation itself (`ResetDisk`, the console "Roll Back Disk"
   action) is irreversible and destructive. This skill NEVER invokes it and
   NEVER generates runnable rollback commands — including "for the user to
   paste". It outputs evidence, the mandatory risk statement, and manual
   console steps only (see [references/rollback-entry-steps.md](references/rollback-entry-steps.md)).
   The same never-auto rule covers: re-initializing a disk, stopping or
   rebooting instances, deleting snapshots, filesystem/boot repair, malware
   cleanup, credential rotation and any billing action.
2. **TWO GATED ACTIONS ONLY, EACH BEHIND ANNOUNCE + CONFIRM.** The state
   changes this skill can make are exactly: the ECS snapshot-creation
   operation (`CreateSnapshot`, one billable fallback snapshot of one named
   disk) and the Cloud Assistant dispatch operation (`RunCommand`, carrying
   exactly one whitelisted non-mutating command). Before either one, the
   agent MUST announce to the user: what will run, on which resource, the
   impact (including snapshot billing), and reversibility — then obtain the
   user's explicit approval, then rerun the script with `--confirm yes`.
   Approval covers that single call only; it never carries over.
3. **HARD WHITELIST FOR GUEST COMMANDS.** `guest-check` accepts only the
   frozen observation catalog (Linux `df -h`, `df -hT`, `findmnt`, `ls`,
   `stat`, `lsof +L1`; Windows `Get-Volume`, `Get-PSDrive`,
   `Get-ChildItem`, `Get-Item`). Any other command string is refused by the
   script and must also be refused by the agent with the reason. Service
   start/stop, process kills, and any write inside the guest are manual
   guidance only.
4. **SNAPSHOT-FIRST DISCIPLINE.** Before guiding any rollback — or any
   cleanup on the way to one — offer the current-state fallback snapshot
   (Rule 2 path). A rollback against a snapshot that is not 100%
   accomplished is never guided. If the customer declines the fallback,
   record the refusal in the report; do not silently proceed.
5. **API WHITELIST.** Only the actions listed in
   [references/ram-policies.md](references/ram-policies.md) may run, only via
   the bundled scripts. Never call or generate anything else — notably not
   `ResetDisk`, `ReInitDisk`, `StopInstance`, `RebootInstance`,
   `DeleteSnapshot`, `DeleteDisk`, `ReplaceSystemDisk`.
6. **NO FABRICATION.** Every conclusion comes from script output or the
   reference modules. Empty or failed queries are reported as limitations,
   never papered over with invented states. Auth failures are worded with
   `NoPermission` / `ImplicitDeny` and name the missing action — never any
   other denial literal.
7. **SCOPE = ONE SYMPTOM AXIS.** Only "restore a disk to a past snapshot
   point" and its direct consequences. Foreign symptoms get the transfer
   matrix: disk space/inode, expansion grow, boot repair, stuck power
   states, snapshot policy/billing, intrusion cleanup, credential repair,
   cross-instance image routes.
8. **CREDENTIALS ARE NEVER HANDLED.** No reading, printing, asking for or
   passing keys/tokens anywhere; the aliyun CLI default credential chain is
   the only source.

## Trigger Conditions

Use this skill when the customer's own wording matches the `description`
Triggers, e.g.: "roll back disk to snapshot", "restore system disk from
snapshot", "recover data lost after rollback", "snapshot expired and
deleted", "rollback button no response", "stuck stopping during rollback",
"connection refused after rollback", "NoPermission snapshot rollback".
Customers state symptoms, not root causes — match the symptom sentence, not
product vocabulary. Requests that are really about snapshot deletion /
capacity / billing, disaster recovery, or an instance stuck in a power
state belong to the skills named in the description's Do NOT use line.

## Execution Principle (single entry point, no fallback)

All cloud evidence MUST be gathered by running the bundled scripts; the
agent never assembles its own `aliyun` CLI commands:

| Invocation | Purpose |
|---|---|
| `python3 scripts/sts_token.py` | verify the active identity (runs first) |
| `python3 scripts/rollback_readiness.py assess ...` | eligibility preconditions, candidate restore points, data-loss window |
| `python3 scripts/rollback_readiness.py guest-check ...` | ONE whitelisted observation command, gated |
| `python3 scripts/rollback_readiness.py snapshot-backup ...` | ONE fallback snapshot, gated |

If a script fails, report its error (`STATUS: FAIL` / `DEGRADED` and the
`NEXT_ACTION:` line) and stop — no manual CLI workarounds. Where the
environment provides the `alibabacloud-workbench-cli` skill, its login and
execution channel takes precedence for guest access; this skill contributes
the frozen command catalog and the confirmation discipline, never its own
login logic.

## Data Flows and External Calls

The scripts contact Alibaba Cloud OpenAPI endpoints only, always through the
local `aliyun` CLI subprocess: the ECS 2014-05-26 actions whitelisted in
`scripts/_constants.py` and the STS identity query. Every request carries
the observability User-Agent described below. What leaves the machine:
region / instance / disk / snapshot identifiers, the exact whitelisted
command string when the customer approved a guest check, and pagination
tokens. No credentials, key material or tokens are ever read, printed or
transmitted; error text is credential-masked before display. No third-party
destinations exist.

## Credentials

Credentials resolve automatically via the aliyun CLI default chain
(environment or `~/.aliyun/config.json`). If `scripts/sts_token.py` fails,
the chain is not configured: instruct the user to run `aliyun configure`
themselves; never ask for, accept, echo or pass key values in either
direction.

## User Confirmation (mandatory before every gated action)

Queries need no confirmation. The two gated actions (`snapshot-backup`,
`guest-check`) follow this fixed sequence, every single time:

1. Run the mode WITHOUT `--confirm` — the script prints the announcement
   block (resource, exact command or disk, impact, billing note,
   reversibility) and exits without acting.
2. Relay that announcement to the user in plain language.
3. Only after the user's explicit approval for that exact call, rerun with
   `--confirm yes`. Re-ask for every new call.

Refusals are reported as refusals. Destructive operations (Rule 1) are
outside the gated path entirely: they never run with or without confirmation.

## Observability

Every OpenAPI call is issued through the shared CLI layer with a unified
User-Agent:

- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`
  with `{skill-name}` = `alibabacloud-ecs-snapshot-rollback-guide`.
- **session-id**: a 32-character lowercase hex string (`uuid.uuid4().hex`)
  generated once per script run and reused for every CLI call of that run,
  so all calls of one diagnosis correlate. The implementation lives in
  `scripts/_cli.py` (`session_id()` / `user_agent()`), attached via the CLI's
  `--user-agent` flag on every invocation.

## Environment and Prerequisites

1. aliyun CLI 3.x installed and configured (default credential chain).
2. Python 3.9+ (standard library only; see `scripts/requirements.txt`).
3. The RAM actions in [references/ram-policies.md](references/ram-policies.md)
   granted to the active identity.

## Input Parameters

| Parameter | Required | Notes |
|---|---|---|
| `--region-id` | yes | e.g. cn-hangzhou; never guessed — ask if unknown |
| `--instance-id` | one of instance/disk for `assess` | must match `i-*` form |
| `--disk-id` | yes for `snapshot-backup` | must match `d-*` form |
| `--snapshot-id` | optional | evaluate one user-named restore point |
| `--before` | optional | UTC date/datetime of the incident's first anomaly: drives the clean restore-point shortlist |
| `--command` + `--os-type` | for `guest-check` | validated against the frozen catalog; `linux` is the default and is declared in output when auto-filled |
| `--confirm yes` | gated modes only | only after the user approved that exact call |

UID is auto-derived via the identity query and only labels the report;
declare auto-filled values (UID, `--os-type` default, `--before` timezone)
explicitly in the final answer.

## Module Index

| Module | File | Responsibility |
|---|---|---|
| M1: RAM policies | [references/ram-policies.md](references/ram-policies.md) | full action whitelist incl. the two gated write-class actions, denial recovery |
| M2: Rollback entry steps | [references/rollback-entry-steps.md](references/rollback-entry-steps.md) | the two console entry points, preconditions, risk wording, post-rollback loop, button-unresponsive checklist |
| M3: Recovery boundaries | [references/recovery-boundaries.md](references/recovery-boundaries.md) | the three not-recoverable verdicts (expired / released / overwritten) with evidence shape and alternative backup sources |
| M4: Backup types | [references/backup-type-comparison.md](references/backup-type-comparison.md) | snapshot vs image vs file backup; the cross-instance route |
| M5: Guest observation catalog | [references/guest-observation-catalog.md](references/guest-observation-catalog.md) | the frozen non-mutating command set, confirmation discipline, degradation path |
| M6: Transfer matrix | [references/transfer-matrix.md](references/transfer-matrix.md) | foreign-symptom recognition and handoff sentences |

## Orchestration

```
symptom --> classify axis (rollback execution? recoverability? route question?)
   |
   +-- scripts/sts_token.py            (identity, always first)
   +-- scripts/rollback_readiness.py assess   (evidence: states P1-P5)
   |       |
   |       +-- ROLLBACK_ELIGIBLE --> risk statement + manual steps (M2)
   |       +-- NO_USABLE_SNAPSHOT --> boundaries + alternatives (M3)
   |       +-- route question     --> backup types / cross-instance (M4)
   |
   +-- gated: snapshot-backup (fallback snapshot, announce+confirm)
   +-- gated: guest-check     (one catalog command, announce+confirm)
   +-- foreign symptom --> transfer matrix (M6)
```

## Execution Flow

1. **Scope confirmation** — restate the target (region, instance/disk) and
   the plan (queries first; anything state-changing requires explicit
   approval). Never run a gated action before that.
2. **Identity** — `python3 scripts/sts_token.py`. On failure, stop and
   report the credential-chain guidance (never handle keys).
3. **Evidence** — `python3 scripts/rollback_readiness.py assess
   --region-id <r> [--instance-id <i> | --disk-id <d>] [--snapshot-id <s>]
   [--before <UTC>]`. Read the P1-P5 preconditions, per-disk verdicts and
   the data-loss window from the output; relay `STATUS` faithfully.
4. **Branch** —
   - eligible + rollback intended: offer the gated fallback snapshot
     (announce → confirm → `snapshot-backup`), wait for 100%, then relay M2's
     manual console steps plus both risk points;
   - not recoverable: deliver M3's evidence-shaped verdict; check alternatives;
   - route confusion: deliver M4's comparison and the cross-instance route;
   - foreign symptom: deliver M6's handoff sentence.
5. **Optional verification** — before/after readings via gated `guest-check`
   of catalog commands; service self-start and listener checks stay a manual
   checklist (they are not on the catalog).
6. **Report** — evidence first, conclusion second, every auto-filled
   parameter declared, the sensitive-information footnote when credentials
   may have been pasted during the incident.

## Error Handling

| Situation | Script behavior | Agent behavior |
|---|---|---|
| `NoPermission` / `ImplicitDeny` on any action | `[WARN]` + `errors[]` entry + hint naming the action | name the missing action, point to references/ram-policies.md, rerun once after the grant; never switch credentials |
| Instance/disk/snapshot not visible | verdict `NO_USABLE_SNAPSHOT` / NOT_VISIBLE note | confirm region/account; released resources -> M3 boundaries |
| Snapshot progress below 100% | excluded from candidates with reason | state the gate (M2 precondition 2); never guide against it |
| Cloud Assistant unreachable | `guest-check` -> `STATUS: DEGRADED` | fall back to customer-pasted output (M5 rule 3) |
| Non-whitelisted command | `[REFUSED]` + reason | relay the refusal; do not rephrase the command to sneak it through |
| Business error codes not in this table | raw code echoed, `STATUS: DEGRADED` | echo the code verbatim; never guess a cause |

## Important Notes

- The rollback button "not responding", a stuck "Stopping" state, and a
  boot jam after rollback are three different axes — the assessment output
  plus the transfer matrix keep them separate.
- A rollback restores the snapshot-time partition state: capacity that grew
  later shrinks back; the grow-partition repair belongs to the expansion
  workflow, not this skill.
- "Restoring" after an intrusion is a data step, not a cure: the
  to-do list (rotate keys, tighten access, patch, clean) transfers to the
  incident-response axis; rollback to an old point without hardening
  reliably re-infects.
- Reports end with `STATUS: OK|DEGRADED|FAIL` + `NEXT_ACTION:`; relay them —
  never replace the machine verdict with a nicer guess.

## Examples

**Example 1 — how do I roll back, really**
> User: "I need to roll back disk d-2ze9xxxx in cn-hangzhou to the snapshot
> from last night. What happens to today's data?"

Run `assess` on that disk, relay the candidates + the data-loss window line,
then the two risk points, then M2's manual steps; offer the gated fallback
snapshot first.

**Example 2 — snapshot expired**
> User: "My automatic snapshot policy kept snapshots for 1 day only and my
> CRM data from 10 days ago is gone. Pay whatever — just recover it."

`assess` proves no snapshot covers the window; deliver M3's verdict shape
(with the evidence list), the alternative-source checklist, and retention
hardening advice — no recovery promise.

**Example 3 — rolled back, site still down**
> User: "Rolled back the system disk after the ransomware, server boots but
> the website says connection refused."

Explain per M2 step 3 (app did not auto-start), output the manual service
checklist; offer `guest-check` catalog readings for the web root; transfer
the cleanup/hardening half via M6.

## Final Answer Contract

1. Open with the script's Summary/`STATUS` (OK / DEGRADED / FAIL) and its
   evidence; quote real field values only.
2. State the verdict (`ROLLBACK_ELIGIBLE` / `NEEDS_ACTION` /
   `NO_USABLE_SNAPSHOT`) and the required actions in order.
3. Relay the risk statement verbatim whenever rollback steps appear; state
   explicitly that the rollback is performed by the customer in the console.
4. Declare every auto-filled parameter (UID, os-type defaults, UTC
   assumptions) and every degraded section.
5. Close with the transfer handoffs applicable and the sensitive-information
   footnote when credentials were shared during the incident.
