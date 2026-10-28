# Manual Rollback Entry Steps and Mandatory Risk Wording

The disk rollback itself is a manual console action performed by the customer.
This skill NEVER performs it (Absolute Rule 1 in `../SKILL.md`). This file is
the authoritative guidance text to relay after `assess` produced the
evidence. Official documents (verbatim URLs):

- Roll back a disk using a snapshot (entry from the **disk** page):
  https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot-1.md
- Roll back a disk using a snapshot (entry from the **snapshot** page):
  https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot.md
- The underlying OpenAPI reference, for experienced customers who operate
  through the API themselves (the skill never calls it):
  https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-resetdisk.md
- Re-initialize a system disk (the factory-reset route -- a DIFFERENT
  operation from snapshot rollback; use it only when the customer's goal is
  "back to a clean system", not "back to my snapshot point"):
  https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk.md

## Two console entry points (customers commonly find only one)

1. **Snapshot-page entry**: ECS console -> Storage & Snapshots -> Snapshots,
   find the target snapshot, use its rollback action for the source disk.
2. **Disk-page entry**: ECS console -> Instances -> the instance -> Disks,
   select the target disk, use its rollback action and choose a snapshot.

Both entries lead to the same operation. When the customer "cannot find the
rollback button", check the entry point first, then the preconditions below.

## Preconditions (verify from `assess` evidence before guiding anything)

1. The target snapshot belongs to the target disk (SourceDiskId match).
2. Snapshot progress is **100%** (status accomplished) -- a progressing or
   failed snapshot is NOT a valid restore point.
3. The instance is **stopped**. Stopping it is a manual customer action;
   this skill never stops, restarts or reboots instances.
4. System disk and every data disk are rolled back **separately, disk by
   disk**; one rollback never covers the other disks.
5. A current-state fallback snapshot exists (or the customer explicitly, in
   their own words, declines one after the risk statement -- record that
   refusal in the report).

## Risk statement (relay both points verbatim, before the steps)

1. Rolling back a disk is **irreversible**. Everything written to that disk
   between the snapshot's creation time and the rollback moment is
   permanently lost. Create a snapshot of the disk's current state first --
   otherwise that window can never be recovered.
2. Rollback restores only the disk's block data to the snapshot point. It
   does not "restore the latest", it does not undo an intrusion, and it does
   not restart applications: services that were not configured to
   auto-start will need to be started again manually.

Time expectation: the official wording is that the rollback completes in
minutes and the disk is usable once the instance starts normally. Give this
document-level expectation only; never promise an SLA figure.

## After the rollback (verification loop)

1. Start the instance manually (customer action), then rerun `assess` or use
   the gated `guest-check` mode to compare readings before/after: `df -h`,
   `findmnt`, `ls`, `stat` against the paths that matter to the business.
2. If disk capacity looks "reverted": a rollback restores the partition /
   file-system state of the snapshot point, so an expansion done AFTER that
   point disappears. The grow-partition path (`growpart` / `resize2fs`)
   belongs to the disk-expansion workflow -- relay the explanation here but
   hand the change over (see [transfer-matrix.md](transfer-matrix.md)).
3. If the site answers "connection refused" after a rollback or restart: the
   usual root cause is the application process not auto-starting -- output
   the manual service checklist (start command, boot autostart config,
   listen port), never start services from this skill.
4. If the instance is stuck in an intermediate power state ("stopping" that
   never finishes): that is the instance-state axis -- hand off per
   [transfer-matrix.md](transfer-matrix.md); the rollback on the cloud side
   may still be proceeding.

## "The rollback button does nothing" (console front-end self-check)

No diagnosis of the console front end exists in the ticket evidence for this
tier, so keep to the self-service checklist and say so honestly:

1. Try the other entry point (snapshot page vs disk page -- section above).
2. Refresh, clear site cache, or switch browser; check the RAM user actually
   sees the disk / snapshot resources.
3. Verify the preconditions in `assess` (a grayed-out action typically means
   instance not stopped or snapshot not on this disk).
4. If it still fails, submit a console ticket with browser, region, disk id,
   snapshot id and a screen recording. Do not conclude "platform failure"
   and do not conclude "customer error" without this evidence.
