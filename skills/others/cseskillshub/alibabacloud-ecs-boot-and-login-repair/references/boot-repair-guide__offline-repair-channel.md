# Offline repair channel: prerequisites and constraints

Almost every real fix in this tier needs an out-of-band path, because the broken operating system cannot
serve a login session. There are three channels, and each has hard prerequisites that are cheap to check
and expensive to discover halfway through an attempt.

| Channel | What it gives you | Reach it by |
|---|---|---|
| VNC console | The screen, including loader prompts, and a keyboard into local single-user or recovery modes | Console instance connect, no network and no guest agent required |
| Repair or pre-install environment disk (the console's repair-disk and diagnostic entry) | A working Linux or Windows environment booted instead of the customer's, able to inspect and mount the customer's volumes | Console diagnostics, requires the instance stopped |
| Cross-instance attach | The customer's system or data disk mounted as a secondary disk on a healthy instance, then entered with a change-root | Detach and re-attach, requires the instance stopped, same zone, compatible type |

`python3 scripts/axes/boot_repair_guide/boot_repair_guide.py preflight` checks the machine-verifiable part of this list and prints
each item as satisfied, blocked, or unverifiable-in-this-release.

## The five prerequisites

1. **The instance is stopped.** A repair disk cannot be attached to a running instance, and detaching a
   system disk requires the stop. This is the prerequisite customers discover too late, so it is stated
   before any repair suggestion, together with the fact that a graceful stop may itself be impossible on a
   hung system and the fallback is a hard power-off, which is exactly the operation that corrupts a volume
   mid-write. Decide and record which of the two you are about to use.
2. **The snapshot is complete, not merely started.** The gate is 100 percent progress on the snapshot that
   covers the volume about to be detached or repaired. A snapshot that is still uploading is not a rollback
   point. This release cannot query snapshot progress, so the value comes from the customer with the console
   figure or screenshot, and the guidance is withheld until it is supplied.
3. **The repair target is in the same zone.** Block storage is a zonal resource. This applies both to a
   rescue instance you attach the customer's disk to and to a disk you build from a snapshot: an
   availability-zone mismatch produces "resource not found" rather than a permission error, which sends
   people hunting in the wrong place. The preflight compares the zone of the two instances from
   `DescribeInstances`.
4. **A working credential exists for the guest.** Mounting a repair environment to reset a lost password, or
   re-attaching a system disk, frequently stalls on credentials: the console wizard asks for a logon password
   or a bound key pair before it will complete. Custom images also differ here — some do not support the
   online password reset path at all and require the offline flow. Establish this before starting, because
   discovering it mid-attempt leaves the disk in a limbo state.
5. **The instance type's storage limits tolerate the extra disk.** Burstable entry-level families cap disk
   IOPS and throughput per instance rather than per disk. Attaching a second disk to such an instance to
   mount a repaired system disk can push the pair over the family ceiling and fail the attach, with an error
   that reads like a permissions problem. The preflight flags burstable families and states the ceiling
   question; resolving it may mean temporarily removing another data disk, or doing the copy from a
   different instance type.

## Known failure modes of the channel itself

- **The first attach attempt fails.** Attaching a repair or pre-install environment is not guaranteed to work
  on the first try; where it does not, the case stops being a self-service repair and becomes an offline
  support request. Say this up front so the customer's expectations and their maintenance window account for
  it.
- **The repair environment cannot reach the network.** A rescue environment usually needs its interface
  brought up manually, with the private address, prefix length, and default gateway taken from the instance's
  own network information, and those settings are temporary and lost on restart. Use the private address, not
  the public one. If a remote shell must be started in the rescue environment, expect the encryption-policy
  and resource-limit failures documented in `references/boot-repair-guide__boot-error-catalog.md` and prefer starting the daemon
  directly against its configuration file on a specific port.
- **Device names in the rescue environment differ from the ones in the instructions.** Confirm the actual
  device names after mounting, before running anything that takes a device argument.
- **Repairing the mounted copy of the file, not the live one.** The classic self-inflicted error: the rescue
  environment has its own `/etc/fstab` and its own loader configuration, so an edit that appears to succeed
  changes nothing about the customer's system. Any file edit or loader reinstall must be performed against
  the mounted customer root, via the change-root path or by naming the mounted location explicitly.
- **The disk comes back and the instance will not accept it.** Re-attaching a system disk can require
  converting the billing method, setting a password, or binding a key first; on a burstable type it can
  require removing another data disk. Note the sequence in the plan before starting, not after it fails.

## Downtime conversation

Use the same four elements every time, in this order; they are the minimum a customer needs to authorize a
window, and omitting the fourth is what generates escalations.

1. What will be done, in one sentence, and whether it touches data (`references/boot-repair-guide__evidence-checklist.md` keeps
   the read-only steps separate from these).
2. How long it typically takes, and what makes it longer (an incomplete snapshot, a large volume, a first
   attach failure).
3. What the customer must approve: the stop, the detach and re-attach, and the risk that the repair does not
   succeed and the case becomes a data rescue.
4. What is irreversible: the stop window itself, and any rollback, which discards changes made after the
   snapshot point. A rollback also requires a restart, so an idea of rolling back "without downtime" is not
   available.

Where the customer cannot accept a stop at all, there is no repair path in this skill. The honest options are
to schedule the window, or to copy the data out through a snapshot-built disk on a separate temporary
instance, which does not touch the original.
