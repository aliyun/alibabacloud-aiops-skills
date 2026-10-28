# Snapshot consistency group rules and capability boundaries

Knowledge cross-checked against the official documentation on **2026-07-31**.
Every rule below is version-sensitive wording: quote the date with the answer,
and re-verify before relying on it for a support scope decision.

Answer shape for every topic: state the rule, name the source, and separate
*verified fact* (from a read-only API) from *documented wording* (from the
official page) from *customer self-report*. Where the evidence is thin, the
LOW CONFIDENCE label is part of the answer and must be relayed, never dropped.

## R1. What a consistency group is, and which consistency it gives

A snapshot consistency group takes snapshots of multiple cloud disks of one
instance at a single point in time, so the multi-disk data is crash-consistent
at that moment. The time point is fixed when the creation is initiated; writes
that happen afterwards do not change the group.

* Default level: crash / filesystem consistency.
* Application consistency needs preparation **inside the guest operating
  system** in advance (for Linux instances: place the official
  application-consistency script and install the Cloud Assistant plugin).
  Without that preparation, a filesystem-consistency snapshot is what you get.
* **LOW CONFIDENCE**: an equivalent Windows preparation procedure is not
  evidenced in the material this skill holds. If asked about Windows
  application consistency, say the rule above covers Linux, that the Windows
  equivalent is not documented in this skill's sources, and hand the question
  to a support ticket. Do not present a Windows procedure as fact.
* The documented wording targets **multiple ESSD cloud disks** of one instance,
  so disk category is a real precondition, not a preference. Confirm it with
  `DescribeDisks` (see [precheck-checklist.md](precheck-checklist.md)).

Sources:
[snapshot consistency group overview](https://help.aliyun.com/zh/ecs/user-guide/snapshot-consistency-group-overview.md),
[create a snapshot consistency group](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-consistent-group.md)

## R2. Automatic snapshot policies never produce a consistency group

This is the single most common question in this tier, and the answer is a hard
product boundary:

* An automatic snapshot policy can be associated with **individual disks or
  with instance tags** only. It cannot be attached to a snapshot consistency
  group, and it never produces one.
* Associating the *same* policy with several disks does **not** make those
  snapshots consistent with each other. The policy is evaluated per disk, so
  each disk gets its own snapshot at its own moment. There is no shared point in
  time.
* Snapshot consistency groups are created **manually** only.
* There is **no supported script or scheduled automation** for producing or
  cleaning up groups. When a customer asks for one, say so plainly and give the
  manual console steps instead.

Because this boundary is what customers keep misreading, state it before
answering any "can it be automatic" question, and back it with the disk facts:
listing each disk with its own policy id turns the abstract rule into visible
evidence.

Source:
[apply an automatic snapshot policy to an instance](https://help.aliyun.com/zh/ecs/user-guide/apply-an-automatic-snapshot-policy-to-the-instance.md),
[create a snapshot consistency group](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-consistent-group.md)

## R3. Support scope: three elements, in this order

"When I cannot find the snapshot consistency group entry in the console" is
answered by three elements, and each one is either a fact, a rule, or a
customer statement - never a guess:

1. **Environment type** - public cloud versus government cloud versus dedicated
   cloud. No read-only API in this skill's whitelist exposes the environment
   type, so **ask the customer**. Ticket evidence indicates that a government
   cloud environment had no group entry at all.
   **LOW CONFIDENCE**: that finding rests on one ticket summary, with no
   official documentation hit as of 2026-07-31, and the conversation for it was
   never retrieved. Relay it as ticket experience, explicitly labelled, and
   point the customer to the console check or a support ticket. Never upgrade it
   to "officially unsupported".
2. **Region** - disks and snapshots are region-isolated. Confirm the region the
   customer is looking at before agreeing that anything is missing; this single
   check resolves a large share of "I cannot see it" reports.
3. **Disk category** - read `DescribeDisks` and report the actual category of
   every disk. Outside the ESSD family, report the category as a fact and say
   the customer must confirm the current supported-category list; do not issue a
   support verdict the documentation does not state.

If all three elements indicate support and the entry is still missing, the
question leaves this skill: hand off to console resource lookup
([handoff-map.md](handoff-map.md)).

## R4. Where snapshots are stored

* Snapshots are stored in service-managed OSS buckets that are **not visible to
  the user**, in the region of the source disks. They do not consume disk
  capacity, and are listed in the ECS console under **Storage & Snapshots >
  Snapshots**.
* A customer-created OSS bucket **cannot** be used to store snapshot data.
* In regions where OSS supports zone-redundant storage, snapshot data is stored
  in zone-redundant buckets by default; otherwise locally redundant.
* Whether a specific region is zone-redundant is **not readable** through this
  skill's whitelisted reads. Say so rather than inferring it from the snapshot
  records.
* Anything about fees, storage packages, which redundancy a package covers, or
  discounts leaves this skill immediately - see
  [handoff-map.md](handoff-map.md). In the originating ticket, the agent
  transferred exactly those questions to another team.

Sources:
[snapshot consistency group overview](https://help.aliyun.com/zh/ecs/user-guide/snapshot-consistency-group-overview.md),
[choosing an ECS data protection scheme](https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md)

## R5. When is a group or snapshot actually finished

* A group snapshot is usable only when its upload reaches 100%, which is the
  point where `Status` becomes `accomplished`. While it reads "creating" or
  "uploading to OSS" it is **not** finished, no matter how long it has been or
  how healthy it looks.
* The first snapshot of a disk is a **full** snapshot and is slow. One real
  measurement: about **30 minutes for 6 disks** on the first run. Subsequent
  snapshots are **incremental** and markedly faster.
* Duration depends on data volume and change rate. Give the full-versus-incremental
  explanation and the measured example as an example, **never as a promise or a
  timeout**.
* Read completion from `DescribeSnapshots` (`Status`, and `CreationTime` to line
  the disks up), not from what the console appears to show.
  [status-guide.md](status-guide.md) covers the mapping in detail.

## R6. Rolling back with a group: what must happen first

* The instance must be **stopped** before a disk rollback.
* Before stopping, take a **fresh snapshot of the current state**, so the newest
  data stays recoverable. A rollback overwrites data; without that backup the
  newest writes are gone.
* The rollback itself is performed by the **customer in the console**. This
  skill states the preconditions and afterwards re-reads facts - it never stops
  an instance, never rolls back, and never reports that a rollback was done for
  the customer.
* After the rollback, restart the instance from the console as a customer action
  (see the restart page below).
* If a data disk then fails to mount **inside the guest**, that is an
  in-guest configuration matter. Have the customer check their own mount table
  and mount order. In the originating ticket the failure turned out to be the
  customer's own incorrect auto-mount entry, found by the customer, with nobody
  entering the instance. This skill does not enter instances; see
  [handoff-map.md](handoff-map.md).

Sources:
[roll back disks using a snapshot consistency group](https://help.aliyun.com/zh/ecs/user-guide/roll-back-disks-by-using-a-snapshot-consistent-group.md),
[restart an instance](https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md)

## R7. What this skill can never confirm

Say these limits out loud in every report; silence about them reads as a
verified answer.

* **Group objects**: no read operation verified for this skill returns the
  group itself, and it is not confirmed that `DescribeSnapshots` exposes a group
  identifier. Membership is therefore inferred by aligning per-disk snapshot
  records and their `CreationTime` values, and the customer confirms the group
  entry in the console. The report labels this inference as such.
* **Environment type**: customer statement only (R3.1).
* **Guest state**: invisible by design; this skill is read-only cloud-side and
  runs nothing inside an instance.
* **Account scope**: the current credential's account, one region at a time.
* **Billing, packages, discounts**: out of scope, always handed off.

## R8. The misunderstanding to defuse first

Customers reaching this tier almost always assume one of:

| Customer assumption | What to say |
|---|---|
| "If I attach a policy to all the disks, I get consistent snapshots automatically." | No - per R2, the policy is evaluated per disk; manual groups are the only consistent path. |
| "The records are there, so the backup is done." | No - per R5, only an accomplished upload counts as finished. |
| "You can see it, so you can do it for me." | No - this skill is read-only; the customer performs the change and this skill re-verifies. |
| "A storage package covers snapshot charges everywhere." | Fee and package-scope questions are handed off; this skill answers none of them. |

State the read-only boundary **before** listing any steps the customer will run
themselves, so nobody reads a step list as work already performed.
