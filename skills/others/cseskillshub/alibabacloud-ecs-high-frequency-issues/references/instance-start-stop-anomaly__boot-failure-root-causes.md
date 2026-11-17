# Boot failure: root-cause families

Entry condition for this file: the instance is in `Starting` / `Pending` / the
"operating system starting" phase for longer than expected, or the console reports
a start failure, or the customer says the system never came back after a reboot or
a change. Order matters: the first family is the most common and the only one this
skill can largely confirm from cloud data alone.

Every recovery action below is a **manual console step** performed by the account
holder. This skill collects evidence, names the candidate, and states the risk. It
never starts, stops, reboots, rolls back, repairs or cleans anything.

## Matching customer wording

Screenshots and OCR text are routinely garbled. Match on short distinctive
anchors, not exact strings: `100.100.100.200`, `Network is unreachable`,
`dev-getty`, `operating system wasn't found`, `allocate memory`, `fstab`,
`emergency mode`. The anchor table used for `--symptom` lives in
`scripts/areas/instance_start_stop_anomaly/_constants.py`; feed it the customer's verbatim text rather than a
paraphrase.

## Family 1 — the boot-time mount table references a disk that is not there

**The single highest-value, most automatable cause in this tier.** Symptom
phrasing: "rebooted and my data is gone", "the disk disappeared", "MySQL cannot
find its files since the restart", or a boot that stalls and drops into
emergency mode.

Mechanism, both directions of the same mismatch:

- An entry names a device or UUID that no longer exists (a data disk that was
  detached, released, or never existed) → the boot blocks waiting for it, times
  out, and often falls into emergency mode.
- No entry exists for an attached data disk → the boot succeeds but the mount
  point is empty, so any service with data there fails afterwards.
- Entry fields are in the wrong order, or the options field is malformed → the
  disk is not mounted after reboot even though it mounted fine before.

**Cloud-side evidence (automatic, no approval needed):** `DescribeDisks` for the
instance answers "how many disks does this instance actually have, and what
device is each attached as". A guest that expects two data disks while the cloud
shows only a system disk is the whole diagnosis. The script prints the mismatch
for you, including the reverse case (guest mounts a device the cloud does not
show).

**Guest-side evidence:** the mounted view via the gated `findmnt` key, `df -h`
and `df -i`, and `ls -l /dev/disk/by-uuid` for the UUID-to-device map. The boot
mount table itself (`/etc/fstab`) is **not** on the whitelist — the customer
pastes it after VNC or SSH access.

**Recovery, in the safe order:**

1. Snapshot the system disk first (Class B write, with the billing notice).
2. The customer edits the mount table to remove or correct the offending line —
   comment the line out rather than deleting it, so it can be restored.
3. The customer reboots from the console (never from inside the session when the
   host is resource-starved; see Family 4).
4. Verify the mount returned, then configure auto-mount for the data disk so the
   next reboot does not repeat it.

Do not perform step 2 or 3. Explain them, and state that an incorrect mount line
will break the next boot again.

## Family 2 — the system disk cannot be booted from

Symptom phrasing: the boot screen shows `An operating system wasn't found`
(SeaBIOS), `No bootable device`, `Invalid boot disk`, `INACCESSIBLE_BOOT_DEVICE`,
or a Windows instance that never reaches the desktop. On Windows, file-level
damage shows up as missing system directories once the disk is inspected from
outside.

**Cloud-side evidence:** `DescribeDisks` (does the system disk exist, is it
attached, is its status normal), `DescribeSnapshots` (is there any usable
recovery point, and from when — only `accomplished` snapshots can roll back),
`DescribeInstancesFullStatus` plus `DescribeInstanceHistoryEvents` (rule a
platform event in or out).

**Guest-side evidence:** usually none reachable — Cloud Assistant needs a booted
guest, so VNC is the only witness. Guide the customer to VNC and tell them which
lines matter: the BIOS/bootloader error text, the partition and disk geometry it
names, and whether the failure appears before any kernel output.

**Recovery paths (all customer-executed, all with snapshot-first):**

| Path | When | Irreversibility |
| --- | --- | --- |
| Roll the system disk back to an earlier snapshot | A usable snapshot predates the damage | Overwrites all current disk content |
| Re-initialize the system disk, then attach an old snapshot as a new pay-as-you-go disk to copy data off | No rollback point, or the rolled-back point is also broken | Original system disk content is replaced |
| Create a custom image from the most recent system-disk snapshot and share it with the investigating account | Support needs to reproduce the failure offline | Adds image storage cost; nothing destroyed |

Repeated rollback attempts without first snapshotting the **current** state is a
common and self-defeating pattern in this tier: each attempt can destroy the only
evidence and the only remaining recovery point. Enforce the order verbally.

Honest limit: this family frequently ends with an unconfirmed root cause — damage
of unknown origin to system files cannot be diagnosed from symptoms. Say so; do
not invent a cause.

## Family 3 — a boot-stage dependency times out

Symptom phrasing, typically after a network or security-group edit: the boot
output contains a failed metadata-service call such as
`Calling http://100.100.100.200/.../meta-data/instance-id failed ...
[Errno 101] Network is unreachable`, or unit timeouts like
`Timed out waiting for device dev-getty.device` and
`Dependency failed for Serial Getty on getty`, sometimes with `Login incorrect`
at a VNC prompt.

Mechanism: early-boot components (cloud-init and units that depend on a device)
block on something that never becomes ready, so the boot stalls at that step even
though the disk and the hypervisor are fine.

**Evidence:** recent-change history from the customer (security-group edits,
route or vSwitch changes, rules for uncommon ports — capture the change time and
compare it with `DescribeInstanceHistoryEvents`), plus the boot-screen lines. The metadata
endpoint `100.100.100.200` is link-local to the instance; nothing outside the
guest can query it, so a guest reading or a VNC screenshot is the only proof.

**Direction, not action:** confirm whether a routing or firewall change removed
the instance's own path to its metadata service, and hand the configuration part
to the connection skills. If the boot log shows the guest did reach a login
prompt, the boot is finished and this is no longer a start/stop problem.

## Family 4 — resource exhaustion hangs the guest

Symptom phrasing: `-bash: fork: Cannot allocate memory`, "the server is frozen",
"every command hangs", "high load", "the site died at 3am", or a stop that took
far longer than 15 minutes on a machine that was busy beforehand.

Mechanism: with memory or process slots exhausted, the OS cannot complete the
ordered shutdown (Family: state machine), so the transition drags; and after a
reboot, services that consume the same memory immediately re-exhaust it, so the
instance looks like it "will not start".

**Cloud-side evidence:** `DescribeMetricLast` for CPU, memory usage and disk
read/write. Read the shape, not just the peak: sustained near-100 percent on
memory or on disk IO is the signature. Judgement caveat — a memory metric is only
reported when the monitoring agent is installed inside the instance; if the area
is empty, the agent is probably absent, which is **not** evidence that memory was
fine.

**Guest-side evidence:** gated `df -h` / `df -i` for a full disk masquerading as a
boot problem; otherwise the customer pastes memory, process-count and `atop`
readings. Historical per-process data does not exist on the cloud side — recommend
deploying `atop` with autostart now so the next incident is answerable.

**Direction, not action:** change the instance type during a low-traffic window
(a spec change takes effect only after a deliberate reboot, so snapshot first);
raise the process limit or configure paging inside the guest; fix the workload
that exhausts memory. All are customer-executed. Prefer a console reboot over an
in-session `reboot` command when the session itself is unresponsive — the console
path is observable and the in-session one can wedge on the very resource that is
exhausted.

## Family 5 — a component the boot needs was removed or replaced

Symptom phrasing: it broke right after a package upgrade, a security cleanup, an
antivirus scan, or a control-panel repair; "ssh is gone", "the library will not
load", "after removing the miner I cannot connect".

Examples of the shape (not a catalogue): an OpenSSL or glibc upgrade that leaves
binaries linked against a version no longer present; a security tool that deleted
the SSH server package; an intrusion that dropped database files; a control panel
that overwrote a service's configuration.

**Cloud-side evidence:** there is little — the instance may well be `Running`. The
value of the queries here is negative and still decisive: it proves the platform
side is fine, which is the fact that ends the argument "Alibaba Cloud stopped my
service".

**Disposition:** route to the OS troubleshooting skill with the boot timeline,
the VNC observation, and the customer's own change history attached. Repairing a
deleted system component is a write operation inside the guest; this skill does
not perform it, and neither package installation nor service restart is on its
whitelist.

## Cross-cutting rules

1. **Snapshot before anything else**, whenever the next step could lose data —
   rollback, re-initialization, disk cleanup, mount-table edit, spec change.
2. **Rule the platform in or out** (`DescribeInstancesFullStatus`,
   `DescribeInstanceHistoryEvents`) before spending the customer's time on guest
   archaeology.
3. **Say what is unknown.** Several tickets in this tier close with an unproven
   cause. A candidate list with the discriminating evidence attached is a correct
   outcome; a confident invention is not.
4. **Degrade loudly.** Every unavailable area gets a line in the report and a
   substitute path.
