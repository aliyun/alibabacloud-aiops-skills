# Handoff map: adjacent symptoms this skill recognises but does not diagnose

Knowledge cross-checked on **2026-07-31**.

This skill covers exactly one symptom axis: **snapshot consistency groups and
multi-disk point-in-time consistency**, answered with read-only cloud facts plus
documented rule wording. Everything below is a neighbouring symptom. The
obligation is twofold: recognise it early, and say the boundary in one sentence
instead of half-diagnosing it here.

Target skill names follow the current skill catalogue. Where a named skill is
not available in the running environment, the fallback is always the same: a
support ticket. Never leave the customer with a dead end, and never answer an
out-of-scope question "just this once".

## H1. Snapshot fees, storage packages, redundancy coverage, discounts

| | |
|---|---|
| **Recognise** | The core question is about charges, deduction, which package to buy, or whether a package covers a redundancy type |
| **Why not here** | Billing is not a read-only consistency question, and the originating ticket itself transferred these questions to another team |
| **Say** | "Snapshot storage fees and resource-package deduction are outside this read-only skill. Please route that to snapshot billing consultation, or open a support ticket so the commercial team can verify it." |
| **Do not** | Quote prices, recommend a package, or state which redundancy a package covers |

## H2. Single-disk snapshots, automatic policies for one disk, cross-region copying

| | |
|---|---|
| **Recognise** | Only one disk is involved, or the customer does not need a shared time point across disks; or the question is about copying a snapshot to another region |
| **Why not here** | Multi-disk consistency is the entry condition of this tier; without it, this is ordinary snapshot management |
| **Say** | "Single-disk snapshot operations belong to the disk and snapshot management area - in the online catalogue, `alibabacloud-ebs-disk-snapshot-management`. This skill only covers multi-disk consistency." |
| **Do not** | Walk the customer through single-disk snapshot design, or discuss replication as if it were a consistency mechanism |
| **Note** | Answer the *consistency* part here when it is genuinely asked: per R2 of [group-rules.md](group-rules.md), an automatic policy - even one policy on several disks - never yields a consistent set |

## H3. Actually performing a rollback, a group creation, or any change

| | |
|---|---|
| **Recognise** | "Roll it back for me", "delete the group", "just run the script", "shut it down first" |
| **Why not here** | This skill is read-only and is structurally blocked from any mutating call; there is also no supported automation for groups at all |
| **Say** | "This skill is strictly read-only and never performs changes. You run the operation in the ECS console. I will state the preconditions - stop the instance first, and take a fresh snapshot of the current state before stopping - and then re-check the resulting facts for you read-only." |
| **Do not** | Emit a mutating command, or a command "for you to run" that changes a resource, or imply that any change was made on the customer's behalf |
| **Then** | Use section C of [precheck-checklist.md](precheck-checklist.md), and re-verify with `--mode verify` |

## H4. In-guest mount, filesystem or partition problems after a rollback

| | |
|---|---|
| **Recognise** | A disk will not mount, a mount point is missing, fstab errors, the partition is not seen - anything only observable inside the operating system |
| **Why not here** | This skill does not enter instances and cannot see guest state |
| **Say** | "Mount configuration lives inside the instance, so this skill cannot read it. Please self-check your own mount table and mount order - a rollback can change a disk identifier while an automatic mount entry still points at the old one. A real case turned out to be exactly that: the customer's own auto-mount entry was wrong, and they fixed it without anyone entering the instance. For deeper diagnosis this hands off to disk attach and in-guest visibility." |
| **Do not** | Generate or run in-guest commands, or attribute a mount failure to the rollback without evidence |

## H5. Console entry still missing although support is confirmed

| | |
|---|---|
| **Recognise** | Environment type, region and disk category all indicate support, yet the customer still sees no group entry |
| **Why not here** | The support-scope question is answered here (R3 of [group-rules.md](group-rules.md)); a missing entry that survives that check is a console visibility question, not a consistency question |
| **Say** | "Support scope checks out, so this is a console lookup matter. Confirm the selected region first, because these resources are region-isolated; beyond that, hand off to console resource lookup and status checking." |
| **Do not** | Escalate to "the feature is broken", or invent an environment restriction to close the gap |

## H6. Commercial callbacks, discount applications, refunds, invoices

| | |
|---|---|
| **Recognise** | Any commercial or approval process, including "have sales call me" |
| **Why not here** | Not a technical question, and outside every capability of this skill |
| **Say** | "Commercial requests go through the support ticket and commercial channel. This skill cannot act on them and will not predict an outcome." |
| **Do not** | Promise a callback, a discount, or any commercial result |

## H7. Backup scheme selection, and recovery after preemption

| | |
|---|---|
| **Recognise** | "Should I use snapshots or file backup?", or restoring data after a preemptible instance was reclaimed |
| **Why not here** | Scheme design and preemption recovery are adjacent tiers; only the consistency element belongs here |
| **Say** | "Scheme comparison belongs to the data-protection selection guidance; see the official comparison page. I can confirm the multi-disk consistency element for you here, read-only." |
| **Do not** | Choose a protection scheme for the customer, or treat a preemption-recovery question as a group question |

## Recognition order when a request spans several areas

A single message often mixes areas. Handle it in this order, and say which parts
were deferred:

1. Answer the consistency-group part with evidence (this skill's scope).
2. State the read-only boundary before any step list.
3. List each out-of-scope part with the matching handoff line above.
4. Never let an out-of-scope part silently redirect the whole answer - the
   customer then never gets the consistency answer they actually needed.
