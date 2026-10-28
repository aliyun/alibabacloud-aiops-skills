# Auto snapshot policy effectiveness (capability C2)

Customer wording: "the automatic snapshot policy is not working", "no snapshots were
created overnight", "I created a policy but the disk has nothing", "what is this
default_policy I never made".

Entry point: `python3 scripts/snapshot_policy_check.py policy-coverage --regions <r1>,<r2> [--policy-id sp-...] [--hours 168]`

## The one rule that explains most of these tickets

A policy only acts on disks it is **applied to**. Creating a policy changes nothing
on its own.

- "You have one policy named default_policy in each of three regions, but no disk is
  associated, so the policy does nothing." (evidence: ticket 0001FRZPLN)
- "Usually this is because the policy was created and never applied to a specific
  disk." The agent then sent the console binding page and the case ended with the
  customer confirming the disk selection (evidence: ticket 000F4RNG48; that thread
  never got a final confirmation that binding succeeded, so treat closure as open).
- Fleet-wide checking is the expensive part: an agent walked region by region and
  instance by instance naming which had automatic snapshots. That is exactly what
  `policy-coverage` outputs as a table instead (evidence: ticket 0004PRZM16).
- The block storage page of the console shows, per region, which disks carry a
  policy, and the list can be exported as a spreadsheet for audit (evidence: ticket
  000ACRK142).

## Why a correctly bound disk can still show nothing today

| Cause | Evidence | How this skill shows it |
|---|---|---|
| The policy was applied **after** the day's trigger hour, so the first creation is the next scheduled hour | ticket 000GJRTG60: policy applied at 13:00, effective 15:24, no 13:00 snapshot that day | `policy-coverage` reports "policy bound, no snapshot in window" and tells you to compare the application time with the trigger hour |
| Account arrears suspends the service silently | ticket 0009LR8YJD | no query exists in this version - see `references/limitations.md`; the console shows the arrears banner |
| `default_policy` was generated when the instance was created, not by the customer, and is unbound so it costs nothing | ticket 0009LR8YJD | surfaced as "no policy id on the disk response, no auto snapshot" |
| Wrong region: the disk lives in a region the customer did not look at | ticket 0001FRZPLN (three regions each with one policy) | pass every region holding disks; this version never enumerates regions itself |
| Disk deleted with the instance, so its automatic snapshots went too | standard behaviour, confirm before relying on history | `lifecycle-inventory` shows what still exists |

## Trigger schedule facts worth repeating to the customer

- Automatic snapshots are created at the scheduled hour of the policy, per disk, and
  inherit the policy's retention. A disk added mid-cycle starts on the next cycle.
- Retention is per snapshot; when it lapses the snapshot is deleted automatically,
  which also stops billing for that one snapshot.
- Automatic snapshots are billed exactly like manual ones. **The policy is free; the
  snapshots are not.** Deleting a policy does not delete the snapshots it already
  made, so it does not stop billing (evidence: tickets 000AWRLY1J, 000G2RJ8LG,
  00069RU80Y; full chain in `references/snapshot-billing-facts.md`).
- Application-consistent behaviour, when a policy drives it, depends on the guest
  agent; see `references/snapshot-lifecycle.md` section 4.

## What the skill will not do

Binding, unbinding, creating, editing or deleting a policy is a customer console
action. The report gives the console page, the disk ids to select, and the check to
run afterwards. Deleting a policy is additionally a billing trap: it looks like a
way to stop charges and is not one.

Console entry: `https://ecs.console.aliyun.com/autoSnapshotPolicy/region/<regionId>`

Verification loop to hand the customer: bind the disk, note the policy's trigger
hour, then re-run `policy-coverage --hours 24` after that hour has passed.
