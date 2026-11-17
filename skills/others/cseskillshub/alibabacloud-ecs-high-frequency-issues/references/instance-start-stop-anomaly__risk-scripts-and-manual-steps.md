# Risk notices and manual-step wording

Everything in this file is **guidance the customer executes in the console**. The
skill prepares it, attaches the evidence that makes it relevant, and states the
risk. It never triggers any of these operations, and it must not present them as
"done for you".

Relay the matching notice **before** pointing at a step, not after the customer
asks what could go wrong.

## The four-point restart notice

Use verbatim before any start, stop or reboot the customer performs — including a
reboot needed to apply a spec change or a mount-table edit:

1. The operation interrupts running workloads.
2. Data still in memory, not yet written to disk, can be lost.
3. Create a snapshot of every affected disk first so the current state stays
   recoverable.
4. Applications that are not enabled for autostart will need to be started
   manually once the instance is back.

## Snapshot-first discipline

Order, always: **snapshot → verify it is usable → change → verify the result.**

- Take it before rollback, before re-initializing the system disk, before
  replacing the OS, before any cleanup that deletes files, and before a spec
  change whose reboot might not come back.
- A snapshot is billed for its stored size, pay-as-you-go. Tell the customer the
  cost is real and ongoing, and that temporary incident snapshots should be
  deleted from the console once the case closes.
- On older cloud disk categories you may need one snapshot **per disk** rather
  than a single multi-disk or image-level operation; enumerate the disks from
  `DescribeDisks` so the customer snapshots all of them, not just the system disk.
- Only an `accomplished` snapshot is a recovery point; a `progressing` one is not
  yet usable, and a `pending` or failed one never will be.
- This skill can create the snapshot on request as its one gated write
  (`--create-snapshot --disk-id`, after the billing notice and an explicit yes).
  **Deleting** snapshots is never performed by this skill — that is a console step
  for the account holder.

## Irreversibility statements that must never be softened

| Operation | What to say |
| --- | --- |
| Roll back a disk to a snapshot | Overwrites the current disk content. Everything written since that snapshot is lost and cannot be recovered afterwards. Irreversible. |
| Re-initialize the system disk | Restores the system disk to the image's initial state: everything on it — data, installed software, configuration — is permanently gone. Data disks are unaffected. |
| Replace the operating system | The feature itself is free, but it **releases the original system disk**; all data and installed software on it are permanently lost. Snapshot first, or the state is unrecoverable. |
| Forced stop / forced reboot | Equivalent to pulling the power. Skips the OS flush and unmount, so in-memory data is lost and the filesystem may need repair on the next boot. Must be chosen **before** the operation; unavailable once a transition has begun. |
| Release the instance | Distinct from "it will not start". Check operation locks and release status before ever discussing it; release is final. |
| Preemptible instance reclaimed | Not a boot failure: the platform reclaimed the capacity. Data retention follows the preemptible-instance rules, so frame recovery, not blame. |

## "You must do this in the console yourself"

Say it plainly and early, because the expectation otherwise escalates:
**rollback, re-initialization, OS replacement, start/stop/reboot, forced
operations, snapshot deletion and release cannot be performed by an agent, by
this skill, or by support on the customer's behalf.** Support historically did not
perform them either; where a ticket appears to show "the engineer rebooted it",
that was a separate privileged human process under an explicit customer
authorization, and it is not a capability this skill offers.

Console navigation, generic (never paste a deep link carrying a customer's region
or instance id into a reply):

    ECS console -> switch to the target region -> Instances -> select the instance
      Start / Stop / Reboot           in the instance actions menu
      Force stop                      checkbox inside the Stop dialog
      Roll back disk                  Disk & Image -> Snapshots -> target snapshot
      Re-initialize system disk       instance actions -> disk actions
      Create snapshot                 Storage -> Disks -> snapshot for the chosen disk
      VNC / connection command        instance actions -> connect

## Manual step sheets to hand over

### A. Boot stalled in a transition (inside the 15-minute window)

1. Confirm from the script output that the state is `Stopping` or `Starting` and
   how long it has been there.
2. Explain the ordered shutdown and the 5 to 10 minute typical / 15 minute ceiling
   figures.
3. State that nothing can intervene while the instance is in `Stopping`.
4. If it must be faster next time: choose the forced option **before** the
   operation, accepting the data risk, and snapshot first.
5. Offer the high-load explanation with the CloudMonitor readings attached, and
   suggest deploying `atop` with autostart so a recurrence is diagnosable.
6. Ask the customer to refresh the console and verify the business, not only the
   status label.

### B. Dwell beyond the ceiling

1. Attach: current status and dwell minutes, platform health and event check,
   resource readings, disk inventory, snapshot availability.
2. State explicitly which evidence area is missing and why it could not be
   collected.
3. Escalate through a support ticket with that package; a forced state change is
   still not something this skill performs.

### C. Correct a boot mount-table entry (Family 1)

1. Snapshot the system disk.
2. Reach the instance over VNC if SSH is unavailable.
3. Paste the mount table (`cat /etc/fstab`, a customer-run reading) and compare it
   line by line with the `DescribeDisks` inventory the script printed.
4. In the copy the customer edits, **comment out** the offending line rather than
   deleting it, so it can be restored.
5. Reboot from the console.
6. After the boot succeeds, add a correct auto-mount entry for the data disk so
   the next reboot keeps it; a manually run `mount` is not persistent and will
   look like the disk vanished again.

### D. Recover a system disk that will not boot (Family 2)

1. Snapshot the current state even though it is broken — it is the only remaining
   evidence and the only undo.
2. List recovery points from `DescribeSnapshots` with their creation times; let
   the customer pick the point, do not pick it for them.
3. Roll back in the console (customer-only, irreversible).
4. If no usable point exists: re-initialize the system disk, then create a pay-as-
   you-go disk from an older snapshot, attach it to a healthy instance, and copy
   the data off. The original content is then gone.
5. If support needs to reproduce the failure: create a custom image from the most
   recent system-disk snapshot and share it with the investigating account.

### E. Apply a spec change that needs a reboot

1. Snapshot all affected disks.
2. Schedule it in a low-traffic window; the change takes effect only after a
   deliberate restart, which is a full stop/start cycle with all four risks.
3. Warn that a start can fail afterwards if the zone lacks capacity for the new
   type — economical-mode stops release resources.
4. Confirm the guest came back before declaring the change done.

### F. Preserve forensic ability for the next incident

`atop` with autostart is the only way to answer "what was eating the machine at
3am" later, because no per-process history exists on the cloud side and a reboot
erases the live view. Deployment, package installation and enabling a service are
all guest writes: hand the customer the procedure and the documentation link, do
not run it.

## Documentation links

Official guidance, safe to quote in a reply:

- Start an instance: https://help.aliyun.com/zh/ecs/user-guide/start-an-instance.md
- Stop an instance: https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md
- Reboot instances: https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md
- Economical (no-charge) stop mode: https://help.aliyun.com/zh/ecs/user-guide/economical-mode.md
- Connect by VNC: https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc.md
- Spec change overview: https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md
- Release an instance: https://help.aliyun.com/zh/ecs/user-guide/release-an-instance.md
- Create a snapshot: https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot
- Snapshot billing: https://help.aliyun.com/zh/ecs/product-overview/snapshots-1
- Roll back a disk from a snapshot: https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot-1
- Custom image from a snapshot: https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-a-snapshot-1.md
- Share a custom image: https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image
- Choosing a data protection scheme: https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md
- Preemptible instance data retention: https://help.aliyun.com/zh/ecs/user-guide/preemptible-instance-data-retention-and-data-recovery-after-interrupt-reclamation.md
- `atop` monitoring: https://help.aliyun.com/zh/ecs/use-cases/use-the-atop-tool-to-monitor-linux-system-metrics
- Replace or migrate the operating system: https://help.aliyun.com/zh/ecs/user-guide/migrate-the-operating-system-of-an-ecs-instance
- Logon credential management (online vs offline reset): https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management
- Windows paging file for memory exhaustion: https://help.aliyun.com/zh/ecs/support/how-to-configure-virtual-memory-for-windows-instances
