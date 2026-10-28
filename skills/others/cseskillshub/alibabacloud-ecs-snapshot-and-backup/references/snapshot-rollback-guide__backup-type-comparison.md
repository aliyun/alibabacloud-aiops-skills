# Three Recovery Routes: Snapshot Rollback vs Custom Image vs File Backup

Customers routinely conflate the three restore mechanisms. Decide the route
from the goal, before touching any procedure.

| | Snapshot rollback | Custom image | File backup (Essential Edition) |
|---|---|---|---|
| Restores | One disk, on the SAME instance it is attached to | Whole system state, onto another instance (via change-OS) or a NEW instance | Individual directories / files into a running system |
| Granularity | Block-level: the entire disk at the snapshot time | Image level: system disk (+ chosen data disks) | File level: selected paths |
| Cross-instance | NO -- a system-disk snapshot cannot be rolled back onto a different instance | YES -- share the image, then change the OS of the target instance | Restore target can be any covered instance |
| Effect on current data | Overwrites the disk; the window since the snapshot is lost | The change-OS step replaces the system disk (its own data-loss rules) | Adds files back; does not overwrite the whole disk |
| Where to read the steps | [rollback-entry-steps.md](rollback-entry-steps.md) | Image workflow (hand off, see [transfer-matrix.md](transfer-matrix.md)) | File-backup workflow (hand off) |

## The cross-instance route (what customers actually need when they ask
"restore server A's system snapshot onto server B")

A system-disk snapshot can only roll back its own source disk on its own
instance. For a same-region same-account cross-instance restore the supported
route is:

1. On A: create a custom image from the instance (or from the system-disk
   snapshot).
2. Share the image with B's account if the accounts differ.
3. On B: change the operating system to that image (manual console step,
   with the change-OS data-loss warnings).

Steps 1-3 are customer-performed. This skill identifies the route and relays
the doc links; it never creates images and never changes operating systems
(the change-OS workflow owns those actions -- see
[transfer-matrix.md](transfer-matrix.md)).

Official selection guide (which mechanism for which goal):
https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md

File-backup configuration reference:
https://help.aliyun.com/zh/ecs/user-guide/configure-automatic-file-backup-and-restoration-for-ecs-instances.md

## Local-disk and preemptible caveat

Instances backed by LOCAL disks (some big-data / legacy families) and
preemptible instances have different or absent snapshot-rollback semantics;
`assess` surfaces the disk category. When the target disk is a local disk,
snapshot rollback of it is not available at all -- say so and hand off to the
data-retention boundary document:
https://help.aliyun.com/zh/ecs/user-guide/preemptible-instance-data-retention-and-data-recovery-after-interrupt-reclamation.md

## One-line disambiguation script (use when the customer's wording is vague)

- "back to how the disk was on <date>, on this same server" -> snapshot rollback.
- "get this server's system onto another server" -> custom image + change OS.
- "just get back the deleted folder / a few files, keep everything else" -> file backup.
- "back to a clean factory system" (no need for old data) -> re-initialize
  the system disk: the manual route documented in
  [rollback-entry-steps.md](rollback-entry-steps.md) (re-initialization link).
