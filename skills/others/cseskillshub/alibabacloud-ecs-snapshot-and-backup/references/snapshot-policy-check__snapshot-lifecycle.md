# Snapshot creation: progress, queueing, failure (capability C1)

Customer wording that lands here: "snapshot stuck at 0%", "progress has not moved
for two hours", "creation is taking all day", "app-consistent snapshot failed".

Entry point: `python3 scripts/snapshot_policy_check.py snapshot-status --regions <r1>,<r2> [--instance-id i-...] [--hours 72] [--polls 3 --poll-interval 30]`

## 1. What creation actually does

A snapshot is an incremental, crash-consistent copy taken at the block level. The
first snapshot of a disk copies the whole used capacity; later ones copy only the
blocks written since the previous snapshot. Duration therefore tracks **how much
data changed**, not the nominal disk size, and it shares regional capacity with
other tenants' tasks.

Reference: `https://help.aliyun.com/zh/ecs/user-guide/how-do-snapshots-work.md`
(see `references/help-documents.md` for the full list; URLs carry the original
Chinese-language document names, which is expected for Alibaba Cloud ECS help).

## 2. Three verdicts, and the evidence for each

| Evidence from `ecs:DescribeSnapshots` | Verdict | What to tell the customer |
|---|---|---|
| `Status = progressing`, `Progress` climbs between samples | normal queueing | Creation is running. Slow is not broken. Report the current percentage and the age. |
| `Status = progressing`, `Progress` identical across samples for over 30 min | candidate stall | Re-sample with `--polls 3`. If still identical, the task needs the product side: file a ticket quoting snapshot id, instance id, disk id and creation time. Nothing in this skill can accelerate it. |
| `Status = failed` | creation rejected | Work the precondition list in section 3, then `references/error-signals.md`. |

Ground rules taken from the ticket record:

- Support could not raise the throughput of a region-wide peak either; the honest
  answer was that regional capacity was saturated and the only lever is an
  off-peak hour (evidence: ticket 000ACRF8K2, 40+ min at 0-5% during a peak).
- A percentage that looks frozen was in fact advancing (59% then 69% on a later
  check) - which is why this skill samples twice before using the word "stuck"
  (evidence: ticket 000DGRP989).
- "Delete it and create again" was tried and did not help, and deletion is
  irreversible; the skill presents it as a customer decision only, never as an
  automated step (evidence: tickets 000DGRP989, 000ACRF8K2).

## 3. Preconditions to rule out before blaming the task

| Check | How | Evidence |
|---|---|---|
| Account arrears or frozen state | console billing state; there is no query for it in this version - see `references/limitations.md` | ticket 000GJRTG60 (balance blocked creation), 0009LR8YJD (arrears shown on the policy page) |
| Real-name subject change freezing operations | account appeal, not a snapshot problem | ticket 00073S02FZ |
| Snapshot quota or name collision in the region | count snapshots in `lifecycle-inventory`, compare with the console limit | standard quota behaviour |
| Disk state | `ecs:DescribeDisks` status; a disk that is creating or released cannot be snapshotted | - |
| Whole-instance backup plan conflicting with an automatic policy | route to Cloud Backup (HBR); the plan owns the schedule | ticket 0003YRW0UP |
| Heavy write activity inside the guest | guided, side-effect-free commands in `references/guest-inspection.md` | ticket 0001FS004N (memory pressure and load coincided with slow creation) |

## 4. Application-consistent snapshots (Windows / SQL Server)

Prerequisites, all verifiable with the query actions:

1. Disk category must be ESSD, without multi-attach (`ecs:DescribeDisks`).
2. Cloud Assistant agent must be present and online; the flow runs a script in the
   guest and its history stays in `ecs:DescribeInvocations`.
3. The RAM role the flow requires must exist and be attached to the instance.

Layered triage from the recorded case (evidence: ticket 000BSRFJZW, whose log is
truncated, so the closing step is unconfirmed):

| Signal | Layer | Human step |
|---|---|---|
| missing or wrong RAM role | identity | create the role the documented flow names, attach it to the instance |
| `exitcode 12` from the assistant command | script stage | read the command output; usually role or provider setup |
| `0x80042304` / `VSS_E_UNEXPECTED_PROVIDER_ERROR` | VSS provider | re-register the EBS VSS provider components, then reboot |
| script blocked or quarantined | Security Center interference | add an exclusion for the assistant script, then retry |
| third-party backup software holding writers | writer conflict | stop it for the window, retry |

Re-registering components, rebooting the instance and touching antivirus software
are **outside the allowed command set**. Output them as guided steps, then verify
the outcome with `snapshot-status` or `check-all` rather than assuming success.

## 5. After any fix

Verify by query, not by hope: `check-all --regions <r>` shows the new snapshot
records, their status and progress. If the customer's real goal is a rollback or a
resize, hand off per `references/handoff-boundaries.md` and leave them a completed
backup first.
