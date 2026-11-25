# Data rescue and rebuild: the two exits when repair is not working

Reached from step 4 of `references/boot-repair-guide__boot-failure-decision-tree.md` when the boot path cannot be restored, or
when the customer cannot afford more attempts. The two exits are:

- **Exit A — roll back to an earlier snapshot.** Fast, restores the whole volume, discards everything after
  the snapshot moment.
- **Exit B — copy the data out and rebuild.** Slower, keeps the current data, leaves the original instance
  untouched until the customer decides to rebuild it.

Both are executed entirely by the customer in their own account. This skill assembles the sequence, the
prerequisites, the cost statements, and the irreversible bits; it does not perform, schedule, or trigger any
of them.

## Choosing the exit

| Situation | Exit |
|---|---|
| A known-good snapshot exists, its time is acceptable to the business, and the volume contents after that point are expendable | A |
| The newest data must survive (databases, uploaded files, mail queues) | B |
| Repair attempts have all failed but the data volume itself is intact | B, or A if an older point is acceptable |
| The start of the disk was overwritten so the partition layout is gone, and loader repairs change nothing | A, to a point before the overwrite; B cannot mount what it cannot identify |
| The boot files or `/etc` are empty, or the system is out of support and no fix exists | B, then rebuild |
| Ransomware encrypted system files | Security handling first; B for the data that is still readable |
| No snapshot exists at any point | Neither; state plainly that the recovery options are gone, and stop before any further destructive step |

An earlier snapshot that is retained automatically may already have expired. Ask about the retention rule
before promising that "any older point" is available, and record that released snapshots cannot be
recovered.

## Exit A — snapshot rollback

Prerequisites the customer must confirm before starting:

1. A snapshot whose completion progress reached 100 percent, identified by id and by its creation time.
2. A new snapshot of the current state, taken before rolling back. This is the step most often skipped, and
   it is the only thing that makes a wrong rollback recoverable; without it, everything between the older
   snapshot and now is gone permanently.
3. A downtime window: a rollback restarts the instance, so "roll back without interrupting the service" is
   not an available option.
4. Acceptance that data written after the chosen snapshot point is discarded, including anything the
   application has since committed.

Verification after rollback: the instance starts, the application reads its data, and the timestamps of the
restored files reflect the snapshot moment rather than the present. If the business expects newer records,
that expectation is the actual question to settle before rolling back.

## Exit B — copy out, then rebuild

The sequence is the same whether the operating system is Linux or Windows; the tooling differs.

1. **Snapshot both volumes** — system disk and each data disk that matters. Record the size and the
   retention of each, and state the snapshot cost and its unit alongside, so the customer is not surprised by
   the bill later.
2. **Build disks from those snapshots.** A disk built from a snapshot must be created in the **same
   availability zone** as the instance that will attach it. This is the single most common reason a rescue
   attempt reports a missing resource.
3. **Create a temporary pay-as-you-go instance** in that same zone, sized for the copy work rather than for
   the original workload. Take the zone from `python3 scripts/axes/boot_repair_guide/boot_repair_guide.py profile`, then run
   `python3 scripts/axes/boot_repair_guide/boot_repair_guide.py rescue-stock --region-id <region> --zone-id <zone>` for the stock
   check; the purchase itself is the customer's action.
4. **Attach the rescue disks** to the temporary instance as data disks. Watch the per-instance storage limits
   of the chosen type: entry-level burstable families cap aggregate IOPS and throughput, and attaching two
   extra disks can exceed the ceiling.
5. **Bring the volumes online and copy.** On Linux, mount read-only where possible so the rescue copy cannot
   be modified by accident. On Windows, bring the disks online in the disk management view, assign letters,
   and copy. Verify file counts or sizes at the destination before continuing.
6. **Take the disks offline, detach, and release** the temporary resources, and **delete the snapshots** that
   were created for the rescue once the data is safely elsewhere. Snapshots bill for as long as they exist,
   and a rescue that leaves three snapshots behind produces a cost the customer did not plan for.
7. **Rebuild the original instance**: replace the system image or re-initialize the system disk, restore the
   application, then re-attach or re-copy the data. Where the rebuilt instance is created from an image, the
   mount-entry trap in `references/boot-repair-guide__fstab-and-devices.md` applies again: entries for disks the new instance
   does not have will reproduce an emergency-mode boot on the fresh machine.

### Variant when a second instance is not wanted

Where the customer only needs the data and the original instance can be discarded, the shorter path is:
snapshot, create a custom image or a disk from the snapshot, attach that to any healthy instance in the same
zone, copy, then release. The trade to state: an image-based path can carry the damaged system disk contents
in a form that is easier to mount, but a share-to-another-account step may be needed for analysis, and that
cross-account copy is a deliberate data-exposure decision the customer makes.

## What the customer must understand before either exit

- Rolling back is irreversible for the discarded interval. There is no undo.
- Re-initializing or replacing a system disk clears the contents of that volume; data-disk volumes are not
  cleared by it, and data on the system volume is only recoverable through a snapshot taken beforehand.
- Operating in the customer's account is the customer's own action. A support channel can be authorized to
  look inside the guest, but console purchase, rollback, and disk operations stay with the account holder, and
  a plan that assumes someone else will click through it is not a plan.
- Safe mode or a rescue environment is not a production state: services that depend on the normal start path
  do not run there.
- Where the failure cause is still unknown and the business needs the machine back within hours, the
  evidence-first choice is Exit B (copy and rebuild) with the original volume preserved for later analysis;
  destroying the original and the snapshots ends the possibility of ever learning the cause.

## Handoff after rescue

Once the data is safe, the remaining questions are outside this skill: rebuilding the workload, re-installing
agents, image creation practice, and any billing dispute about the temporary resources. Say so, and route to
the corresponding flow rather than continuing to offer boot-repair guidance for a machine that no longer
exists in its previous state.
