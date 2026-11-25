# After an update, kernel change, or patch: what is normal and what is broken

The boundary that matters most in this file is between "the system is still working on the update" and
"the update broke the boot path". Getting it wrong in one direction wastes a support window; getting it wrong
in the other direction destroys data by forcing a power-off during a transaction.

This skill covers **the boot-failure side of an update**. It does not scan, install, evaluate, or roll back
patches: that is `alibabacloud-ecs-patch-management`. The test is the presence of a boot-failure signal. A
customer who says "the patch install returned error 133" belongs to the patch skill. A customer who says "I
installed the patch, rebooted, and now it never comes back" belongs here.

## Normal after an update

A cumulative or feature update can make the first successful boot take a very long time, measured in tens of
minutes to hours on a constrained instance, with the screen showing update-configuration progress and the
console appearing unresponsive. This is the system completing transactions, not a hang.

| Observation | Interpretation | Action |
|---|---|---|
| Screen shows update configuration progress, even slowly changing | Normal | Wait; do not power off |
| Progress sits at a high percentage for a long time | Still usually normal on a slow volume | Wait; prepare the escalation path |
| VNC unreachable but the instance still reports `Running` and no progress is visible | Ambiguous: the guest may be deep in update work, or the boot may have failed earlier | Check whether a start succeeded since the change, then decide |
| Same screen for many hours with a frozen percentage, and a completed snapshot exists | Possibly stuck | Consider recovery after the customer accepts the risk; a forced stop mid-transaction can leave the volume needing an integrity repair |
| Boot reaches a loader prompt, an emergency-mode mount error, or a bugcheck | Not a duration question | Go to the relevant branch: `references/boot-repair-guide__grub-efi-repair-guidance.md`, `references/boot-repair-guide__fstab-and-devices.md`, `references/boot-repair-guide__windows-bsod-triage.md` |

Waiting figures are customer-observed ranges, never promises for a specific instance, and this skill will not
commit to "if it exceeds N minutes it is broken". Where the customer has a business deadline, the honest
trade is: keep waiting on the current attempt, or stop the attempt and go to the snapshot rollback or data
rescue path, accepting what is lost.

## Kernel and distribution upgrades (Linux)

The dominant pattern: a kernel or major distribution release changes, and the boot loader configuration, the
installed loader, and the initial RAM disk end up inconsistent with each other. Failure shows at boot with a
loader prompt, a filesystem the loader cannot read, or a loop between firmware and the loader, because the
entry the loader selects no longer matches the modules on disk.

Manual order of operations, all customer-executed:

1. Boot an older entry that still starts, if one exists, and confirm which kernel the running system reports.
   That single fact separates "the new kernel is broken" from "the boot path to every kernel is broken".
2. From a working or rescue environment with the customer's root mounted, compare the recorded boot prefix
   with the real filesystem identifiers.
3. Rebuild the loader configuration and, in the same pass, the initial RAM disk, so the loader, the kernel,
   and the startup contents are regenerated together. Repairing only one of the three is what leaves an
   instance that boots after a reboot and fails after the next firmware change.
4. Where the system will not start at all, perform step 3 through the offline channel described in
   `references/boot-repair-guide__offline-repair-channel.md`.
5. After recovery, decide deliberately whether automatic kernel upgrades should remain enabled. The
   published article covering enabling or disabling kernel upgrades through the package manager is the
   customer-facing answer; it is a configuration change they make themselves.

A prevention note that recurs in tickets: components such as host security agents support specific kernel
builds. Before a kernel change on a production instance, the customer needs the compatibility list from the
component vendor, which is not something this skill can determine; ask for it rather than inferring it.

## Windows updates

| Observed | Likely axis | Route |
|---|---|---|
| Restart after a patch leaves the machine unreachable, and VNC shows a bugcheck | Driver or component incompatibility introduced or exposed by the update | `references/boot-repair-guide__windows-bsod-triage.md` |
| Stuck at the pre-logon update screen for a long time | Often normal duration | This file |
| The volume nearly full, updates failing, and a pending transaction file left behind | Capacity axis that presents as a patch failure | Capacity skill; note that the manual cleanup of a pending transaction is a change the customer performs after backing up |
| Repair attempt fails with a disk-space error code | Capacity axis | Capacity skill |
| Patch fails because a security product holds the file | Patch skill, with a process-stop step the customer performs | Patch skill |
| Update succeeded and now the remote desktop path fails | The OS is up | Connection path |
| System files missing after a failed update, and an in-place repair install is proposed | Patch and image axis | Patch skill or manual; keep the snapshot gate, and warn that third-party protection software frequently interferes with a repair install |

## The false-attribution check

Customers attribute boot failures to the most recent visible change. Before entering any update-related
branch, test the attribution:

- Did the machine boot successfully at any point after the update? If yes, the update may be irrelevant.
- Is the instance actually up according to its status and to console evidence, with the failure living in
  remote access? If yes, route to the connection path.
- Is the public address unreachable for everyone, including services unrelated to the update? If yes,
  suspect network-level filtering or an attack-driven traffic drop, and route to security handling.
- Did the failure appear after a different change in the same window, such as a resize, a credential reset,
  a disk operation, or an application install? Attribute to the change with evidence, not the change with a
  story.

Recording the failed attribution is valuable in the report: it prevents the customer from repeating the same
update-and-reboot cycle on the assumption that the patch is at fault.
