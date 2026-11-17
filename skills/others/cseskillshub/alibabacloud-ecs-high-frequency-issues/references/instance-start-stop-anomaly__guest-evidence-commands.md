# In-guest evidence: the approved commands and their fallbacks

Some facts needed to close a start/stop ticket exist only inside the instance.
Cloud APIs cannot see them: no `Describe` action returns a guest mount table, a
failed boot unit, a previous boot log, or in-guest disk usage. The invocation
history API returns **past execution results**, not current state — it is how a
dispatched command's output is collected, not a source of live facts.

This file defines the entire in-guest surface of the skill: a frozen whitelist of
commands that may be dispatched (Layer 2, `ecs:run-command`), and — equally
important — the list of readings that are **never dispatched**, only requested
from the customer.

## The contract for every entry below

- Dispatch requires `--confirmed`, which the operator sets only after telling the
  customer: the exact command line, the target instance, that the command only
  enumerates state, and that the approval covers this one command at this one
  time.
- One run dispatches **one** command. Approval is not reusable.
- Commands are single, non-mutating statements. Compound strings, pipes into a
  writer, redirection, or a chained `&&` sequence are refused as a matter of
  construction, not policy: the whitelist is keyed, not free text.
- Anything not listed here is refused even with `--confirmed`, and becomes a
  customer-paste request.

## Approved whitelist

Keys are what `--guest-check` accepts; `--os-type` selects the set.

### Linux (`--os-type linux`, dispatched as `RunShellScript`)

| Key | Command | What it answers | How to read the output |
| --- | --- | --- | --- |
| `findmnt` | `findmnt` | The mounted filesystems as the guest sees them right now | Compare each `TARGET`/`SOURCE` pair against `DescribeDisks`. A cloud-attached data disk with no row here did not mount; a row pointing at a device the cloud does not list is the inverse mismatch |
| `df-h` | `df -h` | Space usage per mounted filesystem | A filesystem at 100 percent can hang shutdown and prevent a service from starting; if a mount point is absent from the list, it never mounted |
| `df-i` | `df -i` | Inode usage per mounted filesystem | Inodes exhausted with space free produces the same symptom as a full disk; look for 100 percent `IUse%` |
| `stat` | `stat <path>` (needs `--guest-arg`) | Facts about one path: existence, backing device, timestamps | Use it to settle "is `/mnt` an empty directory on the root disk, or a real mount" — the device id and mtime say which |
| `ls-by-uuid` | `ls -l /dev/disk/by-uuid` | UUID-to-device map | The bridge between a UUID referenced by the boot mount table and the device the cloud says is attached |

Argument rules: `--guest-arg` accepts one absolute path (`/` followed by
letters, digits, `.` `_` `-` `/`), no traversal and no shell metacharacters.
Anything else is rejected before any call is made.

### Windows (`--os-type windows`, dispatched as `RunPowerShellScript`)

| Key | Command | What it answers | How to read the output |
| --- | --- | --- | --- |
| `get-volume` | `Get-Volume` | Volumes, health and size | A volume with an unhealthy `HealthStatus`, or a missing expected volume, is the mount/disk-side candidate |
| `get-psdrive` | `Get-PSDrive` | Mounted drives with free space | A data disk present in `DescribeDisks` but absent here was not mounted after boot |
| `get-childitem` | `Get-ChildItem <path>` (needs `--guest-arg`) | Non-mutating listing of one path | Confirms whether expected directories or files exist at all |

Confidence caveat, stated in the report whenever a Windows capacity judgement
matters: **NTFS has no `df -i` equivalent**, so inode exhaustion cannot be
confirmed on Windows with the approved surface. Report space facts and mark the
inode area as unverified rather than implying it was checked.

## Refused by default: ask the customer to run and paste

These are the readings that would actually finish a boot investigation, and none
of them is on the approved list. Offer them as "please run this over VNC or SSH
and paste the output"; do not dispatch them, and do not escalate the request into
a general authorization ("just give me root and you can check whatever you need").

| Reading needed | Command the customer runs | Why it is not dispatched |
| --- | --- | --- |
| Boot mount table | `cat /etc/fstab` | Not on the whitelist; it is the definitive artifact for Family 1, so paste it |
| Failed boot units | `systemctl list-units --failed` | Not on the whitelist |
| Previous boot error log | `journalctl -b -1 -p err` | Not on the whitelist; note `-b -1` only exists if persistent journaling is on |
| Kernel ring buffer | `dmesg` | Not on the whitelist; after a reboot it shows the current boot only |
| Reboot history | `last -x reboot` | Not on the whitelist |
| Block devices from inside | `lsblk` | Not on the whitelist; substitute the cloud-side disk inventory plus `findmnt` |
| Historical per-process load | `atop -r /var/log/atop/<date>` | Only works if `atop` was installed and enabled beforehand — no cloud data source exists |
| Windows boot and system events | `Get-WinEvent -LogName System -MaxEvents 100` | Not on the whitelist |

Corrections and repairs are a separate category and are **never** performed or
proposed as skill actions: editing the mount table, commenting a config file,
`fsck`, formatting, partitioning, mounting, killing processes, restarting or
installing packages, installing the monitoring agent, changing kernel parameters.
Each is a manual step for the account holder, preceded by the risk notice in
`references/instance-start-stop-anomaly__risk-scripts-and-manual-steps.md`.

## When no guest channel works

This is the normal case for a boot failure, not the exception: the guest may be
unbootable, the Cloud Assistant agent may be offline or not installed, or the
customer may withhold approval. Then:

1. State which channel is unavailable and why, as a `[WARN|DEGRADE]` line.
2. Move to VNC — the only witness when SSH and RDP both fail, because it observes
   the console rather than a network service.
3. Ask for a screenshot and name the lines that decide the case (below).
4. If the instance is beyond a bootable state, stop collecting guest facts and
   switch to the recovery discussion (`DescribeSnapshots` plus the risk notices).

## VNC evidence checklist

What to tell a customer to look at and capture:

| Where the boot stops | What it points at |
| --- | --- |
| BIOS or bootloader message (`An operating system wasn't found`, `No bootable device`, `Invalid boot disk`) | Family 2: system disk or boot chain damage |
| Kernel panics or drops to emergency mode, mentioning a device or a timeout waiting for a device | Family 1: boot mount table vs attached disks |
| Repeated `Timed out waiting for device ...` / `Dependency failed for ...` | Family 3: boot-stage dependency |
| A login prompt is reached | The boot **succeeded**; connect and credential issues are a different tier |
| Service start failures after login | Guest service layer; route to the OS troubleshooting skill |
| Screen frozen with no new output for minutes while the state is still `Starting` | Family 4: exhaustion; capture the last lines before it froze |

Also capture, in the same screenshot: the exact timestamp shown, and whether the
disk activity indicator moved. These distinguish "slow" from "wedged".
