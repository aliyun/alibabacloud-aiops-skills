# Precheck and readiness checklists

Knowledge cross-checked against the official documentation on **2026-07-31**.

This file is the **checklist** half of the skill: what has to be true, what the
customer must do themselves, and what this skill reads to confirm it. The exact
console click sequence is deliberately not reproduced here - the official pages
linked at the bottom are authoritative and change with the console version.

**Standing rule.** Before handing any customer any step below, state the
boundary once: *this skill is read-only; it changes nothing and runs nothing
inside your instance; you perform the console steps; this skill re-checks the
facts afterwards.* Skipping that sentence is how a step list gets read as work
already done.

## A. Before creating a snapshot consistency group

Run:

```
python3 scripts/snapshot_group_check.py --mode precheck \
  --region-id <region> --instance-id <instance-id> \
  --environment <public|gov|dedicated|unknown> \
  --question "<the customer's own wording>"
```

Then walk the checklist against the findings it printed.

| # | Element | How it is established | Ready when |
|---|---|---|---|
| A1 | Environment supports the feature | Customer statement - no read-only API exposes environment type | Public cloud per R3 of [group-rules.md](group-rules.md); government / dedicated cloud stays LOW CONFIDENCE and must be labelled |
| A2 | Right region | `DescribeDisks` / `DescribeInstances` in the given `RegionId` | Resources are found in that region; an empty region means "wrong region or nothing there", so re-confirm before concluding |
| A3 | Disks are in the ESSD family | `DescribeDisks` category per disk | Every intended disk reports an ESSD-family category; anything else is reported as a fact and referred to the current supported-category list |
| A4 | More than one disk needs the same time point | Disk count from `DescribeDisks` | 2 or more disks. A single disk needs no group - hand off per [handoff-map.md](handoff-map.md) |
| A5 | Disks belong to one instance | `DescribeDisks` scope taken through the instance | All intended disks are attached to the same instance |
| A6 | No assumption that a policy will do it | `DescribeDisks` per-disk automatic snapshot policy association | Stated explicitly to the customer: per R2 of [group-rules.md](group-rules.md) a policy is evaluated per disk, so identical policies on several disks give no shared time point |
| A7 | Application consistency, if asked for | Customer self-check inside the guest | The customer confirms the in-guest preparation themselves; this skill runs nothing in the instance. Windows equivalent: LOW CONFIDENCE, say so |

Only after A1-A7 are addressed, give the customer the creation steps from the
official page and have them run it in the console. **Do not** offer or generate a
script to create or clean up groups: there is none (R2).

## B. After the customer created the group

Run:

```
python3 scripts/snapshot_group_check.py --mode verify \
  --region-id <region> --instance-id <instance-id>
```

| # | Check | Evidence | Verdict rule |
|---|---|---|---|
| B1 | Records exist | `DescribeSnapshots` per source disk | One record per intended disk, in that region |
| B2 | Upload finished | `Status` (and progress value when present) | `accomplished` only. "creating" / "uploading" is **not** finished - see [status-guide.md](status-guide.md) |
| B3 | Shared time point | Distinct `CreationTime` values across source disks | One identical value across disks is the observable signature of a group; several different values means these are independent snapshots, not a consistent set |
| B4 | Group entry itself | Not readable through this skill's verified reads | Ask the customer to confirm the group entry in the console, and label it as unverified by API (R7 of [group-rules.md](group-rules.md)) |
| B5 | Duration expectation | Rule wording plus one measured example | Explain first-run full versus later incremental; never promise a duration (R5) |

## C. Before rolling back disks with a group

Rollback is executed by the customer in the console. This skill states
preconditions and re-reads facts only - it never stops an instance and never
rolls anything back.

| # | Precondition | How it is checked | Note |
|---|---|---|---|
| C1 | A fresh backup of the current state exists | `DescribeSnapshots`, newest accomplished record per disk, inside `--window-hours` | Rollback overwrites data. Without this the newest writes after the group's time point are unrecoverable |
| C2 | Instance is stopped | `DescribeInstances` `Status` | Required before rollback. Reporting the state is not the same as stopping it: the customer stops it |
| C3 | Which disks are covered | `DescribeDisks` plus the group entry the customer confirms in the console | Group membership is inferred per R7; have the customer confirm the covered disk list before they roll back |
| C4 | Risk restated | Rule wording | Say what is overwritten, from which time point, and that the action is not reversible except from a backup taken before it |

## D. After a rollback

Run mode `verify` again, then:

| # | Check | Evidence | Verdict rule |
|---|---|---|---|
| D1 | Snapshots still usable | `DescribeSnapshots` | Records and status readable in that region |
| D2 | Instance state | `DescribeInstances` | The customer restarts it from the console; this skill does not |
| D3 | Disks mount inside the guest | **Not observable here** | If a disk fails to mount, that is in-guest configuration: have the customer check their own mount table and mount order, then hand off per [handoff-map.md](handoff-map.md). Do not run or generate in-guest commands |
| D4 | No over-claim | Report wording | Never state that the rollback succeeded on the customer's behalf; state which facts were re-read and what remains for the customer to confirm |

## Authoritative console pages

* [Create a snapshot consistency group](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-consistent-group.md)
* [Roll back disks using a snapshot consistency group](https://help.aliyun.com/zh/ecs/user-guide/roll-back-disks-by-using-a-snapshot-consistent-group.md)
* [Apply an automatic snapshot policy to an instance](https://help.aliyun.com/zh/ecs/user-guide/apply-an-automatic-snapshot-policy-to-the-instance.md)
* [Restart an instance](https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md)
